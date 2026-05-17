from django.urls import path

from . import views


app_name = "institutional"


urlpatterns = [
    path("", views.home, name="home"),
    path("sobre/", views.about, name="about"),
    path("servicos/", views.services, name="services"),
    path("servicos/detalhes/", views.service_details, name="service_details"),
    path("blog/", views.blog, name="blog"),
    path("blog/detalhes/", views.blog_details, name="blog_details"),
    # Static individual blog posts (static templates)
    path("blog/ia-pequenas-empresas/", views.blog_ia_pequenas_empresas, name="blog_ia_pequenas_empresas"),
    path("blog/organizar-dados-antes-automatizar/", views.blog_organizar_dados_antes_automatizar, name="blog_organizar_dados_antes_automatizar"),
    path("blog/manutencao-tpm-confiabilidade-digital/", views.blog_manutencao_tpm_confiabilidade_digital, name="blog_manutencao_tpm_confiabilidade_digital"),
    path("blog/cybersecurity-pequenas-empresas/", views.blog_cybersecurity_pequenas_empresas, name="blog_cybersecurity_pequenas_empresas"),
    path("blog/sistemas-web-operacao-moderna/", views.blog_sistemas_web_operacao_moderna, name="blog_sistemas_web_operacao_moderna"),
    path("blog/automacao-industrial-conectada-gestao/", views.blog_automacao_industrial_conectada_gestao, name="blog_automacao_industrial_conectada_gestao"),
    path("blog/marketing-digital-tecnologia-processo/", views.blog_marketing_digital_tecnologia_processo, name="blog_marketing_digital_tecnologia_processo"),
    path("blog/smart360-operacao-inteligente/", views.blog_smart360_operacao_inteligente, name="blog_smart360_operacao_inteligente"),
    path("contato/", views.contact, name="contact"),
    path("equipe/", views.team, name="team"),
    path("projetos/", views.projects, name="projects"),
    path("projetos/detalhes/", views.project_details, name="project_details"),
    path("faq/", views.faq, name="faq"),
    # Aliases curtos para manter compatibilidade com o novo plano de URLs publicas.
    path("about/", views.about, name="about_alias"),
    path("services/", views.services, name="services_alias"),
    path("contact/", views.contact, name="contact_alias"),
    path("service-details/", views.service_details, name="service_details_alias"),
    path("team/", views.team, name="team_alias"),
    path("projects/", views.projects, name="projects_alias"),
    path("project-details/", views.project_details, name="project_details_alias"),
    path("blog-details/", views.blog_details, name="blog_details_alias"),
    path(
        "automacao-industrial/",
        views.solution_detail,
        {"slug": "automacao-industrial"},
        name="automacao_industrial",
    ),
    path(
        "ar-condicionado/",
        views.solution_detail,
        {"slug": "ar-condicionado"},
        name="ar_condicionado",
    ),
    path(
        "seguranca-da-informacao/",
        views.solution_detail,
        {"slug": "seguranca-da-informacao"},
        name="seguranca_da_informacao",
    ),
    path(
        "sites-sistemas-marketing/",
        views.solution_detail,
        {"slug": "sites-sistemas-marketing"},
        name="sites_sistemas_marketing",
    ),
]
