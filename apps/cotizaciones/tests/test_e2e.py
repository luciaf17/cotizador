"""
Tests de integración end-to-end del cotizador.

Cubren el flujo completo desde la view: selección de productos,
filtrado por propiedades entre pasos, rodados automáticos,
bonificaciones con tope, y acumulación de dimensiones.
"""

import pytest
from decimal import Decimal

from django.test import Client as TestClient

from apps.accounts.tests.factories import UserFactory
from apps.catalogo.tests.factories import (
    CompatibilidadFactory,
    FamiliaFactory,
    ImplementoFactory,
    ProductoFactory,
    ProductoPropiedadFactory,
    PropiedadFactory,
)
from apps.clientes.tests.factories import (
    ClienteFactory,
    FormaPagoFactory,
    TipoClienteFactory,
)
from apps.cotizaciones.models import Cotizacion, CotizacionItem
from apps.precios.tests.factories import ListaPrecioFactory, PrecioProductoFactory
from apps.tenants.tests.factories import TenantFactory


@pytest.fixture
def e2e_setup():
    """Setup completo que simula un escenario real tipo Ceibo."""
    tenant = TenantFactory(bonif_max_porcentaje=Decimal('30'))
    user = UserFactory(tenant=tenant, is_staff=True)
    tipo = TipoClienteFactory(tenant=tenant, nombre='Concesionario', bonificacion_default=Decimal('15'))
    cliente = ClienteFactory(tenant=tenant, tipo_cliente=tipo, bonificacion_porcentaje=Decimal('15'))
    lista = ListaPrecioFactory(tenant=tenant, estado='vigente', creada_por=user)
    forma_pago = FormaPagoFactory(tenant=tenant, nombre='Contado', bonificacion_porcentaje=Decimal('10'))

    # Propiedades
    prop_long = PropiedadFactory(tenant=tenant, nombre='Longitud', unidad='mts', agregacion='SUM')
    prop_peso = PropiedadFactory(tenant=tenant, nombre='Peso', unidad='kg', agregacion='SUM')
    prop_altura = PropiedadFactory(tenant=tenant, nombre='Altura', unidad='mm', agregacion='MAX')
    prop_llantas = PropiedadFactory(tenant=tenant, nombre='Llantas', unidad='u', agregacion='MAX')
    prop_ejes = PropiedadFactory(tenant=tenant, nombre='Ejes', unidad='u', agregacion='MAX')
    prop_elasticos = PropiedadFactory(tenant=tenant, nombre='Elasticos', unidad='u', agregacion='MAX')
    prop_centro = PropiedadFactory(tenant=tenant, nombre='Centro', unidad='mm', agregacion='MAX')

    # Implemento con rodados
    imp = ImplementoFactory(tenant=tenant, nombre='Acoplados Rurales', accesorios_tipo='Rodados', nivel_rodado=1)

    # Paso 1: Tanques (tipo O, obligatoria SI)
    fam_tanques = FamiliaFactory(tenant=tenant, implemento=imp, nombre='Tanques', orden=1, tipo_seleccion='O', obligatoria='SI')
    tanque_2000 = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_tanques, nombre='Tanque 2000 lts')
    ProductoPropiedadFactory(producto=tanque_2000, propiedad=prop_long, tipo='Exacto', valor=Decimal('2.0'))
    ProductoPropiedadFactory(producto=tanque_2000, propiedad=prop_peso, tipo='Exacto', valor=Decimal('1800'))
    ProductoPropiedadFactory(producto=tanque_2000, propiedad=prop_altura, tipo='Exacto', valor=Decimal('770'))
    PrecioProductoFactory(lista=lista, producto=tanque_2000, precio=Decimal('1500000'))

    tanque_4000 = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_tanques, nombre='Tanque 4000 lts')
    ProductoPropiedadFactory(producto=tanque_4000, propiedad=prop_long, tipo='Exacto', valor=Decimal('3.2'))
    ProductoPropiedadFactory(producto=tanque_4000, propiedad=prop_peso, tipo='Exacto', valor=Decimal('3500'))
    ProductoPropiedadFactory(producto=tanque_4000, propiedad=prop_altura, tipo='Exacto', valor=Decimal('870'))
    PrecioProductoFactory(lista=lista, producto=tanque_4000, precio=Decimal('2500000'))

    # Paso 2: Bauleras (tipo Y, obligatoria NO)
    fam_bauleras = FamiliaFactory(tenant=tenant, implemento=imp, nombre='Bauleras', orden=2, tipo_seleccion='Y', obligatoria='NO')
    baulera_750 = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_bauleras, nombre='Baulera 750')
    ProductoPropiedadFactory(producto=baulera_750, propiedad=prop_long, tipo='Exacto', valor=Decimal('0.75'))
    PrecioProductoFactory(lista=lista, producto=baulera_750, precio=Decimal('500000'))

    baulera_1000 = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_bauleras, nombre='Baulera 1000')
    ProductoPropiedadFactory(producto=baulera_1000, propiedad=prop_long, tipo='Exacto', valor=Decimal('1.0'))
    PrecioProductoFactory(lista=lista, producto=baulera_1000, precio=Decimal('700000'))

    # Paso 3: Chasis (tipo O, obligatoria SI) — con restricciones Min/Max
    fam_chasis_1eje = FamiliaFactory(tenant=tenant, implemento=imp, nombre='Chasis 1 Eje', orden=3, tipo_seleccion='O', obligatoria='SI')
    fam_chasis_2ejes = FamiliaFactory(tenant=tenant, implemento=imp, nombre='Chasis 2 Ejes', orden=3, tipo_seleccion='O', obligatoria='SI')

    chasis_l1500 = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_chasis_1eje, nombre='Chasis L1500')
    ProductoPropiedadFactory(producto=chasis_l1500, propiedad=prop_long, tipo='Minimo', valor=Decimal('1.45'))
    ProductoPropiedadFactory(producto=chasis_l1500, propiedad=prop_long, tipo='Maximo', valor=Decimal('1.50'))
    ProductoPropiedadFactory(producto=chasis_l1500, propiedad=prop_llantas, tipo='Exacto', valor=Decimal('2'))
    ProductoPropiedadFactory(producto=chasis_l1500, propiedad=prop_ejes, tipo='Exacto', valor=Decimal('1'))
    ProductoPropiedadFactory(producto=chasis_l1500, propiedad=prop_elasticos, tipo='Exacto', valor=Decimal('2'))
    ProductoPropiedadFactory(producto=chasis_l1500, propiedad=prop_centro, tipo='Exacto', valor=Decimal('92'))
    PrecioProductoFactory(lista=lista, producto=chasis_l1500, precio=Decimal('800000'))

    chasis_l4000 = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_chasis_2ejes, nombre='Chasis L4000')
    ProductoPropiedadFactory(producto=chasis_l4000, propiedad=prop_long, tipo='Minimo', valor=Decimal('3.80'))
    ProductoPropiedadFactory(producto=chasis_l4000, propiedad=prop_long, tipo='Maximo', valor=Decimal('4.00'))
    ProductoPropiedadFactory(producto=chasis_l4000, propiedad=prop_llantas, tipo='Exacto', valor=Decimal('4'))
    ProductoPropiedadFactory(producto=chasis_l4000, propiedad=prop_ejes, tipo='Exacto', valor=Decimal('2'))
    ProductoPropiedadFactory(producto=chasis_l4000, propiedad=prop_elasticos, tipo='Exacto', valor=Decimal('4'))
    ProductoPropiedadFactory(producto=chasis_l4000, propiedad=prop_centro, tipo='Exacto', valor=Decimal('92'))
    PrecioProductoFactory(lista=lista, producto=chasis_l4000, precio=Decimal('2000000'))

    # Rodados (implemento separado "Rodados")
    imp_rodados = ImplementoFactory(tenant=tenant, nombre='Rodados')
    fam_llantas = FamiliaFactory(tenant=tenant, implemento=imp_rodados, nombre='Llantas', orden=1, tipo_seleccion='O', obligatoria='SI')
    fam_ejes = FamiliaFactory(tenant=tenant, implemento=imp_rodados, nombre='Ejes', orden=2, tipo_seleccion='O', obligatoria='SI')
    fam_elasticos = FamiliaFactory(tenant=tenant, implemento=imp_rodados, nombre='Elasticos', orden=3, tipo_seleccion='O', obligatoria='SI')

    llanta_92 = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_llantas, nombre='Llanta Centro 92')
    ProductoPropiedadFactory(producto=llanta_92, propiedad=prop_centro, tipo='Minimo', valor=Decimal('80'))
    ProductoPropiedadFactory(producto=llanta_92, propiedad=prop_centro, tipo='Maximo', valor=Decimal('100'))
    PrecioProductoFactory(lista=lista, producto=llanta_92, precio=Decimal('120000'))

    llanta_152 = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_llantas, nombre='Llanta Centro 152')
    ProductoPropiedadFactory(producto=llanta_152, propiedad=prop_centro, tipo='Minimo', valor=Decimal('140'))
    ProductoPropiedadFactory(producto=llanta_152, propiedad=prop_centro, tipo='Maximo', valor=Decimal('160'))
    PrecioProductoFactory(lista=lista, producto=llanta_152, precio=Decimal('150000'))

    eje = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_ejes, nombre='Eje Standard')
    PrecioProductoFactory(lista=lista, producto=eje, precio=Decimal('400000'))

    elastico = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_elasticos, nombre='Elastico Standard')
    PrecioProductoFactory(lista=lista, producto=elastico, precio=Decimal('100000'))

    client = TestClient()
    client.force_login(user)

    return {
        'tenant': tenant, 'user': user, 'cliente': cliente, 'lista': lista,
        'forma_pago': forma_pago, 'imp': imp,
        'tanque_2000': tanque_2000, 'tanque_4000': tanque_4000,
        'baulera_750': baulera_750, 'baulera_1000': baulera_1000,
        'chasis_l1500': chasis_l1500, 'chasis_l4000': chasis_l4000,
        'fam_tanques': fam_tanques, 'fam_bauleras': fam_bauleras,
        'fam_chasis_1eje': fam_chasis_1eje, 'fam_chasis_2ejes': fam_chasis_2ejes,
        'llanta_92': llanta_92, 'llanta_152': llanta_152,
        'eje': eje, 'elastico': elastico,
        'prop_long': prop_long, 'prop_centro': prop_centro,
        'client': client,
    }


