import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.admin_shell.views import ShellContextMixin
from apps.livia_assistant.models import LiviaHandoffRequest, LiviaLeadCapture

from .forms import CommercialProposalForm, MarketplaceLeadInteractionForm, MarketplaceLeadStatusForm, OperationalForwardNoteForm
from .models import CommercialProposal, Lead, LeadInteraction
from .proposal_helpers import (
    commercial_proposal_is_marketplace_origin,
    marketplace_proposal_suggested_email_intro,
    resolve_marketplace_lead_id_for_detail_link,
)


LIVIA_METADATA_SOURCE = "livia_assistant"
MARKETPLACE_ECOM_ORIGIN = "marketplace_ecom"
MARKETPLACE_LEAD_SOURCE_NAME = "marketplace_ecom"


def marketplace_growth_leads_queryset():
    return Lead.objects.select_related("source", "campaign", "assigned_to").filter(
        Q(metadata__origin=MARKETPLACE_ECOM_ORIGIN) | Q(source__name=MARKETPLACE_LEAD_SOURCE_NAME)
    )


def marketplace_lead_list_row_dict(lead: Lead):
    """Campos seguros por lead para dashboard Marketplace (JSONField pode omitir chaves)."""
    md = getattr(lead, "metadata", None) or {}
    if not isinstance(md, dict):
        md = {}

    def meta_str(key: str) -> str:
        raw = md.get(key)
        if raw is None:
            return ""
        text = str(raw).strip()
        return text if text else ""

    product_title = meta_str("product_title")
    product_slug = meta_str("product_slug")
    origin_meta = meta_str("origin")

    return {
        "lead": lead,
        "product_title": product_title,
        "product_slug": product_slug,
        "origin": origin_meta,
        "product_summary": product_title or product_slug or "—",
    }


def resolve_user_display_label(user) -> str:
    """Rótulo para exibição — User customizado pode não ter get_full_name."""
    if user is None:
        return ""
    get_full_name = getattr(user, "get_full_name", None)
    if callable(get_full_name):
        try:
            name = get_full_name() or ""
        except Exception:
            name = ""
        if isinstance(name, str) and name.strip():
            return name.strip()
    for attr in ("name", "full_name"):
        try:
            value = getattr(user, attr)
        except Exception:
            continue
        if value is not None and str(value).strip():
            return str(value).strip()
    email = getattr(user, "email", None)
    if email is not None and str(email).strip():
        return str(email).strip()
    username = getattr(user, "username", None)
    if username is not None and str(username).strip():
        return str(username).strip()
    pk = getattr(user, "pk", None)
    if pk is not None:
        return str(pk)
    return str(user)


def apply_period_filter(queryset, request):
    """Filtra por created_at a partir dos parâmetros GET date_from / date_to (YYYY-MM-DD)."""
    period_from = request.GET.get("date_from", "").strip()
    period_to = request.GET.get("date_to", "").strip()
    if period_from:
        try:
            df = datetime.strptime(period_from, "%Y-%m-%d").date()
            queryset = queryset.filter(created_at__date__gte=df)
        except ValueError:
            pass
    if period_to:
        try:
            dt = datetime.strptime(period_to, "%Y-%m-%d").date()
            queryset = queryset.filter(created_at__date__lte=dt)
        except ValueError:
            pass
    return queryset


class GrowthDashboardBaseView(ShellContextMixin, TemplateView):
    permission_domain = "dashboard"
    permission_action = "view"
    enforce_billing_access = False
    current_module_slug = "growth-engine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_module_slug"] = self.current_module_slug
        context["page_actions"] = [
            {"label": "Leads Marketplace E-com", "route_name": "admin-shell:growth-marketplace-leads", "permission_domain": "dashboard", "permission_action": "view"},
            {"label": "Leads da Lívia", "route_name": "admin-shell:growth-livia-leads", "permission_domain": "dashboard", "permission_action": "view"},
            {"label": "Propostas aprovadas", "route_name": "admin-shell:growth-proposals-approved", "permission_domain": "dashboard", "permission_action": "view"},
        ]
        return context

    def get_growth_breadcrumbs(self, current_label):
        return [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Growth Engine", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "growth-engine"}},
            {"label": current_label, "url": None},
        ]


def livia_growth_leads_queryset():
    return Lead.objects.select_related("source", "campaign", "assigned_to").filter(
        metadata__source=LIVIA_METADATA_SOURCE,
    )


