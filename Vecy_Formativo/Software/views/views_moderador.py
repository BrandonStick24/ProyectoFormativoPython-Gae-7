from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from Software.models import Negocios, UsuarioPerfil, Pedidos, DetallesPedido, ResenasNegocios, AuthUser, Roles, TipoDocumento, UsuariosRoles, TipoNegocio, Productos, CategoriaProductos, Reportes
from django.utils import timezone
from django.db.models import Count, Avg
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from collections import Counter
from django.contrib.auth.models import User
from django.db.models.functions import ExtractMonth, ExtractYear
from Software.email_utils import enviar_notificacion_simple
from django.urls import reverse

def obtener_datos_moderador(request):
    """Función auxiliar para obtener datos del moderador"""
    try:
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        
        return {
            'nombre_usuario': auth_user.first_name,
            'perfil': perfil,
            'auth_user': auth_user,
        }
    except (AuthUser.DoesNotExist, UsuarioPerfil.DoesNotExist):
        return None

def is_moderator(user):
    """Verifica si el usuario es moderador"""
    if not user.is_authenticated:
        return False
        
    try:
        # Obtener el perfil del usuario
        perfil = UsuarioPerfil.objects.get(fkuser=user)
        
        # Verificar si tiene rol de moderador
        return UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol='MODERADOR'
        ).exists()
    except (UsuarioPerfil.DoesNotExist, AuthUser.DoesNotExist):
        return False

# VISTA PRINCIPAL DEL MODERADOR - AHORA CON ESTADÍSTICAS COMPLETAS
@login_required(login_url='/auth/login/')
def moderador_dash(request):
    """Vista principal del dashboard del moderador con estadísticas completas"""
    try:
        # Verificar si es moderador
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
        
        # Verificar si es moderador
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol='MODERADOR'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect(reverse('login'))
        
        # ============ CÓDIGO DE ESTADÍSTICAS COMPLETAS ============
        # Obtener el rango de tiempo (último año)
        fecha_limite = timezone.now() - timedelta(days=365)
        
        # 1. REGISTRO DE USUARIOS POR MES
        usuarios_por_mes = User.objects.filter(
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
        
        # MÉTRICAS PRINCIPALES
        total_usuarios = User.objects.count()
        usuarios_activos = User.objects.filter(is_active=True).count()
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
            'nombre': request.user.first_name,
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
        
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect(reverse('login'))
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect(reverse('login'))

# GESTIÓN DE USUARIOS
@login_required(login_url='/auth/login/')
def gestion_usuarios(request):
    """Vista para gestión de usuarios por parte del moderador"""
    try:
        # Misma verificación que en estadísticas
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
        
        # Verificar si es moderador
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol='MODERADOR'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect(reverse('login'))
        
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
                    fkrol__desc_rol='MODERADOR'
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
                    user.is_active = (nuevo_estado == 'activo')
                    user.save()
                    
                    # ENVIAR CORREO DE NOTIFICACIÓN - VERSIÓN SIMPLE
                    from Software.email_utils import enviar_notificacion_simple
                    
                    # Notificar al usuario
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
                    
                    # Enviar notificación antes de eliminar usando la versión simple
                    from Software.email_utils import enviar_notificacion_simple
                    
                    # Notificar eliminación
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
            fkrol__desc_rol='MODERADOR'
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
                Q(fkuser__email__icontains=search_query)
            )
        
        if rol_filter:
            usuarios_perfiles = usuarios_perfiles.filter(
                usuariosroles_set__fkrol__desc_rol=rol_filter
            ).distinct()
        
        if estado_filter:
            usuarios_perfiles = usuarios_perfiles.filter(estado_user=estado_filter)
        
        usuarios_data = []
        for perfil_usuario in usuarios_perfiles:
            user = perfil_usuario.fkuser
            roles = perfil_usuario.usuariosroles_set.all()
            
            # Determinar el rol principal
            rol_principal = 'CLIENTE'  # Por defecto
            if roles.exists():
                # Buscar el primer rol que no sea MODERADOR
                for rol in roles:
                    if rol.fkrol.desc_rol != 'MODERADOR':
                        rol_principal = rol.fkrol.desc_rol
                        break
            
            # Obtener negocios si es vendedor
            negocios = []
            if rol_principal == 'VENDEDOR':
                negocios_vendedor = Negocios.objects.filter(
                    fkpropietario_neg=perfil_usuario.id
                ).values('pkid_neg', 'nom_neg')
                negocios = list(negocios_vendedor)
            
            # Construir nombre completo
            nombre_completo = f"{user.first_name} {user.last_name}".strip()
            if not nombre_completo:
                nombre_completo = user.username
            
            usuarios_data.append({
                'id': perfil_usuario.id,
                'user_id': user.id,
                'nombre': nombre_completo,
                'email': user.email,
                'documento': perfil_usuario.doc_user,
                'tipo_documento': perfil_usuario.fktipodoc_user.desc_doc,
                'fecha_nacimiento': perfil_usuario.fechanac_user,
                'estado': perfil_usuario.estado_user,
                'rol': rol_principal,
                'img_user': perfil_usuario.img_user,
                'fecha_registro': user.date_joined,
                'negocios': negocios
            })
        
        # Aplicar filtros adicionales en memoria para búsqueda más precisa
        if search_query:
            search_lower = search_query.lower()
            usuarios_data = [
                u for u in usuarios_data 
                if (search_lower in u['nombre'].lower() or 
                    search_lower in u['email'].lower() or
                    search_lower in u['documento'].lower())
            ]
        
        # Estadísticas para los gráficos (basadas en los datos filtrados)
        total_usuarios = len(usuarios_data)
        usuarios_activos = len([u for u in usuarios_data if u['estado'] == 'activo'])
        total_clientes = len([u for u in usuarios_data if u['rol'] == 'CLIENTE'])
        total_vendedores = len([u for u in usuarios_data if u['rol'] == 'VENDEDOR'])
        
        context = {
            'nombre': request.user.first_name,
            'perfil': perfil,
            'usuarios': usuarios_data,
            'total_usuarios': total_usuarios,
            'usuarios_activos': usuarios_activos,
            'total_clientes': total_clientes,
            'total_vendedores': total_vendedores,
            'titulo_pagina': 'Gestión de Usuarios',
            'search_query': search_query,
            'rol_filter': rol_filter,
            'estado_filter': estado_filter
        }
        
        return render(request, 'Moderador/gestion_usuarios.html', context)
    
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect(reverse('login'))
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect(reverse('login'))

