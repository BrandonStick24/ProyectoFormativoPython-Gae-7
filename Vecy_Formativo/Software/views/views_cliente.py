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

def principal(request):
    negocios = Negocios.objects.filter(estado_neg='activo')
    categorias = CategoriaProductos.objects.all()[:20]
    tipo_negocios = TipoNegocio.objects.all()
    
    todos_productos = Productos.objects.filter(estado_prod='disponible')
    
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
    
    # CATEGORÍAS POPULARES - ACTUALIZADO CON RELATED_NAME
    categorias_populares = CategoriaProductos.objects.annotate(
        num_productos=Count('productos', filter=Q(productos__estado_prod='disponible'))
    ).filter(
        num_productos__gt=0
    ).order_by('-num_productos')[:8]
    
    # Si no hay suficientes categorías con productos, completar con las más recientes
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
        'productos_oferta': productos_oferta,
        'categorias_populares': categorias_populares,
        'productos_mas_vendidos': productos_mas_vendidos_data,
        'productos_con_variantes': productos_con_variantes,
        'hay_promociones': len(productos_oferta) > 0,
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
                        
                        # CALCULAR PRECIO CORRECTO CONSIDERANDO VARIANTES
                        precio_base = float(producto.precio_prod) if producto.precio_prod else 0
                        variante_nombre = None
                        
                        # Si hay variante específica en la promoción
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
                        
                        # CREAR TÍTULO CORTO Y DESCRIPCIÓN MEJORADA
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

        # PRODUCTOS BARATOS - CON CÁLCULO CORRECTO DE DESCUENTOS POR VARIANTE
        productos_baratos_data = []
        try:
            productos_baratos = Productos.objects.filter(
                estado_prod='disponible',
                precio_prod__lte=50000
            ).order_by('precio_prod')[:12]
            
            for producto in productos_baratos:
                try:
                    # PRECIO BASE DEL PRODUCTO
                    precio_base_producto = float(producto.precio_prod) if producto.precio_prod else 0
                    precio_final_producto = precio_base_producto
                    descuento_porcentaje_producto = 0
                    ahorro_producto = 0
                    
                    # BUSCAR PROMOCIÓN ACTIVA PARA EL PRODUCTO BASE
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT p.porcentaje_descuento 
                            FROM promociones p
                            WHERE p.fkproducto_id = %s 
                            AND p.variante_id IS NULL
                            AND p.estado_promo = 'activa'
                            AND p.fecha_inicio <= %s 
                            AND p.fecha_fin >= %s
                            AND p.porcentaje_descuento > 0
                            LIMIT 1
                        """, [producto.pkid_prod, hoy, hoy])
                        
                        result = cursor.fetchone()
                        if result and result[0] is not None:
                            try:
                                descuento_porcentaje_producto = float(result[0])
                                ahorro_producto = precio_base_producto * (descuento_porcentaje_producto / 100)
                                precio_final_producto = precio_base_producto - ahorro_producto
                            except (ValueError, TypeError):
                                descuento_porcentaje_producto = 0
                                precio_final_producto = precio_base_producto
                                ahorro_producto = 0
                    
                    # VARIANTES DEL PRODUCTO - CON CÁLCULO INDEPENDIENTE PARA CADA UNA
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
                                # CALCULAR PRECIO BASE DE LA VARIANTE
                                precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                                precio_base_variante = precio_base_producto + precio_adicional
                                precio_final_variante = precio_base_variante
                                descuento_porcentaje_variante = 0
                                ahorro_variante = 0
                                
                                # ✅ CORRECCIÓN: BUSCAR DESCUENTO ESPECÍFICO PARA ESTA VARIANTE
                                with connection.cursor() as cursor:
                                    cursor.execute("""
                                        SELECT p.porcentaje_descuento 
                                        FROM promociones p
                                        WHERE p.fkproducto_id = %s 
                                        AND p.variante_id = %s
                                        AND p.estado_promo = 'activa'
                                        AND p.fecha_inicio <= %s 
                                        AND p.fecha_fin >= %s
                                        AND p.porcentaje_descuento > 0
                                        LIMIT 1
                                    """, [producto.pkid_prod, variante.id_variante, hoy, hoy])
                                    
                                    result_variante = cursor.fetchone()
                                    if result_variante and result_variante[0] is not None:
                                        try:
                                            descuento_porcentaje_variante = float(result_variante[0])
                                            ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                                            precio_final_variante = precio_base_variante - ahorro_variante
                                        except (ValueError, TypeError):
                                            descuento_porcentaje_variante = 0
                                            precio_final_variante = precio_base_variante
                                            ahorro_variante = 0
                                    else:
                                        # Si no hay descuento específico para la variante, usar el del producto base
                                        descuento_porcentaje_variante = descuento_porcentaje_producto
                                        ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                                        precio_final_variante = precio_base_variante - ahorro_variante
                                
                                variante_data = {
                                    'id_variante': variante.id_variante,
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': precio_adicional,
                                    'stock_variante': variante.stock_variante or 0,
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                    # PRECIOS CALCULADOS ESPECÍFICOS PARA LA VARIANTE
                                    'precio_base_calculado': round(precio_base_variante, 2),
                                    'precio_final_calculado': round(precio_final_variante, 2),
                                    'ahorro_calculado': round(ahorro_variante, 2),
                                    'descuento_porcentaje_calculado': descuento_porcentaje_variante,
                                    'tiene_descuento_calculado': descuento_porcentaje_variante > 0,
                                }
                                variantes_list.append(variante_data)
                            except Exception:
                                continue
                    
                    # SOLO MARCAR COMO "TIENE DESCUENTO" SI REALMENTE HAY UN DESCUENTO > 0
                    tiene_descuento_real = descuento_porcentaje_producto > 0
                    
                    producto_data = {
                        'producto': producto,
                        'precio_base': precio_base_producto,
                        'precio_final': round(precio_final_producto, 2),
                        'tiene_descuento': tiene_descuento_real,
                        'descuento_porcentaje': descuento_porcentaje_producto,
                        'ahorro': round(ahorro_producto, 2),
                        'tiene_variantes': tiene_variantes,
                        'variantes': variantes_list,
                        'stock': producto.stock_prod or 0,
                    }
                    
                    productos_baratos_data.append(producto_data)
                    
                except Exception:
                    continue
                    
        except Exception:
            pass

        # PRODUCTOS DESTACADOS - CON CÁLCULO CORRECTO DE DESCUENTOS POR VARIANTE
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
                    
                    # PRECIO BASE DEL PRODUCTO
                    precio_base_producto = float(producto.precio_prod) if producto.precio_prod else 0
                    precio_final_producto = precio_base_producto
                    descuento_porcentaje_producto = 0
                    ahorro_producto = 0
                    
                    # BUSCAR PROMOCIÓN ACTIVA PARA EL PRODUCTO BASE
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT p.porcentaje_descuento 
                            FROM promociones p
                            WHERE p.fkproducto_id = %s 
                            AND p.variante_id IS NULL
                            AND p.estado_promo = 'activa'
                            AND p.fecha_inicio <= %s 
                            AND p.fecha_fin >= %s
                            AND p.porcentaje_descuento > 0
                            LIMIT 1
                        """, [producto.pkid_prod, hoy, hoy])
                        
                        result = cursor.fetchone()
                        if result and result[0] is not None:
                            try:
                                descuento_porcentaje_producto = float(result[0])
                                ahorro_producto = precio_base_producto * (descuento_porcentaje_producto / 100)
                                precio_final_producto = precio_base_producto - ahorro_producto
                            except (ValueError, TypeError):
                                descuento_porcentaje_producto = 0
                                precio_final_producto = precio_base_producto
                                ahorro_producto = 0
                    
                    # VARIANTES DEL PRODUCTO - CON CÁLCULO INDEPENDIENTE PARA CADA UNA
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
                                # CALCULAR PRECIO BASE DE LA VARIANTE
                                precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                                precio_base_variante = precio_base_producto + precio_adicional
                                precio_final_variante = precio_base_variante
                                descuento_porcentaje_variante = 0
                                ahorro_variante = 0
                                
                                # ✅ CORRECCIÓN: BUSCAR DESCUENTO ESPECÍFICO PARA ESTA VARIANTE
                                with connection.cursor() as cursor:
                                    cursor.execute("""
                                        SELECT p.porcentaje_descuento 
                                        FROM promociones p
                                        WHERE p.fkproducto_id = %s 
                                        AND p.variante_id = %s
                                        AND p.estado_promo = 'activa'
                                        AND p.fecha_inicio <= %s 
                                        AND p.fecha_fin >= %s
                                        AND p.porcentaje_descuento > 0
                                        LIMIT 1
                                    """, [producto.pkid_prod, variante.id_variante, hoy, hoy])
                                    
                                    result_variante = cursor.fetchone()
                                    if result_variante and result_variante[0] is not None:
                                        try:
                                            descuento_porcentaje_variante = float(result_variante[0])
                                            ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                                            precio_final_variante = precio_base_variante - ahorro_variante
                                        except (ValueError, TypeError):
                                            descuento_porcentaje_variante = 0
                                            precio_final_variante = precio_base_variante
                                            ahorro_variante = 0
                                    else:
                                        # Si no hay descuento específico para la variante, usar el del producto base
                                        descuento_porcentaje_variante = descuento_porcentaje_producto
                                        ahorro_variante = precio_base_variante * (descuento_porcentaje_variante / 100)
                                        precio_final_variante = precio_base_variante - ahorro_variante
                                
                                variante_data = {
                                    'id_variante': variante.id_variante,
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': precio_adicional,
                                    'stock_variante': variante.stock_variante or 0,
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                    # PRECIOS CALCULADOS ESPECÍFICOS PARA LA VARIANTE
                                    'precio_base_calculado': round(precio_base_variante, 2),
                                    'precio_final_calculado': round(precio_final_variante, 2),
                                    'ahorro_calculado': round(ahorro_variante, 2),
                                    'descuento_porcentaje_calculado': descuento_porcentaje_variante,
                                    'tiene_descuento_calculado': descuento_porcentaje_variante > 0,
                                }
                                variantes_list.append(variante_data)
                            except Exception:
                                continue
                    
                    # SOLO MARCAR COMO "TIENE DESCUENTO" SI REALMENTE HAY UN DESCUENTO > 0
                    tiene_descuento_real = descuento_porcentaje_producto > 0
                    
                    producto_data = {
                        'producto': producto,
                        'precio_base': precio_base_producto,
                        'precio_final': round(precio_final_producto, 2),
                        'total_vendido': item['total_vendido'],
                        'tiene_descuento': tiene_descuento_real,
                        'descuento_porcentaje': descuento_porcentaje_producto,
                        'ahorro': round(ahorro_producto, 2),
                        'tiene_variantes': tiene_variantes,
                        'variantes': variantes_list,
                        'stock': producto.stock_prod or 0,
                    }
                    
                    productos_destacados_data.append(producto_data)
                    
                except Productos.DoesNotExist:
                    continue
                except Exception:
                    continue
        except Exception:
            pass

        # PRODUCTOS OFERTA - MANTENER LA LÓGICA ACTUAL (QUE YA FUNCIONA BIEN)
        productos_oferta_data = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT p.pkid_promo, p.titulo_promo, p.descripcion_promo,
                           p.porcentaje_descuento, p.fkproducto_id, p.variante_id,
                           pr.nom_prod, pr.precio_prod, pr.desc_prod, 
                           pr.stock_prod, pr.img_prod, pr.fknegocioasociado_prod
                    FROM promociones p
                    INNER JOIN productos pr ON p.fkproducto_id = pr.pkid_prod
                    WHERE pr.estado_prod = 'disponible'
                    AND p.estado_promo = 'activa'
                    AND p.fecha_inicio <= %s
                    AND p.fecha_fin >= %s
                    AND p.porcentaje_descuento > 0
                    LIMIT 12
                """, [hoy, hoy])
                
                productos_oferta_rows = cursor.fetchall()
                
                for row in productos_oferta_rows:
                    try:
                        producto_id = row[4]
                        producto = Productos.objects.get(pkid_prod=producto_id)
                        variante_id = row[5]
                        
                        precio_base = float(row[7]) if row[7] else 0
                        precio_final = precio_base
                        descuento_porcentaje = 0
                        ahorro = 0
                        variante_info = None
                        
                        if row[3] is not None:
                            try:
                                descuento_porcentaje = float(row[3])
                                if descuento_porcentaje > 0:
                                    # SI HAY VARIANTE ESPECÍFICA EN LA OFERTA
                                    if variante_id:
                                        try:
                                            variante = VariantesProducto.objects.get(
                                                id_variante=variante_id,
                                                producto=producto,
                                                estado_variante='activa'
                                            )
                                            # CALCULAR PRECIO CON VARIANTE
                                            precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                                            precio_base += precio_adicional
                                            ahorro = precio_base * (descuento_porcentaje / 100)
                                            precio_final = precio_base - ahorro
                                            
                                            variante_info = {
                                                'id': variante.id_variante,
                                                'nombre': variante.nombre_variante,
                                                'precio_adicional': precio_adicional,
                                                'stock': variante.stock_variante or 0,
                                                'imagen': variante.imagen_variante.url if variante.imagen_variante else None
                                            }
                                        except VariantesProducto.DoesNotExist:
                                            # Si no existe la variante, usar producto base
                                            ahorro = precio_base * (descuento_porcentaje / 100)
                                            precio_final = precio_base - ahorro
                                    else:
                                        # OFERTA EN PRODUCTO BASE
                                        ahorro = precio_base * (descuento_porcentaje / 100)
                                        precio_final = precio_base - ahorro
                            except (ValueError, TypeError):
                                pass
                        
                        # VARIANTES PARA EL PRODUCTO (si no hay variante específica en oferta)
                        variantes_list = []
                        tiene_variantes = VariantesProducto.objects.filter(
                            producto=producto, 
                            estado_variante='activa'
                        ).exists()
                        
                        if tiene_variantes and not variante_info:
                            variantes = VariantesProducto.objects.filter(
                                producto=producto,
                                estado_variante='activa'
                            )
                            
                            for variante in variantes:
                                try:
                                    # CALCULAR PRECIOS PARA VARIANTES CON DESCUENTO
                                    precio_adicional = float(variante.precio_adicional) if variante.precio_adicional else 0
                                    precio_base_variante = precio_base + precio_adicional
                                    
                                    if descuento_porcentaje > 0:
                                        ahorro_variante = precio_base_variante * (descuento_porcentaje / 100)
                                        precio_final_variante = precio_base_variante - ahorro_variante
                                    else:
                                        precio_final_variante = precio_base_variante
                                        ahorro_variante = 0
                                    
                                    variante_data = {
                                        'id_variante': variante.id_variante,
                                        'nombre_variante': variante.nombre_variante,
                                        'precio_adicional': precio_adicional,
                                        'stock_variante': variante.stock_variante or 0,
                                        'imagen_variante': variante.imagen_variante,
                                        'estado_variante': variante.estado_variante,
                                        'sku_variante': variante.sku_variante,
                                        'precio_base_calculado': round(precio_base_variante, 2),
                                        'precio_final_calculado': round(precio_final_variante, 2),
                                        'ahorro_calculado': round(ahorro_variante, 2),
                                    }
                                    variantes_list.append(variante_data)
                                except Exception:
                                    continue
                        
                        producto_data = {
                            'producto': producto,
                            'precio_base': precio_base,
                            'precio_final': round(precio_final, 2),
                            'precio_original': precio_base,
                            'tiene_descuento': descuento_porcentaje > 0,
                            'descuento_porcentaje': descuento_porcentaje,
                            'descuento_monto': round(ahorro, 2),
                            'ahorro': round(ahorro, 2),
                            'tiene_variantes': tiene_variantes,
                            'variantes': variantes_list,
                            'variante': variante_info,
                            'stock': row[9] or 0,
                        }
                        
                        productos_oferta_data.append(producto_data)
                        
                    except Exception:
                        continue
        except Exception:
            pass

        # NEGOCIOS DESTACADOS (mantener igual)
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
            
            'ofertas_carrusel': ofertas_carrusel_data,
            'productos_baratos': productos_baratos_data,
            'productos_destacados': productos_destacados_data,
            'productos_oferta': productos_oferta_data,
            'negocios_destacados': negocios_destacados_data,
            'otros_negocios': otros_negocios_data,
            
            'hay_ofertas_activas': len(ofertas_carrusel_data) > 0,
            'hay_productos_baratos': len(productos_baratos_data) > 0,
            'hay_otros_negocios': len(otros_negocios_data) > 0,
        }
        
        return render(request, 'Cliente/Cliente.html', context)
        
    except Exception as e:
        print(f"Error en cliente_dashboard: {str(e)}")
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
    except Exception as e:
        messages.error(request, f'Error al cargar el detalle del negocio: {str(e)}')
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
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'Error al procesar el reporte: {str(e)}'
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

def descontar_stock_pedido(pedido):
    try:
        detalles_pedido = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
        
        for detalle in detalles_pedido:
            producto = detalle.fkproducto_detalle
            cantidad = detalle.cantidad_detalle
            
            try:
                carrito_item = CarritoItem.objects.filter(
                    fkproducto=producto,
                    variante_id__isnull=False
                ).first()
                
                if carrito_item and carrito_item.variante_id:
                    variante = VariantesProducto.objects.get(
                        id_variante=carrito_item.variante_id,
                        producto=producto
                    )
                    if variante.stock_variante >= cantidad:
                        variante.stock_variante -= cantidad
                        variante.save()
                    else:
                        pass
                
                else:
                    if producto.stock_prod >= cantidad:
                        producto.stock_prod -= cantidad
                        producto.save()
                    else:
                        pass
                        
            except VariantesProducto.DoesNotExist:
                if producto.stock_prod >= cantidad:
                    producto.stock_prod -= cantidad
                    producto.save()
                else:
                    pass
            
            except Exception:
                continue
        
        return True
        
    except Exception:
        return False

def restaurar_stock_pedido(pedido):
    try:
        detalles_pedido = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
        
        for detalle in detalles_pedido:
            producto = detalle.fkproducto_detalle
            cantidad = detalle.cantidad_detalle
            
            try:
                carrito_item = CarritoItem.objects.filter(
                    fkproducto=producto,
                    variante_id__isnull=False
                ).first()
                
                if carrito_item and carrito_item.variante_id:
                    variante = VariantesProducto.objects.get(
                        id_variante=carrito_item.variante_id,
                        producto=producto
                    )
                    variante.stock_variante += cantidad
                    variante.save()
                
                else:
                    producto.stock_prod += cantidad
                    producto.save()
                        
            except VariantesProducto.DoesNotExist:
                producto.stock_prod += cantidad
                producto.save()
            
            except Exception:
                continue
        
        return True
        
    except Exception:
        return False

def validar_stock_pedido(pedido):
    try:
        detalles_pedido = DetallesPedido.objects.filter(fkpedido_detalle=pedido)
        
        for detalle in detalles_pedido:
            producto = detalle.fkproducto_detalle
            cantidad = detalle.cantidad_detalle
            
            carrito_item = CarritoItem.objects.filter(
                fkproducto=producto,
                variante_id__isnull=False
            ).first()
            
            if carrito_item and carrito_item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(
                        id_variante=carrito_item.variante_id,
                        producto=producto
                    )
                    if variante.stock_variante < cantidad:
                        return False, f"Stock insuficiente para {producto.nom_prod} - {variante.nombre_variante}"
                except VariantesProducto.DoesNotExist:
                    if producto.stock_prod < cantidad:
                        return False, f"Stock insuficiente para {producto.nom_prod}"
            else:
                if producto.stock_prod < cantidad:
                    return False, f"Stock insuficiente para {producto.nom_prod}"
        
        return True, "Stock válido"
        
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
        
        if variante_id and variante_id != 'base':
            try:
                variante_id_int = int(variante_id)
                variante = VariantesProducto.objects.get(
                    id_variante=variante_id_int, 
                    producto=producto,
                    estado_variante='activa'
                )
                
                if variante.stock_variante < cantidad:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Stock insuficiente. Solo quedan {variante.stock_variante} unidades de esta variante'
                    }, status=400)
                
                if variante.precio_adicional and float(variante.precio_adicional) > 0:
                    precio_base += float(variante.precio_adicional)
                    precio_final = precio_base
                    
                variante_nombre = variante.nombre_variante
                
            except ValueError:
                return JsonResponse({'success': False, 'message': 'ID de variante inválido'}, status=400)
            except VariantesProducto.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Variante no encontrada'}, status=404)
        else:
            if (producto.stock_prod or 0) < cantidad:
                return JsonResponse({
                    'success': False, 
                    'message': f'Stock insuficiente. Solo quedan {producto.stock_prod} unidades'
                }, status=400)
        
        precio_original = precio_base
        
        # ✅ CORRECCIÓN: APLICAR DESCUENTO TANTO A PRODUCTOS BASE COMO A VARIANTES
        with connection.cursor() as cursor:
            if variante_id_int:
                # Buscar promoción específica para la variante
                cursor.execute("""
                    SELECT porcentaje_descuento 
                    FROM promociones 
                    WHERE (fkproducto_id = %s AND variante_id = %s)
                    AND estado_promo = 'activa'
                    AND fecha_inicio <= %s 
                    AND fecha_fin >= %s
                    LIMIT 1
                """, [producto_id, variante_id_int, hoy, hoy])
            else:
                # Buscar promoción para el producto base
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
            nueva_cantidad = item_existente.cantidad + cantidad
            
            stock_disponible = producto.stock_prod
            if variante_id_int:
                stock_disponible = variante.stock_variante
                
            if stock_disponible < nueva_cantidad:
                return JsonResponse({
                    'success': False,
                    'message': f'Stock insuficiente. Solo puedes agregar {stock_disponible - item_existente.cantidad} unidades más'
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
            'precio_unitario': precio_final,
            'precio_original': precio_original,
            'cantidad': cantidad,
            'subtotal': precio_final * cantidad,
            'tiene_descuento': precio_final < precio_original,
            'descuento_porcentaje': ((precio_original - precio_final) / precio_original * 100) if precio_original > 0 else 0,
            'ahorro_total': ahorro_total,
            'item_actualizado': item_existente is not None,
            'es_variante': variante_id_int is not None,
        }
        
        if variante_nombre:
            response_data['variante_nombre'] = variante_nombre
        
        return JsonResponse(response_data)
        
    except Productos.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Producto no encontrado'}, status=404)
    except UsuarioPerfil.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Perfil de usuario no encontrado'}, status=404)
    except Exception as e:
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
            
            if item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(
                        id_variante=item.variante_id,
                        producto=item.fkproducto,
                        estado_variante='activa'
                    )
                    stock_disponible = variante.stock_variante or 0
                except VariantesProducto.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'La variante seleccionada ya no está disponible'
                    })
            else:
                stock_disponible = item.fkproducto.stock_prod or 0
            
            if stock_disponible < nueva_cantidad:
                return JsonResponse({
                    'success': False,
                    'message': f'Stock insuficiente. Solo quedan {stock_disponible} unidades'
                })
            
            item.cantidad = nueva_cantidad
            item.save()
        
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        return JsonResponse({
            'success': True,
            'carrito_count': carrito_count
        })
        
    except Exception as e:
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
        
    except Exception as e:
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
            # ✅ CORRECCIÓN: OBTENER IMAGEN DE LA VARIANTE SI EXISTE
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
            
            # Calcular si tiene descuento
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
        
    except Exception as e:
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
            
            # ✅ CORRECCIÓN: OBTENER IMAGEN DE LA VARIANTE SI EXISTE
            imagen_producto = item.fkproducto.img_prod.url if item.fkproducto.img_prod else None
            
            if item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(id_variante=item.variante_id)
                    if variante.precio_adicional:
                        precio_original += float(variante.precio_adicional)
                        precio_base += float(variante.precio_adicional)
                    stock_disponible = variante.stock_variante or 0
                    
                    # ✅ USAR IMAGEN DE LA VARIANTE SI TIENE UNA
                    if variante.imagen_variante:
                        imagen_producto = variante.imagen_variante.url
                        
                except VariantesProducto.DoesNotExist:
                    pass
            
            precio_actual = float(item.precio_unitario)
            
            # ✅ CORRECCIÓN: VERIFICAR SI HAY DESCUENTO PARA ESTE PRODUCTO/VARIANTE
            tiene_oferta = False
            ahorro_item = 0
            
            # Buscar promociones activas para este producto
            with connection.cursor() as cursor:
                if item.variante_id:
                    # Buscar promoción específica para la variante
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
                    # Buscar promoción para el producto base
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
                            tiene_oferta = precio_actual <= precio_con_descuento  # Considerar que tiene oferta si el precio actual es menor o igual al precio con descuento
                            ahorro_item = (precio_original - precio_actual) * item.cantidad
                    except (ValueError, TypeError):
                        pass
            
            # Si no se encontró oferta en promociones, verificar si el precio actual es menor al original
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
                'ahorro_item': ahorro_item,  # ✅ AGREGAR AHORRO INDIVIDUAL
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
        
    except Exception as e:
        return JsonResponse({'success': False, 'items': [], 'totales': {}})
    
@login_required(login_url='/auth/login/')
@require_POST
@csrf_exempt
def procesar_pedido(request):
    try:
        data = json.loads(request.body)
        metodo_pago = data.get('metodo_pago')
        metodo_pago_texto = data.get('metodo_pago_texto')
        banco = data.get('banco', None)
        datos_billetera = data.get('datos_billetera', {})

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
                'variante_id': item_carrito.variante_id
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
            metodo_pago=metodo_pago,
            metodo_pago_texto=metodo_pago_texto,
            banco=banco,
            fecha_pedido=timezone.now(),
            fecha_actualizacion=timezone.now()
        )

        for item_carrito in items_carrito:
            DetallesPedido.objects.create(
                fkpedido_detalle=pedido,
                fkproducto_detalle=item_carrito.fkproducto,
                cantidad_detalle=item_carrito.cantidad,
                precio_unitario=item_carrito.precio_unitario
            )

        stock_descontado = descontar_stock_pedido(pedido)
        
        if not stock_descontado:
            pass

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

        items_carrito.delete()

        try:
            email_cliente = auth_user.email
            if email_cliente:
                enviar_comprobante_pedido(email_cliente, pedido, items_detallados, negocios_involucrados)
            else:
                pass
        except Exception:
            pass

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
            'stock_descontado': stock_descontado,
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Error interno del servidor al procesar el pedido'}, status=500)  

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
        
    except Exception as e:
        raise e

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
        except Exception as e:
            messages.error(request, f'Error al guardar la reseña: {str(e)}')
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