"""Tests del motor de cotización — servicios de negocio."""

import pytest
from decimal import Decimal

from apps.catalogo.tests.factories import (
    CompatibilidadFactory,
    FamiliaFactory,
    ImplementoFactory,
    ProductoFactory,
    ProductoPropiedadFactory,
    PropiedadFactory,
)
from apps.tenants.tests.factories import TenantFactory
from apps.cotizaciones.services import (
    calcular_bonificaciones,
    calcular_dimensiones,
    calcular_iva,
    calcular_totales,
    check_compatibilidad,
    check_propiedades,
    get_productos_disponibles,
    get_rodados_para_implemento,
)


# ── Dimensiones acumuladas ──────────────────────────────────────────


@pytest.mark.django_db
class TestCalcularDimensiones:
    def test_sum_longitud_acumula_correctamente(self):
        tenant = TenantFactory()
        prop_long = PropiedadFactory(tenant=tenant, nombre='Longitud', agregacion='SUM')
        p1 = ProductoFactory(tenant=tenant)
        p2 = ProductoFactory(tenant=tenant)
        ProductoPropiedadFactory(producto=p1, propiedad=prop_long, tipo='Exacto', valor=Decimal('2.5'))
        ProductoPropiedadFactory(producto=p2, propiedad=prop_long, tipo='Exacto', valor=Decimal('1.5'))

        acumulado = calcular_dimensiones([p1.id, p2.id])
        assert acumulado[prop_long.id] == Decimal('4.0')

    def test_max_altura_toma_maximo(self):
        tenant = TenantFactory()
        prop_alt = PropiedadFactory(tenant=tenant, nombre='Altura', agregacion='MAX')
        p1 = ProductoFactory(tenant=tenant)
        p2 = ProductoFactory(tenant=tenant)
        ProductoPropiedadFactory(producto=p1, propiedad=prop_alt, tipo='Exacto', valor=Decimal('770'))
        ProductoPropiedadFactory(producto=p2, propiedad=prop_alt, tipo='Exacto', valor=Decimal('870'))

        acumulado = calcular_dimensiones([p1.id, p2.id])
        assert acumulado[prop_alt.id] == Decimal('870')

    def test_sum_con_cantidad(self):
        tenant = TenantFactory()
        prop_peso = PropiedadFactory(tenant=tenant, nombre='Peso', agregacion='SUM')
        p1 = ProductoFactory(tenant=tenant)
        ProductoPropiedadFactory(producto=p1, propiedad=prop_peso, tipo='Exacto', valor=Decimal('100'))

        acumulado = calcular_dimensiones([(p1.id, 3)])
        assert acumulado[prop_peso.id] == Decimal('300')

    def test_lista_vacia_retorna_vacio(self):
        assert calcular_dimensiones([]) == {}

    def test_ignora_propiedades_min_max(self):
        tenant = TenantFactory()
        prop = PropiedadFactory(tenant=tenant, agregacion='SUM')
        p1 = ProductoFactory(tenant=tenant)
        ProductoPropiedadFactory(producto=p1, propiedad=prop, tipo='Minimo', valor=Decimal('5'))
        ProductoPropiedadFactory(producto=p1, propiedad=prop, tipo='Exacto', valor=Decimal('10'))

        acumulado = calcular_dimensiones([p1.id])
        assert acumulado[prop.id] == Decimal('10')


# ── Check de compatibilidad ─────────────────────────────────────────


@pytest.mark.django_db
class TestCheckCompatibilidad:
    def test_producto_vetado_no_aparece(self):
        tenant = TenantFactory()
        padre = ProductoFactory(tenant=tenant)
        hijo = ProductoFactory(tenant=tenant)
        CompatibilidadFactory(tenant=tenant, producto_padre=padre, producto_hijo=hijo, tipo='Vetado')

        resultado = check_compatibilidad(hijo.id, [padre.id])
        assert resultado == 'NO'

    def test_producto_forzado_aparece(self):
        tenant = TenantFactory()
        padre = ProductoFactory(tenant=tenant)
        hijo = ProductoFactory(tenant=tenant)
        CompatibilidadFactory(tenant=tenant, producto_padre=padre, producto_hijo=hijo, tipo='Forzado')

        resultado = check_compatibilidad(hijo.id, [padre.id])
        assert resultado == 'SI'

    def test_sin_regla_retorna_none(self):
        tenant = TenantFactory()
        p1 = ProductoFactory(tenant=tenant)
        p2 = ProductoFactory(tenant=tenant)

        resultado = check_compatibilidad(p2.id, [p1.id])
        assert resultado is None

    def test_ya_seleccionado_retorna_no(self):
        tenant = TenantFactory()
        p1 = ProductoFactory(tenant=tenant)

        resultado = check_compatibilidad(p1.id, [p1.id])
        assert resultado == 'NO'

    def test_seleccionados_vacio_retorna_none(self):
        tenant = TenantFactory()
        p1 = ProductoFactory(tenant=tenant)

        resultado = check_compatibilidad(p1.id, [])
        assert resultado is None


