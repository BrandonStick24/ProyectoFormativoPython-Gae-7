from ..models import *
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import connection, models
from django.db.models import Avg, Count, Sum, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
import json
from datetime import timedelta
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.contrib.auth import logout
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import os
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from django.db import connection
from django.shortcuts import render
from ..models import (
    Negocios, CategoriaProductos, TipoNegocio, Productos, 
    VariantesProducto, ResenasNegocios
)
from ..services.gemini_service import asistente_gemini

# =============================================================================
# VISTAS PARA ACTUALIZACIÓN EN TIEMPO REAL DE CONTADORES
# =============================================================================

@login_required
def get_header_counts(request):
    """Obtener contadores actualizados para el header"""
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # Contador del carrito
        carrito_count = CarritoItem.objects.filter(
            fkcarrito__fkusuario_carrito=perfil_cliente
        ).count()
        
        # Contador de favoritos
        favoritos_count = Favoritos.objects.filter(
            fkusuario=perfil_cliente
        ).count()
        
        # Contador de notificaciones no leídas
        notificaciones_count = Notificacion.objects.filter(
            usuario=request.user,
            leida=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'carrito_count': carrito_count,
            'favoritos_count': favoritos_count,
            'notificaciones_count': notificaciones_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'carrito_count': 0,
            'favoritos_count': 0,
            'notificaciones_count': 0
        })

def chat_asistente(request):
    """Vista para el chat fluido con Gemini"""
    return render(request, 'cliente/chat_asistente.html')

@csrf_exempt
def api_sugerencia(request):
    """API para respuestas interactivas con datos reales"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            mensaje = data.get('mensaje', '').strip()
            user_id = request.user.id if request.user.is_authenticated else None
            
            if not mensaje:
                return JsonResponse({'success': False, 'error': 'Mensaje vacío'})
            
            # Obtener respuesta INTERACTIVA con datos REALES
            respuesta = asistente_gemini.obtener_respuesta_interactiva(mensaje, user_id)
            
            return JsonResponse({
                'success': True,
                'respuesta': respuesta,
                'usuario_logueado': bool(user_id)
            })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

def principal(request):
    negocios = Negocios.objects.filter(estado_neg='activo')
    categorias = CategoriaProductos.objects.all()[:20]
    tipo_negocios = TipoNegocio.objects.all()
    
    todos_productos = Productos.objects.filter(estado_prod='disponible')
    hoy = timezone.now().date()
    
    def procesar_productos_con_variantes(productos_queryset):
        productos_procesados = []
        for producto in productos_queryset:
            variantes = VariantesProducto.objects.filter(
                producto_id=producto.pkid_prod, 
                estado_variante='activa'
            )
            productos_procesados.append({
                'producto': producto,
                'variantes': list(variantes),
                'tiene_variantes': variantes.exists()
            })
        return productos_procesados
    
    productos_oferta_flash = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.pkid_promo, p.fkproducto_id, p.variante_id, p.porcentaje_descuento,
                       p.fecha_inicio, p.fecha_fin, pr.precio_prod, pr.fknegocioasociado_prod_id
                FROM promociones p
                JOIN productos pr ON p.fkproducto_id = pr.pkid_prod
                WHERE p.estado_promo = 'activa'
                AND p.fecha_inicio <= %s
                AND p.fecha_fin >= %s
                AND DATE(p.fecha_fin) = DATE(%s + INTERVAL 1 DAY)
                AND pr.estado_prod = 'disponible'
            """, [hoy, hoy, hoy])
            
            ofertas_flash_data = cursor.fetchall()
            
            for row in ofertas_flash_data:
                try:
                    producto = Productos.objects.get(pkid_prod=row[1])
                    precio_base = float(row[6])
                    descuento_porcentaje = float(row[3]) if row[3] else 0
                    
                    if descuento_porcentaje > 0:
                        descuento_monto = (precio_base * descuento_porcentaje) / 100
                        precio_final = precio_base - descuento_monto
                        
                        fecha_fin = row[5]
                        if isinstance(fecha_fin, str):
                            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                        
                        horas_restantes = 24
                        
                        producto_data = {
                            'producto': producto,
                            'precio_original': precio_base,
                            'precio_final': round(precio_final, 2),
                            'descuento_porcentaje': descuento_porcentaje,
                            'descuento_monto': round(descuento_monto, 2),
                            'tiene_descuento': True,
                            'horas_restantes': horas_restantes,
                            'es_flash': True
                        }
                        productos_oferta_flash.append(producto_data)
                except Exception:
                    continue
                    
    except Exception:
        productos_oferta_flash = []
    
    productos_oferta_temporada = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.pkid_promo, p.titulo_promo, p.descripcion_promo, 
                       p.porcentaje_descuento, p.fecha_inicio, p.fecha_fin,
                       p.estado_promo, p.imagen_promo,
                       p.fknegocio_id, p.fkproducto_id, p.variante_id
                FROM promociones p
                WHERE p.estado_promo = 'activa'
                AND p.fecha_inicio <= %s
                AND p.fecha_fin >= %s
                AND (p.titulo_promo LIKE %s OR p.titulo_promo LIKE %s 
                     OR p.descripcion_promo LIKE %s OR p.descripcion_promo LIKE %s)
            """, [hoy, hoy, '%temporada%', '%estacional%', '%temporada%', '%estacional%'])
            
            promociones_temporada = cursor.fetchall()
            
            for row in promociones_temporada:
                try:
                    producto_id = row[9]
                    if producto_id:
                        producto = Productos.objects.get(pkid_prod=producto_id)
                        precio_base = float(producto.precio_prod)
                        descuento_porcentaje = float(row[3]) if row[3] else 0
                        
                        if descuento_porcentaje > 0:
                            descuento_monto = (precio_base * descuento_porcentaje) / 100
                            precio_final = precio_base - descuento_monto
                            
                            producto_data = {
                                'producto': producto,
                                'precio_original': precio_base,
                                'precio_final': round(precio_final, 2),
                                'descuento_porcentaje': descuento_porcentaje,
                                'descuento_monto': round(descuento_monto, 2),
                                'tiene_descuento': True,
                                'promocion': {
                                    'titulo': row[1],
                                    'descripcion': row[2],
                                    'imagen': row[7]
                                },
                                'es_temporada': True
                            }
                            productos_oferta_temporada.append(producto_data)
                except Productos.DoesNotExist:
                    continue
                    
    except Exception:
        productos_oferta_temporada = []
    
    productos_temporada_data = []
    try:
        categorias_temporada = CategoriaProductos.objects.filter(
            Q(desc_cp__icontains='navidad') | 
            Q(desc_cp__icontains='halloween') |
            Q(desc_cp__icontains='verano') |
            Q(desc_cp__icontains='invierno') |
            Q(desc_cp__icontains='primavera') |
            Q(desc_cp__icontains='otoño') |
            Q(desc_cp__icontains='festivo')
        )
        
        productos_temporada = Productos.objects.filter(
            estado_prod='disponible',
            fkcategoria_prod__in=categorias_temporada
        ).annotate(
            avg_calificacion=Avg('fknegocioasociado_prod__resenasnegocios__estrellas')
        ).order_by('-avg_calificacion', '?')[:8]
        
        productos_temporada_data = procesar_productos_con_variantes(productos_temporada)
        
    except Exception:
        productos_temporada_data = []
    
    productos_oferta_general = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.pkid_promo, p.fkproducto_id, p.porcentaje_descuento, pr.precio_prod
                FROM promociones p
                JOIN productos pr ON p.fkproducto_id = pr.pkid_prod
                WHERE p.estado_promo = 'activa'
                AND p.fecha_inicio <= %s
                AND p.fecha_fin >= %s
                AND pr.estado_prod = 'disponible'
            """, [hoy, hoy])
            
            ofertas_general = cursor.fetchall()
            
            for row in ofertas_general:
                try:
                    producto = Productos.objects.get(pkid_prod=row[1])
                    precio_base = float(row[3])
                    descuento_porcentaje = float(row[2]) if row[2] else 0
                    
                    if descuento_porcentaje > 0:
                        descuento_monto = (precio_base * descuento_porcentaje) / 100
                        precio_final = precio_base - descuento_monto
                        
                        producto_data = {
                            'producto': producto,
                            'precio_original': precio_base,
                            'precio_final': round(precio_final, 2),
                            'descuento_porcentaje': descuento_porcentaje,
                            'descuento_monto': round(descuento_monto, 2),
                            'tiene_descuento': True
                        }
                        if not any(p['producto'].pkid_prod == producto.pkid_prod for p in productos_oferta_flash):
                            productos_oferta_general.append(producto_data)
                except Exception:
                    continue
                    
    except Exception:
        productos_oferta_general = []
    
    productos_oferta_carrusel = productos_oferta_flash + productos_oferta_temporada + productos_oferta_general
    
    negocios_con_calificaciones = []
    for negocio in negocios:
        resenas_negocio = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            estado_resena='activa'
        )
        
        promedio_calificacion = resenas_negocio.aggregate(
            promedio=Avg('estrellas'),
            total_resenas=Count('pkid_resena')
        )
        
        negocio.promedio_calificacion = promedio_calificacion['promedio'] or 0
        negocio.total_resenas = promedio_calificacion['total_resenas'] or 0
        negocios_con_calificaciones.append(negocio)
    
    negocios_mejor_calificados = sorted(
        [n for n in negocios_con_calificaciones if n.promedio_calificacion > 0],
        key=lambda x: x.promedio_calificacion,
        reverse=True
    )[:8]
    
    productos_mas_vendidos_data = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM detalles_pedido")
            count_detalles = cursor.fetchone()[0]
            
            if count_detalles > 0:
                productos_mas_vendidos = Productos.objects.filter(
                    detallespedido__isnull=False,
                    estado_prod='disponible'
                ).annotate(
                    total_vendido=Sum('detallespedido__cantidad_detalle')
                ).filter(
                    total_vendido__gt=0
                ).order_by('-total_vendido')[:8]
            else:
                productos_mas_vendidos = Productos.objects.filter(
                    estado_prod='disponible'
                ).annotate(
                    avg_calificacion=Avg('fknegocioasociado_prod__resenasnegocios__estrellas')
                ).filter(
                    avg_calificacion__isnull=False
                ).order_by('-avg_calificacion')[:8]
    except Exception:
        productos_mas_vendidos = todos_productos.order_by('?')[:8]
    
    productos_mas_vendidos_data = procesar_productos_con_variantes(productos_mas_vendidos)
    
    productos_destacados = Productos.objects.filter(
        estado_prod='disponible',
        stock_prod__gt=5
    ).annotate(
        avg_calificacion=Avg('fknegocioasociado_prod__resenasnegocios__estrellas')
    ).filter(
        Q(avg_calificacion__gte=4.0) | Q(avg_calificacion__isnull=True)
    ).order_by('-avg_calificacion', '?')[:8]
    
    productos_destacados_data = procesar_productos_con_variantes(productos_destacados)
    
    PRECIO_MAX_ACCESIBLE = 150000
    productos_baratos = todos_productos.filter(
        precio_prod__lte=PRECIO_MAX_ACCESIBLE,
        estado_prod='disponible'
    ).annotate(
        avg_calificacion=Avg('fknegocioasociado_prod__resenasnegocios__estrellas')
    ).order_by('precio_prod', '-avg_calificacion')[:8]
    
    productos_baratos_data = procesar_productos_con_variantes(productos_baratos)
    
    nuevos_productos = todos_productos.order_by('-fecha_creacion')[:12]
    nuevos_productos_data = procesar_productos_con_variantes(nuevos_productos)
    
    categorias_populares = CategoriaProductos.objects.annotate(
        num_productos=Count('productos', filter=Q(productos__estado_prod='disponible'))
    ).filter(
        num_productos__gt=0
    ).order_by('-num_productos')[:8]
    
    if categorias_populares.count() < 8:
        categorias_adicionales = CategoriaProductos.objects.exclude(
            pkid_cp__in=[c.pkid_cp for c in categorias_populares]
        ).annotate(
            num_productos=Count('productos')
        ).order_by('-fecha_creacion')[:8 - categorias_populares.count()]
        categorias_populares = list(categorias_populares) + list(categorias_adicionales)
    
    contexto = {
        'negocios': negocios_con_calificaciones[:12],
        'categorias': categorias,
        'tipo_negocios': tipo_negocios,
        'productos_destacados': productos_destacados_data,
        'nuevos_productos': nuevos_productos_data,
        'productos_baratos': productos_baratos_data,
        'negocios_mejor_calificados': negocios_mejor_calificados,
        'productos_oferta': productos_oferta_carrusel,
        'productos_oferta_flash': productos_oferta_flash[:8],
        'productos_oferta_temporada': productos_oferta_temporada[:8],
        'productos_temporada': productos_temporada_data,
        'categorias_populares': categorias_populares,
        'productos_mas_vendidos': productos_mas_vendidos_data,
        'productos_con_variantes': procesar_productos_con_variantes(todos_productos),
        'hay_promociones': len(productos_oferta_carrusel) > 0,
        'hay_ofertas_flash': len(productos_oferta_flash) > 0,
        'hay_ofertas_temporada': len(productos_oferta_temporada) > 0,
        'precio_max_accesible': PRECIO_MAX_ACCESIBLE,
    }
    
    return render(request, 'cliente/principal.html', contexto)

