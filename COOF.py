# =============================================================================
# Script Python para Dashboard de Execução Orçamentária com Streamlit e Plotly
# Adaptado para dados do 'Extrator BI Tesouro.xlsx' (v6 - Chatbot Gemini Direto)
# =============================================================================

# --- 0. Importar Bibliotecas Necessárias ---
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os

# --- Importações para o Chatbot (DIRETO) ---
try:
    import google.generativeai as genai
    GEMINI_INSTALLED = True
except ImportError:
    GEMINI_INSTALLED = False
# -------------------------------------------

# Certifique-se de que 'openpyxl' está instalado
# pip install openpyxl

# --- 1. Configuração da Página Streamlit ---
st.set_page_config(
    page_title="Execução Orçamentária",
    page_icon="📊",
    layout="wide"
)

# --- Inicialização do Estado da Sessão ---
if 'show_po_detail' not in st.session_state:
    st.session_state.show_po_detail = False
if "messages" not in st.session_state:
    st.session_state.messages = [] # Mantém para o histórico do chat
# -----------------------------------------

# --- 2. Função para Carregamento e Preparação dos Dados ---
@st.cache_data
def load_and_process_tesouro_data(file_path):
    # ... (Conteúdo da função load_and_process_tesouro_data permanece EXATAMENTE O MESMO da versão anterior)
    # ... (Ele garante que df e anos_disponiveis sejam retornados corretamente)
    df_local = None
    anos_disponiveis_local = []
    tesouro_cols_new = [
        'Ano_Orcamento', 'Acao_Codigo', 'Acao_Nome', 'PO_Codigo', 'PO_Nome',
        'GND_Codigo', 'RP_Codigo', 'RP_Nome', 'Fonte_Codigo', 'PTRES',
        'Dotacao_Lei_Creditos', 'Valor_Empenhado', 'Valor_Liquidado', 'Valor_Pago'
    ]
    dtype_map = {}
    cols_to_str = ['RP_Codigo', 'Fonte_Codigo', 'Acao_Codigo', 'PO_Codigo', 'GND_Codigo', 'PTRES']
    for col_name in cols_to_str:
        if col_name in tesouro_cols_new:
            try:
                col_index = tesouro_cols_new.index(col_name)
                dtype_map[col_index] = str
            except ValueError:
                 print(f"Aviso interno: Coluna '{col_name}' não encontrada via index.")
        else:
            print(f"Aviso: Coluna '{col_name}' definida para string não encontrada.")
    try:
        df_local = pd.read_excel(file_path, header=0, usecols=range(len(tesouro_cols_new)), dtype=dtype_map)
        df_local.columns = tesouro_cols_new
        currency_cols_tesouro = ['Dotacao_Lei_Creditos', 'Valor_Empenhado', 'Valor_Liquidado', 'Valor_Pago']
        for col in currency_cols_tesouro:
            if col in df_local.columns:
                if not pd.api.types.is_numeric_dtype(df_local[col]):
                    df_local[col] = df_local[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df_local[col] = pd.to_numeric(df_local[col], errors='coerce')
            else: df_local[col] = 0
        df_local[currency_cols_tesouro] = df_local[currency_cols_tesouro].fillna(0)
        if 'Valor_Empenhado' in df_local.columns and 'Valor_Liquidado' in df_local.columns:
            df_local['Saldo_Empenho'] = df_local['Valor_Empenhado'] - df_local['Valor_Liquidado']
        else: df_local['Saldo_Empenho'] = 0
        if 'Dotacao_Lei_Creditos' in df_local.columns and 'Valor_Empenhado' in df_local.columns:
            df_local['Saldo_a_Empenhar'] = df_local['Dotacao_Lei_Creditos'] - df_local['Valor_Empenhado']
        else: df_local['Saldo_a_Empenhar'] = 0
        year_col = 'Ano_Orcamento'
        if year_col in df_local.columns:
            df_local[year_col] = pd.to_numeric(df_local[year_col], errors='coerce')
            df_local[year_col] = df_local[year_col].fillna(0).astype(int)
            anos_disponiveis_local = sorted(df_local[year_col][df_local[year_col] != 0].unique())
            if not anos_disponiveis_local: st.warning(f"Nenhum ano válido (>0) encontrado.")
        else:
            st.error(f"ERRO CRÍTICO: Coluna '{year_col}' não encontrada.")
            return None, []
        str_cols_to_clean = ['Acao_Nome', 'PO_Nome', 'RP_Nome']
        for col in str_cols_to_clean:
            if col in df_local.columns: df_local[col] = df_local[col].astype(str).str.strip()
        return df_local, anos_disponiveis_local
    except FileNotFoundError: st.error(f"Erro: Arquivo '{file_path}' não encontrado."); return None, []
    except ValueError as e: st.error(f"Erro ao ler '{file_path}'. Verifique 'tesouro_cols_new'. Detalhe: {e}"); return None, []
    except Exception as e: st.error(f"Erro inesperado: {e}"); return None, []


# --- 3. Função de Formatação de Moeda ---
def format_currency(value):
    # ... (Função format_currency permanece EXATAMENTE A MESMA)
    try:
        numeric_value = float(value)
        return f"R$ {numeric_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)

# --- 4. Carregar os Dados Iniciais ---
file_path_tesouro = 'Extrator BI Tesouro.xlsx'
with st.spinner(f"Carregando '{file_path_tesouro}'..."):
    df, anos_disponiveis = load_and_process_tesouro_data(file_path_tesouro)

# --- 5. Verifica se os dados foram carregados ---
if df is None: st.error("Falha no carregamento dos dados."); st.stop()
elif df.empty: st.warning("Arquivo lido, mas vazio."); st.stop()
else: st.success(f"Dados carregados ({len(df)} linhas).")

# --- 6. Título Principal ---
st.title("Dashboard de Execução Orçamentária")

# --- 7. Configurar a Barra Lateral e Filtros Dependentes ---
with st.sidebar:
    # ... (Código da sidebar com logo e filtros dependentes permanece EXATAMENTE O MESMO)
    try: st.image("icmbio.png", width=150)
    except Exception: st.warning("Logo 'icmbio.png' não encontrada.")
    st.header("Filtros")
    if anos_disponiveis:
        default_year = [2025] if 2025 in anos_disponiveis else anos_disponiveis
        selected_years = st.multiselect("Ano Orçamento:", options=anos_disponiveis, default=default_year)
    else: selected_years = []
    if selected_years:
        numeric_years = [int(y) for y in selected_years]
        df_pre_filtered = df[df['Ano_Orcamento'].isin(numeric_years)].copy()
    else: df_pre_filtered = df.copy()
    def create_dependent_filter(df_options, col_name, label, default_val=[]):
        if col_name in df_options.columns:
            unique_options = sorted(df_options[col_name].dropna().unique())
            if unique_options:
                valid_default = [d for d in default_val if d in unique_options]
                return st.multiselect(label, options=unique_options, default=valid_default)
            else: st.info(f"Nenhuma opção de {label} para seleção atual."); return []
        else: st.warning(f"Coluna '{col_name}' não encontrada para filtro."); return []
    selected_fonte = create_dependent_filter(df_pre_filtered, 'Fonte_Codigo', "Fonte Codigo:")
    selected_acoes = create_dependent_filter(df_pre_filtered, 'Acao_Codigo', "Acao Codigo:")
    selected_pos = create_dependent_filter(df_pre_filtered, 'PO_Codigo', "PO Codigo:")
    selected_rp = create_dependent_filter(df_pre_filtered, 'RP_Codigo', "RP Codigo:", default_val=["2"])

# --- 8. Aplicar Filtros ---
# ... (Código para criar filtered_df permanece EXATAMENTE O MESMO)
filtered_df = df.copy()
if selected_years:
    numeric_years = [int(y) for y in selected_years]
    filtered_df = filtered_df[filtered_df['Ano_Orcamento'].isin(numeric_years)].copy()
if selected_fonte and 'Fonte_Codigo' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Fonte_Codigo'].isin(selected_fonte)].copy()
if selected_acoes and 'Acao_Codigo' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Acao_Codigo'].isin(selected_acoes)].copy()
if selected_pos and 'PO_Codigo' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['PO_Codigo'].isin(selected_pos)].copy()
if selected_rp and 'RP_Codigo' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['RP_Codigo'].isin(selected_rp)].copy()

