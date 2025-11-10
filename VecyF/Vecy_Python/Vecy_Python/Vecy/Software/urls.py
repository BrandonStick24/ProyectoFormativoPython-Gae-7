# Software/urls.py
from django.urls import path
from . import views, vendedor_views, vendedor_ofertas_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ==================== URLs PÚBLICAS Y CLIENTE ====================
    path('', views.inicio, name='inicio'),
    path('principal/', views.principal, name='principal'),
    path('login/', views.iniciar_sesion, name='login'),
    path('registro/', views.registro_user, name='registro_user'),
    path('cliente/dashboard/', views.cliente_dash, name='cliente_dash'),
    path('cierre/', views.cerrar_sesion, name='cerrar_sesion'),
    path('registrar-negocio/', views.registro_negocio, name='registro_negocios'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('negocio/<int:id>/', views.detalle_negocio, name='detalle_negocio'),
    path('guardar-resena/', views.guardar_resena, name='guardar_resena'),
    path('agregar_carrito/<int:producto_id>/', views.agregar_al_carrito, name='agregar_carrito'),
    path('ver_carrito/', views.ver_carrito, name='ver_carrito'),
    path('agregar_carrito_ajax/', views.agregar_carrito_ajax, name='agregar_carrito_ajax'),
    path('procesar_pago/', views.procesar_pago, name='procesar_pago'),
    path('pago_exitoso/', views.pago_exitoso, name='pago_exitoso'),
    

    # ==================== URLs DEL VENDEDOR ASIDE ====================
    path('dash-vendedor/', vendedor_views.vendedor_dash, name='dash_vendedor'),
    path('vendedor/negocios/', vendedor_views.Negocios_V, name='Negocios_V'),
    path('vendedor/productos/', vendedor_views.Crud_V, name='Crud_V'),
    path('vendedor/chats/', vendedor_views.Chats_V, name='Chats_V'),
    path('vendedor/stock/', vendedor_views.Stock_V, name='Stock_V'),
    path('vendedor/resenas/', vendedor_views.ver_resenas_vendedor, name='ver_resenas_vendedor'),
    path('vendedor/resenas/responder/<int:resena_id>/', vendedor_views.responder_resena, name='responder_resena'),

    # ==================== URLs PARA GESTIÓN DE NEGOCIOS VENDEDOR ====================
    path('vendedor/negocios/seleccionar/<int:negocio_id>/', vendedor_views.seleccionar_negocio, name='seleccionar_negocio'),
    path('vendedor/negocios/registrar/', vendedor_views.registrar_negocio_vendedor, name='registrar_negocio_vendedor'),
    path('vendedor/configurar-negocio/<int:negocio_id>/', vendedor_views.configurar_negocio, name='configurar_negocio'),
    path('vendedor/cambiar-estado-negocio/', vendedor_views.cambiar_estado_negocio, name='cambiar_estado_negocio'),
    path('vendedor/cerrar-negocio/', vendedor_views.cerrar_negocio, name='cerrar_negocio'),
    path('vendedor/eliminar-negocio/', vendedor_views.eliminar_negocio, name='eliminar_negocio'),
    
    # ==================== URLs PARA PRODUCTOS VENDEDOR ====================
    path('vendedor/productos/crear/', vendedor_views.crear_producto_P, name='crear_producto_P'), 
    path('vendedor/productos/editar/<int:producto_id>/', vendedor_views.editar_producto_P, name='editar_producto_P'),
    path('vendedor/productos/datos/<int:producto_id>/', vendedor_views.obtener_datos_producto_P, name='obtener_datos_producto_P'),
    path('vendedor/productos/eliminar/<int:producto_id>/', vendedor_views.eliminar_producto_P, name='eliminar_producto_P'),
    path('vendedor/productos/ajustar-stock/<int:producto_id>/', vendedor_views.ajustar_stock_producto, name='ajustar_stock_producto'),
    path('vendedor/productos/cambiar-estado/<int:producto_id>/', vendedor_views.cambiar_estado_producto, name='cambiar_estado_producto'),
    
    # ==================== URLs PARA VENTAS VENDEDOR ====================
    path('ventas/', vendedor_views.gestionar_ventas, name='gestionar_ventas'),
    path('ventas/recibo/<int:pedido_id>/', vendedor_views.ver_recibo_pedido, name='ver_recibo_pedido'),
    path('ventas/cambiar-estado/<int:pedido_id>/', vendedor_views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('ventas/eliminar/<int:pedido_id>/', vendedor_views.eliminar_pedido, name='eliminar_pedido'),

   
    # ==================== URLs PARA OFERTAS VENDEDOR ====================
    path('ofertas/', vendedor_ofertas_views.Ofertas_V, name='Ofertas_V'),
    path('ofertas/eliminar/<int:oferta_id>/', vendedor_ofertas_views.eliminar_oferta, name='eliminar_oferta'),


    

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)