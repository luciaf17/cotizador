from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.decorators import rol_requerido
from apps.tenants.models import Tenant


def _get_tenant(request=None):
    if request and hasattr(request, 'tenant') and request.tenant:
        return request.tenant
    return Tenant.objects.filter(activo=True).first()


@login_required
@rol_requerido('admin', 'dueno')
def configuracion(request):
    tenant = _get_tenant(request)
    if not tenant:
        return redirect('cotizacion_inicio')

    if request.method == 'POST':
        tenant.nombre = request.POST.get('nombre', tenant.nombre)
        tenant.color_primario = request.POST.get('color_primario', tenant.color_primario)
        tenant.color_secundario = request.POST.get('color_secundario', tenant.color_secundario)
        tenant.bonif_max_porcentaje = request.POST.get('bonif_max_porcentaje', tenant.bonif_max_porcentaje)

        if request.POST.get('quitar_logo'):
            tenant.logo = None
        elif request.FILES.get('logo'):
            import os
            from django.conf import settings
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            tenant.logo = request.FILES['logo']

        tenant.save()
        messages.success(request, 'Configuracion actualizada.')
        return redirect('configuracion_tenant')

    return render(request, 'tenants/configuracion.html', {
        'tenant': tenant,
    })