# --- 9. Verificar se o DataFrame Filtrado Está Vazio ---
# ... (Código permanece EXATAMENTE O MESMO)
if filtered_df.empty:
    st.warning("Sem dados para os filtros selecionados.")
    st.stop()

# --- Layout Principal ---
st.divider()
# --- 10. Exibir Métricas Resumo ---
# ... (Código das métricas permanece EXATAMENTE O MESMO)
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

# --- 11. Tabela Principal e Tabela Detalhada (com botão) ---
# ... (Código das tabelas e do botão toggle permanece EXATAMENTE O MESMO)
st.header("Execução por Ação")
table_cols_group = ['Acao_Codigo', 'Acao_Nome']
table_cols_values = ['Dotacao_Lei_Creditos', 'Valor_Empenhado', 'Valor_Liquidado', 'Valor_Pago', 'Saldo_Empenho', 'Saldo_a_Empenhar']
required_table_cols = table_cols_group + table_cols_values
if all(col in filtered_df.columns for col in required_table_cols):
    table_df_grouped = filtered_df.groupby(table_cols_group, as_index=False)[table_cols_values].sum()
    table_df_grouped = table_df_grouped.sort_values(by='Valor_Empenhado', ascending=False)
    table_df_formatted = table_df_grouped.copy()
    for col in table_cols_values: table_df_formatted[col] = table_df_grouped[col].apply(format_currency)
    st.dataframe(table_df_formatted, use_container_width=True, hide_index=True)
