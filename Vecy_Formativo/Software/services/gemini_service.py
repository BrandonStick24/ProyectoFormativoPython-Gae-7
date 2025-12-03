from google import genai
import json
import os
from pathlib import Path
from django.apps import apps
from django.utils import timezone
from urllib.parse import urlencode
from difflib import SequenceMatcher

class GeminiAssistant:
    def __init__(self):
        self._cargar_variables_entorno()
        self.api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            print("⚠️ GEMINI_API_KEY no encontrada - Modo limitado")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
                print("🚀 Gemini Asistente iniciado")
            except Exception as e:
                print(f"⚠️ Error iniciando Gemini: {e}")
                self.client = None
        
        self.conversacion_historial = []
        self.cache_productos = None
        self.cache_timestamp = None
    
    def _cargar_variables_entorno(self):
        try:
            ruta_env = Path(__file__).parent.parent.parent / '.env'
            if ruta_env.exists():
                with open(ruta_env, 'r', encoding='utf-8') as f:
                    for linea in f:
                        linea = linea.strip()
                        if linea and not linea.startswith('#') and '=' in linea:
                            key, value = linea.split('=', 1)
                            os.environ[key.strip()] = value.strip()
        except Exception as e:
            print(f"⚠️ Error .env: {e}")
    
    def _convertir_markdown_a_html(self, texto):
        if not texto:
            return texto
        
        import re
        texto = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', texto)
        texto = re.sub(r'\*(.*?)\*', r'<em>\1</em>', texto)
        texto = texto.replace('\n', '<br>')
        return texto
    
    def _calcular_similitud(self, palabra1, palabra2):
        """Calcula similitud entre dos palabras (0-1)"""
        return SequenceMatcher(None, palabra1.lower(), palabra2.lower()).ratio()
    
    def _buscar_palabra_en_texto(self, palabra, texto):
        """Busca palabra en texto considerando errores ortográficos"""
        if not texto:
            return 0
        
        palabras_texto = texto.lower().split()
        mejor_similitud = 0
        
        for palabra_texto in palabras_texto:
            similitud = self._calcular_similitud(palabra, palabra_texto)
            if similitud > mejor_similitud:
                mejor_similitud = similitud
        
        return mejor_similitud
    
    def _buscar_productos_inteligente(self, consulta, productos):
        """Búsqueda ultra-tolerante a errores"""
        consulta_lower = consulta.lower().strip()
        productos_encontrados = []
        
        # Diccionario de sinónimos y errores comunes - MÁS EXTENSO
        sinonimos = {
            'audifonos': ['audífonos', 'audifono', 'audífono', 'headphones', 'auriculares', 
                         'sonido', 'audio', 'gamer', 'bluetooth', 'inalambricos', 
                         'inalámbricos', 'headset', 'manos libres', 'earbuds', 'cascos', 
                         'diadema', 'adifonos', 'audifon', 'oudifonos', 'odifonos', 
                         'audifonos bluetooth', 'auriculares bluetooth', 'headphones gamer',
                         'audifonos inalambricos', 'audifono bluetooth', 'audifonos gamer',
                         'adifono', 'odifono', 'aud', 'audiofono', 'adufono'],
            
            'iphone': ['iphone', 'iphones', 'iphonex', 'iphone11', 'iphone12', 'iphone13', 
                      'iphone14', 'iphone15', 'ifon', 'ifone', 'i phone', 'i-phone', 
                      'celular apple', 'smartphone apple', 'apple', 'celular ios',
                      'apple iphone', 'iphone pro', 'iphone max', 'iphone plus',
                      'ifon pro', 'ifone max', 'aifon', 'aifone', 'celular iphone',
                      'celular ifon', 'movil iphone'],
            
            'helados': ['helado', 'heladería', 'postre', 'crema', 'nieve', 'sorbete', 
                       'cremolada', 'gelato', 'paleta', 'cono', 'tarrina', 'postre frío',
                       'gelado', 'elado', 'heldaos', 'hela2', 'helaos', 'hela', 'ice cream',
                       'helado de crema', 'helado chocolate', 'helado vainilla', 'helado fresa',
                       'heldo', 'hela', 'hela', 'heladito', 'helados artesanales'],
            
            'tecnologia': ['tecnología', 'tecnologia', 'electronica', 'electrónica', 
                          'gadgets', 'electrodomésticos', 'dispositivos', 'smart', 
                          'inteligente', 'digital', 'tecno', 'tecnologias', 'tech',
                          'tecnologico', 'tecnológica', 'electronic', 'electrónicos',
                          'tec', 'tecn', 'gadget', 'dispositivo'],
            
            'ropa': ['vestuario', 'moda', 'camisa', 'pantalon', 'zapatos', 'calzado', 
                    'vestido', 'falda', 'blusa', 'chaqueta', 'abrigo', 'accesorio',
                    'ropa', 'ropas', 'prenda', 'prendas', 'ropa mujer', 'ropa hombre',
                    'moda mujer', 'moda hombre', 'camiseta', 'jeans', 'short', 'suéter',
                    'sweater', 'blus', 'pantal', 'chaquet', 'abrig', 'vestid'],
            
            'comida': ['alimento', 'comestible', 'restaurante', 'cocina', 'comestibles', 
                      'alimentos', 'hamburguesa', 'pizza', 'sushi', 'ensalada', 'sandwich', 
                      'comida rápida', 'almuerzo', 'cena', 'desayuno', 'comid', 'comi',
                      'fast food', 'comida rapida', 'comida mexicana', 'comida china',
                      'comida italiana', 'comi', 'com', 'comi', 'almuer', 'cena', 'desayun'],
            
            'zapatos': ['zapatos', 'calzado', 'tenis', 'sneakers', 'zapatillas', 'zapato',
                       'zapat', 'zapatito', 'zapatillas deportivas', 'zapatos deportivos',
                       'tennis', 'zapas', 'zapatillas running', 'zapatos casual',
                       'zapatos formales', 'zapat', 'zapat', 'teni', 'sneaker', 'calzad'],
            
            'computadora': ['computador', 'laptop', 'portatil', 'pc', 'ordenador', 'notebook',
                           'desktop', 'computadora', 'computadoras', 'comput', 'pc gamer',
                           'laptop gamer', 'portátil', 'notebook', 'computadora portatil',
                           'comput', 'lapto', 'porta', 'ordenad', 'notebok', 'deskt', 'pcgam'],
            
            'telefono': ['teléfono', 'celular', 'smartphone', 'móvil', 'mobile', 'movil',
                        'telefono', 'telefonos', 'celulares', 'móviles', 'cel', 'celu',
                        'smartphone', 'celular gamer', 'telefon', 'celula', 'smartphon',
                        'mobi', 'mov', 'celu', 'smart', 'phone', 'telef'],
            
            'libro': ['libros', 'lectura', 'novela', 'cuento', 'texto', 'literatura',
                     'lib', 'libr', 'libritos', 'libros novelas', 'novelas', 'cuentos',
                     'lib', 'libr', 'novel', 'cuent', 'lectur', 'text', 'literatur'],
            
            'mueble': ['muebles', 'muebleria', 'silla', 'mesa', 'sofá', 'sofa', 'cama',
                      'estante', 'rack', 'escritorio', 'mueble de sala', 'mueble cocina',
                      'muebl', 'sill', 'mes', 'sof', 'cam', 'estant', 'rack', 'escritori'],
            
            'deporte': ['deportes', 'deportivo', 'gimnasio', 'ejercicio', 'fitness',
                       'deport', 'deporte', 'equipo deportivo', 'accesorios deportivos',
                       'deport', 'gimnasi', 'ejercici', 'fitnes', 'equipo deport'],
        }
        
        # Procesar consulta
        palabras_consulta = consulta_lower.split()
        
        for producto in productos:
            nombre_lower = producto['nombre'].lower()
            descripcion_lower = (producto['descripcion'] or '').lower()
            categoria_lower = producto['categoria'].lower()
            
            puntuacion = 0
            coincidencia_exacta = False
            
            # 1. COINCIDENCIA EXACTA (máxima prioridad)
            if consulta_lower == nombre_lower:
                puntuacion += 100
                coincidencia_exacta = True
            
            # 2. CONSULTA CONTENIDA EN NOMBRE
            elif consulta_lower in nombre_lower:
                puntuacion += 80
                coincidencia_exacta = True
            
            # 3. CADA PALABRA DE LA CONSULTA EN NOMBRE
            for palabra in palabras_consulta:
                if len(palabra) <= 2:
                    continue  # Ignorar palabras muy cortas
                    
                # En nombre directamente
                if palabra in nombre_lower:
                    puntuacion += 40
                
                # Con similitud en nombre (errores tipográficos)
                sim_nombre = self._buscar_palabra_en_texto(palabra, nombre_lower)
                if sim_nombre > 0.7:  # 70% de similitud
                    puntuacion += int(35 * sim_nombre)
                
                # En descripción
                if palabra in descripcion_lower:
                    puntuacion += 20
                
                # Con similitud en descripción
                sim_desc = self._buscar_palabra_en_texto(palabra, descripcion_lower)
                if sim_desc > 0.7:
                    puntuacion += int(15 * sim_desc)
            
            # 4. VERIFICAR SINÓNIMOS
            for palabra_consulta in palabras_consulta:
                for categoria, lista_sinonimos in sinonimos.items():
                    # Si la palabra de consulta está en sinónimos
                    if palabra_consulta in lista_sinonimos or palabra_consulta == categoria:
                        # Verificar si el producto tiene palabras de esta categoría
                        for sinonimo in lista_sinonimos:
                            if sinonimo in nombre_lower:
                                puntuacion += 50
                                break
                            elif sinonimo in descripcion_lower:
                                puntuacion += 30
                                break
            
            # 5. BONUS POR MÚLTIPLES COINCIDENCIAS
            coincidencias = 0
            for palabra in palabras_consulta:
                if len(palabra) <= 2:
                    continue
                    
                if (palabra in nombre_lower or 
                    self._buscar_palabra_en_texto(palabra, nombre_lower) > 0.7 or
                    palabra in descripcion_lower or
                    self._buscar_palabra_en_texto(palabra, descripcion_lower) > 0.7):
                    coincidencias += 1
            
            if coincidencias >= 2:
                puntuacion += coincidencias * 15
            
            # 6. INCLUIR SI TIENE ALGUNA PUNTUACIÓN
            if puntuacion > 0:
                producto['puntuacion_relevancia'] = puntuacion
                producto['es_exacto'] = coincidencia_exacta
                productos_encontrados.append(producto)
        
        # Ordenar por relevancia
        productos_encontrados.sort(key=lambda x: x.get('puntuacion_relevancia', 0), reverse=True)
        
        print(f"🔍 Búsqueda '{consulta_lower}':")
        print(f"   Encontrados: {len(productos_encontrados)} productos")
        
        if productos_encontrados:
            for i, p in enumerate(productos_encontrados[:3]):
                print(f"   {i+1}. {p['nombre'][:40]}... (punt: {p['puntuacion_relevancia']})")
        
        return productos_encontrados
    
    def _obtener_datos_reales_bd(self, user_id=None):
        """Obtiene datos de la base de datos"""
        try:
            ahora = timezone.now()
            
            # Cache por 2 minutos
            if (self.cache_productos and 
                self.cache_timestamp and 
                (ahora - self.cache_timestamp).seconds < 120):
                return self.cache_productos
            
            Productos = apps.get_model('Software', 'Productos')
            CategoriaProductos = apps.get_model('Software', 'CategoriaProductos')
            
            datos_reales = {
                "productos": [],
                "categorias": [],
                "negocios": [],
                "ofertas_activas": []
            }
            
            # Obtener categorías
            categorias = CategoriaProductos.objects.all()
            mapa_categorias = {}
            for cat in categorias:
                datos_reales["categorias"].append({
                    "id": cat.pkid_cp,
                    "nombre": cat.desc_cp,
                    "slug": cat.desc_cp.lower().replace(' ', '-')
                })
                mapa_categorias[cat.pkid_cp] = cat.desc_cp
            
            # Obtener productos activos
            productos = Productos.objects.filter(
                estado_prod='disponible'
            ).select_related('fkcategoria_prod', 'fknegocioasociado_prod')[:250]  # Más productos
            
            for p in productos:
                try:
                    categoria_nombre = p.fkcategoria_prod.desc_cp if p.fkcategoria_prod else "General"
                    categoria_id = p.fkcategoria_prod.pkid_cp if p.fkcategoria_prod else None
                    
                    producto_data = {
                        "id": p.pkid_prod,
                        "nombre": p.nom_prod,
                        "precio": float(p.precio_prod) if p.precio_prod else 0.0,
                        "precio_final": float(p.precio_prod) if p.precio_prod else 0.0,
                        "categoria": categoria_nombre,
                        "categoria_id": categoria_id,
                        "categoria_slug": mapa_categorias.get(categoria_id, ""),
                        "negocio": p.fknegocioasociado_prod.nom_neg if p.fknegocioasociado_prod else "Vecy",
                        "negocio_id": p.fknegocioasociado_prod.pkid_neg if p.fknegocioasociado_prod else None,
                        "descripcion": p.desc_prod or "",
                        "stock": p.stock_prod or 0,
                        "imagen": p.img_prod.url if p.img_prod and hasattr(p.img_prod, 'url') else None
                    }
                    datos_reales["productos"].append(producto_data)
                except Exception as e:
                    continue
            
            self.cache_productos = datos_reales
            self.cache_timestamp = ahora
            
            print(f"📊 Datos cargados: {len(datos_reales['productos'])} productos")
            return datos_reales
            
        except Exception as e:
            print(f"❌ Error BD: {e}")
            import traceback
            traceback.print_exc()
            return {
                "productos": [],
                "categorias": [],
                "negocios": [],
                "ofertas_activas": []
            }
    
    def _crear_url_productos_filtrados(self, consulta, productos_encontrados):
        """Crea URL para /productos-filtrados/ con parámetros inteligentes"""
        
        params = {
            'buscar': consulta,
            'ordenar': 'recientes'
        }
        
        # Si hay productos encontrados, agregar filtros inteligentes
        if productos_encontrados:
            # Obtener rango de precios de los productos encontrados
            precios = [p.get('precio', 0) for p in productos_encontrados if p.get('precio', 0) > 0]
            if precios:
                precio_min = min(precios)
                precio_max = max(precios)
                # Ampliar un poco el rango
                params['precio_min'] = int(precio_min * 0.9)
                params['precio_max'] = int(precio_max * 1.1)
            
            # Verificar si hay categoría predominante
            categorias_count = {}
            for producto in productos_encontrados[:20]:
                cat_id = producto.get('categoria_id')
                if cat_id:
                    categorias_count[cat_id] = categorias_count.get(cat_id, 0) + 1
            
            if categorias_count:
                mejor_categoria = max(categorias_count, key=categorias_count.get)
                params['categoria'] = str(mejor_categoria)
        
        # Filtrar valores vacíos
        params_filtrados = {k: v for k, v in params.items() if v not in ['', None]}
        
        url = "/productos-filtrados/?" + urlencode(params_filtrados)
        print(f"🔗 URL generada: {url}")
        
        return url
    
    def obtener_respuesta_interactiva(self, consulta_usuario, user_id=None):
        """Método principal - SOLO usa /productos-filtrados/"""
        try:
            print(f"\n" + "="*60)
            print(f"🤖 ASISTENTE - Consulta: '{consulta_usuario}'")
            print(f"👤 Usuario ID: {user_id}")
            
            # Obtener datos de BD
            datos_reales = self._obtener_datos_reales_bd(user_id)
            
            # Buscar productos (con máxima tolerancia)
            productos_encontrados = self._buscar_productos_inteligente(
                consulta_usuario, datos_reales["productos"]
            )
            
            # Crear URL para /productos-filtrados/ (ÚNICA RUTA VÁLIDA)
            url_filtros = self._crear_url_productos_filtrados(consulta_usuario, productos_encontrados)
            
            # Si no hay Gemini, respuesta directa
            if not self.client:
                print("⚠️ Modo sin Gemini - respuesta directa")
                return self._respuesta_directa_simple(consulta_usuario, productos_encontrados, url_filtros)
            
            # Preparar información para Gemini
            productos_destacados_info = []
            for p in productos_encontrados[:4]:
                precio = p.get('precio_final', p.get('precio', 0))
                productos_destacados_info.append(f"- {p['nombre']} (${precio:,.0f})")
            
            # PROMPT SIMPLIFICADO Y DIRECTO
            prompt = f"""
            Eres VECY_ASISTENTE, asistente de compras de Vecy.
            
            El usuario busca: "{consulta_usuario}"
            
            Resultados encontrados: {len(productos_encontrados)} productos
            
            Productos destacados:
            {chr(10).join(productos_destacados_info) if productos_destacados_info else "No se encontraron productos específicos"}
            
            URL de filtros: {url_filtros}
            
            INSTRUCCIONES IMPORTANTES:
            1. Tu respuesta debe ser natural y conversacional
            2. Si hay productos, menciona 1-2 específicos
            3. Siempre invita a hacer clic en el botón para ver los filtros
            4. La URL debe ser exactamente: {url_filtros}
            
            Formato de respuesta JSON:
            {{
                "respuesta_chat": "Texto amigable aquí (máximo 2 oraciones)",
                "tipo_respuesta": "productos|sugerencia",
                "datos_interactivos": {{
                    "mostrar_productos": true/false,
                    "productos_destacados": [IDs de productos],
                    "url_filtros": "{url_filtros}",
                    "texto_boton_filtro": "Ver productos encontrados"
                }},
                "sugerencia_navegacion": {{
                    "pagina_recomendada": "productos_filtrados_logeado",
                    "url_destino": "{url_filtros}",
                    "confianza": 8,
                    "razon": "Ver productos filtrados"
                }}
            }}
            
            Respuesta JSON:
            """
            
            # Llamar a Gemini
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            # Parsear respuesta
            texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
            resultado = json.loads(texto_limpio)
            
            # GARANTIZAR QUE TODO USE LA RUTA CORRECTA
            resultado["datos_interactivos"]["url_filtros"] = url_filtros
            resultado["sugerencia_navegacion"]["url_destino"] = url_filtros
            resultado["sugerencia_navegacion"]["pagina_recomendada"] = "productos_filtrados_logeado"
            
            # Configurar productos destacados
            if productos_encontrados:
                resultado["datos_interactivos"]["mostrar_productos"] = True
                resultado["datos_interactivos"]["productos_destacados"] = [
                    str(p['id']) for p in productos_encontrados[:3]
                ]
                resultado["datos_interactivos"]["texto_boton_filtro"] = f"Ver {len(productos_encontrados)} productos"
                resultado["sugerencia_navegacion"]["confianza"] = 9
            else:
                resultado["datos_interactivos"]["mostrar_productos"] = False
                resultado["datos_interactivos"]["texto_boton_filtro"] = "Explorar productos"
                resultado["sugerencia_navegacion"]["confianza"] = 6
            
            # Convertir markdown
            resultado["respuesta_chat"] = self._convertir_markdown_a_html(resultado["respuesta_chat"])
            
            print(f"✅ Respuesta generada")
            print(f"   URL: {url_filtros}")
            print(f"   Productos: {len(productos_encontrados)} encontrados")
            print("="*60 + "\n")
            
            return resultado
            
        except json.JSONDecodeError as e:
            print(f"❌ Error JSON: {e}")
            print(f"   Respuesta Gemini: {response.text[:200] if 'response' in locals() else 'N/A'}")
            return self._respuesta_directa_simple(consulta_usuario, productos_encontrados, url_filtros)
            
        except Exception as e:
            print(f"❌ Error general: {e}")
            import traceback
            traceback.print_exc()
            url_fallback = f"/productos-filtrados/?buscar={consulta_usuario}&ordenar=recientes"
            return self._respuesta_directa_simple(consulta_usuario, productos_encontrados, url_fallback)
    
    def _respuesta_directa_simple(self, consulta, productos_encontrados, url_filtros):
        """Respuesta directa que SIEMPRE usa /productos-filtrados/"""
        
        if productos_encontrados:
            primer_producto = productos_encontrados[0]
            precio = primer_producto.get('precio_final', primer_producto.get('precio', 0))
            
            respuesta = f"🎯 ¡Perfecto! Encontré <strong>{len(productos_encontrados)} productos</strong> para '<em>{consulta}</em>'. Te recomiendo <strong>{primer_producto['nombre']}</strong> por <strong>${precio:,.0f}</strong>. ¡Haz clic para ver todos con filtros aplicados!"
            
            return {
                "respuesta_chat": respuesta,
                "tipo_respuesta": "productos",
                "datos_interactivos": {
                    "mostrar_productos": True,
                    "productos_destacados": [str(p['id']) for p in productos_encontrados[:3]],
                    "url_filtros": url_filtros,
                    "texto_boton_filtro": f"Ver {len(productos_encontrados)} productos"
                },
                "sugerencia_navegacion": {
                    "pagina_recomendada": "productos_filtrados_logeado",
                    "url_destino": url_filtros,
                    "confianza": 9,
                    "razon": f"{len(productos_encontrados)} productos encontrados para '{consulta}'"
                }
            }
        else:
            respuesta = f"🔍 No encontré productos específicos para '<em>{consulta}</em>'. ¿Quieres <strong>explorar todos nuestros productos</strong> o intentar con otra búsqueda?"
            
            # URL de respaldo SIEMPRE a /productos-filtrados/
            url_respaldo = f"/productos-filtrados/?buscar={consulta}&ordenar=recientes"
            
            return {
                "respuesta_chat": respuesta,
                "tipo_respuesta": "sugerencia",
                "datos_interactivos": {
                    "mostrar_productos": False,
                    "url_filtros": url_respaldo,
                    "texto_boton_filtro": "Explorar productos",
                    "sugerencias": ["audífonos", "iphone", "helados", "ropa", "zapatos", "comida", "tecnología"]
                },
                "sugerencia_navegacion": {
                    "pagina_recomendada": "productos_filtrados_logeado",
                    "url_destino": url_respaldo,
                    "confianza": 6,
                    "razon": "Explorar todos los productos disponibles"
                }
            }
    
    def limpiar_cache(self):
        self.cache_productos = None
        self.cache_timestamp = None
        print("🔄 Cache limpiado")

# Instancia global
asistente_gemini = GeminiAssistant()