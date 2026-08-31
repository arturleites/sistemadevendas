import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime

# CONFIGURAÇÃO DE INTERFACE PROFISSIONAL
st.set_page_config(page_title="ERP Business Pro", layout="wide", initial_sidebar_state="expanded")

# TEMA DARK MODE VIA CSS
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111; border-right: 1px solid #333; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div.stButton > button:first-child { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# CONEXÃO BANCO
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- NAVEGAÇÃO LATERAL ---
with st.sidebar:
    st.title("🚀 ERP Pro")
    st.subheader("Gestão Empresarial")
    menu = st.radio("Módulos", 
        ["📊 Dashboard", "🛒 PDV (Vendas)", "📦 Produtos", "📋 Estoque", "👥 Clientes", "💰 Financeiro", "⚙️ Configurações"])
    st.divider()
    st.caption("Versão 2.0 - Usuário: Admin")

# --- LÓGICA DE DASHBOARD (DADOS REAIS) ---
if menu == "📊 Dashboard":
    st.header("📊 Painel de Controle")
    
    # Busca dados reais para os indicadores
    try:
        vendas_db = supabase.table("vendas").select("*").execute().data
        produtos_db = supabase.table("produtos").select("*").execute().data
        financeiro_db = supabase.table("financeiro").select("*").execute().data
        
        df_v = pd.DataFrame(vendas_db)
        df_p = pd.DataFrame(produtos_db)
        
        # Indicadores Topo
        c1, c2, c3, c4 = st.columns(4)
        if not df_v.empty:
            c1.metric("Vendas Totais", f"R$ {df_v['total_liquido'].sum():,.2f}")
            c2.metric("Nº de Pedidos", len(df_v))
            c3.metric("Ticket Médio", f"R$ {df_v['total_liquido'].mean():,.2f}")
        else:
            c1.metric("Vendas Totais", "R$ 0,00")
            c2.metric("Nº de Pedidos", "0")
            
        # Gráfico de Vendas (Simulação por data)
        if not df_v.empty:
            df_v['data_venda'] = pd.to_datetime(df_v['data_venda'])
            vendas_dia = df_v.groupby(df_v['data_venda'].dt.date)['total_liquido'].sum().reset_index()
            fig = px.line(vendas_dia, x='data_venda', y='total_liquido', title="Faturamento Diário", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro ao carregar Dashboard: {e}")

# --- MÓDULO DE PRODUTOS (COMPLETO) ---
elif menu == "📦 Produtos":
    st.header("📦 Gestão de Produtos")
    tab1, tab2, tab3 = st.tabs(["Lista de Produtos", "Cadastrar Novo", "Categorias"])

    with st.tab2:
        with st.form("form_prod", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome do Produto*")
            sku = col2.text_input("SKU / Código Interno")
            cat = col1.selectbox("Categoria", ["Eletrônicos", "Bikes", "Games", "Acessórios", "Outros"])
            p_compra = col2.number_input("Preço de Compra (R$)", min_value=0.0)
            c_extra = col1.number_input("Custos Extras (R$)", min_value=0.0)
            p_venda = col2.number_input("Preço de Venda (R$)", min_value=0.0)
            estoque = col1.number_input("Estoque Inicial", min_value=0)
            
            # Cálculos automáticos
            custo_real = p_compra + c_extra
            lucro_est = p_venda - custo_real
            margem = (lucro_est / p_venda * 100) if p_venda > 0 else 0
            
            st.info(f"💡 Custo Real: R$ {custo_real:.2f} | Lucro Unitário: R$ {lucro_est:.2f} | Margem: {margem:.1f}%")
            
            if st.form_submit_button("CADASTRAR PRODUTO"):
                if nome and p_venda > 0:
                    data = {
                        "nome": nome, "sku": sku, "categoria": cat,
                        "preco_compra": p_compra, "custo_reparo": c_extra,
                        "preco_venda": p_venda, "estoque_atual": estoque
                    }
                    supabase.table("produtos").insert(data).execute()
                    st.success("Produto cadastrado e estoque atualizado!")
                else:
                    st.error("Preencha os campos obrigatórios.")

    with st.tab1:
        prods = supabase.table("produtos").select("*").execute().data
        if prods:
            df_p = pd.DataFrame(prods)
            st.dataframe(df_p[["id", "nome", "categoria", "estoque_atual", "preco_venda", "status"]], use_container_width=True)
        else:
            st.info("Nenhum produto cadastrado.")

# --- MÓDULO DE VENDAS (PDV MULTI-ITEM) ---
elif menu == "🛒 PDV (Vendas)":
    st.header("🛒 Ponto de Venda")
    
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []

    col_prod, col_carrinho = st.columns([1, 1])

    with col_prod:
        st.subheader("Seleção de Itens")
        prods_db = supabase.table("produtos").select("*").eq("status", "Ativo").gt("estoque_atual", 0).execute().data
        if prods_db:
            df_pdv = pd.DataFrame(prods_db)
            item_sel = st.selectbox("Buscar Produto", df_pdv['nome'].tolist())
            qtd = st.number_input("Quantidade", min_value=1, value=1)
            
            if st.button("➕ Adicionar ao Carrinho"):
                p_info = next(item for item in prods_db if item["nome"] == item_sel)
                st.session_state.carrinho.append({
                    "id": p_info['id'], "nome": p_info['nome'], 
                    "preco": p_info['preco_venda'], "qtd": qtd,
                    "subtotal": p_info['preco_venda'] * qtd
                })
        else:
            st.warning("Estoque zerado. Cadastre produtos primeiro.")

    with col_carrinho:
        st.subheader("Resumo do Pedido")
        if st.session_state.carrinho:
            df_car = pd.DataFrame(st.session_state.carrinho)
            st.table(df_car[["nome", "qtd", "subtotal"]])
            
            total = df_car['subtotal'].sum()
            st.write(f"### TOTAL: R$ {total:,.2f}")
            
            pagamento = st.selectbox("Forma de Pagamento", ["Pix", "Cartão de Crédito", "Dinheiro"])
            
            if st.button("🏁 FINALIZAR VENDA"):
                # 1. Registrar a Venda
                venda_res = supabase.table("vendas").insert({
                    "total_bruto": total, "total_liquido": total, "forma_pagamento": pagamento
                }).execute()
                v_id = venda_res.data[0]['id']
                
                # 2. Registrar Itens e Baixar Estoque
                for item in st.session_state.carrinho:
                    supabase.table("itens_venda").insert({
                        "venda_id": v_id, "produto_id": item['id'], 
                        "quantidade": item['qtd'], "preco_unitario": item['preco']
                    }).execute()
                    # Baixa estoque
                    supabase.rpc('debitar_estoque', {'p_id': item['id'], 'qtd_venda': item['qtd']}).execute()
                
                # 3. Registrar no Financeiro
                supabase.table("financeiro").insert({
                    "tipo": "Receita", "categoria": "Venda", "valor": total, "venda_id": v_id
                }).execute()

                st.session_state.carrinho = []
                st.balloons()
                st.success("Venda finalizada e estoque atualizado!")
        else:
            st.info("Carrinho vazio.")

# Módulos Restantes (Clientes, Estoque, Financeiro) seguiriam o mesmo padrão...
