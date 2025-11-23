from ..models import *
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import connection, models
from django.db.models import Avg, Count, Sum
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
import json
from datetime import timedelta
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

def principal(request):
    return render(request, 'cliente/principal.html')

@never_cache
@login_required
def cliente_dashboard(request):
    try:
        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
        hoy = timezone.now().date()

        ofertas_carrusel_data = _obtener_ofertas_carrusel(hoy)
        productos_baratos_data = _obtener_productos_baratos(hoy)
        productos_destacados_data = _obtener_productos_destacados(hoy)
        productos_oferta_data = _obtener_productos_oferta(hoy)
        negocios_destacados_data = _obtener_negocios_destacados(hoy)
        otros_negocios_data = _obtener_otros_negocios(hoy, negocios_destacados_data)

        carrito_count = CarritoItem.objects.filter(fkcarrito__fkusuario_carrito=perfil_cliente).count()
        favoritos_count = Favoritos.objects.filter(fkusuario=perfil_cliente).count()
        pedidos_pendientes_count = Pedidos.objects.filter(
            fkusuario_pedido=perfil_cliente,
            estado_pedido__in=['pendiente', 'confirmado', 'preparando']
        ).count()

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
        
        return render(request, 'cliente/Cliente.html', context)
        
    except Exception as e:
        return render(request, 'cliente/Cliente.html', {
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

def _obtener_ofertas_carrusel(hoy):
    ofertas_data = []
    try:
        fecha_limite = hoy - timezone.timedelta(days=5)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.pkid_promo, p.titulo_promo, p.descripcion_promo, 
                       p.porcentaje_descuento, p.imagen_promo,
                       p.fknegocio_id, p.fkproducto_id
                FROM promociones p
                INNER JOIN productos pr ON p.fkproducto_id = pr.pkid_prod
                WHERE p.estado_promo = 'activa'
                AND p.fecha_inicio >= %s AND p.fecha_fin >= %s
                AND pr.stock_prod > 0 AND pr.estado_prod = 'disponible'
                ORDER BY p.fecha_inicio DESC LIMIT 5
            """, [fecha_limite, hoy])
            
            for row in cursor.fetchall():
                try:
                    producto = Productos.objects.get(pkid_prod=row[6])
                    negocio = Negocios.objects.get(pkid_neg=row[5])
                    
                    descuento_valor = float(row[3]) if row[3] else 0
                    precio_base = float(producto.precio_prod) if producto.precio_prod else 0
                    ahorro_oferta = precio_base * (descuento_valor / 100)
                    
                    ofertas_data.append({
                        'pkid_promo': row[0],
                        'titulo_promo': row[1],
                        'descripcion_promo': row[2],
                        'porcentaje_descuento': descuento_valor,
                        'precio_base': precio_base,
                        'precio_final': precio_base - ahorro_oferta,
                        'ahorro_oferta': round(ahorro_oferta, 2),
                        'imagen_promo': row[4] or (producto.img_prod if producto.img_prod else None),
                        'fkproducto': producto,
                        'fknegocio': negocio,
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return ofertas_data

def _obtener_productos_baratos(hoy):
    productos_data = []
    try:
        productos_baratos = Productos.objects.filter(
            estado_prod='disponible',
            stock_prod__gt=0,
            precio_prod__lte=50000
        ).order_by('precio_prod')[:12]
        
        for producto in productos_baratos:
            precio_base = float(producto.precio_prod) if producto.precio_prod else 0
            precio_final, descuento_porcentaje, ahorro = _calcular_precio_con_descuento(producto.pkid_prod, precio_base, hoy)
            variantes_list = _obtener_variantes_producto(producto)
            
            productos_data.append({
                'producto': producto,
                'precio_base': precio_base,
                'precio_final': round(precio_final, 2),
                'tiene_descuento': descuento_porcentaje > 0,
                'descuento_porcentaje': descuento_porcentaje,
                'ahorro': round(ahorro, 2),
                'tiene_variantes': len(variantes_list) > 0,
                'variantes': variantes_list,
                'stock': producto.stock_prod or 0,
            })
    except Exception:
        pass
    return productos_data

def _obtener_productos_destacados(hoy):
    productos_data = []
    try:
        productos_vendidos = DetallesPedido.objects.filter(
            fkproducto_detalle__estado_prod='disponible',
            fkproducto_detalle__stock_prod__gt=0
        ).values('fkproducto_detalle').annotate(
            total_vendido=Sum('cantidad_detalle')
        ).order_by('-total_vendido')[:12]
        
        for item in productos_vendidos:
            try:
                producto = Productos.objects.get(pkid_prod=item['fkproducto_detalle'])
                precio_base = float(producto.precio_prod) if producto.precio_prod else 0
                precio_final, descuento_porcentaje, ahorro = _calcular_precio_con_descuento(producto.pkid_prod, precio_base, hoy)
                variantes_list = _obtener_variantes_producto(producto)
                
                productos_data.append({
                    'producto': producto,
                    'precio_base': precio_base,
                    'precio_final': round(precio_final, 2),
                    'total_vendido': item['total_vendido'],
                    'tiene_descuento': descuento_porcentaje > 0,
                    'descuento_porcentaje': descuento_porcentaje,
                    'ahorro': round(ahorro, 2),
                    'tiene_variantes': len(variantes_list) > 0,
                    'variantes': variantes_list,
                    'stock': producto.stock_prod or 0,
                })
            except Productos.DoesNotExist:
                continue
    except Exception:
        pass
    return productos_data

def _obtener_productos_oferta(hoy):
    productos_data = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT pr.pkid_prod, pr.nom_prod, pr.precio_prod, 
                       pr.desc_prod, pr.stock_prod, pr.img_prod,
                       p.porcentaje_descuento, pr.fknegocioasociado_prod
                FROM productos pr
                INNER JOIN promociones p ON pr.pkid_prod = p.fkproducto_id
                WHERE pr.estado_prod = 'disponible'
                AND pr.stock_prod > 0
                AND p.estado_promo = 'activa'
                AND p.fecha_inicio <= %s
                AND p.fecha_fin >= %s
                LIMIT 12
            """, [hoy, hoy])
            
            for row in cursor.fetchall():
                try:
                    producto = Productos.objects.get(pkid_prod=row[0])
                    precio_base = float(row[2]) if row[2] else 0
                    precio_final = precio_base
                    descuento_porcentaje = 0
                    ahorro = 0
                    
                    if row[6] is not None:
                        try:
                            descuento_porcentaje = float(row[6])
                            if descuento_porcentaje > 0:
                                precio_final = precio_base * (1 - (descuento_porcentaje / 100))
                                ahorro = precio_base - precio_final
                        except (ValueError, TypeError):
                            pass
                    
                    variantes_list = _obtener_variantes_producto(producto)
                    
                    productos_data.append({
                        'producto': producto,
                        'precio_base': precio_base,
                        'precio_final': round(precio_final, 2),
                        'tiene_descuento': descuento_porcentaje > 0,
                        'descuento_porcentaje': descuento_porcentaje,
                        'ahorro': round(ahorro, 2),
                        'tiene_variantes': len(variantes_list) > 0,
                        'variantes': variantes_list,
                        'stock': row[4] or 0,
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return productos_data

def _obtener_negocios_destacados(hoy):
    negocios_data = []
    try:
        negocios_con_resenas = Negocios.objects.filter(
            estado_neg='activo'
        ).annotate(
            promedio_calificacion=Avg('resenasnegocios__estrellas')
        ).filter(
            promedio_calificacion__gte=4.0
        ).order_by('-promedio_calificacion')[:6]
        
        for negocio in negocios_con_resenas:
            total_resenas = ResenasNegocios.objects.filter(
                fknegocio_resena=negocio
            ).count()
            
            total_productos_disponibles = Productos.objects.filter(
                fknegocioasociado_prod=negocio,
                estado_prod='disponible',
                stock_prod__gt=0
            ).count()
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(DISTINCT pr.pkid_prod)
                    FROM productos pr
                    INNER JOIN promociones p ON pr.pkid_prod = p.fkproducto_id
                    WHERE pr.fknegocioasociado_prod = %s
                    AND pr.estado_prod = 'disponible'
                    AND pr.stock_prod > 0
                    AND p.estado_promo = 'activa'
                    AND p.fecha_inicio <= %s
                    AND p.fecha_fin >= %s
                """, [negocio.pkid_neg, hoy, hoy])
                
                productos_en_oferta = cursor.fetchone()[0] or 0
            
            negocios_data.append({
                'negocio': negocio,
                'promedio_calificacion': float(negocio.promedio_calificacion) if negocio.promedio_calificacion else 0,
                'total_resenas': total_resenas,
                'total_productos': total_productos_disponibles,
                'productos_en_oferta': productos_en_oferta,
            })
    except Exception:
        pass
    return negocios_data

def _obtener_otros_negocios(hoy, negocios_destacados):
    otros_negocios_data = []
    try:
        negocios_destacados_ids = [neg['negocio'].pkid_neg for neg in negocios_destacados]
        
        otros_negocios = Negocios.objects.filter(
            estado_neg='activo'
        ).exclude(
            pkid_neg__in=negocios_destacados_ids
        ).annotate(
            promedio_calificacion=Avg('resenasnegocios__estrellas')
        ).order_by('-promedio_calificacion')[:6]
        
        for negocio in otros_negocios:
            total_resenas = ResenasNegocios.objects.filter(
                fknegocio_resena=negocio
            ).count()
            
            total_productos_disponibles = Productos.objects.filter(
                fknegocioasociado_prod=negocio,
                estado_prod='disponible',
                stock_prod__gt=0
            ).count()
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(DISTINCT pr.pkid_prod)
                    FROM productos pr
                    INNER JOIN promociones p ON pr.pkid_prod = p.fkproducto_id
                    WHERE pr.fknegocioasociado_prod = %s
                    AND pr.estado_prod = 'disponible'
                    AND pr.stock_prod > 0
                    AND p.estado_promo = 'activa'
                    AND p.fecha_inicio <= %s
                    AND p.fecha_fin >= %s
                """, [negocio.pkid_neg, hoy, hoy])
                
                productos_en_oferta = cursor.fetchone()[0] or 0
            
            otros_negocios_data.append({
                'negocio': negocio,
                'promedio_calificacion': float(negocio.promedio_calificacion) if negocio.promedio_calificacion else 0,
                'total_resenas': total_resenas,
                'total_productos': total_productos_disponibles,
                'productos_en_oferta': productos_en_oferta,
            })
    except Exception:
        pass
    return otros_negocios_data

def _calcular_precio_con_descuento(producto_id, precio_base, hoy):
    precio_final = precio_base
    descuento_porcentaje = 0
    ahorro = 0
    
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
            if result and result[0] is not None:
                try:
                    descuento_porcentaje = float(result[0])
                    if descuento_porcentaje > 0:
                        precio_final = precio_base * (1 - (descuento_porcentaje / 100))
                        ahorro = precio_base - precio_final
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass
    
    return precio_final, descuento_porcentaje, ahorro

def _obtener_variantes_producto(producto):
    variantes_list = []
    try:
        variantes = VariantesProducto.objects.filter(
            producto=producto,
            estado_variante='activa'
        )
        
        for variante in variantes:
            variante_data = {
                'id_variante': variante.id_variante,
                'nombre_variante': variante.nombre_variante,
                'precio_adicional': float(variante.precio_adicional) if variante.precio_adicional else 0,
                'stock_variante': variante.stock_variante,
                'imagen_variante': variante.imagen_variante,
                'estado_variante': variante.estado_variante,
                'sku_variante': variante.sku_variante,
            }
            variantes_list.append(variante_data)
    except Exception:
        pass
    
    return variantes_list

@login_required
def detalle_negocio_logeado(request, id):
    try:
        negocio = get_object_or_404(
            Negocios.objects.select_related('fkpropietario_neg', 'fktiponeg_neg'), 
            pkid_neg=id, 
            estado_neg='activo'
        )
        
        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
        
        productos = Productos.objects.filter(
            fknegocioasociado_prod=negocio,
            estado_prod='disponible',
            stock_prod__gt=0
        ).select_related('fkcategoria_prod')
        
        resenas = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            estado_resena='activa'
        ).select_related('fkusuario_resena__user').order_by('-fecha_resena')
        
        promedio_calificacion = resenas.aggregate(
            promedio=Avg('estrellas'),
            total_resenas=Count('pkid_resena')
        )
        
        usuario_ya_reseno = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            fkusuario_resena=perfil_cliente
        ).exists()
        
        carrito_count = 0
        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        except Carrito.DoesNotExist:
            pass
        
        contexto = {
            'negocio': negocio,
            'propietario': negocio.fkpropietario_neg,
            'tipo_negocio': negocio.fktiponeg_neg,
            'productos': productos,
            'perfil_cliente': perfil_cliente,
            'resenas': resenas,
            'promedio_calificacion': promedio_calificacion['promedio'] or 0,
            'total_resenas': promedio_calificacion['total_resenas'] or 0,
            'usuario_ya_reseno': usuario_ya_reseno,
            'carrito_count': carrito_count,
            'es_vista_logeada': True,
            'nombre': f"{request.user.first_name} {request.user.last_name}",
        }
        
        return render(request, 'Cliente/detalle_neg_logeado.html', contexto)
        
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, 'Complete su perfil para acceder a esta funcionalidad.')
        return redirect('completar_perfil')
    except Exception as e:
        messages.error(request, f'Error al cargar el detalle del negocio: {str(e)}')
        return redirect('cliente_dashboard')

