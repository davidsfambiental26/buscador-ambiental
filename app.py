import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Buscador local de legislación SGA", layout="wide")

# ---------------- CONFIGURACIÓN ----------------
ASPECTOS_SGA = [
    "Residuos",
    "Emisiones Atmosféricas",
    "Vertidos y Aguas",
    "Suelos Contaminados",
    "Evaluación de Impacto Ambiental",
    "Cambio Climático y Energía",
    "Ruidos y Vibraciones",
    "Sustancias Químicas (REACH/CLP)",
    "Responsabilidad Medioambiental",
    "Envases y Embalajes",
    "Eficiencia Energética",
    "Biodiversidad y Espacios Protegidos",
]

NIVELES = ["UE", "ES", "CAN"]

# ---------------- CARGA DEL EXCEL ----------------
@st.cache_data
def cargar_legislacion(ruta_excel: str):
    # Lee las tres hojas y añade columna Nivel si no existe
    xls = pd.read_excel(ruta_excel, sheet_name=None)

    dfs = []

    for nombre_hoja, nivel in [("EU", "UE"), ("ES", "ES"), ("CAN", "CAN")]:
        if nombre_hoja not in xls:
            continue
        df = xls[nombre_hoja].copy()

        # Normalizamos nombres de columnas
        df.columns = [c.strip() for c in df.columns]

        # Aseguramos columnas mínimas
        for col in ["Nivel", "Aspecto", "Fecha", "Título", "Enlace"]:
            if col not in df.columns:
                df[col] = ""

        # Si no hay Nivel en la hoja, lo fijamos
        df["Nivel"] = df["Nivel"].replace("", nivel)

        # Convertimos Fecha a datetime
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

        dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=["Nivel", "Aspecto", "Fecha", "Título", "Enlace"])

    return pd.concat(dfs, ignore_index=True)


st.title("⚖️ Buscador local de legislación ambiental (SGA)")

ruta_excel = st.text_input(
    "Ruta del archivo Excel con la legislación (legislacion_sga.xlsx):",
    value="legislacion_sga.xlsx",
)

if not ruta_excel:
    st.stop()

try:
    df_all = cargar_legislacion(ruta_excel)
except Exception as e:
    st.error(f"No se pudo leer el archivo: {e}")
    st.stop()

if df_all.empty:
    st.warning("El archivo se ha cargado pero no contiene datos o no se han encontrado las hojas EU/ES/CAN.")
    st.stop()

# ---------------- FILTROS ----------------
with st.sidebar:
    st.header("Filtros de búsqueda")

    nivel_sel = st.multiselect("Nivel", NIVELES, default=NIVELES)

    aspecto_sel = st.multiselect("Aspecto ambiental (SGA)", ASPECTOS_SGA, default=ASPECTOS_SGA)

    # Rango temporal
    min_fecha = df_all["Fecha"].min()
    max_fecha = df_all["Fecha"].max()

    if pd.isna(min_fecha) or pd.isna(max_fecha):
        f_ini = st.date_input("Fecha inicial", value=date(1990, 1, 1))
        f_fin = st.date_input("Fecha final", value=date.today())
    else:
        f_ini = st.date_input("Fecha inicial", value=min_fecha.date())
        f_fin = st.date_input("Fecha final", value=max_fecha.date())

    texto_libre = st.text_input("Búsqueda en título (opcional):", value="")

# ---------------- APLICAR FILTROS ----------------
df_filtrado = df_all.copy()

df_filtrado = df_filtrado[df_filtrado["Nivel"].isin(nivel_sel)]
df_filtrado = df_filtrado[df_filtrado["Aspecto"].isin(aspecto_sel)]

df_filtrado = df_filtrado[
    (df_filtrado["Fecha"] >= pd.to_datetime(f_ini)) &
    (df_filtrado["Fecha"] <= pd.to_datetime(f_fin))
]

if texto_libre:
    df_filtrado = df_filtrado[
        df_filtrado["Título"].str.contains(texto_libre, case=False, na=False)
    ]

# ---------------- RESULTADOS ----------------
st.subheader("Resultados filtrados")

if df_filtrado.empty:
    st.warning("No hay resultados con los filtros seleccionados.")
else:
    # Orden por fecha descendente
    df_filtrado = df_filtrado.sort_values("Fecha", ascending=False)

    # Mostrar con enlace clicable
    st.dataframe(
        df_filtrado[["Nivel", "Aspecto", "Fecha", "Título", "Enlace"]],
        column_config={
            "Enlace": st.column_config.LinkColumn("Abrir norma"),
        },
        hide_index=True,
        use_container_width=True,
    )

    # Opción de descarga
    csv = df_filtrado.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Descargar resultados filtrados (CSV)",
        data=csv,
        file_name="legislacion_filtrada_sga.csv",
        mime="text/csv",
    )
