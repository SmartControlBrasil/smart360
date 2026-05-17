from django.urls import path

from . import views


app_name = "institutional"


urlpatterns = [
    path("", views.home, name="home"),
    path("sobre/", views.about, name="about"),
    path("servicos/", views.services, name="services"),
    path("servicos/detalhes/", views.service_details, name="service_details"),
    path("blog/", views.blog, name="blog"),
    path("blog/pagina/2/", views.blog_page_2, name="blog_page_2"),
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
    path("projetos/pagina/2/", views.projects_page_2, name="projects_page_2"),
    path("projetos/pagina/3/", views.projects_page_3, name="projects_page_3"),
    path("projetos/smart360/", views.project_smart360, name="project_smart360"),
    path("projetos/diagnostico-ia-dados-automacao/", views.project_diagnostico_ia_dados_automacao, name="project_diagnostico_ia_dados_automacao"),
    path("projetos/automacao-industrial-clps/", views.project_automacao_industrial_clps, name="project_automacao_industrial_clps"),
    path("projetos/manutencao-confiabilidade/", views.project_manutencao_confiabilidade, name="project_manutencao_confiabilidade"),
    path("projetos/cybersecurity-empresas/", views.project_cybersecurity_empresas, name="project_cybersecurity_empresas"),
    path("projetos/sites-marketing-conteudo/", views.project_sites_marketing_conteudo, name="project_sites_marketing_conteudo"),
    path("projetos/sistemas-web-django-python/", views.project_sistemas_web_django_python, name="project_sistemas_web_django_python"),
    path("projetos/ia-atendimento-operacao/", views.project_ia_atendimento_operacao, name="project_ia_atendimento_operacao"),
    path("projetos/dashboards-indicadores-operacionais/", views.project_dashboards_indicadores_operacionais, name="project_dashboards_indicadores_operacionais"),
    path("projetos/gestao-os-ativos/", views.project_gestao_os_ativos, name="project_gestao_os_ativos"),
    path("projetos/integracao-dados-sistemas/", views.project_integracao_dados_sistemas, name="project_integracao_dados_sistemas"),
    path("projetos/seguranca-backup-continuidade/", views.project_seguranca_backup_continuidade, name="project_seguranca_backup_continuidade"),
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
