"""Tests de permisos por rol y flujo de aprobación."""

import pytest
from decimal import Decimal

from django.test import Client as TestClient

from apps.accounts.tests.factories import UserFactory
from apps.catalogo.tests.factories import FamiliaFactory, ImplementoFactory, ProductoFactory
from apps.clientes.tests.factories import ClienteFactory, FormaPagoFactory, TipoClienteFactory
from apps.cotizaciones.models import Cotizacion, CotizacionItem
from apps.precios.tests.factories import ListaPrecioFactory, PrecioProductoFactory
from apps.tenants.tests.factories import TenantFactory


@pytest.fixture
def tenant():
    return TenantFactory()


@pytest.fixture
def setup(tenant):
    dueno = UserFactory(tenant=tenant, rol='dueno', is_staff=True, requiere_validacion=False)
    vendedor = UserFactory(tenant=tenant, rol='vendedor', requiere_validacion=True)
    vendedor_libre = UserFactory(tenant=tenant, rol='vendedor', requiere_validacion=False)
    tipo = TipoClienteFactory(tenant=tenant)
    cliente = ClienteFactory(tenant=tenant, tipo_cliente=tipo)
    imp = ImplementoFactory(tenant=tenant)
    fam = FamiliaFactory(tenant=tenant, implemento=imp, orden=1)
    prod = ProductoFactory(tenant=tenant, implemento=imp, familia=fam)
    lista = ListaPrecioFactory(tenant=tenant, estado='vigente', creada_por=dueno)
    PrecioProductoFactory(lista=lista, producto=prod, precio=Decimal('10000'))
    forma_pago = FormaPagoFactory(tenant=tenant)

    return {
        'tenant': tenant, 'dueno': dueno, 'vendedor': vendedor,
        'vendedor_libre': vendedor_libre, 'cliente': cliente,
        'imp': imp, 'fam': fam, 'prod': prod, 'lista': lista,
        'forma_pago': forma_pago,
    }


def _crear_cotizacion(setup, vendedor):
    return Cotizacion.objects.create(
        tenant=setup['tenant'], implemento=setup['imp'],
        vendedor=vendedor, cliente=setup['cliente'],
        lista=setup['lista'], forma_pago=setup['forma_pago'],
        numero=f'COT-TEST-{vendedor.id}',
    )


@pytest.mark.django_db
class TestVisibilidadHistorial:
    def test_vendedor_ve_solo_sus_cotizaciones(self, setup):
        s = setup
        cot_propia = _crear_cotizacion(s, s['vendedor'])
        cot_ajena = _crear_cotizacion(s, s['vendedor_libre'])

        client = TestClient()
        client.force_login(s['vendedor'])
        response = client.get('/historial/')
        content = response.content.decode()

        assert cot_propia.numero in content
        assert cot_ajena.numero not in content

    def test_dueno_ve_todas_las_cotizaciones(self, setup):
        s = setup
        cot1 = _crear_cotizacion(s, s['vendedor'])
        cot2 = _crear_cotizacion(s, s['vendedor_libre'])

        client = TestClient()
        client.force_login(s['dueno'])
        response = client.get('/historial/')
        content = response.content.decode()

        assert cot1.numero in content
        assert cot2.numero in content


@pytest.mark.django_db
class TestFlujoAprobacion:
    def test_aprobar_cambia_estado_a_aprobada(self, setup):
        s = setup
        cot = _crear_cotizacion(s, s['vendedor'])

        client = TestClient()
        client.force_login(s['vendedor'])
        client.post(f'/{cot.id}/aprobar/')
        cot.refresh_from_db()
        assert cot.estado == 'aprobada'

    def test_vendedor_con_validacion_no_puede_confirmar(self, setup):
        s = setup
        cot = _crear_cotizacion(s, s['vendedor'])
        cot.estado = 'aprobada'
        cot.save()

        client = TestClient()
        client.force_login(s['vendedor'])
        client.post(f'/{cot.id}/confirmar/')
        cot.refresh_from_db()
        # Sigue aprobada, no confirmada
        assert cot.estado == 'aprobada'

    def test_vendedor_sin_validacion_puede_confirmar(self, setup):
        s = setup
        cot = _crear_cotizacion(s, s['vendedor_libre'])
        cot.estado = 'aprobada'
        cot.save()

        client = TestClient()
        client.force_login(s['vendedor_libre'])
        client.post(f'/{cot.id}/confirmar/')
        cot.refresh_from_db()
        assert cot.estado == 'confirmada'

    def test_dueno_puede_confirmar(self, setup):
        s = setup
        cot = _crear_cotizacion(s, s['vendedor'])
        cot.estado = 'aprobada'
        cot.save()

        client = TestClient()
        client.force_login(s['dueno'])
        client.post(f'/{cot.id}/confirmar/')
        cot.refresh_from_db()
        assert cot.estado == 'confirmada'
        assert cot.confirmada_por == s['dueno']
        assert cot.confirmada_at is not None


@pytest.mark.django_db
class TestPermisosRol:
    def test_vendedor_no_puede_crear_lista(self, setup):
        s = setup
        client = TestClient()
        client.force_login(s['vendedor'])
        response = client.get('/precios/listas/crear/')
        assert response.status_code == 403

    def test_dueno_puede_crear_lista(self, setup):
        s = setup
        client = TestClient()
        client.force_login(s['dueno'])
        response = client.get('/precios/listas/crear/')
        assert response.status_code == 200

    def test_login_redirige_a_inicio(self, setup):
        s = setup
        client = TestClient()
        response = client.post('/auth/login/', {
            'email': s['vendedor'].email,
            'password': 'testpass123',
        })
        assert response.status_code == 302
        assert response.url == '/'

    def test_login_incorrecto_muestra_error(self, setup):
        client = TestClient()
        response = client.post('/auth/login/', {
            'email': 'noexiste@test.com',
            'password': 'wrong',
        })
        assert response.status_code == 200
        assert b'incorrecto' in response.content
