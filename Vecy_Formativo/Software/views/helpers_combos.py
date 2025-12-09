# helpers_combos.py
from django.db import connection
from django.utils import timezone
from decimal import Decimal
from ..models import Combos, ComboItems, Productos, VariantesProducto, Promociones2x1
from django.db import connection, models

def formatear_precio(valor):
    """Formatea un valor numérico como precio con 2 decimales"""
    try:
        if valor is None:
            return "0.00"
        # Convertir a float y luego formatear
        valor_float = float(valor)
        return "{:,.2f}".format(valor_float).replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "0.00"


def obtener_combos_activos(negocio_id=None, limite=12):
    """
    Obtiene combos activos disponibles
    """
    hoy = timezone.now().date()
    
    try:
        combos_query = Combos.objects.filter(
            estado_combo='activo',
            stock_combo__gt=0
        )
        
        if negocio_id:
            combos_query = combos_query.filter(fknegocio_id=negocio_id)
        
        # Filtrar por fechas si están definidas
        combos_query = combos_query.filter(
            models.Q(fecha_inicio__isnull=True) | models.Q(fecha_inicio__lte=hoy)
        ).filter(
            models.Q(fecha_fin__isnull=True) | models.Q(fecha_fin__gte=hoy)
        )
        
        combos = combos_query.order_by('-descuento_porcentaje', '-fecha_creacion')[:limite]
        
        combos_data = []
        for combo in combos:
            try:
                # Obtener items del combo
                items_combo = ComboItems.objects.filter(fkcombo=combo)
                
                # Verificar stock de todos los productos del combo
                stock_suficiente = True
                productos_combo = []
                
                for item in items_combo:
                    if item.variante:
                        stock_disponible = item.variante.stock_variante or 0
                    else:
                        stock_disponible = item.fkproducto.stock_prod or 0
                    
                    if stock_disponible < item.cantidad:
                        stock_suficiente = False
                        break
                    
                    # Información del producto para mostrar
                    producto_info = {
                        'producto': item.fkproducto,
                        'cantidad': item.cantidad,
                        'variante': item.variante,
                        'nombre_completo': item.fkproducto.nom_prod
                    }
                    
                    if item.variante:
                        producto_info['nombre_completo'] = f"{item.fkproducto.nom_prod} - {item.variante.nombre_variante}"
                    
                    productos_combo.append(producto_info)
                
                if not stock_suficiente:
                    continue
                
                # Calcular precio total regular
                precio_regular_total = 0
                for item in items_combo:
                    precio_producto = float(item.fkproducto.precio_prod) if item.fkproducto.precio_prod else 0
                    
                    if item.variante and item.variante.precio_adicional:
                        precio_producto += float(item.variante.precio_adicional)
                    
                    precio_regular_total += precio_producto * item.cantidad
                
                # Si no hay precio regular calculado, usar el del combo
                if precio_regular_total == 0 and combo.precio_regular:
                    precio_regular_total = float(combo.precio_regular)
                
                # Calcular descuento si no está definido
                if combo.descuento_porcentaje == 0 and precio_regular_total > 0:
                    descuento_porcentaje = ((precio_regular_total - float(combo.precio_combo)) / precio_regular_total) * 100
                    descuento_porcentaje = round(descuento_porcentaje, 2)
                else:
                    descuento_porcentaje = float(combo.descuento_porcentaje)
                
                # Preparar datos del combo
                combo_data = {
                    'combo': combo,
                    'productos': productos_combo,
                    'cantidad_productos': len(productos_combo),
                    'precio_combo': float(combo.precio_combo),
                    'precio_combo_formateado': formatear_precio(combo.precio_combo),
                    'precio_regular': precio_regular_total,
                    'precio_regular_formateado': formatear_precio(precio_regular_total),
                    'descuento_porcentaje': descuento_porcentaje,
                    'ahorro': precio_regular_total - float(combo.precio_combo),
                    'ahorro_formateado': formatear_precio(precio_regular_total - float(combo.precio_combo)),
                    'stock': combo.stock_combo,
                    'negocio': combo.fknegocio,
                    'imagen_url': combo.imagen_combo.url if combo.imagen_combo else None,
                }
                
                combos_data.append(combo_data)
                
            except Exception as e:
                print(f"Error procesando combo {combo.pkid_combo}: {str(e)}")
                continue
        
        return combos_data
        
    except Exception as e:
        print(f"Error obteniendo combos: {str(e)}")
        return []


