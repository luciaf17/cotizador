from django.urls import path

from . import views

urlpatterns = [
    # Inicio: selección de cliente
    path('', views.inicio, name='cotizacion_inicio'),
    # Historial
    path('historial/', views.historial, name='cotizacion_historial'),
    # Buscar clientes (HTMX)
    path('buscar-clientes/', views.buscar_clientes, name='buscar_clientes'),
    # Crear cliente inline (HTMX)
    path('crear-cliente/', views.crear_cliente, name='crear_cliente'),
    # Selección de implemento
    path('implementos/<int:cliente_id>/', views.seleccionar_implemento, name='seleccionar_implemento'),
    # Flujo step-by-step
    path('nuevo/<int:cliente_id>/<int:implemento_id>/', views.cotizacion_nueva, name='cotizacion_nueva'),
    path('<int:cotizacion_id>/cargar-prearmado/', views.cargar_prearmado, name='cargar_prearmado'),
    # Paso HTMX
    path('<int:cotizacion_id>/paso/<int:orden>/', views.paso, name='cotizacion_paso'),
    # Seleccionar producto en paso
    path('<int:cotizacion_id>/seleccionar/', views.seleccionar_producto, name='seleccionar_producto'),
    # Quitar item desde resumen lateral
    path('<int:cotizacion_id>/quitar-item/<int:item_id>/', views.quitar_item, name='quitar_item'),
    # Rodados automáticos
    path('<int:cotizacion_id>/rodados/<int:familia_idx>/', views.paso_rodados, name='cotizacion_rodados'),
    path('<int:cotizacion_id>/seleccionar-rodado/', views.seleccionar_rodado, name='seleccionar_rodado'),
    # Bonificaciones y resumen
    path('<int:cotizacion_id>/bonificaciones/', views.bonificaciones, name='cotizacion_bonificaciones'),
    # Calcular totales (HTMX)
    path('<int:cotizacion_id>/calcular/', views.calcular_preview, name='cotizacion_calcular'),
    # Resumen final
    path('<int:cotizacion_id>/resumen/', views.resumen, name='cotizacion_resumen'),
    # Aprobar, confirmar y descartar
    path('<int:cotizacion_id>/aprobar/', views.aprobar, name='cotizacion_aprobar'),
    path('<int:cotizacion_id>/confirmar/', views.confirmar, name='cotizacion_confirmar'),
    path('<int:cotizacion_id>/descartar/', views.descartar, name='cotizacion_descartar'),
    # PDF
    path('<int:cotizacion_id>/pdf/', views.descargar_pdf, name='cotizacion_pdf'),
]
