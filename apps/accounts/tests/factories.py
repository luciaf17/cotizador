import factory

from apps.tenants.tests.factories import TenantFactory


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'accounts.User'

    tenant = factory.SubFactory(TenantFactory)
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    nombre = factory.Faker('name')
    rol = 'vendedor'
    requiere_validacion = False
    activo = True
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