def next_commercial_proposal_number():
    return f"GPRO-{timezone.localdate().year}-{CommercialProposal.objects.count() + 1:04d}"


def find_commercial_proposal_linked_to_lead(lead: Lead):
    proposal_id_meta = (lead.metadata or {}).get("proposal_id")
    if proposal_id_meta is not None:
        cached = CommercialProposal.objects.filter(pk=proposal_id_meta).first()
        if cached:
            return cached
    by_fk = CommercialProposal.objects.filter(lead=lead).order_by("-created_at").first()
    if by_fk:
        return by_fk
    return CommercialProposal.objects.filter(metadata__marketplace_lead_id=lead.pk).order_by("-created_at").first()


def persist_marketplace_lead_as_commercial_proposal(*, lead: Lead, user):
    meta = lead.metadata or {}
    product_title = (meta.get("product_title") or "").strip()
    product_slug = (meta.get("product_slug") or "").strip()
    product_line = (product_title or product_slug).strip()

    summary_lines = [
        "Demanda originada pelo Marketplace E-com Smart360 (canal B2B técnico sob consulta, sem fluxo transacional automatizado).",
        "Este rascunho consolida dados da solicitação de orçamento recebida; valores, SLA, garantias e especificações finais ficam sob validação conjunta das áreas comercial e técnica.",
    ]
    if meta.get("request_type"):
        summary_lines.append(f"Tipo de solicitação registrado: {meta.get('request_type')}.")
    if product_title:
        summary_lines.append(f"Produto / solução citada pelo cliente (catálogo): {product_title}.")
    elif product_slug:
        summary_lines.append(f"Identificador de catálogo (slug): {product_slug}.")
    for aux_key in ("brand", "supplier", "category", "application_area"):
        if meta.get(aux_key):
            summary_lines.append(f"{aux_key.replace('_', ' ').title()} (contexto): {meta[aux_key]}.")
    if lead.notes:
        summary_lines.append("Observações operacionais do lead:")
        summary_lines.append(lead.notes)

    scope_chunks = []
    scope_chunks.append(
        "Escopo inicial (baseline comercial/tecnológico):\n"
        "• responder à solicitação recebida no marketplace técnico, alinhando a linha solicitada aos requisitos de integração/indústria informados;"
        "\n• levantamento de pontos para compatibilização (energia, automação existente, interface de campo, ERP/SCADA onde aplicável);"
        "\n• fechamento de escopo físico/logístico apenas após revisão humana das condições e documentação técnica."
    )
    if product_title or product_slug:
        scope_chunks.append(
            "Referência solicitada pelo cliente — "
            f"título catalogado: {product_title or '—'}; slug: {product_slug or '—'}."
        )
    for aux_key in ("brand", "supplier", "category", "application_area"):
        if meta.get(aux_key):
            scope_chunks.append(f"{aux_key.replace('_', ' ').title()} (marketplace): {meta[aux_key]}")

    now = timezone.now()
    authenticated = getattr(user, "is_authenticated", False)
    phone_guess = lead.whatsapp or lead.phone or ""
    proposal = CommercialProposal(
        proposal_number=next_commercial_proposal_number(),
        lead=lead,
        status=CommercialProposal.Status.DRAFT,
        company_name=lead.company_name,
        contact_name=lead.contact_name,
        email=lead.email,
        phone=str(phone_guess)[:30],
        service_interest=product_line[:180] if product_line else "",
        urgency="",
        origin="marketplace_ecom",
        summary="\n".join(summary_lines),
        scope="\n".join(scope_chunks) if scope_chunks else "",
        customer_message=(
            "Prezados,\n\n"
            "Esta mensagem faz referência ao orçamento solicitado através do nosso Marketplace técnico B2B (catálogo sob consulta).\n\n"
            "Apresentamos a seguir uma proposta comercial em formato de minuta, elaborada a partir das informações fornecidas no pedido inicial. "
            "Valores, prazos, responsabilidades e condições de entrega/execução serão confirmados após revisão pela nossa equipe comercial.",
        ),
        total_value=0,
        created_by=user if authenticated else None,
        updated_by=user if authenticated else None,
    )
    proposal.metadata = {
        "source": "marketplace_ecom",
        "marketplace_lead_id": lead.id,
        "lead_id": lead.id,
        "lead_public_id": str(lead.public_id),
        "product_slug": product_slug or None,
        "product_title": product_title or None,
        "request_type": meta.get("request_type"),
        "proposal_origin": "marketplace_ecom",
        "growth_engine_quick_create": True,
        "brand": meta.get("brand"),
        "supplier": meta.get("supplier"),
        "category": meta.get("category"),
        "application_area": meta.get("application_area"),
    }
    proposal.save()

    lead_meta = {**meta}
    lead_meta.update(
        {
            "proposal_id": proposal.id,
            "proposal_number": proposal.proposal_number,
            "proposal_created_at": now.isoformat(),
            "proposal_origin": "marketplace_ecom",
            "last_action": "marketplace-create-proposal",
            "last_action_at": now.isoformat(),
            "last_action_by": getattr(user, "email", "") or str(getattr(user, "pk", "")),
        }
    )
    lead.metadata = lead_meta
    lead.status = Lead.Status.PROPOSAL
    lead.save()

    create_lead_interaction(
        lead=lead,
        user=user,
        summary=(
            f"Proposta comercial {proposal.proposal_number} criada automaticamente "
            "a partir do lead do Marketplace E-com."
        ),
    )

    return proposal