def productos_todos(request):
    productos = Productos.objects.select_related(
        'fknegocioasociado_prod', 
        'fkcategoria_prod'
    ).prefetch_related('variantesproducto_set').filter(
        estado_prod='disponible'
    ).order_by('-fecha_creacion')
    
    categorias = CategoriaProductos.objects.annotate(
        num_productos=Count('productos')
    ).order_by('desc_cp')
    
    negocios = Negocios.objects.filter(estado_neg='activo').annotate(
        num_productos=Count('productos')
    ).order_by('nom_neg')
    
    categoria_filtro = request.GET.get('categoria', '')
    negocio_filtro = request.GET.get('negocio', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    ordenar_por = request.GET.get('ordenar_por', 'recientes')
    buscar = request.GET.get('buscar', '')
    
    if categoria_filtro and categoria_filtro != 'None':
        try:
            productos = productos.filter(fkcategoria_prod__pkid_cp=int(categoria_filtro))
        except (ValueError, TypeError):
            pass
    
    if negocio_filtro and negocio_filtro != 'None':
        try:
            productos = productos.filter(fknegocioasociado_prod__pkid_neg=int(negocio_filtro))
        except (ValueError, TypeError):
            pass
    
    if precio_min:
        try:
            productos = productos.filter(precio_prod__gte=float(precio_min))
        except (ValueError, TypeError):
            pass
    
    if precio_max:
        try:
            productos = productos.filter(precio_prod__lte=float(precio_max))
        except (ValueError, TypeError):
            pass
    
    if buscar and buscar != 'None':
        productos = productos.filter(
            Q(nom_prod__icontains=buscar) |
            Q(desc_prod__icontains=buscar) |
            Q(fknegocioasociado_prod__nom_neg__icontains=buscar)
        )
    
    if ordenar_por == 'precio_asc':
        productos = productos.order_by('precio_prod')
    elif ordenar_por == 'precio_desc':
        productos = productos.order_by('-precio_prod')
    elif ordenar_por == 'nombre':
        productos = productos.order_by('nom_prod')
    elif ordenar_por == 'recientes':
        productos = productos.order_by('-fecha_creacion')
    elif ordenar_por == 'stock':
        productos = productos.order_by('-stock_prod')
    
    productos_data = []
    for producto in productos:
        variantes = VariantesProducto.objects.filter(
            producto=producto, 
            estado_variante='activa'
        )
        tiene_variantes = variantes.exists()
        
        precio_original = producto.precio_prod
        precio_final = precio_original
        
        productos_data.append({
            'producto': producto,
            'tiene_variantes': tiene_variantes,
            'variantes': variantes,
            'precio_original': precio_original,
            'precio_final': precio_final,
            'tiene_descuento': False,
            'descuento_porcentaje': 0,
        })
    
    paginator = Paginator(productos_data, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'productos_data': page_obj,
        'categorias': categorias,
        'negocios': negocios,
        'filtros_aplicados': {
            'categoria': categoria_filtro,
            'negocio': negocio_filtro,
            'precio_min': precio_min,
            'precio_max': precio_max,
            'ordenar_por': ordenar_por,
            'buscar': buscar,
        },
        'total_productos': paginator.count,
    }
    
    return render(request, 'Cliente/todos_productos.html', context)

def productos_por_categoria(request, categoria_id):
    categoria = get_object_or_404(CategoriaProductos, pkid_cp=categoria_id)
    
    productos = Productos.objects.select_related(
        'fknegocioasociado_prod', 
        'fkcategoria_prod'
    ).prefetch_related('variantesproducto_set').filter(
        estado_prod='disponible',
        fkcategoria_prod=categoria
    ).order_by('-fecha_creacion')
    
    categorias = CategoriaProductos.objects.annotate(
        num_productos=Count('productos')
    ).order_by('desc_cp')
    
    negocios = Negocios.objects.filter(estado_neg='activo').annotate(
        num_productos=Count('productos')
    ).order_by('nom_neg')
    
    negocio_filtro = request.GET.get('negocio')
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    ordenar_por = request.GET.get('ordenar_por', 'recientes')
    buscar = request.GET.get('buscar')
    
    if negocio_filtro:
        productos = productos.filter(fknegocioasociado_prod__pkid_neg=negocio_filtro)
    
    if precio_min:
        productos = productos.filter(precio_prod__gte=precio_min)
    
    if precio_max:
        productos = productos.filter(precio_prod__lte=precio_max)
    
    if buscar:
        productos = productos.filter(
            Q(nom_prod__icontains=buscar) |
            Q(desc_prod__icontains=buscar) |
            Q(fknegocioasociado_prod__nom_neg__icontains=buscar)
        )
    
    if ordenar_por == 'precio_asc':
        productos = productos.order_by('precio_prod')
    elif ordenar_por == 'precio_desc':
        productos = productos.order_by('-precio_prod')
    elif ordenar_por == 'nombre':
        productos = productos.order_by('nom_prod')
    elif ordenar_por == 'recientes':
        productos = productos.order_by('-fecha_creacion')
    elif ordenar_por == 'stock':
        productos = productos.order_by('-stock_prod')
    
    productos_data = []
    for producto in productos:
        variantes = VariantesProducto.objects.filter(
            producto=producto, 
            estado_variante='activa'
        )
        tiene_variantes = variantes.exists()
        
        precio_original = producto.precio_prod
        precio_final = precio_original
        
        productos_data.append({
            'producto': producto,
            'tiene_variantes': tiene_variantes,
            'variantes': variantes,
            'precio_original': precio_original,
            'precio_final': precio_final,
            'tiene_descuento': False,
            'descuento_porcentaje': 0,
        })
    
    paginator = Paginator(productos_data, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'productos_data': page_obj,
        'categorias': categorias,
        'negocios': negocios,
        'categoria_actual': categoria,
        'filtros_aplicados': {
            'categoria': categoria_id,
            'negocio': negocio_filtro,
            'precio_min': precio_min,
            'precio_max': precio_max,
            'ordenar_por': ordenar_por,
            'buscar': buscar,
        },
        'total_productos': paginator.count,
    }
    
    return render(request, 'cliente/todos_productos.html', context)

def detalle_negocio(request, id):
    negocio = get_object_or_404(Negocios, pkid_neg=id, estado_neg='activo')
    propietario = negocio.fkpropietario_neg
    tipo_negocio = negocio.fktiponeg_neg

    productos = Productos.objects.filter(
        fknegocioasociado_prod=negocio,
        estado_prod='disponible'
    ).select_related('fkcategoria_prod')
    
    resenas = ResenasNegocios.objects.filter(
        fknegocio_resena=negocio,
        estado_resena='activa'
    ).select_related('fkusuario_resena__fkuser')

    promedio_calificacion = resenas.aggregate(
        promedio=Avg('estrellas'),
        total_resenas=Count('pkid_resena')
    )

    contexto = {
        'negocio': negocio,
        'propietario': propietario,
        'productos': productos,
        'tipo_negocio': tipo_negocio,
        'resenas': resenas,
        'promedio_calificacion': promedio_calificacion['promedio'] or 0,
        'total_resenas': promedio_calificacion['total_resenas'] or 0,
        'nombre': request.user.first_name if request.user.is_authenticated else '',
    }

    return render(request, 'Cliente/detalle_neg.html', contexto)

@never_cache
@login_required(login_url='/auth/login/')
def cliente_dashboard(request):
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        from django.utils import timezone
        from django.db.models import Q, Avg, Count, Sum
        from django.db import connection
        from decimal import Decimal
        hoy = timezone.now().date()

        # =============================================
        # DETECCIÓN DE FECHAS ESPECIALES
        # =============================================
        fecha_especial = None
        mensaje_especial = None
        try:
            mes_actual = hoy.month
            dia_actual = hoy.day
            
            # Detectar fechas especiales - NAVIDAD CORREGIDA
            if mes_actual == 11 and dia_actual >= 28:  # Desde 28 de noviembre
                fecha_especial = "navidad"
                mensaje_especial = "🎄 ¡Especiales de Navidad! 🎁"
            elif mes_actual == 12:  # Todo diciembre
                if dia_actual <= 25:
                    fecha_especial = "navidad"
                    mensaje_especial = "🎄 ¡Especiales de Navidad! 🎁"
                else:
                    fecha_especial = "navidad" 
                    mensaje_especial = "🎄 ¡Ofertas Post-Navidad! 🎁"
            elif mes_actual == 2 and dia_actual == 14:
                fecha_especial = "san_valentin"
                mensaje_especial = "💝 Ofertas de San Valentín"
            elif mes_actual == 5 and (dia_actual >= 8 and dia_actual <= 15):
                fecha_especial = "dia_madre"
                mensaje_especial = "🌸 Especial Día de la Madre"
            elif mes_actual == 6 and (dia_actual >= 15 and dia_actual <= 20):
                fecha_especial = "dia_padre"
                mensaje_especial = "👔 Especial Día del Padre"
            elif mes_actual == 11 and dia_actual >= 20 and dia_actual <= 27:  # Black Friday antes del 28
                fecha_especial = "black_friday"
                mensaje_especial = "⚫️ Black Friday ⚫️"
            elif (mes_actual == 12 and dia_actual >= 28) or (mes_actual == 1 and dia_actual <= 10):
                fecha_especial = "ano_nuevo"
                mensaje_especial = "🎉 Ofertas de Año Nuevo"
            elif mes_actual == 9 and (dia_actual >= 15 and dia_actual <= 20):
                 fecha_especial = "fiestas_patrias"
                 mensaje_especial = "🇨🇱 ¡Fiestas Patrias! 🇨🇱"
                
        except Exception:
            pass

        # =============================================
        # FUNCIÓN AUXILIAR PARA OFERTAS
        # =============================================
        def obtener_info_oferta_corregida(producto_id, variante_id=None):
            try:
                with connection.cursor() as cursor:
                    if variante_id:
                        cursor.execute("""
                            SELECT p.porcentaje_descuento, p.pkid_promo, p.variante_id
                            FROM promociones p
                            WHERE p.fkproducto_id = %s 
                            AND p.variante_id = %s
                            AND p.estado_promo = 'activa'
                            AND p.fecha_inicio <= %s 
                            AND p.fecha_fin >= %s
                            AND p.porcentaje_descuento > 0
                            LIMIT 1
                        """, [producto_id, variante_id, hoy, hoy])
                        result = cursor.fetchone()
                        
                        if result:
                            return {
                                'porcentaje_descuento': float(result[0]),
                                'pkid_promo': result[1],
                                'variante_id': result[2],
                                'es_oferta_especifica': True,
                                'tiene_oferta': True
                            }
                    
                    if variante_id is None:
                        cursor.execute("""
                            SELECT p.porcentaje_descuento, p.pkid_promo, p.variante_id
                            FROM promociones p
                            WHERE p.fkproducto_id = %s 
                            AND p.variante_id IS NULL
                            AND p.estado_promo = 'activa'
                            AND p.fecha_inicio <= %s 
                            AND p.fecha_fin >= %s
                            AND p.porcentaje_descuento > 0
                            LIMIT 1
                        """, [producto_id, hoy, hoy])
                        
                        result = cursor.fetchone()
                        if result:
                            return {
                                'porcentaje_descuento': float(result[0]),
                                'pkid_promo': result[1],
                                'variante_id': result[2],
                                'es_oferta_especifica': False,
                                'tiene_oferta': True
                            }
                    
                    return None
            except Exception:
                return None

        # =============================================
        # OFERTAS CARRUSEL
        # =============================================
        ofertas_carrusel_data = []
        try:
            fecha_limite = hoy - timezone.timedelta(days=5)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT p.pkid_promo, p.titulo_promo, p.descripcion_promo, 
                           p.porcentaje_descuento, p.fecha_inicio, p.fecha_fin,
                           p.estado_promo, p.imagen_promo,
                           p.fknegocio_id, p.fkproducto_id, p.variante_id
                    FROM promociones p
                    INNER JOIN productos pr ON p.fkproducto_id = pr.pkid_prod
                    WHERE p.estado_promo = 'activa'
                    AND p.fecha_inicio >= %s
                    AND p.fecha_fin >= %s
                    AND pr.stock_prod > 0
                    AND pr.estado_prod = 'disponible'
                    ORDER BY p.fecha_inicio DESC
                    LIMIT 5
                """, [fecha_limite, hoy])
                
                ofertas_carrusel = cursor.fetchall()
                
                for row in ofertas_carrusel:
                    try:
                        descuento_valor = 0
                        if row[3] is not None:
                            try:
                                descuento_valor = float(row[3])
                            except (ValueError, TypeError):
                                descuento_valor = 0
                        
                        producto = Productos.objects.get(pkid_prod=row[9])
                        negocio = Negocios.objects.get(pkid_neg=row[8])
                        variante_id = row[10]
                        
                        precio_base = float(producto.precio_prod) if producto.precio_prod else 0
                        variante_nombre = None
                        
                        if variante_id:
                            try:
                                variante = VariantesProducto.objects.get(
                                    id_variante=variante_id,
                                    producto=producto,
                                    estado_variante='activa'
                                )
                                if variante.precio_adicional:
                                    precio_base += float(variante.precio_adicional)
                                variante_nombre = variante.nombre_variante
                            except VariantesProducto.DoesNotExist:
                                pass
                        
                        ahorro_oferta = precio_base * (descuento_valor / 100)
                        
                        titulo_corto = f"{producto.nom_prod}"
                        if variante_nombre:
                            titulo_corto = f"{variante_nombre}"
                        
                        descripcion_corta = f"Oferta especial -{descuento_valor}% OFF"
                        
                        oferta_data = {
                            'pkid_promo': row[0],
                            'titulo_promo': titulo_corto,
                            'descripcion_promo': descripcion_corta,
                            'porcentaje_descuento': descuento_valor,
                            'precio_base': precio_base,
                            'precio_final': precio_base - ahorro_oferta,
                            'ahorro_oferta': round(ahorro_oferta, 2),
                            'imagen_promo': row[7] or (producto.img_prod.url if producto.img_prod else None),
                            'fkproducto': producto,
                            'fknegocio': negocio,
                            'variante_id': variante_id,
                            'variante_nombre': variante_nombre,
                        }
                        
                        ofertas_carrusel_data.append(oferta_data)
                        
                    except Exception:
                        continue
        except Exception:
            pass

        # =============================================
        # PRODUCTOS POR FECHA ESPECIAL - CON CATEGORÍAS REALES
        # =============================================
        productos_fecha_especial_data = []
        try:
            if fecha_especial:
                categorias_fecha_especial = []
                
                if fecha_especial == "navidad":
                    categorias_fecha_especial = [1, 5, 19, 12, 39]
                elif fecha_especial == "san_valentin":
                    categorias_fecha_especial = [12, 31, 14]
                elif fecha_especial == "dia_madre":
                    categorias_fecha_especial = [14, 6, 8, 5]
                elif fecha_especial == "dia_padre":
                    categorias_fecha_especial = [1, 17, 27]
                elif fecha_especial == "black_friday":
                    categorias_fecha_especial = [1, 2, 5, 33]
                elif fecha_especial == "ano_nuevo":
                    categorias_fecha_especial = [12, 46, 39]
                elif fecha_especial == "fiestas_patrias":
                    categorias_fecha_especial = [8, 46, 39]
                
                if categorias_fecha_especial:
                    productos_fecha_especial = Productos.objects.filter(
                        estado_prod='disponible',
                        fkcategoria_prod__in=categorias_fecha_especial
                    ).order_by('?')[:10]
                    
                    for producto in productos_fecha_especial:
                        try:
                            tiene_stock_base = (producto.stock_prod or 0) > 0
                            tiene_variantes_con_stock = VariantesProducto.objects.filter(
                                producto=producto,
                                estado_variante='activa',
                                stock_variante__gt=0
                            ).exists()
                            
                            if not tiene_stock_base and not tiene_variantes_con_stock:
                                continue
                            
                            precio_base_producto = float(producto.precio_prod) if producto.precio_prod else 0
                            
                            info_oferta_producto = obtener_info_oferta_corregida(producto.pkid_prod)
                            if info_oferta_producto:
                                descuento_porcentaje_producto = info_oferta_producto['porcentaje_descuento']
                                ahorro_producto = precio_base_producto * (descuento_porcentaje_producto / 100)
                                precio_final_producto = precio_base_producto - ahorro_producto
                                tiene_oferta_producto = True
                            else:
                                descuento_porcentaje_producto = 0
                                ahorro_producto = 0
                                precio_final_producto = precio_base_producto
                                tiene_oferta_producto = False
                            
                            # Procesar variantes
                            variantes_list = []
                            tiene_variantes = VariantesProducto.objects.filter(
                                producto=producto, 
                                estado_variante='activa'
                            ).exists()
                            
                            if tiene_variantes:
                                variantes = VariantesProducto.objects.filter(
                                    producto=producto,
                                    estado_variante='activa'
                                )
                                
                                for variante in variantes:
                                    try:
                                        stock_variante = variante.stock_variante or 0
                                        if stock_variante <= 0:
                                            continue
                                        
                                        precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                                        precio_base_variante = precio_base_producto + precio_adicional
                                        
                                        info_oferta_variante = obtener_info_oferta_corregida(
                                            producto.pkid_prod, 
                                            variante.id_variante
                                        )
                                        
                                        if info_oferta_variante:
                                            descuento_porcentaje_variante = info_oferta_variante['porcentaje_descuento']
                                            ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                                            precio_final_variante = precio_base_variante - ahorro_variante
                                            tiene_descuento_variante = True
                                            tiene_oferta_activa_variante = True
                                        else:
                                            descuento_porcentaje_variante = 0
                                            ahorro_variante = 0
                                            precio_final_variante = precio_base_variante
                                            tiene_descuento_variante = False
                                            tiene_oferta_activa_variante = False
                                        
                                        variante_data = {
                                            'id_variante': variante.id_variante,
                                            'nombre_variante': variante.nombre_variante,
                                            'precio_adicional': precio_adicional,
                                            'stock_variante': stock_variante,
                                            'imagen_variante': variante.imagen_variante,
                                            'estado_variante': variante.estado_variante,
                                            'sku_variante': variante.sku_variante,
                                            'precio_base_calculado': round(precio_base_variante, 2),
                                            'precio_final_calculado': round(precio_final_variante, 2),
                                            'ahorro_calculado': round(ahorro_variante, 2),
                                            'descuento_porcentaje_calculado': descuento_porcentaje_variante,
                                            'tiene_descuento_calculado': tiene_descuento_variante,
                                            'tiene_oferta_activa': tiene_oferta_activa_variante,
                                        }
                                        variantes_list.append(variante_data)
                                        
                                    except Exception:
                                        continue
                            
                            tiene_stock_para_mostrar = tiene_stock_base or len(variantes_list) > 0
                            
                            if tiene_stock_para_mostrar:
                                producto_data = {
                                    'producto': producto,
                                    'precio_base': precio_base_producto,
                                    'precio_final': round(precio_final_producto, 2),
                                    'tiene_descuento': tiene_oferta_producto,
                                    'descuento_porcentaje': descuento_porcentaje_producto,
                                    'ahorro': round(ahorro_producto, 2),
                                    'tiene_variantes': tiene_variantes,
                                    'variantes': variantes_list,
                                    'stock': producto.stock_prod or 0,
                                    'tiene_oferta_activa': tiene_oferta_producto,
                                }
                                
                                productos_fecha_especial_data.append(producto_data)
                                
                        except Exception:
                            continue
        except Exception:
            pass

        # =============================================
        # ELECTRODOMÉSTICOS - CON CATEGORÍA REAL
        # =============================================
        electrodomesticos_data = []
        try:
            electrodomesticos = Productos.objects.filter(
                estado_prod='disponible',
                fkcategoria_prod=5
            ).order_by('-precio_prod')[:8]
            
            for producto in electrodomesticos:
                try:
                    tiene_stock_base = (producto.stock_prod or 0) > 0
                    tiene_variantes_con_stock = VariantesProducto.objects.filter(
                        producto=producto,
                        estado_variante='activa',
                        stock_variante__gt=0
                    ).exists()
                    
                    if not tiene_stock_base and not tiene_variantes_con_stock:
                        continue
                    
                    precio_base_producto = float(producto.precio_prod) if producto.precio_prod else 0
                    
                    info_oferta_producto = obtener_info_oferta_corregida(producto.pkid_prod)
                    if info_oferta_producto:
                        descuento_porcentaje_producto = info_oferta_producto['porcentaje_descuento']
                        ahorro_producto = precio_base_producto * (descuento_porcentaje_producto / 100)
                        precio_final_producto = precio_base_producto - ahorro_producto
                        tiene_oferta_producto = True
                    else:
                        descuento_porcentaje_producto = 0
                        ahorro_producto = 0
                        precio_final_producto = precio_base_producto
                        tiene_oferta_producto = False
                    
                    # Procesar variantes
                    variantes_list = []
                    tiene_variantes = VariantesProducto.objects.filter(
                        producto=producto, 
                        estado_variante='activa'
                    ).exists()
                    
                    if tiene_variantes:
                        variantes = VariantesProducto.objects.filter(
                            producto=producto,
                            estado_variante='activa'
                        )
                        
                        for variante in variantes:
                            try:
                                stock_variante = variante.stock_variante or 0
                                if stock_variante <= 0:
                                    continue
                                
                                precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                                precio_base_variante = precio_base_producto + precio_adicional
                                
                                info_oferta_variante = obtener_info_oferta_corregida(
                                    producto.pkid_prod, 
                                    variante.id_variante
                                )
                                
                                if info_oferta_variante:
                                    descuento_porcentaje_variante = info_oferta_variante['porcentaje_descuento']
                                    ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                                    precio_final_variante = precio_base_variante - ahorro_variante
                                    tiene_descuento_variante = True
                                    tiene_oferta_activa_variante = True
                                else:
                                    descuento_porcentaje_variante = 0
                                    ahorro_variante = 0
                                    precio_final_variante = precio_base_variante
                                    tiene_descuento_variante = False
                                    tiene_oferta_activa_variante = False
                                
                                variante_data = {
                                    'id_variante': variante.id_variante,
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': precio_adicional,
                                    'stock_variante': stock_variante,
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                    'precio_base_calculado': round(precio_base_variante, 2),
                                    'precio_final_calculado': round(precio_final_variante, 2),
                                    'ahorro_calculado': round(ahorro_variante, 2),
                                    'descuento_porcentaje_calculado': descuento_porcentaje_variante,
                                    'tiene_descuento_calculado': tiene_descuento_variante,
                                    'tiene_oferta_activa': tiene_oferta_activa_variante,
                                }
                                variantes_list.append(variante_data)
                                
                            except Exception:
                                continue
                    
                    tiene_stock_para_mostrar = tiene_stock_base or len(variantes_list) > 0
                    
                    if tiene_stock_para_mostrar:
                        producto_data = {
                            'producto': producto,
                            'precio_base': precio_base_producto,
                            'precio_final': round(precio_final_producto, 2),
                            'tiene_descuento': tiene_oferta_producto,
                            'descuento_porcentaje': descuento_porcentaje_producto,
                            'ahorro': round(ahorro_producto, 2),
                            'tiene_variantes': tiene_variantes,
                            'variantes': variantes_list,
                            'stock': producto.stock_prod or 0,
                            'tiene_oferta_activa': tiene_oferta_producto,
                        }
                        
                        electrodomesticos_data.append(producto_data)
                    
                except Exception:
                    continue
        except Exception:
            pass

        # =============================================
        # TECNOLOGÍA - CON CATEGORÍAS REALES
        # =============================================
        tecnologia_data = []
        try:
            categorias_tecnologia = [1, 2, 3, 4, 33]
            
            tecnologia = Productos.objects.filter(
                estado_prod='disponible',
                fkcategoria_prod__in=categorias_tecnologia
            ).order_by('-precio_prod')[:8]
            
            for producto in tecnologia:
                try:
                    tiene_stock_base = (producto.stock_prod or 0) > 0
                    tiene_variantes_con_stock = VariantesProducto.objects.filter(
                        producto=producto,
                        estado_variante='activa',
                        stock_variante__gt=0
                    ).exists()
                    
                    if not tiene_stock_base and not tiene_variantes_con_stock:
                        continue
                    
                    precio_base_producto = float(producto.precio_prod) if producto.precio_prod else 0
                    
                    info_oferta_producto = obtener_info_oferta_corregida(producto.pkid_prod)
                    if info_oferta_producto:
                        descuento_porcentaje_producto = info_oferta_producto['porcentaje_descuento']
                        ahorro_producto = precio_base_producto * (descuento_porcentaje_producto / 100)
                        precio_final_producto = precio_base_producto - ahorro_producto
                        tiene_oferta_producto = True
                    else:
                        descuento_porcentaje_producto = 0
                        ahorro_producto = 0
                        precio_final_producto = precio_base_producto
                        tiene_oferta_producto = False
                    
                    # Procesar variantes
                    variantes_list = []
                    tiene_variantes = VariantesProducto.objects.filter(
                        producto=producto, 
                        estado_variante='activa'
                    ).exists()
                    
                    if tiene_variantes:
                        variantes = VariantesProducto.objects.filter(
                            producto=producto,
                            estado_variante='activa'
                        )
                        
                        for variante in variantes:
                            try:
                                stock_variante = variante.stock_variante or 0
                                if stock_variante <= 0:
                                    continue
                                
                                precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                                precio_base_variante = precio_base_producto + precio_adicional
                                
                                info_oferta_variante = obtener_info_oferta_corregida(
                                    producto.pkid_prod, 
                                    variante.id_variante
                                )
                                
                                if info_oferta_variante:
                                    descuento_porcentaje_variante = info_oferta_variante['porcentaje_descuento']
                                    ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                                    precio_final_variante = precio_base_variante - ahorro_variante
                                    tiene_descuento_variante = True
                                    tiene_oferta_activa_variante = True
                                else:
                                    descuento_porcentaje_variante = 0
                                    ahorro_variante = 0
                                    precio_final_variante = precio_base_variante
                                    tiene_descuento_variante = False
                                    tiene_oferta_activa_variante = False
                                
                                variante_data = {
                                    'id_variante': variante.id_variante,
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': precio_adicional,
                                    'stock_variante': stock_variante,
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                    'precio_base_calculado': round(precio_base_variante, 2),
                                    'precio_final_calculado': round(precio_final_variante, 2),
                                    'ahorro_calculado': round(ahorro_variante, 2),
                                    'descuento_porcentaje_calculado': descuento_porcentaje_variante,
                                    'tiene_descuento_calculado': tiene_descuento_variante,
                                    'tiene_oferta_activa': tiene_oferta_activa_variante,
                                }
                                variantes_list.append(variante_data)
                                
                            except Exception:
                                continue
                    
                    tiene_stock_para_mostrar = tiene_stock_base or len(variantes_list) > 0
                    
                    if tiene_stock_para_mostrar:
                        producto_data = {
                            'producto': producto,
                            'precio_base': precio_base_producto,
                            'precio_final': round(precio_final_producto, 2),
                            'tiene_descuento': tiene_oferta_producto,
                            'descuento_porcentaje': descuento_porcentaje_producto,
                            'ahorro': round(ahorro_producto, 2),
                            'tiene_variantes': tiene_variantes,
                            'variantes': variantes_list,
                            'stock': producto.stock_prod or 0,
                            'tiene_oferta_activa': tiene_oferta_producto,
                        }
                        
                        tecnologia_data.append(producto_data)
                    
                except Exception:
                    continue
        except Exception:
            pass

        # =============================================
        # PRODUCTOS BARATOS (MANTENER IGUAL)
        # =============================================
        productos_baratos_data = []
        try:
            productos_baratos = Productos.objects.filter(
                estado_prod='disponible',
                precio_prod__lte=50000
            ).order_by('precio_prod')[:12]
            
            for producto in productos_baratos:
                try:
                    tiene_stock_base = (producto.stock_prod or 0) > 0
                    tiene_variantes_con_stock = VariantesProducto.objects.filter(
                        producto=producto,
                        estado_variante='activa',
                        stock_variante__gt=0
                    ).exists()
                    
                    if not tiene_stock_base and not tiene_variantes_con_stock:
                        continue
                    
                    precio_base_producto = float(producto.precio_prod) if producto.precio_prod else 0
                    
                    info_oferta_producto = obtener_info_oferta_corregida(producto.pkid_prod)
                    if info_oferta_producto:
                        descuento_porcentaje_producto = info_oferta_producto['porcentaje_descuento']
                        ahorro_producto = precio_base_producto * (descuento_porcentaje_producto / 100)
                        precio_final_producto = precio_base_producto - ahorro_producto
                        tiene_oferta_producto = True
                    else:
                        descuento_porcentaje_producto = 0
                        ahorro_producto = 0
                        precio_final_producto = precio_base_producto
                        tiene_oferta_producto = False
                    
                    variantes_list = []
                    tiene_variantes = VariantesProducto.objects.filter(
                        producto=producto, 
                        estado_variante='activa'
                    ).exists()
                    
                    if tiene_variantes:
                        variantes = VariantesProducto.objects.filter(
                            producto=producto,
                            estado_variante='activa'
                        )
                        
                        for variante in variantes:
                            try:
                                stock_variante = variante.stock_variante or 0
                                if stock_variante <= 0:
                                    continue
                                
                                precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                                precio_base_variante = precio_base_producto + precio_adicional
                                
                                info_oferta_variante = obtener_info_oferta_corregida(
                                    producto.pkid_prod, 
                                    variante.id_variante
                                )
                                
                                if info_oferta_variante:
                                    descuento_porcentaje_variante = info_oferta_variante['porcentaje_descuento']
                                    ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                                    precio_final_variante = precio_base_variante - ahorro_variante
                                    tiene_descuento_variante = True
                                    tiene_oferta_activa_variante = True
                                else:
                                    descuento_porcentaje_variante = 0
                                    ahorro_variante = 0
                                    precio_final_variante = precio_base_variante
                                    tiene_descuento_variante = False
                                    tiene_oferta_activa_variante = False
                                
                                variante_data = {
                                    'id_variante': variante.id_variante,
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': precio_adicional,
                                    'stock_variante': stock_variante,
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                    'precio_base_calculado': round(precio_base_variante, 2),
                                    'precio_final_calculado': round(precio_final_variante, 2),
                                    'ahorro_calculado': round(ahorro_variante, 2),
                                    'descuento_porcentaje_calculado': descuento_porcentaje_variante,
                                    'tiene_descuento_calculado': tiene_descuento_variante,
                                    'tiene_oferta_activa': tiene_oferta_activa_variante,
                                }
                                variantes_list.append(variante_data)
                                
                            except Exception:
                                continue
                    
                    tiene_stock_para_mostrar = tiene_stock_base or len(variantes_list) > 0
                    
                    if tiene_stock_para_mostrar:
                        producto_data = {
                            'producto': producto,
                            'precio_base': precio_base_producto,
                            'precio_final': round(precio_final_producto, 2),
                            'tiene_descuento': tiene_oferta_producto,
                            'descuento_porcentaje': descuento_porcentaje_producto,
                            'ahorro': round(ahorro_producto, 2),
                            'tiene_variantes': tiene_variantes,
                            'variantes': variantes_list,
                            'stock': producto.stock_prod or 0,
                            'tiene_oferta_activa': tiene_oferta_producto,
                        }
                        
                        productos_baratos_data.append(producto_data)
                    
                except Exception:
                    continue
                    
        except Exception:
            pass

        # =============================================
        # PRODUCTOS DESTACADOS (MANTENER IGUAL)
        # =============================================
        productos_destacados_data = []
        try:
            productos_vendidos = DetallesPedido.objects.filter(
                fkproducto_detalle__estado_prod='disponible'
            ).values(
                'fkproducto_detalle'
            ).annotate(
                total_vendido=Sum('cantidad_detalle')
            ).order_by('-total_vendido')[:12]
            
            for item in productos_vendidos:
                try:
                    producto = Productos.objects.get(pkid_prod=item['fkproducto_detalle'])
                    
                    tiene_stock_base = (producto.stock_prod or 0) > 0
                    tiene_variantes_con_stock = VariantesProducto.objects.filter(
                        producto=producto,
                        estado_variante='activa',
                        stock_variante__gt=0
                    ).exists()
                    
                    if not tiene_stock_base and not tiene_variantes_con_stock:
                        continue
                    
                    precio_base_producto = float(producto.precio_prod) if producto.precio_prod else 0
                    
                    info_oferta_producto = obtener_info_oferta_corregida(producto.pkid_prod)
                    if info_oferta_producto:
                        descuento_porcentaje_producto = info_oferta_producto['porcentaje_descuento']
                        ahorro_producto = precio_base_producto * (descuento_porcentaje_producto / 100)
                        precio_final_producto = precio_base_producto - ahorro_producto
                        tiene_oferta_producto = True
                    else:
                        descuento_porcentaje_producto = 0
                        ahorro_producto = 0
                        precio_final_producto = precio_base_producto
                        tiene_oferta_producto = False
                    
                    variantes_list = []
                    tiene_variantes = VariantesProducto.objects.filter(
                        producto=producto, 
                        estado_variante='activa'
                    ).exists()
                    
                    if tiene_variantes:
                        variantes = VariantesProducto.objects.filter(
                            producto=producto,
                            estado_variante='activa'
                        )
                        
                        for variante in variantes:
                            try:
                                stock_variante = variante.stock_variante or 0
                                if stock_variante <= 0:
                                    continue
                                
                                precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                                precio_base_variante = precio_base_producto + precio_adicional
                                
                                info_oferta_variante = obtener_info_oferta_corregida(
                                    producto.pkid_prod, 
                                    variante.id_variante
                                )
                                
                                if info_oferta_variante:
                                    descuento_porcentaje_variante = info_oferta_variante['porcentaje_descuento']
                                    ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                                    precio_final_variante = precio_base_variante - ahorro_variante
                                    tiene_descuento_variante = True
                                    tiene_oferta_activa_variante = True
                                else:
                                    descuento_porcentaje_variante = 0
                                    ahorro_variante = 0
                                    precio_final_variante = precio_base_variante
                                    tiene_descuento_variante = False
                                    tiene_oferta_activa_variante = False
                                
                                variante_data = {
                                    'id_variante': variante.id_variante,
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': precio_adicional,
                                    'stock_variante': stock_variante,
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                    'precio_base_calculado': round(precio_base_variante, 2),
                                    'precio_final_calculado': round(precio_final_variante, 2),
                                    'ahorro_calculado': round(ahorro_variante, 2),
                                    'descuento_porcentaje_calculado': descuento_porcentaje_variante,
                                    'tiene_descuento_calculado': tiene_descuento_variante,
                                    'tiene_oferta_activa': tiene_oferta_activa_variante,
                                }
                                variantes_list.append(variante_data)
                                
                            except Exception:
                                continue
                    
                    tiene_stock_para_mostrar = tiene_stock_base or len(variantes_list) > 0
                    
                    if tiene_stock_para_mostrar:
                        producto_data = {
                            'producto': producto,
                            'precio_base': precio_base_producto,
                            'precio_final': round(precio_final_producto, 2),
                            'total_vendido': item['total_vendido'],
                            'tiene_descuento': tiene_oferta_producto,
                            'descuento_porcentaje': descuento_porcentaje_producto,
                            'ahorro': round(ahorro_producto, 2),
                            'tiene_variantes': tiene_variantes,
                            'variantes': variantes_list,
                            'stock': producto.stock_prod or 0,
                            'tiene_oferta_activa': tiene_oferta_producto,
                        }
                        
                        productos_destacados_data.append(producto_data)
                    
                except Productos.DoesNotExist:
                    continue
                except Exception:
                    continue
        except Exception:
            pass

        # =============================================
        # PRODUCTOS EN OFERTA (MANTENER IGUAL)
        # =============================================
        productos_oferta_data = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT 
                        p.pkid_promo, p.titulo_promo, p.descripcion_promo,
                        p.porcentaje_descuento, p.fkproducto_id, p.variante_id,
                        pr.nom_prod, pr.precio_prod, pr.desc_prod, 
                        pr.stock_prod, pr.img_prod, pr.fknegocioasociado_prod,
                        vp.nombre_variante, vp.precio_adicional, vp.stock_variante, 
                        vp.imagen_variante, vp.id_variante
                    FROM promociones p
                    INNER JOIN productos pr ON p.fkproducto_id = pr.pkid_prod
                    LEFT JOIN variantes_producto vp ON p.variante_id = vp.id_variante AND vp.producto_id = pr.pkid_prod
                    WHERE pr.estado_prod = 'disponible'
                    AND p.estado_promo = 'activa'
                    AND p.fecha_inicio <= %s
                    AND p.fecha_fin >= %s
                    AND p.porcentaje_descuento > 0
                    AND (
                        (p.variante_id IS NULL AND pr.stock_prod > 0) OR 
                        (p.variante_id IS NOT NULL AND vp.stock_variante > 0)
                    )
                    ORDER BY p.porcentaje_descuento DESC
                    LIMIT 12
                """, [hoy, hoy])
                
                productos_oferta_rows = cursor.fetchall()
                
                for row in productos_oferta_rows:
                    try:
                        producto_id = row[4]
                        producto = Productos.objects.get(pkid_prod=producto_id)
                        variante_id = row[5]
                        
                        precio_base = float(row[7]) if row[7] else 0
                        precio_original = precio_base
                        descuento_porcentaje = 0
                        descuento_monto = 0
                        precio_final = precio_base
                        variante_info = None
                        
                        imagen_producto_url = None
                        
                        if row[3] is not None:
                            try:
                                descuento_porcentaje = float(row[3])
                                if descuento_porcentaje > 0:
                                    if variante_id:
                                        try:
                                            variante_nombre = row[12] if row[12] else "Variante"
                                            precio_adicional = float(row[13]) if row[13] else 0
                                            stock_variante = row[14] if row[14] else 0
                                            imagen_variante = row[15]
                                            id_variante = row[16] if row[16] else variante_id
                                            
                                            precio_base += precio_adicional
                                            precio_original = precio_base
                                            descuento_monto = precio_base * (descuento_porcentaje / 100)
                                            precio_final = precio_base - descuento_monto
                                            
                                            if imagen_variante:
                                                try:
                                                    variante_obj = VariantesProducto.objects.get(id_variante=variante_id)
                                                    imagen_producto_url = variante_obj.imagen_variante.url if variante_obj.imagen_variante else None
                                                except:
                                                    imagen_producto_url = None
                                            else:
                                                imagen_producto_url = producto.img_prod.url if producto.img_prod else None
                                            
                                            variante_info = {
                                                'id': id_variante,
                                                'nombre': variante_nombre,
                                                'precio_adicional': precio_adicional,
                                                'stock': stock_variante,
                                                'imagen': imagen_variante
                                            }
                                        except Exception:
                                            continue
                                    else:
                                        if (producto.stock_prod or 0) > 0:
                                            precio_original = precio_base
                                            descuento_monto = precio_base * (descuento_porcentaje / 100)
                                            precio_final = precio_base - descuento_monto
                                            imagen_producto_url = producto.img_prod.url if producto.img_prod else None
                                        else:
                                            continue
                            except (ValueError, TypeError):
                                pass
                        
                        if not imagen_producto_url and producto.img_prod:
                            imagen_producto_url = producto.img_prod.url
                        
                        if descuento_porcentaje > 0:
                            producto_data = {
                                'producto': producto,
                                'precio_base': precio_base,
                                'precio_final': round(precio_final, 2),
                                'precio_original': precio_original,
                                'tiene_descuento': True,
                                'descuento_porcentaje': descuento_porcentaje,
                                'descuento_monto': round(descuento_monto, 2),
                                'ahorro': round(descuento_monto, 2),
                                'tiene_variantes': variante_info is not None,
                                'variantes': [],
                                'variante': variante_info,
                                'stock': row[9] or 0,
                                'tiene_oferta_activa': True,
                                'imagen_producto': imagen_producto_url,
                                'pkid_promo': row[0],
                                'titulo_promo': row[1],
                            }
                            
                            productos_oferta_data.append(producto_data)
                        
                    except Exception:
                        continue
        except Exception:
            pass

        # =============================================
        # NEGOCIOS DESTACADOS (MANTENER IGUAL)
        # =============================================
        negocios_destacados_data = []
        try:
            negocios_con_resenas = Negocios.objects.filter(
                estado_neg='activo'
            ).annotate(
                promedio_calificacion=Avg('resenasnegocios__estrellas')
            ).filter(
                promedio_calificacion__gte=4.0
            ).order_by('-promedio_calificacion')[:6]
            
            for negocio in negocios_con_resenas:
                try:
                    total_resenas = ResenasNegocios.objects.filter(
                        fknegocio_resena=negocio
                    ).count()
                    
                    total_productos_disponibles = Productos.objects.filter(
                        fknegocioasociado_prod=negocio,
                        estado_prod='disponible'
                    ).count()
                    
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT COUNT(DISTINCT pr.pkid_prod)
                            FROM productos pr
                            INNER JOIN promociones p ON pr.pkid_prod = p.fkproducto_id
                            WHERE pr.fknegocioasociado_prod = %s
                            AND pr.estado_prod = 'disponible'
                            AND p.estado_promo = 'activa'
                            AND p.fecha_inicio <= %s
                            AND p.fecha_fin >= %s
                        """, [negocio.pkid_neg, hoy, hoy])
                        
                        productos_en_oferta = cursor.fetchone()[0] or 0
                    
                    negocio_data = {
                        'negocio': negocio,
                        'promedio_calificacion': float(negocio.promedio_calificacion) if negocio.promedio_calificacion else 0,
                        'total_resenas': total_resenas,
                        'total_productos': total_productos_disponibles,
                        'productos_en_oferta': productos_en_oferta,
                    }
                    
                    negocios_destacados_data.append(negocio_data)
                    
                except Exception:
                    continue
        except Exception:
            pass

        # =============================================
        # OTROS NEGOCIOS (MANTENER IGUAL)
        # =============================================
        otros_negocios_data = []
        try:
            negocios_destacados_ids = [neg['negocio'].pkid_neg for neg in negocios_destacados_data]
            
            otros_negocios = Negocios.objects.filter(
                estado_neg='activo'
            ).exclude(
                pkid_neg__in=negocios_destacados_ids
            ).annotate(
                promedio_calificacion=Avg('resenasnegocios__estrellas')
            ).order_by('-promedio_calificacion')[:6]
            
            for negocio in otros_negocios:
                try:
                    total_resenas = ResenasNegocios.objects.filter(
                        fknegocio_resena=negocio
                    ).count()
                    
                    total_productos_disponibles = Productos.objects.filter(
                        fknegocioasociado_prod=negocio,
                        estado_prod='disponible'
                    ).count()
                    
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT COUNT(DISTINCT pr.pkid_prod)
                            FROM productos pr
                            INNER JOIN promociones p ON pr.pkid_prod = p.fkproducto_id
                            WHERE pr.fknegocioasociado_prod = %s
                            AND pr.estado_prod = 'disponible'
                            AND p.estado_promo = 'activa'
                            AND p.fecha_inicio <= %s
                            AND p.fecha_fin >= %s
                        """, [negocio.pkid_neg, hoy, hoy])
                        
                        productos_en_oferta = cursor.fetchone()[0] or 0
                    
                    negocio_data = {
                        'negocio': negocio,
                        'promedio_calificacion': float(negocio.promedio_calificacion) if negocio.promedio_calificacion else 0,
                        'total_resenas': total_resenas,
                        'total_productos': total_productos_disponibles,
                        'productos_en_oferta': productos_en_oferta,
                    }
                    
                    otros_negocios_data.append(negocio_data)
                    
                except Exception:
                    continue
        except Exception:
            pass

        # =============================================
        # CONTADORES Y CONTEXT FINAL
        # =============================================
        carrito_count = 0
        favoritos_count = 0
        
        try:
            carrito_count = CarritoItem.objects.filter(
                fkcarrito__fkusuario_carrito=perfil_cliente
            ).count()
            
            favoritos_count = Favoritos.objects.filter(
                fkusuario=perfil_cliente
            ).count()
        except Exception:
            pass

        pedidos_pendientes_count = 0
        try:
            pedidos_pendientes_count = Pedidos.objects.filter(
                fkusuario_pedido=perfil_cliente,
                estado_pedido__in=['pendiente', 'confirmado', 'preparando']
            ).count()
        except Exception:
            pass

        context = {
            'perfil': perfil_cliente,
            'carrito_count': carrito_count,
            'favoritos_count': favoritos_count,
            'pedidos_pendientes_count': pedidos_pendientes_count,
            
            # Secciones originales
            'ofertas_carrusel': ofertas_carrusel_data,
            'productos_baratos': productos_baratos_data,
            'productos_destacados': productos_destacados_data,
            'productos_oferta': productos_oferta_data,
            'negocios_destacados': negocios_destacados_data,
            'otros_negocios': otros_negocios_data,
            
            # NUEVAS SECCIONES
            'fecha_especial': fecha_especial,
            'mensaje_especial': mensaje_especial,
            'productos_fecha_especial': productos_fecha_especial_data,
            'electrodomesticos': electrodomesticos_data,
            'tecnologia': tecnologia_data,
            
            # Flags de existencia
            'hay_ofertas_activas': len(ofertas_carrusel_data) > 0,
            'hay_productos_baratos': len(productos_baratos_data) > 0,
            'hay_productos_destacados': len(productos_destacados_data) > 0,
            'hay_productos_oferta': len(productos_oferta_data) > 0,
            'hay_negocios_destacados': len(negocios_destacados_data) > 0,
            'hay_otros_negocios': len(otros_negocios_data) > 0,
            'hay_fecha_especial': fecha_especial is not None,
            'hay_productos_fecha_especial': len(productos_fecha_especial_data) > 0,
            'hay_electrodomesticos': len(electrodomesticos_data) > 0,
            'hay_tecnologia': len(tecnologia_data) > 0,
        }
        
        return render(request, 'Cliente/Cliente.html', context)
        
    except Exception:
        return render(request, 'Cliente/Cliente.html', {
            'carrito_count': 0,
            'favoritos_count': 0,
            'pedidos_pendientes_count': 0,
            'ofertas_carrusel': [],
            'productos_baratos': [],
            'productos_destacados': [],
            'productos_oferta': [],
            'negocios_destacados': [],
            'otros_negocios': [],
            'productos_fecha_especial': [],
            'electrodomesticos': [],
            'tecnologia': [],
            'hay_ofertas_activas': False,
            'hay_productos_baratos': False,
            'hay_productos_destacados': False,
            'hay_productos_oferta': False,
            'hay_negocios_destacados': False,
            'hay_otros_negocios': False,
            'hay_fecha_especial': False,
            'hay_productos_fecha_especial': False,
            'hay_electrodomesticos': False,
            'hay_tecnologia': False,
        })
        
