# =============================================================================
# Script Python para Dashboard de Execução Orçamentária com Streamlit e Plotly
# Adaptado para dados do 'Extrator BI Tesouro.xlsx' (v3 - Correção dtype)
# =============================================================================

# --- 0. Importar Bibliotecas Necessárias ---
import streamlit as st      # Biblioteca principal para construir o app web
import pandas as pd         # Biblioteca para manipulação e análise de dados (DataFrames)
import plotly.express as px # Biblioteca para criar gráficos de forma fácil (baseado em Plotly)
import numpy as np          # Biblioteca para operações numéricas
import os                   # Biblioteca para interagir com o sistema operacional

# Certifique-se de que 'openpyxl' está instalado para ler arquivos .xlsx:
# pip install openpyxl

# --- 1. Configuração da Página Streamlit ---
st.set_page_config(
    page_title="COOF",   # Título na aba do navegador
    page_icon="🎪",     # Ícone na aba (pode ser um emoji ou URL/caminho)
    layout="wide"                   # Layout da página
)

# --- 2. Função para Carregamento e Preparação dos Dados (Extrator BI Tesouro) ---
@st.cache_data # Cache para otimizar o carregamento
def load_and_process_tesouro_data(file_path):
    """
    Carrega e processa o arquivo Excel 'Extrator BI Tesouro.xlsx'.
    Realiza limpeza: renomear colunas, tratar valores monetários e ano, calcular saldos.
    Retorna o DataFrame processado e a lista de anos disponíveis.
    """
    df_local = None
    anos_disponiveis_local = []

    # ================== LISTA DE COLUNAS ATUALIZADA ==================
    tesouro_cols_new = [
        'Ano_Orcamento',         # Ex: 'Ano do Orçamento'
        'Acao_Codigo',           # Ex: Código da Ação
        'Acao_Nome',             # Ex: Nome da Ação
        'PO_Codigo',             # Ex: Código do Plano Orçamentário
        'PO_Nome',               # Ex: 'Plano Orçamentário Nome'
        'GND_Codigo',            # Ex: Código do Grupo de Natureza da Despesa
        'RP_Codigo',             # Código do Resultado Primário <<<--- Ler como String
        'RP_Nome',               # Nome do Resultado Primário
        'Fonte_Codigo',          # Ex: Código da Fonte  <<<--- Ler como String
        'PTRES',                 # Programa de Trabalho Resumido
        'Dotacao_Lei_Creditos',  # Coluna que representa 'Lei + Créditos'
        'Valor_Empenhado',       # Coluna 'Empenhado'
        'Valor_Liquidado',       # Coluna 'Liquidado'
        'Valor_Pago'             # Coluna 'Pago'
    ]
    # =================================================================

    # --- Cria dicionário dtype dinamicamente ---
    # Mapeia os NOMES das colunas que queremos como string para o tipo 'str'
    # Isso evita problemas se a ordem das colunas mudar na lista acima
    dtype_map = {}
    cols_to_str = ['RP_Codigo', 'Fonte_Codigo', 'Acao_Codigo', 'PO_Codigo', 'GND_Codigo', 'PTRES'] # Adicione outros códigos se necessário

    for col_name in cols_to_str:
        if col_name in tesouro_cols_new:
            # Encontra o índice da coluna na lista para usar no dtype
            col_index = tesouro_cols_new.index(col_name)
            dtype_map[col_index] = str
        else:
            # Aviso se uma coluna esperada como string não estiver na lista principal
            print(f"Aviso: Coluna '{col_name}' definida para ser lida como string não encontrada em 'tesouro_cols_new'.")


    try:
        # --- 2.1. Lê o arquivo Excel, especificando DTYPE para colunas de código ---
        df_local = pd.read_excel(
            file_path,
            header=0,
            usecols=range(len(tesouro_cols_new)), # Lê apenas as colunas de 0 até len-1
            dtype=dtype_map                      # <--- ADICIONADO: Força o tipo string para os índices mapeados
        )

        # --- 2.2. Renomeia as colunas lidas ---
        df_local.columns = tesouro_cols_new
        # Remove a mensagem de sucesso daqui para evitar poluir a interface a cada recarga
        # st.success(f"Arquivo '{file_path}' lido com sucesso. Colunas renomeadas.")

        # --- 2.3. Limpeza de Colunas de Moeda ---
        currency_cols_tesouro = [
            'Dotacao_Lei_Creditos', 'Valor_Empenhado',
            'Valor_Liquidado', 'Valor_Pago'
        ]
        for col in currency_cols_tesouro:
            if col in df_local.columns:
                # Verifica se NÃO é numérico antes de tentar limpar (mais seguro)
                if not pd.api.types.is_numeric_dtype(df_local[col]):
                    df_local[col] = df_local[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                # Converte para numérico, erros viram NaN (necessário mesmo se já for numérico para garantir float)
                df_local[col] = pd.to_numeric(df_local[col], errors='coerce')
            else:
                st.warning(f"Coluna de moeda esperada '{col}' não encontrada no arquivo. Será preenchida com 0.")
                df_local[col] = 0
        df_local[currency_cols_tesouro] = df_local[currency_cols_tesouro].fillna(0)

        # --- 2.4. Calcular Saldos ---
        # (Código dos cálculos inalterado)
        if 'Valor_Empenhado' in df_local.columns and 'Valor_Liquidado' in df_local.columns:
            df_local['Saldo_Empenho'] = df_local['Valor_Empenhado'] - df_local['Valor_Liquidado']
        else:
            st.warning("Colunas 'Valor_Empenhado' ou 'Valor_Liquidado' não encontradas para calcular 'Saldo_Empenho'. Coluna criada com 0.")
            df_local['Saldo_Empenho'] = 0

        if 'Dotacao_Lei_Creditos' in df_local.columns and 'Valor_Empenhado' in df_local.columns:
            df_local['Saldo_a_Empenhar'] = df_local['Dotacao_Lei_Creditos'] - df_local['Valor_Empenhado']
        else:
             st.warning("Colunas 'Dotacao_Lei_Creditos' ou 'Valor_Empenhado' não encontradas para calcular 'Saldo_a_Empenhar'. Coluna criada com 0.")
             df_local['Saldo_a_Empenhar'] = 0

        # --- 2.5. Limpeza da Coluna de Ano ---
        # (Código do ano inalterado)
        year_col = 'Ano_Orcamento'
        if year_col in df_local.columns:
            df_local[year_col] = pd.to_numeric(df_local[year_col], errors='coerce')
            df_local[year_col] = df_local[year_col].fillna(0).astype(int)
            anos_disponiveis_local = sorted(df_local[year_col].unique())
            anos_disponiveis_local = [ano for ano in anos_disponiveis_local if ano != 0]
            if not anos_disponiveis_local:
                 st.warning(f"Nenhum ano válido encontrado na coluna '{year_col}'.")
        else:
            st.error(f"ERRO CRÍTICO: Coluna de ano '{year_col}' não encontrada. Filtro de ano não funcionará.")
            return None, []

        # --- 2.6. Limpeza de Colunas String (Remover Espaços Extras) ---
        # (Código de limpeza de strings _Nome inalterado)
        str_cols_to_clean = [
             'Acao_Nome', 'PO_Nome', 'RP_Nome'
        ]
        for col in str_cols_to_clean:
            if col in df_local.columns:
                df_local[col] = df_local[col].astype(str).str.strip()

        # --- 2.7. Retorna o DataFrame processado e a lista de anos ---
        return df_local, anos_disponiveis_local

    except FileNotFoundError:
        st.error(f"Erro: Arquivo '{file_path}' não encontrado. Verifique o nome e o local do arquivo.")
        return None, []
    except ValueError as e:
        st.error(f"Erro ao ler o arquivo '{file_path}'. Verifique se o número de colunas na lista 'tesouro_cols_new' ({len(tesouro_cols_new)}) corresponde às colunas lidas até 'Pago' no Excel e se os tipos de dados estão corretos. Detalhe: {e}")
        return None, []
    except KeyError as e:
        st.error(f"Erro de processamento: Coluna esperada {e} não encontrada após renomear ou durante cálculos. Verifique a lista 'tesouro_cols_new' e as etapas de limpeza/cálculo.")
        return None, []
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao ler ou processar o arquivo {file_path}: {e}")
        return None, []

# --- 3. Função de Formatação de Moeda ---
# (Inalterado)
def format_currency(value):
    """Formata um valor numérico como moeda brasileira (R$)."""
    try:
        numeric_value = float(value)
        return f"R$ {numeric_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)

# --- 4. Carregar os Dados Iniciais ---
file_path_tesouro = 'Extrator BI Tesouro.xlsx'
# Adiciona uma mensagem informativa ao carregar/recarregar
with st.spinner(f"Carregando e processando '{file_path_tesouro}'..."):
    df, anos_disponiveis = load_and_process_tesouro_data(file_path_tesouro)

# --- 5. Verifica se os dados foram carregados com sucesso ---
if df is None:
    st.error("Falha no carregamento ou processamento dos dados. Verifique as mensagens acima.")
    st.stop()
elif df.empty:
    st.warning("O arquivo foi lido, mas não contém dados.")
    st.stop()
else:
    # Exibe a mensagem de sucesso apenas uma vez após o carregamento bem-sucedido
    st.success(f"Dados de '{file_path_tesouro}' carregados com sucesso ({len(df)} linhas).")


# --- 6. Título Principal do Dashboard ---
st.title("Dashboard de Execução Orçamentária (Base Tesouro)")

# --- 7. Configurar a Barra Lateral (Sidebar) e Adicionar Filtros ---
with st.sidebar:
    st.header("Filtros")

    # --- 7.1. Filtro por Ano do Orçamento ---
    # (Inalterado)
    if anos_disponiveis:
        selected_years = st.multiselect(
            "Ano Orçamento:", options=anos_disponiveis, default=[2025, 2024, 2023]
        )
    else:
        st.warning("Nenhum ano disponível para filtro.")
        selected_years = []

    # --- 7.2. Filtro por Plano Orçamentário (Código) ---
    # Usando Código agora que é string
    filter_col_po = 'PO_Codigo'
    if filter_col_po in df.columns:
        # Não precisa mais de .astype(str) aqui, pois já é string
        unique_pos = sorted(df[filter_col_po].dropna().unique())
        selected_pos = st.multiselect(
            f"{filter_col_po.replace('_',' ').title()}:", options=unique_pos, default=[]
        )
    else:
        st.warning(f"Coluna '{filter_col_po}' não encontrada para filtro.")
        selected_pos = []

    # --- 7.3. Filtro por Ação (Código) ---
    # Usando Código agora que é string
    filter_col_acao = 'Acao_Codigo'
    if filter_col_acao in df.columns:
        # Não precisa mais de .astype(str) aqui
        unique_acoes = sorted(df[filter_col_acao].dropna().unique())
        selected_acoes = st.multiselect(
             f"{filter_col_acao.replace('_',' ').title()}:", options=unique_acoes, default=[]
        )
    else:
        st.warning(f"Coluna '{filter_col_acao}' não encontrada para filtro.")
        selected_acoes = []

    # --- 7.4. Filtro por Resultado Primário (Código) ---
    # Usando Código agora que é string
    filter_col_rp = 'RP_Codigo'
    if filter_col_rp in df.columns:
        # Não precisa mais de .astype(str) aqui
        unique_rp = sorted(df[filter_col_rp].dropna().unique())
        selected_rp = st.multiselect(
             f"{filter_col_rp.replace('_',' ').title()}:", options=unique_rp, default=["2"]
        )
    else:
        st.warning(f"Coluna '{filter_col_rp}' não encontrada para filtro.")
        selected_rp = []


    # --- 7.5. Filtro por Fonte (Código) ---
    # Usando Código agora que é string
    filter_col_fonte = 'Fonte_Codigo'
    if filter_col_fonte in df.columns:
         # Não precisa mais de .astype(str) aqui
        unique_fonte = sorted(df[filter_col_fonte].dropna().unique())
        # Corrigido nome da variável para selected_fonte
        selected_fonte = st.multiselect(
             f"{filter_col_fonte.replace('_',' ').title()}:", options=unique_fonte, default=[]
        )
    else:
        st.sidebar.warning(f"Coluna '{filter_col_fonte}' não encontrada para filtro.")
        selected_fonte = [] # Define a variável mesmo se a coluna não existir


# --- 8. Aplicar Filtros Selecionados pelo Usuário ---
# (Lógica de aplicação dos filtros inalterada, apenas corrigido o nome da variável no filtro de fonte)
filtered_df = df.copy()

if selected_years:
    try:
        numeric_years = [int(y) for y in selected_years]
        filtered_df = filtered_df[filtered_df['Ano_Orcamento'].isin(numeric_years)].copy()
    except Exception as e:
        st.error(f"Erro ao aplicar filtro de ano: {e}")
if selected_pos:
     if filter_col_po in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[filter_col_po].isin(selected_pos)].copy()
