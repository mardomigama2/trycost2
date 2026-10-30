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
# FUNÇÕES DE PERSISTÊNCIA EM DISCO
# =========================================================
FILE_FORNECEDORES = "dados_fornecedores.json"
FILE_VOLUMES = "dados_volumes.json"
FILE_INDICES = "dados_indices.json"
FILE_CUSTOM_RF = "dados_custom_rf.json"
FILE_PB_FORNECEDORES = "dados_pb_fornecedores.json"
FILE_HISTORICO_RFX = "historico_rfx.json"

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
# FORMATAÇÃO PT-BR
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
    {"Fornecedor": "VLI", "Tipo": "Tarifa (R$/t)", "Valor_Base": 117.48, "Gatilho_Mensal": "Diesel", "Mes_Inicio": 1, "Mes_Aniv": 6, "Indice_Aniv": "IPCA"},
    {"Fornecedor": "FTL", "Tipo": "Tarifa (R$/t)", "Valor_Base": 17.77, "Gatilho_Mensal": "Diesel", "Mes_Inicio": 1, "Mes_Aniv": 9, "Indice_Aniv": "IPCA"},
    {"Fornecedor": "ASG G5", "Tipo": "Fixo (R$)", "Valor_Base": 104040.00, "Gatilho_Mensal": "Nenhum", "Mes_Inicio": 1, "Mes_Aniv": 5, "Indice_Aniv": "INPC"},
    {"Fornecedor": "Manutenção VLI", "Tipo": "Fixo (R$)", "Valor_Base": 178000.00, "Gatilho_Mensal": "Nenhum", "Mes_Inicio": 1, "Mes_Aniv": 6, "Indice_Aniv": "IPCA"}
]
default_vol_pb = [151923, 122844, 88439, 136974, 136854, 118845, 138754, 146088, 139023, 147327, 139805, 142788]

default_pb_fornecedores = {
    "VLI": [117.48, 116.60, 119.75, 121.42, 122.14, 119.62, 117.15, 114.04, 116.55, 117.26, 118.72, 115.31],
    "FTL": [17.77, 18.61, 19.23, 18.68, 18.09, 17.52, 17.18, 17.22, 17.10, 16.74, 16.93, 16.32],
    "ASG G5": [104040.00, 104040.00, 104040.00, 104040.00, 108721.80, 108721.80, 108721.80, 108721.80, 108721.80, 108721.80, 108721.80, 108721.80],
    "Manutenção VLI": [178000.00] * 12
}

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

if "pb_fornecedores" not in st.session_state:
    st.session_state.pb_fornecedores = carregar_json(FILE_PB_FORNECEDORES, default_pb_fornecedores)

if "historico_rfx" not in st.session_state:
    st.session_state.historico_rfx = carregar_json(FILE_HISTORICO_RFX, {})

if "pb_vol_desbloqueado" not in st.session_state:
    st.session_state.pb_vol_desbloqueado = False

if "pb_fornec_desbloqueado" not in st.session_state:
    st.session_state.pb_fornec_desbloqueado = False

