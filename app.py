import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os

st.set_page_config(page_title="Gestão de Custo Variável - Imperatriz", layout="wide")

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
mes_atual_sistema = datetime.today().month - 1

# =========================================================
# FUNÇÕES DE PERSISTÊNCIA EM DISCO (ARQUIVOS LOCAIS)
# =========================================================
FILE_FORNECEDORES = "dados_fornecedores.json"
FILE_VOLUMES = "dados_volumes.json"
FILE_INDICES = "dados_indices.json"
FILE_CUSTOM_RF = "dados_custom_rf.json"

def carregar_json(caminho, default):
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def salvar_json(caminho, dados):
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar dados locais: {e}")

# =========================================================
# FUNÇÕES DE FORMATAÇÃO PT-BR
# =========================================================
def fmt_moeda_br(v):
    if pd.isna(v) or v is None:
        return ""
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_unit_br(v):
    if pd.isna(v) or v is None:
        return ""
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_vol_br(v):
    if pd.isna(v) or v is None:
        return ""
    return f"{v:,.0f}".replace(",", ".")

def fmt_pct_br(v):
    if pd.isna(v) or v is None:
        return ""
    return f"{v:.2f}%".replace(".", ",")

# =========================================================
# INICIALIZAÇÃO DE DADOS
# =========================================================
default_fornec = [
    {"Fornecedor": "VLI", "Tipo": "Tarifa (R$/t)", "Valor_Base": 113.40, "Gatilho_Mensal": "Diesel", "Mes_Inicio": 1, "Mes_Aniv": 6, "Indice_Aniv": "IPCA"},
    {"Fornecedor": "FTL", "Tipo": "Tarifa (R$/t)", "Valor_Base": 17.80, "Gatilho_Mensal": "Diesel", "Mes_Inicio": 1, "Mes_Aniv": 9, "Indice_Aniv": "IPCA"},
    {"Fornecedor": "ASG G5", "Tipo": "Fixo (R$)", "Valor_Base": 104040.00, "Gatilho_Mensal": "Nenhum", "Mes_Inicio": 1, "Mes_Aniv": 5, "Indice_Aniv": "INPC"},
    {"Fornecedor": "Manutenção VLI", "Tipo": "Fixo (R$)", "Valor_Base": 167200.00, "Gatilho_Mensal": "Nenhum", "Mes_Inicio": 1, "Mes_Aniv": 6, "Indice_Aniv": "IPCA"}
]
default_vol_pb = [151923, 122844, 88439, 136974, 136854, 118845, 138754, 146088, 139023, 147327, 139805, 142788]

if "fornecedores" not in st.session_state:
    st.session_state.fornecedores = pd.DataFrame(carregar_json(FILE_FORNECEDORES, default_fornec))

dados_vol_salvos = carregar_json(FILE_VOLUMES, {"pb": default_vol_pb, "real_rf": default_vol_pb})
if "vol_pb" not in st.session_state:
    st.session_state.vol_pb = dados_vol_salvos.get("pb", default_vol_pb)
if "vol_real_rf" not in st.session_state:
    st.session_state.vol_real_rf = dados_vol_salvos.get("real_rf", default_vol_pb)

default_indices = {
    "Mês": MESES,
    "Diesel_%": [0.50] * 12,
    "IPCA_%": [0.35] * 12,
    "INPC_%": [0.30] * 12,
    "IGPM_%": [0.40] * 12
}
if "indices" not in st.session_state:
    st.session_state.indices = pd.DataFrame(carregar_json(FILE_INDICES, default_indices))

if "matriz_real_rf_custom" not in st.session_state:
    st.session_state.matriz_real_rf_custom = carregar_json(FILE_CUSTOM_RF, {})

if "pb_desbloqueado" not in st.session_state:
    st.session_state.pb_desbloqueado = False

tab1, tab2 = st.tabs(["⚙️ Aba 1: Inputs & Premissas Base", "📊 Aba 2: Resultados & Bridges"])

