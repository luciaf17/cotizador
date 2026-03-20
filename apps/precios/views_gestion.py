"""CRUD de prearmados para el panel de gestión."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import rol_requerido
from apps.catalogo.models import Implemento, Producto
from apps.tenants.models import Tenant

from .models import EstructuraPrearmado, ListaPrecio, Prearmado, PrecioProducto
from .services import calcular_precio_prearmado


def _get_tenant(request):
    if hasattr(request, 'tenant') and request.tenant:
        return request.tenant
    return Tenant.objects.filter(activo=True).first()


@login_required
@rol_requerido('admin', 'dueno')
def prearmados_lista(request):
    tenant = _get_tenant(request)
    imp_id = request.GET.get('implemento', '')
    implementos = Implemento.objects.filter(tenant=tenant).order_by('nombre')
    prearmados = Prearmado.objects.filter(tenant=tenant).select_related('implemento').order_by('implemento__nombre', 'nombre')
    if imp_id:
        prearmados = prearmados.filter(implemento_id=imp_id)

    lista = ListaPrecio.objects.filter(tenant=tenant, estado='vigente').first()

    data = []
    for pre in prearmados:
        precio_calc = calcular_precio_prearmado(pre, lista) if lista else Decimal('0')
        dif = precio_calc - (pre.precio_referencia or 0) if pre.precio_referencia else None
        data.append({
            'pre': pre,
            'precio_calculado': precio_calc,
            'diferencia': dif,
            'estructura_count': pre.estructura.count(),
        })

    return render(request, 'gestion/prearmados/lista.html', {
        'prearmados': data,
        'implementos': implementos,
        'filtro_implemento': imp_id,
        'lista': lista,
    })


@login_required
@rol_requerido('admin', 'dueno')
def prearmado_form(request, pre_id=None):
    tenant = _get_tenant(request)
    prearmado = get_object_or_404(Prearmado, id=pre_id, tenant=tenant) if pre_id else None
    implementos = Implemento.objects.filter(tenant=tenant).order_by('nombre')
    productos = Producto.objects.filter(tenant=tenant).order_by('implemento__nombre', 'nombre')
    lista = ListaPrecio.objects.filter(tenant=tenant, estado='vigente').first()

    # Cargar estructura desde prearmado existente o desde base
    fuente = prearmado
    if not fuente and not pre_id:
        base_id = request.GET.get('base', '')
        if base_id:
            fuente = Prearmado.objects.filter(id=base_id, tenant=tenant).first()

    estructura = []
    if fuente:
        for est in EstructuraPrearmado.objects.filter(prearmado=fuente).select_related('producto'):
            precio = Decimal('0')
            if lista:
                try:
                    precio = PrecioProducto.objects.get(lista=lista, producto=est.producto).precio
                except PrecioProducto.DoesNotExist:
                    pass
            estructura.append({
                'est': est,
                'precio_unitario': precio,
                'precio_linea': precio * est.cantidad,
            })

    prearmados_existentes = Prearmado.objects.filter(tenant=tenant).order_by('nombre') if not pre_id else []

    precio_calculado = sum(e['precio_linea'] for e in estructura)

    if request.method == 'POST':
        implemento_id = request.POST.get('implemento')
        nombre = request.POST.get('nombre', '').strip()
        precio_ref = request.POST.get('precio_referencia', '').strip()
        precio_ref = Decimal(precio_ref) if precio_ref else None

        imp = get_object_or_404(Implemento, id=implemento_id, tenant=tenant)

        if prearmado:
            prearmado.implemento = imp
            prearmado.nombre = nombre
            prearmado.precio_referencia = precio_ref
            prearmado.save()
        else:
            prearmado = Prearmado.objects.create(
                tenant=tenant, implemento=imp, nombre=nombre,
                precio_referencia=precio_ref,
            )

        # Guardar estructura
        EstructuraPrearmado.objects.filter(prearmado=prearmado).delete()
        prod_ids = request.POST.getlist('prod_id')
        cantidades = request.POST.getlist('prod_cantidad')
        for pid, cant in zip(prod_ids, cantidades):
            if pid and cant:
                try:
                    EstructuraPrearmado.objects.create(
                        prearmado=prearmado,
                        producto_id=int(pid),
                        cantidad=int(cant),
                    )
                except (ValueError, Producto.DoesNotExist):
                    pass

        messages.success(request, f'Prearmado "{nombre}" guardado.')
        return redirect('gestion_prearmados')

    # Mapa de precios para JS (producto_id → precio)
    precios_map = []
    if lista:
        precios_map = list(PrecioProducto.objects.filter(lista=lista).values('producto_id', 'precio'))

    return render(request, 'gestion/prearmados/form.html', {
        'prearmado': prearmado,
        'implementos': implementos,
        'productos': productos,
        'estructura': estructura,
        'precio_calculado': precio_calculado,
        'precios_map': precios_map,
        'prearmados_existentes': prearmados_existentes,
    })
