import pytest

from apps.accounts.models import User

from .factories import UserFactory


@pytest.mark.django_db
class TestUser:
    def test_crear_user(self):
        user = UserFactory()
        assert user.pk is not None
        assert user.activo is True

    def test_email_unique(self):
        UserFactory(email='test@example.com')
        with pytest.raises(Exception):
            UserFactory(email='test@example.com')

    def test_str_con_nombre(self):
        user = UserFactory(nombre='Juan Pérez')
        assert str(user) == 'Juan Pérez'

    def test_str_sin_nombre(self):
        user = UserFactory(nombre='')
        assert str(user) == user.email

    def test_login_con_email(self):
        assert User.USERNAME_FIELD == 'email'

    def test_roles(self):
        admin = UserFactory(rol='admin')
        dueno = UserFactory(rol='dueno')
        vendedor = UserFactory(rol='vendedor')
        assert admin.rol == 'admin'
        assert dueno.rol == 'dueno'
        assert vendedor.rol == 'vendedor'
