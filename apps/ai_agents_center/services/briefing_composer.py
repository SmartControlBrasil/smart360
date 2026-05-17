from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.access_control_center.models import UserRoleAssignment
from apps.admin_shell.services.client_portal import get_client_dashboard_context
from apps.admin_shell.services.technician_mobile import (
    get_technician_dashboard_context,
    get_technician_service_listing_context,
)
from apps.ai_agents_center.models import (
    AIBriefing,
    AIBriefingConfiguration,
    AIBriefingDelivery,
    AgentActionProposal,
    AgentAnomalyAttentionFlag,
    AgentAssetAttentionFlag,
    AgentMarketplaceRequestFlag,
    AgentProfitabilityAttentionFlag,
    AgentRecommendation,
    AgentScheduleHealthFlag,
)
from apps.analytics_platform.models import OperationalMetrics
from apps.analytics_platform.services.analytics_service import ExecutiveAnalyticsService
from apps.companies.models import Company, Membership
from apps.notification_center.models import InAppNotification, NotificationChannel, NotificationMessage
from apps.notification_center.services.notification_service import InAppNotificationService, NotificationMessageService
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import OperationalSite


@dataclass(frozen=True)
class BriefingPeriod:
    label: str
    start: timezone.datetime.date
    end: timezone.datetime.date