def _crear_cotizacion(e2e):
    """Helper: crear cotización y retornar id."""
    e2e['client'].get(f'/nuevo/{e2e["cliente"].id}/{e2e["imp"].id}/')
    return Cotizacion.objects.filter(tenant=e2e['tenant']).last()


@pytest.mark.django_db
class TestFlujoCompletoE2E:
    """Flujo completo: tanque → bauleras → chasis filtrado → rodados → bonificaciones → aprobación."""

    def test_flujo_tanque_4000_filtra_chasis_correctamente(self, e2e_setup):
        """Seleccionar Tanque 4000 + Baulera 750 → solo chasis con rango 3.80-4.00."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        # Paso 1: seleccionar Tanque 4000 (tipo O, auto-avanza)
        response = s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['tanque_4000'].id,
            'familia_id': s['fam_tanques'].id,
            'orden': 1, 'accion': 'add',
        })
        # No auto-avanza porque hay 2+ ordenes y tipo O con 1 familia → auto-avance al paso 2
        assert response.status_code == 200  # HX-Redirect
        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 1

        # Paso 2: seleccionar Baulera 750 (tipo Y, redirect al mismo paso)
        response = s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['baulera_750'].id,
            'familia_id': s['fam_bauleras'].id,
            'orden': 2, 'accion': 'add',
        })
        assert response.status_code == 302
        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 2

        # Paso 3: verificar que el chasis filtra por longitud acumulada (3.2 + 0.75 = 3.95)
        response = s['client'].get(f'/{cot.id}/paso/3/')
        content = response.content.decode()
        # Chasis L4000 (rango 3.80-4.00) debe aparecer — 3.95 está en rango
        assert 'Chasis L4000' in content
        # Chasis L1500 (rango 1.45-1.50) NO debe aparecer — 3.95 > 1.50
        assert 'Chasis L1500' not in content

    def test_flujo_tanque_2000_solo_ve_chasis_chicos(self, e2e_setup):
        """Con Tanque 2000 (long=2.0) sin baulera, solo chasis con rango que contenga 2.0."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['tanque_2000'].id,
            'familia_id': s['fam_tanques'].id,
            'orden': 1, 'accion': 'add',
        })

        # Ir directo al paso 3 (sin bauleras)
        response = s['client'].get(f'/{cot.id}/paso/3/')
        content = response.content.decode()
        # Acumulado long = 2.0
        # L1500: rango 1.45-1.50 → 2.0 > 1.50 → NO aparece
        # L4000: rango 3.80-4.00 → 2.0 < 3.80 → NO aparece
        assert 'Chasis L1500' not in content
        assert 'Chasis L4000' not in content

    def test_dimensiones_se_acumulan_con_multiples_bauleras(self, e2e_setup):
        """Seleccionar 2 bauleras suma sus longitudes."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        # Seleccionar tanque
        s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['tanque_4000'].id,
            'familia_id': s['fam_tanques'].id,
            'orden': 1, 'accion': 'add',
        })

        # Seleccionar baulera 750 (long=0.75)
        s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['baulera_750'].id,
            'familia_id': s['fam_bauleras'].id,
            'orden': 2, 'accion': 'add',
        })

        # Seleccionar baulera 1000 (long=1.0)
        s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['baulera_1000'].id,
            'familia_id': s['fam_bauleras'].id,
            'orden': 2, 'accion': 'add',
        })

        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 3

        # Paso 3: acumulado = 3.2 + 0.75 + 1.0 = 4.95
        # L4000 rango 3.80-4.00 → 4.95 > 4.00 → NO aparece
        response = s['client'].get(f'/{cot.id}/paso/3/')
        content = response.content.decode()
        assert 'Chasis L4000' not in content
        assert 'Chasis L1500' not in content

        # Verificar dimensiones en sidebar
        assert '4.95' in content or '4,95' in content

    def test_sidebar_muestra_dimensiones_actualizadas(self, e2e_setup):
        """El sidebar muestra dimensiones despues de seleccionar productos."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['tanque_4000'].id,
            'familia_id': s['fam_tanques'].id,
            'orden': 1, 'accion': 'add',
        })

        # Paso 2: la pagina deberia mostrar dimensiones del tanque
        response = s['client'].get(f'/{cot.id}/paso/2/')
        content = response.content.decode()
        # Longitud del tanque 4000 = 3.2
        assert '3.2' in content or '3,2' in content


