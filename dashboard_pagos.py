import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import io
import base64

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Proyección de Pagos - Agosto 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3D59;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6B7B8D;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1E3D59;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E3D59;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6B7B8D;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .alert-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .alert-success {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
    }
    .alert-warning {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
    }
    .alert-danger {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }
    .stButton > button {
        background-color: #1E3D59;
        color: white;
        border-radius: 20px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        border: none;
    }
    .stButton > button:hover {
        background-color: #2C5A7A;
        color: white;
    }
    .filter-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #1E3D59;
    }
    .css-1d391kg {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# 1. CARGA Y PROCESAMIENTO DE DATOS
# ============================================

@st.cache_data
def load_and_process_data(file, tasa_bcv, tasa_cop=4000):
    """
    Carga y procesa el archivo Excel con la proyección de pagos
    """
    try:
        # Cargar el archivo Excel
        df = pd.read_excel(file, sheet_name='Plantilla', header=0)
        
        # Limpieza de datos
        df = df.dropna(subset=['CATEGORIA DE LA PARTIDA'], how='all')
        df = df[df['CATEGORIA DE LA PARTIDA'].notna()]
        
        # Filtrar filas vacías o con todos los valores nulos
        df = df.dropna(how='all')
        
        # Limpiar nombres de columnas
        df.columns = df.columns.str.strip()
        
        # Convertir montos a numérico
        df['MONTO PLAN USD'] = pd.to_numeric(df['MONTO PLAN USD'], errors='coerce').fillna(0)
        
        # Calcular MONTO_EN_USD según la moneda
        def calcular_monto_usd(row):
            monto = row['MONTO PLAN USD']
            moneda = str(row['MONEDA DE PAGO']).strip().upper()
            
            if pd.isna(monto) or monto == 0:
                return 0.0
            
            if moneda == 'USD':
                return float(monto)
            elif moneda in ['BS/USD', 'BS', 'BS.']:
                # Convertir BS a USD usando la tasa BCV
                return float(monto) / tasa_bcv if tasa_bcv > 0 else 0
            elif moneda == 'COP':
                return float(monto) / tasa_cop if tasa_cop > 0 else 0
            else:
                # Si no tiene moneda, asumir que está en USD
                return float(monto)
        
        df['MONTO_EN_USD'] = df.apply(calcular_monto_usd, axis=1)
        
        # Limpiar categorías
        df['CATEGORIA_LIMPIA'] = df['CATEGORIA DE LA PARTIDA'].str.replace(r'^\d+\.\s*', '', regex=True)
        df['CATEGORIA_LIMPIA'] = df['CATEGORIA_LIMPIA'].str.replace(r'^\d+\.\s*', '', regex=True)
        
        # Extraer TIPO DE PARTIDA (OPEX/CAPEX) de la categoría
        df['TIPO'] = df['CATEGORIA_LIMPIA'].apply(
            lambda x: 'OPEX' if 'OPEX' in str(x).upper() else ('CAPEX' if 'CAPEX' in str(x).upper() else 'OTROS')
        )
        
        return df
    
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}")
        return pd.DataFrame()

# ============================================
# 2. FUNCIONES DE VISUALIZACIÓN
# ============================================

def crear_kpi_globales(df):
    """
    Crea las tarjetas KPI globales
    """
    total_opex = df[df['TIPO'] == 'OPEX']['MONTO_EN_USD'].sum()
    total_capex = df[df['TIPO'] == 'CAPEX']['MONTO_EN_USD'].sum()
    total_general = total_opex + total_capex
    porcentaje_opex = (total_opex / total_general * 100) if total_general > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Total OPEX",
            value=f"${total_opex:,.2f}",
            delta=f"{porcentaje_opex:.1f}% del total"
        )
    
    with col2:
        st.metric(
            label="🏗️ Total CAPEX",
            value=f"${total_capex:,.2f}",
            delta=f"{(100 - porcentaje_opex):.1f}% del total"
        )
    
    with col3:
        st.metric(
            label="📊 Total General",
            value=f"${total_general:,.2f}"
        )
    
    with col4:
        st.metric(
            label="📈 Ratio OPEX/CAPEX",
            value=f"{porcentaje_opex:.1f}% / {(100 - porcentaje_opex):.1f}%"
        )
    
    return total_opex, total_capex, total_general

def grafico_distribucion_tipo(df):
    """
    Gráfico de distribución OPEX vs CAPEX
    """
    data = df.groupby('TIPO')['MONTO_EN_USD'].sum().reset_index()
    
    fig = px.pie(
        data,
        values='MONTO_EN_USD',
        names='TIPO',
        title='Distribución OPEX vs CAPEX',
        color_discrete_map={'OPEX': '#2E86AB', 'CAPEX': '#E67E22'},
        hole=0.4
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='%{label}: $%{value:,.2f}<br>%{percent}'
    )
    
    fig.update_layout(
        showlegend=False,
        height=350,
        margin=dict(t=40, b=0, l=0, r=0)
    )
    
    return fig

def grafico_top_categorias(df, tipo=None, n=10):
    """
    Gráfico de Top N categorías de gasto
    """
    df_filtrado = df if tipo is None else df[df['TIPO'] == tipo]
    
    data = df_filtrado.groupby('CATEGORIA_LIMPIA')['MONTO_EN_USD'].sum().reset_index()
    data = data.sort_values('MONTO_EN_USD', ascending=True).tail(n)
    
    colors = ['#2E86AB' if 'OPEX' in cat else '#E67E22' if 'CAPEX' in cat else '#95A5A6' 
              for cat in data['CATEGORIA_LIMPIA']]
    
    fig = px.bar(
        data,
        x='MONTO_EN_USD',
        y='CATEGORIA_LIMPIA',
        orientation='h',
        title=f'Top {n} Categorías de Gasto',
        color_discrete_sequence=colors,
        labels={'MONTO_EN_USD': 'Monto (USD)', 'CATEGORIA_LIMPIA': 'Categoría'}
    )
    
    fig.update_traces(
        texttemplate='$%{x:,.0f}',
        textposition='outside',
        hovertemplate='%{y}<br>$%{x:,.2f}<extra></extra>'
    )
    
    fig.update_layout(
        height=400,
        margin=dict(t=40, b=0, l=150, r=50),
        xaxis_title='Monto (USD)',
        yaxis_title=''
    )
    
    return fig

def grafico_barras_apiladas(df):
    """
    Gráfico de barras apiladas por categoría (OPEX vs CAPEX)
    """
    data = df.groupby(['CATEGORIA_LIMPIA', 'TIPO'])['MONTO_EN_USD'].sum().reset_index()
    data = data[data['TIPO'] != 'OTROS']
    
    # Ordenar por total descendente
    totals = data.groupby('CATEGORIA_LIMPIA')['MONTO_EN_USD'].sum().reset_index()
    totals = totals.sort_values('MONTO_EN_USD', ascending=False)
    top_categories = totals['CATEGORIA_LIMPIA'].head(15).tolist()
    
    data_filtrado = data[data['CATEGORIA_LIMPIA'].isin(top_categories)]
    
    fig = px.bar(
        data_filtrado,
        x='CATEGORIA_LIMPIA',
        y='MONTO_EN_USD',
        color='TIPO',
        title='Gasto por Categoría - OPEX vs CAPEX',
        color_discrete_map={'OPEX': '#2E86AB', 'CAPEX': '#E67E22'},
        barmode='stack',
        labels={'MONTO_EN_USD': 'Monto (USD)', 'CATEGORIA_LIMPIA': 'Categoría'}
    )
    
    fig.update_layout(
        height=400,
        margin=dict(t=40, b=0, l=0, r=0),
        xaxis_tickangle=-45,
        legend_title='Tipo',
        hovermode='x unified'
    )
    
    fig.update_traces(
        hovertemplate='%{x}<br>%{data.name}: $%{y:,.2f}<extra></extra>'
    )
    
    return fig

def grafico_cascada_direccion(df):
    """
    Gráfico de cascada por Dirección (Nivel 1)
    """
    data = df.groupby('DIRECCION')['MONTO_EN_USD'].sum().reset_index()
    data = data[data['DIRECCION'].notna()]
    data = data[data['DIRECCION'] != '']
    data = data.sort_values('MONTO_EN_USD', ascending=False)
    
    fig = px.bar(
        data,
        x='DIRECCION',
        y='MONTO_EN_USD',
        title='Gasto por Dirección',
        color='MONTO_EN_USD',
        color_continuous_scale='Blues',
        labels={'MONTO_EN_USD': 'Monto (USD)', 'DIRECCION': 'Dirección'}
    )
    
    fig.update_traces(
        texttemplate='$%{y:,.0f}',
        textposition='outside',
        hovertemplate='%{x}<br>$%{y:,.2f}<extra></extra>'
    )
    
    fig.update_layout(
        height=350,
        margin=dict(t=40, b=0, l=0, r=0),
        coloraxis_showscale=False,
        xaxis_tickangle=-30
    )
    
    return fig

def grafico_detalle_gerencia(df, direccion_seleccionada):
    """
    Gráfico de detalle por Gerencia para una Dirección específica
    """
    if not direccion_seleccionada:
        return None
    
    data = df[df['DIRECCION'] == direccion_seleccionada]
    data = data.groupby('GERENCIA')['MONTO_EN_USD'].sum().reset_index()
    data = data[data['GERENCIA'].notna()]
    data = data[data['GERENCIA'] != '']
    data = data.sort_values('MONTO_EN_USD', ascending=False)
    
    if len(data) == 0:
        return None
    
    fig = px.bar(
        data,
        x='GERENCIA',
        y='MONTO_EN_USD',
        title=f'Gasto por Gerencia - {direccion_seleccionada}',
        color='MONTO_EN_USD',
        color_continuous_scale='Oranges',
        labels={'MONTO_EN_USD': 'Monto (USD)', 'GERENCIA': 'Gerencia'}
    )
    
    fig.update_traces(
        texttemplate='$%{y:,.0f}',
        textposition='outside',
        hovertemplate='%{x}<br>$%{y:,.2f}<extra></extra>'
    )
    
    fig.update_layout(
        height=300,
        margin=dict(t=40, b=0, l=0, r=0),
        coloraxis_showscale=False,
        xaxis_tickangle=-30
    )
    
    return fig

def tabla_detalle_dinamica(df, filtros):
    """
    Tabla dinámica de detalle con filtros
    """
    df_filtrado = df.copy()
    
    # Aplicar filtros
    if filtros.get('tipo') and filtros['tipo'] != 'TODOS':
        df_filtrado = df_filtrado[df_filtrado['TIPO'] == filtros['tipo']]
    
    if filtros.get('direccion'):
        df_filtrado = df_filtrado[df_filtrado['DIRECCION'] == filtros['direccion']]
    
    if filtros.get('categoria'):
        df_filtrado = df_filtrado[df_filtrado['CATEGORIA_LIMPIA'] == filtros['categoria']]
    
    if filtros.get('busqueda'):
        busqueda = filtros['busqueda'].lower()
        df_filtrado = df_filtrado[
            df_filtrado['DETALLE DE LA PARTIDA'].str.lower().str.contains(busqueda, na=False) |
            df_filtrado['CATEGORIA_LIMPIA'].str.lower().str.contains(busqueda, na=False) |
            df_filtrado['NRO PDC'].str.lower().str.contains(busqueda, na=False)
        ]
    
    # Seleccionar columnas para mostrar
    columnas_mostrar = [
        'CATEGORIA_LIMPIA',
        'DETALLE DE LA PARTIDA',
        'DIRECCION',
        'GERENCIA',
        'MONEDA DE PAGO',
        'MONTO PLAN USD',
        'MONTO_EN_USD',
        'NRO PDC',
        'NRO SOLICITUD en ODOO'
    ]
    
    df_mostrar = df_filtrado[columnas_mostrar].copy()
    df_mostrar = df_mostrar[df_mostrar['MONTO_EN_USD'] > 0]
    df_mostrar = df_mostrar.sort_values('MONTO_EN_USD', ascending=False)
    
    # Formatear columnas numéricas
    df_mostrar['MONTO PLAN USD'] = df_mostrar['MONTO PLAN USD'].apply(lambda x: f"{x:,.2f}")
    df_mostrar['MONTO_EN_USD'] = df_mostrar['MONTO_EN_USD'].apply(lambda x: f"${x:,.2f}")
    
    # Renombrar columnas
    df_mostrar.columns = [
        'Categoría',
        'Detalle',
        'Dirección',
        'Gerencia',
        'Moneda Pago',
        'Monto Origen',
        'Monto USD',
        'NRO PDC',
        'NRO Solicitud'
    ]
    
    return df_mostrar

def sistema_alertas(df):
    """
    Sistema de alertas (COSO/ISO Flexible)
    """
    alertas = []
    
    # 1. Alertas por categoría (> 15% del total)
    total_general = df['MONTO_EN_USD'].sum()
    data_cat = df.groupby('CATEGORIA_LIMPIA')['MONTO_EN_USD'].sum().reset_index()
    data_cat['porcentaje'] = (data_cat['MONTO_EN_USD'] / total_general * 100)
    
    for _, row in data_cat.iterrows():
        if row['porcentaje'] > 15:
            alertas.append({
                'tipo': 'danger',
                'mensaje': f"🔴 {row['CATEGORIA_LIMPIA']}: {row['porcentaje']:.1f}% del total (>{'15%'})",
                'categoria': row['CATEGORIA_LIMPIA']
            })
        elif row['porcentaje'] > 8:
            alertas.append({
                'tipo': 'warning',
                'mensaje': f"🟡 {row['CATEGORIA_LIMPIA']}: {row['porcentaje']:.1f}% del total (>8%)",
                'categoria': row['CATEGORIA_LIMPIA']
            })
    
    # 2. Alertas por moneda (riesgo cambiario)
    data_moneda = df[df['MONEDA DE PAGO'].isin(['BS', 'BS/USD'])].groupby('MONEDA DE PAGO')['MONTO_EN_USD'].sum().reset_index()
    
    for _, row in data_moneda.iterrows():
        if row['MONTO_EN_USD'] > 100000:
            alertas.append({
                'tipo': 'warning',
                'mensaje': f"⚠️ {row['MONTO_EN_USD']:,.2f} USD en {row['MONEDA DE PAGO']} - Riesgo cambiario",
                'categoria': 'Moneda'
            })
    
    return alertas

def mostrar_alertas(alertas):
    """
    Muestra las alertas en el dashboard
    """
    if not alertas:
        st.markdown("""
        <div class="alert-box alert-success">
            ✅ Todas las partidas están dentro de los parámetros establecidos
        </div>
        """, unsafe_allow_html=True)
        return
    
    for alerta in alertas[:5]:  # Mostrar máximo 5 alertas
        clase = f"alert-{alerta['tipo']}"
        st.markdown(f"""
        <div class="alert-box {clase}">
            {alerta['mensaje']}
        </div>
        """, unsafe_allow_html=True)
    
    if len(alertas) > 5:
        st.info(f"📌 {len(alertas) - 5} alertas adicionales no mostradas")

# ============================================
# 3. CONFIGURACIÓN DE FILTROS
# ============================================

def configurar_filtros(df):
    """
    Configura los filtros del dashboard
    """
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.markdown("### 🎯 Filtros")
        
        # Filtro de tipo
        tipos = ['TODOS', 'OPEX', 'CAPEX']
        tipo_seleccionado = st.selectbox(
            'Tipo de Partida',
            tipos,
            index=0,
            help='Selecciona OPEX, CAPEX o TODOS'
        )
        
        # Filtro de Dirección
        direcciones = ['TODAS'] + sorted(df['DIRECCION'].dropna().unique().tolist())
        direccion_seleccionada = st.selectbox(
            'Dirección',
            direcciones,
            index=0,
            help='Filtra por dirección específica'
        )
        
        # Filtro de Categoría
        categorias = ['TODAS'] + sorted(df['CATEGORIA_LIMPIA'].dropna().unique().tolist())
        categoria_seleccionada = st.selectbox(
            'Categoría',
            categorias,
            index=0,
            help='Filtra por categoría específica'
        )
        
        # Búsqueda
        busqueda = st.text_input(
            '🔍 Buscar',
            placeholder='NRO PDC, Detalle, Categoría...',
            help='Busca por NRO PDC, detalle o categoría'
        )
        
        st.divider()
        
        # Configuración de Tasa de Cambio
        st.markdown("### 💱 Configuración")
        tasa_bcv = st.number_input(
            'Tasa BCV (USD/BS)',
            min_value=1.0,
            max_value=1000.0,
            value=40.0,
            step=0.5,
            help='Tasa de cambio para convertir BS a USD'
        )
        
        st.caption("💡 Actualiza la tasa de cambio para recalcular todos los montos")
        
        return {
            'tipo': tipo_seleccionado,
            'direccion': direccion_seleccionada,
            'categoria': categoria_seleccionada,
            'busqueda': busqueda,
            'tasa_bcv': tasa_bcv
        }

# ============================================
# 4. FUNCIÓN PRINCIPAL DEL DASHBOARD
# ============================================

def main():
    st.markdown('<p class="main-header">📊 Proyección de Pagos - Agosto 2026</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Dashboard interactivo para análisis de gastos OPEX y CAPEX</p>', unsafe_allow_html=True)
    
    # Carga de archivo
    uploaded_file = st.file_uploader(
        "📤 Cargar archivo Excel con la proyección",
        type=['xlsx', 'xls'],
        help="Sube el archivo Excel con la estructura de la plantilla"
    )
    
    if uploaded_file is not None:
        # Configurar filtros
        filtros = configurar_filtros(pd.DataFrame())  # Placeholder
        
        # Cargar y procesar datos
        with st.spinner('⏳ Procesando datos...'):
            df = load_and_process_data(uploaded_file, filtros.get('tasa_bcv', 40.0))
        
        if df.empty:
            st.warning("⚠️ No se encontraron datos en el archivo. Verifica el formato.")
            return
        
        # Actualizar filtros con los datos cargados
        filtros = configurar_filtros(df)
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if filtros['tipo'] != 'TODOS':
            df_filtrado = df_filtrado[df_filtrado['TIPO'] == filtros['tipo']]
        
        if filtros['direccion'] != 'TODAS':
            df_filtrado = df_filtrado[df_filtrado['DIRECCION'] == filtros['direccion']]
        
        if filtros['categoria'] != 'TODAS':
            df_filtrado = df_filtrado[df_filtrado['CATEGORIA_LIMPIA'] == filtros['categoria']]
        
        if filtros['busqueda']:
            busqueda = filtros['busqueda'].lower()
            df_filtrado = df_filtrado[
                df_filtrado['DETALLE DE LA PARTIDA'].str.lower().str.contains(busqueda, na=False) |
                df_filtrado['CATEGORIA_LIMPIA'].str.lower().str.contains(busqueda, na=False) |
                df_filtrado['NRO PDC'].str.lower().str.contains(busqueda, na=False)
            ]
        
        if df_filtrado.empty:
            st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados")
            return
        
        # ============================================
        # KPI's GLOBALES
        # ============================================
        total_opex, total_capex, total_general = crear_kpi_globales(df_filtrado)
        
        st.divider()
        
        # ============================================
        # FILA 1: Distribución y Top Categorías
        # ============================================
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            fig1 = grafico_distribucion_tipo(df_filtrado)
            st.plotly_chart(fig1, use_container_width=True, key="distribucion")
        
        with col2:
            fig2 = grafico_top_categorias(df_filtrado, filtros['tipo'] if filtros['tipo'] != 'TODOS' else None)
            st.plotly_chart(fig2, use_container_width=True, key="top_categorias")
        
        # ============================================
        # FILA 2: Barras Apiladas
        # ============================================
        st.subheader("📊 Análisis Detallado por Categoría")
        fig3 = grafico_barras_apiladas(df_filtrado)
        st.plotly_chart(fig3, use_container_width=True, key="barras_apiladas")
        
        # ============================================
        # FILA 3: Análisis por Unidad Organizacional
        # ============================================
        st.subheader("🏢 Análisis por Unidad Organizacional")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig4 = grafico_cascada_direccion(df_filtrado)
            st.plotly_chart(fig4, use_container_width=True, key="cascada_direccion")
        
        with col2:
            # Obtener dirección seleccionada (la más grande por defecto)
            direcciones = df_filtrado.groupby('DIRECCION')['MONTO_EN_USD'].sum().reset_index()
            direcciones = direcciones[direcciones['DIRECCION'].notna()]
            direcciones = direcciones[direcciones['DIRECCION'] != '']
            if not direcciones.empty:
                top_direccion = direcciones.sort_values('MONTO_EN_USD', ascending=False).iloc[0]['DIRECCION']
                fig5 = grafico_detalle_gerencia(df_filtrado, top_direccion)
                if fig5:
                    st.plotly_chart(fig5, use_container_width=True, key="detalle_gerencia")
                else:
                    st.info("No hay datos de gerencia para esta dirección")
            else:
                st.info("No hay direcciones disponibles")
        
        # ============================================
        # FILA 4: Tabla Dinámica de Detalle
        # ============================================
        st.subheader("📋 Detalle de Partidas")
        
        # Opciones de la tabla
        col1, col2 = st.columns([3, 1])
        with col2:
            mostrar_detalle = st.checkbox("Mostrar todas las columnas", value=False)
        
        # Preparar filtros para la tabla
        filtros_tabla = {
            'tipo': filtros['tipo'],
            'direccion': filtros['direccion'] if filtros['direccion'] != 'TODAS' else None,
            'categoria': filtros['categoria'] if filtros['categoria'] != 'TODAS' else None,
            'busqueda': filtros['busqueda'] if filtros['busqueda'] else None
        }
        
        df_tabla = tabla_detalle_dinamica(df_filtrado, filtros_tabla)
        
        if not df_tabla.empty:
            # Mostrar estadísticas
            st.caption(f"📌 {len(df_tabla)} partidas encontradas | Total: ${df_filtrado['MONTO_EN_USD'].sum():,.2f}")
            
            # Formato condicional para la tabla
            def highlight_monto(val):
                try:
                    val_num = float(val.replace('$', '').replace(',', ''))
                    if val_num > 10000:
                        return 'background-color: #f8d7da'
                    elif val_num > 5000:
                        return 'background-color: #fff3cd'
                    return ''
                except:
                    return ''
            
            # Mostrar tabla con estilo
            st.dataframe(
                df_tabla,
                use_container_width=True,
                height=400,
                column_config={
                    "Monto USD": st.column_config.NumberColumn(
                        "Monto USD",
                        format="$%.2f"
                    ),
                    "Monto Origen": st.column_config.NumberColumn(
                        "Monto Origen",
                        format="%.2f"
                    )
                }
            )
        else:
            st.info("No hay partidas que coincidan con los filtros seleccionados")
        
        # ============================================
        # FILA 5: Alertas y Monitoreo
        # ============================================
        st.subheader("🚨 Alertas y Monitoreo (COSO/ISO)")
        
        alertas = sistema_alertas(df_filtrado)
        mostrar_alertas(alertas)
        
        # ============================================
        # FILA 6: Resumen de Datos
        # ============================================
        with st.expander("📊 Resumen Estadístico"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Total de Partidas",
                    f"{len(df_filtrado):,}"
                )
            
            with col2:
                categorias_unicas = df_filtrado['CATEGORIA_LIMPIA'].nunique()
                st.metric(
                    "Categorías Únicas",
                    f"{categorias_unicas}"
                )
            
            with col3:
                monedas = df_filtrado['MONEDA DE PAGO'].unique().tolist()
                st.metric(
                    "Monedas de Pago",
                    ", ".join([str(m) for m in monedas if pd.notna(m)])
                )
            
            # Tabla resumen por tipo
            st.markdown("#### Resumen por Tipo de Partida")
            resumen_tipo = df_filtrado.groupby('TIPO').agg({
                'MONTO_EN_USD': ['sum', 'count', 'mean']
            }).round(2)
            resumen_tipo.columns = ['Total USD', 'Cantidad', 'Promedio USD']
            resumen_tipo['Total USD'] = resumen_tipo['Total USD'].apply(lambda x: f"${x:,.2f}")
            resumen_tipo['Promedio USD'] = resumen_tipo['Promedio USD'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(resumen_tipo, use_container_width=True)
            
            # Descargar datos filtrados
            csv = df_filtrado.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="datos_filtrados.csv">📥 Descargar datos filtrados (CSV)</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    else:
        # Mensaje cuando no hay archivo cargado
        st.info("📤 Por favor, carga un archivo Excel para comenzar el análisis")
        
        # Mostrar ejemplo de estructura
        st.markdown("""
        ### 📋 Estructura del Archivo Requerida
        
        El archivo debe tener las siguientes columnas:
        - **CATEGORIA DE LA PARTIDA**: Categoría del gasto (ej. "3. OPEX - INSTALACIONES")
        - **DETALLE DE LA PARTIDA**: Descripción detallada del gasto
        - **MONTO PLAN USD**: Monto en la moneda de pago
        - **MONEDA DE PAGO**: USD, BS/USD, BS, COP
        - **DIRECCION**: COO, CFO, CTO, STAFF PRESIDENCIA
        - **GERENCIA**: Unidad organizacional
        - **NRO PDC**: Número de orden de compra
        - **NRO SOLICITUD en ODOO**: Número de solicitud
        """)

# ============================================
# 5. EJECUCIÓN DEL DASHBOARD
# ============================================

if __name__ == "__main__":
    main()