def operational_forward_display_context(proposal):
    """Dados já registrados para o encaminhamento operacional (exibição no detalhe)."""
    from django.utils.dateparse import parse_datetime

    proposal_md = getattr(proposal, "metadata", None) or {}
    at_raw = proposal_md.get("operational_forwarded_at")
    if not at_raw:
        return None

    at_display = str(at_raw)
    try:
        if isinstance(at_raw, str):
            at_dt = parse_datetime(at_raw.replace("Z", "+00:00"))
            if at_dt is not None:
                at_dt_local = timezone.localtime(at_dt) if timezone.is_aware(at_dt) else at_dt
                at_display = at_dt_local.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        pass

    by_label = None
    uid = proposal_md.get("operational_forwarded_by_id")
    if uid is not None:
        try:
            user_pk = int(uid)
        except (TypeError, ValueError):
            user_pk = None
        if user_pk is not None:
            fwd_user = get_user_model().objects.filter(pk=user_pk).first()
            if fwd_user is not None:
                label = resolve_user_display_label(fwd_user)
                by_label = label or None

    note = proposal_md.get("operational_forward_note") or ""

    return {
        "at_display": at_display,
        "by_label": by_label,
        "note": note,
    }


class GrowthLiviaLeadListView(GrowthDashboardBaseView):
    template_name = "admin_shell/growth_livia_leads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get("status", "")
        queryset = livia_growth_leads_queryset().order_by("-created_at")
        if status:
            queryset = queryset.filter(status=status)

        total = livia_growth_leads_queryset().count()
        won = livia_growth_leads_queryset().filter(status=Lead.Status.WON).count()
        conversion_rate = round((won / total) * 100, 1) if total else 0
        pending_handoffs = LiviaHandoffRequest.objects.filter(status=LiviaHandoffRequest.Status.PENDING).count()

        context["page_title"] = "Leads da Lívia"
        context["page_description"] = "Leads sincronizados pela assistente Lívia dentro do pipeline do Growth Engine."
        context["breadcrumbs"] = self.get_growth_breadcrumbs("Leads da Lívia")
        context["leads"] = queryset[:100]
        context["status_choices"] = Lead.Status.choices
        context["current_status"] = status
        context["summary_cards"] = [
            {"label": "Leads da Lívia", "value": total},
            {"label": "Handoffs pendentes", "value": pending_handoffs},
            {"label": "Taxa de conversão", "value": f"{conversion_rate}%"},
        ]
        return context


class GrowthMarketplaceLeadListView(GrowthDashboardBaseView):
    template_name = "dashboard/growth/marketplace_leads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        queryset = marketplace_growth_leads_queryset().order_by("-created_at")

        status_filter = request.GET.get("status", "").strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        queryset = apply_period_filter(queryset, request)

        search_query = request.GET.get("q", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(company_name__icontains=search_query)
                | Q(contact_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phone__icontains=search_query)
                | Q(whatsapp__icontains=search_query)
                | Q(metadata__product_title__icontains=search_query)
                | Q(metadata__product_slug__icontains=search_query)
            )

        total_qs = marketplace_growth_leads_queryset()

        context["page_title"] = "Leads — Marketplace E-com"
        context["page_description"] = "Leads originados pelo fluxo de solicitação de orçamento do Marketplace."
        context["breadcrumbs"] = self.get_growth_breadcrumbs("Leads Marketplace")
        context["marketplace_lead_rows"] = [marketplace_lead_list_row_dict(lead_obj) for lead_obj in queryset[:200]]
        context["status_choices"] = Lead.Status.choices
        context["current_status"] = status_filter
        context["search_query"] = search_query
        context["date_from"] = request.GET.get("date_from", "").strip()
        context["date_to"] = request.GET.get("date_to", "").strip()
        context["summary_cards"] = [
            {"label": "Total marketplace", "value": total_qs.count()},
            {"label": "Novos (30 dias)", "value": total_qs.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()},
            {"label": "Em pipeline", "value": total_qs.filter(status__in=[Lead.Status.NEW, Lead.Status.CONTACTED, Lead.Status.QUALIFIED, Lead.Status.PROPOSAL]).count()},
        ]
        return context