# Três Abas de Trabalho
tab1, tab2, tab3 = st.tabs([
    "⚙️ Aba 1: Inputs & Premissas Base",
    "📊 Aba 2: Controle & Resultados",
    "📚 Aba 3: Histórico de Versões (RFX)"
])

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
            help="O mês selecionado fica em azul claro. Os meses anteriores ficam em verde (Realizados)."
        )
    mes_vigente_idx = MESES.index(mes_vigente_sel)

    def estilizar_colunas_periodo_padrao(df):
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        for i, col in enumerate(MESES):
            if col in styles.columns:
                if i < mes_vigente_idx:
                    styles[col] = "background-color: #E8F5E9;"
                elif i == mes_vigente_idx:
                    styles[col] = "background-color: #E3F2FD; border: 2px solid #2196F3;"
        return styles

    def estilizar_tabela_volume(df):
        styles = estilizar_colunas_periodo_padrao(df)
        for col in MESES:
            if col in df.columns and "Volume Real+RF" in df.index and "Volume PB" in df.index:
                v_rf = df.loc["Volume Real+RF", col]
                v_pb = df.loc["Volume PB", col]
                if pd.notna(v_rf) and pd.notna(v_pb) and float(v_rf) < float(v_pb):
                    styles.loc["Volume Real+RF", col] += " color: #D32F2F; font-weight: bold;"
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
        if not st.session_state.pb_vol_desbloqueado:
            col_pwd, col_btn = st.columns([3, 1])
            with col_pwd:
                senha_pb_vol = st.text_input("Senha de autorização para Volume PB:", type="password", key="pwd_pb_vol")
            with col_btn:
                st.write("")
                st.write("")
                if st.button("Destravar Volume PB"):
                    if senha_pb_vol == "mudar123":
                        st.session_state.pb_vol_desbloqueado = True
                        st.success("Volume PB desbloqueado!")
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
                if st.button("💾 Confirmar e Salvar Novo Volume PB", type="primary"):
                    st.session_state.vol_pb = [float(res_pb.iloc[0, i]) for i in range(12)]
                    st.session_state.pb_vol_desbloqueado = False
                    salvar_json(FILE_VOLUMES, {"pb": st.session_state.vol_pb, "real_rf": st.session_state.vol_real_rf})
                    st.success("Volume PB salvo e travado.")
                    st.rerun()
            with col_b2:
                if st.button("Cancelar Volume PB"):
                    st.session_state.pb_vol_desbloqueado = False
                    st.rerun()

    st.markdown("---")
    
    # -------------------------------------------------------------
    # 2. CUSTO PB
    # -------------------------------------------------------------
    st.header("2. Custo PB")
    st.caption("🔒 *Tabela travada que alimenta o PB de forma imutável. Tarifas em R$/t e Custos Fixos em R$ mensal.*")

    for _, f_row in st.session_state.fornecedores.iterrows():
        f_nome = str(f_row["Fornecedor"]).strip()
        if f_nome and f_nome not in st.session_state.pb_fornecedores:
            st.session_state.pb_fornecedores[f_nome] = [float(f_row.get("Valor_Base", 0.0))] * 12

    df_pb_fornec_exib = pd.DataFrame.from_dict(
        st.session_state.pb_fornecedores,
        orient="index",
        columns=MESES
    )

    tipo_fornec_map = {}
    for _, f_row in st.session_state.fornecedores.iterrows():
        tipo_fornec_map[str(f_row["Fornecedor"]).strip()] = str(f_row.get("Tipo", "Tarifa (R$/t)"))

    def formatar_tabela_pb_fornec(df):
        formatted_df = pd.DataFrame(index=df.index, columns=df.columns, dtype=object)
        for r in df.index:
            t = tipo_fornec_map.get(r, "Tarifa (R$/t)")
            for c in df.columns:
                val = df.loc[r, c]
                if "Tarifa" in t:
                    formatted_df.loc[r, c] = fmt_unit_br(val)
                else:
                    formatted_df.loc[r, c] = fmt_moeda_br(val)
        return formatted_df

    st.dataframe(
        formatar_tabela_pb_fornec(df_pb_fornec_exib).style.apply(estilizar_colunas_periodo_padrao, axis=None),
        use_container_width=True
    )

    with st.expander("🔒 Desbloquear Edição do Custo PB (Senha: mudar123)", expanded=False):
        if not st.session_state.pb_fornec_desbloqueado:
            col_p_forn, col_b_forn = st.columns([3, 1])
            with col_p_forn:
                senha_forn = st.text_input("Senha para alterar o Custo PB:", type="password", key="pwd_pb_fornec")
            with col_b_forn:
                st.write("")
                st.write("")
                if st.button("Destravar Custo PB"):
                    if senha_forn == "mudar123":
                        st.session_state.pb_fornec_desbloqueado = True
                        st.success("Custo PB destravado!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta!")
        else:
            st.warning("⚠️ Edição do Custo PB Habilitada")
            edit_pb_fornec = st.data_editor(
                df_pb_fornec_exib.astype(float),
                use_container_width=True,
                key="editor_pb_fornec_key"
            )
            col_bf1, col_bf2 = st.columns(2)
            with col_bf1:
                if st.button("💾 Salvar e Travar Novo Custo PB", type="primary"):
                    for r in edit_pb_fornec.index:
                        st.session_state.pb_fornecedores[r] = [float(x) for x in edit_pb_fornec.loc[r].values]
                    salvar_json(FILE_PB_FORNECEDORES, st.session_state.pb_fornecedores)
                    st.session_state.pb_fornec_desbloqueado = False
                    st.success("Novo Custo PB salvo e travado!")
                    st.rerun()
            with col_bf2:
                if st.button("Cancelar Custo PB"):
                    st.session_state.pb_fornec_desbloqueado = False
                    st.rerun()

    st.markdown("---")
    
    # -------------------------------------------------------------
    # 3. PREMISSAS MACROECONÔMICAS
    # -------------------------------------------------------------
    st.header("3. Índices Macroeconômicos (% ao mês)")
    df_ind_exib = st.session_state.indices.set_index("Mês").T

    st.dataframe(
        df_ind_exib.style.apply(estilizar_colunas_periodo_padrao, axis=None).format(fmt_pct_br),
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
    
    # -------------------------------------------------------------
    # 4. SIMULADOR RF
    # -------------------------------------------------------------
    st.header("4. Simulador RF")
    st.caption("ℹ️ Defina o novo valor base e o mês de início da nova regra. Os reajustes paramétricos incidem nos meses seguintes.")
    
    if "Mes_Inicio" not in st.session_state.fornecedores.columns:
        st.session_state.fornecedores["Mes_Inicio"] = 1

    edit_fornec = st.data_editor(
        st.session_state.fornecedores,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Fornecedor": st.column_config.TextColumn("Fornecedor", required=True),
            "Tipo": st.column_config.SelectboxColumn("Tipo de Custo", options=["Tarifa (R$/t)", "Fixo (R$)"], required=True),
            "Valor_Base": st.column_config.NumberColumn("Valor Base Projeção (R$)", step=0.1, required=True),
            "Mes_Inicio": st.column_config.NumberColumn("Mês Início Nova Regra (1-12)", min_value=1, max_value=12, step=1, default=1),
            "Gatilho_Mensal": st.column_config.SelectboxColumn("Gatilho Mensal", options=["Nenhum", "Diesel", "IPCA", "INPC", "IGPM"]),
            "Mes_Aniv": st.column_config.NumberColumn("Mês Aniv. (1-12)", min_value=1, max_value=12, step=1),
            "Indice_Aniv": st.column_config.SelectboxColumn("Índice Aniversário", options=["Nenhum", "IPCA", "INPC", "IGPM"])
        },
        key="editor_fornecedores_table"
    )

    if st.button("💾 Salvar e Atualizar Projeção Simulador RF", type="primary"):
        st.session_state.fornecedores = edit_fornec
        salvar_json(FILE_FORNECEDORES, edit_fornec.to_dict(orient="records"))
        
        st.session_state.matriz_real_rf_custom = {}
        salvar_json(FILE_CUSTOM_RF, {})
        
        st.success("✅ Projeção do Simulador RF atualizada com sucesso! Verifique os novos valores na Aba 2.")
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
unitario_pb = {}

