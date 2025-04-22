# =============================================================================
# Script Python para Dashboard de Execução Orçamentária com Streamlit e Plotly
# Adaptado para dados do 'Extrator BI Tesouro.xlsx' (v4 - Chatbot Integrado)
# =============================================================================

# --- 0. Importar Bibliotecas Necessárias ---
import streamlit as st          # Biblioteca principal para construir o app web
import pandas as pd             # Biblioteca para manipulação e análise de dados (DataFrames)
import plotly.express as px     # Biblioteca para criar gráficos de forma fácil (baseado em Plotly)
import numpy as np              # Biblioteca para operações numéricas
import os                       # Biblioteca para interagir com o sistema operacional

# --- Importações para o Chatbot ---
# Tenta importar, mas não quebra o app se não estiverem instaladas
try:
    from pandasai import SmartDataframe
    # Verifique o nome correto da classe para Gemini na versão do PandasAI que instalar
    # Pode ser GoogleGemini, GoogleVertexAI, etc.
    from pandasai.llm import GoogleGemini
    PANDASAI_INSTALLED = True
except ImportError:
    PANDASAI_INSTALLED = False
# ---------------------------------------

# Certifique-se de que 'openpyxl' está instalado para ler arquivos .xlsx:
# pip install openpyxl

# --- 1. Configuração da Página Streamlit ---
st.set_page_config(
    page_title="Execução Orçamentária", # Título na aba do navegador
    page_icon="📊",                  # Ícone na aba
    layout="wide"                   # Layout da página
)

# --- Inicialização do Estado da Sessão ---
# Para controlar a visibilidade da tabela detalhada
if 'show_po_detail' not in st.session_state:
    st.session_state.show_po_detail = False
# Para o histórico do chatbot
if "messages" not in st.session_state:
    st.session_state.messages = []