class GrowthMarketplaceLeadDetailView(GrowthDashboardBaseView):
    template_name = "dashboard/growth/marketplace_lead_detail.html"

    def get_marketplace_lead(self):
        qs = marketplace_growth_leads_queryset().select_related(
            "source",
            "campaign",
            "assigned_to",
            "created_by",
        ).prefetch_related("interactions")
        return get_object_or_404(qs, pk=self.kwargs["lead_id"])

    def _metadata_rows(self, lead):
        rows = []
        for key in sorted((lead.metadata or {}).keys(), key=str):
            value = (lead.metadata or {}).get(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            rows.append((str(key), value))
        return rows

    def get_context_data(self, interaction_form=None, status_form=None, **kwargs):
        context = super().get_context_data(**kwargs)
        lead = self.get_marketplace_lead()
        if interaction_form is None:
            interaction_form = MarketplaceLeadInteractionForm()
        if status_form is None:
            status_form = MarketplaceLeadStatusForm(initial={"status": lead.status})
        context["page_title"] = f"Marketplace — {lead.company_name}"
        context["page_description"] = "Detalhes do lead e registro comercial proveniente do Marketplace E-com."
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Growth Engine", "url": "admin-shell:module-page", "route_kwargs": {"module_slug": "growth-engine"}},
            {"label": "Leads Marketplace", "url": "admin-shell:growth-marketplace-leads"},
            {"label": lead.company_name, "url": None},
        ]
        context["lead"] = lead
        context["metadata_rows"] = self._metadata_rows(lead)
        context["interaction_form"] = interaction_form
        context["status_form"] = status_form
        context["interactions"] = lead.interactions.all()
        context["commercial_proposal"] = find_commercial_proposal_linked_to_lead(lead)
        return context

    def post(self, request, *args, **kwargs):
        lead = self.get_marketplace_lead()
        detail_url = reverse("admin-shell:growth-marketplace-lead-detail", kwargs={"lead_id": lead.id})

        if "interaction_submit" in request.POST:
            interaction_form = MarketplaceLeadInteractionForm(request.POST)
            status_form = MarketplaceLeadStatusForm(initial={"status": lead.status})
            if interaction_form.is_valid():
                inst = interaction_form.save(commit=False)
                inst.lead = lead
                inst.owner = request.user if getattr(request.user, "is_authenticated", False) else None
                inst.happened_at = timezone.now()
                inst.save()
                messages.success(request, "Interação registrada com sucesso.")
                return redirect(detail_url)
            messages.error(request, "Não foi possível registrar a interação. Verifique os campos destacados.")
            ctx = self.get_context_data(interaction_form=interaction_form, status_form=status_form)
            return render(request, self.template_name, ctx, status=400)

        if "status_submit" in request.POST:
            interaction_form = MarketplaceLeadInteractionForm()
            status_form = MarketplaceLeadStatusForm(request.POST)
            if status_form.is_valid():
                lead.status = status_form.cleaned_data["status"]
                lead.save()
                messages.success(request, "Status do lead atualizado.")
                return redirect(detail_url)
            messages.error(request, "Status inválido. Tente novamente.")
            ctx = self.get_context_data(interaction_form=interaction_form, status_form=status_form)
            return render(request, self.template_name, ctx, status=400)

        messages.error(request, "Nenhuma ação reconhecida.")
        return redirect(detail_url)


