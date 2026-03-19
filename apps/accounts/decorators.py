"""Decoradores de permisos por rol."""

from functools import wraps

from django.http import HttpResponseForbidden


def rol_requerido(*roles):
    """Permite acceso solo a usuarios con los roles indicados (o superuser)."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('login')
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.rol not in roles:
                return HttpResponseForbidden('No tenés permiso para acceder.')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
