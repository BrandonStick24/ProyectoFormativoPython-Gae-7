from django.urls import path
from . import views, vendedor_views, vendedor_ofertas_views, moderador_views, vendedor_stock_views, vendedor_categorias_views, vendedor_variantes_views       
from .vendedor_variantes_views import gestionar_variantes, crear_variante, editar_variante, eliminar_variante, ajustar_stock_variante
from .vendedor_categorias_views import gestionar_categorias_tiponegocio, asignar_categoria_tiponegocio, cambiar_estado_asignacion, eliminar_asignacion
from .vendedor_ofertas_views import verificar_estado_ofertas
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
    
    # ==================== URLs PARA VARIANTES DE PRODUCTOS ====================
    path('vendedor/productos/variantes/<int:producto_id>/', gestionar_variantes, name='gestionar_variantes'),
    path('vendedor/productos/variantes/crear/<int:producto_id>/', crear_variante, name='crear_variante'),
    path('vendedor/productos/variantes/editar/<int:variante_id>/', editar_variante, name='editar_variante'),
    path('vendedor/productos/variantes/eliminar/<int:variante_id>/', eliminar_variante, name='eliminar_variante'),
    path('vendedor/productos/variantes/ajustar-stock/<int:variante_id>/', ajustar_stock_variante, name='ajustar_stock_variante'),
    
    # ==================== URLs PARA CATEGORÍAS POR TIPO DE NEGOCIO ====================
    path('vendedor/categorias-tiponegocio/', gestionar_categorias_tiponegocio, name='gestionar_categorias_tiponegocio'),
    path('vendedor/categorias-tiponegocio/asignar/', asignar_categoria_tiponegocio, name='asignar_categoria_tiponegocio'),
    path('vendedor/categorias-tiponegocio/cambiar-estado/<int:asignacion_id>/', cambiar_estado_asignacion, name='cambiar_estado_asignacion'),
    path('vendedor/categorias-tiponegocio/eliminar/<int:asignacion_id>/', eliminar_asignacion, name='eliminar_asignacion'),
    
    # ==================== URLs PARA VENTAS VENDEDOR ====================
    path('ventas/', vendedor_views.gestionar_ventas, name='gestionar_ventas'),
    path('ventas/recibo/<int:pedido_id>/', vendedor_views.ver_recibo_pedido, name='ver_recibo_pedido'),
    path('ventas/cambiar-estado/<int:pedido_id>/', vendedor_views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('ventas/eliminar/<int:pedido_id>/', vendedor_views.eliminar_pedido, name='eliminar_pedido'),

    # ==================== URLs PARA OFERTAS VENDEDOR ====================
    path('ofertas/', vendedor_ofertas_views.Ofertas_V, name='Ofertas_V'),
    path('ofertas/crear/', vendedor_ofertas_views.crear_oferta, name='crear_oferta'),
    path('ofertas/eliminar/<int:oferta_id>/', vendedor_ofertas_views.eliminar_oferta, name='eliminar_oferta'),
    path('ofertas/finalizar/<int:oferta_id>/', vendedor_ofertas_views.finalizar_oferta_manual, name='finalizar_oferta_manual'),
    path('ofertas/verificar-estado/', vendedor_ofertas_views.verificar_estado_ofertas, name='verificar_estado_ofertas'),

    # ==================== URLs DE STOCK VENDEDOR ====================
    path('vendedor/stock/', vendedor_stock_views.Stock_V, name='Stock_V'),
    path('vendedor/stock/ajustar/<int:producto_id>/', vendedor_stock_views.ajustar_stock_producto, name='ajustar_stock_producto'),
    path('vendedor/stock/entrada/<int:producto_id>/', vendedor_stock_views.entrada_stock_producto, name='entrada_stock_producto'),
    path('vendedor/stock/reporte/', vendedor_stock_views.reporte_movimientos_stock, name='reporte_movimientos_stock'),

    path('productos/<int:producto_id>/variantes/', vendedor_variantes_views.gestionar_variantes, name='gestionar_variantes'),
    path('productos/<int:producto_id>/variantes/crear/', vendedor_variantes_views.crear_variante, name='crear_variante'),
    path('variantes/<int:variante_id>/editar/', vendedor_variantes_views.editar_variante, name='editar_variante'),
    path('variantes/<int:variante_id>/eliminar/', vendedor_variantes_views.eliminar_variante, name='eliminar_variante'),
    path('variantes/<int:variante_id>/ajustar-stock/', vendedor_variantes_views.ajustar_stock_variante, name='ajustar_stock_variante'),
    
    # ==================== URLs MODERADOR ====================
    path('moderador/dashboard/', moderador_views.moderador_dash, name='moderador_dash'),
    path('moderador/gestion-usuarios/', moderador_views.gestion_usuarios, name='gestion_usuarios'),
    path('moderador/gestion-negocios/', moderador_views.gestion_negocios, name='gestion_negocios'),
    path('moderador/enviar-correos/', moderador_views.enviar_correos, name='enviar_correos'),
    
    # ==================== APIs MODERADOR - NEGOCIOS ====================
    path('moderador/api/negocio/<int:negocio_id>/', moderador_views.detalle_negocio_json, name='detalle_negocio_json'),
    path('moderador/api/negocio/<int:negocio_id>/resenas/', moderador_views.resenas_negocio_json, name='resenas_negocio_json'),
    path('moderador/api/negocio/<int:negocio_id>/productos/', moderador_views.productos_negocio_json, name='productos_negocio_json'),
    path('moderador/api/negocio/<int:negocio_id>/cambiar-estado/', moderador_views.cambiar_estado_negocio, name='api_cambiar_estado_negocio'),
    path('moderador/api/negocio/<int:negocio_id>/eliminar/', moderador_views.eliminar_negocio, name='api_eliminar_negocio'),
    
    # ==================== APIs MODERADOR - USUARIOS ====================
    path('moderador/api/usuario/<int:usuario_id>/', moderador_views.detalle_usuario_json, name='detalle_usuario_json'),
    path('moderador/api/usuario/<int:usuario_id>/cambiar-estado/', moderador_views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    path('moderador/api/usuario/<int:usuario_id>/cambiar-estado/', moderador_views.cambiar_estado_usuario, name='api_cambiar_estado_usuario'),
    
    # ==================== APIs MODERADOR - CORREOS ====================
    path('moderador/enviar-correo-masivo/', moderador_views.enviar_correo_masivo, name='enviar_correo_masivo'),
    

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