@login_required(login_url='/auth/login/')
def detalle_negocio_logeado(request, id):
    try:
        negocio = get_object_or_404(
            Negocios.objects.select_related('fkpropietario_neg', 'fktiponeg_neg'), 
            pkid_neg=id, 
            estado_neg='activo'
        )
        
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        productos = Productos.objects.filter(
            fknegocioasociado_prod=negocio,
            estado_prod='disponible'
        ).select_related('fkcategoria_prod')
        
        productos_list = []
        hoy = timezone.now().date()
        
        for producto in productos:
            precio_base = float(producto.precio_prod) if producto.precio_prod else 0
            precio_final = precio_base
            descuento_porcentaje = 0
            ahorro = 0
            tiene_descuento = False
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT porcentaje_descuento 
                    FROM promociones 
                    WHERE fkproducto_id = %s 
                    AND estado_promo = 'activa'
                    AND fecha_inicio <= %s 
                    AND fecha_fin >= %s
                    LIMIT 1
                """, [producto.pkid_prod, hoy, hoy])
                
                result = cursor.fetchone()
                if result and result[0] is not None:
                    try:
                        descuento_porcentaje = float(result[0])
                        if descuento_porcentaje > 0:
                            precio_final = precio_base * (1 - (descuento_porcentaje / 100))
                            ahorro = precio_base - precio_final
                            tiene_descuento = True
                    except (ValueError, TypeError):
                        pass
            
            variantes_list = []
            tiene_variantes = VariantesProducto.objects.filter(
                producto=producto, 
                estado_variante='activa'
            ).exists()
            
            if tiene_variantes:
                variantes = VariantesProducto.objects.filter(
                    producto=producto,
                    estado_variante='activa'
                )
                
                for variante in variantes:
                    try:
                        variante_data = {
                            'id_variante': variante.id_variante,
                            'nombre_variante': variante.nombre_variante,
                            'precio_adicional': float(variante.precio_adicional) if variante.precio_adicional else 0,
                            'stock_variante': variante.stock_variante or 0,
                            'imagen_variante': variante.imagen_variante,
                        }
                        variantes_list.append(variante_data)
                    except Exception:
                        continue
            
            stock_total = producto.stock_prod or 0
            if tiene_variantes:
                stock_variantes = sum(variante['stock_variante'] for variante in variantes_list)
                stock_total += stock_variantes
            
            producto_data = {
                'producto': producto,
                'precio_base': precio_base,
                'precio_final': round(precio_final, 2),
                'tiene_descuento': tiene_descuento,
                'descuento_porcentaje': descuento_porcentaje,
                'ahorro': round(ahorro, 2),
                'tiene_variantes': tiene_variantes,
                'variantes': variantes_list,
                'stock': stock_total,
            }
            productos_list.append(producto_data)
        
        resenas_list = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            estado_resena='activa'
        ).select_related('fkusuario_resena__fkuser').order_by('-fecha_resena')
        
        paginator = Paginator(resenas_list, 5)
        page_number = request.GET.get('page', 1)
        resenas_paginadas = paginator.get_page(page_number)
        
        total_resenas = resenas_list.count()
        
        promedio_calificacion = resenas_list.aggregate(
            promedio=Avg('estrellas')
        )['promedio'] or 0
        
        distribucion_estrellas = []
        conteo_estrellas = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        
        for resena in resenas_list:
            if resena.estrellas in conteo_estrellas:
                conteo_estrellas[resena.estrellas] += 1
        
        for estrellas in [5, 4, 3, 2, 1]:
            cantidad = conteo_estrellas[estrellas]
            porcentaje = (cantidad / total_resenas * 100) if total_resenas > 0 else 0
            
            distribucion_estrellas.append({
                'estrellas': estrellas,
                'cantidad': cantidad,
                'porcentaje': round(porcentaje, 1)
            })
        
        estadisticas_resenas = {
            'promedio': round(promedio_calificacion, 1),
            'total_resenas': total_resenas,
            'distribucion': distribucion_estrellas,
        }
        
        for item in distribucion_estrellas:
            estrellas = item['estrellas']
            estadisticas_resenas[f'porcentaje_{estrellas}'] = item['porcentaje']
            estadisticas_resenas[f'{estrellas}_estrellas'] = item['cantidad']
        
        for star in [5, 4, 3, 2, 1]:
            if f'porcentaje_{star}' not in estadisticas_resenas:
                estadisticas_resenas[f'porcentaje_{star}'] = 0
            if f'{star}_estrellas' not in estadisticas_resenas:
                estadisticas_resenas[f'{star}_estrellas'] = 0
        
        usuario_ya_reseno = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            fkusuario_resena=perfil_cliente,
            estado_resena='activa'
        ).exists()
        
        reseña_usuario_actual = None
        if usuario_ya_reseno:
            reseña_usuario_actual = ResenasNegocios.objects.filter(
                fknegocio_resena=negocio,
                fkusuario_resena=perfil_cliente,
                estado_resena='activa'
            ).first()
        
        carrito_count = 0
        try:
            carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        except Exception:
            pass
        
        contexto = {
            'negocio': negocio,
            'propietario': negocio.fkpropietario_neg,
            'tipo_negocio': negocio.fktiponeg_neg,
            'productos': productos_list,
            'perfil_cliente': perfil_cliente,
            'resenas': resenas_paginadas,
            'estadisticas_resenas': estadisticas_resenas,
            'distribucion_estrellas': distribucion_estrellas,
            'usuario_ya_reseno': usuario_ya_reseno,
            'reseña_usuario_actual': reseña_usuario_actual,
            'carrito_count': carrito_count,
            'es_vista_logeada': True,
            'nombre': f"{request.user.first_name} {request.user.last_name}",
            
            'hay_productos': len(productos_list) > 0,
            'hay_resenas': total_resenas > 0,
            'total_resenas': total_resenas,
            'hay_mas_resenas': resenas_paginadas.has_next(),
            'pagina_actual': page_number,
            'total_paginas': paginator.num_pages,
        }
        
        return render(request, 'cliente/detalle_neg_logeado.html', contexto)
        
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, 'Complete su perfil para acceder a esta funcionalidad.')
        return redirect('completar_perfil')
    except Exception:
        messages.error(request, 'Error al cargar el detalle del negocio')
        return redirect('cliente_dashboard')  

@login_required
def reportar_negocio(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            negocio_id = data.get('negocio_id')
            reseña_id = data.get('reseña_id')
            asunto = data.get('asunto')
            motivo = data.get('motivo')
            descripcion = data.get('descripcion', '')
            
            if not negocio_id or not asunto or not motivo:
                return JsonResponse({
                    'success': False, 
                    'message': 'Faltan campos obligatorios'
                })
            
            perfil_usuario = UsuarioPerfil.objects.get(fkuser=request.user)
            
            negocio = Negocios.objects.get(pkid_neg=negocio_id)
            
            tipo_reporte = 'resena' if reseña_id else 'negocio'
            reseña_obj = None
            
            if tipo_reporte == 'resena':
                reseña_obj = ResenasNegocios.objects.get(
                    pkid_resena=reseña_id,
                    fknegocio_resena=negocio,
                    estado_resena='activa'
                )
                
                if reseña_obj.fkusuario_resena == perfil_usuario:
                    return JsonResponse({
                        'success': False, 
                        'message': 'No puedes reportar tu propia reseña'
                    })
                
                reporte_existente = Reportes.objects.filter(
                    fknegocio_reportado=negocio,
                    fkresena_reporte=reseña_obj,
                    fkusuario_reporta=perfil_usuario,
                    tipo_reporte='resena'
                ).exists()
                
                if reporte_existente:
                    return JsonResponse({
                        'success': False, 
                        'message': 'Ya has reportado esta reseña anteriormente'
                    })
            
            else:
                if negocio.fkpropietario_neg == perfil_usuario:
                    return JsonResponse({
                        'success': False, 
                        'message': 'No puedes reportar tu propio negocio'
                    })
                
                reporte_existente = Reportes.objects.filter(
                    fknegocio_reportado=negocio,
                    fkusuario_reporta=perfil_usuario,
                    tipo_reporte='negocio'
                ).exists()
                
                if reporte_existente:
                    return JsonResponse({
                        'success': False, 
                        'message': 'Ya has reportado este negocio anteriormente'
                    })
            
            reporte = Reportes(
                fknegocio_reportado=negocio,
                fkresena_reporte=reseña_obj,
                fkusuario_reporta=perfil_usuario,
                tipo_reporte=tipo_reporte,
                asunto=asunto,
                motivo=motivo,
                descripcion=descripcion,
                estado_reporte='pendiente',
                leido=False
            )
            reporte.save()
            
            return JsonResponse({
                'success': True, 
                'message': 'Reporte enviado correctamente. Lo revisaremos pronto.'
            })
            
        except Negocios.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'El negocio no existe'
            })
        except ResenasNegocios.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'La reseña no existe'
            })
        except UsuarioPerfil.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'Complete su perfil para realizar esta acción'
            })
        except Exception:
            return JsonResponse({
                'success': False, 
                'message': 'Error al procesar el reporte'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@login_required
def obtener_opciones_reporte(request):
    tipo = request.GET.get('tipo')
    
    opciones = {
        'negocio': [
            {'value': 'informacion_falsa', 'text': 'Información falsa o engañosa'},
            {'value': 'contenido_inapropiado', 'text': 'Contenido inapropiado'},
            {'value': 'actividades_sospechosas', 'text': 'Actividades sospechosas'},
            {'value': 'violacion_derechos', 'text': 'Violación de derechos de autor'},
            {'value': 'mal_servicio', 'text': 'Mal servicio al cliente'},
            {'value': 'otro', 'text': 'Otro motivo'}
        ],
        'resena': [
            {'value': 'contenido_inapropiado', 'text': 'Contenido inapropiado u ofensivo'},
            {'value': 'lenguaje_ofensivo', 'text': 'Lenguaje ofensivo o discriminatorio'},
            {'value': 'informacion_falsa', 'text': 'Información falsa o engañosa'},
            {'value': 'spam', 'text': 'Spam o publicidad no deseada'},
            {'value': 'acoso', 'text': 'Acoso o bullying'},
            {'value': 'conflicto_interes', 'text': 'Conflicto de interés (empleado/familiar)'},
            {'value': 'otro', 'text': 'Otro motivo'}
        ]
    }
    
    return JsonResponse({'opciones': opciones.get(tipo, [])})

def descontar_stock_pedido(pedido, items_carrito=None):
    try:
        if items_carrito is None:
            items_carrito = CarritoItem.objects.filter(
                fkcarrito__fkusuario_carrito=pedido.fkusuario_pedido
            )
        
        hoy = timezone.now().date()
        
        for item in items_carrito:
            producto = item.fkproducto
            cantidad = item.cantidad
            variante_id = item.variante_id

            # Verificar si el producto/variante tiene promoción activa con stock específico
            with connection.cursor() as cursor:
                if variante_id:
                    cursor.execute("""
                        SELECT pkid_promo, stock_actual_oferta, stock_oferta, activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND variante_id = %s
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [producto.pkid_prod, variante_id, hoy, hoy])
                else:
                    cursor.execute("""
                        SELECT pkid_promo, stock_actual_oferta, stock_oferta, activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [producto.pkid_prod, hoy, hoy])
                
                promocion_data = cursor.fetchone()
            
            # Si hay promoción con stock de oferta, descontar de ahí primero
            if promocion_data and promocion_data[3]:
                promo_id, stock_actual_oferta, stock_oferta, activa_por_stock = promocion_data
                
                if stock_actual_oferta is not None and stock_actual_oferta > 0:
                    cantidad_a_descontar_oferta = min(cantidad, stock_actual_oferta)
                    cantidad_restante = cantidad - cantidad_a_descontar_oferta
                    
                    # Actualizar stock de la oferta
                    nuevo_stock_oferta = stock_actual_oferta - cantidad_a_descontar_oferta
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE promociones 
                            SET stock_actual_oferta = %s 
                            WHERE pkid_promo = %s
                        """, [nuevo_stock_oferta, promo_id])
                    
                    # Registrar movimiento de stock de oferta
                    try:
                        MovimientosStock.objects.create(
                            producto=producto,
                            negocio=producto.fknegocioasociado_prod,
                            tipo_movimiento='salida',
                            motivo='venta_oferta',
                            cantidad=cantidad_a_descontar_oferta,
                            stock_anterior=stock_actual_oferta,
                            stock_nuevo=nuevo_stock_oferta,
                            usuario=pedido.fkusuario_pedido,
                            pedido=pedido,
                            variante_id=variante_id
                        )
                    except Exception:
                        pass
                    
                    # Si todavía queda cantidad por descontar, descontar del stock general
                    if cantidad_restante > 0:
                        _descontar_stock_general(producto, cantidad_restante, pedido, variante_id)
                    
                    continue
                else:
                    pass
            
            # Si no hay promoción con stock de oferta, descontar del stock general
            _descontar_stock_general(producto, cantidad, pedido, variante_id)
        
        return True
        
    except Exception:
        return False

