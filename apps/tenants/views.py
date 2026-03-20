import logging
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.decorators import rol_requerido
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


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
        tenant.mostrar_comisiones = request.POST.get('mostrar_comisiones') == '1'
        comision_impacto = request.POST.get('comision_impacto_bonif', '')
        if comision_impacto:
            from decimal import Decimal
            tenant.comision_impacto_bonif = Decimal(comision_impacto)

        if request.POST.get('quitar_logo'):
            tenant.logo = None
        elif request.FILES.get('logo'):
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'tenants', 'logos')
            os.makedirs(upload_dir, exist_ok=True)
            tenant.logo = request.FILES['logo']

        try:
            tenant.save()
            messages.success(request, 'Configuracion actualizada.')
        except Exception as e:
            logger.error(f'Error guardando configuracion tenant: {e}', exc_info=True)
            messages.error(request, f'Error al guardar: {e}')

        return redirect('configuracion_tenant')

    return render(request, 'tenants/configuracion.html', {
        'tenant': tenant,
    })
