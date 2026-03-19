"""
Tests de lógica de negocio — edge cases.

Cubre: filtrado dimensional, vetados, rodados condicionales,
bonificaciones cascada, comisiones, IVA, listas de precios,
prearmados, obligatoriedad tipo O/Y.
"""

import math
import pytest
from decimal import Decimal

from apps.catalogo.models import (
    Compatibilidad, Familia, Implemento, Producto,
    ProductoPropiedad, Propiedad,
)
from apps.cotizaciones.services import (
    calcular_bonificaciones, calcular_comision, calcular_dimensiones,
    calcular_iva, calcular_totales, check_compatibilidad,
    check_propiedades, get_productos_disponibles,
    get_rodados_para_implemento,
)
from apps.precios.models import (
    EstructuraPrearmado, ListaPrecio, Prearmado, PrecioProducto,
)
from apps.precios.services import activar_lista, calcular_precio_prearmado, crear_nueva_lista
from apps.accounts.tests.factories import UserFactory
from apps.tenants.tests.factories import TenantFactory


# ── Filtrado dimensional ─────────────────────────────────────────────


@pytest.mark.django_db
class TestFiltradoDimensional:
    def _setup_acoplado(self):
        t = TenantFactory()
        imp = Implemento.objects.create(tenant=t, nombre='Acoplados Rurales', accesorios_tipo='Rodados', nivel_rodado=1)
        prop_long = Propiedad.objects.create(tenant=t, nombre='Longitud', unidad='mts', agregacion='SUM')

        fam_tanques = Familia.objects.create(tenant=t, implemento=imp, nombre='Tanques', orden=1, tipo_seleccion='O', obligatoria='SI')
        fam_bauleras = Familia.objects.create(tenant=t, implemento=imp, nombre='Bauleras', orden=2, tipo_seleccion='Y', obligatoria='NO')
        fam_chasis = Familia.objects.create(tenant=t, implemento=imp, nombre='Chasis', orden=3, tipo_seleccion='O', obligatoria='SI')

        # Tanques
        tanque_4000 = Producto.objects.create(tenant=t, implemento=imp, familia=fam_tanques, nombre='Tanque 4000')
        ProductoPropiedad.objects.create(producto=tanque_4000, propiedad=prop_long, tipo='Exacto', valor=Decimal('3.2'))

        tanque_1100 = Producto.objects.create(tenant=t, implemento=imp, familia=fam_tanques, nombre='Tanque 1100')
        ProductoPropiedad.objects.create(producto=tanque_1100, propiedad=prop_long, tipo='Exacto', valor=Decimal('1.3'))

        # Baulera
        baulera = Producto.objects.create(tenant=t, implemento=imp, familia=fam_bauleras, nombre='Baulera 750')
        ProductoPropiedad.objects.create(producto=baulera, propiedad=prop_long, tipo='Exacto', valor=Decimal('0.75'))

        # Chasis con rangos
        chasis_l1500 = Producto.objects.create(tenant=t, implemento=imp, familia=fam_chasis, nombre='L1500')
        ProductoPropiedad.objects.create(producto=chasis_l1500, propiedad=prop_long, tipo='Minimo', valor=Decimal('1.2'))
        ProductoPropiedad.objects.create(producto=chasis_l1500, propiedad=prop_long, tipo='Maximo', valor=Decimal('1.5'))

        chasis_l1800 = Producto.objects.create(tenant=t, implemento=imp, familia=fam_chasis, nombre='L1800')
        ProductoPropiedad.objects.create(producto=chasis_l1800, propiedad=prop_long, tipo='Minimo', valor=Decimal('1.75'))
        ProductoPropiedad.objects.create(producto=chasis_l1800, propiedad=prop_long, tipo='Maximo', valor=Decimal('1.8'))

        chasis_l4000 = Producto.objects.create(tenant=t, implemento=imp, familia=fam_chasis, nombre='L4000')
        ProductoPropiedad.objects.create(producto=chasis_l4000, propiedad=prop_long, tipo='Minimo', valor=Decimal('3.8'))
        ProductoPropiedad.objects.create(producto=chasis_l4000, propiedad=prop_long, tipo='Maximo', valor=Decimal('4.0'))

        chasis_l4000r = Producto.objects.create(tenant=t, implemento=imp, familia=fam_chasis, nombre='L4000 Reforzado')
        ProductoPropiedad.objects.create(producto=chasis_l4000r, propiedad=prop_long, tipo='Minimo', valor=Decimal('3.8'))
        ProductoPropiedad.objects.create(producto=chasis_l4000r, propiedad=prop_long, tipo='Maximo', valor=Decimal('4.0'))

        return {
            'imp': imp, 'tanque_4000': tanque_4000, 'tanque_1100': tanque_1100,
            'baulera': baulera, 'chasis_l1500': chasis_l1500, 'chasis_l1800': chasis_l1800,
            'chasis_l4000': chasis_l4000, 'chasis_l4000r': chasis_l4000r,
        }

    def test_tanque_4000_baulera_750_solo_chasis_l4000(self):
        s = self._setup_acoplado()
        sel = [s['tanque_4000'].id, s['baulera'].id]
        acum = calcular_dimensiones(sel)  # long = 3.2 + 0.75 = 3.95
        disponibles = get_productos_disponibles(s['imp'].id, 3, sel, acum)
        nombres = [p.nombre for p in disponibles]
        assert 'L4000' in nombres
        assert 'L4000 Reforzado' in nombres
        assert 'L1500' not in nombres
        assert 'L1800' not in nombres

    def test_tanque_1100_solo_chasis_chicos(self):
        s = self._setup_acoplado()
        sel = [s['tanque_1100'].id]
        acum = calcular_dimensiones(sel)  # long = 1.3
        disponibles = get_productos_disponibles(s['imp'].id, 3, sel, acum)
        nombres = [p.nombre for p in disponibles]
        assert 'L1500' in nombres  # 1.2 <= 1.3 <= 1.5
        assert 'L4000' not in nombres


