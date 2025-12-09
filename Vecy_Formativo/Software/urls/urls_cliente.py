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
    path('categoria/<int:categoria_id>/', views_cliente.productos_por_categoria, name='productos_por_categoria'),
    
    # Productos filtrados (logueado)
    path('productos-filtrados/', views_cliente.productos_filtrados_logeado, name='productos_filtrados_logeado'),
    
    # Favoritos
    path('favoritos/agregar/', views_cliente.agregar_favorito, name='agregar_favorito'),
    path('favoritos/eliminar/', views_cliente.eliminar_favorito, name='eliminar_favorito'),
    path('favoritos/', views_cliente.ver_favoritos, name='ver_favoritos'),
    path('favoritos/verificar/', views_cliente.verificar_favorito, name='verificar_favorito'),
    path('favoritos/contar/', views_cliente.contar_favoritos, name='contar_favoritos'),
    path('api/favoritos/', views_cliente.favoritos_data, name='favoritos_data'),
    
    # Perfil
    path('perfil/form/', views_cliente.get_perfil_form, name='get_perfil_form'),
    path('perfil/actualizar/', views_cliente.actualizar_perfil, name='actualizar_perfil'),
    
    # Notificaciones
    path('notificaciones/', views_cliente.get_notifications, name='get_notifications'),
    path('notificaciones/marcar-leida/', views_cliente.mark_notification_read, name='mark_notification_read'),
    path('notificaciones/marcar-todas-leidas/', views_cliente.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notificaciones/ver-todas/', views_cliente.ver_notificaciones, name='ver_notificaciones'),
    path('get-header-counts/', views_cliente.get_header_counts, name='get_header_counts'),
    
    # Domicilio
    path('verificar-domicilio-negocio/', views_cliente.verificar_domicilio_negocio, name='verificar_domicilio_negocio'),
    
    # Promociones y combos
    path('agregar-combo-carrito/', views_cliente.agregar_combo_carrito, name='agregar_combo_carrito'),
    path('agregar-2x1-carrito/', views_cliente.agregar_promocion_2x1_carrito, name='agregar_promocion_2x1_carrito'),
    
    # ==================== API PARA CHATBOT ====================
    # API DEBUG para búsquedas de productos (para testing)
    path('api/sugerencia-debug/', views_cliente.api_sugerencia_completa, name='api_sugerencia_debug'),
    
    # API PRINCIPAL del chatbot con Gemini (la que debe funcionar)
    path('api/sugerencia/', views_cliente.api_sugerencia, name='api_sugerencia'),
    
    # ==================== OTRAS VISTAS ====================
    # Detalle de producto
    path('producto/<int:id>/', views_cliente.producto_detalle_logeado, name='producto_detalle_logeado'),
    
    # Chat asistente
    path('chat-asistente/', views_cliente.chat_asistente, name='chat_asistente'),
]