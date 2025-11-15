from django.urls import path
from . import views_auth

urlpatterns = [
    path('iniciar-sesion/', views_auth.iniciar_sesion, name='iniciar_sesion'),
    path('registro/', views_auth.registro_usuario, name='registro_usuario'),
    path('registro-negocio/', views_auth.registro_negocio, name='registro_negocio'),
    path('recuperar-contrasena/', views_auth.recuperar_contrasena, name='recuperar_contrasena'),
    path('verificar-codigo/', views_auth.verificar_codigo, name='verificar_codigo'),
    path('restablecer-contrasena/', views_auth.restablecer_contrasena, name='restablecer_contrasena'),
    path('cerrar-sesion/', views_auth.cerrar_sesion, name='cerrar_sesion'),
]