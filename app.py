import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# Configuración de la interfaz profesional
st.set_page_config(page_title="Monitor Legislativo SGA", layout="wide", page_icon="⚖️")

# --- 1. AMPLIACIÓN DE MATERIAS SGA ---
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

# --- 2. FUNCIONES DE EXTRACCIÓN DE DATOS ---

def fetch_europa(materia):
    """Extracción real vía SPARQL de la UE"""
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    SELECT DISTINCT ?celex ?title ?date WHERE {{
      ?work cdm:resource_legal_id_celex ?celex .
      ?work cdm:work_date_document ?date .
      ?work cdm:work_has_resource-type <http://publications.europa.eu/resource/authority/resource-type/DIR> .
      ?work cdm:work_has_title ?title_res .
      ?title_res cdm:title_has_content ?title .
      FILTER(lang(?title) = "es")
      FILTER(CONTAINS(LCASE(?title), "{materia.lower()}"))
    }} ORDER BY DESC(?date) LIMIT 10
    """
    try:
        r = requests.get(endpoint, params={'query': query}, headers={'Accept': 'application/sparql-results+json'}, timeout=10)
        if r.status_code == 200:
            bindings = r.json()['results']['bindings']
            return [{"Fecha": b['date']['value'], "Título": b['title']['value'], "Enlace": f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{b['celex']['value']}"} for b in bindings]
    except: return []
    return []

def fetch_boe(materia):
    """Uso del buscador de Legislación del BOE mediante URL de consulta directa"""
    # El BOE no permite scraping fácil, generamos la fila de acceso a la tabla de resultados real
    url_boe = f"https://www.boe.es/buscar/boe.php?campo=tit&dato={materia}&operador=AND&punto_leg=on"
    return [{
        "Fecha": "Consultar Actualización",
        "Título": f"Repertorio Consolidado: Normativa sobre {materia.upper()}",
        "Enlace": url_boe
    }]

def fetch_boc(materia):
    """Enlace directo al listado de resultados del Gobierno de Canarias"""
    url_boc = f"http://www.gobiernodecanarias.org/juridico/boc/buscar.jsp?busqueda={materia}"
    return [{
        "Fecha": "Consultar Actualización",
        "Título": f"Disposiciones Autonómicas: {materia.upper()}",
        "Enlace": url_boc
    }]

# --- 3. INTERFAZ DE USUARIO ---

st.title("🌿 Monitor de Legislación Ambiental para SGA")
st.markdown("### Identificación y Evaluación de Requisitos Legales")

with st.sidebar:
    st.header("Parámetros del Estudio")
    seleccion = st.selectbox("Seleccione Aspecto Ambiental:", list(MATERIAS_SGA.keys()))
    termino_busqueda = MATERIAS_SGA[seleccion]
    
    st.divider()
    st.write("**Instrucciones:**")
    st.caption("1. Seleccione el aspecto ambiental.")
    st.caption("2. El sistema consultará Europa, España y Canarias.")
    st.caption("3. Use los enlaces para descargar el PDF oficial.")

if st.button(f"🚀 Ejecutar Auditoría para {seleccion}"):
    
    # --- NIVEL EUROPEO ---
    st.subheader("🇪🇺 Nivel Europeo (Directivas y Reglamentos)")
    data_eu = fetch_europa(termino_busqueda)
    if data_eu:
        df_eu = pd.DataFrame(data_eu)
        st.dataframe(df_eu, column_config={"Enlace": st.column_config.LinkColumn("PDF/HTML")}, use_container_width=True, hide_index=True)
    else:
        st.warning("No se encontraron Directivas recientes con ese término en EUR-Lex.")

    # --- NIVEL ESTATAL ---
    st.subheader("🇪🇸 Nivel Nacional (BOE)")
    data_es = fetch_boe(termino_busqueda)
    df_es = pd.DataFrame(data_es)
    st.dataframe(df_es, column_config={"Enlace": st.column_config.LinkColumn("Acceso al Listado BOE")}, use_container_width=True, hide_index=True)

    # --- NIVEL AUTONÓMICO ---
    st.subheader("🇮🇨 Nivel Autonómico (BOC - Canarias)")
    data_can = fetch_boc(termino_busqueda)
    df_can = pd.DataFrame(data_can)
    st.dataframe(df_can, column_config={"Enlace": st.column_config.LinkColumn("Acceso al Listado BOC")}, use_container_width=True, hide_index=True)

    # --- BOTÓN DE EXPORTACIÓN ---
    st.divider()
    st.write("¿Deseas exportar estos puntos de control?")
    # Consolidamos todo para el CSV
    full_report = pd.concat([pd.DataFrame(data_eu), pd.DataFrame(data_es), pd.DataFrame(data_can)])
    csv = full_report.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Tabla de Requisitos (CSV)", csv, "matriz_legislativa.csv", "text/csv")
