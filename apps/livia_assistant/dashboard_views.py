from django.contrib import messages
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.admin_shell.views import ShellContextMixin

from .crm_bridge import LiviaCRMBridge
from .forms import LiviaKnowledgeItemForm
from .models import LiviaConversation, LiviaHandoffRequest, LiviaKnowledgeItem, LiviaLeadCapture


class LiviaDashboardBaseView(ShellContextMixin, TemplateView):
    permission_domain = "ai_agents_admin"
    permission_action = "view"
    enforce_billing_access = False
    current_module_slug = "ai-agents-center"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_module_slug"] = self.current_module_slug
        context["page_actions"] = [
            {"label": "Conversas", "route_name": "admin-shell:livia-conversations", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Leads", "route_name": "admin-shell:livia-leads", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Handoffs", "route_name": "admin-shell:livia-handoffs", "permission_domain": "ai_agents_admin", "permission_action": "view"},
            {"label": "Conhecimento", "route_name": "admin-shell:livia-knowledge", "permission_domain": "ai_agents_admin", "permission_action": "view"},
        ]
        return context

    def get_livia_breadcrumbs(self, current_label):
        return [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Intelligence", "url": None},
            {"label": "Lívia Assistente", "url": "admin-shell:livia-dashboard"},
            {"label": current_label, "url": None},
        ]


class LiviaDashboardView(LiviaDashboardBaseView):
    template_name = "admin_shell/livia_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Lívia Assistente"
        context["page_description"] = "Triagem comercial, leads capturados e handoffs da assistente pública da Smart Control Brasil."
        context["breadcrumbs"] = self.get_livia_breadcrumbs("Visão geral")
        context["summary_cards"] = [
            {"label": "Conversas abertas", "value": LiviaConversation.objects.filter(status=LiviaConversation.Status.OPEN).count()},
            {"label": "Leads qualificados", "value": LiviaLeadCapture.objects.filter(is_qualified=True).count()},
            {"label": "Handoffs pendentes", "value": LiviaHandoffRequest.objects.filter(status=LiviaHandoffRequest.Status.PENDING).count()},
            {"label": "Itens ativos", "value": LiviaKnowledgeItem.objects.filter(is_active=True).count()},
        ]
        context["recent_conversations"] = self._conversation_queryset()[:8]
        context["recent_leads"] = LiviaLeadCapture.objects.select_related("conversation").order_by("-created_at")[:8]
        context["pending_handoffs"] = LiviaHandoffRequest.objects.select_related("conversation").filter(status=LiviaHandoffRequest.Status.PENDING).order_by("-created_at")[:8]
        return context

    def _conversation_queryset(self):
        return LiviaConversation.objects.annotate(
            message_count=Count("messages"),
            last_message_at=Max("messages__created_at"),
        ).order_by("-updated_at")


class LiviaConversationListView(LiviaDashboardBaseView):
    template_name = "admin_shell/livia_conversations.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get("status", "")
        queryset = LiviaConversation.objects.annotate(
            message_count=Count("messages"),
            last_message_at=Max("messages__created_at"),
        ).order_by("-updated_at")
        if status:
            queryset = queryset.filter(status=status)

        context["page_title"] = "Conversas da Lívia"
        context["page_description"] = "Histórico recente de atendimentos públicos e pré-qualificação comercial."
        context["breadcrumbs"] = self.get_livia_breadcrumbs("Conversas")
        context["conversations"] = queryset[:100]
        context["current_status"] = status
        context["status_choices"] = LiviaConversation.Status.choices
        return context


class LiviaConversationDetailView(LiviaDashboardBaseView):
    template_name = "admin_shell/livia_conversation_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = get_object_or_404(
            LiviaConversation.objects.prefetch_related("messages", "lead_captures", "handoff_requests"),
            pk=self.kwargs["conversation_id"],
        )
        context["page_title"] = f"Conversa #{conversation.pk}"
        context["page_description"] = "Mensagens, dados capturados e encaminhamentos da conversa."
        context["breadcrumbs"] = self.get_livia_breadcrumbs(f"Conversa #{conversation.pk}")
        context["conversation"] = conversation
        context["messages_list"] = conversation.messages.all()
        context["lead_captures"] = conversation.lead_captures.all()
        context["handoff_requests"] = conversation.handoff_requests.all()
        return context


class LiviaLeadListView(LiviaDashboardBaseView):
    template_name = "admin_shell/livia_leads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        urgency = self.request.GET.get("urgency", "")
        qualified = self.request.GET.get("qualified", "")
        queryset = LiviaLeadCapture.objects.select_related("conversation").order_by("-created_at")
        if urgency:
            queryset = queryset.filter(urgency=urgency)
        if qualified in {"true", "false"}:
            queryset = queryset.filter(is_qualified=(qualified == "true"))

        context["page_title"] = "Leads da Lívia"
        context["page_description"] = "Dados comerciais capturados pela assistente pública."
        context["breadcrumbs"] = self.get_livia_breadcrumbs("Leads")
        context["leads"] = queryset[:100]
        context["current_urgency"] = urgency
        context["current_qualified"] = qualified
        context["urgency_choices"] = LiviaLeadCapture.Urgency.choices
        return context


