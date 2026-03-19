from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.accounts.urls')),
    path('gestion/', include('apps.accounts.urls_gestion')),
    path('tenant/', include('apps.tenants.urls')),
    path('precios/', include('apps.precios.urls')),
    path('', include('apps.cotizaciones.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    from django.conf.urls.static import static
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
