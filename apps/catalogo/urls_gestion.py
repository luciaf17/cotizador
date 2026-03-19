from django.urls import path

from . import views_gestion as views

urlpatterns = [
    path('implementos/', views.implementos_lista, name='gestion_implementos'),
    path('implementos/crear/', views.implemento_form, name='gestion_implemento_crear'),
    path('implementos/<int:imp_id>/editar/', views.implemento_form, name='gestion_implemento_editar'),

    path('familias/', views.familias_lista, name='gestion_familias'),
    path('familias/crear/', views.familia_form, name='gestion_familia_crear'),
    path('familias/<int:fam_id>/editar/', views.familia_form, name='gestion_familia_editar'),

    path('productos/', views.productos_lista, name='gestion_productos'),
    path('productos/crear/', views.producto_form, name='gestion_producto_crear'),
    path('productos/<int:prod_id>/editar/', views.producto_form, name='gestion_producto_editar'),

    path('propiedades/', views.propiedades_lista, name='gestion_propiedades'),
    path('propiedades/guardar/', views.propiedad_guardar, name='gestion_propiedad_guardar'),

    path('compatibilidades/', views.compatibilidades_lista, name='gestion_compatibilidades'),
    path('compatibilidades/crear/', views.compatibilidad_form, name='gestion_compatibilidad_crear'),
    path('compatibilidades/<int:comp_id>/editar/', views.compatibilidad_form, name='gestion_compatibilidad_editar'),
    path('compatibilidades/<int:comp_id>/eliminar/', views.compatibilidad_eliminar, name='gestion_compatibilidad_eliminar'),
]