# GESTIÓN DE NEGOCIOS
@login_required(login_url='/auth/login/')
def gestion_negocios(request):
    """Vista principal de gestión de negocios para moderadores"""    
    try:
        # Misma verificación que en estadísticas
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
        
        # Verificar si es moderador
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol='MODERADOR'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect(reverse('login'))
        
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
            'nombre': request.user.first_name,
            'perfil': perfil,
            'negocios': negocios_data,
            'titulo_pagina': 'Gestión de Negocios',
            'search_query': search_query,
            'status_filter': status_filter
        }
        
        return render(request, 'Moderador/gestion_negocios.html', context)
    
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect(reverse('login'))
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect(reverse('login'))

# ==================== APIs para Gestión de Negocios ====================

@login_required(login_url='/auth/login/')
def detalle_negocio_json(request, negocio_id):
    """API para obtener detalles completos de un negocio (para modal)"""
    try:
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
        perfil = UsuarioPerfil.objects.select_related(
            'fkuser', 'fktipodoc_user'
        ).prefetch_related('usuariosroles_set__fkrol').get(id=usuario_id)
        
        user = perfil.fkuser
        roles = perfil.usuariosroles_set.all()
        rol_principal = 'CLIENTE'
        if roles.exists():
            rol_principal = roles.first().fkrol.desc_rol
        
        # Obtener negocios si es vendedor
        negocios_data = []
        if rol_principal == 'VENDEDOR':
            negocios = Negocios.objects.filter(fkpropietario_neg=perfil.id)
            for negocio in negocios:
                negocios_data.append({
                    'id': negocio.pkid_neg,
                    'nombre': negocio.nom_neg,
                    'nit': negocio.nit_neg,
                    'estado': negocio.estado_neg,
                    'fecha_creacion': negocio.fechacreacion_neg.strftime("%d/%m/%Y")
                })
        
        datos_usuario = {
            'id': perfil.id,
            'user_id': user.id,
            'nombre': f"{user.first_name} {user.last_name}".strip() or user.username,
            'email': user.email,
            'documento': perfil.doc_user,
            'tipo_documento': perfil.fktipodoc_user.desc_doc,
            'fecha_nacimiento': perfil.fechanac_user.strftime("%d/%m/%Y") if perfil.fechanac_user else 'No especificada',
            'estado': perfil.estado_user,
            'rol': rol_principal,
            'img_user': request.build_absolute_uri(perfil.img_user.url) if perfil.img_user else '',
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
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        
        # Validar estado
        if nuevo_estado not in ['activo', 'inactivo', 'bloqueado']:
            return JsonResponse({'error': 'Estado inválido'}, status=400)
        
        perfil = UsuarioPerfil.objects.get(id=usuario_id)
        perfil.estado_user = nuevo_estado
        perfil.save()
        
        # También actualizar el estado en auth_user si es necesario
        user = perfil.fkuser
        user.is_active = (nuevo_estado == 'activo')
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
    negocios = Negocios.objects.all()
    t_negocios = TipoNegocio.objects.all()
    try:
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect('inicio')
    
    contexto = {
        'nombre' : request.user.first_name,
        'perfil' : perfil,
        'negocios': negocios,
        't_negocios': t_negocios
    }
    return render(request, 'Cliente/Cliente.html', contexto)

# ==================== VISTAS PARA CORREOS ====================

@login_required(login_url='/auth/login/')
def enviar_correos(request):
    """Vista para la página de envío de correos"""
    try:
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
        
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol='MODERADOR'
        ).exists()
        
        if not es_moderador:
            messages.error(request, "No tienes permisos de moderador.")
            return redirect(reverse('login'))
        
        # Obtener usuarios EXCLUYENDO MODERADORES
        perfiles_moderadores = UsuariosRoles.objects.filter(
            fkrol__desc_rol='MODERADOR'
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
                    if rol.fkrol.desc_rol != 'MODERADOR':
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
            'nombre': request.user.first_name,
            'perfil': perfil,
            'titulo_pagina': 'Enviar Correos',
            'total_usuarios': total_usuarios,
            'total_vendedores': total_vendedores,
            'total_clientes': total_clientes,
            'usuarios': usuarios_data,  # Pasar los usuarios al template
        }
        
        return render(request, 'Moderador/correo.html', context)
    
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect(reverse('login'))
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect(reverse('login'))
    