class GrowthMarketplaceLeadCreateProposalView(GrowthDashboardBaseView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        lead = get_object_or_404(marketplace_growth_leads_queryset(), pk=self.kwargs["lead_id"])
        existing = find_commercial_proposal_linked_to_lead(lead)
        if existing:
            messages.warning(
                request,
                "Este lead do Marketplace já possui proposta comercial vinculada. Abrindo o registro existente.",
            )
            return redirect("admin-shell:growth-proposal-detail", proposal_id=existing.id)
        proposal = persist_marketplace_lead_as_commercial_proposal(lead=lead, user=request.user)
        messages.success(
            request,
            f"Proposta {proposal.proposal_number} criada em rascunho a partir deste lead. Revise antes do envio ao cliente.",
        )
        return redirect("admin-shell:growth-proposal-detail", proposal_id=proposal.id)


class GrowthLeadDetailView(GrowthDashboardBaseView):
    template_name = "admin_shell/growth_lead_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead = get_object_or_404(
            Lead.objects.select_related("source", "campaign", "assigned_to", "created_by").prefetch_related("interactions", "commercial_proposals"),
            pk=self.kwargs["lead_id"],
        )
        livia_lead = None
        if lead.metadata.get("source") == LIVIA_METADATA_SOURCE:
            livia_lead_id = lead.metadata.get("livia_lead_id")
            livia_query = LiviaLeadCapture.objects.select_related("conversation")
            if livia_lead_id:
                livia_lead = livia_query.filter(pk=livia_lead_id).first()
            if livia_lead is None:
                livia_lead = livia_query.filter(crm_lead_id=lead.id).order_by("-created_at").first()

        proposal = self._proposal_for_lead(lead)
        context["page_title"] = f"Lead: {lead.company_name}"
        context["page_description"] = "Detalhe comercial do lead no Growth Engine."
        context["breadcrumbs"] = self.get_growth_breadcrumbs("Detalhe do lead")
        context["lead"] = lead
        context["interactions"] = lead.interactions.all()[:20]
        context["livia_lead"] = livia_lead
        context["proposal"] = proposal
        return context

    def _proposal_for_lead(self, lead):
        proposal_id = (lead.metadata or {}).get("proposal_id")
        if proposal_id:
            proposal = CommercialProposal.objects.filter(pk=proposal_id).first()
            if proposal:
                return proposal
        return lead.commercial_proposals.order_by("-created_at").first()


class GrowthLeadActionView(GrowthDashboardBaseView, View):
    ACTIONS = {
        "mark-contacted": (Lead.Status.CONTACTED, "Lead marcado como contatado."),
        "mark-lost": (Lead.Status.LOST, "Lead marcado como perdido."),
        "mark-converted": (Lead.Status.WON, "Lead marcado como convertido."),
        "move-to-proposal": (Lead.Status.PROPOSAL, "Lead movido para proposta."),
    }

    def post(self, request, *args, **kwargs):
        lead = get_object_or_404(Lead, pk=kwargs["lead_id"])
        action = kwargs["action"]
        if action not in self.ACTIONS:
            messages.error(request, "Ação comercial inválida.")
            return redirect("admin-shell:growth-lead-detail", lead_id=lead.id)

        status, message = self.ACTIONS[action]
        self._apply_action(lead=lead, action=action, status=status, user=request.user)
        messages.success(request, message)

        if action == "move-to-proposal":
            messages.info(request, "Dados do lead foram preparados. Revise e confirme a proposta antes de salvar.")
            return redirect("admin-shell:growth-lead-create-proposal", lead_id=lead.id)
        return redirect("admin-shell:growth-lead-detail", lead_id=lead.id)

    def _apply_action(self, *, lead, action, status, user):
        now = timezone.now()
        metadata = {**(lead.metadata or {})}
        metadata.update(
            {
                "last_action": action,
                "last_action_at": now.isoformat(),
                "last_action_by": getattr(user, "email", "") or str(getattr(user, "pk", "")),
            }
        )
        if metadata.get("source") == LIVIA_METADATA_SOURCE:
            metadata["livia_origin"] = True
        if action == "move-to-proposal":
            metadata["proposal_prefill"] = build_proposal_initial(lead)
            metadata["proposal_requires_human_confirmation"] = True

        lead.status = status
        lead.metadata = metadata
        lead.save(update_fields=["status", "metadata", "updated_at"])
        create_lead_interaction(lead=lead, user=user, summary=self._interaction_summary(action))

    def _interaction_summary(self, action):
        return {
            "mark-contacted": "Lead marcado como contatado no Growth Engine.",
            "mark-lost": "Lead marcado como perdido no Growth Engine.",
            "mark-converted": "Lead marcado como convertido no Growth Engine.",
            "move-to-proposal": "Lead movido para etapa de proposta; criação de proposta pendente de confirmação humana.",
        }[action]


