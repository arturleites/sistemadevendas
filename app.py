import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime

# CONFIGURAÇÃO DO SISTEMA
st.set_page_config(page_title="ERP BUSINESS PRO", layout="wide", initial_sidebar_state="expanded")

# ESTILO DARK MODE PROFISSIONAL
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #111; border-right: 1px solid #333; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div.stButton > button { width: 100%; border-radius: 5px; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# CONEXÃO
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🚀 ERP PRO v3")
    menu = st.radio("MÓDULOS", [
        "📊 Dashboard", "🛒 Vendas (PDV)", "📦 Produtos", 
        "📋 Estoque", "👥 Clientes", "💰 Financeiro", "⚙️ Configurações"
    ])
    st.divider()
    st.info(f"Usuário: Administrador\nData: {datetime.now().strftime('%d/%m/%Y')}")

# --- FUNÇÕES DE APOIO ---
def get_data(table):
    return supabase.table(table).select("*").execute().data

# ==========================================
# MÓDULO: DASHBOARD
# ==========================================
if menu == "📊 Dashboard":
    st.header("📊 Resumo Executivo")
    try:
        vendas = get_data("vendas")
        df_v = pd.DataFrame(vendas)
        
        c1, c2, c3, c4 = st.columns(4)
        if not df_v.empty:
            c1.metric("Faturamento Total", f"R$ {df_v['total_liquido'].sum():,.2f}")
            c2.metric("Total de Vendas", len(df_v))
            c3.metric("Ticket Médio", f"R$ {df_v['total_liquido'].mean():,.2f}")
            
            # Gráfico de Vendas
            df_v['data_venda'] = pd.to_datetime(df_v['data_venda'])
            vendas_dia = df_v.groupby(df_v['data_venda'].dt.date)['total_liquido'].sum().reset_index()
            fig = px.area(vendas_dia, x='data_venda', y='total_liquido', title="Evolução Diária", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Inicie suas operações para visualizar os dados.")
    except: st.warning("Erro ao carregar indicadores.")

# ==========================================
# MÓDULO: PRODUTOS
# ==========================================
elif menu == "📦 Produtos":
    st.header("📦 Cadastro de Produtos")
    with st.form("form_prod"):
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome do Produto")
        sku = c2.text_input("SKU/Código")
        cat = c3.selectbox("Categoria", ["Bikes", "Eletrônicos", "Games", "Outros"])
        
        c4, c5, c6 = st.columns(3)
        p_compra = c4.number_input("Custo de Compra", 0.0)
        p_venda = c5.number_input("Preço de Venda", 0.0)
        estoque = c6.number_input("Estoque Inicial", 0)
        
        if st.form_submit_button("SALVAR PRODUTO"):
            supabase.table("produtos").insert({
                "nome": nome, "sku": sku, "categoria": cat,
                "preco_compra": p_compra, "preco_venda": p_venda, "estoque_atual": estoque
            }).execute()
            st.success("Produto salvo!")

# ==========================================
# MÓDULO: VENDAS (PDV)
# ==========================================
elif menu == "🛒 Vendas (PDV)":
    st.header("🛒 Ponto de Venda")
    if 'cart' not in st.session_state: st.session_state.cart = []
    
    prods = get_data("produtos")
    clis = get_data("clientes")
    
    col_l, col_r = st.columns([1.5, 1])
    
    with col_l:
        st.subheader("Seleção de Itens")
        if prods:
            df_p = pd.DataFrame(prods)
            # Filtro de busca
            busca = st.text_input("🔍 Pesquisar produto")
            df_filtrado = df_p[df_p['nome'].str.contains(busca, case=False)]
            
            sel = st.selectbox("Selecione o item", df_filtrado['nome'].tolist())
            qtd = st.number_input("Qtd", 1, 100)
            if st.button("➕ ADICIONAR AO CARRINHO"):
                item = next(p for p in prods if p['nome'] == sel)
                st.session_state.cart.append({
                    "id": item['id'], "nome": item['nome'], 
                    "preco": item['preco_venda'], "qtd": qtd, "sub": item['preco_venda'] * qtd
                })
                st.rerun()

    with col_r:
        st.subheader("Carrinho")
        if st.session_state.cart:
            df_c = pd.DataFrame(st.session_state.cart)
            st.table(df_c[['nome', 'qtd', 'sub']])
            total = df_c['sub'].sum()
            st.write(f"## TOTAL: R$ {total:,.2f}")
            
            forma = st.selectbox("Pagamento", ["Pix", "Dinheiro", "Cartão"])
            if st.button("🏁 FINALIZAR VENDA"):
                venda = supabase.table("vendas").insert({"total_liquido": total, "forma_pagamento": forma}).execute()
                v_id = venda.data[0]['id']
                for i in st.session_state.cart:
                    # Registra item
                    supabase.table("itens_venda").insert({"venda_id": v_id, "produto_id": i['id'], "quantidade": i['qtd'], "preco_unitario": i['preco']}).execute()
                    # Baixa estoque
                    p_atual = next(p for p in prods if p['id'] == i['id'])
                    supabase.table("produtos").update({"estoque_atual": p_atual['estoque_atual'] - i['qtd']}).eq("id", i['id']).execute()
                
                # Financeiro
                supabase.table("financeiro").insert({"tipo": "Receita", "valor": total, "descricao": f"Venda #{v_id}"}).execute()
                
                st.session_state.cart = []
                st.success("Venda Finalizada!")
                st.rerun()
        else: st.info("Carrinho vazio.")

# ==========================================
# MÓDULO: CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.header("👥 Gestão de Clientes")
    with st.expander("Novo Cliente"):
        with st.form("f_cli"):
            n = st.text_input("Nome/Razão Social")
            d = st.text_input("CPF/CNPJ")
            t = st.text_input("WhatsApp")
            if st.form_submit_button("Cadastrar"):
                supabase.table("clientes").insert({"nome": n, "documento": d, "telefone": t}).execute()
                st.success("Cliente salvo!")
    
    clis = get_data("clientes")
    if clis: st.dataframe(pd.DataFrame(clis), use_container_width=True)

# ==========================================
# MÓDULO: FINANCEIRO
# ==========================================
elif menu == "💰 Financeiro":
    st.header("💰 Fluxo de Caixa")
    fin = get_data("financeiro")
    if fin:
        df_f = pd.DataFrame(fin)
        c1, c2 = st.columns(2)
        receita = df_f[df_f['tipo'] == 'Receita']['valor'].sum()
        despesa = df_f[df_f['tipo'] == 'Despesa']['valor'].sum()
        c1.metric("Receitas", f"R$ {receita:,.2f}")
        c2.metric("Despesas", f"R$ {despesa:,.2f}", delta_color="inverse", delta=f"Saldo: R$ {receita-despesa:,.2f}")
        
        st.write("### Extrato de Movimentações")
        st.dataframe(df_f, use_container_width=True)
    
    with st.expander("Lançar Despesa Manual"):
        with st.form("f_fin"):
            desc = st.text_input("Descrição (ex: Aluguel)")
            val = st.number_input("Valor", 0.0)
            if st.form_submit_button("Lançar Despesa"):
                supabase.table("financeiro").insert({"tipo": "Despesa", "valor": val, "descricao": desc}).execute()
                st.rerun()

# ==========================================
# MÓDULO: ESTOQUE
# ==========================================
elif menu == "📋 Estoque":
    st.header("📋 Relatório de Estoque")
    prods = get_data("produtos")
    if prods:
        df_e = pd.DataFrame(prods)
        # Alerta de estoque baixo
        baixo = df_e[df_e['estoque_atual'] <= df_e['estoque_minimo']]
        if not baixo.empty:
            st.warning(f"⚠️ Atenção: {len(baixo)} itens com estoque baixo!")
        st.dataframe(df_e[['nome', 'sku', 'categoria', 'estoque_atual', 'estoque_minimo', 'preco_compra', 'preco_venda']], use_container_width=True)
