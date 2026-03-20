from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.accounts.urls')),
    path('gestion/', include('apps.accounts.urls_gestion')),
    path('gestion/catalogo/', include('apps.catalogo.urls_gestion')),
    path('gestion/prearmados/', include('apps.precios.urls_gestion')),
    path('tenant/', include('apps.tenants.urls')),
    path('precios/', include('apps.precios.urls')),
    path('', include('apps.cotizaciones.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
