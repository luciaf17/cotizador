"""
TenantMiddleware: inyecta request.tenant basado en el usuario autenticado.
"""


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.tenant = getattr(request.user, 'tenant', None)
        return self.get_response(request)
