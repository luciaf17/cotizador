from django.contrib import admin

from .models import (
    Compatibilidad,
    Familia,
    Implemento,
    Producto,
    ProductoPropiedad,
    Propiedad,
)


@admin.register(Implemento)
class ImplementoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tenant', 'accesorios_tipo', 'nivel_rodado']
    list_filter = ['tenant', 'accesorios_tipo']
    search_fields = ['nombre']
    raw_id_fields = ['tenant']


@admin.register(Familia)
class FamiliaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'implemento', 'orden', 'tipo_seleccion', 'obligatoria', 'tenant']
    list_filter = ['tenant', 'tipo_seleccion', 'obligatoria']
    search_fields = ['nombre']
    raw_id_fields = ['tenant', 'implemento']


class ProductoPropiedadInline(admin.TabularInline):
    model = ProductoPropiedad
    extra = 1
    raw_id_fields = ['propiedad']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'familia', 'implemento', 'cod_comercio', 'iva_porcentaje', 'tenant']
    list_filter = ['tenant', 'implemento', 'iva_porcentaje']
    search_fields = ['nombre', 'cod_comercio', 'cod_factura']
    raw_id_fields = ['tenant', 'implemento', 'familia']
    inlines = [ProductoPropiedadInline]


@admin.register(Propiedad)
class PropiedadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'unidad', 'agregacion', 'tenant']
    list_filter = ['tenant', 'agregacion']
    search_fields = ['nombre']
    raw_id_fields = ['tenant']


@admin.register(ProductoPropiedad)
class ProductoPropiedadAdmin(admin.ModelAdmin):
    list_display = ['producto', 'propiedad', 'tipo', 'valor', 'valor_neto', 'prioridad']
    list_filter = ['tipo', 'propiedad']
    search_fields = ['producto__nombre', 'propiedad__nombre']
    raw_id_fields = ['producto', 'propiedad']


@admin.register(Compatibilidad)
class CompatibilidadAdmin(admin.ModelAdmin):
    list_display = ['producto_padre', 'producto_hijo', 'tipo', 'tenant']
    list_filter = ['tenant', 'tipo']
    search_fields = ['producto_padre__nombre', 'producto_hijo__nombre']
    raw_id_fields = ['tenant', 'producto_padre', 'producto_hijo']