# -----------------------------------------

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

    # ================== LISTA DE COLUNAS (AJUSTE CONFORME SEU ARQUIVO) ==================
    tesouro_cols_new = [
        'Ano_Orcamento', 'Acao_Codigo', 'Acao_Nome', 'PO_Codigo', 'PO_Nome',
        'GND_Codigo', 'RP_Codigo', 'RP_Nome', 'Fonte_Codigo', 'PTRES',
        'Dotacao_Lei_Creditos', 'Valor_Empenhado', 'Valor_Liquidado', 'Valor_Pago'
    ]
    # ====================================================================================

    dtype_map = {}
    cols_to_str = ['RP_Codigo', 'Fonte_Codigo', 'Acao_Codigo', 'PO_Codigo', 'GND_Codigo', 'PTRES']
    for col_name in cols_to_str:
        if col_name in tesouro_cols_new:
            try:
                col_index = tesouro_cols_new.index(col_name)
                dtype_map[col_index] = str
            except ValueError:
                 # Deveria ser impossível chegar aqui se col_name in tesouro_cols_new, mas por segurança
                 print(f"Aviso interno: Coluna '{col_name}' não encontrada via index, embora presente na lista.")
        else:
            print(f"Aviso: Coluna '{col_name}' definida para ser string não encontrada em 'tesouro_cols_new'.")

    try:
        df_local = pd.read_excel(
            file_path,
            header=0,
            usecols=range(len(tesouro_cols_new)),
            dtype=dtype_map
        )
        df_local.columns = tesouro_cols_new

        currency_cols_tesouro = [
            'Dotacao_Lei_Creditos', 'Valor_Empenhado', 'Valor_Liquidado', 'Valor_Pago'
        ]
        for col in currency_cols_tesouro:
            if col in df_local.columns:
                if not pd.api.types.is_numeric_dtype(df_local[col]):
                    df_local[col] = df_local[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df_local[col] = pd.to_numeric(df_local[col], errors='coerce')
            else:
                # st.warning(f"Coluna de moeda esperada '{col}' não encontrada.") # Removido para diminuir warnings
                df_local[col] = 0
        df_local[currency_cols_tesouro] = df_local[currency_cols_tesouro].fillna(0)

        if 'Valor_Empenhado' in df_local.columns and 'Valor_Liquidado' in df_local.columns:
            df_local['Saldo_Empenho'] = df_local['Valor_Empenhado'] - df_local['Valor_Liquidado']
        else:
            df_local['Saldo_Empenho'] = 0
        if 'Dotacao_Lei_Creditos' in df_local.columns and 'Valor_Empenhado' in df_local.columns:
            df_local['Saldo_a_Empenhar'] = df_local['Dotacao_Lei_Creditos'] - df_local['Valor_Empenhado']
        else:
            df_local['Saldo_a_Empenhar'] = 0

        year_col = 'Ano_Orcamento'
        if year_col in df_local.columns:
            df_local[year_col] = pd.to_numeric(df_local[year_col], errors='coerce')
            df_local[year_col] = df_local[year_col].fillna(0).astype(int)
            anos_disponiveis_local = sorted(df_local[year_col][df_local[year_col] != 0].unique())
            if not anos_disponiveis_local:
                 st.warning(f"Nenhum ano válido (>0) encontrado na coluna '{year_col}'.")
        else:
            st.error(f"ERRO CRÍTICO: Coluna de ano '{year_col}' não encontrada.")
            return None, []

        str_cols_to_clean = ['Acao_Nome', 'PO_Nome', 'RP_Nome']
        for col in str_cols_to_clean:
            if col in df_local.columns:
                df_local[col] = df_local[col].astype(str).str.strip()

        return df_local, anos_disponiveis_local

    except FileNotFoundError:
        st.error(f"Erro: Arquivo '{file_path}' não encontrado.")
        return None, []
    except ValueError as e:
        st.error(f"Erro ao ler '{file_path}'. Verifique se 'tesouro_cols_new' ({len(tesouro_cols_new)} colunas) corresponde ao arquivo Excel e se a planilha está correta. Detalhe: {e}")
        return None, []
    except Exception as e:
        st.error(f"Erro inesperado ao processar {file_path}: {e}")
        return None, []

# --- 3. Função de Formatação de Moeda ---
def format_currency(value):
    try:
        numeric_value = float(value)
        return f"R$ {numeric_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)

# --- 4. Carregar os Dados Iniciais ---
file_path_tesouro = 'Extrator BI Tesouro.xlsx' # Certifique-se que este é o nome correto
with st.spinner(f"Carregando e processando '{file_path_tesouro}'..."):
    df, anos_disponiveis = load_and_process_tesouro_data(file_path_tesouro)

# --- 5. Verifica se os dados foram carregados com sucesso ---
if df is None:
    st.error("Falha no carregamento dos dados. Script interrompido.")
    st.stop()
elif df.empty:
    st.warning("Arquivo lido com sucesso, mas está vazio ou não contém dados válidos.")
    st.stop()
else:
    st.success(f"Dados de '{file_path_tesouro}' carregados ({len(df)} linhas).")

# --- 6. Título Principal do Dashboard ---
st.title("Dashboard de Execução Orçamentária")

# --- 7. Configurar a Barra Lateral (Sidebar) e Filtros Dependentes ---
with st.sidebar:
    # Use um caminho relativo se a logo estiver no repo
    try:
        st.image("icmbio.png", width=150) # Verifique o nome/caminho do arquivo da logo
    except FileNotFoundError:
        st.warning("Arquivo da logo 'icmbio.png' não encontrado.")
    except Exception as e:
        st.warning(f"Não foi possível carregar a logo: {e}")

    st.header("Filtros")

    # Filtro PAI: Ano
    if anos_disponiveis:
        # Definindo 2025 como default, se existir
        default_year = [2025] if 2025 in anos_disponiveis else anos_disponiveis
        selected_years = st.multiselect("Ano Orçamento:", options=anos_disponiveis, default=default_year)
    else:
        selected_years = []

    # DF pré-filtrado por ano para gerar opções dos filtros filhos
    if selected_years:
        numeric_years = [int(y) for y in selected_years]
        df_pre_filtered = df[df['Ano_Orcamento'].isin(numeric_years)].copy()
    else:
        df_pre_filtered = df.copy() # Mostra todas as opções se nenhum ano selecionado

    # Função auxiliar para criar filtros dependentes
    def create_dependent_filter(df_options, col_name, label, default_val=[]):
        if col_name in df_options.columns:
            unique_options = sorted(df_options[col_name].dropna().unique())
            if unique_options:
                # Garante que o default só contenha opções válidas
                valid_default = [d for d in default_val if d in unique_options]
                return st.multiselect(label, options=unique_options, default=valid_default)
            else:
                st.info(f"Nenhuma opção de {label} encontrada para a seleção atual.")
                return [] # Retorna lista vazia se não há opções
        else:
            st.warning(f"Coluna '{col_name}' não encontrada para o filtro '{label}'.")
            return []

    # Cria os filtros filhos usando a função auxiliar
    selected_fonte = create_dependent_filter(df_pre_filtered, 'Fonte_Codigo', "Fonte Codigo:")
    selected_acoes = create_dependent_filter(df_pre_filtered, 'Acao_Codigo', "Acao Codigo:")
    selected_pos = create_dependent_filter(df_pre_filtered, 'PO_Codigo', "PO Codigo:")
    # Exemplo de default para RP_Codigo (ajuste se necessário)
    selected_rp = create_dependent_filter(df_pre_filtered, 'RP_Codigo', "RP Codigo:", default_val=["2"])


# --- 8. Aplicar Filtros Selecionados pelo Usuário ---
filtered_df = df.copy()
if selected_years:
    numeric_years = [int(y) for y in selected_years]
    filtered_df = filtered_df[filtered_df['Ano_Orcamento'].isin(numeric_years)].copy()
# Aplica filtros filhos somente se houver seleção neles
if selected_fonte and 'Fonte_Codigo' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Fonte_Codigo'].isin(selected_fonte)].copy()
if selected_acoes and 'Acao_Codigo' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Acao_Codigo'].isin(selected_acoes)].copy()
if selected_pos and 'PO_Codigo' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['PO_Codigo'].isin(selected_pos)].copy()
if selected_rp and 'RP_Codigo' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['RP_Codigo'].isin(selected_rp)].copy()

# --- 9. Verificar se o DataFrame Filtrado Está Vazio ---
if filtered_df.empty:
    st.warning("Sem dados para os filtros selecionados. Ajuste os filtros na barra lateral.")
    # Placeholders podem ser adicionados aqui se desejar, antes de st.stop()
    st.stop() # Interrompe a execução se não houver dados

# --- Layout Principal ---
st.divider()

# --- 10. Exibir Métricas Resumo ---
st.header("Resumo da Execução")
total_dotacao = filtered_df['Dotacao_Lei_Creditos'].sum()
total_empenhado = filtered_df['Valor_Empenhado'].sum()
total_liquidado = filtered_df['Valor_Liquidado'].sum()
total_pago = filtered_df['Valor_Pago'].sum()
total_saldo_empenho = filtered_df['Saldo_Empenho'].sum()
total_saldo_a_empenhar = filtered_df['Saldo_a_Empenhar'].sum()

m_col1, m_col2, m_col3 = st.columns(3)
with m_col1: st.metric("Dotação Total", format_currency(total_dotacao))
with m_col2: st.metric("Total Empenhado", format_currency(total_empenhado))
with m_col3: st.metric("Total Liquidado", format_currency(total_liquidado))

m_col4, m_col5, m_col6 = st.columns(3)
with m_col4: st.metric("Total Pago", format_currency(total_pago))
with m_col5: st.metric("Saldo de Empenho", format_currency(total_saldo_empenho), delta=format_currency(total_saldo_empenho - total_empenhado) if total_empenhado else None, help="Empenhado - Liquidado")
with m_col6: st.metric("Saldo a Empenhar", format_currency(total_saldo_a_empenhar), delta=format_currency(total_saldo_a_empenhar - total_dotacao) if total_dotacao else None, help="Dotação - Empenhado")

st.divider()

# --- 11. Exibir Tabela Principal Agrupada ---
st.header("Execução por Ação")
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
    st.warning(f"Não foi possível gerar a tabela por Ação. Colunas ausentes: {missing_cols}")

