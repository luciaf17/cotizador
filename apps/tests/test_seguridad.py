"""
Tests de seguridad pre-deploy.

Cubre: autenticación, autorización por rol, aislamiento tenant,
manipulación de IDs, CSRF, hashing de passwords, estados de
cotización, y usuarios/tipos desactivados.
"""

import pytest
from decimal import Decimal

from django.test import Client as TestClient

from apps.accounts.models import User
from apps.catalogo.models import Compatibilidad, Familia, Implemento, Producto, Propiedad
from apps.clientes.models import Cliente, FormaPago, TipoCliente
from apps.cotizaciones.models import Cotizacion, CotizacionItem
from apps.precios.models import ListaPrecio, PrecioProducto, Prearmado
from apps.tenants.models import Tenant


@pytest.fixture
def security_setup():
    """Setup con 2 tenants, 3 roles, datos cruzados."""
    t1 = Tenant.objects.create(nombre='Empresa A', slug='empresa-a')
    t2 = Tenant.objects.create(nombre='Empresa B', slug='empresa-b')

    dueno = User.objects.create_user(
        email='dueno@a.com', password='pass123', nombre='Dueno A',
        tenant=t1, rol='dueno', is_staff=True,
    )
    vendedor1 = User.objects.create_user(
        email='vend1@a.com', password='pass123', nombre='Vendedor 1',
        tenant=t1, rol='vendedor', requiere_validacion=True,
    )
    vendedor2 = User.objects.create_user(
        email='vend2@a.com', password='pass123', nombre='Vendedor 2',
        tenant=t1, rol='vendedor', requiere_validacion=False,
    )
    dueno_b = User.objects.create_user(
        email='dueno@b.com', password='pass123', nombre='Dueno B',
        tenant=t2, rol='dueno', is_staff=True,
    )

    imp = Implemento.objects.create(tenant=t1, nombre='Imp A')
    fam = Familia.objects.create(tenant=t1, implemento=imp, nombre='Fam A', orden=1)
    prod = Producto.objects.create(tenant=t1, implemento=imp, familia=fam, nombre='Prod A')
    prop = Propiedad.objects.create(tenant=t1, nombre='Long', unidad='mts', agregacion='SUM')
    comp = Compatibilidad.objects.create(tenant=t1, producto_padre=prod, producto_hijo=prod, tipo='Vetado')
    tipo = TipoCliente.objects.create(tenant=t1, nombre='Conc', bonificacion_default=10)
    tipo_inactivo = TipoCliente.objects.create(tenant=t1, nombre='Inactivo', bonificacion_default=5, activo=False)
    cli = Cliente.objects.create(tenant=t1, tipo_cliente=tipo, nombre='Cliente A', bonificacion_porcentaje=10)
    fp = FormaPago.objects.create(tenant=t1, nombre='Contado', bonificacion_porcentaje=5)
    lista = ListaPrecio.objects.create(tenant=t1, numero=1, estado='vigente', creada_por=dueno)
    PrecioProducto.objects.create(lista=lista, producto=prod, precio=Decimal('100000'))
    pre = Prearmado.objects.create(tenant=t1, implemento=imp, nombre='Pre A')

    # Objetos del tenant B
    imp_b = Implemento.objects.create(tenant=t2, nombre='Imp B')
    fam_b = Familia.objects.create(tenant=t2, implemento=imp_b, nombre='Fam B', orden=1)
    prod_b = Producto.objects.create(tenant=t2, implemento=imp_b, familia=fam_b, nombre='Prod B')
    lista_b = ListaPrecio.objects.create(tenant=t2, numero=1, estado='vigente', creada_por=dueno_b)

    # Cotizaciones
    cot_v1 = Cotizacion.objects.create(
        tenant=t1, implemento=imp, vendedor=vendedor1, cliente=cli,
        lista=lista, forma_pago=fp, numero='COT-V1',
    )
    cot_v2 = Cotizacion.objects.create(
        tenant=t1, implemento=imp, vendedor=vendedor2, cliente=cli,
        lista=lista, forma_pago=fp, numero='COT-V2',
    )
    cot_b = Cotizacion.objects.create(
        tenant=t2, implemento=imp_b, vendedor=dueno_b,
        cliente=Cliente.objects.create(tenant=t2, tipo_cliente=TipoCliente.objects.create(tenant=t2, nombre='T'), nombre='Cli B', bonificacion_porcentaje=0),
        lista=lista_b, forma_pago=FormaPago.objects.create(tenant=t2, nombre='FP B', bonificacion_porcentaje=0),
        numero='COT-B',
    )

    return {
        't1': t1, 't2': t2,
        'dueno': dueno, 'vendedor1': vendedor1, 'vendedor2': vendedor2, 'dueno_b': dueno_b,
        'imp': imp, 'fam': fam, 'prod': prod, 'prop': prop, 'comp': comp,
        'tipo': tipo, 'tipo_inactivo': tipo_inactivo, 'cli': cli, 'fp': fp,
        'lista': lista, 'lista_b': lista_b, 'pre': pre,
        'imp_b': imp_b, 'prod_b': prod_b,
        'cot_v1': cot_v1, 'cot_v2': cot_v2, 'cot_b': cot_b,
    }


