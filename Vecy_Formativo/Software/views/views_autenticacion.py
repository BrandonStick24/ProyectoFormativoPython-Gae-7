from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from datetime import date, datetime
import re
from django.views.decorators.cache import never_cache

from ..models import *

def _obtener_rol_usuario(perfil):
    try:
        rol_usuario = UsuariosRoles.objects.filter(fkperfil=perfil).first()
        return rol_usuario.fkrol.desc_rol.lower() if rol_usuario else None
    except Exception:
        return None

def _tiene_negocio_activo(perfil):
    try:
        return Negocios.objects.filter(
            fkpropietario_neg=perfil, 
            estado_neg='activo'
        ).exists()
    except Exception:
        return False

def _redirigir_segun_rol(user):
    try:
        perfil = UsuarioPerfil.objects.get(fkuser=user)
        rol_usuario = _obtener_rol_usuario(perfil)
        
        if rol_usuario == 'vendedor':
            return redirect('dash_vendedor')
        elif rol_usuario == 'cliente':
            return redirect('cliente_dashboard')
        elif rol_usuario == 'moderador':
            return redirect('moderador_dash')
        else:
            return redirect('principal')
            
    except Exception:
        return redirect('principal')

def validar_email(email):
    try:
        validate_email(email)
        return True, ""
    except ValidationError:
        return False, "El formato del correo electrónico no es válido."

def validar_contraseña(contrasena):
    if len(contrasena) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    
    if not re.search(r'[A-Z]', contrasena):
        return False, "La contraseña debe contener al menos una letra mayúscula."
    
    if not re.search(r'[a-z]', contrasena):
        return False, "La contraseña debe contener al menos una letra minúscula."
    
    if not re.search(r'\d', contrasena):
        return False, "La contraseña debe contener al menos un número."
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', contrasena):
        return False, "La contraseña debe contener al menos un carácter especial."
    
    return True, ""

def validar_documento(tipo_doc, documento):
    if tipo_doc == '1':
        if not documento.isdigit() or len(documento) < 8 or len(documento) > 10:
            return False, "La cédula debe tener entre 8 y 10 dígitos."
    elif tipo_doc == '2':
        if not documento.isdigit() or len(documento) < 6 or len(documento) > 10:
            return False, "La tarjeta de identidad debe tener entre 6 y 10 dígitos."
    elif tipo_doc == '3':
        if len(documento) < 6:
            return False, "La cédula de extranjería debe tener al menos 6 caracteres."
    return True, ""

def validar_nombre(nombre):
    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
        return False, "El nombre solo puede contener letras y espacios."
    
    if len(nombre.strip()) < 2:
        return False, "El nombre debe tener al menos 2 caracteres."
    
    return True, ""

def validar_fecha_nacimiento(fecha_nac):
    try:
        fecha_nac_date = date.fromisoformat(fecha_nac)
        hoy = date.today()
        
        if fecha_nac_date > hoy:
            return False, "La fecha de nacimiento no puede ser futura."
        
        edad = hoy.year - fecha_nac_date.year - ((hoy.month, hoy.day) < (fecha_nac_date.month, fecha_nac_date.day))
        
        if edad < 18:
            return False, "Debes ser mayor de 18 años para registrarte."
        
        if edad > 100:
            return False, "La edad ingresada no es válida."
            
        return True, ""
        
    except ValueError:
        return False, "La fecha de nacimiento no tiene un formato válido."

