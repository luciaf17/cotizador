import factory


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'tenants.Tenant'

    nombre = factory.Faker('company')
    slug = factory.Sequence(lambda n: f'tenant-{n}')
    moneda = 'ARS'
    comision_impacto_bonif = '0.60'
    mostrar_comisiones = True
    activo = True