class LiviaLeadDetailView(LiviaDashboardBaseView):
    template_name = "admin_shell/livia_lead_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead = get_object_or_404(
            LiviaLeadCapture.objects.select_related("conversation"),
            pk=self.kwargs["lead_id"],
        )
        context["page_title"] = f"Lead #{lead.pk}"
        context["page_description"] = "Ações comerciais e dados capturados pela Lívia."
        context["breadcrumbs"] = self.get_livia_breadcrumbs(f"Lead #{lead.pk}")
        context["lead"] = lead
        context["handoff_requests"] = lead.conversation.handoff_requests.all()
        return context


class LiviaLeadActionView(LiviaDashboardBaseView, View):
    def post(self, request, *args, **kwargs):
        lead = get_object_or_404(LiviaLeadCapture.objects.select_related("conversation"), pk=kwargs["lead_id"])
        action = kwargs["action"]
        bridge = LiviaCRMBridge()

        if action == "send-to-crm":
            crm_lead = bridge.create_or_update_crm_lead(lead)
            if crm_lead is None:
                messages.warning(request, "Não foi possível enviar ao CRM. Verifique se o lead está qualificado e se o Growth Engine está disponível.")
            else:
                messages.success(request, "Lead enviado ao CRM.")
        elif action == "mark-contacted":
            bridge.mark_contacted(lead)
            messages.success(request, "Lead marcado como contatado.")
        elif action == "create-handoff":
            bridge.create_livia_handoff(lead)
            messages.success(request, "Handoff criado para atendimento humano.")
        else:
            messages.error(request, "Ação inválida.")

        return redirect("admin-shell:livia-lead-detail", lead_id=lead.id)


class LiviaHandoffListView(LiviaDashboardBaseView):
    template_name = "admin_shell/livia_handoffs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get("status", LiviaHandoffRequest.Status.PENDING)
        queryset = LiviaHandoffRequest.objects.select_related("conversation").order_by("-created_at")
        if status:
            queryset = queryset.filter(status=status)

        context["page_title"] = "Handoffs da Lívia"
        context["page_description"] = "Solicitações que exigem atendimento humano, urgência técnica ou continuidade comercial."
        context["breadcrumbs"] = self.get_livia_breadcrumbs("Handoffs")
        context["handoffs"] = queryset[:100]
        context["current_status"] = status
        context["status_choices"] = LiviaHandoffRequest.Status.choices
        return context


class LiviaKnowledgeListView(LiviaDashboardBaseView):
    template_name = "admin_shell/livia_knowledge.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.request.GET.get("category", "")
        active = self.request.GET.get("active", "")
        queryset = LiviaKnowledgeItem.objects.all().order_by("-priority", "title")
        if category:
            queryset = queryset.filter(category=category)
        if active in {"true", "false"}:
            queryset = queryset.filter(is_active=(active == "true"))

        context["page_title"] = "Conhecimento da Lívia"
        context["page_description"] = "Base textual simples usada como contexto auxiliar antes da resposta da assistente."
        context["breadcrumbs"] = self.get_livia_breadcrumbs("Conhecimento")
        context["knowledge_items"] = queryset[:100]
        context["category_choices"] = LiviaKnowledgeItem.Category.choices
        context["current_category"] = category
        context["current_active"] = active
        return context


class LiviaKnowledgeCreateView(LiviaDashboardBaseView):
    template_name = "admin_shell/livia_knowledge_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Novo conhecimento"
        context["page_description"] = "Cadastre uma informação curta e segura para apoiar as respostas da Lívia."
        context["breadcrumbs"] = self.get_livia_breadcrumbs("Novo conhecimento")
        context["form"] = kwargs.get("form") or LiviaKnowledgeItemForm()
        context["submit_label"] = "Criar item"
        return context

    def post(self, request, *args, **kwargs):
        form = LiviaKnowledgeItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Item de conhecimento criado.")
            return redirect("admin-shell:livia-knowledge")
        return self.form_invalid(form)


class LiviaKnowledgeUpdateView(LiviaDashboardBaseView):
    template_name = "admin_shell/livia_knowledge_form.html"

    def get_object(self):
        return get_object_or_404(LiviaKnowledgeItem, pk=self.kwargs["knowledge_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.get_object()
        context["page_title"] = "Editar conhecimento"
        context["page_description"] = "Atualize o contexto usado pela Lívia com cuidado comercial e técnico."
        context["breadcrumbs"] = self.get_livia_breadcrumbs("Editar conhecimento")
        context["form"] = kwargs.get("form") or LiviaKnowledgeItemForm(instance=item)
        context["knowledge_item"] = item
        context["submit_label"] = "Salvar alterações"
        return context

    def post(self, request, *args, **kwargs):
        item = self.get_object()
        form = LiviaKnowledgeItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item de conhecimento atualizado.")
            return redirect("admin-shell:livia-knowledge")
        return self.form_invalid(form)
