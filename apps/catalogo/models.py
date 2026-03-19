from django.db import models

from apps.tenants.models import TenantModel


class Implemento(TenantModel):
    nombre = models.CharField(max_length=200)
    accesorios_tipo = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name='Tipo de accesorios',
    )
    nivel_rodado = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'implementos'
        verbose_name = 'Implemento'
        verbose_name_plural = 'Implementos'

    def __str__(self):
        return self.nombre


class Familia(TenantModel):
    class TipoSeleccion(models.TextChoices):
        UNO = 'O', 'Uno (radio)'
        VARIOS = 'Y', 'Varios (checkbox)'

    class Obligatoria(models.TextChoices):
        SI = 'SI', 'Sí'
        NO = 'NO', 'No'

    implemento = models.ForeignKey(
        Implemento, on_delete=models.CASCADE, related_name='familias',
    )
    nombre = models.CharField(max_length=200)
    orden = models.IntegerField()
    tipo_seleccion = models.CharField(
        max_length=1, choices=TipoSeleccion.choices, default=TipoSeleccion.UNO,
    )
    obligatoria = models.CharField(
        max_length=2, choices=Obligatoria.choices, default=Obligatoria.SI,
    )

    class Meta:
        db_table = 'familias'
        verbose_name = 'Familia'
        verbose_name_plural = 'Familias'
        ordering = ['implemento', 'orden']

    def __str__(self):
        return f'{self.implemento.nombre} - {self.nombre} (orden {self.orden})'


class Producto(TenantModel):
    implemento = models.ForeignKey(
        Implemento, on_delete=models.CASCADE, related_name='productos',
    )
    familia = models.ForeignKey(
        Familia, on_delete=models.CASCADE, related_name='productos',
    )
    nombre = models.CharField(max_length=300)
    cod_comercio = models.CharField(max_length=100, null=True, blank=True)
    plano = models.CharField(max_length=100, null=True, blank=True)
    cod_factura = models.CharField(max_length=100, null=True, blank=True)
    orden = models.IntegerField(default=0)
    link_web = models.URLField(max_length=500, null=True, blank=True, verbose_name='Link web')
    iva_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=21,
        verbose_name='IVA (%)',
    )

    class Meta:
        db_table = 'productos'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['familia', 'orden']

    def __str__(self):
        return self.nombre


class Propiedad(TenantModel):
    class Agregacion(models.TextChoices):
        SUM = 'SUM', 'Suma'
        MAX = 'MAX', 'Máximo'

    nombre = models.CharField(max_length=100)
    unidad = models.CharField(max_length=20)
    agregacion = models.CharField(
        max_length=3, choices=Agregacion.choices, default=Agregacion.SUM,
    )

    class Meta:
        db_table = 'propiedades'
        verbose_name = 'Propiedad'
        verbose_name_plural = 'Propiedades'

    def __str__(self):
        return f'{self.nombre} ({self.unidad})'


class ProductoPropiedad(models.Model):
    class TipoValor(models.TextChoices):
        EXACTO = 'Exacto', 'Exacto'
        MINIMO = 'Minimo', 'Mínimo'
        MAXIMO = 'Maximo', 'Máximo'

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='propiedades',
    )
    propiedad = models.ForeignKey(
        Propiedad, on_delete=models.CASCADE, related_name='producto_propiedades',
    )
    tipo = models.CharField(
        max_length=6, choices=TipoValor.choices, default=TipoValor.EXACTO,
    )
    valor = models.DecimalField(max_digits=12, decimal_places=4)
    valor_neto = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
    )
    prioridad = models.IntegerField(default=0)

    class Meta:
        db_table = 'producto_propiedades'
        verbose_name = 'Producto-Propiedad'
        verbose_name_plural = 'Producto-Propiedades'

    def __str__(self):
        return f'{self.producto.nombre} - {self.propiedad.nombre}: {self.valor}'


class Compatibilidad(TenantModel):
    class TipoCompatibilidad(models.TextChoices):
        VETADO = 'Vetado', 'Vetado'
        FORZADO = 'Forzado', 'Forzado'

    producto_padre = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='compatibilidades_padre',
    )
    producto_hijo = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='compatibilidades_hijo',
    )
    tipo = models.CharField(
        max_length=7, choices=TipoCompatibilidad.choices,
    )

    class Meta:
        db_table = 'compatibilidades'
        verbose_name = 'Compatibilidad'
        verbose_name_plural = 'Compatibilidades'

    def __str__(self):
        return f'{self.producto_padre.nombre} → {self.producto_hijo.nombre} ({self.tipo})'
