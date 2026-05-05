# app_v1_completa.py - BUSCADOR COMPLETO (UE + BOE + BOC)
import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuración
st.set_page_config(page_title="Buscador Legislativo Ambiental", page_icon="🌍", layout="wide")

st.title("🔍 Buscador de Legislación Ambiental")
st.markdown("**Unión Europea | España | Canarias**")

# ============================================
# PALABRAS CLAVE COMPLETAS (solo español)
# ============================================
CATEGORIAS = {
    "Agua": ["agua", "hidrológico", "vertido", "depuración", "acuífero", "desalación", "trasvase", "embalse", "cuenca", "regadío"],
    "Residuos": ["residuo", "basura", "reciclaje", "vertedero", "economía circular", "envases", "plástico", "orgánico", "peligroso"],
    "Aire": ["aire", "atmósfera", "emisión", "calidad del aire", "ozono", "partículas", "CO2", "contaminación atmosférica"],
    "Suelo": ["suelo", "contaminación del suelo", "restauración", "sedimento", "erosión"],
    "Ruido": ["ruido", "acústica", "vibración", "sonométrico", "decibelios"],
    "Radiactividad": ["radiactivo", "nuclear", "radiación", "Euratom", "central nuclear"]
}

# ============================================
# CONFIGURACIÓN DE SESIÓN PARA EVITAR BLOQUEOS
# ============================================
if 'resultados_mostrados' not in st.session_state:
    st.session_state.resultados_mostrados = False
if 'ultima_busqueda' not in st.session_state:
    st.session_state.ultima_busqueda = None

