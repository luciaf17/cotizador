import factory

from apps.tenants.tests.factories import TenantFactory


class ImplementoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'catalogo.Implemento'

    tenant = factory.SubFactory(TenantFactory)
    nombre = factory.Faker('word')
    accesorios_tipo = None
    nivel_rodado = None


class FamiliaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'catalogo.Familia'

    tenant = factory.SubFactory(TenantFactory)
    implemento = factory.SubFactory(ImplementoFactory)
    nombre = factory.Faker('word')
    orden = factory.Sequence(lambda n: n + 1)
    tipo_seleccion = 'O'
    obligatoria = 'SI'


class ProductoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'catalogo.Producto'

    tenant = factory.SubFactory(TenantFactory)
    implemento = factory.SubFactory(ImplementoFactory)
    familia = factory.SubFactory(FamiliaFactory)
    nombre = factory.Faker('word')
    cod_comercio = factory.Faker('bothify', text='??-####')
    iva_porcentaje = 21


class PropiedadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'catalogo.Propiedad'

    tenant = factory.SubFactory(TenantFactory)
    nombre = factory.Faker('word')
    unidad = 'mts'
    agregacion = 'SUM'


class ProductoPropiedadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'catalogo.ProductoPropiedad'

    producto = factory.SubFactory(ProductoFactory)
    propiedad = factory.SubFactory(PropiedadFactory)
    tipo = 'Exacto'
    valor = 10
    valor_neto = None
    prioridad = 0


class CompatibilidadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'catalogo.Compatibilidad'

    tenant = factory.SubFactory(TenantFactory)
    producto_padre = factory.SubFactory(ProductoFactory)
    producto_hijo = factory.SubFactory(ProductoFactory)
    tipo = 'Vetado'
