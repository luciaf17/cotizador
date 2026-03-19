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
        # Tipo O con solo 1 orden → redirect a bonificaciones
        assert response.status_code == 302
        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 1
        assert 'bonificaciones' in response.url

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
        # precio_ar filter: $12.100
        assert b'$12.100' in response.content

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
        # precio_ar filter: $9.000
        assert b'$9.000' in response.content

    def test_bonif_slider_max_incluye_extra(self, auth_client, setup_basico):
        """Slider max = default + extra_por_barra, no 100."""
        s = setup_basico
        # Cliente bonif=10, user bonif_max=15 → extra=7.5 → slider max=17.5
        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['producto'], familia=s['familia'],
            cantidad=1, precio_unitario=Decimal('10000'),
            precio_linea=Decimal('10000'), iva_porcentaje=Decimal('21'),
        )
        response = auth_client.get(f'/{cot.id}/bonificaciones/')
        assert response.status_code == 200
        content = response.content.decode()
        # max = 10 + 7.5 = 17.5
        assert 'max="17.5"' in content
        assert 'max="100"' not in content

    def test_seleccionar_tipo_y_redirige_al_mismo_paso(self, auth_client, setup_basico):
        """Bug 2: seleccionar tipo Y debe recargar la página completa."""
        s = setup_basico
        fam_y = FamiliaFactory(
            tenant=s['tenant'], implemento=s['implemento'],
            orden=2, tipo_seleccion='Y', obligatoria='NO',
        )
        prod_y = ProductoFactory(
            tenant=s['tenant'], implemento=s['implemento'], familia=fam_y,
        )
        PrecioProductoFactory(lista=s['lista'], producto=prod_y, precio=Decimal('5000'))

        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()
        response = auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': prod_y.id,
            'familia_id': fam_y.id,
            'orden': 2,
            'accion': 'add',
        })
        # Debe hacer redirect (302) al mismo paso para refrescar sidebar
        assert response.status_code == 302
        assert f'/{cot.id}/paso/2/' in response.url


@pytest.mark.django_db
class TestRodadosView:
    def test_rodados_accesible(self, auth_client, setup_basico):
        """Bug 3: rodados deben tener view accesible."""
        s = setup_basico
        tenant = s['tenant']
        imp = ImplementoFactory(tenant=tenant, accesorios_tipo='Rodados', nivel_rodado=1)
        imp_rodados = ImplementoFactory(tenant=tenant, nombre='Rodados')
        prop_llantas = PropiedadFactory(tenant=tenant, nombre='Llantas', agregacion='MAX')
        fam = FamiliaFactory(tenant=tenant, implemento=imp, orden=1)
        fam_llantas = FamiliaFactory(tenant=tenant, implemento=imp_rodados, nombre='Llantas', orden=1)
        prod = ProductoFactory(tenant=tenant, implemento=imp, familia=fam)
        ProductoPropiedadFactory(producto=prod, propiedad=prop_llantas, tipo='Exacto', valor=Decimal('4'))
        llanta = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_llantas)
        PrecioProductoFactory(lista=s['lista'], producto=prod, precio=Decimal('10000'))
        PrecioProductoFactory(lista=s['lista'], producto=llanta, precio=Decimal('500'))

        # Crear cotización directamente
        cot = Cotizacion.objects.create(
            tenant=tenant, implemento=imp, vendedor=s['tenant'].user_set.first(),
            cliente=s['cliente'], lista=s['lista'], forma_pago=s['forma_pago'],
            numero='COT-TEST-RODADOS',
        )
        CotizacionItem.objects.create(
            cotizacion=cot, producto=prod, familia=fam,
            cantidad=1, precio_unitario=Decimal('10000'),
            precio_linea=Decimal('10000'), iva_porcentaje=Decimal('21'),
        )
        response = auth_client.get(f'/{cot.id}/rodados/0/')
        assert response.status_code == 200
        assert b'Llantas' in response.content


@pytest.mark.django_db
class TestTipoORadioButtons:
    def test_tipo_o_selecciona_y_guarda_item(self, auth_client, setup_basico):
        """Form POST en tipo O crea el CotizacionItem correctamente."""
        s = setup_basico
        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()

        response = auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['producto'].id,
            'familia_id': s['familia'].id,
            'orden': 1,
            'accion': 'add',
        })
        # Debe redirigir (302) no quedarse quieto
        assert response.status_code == 302
        item = CotizacionItem.objects.get(cotizacion=cot)
        assert item.producto_id == s['producto'].id
        assert item.precio_unitario == Decimal('10000')

    def test_tipo_o_reemplaza_seleccion_anterior(self, auth_client, setup_basico):
        """Seleccionar otro producto en tipo O reemplaza el anterior."""
        s = setup_basico
        prod2 = ProductoFactory(tenant=s['tenant'], implemento=s['implemento'], familia=s['familia'])
        PrecioProductoFactory(lista=s['lista'], producto=prod2, precio=Decimal('20000'))

        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()

        # Seleccionar primer producto
        auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['producto'].id,
            'familia_id': s['familia'].id,
            'orden': 1, 'accion': 'add',
        })
        # Seleccionar segundo (debe reemplazar)
        auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': prod2.id,
            'familia_id': s['familia'].id,
            'orden': 1, 'accion': 'add',
        })
        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 1
        assert CotizacionItem.objects.get(cotizacion=cot).producto_id == prod2.id

    def test_tipo_o_exclusivo_entre_familias_mismo_orden(self, auth_client, setup_basico):
        """SPEC 5.2: familias tipo O mismo orden son alternativas mutuamente excluyentes."""
        s = setup_basico
        # 2 familias tipo O en orden 1
        fam2 = FamiliaFactory(
            tenant=s['tenant'], implemento=s['implemento'],
            orden=1, tipo_seleccion='O', obligatoria='SI',
        )
        prod2 = ProductoFactory(tenant=s['tenant'], implemento=s['implemento'], familia=fam2)
        PrecioProductoFactory(lista=s['lista'], producto=prod2, precio=Decimal('20000'))
        # Agregar orden 2 para que no sea auto-avance
        FamiliaFactory(tenant=s['tenant'], implemento=s['implemento'], orden=2, tipo_seleccion='Y', obligatoria='NO')

        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()

        # Seleccionar de familia 1
        auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['producto'].id,
            'familia_id': s['familia'].id,
            'orden': 1, 'accion': 'add',
        })
        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 1

        # Seleccionar de familia 2 → debe reemplazar el de familia 1
        auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': prod2.id,
            'familia_id': fam2.id,
            'orden': 1, 'accion': 'add',
        })
        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 1
        assert CotizacionItem.objects.get(cotizacion=cot).producto_id == prod2.id