# =========================================================
# ABA 1: INPUTS
# =========================================================
with tab1:
    st.header("1. Status do Período e Volumes Operacionais (t)")
    
    col_st1, col_st2 = st.columns([2, 4])
    with col_st1:
        st.info(f"📅 **Mês Atual do Calendário:** {MESES[mes_atual_sistema]}")
    with col_st2:
        mes_vigente_sel = st.selectbox(
            "Selecione o Mês Vigente Operacional:",
            MESES,
            index=mes_atual_sistema,
            help="O valor base cadastrado será aplicado neste mês. Meses anteriores ficam em verde (Realizados) e posteriores recebem a projeção encadeada."
        )
    mes_vigente_idx = MESES.index(mes_vigente_sel)

    # Estilização de Volumes
    def estilizar_tabela_volume(df):
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        for i, col in enumerate(MESES):
            bg = ""
            if i < mes_vigente_idx:
                bg = "background-color: #E8F5E9;"
            elif i == mes_vigente_idx:
                bg = "background-color: #E3F2FD; border: 2px solid #2196F3;"
            
            for idx in df.index:
                cell_style = bg
                if idx == "Volume Real+RF":
                    v_rf = df.loc["Volume Real+RF", col]
                    v_pb = df.loc["Volume PB", col]
                    if pd.notna(v_rf) and pd.notna(v_pb) and float(v_rf) < float(v_pb):
                        cell_style += " color: #D32F2F; font-weight: bold;"
                styles.loc[idx, col] = cell_style
        return styles

    st.subheader("Painel Comparativo de Volumes (t)")
    st.caption("🔴 *Números em vermelho indicam que o Volume Real+RF está abaixo do PB orçado.*")
    df_vol_comp = pd.DataFrame(
        [st.session_state.vol_pb, st.session_state.vol_real_rf],
        columns=MESES,
        index=["Volume PB", "Volume Real+RF"]
    )
    st.dataframe(
        df_vol_comp.style.apply(estilizar_tabela_volume, axis=None).format(fmt_vol_br),
        use_container_width=True
    )

    with st.expander("✏️ Editar / Colar Volumes Real+RF", expanded=False):
        df_edit_rf = pd.DataFrame([st.session_state.vol_real_rf], columns=MESES, index=["Volume Real+RF"])
        res_v_rf = st.data_editor(df_edit_rf, key="editor_vol_rf_key", use_container_width=True)
        if st.button("💾 Salvar Novo Volume Real+RF"):
            st.session_state.vol_real_rf = [float(res_v_rf.iloc[0, i]) for i in range(12)]
            salvar_json(FILE_VOLUMES, {"pb": st.session_state.vol_pb, "real_rf": st.session_state.vol_real_rf})
            st.success("Volumes Real+RF salvos!")
            st.rerun()

    with st.expander("🔒 Desbloquear Volume PB (Senha: mudar123)", expanded=False):
        if not st.session_state.pb_desbloqueado:
            col_pwd, col_btn = st.columns([3, 1])
            with col_pwd:
                senha_pb = st.text_input("Senha de autorização:", type="password", key="pwd_pb")
            with col_btn:
                st.write("")
                st.write("")
                if st.button("Destravar PB"):
                    if senha_pb == "mudar123":
                        st.session_state.pb_desbloqueado = True
                        st.success("PB desbloqueado!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta!")
        else:
            st.warning("Modo de edição do Volume PB liberado.")
            arq_pb = st.file_uploader("Subir novo arquivo PB (Excel/CSV):", type=["xlsx", "csv"], key="upload_pb")
            if arq_pb is not None:
                try:
                    df_up = pd.read_csv(arq_pb) if arq_pb.name.endswith(".csv") else pd.read_excel(arq_pb)
                    nums = df_up.select_dtypes(include=[np.number]).iloc[0, :12].tolist()
                    if len(nums) == 12:
                        st.session_state.vol_pb = [float(x) for x in nums]
                        salvar_json(FILE_VOLUMES, {"pb": st.session_state.vol_pb, "real_rf": st.session_state.vol_real_rf})
                        st.success("PB importado!")
                except Exception as e:
                    st.error(f"Erro: {e}")
            
            df_edit_pb = pd.DataFrame([st.session_state.vol_pb], columns=MESES, index=["Volume PB"])
            res_pb = st.data_editor(df_edit_pb, key="edit_pb_ativo_key", use_container_width=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("💾 Confirmar e Salvar Novo PB", type="primary"):
                    st.session_state.vol_pb = [float(res_pb.iloc[0, i]) for i in range(12)]
                    st.session_state.pb_desbloqueado = False
                    salvar_json(FILE_VOLUMES, {"pb": st.session_state.vol_pb, "real_rf": st.session_state.vol_real_rf})
                    st.success("PB salvo e travado.")
                    st.rerun()
            with col_b2:
                if st.button("Cancelar"):
                    st.session_state.pb_desbloqueado = False
                    st.rerun()

    st.markdown("---")
    
    # 2. Premissas Macroeconômicas
    st.header("2. Índices Macroeconômicos (% ao mês)")
    df_ind_exib = st.session_state.indices.set_index("Mês").T

    def estilizar_indices(df):
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        for i, col in enumerate(MESES):
            if col in styles.columns:
                if i < mes_vigente_idx:
                    styles[col] = "background-color: #E8F5E9;"
                elif i == mes_vigente_idx:
                    styles[col] = "background-color: #E3F2FD; border: 2px solid #2196F3;"
        return styles

    st.dataframe(
        df_ind_exib.style.apply(estilizar_indices, axis=None).format(fmt_pct_br),
        use_container_width=True
    )

    with st.expander("✏️ Editar Índices Econômicos"):
        edit_ind = st.data_editor(
            st.session_state.indices,
            num_rows="fixed",
            height=160,
            use_container_width=True,
            key="editor_indices_key"
        )
        if st.button("💾 Salvar Índices"):
            st.session_state.indices = edit_ind
            salvar_json(FILE_INDICES, edit_ind.to_dict(orient="list"))
            st.success("Índices salvos!")
            st.rerun()

    st.markdown("---")
    
    # 3. Cadastro de Fornecedores
    st.header("3. Cadastro de Fornecedores & Paramétricas")
    st.caption("ℹ️ O campo **Mês Início (1 a 12)** define quando o fornecedor entra em operação. O **Valor Base** é o valor já fechado do **Mês Vigente**.")
    
    if "Mes_Inicio" not in st.session_state.fornecedores.columns:
        st.session_state.fornecedores["Mes_Inicio"] = 1

    edit_fornec = st.data_editor(
        st.session_state.fornecedores,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Fornecedor": st.column_config.TextColumn("Fornecedor", required=True),
            "Tipo": st.column_config.SelectboxColumn("Tipo de Custo", options=["Tarifa (R$/t)", "Fixo (R$)"], required=True),
            "Valor_Base": st.column_config.NumberColumn("Valor Base Mês Vigente (R$)", step=0.1, required=True),
            "Mes_Inicio": st.column_config.NumberColumn("Mês Início (1-12)", min_value=1, max_value=12, step=1, default=1),
            "Gatilho_Mensal": st.column_config.SelectboxColumn("Gatilho Mensal", options=["Nenhum", "Diesel", "IPCA", "INPC", "IGPM"]),
            "Mes_Aniv": st.column_config.NumberColumn("Mês Aniv. (1-12)", min_value=1, max_value=12, step=1),
            "Indice_Aniv": st.column_config.SelectboxColumn("Índice Aniversário", options=["Nenhum", "IPCA", "INPC", "IGPM"])
        },
        key="editor_fornecedores_table"
    )

    if st.button("💾 Salvar Cadastro de Fornecedores", type="primary"):
        st.session_state.fornecedores = edit_fornec
        salvar_json(FILE_FORNECEDORES, edit_fornec.to_dict(orient="records"))
        st.success("Fornecedores salvos com sucesso!")
        st.rerun()