@pytest.mark.django_db
class TestRodadosE2E:
    def test_rodados_aparecen_despues_del_ultimo_paso(self, e2e_setup):
        """Despues de chasis, el Continuar lleva a rodados."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        # Seleccionar tanque 4000 + baulera 750 (long total = 3.95)
        s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['tanque_4000'].id,
            'familia_id': s['fam_tanques'].id,
            'orden': 1, 'accion': 'add',
        })
        s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['baulera_750'].id,
            'familia_id': s['fam_bauleras'].id,
            'orden': 2, 'accion': 'add',
        })

        # Verificar que el boton continuar del paso 3 apunta a rodados
        response = s['client'].get(f'/{cot.id}/paso/3/')
        content = response.content.decode()
        assert '/rodados/0/' in content or 'bonificaciones' in content

    def test_rodados_filtran_llantas_por_centro(self, e2e_setup):
        """Solo llantas compatibles con el centro del chasis aparecen."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        # Tanque + baulera + chasis L4000 (centro=92)
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['tanque_4000'], familia=s['fam_tanques'],
            cantidad=1, precio_unitario=Decimal('2500000'),
            precio_linea=Decimal('2500000'), iva_porcentaje=Decimal('21'),
        )
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['baulera_750'], familia=s['fam_bauleras'],
            cantidad=1, precio_unitario=Decimal('500000'),
            precio_linea=Decimal('500000'), iva_porcentaje=Decimal('21'),
        )
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['chasis_l4000'], familia=s['fam_chasis_2ejes'],
            cantidad=1, precio_unitario=Decimal('2000000'),
            precio_linea=Decimal('2000000'), iva_porcentaje=Decimal('21'),
        )

        response = s['client'].get(f'/{cot.id}/rodados/0/')
        content = response.content.decode()
        # Llantas: centro del chasis = 92
        # Llanta Centro 92 (rango 80-100) → aparece
        assert 'Llanta Centro 92' in content
        # Llanta Centro 152 (rango 140-160) → NO aparece
        assert 'Llanta Centro 152' not in content

    def test_rodados_cantidad_segun_chasis(self, e2e_setup):
        """Las cantidades de rodados vienen de las propiedades del chasis."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        # Chasis L4000: llantas=4, ejes=2, elasticos=4
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['chasis_l4000'], familia=s['fam_chasis_2ejes'],
            cantidad=1, precio_unitario=Decimal('2000000'),
            precio_linea=Decimal('2000000'), iva_porcentaje=Decimal('21'),
        )

        response = s['client'].get(f'/{cot.id}/rodados/0/')
        content = response.content.decode()
        # Debe mostrar x4 para llantas
        assert 'x4' in content


@pytest.mark.django_db
class TestBonificacionesE2E:
    def test_bonificacion_no_supera_bonif_max(self, e2e_setup):
        """El calculo server-side limita la bonificacion combinada al bonif_max."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['tanque_4000'], familia=s['fam_tanques'],
            cantidad=1, precio_unitario=Decimal('2500000'),
            precio_linea=Decimal('2500000'), iva_porcentaje=Decimal('21'),
        )

        # Intentar 20% cliente + 20% pago = 40% > bonif_max(30%)
        response = s['client'].post(f'/{cot.id}/bonificaciones/', {
            'bonif_cliente_pct': '20',
            'bonif_pago_pct': '20',
            'forma_pago_id': s['forma_pago'].id,
        })
        assert response.status_code == 302

        cot.refresh_from_db()
        # Debe reducir proporcionalmente: 15 + 15 = 30
        total_bonif = cot.bonif_cliente_pct + cot.bonif_pago_pct
        assert total_bonif <= Decimal('30.00')

    def test_slider_max_es_bonif_max_del_tenant(self, e2e_setup):
        """El slider HTML tiene max=bonif_max, no 100."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['tanque_4000'], familia=s['fam_tanques'],
            cantidad=1, precio_unitario=Decimal('2500000'),
            precio_linea=Decimal('2500000'), iva_porcentaje=Decimal('21'),
        )

        response = s['client'].get(f'/{cot.id}/bonificaciones/')
        content = response.content.decode()
        assert 'max="30' in content
        assert 'max="100"' not in content

    def test_aprobacion_completa(self, e2e_setup):
        """Una cotizacion con totales calculados puede aprobarse."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['tanque_4000'], familia=s['fam_tanques'],
            cantidad=1, precio_unitario=Decimal('2500000'),
            precio_linea=Decimal('2500000'), iva_porcentaje=Decimal('21'),
        )

        # Bonificaciones
        s['client'].post(f'/{cot.id}/bonificaciones/', {
            'bonif_cliente_pct': '15',
            'bonif_pago_pct': '10',
            'forma_pago_id': s['forma_pago'].id,
        })

        cot.refresh_from_db()
        assert cot.subtotal_bruto == Decimal('2500000')
        assert cot.precio_total > 0

        # Aprobar
        s['client'].post(f'/{cot.id}/aprobar/')
        cot.refresh_from_db()
        assert cot.estado == 'aprobada'


