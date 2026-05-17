from django.shortcuts import render


def home(request):
    return render(request, "institutional/eitech/pages/home.html")


def about(request):
    return render(request, "institutional/eitech/pages/about.html")


def services(request):
    return render(request, "institutional/eitech/pages/services.html")


def service_details(request):
    return render(request, "institutional/eitech/pages/service-details.html")


def contact(request):
    return render(request, "institutional/eitech/pages/contact.html")


def team(request):
    return render(request, "institutional/eitech/pages/team.html")


def projects(request):
    return render(request, "institutional/eitech/pages/projects.html")


def projects_page_2(request):
    return render(request, "institutional/eitech/pages/projects-page-2.html")


def projects_page_3(request):
    return render(request, "institutional/eitech/pages/projects-page-3.html")


def project_details(request):
    return render(request, "institutional/eitech/pages/project-details.html")


def project_smart360(request):
    return render(request, "institutional/eitech/pages/projects/smart360.html")


def project_diagnostico_ia_dados_automacao(request):
    return render(request, "institutional/eitech/pages/projects/diagnostico-ia-dados-automacao.html")


def project_automacao_industrial_clps(request):
    return render(request, "institutional/eitech/pages/projects/automacao-industrial-clps.html")


def project_manutencao_confiabilidade(request):
    return render(request, "institutional/eitech/pages/projects/manutencao-confiabilidade.html")


def project_cybersecurity_empresas(request):
    return render(request, "institutional/eitech/pages/projects/cybersecurity-empresas.html")


def project_sites_marketing_conteudo(request):
    return render(request, "institutional/eitech/pages/projects/sites-marketing-conteudo.html")


def project_sistemas_web_django_python(request):
    return render(request, "institutional/eitech/pages/projects/sistemas-web-django-python.html")


def project_ia_atendimento_operacao(request):
    return render(request, "institutional/eitech/pages/projects/ia-atendimento-operacao.html")


def project_dashboards_indicadores_operacionais(request):
    return render(request, "institutional/eitech/pages/projects/dashboards-indicadores-operacionais.html")


def project_gestao_os_ativos(request):
    return render(request, "institutional/eitech/pages/projects/gestao-os-ativos.html")


def project_integracao_dados_sistemas(request):
    return render(request, "institutional/eitech/pages/projects/integracao-dados-sistemas.html")


def project_seguranca_backup_continuidade(request):
    return render(request, "institutional/eitech/pages/projects/seguranca-backup-continuidade.html")


def blog(request):
    return render(request, "institutional/eitech/pages/blog.html")


def blog_page_2(request):
    return render(request, "institutional/eitech/pages/blog-page-2.html")


def blog_details(request):
    return render(request, "institutional/eitech/pages/blog-details.html")


# Static blog article pages (render templates under pages/blog/)
def blog_ia_pequenas_empresas(request):
    return render(request, "institutional/eitech/pages/blog/ia-pequenas-empresas.html")


def blog_organizar_dados_antes_automatizar(request):
    return render(request, "institutional/eitech/pages/blog/organizar-dados-antes-automatizar.html")


def blog_manutencao_tpm_confiabilidade_digital(request):
    return render(request, "institutional/eitech/pages/blog/manutencao-tpm-confiabilidade-digital.html")


def blog_cybersecurity_pequenas_empresas(request):
    return render(request, "institutional/eitech/pages/blog/cybersecurity-pequenas-empresas.html")


def blog_sistemas_web_operacao_moderna(request):
    return render(request, "institutional/eitech/pages/blog/sistemas-web-operacao-moderna.html")


def blog_automacao_industrial_conectada_gestao(request):
    return render(request, "institutional/eitech/pages/blog/automacao-industrial-conectada-gestao.html")


def blog_marketing_digital_tecnologia_processo(request):
    return render(request, "institutional/eitech/pages/blog/marketing-digital-tecnologia-processo.html")


def blog_smart360_operacao_inteligente(request):
    return render(request, "institutional/eitech/pages/blog/smart360-operacao-inteligente.html")

def faq(request):
    return render(request, "institutional/eitech/pages/faq.html")


def solution_detail(request, slug: str):
    # Compatibilidade com slugs legados apontando para detalhe de servico.
    return service_details(request)
