import factory

from apps.tenants.tests.factories import TenantFactory


class TipoClienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'clientes.TipoCliente'

    tenant = factory.SubFactory(TenantFactory)
    nombre = factory.Faker('word')
    bonificacion_default = 10


class ClienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'clientes.Cliente'

    tenant = factory.SubFactory(TenantFactory)
    tipo_cliente = factory.SubFactory(TipoClienteFactory)
    nombre = factory.Faker('name')
    telefono = factory.Faker('phone_number')
    email = factory.Faker('email')
    bonificacion_porcentaje = 10


class FormaPagoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'clientes.FormaPago'

    tenant = factory.SubFactory(TenantFactory)
    nombre = factory.Faker('word')
    bonificacion_porcentaje = 5
    activo = True