# ── Check de propiedades ─────────────────────────────────────────────


@pytest.mark.django_db
class TestCheckPropiedades:
    def test_chasis_dentro_de_rango_longitud_aparece(self):
        tenant = TenantFactory()
        prop_long = PropiedadFactory(tenant=tenant, nombre='Longitud', agregacion='SUM')
        candidato = ProductoFactory(tenant=tenant)
        # Candidato requiere longitud mín 2 y máx 5
        ProductoPropiedadFactory(producto=candidato, propiedad=prop_long, tipo='Minimo', valor=Decimal('2'))
        ProductoPropiedadFactory(producto=candidato, propiedad=prop_long, tipo='Maximo', valor=Decimal('5'))

        acumulado = {prop_long.id: Decimal('3')}
        assert check_propiedades(candidato.id, acumulado) is True

    def test_chasis_fuera_de_rango_longitud_no_aparece(self):
        tenant = TenantFactory()
        prop_long = PropiedadFactory(tenant=tenant, nombre='Longitud', agregacion='SUM')
        candidato = ProductoFactory(tenant=tenant)
        ProductoPropiedadFactory(producto=candidato, propiedad=prop_long, tipo='Maximo', valor=Decimal('3'))

        acumulado = {prop_long.id: Decimal('5')}
        assert check_propiedades(candidato.id, acumulado) is False

    def test_minimo_no_alcanzado_falla(self):
        tenant = TenantFactory()
        prop = PropiedadFactory(tenant=tenant, agregacion='SUM')
        candidato = ProductoFactory(tenant=tenant)
        ProductoPropiedadFactory(producto=candidato, propiedad=prop, tipo='Minimo', valor=Decimal('10'))

        acumulado = {prop.id: Decimal('5')}
        assert check_propiedades(candidato.id, acumulado) is False

    def test_sin_restricciones_pasa(self):
        tenant = TenantFactory()
        candidato = ProductoFactory(tenant=tenant)
        assert check_propiedades(candidato.id, {}) is True

    def test_propiedad_no_en_acumulado_usa_cero(self):
        tenant = TenantFactory()
        prop = PropiedadFactory(tenant=tenant, agregacion='SUM')
        candidato = ProductoFactory(tenant=tenant)
        ProductoPropiedadFactory(producto=candidato, propiedad=prop, tipo='Minimo', valor=Decimal('5'))

        # No hay nada acumulado → dim_actual=0 < 5 → falla
        assert check_propiedades(candidato.id, {}) is False


# ── Productos disponibles ────────────────────────────────────────────