@login_required
@require_POST
@csrf_exempt
def agregar_al_carrito(request):
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        cantidad = int(data.get('cantidad', 1))
        variante_id = data.get('variante_id', None)
        
        if not producto_id:
            return JsonResponse({'success': False, 'message': 'ID de producto requerido'}, status=400)
        
        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
        producto = Productos.objects.get(pkid_prod=producto_id)
        
        if producto.estado_prod != 'disponible':
            return JsonResponse({'success': False, 'message': 'Producto no disponible'}, status=400)
        
        precio_final = float(producto.precio_prod)
        variante_nombre = None
        variante_id_int = None
        
        aplicar_descuento = True
        
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
                        'message': f'Stock insuficiente. Solo quedan {variante.stock_variante} unidades'
                    }, status=400)
                
                if variante.precio_adicional and float(variante.precio_adicional) > 0:
                    precio_final += float(variante.precio_adicional)
                    
                variante_nombre = variante.nombre_variante
                aplicar_descuento = True
                
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
                            precio_final = precio_final * (1 - (descuento / 100))
            except Exception:
                pass
        
        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
        
        nuevo_item = CarritoItem.objects.create(
            fkcarrito=carrito,
            fkproducto=producto,
            fknegocio=producto.fknegocioasociado_prod,
            cantidad=cantidad,
            precio_unitario=precio_final,
            variante_seleccionada=variante_nombre,
            variante_id=variante_id_int
        )
        
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        nombre_producto_completo = producto.nom_prod
        if variante_nombre:
            nombre_producto_completo = f"{producto.nom_prod} - {variante_nombre}"
        
        response_data = {
            'success': True,
            'message': 'Producto agregado al carrito exitosamente',
            'carrito_count': carrito_count,
            'producto_nombre': nombre_producto_completo,
            'precio_unitario': precio_final,
            'cantidad': cantidad,
            'subtotal': precio_final * cantidad,
            'tiene_descuento': aplicar_descuento
        }
        
        if variante_nombre:
            response_data['variante_nombre'] = variante_nombre
        
        return JsonResponse(response_data)
        
    except Productos.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Producto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': 'Error interno del servidor'
        }, status=500)