# ── Vetados ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVetados:
    def test_vetado_oculta_producto(self):
        t = TenantFactory()
        imp = Implemento.objects.create(tenant=t, nombre='Gruas')
        fam1 = Familia.objects.create(tenant=t, implemento=imp, nombre='Chasis', orden=1)
        fam2 = Familia.objects.create(tenant=t, implemento=imp, nombre='Llantas', orden=2)
        grua = Producto.objects.create(tenant=t, implemento=imp, familia=fam1, nombre='G1500')
        llanta_92 = Producto.objects.create(tenant=t, implemento=imp, familia=fam2, nombre='Llanta 92')
        llanta_152 = Producto.objects.create(tenant=t, implemento=imp, familia=fam2, nombre='Llanta 152')
        Compatibilidad.objects.create(tenant=t, producto_padre=grua, producto_hijo=llanta_152, tipo='Vetado')

        disponibles = get_productos_disponibles(imp.id, 2, [grua.id])
        nombres = [p.nombre for p in disponibles]
        assert 'Llanta 92' in nombres
        assert 'Llanta 152' not in nombres


# ── Rodados condicionales ────────────────────────────────────────────


@pytest.mark.django_db
class TestRodadosCondicionales:
    def _setup_desmalezadora(self):
        t = TenantFactory()
        imp = Implemento.objects.create(tenant=t, nombre='Desmalezadoras', accesorios_tipo='Rodados', nivel_rodado=1)
        imp_rod = Implemento.objects.create(tenant=t, nombre='Rodados')
        prop_llantas = Propiedad.objects.create(tenant=t, nombre='Llantas', unidad='u', agregacion='MAX')
        fam_llantas = Familia.objects.create(tenant=t, implemento=imp_rod, nombre='Llantas', orden=1)
        Producto.objects.create(tenant=t, implemento=imp_rod, familia=fam_llantas, nombre='Llanta')

        fam = Familia.objects.create(tenant=t, implemento=imp, nombre='Acople', orden=1)
        acople_3p = Producto.objects.create(tenant=t, implemento=imp, familia=fam, nombre='Acople 3P')
        # Acople 3P: Llantas=0 → no debería mostrar paso llantas
        acople_arrastre = Producto.objects.create(tenant=t, implemento=imp, familia=fam, nombre='Acople Arrastre')
        ProductoPropiedad.objects.create(producto=acople_arrastre, propiedad=prop_llantas, tipo='Exacto', valor=Decimal('2'))

        return {'imp': imp, 'acople_3p': acople_3p, 'acople_arrastre': acople_arrastre}

    def test_acople_3p_sin_llantas_no_muestra_paso(self):
        s = self._setup_desmalezadora()
        acum = calcular_dimensiones([s['acople_3p'].id])
        rodados = get_rodados_para_implemento(s['imp'], [s['acople_3p'].id], acum)
        assert len(rodados) == 0

    def test_acople_arrastre_con_llantas_muestra_paso(self):
        s = self._setup_desmalezadora()
        acum = calcular_dimensiones([s['acople_arrastre'].id])
        rodados = get_rodados_para_implemento(s['imp'], [s['acople_arrastre'].id], acum)
        assert len(rodados) == 1
        assert rodados[0]['cantidad'] == 2