@pytest.mark.django_db
class TestGetProductosDisponibles:
    def test_retorna_productos_del_orden(self):
        tenant = TenantFactory()
        imp = ImplementoFactory(tenant=tenant)
        fam = FamiliaFactory(tenant=tenant, implemento=imp, orden=1)
        p1 = ProductoFactory(tenant=tenant, implemento=imp, familia=fam)
        ProductoFactory(tenant=tenant, implemento=imp,
                        familia=FamiliaFactory(tenant=tenant, implemento=imp, orden=2))

        disponibles = get_productos_disponibles(imp.id, 1, [])
        assert p1 in disponibles
        assert len(disponibles) == 1

    def test_excluye_producto_vetado(self):
        tenant = TenantFactory()
        imp = ImplementoFactory(tenant=tenant)
        fam = FamiliaFactory(tenant=tenant, implemento=imp, orden=1)
        padre = ProductoFactory(tenant=tenant, implemento=imp, familia=fam)
        fam2 = FamiliaFactory(tenant=tenant, implemento=imp, orden=2)
        hijo = ProductoFactory(tenant=tenant, implemento=imp, familia=fam2)
        CompatibilidadFactory(tenant=tenant, producto_padre=padre, producto_hijo=hijo, tipo='Vetado')

        disponibles = get_productos_disponibles(imp.id, 2, [padre.id])
        assert hijo not in disponibles

    def test_incluye_producto_forzado(self):
        tenant = TenantFactory()
        imp = ImplementoFactory(tenant=tenant)
        fam = FamiliaFactory(tenant=tenant, implemento=imp, orden=1)
        padre = ProductoFactory(tenant=tenant, implemento=imp, familia=fam)
        fam2 = FamiliaFactory(tenant=tenant, implemento=imp, orden=2)
        hijo = ProductoFactory(tenant=tenant, implemento=imp, familia=fam2)
        CompatibilidadFactory(tenant=tenant, producto_padre=padre, producto_hijo=hijo, tipo='Forzado')

        disponibles = get_productos_disponibles(imp.id, 2, [padre.id])
        assert hijo in disponibles

    def test_excluye_por_propiedad_fuera_rango(self):
        tenant = TenantFactory()
        imp = ImplementoFactory(tenant=tenant)
        prop = PropiedadFactory(tenant=tenant, agregacion='SUM')
        fam1 = FamiliaFactory(tenant=tenant, implemento=imp, orden=1)
        chasis = ProductoFactory(tenant=tenant, implemento=imp, familia=fam1)
        ProductoPropiedadFactory(producto=chasis, propiedad=prop, tipo='Exacto', valor=Decimal('10'))
        fam2 = FamiliaFactory(tenant=tenant, implemento=imp, orden=2)
        accesorio = ProductoFactory(tenant=tenant, implemento=imp, familia=fam2)
        ProductoPropiedadFactory(producto=accesorio, propiedad=prop, tipo='Maximo', valor=Decimal('5'))

        acumulado = calcular_dimensiones([chasis.id])
        disponibles = get_productos_disponibles(imp.id, 2, [chasis.id], acumulado)
        assert accesorio not in disponibles


# ── Rodados automáticos ──────────────────────────────────────────────


@pytest.mark.django_db
class TestRodadosAutomaticos:
    def test_rodados_se_inyectan_con_cantidades_del_chasis(self):
        tenant = TenantFactory()
        imp = ImplementoFactory(tenant=tenant, accesorios_tipo='Rodados', nivel_rodado=1)
        imp_rodados = ImplementoFactory(tenant=tenant, nombre='Rodados')

        prop_llantas = PropiedadFactory(tenant=tenant, nombre='Llantas', agregacion='MAX')
        prop_ejes = PropiedadFactory(tenant=tenant, nombre='Ejes', agregacion='MAX')

        fam_llantas = FamiliaFactory(tenant=tenant, implemento=imp_rodados, nombre='Llantas', orden=1)
        fam_ejes = FamiliaFactory(tenant=tenant, implemento=imp_rodados, nombre='Ejes', orden=2)

        llanta = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_llantas)
        eje = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_ejes)

        chasis = ProductoFactory(tenant=tenant, implemento=imp)
        ProductoPropiedadFactory(producto=chasis, propiedad=prop_llantas, tipo='Exacto', valor=Decimal('4'))
        ProductoPropiedadFactory(producto=chasis, propiedad=prop_ejes, tipo='Exacto', valor=Decimal('2'))

        acumulado = calcular_dimensiones([chasis.id])
        rodados = get_rodados_para_implemento(imp, [chasis.id], acumulado)

        assert len(rodados) == 2
        # Llantas: 4 * nivel_rodado(1) = 4
        assert rodados[0]['cantidad'] == 4
        assert llanta in rodados[0]['productos']
        # Ejes: 2 * 1 = 2
        assert rodados[1]['cantidad'] == 2

    def test_sin_rodados_retorna_vacio(self):
        tenant = TenantFactory()
        imp = ImplementoFactory(tenant=tenant, accesorios_tipo=None)
        resultado = get_rodados_para_implemento(imp, [])
        assert resultado == []

    def test_centro_chasis_filtra_llantas_compatibles(self):
        tenant = TenantFactory()
        imp = ImplementoFactory(tenant=tenant, accesorios_tipo='Rodados', nivel_rodado=1)
        imp_rodados = ImplementoFactory(tenant=tenant, nombre='Rodados')

        prop_llantas = PropiedadFactory(tenant=tenant, nombre='Llantas', agregacion='MAX')
        prop_centro = PropiedadFactory(tenant=tenant, nombre='Centro', agregacion='MAX')

        fam_llantas = FamiliaFactory(tenant=tenant, implemento=imp_rodados, nombre='Llantas', orden=1)
        llanta_92 = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_llantas, nombre='Llanta Centro 92')
        llanta_152 = ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_llantas, nombre='Llanta Centro 152')
        # Llanta 92 requiere centro min 80, max 100
        ProductoPropiedadFactory(producto=llanta_92, propiedad=prop_centro, tipo='Minimo', valor=Decimal('80'))
        ProductoPropiedadFactory(producto=llanta_92, propiedad=prop_centro, tipo='Maximo', valor=Decimal('100'))
        # Llanta 152 requiere centro min 140, max 160
        ProductoPropiedadFactory(producto=llanta_152, propiedad=prop_centro, tipo='Minimo', valor=Decimal('140'))
        ProductoPropiedadFactory(producto=llanta_152, propiedad=prop_centro, tipo='Maximo', valor=Decimal('160'))

        chasis = ProductoFactory(tenant=tenant, implemento=imp)
        ProductoPropiedadFactory(producto=chasis, propiedad=prop_llantas, tipo='Exacto', valor=Decimal('4'))
        ProductoPropiedadFactory(producto=chasis, propiedad=prop_centro, tipo='Exacto', valor=Decimal('92'))

        acumulado = calcular_dimensiones([chasis.id])
        rodados = get_rodados_para_implemento(imp, [chasis.id], acumulado)

        llantas_disponibles = rodados[0]['productos']
        assert llanta_92 in llantas_disponibles
        assert llanta_152 not in llantas_disponibles