class GrowthLeadCreateProposalView(GrowthDashboardBaseView):
    template_name = "admin_shell/growth_proposal_form.html"

    def get(self, request, *args, **kwargs):
        lead = self.get_lead()
        existing = self.get_existing_proposal(lead)
        if existing:
            messages.warning(request, "Este lead já possui proposta vinculada. Revise a proposta existente antes de criar outra.")
            return redirect("admin-shell:growth-proposal-detail", proposal_id=existing.id)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        lead = self.get_lead()
        existing = self.get_existing_proposal(lead)
        if existing:
            messages.warning(request, "Este lead já possui proposta vinculada. Revise a proposta existente antes de criar outra.")
            return redirect("admin-shell:growth-proposal-detail", proposal_id=existing.id)

        form = CommercialProposalForm(request.POST)
        if not form.is_valid():
            return self.form_invalid(form)

        proposal = form.save(commit=False)
        proposal.proposal_number = next_commercial_proposal_number()
        proposal.lead = lead
        proposal.created_by = request.user if request.user.is_authenticated else None
        proposal.updated_by = request.user if request.user.is_authenticated else None
        proposal.metadata = {
            "source": "growth_engine_lead",
            "lead_id": lead.id,
            "lead_public_id": str(lead.public_id),
            "livia_origin": lead.metadata.get("source") == LIVIA_METADATA_SOURCE,
            "livia_conversation_id": lead.metadata.get("livia_conversation_id"),
            "proposal_origin": LIVIA_METADATA_SOURCE if lead.metadata.get("source") == LIVIA_METADATA_SOURCE else "growth_engine",
        }
        proposal.save()

        metadata = {**(lead.metadata or {})}
        metadata.update(
            {
                "proposal_created_at": timezone.now().isoformat(),
                "proposal_id": proposal.id,
                "proposal_number": proposal.proposal_number,
                "proposal_origin": LIVIA_METADATA_SOURCE if metadata.get("source") == LIVIA_METADATA_SOURCE else "growth_engine",
                "last_action": "create-proposal",
                "last_action_at": timezone.now().isoformat(),
                "last_action_by": getattr(request.user, "email", "") or str(getattr(request.user, "pk", "")),
            }
        )
        if metadata.get("source") == LIVIA_METADATA_SOURCE:
            metadata["livia_origin"] = True
        lead.status = Lead.Status.PROPOSAL
        lead.metadata = metadata
        lead.save(update_fields=["status", "metadata", "updated_at"])
        create_lead_interaction(
            lead=lead,
            user=request.user,
            summary=f"Proposta comercial {proposal.proposal_number} criada a partir do lead.",
        )
        messages.success(request, "Proposta criada e vinculada ao lead.")
        return redirect("admin-shell:growth-proposal-detail", proposal_id=proposal.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead = self.get_lead()
        context["page_title"] = "Criar proposta"
        context["page_description"] = "Revise os dados do lead antes de confirmar a criação da proposta comercial."
        context["breadcrumbs"] = self.get_growth_breadcrumbs("Criar proposta")
        context["lead"] = lead
        context["form"] = kwargs.get("form") or CommercialProposalForm(initial=build_proposal_initial(lead))
        return context

    def get_lead(self):
        return get_object_or_404(Lead, pk=self.kwargs["lead_id"])

    def get_existing_proposal(self, lead):
        proposal_id = (lead.metadata or {}).get("proposal_id")
        if proposal_id:
            proposal = CommercialProposal.objects.filter(pk=proposal_id).first()
            if proposal:
                return proposal
        return CommercialProposal.objects.filter(lead=lead).order_by("-created_at").first()


class GrowthApprovedProposalsListView(GrowthDashboardBaseView):
    """Lista propostas comerciais já aceitas (fila para encaminhamento operacional)."""

    template_name = "admin_shell/growth_proposals_approved.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = (
            CommercialProposal.objects.filter(status=CommercialProposal.Status.ACCEPTED)
            .select_related("lead", "lead__source")
            .order_by("-updated_at")
        )
        proposals = list(qs[:500])
        context["page_title"] = "Propostas aprovadas"
        context["page_description"] = (
            "Visão das propostas aceitas pelo cliente, prontas para encaminhamento operacional. "
            "Não há criação automática de OS nesta etapa."
        )
        context["breadcrumbs"] = self.get_growth_breadcrumbs("Propostas aprovadas")
        context["approved_proposal_rows"] = [
            {"proposal": proposal, "is_marketplace": commercial_proposal_is_marketplace_origin(proposal)}
            for proposal in proposals
        ]
        context["approved_proposals_total"] = qs.count()
        return context


