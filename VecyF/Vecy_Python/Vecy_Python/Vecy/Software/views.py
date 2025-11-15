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
from django.db.models import Avg, Count, Q


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
    
    # PRODUCTOS DISPONIBLES
    todos_productos = Productos.objects.filter(estado_prod='disponible')
    
    print("=== DEBUG PROMOCIONES ===")
    
    # SOLUCIÓN: Usar SQL directo para evitar el problema del JSONField
    try:
        hoy = timezone.now().date()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.pkid_promo, p.titulo_promo, p.descripcion_promo, 
                       p.porcentaje_descuento, p.fecha_inicio, p.fecha_fin,
                       p.estado_promo, p.imagen_promo,
                       p.fknegocio_id, p.fkproducto_id
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
                        'fkproducto_id': row[9]
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
            # Obtener el producto y negocio usando los IDs
            producto_id = promocion_data['fkproducto_id']
            negocio_id = promocion_data['fknegocio_id']
            
            if producto_id:
                producto = Productos.objects.get(pkid_prod=producto_id)
                negocio = Negocios.objects.get(pkid_neg=negocio_id)
                
                print(f"Procesando: {producto.nom_prod} - {promocion_data['titulo_promo']}")
                
                if producto.estado_prod == 'disponible':
                    precio_original = float(producto.precio_prod)
                    descuento_porcentaje = promocion_data['porcentaje_descuento']
                    
                    if descuento_porcentaje and descuento_porcentaje > 0:
                        descuento_monto = (precio_original * descuento_porcentaje) / 100
                        precio_final = precio_original - descuento_monto
                        
                        producto_data = {
                            'producto': producto,
                            'precio_original': precio_original,
                            'precio_final': round(precio_final, 2),
                            'descuento_porcentaje': descuento_porcentaje,
                            'descuento_monto': round(descuento_monto, 2),
                            'tiene_descuento': True,
                            'promocion': promocion_data
                        }
                        productos_oferta.append(producto_data)
                        print(f"✅ Agregado a ofertas: {producto.nom_prod} - ${precio_final}")
                    else:
                        print(f"❌ Descuento no válido: {descuento_porcentaje}")
                else:
                    print(f"❌ Producto no disponible: {producto.nom_prod}")
            else:
                print(f"❌ Promoción sin producto asociado")
                
        except Productos.DoesNotExist:
            print(f"❌ Producto no encontrado: ID {producto_id}")
        except Negocios.DoesNotExist:
            print(f"❌ Negocio no encontrado: ID {negocio_id}")
        except Exception as e:
            print(f"❌ Error procesando promoción: {e}")
    
    print(f"Total productos en oferta: {len(productos_oferta)}")
    print("=== FIN DEBUG ===")
    
    # ==================== CORRECCIÓN: CALIFICACIONES PARA TODOS LOS NEGOCIOS ====================
    
    # NEGOCIOS CON CALIFICACIONES CALCULADAS (igual que en detalle_negocio)
    negocios_con_calificaciones = []
    for negocio in negocios:
        # Calcular promedio de reseñas (igual que en detalle_negocio)
        resenas_negocio = ResenasNegocios.objects.filter(
            fknegocio_resena=negocio,
            estado_resena='activa'
        )
        
        promedio_calificacion = resenas_negocio.aggregate(
            promedio=Avg('estrellas'),
            total_resenas=Count('pkid_resena')
        )
        
        # Agregar los campos calculados al objeto negocio
        negocio.promedio_calificacion = promedio_calificacion['promedio'] or 0
        negocio.total_resenas = promedio_calificacion['total_resenas'] or 0
        negocios_con_calificaciones.append(negocio)
    
    # NEGOCIOS MEJOR CALIFICADOS (usando los cálculos anteriores)
    negocios_mejor_calificados = sorted(
        [n for n in negocios_con_calificaciones if n.promedio_calificacion > 0],
        key=lambda x: x.promedio_calificacion,
        reverse=True
    )[:8]
    
    # PRODUCTOS MÁS VENDIDOS
    productos_mas_vendidos = Productos.objects.filter(
        detallespedido__isnull=False,
        estado_prod='disponible'
    ).annotate(
        total_vendido=Sum('detallespedido__cantidad_detalle')
    ).filter(
        total_vendido__gt=0
    ).order_by('-total_vendido')[:8]
    
    if not productos_mas_vendidos:
        productos_mas_vendidos = todos_productos.order_by('?')[:8]
    
    # PRODUCTOS MÁS BARATOS
    productos_baratos = todos_productos.order_by('precio_prod')[:8]
    
    # NUEVOS PRODUCTOS
    nuevos_productos = todos_productos.order_by('-fecha_creacion')[:12]
    
    # PRODUCTOS DESTACADOS
    productos_destacados = todos_productos.order_by('?')[:8]
    
    # CATEGORÍAS POPULARES
    categorias_populares = categorias[:8]
    
    contexto = {
        'negocios': negocios_con_calificaciones[:12],  # Usar negocios con calificaciones
        'categorias': categorias,
        'tipo_negocios': tipo_negocios,
        'productos_destacados': productos_destacados,
        'nuevos_productos': nuevos_productos,
        'productos_baratos': productos_baratos,
        'negocios_mejor_calificados': negocios_mejor_calificados,
        'productos_oferta': productos_oferta,
        'categorias_populares': categorias_populares,
        'productos_mas_vendidos': productos_mas_vendidos,
        'hay_promociones': len(productos_oferta) > 0,
    }
    
    return render(request, 'Cliente/Principal.html', contexto)


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
    """Dashboard principal del cliente logueado"""
    try:
        # PRIMERO obtener el objeto AuthUser completo
        auth_user = AuthUser.objects.get(username=request.user.username)
        
        # LUEGO buscar el perfil asociado
        perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
        
        # Estadísticas del cliente
        pedidos_count = Pedidos.objects.filter(fkusuario_pedido=perfil_cliente).count()
        pedidos_pendientes = Pedidos.objects.filter(
            fkusuario_pedido=perfil_cliente, 
            estado_pedido='pendiente'
        ).count()
        
        # Carrito count
        carrito_count = 0
        try:
            carrito = Carrito.objects.get(fkusuario_carrito=perfil_cliente)
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
        except Carrito.DoesNotExist:
            pass
        
        # Negocios recientes (para la sección de estadísticas)
        negocios_recientes = Negocios.objects.filter(estado_neg='activo').order_by('-fechacreacion_neg')[:6]
        
        # Negocios mejor calificados - CORREGIDO: usar el campo correcto 'estrellas'
        negocios_mejor_calificados = Negocios.objects.filter(
            estado_neg='activo'
        ).annotate(
            promedio=Avg('resenasnegocios__estrellas'),
            total_resenas=Count('resenasnegocios')
        ).order_by('-promedio')[:6]
        
        # Productos recomendados (con stock)
        productos_recomendados = Productos.objects.filter(
            stock_prod__gt=0,
            estado_prod='activo'
        ).select_related('fknegocioasociado_prod', 'fkcategoria_prod')[:8]
        
        # Productos en oferta (para la sección de ofertas flash)
        productos_oferta = Productos.objects.filter(
            stock_prod__gt=0,
            estado_prod='activo'
        ).select_related('fknegocioasociado_prod')[:6]
        
        # Productos destacados
        productos_destacados = Productos.objects.filter(
            stock_prod__gt=0,
            estado_prod='activo'
        ).select_related('fknegocioasociado_prod')[:4]

        context = {
            'perfil': perfil_cliente,
            'pedidos_count': pedidos_count,
            'pedidos_pendientes': pedidos_pendientes,
            'carrito_count': carrito_count,
            'negocios_recientes': negocios_recientes,
            'negocios_mejor_calificados': negocios_mejor_calificados,
            'productos_recomendados': productos_recomendados,
            'productos_oferta': productos_oferta,
            'productos_destacados': productos_destacados,
        }
        
        return render(request, 'Cliente/Cliente.html', context)
        
    except AuthUser.DoesNotExist:
        messages.error(request, 'Usuario no encontrado en el sistema.')
        return redirect('principal')
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, 'Perfil de usuario no encontrado. Complete su perfil.')
        return redirect('completar_perfil')
    except Exception as e:
        messages.error(request, f'Error al cargar el dashboard: {str(e)}')
        return redirect('principal')
    
