from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from Software.models import Negocios, UsuarioPerfil, Pedidos, DetallesPedido, ResenasNegocios, AuthUser, Roles, TipoDocumento, UsuariosRoles, TipoNegocio, Productos, CategoriaProductos, Reportes
from django.utils import timezone
from django.db import connection
from django.db.models import Count, Avg
from django.contrib import messages
from django.db.models import Q
from datetime import timedelta
from collections import Counter
from django.db.models.functions import ExtractMonth, ExtractYear
from Software.email_utils import enviar_notificacion_simple

# Importaciones para correos
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def obtener_datos_moderador(request):
    """Función auxiliar para obtener datos del moderador"""
    try:
        # CORREGIDO: Usar UsuarioPerfil directamente del request.user
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        
        return {
            'nombre_usuario': request.user.first_name,
            'perfil': perfil,
            'auth_user': request.user,
        }
    except (AuthUser.DoesNotExist, UsuarioPerfil.DoesNotExist):
        return None

def is_moderator(user):
    """Verifica si el usuario es moderador - CORREGIDO"""
    if not user.is_authenticated:
        return False
        
    try:
        # CORREGIDO: Usar UsuarioPerfil directamente
        perfil = UsuarioPerfil.objects.get(fkuser=user)
        
        # Verificar si tiene rol de moderador
        return UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
    except (AuthUser.DoesNotExist, UsuarioPerfil.DoesNotExist):
        return False

# VISTA PRINCIPAL DEL MODERADOR - CORREGIDA
@login_required(login_url='/auth/login/')
def moderador_dash(request):
    """Vista principal del dashboard del moderador con verificación corregida"""
    try:
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            messages.error(request, "Debes iniciar sesión para acceder al panel de moderador.")
            return redirect('iniciar_sesion')
        
        # Obtener perfil del usuario - CORREGIDO
        try:
            # CORREGIDO: Usar UsuarioPerfil directamente
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        except UsuarioPerfil.DoesNotExist:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('iniciar_sesion')
        
        # Verificar si es moderador - FORMA MÁS ROBUSTA
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect('principal')
        
        # ============ CÓDIGO DE ESTADÍSTICAS COMPLETAS ============
        # Obtener el rango de tiempo (último año)
        fecha_limite = timezone.now() - timedelta(days=365)
        
        # 1. REGISTRO DE USUARIOS POR MES - CORREGIDO: Usar AuthUser
        usuarios_por_mes = AuthUser.objects.filter(
            date_joined__gte=fecha_limite
        ).annotate(
            mes=ExtractMonth('date_joined'),
            ano=ExtractYear('date_joined')
        ).values('mes', 'ano').annotate(total=Count('pk')).order_by('ano', 'mes')
        
        # Preparar datos para el gráfico de usuarios por mes
        meses_labels = []
        usuarios_data = []
        
        # Crear nombres de meses en español
        meses_espanol = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }
        
        for item in usuarios_por_mes:
            mes_num = item['mes']
            ano = item['ano']
            meses_labels.append(f"{meses_espanol.get(mes_num, mes_num)}/{str(ano)[-2:]}")
            usuarios_data.append(item['total'])
        
        # 2. NEGOCIOS POR CATEGORÍA
        negocios_por_categoria = Negocios.objects.values(
            'fktiponeg_neg__desc_tiponeg'
        ).annotate(total=Count('pkid_neg')).order_by('-total')[:10]
        
        categorias_nombres = [item['fktiponeg_neg__desc_tiponeg'] for item in negocios_por_categoria]
        categorias_totales = [item['total'] for item in negocios_por_categoria]
        
        # 3. REPORTES POR TIPO
        reportes_por_tipo = Reportes.objects.values('motivo').annotate(
            total=Count('pkid_reporte')
        ).order_by('-total')
        
        reportes_tipos = [item['motivo'] for item in reportes_por_tipo]
        reportes_totales = [item['total'] for item in reportes_por_tipo]
        
        # 4. ACTIVIDAD DE MODERACIÓN
        acciones_moderacion = [
            {'tipo_accion': 'Negocios Aprobados', 'total': Negocios.objects.filter(estado_neg='activo').count()},
            {'tipo_accion': 'Negocios Rechazados', 'total': Negocios.objects.filter(estado_neg='inactivo').count()},
            {'tipo_accion': 'Negocios Suspendidos', 'total': Negocios.objects.filter(estado_neg='suspendido').count()},
            {'tipo_accion': 'Reportes Atendidos', 'total': Reportes.objects.filter(estado_reporte='atendido').count()},
            {'tipo_accion': 'Reseñas Moderadas', 'total': ResenasNegocios.objects.filter(~Q(estado_resena='pendiente')).count()},
        ]
        
        acciones_tipos = [item['tipo_accion'] for item in acciones_moderacion]
        acciones_totales = [item['total'] for item in acciones_moderacion]
        
        # MÉTRICAS PRINCIPALES - CORREGIDO: Usar AuthUser
        total_usuarios = AuthUser.objects.count()
        usuarios_activos = AuthUser.objects.filter(is_active=1).count()
        total_negocios = Negocios.objects.count()
        negocios_activos = Negocios.objects.filter(estado_neg='activo').count()
        negocios_suspendidos = Negocios.objects.filter(estado_neg='suspendido').count()
        negocios_inactivos = Negocios.objects.filter(estado_neg='inactivo').count()
        total_resenas = ResenasNegocios.objects.count()
        
        resenas_activas = ResenasNegocios.objects.filter(estado_resena='activa').count()
        
        # Calcular promedio de estrellas
        promedio_estrellas = ResenasNegocios.objects.aggregate(
            avg_rating=Avg('estrellas')
        )['avg_rating'] or 0
        
        contexto = {
            'nombre': request.user.first_name or request.user.username,
            'perfil': perfil,
            
            # Métricas principales para las tarjetas
            'total_usuarios': total_usuarios,
            'usuarios_activos': usuarios_activos,
            'total_negocios': total_negocios,
            'negocios_activos': negocios_activos,
            'negocios_suspendidos': negocios_suspendidos,
            'negocios_inactivos': negocios_inactivos,
            'total_resenas': total_resenas,
            'resenas_activas': resenas_activas,
            'promedio_estrellas': round(promedio_estrellas, 1),
            
            # Datos para gráficas
            'meses_labels': meses_labels,
            'usuarios_data': usuarios_data,
            'categorias_nombres': categorias_nombres,
            'categorias_totales': categorias_totales,
            'reportes_tipos': reportes_tipos,
            'reportes_totales': reportes_totales,
            'acciones_tipos': acciones_tipos,
            'acciones_totales': acciones_totales,
            'negocios_por_categoria': negocios_por_categoria,
        }
        
        return render(request, 'Moderador/estadisticas.html', contexto)
        
    except Exception as e:
        messages.error(request, f"Error al cargar el dashboard: {str(e)}")
        return redirect('principal')

