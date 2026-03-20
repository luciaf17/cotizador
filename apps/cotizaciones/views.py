from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalogo.models import Familia, Implemento, Producto, Propiedad
from apps.clientes.models import Cliente, FormaPago, TipoCliente
from apps.precios.models import EstructuraPrearmado, ListaPrecio, Prearmado, PrecioProducto
from apps.tenants.models import Tenant

from .models import Cotizacion, CotizacionItem
from .services import (
    calcular_dimensiones,
    calcular_totales,
    check_compatibilidad,
    check_propiedades,
    get_productos_disponibles,
    get_rodados_para_implemento,
)


def _get_tenant(request=None):
    """Obtener tenant del request (middleware) o fallback al primero activo."""
    if request and hasattr(request, 'tenant') and request.tenant:
        return request.tenant
    return Tenant.objects.filter(activo=True).first()


def _get_ordenes(implemento):
    """Obtener lista ordenada de órdenes únicos para un implemento."""
    return list(
        Familia.objects.filter(implemento=implemento)
        .values_list('orden', flat=True)
        .distinct()
        .order_by('orden')
    )


def _get_items_data(cotizacion):
    """Convertir items de cotización a formato para calcular_totales."""
    return [
        {
            'precio_linea': item.precio_linea,
            'iva_porcentaje': item.iva_porcentaje,
        }
        for item in cotizacion.items.all()
    ]


def _get_selected_ids(cotizacion):
    """IDs de productos ya seleccionados en la cotización."""
    return list(cotizacion.items.values_list('producto_id', flat=True))


def _build_dimensiones(acumulado, tenant):
    """Construir lista de dimensiones para el template."""
    if not acumulado:
        return []
    dimensiones = []
    for prop in Propiedad.objects.filter(tenant=tenant):
        if prop.id in acumulado:
            dimensiones.append({
                'nombre': prop.nombre,
                'valor': acumulado[prop.id],
                'unidad': prop.unidad,
            })
    return dimensiones