# ── Bonificaciones en cascada ────────────────────────────────────────


class TestCalcularBonificaciones:
    def test_bonificacion_cascada_cliente_primero_luego_pago(self):
        resultado = calcular_bonificaciones(
            subtotal_bruto=Decimal('10000'),
            bonif_cliente_pct=Decimal('10'),
            bonif_pago_pct=Decimal('5'),
        )
        # 10000 - 1000 (10%) = 9000, luego 9000 - 450 (5%) = 8550
        assert resultado['subtotal_neto'] == Decimal('8550.00')
        assert resultado['bonif_cliente_monto'] == Decimal('1000.00')
        assert resultado['bonif_pago_monto'] == Decimal('450.00')

    def test_sin_bonificaciones(self):
        resultado = calcular_bonificaciones(
            subtotal_bruto=Decimal('5000'),
            bonif_cliente_pct=Decimal('0'),
            bonif_pago_pct=Decimal('0'),
        )
        assert resultado['subtotal_neto'] == Decimal('5000.00')
        assert resultado['bonif_cliente_monto'] == Decimal('0.00')
        assert resultado['bonif_pago_monto'] == Decimal('0.00')

    def test_solo_bonif_cliente(self):
        resultado = calcular_bonificaciones(
            subtotal_bruto=Decimal('10000'),
            bonif_cliente_pct=Decimal('20'),
            bonif_pago_pct=Decimal('0'),
        )
        assert resultado['subtotal_neto'] == Decimal('8000.00')

    def test_bonificaciones_sin_tope(self):
        resultado = calcular_bonificaciones(
            subtotal_bruto=Decimal('10000'),
            bonif_cliente_pct=Decimal('20'),
            bonif_pago_pct=Decimal('15'),
        )
        # Sin tope, se aplican tal cual en cascada
        assert resultado['bonif_cliente_pct'] == Decimal('20')
        assert resultado['bonif_pago_pct'] == Decimal('15')


# ── IVA por alícuota ─────────────────────────────────────────────────


