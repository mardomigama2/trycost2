import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Gestão de Custo Variável - Imperatriz", layout="wide")

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Inicialização de variáveis de sessão
if "fornecedores" not in st.session_state:
    st.session_state.fornecedores = pd.DataFrame([
        {"Fornecedor": "VLI", "Tipo": "Tarifa (R$/t)", "Valor_Base": 113.40, "Gatilho_Mensal": "Diesel", "Mes_Aniv": 6, "Indice_Aniv": "IPCA"},
        {"Fornecedor": "FTL", "Tipo": "Tarifa (R$/t)", "Valor_Base": 17.80, "Gatilho_Mensal": "Diesel", "Mes_Aniv": 9, "Indice_Aniv": "IPCA"},
        {"Fornecedor": "ASG G5", "Tipo": "Fixo (R$)", "Valor_Base": 104040.00, "Gatilho_Mensal": "Nenhum", "Mes_Aniv": 5, "Indice_Aniv": "INPC"},
        {"Fornecedor": "Manutencao VLI", "Tipo": "Fixo (R$)", "Valor_Base": 167200.00, "Gatilho_Mensal": "Nenhum", "Mes_Aniv": 6, "Indice_Aniv": "IPCA"}
    ])

if "vol_pb" not in st.session_state:
    st.session_state.vol_pb = [151923, 122844, 88439, 136974, 136854, 118845, 138754, 146088, 139023, 147327, 139805, 142788]

if "vol_rf" not in st.session_state:
    st.session_state.vol_rf = list(st.session_state.vol_pb)

if "indices" not in st.session_state:
    st.session_state.indices = pd.DataFrame({
        "Mes": MESES,
        "Diesel_%": [0.5] * 12,
        "IPCA_%": [0.35] * 12,
        "INPC_%": [0.30] * 12,
        "IGPM_%": [0.40] * 12
    })

tab1, tab2 = st.tabs(["⚙️ Aba 1: Inputs & Premissas Base", "📊 Aba 2: Resultados & Bridge"])

# =========================================================
# ABA 1: INPUTS
# =========================================================
with tab1:
    st.header("1. Volumes Operacionais (t)")
    col_v1, col_v2 = st.columns(2)
    
    with col_v1:
        st.subheader("Volume PB (Travado)")
        df_v_pb = pd.DataFrame([st.session_state.vol_pb], columns=MESES, index=["Volume PB"])
        st.dataframe(df_v_pb.style.format("{:,.0f}"))
        
    with col_v2:
        st.subheader("Volume Real + RF (Editável)")
        df_v_rf = pd.DataFrame([st.session_state.vol_rf], columns=MESES, index=["Volume RF"])
        edit_v_rf = st.data_editor(df_v_rf, key="editor_vol_rf")
        st.session_state.vol_rf = [float(edit_v_rf.iloc[0, i]) for i in range(12)]

    st.markdown("---")
    st.header("2. Índices Macroeconômicos (% a.m.)")
    st.caption("Insira as projeções ou variações efetivas de cada indexador para alimentar as paramétricas.")
    st.session_state.indices = st.data_editor(st.session_state.indices, num_rows="fixed")

    st.markdown("---")
    st.header("3. Paramétricas dos Fornecedores")
    st.caption("Cadastre valores base, tipo de custo e regras de reajuste.")
    
    edit_fornec = st.data_editor(
        st.session_state.fornecedores,
        num_rows="dynamic",
        column_config={
            "Tipo": st.column_config.SelectboxColumn("Tipo de Custo", options=["Tarifa (R$/t)", "Fixo (R$)"]),
            "Gatilho_Mensal": st.column_config.SelectboxColumn("Gatilho Mensal", options=["Nenhum", "Diesel", "IPCA", "IGPM"]),
            "Mes_Aniv": st.column_config.NumberColumn("Mês Aniv. (1 a 12)", min_value=1, max_value=12, step=1),
            "Indice_Aniv": st.column_config.SelectboxColumn("Índice Aniversário", options=["IPCA", "INPC", "IGPM", "Nenhum"]),
            "Valor_Base": st.column_config.NumberColumn("Valor Base (R$)", format="R$ %.2f")
        },
        key="editor_fornecedores"
    )
    st.session_state.fornecedores = edit_fornec

# =========================================================
# LÓGICA DE CÁLCULO
# =========================================================
vol_pb_arr = np.array(st.session_state.vol_pb)
vol_rf_arr = np.array(st.session_state.vol_rf)
df_ind = st.session_state.indices

diesel_taxa = df_ind["Diesel_%"].values / 100.0
ipca_taxa = df_ind["IPCA_%"].values / 100.0
inpc_taxa = df_ind["INPC_%"].values / 100.0

# Fator Diesel Acumulado mês a mês
fator_diesel = np.cumprod(1.0 + diesel_taxa)

montante_pb = {}
montante_rf = {}
unitario_pb = {}
unitario_rf = {}

