from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        DUENO = 'dueno', 'Dueño'
        VENDEDOR = 'vendedor', 'Vendedor'

    username = None
    email = models.EmailField('email', unique=True)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    nombre = models.CharField(max_length=200, blank=True)
    rol = models.CharField(
        max_length=10,
        choices=Rol.choices,
        default=Rol.VENDEDOR,
    )
    requiere_validacion = models.BooleanField(
        default=False,
        verbose_name='Requiere validación',
    )
    activo = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        db_table = 'users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.nombre or self.email
