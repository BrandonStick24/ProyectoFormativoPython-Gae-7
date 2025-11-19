from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import date
from django.contrib.auth.decorators import login_required
from Software.models import *
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import json
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.views.decorators.csrf import csrf_exempt
#importar require_POST
#importar connection
from django.db import connection
from decimal import Decimal
from django.views.decorators.http import require_POST


# ==================== VISTAS PÚBLICAS ====================
def inicio(request):
    return render(request, 'Cliente/Index.html')

def principal(request):
    from django.utils import timezone
    from django.db.models import Avg, Count, Sum
    from django.db import connection
    from decimal import Decimal
    
    # Obtener datos base
    negocios = Negocios.objects.filter(estado_neg='activo')
    categorias = CategoriaProductos.objects.all()[:20]
    tipo_negocios = TipoNegocio.objects.all()
    
    # PRODUCTOS DISPONIBLES CON SUS VARIANTES
    todos_productos = Productos.objects.filter(estado_prod='disponible')
    
    # Obtener variantes para cada producto
    productos_con_variantes = []
    for producto in todos_productos:
        # Buscar variantes para este producto
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
    
    print("=== DEBUG PROMOCIONES ===")
    
    # SOLUCIÓN: Usar SQL directo para evitar el problema del JSONField
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
            print(f"Promociones encontradas via SQL: {len(promociones_data)}")
            
            # Procesar los resultados manualmente
            promociones_procesadas = []
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
                    print(f"✅ Procesada: {promocion_dict['titulo_promo']} - {promocion_dict['porcentaje_descuento']}%")
                except Exception as e:
                    print(f"❌ Error procesando fila: {e}")
                    continue
                    
    except Exception as e:
        print(f"ERROR en consulta SQL: {e}")
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
                
                # Obtener variante si existe - CORREGIDO AQUÍ
                variante_info = None
                if variante_id:
                    try:
                        variante = VariantesProducto.objects.get(id_variante=variante_id)
                        variante_info = {
                            'id': variante.id_variante,
                            'nombre': variante.nombre_variante,
                            'precio_adicional': float(variante.precio_adicional),
                            'stock': variante.stock_variante,
                            # CORRECCIÓN: Usar .url para el ImageField
                            'imagen': variante.imagen_variante.url if variante.imagen_variante else None
                        }
                    except VariantesProducto.DoesNotExist:
                        print(f"❌ Variante no encontrada: ID {variante_id}")
                
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
            else:
                print(f"❌ Promoción sin producto asociado")
                
        except (Productos.DoesNotExist, Negocios.DoesNotExist, Exception) as e:
            print(f"❌ Error procesando promoción: {e}")
    
    print(f"Total productos en oferta: {len(productos_oferta)}")
    print("=== FIN DEBUG ===")
    
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
    
    return render(request, 'Cliente/Principal.html', contexto)


from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Productos, CategoriaProductos, Negocios, VariantesProducto

