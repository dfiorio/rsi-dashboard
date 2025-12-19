import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="RSI Monitor - Nasdaq & S&P 500",
    page_icon="📈",
    layout="wide"
)

# Título
st.title("📈 Monitor de RSI - 50 Stocks Mais Negociados")
st.markdown("**RSI Diário e Semanal atualizado automaticamente**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Seleção de grupos
    grupos = st.multiselect(
        "Selecione os grupos:",
        ["NASDAQ", "S&P 500"],
        default=["NASDAQ", "S&P 500"]
    )
    
    # Filtro de RSI
    st.subheader("Filtros de RSI")
    col1, col2 = st.columns(2)
    with col1:
        rsi_min = st.slider("RSI Mínimo", 0, 100, 0)
    with col2:
        rsi_max = st.slider("RSI Máximo", 0, 100, 100)
    
    # Botão de atualização
    if st.button("🔄 Atualizar Dados Agora", type="primary"):
        st.cache_data.clear()
        st.rerun()

# Função para calcular RSI
@st.cache_data
def calcular_rsi(precos, periodo=14):
    delta = precos.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Dados das ações
@st.cache_data(ttl=3600)  # Cache por 1 hora
def carregar_dados():
    # Lista de tickers
    nasdaq_top = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'AVGO', 'PEP', 'COST',
                  'ADBE', 'CSCO', 'NFLX', 'AMD', 'INTC', 'CMCSA', 'QCOM', 'INTU', 'AMGN', 'TMUS',
                  'PYPL', 'SBUX', 'GILD', 'MDLZ', 'REGN']
    
    sp500_top = ['XOM', 'JPM', 'JNJ', 'V', 'PG', 'UNH', 'MA', 'HD', 'CVX', 'LLY',
                 'BAC', 'KO', 'PFE', 'WMT', 'MRK', 'ABT', 'TMO', 'ACN', 'DHR', 'NEE',
                 'WFC', 'PM', 'LIN', 'DIS', 'RTX']
    
    todos_tickers = []
    if "NASDAQ" in grupos:
        todos_tickers.extend([(ticker, "NASDAQ") for ticker in nasdaq_top])
    if "S&P 500" in grupos:
        todos_tickers.extend([(ticker, "S&P 500") for ticker in sp500_top])
    
    dados_completos = []
    
    for ticker, grupo in todos_tickers:
        try:
            # Baixar dados
            stock_data = yf.download(
                ticker,
                start=datetime.now() - timedelta(days=90),
                end=datetime.now(),
                progress=False
            )
            
            if len(stock_data) > 14:
                # Informações da empresa
                info = yf.Ticker(ticker).info
                
                # RSI Diário
                rsi_diario = calcular_rsi(stock_data['Close'])
                rsi_diario_atual = round(rsi_diario.iloc[-1], 2) if not pd.isna(rsi_diario.iloc[-1]) else None
                
                # RSI Semanal
                weekly_data = stock_data['Close'].resample('W-FRI').last()
                rsi_semanal = calcular_rsi(weekly_data)
                rsi_semanal_atual = round(rsi_semanal.iloc[-1], 2) if len(rsi_semanal) > 0 else None
                
                # Determinar status
                if rsi_diario_atual:
                    if rsi_diario_atual < 30:
                        status = "🔵 Sobrevendido"
                    elif rsi_diario_atual > 70:
                        status = "🔴 Sobrecomprado"
                    else:
                        status = "🟢 Neutro"
                else:
                    status = "⚪ N/A"
                
                # Adicionar aos dados
                dados_completos.append({
                    'Ticker': ticker,
                    'Empresa': info.get('longName', ticker)[:30],
                    'Grupo': grupo,
                    'Preço': round(info.get('currentPrice', stock_data['Close'].iloc[-1]), 2),
                    'RSI Diário': rsi_diario_atual,
                    'RSI Semanal': rsi_semanal_atual,
                    'Status': status,
                    'Volume': f"{info.get('volume', 0):,}",
                    'Setor': info.get('sector', 'N/A')[:15]
                })
                
        except Exception as e:
            st.sidebar.warning(f"Erro com {ticker}: {str(e)[:50]}")
            continue
    
    return pd.DataFrame(dados_completos)

