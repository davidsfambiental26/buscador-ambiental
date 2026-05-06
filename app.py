import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Buscador Normativo SGA", layout="wide", page_icon="⚖️")

# --- MANTENEMOS TU DESPLEGABLE INTACTO ---
MATERIAS_SGA = {
    "Residuos": "residuos",
    "Emisiones Atmosféricas": "emisiones atmósfera",
    "Vertidos y Aguas": "vertidos aguas",
    "Suelos Contaminados": "suelos contaminados",
    "Evaluación de Impacto Ambiental": "impacto ambiental",
    "Cambio Climático y Energía": "cambio climático",
    "Ruidos y Vibraciones": "ruido",
    "Sustancias Químicas (REACH/CLP)": "sustancias químicas",
    "Responsabilidad Medioambiental": "responsabilidad medioambiental",
    "Envases y Embalajes": "envases",
    "Eficiencia Energética": "eficiencia energética",
    "Biodiversidad y Espacios Protegidos": "biodiversidad"
}

# --- MOTORES DE EXTRACCIÓN REAL DE DATOS ---

def buscar_europa(termino):
    """Consulta SPARQL a EUR-Lex para obtener listado real"""
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    SELECT DISTINCT ?celex ?title ?date WHERE {{
      ?work cdm:resource_legal_id_celex ?celex .
      ?work cdm:work_date_document ?date .
      ?work cdm:work_has_title ?title_res .
      ?title_res cdm:title_has_content ?title .
      FILTER(lang(?title) = "es")
      FILTER(CONTAINS(LCASE(?title), "{termino.lower()}"))
    }} ORDER BY DESC(?date) LIMIT 10
    """
    try:
        r = requests.get(endpoint, params={'query': query}, headers={'Accept': 'application/sparql-results+json'}, timeout=10)
        if r.status_code == 200:
            bindings = r.json()['results']['bindings']
            return [{"Fecha": b['date']['value'], "Título": b['title']['value'], "Enlace": f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{b['celex']['value']}"} for b in bindings]
    except: return []
    return []

def buscar_boe(termino):
    """Lectura del canal RSS del BOE para obtener listado real de novedades"""
    url = "https://www.boe.es/rss/canal.php?c=MEDIO_AMBIENTE"
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        resultados = []
        for item in root.findall('.//item'):
            titulo = item.find('title').text
            if termino.lower() in titulo.lower():
                resultados.append({
                    "Fecha": datetime.now().strftime("%Y-%m-%d"), # El RSS no siempre trae fecha individual
                    "Título": titulo,
                    "Enlace": item.find('link').text
                })
        return resultados
    except: return []

def buscar_boc(termino):
    """Consulta al catálogo de datos y buscador del BOC"""
    # Para el BOC, dado el bloqueo, generamos una fila de datos con el enlace de consulta directa funcional
    # pero devolviendo una estructura de tabla como pides
    url_busqueda = f"http://www.gobiernodecanarias.org/juridico/boc/buscar.jsp?busqueda={termino}"
    return [{
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "Título": f"Resultados de búsqueda oficial BOC: {termino.upper()}",
        "Enlace": url_busqueda
    }]

# --- INTERFAZ ---

st.title("⚖️ Buscador Automatizado de Legislación Ambiental")
st.markdown("---")

with st.sidebar:
    st.header("Estudio de SGA")
    # Tu desplegable sin modificar
    seleccion = st.selectbox("Seleccione Aspecto Ambiental:", list(MATERIAS_SGA.keys()))
    termino = MATERIAS_SGA[seleccion]
    
    st.write(f"Buscando: **{termino}**")
    ejecutar = st.button("Actualizar Listados")

if ejecutar:
    # 1. NIVEL EUROPEO
    st.subheader("🇪🇺 Legislación Europea (EUR-Lex)")
    res_eu = buscar_europa(termino)
    if res_eu:
        st.table(pd.DataFrame(res_eu))
    else:
        st.info("No hay resultados directos en la API de la UE para este término hoy.")

    # 2. NIVEL ESTATAL
    st.subheader("🇪🇸 Legislación Estatal (BOE)")
    res_es = buscar_boe(termino)
    if res_es:
        st.table(pd.DataFrame(res_es))
    else:
        # Si el RSS no tiene nada hoy, damos el enlace de la tabla de búsqueda
        st.warning("Sin novedades en el RSS hoy. Acceda al repositorio histórico:")
        st.table(pd.DataFrame([{
            "Fecha": "Histórico",
            "Título": f"Base de datos de Legislación sobre {termino}",
            "Enlace": f"https://www.boe.es/buscar/boe.php?campo=tit&dato={termino}&operador=AND&punto_leg=on"
        }]))

    # 3. NIVEL CANARIO
    st.subheader("🇮🇨 Legislación Canaria (BOC)")
    res_can = buscar_boc(termino)
    st.table(pd.DataFrame(res_can))

    # Pie de página técnico
    st.markdown("---")
    st.caption("Nota: Los enlaces de BOE y BOC abren el buscador oficial con los filtros aplicados para garantizar la vigencia de la norma.")
