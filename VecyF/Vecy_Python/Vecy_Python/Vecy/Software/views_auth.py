from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import date, datetime
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.http import JsonResponse
import re
import random
import string

from .models import AuthUser, UsuarioPerfil, Roles, TipoDocumento, UsuariosRoles, Negocios, TipoNegocio

# ==================== VALIDACIONES AUXILIARES ====================

def validar_email(email):
    """Valida que el email tenga formato correcto"""
    try:
        validate_email(email)
        return True, ""
    except ValidationError:
        return False, "El formato del correo electrónico no es válido."

def validar_contraseña(contrasena):
    """Valida fortaleza de la contraseña"""
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
    """Valida formato del documento según el tipo"""
    if tipo_doc == '1':  # CC
        if not documento.isdigit() or len(documento) < 8 or len(documento) > 10:
            return False, "La cédula debe tener entre 8 y 10 dígitos."
    elif tipo_doc == '2':  # TI
        if not documento.isdigit() or len(documento) < 6 or len(documento) > 10:
            return False, "La tarjeta de identidad debe tener entre 6 y 10 dígitos."
    elif tipo_doc == '3':  # CE
        if len(documento) < 6:
            return False, "La cédula de extranjería debe tener al menos 6 caracteres."
    return True, ""

def validar_nombre(nombre):
    """Valida que el nombre solo contenga letras y espacios"""
    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
        return False, "El nombre solo puede contener letras y espacios."
    
    if len(nombre.strip()) < 2:
        return False, "El nombre debe tener al menos 2 caracteres."
    
    return True, ""

def validar_fecha_nacimiento(fecha_nac):
    """Valida que el usuario sea mayor de 18 años"""
    try:
        fecha_nac_date = date.fromisoformat(fecha_nac)
        hoy = date.today()
        
        # Verificar que la fecha no sea futura
        if fecha_nac_date > hoy:
            return False, "La fecha de nacimiento no puede ser futura."
        
        # Calcular edad
        edad = hoy.year - fecha_nac_date.year - ((hoy.month, hoy.day) < (fecha_nac_date.month, fecha_nac_date.day))
        
        if edad < 18:
            return False, "Debes ser mayor de 18 años para registrarte."
        
        if edad > 100:
            return False, "La edad ingresada no es válida."
            
        return True, ""
        
    except ValueError:
        return False, "La fecha de nacimiento no tiene un formato válido."

# ==================== VISTAS DE AUTENTICACIÓN ====================