@login_required
def ver_carrito(request):
    try:
        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
        
        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            items_carrito = CarritoItem.objects.filter(fkcarrito=carrito).select_related(
                'fkproducto', 'fknegocio'
            )
        except Carrito.DoesNotExist:
            items_carrito = []
            carrito = None
        
        total_carrito = 0
        items_detallados = []
        
        for item in items_carrito:
            subtotal = float(item.precio_unitario) * item.cantidad
            
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

@login_required
def carrito_data(request):
    try:
        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
        
        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
        items = CarritoItem.objects.filter(fkcarrito=carrito).select_related('fkproducto', 'fknegocio')
        
        carrito_items = []
        subtotal = 0
        ahorro_total = 0
        
        for item in items:
            nombre_completo = item.fkproducto.nom_prod
            if item.variante_seleccionada:
                nombre_completo = f"{item.fkproducto.nom_prod} - {item.variante_seleccionada}"
            
            precio_original = float(item.fkproducto.precio_prod)
            
            if item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(id_variante=item.variante_id)
                    if variante.precio_adicional:
                        precio_original += float(variante.precio_adicional)
                except VariantesProducto.DoesNotExist:
                    pass
            
            precio_actual = float(item.precio_unitario)
            
            tiene_oferta = precio_actual < precio_original
            ahorro_item = (precio_original - precio_actual) * item.cantidad if tiene_oferta else 0
            
            carrito_items.append({
                'id': item.pkid_item,
                'nombre': nombre_completo,
                'negocio': item.fknegocio.nom_neg,
                'cantidad': item.cantidad,
                'precio_unitario': precio_actual,
                'precio_original': precio_original,
                'tiene_oferta': tiene_oferta,
                'imagen': item.fkproducto.img_prod.url if item.fkproducto.img_prod else None,
                'variante': item.variante_seleccionada,
                'es_variante': bool(item.variante_id)
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
            'carrito_count': len(carrito_items)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'success': False, 'items': [], 'totales': {}})