def productos_todos(request):
    # Obtener todos los productos disponibles con información relacionada
    productos = Productos.objects.select_related(
        'fknegocioasociado_prod', 
        'fkcategoria_prod'
    ).prefetch_related('variantesproducto_set').filter(
        estado_prod='disponible'
    ).order_by('-fecha_creacion')
    
    # Obtener categorías para los filtros
    categorias = CategoriaProductos.objects.annotate(
        num_productos=Count('productos')
    ).order_by('desc_cp')
    
    # Obtener negocios activos para los filtros
    negocios = Negocios.objects.filter(estado_neg='activo').annotate(
        num_productos=Count('productos')
    ).order_by('nom_neg')
    
    # Filtros - con mejor manejo de valores
    categoria_filtro = request.GET.get('categoria', '')
    negocio_filtro = request.GET.get('negocio', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    ordenar_por = request.GET.get('ordenar_por', 'recientes')
    buscar = request.GET.get('buscar', '')
    
    # DEBUG: Mostrar los valores de los filtros
    print(f"=== FILTROS ACTIVOS ===")
    print(f"Categoria: {categoria_filtro}")
    print(f"Negocio: {negocio_filtro}")
    print(f"Precio min: {precio_min}, Precio max: {precio_max}")
    print(f"Ordenar: {ordenar_por}")
    print(f"Buscar: {buscar}")
    print(f"Productos iniciales: {productos.count()}")
    
    # Aplicar filtros - solo si tienen valor
    if categoria_filtro and categoria_filtro != 'None':
        try:
            productos = productos.filter(fkcategoria_prod__pkid_cp=int(categoria_filtro))
            print(f"✅ Filtrando por categoria ID: {categoria_filtro}")
        except (ValueError, TypeError):
            print(f"❌ Error con categoria ID: {categoria_filtro}")
    
    if negocio_filtro and negocio_filtro != 'None':
        try:
            productos = productos.filter(fknegocioasociado_prod__pkid_neg=int(negocio_filtro))
            print(f"✅ Filtrando por negocio ID: {negocio_filtro}")
        except (ValueError, TypeError):
            print(f"❌ Error con negocio ID: {negocio_filtro}")
    
    if precio_min:
        try:
            productos = productos.filter(precio_prod__gte=float(precio_min))
            print(f"✅ Filtrando por precio mínimo: {precio_min}")
        except (ValueError, TypeError):
            print(f"❌ Error con precio mínimo: {precio_min}")
    
    if precio_max:
        try:
            productos = productos.filter(precio_prod__lte=float(precio_max))
            print(f"✅ Filtrando por precio máximo: {precio_max}")
        except (ValueError, TypeError):
            print(f"❌ Error con precio máximo: {precio_max}")
    
    if buscar and buscar != 'None':
        productos = productos.filter(
            Q(nom_prod__icontains=buscar) |
            Q(desc_prod__icontains=buscar) |
            Q(fknegocioasociado_prod__nom_neg__icontains=buscar)
        )
        print(f"✅ Filtrando por búsqueda: '{buscar}'")
    
    # Ordenar
    if ordenar_por == 'precio_asc':
        productos = productos.order_by('precio_prod')
        print("✅ Ordenando por precio ascendente")
    elif ordenar_por == 'precio_desc':
        productos = productos.order_by('-precio_prod')
        print("✅ Ordenando por precio descendente")
    elif ordenar_por == 'nombre':
        productos = productos.order_by('nom_prod')
        print("✅ Ordenando por nombre")
    elif ordenar_por == 'recientes':
        productos = productos.order_by('-fecha_creacion')
        print("✅ Ordenando por más recientes")
    elif ordenar_por == 'stock':
        productos = productos.order_by('-stock_prod')
        print("✅ Ordenando por stock")
    
    print(f"🎯 Productos después de filtros: {productos.count()}")
    
    # Si no hay productos, mostrar algunos datos de debug
    if productos.count() == 0:
        print("🔍 DEBUG - Mostrando información de categorías y negocios:")
        for cat in categorias:
            print(f"  Categoria {cat.pkid_cp}: {cat.desc_cp} - {cat.num_productos} productos")
        for neg in negocios:
            print(f"  Negocio {neg.pkid_neg}: {neg.nom_neg} - {neg.num_productos} productos")
    
    # Preparar datos para el template
    productos_data = []
    for producto in productos:
        # Obtener variantes si existen
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
    categoria = get_object_or_404(CategoriaProductos, pkid_cp=categoria_id)
    
    productos = Productos.objects.select_related(
        'fknegocioasociado_prod', 
        'fkcategoria_prod'
    ).prefetch_related('variantesproducto_set').filter(
        estado_prod='disponible',
        fkcategoria_prod=categoria
    ).order_by('-fecha_creacion')
    
    # El resto del código es similar a productos_todos...
    categorias = CategoriaProductos.objects.annotate(
        num_productos=Count('productos')
    ).order_by('desc_cp')
    
    negocios = Negocios.objects.filter(estado_neg='activo').annotate(
        num_productos=Count('productos')
    ).order_by('nom_neg')
    
    # Filtros (similar a productos_todos)
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

# ==================== VISTA PÚBLICA DETALLE NEGOCIO ====================
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

# ==================== VISTA PRIVADA DETALLE NEGOCIO LOGEADO ====================
@login_required
def detalle_negocio_logeado(request, id):
    """Vista detallada del negocio para el cliente logueado (con funcionalidades extra)"""
    try:
        # Obtener negocio y relaciones
        negocio = get_object_or_404(
            Negocios.objects.select_related('fkpropietario_neg', 'fktiponeg_neg'), 
            pkid_neg=id, 
            estado_neg='activo'
        )
        
        # DEBUG COMPLETO
        print("=" * 50)
        print("DEBUG DETALLE_NEGOCIO_LOGEADO")
        print(f"Negocio ID: {id}")
        print(f"Negocio encontrado: {negocio.nom_neg}")
        print(f"Estado negocio: {negocio.estado_neg}")
        print("=" * 50)
        
        # Obtener perfil del cliente logueado
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
        
        # PRUEBA 1: Productos sin filtros
        print("PRUEBA 1 - Todos los productos del negocio:")
        productos_todos = Productos.objects.filter(fknegocioasociado_prod=negocio)
        print(f"Total productos (sin filtros): {productos_todos.count()}")
        for p in productos_todos:
            print(f"  - {p.nom_prod} | Estado: {p.estado_prod} | Stock: {p.stock_prod}")
        
        # PRUEBA 2: Productos con filtros actuales
        print("PRUEBA 2 - Productos con filtros actuales:")
        productos = Productos.objects.filter(
            fknegocioasociado_prod=negocio,
            estado_prod='activo',
            stock_prod__gt=0
        ).select_related('fkcategoria_prod')
        print(f"Productos filtrados: {productos.count()}")
        for p in productos:
            print(f"  - {p.nom_prod} | Estado: {p.estado_prod} | Stock: {p.stock_prod}")
        
        # PRUEBA 3: Consulta alternativa
        print("PRUEBA 3 - Consulta alternativa (solo activos):")
        productos_alternativa = Productos.objects.filter(
            fknegocioasociado_prod_id=id,
            estado_prod='activo'
        )
        print(f"Productos alternativa: {productos_alternativa.count()}")
        for p in productos_alternativa:
            print(f"  - {p.nom_prod} | Estado: {p.estado_prod} | Stock: {p.stock_prod}")
        
        # Usar la consulta que funcione
        if productos.exists():
            productos_final = productos
        elif productos_alternativa.exists():
            productos_final = productos_alternativa
        else:
            productos_final = productos_todos
            
        print(f"PRODUCTOS FINALES A MOSTRAR: {productos_final.count()}")
        print("=" * 50)
        
        # Reseñas del negocio con información del usuario
        resenas = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            estado_resena='activa'
        ).select_related('fkusuario_resena__fkuser').order_by('-fecha_resena')
        
        # Promedio de calificaciones
        promedio_calificacion = resenas.aggregate(
            promedio=Avg('estrellas'),
            total_resenas=Count('pkid_resena')
        )
        
        # Verificar si el usuario ya ha reseñado este negocio
        usuario_ya_reseno = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            fkusuario_resena=perfil_cliente
        ).exists()
        
        # Obtener carrito del usuario
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
            'productos': productos_final,  # Usar los productos que sí existen
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
        
    except (AuthUser.DoesNotExist, UsuarioPerfil.DoesNotExist):
        messages.error(request, 'Complete su perfil para acceder a esta funcionalidad.')
        return redirect('completar_perfil')
    except Exception as e:
        messages.error(request, f'Error al cargar el detalle del negocio: {str(e)}')
        print(f"ERROR: {str(e)}")
        return redirect('cliente_dashboard')
    