class GrowthProposalDetailView(GrowthDashboardBaseView):
    template_name = "admin_shell/growth_proposal_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proposal = get_object_or_404(CommercialProposal.objects.select_related("lead"), pk=self.kwargs["proposal_id"])
        is_mp = commercial_proposal_is_marketplace_origin(proposal)
        mpl_id = resolve_marketplace_lead_id_for_detail_link(proposal) if is_mp else None

        context["page_title"] = f"Proposta {proposal.proposal_number}"
        context["page_description"] = (
            "Proposta comercial originada pela solicitação de orçamento no Marketplace técnico B2B (canal sob consulta)."
            if is_mp
            else "Proposta comercial criada no Growth Engine."
        )
        context["breadcrumbs"] = self.get_growth_breadcrumbs("Proposta")
        context["proposal"] = proposal
        context["lead"] = proposal.lead
        context["is_marketplace_proposal"] = is_mp
        context["marketplace_lead_detail_id"] = mpl_id
        proposal_md = getattr(proposal, "metadata", None) or {}
        lead_md = getattr(proposal.lead, "metadata", None) or {} if proposal.lead_id else {}

        def _meta_pick(key: str):
            val = proposal_md.get(key)
            if val:
                return val
            val = lead_md.get(key)
            return val if val is not None else ""

        context["marketplace_meta"] = {
            "product_title": (_meta_pick("product_title") or ""),
            "product_slug": (_meta_pick("product_slug") or ""),
            "brand": (_meta_pick("brand") or ""),
            "supplier": (_meta_pick("supplier") or ""),
            "category": (_meta_pick("category") or ""),
            "application_area": (_meta_pick("application_area") or ""),
            "request_type": (_meta_pick("request_type") or ""),
        }
        lead_notes = (getattr(proposal.lead, "notes", None) or "") if proposal.lead_id else ""
        context["marketplace_lead_notes"] = lead_notes or ""
        context["marketplace_email_suggested_body"] = marketplace_proposal_suggested_email_intro(proposal) if is_mp else ""
        st = proposal.status
        context["can_mark_proposal_sent"] = st == CommercialProposal.Status.DRAFT
        context["can_approve_proposal"] = st in (
            CommercialProposal.Status.DRAFT,
            CommercialProposal.Status.SENT,
        )
        context["can_reject_proposal"] = st in (
            CommercialProposal.Status.DRAFT,
            CommercialProposal.Status.SENT,
        )
        context["show_operational_next_step"] = st == CommercialProposal.Status.ACCEPTED
        of_display = operational_forward_display_context(proposal)
        context["operational_forward_complete"] = of_display is not None
        context["operational_forward"] = of_display or {}
        context["show_operational_forward_form"] = context["show_operational_next_step"] and not context["operational_forward_complete"]
        context["operational_forward_form"] = OperationalForwardNoteForm() if context["show_operational_forward_form"] else None
        context["show_approved_proposals_queue_link"] = st == CommercialProposal.Status.ACCEPTED
        return context


_COMMERCIAL_PROPOSAL_ACTION_TRANSITIONS = {
    "mark-sent": {CommercialProposal.Status.DRAFT: CommercialProposal.Status.SENT},
    "approve": {
        CommercialProposal.Status.DRAFT: CommercialProposal.Status.ACCEPTED,
        CommercialProposal.Status.SENT: CommercialProposal.Status.ACCEPTED,
    },
    "reject": {
        CommercialProposal.Status.DRAFT: CommercialProposal.Status.REJECTED,
        CommercialProposal.Status.SENT: CommercialProposal.Status.REJECTED,
    },
}


_COMMERCIAL_PROPOSAL_ACTION_SUCCESS_MESSAGES = {
    "mark-sent": "Proposta marcada como enviada (registro interno apenas; nenhum e-mail foi enviado automaticamente).",
    "approve": "Proposta com status atualizado para «aceita» (registro interno do pipeline comercial — não há integração externa nem e-mail nesta etapa).",
    "reject": "Proposta marcada como rejeitada.",
}


