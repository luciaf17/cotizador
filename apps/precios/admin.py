from django.contrib import admin

from .models import EstructuraPrearmado, ListaPrecio, Prearmado, PrecioProducto


@admin.register(ListaPrecio)
class ListaPrecioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nombre', 'estado', 'ajuste_pct', 'creada_por', 'tenant']
    list_filter = ['tenant', 'estado']
    search_fields = ['nombre', 'numero']
    raw_id_fields = ['tenant', 'lista_base', 'creada_por']


@admin.register(PrecioProducto)
class PrecioProductoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'lista', 'precio', 'editado_por']
    list_filter = ['lista']
    search_fields = ['producto__nombre']
    raw_id_fields = ['lista', 'producto', 'editado_por']


class EstructuraPrearmadoInline(admin.TabularInline):
    model = EstructuraPrearmado
    extra = 1
    raw_id_fields = ['producto']


@admin.register(Prearmado)
class PrearmadoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'implemento', 'precio_referencia', 'tenant']
    list_filter = ['tenant', 'implemento']
    search_fields = ['nombre']
    raw_id_fields = ['tenant', 'implemento']
    inlines = [EstructuraPrearmadoInline]


@admin.register(EstructuraPrearmado)
class EstructuraPrearmadoAdmin(admin.ModelAdmin):
    list_display = ['prearmado', 'producto', 'cantidad']
    search_fields = ['prearmado__nombre', 'producto__nombre']
    raw_id_fields = ['prearmado', 'producto']