# 1. PB 100% BLINDADO
for f_nome, vals_pb in st.session_state.pb_fornecedores.items():
    f_nome_str = str(f_nome).strip()
    tipo_f = tipo_fornec_map.get(f_nome_str, "Tarifa (R$/t)")
    vals_arr = np.array(vals_pb, dtype=float)
    
    if "Tarifa" in tipo_f:
        unitario_pb[f_nome_str] = vals_arr
        montante_pb[f_nome_str] = vals_arr * vol_pb_arr
    else:
        montante_pb[f_nome_str] = vals_arr
        unitario_pb[f_nome_str] = np.where(vol_pb_arr > 0, vals_arr / vol_pb_arr, 0.0)

# 2. MOTOR DINÂMICO DE REAL+RF COM ENCATENAMENTO DE INTERVALO
montante_real_rf = {}
unitario_real_rf = {}

for _, row in st.session_state.fornecedores.iterrows():
    nome = str(row.get("Fornecedor", "")).strip()
    if not nome or pd.isna(nome):
        continue
        
    tipo = str(row.get("Tipo", "Tarifa (R$/t)"))
    base_simulador = float(row.get("Valor_Base", 0.0))
    gatilho = str(row.get("Gatilho_Mensal", "Nenhum"))
    
    mes_inicio_raw = row.get("Mes_Inicio", 1)
    m_inicio_sim = (int(mes_inicio_raw) - 1) if pd.notna(mes_inicio_raw) and mes_inicio_raw > 0 else 0

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

    hist_pb_forn = st.session_state.pb_fornecedores.get(nome, [base_simulador] * 12)
    custom_vals = st.session_state.matriz_real_rf_custom.get(nome, None)

    curva_u = np.zeros(12)
    curva_m = np.zeros(12)

    # Meses Passados (< mes_vigente_idx)
    for m in range(mes_vigente_idx):
        if custom_vals is not None and pd.notna(custom_vals[m]) and float(custom_vals[m]) > 0:
            val_p = float(custom_vals[m])
        elif nome in st.session_state.pb_fornecedores:
            val_p = float(hist_pb_forn[m])
        else:
            val_p = base_simulador if m >= m_inicio_sim else 0.0

        if "Tarifa" in tipo:
            curva_u[m] = val_p
            curva_m[m] = val_p * vol_real_rf_arr[m]
        else:
            curva_m[m] = val_p
            curva_u[m] = val_p / vol_real_rf_arr[m] if vol_real_rf_arr[m] > 0 else 0.0

    # Mês Vigente (mes_vigente_idx) -> ÂNCORA
    if custom_vals is not None and pd.notna(custom_vals[mes_vigente_idx]) and float(custom_vals[mes_vigente_idx]) > 0:
        val_vigente = float(custom_vals[mes_vigente_idx])
    else:
        val_vigente = base_simulador if mes_vigente_idx >= m_inicio_sim else float(hist_pb_forn[mes_vigente_idx])

    if "Tarifa" in tipo:
        curva_u[mes_vigente_idx] = val_vigente
        curva_m[mes_vigente_idx] = val_vigente * vol_real_rf_arr[mes_vigente_idx]
    else:
        curva_m[mes_vigente_idx] = val_vigente
        curva_u[mes_vigente_idx] = val_vigente / vol_real_rf_arr[mes_vigente_idx] if vol_real_rf_arr[mes_vigente_idx] > 0 else 0.0

    # Meses Futuros (> mes_vigente_idx)
    for m in range(mes_vigente_idx + 1, 12):
        if custom_vals is not None and pd.notna(custom_vals[m]) and float(custom_vals[m]) > 0:
            val_m = float(custom_vals[m])
            if "Tarifa" in tipo:
                curva_u[m] = val_m
                curva_m[m] = val_m * vol_real_rf_arr[m]
            else:
                curva_m[m] = val_m
                curva_u[m] = val_m / vol_real_rf_arr[m] if vol_real_rf_arr[m] > 0 else 0.0
            continue

        var_mensal = (1.0 + diesel_taxa[m]) if gatilho == "Diesel" else 1.0
        var_aniv = (1.0 + taxa_aniv) if m == m_aniv else 1.0

        if m == m_inicio_sim and m_inicio_sim > mes_vigente_idx:
            if "Tarifa" in tipo:
                curva_u[m] = base_simulador
                curva_m[m] = base_simulador * vol_real_rf_arr[m]
            else:
                curva_m[m] = base_simulador
                curva_u[m] = base_simulador / vol_real_rf_arr[m] if vol_real_rf_arr[m] > 0 else 0.0
        else:
            if "Tarifa" in tipo:
                tarifa_ant = curva_u[m - 1]
                tarifa_m = tarifa_ant * var_mensal * var_aniv
                curva_u[m] = tarifa_m
                curva_m[m] = tarifa_m * vol_real_rf_arr[m]
            else:
                custo_ant = curva_m[m - 1]
                custo_m = custo_ant * var_aniv
                curva_m[m] = custo_m
                curva_u[m] = custo_m / vol_real_rf_arr[m] if vol_real_rf_arr[m] > 0 else 0.0

    unitario_real_rf[nome] = curva_u
    montante_real_rf[nome] = curva_m