if selected_acoes:
     if filter_col_acao in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[filter_col_acao].isin(selected_acoes)].copy()
if selected_rp:
     if filter_col_rp in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[filter_col_rp].isin(selected_rp)].copy()
# Corrigido para usar selected_fonte
if selected_fonte:
    if filter_col_fonte in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[filter_col_fonte].isin(selected_fonte)].copy()


# --- 9. Verificar se o DataFrame Filtrado Está Vazio ---
# (Inalterado)
if filtered_df.empty:
    st.warning("Sem dados para os filtros selecionados. Por favor, ajuste os filtros na barra lateral.")
    # Placeholders...
    st.header("Resumo da Execução")
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
    with m_col1: st.metric("Dotação Total", format_currency(0))
    with m_col2: st.metric("Total Empenhado", format_currency(0))
    with m_col3: st.metric("Total Liquidado", format_currency(0))
    with m_col4: st.metric("Total Pago", format_currency(0))
    with m_col5: st.metric("Saldo de Empenho", format_currency(0))
    with m_col6: st.metric("Saldo a Empenhar", format_currency(0))
    st.header("Detalhes da Execução")
    st.dataframe(pd.DataFrame(), use_container_width=True)
    st.header("Análise Gráfica")
    empty_fig = {'data': [], 'layout': {'title': 'Sem dados para exibir', 'template': 'plotly_dark'}}
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1: st.plotly_chart(empty_fig, use_container_width=True)
    with chart_col2: st.plotly_chart(empty_fig, use_container_width=True)
    st.stop()


