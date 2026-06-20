from __future__ import annotations

from apps.ai_agents_center.models import AgentDefinition, AgentExecutionPolicy


def get_agent_class_map():
    from apps.ai_agents_center.agents.anomaly import AnomalyDetectionAgent
    from apps.ai_agents_center.agents.atlas import AtlasCommercialIntelligenceAgent
    from apps.ai_agents_center.agents.maintenance import MaintenanceIntelligenceAgent
    from apps.ai_agents_center.agents.marketplace import MarketplaceAllocationAgent
    from apps.ai_agents_center.agents.profitability import ProfitabilityAgent
    from apps.ai_agents_center.agents.scheduling import SchedulingOptimizationAgent

    return {
        MaintenanceIntelligenceAgent.slug: MaintenanceIntelligenceAgent,
        SchedulingOptimizationAgent.slug: SchedulingOptimizationAgent,
        ProfitabilityAgent.slug: ProfitabilityAgent,
        MarketplaceAllocationAgent.slug: MarketplaceAllocationAgent,
        AnomalyDetectionAgent.slug: AnomalyDetectionAgent,
        AtlasCommercialIntelligenceAgent.slug: AtlasCommercialIntelligenceAgent,
    }


class AgentRegistryService:
    DEFAULT_DEFINITIONS = [
        {
            "slug": "maintenance-agent",
            "name": "Maintenance Intelligence Agent",
            "description": "Analisa falhas, reincidencia, preventivas, confiabilidade e propoe acoes auditaveis para ativos.",
            "domain": AgentDefinition.Domain.MAINTENANCE,
            "autonomy_level": AgentDefinition.AutonomyLevel.PROPOSE,
            "config": {
                "tools": [
                    "query_asset_profile",
                    "query_asset_failures",
                    "query_asset_work_orders",
                    "query_asset_preventives",
                    "query_asset_checklists",
                    "query_asset_reliability_metrics",
                    "query_asset_reports",
                    "create_maintenance_recommendation",
                    "create_maintenance_action_proposal",
                    "mark_asset_attention_flag",
                ],
                "heuristics": {
                    "recurring_failure_window_days": 45,
                    "recurring_failure_count": 3,
                    "critical_overdue_days": 7,
                    "checklist_consecutive_nok": 2,
                    "intervention_spike_min_current": 3,
                    "intervention_spike_multiplier": 1.5,
                    "mtbf_drop_ratio": 0.2,
                    "preventive_adherence_warning": 0.8,
                    "preventive_adherence_critical": 0.6,
                },
            },
        },
        {
            "slug": "scheduling-agent",
            "name": "Scheduling Optimization Agent",
            "description": "Analisa agenda, conflitos, deslocamento, capacidade e redistribuicao operacional de atendimentos.",
            "domain": AgentDefinition.Domain.SCHEDULING,
            "autonomy_level": AgentDefinition.AutonomyLevel.PROPOSE,
            "config": {
                "tools": [
                    "query_technician_schedule",
                    "query_day_visits",
                    "query_unassigned_visits",
                    "query_route_plan",
                    "query_technician_capacity",
                    "query_technician_availability",
                    "query_sla_risk_visits",
                    "query_marketplace_alternatives",
                    "create_schedule_recommendation",
                    "create_schedule_action_proposal",
                    "simulate_route_reorder",
                    "simulate_visit_reassignment",
                ],
                "heuristics": {
                    "overload_jobs": 6,
                    "overload_minutes": 600,
                    "max_travel_minutes": 180,
                    "max_idle_minutes": 180,
                    "sla_risk_hours": 24,
                    "unassigned_critical_hours": 24,
                    "reorder_gain_minutes": 20,
                    "reassignment_capacity_buffer": 90,
                },
            },
        },
        {
            "slug": "profitability-agent",
            "name": "Profitability Agent",
            "description": "Analisa margem por cliente, contrato, atendimento, rota e tecnico, propondo acoes gerenciais auditaveis.",
            "domain": AgentDefinition.Domain.PROFITABILITY,
            "autonomy_level": AgentDefinition.AutonomyLevel.PROPOSE,
            "config": {
                "tools": [
                    "query_client_profitability",
                    "query_contract_profitability",
                    "query_work_order_costs",
                    "query_parts_consumption_cost",
                    "query_technician_profitability",
                    "query_route_cost_impact",
                    "query_budget_vs_execution_cost",
                    "query_recurring_contract_effort",
                    "create_profitability_recommendation",
                    "create_profitability_action_proposal",
                    "flag_profitability_attention",
                ],
                "heuristics": {
                    "minimum_margin_percent": "12.00",
                    "critical_negative_margin_percent": "-10.00",
                    "negative_cycles_for_client_alert": 2,
                    "cost_to_revenue_alert_ratio": "1.20",
                    "travel_share_warning": "0.25",
                    "parts_share_warning": "0.35",
                    "corrective_mix_warning": "0.60",
                    "low_efficiency_vs_team_ratio": "0.60",
                },
            },
        },
        {
            "slug": "marketplace-agent",
            "name": "Marketplace Allocation Agent",
            "description": "Analisa matching, disponibilidade real, agenda, deslocamento e SLA para alocar tecnicos do marketplace.",
            "domain": AgentDefinition.Domain.MARKETPLACE,
            "autonomy_level": AgentDefinition.AutonomyLevel.PROPOSE,
            "config": {
                "tools": [
                    "query_service_request",
                    "query_marketplace_candidates",
                    "query_matching_scores",
                    "query_technician_schedule",
                    "query_technician_capacity",
                    "query_technician_availability",
                    "query_assignment_history",
                    "query_sla_context",
                    "create_marketplace_recommendation",
                    "create_marketplace_action_proposal",
                    "simulate_assignment_candidate",
                    "simulate_alternative_allocation",
                ],
                "heuristics": {
                    "max_urgent_distance_km": 30,
                    "max_high_distance_km": 60,
                    "max_daily_jobs": 6,
                    "max_daily_minutes": 600,
                    "request_stale_hours": 6,
                    "minimum_viability_score": "55.00",
                    "low_acceptance_penalty_threshold": "0.50",
                },
            },
        },
        {
            "slug": "atlas-commercial-intelligence-agent",
            "name": "Atlas Commercial Intelligence Agent",
            "description": "Identifica oportunidades comerciais publicas, qualifica problemas e propoe leads para o Growth Engine.",
            "domain": AgentDefinition.Domain.MARKETPLACE,
            "autonomy_level": AgentDefinition.AutonomyLevel.PROPOSE,
            "config": {
                "prompt_reference": "knowledge/comercial/agente_atlas.md",
                "tools": [
                    "query_public_company_profile",
                    "query_public_digital_presence",
                    "query_public_institutional_contacts",
                    "analyze_market_problem_fit",
                    "score_commercial_opportunity",
                    "review_commercial_opportunity",
                    "enrich_commercial_opportunity",
                    "convert_commercial_opportunity_to_lead",
                ],
                "portfolio": {
                    "robotics": ["NeoBot", "HostBot", "ConnectBot", "Buddy", "OrbitBot", "PatrolBot", "LIRO", "LittleBot", "HygiBot", "Duno", "MowerBot"],
                    "engineering": ["Automacao Industrial", "CLPs", "IHMs", "Supervisorios", "SCADA", "Servoacionamentos", "Inversores de frequencia", "IoT Industrial", "Retrofit de maquinas", "Engenharia embarcada", "Confiabilidade", "TPM", "Manutencao industrial"],
                    "technology": ["Smart360", "Sistemas Web", "Sistemas corporativos", "Integracoes", "Inteligencia Artificial", "Assistentes virtuais", "Dashboards", "Portais corporativos"],
                },
                "heuristics": {
                    "minimum_required_fields": ["company_name", "problems"],
                    "public_sources_only": True,
                    "institutional_contacts_only": True,
                    "never_invent_missing_data": True,
                    "strategic_score": 85,
                    "high_score": 70,
                    "medium_score": 45,
                },
            },
        },
        {
            "slug": "anomaly-agent",
            "name": "Anomaly Detection Agent",
            "description": "Detecta desvios operacionais, financeiros e comerciais em falhas, backlog, SLA, pecas, marketplace e rentabilidade.",
            "domain": AgentDefinition.Domain.ANOMALY,
            "autonomy_level": AgentDefinition.AutonomyLevel.PROPOSE,
            "config": {
                "tools": [
                    "query_failure_timeseries",
                    "query_work_order_timeseries",
                    "query_backlog_metrics",
                    "query_sla_metrics",
                    "query_parts_consumption_metrics",
                    "query_technician_performance_metrics",
                    "query_marketplace_operational_metrics",
                    "query_contract_profitability_metrics",
                    "query_baseline_comparison",
                    "create_anomaly_recommendation",
                    "create_anomaly_action_proposal",
                    "flag_anomaly_attention",
                ],
                "heuristics": {
                    "recent_window_days": 7,
                    "baseline_window_days": 28,
                    "failure_spike_multiplier": "1.80",
                    "minimum_failure_spike": 3,
                    "backlog_growth_multiplier": "1.70",
                    "minimum_backlog_open": 6,
                    "sla_drop_points": "15.00",
                    "critical_sla_rate": "75.00",
                    "parts_spike_multiplier": "2.50",
                    "minimum_parts_cost": "300.00",
                    "technician_drop_ratio": "0.50",
                    "minimum_assignment_cancellations": 3,
                    "marketplace_acceptance_drop_points": "20.00",
                    "marketplace_unassigned_threshold": 3,
                    "contract_margin_shift_points": "15.00",
                },
            },
        },
    ]

    @classmethod
    def bootstrap_registry(cls):
        definitions = []
        for item in cls.DEFAULT_DEFINITIONS:
            definition, _ = AgentDefinition.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "description": item["description"],
                    "domain": item["domain"],
                    "status": AgentDefinition.Status.ACTIVE,
                    "enabled": True,
                    "autonomy_level": item["autonomy_level"],
                    "config": item["config"],
                },
            )
            AgentExecutionPolicy.objects.update_or_create(
                agent=definition,
                defaults={
                    "require_human_approval": definition.autonomy_level >= AgentDefinition.AutonomyLevel.PROPOSE,
                    "allowed_tools": item["config"].get("tools", []),
                    "allowed_action_types": [
                        "schedule_preventive_proposal",
                        "open_inspection_work_order",
                        "review_preventive_plan",
                        "mark_asset_under_watch",
                        "create_technical_analysis",
                        "review_checklist_strategy",
                        "reevaluate_preventive_frequency",
                        "suggest_route_adjustment",
                        "reassign_visits_between_technicians",
                        "reorder_route_plan",
                        "schedule_unassigned_visit",
                        "block_schedule_for_review",
                        "move_visit_to_earlier_slot",
                        "suggest_alternative_technician_via_matching",
                        "flag_contract_risk",
                        "review_client_in_management_committee",
                        "suggest_contract_repricing",
                        "suggest_scope_recalibration",
                        "suggest_route_consolidation",
                        "prioritize_preventive_to_reduce_corrective_cost",
                        "create_recurring_profitability_alert",
                        "assign_best_marketplace_technician",
                        "assign_recommended_marketplace_technician",
                        "reassess_candidate_due_unavailability",
                        "activate_marketplace_fallback",
                        "redistribute_technician_agenda_for_request",
                        "adjust_marketplace_request_window",
                        "escalate_marketplace_request_attention",
                        "open_operational_investigation",
                        "trigger_maintenance_specialist_review",
                        "review_parts_consumption",
                        "review_marketplace_regional_coverage",
                        "review_contract_profitability_shift",
                        "open_operational_attention_committee",
                        "review_commercial_opportunity",
                        "enrich_commercial_opportunity",
                        "convert_commercial_opportunity_to_lead",
                    ],
                },
            )
            definitions.append(definition)
        return definitions

    @classmethod
    def get_available_agents(cls):
        return AgentDefinition.objects.filter(enabled=True, status=AgentDefinition.Status.ACTIVE).order_by("name")

    @classmethod
    def get_agent_definition(cls, slug):
        return AgentDefinition.objects.filter(slug=slug, enabled=True).select_related("execution_policy").first()

    @classmethod
    def resolve_agent_class(cls, slug):
        return get_agent_class_map()[slug]

    @classmethod
    def instantiate(cls, slug):
        definition = cls.get_agent_definition(slug)
        if definition is None:
            raise KeyError(f"Agent {slug} not found.")
        return cls.resolve_agent_class(slug)(definition=definition)