@login_required(login_url='/auth/login/')
def gestion_usuarios(request):
    """Vista para gestión de usuarios por parte del moderador - CORREGIDA"""
    try:
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            messages.error(request, "Debes iniciar sesión.")
            return redirect('iniciar_sesion')
        
        # Obtener perfil del usuario - CORREGIDO
        try:
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        except UsuarioPerfil.DoesNotExist:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('iniciar_sesion')
        
        # Verificar si es moderador
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect('principal')
        
        # Procesar cambio de estado si viene por POST
        if request.method == 'POST':
            usuario_id = request.POST.get('usuario_id')
            accion = request.POST.get('accion')
            
            try:
                perfil_usuario = UsuarioPerfil.objects.get(id=usuario_id)
                user = perfil_usuario.fkuser
                
                # Verificar que no sea un moderador
                es_moderador_usuario = UsuariosRoles.objects.filter(
                    fkperfil=perfil_usuario, 
                    fkrol__desc_rol__iexact='moderador'
                ).exists()
                
                if es_moderador_usuario:
                    messages.error(request, 'No puedes modificar usuarios con rol de MODERADOR')
                    return redirect('gestion_usuarios')
                
                if accion == 'cambiar_estado':
                    nuevo_estado = 'inactivo' if perfil_usuario.estado_user == 'activo' else 'activo'
                    estado_anterior = perfil_usuario.estado_user
                    perfil_usuario.estado_user = nuevo_estado
                    perfil_usuario.save()
                    
                    # También actualizar el estado en auth_user
                    user.is_active = 1 if nuevo_estado == 'activo' else 0
                    user.save()
                    
                    # ENVIAR CORREO DE NOTIFICACIÓN
                    accion_correo = 'bloquear' if nuevo_estado == 'inactivo' else 'desbloquear'
                    resultado = enviar_notificacion_simple(user, accion_correo)
                    
                    mensaje = f'Estado del usuario {user.username} cambiado a {nuevo_estado}'
                    if resultado['success']:
                        if resultado['enviado_a'] == user.email:
                            mensaje += ' - Notificación enviada al usuario'
                        else:
                            mensaje += ' - Notificación enviada al administrador'
                    else:
                        mensaje += f' - Error: {resultado["error"]}'
                    
                    messages.success(request, mensaje)
                
                elif accion == 'eliminar':
                    username = user.username
                    
                    # Enviar notificación antes de eliminar
                    resultado = enviar_notificacion_simple(user, 'eliminar')
                    
                    # Eliminar el perfil y el usuario
                    user.delete()
                    
                    mensaje = f'Usuario {username} eliminado correctamente'
                    if resultado['success']:
                        if resultado['enviado_a'] == user.email:
                            mensaje += ' - Notificación enviada al usuario'
                        else:
                            mensaje += ' - Notificación enviada al administrador'
                    else:
                        mensaje += f' - Error: {resultado["error"]}'
                    
                    messages.success(request, mensaje)
                
            except UsuarioPerfil.DoesNotExist:
                messages.error(request, 'Usuario no encontrado')
            except Exception as e:
                messages.error(request, f'Error al procesar la solicitud: {str(e)}')
            
            return redirect('gestion_usuarios')
        
        # Obtener parámetros de filtrado
        search_query = request.GET.get('search', '')
        rol_filter = request.GET.get('rol', '')
        estado_filter = request.GET.get('estado', '')
        
        # Obtener usuarios EXCLUYENDO MODERADORES usando subquery
        perfiles_moderadores = UsuariosRoles.objects.filter(
            fkrol__desc_rol__iexact='moderador'
        ).values_list('fkperfil_id', flat=True)
        
        # Consulta base excluyendo moderadores
        usuarios_perfiles = UsuarioPerfil.objects.select_related(
            'fkuser', 'fktipodoc_user'
        ).prefetch_related('usuariosroles_set__fkrol').exclude(
            id__in=perfiles_moderadores
        )
        
        # Aplicar filtros
        if search_query:
            usuarios_perfiles = usuarios_perfiles.filter(
                Q(fkuser__first_name__icontains=search_query) |
                Q(fkuser__last_name__icontains=search_query) |
                Q(fkuser__username__icontains=search_query) |
                Q(fkuser__email__icontains=search_query) |
                Q(doc_user__icontains=search_query)
            )
        
        if rol_filter:
            usuarios_perfiles = usuarios_perfiles.filter(
                usuariosroles_set__fkrol__desc_rol=rol_filter
            ).distinct()
        
        if estado_filter:
            usuarios_perfiles = usuarios_perfiles.filter(estado_user=estado_filter)
        
        # Preparar datos para el template
        usuarios_data = []
        for perfil_usuario in usuarios_perfiles:
            user = perfil_usuario.fkuser
            
            # Obtener roles del usuario
            roles_usuario = UsuariosRoles.objects.filter(fkperfil=perfil_usuario)
            roles_nombres = [rol.fkrol.desc_rol for rol in roles_usuario]
            
            # Determinar rol principal (excluyendo moderador)
            rol_principal = 'CLIENTE'
            for rol_nombre in roles_nombres:
                if rol_nombre.lower() != 'moderador':
                    rol_principal = rol_nombre
                    break
            
            # Construir nombre completo
            nombre_completo = f"{user.first_name} {user.last_name}".strip()
            if not nombre_completo:
                nombre_completo = user.username
            
            # Obtener negocios si es vendedor
            negocios = []
            if rol_principal == 'VENDEDOR':
                negocios_vendedor = Negocios.objects.filter(
                    fkpropietario_neg=perfil_usuario.id
                ).values('pkid_neg', 'nom_neg', 'estado_neg')
                negocios = list(negocios_vendedor)
            
            # Manejar imagen del usuario
            imagen_url = ''
            if perfil_usuario.img_user:
                try:
                    imagen_url = perfil_usuario.img_user.url
                except:
                    imagen_url = '/static/images/default-user.png'
            else:
                imagen_url = '/static/images/default-user.png'
            
            usuarios_data.append({
                'id': perfil_usuario.id,
                'user_id': user.id,
                'nombre': nombre_completo,
                'email': user.email,
                'username': user.username,
                'documento': perfil_usuario.doc_user,
                'tipo_documento': perfil_usuario.fktipodoc_user.desc_doc if perfil_usuario.fktipodoc_user else 'No especificado',
                'fecha_nacimiento': perfil_usuario.fechanac_user,
                'estado': perfil_usuario.estado_user,
                'rol': rol_principal,
                'roles': roles_nombres,
                'img_user': imagen_url,
                'fecha_registro': user.date_joined,
                'ultimo_login': user.last_login,
                'negocios': negocios
            })
        
        # Aplicar filtros adicionales en memoria para búsqueda más precisa
        if search_query:
            search_lower = search_query.lower()
            usuarios_data = [
                u for u in usuarios_data 
                if (search_lower in u['nombre'].lower() or 
                    search_lower in u['email'].lower() or
                    search_lower in u['username'].lower() or
                    search_lower in u['documento'].lower())
            ]
        
        # Aplicar filtros de rol y estado en memoria (para mayor precisión)
        if rol_filter:
            usuarios_data = [u for u in usuarios_data if u['rol'] == rol_filter]
        
        if estado_filter:
            usuarios_data = [u for u in usuarios_data if u['estado'] == estado_filter]
        
        # **CORRECCIÓN: CALCULAR ESTADÍSTICAS DIRECTAMENTE DE LA BASE DE DATOS**
        # Obtener todos los perfiles excluyendo moderadores para estadísticas
        perfiles_totales = UsuarioPerfil.objects.exclude(
            id__in=perfiles_moderadores
        )
        
        # Calcular estadísticas desde la base de datos (más preciso)
        total_usuarios = perfiles_totales.count()
        usuarios_activos = perfiles_totales.filter(estado_user='activo').count()
        
        # Contar clientes y vendedores por roles
        perfiles_clientes = UsuariosRoles.objects.filter(
            fkrol__desc_rol='CLIENTE'
        ).exclude(fkperfil__id__in=perfiles_moderadores).values('fkperfil').distinct().count()
        
        perfiles_vendedores = UsuariosRoles.objects.filter(
            fkrol__desc_rol='VENDEDOR'
        ).exclude(fkperfil__id__in=perfiles_moderadores).values('fkperfil').distinct().count()
        
        context = {
            'nombre': request.user.first_name or request.user.username,
            'perfil': perfil,
            'usuarios': usuarios_data,
            'total_usuarios': total_usuarios,
            'usuarios_activos': usuarios_activos,
            'total_clientes': perfiles_clientes,
            'total_vendedores': perfiles_vendedores,
            'titulo_pagina': 'Gestión de Usuarios',
            'search_query': search_query,
            'rol_filter': rol_filter,
            'estado_filter': estado_filter
        }
        
        return render(request, 'Moderador/gestion_usuarios.html', context)
    
    except Exception as e:
        print(f"ERROR en gestión de usuarios: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
        return redirect('principal')

# GESTIÓN DE NEGOCIOS - CORREGIDA
@login_required(login_url='/auth/login/')
def gestion_negocios(request):
    """Vista principal de gestión de negocios para moderadores - CORREGIDA"""    
    try:
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            messages.error(request, "Debes iniciar sesión.")
            return redirect('iniciar_sesion')
        
        # Obtener perfil del usuario - CORREGIDO
        try:
            # CORREGIDO: Usar UsuarioPerfil directamente
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        except UsuarioPerfil.DoesNotExist:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('iniciar_sesion')
        
        # Verificar si es moderador
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect('principal')
        
        # Procesar acciones por POST
        if request.method == 'POST':
            negocio_id = request.POST.get('negocio_id')
            accion = request.POST.get('accion')
            nuevo_estado = request.POST.get('nuevo_estado')
            
            try:
                negocio = Negocios.objects.get(pkid_neg=negocio_id)
                
                if accion == 'cambiar_estado' and nuevo_estado:
                    # Validar estado
                    if nuevo_estado in ['activo', 'inactivo', 'suspendido']:
                        estado_anterior = negocio.estado_neg
                        negocio.estado_neg = nuevo_estado
                        negocio.save()
                        
                        # Mapear estados para mensaje
                        estado_map = {
                            'activo': 'Activo',
                            'inactivo': 'Rechazado', 
                            'suspendido': 'Suspendido'
                        }
                        
                        messages.success(
                            request, 
                            f'Estado del negocio "{negocio.nom_neg}" cambiado de ' 
                            f'{estado_map.get(estado_anterior, estado_anterior)} a '
                            f'{estado_map.get(nuevo_estado, nuevo_estado)}'
                        )
                    else:
                        messages.error(request, 'Estado inválido')
                
                elif accion == 'eliminar':
                    nombre_negocio = negocio.nom_neg
                    negocio.delete()
                    messages.success(request, f'Negocios "{nombre_negocio}" eliminado correctamente')
                
                else:
                    messages.error(request, 'Acción no válida')
                    
            except Negocios.DoesNotExist:
                messages.error(request, 'Negocio no encontrado')
            except Exception as e:
                messages.error(request, f'Error al procesar la solicitud: {str(e)}')
            
            return redirect('gestion_negocios')
        
        # Obtener parámetros de filtrado
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        
        # Consulta base - todos los negocios
        negocios_list = Negocios.objects.select_related(
            'fkpropietario_neg__fkuser', 
            'fktiponeg_neg'
        ).all().order_by('-fechacreacion_neg')
        
        # Aplicar filtros
        if search_query:
            negocios_list = negocios_list.filter(
                Q(nom_neg__icontains=search_query) |
                Q(nit_neg__icontains=search_query) |
                Q(fkpropietario_neg__fkuser__first_name__icontains=search_query) |
                Q(fkpropietario_neg__fkuser__last_name__icontains=search_query)
            )
        
        if status_filter:
            # Mapeo inverso de estados del frontend a estados de la BD
            status_map = {
                'Activo': 'activo',
                'Rechazado': 'inactivo',
                'Suspendido': 'suspendido'
            }
            estado_db = status_map.get(status_filter)
            if estado_db:
                negocios_list = negocios_list.filter(estado_neg=estado_db)
        
        # Preparar datos para el template
        negocios_data = []
        for negocio in negocios_list:
            # Obtener estadísticas de reseñas
            reseñas_stats = ResenasNegocios.objects.filter(
                fknegocio_resena=negocio.pkid_neg,
                estado_resena='activa'
            ).aggregate(
                total_reseñas=Count('pkid_resena'),
                promedio_estrellas=Avg('estrellas')
            )
            
            # Obtener productos del negocio
            total_productos = Productos.objects.filter(
                fknegocioasociado_prod=negocio.pkid_neg
            ).count()
            
            # Mapear estados de la base de datos a los estados del frontend
            estado_map = {
                'activo': 'Activo',
                'inactivo': 'Rechazado', 
                'suspendido': 'Suspendido'
            }
            
            estado_display = estado_map.get(negocio.estado_neg, 'Pendiente')
            
            # Obtener información del propietario de manera segura
            propietario_user = negocio.fkpropietario_neg.fkuser
            nombre_propietario = f"{propietario_user.first_name} {propietario_user.last_name}".strip()
            if not nombre_propietario:
                nombre_propietario = propietario_user.username
            
            # Manejar imagen del negocio
            imagen_url = ''
            if negocio.img_neg:
                try:
                    imagen_url = negocio.img_neg.url
                except:
                    imagen_url = '/static/images/default-business.jpg'
            else:
                imagen_url = '/static/images/default-business.jpg'
            
            negocios_data.append({
                'id': negocio.pkid_neg,
                'nit': negocio.nit_neg,
                'nombre': negocio.nom_neg,
                'direccion': negocio.direcc_neg,
                'descripcion': negocio.desc_neg or 'Sin descripción',
                'categoria': negocio.fktiponeg_neg.desc_tiponeg,
                'estado': estado_display,
                'estado_db': negocio.estado_neg,
                'telefono': propietario_user.email,  # Usando email como contacto
                'propietario': nombre_propietario,
                'email_propietario': propietario_user.email,
                'imagen': imagen_url,
                'fecha_creacion': negocio.fechacreacion_neg,
                'total_reseñas': reseñas_stats['total_reseñas'] or 0,
                'promedio_estrellas': round(reseñas_stats['promedio_estrellas'] or 0, 1),
                'total_productos': total_productos,
            })
        
        context = {
            'nombre': request.user.first_name or request.user.username,
            'perfil': perfil,
            'negocios': negocios_data,
            'titulo_pagina': 'Gestión de Negocios',
            'search_query': search_query,
            'status_filter': status_filter
        }
        
        return render(request, 'Moderador/gestion_negocios.html', context)
    
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('principal')

# ==================== APIs para Gestión de Negocios ====================

@login_required(login_url='/auth/login/')
def detalle_negocio_json(request, negocio_id):
    """API para obtener detalles completos de un negocio (para modal)"""
    try:
        # Verificar permisos de moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'error': 'No tienes permisos de moderador'}, status=403)
        
        negocio = Negocios.objects.select_related(
            'fkpropietario_neg__fkuser', 
            'fktiponeg_neg'
        ).get(pkid_neg=negocio_id)
        
        # Mapear estados
        estado_map = {
            'activo': 'Activo',
            'inactivo': 'Rechazado', 
            'suspendido': 'Suspendido'
        }
        
        estado_display = estado_map.get(negocio.estado_neg, 'Pendiente')
        
        # Información del propietario
        propietario_user = negocio.fkpropietario_neg.fkuser
        nombre_propietario = f"{propietario_user.first_name} {propietario_user.last_name}".strip()
        if not nombre_propietario:
            nombre_propietario = propietario_user.username
        
        # Manejar imagen
        imagen_url = ''
        if negocio.img_neg:
            try:
                imagen_url = request.build_absolute_uri(negocio.img_neg.url)
            except:
                imagen_url = '/static/images/default-business.jpg'
        else:
            imagen_url = '/static/images/default-business.jpg'
        
        datos_negocio = {
            'id': negocio.pkid_neg,
            'nit': negocio.nit_neg,
            'name': negocio.nom_neg,
            'address': negocio.direcc_neg,
            'category': negocio.fktiponeg_neg.desc_tiponeg,
            'status': estado_display,
            'phone': propietario_user.email,
            'description': negocio.desc_neg or 'Sin descripción',
            'image': imagen_url,
            'propietario': nombre_propietario,
            'fecha_registro': negocio.fechacreacion_neg.strftime("%d/%m/%Y %H:%M")
        }
        
        return JsonResponse(datos_negocio)
    except Negocios.DoesNotExist:
        return JsonResponse({'error': 'Negocio no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='/auth/login/')
def resenas_negocio_json(request, negocio_id):
    """API para obtener reseñas de un negocio"""
    try:
        # Verificar permisos de moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'error': 'No tienes permisos de moderador'}, status=403)
        
        reseñas = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio_id, 
            estado_resena='activa'
        ).select_related('fkusuario_resena__fkuser').order_by('-fecha_resena')
        
        reseñas_data = []
        for reseña in reseñas:
            usuario = reseña.fkusuario_resena.fkuser
            nombre_usuario = f"{usuario.first_name} {usuario.last_name}".strip()
            if not nombre_usuario:
                nombre_usuario = usuario.username
                
            reseñas_data.append({
                'user': nombre_usuario,
                'rating': reseña.estrellas,
                'comment': reseña.comentario or 'Sin comentario',
                'date': reseña.fecha_resena.strftime("%d/%m/%Y %H:%M")
            })
        
        return JsonResponse(reseñas_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='/auth/login/')
def productos_negocio_json(request, negocio_id):
    """API para obtener productos de un negocio"""
    try:
        # Verificar permisos de moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'error': 'No tienes permisos de moderador'}, status=403)
        
        productos = Productos.objects.filter(
            fknegocioasociado_prod=negocio_id
        ).select_related('fkcategoria_prod')
        
        productos_data = []
        for producto in productos:
            # Manejar imagen del producto
            imagen_url = ''
            if producto.img_prod:
                try:
                    imagen_url = request.build_absolute_uri(producto.img_prod.url)
                except:
                    imagen_url = '/static/images/default-product.jpg'
            else:
                imagen_url = '/static/images/default-product.jpg'
            
            productos_data.append({
                'id': producto.pkid_prod,
                'nombre': producto.nom_prod,
                'precio': str(producto.precio_prod),
                'descripcion': producto.desc_prod or 'Sin descripción',
                'categoria': producto.fkcategoria_prod.desc_cp,
                'stock': producto.stock_prod,
                'estado': producto.estado_prod,
                'imagen': imagen_url
            })
        
        return JsonResponse(productos_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='/auth/login/')
@csrf_exempt
@require_http_methods(["POST"])
def cambiar_estado_negocio(request, negocio_id):
    """API para cambiar el estado de un negocio"""
    try:
        # Verificar permisos de moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'error': 'No tienes permisos de moderador'}, status=403)
        
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        
        # Validar estado
        if nuevo_estado not in ['activo', 'inactivo', 'suspendido']:
            return JsonResponse({'error': 'Estado inválido'}, status=400)
        
        negocio = Negocios.objects.get(pkid_neg=negocio_id)
        negocio.estado_neg = nuevo_estado
        negocio.save()
        
        # Mapear estado para respuesta
        estado_map = {
            'activo': 'Activo',
            'inactivo': 'Rechazado', 
            'suspendido': 'Suspendido'
        }
        
        return JsonResponse({
            'success': True, 
            'nuevo_estado': estado_map.get(nuevo_estado, 'Pendiente'),
            'mensaje': f'Estado del negocio cambiado a {estado_map.get(nuevo_estado, "Pendiente")}'
        })
        
    except Negocios.DoesNotExist:
        return JsonResponse({'error': 'Negocio no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='/auth/login/')
@csrf_exempt
@require_http_methods(["POST"])
def eliminar_negocio(request, negocio_id):
    """API para eliminar un negocio"""
    try:
        # Verificar permisos de moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'error': 'No tienes permisos de moderador'}, status=403)
        
        negocio = Negocios.objects.get(pkid_neg=negocio_id)
        nombre_negocio = negocio.nom_neg
        negocio.delete()
        
        return JsonResponse({
            'success': True, 
            'mensaje': f'Negocio "{nombre_negocio}" eliminado correctamente'
        })
        
    except Negocios.DoesNotExist:
        return JsonResponse({'error': 'Negocio no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ==================== APIs para Gestión de Usuarios ====================

@login_required(login_url='/auth/login/')
def detalle_usuario_json(request, usuario_id):
    """API para obtener detalles completos de un usuario (para modal)"""
    try:
        # Verificar permisos de moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'error': 'No tienes permisos de moderador'}, status=403)
        
        perfil_usuario = UsuarioPerfil.objects.select_related(
            'fkuser', 'fktipodoc_user'
        ).prefetch_related('usuariosroles_set__fkrol').get(id=usuario_id)
        
        user = perfil_usuario.fkuser
        roles = perfil_usuario.usuariosroles_set.all()
        rol_principal = 'CLIENTE'
        if roles.exists():
            rol_principal = roles.first().fkrol.desc_rol
        
        # Obtener negocios si es vendedor
        negocios_data = []
        if rol_principal == 'VENDEDOR':
            negocios = Negocios.objects.filter(fkpropietario_neg=perfil_usuario.id)
            for negocio in negocios:
                negocios_data.append({
                    'id': negocio.pkid_neg,
                    'nombre': negocio.nom_neg,
                    'nit': negocio.nit_neg,
                    'estado': negocio.estado_neg,
                    'fecha_creacion': negocio.fechacreacion_neg.strftime("%d/%m/%Y")
                })
        
        datos_usuario = {
            'id': perfil_usuario.id,
            'user_id': user.id,
            'nombre': f"{user.first_name} {user.last_name}".strip() or user.username,
            'email': user.email,
            'documento': perfil_usuario.doc_user,
            'tipo_documento': perfil_usuario.fktipodoc_user.desc_doc,
            'fecha_nacimiento': perfil_usuario.fechanac_user.strftime("%d/%m/%Y") if perfil_usuario.fechanac_user else 'No especificada',
            'estado': perfil_usuario.estado_user,
            'rol': rol_principal,
            'img_user': request.build_absolute_uri(perfil_usuario.img_user.url) if perfil_usuario.img_user else '',
            'fecha_registro': user.date_joined.strftime("%d/%m/%Y %H:%M"),
            'ultimo_login': user.last_login.strftime("%d/%m/%Y %H:%M") if user.last_login else 'Nunca',
            'negocios': negocios_data
        }
        
        return JsonResponse(datos_usuario)
    except UsuarioPerfil.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='/auth/login/')
@csrf_exempt
@require_http_methods(["POST"])
def cambiar_estado_usuario(request, usuario_id):
    """API para cambiar el estado de un usuario"""
    try:
        # Verificar permisos de moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'error': 'No tienes permisos de moderador'}, status=403)
        
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        
        # Validar estado
        if nuevo_estado not in ['activo', 'inactivo', 'bloqueado']:
            return JsonResponse({'error': 'Estado inválido'}, status=400)
        
        perfil_usuario = UsuarioPerfil.objects.get(id=usuario_id)
        perfil_usuario.estado_user = nuevo_estado
        perfil_usuario.save()
        
        # También actualizar el estado en auth_user si es necesario
        user = perfil_usuario.fkuser
        user.is_active = 1 if nuevo_estado == 'activo' else 0
        user.save()
        
        return JsonResponse({
            'success': True, 
            'nuevo_estado': nuevo_estado,
            'mensaje': f'Estado del usuario cambiado a {nuevo_estado}'
        })
        
    except UsuarioPerfil.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# VISTA DE VERIFICACIÓN DE LOGIN (opcional)
@login_required(login_url='/auth/login/')
def verificar_moderador_login(request):
    """Vista para verificar el login del moderador - CORREGIDA"""
    try:
        # Verificar si es moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect('principal')
        
        # Si es moderador, redirigir al dashboard
        return redirect('moderador_dash')
        
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect('principal')

# ==================== FUNCIONES PARA CORREOS ====================

def obtener_destinatarios_por_ids(usuario_ids):
    """
    Obtiene correos de usuarios específicos por sus IDs
    """
    try:
        correos = []
        for usuario_id in usuario_ids:
            try:
                perfil = UsuarioPerfil.objects.get(id=usuario_id)
                email = perfil.fkuser.email
                if email and '@' in email:
                    correos.append(email)
            except UsuarioPerfil.DoesNotExist:
                print(f"Usuario con ID {usuario_id} no encontrado")
                continue
        
        return correos
        
    except Exception as e:
        print(f"Error obteniendo destinatarios por IDs: {str(e)}")
        return []

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

# ==================== VISTAS PARA CORREOS ====================

@login_required(login_url='/auth/login/')
def enviar_correos(request):
    """Vista para la página de envío de correos - CORREGIDA"""
    try:
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            messages.error(request, "Debes iniciar sesión.")
            return redirect('iniciar_sesion')
        
        # Obtener perfil del usuario - CORREGIDO
        try:
            # CORREGIDO: Usar UsuarioPerfil directamente
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        except UsuarioPerfil.DoesNotExist:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('iniciar_sesion')
        
        # Verificar si es moderador
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect('principal')
        
        # Obtener usuarios EXCLUYENDO MODERADORES
        perfiles_moderadores = UsuariosRoles.objects.filter(
            fkrol__desc_rol__iexact='moderador'
        ).values_list('fkperfil_id', flat=True)
        
        usuarios_perfiles = UsuarioPerfil.objects.select_related(
            'fkuser', 'fktipodoc_user'
        ).prefetch_related('usuariosroles_set__fkrol').exclude(
            id__in=perfiles_moderadores
        )
        
        usuarios_data = []
        for perfil_usuario in usuarios_perfiles:
            user = perfil_usuario.fkuser
            roles = perfil_usuario.usuariosroles_set.all()
            
            # Determinar el rol principal
            rol_principal = 'CLIENTE'
            if roles.exists():
                for rol in roles:
                    if rol.fkrol.desc_rol.lower() != 'moderador':
                        rol_principal = rol.fkrol.desc_rol
                        break
            
            # Construir nombre completo
            nombre_completo = f"{user.first_name} {user.last_name}".strip()
            if not nombre_completo:
                nombre_completo = user.username
            
            usuarios_data.append({
                'id': perfil_usuario.id,
                'nombre': nombre_completo,
                'email': user.email,
                'documento': perfil_usuario.doc_user,
                'tipo_documento': perfil_usuario.fktipodoc_user.desc_doc,
                'estado': perfil_usuario.estado_user,
                'rol': rol_principal,
                'fecha_registro': user.date_joined.strftime("%d/%m/%Y")
            })
        
        # Obtener estadísticas
        total_usuarios = len(usuarios_data)
        total_vendedores = len([u for u in usuarios_data if u['rol'] == 'VENDEDOR'])
        total_clientes = len([u for u in usuarios_data if u['rol'] == 'CLIENTE'])
        
        context = {
            'nombre': request.user.first_name or request.user.username,
            'perfil': perfil,
            'titulo_pagina': 'Enviar Correos',
            'total_usuarios': total_usuarios,
            'total_vendedores': total_vendedores,
            'total_clientes': total_clientes,
            'usuarios': usuarios_data,
        }
        
        return render(request, 'Moderador/correo.html', context)
    
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('principal')

@login_required(login_url='/auth/login/')
@csrf_exempt
@require_http_methods(["POST"])
def enviar_correo_masivo(request):
    """API para enviar correos masivos SOLO a usuarios seleccionados - CORREGIDA"""
    try:
        # Verificar permisos de moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'success': False, 'error': 'No tienes permisos de moderador'})

        # CORRECCIÓN: Usar request.POST y request.FILES en lugar de json.loads
        destinatarios_ids = request.POST.getlist('destinatarios[]')
        # Si no viene como lista, intentar parsear como JSON
        if not destinatarios_ids and 'destinatarios' in request.POST:
            try:
                destinatarios_data = request.POST.get('destinatarios')
                if destinatarios_data:
                    destinatarios_ids = json.loads(destinatarios_data)
            except:
                destinatarios_ids = []
        
        asunto = request.POST.get('asunto', '')
        mensaje_html = request.POST.get('mensaje', '')
        tipo_correo = request.POST.get('tipo_correo', 'simple')
        urgente = request.POST.get('urgente', 'false') == 'true'
        test_mode = request.POST.get('test_mode', 'false') == 'true'

        if not asunto or not mensaje_html:
            return JsonResponse({'success': False, 'error': 'Asunto y mensaje son requeridos'})
        
        # CORRECCIÓN: Obtener SOLO los correos de los usuarios seleccionados
        correos_destinatarios = []
        
        if test_mode:
            # En modo prueba, enviar solo al admin
            correos_destinatarios = [settings.EMAIL_HOST_USER]
        else:
            # Obtener los correos de los usuarios específicamente seleccionados
            if destinatarios_ids and destinatarios_ids != ['admin']:
                correos_destinatarios = obtener_destinatarios_por_ids(destinatarios_ids)
            
            # Si no hay destinatarios seleccionados, retornar error
            if not correos_destinatarios:
                return JsonResponse({
                    'success': False, 
                    'error': 'No se encontraron destinatarios válidos seleccionados'
                })
        
        try:
            # CORRECCIÓN: Enviar correo según el tipo con manejo de archivos
            if tipo_correo == 'promocional':
                resultado = enviar_correo_promocional_masivo(
                    destinatarios=correos_destinatarios,
                    asunto=asunto,
                    mensaje_html=mensaje_html,
                    archivos_adjuntos=request.FILES.getlist('archivos'),
                    es_test=test_mode
                )
            else:
                resultado = enviar_correo_simple_masivo(
                    destinatarios=correos_destinatarios,
                    asunto=asunto,
                    mensaje_html=mensaje_html,
                    archivos_adjuntos=request.FILES.getlist('archivos'),
                    urgente=urgente,
                    es_test=test_mode
                )
            
            # Agregar información adicional al resultado
            if resultado['success']:
                resultado['enviados'] = len(correos_destinatarios)
                resultado['destinatarios'] = correos_destinatarios
            
            return JsonResponse(resultado)
            
        except Exception as email_error:
            return JsonResponse({'success': False, 'error': f'Error al enviar correo: {str(email_error)}'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# NUEVAS FUNCIONES CORREGIDAS PARA MANEJAR ARCHIVOS ADJUNTOS
def enviar_correo_promocional_masivo(destinatarios, asunto, mensaje_html, archivos_adjuntos=None, es_test=True):
    """
    Función CORREGIDA para enviar correos promocionales con archivos adjuntos
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
        
        # CORRECCIÓN: Adjuntar archivos de manera segura
        if archivos_adjuntos:
            for archivo in archivos_adjuntos:
                try:
                    # Leer el archivo en modo binario
                    archivo.seek(0)  # Asegurarse de estar al inicio del archivo
                    contenido = archivo.read()
                    
                    # Adjuntar el archivo
                    email.attach(
                        filename=archivo.name,
                        content=contenido,
                        mimetype=archivo.content_type or 'application/octet-stream'
                    )
                except Exception as attach_error:
                    print(f"Error adjuntando archivo {archivo.name}: {str(attach_error)}")
                    continue
        
        email.send(fail_silently=False)
        
        return {
            'success': True,
            'enviados_a': destinatarios,
            'total': len(destinatarios),
            'archivos_adjuntos': len(archivos_adjuntos) if archivos_adjuntos else 0
        }
        
    except Exception as e:
        print(f"ERROR enviando correo promocional: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def enviar_correo_simple_masivo(destinatarios, asunto, mensaje_html, archivos_adjuntos=None, urgente=False, es_test=True):
    """
    Función CORREGIDA para enviar correos simples con archivos adjuntos
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
        
        # CORRECCIÓN: Adjuntar archivos de manera segura
        if archivos_adjuntos:
            for archivo in archivos_adjuntos:
                try:
                    # Leer el archivo en modo binario
                    archivo.seek(0)  # Asegurarse de estar al inicio del archivo
                    contenido = archivo.read()
                    
                    # Adjuntar el archivo
                    email.attach(
                        filename=archivo.name,
                        content=contenido,
                        mimetype=archivo.content_type or 'application/octet-stream'
                    )
                except Exception as attach_error:
                    print(f"Error adjuntando archivo {archivo.name}: {str(attach_error)}")
                    continue
        
        email.send(fail_silently=False)
        
        return {
            'success': True,
            'enviados_a': destinatarios,
            'total': len(destinatarios),
            'urgente': urgente,
            'archivos_adjuntos': len(archivos_adjuntos) if archivos_adjuntos else 0
        }
        
    except Exception as e:
        print(f"ERROR enviando correo simple: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

# API para obtener usuarios para correos
@login_required(login_url='/auth/login/')
def api_usuarios_correos(request):
    """API para obtener usuarios para el sistema de correos"""
    try:
        # Verificar permisos de moderador - CORREGIDO
        perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'error': 'No tienes permisos'}, status=403)
        
        # Obtener usuarios EXCLUYENDO MODERADORES
        perfiles_moderadores = UsuariosRoles.objects.filter(
            fkrol__desc_rol__iexact='moderador'
        ).values_list('fkperfil_id', flat=True)
        
        usuarios_perfiles = UsuarioPerfil.objects.select_related(
            'fkuser', 'fktipodoc_user'
        ).prefetch_related('usuariosroles_set__fkrol').exclude(
            id__in=perfiles_moderadores
        )
        
        usuarios_data = []
        for perfil_usuario in usuarios_perfiles:
            user = perfil_usuario.fkuser
            roles = perfil_usuario.usuariosroles_set.all()
            
            # Determinar el rol principal
            rol_principal = 'CLIENTE'
            if roles.exists():
                for rol in roles:
                    if rol.fkrol.desc_rol.lower() != 'moderador':
                        rol_principal = rol.fkrol.desc_rol
                        break
            
            # Construir nombre completo
            nombre_completo = f"{user.first_name} {user.last_name}".strip()
            if not nombre_completo:
                nombre_completo = user.username
            
            usuarios_data.append({
                'id': perfil_usuario.id,
                'nombre': nombre_completo,
                'email': user.email,
                'documento': perfil_usuario.doc_user,
                'tipo_documento': perfil_usuario.fktipodoc_user.desc_doc,
                'estado': perfil_usuario.estado_user,
                'rol': rol_principal,
                'fecha_registro': user.date_joined.strftime("%d/%m/%Y")
            })
        
        return JsonResponse({
            'usuarios': usuarios_data,
            'total': len(usuarios_data),
            'vendedores': len([u for u in usuarios_data if u['rol'] == 'VENDEDOR']),
            'clientes': len([u for u in usuarios_data if u['rol'] == 'CLIENTE'])
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
 
# VISTA PARA RESEÑAS REPORTADAS - COMPLETAMENTE CORREGIDA
# VISTA PARA RESEÑAS REPORTADAS - CON SQL PURO
@login_required(login_url='/auth/login/')
def gestion_resenas_reportadas(request):
    """Vista para gestión de reseñas reportadas usando SQL puro"""
    try:
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            messages.error(request, "Debes iniciar sesión.")
            return redirect('iniciar_sesion')
        
        # Obtener perfil del usuario
        try:
            perfil = UsuarioPerfil.objects.get(fkuser=request.user)
        except UsuarioPerfil.DoesNotExist:
            messages.error(request, "Perfil de usuario no encontrado.")
            return redirect('iniciar_sesion')
        
        # Verificar si es moderador
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol__iexact='moderador'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect('principal')
        
        # Procesar acciones por POST
        if request.method == 'POST':
            resena_id = request.POST.get('resena_id')
            accion = request.POST.get('accion')
            
            try:
                with connection.cursor() as cursor:
                    if accion == 'aprobar':
                        # Aprobar la reseña (mantenerla activa)
                        cursor.execute(
                            "UPDATE resenas_negocios SET estado_resena = 'activa' WHERE pkid_resena = %s",
                            [resena_id]
                        )
                        
                        # Actualizar reportes relacionados
                        cursor.execute(
                            "UPDATE reportes SET estado_reporte = 'revisado' WHERE fkresena_reporte = %s AND estado_reporte = 'pendiente'",
                            [resena_id]
                        )
                        
                        messages.success(request, 'Reseña aprobada correctamente')
                    
                    elif accion == 'eliminar':
                        # Eliminar la reseña (cambiar estado a eliminada)
                        cursor.execute(
                            "UPDATE resenas_negocios SET estado_resena = 'eliminada' WHERE pkid_resena = %s",
                            [resena_id]
                        )
                        
                        # Actualizar reportes relacionados
                        cursor.execute(
                            "UPDATE reportes SET estado_reporte = 'resuelto' WHERE fkresena_reporte = %s AND estado_reporte = 'pendiente'",
                            [resena_id]
                        )
                        
                        messages.success(request, 'Reseña eliminada correctamente')
                    
                    else:
                        messages.error(request, 'Acción no válida')
                        
            except Exception as e:
                messages.error(request, f'Error al procesar la solicitud: {str(e)}')
            
            return redirect('gestion_resenas_reportadas')
        
        # Obtener parámetros de filtrado
        estado_filter = request.GET.get('estado', '')
        gravedad_filter = request.GET.get('gravedad', '')
        fecha_filter = request.GET.get('fecha', '')
        
        # CONSULTA SQL PRINCIPAL: Obtener reseñas que tienen reportes pendientes
        sql = """
        SELECT 
            rn.pkid_resena as id,
            rn.comentario,
            rn.estrellas,
            rn.fecha_resena,
            rn.estado_resena as estado_db,
            n.pkid_neg as negocio_id,
            n.nom_neg as negocio_nombre,
            tn.desc_tiponeg as negocio_categoria,
            n.direcc_neg as negocio_direccion,
            up.id as usuario_id,
            CONCAT(au.first_name, ' ', au.last_name) as usuario_nombre,
            au.email as usuario_email,
            au.username as usuario_username,
            up.img_user as usuario_imagen,
            COUNT(rep.pkid_reporte) as total_reportes,
            MAX(rep.fecha_reporte) as ultimo_reporte
        FROM reportes rep
        INNER JOIN resenas_negocios rn ON rep.fkresena_reporte = rn.pkid_resena
        INNER JOIN negocios n ON rn.fknegocio_resena = n.pkid_neg
        INNER JOIN tipo_negocio tn ON n.fktiponeg_neg = tn.pkid_tiponeg
        INNER JOIN usuario_perfil up ON rn.fkusuario_resena = up.id
        INNER JOIN auth_user au ON up.fkuser_id = au.id
        WHERE rep.estado_reporte = 'pendiente'
        AND rep.fkresena_reporte IS NOT NULL
        """
        
        params = []
        
        # Aplicar filtros
        if estado_filter:
            sql += " AND rep.estado_reporte = %s"
            params.append(estado_filter)
        
        if fecha_filter:
            sql += " AND DATE(rep.fecha_reporte) = %s"
            params.append(fecha_filter)
        
        sql += " GROUP BY rn.pkid_resena, n.pkid_neg, up.id, au.id ORDER BY ultimo_reporte DESC"
        
        # Ejecutar consulta principal
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            reseñas_base = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Para cada reseña, obtener los detalles de los reportes
        reseñas_data = []
        for reseña in reseñas_base:
            # Obtener motivos y usuarios que reportaron para esta reseña
            sql_reportes = """
            SELECT 
                rep.motivo,
                rep.descripcion,
                rep.fecha_reporte,
                CONCAT(au2.first_name, ' ', au2.last_name) as reportero_nombre,
                au2.email as reportero_email
            FROM reportes rep
            INNER JOIN usuario_perfil up2 ON rep.fkusuario_reporta = up2.id
            INNER JOIN auth_user au2 ON up2.fkuser_id = au2.id
            WHERE rep.fkresena_reporte = %s 
            AND rep.estado_reporte = 'pendiente'
            ORDER BY rep.fecha_reporte DESC
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql_reportes, [reseña['id']])
                columns_reportes = [col[0] for col in cursor.description]
                reportes_detalle = [dict(zip(columns_reportes, row)) for row in cursor.fetchall()]
            
            # Obtener motivos únicos
            motivos_reportes = list(set([reporte['motivo'] for reporte in reportes_detalle]))
            
            # Preparar información de usuarios que reportaron
            usuarios_reportan_info = []
            for reporte in reportes_detalle:
                usuarios_reportan_info.append({
                    'nombre': reporte['reportero_nombre'] or reporte['reportero_email'],
                    'email': reporte['reportero_email'],
                    'motivo': reporte['motivo'],
                    'descripcion': reporte['descripcion'] or 'Sin descripción adicional',
                    'fecha': reporte['fecha_reporte']
                })
            
            # Determinar gravedad basada en número de reportes
            total_reportes = reseña['total_reportes']
            if total_reportes >= 3:
                gravedad = 'alta'
            elif total_reportes == 2:
                gravedad = 'media'
            else:
                gravedad = 'baja'
            
            # Aplicar filtro de gravedad
            if gravedad_filter and gravedad != gravedad_filter:
                continue
            
            # Manejar imagen del usuario
            imagen_usuario = ''
            if reseña['usuario_imagen']:
                try:
                    imagen_usuario = reseña['usuario_imagen']
                except:
                    imagen_usuario = '/static/img/default-avatar.png'
            else:
                imagen_usuario = '/static/img/default-avatar.png'
            
            reseñas_data.append({
                'id': reseña['id'],
                'comentario': reseña['comentario'] or 'Sin comentario',
                'estrellas': reseña['estrellas'],
                'fecha_resena': reseña['fecha_resena'],
                'estado': 'Activa' if reseña['estado_db'] == 'activa' else 'Eliminada',
                'estado_db': reseña['estado_db'],
                'gravedad': gravedad,
                
                # Información del negocio
                'negocio_id': reseña['negocio_id'],
                'negocio_nombre': reseña['negocio_nombre'],
                'negocio_categoria': reseña['negocio_categoria'],
                'negocio_direccion': reseña['negocio_direccion'],
                
                # Información del usuario que hizo la reseña
                'usuario_id': reseña['usuario_id'],
                'usuario_nombre': reseña['usuario_nombre'] or reseña['usuario_username'],
                'usuario_email': reseña['usuario_email'],
                'usuario_imagen': imagen_usuario,
                'usuario_username': reseña['usuario_username'],
                
                # Información de reportes
                'total_reportes': total_reportes,
                'motivos_reportes': motivos_reportes,
                'usuarios_reportan': usuarios_reportan_info,
                'ultimo_reporte': reseña['ultimo_reporte'],
            })
        
        # Calcular estadísticas para las tarjetas
        with connection.cursor() as cursor:
            # Total de reportes pendientes de reseñas
            cursor.execute("""
                SELECT COUNT(*) FROM reportes 
                WHERE estado_reporte = 'pendiente' 
                AND fkresena_reporte IS NOT NULL
            """)
            total_reportes_count = cursor.fetchone()[0]
            
            # Reportes pendientes
            cursor.execute("""
                SELECT COUNT(*) FROM reportes 
                WHERE estado_reporte = 'pendiente' 
                AND fkresena_reporte IS NOT NULL
            """)
            pendientes_count = cursor.fetchone()[0]
            
            # Reportes resueltos de reseñas
            cursor.execute("""
                SELECT COUNT(*) FROM reportes 
                WHERE estado_reporte = 'resuelto' 
                AND fkresena_reporte IS NOT NULL
            """)
            resueltos_count = cursor.fetchone()[0]
        
        # Para alta prioridad, contamos reseñas con múltiples reportes
        alta_prioridad_count = 0
        for resena_data in reseñas_data:
            if resena_data['total_reportes'] >= 3:
                alta_prioridad_count += 1
        
        # Paginación
        from django.core.paginator import Paginator
        paginator = Paginator(reseñas_data, 10)  # 10 items por página
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'nombre': request.user.first_name or request.user.username,
            'perfil': perfil,
            'reseñas_reportadas': page_obj,
            'titulo_pagina': 'Reseñas Reportadas',
            
            # Filtros actuales para mantener en la interfaz
            'estado_filter': estado_filter,
            'gravedad_filter': gravedad_filter,
            'fecha_filter': fecha_filter,
            
            # Estadísticas para las tarjetas
            'total_reportes': total_reportes_count,
            'pendientes': pendientes_count,
            'resueltos': resueltos_count,
            'alta_prioridad': alta_prioridad_count
        }
        
        return render(request, 'Moderador/reporte_resenas.html', context)
    
    except Exception as e:
        print(f"ERROR en vista reseñas reportadas: {str(e)}")
        messages.error(request, f"Error al cargar las reseñas reportadas: {str(e)}")
        return redirect('principal')