class GrowthCommercialProposalActionView(GrowthDashboardBaseView, View):
    """POST: atualiza CommercialProposal.status com transição permitida."""

    http_method_names = ["post"]
    action_name = "mark-sent"

    def post(self, request, *args, proposal_id, **kwargs):
        proposal = get_object_or_404(CommercialProposal.objects.select_related("lead"), pk=proposal_id)
        action = getattr(self, "action_name", "mark-sent")
        transitions = _COMMERCIAL_PROPOSAL_ACTION_TRANSITIONS.get(action)
        if transitions is None:
            messages.error(request, "Ação comercial não reconhecida.")
            return redirect("admin-shell:growth-proposal-detail", proposal_id=proposal.id)

        new_status = transitions.get(proposal.status)
        if new_status is None:
            messages.warning(
                request,
                "Esta ação não está disponível para o status atual da proposta.",
            )
            return redirect("admin-shell:growth-proposal-detail", proposal_id=proposal.id)

        proposal.status = new_status
        if getattr(request.user, "is_authenticated", False):
            proposal.updated_by = request.user
        proposal.save()

        if proposal.lead_id:
            create_lead_interaction(
                lead=proposal.lead,
                user=request.user,
                summary=(
                    f"Proposta comercial {proposal.proposal_number}: status atualizado para "
                    f"«{proposal.get_status_display()}» (ação comercial: {action})."
                ),
            )

        messages.success(
            request,
            _COMMERCIAL_PROPOSAL_ACTION_SUCCESS_MESSAGES.get(action, "Status da proposta atualizado."),
        )
        return redirect("admin-shell:growth-proposal-detail", proposal_id=proposal.id)


class GrowthCommercialProposalOperationalForwardView(GrowthDashboardBaseView, View):
    """POST: registra encaminhamento operacional (somente accepted, uma vez por proposta)."""

    http_method_names = ["post"]

    def post(self, request, *args, proposal_id, **kwargs):
        proposal = get_object_or_404(CommercialProposal.objects.select_related("lead"), pk=proposal_id)
        redirect_detail = redirect("admin-shell:growth-proposal-detail", proposal_id=proposal.id)

        if proposal.status != CommercialProposal.Status.ACCEPTED:
            messages.warning(
                request,
                "Encaminhamento operacional só está disponível para propostas aprovadas (aceitas).",
            )
            return redirect_detail

        md = dict(proposal.metadata or {})
        if md.get("operational_forwarded_at"):
            messages.warning(
                request,
                "Esta proposta já foi registrada como encaminhada à área operacional.",
            )
            return redirect_detail

        form = OperationalForwardNoteForm(request.POST)
        if not form.is_valid():
            messages.error(
                request,
                "Informe uma observação válida para o encaminhamento (mínimo 3 caracteres).",
            )
            return redirect_detail

        note = form.cleaned_data["note"].strip()
        now = timezone.now()

        md["operational_forwarded_at"] = now.isoformat()
        if getattr(request.user, "is_authenticated", False):
            md["operational_forwarded_by_id"] = request.user.pk
        md["operational_forward_note"] = note
        proposal.metadata = md

        if getattr(request.user, "is_authenticated", False):
            proposal.updated_by = request.user
        proposal.save()

        if proposal.lead_id:
            summary = (
                "Proposta encaminhada para etapa operacional. "
                f"Proposta: {proposal.proposal_number}. "
                f"Observação: {note}"
            )
            create_lead_interaction(lead=proposal.lead, user=request.user, summary=summary)

        messages.success(
            request,
            "Encaminhamento operacional registrado com sucesso.",
        )
        return redirect_detail


def build_proposal_initial(lead):
    metadata = lead.metadata or {}
    return {
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "email": lead.email,
        "phone": lead.whatsapp or lead.phone,
        "service_interest": metadata.get("service_interest", ""),
        "urgency": metadata.get("urgency", ""),
        "origin": LIVIA_METADATA_SOURCE if metadata.get("source") == LIVIA_METADATA_SOURCE else metadata.get("source", "growth_engine"),
        "summary": metadata.get("capture_summary") or lead.notes,
        "scope": metadata.get("service_interest", ""),
        "customer_message": "Proposta em rascunho para revisão humana antes do envio ao cliente.",
        "total_value": 0,
    }


def create_lead_interaction(*, lead, user, summary):
    return LeadInteraction.objects.create(
        lead=lead,
        interaction_type=LeadInteraction.InteractionType.NOTE,
        channel=LeadInteraction.Channel.OTHER,
        owner=user if getattr(user, "is_authenticated", False) else None,
        summary=summary,
    )