@login_required
def cliente_dashboard(request):
    """Dashboard principal del cliente logueado - VERSIÓN COMPLETAMENTE CORREGIDA"""
    try:
        # Obtener el perfil del cliente
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
        
        from django.utils import timezone
        from django.db.models import Q, Avg, Count, Sum
        from django.db import connection
        from decimal import Decimal
        hoy = timezone.now().date()

        print("=== DEBUG CLIENTE DASHBOARD INICIO ===")

        # ========== CARRUSEL DE OFERTAS RECIENTES ==========
        ofertas_carrusel_data = []
        try:
            fecha_limite = hoy - timezone.timedelta(days=2)
            
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

        # ========== PRODUCTOS BARATOS (HASTA 50,000 PESOS) ==========
        productos_baratos_data = []
        try:
            # FILTRO CORREGIDO: Solo productos hasta 50,000 pesos
            productos_baratos = Productos.objects.filter(
                estado_prod='disponible',
                stock_prod__gt=0,
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
                    
                    # CORRECCIÓN COMPLETA: OBTENER VARIANTES CON CAMPOS CORRECTOS
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
                                    'id_variante': variante.id_variante,  # ✅ CAMPO CORRECTO
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': float(variante.precio_adicional) if variante.precio_adicional else 0,
                                    'stock_variante': variante.stock_variante,
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                }
                                variantes_list.append(variante_data)
                                print(f"    📦 Variante procesada: {variante.nombre_variante} (ID: {variante.id_variante}) - Precio adicional: ${variante_data['precio_adicional']} - Stock: {variante.stock_variante}")
                                
                            except Exception as e:
                                print(f"    ❌ Error procesando variante: {e}")
                                # DEBUG: Mostrar información de la variante problemática
                                print(f"    🔍 Variante problemática: {variante}")
                                print(f"    🔍 Atributos disponibles: {[attr for attr in dir(variante) if not attr.startswith('_')]}")
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
                        'stock': producto.stock_prod or 0,
                    }
                    
                    productos_baratos_data.append(producto_data)
                    print(f"    ✅ Producto barato agregado: {producto.nom_prod} - Precio final: ${precio_final} - Tiene variantes: {tiene_variantes} - Variantes: {len(variantes_list)}")
                    
                except Exception as e:
                    print(f"    ❌ Error procesando producto barato {producto.nom_prod}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error obteniendo productos baratos: {e}")

        print(f"📦 Productos baratos finales (hasta $50,000): {len(productos_baratos_data)}")

        # ========== PRODUCTOS DESTACADOS ==========
        productos_destacados_data = []
        try:
            productos_vendidos = DetallesPedido.objects.filter(
                fkproducto_detalle__estado_prod='disponible',
                fkproducto_detalle__stock_prod__gt=0
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
                    
                    # CORRECCIÓN COMPLETA: OBTENER VARIANTES CON CAMPOS CORRECTOS
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
                                    'id_variante': variante.id_variante,  # ✅ CAMPO CORRECTO
                                    'nombre_variante': variante.nombre_variante,
                                    'precio_adicional': float(variante.precio_adicional) if variante.precio_adicional else 0,
                                    'stock_variante': variante.stock_variante,
                                    'imagen_variante': variante.imagen_variante,
                                    'estado_variante': variante.estado_variante,
                                    'sku_variante': variante.sku_variante,
                                }
                                variantes_list.append(variante_data)
                                print(f"    📦 Variante encontrada: {variante.nombre_variante} (ID: {variante.id_variante})")
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
                        'stock': producto.stock_prod or 0,
                    }
                    
                    productos_destacados_data.append(producto_data)
                    print(f"    ✅ Producto destacado agregado: {producto.nom_prod} - Variantes: {len(variantes_list)}")
                    
                except Productos.DoesNotExist:
                    print(f"    ❌ Producto no encontrado: {item['fkproducto_detalle']}")
                    continue
                except Exception as e:
                    print(f"    ❌ Error procesando producto destacado: {e}")
                    continue
        except Exception as e:
            print(f"❌ Error obteniendo productos destacados: {e}")

        print(f"📦 Productos destacados finales: {len(productos_destacados_data)}")

        # ========== PRODUCTOS EN OFERTA ==========
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
                    AND pr.stock_prod > 0
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
                        
                        # CORRECCIÓN COMPLETA: OBTENER VARIANTES CON CAMPOS CORRECTOS
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
                                        'id_variante': variante.id_variante,  # ✅ CAMPO CORRECTO
                                        'nombre_variante': variante.nombre_variante,
                                        'precio_adicional': float(variante.precio_adicional) if variante.precio_adicional else 0,
                                        'stock_variante': variante.stock_variante,
                                        'imagen_variante': variante.imagen_variante,
                                        'estado_variante': variante.estado_variante,
                                        'sku_variante': variante.sku_variante,
                                    }
                                    variantes_list.append(variante_data)
                                    print(f"    📦 Variante encontrada: {variante.nombre_variante} (ID: {variante.id_variante})")
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
                            'stock': row[4] or 0,
                        }
                        
                        productos_oferta_data.append(producto_data)
                        print(f"    ✅ Producto oferta agregado: {producto.nom_prod} - Variantes: {len(variantes_list)}")
                        
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
            ).order_by('-promedio_calificacion')[:8]
            
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
                        estado_prod='disponible',
                        stock_prod__gt=0
                    ).count()
                    
                    # Calcular productos en oferta usando SQL
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

        print("=== RESUMEN FINAL ===")
        print(f"🎯 Ofertas carrusel: {len(ofertas_carrusel_data)}")
        print(f"💰 Productos baratos (hasta $50,000): {len(productos_baratos_data)}")
        print(f"⭐ Productos destacados: {len(productos_destacados_data)}")
        print(f"🔥 Productos oferta: {len(productos_oferta_data)}")
        print(f"🏆 Negocios destacados: {len(negocios_destacados_data)}")
        print(f"🛒 Carrito: {carrito_count}")
        print(f"❤️ Favoritos: {favoritos_count}")
        
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
            
            # Secciones principales
            'ofertas_carrusel': ofertas_carrusel_data,
            'productos_baratos': productos_baratos_data,
            'productos_destacados': productos_destacados_data,
            'productos_oferta': productos_oferta_data,
            'negocios_destacados': negocios_destacados_data,
            
            # Flags
            'hay_ofertas_activas': len(ofertas_carrusel_data) > 0,
            'hay_productos_baratos': len(productos_baratos_data) > 0,
        }
        
        return render(request, 'Cliente/Cliente.html', context)
        
    except Exception as e:
        print(f"❌ Error en dashboard cliente: {e}")
        import traceback
        traceback.print_exc()
        
        return render(request, 'Cliente/Cliente.html', {
            'carrito_count': 0,
            'favoritos_count': 0,
            'ofertas_carrusel': [],
            'productos_baratos': [],
            'productos_destacados': [],
            'productos_oferta': [],
            'negocios_destacados': [],
            'hay_ofertas_activas': False,
            'hay_productos_baratos': False,
        })     
