from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
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


def _get_tenant():
    return Tenant.objects.filter(activo=True).first()


def _get_logo_url(tenant):
    """Retorna path absoluto del logo para WeasyPrint, o None."""
    if tenant and tenant.logo:
        import os
        path = tenant.logo.path
        if os.path.exists(path):
            return path
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
    tenant = _get_tenant()
    listas = ListaPrecio.objects.filter(tenant=tenant).order_by('-numero')
    vigente = listas.filter(estado='vigente').first()
    return render(request, 'precios/panel_listas.html', {
        'listas': listas,
        'vigente': vigente,
    })


@login_required
def crear_lista(request):
    tenant = _get_tenant()
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
    tenant = _get_tenant()
    lista = get_object_or_404(ListaPrecio, id=lista_id, tenant=tenant)
    precios = PrecioProducto.objects.filter(lista=lista).select_related('producto').order_by('producto__nombre')
    q = request.GET.get('q', '').strip()
    if q:
        precios = precios.filter(producto__nombre__icontains=q)

    return render(request, 'precios/editar_lista.html', {
        'lista': lista,
        'precios': precios,
        'q': q,
    })


@login_required
def editar_precio(request, precio_id):
    tenant = _get_tenant()
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
def activar_lista_view(request, lista_id):
    tenant = _get_tenant()
    lista = get_object_or_404(ListaPrecio, id=lista_id, tenant=tenant)

    if request.method == 'POST' and lista.estado in ('borrador', 'historica'):
        activar_lista(lista)
        messages.success(request, f'Lista #{lista.numero} activada como vigente.')

    return redirect('panel_listas')


# ── PDF Cotización ───────────────────────────────────────────────────


@login_required
def generar_pdf_cotizacion(request, cotizacion_id):
    from apps.cotizaciones.models import Cotizacion
    tenant = _get_tenant()
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
def generar_pdf_prearmados(request):
    tenant = _get_tenant()
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
