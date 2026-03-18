from django.urls import path

from . import views

urlpatterns = [
    path('listas/', views.panel_listas, name='panel_listas'),
    path('listas/crear/', views.crear_lista, name='crear_lista'),
    path('listas/<int:lista_id>/editar/', views.editar_lista, name='editar_lista'),
    path('listas/<int:lista_id>/activar/', views.activar_lista_view, name='activar_lista'),
    path('precios/<int:precio_id>/editar/', views.editar_precio, name='editar_precio'),
    path('prearmados/pdf/', views.generar_pdf_prearmados, name='pdf_prearmados'),
]
