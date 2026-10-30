import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Gestão de Custo Variável - Imperatriz", layout="wide")

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Reconhecimento automático do mês atual (0 = Jan, ..., 11 = Dez)
mes_atual_sistema = datetime.today().month - 1

# =========================================================
# INICIALIZAÇÃO DE SESSÃO
# =========================================================
if "fornecedores" not in st.session_state:
    st.session_state.fornecedores = pd.DataFrame([
        {"Fornecedor": "VLI", "Tipo": "Tarifa (R$/t)", "Valor_Base": 113.40, "Gatilho_Mensal": "Diesel", "Mes_Aniv": 6, "Indice_Aniv": "IPCA"},
        {"Fornecedor": "FTL", "Tipo": "Tarifa (R$/t)", "Valor_Base": 17.80, "Gatilho_Mensal": "Diesel", "Mes_Aniv": 9, "Indice_Aniv": "IPCA"},
        {"Fornecedor": "ASG G5", "Tipo": "Fixo (R$)", "Valor_Base": 104040.00, "Gatilho_Mensal": "Nenhum", "Mes_Aniv": 5, "Indice_Aniv": "INPC"},
        {"Fornecedor": "Manutenção VLI", "Tipo": "Fixo (R$)", "Valor_Base": 167200.00, "Gatilho_Mensal": "Nenhum", "Mes_Aniv": 6, "Indice_Aniv": "IPCA"}
    ])

if "vol_pb" not in st.session_state:
    st.session_state.vol_pb = [151923, 122844, 88439, 136974, 136854, 118845, 138754, 146088, 139023, 147327, 139805, 142788]

if "vol_real_rf" not in st.session_state:
    st.session_state.vol_real_rf = list(st.session_state.vol_pb)

if "pb_desbloqueado" not in st.session_state:
    st.session_state.pb_desbloqueado = False

if "indices" not in st.session_state:
    st.session_state.indices = pd.DataFrame({
        "Mês": MESES,
        "Diesel_%": [0.50] * 12,
        "IPCA_%": [0.35] * 12,
        "INPC_%": [0.30] * 12,
        "IGPM_%": [0.40] * 12
    })

# Armazenamento dos valores customizados/editados de Real+RF por fornecedor
if "matriz_real_rf_custom" not in st.session_state:
    st.session_state.matriz_real_rf_custom = {}

tab1, tab2 = st.tabs(["⚙️ Aba 1: Inputs & Premissas Base", "📊 Aba 2: Resultados & Bridges"])

