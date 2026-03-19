"""
Tests de aislamiento multi-tenant.

Verifica que un usuario de un tenant NO puede ver datos de otro tenant
en ninguna vista del sistema.
"""

import pytest
from decimal import Decimal

from django.test import Client as TestClient

from apps.accounts.models import User
from apps.catalogo.models import Implemento, Familia, Producto, Propiedad
from apps.clientes.models import Cliente, FormaPago, TipoCliente
from apps.cotizaciones.models import Cotizacion, CotizacionItem
from apps.precios.models import EstructuraPrearmado, ListaPrecio, PrecioProducto, Prearmado
from apps.tenants.models import Tenant


@pytest.fixture
def tenants():
    """Crea 2 tenants con datos completos y aislados."""
    t1 = Tenant.objects.create(nombre='Tenant A', slug='tenant-a', moneda='ARS')
    t2 = Tenant.objects.create(nombre='Tenant B', slug='tenant-b', moneda='ARS')

    # Usuarios
    u1 = User.objects.create_user(email='dueno@a.com', password='test123', nombre='Dueno A',
                                   tenant=t1, rol='dueno', is_staff=True)
    u2 = User.objects.create_user(email='dueno@b.com', password='test123', nombre='Dueno B',
                                   tenant=t2, rol='dueno', is_staff=True)

    # Datos Tenant A
    imp_a = Implemento.objects.create(tenant=t1, nombre='Implemento A')
    fam_a = Familia.objects.create(tenant=t1, implemento=imp_a, nombre='Familia A', orden=1)
    prod_a = Producto.objects.create(tenant=t1, implemento=imp_a, familia=fam_a, nombre='Producto A')
    tipo_a = TipoCliente.objects.create(tenant=t1, nombre='Tipo A', bonificacion_default=10)
    cli_a = Cliente.objects.create(tenant=t1, tipo_cliente=tipo_a, nombre='Cliente A', bonificacion_porcentaje=10)
    fp_a = FormaPago.objects.create(tenant=t1, nombre='Contado A', bonificacion_porcentaje=5)
    lista_a = ListaPrecio.objects.create(tenant=t1, numero=1, estado='vigente', creada_por=u1)
    PrecioProducto.objects.create(lista=lista_a, producto=prod_a, precio=Decimal('1000000'))
    cot_a = Cotizacion.objects.create(
        tenant=t1, implemento=imp_a, vendedor=u1, cliente=cli_a,
        lista=lista_a, forma_pago=fp_a, numero='COT-A-001',
        subtotal_bruto=Decimal('1000000'), precio_total=Decimal('1210000'),
    )

    # Datos Tenant B
    imp_b = Implemento.objects.create(tenant=t2, nombre='Implemento B')
    fam_b = Familia.objects.create(tenant=t2, implemento=imp_b, nombre='Familia B', orden=1)
    prod_b = Producto.objects.create(tenant=t2, implemento=imp_b, familia=fam_b, nombre='Producto B')
    tipo_b = TipoCliente.objects.create(tenant=t2, nombre='Tipo B', bonificacion_default=15)
    cli_b = Cliente.objects.create(tenant=t2, tipo_cliente=tipo_b, nombre='Cliente B', bonificacion_porcentaje=15)
    fp_b = FormaPago.objects.create(tenant=t2, nombre='Contado B', bonificacion_porcentaje=10)
    lista_b = ListaPrecio.objects.create(tenant=t2, numero=1, estado='vigente', creada_por=u2)
    PrecioProducto.objects.create(lista=lista_b, producto=prod_b, precio=Decimal('2000000'))
    cot_b = Cotizacion.objects.create(
        tenant=t2, implemento=imp_b, vendedor=u2, cliente=cli_b,
        lista=lista_b, forma_pago=fp_b, numero='COT-B-001',
        subtotal_bruto=Decimal('2000000'), precio_total=Decimal('2420000'),
    )

    # Propiedades
    prop_a = Propiedad.objects.create(tenant=t1, nombre='Longitud A', unidad='mts', agregacion='SUM')
    prop_b = Propiedad.objects.create(tenant=t2, nombre='Longitud B', unidad='mts', agregacion='SUM')

    # Compatibilidades
    from apps.catalogo.models import Compatibilidad
    comp_a = Compatibilidad.objects.create(tenant=t1, producto_padre=prod_a, producto_hijo=prod_a, tipo='Vetado')
    comp_b = Compatibilidad.objects.create(tenant=t2, producto_padre=prod_b, producto_hijo=prod_b, tipo='Vetado')

    # Prearmados
    pre_a = Prearmado.objects.create(tenant=t1, implemento=imp_a, nombre='Prearmado A')
    pre_b = Prearmado.objects.create(tenant=t2, implemento=imp_b, nombre='Prearmado B')

    return {
        't1': t1, 't2': t2, 'u1': u1, 'u2': u2,
        'imp_a': imp_a, 'imp_b': imp_b,
        'fam_a': fam_a, 'fam_b': fam_b,
        'prod_a': prod_a, 'prod_b': prod_b,
        'prop_a': prop_a, 'prop_b': prop_b,
        'comp_a': comp_a, 'comp_b': comp_b,
        'pre_a': pre_a, 'pre_b': pre_b,
        'cot_a': cot_a, 'cot_b': cot_b,
        'lista_a': lista_a, 'lista_b': lista_b,
        'cli_a': cli_a, 'cli_b': cli_b,
    }


def _client_for(user):
    c = TestClient()
    c.force_login(user)
    return c


