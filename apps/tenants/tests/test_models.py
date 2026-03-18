import pytest

from .factories import TenantFactory


@pytest.mark.django_db
class TestTenant:
    def test_crear_tenant(self):
        tenant = TenantFactory()
        assert tenant.pk is not None
        assert tenant.activo is True

    def test_str(self):
        tenant = TenantFactory(nombre='Ceibo')
        assert str(tenant) == 'Ceibo'

    def test_slug_unique(self):
        TenantFactory(slug='test-unique-slug')
        with pytest.raises(Exception):
            TenantFactory(slug='test-unique-slug')