# ============================================
# FUNCIÓN 1: BUSCADOR EUR-LEX (CON SPARQL MEJORADO)
# ============================================
def buscar_eurlex_con_timeout(palabra, fecha_inicio, fecha_fin, timeout=20):
    """
    Búsqueda en EUR-Lex con manejo de timeouts y reintentos
    """
    resultados = []
    
    # Traducción para EUR-Lex
    traduccion_rapida = {
        "agua": "water", "residuos": "waste", "aire": "air",
        "suelo": "soil", "ruido": "noise", "radiactividad": "radioactivity"
    }
    termino_ue = traduccion_rapida.get(palabra.lower(), palabra.lower())
    
    # Endpoint SPARQL
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    
    # Consulta SPARQL más simple y robusta
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    
    SELECT DISTINCT ?title ?celex ?date
    WHERE {{
        ?work a cdm:work.
        ?work dc:title ?title.
        OPTIONAL {{ ?work cdm:work_celex ?celex. }}
        OPTIONAL {{ ?work cdm:work_date_document ?date. }}
        FILTER( CONTAINS(LCASE(?title), "{termino_ue}") )
    }}
    LIMIT 10
    """
    
    # Configurar sesión con reintentos
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.5)
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        response = session.post(
            endpoint,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            
            for binding in bindings:
                titulo = binding.get("title", {}).get("value", "Sin título")[:200]
                celex = binding.get("celex", {}).get("value", "")
                fecha = binding.get("date", {}).get("value", "")[:10]
                
                if celex:
                    url = f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{celex}"
                    resultados.append({
                        "Título": titulo,
                        "Fuente": "EUR-Lex (UE)",
                        "Fecha": fecha if fecha else "Fecha no disponible",
                        "Estado": "✅ Verificar vigencia en enlace",
                        "Enlace": url
                    })
                    
    except requests.exceptions.Timeout:
        st.warning("⏰ EUR-Lex: Tiempo de espera agotado. El servidor de la UE está lento.")
    except Exception as e:
        st.warning(f"⚠️ EUR-Lex: {str(e)[:80]}")
    
    return resultados

# ============================================
# FUNCIÓN 2: BUSCADOR BOE (CON TIMEOUT CORTO)
# ============================================
def buscar_boe_con_timeout(palabra, fecha_inicio, fecha_fin, timeout=10):
    """Búsqueda en BOE con timeout controlado"""
    resultados = []
    url = "https://www.boe.es/buscar/api.php"
    
    params = {
        'q': palabra,
        'fecha_desde': fecha_inicio.strftime("%Y%m%d"),
        'fecha_hasta': fecha_fin.strftime("%Y%m%d"),
        'coleccion': 'boe',
        'pageSize': 15
    }
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            for item in data.get('resultados', []):
                titulo = item.get('titulo', 'Sin título')
                estado = "✅ Vigente"
                if re.search(r'derogad[ao]|sin vigencia', titulo.lower()):
                    estado = "❌ DEROGADA"
                
                resultados.append({
                    "Título": titulo[:200],
                    "Fuente": "BOE (España)",
                    "Fecha": item.get('fecha', ''),
                    "Estado": estado,
                    "Enlace": f"https://www.boe.es{item.get('url_pdf', '')}"
                })
    except requests.exceptions.Timeout:
        st.warning("⏰ BOE: Tiempo de espera agotado")
    except Exception as e:
        st.warning(f"⚠️ BOE: {str(e)[:50]}")
    
    return resultados

# ============================================
# FUNCIÓN 3: BUSCADOR BOC (OPTIMIZADO - NO BLOQUEA)
# ============================================
def buscar_boc_optimizado(palabra, año_inicio=2015, año_fin=None):
    """
    Búsqueda en BOC limitada a años recientes para evitar bloqueos
    """
    if año_fin is None:
        año_fin = datetime.now().year
    
    # Limitar a últimos 5 años para no bloquear
    año_inicio = max(año_inicio, año_fin - 5)
    
    resultados = []
    
    for año in range(año_inicio, año_fin + 1):
        # Solo buscar en últimos 6 meses del año actual
        meses_a_buscar = range(1, 13) if año < año_fin else range(1, datetime.now().month + 1)
        
        for mes in meses_a_buscar:
            url_sumario = f"https://www.gobiernodecanarias.org/boc/sumarios/{año}/{str(mes).zfill(2)}/"
            
            try:
                response = requests.get(url_sumario, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    texto = soup.get_text().lower()
                    
                    if palabra.lower() in texto:
                        resultados.append({
                            "Título": f"Contenido en BOC ({año}/{mes}) - '{palabra}'",
                            "Fuente": "BOC (Canarias)",
                            "Fecha": f"{año}-{str(mes).zfill(2)}-01",
                            "Estado": "✅ Verificar en BOC",
                            "Enlace": url_sumario
                        })
                time.sleep(0.3)
            except:
                pass
    
    return resultados

# ============================================
# INTERFAZ DE USUARIO
# ============================================
st.sidebar.header("🔍 Configuración")

categoria = st.sidebar.selectbox("Categoría ambiental", list(CATEGORIAS.keys()))
palabra = st.sidebar.selectbox("Palabra clave", CATEGORIAS[categoria])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌍 Niveles a consultar")
buscar_ue = st.sidebar.checkbox("🇪🇺 Unión Europea (EUR-Lex)", value=True, 
                                 help="Búsqueda en tiempo real - Puede tardar hasta 20 segundos")
buscar_es = st.sidebar.checkbox("🇪🇸 España (BOE)", value=True)
buscar_can = st.sidebar.checkbox("🇮🇨 Canarias (BOC)", value=True, 
                                 help="Búsqueda limitada a últimos 5 años")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Rango temporal (BOE/BOC)")
fecha_desde = st.sidebar.date_input("Desde", datetime(2015, 1, 1))
fecha_hasta = st.sidebar.date_input("Hasta", datetime.now())

st.sidebar.markdown("---")
st.sidebar.warning("⚠️ Las búsquedas en EUR-Lex pueden tardar hasta 20 segundos")

boton_buscar = st.sidebar.button("🔍 BUSCAR LEGISLACIÓN", type="primary", use_container_width=True)

# ============================================
# EJECUCIÓN DE BÚSQUEDA
# ============================================
if boton_buscar:
    st.session_state.resultados_mostrados = True
    st.session_state.ultima_busqueda = palabra
    
    st.header(f"📋 Resultados para: '{palabra}'")
    
    resultados_totales = []
    errores = []
    
    # Barra de progreso
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    # Búsqueda UE
    if buscar_ue:
        progress_text.text("🇪🇺 Buscando en EUR-Lex (puede tardar)...")
        resultados_ue = buscar_eurlex_con_timeout(palabra, fecha_desde, fecha_hasta)
        resultados_totales.extend(resultados_ue)
        progress_bar.progress(33)
        if not resultados_ue:
            errores.append("EUR-Lex no devolvió resultados")
    
    # Búsqueda BOE
    if buscar_es:
        progress_text.text("🇪🇸 Buscando en BOE...")
        resultados_es = buscar_boe_con_timeout(palabra, fecha_desde, fecha_hasta)
        resultados_totales.extend(resultados_es)
        progress_bar.progress(66)
    
    # Búsqueda BOC
    if buscar_can:
        progress_text.text("🇮🇨 Buscando en BOC...")
        resultados_can = buscar_boc_optimizado(palabra, fecha_desde.year, fecha_hasta.year)
        resultados_totales.extend(resultados_can)
        progress_bar.progress(100)
    
    progress_text.empty()
    progress_bar.empty()
    
    # Mostrar resultados
    if resultados_totales:
        st.success(f"✅ Total: {len(resultados_totales)} resultados")
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📄 Total", len(resultados_totales))
        col2.metric("🇪🇺 UE", len([r for r in resultados_totales if "EUR-Lex" in r["Fuente"]]))
        col3.metric("🇪🇸 BOE", len([r for r in resultados_totales if "BOE" in r["Fuente"]]))
        col4.metric("🇮🇨 BOC", len([r for r in resultados_totales if "BOC" in r["Fuente"]]))
        
        df = pd.DataFrame(resultados_totales)
        st.dataframe(df[["Título", "Fuente", "Fecha", "Estado"]], use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar CSV", csv, f"legislacion_{palabra}.csv", "text/csv")
    else:
        st.warning("No se encontraron resultados")
        
    if errores:
        with st.expander("ℹ️ Información de la búsqueda"):
            for error in errores:
                st.caption(error)

else:
    if not st.session_state.resultados_mostrados:
        st.info("👈 Selecciona categoría y haz clic en BUSCAR")
        st.caption("La búsqueda en EUR-Lex puede tardar hasta 20 segundos por limitaciones del servidor de la UE")