# --- 11.1. Botão e Lógica para Tabela Detalhada por PO ---
st.divider()
button_label = "Ocultar detalhado por PO" if st.session_state.show_po_detail else "Ver detalhado por PO"
if st.button(button_label):
    st.session_state.show_po_detail = not st.session_state.show_po_detail

# --- 11.2. Seção da Tabela Detalhada por PO ---
if st.session_state.show_po_detail:
    st.header("Execução Detalhada por PO")
    detail_cols_group = [
        'Acao_Codigo', 'Acao_Nome', 'PO_Codigo', 'PO_Nome', 'Fonte_Codigo', 'PTRES'
    ]
    # Reusa table_cols_values definida acima
    required_detail_cols = detail_cols_group + table_cols_values
    if all(col in filtered_df.columns for col in required_detail_cols):
        try:
            detail_df_grouped = filtered_df.groupby(detail_cols_group, as_index=False)[table_cols_values].sum()
            sum_values = detail_df_grouped[table_cols_values].abs().sum(axis=1)
            detail_df_grouped = detail_df_grouped[sum_values > 0.01] # Remove linhas zeradas

            if not detail_df_grouped.empty:
                detail_df_grouped = detail_df_grouped.sort_values(by=['Acao_Codigo', 'PO_Codigo', 'Fonte_Codigo'], ascending=True)
                detail_df_formatted = detail_df_grouped.copy()
                for col in table_cols_values:
                    detail_df_formatted[col] = detail_df_grouped[col].apply(format_currency)
                st.dataframe(detail_df_formatted, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum dado encontrado para o detalhamento por PO com os filtros atuais.")
        except Exception as e:
            st.error(f"Erro ao gerar a tabela detalhada por PO: {e}")
    else:
        missing_cols_detail = [col for col in required_detail_cols if col not in filtered_df.columns]
        st.warning(f"Não foi possível gerar a tabela detalhada por PO. Colunas ausentes: {missing_cols_detail}")

# --- 12. Exibir Gráficos ---
st.divider()
st.header("Análise Gráfica")
chart_col1, chart_col2 = st.columns(2)

# --- 12.1. Gráfico de Barras: Dotação Total por Ano ---
with chart_col1:
    bar_chart_col_year = 'Ano_Orcamento'
    bar_chart_col_value = 'Dotacao_Lei_Creditos'
    if bar_chart_col_year in filtered_df.columns and bar_chart_col_value in filtered_df.columns:
        bar_data = filtered_df.groupby(bar_chart_col_year)[bar_chart_col_value].sum().reset_index()
        bar_data = bar_data[bar_data[bar_chart_col_value] > 0]
        if not bar_data.empty:
            bar_data[bar_chart_col_year] = bar_data[bar_chart_col_year].astype(str)
            bar_fig = px.bar(bar_data, x=bar_chart_col_year, y=bar_chart_col_value,
                             title='Dotação por Ano', template='plotly_dark', text_auto='.2s')
            bar_fig.update_layout(xaxis_title='Ano Orçamento', yaxis_title='Dotação (R$)', xaxis_type='category')
            bar_fig.update_traces(textposition='outside', hovertemplate='%{x}<br>%{y:,.2f} R$')
            st.plotly_chart(bar_fig, use_container_width=True)
        else:
             st.info("Sem dados de Dotação para o gráfico de barras por ano.")
    else:
        st.warning("Colunas para o gráfico de barras (Ano/Dotação) não encontradas.")

# --- 12.2. Gráfico de Pizza: Dotação por Ação ---
with chart_col2:
    # Usando Acao_Codigo para agrupar, mas você pode mudar para Acao_Nome se preferir os nomes
    pie_chart_col_group = 'Acao_Codigo'
    pie_chart_col_value = 'Dotacao_Lei_Creditos'
    if pie_chart_col_group in filtered_df.columns and pie_chart_col_value in filtered_df.columns:
        pie_data = filtered_df.groupby(pie_chart_col_group)[pie_chart_col_value].sum().reset_index()
        pie_data = pie_data[pie_data[pie_chart_col_value] > 0]
        if not pie_data.empty:
            max_slices = 7
            if len(pie_data) > max_slices:
                pie_data = pie_data.sort_values(by=pie_chart_col_value, ascending=False)
                pie_data_top = pie_data.head(max_slices - 1)
                outros_sum = pie_data.iloc[max_slices-1:][pie_chart_col_value].sum()
                if outros_sum > 0:
                    outros_row = pd.DataFrame([{pie_chart_col_group: 'Outras Ações', pie_chart_col_value: outros_sum}])
                    pie_data = pd.concat([pie_data_top, outros_row], ignore_index=True)
                else:
                    pie_data = pie_data_top
            pie_fig = px.pie(pie_data, names=pie_chart_col_group, values=pie_chart_col_value,
                             title='Dotação por Ação (Código)', hole=0.3, template='plotly_dark')
            pie_fig.update_traces(textposition='outside', textinfo='percent+label', hovertemplate='%{label}<br>%{value:,.2f} R$ (%{percent})')
            pie_fig.update_layout(showlegend=False)
            st.plotly_chart(pie_fig, use_container_width=True)
        else:
            st.info("Sem dados de Dotação para o gráfico de pizza por Ação.")
    else:
        st.warning("Colunas para o gráfico de pizza (Ação/Dotação) não encontradas.")


# --- 13. Seção do Chatbot Interativo ---
st.divider()
st.header("🤖 Converse com os Dados Filtrados (via Google Gemini)")

if PANDASAI_INSTALLED: # Verifica se a biblioteca foi importada
    # Exibe mensagens antigas do histórico
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Usamos st.write aqui pois ele lida bem com strings, dataframes, etc.
            st.write(message["content"])

    # Input do usuário
    if prompt := st.chat_input("Ex: Qual a dotação total? Qual ação teve maior saldo a empenhar?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Chama a IA
        try:
            # Busca a chave de API (necessário configurar em Segredos no Streamlit Cloud)
            api_key = st.secrets["GOOGLE_API_KEY"]
            llm = GoogleGemini(api_key=api_key) # Ou a classe correta para sua versão do PandasAI

            if not filtered_df.empty:
                # Usa o DataFrame JÁ FILTRADO pelos controles da sidebar
                pandas_ai_df = SmartDataframe(filtered_df, config={"llm": llm})

                with st.chat_message("assistant"):
                    with st.spinner("Analisando com Gemini..."):
                        response = pandas_ai_df.chat(prompt)
                        st.write(response) # Exibe a resposta (pode ser texto, número, df)
                        response_content = response # Guarda para o histórico

            else:
                response_content = "Não há dados selecionados pelos filtros para analisar."
                with st.chat_message("assistant"):
                    st.warning(response_content)

            # Adiciona resposta ao histórico (mesmo se for aviso)
            st.session_state.messages.append({"role": "assistant", "content": response_content})

        except KeyError:
             response_content = "Erro: Chave de API do Google (GOOGLE_API_KEY) não configurada nos Segredos do Streamlit."
             with st.chat_message("assistant"):
                 st.error(response_content)
             st.session_state.messages.append({"role": "assistant", "content": response_content})
        except NameError as e:
             response_content = f"Erro: A classe LLM do Google não foi encontrada. Verifique a importação e instalação das bibliotecas 'pandasai' e 'google-generativeai'. ({e})"
             with st.chat_message("assistant"):
                 st.error(response_content)
             st.session_state.messages.append({"role": "assistant", "content": response_content})
        except Exception as e:
            response_content = f"Ocorreu um erro inesperado ao processar sua pergunta: {e}"
            with st.chat_message("assistant"):
                st.error(response_content)
            st.session_state.messages.append({"role": "assistant", "content": response_content})
else:
     # Mensagem se pandasai não está instalado
     st.warning("Funcionalidade de Chat desabilitada. Instale as bibliotecas necessárias (veja o comando pip).")


# --- Fim do Script ---
st.caption("Dashboard gerado com Streamlit e Plotly.")