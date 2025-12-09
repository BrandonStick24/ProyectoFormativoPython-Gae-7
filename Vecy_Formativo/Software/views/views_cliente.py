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
from django.utils import timezone
from django.db import connection
from django.shortcuts import render
from ..models import *
from ..services.gemini_service import asistente_gemini
from django.db import connection, models
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from datetime import date
from django.http import JsonResponse
from django.db.models import Q
import json
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models import Q
from Software.models import Productos, CategoriaProductos

@csrf_exempt
def api_sugerencia_completa(request):
    """API DEBUG - Siempre funciona, muestra datos reales CON FILTRO EXACTO"""
    
    query = request.GET.get('q', '').strip().lower()  # Convertir a minúsculas
    print(f"🎯 DEBUG API - Query recibida: '{query}'")
    
    suggestions = []
    
    try:
        from ..models import Productos
        
        if query:
            # FILTRO EXACTO - Solo productos que CONTENGAN la query
            print(f"🔍 Buscando productos que contengan: '{query}'")
            
            # Usar icontains para búsqueda case-insensitive
            productos = Productos.objects.filter(
                estado_prod='disponible',
                nom_prod__icontains=query  # ESTA ES LA LÍNEA CLAVE
            )[:8]  # Aumentar a 8 resultados
            
            print(f"📦 Productos encontrados en BD: {productos.count()}")
            
            # DEBUG: Mostrar qué productos encontró
            for p in productos:
                print(f"   • {p.nom_prod} - ¿Contiene '{query}'?: {'SÍ' if query in p.nom_prod.lower() else 'NO'}")
            
            for p in productos:
                # Verificar que realmente contenga la query
                if query not in p.nom_prod.lower():
                    print(f"⚠️ Saltando: {p.nom_prod} no contiene '{query}'")
                    continue
                    
                suggestions.append({
                    'type': 'producto',
                    'id': p.pkid_prod,
                    'value': p.nom_prod,
                    'text': f"{p.nom_prod} (${float(p.precio_prod) if p.precio_prod else 0:,.0f})",
                    'category': getattr(p.fkcategoria_prod, 'desc_cp', 'General'),
                    'negocio': getattr(p.fknegocioasociado_prod, 'nom_neg', 'VECY'),
                    'precio': float(p.precio_prod) if p.precio_prod else 0,
                    'precio_formateado': f"${float(p.precio_prod):,.0f}".replace(',', '.') if p.precio_prod else '$0',
                    'url': f"/productos-filtrados/?q={p.nom_prod.replace(' ', '+')}"
                })
                
        else:
            # Si no hay query, productos populares
            print("📦 Mostrando productos populares (sin query)")
            productos = Productos.objects.filter(estado_prod='disponible')[:5]
            
            for p in productos:
                suggestions.append({
                    'type': 'producto',
                    'id': p.pkid_prod,
                    'value': p.nom_prod,
                    'text': f"{p.nom_prod} (${float(p.precio_prod) if p.precio_prod else 0:,.0f})",
                    'category': getattr(p.fkcategoria_prod, 'desc_cp', 'General'),
                    'negocio': getattr(p.fknegocioasociado_prod, 'nom_neg', 'VECY'),
                    'precio': float(p.precio_prod) if p.precio_prod else 0,
                    'precio_formateado': f"${float(p.precio_prod):,.0f}".replace(',', '.') if p.precio_prod else '$0',
                    'url': f"/productos-filtrados/?q={p.nom_prod.replace(' ', '+')}"
                })
            
        print(f"✅ DEBUG: Devolviendo {len(suggestions)} productos REALES")
        
        # Si no hay resultados, mostrar mensaje
        if query and len(suggestions) == 0:
            print(f"⚠️ No se encontraron productos con '{query}'")
        
    except Exception as e:
        print(f"❌ DEBUG Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Datos de emergencia que SI coincidan con la query
        if query:
            suggestions = [
                {
                    'type': 'producto',
                    'id': 1,
                    'value': f'Producto de prueba {query}',
                    'text': f'Producto de prueba {query} ($10.000)',
                    'category': 'Prueba',
                    'negocio': 'Tienda Demo',
                    'precio': 10000,
                    'precio_formateado': '$10.000',
                    'url': f'/productos-filtrados/?q={query.replace(" ", "+")}'
                }
            ]
        else:
            suggestions = [
                {
                    'type': 'producto',
                    'id': 1,
                    'value': 'Producto de ejemplo 1',
                    'text': 'Producto de ejemplo 1 ($10.000)',
                    'category': 'Ejemplo',
                    'negocio': 'Tienda Demo',
                    'precio': 10000,
                    'precio_formateado': '$10.000',
                    'url': '/productos-filtrados/?q=Producto+de+ejemplo+1'
                }
            ]
    
    return JsonResponse({
        'success': True,
        'query': query,
        'suggestions': suggestions,
        'count': len(suggestions),
        'debug': f'Modo debug: {len(suggestions)} resultados para "{query}"'
    })


# =============================================================================
# VISTAS PARA ACTUALIZACIÓN EN TIEMPO REAL DE CONTADORES
# =============================================================================
def prueba_productos(request):
    """Vista de prueba para ver productos en la BD"""
    from ..models import Productos, CategoriaProductos, Negocios
    
    productos = Productos.objects.all()[:20]
    total_productos = Productos.objects.count()
    productos_disponibles = Productos.objects.filter(estado_prod='disponible').count()
    
    resultados = []
    for p in productos:
        resultados.append({
            'id': p.pkid_prod,
            'nombre': p.nom_prod,
            'precio': str(p.precio_prod),
            'estado': p.estado_prod,
            'categoria': p.fkcategoria_prod.desc_cp if p.fkcategoria_prod else 'None',
            'negocio': p.fknegocioasociado_prod.nom_neg if p.fknegocioasociado_prod else 'None'
        })
    
    return JsonResponse({
        'total_productos': total_productos,
        'productos_disponibles': productos_disponibles,
        'productos_ejemplo': resultados
    })
    
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

@never_cache
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

@never_cache
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

@never_cache
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

@never_cache
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
        # IMPORTAR HELPER DE COMBOS
        # =============================================
        combos_activos = []
        promociones_2x1 = []
        ofertas_especiales = []
        
        try:
            from .helpers_combos import (
                obtener_combos_activos,
                obtener_promociones_2x1,
                obtener_ofertas_especiales
            )
            
            combos_activos = obtener_combos_activos(limite=8)
            promociones_2x1 = obtener_promociones_2x1(limite=8)
            ofertas_especiales = obtener_ofertas_especiales()
        except ImportError:
            try:
                from helpers_combos import (
                    obtener_combos_activos,
                    obtener_promociones_2x1,
                    obtener_ofertas_especiales
                )
                combos_activos = obtener_combos_activos(limite=8)
                promociones_2x1 = obtener_promociones_2x1(limite=8)
                ofertas_especiales = obtener_ofertas_especiales()
            except ImportError:
                pass

        # =============================================
        # FUNCIÓN PARA FORMATEAR PRECIOS
        # =============================================
        def formatear_precio(valor):
            try:
                if valor is None:
                    return "0.00"
                valor_float = float(valor)
                return "{:,.2f}".format(valor_float).replace(',', 'X').replace('.', ',').replace('X', '.')
            except (ValueError, TypeError):
                return "0.00"

        # =============================================
        # DETECCIÓN DE FECHAS ESPECIALES
        # =============================================
        fecha_especial = None
        mensaje_especial = None
        try:
            mes_actual = hoy.month
            dia_actual = hoy.day
            
            if mes_actual == 11 and dia_actual >= 28:
                fecha_especial = "navidad"
                mensaje_especial = "🎄 ¡Especiales de Navidad! 🎁"
            elif mes_actual == 12:
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
            elif mes_actual == 11 and dia_actual >= 20 and dia_actual <= 27:
                fecha_especial = "black_friday"
                mensaje_especial = "⚫️ Black Friday ⚫️"
            elif (mes_actual == 12 and dia_actual >= 28) or (mes_actual == 1 and dia_actual <= 10):
                fecha_especial = "ano_nuevo"
                mensaje_especial = "🎉 Ofertas de Año Nuevo"
            elif mes_actual == 9 and (dia_actual >= 15 and dia_actual <= 20):
                 fecha_especial = "fiestas_patrias"
                 mensaje_especial = "🇨🇱 ¡Fiestas Patrias! 🇨🇱"
        except:
            pass

        # =============================================
        # FUNCIÓN PARA OBTENER INFO DE OFERTA
        # =============================================
        def obtener_info_oferta(producto_id, variante_id=None):
            try:
                with connection.cursor() as cursor:
                    if variante_id:
                        cursor.execute("""
                            SELECT p.porcentaje_descuento, p.pkid_promo, p.variante_id, 
                                   p.stock_actual_oferta, p.stock_inicial_oferta, p.activa_por_stock
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
                            stock_oferta = result[3] if result[5] == 1 else None
                            return {
                                'porcentaje_descuento': float(result[0]),
                                'pkid_promo': result[1],
                                'variante_id': result[2],
                                'stock_oferta': stock_oferta,
                                'activa_por_stock': result[5],
                                'es_oferta_especifica': True,
                                'tiene_oferta': True
                            }
                    
                    if variante_id is None:
                        cursor.execute("""
                            SELECT p.porcentaje_descuento, p.pkid_promo, p.variante_id,
                                   p.stock_actual_oferta, p.stock_inicial_oferta, p.activa_por_stock
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
                            stock_oferta = result[3] if result[5] == 1 else None
                            return {
                                'porcentaje_descuento': float(result[0]),
                                'pkid_promo': result[1],
                                'variante_id': result[2],
                                'stock_oferta': stock_oferta,
                                'activa_por_stock': result[5],
                                'es_oferta_especifica': False,
                                'tiene_oferta': True
                            }
                    
                    return None
            except:
                return None

        # =============================================
        # FUNCIÓN PARA CREAR ITEMS INDIVIDUALES DE VARIANTES
        # =============================================
        def crear_items_individuales(producto):
            items = []
            
            try:
                precio_base_producto = float(producto.precio_prod) if producto.precio_prod else 0
                
                # Verificar si el producto base tiene stock
                stock_base = producto.stock_prod or 0
                if stock_base > 0:
                    info_oferta_producto = obtener_info_oferta(producto.pkid_prod)
                    
                    if info_oferta_producto:
                        descuento = info_oferta_producto['porcentaje_descuento']
                        ahorro = precio_base_producto * (descuento / 100)
                        precio_final = precio_base_producto - ahorro
                        stock_mostrar = info_oferta_producto.get('stock_oferta') if info_oferta_producto.get('activa_por_stock') == 1 else stock_base
                    else:
                        descuento = 0
                        ahorro = 0
                        precio_final = precio_base_producto
                        stock_mostrar = stock_base
                    
                    item_base = {
                        'producto': producto,
                        'id_variante': None,
                        'nombre_completo': producto.nom_prod,
                        'precio_base': precio_base_producto,
                        'precio_base_formateado': formatear_precio(precio_base_producto),
                        'precio_final': round(precio_final, 2),
                        'precio_final_formateado': formatear_precio(precio_final),
                        'descuento_porcentaje': descuento,
                        'ahorro': round(ahorro, 2),
                        'ahorro_formateado': formatear_precio(ahorro),
                        'stock': stock_mostrar,
                        'imagen': producto.img_prod.url if producto.img_prod else None,
                        'es_variante': False,
                        'tiene_oferta': descuento > 0
                    }
                    items.append(item_base)
                
                # Agregar variantes como items individuales
                variantes = VariantesProducto.objects.filter(
                    producto=producto,
                    estado_variante='activa',
                    stock_variante__gt=0
                )
                
                for variante in variantes:
                    precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                    precio_base_variante = precio_base_producto + precio_adicional
                    
                    info_oferta_variante = obtener_info_oferta(producto.pkid_prod, variante.id_variante)
                    
                    if info_oferta_variante:
                        descuento = info_oferta_variante['porcentaje_descuento']
                        ahorro = precio_base_variante * (descuento / 100)
                        precio_final = precio_base_variante - ahorro
                        stock_mostrar = info_oferta_variante.get('stock_oferta') if info_oferta_variante.get('activa_por_stock') == 1 else variante.stock_variante
                    else:
                        descuento = 0
                        ahorro = 0
                        precio_final = precio_base_variante
                        stock_mostrar = variante.stock_variante
                    
                    item_variante = {
                        'producto': producto,
                        'id_variante': variante.id_variante,
                        'nombre_completo': f"{producto.nom_prod} - {variante.nombre_variante}",
                        'nombre_variante': variante.nombre_variante,
                        'precio_base': precio_base_variante,
                        'precio_base_formateado': formatear_precio(precio_base_variante),
                        'precio_final': round(precio_final, 2),
                        'precio_final_formateado': formatear_precio(precio_final),
                        'descuento_porcentaje': descuento,
                        'ahorro': round(ahorro, 2),
                        'ahorro_formateado': formatear_precio(ahorro),
                        'stock': stock_mostrar,
                        'imagen': variante.imagen_variante.url if variante.imagen_variante else (producto.img_prod.url if producto.img_prod else None),
                        'es_variante': True,
                        'tiene_oferta': descuento > 0
                    }
                    items.append(item_variante)
                    
            except:
                pass
            
            return items

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
                           p.fknegocio_id, p.fkproducto_id, p.variante_id,
                           p.stock_actual_oferta, p.activa_por_stock
                    FROM promociones p
                    INNER JOIN productos pr ON p.fkproducto_id = pr.pkid_prod
                    WHERE p.estado_promo = 'activa'
                    AND p.fecha_inicio >= %s
                    AND p.fecha_fin >= %s
                    AND (
                        (p.activa_por_stock = 1 AND p.stock_actual_oferta > 0) OR
                        (p.activa_por_stock = 0 AND pr.stock_prod > 0)
                    )
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
                            except:
                                descuento_valor = 0
                        
                        producto = Productos.objects.get(pkid_prod=row[9])
                        negocio = Negocios.objects.get(pkid_neg=row[8])
                        variante_id = row[10]
                        stock_oferta = row[11]
                        activa_por_stock = row[12]
                        
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
                            except:
                                pass
                        
                        ahorro_oferta = precio_base * (descuento_valor / 100)
                        
                        titulo_corto = f"{producto.nom_prod}"
                        if variante_nombre:
                            titulo_corto = f"{variante_nombre}"
                        
                        descripcion_corta = f"Oferta especial -{descuento_valor}% OFF"
                        
                        if activa_por_stock == 1:
                            stock_mostrar = stock_oferta
                            es_stock_limitado = True
                        else:
                            stock_mostrar = producto.stock_prod or 0
                            es_stock_limitado = False
                        
                        oferta_data = {
                            'pkid_promo': row[0],
                            'titulo_promo': titulo_corto,
                            'descripcion_promo': descripcion_corta,
                            'porcentaje_descuento': descuento_valor,
                            'precio_base': precio_base,
                            'precio_base_formateado': formatear_precio(precio_base),
                            'precio_final': precio_base - ahorro_oferta,
                            'precio_final_formateado': formatear_precio(precio_base - ahorro_oferta),
                            'ahorro_oferta': round(ahorro_oferta, 2),
                            'ahorro_oferta_formateado': formatear_precio(ahorro_oferta),
                            'imagen_promo': row[7] or (producto.img_prod.url if producto.img_prod else None),
                            'fkproducto': producto,
                            'fknegocio': negocio,
                            'variante_id': variante_id,
                            'variante_nombre': variante_nombre,
                            'stock_oferta': stock_mostrar,
                            'es_stock_limitado': es_stock_limitado,
                        }
                        
                        ofertas_carrusel_data.append(oferta_data)
                        
                    except:
                        continue
        except:
            pass

        # =============================================
        # PRODUCTOS POR FECHA ESPECIAL (INDIVIDUALES)
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
                        items = crear_items_individuales(producto)
                        productos_fecha_especial_data.extend(items)
        except:
            pass

        # =============================================
        # ELECTRODOMÉSTICOS (INDIVIDUALES)
        # =============================================
        electrodomesticos_data = []
        try:
            electrodomesticos = Productos.objects.filter(
                estado_prod='disponible',
                fkcategoria_prod=5
            ).order_by('-precio_prod')[:8]
            
            for producto in electrodomesticos:
                items = crear_items_individuales(producto)
                electrodomesticos_data.extend(items)
        except:
            pass

        # =============================================
        # TECNOLOGÍA (INDIVIDUALES)
        # =============================================
        tecnologia_data = []
        try:
            categorias_tecnologia = [1, 2, 3, 4, 33]
            
            tecnologia = Productos.objects.filter(
                estado_prod='disponible',
                fkcategoria_prod__in=categorias_tecnologia
            ).order_by('-precio_prod')[:8]
            
            for producto in tecnologia:
                items = crear_items_individuales(producto)
                tecnologia_data.extend(items)
        except:
            pass

        # =============================================
        # PRODUCTOS BARATOS (INDIVIDUALES)
        # =============================================
        productos_baratos_data = []
        try:
            productos_baratos = Productos.objects.filter(
                estado_prod='disponible',
                precio_prod__lte=50000
            ).order_by('precio_prod')[:12]
            
            for producto in productos_baratos:
                items = crear_items_individuales(producto)
                productos_baratos_data.extend(items)
        except:
            pass

        # =============================================
        # PRODUCTOS DESTACADOS (INDIVIDUALES)
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
                    items = crear_items_individuales(producto)
                    
                    # Agregar total vendido a cada item
                    for item_data in items:
                        item_data['total_vendido'] = item['total_vendido']
                    
                    productos_destacados_data.extend(items)
                except:
                    continue
        except:
            pass

        # =============================================
        # PRODUCTOS EN OFERTA (INDIVIDUALES)
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
                        vp.imagen_variante, vp.id_variante,
                        p.stock_actual_oferta, p.activa_por_stock
                    FROM promociones p
                    INNER JOIN productos pr ON p.fkproducto_id = pr.pkid_prod
                    LEFT JOIN variantes_producto vp ON p.variante_id = vp.id_variante AND vp.producto_id = pr.pkid_prod
                    WHERE pr.estado_prod = 'disponible'
                    AND p.estado_promo = 'activa'
                    AND p.fecha_inicio <= %s
                    AND p.fecha_fin >= %s
                    AND p.porcentaje_descuento > 0
                    AND (
                        (p.activa_por_stock = 1 AND p.stock_actual_oferta > 0) OR
                        (p.activa_por_stock = 0 AND (
                            (p.variante_id IS NULL AND pr.stock_prod > 0) OR 
                            (p.variante_id IS NOT NULL AND vp.stock_variante > 0)
                        ))
                    )
                    ORDER BY p.porcentaje_descuento DESC
                    LIMIT 12
                """, [hoy, hoy])
                
                productos_oferta_rows = cursor.fetchall()
                
                for row in productos_oferta_rows:
                    try:
                        producto_id = row[4]
                        producto = Productos.objects.get(pkid_prod=producto_id)
                        
                        # Crear items individuales para este producto
                        items = crear_items_individuales(producto)
                        
                        # Filtrar solo los items que tienen oferta activa
                        for item in items:
                            if item['tiene_oferta']:
                                item['pkid_promo'] = row[0]
                                item['titulo_promo'] = row[1]
                                productos_oferta_data.append(item)
                                
                    except:
                        continue
        except:
            pass

        # =============================================
        # NEGOCIOS DESTACADOS
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
                    
                except:
                    continue
        except:
            pass

        # =============================================
        # OTROS NEGOCIOS
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
                    
                except:
                    continue
        except:
            pass

        # =============================================
        # CONTADORES
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
        except:
            pass

        pedidos_pendientes_count = 0
        try:
            pedidos_pendientes_count = Pedidos.objects.filter(
                fkusuario_pedido=perfil_cliente,
                estado_pedido__in=['pendiente', 'confirmado', 'preparando']
            ).count()
        except:
            pass

        # =============================================
        # CONTEXT FINAL
        # =============================================
        context = {
            'perfil': perfil_cliente,
            'carrito_count': carrito_count,
            'favoritos_count': favoritos_count,
            'pedidos_pendientes_count': pedidos_pendientes_count,
            
            # Secciones con items individuales
            'ofertas_carrusel': ofertas_carrusel_data,
            'productos_baratos': productos_baratos_data[:12],
            'productos_destacados': productos_destacados_data[:12],
            'productos_oferta': productos_oferta_data[:12],
            'negocios_destacados': negocios_destacados_data,
            'otros_negocios': otros_negocios_data,
            
            # Secciones con fecha especial
            'fecha_especial': fecha_especial,
            'mensaje_especial': mensaje_especial,
            'productos_fecha_especial': productos_fecha_especial_data[:10],
            'electrodomesticos': electrodomesticos_data[:8],
            'tecnologia': tecnologia_data[:8],
            
            # Secciones de combos
            'combos_activos': combos_activos,
            'promociones_2x1': promociones_2x1,
            'ofertas_especiales': ofertas_especiales,
            
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
            'hay_combos_activos': len(combos_activos) > 0,
            'hay_promociones_2x1': len(promociones_2x1) > 0,
            'hay_ofertas_especiales': len(ofertas_especiales) > 0,
        }
        
        return render(request, 'Cliente/Cliente.html', context)
        
    except Exception as e:
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
            'combos_activos': [],
            'promociones_2x1': [],
            'ofertas_especiales': [],
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
            'hay_combos_activos': False,
            'hay_promociones_2x1': False,
            'hay_ofertas_especiales': False,
        })        

@csrf_exempt
@login_required
def agregar_combo_carrito(request):
    """Agrega un combo al carrito"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            combo_id = data.get('combo_id')
            cantidad = int(data.get('cantidad', 1))
            
            # Verificar que el usuario esté autenticado
            perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
            
            # Obtener el combo
            try:
                combo = Combos.objects.get(pkid_combo=combo_id, estado_combo='activo')
            except Combos.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Combo no encontrado o no disponible'})
            
            # Verificar stock del combo
            if combo.stock_combo < cantidad:
                return JsonResponse({'success': False, 'error': 'Stock insuficiente'})
            
            # Verificar stock de cada producto del combo
            items_combo = ComboItems.objects.filter(fkcombo=combo)
            for item in items_combo:
                if item.variante:
                    stock_disponible = item.variante.stock_variante or 0
                else:
                    stock_disponible = item.fkproducto.stock_prod or 0
                
                if stock_disponible < (item.cantidad * cantidad):
                    return JsonResponse({
                        'success': False, 
                        'error': f'Stock insuficiente para {item.fkproducto.nom_prod}'
                    })
            
            # Obtener o crear carrito
            carrito, created = Carrito.objects.get_or_create(
                fkusuario_carrito=perfil_cliente
            )
            
            # Verificar si ya existe el combo en el carrito
            item_existente = CarritoItem.objects.filter(
                fkcarrito=carrito,
                fkcombo_id=combo_id,
                tipo_item='combo'
            ).first()
            
            if item_existente:
                # Actualizar cantidad
                nueva_cantidad = item_existente.cantidad + cantidad
                if nueva_cantidad > combo.stock_combo:
                    return JsonResponse({'success': False, 'error': 'Stock insuficiente'})
                
                item_existente.cantidad = nueva_cantidad
                item_existente.save()
                
                mensaje = f'Cantidad actualizada: {item_existente.cantidad}'
            else:
                # Crear nuevo item de combo
                nuevo_item = CarritoItem.objects.create(
                    fkcarrito=carrito,
                    fkcombo=combo,
                    fknegocio=combo.fknegocio,
                    cantidad=cantidad,
                    precio_unitario=combo.precio_combo,
                    tipo_item='combo',
                    variante_seleccionada='Combo completo'
                )
                mensaje = 'Combo agregado al carrito'
            
            # Actualizar contador del carrito
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
            
            return JsonResponse({
                'success': True,
                'message': mensaje,
                'carrito_count': carrito_count
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@csrf_exempt
@login_required
def agregar_promocion_2x1_carrito(request):
    """Agrega una promoción 2x1 al carrito"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            promocion_id = data.get('promocion_id')
            cantidad_pares = int(data.get('cantidad', 1))  # Cantidad de pares (2x1)
            
            # Verificar que el usuario esté autenticado
            perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
            
            # Obtener la promoción
            try:
                promocion = Promociones2x1.objects.get(
                    pkid_promo_2x1=promocion_id, 
                    estado='activa'
                )
            except Promociones2x1.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Promoción no encontrada o no disponible'})
            
            # Calcular cantidad total (cada par es 2 productos)
            cantidad_total = cantidad_pares * 2
            
            # Verificar stock
            if promocion.variante:
                stock_disponible = promocion.variante.stock_variante or 0
                producto = promocion.fkproducto
                variante = promocion.variante
                precio_base = float(producto.precio_prod) if producto.precio_prod else 0
                precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                precio_total = precio_base + precio_adicional
                nombre_producto = f"{producto.nom_prod} - {variante.nombre_variante}"
                variante_id = variante.id_variante
            else:
                stock_disponible = promocion.fkproducto.stock_prod or 0
                producto = promocion.fkproducto
                precio_total = float(producto.precio_prod) if producto.precio_prod else 0
                nombre_producto = producto.nom_prod
                variante_id = None
            
            if stock_disponible < cantidad_total:
                return JsonResponse({'success': False, 'error': 'Stock insuficiente'})
            
            # Calcular precio con descuento 2x1 (paga 1, lleva 2)
            precio_unitario_oferta = precio_total / 2
            precio_final = precio_unitario_oferta * cantidad_total
            
            # Obtener o crear carrito
            carrito, created = Carrito.objects.get_or_create(
                fkusuario_carrito=perfil_cliente
            )
            
            # Para promociones 2x1, se agrega como producto normal pero con precio especial
            # Podrías crear un tipo especial o manejarlo diferente según tu lógica
            
            # Por ahora, lo agregamos como producto normal con descuento
            item_existente = None
            if variante_id:
                item_existente = CarritoItem.objects.filter(
                    fkcarrito=carrito,
                    fkproducto=producto,
                    variante_id=variante_id,
                    tipo_item='producto'
                ).first()
            else:
                item_existente = CarritoItem.objects.filter(
                    fkcarrito=carrito,
                    fkproducto=producto,
                    tipo_item='producto',
                    variante_id__isnull=True
                ).first()
            
            if item_existente:
                # Actualizar cantidad
                nueva_cantidad = item_existente.cantidad + cantidad_total
                if nueva_cantidad > stock_disponible:
                    return JsonResponse({'success': False, 'error': 'Stock insuficiente'})
                
                item_existente.cantidad = nueva_cantidad
                # Actualizar precio si aplica la promoción
                if item_existente.precio_unitario != precio_unitario_oferta:
                    item_existente.precio_unitario = precio_unitario_oferta
                item_existente.save()
                
                mensaje = f'Cantidad actualizada: {item_existente.cantidad}'
            else:
                # Crear nuevo item
                nuevo_item = CarritoItem.objects.create(
                    fkcarrito=carrito,
                    fkproducto=producto,
                    fknegocio=promocion.fknegocio,
                    cantidad=cantidad_total,
                    precio_unitario=precio_unitario_oferta,
                    tipo_item='producto',
                    variante_id=variante_id,
                    variante_seleccionada=nombre_producto if variante_id else None
                )
                mensaje = 'Promoción 2x1 agregada al carrito'
            
            # Actualizar contador del carrito
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
            
            return JsonResponse({
                'success': True,
                'message': mensaje,
                'carrito_count': carrito_count
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@never_cache
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

@never_cache
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

@never_cache
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

# =============================================================================
# FUNCIONES DE UTILIDAD PARA STOCK (SIN @never_cache)
# =============================================================================

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
    
@never_cache
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

@never_cache         
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

@never_cache    
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

@never_cache
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
            
            # Manejar caso donde precio_prod podría ser None
            precio_base = float(item.fkproducto.precio_prod) if item.fkproducto.precio_prod else 0
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
            
            precio_actual = float(item.precio_unitario) if item.precio_unitario else 0
            subtotal = precio_actual * item.cantidad
            
            tiene_oferta = precio_actual < precio_original
            ahorro_item = (precio_original - precio_actual) * item.cantidad if tiene_oferta else 0
            
            # Evitar división por cero
            if precio_original > 0:
                descuento_porcentaje = ((precio_original - precio_actual) / precio_original * 100)
            else:
                descuento_porcentaje = 0
            
            items_detallados.append({
                'item': item,
                'imagen': imagen_producto,
                'subtotal': subtotal,
                'tiene_oferta': tiene_oferta,
                'precio_original': precio_original,
                'precio_actual': precio_actual,
                'descuento_porcentaje': descuento_porcentaje,
                'ahorro': ahorro_item,
                'nombre_completo': f"{item.fkproducto.nom_prod} - {item.variante_seleccionada}" if item.variante_seleccionada else item.fkproducto.nom_prod,
                'negocio_nombre': item.fknegocio.nom_neg if item.fknegocio else 'Vecy',
                'cantidad': item.cantidad,
                'id': item.pkid_item,
                'es_variante': bool(item.variante_id),
                'variante_nombre': item.variante_seleccionada,
                'stock_disponible': item.fkproducto.stock_prod or 0
            })
            
            total_carrito += subtotal
            if tiene_oferta:
                ahorro_total += ahorro_item
        
        context = {
            'items_carrito': items_detallados,
            'total_carrito': total_carrito,
            'ahorro_total': ahorro_total,
            'carrito_count': len(items_carrito),
            'carrito_vacio': len(items_carrito) == 0,
            'perfil_cliente': perfil_cliente
        }
        
        # Si es una petición AJAX, devolver JSON para carga dinámica
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'items': items_detallados,
                'totales': {
                    'subtotal': total_carrito,
                    'ahorro_total': ahorro_total,
                    'total': total_carrito
                },
                'carrito_count': len(items_carrito)
            })
        
        # Si es petición normal, renderizar página completa
        return render(request, 'Cliente/carrito.html', context)
        
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, 'Debes completar tu perfil para acceder al carrito')
        return redirect('completar_perfil')
    
    except Exception as e:
        # Log del error para debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error en ver_carrito: {str(e)}")
        
        # Si es AJAX, devolver error en JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Ocurrió un error al cargar el carrito'
            })
        
        # Devolver carrito vacío en caso de error
        return render(request, 'Cliente/carrito.html', {
            'items_carrito': [],
            'total_carrito': 0,
            'ahorro_total': 0,
            'carrito_count': 0,
            'carrito_vacio': True,
            'error': 'Ocurrió un error al cargar el carrito'
        })
        
@never_cache
@login_required(login_url='/auth/login/')
def carrito_data(request):
    """API para obtener datos del carrito - AHORA INCLUYE COMBOS"""
    try:
        print("🔄 carrito_data: Iniciando...")
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        print(f"👤 Perfil cliente: {perfil_cliente.pk}")
        
        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
        print(f"🛒 Carrito: {carrito.pkid_carrito}, Creado: {created}")
        
        # Obtener items del carrito incluyendo combos
        items = CarritoItem.objects.filter(fkcarrito=carrito).select_related(
            'fkproducto', 'fknegocio', 'fkcombo'
        )
        print(f"📦 Items en carrito: {items.count()}")
        
        carrito_items = []
        subtotal = 0
        ahorro_total = 0
        hoy = timezone.now().date()
        items_a_eliminar = []  # Items con productos nulos que debemos eliminar

        for item in items:
            print(f"  📋 Procesando item: {item.pkid_item} - Tipo: {item.tipo_item}")
            
            # ==================== MANEJAR COMBOS ====================
            if item.tipo_item == 'combo' and item.fkcombo:
                print(f"    🎁 Procesando COMBO: {item.fkcombo.nombre_combo}")
                
                # Verificar que el combo esté activo
                if item.fkcombo.estado_combo != 'activo':
                    print(f"    ⚠️ Combo inactivo, marcando para eliminación: Combo {item.fkcombo.pkid_combo}")
                    items_a_eliminar.append(item.pkid_item)
                    continue
                
                # Verificar stock del combo
                if item.fkcombo.stock_combo < item.cantidad:
                    print(f"    ⚠️ Stock insuficiente para combo: Stock {item.fkcombo.stock_combo}, Cantidad {item.cantidad}")
                
                # Obtener imagen del combo (primera imagen de los productos o imagen por defecto)
                imagen_combo = None
                try:
                    # Intentar obtener imagen del primer producto del combo
                    items_combo = ComboItems.objects.filter(fkcombo=item.fkcombo).first()
                    if items_combo and items_combo.fkproducto and items_combo.fkproducto.img_prod:
                        imagen_combo = items_combo.fkproducto.img_prod.url
                except:
                    pass
                
                if not imagen_combo:
                    imagen_combo = 'https://via.placeholder.com/80x80/4a90e2/ffffff?text=COMBO'
                
                # Calcular precio
                precio_combo = float(item.fkcombo.precio_combo) if item.fkcombo.precio_combo else 0
                precio_original = precio_combo
                precio_actual = float(item.precio_unitario) if item.precio_unitario else precio_combo
                tiene_oferta = precio_actual < precio_original
                ahorro_item = (precio_original - precio_actual) * item.cantidad if tiene_oferta else 0
                
                # Obtener productos del combo para mostrar
                productos_combo = []
                try:
                    combo_items = ComboItems.objects.filter(fkcombo=item.fkcombo).select_related('fkproducto')
                    for combo_item in combo_items[:3]:  # Mostrar solo primeros 3 productos
                        productos_combo.append({
                            'nombre': combo_item.fkproducto.nom_prod,
                            'cantidad': combo_item.cantidad,
                            'variante': combo_item.variante.nombre_variante if combo_item.variante else None
                        })
                except:
                    pass
                
                item_data = {
                    'id': item.pkid_item,
                    'nombre': item.fkcombo.nombre_combo,
                    'negocio': item.fknegocio.nom_neg if item.fknegocio else item.fkcombo.fknegocio.nom_neg,
                    'cantidad': item.cantidad,
                    'precio_unitario': precio_actual,
                    'precio_original': precio_original,
                    'tiene_oferta': tiene_oferta,
                    'imagen': imagen_combo,
                    'variante': 'Combo completo',
                    'es_variante': False,
                    'es_combo': True,
                    'combo_id': item.fkcombo.pkid_combo,
                    'productos_combo': productos_combo,
                    'descripcion_combo': item.fkcombo.descripcion_combo,
                    'stock_disponible': item.fkcombo.stock_combo or 0,
                    'ahorro_item': ahorro_item,
                    'producto_id': None,
                }
                
                print(f"    ✅ Combo procesado: {item_data['nombre']} - ${item_data['precio_unitario']} x {item_data['cantidad']}")
                
                carrito_items.append(item_data)
                subtotal += precio_actual * item.cantidad
                if tiene_oferta:
                    ahorro_total += ahorro_item
                continue
            
            # ==================== MANEJAR PRODUCTOS INDIVIDUALES ====================
            print(f"    🛍️ Procesando PRODUCTO: Item {item.pkid_item}")
            
            # CRÍTICO: Verificar si el producto existe
            if not item.fkproducto:
                print(f"    ⚠️ Producto NULO encontrado, marcando para eliminación: Item {item.pkid_item}")
                items_a_eliminar.append(item.pkid_item)
                continue
            
            print(f"    ✅ Producto: {item.fkproducto.nom_prod}")
            
            # Nombre completo
            nombre_completo = item.fkproducto.nom_prod
            if item.variante_seleccionada:
                nombre_completo = f"{item.fkproducto.nom_prod} - {item.variante_seleccionada}"
            
            # Precio base - manejar None
            precio_base = 0
            try:
                precio_base = float(item.fkproducto.precio_prod) if item.fkproducto.precio_prod else 0
            except (TypeError, ValueError):
                precio_base = 0
                
            precio_original = precio_base
            
            # Stock disponible
            stock_disponible = item.fkproducto.stock_prod or 0 if item.fkproducto else 0
            
            # Imagen
            imagen_producto = None
            if item.fkproducto and item.fkproducto.img_prod:
                try:
                    imagen_producto = item.fkproducto.img_prod.url
                except:
                    imagen_producto = None
            
            # Manejo de variantes
            if item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(id_variante=item.variante_id)
                    if variante.precio_adicional:
                        try:
                            precio_original += float(variante.precio_adicional)
                            precio_base += float(variante.precio_adicional)
                        except (TypeError, ValueError):
                            pass
                    stock_disponible = variante.stock_variante or 0
                    
                    if variante.imagen_variante:
                        try:
                            imagen_producto = variante.imagen_variante.url
                        except:
                            pass
                        
                except VariantesProducto.DoesNotExist:
                    print(f"    ⚠️ Variante {item.variante_id} no encontrada")
            
            # Precio actual del carrito
            precio_actual = 0
            try:
                precio_actual = float(item.precio_unitario) if item.precio_unitario else 0
            except (TypeError, ValueError):
                precio_actual = 0
            
            # Verificar ofertas - solo si el producto existe
            tiene_oferta = False
            ahorro_item = 0
            
            if item.fkproducto:
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
                                print(f"    🔥 Tiene oferta: {descuento_porcentaje}%")
                        except (ValueError, TypeError):
                            pass
            
            # Si no tiene oferta activa pero el precio es menor al original
            if not tiene_oferta and precio_actual < precio_original:
                tiene_oferta = True
                ahorro_item = (precio_original - precio_actual) * item.cantidad
            
            # Verificar negocio
            negocio_nombre = 'Tienda Vecy'
            if item.fknegocio:
                negocio_nombre = item.fknegocio.nom_neg
            elif item.fkproducto and item.fkproducto.fknegocioasociado_prod:
                negocio_nombre = item.fkproducto.fknegocioasociado_prod.nom_neg
            
            item_data = {
                'id': item.pkid_item,
                'nombre': nombre_completo,
                'negocio': negocio_nombre,
                'cantidad': item.cantidad,
                'precio_unitario': precio_actual,
                'precio_original': precio_original,
                'tiene_oferta': tiene_oferta,
                'imagen': imagen_producto,
                'variante': item.variante_seleccionada,
                'es_variante': bool(item.variante_id),
                'es_combo': False,
                'stock_disponible': stock_disponible,
                'ahorro_item': ahorro_item,
                'producto_id': item.fkproducto.pkid_prod if item.fkproducto else None,
            }
            
            print(f"    ✅ Item procesado: {item_data['nombre']} - ${item_data['precio_unitario']} x {item_data['cantidad']}")
            
            carrito_items.append(item_data)
            
            subtotal += precio_actual * item.cantidad
            if tiene_oferta:
                ahorro_total += ahorro_item
        
        # Eliminar items con productos nulos o combos inactivos
        if items_a_eliminar:
            print(f"🗑️ Eliminando {len(items_a_eliminar)} items inválidos...")
            CarritoItem.objects.filter(pkid_item__in=items_a_eliminar).delete()
            print("✅ Items eliminados")
        
        print(f"💰 Subtotal: ${subtotal}")
        print(f"🎯 Ahorro total: ${ahorro_total}")
        print(f"📊 Total items válidos: {len(carrito_items)}")
        print(f"🎁 Combos en carrito: {sum(1 for item in carrito_items if item.get('es_combo'))}")
        
        response_data = {
            'success': True,
            'items': carrito_items,
            'totales': {
                'subtotal': subtotal,
                'ahorro_total': ahorro_total,
                'total': subtotal
            },
            'carrito_count': len(carrito_items),
            'items_eliminados': len(items_a_eliminar),
            'debug': {
                'usuario': request.user.username,
                'items_validos': len(carrito_items),
                'items_invalidos': len(items_a_eliminar),
                'combos_count': sum(1 for item in carrito_items if item.get('es_combo')),
                'timestamp': timezone.now().isoformat()
            }
        }
        
        print("✅ carrito_data: Datos preparados, enviando respuesta...")
        return JsonResponse(response_data)
        
    except UsuarioPerfil.DoesNotExist:
        print("❌ carrito_data: UsuarioPerfil no encontrado")
        return JsonResponse({
            'success': False, 
            'error': 'Perfil de usuario no encontrado'
        })
    except Exception as e:
        print(f"❌ carrito_data: Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': 'Error interno del servidor'
        })

import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.db import connection
from ..models import *

# Configurar logger
logger = logging.getLogger(__name__)

@never_cache
@login_required(login_url='/auth/login/')
def producto_detalle_logeado(request, id):
    try:
        # Obtener perfil del usuario (CRÍTICO para el sistema de carrito)
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # Obtener el producto principal
        producto = get_object_or_404(Productos, pkid_prod=id)
        
        # =============================================
        # OBTENER DATOS DEL CARRITO - ¡ESTO ES CRÍTICO!
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
        except Exception as e:
            print(f"Error obteniendo datos carrito/favoritos: {str(e)}")
            carrito_count = 0
            favoritos_count = 0
        
        # =============================================
        # FUNCIÓN PARA BUSCAR OFERTAS (igual que dashboard)
        # =============================================
        def obtener_info_oferta(producto_id, variante_id=None):
            hoy = timezone.now().date()
            try:
                with connection.cursor() as cursor:
                    if variante_id:
                        cursor.execute("""
                            SELECT p.porcentaje_descuento, p.pkid_promo, p.variante_id, 
                                   p.stock_actual_oferta, p.stock_inicial_oferta, p.activa_por_stock
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
                            stock_oferta = result[3] if result[5] == 1 else None
                            return {
                                'porcentaje_descuento': float(result[0]),
                                'pkid_promo': result[1],
                                'variante_id': result[2],
                                'stock_oferta': stock_oferta,
                                'activa_por_stock': result[5],
                                'es_oferta_especifica': True,
                                'tiene_oferta': True
                            }
                    
                    if variante_id is None:
                        cursor.execute("""
                            SELECT p.porcentaje_descuento, p.pkid_promo, p.variante_id,
                                   p.stock_actual_oferta, p.stock_inicial_oferta, p.activa_por_stock
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
                            stock_oferta = result[3] if result[5] == 1 else None
                            return {
                                'porcentaje_descuento': float(result[0]),
                                'pkid_promo': result[1],
                                'variante_id': result[2],
                                'stock_oferta': stock_oferta,
                                'activa_por_stock': result[5],
                                'es_oferta_especifica': False,
                                'tiene_oferta': True
                            }
                    
                    return None
            except:
                return None
        
        # =============================================
        # OBTENER Y PROCESAR VARIANTES
        # =============================================
        variantes = VariantesProducto.objects.filter(
            producto=producto,
            estado_variante='activa'
        ).select_related('producto')
        
        variantes_data = []
        
        for variante in variantes:
            # Precio base del producto
            precio_base = float(producto.precio_prod) if producto.precio_prod else 0.0
            
            # Precio adicional de la variante
            precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0.0
            
            # Stock de la variante
            stock_variante = int(variante.stock_variante) if variante.stock_variante else 0
            
            # Precio total de la variante
            precio_total_variante = precio_base + precio_adicional
            
            # Buscar ofertas
            info_oferta = obtener_info_oferta(producto.pkid_prod, variante.id_variante)
            
            if info_oferta and info_oferta['tiene_oferta']:
                descuento = info_oferta['porcentaje_descuento']
                ahorro = precio_total_variante * (descuento / 100)
                precio_final = precio_total_variante - ahorro
                
                # Manejar stock si la oferta tiene stock limitado
                if info_oferta.get('activa_por_stock') == 1:
                    stock_oferta = info_oferta.get('stock_oferta')
                    if stock_oferta is not None:
                        stock_variante = min(stock_variante, stock_oferta)
            else:
                # Verificar si hay oferta general del producto
                info_oferta_general = obtener_info_oferta(producto.pkid_prod)
                if info_oferta_general and info_oferta_general['tiene_oferta']:
                    descuento = info_oferta_general['porcentaje_descuento']
                    ahorro = precio_total_variante * (descuento / 100)
                    precio_final = precio_total_variante - ahorro
                    
                    if info_oferta_general.get('activa_por_stock') == 1:
                        stock_oferta = info_oferta_general.get('stock_oferta')
                        if stock_oferta is not None:
                            stock_variante = min(stock_variante, stock_oferta)
                else:
                    descuento = 0
                    ahorro = 0
                    precio_final = precio_total_variante
            
            # Formatear precios
            def formatear_precio(valor):
                try:
                    if valor is None:
                        return "0.00"
                    valor_float = float(valor)
                    return "{:,.2f}".format(valor_float).replace(',', 'X').replace('.', ',').replace('X', '.')
                except (ValueError, TypeError):
                    return "0.00"
            
            # Determinar estado de stock
            if stock_variante > 10:
                estado_stock = 'in-stock'
            elif stock_variante > 0:
                estado_stock = 'low-stock'
            else:
                estado_stock = 'out-stock'
            
            # Obtener imagen de la variante
            imagen_variante = None
            try:
                if hasattr(variante, 'imagen_variante') and variante.imagen_variante:
                    imagen_variante = variante.imagen_variante.url
                elif producto.img_prod and hasattr(producto.img_prod, 'url'):
                    imagen_variante = producto.img_prod.url
            except:
                imagen_variante = None
            
            variante_data = {
                'pkid_variante': variante.id_variante,
                'nombre_variante': variante.nombre_variante,
                'precio_adicional': precio_adicional,
                'precio_base': precio_total_variante,
                'precio_final': round(precio_final, 0),
                'precio_final_formateado': formatear_precio(precio_final),
                'stock_disponible': stock_variante,
                'stock_real': stock_variante,
                'imagen': imagen_variante,
                'sku_variante': variante.sku_variante or f"{producto.pkid_prod}-{variante.id_variante}",
                'estado_stock': estado_stock,
                'tiene_oferta': descuento > 0,
                'porcentaje_descuento': descuento,
                'ahorro': round(ahorro, 0),
            }
            
            variantes_data.append(variante_data)
        
        # =============================================
        # PROCESAR PRODUCTO BASE
        # =============================================
        precio_base = float(producto.precio_prod) if producto.precio_prod else 0.0
        stock_producto = producto.stock_prod or 0
        
        # Buscar oferta para el producto base
        info_oferta_producto = obtener_info_oferta(producto.pkid_prod)
        
        if info_oferta_producto and info_oferta_producto['tiene_oferta']:
            descuento_producto = info_oferta_producto['porcentaje_descuento']
            ahorro_producto = precio_base * (descuento_producto / 100)
            precio_final_producto = precio_base - ahorro_producto
            
            # Manejar stock limitado
            if info_oferta_producto.get('activa_por_stock') == 1:
                stock_oferta = info_oferta_producto.get('stock_oferta')
                if stock_oferta is not None:
                    stock_producto = min(stock_producto, stock_oferta)
        else:
            descuento_producto = 0
            ahorro_producto = 0
            precio_final_producto = precio_base
        
        # Determinar estado de stock del producto base
        if stock_producto > 10:
            estado_stock_producto = 'in-stock'
        elif stock_producto > 0:
            estado_stock_producto = 'low-stock'
        else:
            estado_stock_producto = 'out-stock'
        
        # =============================================
        # OBTENER PRODUCTOS RELACIONADOS
        # =============================================
        productos_similares = []
        productos_vistos = []
        
        try:
            # Productos similares
            productos_similares = Productos.objects.filter(
                fkcategoria_prod=producto.fkcategoria_prod,
                estado_prod='disponible'
            ).exclude(
                pkid_prod=producto.pkid_prod
            )[:4]
            
            # Productos vistos
            productos_vistos_ids = request.session.get('productos_vistos', [])
            if productos_vistos_ids:
                productos_vistos = Productos.objects.filter(
                    pkid_prod__in=productos_vistos_ids
                ).exclude(
                    pkid_prod=producto.pkid_prod
                )[:4]
            
            # Agregar este producto a los vistos
            if 'productos_vistos' not in request.session:
                request.session['productos_vistos'] = []
            
            if id not in request.session['productos_vistos']:
                request.session['productos_vistos'].insert(0, id)
                if len(request.session['productos_vistos']) > 10:
                    request.session['productos_vistos'] = request.session['productos_vistos'][:10]
                request.session.modified = True
                
        except Exception as e:
            print(f"Error obteniendo productos relacionados: {str(e)}")
        
        # =============================================
        # FUNCIÓN PARA FORMATEAR PRECIOS
        # =============================================
        def formatear_precio_context(valor):
            try:
                if valor is None:
                    return "0.00"
                valor_float = float(valor)
                return "{:,.2f}".format(valor_float).replace(',', 'X').replace('.', ',').replace('X', '.')
            except (ValueError, TypeError):
                return "0.00"
        
        # =============================================
        # CONTEXTO COMPLETO - ¡INCLUYE VARIABLES DEL CARRITO!
        # =============================================
        context = {
            'producto': producto,
            'variantes': variantes_data,
            'precio_original': precio_base,
            'precio_original_formateado': formatear_precio_context(precio_base),
            'precio_final': round(precio_final_producto, 0),
            'precio_final_formateado': formatear_precio_context(precio_final_producto),
            'stock_disponible': stock_producto,
            'estado_stock': estado_stock_producto,
            'porcentaje_descuento': descuento_producto,
            'ahorro': round(ahorro_producto, 0),
            'ahorro_formateado': formatear_precio_context(ahorro_producto),
            'imagen_inicial': producto.img_prod.url if producto.img_prod and hasattr(producto.img_prod, 'url') else '',
            'productos_similares': productos_similares,
            'productos_vistos': productos_vistos,
            'negocio': producto.fknegocioasociado_prod,
            
            # ¡¡¡CRÍTICO: VARIABLES DEL SISTEMA DE CARRITO!!!
            'carrito_count': carrito_count,
            'favoritos_count': favoritos_count,
            'perfil': perfil_cliente,  # También el perfil para que funcione el sistema
            
            # Variables para pedidos (si tu sistema los usa)
            'pedidos_pendientes_count': 0,  # Puedes calcular esto si lo necesitas
            
            # Variables para compatibilidad con dashboard
            'hay_ofertas_activas': descuento_producto > 0,
            'hay_productos_similares': len(productos_similares) > 0,
            'hay_variantes': len(variantes_data) > 0,
        }
        
        return render(request, 'cliente/producto_detalle.html', context)
        
    except Exception as e:
        print(f"Error en producto_detalle_logeado: {str(e)}")
        
        # Contexto de error pero con variables del carrito
        try:
            perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
            carrito_count = CarritoItem.objects.filter(
                fkcarrito__fkusuario_carrito=perfil_cliente
            ).count()
            favoritos_count = Favoritos.objects.filter(
                fkusuario=perfil_cliente
            ).count()
        except:
            carrito_count = 0
            favoritos_count = 0
        
        context = {
            'error': str(e),
            'carrito_count': carrito_count,
            'favoritos_count': favoritos_count,
            'perfil': perfil_cliente if 'perfil_cliente' in locals() else None,
        }
        
        return render(request, 'cliente/error_producto.html', context)
     
@login_required(login_url='/auth/login/')
@require_POST
@csrf_exempt
def procesar_pedido(request):
    try:
        print("=== INICIANDO PROCESO DE PEDIDO ===")
        
        # Obtener hora actual (Django ya maneja la conversión a zona local)
        from django.utils import timezone
        
        # Esta hora ya debería estar en Colombia porque TIME_ZONE = 'America/Bogota'
        fecha_actual = timezone.localtime(timezone.now())
        print(f"Hora Colombia (desde Django): {fecha_actual}")
        
        # Convertir a formato sin timezone para MySQL
        fecha_mysql = fecha_actual.replace(tzinfo=None)
        print(f"Hora para MySQL: {fecha_mysql}")
        
        # 1. Validar que sea una solicitud JSON
        if request.content_type != 'application/json':
            return JsonResponse({
                'success': False, 
                'message': 'Content-Type debe ser application/json'
            }, status=400)
        
        # 2. Parsear JSON
        try:
            data = json.loads(request.body)
            print(f"Datos recibidos: {data}")
        except json.JSONDecodeError as e:
            print(f"Error JSON: {str(e)}")
            return JsonResponse({
                'success': False, 
                'message': 'Error en el formato de datos JSON'
            }, status=400)
        
        # 3. Verificar datos mínimos
        if 'metodo_pago' not in data:
            return JsonResponse({
                'success': False, 
                'message': 'Método de pago requerido'
            }, status=400)
        
        auth_user = request.user
        print(f"Usuario autenticado: {auth_user.username} ({auth_user.id})")
        
        # 4. Obtener perfil del cliente
        try:
            perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
            print(f"Perfil cliente obtenido: ID {perfil_cliente.pk}")
        except UsuarioPerfil.DoesNotExist:
            print("ERROR: UsuarioPerfil no encontrado")
            return JsonResponse({
                'success': False, 
                'message': 'Perfil de usuario no encontrado. Complete su perfil.'
            }, status=404)
        
        # 5. Obtener carrito del usuario
        try:
            carrito, created = Carrito.objects.get_or_create(
                fkusuario_carrito=perfil_cliente
            )
            print(f"Carrito obtenido/creado: ID {carrito.pkid_carrito}, Creado: {created}")
        except Exception as e:
            print(f"ERROR al obtener/crear carrito: {str(e)}")
            return JsonResponse({
                'success': False, 
                'message': f'Error al acceder al carrito: {str(e)}'
            }, status=500)
        
        # 6. Obtener items del carrito
        try:
            items_carrito = CarritoItem.objects.filter(fkcarrito=carrito)
            items_count = items_carrito.count()
            print(f"Items en carrito: {items_count}")
            
            if items_count == 0:
                return JsonResponse({
                    'success': False, 
                    'message': 'El carrito está vacío'
                }, status=400)
                
        except Exception as e:
            print(f"ERROR al obtener items del carrito: {str(e)}")
            return JsonResponse({
                'success': False, 
                'message': f'Error al obtener items del carrito: {str(e)}'
            }, status=500)
        
        # 7. Validar stock y calcular total
        total_pedido = 0
        negocios_involucrados = {}
        items_detallados = []
        
        try:
            for item_carrito in items_carrito:
                print(f"Procesando item: {item_carrito.pkid_item} - Producto: {item_carrito.fkproducto.nom_prod}")
                
                # Validar stock para producto base o variante
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
                
                # Calcular monto del item
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
                
            print(f"Total pedido calculado: {total_pedido}")
            print(f"Negocios involucrados: {len(negocios_involucrados)}")
            
        except Exception as e:
            print(f"ERROR al validar stock/calcular total: {str(e)}")
            return JsonResponse({
                'success': False, 
                'message': f'Error al validar stock: {str(e)}'
            }, status=500)
        
        # 8. Determinar negocio principal (mayor monto)
        try:
            negocio_principal = None
            mayor_monto = 0
            
            for negocio, monto in negocios_involucrados.items():
                if monto > mayor_monto:
                    mayor_monto = monto
                    negocio_principal = negocio
            
            if not negocio_principal:
                return JsonResponse({
                    'success': False, 
                    'message': 'No se pudo determinar el negocio principal'
                }, status=500)
                
            print(f"Negocio principal: {negocio_principal.nom_neg} (ID: {negocio_principal.pkid_neg})")
            
        except Exception as e:
            print(f"ERROR al determinar negocio principal: {str(e)}")
            return JsonResponse({
                'success': False, 
                'message': f'Error al determinar negocio principal: {str(e)}'
            }, status=500)
        
        # 9. Crear pedido en la base de datos
        try:
            # Usar la fecha/hora Colombia que preparamos
            pedido_fecha = fecha_mysql
            
            # Insertar con SQL directo para control total
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO pedidos (
                        fkusuario_pedido, fknegocio_pedido, estado_pedido, 
                        total_pedido, metodo_pago, metodo_pago_texto, banco,
                        fecha_pedido, fecha_actualizacion
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql, [
                    perfil_cliente.pk,
                    negocio_principal.pk,
                    'pendiente',
                    float(total_pedido),
                    data.get('metodo_pago', ''),
                    data.get('metodo_pago_texto', '').strip(),
                    data.get('banco', ''),
                    pedido_fecha,  # Hora Colombia
                    pedido_fecha   # Hora Colombia
                ])
                
                pedido_id = cursor.lastrowid
            
            # Recuperar el pedido
            pedido = Pedidos.objects.get(pkid_pedido=pedido_id)
            
            print(f"✅ Pedido creado: ID {pedido.pkid_pedido}")
            print(f"✅ Fecha/hora guardada en MySQL: {pedido.fecha_pedido}")
            
        except Exception as e:
            print(f"ERROR al crear pedido: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False, 
                'message': f'Error al crear el pedido: {str(e)}'
            }, status=500)
        
        # 10. Crear detalles del pedido
        try:
            detalles_creados = []
            for item_detallado in items_detallados:
                detalle = DetallesPedido.objects.create(
                    fkpedido_detalle=pedido,
                    fkproducto_detalle=item_detallado['producto'],
                    cantidad_detalle=item_detallado['cantidad'],
                    precio_unitario=item_detallado['precio_unitario']
                )
                detalles_creados.append(detalle)
            
            print(f"Detalles creados: {len(detalles_creados)}")
            
        except Exception as e:
            print(f"ERROR al crear detalles: {str(e)}")
            # Revertir pedido si fallan los detalles
            pedido.delete()
            return JsonResponse({
                'success': False, 
                'message': f'Error al crear detalles del pedido: {str(e)}'
            }, status=500)
        
        # 11. Descontar stock
        try:
            stock_descontado = descontar_stock_pedido(pedido, items_carrito)
            print(f"Stock descontado: {stock_descontado}")
        except Exception as e:
            print(f"ERROR al descontar stock: {str(e)}")
            # Continuar aunque falle el descuento de stock
        
        # 12. Crear pagos para cada negocio
        try:
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
                    fecha_pago=fecha_mysql,  # Usar misma hora Colombia
                    estado_pago=estado_pago,
                    metodo_pago=metodo_pago
                )
            
            print(f"Pagos creados: {len(negocios_involucrados)}")
            
        except Exception as e:
            print(f"ERROR al crear pagos: {str(e)}")
            # Continuar aunque falle la creación de pagos
        
        # 13. Crear notificaciones
        try:
            # Notificación para el CLIENTE
            Notificacion.objects.create(
                usuario=auth_user,
                tipo='pedido',
                titulo='✅ Pedido Confirmado',
                mensaje=f'Tu pedido #{pedido.pkid_pedido} ha sido procesado exitosamente. Total: ${total_pedido:,.0f}',
                url=f'/pedidos/{pedido.pkid_pedido}/',
                fecha_creacion=fecha_mysql
            )
            
            # Notificación para el NEGOCIO PRINCIPAL
            if negocio_principal and negocio_principal.fkpropietario_neg and negocio_principal.fkpropietario_neg.fkuser:
                Notificacion.objects.create(
                    usuario=negocio_principal.fkpropietario_neg.fkuser,
                    tipo='pedido',
                    titulo='🛒 Nuevo Pedido Recibido',
                    mensaje=f'Tienes un nuevo pedido #{pedido.pkid_pedido} de {auth_user.first_name or auth_user.username}. Total: ${mayor_monto:,.0f}',
                    url=f'/negocio/pedidos/{pedido.pkid_pedido}/',
                    fecha_creacion=fecha_mysql
                )
            
            # Notificaciones para otros negocios
            for negocio, monto in negocios_involucrados.items():
                if negocio != negocio_principal and negocio.fkpropietario_neg and negocio.fkpropietario_neg.fkuser:
                    Notificacion.objects.create(
                        usuario=negocio.fkpropietario_neg.fkuser,
                        tipo='pedido',
                        titulo='🛒 Pedido Multi-Negocio',
                        mensaje=f'Tienes productos en el pedido #{pedido.pkid_pedido}. Tu ganancia: ${monto:,.0f}',
                        url=f'/negocio/pedidos/{pedido.pkid_pedido}/',
                        fecha_creacion=fecha_mysql
                    )
            
            print(f"Notificaciones creadas: {1 + len(negocios_involucrados)}")
            
        except Exception as e:
            print(f"ERROR al crear notificaciones: {str(e)}")
            # Continuar aunque falle la creación de notificaciones
        
        # 14. Vaciar carrito
        try:
            items_carrito.delete()
            print("Carrito vaciado exitosamente")
        except Exception as e:
            print(f"ERROR al vaciar carrito: {str(e)}")
            # Continuar aunque falle el vaciado del carrito
        
        # 15. Enviar comprobante por correo
        try:
            email_cliente = auth_user.email
            if email_cliente:
                enviar_comprobante_pedido(email_cliente, pedido, items_detallados, negocios_involucrados)
                print(f"Correo enviado a: {email_cliente}")
        except Exception as e:
            print(f"ERROR al enviar correo: {str(e)}")
            # Continuar aunque falle el envío de correo
        
        # 16. Formatear respuesta exitosa
        # Usar la fecha del pedido que guardamos
        fecha_respuesta = timezone.localtime(pedido.fecha_pedido)
        fecha_formateada = fecha_respuesta.strftime("%d/%m/%Y %I:%M:%S %p").lower()
        
        response_data = {
            'success': True,
            'message': 'Pedido procesado exitosamente',
            'numero_pedido': pedido.pkid_pedido,
            'total': float(total_pedido),
            'metodo_pago': data.get('metodo_pago_texto', '').strip(),
            'fecha': fecha_formateada,
            'fecha_raw': pedido.fecha_pedido.isoformat() if hasattr(pedido.fecha_pedido, 'isoformat') else str(pedido.fecha_pedido),
            'estado_pedido': pedido.estado_pedido,
            'pagos_creados': len(negocios_involucrados),
            'negocio_principal': negocio_principal.nom_neg,
            'items_procesados': len(items_detallados),
            'stock_descontado': stock_descontado if 'stock_descontado' in locals() else False,
        }
        
        print(f"=== PEDIDO PROCESADO EXITOSAMENTE ===")
        print(f"ID Pedido: {pedido.pkid_pedido}")
        print(f"Hora Colombia guardada: {pedido.fecha_pedido}")
        print(f"Hora Colombia formateada: {fecha_formateada}")
        
        return JsonResponse(response_data)

    except Exception as e:
        print(f"=== ERROR CRÍTICO NO CAPTURADO: {str(e)} ===")
        import traceback
        traceback.print_exc()
        
        # Crear notificación de error
        try:
            Notificacion.objects.create(
                usuario=request.user,
                tipo='alerta',
                titulo='❌ Error en Pedido',
                mensaje='Ocurrió un error crítico al procesar tu pedido. Por favor intenta nuevamente.',
                url='/carrito/'
            )
        except:
            pass
            
        return JsonResponse({
            'success': False, 
            'message': f'Error interno del servidor: {str(e)[:100]}...'
        }, status=500)
        
# =============================================================================
# FUNCIONES PARA CREAR NOTIFICACIONES (SIN @never_cache)
# =============================================================================

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

@never_cache
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


@never_cache
@login_required(login_url='/auth/login/')
def productos_filtrados_logeado(request):
    """
    Vista corregida para procesar correctamente TODOS los filtros
    incluyendo los que envía Gemini.
    """
    print(f"\n🎯 DEBUG - PRODUCTOS FILTRADOS LOGEADO")
    print(f"🔍 Parámetros GET recibidos: {dict(request.GET)}")
    
    # Obtener TODOS los parámetros de filtro
    filtro_tipo = request.GET.get('filtro', '')
    categoria_id = request.GET.get('categoria', '')
    negocio_id = request.GET.get('negocio', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    ordenar = request.GET.get('ordenar', 'recientes')
    
    # IMPORTANTE: Aceptar AMBOS parámetros de búsqueda
    buscar_param = request.GET.get('q', '')
    buscar_alternativo = request.GET.get('buscar', '')
    buscar = buscar_param if buscar_param else buscar_alternativo
    
    print(f"📝 Búsqueda procesada: '{buscar}'")
    print(f"🏷️ Categoría: {categoria_id}")
    print(f"💰 Precio min: {precio_min}, max: {precio_max}")
    print(f"📊 Ordenar: {ordenar}")
    
    # Iniciar con todos los productos disponibles
    productos = Productos.objects.filter(estado_prod='disponible')
    
    # 1. APLICAR FILTRO POR TIPO (si existe)
    if filtro_tipo:
        print(f"🔧 Aplicando filtro tipo: {filtro_tipo}")
        
        if filtro_tipo == 'ofertas':
            hoy = date.today()
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT fkproducto_id 
                    FROM promociones 
                    WHERE estado_promo = 'activa' 
                    AND fecha_inicio <= %s 
                    AND fecha_fin >= %s
                    AND porcentaje_descuento > 0
                """, [hoy, hoy])
                
                resultados = cursor.fetchall()
                productos_con_ofertas_ids = [row[0] for row in resultados if row[0] is not None]
            
            if productos_con_ofertas_ids:
                productos = productos.filter(pkid_prod__in=productos_con_ofertas_ids)
                print(f"   ✅ Ofertas aplicadas: {len(productos_con_ofertas_ids)} productos")
            else:
                productos = productos.none()
                print(f"   ⚠️ Sin ofertas activas")
            
            titulo_filtro = "🎯 Ofertas Especiales"
        
        elif filtro_tipo == 'destacados':
            productos = productos.filter(stock_prod__gt=0).order_by('?')
            print(f"   ✅ Destacados filtrados: stock > 0")
            titulo_filtro = "⭐ Productos Destacados"
        
        elif filtro_tipo == 'economicos':
            productos = productos.order_by('precio_prod')
            print(f"   ✅ Ordenado por precio ascendente")
            titulo_filtro = "💰 Productos Económicos"
        
        elif filtro_tipo == 'nuevos':
            productos = productos.order_by('-fecha_creacion')
            print(f"   ✅ Ordenado por fecha creación (nuevos)")
            titulo_filtro = "🆕 Nuevos Productos"
        
        elif filtro_tipo == 'mas-vendidos':
            productos = productos.annotate(
                total_vendido=Sum('detallespedido__cantidad_detalle')
            ).filter(total_vendido__gt=0).order_by('-total_vendido')
            print(f"   ✅ Ordenado por más vendidos")
            titulo_filtro = "🔥 Más Vendidos"
        
        else:
            titulo_filtro = "🛍️ Todos los Productos"
    else:
        titulo_filtro = "🛍️ Todos los Productos"

    # 2. APLICAR BÚSQUEDA POR TEXTO (si existe)
    if buscar and buscar.strip():
        print(f"🔍 Aplicando búsqueda: '{buscar}'")
        
        # Búsqueda multi-campo
        consulta_busqueda = Q(
            Q(nom_prod__icontains=buscar) |
            Q(desc_prod__icontains=buscar) |
            Q(fknegocioasociado_prod__nom_neg__icontains=buscar) |
            Q(fkcategoria_prod__desc_cp__icontains=buscar)
        )
        
        productos = productos.filter(consulta_busqueda)
        print(f"   ✅ Búsqueda aplicada: {productos.count()} productos")
    
    # 3. APLICAR FILTRO POR CATEGORÍA (si existe)
    if categoria_id and categoria_id.isdigit():
        try:
            categoria_int = int(categoria_id)
            productos = productos.filter(fkcategoria_prod_id=categoria_int)
            
            # Obtener nombre de categoría para mostrar
            try:
                categoria_obj = CategoriaProductos.objects.get(pkid_cp=categoria_int)
                titulo_filtro += f" - {categoria_obj.desc_cp}"
            except:
                pass
            
            print(f"   ✅ Filtro categoría ID: {categoria_id}")
        except ValueError:
            print(f"   ⚠️ Categoría ID inválido: {categoria_id}")

    # 4. APLICAR FILTRO POR NEGOCIO (si existe)
    if negocio_id and negocio_id.isdigit():
        try:
            negocio_int = int(negocio_id)
            productos = productos.filter(fknegocioasociado_prod_id=negocio_int)
            print(f"   ✅ Filtro negocio ID: {negocio_id}")
        except ValueError:
            print(f"   ⚠️ Negocio ID inválido: {negocio_id}")

    # 5. APLICAR FILTRO POR RANGO DE PRECIO (si existe)
    precio_filtros_aplicados = []
    
    if precio_min:
        try:
            precio_min_float = float(precio_min)
            if precio_min_float > 0:
                productos = productos.filter(precio_prod__gte=precio_min_float)
                precio_filtros_aplicados.append(f"Min: ${precio_min_float:,.0f}")
                print(f"   ✅ Precio mínimo: ${precio_min_float:,.0f}")
        except (ValueError, TypeError) as e:
            print(f"   ⚠️ Error precio_min: {e}")

    if precio_max:
        try:
            precio_max_float = float(precio_max)
            if precio_max_float > 0:
                productos = productos.filter(precio_prod__lte=precio_max_float)
                precio_filtros_aplicados.append(f"Máx: ${precio_max_float:,.0f}")
                print(f"   ✅ Precio máximo: ${precio_max_float:,.0f}")
        except (ValueError, TypeError) as e:
            print(f"   ⚠️ Error precio_max: {e}")
    
    # 6. APLICAR ORDENAMIENTO
    print(f"📊 Aplicando ordenamiento: {ordenar}")
    
    ordenamientos = {
        'precio_asc': 'precio_prod',
        'precio_desc': '-precio_prod',
        'nombre': 'nom_prod',
        'nuevos': '-fecha_creacion',
        'stock': '-stock_prod',
        'recientes': '-fecha_creacion'
    }
    
    campo_orden = ordenamientos.get(ordenar, '-fecha_creacion')
    productos = productos.order_by(campo_orden)
    
    print(f"   ✅ Ordenado por: {campo_orden}")
    
    # 7. OBTENER DATOS PARA FILTROS
    categorias = CategoriaProductos.objects.annotate(
        num_productos=Count('productos', filter=Q(productos__estado_prod='disponible'))
    ).order_by('desc_cp')
    
    negocios = Negocios.objects.annotate(
        num_productos=Count('productos', filter=Q(productos__estado_prod='disponible'))
    ).filter(estado_neg='activo').order_by('nom_neg')
    
    # 8. PROCESAR PRODUCTOS CON VARIANTES Y OFERTAS
    productos_data = []
    hoy = date.today()
    total_productos = productos.count()
    
    print(f"📦 Procesando {total_productos} productos...")
    
    for producto in productos[:200]:  # Limitar para no sobrecargar
        producto_data = {
            'producto': producto,
            'precio_base': float(producto.precio_prod) if producto.precio_prod else 0,
            'precio_final': float(producto.precio_prod) if producto.precio_prod else 0,
            'tiene_descuento': False,
            'descuento_porcentaje': 0,
            'ahorro': 0,
            'stock': producto.stock_prod or 0,
            'tiene_variantes': False,
            'variantes': []
        }
        
        # Verificar variantes
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
                    'precio_adicional': float(variante.precio_adicional) if variante.precio_adicional else 0,
                    'stock_variante': variante.stock_variante or 0,
                    'imagen_variante': variante.imagen_variante,
                    'sku_variante': variante.sku_variante
                }
                variantes_detalladas.append(variante_data)
            
            producto_data['variantes'] = variantes_detalladas
        
        # Verificar ofertas activas
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
                descuento = float(porcentaje_descuento) if porcentaje_descuento else 0
                
                if descuento > 0:
                    precio_base = float(producto.precio_prod) if producto.precio_prod else 0
                    producto_data['precio_final'] = precio_base * (1 - descuento / 100)
                    producto_data['tiene_descuento'] = True
                    producto_data['descuento_porcentaje'] = descuento
                    producto_data['ahorro'] = precio_base - producto_data['precio_final']
                    producto_data['titulo_promo'] = titulo_promo
            except (ValueError, TypeError):
                pass
        
        productos_data.append(producto_data)
    
    print(f"✅ Productos procesados: {len(productos_data)}")
    
    # 9. PAGINACIÓN
    paginator = Paginator(productos_data, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 10. OBTENER CONTADOR DEL CARRITO
    carrito_count = 0
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        except Carrito.DoesNotExist:
            carrito_count = 0
    except Exception as e:
        print(f"⚠️ Error carrito: {e}")
        carrito_count = 0
    
    # 11. CONSTRUIR TÍTULO DESCRIPTIVO
    titulo_completo = titulo_filtro
    
    if buscar:
        titulo_completo += f" para '{buscar}'"
    
    if precio_filtros_aplicados:
        titulo_completo += f" ({', '.join(precio_filtros_aplicados)})"
    
    # 12. PREPARAR CONTEXTO
    context = {
        'productos_data': page_obj,
        'categorias': categorias,
        'negocios': negocios,
        'total_productos': paginator.count,
        
        # Parámetros actuales para mantener en formularios
        'filtro_actual': filtro_tipo,
        'categoria_actual': categoria_id,
        'negocio_actual': negocio_id,
        'precio_min_actual': precio_min,
        'precio_max_actual': precio_max,
        'ordenar_actual': ordenar,
        'buscar_actual': buscar,
        
        # Para barra de búsqueda (compatibilidad)
        'q': buscar,
        
        # Información para mostrar
        'titulo_filtro': titulo_completo,
        'carrito_count': carrito_count,
        
        # Debug info (puedes quitar esto en producción)
        'debug_info': {
            'parametros_recibidos': dict(request.GET),
            'productos_total': paginator.count,
            'filtros_aplicados': {
                'texto': buscar,
                'categoria': categoria_id,
                'precio_min': precio_min,
                'precio_max': precio_max
            }
        }
    }
    
    print(f"✅ Vista completada. Productos totales: {paginator.count}")
    print("="*60 + "\n")
    
    return render(request, 'Cliente/productos_filtros_logeado.html', context)

@never_cache
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

@never_cache
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

@never_cache
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

@never_cache
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

@never_cache
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

@never_cache   
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

@never_cache
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

@never_cache    
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
# FUNCIONES AUXILIARES PARA STOCK (SIN @never_cache)
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
# FUNCIONES PARA CREAR NOTIFICACIONES AUTOMÁTICAS (SIN @never_cache)
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

def procesar_pedido_contraentrega(negocio, pedido_data):
    """
    Lógica simple para pago contraentrega
    """
    # 1. Verificar si el negocio ofrece domicilio
    if pedido_data.get('tipo_entrega') == 'domicilio' and not negocio.ofrece_domicilio:
        return False, "Este negocio no ofrece servicio a domicilio"
    
    # 2. Calcular montos
    total = pedido_data['total_pedido']
    anticipo_porcentaje = pedido_data.get('anticipo_porcentaje', 20)
    monto_anticipo = (total * anticipo_porcentaje) / 100
    monto_pendiente = total - monto_anticipo
    
    # 3. Crear pedido con pago contraentrega
    pedido = Pedidos(
        fknegocio_pedido=negocio,
        total_pedido=total,
        tipo_entrega=pedido_data.get('tipo_entrega', 'recoge'),
        pago_contraentrega=True,
        anticipo_porcentaje=anticipo_porcentaje,
        monto_anticipo=monto_anticipo,
        monto_pendiente=monto_pendiente,
        direccion_entrega=pedido_data.get('direccion_entrega'),
        estado_pedido='pendiente'
    )
    pedido.save()
    
    return True, pedido


@csrf_exempt
@require_http_methods(["GET"])
def verificar_domicilio_negocio(request):
    """Verifica si el negocio ofrece domicilio y su costo"""
    try:
        # Obtener información del negocio desde el carrito
        carrito = Carrito.objects.filter(fkusuario_carrito=request.user.usuario_perfil).first()
        
        if carrito:
            items = CarritoItem.objects.filter(fkcarrito=carrito)
            if items.exists():
                negocio = items.first().fknegocio
                
                return JsonResponse({
                    'success': True,
                    'ofrece_domicilio': negocio.ofrece_domicilio if hasattr(negocio, 'ofrece_domicilio') else False,
                    'costo_domicilio': float(negocio.costo_domicilio) if hasattr(negocio, 'costo_domicilio') else 0,
                    'nombre_negocio': negocio.nom_neg,
                    'direccion_negocio': negocio.direcc_neg
                })
        
        return JsonResponse({
            'success': True,
            'ofrece_domicilio': False,
            'costo_domicilio': 0,
            'nombre_negocio': '',
            'direccion_negocio': ''
        })
        
    except Exception as e:
        print(f"Error verificando domicilio: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })