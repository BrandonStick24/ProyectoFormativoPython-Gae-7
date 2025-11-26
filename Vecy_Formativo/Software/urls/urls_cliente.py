from django.urls import path

from ..views import views_cliente

urlpatterns = [
    # ==================== VISTAS PÚBLICAS ====================
    path('', views_cliente.principal, name='principal'),
    
    # Productos públicos
    path('productos/', views_cliente.productos_todos, name='todos_productos'),
    path('productos/categoria/<int:categoria_id>/', views_cliente.productos_por_categoria, name='productos_categoria'),
    
    # Negocios públicos
    path('negocio/<int:id>/', views_cliente.detalle_negocio, name='detalle_negocio'),
    
    # Secciones del principal
    path('ofertas/', views_cliente.productos_todos, name='ofertas_especiales'),
    path('destacados/', views_cliente.productos_todos, name='productos_destacados'),
    path('mas-vendidos/', views_cliente.productos_todos, name='mas_vendidos'),
    path('nuevos/', views_cliente.productos_todos, name='nuevos_productos'),
    path('economicos/', views_cliente.productos_todos, name='productos_economicos'),
    
    # ==================== VISTAS PRIVADAS (logueadas) ====================
    # Dashboard y negocio logueado
    path('dashboard/', views_cliente.cliente_dashboard, name='cliente_dashboard'),
    path('negocio-logeado/<int:id>/', views_cliente.detalle_negocio_logeado, name='detalle_negocio_logeado'),
    path('reportar/', views_cliente.reportar_negocio, name='reportar_negocio'),
    path('obtener-opciones-reporte/', views_cliente.obtener_opciones_reporte, name='obtener_opciones_reporte'),
    
    # Carrito y compras
    path('agregar-carrito/', views_cliente.agregar_al_carrito, name='agregar_carrito'),
    path('carrito/', views_cliente.ver_carrito, name='ver_carrito'),
    path('carrito-data/', views_cliente.carrito_data, name='carrito_data'),
    path('actualizar-cantidad-carrito/', views_cliente.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('eliminar-item-carrito/', views_cliente.eliminar_item_carrito, name='eliminar_item_carrito'),
    path('procesar-pedido/', views_cliente.procesar_pedido, name='procesar_pedido'),
    
    # Pedidos y reseñas
    path('mis-pedidos-data/', views_cliente.mis_pedidos_data, name='mis_pedidos_data'),
    path('cancelar-pedido/', views_cliente.cancelar_pedido, name='cancelar_pedido'),
    path('guardar-resena/', views_cliente.guardar_resena, name='guardar_resena'),
    
    # Productos filtrados (logueado)
    path('productos-filtrados/', views_cliente.productos_filtrados_logeado, name='productos_filtrados_logeado'),
]