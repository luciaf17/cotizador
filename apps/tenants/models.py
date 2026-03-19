import uuid
from decimal import Decimal

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(TimeStampedModel):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class Tenant(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    moneda = models.CharField(max_length=3, default='ARS')
    comision_impacto_bonif = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.60'),
        verbose_name='Factor impacto bonificación sobre comisión',
    )
    mostrar_comisiones = models.BooleanField(
        default=False,
        verbose_name='Vendedor ve su comisión',
    )
    logo = models.ImageField(
        upload_to='tenants/logos/',
        null=True, blank=True,
        verbose_name='Logo',
    )
    color_primario = models.CharField(
        max_length=7, default='#0f172a',
        verbose_name='Color primario (header PDF)',
    )
    color_secundario = models.CharField(
        max_length=7, default='#2563eb',
        verbose_name='Color secundario (acentos PDF)',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tenants'
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'

    def __str__(self):
        return self.nombre