class AIBriefingComposer:
    DEFAULT_CHANNELS = [
        AIBriefingDelivery.Channel.DASHBOARD,
        AIBriefingDelivery.Channel.IN_APP,
    ]

    AGENT_SLUGS = [
        "maintenance-agent",
        "scheduling-agent",
        "profitability-agent",
        "marketplace-agent",
        "anomaly-agent",
    ]

    @classmethod
    def get_configuration(cls, *, company=None):
        configuration = None
        if company is not None:
            configuration = AIBriefingConfiguration.objects.filter(company=company).first()
        if configuration is None:
            configuration = AIBriefingConfiguration.objects.filter(company__isnull=True).first()
        return configuration

    @classmethod
    def resolve_period(cls, briefing_type: str, *, reference_date=None, start=None, end=None) -> BriefingPeriod:
        reference_date = reference_date or timezone.localdate()
        if briefing_type == AIBriefing.BriefingType.WEEKLY_EXECUTIVE:
            period_end = end or reference_date
            period_start = start or (period_end - timedelta(days=6))
            return BriefingPeriod(label=f"Semana {period_start:%d/%m} a {period_end:%d/%m}", start=period_start, end=period_end)
        if start and end:
            return BriefingPeriod(label=f"{start:%d/%m/%Y} a {end:%d/%m/%Y}", start=start, end=end)
        return BriefingPeriod(label=f"{reference_date:%d/%m/%Y}", start=reference_date, end=reference_date)

    @classmethod
    def _recommendations(cls, *, company, site=None, user=None, audience=None):
        queryset = AgentRecommendation.objects.select_related("agent_run", "agent_run__agent", "company", "site").filter(
            company=company,
            agent_run__agent__slug__in=cls.AGENT_SLUGS,
        ).order_by("-attention_score", "-created_at")
        if site is not None:
            queryset = queryset.filter(Q(site=site) | Q(site__isnull=True))
        if audience == AIBriefing.Audience.TECHNICIAN and user is not None:
            queryset = queryset.filter(
                Q(entity_type="user", entity_id=str(user.id))
                | Q(payload__technician__technician_id=user.id)
                | Q(entity_type="asset")
                | Q(entity_type="")
            )
        return list(queryset[:8])

    @classmethod
    def _proposals(cls, *, company, site=None):
        queryset = AgentActionProposal.objects.select_related("agent_run", "agent_run__agent").filter(
            agent_run__company=company,
            status=AgentActionProposal.Status.PENDING_APPROVAL,
        ).order_by("-created_at")
        if site is not None:
            queryset = queryset.filter(Q(agent_run__site=site) | Q(agent_run__site__isnull=True))
        return list(queryset[:6])

    @classmethod
    def _executive_payload(cls, *, company, site=None, period: BriefingPeriod):
        analytics = ExecutiveAnalyticsService.build_executive_dashboard(
            company=company,
            period_type=OperationalMetrics.PeriodType.DAILY if period.start == period.end else OperationalMetrics.PeriodType.MONTHLY,
            reference_date=period.end,
        )
        attention_assets = list(
            AgentAssetAttentionFlag.objects.select_related("asset", "site", "latest_recommendation")
            .filter(company=company, status__in=["active", "watching"])
            .order_by("-attention_score", "-updated_at")[:5]
        )
        schedule_health = list(
            AgentScheduleHealthFlag.objects.select_related("technician", "site", "latest_recommendation")
            .filter(company=company, status__in=["active", "watching"])
            .order_by("-attention_score", "-updated_at")[:4]
        )
        profitability = list(
            AgentProfitabilityAttentionFlag.objects.select_related("client", "contract", "site", "latest_recommendation")
            .filter(company=company, status__in=["active", "watching"])
            .order_by("-attention_score", "-updated_at")[:4]
        )
        anomalies = list(
            AgentAnomalyAttentionFlag.objects.select_related("site", "asset", "client", "contract", "latest_recommendation")
            .filter(company=company, status__in=["active", "watching"])
            .order_by("-attention_score", "-updated_at")[:4]
        )
        recommendations = cls._recommendations(company=company, site=site, audience=AIBriefing.Audience.MANAGER)
        proposals = cls._proposals(company=company, site=site)
        priorities = []
        for item in recommendations[:3]:
            priorities.append(item.summary)
        if not priorities:
            priorities.append("Operacao sem recomendacoes criticas abertas no escopo atual.")
        alerts = [
            f"Ativos em atencao: {len(attention_assets)}.",
            f"Agenda com risco: {len(schedule_health)} caso(s).",
            f"Rentabilidade em atencao: {len(profitability)} caso(s).",
            f"Anomalias relevantes: {len(anomalies)}.",
        ]
        actions = []
        for proposal in proposals[:3]:
            actions.append(proposal.summary or proposal.title or proposal.action_type)
        if not actions:
            actions.append("Revisar recomendacoes abertas e manter monitoramento do dashboard.")
        cards = [
            {"label": "Receita", "value": str(analytics["summary_cards"][0]["value"]), "meta": "periodo"},
            {"label": "Margem", "value": str(analytics["summary_cards"][2]["value"]), "meta": "periodo"},
            {"label": "Backlog", "value": analytics["summary_cards"][5]["value"], "meta": "OS abertas"},
            {"label": "SLA", "value": str(analytics["summary_cards"][3]["value"]), "meta": "taxa do periodo"},
        ]
        return {
            "title": "Daily Executive Briefing" if period.start == period.end else "Weekly Executive Summary",
            "summary": f"{company.name}: {analytics['summary_cards'][5]['value']} OS abertas, {len(analytics['problematic_assets'])} ativos problemáticos e SLA de {analytics['summary_cards'][3]['value']}.",
            "priorities": priorities,
            "alerts": alerts,
            "recommendations": [
                {
                    "title": item.title,
                    "summary": item.summary,
                    "severity": item.severity,
                    "priority": item.priority,
                    "agent": item.agent_run.agent.name,
                }
                for item in recommendations[:5]
            ],
            "suggested_actions": actions,
            "cards": cards,
            "links": [
                {"label": "Ver AI Agents Center", "href": reverse("admin-shell:ai-agents-dashboard")},
                {"label": "Ver Health de manutencao", "href": reverse("admin-shell:ai-agents-maintenance-health")},
                {"label": "Abrir Copilot do gestor", "href": reverse("admin-shell:ai-manager-copilot")},
            ],
            "source_agents": sorted({item.agent_run.agent.slug for item in recommendations}),
            "source_recommendation_ids": [str(item.public_id) for item in recommendations],
            "source_proposal_ids": [str(item.public_id) for item in proposals],
        }

    @classmethod
    def _technician_payload(cls, *, user, company, site=None, period: BriefingPeriod):
        tenant_context = {"company": company, "site": site}
        dashboard = get_technician_dashboard_context(user, tenant_context)
        services = get_technician_service_listing_context(user, tenant_context, {"preset": "today"})
        recommendations = cls._recommendations(company=company, site=site, user=user, audience=AIBriefing.Audience.TECHNICIAN)
        service_cards = services["service_cards"][:4]
        priorities = [
            f"{service['code']} - {service['title']} ({service['priority']})"
            for service in service_cards
        ] or ["Nenhuma OS prioritaria atribuida para hoje."]
        alerts = [alert["title"] + ": " + alert["description"] for alert in dashboard["operational_alerts"][:3]]
        if not alerts:
            alerts.append("Sem alertas operacionais criticos para o turno atual.")
        recommendation_lines = [item.summary for item in recommendations[:4]] or ["Sem recomendacao adicional do Maintenance Agent no contexto atual."]
        pieces = []
        for service in service_cards:
            if service.get("piece_pending"):
                pieces.append(f"{service['code']}: validar peca pendente antes da execucao.")
        return {
            "title": "Daily Field Briefing",
            "summary": f"Agenda de {user.display_name or user.email}: {len(service_cards)} atendimento(s) priorizados para o dia.",
            "priorities": priorities,
            "alerts": alerts,
            "recommendations": [{"summary": item} for item in recommendation_lines],
            "suggested_actions": pieces or ["Conferir rota, checklist e materiais antes do primeiro deslocamento."],
            "cards": dashboard["dashboard_cards"],
            "links": [
                {"label": "Abrir agenda", "href": reverse("admin-shell:technician-app-schedule")},
                {"label": "Abrir servicos", "href": reverse("admin-shell:technician-app-services")},
            ],
            "source_agents": sorted({item.agent_run.agent.slug for item in recommendations}),
            "source_recommendation_ids": [str(item.public_id) for item in recommendations],
            "source_proposal_ids": [],
        }

    @classmethod
    def _client_payload(cls, *, user, company, site=None, period: BriefingPeriod):
        tenant_context = {"company": company, "site": site}
        dashboard = get_client_dashboard_context(user._briefing_request, tenant_context)
        recommendations = cls._recommendations(company=company, site=site, audience=AIBriefing.Audience.CLIENT)
        safe_recommendations = [
            item.summary
            for item in recommendations
            if not any(term in item.summary.lower() for term in ["margem", "lucro", "custo", "rentabilidade"])
        ][:4]
        pending_quotes = dashboard["dashboard_pending_quotes"][:3]
        return {
            "title": "Daily Client Briefing",
            "summary": f"{company.name}: {dashboard['dashboard_kpis'][1]['value']} OS abertas e {dashboard['dashboard_kpis'][3]['value']} preventivas previstas no contexto visivel.",
            "priorities": [
                f"{item['label']}: {item['value']}"
                for item in dashboard["dashboard_kpis"][:4]
            ],
            "alerts": [
                f"Orcamentos pendentes: {len(pending_quotes)}.",
                f"Relatorios recentes: {len(dashboard['dashboard_recent_reports'])}.",
                f"Chamados em acompanhamento: {len(dashboard['dashboard_recent_requests'])}.",
            ],
            "recommendations": [{"summary": line} for line in safe_recommendations] or [{"summary": "Sem alertas adicionais publicados para o portal hoje."}],
            "suggested_actions": [
                "Revisar orcamentos pendentes de aprovacao." if pending_quotes else "Acompanhar os relatorios mais recentes do portal.",
                "Abrir a unidade e verificar OS/preventivas em andamento.",
            ],
            "cards": dashboard["dashboard_kpis"][:6],
            "links": [
                {"label": "Abrir portal", "href": reverse("admin-shell:client-portal-dashboard")},
                {"label": "Ver orcamentos", "href": reverse("admin-shell:client-portal-quotes")},
                {"label": "Abrir Copilot do cliente", "href": reverse("admin-shell:client-portal-copilot")},
            ],
            "source_agents": sorted({item.agent_run.agent.slug for item in recommendations}),
            "source_recommendation_ids": [str(item.public_id) for item in recommendations[:4]],
            "source_proposal_ids": [],
        }

    @classmethod
    def _build_request_stub(cls, *, user, company, site=None):
        class _StubRequest:
            pass

        request = _StubRequest()
        request.user = user
        request.GET = {}
        request.POST = {}
        request.session = {}
        request.path = "/briefings/"
        request.method = "GET"
        request.resolver_match = None
        request._cached_user = user
        request._briefing_company = company
        request._briefing_site = site
        return request

    @classmethod
    def compose(
        cls,
        *,
        briefing_type: str,
        audience: str,
        company,
        user=None,
        site=None,
        reference_date=None,
        start=None,
        end=None,
        filters=None,
    ):
        period = cls.resolve_period(briefing_type, reference_date=reference_date, start=start, end=end)
        if audience == AIBriefing.Audience.MANAGER:
            payload = cls._executive_payload(company=company, site=site, period=period)
        elif audience == AIBriefing.Audience.TECHNICIAN:
            payload = cls._technician_payload(user=user, company=company, site=site, period=period)
        else:
            request = cls._build_request_stub(user=user, company=company, site=site)
            user._briefing_request = request
            payload = cls._client_payload(user=user, company=company, site=site, period=period)
            delattr(user, "_briefing_request")
        payload["period"] = {"label": period.label, "start": str(period.start), "end": str(period.end)}
        payload["filters"] = filters or {}
        return payload

    @classmethod
    @transaction.atomic
    def generate_briefing(
        cls,
        *,
        briefing_type: str,
        audience: str,
        company,
        user=None,
        site=None,
        reference_date=None,
        start=None,
        end=None,
        filters=None,
    ):
        payload = cls.compose(
            briefing_type=briefing_type,
            audience=audience,
            company=company,
            user=user,
            site=site,
            reference_date=reference_date,
            start=start,
            end=end,
            filters=filters,
        )
        briefing = AIBriefing.objects.create(
            briefing_type=briefing_type,
            audience=audience,
            company=company,
            site=site,
            user=user,
            title=payload["title"],
            summary=payload["summary"],
            period_label=payload["period"]["label"],
            period_start=period.start,
            period_end=period.end,
            content=payload,
            source_agents=payload.get("source_agents", []),
            source_recommendation_ids=payload.get("source_recommendation_ids", []),
            source_proposal_ids=payload.get("source_proposal_ids", []),
            filters=filters or {},
        )
        SystemEventService.log_system_event(
            event_type="briefing.generated",
            source_module="ai_agents_center",
            message="AI briefing generated.",
            company=company,
            site=site,
            user=user,
            entity_type="ai_briefing",
            entity_id=str(briefing.public_id),
            payload={"briefing_type": briefing_type, "audience": audience},
        )
        return briefing

    @classmethod
    def deliver_briefing(cls, *, briefing, channels=None):
        configuration = cls.get_configuration(company=briefing.company)
        delivery_channels = channels or (configuration.delivery_channels if configuration and configuration.delivery_channels else cls.DEFAULT_CHANNELS)
        in_app_channel = NotificationChannel.objects.filter(channel_type=NotificationChannel.ChannelType.IN_APP, is_active=True).first()
        email_channel = NotificationChannel.objects.filter(channel_type=NotificationChannel.ChannelType.EMAIL, is_active=True).first()
        for channel in delivery_channels:
            delivery = AIBriefingDelivery.objects.create(
                briefing=briefing,
                channel=channel,
                recipient_user=briefing.user,
                status=AIBriefingDelivery.Status.PENDING,
            )
            if channel == AIBriefingDelivery.Channel.IN_APP and briefing.user is not None:
                InAppNotificationService.create_notification(
                    user=briefing.user,
                    title=briefing.title,
                    body=briefing.summary,
                    link_url=cls._default_link_for_briefing(briefing),
                    notification_type=InAppNotification.NotificationType.INFO,
                )
            if channel == AIBriefingDelivery.Channel.EMAIL and email_channel is not None:
                NotificationMessageService.create_message(
                    event_key=f"briefing.{briefing.briefing_type}",
                    channel=email_channel,
                    recipient_user=briefing.user,
                    recipient_company=briefing.company,
                    recipient_address=getattr(briefing.user, "email", ""),
                    body_rendered=briefing.summary,
                    subject_rendered=briefing.title,
                    payload={"briefing_public_id": str(briefing.public_id)},
                    status=NotificationMessage.Status.SCHEDULED,
                )
            delivery.status = AIBriefingDelivery.Status.DELIVERED
            delivery.delivered_at = timezone.now()
            delivery.metadata = {"link_url": cls._default_link_for_briefing(briefing)}
            delivery.save(update_fields=["status", "delivered_at", "metadata", "updated_at"])
        briefing.status = AIBriefing.Status.DELIVERED
        briefing.delivered_at = timezone.now()
        briefing.save(update_fields=["status", "delivered_at", "updated_at"])
        SystemEventService.log_system_event(
            event_type="briefing.delivered",
            source_module="ai_agents_center",
            message="AI briefing delivered.",
            company=briefing.company,
            site=briefing.site,
            user=briefing.user,
            entity_type="ai_briefing",
            entity_id=str(briefing.public_id),
            payload={"channels": delivery_channels},
        )
        return briefing

    @classmethod
    def mark_viewed(cls, *, briefing, user=None):
        now = timezone.now()
        briefing.status = AIBriefing.Status.VIEWED
        briefing.viewed_at = now
        briefing.save(update_fields=["status", "viewed_at", "updated_at"])
        deliveries = briefing.deliveries.filter(Q(recipient_user=user) | Q(recipient_user__isnull=True))
        for delivery in deliveries:
            delivery.status = AIBriefingDelivery.Status.VIEWED
            delivery.viewed_at = now
            delivery.save(update_fields=["status", "viewed_at", "updated_at"])
        SystemEventService.log_system_event(
            event_type="briefing.viewed",
            source_module="ai_agents_center",
            message="AI briefing viewed.",
            company=briefing.company,
            site=briefing.site,
            user=user or briefing.user,
            entity_type="ai_briefing",
            entity_id=str(briefing.public_id),
            payload={"briefing_type": briefing.briefing_type},
        )
        return briefing

    @classmethod
    def list_accessible_briefings(cls, *, user, company=None, audience=None):
        queryset = AIBriefing.objects.select_related("company", "site", "user").all()
        if not getattr(user, "is_superuser", False):
            company_ids = list(Membership.objects.filter(user=user).values_list("company_id", flat=True))
            queryset = queryset.filter(Q(company_id__in=company_ids) | Q(user=user))
        if company is not None:
            queryset = queryset.filter(company=company)
        if audience:
            queryset = queryset.filter(audience=audience)
        return queryset.order_by("-generated_at")

    @classmethod
    def latest_for_context(cls, *, company, audience, user=None, site=None):
        queryset = AIBriefing.objects.filter(company=company, audience=audience)
        if user is not None:
            queryset = queryset.filter(Q(user=user) | Q(user__isnull=True))
        if site is not None:
            queryset = queryset.filter(Q(site=site) | Q(site__isnull=True))
        return queryset.order_by("-generated_at").first()

    @classmethod
    def generate_daily_executive_briefings(cls, *, reference_date=None):
        reference_date = reference_date or timezone.localdate()
        companies = Company.objects.filter(status=Company.Status.ACTIVE)
        generated = []
        manager_assignments = UserRoleAssignment.objects.filter(
            is_active=True,
            role__slug__in=["maintenance-manager", "super-admin", "finance-readonly"],
        ).select_related("user", "company", "role")
        for company in companies:
            company_users = []
            for assignment in manager_assignments:
                if assignment.company_id in (None, company.id):
                    company_users.append(assignment.user)
            if not company_users:
                company_users = [membership.user for membership in Membership.objects.filter(company=company, is_primary=True).select_related("user")[:1]]
            for user in company_users[:3] or [None]:
                briefing = cls.generate_briefing(
                    briefing_type=AIBriefing.BriefingType.DAILY_EXECUTIVE,
                    audience=AIBriefing.Audience.MANAGER,
                    company=company,
                    user=user,
                    reference_date=reference_date,
                )
                cls.deliver_briefing(briefing=briefing)
                generated.append(briefing)
        return generated

    @classmethod
    def generate_daily_field_briefings(cls, *, reference_date=None):
        reference_date = reference_date or timezone.localdate()
        assignments = UserRoleAssignment.objects.filter(is_active=True, role__slug="technician").select_related("user", "company")
        generated = []
        for assignment in assignments:
            company = assignment.company or Membership.objects.filter(user=assignment.user, is_primary=True).select_related("company").first().company
            if company is None:
                continue
            briefing = cls.generate_briefing(
                briefing_type=AIBriefing.BriefingType.DAILY_FIELD,
                audience=AIBriefing.Audience.TECHNICIAN,
                company=company,
                user=assignment.user,
                reference_date=reference_date,
            )
            cls.deliver_briefing(
                briefing=briefing,
                channels=[AIBriefingDelivery.Channel.FIELD_APP, AIBriefingDelivery.Channel.IN_APP],
            )
            generated.append(briefing)
        return generated

    @classmethod
    def generate_daily_client_briefings(cls, *, reference_date=None):
        reference_date = reference_date or timezone.localdate()
        assignments = UserRoleAssignment.objects.filter(
            is_active=True,
            role__slug__in=["client-manager", "client-readonly", "requester"],
        ).select_related("user", "company")
        generated = []
        for assignment in assignments:
            company = assignment.company or Membership.objects.filter(user=assignment.user, is_primary=True).select_related("company").first().company
            if company is None:
                continue
            site_membership = assignment.user.site_memberships.filter(company=company, is_primary=True).select_related("site").first()
            briefing = cls.generate_briefing(
                briefing_type=AIBriefing.BriefingType.DAILY_CLIENT,
                audience=AIBriefing.Audience.CLIENT,
                company=company,
                user=assignment.user,
                site=site_membership.site if site_membership else None,
                reference_date=reference_date,
            )
            cls.deliver_briefing(
                briefing=briefing,
                channels=[AIBriefingDelivery.Channel.PORTAL, AIBriefingDelivery.Channel.IN_APP],
            )
            generated.append(briefing)
        return generated

    @classmethod
    def generate_weekly_executive_briefings(cls, *, reference_date=None):
        reference_date = reference_date or timezone.localdate()
        companies = Company.objects.filter(status=Company.Status.ACTIVE)
        generated = []
        manager_memberships = Membership.objects.filter(is_primary=True).select_related("user", "company")
        for membership in manager_memberships:
            briefing = cls.generate_briefing(
                briefing_type=AIBriefing.BriefingType.WEEKLY_EXECUTIVE,
                audience=AIBriefing.Audience.MANAGER,
                company=membership.company,
                user=membership.user,
                reference_date=reference_date,
                start=reference_date - timedelta(days=6),
                end=reference_date,
            )
            cls.deliver_briefing(briefing=briefing)
            generated.append(briefing)
        return generated

    @classmethod
    def _default_link_for_briefing(cls, briefing):
        if briefing.audience == AIBriefing.Audience.TECHNICIAN:
            return reverse("admin-shell:technician-app-briefing-detail", kwargs={"briefing_id": briefing.public_id})
        if briefing.audience == AIBriefing.Audience.CLIENT:
            return reverse("admin-shell:client-portal-briefing-detail", kwargs={"briefing_id": briefing.public_id})
        return reverse("admin-shell:ai-briefing-detail", kwargs={"briefing_id": briefing.public_id})
