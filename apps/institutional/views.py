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


def project_details(request):
    return render(request, "institutional/eitech/pages/project-details.html")


def blog(request):
    return render(request, "institutional/eitech/pages/blog.html")


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
