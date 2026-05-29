from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render


def home(request):
    return render(request, "institutional/eitech/pages/home.html")


def about(request):
    return render(request, "institutional/eitech/pages/about.html")


def services(request):
    return render(request, "institutional/eitech/pages/services.html")


def service_details(request):
    return render(request, "institutional/eitech/pages/service-details.html")


def service_marketing_digital(request):
    return render(request, "institutional/eitech/pages/service-marketing-digital.html")


def service_automacao_industrial_clps(request):
    return render(request, "institutional/eitech/pages/service-automacao-industrial-clps.html")


def service_inteligencia_artificial(request):
    return render(request, "institutional/eitech/pages/service-inteligencia-artificial.html")


def service_robotica_integracao(request):
    return render(request, "institutional/eitech/pages/service-robotica-integracao.html")


def service_manutencao_tpm_confiabilidade(request):
    return render(request, "institutional/eitech/pages/service-manutencao-tpm-confiabilidade.html")


def service_diagnostico_ia_dados_automacao(request):
    return render(request, "institutional/eitech/pages/service-diagnostico-ia-dados-automacao.html")


def contact(request):
    if request.method == "POST":
        contact_name = request.POST.get("contact_name", "").strip()
        company = request.POST.get("company", "").strip()
        whatsapp = request.POST.get("whatsapp", "").strip()
        email = request.POST.get("email", "").strip()
        segment = request.POST.get("segment", "").strip()
        interest = (
            request.POST.get("interest", "").strip()
            or request.POST.get("primary_interest", "").strip()
        )
        main_problem = request.POST.get("main_problem", "").strip()
        message = request.POST.get("message", "").strip()

        if not contact_name or not email or not message:
            messages.error(request, "Preencha nome, e-mail e mensagem antes de enviar.")
            return redirect("institutional:contact")

        interest_label_by_value = {
            "automacao": "Automação Industrial, CLPs e IHMs",
            "robotica": "Robótica e Automação Aplicada",
            "iot_dados": "IoT, Dados, Integração e Dashboards",
            "produtos": "Produtos, Kits, Robôs e Componentes",
            "retrofit": "Retrofit de Máquinas e Painéis Elétricos",
            "manutencao": "Manutenção Técnica, TPM e Confiabilidade",
            "acionamentos": "Inversores, Servoacionamentos e Motion Control",
            "supervisorio": "Supervisório, Dados Industriais e Indicadores",
            "energia": "Gerenciamento de Energia e Utilidades",
        }
        interest_display = interest_label_by_value.get(
            interest, interest or "Não informado"
        )

        subject_line = (
            f"Diagnóstico pelo site: {interest_display}"
            if interest
            else "Diagnóstico inicial pelo site"
        )

        body = f"""
Solicitação de diagnóstico inicial — Smart Control Brasil.

Nome: {contact_name}
Empresa: {company or "Não informada"}
WhatsApp: {whatsapp or "Não informado"}
E-mail: {email}
Segmento: {segment or "Não informado"}
Interesse principal: {interest_display}

Principal problema atual:
{main_problem or "Não informado"}

Mensagem:
{message}
""".strip()

        try:
            send_mail(
                subject=subject_line,
                message=body,
                from_email=getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    "Smart Control Brasil <contato@smartcontrolbrasil.com.br>",
                ),
                recipient_list=[
                    getattr(settings, "CONTACT_EMAIL", "contato@smartcontrolbrasil.com.br")
                ],
                fail_silently=False,
            )
            messages.success(
                request,
                "Recebemos sua solicitação de diagnóstico. Em breve entraremos em contato.",
            )
        except Exception:
            messages.error(
                request,
                "Não foi possível enviar sua mensagem agora. Tente novamente em alguns minutos.",
            )

        return redirect("institutional:contact")

    return render(request, "institutional/eitech/pages/contact.html")


def team(request):
    return render(request, "institutional/eitech/pages/team.html")


