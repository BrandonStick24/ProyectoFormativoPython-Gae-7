from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from ..views import views_moderador

urlpatterns = [
    # ==================== URLs MODERADOR ====================
    path('moderador/dashboard/', views_moderador.moderador_dash, name='moderador_dash'),
    path('moderador/gestion-usuarios/', views_moderador.gestion_usuarios, name='gestion_usuarios'),
    path('moderador/gestion-negocios/', views_moderador.gestion_negocios, name='gestion_negocios'),
    path('moderador/enviar-correos/', views_moderador.enviar_correos, name='enviar_correos'),
    
    # ==================== APIs MODERADOR - NEGOCIOS ====================
    path('moderador/api/negocio/<int:negocio_id>/', views_moderador.detalle_negocio_json, name='detalle_negocio_json'),
    path('moderador/api/negocio/<int:negocio_id>/resenas/', views_moderador.resenas_negocio_json, name='resenas_negocio_json'),
    path('moderador/api/negocio/<int:negocio_id>/productos/', views_moderador.productos_negocio_json, name='productos_negocio_json'),
    path('moderador/api/negocio/<int:negocio_id>/cambiar-estado/', views_moderador.cambiar_estado_negocio, name='api_cambiar_estado_negocio'),
    path('moderador/api/negocio/<int:negocio_id>/eliminar/', views_moderador.eliminar_negocio, name='api_eliminar_negocio'),
    
    # ==================== APIs MODERADOR - USUARIOS ====================
    path('moderador/api/usuario/<int:usuario_id>/', views_moderador.detalle_usuario_json, name='detalle_usuario_json'),
    path('moderador/api/usuario/<int:usuario_id>/cambiar-estado/', views_moderador.cambiar_estado_usuario, name='api_cambiar_estado_usuario'),
    
    # ==================== APIs MODERADOR - CORREOS ====================
    path('moderador/enviar-correo-masivo/', views_moderador.enviar_correo_masivo, name='enviar_correo_masivo'),

    # ==================== APIs MODERADOR - RESEÑAS ====================
   path('moderador/gestion-resenas/', views_moderador.gestion_resenas_reportadas, name='gestion_resenas_reportadas'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)