def _build_paso_context(cotizacion, orden, tenant):
    """Construir contexto completo para un paso (reutilizable)."""
    implemento = cotizacion.implemento
    ordenes = _get_ordenes(implemento)
    current_idx = ordenes.index(orden) if orden in ordenes else 0

    seleccionados_ids = _get_selected_ids(cotizacion)
    acumulado = calcular_dimensiones(seleccionados_ids)

    # Familias del orden actual
    familias = Familia.objects.filter(implemento=implemento, orden=orden)

    # Productos disponibles (filtrados por compatibilidad y propiedades)
    todos_disponibles = get_productos_disponibles(
        implemento.id, orden, seleccionados_ids, acumulado,
    )
    ids_disponibles = {p.id for p in todos_disponibles}

    familias_data = []
    for familia in familias:
        # Items ya seleccionados en esta familia (de la DB)
        seleccionados_familia = set(
            cotizacion.items.filter(familia=familia).values_list('producto_id', flat=True),
        )

        # Todos los productos de la familia en orden estable (DB order),
        # mostrando solo los disponibles + los ya seleccionados
        productos_familia = []
        for p in Producto.objects.filter(familia=familia).order_by('orden', 'id'):
            if p.id in ids_disponibles or p.id in seleccionados_familia:
                productos_familia.append(p)

        precios = dict(
            PrecioProducto.objects.filter(
                lista=cotizacion.lista,
                producto_id__in=[p.id for p in productos_familia],
            ).values_list('producto_id', 'precio'),
        )

        familias_data.append({
            'familia': familia,
            'productos': [
                {
                    'producto': p,
                    'precio': precios.get(p.id, Decimal('0')),
                    'seleccionado': p.id in seleccionados_familia,
                }
                for p in productos_familia
            ],
            'seleccionados': seleccionados_familia,
        })

    dimensiones = _build_dimensiones(acumulado, tenant)

    # Resumen de selecciones: todos los items de la cotización
    items_resumen = []
    for item in cotizacion.items.select_related('producto', 'familia').all():
        items_resumen.append({
            'item': item,
            'puede_quitar': item.familia.obligatoria == 'NO',
        })

    # Nav
    has_prev = current_idx > 0
    prev_orden = ordenes[current_idx - 1] if has_prev else None
    has_next = current_idx + 1 < len(ordenes)
    next_orden = ordenes[current_idx + 1] if has_next else None

    # Auto-avance: tipo O con una sola familia
    todas_tipo_o = all(f['familia'].tipo_seleccion == 'O' for f in familias_data)
    una_sola_familia = len(familias_data) == 1
    auto_avance = todas_tipo_o and una_sola_familia
    mostrar_continuar = not auto_avance

    # Verificar si falta selección obligatoria (para deshabilitar Continuar)
    # Familias tipo O con mismo orden son alternativas mutuamente excluyentes
    # (SPEC 5.2): seleccionar en UNA satisface la obligatoriedad del grupo.
    # Familias tipo Y se evalúan individualmente.
    falta_obligatorio = False
    familias_o_obligatorias = [
        fd for fd in familias_data
        if fd['familia'].tipo_seleccion == 'O' and fd['familia'].obligatoria == 'SI'
    ]
    if familias_o_obligatorias:
        # Al menos una familia O obligatoria con productos debe tener selección
        tiene_productos = any(fd['productos'] for fd in familias_o_obligatorias)
        tiene_seleccion = any(fd['seleccionados'] for fd in familias_o_obligatorias)
        if tiene_productos and not tiene_seleccion:
            falta_obligatorio = True

    for fd in familias_data:
        if fd['familia'].tipo_seleccion == 'Y' and fd['familia'].obligatoria == 'SI':
            if fd['productos'] and not fd['seleccionados']:
                falta_obligatorio = True
                break

    # Determinar URL de "Continuar"
    if has_next:
        continuar_url = f'/{cotizacion.id}/paso/{next_orden}/'
    else:
        # Último paso: verificar rodados
        rodados = get_rodados_para_implemento(implemento, seleccionados_ids, acumulado)
        if rodados:
            continuar_url = f'/{cotizacion.id}/rodados/0/'
        else:
            continuar_url = f'/{cotizacion.id}/bonificaciones/'

    return {
        'cotizacion': cotizacion,
        'orden': orden,
        'ordenes': ordenes,
        'current_idx': current_idx,
        'familias_data': familias_data,
        'dimensiones': dimensiones,
        'has_prev': has_prev,
        'prev_orden': prev_orden,
        'has_next': has_next,
        'next_orden': next_orden,
        'mostrar_continuar': mostrar_continuar,
        'falta_obligatorio': falta_obligatorio,
        'continuar_url': continuar_url,
        'es_rodado': False,
        'items_resumen': items_resumen,
    }


# ── Inicio: selección de cliente ─────────────────────────────────────


@login_required
def inicio(request):
    tenant = _get_tenant(request)
    tipos_cliente = TipoCliente.objects.filter(tenant=tenant, activo=True) if tenant else []
    return render(request, 'cotizaciones/inicio.html', {
        'tipos_cliente': tipos_cliente,
    })


@login_required
def buscar_clientes(request):
    tenant = _get_tenant(request)
    q = request.GET.get('q', '').strip()
    clientes = []
    if q and tenant:
        clientes = Cliente.objects.filter(
            tenant=tenant,
        ).filter(
            Q(nombre__icontains=q) | Q(email__icontains=q) | Q(telefono__icontains=q),
        )[:10]
    return render(request, 'cotizaciones/partials/clientes_lista.html', {
        'clientes': clientes,
        'q': q,
    })