def smart360(request):
    return render(request, "institutional/eitech/pages/smart360.html")


def projects(request):
    return render(request, "institutional/eitech/pages/projects.html")


def projects_page_2(request):
    return render(request, "institutional/eitech/pages/projects-page-2.html")


def projects_page_3(request):
    return render(request, "institutional/eitech/pages/projects-page-3.html")


def project_details(request):
    return render(request, "institutional/eitech/pages/project-details.html")


def blog(request):
    return render(request, "institutional/eitech/pages/blog.html")


def blog_page_2(request):
    return render(request, "institutional/eitech/pages/blog-page-2.html")


def blog_details(request):
    return render(request, "institutional/eitech/pages/blog-details.html")


def supervisao_dados_industriais(request):
    return render(request, "institutional/eitech/pages/projects/smart360.html")


def diagnostico_industrial_engenharia_solucao(request):
    return render(request, "institutional/eitech/pages/projects/diagnostico-ia-dados-automacao.html")


def automacao_industrial_clps_ihms(request):
    return render(request, "institutional/eitech/pages/projects/automacao-industrial-clps.html")


def manutencao_retrofit_confiabilidade(request):
    return render(request, "institutional/eitech/pages/projects/manutencao-confiabilidade.html")


def inversores_eficiencia_energetica(request):
    return render(request, "institutional/eitech/pages/projects/cybersecurity-empresas.html")


def servoacionamentos_motion_control(request):
    return render(request, "institutional/eitech/pages/projects/sites-marketing-conteudo.html")


def supervisorio_scada_dados_industriais(request):
    return render(request, "institutional/eitech/pages/projects/sistemas-web-django-python.html")


def robotica_celulas_automatizadas(request):
    return render(request, "institutional/eitech/pages/projects/ia-atendimento-operacao.html")


def gerenciamento_energia_utilidades(request):
    return render(request, "institutional/eitech/pages/projects/dashboards-indicadores-operacionais.html")


def paineis_eletricos_baixa_tensao(request):
    return render(request, "institutional/eitech/pages/projects/gestao-os-ativos.html")


def integracao_chao_fabrica_dados_industriais(request):
    return render(request, "institutional/eitech/pages/projects/integracao-dados-sistemas.html")


def seguranca_maquinas_continuidade_operacional(request):
    return render(request, "institutional/eitech/pages/projects/seguranca-backup-continuidade.html")


def blog_retrofit_maquina_industrial(request):
    return render(request, "institutional/eitech/pages/blog/ia-pequenas-empresas.html")


def blog_organizar_sinais_dados_antes_automatizar(request):
    return render(request, "institutional/eitech/pages/blog/organizar-dados-antes-automatizar.html")


def blog_manutencao_tpm_confiabilidade_sistemas_automatizados(request):
    return render(request, "institutional/eitech/pages/blog/manutencao-tpm-confiabilidade-digital.html")


def blog_clp_ihm_inversor_falhas_maquina(request):
    return render(request, "institutional/eitech/pages/blog/cybersecurity-pequenas-empresas.html")


def blog_supervisorio_industrial_dados_tempo_real(request):
    return render(request, "institutional/eitech/pages/blog/sistemas-web-operacao-moderna.html")


def blog_automacao_industrial_conectada_manutencao_gestao(request):
    return render(request, "institutional/eitech/pages/blog/automacao-industrial-conectada-gestao.html")


def blog_paineis_eletricos_organizacao_seguranca_manutenibilidade(request):
    return render(request, "institutional/eitech/pages/blog/marketing-digital-tecnologia-processo.html")


def blog_dados_industriais_confiabilidade_reduzir_paradas(request):
    return render(request, "institutional/eitech/pages/blog/smart360-operacao-inteligente.html")


def faq(request):
    return render(request, "institutional/eitech/pages/faq.html")


def solution_detail(request, slug: str):
    # Compatibilidade com slugs legados apontando para detalhe de servico.
    return service_details(request)
