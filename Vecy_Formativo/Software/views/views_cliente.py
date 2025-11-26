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

# ==================== VISTAS PÚBLICAS ====================
def principal(request):
    # Obtener datos base
    negocios = Negocios.objects.filter(estado_neg='activo')
    categorias = CategoriaProductos.objects.all()[:20]
    tipo_negocios = TipoNegocio.objects.all()
    
    # PRODUCTOS DISPONIBLES CON SUS VARIANTES
    todos_productos = Productos.objects.filter(estado_prod='disponible')
    
    # Obtener variantes para cada producto
    productos_con_variantes = []
    for producto in todos_productos:
        variantes = VariantesProducto.objects.filter(
            producto_id=producto.pkid_prod, 
            estado_variante='activa'
        )
        
        producto_data = {
            'producto': producto,
            'variantes': list(variantes),
            'tiene_variantes': variantes.exists()
        }
        productos_con_variantes.append(producto_data)
    
    # PROMOCIONES ACTIVAS
    promociones_procesadas = []
    try:
        hoy = timezone.now().date()
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
            """, [hoy, hoy])
            
            promociones_data = cursor.fetchall()
            
            for row in promociones_data:
                try:
                    promocion_dict = {
                        'pkid_promo': row[0],
                        'titulo_promo': row[1],
                        'descripcion_promo': row[2],
                        'porcentaje_descuento': float(row[3]) if row[3] is not None else 0.0,
                        'fecha_inicio': row[4],
                        'fecha_fin': row[5],
                        'estado_promo': row[6],
                        'imagen_promo': row[7],
                        'fknegocio_id': row[8],
                        'fkproducto_id': row[9],
                        'variante_id': row[10]
                    }
                    promociones_procesadas.append(promocion_dict)
                except Exception:
                    continue
                    
    except Exception:
        promociones_procesadas = []
    
    # PRODUCTOS CON OFERTAS REALES
    productos_oferta = []
    
    for promocion_data in promociones_procesadas:
        try:
            producto_id = promocion_data['fkproducto_id']
            negocio_id = promocion_data['fknegocio_id']
            variante_id = promocion_data.get('variante_id')
            
            if producto_id:
                producto = Productos.objects.get(pkid_prod=producto_id)
                negocio = Negocios.objects.get(pkid_neg=negocio_id)
                
                variante_info = None
                if variante_id:
                    try:
                        variante = VariantesProducto.objects.get(id_variante=variante_id)
                        variante_info = {
                            'id': variante.id_variante,
                            'nombre': variante.nombre_variante,
                            'precio_adicional': float(variante.precio_adicional),
                            'stock': variante.stock_variante,
                            'imagen': variante.imagen_variante.url if variante.imagen_variante else None
                        }
                    except VariantesProducto.DoesNotExist:
                        pass
                
                if producto.estado_prod == 'disponible':
                    precio_base = float(producto.precio_prod)
                    if variante_info:
                        precio_base += variante_info['precio_adicional']
                    
                    descuento_porcentaje = promocion_data['porcentaje_descuento']
                    
                    if descuento_porcentaje and descuento_porcentaje > 0:
                        descuento_monto = (precio_base * descuento_porcentaje) / 100
                        precio_final = precio_base - descuento_monto
                        
                        producto_data = {
                            'producto': producto,
                            'precio_original': precio_base,
                            'precio_final': round(precio_final, 2),
                            'descuento_porcentaje': descuento_porcentaje,
                            'descuento_monto': round(descuento_monto, 2),
                            'tiene_descuento': True,
                            'promocion': promocion_data,
                            'variante': variante_info
                        }
                        productos_oferta.append(producto_data)
        except (Productos.DoesNotExist, Negocios.DoesNotExist):
            continue
    
    # NEGOCIOS CON CALIFICACIONES CALCULADAS
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
    
    # NEGOCIOS MEJOR CALIFICADOS
    negocios_mejor_calificados = sorted(
        [n for n in negocios_con_calificaciones if n.promedio_calificacion > 0],
        key=lambda x: x.promedio_calificacion,
        reverse=True
    )[:8]
    
    # PRODUCTOS MÁS VENDIDOS (con variantes)
    productos_mas_vendidos_data = []
    productos_mas_vendidos = Productos.objects.filter(
        detallespedido__isnull=False,
        estado_prod='disponible'
    ).annotate(
        total_vendido=Sum('detallespedido__cantidad_detalle')
    ).filter(
        total_vendido__gt=0
    ).order_by('-total_vendido')[:8]
    
    for producto in productos_mas_vendidos:
        variantes = VariantesProducto.objects.filter(
            producto_id=producto.pkid_prod, 
            estado_variante='activa'
        )
        productos_mas_vendidos_data.append({
            'producto': producto,
            'variantes': list(variantes),
            'tiene_variantes': variantes.exists()
        })
    
    if not productos_mas_vendidos_data:
        productos_aleatorios = todos_productos.order_by('?')[:8]
        productos_mas_vendidos_data = []
        for producto in productos_aleatorios:
            variantes = VariantesProducto.objects.filter(
                producto_id=producto.pkid_prod, 
                estado_variante='activa'
            )
            productos_mas_vendidos_data.append({
                'producto': producto,
                'variantes': list(variantes),
                'tiene_variantes': variantes.exists()
            })
    
    # PRODUCTOS MÁS BARATOS (con variantes)
    productos_baratos_data = []
    productos_baratos = todos_productos.order_by('precio_prod')[:8]
    for producto in productos_baratos:
        variantes = VariantesProducto.objects.filter(
            producto_id=producto.pkid_prod, 
            estado_variante='activa'
        )
        productos_baratos_data.append({
            'producto': producto,
            'variantes': list(variantes),
            'tiene_variantes': variantes.exists()
        })
    
    # NUEVOS PRODUCTOS (con variantes)
    nuevos_productos_data = []
    nuevos_productos = todos_productos.order_by('-fecha_creacion')[:12]
    for producto in nuevos_productos:
        variantes = VariantesProducto.objects.filter(
            producto_id=producto.pkid_prod, 
            estado_variante='activa'
        )
        nuevos_productos_data.append({
            'producto': producto,
            'variantes': list(variantes),
            'tiene_variantes': variantes.exists()
        })
    
    # PRODUCTOS DESTACADOS (con variantes)
    productos_destacados_data = []
    productos_destacados = todos_productos.order_by('?')[:8]
    for producto in productos_destacados:
        variantes = VariantesProducto.objects.filter(
            producto_id=producto.pkid_prod, 
            estado_variante='activa'
        )
        productos_destacados_data.append({
            'producto': producto,
            'variantes': list(variantes),
            'tiene_variantes': variantes.exists()
        })
    
    # CATEGORÍAS POPULARES
    categorias_populares = categorias[:8]
    
    contexto = {
        'negocios': negocios_con_calificaciones[:12],
        'categorias': categorias,
        'tipo_negocios': tipo_negocios,
        'productos_destacados': productos_destacados_data,
        'nuevos_productos': nuevos_productos_data,
        'productos_baratos': productos_baratos_data,
        'negocios_mejor_calificados': negocios_mejor_calificados,
        'productos_oferta': productos_oferta,
        'categorias_populares': categorias_populares,
        'productos_mas_vendidos': productos_mas_vendidos_data,
        'productos_con_variantes': productos_con_variantes,
        'hay_promociones': len(productos_oferta) > 0,
    }
    
    return render(request, 'cliente/principal.html', contexto)

def productos_todos(request):
    """Vista pública de todos los productos"""
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
    
    # Filtros
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
    
    # Ordenar
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
    
    # Preparar datos para el template
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
    
    # Paginación
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
    """Vista pública de productos por categoría"""
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
    
    # Filtros
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
    
    # Preparar datos para el template
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
    
    return render(request, 'Cliente/productos_todos.html', context)

def detalle_negocio(request, id):
    """Vista pública del detalle del negocio (accesible sin login)"""
    # Obtener negocio y propietario
    negocio = get_object_or_404(Negocios, pkid_neg=id, estado_neg='activo')
    propietario = negocio.fkpropietario_neg
    tipo_negocio = negocio.fktiponeg_neg

    # Productos del negocio
    productos = Productos.objects.filter(
        fknegocioasociado_prod=negocio,
        estado_prod='disponible'
    ).select_related('fkcategoria_prod')
    
    # Reseñas del negocio
    resenas = ResenasNegocios.objects.filter(
        fknegocio_resena=negocio,
        estado_resena='activa'
    ).select_related('fkusuario_resena__fkuser')

    # Calcular promedio
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

# ==================== VISTAS PRIVADAS ====================
@never_cache
@login_required(login_url='/auth/login/')
def cliente_dashboard(request):
    """Dashboard principal del cliente logueado"""
    try:
        # Obtener el perfil del cliente
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        from django.utils import timezone
        from django.db.models import Q, Avg, Count, Sum
        from django.db import connection
        from decimal import Decimal
        hoy = timezone.now().date()

        print("=== DEBUG CLIENTE DASHBOARD INICIO ===")

        # ========== CARRUSEL DE OFERTAS RECIENTES ==========
        ofertas_carrusel_data = []
        try:
            fecha_limite = hoy - timezone.timedelta(days=5)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT p.pkid_promo, p.titulo_promo, p.descripcion_promo, 
                           p.porcentaje_descuento, p.fecha_inicio, p.fecha_fin,
                           p.estado_promo, p.imagen_promo,
                           p.fknegocio_id, p.fkproducto_id
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
                print(f"🔄 Ofertas carrusel SQL encontradas: {len(ofertas_carrusel)}")
                
                for i, row in enumerate(ofertas_carrusel):
                    try:
                        print(f"  🔍 Procesando oferta {i+1}: {row[1]} - Descuento: {row[3]}")
                        
                        # Procesar descuento de forma segura
                        descuento_valor = 0
                        if row[3] is not None:
                            try:
                                descuento_valor = float(row[3])
                                print(f"    ✅ Descuento procesado: {descuento_valor}%")
                            except (ValueError, TypeError) as e:
                                print(f"    ❌ Error en descuento: {e}")
                                descuento_valor = 0
                        
                        # Obtener producto y negocio
                        producto = Productos.objects.get(pkid_prod=row[9])
                        negocio = Negocios.objects.get(pkid_neg=row[8])
                        
                        precio_base = float(producto.precio_prod) if producto.precio_prod else 0
                        ahorro_oferta = precio_base * (descuento_valor / 100)
                        
                        oferta_data = {
                            'pkid_promo': row[0],
                            'titulo_promo': row[1],
                            'descripcion_promo': row[2],
                            'porcentaje_descuento': descuento_valor,
                            'precio_base': precio_base,
                            'precio_final': precio_base - ahorro_oferta,
                            'ahorro_oferta': round(ahorro_oferta, 2),
                            'imagen_promo': row[7] or (producto.img_prod.url if producto.img_prod else None),
                            'fkproducto': producto,
                            'fknegocio': negocio,
                        }
                        
                        ofertas_carrusel_data.append(oferta_data)
                        print(f"    ✅ Oferta agregada: {oferta_data['titulo_promo']}")
                        
                    except Exception as e:
                        print(f"    ❌ Error procesando oferta carrusel: {e}")
                        continue
        except Exception as e:
            print(f"❌ Error obteniendo ofertas carrusel: {e}")

        print(f"📦 Ofertas carrusel finales: {len(ofertas_carrusel_data)}")

        # ========== PRODUCTOS BARATOS (HASTA 50,000 PESOS) - CORREGIDO ==========
        productos_baratos_data = []
        try:
            # FILTRO CORREGIDO: Solo productos hasta 50,000 pesos
            productos_baratos = Productos.objects.filter(
                estado_prod='disponible',
                precio_prod__lte=50000
            ).order_by('precio_prod')[:12]
            
            print(f"🔄 Productos baratos encontrados (hasta $50,000): {productos_baratos.count()}")
            
            for i, producto in enumerate(productos_baratos):
                try:
                    print(f"  🔍 Procesando producto barato {i+1}: {producto.nom_prod} - Precio: {producto.precio_prod}")
                    
                    precio_base = float(producto.precio_prod) if producto.precio_prod else 0
                    precio_final = precio_base
                    descuento_porcentaje = 0
                    ahorro = 0
                    
                    # Verificar si tiene oferta activa usando SQL
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
                                    print(f"    ✅ Descuento aplicado: {descuento_porcentaje}%")
                            except (ValueError, TypeError) as e:
                                print(f"    ❌ Error en descuento: {e}")
                                pass
                    
                    # CORRECCIÓN COMPLETA: OBTENER VARIANTES CON STOCK REAL INDIVIDUAL
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
                        
                        print(f"    🔍 Variantes encontradas para {producto.nom_prod}: {variantes.count()}")
                        
                        for variante in variantes:
                            try:
                                # USAR LOS CAMPOS CORRECTOS DEL MODELO VariantesProducto
                                variante_data = {
                                    'id_variante': variante.id_variante,
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': float(variante.precio_adicional) if variante.precio_adicional else 0,
                                    'stock_variante': variante.stock_variante or 0,  # ✅ STOCK REAL INDIVIDUAL DE LA VARIANTE
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                }
                                variantes_list.append(variante_data)
                                print(f"    📦 Variante procesada: {variante.nombre_variante} (ID: {variante.id_variante}) - Precio adicional: ${variante_data['precio_adicional']} - Stock: {variante_data['stock_variante']}")
                                
                            except Exception as e:
                                print(f"    ❌ Error procesando variante: {e}")
                                continue
                    
                    # ✅ CORRECCIÓN: Stock del producto base SOLO para el producto base
                    producto_data = {
                        'producto': producto,
                        'precio_base': precio_base,
                        'precio_final': round(precio_final, 2),
                        'tiene_descuento': descuento_porcentaje > 0,
                        'descuento_porcentaje': descuento_porcentaje,
                        'ahorro': round(ahorro, 2),
                        'tiene_variantes': tiene_variantes,
                        'variantes': variantes_list,
                        'stock': producto.stock_prod or 0,  # ✅ SOLO STOCK DEL PRODUCTO BASE
                    }
                    
                    productos_baratos_data.append(producto_data)
                    print(f"    ✅ Producto barato agregado: {producto.nom_prod} - Precio final: ${precio_final} - Tiene variantes: {tiene_variantes} - Variantes: {len(variantes_list)} - Stock base: {producto.stock_prod}")
                    
                except Exception as e:
                    print(f"    ❌ Error procesando producto barato {producto.nom_prod}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error obteniendo productos baratos: {e}")

        print(f"📦 Productos baratos finales (hasta $50,000): {len(productos_baratos_data)}")

        # ========== PRODUCTOS DESTACADOS - CORREGIDO ==========
        productos_destacados_data = []
        try:
            productos_vendidos = DetallesPedido.objects.filter(
                fkproducto_detalle__estado_prod='disponible'
            ).values(
                'fkproducto_detalle'
            ).annotate(
                total_vendido=Sum('cantidad_detalle')
            ).order_by('-total_vendido')[:12]
            
            print(f"🔄 Productos vendidos encontrados: {len(productos_vendidos)}")
            
            for i, item in enumerate(productos_vendidos):
                try:
                    producto = Productos.objects.get(pkid_prod=item['fkproducto_detalle'])
                    print(f"  🔍 Procesando producto destacado {i+1}: {producto.nom_prod} - Vendidos: {item['total_vendido']}")
                    
                    precio_base = float(producto.precio_prod) if producto.precio_prod else 0
                    precio_final = precio_base
                    descuento_porcentaje = 0
                    ahorro = 0
                    
                    # Verificar ofertas usando SQL
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
                                    print(f"    ✅ Descuento aplicado: {descuento_porcentaje}%")
                            except (ValueError, TypeError) as e:
                                print(f"    ❌ Error en descuento: {e}")
                                pass
                    
                    # CORRECCIÓN COMPLETA: OBTENER VARIANTES CON STOCK REAL INDIVIDUAL
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
                                # USAR LOS CAMPOS CORRECTOS DEL MODELO
                                variante_data = {
                                    'id_variante': variante.id_variante,
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': float(variante.precio_adicional) if variante.precio_adicional else 0,
                                    'stock_variante': variante.stock_variante or 0,  # ✅ STOCK REAL INDIVIDUAL DE LA VARIANTE
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                }
                                variantes_list.append(variante_data)
                                print(f"    📦 Variante encontrada: {variante.nombre_variante} (ID: {variante.id_variante}) - Stock: {variante_data['stock_variante']}")
                            except Exception as e:
                                print(f"    ❌ Error procesando variante: {e}")
                                continue
                    
                    producto_data = {
                        'producto': producto,
                        'precio_base': precio_base,
                        'precio_final': round(precio_final, 2),
                        'total_vendido': item['total_vendido'],
                        'tiene_descuento': descuento_porcentaje > 0,
                        'descuento_porcentaje': descuento_porcentaje,
                        'ahorro': round(ahorro, 2),
                        'tiene_variantes': tiene_variantes,
                        'variantes': variantes_list,
                        'stock': producto.stock_prod or 0,  # ✅ SOLO STOCK DEL PRODUCTO BASE
                    }
                    
                    productos_destacados_data.append(producto_data)
                    print(f"    ✅ Producto destacado agregado: {producto.nom_prod} - Variantes: {len(variantes_list)} - Stock base: {producto.stock_prod}")
                    
                except Productos.DoesNotExist:
                    print(f"    ❌ Producto no encontrado: {item['fkproducto_detalle']}")
                    continue
                except Exception as e:
                    print(f"    ❌ Error procesando producto destacado: {e}")
                    continue
        except Exception as e:
            print(f"❌ Error obteniendo productos destacados: {e}")

        print(f"📦 Productos destacados finales: {len(productos_destacados_data)}")

        # ========== PRODUCTOS EN OFERTA - CORREGIDO ==========
        productos_oferta_data = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT pr.pkid_prod, pr.nom_prod, pr.precio_prod, 
                           pr.desc_prod, pr.stock_prod, pr.img_prod,
                           p.porcentaje_descuento, pr.fknegocioasociado_prod
                    FROM productos pr
                    INNER JOIN promociones p ON pr.pkid_prod = p.fkproducto_id
                    WHERE pr.estado_prod = 'disponible'
                    AND p.estado_promo = 'activa'
                    AND p.fecha_inicio <= %s
                    AND p.fecha_fin >= %s
                    LIMIT 12
                """, [hoy, hoy])
                
                productos_oferta_rows = cursor.fetchall()
                print(f"🔄 Productos oferta SQL encontrados: {len(productos_oferta_rows)}")
                
                for i, row in enumerate(productos_oferta_rows):
                    try:
                        print(f"  🔍 Procesando producto oferta {i+1}: {row[1]} - Precio: {row[2]}")
                        
                        producto_id = row[0]
                        producto = Productos.objects.get(pkid_prod=producto_id)
                        
                        precio_base = float(row[2]) if row[2] else 0
                        precio_final = precio_base
                        descuento_porcentaje = 0
                        ahorro = 0
                        
                        # Procesar descuento
                        if row[6] is not None:
                            try:
                                descuento_porcentaje = float(row[6])
                                if descuento_porcentaje > 0:
                                    precio_final = precio_base * (1 - (descuento_porcentaje / 100))
                                    ahorro = precio_base - precio_final
                                    print(f"    ✅ Descuento aplicado: {descuento_porcentaje}%")
                            except (ValueError, TypeError) as e:
                                print(f"    ❌ Error en descuento: {e}")
                                pass
                        
                        # CORRECCIÓN COMPLETA: OBTENER VARIANTES CON STOCK REAL INDIVIDUAL
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
                                    # USAR LOS CAMPOS CORRECTOS DEL MODELO
                                    variante_data = {
                                        'id_variante': variante.id_variante,
                                        'nombre_variante': variante.nombre_variante,
                                        'precio_adicional': float(variante.precio_adicional) if variante.precio_adicional else 0,
                                        'stock_variante': variante.stock_variante or 0,  # ✅ STOCK REAL INDIVIDUAL DE LA VARIANTE
                                        'imagen_variante': variante.imagen_variante,
                                        'estado_variante': variante.estado_variante,
                                        'sku_variante': variante.sku_variante,
                                    }
                                    variantes_list.append(variante_data)
                                    print(f"    📦 Variante encontrada: {variante.nombre_variante} (ID: {variante.id_variante}) - Stock: {variante_data['stock_variante']}")
                                except Exception as e:
                                    print(f"    ❌ Error procesando variante: {e}")
                                    continue
                        
                        producto_data = {
                            'producto': producto,
                            'precio_base': precio_base,
                            'precio_final': round(precio_final, 2),
                            'tiene_descuento': descuento_porcentaje > 0,
                            'descuento_porcentaje': descuento_porcentaje,
                            'ahorro': round(ahorro, 2),
                            'tiene_variantes': tiene_variantes,
                            'variantes': variantes_list,
                            'stock': row[4] or 0,  # ✅ SOLO STOCK DEL PRODUCTO BASE
                        }
                        
                        productos_oferta_data.append(producto_data)
                        print(f"    ✅ Producto oferta agregado: {producto.nom_prod} - Variantes: {len(variantes_list)} - Stock base: {row[4]}")
                        
                    except Exception as e:
                        print(f"    ❌ Error procesando producto oferta: {e}")
                        continue
        except Exception as e:
            print(f"❌ Error obteniendo productos oferta: {e}")

        print(f"📦 Productos oferta finales: {len(productos_oferta_data)}")

        # ========== NEGOCIOS DESTACADOS ==========
        negocios_destacados_data = []
        try:
            negocios_con_resenas = Negocios.objects.filter(
                estado_neg='activo'
            ).annotate(
                promedio_calificacion=Avg('resenasnegocios__estrellas')
            ).filter(
                promedio_calificacion__gte=4.0
            ).order_by('-promedio_calificacion')[:6]
            
            print(f"🔄 Negocios destacados encontrados: {negocios_con_resenas.count()}")
            
            for negocio in negocios_con_resenas:
                try:
                    # Contar reseñas únicas
                    total_resenas = ResenasNegocios.objects.filter(
                        fknegocio_resena=negocio
                    ).count()
                    
                    # Contar productos disponibles con stock
                    total_productos_disponibles = Productos.objects.filter(
                        fknegocioasociado_prod=negocio,
                        estado_prod='disponible'
                    ).count()
                    
                    # Calcular productos en oferta usando SQL
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
                    print(f"✅ Negocio destacado agregado: {negocio.nom_neg} - Reseñas: {total_resenas}, Productos: {total_productos_disponibles}")
                    
                except Exception as e:
                    print(f"❌ Error procesando negocio destacado: {e}")
                    continue
        except Exception as e:
            print(f"❌ Error obteniendo negocios destacados: {e}")

        print(f"📦 Negocios destacados finales: {len(negocios_destacados_data)}")

        # ========== OTROS NEGOCIOS ACTIVOS ==========
        otros_negocios_data = []
        try:
            # Obtener IDs de negocios destacados para excluirlos
            negocios_destacados_ids = [neg['negocio'].pkid_neg for neg in negocios_destacados_data]
            
            # Obtener negocios activos que NO están en los destacados
            otros_negocios = Negocios.objects.filter(
                estado_neg='activo'
            ).exclude(
                pkid_neg__in=negocios_destacados_ids
            ).annotate(
                promedio_calificacion=Avg('resenasnegocios__estrellas')
            ).order_by('-promedio_calificacion')[:6]
            
            print(f"🔄 Otros negocios encontrados: {otros_negocios.count()}")
            
            for negocio in otros_negocios:
                try:
                    # Contar reseñas únicas
                    total_resenas = ResenasNegocios.objects.filter(
                        fknegocio_resena=negocio
                    ).count()
                    
                    # Contar productos disponibles con stock
                    total_productos_disponibles = Productos.objects.filter(
                        fknegocioasociado_prod=negocio,
                        estado_prod='disponible'
                    ).count()
                    
                    # Calcular productos en oferta usando SQL
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
                    print(f"✅ Otro negocio agregado: {negocio.nom_neg} - Reseñas: {total_resenas}, Productos: {total_productos_disponibles}")
                    
                except Exception as e:
                    print(f"❌ Error procesando otro negocio: {e}")
                    continue
        except Exception as e:
            print(f"❌ Error obteniendo otros negocios: {e}")

        print(f"📦 Otros negocios finales: {len(otros_negocios_data)}")

        # ========== CARRITO Y FAVORITOS ==========
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
            print(f"❌ Error obteniendo carrito/favoritos: {e}")

        # ========== PEDIDOS PENDIENTES ==========
        pedidos_pendientes_count = 0
        try:
            pedidos_pendientes_count = Pedidos.objects.filter(
                fkusuario_pedido=perfil_cliente,
                estado_pedido__in=['pendiente', 'confirmado', 'preparando']
            ).count()
            print(f"📋 Pedidos pendientes encontrados: {pedidos_pendientes_count}")
        except Exception as e:
            print(f"❌ Error contando pedidos pendientes: {e}")

        print("=== RESUMEN FINAL ===")
        print(f"🎯 Ofertas carrusel: {len(ofertas_carrusel_data)}")
        print(f"💰 Productos baratos (hasta $50,000): {len(productos_baratos_data)}")
        print(f"⭐ Productos destacados: {len(productos_destacados_data)}")
        print(f"🔥 Productos oferta: {len(productos_oferta_data)}")
        print(f"🏆 Negocios destacados: {len(negocios_destacados_data)}")
        print(f"🏪 Otros negocios: {len(otros_negocios_data)}")
        print(f"🛒 Carrito: {carrito_count}")
        print(f"❤️ Favoritos: {favoritos_count}")
        print(f"📋 Pedidos pendientes: {pedidos_pendientes_count}")
        
        # DEBUG DETALLADO: Verificar productos con variantes
        productos_con_variantes = [p for p in productos_baratos_data if p['tiene_variantes']]
        print(f"🔍 Productos con variantes: {len(productos_con_variantes)}")
        for p in productos_con_variantes:
            print(f"   📦 {p['producto'].nom_prod}: {len(p['variantes'])} variantes")
            for v in p['variantes']:
                print(f"      🎯 Variante: {v['nombre_variante']} (ID: {v['id_variante']}) - Precio adicional: ${v['precio_adicional']} - Stock: {v['stock_variante']}")
        
        print("=== DEBUG CLIENTE DASHBOARD FIN ===")

        context = {
            'perfil': perfil_cliente,
            'carrito_count': carrito_count,
            'favoritos_count': favoritos_count,
            'pedidos_pendientes_count': pedidos_pendientes_count,
            
            # Secciones principales
            'ofertas_carrusel': ofertas_carrusel_data,
            'productos_baratos': productos_baratos_data,
            'productos_destacados': productos_destacados_data,
            'productos_oferta': productos_oferta_data,
            'negocios_destacados': negocios_destacados_data,
            'otros_negocios': otros_negocios_data,
            
            # Flags
            'hay_ofertas_activas': len(ofertas_carrusel_data) > 0,
            'hay_productos_baratos': len(productos_baratos_data) > 0,
            'hay_otros_negocios': len(otros_negocios_data) > 0,
        }
        
        return render(request, 'Cliente/Cliente.html', context)
        
    except Exception as e:
        print(f"❌ Error en dashboard cliente: {e}")
        import traceback
        traceback.print_exc()
        
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
            'hay_ofertas_activas': False,
            'hay_productos_baratos': False,
            'hay_otros_negocios': False,
        })    

