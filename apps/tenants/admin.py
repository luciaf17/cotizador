from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'slug', 'moneda', 'comision_impacto_bonif', 'mostrar_comisiones', 'activo']
    list_filter = ['activo', 'moneda', 'mostrar_comisiones']
    search_fields = ['nombre', 'slug']
    prepopulated_fields = {'slug': ('nombre',)}
    fieldsets = (
        (None, {'fields': ('nombre', 'slug', 'moneda', 'activo')}),
        ('Comisiones', {'fields': ('comision_impacto_bonif', 'mostrar_comisiones')}),
        ('Marca', {'fields': ('logo', 'color_primario', 'color_secundario')}),
    )
