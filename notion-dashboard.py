import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# =============================================================================
# Configuración: Credenciales y IDs de Notion desde st.secrets
# =============================================================================
NOTION_API_KEY = st.secrets["NOTION_API_KEY"]
DATABASE_PROYECTOS   = st.secrets["DATABASE_PROYECTOS"]
DATABASE_CELULAS     = st.secrets["DATABASE_CELULAS"]
DATABASE_PRODUCTOS   = st.secrets["DATABASE_PRODUCTOS"]
DATABASE_CLIENTES    = st.secrets["DATABASE_CLIENTES"]
DATABASE_PERSONAS    = st.secrets["DATABASE_PERSONAS"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# =============================================================================
# Funciones para obtener y procesar los datos desde Notion
# =============================================================================

@st.cache_data
def get_notion_data(database_id):
    """
    Realiza la consulta a la API de Notion para la base de datos con el ID proporcionado.
    Retorna el JSON con los datos o None en caso de error.
    """
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener datos de Notion (ID: {database_id}): {response.status_code}")
        st.json(response.json())
        return None

def parse_notion_data(data, mapping):
    """
    Convierte la respuesta JSON de Notion en un DataFrame.
    mapping: Diccionario con formato { "NombreColumna": "tipo" }
    Tipos soportados: title, select, multi_select, date, number, relation, rich_text, phone_number, email.
    """
    records = []
    for result in data.get("results", []):
        props = result.get("properties", {})
        record = {}
        for col, col_type in mapping.items():
            if col_type == "title":
                titles = props.get(col, {}).get("title", [])
                record[col] = " ".join([t.get("plain_text", "") for t in titles]) if titles else ""
            elif col_type == "select":
                record[col] = props.get(col, {}).get("select", {}).get("name", "")
            elif col_type == "multi_select":
                multi = props.get(col, {}).get("multi_select", [])
                record[col] = ", ".join([item.get("name", "") for item in multi]) if multi else ""
            elif col_type == "date":
                value = props.get(col)
                if isinstance(value, dict) and "date" in value:
                 record[col] = value["date"].get("start", "")
                else:
                 record[col] = ""
            elif col_type == "number":
                record[col] = props.get(col, {}).get("number", 0)
            elif col_type == "relation":
                rel = props.get(col, {}).get("relation", [])
                record[col] = [item.get("id", "") for item in rel] if rel else []
            elif col_type == "rich_text":
                rich = props.get(col, {}).get("rich_text", [])
                record[col] = " ".join([item.get("plain_text", "") for item in rich]) if rich else ""
            elif col_type == "phone_number":
                record[col] = props.get(col, {}).get("phone_number", "")
            elif col_type == "email":
                record[col] = props.get(col, {}).get("email", "")
            else:
                record[col] = ""
        records.append(record)
    return pd.DataFrame(records)

# =============================================================================
# Mapeo de columnas para cada base de datos (ajusta los nombres según tu Notion)
# =============================================================================

mapping_proyectos = {
    "Nombre": "title",
    "Estado del Proyecto": "select",
    "Fecha de Inicio Estimada": "date",
    "Fecha de Finalización Estimada": "date",
    "Fecha de Inicio Real": "date",
    "Fecha de Finalización Real": "date",
    "Valor": "number",
    "Descripción": "rich_text",
    "👥 Célula": "relation",
    "💸 Cliente/Empresa": "relation",
    "📝 Producto/Servicio": "relation"
}

mapping_celulas = {
    "Nombre": "title",
    "Fecha de Creación": "date",
    "Descripción": "rich_text",
    "Personas Asociadas": "relation",
    "📝 Producto/Servicio": "relation",
    "💼 Proyecto": "relation",
    "Estado": "select"
}

mapping_productos = {
    "Nombre": "title",
    "Descripción": "rich_text",
    "Precio": "number",
    "Fecha de lanzamiento": "date",
    "💼 Proyecto": "relation",
    "👥 Célula": "relation",
    "Estado de Producto": "select"
}

mapping_clientes = {
    "Nombre": "title",
    "Sector": "select",
    "Dirección": "rich_text",
    "Tamaño": "select",
    "Fecha de Registro": "date",
    "💼 Proyecto": "relation",
    "Estado de Cliente": "select",
    "Personas Asociadas": "relation"
}

mapping_personas = {
    "Nombre": "title",
    "Estado": "select",
    "Cargo": "rich_text",
    "Mail": "email",
    "Teléfono": "phone_number",
    "💸 Cliente/Empresa": "relation",
    "👥 Célula": "relation",
    "Fecha de Registro": "date",
    "Tipo Persona": "multi_select"
}

# =============================================================================
# Obtener y procesar los datos de cada base
# =============================================================================

data_proyectos = get_notion_data(DATABASE_PROYECTOS)
data_celulas   = get_notion_data(DATABASE_CELULAS)
data_productos = get_notion_data(DATABASE_PRODUCTOS)
data_clientes  = get_notion_data(DATABASE_CLIENTES)
data_personas  = get_notion_data(DATABASE_PERSONAS)

df_proyectos = parse_notion_data(data_proyectos, mapping_proyectos) if data_proyectos else pd.DataFrame()
df_celulas   = parse_notion_data(data_celulas, mapping_celulas) if data_celulas else pd.DataFrame()
df_productos = parse_notion_data(data_productos, mapping_productos) if data_productos else pd.DataFrame()
df_clientes  = parse_notion_data(data_clientes, mapping_clientes) if data_clientes else pd.DataFrame()
df_personas  = parse_notion_data(data_personas, mapping_personas) if data_personas else pd.DataFrame()

# Convertir columnas de fecha a datetime
def convert_dates(df, mapping):
    for col, typ in mapping.items():
        if typ == "date" and col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

df_proyectos = convert_dates(df_proyectos, mapping_proyectos)
df_celulas   = convert_dates(df_celulas, mapping_celulas)
df_productos = convert_dates(df_productos, mapping_productos)
df_clientes  = convert_dates(df_clientes, mapping_clientes)
df_personas  = convert_dates(df_personas, mapping_personas)

# =============================================================================
# Dashboard en Streamlit: Menú lateral para secciones
# =============================================================================

st.title("Dashboard Notion: Gestión Integral")

section = st.sidebar.radio("Selecciona la sección", 
                           ["Proyectos", "Células", "Productos/Servicios", "Clientes/Empresas", "Personas"])

# =============================================================================
# Sección de Proyectos
# =============================================================================

if section == "Proyectos":
    st.header("Métricas de Proyectos")
    if not df_proyectos.empty:
        # 1. Cantidad total y distribución por estado
        total = len(df_proyectos)
        st.metric("Total de Proyectos", total)
        estado_counts = df_proyectos["Estado del Proyecto"].value_counts().reset_index()
        estado_counts.columns = ["Estado", "Cantidad"]
        fig_estado = px.pie(estado_counts, values="Cantidad", names="Estado", title="Proporción de Proyectos por Estado")
        st.plotly_chart(fig_estado)
        
        # 2. Distribución de proyectos por cliente
        # Suponemos que en "💸 Cliente/Empresa" se guarda una lista de IDs; tomamos el primero si existe.
        df_proyectos["ClienteID"] = df_proyectos["💸 Cliente/Empresa"].apply(lambda x: x[0] if isinstance(x, list) and x else None)
        cliente_counts = df_proyectos["ClienteID"].value_counts().reset_index()
        cliente_counts.columns = ["ClienteID", "Cantidad"]
        st.subheader("Proyectos por Cliente (ID)")
        st.write(cliente_counts)
        fig_cliente = px.bar(cliente_counts, x="ClienteID", y="Cantidad", title="Proyectos por Cliente")
        st.plotly_chart(fig_cliente)
        
        # 3. Duración promedio de los proyectos (usando fechas reales)
        df_duration = df_proyectos.dropna(subset=["Fecha de Inicio Real", "Fecha de Finalización Real"]).copy()
        if not df_duration.empty:
            df_duration["Duracion (días)"] = (df_duration["Fecha de Finalización Real"] - df_duration["Fecha de Inicio Real"]).dt.days
            avg_duration = df_duration["Duracion (días)"].mean()
            st.metric("Duración Promedio (días)", f"{avg_duration:.1f}")
        else:
            st.warning("No hay datos suficientes de fechas reales.")
        
        # 4. Cantidad de proyectos por célula
        df_proyectos["CelulaID"] = df_proyectos["👥 Célula"].apply(lambda x: x[0] if isinstance(x, list) and x else None)
        cell_counts = df_proyectos["CelulaID"].value_counts().reset_index()
        cell_counts.columns = ["CelulaID", "Cantidad"]
        st.subheader("Proyectos por Célula (ID)")
        st.write(cell_counts)
        fig_cell = px.bar(cell_counts, x="CelulaID", y="Cantidad", title="Proyectos por Célula")
        st.plotly_chart(fig_cell)
        
        # 5. % de proyectos retrasados vs. a tiempo (comparando fecha estimada y real de cierre)
        df_time = df_proyectos.dropna(subset=["Fecha de Finalización Estimada", "Fecha de Finalización Real"]).copy()
        if not df_time.empty:
            df_time["Estado Tiempo"] = df_time.apply(
                lambda row: "Retrasado" if row["Fecha de Finalización Real"] > row["Fecha de Finalización Estimada"] else "A Tiempo",
                axis=1
            )
            delay_counts = df_time["Estado Tiempo"].value_counts().reset_index()
            delay_counts.columns = ["Estado Tiempo", "Cantidad"]
            fig_delay = px.pie(delay_counts, values="Cantidad", names="Estado Tiempo", title="Proyectos: Retrasados vs. A Tiempo")
            st.plotly_chart(fig_delay)
        else:
            st.warning("No hay suficientes datos para evaluar retrasos.")
        
        # 6. Evolución de proyectos a lo largo del tiempo (por mes de inicio estimado)
        if "Fecha de Inicio Estimada" in df_proyectos.columns:
            df_proyectos["Mes_Inicio"] = df_proyectos["Fecha de Inicio Estimada"].dt.to_period("M").astype(str)
            timeline = df_proyectos["Mes_Inicio"].value_counts().sort_index().reset_index()
            timeline.columns = ["Mes", "Cantidad"]
            fig_line = px.line(timeline, x="Mes", y="Cantidad", markers=True, title="Evolución de Proyectos")
            st.plotly_chart(fig_line)
    else:
        st.warning("No se encontraron datos de Proyectos.")

# =============================================================================
# Sección de Células (Equipos de Trabajo)
# =============================================================================

elif section == "Células":
    st.header("Métricas de Células")
    if not df_celulas.empty:
        # Número de personas por célula (unir con df_personas)
        if not df_personas.empty:
            df_personas["CelulaID"] = df_personas["👥 Célula"].apply(lambda x: x[0] if isinstance(x, list) and x else None)
            personas_por_celula = df_personas.groupby("CelulaID").size().reset_index(name="Cantidad de Personas")
            st.subheader("Número de Personas por Célula")
            st.write(personas_por_celula)
            fig_personas = px.bar(personas_por_celula, x="CelulaID", y="Cantidad de Personas", title="Personas por Célula")
            st.plotly_chart(fig_personas)
        else:
            st.warning("No hay datos de Personas para relacionar con las Células.")
        
        # Cantidad de proyectos asignados a cada célula
        if not df_proyectos.empty:
            cell_projects = df_proyectos["👥 Célula"].apply(lambda x: x[0] if isinstance(x, list) and x else None)
            cell_project_counts = cell_projects.value_counts().reset_index()
            cell_project_counts.columns = ["CelulaID", "Cantidad de Proyectos"]
            st.subheader("Proyectos por Célula")
            st.write(cell_project_counts)
            fig_cell_proj = px.bar(cell_project_counts, x="CelulaID", y="Cantidad de Proyectos", title="Proyectos por Célula")
            st.plotly_chart(fig_cell_proj)
        else:
            st.warning("No hay datos de Proyectos para asignar a las Células.")
        
        # Tiempo de finalización promedio por célula (usando fechas reales de Proyectos)
        df_time_cell = df_proyectos.dropna(subset=["Fecha de Inicio Real", "Fecha de Finalización Real"]).copy()
        if not df_time_cell.empty:
            df_time_cell["Duracion (días)"] = (df_time_cell["Fecha de Finalización Real"] - df_time_cell["Fecha de Inicio Real"]).dt.days
            df_time_cell["CelulaID"] = df_time_cell["👥 Célula"].apply(lambda x: x[0] if isinstance(x, list) and x else None)
            duration_by_cell = df_time_cell.groupby("CelulaID")["Duracion (días)"].mean().reset_index()
            st.subheader("Duración Promedio de Proyectos por Célula")
            st.write(duration_by_cell)
            fig_duration = px.bar(duration_by_cell, x="CelulaID", y="Duracion (días)", title="Duración Promedio por Célula")
            st.plotly_chart(fig_duration)
        else:
            st.warning("No hay suficientes datos de fechas reales para evaluar duración por Célula.")
    else:
        st.warning("No se encontraron datos de Células.")

# =============================================================================
# Sección de Productos/Servicios
# =============================================================================

elif section == "Productos/Servicios":
    st.header("Métricas de Productos y Servicios")
    if not df_productos.empty and not df_proyectos.empty:
        # Productos más utilizados en Proyectos
        df_proyectos["ProductoID"] = df_proyectos["📝 Producto/Servicio"].apply(lambda x: x[0] if isinstance(x, list) and x else None)
        product_usage = df_proyectos["ProductoID"].value_counts().reset_index()
        product_usage.columns = ["ProductoID", "Cantidad de Usos"]
        st.subheader("Uso de Productos/Servicios")
        st.write(product_usage)
        fig_prod_usage = px.bar(product_usage, x="ProductoID", y="Cantidad de Usos", title="Productos/Servicios más utilizados")
        st.plotly_chart(fig_prod_usage)
        
        # Ingresos totales generados por cada producto
        product_rev = df_productos.copy()
        # Contamos en cuántos proyectos aparece cada producto (buscando por ID en la relación)
        product_rev["Cantidad de Proyectos"] = product_rev["Nombre"].apply(
            lambda prod: df_proyectos["📝 Producto/Servicio"].apply(
                lambda rel: prod in rel if isinstance(rel, list) else False
            ).sum()
        )
        product_rev["Ingresos Totales"] = product_rev["Precio"] * product_rev["Cantidad de Proyectos"]
        st.subheader("Ingresos Totales por Producto/Servicio")
        st.write(product_rev[["Nombre", "Precio", "Cantidad de Proyectos", "Ingresos Totales"]])
        fig_prod_rev = px.bar(product_rev, x="Nombre", y="Ingresos Totales", title="Ingresos Totales por Producto/Servicio")
        st.plotly_chart(fig_prod_rev)
    else:
        st.warning("No hay suficientes datos de Productos o Proyectos.")

# =============================================================================
# Sección de Clientes/Empresas
# =============================================================================

elif section == "Clientes/Empresas":
    st.header("Métricas de Clientes/Empresas")
    if not df_clientes.empty:
        total_clientes = len(df_clientes)
        st.metric("Total de Clientes", total_clientes)
        estado_clientes = df_clientes["Estado de Cliente"].value_counts().reset_index()
        estado_clientes.columns = ["Estado", "Cantidad"]
        fig_client_estado = px.pie(estado_clientes, values="Cantidad", names="Estado", title="Clientes Activos vs. Inactivos")
        st.plotly_chart(fig_client_estado)
        
        # Proyectos por Cliente
        df_clientes["Cantidad de Proyectos"] = df_clientes["💼 Proyecto"].apply(lambda x: len(x) if isinstance(x, list) else 0)
        st.subheader("Proyectos por Cliente")
        fig_client_proj = px.bar(df_clientes, x="Nombre", y="Cantidad de Proyectos", title="Proyectos por Cliente")
        st.plotly_chart(fig_client_proj)
        
        # Distribución del tamaño de las empresas
        tamaño_counts = df_clientes["Tamaño"].value_counts().reset_index()
        tamaño_counts.columns = ["Tamaño", "Cantidad"]
        st.subheader("Distribución de Tamaño de Empresas")
        fig_tamano = px.pie(tamaño_counts, values="Cantidad", names="Tamaño", title="Tamaño de Empresas")
        st.plotly_chart(fig_tamano)
    else:
        st.warning("No se encontraron datos de Clientes/Empresas.")

# =============================================================================
# Sección de Personas
# =============================================================================

elif section == "Personas":
    st.header("Métricas de Personas")
    if not df_personas.empty:
        total_personas = len(df_personas)
        st.metric("Total de Personas", total_personas)
        
        # Personas por Célula
        df_personas["CelulaID"] = df_personas["👥 Célula"].apply(lambda x: x[0] if isinstance(x, list) and x else None)
        personas_por_celula = df_personas.groupby("CelulaID").size().reset_index(name="Cantidad")
        st.subheader("Personas por Célula")
        st.write(personas_por_celula)
        fig_personas_cel = px.bar(personas_por_celula, x="CelulaID", y="Cantidad", title="Distribución de Personas por Célula")
        st.plotly_chart(fig_personas_cel)
        
        # Distribución de Roles/Cargos
        if "Cargo" in df_personas.columns:
            cargos = df_personas["Cargo"].replace("", "Sin Cargo")
            cargo_counts = cargos.value_counts().reset_index()
            cargo_counts.columns = ["Cargo", "Cantidad"]
            st.subheader("Distribución de Roles/Cargos")
            st.write(cargo_counts)
            fig_cargos = px.bar(cargo_counts, x="Cargo", y="Cantidad", title="Roles/Cargos en el Sistema")
            st.plotly_chart(fig_cargos)
            # Nube de palabras para roles, si se tiene la librería wordcloud
            try:
                from wordcloud import WordCloud
                import matplotlib.pyplot as plt
                text = " ".join(cargos)
                wc = WordCloud(width=800, height=400, background_color="white").generate(text)
                plt.figure(figsize=(10, 5))
                plt.imshow(wc, interpolation="bilinear")
                plt.axis("off")
                st.subheader("Nube de Palabras de Roles/Cargos")
                st.pyplot(plt)
            except ImportError:
                st.info("Instalá la librería wordcloud para visualizar la nube de palabras.")
        else:
            st.warning("No se encontró información de Roles/Cargos.")
        
        # (Opcional) Personas con más proyectos asignados:
        # Si la relación de Personas en Proyectos estuviera definida, se podría contar.
    else:
        st.warning("No se encontraron datos de Personas.")

st.write("Dashboard actualizado dinámicamente desde Notion API 🚀")
