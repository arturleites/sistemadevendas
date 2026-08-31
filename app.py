import streamlit as st
from supabase import create_client
import pandas as pd

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema de Vendas Completo", layout="wide")

# CONEXÃO
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# MENU LATERAL
st.sidebar.title("💰 Gestão de Vendas")
menu = st.sidebar.selectbox("Navegação", ["Dashboard", "Cadastrar Produto", "Estoque", "Registrar Venda"])

# --- TELA: CADASTRAR PRODUTO ---
if menu == "Cadastrar Produto":
    st.header("📦 Cadastrar Novo Item")
    with st.form("form_cadastro"):
        nome = st.text_input("Nome do Produto")
        cat = st.selectbox("Categoria", ["Eletrônicos", "Games", "Bikes", "Casa", "Outros"])
        serie = st.text_input("Nº de Série / IMEI")
        p_compra = st.number_input("Preço de Compra (R$)", min_value=0.0)
        c_reparo = st.number_input("Custos Extras (R$)", min_value=0.0)
        foto = st.file_uploader("Foto", type=["jpg", "png", "jpeg"])
        
        if st.form_submit_button("Salvar no Estoque"):
            foto_url = ""
            if foto:
                try:
                    path = f"fotos/{foto.name}"
                    supabase.storage.from_("fotos_produtos").upload(path, foto.read())
                    foto_url = supabase.storage.from_("fotos_produtos").get_public_url(path)
                except: pass

            supabase.table("produtos").insert({
                "nome": nome, "categoria": cat, "numero_serie": serie,
                "preco_compra": p_compra, "custo_reparo": c_reparo,
                "foto_url": foto_url, "status": "Disponível"
            }).execute()
            st.success("Produto salvo!")

# --- TELA: ESTOQUE ---
elif menu == "Estoque":
    st.header("📋 Itens em Estoque")
    res = supabase.table("produtos").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[["nome", "categoria", "preco_compra", "status"]])
        for item in res.data:
            with st.expander(f"Detalhes: {item['nome']} ({item['status']})"):
                if item['foto_url']: st.image(item['foto_url'], width=200)
                st.write(f"Custo total: R$ {item['preco_compra'] + item['custo_reparo']}")

# --- TELA: REGISTRAR VENDA ---
elif menu == "Registrar Venda":
    st.header("💸 Registrar Venda")
    res = supabase.table("produtos").select("*").eq("status", "Disponível").execute()
    if res.data:
        prods = {p['nome']: p['id'] for p in res.data}
        item_nome = st.selectbox("Item vendido", list(prods.keys()))
        p_venda = st.number_input("Preço de Venda", min_value=0.0)
        taxa = st.number_input("Taxas", min_value=0.0)
        canal = st.selectbox("Canal", ["ML", "OLX", "Particular"])
        
        if st.button("Finalizar"):
            p_id = prods[item_nome]
            supabase.table("vendas").insert({"produto_id": p_id, "preco_venda": p_venda, "taxa_plataforma": taxa, "canal_venda": canal}).execute()
            supabase.table("produtos").update({"status": "Vendido"}).eq("id", p_id).execute()
            st.success("Vendido!")
    else: st.info("Sem itens no estoque.")

# --- TELA: DASHBOARD ---
elif menu == "Dashboard":
    st.header("📊 Resumo")
    vendas_res = supabase.table("vendas").select("*").execute()
    produtos_res = supabase.table("produtos").select("*").execute()
    
    if vendas_res.data and produtos_res.data:
        v = pd.DataFrame(vendas_res.data)
        p = pd.DataFrame(produtos_res.data)
        # Juntando as tabelas no Python para evitar erro de banco
        df = v.merge(p, left_on="produto_id", right_on="id")
        df['lucro'] = df['preco_venda'] - df['taxa_plataforma'] - (df['preco_compra'] + df['custo_reparo'])
        
        c1, c2 = st.columns(2)
        c1.metric("Vendas Totais", f"R$ {df['preco_venda'].sum():,.2f}")
        c2.metric("Lucro Real", f"R$ {df['lucro'].sum():,.2f}")
        st.bar_chart(df['canal_venda'].value_counts())
    else:
        st.info("Aguardando primeira venda...")