# =========================================================
# ABA 1: INPUTS
# =========================================================
with tab1:
    st.header("1. Status do Período e Volumes Operacionais (t)")
    
    col_st1, col_st2 = st.columns([2, 4])
    with col_st1:
        st.info(f"📅 **Mês Vigente do Sistema:** {MESES[mes_atual_sistema]}")
    with col_st2:
        mes_vigente_sel = st.selectbox(
            "Mês Vigente Operacional:",
            MESES,
            index=mes_atual_sistema,
            help="O mês selecionado fica destacado em azul claro. Os meses anteriores ficam em verde (Realizados)."
        )
    mes_vigente_idx = MESES.index(mes_vigente_sel)

    # Volume PB (Em Cima)
    st.subheader("Volume PB (Plano Básico)")
    if not st.session_state.pb_desbloqueado:
        df_v_pb = pd.DataFrame([st.session_state.vol_pb], columns=MESES, index=["Volume PB"])
        st.dataframe(df_v_pb.style.format("{:,.0f}"), use_container_width=True)
        
        with st.expander("🔒 Desbloquear PB para edição ou substituição"):
            col_pwd, col_btn = st.columns([3, 1])
            with col_pwd:
                senha_pb = st.text_input("Senha de autorização:", type="password", key="pwd_pb")
            with col_btn:
                st.write("")
                st.write("")
                if st.button("Destravar PB"):
                    if senha_pb == "mudar123":
                        st.session_state.pb_desbloqueado = True
                        st.success("PB liberado!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta!")
    else:
        st.warning("⚠️ Edição de Volume PB Habilitada")
        arq_pb = st.file_uploader("Carregar planilha para novo PB (Excel/CSV):", type=["xlsx", "csv"], key="upload_pb")
        if arq_pb is not None:
            try:
                df_up = pd.read_csv(arq_pb) if arq_pb.name.endswith(".csv") else pd.read_excel(arq_pb)
                nums = df_up.select_dtypes(include=[np.number]).iloc[0, :12].tolist()
                if len(nums) == 12:
                    st.session_state.vol_pb = [float(x) for x in nums]
                    st.success("Volumes carregados do arquivo com sucesso!")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
        
        df_v_pb_edit = pd.DataFrame([st.session_state.vol_pb], columns=MESES, index=["Volume PB"])
        edit_pb = st.data_editor(df_v_pb_edit, key="edit_pb_ativo", use_container_width=True)
        
        col_s1, col_s2 = st.columns([1, 4])
        with col_s1:
            if st.button("💾 Confirmar e Travar PB", type="primary"):
                st.session_state.vol_pb = [float(edit_pb.iloc[0, i]) for i in range(12)]
                st.session_state.pb_desbloqueado = False
                st.success("PB salvo e travado.")
                st.rerun()
        with col_s2:
            if st.button("Cancelar"):
                st.session_state.pb_desbloqueado = False
                st.rerun()

    # Volume Real + RF (Embaixo)
    st.subheader("Volume Real+RF (Editável / Copiar e Colar)")
    df_v_real_rf = pd.DataFrame([st.session_state.vol_real_rf], columns=MESES, index=["Volume Real+RF"])
    edit_v_real_rf = st.data_editor(df_v_real_rf, key="editor_vol_real_rf", use_container_width=True)
    st.session_state.vol_real_rf = [float(edit_v_real_rf.iloc[0, i]) for i in range(12)]

    st.markdown("---")
    
    # 2. Índices Macroeconômicos
    st.header("2. Índices Macroeconômicos (% ao mês)")
    st.session_state.indices = st.data_editor(
        st.session_state.indices,
        num_rows="fixed",
        height=180,
        use_container_width=True,
        column_config={
            "Mês": st.column_config.TextColumn("Mês", disabled=True, width="small"),
            "Diesel_%": st.column_config.NumberColumn("Diesel (%)", format="%.2f%%", step=0.05, width="small"),
            "IPCA_%": st.column_config.NumberColumn("IPCA (%)", format="%.2f%%", step=0.05, width="small"),
            "INPC_%": st.column_config.NumberColumn("INPC (%)", format="%.2f%%", step=0.05, width="small"),
            "IGPM_%": st.column_config.NumberColumn("IGPM (%)", format="%.2f%%", step=0.05, width="small"),
        }
    )

    st.markdown("---")
    
    # 3. Fornecedores
    st.header("3. Cadastro de Fornecedores & Paramétricas")
    st.caption("ℹ️ Qualquer novo fornecedor adicionado com o botão '+' refletirá imediatamente nas tabelas da Aba 2. Índices e datas de aniversário são opcionais.")
    
    edit_fornec = st.data_editor(
        st.session_state.fornecedores,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Fornecedor": st.column_config.TextColumn("Fornecedor", required=True),
            "Tipo": st.column_config.SelectboxColumn("Tipo de Custo", options=["Tarifa (R$/t)", "Fixo (R$)"], required=True),
            "Valor_Base": st.column_config.NumberColumn("Valor Base (R$)", format="R$ %.2f", required=True),
            "Gatilho_Mensal": st.column_config.SelectboxColumn("Gatilho Mensal", options=["Nenhum", "Diesel", "IPCA", "INPC", "IGPM"]),
            "Mes_Aniv": st.column_config.NumberColumn("Mês Aniv. (1-12)", min_value=1, max_value=12, step=1),
            "Indice_Aniv": st.column_config.SelectboxColumn("Índice Aniversário", options=["Nenhum", "IPCA", "INPC", "IGPM"])
        },
        key="editor_fornecedores"
    )
    st.session_state.fornecedores = edit_fornec


