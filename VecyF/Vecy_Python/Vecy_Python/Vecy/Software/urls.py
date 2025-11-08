from django.urls import path
from . import views, vendedor_views
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
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
    path('dash-vendedor/', views.vendedor_dash, name='dash_vendedor'),
    path('vendedor/negocios/', views.Negocios_V, name='Negocios_V'),
    path('vendedor/productos/', views.Crud_V, name='Crud_V'),
    path('vendedor/ofertas/', views.Ofertas_V, name='Ofertas_V'),
    path('vendedor/chats/', views.Chats_V, name='Chats_V'),
    path('vendedor/stock/', views.Stock_V, name='Stock_V'),
    path('vendedor/resenas/', vendedor_views.ver_resenas_vendedor, name='ver_resenas_vendedor'),
    path('vendedor/resenas/responder/<int:resena_id>/', vendedor_views.responder_resena, name='responder_resena'),

    # ==================== NUEVAS URLs PARA MÚLTIPLES NEGOCIOS ====================
    path('vendedor/negocios/seleccionar/<int:negocio_id>/', views.seleccionar_negocio, name='seleccionar_negocio'),
    path('vendedor/negocios/registrar/', views.registrar_negocio_vendedor, name='registrar_negocio_vendedor'),
    
    # ==================== URLs PARA PRODUCTOS ====================
    path('vendedor/productos/crear/', views.crear_producto_P, name='crear_producto_P'), 
    path('vendedor/productos/editar/<int:producto_id>/', views.editar_producto_P, name='editar_producto_P'),
    path('vendedor/productos/datos/<int:producto_id>/', views.obtener_datos_producto_P, name='obtener_datos_producto_P'),
    path('vendedor/productos/eliminar/<int:producto_id>/', views.eliminar_producto_P, name='eliminar_producto_P'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)