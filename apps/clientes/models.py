from django.db import models

from apps.tenants.models import TenantModel


class TipoCliente(TenantModel):
    nombre = models.CharField(max_length=100)
    bonificacion_default = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Bonificación default (%)',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tipos_cliente'
        verbose_name = 'Tipo de Cliente'
        verbose_name_plural = 'Tipos de Cliente'

    def __str__(self):
        return self.nombre


class Cliente(TenantModel):
    tipo_cliente = models.ForeignKey(
        TipoCliente, on_delete=models.CASCADE, related_name='clientes',
    )
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    bonificacion_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Bonificación (%)',
    )

    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.nombre


class FormaPago(TenantModel):
    nombre = models.CharField(max_length=100)
    bonificacion_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Bonificación (%)',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'formas_pago'
        verbose_name = 'Forma de Pago'
        verbose_name_plural = 'Formas de Pago'

    def __str__(self):
        return self.nombre
