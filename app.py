import streamlit as st
from supabase import create_client
import pandas as pd

# CONFIGURAÇÃO
st.set_page_config(page_title="Sistema de Vendas", layout="wide")

# CONEXÃO (Protegida)
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"Erro nas chaves de acesso: {e}")
    st.stop()

# MENU
menu = st.sidebar.selectbox("Navegação", ["Dashboard", "Cadastrar Produto", "Estoque", "Registrar Venda"])

# --- FUNÇÃO AUXILIAR PARA BUSCAR DADOS ---
def buscar_dados(tabela):
    try:
        res = supabase.table(tabela).select("*").execute()
        return res.data
    except Exception as e:
        st.error(f"Erro ao ler tabela {tabela}: {e}")
        return []

# --- DASHBOARD ---
if menu == "Dashboard":
    st.header("📊 Resumo do Negócio")
    vendas = buscar_dados("vendas")
    produtos = buscar_dados("produtos")
    
    if vendas and produtos:
        df_v = pd.DataFrame(vendas)
        df_p = pd.DataFrame(produtos)
        df = df_v.merge(df_p, left_on="produto_id", right_on="id")
        
        df['lucro'] = df['preco_venda'] - df['taxa_plataforma'] - (df['preco_compra'] + df['custo_reparo'])
        
        c1, c2 = st.columns(2)
        c1.metric("Vendas Totais", f"R$ {df['preco_venda'].sum():,.2f}")
        c2.metric("Lucro Líquido", f"R$ {df['lucro'].sum():,.2f}")
        st.bar_chart(df['canal_venda'].value_counts())
    else:
        st.info("Nenhuma venda encontrada para gerar o resumo.")

# --- CADASTRAR ---
elif menu == "Cadastrar Produto":
    st.header("📦 Novo Produto")
    with st.form("cad"):
        n = st.text_input("Nome")
        cat = st.selectbox("Cat", ["Bikes", "Games", "Eletrônicos", "Casa", "Outros"])
        p_c = st.number_input("Preço Compra", 0.0)
        c_r = st.number_input("Reparo/Custos Extras", 0.0)
        if st.form_submit_button("Salvar"):
            supabase.table("produtos").insert({"nome": n, "categoria": cat, "preco_compra": p_c, "custo_reparo": c_r}).execute()
            st.success("Salvo!")

# --- ESTOQUE ---
elif menu == "Estoque":
    st.header("📋 Estoque")
    itens = buscar_dados("produtos")
    if itens:
        st.table(pd.DataFrame(itens)[["nome", "categoria", "preco_compra", "status"]])
    else:
        st.write("Estoque vazio.")

# --- VENDA ---
elif menu == "Registrar Venda":
    st.header("💸 Registrar Venda")
    disponiveis = supabase.table("produtos").select("*").eq("status", "Disponível").execute().data
    if disponiveis:
        itens_dict = {i['nome']: i['id'] for i in disponiveis}
        escolha = st.selectbox("O que vendeu?", list(itens_dict.keys()))
        venda_p = st.number_input("Preço Venda", 0.0)
        taxa = st.number_input("Taxas", 0.0)
        canal = st.selectbox("Onde?", ["ML", "OLX", "Direto"])
        if st.button("Vender"):
            p_id = itens_dict[escolha]
            supabase.table("vendas").insert({"produto_id": p_id, "preco_venda": venda_p, "taxa_plataforma": taxa, "canal_venda": canal}).execute()
            supabase.table("produtos").update({"status": "Vendido"}).eq("id", p_id).execute()
            st.success("Vendido!")
    else:
        st.info("Não há itens disponíveis.")
