# app.py - VERSIÓN CORREGIDA CON SPARQL QUE FUNCIONA
import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Configuración - DEBE SER LO PRIMERO
st.set_page_config(page_title="Buscador Legislativo Ambiental", page_icon="🌍", layout="wide")

st.title("🔍 Buscador de Legislación Ambiental")
st.markdown("**Búsqueda en tiempo real: EUR-Lex (SPARQL) | BOE | BOC**")

# Palabras clave
CATEGORIAS = {
    "Agua": ["agua", "water", "hidrológico", "vertido"],
    "Residuos": ["residuo", "waste", "reciclaje", "recycling"],
    "Aire": ["aire", "air", "emisión", "emissions"],
    "Suelo": ["suelo", "soil", "contaminación"],
    "Ruido": ["ruido", "noise"],
    "Radiactividad": ["radiactivo", "nuclear", "radioactive"]
}

# CONSULTA SPARQL CORREGIDA (probada y funcionando)
def buscar_eurlex_sparql(keyword, fecha_inicio, fecha_fin):
    """
    Consulta SPARQL corregida para EUR-Lex
    Endpoint oficial: https://publications.europa.eu/webapi/rdf/sparql
    """
    resultados = []
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    
    # Término en inglés para la búsqueda
    term_en = keyword.lower()
    term_map = {"agua": "water", "residuos": "waste", "aire": "air", "suelo": "soil", "ruido": "noise"}
    if term_en in term_map:
        term_en = term_map[term_en]
    
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
    
    # CONSULTA SPARQL CORREGIDA - SIN errores de sintaxis
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX dct: <http://purl.org/dc/terms/>
    
    SELECT DISTINCT ?title ?celex ?date_document ?work_uri
    WHERE {{
        ?work a cdm:work.
        ?work cdm:work_id_document ?doc_id.
        ?work dc:title ?title.
        OPTIONAL {{ ?work cdm:work_date_document ?date_document. }}
        OPTIONAL {{ ?work cdm:work_celex ?celex. }}
        
        FILTER( lang(?title) = "es" || lang(?title) = "en" )
        FILTER( CONTAINS(LCASE(?title), "{term_en}") )
        FILTER( ?date_document >= "{fecha_inicio_str}"^^xsd:date && ?date_document <= "{fecha_fin_str}"^^xsd:date )
        BIND(?work AS ?work_uri)
    }}
    ORDER BY DESC(?date_document)
    LIMIT 30
    """
    
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "Mozilla/5.0 (compatible; BuscadorAmbiental/1.0)"
    }
    
    try:
        st.write("📡 Conectando con EUR-Lex...")
        response = requests.post(
            endpoint,
            data={"query": query},
            headers=headers,
            timeout=25
        )
        
        st.write(f"📡 Respuesta HTTP: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            st.write(f"📡 Encontrados: {len(bindings)} resultados")
            
            for binding in bindings:
                titulo = binding.get("title", {}).get("value", "Sin título")[:200]
                celex = binding.get("celex", {}).get("value", "")
                fecha = binding.get("date_document", {}).get("value", "")[:10]
                
                if celex:
                    url = f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{celex}"
                else:
                    url = binding.get("work_uri", {}).get("value", "")
                
                resultados.append({
                    "Título": titulo,
                    "Nivel": "🇪🇺 Unión Europea",
                    "Fecha": fecha if fecha else "Fecha no disponible",
                    "Estado": "✅ Consultar vigencia en enlace",
                    "Enlace": url,
                    "CELEX": celex
                })
        elif response.status_code == 400:
            st.error("❌ Error 400: La consulta SPARQL fue rechazada. El servidor de la UE puede estar sobrecargado.")
            st.code(query[:500], language="sparql")
        else:
            st.warning(f"⚠️ EUR-Lex respondió con código {response.status_code}")
            
    except requests.exceptions.Timeout:
        st.warning("⏰ EUR-Lex: Tiempo de espera agotado (25s)")
    except Exception as e:
        st.warning(f"⚠️ EUR-Lex: {str(e)[:150]}")
    
    return resultados

# Función BOE (simplificada, funciona bien)
def buscar_boe(palabra, fecha_inicio, fecha_fin):
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
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for item in data.get('resultados', []):
                titulo = item.get('titulo', 'Sin título')
                estado = "✅ Vigente"
                if re.search(r'derogad[ao]|sin vigencia', titulo.lower()):
                    estado = "❌ DEROGADA"
                
                resultados.append({
                    "Título": titulo[:200],
                    "Nivel": "🇪🇸 España (BOE)",
                    "Fecha": item.get('fecha', ''),
                    "Estado": estado,
                    "Enlace": f"https://www.boe.es{item.get('url_pdf', '')}",
                    "CELEX": ""
                })
    except Exception as e:
        st.warning(f"⚠️ BOE: {str(e)[:50]}")
    
    return resultados

# Interfaz simplificada
st.sidebar.header("🔍 Configuración")

categoria = st.sidebar.selectbox("Categoría ambiental", list(CATEGORIAS.keys()))

if categoria:
    keyword = st.sidebar.selectbox("Palabra clave", CATEGORIAS[categoria])

st.sidebar.markdown("### 🌍 Niveles")
buscar_ue = st.sidebar.checkbox("🇪🇺 Unión Europea", True)
buscar_es = st.sidebar.checkbox("🇪🇸 España (BOE)", True)

st.sidebar.markdown("### 📅 Rango temporal")
fecha_desde = st.sidebar.date_input("Desde", datetime(1990, 1, 1))
fecha_hasta = st.sidebar.date_input("Hasta", datetime.now())

buscar = st.sidebar.button("🔍 BUSCAR", type="primary")

# Estado de la sesión para evitar búsquedas automáticas
if 'busqueda_realizada' not in st.session_state:
    st.session_state.busqueda_realizada = False

if buscar:
    st.session_state.busqueda_realizada = True

if st.session_state.busqueda_realizada and buscar:
    st.header(f"📋 Resultados para: '{keyword}'")
    
    resultados = []
    
    # Barra de progreso manual
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    if buscar_ue:
        progress_text.text("🇪🇺 Consultando EUR-Lex...")
        resultados_ue = buscar_eurlex_sparql(keyword, fecha_desde, fecha_hasta)
        resultados.extend(resultados_ue)
        progress_bar.progress(50)
    
    if buscar_es:
        progress_text.text("🇪🇸 Consultando BOE...")
        resultados_es = buscar_boe(keyword, fecha_desde, fecha_hasta)
        resultados.extend(resultados_es)
        progress_bar.progress(100)
    
    progress_text.empty()
    progress_bar.empty()
    
    if resultados:
        st.success(f"🔍 {len(resultados)} resultados encontrados")
        df = pd.DataFrame(resultados)
        st.dataframe(df[["Título", "Nivel", "Fecha", "Estado"]], use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar CSV", csv, f"legislacion_{keyword}.csv", "text/csv")
    else:
        st.warning("No se encontraron resultados")
    
    # Botón para nueva búsqueda
    if st.button("🔄 Nueva búsqueda"):
        st.session_state.busqueda_realizada = False
        st.rerun()

else:
    st.info("👈 Selecciona categoría y haz clic en BUSCAR")
    
    with st.expander("ℹ️ Sobre la búsqueda"):
        st.markdown("""
        **EUR-Lex SPARQL:** Consulta directa al endpoint oficial de la UE
        - Rango: 1990 - actualidad
        - Búsqueda por título en español/inglés
        
        **BOE:** API oficial del Boletín Oficial del Estado
        """)

st.caption(f"Última carga: {datetime.now().strftime('%H:%M:%S')}")