@login_required
@require_POST
@csrf_exempt
def agregar_al_carrito(request):
    """Agregar producto al carrito - VERSIÓN CORREGIDA PARA VARIANTES"""
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        cantidad = int(data.get('cantidad', 1))
        variante_id = data.get('variante_id', None)
        
        print(f"🛒 AGREGANDO AL CARRITO - Producto: {producto_id}, Variante: {variante_id}")
        
        if not producto_id:
            return JsonResponse({'success': False, 'message': 'ID de producto requerido'}, status=400)
        
        # Obtener usuario y producto
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
        producto = Productos.objects.get(pkid_prod=producto_id)
        
        if producto.estado_prod != 'disponible':
            return JsonResponse({'success': False, 'message': 'Producto no disponible'}, status=400)
        
        # Precio base del producto
        precio_final = float(producto.precio_prod)
        variante_nombre = None
        variante_id_int = None
        
        # ✅ NUEVA VARIABLE: Controlar si aplica descuento
        aplicar_descuento = True  # Por defecto SÍ aplica descuento
        
        if variante_id and variante_id != 'base':
            print(f"🔍 Buscando variante ID: {variante_id}")
            
            try:
                variante_id_int = int(variante_id)
                variante = VariantesProducto.objects.get(
                    id_variante=variante_id_int, 
                    producto=producto,
                    estado_variante='activa'
                )
                
                print(f"✅ Variante encontrada: {variante.nombre_variante}")
                print(f"💰 Precio adicional: {variante.precio_adicional}, Stock: {variante.stock_variante}")
                
                if variante.stock_variante < cantidad:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Stock insuficiente. Solo quedan {variante.stock_variante} unidades'
                    }, status=400)
                
                # Sumar precio adicional si existe
                if variante.precio_adicional and float(variante.precio_adicional) > 0:
                    precio_final += float(variante.precio_adicional)
                    print(f"💰 Precio con adicional: ${precio_final}")
                    
                variante_nombre = variante.nombre_variante
                
                # ✅ IMPORTANTE: LAS VARIANTES NO TIENEN DESCUENTO
                aplicar_descuento = False
                print("🚫 DESCUENTO DESACTIVADO para variante")
                
            except ValueError:
                return JsonResponse({'success': False, 'message': 'ID de variante inválido'}, status=400)
            except VariantesProducto.DoesNotExist:
                print(f"❌ Variante {variante_id} no encontrada")
                return JsonResponse({'success': False, 'message': 'Variante no encontrada'}, status=404)
        else:
            # Verificar stock del producto base
            if (producto.stock_prod or 0) < cantidad:
                return JsonResponse({
                    'success': False, 
                    'message': f'Stock insuficiente. Solo quedan {producto.stock_prod} unidades'
                }, status=400)
            print("✅ Producto base (sin variante) - DESCUENTO ACTIVADO")
        
        # ✅ APLICAR OFERTAS SOLO SI CORRESPONDE
        if aplicar_descuento:
            from django.utils import timezone
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
                            print(f"✅ OFERTA APLICADA: {descuento}% - De ${precio_original} a ${precio_final}")
            except Exception as e:
                print(f"⚠️ Error verificando ofertas: {e}")
        else:
            print("🚫 OFERTA NO APLICADA - Es una variante")
        
        # Crear o actualizar carrito
        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=perfil_cliente)
        
        # ✅ CREAR NUEVO ITEM EN EL CARRITO CON INFORMACIÓN DE VARIANTE
        nuevo_item = CarritoItem.objects.create(
            fkcarrito=carrito,
            fkproducto=producto,
            fknegocio=producto.fknegocioasociado_prod,
            cantidad=cantidad,
            precio_unitario=precio_final,
            variante_seleccionada=variante_nombre,  # ✅ GUARDAR NOMBRE DE VARIANTE
            variante_id=variante_id_int  # ✅ GUARDAR ID DE VARIANTE
        )
        
        carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        
        # ✅ CONSTRUIR NOMBRE COMPLETO DEL PRODUCTO CON VARIANTE
        nombre_producto_completo = producto.nom_prod
        if variante_nombre:
            nombre_producto_completo = f"{producto.nom_prod} - {variante_nombre}"
        
        response_data = {
            'success': True,
            'message': 'Producto agregado al carrito exitosamente',
            'carrito_count': carrito_count,
            'producto_nombre': nombre_producto_completo,  # ✅ ENVIAR NOMBRE COMPLETO
            'precio_unitario': precio_final,
            'cantidad': cantidad,
            'subtotal': precio_final * cantidad,
            'tiene_descuento': aplicar_descuento  # ✅ INFORMAR SI TIENE DESCUENTO
        }
        
        if variante_nombre:
            response_data['variante_nombre'] = variante_nombre
        
        print(f"✅ PRODUCTO AGREGADO: {nombre_producto_completo} - ${precio_final}")
        print(f"📝 RESUMEN: Variante={variante_nombre}, Descuento={'SÍ' if aplicar_descuento else 'NO'}")
        return JsonResponse(response_data)
        
    except Productos.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Producto no encontrado'}, status=404)
    except Exception as e:
        print(f"❌ Error en agregar_al_carrito: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': 'Error interno del servidor'
        }, status=500)

