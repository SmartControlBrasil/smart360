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


def faq(request):
    return render(request, "institutional/eitech/pages/faq.html")


def solution_detail(request, slug: str):
    # Compatibilidade com slugs legados apontando para detalhe de servico.
    return service_details(request)
