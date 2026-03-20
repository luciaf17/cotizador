"""
Tests de funcionalidades nuevas:
- Prearmado rápido en cotización
- Prearmado como base al crear prearmado
- Link web en productos
- Orden de items
- Rodados condicionales
"""

import pytest
from decimal import Decimal

from django.test import Client as TestClient

from apps.accounts.models import User
from apps.catalogo.models import (
    Familia, Implemento, Producto, ProductoPropiedad, Propiedad,
)
from apps.clientes.models import Cliente, FormaPago, TipoCliente
from apps.cotizaciones.models import Cotizacion, CotizacionItem
from apps.cotizaciones.services import calcular_dimensiones, get_rodados_para_implemento
from apps.precios.models import (
    EstructuraPrearmado, ListaPrecio, Prearmado, PrecioProducto,
)
from apps.tenants.models import Tenant


@pytest.fixture
def setup_completo():
    t = Tenant.objects.create(nombre='Test', slug='test-fn')
    u = User.objects.create_user(
        email='dueno@fn.com', password='test123', nombre='Dueno',
        tenant=t, rol='dueno', is_staff=True,
        bonif_max_porcentaje=Decimal('10'), comision_porcentaje=Decimal('5'),
    )
    tipo = TipoCliente.objects.create(tenant=t, nombre='Conc', bonificacion_default=10)
    cli = Cliente.objects.create(tenant=t, tipo_cliente=tipo, nombre='Cliente', bonificacion_porcentaje=10)
    fp = FormaPago.objects.create(tenant=t, nombre='Contado', bonificacion_porcentaje=5)
    imp = Implemento.objects.create(tenant=t, nombre='Acoplados', accesorios_tipo='Rodados', nivel_rodado=1)

    prop_long = Propiedad.objects.create(tenant=t, nombre='Longitud', unidad='mts', agregacion='SUM')
    prop_llantas = Propiedad.objects.create(tenant=t, nombre='Llantas', unidad='u', agregacion='MAX')

    # Familias con distintos ordenes
    fam1 = Familia.objects.create(tenant=t, implemento=imp, nombre='Tanques', orden=1, tipo_seleccion='O', obligatoria='SI')
    fam2 = Familia.objects.create(tenant=t, implemento=imp, nombre='Bauleras', orden=2, tipo_seleccion='Y', obligatoria='NO')
    fam3 = Familia.objects.create(tenant=t, implemento=imp, nombre='Chasis', orden=3, tipo_seleccion='O', obligatoria='SI')

    tanque = Producto.objects.create(tenant=t, implemento=imp, familia=fam1, nombre='Tanque 2000')
    ProductoPropiedad.objects.create(producto=tanque, propiedad=prop_long, tipo='Exacto', valor=Decimal('2.0'))

    baulera = Producto.objects.create(tenant=t, implemento=imp, familia=fam2, nombre='Baulera 750')
    ProductoPropiedad.objects.create(producto=baulera, propiedad=prop_long, tipo='Exacto', valor=Decimal('0.75'))

    chasis = Producto.objects.create(tenant=t, implemento=imp, familia=fam3, nombre='Chasis L2000',
                                      link_web='https://example.com/chasis')
    ProductoPropiedad.objects.create(producto=chasis, propiedad=prop_long, tipo='Minimo', valor=Decimal('1.8'))
    ProductoPropiedad.objects.create(producto=chasis, propiedad=prop_long, tipo='Maximo', valor=Decimal('3.0'))
    ProductoPropiedad.objects.create(producto=chasis, propiedad=prop_llantas, tipo='Exacto', valor=Decimal('2'))

    prod_sin_link = Producto.objects.create(tenant=t, implemento=imp, familia=fam1, nombre='Tanque 1000')

    lista = ListaPrecio.objects.create(tenant=t, numero=1, estado='vigente', creada_por=u)
    for prod in [tanque, baulera, chasis, prod_sin_link]:
        PrecioProducto.objects.create(lista=lista, producto=prod, precio=Decimal('1000000'))

    # Prearmado
    pre = Prearmado.objects.create(tenant=t, implemento=imp, nombre='Pre Estandar')
    EstructuraPrearmado.objects.create(prearmado=pre, producto=tanque, cantidad=1)
    EstructuraPrearmado.objects.create(prearmado=pre, producto=baulera, cantidad=1)
    EstructuraPrearmado.objects.create(prearmado=pre, producto=chasis, cantidad=1)

    # Rodados
    imp_rod = Implemento.objects.create(tenant=t, nombre='Rodados')
    fam_llantas = Familia.objects.create(tenant=t, implemento=imp_rod, nombre='Llantas', orden=1, obligatoria='SI')
    llanta = Producto.objects.create(tenant=t, implemento=imp_rod, familia=fam_llantas, nombre='Llanta 16')
    PrecioProducto.objects.create(lista=lista, producto=llanta, precio=Decimal('100000'))

    client = TestClient()
    client.force_login(u)

    return {
        't': t, 'u': u, 'cli': cli, 'fp': fp, 'imp': imp, 'lista': lista,
        'fam1': fam1, 'fam2': fam2, 'fam3': fam3,
        'tanque': tanque, 'baulera': baulera, 'chasis': chasis,
        'prod_sin_link': prod_sin_link, 'pre': pre,
        'prop_llantas': prop_llantas, 'client': client,
    }