@login_required
def ver_carrito(request):
    """Vista para ver el carrito del usuario"""
    try:
        # Obtener perfil del usuario
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
        
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
        print(f"❌ Error viendo carrito: {e}")
        return render(request, 'Cliente/carrito.html', {
            'items_carrito': [],
            'total_carrito': 0,
            'carrito_count': 0,
            'carrito_vacio': True
        })
     
from django.http import JsonResponse
import json

@login_required
def carrito_data(request):
    """Obtener datos del carrito para AJAX - VERSIÓN CORREGIDA"""
    try:
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
        
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
            
            # Obtener precio original (sin descuento)
            precio_original = float(item.fkproducto.precio_prod)
            
            # ✅ CORREGIDO: Si hay variante, sumar precio adicional al precio original
            if item.variante_id:
                try:
                    variante = VariantesProducto.objects.get(id_variante=item.variante_id)
                    if variante.precio_adicional:
                        precio_original += float(variante.precio_adicional)
                except VariantesProducto.DoesNotExist:
                    pass
            
            precio_actual = float(item.precio_unitario)
            
            # ✅ CORREGIDO: Solo calcular ahorro si realmente hay descuento
            tiene_oferta = precio_actual < precio_original
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
                'es_variante': bool(item.variante_id)  # ✅ INDICAR SI ES VARIANTE
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
        print(f"❌ Error en carrito_data: {str(e)}")
        return JsonResponse({'success': False, 'items': [], 'totales': {}})

