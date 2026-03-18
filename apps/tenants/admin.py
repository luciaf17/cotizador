from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'slug', 'moneda', 'bonif_max_porcentaje', 'activo']
    list_filter = ['activo', 'moneda']
    search_fields = ['nombre', 'slug']
    prepopulated_fields = {'slug': ('nombre',)}