@pytest.mark.django_db
class TestResumenSeleccionesE2E:
    def test_resumen_lateral_muestra_items_seleccionados(self, e2e_setup):
        """El sidebar muestra los productos seleccionados."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['tanque_4000'], familia=s['fam_tanques'],
            cantidad=1, precio_unitario=Decimal('2500000'),
            precio_linea=Decimal('2500000'), iva_porcentaje=Decimal('21'),
        )
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['baulera_750'], familia=s['fam_bauleras'],
            cantidad=1, precio_unitario=Decimal('500000'),
            precio_linea=Decimal('500000'), iva_porcentaje=Decimal('21'),
        )

        response = s['client'].get(f'/{cot.id}/paso/3/')
        content = response.content.decode()
        assert 'Tanque 4000 lts' in content
        assert 'Baulera 750' in content
        assert 'Seleccionados' in content

    def test_quitar_item_opcional_funciona(self, e2e_setup):
        """Se puede quitar un item de familia con obligatoria=NO."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['tanque_4000'], familia=s['fam_tanques'],
            cantidad=1, precio_unitario=Decimal('2500000'),
            precio_linea=Decimal('2500000'), iva_porcentaje=Decimal('21'),
        )
        item_baulera = CotizacionItem.objects.create(
            cotizacion=cot, producto=s['baulera_750'], familia=s['fam_bauleras'],
            cantidad=1, precio_unitario=Decimal('500000'),
            precio_linea=Decimal('500000'), iva_porcentaje=Decimal('21'),
        )

        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 2

        # Quitar la baulera (obligatoria=NO)
        response = s['client'].post(f'/{cot.id}/quitar-item/{item_baulera.id}/')
        assert response.status_code == 302
        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 1

    def test_no_puede_quitar_item_obligatorio(self, e2e_setup):
        """No se puede quitar un item de familia con obligatoria=SI."""
        s = e2e_setup
        cot = _crear_cotizacion(s)

        item_tanque = CotizacionItem.objects.create(
            cotizacion=cot, producto=s['tanque_4000'], familia=s['fam_tanques'],
            cantidad=1, precio_unitario=Decimal('2500000'),
            precio_linea=Decimal('2500000'), iva_porcentaje=Decimal('21'),
        )

        # Intentar quitar el tanque (obligatoria=SI) → no se borra
        s['client'].post(f'/{cot.id}/quitar-item/{item_tanque.id}/')
        assert CotizacionItem.objects.filter(cotizacion=cot, id=item_tanque.id).exists()