@login_required
@require_POST
def actualizar_cantidad_carrito(request):
    """Actualizar cantidad de un item en el carrito"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        cambio = data.get('cambio', 0)
        
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
        
        carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
        item = CarritoItem.objects.get(pkid_item=item_id, fkcarrito=carrito)
        
        nueva_cantidad = item.cantidad + cambio
        
        if nueva_cantidad <= 0:
            item.delete()
        else:
            # Verificar stock
            if item.fkproducto.stock_prod < nueva_cantidad:
                return JsonResponse({
                    'success': False,
                    'message': f'Stock insuficiente. Solo quedan {item.fkproducto.stock_prod} unidades'
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
        print(f"Error actualizando cantidad: {e}")
        return JsonResponse({'success': False, 'message': 'Error interno'})

@login_required
@require_POST
def eliminar_item_carrito(request):
    """Eliminar item del carrito"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        auth_user = AuthUser.objects.get(username=request.user.username)
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
        
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
        print(f"Error eliminando item: {e}")
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

        auth_user = AuthUser.objects.get(username=request.user.username)
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

        from django.utils import timezone

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

        # ENVIAR COMPROBANTE POR CORREO
        try:
            enviar_comprobante_pedido(auth_user.email, pedido, items_detallados, negocios_involucrados)
        except Exception as e:
            print(f"⚠️ Error enviando correo: {e}")

        # Formatear fecha para la respuesta JSON (hora Colombia)
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
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': 'Error interno del servidor al procesar el pedido'}, status=500)

