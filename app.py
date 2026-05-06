import streamlit as st
import pandas as pd
import requests
from datetime import date

# Configuración de la página
st.set_page_config(page_title="Monitor Ambiental Legal", layout="wide")

# --- LISTADO DESPLEGABLE (MANTENIDO INTACTO) ---
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

# --- FUNCIÓN DE CONSULTA EUROPA (SPARQL) ---
def buscar_eurlex(termino, f_inicio, f_fin):
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    # Formateo de fechas para SPARQL
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    SELECT DISTINCT ?celex ?title ?date WHERE {{
      ?work cdm:resource_legal_id_celex ?celex .
      ?work cdm:work_date_document ?date .
      ?work cdm:work_has_title ?title_res .
      ?title_res cdm:title_has_content ?title .
      FILTER(lang(?title) = "es")
      FILTER(CONTAINS(LCASE(?title), "{termino.lower()}"))
      FILTER(?date >= "{f_inicio}"^^<http://www.w3.org/2001/XMLSchema#date>)
      FILTER(?date <= "{f_fin}"^^<http://www.w3.org/2001/XMLSchema#date>)
    }} ORDER BY DESC(?date) LIMIT 25
    """
    try:
        r = requests.get(endpoint, params={'query': query}, headers={'Accept': 'application/sparql-results+json'}, timeout=15)
        if r.status_code == 200:
            res = r.json()['results']['bindings']
            return [{"Fecha": b['date']['value'], "Normativa": b['title']['value'], "Enlace": f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{b['celex']['value']}"} for b in res]
    except:
        return []
    return []

# --- INTERFAZ ---
st.title("⚖️ Buscador Legislativo de Materias Ambientales")

with st.sidebar:
    st.header("Filtros Temporales")
    f_ini = st.date_input("Fecha Inicial:", value=date(1990, 1, 1), min_value=date(1990, 1, 1))
    f_fin = st.date_input("Fecha Final:", value=date.today())
    
    st.divider()
    # Desplegable intacto
    seleccion = st.selectbox("Aspecto Ambiental:", list(MATERIAS_SGA.keys()))
    termino = MATERIAS_SGA[seleccion]
    
    ejecutar = st.button("🔍 Obtener Listados")

if ejecutar:
    # 1. NIVEL EUROPEO
    st.subheader(f"🇪🇺 Listado de Directivas y Reglamentos Europeos ({seleccion})")
    with st.spinner("Consultando repositorio de la Unión Europea..."):
        listado_eu = buscar_eurlex(termino, f_ini, f_fin)
        if listado_eu:
            df_eu = pd.DataFrame(listado_eu)
            st.dataframe(
                df_eu, 
                column_config={"Enlace": st.column_config.LinkColumn("Abrir Norma")},
                hide_index=True, 
                use_container_width=True
            )
        else:
            st.warning("EUR-Lex no devolvió resultados para este término en el rango elegido. Pruebe a ampliar el término.")

    # 2. NIVEL NACIONAL Y CANARIO (ENLACES DE EJECUCIÓN DIRECTA)
    st.subheader("🇪🇸 Ámbito Nacional e Insular")
    st.info("Debido a restricciones de seguridad de los servidores del BOE y BOC, use los siguientes accesos directos para generar el listado oficial en tiempo real:")
    
    # Construcción de URLs de búsqueda funcional para BOE y BOC
    # BOE: Filtro por título, legislación y rango de fechas
    url_boe = f"https://www.boe.es/buscar/boe.php?campo=tit&dato={termino}&operador=AND&punto_leg=on&fmin={f_ini.year}&fmax={f_fin.year}"
    
    # BOC: Buscador jurídico oficial del Gobierno de Canarias
    url_boc = f"http://www.gobiernodecanarias.org/juridico/boc/buscar.jsp?busqueda={termino}"

    # Tabla de listados nacionales
    data_nacional = [
        {
            "Nivel": "ESTATAL (BOE)", 
            "Descripción": f"Listado completo de Leyes y Reales Decretos sobre {seleccion}", 
            "Acceso": url_boe
        },
        {
            "Nivel": "CANARIAS (BOC)", 
            "Descripción": f"Listado de Decretos y Órdenes de la C.A. Canaria sobre {seleccion}", 
            "Acceso": url_boc
        }
    ]
    
    df_nacional = pd.DataFrame(data_nacional)
    st.dataframe(
        df_nacional,
        column_config={"Acceso": st.column_config.LinkColumn("Generar Listado en Diario Oficial")},
        hide_index=True,
        use_container_width=True
    )

st.divider()
st.caption("Nota profesional: Los enlaces estatales y autonómicos abren el listado oficial actualizado en el portal del legislador.")
