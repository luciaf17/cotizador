"""Tests de servicios de listas de precios."""

import pytest
from decimal import Decimal

from apps.accounts.tests.factories import UserFactory
from apps.catalogo.tests.factories import ImplementoFactory, ProductoFactory
from apps.precios.models import ListaPrecio, PrecioProducto, Prearmado, EstructuraPrearmado
from apps.precios.services import activar_lista, calcular_precio_prearmado, crear_nueva_lista
from apps.precios.tests.factories import (
    ListaPrecioFactory,
    PrearmadoFactory,
    PrecioProductoFactory,
)
from apps.tenants.tests.factories import TenantFactory


@pytest.mark.django_db
class TestCrearNuevaLista:
    def test_crea_lista_borrador_con_precios_ajustados(self):
        tenant = TenantFactory()
        user = UserFactory(tenant=tenant)
        lista_base = ListaPrecioFactory(tenant=tenant, numero=81, estado='vigente', creada_por=user)
        prod = ProductoFactory(tenant=tenant)
        PrecioProductoFactory(lista=lista_base, producto=prod, precio=Decimal('10000'))

        nueva = crear_nueva_lista(tenant, lista_base, Decimal('5'), user)

        assert nueva.estado == 'borrador'
        assert nueva.numero == 82
        assert nueva.lista_base == lista_base
        pp = PrecioProducto.objects.get(lista=nueva, producto=prod)
        # CEILING(10000 * 1.05) = 10500
        assert pp.precio == Decimal('10500')

    def test_ceiling_redondea_hacia_arriba(self):
        tenant = TenantFactory()
        user = UserFactory(tenant=tenant)
        lista_base = ListaPrecioFactory(tenant=tenant, numero=1, estado='vigente', creada_por=user)
        prod = ProductoFactory(tenant=tenant)
        PrecioProductoFactory(lista=lista_base, producto=prod, precio=Decimal('10001'))

        nueva = crear_nueva_lista(tenant, lista_base, Decimal('5'), user)
        pp = PrecioProducto.objects.get(lista=nueva, producto=prod)
        # CEILING(10001 * 1.05) = CEILING(10501.05) = 10502
        assert pp.precio == Decimal('10502')

    def test_todos_los_precios_se_copian(self):
        tenant = TenantFactory()
        user = UserFactory(tenant=tenant)
        lista_base = ListaPrecioFactory(tenant=tenant, numero=1, estado='vigente', creada_por=user)
        for i in range(5):
            PrecioProductoFactory(lista=lista_base, producto=ProductoFactory(tenant=tenant))

        nueva = crear_nueva_lista(tenant, lista_base, Decimal('10'), user)
        assert PrecioProducto.objects.filter(lista=nueva).count() == 5


@pytest.mark.django_db
class TestActivarLista:
    def test_activa_lista_y_pone_anterior_como_historica(self):
        tenant = TenantFactory()
        user = UserFactory(tenant=tenant)
        vigente = ListaPrecioFactory(tenant=tenant, numero=81, estado='vigente', creada_por=user)
        borrador = ListaPrecioFactory(tenant=tenant, numero=82, estado='borrador', creada_por=user)

        activar_lista(borrador)

        vigente.refresh_from_db()
        borrador.refresh_from_db()
        assert vigente.estado == 'historica'
        assert borrador.estado == 'vigente'


@pytest.mark.django_db
class TestCalcularPrecioPrearmado:
    def test_precio_es_suma_de_estructura(self):
        tenant = TenantFactory()
        user = UserFactory(tenant=tenant)
        lista = ListaPrecioFactory(tenant=tenant, estado='vigente', creada_por=user)
        imp = ImplementoFactory(tenant=tenant)
        pre = PrearmadoFactory(tenant=tenant, implemento=imp)

        prod1 = ProductoFactory(tenant=tenant)
        prod2 = ProductoFactory(tenant=tenant)
        PrecioProductoFactory(lista=lista, producto=prod1, precio=Decimal('1000'))
        PrecioProductoFactory(lista=lista, producto=prod2, precio=Decimal('2000'))

        EstructuraPrearmado.objects.create(prearmado=pre, producto=prod1, cantidad=2)
        EstructuraPrearmado.objects.create(prearmado=pre, producto=prod2, cantidad=1)

        precio = calcular_precio_prearmado(pre, lista)
        # 1000*2 + 2000*1 = 4000
        assert precio == Decimal('4000')
