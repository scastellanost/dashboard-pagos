import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import base64

st.set_page_config(
    page_title="Dashboard Proyección de Pagos - Agosto 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# FUNCIÓN PRINCIPAL MEJORADA
# ============================================

def main():
    st.markdown('<h1 style="color:#1E3D59;">📊 Proyección de Pagos - Agosto 2026</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#6B7B8D;font-size:1.2rem;">Dashboard interactivo para análisis de gastos OPEX y CAPEX</p>', unsafe_allow_html=True)
    
    # Carga de archivo
    uploaded_file = st.file_uploader(
        "📤 Cargar archivo Excel con la proyección",
        type=['xlsx', 'xls'],
        help="Sube el archivo Excel con la estructura de la plantilla"
    )
    
    if uploaded_file is not None:
        try:
            # Cargar el archivo
            df = pd.read_excel(uploaded_file, sheet_name='Plantilla', header=0)
            
            # Limpiar nombres de columnas
            df.columns = df.columns.str.strip()
            
            # Debug: mostrar columnas
            st.info(f"📋 Columnas encontradas: {', '.join(df.columns.tolist())}")
            
            # Verificar si hay datos
            if df.empty:
                st.warning("⚠️ El archivo está vacío")
                return
            
            # Limpiar datos básicos
            df = df.dropna(subset=['CATEGORIA DE LA PARTIDA'], how='all')
            df = df[df['CATEGORIA DE LA PARTIDA'].notna()]
            
            # Convertir montos
            df['MONTO PLAN USD'] = pd.to_numeric(df['MONTO PLAN USD'], errors='coerce').fillna(0)
            
            # Calcular MONTO_EN_USD
            def calcular_monto_usd(row):
                monto = row['MONTO PLAN USD']
                moneda = str(row['MONEDA DE PAGO']).strip().upper() if pd.notna(row['MONEDA DE PAGO']) else 'USD'
                
                if pd.isna(monto) or monto == 0:
                    return 0.0
                
                if moneda == 'USD':
                    return float(monto)
                elif moneda in ['BS/USD', 'BS', 'BS.']:
                    return float(monto) / 40.0  # Tasa default
                else:
                    return float(monto)
            
            df['MONTO_EN_USD'] = df.apply(calcular_monto_usd, axis=1)
            
            # Crear categoría limpia
            df['CATEGORIA_LIMPIA'] = df['CATEGORIA DE LA PARTIDA'].str.replace(r'^\d+\.\s*', '', regex=True)
            
            # Extraer TIPO
            df['TIPO'] = df['CATEGORIA_LIMPIA'].apply(
                lambda x: 'OPEX' if 'OPEX' in str(x).upper() else ('CAPEX' if 'CAPEX' in str(x).upper() else 'OTROS')
            )
            
            # Filtros en sidebar
            with st.sidebar:
                st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
                st.markdown("### 🎯 Filtros")
                
                tipo = st.selectbox('Tipo de Partida', ['TODOS', 'OPEX', 'CAPEX'])
                
                # Direcciones
                direcciones = ['TODAS'] + sorted(df['DIRECCION'].dropna().unique().tolist()) if 'DIRECCION' in df.columns else ['TODAS']
                direccion = st.selectbox('Dirección', direcciones)
                
                # Categorías
                categorias = ['TODAS'] + sorted(df['CATEGORIA_LIMPIA'].dropna().unique().tolist())
                categoria = st.selectbox('Categoría', categorias)
                
                busqueda = st.text_input('🔍 Buscar', placeholder='NRO PDC, Detalle...')
                
                st.divider()
                st.markdown("### 💱 Configuración")
                tasa_bcv = st.number_input('Tasa BCV (USD/BS)', min_value=1.0, value=40.0, step=0.5)
            
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
                    df_filtrado['DETALLE DE LA PARTIDA'].str.lower().str.contains(busqueda_lower, na=False) |
                    df_filtrado['CATEGORIA_LIMPIA'].str.lower().str.contains(busqueda_lower, na=False) |
                    df_filtrado['NRO PDC'].str.lower().str.contains(busqueda_lower, na=False)
                ]
            
            # KPI's
            total_opex = df_filtrado[df_filtrado['TIPO'] == 'OPEX']['MONTO_EN_USD'].sum()
            total_capex = df_filtrado[df_filtrado['TIPO'] == 'CAPEX']['MONTO_EN_USD'].sum()
            total_general = total_opex + total_capex
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Total OPEX", f"${total_opex:,.2f}")
            with col2:
                st.metric("🏗️ Total CAPEX", f"${total_capex:,.2f}")
            with col3:
                st.metric("📊 Total General", f"${total_general:,.2f}")
            
            # Gráficos simples
            st.subheader("📊 Distribución de Gastos")
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de distribución
                data_tipo = df_filtrado.groupby('TIPO')['MONTO_EN_USD'].sum().reset_index()
                fig1 = px.pie(data_tipo, values='MONTO_EN_USD', names='TIPO', title='OPEX vs CAPEX')
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Top categorías
                data_cat = df_filtrado.groupby('CATEGORIA_LIMPIA')['MONTO_EN_USD'].sum().reset_index()
                data_cat = data_cat.sort_values('MONTO_EN_USD', ascending=False).head(10)
                fig2 = px.bar(data_cat, x='CATEGORIA_LIMPIA', y='MONTO_EN_USD', title='Top 10 Categorías')
                st.plotly_chart(fig2, use_container_width=True)
            
            # Tabla de detalle
            st.subheader("📋 Detalle de Partidas")
            columnas_mostrar = ['CATEGORIA_LIMPIA', 'DETALLE DE LA PARTIDA', 'DIRECCION', 'MONTO_EN_USD', 'NRO PDC']
            df_tabla = df_filtrado[columnas_mostrar].copy()
            df_tabla = df_tabla[df_tabla['MONTO_EN_USD'] > 0]
            df_tabla = df_tabla.sort_values('MONTO_EN_USD', ascending=False)
            df_tabla['MONTO_EN_USD'] = df_tabla['MONTO_EN_USD'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(df_tabla, use_container_width=True, height=400)
            
            # Resumen
            st.success(f"✅ {len(df_tabla)} partidas encontradas | Total: ${total_general:,.2f}")
            
            # Descarga CSV
            csv = df_filtrado.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="datos_filtrados.csv">📥 Descargar datos filtrados (CSV)</a>'
            st.markdown(href, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")
            st.info("💡 Asegúrate de que el archivo tenga las columnas correctas: CATEGORIA DE LA PARTIDA, DETALLE DE LA PARTIDA, MONTO PLAN USD, MONEDA DE PAGO")
    
    else:
        st.info("📤 Por favor, carga un archivo Excel para comenzar el análisis")
        st.markdown("""
        ### 📋 Estructura del Archivo Requerida
        El archivo debe tener:
        - **CATEGORIA DE LA PARTIDA**: Categoría del gasto
        - **DETALLE DE LA PARTIDA**: Descripción del gasto
        - **MONTO PLAN USD**: Monto en la moneda de pago
        - **MONEDA DE PAGO**: USD, BS/USD, BS, COP
        - **DIRECCION**: COO, CFO, CTO, STAFF PRESIDENCIA
        """)

if __name__ == "__main__":
    main()
