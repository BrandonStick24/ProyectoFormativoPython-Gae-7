from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import date
from django.contrib.auth.decorators import login_required
from Software.models import Pedidos, DetallesPedido, ResenasNegocios, AuthUser, UsuarioPerfil, Roles, TipoDocumento, UsuariosRoles, Negocios, TipoNegocio, Productos, CategoriaProductos
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import json
from django.db import transaction


# ==================== VISTAS PÚBLICAS ====================
def inicio(request):
    return render(request, 'Cliente/Index.html')


from django.db.models import Avg
from .models import Negocios, CategoriaProductos, ResenasNegocios

def principal(request):
    negocios = Negocios.objects.all()
    categorias = CategoriaProductos.objects.all()[:20]
    categoria_principal = CategoriaProductos.objects.filter(desc_cp="Celulares y accesorios").first()
    otras_categorias = CategoriaProductos.objects.exclude(desc_cp="Celulares y accesorios")[:11]
    t_negocios = TipoNegocio.objects.all()
    if categoria_principal:
        categorias_interes = [categoria_principal] + list(otras_categorias)
    else:
        categorias_interes = list(otras_categorias)

    # Negocios mejor calificados (promedio de estrellas de 4 a 5)
    negocios_mejor_calificados = (
        Negocios.objects
        .annotate(promedio=Avg('resenasnegocios__estrellas'))
        .filter(promedio__gte=4)
        .order_by('-promedio')[:10]  # Puedes ajustar la cantidad que se muestra
    )

    contexto = {
        'negocios': negocios,
        'categorias': categorias,
        'categorias_interes': categorias_interes,
        'negocios_mejor_calificados': negocios_mejor_calificados,
        't_negocios': t_negocios
    }

    return render(request, 'Cliente/Principal.html', contexto)


def iniciar_sesion(request):
    # LIMPIAR MENSAJES ANTIGUOS AL CARGAR LA PÁGINA DE LOGIN
    storage = messages.get_messages(request)
    for message in storage:
        pass
    
    if request.method == "POST":
        correo = request.POST.get("correo")
        password = request.POST.get("contrasena")

        try:
            user_obj = AuthUser.objects.get(email=correo)
        except AuthUser.DoesNotExist:
            messages.error(request, "Correo incorrecto.", extra_tags='correo')
            return render(request, "Login_Registro/login.html")

        user = authenticate(request, username=user_obj.username, password=password)
        if not user:
            messages.error(request, "Contraseña incorrecta.", extra_tags='contrasena')
            return render(request, "Login_Registro/login.html")

        try:
            perfil = UsuarioPerfil.objects.get(fkuser=user_obj)
        except UsuarioPerfil.DoesNotExist:
            messages.error(request, "Perfil de usuario no encontrado.", extra_tags='general')
            return render(request, "Login_Registro/login.html")

        rol_usuario = UsuariosRoles.objects.filter(fkperfil=perfil).first()
        if not rol_usuario:
            messages.error(request, "Rol de usuario no definido.", extra_tags='general')
            return render(request, "Login_Registro/login.html")

        rol_desc = rol_usuario.fkrol.desc_rol.upper()

        if rol_desc == 'VENDEDOR':
            negocio = Negocios.objects.filter(fkpropietario_neg=perfil, estado_neg='activo').first()
            if not negocio:
                messages.error(request, "No tienes un negocio activo registrado.", extra_tags='negocio')
                return render(request, "Login_Registro/login.html")
            
            login(request, user)
            messages.success(request, "¡Bienvenido, Vendedor!", extra_tags='general')
            return redirect('dash_vendedor')

        elif rol_desc == 'CLIENTE':
            login(request, user)
            messages.success(request, "¡Bienvenido, Cliente!", extra_tags='general')
            return redirect('cliente_dash')
        
        elif rol_desc == 'MODERADOR':
            login(request, user)
            messages.success(request, "¡Bienvenido, Moderador!", extra_tags='general')
            return render(request, 'Moderador/moderador_dash.html')


        else:
            messages.error(request, "Rol no permitido.", extra_tags='general')
            return render(request, "Login_Registro/login.html")

    return render(request, "Login_Registro/login.html")


