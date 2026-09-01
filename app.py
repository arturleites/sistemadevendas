import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="ERP Business Pro", layout="wide", initial_sidebar_state="expanded")

# Estilo visual (Dark Mode)
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111; border-right: 1px solid #333; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO COM O BANCO
try:
    URL = st.secrets["SUPABASE_URL"].strip().rstrip("/")
    KEY = st.secrets["SUPABASE_KEY"].strip()
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error(f"Erro na conexão: Verifique os Secrets no Streamlit. {e}")
    st.stop()

# 3. MENU LATERAL
with st.sidebar:
    st.title("🚀 ERP Pro")
    menu = st.sidebar.radio("Módulos", 
        ["📊 Dashboard", "🛒 PDV (Vendas)", "📦 Produtos", "📋 Estoque", "💰 Financeiro"])
    st.divider()
    st.caption("Versão 2.0 - Usuário: Admin")

# --- MÓDULO: DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Painel de Controle")
    try:
        vendas_db = supabase.table("vendas").select("*").execute().data
        if vendas_db:
            df_v = pd.DataFrame(vendas_db)
            c1, c2, c3 = st.columns(3)
            c1.metric("Vendas Totais", f"R$ {df_v['total_liquido'].sum():,.2f}")
            c2.metric("Nº de Pedidos", len(df_v))
            c3.metric("Ticket Médio", f"R$ {df_v['total_liquido'].mean():,.2f}")
            
            df_v['data_venda'] = pd.to_datetime(df_v['data_venda'])
            vendas_dia = df_v.groupby(df_v['data_venda'].dt.date)['total_liquido'].sum().reset_index()
            fig = px.line(vendas_dia, x='data_venda', y='total_liquido', title="Evolução de Vendas", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aguardando primeiras vendas para gerar gráficos.")
    except:
        st.info("Inicie o sistema cadastrando produtos e realizando vendas.")

# --- MÓDULO: PRODUTOS ---
elif menu == "📦 Produtos":
    st.header("📦 Gestão de Produtos")
    with st.form("form_prod", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Produto*")
        cat = col1.selectbox("Categoria", ["Eletrônicos", "Bikes", "Games", "Casa", "Outros"])
        p_compra = col2.number_input("Preço de Compra (R$)", min_value=0.0)
        p_venda = col2.number_input("Preço de Venda (R$)", min_value=0.0)
        estoque = col1.number_input("Estoque Inicial", min_value=0)
        
        if st.form_submit_button("CADASTRAR PRODUTO"):
            if nome and p_venda > 0:
                supabase.table("produtos").insert({
                    "nome": nome, "categoria": cat, "preco_compra": p_compra,
                    "preco_venda": p_venda, "estoque_atual": estoque, "status": "Ativo"
                }).execute()
                st.success(f"Produto {nome} cadastrado!")
            else:
                st.error("Nome e Preço de Venda são obrigatórios.")

# --- MÓDULO: PDV (VENDAS) ---
elif menu == "🛒 PDV (Vendas)":
    st.header("🛒 Ponto de Venda")
    if 'carrinho' not in st.session_state: st.session_state.carrinho = []

    try:
        # Busca produtos e filtra no Python para evitar erros de API
        res = supabase.table("produtos").select("*").execute()
        prods_db = res.data if res.data else []
        disponiveis = [p for p in prods_db if p.get('status') == 'Ativo' and p.get('estoque_atual', 0) > 0]

        col1, col2 = st.columns([1, 1])
        with col1:
            if disponiveis:
                nomes = [p['nome'] for p in disponiveis]
                sel = st.selectbox("Escolha o Produto", nomes)
                qtd = st.number_input("Qtd", min_value=1, value=1)
                if st.button("➕ Adicionar"):
                    p_info = next(p for p in disponiveis if p['nome'] == sel)
                    st.session_state.carrinho.append({
                        "id": p_info['id'], "nome": p_info['nome'], 
                        "preco": p_info['preco_venda'], "qtd": qtd, "subtotal": p_info['preco_venda'] * qtd
                    })
                    st.rerun()
            else:
                st.warning("Sem produtos no estoque.")

        with col2:
            if st.session_state.carrinho:
                df_c = pd.DataFrame(st.session_state.carrinho)
                st.table(df_c[["nome", "qtd", "subtotal"]])
                total = df_c['subtotal'].sum()
                st.write(f"### TOTAL: R$ {total:,.2f}")
                if st.button("🏁 FINALIZAR VENDA"):
                    venda = supabase.table("vendas").insert({"total_bruto": total, "total_liquido": total, "forma_pagamento": "Pix"}).execute()
                    v_id = venda.data[0]['id']
                    for item in st.session_state.carrinho:
                        supabase.table("itens_venda").insert({"venda_id": v_id, "produto_id": item['id'], "quantidade": item['qtd'], "preco_unitario": item['preco']}).execute()
                        # Baixa de estoque simplificada
                        nova_qtd = next(p['estoque_atual'] for p in disponiveis if p['id'] == item['id']) - item['qtd']
                        supabase.table("produtos").update({"estoque_atual": nova_qtd}).eq("id", item['id']).execute()
                    
                    st.session_state.carrinho = []
                    st.success("Venda Finalizada!")
                    st.rerun()
            else:
                st.info("Carrinho vazio.")
    except Exception as e:
        st.error(f"Erro no PDV: {e}")

# --- MÓDULO: ESTOQUE ---
elif menu == "📋 Estoque":
    st.header("📋 Controle de Estoque")
    try:
        itens = supabase.table("produtos").select("*").execute().data
        if itens:
            df_e = pd.DataFrame(itens)
            st.dataframe(df_e[["nome", "categoria", "estoque_atual", "preco_compra", "preco_venda"]], use_container_width=True)
        else:
            st.info("Nenhum item no estoque.")
    except Exception as e:
        st.error(f"Erro: {e}")

# --- MÓDULO: FINANCEIRO ---
elif menu == "💰 Financeiro":
    st.header("💰 Fluxo de Caixa")
    try:
        vendas = supabase.table("vendas").select("*").execute().data
        if vendas:
            df_f = pd.DataFrame(vendas)
            st.metric("Total em Caixa (Vendas)", f"R$ {df_f['total_liquido'].sum():,.2f}")
            st.write("### Histórico de Entradas")
            st.dataframe(df_f[["id", "data_venda", "total_liquido", "forma_pagamento"]], use_container_width=True)
        else:
            st.info("Nenhuma movimentação financeira.")
    except:
        st.error("Erro ao carregar financeiro.")
