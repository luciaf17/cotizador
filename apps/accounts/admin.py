from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'nombre', 'rol', 'tenant', 'requiere_validacion', 'activo']
    list_filter = ['rol', 'activo', 'requiere_validacion', 'tenant']
    search_fields = ['email', 'nombre']
    raw_id_fields = ['tenant']
    ordering = ['email']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Info', {'fields': ('nombre', 'tenant', 'rol', 'requiere_validacion', 'activo')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'password1', 'password2', 'tenant', 'rol'),
        }),
    )
