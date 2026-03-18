from django.contrib import admin

from .models import Cliente, FormaPago, TipoCliente


@admin.register(TipoCliente)
class TipoClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'bonificacion_default', 'tenant']
    list_filter = ['tenant']
    search_fields = ['nombre']
    raw_id_fields = ['tenant']


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_cliente', 'bonificacion_porcentaje', 'telefono', 'email', 'tenant']
    list_filter = ['tenant', 'tipo_cliente']
    search_fields = ['nombre', 'email', 'telefono']
    raw_id_fields = ['tenant', 'tipo_cliente']


@admin.register(FormaPago)
class FormaPagoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'bonificacion_porcentaje', 'activo', 'tenant']
    list_filter = ['tenant', 'activo']
    search_fields = ['nombre']
    raw_id_fields = ['tenant']
