"""Servicios de listas de precios."""

import math
from decimal import Decimal

from .models import EstructuraPrearmado, ListaPrecio, PrecioProducto


def crear_nueva_lista(tenant, lista_base, ajuste_pct, creada_por, nombre=None):
    """
    Crea nueva lista de precios con ajuste % sobre la lista base.
    CEILING(precio_anterior × (1 + %/100), 1)

    Returns:
        ListaPrecio en estado borrador
    """
    ultimo_numero = (
        ListaPrecio.objects.filter(tenant=tenant)
        .order_by('-numero')
        .values_list('numero', flat=True)
        .first()
    ) or 0

    nueva = ListaPrecio.objects.create(
        tenant=tenant,
        numero=ultimo_numero + 1,
        nombre=nombre or f'Lista #{ultimo_numero + 1}',
        estado='borrador',
        ajuste_pct=ajuste_pct,
        lista_base=lista_base,
        creada_por=creada_por,
    )

    factor = 1 + Decimal(str(ajuste_pct)) / 100
    precios_base = PrecioProducto.objects.filter(lista=lista_base)

    nuevos_precios = []
    for pp in precios_base:
        nuevo_precio = Decimal(str(math.ceil(float(pp.precio * factor))))
        nuevos_precios.append(PrecioProducto(
            lista=nueva,
            producto=pp.producto,
            precio=nuevo_precio,
        ))

    PrecioProducto.objects.bulk_create(nuevos_precios)
    return nueva


def activar_lista(lista):
    """
    Activa una lista borrador: la anterior vigente pasa a histórica.
    """
    ListaPrecio.objects.filter(
        tenant=lista.tenant,
        estado='vigente',
    ).update(estado='historica')

    lista.estado = 'vigente'
    lista.save()
    return lista


def calcular_precio_prearmado(prearmado, lista):
    """Precio prearmado = Σ(precio_en_lista × cantidad)."""
    total = Decimal('0')
    for est in EstructuraPrearmado.objects.filter(prearmado=prearmado):
        try:
            pp = PrecioProducto.objects.get(lista=lista, producto=est.producto)
            total += pp.precio * est.cantidad
        except PrecioProducto.DoesNotExist:
            pass
    return total