def obtener_promociones_2x1(negocio_id=None, limite=8):
    """
    Obtiene promociones 2x1 activas
    """
    hoy = timezone.now().date()
    
    try:
        promociones_query = Promociones2x1.objects.filter(
            estado='activa',
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        
        if negocio_id:
            promociones_query = promociones_query.filter(fknegocio_id=negocio_id)
        
        promociones = promociones_query.order_by('-fecha_creacion')[:limite]
        
        promociones_data = []
        for promo in promociones:
            try:
                # Verificar stock
                if promo.variante:
                    stock_disponible = promo.variante.stock_variante or 0
                    precio_base = float(promo.fkproducto.precio_prod) if promo.fkproducto.precio_prod else 0
                    precio_adicional = float(promo.variante.precio_adicional) if promo.variante.precio_adicional else 0
                    precio_total = precio_base + precio_adicional
                    variante_nombre = promo.variante.nombre_variante
                    imagen = promo.variante.imagen_variante if promo.variante.imagen_variante else promo.fkproducto.img_prod
                else:
                    stock_disponible = promo.fkproducto.stock_prod or 0
                    precio_total = float(promo.fkproducto.precio_prod) if promo.fkproducto.precio_prod else 0
                    variante_nombre = None
                    imagen = promo.fkproducto.img_prod
                
                if stock_disponible < 2:  # Necesita al menos 2 unidades para 2x1
                    continue
                
                # Calcular precio por unidad en oferta (paga 1, lleva 2)
                precio_unitario_oferta = precio_total / 2
                
                promo_data = {
                    'promocion': promo,
                    'producto': promo.fkproducto,
                    'variante': promo.variante,
                    'variante_nombre': variante_nombre,
                    'precio_original': precio_total,
                    'precio_original_formateado': formatear_precio(precio_total),
                    'precio_unitario_oferta': precio_unitario_oferta,
                    'precio_unitario_oferta_formateado': formatear_precio(precio_unitario_oferta),
                    'ahorro_porcentaje': 50,  # Siempre 50% en 2x1
                    'ahorro_monto': precio_total - precio_unitario_oferta,
                    'ahorro_monto_formateado': formatear_precio(precio_total - precio_unitario_oferta),
                    'stock': stock_disponible,
                    'negocio': promo.fknegocio,
                    'imagen_url': imagen.url if imagen else None,
                    'es_2x1': True,
                }
                
                promociones_data.append(promo_data)
                
            except Exception as e:
                print(f"Error procesando promoción 2x1 {promo.pkid_promo_2x1}: {str(e)}")
                continue
        
        return promociones_data
        
    except Exception as e:
        print(f"Error obteniendo promociones 2x1: {str(e)}")
        return []


def obtener_ofertas_especiales():
    """
    Obtiene todas las ofertas especiales (combos + 2x1) mezcladas
    """
    combos = obtener_combos_activos(limite=6)
    promociones_2x1 = obtener_promociones_2x1(limite=6)
    
    # Mezclar y ordenar por descuento
    todas_ofertas = combos + promociones_2x1
    todas_ofertas.sort(key=lambda x: x.get('descuento_porcentaje', 0) if 'descuento_porcentaje' in x else x.get('ahorro_porcentaje', 0), reverse=True)
    
    return todas_ofertas[:8]  # Limitar a 8 ofertas


def verificar_stock_combo(combo_id):
    """
    Verifica si hay suficiente stock para un combo
    """
    try:
        combo = Combos.objects.get(pkid_combo=combo_id)
        
        if combo.stock_combo <= 0:
            return False
        
        items = ComboItems.objects.filter(fkcombo=combo)
        
        for item in items:
            if item.variante:
                stock_disponible = item.variante.stock_variante or 0
            else:
                stock_disponible = item.fkproducto.stock_prod or 0
            
            if stock_disponible < item.cantidad:
                return False
        
        return True
        
    except Combos.DoesNotExist:
        return False