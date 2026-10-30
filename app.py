import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import textwrap

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
FILE_JUSTIFICATIVAS = "dados_justificativas.json"
FILE_FECHAMENTOS_MES = "fechamentos_mensais.json"

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

def quebrar_texto_plaquinha(texto, largura=22):
    if not texto:
        return ""
    linhas = textwrap.wrap(str(texto).strip(), width=largura)
    return "<br>".join(linhas)

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

if "justificativas" not in st.session_state:
    st.session_state.justificativas = carregar_json(FILE_JUSTIFICATIVAS, {})

if "fechamentos_mes" not in st.session_state:
    st.session_state.fechamentos_mes = carregar_json(FILE_FECHAMENTOS_MES, {})

if "pb_vol_desbloqueado" not in st.session_state:
    st.session_state.pb_vol_desbloqueado = False

if "pb_fornec_desbloqueado" not in st.session_state:
    st.session_state.pb_fornec_desbloqueado = False

# Abas de Trabalho
tab1, tab2, tab3 = st.tabs([
    "⚙️ Aba 1: Inputs & Premissas Base",
    "📊 Aba 2: Controle & Bridges",
    "📚 Aba 3: Histórico de Versões (RFX & Fechamentos)"
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
                    styles[col] = "background-color: #E8F5E9;"  # Verde claro
                elif i == mes_vigente_idx:
                    styles[col] = "background-color: #E3F2FD; border: 2px solid #2196F3;"  # Azul claro
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
            bg = "background-color: #E8F5E9;"  # Verde claro
        elif i == mes_vigente_idx:
            bg = "background-color: #E3F2FD; border: 2px solid #2196F3;"  # Azul claro
        
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
    # 3. REGISTRO DE JUSTIFICATIVAS COM CONTROLE DE POSIÇÃO
    # -------------------------------------------------------------
    st.header("📝 Registro de Justificativas das Variações")
    st.caption("Insira o motivo das variações. O texto cresce na vertical e você pode ajustar o deslocamento para evitar que uma placa cubra a outra.")

    chave_just_mes = f"Mês: {mes_vigente_sel}"
    chave_just_ytd = f"YTD (Jan-{mes_vigente_sel})"
    chave_just_fy = "Full Year (FY)"

    # Inicialização da estrutura de justificativas (com texto, yshift e xshift)
    for c in [chave_just_mes, chave_just_ytd, chave_just_fy]:
        if c not in st.session_state.justificativas:
            st.session_state.justificativas[c] = {}
        for f in todos_fornecedores_ordenados:
            if f not in st.session_state.justificativas[c] or not isinstance(st.session_state.justificativas[c][f], dict):
                # Se era texto antigo simples ou inexistente, converte para dict
                antigo_txt = st.session_state.justificativas[c].get(f, "")
                txt_limpo = antigo_txt if isinstance(antigo_txt, str) else ""
                st.session_state.justificativas[c][f] = {"texto": txt_limpo, "yshift": 25, "xshift": 0}

    with st.expander("✏️ Editar Justificativas e Ajustar Posição das Placas", expanded=False):
        tab_j1, tab_j2, tab_j3 = st.tabs([
            f"📅 Mês Vigente ({mes_vigente_sel})",
            f"📈 YTD (Jan-{mes_vigente_sel})",
            "🌐 Full Year (FY)"
        ])

        # Editor Mês Vigente
        with tab_j1:
            u_pb_m = [unitario_pb.get(f, np.zeros(12))[mes_vigente_idx] for f in todos_fornecedores_ordenados]
            u_rf_m = [unitario_real_rf.get(f, np.zeros(12))[mes_vigente_idx] for f in todos_fornecedores_ordenados]
            df_j_mes = pd.DataFrame({
                "Fornecedor": todos_fornecedores_ordenados,
                "Desvio (R$/t)": np.array(u_rf_m) - np.array(u_pb_m),
                "Justificativa": [st.session_state.justificativas[chave_just_mes][f]["texto"] for f in todos_fornecedores_ordenados],
                "Subir/Descer (Y)": [int(st.session_state.justificativas[chave_just_mes][f].get("yshift", 25)) for f in todos_fornecedores_ordenados],
                "Mover Lateral (X)": [int(st.session_state.justificativas[chave_just_mes][f].get("xshift", 0)) for f in todos_fornecedores_ordenados]
            })
            res_j_mes = st.data_editor(
                df_j_mes,
                disabled=["Fornecedor", "Desvio (R$/t)"],
                column_config={
                    "Desvio (R$/t)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Justificativa": st.column_config.TextColumn("Justificativa", width="large"),
                    "Subir/Descer (Y)": st.column_config.NumberColumn("Subir/Descer Y (px)", help="Aumente para subir a placa (ex: 45, 65) e evitar cobrir a placa vizinha", step=5),
                    "Mover Lateral (X)": st.column_config.NumberColumn("Mover Lateral X (px)", help="Desloque para esquerda (-) ou direita (+) se necessário", step=5)
                },
                key="ed_j_mes",
                use_container_width=True
            )

        # Editor YTD
        with tab_j2:
            v_pb_y = vol_pb_arr[:mes_vigente_idx + 1].sum()
            v_rf_y = vol_real_rf_arr[:mes_vigente_idx + 1].sum()
            u_pb_y = [montante_pb.get(f, np.zeros(12))[:mes_vigente_idx + 1].sum() / v_pb_y if v_pb_y > 0 else 0.0 for f in todos_fornecedores_ordenados]
            u_rf_y = [montante_real_rf.get(f, np.zeros(12))[:mes_vigente_idx + 1].sum() / v_rf_y if v_rf_y > 0 else 0.0 for f in todos_fornecedores_ordenados]
            df_j_ytd = pd.DataFrame({
                "Fornecedor": todos_fornecedores_ordenados,
                "Desvio YTD (R$/t)": np.array(u_rf_y) - np.array(u_pb_y),
                "Justificativa": [st.session_state.justificativas[chave_just_ytd][f]["texto"] for f in todos_fornecedores_ordenados],
                "Subir/Descer (Y)": [int(st.session_state.justificativas[chave_just_ytd][f].get("yshift", 25)) for f in todos_fornecedores_ordenados],
                "Mover Lateral (X)": [int(st.session_state.justificativas[chave_just_ytd][f].get("xshift", 0)) for f in todos_fornecedores_ordenados]
            })
            res_j_ytd = st.data_editor(
                df_j_ytd,
                disabled=["Fornecedor", "Desvio YTD (R$/t)"],
                column_config={
                    "Desvio YTD (R$/t)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Justificativa": st.column_config.TextColumn("Justificativa", width="large"),
                    "Subir/Descer (Y)": st.column_config.NumberColumn("Subir/Descer Y (px)", step=5),
                    "Mover Lateral (X)": st.column_config.NumberColumn("Mover Lateral X (px)", step=5)
                },
                key="ed_j_ytd",
                use_container_width=True
            )

        # Editor FY
        with tab_j3:
            v_pb_f = sum_vol_pb
            v_rf_f = sum_vol_rf
            u_pb_f = [sum(montante_pb.get(f, np.zeros(12))) / v_pb_f if v_pb_f > 0 else 0.0 for f in todos_fornecedores_ordenados]
            u_rf_f = [sum(montante_real_rf.get(f, np.zeros(12))) / v_rf_f if v_rf_f > 0 else 0.0 for f in todos_fornecedores_ordenados]
            df_j_fy = pd.DataFrame({
                "Fornecedor": todos_fornecedores_ordenados,
                "Desvio FY (R$/t)": np.array(u_rf_f) - np.array(u_pb_f),
                "Justificativa": [st.session_state.justificativas[chave_just_fy][f]["texto"] for f in todos_fornecedores_ordenados],
                "Subir/Descer (Y)": [int(st.session_state.justificativas[chave_just_fy][f].get("yshift", 25)) for f in todos_fornecedores_ordenados],
                "Mover Lateral (X)": [int(st.session_state.justificativas[chave_just_fy][f].get("xshift", 0)) for f in todos_fornecedores_ordenados]
            })
            res_j_fy = st.data_editor(
                df_j_fy,
                disabled=["Fornecedor", "Desvio FY (R$/t)"],
                column_config={
                    "Desvio FY (R$/t)": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Justificativa": st.column_config.TextColumn("Justificativa", width="large"),
                    "Subir/Descer (Y)": st.column_config.NumberColumn("Subir/Descer Y (px)", step=5),
                    "Mover Lateral (X)": st.column_config.NumberColumn("Mover Lateral X (px)", step=5)
                },
                key="ed_j_fy",
                use_container_width=True
            )

        if st.button("💾 Salvar Todas as Justificativas e Posições", type="primary"):
            for _, r in res_j_mes.iterrows():
                st.session_state.justificativas[chave_just_mes][r["Fornecedor"]] = {
                    "texto": str(r["Justificativa"]).strip(),
                    "yshift": int(r["Subir/Descer (Y)"]),
                    "xshift": int(r["Mover Lateral (X)"])
                }
            for _, r in res_j_ytd.iterrows():
                st.session_state.justificativas[chave_just_ytd][r["Fornecedor"]] = {
                    "texto": str(r["Justificativa"]).strip(),
                    "yshift": int(r["Subir/Descer (Y)"]),
                    "xshift": int(r["Mover Lateral (X)"])
                }
            for _, r in res_j_fy.iterrows():
                st.session_state.justificativas[chave_just_fy][r["Fornecedor"]] = {
                    "texto": str(r["Justificativa"]).strip(),
                    "yshift": int(r["Subir/Descer (Y)"]),
                    "xshift": int(r["Mover Lateral (X)"])
                }
            salvar_json(FILE_JUSTIFICATIVAS, st.session_state.justificativas)
            st.success("Justificativas e posições salvas com sucesso!")
            st.rerun()

    st.markdown("---")
    
    # -------------------------------------------------------------
    # 4. BRIDGES WATERFALL
    # -------------------------------------------------------------
    st.header("🌉 Bridges de Impacto no Custo Unitário (R$/t)")

    def gerar_waterfall_fpna(titulo, label_final, start_idx, end_idx, chave_just_atual):
        v_pb = vol_pb_arr[start_idx:end_idx].sum()
        v_rf = vol_real_rf_arr[start_idx:end_idx].sum()
        
        tot_pb = sum([montante_pb[k][start_idx:end_idx].sum() for k in montante_pb])
        tot_rf = sum([montante_real_rf[k][start_idx:end_idx].sum() for k in montante_real_rf])

        u_pb_tot = tot_pb / v_pb if v_pb > 0 else 0.0
        u_rf_tot = tot_rf / v_rf if v_rf > 0 else 0.0
        
        delta_abs_total = u_rf_tot - u_pb_tot
        pct_delta_total = ((u_rf_tot / u_pb_tot) - 1) * 100 if u_pb_tot > 0 else 0.0

        x_labels = ["PB"]
        y_vals = [u_pb_tot]
        measures = ["absolute"]

        deltas_fornec = []
        for f in todos_fornecedores_ordenados:
            m_f_pb = montante_pb.get(f, np.zeros(12))[start_idx:end_idx].sum()
            m_f_rf = montante_real_rf.get(f, np.zeros(12))[start_idx:end_idx].sum()
            
            u_f_pb = m_f_pb / v_pb if v_pb > 0 else 0.0
            u_f_rf = m_f_rf / v_rf if v_rf > 0 else 0.0
            delta = u_f_rf - u_f_pb
            
            x_labels.append(f)
            y_vals.append(delta)
            deltas_fornec.append(delta)
            measures.append("relative")

        x_labels.append(label_final)
        y_vals.append(0)
        measures.append("total")

        textos = []
        for v, m in zip(y_vals, measures):
            if m == "relative":
                sinal = "+" if v >= 0 else "-"
                textos.append(f"{sinal} R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            elif m == "total":
                textos.append(f"R$ {u_rf_tot:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            else:
                textos.append(f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        fig = go.Figure(go.Waterfall(
            name=titulo,
            orientation="v",
            measure=measures,
            x=x_labels,
            textposition="outside",
            text=textos,
            y=y_vals,
            connector={"line": {"color": "#666", "width": 1.2, "dash": "dot"}},
            increasing={"marker": {"color": "#E53935"}},
            decreasing={"marker": {"color": "#43A047"}},
            totals={"marker": {"color": "#1E88E5"}}
        ))

        max_base = max(u_pb_tot, u_rf_tot)
        y_top_bracket = max_base * 1.25
        y_teto_grafico = max_base * 1.45

        # 1. LINHA EM SUPORTE RETANGULAR FINO
        fig.add_shape(
            type="path",
            path=f"M 0,{u_pb_tot * 1.05} L 0,{y_top_bracket} L {len(x_labels)-1},{y_top_bracket} L {len(x_labels)-1},{u_rf_tot * 1.05}",
            line=dict(color="#222222", width=1.3),
            layer="above"
        )

        # 2. MEDALHA OVAL COM TIPOGRAFIA PADRÃO
        x_meio = (len(x_labels) - 1) / 2.0
        sinal_delta = "+" if delta_abs_total >= 0 else ""
        texto_medalha = f"{sinal_delta}{delta_abs_total:,.2f} ({sinal_delta}{pct_delta_total:.1f}%)".replace(".", ",").replace("X", ".")

        fig.add_annotation(
            x=x_meio,
            y=y_top_bracket,
            text=texto_medalha,
            showarrow=False,
            font=dict(size=12, color="#222222", family="Arial, sans-serif"),
            bgcolor="#FFFFFF",
            bordercolor="#222222",
            borderwidth=1.5,
            borderpad=6,
            align="center",
            yshift=0
        )

        # 3. PLAQUINHAS COM FUNDO BRANCO, QUEBRA VERTICAL E AJUSTE DE POSIÇÃO
        just_map = st.session_state.justificativas.get(chave_just_atual, {})
        acumulado = u_pb_tot
        
        for i, f in enumerate(todos_fornecedores_ordenados):
            delta_val = deltas_fornec[i]
            acumulado_anterior = acumulado
            acumulado += delta_val
            
            dado_f = just_map.get(f, {})
            texto_raw = dado_f.get("texto", "") if isinstance(dado_f, dict) else str(dado_f)
            yshift_custom = int(dado_f.get("yshift", 25)) if isinstance(dado_f, dict) else 25
            xshift_custom = int(dado_f.get("xshift", 0)) if isinstance(dado_f, dict) else 0

            texto_limpo = texto_raw.strip()
            if texto_limpo and abs(delta_val) > 0.001:
                y_pos_barra = max(acumulado_anterior, acumulado)
                cor_borda = "#D32F2F" if delta_val > 0 else "#2E7D32"
                cor_texto = "#B71C1C" if delta_val > 0 else "#1B5E20"
                texto_formatado = quebrar_texto_plaquinha(texto_limpo, largura=22)
                
                fig.add_annotation(
                    x=f,
                    y=y_pos_barra,
                    text=f"💬 <i>{texto_formatado}</i>",
                    showarrow=False,
                    font=dict(size=9.5, color=cor_texto, family="Arial, sans-serif"),
                    bgcolor="#FFFFFF",  # Fundo 100% Branco
                    bordercolor=cor_borda,
                    borderwidth=1.2,
                    borderpad=5,
                    yshift=yshift_custom,
                    xshift=xshift_custom,
                    align="center"
                )

        fig.update_layout(
            title=dict(text=f"<b>{titulo}</b>", x=0.5, xanchor="center", font=dict(size=17, color="#222")),
            yaxis_title="R$/t",
            waterfallgap=0.3,
            height=540,
            yaxis=dict(range=[0, y_teto_grafico]),
            margin=dict(l=30, r=30, t=75, b=40)
        )
        return fig

    b_tab1, b_tab2, b_tab3 = st.tabs([
        f"📅 Bridge Mês Vigente ({mes_vigente_sel})",
        f"📈 Bridge YTD (Jan até {mes_vigente_sel})",
        "🌐 Bridge Full Year (FY - Jan a Dez)"
    ])

    with b_tab1:
        st.plotly_chart(
            gerar_waterfall_fpna(
                f"Real vs Orçado - {mes_vigente_sel}",
                "Real",
                mes_vigente_idx,
                mes_vigente_idx + 1,
                chave_just_mes
            ),
            use_container_width=True
        )

    with b_tab2:
        st.plotly_chart(
            gerar_waterfall_fpna(
                f"Real vs Orçado - YTD (Janeiro a {mes_vigente_sel})",
                "Real YTD",
                0,
                mes_vigente_idx + 1,
                chave_just_ytd
            ),
            use_container_width=True
        )

    with b_tab3:
        st.plotly_chart(
            gerar_waterfall_fpna(
                "Real vs Orçado - Full Year (FY 12 Meses)",
                "Real+RF",
                0,
                12,
                chave_just_fy
            ),
            use_container_width=True
        )

    st.markdown("---")
    
    # -------------------------------------------------------------
    # 5. BOTÕES DE REGISTRO OFICIAL (FECHAMENTO DO MÊS E RFX)
    # -------------------------------------------------------------
    st.subheader("📸 Registros Oficiais (Snapshot / Fechamento)")
    
    col_reg1, col_reg2 = st.columns(2)
    
    with col_reg1:
        st.markdown("##### 1. Registrar Fechamento Oficial do Mês")
        st.caption(f"Grava um screenshot/snapshot permanente dos dados realizados e justificativas de **{mes_vigente_sel}** para consulta histórica na Aba 3.")
        if st.button(f"🔒 Gravar Fechamento Oficial de {mes_vigente_sel}", type="primary"):
            dados_fechamento = {
                "mes": mes_vigente_sel,
                "data_fechamento": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "vol_pb": float(vol_pb_arr[mes_vigente_idx]),
                "vol_real": float(vol_real_rf_arr[mes_vigente_idx]),
                "unitario_pb": {k: float(v[mes_vigente_idx]) for k, v in unitario_pb.items()},
                "unitario_real": {k: float(v[mes_vigente_idx]) for k, v in unitario_real_rf.items()},
                "montante_pb": {k: float(v[mes_vigente_idx]) for k, v in montante_pb.items()},
                "montante_real": {k: float(v[mes_vigente_idx]) for k, v in montante_real_rf.items()},
                "justificativas": st.session_state.justificativas.get(chave_just_mes, {})
            }
            st.session_state.fechamentos_mes[mes_vigente_sel] = dados_fechamento
            salvar_json(FILE_FECHAMENTOS_MES, st.session_state.fechamentos_mes)
            st.success(f"✅ Fechamento de {mes_vigente_sel} gravado com sucesso! Consulte-o na Aba 3.")
            st.rerun()

    with col_reg2:
        st.markdown("##### 2. Congelar Relatório de Rolling Forecast (RFX)")
        sugestao_nome = f"RF{mes_vigente_idx + 1:02d}"
        col_n, col_b = st.columns([2, 1])
        with col_n:
            nome_versao_rfx = st.text_input("Código do RF:", value=sugestao_nome, help="Exemplo: RF03, RF06, RF09")
        with col_b:
            st.write("")
            st.write("")
            if st.button("💾 Congelar RFX"):
                dados_congelados = {
                    "data_gravacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "mes_corte": mes_vigente_sel,
                    "vol_pb": list(vol_pb_arr),
                    "vol_real_rf": list(vol_real_rf_arr),
                    "unitario_pb": {k: list(v) for k, v in unitario_pb.items()},
                    "unitario_real_rf": {k: list(v) for k, v in unitario_real_rf.items()},
                    "montante_pb": {k: list(v) for k, v in montante_pb.items()},
                    "montante_real_rf": {k: list(v) for k, v in montante_real_rf.items()},
                    "justificativas_mes": st.session_state.justificativas.get(chave_just_mes, {}),
                    "justificativas_ytd": st.session_state.justificativas.get(chave_just_ytd, {}),
                    "justificativas_fy": st.session_state.justificativas.get(chave_just_fy, {})
                }
                st.session_state.historico_rfx[nome_versao_rfx] = dados_congelados
                salvar_json(FILE_HISTORICO_RFX, st.session_state.historico_rfx)
                st.success(f"✅ Versão '{nome_versao_rfx}' gravada com sucesso! Consulte-a na Aba 3.")
                st.rerun()


# =========================================================
# ABA 3: HISTÓRICO DE VERSÕES CONGELADAS (RFX & FECHAMENTOS)
# =========================================================
with tab3:
    st.header("📚 Relatórios de Rolling Forecast e Fechamentos Mensais")

    subtab_a, subtab_b = st.tabs(["📑 Histórico de Rolling Forecast (RFX)", "🔒 Histórico de Fechamentos Mensais"])

    # SUB-ABA A: ROLLING FORECAST
    with subtab_a:
        versoes_disponiveis = list(st.session_state.historico_rfx.keys())
        if not versoes_disponiveis:
            st.info("Nenhuma versão de RFX foi salva até o momento.")
        else:
            col_v_sel, col_v_del = st.columns([3, 1])
            with col_v_sel:
                versao_selecionada = st.selectbox("Selecione a Versão de Rolling Forecast:", versoes_disponiveis, key="sel_rfx_box")
            with col_v_del:
                st.write("")
                st.write("")
                if st.button("🗑️ Excluir RFX"):
                    del st.session_state.historico_rfx[versao_selecionada]
                    salvar_json(FILE_HISTORICO_RFX, st.session_state.historico_rfx)
                    st.warning(f"Versão {versao_selecionada} excluída.")
                    st.rerun()

            dados_v = st.session_state.historico_rfx[versao_selecionada]
            st.success(f"📌 **Relatório {versao_selecionada}** | Data de Congelamento: **{dados_v.get('data_gravacao', '-')}** | Mês de Corte: **{dados_v.get('mes_corte', '-')}**")

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

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric(f"Volume ({versao_selecionada})", f"{sum(v_vol_rf):,.0f} t".replace(",", "."))
            kpi2.metric(f"Montante Total ({versao_selecionada})", fmt_moeda_br(sum(v_tot_m_rf)))
            kpi3.metric(f"Unitário Médio ({versao_selecionada})", fmt_unit_br(sum(v_tot_m_rf) / sum(v_vol_rf)))
            delta_u_rfx = (sum(v_tot_m_rf) / sum(v_vol_rf)) - (sum(v_tot_m_pb) / sum(v_vol_pb))
            kpi4.metric(f"∆ Unitário vs PB", fmt_unit_br(delta_u_rfx), delta=f"{delta_u_rfx:+.2f} R$/t", delta_color="inverse")

            st.markdown("---")
            st.subheader(f"1. Custo Unitário (R$/t) - {versao_selecionada}")
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

    # SUB-ABA B: HISTÓRICO DE FECHAMENTOS MENSAIS
    with subtab_b:
        fechamentos_disponiveis = list(st.session_state.fechamentos_mes.keys())
        if not fechamentos_disponiveis:
            st.info("Nenhum fechamento mensal foi gravado até o momento. Utilize o botão 'Gravar Fechamento Oficial' na Aba 2.")
        else:
            col_f_sel, col_f_del = st.columns([3, 1])
            with col_f_sel:
                mes_fechado_sel = st.selectbox("Selecione o Mês Fechado:", fechamentos_disponiveis, key="sel_fech_mes")
            with col_f_del:
                st.write("")
                st.write("")
                if st.button("🗑️ Excluir Fechamento"):
                    del st.session_state.fechamentos_mes[mes_fechado_sel]
                    salvar_json(FILE_FECHAMENTOS_MES, st.session_state.fechamentos_mes)
                    st.warning(f"Fechamento de {mes_fechado_sel} excluído.")
                    st.rerun()

            dados_fech = st.session_state.fechamentos_mes[mes_fechado_sel]
            st.success(f"📌 **Fechamento Oficial: {mes_fechado_sel}** | Gravado em: **{dados_fech.get('data_fechamento', '-')}**")

            f_u_pb = sum(dados_fech["montante_pb"].values()) / dados_fech["vol_pb"]
            f_u_real = sum(dados_fech["montante_real"].values()) / dados_fech["vol_real"]
            delta_f = f_u_real - f_u_pb
            pct_f = ((f_u_real / f_u_pb) - 1) * 100

            fk1, fk2, fk3, fk4 = st.columns(4)
            fk1.metric("Volume Realizado", f"{dados_fech['vol_real']:,.0f} t".replace(",", "."))
            fk2.metric("Desembolso Real", fmt_moeda_br(sum(dados_fech["montante_real"].values())))
            fk3.metric("Unitário Realizado", fmt_unit_br(f_u_real))
            fk4.metric("Desvio vs PB", fmt_unit_br(delta_f), delta=f"{pct_f:+.2f}%", delta_color="inverse")

            st.markdown("---")
            st.subheader(f"Tabela de Desvios e Justificativas - {mes_fechado_sel}")
            
            linhas_fech = []
            justs_fech = dados_fech.get("justificativas", {})
            for f in dados_fech["unitario_pb"].keys():
                u_p = dados_fech["unitario_pb"][f]
                u_r = dados_fech["unitario_real"][f]
                dado_j = justs_fech.get(f, {})
                txt_just = dado_j.get("texto", "") if isinstance(dado_j, dict) else str(dado_j)
                linhas_fech.append({
                    "Fornecedor": f,
                    "PB (R$/t)": u_p,
                    "Real (R$/t)": u_r,
                    "Desvio (R$/t)": u_r - u_p,
                    "Justificativa Registrada": txt_just if txt_just else "Sem justificativa"
                })
            
            df_fech_tabela = pd.DataFrame(linhas_fech)
            st.dataframe(
                df_fech_tabela.style.format({
                    "PB (R$/t)": fmt_unit_br,
                    "Real (R$/t)": fmt_unit_br,
                    "Desvio (R$/t)": fmt_unit_br
                }),
                use_container_width=True
            )