def _descontar_stock_general(producto, cantidad, pedido, variante_id=None):
    """Descontar del stock general del producto o variante"""
    try:
        if variante_id:
            # Descontar de variante
            variante = VariantesProducto.objects.get(
                id_variante=variante_id,
                producto=producto,
                estado_variante='activa'
            )
            
            stock_anterior = variante.stock_variante
            
            if stock_anterior >= cantidad:
                variante.stock_variante -= cantidad
                variante.save()
                
                try:
                    MovimientosStock.objects.create(
                        producto=producto,
                        negocio=producto.fknegocioasociado_prod,
                        tipo_movimiento='salida',
                        motivo='venta',
                        cantidad=cantidad,
                        stock_anterior=stock_anterior,
                        stock_nuevo=variante.stock_variante,
                        usuario=pedido.fkusuario_pedido,
                        pedido=pedido,
                        variante_id=variante_id
                    )
                except Exception:
                    pass
            else:
                # Si no hay suficiente stock, descontar lo que haya
                cantidad_real = stock_anterior
                variante.stock_variante = 0
                variante.save()
                
        else:
            # Descontar de producto base
            stock_anterior = producto.stock_prod or 0
            
            if stock_anterior >= cantidad:
                producto.stock_prod -= cantidad
                producto.save()
                
                try:
                    MovimientosStock.objects.create(
                        producto=producto,
                        negocio=producto.fknegocioasociado_prod,
                        tipo_movimiento='salida',
                        motivo='venta',
                        cantidad=cantidad,
                        stock_anterior=stock_anterior,
                        stock_nuevo=producto.stock_prod,
                        usuario=pedido.fkusuario_pedido,
                        pedido=pedido,
                        variante_id=None
                    )
                except Exception:
                    pass
            else:
                # Si no hay suficiente stock, descontar lo que haya
                cantidad_real = stock_anterior
                producto.stock_prod = 0
                producto.save()
                
    except Exception:
        pass
         