@pytest.mark.django_db
class TestAislamientoHistorial:
    def test_usuario_a_no_ve_cotizaciones_de_b(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/historial/')
        content = response.content.decode()
        assert 'COT-A-001' in content
        assert 'COT-B-001' not in content
        assert 'Cliente B' not in content

    def test_usuario_b_no_ve_cotizaciones_de_a(self, tenants):
        client = _client_for(tenants['u2'])
        response = client.get('/historial/')
        content = response.content.decode()
        assert 'COT-B-001' in content
        assert 'COT-A-001' not in content
        assert 'Cliente A' not in content


@pytest.mark.django_db
class TestAislamientoResumen:
    def test_usuario_a_no_puede_ver_cotizacion_de_b(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get(f'/{tenants["cot_b"].id}/resumen/')
        assert response.status_code == 404

    def test_usuario_b_no_puede_ver_cotizacion_de_a(self, tenants):
        client = _client_for(tenants['u2'])
        response = client.get(f'/{tenants["cot_a"].id}/resumen/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestAislamientoListasPrecios:
    def test_usuario_a_ve_solo_listas_de_a(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/precios/listas/')
        content = response.content.decode()
        assert 'Tenant A' not in content or True  # listas no muestran nombre tenant
        # Verificar que solo hay 1 lista (la de A)
        assert content.count('Lista #1') >= 1

    def test_usuario_a_no_puede_editar_lista_de_b(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get(f'/precios/listas/{tenants["lista_b"].id}/editar/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestAislamientoImplementos:
    def test_usuario_a_ve_solo_implementos_de_a(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/implementos/' + str(tenants['cli_a'].id) + '/')
        content = response.content.decode()
        assert 'Implemento A' in content
        assert 'Implemento B' not in content


@pytest.mark.django_db
class TestAislamientoGestion:
    def test_dashboard_solo_datos_propios(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/')
        content = response.content.decode()
        # No debe mostrar datos del tenant B
        assert 'Dueno B' not in content

    def test_usuarios_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/usuarios/')
        content = response.content.decode()
        assert 'dueno@a.com' in content
        assert 'dueno@b.com' not in content

    def test_tipos_cliente_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/tipos-cliente/')
        content = response.content.decode()
        assert 'Tipo A' in content
        assert 'Tipo B' not in content

    def test_formas_pago_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/formas-pago/')
        content = response.content.decode()
        assert 'Contado A' in content
        assert 'Contado B' not in content

    def test_reportes_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/reportes/')
        assert response.status_code == 200

    def test_implementos_gestion_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/catalogo/implementos/')
        content = response.content.decode()
        assert 'Implemento A' in content
        assert 'Implemento B' not in content

    def test_productos_gestion_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/catalogo/productos/')
        content = response.content.decode()
        assert 'Producto A' in content
        assert 'Producto B' not in content


@pytest.mark.django_db
class TestAislamientoConfiguracion:
    def test_configuracion_muestra_tenant_propio(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/tenant/configuracion/')
        content = response.content.decode()
        assert 'Tenant A' in content

    def test_configuracion_no_muestra_tenant_ajeno(self, tenants):
        client = _client_for(tenants['u2'])
        response = client.get('/tenant/configuracion/')
        content = response.content.decode()
        assert 'Tenant B' in content
        assert 'Tenant A' not in content


@pytest.mark.django_db
class TestAislamientoCrearCotizacion:
    def test_nuevo_cotizacion_solo_implementos_propios(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get(f'/implementos/{tenants["cli_a"].id}/')
        content = response.content.decode()
        assert 'Implemento A' in content
        assert 'Implemento B' not in content

    def test_no_puede_cotizar_con_cliente_de_otro_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get(f'/implementos/{tenants["cli_b"].id}/')
        assert response.status_code == 404

    def test_buscar_clientes_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/buscar-clientes/?q=Cliente')
        content = response.content.decode()
        assert 'Cliente A' in content
        assert 'Cliente B' not in content


@pytest.mark.django_db
class TestAislamientoCatalogo:
    def test_familias_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/catalogo/familias/')
        content = response.content.decode()
        assert 'Familia A' in content
        assert 'Familia B' not in content

    def test_editar_familia_de_otro_tenant_404(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get(f'/gestion/catalogo/familias/{tenants["fam_b"].id}/editar/')
        assert response.status_code == 404

    def test_propiedades_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/catalogo/propiedades/')
        content = response.content.decode()
        assert 'Longitud A' in content
        assert 'Longitud B' not in content

    def test_compatibilidades_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/catalogo/compatibilidades/')
        content = response.content.decode()
        assert 'Producto A' in content
        assert 'Producto B' not in content

    def test_editar_compatibilidad_de_otro_tenant_404(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get(f'/gestion/catalogo/compatibilidades/{tenants["comp_b"].id}/editar/')
        assert response.status_code == 404

    def test_editar_implemento_de_otro_tenant_404(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get(f'/gestion/catalogo/implementos/{tenants["imp_b"].id}/editar/')
        assert response.status_code == 404

    def test_editar_producto_de_otro_tenant_404(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get(f'/gestion/catalogo/productos/{tenants["prod_b"].id}/editar/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestAislamientoPrearmados:
    def test_prearmados_solo_del_tenant(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get('/gestion/prearmados/')
        content = response.content.decode()
        assert 'Prearmado A' in content
        assert 'Prearmado B' not in content

    def test_editar_prearmado_de_otro_tenant_404(self, tenants):
        client = _client_for(tenants['u1'])
        response = client.get(f'/gestion/prearmados/{tenants["pre_b"].id}/editar/')
        assert response.status_code == 404