def registro_user(request):
    roles = Roles.objects.exclude(desc_rol='MODERADOR')
    tipo_documentos = TipoDocumento.objects.all()

    if request.method == 'POST':
        tipo_doc_id = request.POST.get("tipo_doc")
        doc_user = request.POST.get("documento")
        nombre = request.POST.get("nombre")
        correo = request.POST.get("correo")
        fecha_nac = request.POST.get("fechan")
        contrasena = request.POST.get("contrasena")
        confirmar_contrasena = request.POST.get("confirmar_contrasena")
        rol_id = request.POST.get("rol")
        
        errores = False

        try:
            fecha_nac_date = date.fromisoformat(fecha_nac)
            hoy = date.today()
            fecha_limite = hoy.replace(year=hoy.year - 18)

            if fecha_nac_date > fecha_limite:
                messages.error(request, "Debes ser mayor de 18 años para registrarte.", extra_tags='fechan')
                errores = True
        except:
            messages.error(request, "Fecha de nacimiento inválida.", extra_tags='fechan')
            errores = True

        if contrasena != confirmar_contrasena:
            messages.error(request, "Las contraseñas no coinciden.", extra_tags='confirmar_contrasena')
            errores = True

        if len(contrasena) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.", extra_tags='contrasena')
            errores = True

        if UsuarioPerfil.objects.filter(doc_user=doc_user).exists():
            messages.error(request, "El número de documento ya está registrado.", extra_tags='documento')
            errores = True

        if User.objects.filter(email=correo).exists():
            messages.error(request, "El correo electrónico ya está registrado.", extra_tags='correo')
            errores = True

        if errores:
            return render(request, 'Login_Registro/registro.html', {
                'roles': roles,
                'tipo_documentos': tipo_documentos
            })

        auth_user = AuthUser.objects.create(
            username=correo, 
            first_name=nombre,
            last_name='',
            email=correo,
            password=make_password(contrasena),
            is_active=1,
            is_staff=0,
            is_superuser=0,
            date_joined=timezone.now()
        )

        perfil = UsuarioPerfil.objects.create(
            fkuser=auth_user,
            fktipodoc_user_id=tipo_doc_id,
            doc_user=doc_user,
            fechanac_user=fecha_nac,
            estado_user='activo',
            fecha_creacion=timezone.now()
        )

        rol = Roles.objects.get(pk=rol_id)
        UsuariosRoles.objects.create(
            fkperfil=perfil,
            fkrol=rol
        )
        
        if rol.desc_rol.upper() == 'VENDEDOR':
            request.session['perfil_registro_negocio'] = perfil.pk
            return redirect('registro_negocios')

        messages.success(request, "Usuario registrado exitosamente.")
        return redirect('inicio')

    return render(request, 'Login_Registro/registro.html', {
        'roles': roles,
        'tipo_documentos': tipo_documentos
    })


def registro_negocio(request):
    tipo_negocios = TipoNegocio.objects.all()

    perfil_id = request.session.get('perfil_registro_negocio')

    if not perfil_id:
        messages.error(request, "Primero debes registrarte.")
        return redirect('registro')

    propietario = UsuarioPerfil.objects.get(pk=perfil_id)

    if request.method == 'POST':
        nit = request.POST.get('nit')
        nombre = request.POST.get('nom_neg')
        direccion = request.POST.get('direcc_neg')
        descripcion = request.POST.get('desc_neg')
        tipo_neg = request.POST.get('fktiponeg_neg')
        imagen = request.FILES.get('img_neg')

        Negocios.objects.create(
            nit_neg=nit,
            nom_neg=nombre,
            direcc_neg=direccion,
            desc_neg=descripcion,
            fktiponeg_neg_id=tipo_neg,
            fkpropietario_neg=propietario,
            estado_neg='activo',
            fechacreacion_neg=timezone.now(),
            img_neg=imagen
        )

        del request.session['perfil_registro_negocio']  # Limpia la sesión después de usarla

        messages.success(request, "Negocio registrado exitosamente. Ahora inicia sesión.")
        return redirect('login')

    return render(request, 'Login_Registro/registroNegocio.html', {
        'tipo_negocios': tipo_negocios
    })

#=====================================================================================================
# ========================================== VISTAS CLIENTE ==========================================
#=====================================================================================================

