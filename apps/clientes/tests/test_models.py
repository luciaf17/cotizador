import pytest

from .factories import ClienteFactory, FormaPagoFactory, TipoClienteFactory


@pytest.mark.django_db
class TestTipoCliente:
    def test_crear_tipo_cliente(self):
        tc = TipoClienteFactory()
        assert tc.pk is not None

    def test_str(self):
        tc = TipoClienteFactory(nombre='Concesionario')
        assert str(tc) == 'Concesionario'


@pytest.mark.django_db
class TestCliente:
    def test_crear_cliente(self):
        cli = ClienteFactory()
        assert cli.pk is not None
        assert cli.tipo_cliente is not None

    def test_str(self):
        cli = ClienteFactory(nombre='Juan Pérez')
        assert str(cli) == 'Juan Pérez'


@pytest.mark.django_db
class TestFormaPago:
    def test_crear_forma_pago(self):
        fp = FormaPagoFactory()
        assert fp.pk is not None
        assert fp.activo is True

    def test_str(self):
        fp = FormaPagoFactory(nombre='Contado')
        assert str(fp) == 'Contado'
