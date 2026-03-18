"""Tests de views del cotizador."""

import pytest
from decimal import Decimal

from django.test import Client as TestClient

from apps.accounts.tests.factories import UserFactory
from apps.catalogo.tests.factories import (
    FamiliaFactory,
    ImplementoFactory,
    ProductoFactory,
    PropiedadFactory,
    ProductoPropiedadFactory,
)
from apps.clientes.tests.factories import (
    ClienteFactory,
    FormaPagoFactory,
    TipoClienteFactory,
)
from apps.cotizaciones.models import Cotizacion, CotizacionItem
from apps.cotizaciones.tests.factories import CotizacionFactory
from apps.precios.tests.factories import ListaPrecioFactory, PrecioProductoFactory
from apps.tenants.tests.factories import TenantFactory


@pytest.fixture
def tenant():
    return TenantFactory()


@pytest.fixture
def user(tenant):
    u = UserFactory(tenant=tenant)
    u.is_staff = True
    u.save()
    return u


@pytest.fixture
def auth_client(user):
    c = TestClient()
    c.force_login(user)
    return c


@pytest.fixture
def setup_basico(tenant, user):
    tipo = TipoClienteFactory(tenant=tenant, bonificacion_default=Decimal('10'))
    cliente = ClienteFactory(tenant=tenant, tipo_cliente=tipo)
    imp = ImplementoFactory(tenant=tenant)
    fam = FamiliaFactory(tenant=tenant, implemento=imp, orden=1, tipo_seleccion='O', obligatoria='SI')
    prod = ProductoFactory(tenant=tenant, implemento=imp, familia=fam)
    lista = ListaPrecioFactory(tenant=tenant, estado='vigente', creada_por=user)
    PrecioProductoFactory(lista=lista, producto=prod, precio=Decimal('10000'))
    forma_pago = FormaPagoFactory(tenant=tenant)
    return {
        'tenant': tenant,
        'cliente': cliente,
        'implemento': imp,
        'familia': fam,
        'producto': prod,
        'lista': lista,
        'forma_pago': forma_pago,
        'tipo': tipo,
    }


@pytest.mark.django_db
class TestInicio:
    def test_inicio_get(self, auth_client, setup_basico):
        response = auth_client.get('/')
        assert response.status_code == 200
        assert b'Nueva Cotizaci' in response.content

    def test_buscar_clientes(self, auth_client, setup_basico):
        nombre = setup_basico['cliente'].nombre
        response = auth_client.get('/buscar-clientes/', {'q': nombre[:5]})
        assert response.status_code == 200

    def test_crear_cliente_post(self, auth_client, setup_basico):
        response = auth_client.post('/crear-cliente/', {
            'nombre': 'Test Cliente Nuevo',
            'tipo_cliente': setup_basico['tipo'].id,
            'telefono': '123456',
        })
        assert response.status_code == 302

    def test_crear_cliente_sin_nombre_falla(self, auth_client, setup_basico):
        response = auth_client.post('/crear-cliente/', {
            'nombre': '',
            'tipo_cliente': setup_basico['tipo'].id,
        })
        assert response.status_code == 200
        assert b'obligatorio' in response.content


@pytest.mark.django_db
class TestImplementos:
    def test_seleccionar_implemento(self, auth_client, setup_basico):
        cliente = setup_basico['cliente']
        response = auth_client.get(f'/implementos/{cliente.id}/')
        assert response.status_code == 200
        assert setup_basico['implemento'].nombre.encode() in response.content


@pytest.mark.django_db
class TestFlujo:
    def test_crear_cotizacion_redirige_a_paso(self, auth_client, setup_basico):
        s = setup_basico
        response = auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        assert response.status_code == 302
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        assert cot is not None
        assert cot.estado == 'borrador'
        assert '/paso/1/' in response.url

    def test_paso_muestra_productos(self, auth_client, setup_basico):
        s = setup_basico
        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        response = auth_client.get(f'/{cot.id}/paso/1/')
        assert response.status_code == 200
        assert s['producto'].nombre.encode() in response.content

    def test_seleccionar_producto_tipo_o(self, auth_client, setup_basico):
        s = setup_basico
        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        response = auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['producto'].id,
            'familia_id': s['familia'].id,
            'orden': 1,
            'accion': 'add',
        })
        # Tipo O con solo 1 orden → redirige a bonificaciones
        assert response.status_code == 200
        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 1

    def test_bonificaciones_get(self, auth_client, setup_basico):
        s = setup_basico
        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['producto'], familia=s['familia'],
            cantidad=1, precio_unitario=Decimal('10000'),
            precio_linea=Decimal('10000'), iva_porcentaje=Decimal('21'),
        )
        response = auth_client.get(f'/{cot.id}/bonificaciones/')
        assert response.status_code == 200
        assert b'Bonificacion' in response.content or b'Bonificaci' in response.content

    def test_bonificaciones_post_calcula_totales(self, auth_client, setup_basico):
        s = setup_basico
        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['producto'], familia=s['familia'],
            cantidad=1, precio_unitario=Decimal('10000'),
            precio_linea=Decimal('10000'), iva_porcentaje=Decimal('21'),
        )
        response = auth_client.post(f'/{cot.id}/bonificaciones/', {
            'bonif_cliente_pct': '10',
            'bonif_pago_pct': '5',
            'forma_pago_id': s['forma_pago'].id,
        })
        assert response.status_code == 302
        cot.refresh_from_db()
        assert cot.subtotal_bruto == Decimal('10000')
        assert cot.subtotal_neto == Decimal('8550.00')

    def test_resumen_muestra_totales(self, auth_client, setup_basico):
        s = setup_basico
        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        cot.subtotal_bruto = Decimal('10000')
        cot.precio_total = Decimal('12100')
        cot.save()
        response = auth_client.get(f'/{cot.id}/resumen/')
        assert response.status_code == 200
        assert b'12100' in response.content or b'12,100' in response.content

    def test_aprobar_cambia_estado(self, auth_client, setup_basico):
        s = setup_basico
        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        response = auth_client.post(f'/{cot.id}/aprobar/')
        assert response.status_code == 302
        cot.refresh_from_db()
        assert cot.estado == 'aprobada'

    def test_calcular_preview_htmx(self, auth_client, setup_basico):
        s = setup_basico
        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['producto'], familia=s['familia'],
            cantidad=1, precio_unitario=Decimal('10000'),
            precio_linea=Decimal('10000'), iva_porcentaje=Decimal('21'),
        )
        response = auth_client.get(f'/{cot.id}/calcular/', {
            'bonif_cliente_pct': '10',
            'bonif_pago_pct': '0',
        })
        assert response.status_code == 200
        assert b'9000' in response.content or b'9,000' in response.content