@login_required(login_url='/auth/login/')
def detalle_negocio_logeado(request, id):
    """Vista detallada del negocio para el cliente logueado - VERSIÓN COMPLETAMENTE CORREGIDA CON PAGINACIÓN"""
    try:
        # Obtener negocio y relaciones
        negocio = get_object_or_404(
            Negocios.objects.select_related('fkpropietario_neg', 'fktiponeg_neg'), 
            pkid_neg=id, 
            estado_neg='activo'
        )
        
        # Obtener perfil del cliente logueado
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # PRODUCTOS DEL NEGOCIO - CON MANEJO COMPLETO DE VARIANTES Y OFERTAS
        productos = Productos.objects.filter(
            fknegocioasociado_prod=negocio,
            estado_prod='disponible'
        ).select_related('fkcategoria_prod')
        
        # Preparar productos con manejo completo de variantes y ofertas
        productos_list = []
        hoy = timezone.now().date()
        
        for producto in productos:
            # Precio base del producto
            precio_base = float(producto.precio_prod) if producto.precio_prod else 0
            precio_final = precio_base
            descuento_porcentaje = 0
            ahorro = 0
            tiene_descuento = False
            
            # Verificar si tiene oferta activa usando SQL
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
            
            # OBTENER VARIANTES CON STOCK INDIVIDUAL
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
                    except Exception as e:
                        print(f"❌ Error procesando variante: {e}")
                        continue
            
            # Calcular stock total (producto base + variantes)
            stock_total = producto.stock_prod or 0
            if tiene_variantes:
                stock_variantes = sum(variante['stock_variante'] for variante in variantes_list)
                stock_total += stock_variantes
            
            # Datos completos del producto
            producto_data = {
                'producto': producto,
                'precio_base': precio_base,
                'precio_final': round(precio_final, 2),
                'tiene_descuento': tiene_descuento,
                'descuento_porcentaje': descuento_porcentaje,
                'ahorro': round(ahorro, 2),
                'tiene_variantes': tiene_variantes,
                'variantes': variantes_list,
                'stock': stock_total,  # Stock total considerando variantes
            }
            productos_list.append(producto_data)
        
        # RESEÑAS DEL NEGOCIO - CON PAGINACIÓN (5 POR PÁGINA)
        resenas_list = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            estado_resena='activa'
        ).select_related('fkusuario_resena__fkuser').order_by('-fecha_resena')
        
        # ✅ PAGINACIÓN: Mostrar solo 5 reseñas inicialmente
        paginator = Paginator(resenas_list, 5)  # 5 reseñas por página
        page_number = request.GET.get('page', 1)  # Página actual, por defecto 1
        resenas_paginadas = paginator.get_page(page_number)
        
        # ✅ CÁLCULO CORRECTO DE ESTADÍSTICAS DE RESEÑAS
        total_resenas = resenas_list.count()
        
        # Calcular promedio de calificación
        promedio_calificacion = resenas_list.aggregate(
            promedio=Avg('estrellas')
        )['promedio'] or 0
        
        # ✅ CÁLCULO CORRECTO DE DISTRIBUCIÓN POR ESTRELLAS
        distribucion_estrellas = []
        conteo_estrellas = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        
        # Contar reseñas por cada cantidad de estrellas
        for resena in resenas_list:
            if resena.estrellas in conteo_estrellas:
                conteo_estrellas[resena.estrellas] += 1
        
        # Crear distribución con porcentajes
        for estrellas in [5, 4, 3, 2, 1]:
            cantidad = conteo_estrellas[estrellas]
            porcentaje = (cantidad / total_resenas * 100) if total_resenas > 0 else 0
            
            distribucion_estrellas.append({
                'estrellas': estrellas,
                'cantidad': cantidad,
                'porcentaje': round(porcentaje, 1)
            })
        
        # ✅ CREAR DICCIONARIO DE ESTADÍSTICAS COMPATIBLE CON EL TEMPLATE
        estadisticas_resenas = {
            'promedio': round(promedio_calificacion, 1),
            'total_resenas': total_resenas,
            'distribucion': distribucion_estrellas,
        }
        
        # ✅ AGREGAR CAMPOS INDIVIDUALES PARA COMPATIBILIDAD CON EL TEMPLATE
        for item in distribucion_estrellas:
            estrellas = item['estrellas']
            estadisticas_resenas[f'porcentaje_{estrellas}'] = item['porcentaje']
            estadisticas_resenas[f'{estrellas}_estrellas'] = item['cantidad']
        
        # ✅ ASEGURAR QUE TODOS LOS CAMPOS EXISTAN (incluso si no hay reseñas)
        for star in [5, 4, 3, 2, 1]:
            if f'porcentaje_{star}' not in estadisticas_resenas:
                estadisticas_resenas[f'porcentaje_{star}'] = 0
            if f'{star}_estrellas' not in estadisticas_resenas:
                estadisticas_resenas[f'{star}_estrellas'] = 0
        
        # Verificar si el usuario actual ya reseñó este negocio
        usuario_ya_reseno = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            fkusuario_resena=perfil_cliente,
            estado_resena='activa'
        ).exists()
        
        # Obtener la reseña del usuario actual si existe
        reseña_usuario_actual = None
        if usuario_ya_reseno:
            reseña_usuario_actual = ResenasNegocios.objects.filter(
                fknegocio_resena=negocio,
                fkusuario_resena=perfil_cliente,
                estado_resena='activa'
            ).first()
        
        # Obtener carrito del usuario
        carrito_count = 0
        try:
            carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        except Exception as e:
            print(f"⚠️ Error obteniendo carrito: {e}")
        
        # DEBUG: Mostrar estadísticas en consola del servidor
        print(f"📊 ESTADÍSTICAS DE RESEÑAS PARA {negocio.nom_neg}:")
        print(f"   - Promedio: {estadisticas_resenas['promedio']}")
        print(f"   - Total reseñas: {total_resenas}")
        print(f"   - Distribución:")
        for item in distribucion_estrellas:
            print(f"     {item['estrellas']} estrellas: {item['cantidad']} ({item['porcentaje']}%)")
        
        contexto = {
            'negocio': negocio,
            'propietario': negocio.fkpropietario_neg,
            'tipo_negocio': negocio.fktiponeg_neg,
            'productos': productos_list,
            'perfil_cliente': perfil_cliente,
            'resenas': resenas_paginadas,  # ✅ Ahora es objeto paginado
            'estadisticas_resenas': estadisticas_resenas,
            'distribucion_estrellas': distribucion_estrellas,
            'usuario_ya_reseno': usuario_ya_reseno,
            'reseña_usuario_actual': reseña_usuario_actual,
            'carrito_count': carrito_count,
            'es_vista_logeada': True,
            'nombre': f"{request.user.first_name} {request.user.last_name}",
            
            # Flags para el template
            'hay_productos': len(productos_list) > 0,
            'hay_resenas': total_resenas > 0,
            'total_resenas': total_resenas,  # ✅ Total para mostrar
            'hay_mas_resenas': resenas_paginadas.has_next(),  # ✅ Para botón "Ver más"
            'pagina_actual': page_number,
            'total_paginas': paginator.num_pages,
        }
        
        return render(request, 'cliente/detalle_neg_logeado.html', contexto)
        
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, 'Complete su perfil para acceder a esta funcionalidad.')
        return redirect('completar_perfil')
    except Exception as e:
        print(f"❌ ERROR en detalle_negocio_logeado: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error al cargar el detalle del negocio: {str(e)}')
        return redirect('cliente_dashboard')  

@login_required
def reportar_negocio(request):
    """Vista para reportar un negocio o reseña"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            negocio_id = data.get('negocio_id')
            reseña_id = data.get('reseña_id')
            asunto = data.get('asunto')
            motivo = data.get('motivo')
            descripcion = data.get('descripcion', '')
            
            # Validaciones
            if not negocio_id or not asunto or not motivo:
                return JsonResponse({
                    'success': False, 
                    'message': 'Faltan campos obligatorios'
                })
            
            # Obtener perfil del usuario
            perfil_usuario = UsuarioPerfil.objects.get(fkuser=request.user)
            
            # Obtener negocio
            negocio = Negocios.objects.get(pkid_neg=negocio_id)
            
            # Determinar tipo de reporte
            tipo_reporte = 'resena' if reseña_id else 'negocio'
            reseña_obj = None
            
            if tipo_reporte == 'resena':
                # Verificar que la reseña existe y pertenece al negocio
                reseña_obj = ResenasNegocios.objects.get(
                    pkid_resena=reseña_id,
                    fknegocio_resena=negocio,
                    estado_resena='activa'
                )
                
                # Verificar que el usuario no reporte su propia reseña
                if reseña_obj.fkusuario_resena == perfil_usuario:
                    return JsonResponse({
                        'success': False, 
                        'message': 'No puedes reportar tu propia reseña'
                    })
                
                # Verificar que el usuario no haya reportado esta reseña antes
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
                # Verificar que el usuario no reporte su propio negocio
                if negocio.fkpropietario_neg == perfil_usuario:
                    return JsonResponse({
                        'success': False, 
                        'message': 'No puedes reportar tu propio negocio'
                    })
                
                # Verificar que el usuario no haya reportado este negocio antes
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
            
            # Crear el reporte
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
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'Error al procesar el reporte: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@login_required
def obtener_opciones_reporte(request):
    """Obtener opciones de reporte para el modal"""
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

# ==================== FUNCIONES DE GESTIÓN DE STOCK ====================

def descontar_stock_pedido(pedido):
    """
    Descontar stock cuando se procesa un pedido
    """
    try:
        detalles_pedido = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
        
        for detalle in detalles_pedido:
            producto = detalle.fkproducto_detalle
            cantidad = detalle.cantidad_detalle
            
            # Buscar el item del carrito original para obtener información de variantes
            try:
                # Intentar encontrar si era un producto con variante
                carrito_item = CarritoItem.objects.filter(
                    fkproducto=producto,
                    variante_id__isnull=False
                ).first()
                
                if carrito_item and carrito_item.variante_id:
                    # Es una variante - descontar stock de la variante
                    variante = VariantesProducto.objects.get(
                        id_variante=carrito_item.variante_id,
                        producto=producto
                    )
                    if variante.stock_variante >= cantidad:
                        variante.stock_variante -= cantidad
                        variante.save()
                        print(f"✅ Stock descontado - Variante: {variante.nombre_variante}, Cantidad: {cantidad}, Stock restante: {variante.stock_variante}")
                    else:
                        print(f"⚠️ Stock insuficiente en variante: {variante.nombre_variante}")
                
                else:
                    # Es producto base - descontar stock del producto
                    if producto.stock_prod >= cantidad:
                        producto.stock_prod -= cantidad
                        producto.save()
                        print(f"✅ Stock descontado - Producto: {producto.nom_prod}, Cantidad: {cantidad}, Stock restante: {producto.stock_prod}")
                    else:
                        print(f"⚠️ Stock insuficiente en producto: {producto.nom_prod}")
                        
            except VariantesProducto.DoesNotExist:
                # Si no existe la variante, descontar del producto base
                if producto.stock_prod >= cantidad:
                    producto.stock_prod -= cantidad
                    producto.save()
                    print(f"✅ Stock descontado (fallback) - Producto: {producto.nom_prod}, Cantidad: {cantidad}, Stock restante: {producto.stock_prod}")
                else:
                    print(f"⚠️ Stock insuficiente en producto (fallback): {producto.nom_prod}")
            
            except Exception as e:
                print(f"❌ Error al descontar stock para {producto.nom_prod}: {e}")
                continue
        
        return True
        
    except Exception as e:
        print(f"❌ Error general en descontar_stock_pedido: {e}")
        return False

def restaurar_stock_pedido(pedido):
    """
    Restaurar stock cuando se cancela un pedido
    """
    try:
        detalles_pedido = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
        
        for detalle in detalles_pedido:
            producto = detalle.fkproducto_detalle
            cantidad = detalle.cantidad_detalle
            
            # Buscar el item del carrito original para obtener información de variantes
            try:
                # Intentar encontrar si era un producto con variante
                carrito_item = CarritoItem.objects.filter(
                    fkproducto=producto,
                    variante_id__isnull=False
                ).first()
                
                if carrito_item and carrito_item.variante_id:
                    # Es una variante - restaurar stock de la variante
                    variante = VariantesProducto.objects.get(
                        id_variante=carrito_item.variante_id,
                        producto=producto
                    )
                    variante.stock_variante += cantidad
                    variante.save()
                    print(f"✅ Stock restaurado - Variante: {variante.nombre_variante}, Cantidad: {cantidad}, Stock actual: {variante.stock_variante}")
                
                else:
                    # Es producto base - restaurar stock del producto
                    producto.stock_prod += cantidad
                    producto.save()
                    print(f"✅ Stock restaurado - Producto: {producto.nom_prod}, Cantidad: {cantidad}, Stock actual: {producto.stock_prod}")
                        
            except VariantesProducto.DoesNotExist:
                # Si no existe la variante, restaurar al producto base
                producto.stock_prod += cantidad
                producto.save()
                print(f"✅ Stock restaurado (fallback) - Producto: {producto.nom_prod}, Cantidad: {cantidad}, Stock actual: {producto.stock_prod}")
            
            except Exception as e:
                print(f"❌ Error al restaurar stock para {producto.nom_prod}: {e}")
                continue
        
        return True
        
    except Exception as e:
        print(f"❌ Error general en restaurar_stock_pedido: {e}")
        return False

def validar_stock_pedido(pedido):
    """
    Validar que hay suficiente stock para todos los items del pedido
    """
    try:
        detalles_pedido = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
        
        for detalle in detalles_pedido:
            producto = detalle.fkproducto_detalle
            cantidad = detalle.cantidad_detalle
            
            # Buscar información de variantes
            carrito_item = CarritoItem.objects.filter(
                fkproducto=producto,
                variante_id__isnull=False
            ).first()
            
            if carrito_item and carrito_item.variante_id:
                # Validar stock de variante
                try:
                    variante = VariantesProducto.objects.get(
                        id_variante=carrito_item.variante_id,
                        producto=producto
                    )
                    if variante.stock_variante < cantidad:
                        return False, f"Stock insuficiente para {producto.nom_prod} - {variante.nombre_variante}"
                except VariantesProducto.DoesNotExist:
                    # Si la variante no existe, validar producto base
                    if producto.stock_prod < cantidad:
                        return False, f"Stock insuficiente para {producto.nom_prod}"
            else:
                # Validar stock de producto base
                if producto.stock_prod < cantidad:
                    return False, f"Stock insuficiente para {producto.nom_prod}"
        
        return True, "Stock válido"
        
    except Exception as e:
        return False, f"Error validando stock: {str(e)}"
    
@login_required(login_url='/auth/login/')
@require_POST
def agregar_al_carrito(request):
    """Agregar producto al carrito - CON validación de stock pero SIN descontarlo"""
    
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        cantidad = int(data.get('cantidad', 1))
        variante_id = data.get('variante_id', None)
        
        if not producto_id:
            return JsonResponse({'success': False, 'message': 'ID de producto requerido'}, status=400)
        
        # Obtener usuario y producto
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        producto = Productos.objects.get(pkid_prod=producto_id)
        
        if producto.estado_prod != 'disponible':
            return JsonResponse({'success': False, 'message': 'Producto no disponible'}, status=400)
        
        # Precio base del producto
        precio_final = float(producto.precio_prod)
        variante_nombre = None
        variante_id_int = None
        
        # ✅ VALIDAR STOCK AL AGREGAR AL CARRITO
        aplicar_descuento = True  # Por defecto SÍ aplica descuento al producto base
        
        if variante_id and variante_id != 'base':
            try:
                variante_id_int = int(variante_id)
                variante = VariantesProducto.objects.get(
                    id_variante=variante_id_int, 
                    producto=producto,
                    estado_variante='activa'
                )
                
                print(f"🔍 DEBUG: Procesando variante ID {variante_id_int} - {variante.nombre_variante}")
                print(f"🔍 DEBUG: Stock variante: {variante.stock_variante}, Cantidad solicitada: {cantidad}")
                
                # ✅ VALIDAR STOCK DE LA VARIANTE
                if variante.stock_variante < cantidad:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Stock insuficiente. Solo quedan {variante.stock_variante} unidades de esta variante'
                    }, status=400)
                
                # Sumar precio adicional si existe
                if variante.precio_adicional and float(variante.precio_adicional) > 0:
                    precio_final += float(variante.precio_adicional)
                    print(f"🔍 DEBUG: Precio con variante - Base: {producto.precio_prod}, Adicional: {variante.precio_adicional}, Total: {precio_final}")
                    
                variante_nombre = variante.nombre_variante
                
                # ✅ LAS VARIANTES NO TIENEN DESCUENTO
                aplicar_descuento = False
                print(f"🔍 DEBUG: Variante detectada - NO se aplicarán descuentos")
                
            except ValueError:
                return JsonResponse({'success': False, 'message': 'ID de variante inválido'}, status=400)
            except VariantesProducto.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Variante no encontrada'}, status=404)
        else:
            # ✅ VALIDAR STOCK DEL PRODUCTO BASE
            print(f"🔍 DEBUG: Producto base - Stock: {producto.stock_prod}, Cantidad solicitada: {cantidad}")
            if (producto.stock_prod or 0) < cantidad:
                return JsonResponse({
                    'success': False, 
                    'message': f'Stock insuficiente. Solo quedan {producto.stock_prod} unidades'
                }, status=400)
        
        # ✅ APLICAR OFERTAS SOLO SI CORRESPONDE (NO PARA VARIANTES)
        precio_original = precio_final  # Guardar precio sin descuento para debug
        
        if aplicar_descuento:
            hoy = timezone.now().date()
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT porcentaje_descuento 
                        FROM promociones 
                        WHERE fkproducto_id = %s 
                        AND estado_promo = 'activa'
                        AND fecha_inicio <= %s 
                        AND fecha_fin >= %s
                        LIMIT 1
                    """, [producto_id, hoy, hoy])
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        descuento = float(result[0])
                        if descuento > 0:
                            precio_original = precio_final
                            precio_final = precio_final * (1 - (descuento / 100))
                            print(f"🔍 DEBUG: Descuento aplicado - Porcentaje: {descuento}%, Original: {precio_original}, Final: {precio_final}")
            except Exception as e:
                print(f"🔍 DEBUG: Error al verificar descuento: {e}")
                pass
        else:
            print(f"🔍 DEBUG: No se aplica descuento (es variante)")
        
        # Crear o actualizar carrito
        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
        
        # ✅ VERIFICAR SI EL PRODUCTO YA EXISTE EN EL CARRITO
        item_existente = None
        
        if variante_id_int:
            # Buscar item con misma variante
            item_existente = CarritoItem.objects.filter(
                fkcarrito=carrito,
                fkproducto=producto,
                variante_id=variante_id_int
            ).first()
            print(f"🔍 DEBUG: Buscando item existente con variante {variante_id_int} - Encontrado: {item_existente is not None}")
        else:
            # Buscar item sin variante
            item_existente = CarritoItem.objects.filter(
                fkcarrito=carrito,
                fkproducto=producto,
                variante_id__isnull=True
            ).first()
            print(f"🔍 DEBUG: Buscando item existente sin variante - Encontrado: {item_existente is not None}")
        
        if item_existente:
            # ✅ SI EXISTE, ACTUALIZAR CANTIDAD
            nueva_cantidad = item_existente.cantidad + cantidad
            
            # ✅ VALIDAR STOCK NUEVAMENTE PARA LA NUEVA CANTIDAD TOTAL
            stock_disponible = producto.stock_prod
            if variante_id_int:
                stock_disponible = variante.stock_variante
                
            if stock_disponible < nueva_cantidad:
                return JsonResponse({
                    'success': False,
                    'message': f'Stock insuficiente. Solo puedes agregar {stock_disponible - item_existente.cantidad} unidades más'
                }, status=400)
            
            item_existente.cantidad = nueva_cantidad
            item_existente.precio_unitario = precio_final  # Actualizar precio por si hay cambios
            item_existente.save()
            
            mensaje = 'Cantidad actualizada en el carrito'
            print(f"🔍 DEBUG: Item actualizado - Nueva cantidad: {nueva_cantidad}, Precio: {precio_final}")
            
        else:
            # ✅ SI NO EXISTE, CREAR NUEVO ITEM
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
            print(f"🔍 DEBUG: Nuevo item creado - Cantidad: {cantidad}, Precio: {precio_final}, Variante: {variante_nombre}")
        
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        # ✅ CONSTRUIR NOMBRE COMPLETO DEL PRODUCTO CON VARIANTE
        nombre_producto_completo = producto.nom_prod
        if variante_nombre:
            nombre_producto_completo = f"{producto.nom_prod} - {variante_nombre}"
        
        response_data = {
            'success': True,
            'message': mensaje,
            'carrito_count': carrito_count,
            'producto_nombre': nombre_producto_completo,
            'precio_unitario': precio_final,
            'cantidad': cantidad,
            'subtotal': precio_final * cantidad,
            'tiene_descuento': aplicar_descuento and precio_final < precio_original,
            'item_actualizado': item_existente is not None,
            'es_variante': variante_id_int is not None,
        }
        
        if variante_nombre:
            response_data['variante_nombre'] = variante_nombre
        
        print(f"🔍 DEBUG: Respuesta final - {response_data}")
        
        return JsonResponse(response_data)
        
    except Productos.DoesNotExist:
        print(f"❌ ERROR: Producto no encontrado - ID: {producto_id}")
        return JsonResponse({'success': False, 'message': 'Producto no encontrado'}, status=404)
    except UsuarioPerfil.DoesNotExist:
        print(f"❌ ERROR: Perfil de usuario no encontrado")
        return JsonResponse({'success': False, 'message': 'Perfil de usuario no encontrado'}, status=404)
    except Exception as e:
        print(f"❌ ERROR: Error interno del servidor: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'message': 'Error interno del servidor'
        }, status=500)

