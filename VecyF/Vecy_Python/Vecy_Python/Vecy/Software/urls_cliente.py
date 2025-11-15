from django.urls import path
from . import views

urlpatterns = [
    # Vistas públicas
    path('', views.principal, name='principal'),
    path('inicio/', views.inicio, name='inicio'),
    
    # Vistas privadas (logueadas) - DEBEN IR ANTES para evitar conflictos
    path('negocio-logeado/<int:id>/', views.detalle_negocio_logeado, name='detalle_negocio_logeado'),  # PRIMERO
    
    # Vistas públicas - DESPUÉS
    path('negocio/<int:id>/', views.detalle_negocio, name='detalle_negocio'),  # DESPUÉS
    
    # Otras URLs
    path('dashboard/', views.cliente_dashboard, name='cliente_dashboard'),
    path('agregar-carrito/', views.agregar_al_carrito_logeado, name='agregar_carrito_logeado'),
    path('seguir-negocio/', views.seguir_negocio_logeado, name='seguir_negocio_logeado'),
    path('guardar-resena/', views.guardar_resena, name='guardar_resena'),
    path('cerrar-sesion/', views.cerrar_sesion, name='cerrar_sesion'),
]