else: st.warning(f"Colunas ausentes para Tabela por Ação: {[c for c in required_table_cols if c not in filtered_df.columns]}")
st.divider()
button_label = "Ocultar detalhado por PO" if st.session_state.show_po_detail else "Ver detalhado por PO"
if st.button(button_label): st.session_state.show_po_detail = not st.session_state.show_po_detail
if st.session_state.show_po_detail:
    st.header("Execução Detalhada por PO")
    detail_cols_group = ['Acao_Codigo', 'Acao_Nome', 'PO_Codigo', 'PO_Nome', 'Fonte_Codigo', 'PTRES']
    required_detail_cols = detail_cols_group + table_cols_values
    if all(col in filtered_df.columns for col in required_detail_cols):
        try:
            detail_df_grouped = filtered_df.groupby(detail_cols_group, as_index=False)[table_cols_values].sum()
            sum_values = detail_df_grouped[table_cols_values].abs().sum(axis=1)
            detail_df_grouped = detail_df_grouped[sum_values > 0.01]
            if not detail_df_grouped.empty:
                detail_df_grouped = detail_df_grouped.sort_values(by=['Acao_Codigo', 'PO_Codigo', 'Fonte_Codigo'], ascending=True)
                detail_df_formatted = detail_df_grouped.copy()
                for col in table_cols_values: detail_df_formatted[col] = detail_df_grouped[col].apply(format_currency)
                st.dataframe(detail_df_formatted, use_container_width=True, hide_index=True)
            else: st.info("Nenhum dado encontrado para o detalhamento por PO com os filtros atuais.")
        except Exception as e: st.error(f"Erro ao gerar tabela detalhada por PO: {e}")
    else: st.warning(f"Colunas ausentes para Tabela Detalhada por PO: {[c for c in required_detail_cols if c not in filtered_df.columns]}")

# --- 12. Exibir Gráficos ---
# ... (Código dos gráficos permanece EXATAMENTE O MESMO)
st.divider()
st.header("Análise Gráfica")
chart_col1, chart_col2 = st.columns(2)
with chart_col1: # Gráfico de Barras
    bar_chart_col_year = 'Ano_Orcamento'; bar_chart_col_value = 'Dotacao_Lei_Creditos'
    if bar_chart_col_year in filtered_df.columns and bar_chart_col_value in filtered_df.columns:
        bar_data = filtered_df.groupby(bar_chart_col_year)[bar_chart_col_value].sum().reset_index()
        bar_data = bar_data[bar_data[bar_chart_col_value] > 0]
        if not bar_data.empty:
            bar_data[bar_chart_col_year] = bar_data[bar_chart_col_year].astype(str)
            bar_fig = px.bar(bar_data, x=bar_chart_col_year, y=bar_chart_col_value, title='Dotação por Ano', template='plotly_dark', text_auto='.2s')
            bar_fig.update_layout(xaxis_title='Ano Orçamento', yaxis_title='Dotação (R$)', xaxis_type='category')
            bar_fig.update_traces(textposition='outside', hovertemplate='%{x}<br>%{y:,.2f} R$')
            st.plotly_chart(bar_fig, use_container_width=True)
        else: st.info("Sem dados de Dotação para gráfico de barras.")
    else: st.warning("Colunas para gráfico de barras não encontradas.")
with chart_col2: # Gráfico de Pizza
    pie_chart_col_group = 'Acao_Codigo'; pie_chart_col_value = 'Dotacao_Lei_Creditos'
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
                else: pie_data = pie_data_top
            pie_fig = px.pie(pie_data, names=pie_chart_col_group, values=pie_chart_col_value, title='Dotação por Ação (Código)', hole=0.3, template='plotly_dark')
            pie_fig.update_traces(textposition='outside', textinfo='percent+label', hovertemplate='%{label}<br>%{value:,.2f} R$ (%{percent})')
            pie_fig.update_layout(showlegend=False)
            st.plotly_chart(pie_fig, use_container_width=True)
        else: st.info("Sem dados de Dotação para gráfico de pizza.")
    else: st.warning("Colunas para gráfico de pizza não encontradas.")


# --- 13. Seção do Chatbot Interativo (MODIFICADO - Sem PandasAI) ---
st.divider()
st.header("🤖 Converse com os Dados Filtrados (via Google Gemini)")

# Verifica se a biblioteca do Google foi importada
if GEMINI_INSTALLED:
    # Exibe mensagens antigas do histórico
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"]) # st.write lida bem com markdown/texto

    # Input do usuário
    if prompt := st.chat_input("Faça uma pergunta sobre os dados exibidos..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Chama a IA (Gemini API direto)
        try:
            # Busca a chave de API (necessário configurar em Segredos no Streamlit Cloud)
            api_key = st.secrets["GOOGLE_API_KEY"]
            genai.configure(api_key=api_key)

            # Configura o modelo Gemini Pro
            # Para segurança, desabilitamos categorias potencialmente problemáticas
            generation_config = {
              "temperature": 0.8, # Um pouco mais criativo, ajuste se necessário
              "top_p": 1,
              "top_k": 1,
              "max_output_tokens": 2048,
            }
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash-latest", # Modelo gratuito geralmente disponível
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            # Prepara o contexto de dados a partir do filtered_df
            if not filtered_df.empty:
                # Converte o DataFrame filtrado (ou uma amostra) para texto/markdown
                # Cuidado com o tamanho! Limita a um número de caracteres razoável.
                MAX_CONTEXT_CHARS = 3500 # Ajuste conforme testes e limites de token
                try:
                    # Tenta usar markdown que é mais legível para o LLM
                    data_context = filtered_df.to_markdown(index=False)
                except ImportError:
                    # Fallback para string simples se tabulate não estiver instalado
                    data_context = filtered_df.to_string(index=False)

                if len(data_context) > MAX_CONTEXT_CHARS:
                    # Trunca o contexto se for muito grande
                    data_context = data_context[:MAX_CONTEXT_CHARS] + "\n... (dados truncados)"
                    st.caption(f"Atenção: Apenas parte dos dados filtrados ({MAX_CONTEXT_CHARS} caracteres) foi enviada como contexto para a IA.")

                # Constrói o prompt final para o Gemini
                full_prompt = f"""Você é um assistente prestativo especialista em análise de dados orçamentários.
Analise os seguintes dados, que representam um extrato de execução orçamentária já filtrado:

--- INÍCIO DOS DADOS ---
{data_context}
--- FIM DOS DADOS ---

Responda à seguinte pergunta do usuário, baseando-se **estritamente** nos dados fornecidos acima.
Se a resposta não puder ser encontrada nos dados fornecidos, diga explicitamente que a informação não está disponível nos dados apresentados.
Não invente informações. Seja conciso e direto.

Pergunta do usuário: {prompt}
"""
                # Mostra o spinner enquanto chama a API
                with st.chat_message("assistant"):
                    with st.spinner("Pensando com Gemini..."):
                        response = model.generate_content(full_prompt)
                        try:
                             # A resposta principal geralmente está em response.text
                             response_content = response.text
                        except ValueError:
                             # Às vezes a resposta pode ser bloqueada por segurança
                             response_content = "A resposta foi bloqueada devido às configurações de segurança. Tente reformular sua pergunta."
                             # Opcional: Logar a resposta completa para depuração se necessário
                             # print(response.prompt_feedback)
                        except Exception as e_resp:
                             response_content = f"Erro ao extrair texto da resposta: {e_resp}"

                        st.write(response_content) # Exibe a resposta

            else: # Se filtered_df estiver vazio
                response_content = "Não há dados selecionados pelos filtros para analisar."
                with st.chat_message("assistant"):
                    st.warning(response_content)

            # Adiciona resposta ao histórico
            st.session_state.messages.append({"role": "assistant", "content": response_content})

        except KeyError:
             response_content = "Erro: Chave de API do Google (GOOGLE_API_KEY) não configurada nos Segredos do Streamlit."
             with st.chat_message("assistant"): st.error(response_content)
             st.session_state.messages.append({"role": "assistant", "content": response_content})
        except NameError as e:
             response_content = f"Erro: A biblioteca 'google.generativeai' não foi encontrada. ({e})"
             with st.chat_message("assistant"): st.error(response_content)
             st.session_state.messages.append({"role": "assistant", "content": response_content})
        except Exception as e:
            response_content = f"Ocorreu um erro inesperado ao chamar a API Gemini: {e}"
            with st.chat_message("assistant"): st.error(response_content)
            st.session_state.messages.append({"role": "assistant", "content": response_content})
else:
     # Mensagem se google-generativeai não está instalado
     st.warning("Funcionalidade de Chat desabilitada. Instale a biblioteca 'google-generativeai'.")

# --- Fim do Script ---
st.caption("Dashboard gerado com Streamlit e Plotly.")