# --- 10. Exibir Métricas Resumo ---
# (Inalterado)
st.header("Resumo da Execução")
total_dotacao = filtered_df['Dotacao_Lei_Creditos'].sum()
total_empenhado = filtered_df['Valor_Empenhado'].sum()
total_liquidado = filtered_df['Valor_Liquidado'].sum()


m_col1, m_col2, m_col3 = st.columns(3)
with m_col1: st.metric("Dotação Total", format_currency(total_dotacao))
with m_col2: st.metric("Total Empenhado", format_currency(total_empenhado))
with m_col3: st.metric("Total Liquidado", format_currency(total_liquidado))


total_pago = filtered_df['Valor_Pago'].sum()
total_saldo_empenho = filtered_df['Saldo_Empenho'].sum()
total_saldo_a_empenhar = filtered_df['Saldo_a_Empenhar'].sum()

m_col4, m_col5, m_col6 = st.columns(3)
with m_col4: st.metric("Total Pago", format_currency(total_pago))
with m_col5: st.metric("Saldo de Empenho", format_currency(total_saldo_empenho), delta=format_currency(total_saldo_empenho - total_empenhado) if total_empenhado else None, help="Empenhado - Liquidado")
with m_col6: st.metric("Saldo a Empenhar", format_currency(total_saldo_a_empenhar), delta=format_currency(total_saldo_a_empenhar - total_dotacao) if total_dotacao else None, help="Dotação - Empenhado")
# --- 11. Exibir Tabela Principal Agrupada ---
# (Inalterado - Agrupando por Acao_Codigo e Acao_Nome)
st.header("Detalhes da Execução por Ação")
table_cols_group = ['Acao_Codigo', 'Acao_Nome']
table_cols_values = [
    'Dotacao_Lei_Creditos', 'Valor_Empenhado', 'Valor_Liquidado',
    'Valor_Pago', 'Saldo_Empenho', 'Saldo_a_Empenhar'
]