@login_required(login_url='login')
def cliente_dash(request):
    negocios = Negocios.objects.all()
    categorias = CategoriaProductos.objects.all()[:20]
    categoria_principal = CategoriaProductos.objects.filter(desc_cp="Celulares y accesorios").first()
    otras_categorias = CategoriaProductos.objects.exclude(desc_cp="Celulares y accesorios")[:11]
    t_negocios = TipoNegocio.objects.all()
    negocios_mejor_calificados = (
        Negocios.objects
        .annotate(promedio=Avg('resenasnegocios__estrellas'))
        .filter(promedio__gte=4)
        .order_by('-promedio')[:10]
    )
    if categoria_principal:
        categorias_interes = [categoria_principal] + list(otras_categorias)
    else:
        categorias_interes = list(otras_categorias)

    try:
        perfil = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
    except UsuarioPerfil.DoesNotExist:
        messages.error(request, "Perfil de usuario no encontrado.")
        return redirect('inicio')
    
    contexto = {
        'nombre' : request.user.first_name,
        'perfil' : perfil,
        'negocios': negocios,
        't_negocios': t_negocios,
        'categorias': categorias,
        'categorias_interes': categorias_interes,
        'negocios_mejor_calificados': negocios_mejor_calificados
    }
    return render(request, 'Cliente/Cliente.html', contexto)

#==================== PEDIDOS =====================
from django.shortcuts import redirect, get_object_or_404
from .models import Carrito, CarritoItem, Productos, UsuarioPerfil
from django.utils import timezone

@login_required(login_url='login')
def agregar_al_carrito(request, producto_id):
    if not request.user.is_authenticated:
        return redirect('login')
    auth_user = get_object_or_404(AuthUser, username=request.user.username)
    usuario_perfil = get_object_or_404(UsuarioPerfil, fkuser=auth_user)
    
    producto = get_object_or_404(Productos, pkid_prod=producto_id)

    # Obtener o crear carrito del usuario
    carrito, created = Carrito.objects.get_or_create(
        fkusuario_carrito=usuario_perfil
    )

    # Verificar si el producto ya está en el carrito
    item, created = CarritoItem.objects.get_or_create(
        fkcarrito=carrito,
        fkproducto=producto,
        fknegocio=producto.fknegocioasociado_prod,
        defaults={'cantidad': 1, 'precio_unitario': producto.precio_prod}
    )

    if not created:
        item.cantidad += 1
        item.save()

    return redirect('ver_carrito')

@login_required(login_url='login')
def agregar_carrito_ajax(request):
    import json
    from django.http import JsonResponse

    if request.method == "POST":
        data = json.loads(request.body)
        prod_id = data.get('prod_id')
        cantidad = data.get('cantidad', 1)

        # Usamos directamente request.user
        try:
            auth_user = AuthUser.objects.get(username=request.user.username)
            usuario_perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
        except UsuarioPerfil.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Perfil no encontrado'})

        producto = get_object_or_404(Productos, pkid_prod=prod_id)

        carrito, created = Carrito.objects.get_or_create(fkusuario_carrito=usuario_perfil)

        item, created = CarritoItem.objects.get_or_create(
            fkcarrito=carrito,
            fkproducto=producto,
            fknegocio=producto.fknegocioasociado_prod,
            defaults={'cantidad': cantidad, 'precio_unitario': producto.precio_prod}
        )

        if not created:
            item.cantidad += cantidad
            item.save()

        return JsonResponse({'success': True})

from django.utils import timezone
from decimal import Decimal
from collections import defaultdict
from django.shortcuts import redirect
from .models import Pedidos, DetallesPedido, PagosNegocios, CarritoItem

from django.shortcuts import redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import CarritoItem, Pedidos, DetallesPedido, PagosNegocios, UsuarioPerfil

from django.db import transaction