@login_required(login_url='/auth/login/')
@require_POST
def actualizar_cantidad_carrito(request):
    """Actualizar cantidad de un item en el carrito - VERSIÓN CORREGIDA"""
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
            # ✅ CORRECCIÓN: VERIFICAR STOCK SEGÚN SI ES VARIANTE O PRODUCTO BASE
            stock_disponible = 0
            
            if item.variante_id:
                # Es una variante - verificar stock de la variante específica
                try:
                    variante = VariantesProducto.objects.get(
                        id_variante=item.variante_id,
                        producto=item.fkproducto,
                        estado_variante='activa'
                    )
                    stock_disponible = variante.stock_variante or 0
                    print(f"🔍 DEBUG actualizar_cantidad: Variante {variante.nombre_variante} - Stock disponible: {stock_disponible}, Nueva cantidad: {nueva_cantidad}")
                except VariantesProducto.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'La variante seleccionada ya no está disponible'
                    })
            else:
                # Es producto base - verificar stock del producto
                stock_disponible = item.fkproducto.stock_prod or 0
                print(f"🔍 DEBUG actualizar_cantidad: Producto base - Stock disponible: {stock_disponible}, Nueva cantidad: {nueva_cantidad}")
            
            # Verificar stock disponible
            if stock_disponible < nueva_cantidad:
                return JsonResponse({
                    'success': False,
                    'message': f'Stock insuficiente. Solo quedan {stock_disponible} unidades'
                })
            
            item.cantidad = nueva_cantidad
            item.save()
        
        # Obtener nuevo conteo
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        return JsonResponse({
            'success': True,
            'carrito_count': carrito_count
        })
        
    except Exception as e:
        print(f"❌ ERROR actualizar_cantidad: {e}")
        return JsonResponse({'success': False, 'message': 'Error interno del servidor'})

