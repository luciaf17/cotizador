import pytest

from .factories import (
    CompatibilidadFactory,
    FamiliaFactory,
    ImplementoFactory,
    ProductoFactory,
    ProductoPropiedadFactory,
    PropiedadFactory,
)


@pytest.mark.django_db
class TestImplemento:
    def test_crear_implemento(self):
        imp = ImplementoFactory()
        assert imp.pk is not None

    def test_str(self):
        imp = ImplementoFactory(nombre='Elevadores Frontales')
        assert str(imp) == 'Elevadores Frontales'

    def test_con_rodados(self):
        imp = ImplementoFactory(accesorios_tipo='Rodados', nivel_rodado=1)
        assert imp.accesorios_tipo == 'Rodados'
        assert imp.nivel_rodado == 1


@pytest.mark.django_db
class TestFamilia:
    def test_crear_familia(self):
        fam = FamiliaFactory()
        assert fam.pk is not None
        assert fam.implemento is not None

    def test_tipo_seleccion(self):
        fam_o = FamiliaFactory(tipo_seleccion='O')
        fam_y = FamiliaFactory(tipo_seleccion='Y')
        assert fam_o.tipo_seleccion == 'O'
        assert fam_y.tipo_seleccion == 'Y'

    def test_obligatoria(self):
        fam_si = FamiliaFactory(obligatoria='SI')
        fam_no = FamiliaFactory(obligatoria='NO')
        assert fam_si.obligatoria == 'SI'
        assert fam_no.obligatoria == 'NO'


@pytest.mark.django_db
class TestProducto:
    def test_crear_producto(self):
        prod = ProductoFactory()
        assert prod.pk is not None
        assert prod.familia is not None
        assert prod.implemento is not None

    def test_iva_default(self):
        prod = ProductoFactory()
        assert prod.iva_porcentaje == 21

    def test_iva_custom(self):
        prod = ProductoFactory(iva_porcentaje=10.5)
        assert float(prod.iva_porcentaje) == 10.5


@pytest.mark.django_db
class TestPropiedad:
    def test_crear_propiedad(self):
        prop = PropiedadFactory()
        assert prop.pk is not None

    def test_agregacion_sum(self):
        prop = PropiedadFactory(agregacion='SUM')
        assert prop.agregacion == 'SUM'

    def test_agregacion_max(self):
        prop = PropiedadFactory(agregacion='MAX')
        assert prop.agregacion == 'MAX'


@pytest.mark.django_db
class TestProductoPropiedad:
    def test_crear_producto_propiedad(self):
        pp = ProductoPropiedadFactory()
        assert pp.pk is not None
        assert pp.producto is not None
        assert pp.propiedad is not None

    def test_tipos(self):
        exacto = ProductoPropiedadFactory(tipo='Exacto')
        minimo = ProductoPropiedadFactory(tipo='Minimo')
        maximo = ProductoPropiedadFactory(tipo='Maximo')
        assert exacto.tipo == 'Exacto'
        assert minimo.tipo == 'Minimo'
        assert maximo.tipo == 'Maximo'


@pytest.mark.django_db
class TestCompatibilidad:
    def test_crear_compatibilidad(self):
        comp = CompatibilidadFactory()
        assert comp.pk is not None

    def test_vetado(self):
        comp = CompatibilidadFactory(tipo='Vetado')
        assert comp.tipo == 'Vetado'

    def test_forzado(self):
        comp = CompatibilidadFactory(tipo='Forzado')
        assert comp.tipo == 'Forzado'