def iniciar_sesion(request):
    # Limpiar mensajes antiguos
    storage = messages.get_messages(request)
    for message in storage:
        pass
    
    if request.method == "POST":
        correo = request.POST.get("correo", "").strip().lower()
        password = request.POST.get("contrasena", "")
        
        errores = False
        
        # Validaciones de entrada
        if not correo:
            messages.error(request, "El correo electrónico es obligatorio.", extra_tags='correo')
            errores = True
        else:
            email_valido, mensaje_email = validar_email(correo)
            if not email_valido:
                messages.error(request, mensaje_email, extra_tags='correo')
                errores = True
        
        if not password:
            messages.error(request, "La contraseña es obligatoria.", extra_tags='contrasena')
            errores = True
        
        if errores:
            return render(request, "Autenticacion/iniciar_sesion.html")
        
        try:
            # 1. Buscar usuario por email
            user_obj = AuthUser.objects.get(email=correo)
            print(f"🔍 Usuario encontrado: {user_obj.username}")
            print(f"🔍 Email: {user_obj.email}")
            print(f"🔍 Activo: {user_obj.is_active}")
            print(f"🔍 Password hash: {user_obj.password}")
            
            # 2. Verificar si el usuario está activo
            if user_obj.is_active != 1:  # Usar != 1 porque es IntegerField
                messages.error(request, "Tu cuenta está desactivada. Contacta al administrador.", extra_tags='general')
                return render(request, "Autenticacion/iniciar_sesion.html")
            
            # 3. Verificar contraseña DIRECTAMENTE (más confiable)
            if not check_password(password, user_obj.password):
                messages.error(request, "Contraseña incorrecta.", extra_tags='contrasena')
                return render(request, "Autenticacion/iniciar_sesion.html")
            
            # 4. Obtener perfil del usuario
            try:
                perfil = UsuarioPerfil.objects.get(fkuser=user_obj)
            except UsuarioPerfil.DoesNotExist:
                messages.error(request, "Perfil de usuario no encontrado. Contacta al administrador.", extra_tags='general')
                return render(request, "Autenticacion/iniciar_sesion.html")
            
            # 5. Verificar estado del perfil
            if perfil.estado_user != 'activo':
                messages.error(request, "Tu perfil está inactivo. Contacta al administrador.", extra_tags='general')
                return render(request, "Autenticacion/iniciar_sesion.html")
            
            # 6. Obtener rol del usuario
            rol_usuario = UsuariosRoles.objects.filter(fkperfil=perfil).first()
            if not rol_usuario:
                messages.error(request, "Rol de usuario no definido. Contacta al administrador.", extra_tags='general')
                return render(request, "Autenticacion/iniciar_sesion.html")
            
            rol_desc = rol_usuario.fkrol.desc_rol.upper()
            
            # 7. VERIFICACIÓN ADICIONAL PARA VENDEDORES
            if rol_desc == 'VENDEDOR':
                negocio = Negocios.objects.filter(fkpropietario_neg=perfil, estado_neg='activo').first()
                if not negocio:
                    messages.error(request, "No tienes un negocio activo registrado.", extra_tags='negocio')
                    return render(request, "Autenticacion/iniciar_sesion.html")
            
            # 8. AUTENTICAR Y LOGIN - FORMA CORRECTA
            # Primero autenticar correctamente
            user_auth = authenticate(request, username=user_obj.username, password=password)
            
            # Si authenticate falla pero la contraseña es correcta, usar el backend manual
            if user_auth is None:
                # Forzar el login manualmente
                user_obj.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user_obj)
            else:
                # Usar el usuario autenticado normalmente
                login(request, user_auth)
            
            # 9. Redirección según rol
            messages.success(request, f"¡Bienvenido de nuevo, {user_obj.first_name}!", extra_tags='general')
            
            if rol_desc == 'VENDEDOR':
                return redirect('dash_vendedor')
            elif rol_desc == 'CLIENTE':
                return redirect('cliente_dashboard')
            elif rol_desc == 'MODERADOR':
                return redirect('moderador_dash')
            else:
                return redirect('principal')
                
        except AuthUser.DoesNotExist:
            messages.error(request, "No existe una cuenta con este correo electrónico.", extra_tags='correo')
        except Exception as e:
            messages.error(request, f"Error interno del sistema: {str(e)}", extra_tags='general')
            # Para debugging - muestra el error completo en consola
            import traceback
            print("ERROR EN LOGIN:")
            print(traceback.format_exc())
    
    return render(request, "Autenticacion/iniciar_sesion.html")