# =========================================================
# MOTOR DE CÁLCULO DINÂMICO
# =========================================================
vol_pb_arr = np.array(st.session_state.vol_pb, dtype=float)
vol_real_rf_arr = np.array(st.session_state.vol_real_rf, dtype=float)
df_ind = st.session_state.indices

diesel_taxa = df_ind["Diesel_%"].values / 100.0
ipca_taxa = df_ind["IPCA_%"].values / 100.0
inpc_taxa = df_ind["INPC_%"].values / 100.0
igpm_taxa = df_ind["IGPM_%"].values / 100.0

montante_pb = {}
montante_real_rf_calculado = {}
unitario_pb = {}

for _, row in st.session_state.fornecedores.iterrows():
    nome = str(row.get("Fornecedor", "")).strip()
    if not nome or pd.isna(nome):
        continue
        
    tipo = str(row.get("Tipo", "Tarifa (R$/t)"))
    base = float(row.get("Valor_Base", 0.0))
    gatilho = str(row.get("Gatilho_Mensal", "Nenhum"))
    
    # Mês de início de operação
    mes_inicio_raw = row.get("Mes_Inicio", 1)
    m_inicio = (int(mes_inicio_raw) - 1) if pd.notna(mes_inicio_raw) and mes_inicio_raw > 0 else 0

    mes_aniv_raw = row.get("Mes_Aniv")
    m_aniv = (int(mes_aniv_raw) - 1) if pd.notna(mes_aniv_raw) and mes_aniv_raw > 0 else 99
    idx_aniv = str(row.get("Indice_Aniv", "Nenhum"))
    
    taxa_aniv = 0.0
    if idx_aniv == "IPCA":
        taxa_aniv = np.sum(ipca_taxa)
    elif idx_aniv == "INPC":
        taxa_aniv = np.sum(inpc_taxa)
    elif idx_aniv == "IGPM":
        taxa_aniv = np.sum(igpm_taxa)

    # 1. PB Base (Considera o fornecedor ativo a partir de m_inicio)
    m_pb = np.zeros(12)
    u_pb = np.zeros(12)
    for m in range(12):
        if m >= m_inicio:
            if tipo == "Tarifa (R$/t)":
                m_pb[m] = base * vol_pb_arr[m]
                u_pb[m] = base
            else:
                m_pb[m] = base
                u_pb[m] = base / vol_pb_arr[m] if vol_pb_arr[m] > 0 else 0.0

    montante_pb[nome] = m_pb
    unitario_pb[nome] = u_pb

    # 2. Real+RF Encadeado:
    # - Mês vigente (mes_vigente_idx): assume exatamente o Valor_Base (já inclui tudo!).
    # - Meses anteriores: mantêm o valor base original (ou dados imputados manualmente).
    # - Meses posteriores: calculados mês a mês com variação de diesel e aniversário de contrato.
    m_calc = np.zeros(12)
    u_calc = np.zeros(12)
    
    # Preenche meses até o mês vigente
    for m in range(mes_vigente_idx + 1):
        if m >= m_inicio:
            if tipo == "Tarifa (R$/t)":
                u_calc[m] = base
                m_calc[m] = base * vol_real_rf_arr[m]
            else:
                m_calc[m] = base
                u_calc[m] = base / vol_real_rf_arr[m] if vol_real_rf_arr[m] > 0 else 0.0

    # Encadeamento para os meses seguintes (m > mes_vigente_idx)
    for m in range(mes_vigente_idx + 1, 12):
        if m < m_inicio:
            continue
        
        # Variação do diesel do mês anterior para o atual
        var_mensal = (1.0 + diesel_taxa[m]) if gatilho == "Diesel" else 1.0
        # Reajuste pontual no mês de aniversário
        var_aniv = (1.0 + taxa_aniv) if m == m_aniv else 1.0
        
        if tipo == "Tarifa (R$/t)":
            tarifa_ant = u_calc[m - 1] if m - 1 >= m_inicio else base
            tarifa_m = tarifa_ant * var_mensal * var_aniv
            u_calc[m] = tarifa_m
            m_calc[m] = tarifa_m * vol_real_rf_arr[m]
        else:
            custo_ant = m_calc[m - 1] if m - 1 >= m_inicio else base
            custo_m = custo_ant * var_aniv
            m_calc[m] = custo_m
            u_calc[m] = custo_m / vol_real_rf_arr[m] if vol_real_rf_arr[m] > 0 else 0.0

    montante_real_rf_calculado[nome] = m_calc