@never_cache
@csrf_protect
def iniciar_sesion(request):
    if request.user.is_authenticated:
        return _redirigir_segun_rol(request.user)

    if request.method == "POST":
        correo = request.POST.get("correo", "").strip().lower()
        password = request.POST.get("contrasena", "")

        if not correo or not password:
            messages.error(request, "Correo electrónico y contraseña son obligatorios.")
            return render(request, "Autenticacion/login.html")

        try:
            try:
                user = User.objects.get(email=correo)
            except User.DoesNotExist:
                messages.error(request, "No existe una cuenta con este correo electrónico.")
                return render(request, "Autenticacion/login.html")

            if not user.is_active:
                messages.error(request, "Tu cuenta está desactivada. Contacta al administrador.")
                return render(request, "Autenticacion/login.html")

            user_auth = authenticate(request, username=user.username, password=password)
            
            if user_auth is not None:
                login(request, user_auth)
                
                try:
                    perfil = UsuarioPerfil.objects.get(fkuser=user)
                    
                    if perfil.estado_user != 'activo':
                        logout(request)
                        messages.error(request, "Tu perfil está inactivo. Contacta al administrador.")
                        return render(request, "Autenticacion/login.html")
                    
                    rol_usuario = _obtener_rol_usuario(perfil)
                    if not rol_usuario:
                        logout(request)
                        messages.error(request, "Rol de usuario no definido. Contacta al administrador.")
                        return render(request, "Autenticacion/login.html")
                    
                    if rol_usuario == 'vendedor':
                        if not _tiene_negocio_activo(perfil):
                            logout(request)
                            messages.error(request, "No tienes un negocio activo registrado.")
                            return render(request, "Autenticacion/login.html")
                    
                    messages.success(request, f"¡Bienvenido de nuevo, {user.first_name}!")
                    return _redirigir_segun_rol(user)
                    
                except UsuarioPerfil.DoesNotExist:
                    logout(request)
                    messages.error(request, "Perfil de usuario no encontrado. Contacta al administrador.")
                    return render(request, "Autenticacion/login.html")
                    
            else:
                messages.error(request, "Contraseña incorrecta.")
                return render(request, "Autenticacion/login.html")

        except Exception as e:
            messages.error(request, "Error interno del sistema. Por favor, intenta más tarde.")

    return render(request, "Autenticacion/login.html")