def registro_usuario(request):
    roles = Roles.objects.exclude(desc_rol__icontains='admin')
    tipo_documentos = TipoDocumento.objects.all()
    tipo_negocios = TipoNegocio.objects.all()  # Agregar esto para el paso 2
    
    if request.method == 'POST':
        # Obtener datos del formulario
        tipo_doc_id = request.POST.get("tipo_doc", "").strip()
        doc_user = request.POST.get("documento", "").strip()
        nombre = request.POST.get("nombre", "").strip()
        correo = request.POST.get("correo", "").strip().lower()
        fecha_nac = request.POST.get("fechan", "")
        contrasena = request.POST.get("contrasena", "")
        confirmar_contrasena = request.POST.get("confirmar_contrasena", "")
        rol_id = request.POST.get("rol", "")
        
        # Datos del negocio (si es vendedor)
        nit = request.POST.get("nit", "").strip()
        nom_neg = request.POST.get("nom_neg", "").strip()
        direcc_neg = request.POST.get("direcc_neg", "").strip()
        desc_neg = request.POST.get("desc_neg", "").strip()
        fktiponeg_neg = request.POST.get("fktiponeg_neg", "")
        img_neg = request.FILES.get('img_neg')
        
        errores = False
        
        # Validaciones del usuario (igual que antes)
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
        
        # Verificar duplicados en base de datos
        if not errores:
            if UsuarioPerfil.objects.filter(doc_user=doc_user).exists():
                messages.error(request, "El número de documento ya está registrado.", extra_tags='documento')
                errores = True
            
            if AuthUser.objects.filter(email=correo).exists():
                messages.error(request, "El correo electrónico ya está registrado.", extra_tags='correo')
                errores = True
        
        # Si es vendedor, validar datos del negocio
        rol = None
        if rol_id:
            try:
                rol = Roles.objects.get(pk=rol_id)
                if rol.desc_rol.upper() == 'VENDEDOR':
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
        
        # Crear usuario y negocio en transacción atómica
        try:
            with transaction.atomic():
                # Crear usuario en AuthUser
                auth_user = AuthUser.objects.create(
                    username=correo, 
                    first_name=nombre.title(),
                    last_name='',
                    email=correo,
                    password=make_password(contrasena),
                    is_active=1,
                    is_staff=0,
                    is_superuser=0,
                    date_joined=timezone.now()
                )
                
                # Crear perfil de usuario
                perfil = UsuarioPerfil.objects.create(
                    fkuser=auth_user,
                    fktipodoc_user_id=tipo_doc_id,
                    doc_user=doc_user,
                    fechanac_user=fecha_nac,
                    estado_user='activo',
                    fecha_creacion=timezone.now()
                )
                
                # Asignar rol
                rol = Roles.objects.get(pk=rol_id)
                UsuariosRoles.objects.create(
                    fkperfil=perfil,
                    fkrol=rol
                )
                
                # Si es vendedor, crear negocio
                if rol.desc_rol.upper() == 'VENDEDOR':
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
                
                # Iniciar sesión automáticamente
                user = authenticate(request, username=correo, password=contrasena)
                if user:
                    login(request, user)
                    
                    if rol.desc_rol.upper() == 'VENDEDOR':
                        messages.success(request, f"¡Cuenta y negocio creados exitosamente! Bienvenido a VECY, {nombre.title()}.")
                    else:
                        messages.success(request, f"¡Cuenta creada exitosamente! Bienvenido a VECY, {nombre.title()}.")
                    
                    return redirect('principal')
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

