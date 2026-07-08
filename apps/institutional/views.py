import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.http import Http404
from django.shortcuts import redirect, render

from .services.contact_spam_guard import (
    ContactSubmissionClass,
    classify_contact_submission,
    is_contact_rate_limited,
    partial_ip,
)
from .xyron_robots import XYRON_ROBOTS, get_featured_xyron_robots, get_other_xyron_robots, get_xyron_robot

XYRON_ROBOT_PAGE_TEMPLATES = {
    "liro-littlebot": "institutional/eitech/pages/xyron/liro-littlebot.html",
    "neobot": "institutional/eitech/pages/xyron/neobot.html",
    "buddy": "institutional/eitech/pages/xyron/buddy.html",
    "patrol-orbit": "institutional/eitech/pages/xyron/patrol-orbit.html",
    "hygibot": "institutional/eitech/pages/xyron/hygibot.html",
    "hostbot": "institutional/eitech/pages/xyron/hostbot.html",
    "waiterbot": "institutional/eitech/pages/xyron/waiterbot.html",
    "carebot": "institutional/eitech/pages/xyron/carebot.html",
    "mowerbot": "institutional/eitech/pages/xyron/mowerbot.html",
}


logger = logging.getLogger(__name__)

CONTACT_GENERIC_SUCCESS_MESSAGE = "Mensagem recebida. Obrigado pelo contato."


def _client_ip(request) -> str:
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or (request.META.get("REMOTE_ADDR") or "").strip()


def _log_contact_guard_event(
    *,
    classification: str,
    score: int,
    reasons: tuple[str, ...],
    ip: str,
    email: str,
) -> None:
    email_domain = email.split("@", 1)[1].lower() if "@" in email else ""
    logger.info(
        "Contato institucional classificado como %s.",
        classification,
        extra={
            "event": "institutional_contact_spam_guard",
            "classification": classification,
            "score": score,
            "reasons": list(reasons[:5]),
            "ip_partial": partial_ip(ip),
            "email_domain": email_domain,
        },
    )


def home(request):
    return render(request, "institutional/eitech/pages/index.html")


def about(request):
    return render(request, "institutional/eitech/pages/about.html")


def services(request):
    return render(request, "institutional/eitech/pages/services.html")


def engenharia_embarcada(request):
    return render(request, "institutional/eitech/pages/engenharia_embarcada.html")


def refrigeracao(request):
    return redirect("institutional:engenharia_embarcada", permanent=True)


def service_details(request):
    return render(request, "institutional/eitech/pages/service-details.html")


def service_marketing_digital(request):
    return render(request, "institutional/eitech/pages/service-marketing-digital.html")


def service_automacao_industrial_clps(request):
    return render(request, "institutional/eitech/pages/service-automacao-industrial-clps.html")


def service_inteligencia_artificial(request):
    return render(request, "institutional/eitech/pages/service-inteligencia-artificial.html")


def service_sistemas_web_aplicativos(request):
    return render(request, "institutional/eitech/pages/service-sistemas-web-aplicativos.html")


def service_robotica_integracao(request):
    return render(request, "institutional/eitech/pages/service-robotica-integracao.html")