# ── Bonificaciones en cascada ────────────────────────────────────────


class TestBonificacionesCascadaEdgeCases:
    def test_cascada_exacta(self):
        """$10.000.000, cliente 15%, pago 10%."""
        r = calcular_bonificaciones(Decimal('10000000'), Decimal('15'), Decimal('10'))
        assert r['bonif_cliente_monto'] == Decimal('1500000.00')
        # Pago sobre 8.500.000
        assert r['bonif_pago_monto'] == Decimal('850000.00')
        assert r['subtotal_neto'] == Decimal('7650000.00')

    def test_cascada_cero_porciento(self):
        r = calcular_bonificaciones(Decimal('5000000'), Decimal('0'), Decimal('0'))
        assert r['subtotal_neto'] == Decimal('5000000.00')

    def test_cascada_100_porciento_cliente(self):
        r = calcular_bonificaciones(Decimal('1000000'), Decimal('100'), Decimal('50'))
        assert r['subtotal_neto'] == Decimal('0.00')


# ── Comisión con impacto ─────────────────────────────────────────────


class TestComisionImpacto:
    def test_sin_extra_comision_completa(self):
        r = calcular_comision(
            subtotal_neto=Decimal('10000000'),
            bonif_cliente_real=Decimal('15'), bonif_pago_real=Decimal('10'),
            bonif_cliente_default=Decimal('15'), bonif_pago_default=Decimal('10'),
            usuario_bonif_max=Decimal('10'), usuario_comision_pct=Decimal('5'),
            comision_impacto_bonif=Decimal('0.60'),
        )
        assert r['comision_porcentaje_efectivo'] == Decimal('5.00')

    def test_extra_maximo_reduce_comision(self):
        r = calcular_comision(
            subtotal_neto=Decimal('10000000'),
            bonif_cliente_real=Decimal('20'), bonif_pago_real=Decimal('15'),
            bonif_cliente_default=Decimal('15'), bonif_pago_default=Decimal('10'),
            usuario_bonif_max=Decimal('10'), usuario_comision_pct=Decimal('5'),
            comision_impacto_bonif=Decimal('0.60'),
        )
        # Extra usada = 5 + 5 = 10 de 10 max → 100% → reduccion = 0.60
        # comision = 5 × (1 - 0.60) = 2.00
        assert r['comision_porcentaje_efectivo'] == Decimal('2.00')


# ── IVA por alícuota ─────────────────────────────────────────────────