@login_required(login_url='/auth/login/')
@require_POST
def eliminar_item_carrito(request):
    """Eliminar item del carrito - VERSIÓN CORREGIDA"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
        item = CarritoItem.objects.get(pkid_item=item_id, fkcarrito=carrito)
        item.delete()
        
        # Obtener nuevo conteo
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        return JsonResponse({
            'success': True,
            'carrito_count': carrito_count
        })
        
    except Exception as e:
        print(f"❌ ERROR eliminar_item: {e}")
        return JsonResponse({'success': False, 'message': 'Error interno del servidor'})
          
@login_required(login_url='/auth/login/')
def ver_carrito(request):
    """Vista para ver el carrito del usuario"""
    try:
        # Obtener perfil del usuario
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # Obtener carrito del usuario
        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            items_carrito = CarritoItem.objects.filter(fkcarrito=carrito).select_related(
                'fkproducto', 'fknegocio'
            )
        except Carrito.DoesNotExist:
            items_carrito = []
            carrito = None
        
        # Calcular totales
        total_carrito = 0
        items_detallados = []
        
        for item in items_carrito:
            subtotal = float(item.precio_unitario) * item.cantidad
            
            # Verificar si el producto tiene oferta activa
            precio_original = float(item.fkproducto.precio_prod)
            tiene_oferta = item.precio_unitario < precio_original
            
            items_detallados.append({
                'item': item,
                'subtotal': subtotal,
                'tiene_oferta': tiene_oferta,
                'precio_original': precio_original,
                'ahorro': (precio_original - float(item.precio_unitario)) * item.cantidad if tiene_oferta else 0
            })
            
            total_carrito += subtotal
        
        context = {
            'items_carrito': items_detallados,
            'total_carrito': total_carrito,
            'carrito_count': len(items_carrito),
            'carrito_vacio': len(items_carrito) == 0
        }
        
        return render(request, 'Cliente/carrito.html', context)
        
    except Exception as e:
        return render(request, 'Cliente/carrito.html', {
            'items_carrito': [],
            'total_carrito': 0,
            'carrito_count': 0,
            'carrito_vacio': True
        })

@login_required(login_url='/auth/login/')
def carrito_data(request):
    """Obtener datos del carrito para AJAX - VERSIÓN MEJORADA PARA VARIANTES"""
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
        items = CarritoItem.objects.filter(fkcarrito=carrito).select_related('fkproducto', 'fknegocio')
        
        carrito_items = []
        subtotal = 0
        ahorro_total = 0
        
        for item in items:
            # ✅ CONSTRUIR NOMBRE COMPLETO CON VARIANTE
            nombre_completo = item.fkproducto.nom_prod
            if item.variante_seleccionada:
                nombre_completo = f"{item.fkproducto.nom_prod} - {item.variante_seleccionada}"
            
            # Obtener precio base del producto
            precio_base = float(item.fkproducto.precio_prod)
            
            # ✅ CORRECCIÓN: Si hay variante, sumar precio adicional al precio base
            precio_original = precio_base
            stock_disponible = item.fkproducto.stock_prod or 0
            
            if item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(id_variante=item.variante_id)
                    if variante.precio_adicional:
                        precio_original += float(variante.precio_adicional)
                    # ✅ IMPORTANTE: Obtener stock de la variante específica
                    stock_disponible = variante.stock_variante or 0
                    print(f"🔍 DEBUG carrito_data: Variante {variante.nombre_variante} - Stock: {stock_disponible}")
                except VariantesProducto.DoesNotExist:
                    print(f"⚠️ WARNING: Variante no encontrada - ID: {item.variante_id}")
                    pass
            
            precio_actual = float(item.precio_unitario)
            
            # ✅ CORREGIDO: Solo calcular ahorro si es producto base (sin variante) y realmente hay descuento
            tiene_oferta = (item.variante_id is None) and (precio_actual < precio_original)
            ahorro_item = (precio_original - precio_actual) * item.cantidad if tiene_oferta else 0
            
            carrito_items.append({
                'id': item.pkid_item,
                'nombre': nombre_completo,  # ✅ USAR NOMBRE COMPLETO
                'negocio': item.fknegocio.nom_neg,
                'cantidad': item.cantidad,
                'precio_unitario': precio_actual,
                'precio_original': precio_original,
                'tiene_oferta': tiene_oferta,
                'imagen': item.fkproducto.img_prod.url if item.fkproducto.img_prod else None,
                'variante': item.variante_seleccionada,  # ✅ INCLUIR INFO DE VARIANTE
                'es_variante': bool(item.variante_id),  # ✅ INDICAR SI ES VARIANTE
                'stock_disponible': stock_disponible,  # ✅ INCLUIR STOCK DISPONIBLE
                'debug_info': {
                    'precio_base': precio_base,
                    'precio_original': precio_original,
                    'precio_actual': precio_actual,
                    'variante_id': item.variante_id,
                    'stock_disponible': stock_disponible
                }
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
            'debug_total_items': len(carrito_items)
        }
        
        print(f"🔍 DEBUG carrito_data: Respuesta - {len(carrito_items)} items, Subtotal: {subtotal}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ ERROR carrito_data: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'items': [], 'totales': {}})

@login_required(login_url='/auth/login/')
@require_POST
@csrf_exempt
def procesar_pedido(request):
    """Procesar pedido del carrito - CON descuento de stock"""
    try:
        data = json.loads(request.body)
        metodo_pago = data.get('metodo_pago')
        metodo_pago_texto = data.get('metodo_pago_texto')
        banco = data.get('banco', None)
        datos_billetera = data.get('datos_billetera', {})

        # Obtener usuario autenticado y perfil
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

        print(f"🔍 DEBUG procesar_pedido: Procesando {items_carrito.count()} items del carrito")

        # ✅ PRIMERO VALIDAR STOCK DE TODOS LOS ITEMS
        for item_carrito in items_carrito:
            # Validar stock antes de procesar el pedido
            if item_carrito.variante_id:
                # Validar stock de variante
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
                # Validar stock de producto base
                if (item_carrito.fkproducto.stock_prod or 0) < item_carrito.cantidad:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Stock insuficiente para {item_carrito.fkproducto.nom_prod}. Solo quedan {item_carrito.fkproducto.stock_prod} unidades'
                    }, status=400)

        # ✅ SI PASÓ LA VALIDACIÓN DE STOCK, CREAR EL PEDIDO
        for item_carrito in items_carrito:
            monto_item = float(item_carrito.precio_unitario) * item_carrito.cantidad
            total_pedido += monto_item
            negocio = item_carrito.fknegocio
            
            print(f"🔍 DEBUG procesar_pedido: Item - {item_carrito.fkproducto.nom_prod}, "
                  f"Variante: {item_carrito.variante_seleccionada}, "
                  f"Precio: {item_carrito.precio_unitario}, "
                  f"Cantidad: {item_carrito.cantidad}, "
                  f"Subtotal: {monto_item}")
            
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
                'variante_id': item_carrito.variante_id
            })

        negocio_principal = None
        mayor_monto = 0

        for negocio, monto in negocios_involucrados.items():
            if monto > mayor_monto:
                mayor_monto = monto
                negocio_principal = negocio

        print(f"🔍 DEBUG procesar_pedido: Total pedido: {total_pedido}, Negocio principal: {negocio_principal.nom_neg}")

        # CREAR EL PEDIDO
        pedido = Pedidos.objects.create(
            fkusuario_pedido=perfil_cliente,
            fknegocio_pedido=negocio_principal,
            estado_pedido='pendiente',
            total_pedido=total_pedido,
            metodo_pago=metodo_pago,
            metodo_pago_texto=metodo_pago_texto,
            banco=banco,
            fecha_pedido=timezone.now(),
            fecha_actualizacion=timezone.now()
        )

        # ✅ CREAR DETALLES DEL PEDIDO
        for item_carrito in items_carrito:
            DetallesPedido.objects.create(
                fkpedido_detalle=pedido,
                fkproducto_detalle=item_carrito.fkproducto,
                cantidad_detalle=item_carrito.cantidad,
                precio_unitario=item_carrito.precio_unitario
            )

        # ✅ DESCONTAR STOCK DEL PEDIDO
        stock_descontado = descontar_stock_pedido(pedido)
        
        if not stock_descontado:
            print("⚠️ ADVERTENCIA: No se pudo descontar el stock correctamente")

        # Crear pagos para cada negocio involucrado
        for negocio, monto in negocios_involucrados.items():
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
            print(f"🔍 DEBUG procesar_pedido: Pago creado para negocio {negocio.nom_neg} - Monto: {monto}")

        # Limpiar carrito
        items_carrito.delete()
        print(f"🔍 DEBUG procesar_pedido: Carrito limpiado")

        # ✅ ENVIAR COMPROBANTE POR CORREO
        try:
            email_cliente = auth_user.email
            if email_cliente:
                enviar_comprobante_pedido(email_cliente, pedido, items_detallados, negocios_involucrados)
                print(f"📧 DEBUG procesar_pedido: Correo enviado a: {email_cliente}")
            else:
                print("⚠️ DEBUG procesar_pedido: El usuario no tiene email configurado")
        except Exception as e:
            print(f"⚠️ DEBUG procesar_pedido: Error enviando correo: {e}")

        # Formatear fecha para la respuesta JSON (hora Colombia)
        fecha_colombia = timezone.localtime(pedido.fecha_pedido)
        fecha_formateada = fecha_colombia.strftime("%d/%m/%Y %I:%M %p").lower()

        response_data = {
            'success': True,
            'message': 'Pedido procesado exitosamente. Stock descontado correctamente.',
            'numero_pedido': pedido.pkid_pedido,
            'total': total_pedido,
            'metodo_pago': metodo_pago_texto,
            'fecha': fecha_formateada,
            'estado_pedido': pedido.estado_pedido,
            'pagos_creados': len(negocios_involucrados),
            'negocio_principal': negocio_principal.nom_neg,
            'correo_enviado': bool(email_cliente),
            'stock_validado': True,
            'stock_descontado': stock_descontado,  # ✅ INDICAR QUE SE DESCONTÓ EL STOCK
        }

        print(f"🔍 DEBUG procesar_pedido: Pedido {pedido.pkid_pedido} procesado exitosamente - STOCK DESCONTADO")
        return JsonResponse(response_data)

    except Exception as e:
        print(f"❌ ERROR procesar_pedido: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': 'Error interno del servidor al procesar el pedido'}, status=500)  

def enviar_comprobante_pedido(email_cliente, pedido, items_detallados, negocios_involucrados):
    """Enviar comprobante de pedido por correo electrónico"""
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
        
    except Exception as e:
        raise e

@login_required(login_url='/auth/login/')
def guardar_resena(request):
    """Guardar reseña del negocio - PERMITE MÚLTIPLES RESEÑAS"""
    if request.method == 'POST':
        try:
            estrellas = int(request.POST.get('estrellas', 5))
            comentario = request.POST.get('comentario', '').strip()
            negocio_id = request.POST.get('fknegocio_resena')
            es_vista_logeada = request.POST.get('es_vista_logeada', False)

            # Validaciones básicas
            if not negocio_id:
                messages.error(request, 'ID de negocio requerido')
                return redirect('cliente_dashboard')
            
            if estrellas < 1 or estrellas > 5:
                messages.error(request, 'La calificación debe estar entre 1 y 5 estrellas')
                if es_vista_logeada:
                    return redirect('detalle_negocio_logeado', id=negocio_id)
                else:
                    return redirect('detalle_negocio', id=negocio_id)

            # Obtener perfil del cliente
            perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
            
            # Obtener negocio
            negocio = get_object_or_404(Negocios, pkid_neg=negocio_id)

            # ✅ CORRECCIÓN: PERMITIR MÚLTIPLES RESEÑAS DEL MISMO USUARIO
            # Crear nueva reseña sin verificar si ya existe
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
            
            # Redirigir según la vista de origen
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
        except Exception as e:
            messages.error(request, f'Error al guardar la reseña: {str(e)}')
            if negocio_id:
                if es_vista_logeada:
                    return redirect('detalle_negocio_logeado', id=negocio_id)
                else:
                    return redirect('detalle_negocio', id=negocio_id)
            return redirect('cliente_dashboard')
    
    # Si no es POST, redirigir al dashboard
    return redirect('cliente_dashboard')

@login_required(login_url='/auth/login/')
def productos_filtrados_logeado(request):
    """Vista de productos filtrados para usuarios logueados - VERSIÓN CORREGIDA"""
    
    # Obtener parámetros de filtro de la URL
    filtro_tipo = request.GET.get('filtro', '')
    categoria_id = request.GET.get('categoria', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    ordenar = request.GET.get('ordenar', '')
    buscar = request.GET.get('buscar', '')
    
    # Query base
    productos = Productos.objects.filter(estado_prod='disponible')
    
    # Aplicar filtros según el parámetro
    if filtro_tipo == 'ofertas':
        from django.db import connection
        from datetime import date
        
        hoy = date.today()
        
        # Consulta directa SQL para evitar problemas de serialización JSON
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
        
        # Filtrar productos
        if productos_con_ofertas_ids:
            productos = productos.filter(pkid_prod__in=productos_con_ofertas_ids)
        else:
            productos = productos.none()
        
        titulo_filtro = "Ofertas Especiales"
    
    elif filtro_tipo == 'destacados':
        # Filtrar productos destacados (con stock disponible)
        productos = productos.filter(stock_prod__gt=0)
        titulo_filtro = "Productos Destacados"
    
    elif filtro_tipo == 'economicos':
        # Filtrar productos económicos (precio más bajo)
        productos = productos.order_by('precio_prod')
        titulo_filtro = "Productos Baratos"
    
    elif filtro_tipo == 'nuevos':
        # Filtrar productos nuevos (recientemente agregados)
        productos = productos.order_by('-fecha_creacion')
        titulo_filtro = "Nuevos Productos"
    
    elif filtro_tipo == 'mas-vendidos':
        # Filtrar productos con stock disponible
        productos = productos.filter(stock_prod__gt=0)
        titulo_filtro = "Productos Disponibles"
    
    else:
        titulo_filtro = "Todos los Productos"

    # Aplicar búsqueda por texto
    if buscar:
        productos = productos.filter(
            models.Q(nom_prod__icontains=buscar) |
            models.Q(desc_prod__icontains=buscar)
        )

    # Aplicar filtro por categoría si se especifica
    if categoria_id:
        productos = productos.filter(fkcategoria_prod_id=categoria_id)
    
    # Aplicar filtro por rango de precios
    if precio_min:
        productos = productos.filter(precio_prod__gte=precio_min)
    if precio_max:
        productos = productos.filter(precio_prod__lte=precio_max)
    
    # Aplicar ordenamiento
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
        # Orden por defecto
        productos = productos.order_by('-fecha_creacion')
    
    # Obtener categorías para el filtro
    categorias = CategoriaProductos.objects.annotate(
        num_productos=models.Count('productos', filter=models.Q(productos__estado_prod='disponible'))
    )
    
    # Obtener negocios para el filtro
    negocios = Negocios.objects.annotate(
        num_productos=models.Count('productos', filter=models.Q(productos__estado_prod='disponible'))
    ).filter(estado_neg='activo')
    
    # Preparar datos para el template
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
        
        # Verificar si tiene variantes
        variantes = VariantesProducto.objects.filter(
            producto=producto, 
            estado_variante='activa'
        )
        
        if variantes.exists():
            producto_data['tiene_variantes'] = True
            
            # Preparar datos detallados de variantes
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
        
        # Consulta directa para promociones
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
                # Convertir el descuento
                descuento = float(porcentaje_descuento)
                
                producto_data['precio_final'] = float(producto.precio_prod) * (1 - descuento / 100)
                producto_data['tiene_descuento'] = True
                producto_data['descuento_porcentaje'] = descuento
                producto_data['ahorro'] = float(producto.precio_prod) - producto_data['precio_final']
            except (ValueError, TypeError):
                pass
        
        productos_data.append(producto_data)
    
    # Paginación
    paginator = Paginator(productos_data, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ==================== OBTENER CARRITO COUNT ====================
    carrito_count = 0
    try:
        # Obtener perfil del usuario
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # Intentar obtener el carrito existente
        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        except Carrito.DoesNotExist:
            # Si no existe carrito, crear uno vacío
            carrito = Carrito.objects.create(fkusuario_carrito=perfil_cliente)
            carrito_count = 0
            
    except Exception as e:
        print(f"❌ Error obteniendo carrito count: {e}")
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
        'carrito_count': carrito_count,  # ✅ AÑADIDO - ESTO ES LO QUE FALTABA
    }
    
    return render(request, 'Cliente/productos_filtros_logeado.html', context)

@login_required(login_url='/auth/login/')
def mis_pedidos_data(request):
    """Obtener los datos de los pedidos del usuario para el panel lateral"""
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=request.user)
        
        # Obtener pedidos del usuario ordenados por fecha más reciente
        pedidos = Pedidos.objects.filter(
            fkusuario_pedido=perfil_cliente
        ).order_by('-fecha_pedido')[:10]  # Últimos 10 pedidos
        
        pedidos_data = []
        
        for pedido in pedidos:
            # Obtener detalles del pedido
            detalles = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
            
            productos_data = []
            for detalle in detalles:
                productos_data.append({
                    'nombre': detalle.fkproducto_detalle.nom_prod,
                    'cantidad': detalle.cantidad_detalle,
                    'precio_unitario': float(detalle.precio_unitario),
                    'imagen': detalle.fkproducto_detalle.img_prod.url if detalle.fkproducto_detalle.img_prod else None
                })
            
            # Calcular si se puede cancelar (menos de 1 hora)
            tiempo_transcurrido = timezone.now() - pedido.fecha_pedido
            puede_cancelar = (tiempo_transcurrido < timedelta(hours=1) and 
                            pedido.estado_pedido in ['pendiente', 'confirmado'])
            
            # Calcular tiempo restante para cancelar
            tiempo_restante = None
            if puede_cancelar:
                tiempo_restante_segundos = timedelta(hours=1).total_seconds() - tiempo_transcurrido.total_seconds()
                horas = int(tiempo_restante_segundos // 3600)
                minutos = int((tiempo_restante_segundos % 3600) // 60)
                tiempo_restante = f"{minutos} min"
                if horas > 0:
                    tiempo_restante = f"{horas}h {minutos}min"
            
            # Mapear estados a texto legible
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
        
    except Exception as e:
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
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'Error al cancelar el pedido'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    })
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
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'Error al cancelar el pedido'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    })