@pytest.mark.django_db
class TestContinuarObligatorio:
    def test_continuar_deshabilitado_sin_seleccion_obligatoria(self, auth_client, setup_basico):
        """Si familia obligatoria=SI y nada seleccionado, Continuar esta deshabilitado."""
        s = setup_basico
        # Agregar un segundo orden para que el paso 1 tenga boton Continuar
        fam2 = FamiliaFactory(
            tenant=s['tenant'], implemento=s['implemento'],
            orden=1, tipo_seleccion='O', obligatoria='SI',
        )
        ProductoFactory(tenant=s['tenant'], implemento=s['implemento'], familia=fam2)

        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()

        response = auth_client.get(f'/{cot.id}/paso/1/')
        content = response.content.decode()
        # Boton deshabilitado (span con cursor: not-allowed)
        assert 'cursor: not-allowed' in content

    def test_continuar_habilitado_con_seleccion(self, auth_client, setup_basico):
        """Con producto seleccionado en familia obligatoria, Continuar esta habilitado."""
        s = setup_basico
        fam2 = FamiliaFactory(
            tenant=s['tenant'], implemento=s['implemento'],
            orden=1, tipo_seleccion='O', obligatoria='SI',
        )
        prod2 = ProductoFactory(tenant=s['tenant'], implemento=s['implemento'], familia=fam2)
        PrecioProductoFactory(lista=s['lista'], producto=prod2, precio=Decimal('5000'))
        FamiliaFactory(tenant=s['tenant'], implemento=s['implemento'], orden=2, tipo_seleccion='Y', obligatoria='NO')

        auth_client.get(f'/nuevo/{s["cliente"].id}/{s["implemento"].id}/')
        cot = Cotizacion.objects.filter(tenant=s['tenant']).last()

        # Seleccionar en ambas familias obligatorias
        auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['producto'].id,
            'familia_id': s['familia'].id,
            'orden': 1, 'accion': 'add',
        })
        auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': prod2.id,
            'familia_id': fam2.id,
            'orden': 1, 'accion': 'add',
        })

        response = auth_client.get(f'/{cot.id}/paso/1/')
        content = response.content.decode()
        assert 'cursor: not-allowed' not in content
        assert 'Continuar' in content


@pytest.mark.django_db
class TestAutoAvanceARodados:
    def test_tipo_o_auto_avance_ultimo_paso_redirige_a_rodados(self, auth_client, setup_basico):
        """Tipo O con 1 familia en ultimo paso redirige a rodados si aplica."""
        s = setup_basico
        tenant = s['tenant']
        # Implemento con rodados, una sola familia tipo O
        imp = ImplementoFactory(tenant=tenant, accesorios_tipo='Rodados', nivel_rodado=1)
        fam = FamiliaFactory(tenant=tenant, implemento=imp, orden=1, tipo_seleccion='O', obligatoria='SI')
        prod = ProductoFactory(tenant=tenant, implemento=imp, familia=fam)
        prop_llantas = PropiedadFactory(tenant=tenant, nombre='Llantas2', agregacion='MAX')
        ProductoPropiedadFactory(producto=prod, propiedad=prop_llantas, tipo='Exacto', valor=Decimal('4'))
        PrecioProductoFactory(lista=s['lista'], producto=prod, precio=Decimal('10000'))

        imp_rodados = ImplementoFactory(tenant=tenant, nombre='Rodados')
        fam_llantas = FamiliaFactory(tenant=tenant, implemento=imp_rodados, nombre='Llantas', orden=1)
        llanta = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_llantas)
        PrecioProductoFactory(lista=s['lista'], producto=llanta, precio=Decimal('500'))

        cot = Cotizacion.objects.create(
            tenant=tenant, implemento=imp, vendedor=tenant.user_set.first(),
            cliente=s['cliente'], lista=s['lista'], forma_pago=s['forma_pago'],
            numero='COT-TEST-AUTO-ROD',
        )

        response = auth_client.post(f'/{cot.id}/seleccionar/', {
            'producto_id': prod.id,
            'familia_id': fam.id,
            'orden': 1, 'accion': 'add',
        })
        # Ultimo paso tipo O auto-avance → debe ir a rodados
        assert response.status_code == 302
        assert '/rodados/0/' in response.url
