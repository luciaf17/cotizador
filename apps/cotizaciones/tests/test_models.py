import pytest

from .factories import (
    CotizacionDimensionFactory,
    CotizacionFactory,
    CotizacionItemFactory,
)


@pytest.mark.django_db
class TestCotizacion:
    def test_crear_cotizacion(self):
        cot = CotizacionFactory()
        assert cot.pk is not None
        assert cot.estado == 'borrador'

    def test_numero_unique(self):
        CotizacionFactory(numero='COT-2026-0001')
        with pytest.raises(Exception):
            CotizacionFactory(numero='COT-2026-0001')

    def test_estados(self):
        borrador = CotizacionFactory(estado='borrador')
        aprobada = CotizacionFactory(estado='aprobada')
        confirmada = CotizacionFactory(estado='confirmada')
        assert borrador.estado == 'borrador'
        assert aprobada.estado == 'aprobada'
        assert confirmada.estado == 'confirmada'


@pytest.mark.django_db
class TestCotizacionItem:
    def test_crear_item(self):
        item = CotizacionItemFactory()
        assert item.pk is not None
        assert item.cantidad == 1

    def test_precio_linea(self):
        item = CotizacionItemFactory(precio_unitario=500, precio_linea=1500, cantidad=3)
        assert item.precio_linea == 1500


@pytest.mark.django_db
class TestCotizacionDimension:
    def test_crear_dimension(self):
        dim = CotizacionDimensionFactory()
        assert dim.pk is not None
        assert dim.valor_acumulado == 10