class TestCalcularIva:
    def test_iva_desglosa_por_alicuota_105_y_21(self):
        items = [
            {'precio_linea': Decimal('1000'), 'iva_porcentaje': Decimal('21.00')},
            {'precio_linea': Decimal('2000'), 'iva_porcentaje': Decimal('10.50')},
        ]
        resultado = calcular_iva(items, Decimal('3000'), Decimal('3000'))

        assert Decimal('21.00') in resultado['desglose']
        assert Decimal('10.50') in resultado['desglose']
        assert resultado['desglose'][Decimal('21.00')]['monto'] == Decimal('210.00')
        assert resultado['desglose'][Decimal('10.50')]['monto'] == Decimal('210.00')
        assert resultado['iva_total'] == Decimal('420.00')

    def test_iva_proporcional_post_bonificacion(self):
        items = [
            {'precio_linea': Decimal('5000'), 'iva_porcentaje': Decimal('21.00')},
            {'precio_linea': Decimal('5000'), 'iva_porcentaje': Decimal('10.50')},
        ]
        # 50% de descuento: bruto=10000, neto=5000
        resultado = calcular_iva(items, Decimal('10000'), Decimal('5000'))

        assert resultado['desglose'][Decimal('21.00')]['base'] == Decimal('2500.00')
        assert resultado['desglose'][Decimal('21.00')]['monto'] == Decimal('525.00')
        assert resultado['desglose'][Decimal('10.50')]['base'] == Decimal('2500.00')
        assert resultado['desglose'][Decimal('10.50')]['monto'] == Decimal('262.50')

    def test_iva_con_bruto_cero(self):
        resultado = calcular_iva([], Decimal('0'), Decimal('0'))
        assert resultado['iva_total'] == Decimal('0')

    def test_iva_una_sola_alicuota(self):
        items = [
            {'precio_linea': Decimal('1000'), 'iva_porcentaje': Decimal('21.00')},
            {'precio_linea': Decimal('2000'), 'iva_porcentaje': Decimal('21.00')},
        ]
        resultado = calcular_iva(items, Decimal('3000'), Decimal('3000'))
        assert len(resultado['desglose']) == 1
        assert resultado['desglose'][Decimal('21.00')]['monto'] == Decimal('630.00')


# ── Cálculo de totales ───────────────────────────────────────────────


class TestCalcularTotales:
    def test_total_es_neto_mas_iva(self):
        items = [
            {'precio_linea': Decimal('10000'), 'iva_porcentaje': Decimal('21.00')},
        ]
        resultado = calcular_totales(items, Decimal('10'), Decimal('5'))

        # Bruto: 10000
        # Bonif cliente: 10000 * 10% = 1000 → 9000
        # Bonif pago: 9000 * 5% = 450 → 8550
        # IVA 21%: 8550 * 0.21 = 1795.50
        # Total: 8550 + 1795.50 = 10345.50
        assert resultado['subtotal_bruto'] == Decimal('10000')
        assert resultado['subtotal_neto'] == Decimal('8550.00')
        assert resultado['iva_21_base'] == Decimal('8550.00')
        assert resultado['iva_21_monto'] == Decimal('1795.50')
        assert resultado['precio_total'] == Decimal('10345.50')

    def test_total_con_dos_alicuotas(self):
        items = [
            {'precio_linea': Decimal('6000'), 'iva_porcentaje': Decimal('21.00')},
            {'precio_linea': Decimal('4000'), 'iva_porcentaje': Decimal('10.50')},
        ]
        resultado = calcular_totales(items, Decimal('0'), Decimal('0'))

        assert resultado['subtotal_bruto'] == Decimal('10000')
        assert resultado['subtotal_neto'] == Decimal('10000.00')
        assert resultado['iva_21_base'] == Decimal('6000.00')
        assert resultado['iva_21_monto'] == Decimal('1260.00')
        assert resultado['iva_105_base'] == Decimal('4000.00')
        assert resultado['iva_105_monto'] == Decimal('420.00')
        assert resultado['iva_total'] == Decimal('1680.00')
        assert resultado['precio_total'] == Decimal('11680.00')

    def test_total_con_comision(self):
        items = [
            {'precio_linea': Decimal('10000'), 'iva_porcentaje': Decimal('21.00')},
        ]
        resultado = calcular_totales(
            items, Decimal('10'), Decimal('5'),
            bonif_cliente_default=Decimal('10'),
            bonif_pago_default=Decimal('5'),
            usuario_bonif_max=Decimal('15'),
            usuario_comision_pct=Decimal('5'),
            comision_impacto_bonif=Decimal('0.60'),
        )
        # Sin bonif extra (real == default), comision = 5% full
        assert resultado['comision_porcentaje_efectivo'] == Decimal('5.00')
        # subtotal_neto = 8550, comision = 8550 * 5% = 427.50
        assert resultado['comision_monto'] == Decimal('427.50')

    def test_total_sin_items(self):
        resultado = calcular_totales([], Decimal('0'), Decimal('0'))
        assert resultado['subtotal_bruto'] == Decimal('0')
        assert resultado['precio_total'] == Decimal('0')

    def test_total_campos_iva_105_vacios_si_no_hay(self):
        items = [
            {'precio_linea': Decimal('1000'), 'iva_porcentaje': Decimal('21.00')},
        ]
        resultado = calcular_totales(items, Decimal('0'), Decimal('0'))
        assert resultado['iva_105_base'] == Decimal('0')
        assert resultado['iva_105_monto'] == Decimal('0')


