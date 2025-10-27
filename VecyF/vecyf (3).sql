-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 27-10-2025 a las 02:45:03
-- Versión del servidor: 10.6.23-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `vecyf`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_group`
--

CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL,
  `name` varchar(150) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_group_permissions`
--

CREATE TABLE `auth_group_permissions` (
  `id` bigint(20) NOT NULL,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_permission`
--

CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `auth_permission`
--

INSERT INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
(1, 'Can add log entry', 1, 'add_logentry'),
(2, 'Can change log entry', 1, 'change_logentry'),
(3, 'Can delete log entry', 1, 'delete_logentry'),
(4, 'Can view log entry', 1, 'view_logentry'),
(5, 'Can add permission', 2, 'add_permission'),
(6, 'Can change permission', 2, 'change_permission'),
(7, 'Can delete permission', 2, 'delete_permission'),
(8, 'Can view permission', 2, 'view_permission'),
(9, 'Can add group', 3, 'add_group'),
(10, 'Can change group', 3, 'change_group'),
(11, 'Can delete group', 3, 'delete_group'),
(12, 'Can view group', 3, 'view_group'),
(13, 'Can add user', 4, 'add_user'),
(14, 'Can change user', 4, 'change_user'),
(15, 'Can delete user', 4, 'delete_user'),
(16, 'Can view user', 4, 'view_user'),
(17, 'Can add content type', 5, 'add_contenttype'),
(18, 'Can change content type', 5, 'change_contenttype'),
(19, 'Can delete content type', 5, 'delete_contenttype'),
(20, 'Can view content type', 5, 'view_contenttype'),
(21, 'Can add session', 6, 'add_session'),
(22, 'Can change session', 6, 'change_session'),
(23, 'Can delete session', 6, 'delete_session'),
(24, 'Can view session', 6, 'view_session'),
(25, 'Can add auth group', 7, 'add_authgroup'),
(26, 'Can change auth group', 7, 'change_authgroup'),
(27, 'Can delete auth group', 7, 'delete_authgroup'),
(28, 'Can view auth group', 7, 'view_authgroup'),
(29, 'Can add auth group permissions', 8, 'add_authgrouppermissions'),
(30, 'Can change auth group permissions', 8, 'change_authgrouppermissions'),
(31, 'Can delete auth group permissions', 8, 'delete_authgrouppermissions'),
(32, 'Can view auth group permissions', 8, 'view_authgrouppermissions'),
(33, 'Can add auth permission', 9, 'add_authpermission'),
(34, 'Can change auth permission', 9, 'change_authpermission'),
(35, 'Can delete auth permission', 9, 'delete_authpermission'),
(36, 'Can view auth permission', 9, 'view_authpermission'),
(37, 'Can add auth user', 10, 'add_authuser'),
(38, 'Can change auth user', 10, 'change_authuser'),
(39, 'Can delete auth user', 10, 'delete_authuser'),
(40, 'Can view auth user', 10, 'view_authuser'),
(41, 'Can add auth user groups', 11, 'add_authusergroups'),
(42, 'Can change auth user groups', 11, 'change_authusergroups'),
(43, 'Can delete auth user groups', 11, 'delete_authusergroups'),
(44, 'Can view auth user groups', 11, 'view_authusergroups'),
(45, 'Can add auth user user permissions', 12, 'add_authuseruserpermissions'),
(46, 'Can change auth user user permissions', 12, 'change_authuseruserpermissions'),
(47, 'Can delete auth user user permissions', 12, 'delete_authuseruserpermissions'),
(48, 'Can view auth user user permissions', 12, 'view_authuseruserpermissions'),
(49, 'Can add carrito compras', 13, 'add_carritocompras'),
(50, 'Can change carrito compras', 13, 'change_carritocompras'),
(51, 'Can delete carrito compras', 13, 'delete_carritocompras'),
(52, 'Can view carrito compras', 13, 'view_carritocompras'),
(53, 'Can add categoria productos', 14, 'add_categoriaproductos'),
(54, 'Can change categoria productos', 14, 'change_categoriaproductos'),
(55, 'Can delete categoria productos', 14, 'delete_categoriaproductos'),
(56, 'Can view categoria productos', 14, 'view_categoriaproductos'),
(57, 'Can add detalles pedido', 15, 'add_detallespedido'),
(58, 'Can change detalles pedido', 15, 'change_detallespedido'),
(59, 'Can delete detalles pedido', 15, 'delete_detallespedido'),
(60, 'Can view detalles pedido', 15, 'view_detallespedido'),
(61, 'Can add django admin log', 16, 'add_djangoadminlog'),
(62, 'Can change django admin log', 16, 'change_djangoadminlog'),
(63, 'Can delete django admin log', 16, 'delete_djangoadminlog'),
(64, 'Can view django admin log', 16, 'view_djangoadminlog'),
(65, 'Can add django content type', 17, 'add_djangocontenttype'),
(66, 'Can change django content type', 17, 'change_djangocontenttype'),
(67, 'Can delete django content type', 17, 'delete_djangocontenttype'),
(68, 'Can view django content type', 17, 'view_djangocontenttype'),
(69, 'Can add django migrations', 18, 'add_djangomigrations'),
(70, 'Can change django migrations', 18, 'change_djangomigrations'),
(71, 'Can delete django migrations', 18, 'delete_djangomigrations'),
(72, 'Can view django migrations', 18, 'view_djangomigrations'),
(73, 'Can add django session', 19, 'add_djangosession'),
(74, 'Can change django session', 19, 'change_djangosession'),
(75, 'Can delete django session', 19, 'delete_djangosession'),
(76, 'Can view django session', 19, 'view_djangosession'),
(77, 'Can add negocios', 20, 'add_negocios'),
(78, 'Can change negocios', 20, 'change_negocios'),
(79, 'Can delete negocios', 20, 'delete_negocios'),
(80, 'Can view negocios', 20, 'view_negocios'),
(81, 'Can add pedidos', 21, 'add_pedidos'),
(82, 'Can change pedidos', 21, 'change_pedidos'),
(83, 'Can delete pedidos', 21, 'delete_pedidos'),
(84, 'Can view pedidos', 21, 'view_pedidos'),
(85, 'Can add productos', 22, 'add_productos'),
(86, 'Can change productos', 22, 'change_productos'),
(87, 'Can delete productos', 22, 'delete_productos'),
(88, 'Can view productos', 22, 'view_productos'),
(89, 'Can add promociones', 23, 'add_promociones'),
(90, 'Can change promociones', 23, 'change_promociones'),
(91, 'Can delete promociones', 23, 'delete_promociones'),
(92, 'Can view promociones', 23, 'view_promociones'),
(93, 'Can add reportes', 24, 'add_reportes'),
(94, 'Can change reportes', 24, 'change_reportes'),
(95, 'Can delete reportes', 24, 'delete_reportes'),
(96, 'Can view reportes', 24, 'view_reportes'),
(97, 'Can add resenas negocios', 25, 'add_resenasnegocios'),
(98, 'Can change resenas negocios', 25, 'change_resenasnegocios'),
(99, 'Can delete resenas negocios', 25, 'delete_resenasnegocios'),
(100, 'Can view resenas negocios', 25, 'view_resenasnegocios'),
(101, 'Can add resenas servicios', 26, 'add_resenasservicios'),
(102, 'Can change resenas servicios', 26, 'change_resenasservicios'),
(103, 'Can delete resenas servicios', 26, 'delete_resenasservicios'),
(104, 'Can view resenas servicios', 26, 'view_resenasservicios'),
(105, 'Can add servicios', 27, 'add_servicios'),
(106, 'Can change servicios', 27, 'change_servicios'),
(107, 'Can delete servicios', 27, 'delete_servicios'),
(108, 'Can view servicios', 27, 'view_servicios'),
(109, 'Can add tipo documento', 28, 'add_tipodocumento'),
(110, 'Can change tipo documento', 28, 'change_tipodocumento'),
(111, 'Can delete tipo documento', 28, 'delete_tipodocumento'),
(112, 'Can view tipo documento', 28, 'view_tipodocumento'),
(113, 'Can add tipo negocio', 29, 'add_tiponegocio'),
(114, 'Can change tipo negocio', 29, 'change_tiponegocio'),
(115, 'Can delete tipo negocio', 29, 'delete_tiponegocio'),
(116, 'Can view tipo negocio', 29, 'view_tiponegocio'),
(117, 'Can add roles', 30, 'add_roles'),
(118, 'Can change roles', 30, 'change_roles'),
(119, 'Can delete roles', 30, 'delete_roles'),
(120, 'Can view roles', 30, 'view_roles'),
(121, 'Can add usuario perfil', 31, 'add_usuarioperfil'),
(122, 'Can change usuario perfil', 31, 'change_usuarioperfil'),
(123, 'Can delete usuario perfil', 31, 'delete_usuarioperfil'),
(124, 'Can view usuario perfil', 31, 'view_usuarioperfil'),
(125, 'Can add usuarios roles', 32, 'add_usuariosroles'),
(126, 'Can change usuarios roles', 32, 'change_usuariosroles'),
(127, 'Can delete usuarios roles', 32, 'delete_usuariosroles'),
(128, 'Can view usuarios roles', 32, 'view_usuariosroles');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_user`
--

CREATE TABLE `auth_user` (
  `id` int(11) NOT NULL,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `auth_user`
--

INSERT INTO `auth_user` (`id`, `password`, `last_login`, `is_superuser`, `username`, `first_name`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`) VALUES
(19, 'pbkdf2_sha256$1000000$rii1veuiDBBM0sPmeoKMUN$qC8jpc1bYUiDSBKF3jdPv5yWOXT2Z3vVT4kVZkZ8mas=', '2025-10-26 22:47:10.750131', 0, 'gilberto@gmail.com', 'Gilberto Danilo', '', 'gilberto@gmail.com', 0, 1, '2025-10-26 22:45:36.508300'),
(20, 'pbkdf2_sha256$1000000$DJMwbPS82nr8NFvOBq0laV$Ldtr909Y3Yd3dKbfXngB+xEzCBAFaqInwvNI5vFC9Ec=', NULL, 0, 'javi@correo.com', 'Javier Barreto', '', 'javi@correo.com', 0, 1, '2025-10-26 22:54:45.751712'),
(21, 'pbkdf2_sha256$1000000$hGvBsb6axCCChCB4jEjYjM$C7vOKDwKewyUvjI6Qkqlwn2dIvaWt1NbSv65WrD2vKo=', NULL, 0, 'anag@gmail.com', 'Ana García', '', 'anag@gmail.com', 0, 1, '2025-10-26 23:02:26.771232'),
(22, 'pbkdf2_sha256$1000000$5icdoYWXkBPle46kab24Kt$DdJCSSUgUPSVFkcih/KQy2HsfjD108URp+lRWcNScbo=', NULL, 0, 'roberto@gmail.com', 'Roberto Garcia', '', 'roberto@gmail.com', 0, 1, '2025-10-26 23:11:53.674294'),
(23, 'pbkdf2_sha256$1000000$tX4u2F8JP6s5w8th4eRwJn$07+wjSqkYxsg4xCxX94llpLOdHkkkukgCdcDW5gXxxk=', NULL, 0, 'yenifer@gmail.com', 'Yenifer Quintana', '', 'yenifer@gmail.com', 0, 1, '2025-10-26 23:14:00.551813'),
(24, 'pbkdf2_sha256$1000000$uumMAykCtvBb20PFfqCTaU$Ib2D9FhKTH4rbdttwJZoUahTQ3Oaq/bFtTMjKyyMaPs=', '2025-10-26 23:39:38.790382', 0, 'wilson@gmail.com', 'Wilson Yepes', '', 'wilson@gmail.com', 0, 1, '2025-10-26 23:36:29.202262');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_user_groups`
--

CREATE TABLE `auth_user_groups` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `auth_user_user_permissions`
--

CREATE TABLE `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `carrito_compras`
--

CREATE TABLE `carrito_compras` (
  `pkid_carrito` int(11) NOT NULL,
  `fkusuario_carrito` int(11) NOT NULL,
  `fknegocio_carrito` int(11) NOT NULL,
  `fkproducto_carrito` int(11) NOT NULL,
  `cantidad_carrito` int(11) NOT NULL DEFAULT 1 CHECK (`cantidad_carrito` > 0),
  `precio_unitario` decimal(10,2) NOT NULL,
  `fecha_agregado` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `categoria_productos`
--

CREATE TABLE `categoria_productos` (
  `pkid_cp` int(11) NOT NULL,
  `desc_cp` varchar(100) NOT NULL,
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `detalles_pedido`
--

CREATE TABLE `detalles_pedido` (
  `pkid_detalle` int(11) NOT NULL,
  `fkpedido_detalle` int(11) NOT NULL,
  `fkproducto_detalle` int(11) NOT NULL,
  `cantidad_detalle` int(11) NOT NULL,
  `precio_unitario` decimal(10,2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_admin_log`
--

CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) UNSIGNED NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_content_type`
--

CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `django_content_type`
--

INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(1, 'admin', 'logentry'),
(3, 'auth', 'group'),
(2, 'auth', 'permission'),
(4, 'auth', 'user'),
(5, 'contenttypes', 'contenttype'),
(6, 'sessions', 'session'),
(7, 'Software', 'authgroup'),
(8, 'Software', 'authgrouppermissions'),
(9, 'Software', 'authpermission'),
(10, 'Software', 'authuser'),
(11, 'Software', 'authusergroups'),
(12, 'Software', 'authuseruserpermissions'),
(13, 'Software', 'carritocompras'),
(14, 'Software', 'categoriaproductos'),
(15, 'Software', 'detallespedido'),
(16, 'Software', 'djangoadminlog'),
(17, 'Software', 'djangocontenttype'),
(18, 'Software', 'djangomigrations'),
(19, 'Software', 'djangosession'),
(20, 'Software', 'negocios'),
(21, 'Software', 'pedidos'),
(22, 'Software', 'productos'),
(23, 'Software', 'promociones'),
(24, 'Software', 'reportes'),
(25, 'Software', 'resenasnegocios'),
(26, 'Software', 'resenasservicios'),
(30, 'Software', 'roles'),
(27, 'Software', 'servicios'),
(28, 'Software', 'tipodocumento'),
(29, 'Software', 'tiponegocio'),
(31, 'Software', 'usuarioperfil'),
(32, 'Software', 'usuariosroles');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_migrations`
--

CREATE TABLE `django_migrations` (
  `id` bigint(20) NOT NULL,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `django_migrations`
--

INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
(1, 'contenttypes', '0001_initial', '2025-10-26 15:37:37.674618'),
(2, 'auth', '0001_initial', '2025-10-26 15:37:37.856044'),
(3, 'admin', '0001_initial', '2025-10-26 15:37:37.909035'),
(4, 'admin', '0002_logentry_remove_auto_add', '2025-10-26 15:37:37.914977'),
(5, 'admin', '0003_logentry_add_action_flag_choices', '2025-10-26 15:37:37.921500'),
(6, 'contenttypes', '0002_remove_content_type_name', '2025-10-26 15:37:37.960469'),
(7, 'auth', '0002_alter_permission_name_max_length', '2025-10-26 15:37:37.986852'),
(8, 'auth', '0003_alter_user_email_max_length', '2025-10-26 15:37:37.996618'),
(9, 'auth', '0004_alter_user_username_opts', '2025-10-26 15:37:38.005840'),
(10, 'auth', '0005_alter_user_last_login_null', '2025-10-26 15:37:38.024952'),
(11, 'auth', '0006_require_contenttypes_0002', '2025-10-26 15:37:38.026122'),
(12, 'auth', '0007_alter_validators_add_error_messages', '2025-10-26 15:37:38.031032'),
(13, 'auth', '0008_alter_user_username_max_length', '2025-10-26 15:37:38.051761'),
(14, 'auth', '0009_alter_user_last_name_max_length', '2025-10-26 15:37:38.075422'),
(15, 'auth', '0010_alter_group_name_max_length', '2025-10-26 15:37:38.097208'),
(16, 'auth', '0011_update_proxy_permissions', '2025-10-26 15:37:38.106395'),
(17, 'auth', '0012_alter_user_first_name_max_length', '2025-10-26 15:37:38.120304'),
(18, 'sessions', '0001_initial', '2025-10-26 15:37:38.137816'),
(19, 'Software', '0001_initial', '2025-10-26 15:51:30.004237'),
(20, 'Software', '0002_alter_negocios_options', '2025-10-26 19:32:16.235496');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `django_session`
--

CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `django_session`
--

INSERT INTO `django_session` (`session_key`, `session_data`, `expire_date`) VALUES
('z5uuef16brwold702t11bdjiyb1a45ex', '.eJxVjDEOgzAMAP_iuYqICQQzdu8bkGM7hbYCicBU9e8VEkO73p3uDQPv2zjsxdZhUugBA1x-YWJ52nwYffB8X5ws87ZOyR2JO21xt0XtdT3bv8HIZYQeqKGUNWIQq3PXtEIYGopiCVVYOvK-tUojSqfEiXxE5FqihFRXlhk-XxcLOKU:1vDAKo:d5KXhP_PEPxQwHq3c6TmMMnjFB5i98kEQRfrnccgEgQ', '2025-11-09 23:39:38.795983');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `negocios`
--

CREATE TABLE `negocios` (
  `pkid_neg` int(11) NOT NULL,
  `nit_neg` varchar(11) NOT NULL,
  `nom_neg` varchar(100) NOT NULL,
  `direcc_neg` varchar(100) NOT NULL,
  `desc_neg` longtext DEFAULT NULL,
  `fktiponeg_neg` int(11) NOT NULL,
  `fkpropietario_neg` int(11) NOT NULL,
  `estado_neg` enum('activo','inactivo','suspendido') DEFAULT 'activo',
  `fechacreacion_neg` timestamp NOT NULL DEFAULT current_timestamp(),
  `img_neg` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `negocios`
--

INSERT INTO `negocios` (`pkid_neg`, `nit_neg`, `nom_neg`, `direcc_neg`, `desc_neg`, `fktiponeg_neg`, `fkpropietario_neg`, `estado_neg`, `fechacreacion_neg`, `img_neg`) VALUES
(2, '123456789-0', 'Dulceria Gilberto', 'Calle 5 #34-21', 'Encuentra los mejores dulces de fosca aquí', 4, 18, 'activo', '2025-10-27 03:46:53', 'negocios/fosca.jpg'),
(3, '123456789-1', 'Heladería el Mono', 'Calle 5 #34-25', 'Ven y disfruta de los helados mas deliciosos de fosca, son naturales y baratos', 4, 19, 'activo', '2025-10-27 03:57:03', 'negocios/heladeria.jpg'),
(4, '123456789-2', 'Tienda Doña Ana', 'Calle 5 #34-25(Centro de fosca)', 'Ven y encuentra lo necesites para abastecer tu hogar.', 2, 20, 'activo', '2025-10-27 04:07:22', 'negocios/Goku_7CjpJWt.jpg'),
(5, '123456789-4', 'Biblioteca Municipal', 'Calle 5 #34-21', 'Encuentra los libros que más te gusten aquí. Alquilalos a un buen precio.', 6, 21, 'activo', '2025-10-27 04:13:05', 'negocios/Biblioteca.jpg'),
(6, '123456789-8', 'Panadería El Rincón', 'Calle 5 #34-20', 'Panadería de variedad de panes y pasteles. Sean Bienvenidos', 3, 22, 'activo', '2025-10-27 04:30:48', 'negocios/Panadería.jpg');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `pedidos`
--

CREATE TABLE `pedidos` (
  `pkid_pedido` int(11) NOT NULL,
  `fkusuario_pedido` int(11) NOT NULL,
  `fknegocio_pedido` int(11) NOT NULL,
  `estado_pedido` enum('pendiente','confirmado','preparando','enviado','entregado','cancelado') DEFAULT 'pendiente',
  `total_pedido` decimal(10,2) NOT NULL,
  `fecha_pedido` timestamp NOT NULL DEFAULT current_timestamp(),
  `fecha_actualizacion` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `productos`
--

CREATE TABLE `productos` (
  `pkid_prod` int(11) NOT NULL,
  `nom_prod` varchar(50) NOT NULL,
  `precio_prod` decimal(10,2) NOT NULL,
  `desc_prod` longtext DEFAULT NULL,
  `estado_prod` enum('disponible','no_disponible','agotado') DEFAULT 'disponible',
  `fkcategoria_prod` int(11) NOT NULL,
  `stock_prod` int(11) DEFAULT 0,
  `stock_minimo` int(11) DEFAULT 5,
  `fknegocioasociado_prod` int(11) NOT NULL,
  `img_prod` varchar(255) DEFAULT NULL,
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `promociones`
--

CREATE TABLE `promociones` (
  `pkid_promo` int(11) NOT NULL,
  `fknegocio_id` int(11) NOT NULL,
  `fkproducto_id` int(11) DEFAULT NULL,
  `titulo_promo` varchar(100) NOT NULL,
  `descripcion_promo` longtext DEFAULT NULL,
  `porcentaje_descuento` decimal(5,2) DEFAULT NULL CHECK (`porcentaje_descuento` between 0 and 100),
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date NOT NULL,
  `estado_promo` enum('activa','inactiva','finalizada') DEFAULT 'activa',
  `imagen_promo` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `reportes`
--

CREATE TABLE `reportes` (
  `pkid_reporte` int(11) NOT NULL,
  `fknegocio_reportado` int(11) NOT NULL,
  `fkusuario_reporta` int(11) NOT NULL,
  `motivo` varchar(255) NOT NULL,
  `descripcion` longtext DEFAULT NULL,
  `fecha_reporte` timestamp NOT NULL DEFAULT current_timestamp(),
  `estado_reporte` enum('pendiente','revisado','resuelto') DEFAULT 'pendiente'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `resenas_negocios`
--

CREATE TABLE `resenas_negocios` (
  `pkid_resena` int(11) NOT NULL,
  `fknegocio_resena` int(11) NOT NULL,
  `fkusuario_resena` int(11) NOT NULL,
  `estrellas` tinyint(4) NOT NULL CHECK (`estrellas` between 1 and 5),
  `comentario` longtext DEFAULT NULL,
  `fecha_resena` timestamp NOT NULL DEFAULT current_timestamp(),
  `estado_resena` enum('activa','inactiva','eliminada') DEFAULT 'activa'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `resenas_servicios`
--

CREATE TABLE `resenas_servicios` (
  `pkid_resena` int(11) NOT NULL,
  `fkservicio_resena` int(11) NOT NULL,
  `fkusuario_resena` int(11) NOT NULL,
  `estrellas` tinyint(4) NOT NULL CHECK (`estrellas` between 1 and 5),
  `comentario` longtext DEFAULT NULL,
  `fecha_resena` timestamp NOT NULL DEFAULT current_timestamp(),
  `estado_resena` enum('activa','inactiva','eliminada') DEFAULT 'activa'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `roles`
--

CREATE TABLE `roles` (
  `pkid_rol` int(11) NOT NULL,
  `desc_rol` varchar(25) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `roles`
--

INSERT INTO `roles` (`pkid_rol`, `desc_rol`) VALUES
(1, 'CLIENTE'),
(2, 'MODERADOR'),
(3, 'VENDEDOR');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `servicios`
--

CREATE TABLE `servicios` (
  `pkid_servicio` int(11) NOT NULL,
  `nom_servicio` varchar(100) NOT NULL,
  `descripcion` longtext DEFAULT NULL,
  `precio` decimal(10,2) DEFAULT NULL,
  `fknegocio_servicio` int(11) NOT NULL,
  `fkcategoria_servicio` int(11) DEFAULT NULL,
  `estado_servicio` enum('disponible','no_disponible','agotado') DEFAULT 'disponible',
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tipo_documento`
--

CREATE TABLE `tipo_documento` (
  `pkid_doc` int(11) NOT NULL,
  `tipo_doc` varchar(2) NOT NULL,
  `desc_doc` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `tipo_documento`
--

INSERT INTO `tipo_documento` (`pkid_doc`, `tipo_doc`, `desc_doc`) VALUES
(1, 'CC', 'Cédula de Ciudadanía'),
(2, 'TI', 'Tarjeta de Identidad');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tipo_negocio`
--

CREATE TABLE `tipo_negocio` (
  `pkid_tiponeg` int(11) NOT NULL,
  `desc_tiponeg` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `tipo_negocio`
--

INSERT INTO `tipo_negocio` (`pkid_tiponeg`, `desc_tiponeg`) VALUES
(1, 'Restaurante'),
(2, 'Tienda'),
(3, 'Panadería'),
(4, 'Heladería'),
(6, 'Biblioteca'),
(7, 'Zapatería'),
(8, 'Cafetería'),
(9, 'Supermercado'),
(10, 'Minimarket'),
(11, 'Papelería'),
(12, 'Ferretería'),
(13, 'Droguería / Farmacia'),
(14, 'Salón de Belleza'),
(15, 'Barbería'),
(16, 'Miscelánea'),
(17, 'Boutique / Ropa'),
(18, 'Verdulería / Frutería'),
(19, 'Carnicería'),
(20, 'Pizzería'),
(21, 'Licorería'),
(22, 'Veterinaria'),
(23, 'Taller de Motos'),
(24, 'Taller de Bicicletas'),
(25, 'Tecnología y Accesorios'),
(26, 'Joyería'),
(27, 'Floristería'),
(28, 'Lavandería'),
(29, 'Artesanías'),
(30, 'Pastelería'),
(31, 'Comida Rápida'),
(32, 'Gimnasio'),
(33, 'Fotografía'),
(34, 'Estanco'),
(35, 'Servicios de Internet / Cabinas'),
(36, 'Panadería y Café'),
(37, 'Repostería'),
(38, 'Juguetería');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuarios_roles`
--

CREATE TABLE `usuarios_roles` (
  `id` int(11) NOT NULL,
  `fkperfil_id` int(11) NOT NULL,
  `fkrol_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `usuarios_roles`
--

INSERT INTO `usuarios_roles` (`id`, `fkperfil_id`, `fkrol_id`) VALUES
(18, 18, 3),
(19, 19, 3),
(20, 20, 3),
(21, 21, 3),
(22, 22, 3),
(23, 23, 1);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuario_perfil`
--

CREATE TABLE `usuario_perfil` (
  `id` int(11) NOT NULL,
  `fkuser_id` int(11) NOT NULL,
  `fktipodoc_user` int(11) NOT NULL,
  `doc_user` varchar(15) NOT NULL,
  `fechanac_user` date DEFAULT NULL,
  `estado_user` enum('activo','bloqueado','inactivo') DEFAULT 'activo',
  `img_user` varchar(255) DEFAULT NULL,
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `usuario_perfil`
--

INSERT INTO `usuario_perfil` (`id`, `fkuser_id`, `fktipodoc_user`, `doc_user`, `fechanac_user`, `estado_user`, `img_user`, `fecha_creacion`) VALUES
(18, 19, 1, '1111111111', '2000-10-12', 'activo', NULL, '2025-10-27 03:45:36'),
(19, 20, 1, '1111111112', '2000-03-12', 'activo', NULL, '2025-10-27 03:54:45'),
(20, 21, 1, '1111111113', '1995-03-12', 'activo', NULL, '2025-10-27 04:02:26'),
(21, 22, 1, '1111111115', '1969-05-12', 'activo', NULL, '2025-10-27 04:11:53'),
(22, 23, 1, '1111111116', '1970-12-11', 'activo', NULL, '2025-10-27 04:14:00'),
(23, 24, 1, '1105305033', '2007-02-05', 'activo', NULL, '2025-10-27 04:36:29');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `auth_group`
--
ALTER TABLE `auth_group`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indices de la tabla `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  ADD KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`);

--
-- Indices de la tabla `auth_permission`
--
ALTER TABLE `auth_permission`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`);

--
-- Indices de la tabla `auth_user`
--
ALTER TABLE `auth_user`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indices de la tabla `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  ADD KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`);

--
-- Indices de la tabla `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  ADD KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`);

--
-- Indices de la tabla `carrito_compras`
--
ALTER TABLE `carrito_compras`
  ADD PRIMARY KEY (`pkid_carrito`),
  ADD KEY `fkusuario_carrito` (`fkusuario_carrito`),
  ADD KEY `fknegocio_carrito` (`fknegocio_carrito`),
  ADD KEY `fkproducto_carrito` (`fkproducto_carrito`);

--
-- Indices de la tabla `categoria_productos`
--
ALTER TABLE `categoria_productos`
  ADD PRIMARY KEY (`pkid_cp`);

--
-- Indices de la tabla `detalles_pedido`
--
ALTER TABLE `detalles_pedido`
  ADD PRIMARY KEY (`pkid_detalle`),
  ADD KEY `fkpedido_detalle` (`fkpedido_detalle`),
  ADD KEY `fkproducto_detalle` (`fkproducto_detalle`);

--
-- Indices de la tabla `django_admin_log`
--
ALTER TABLE `django_admin_log`
  ADD PRIMARY KEY (`id`),
  ADD KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  ADD KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`);

--
-- Indices de la tabla `django_content_type`
--
ALTER TABLE `django_content_type`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`);

--
-- Indices de la tabla `django_migrations`
--
ALTER TABLE `django_migrations`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `django_session`
--
ALTER TABLE `django_session`
  ADD PRIMARY KEY (`session_key`),
  ADD KEY `django_session_expire_date_a5c62663` (`expire_date`);

--
-- Indices de la tabla `negocios`
--
ALTER TABLE `negocios`
  ADD PRIMARY KEY (`pkid_neg`),
  ADD UNIQUE KEY `nit_neg` (`nit_neg`),
  ADD KEY `fkpropietario_neg` (`fkpropietario_neg`),
  ADD KEY `fktiponeg_neg` (`fktiponeg_neg`);

--
-- Indices de la tabla `pedidos`
--
ALTER TABLE `pedidos`
  ADD PRIMARY KEY (`pkid_pedido`),
  ADD KEY `fkusuario_pedido` (`fkusuario_pedido`),
  ADD KEY `fknegocio_pedido` (`fknegocio_pedido`);

--
-- Indices de la tabla `productos`
--
ALTER TABLE `productos`
  ADD PRIMARY KEY (`pkid_prod`),
  ADD KEY `fkcategoria_prod` (`fkcategoria_prod`),
  ADD KEY `fknegocioasociado_prod` (`fknegocioasociado_prod`);

--
-- Indices de la tabla `promociones`
--
ALTER TABLE `promociones`
  ADD PRIMARY KEY (`pkid_promo`),
  ADD KEY `fknegocio_id` (`fknegocio_id`),
  ADD KEY `fkproducto_id` (`fkproducto_id`);

--
-- Indices de la tabla `reportes`
--
ALTER TABLE `reportes`
  ADD PRIMARY KEY (`pkid_reporte`),
  ADD KEY `fknegocio_reportado` (`fknegocio_reportado`),
  ADD KEY `fkusuario_reporta` (`fkusuario_reporta`);

--
-- Indices de la tabla `resenas_negocios`
--
ALTER TABLE `resenas_negocios`
  ADD PRIMARY KEY (`pkid_resena`),
  ADD KEY `fknegocio_resena` (`fknegocio_resena`),
  ADD KEY `fkusuario_resena` (`fkusuario_resena`);

--
-- Indices de la tabla `resenas_servicios`
--
ALTER TABLE `resenas_servicios`
  ADD PRIMARY KEY (`pkid_resena`),
  ADD KEY `fkservicio_resena` (`fkservicio_resena`),
  ADD KEY `fkusuario_resena` (`fkusuario_resena`);

--
-- Indices de la tabla `roles`
--
ALTER TABLE `roles`
  ADD PRIMARY KEY (`pkid_rol`);

--
-- Indices de la tabla `servicios`
--
ALTER TABLE `servicios`
  ADD PRIMARY KEY (`pkid_servicio`),
  ADD KEY `fknegocio_servicio` (`fknegocio_servicio`),
  ADD KEY `fkcategoria_servicio` (`fkcategoria_servicio`);

--
-- Indices de la tabla `tipo_documento`
--
ALTER TABLE `tipo_documento`
  ADD PRIMARY KEY (`pkid_doc`);

--
-- Indices de la tabla `tipo_negocio`
--
ALTER TABLE `tipo_negocio`
  ADD PRIMARY KEY (`pkid_tiponeg`);

--
-- Indices de la tabla `usuarios_roles`
--
ALTER TABLE `usuarios_roles`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `usuario_rol_unico` (`fkperfil_id`,`fkrol_id`),
  ADD KEY `fkrol_id` (`fkrol_id`);

--
-- Indices de la tabla `usuario_perfil`
--
ALTER TABLE `usuario_perfil`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `doc_user` (`doc_user`),
  ADD KEY `fkuser_id` (`fkuser_id`),
  ADD KEY `fktipodoc_user` (`fktipodoc_user`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `auth_group`
--
ALTER TABLE `auth_group`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_permission`
--
ALTER TABLE `auth_permission`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=129;

--
-- AUTO_INCREMENT de la tabla `auth_user`
--
ALTER TABLE `auth_user`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=25;

--
-- AUTO_INCREMENT de la tabla `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `carrito_compras`
--
ALTER TABLE `carrito_compras`
  MODIFY `pkid_carrito` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `categoria_productos`
--
ALTER TABLE `categoria_productos`
  MODIFY `pkid_cp` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `detalles_pedido`
--
ALTER TABLE `detalles_pedido`
  MODIFY `pkid_detalle` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `django_admin_log`
--
ALTER TABLE `django_admin_log`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `django_content_type`
--
ALTER TABLE `django_content_type`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=33;

--
-- AUTO_INCREMENT de la tabla `django_migrations`
--
ALTER TABLE `django_migrations`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- AUTO_INCREMENT de la tabla `negocios`
--
ALTER TABLE `negocios`
  MODIFY `pkid_neg` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de la tabla `pedidos`
--
ALTER TABLE `pedidos`
  MODIFY `pkid_pedido` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `productos`
--
ALTER TABLE `productos`
  MODIFY `pkid_prod` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `promociones`
--
ALTER TABLE `promociones`
  MODIFY `pkid_promo` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `reportes`
--
ALTER TABLE `reportes`
  MODIFY `pkid_reporte` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `resenas_negocios`
--
ALTER TABLE `resenas_negocios`
  MODIFY `pkid_resena` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `resenas_servicios`
--
ALTER TABLE `resenas_servicios`
  MODIFY `pkid_resena` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `roles`
--
ALTER TABLE `roles`
  MODIFY `pkid_rol` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de la tabla `servicios`
--
ALTER TABLE `servicios`
  MODIFY `pkid_servicio` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `tipo_documento`
--
ALTER TABLE `tipo_documento`
  MODIFY `pkid_doc` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `tipo_negocio`
--
ALTER TABLE `tipo_negocio`
  MODIFY `pkid_tiponeg` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=39;

--
-- AUTO_INCREMENT de la tabla `usuarios_roles`
--
ALTER TABLE `usuarios_roles`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=24;

--
-- AUTO_INCREMENT de la tabla `usuario_perfil`
--
ALTER TABLE `usuario_perfil`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=24;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  ADD CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  ADD CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);

--
-- Filtros para la tabla `auth_permission`
--
ALTER TABLE `auth_permission`
  ADD CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);

--
-- Filtros para la tabla `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  ADD CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  ADD CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Filtros para la tabla `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  ADD CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  ADD CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Filtros para la tabla `carrito_compras`
--
ALTER TABLE `carrito_compras`
  ADD CONSTRAINT `carrito_compras_ibfk_1` FOREIGN KEY (`fkusuario_carrito`) REFERENCES `usuario_perfil` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `carrito_compras_ibfk_2` FOREIGN KEY (`fknegocio_carrito`) REFERENCES `negocios` (`pkid_neg`) ON DELETE CASCADE,
  ADD CONSTRAINT `carrito_compras_ibfk_3` FOREIGN KEY (`fkproducto_carrito`) REFERENCES `productos` (`pkid_prod`) ON DELETE CASCADE;

--
-- Filtros para la tabla `detalles_pedido`
--
ALTER TABLE `detalles_pedido`
  ADD CONSTRAINT `detalles_pedido_ibfk_1` FOREIGN KEY (`fkpedido_detalle`) REFERENCES `pedidos` (`pkid_pedido`) ON DELETE CASCADE,
  ADD CONSTRAINT `detalles_pedido_ibfk_2` FOREIGN KEY (`fkproducto_detalle`) REFERENCES `productos` (`pkid_prod`);

--
-- Filtros para la tabla `django_admin_log`
--
ALTER TABLE `django_admin_log`
  ADD CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Filtros para la tabla `negocios`
--
ALTER TABLE `negocios`
  ADD CONSTRAINT `negocios_ibfk_1` FOREIGN KEY (`fkpropietario_neg`) REFERENCES `usuario_perfil` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `negocios_ibfk_2` FOREIGN KEY (`fktiponeg_neg`) REFERENCES `tipo_negocio` (`pkid_tiponeg`);

--
-- Filtros para la tabla `pedidos`
--
ALTER TABLE `pedidos`
  ADD CONSTRAINT `pedidos_ibfk_1` FOREIGN KEY (`fkusuario_pedido`) REFERENCES `usuario_perfil` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `pedidos_ibfk_2` FOREIGN KEY (`fknegocio_pedido`) REFERENCES `negocios` (`pkid_neg`) ON DELETE CASCADE;

--
-- Filtros para la tabla `productos`
--
ALTER TABLE `productos`
  ADD CONSTRAINT `productos_ibfk_1` FOREIGN KEY (`fkcategoria_prod`) REFERENCES `categoria_productos` (`pkid_cp`),
  ADD CONSTRAINT `productos_ibfk_2` FOREIGN KEY (`fknegocioasociado_prod`) REFERENCES `negocios` (`pkid_neg`) ON DELETE CASCADE;

--
-- Filtros para la tabla `promociones`
--
ALTER TABLE `promociones`
  ADD CONSTRAINT `promociones_ibfk_1` FOREIGN KEY (`fknegocio_id`) REFERENCES `negocios` (`pkid_neg`) ON DELETE CASCADE,
  ADD CONSTRAINT `promociones_ibfk_2` FOREIGN KEY (`fkproducto_id`) REFERENCES `productos` (`pkid_prod`) ON DELETE SET NULL;

--
-- Filtros para la tabla `reportes`
--
ALTER TABLE `reportes`
  ADD CONSTRAINT `reportes_ibfk_1` FOREIGN KEY (`fknegocio_reportado`) REFERENCES `negocios` (`pkid_neg`) ON DELETE CASCADE,
  ADD CONSTRAINT `reportes_ibfk_2` FOREIGN KEY (`fkusuario_reporta`) REFERENCES `usuario_perfil` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `resenas_negocios`
--
ALTER TABLE `resenas_negocios`
  ADD CONSTRAINT `resenas_negocios_ibfk_1` FOREIGN KEY (`fknegocio_resena`) REFERENCES `negocios` (`pkid_neg`) ON DELETE CASCADE,
  ADD CONSTRAINT `resenas_negocios_ibfk_2` FOREIGN KEY (`fkusuario_resena`) REFERENCES `usuario_perfil` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `resenas_servicios`
--
ALTER TABLE `resenas_servicios`
  ADD CONSTRAINT `resenas_servicios_ibfk_1` FOREIGN KEY (`fkservicio_resena`) REFERENCES `servicios` (`pkid_servicio`) ON DELETE CASCADE,
  ADD CONSTRAINT `resenas_servicios_ibfk_2` FOREIGN KEY (`fkusuario_resena`) REFERENCES `usuario_perfil` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `servicios`
--
ALTER TABLE `servicios`
  ADD CONSTRAINT `servicios_ibfk_1` FOREIGN KEY (`fknegocio_servicio`) REFERENCES `negocios` (`pkid_neg`) ON DELETE CASCADE,
  ADD CONSTRAINT `servicios_ibfk_2` FOREIGN KEY (`fkcategoria_servicio`) REFERENCES `categoria_productos` (`pkid_cp`) ON DELETE SET NULL;

--
-- Filtros para la tabla `usuarios_roles`
--
ALTER TABLE `usuarios_roles`
  ADD CONSTRAINT `usuarios_roles_ibfk_1` FOREIGN KEY (`fkperfil_id`) REFERENCES `usuario_perfil` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `usuarios_roles_ibfk_2` FOREIGN KEY (`fkrol_id`) REFERENCES `roles` (`pkid_rol`) ON DELETE CASCADE;

--
-- Filtros para la tabla `usuario_perfil`
--
ALTER TABLE `usuario_perfil`
  ADD CONSTRAINT `usuario_perfil_ibfk_1` FOREIGN KEY (`fkuser_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `usuario_perfil_ibfk_2` FOREIGN KEY (`fktipodoc_user`) REFERENCES `tipo_documento` (`pkid_doc`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