# ==================== FUNCIONALIDADES PARA USUARIO LOGEADO ====================
@login_required
@transaction.atomic
def agregar_al_carrito_logeado(request):
    """Agregar producto al carrito desde el detalle del negocio logueado"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            producto_id = data.get('producto_id')
            cantidad = int(data.get('cantidad', 1))
            
            # Obtener usuario y perfil
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
            
            # Obtener producto
            producto = get_object_or_404(
                Productos, 
                pkid_prod=producto_id,
                estado_prod='activo',
                stock_prod__gte=cantidad
            )
            
            # Obtener o crear carrito
            carrito, created = Carrito.objects.get_or_create(
                fkusuario_carrito=perfil_cliente
            )
            
            # Verificar si el producto ya está en el carrito
            item_existente = CarritoItem.objects.filter(
                fkcarrito=carrito,
                fkproducto=producto
            ).first()
            
            if item_existente:
                # Actualizar cantidad si ya existe
                item_existente.cantidad += cantidad
                item_existente.save()
            else:
                # Crear nuevo item
                CarritoItem.objects.create(
                    fkcarrito=carrito,
                    fkproducto=producto,
                    fknegocio=producto.fknegocioasociado_prod,
                    cantidad=cantidad,
                    precio_unitario=producto.precio_prod
                )
            
            # Actualizar contador del carrito
            carrito_count = CarritoItem.objects.filter(fkcarrito=carrito).count()
            
            return JsonResponse({
                'success': True,
                'message': 'Producto agregado al carrito',
                'carrito_count': carrito_count
            })
            
        except Productos.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Producto no disponible'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

@login_required
def seguir_negocio_logeado(request):
    """Seguir o dejar de seguir un negocio (solo para usuarios logueados)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            negocio_id = data.get('negocio_id')
            accion = data.get('accion')  # 'seguir' o 'dejar_seguir'
            
            auth_user = AuthUser.objects.get(username=request.user.username)
            perfil_cliente = UsuarioPerfil.objects.get(fkuser=auth_user)
            negocio = get_object_or_404(Negocios, pkid_neg=negocio_id)
            
            # Aquí puedes implementar la lógica para seguir negocios
            # Por ahora, solo devolvemos una respuesta de éxito
            
            if accion == 'seguir':
                message = 'Negocio agregado a favoritos'
            else:
                message = 'Negocio removido de favoritos'
                
            return JsonResponse({
                'success': True,
                'message': message
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

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