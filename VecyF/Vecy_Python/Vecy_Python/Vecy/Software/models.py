# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class CarritoCompras(models.Model):
    pkid_carrito = models.AutoField(primary_key=True)
    fkusuario_carrito = models.ForeignKey('UsuarioPerfil', models.DO_NOTHING, db_column='fkusuario_carrito')
    fknegocio_carrito = models.ForeignKey('Negocios', models.DO_NOTHING, db_column='fknegocio_carrito')
    fkproducto_carrito = models.ForeignKey('Productos', models.DO_NOTHING, db_column='fkproducto_carrito')
    cantidad_carrito = models.JSONField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_agregado = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'carrito_compras'


class CategoriaProductos(models.Model):
    pkid_cp = models.AutoField(primary_key=True)
    desc_cp = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'categoria_productos'


class DetallesPedido(models.Model):
    pkid_detalle = models.AutoField(primary_key=True)
    fkpedido_detalle = models.ForeignKey('Pedidos', models.DO_NOTHING, db_column='fkpedido_detalle')
    fkproducto_detalle = models.ForeignKey('Productos', models.DO_NOTHING, db_column='fkproducto_detalle')
    cantidad_detalle = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'detalles_pedido'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class Negocios(models.Model):
    pkid_neg = models.AutoField(primary_key=True)
    nit_neg = models.CharField(unique=True, max_length=11)
    nom_neg = models.CharField(max_length=100)
    direcc_neg = models.CharField(max_length=100)
    desc_neg = models.TextField(blank=True, null=True)
    fktiponeg_neg = models.ForeignKey('TipoNegocio', models.DO_NOTHING, db_column='fktiponeg_neg')
    fkpropietario_neg = models.ForeignKey('UsuarioPerfil', models.DO_NOTHING, db_column='fkpropietario_neg')
    estado_neg = models.CharField(max_length=10, blank=True, null=True)
    fechacreacion_neg = models.DateTimeField()
    img_neg = models.ImageField(upload_to='negocios/', null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'negocios'


class Pedidos(models.Model):
    pkid_pedido = models.AutoField(primary_key=True)
    fkusuario_pedido = models.ForeignKey('UsuarioPerfil', models.DO_NOTHING, db_column='fkusuario_pedido')
    fknegocio_pedido = models.ForeignKey(Negocios, models.DO_NOTHING, db_column='fknegocio_pedido')
    estado_pedido = models.CharField(max_length=10, blank=True, null=True)
    total_pedido = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pedido = models.DateTimeField()
    fecha_actualizacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'pedidos'


class Productos(models.Model):
    pkid_prod = models.AutoField(primary_key=True)
    nom_prod = models.CharField(max_length=50)
    precio_prod = models.DecimalField(max_digits=10, decimal_places=2)
    desc_prod = models.TextField(blank=True, null=True)
    estado_prod = models.CharField(max_length=13, blank=True, null=True)
    fkcategoria_prod = models.ForeignKey(CategoriaProductos, models.DO_NOTHING, db_column='fkcategoria_prod')
    stock_prod = models.IntegerField(blank=True, null=True)
    stock_minimo = models.IntegerField(blank=True, null=True)
    fknegocioasociado_prod = models.ForeignKey(Negocios, models.DO_NOTHING, db_column='fknegocioasociado_prod')
    img_prod = models.ImageField(upload_to='productos/', null=True, blank=True)
    fecha_creacion = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'productos'


class Promociones(models.Model):
    pkid_promo = models.AutoField(primary_key=True)
    fknegocio = models.ForeignKey(Negocios, models.DO_NOTHING)
    fkproducto = models.ForeignKey(Productos, models.DO_NOTHING, blank=True, null=True)
    titulo_promo = models.CharField(max_length=100)
    descripcion_promo = models.TextField(blank=True, null=True)
    porcentaje_descuento = models.JSONField(blank=True, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado_promo = models.CharField(max_length=10, blank=True, null=True)
    imagen_promo = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'promociones'


class Reportes(models.Model):
    pkid_reporte = models.AutoField(primary_key=True)
    fknegocio_reportado = models.ForeignKey(Negocios, models.DO_NOTHING, db_column='fknegocio_reportado')
    fkusuario_reporta = models.ForeignKey('UsuarioPerfil', models.DO_NOTHING, db_column='fkusuario_reporta')
    motivo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    fecha_reporte = models.DateTimeField()
    estado_reporte = models.CharField(max_length=9, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'reportes'


class ResenasNegocios(models.Model):
    pkid_resena = models.AutoField(primary_key=True)
    fknegocio_resena = models.ForeignKey(Negocios, models.DO_NOTHING, db_column='fknegocio_resena')
    fkusuario_resena = models.ForeignKey('UsuarioPerfil', models.DO_NOTHING, db_column='fkusuario_resena')
    estrellas = models.IntegerField()
    comentario = models.TextField(blank=True, null=True)
    fecha_resena = models.DateTimeField()
    estado_resena = models.CharField(max_length=9, blank=True, null=True)
    respuesta_vendedor = models.TextField(blank=True, null=True)
    fecha_respuesta = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resenas_negocios'


class ResenasServicios(models.Model):
    pkid_resena = models.AutoField(primary_key=True)
    fkservicio_resena = models.ForeignKey('Servicios', models.DO_NOTHING, db_column='fkservicio_resena')
    fkusuario_resena = models.ForeignKey('UsuarioPerfil', models.DO_NOTHING, db_column='fkusuario_resena')
    estrellas = models.JSONField()
    comentario = models.TextField(blank=True, null=True)
    fecha_resena = models.DateTimeField()
    estado_resena = models.CharField(max_length=9, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resenas_servicios'


class Roles(models.Model):
    pkid_rol = models.AutoField(primary_key=True)
    desc_rol = models.CharField(max_length=25)

    class Meta:
        managed = True
        db_table = 'roles'


class Servicios(models.Model):
    pkid_servicio = models.AutoField(primary_key=True)
    nom_servicio = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fknegocio_servicio = models.ForeignKey(Negocios, models.DO_NOTHING, db_column='fknegocio_servicio')
    fkcategoria_servicio = models.ForeignKey(CategoriaProductos, models.DO_NOTHING, db_column='fkcategoria_servicio', blank=True, null=True)
    estado_servicio = models.CharField(max_length=13, blank=True, null=True)
    fecha_creacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'servicios'


class TipoDocumento(models.Model):
    pkid_doc = models.AutoField(primary_key=True)
    tipo_doc = models.CharField(max_length=2)
    desc_doc = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'tipo_documento'


class TipoNegocio(models.Model):
    pkid_tiponeg = models.AutoField(primary_key=True)
    desc_tiponeg = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'tipo_negocio'


class UsuarioPerfil(models.Model):
    fkuser = models.ForeignKey(AuthUser, models.DO_NOTHING)
    fktipodoc_user = models.ForeignKey(TipoDocumento, models.DO_NOTHING, db_column='fktipodoc_user')
    doc_user = models.CharField(unique=True, max_length=15)
    fechanac_user = models.DateField(blank=True, null=True)
    estado_user = models.CharField(max_length=9, blank=True, null=True)
    img_user = models.CharField(max_length=255, blank=True, null=True)
    fecha_creacion = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'usuario_perfil'


class UsuariosRoles(models.Model):
    fkperfil = models.ForeignKey(UsuarioPerfil, models.DO_NOTHING)
    fkrol = models.ForeignKey(Roles, models.DO_NOTHING)

    class Meta:
        managed = True
        db_table = 'usuarios_roles'
        unique_together = (('fkperfil', 'fkrol'),)