# Carregar dados
with st.spinner("🔄 Carregando dados do Yahoo Finance..."):
    df = carregar_dados()

# Filtros
df_filtrado = df[
    (df['RSI Diário'].between(rsi_min, rsi_max) | df['RSI Diário'].isna())
].sort_values('RSI Diário', ascending=False)

# Layout principal
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    st.metric("📊 Total de Ações", len(df_filtrado))
    
with col2:
    sobrevendidas = len(df_filtrado[df_filtrado['RSI Diário'] < 30])
    st.metric("🔵 Sobrevendidas", sobrevendidas)
    
with col3:
    sobrecompradas = len(df_filtrado[df_filtrado['RSI Diário'] > 70])
    st.metric("🔴 Sobrecompradas", sobrecompradas)

# Separador
st.divider()

# Tabela de dados
st.subheader("📋 Tabela de RSI - Análise Completa")

# Formatar a tabela
def color_rsi(val):
    if pd.isna(val):
        return 'background-color: #f0f0f0'
    elif val < 30:
        return 'background-color: #d4edda'
    elif val > 70:
        return 'background-color: #f8d7da'
    else:
        return 'background-color: #fff3cd'

styled_df = df_filtrado.style.applymap(
    color_rsi, 
    subset=['RSI Diário', 'RSI Semanal']
).format({
    'Preço': '${:.2f}',
    'RSI Diário': '{:.1f}',
    'RSI Semanal': '{:.1f}'
})

st.dataframe(
    styled_df,
    use_container_width=True,
    height=600,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
        "Empresa": st.column_config.TextColumn("Empresa", width="medium"),
        "Grupo": st.column_config.TextColumn("Grupo", width="small"),
        "Preço": st.column_config.NumberColumn("Preço", format="$%.2f"),
        "RSI Diário": st.column_config.ProgressColumn(
            "RSI Diário",
            format="%.1f",
            min_value=0,
            max_value=100,
        ),
        "RSI Semanal": st.column_config.NumberColumn("RSI Semanal", format="%.1f"),
        "Status": st.column_config.TextColumn("Status", width="medium"),
        "Volume": st.column_config.TextColumn("Volume"),
        "Setor": st.column_config.TextColumn("Setor")
    }
)

# Gráficos
st.subheader("📊 Visualizações")

col1, col2 = st.columns(2)

with col1:
    # Gráfico de distribuição
    fig1 = go.Figure()
    
    if not df_filtrado.empty:
        fig1.add_trace(go.Histogram(
            x=df_filtrado['RSI Diário'].dropna(),
            nbinsx=20,
            marker_color='lightblue',
            name='Distribuição RSI'
        ))
    
    fig1.add_vline(x=30, line_dash="dash", line_color="green", 
                   annotation_text="Sobrevendido <30", annotation_position="top")
    fig1.add_vline(x=70, line_dash="dash", line_color="red", 
                   annotation_text="Sobrecomprado >70", annotation_position="top")
    
    fig1.update_layout(
        title="Distribuição do RSI Diário",
        xaxis_title="Valor do RSI",
        yaxis_title="Quantidade de Ações",
        height=400
    )
    
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    # Scatter plot RSI vs Preço
    if not df_filtrado.empty:
        fig2 = go.Figure()
        
        # Agrupar por status
        for status in df_filtrado['Status'].unique():
            df_status = df_filtrado[df_filtrado['Status'] == status]
            
            fig2.add_trace(go.Scatter(
                x=df_status['RSI Diário'],
                y=df_status['Preço'],
                mode='markers',
                name=status,
                text=df_status['Ticker'],
                marker=dict(size=10),
                hovertemplate='<b>%{text}</b><br>RSI: %{x:.1f}<br>Preço: $%{y:.2f}<extra></extra>'
            ))
        
        fig2.update_layout(
            title="RSI vs Preço (por Status)",
            xaxis_title="RSI Diário",
            yaxis_title="Preço (USD)",
            height=400,
            xaxis_range=[0, 100]
        )
        
        # Adicionar zonas
        fig2.add_vrect(x0=0, x1=30, fillcolor="green", opacity=0.1, line_width=0)
        fig2.add_vrect(x0=70, x1=100, fillcolor="red", opacity=0.1, line_width=0)
        
        st.plotly_chart(fig2, use_container_width=True)

