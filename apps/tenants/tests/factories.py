import factory


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'tenants.Tenant'

    nombre = factory.Faker('company')
    slug = factory.Sequence(lambda n: f'tenant-{n}')
    bonif_max_porcentaje = 30
    moneda = 'ARS'
    activo = True