@login_required
@require_POST
def actualizar_cantidad_carrito(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        cambio = data.get('cambio', 0)
        
        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
        
        carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
        item = CarritoItem.objects.get(pkid_item=item_id, fkcarrito=carrito)
        
        nueva_cantidad = item.cantidad + cambio
        
        if nueva_cantidad <= 0:
            item.delete()
        else:
            if item.fkproducto.stock_prod < nueva_cantidad:
                return JsonResponse({
                    'success': False,
                    'message': f'Stock insuficiente. Solo quedan {item.fkproducto.stock_prod} unidades'
                })
            
            item.cantidad = nueva_cantidad
            item.save()
        
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        return JsonResponse({
            'success': True,
            'carrito_count': carrito_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Error interno'})

@login_required
@require_POST
def eliminar_item_carrito(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
        
        carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
        item = CarritoItem.objects.get(pkid_item=item_id, fkcarrito=carrito)
        item.delete()
        
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        return JsonResponse({
            'success': True,
            'carrito_count': carrito_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Error interno'})

@login_required
@require_POST
@csrf_exempt
def procesar_pedido(request):
    try:
        data = json.loads(request.body)
        metodo_pago = data.get('metodo_pago')
        metodo_pago_texto = data.get('metodo_pago_texto')
        banco = data.get('banco', None)
        datos_billetera = data.get('datos_billetera', {})

        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)

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
                'negocio': negocio
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
            producto = item_carrito.fkproducto
            producto.stock_prod = (producto.stock_prod or 0) - item_carrito.cantidad
            producto.save()

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
            enviar_comprobante_pedido(request.user.email, pedido, items_detallados, negocios_involucrados)
        except Exception as e:
            print(f"Error enviando correo: {e}")

        fecha_colombia = timezone.localtime(pedido.fecha_pedido)
        fecha_formateada = fecha_colombia.strftime("%d/%m/%Y %I:%M %p").lower()

        response_data = {
            'success': True,
            'message': 'Pedido procesado exitosamente',
            'numero_pedido': pedido.pkid_pedido,
            'total': total_pedido,
            'metodo_pago': metodo_pago_texto,
            'fecha': fecha_formateada,
            'estado_pedido': pedido.estado_pedido,
            'pagos_creados': len(negocios_involucrados),
            'negocio_principal': negocio_principal.nom_neg
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Error interno del servidor al procesar el pedido'}, status=500)

def enviar_comprobante_pedido(email_cliente, pedido, items_detallados, negocios_involucrados):
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    import os
    
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

@login_required
def guardar_resena(request):
    if request.method == 'POST':
        estrellas = int(request.POST.get('estrellas', 5))
        comentario = request.POST.get('comentario', '')
        negocio_id = request.POST.get('fknegocio_resena')

        usuario = UsuarioPerfil.objects.get(user=request.user)
        negocio = get_object_or_404(Negocios, pkid_neg=negocio_id)

        resena = ResenasNegocios(
            fkusuario_resena=usuario,
            fknegocio_resena=negocio,
            estrellas=int(estrellas),
            comentario=comentario,
            fecha_resena=timezone.now(),
            estado_resena='activa'
        )
        resena.save()

        if request.POST.get('es_vista_logeada'):
            return redirect('detalle_negocio_logeado', id=negocio_id)
        else:
            return redirect('detalle_negocio', id=negocio_id)

@login_required
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
        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
        
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

@login_required
def mis_pedidos_data(request):
    try:
        perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
        
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

@login_required
def cancelar_pedido(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pedido_id = data.get('pedido_id')
            
            perfil_cliente = UsuarioPerfil.objects.get(user=request.user)
            
            pedido = Pedidos.objects.get(
                pkid_pedido=pedido_id,
                fkusuario_pedido=perfil_cliente
            )
            
            tiempo_transcurrido = timezone.now() - pedido.fecha_pedido
            if tiempo_transcurrido > timedelta(hours=1):
                return JsonResponse({
                    'success': False,
                    'message': 'No se puede cancelar el pedido. Ha pasado más de 1 hora desde que se realizó.'
                })
            
            if pedido.estado_pedido not in ['pendiente', 'confirmado']:
                return JsonResponse({
                    'success': False, 
                    'message': f'No se puede cancelar un pedido en estado: {pedido.estado_pedido}'
                })
            
            pedido.estado_pedido = 'cancelado'
            pedido.fecha_actualizacion = timezone.now()
            pedido.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Pedido cancelado exitosamente'
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