@login_required
def crear_cliente(request):
    tenant = _get_tenant(request)
    if request.method == 'POST':
        tipo_id = request.POST.get('tipo_cliente')
        nombre = request.POST.get('nombre', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        direccion = request.POST.get('direccion', '').strip()

        if not nombre or not tipo_id:
            return HttpResponse(
                '<div style="color:#f87171;font-size:13px;padding:10px;'
                'background:rgba(248,113,113,0.1);border-radius:8px;">'
                'Nombre y tipo son obligatorios.</div>',
            )

        tipo = get_object_or_404(TipoCliente, id=tipo_id, tenant=tenant)
        cliente = Cliente.objects.create(
            tenant=tenant,
            tipo_cliente=tipo,
            nombre=nombre,
            telefono=telefono or None,
            email=email or None,
            direccion=direccion or None,
            bonificacion_porcentaje=tipo.bonificacion_default,
        )
        return redirect('seleccionar_implemento', cliente_id=cliente.id)

    return HttpResponse(status=400)


# ── Selección de implemento ──────────────────────────────────────────


@login_required
def seleccionar_implemento(request, cliente_id):
    tenant = _get_tenant(request)
    cliente = get_object_or_404(Cliente, id=cliente_id, tenant=tenant)
    implementos = Implemento.objects.filter(tenant=tenant)
    return render(request, 'cotizaciones/implementos.html', {
        'cliente': cliente,
        'implementos': implementos,
    })


# ── Crear cotización y empezar flujo ─────────────────────────────────


@login_required
def cotizacion_nueva(request, cliente_id, implemento_id):
    tenant = _get_tenant(request)
    cliente = get_object_or_404(Cliente, id=cliente_id, tenant=tenant)
    implemento = get_object_or_404(Implemento, id=implemento_id, tenant=tenant)
    lista = ListaPrecio.objects.filter(tenant=tenant, estado='vigente').first()

    if not lista:
        messages.error(request, 'No hay lista de precios vigente.')
        return redirect('seleccionar_implemento', cliente_id=cliente_id)

    forma_pago = FormaPago.objects.filter(tenant=tenant, activo=True).first()
    if not forma_pago:
        messages.error(request, 'No hay formas de pago configuradas.')
        return redirect('seleccionar_implemento', cliente_id=cliente_id)

    count = Cotizacion.objects.filter(tenant=tenant).count() + 1
    numero = f'COT-{date.today().year}-{count:04d}'

    cotizacion = Cotizacion.objects.create(
        tenant=tenant,
        implemento=implemento,
        vendedor=request.user,
        cliente=cliente,
        lista=lista,
        forma_pago=forma_pago,
        numero=numero,
    )

    # Si hay prearmados para este implemento, mostrar paso intermedio
    prearmados = Prearmado.objects.filter(tenant=tenant, implemento=implemento)
    if prearmados.exists():
        return render(request, 'cotizaciones/prearmado_rapido.html', {
            'cotizacion': cotizacion,
            'prearmados': prearmados,
        })

    ordenes = _get_ordenes(implemento)
    if ordenes:
        return redirect('cotizacion_paso', cotizacion_id=cotizacion.id, orden=ordenes[0])

    return redirect('cotizacion_bonificaciones', cotizacion_id=cotizacion.id)


@login_required
def cargar_prearmado(request, cotizacion_id):
    """Carga productos de un prearmado en la cotización y salta a bonificaciones."""
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)

    if request.method == 'POST':
        prearmado_id = request.POST.get('prearmado_id')

        if not prearmado_id:
            # "Cotizar desde cero" — ir al paso 1
            ordenes = _get_ordenes(cotizacion.implemento)
            if ordenes:
                return redirect('cotizacion_paso', cotizacion_id=cotizacion.id, orden=ordenes[0])
            return redirect('cotizacion_bonificaciones', cotizacion_id=cotizacion.id)

        prearmado = get_object_or_404(Prearmado, id=prearmado_id, tenant=tenant)
        estructura = EstructuraPrearmado.objects.filter(prearmado=prearmado).select_related('producto', 'producto__familia')

        # Limpiar items existentes
        cotizacion.items.all().delete()

        descartados = []
        cargados = 0
        for est in estructura:
            prod = est.producto
            # Obtener precio
            precio = Decimal('0')
            try:
                pp = PrecioProducto.objects.get(lista=cotizacion.lista, producto=prod)
                precio = pp.precio
            except PrecioProducto.DoesNotExist:
                pass

            CotizacionItem.objects.create(
                cotizacion=cotizacion,
                producto=prod,
                familia=prod.familia,
                cantidad=est.cantidad,
                precio_unitario=precio,
                precio_linea=precio * est.cantidad,
                iva_porcentaje=prod.iva_porcentaje,
            )
            cargados += 1

        if descartados:
            messages.warning(request, f'Se descartaron {len(descartados)} productos incompatibles: {", ".join(descartados)}')

        messages.success(request, f'Prearmado "{prearmado.nombre}" cargado ({cargados} productos). Ajusta bonificaciones.')
        return redirect('cotizacion_bonificaciones', cotizacion_id=cotizacion.id)

    return redirect('cotizacion_inicio')


