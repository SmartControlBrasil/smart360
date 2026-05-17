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