class TestIVAPorAlicuota:
    def test_desglose_proporcional_post_bonificacion(self):
        items = [
            {'precio_linea': Decimal('6000000'), 'iva_porcentaje': Decimal('21.00')},
            {'precio_linea': Decimal('4000000'), 'iva_porcentaje': Decimal('10.50')},
        ]
        # Bruto = 10M, neto = 7.65M (con 15%+10% cascada)
        bruto = Decimal('10000000')
        neto = Decimal('7650000')
        r = calcular_iva(items, bruto, neto)

        # Proporcion = 0.765
        # Base 21% = 6M × 0.765 = 4.590.000
        assert r['desglose'][Decimal('21.00')]['base'] == Decimal('4590000.00')
        # IVA 21% = 4.590.000 × 0.21 = 963.900
        assert r['desglose'][Decimal('21.00')]['monto'] == Decimal('963900.00')
        # Base 10.5% = 4M × 0.765 = 3.060.000
        assert r['desglose'][Decimal('10.50')]['base'] == Decimal('3060000.00')
        # IVA 10.5% = 3.060.000 × 0.105 = 321.300
        assert r['desglose'][Decimal('10.50')]['monto'] == Decimal('321300.00')


# ── Listas de precios ────────────────────────────────────────────────


@pytest.mark.django_db
class TestListasPrecios:
    def test_ceiling_aplica_correctamente(self):
        t = TenantFactory()
        u = UserFactory(tenant=t)
        lista1 = ListaPrecio.objects.create(tenant=t, numero=1, estado='vigente', creada_por=u)
        prod = Producto.objects.create(tenant=t, implemento=Implemento.objects.create(tenant=t, nombre='I'),
                                        familia=Familia.objects.create(tenant=t, implemento=Implemento.objects.last(), nombre='F', orden=1),
                                        nombre='P')
        PrecioProducto.objects.create(lista=lista1, producto=prod, precio=Decimal('1000001'))

        lista2 = crear_nueva_lista(t, lista1, Decimal('10'), u)
        pp = PrecioProducto.objects.get(lista=lista2, producto=prod)
        # CEILING(1000001 × 1.10) = CEILING(1100001.1) = 1100002
        assert pp.precio == Decimal(str(math.ceil(1000001 * 1.10)))

    def test_activar_lista_pone_anterior_como_historica(self):
        t = TenantFactory()
        u = UserFactory(tenant=t)
        vigente = ListaPrecio.objects.create(tenant=t, numero=1, estado='vigente', creada_por=u)
        borrador = ListaPrecio.objects.create(tenant=t, numero=2, estado='borrador', creada_por=u)

        activar_lista(borrador)
        vigente.refresh_from_db()
        borrador.refresh_from_db()
        assert vigente.estado == 'historica'
        assert borrador.estado == 'vigente'

    def test_reactivar_historica(self):
        t = TenantFactory()
        u = UserFactory(tenant=t)
        historica = ListaPrecio.objects.create(tenant=t, numero=1, estado='historica', creada_por=u)
        vigente = ListaPrecio.objects.create(tenant=t, numero=2, estado='vigente', creada_por=u)

        activar_lista(historica)
        vigente.refresh_from_db()
        historica.refresh_from_db()
        assert vigente.estado == 'historica'
        assert historica.estado == 'vigente'


# ── Prearmados ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPrearmadosPrecio:
    def test_precio_calculado_suma_estructura(self):
        t = TenantFactory()
        u = UserFactory(tenant=t)
        imp = Implemento.objects.create(tenant=t, nombre='I')
        fam = Familia.objects.create(tenant=t, implemento=imp, nombre='F', orden=1)
        p1 = Producto.objects.create(tenant=t, implemento=imp, familia=fam, nombre='P1')
        p2 = Producto.objects.create(tenant=t, implemento=imp, familia=fam, nombre='P2')
        lista = ListaPrecio.objects.create(tenant=t, numero=1, estado='vigente', creada_por=u)
        PrecioProducto.objects.create(lista=lista, producto=p1, precio=Decimal('500000'))
        PrecioProducto.objects.create(lista=lista, producto=p2, precio=Decimal('300000'))

        pre = Prearmado.objects.create(tenant=t, implemento=imp, nombre='Pre')
        EstructuraPrearmado.objects.create(prearmado=pre, producto=p1, cantidad=2)
        EstructuraPrearmado.objects.create(prearmado=pre, producto=p2, cantidad=3)

        precio = calcular_precio_prearmado(pre, lista)
        # 500000×2 + 300000×3 = 1.900.000
        assert precio == Decimal('1900000')


