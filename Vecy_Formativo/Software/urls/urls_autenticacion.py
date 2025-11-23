from django.urls import path
from ..views import views_autenticacion

urlpatterns = [
    path('iniciar/sesion', views_autenticacion.iniciar_sesion, name='iniciar_sesion'),
    path('registro/', views_autenticacion.registro_usuario, name='registro_usuario'),
    path('cerrar-sesion/', views_autenticacion.cerrar_sesion, name='cerrar_sesion'),
    
    path('restablecer-contrasena/', views_autenticacion.restablecer_contrasena, name='restablecer_contrasena'),
    path('cambiar-contrasena/', views_autenticacion.cambiar_contrasena, name='cambiar_contrasena'),
    path('verificar-email/', views_autenticacion.verificar_email, name='verificar_email'),
    path('verificar-documento/', views_autenticacion.verificar_documento, name='verificar_documento'),
    path('verificar-nit/', views_autenticacion.verificar_nit, name='verificar_nit'),
    path('verificar-codigo/', views_autenticacion.verificar_codigo, name='verificar_codigo'),
    path('recuperar-contrasena/', views_autenticacion.recuperar_contrasena, name='recuperar_contrasena'),
]