def _restaurar_producto_base(producto, cantidad):
    try:
        stock_anterior = producto.stock_prod or 0
        producto.stock_prod += cantidad
        producto.save()
        
    except Exception:
        pass
        
def validar_stock_pedido(pedido):
    try:
        detalles_pedido = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
        hoy = timezone.now().date()
        
        for detalle in detalles_pedido:
            producto = detalle.fkproducto_detalle
            cantidad = detalle.cantidad_detalle
            
            carrito_item = CarritoItem.objects.filter(
                fkproducto=producto,
                fkcarrito__fkusuario_carrito=pedido.fkusuario_pedido,
                variante_id__isnull=False
            ).first()
            
            variante_id = carrito_item.variante_id if carrito_item else None
            
            # Verificar stock considerando promociones con stock específico
            with connection.cursor() as cursor:
                if variante_id:
                    cursor.execute("""
                        SELECT stock_actual_oferta, activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND variante_id = %s
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [producto.pkid_prod, variante_id, hoy, hoy])
                else:
                    cursor.execute("""
                        SELECT stock_actual_oferta, activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [producto.pkid_prod, hoy, hoy])
                
                promocion_data = cursor.fetchone()
            
            stock_disponible = 0
            
            if promocion_data and promocion_data[1]:
                stock_oferta = promocion_data[0] or 0
                # Sumar stock de oferta + stock general
                if variante_id:
                    try:
                        variante = VariantesProducto.objects.get(
                            id_variante=variante_id,
                            producto=producto,
                            estado_variante='activa'
                        )
                        stock_disponible = stock_oferta + (variante.stock_variante or 0)
                    except VariantesProducto.DoesNotExist:
                        stock_disponible = stock_oferta
                else:
                    stock_disponible = stock_oferta + (producto.stock_prod or 0)
            else:
                # Solo stock general
                if variante_id:
                    try:
                        variante = VariantesProducto.objects.get(
                            id_variante=variante_id,
                            producto=producto,
                            estado_variante='activa'
                        )
                        stock_disponible = variante.stock_variante or 0
                    except VariantesProducto.DoesNotExist:
                        stock_disponible = producto.stock_prod or 0
                else:
                    stock_disponible = producto.stock_prod or 0
            
            if stock_disponible < cantidad:
                nombre_producto = producto.nom_prod
                if variante_id:
                    try:
                        variante = VariantesProducto.objects.get(id_variante=variante_id)
                        nombre_producto = f"{producto.nom_prod} - {variante.nombre_variante}"
                    except VariantesProducto.DoesNotExist:
                        pass
                
                return False, f"Stock insuficiente para {nombre_producto}. Disponible: {stock_disponible}, Solicitado: {cantidad}"
        
        return True, "Stock válido para todos los productos"
        
    except Exception as e:
        return False, f"Error validando stock: {str(e)}"
    
@login_required(login_url='/auth/login/')
@require_POST
def agregar_al_carrito(request):
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        cantidad = int(data.get('cantidad', 1))
        variante_id = data.get('variante_id', None)
        
        if not producto_id:
            return JsonResponse({'success': False, 'message': 'ID de producto requerido'}, status=400)
        
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        producto = Productos.objects.get(pkid_prod=producto_id)
        
        if producto.estado_prod != 'disponible':
            return JsonResponse({'success': False, 'message': 'Producto no disponible'}, status=400)
        
        precio_base = float(producto.precio_prod)
        precio_final = precio_base
        variante_nombre = None
        variante_id_int = None
        hoy = timezone.now().date()
        
        # VARIABLES PARA CONTROL DE OFERTA
        stock_oferta_disponible = 0
        stock_general_disponible = 0
        limite_oferta = None
        tiene_oferta_activa = False
        descuento_porcentaje = 0
        promo_id = None
        
        # VERIFICAR OFERTAS ACTIVAS PRIMERO
        with connection.cursor() as cursor:
            if variante_id and variante_id != 'base':
                try:
                    variante_id_int = int(variante_id)
                    cursor.execute("""
                        SELECT p.pkid_promo, p.porcentaje_descuento, p.stock_actual_oferta, p.stock_oferta, p.activa_por_stock
                        FROM promociones p
                        WHERE p.fkproducto_id = %s 
                        AND p.variante_id = %s
                        AND p.estado_promo = 'activa'
                        AND p.fecha_inicio <= %s 
                        AND p.fecha_fin >= %s
                        LIMIT 1
                    """, [producto.pkid_prod, variante_id_int, hoy, hoy])
                except ValueError:
                    return JsonResponse({'success': False, 'message': 'ID de variante inválido'}, status=400)
            else:
                cursor.execute("""
                    SELECT p.pkid_promo, p.porcentaje_descuento, p.stock_actual_oferta, p.stock_oferta, p.activa_por_stock
                    FROM promociones p
                    WHERE p.fkproducto_id = %s 
                    AND p.estado_promo = 'activa'
                    AND p.fecha_inicio <= %s 
                    AND p.fecha_fin >= %s
                    LIMIT 1
                """, [producto.pkid_prod, hoy, hoy])
            
            promocion_data = cursor.fetchone()
        
        if promocion_data:
            promo_id = promocion_data[0]
            descuento_porcentaje = float(promocion_data[1]) if promocion_data[1] else 0
            stock_oferta_disponible = promocion_data[2] if promocion_data[2] is not None else 0
            limite_oferta = promocion_data[3] if promocion_data[3] is not None else 0
            tiene_oferta_activa = promocion_data[4] if promocion_data[4] is not None else False
            
            # VERIFICACIÓN CRÍTICA DEL LÍMITE
            if tiene_oferta_activa and limite_oferta > 0:
                if cantidad > stock_oferta_disponible:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Límite de oferta alcanzado. Solo {stock_oferta_disponible} unidades disponibles en oferta especial'
                    }, status=400)

        if variante_id and variante_id != 'base':
            try:
                variante_id_int = int(variante_id)
                variante = VariantesProducto.objects.get(
                    id_variante=variante_id_int, 
                    producto=producto,
                    estado_variante='activa'
                )
                
                # CALCULAR STOCK TOTAL DISPONIBLE
                if tiene_oferta_activa:
                    # Si hay oferta con stock específico
                    stock_general_disponible = variante.stock_variante or 0
                    stock_total_disponible = stock_oferta_disponible + stock_general_disponible
                    
                    # Validación específica para ofertas con límite
                    if tiene_oferta_activa and limite_oferta > 0:
                        if cantidad > stock_oferta_disponible:
                            return JsonResponse({
                                'success': False, 
                                'message': f'Solo {stock_oferta_disponible} unidades disponibles en oferta especial para esta variante'
                            }, status=400)
                    
                    if stock_total_disponible < cantidad:
                        mensaje_error = f'Stock insuficiente para la variante. Solo quedan {stock_total_disponible} unidades'
                        if tiene_oferta_activa:
                            mensaje_error += f' ({stock_oferta_disponible} en oferta especial)'
                        return JsonResponse({
                            'success': False, 
                            'message': mensaje_error
                        }, status=400)
                else:
                    # Solo stock general de variante
                    stock_total_disponible = variante.stock_variante or 0
                    
                    if stock_total_disponible < cantidad:
                        return JsonResponse({
                            'success': False, 
                            'message': f'Stock insuficiente. Solo quedan {stock_total_disponible} unidades'
                        }, status=400)
                
                if variante.precio_adicional and float(variante.precio_adicional) > 0:
                    precio_base += float(variante.precio_adicional)
                    precio_final = precio_base
                    
                variante_nombre = variante.nombre_variante
                
            except VariantesProducto.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Variante no encontrada'}, status=404)
        else:
            # PRODUCTO BASE - CALCULAR STOCK TOTAL
            stock_general_disponible = producto.stock_prod or 0
            
            if tiene_oferta_activa:
                stock_total_disponible = stock_oferta_disponible + stock_general_disponible
                
                # Validación específica para ofertas con límite
                if tiene_oferta_activa and limite_oferta > 0:
                    if cantidad > stock_oferta_disponible:
                        return JsonResponse({
                            'success': False, 
                            'message': f'Solo {stock_oferta_disponible} unidades disponibles en oferta especial para este producto'
                        }, status=400)
                
                if stock_total_disponible < cantidad:
                    mensaje_error = f'Stock insuficiente. Solo quedan {stock_total_disponible} unidades'
                    if tiene_oferta_activa:
                        mensaje_error += f' ({stock_oferta_disponible} en oferta especial)'
                    return JsonResponse({
                        'success': False, 
                        'message': mensaje_error
                    }, status=400)
            else:
                stock_total_disponible = stock_general_disponible
                
                if stock_total_disponible < cantidad:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Stock insuficiente. Solo quedan {stock_total_disponible} unidades'
                    }, status=400)
        
        precio_original = precio_base
        
        # APLICAR DESCUENTO SI HAY OFERTA
        if descuento_porcentaje > 0:
            precio_original = precio_final
            precio_final = precio_final * (1 - (descuento_porcentaje / 100))
        
        # AGREGAR AL CARRITO
        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
        
        item_existente = None
        
        if variante_id_int:
            item_existente = CarritoItem.objects.filter(
                fkcarrito=carrito,
                fkproducto=producto,
                variante_id=variante_id_int
            ).first()
        else:
            item_existente = CarritoItem.objects.filter(
                fkcarrito=carrito,
                fkproducto=producto,
                variante_id__isnull=True
            ).first()
        
        if item_existente:
            # VERIFICAR STOCK PARA LA NUEVA CANTIDAD TOTAL
            nueva_cantidad = item_existente.cantidad + cantidad
            
            # Recalcular stock disponible considerando ofertas
            stock_total_actual = 0
            stock_oferta_actual = 0
            
            if variante_id_int:
                # Recalcular stock disponible para la variante
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT COALESCE(stock_actual_oferta, 0) as stock_oferta, COALESCE(stock_oferta, 0) as limite_oferta, activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND variante_id = %s
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [producto.pkid_prod, variante_id_int, hoy, hoy])
                    
                    promocion_data_actual = cursor.fetchone()
                
                if promocion_data_actual and promocion_data_actual[2]:
                    stock_oferta_actual = promocion_data_actual[0] or 0
                    limite_oferta_actual = promocion_data_actual[1] or 0
                    stock_general_actual = variante.stock_variante or 0
                    
                    stock_total_actual = stock_oferta_actual + stock_general_actual
                    
                    # Validación específica para ofertas con límite
                    if promocion_data_actual[2] and limite_oferta_actual > 0:
                        if nueva_cantidad > stock_oferta_actual:
                            return JsonResponse({
                                'success': False,
                                'message': f'Solo puedes agregar {stock_oferta_actual - item_existente.cantidad} unidades más (límite de oferta)'
                            }, status=400)
                else:
                    stock_total_actual = variante.stock_variante or 0
            else:
                # Recalcular stock disponible para producto base
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT COALESCE(stock_actual_oferta, 0) as stock_oferta, COALESCE(stock_oferta, 0) as limite_oferta, activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [producto.pkid_prod, hoy, hoy])
                    
                    promocion_data_actual = cursor.fetchone()
                
                if promocion_data_actual and promocion_data_actual[2]:
                    stock_oferta_actual = promocion_data_actual[0] or 0
                    limite_oferta_actual = promocion_data_actual[1] or 0
                    stock_general_actual = producto.stock_prod or 0
                    
                    stock_total_actual = stock_oferta_actual + stock_general_actual
                    
                    # Validación específica para ofertas con límite
                    if promocion_data_actual[2] and limite_oferta_actual > 0:
                        if nueva_cantidad > stock_oferta_actual:
                            return JsonResponse({
                                'success': False,
                                'message': f'Solo puedes agregar {stock_oferta_actual - item_existente.cantidad} unidades más (límite de oferta)'
                            }, status=400)
                else:
                    stock_total_actual = producto.stock_prod or 0
            
            if stock_total_actual < nueva_cantidad:
                unidades_disponibles = stock_total_actual - item_existente.cantidad
                mensaje_error = f'Stock insuficiente. Solo puedes agregar {unidades_disponibles} unidades más'
                if promocion_data_actual and promocion_data_actual[2] and stock_oferta_actual > 0:
                    mensaje_error += f' ({stock_oferta_actual} en oferta especial)'
                return JsonResponse({
                    'success': False,
                    'message': mensaje_error
                }, status=400)
            
            item_existente.cantidad = nueva_cantidad
            item_existente.precio_unitario = precio_final
            item_existente.save()
            
            mensaje = 'Cantidad actualizada en el carrito'
            
        else:
            nuevo_item = CarritoItem.objects.create(
                fkcarrito=carrito,
                fkproducto=producto,
                fknegocio=producto.fknegocioasociado_prod,
                cantidad=cantidad,
                precio_unitario=precio_final,
                variante_seleccionada=variante_nombre,
                variante_id=variante_id_int
            )
            mensaje = 'Producto agregado al carrito exitosamente'
        
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        nombre_producto_completo = producto.nom_prod
        if variante_nombre:
            nombre_producto_completo = f"{producto.nom_prod} - {variante_nombre}"
        
        ahorro_total = (precio_original - precio_final) * cantidad
        
        response_data = {
            'success': True,
            'message': mensaje,
            'carrito_count': carrito_count,
            'producto_nombre': nombre_producto_completo,
            'precio_unitario': round(precio_final, 2),
            'precio_original': round(precio_original, 2),
            'cantidad': cantidad,
            'subtotal': round(precio_final * cantidad, 2),
            'tiene_descuento': precio_final < precio_original,
            'descuento_porcentaje': descuento_porcentaje,
            'ahorro_total': round(ahorro_total, 2),
            'item_actualizado': item_existente is not None,
            'es_variante': variante_id_int is not None,
            'tiene_oferta_activa': tiene_oferta_activa,
            'stock_oferta_disponible': stock_oferta_disponible,
            'limite_oferta': limite_oferta,
            'stock_total_disponible': stock_total_disponible,
        }
        
        if variante_nombre:
            response_data['variante_nombre'] = variante_nombre
        
        return JsonResponse(response_data)
        
    except Productos.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Producto no encontrado'}, status=404)
    except UsuarioPerfil.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Perfil de usuario no encontrado'}, status=404)
    except Exception:
        return JsonResponse({
            'success': False, 
            'message': 'Error interno del servidor'
        }, status=500)
              
@login_required(login_url='/auth/login/')
@require_POST
def actualizar_cantidad_carrito(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        cambio = data.get('cambio', 0)
        
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
        item = CarritoItem.objects.get(pkid_item=item_id, fkcarrito=carrito)
        
        nueva_cantidad = item.cantidad + cambio
        
        if nueva_cantidad <= 0:
            item.delete()
        else:
            stock_disponible = 0
            stock_oferta = 0
            limite_oferta = 0
            tiene_oferta_activa = False
            hoy = timezone.now().date()
            
            # VERIFICAR SI EL PRODUCTO TIENE OFERTA ACTIVA
            with connection.cursor() as cursor:
                if item.variante_id:
                    cursor.execute("""
                        SELECT COALESCE(stock_actual_oferta, 0), COALESCE(stock_oferta, 0), activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND variante_id = %s
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [item.fkproducto.pkid_prod, item.variante_id, hoy, hoy])
                else:
                    cursor.execute("""
                        SELECT COALESCE(stock_actual_oferta, 0), COALESCE(stock_oferta, 0), activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [item.fkproducto.pkid_prod, hoy, hoy])
                
                promocion_data = cursor.fetchone()
            
            if promocion_data:
                stock_oferta = promocion_data[0] or 0
                limite_oferta = promocion_data[1] or 0
                tiene_oferta_activa = promocion_data[2]
            
            if item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(
                        id_variante=item.variante_id,
                        producto=item.fkproducto,
                        estado_variante='activa'
                    )
                    
                    if tiene_oferta_activa:
                        stock_general = variante.stock_variante or 0
                        # Calcular stock real considerando límites de oferta
                        stock_oferta_real = min(stock_oferta, limite_oferta) if limite_oferta > 0 else stock_oferta
                        stock_disponible = stock_oferta_real + stock_general
                        
                        # VALIDACIÓN CRÍTICA: No permitir exceder el límite de oferta
                        if tiene_oferta_activa and limite_oferta > 0:
                            if nueva_cantidad > stock_oferta_real:
                                return JsonResponse({
                                    'success': False,
                                    'message': f'Límite de oferta alcanzado. Máximo {stock_oferta_real} unidades en oferta especial'
                                })
                    else:
                        stock_disponible = variante.stock_variante or 0
                        
                except VariantesProducto.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'La variante seleccionada ya no está disponible'
                    })
            else:
                if tiene_oferta_activa:
                    stock_general = item.fkproducto.stock_prod or 0
                    # Calcular stock real considerando límites de oferta
                    stock_oferta_real = min(stock_oferta, limite_oferta) if limite_oferta > 0 else stock_oferta
                    stock_disponible = stock_oferta_real + stock_general
                    
                    # VALIDACIÓN CRÍTICA: No permitir exceder el límite de oferta
                    if tiene_oferta_activa and limite_oferta > 0:
                        if nueva_cantidad > stock_oferta_real:
                            return JsonResponse({
                                'success': False,
                                'message': f'Límite de oferta alcanzado. Máximo {stock_oferta_real} unidades en oferta especial'
                            })
                else:
                    stock_disponible = item.fkproducto.stock_prod or 0
            
            if stock_disponible < nueva_cantidad:
                mensaje_error = f'Stock insuficiente. Solo quedan {stock_disponible} unidades'
                if tiene_oferta_activa and stock_oferta > 0:
                    stock_oferta_real = min(stock_oferta, limite_oferta) if limite_oferta > 0 else stock_oferta
                    mensaje_error += f' ({stock_oferta_real} en oferta especial)'
                return JsonResponse({
                    'success': False,
                    'message': mensaje_error
                })
            
            item.cantidad = nueva_cantidad
            item.save()
        
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        return JsonResponse({
            'success': True,
            'carrito_count': carrito_count
        })
        
    except Exception:
        return JsonResponse({'success': False, 'message': 'Error interno del servidor'})
    