def registro_negocio(request):
    tipo_negocios = TipoNegocio.objects.all()
    perfil_id = request.session.get('perfil_registro_negocio')
    
    if not perfil_id:
        messages.error(request, "Primero debes completar tu registro de usuario.")
        return redirect('registro_usuario')
    
    try:
        propietario = UsuarioPerfil.objects.get(pk=perfil_id)
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect('registro_usuario')
    
    if request.method == 'POST':
        nit = request.POST.get('nit', '').strip()
        nombre = request.POST.get('nom_neg', '').strip()
        direccion = request.POST.get('direcc_neg', '').strip()
        descripcion = request.POST.get('desc_neg', '').strip()
        tipo_neg = request.POST.get('fktiponeg_neg', '')
        imagen = request.FILES.get('img_neg')
        
        errores = False
        
        # Validaciones del negocio
        if not nit:
            messages.error(request, "El NIT es obligatorio.", extra_tags='nit')
            errores = True
        elif not nit.isdigit() or len(nit) < 8 or len(nit) > 15:
            messages.error(request, "El NIT debe contener entre 8 y 15 dígitos.", extra_tags='nit')
            errores = True
        elif Negocios.objects.filter(nit_neg=nit).exists():
            messages.error(request, "Este NIT ya está registrado.", extra_tags='nit')
            errores = True
        
        if not nombre:
            messages.error(request, "El nombre del negocio es obligatorio.", extra_tags='nom_neg')
            errores = True
        elif len(nombre) < 3:
            messages.error(request, "El nombre del negocio debe tener al menos 3 caracteres.", extra_tags='nom_neg')
            errores = True
        
        if not direccion:
            messages.error(request, "La dirección del negocio es obligatoria.", extra_tags='direcc_neg')
            errores = True
        
        if not tipo_neg:
            messages.error(request, "Debes seleccionar un tipo de negocio.", extra_tags='fktiponeg_neg')
            errores = True
        
        if errores:
            return render(request, 'Autenticacion/registroNegocio.html', {
                'tipo_negocios': tipo_negocios,
                'form_data': {
                    'nit': nit,
                    'nom_neg': nombre,
                    'direcc_neg': direccion,
                    'desc_neg': descripcion,
                    'fktiponeg_neg': tipo_neg
                }
            })
        
        try:
            # Crear negocio
            Negocios.objects.create(
                nit_neg=nit,
                nom_neg=nombre,
                direcc_neg=direccion,
                desc_neg=descripcion,
                fktiponeg_neg_id=tipo_neg,
                fkpropietario_neg=propietario,
                estado_neg='activo',
                fechacreacion_neg=timezone.now(),
                img_neg=imagen
            )
            
            # Limpiar sesión
            del request.session['perfil_registro_negocio']
            
            messages.success(request, "¡Negocio registrado exitosamente! Ahora puedes acceder a todas las funcionalidades de vendedor.")
            return redirect('pagina_principal')
            
        except IntegrityError:
            messages.error(request, "Error al registrar el negocio. El NIT ya existe.", extra_tags='nit')
        except Exception as e:
            messages.error(request, f"Error al registrar el negocio: {str(e)}", extra_tags='general')
    
    return render(request, 'Autenticacion/registro_negocio.html', {
        'tipo_negocios': tipo_negocios
    })

# ==================== VISTAS DE RECUPERACIÓN ====================

def recuperar_contrasena(request):
    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip().lower()
        
        if not correo:
            messages.error(request, "El correo electrónico es obligatorio.")
            return render(request, 'Autenticacion/recuperar_contrasena.html')
        
        email_valido, mensaje_email = validar_email(correo)
        if not email_valido:
            messages.error(request, mensaje_email)
            return render(request, 'Autenticacion/recuperar_contrasena.html')
        
        try:
            user = AuthUser.objects.get(email=correo)
            
            # Generar código de verificación
            codigo_verificacion = ''.join(random.choices(string.digits, k=6))
            request.session['codigo_recuperacion'] = codigo_verificacion
            request.session['usuario_recuperacion_id'] = user.id
            request.session['codigo_timestamp'] = timezone.now().isoformat()
            
            # ENVIAR CÓDIGO POR EMAIL
            try:
                from django.core.mail import send_mail
                from django.conf import settings  # ¡IMPORTANTE! Agregar esta línea
                
                asunto = "Código de recuperación - VECY"
                mensaje = f"""
Hola {user.first_name},

Has solicitado restablecer tu contraseña en VECY.

Tu código de verificación es: {codigo_verificacion}

Este código expirará en 15 minutos.

Si no solicitaste este cambio, por favor ignora este mensaje.

Saludos,
Equipo VECY
                """
                
                send_mail(
                    asunto,
                    mensaje.strip(),  # strip() para limpiar espacios
                    settings.DEFAULT_FROM_EMAIL,  # Usar desde settings
                    [correo],
                    fail_silently=False,
                )
                
                messages.success(request, "Se ha enviado un código de verificación a tu correo electrónico.")
                return redirect('verificar_codigo')
                
            except Exception as e:
                messages.error(request, f"Error al enviar el email: {str(e)}")
                # Mantener los datos en sesión para reintentar
                return render(request, 'Autenticacion/recuperar_contrasena.html')
            
        except AuthUser.DoesNotExist:
            messages.error(request, "No existe una cuenta con este correo electrónico.")
    
    return render(request, 'Autenticacion/recuperar_contrasena.html')

