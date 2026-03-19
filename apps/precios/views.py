from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from apps.accounts.decorators import rol_requerido
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from apps.catalogo.models import Producto
from apps.precios.models import (
    EstructuraPrearmado,
    ListaPrecio,
    Prearmado,
    PrecioProducto,
)
from apps.tenants.models import Tenant

from .services import activar_lista, calcular_precio_prearmado, crear_nueva_lista


def _get_tenant(request=None):
    if request and hasattr(request, 'tenant') and request.tenant:
        return request.tenant
    return Tenant.objects.filter(activo=True).first()


def _get_logo_url(tenant):
    """Retorna data URI PNG base64 del logo para WeasyPrint, o None."""
    if tenant and tenant.logo:
        import os
        if not os.path.exists(tenant.logo.path):
            return None
        import base64
        import io
        from PIL import Image
        img = Image.open(tenant.logo.path)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        return f'data:image/png;base64,{b64}'
    return None


def _generate_pdf(html_string, base_url=None):
    """Genera PDF desde HTML string con WeasyPrint."""
    from weasyprint import HTML
    from django.conf import settings
    burl = base_url or str(settings.BASE_DIR)
    return HTML(string=html_string, base_url=burl).write_pdf()


# ── Listas de precios ────────────────────────────────────────────────


@login_required
def panel_listas(request):
    tenant = _get_tenant(request)
    listas = ListaPrecio.objects.filter(tenant=tenant).order_by('-numero')
    vigente = listas.filter(estado='vigente').first()
    return render(request, 'precios/panel_listas.html', {
        'listas': listas,
        'vigente': vigente,
    })


@login_required
@rol_requerido("admin", "dueno")
def crear_lista(request):
    tenant = _get_tenant(request)
    vigente = ListaPrecio.objects.filter(tenant=tenant, estado='vigente').first()

    if not vigente:
        messages.error(request, 'No hay lista vigente para usar como base.')
        return redirect('panel_listas')

    if request.method == 'POST':
        ajuste_pct = Decimal(request.POST.get('ajuste_pct', '0'))
        nombre = request.POST.get('nombre', '').strip()
        nueva = crear_nueva_lista(tenant, vigente, ajuste_pct, request.user, nombre or None)
        messages.success(request, f'Lista #{nueva.numero} creada en borrador.')
        return redirect('editar_lista', lista_id=nueva.id)

    return render(request, 'precios/crear_lista.html', {
        'vigente': vigente,
    })


@login_required
def editar_lista(request, lista_id):
    tenant = _get_tenant(request)
    lista = get_object_or_404(ListaPrecio, id=lista_id, tenant=tenant)
    precios_qs = PrecioProducto.objects.filter(lista=lista).select_related('producto').order_by('producto__nombre')
    q = request.GET.get('q', '').strip()
    if q:
        precios_qs = precios_qs.filter(producto__nombre__icontains=q)

    # Precios vigentes para comparar
    vigente = ListaPrecio.objects.filter(tenant=tenant, estado='vigente').first()
    precios_vigentes = {}
    if vigente and vigente.id != lista.id:
        precios_vigentes = dict(
            PrecioProducto.objects.filter(lista=vigente).values_list('producto_id', 'precio')
        )

    # Precios ajustados originales (recalcular desde base si existe)
    import math
    precios_ajustados = {}
    if lista.lista_base and lista.ajuste_pct is not None:
        factor = 1 + float(lista.ajuste_pct) / 100
        for pp_base in PrecioProducto.objects.filter(lista=lista.lista_base):
            precios_ajustados[pp_base.producto_id] = Decimal(str(math.ceil(float(pp_base.precio * Decimal(str(factor))))))

    # Armar datos para el template
    precios_data = []
    for pp in precios_qs:
        precio_vigente = precios_vigentes.get(pp.producto_id, Decimal('0'))
        precio_ajustado = precios_ajustados.get(pp.producto_id, pp.precio)
        fue_editado = pp.precio != precio_ajustado and pp.editado_por is not None
        if precio_vigente > 0:
            dif_monto = pp.precio - precio_vigente
            dif_pct = ((pp.precio - precio_vigente) / precio_vigente * 100).quantize(Decimal('0.1'))
        else:
            dif_monto = Decimal('0')
            dif_pct = Decimal('0')
        precios_data.append({
            'pp': pp,
            'precio_vigente': precio_vigente,
            'precio_ajustado': precio_ajustado,
            'fue_editado': fue_editado,
            'dif_monto': dif_monto,
            'dif_pct': dif_pct,
        })

    return render(request, 'precios/editar_lista.html', {
        'lista': lista,
        'precios_data': precios_data,
        'q': q,
    })


@login_required
@rol_requerido("admin", "dueno")
def editar_precio(request, precio_id):
    tenant = _get_tenant(request)
    pp = get_object_or_404(PrecioProducto, id=precio_id, lista__tenant=tenant)

    if request.method == 'POST' and pp.lista.estado == 'borrador':
        nuevo_precio = request.POST.get('precio', '').strip()
        try:
            pp.precio = Decimal(nuevo_precio)
            pp.editado_por = request.user
            pp.save()
        except Exception:
            pass
        return redirect('editar_lista', lista_id=pp.lista.id)

    return redirect('editar_lista', lista_id=pp.lista.id)


@login_required
@rol_requerido("admin", "dueno")
def activar_lista_view(request, lista_id):
    tenant = _get_tenant(request)
    lista = get_object_or_404(ListaPrecio, id=lista_id, tenant=tenant)

    if request.method == 'POST' and lista.estado in ('borrador', 'historica'):
        activar_lista(lista)
        messages.success(request, f'Lista #{lista.numero} activada como vigente.')

    return redirect('panel_listas')


# ── PDF Cotización ───────────────────────────────────────────────────


@login_required
def generar_pdf_cotizacion(request, cotizacion_id):
    from apps.cotizaciones.models import Cotizacion
    tenant = _get_tenant(request)
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id, tenant=tenant)
    items = cotizacion.items.select_related('producto', 'familia').all()

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


# ── PDF Prearmados ───────────────────────────────────────────────────


@login_required
@rol_requerido("admin", "dueno")
def generar_pdf_prearmados(request):
    tenant = _get_tenant(request)
    lista = ListaPrecio.objects.filter(tenant=tenant, estado='vigente').first()

    if not lista:
        messages.error(request, 'No hay lista vigente.')
        return redirect('panel_listas')

    prearmados = Prearmado.objects.filter(tenant=tenant).select_related('implemento').order_by('implemento__nombre', 'nombre')
    for pre in prearmados:
        pre.precio_calculado = calcular_precio_prearmado(pre, lista)

    html = render_to_string('pdf/prearmados.html', {
        'prearmados': prearmados,
        'lista': lista,
        'tenant': tenant,
        'fecha': date.today(),
        'logo_url': _get_logo_url(tenant),
    })

    pdf_bytes = _generate_pdf(html)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="prearmados-lista-{lista.numero}.pdf"'
    return response