# Totais consolidados
total_m_pb = sum(montante_pb.values())
total_m_real_rf = sum(montante_real_rf.values())
total_u_pb = np.where(vol_pb_arr > 0, total_m_pb / vol_pb_arr, 0.0)
total_u_real_rf = np.where(vol_real_rf_arr > 0, total_m_real_rf / vol_real_rf_arr, 0.0)

todos_fornecedores_ordenados = list(dict.fromkeys(list(montante_pb.keys()) + list(montante_real_rf.keys())))
ordem_linhas = ["TOTAL PB", "TOTAL Real+RF"]
for f in todos_fornecedores_ordenados:
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


# =========================================================
# ABA 2: RESULTADOS & CONTROLE MÊS A MÊS
# =========================================================
with tab2:
    st.header("Resultados Consolidados & Bridges (Mês a Mês)")
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

    # -------------------------------------------------------------
    # EDITOR CUSTOMIZADO DE REAL+RF (TARIFA vs FIXO)
    # -------------------------------------------------------------
    with st.expander("✏️ Ajustar Valores de Real+RF (Tarifas em R$/t e Fixos em R$)", expanded=False):
        st.write("Ajuste os valores reais apurados ou o fechamento do mês vigente. Os meses seguintes até o próximo reajuste do Simulador RF serão ajustados automaticamente com base no valor vigente.")
        
        st.markdown("##### 1. Fornecedores Tarifários (Editar Tarifa em R$/t)")
        lista_tarifarios = [f for f in st.session_state.fornecedores["Fornecedor"].dropna().unique() if "Tarifa" in tipo_fornec_map.get(f, "")]
        if lista_tarifarios:
            df_tar_edit = pd.DataFrame(index=lista_tarifarios, columns=MESES)
            for f in lista_tarifarios:
                df_tar_edit.loc[f] = unitario_real_rf.get(f, [0.0] * 12)
            res_tar = st.data_editor(df_tar_edit.astype(float), use_container_width=True, key="editor_tar_rf")
        else:
            res_tar = pd.DataFrame()

        st.markdown("##### 2. Fornecedores de Custo Fixo (Editar Montante em R$)")
        lista_fixos = [f for f in st.session_state.fornecedores["Fornecedor"].dropna().unique() if "Fixo" in tipo_fornec_map.get(f, "")]
        if lista_fixos:
            df_fix_edit = pd.DataFrame(index=lista_fixos, columns=MESES)
            for f in lista_fixos:
                df_fix_edit.loc[f] = montante_real_rf.get(f, [0.0] * 12)
            res_fix = st.data_editor(df_fix_edit.astype(float), use_container_width=True, key="editor_fix_rf")
        else:
            res_fix = pd.DataFrame()

        col_s_rf1, col_s_rf2 = st.columns([2, 3])
        with col_s_rf1:
            if st.button("💾 Salvar Ajuste e Recalcular Intervalo", type="primary"):
                for f in res_tar.index:
                    st.session_state.matriz_real_rf_custom[f] = [float(x) for x in res_tar.loc[f].values]
                for f in res_fix.index:
                    st.session_state.matriz_real_rf_custom[f] = [float(x) for x in res_fix.loc[f].values]
                salvar_json(FILE_CUSTOM_RF, st.session_state.matriz_real_rf_custom)
                st.success("Ajustes salvos! Projeção encadeada recalculada.")
                st.rerun()
        with col_s_rf2:
            if st.button("🔄 Redefinir Tudo com Base no Simulador RF"):
                st.session_state.matriz_real_rf_custom = {}
                salvar_json(FILE_CUSTOM_RF, {})
                st.info("Ajustes manuais limpos. Tabelas sincronizadas diretamente com o Simulador RF!")
                st.rerun()

    # -------------------------------------------------------------
    # 1. TABELA DE CUSTO UNITÁRIO
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
            vals = unitario_pb.get(fn, np.zeros(12))
            media = sum(montante_pb.get(fn, np.zeros(12))) / sum_vol_pb if sum_vol_pb > 0 else 0.0
            dados_u[l] = list(vals) + [media]
        elif "(Real+RF)" in l:
            fn = l.replace(" (Real+RF)", "")
            vals = unitario_real_rf.get(fn, np.zeros(12))
            media = sum(montante_real_rf.get(fn, np.zeros(12))) / sum_vol_rf if sum_vol_rf > 0 else 0.0
            dados_u[l] = list(vals) + [media]

    df_tabela_u = pd.DataFrame.from_dict(dados_u, orient="index", columns=MESES + ["Média Ponderada"])
    st.dataframe(
        df_tabela_u.style.apply(estilizar_tabela_custos, axis=None).format(fmt_unit_br),
        use_container_width=True
    )

    # -------------------------------------------------------------
    # 2. TABELA DE MONTANTE
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
            vals = montante_pb.get(fn, np.zeros(12))
            dados_m[l] = list(vals) + [sum(vals)]
        elif "(Real+RF)" in l:
            fn = l.replace(" (Real+RF)", "")
            vals = montante_real_rf.get(fn, np.zeros(12))
            dados_m[l] = list(vals) + [sum(vals)]

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

    def gerar_waterfall(titulo, start_idx, end_idx, m_pb_dict, m_rf_dict, v_pb_arr, v_rf_arr):
        v_pb = v_pb_arr[start_idx:end_idx].sum()
        v_rf = v_rf_arr[start_idx:end_idx].sum()
        
        tot_pb = sum([m_pb_dict[k][start_idx:end_idx].sum() for k in m_pb_dict])
        tot_rf = sum([m_rf_dict[k][start_idx:end_idx].sum() for k in m_rf_dict])

        u_pb_tot = tot_pb / v_pb if v_pb > 0 else 0.0
        u_rf_tot = tot_rf / v_rf if v_rf > 0 else 0.0

        x = ["PB Base"]
        y = [u_pb_tot]
        measures = ["absolute"]

        for f in todos_fornecedores_ordenados:
            m_f_pb = m_pb_dict.get(f, np.zeros(12))[start_idx:end_idx].sum()
            m_f_rf = m_rf_dict.get(f, np.zeros(12))[start_idx:end_idx].sum()
            
            u_f_pb = m_f_pb / v_pb if v_pb > 0 else 0.0
            u_f_rf = m_f_rf / v_rf if v_rf > 0 else 0.0
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
        st.plotly_chart(gerar_waterfall(f"Bridge Unitário: Mês de {mes_vigente_sel} (PB vs Real+RF)", mes_vigente_idx, mes_vigente_idx + 1, montante_pb, montante_real_rf, vol_pb_arr, vol_real_rf_arr), use_container_width=True)

    with b_tab2:
        st.plotly_chart(gerar_waterfall(f"Bridge Unitário YTD: Janeiro a {mes_vigente_sel} (PB vs Real+RF)", 0, mes_vigente_idx + 1, montante_pb, montante_real_rf, vol_pb_arr, vol_real_rf_arr), use_container_width=True)

    with b_tab3:
        st.plotly_chart(gerar_waterfall("Bridge Unitário Full Year: Jan a Dez (PB vs Real+RF)", 0, 12, montante_pb, montante_real_rf, vol_pb_arr, vol_real_rf_arr), use_container_width=True)

    st.markdown("---")
    
    # -------------------------------------------------------------
    # 4. BOTÃO PARA CONGELAR E SALVAR A PROJEÇÃO RFX
    # -------------------------------------------------------------
    st.subheader("📸 Salvar Versão Oficial de Rolling Forecast (RFX)")
    st.caption("Grave o cenário atual como uma versão histórica oficial (ex.: RF03, RF06, RF09) para consultas e apresentações à diretoria na Aba 3.")
    
    col_rf_nome, col_rf_btn = st.columns([2, 2])
    with col_rf_nome:
        sugestao_nome = f"RF{mes_vigente_idx + 1:02d}"
        nome_versao_rfx = st.text_input("Nome da Versão:", value=sugestao_nome, help="Exemplo: RF03, RF06, RF09")
    with col_rf_btn:
        st.write("")
        st.write("")
        if st.button("💾 Congelar e Salvar Versão RFX", type="primary"):
            dados_congelados = {
                "data_gravacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "mes_corte": mes_vigente_sel,
                "vol_pb": list(vol_pb_arr),
                "vol_real_rf": list(vol_real_rf_arr),
                "unitario_pb": {k: list(v) for k, v in unitario_pb.items()},
                "unitario_real_rf": {k: list(v) for k, v in unitario_real_rf.items()},
                "montante_pb": {k: list(v) for k, v in montante_pb.items()},
                "montante_real_rf": {k: list(v) for k, v in montante_real_rf.items()}
            }
            st.session_state.historico_rfx[nome_versao_rfx] = dados_congelados
            salvar_json(FILE_HISTORICO_RFX, st.session_state.historico_rfx)
            st.success(f"✅ Versão '{nome_versao_rfx}' gravada com sucesso! Consulte-a a qualquer momento na 'Aba 3: Histórico de Versões'.")
            st.rerun()