@login_required(login_url='login')
def procesar_pago(request):
    auth_user = AuthUser.objects.get(username=request.user.username)
    usuario_perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
    carrito_items = CarritoItem.objects.filter(fkcarrito__fkusuario_carrito=usuario_perfil)

    if not carrito_items.exists():
        return redirect('ver_carrito')

    # Obtener método de pago del formulario (ficticio)
    metodo_seleccionado = request.POST.get('metodo_pago', 'pse').lower()

    negocios_items = {}
    for item in carrito_items:
        negocio = item.fknegocio
        if negocio not in negocios_items:
            negocios_items[negocio] = []
        negocios_items[negocio].append(item)

    try:
        with transaction.atomic():
            for negocio, items in negocios_items.items():
                total_pedido = sum(item.cantidad * item.precio_unitario for item in items)

                # Crear pedido
                pedido = Pedidos.objects.create(
                    fkusuario_pedido=usuario_perfil,
                    fknegocio_pedido=negocio,
                    estado_pedido='pendiente',  # se actualizará según método
                    total_pedido=total_pedido,
                    fecha_pedido=timezone.now(),
                    fecha_actualizacion=timezone.now()
                )

                # Decidir estado según método de pago
                if metodo_seleccionado in ('nequi', 'daviplata', 'tarjeta', 'pse'):
                    estado_pago = 'pagado'
                    pedido.estado_pedido = 'confirmado'
                else:  # efectivo, contra_entrega, etc.
                    estado_pago = 'pendiente'
                    pedido.estado_pedido = 'pendiente'

                # Crear registro de pago
                pago = PagosNegocios.objects.create(
                    fkpedido=pedido,
                    fknegocio=negocio,
                    monto=total_pedido,
                    estado_pago=estado_pago,
                    metodo_pago=metodo_seleccionado
                )

                # Guardar estado del pedido
                pedido.save()

                # Crear detalles del pedido y actualizar stock
                for item in items:
                    producto = item.fkproducto
                    if producto.stock_prod < item.cantidad:
                        raise ValueError(f"No hay suficiente stock de {producto.nom_prod}.")

                    DetallesPedido.objects.create(
                        fkpedido_detalle=pedido,
                        fkproducto_detalle=producto,
                        cantidad_detalle=item.cantidad,
                        precio_unitario=item.precio_unitario
                    )

                    producto.stock_prod -= item.cantidad
                    producto.save()

            # Vaciar carrito
            carrito_items.delete()

    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
        return redirect('ver_carrito')

    # Pasar método de pago a la vista de pago exitoso opcionalmente
    request.session['metodo_pago'] = metodo_seleccionado

    return redirect('pago_exitoso')


@login_required(login_url='login')
def pago_exitoso(request):
    return render(request, 'Cliente/pago_exitoso.html')

def ver_carrito(request):
    auth_user = AuthUser.objects.get(username=request.user.username)
    usuario_perfil = UsuarioPerfil.objects.get(fkuser=auth_user)
    carrito_items = CarritoItem.objects.filter(fkcarrito__fkusuario_carrito=usuario_perfil)

    # Calcula subtotal de cada item
    items_con_subtotal = []
    total_carrito = 0
    for item in carrito_items:
        subtotal = item.cantidad * item.precio_unitario
        total_carrito += subtotal
        items_con_subtotal.append({
            'item': item,
            'subtotal': subtotal
        })

    context = {
        'carrito_items': items_con_subtotal,
        'total_carrito': total_carrito
    }
    return render(request, 'Cliente/ver_carrito.html', context)

@login_required(login_url='login')
def detalle_negocio(request, id):
    # Obtener negocio y propietario
    negocio = get_object_or_404(Negocios, pkid_neg=id)
    propietario = negocio.fkpropietario_neg
    tipo_negocio = negocio.fktiponeg_neg

    # Productos del negocio
    productos = Productos.objects.filter(fknegocioasociado_prod=negocio).select_related('fkcategoria_prod')

    # Perfil del cliente logueado
    try:
        perfil_cliente = UsuarioPerfil.objects.get(fkuser__username=request.user.username)
    except UsuarioPerfil.DoesNotExist:
        perfil_cliente = None

    # Reseñas del negocio directamente desde la BD
    resenas = ResenasNegocios.objects.filter(fknegocio_resena=negocio).select_related('fkusuario_resena__fkuser')

    contexto = {
        'negocio': negocio,
        'propietario': propietario,
        'productos': productos,
        'tipo_negocio': tipo_negocio,
        'perfil_cliente': perfil_cliente,
        'resenas': resenas,   # directamente el queryset
        'nombre': request.user.first_name,
    }

    return render(request, 'Cliente/detalle_neg.html', contexto)

@login_required
def guardar_resena(request):
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
        estrellas=int(estrellas),  # directamente entero
        comentario=comentario,
        fecha_resena=timezone.now(),
        estado_resena='activa'
        )
        resena.save()

        return redirect('detalle_negocio', id=negocio_id)



# ==================== CERRAR SESION ====================
@login_required(login_url='login')
def cerrar_sesion(request):
    logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("principal")