# ── Paso step-by-step ────────────────────────────────────────────────


@login_required
def paso(request, cotizacion_id, orden):
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)
    context = _build_paso_context(cotizacion, orden, tenant)

    if request.headers.get('HX-Request'):
        return render(request, 'cotizaciones/partials/paso_content.html', context)

    return render(request, 'cotizaciones/paso.html', context)


@login_required
def seleccionar_producto(request, cotizacion_id):
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)

    if request.method != 'POST':
        return HttpResponse(status=405)

    producto_id = request.POST.get('producto_id')
    familia_id = request.POST.get('familia_id')
    accion = request.POST.get('accion', 'add')
    orden = int(request.POST.get('orden', 0))

    if not producto_id or not familia_id:
        return HttpResponse(status=400)

    producto = get_object_or_404(Producto, id=producto_id)
    familia = get_object_or_404(Familia, id=familia_id)

    if accion == 'remove':
        cotizacion.items.filter(producto=producto, familia=familia).delete()
    else:
        if familia.tipo_seleccion == 'O':
            # SPEC 5.2: familias tipo O con mismo orden son alternativas
            # mutuamente excluyentes. Limpiar items de TODAS las familias
            # tipo O del mismo orden, no solo la familia actual.
            familias_o_mismo_orden = Familia.objects.filter(
                implemento=cotizacion.implemento,
                orden=orden,
                tipo_seleccion='O',
            )
            cotizacion.items.filter(familia__in=familias_o_mismo_orden).delete()

        precio = Decimal('0')
        try:
            pp = PrecioProducto.objects.get(lista=cotizacion.lista, producto=producto)
            precio = pp.precio
        except PrecioProducto.DoesNotExist:
            pass

        CotizacionItem.objects.create(
            cotizacion=cotizacion,
            producto=producto,
            familia=familia,
            cantidad=1,
            precio_unitario=precio,
            precio_linea=precio,
            iva_porcentaje=producto.iva_porcentaje,
        )

    # Determinar siguiente destino
    familias_del_orden = Familia.objects.filter(
        implemento=cotizacion.implemento, orden=orden,
    )
    todas_tipo_o = all(f.tipo_seleccion == 'O' for f in familias_del_orden)
    una_sola_familia = familias_del_orden.count() == 1
    auto_avance = familia.tipo_seleccion == 'O' and todas_tipo_o and una_sola_familia

    if auto_avance:
        ordenes = _get_ordenes(cotizacion.implemento)
        current_idx = ordenes.index(orden) if orden in ordenes else 0
        if current_idx + 1 < len(ordenes):
            return redirect('cotizacion_paso', cotizacion_id=cotizacion_id, orden=ordenes[current_idx + 1])
        else:
            sel = _get_selected_ids(cotizacion)
            acum = calcular_dimensiones(sel)
            rodados = get_rodados_para_implemento(cotizacion.implemento, sel, acum)
            if rodados:
                return redirect('cotizacion_rodados', cotizacion_id=cotizacion_id, familia_idx=0)
            return redirect('cotizacion_bonificaciones', cotizacion_id=cotizacion_id)

    # No auto-avance: recargar paso completo
    return redirect('cotizacion_paso', cotizacion_id=cotizacion_id, orden=orden)