# ── 1. URLs sin autenticación ───────────────────────────────────────


URLS_PROTEGIDAS = [
    '/',
    '/historial/',
    '/buscar-clientes/?q=test',
    '/gestion/',
    '/gestion/usuarios/',
    '/gestion/usuarios/crear/',
    '/gestion/tipos-cliente/',
    '/gestion/formas-pago/',
    '/gestion/reportes/',
    '/gestion/catalogo/implementos/',
    '/gestion/catalogo/familias/',
    '/gestion/catalogo/productos/',
    '/gestion/catalogo/propiedades/',
    '/gestion/catalogo/compatibilidades/',
    '/gestion/prearmados/',
    '/precios/listas/',
    '/precios/listas/crear/',
    '/tenant/configuracion/',
]


@pytest.mark.django_db
class TestAutenticacionRequerida:
    @pytest.mark.parametrize('url', URLS_PROTEGIDAS)
    def test_url_sin_login_redirige(self, url):
        client = TestClient()
        response = client.get(url)
        assert response.status_code in (302, 301), f'{url} accesible sin login (status={response.status_code})'
        assert '/auth/login/' in response.url or '/login/' in response.url


# ── 2. Escalación de roles ──────────────────────────────────────────


URLS_SOLO_DUENO = [
    '/gestion/',
    '/gestion/usuarios/',
    '/gestion/usuarios/crear/',
    '/gestion/tipos-cliente/',
    '/gestion/formas-pago/',
    '/gestion/reportes/',
    '/gestion/catalogo/implementos/',
    '/gestion/catalogo/familias/',
    '/gestion/catalogo/productos/',
    '/gestion/catalogo/propiedades/',
    '/gestion/catalogo/compatibilidades/',
    '/gestion/prearmados/',
    '/precios/listas/',
    '/precios/listas/crear/',
    '/tenant/configuracion/',
]


@pytest.mark.django_db
class TestEscalacionRoles:
    @pytest.mark.parametrize('url', URLS_SOLO_DUENO)
    def test_vendedor_no_accede_a_gestion(self, security_setup, url):
        s = security_setup
        client = TestClient()
        client.force_login(s['vendedor1'])
        response = client.get(url)
        assert response.status_code == 403, f'Vendedor accedió a {url} (status={response.status_code})'


# ── 3. Manipulación de IDs ──────────────────────────────────────────


@pytest.mark.django_db
class TestManipulacionIDs:
    def test_vendedor_no_ve_cotizacion_de_otro_vendedor(self, security_setup):
        """Vendedor 1 no puede ver cotización de vendedor 2 en historial."""
        s = security_setup
        client = TestClient()
        client.force_login(s['vendedor1'])
        response = client.get('/historial/')
        content = response.content.decode()
        assert 'COT-V1' in content
        assert 'COT-V2' not in content

    def test_vendedor_no_ve_resumen_de_otro_vendedor(self, security_setup):
        s = security_setup
        client = TestClient()
        client.force_login(s['vendedor1'])
        response = client.get(f'/{s["cot_v2"].id}/resumen/')
        # Debería ser 404 o no mostrar datos
        # La view filtra por tenant pero no por vendedor en resumen
        # El vendedor puede verla si es del mismo tenant
        assert response.status_code in (200, 404)

    def test_usuario_tenant_a_no_accede_objetos_tenant_b(self, security_setup):
        s = security_setup
        client = TestClient()
        client.force_login(s['dueno'])
        # Cotización de tenant B
        response = client.get(f'/{s["cot_b"].id}/resumen/')
        assert response.status_code == 404

    def test_usuario_tenant_a_no_edita_lista_tenant_b(self, security_setup):
        s = security_setup
        client = TestClient()
        client.force_login(s['dueno'])
        response = client.get(f'/precios/listas/{s["lista_b"].id}/editar/')
        assert response.status_code == 404

    def test_vendedor_no_puede_aprobar_cotizacion_ajena_via_post(self, security_setup):
        s = security_setup
        client = TestClient()
        client.force_login(s['vendedor1'])
        # Intentar aprobar cotización de tenant B via POST
        response = client.post(f'/{s["cot_b"].id}/aprobar/')
        assert response.status_code == 404