@login_required(login_url='/auth/login/')
@csrf_exempt
@require_http_methods(["POST"])
def enviar_correo_masivo(request):
    """API para enviar correos masivos"""
    try:
        # Verificar permisos de moderador
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol='MODERADOR'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'success': False, 'error': 'No tienes permisos de moderador'})
        
        # Obtener datos del formulario
        data = json.loads(request.body)
        
        destinatarios_ids = data.get('destinatarios', [])
        asunto = data.get('asunto', '')
        mensaje_html = data.get('mensaje', '')
        tipo_correo = data.get('tipo_correo', 'promocional')
        urgente = data.get('urgente', False)
        
        if not asunto or not mensaje_html:
            return JsonResponse({'success': False, 'error': 'Asunto y mensaje son requeridos'})
        
        # Obtener correos de destinatarios usando la nueva función
        from Software.email_utils import obtener_destinatarios_usuarios, enviar_correo_promocional, enviar_correo_simple
        
        todos_correos = obtener_destinatarios_usuarios()
        
        if not todos_correos:
            return JsonResponse({'success': False, 'error': 'No se encontraron destinatarios válidos'})
        
        # Enviar correo según el tipo
        if tipo_correo == 'promocional':
            resultado = enviar_correo_promocional(
                destinatarios=todos_correos,
                asunto=asunto,
                mensaje_html=mensaje_html,
                es_test=False  # Cambiar a False cuando estés en producción
            )
        else:
            resultado = enviar_correo_simple(
                destinatarios=todos_correos,
                asunto=asunto,
                mensaje_html=mensaje_html,
                urgente=urgente,
                es_test=False  # Cambiar a False cuando estés en producción
            )
        
        return JsonResponse(resultado)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# En views.py - agregar esta vista
@login_required(login_url='/auth/login/')
def api_usuarios_correos(request):
    """API para obtener usuarios para el sistema de correos"""
    try:
        # Verificar permisos de moderador
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
        es_moderador = UsuariosRoles.objects.filter(
            fkperfil=perfil, 
            fkrol__desc_rol='MODERADOR'
        ).exists()
        
        if not es_moderador:
            return JsonResponse({'error': 'No tienes permisos'}, status=403)
        
        # Obtener usuarios EXCLUYENDO MODERADORES
        perfiles_moderadores = UsuariosRoles.objects.filter(
            fkrol__desc_rol='MODERADOR'
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
                    if rol.fkrol.desc_rol != 'MODERADOR':
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