# =========================================================
# ABA 2: RESULTADOS & BRIDGES
# =========================================================
with tab2:
    st.header("Resultados Consolidados & Bridges")
    st.markdown(
        f"""
        <div style='display: flex; gap: 20px; align-items: center; margin-bottom: 12px;'>
            <span>🟢 <b>Verde Claro:</b> Meses Realizados (anteriores a {mes_vigente_sel})</span>
            <span>🔵 <b>Azul Claro:</b> Mês Vigente Atual ({mes_vigente_sel})</span>
            <span>🔴 <b>Texto em Vermelho:</b> Custo Real+RF <b>maior</b> que o PB orçado (desvio desfavorável)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("✏️ Clique aqui para imputar / ajustar valores mensais de Real+RF por fornecedor", expanded=False):
        st.caption("Você pode ajustar os valores de cada mês livremente. Ao salvar, as alterações ficam gravadas permanentemente.")
        df_editor_input = pd.DataFrame(index=list(montante_pb.keys()), columns=MESES)
        for f in montante_pb.keys():
            if f in st.session_state.matriz_real_rf_custom:
                df_editor_input.loc[f] = st.session_state.matriz_real_rf_custom[f]
            else:
                df_editor_input.loc[f] = montante_real_rf_calculado[f]

        editado_rf = st.data_editor(df_editor_input.astype(float), use_container_width=True, key="editor_matriz_rf_key")
        
        if st.button("💾 Salvar Valores de Real+RF"):
            for f in editado_rf.index:
                st.session_state.matriz_real_rf_custom[f] = [float(x) for x in editado_rf.loc[f].values]
            salvar_json(FILE_CUSTOM_RF, st.session_state.matriz_real_rf_custom)
            st.success("Valores salvos com sucesso!")
            st.rerun()

    # Montagem consolidada
    montante_real_rf = {}
    unitario_real_rf = {}
    for f in montante_pb.keys():
        if f in st.session_state.matriz_real_rf_custom:
            m_rf_val = np.array(st.session_state.matriz_real_rf_custom[f], dtype=float)
        else:
            m_rf_val = montante_real_rf_calculado[f]
        
        montante_real_rf[f] = m_rf_val
        unitario_real_rf[f] = np.where(vol_real_rf_arr > 0, m_rf_val / vol_real_rf_arr, 0.0)

    total_m_pb = sum(montante_pb.values())
    total_m_real_rf = sum(montante_real_rf.values())
    total_u_pb = np.where(vol_pb_arr > 0, total_m_pb / vol_pb_arr, 0.0)
    total_u_real_rf = np.where(vol_real_rf_arr > 0, total_m_real_rf / vol_real_rf_arr, 0.0)

    ordem_linhas = ["TOTAL PB", "TOTAL Real+RF"]
    for f in montante_pb.keys():
        ordem_linhas.append(f"{f} (PB)")
        ordem_linhas.append(f"{f} (Real+RF)")

    def estilizar_tabela_custos(df):
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        for i, col in enumerate(MESES):
            bg = ""
            if i < mes_vigente_idx:
                bg = "background-color: #E8F5E9;"
            elif i == mes_vigente_idx:
                bg = "background-color: #E3F2FD; border: 2px solid #2196F3;"
            
            for idx in df.index:
                cell_style = bg
                if "(Real+RF)" in idx:
                    idx_pb = idx.replace(" (Real+RF)", " (PB)")
                    if idx_pb in df.index and float(df.loc[idx, col]) > float(df.loc[idx_pb, col]):
                        cell_style += " color: #D32F2F; font-weight: bold;"
                elif idx == "TOTAL Real+RF":
                    if float(df.loc["TOTAL Real+RF", col]) > float(df.loc["TOTAL PB", col]):
                        cell_style += " color: #D32F2F; font-weight: bold;"
                        
                styles.loc[idx, col] = cell_style
        return styles

    sum_vol_pb = sum(vol_pb_arr)
    sum_vol_rf = sum(vol_real_rf_arr)

    # -------------------------------------------------------------
    # 1. TABELA DE CUSTO UNITÁRIO (PRIMEIRO)
    # -------------------------------------------------------------
    st.subheader("1. Tabela Comparativa em Unitário (R$/t)")
    dados_u = {}
    for l in ordem_linhas:
        if l == "TOTAL PB":
            media = sum(total_m_pb) / sum_vol_pb if sum_vol_pb > 0 else 0.0
            dados_u[l] = list(total_u_pb) + [media]
        elif l == "TOTAL Real+RF":
            media = sum(total_m_real_rf) / sum_vol_rf if sum_vol_rf > 0 else 0.0
            dados_u[l] = list(total_u_real_rf) + [media]
        elif "(PB)" in l:
            fn = l.replace(" (PB)", "")
            media = sum(montante_pb[fn]) / sum_vol_pb if sum_vol_pb > 0 else 0.0
            dados_u[l] = list(unitario_pb[fn]) + [media]
        elif "(Real+RF)" in l:
            fn = l.replace(" (Real+RF)", "")
            media = sum(montante_real_rf[fn]) / sum_vol_rf if sum_vol_rf > 0 else 0.0
            dados_u[l] = list(unitario_real_rf[fn]) + [media]

    df_tabela_u = pd.DataFrame.from_dict(dados_u, orient="index", columns=MESES + ["Média Ponderada"])
    st.dataframe(
        df_tabela_u.style.apply(estilizar_tabela_custos, axis=None).format(fmt_unit_br),
        use_container_width=True
    )

    # -------------------------------------------------------------
    # 2. TABELA DE MONTANTE (DEPOIS)
    # -------------------------------------------------------------
    st.subheader("2. Tabela Comparativa em Montante (R$)")
    dados_m = {}
    for l in ordem_linhas:
        if l == "TOTAL PB":
            dados_m[l] = list(total_m_pb) + [sum(total_m_pb)]
        elif l == "TOTAL Real+RF":
            dados_m[l] = list(total_m_real_rf) + [sum(total_m_real_rf)]
        elif "(PB)" in l:
            fn = l.replace(" (PB)", "")
            dados_m[l] = list(montante_pb[fn]) + [sum(montante_pb[fn])]
        elif "(Real+RF)" in l:
            fn = l.replace(" (Real+RF)", "")
            dados_m[l] = list(montante_real_rf[fn]) + [sum(montante_real_rf[fn])]

    df_tabela_m = pd.DataFrame.from_dict(dados_m, orient="index", columns=MESES + ["Total Ano"])
    st.dataframe(
        df_tabela_m.style.apply(estilizar_tabela_custos, axis=None).format(fmt_moeda_br),
        use_container_width=True
    )

    st.markdown("---")
    
    # -------------------------------------------------------------
    # 3. BRIDGES WATERFALL
    # -------------------------------------------------------------
    st.header("🌉 Bridges de Impacto no Custo Unitário (R$/t)")

    def gerar_waterfall(titulo, start_idx, end_idx):
        v_pb = vol_pb_arr[start_idx:end_idx].sum()
        v_rf = vol_real_rf_arr[start_idx:end_idx].sum()
        
        u_pb_tot = total_m_pb[start_idx:end_idx].sum() / v_pb if v_pb > 0 else 0.0
        u_rf_tot = total_m_real_rf[start_idx:end_idx].sum() / v_rf if v_rf > 0 else 0.0

        x = ["PB Base"]
        y = [u_pb_tot]
        measures = ["absolute"]

        for f in montante_pb.keys():
            u_f_pb = montante_pb[f][start_idx:end_idx].sum() / v_pb if v_pb > 0 else 0.0
            u_f_rf = montante_real_rf[f][start_idx:end_idx].sum() / v_rf if v_rf > 0 else 0.0
            delta = u_f_rf - u_f_pb
            x.append(f)
            y.append(delta)
            measures.append("relative")

        x.append("Real+RF Final")
        y.append(0)
        measures.append("total")

        textos = []
        for v, m in zip(y, measures):
            if m == "relative":
                sinal = "+" if v >= 0 else "-"
                textos.append(f"{sinal} R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            else:
                textos.append(f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        fig = go.Figure(go.Waterfall(
            name=titulo,
            orientation="v",
            measure=measures,
            x=x,
            textposition="outside",
            text=textos,
            y=y,
            connector={"line": {"color": "#666"}},
            increasing={"marker": {"color": "#E53935"}},
            decreasing={"marker": {"color": "#43A047"}},
            totals={"marker": {"color": "#1E88E5"}}
        ))
        fig.update_layout(
            title=titulo,
            yaxis_title="R$/t",
            waterfallgap=0.3,
            height=430,
            margin=dict(l=30, r=30, t=50, b=30)
        )
        return fig

    b_tab1, b_tab2, b_tab3 = st.tabs([
        f"📅 Bridge Mês Vigente ({mes_vigente_sel})",
        f"📈 Bridge YTD (Jan até {mes_vigente_sel})",
        "🌐 Bridge Full Year (FY - Jan a Dez)"
    ])

    with b_tab1:
        st.plotly_chart(gerar_waterfall(f"Bridge Unitário: Mês de {mes_vigente_sel} (PB vs Real+RF)", mes_vigente_idx, mes_vigente_idx + 1), use_container_width=True)

    with b_tab2:
        st.plotly_chart(gerar_waterfall(f"Bridge Unitário YTD: Janeiro a {mes_vigente_sel} (PB vs Real+RF)", 0, mes_vigente_idx + 1), use_container_width=True)

    with b_tab3:
        st.plotly_chart(gerar_waterfall("Bridge Unitário Full Year: Jan a Dez (PB vs Real+RF)", 0, 12), use_container_width=True)