# =========================================================
# MOTOR DE CÁLCULO DINÂMICO
# =========================================================
vol_pb_arr = np.array(st.session_state.vol_pb, dtype=float)
vol_real_rf_arr = np.array(st.session_state.vol_real_rf, dtype=float)
df_ind = st.session_state.indices

diesel_taxa = df_ind["Diesel_%"].values / 100.0
ipca_taxa = df_ind["IPCA_%"].values / 100.0
inpc_taxa = df_ind["INPC_%"].values / 100.0
fator_diesel = np.cumprod(1.0 + diesel_taxa)

montante_pb = {}
montante_real_rf_calculado = {}
unitario_pb = {}

for _, row in st.session_state.fornecedores.iterrows():
    nome = str(row["Fornecedor"]).strip()
    if not nome or pd.isna(nome):
        continue
        
    tipo = str(row.get("Tipo", "Tarifa (R$/t)"))
    base = float(row.get("Valor_Base", 0.0))
    gatilho = str(row.get("Gatilho_Mensal", "Nenhum"))
    
    # Aniversário é opcional
    mes_aniv_raw = row.get("Mes_Aniv")
    m_aniv = (int(mes_aniv_raw) - 1) if pd.notna(mes_aniv_raw) and mes_aniv_raw > 0 else 99
    idx_aniv = str(row.get("Indice_Aniv", "Nenhum"))
    
    taxa_aniv = 0.0
    if idx_aniv == "IPCA":
        taxa_aniv = np.sum(ipca_taxa)
    elif idx_aniv == "INPC":
        taxa_aniv = np.sum(inpc_taxa)
    elif idx_aniv == "IGPM":
        taxa_aniv = np.sum(df_ind["IGPM_%"].values / 100.0)

    # 1. PB Base
    if tipo == "Tarifa (R$/t)":
        m_pb = base * vol_pb_arr
        u_pb = np.full(12, base)
    else:
        m_pb = np.full(12, base)
        u_pb = m_pb / vol_pb_arr

    montante_pb[nome] = m_pb
    unitario_pb[nome] = u_pb

    # 2. Projeção Base Real+RF:
    # Regra: Novo valor base só impacta a partir do mês vigente em diante (m >= mes_vigente_idx).
    m_calc = np.zeros(12)
    for m in range(12):
        fator_g = fator_diesel[m] if gatilho == "Diesel" else 1.0
        fator_a = (1.0 + taxa_aniv) if m >= m_aniv else 1.0
        
        if tipo == "Tarifa (R$/t)":
            tarifa_m = base * fator_g * fator_a
            m_calc[m] = tarifa_m * vol_real_rf_arr[m]
        else:
            custo_fixo_m = base * fator_a
            m_calc[m] = custo_fixo_m

    montante_real_rf_calculado[nome] = m_calc


