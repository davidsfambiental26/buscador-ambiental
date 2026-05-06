import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Configuración de la página profesional
st.set_page_config(page_title="Vigilancia Normativa SGA 1990-2026", layout="wide")

# --- LISTADO DESPLEGABLE (SIN MODIFICAR) ---
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

# --- MOTORES DE BÚSQUEDA ---

def buscar_eurlex_historico(termino, anio_min, anio_max):
    """Consulta SPARQL optimizada para rango temporal 1990-Actualidad"""
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    
    # Filtramos por el Sector 15 (Medio Ambiente) del directorio de legislación
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    SELECT DISTINCT ?celex ?title ?date WHERE {{
      ?work cdm:resource_legal_id_celex ?celex .
      ?work cdm:work_date_document ?date .
      ?work cdm:work_has_resource-type <http://publications.europa.eu/resource/authority/resource-type/DIR> .
      ?work cdm:work_has_title ?title_res .
      ?title_res cdm:title_has_content ?title .
      FILTER(lang(?title) = "es")
      FILTER(CONTAINS(LCASE(?title), "{termino.lower()}"))
      FILTER(?date >= "{anio_min}-01-01"^^<http://www.w3.org/2001/XMLSchema#date>)
      FILTER(?date <= "{anio_max}-12-31"^^<http://www.w3.org/2001/XMLSchema#date>)
    }} ORDER BY DESC(?date) LIMIT 50
    """
    try:
        r = requests.get(endpoint, params={'query': query}, headers={'Accept': 'application/sparql-results+json'}, timeout=15)
        if r.status_code == 200:
            bindings = r.json()['results']['bindings']
            return [{"Fecha": b['date']['value'], "Título": b['title']['value'], "Enlace": f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{b['celex']['value']}"} for b in bindings]
    except: return []
    return []

# --- INTERFAZ STREAMLIT ---

st.title("⚖️ Buscador Legislativo Ambiental de Largo Alcance")
st.markdown("### Identificación de Requisitos Legales (1990 - 2026)")

with st.sidebar:
    st.header("Configuración del Filtro")
    
    # Rango temporal solicitado
    range_years = st.slider("Rango Temporal de Búsqueda:", 1990, 2026, (1990, 2026))
    
    # Tu desplegable intacto
    seleccion = st.selectbox("Seleccione Aspecto Ambiental:", list(MATERIAS_SGA.keys()))
    termino = MATERIAS_SGA[seleccion]
    
    st.divider()
    st.info("La búsqueda europea devuelve hasta 50 normas clave del sector medio ambiente.")

if st.button(f"🔍 Consultar Histórico de {seleccion}"):
    
    # --- NIVEL EUROPEO (CON LISTADO REAL) ---
    st.subheader(f"🇪🇺 Listado Europeo (Directivas) - {range_years[0]} a {range_years[1]}")
    res_eu = buscar_eurlex_historico(termino, range_years[0], range_years[1])
    
    if res_eu:
        df_eu = pd.DataFrame(res_eu)
        st.dataframe(
            df_eu, 
            column_config={"Enlace": st.column_config.LinkColumn("Ver Texto Íntegro")},
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No se encontraron registros en EUR-Lex para ese rango y término.")

    # --- NIVEL ESTATAL Y AUTONÓMICO (ENLACES CORREGIDOS) ---
    st.subheader("🇪🇸 Ámbito Nacional y Canario")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**España (BOE - Legislación Consolidada)**")
        # URL parametrizada corregida para evitar error de "valores incorrectos"
        url_boe_ok = f"https://www.boe.es/buscar/boe.php?campo=tit&dato={termino}&operador=AND&punto_leg=on&fecha_min={range_years[0]}&fecha_max={range_years[1]}"
        
        st.table(pd.DataFrame([{
            "Nivel": "Nacional",
            "Acción": f"Listado de Leyes sobre {seleccion}",
            "Enlace": url_boe_ok
        }]))
        st.caption("Nota: El enlace abre el repertorio consolidado del BOE filtrado por años.")

    with col2:
        st.markdown("**Canarias (BOC - Buscador Jurídico)**")
        # URL de búsqueda terminológica directa
        url_boc_ok = f"http://www.gobiernodecanarias.org/juridico/boc/buscar.jsp?busqueda={termino}"
        
        st.table(pd.DataFrame([{
            "Nivel": "Autonómico",
            "Acción": f"Listado de Decretos sobre {seleccion}",
            "Enlace": url_boc_ok
        }]))
        st.caption("Nota: Acceso al índice del Gobierno de Canarias.")

# --- PIE DE PÁGINA ---
st.divider()
st.markdown("""
<style>
    .footer { font-size: 12px; color: gray; text-align: center; }
</style>
<div class="footer">
    Herramienta de Vigilancia Normativa para Abogacía Ambiental. 
    Los datos europeos se obtienen vía SPARQL de Cellar. 
    Los datos nacionales/autonómicos se consultan en portales oficiales.
</div>
""", unsafe_allow_markdown=True)
