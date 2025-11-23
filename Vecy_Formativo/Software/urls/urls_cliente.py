from django.urls import path
from ..views import views_cliente

urlpatterns = [
    # Página principal del cliente
    path('cliente/', views_cliente.principal, name='principal'),
    
    # Dashboard principal del cliente
    path('cliente/dashboard/', views_cliente.cliente_dashboard, name='cliente_dashboard'),
    
    # Detalle de negocio para usuario logueado
    path('cliente/negocio/<int:id>/', views_cliente.detalle_negocio_logeado, name='detalle_negocio_logeado'),
    
    # Carrito y gestión
    path('cliente/carrito/', views_cliente.ver_carrito, name='ver_carrito'),
    path('cliente/carrito/data/', views_cliente.carrito_data, name='carrito_data'),
    path('cliente/carrito/agregar/', views_cliente.agregar_al_carrito, name='agregar_al_carrito'),
    path('cliente/carrito/actualizar/', views_cliente.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('cliente/carrito/eliminar/', views_cliente.eliminar_item_carrito, name='eliminar_item_carrito'),
    
    # Pedidos
    path('cliente/pedido/procesar/', views_cliente.procesar_pedido, name='procesar_pedido'),
    path('cliente/pedidos/data/', views_cliente.mis_pedidos_data, name='mis_pedidos_data'),
    path('cliente/pedido/cancelar/', views_cliente.cancelar_pedido, name='cancelar_pedido'),
    
    # Reseñas
    path('cliente/resena/guardar/', views_cliente.guardar_resena, name='guardar_resena'),
    
    # Productos filtrados
    path('cliente/productos/filtrados/', views_cliente.productos_filtrados_logeado, name='productos_filtrados_logeado'),
]