def _crear_cotizacion(s):
    """Crea cotización via la view (muestra prearmado rápido si hay prearmados)."""
    response = s['client'].get(f'/nuevo/{s["cli"].id}/{s["imp"].id}/')
    return Cotizacion.objects.filter(tenant=s['t']).last(), response


# ── Prearmado rápido en cotización ───────────────────────────────────


@pytest.mark.django_db
class TestPrearmadoRapidoCotizacion:
    def test_muestra_paso_prearmado_si_hay_prearmados(self, setup_completo):
        s = setup_completo
        cot, response = _crear_cotizacion(s)
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Usar un prearmado como base' in content
        assert 'Pre Estandar' in content

    def test_cargar_prearmado_crea_items(self, setup_completo):
        s = setup_completo
        cot, _ = _crear_cotizacion(s)

        response = s['client'].post(f'/{cot.id}/cargar-prearmado/', {
            'prearmado_id': s['pre'].id,
        })
        assert response.status_code == 302
        assert 'bonificaciones' in response.url

        items = CotizacionItem.objects.filter(cotizacion=cot)
        assert items.count() == 3
        nombres = set(items.values_list('producto__nombre', flat=True))
        assert 'Tanque 2000' in nombres
        assert 'Baulera 750' in nombres
        assert 'Chasis L2000' in nombres

    def test_cotizar_desde_cero_va_a_paso_1(self, setup_completo):
        s = setup_completo
        cot, _ = _crear_cotizacion(s)

        response = s['client'].post(f'/{cot.id}/cargar-prearmado/', {
            'prearmado_id': '',
        })
        assert response.status_code == 302
        assert '/paso/1/' in response.url
        assert CotizacionItem.objects.filter(cotizacion=cot).count() == 0

    def test_prearmado_cargado_puede_volver_a_editar(self, setup_completo):
        s = setup_completo
        cot, _ = _crear_cotizacion(s)

        s['client'].post(f'/{cot.id}/cargar-prearmado/', {
            'prearmado_id': s['pre'].id,
        })

        # Puede ir a bonificaciones
        response = s['client'].get(f'/{cot.id}/bonificaciones/')
        assert response.status_code == 200

        # Puede volver a un paso para modificar
        response = s['client'].get(f'/{cot.id}/paso/1/')
        assert response.status_code == 200

        # Puede volver a bonificaciones
        response = s['client'].get(f'/{cot.id}/bonificaciones/')
        assert response.status_code == 200

    def test_prearmado_cargado_puede_aprobar(self, setup_completo):
        s = setup_completo
        cot, _ = _crear_cotizacion(s)

        s['client'].post(f'/{cot.id}/cargar-prearmado/', {
            'prearmado_id': s['pre'].id,
        })

        # Bonificaciones
        s['client'].post(f'/{cot.id}/bonificaciones/', {
            'bonif_cliente_pct': '10',
            'bonif_pago_pct': '5',
            'forma_pago_id': s['fp'].id,
        })

        cot.refresh_from_db()
        assert cot.subtotal_bruto > 0

        # Aprobar
        s['client'].post(f'/{cot.id}/aprobar/')
        cot.refresh_from_db()
        assert cot.estado == 'aprobada'


# ── Prearmado como base al crear prearmado ───────────────────────────


@pytest.mark.django_db
class TestPrearmadoComoBase:
    def test_base_carga_estructura(self, setup_completo):
        s = setup_completo

        response = s['client'].get(f'/gestion/prearmados/crear/?base={s["pre"].id}')
        assert response.status_code == 200
        content = response.content.decode()
        # Debe tener los productos del prearmado base precargados
        assert 'Tanque 2000' in content
        assert 'Baulera 750' in content
        assert 'Chasis L2000' in content

    def test_sin_base_formulario_vacio(self, setup_completo):
        s = setup_completo

        response = s['client'].get('/gestion/prearmados/crear/')
        assert response.status_code == 200
        content = response.content.decode()
        # No debe tener productos precargados (solo el selector vacio)
        assert 'Usar como base' in content


