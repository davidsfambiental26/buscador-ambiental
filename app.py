import streamlit as st
import pandas as pd
import requests
from datetime import date

# Configuración de la página
st.set_page_config(page_title="Vigilancia Normativa SGA", layout="wide")

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

# --- FUNCIÓN DE CONSULTA EUROPEA ---
def buscar_eurlex(termino, fecha_inicio, fecha_fin):
    endpoint = "https://publications.europa.eu/webapi/rdf/sparql"
    # Convertimos fechas a string para la consulta SPARQL
    f_ini = fecha_inicio.strftime("%Y-%m-%d")
    f_fin = fecha_fin.strftime("%Y-%m-%d")
    
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    SELECT DISTINCT ?celex ?title ?date WHERE {{
      ?work cdm:resource_legal_id_celex ?celex .
      ?work cdm:work_date_document ?date .
      ?work cdm:work_has_title ?title_res .
      ?title_res cdm:title_has_content ?title .
      FILTER(lang(?title) = "es")
      FILTER(CONTAINS(LCASE(?title), "{termino.lower()}"))
      FILTER(?date >= "{f_ini}"^^<http://www.w3.org/2001/XMLSchema#date>)
      FILTER(?date <= "{f_fin}"^^<http://www.w3.org/2001/XMLSchema#date>)
    }} ORDER BY DESC(?date) LIMIT 50
    """
    try:
        r = requests.get(endpoint, params={'query': query}, headers={'Accept': 'application/sparql-results+json'}, timeout=12)
        if r.status_code == 200:
            res = r.json()['results']['bindings']
            return [{"Fecha": b['date']['value'], "Título": b['title']['value'], "Enlace": f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{b['celex']['value']}"} for b in res]
    except: return []
    return []

# --- INTERFAZ ---
st.title("⚖️ Buscador Legislativo Ambiental")
st.subheader("Estudio de SGA - Vigilancia de Requisitos Legales")

with st.sidebar:
    st.header("Parámetros de Auditoría")
    
    # Calendarios para selección de fecha exacta
    fecha_inicio = st.date_input("Fecha Inicial:", value=date(1990, 1, 1), min_value=date(1990, 1, 1))
    fecha_final = st.date_input("Fecha Final:", value=date.today())
    
    st.divider()
    
    # Selector de materia (Intacto)
    seleccion = st.selectbox("Aspecto Ambiental:", list(MATERIAS_SGA.keys()))
    termino = MATERIAS_SGA[seleccion]
    
    st.divider()
    ejecutar = st.button("🔍 Ejecutar Vigilancia")

if ejecutar:
    # Validación de fechas
    if fecha_inicio > fecha_final:
        st.error("Error: La fecha inicial no puede ser posterior a la fecha final.")
    else:
        # 1. NIVEL EUROPEO (TABLA REAL)
        st.subheader(f"🇪🇺 Normativa Europea: {seleccion}")
        lista_eu = buscar_eurlex(termino, fecha_inicio, fecha_final)
        
        if lista_eu:
            df_eu = pd.DataFrame(lista_eu)
            st.dataframe(
                df_eu, 
                column_config={"Enlace": st.column_config.LinkColumn("Texto Íntegro")}, 
                hide_index=True, 
                use_container_width=True
            )
        else:
            st.info("No se encontraron resultados en el repositorio europeo para estas fechas.")

        # 2. NIVEL NACIONAL Y CANARIO (TABLA DE ACCESO)
        st.subheader("🇪🇸 Ámbito Nacional y Autonómico")
        
        # Enlaces parametrizados con las fechas seleccionadas
        url_boe = f"https://www.boe.es/buscar/boe.php?campo=tit&dato={termino}&operador=AND&punto_leg=on&fmin={fecha_inicio.year}&fmax={fecha_final.year}"
        url_boc = f"http://www.gobiernodecanarias.org/juridico/boc/buscar.jsp?busqueda={termino}"
        
        data_locales = [
            {"Nivel": "España (BOE)", "Detalle": f"Legislación consolidada (Rango anual {fecha_inicio.year}-{fecha_final.year})", "Acceso": url_boe},
            {"Nivel": "Canarias (BOC)", "Detalle": f"Buscador jurídico - Materia: {seleccion}", "Acceso": url_boc}
        ]
        
        st.dataframe(
            pd.DataFrame(data_locales), 
            column_config={"Acceso": st.column_config.LinkColumn("Abrir Resultados")}, 
            hide_index=True, 
            use_container_width=True
        )

# --- PIE DE PÁGINA SEGURO ---
st.divider()
st.caption(f"Consulta generada el {date.today().strftime('%d/%m/%Y')} | Fuente: EUR-Lex (Cellar), BOE y BOC.")