# Análise por ticker individual
st.subheader("🔍 Análise Detalhada por Ticker")

ticker_selecionado = st.selectbox(
    "Selecione um ticker para análise detalhada:",
    df_filtrado['Ticker'].tolist()
)

if ticker_selecionado:
    try:
        # Baixar dados históricos
        dados_detalhados = yf.download(
            ticker_selecionado, 
            period="6mo", 
            interval="1d"
        )
        
        # Calcular RSI histórico
        rsi_historico = calcular_rsi(dados_detalhados['Close'])
        
        # Gráfico duplo
        fig3 = go.Figure()
        
        # Preço
        fig3.add_trace(go.Scatter(
            x=dados_detalhados.index,
            y=dados_detalhados['Close'],
            name="Preço",
            yaxis="y1",
            line=dict(color='blue')
        ))
        
        # RSI
        fig3.add_trace(go.Scatter(
            x=dados_detalhados.index,
            y=rsi_historico,
            name="RSI (14)",
            yaxis="y2",
            line=dict(color='orange')
        ))
        
        fig3.update_layout(
            title=f"{ticker_selecionado} - Evolução de Preço e RSI",
            yaxis=dict(title="Preço (USD)", side="left"),
            yaxis2=dict(title="RSI", overlaying="y", side="right", range=[0, 100]),
            height=400,
            hovermode="x unified"
        )
        
        # Adicionar zonas do RSI
        fig3.add_hrect(y0=70, y1=100, line_width=0, fillcolor="red", opacity=0.1, yref="y2")
        fig3.add_hrect(y0=0, y1=30, line_width=0, fillcolor="green", opacity=0.1, yref="y2")
        
        st.plotly_chart(fig3, use_container_width=True)
        
        # Estatísticas do ticker selecionado
        ticker_info = df_filtrado[df_filtrado['Ticker'] == ticker_selecionado].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Preço Atual", f"${ticker_info['Preço']:.2f}")
        with col2:
            st.metric("RSI Diário", f"{ticker_info['RSI Diário']:.1f}")
        with col3:
            st.metric("RSI Semanal", f"{ticker_info['RSI Semanal']:.1f}" if ticker_info['RSI Semanal'] else "N/A")
        with col4:
            st.metric("Status", ticker_info['Status'])
            
    except Exception as e:
        st.error(f"Erro ao carregar dados detalhados para {ticker_selecionado}: {str(e)}")

# Rodapé
st.divider()
st.caption(f"📊 Dados atualizados: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
st.caption("Fonte: Yahoo Finance API | Atualização automática a cada hora")

# Instruções de deploy
with st.expander("🚀 Como Fazer Deploy"):
    st.markdown("""
    ### Para colocar este app no ar:
    
    1. **Faça commit** das mudanças no GitHub
    2. **Acesse** [share.streamlit.io](https://share.streamlit.io)
    3. **Clique em** "New app"
    4. **Selecione** seu repositório
    5. **Branch:** main
    6. **Main file path:** app.py
    7. **Clique** "Deploy"
    
    ⏱️ Em 2 minutos seu app estará online!
    """)