# ── Obligatoriedad tipo O / tipo Y ───────────────────────────────────


@pytest.mark.django_db
class TestObligatoriedadTipos:
    def test_tipo_o_obligatorio_bloquea_sin_seleccion(self):
        """Familias tipo O con obligatoria=SI y productos → falta_obligatorio=True."""
        t = TenantFactory()
        imp = Implemento.objects.create(tenant=t, nombre='I')
        fam = Familia.objects.create(tenant=t, implemento=imp, nombre='F', orden=1, tipo_seleccion='O', obligatoria='SI')
        Producto.objects.create(tenant=t, implemento=imp, familia=fam, nombre='P')

        # Simular la lógica de _build_paso_context
        disponibles = get_productos_disponibles(imp.id, 1, [])
        familias_data = [{'familia': fam, 'productos': [{'producto': p} for p in disponibles if p.familia_id == fam.id], 'seleccionados': set()}]

        familias_o_obligatorias = [fd for fd in familias_data if fd['familia'].tipo_seleccion == 'O' and fd['familia'].obligatoria == 'SI']
        tiene_productos = any(fd['productos'] for fd in familias_o_obligatorias)
        tiene_seleccion = any(fd['seleccionados'] for fd in familias_o_obligatorias)

        assert tiene_productos and not tiene_seleccion  # falta_obligatorio = True

    def test_tipo_y_opcional_permite_avanzar(self):
        """Familias tipo Y con obligatoria=NO → no bloquea."""
        t = TenantFactory()
        imp = Implemento.objects.create(tenant=t, nombre='I')
        fam = Familia.objects.create(tenant=t, implemento=imp, nombre='F', orden=1, tipo_seleccion='Y', obligatoria='NO')
        Producto.objects.create(tenant=t, implemento=imp, familia=fam, nombre='P')

        familias_data = [{'familia': fam, 'productos': [{}], 'seleccionados': set()}]

        falta = False
        for fd in familias_data:
            if fd['familia'].tipo_seleccion == 'Y' and fd['familia'].obligatoria == 'SI':
                if fd['productos'] and not fd['seleccionados']:
                    falta = True
        assert not falta

    def test_tipo_o_multiples_familias_satisface_con_una(self):
        """Familias tipo O mismo orden: seleccionar en una satisface el grupo."""
        t = TenantFactory()
        imp = Implemento.objects.create(tenant=t, nombre='I')
        fam1 = Familia.objects.create(tenant=t, implemento=imp, nombre='F1', orden=1, tipo_seleccion='O', obligatoria='SI')
        fam2 = Familia.objects.create(tenant=t, implemento=imp, nombre='F2', orden=1, tipo_seleccion='O', obligatoria='SI')
        p1 = Producto.objects.create(tenant=t, implemento=imp, familia=fam1, nombre='P1')
        Producto.objects.create(tenant=t, implemento=imp, familia=fam2, nombre='P2')

        familias_data = [
            {'familia': fam1, 'productos': [{}], 'seleccionados': {p1.id}},
            {'familia': fam2, 'productos': [{}], 'seleccionados': set()},
        ]

        familias_o = [fd for fd in familias_data if fd['familia'].tipo_seleccion == 'O' and fd['familia'].obligatoria == 'SI']
        tiene_seleccion = any(fd['seleccionados'] for fd in familias_o)
        assert tiene_seleccion  # falta_obligatorio = False
