from django.urls import path

from . import views

urlpatterns = [
    path('configuracion/', views.configuracion, name='configuracion_tenant'),
]