def enviar_comprobante_pedido(email_cliente, pedido, items_detallados, negocios_involucrados):
    """
    Envía un comprobante de pedido por correo electrónico
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.utils import timezone
    import os
    from datetime import datetime
    
    try:
        # Convertir a hora de Colombia y formatear en español
        fecha_colombia = timezone.localtime(pedido.fecha_pedido)
        
        # Nombres de meses en español
        meses_es = [
            'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]
        
        dias_es = [
            'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'
        ]
        
        fecha_formateada = fecha_colombia.strftime(f"%d de {meses_es[fecha_colombia.month-1]} de %Y")
        hora_formateada = fecha_colombia.strftime("%I:%M %p").lower()
        
        # Si quieres el día de la semana también:
        dia_semana = dias_es[fecha_colombia.weekday()]
        fecha_completa = f"{dia_semana}, {fecha_formateada} a las {hora_formateada}"
        
        # Contexto para el template
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
        
        # Renderizar template HTML
        html_content = render_to_string('emails/comprobante_pedido.html', context)
        text_content = strip_tags(html_content)
        
        # Configurar el email
        subject = f'✅ Comprobante de Pedido VECY - #{context["numero_pedido"]}'
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=os.getenv('DEFAULT_FROM_EMAIL', 'noreply@vecy.com'),
            to=[email_cliente],
            reply_to=['soporte@vecy.com']
        )
        
        email.attach_alternative(html_content, "text/html")
        
        # Enviar email
        email.send()
        
        print(f"📧 Comprobante enviado a: {email_cliente} - Pedido: {context['numero_pedido']}")
        
    except Exception as e:
        print(f"❌ Error enviando comprobante: {e}")
        raise e

@login_required
def guardar_resena(request):
    """Guardar reseña del negocio (solo para usuarios logueados)"""
    if request.method == 'POST':
        estrellas = int(request.POST.get('estrellas', 5))
        comentario = request.POST.get('comentario', '')
        negocio_id = request.POST.get('fknegocio_resena')

        # Obtener instancia de AuthUser
        auth_user = get_object_or_404(AuthUser, username=request.user.username)

        # Obtener perfil del usuario logueado
        usuario = get_object_or_404(UsuarioPerfil, fkuser=auth_user)

        # Obtener negocio
        negocio = get_object_or_404(Negocios, pkid_neg=negocio_id)

        # Crear y guardar la reseña
        resena = ResenasNegocios(
            fkusuario_resena=usuario,
            fknegocio_resena=negocio,
            estrellas=int(estrellas),
            comentario=comentario,
            fecha_resena=timezone.now(),
            estado_resena='activa'
        )
        resena.save()

        # Redirigir a la vista correspondiente según de dónde vino
        if request.POST.get('es_vista_logeada'):
            return redirect('detalle_negocio_logeado', id=negocio_id)
        else:
            return redirect('detalle_negocio', id=negocio_id)
   
# ==================== CERRAR SESION ====================
@login_required(login_url='login')
def cerrar_sesion(request):
    logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("principal")