def registro_usuario(request):
    roles = Roles.objects.exclude(desc_rol__icontains='admin')
    tipo_documentos = TipoDocumento.objects.all()
    tipo_negocios = TipoNegocio.objects.all()
    
    if request.method == 'POST':
        tipo_doc_id = request.POST.get("tipo_doc", "").strip()
        doc_user = request.POST.get("documento", "").strip()
        nombre = request.POST.get("nombre", "").strip()
        correo = request.POST.get("correo", "").strip().lower()
        fecha_nac = request.POST.get("fechan", "")
        contrasena = request.POST.get("contrasena", "")
        confirmar_contrasena = request.POST.get("confirmar_contrasena", "")
        rol_id = request.POST.get("rol", "")
        
        nit = request.POST.get("nit", "").strip()
        nom_neg = request.POST.get("nom_neg", "").strip()
        direcc_neg = request.POST.get("direcc_neg", "").strip()
        desc_neg = request.POST.get("desc_neg", "").strip()
        fktiponeg_neg = request.POST.get("fktiponeg_neg", "")
        img_neg = request.FILES.get('img_neg')
        
        errores = False
        
        if not tipo_doc_id:
            messages.error(request, "El tipo de documento es obligatorio.", extra_tags='tipo_doc')
            errores = True
        
        if not doc_user:
            messages.error(request, "El número de documento es obligatorio.", extra_tags='documento')
            errores = True
        else:
            doc_valido, mensaje_doc = validar_documento(tipo_doc_id, doc_user)
            if not doc_valido:
                messages.error(request, mensaje_doc, extra_tags='documento')
                errores = True
        
        if not nombre:
            messages.error(request, "El nombre completo es obligatorio.", extra_tags='nombre')
            errores = True
        else:
            nombre_valido, mensaje_nombre = validar_nombre(nombre)
            if not nombre_valido:
                messages.error(request, mensaje_nombre, extra_tags='nombre')
                errores = True
        
        if not correo:
            messages.error(request, "El correo electrónico es obligatorio.", extra_tags='correo')
            errores = True
        else:
            email_valido, mensaje_email = validar_email(correo)
            if not email_valido:
                messages.error(request, mensaje_email, extra_tags='correo')
                errores = True
        
        if not fecha_nac:
            messages.error(request, "La fecha de nacimiento es obligatoria.", extra_tags='fechan')
            errores = True
        else:
            fecha_valida, mensaje_fecha = validar_fecha_nacimiento(fecha_nac)
            if not fecha_valida:
                messages.error(request, mensaje_fecha, extra_tags='fechan')
                errores = True
        
        if not contrasena:
            messages.error(request, "La contraseña es obligatoria.", extra_tags='contrasena')
            errores = True
        else:
            contrasena_valida, mensaje_contrasena = validar_contraseña(contrasena)
            if not contrasena_valida:
                messages.error(request, mensaje_contrasena, extra_tags='contrasena')
                errores = True
        
        if not confirmar_contrasena:
            messages.error(request, "Debes confirmar tu contraseña.", extra_tags='confirmar_contrasena')
            errores = True
        elif contrasena != confirmar_contrasena:
            messages.error(request, "Las contraseñas no coinciden.", extra_tags='confirmar_contrasena')
            errores = True
        
        if not rol_id:
            messages.error(request, "Debes seleccionar un tipo de cuenta.", extra_tags='rol')
            errores = True
        
        if not errores:
            if UsuarioPerfil.objects.filter(doc_user=doc_user).exists():
                messages.error(request, "El número de documento ya está registrado.", extra_tags='documento')
                errores = True
            
            if User.objects.filter(email=correo).exists():
                messages.error(request, "El correo electrónico ya está registrado.", extra_tags='correo')
                errores = True
        
        rol = None
        if rol_id:
            try:
                rol = Roles.objects.get(pk=rol_id)
                if rol.desc_rol.lower() == 'vendedor':
                    if not nit:
                        messages.error(request, "El NIT del negocio es obligatorio para vendedores.", extra_tags='nit')
                        errores = True
                    elif not nit.isdigit() or len(nit) < 8 or len(nit) > 15:
                        messages.error(request, "El NIT debe contener entre 8 y 15 dígitos.", extra_tags='nit')
                        errores = True
                    elif Negocios.objects.filter(nit_neg=nit).exists():
                        messages.error(request, "Este NIT ya está registrado.", extra_tags='nit')
                        errores = True
                    
                    if not nom_neg:
                        messages.error(request, "El nombre del negocio es obligatorio.", extra_tags='nom_neg')
                        errores = True
                    
                    if not direcc_neg:
                        messages.error(request, "La dirección del negocio es obligatoria.", extra_tags='direcc_neg')
                        errores = True
                    
                    if not fktiponeg_neg:
                        messages.error(request, "Debes seleccionar un tipo de negocio.", extra_tags='fktiponeg_neg')
                        errores = True
            except Roles.DoesNotExist:
                messages.error(request, "Rol seleccionado no válido.", extra_tags='rol')
                errores = True
        
        if errores:
            return render(request, 'Autenticacion/registro_usuario.html', {
                'roles': roles,
                'tipo_documentos': tipo_documentos,
                'tipo_negocios': tipo_negocios,
                'form_data': {
                    'tipo_doc': tipo_doc_id,
                    'documento': doc_user,
                    'nombre': nombre,
                    'correo': correo,
                    'fechan': fecha_nac,
                    'rol': rol_id,
                    'nit': nit,
                    'nom_neg': nom_neg,
                    'direcc_neg': direcc_neg,
                    'desc_neg': desc_neg,
                    'fktiponeg_neg': fktiponeg_neg
                }
            })
        
        try:
            with transaction.atomic():
                user = User.objects.create(
                    username=correo,
                    first_name=nombre.title(),
                    last_name='',
                    email=correo,
                    password=make_password(contrasena),
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                    date_joined=timezone.now()
                )
                
                perfil = UsuarioPerfil.objects.create(
                    fkuser=user,
                    fktipodoc_user_id=tipo_doc_id,
                    doc_user=doc_user,
                    fechanac_user=fecha_nac,
                    estado_user='activo',
                    fecha_creacion=timezone.now()
                )
                
                rol = Roles.objects.get(pk=rol_id)
                UsuariosRoles.objects.create(
                    fkperfil=perfil,
                    fkrol=rol
                )
                
                if rol.desc_rol.lower() == 'vendedor':
                    Negocios.objects.create(
                        nit_neg=nit,
                        nom_neg=nom_neg,
                        direcc_neg=direcc_neg,
                        desc_neg=desc_neg,
                        fktiponeg_neg_id=fktiponeg_neg,
                        fkpropietario_neg=perfil,
                        estado_neg='activo',
                        fechacreacion_neg=timezone.now(),
                        img_neg=img_neg
                    )
                
                user_auth = authenticate(request, username=correo, password=contrasena)
                if user_auth:
                    login(request, user_auth)
                    
                    if rol.desc_rol.lower() == 'vendedor':
                        messages.success(request, f"¡Cuenta y negocio creados exitosamente! Bienvenido a VECY, {nombre.title()}.")
                        return redirect('iniciar_sesion')
                    else:
                        messages.success(request, f"¡Cuenta creada exitosamente! Bienvenido a VECY, {nombre.title()}.")
                        return redirect('iniciar_sesion')
                else:
                    messages.success(request, "Usuario registrado exitosamente. Ahora puedes iniciar sesión.")
                    return redirect('iniciar_sesion')
                    
        except IntegrityError:
            messages.error(request, "Error al crear la cuenta. Por favor, intenta nuevamente.", extra_tags='general')
        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}", extra_tags='general')
    
    return render(request, 'Autenticacion/registro_usuario.html', {
        'roles': roles,
        'tipo_documentos': tipo_documentos,
        'tipo_negocios': tipo_negocios
    })