@login_required
def quitar_item(request, cotizacion_id, item_id):
    """Quitar un item desde el resumen lateral (solo familias con obligatoria=NO)."""
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)

    if request.method == 'POST':
        item = get_object_or_404(CotizacionItem, id=item_id, cotizacion=cotizacion)
        if item.familia.obligatoria == 'NO':
            orden = item.familia.orden
            item.delete()
            return redirect('cotizacion_paso', cotizacion_id=cotizacion_id, orden=orden)

    return redirect('cotizacion_inicio')


# ── Rodados automáticos ──────────────────────────────────────────────


@login_required
def paso_rodados(request, cotizacion_id, familia_idx):
    """Paso de rodados: Llantas → Ejes → Elásticos."""
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)

    # Recalcular con TODOS los items actuales (incluyendo rodados ya elegidos)
    seleccionados_ids = _get_selected_ids(cotizacion)
    acumulado = calcular_dimensiones(seleccionados_ids)
    rodados = get_rodados_para_implemento(cotizacion.implemento, seleccionados_ids, acumulado)

    if not rodados or familia_idx >= len(rodados):
        return redirect('cotizacion_bonificaciones', cotizacion_id=cotizacion.id)

    rodado = rodados[familia_idx]
    familia = rodado['familia']
    cantidad = rodado['cantidad']
    productos_disponibles = rodado['productos']

    # Incluir productos ya seleccionados que no están en disponibles
    seleccionados_familia = set(
        cotizacion.items.filter(familia=familia).values_list('producto_id', flat=True),
    )
    ids_disp = {p.id for p in productos_disponibles}
    for sel_id in seleccionados_familia:
        if sel_id not in ids_disp:
            try:
                productos_disponibles.append(Producto.objects.get(id=sel_id))
            except Producto.DoesNotExist:
                pass

    precios = dict(
        PrecioProducto.objects.filter(
            lista=cotizacion.lista,
            producto_id__in=[p.id for p in productos_disponibles],
        ).values_list('producto_id', 'precio'),
    )

    # Determinar URL siguiente
    if familia_idx + 1 < len(rodados):
        continuar_url = f'/{cotizacion.id}/rodados/{familia_idx + 1}/'
    else:
        continuar_url = f'/{cotizacion.id}/bonificaciones/'

    ordenes_normales = _get_ordenes(cotizacion.implemento)

    context = {
        'cotizacion': cotizacion,
        'familia': familia,
        'cantidad': cantidad,
        'productos': [
            {
                'producto': p,
                'precio': precios.get(p.id, Decimal('0')),
                'seleccionado': p.id in seleccionados_familia,
            }
            for p in productos_disponibles
        ],
        'seleccionados': seleccionados_familia,
        'dimensiones': _build_dimensiones(acumulado, tenant),
        'familia_idx': familia_idx,
        'total_rodados': len(rodados),
        'continuar_url': continuar_url,
        'ordenes': ordenes_normales,
        'es_rodado': True,
        'falta_seleccion': familia.obligatoria == 'SI' and not seleccionados_familia and bool(productos_disponibles),
        'items_resumen': [
            {'item': item, 'puede_quitar': item.familia.obligatoria == 'NO'}
            for item in cotizacion.items.select_related('producto', 'familia').all()
        ],
    }

    return render(request, 'cotizaciones/paso_rodados.html', context)