required_table_cols = table_cols_group + table_cols_values
if all(col in filtered_df.columns for col in required_table_cols):
    table_df_grouped = filtered_df.groupby(table_cols_group, as_index=False)[table_cols_values].sum()
    table_df_grouped = table_df_grouped.sort_values(by='Valor_Empenhado', ascending=False)
    table_df_formatted = table_df_grouped.copy()
    for col in table_cols_values:
        table_df_formatted[col] = table_df_grouped[col].apply(format_currency)
    st.dataframe(table_df_formatted, use_container_width=True, hide_index=True)
else:
    missing_cols = [col for col in required_table_cols if col not in filtered_df.columns]
    st.warning(f"Não foi possível gerar a tabela detalhada por Ação. Colunas ausentes: {missing_cols}")


# --- 12. Exibir Gráficos ---
st.header("Análise Gráfica")
chart_col1, chart_col2 = st.columns(2)

# --- 12.1. Gráfico de Barras: Dotação Total por Ano ---
with chart_col1:
    bar_chart_col_year = 'Ano_Orcamento'
    bar_chart_col_value = 'Dotacao_Lei_Creditos'

    if bar_chart_col_year in filtered_df.columns and bar_chart_col_value in filtered_df.columns:
        # Prepara os dados: agrupa por ano e soma a dotação
        bar_data = filtered_df.groupby(bar_chart_col_year)[bar_chart_col_value].sum().reset_index()
        bar_data = bar_data[bar_data[bar_chart_col_value] > 0]

        if not bar_data.empty:
            # --- CORREÇÃO AQUI ---
            # Converte a coluna de ano para string ANTES de plotar
            # Isso força o Plotly a tratar o eixo X como categórico
            bar_data[bar_chart_col_year] = bar_data[bar_chart_col_year].astype(str)
            # --------------------

            # Cria o gráfico de barras
            bar_fig = px.bar(bar_data,
                             x=bar_chart_col_year, # Agora passará strings ('2024', '2025', etc.)
                             y=bar_chart_col_value,
                             title=f'{bar_chart_col_value.replace("_"," ").title()} por Ano',
                             template='plotly_dark',
                             text_auto='.2s'
                            )
            bar_fig.update_layout(
                xaxis_title='Ano Orçamento',
                yaxis_title=f'{bar_chart_col_value.replace("_"," ").title()} (R$)',
                 # Removido categoryorder, pois a ordem natural de string ('2024', '2025') já funciona
                 # Se quiser ordem específica, pode ordenar o bar_data antes de plotar
                 # xaxis={'categoryorder':'total descending'} # Opcional: reativar se quiser ordem por valor
                xaxis_type='category' # Garante que o eixo seja tratado como categoria
            )
            bar_fig.update_traces(textposition='outside', hovertemplate='%{x}<br>%{y:,.2f} R$')
            st.plotly_chart(bar_fig, use_container_width=True)
        else:
             st.info(f"Sem dados positivos de '{bar_chart_col_value}' para exibir no gráfico de barras por ano.")
    else:
        st.warning(f"Colunas '{bar_chart_col_year}' ou '{bar_chart_col_value}' não encontradas para o gráfico de barras.")

