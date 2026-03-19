from django.urls import path

from . import views_gestion as views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('usuarios/', views.usuarios_lista, name='usuarios_lista'),
    path('usuarios/crear/', views.usuario_crear, name='usuario_crear'),
    path('usuarios/<int:user_id>/editar/', views.usuario_editar, name='usuario_editar'),
    path('tipos-cliente/', views.tipos_cliente_lista, name='tipos_cliente_lista'),
    path('tipos-cliente/guardar/', views.tipo_cliente_guardar, name='tipo_cliente_guardar'),
    path('formas-pago/', views.formas_pago_lista, name='formas_pago_lista'),
    path('formas-pago/guardar/', views.forma_pago_guardar, name='forma_pago_guardar'),
    path('reportes/', views.reportes, name='reportes'),
]