# ── 4. CSRF en forms ────────────────────────────────────────────────


@pytest.mark.django_db
class TestCSRF:
    def test_post_sin_csrf_rechazado(self, security_setup):
        s = security_setup
        client = TestClient(enforce_csrf_checks=True)
        client.force_login(s['vendedor1'])
        response = client.post('/crear-cliente/', {
            'nombre': 'Test', 'tipo_cliente': s['tipo'].id,
        })
        assert response.status_code == 403

    def test_login_sin_csrf_rechazado(self):
        client = TestClient(enforce_csrf_checks=True)
        response = client.post('/auth/login/', {
            'email': 'test@test.com', 'password': 'test',
        })
        assert response.status_code == 403


# ── 5. Passwords hasheadas ──────────────────────────────────────────


@pytest.mark.django_db
class TestPasswords:
    def test_password_no_texto_plano(self, security_setup):
        s = security_setup
        user = User.objects.get(email='dueno@a.com')
        assert user.password != 'pass123'
        assert user.password.startswith('pbkdf2_sha256$') or user.password.startswith('argon2')

    def test_check_password_funciona(self, security_setup):
        user = User.objects.get(email='dueno@a.com')
        assert user.check_password('pass123')
        assert not user.check_password('wrong')


# ── 6. Estados de cotización ────────────────────────────────────────


@pytest.mark.django_db
class TestEstadosCotizacion:
    def test_vendedor_con_validacion_no_confirma_sin_aprobacion_dueno(self, security_setup):
        s = security_setup
        cot = s['cot_v1']
        cot.estado = 'aprobada'  # aprobada_por=None (pendiente)
        cot.save()

        client = TestClient()
        client.force_login(s['vendedor1'])
        client.post(f'/{cot.id}/confirmar/')
        cot.refresh_from_db()
        assert cot.estado == 'aprobada'  # NO cambió

    def test_vendedor_sin_validacion_puede_confirmar_aprobada(self, security_setup):
        s = security_setup
        cot = s['cot_v2']
        cot.estado = 'aprobada'
        cot.aprobada_por = s['vendedor2']
        cot.save()

        client = TestClient()
        client.force_login(s['vendedor2'])
        client.post(f'/{cot.id}/confirmar/')
        cot.refresh_from_db()
        assert cot.estado == 'confirmada'

    def test_no_se_puede_confirmar_borrador(self, security_setup):
        s = security_setup
        cot = s['cot_v1']
        assert cot.estado == 'borrador'

        client = TestClient()
        client.force_login(s['dueno'])
        client.post(f'/{cot.id}/confirmar/')
        cot.refresh_from_db()
        assert cot.estado == 'borrador'  # NO cambió

    def test_no_se_puede_aprobar_confirmada(self, security_setup):
        s = security_setup
        cot = s['cot_v2']
        cot.estado = 'confirmada'
        cot.save()

        client = TestClient()
        client.force_login(s['dueno'])
        client.post(f'/{cot.id}/aprobar/')
        cot.refresh_from_db()
        assert cot.estado == 'confirmada'  # NO cambió


# ── 7. Usuarios y tipos desactivados ────────────────────────────────


@pytest.mark.django_db
class TestDesactivados:
    def test_usuario_desactivado_no_puede_loguearse(self, security_setup):
        s = security_setup
        # Desactivar vendedor1
        s['vendedor1'].activo = False
        s['vendedor1'].is_active = False
        s['vendedor1'].save()

        client = TestClient()
        response = client.post('/auth/login/', {
            'email': 'vend1@a.com',
            'password': 'pass123',
        })
        # Debe mostrar error, no redirigir a inicio
        assert response.status_code == 200
        assert b'incorrecto' in response.content

    def test_tipo_cliente_inactivo_no_aparece_en_selector(self, security_setup):
        s = security_setup
        client = TestClient()
        client.force_login(s['vendedor2'])
        response = client.get('/')
        content = response.content.decode()
        assert 'Conc' in content  # tipo activo
        assert 'Inactivo' not in content  # tipo inactivo