# --- 12.2. Gráfico de Pizza: Dotação por Ação ---
with chart_col2:
    # Alterado para agrupar por Ação e mostrar Dotação
    pie_chart_col_group = 'Acao_Codigo'
    pie_chart_col_value = 'Dotacao_Lei_Creditos'

    if pie_chart_col_group in filtered_df.columns and pie_chart_col_value in filtered_df.columns:
        # Prepara os dados: agrupa por Ação e soma a Dotação
        pie_data = filtered_df.groupby(pie_chart_col_group)[pie_chart_col_value].sum().reset_index()
        pie_data = pie_data[pie_data[pie_chart_col_value] > 0] # Remove valores <= 0

        if not pie_data.empty:
            # Lógica 'Outros' para agrupar fatias pequenas (mantida)
            max_slices = 7 # Número máximo de fatias (incluindo 'Outros')
            if len(pie_data) > max_slices:
                pie_data = pie_data.sort_values(by=pie_chart_col_value, ascending=False)
                pie_data_top = pie_data.head(max_slices - 1)
                outros_sum = pie_data.iloc[max_slices-1:][pie_chart_col_value].sum()
                if outros_sum > 0:
                    outros_row = pd.DataFrame([{pie_chart_col_group: 'Outras Ações', pie_chart_col_value: outros_sum}])
                    pie_data = pd.concat([pie_data_top, outros_row], ignore_index=True)
                else:
                    pie_data = pie_data_top # Caso a soma dos outros seja 0

            # Cria o gráfico de pizza (donut)
            pie_fig = px.pie(pie_data,
                             names=pie_chart_col_group,
                             values=pie_chart_col_value,
                             title=f'{pie_chart_col_value.replace("_"," ").title()} por {pie_chart_col_group.replace("_"," ").title()}',
                             hole=0.3, # Estilo Donut
                             template='plotly_dark')
            # Ajusta os textos e o hover
            pie_fig.update_traces(textposition='outside', textinfo='percent+label', # Mostra percentual e nome fora da fatia
                                  hovertemplate='%{label}<br>%{value:,.2f} R$ (%{percent})') # Tooltip ao passar o mouse
            pie_fig.update_layout(showlegend=False) # Esconde a legenda (informação já está nos labels)
            st.plotly_chart(pie_fig, use_container_width=True)
        else:
            st.info(f"Sem dados positivos de '{pie_chart_col_value}' para exibir no gráfico de pizza por '{pie_chart_col_group}'.")
    else:
        st.warning(f"Colunas '{pie_chart_col_group}' ou '{pie_chart_col_value}' não encontradas para o gráfico de pizza.")


# --- Fim do Script ---
st.caption("Dashboard gerado com Streamlit e Plotly.")