# ── Comisiones ───────────────────────────────────────────────────────


class TestCalcularComision:
    def test_comision_sin_bonif_extra(self):
        from apps.cotizaciones.services import calcular_comision
        result = calcular_comision(
            subtotal_neto=Decimal('10000'),
            bonif_cliente_real=Decimal('15'), bonif_pago_real=Decimal('10'),
            bonif_cliente_default=Decimal('15'), bonif_pago_default=Decimal('10'),
            usuario_bonif_max=Decimal('15'), usuario_comision_pct=Decimal('5'),
            comision_impacto_bonif=Decimal('0.60'),
        )
        # No usó extra → comision full 5%
        assert result['comision_porcentaje_efectivo'] == Decimal('5.00')
        assert result['comision_monto'] == Decimal('500.00')

    def test_comision_con_bonif_extra_total(self):
        from apps.cotizaciones.services import calcular_comision
        result = calcular_comision(
            subtotal_neto=Decimal('10000'),
            bonif_cliente_real=Decimal('22.5'), bonif_pago_real=Decimal('17.5'),
            bonif_cliente_default=Decimal('15'), bonif_pago_default=Decimal('10'),
            usuario_bonif_max=Decimal('15'), usuario_comision_pct=Decimal('5'),
            comision_impacto_bonif=Decimal('0.60'),
        )
        # Usó 7.5 + 7.5 = 15 de 15 max → 100% uso → reduccion = 0.60
        # comision = 5 * (1 - 0.60) = 2.00
        assert result['comision_porcentaje_efectivo'] == Decimal('2.00')
        assert result['comision_monto'] == Decimal('200.00')

    def test_comision_con_bonif_extra_parcial(self):
        from apps.cotizaciones.services import calcular_comision
        result = calcular_comision(
            subtotal_neto=Decimal('10000'),
            bonif_cliente_real=Decimal('18.75'), bonif_pago_real=Decimal('10'),
            bonif_cliente_default=Decimal('15'), bonif_pago_default=Decimal('10'),
            usuario_bonif_max=Decimal('15'), usuario_comision_pct=Decimal('5'),
            comision_impacto_bonif=Decimal('0.60'),
        )
        # Extra usada = 3.75 de 15 → 25% uso → reduccion = 0.25 * 0.60 = 0.15
        # comision = 5 * (1 - 0.15) = 4.25
        assert result['comision_porcentaje_efectivo'] == Decimal('4.25')

    def test_comision_cero_si_usuario_sin_comision(self):
        from apps.cotizaciones.services import calcular_comision
        result = calcular_comision(
            subtotal_neto=Decimal('10000'),
            bonif_cliente_real=Decimal('15'), bonif_pago_real=Decimal('10'),
            bonif_cliente_default=Decimal('15'), bonif_pago_default=Decimal('10'),
            usuario_bonif_max=Decimal('0'), usuario_comision_pct=Decimal('0'),
            comision_impacto_bonif=Decimal('0.60'),
        )
        assert result['comision_porcentaje_efectivo'] == Decimal('0.00')
        assert result['comision_monto'] == Decimal('0.00')


# ── Tests de bugs corregidos ─────────────────────────────────────────


