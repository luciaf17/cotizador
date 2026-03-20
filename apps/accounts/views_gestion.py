"""Views de gestión de usuarios y dashboard del dueño."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import rol_requerido
from apps.accounts.models import User
from apps.catalogo.models import Implemento
from apps.clientes.models import Cliente, FormaPago, TipoCliente
from apps.cotizaciones.models import Cotizacion
from apps.tenants.models import Tenant


def _get_tenant(request):
    if hasattr(request, 'tenant') and request.tenant:
        return request.tenant
    return Tenant.objects.filter(activo=True).first()


# ── Dashboard ────────────────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def dashboard(request):
    tenant = _get_tenant(request)

    cotizaciones = Cotizacion.objects.filter(tenant=tenant)
    pendientes = cotizaciones.filter(estado='aprobada', aprobada_por__isnull=True).count()
    confirmadas = cotizaciones.filter(estado='confirmada')
    total_confirmadas = confirmadas.aggregate(total=Sum('precio_total'))['total'] or 0
    vendedores = User.objects.filter(tenant=tenant, activo=True, rol='vendedor').count()
    implementos = Implemento.objects.filter(tenant=tenant).count()

    # Top vendedores por monto confirmado (excluir superusers)
    top_vendedores = (
        confirmadas
        .filter(vendedor__is_superuser=False)
        .values('vendedor__nombre', 'vendedor__email')
        .annotate(total=Sum('precio_total'), cantidad=Count('id'))
        .order_by('-total')[:5]
    )

    # Top implementos
    top_implementos = (
        confirmadas
        .values('implemento__nombre')
        .annotate(total=Sum('precio_total'), cantidad=Count('id'))
        .order_by('-total')[:5]
    )

    return render(request, 'gestion/dashboard.html', {
        'pendientes': pendientes,
        'total_cotizaciones': cotizaciones.count(),
        'total_confirmadas_monto': total_confirmadas,
        'cant_confirmadas': confirmadas.count(),
        'vendedores': vendedores,
        'implementos': implementos,
        'top_vendedores': top_vendedores,
        'top_implementos': top_implementos,
    })


# ── Gestión de usuarios ──────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def usuarios_lista(request):
    tenant = _get_tenant(request)
    qs = User.objects.filter(tenant=tenant)
    if request.user.rol != 'admin':
        qs = qs.exclude(rol='admin')
    usuarios = qs.order_by('rol', 'nombre')
    return render(request, 'gestion/usuarios_lista.html', {'usuarios': usuarios})


@login_required
@rol_requerido('admin', 'dueno')
def usuario_crear(request):
    tenant = _get_tenant(request)
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        password = request.POST.get('password', '').strip()
        rol = request.POST.get('rol', 'vendedor')
        requiere_validacion = request.POST.get('requiere_validacion') == '1'
        bonif_max = Decimal(request.POST.get('bonif_max_porcentaje', '0'))
        comision = Decimal(request.POST.get('comision_porcentaje', '0'))

        if not email or not nombre or not password:
            messages.error(request, 'Email, nombre y contrasena son obligatorios.')
            return render(request, 'gestion/usuario_form.html', {'modo': 'crear'})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Ya existe un usuario con ese email.')
            return render(request, 'gestion/usuario_form.html', {'modo': 'crear'})

        User.objects.create_user(
            email=email, password=password, nombre=nombre,
            tenant=tenant, rol=rol, requiere_validacion=requiere_validacion,
            bonif_max_porcentaje=bonif_max, comision_porcentaje=comision,
        )
        messages.success(request, f'Usuario {nombre} creado.')
        return redirect('usuarios_lista')

    return render(request, 'gestion/usuario_form.html', {'modo': 'crear'})


@login_required
@rol_requerido('admin', 'dueno')
def usuario_editar(request, user_id):
    tenant = _get_tenant(request)
    usuario = get_object_or_404(User, id=user_id, tenant=tenant)

    if request.method == 'POST':
        usuario.nombre = request.POST.get('nombre', usuario.nombre)
        usuario.rol = request.POST.get('rol', usuario.rol)
        usuario.requiere_validacion = request.POST.get('requiere_validacion') == '1'
        usuario.bonif_max_porcentaje = Decimal(request.POST.get('bonif_max_porcentaje', '0'))
        usuario.comision_porcentaje = Decimal(request.POST.get('comision_porcentaje', '0'))
        usuario.activo = request.POST.get('activo') == '1'

        new_password = request.POST.get('password', '').strip()
        if new_password:
            usuario.set_password(new_password)

        usuario.save()
        messages.success(request, f'Usuario {usuario.nombre} actualizado.')
        return redirect('usuarios_lista')

    return render(request, 'gestion/usuario_form.html', {
        'modo': 'editar',
        'usuario': usuario,
    })


@login_required
@rol_requerido('admin', 'dueno')
def usuario_toggle_activo(request, user_id):
    tenant = _get_tenant(request)
    usuario = get_object_or_404(User, id=user_id, tenant=tenant)
    if request.method == 'POST':
        usuario.activo = not usuario.activo
        usuario.is_active = usuario.activo
        usuario.save()
        estado = 'activado' if usuario.activo else 'desactivado'
        messages.success(request, f'Usuario {usuario.nombre} {estado}.')
    return redirect('usuarios_lista')


# ── CRUD Tipos de Cliente ────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def tipos_cliente_lista(request):
    tenant = _get_tenant(request)
    tipos = TipoCliente.objects.filter(tenant=tenant)
    return render(request, 'gestion/tipos_cliente.html', {'tipos': tipos})


@login_required
@rol_requerido('admin', 'dueno')
def tipo_cliente_guardar(request):
    tenant = _get_tenant(request)
    if request.method == 'POST':
        tipo_id = request.POST.get('tipo_id')
        nombre = request.POST.get('nombre', '').strip()
        bonif = Decimal(request.POST.get('bonificacion_default', '0'))

        activo = request.POST.get('activo') == '1'

        if tipo_id:
            tipo = get_object_or_404(TipoCliente, id=tipo_id, tenant=tenant)
            tipo.nombre = nombre
            tipo.bonificacion_default = bonif
            tipo.activo = activo
            tipo.save()
        else:
            TipoCliente.objects.create(tenant=tenant, nombre=nombre, bonificacion_default=bonif)

        messages.success(request, f'Tipo de cliente "{nombre}" guardado.')
    return redirect('tipos_cliente_lista')


# ── CRUD Formas de Pago ──────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def formas_pago_lista(request):
    tenant = _get_tenant(request)
    formas = FormaPago.objects.filter(tenant=tenant)
    return render(request, 'gestion/formas_pago.html', {'formas': formas})


@login_required
@rol_requerido('admin', 'dueno')
def forma_pago_guardar(request):
    tenant = _get_tenant(request)
    if request.method == 'POST':
        fp_id = request.POST.get('forma_id')
        nombre = request.POST.get('nombre', '').strip()
        bonif = Decimal(request.POST.get('bonificacion_porcentaje', '0'))
        activo = request.POST.get('activo') == '1'

        if fp_id:
            fp = get_object_or_404(FormaPago, id=fp_id, tenant=tenant)
            fp.nombre = nombre
            fp.bonificacion_porcentaje = bonif
            fp.activo = activo
            fp.save()
        else:
            FormaPago.objects.create(tenant=tenant, nombre=nombre, bonificacion_porcentaje=bonif)

        messages.success(request, f'Forma de pago "{nombre}" guardada.')
    return redirect('formas_pago_lista')


# ── CRUD Clientes ────────────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def clientes_lista(request):
    tenant = _get_tenant(request)
    clientes = Cliente.objects.filter(tenant=tenant).select_related('tipo_cliente').order_by('nombre')
    return render(request, 'gestion/clientes_lista.html', {'clientes': clientes})


@login_required
@rol_requerido('admin', 'dueno')
def cliente_crear(request):
    tenant = _get_tenant(request)
    tipos = TipoCliente.objects.filter(tenant=tenant, activo=True)

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        tipo_id = request.POST.get('tipo_cliente')
        telefono = request.POST.get('telefono', '').strip() or None
        email = request.POST.get('email', '').strip() or None
        direccion = request.POST.get('direccion', '').strip() or None
        bonif = Decimal(request.POST.get('bonificacion_porcentaje', '0'))

        if not nombre or not tipo_id:
            messages.error(request, 'Nombre y tipo de cliente son obligatorios.')
            return render(request, 'gestion/cliente_form.html', {'modo': 'crear', 'tipos': tipos})

        tipo = get_object_or_404(TipoCliente, id=tipo_id, tenant=tenant)
        Cliente.objects.create(
            tenant=tenant, tipo_cliente=tipo, nombre=nombre,
            telefono=telefono, email=email, direccion=direccion,
            bonificacion_porcentaje=bonif,
        )
        messages.success(request, f'Cliente "{nombre}" creado.')
        return redirect('clientes_lista')

    return render(request, 'gestion/cliente_form.html', {'modo': 'crear', 'tipos': tipos})


@login_required
@rol_requerido('admin', 'dueno')
def cliente_editar(request, cliente_id):
    tenant = _get_tenant(request)
    cliente = get_object_or_404(Cliente, id=cliente_id, tenant=tenant)
    tipos = TipoCliente.objects.filter(tenant=tenant, activo=True)

    if request.method == 'POST':
        cliente.nombre = request.POST.get('nombre', cliente.nombre).strip()
        tipo_id = request.POST.get('tipo_cliente')
        if tipo_id:
            cliente.tipo_cliente = get_object_or_404(TipoCliente, id=tipo_id, tenant=tenant)
        cliente.telefono = request.POST.get('telefono', '').strip() or None
        cliente.email = request.POST.get('email', '').strip() or None
        cliente.direccion = request.POST.get('direccion', '').strip() or None
        cliente.bonificacion_porcentaje = Decimal(request.POST.get('bonificacion_porcentaje', '0'))
        cliente.save()
        messages.success(request, f'Cliente "{cliente.nombre}" actualizado.')
        return redirect('clientes_lista')

    return render(request, 'gestion/cliente_form.html', {
        'modo': 'editar',
        'cliente': cliente,
        'tipos': tipos,
    })


@login_required
@rol_requerido('admin', 'dueno')
def cliente_eliminar(request, cliente_id):
    tenant = _get_tenant(request)
    cliente = get_object_or_404(Cliente, id=cliente_id, tenant=tenant)
    if request.method == 'POST':
        nombre = cliente.nombre
        cliente.delete()
        messages.success(request, f'Cliente "{nombre}" eliminado.')
    return redirect('clientes_lista')


# ── Reportes ─────────────────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def reportes(request):
    tenant = _get_tenant(request)

    filtro_estado = request.GET.get('estado', 'confirmada')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    qs = Cotizacion.objects.filter(tenant=tenant)
    if filtro_estado == 'confirmada':
        qs = qs.filter(estado='confirmada')
    elif filtro_estado == 'aprobada':
        qs = qs.filter(estado='aprobada')

    if fecha_desde:
        qs = qs.filter(created_at__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(created_at__date__lte=fecha_hasta)

    total_monto = qs.aggregate(t=Sum('precio_total'))['t'] or Decimal('0')
    total_comision = qs.aggregate(t=Sum('comision_monto'))['t'] or Decimal('0')

    por_vendedor = (
        qs
        .values('vendedor__nombre')
        .annotate(monto=Sum('precio_total'), cantidad=Count('id'), comision=Sum('comision_monto'))
        .order_by('-monto')
    )

    por_implemento = (
        qs
        .values('implemento__nombre')
        .annotate(monto=Sum('precio_total'), cantidad=Count('id'))
        .order_by('-monto')
    )

    por_cliente = (
        qs
        .values('cliente__nombre', 'cliente__tipo_cliente__nombre')
        .annotate(monto=Sum('precio_total'), cantidad=Count('id'))
        .order_by('-monto')[:10]
    )

    return render(request, 'gestion/reportes.html', {
        'total_monto': total_monto,
        'total_comision': total_comision,
        'cant_resultados': qs.count(),
        'por_vendedor': por_vendedor,
        'por_implemento': por_implemento,
        'por_cliente': por_cliente,
        'filtro_estado': filtro_estado,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })
