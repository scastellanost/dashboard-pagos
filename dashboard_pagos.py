import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import base64

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Proyección de Pagos - Agosto 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1E3D59; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #6B7B8D; margin-bottom: 2rem; }
    .alert-box { padding: 1rem; border-radius: 8px; margin: 0.5rem 0; }
    .alert-success { background-color: #d4edda; border-left: 4px solid #28a745; }
    .alert-warning { background-color: #fff3cd; border-left: 4px solid #ffc107; }
    .alert-danger { background-color: #f8d7da; border-left: 4px solid #dc3545; }
</style>
""", unsafe_allow_html=True)

# ============================================
# MAPEO DE COLUMNAS (CORREGIDO)
# ============================================

COLUMNAS_MAPEO = {
    'DIRECCION EJECUTIVA (CHIEF)': 'DIRECCION_EJECUTIVA',
    'DIRECCION': 'DIRECCION',
    'GERENCIA': 'GERENCIA',
    'EMPRESA': 'EMPRESA',
    'NRO SOLICITUD en ODOO': 'NRO_SOLICITUD',
    'NRO PDC': 'NRO_PDC',
    'TIPO DE PARTIDA': 'TIPO_PARTIDA',
    'NOMBRE DEL PROYECTO (solo para CAPEX)': 'PROYECTO',
    'CATEGORIA DE LA PARTIDA': 'CATEGORIA',
    'DETALLE DE LA PARTIDA': 'DETALLE',
    'INFORMACION DEL GASTO': 'INFORMACION',
    'MONTO PLAN USD': 'MONTO',
    'MONEDA DE PAGO': 'MONEDA',
    'FORMA DE PAGO': 'FORMA_PAGO',
    'OBSERVACION': 'OBSERVACION',
}

# ============================================
# FUNCIONES DE PROCESAMIENTO
# ============================================

def cargar_y_procesar_datos(file, tasa_bcv=40.0):
    """Carga y procesa el archivo Excel"""
    try:
        # Cargar archivo
        df = pd.read_excel(file, sheet_name='Plantilla', header=0)
        
        # Limpiar nombres de columnas (eliminar espacios extra)
        df.columns = df.columns.str.strip()
        
        # Renombrar columnas usando el mapeo
        columnas_renombrar = {}
        for col_original, col_nueva in COLUMNAS_MAPEO.items():
            if col_original in df.columns:
                columnas_renombrar[col_original] = col_nueva
        
        df = df.rename(columns=columnas_renombrar)
        
        # Verificar columnas críticas
        columnas_requeridas = ['CATEGORIA', 'MONTO']
        for col in columnas_requeridas:
            if col not in df.columns:
                # Buscar columnas similares
                columnas_posibles = [c for c in df.columns if 'MONTO' in c.upper() or 'CATEGORIA' in c.upper()]
                st.warning(f"⚠️ No se encontró la columna '{col}'. Columnas disponibles similares: {columnas_posibles}")
                return pd.DataFrame()
        
        # Limpiar datos
        df = df.dropna(subset=['CATEGORIA'], how='all')
        df = df[df['CATEGORIA'].notna()]
        
        # Convertir montos a numérico
        df['MONTO'] = pd.to_numeric(df['MONTO'], errors='coerce').fillna(0)
        
        # Calcular MONTO_EN_USD según la moneda
        def calcular_monto_usd(row):
            monto = row['MONTO']
            moneda = str(row['MONEDA']).strip().upper() if pd.notna(row['MONEDA']) else 'USD'
            
            if pd.isna(monto) or monto == 0:
                return 0.0
            
            if moneda == 'USD':
                return float(monto)
            elif moneda in ['BS/USD', 'BS', 'BS.']:
                return float(monto) / tasa_bcv if tasa_bcv > 0 else 0
            elif moneda == 'COP':
                return float(monto) / 4000.0
            else:
                return float(monto)
        
        df['MONTO_EN_USD'] = df.apply(calcular_monto_usd, axis=1)
        
        # Limpiar categorías
        df['CATEGORIA_LIMPIA'] = df['CATEGORIA'].str.replace(r'^\d+\.\s*', '', regex=True)
        
        # Extraer TIPO (OPEX/CAPEX)
        df['TIPO'] = df['CATEGORIA_LIMPIA'].apply(
            lambda x: 'OPEX' if 'OPEX' in str(x).upper() else ('CAPEX' if 'CAPEX' in str(x).upper() else 'OTROS')
        )
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error al procesar: {str(e)}")
        st.info("💡 Asegúrate de que el archivo sea el correcto")
        return pd.DataFrame()

# ============================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================

def crear_kpi_globales(df):
    """Crea las tarjetas KPI"""
    total_opex = df[df['TIPO'] == 'OPEX']['MONTO_EN_USD'].sum()
    total_capex = df[df['TIPO'] == 'CAPEX']['MONTO_EN_USD'].sum()
    total_general = total_opex + total_capex
    porcentaje_opex = (total_opex / total_general * 100) if total_general > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Total OPEX", f"${total_opex:,.2f}", f"{porcentaje_opex:.1f}%")
    with col2:
        st.metric("🏗️ Total CAPEX", f"${total_capex:,.2f}", f"{(100 - porcentaje_opex):.1f}%")
    with col3:
        st.metric("📊 Total General", f"${total_general:,.2f}")
    with col4:
        st.metric("📈 OPEX/CAPEX", f"{porcentaje_opex:.0f}% / {(100 - porcentaje_opex):.0f}%")
    
    return total_opex, total_capex, total_general

def grafico_distribucion_tipo(df):
    """Gráfico de distribución OPEX vs CAPEX"""
    data = df.groupby('TIPO')['MONTO_EN_USD'].sum().reset_index()
    data = data[data['TIPO'] != 'OTROS']
    
    fig = px.pie(
        data, values='MONTO_EN_USD', names='TIPO',
        title='Distribución OPEX vs CAPEX',
        color_discrete_map={'OPEX': '#2E86AB', 'CAPEX': '#E67E22'},
        hole=0.4
    )
    fig.update_layout(height=350, margin=dict(t=40, b=0, l=0, r=0))
    return fig

def grafico_top_categorias(df, n=10):
    """Gráfico de Top N categorías"""
    data = df.groupby('CATEGORIA_LIMPIA')['MONTO_EN_USD'].sum().reset_index()
    data = data.sort_values('MONTO_EN_USD', ascending=True).tail(n)
    
    fig = px.bar(
        data, x='MONTO_EN_USD', y='CATEGORIA_LIMPIA', orientation='h',
        title=f'Top {n} Categorías de Gasto',
        color='MONTO_EN_USD', color_continuous_scale='Blues'
    )
    fig.update_layout(height=400, margin=dict(t=40, b=0, l=150, r=50))
    return fig

def grafico_barras_apiladas(df):
    """Gráfico de barras apiladas OPEX vs CAPEX por categoría"""
    data = df.groupby(['CATEGORIA_LIMPIA', 'TIPO'])['MONTO_EN_USD'].sum().reset_index()
    data = data[data['TIPO'] != 'OTROS']
    
    totals = data.groupby('CATEGORIA_LIMPIA')['MONTO_EN_USD'].sum().reset_index()
    top_cats = totals.sort_values('MONTO_EN_USD', ascending=False).head(10)['CATEGORIA_LIMPIA'].tolist()
    data = data[data['CATEGORIA_LIMPIA'].isin(top_cats)]
    
    fig = px.bar(
        data, x='CATEGORIA_LIMPIA', y='MONTO_EN_USD', color='TIPO',
        title='Gasto por Categoría - OPEX vs CAPEX',
        color_discrete_map={'OPEX': '#2E86AB', 'CAPEX': '#E67E22'},
        barmode='stack'
    )
    fig.update_layout(height=400, margin=dict(t=40, b=0, l=0, r=0), xaxis_tickangle=-45)
    return fig

def grafico_cascada_direccion(df):
    """Gráfico de cascada por Dirección"""
    data = df.groupby('DIRECCION')['MONTO_EN_USD'].sum().reset_index()
    data = data[data['DIRECCION'].notna() & (data['DIRECCION'] != '')]
    data = data.sort_values('MONTO_EN_USD', ascending=False)
    
    fig = px.bar(
        data, x='DIRECCION', y='MONTO_EN_USD',
        title='Gasto por Dirección',
        color='MONTO_EN_USD', color_continuous_scale='Blues'
    )
    fig.update_layout(height=350, margin=dict(t=40, b=0, l=0, r=0), coloraxis_showscale=False)
    return fig

def grafico_detalle_gerencia(df, direccion):
    """Gráfico de detalle por Gerencia"""
    if not direccion or direccion == 'TODAS':
        return None
    
    data = df[df['DIRECCION'] == direccion]
    data = data.groupby('GERENCIA')['MONTO_EN_USD'].sum().reset_index()
    data = data[data['GERENCIA'].notna() & (data['GERENCIA'] != '')]
    data = data.sort_values('MONTO_EN_USD', ascending=False)
    
    if len(data) == 0:
        return None
    
    fig = px.bar(
        data, x='GERENCIA', y='MONTO_EN_USD',
        title=f'Gasto por Gerencia - {direccion}',
        color='MONTO_EN_USD', color_continuous_scale='Oranges'
    )
    fig.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0), coloraxis_showscale=False)
    return fig

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    st.markdown('<p class="main-header">📊 Proyección de Pagos - Agosto 2026</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Dashboard interactivo para análisis de gastos OPEX y CAPEX</p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "📤 Cargar archivo Excel con la proyección",
        type=['xlsx', 'xls']
    )
    
    if uploaded_file is not None:
        # Sidebar con filtros (se cargan después de procesar)
        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
            st.markdown("### 🎯 Filtros")
            tasa_bcv = st.number_input('💱 Tasa BCV (USD/BS)', min_value=1.0, value=40.0, step=0.5)
        
        # Procesar datos
        with st.spinner('⏳ Procesando datos...'):
            df = cargar_y_procesar_datos(uploaded_file, tasa_bcv)
        
        if df.empty:
            st.warning("⚠️ No se encontraron datos en el archivo")
            return
        
        # Sidebar: filtros después de cargar datos
        with st.sidebar:
            tipo = st.selectbox('Tipo de Partida', ['TODOS', 'OPEX', 'CAPEX'])
            direcciones = ['TODAS'] + sorted(df['DIRECCION'].dropna().unique().tolist())
            direccion = st.selectbox('Dirección', direcciones)
            categorias = ['TODAS'] + sorted(df['CATEGORIA_LIMPIA'].dropna().unique().tolist())
            categoria = st.selectbox('Categoría', categorias)
            busqueda = st.text_input('🔍 Buscar', placeholder='NRO PDC, Detalle...')
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if tipo != 'TODOS':
            df_filtrado = df_filtrado[df_filtrado['TIPO'] == tipo]
        if direccion != 'TODAS':
            df_filtrado = df_filtrado[df_filtrado['DIRECCION'] == direccion]
        if categoria != 'TODAS':
            df_filtrado = df_filtrado[df_filtrado['CATEGORIA_LIMPIA'] == categoria]
        if busqueda:
            busqueda_lower = busqueda.lower()
            df_filtrado = df_filtrado[
                df_filtrado['DETALLE'].str.lower().str.contains(busqueda_lower, na=False) |
                df_filtrado['CATEGORIA_LIMPIA'].str.lower().str.contains(busqueda_lower, na=False) |
                df_filtrado['NRO_PDC'].str.lower().str.contains(busqueda_lower, na=False)
            ]
        
        if df_filtrado.empty:
            st.warning("⚠️ No hay datos que coincidan con los filtros")
            return
        
        # KPI's
        crear_kpi_globales(df_filtrado)
        
        st.divider()
        
        # FILA 1: Distribución y Top Categorías
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(grafico_distribucion_tipo(df_filtrado), use_container_width=True)
        with col2:
            st.plotly_chart(grafico_top_categorias(df_filtrado), use_container_width=True)
        
        # FILA 2: Barras Apiladas
        st.subheader("📊 Análisis Detallado por Categoría")
        st.plotly_chart(grafico_barras_apiladas(df_filtrado), use_container_width=True)
        
        # FILA 3: Análisis por Unidad
        st.subheader("🏢 Análisis por Unidad Organizacional")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(grafico_cascada_direccion(df_filtrado), use_container_width=True)
        with col2:
            top_dir = df_filtrado.groupby('DIRECCION')['MONTO_EN_USD'].sum().reset_index()
            top_dir = top_dir[top_dir['DIRECCION'].notna() & (top_dir['DIRECCION'] != '')]
            if not top_dir.empty:
                fig = grafico_detalle_gerencia(df_filtrado, top_dir.iloc[0]['DIRECCION'])
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
        
        # FILA 4: Tabla de Detalle
        st.subheader("📋 Detalle de Partidas")
        
        columnas_mostrar = [
            'CATEGORIA_LIMPIA', 'DETALLE', 'DIRECCION', 'GERENCIA',
            'MONEDA', 'MONTO', 'MONTO_EN_USD', 'NRO_PDC'
        ]
        # Filtrar columnas que existen
        columnas_existentes = [col for col in columnas_mostrar if col in df_filtrado.columns]
        df_tabla = df_filtrado[columnas_existentes].copy()
        df_tabla = df_tabla[df_tabla['MONTO_EN_USD'] > 0]
        df_tabla = df_tabla.sort_values('MONTO_EN_USD', ascending=False)
        df_tabla['MONTO_EN_USD'] = df_tabla['MONTO_EN_USD'].apply(lambda x: f"${x:,.2f}")
        df_tabla['MONTO'] = df_tabla['MONTO'].apply(lambda x: f"{x:,.2f}")
        
        st.caption(f"📌 {len(df_tabla)} partidas encontradas")
        st.dataframe(df_tabla, use_container_width=True, height=400)
        
        # Descarga CSV
        csv = df_filtrado.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        st.markdown(f'<a href="data:file/csv;base64,{b64}" download="datos_filtrados.csv">📥 Descargar datos filtrados (CSV)</a>', unsafe_allow_html=True)
    
    else:
        st.info("📤 Por favor, carga un archivo Excel para comenzar el análisis")

if __name__ == "__main__":
    main()
