import requests
import pandas as pd
import streamlit as st
import plotly.express as px

# Configurar la API de Notion
NOTION_API_KEY = st.secrets["NOTION_API_KEY"]
DATABASES = {
    "proyectos": st.secrets["DATABASE_PROYECTOS"],
    "celulas": st.secrets["DATABASE_CELULAS"],
    "productos": st.secrets["DATABASE_PRODUCTOS"],
    "clientes": st.secrets["DATABASE_CLIENTES"],
    "personas": st.secrets["DATABASE_PERSONAS"],
}

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# Función para obtener datos de Notion
#def get_notion_data(database_id):
#    url = f"https://api.notion.com/v1/databases/{database_id}/query"
#    response = requests.post(url, headers=HEADERS)
#    if response.status_code == 200:
#        return response.json()
#    else:
#        st.error(f"Error al obtener datos de Notion ({response.status_code})")
#        return None 


def get_notion_data(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=HEADERS)
    
    # Mostramos el código de estado y la respuesta para depurar errores
    st.write(f"Obteniendo datos de {database_id} -> Código de respuesta: {response.status_code}")
    st.write(response.json())  # Esto nos dirá el error exacto

    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener datos de Notion ({response.status_code})")
        return None



# Función para procesar los datos y convertirlos en DataFrame
def parse_notion_data(data, columns):
    registros = []
    for result in data["results"]:
        props = result.get("properties", {})
        fila = {}
        for col, col_type in columns.items():
            if col_type == "title":
                fila[col] = props.get(col, {}).get("title", [{}])[0].get("text", {}).get("content", "Sin Nombre")
            elif col_type == "select":
                fila[col] = props.get(col, {}).get("select", {}).get("name", "Sin Datos")
            elif col_type == "multi_select":
                fila[col] = ", ".join([opt["name"] for opt in props.get(col, {}).get("multi_select", [])])
            elif col_type == "date":
                fila[col] = props.get(col, {}).get("date", {}).get("start", "")
            elif col_type == "number":
                fila[col] = props.get(col, {}).get("number", 0)
            elif col_type == "relation":
                fila[col] = [rel["id"] for rel in props.get(col, {}).get("relation", [])]
            else:
                fila[col] = "Sin Datos"
        registros.append(fila)
    return pd.DataFrame(registros)

# Obtener y procesar todas las bases de datos
dataframes = {}
columns_mapping = {
    "proyectos": {"Nombre": "title", "Estado": "select", "Fecha Inicio": "date", "Fecha Fin": "date", "Células": "relation", "Productos": "relation"},
    "celulas": {"Nombre": "title", "Personas": "relation"},
    "productos": {"Nombre": "title", "Precio": "number", "Proyectos": "relation"},
    "clientes": {"Nombre": "title", "Sector": "select", "Proyectos": "relation"},
    "personas": {"Nombre": "title", "Cargo": "select", "Célula": "relation"}
}

for key, db_id in DATABASES.items():
    data = get_notion_data(db_id)
    if data:
        dataframes[key] = parse_notion_data(data, columns_mapping[key])

# Crear dashboard en Streamlit
st.title("Dashboard de Gestión de Proyectos")

if "proyectos" in dataframes:
    df_proyectos = dataframes["proyectos"]
    st.subheader("Estado de los Proyectos")
    fig_estado = px.bar(df_proyectos["Estado"].value_counts(), labels={"index": "Estado", "value": "Cantidad"}, title="Distribución de Proyectos")
    st.plotly_chart(fig_estado)
    
    st.subheader("Proyectos en el Tiempo")
    df_proyectos["Fecha Inicio"] = pd.to_datetime(df_proyectos["Fecha Inicio"], errors='coerce')
    df_proyectos["Fecha Fin"] = pd.to_datetime(df_proyectos["Fecha Fin"], errors='coerce')
    df_proyectos = df_proyectos.dropna(subset=["Fecha Inicio", "Fecha Fin"])
    fig_timeline = px.timeline(df_proyectos, x_start="Fecha Inicio", x_end="Fecha Fin", y="Nombre", title="Línea de Tiempo de Proyectos")
    st.plotly_chart(fig_timeline)
    
if "clientes" in dataframes:
    df_clientes = dataframes["clientes"]
    st.subheader("Clientes y Proyectos")
    fig_clientes = px.bar(df_clientes, x="Nombre", y=df_clientes["Proyectos"].apply(len), title="Proyectos por Cliente")
    st.plotly_chart(fig_clientes)

st.write("Actualizado dinámicamente desde Notion API 🚀")