# ── Link web en productos ────────────────────────────────────────────


@pytest.mark.django_db
class TestLinkWebProductos:
    def test_link_aparece_en_paso_si_producto_tiene_link(self, setup_completo):
        s = setup_completo
        cot, _ = _crear_cotizacion(s)
        s['client'].post(f'/{cot.id}/cargar-prearmado/', {'prearmado_id': ''})

        # Seleccionar tanque primero para que chasis pase filtro dimensional
        s['client'].post(f'/{cot.id}/seleccionar/', {
            'producto_id': s['tanque'].id,
            'familia_id': s['fam1'].id,
            'orden': 1, 'accion': 'add',
        })

        response = s['client'].get(f'/{cot.id}/paso/3/')
        content = response.content.decode()
        # chasis tiene link_web
        assert 'https://example.com/chasis' in content
        assert '8599' in content

    def test_link_no_aparece_si_producto_no_tiene_link(self, setup_completo):
        s = setup_completo
        cot, _ = _crear_cotizacion(s)
        s['client'].post(f'/{cot.id}/cargar-prearmado/', {'prearmado_id': ''})

        response = s['client'].get(f'/{cot.id}/paso/1/')
        content = response.content.decode()
        # Tanque 1000 no tiene link_web - verificar que no hay link spurio
        assert 'Tanque 1000' in content
        # No debería haber link para Tanque 1000
        assert 'example.com' not in content

    def test_link_aparece_en_resumen(self, setup_completo):
        s = setup_completo
        cot, _ = _crear_cotizacion(s)
        s['client'].post(f'/{cot.id}/cargar-prearmado/', {
            'prearmado_id': s['pre'].id,
        })
        s['client'].post(f'/{cot.id}/bonificaciones/', {
            'bonif_cliente_pct': '10',
            'bonif_pago_pct': '5',
            'forma_pago_id': s['fp'].id,
        })

        response = s['client'].get(f'/{cot.id}/resumen/')
        content = response.content.decode()
        assert 'https://example.com/chasis' in content


# ── Orden de items ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestOrdenItems:
    def test_items_ordenados_por_familia_orden_en_resumen(self, setup_completo):
        s = setup_completo
        cot, _ = _crear_cotizacion(s)

        # Crear items en orden inverso para verificar que se reordenan
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['chasis'], familia=s['fam3'],
            cantidad=1, precio_unitario=1000000, precio_linea=1000000, iva_porcentaje=21,
        )
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['tanque'], familia=s['fam1'],
            cantidad=1, precio_unitario=1000000, precio_linea=1000000, iva_porcentaje=21,
        )
        CotizacionItem.objects.create(
            cotizacion=cot, producto=s['baulera'], familia=s['fam2'],
            cantidad=1, precio_unitario=1000000, precio_linea=1000000, iva_porcentaje=21,
        )

        response = s['client'].get(f'/{cot.id}/resumen/')
        content = response.content.decode()

        # Tanque (orden 1) debe aparecer antes que Baulera (orden 2) antes que Chasis (orden 3)
        pos_tanque = content.find('Tanque 2000')
        pos_baulera = content.find('Baulera 750')
        pos_chasis = content.find('Chasis L2000')

        assert pos_tanque < pos_baulera < pos_chasis


# ── Rodados condicionales por dimensiones ────────────────────────────


@pytest.mark.django_db
class TestRodadosCondicionales:
    def test_llantas_cero_no_muestra_paso(self, setup_completo):
        s = setup_completo
        # Producto SIN propiedad Llantas
        prod_sin_llantas = Producto.objects.create(
            tenant=s['t'], implemento=s['imp'],
            familia=s['fam1'], nombre='Producto Sin Llantas',
        )

        acum = calcular_dimensiones([prod_sin_llantas.id])
        rodados = get_rodados_para_implemento(s['imp'], [prod_sin_llantas.id], acum)
        assert len(rodados) == 0

    def test_llantas_mayor_cero_muestra_paso(self, setup_completo):
        s = setup_completo
        # Chasis tiene Llantas=2
        acum = calcular_dimensiones([s['chasis'].id])
        assert acum.get(s['prop_llantas'].id, 0) == Decimal('2')

        rodados = get_rodados_para_implemento(s['imp'], [s['chasis'].id], acum)
        assert len(rodados) >= 1
        llantas_step = [r for r in rodados if 'llanta' in r['familia'].nombre.lower()]
        assert len(llantas_step) == 1
        assert llantas_step[0]['cantidad'] == 2
