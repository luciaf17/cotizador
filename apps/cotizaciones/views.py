from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalogo.models import Familia, Implemento, Producto
from apps.clientes.models import Cliente, FormaPago, TipoCliente
from apps.precios.models import ListaPrecio, PrecioProducto
from apps.tenants.models import Tenant

from .models import Cotizacion, CotizacionDimension, CotizacionItem
from .services import (
    calcular_dimensiones,
    calcular_totales,
    get_productos_disponibles,
    get_rodados_para_implemento,
)


def _get_tenant():
    """Obtener tenant por defecto (hasta implementar middleware)."""
    return Tenant.objects.filter(activo=True).first()


def _get_ordenes(implemento):
    """Obtener lista ordenada de órdenes únicos para un implemento."""
    return (
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


# ── Inicio: selección de cliente ─────────────────────────────────────


@login_required
def inicio(request):
    tenant = _get_tenant()
    tipos_cliente = TipoCliente.objects.filter(tenant=tenant) if tenant else []
    return render(request, 'cotizaciones/inicio.html', {
        'tipos_cliente': tipos_cliente,
    })


@login_required
def buscar_clientes(request):
    tenant = _get_tenant()
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
    tenant = _get_tenant()
    if request.method == 'POST':
        tipo_id = request.POST.get('tipo_cliente')
        nombre = request.POST.get('nombre', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        direccion = request.POST.get('direccion', '').strip()

        if not nombre or not tipo_id:
            return HttpResponse(
                '<div class="text-red-600 text-sm">Nombre y tipo son obligatorios.</div>',
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
    tenant = _get_tenant()
    cliente = get_object_or_404(Cliente, id=cliente_id, tenant=tenant)
    implementos = Implemento.objects.filter(tenant=tenant)
    return render(request, 'cotizaciones/implementos.html', {
        'cliente': cliente,
        'implementos': implementos,
    })


# ── Crear cotización y empezar flujo ─────────────────────────────────


@login_required
def cotizacion_nueva(request, cliente_id, implemento_id):
    tenant = _get_tenant()
    cliente = get_object_or_404(Cliente, id=cliente_id, tenant=tenant)
    implemento = get_object_or_404(Implemento, id=implemento_id, tenant=tenant)
    lista = ListaPrecio.objects.filter(tenant=tenant, estado='vigente').first()

    if not lista:
        messages.error(request, 'No hay lista de precios vigente.')
        return redirect('seleccionar_implemento', cliente_id=cliente_id)

    # Buscar forma de pago por defecto
    forma_pago = FormaPago.objects.filter(tenant=tenant, activo=True).first()
    if not forma_pago:
        messages.error(request, 'No hay formas de pago configuradas.')
        return redirect('seleccionar_implemento', cliente_id=cliente_id)

    # Generar número
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

    ordenes = _get_ordenes(implemento)
    if ordenes:
        return redirect('cotizacion_paso', cotizacion_id=cotizacion.id, orden=ordenes[0])

    return redirect('cotizacion_bonificaciones', cotizacion_id=cotizacion.id)


# ── Paso step-by-step ────────────────────────────────────────────────


@login_required
def paso(request, cotizacion_id, orden):
    tenant = _get_tenant()
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)
    implemento = cotizacion.implemento

    ordenes = list(_get_ordenes(implemento))
    current_idx = ordenes.index(orden) if orden in ordenes else 0

    seleccionados_ids = _get_selected_ids(cotizacion)
    acumulado = calcular_dimensiones(seleccionados_ids)

    # Familias del orden actual
    familias = Familia.objects.filter(implemento=implemento, orden=orden)

    # Productos disponibles agrupados por familia
    familias_data = []
    for familia in familias:
        productos = get_productos_disponibles(
            implemento.id, orden, seleccionados_ids, acumulado,
        )
        # Filtrar solo los de esta familia
        productos_familia = [p for p in productos if p.familia_id == familia.id]

        # Obtener precios
        precios = dict(
            PrecioProducto.objects.filter(
                lista=cotizacion.lista,
                producto_id__in=[p.id for p in productos_familia],
            ).values_list('producto_id', 'precio'),
        )

        # Items ya seleccionados de esta familia
        seleccionados_familia = set(
            cotizacion.items.filter(familia=familia).values_list('producto_id', flat=True),
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

    # Dimensiones acumuladas para mostrar
    dimensiones = []
    if acumulado:
        from apps.catalogo.models import Propiedad
        for prop in Propiedad.objects.filter(tenant=tenant):
            if prop.id in acumulado:
                dimensiones.append({
                    'nombre': prop.nombre,
                    'valor': acumulado[prop.id],
                    'unidad': prop.unidad,
                })

    # Nav info
    has_prev = current_idx > 0
    prev_orden = ordenes[current_idx - 1] if has_prev else None

    context = {
        'cotizacion': cotizacion,
        'orden': orden,
        'ordenes': ordenes,
        'current_idx': current_idx,
        'familias_data': familias_data,
        'dimensiones': dimensiones,
        'has_prev': has_prev,
        'prev_orden': prev_orden,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'cotizaciones/partials/paso_content.html', context)

    return render(request, 'cotizaciones/paso.html', context)


@login_required
def seleccionar_producto(request, cotizacion_id):
    tenant = _get_tenant()
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
        # Tipo O: reemplazar selección de la misma familia
        if familia.tipo_seleccion == 'O':
            cotizacion.items.filter(familia=familia).delete()

        # Obtener precio
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

    # Determinar siguiente paso
    ordenes = list(_get_ordenes(cotizacion.implemento))
    siguiente_url = None

    if familia.tipo_seleccion == 'O':
        # Tipo O: avanza automáticamente
        current_idx = ordenes.index(orden) if orden in ordenes else 0
        if current_idx + 1 < len(ordenes):
            siguiente_orden = ordenes[current_idx + 1]
            siguiente_url = f'/cotizaciones/{cotizacion.id}/paso/{siguiente_orden}/'
        else:
            # Verificar rodados
            rodados = get_rodados_para_implemento(
                cotizacion.implemento,
                _get_selected_ids(cotizacion),
            )
            if rodados:
                siguiente_url = f'/cotizaciones/{cotizacion.id}/paso/{orden}/'  # reload for rodados
            else:
                siguiente_url = f'/cotizaciones/{cotizacion.id}/bonificaciones/'

    if siguiente_url:
        return HttpResponse(status=200, headers={'HX-Redirect': siguiente_url})

    # Tipo Y: recargar el mismo paso
    return paso(request, cotizacion_id, orden)


# ── Avanzar al siguiente paso (tipo Y) ──────────────────────────────


def _avanzar_paso(request, cotizacion, orden):
    ordenes = list(_get_ordenes(cotizacion.implemento))
    current_idx = ordenes.index(orden) if orden in ordenes else 0

    if current_idx + 1 < len(ordenes):
        return redirect('cotizacion_paso', cotizacion_id=cotizacion.id, orden=ordenes[current_idx + 1])

    # Verificar si hay rodados
    seleccionados = _get_selected_ids(cotizacion)
    rodados = get_rodados_para_implemento(cotizacion.implemento, seleccionados)
    if rodados:
        # TODO: paso de rodados
        pass

    return redirect('cotizacion_bonificaciones', cotizacion_id=cotizacion.id)


# ── Bonificaciones ───────────────────────────────────────────────────


@login_required
def bonificaciones(request, cotizacion_id):
    tenant = _get_tenant()
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)

    formas_pago = FormaPago.objects.filter(tenant=tenant, activo=True)
    bonif_max = tenant.bonif_max_porcentaje if tenant else Decimal('30')

    if request.method == 'POST':
        bonif_cliente_pct = Decimal(request.POST.get('bonif_cliente_pct', '0'))
        bonif_pago_pct = Decimal(request.POST.get('bonif_pago_pct', '0'))
        forma_pago_id = request.POST.get('forma_pago_id')
        fecha_entrega = request.POST.get('fecha_entrega')
        notas = request.POST.get('notas', '')

        if forma_pago_id:
            cotizacion.forma_pago_id = forma_pago_id

        # Calcular totales
        items_data = _get_items_data(cotizacion)
        totales = calcular_totales(
            items_data, bonif_cliente_pct, bonif_pago_pct, bonif_max,
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
        cotizacion.notas = notas

        if fecha_entrega:
            cotizacion.fecha_entrega = fecha_entrega

        cotizacion.save()
        return redirect('cotizacion_resumen', cotizacion_id=cotizacion.id)

    # GET: mostrar form
    items_data = _get_items_data(cotizacion)
    subtotal_bruto = sum(Decimal(str(i['precio_linea'])) for i in items_data)

    return render(request, 'cotizaciones/bonificaciones.html', {
        'cotizacion': cotizacion,
        'formas_pago': formas_pago,
        'bonif_max': bonif_max,
        'subtotal_bruto': subtotal_bruto,
        'bonif_cliente_default': cotizacion.cliente.bonificacion_porcentaje,
    })


@login_required
def calcular_preview(request, cotizacion_id):
    """HTMX endpoint para preview de totales en vivo."""
    tenant = _get_tenant()
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)

    bonif_cliente_pct = Decimal(request.GET.get('bonif_cliente_pct', '0'))
    bonif_pago_pct = Decimal(request.GET.get('bonif_pago_pct', '0'))
    bonif_max = tenant.bonif_max_porcentaje if tenant else Decimal('30')

    items_data = _get_items_data(cotizacion)
    totales = calcular_totales(items_data, bonif_cliente_pct, bonif_pago_pct, bonif_max)

    return render(request, 'cotizaciones/partials/totales_preview.html', {
        'totales': totales,
    })


# ── Resumen ──────────────────────────────────────────────────────────


@login_required
def resumen(request, cotizacion_id):
    tenant = _get_tenant()
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)
    items = cotizacion.items.select_related('producto', 'familia').all()

    return render(request, 'cotizaciones/resumen.html', {
        'cotizacion': cotizacion,
        'items': items,
    })


# ── Aprobar ──────────────────────────────────────────────────────────


@login_required
def aprobar(request, cotizacion_id):
    tenant = _get_tenant()
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)

    if request.method == 'POST':
        cotizacion.estado = 'aprobada'
        cotizacion.save()
        messages.success(request, f'Cotización {cotizacion.numero} aprobada.')
        return redirect('cotizacion_resumen', cotizacion_id=cotizacion.id)

    return redirect('cotizacion_resumen', cotizacion_id=cotizacion.id)
