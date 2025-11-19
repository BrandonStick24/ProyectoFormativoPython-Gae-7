from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from Software.models import UsuarioPerfil, UsuariosRoles

def obtener_destinatarios_usuarios():
    """
    Obtiene todos los correos de usuarios excluyendo moderadores
    """
    try:
        # Obtener perfiles de moderadores
        perfiles_moderadores = UsuariosRoles.objects.filter(
            fkrol__desc_rol='MODERADOR'
        ).values_list('fkperfil_id', flat=True)
        
        # Obtener usuarios excluyendo moderadores
        usuarios_perfiles = UsuarioPerfil.objects.select_related('fkuser').exclude(
            id__in=perfiles_moderadores
        )
        
        # Extraer correos válidos
        correos = []
        for perfil in usuarios_perfiles:
            email = perfil.fkuser.email
            if email and '@' in email:  # Validación básica de email
                correos.append(email)
        
        return correos
        
    except Exception as e:
        print(f"Error obteniendo destinatarios: {str(e)}")
        return []

def enviar_correo_promocional(destinatarios, asunto, mensaje_html, imagen_promocion=None, es_test=True):
    """
    Función para enviar correos promocionales
    """
    try:
        if es_test:
            # En modo test, enviar solo al admin
            destinatarios = [settings.EMAIL_HOST_USER]
        
        # Crear versión de texto plano
        text_content = f"""
        {asunto}
        
        {mensaje_html}
        
        Saludos,
        El equipo de Vecy
        """
        
        # Enviar correo
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
        )
        email.attach_alternative(mensaje_html, "text/html")
        
        # Adjuntar imagen si se proporciona
        if imagen_promocion:
            email.attach(imagen_promocion.name, imagen_promocion.read(), imagen_promocion.content_type)
        
        email.send(fail_silently=False)
        
        return {
            'success': True,
            'enviados_a': destinatarios,
            'total': len(destinatarios)
        }
        
    except Exception as e:
        print(f"ERROR enviando correo promocional: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def enviar_correo_simple(destinatarios, asunto, mensaje_html, urgente=False, es_test=True):
    """
    Función para enviar correos simples
    """
    try:
        if es_test:
            # En modo test, enviar solo al admin
            destinatarios = [settings.EMAIL_HOST_USER]
        
        # Agregar prefijo de urgente si es necesario
        if urgente:
            asunto = f"🚨 URGENTE: {asunto}"
        
        # Crear versión de texto plano
        text_content = f"""
        {asunto}
        
        {mensaje_html}
        
        Saludos,
        El equipo de Vecy
        """
        
        # Enviar correo
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
        )
        email.attach_alternative(mensaje_html, "text/html")
        email.send(fail_silently=False)
        
        return {
            'success': True,
            'enviados_a': destinatarios,
            'total': len(destinatarios),
            'urgente': urgente
        }
        
    except Exception as e:
        print(f"ERROR enviando correo simple: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def enviar_notificacion_simple(usuario, accion):
    """
    Función para enviar notificaciones usando plantilla HTML
    """
    try:
        # Determinar el correo destino
        correo_destino = usuario.email
        
        # Si no tiene correo o no es válido, enviar al admin
        if not correo_destino or '@' not in correo_destino:
            correo_destino = settings.EMAIL_HOST_USER
        
        # Determinar el mensaje según la acción
        if accion == 'bloquear':
            asunto = '🔒 Tu cuenta ha sido bloqueada'
            estado_actual = 'Bloqueada'
            mensaje_personalizado = 'Tu cuenta ha sido bloqueada temporalmente. Si crees que esto es un error, por favor contacta con nuestro equipo de soporte.'
        elif accion == 'eliminar':
            asunto = '❌ Tu cuenta ha sido eliminada'
            estado_actual = 'Eliminada'
            mensaje_personalizado = 'Tu cuenta ha sido eliminada de nuestro sistema. Si crees que esto es un error, por favor contacta con nuestro equipo de soporte.'
        else:  # desbloquear
            asunto = '✅ Tu cuenta ha sido activada'
            estado_actual = 'Activa'
            mensaje_personalizado = 'Tu cuenta ha sido activada. Ya puedes acceder nuevamente a todos nuestros servicios.'
        
        # Contexto para la plantilla
        context = {
            'nombre_usuario': usuario.first_name or usuario.username,
            'username': usuario.username,
            'email': usuario.email,
            'accion': accion,
            'estado_actual': estado_actual,
            'fecha_accion': timezone.now().strftime("%d/%m/%Y %H:%M"),
            'mensaje_personalizado': mensaje_personalizado,
        }
        
        # Renderizar la plantilla HTML
        html_content = render_to_string('Moderador/bloqueo_usuario.html', context)
        
        # Crear versión de texto plano
        text_content = f"""
        Hola {usuario.username},
        
        {mensaje_personalizado}
        
        Detalles:
        - Usuario: {usuario.username}
        - Correo: {usuario.email}
        - Fecha: {context['fecha_accion']}
        - Estado actual: {estado_actual}
        
        Saludos,
        El equipo de Vecy
        """
        
        # Enviar correo con HTML y texto plano
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[correo_destino],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        return {
            'success': True,
            'enviado_a': correo_destino,
            'accion': accion
        }
        
    except Exception as e:
        print(f"ERROR enviando correo: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }