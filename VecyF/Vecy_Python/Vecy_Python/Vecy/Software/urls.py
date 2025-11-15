from django.urls import path
from . import views, vendedor_views, vendedor_ofertas_views, moderador_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import include

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('principal/', views.principal, name='principal'),
    path('auth/', include('Software.urls_auth')),  # Cambia el prefijo
    path('cliente/', include('Software.urls_cliente')),  # Cambia el prefijo
    
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


    # ==================== URLs MODERADOR ====================
    path('moderador/gestion-usuarios/', moderador_views.gestion_usuarios, name='gestion_usuarios'),
    path('moderador/dashboard/', moderador_views.moderador_dash, name='moderador_dash'),
    path('moderador/gestion-negocios/', moderador_views.gestion_negocios, name='gestion_negocios'),
    path('moderador/api/negocio/<int:negocio_id>/', moderador_views.detalle_negocio_json, name='detalle_negocio_json'),
    path('moderador/api/negocio/<int:negocio_id>/resenas/', moderador_views.resenas_negocio_json, name='resenas_negocio_json'),
    path('moderador/api/negocio/<int:negocio_id>/productos/', moderador_views.productos_negocio_json, name='productos_negocio_json'),
    path('moderador/api/negocio/<int:negocio_id>/cambiar-estado/', moderador_views.cambiar_estado_negocio, name='cambiar_estado_negocio'),
    path('moderador/api/negocio/<int:negocio_id>/eliminar/', moderador_views.eliminar_negocio, name='eliminar_negocio'),
    path('moderador/api/usuario/<int:usuario_id>/', moderador_views.detalle_usuario_json, name='detalle_usuario_json'),
    path('moderador/api/usuario/<int:usuario_id>/cambiar-estado/', moderador_views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)