def recuperar_contrasena(request):
    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip().lower()
        
        if not correo:
            messages.error(request, "El correo electrónico es obligatorio.")
            return render(request, 'Autenticacion/recuperar_contrasena.html')
        
        try:
            validate_email(correo)
        except ValidationError:
            messages.error(request, "Por favor, introduce una dirección de correo electrónico válida.")
            return render(request, 'Autenticacion/recuperar_contrasena.html')
        
        # VERIFICAR SI EL CORREO EXISTE
        user_exists = User.objects.filter(email=correo).exists()
        
        if not user_exists:
            # Por seguridad, no revelar si el correo existe o no
            messages.success(request, "Si el correo está registrado en nuestro sistema, recibirás un código de verificación en unos momentos.")
            return render(request, 'Autenticacion/recuperar_contrasena.html')
        
        try:
            user = User.objects.get(email=correo)
            
            if not user.is_active:
                messages.error(request, "Esta cuenta está desactivada. Contacta con el administrador.")
                return render(request, 'Autenticacion/recuperar_contrasena.html')
            
            codigo_verificacion = ''.join(random.choices(string.digits, k=6))
            
            ahora = timezone.now()
            request.session['codigo_recuperacion'] = codigo_verificacion
            request.session['usuario_recuperacion_id'] = user.id
            request.session['correo_recuperacion'] = correo
            request.session['codigo_timestamp'] = ahora.isoformat()
            request.session['codigo_intentos'] = 0
            request.session.set_expiry(900)
            
            try:
                asunto = "Código de recuperación - VECY"
                mensaje = f"""
Hola {user.first_name or 'usuario/a'},

Has solicitado restablecer tu contraseña en VECY.

Tu código de verificación es: {codigo_verificacion}

Este código expirará en 15 minutos.

Si no solicitaste este cambio, por favor ignora este mensaje.

Saludos,
Equipo VECY
                """
                
                send_mail(
                    asunto,
                    mensaje.strip(),
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'soportevecy@gmail.com'),
                    [correo],
                    fail_silently=False,
                )
                
                messages.success(request, "Se ha enviado un código de verificación a tu correo electrónico.")
                return redirect('verificar_codigo')
                
            except Exception as e:
                if 'codigo_recuperacion' in request.session:
                    del request.session['codigo_recuperacion']
                if 'usuario_recuperacion_id' in request.session:
                    del request.session['usuario_recuperacion_id']
                if 'codigo_timestamp' in request.session:
                    del request.session['codigo_timestamp']
                    
                messages.error(request, "Error al enviar el email. Por favor, intenta nuevamente.")
                return render(request, 'Autenticacion/recuperar_contrasena.html')
            
        except User.DoesNotExist:
            # Esto no debería pasar porque ya verificamos con exists()
            messages.success(request, "Si el correo está registrado en nuestro sistema, recibirás un código de verificación en unos momentos.")
            return render(request, 'Autenticacion/recuperar_contrasena.html')
    
    return render(request, 'Autenticacion/recuperar_contrasena.html')

def verificar_codigo(request):
    if 'codigo_recuperacion' not in request.session:
        messages.error(request, "Debes solicitar un código de verificación primero.")
        return redirect('recuperar_contrasena')
    
    codigo_timestamp = request.session.get('codigo_timestamp')
    if codigo_timestamp:
        tiempo_expiracion = timezone.now() - timezone.datetime.fromisoformat(codigo_timestamp)
        if tiempo_expiracion.total_seconds() > 900:
            messages.error(request, "El código de verificación ha expirado.")
            del request.session['codigo_recuperacion']
            del request.session['usuario_recuperacion_id']
            del request.session['codigo_timestamp']
            return redirect('recuperar_contrasena')
    
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo', '').strip()
        codigo_correcto = request.session.get('codigo_recuperacion')
        
        if not codigo_ingresado:
            messages.error(request, "Debes ingresar el código de verificación.")
            return render(request, 'Autenticacion/verificar_codigo.html')
        
        if codigo_ingresado == codigo_correcto:
            return redirect('restablecer_contrasena')
        else:
            messages.error(request, "Código de verificación incorrecto.")
    
    return render(request, 'Autenticacion/verificar_codigo.html')