@login_required
def seleccionar_rodado(request, cotizacion_id):
    """Seleccionar un producto de rodados."""
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)

    if request.method != 'POST':
        return HttpResponse(status=405)

    producto_id = request.POST.get('producto_id')
    familia_id = request.POST.get('familia_id')
    familia_idx = int(request.POST.get('familia_idx', 0))
    cantidad = int(request.POST.get('cantidad', 1))
    accion = request.POST.get('accion', 'add')

    producto = get_object_or_404(Producto, id=producto_id)
    familia = get_object_or_404(Familia, id=familia_id)

    if accion == 'remove':
        cotizacion.items.filter(producto=producto, familia=familia).delete()
    else:
        # Tipo O: reemplazar en la familia
        if familia.tipo_seleccion == 'O':
            cotizacion.items.filter(familia=familia).delete()

        precio = Decimal('0')
        try:
            pp = PrecioProducto.objects.get(lista=cotizacion.lista, producto=producto)
            precio = pp.precio
        except PrecioProducto.DoesNotExist:
            pass

        CotizacionItem.objects.create(
            cotizacion=cotizacion,
            producto=producto,
            familia=familia,
            cantidad=cantidad,
            precio_unitario=precio,
            precio_linea=precio * cantidad,
            iva_porcentaje=producto.iva_porcentaje,
        )

    return redirect('cotizacion_rodados', cotizacion_id=cotizacion.id, familia_idx=familia_idx)


# ── Bonificaciones ───────────────────────────────────────────────────


@login_required
def bonificaciones(request, cotizacion_id):
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)
    user = request.user

    formas_pago = FormaPago.objects.filter(tenant=tenant, activo=True)
    extra_por_barra = float(user.bonif_max_porcentaje) / 2

    # Defaults de bonificación
    cliente_default = float(cotizacion.cliente.bonificacion_porcentaje)
    forma_pago_actual = cotizacion.forma_pago
    pago_default = float(forma_pago_actual.bonificacion_porcentaje) if forma_pago_actual else 0

    # Max de cada barra = default + extra
    cliente_max = cliente_default + extra_por_barra
    pago_max = pago_default + extra_por_barra

    if request.method == 'POST':
        bonif_cliente_pct = Decimal(request.POST.get('bonif_cliente_pct', '0'))
        bonif_pago_pct = Decimal(request.POST.get('bonif_pago_pct', '0'))
        forma_pago_id = request.POST.get('forma_pago_id')
        fecha_entrega = request.POST.get('fecha_entrega')
        notas = request.POST.get('notas', '')

        if forma_pago_id:
            cotizacion.forma_pago_id = forma_pago_id
            # Recalcular pago_default con la forma de pago elegida
            fp = FormaPago.objects.filter(id=forma_pago_id).first()
            if fp:
                pago_default = float(fp.bonificacion_porcentaje)

        items_data = _get_items_data(cotizacion)
        totales = calcular_totales(
            items_data, bonif_cliente_pct, bonif_pago_pct,
            bonif_cliente_default=Decimal(str(cliente_default)),
            bonif_pago_default=Decimal(str(pago_default)),
            usuario_bonif_max=user.bonif_max_porcentaje,
            usuario_comision_pct=user.comision_porcentaje,
            comision_impacto_bonif=tenant.comision_impacto_bonif,
        )

        cotizacion.subtotal_bruto = totales['subtotal_bruto']
        cotizacion.bonif_cliente_pct = totales['bonif_cliente_pct']
        cotizacion.bonif_cliente_monto = totales['bonif_cliente_monto']
        cotizacion.bonif_pago_pct = totales['bonif_pago_pct']
        cotizacion.bonif_pago_monto = totales['bonif_pago_monto']
        cotizacion.subtotal_neto = totales['subtotal_neto']
        cotizacion.iva_105_base = totales['iva_105_base']
        cotizacion.iva_105_monto = totales['iva_105_monto']
        cotizacion.iva_21_base = totales['iva_21_base']
        cotizacion.iva_21_monto = totales['iva_21_monto']
        cotizacion.iva_total = totales['iva_total']
        cotizacion.precio_total = totales['precio_total']
        cotizacion.comision_porcentaje_efectivo = totales['comision_porcentaje_efectivo']
        cotizacion.comision_monto = totales['comision_monto']
        cotizacion.notas = notas

        if fecha_entrega:
            cotizacion.fecha_entrega = fecha_entrega

        cotizacion.save()
        return redirect('cotizacion_resumen', cotizacion_id=cotizacion.id)

    items_data = _get_items_data(cotizacion)
    subtotal_bruto = sum(Decimal(str(i['precio_linea'])) for i in items_data)

    # Puede ver comisión?
    puede_ver_comision = (
        tenant.mostrar_comisiones
        or user.rol in ('admin', 'dueno')
        or user.is_superuser
    )

    return render(request, 'cotizaciones/bonificaciones.html', {
        'cotizacion': cotizacion,
        'formas_pago': formas_pago,
        'bonif_cliente_max': str(cliente_max),
        'bonif_pago_max': str(pago_max),
        'bonif_cliente_init': str(cliente_default),
        'bonif_pago_init': str(pago_default),
        'extra_por_barra': str(extra_por_barra),
        'subtotal_bruto': subtotal_bruto,
        'forma_pago_nombre': forma_pago_actual.nombre if forma_pago_actual else '',
        'fecha_min': date.today().isoformat(),
        'puede_ver_comision': puede_ver_comision,
        'usuario_comision_pct': str(user.comision_porcentaje),
        'ordenes': _get_ordenes(cotizacion.implemento),
    })


