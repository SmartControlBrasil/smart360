from __future__ import annotations

from apps.ai_agents_center.models import AIBriefing, AgentActionProposal, AgentAnomalyAttentionFlag, AgentAssetAttentionFlag, AgentDefinition, AgentMarketplaceRequestFlag, AgentProfitabilityAttentionFlag, AgentRecommendation, AgentRun, AgentScheduleHealthFlag, ManagerCopilotSession


class AgentDashboardService:
    @staticmethod
    def build_dashboard(*, company=None):
        agent_queryset = AgentDefinition.objects.all()
        run_queryset = AgentRun.objects.select_related("agent", "company", "site").all()
        recommendation_queryset = AgentRecommendation.objects.select_related("agent_run", "agent_run__agent", "company", "site").all()
        proposal_queryset = AgentActionProposal.objects.select_related("agent_run", "agent_run__agent").all()
        attention_queryset = AgentAssetAttentionFlag.objects.select_related("asset", "site", "latest_recommendation").all()
        schedule_health_queryset = AgentScheduleHealthFlag.objects.select_related("technician", "site", "latest_recommendation").all()
        profitability_health_queryset = AgentProfitabilityAttentionFlag.objects.select_related("site", "client", "contract", "technician", "latest_recommendation").all()
        marketplace_health_queryset = AgentMarketplaceRequestFlag.objects.select_related("service_request", "site", "latest_recommendation").all()
        anomaly_health_queryset = AgentAnomalyAttentionFlag.objects.select_related("site", "asset", "client", "contract", "technician", "part", "latest_recommendation").all()
        copilot_session_queryset = ManagerCopilotSession.objects.select_related("company", "site", "user").all()
        briefing_queryset = AIBriefing.objects.select_related("company", "site", "user").all()
        if company is not None:
            run_queryset = run_queryset.filter(company=company)
            recommendation_queryset = recommendation_queryset.filter(company=company)
            proposal_queryset = proposal_queryset.filter(agent_run__company=company)
            attention_queryset = attention_queryset.filter(company=company)
            schedule_health_queryset = schedule_health_queryset.filter(company=company)
            profitability_health_queryset = profitability_health_queryset.filter(company=company)
            marketplace_health_queryset = marketplace_health_queryset.filter(company=company)
            anomaly_health_queryset = anomaly_health_queryset.filter(company=company)
            copilot_session_queryset = copilot_session_queryset.filter(company=company)
            briefing_queryset = briefing_queryset.filter(company=company)
        return {
            "summary_cards": [
                {"label": "Agentes ativos", "value": agent_queryset.filter(enabled=True, status="active").count()},
                {"label": "Runs recentes", "value": run_queryset.count()},
                {"label": "Recomendacoes abertas", "value": recommendation_queryset.filter(status="open").count()},
                {"label": "Acoes pendentes", "value": proposal_queryset.filter(status="pending_approval").count()},
                {"label": "Sessoes do copilot", "value": copilot_session_queryset.filter(status__in=["active", "reset"]).count()},
                {"label": "Ativos em observacao", "value": attention_queryset.filter(status__in=["active", "watching"]).count()},
                {"label": "Agenda em atencao", "value": schedule_health_queryset.filter(status__in=["active", "watching"]).count()},
                {"label": "Rentabilidade em atencao", "value": profitability_health_queryset.filter(status__in=["active", "watching"]).count()},
                {"label": "Marketplace em atencao", "value": marketplace_health_queryset.filter(status__in=["active", "watching"]).count()},
                {"label": "Anomalias em atencao", "value": anomaly_health_queryset.filter(status__in=["active", "watching"]).count()},
                {"label": "Briefings gerados", "value": briefing_queryset.count()},
            ],
            "agents": list(agent_queryset.order_by("name")),
            "recent_runs": list(run_queryset.order_by("-created_at")[:20]),
            "recent_recommendations": list(recommendation_queryset.order_by("-created_at")[:20]),
            "pending_proposals": list(proposal_queryset.order_by("-created_at")[:20]),
            "attention_assets": list(attention_queryset.order_by("-attention_score", "-updated_at")[:20]),
            "schedule_health": list(schedule_health_queryset.order_by("-attention_score", "-updated_at")[:20]),
            "profitability_health": list(profitability_health_queryset.order_by("-attention_score", "-updated_at")[:20]),
            "marketplace_health": list(marketplace_health_queryset.order_by("-attention_score", "-updated_at")[:20]),
            "anomaly_health": list(anomaly_health_queryset.order_by("-attention_score", "-updated_at")[:20]),
            "recent_copilot_sessions": list(copilot_session_queryset.order_by("-last_activity_at")[:10]),
            "recent_briefings": list(briefing_queryset.order_by("-generated_at")[:10]),
        }
