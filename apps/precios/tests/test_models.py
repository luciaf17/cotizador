import pytest

from .factories import (
    EstructuraPrearmadoFactory,
    ListaPrecioFactory,
    PrearmadoFactory,
    PrecioProductoFactory,
)


@pytest.mark.django_db
class TestListaPrecio:
    def test_crear_lista(self):
        lista = ListaPrecioFactory()
        assert lista.pk is not None

    def test_str(self):
        lista = ListaPrecioFactory(numero=81, estado='vigente')
        assert str(lista) == 'Lista #81 (vigente)'

    def test_estados(self):
        vigente = ListaPrecioFactory(estado='vigente')
        historica = ListaPrecioFactory(estado='historica')
        borrador = ListaPrecioFactory(estado='borrador')
        assert vigente.estado == 'vigente'
        assert historica.estado == 'historica'
        assert borrador.estado == 'borrador'


@pytest.mark.django_db
class TestPrecioProducto:
    def test_crear_precio(self):
        pp = PrecioProductoFactory()
        assert pp.pk is not None
        assert pp.precio > 0

    def test_unique_lista_producto(self):
        pp = PrecioProductoFactory()
        with pytest.raises(Exception):
            PrecioProductoFactory(lista=pp.lista, producto=pp.producto)


@pytest.mark.django_db
class TestPrearmado:
    def test_crear_prearmado(self):
        pre = PrearmadoFactory()
        assert pre.pk is not None

    def test_str(self):
        pre = PrearmadoFactory(nombre='Config Estándar')
        assert str(pre) == 'Config Estándar'


@pytest.mark.django_db
class TestEstructuraPrearmado:
    def test_crear_estructura(self):
        est = EstructuraPrearmadoFactory()
        assert est.pk is not None
        assert est.cantidad == 1
