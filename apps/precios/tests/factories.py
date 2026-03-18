import factory

from apps.accounts.tests.factories import UserFactory
from apps.catalogo.tests.factories import ImplementoFactory, ProductoFactory
from apps.tenants.tests.factories import TenantFactory


class ListaPrecioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'precios.ListaPrecio'

    tenant = factory.SubFactory(TenantFactory)
    numero = factory.Sequence(lambda n: n + 1)
    nombre = factory.Faker('sentence', nb_words=3)
    estado = 'vigente'
    creada_por = factory.SubFactory(UserFactory)


class PrecioProductoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'precios.PrecioProducto'

    lista = factory.SubFactory(ListaPrecioFactory)
    producto = factory.SubFactory(ProductoFactory)
    precio = factory.Faker('pydecimal', left_digits=6, right_digits=2, positive=True)


class PrearmadoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'precios.Prearmado'

    tenant = factory.SubFactory(TenantFactory)
    implemento = factory.SubFactory(ImplementoFactory)
    nombre = factory.Faker('sentence', nb_words=3)
    precio_referencia = None


class EstructuraPrearmadoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'precios.EstructuraPrearmado'

    prearmado = factory.SubFactory(PrearmadoFactory)
    producto = factory.SubFactory(ProductoFactory)
    cantidad = 1