# =========================================================
# ABA 3: HISTÓRICO DE VERSÕES CONGELADAS (RFX)
# =========================================================
with tab3:
    st.header("📚 Relatórios de Rolling Forecast Congelados (RFX)")
    st.caption("Consulte os cenários oficiais salvos e compare as projeções históricas apresentadas à diretoria.")

    versoes_disponiveis = list(st.session_state.historico_rfx.keys())

    if not versoes_disponiveis:
        st.info("Nenhuma versão de RFX foi salva até o momento. Vá até a Aba 2 e utilize o botão '📸 Congelar e Salvar Versão RFX'.")
    else:
        col_v_sel, col_v_del = st.columns([3, 1])
        with col_v_sel:
            versao_selecionada = st.selectbox("Selecione a Versão de Rolling Forecast para Visualizar:", versoes_disponiveis)
        with col_v_del:
            st.write("")
            st.write("")
            if st.button("🗑️ Excluir esta Versão"):
                del st.session_state.historico_rfx[versao_selecionada]
                salvar_json(FILE_HISTORICO_RFX, st.session_state.historico_rfx)
                st.warning(f"Versão {versao_selecionada} excluída com sucesso.")
                st.rerun()

        dados_v = st.session_state.historico_rfx[versao_selecionada]
        st.success(f"📌 **Relatório {versao_selecionada}** | Salvo em: **{dados_v.get('data_gravacao', '-')}** | Mês Vigente no Fechamento: **{dados_v.get('mes_corte', '-')}**")

        v_vol_pb = np.array(dados_v["vol_pb"])
        v_vol_rf = np.array(dados_v["vol_real_rf"])
        v_montante_pb = {k: np.array(v) for k, v in dados_v["montante_pb"].items()}
        v_montante_rf = {k: np.array(v) for k, v in dados_v["montante_real_rf"].items()}
        v_unit_pb = {k: np.array(v) for k, v in dados_v["unitario_pb"].items()}
        v_unit_rf = {k: np.array(v) for k, v in dados_v["unitario_real_rf"].items()}

        v_tot_m_pb = sum(v_montante_pb.values())
        v_tot_m_rf = sum(v_montante_rf.values())
        v_tot_u_pb = np.where(v_vol_pb > 0, v_tot_m_pb / v_vol_pb, 0.0)
        v_tot_u_rf = np.where(v_vol_rf > 0, v_tot_m_rf / v_vol_rf, 0.0)

        # Indicadores Chave do RFX
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(f"Volume Total ({versao_selecionada})", f"{sum(v_vol_rf):,.0f} t".replace(",", "."))
        kpi2.metric(f"Montante Total ({versao_selecionada})", fmt_moeda_br(sum(v_tot_m_rf)))
        kpi3.metric(f"Unitário Médio ({versao_selecionada})", fmt_unit_br(sum(v_tot_m_rf) / sum(v_vol_rf)))
        delta_u_rfx = (sum(v_tot_m_rf) / sum(v_vol_rf)) - (sum(v_tot_m_pb) / sum(v_vol_pb))
        kpi4.metric(f"∆ Unitário vs PB", fmt_unit_br(delta_u_rfx), delta=f"{delta_u_rfx:+.2f} R$/t", delta_color="inverse")

        st.markdown("---")

        # 1. Tabela de Custo Unitário Salvo
        st.subheader(f"1. Custo Unitário (R$/t) - Versão {versao_selecionada}")
        v_ordem = ["TOTAL PB", f"TOTAL {versao_selecionada}"]
        for f in v_montante_pb.keys():
            v_ordem.append(f"{f} (PB)")
            v_ordem.append(f"{f} ({versao_selecionada})")

        dados_v_u = {}
        for l in v_ordem:
            if l == "TOTAL PB":
                dados_v_u[l] = list(v_tot_u_pb) + [sum(v_tot_m_pb) / sum(v_vol_pb)]
            elif l == f"TOTAL {versao_selecionada}":
                dados_v_u[l] = list(v_tot_u_rf) + [sum(v_tot_m_rf) / sum(v_vol_rf)]
            elif "(PB)" in l:
                fn = l.replace(" (PB)", "")
                dados_v_u[l] = list(v_unit_pb.get(fn, np.zeros(12))) + [sum(v_montante_pb.get(fn, np.zeros(12))) / sum(v_vol_pb)]
            elif f"({versao_selecionada})" in l:
                fn = l.replace(f" ({versao_selecionada})", "")
                dados_v_u[l] = list(v_unit_rf.get(fn, np.zeros(12))) + [sum(v_montante_rf.get(fn, np.zeros(12))) / sum(v_vol_rf)]

        df_v_exib_u = pd.DataFrame.from_dict(dados_v_u, orient="index", columns=MESES + ["Média Ponderada"])
        st.dataframe(df_v_exib_u.style.format(fmt_unit_br), use_container_width=True)

        # 2. Tabela de Montante Salvo
        st.subheader(f"2. Montante (R$) - Versão {versao_selecionada}")
        dados_v_m = {}
        for l in v_ordem:
            if l == "TOTAL PB":
                dados_v_m[l] = list(v_tot_m_pb) + [sum(v_tot_m_pb)]
            elif l == f"TOTAL {versao_selecionada}":
                dados_v_m[l] = list(v_tot_m_rf) + [sum(v_tot_m_rf)]
            elif "(PB)" in l:
                fn = l.replace(" (PB)", "")
                dados_v_m[l] = list(v_montante_pb.get(fn, np.zeros(12))) + [sum(v_montante_pb.get(fn, np.zeros(12)))]
            elif f"({versao_selecionada})" in l:
                fn = l.replace(f" ({versao_selecionada})", "")
                dados_v_m[l] = list(v_montante_rf.get(fn, np.zeros(12))) + [sum(v_montante_rf.get(fn, np.zeros(12)))]

        df_v_exib_m = pd.DataFrame.from_dict(dados_v_m, orient="index", columns=MESES + ["Total Ano"])
        st.dataframe(df_v_exib_m.style.format(fmt_moeda_br), use_container_width=True)

        st.markdown("---")
        
        # 3. Bridge Waterfall da Versão Salva
        st.subheader(f"3. Bridge Unitário: PB vs {versao_selecionada} (Ano Completo)")
        
        u_base_pb = sum(v_tot_m_pb) / sum(v_vol_pb)
        u_final_rf = sum(v_tot_m_rf) / sum(v_vol_rf)
        
        bx = ["PB Base"]
        by = [u_base_pb]
        bmeasures = ["absolute"]

        for f in v_montante_pb.keys():
            u_f_pb = sum(v_montante_pb[f]) / sum(v_vol_pb)
            u_f_rf = sum(v_montante_rf[f]) / sum(v_vol_rf)
            bx.append(f)
            by.append(u_f_rf - u_f_pb)
            bmeasures.append("relative")

        bx.append(f"{versao_selecionada} Final")
        by.append(0)
        bmeasures.append("total")

        btextos = []
        for v, m in zip(by, bmeasures):
            if m == "relative":
                sinal = "+" if v >= 0 else "-"
                btextos.append(f"{sinal} R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            else:
                btextos.append(f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        fig_v = go.Figure(go.Waterfall(
            name=f"Bridge {versao_selecionada}",
            orientation="v",
            measure=bmeasures,
            x=bx,
            textposition="outside",
            text=btextos,
            y=by,
            connector={"line": {"color": "#666"}},
            increasing={"marker": {"color": "#E53935"}},
            decreasing={"marker": {"color": "#43A047"}},
            totals={"marker": {"color": "#1E88E5"}}
        ))
        fig_v.update_layout(
            title=f"Bridge de Variação Unitária: PB vs {versao_selecionada} (R$/t)",
            yaxis_title="R$/t",
            waterfallgap=0.3,
            height=430,
            margin=dict(l=30, r=30, t=50, b=30)
        )
        st.plotly_chart(fig_v, use_container_width=True)
