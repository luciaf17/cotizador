from django.conf import settings
from django.db import models

from apps.tenants.models import TenantModel


class Cotizacion(TenantModel):
    class Estado(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        APROBADA = 'aprobada', 'Aprobada'
        CONFIRMADA = 'confirmada', 'Confirmada'

    implemento = models.ForeignKey(
        'catalogo.Implemento', on_delete=models.CASCADE,
        related_name='cotizaciones',
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='cotizaciones',
    )
    cliente = models.ForeignKey(
        'clientes.Cliente', on_delete=models.CASCADE,
        related_name='cotizaciones',
    )
    lista = models.ForeignKey(
        'precios.ListaPrecio', on_delete=models.CASCADE,
        related_name='cotizaciones',
    )
    forma_pago = models.ForeignKey(
        'clientes.FormaPago', on_delete=models.CASCADE,
        related_name='cotizaciones',
    )
    numero = models.CharField(max_length=20, unique=True)
    subtotal_bruto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    bonif_cliente_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
    )
    bonif_cliente_monto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    bonif_pago_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
    )
    bonif_pago_monto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    subtotal_neto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    iva_105_base = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    iva_105_monto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    iva_21_base = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    iva_21_monto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    iva_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    precio_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    comision_porcentaje_efectivo = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
    )
    comision_monto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
    )
    fecha_entrega = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.BORRADOR,
    )
    aprobada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cotizaciones_aprobadas',
    )
    aprobada_at = models.DateTimeField(null=True, blank=True)
    confirmada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cotizaciones_confirmadas',
    )
    confirmada_at = models.DateTimeField(null=True, blank=True)
    pdf_url = models.TextField(null=True, blank=True)
    notas = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'cotizaciones'
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'

    def __str__(self):
        return f'{self.numero} - {self.cliente.nombre}'


class CotizacionItem(models.Model):
    cotizacion = models.ForeignKey(
        Cotizacion, on_delete=models.CASCADE, related_name='items',
    )
    producto = models.ForeignKey(
        'catalogo.Producto', on_delete=models.CASCADE,
    )
    familia = models.ForeignKey(
        'catalogo.Familia', on_delete=models.CASCADE,
    )
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=2)
    precio_linea = models.DecimalField(max_digits=14, decimal_places=2)
    iva_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=21,
    )

    class Meta:
        db_table = 'cotizacion_items'
        verbose_name = 'Item de Cotización'
        verbose_name_plural = 'Items de Cotización'

    def __str__(self):
        return f'{self.producto.nombre} x{self.cantidad}'


class CotizacionDimension(models.Model):
    cotizacion = models.ForeignKey(
        Cotizacion, on_delete=models.CASCADE, related_name='dimensiones',
    )
    propiedad = models.ForeignKey(
        'catalogo.Propiedad', on_delete=models.CASCADE,
    )
    valor_acumulado = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        db_table = 'cotizacion_dimensiones'
        verbose_name = 'Dimensión de Cotización'
        verbose_name_plural = 'Dimensiones de Cotización'

    def __str__(self):
        return f'{self.propiedad.nombre}: {self.valor_acumulado}'
