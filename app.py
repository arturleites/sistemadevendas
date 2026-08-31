import streamlit as st
from supabase import create_client
import pandas as pd

st.set_page_config(page_title="Sistema de Vendas", layout="wide")

# CONEXÃO
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Erro nas chaves do Streamlit Secrets.")
    st.stop()

menu = st.sidebar.selectbox("Menu", ["Dashboard", "Cadastrar", "Estoque", "Vender"])

# --- CADASTRAR ---
if menu == "Cadastrar":
    st.header("📦 Cadastrar Produto")
    with st.form("form_cad"):
        nome = st.text_input("Nome do Item")
        cat = st.selectbox("Categoria", ["Bikes", "Games", "Eletrônicos", "Outros"])
        p_c = st.number_input("Preço Compra (R$)", 0.0)
        c_r = st.number_input("Custo Reparo/Extra (R$)", 0.0)
        
        if st.form_submit_button("SALVAR NO SISTEMA"):
            if nome:
                try:
                    # Tenta inserir no banco
                    dados = {"nome": nome, "categoria": cat, "preco_compra": p_c, "custo_reparo": c_r}
                    supabase.table("produtos").insert(dados).execute()
                    st.success(f"Sucesso! {nome} adicionado.")
                except Exception as e:
                    # Mostra o erro real se falhar
                    st.error(f"Erro do Banco de Dados: {e}")
            else:
                st.warning("Digite o nome do produto.")

# --- ESTOQUE ---
elif menu == "Estoque":
    st.header("📋 Estoque Atual")
    try:
        res = supabase.table("produtos").select("*").execute()
        if res.data:
            st.table(pd.DataFrame(res.data)[["nome", "categoria", "preco_compra", "status"]])
        else:
            st.info("Estoque vazio.")
    except Exception as e:
        st.error(f"Erro ao ler estoque: {e}")

# --- VENDER ---
elif menu == "Vender":
    st.header("💸 Registrar Venda")
    try:
        itens = supabase.table("produtos").select("*").eq("status", "Disponível").execute().data
        if itens:
            opcoes = {i['nome']: i['id'] for i in itens}
            item = st.selectbox("Produto", list(opcoes.keys()))
            v_p = st.number_input("Preço de Venda", 0.0)
            tx = st.number_input("Taxas", 0.0)
            canal = st.selectbox("Canal", ["ML", "OLX", "Direto"])
            
            if st.button("CONFIRMAR VENDA"):
                p_id = opcoes[item]
                supabase.table("vendas").insert({"produto_id": p_id, "preco_venda": v_p, "taxa_plataforma": tx, "canal_venda": canal}).execute()
                supabase.table("produtos").update({"status": "Vendido"}).eq("id", p_id).execute()
                st.success("Vendido com sucesso!")
        else:
            st.warning("Sem itens para vender.")
    except Exception as e:
        st.error(f"Erro ao carregar vendas: {e}")

# --- DASHBOARD ---
elif menu == "Dashboard":
    st.header("📊 Resumo")
    try:
        v = supabase.table("vendas").select("*").execute().data
        p = supabase.table("produtos").select("*").execute().data
        if v and p:
            df = pd.DataFrame(v).merge(pd.DataFrame(p), left_on="produto_id", right_on="id")
            df['lucro'] = df['preco_venda'] - df['taxa_plataforma'] - (df['preco_compra'] + df['custo_reparo'])
            c1, c2 = st.columns(2)
            c1.metric("Vendas Totais", f"R$ {df['preco_venda'].sum():,.2f}")
            c2.metric("Lucro Líquido", f"R$ {df['lucro'].sum():,.2f}")
        else:
            st.info("Aguardando vendas...")
    except:
        st.info("Aguardando dados...")
