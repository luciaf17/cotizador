import factory

from apps.accounts.tests.factories import UserFactory
from apps.catalogo.tests.factories import (
    FamiliaFactory,
    ImplementoFactory,
    ProductoFactory,
    PropiedadFactory,
)
from apps.clientes.tests.factories import ClienteFactory, FormaPagoFactory
from apps.precios.tests.factories import ListaPrecioFactory
from apps.tenants.tests.factories import TenantFactory


class CotizacionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'cotizaciones.Cotizacion'

    tenant = factory.SubFactory(TenantFactory)
    implemento = factory.SubFactory(ImplementoFactory)
    vendedor = factory.SubFactory(UserFactory)
    cliente = factory.SubFactory(ClienteFactory)
    lista = factory.SubFactory(ListaPrecioFactory)
    forma_pago = factory.SubFactory(FormaPagoFactory)
    numero = factory.Sequence(lambda n: f'COT-2026-{n:04d}')
    estado = 'borrador'


class CotizacionItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'cotizaciones.CotizacionItem'

    cotizacion = factory.SubFactory(CotizacionFactory)
    producto = factory.SubFactory(ProductoFactory)
    familia = factory.SubFactory(FamiliaFactory)
    cantidad = 1
    precio_unitario = 1000
    precio_linea = 1000
    iva_porcentaje = 21


class CotizacionDimensionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'cotizaciones.CotizacionDimension'

    cotizacion = factory.SubFactory(CotizacionFactory)
    propiedad = factory.SubFactory(PropiedadFactory)
    valor_acumulado = 10
