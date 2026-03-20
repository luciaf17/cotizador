from django.urls import path

from . import views_gestion as views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('usuarios/', views.usuarios_lista, name='usuarios_lista'),
    path('usuarios/crear/', views.usuario_crear, name='usuario_crear'),
    path('usuarios/<int:user_id>/editar/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/<int:user_id>/toggle/', views.usuario_toggle_activo, name='usuario_toggle_activo'),
    path('tipos-cliente/', views.tipos_cliente_lista, name='tipos_cliente_lista'),
    path('tipos-cliente/guardar/', views.tipo_cliente_guardar, name='tipo_cliente_guardar'),
    path('formas-pago/', views.formas_pago_lista, name='formas_pago_lista'),
    path('formas-pago/guardar/', views.forma_pago_guardar, name='forma_pago_guardar'),
    path('clientes/', views.clientes_lista, name='clientes_lista'),
    path('clientes/crear/', views.cliente_crear, name='cliente_crear'),
    path('clientes/<int:cliente_id>/editar/', views.cliente_editar, name='cliente_editar'),
    path('clientes/<int:cliente_id>/eliminar/', views.cliente_eliminar, name='cliente_eliminar'),
    path('reportes/', views.reportes, name='reportes'),
]
