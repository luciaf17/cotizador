from django.urls import path

from . import views_gestion as views

urlpatterns = [
    path('', views.prearmados_lista, name='gestion_prearmados'),
    path('crear/', views.prearmado_form, name='gestion_prearmado_crear'),
    path('<int:pre_id>/editar/', views.prearmado_form, name='gestion_prearmado_editar'),
]
