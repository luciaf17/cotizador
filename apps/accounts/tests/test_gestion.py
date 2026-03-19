"""Tests de ABM y gestión del dueño."""

import pytest
from decimal import Decimal

from django.test import Client as TestClient

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.clientes.models import FormaPago, TipoCliente
from apps.clientes.tests.factories import FormaPagoFactory, TipoClienteFactory
from apps.tenants.tests.factories import TenantFactory


@pytest.fixture
def tenant():
    return TenantFactory()


@pytest.fixture
def dueno(tenant):
    u = UserFactory(tenant=tenant, rol='dueno', is_staff=True)
    return u


@pytest.fixture
def vendedor(tenant):
    return UserFactory(tenant=tenant, rol='vendedor')


@pytest.fixture
def dueno_client(dueno):
    c = TestClient()
    c.force_login(dueno)
    return c


@pytest.fixture
def vendedor_client(vendedor):
    c = TestClient()
    c.force_login(vendedor)
    return c


@pytest.mark.django_db
class TestDashboard:
    def test_dueno_ve_dashboard(self, dueno_client):
        response = dueno_client.get('/gestion/')
        assert response.status_code == 200
        assert b'Dashboard' in response.content

    def test_vendedor_no_ve_dashboard(self, vendedor_client):
        response = vendedor_client.get('/gestion/')
        assert response.status_code == 403


@pytest.mark.django_db
class TestGestionUsuarios:
    def test_lista_usuarios(self, dueno_client, tenant):
        response = dueno_client.get('/gestion/usuarios/')
        assert response.status_code == 200

    def test_crear_usuario(self, dueno_client, tenant):
        response = dueno_client.post('/gestion/usuarios/crear/', {
            'email': 'nuevo@test.com',
            'nombre': 'Nuevo Vendedor',
            'password': 'test1234',
            'rol': 'vendedor',
            'bonif_max_porcentaje': '10',
            'comision_porcentaje': '3',
        })
        assert response.status_code == 302
        assert User.objects.filter(email='nuevo@test.com').exists()
        u = User.objects.get(email='nuevo@test.com')
        assert u.tenant == tenant
        assert u.bonif_max_porcentaje == Decimal('10')

    def test_editar_usuario(self, dueno_client, vendedor):
        response = dueno_client.post(f'/gestion/usuarios/{vendedor.id}/editar/', {
            'nombre': 'Nombre Cambiado',
            'rol': 'vendedor',
            'bonif_max_porcentaje': '20',
            'comision_porcentaje': '7',
            'activo': '1',
        })
        assert response.status_code == 302
        vendedor.refresh_from_db()
        assert vendedor.nombre == 'Nombre Cambiado'
        assert vendedor.bonif_max_porcentaje == Decimal('20')

    def test_vendedor_no_puede_crear_usuarios(self, vendedor_client):
        response = vendedor_client.get('/gestion/usuarios/crear/')
        assert response.status_code == 403


@pytest.mark.django_db
class TestCRUDTiposCliente:
    def test_lista_tipos_cliente(self, dueno_client, tenant):
        TipoClienteFactory(tenant=tenant, nombre='Concesionario')
        response = dueno_client.get('/gestion/tipos-cliente/')
        assert response.status_code == 200
        assert b'Concesionario' in response.content

    def test_crear_tipo_cliente(self, dueno_client, tenant):
        dueno_client.post('/gestion/tipos-cliente/guardar/', {
            'nombre': 'Distribuidor',
            'bonificacion_default': '12',
        })
        assert TipoCliente.objects.filter(tenant=tenant, nombre='Distribuidor').exists()

    def test_editar_tipo_cliente(self, dueno_client, tenant):
        tipo = TipoClienteFactory(tenant=tenant, nombre='Viejo')
        dueno_client.post('/gestion/tipos-cliente/guardar/', {
            'tipo_id': tipo.id,
            'nombre': 'Nuevo',
            'bonificacion_default': '20',
        })
        tipo.refresh_from_db()
        assert tipo.nombre == 'Nuevo'
        assert tipo.bonificacion_default == Decimal('20')


@pytest.mark.django_db
class TestCRUDFormasPago:
    def test_lista_formas_pago(self, dueno_client, tenant):
        FormaPagoFactory(tenant=tenant, nombre='Contado')
        response = dueno_client.get('/gestion/formas-pago/')
        assert response.status_code == 200
        assert b'Contado' in response.content

    def test_crear_forma_pago(self, dueno_client, tenant):
        dueno_client.post('/gestion/formas-pago/guardar/', {
            'nombre': 'Transferencia',
            'bonificacion_porcentaje': '8',
        })
        assert FormaPago.objects.filter(tenant=tenant, nombre='Transferencia').exists()


@pytest.mark.django_db
class TestReportes:
    def test_reportes_accesible(self, dueno_client):
        response = dueno_client.get('/gestion/reportes/')
        assert response.status_code == 200
        assert b'Reportes' in response.content

    def test_vendedor_no_ve_reportes(self, vendedor_client):
        response = vendedor_client.get('/gestion/reportes/')
        assert response.status_code == 403
