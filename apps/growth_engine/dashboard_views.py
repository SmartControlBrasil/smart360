from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.admin_shell.views import ShellContextMixin
from apps.livia_assistant.models import LiviaHandoffRequest, LiviaLeadCapture

from .forms import CommercialProposalForm
from .models import CommercialProposal, Lead, LeadInteraction


LIVIA_METADATA_SOURCE = "livia_assistant"


class GrowthDashboardBaseView(ShellContextMixin, TemplateView):
    permission_domain = "dashboard"
    permission_action = "view"
    enforce_billing_access = False
    current_module_slug = "growth-engine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_module_slug"] = self.current_module_slug
        context["page_actions"] = [
            {"label": "Leads da Lívia", "route_name": "admin-shell:growth-livia-leads", "permission_domain": "dashboard", "permission_action": "view"},
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


class GrowthProposalDetailView(GrowthDashboardBaseView):
    template_name = "admin_shell/growth_proposal_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proposal = get_object_or_404(CommercialProposal.objects.select_related("lead"), pk=self.kwargs["proposal_id"])
        context["page_title"] = f"Proposta {proposal.proposal_number}"
        context["page_description"] = "Proposta comercial criada a partir do Growth Engine."
        context["breadcrumbs"] = self.get_growth_breadcrumbs("Proposta")
        context["proposal"] = proposal
        context["lead"] = proposal.lead
        return context


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
