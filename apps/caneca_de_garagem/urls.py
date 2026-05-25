from django.urls import path

from . import views

app_name = "caneca_de_garagem"

urlpatterns = [
    path("", views.home, name="home"),
    path("sobre/", views.about, name="about"),
    path("explorar/canecas/", views.explore_canecas, name="explore-canecas"),
    path("explorar/long-drink/", views.explore_long_drink, name="explore-long-drink"),
    path("explorar/camisetas/", views.explore_camisetas, name="explore-camisetas"),
    path("explorar/caneca-de-chopp/", views.explore_caneca_chopp, name="explore-caneca-chopp"),
    path("produtos/", views.product_list, name="product_list"),
    path("produtos/<slug:slug>/", views.product_detail, name="product_detail"),
    path("marketplace/", views.marketplace_dashboard, name="market"),
    path("marketplace/explorar/", views.marketplace_explore, name="market-explore"),
    path("marketplace/orcamentos-ativos/", views.marketplace_active_quotes, name="market-active-quote"),
    path("marketplace/colecoes/", views.marketplace_collections, name="market-collection"),
    path("marketplace/favoritos/", views.marketplace_favorites, name="market-favorite"),
    path("marketplace/pedidos/", views.marketplace_orders_area, name="market-orders-area"),
    path("marketplace/historico/", views.marketplace_history, name="market-history"),
    path("parceiros/cadastrar-produto/", views.marketplace_partner_create_product, name="market-create"),
    path("termos/", views.terms_condition, name="terms"),
    path("sem-resultados/", views.no_result, name="no-result"),
    path("faq/", views.faq, name="faq"),
    path("em-breve/", views.coming_soon, name="coming-soon"),
    path("manutencao/", views.maintenance_preview, name="maintenance"),
    path("404-preview/", views.not_found_preview, name="not-found-preview"),
    path("entrar/", views.login_preview, name="login"),
    path("cadastro/", views.sign_up_preview, name="sign-up"),
    path("criadores/", views.author_list, name="author-list"),
    path("criadores/<slug:slug>/", views.author_detail, name="author-detail"),
    path("orcamento-b2b/", views.b2b_quote, name="b2b_quote"),
    path("contato/", views.contact, name="contact"),
    path("pedido/sucesso/", views.order_success, name="order_success"),
    path("blog/", views.blog_list, name="blog-list"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog-detail"),
]