def representada_mitsubishi_automacao(request):
    return render(request, "institutional/eitech/pages/mitsubishi.html")


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
        client_ip = _client_ip(request)

        rate_limit = getattr(settings, "CONTACT_FORM_RATE_LIMIT", 5)
        rate_window = getattr(settings, "CONTACT_FORM_RATE_WINDOW_SECONDS", 900)
        if is_contact_rate_limited(
            client_ip,
            limit=rate_limit,
            window_seconds=rate_window,
        ):
            _log_contact_guard_event(
                classification="rate_limited",
                score=0,
                reasons=("rate_limit_exceeded",),
                ip=client_ip,
                email=email,
            )
            messages.success(request, CONTACT_GENERIC_SUCCESS_MESSAGE)
            return redirect("institutional:contact")

        verdict = classify_contact_submission(request.POST)
        if verdict.classification in {ContactSubmissionClass.SPAM, ContactSubmissionClass.SUSPICIOUS}:
            _log_contact_guard_event(
                classification=verdict.classification.value,
                score=verdict.score,
                reasons=verdict.reasons,
                ip=client_ip,
                email=email,
            )
            messages.success(request, CONTACT_GENERIC_SUCCESS_MESSAGE)
            return redirect("institutional:contact")

        interest_label_by_value = {
            "automacao": "Automação Industrial, CLPs e IHMs",
            "robotica": "Robótica e Automação Aplicada",
            "iot_dados": "IoT, Dados, Integração e Dashboards",
            "produtos": "Produtos, Kits, Robôs e Componentes",
            "software": "Softwares, Sistemas Web e Dashboards",
            "retrofit": "Retrofit de Máquinas e Painéis Elétricos",
            "retrofit_suporte": "Retrofit, Suporte Técnico e Manutenção",
            "manutencao": "Manutenção Técnica, TPM e Confiabilidade",
            "acionamentos": "Inversores, Servoacionamentos e Motion Control",
            "supervisorio": "Supervisório, Dados Industriais e Indicadores",
            "energia": "Gerenciamento de Energia e Utilidades",
        }
        interest_display = interest_label_by_value.get(
            interest, interest or "Não informado"
        )

        body = f"""
Nova solicitação recebida pelo site Smart Control Brasil

Nome: {contact_name}
Empresa: {company or "Não informada"}
WhatsApp: {whatsapp or "Não informado"}
E-mail: {email}
Segmento: {segment or "Não informado"}
Interesse principal: {interest_display}

Objetivo principal:
{main_problem or "Não informado"}

Mensagem:
{message}

Dados técnicos:
Origem: Página de contato institucional
""".strip()

        reply_to = []
        try:
            validate_email(email)
            reply_to.append(email)
        except ValidationError:
            pass

        try:
            email_message = EmailMessage(
                subject="Nova solicitação pelo site | Smart Control Brasil",
                body=body,
                from_email=getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    "engenharia@smartcontrolbrasil.com.br",
                ),
                to=getattr(
                    settings,
                    "CONTACT_FORM_RECIPIENTS",
                    ["contato@smartcontrolbrasil.com.br"],
                ),
                bcc=getattr(
                    settings,
                    "CONTACT_FORM_BCC",
                    ["engenharia@smartcontrolbrasil.com.br"],
                ),
                reply_to=reply_to,
            )
            email_message.send(fail_silently=False)
            messages.success(
                request,
                "Mensagem enviada com sucesso. Em breve nossa equipe entrará em contato.",
            )
        except Exception:
            logger.exception("Erro ao enviar solicitação da página de contato institucional")
            messages.error(
                request,
                "Não foi possível enviar sua solicitação agora. Tente novamente ou chame pelo WhatsApp.",
            )
            return render(request, "institutional/eitech/pages/contact.html")

        return redirect("institutional:contact")

    return render(request, "institutional/eitech/pages/contact.html")


def team(request):
    return render(request, "institutional/eitech/pages/team.html")


def parceiro_xyron_robotics(request):
    return render(
        request,
        "institutional/eitech/pages/xyron-robotics.html",
        {"xyron_robots": XYRON_ROBOTS},
    )


def _render_xyron_robot_detail(request, slug):
    robot = get_xyron_robot(slug)
    if robot is None:
        raise Http404("Robô Xyron não encontrado")

    sidebar_robots = get_other_xyron_robots(slug)
    context = {
        "robot": robot,
        "current_slug": slug,
        "sidebar_robots": sidebar_robots,
        "related_robots": get_featured_xyron_robots(slug),
    }

    template = XYRON_ROBOT_PAGE_TEMPLATES[slug]
    return render(request, template, context)


def xyron_robot_detail(request, slug):
    return _render_xyron_robot_detail(request, slug)


def xyron_liro_littlebot(request):
    return _render_xyron_robot_detail(request, "liro-littlebot")


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


def tecnologia_embarcada_solucoes_customizadas(request):
    return render(request, "institutional/eitech/pages/projects/tecnologia-embarcada-solucoes-customizadas.html")


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