# =========================================================
# ABA 2: RESULTADOS & BRIDGES
# =========================================================
with tab2:
    st.header("Resultados Consolidados & Bridges")
    
    st.markdown(
        f"""
        <div style='display: flex; gap: 20px; align-items: center; margin-bottom: 15px;'>
            <span>🟢 <b>Verde Claro:</b> Meses Realizados (anteriores a {mes_vigente_sel})</span>
            <span>🔵 <b>Azul Claro:</b> Mês Vigente Atual ({mes_vigente_sel})</span>
            <span>⚪ <b>Branco:</b> Projeções Futuras (Real+RF)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Bloco Editável do Real+RF por Fornecedor
    with st.expander("✏️ Clique aqui para imputar / editar valores mensais de Real+RF", expanded=False):
        st.write("Ajuste ou cole os valores mensais realizados/projetados diretamente abaixo:")
        
        # Monta DataFrame editável com base calculada ou customizada existente
        df_editor_input = pd.DataFrame(index=list(montante_pb.keys()), columns=MESES)
        for f in montante_pb.keys():
            if f in st.session_state.matriz_real_rf_custom:
                df_editor_input.loc[f] = st.session_state.matriz_real_rf_custom[f]
            else:
                df_editor_input.loc[f] = montante_real_rf_calculado[f]

        editado_rf = st.data_editor(df_editor_input.astype(float), use_container_width=True, key="editor_matriz_rf")
        
        # Salva alterações na sessão
        for f in editado_rf.index:
            st.session_state.matriz_real_rf_custom[f] = editado_rf.loc[f].values.astype(float)

    # Obtenção final dos montantes de Real+RF (calculado ou editado)
    montante_real_rf = {}
    unitario_real_rf = {}
    for f in montante_pb.keys():
        if f in st.session_state.matriz_real_rf_custom:
            m_rf_val = np.array(st.session_state.matriz_real_rf_custom[f], dtype=float)
        else:
            m_rf_val = montante_real_rf_calculado[f]
        
        montante_real_rf[f] = m_rf_val
        unitario_real_rf[f] = np.where(vol_real_rf_arr > 0, m_rf_val / vol_real_rf_arr, 0.0)

    # Totais consolidados
    total_m_pb = sum(montante_pb.values())
    total_m_real_rf = sum(montante_real_rf.values())
    total_u_pb = total_m_pb / vol_pb_arr
    total_u_real_rf = np.where(vol_real_rf_arr > 0, total_m_real_rf / vol_real_rf_arr, 0.0)

    # Ordenação das linhas
    ordem_linhas = ["TOTAL PB", "TOTAL Real+RF"]
    for f in montante_pb.keys():
        ordem_linhas.append(f"{f} (PB)")
        ordem_linhas.append(f"{f} (Real+RF)")

    # Função para estilização: Passado = Verde Claro, Vigente = Azul Claro
    def estilizar_colunas_periodo(data):
        styles = pd.DataFrame("", index=data.index, columns=data.columns)
        for i, col in enumerate(MESES):
            if col in styles.columns:
                if i < mes_vigente_idx:
                    styles[col] = "background-color: #E8F5E9; font-weight: 500;"  # Verde suave
                elif i == mes_vigente_idx:
                    styles[col] = "background-color: #E3F2FD; font-weight: bold; border-left: 2px solid #2196F3; border-right: 2px solid #2196F3;"  # Azul suave
        return styles

    # 1. Tabela Montante (R$)
    st.subheader("1. Tabela Comparativa em Montante (R$)")
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
    st_styled_m = df_tabela_m.style.apply(estilizar_colunas_periodo, axis=None).format("R$ {:,.0f}")
    st.dataframe(st_styled_m, use_container_width=True)

    # 2. Tabela Unitário (R$/t)
    st.subheader("2. Tabela Comparativa em Unitário (R$/t)")
    dados_u = {}
    for l in ordem_linhas:
        if l == "TOTAL PB":
            dados_u[l] = list(total_u_pb) + [sum(total_m_pb) / sum(vol_pb_arr)]
        elif l == "TOTAL Real+RF":
            dados_u[l] = list(total_u_real_rf) + [sum(total_m_real_rf) / sum(vol_real_rf_arr)]
        elif "(PB)" in l:
            fn = l.replace(" (PB)", "")
            dados_u[l] = list(unitario_pb[fn]) + [sum(montante_pb[fn]) / sum(vol_pb_arr)]
        elif "(Real+RF)" in l:
            fn = l.replace(" (Real+RF)", "")
            dados_u[l] = list(unitario_real_rf[fn]) + [sum(montante_real_rf[fn]) / sum(vol_real_rf_arr)]

    df_tabela_u = pd.DataFrame.from_dict(dados_u, orient="index", columns=MESES + ["Média Ponderada"])
    st_styled_u = df_tabela_u.style.apply(estilizar_colunas_periodo, axis=None).format("R$ {:.2f}")
    st.dataframe(st_styled_u, use_container_width=True)

    st.markdown("---")
    
    # 3. Bridges Waterfall
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

        textos = [f"{v:+.2f}" if m == "relative" else f"{v:.2f}" for v, m in zip(y, measures)]

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
            height=420,
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
