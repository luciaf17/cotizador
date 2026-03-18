from django.conf import settings
from django.db import models

from apps.tenants.models import TenantModel


class ListaPrecio(TenantModel):
    class Estado(models.TextChoices):
        VIGENTE = 'vigente', 'Vigente'
        HISTORICA = 'historica', 'Histórica'
        BORRADOR = 'borrador', 'Borrador'

    numero = models.IntegerField()
    nombre = models.CharField(max_length=200, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.BORRADOR,
    )
    ajuste_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Ajuste (%)',
    )
    lista_base = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='listas_derivadas',
    )
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='listas_creadas',
    )

    class Meta:
        db_table = 'listas_precios'
        verbose_name = 'Lista de Precio'
        verbose_name_plural = 'Listas de Precios'

    def __str__(self):
        return f'Lista #{self.numero} ({self.estado})'


class PrecioProducto(models.Model):
    lista = models.ForeignKey(
        ListaPrecio, on_delete=models.CASCADE, related_name='precios',
    )
    producto = models.ForeignKey(
        'catalogo.Producto', on_delete=models.CASCADE, related_name='precios',
    )
    precio = models.DecimalField(max_digits=14, decimal_places=2)
    editado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='precios_editados',
    )

    class Meta:
        db_table = 'precios_productos'
        verbose_name = 'Precio de Producto'
        verbose_name_plural = 'Precios de Productos'
        unique_together = [('lista', 'producto')]

    def __str__(self):
        return f'{self.producto.nombre} - ${self.precio}'


class Prearmado(TenantModel):
    implemento = models.ForeignKey(
        'catalogo.Implemento', on_delete=models.CASCADE, related_name='prearmados',
    )
    nombre = models.CharField(max_length=300)
    precio_referencia = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
    )

    class Meta:
        db_table = 'prearmados'
        verbose_name = 'Prearmado'
        verbose_name_plural = 'Prearmados'

    def __str__(self):
        return self.nombre


class EstructuraPrearmado(models.Model):
    prearmado = models.ForeignKey(
        Prearmado, on_delete=models.CASCADE, related_name='estructura',
    )
    producto = models.ForeignKey(
        'catalogo.Producto', on_delete=models.CASCADE,
        related_name='en_prearmados',
    )
    cantidad = models.IntegerField(default=1)

    class Meta:
        db_table = 'estructura_prearmados'
        verbose_name = 'Estructura Prearmado'
        verbose_name_plural = 'Estructura Prearmados'

    def __str__(self):
        return f'{self.prearmado.nombre} - {self.producto.nombre} x{self.cantidad}'
