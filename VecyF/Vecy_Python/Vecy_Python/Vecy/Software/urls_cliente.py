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
    path('guardar-resena/', views.guardar_resena, name='guardar_resena'),
    path('cerrar-sesion/', views.cerrar_sesion, name='cerrar_sesion'),
    
    path('productos/', views.productos_todos, name='todos_productos'),
    path('productos/categoria/<int:categoria_id>/', views.productos_por_categoria, name='productos_categoria'),
    
    # URLs para las secciones del Principal que apuntan aquí
    path('ofertas/', views.productos_todos, name='ofertas_especiales'),
    path('destacados/', views.productos_todos, name='productos_destacados'),
    path('mas-vendidos/', views.productos_todos, name='mas_vendidos'),
    path('nuevos/', views.productos_todos, name='nuevos_productos'),
    path('economicos/', views.productos_todos, name='productos_economicos'),
    
    path('agregar-carrito/', views.agregar_al_carrito, name='agregar_carrito'),
    path('carrito-data/', views.carrito_data, name='carrito_data'),
    path('actualizar-cantidad-carrito/', views.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('eliminar-item-carrito/', views.eliminar_item_carrito, name='eliminar_item_carrito'),
    path('procesar-pedido/', views.procesar_pedido, name='procesar_pedido'),
]