@login_required(login_url='/auth/login/')
@require_POST
def eliminar_item_carrito(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
        item = CarritoItem.objects.get(pkid_item=item_id, fkcarrito=carrito)
        item.delete()
        
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        return JsonResponse({
            'success': True,
            'carrito_count': carrito_count
        })
        
    except Exception:
        return JsonResponse({'success': False, 'message': 'Error interno del servidor'})
          
@login_required(login_url='/auth/login/')
def ver_carrito(request):
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            items_carrito = CarritoItem.objects.filter(fkcarrito=carrito).select_related(
                'fkproducto', 'fknegocio'
            )
        except Carrito.DoesNotExist:
            items_carrito = []
            carrito = None
        
        total_carrito = 0
        ahorro_total = 0
        items_detallados = []
        hoy = timezone.now().date()

        for item in items_carrito:
            imagen_producto = item.fkproducto.img_prod.url if item.fkproducto.img_prod else None
            
            precio_base = float(item.fkproducto.precio_prod)
            precio_original = precio_base
            
            if item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(id_variante=item.variante_id)
                    if variante.imagen_variante:
                        imagen_producto = variante.imagen_variante.url
                    if variante.precio_adicional:
                        precio_original += float(variante.precio_adicional)
                except VariantesProducto.DoesNotExist:
                    pass
            
            precio_actual = float(item.precio_unitario)
            subtotal = precio_actual * item.cantidad
            
            tiene_oferta = precio_actual < precio_original
            ahorro_item = (precio_original - precio_actual) * item.cantidad if tiene_oferta else 0
            descuento_porcentaje = ((precio_original - precio_actual) / precio_original * 100) if precio_original > 0 else 0
            
            items_detallados.append({
                'item': item,
                'imagen': imagen_producto,
                'subtotal': subtotal,
                'tiene_oferta': tiene_oferta,
                'precio_original': precio_original,
                'precio_actual': precio_actual,
                'descuento_porcentaje': descuento_porcentaje,
                'ahorro': ahorro_item
            })
            
            total_carrito += subtotal
            if tiene_oferta:
                ahorro_total += ahorro_item
        
        context = {
            'items_carrito': items_detallados,
            'total_carrito': total_carrito,
            'ahorro_total': ahorro_total,
            'carrito_count': len(items_carrito),
            'carrito_vacio': len(items_carrito) == 0
        }
        
        return render(request, 'Cliente/carrito.html', context)
        
    except Exception:
        return render(request, 'Cliente/carrito.html', {
            'items_carrito': [],
            'total_carrito': 0,
            'ahorro_total': 0,
            'carrito_count': 0,
            'carrito_vacio': True
        })
        
@login_required(login_url='/auth/login/')
def carrito_data(request):
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
        items = CarritoItem.objects.filter(fkcarrito=carrito).select_related('fkproducto', 'fknegocio')
        
        carrito_items = []
        subtotal = 0
        ahorro_total = 0
        hoy = timezone.now().date()

        for item in items:
            nombre_completo = item.fkproducto.nom_prod
            if item.variante_seleccionada:
                nombre_completo = f"{item.fkproducto.nom_prod} - {item.variante_seleccionada}"
            
            precio_base = float(item.fkproducto.precio_prod)
            
            precio_original = precio_base
            stock_disponible = item.fkproducto.stock_prod or 0
            
            imagen_producto = item.fkproducto.img_prod.url if item.fkproducto.img_prod else None
            
            if item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(id_variante=item.variante_id)
                    if variante.precio_adicional:
                        precio_original += float(variante.precio_adicional)
                        precio_base += float(variante.precio_adicional)
                    stock_disponible = variante.stock_variante or 0
                    
                    if variante.imagen_variante:
                        imagen_producto = variante.imagen_variante.url
                        
                except VariantesProducto.DoesNotExist:
                    pass
            
            precio_actual = float(item.precio_unitario)
            
            tiene_oferta = False
            ahorro_item = 0
            
            with connection.cursor() as cursor:
                if item.variante_id:
                    cursor.execute("""
                        SELECT porcentaje_descuento 
                        FROM promociones 
                        WHERE (fkproducto_id = %s AND variante_id = %s)
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [item.fkproducto.pkid_prod, item.variante_id, hoy, hoy])
                else:
                    cursor.execute("""
                        SELECT porcentaje_descuento 
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [item.fkproducto.pkid_prod, hoy, hoy])
                
                result = cursor.fetchone()
                if result and result[0] is not None:
                    try:
                        descuento_porcentaje = float(result[0])
                        if descuento_porcentaje > 0:
                            precio_con_descuento = precio_original * (1 - (descuento_porcentaje / 100))
                            tiene_oferta = precio_actual <= precio_con_descuento
                            ahorro_item = (precio_original - precio_actual) * item.cantidad
                    except (ValueError, TypeError):
                        pass
            
            if not tiene_oferta and precio_actual < precio_original:
                tiene_oferta = True
                ahorro_item = (precio_original - precio_actual) * item.cantidad
            
            carrito_items.append({
                'id': item.pkid_item,
                'nombre': nombre_completo,
                'negocio': item.fknegocio.nom_neg,
                'cantidad': item.cantidad,
                'precio_unitario': precio_actual,
                'precio_original': precio_original,
                'tiene_oferta': tiene_oferta,
                'imagen': imagen_producto,
                'variante': item.variante_seleccionada,
                'es_variante': bool(item.variante_id),
                'stock_disponible': stock_disponible,
                'ahorro_item': ahorro_item,
            })
            
            subtotal += precio_actual * item.cantidad
            if tiene_oferta:
                ahorro_total += ahorro_item
        
        response_data = {
            'success': True,
            'items': carrito_items,
            'totales': {
                'subtotal': subtotal,
                'ahorro_total': ahorro_total,
                'total': subtotal
            },
            'carrito_count': len(carrito_items),
        }
        
        return JsonResponse(response_data)
        
    except Exception:
        return JsonResponse({'success': False, 'items': [], 'totales': {}})
    
@login_required(login_url='/auth/login/')
@require_POST
@csrf_exempt
def procesar_pedido(request):
    try:
        data = json.loads(request.body)

        auth_user = request.user
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)

        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            items_carrito = CarritoItem.objects.filter(fkcarrito=carrito)
                
        except Carrito.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No hay items en el carrito'}, status=400)

        if not items_carrito.exists():
            return JsonResponse({'success': False, 'message': 'El carrito está vacío'}, status=400)

        total_pedido = 0
        negocios_involucrados = {}
        items_detallados = []

        for item_carrito in items_carrito:
            if item_carrito.variante_id:
                try:
                    variante = VariantesProducto.objects.get(
                        id_variante=item_carrito.variante_id,
                        producto=item_carrito.fkproducto,
                        estado_variante='activa'
                    )
                    if (variante.stock_variante or 0) < item_carrito.cantidad:
                        return JsonResponse({
                            'success': False, 
                            'message': f'Stock insuficiente para {item_carrito.fkproducto.nom_prod} - {variante.nombre_variante}. Solo quedan {variante.stock_variante} unidades'
                        }, status=400)
                except VariantesProducto.DoesNotExist:
                    return JsonResponse({
                        'success': False, 
                        'message': f'La variante de {item_carrito.fkproducto.nom_prod} ya no está disponible'
                    }, status=400)
            else:
                if (item_carrito.fkproducto.stock_prod or 0) < item_carrito.cantidad:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Stock insuficiente para {item_carrito.fkproducto.nom_prod}. Solo quedan {item_carrito.fkproducto.stock_prod} unidades'
                    }, status=400)

        for item_carrito in items_carrito:
            monto_item = float(item_carrito.precio_unitario) * item_carrito.cantidad
            total_pedido += monto_item
            negocio = item_carrito.fknegocio
            
            if negocio in negocios_involucrados:
                negocios_involucrados[negocio] += monto_item
            else:
                negocios_involucrados[negocio] = monto_item
            
            items_detallados.append({
                'producto': item_carrito.fkproducto,
                'cantidad': item_carrito.cantidad,
                'precio_unitario': item_carrito.precio_unitario,
                'subtotal': monto_item,
                'negocio': negocio,
                'variante_seleccionada': item_carrito.variante_seleccionada,
                'variante_id': item_carrito.variante_id,
                'carrito_item_id': item_carrito.pkid_item
            })

        negocio_principal = None
        mayor_monto = 0

        for negocio, monto in negocios_involucrados.items():
            if monto > mayor_monto:
                mayor_monto = monto
                negocio_principal = negocio

        pedido = Pedidos.objects.create(
            fkusuario_pedido=perfil_cliente,
            fknegocio_pedido=negocio_principal,
            estado_pedido='pendiente',
            total_pedido=total_pedido,
            metodo_pago=data.get('metodo_pago'),
            metodo_pago_texto=data.get('metodo_pago_texto'),
            banco=data.get('banco', None),
            fecha_pedido=timezone.now(),
            fecha_actualizacion=timezone.now()
        )

        detalles_creados = []
        for item_detallado in items_detallados:
            detalle = DetallesPedido.objects.create(
                fkpedido_detalle=pedido,
                fkproducto_detalle=item_detallado['producto'],
                cantidad_detalle=item_detallado['cantidad'],
                precio_unitario=item_detallado['precio_unitario']
            )
            detalles_creados.append(detalle)
        
        stock_descontado = descontar_stock_pedido(pedido, items_carrito)

        for negocio, monto in negocios_involucrados.items():
            metodo_pago = data.get('metodo_pago')
            if metodo_pago in ['transferencia', 'nequi', 'daviplata', 'pse']:
                estado_pago = 'pagado'
            elif metodo_pago == 'contra_entrega':
                estado_pago = 'por_cobrar'
            elif metodo_pago == 'tarjeta':
                estado_pago = 'completado'
            else:
                estado_pago = 'pendiente'

            PagosNegocios.objects.create(
                fkpedido=pedido,
                fknegocio=negocio,
                monto=monto,
                fecha_pago=timezone.now(),
                estado_pago=estado_pago,
                metodo_pago=metodo_pago
            )

        # =====================================================================
        # CREAR NOTIFICACIONES - AGREGADO AQUÍ
        # =====================================================================
        
        # 1. Notificación para el CLIENTE
        Notificacion.objects.create(
            usuario=auth_user,
            tipo='pedido',
            titulo='✅ Pedido Confirmado',
            mensaje=f'Tu pedido #{pedido.pkid_pedido} ha sido procesado exitosamente. Total: ${total_pedido:,.0f}',
            url=f'/pedidos/{pedido.pkid_pedido}/'
        )
        
        # 2. Notificación para el NEGOCIO PRINCIPAL
        if negocio_principal and negocio_principal.fkpropietario_neg and negocio_principal.fkpropietario_neg.fkuser:
            Notificacion.objects.create(
                usuario=negocio_principal.fkpropietario_neg.fkuser,
                tipo='pedido',
                titulo='🛒 Nuevo Pedido Recibido',
                mensaje=f'Tienes un nuevo pedido #{pedido.pkid_pedido} de {auth_user.first_name or auth_user.username}. Total: ${mayor_monto:,.0f}',
                url=f'/negocio/pedidos/{pedido.pkid_pedido}/'
            )
        
        # 3. Notificaciones para otros negocios involucrados
        for negocio, monto in negocios_involucrados.items():
            if negocio != negocio_principal and negocio.fkpropietario_neg and negocio.fkpropietario_neg.fkuser:
                Notificacion.objects.create(
                    usuario=negocio.fkpropietario_neg.fkuser,
                    tipo='pedido',
                    titulo='🛒 Pedido Multi-Negocio',
                    mensaje=f'Tienes productos en el pedido #{pedido.pkid_pedido}. Tu ganancia: ${monto:,.0f}',
                    url=f'/negocio/pedidos/{pedido.pkid_pedido}/'
                )
        
        # =====================================================================

        items_carrito.delete()

        try:
            email_cliente = auth_user.email
            if email_cliente:
                enviar_comprobante_pedido(email_cliente, pedido, items_detallados, negocios_involucrados)
        except Exception:
            pass

        fecha_colombia = timezone.localtime(pedido.fecha_pedido)
        fecha_formateada = fecha_colombia.strftime("%d/%m/%Y %I:%M %p").lower()

        response_data = {
            'success': True,
            'message': 'Pedido procesado exitosamente. Stock descontado correctamente.',
            'numero_pedido': pedido.pkid_pedido,
            'total': total_pedido,
            'metodo_pago': data.get('metodo_pago_texto'),
            'fecha': fecha_formateada,
            'estado_pedido': pedido.estado_pedido,
            'pagos_creados': len(negocios_involucrados),
            'negocio_principal': negocio_principal.nom_neg,
            'correo_enviado': bool(email_cliente),
            'stock_validado': True,
            'stock_descontado': stock_descontado,
            'notificaciones_creadas': 1 + len(negocios_involucrados),
        }

        return JsonResponse(response_data)

    except Exception:
        # Notificación de error si ocurre
        try:
            Notificacion.objects.create(
                usuario=request.user,
                tipo='alerta',
                titulo='❌ Error en Pedido',
                mensaje=f'Ocurrió un error al procesar tu pedido. Por favor intenta nuevamente.',
                url='/carrito/'
            )
        except:
            pass
            
        return JsonResponse({'success': False, 'message': 'Error interno del servidor al procesar el pedido'}, status=500)

def crear_notificacion_estado_pedido(pedido, nuevo_estado):
    """Crear notificación cuando cambia el estado de un pedido"""
    estados_mensajes = {
        'confirmado': f'✅ Tu pedido #{pedido.pkid_pedido} ha sido confirmado por el negocio',
        'preparando': f'👨‍🍳 Tu pedido #{pedido.pkid_pedido} está en preparación',
        'en_camino': f'🚚 Tu pedido #{pedido.pkid_pedido} está en camino',
        'entregado': f'🎉 Pedido #{pedido.pkid_pedido} entregado exitosamente',
        'cancelado': f'❌ Pedido #{pedido.pkid_pedido} ha sido cancelado',
    }
    
    mensaje = estados_mensajes.get(nuevo_estado, f'Estado actualizado del pedido #{pedido.pkid_pedido}')
    
    # Notificación para el cliente
    Notificacion.objects.create(
        usuario=pedido.fkusuario_pedido.fkuser,
        tipo='pedido',
        titulo=f'Actualización de Pedido #{pedido.pkid_pedido}',
        mensaje=mensaje,
        url=f'/pedidos/{pedido.pkid_pedido}/'
    )
    
    # Notificación para el negocio (si no es cancelado)
    if nuevo_estado != 'cancelado' and pedido.fknegocio_pedido.fkpropietario_neg:
        Notificacion.objects.create(
            usuario=pedido.fknegocio_pedido.fkpropietario_neg.fkuser,
            tipo='pedido', 
            titulo=f'Estado Actualizado - Pedido #{pedido.pkid_pedido}',
            mensaje=f'Has actualizado el pedido #{pedido.pkid_pedido} a: {nuevo_estado}',
            url=f'/negocio/pedidos/{pedido.pkid_pedido}/'
        )
        