def restablecer_contrasena(request):
    if 'usuario_recuperacion_id' not in request.session:
        messages.error(request, "Sesión de recuperación no válida.")
        return redirect('recuperar_contrasena')
    
    if request.method == 'POST':
        nueva_contrasena = request.POST.get('nueva_contrasena', '')
        confirmar_contrasena = request.POST.get('confirmar_contrasena', '')
        
        errores = False
        
        if not nueva_contrasena:
            messages.error(request, "La nueva contraseña es obligatoria.")
            errores = True
        else:
            contrasena_valida, mensaje_contrasena = validar_contraseña(nueva_contrasena)
            if not contrasena_valida:
                messages.error(request, mensaje_contrasena)
                errores = True
        
        if not confirmar_contrasena:
            messages.error(request, "Debes confirmar la nueva contraseña.")
            errores = True
        elif nueva_contrasena != confirmar_contrasena:
            messages.error(request, "Las contraseñas no coinciden.")
            errores = True
        
        if errores:
            return render(request, 'Autenticacion/restablecer_contrasena.html')
        
        try:
            user_id = request.session['usuario_recuperacion_id']
            user = User.objects.get(id=user_id)
            user.password = make_password(nueva_contrasena)
            user.save()
            
            del request.session['codigo_recuperacion']
            del request.session['usuario_recuperacion_id']
            del request.session['codigo_timestamp']
            
            messages.success(request, "Contraseña restablecida exitosamente. Ahora puedes iniciar sesión.")
            return redirect('iniciar_sesion')
            
        except User.DoesNotExist:
            messages.error(request, "Error al restablecer la contraseña.")
    
    return render(request, 'Autenticacion/restablecer_contrasena.html')

@login_required
def cambiar_contrasena(request):
    if request.method == 'POST':
        contrasena_actual = request.POST.get('contrasena_actual', '')
        nueva_contrasena = request.POST.get('nueva_contrasena', '')
        confirmar_contrasena = request.POST.get('confirmar_contrasena', '')
        
        user = request.user
        
        if not check_password(contrasena_actual, user.password):
            messages.error(request, "La contraseña actual es incorrecta.")
            return render(request, 'Autenticacion/cambiar_contrasena.html')
        
        contrasena_valida, mensaje_contrasena = validar_contraseña(nueva_contrasena)
        if not contrasena_valida:
            messages.error(request, mensaje_contrasena)
            return render(request, 'Autenticacion/cambiar_contrasena.html')
        
        if nueva_contrasena != confirmar_contrasena:
            messages.error(request, "Las nuevas contraseñas no coinciden.")
            return render(request, 'Autenticacion/cambiar_contrasena.html')
        
        user.password = make_password(nueva_contrasena)
        user.save()
        
        messages.success(request, "Contraseña cambiada exitosamente.")
        return redirect('principal')
    
    return render(request, 'Autenticacion/cambiar_contrasena.html')

def verificar_email(request):
    if request.method == 'GET' and 'email' in request.GET:
        email = request.GET.get('email', '').strip().lower()
        existe = User.objects.filter(email=email).exists()
        return JsonResponse({'existe': existe})
    return JsonResponse({'error': 'Método no permitido'}, status=400)

def verificar_documento(request):
    if request.method == 'GET' and 'documento' in request.GET:
        documento = request.GET.get('documento', '').strip()
        existe = UsuarioPerfil.objects.filter(doc_user=documento).exists()
        return JsonResponse({'existe': existe})
    return JsonResponse({'error': 'Método no permitido'}, status=400)

def verificar_nit(request):
    if request.method == 'GET' and 'nit' in request.GET:
        nit = request.GET.get('nit', '').strip()
        existe = Negocios.objects.filter(nit_neg=nit).exists()
        return JsonResponse({'existe': existe})
    return JsonResponse({'error': 'Método no permitido'}, status=400)

@login_required
def cerrar_sesion(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente')
    return redirect('iniciar_sesion')