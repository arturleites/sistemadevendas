import streamlit as st
from supabase import create_client
import pandas as pd

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema de Vendas Completo", layout="wide")

# CONEXÃO COM O BANCO DE DADOS (Vamos configurar as chaves depois)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# MENU LATERAL
st.sidebar.title("💰 Minhas Vendas")
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Cadastrar Produto", "Estoque", "Registrar Venda"])

# --- FUNÇÕES AUXILIARES ---
def listar_produtos_disponiveis():
    res = supabase.table("produtos").select("*").eq("status", "Disponível").execute()
    return res.data

# --- TELA: CADASTRAR PRODUTO ---
if menu == "Cadastrar Produto":
    st.header("📦 Cadastrar Novo Item")
    
    with st.form("cadastro_prod", clear_on_submit=True):
        nome = st.text_input("Nome do Produto (ex: iPhone 13, Bike Trek)")
        cat = st.selectbox("Categoria", ["Eletrônicos", "Games", "Bikes", "Casa", "Outros"])
        serie = st.text_input("Nº de Série / IMEI / Chassi")
        preco_c = st.number_input("Preço de Compra (R$)", min_value=0.0)
        custo_ext = st.number_input("Custos Extras (Limpeza, Peças, Frete) (R$)", min_value=0.0)
        foto = st.file_uploader("Foto do Produto", type=["jpg", "png", "jpeg"])
        
        if st.form_submit_button("Salvar no Estoque"):
            foto_url = ""
            if foto:
                # Upload da foto para o Storage
                file_path = f"fotos/{foto.name}"
                supabase.storage.from_("fotos_produtos").upload(file_path, foto.read())
                foto_url = supabase.storage.from_("fotos_produtos").get_public_url(file_path)

            supabase.table("produtos").insert({
                "nome": nome, "categoria": cat, "numero_serie": serie,
                "preco_compra": preco_c, "custo_reparo": custo_ext,
                "foto_url": foto_url, "status": "Disponível"
            }).execute()
            st.success("Item adicionado com sucesso!")

# --- TELA: ESTOQUE ---
elif menu == "Estoque":
    st.header("📋 Itens em Estoque")
    dados = supabase.table("produtos").select("*").execute()
    if dados.data:
        df = pd.DataFrame(dados.data)
        st.dataframe(df[["nome", "categoria", "preco_compra", "status", "numero_serie"]])
        
        for item in dados.data:
            with st.expander(f"Ver Detalhes: {item['nome']}"):
                col1, col2 = st.columns(2)
                with col1:
                    if item['foto_url']:
                        st.image(item['foto_url'], width=250)
                with col2:
                    st.write(f"**Série:** {item['numero_serie']}")
                    st.write(f"**Custo Total:** R$ {item['preco_compra'] + item['custo_reparo']}")
                    st.write(f"**Status:** {item['status']}")

# --- TELA: REGISTRAR VENDA ---
elif menu == "Registrar Venda":
    st.header("💸 Registrar Venda")
    prods = listar_produtos_disponiveis()
    
    if prods:
        nomes_prods = {p['nome']: p['id'] for p in prods}
        escolha = st.selectbox("Qual item você vendeu?", list(nomes_prods.keys()))
        
        preco_v = st.number_input("Preço de Venda (R$)", min_value=0.0)
        taxa = st.number_input("Taxas (Plataforma/Cartão) (R$)", min_value=0.0)
        canal = st.selectbox("Canal de Venda", ["Mercado Livre", "OLX", "Marketplace", "Particular", "Outro"])
        
        if st.button("Finalizar Venda"):
            prod_id = nomes_prods[escolha]
            # Salva a venda
            supabase.table("vendas").insert({
                "produto_id": prod_id, "preco_venda": preco_v,
                "taxa_plataforma": taxa, "canal_venda": canal
            }).execute()
            # Atualiza status do produto
            supabase.table("produtos").update({"status": "Vendido"}).eq("id", prod_id).execute()
            st.balloons()
            st.success(f"Venda de {escolha} registrada!")
    else:
        st.warning("Não há produtos disponíveis para venda.")

# --- TELA: DASHBOARD ---
elif menu == "Dashboard":
    st.header("📊 Resumo do Negócio")
    
    # Cálculos Simples
    vendas = supabase.table("vendas").select("*, produtos(preco_compra, custo_reparo)").execute()
    if vendas.data:
        df_vendas = pd.DataFrame(vendas.data)
        # Cálculo de Lucro Líquido
        df_vendas['custo_total'] = df_vendas['produtos'].apply(lambda x: x['preco_compra'] + x['custo_reparo'])
        df_vendas['lucro'] = df_vendas['preco_venda'] - df_vendas['taxa_plataforma'] - df_vendas['custo_total']
        
        total_lucro = df_vendas['lucro'].sum()
        total_vendas = df_vendas['preco_venda'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Vendas Totais", f"R$ {total_vendas:,.2f}")
        c2.metric("Lucro Líquido Total", f"R$ {total_lucro:,.2f}", delta=f"{((total_lucro/total_vendas)*100):.1f}% ROI")
        
        st.subheader("Vendas por Canal")
        st.bar_chart(df_vendas['canal_venda'].value_counts())