@pytest.mark.django_db
class TestDimensionesMultiplesProductos:
    """Bug 5: bauleras múltiples deben sumar longitud correctamente."""

    def test_suma_longitud_dos_bauleras(self):
        tenant = TenantFactory()
        prop_long = PropiedadFactory(tenant=tenant, nombre='Longitud', agregacion='SUM')
        b1 = ProductoFactory(tenant=tenant, nombre='Baulera 750')
        b2 = ProductoFactory(tenant=tenant, nombre='Baulera 1700')
        ProductoPropiedadFactory(producto=b1, propiedad=prop_long, tipo='Exacto', valor=Decimal('0.75'))
        ProductoPropiedadFactory(producto=b2, propiedad=prop_long, tipo='Exacto', valor=Decimal('1.70'))

        acumulado = calcular_dimensiones([b1.id, b2.id])
        assert acumulado[prop_long.id] == Decimal('2.45')

    def test_filtro_chasis_por_longitud_acumulada(self):
        """Bug 1: chasis deben filtrarse por longitud acumulada de tanque+baulera."""
        tenant = TenantFactory()
        prop_long = PropiedadFactory(tenant=tenant, nombre='Longitud', agregacion='SUM')
        imp = ImplementoFactory(tenant=tenant)

        # Tanque y baulera en pasos previos
        fam_tanque = FamiliaFactory(tenant=tenant, implemento=imp, orden=1)
        tanque = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_tanque)
        ProductoPropiedadFactory(producto=tanque, propiedad=prop_long, tipo='Exacto', valor=Decimal('3.20'))

        fam_baulera = FamiliaFactory(tenant=tenant, implemento=imp, orden=2, tipo_seleccion='Y')
        baulera = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_baulera)
        ProductoPropiedadFactory(producto=baulera, propiedad=prop_long, tipo='Exacto', valor=Decimal('0.75'))

        # Chasis en paso 3
        fam_chasis = FamiliaFactory(tenant=tenant, implemento=imp, orden=3)
        chasis_ok = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_chasis, nombre='L4000')
        ProductoPropiedadFactory(producto=chasis_ok, propiedad=prop_long, tipo='Minimo', valor=Decimal('3.80'))
        ProductoPropiedadFactory(producto=chasis_ok, propiedad=prop_long, tipo='Maximo', valor=Decimal('4.00'))

        chasis_chico = ProductoFactory(tenant=tenant, implemento=imp, familia=fam_chasis, nombre='L1400')
        ProductoPropiedadFactory(producto=chasis_chico, propiedad=prop_long, tipo='Minimo', valor=Decimal('1.20'))
        ProductoPropiedadFactory(producto=chasis_chico, propiedad=prop_long, tipo='Maximo', valor=Decimal('1.40'))

        # Acumulado: 3.20 + 0.75 = 3.95
        seleccionados = [tanque.id, baulera.id]
        acumulado = calcular_dimensiones(seleccionados)
        assert acumulado[prop_long.id] == Decimal('3.95')

        disponibles = get_productos_disponibles(imp.id, 3, seleccionados, acumulado)
        assert chasis_ok in disponibles
        assert chasis_chico not in disponibles


@pytest.mark.django_db
class TestRodadosConNivelMultiple:
    """Bug 3: rodados con nivel > 1 multiplican cantidades."""

    def test_cantidad_rodados_viene_del_chasis(self):
        """La cantidad de rodados es el valor de la propiedad del chasis (no * nivel)."""
        tenant = TenantFactory()
        imp = ImplementoFactory(tenant=tenant, accesorios_tipo='Rodados', nivel_rodado=3)
        imp_rodados = ImplementoFactory(tenant=tenant, nombre='Rodados')

        prop_llantas = PropiedadFactory(tenant=tenant, nombre='Llantas', agregacion='MAX')
        fam_llantas = FamiliaFactory(tenant=tenant, implemento=imp_rodados, nombre='Llantas', orden=1)
        ProductoFactory(tenant=tenant, implemento=imp_rodados, familia=fam_llantas)

        chasis = ProductoFactory(tenant=tenant, implemento=imp)
        ProductoPropiedadFactory(producto=chasis, propiedad=prop_llantas, tipo='Exacto', valor=Decimal('4'))

        acumulado = calcular_dimensiones([chasis.id])
        rodados = get_rodados_para_implemento(imp, [chasis.id], acumulado)

        # Cantidad = valor propiedad Llantas del chasis (4), no multiplicado por nivel
        assert rodados[0]['cantidad'] == 4