@login_required
def calcular_preview(request, cotizacion_id):
    """HTMX endpoint para preview de totales en vivo."""
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)
    user = request.user

    bonif_cliente_pct = Decimal(request.GET.get('bonif_cliente_pct', '0'))
    bonif_pago_pct = Decimal(request.GET.get('bonif_pago_pct', '0'))
    forma_pago_id = request.GET.get('forma_pago_id', '')

    cliente_default = cotizacion.cliente.bonificacion_porcentaje
    pago_default = cotizacion.forma_pago.bonificacion_porcentaje
    forma_pago_nombre = cotizacion.forma_pago.nombre

    if forma_pago_id:
        fp = FormaPago.objects.filter(id=forma_pago_id, tenant=tenant).first()
        if fp:
            forma_pago_nombre = fp.nombre
            pago_default = fp.bonificacion_porcentaje

    items_data = _get_items_data(cotizacion)
    totales = calcular_totales(
        items_data, bonif_cliente_pct, bonif_pago_pct,
        bonif_cliente_default=cliente_default,
        bonif_pago_default=pago_default,
        usuario_bonif_max=user.bonif_max_porcentaje,
        usuario_comision_pct=user.comision_porcentaje,
        comision_impacto_bonif=tenant.comision_impacto_bonif,
    )

    puede_ver_comision = (
        tenant.mostrar_comisiones
        or user.rol in ('admin', 'dueno')
        or user.is_superuser
    )

    return render(request, 'cotizaciones/partials/totales_preview.html', {
        'totales': totales,
        'cotizacion': cotizacion,
        'forma_pago_nombre': forma_pago_nombre,
        'puede_ver_comision': puede_ver_comision,
    })


# ── Resumen ──────────────────────────────────────────────────────────


@login_required
def historial(request):
    tenant = _get_tenant(request)
    cotizaciones = Cotizacion.objects.filter(tenant=tenant).select_related(
        'cliente', 'implemento', 'vendedor',
    ).order_by('-created_at')

    # Vendedor ve solo las suyas (SPEC 2.3)
    if request.user.rol == 'vendedor':
        cotizaciones = cotizaciones.filter(vendedor=request.user)

    # Filtros
    estado = request.GET.get('estado', '')
    if estado:
        cotizaciones = cotizaciones.filter(estado=estado)
    implemento_id = request.GET.get('implemento', '')
    if implemento_id:
        cotizaciones = cotizaciones.filter(implemento_id=implemento_id)
    q = request.GET.get('q', '').strip()
    if q:
        cotizaciones = cotizaciones.filter(
            Q(numero__icontains=q) | Q(cliente__nombre__icontains=q) | Q(vendedor__nombre__icontains=q),
        )

    implementos = Implemento.objects.filter(tenant=tenant)

    return render(request, 'cotizaciones/historial.html', {
        'cotizaciones': cotizaciones[:50],
        'implementos': implementos,
        'filtro_estado': estado,
        'filtro_implemento': implemento_id,
        'filtro_q': q,
    })


