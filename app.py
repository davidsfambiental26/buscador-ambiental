import streamlit as st
import pandas as pd
import urllib.parse

# Configuración de página
st.set_page_config(page_title="Vigilancia Ambiental SGA", layout="wide", page_icon="🌿")

## --- FUNCIONES DE CONSTRUCCIÓN DE ENLACES (Vínculos Directos) ---

def get_eurlex_link(query):
    # Genera una búsqueda terminológica en el repositorio de legislación europea
    base_url = "https://eur-lex.europa.eu/search.html?"
    params = {
        "scope": "EURLEX",
        "text": query,
        "lang": "es",
        "type": "quick",
        "qid": "123"
    }
    return base_url + urllib.parse.urlencode(params)

def get_boe_link(query):
    # Genera enlace al buscador del BOE para Legislación Consolidada (la que importa en SGA)
    base_url = "https://www.boe.es/buscar/boe.php?"
    params = {
        "campo": "tit",
        "dato": query,
        "operador": "AND",
        "punto_leg": "on" # Filtra solo legislación, evita anuncios
    }
    return base_url + urllib.parse.urlencode(params)

def get_boc_link(query):
    # Enlace al buscador oficial del Boletín Oficial de Canarias
    base_url = "http://www.gobiernodecanarias.org/juridico/boc/buscar.jsp?"
    params = {"busqueda": query}
    return base_url + urllib.parse.urlencode(params)

## --- INTERFAZ STREAMLIT ---

st.title("⚖️ Buscador Legislativo Ambiental Integrado")
st.subheader("Herramienta de cumplimiento para Sistemas de Gestión Ambiental (SGA)")

with st.sidebar:
    st.header("Configuración de búsqueda")
    aspecto = st.selectbox("Aspecto Ambiental a Evaluar:", 
                            ["Residuos", "Cambio Climático", "Emisiones Atmosféricas", 
                             "Vertidos", "Suelos Contaminados", "Eficiencia Energética"])
    
    st.info("Esta herramienta genera enlaces directos a las bases de datos jurídicas oficiales.")

# Ejecución de la búsqueda
if st.button(f"Generar Matriz de Requisitos para: {aspecto}"):
    
    # Creamos un diccionario con los niveles normativos
    # Usamos URLs de búsqueda parametrizadas que el servidor del BOE/BOC aceptará
    data = [
        {
            "Nivel": "Unión Europea (Directivas/Reglamentos)",
            "Fuente": "EUR-Lex",
            "Descripción": f"Legislación vigente sobre {aspecto} en el marco de la UE.",
            "Enlace": get_eurlex_link(aspecto)
        },
        {
            "Nivel": "Estado Español (Leyes/RD)",
            "Fuente": "BOE (Legislación)",
            "Descripción": f"Normativa estatal consolidada aplicable a {aspecto}.",
            "Enlace": get_boe_link(aspecto)
        },
        {
            "Nivel": "Comunidad Autónoma (Canarias)",
            "Fuente": "BOC",
            "Descripción": f"Decretos y órdenes regionales para Canarias sobre {aspecto}.",
            "Enlace": get_boc_link(aspecto)
        }
    ]
    
    df = pd.DataFrame(data)
    
    st.success(f"Se han generado los puntos de acceso para la materia: {aspecto}")
    
    # Visualización con Links activos
    st.data_editor(
        df,
        column_config={
            "Enlace": st.column_config.LinkColumn(
                "Abrir Buscador Oficial",
                help="Haz clic para abrir el buscador oficial con los resultados filtrados",
                validate=r"^http",
                display_text="Ver Normativa Actualizada"
            ),
        },
        disabled=["Nivel", "Fuente", "Descripción"],
        hide_index=True,
        use_container_width=True
    )

    st.warning("⚠️ Nota del Abogado: Al hacer clic, se abrirá una pestaña nueva con la búsqueda oficial pre-cargada. Verifique que la norma no haya sido derogada.")

st.markdown("---")
st.caption("Especialista en Derecho Ambiental - Automatización de Vigilancia Normativa v3.0")