def verificar_codigo(request):
    if 'codigo_recuperacion' not in request.session:
        messages.error(request, "Debes solicitar un código de verificación primero.")
        return redirect('recuperar_contrasena')
    
    # Verificar expiración del código (15 minutos)
    codigo_timestamp = request.session.get('codigo_timestamp')
    if codigo_timestamp:
        tiempo_expiracion = timezone.now() - timezone.datetime.fromisoformat(codigo_timestamp)
        if tiempo_expiracion.total_seconds() > 900:  # 15 minutos
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
            user = AuthUser.objects.get(id=user_id)
            user.password = make_password(nueva_contrasena)
            user.save()
            
            # Limpiar sesión de recuperación
            del request.session['codigo_recuperacion']
            del request.session['usuario_recuperacion_id']
            del request.session['codigo_timestamp']
            
            messages.success(request, "Contraseña restablecida exitosamente. Ahora puedes iniciar sesión.")
            return redirect('iniciar_sesion')
            
        except AuthUser.DoesNotExist:
            messages.error(request, "Error al restablecer la contraseña.")
    
    return render(request, 'Autenticacion/restablecer_contrasena.html')

# ==================== VISTAS ADICIONALES ====================

@login_required
def cambiar_contrasena(request):
    if request.method == 'POST':
        contrasena_actual = request.POST.get('contrasena_actual', '')
        nueva_contrasena = request.POST.get('nueva_contrasena', '')
        confirmar_contrasena = request.POST.get('confirmar_contrasena', '')
        
        user = request.user
        
        # Verificar contraseña actual
        if not check_password(contrasena_actual, user.password):
            messages.error(request, "La contraseña actual es incorrecta.")
            return render(request, 'Autenticacion/cambiar_contrasena.html')
        
        # Validar nueva contraseña
        contrasena_valida, mensaje_contrasena = validar_contraseña(nueva_contrasena)
        if not contrasena_valida:
            messages.error(request, mensaje_contrasena)
            return render(request, 'Autenticacion/cambiar_contrasena.html')
        
        if nueva_contrasena != confirmar_contrasena:
            messages.error(request, "Las nuevas contraseñas no coinciden.")
            return render(request, 'Autenticacion/cambiar_contrasena.html')
        
        # Cambiar contraseña
        user.password = make_password(nueva_contrasena)
        user.save()
        
        messages.success(request, "Contraseña cambiada exitosamente.")
        return redirect('principal')
    
    return render(request, 'Autenticacion/cambiar_contrasena.html')

def cerrar_sesion(request):
    logout(request)
    # Limpiar sesiones personalizadas
    for key in ['perfil_registro_negocio', 'codigo_recuperacion', 'usuario_recuperacion_id', 'codigo_timestamp']:
        if key in request.session:
            del request.session[key]
    
    messages.success(request, "Sesión cerrada exitosamente.")
    return redirect('inicio')

# ==================== APIs AUXILIARES ====================

def verificar_email(request):
    """API para verificar si un email ya existe (AJAX)"""
    if request.method == 'GET' and 'email' in request.GET:
        email = request.GET.get('email', '').strip().lower()
        existe = AuthUser.objects.filter(email=email).exists()
        return JsonResponse({'existe': existe})
    return JsonResponse({'error': 'Método no permitido'}, status=400)

def verificar_documento(request):
    """API para verificar si un documento ya existe (AJAX)"""
    if request.method == 'GET' and 'documento' in request.GET:
        documento = request.GET.get('documento', '').strip()
        existe = UsuarioPerfil.objects.filter(doc_user=documento).exists()
        return JsonResponse({'existe': existe})
    return JsonResponse({'error': 'Método no permitido'}, status=400)

def verificar_nit(request):
    """API para verificar si un NIT ya existe (AJAX)"""
    if request.method == 'GET' and 'nit' in request.GET:
        nit = request.GET.get('nit', '').strip()
        existe = Negocios.objects.filter(nit_neg=nit).exists()
        return JsonResponse({'existe': existe})
    return JsonResponse({'error': 'Método no permitido'}, status=400)