for _, row in st.session_state.fornecedores.iterrows():
    nome = row["Fornecedor"]
    tipo = row["Tipo"]
    base = row["Valor_Base"]
    m_aniv = int(row["Mes_Aniv"]) - 1  # 0-indexed
    idx_aniv = row["Indice_Aniv"]
    
    # Taxa de aniversário calculada
    if idx_aniv == "IPCA":
        taxa_reajuste = np.sum(ipca_taxa)  # acumulado anual estimado
    elif idx_aniv == "INPC":
        taxa_reajuste = np.sum(inpc_taxa)
    else:
        taxa_reajuste = 0.0

    # PB Fixo base
    if tipo == "Tarifa (R$/t)":
        m_pb = base * vol_pb_arr
        u_pb = np.full(12, base)
    else:
        m_pb = np.full(12, base)
        u_pb = m_pb / vol_pb_arr

    montante_pb[nome] = m_pb
    unitario_pb[nome] = u_pb

    # Cálculo RF com paramétrica
    m_rf = np.zeros(12)
    u_rf = np.zeros(12)
    for m in range(12):
        fator_mensal = fator_diesel[m] if row["Gatilho_Mensal"] == "Diesel" else 1.0
        fator_aniv = (1.0 + taxa_reajuste) if m >= m_aniv else 1.0
        
        if tipo == "Tarifa (R$/t)":
            tarifa_m = base * fator_mensal * fator_aniv
            u_rf[m] = tarifa_m
            m_rf[m] = tarifa_m * vol_rf_arr[m]
        else:
            custo_fixo_m = base * fator_aniv
            m_rf[m] = custo_fixo_m
            u_rf[m] = custo_fixo_m / vol_rf_arr[m] if vol_rf_arr[m] > 0 else 0.0

    montante_rf[nome] = m_rf
    unitario_rf[nome] = u_rf

# =========================================================
# ABA 2: RESULTADOS & BRIDGE
# =========================================================
with tab2:
    st.header("Resultados Consolidados: PB vs Real + RF")

    # Consolidação dos Totais
    total_m_pb = sum(montante_pb.values())
    total_m_rf = sum(montante_rf.values())
    total_u_pb = total_m_pb / vol_pb_arr
    total_u_rf = total_m_rf / vol_rf_arr

    st.subheader("1. Tabela Comparativa em Montante (R$)")
    df_montante = pd.DataFrame(index=[f"{f} (PB)" for f in montante_pb.keys()] + [f"{f} (RF)" for f in montante_rf.keys()] + ["TOTAL PB", "TOTAL RF"])
    for i, m in enumerate(MESES):
        vals = [montante_pb[f][i] for f in montante_pb.keys()] + [montante_rf[f][i] for f in montante_rf.keys()] + [total_m_pb[i], total_m_rf[i]]
        df_montante[m] = vals
    df_montante["Total Ano"] = df_montante.sum(axis=1)
    st.dataframe(df_montante.style.format("R$ {:,.0f}"), use_container_width=True)

    st.subheader("2. Tabela Comparativa em Unitário (R$/t)")
    df_unit = pd.DataFrame(index=[f"{f} (PB)" for f in unitario_pb.keys()] + [f"{f} (RF)" for f in unitario_rf.keys()] + ["UNITÁRIO TOTAL PB", "UNITÁRIO TOTAL RF"])
    for i, m in enumerate(MESES):
        vals = [unitario_pb[f][i] for f in unitario_pb.keys()] + [unitario_rf[f][i] for f in unitario_rf.keys()] + [total_u_pb[i], total_u_rf[i]]
        df_unit[m] = vals
    df_unit["Média Ponderada"] = [
        sum(montante_pb[f])/sum(vol_pb_arr) for f in montante_pb.keys()
    ] + [
        sum(montante_rf[f])/sum(vol_rf_arr) for f in montante_rf.keys()
    ] + [sum(total_m_pb)/sum(vol_pb_arr), sum(total_m_rf)/sum(vol_rf_arr)]
    st.dataframe(df_unit.style.format("R$ {:.2f}"), use_container_width=True)

    st.markdown("---")
    st.subheader("3. Gráfico Waterfall: Bridge de Impacto no Custo Unitário Anual")
    
    unit_pb_ano = sum(total_m_pb) / sum(vol_pb_arr)
    unit_rf_ano = sum(total_m_rf) / sum(vol_rf_arr)
    
    # Deltas unitários por fornecedor
    x_labels = ["PB Base"]
    y_vals = [unit_pb_ano]
    measures = ["absolute"]

    for f in montante_pb.keys():
        u_f_pb = sum(montante_pb[f]) / sum(vol_pb_arr)
        u_f_rf = sum(montante_rf[f]) / sum(vol_rf_arr)
        delta_f = u_f_rf - u_f_pb
        x_labels.append(f)
        y_vals.append(delta_f)
        measures.append("relative")

    x_labels.append("RF Final")
    y_vals.append(0)
    measures.append("total")

    fig = go.Figure(go.Waterfall(
        name="Bridge Unitário",
        orientation="v",
        measure=measures,
        x=x_labels,
        textposition="outside",
        text=[f"{v:+.2f}" if m == "relative" else f"{v:.2f}" for v, m in zip(y_vals, measures)],
        y=y_vals,
        connector={"line": {"color": "#666"}},
        increasing={"marker": {"color": "#E53935"}},
        decreasing={"marker": {"color": "#43A047"}},
        totals={"marker": {"color": "#1E88E5"}}
    ))
    fig.update_layout(title="Bridge PB vs RF: Custo Unitário Ponderado (R$/t)", yaxis_title="R$/t", height=500)
    st.plotly_chart(fig, use_container_width=True)