@login_required
def resumen(request, cotizacion_id):
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)
    items = cotizacion.items.select_related('producto', 'familia').all()

    puede_ver_comision = (
        tenant.mostrar_comisiones
        or request.user.rol in ('admin', 'dueno')
        or request.user.is_superuser
    )

    user = request.user
    es_dueno_admin = user.rol in ('admin', 'dueno') or user.is_superuser
    pendiente_aprobacion = (
        cotizacion.estado == 'aprobada'
        and cotizacion.vendedor.requiere_validacion
        and not cotizacion.aprobada_por
    )

    return render(request, 'cotizaciones/resumen.html', {
        'cotizacion': cotizacion,
        'items': items,
        'puede_ver_comision': puede_ver_comision,
        'es_dueno_admin': es_dueno_admin,
        'pendiente_aprobacion': pendiente_aprobacion,
    })


# ── Aprobar ──────────────────────────────────────────────────────────


@login_required
def aprobar(request, cotizacion_id):
    """
    Aprobar cotización.
    - borrador → aprobada: cualquier usuario puede aprobar su cotización
    - aprobada (pendiente) → aprobada (visto bueno): Dueño/Admin da su OK
      cuando vendedor.requiere_validacion=true
    """
    from django.utils import timezone
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)
    user = request.user

    if request.method == 'POST':
        if cotizacion.estado == 'borrador':
            cotizacion.estado = 'aprobada'
            # Si no requiere validacion o es dueno/admin, aprobar directamente
            if not cotizacion.vendedor.requiere_validacion or user.rol in ('admin', 'dueno') or user.is_superuser:
                cotizacion.aprobada_por = user
                cotizacion.aprobada_at = timezone.now()
            cotizacion.save()
            if cotizacion.aprobada_por:
                messages.success(request, f'Cotizacion {cotizacion.numero} aprobada.')
            else:
                messages.info(request, f'Cotizacion {cotizacion.numero} enviada. Pendiente de aprobacion del Dueno.')

        elif cotizacion.estado == 'aprobada' and not cotizacion.aprobada_por:
            # Dueño da visto bueno a cotización pendiente
            if user.rol in ('admin', 'dueno') or user.is_superuser:
                cotizacion.aprobada_por = user
                cotizacion.aprobada_at = timezone.now()
                cotizacion.save()
                messages.success(request, f'Cotizacion {cotizacion.numero} aprobada por {user.nombre}.')

    return redirect('cotizacion_resumen', cotizacion_id=cotizacion.id)


@login_required
def confirmar(request, cotizacion_id):
    """Confirmar cotización (aprobada → confirmada). La venta se concretó."""
    from django.utils import timezone
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)

    if request.method == 'POST' and cotizacion.estado == 'aprobada' and cotizacion.aprobada_por:
        cotizacion.estado = 'confirmada'
        cotizacion.confirmada_por = request.user
        cotizacion.confirmada_at = timezone.now()
        cotizacion.save()
        messages.success(request, f'Cotizacion {cotizacion.numero} confirmada.')

    return redirect('cotizacion_resumen', cotizacion_id=cotizacion.id)


@login_required
def descargar_pdf(request, cotizacion_id):
    from django.template.loader import render_to_string
    from apps.precios.views import _generate_pdf
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)
    items = cotizacion.items.select_related('producto', 'familia').all()

    from apps.precios.views import _get_logo_url
    html = render_to_string('pdf/cotizacion.html', {
        'cotizacion': cotizacion,
        'items': items,
        'tenant': tenant,
        'logo_url': _get_logo_url(tenant),
    })

    pdf_bytes = _generate_pdf(html)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{cotizacion.numero}.pdf"'
    return response
