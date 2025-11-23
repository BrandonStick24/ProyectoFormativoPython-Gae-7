from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from ..views import vendedor_categorias_views, vendedor_ofertas_views, vendedor_stock_views, vendedor_variantes_views, vendedor_views

urlpatterns = [    
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
    path('vendedor/productos/variantes/<int:producto_id>/', vendedor_variantes_views.gestionar_variantes, name='gestionar_variantes'),
    path('vendedor/productos/variantes/crear/<int:producto_id>/',vendedor_variantes_views.crear_variante, name='crear_variante'),
    path('vendedor/productos/variantes/editar/<int:variante_id>/', vendedor_variantes_views.editar_variante, name='editar_variante'),
    path('vendedor/productos/variantes/eliminar/<int:variante_id>/', vendedor_variantes_views.eliminar_variante, name='eliminar_variante'),
    path('vendedor/productos/variantes/ajustar-stock/<int:variante_id>/', vendedor_variantes_views.ajustar_stock_variante, name='ajustar_stock_variante'),
    
    # ==================== URLs PARA CATEGORÍAS POR TIPO DE NEGOCIO ====================
    path('vendedor/categorias-tiponegocio/', vendedor_categorias_views.gestionar_categorias_tiponegocio, name='gestionar_categorias_tiponegocio'),
    path('vendedor/categorias-tiponegocio/asignar/', vendedor_categorias_views.asignar_categoria_tiponegocio, name='asignar_categoria_tiponegocio'),
    path('vendedor/categorias-tiponegocio/cambiar-estado/<int:asignacion_id>/', vendedor_categorias_views.cambiar_estado_asignacion, name='cambiar_estado_asignacion'),
    path('vendedor/categorias-tiponegocio/eliminar/<int:asignacion_id>/', vendedor_categorias_views.eliminar_asignacion, name='eliminar_asignacion'),
    
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
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