def enviar_comprobante_pedido(email_cliente, pedido, items_detallados, negocios_involucrados):
    try:
        fecha_colombia = timezone.localtime(pedido.fecha_pedido)
        
        meses_es = [
            'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]
        
        dias_es = [
            'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'
        ]
        
        fecha_formateada = fecha_colombia.strftime(f"%d de {meses_es[fecha_colombia.month-1]} de %Y")
        hora_formateada = fecha_colombia.strftime("%I:%M %p").lower()
        
        dia_semana = dias_es[fecha_colombia.weekday()]
        fecha_completa = f"{dia_semana}, {fecha_formateada} a las {hora_formateada}"
        
        context = {
            'pedido': pedido,
            'items': items_detallados,
            'negocios': negocios_involucrados,
            'cliente': pedido.fkusuario_pedido,
            'fecha_pedido': fecha_completa,
            'fecha_simple': fecha_formateada,
            'hora_pedido': hora_formateada,
            'total_pedido': pedido.total_pedido,
            'metodo_pago': pedido.metodo_pago_texto,
            'numero_pedido': f"VECY-{pedido.pkid_pedido:06d}",
        }
        
        html_content = render_to_string('emails/comprobante_pedido.html', context)
        text_content = strip_tags(html_content)
        
        subject = f'✅ Comprobante de Pedido VECY - #{context["numero_pedido"]}'
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=os.getenv('DEFAULT_FROM_EMAIL', 'noreply@vecy.com'),
            to=[email_cliente],
            reply_to=['soporte@vecy.com']
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send()
        
    except Exception:
        pass

@login_required(login_url='/auth/login/')
def guardar_resena(request):
    if request.method == 'POST':
        try:
            estrellas = int(request.POST.get('estrellas', 5))
            comentario = request.POST.get('comentario', '').strip()
            negocio_id = request.POST.get('fknegocio_resena')
            es_vista_logeada = request.POST.get('es_vista_logeada', False)

            if not negocio_id:
                messages.error(request, 'ID de negocio requerido')
                return redirect('cliente_dashboard')
            
            if estrellas < 1 or estrellas > 5:
                messages.error(request, 'La calificación debe estar entre 1 y 5 estrellas')
                if es_vista_logeada:
                    return redirect('detalle_negocio_logeado', id=negocio_id)
                else:
                    return redirect('detalle_negocio', id=negocio_id)

            perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
            
            negocio = get_object_or_404(Negocios, pkid_neg=negocio_id)

            resena = ResenasNegocios(
                fkusuario_resena=perfil_cliente,
                fknegocio_resena=negocio,
                estrellas=estrellas,
                comentario=comentario,
                fecha_resena=timezone.now(),
                estado_resena='activa'
            )
            resena.save()

            messages.success(request, '¡Reseña guardada exitosamente!')
            
            if es_vista_logeada:
                return redirect('detalle_negocio_logeado', id=negocio_id)
            else:
                return redirect('detalle_negocio', id=negocio_id)

        except Negocios.DoesNotExist:
            messages.error(request, 'Negocio no encontrado')
            return redirect('cliente_dashboard')
        except UsuarioPerfil.DoesNotExist:
            messages.error(request, 'Perfil de usuario no encontrado')
            return redirect('cliente_dashboard')
        except Exception:
            messages.error(request, 'Error al guardar la reseña')
            if negocio_id:
                if es_vista_logeada:
                    return redirect('detalle_negocio_logeado', id=negocio_id)
                else:
                    return redirect('detalle_negocio', id=negocio_id)
            return redirect('cliente_dashboard')
    
    return redirect('cliente_dashboard')

@login_required(login_url='/auth/login/')
def productos_filtrados_logeado(request):
    
    filtro_tipo = request.GET.get('filtro', '')
    categoria_id = request.GET.get('categoria', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    ordenar = request.GET.get('ordenar', '')
    buscar = request.GET.get('buscar', '')
    
    productos = Productos.objects.filter(estado_prod='disponible')
    
    if filtro_tipo == 'ofertas':
        from django.db import connection
        from datetime import date
        
        hoy = date.today()
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT fkproducto_id 
                FROM promociones 
                WHERE estado_promo = 'activa' 
                AND fecha_inicio <= %s 
                AND fecha_fin >= %s
            """, [hoy, hoy])
            
            resultados = cursor.fetchall()
            productos_con_ofertas_ids = [row[0] for row in resultados if row[0] is not None]
        
        if productos_con_ofertas_ids:
            productos = productos.filter(pkid_prod__in=productos_con_ofertas_ids)
        else:
            productos = productos.none()
        
        titulo_filtro = "Ofertas Especiales"
    
    elif filtro_tipo == 'destacados':
        productos = productos.filter(stock_prod__gt=0)
        titulo_filtro = "Productos Destacados"
    
    elif filtro_tipo == 'economicos':
        productos = productos.order_by('precio_prod')
        titulo_filtro = "Productos Baratos"
    
    elif filtro_tipo == 'nuevos':
        productos = productos.order_by('-fecha_creacion')
        titulo_filtro = "Nuevos Productos"
    
    elif filtro_tipo == 'mas-vendidos':
        productos = productos.filter(stock_prod__gt=0)
        titulo_filtro = "Productos Disponibles"
    
    else:
        titulo_filtro = "Todos los Productos"

    if buscar:
        productos = productos.filter(
            models.Q(nom_prod__icontains=buscar) |
            models.Q(desc_prod__icontains=buscar)
        )

    if categoria_id:
        productos = productos.filter(fkcategoria_prod_id=categoria_id)
    
    if precio_min:
        productos = productos.filter(precio_prod__gte=precio_min)
    if precio_max:
        productos = productos.filter(precio_prod__lte=precio_max)
    
    if ordenar == 'precio_asc':
        productos = productos.order_by('precio_prod')
    elif ordenar == 'precio_desc':
        productos = productos.order_by('-precio_prod')
    elif ordenar == 'nombre':
        productos = productos.order_by('nom_prod')
    elif ordenar == 'nuevos':
        productos = productos.order_by('-fecha_creacion')
    elif ordenar == 'stock':
        productos = productos.order_by('-stock_prod')
    else:
        productos = productos.order_by('-fecha_creacion')
    
    categorias = CategoriaProductos.objects.annotate(
        num_productos=models.Count('productos', filter=models.Q(productos__estado_prod='disponible'))
    )
    
    negocios = Negocios.objects.annotate(
        num_productos=models.Count('productos', filter=models.Q(productos__estado_prod='disponible'))
    ).filter(estado_neg='activo')
    
    productos_data = []
    for producto in productos:
        producto_data = {
            'producto': producto,
            'precio_base': float(producto.precio_prod),
            'precio_final': float(producto.precio_prod),
            'tiene_descuento': False,
            'descuento_porcentaje': 0,
            'ahorro': 0,
            'stock': producto.stock_prod or 0,
            'tiene_variantes': False,
            'variantes': []
        }
        
        variantes = VariantesProducto.objects.filter(
            producto=producto, 
            estado_variante='activa'
        )
        
        if variantes.exists():
            producto_data['tiene_variantes'] = True
            
            variantes_detalladas = []
            for variante in variantes:
                variante_data = {
                    'id_variante': variante.id_variante,
                    'nombre_variante': variante.nombre_variante,
                    'precio_adicional': float(variante.precio_adicional),
                    'stock_variante': variante.stock_variante,
                    'imagen_variante': variante.imagen_variante,
                    'sku_variante': variante.sku_variante
                }
                variantes_detalladas.append(variante_data)
            
            producto_data['variantes'] = variantes_detalladas
        
        from django.db import connection
        from datetime import date
        
        hoy = date.today()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT porcentaje_descuento, titulo_promo 
                FROM promociones 
                WHERE fkproducto_id = %s 
                AND estado_promo = 'activa' 
                AND fecha_inicio <= %s 
                AND fecha_fin >= %s
                LIMIT 1
            """, [producto.pkid_prod, hoy, hoy])
            
            resultado = cursor.fetchone()
        
        if resultado:
            porcentaje_descuento, titulo_promo = resultado
            
            try:
                descuento = float(porcentaje_descuento)
                
                producto_data['precio_final'] = float(producto.precio_prod) * (1 - descuento / 100)
                producto_data['tiene_descuento'] = True
                producto_data['descuento_porcentaje'] = descuento
                producto_data['ahorro'] = float(producto.precio_prod) - producto_data['precio_final']
            except (ValueError, TypeError):
                pass
        
        productos_data.append(producto_data)
    
    paginator = Paginator(productos_data, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    carrito_count = 0
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        except Carrito.DoesNotExist:
            carrito = Carrito.objects.create(fkusuario_carrito=perfil_cliente)
            carrito_count = 0
            
    except Exception:
        carrito_count = 0
    
    context = {
        'productos_data': page_obj,
        'categorias': categorias,
        'negocios': negocios,
        'total_productos': paginator.count,
        'filtros_aplicados': {
            'buscar': buscar,
            'categoria': categoria_id,
            'negocio': request.GET.get('negocio', ''),
            'precio_min': precio_min,
            'precio_max': precio_max,
            'ordenar_por': ordenar,
        },
        'filtro_actual': filtro_tipo,
        'categoria_actual': categoria_id,
        'precio_min_actual': precio_min,
        'precio_max_actual': precio_max,
        'ordenar_actual': ordenar,
        'titulo_filtro': titulo_filtro,
        'carrito_count': carrito_count,
    }
    
    return render(request, 'Cliente/productos_filtros_logeado.html', context)

@login_required(login_url='/auth/login/')
def mis_pedidos_data(request):
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        pedidos = Pedidos.objects.filter(
            fkusuario_pedido=perfil_cliente
        ).order_by('-fecha_pedido')[:10]
        
        pedidos_data = []
        
        for pedido in pedidos:
            detalles = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
            
            productos_data = []
            for detalle in detalles:
                productos_data.append({
                    'nombre': detalle.fkproducto_detalle.nom_prod,
                    'cantidad': detalle.cantidad_detalle,
                    'precio_unitario': float(detalle.precio_unitario),
                    'imagen': detalle.fkproducto_detalle.img_prod.url if detalle.fkproducto_detalle.img_prod else None
                })
            
            tiempo_transcurrido = timezone.now() - pedido.fecha_pedido
            puede_cancelar = (tiempo_transcurrido < timedelta(hours=1) and 
                            pedido.estado_pedido in ['pendiente', 'confirmado'])
            
            tiempo_restante = None
            if puede_cancelar:
                tiempo_restante_segundos = timedelta(hours=1).total_seconds() - tiempo_transcurrido.total_seconds()
                horas = int(tiempo_restante_segundos // 3600)
                minutos = int((tiempo_restante_segundos % 3600) // 60)
                tiempo_restante = f"{minutos} min"
                if horas > 0:
                    tiempo_restante = f"{horas}h {minutos}min"
            
            estados_display = {
                'pendiente': 'Pendiente',
                'confirmado': 'Confirmado', 
                'preparando': 'Preparando',
                'enviado': 'Enviado',
                'entregado': 'Entregado',
                'cancelado': 'Cancelado'
            }
            
            pedido_data = {
                'pkid_pedido': pedido.pkid_pedido,
                'numero_pedido': f"{pedido.pkid_pedido:06d}",
                'estado_pedido': pedido.estado_pedido,
                'estado_display': estados_display.get(pedido.estado_pedido, pedido.estado_pedido),
                'total_pedido': float(pedido.total_pedido),
                'fecha_pedido': pedido.fecha_pedido.strftime('%d/%m/%Y %H:%M'),
                'negocio_nombre': pedido.fknegocio_pedido.nom_neg,
                'productos': productos_data,
                'puede_cancelar': puede_cancelar,
                'tiempo_restante': tiempo_restante,
                'metodo_pago': pedido.metodo_pago_texto or pedido.metodo_pago
            }
            
            pedidos_data.append(pedido_data)
        
        return JsonResponse({
            'success': True,
            'pedidos': pedidos_data
        })
        
    except Exception:
        return JsonResponse({
            'success': False,
            'message': 'Error al cargar los pedidos'
        })

@login_required(login_url='/auth/login/')
def cancelar_pedido(request):
    """Cancelar un pedido si no ha pasado 1 hora y restaurar stock"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pedido_id = data.get('pedido_id')
            
            perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
            
            # Obtener el pedido
            pedido = Pedidos.objects.get(
                pkid_pedido=pedido_id,
                fkusuario_pedido=perfil_cliente
            )
            
            # Verificar que no haya pasado 1 hora
            tiempo_transcurrido = timezone.now() - pedido.fecha_pedido
            if tiempo_transcurrido > timedelta(hours=1):
                return JsonResponse({
                    'success': False,
                    'message': 'No se puede cancelar el pedido. Ha pasado más de 1 hora desde que se realizó.'
                })
            
            # Verificar que el pedido esté en estado cancelable
            if pedido.estado_pedido not in ['pendiente', 'confirmado']:
                return JsonResponse({
                    'success': False, 
                    'message': f'No se puede cancelar un pedido en estado: {pedido.estado_pedido}'
                })
            
            # ✅ RESTAURAR STOCK ANTES DE CANCELAR
            stock_restaurado = restaurar_stock_pedido(pedido)
            
            # Actualizar estado del pedido
            pedido.estado_pedido = 'cancelado'
            pedido.fecha_actualizacion = timezone.now()
            pedido.save()
            
            mensaje = 'Pedido cancelado exitosamente'
            if stock_restaurado:
                mensaje += ' y stock restaurado'
            else:
                mensaje += ' (pero hubo un problema al restaurar el stock)'
            
            return JsonResponse({
                'success': True,
                'message': mensaje,
                'stock_restaurado': stock_restaurado
            })
            
        except Pedidos.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Pedido no encontrado'
            })
        except Exception:
            return JsonResponse({
                'success': False,
                'message': 'Error al cancelar el pedido'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    })

# =============================================================================
# VISTAS PARA FAVORITOS CON ACTUALIZACIÓN EN TIEMPO REAL
# =============================================================================

@login_required(login_url='/auth/login/')
@require_POST
def agregar_favorito(request):
    """Agregar producto a favoritos"""
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        
        if not producto_id:
            return JsonResponse({'success': False, 'message': 'ID de producto requerido'})
        
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        producto = Productos.objects.get(pkid_prod=producto_id, estado_prod='disponible')
        
        # Verificar si ya existe en favoritos
        favorito_existente = Favoritos.objects.filter(
            fkusuario=perfil_cliente,
            fkproducto=producto
        ).exists()
        
        if favorito_existente:
            return JsonResponse({
                'success': False, 
                'message': 'Este producto ya está en tus favoritos'
            })
        
        # Crear nuevo favorito
        favorito = Favoritos.objects.create(
            fkusuario=perfil_cliente,
            fkproducto=producto
        )
        
        # Contar favoritos actualizados
        favoritos_count = Favoritos.objects.filter(fkusuario=perfil_cliente).count()
        carrito_count = CarritoItem.objects.filter(
            fkcarrito__fkusuario_carrito=perfil_cliente
        ).count()
        
        return JsonResponse({
            'success': True, 
            'message': 'Producto agregado a favoritos',
            'favoritos_count': favoritos_count,
            'carrito_count': carrito_count
        })
            
    except Productos.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Producto no encontrado'})
    except UsuarioPerfil.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Perfil de usuario no encontrado'})
    except Exception:
        return JsonResponse({'success': False, 'message': 'Error al agregar a favoritos'})

@login_required(login_url='/auth/login/')
@require_POST
def eliminar_favorito(request):
    """Eliminar producto de favoritos"""
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        
        if not producto_id:
            return JsonResponse({'success': False, 'message': 'ID de producto requerido'})
        
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # Eliminar favorito
        deleted_count, _ = Favoritos.objects.filter(
            fkusuario=perfil_cliente,
            fkproducto_id=producto_id
        ).delete()
        
        if deleted_count == 0:
            return JsonResponse({
                'success': False, 
                'message': 'El producto no estaba en tus favoritos'
            })
        
        # Contar favoritos actualizados
        favoritos_count = Favoritos.objects.filter(fkusuario=perfil_cliente).count()
        carrito_count = CarritoItem.objects.filter(
            fkcarrito__fkusuario_carrito=perfil_cliente
        ).count()
        
        return JsonResponse({
            'success': True,
            'message': 'Producto eliminado de favoritos',
            'favoritos_count': favoritos_count,
            'carrito_count': carrito_count
        })
        
    except Exception:
        return JsonResponse({'success': False, 'message': 'Error al eliminar de favoritos'})

@login_required(login_url='/auth/login/')
def ver_favoritos(request):
    """Página para ver todos los favoritos del usuario con variantes y ofertas"""
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # Obtener favoritos con información completa
        favoritos = Favoritos.objects.filter(
            fkusuario=perfil_cliente
        ).select_related(
            'fkproducto',
            'fkproducto__fknegocioasociado_prod'
        ).order_by('-fecha_agregado')
        
        productos_favoritos = []
        hoy = timezone.now().date()
        
        for favorito in favoritos:
            producto = favorito.fkproducto
            
            # Verificar ofertas activas para el producto base
            precio_base = float(producto.precio_prod)
            precio_final = precio_base
            tiene_descuento = False
            descuento_porcentaje = 0
            ahorro = 0
            tiene_oferta_activa = False
            
            # Función auxiliar para obtener ofertas
            def obtener_info_oferta_corregida(producto_id, variante_id=None):
                try:
                    with connection.cursor() as cursor:
                        if variante_id:
                            cursor.execute("""
                                SELECT p.porcentaje_descuento, p.pkid_promo, p.variante_id
                                FROM promociones p
                                WHERE p.fkproducto_id = %s 
                                AND p.variante_id = %s
                                AND p.estado_promo = 'activa'
                                AND p.fecha_inicio <= %s 
                                AND p.fecha_fin >= %s
                                AND p.porcentaje_descuento > 0
                                LIMIT 1
                            """, [producto_id, variante_id, hoy, hoy])
                            result = cursor.fetchone()
                            
                            if result:
                                return {
                                    'porcentaje_descuento': float(result[0]),
                                    'pkid_promo': result[1],
                                    'variante_id': result[2],
                                    'es_oferta_especifica': True,
                                    'tiene_oferta': True
                                }
                        
                        # Buscar oferta para producto base
                        cursor.execute("""
                            SELECT p.porcentaje_descuento, p.pkid_promo, p.variante_id
                            FROM promociones p
                            WHERE p.fkproducto_id = %s 
                            AND p.variante_id IS NULL
                            AND p.estado_promo = 'activa'
                            AND p.fecha_inicio <= %s 
                            AND p.fecha_fin >= %s
                            AND p.porcentaje_descuento > 0
                            LIMIT 1
                        """, [producto_id, hoy, hoy])
                        
                        result = cursor.fetchone()
                        if result:
                            return {
                                'porcentaje_descuento': float(result[0]),
                                'pkid_promo': result[1],
                                'variante_id': result[2],
                                'es_oferta_especifica': False,
                                'tiene_oferta': True
                            }
                        
                        return None
                except Exception:
                    return None

            # Obtener oferta para producto base
            info_oferta_producto = obtener_info_oferta_corregida(producto.pkid_prod)
            if info_oferta_producto:
                descuento_porcentaje = info_oferta_producto['porcentaje_descuento']
                ahorro = precio_base * (descuento_porcentaje / 100)
                precio_final = precio_base - ahorro
                tiene_descuento = True
                tiene_oferta_activa = True
            
            # Verificar variantes
            variantes_list = []
            tiene_variantes = VariantesProducto.objects.filter(
                producto=producto, 
                estado_variante='activa'
            ).exists()
            
            if tiene_variantes:
                variantes = VariantesProducto.objects.filter(
                    producto=producto,
                    estado_variante='activa'
                )
                
                for variante in variantes:
                    try:
                        stock_variante = variante.stock_variante or 0
                        if stock_variante <= 0:
                            continue
                        
                        precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                        precio_base_variante = precio_base + precio_adicional
                        
                        # Verificar oferta para esta variante específica
                        info_oferta_variante = obtener_info_oferta_corregida(
                            producto.pkid_prod, 
                            variante.id_variante
                        )
                        
                        if info_oferta_variante:
                            descuento_porcentaje_variante = info_oferta_variante['porcentaje_descuento']
                            ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                            precio_final_variante = precio_base_variante - ahorro_variante
                            tiene_descuento_variante = True
                            tiene_oferta_activa_variante = True
                        else:
                            # Si no hay oferta específica para la variante, usar la oferta del producto base
                            descuento_porcentaje_variante = descuento_porcentaje
                            ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100) if descuento_porcentaje_variante > 0 else 0
                            precio_final_variante = precio_base_variante - ahorro_variante
                            tiene_descuento_variante = tiene_descuento
                            tiene_oferta_activa_variante = tiene_oferta_activa
                        
                        variante_data = {
                            'id_variante': variante.id_variante,
                            'nombre_variante': variante.nombre_variante,
                            'precio_adicional': precio_adicional,
                            'stock_variante': stock_variante,
                            'imagen_variante': variante.imagen_variante,
                            'estado_variante': variante.estado_variante,
                            'sku_variante': variante.sku_variante,
                            'precio_base_calculado': round(precio_base_variante, 2),
                            'precio_final_calculado': round(precio_final_variante, 2),
                            'ahorro_calculado': round(ahorro_variante, 2),
                            'descuento_porcentaje_calculado': descuento_porcentaje_variante,
                            'tiene_descuento_calculado': tiene_descuento_variante,
                            'tiene_oferta_activa': tiene_oferta_activa_variante,
                        }
                        variantes_list.append(variante_data)
                        
                    except Exception:
                        continue
            
            # Obtener URL de imagen
            imagen_url = ''
            if producto.img_prod:
                try:
                    imagen_url = request.build_absolute_uri(producto.img_prod.url)
                except:
                    imagen_url = '/static/img/placeholder-producto.jpg'
            else:
                imagen_url = '/static/img/placeholder-producto.jpg'
            
            producto_data = {
                'producto': producto,
                'precio_base': precio_base,
                'precio_final': round(precio_final, 2),
                'tiene_descuento': tiene_descuento,
                'descuento_porcentaje': descuento_porcentaje,
                'ahorro': round(ahorro, 2),
                'tiene_variantes': tiene_variantes,
                'variantes': variantes_list,
                'stock': producto.stock_prod or 0,
                'fecha_agregado': favorito.fecha_agregado,
                'es_favorito': True,
                'favorito_id': favorito.pkid_favorito,
                'nombre': producto.nom_prod,
                'precio_actual': str(producto.precio_prod),
                'imagen': imagen_url,
                'negocio': producto.fknegocioasociado_prod.nom_neg if producto.fknegocioasociado_prod else 'Vecy',
                'tiene_oferta_activa': tiene_oferta_activa,
                'tiene_stock': (producto.stock_prod or 0) > 0 or len(variantes_list) > 0
            }
            
            productos_favoritos.append(producto_data)
        
        # Contadores para el dashboard
        carrito_count = 0
        favoritos_count = favoritos.count()
        pedidos_pendientes_count = 0
        
        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        except Carrito.DoesNotExist:
            pass
        
        try:
            pedidos_pendientes_count = Pedidos.objects.filter(
                fkusuario_pedido=perfil_cliente,
                estado_pedido__in=['pendiente', 'confirmado', 'preparando']
            ).count()
        except Exception:
            pass
        
        context = {
            'productos_favoritos': productos_favoritos,
            'total_favoritos': len(productos_favoritos),
            'carrito_count': carrito_count,
            'favoritos_count': favoritos_count,
            'pedidos_pendientes_count': pedidos_pendientes_count,
            'hay_favoritos': len(productos_favoritos) > 0,
        }
        
        return render(request, 'cliente/favoritos.html', context)
        
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, 'Complete su perfil para acceder a esta funcionalidad.')
        return redirect('completar_perfil')
    except Exception:
        messages.error(request, 'Error al cargar los favoritos')
        return redirect('cliente_dashboard')
    
@login_required(login_url='/auth/login/')
def verificar_favorito(request):
    """Verificar si un producto está en favoritos"""
    try:
        producto_id = request.GET.get('producto_id')
        
        if not producto_id:
            return JsonResponse({'success': False, 'es_favorito': False})
        
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        es_favorito = Favoritos.objects.filter(
            fkusuario=perfil_cliente,
            fkproducto_id=producto_id
        ).exists()
        
        return JsonResponse({
            'success': True,
            'es_favorito': es_favorito
        })
        
    except Exception:
        return JsonResponse({'success': False, 'es_favorito': False})

@login_required(login_url='/auth/login/')
def contar_favoritos(request):
    """Obtener contador actual de favoritos"""
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        favoritos_count = Favoritos.objects.filter(fkusuario=perfil_cliente).count()
        
        return JsonResponse({
            'success': True,
            'favoritos_count': favoritos_count
        })
        
    except Exception:
        return JsonResponse({'success': False, 'favoritos_count': 0})
    
@login_required
def favoritos_data(request):
    """API para obtener favoritos en formato JSON con variantes y ofertas"""
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        favoritos = Favoritos.objects.filter(
            fkusuario=perfil_cliente
        ).select_related(
            'fkproducto',
            'fkproducto__fknegocioasociado_prod'
        ).order_by('-fecha_agregado')
        
        hoy = timezone.now().date()
        favoritos_data = []
        
        for favorito in favoritos:
            producto = favorito.fkproducto
            
            # INFORMACIÓN BASE DEL PRODUCTO
            precio_base = float(producto.precio_prod)
            precio_final = precio_base
            tiene_descuento = False
            descuento_porcentaje = 0
            ahorro = 0
            tiene_oferta_activa = False
            
            # VERIFICAR OFERTAS ACTIVAS
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT porcentaje_descuento, titulo_promo 
                    FROM promociones 
                    WHERE fkproducto_id = %s 
                    AND estado_promo = 'activa'
                    AND fecha_inicio <= %s 
                    AND fecha_fin >= %s
                    LIMIT 1
                """, [producto.pkid_prod, hoy, hoy])
                
                result = cursor.fetchone()
                if result and result[0] is not None:
                    try:
                        descuento_porcentaje = float(result[0])
                        if descuento_porcentaje > 0:
                            precio_final = precio_base * (1 - (descuento_porcentaje / 100))
                            ahorro = precio_base - precio_final
                            tiene_descuento = True
                            tiene_oferta_activa = True
                    except (ValueError, TypeError):
                        pass
            
            # INFORMACIÓN DE VARIANTES
            variantes_list = []
            tiene_variantes = VariantesProducto.objects.filter(
                producto=producto, 
                estado_variante='activa'
            ).exists()
            
            if tiene_variantes:
                variantes = VariantesProducto.objects.filter(
                    producto=producto,
                    estado_variante='activa'
                )
                
                for variante in variantes:
                    # Verificar ofertas para cada variante
                    precio_base_variante = precio_base + float(variante.precio_adicional or 0)
                    precio_final_variante = precio_base_variante
                    tiene_descuento_variante = False
                    descuento_porcentaje_variante = 0
                    
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT porcentaje_descuento 
                            FROM promociones 
                            WHERE fkproducto_id = %s 
                            AND variante_id = %s
                            AND estado_promo = 'activa'
                            AND fecha_inicio <= %s 
                            AND fecha_fin >= %s
                            LIMIT 1
                        """, [producto.pkid_prod, variante.id_variante, hoy, hoy])
                        
                        result_variante = cursor.fetchone()
                        if result_variante and result_variante[0] is not None:
                            try:
                                descuento_porcentaje_variante = float(result_variante[0])
                                if descuento_porcentaje_variante > 0:
                                    precio_final_variante = precio_base_variante * (1 - (descuento_porcentaje_variante / 100))
                                    tiene_descuento_variante = True
                            except (ValueError, TypeError):
                                pass
                    
                    variante_data = {
                        'id_variante': variante.id_variante,
                        'nombre_variante': variante.nombre_variante,
                        'precio_adicional': float(variante.precio_adicional or 0),
                        'stock_variante': variante.stock_variante or 0,
                        'imagen_variante': variante.imagen_variante.url if variante.imagen_variante else None,
                        'precio_base': precio_base_variante,
                        'precio_final': precio_final_variante,
                        'tiene_descuento': tiene_descuento_variante,
                        'descuento_porcentaje': descuento_porcentaje_variante,
                    }
                    variantes_list.append(variante_data)
            
            # Obtener URL de imagen
            imagen_url = ''
            if producto.img_prod:
                try:
                    imagen_url = request.build_absolute_uri(producto.img_prod.url)
                except:
                    imagen_url = '/static/img/placeholder-producto.jpg'
            else:
                imagen_url = '/static/img/placeholder-producto.jpg'
            
            # Construir respuesta
            favorito_item = {
                'producto_id': producto.pkid_prod,
                'nombre': producto.nom_prod,
                'precio_base': precio_base,
                'precio_final': round(precio_final, 2),
                'precio_original': precio_base,  # Para comparar
                'tiene_descuento': tiene_descuento,
                'descuento_porcentaje': descuento_porcentaje,
                'ahorro': round(ahorro, 2),
                'tiene_oferta_activa': tiene_oferta_activa,
                'imagen': imagen_url,
                'negocio': producto.fknegocioasociado_prod.nom_neg if producto.fknegocioasociado_prod else 'Vecy',
                'fecha_agregado': favorito.fecha_agregado.strftime('%Y-%m-%d %H:%M'),
                'tiene_variantes': tiene_variantes,
                'variantes': variantes_list,
                'stock': producto.stock_prod or 0,
                'tiene_stock': (producto.stock_prod or 0) > 0 or len(variantes_list) > 0,
                'es_variante': tiene_variantes,  # Para mostrar badge en template
            }
            
            favoritos_data.append(favorito_item)
        
        response_data = {
            'success': True,
            'favoritos': favoritos_data,
            'total': len(favoritos_data),
            'debug': {
                'usuario': request.user.username,
                'favoritos_count': favoritos.count(),
                'timestamp': timezone.now().isoformat()
            }
        }
        
        return JsonResponse(response_data)
        
    except UsuarioPerfil.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Perfil de usuario no encontrado'
        }, status=404)
    except Exception:
        return JsonResponse({
            'success': False,
            'error': 'Error al cargar favoritos'
        }, status=500)

# =============================================================================
# VISTAS PARA PERFIL DE USUARIO
# =============================================================================

from ..forms import UserProfileForm

@login_required
def get_perfil_form(request):
    """Vista que retorna solo el formulario para el modal"""
    try:
        usuario = request.user
        form = UserProfileForm(instance=usuario)
        
        context = {
            'form': form,
            'user': usuario
        }
        
        return render(request, 'perfil/_perfil_form.html', context)
        
    except Exception:
        form = UserProfileForm()
        return render(request, 'perfil/_perfil_form.html', {
            'form': form,
            'error': 'Error al cargar el formulario'
        })

@login_required
def actualizar_perfil(request):
    """Vista para actualizar el perfil del usuario"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            usuario = request.user
            form = UserProfileForm(request.POST, request.FILES, instance=usuario)
            
            if form.is_valid():
                user = form.save()
                
                # ACTUALIZAR SESIÓN CON LA NUEVA IMAGEN
                request.session['usuario_nombre'] = user.first_name
                if hasattr(user, 'usuarioperfil') and user.usuarioperfil.img_user:
                    request.session['usuario_imagen'] = user.usuarioperfil.img_user.url
                
                return JsonResponse({
                    'success': True,
                    'message': 'Perfil actualizado correctamente',
                    'usuario_nombre': user.first_name,
                    'usuario_imagen': user.usuarioperfil.img_user.url if hasattr(user, 'usuarioperfil') and user.usuarioperfil.img_user else None
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Por favor corrige los errores del formulario',
                    'errors': form.errors
                })
                
        except Exception:
            return JsonResponse({
                'success': False,
                'message': 'Error al actualizar el perfil'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    })

# =============================================================================
# VISTAS PARA NOTIFICACIONES
# =============================================================================

@login_required
def get_notifications(request):
    """Obtener notificaciones no leídas y recientes"""
    try:
        # Obtener notificaciones no leídas + las últimas 10 leídas
        notificaciones_no_leidas = Notificacion.objects.filter(
            usuario=request.user, 
            leida=False
        ).order_by('-fecha_creacion')
        
        notificaciones_leidas = Notificacion.objects.filter(
            usuario=request.user, 
            leida=True
        ).order_by('-fecha_creacion')[:10]
        
        notificaciones = list(notificaciones_no_leidas) + list(notificaciones_leidas)
        notificaciones.sort(key=lambda x: x.fecha_creacion, reverse=True)
        
        notifications_data = []
        for notificacion in notificaciones:
            notifications_data.append({
                'id': notificacion.id,
                'tipo': notificacion.tipo,
                'titulo': notificacion.titulo,
                'mensaje': notificacion.mensaje,
                'leida': notificacion.leida,
                'tiempo': notificacion.tiempo_transcurrido,
                'url': notificacion.url,
                'fecha': notificacion.fecha_creacion.strftime("%d/%m/%Y %H:%M")
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': notificaciones_no_leidas.count()
        })
        
    except Exception:
        return JsonResponse({
            'success': False,
            'error': 'Error al cargar notificaciones'
        })

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def mark_notification_read(request):
    """Marcar una notificación como leída"""
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        notificacion = Notificacion.objects.get(
            id=notification_id, 
            usuario=request.user
        )
        notificacion.leida = True
        notificacion.save()
        
        return JsonResponse({'success': True})
        
    except Notificacion.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notificación no encontrada'})
    except Exception:
        return JsonResponse({'success': False, 'error': 'Error al marcar notificación'})

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def mark_all_notifications_read(request):
    """Marcar todas las notificaciones como leídas"""
    try:
        Notificacion.objects.filter(
            usuario=request.user, 
            leida=False
        ).update(leida=True)
        
        return JsonResponse({'success': True})
        
    except Exception:
        return JsonResponse({'success': False, 'error': 'Error al marcar notificaciones'})

@login_required
def ver_notificaciones(request):
    """Página para ver todas las notificaciones"""
    notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(notificaciones, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'notificaciones/ver_notificaciones.html', {
        'page_obj': page_obj,
        'unread_count': notificaciones.filter(leida=False).count()
    })

# =============================================================================
# FUNCIONES AUXILIARES PARA STOCK
# =============================================================================

def restaurar_stock_pedido(pedido):
    """Restaurar stock cuando se cancela un pedido"""
    try:
        detalles_pedido = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
        hoy = timezone.now().date()
        
        for detalle in detalles_pedido:
            producto = detalle.fkproducto_detalle
            cantidad = detalle.cantidad_detalle
            
            # Buscar el item del carrito correspondiente para obtener variante_id
            try:
                carrito_items = CarritoItem.objects.filter(
                    fkproducto=producto,
                    fkcarrito__fkusuario_carrito=pedido.fkusuario_pedido
                )
                
                item_correspondiente = None
                for item in carrito_items:
                    if item.cantidad == cantidad or abs(item.cantidad - cantidad) <= 2:
                        item_correspondiente = item
                        break
                
                if not item_correspondiente and carrito_items.exists():
                    item_correspondiente = carrito_items.first()
                
                variante_id = item_correspondiente.variante_id if item_correspondiente else None
                
            except Exception:
                variante_id = None
            
            # Verificar si este producto/variante estaba en oferta con stock específico
            with connection.cursor() as cursor:
                if variante_id:
                    cursor.execute("""
                        SELECT pkid_promo, stock_actual_oferta, stock_oferta, activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND variante_id = %s
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [producto.pkid_prod, variante_id, hoy, hoy])
                else:
                    cursor.execute("""
                        SELECT pkid_promo, stock_actual_oferta, stock_oferta, activa_por_stock
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [producto.pkid_prod, hoy, hoy])
                
                promocion_data = cursor.fetchone()
            
            # Si había una promoción con stock de oferta, restaurar ahí primero
            if promocion_data and promocion_data[3]:
                promo_id, stock_actual_oferta, stock_oferta, activa_por_stock = promocion_data
                
                if stock_actual_oferta is not None and stock_oferta is not None:
                    # Restaurar al stock de oferta (hasta el máximo original)
                    nuevo_stock_oferta = min(stock_actual_oferta + cantidad, stock_oferta)
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE promociones 
                            SET stock_actual_oferta = %s 
                            WHERE pkid_promo = %s
                        """, [nuevo_stock_oferta, promo_id])
                    
                    # Si hay excedente después de llenar el stock de oferta, restaurar al stock general
                    excedente = max(0, (stock_actual_oferta + cantidad) - stock_oferta)
                    if excedente > 0:
                        _restaurar_stock_general(producto, excedente, variante_id)
                    
                    continue
            
            # Si no había promoción con stock de oferta, restaurar al stock general
            _restaurar_stock_general(producto, cantidad, variante_id)
        
        return True
        
    except Exception:
        return False

def _restaurar_stock_general(producto, cantidad, variante_id=None):
    """Restaurar stock general del producto o variante"""
    try:
        if variante_id:
            # Restaurar stock de variante
            variante = VariantesProducto.objects.get(
                id_variante=variante_id,
                producto=producto
            )
            variante.stock_variante += cantidad
            variante.save()
        else:
            # Restaurar stock de producto base
            producto.stock_prod += cantidad
            producto.save()
            
    except Exception:
        pass

# =============================================================================
# FUNCIONES PARA CREAR NOTIFICACIONES AUTOMÁTICAS
# =============================================================================

def crear_notificacion_pedido(usuario, pedido, tipo_estado):
    """Crear notificación por cambio de estado de pedido"""
    mensajes = {
        'confirmado': f"Tu pedido #{pedido.pkid_pedido} ha sido confirmado",
        'preparando': f"¡Tu pedido #{pedido.pkid_pedido} está en preparación!",
        'en_camino': f"El repartidor está en camino con tu pedido #{pedido.pkid_pedido}",
        'entregado': f"🎉 Pedido #{pedido.pkid_pedido} entregado exitosamente",
        'cancelado': f"Pedido #{pedido.pkid_pedido} cancelado",
    }
    
    Notificacion.objects.create(
        usuario=usuario,
        tipo='pedido',
        titulo='Actualización de Pedido',
        mensaje=mensajes.get(tipo_estado, f"Actualización en tu pedido #{pedido.pkid_pedido}"),
        url=f"/pedidos/{pedido.pkid_pedido}/"
    )

def crear_notificacion_oferta_flash(usuario, producto, descuento, horas_duracion):
    """Crear notificación de oferta flash"""
    Notificacion.objects.create(
        usuario=usuario,
        tipo='oferta',
        titulo='🔥 OFERTA FLASH',
        mensaje=f"{descuento}% OFF en {producto.nom_prod} - Solo por {horas_duracion} horas!",
        url=f"/producto/{producto.pkid_prod}/",
        datos_extra={
            'producto_id': producto.pkid_prod,
            'descuento': descuento,
            'valido_hasta': (timezone.now() + timedelta(hours=horas_duracion)).isoformat()
        }
    )

def crear_notificacion_nuevo_producto(usuario, negocio, producto):
    """Notificación cuando un negocio agrega nuevo producto"""
    Notificacion.objects.create(
        usuario=usuario,
        tipo='negocio',
        titulo='Nuevo Producto Disponible',
        mensaje=f"{negocio.nom_neg} agregó: {producto.nom_prod}",
        url=f"/producto/{producto.pkid_prod}/"
    )

def crear_notificacion_personalizada(usuario, producto, tipo):
    """Notificaciones personalizadas basadas en comportamiento"""
    mensajes = {
        'precio_bajo': f"¡Buenas noticias! {producto.nom_prod} bajó de precio",
        'stock_nuevo': f"¡Stock renovado! {producto.nom_prod} está disponible nuevamente",
        'visto_recientemente': f"¿Te interesa? {producto.nom_prod} que viste está en oferta",
    }
    
    Notificacion.objects.create(
        usuario=usuario,
        tipo='promocion',
        titulo='Oportunidad Especial',
        mensaje=mensajes.get(tipo, f"Oferta especial en {producto.nom_prod}"),
        url=f"/producto/{producto.pkid_prod}/"
    )

def crear_notificacion_sistema(usuario, titulo, mensaje, url=None):
    """Notificación genérica del sistema"""
    Notificacion.objects.create(
        usuario=usuario,
        tipo='sistema',
        titulo=titulo,
        mensaje=mensaje,
        url=url
    )