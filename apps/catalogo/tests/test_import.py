"""Tests para verificar la integridad de los datos importados desde Excel."""

import pytest
from decimal import Decimal

from django.core.management import call_command

from apps.catalogo.models import (
    Compatibilidad,
    Familia,
    Implemento,
    Producto,
    ProductoPropiedad,
    Propiedad,
)
from apps.clientes.models import FormaPago, TipoCliente
from apps.precios.models import (
    EstructuraPrearmado,
    ListaPrecio,
    Prearmado,
    PrecioProducto,
)
from apps.tenants.models import Tenant


@pytest.fixture(scope='session')
def django_db_setup(django_test_environment, django_db_blocker):
    """Ejecutar import_ceibo una vez para toda la sesión de tests."""
    with django_db_blocker.unblock():
        call_command('import_ceibo')


@pytest.fixture
def ceibo(django_db_setup):
    return Tenant.objects.get(slug='ceibo')


@pytest.mark.django_db
class TestImportConteos:
    def test_tenant_ceibo_existe(self, ceibo):
        assert ceibo is not None
        assert ceibo.nombre == 'Metalúrgica Ceibo'

    def test_implementos_count(self, ceibo):
        assert Implemento.objects.filter(tenant=ceibo).count() == 11

    def test_familias_count(self, ceibo):
        assert Familia.objects.filter(tenant=ceibo).count() == 31

    def test_productos_count(self, ceibo):
        assert Producto.objects.filter(tenant=ceibo).count() == 153

    def test_propiedades_count(self, ceibo):
        assert Propiedad.objects.filter(tenant=ceibo).count() == 10

    def test_producto_propiedades_count(self, ceibo):
        assert ProductoPropiedad.objects.filter(
            producto__tenant=ceibo,
        ).count() == 333

    def test_compatibilidades_count(self, ceibo):
        assert Compatibilidad.objects.filter(tenant=ceibo).count() == 5

    def test_prearmados_count(self, ceibo):
        assert Prearmado.objects.filter(tenant=ceibo).count() == 51

    def test_estructuras_count(self, ceibo):
        assert EstructuraPrearmado.objects.filter(
            prearmado__tenant=ceibo,
        ).count() == 183

    def test_lista_precio_81_existe(self, ceibo):
        lista = ListaPrecio.objects.get(tenant=ceibo, numero=81)
        assert lista.estado == 'vigente'

    def test_precios_productos_count(self, ceibo):
        lista = ListaPrecio.objects.get(tenant=ceibo, numero=81)
        assert PrecioProducto.objects.filter(lista=lista).count() == 153

    def test_tipos_cliente_count(self, ceibo):
        assert TipoCliente.objects.filter(tenant=ceibo).count() == 3

    def test_formas_pago_count(self, ceibo):
        assert FormaPago.objects.filter(tenant=ceibo).count() == 4


@pytest.mark.django_db
class TestImportRelaciones:
    def test_implemento_con_rodados(self, ceibo):
        desmalezadoras = Implemento.objects.get(tenant=ceibo, nombre='Desmalezadoras')
        assert desmalezadoras.accesorios_tipo == 'Rodados'
        assert desmalezadoras.nivel_rodado == 1

    def test_implemento_sin_rodados(self, ceibo):
        elevadores = Implemento.objects.get(tenant=ceibo, nombre='Elevadores Frontales')
        assert elevadores.accesorios_tipo is None
        assert elevadores.nivel_rodado is None

    def test_familia_pertenece_a_implemento(self, ceibo):
        fam = Familia.objects.filter(tenant=ceibo).first()
        assert fam.implemento is not None
        assert fam.implemento.tenant == ceibo

    def test_producto_pertenece_a_familia_e_implemento(self, ceibo):
        prod = Producto.objects.filter(tenant=ceibo).first()
        assert prod.familia is not None
        assert prod.implemento is not None

    def test_producto_propiedad_relaciones(self, ceibo):
        pp = ProductoPropiedad.objects.filter(producto__tenant=ceibo).first()
        assert pp.producto is not None
        assert pp.propiedad is not None

    def test_compatibilidad_vetado(self, ceibo):
        comp = Compatibilidad.objects.filter(tenant=ceibo).first()
        assert comp.tipo == 'Vetado'
        assert comp.producto_padre is not None
        assert comp.producto_hijo is not None

    def test_prearmado_tiene_estructura(self, ceibo):
        pre = Prearmado.objects.filter(tenant=ceibo).first()
        assert pre.estructura.count() > 0

    def test_precio_producto_vinculado_a_lista(self, ceibo):
        lista = ListaPrecio.objects.get(tenant=ceibo, numero=81)
        pp = PrecioProducto.objects.filter(lista=lista).first()
        assert pp.producto is not None
        assert pp.precio >= 0


@pytest.mark.django_db
class TestImportDatos:
    def test_propiedades_agregacion_correcta(self, ceibo):
        longitud = Propiedad.objects.get(tenant=ceibo, nombre='Longitud')
        assert longitud.agregacion == 'SUM'
        peso = Propiedad.objects.get(tenant=ceibo, nombre='Peso')
        assert peso.agregacion == 'SUM'
        altura = Propiedad.objects.get(tenant=ceibo, nombre='Altura')
        assert altura.agregacion == 'MAX'
        centro = Propiedad.objects.get(tenant=ceibo, nombre='Centro')
        assert centro.agregacion == 'MAX'

    def test_familia_tipo_seleccion_valido(self, ceibo):
        for fam in Familia.objects.filter(tenant=ceibo):
            assert fam.tipo_seleccion in ('O', 'Y')
            assert fam.obligatoria in ('SI', 'NO')

    def test_tipo_cliente_bonificacion(self, ceibo):
        conc = TipoCliente.objects.get(tenant=ceibo, nombre='Concesionario')
        assert conc.bonificacion_default == Decimal('15.00')

    def test_forma_pago_bonificacion(self, ceibo):
        contado = FormaPago.objects.get(tenant=ceibo, nombre='Contado')
        assert contado.bonificacion_porcentaje == Decimal('15.00')

    def test_idempotencia_import(self, ceibo):
        """El import puede ejecutarse múltiples veces sin duplicar datos."""
        count_antes = Implemento.objects.filter(tenant=ceibo).count()
        call_command('import_ceibo', verbosity=0)
        count_despues = Implemento.objects.filter(tenant=ceibo).count()
        assert count_antes == count_despues
