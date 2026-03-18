from django.contrib import admin

from .models import Cotizacion, CotizacionDimension, CotizacionItem


class CotizacionItemInline(admin.TabularInline):
    model = CotizacionItem
    extra = 0
    raw_id_fields = ['producto', 'familia']


class CotizacionDimensionInline(admin.TabularInline):
    model = CotizacionDimension
    extra = 0
    raw_id_fields = ['propiedad']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'cliente', 'implemento', 'vendedor',
        'estado', 'precio_total', 'tenant',
    ]
    list_filter = ['tenant', 'estado', 'implemento']
    search_fields = ['numero', 'cliente__nombre', 'vendedor__nombre']
    raw_id_fields = ['tenant', 'implemento', 'vendedor', 'cliente', 'lista', 'forma_pago', 'confirmada_por']
    inlines = [CotizacionItemInline, CotizacionDimensionInline]


@admin.register(CotizacionItem)
class CotizacionItemAdmin(admin.ModelAdmin):
    list_display = ['cotizacion', 'producto', 'cantidad', 'precio_unitario', 'precio_linea', 'iva_porcentaje']
    list_filter = ['iva_porcentaje']
    search_fields = ['producto__nombre', 'cotizacion__numero']
    raw_id_fields = ['cotizacion', 'producto', 'familia']


@admin.register(CotizacionDimension)
class CotizacionDimensionAdmin(admin.ModelAdmin):
    list_display = ['cotizacion', 'propiedad', 'valor_acumulado']
    search_fields = ['cotizacion__numero', 'propiedad__nombre']
    raw_id_fields = ['cotizacion', 'propiedad']
