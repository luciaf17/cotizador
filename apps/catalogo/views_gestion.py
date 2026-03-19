"""CRUD de catálogo para el panel de gestión del Dueño."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import rol_requerido
from apps.tenants.models import Tenant

from .models import (
    Compatibilidad,
    Familia,
    Implemento,
    Producto,
    ProductoPropiedad,
    Propiedad,
)


def _get_tenant(request):
    if hasattr(request, 'tenant') and request.tenant:
        return request.tenant
    return Tenant.objects.filter(activo=True).first()


# ── Implementos ──────────────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def implementos_lista(request):
    tenant = _get_tenant(request)
    implementos = Implemento.objects.filter(tenant=tenant).order_by('nombre')
    data = []
    for imp in implementos:
        data.append({
            'imp': imp,
            'familias': imp.familias.count(),
            'productos': imp.productos.count(),
        })
    return render(request, 'gestion/catalogo/implementos.html', {'implementos': data})


@login_required
@rol_requerido('admin', 'dueno')
def implemento_form(request, imp_id=None):
    tenant = _get_tenant(request)
    implemento = get_object_or_404(Implemento, id=imp_id, tenant=tenant) if imp_id else None

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        accesorios_tipo = request.POST.get('accesorios_tipo', '').strip() or None
        nivel_rodado = request.POST.get('nivel_rodado', '').strip()
        nivel_rodado = int(nivel_rodado) if nivel_rodado else None

        if implemento:
            implemento.nombre = nombre
            implemento.accesorios_tipo = accesorios_tipo
            implemento.nivel_rodado = nivel_rodado
            implemento.save()
        else:
            implemento = Implemento.objects.create(
                tenant=tenant, nombre=nombre,
                accesorios_tipo=accesorios_tipo, nivel_rodado=nivel_rodado,
            )
        messages.success(request, f'Implemento "{nombre}" guardado.')
        return redirect('gestion_implementos')

    return render(request, 'gestion/catalogo/implemento_form.html', {
        'implemento': implemento,
    })


# ── Familias ─────────────────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def familias_lista(request):
    tenant = _get_tenant(request)
    imp_id = request.GET.get('implemento', '')
    implementos = Implemento.objects.filter(tenant=tenant).order_by('nombre')
    familias = Familia.objects.filter(tenant=tenant).select_related('implemento').order_by('implemento__nombre', 'orden')
    if imp_id:
        familias = familias.filter(implemento_id=imp_id)
    return render(request, 'gestion/catalogo/familias.html', {
        'familias': familias,
        'implementos': implementos,
        'filtro_implemento': imp_id,
    })


@login_required
@rol_requerido('admin', 'dueno')
def familia_form(request, fam_id=None):
    tenant = _get_tenant(request)
    familia = get_object_or_404(Familia, id=fam_id, tenant=tenant) if fam_id else None
    implementos = Implemento.objects.filter(tenant=tenant).order_by('nombre')

    # Árbol de familias del implemento seleccionado
    arbol = []
    imp_id = request.GET.get('implemento') or (familia.implemento_id if familia else None)
    if imp_id:
        arbol = Familia.objects.filter(implemento_id=imp_id).order_by('orden')

    if request.method == 'POST':
        implemento_id = request.POST.get('implemento')
        nombre = request.POST.get('nombre', '').strip()
        orden = int(request.POST.get('orden', 1))
        tipo_seleccion = request.POST.get('tipo_seleccion', 'O')
        obligatoria = request.POST.get('obligatoria', 'SI')

        # Si el orden ya existe, heredar tipo_seleccion y obligatoria
        existente = Familia.objects.filter(implemento_id=implemento_id, orden=orden).exclude(
            id=fam_id if fam_id else 0,
        ).first()
        if existente:
            tipo_seleccion = existente.tipo_seleccion
            obligatoria = existente.obligatoria

        implemento = get_object_or_404(Implemento, id=implemento_id, tenant=tenant)

        if familia:
            familia.implemento = implemento
            familia.nombre = nombre
            familia.orden = orden
            familia.tipo_seleccion = tipo_seleccion
            familia.obligatoria = obligatoria
            familia.save()
        else:
            Familia.objects.create(
                tenant=tenant, implemento=implemento, nombre=nombre,
                orden=orden, tipo_seleccion=tipo_seleccion, obligatoria=obligatoria,
            )
        messages.success(request, f'Familia "{nombre}" guardada.')
        return redirect('gestion_familias')

    return render(request, 'gestion/catalogo/familia_form.html', {
        'familia': familia,
        'implementos': implementos,
        'arbol': arbol,
        'imp_id': imp_id,
    })


# ── Productos ────────────────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def productos_lista(request):
    tenant = _get_tenant(request)
    q = request.GET.get('q', '').strip()
    imp_id = request.GET.get('implemento', '')
    implementos = Implemento.objects.filter(tenant=tenant).order_by('nombre')
    productos = Producto.objects.filter(tenant=tenant).select_related('implemento', 'familia').order_by('implemento__nombre', 'familia__orden', 'nombre')
    if q:
        productos = productos.filter(nombre__icontains=q)
    if imp_id:
        productos = productos.filter(implemento_id=imp_id)
    return render(request, 'gestion/catalogo/productos.html', {
        'productos': productos[:100],
        'implementos': implementos,
        'filtro_q': q,
        'filtro_implemento': imp_id,
    })


@login_required
@rol_requerido('admin', 'dueno')
def producto_form(request, prod_id=None):
    tenant = _get_tenant(request)
    producto = get_object_or_404(Producto, id=prod_id, tenant=tenant) if prod_id else None
    implementos = Implemento.objects.filter(tenant=tenant).order_by('nombre')
    familias = Familia.objects.filter(tenant=tenant).order_by('implemento__nombre', 'orden')
    propiedades = Propiedad.objects.filter(tenant=tenant).order_by('nombre')

    prod_props = []
    if producto:
        prod_props = ProductoPropiedad.objects.filter(producto=producto).select_related('propiedad')

    if request.method == 'POST':
        implemento_id = request.POST.get('implemento')
        familia_id = request.POST.get('familia')
        nombre = request.POST.get('nombre', '').strip()
        cod_comercio = request.POST.get('cod_comercio', '').strip() or None
        plano = request.POST.get('plano', '').strip() or None
        cod_factura = request.POST.get('cod_factura', '').strip() or None
        orden = int(request.POST.get('orden', 0))
        iva_porcentaje = Decimal(request.POST.get('iva_porcentaje', '21'))
        link_web = request.POST.get('link_web', '').strip() or None

        imp = get_object_or_404(Implemento, id=implemento_id, tenant=tenant)
        fam = get_object_or_404(Familia, id=familia_id, tenant=tenant)

        if producto:
            producto.implemento = imp
            producto.familia = fam
            producto.nombre = nombre
            producto.cod_comercio = cod_comercio
            producto.plano = plano
            producto.cod_factura = cod_factura
            producto.orden = orden
            producto.iva_porcentaje = iva_porcentaje
            producto.link_web = link_web
            producto.save()
        else:
            producto = Producto.objects.create(
                tenant=tenant, implemento=imp, familia=fam,
                nombre=nombre, cod_comercio=cod_comercio, plano=plano,
                cod_factura=cod_factura, orden=orden,
                iva_porcentaje=iva_porcentaje, link_web=link_web,
            )

        # Guardar propiedades inline
        ProductoPropiedad.objects.filter(producto=producto).delete()
        prop_ids = request.POST.getlist('prop_id')
        prop_tipos = request.POST.getlist('prop_tipo')
        prop_valores = request.POST.getlist('prop_valor')
        for pid, ptipo, pval in zip(prop_ids, prop_tipos, prop_valores):
            if pid and pval:
                ProductoPropiedad.objects.create(
                    producto=producto,
                    propiedad_id=int(pid),
                    tipo=ptipo,
                    valor=Decimal(pval),
                )

        messages.success(request, f'Producto "{nombre}" guardado.')
        return redirect('gestion_productos')

    return render(request, 'gestion/catalogo/producto_form.html', {
        'producto': producto,
        'implementos': implementos,
        'familias': familias,
        'propiedades': propiedades,
        'prod_props': prod_props,
    })


# ── Propiedades ──────────────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def propiedades_lista(request):
    tenant = _get_tenant(request)
    propiedades = Propiedad.objects.filter(tenant=tenant).order_by('nombre')
    return render(request, 'gestion/catalogo/propiedades.html', {'propiedades': propiedades})


@login_required
@rol_requerido('admin', 'dueno')
def propiedad_guardar(request):
    tenant = _get_tenant(request)
    if request.method == 'POST':
        prop_id = request.POST.get('prop_id')
        nombre = request.POST.get('nombre', '').strip()
        unidad = request.POST.get('unidad', '').strip()
        agregacion = request.POST.get('agregacion', 'SUM')

        if prop_id:
            prop = get_object_or_404(Propiedad, id=prop_id, tenant=tenant)
            prop.nombre = nombre
            prop.unidad = unidad
            prop.agregacion = agregacion
            prop.save()
        else:
            Propiedad.objects.create(tenant=tenant, nombre=nombre, unidad=unidad, agregacion=agregacion)

        messages.success(request, f'Propiedad "{nombre}" guardada.')
    return redirect('gestion_propiedades')


# ── Compatibilidades ────────────────────────────────────────────────


@login_required
@rol_requerido('admin', 'dueno')
def compatibilidades_lista(request):
    tenant = _get_tenant(request)
    imp_id = request.GET.get('implemento', '')
    implementos = Implemento.objects.filter(tenant=tenant).order_by('nombre')
    compats = Compatibilidad.objects.filter(tenant=tenant).select_related(
        'producto_padre', 'producto_hijo',
    ).order_by('producto_padre__nombre')
    if imp_id:
        compats = compats.filter(producto_padre__implemento_id=imp_id)
    return render(request, 'gestion/catalogo/compatibilidades.html', {
        'compats': compats,
        'implementos': implementos,
        'filtro_implemento': imp_id,
    })


@login_required
@rol_requerido('admin', 'dueno')
def compatibilidad_form(request, comp_id=None):
    tenant = _get_tenant(request)
    compat = get_object_or_404(Compatibilidad, id=comp_id, tenant=tenant) if comp_id else None
    productos = Producto.objects.filter(tenant=tenant).order_by('implemento__nombre', 'nombre')

    if request.method == 'POST':
        padre_id = request.POST.get('producto_padre')
        hijo_id = request.POST.get('producto_hijo')
        tipo = request.POST.get('tipo', 'Vetado')

        padre = get_object_or_404(Producto, id=padre_id, tenant=tenant)
        hijo = get_object_or_404(Producto, id=hijo_id, tenant=tenant)

        if compat:
            compat.producto_padre = padre
            compat.producto_hijo = hijo
            compat.tipo = tipo
            compat.save()
        else:
            Compatibilidad.objects.create(
                tenant=tenant, producto_padre=padre, producto_hijo=hijo, tipo=tipo,
            )
        messages.success(request, f'Compatibilidad guardada.')
        return redirect('gestion_compatibilidades')

    return render(request, 'gestion/catalogo/compatibilidad_form.html', {
        'compat': compat,
        'productos': productos,
    })


@login_required
@rol_requerido('admin', 'dueno')
def compatibilidad_eliminar(request, comp_id):
    tenant = _get_tenant(request)
    compat = get_object_or_404(Compatibilidad, id=comp_id, tenant=tenant)
    if request.method == 'POST':
        compat.delete()
        messages.success(request, 'Compatibilidad eliminada.')
    return redirect('gestion_compatibilidades')
