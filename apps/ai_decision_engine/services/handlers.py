from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from apps.ai_agents_center.models import AgentAssetAttentionFlag, AgentProfitabilityAttentionFlag
from apps.ai_decision_engine.models import AgentDecision
from apps.marketplace_technicians.models import TechnicianMatchingRecord, TechnicianProfile, TechnicianServiceRequest
from apps.marketplace_technicians.services.marketplace_service import TechnicianAssignmentService
from apps.smart_system.models import (
    Asset,
    AssetHistoryEvent,
    FailureEvent,
    MaintenanceContract,
    MaintenancePlan,
    RoutePlan,
    ScheduledVisit,
    ServiceOrder,
    TechnicianSchedule,
)
from apps.smart_system.services.maintenance_service import AssetHistoryService, ServiceOrderService


@dataclass(frozen=True)
class ActionHandlerResult:
    summary: str
    related_entity_type: str
    related_entity_id: str
    payload: dict
    rollback_supported: bool = False


class BaseDecisionHandler:
    action_types: tuple[str, ...] = ()

    def supports(self, normalized_action_type: str) -> bool:
        return normalized_action_type in self.action_types


class CreateWorkOrderHandler(BaseDecisionHandler):
    action_types = ("create_work_order_proposal",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        payload = decision.agent_action_proposal.proposed_payload or {}
        asset_public_id = payload.get("asset_public_id") or decision.target_entity_id
        asset = Asset.objects.select_related("operational_site", "operational_site__maintenance_client").get(public_id=asset_public_id)
        order = ServiceOrderService.create_service_order(
            user=actor,
            validated_data={
                "client": asset.operational_site.maintenance_client,
                "operational_site": asset.operational_site,
                "asset": asset,
                "maintenance_type": payload.get("maintenance_type", ServiceOrder.MaintenanceType.INSPECTION),
                "priority": ServiceOrder.Priority.HIGH if decision.risk_level in {"high", "critical"} else ServiceOrder.Priority.MEDIUM,
                "status": ServiceOrder.Status.OPEN,
                "source": ServiceOrder.Source.ALERT,
                "title": decision.agent_action_proposal.title or f"Actioned by AI decision for {asset.asset_tag}",
                "description": decision.agent_action_proposal.summary or payload.get("reason", ""),
                "requested_by": "AI Decision Engine",
            },
        )
        return ActionHandlerResult(
            summary=f"OS {order.order_number} criada para o ativo {asset.asset_tag}.",
            related_entity_type="service_order",
            related_entity_id=str(order.public_id),
            payload={"order_number": order.order_number, "asset_public_id": str(asset.public_id)},
            rollback_supported=False,
        )


class CreatePreventiveReviewTaskHandler(BaseDecisionHandler):
    action_types = ("create_preventive_review_task",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        payload = decision.agent_action_proposal.proposed_payload or {}
        plan = None
        asset = None
        if payload.get("maintenance_plan_public_id"):
            plan = MaintenancePlan.objects.select_related("asset", "operational_site", "operational_site__maintenance_client").get(
                public_id=payload["maintenance_plan_public_id"]
            )
            asset = plan.asset
        else:
            asset = Asset.objects.select_related("operational_site", "operational_site__maintenance_client").get(
                public_id=payload.get("asset_public_id") or decision.target_entity_id
            )
        order = ServiceOrderService.create_service_order(
            user=actor,
            validated_data={
                "client": asset.operational_site.maintenance_client,
                "operational_site": asset.operational_site,
                "asset": asset,
                "maintenance_plan": plan,
                "maintenance_type": ServiceOrder.MaintenanceType.PREVENTIVE,
                "priority": ServiceOrder.Priority.HIGH if decision.risk_level in {"high", "critical"} else ServiceOrder.Priority.MEDIUM,
                "status": ServiceOrder.Status.OPEN,
                "source": ServiceOrder.Source.PLAN if plan else ServiceOrder.Source.ALERT,
                "title": decision.agent_action_proposal.title or f"Preventive review for {asset.asset_tag}",
                "description": decision.agent_action_proposal.summary or payload.get("reason", ""),
                "requested_by": "AI Decision Engine",
            },
        )
        return ActionHandlerResult(
            summary=f"Revisao preventiva materializada na OS {order.order_number}.",
            related_entity_type="service_order",
            related_entity_id=str(order.public_id),
            payload={"order_number": order.order_number, "maintenance_plan_public_id": str(plan.public_id) if plan else ""},
            rollback_supported=False,
        )


class MarkAssetAttentionHandler(BaseDecisionHandler):
    action_types = ("mark_asset_attention",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        payload = decision.agent_action_proposal.proposed_payload or {}
        asset = Asset.objects.select_related("operational_site", "operational_site__maintenance_client").get(
            public_id=payload.get("asset_public_id") or decision.target_entity_id
        )
        flag, _ = AgentAssetAttentionFlag.objects.update_or_create(
            agent=decision.agent_action_proposal.agent_run.agent,
            company=decision.company or asset.operational_site.maintenance_client.company,
            asset=asset,
            defaults={
                "site": decision.site or asset.operational_site,
                "latest_run": decision.agent_action_proposal.agent_run,
                "status": AgentAssetAttentionFlag.Status.ACTIVE,
                "attention_score": max(payload.get("attention_score", 75), 50),
                "summary": decision.agent_action_proposal.summary or decision.agent_action_proposal.title or asset.name,
                "risk_level": decision.risk_level,
                "payload": payload,
            },
        )
        return ActionHandlerResult(
            summary=f"Ativo {asset.asset_tag} entrou em watchlist controlada.",
            related_entity_type="asset_attention_flag",
            related_entity_id=str(flag.public_id),
            payload={"asset_public_id": str(asset.public_id), "flag_public_id": str(flag.public_id)},
            rollback_supported=True,
        )


class CreateScheduleAdjustmentHandler(BaseDecisionHandler):
    action_types = ("create_schedule_adjustment_proposal",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        payload = decision.agent_action_proposal.proposed_payload or {}
        visit_public_id = payload.get("visit_public_id")
        date_value = payload.get("date") or timezone.localdate().isoformat()
        if isinstance(date_value, str):
            date_value = date.fromisoformat(date_value)
        technician_id = payload.get("to_technician_id") or payload.get("technician_id")
        if visit_public_id:
            visit = ScheduledVisit.objects.select_related("company", "operational_site", "work_order").get(public_id=visit_public_id)
        else:
            visit = ScheduledVisit.objects.select_related("company", "operational_site", "work_order").get(public_id=decision.target_entity_id)
        schedule, _ = TechnicianSchedule.objects.get_or_create(
            company=decision.company or visit.company,
            technician_id=technician_id or visit.technician_id,
            date=date_value,
            defaults={"operational_site": decision.site or visit.operational_site},
        )
        visit.technician_id = technician_id or visit.technician_id
        visit.technician_schedule = schedule
        visit.status = ScheduledVisit.Status.SCHEDULED
        visit.notes = f"{visit.notes}\nAI Decision Engine: {decision.agent_action_proposal.summary}".strip()
        visit.save(update_fields=["technician", "technician_schedule", "status", "notes", "updated_at"])
        return ActionHandlerResult(
            summary=f"Visita {visit.title} vinculada a agenda controlada do tecnico {visit.technician_id}.",
            related_entity_type="scheduled_visit",
            related_entity_id=str(visit.public_id),
            payload={"visit_public_id": str(visit.public_id), "schedule_public_id": str(schedule.public_id)},
            rollback_supported=True,
        )


class ReorderRouteProposalHandler(BaseDecisionHandler):
    action_types = ("reorder_route_proposal",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        payload = decision.agent_action_proposal.proposed_payload or {}
        technician_id = payload.get("technician_id")
        date_value = payload.get("date") or timezone.localdate().isoformat()
        route_plan, _ = RoutePlan.objects.get_or_create(
            company=decision.company,
            technician_id=technician_id,
            date=date_value,
            defaults={"operational_site": decision.site, "optimization_status": RoutePlan.OptimizationStatus.NEEDS_REVIEW},
        )
        route_plan.optimization_status = RoutePlan.OptimizationStatus.NEEDS_REVIEW
        route_plan.route_summary = {
            **(route_plan.route_summary or {}),
            "ordered_public_ids": payload.get("ordered_public_ids", []),
            "decision_public_id": str(decision.public_id),
        }
        route_plan.notes = f"{route_plan.notes}\nAI Decision Engine: rota proposta para revisao.".strip()
        route_plan.save(update_fields=["optimization_status", "route_summary", "notes", "updated_at"])
        return ActionHandlerResult(
            summary=f"Rota do tecnico {technician_id} marcada para revisao com ordem proposta.",
            related_entity_type="route_plan",
            related_entity_id=str(route_plan.public_id),
            payload={"route_plan_public_id": str(route_plan.public_id)},
            rollback_supported=True,
        )


class AssignMarketplaceCandidateHandler(BaseDecisionHandler):
    action_types = ("assign_marketplace_candidate_proposal",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        payload = decision.agent_action_proposal.proposed_payload or {}
        service_request_public_id = payload.get("service_request_public_id") or decision.target_entity_id
        service_request = TechnicianServiceRequest.objects.select_related("requester_company", "related_site").get(public_id=service_request_public_id)
        profile_public_id = payload.get("technician_profile_public_id")
        if not profile_public_id and payload.get("marketplace_candidates"):
            profile_public_id = payload["marketplace_candidates"][0].get("technician_profile_public_id")
        if not profile_public_id and payload.get("candidate"):
            profile_public_id = payload["candidate"].get("technician_profile_public_id")
        if not profile_public_id:
            match = TechnicianMatchingRecord.objects.filter(technician_service_request=service_request).select_related("technician_profile").order_by("-match_score").first()
            technician_profile = match.technician_profile if match else None
        else:
            technician_profile = TechnicianProfile.objects.get(public_id=profile_public_id)
        if technician_profile is None:
            raise ValueError("Nenhum tecnico elegivel encontrado para a alocacao.")
        assignment = TechnicianAssignmentService.assign(
            service_request=service_request,
            technician_profile=technician_profile,
            notes=f"AI Decision Engine approved assignment {decision.public_id}",
        )
        return ActionHandlerResult(
            summary=f"Marketplace assignment criado para {technician_profile.display_name}.",
            related_entity_type="marketplace_assignment",
            related_entity_id=str(assignment.public_id),
            payload={"assignment_public_id": str(assignment.public_id), "service_request_public_id": str(service_request.public_id)},
            rollback_supported=True,
        )


class FlagContractProfitabilityAttentionHandler(BaseDecisionHandler):
    action_types = ("flag_contract_profitability_attention",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        payload = decision.agent_action_proposal.proposed_payload or {}
        contract_public_id = payload.get("contract_public_id") or decision.target_entity_id
        contract = None
        if contract_public_id:
            contract = MaintenanceContract.objects.select_related("client", "operational_site").filter(public_id=contract_public_id).first()
        focus_type = "contract" if contract else "client"
        display_label = contract.contract_number if contract else payload.get("client_name", decision.agent_action_proposal.title)
        flag, _ = AgentProfitabilityAttentionFlag.objects.update_or_create(
            agent=decision.agent_action_proposal.agent_run.agent,
            company=decision.company,
            focus_type=focus_type,
            target_entity_type=decision.target_entity or ("maintenance_contract" if contract else "maintenance_client"),
            target_entity_id=contract_public_id or decision.target_entity_id,
            defaults={
                "site": decision.site or getattr(contract, "operational_site", None),
                "client": getattr(contract, "client", None),
                "contract": contract,
                "display_label": display_label,
                "latest_run": decision.agent_action_proposal.agent_run,
                "status": AgentProfitabilityAttentionFlag.Status.ACTIVE,
                "attention_score": max(payload.get("attention_score", 70), 55),
                "summary": decision.agent_action_proposal.summary or decision.agent_action_proposal.title,
                "risk_level": decision.risk_level,
                "payload": payload,
            },
        )
        return ActionHandlerResult(
            summary=f"Flag de rentabilidade registrada para {display_label}.",
            related_entity_type="profitability_attention_flag",
            related_entity_id=str(flag.public_id),
            payload={"flag_public_id": str(flag.public_id)},
            rollback_supported=True,
        )


class CreateInvestigationTaskHandler(BaseDecisionHandler):
    action_types = ("create_investigation_task",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        payload = decision.agent_action_proposal.proposed_payload or {}
        if decision.target_entity == "asset":
            asset = Asset.objects.select_related("operational_site", "operational_site__maintenance_client").get(
                public_id=payload.get("asset_public_id") or decision.target_entity_id
            )
            failure_event = FailureEvent.objects.create(
                asset=asset,
                detected_at=timezone.now(),
                symptom=decision.agent_action_proposal.title or "Investigacao aberta pelo Decision Engine",
                probable_cause=payload.get("reason", ""),
                severity=FailureEvent.Severity.HIGH if decision.risk_level in {"high", "critical"} else FailureEvent.Severity.MEDIUM,
                status=FailureEvent.Status.ANALYZING,
                notes=decision.agent_action_proposal.summary,
            )
            AssetHistoryService.create_event(
                asset=asset,
                event_type=AssetHistoryEvent.EventType.GENERAL,
                title="Investigacao operacional aberta",
                description=decision.agent_action_proposal.summary,
                related_failure_event=failure_event,
                created_by=actor,
            )
            return ActionHandlerResult(
                summary=f"Investigacao aberta para o ativo {asset.asset_tag}.",
                related_entity_type="failure_event",
                related_entity_id=str(failure_event.public_id),
                payload={"failure_event_public_id": str(failure_event.public_id)},
                rollback_supported=False,
            )
        site = decision.site
        if site is None and payload.get("site_id"):
            from apps.smart_system.models import OperationalSite

            site = OperationalSite.objects.get(id=payload["site_id"])
        if site is None:
            raise ValueError("Investigacao sem site resolvido.")
        anchor_asset = site.assets.order_by("id").first()
        if anchor_asset is None:
            raise ValueError("Nao existe ativo ancora para registrar a investigacao desta unidade.")
        history = AssetHistoryEvent.objects.create(
            asset=anchor_asset,
            event_type=AssetHistoryEvent.EventType.GENERAL,
            title=decision.agent_action_proposal.title or "Investigacao operacional",
            description=decision.agent_action_proposal.summary,
            created_by=actor,
        )
        return ActionHandlerResult(
            summary=f"Investigacao registrada para a unidade {site.name}.",
            related_entity_type="asset_history_event",
            related_entity_id=str(history.public_id),
            payload={"history_event_public_id": str(history.public_id), "site_id": site.id},
            rollback_supported=False,
        )


class EscalateOperationalAlertHandler(BaseDecisionHandler):
    action_types = ("escalate_operational_alert",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        payload = decision.agent_action_proposal.proposed_payload or {}
        asset = None
        if decision.target_entity == "asset":
            asset = Asset.objects.get(public_id=decision.target_entity_id)
        elif decision.site and decision.site.assets.exists():
            asset = decision.site.assets.order_by("id").first()
        if asset is None:
            raise ValueError("Nao foi possivel ancorar o alerta operacional em um ativo/site auditavel.")
        history = AssetHistoryService.create_event(
            asset=asset,
            event_type=AssetHistoryEvent.EventType.GENERAL,
            title=decision.agent_action_proposal.title or "Alerta operacional escalado",
            description=decision.agent_action_proposal.summary or str(payload),
            created_by=actor,
        )
        return ActionHandlerResult(
            summary=f"Alerta operacional escalado e registrado para {asset.asset_tag}.",
            related_entity_type="asset_history_event",
            related_entity_id=str(history.public_id),
            payload={"history_event_public_id": str(history.public_id), "asset_public_id": str(asset.public_id)},
            rollback_supported=False,
        )


class ReviewCommercialOpportunityHandler(BaseDecisionHandler):
    action_types = ("review_commercial_opportunity",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        from apps.ai_agents_center.models import CommercialOpportunity
        from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService

        payload = decision.agent_action_proposal.proposed_payload or {}
        opp_id = payload.get("commercial_opportunity_public_id") or decision.target_entity_id
        if not opp_id:
            raise ValueError("ID da oportunidade comercial ausente no payload.")

        try:
            opportunity = CommercialOpportunity.objects.get(public_id=opp_id)
        except (ValueError, CommercialOpportunity.DoesNotExist):
            opportunity = CommercialOpportunity.objects.get(id=opp_id)

        OpportunityBuilderService.approve(opportunity=opportunity, user=actor)
        return ActionHandlerResult(
            summary=f"Oportunidade comercial {opportunity.company_name} aprovada.",
            related_entity_type="commercial_opportunity",
            related_entity_id=str(opportunity.public_id),
            payload={"opportunity_public_id": str(opportunity.public_id), "status": opportunity.status},
            rollback_supported=False,
        )

    def reject(self, *, decision: AgentDecision, actor=None, reason="") -> ActionHandlerResult:
        from apps.ai_agents_center.models import CommercialOpportunity
        from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService

        payload = decision.agent_action_proposal.proposed_payload or {}
        opp_id = payload.get("commercial_opportunity_public_id") or decision.target_entity_id
        if not opp_id:
            raise ValueError("ID da oportunidade comercial ausente no payload.")

        try:
            opportunity = CommercialOpportunity.objects.get(public_id=opp_id)
        except (ValueError, CommercialOpportunity.DoesNotExist):
            opportunity = CommercialOpportunity.objects.get(id=opp_id)

        OpportunityBuilderService.reject(opportunity=opportunity, user=actor, reason=reason)
        return ActionHandlerResult(
            summary=f"Oportunidade comercial {opportunity.company_name} rejeitada.",
            related_entity_type="commercial_opportunity",
            related_entity_id=str(opportunity.public_id),
            payload={"opportunity_public_id": str(opportunity.public_id), "status": opportunity.status, "rejection_reason": reason},
            rollback_supported=False,
        )


class EnrichCommercialOpportunityHandler(BaseDecisionHandler):
    action_types = ("enrich_commercial_opportunity",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        from apps.ai_agents_center.models import CommercialOpportunity

        payload = decision.agent_action_proposal.proposed_payload or {}
        opp_id = payload.get("commercial_opportunity_public_id") or decision.target_entity_id
        if not opp_id:
            raise ValueError("ID da oportunidade comercial ausente no payload.")

        try:
            opportunity = CommercialOpportunity.objects.get(public_id=opp_id)
        except (ValueError, CommercialOpportunity.DoesNotExist):
            opportunity = CommercialOpportunity.objects.get(id=opp_id)

        opportunity.status = CommercialOpportunity.Status.ENRICHING
        opportunity.metadata = {
            **(opportunity.metadata or {}),
            "enrichment_trail": {
                "timestamp": timezone.now().isoformat(),
                "actor": str(actor) if actor else "Decision Engine",
                "message": "Enriquecimento executado de forma deterministica.",
            }
        }
        opportunity.save(update_fields=["status", "metadata", "updated_at"])

        return ActionHandlerResult(
            summary=f"Oportunidade comercial {opportunity.company_name} marcada como enriquecendo.",
            related_entity_type="commercial_opportunity",
            related_entity_id=str(opportunity.public_id),
            payload={"opportunity_public_id": str(opportunity.public_id), "status": opportunity.status},
            rollback_supported=False,
        )


class ConvertCommercialOpportunityToLeadHandler(BaseDecisionHandler):
    action_types = ("convert_commercial_opportunity_to_lead",)

    def execute(self, *, decision: AgentDecision, actor=None) -> ActionHandlerResult:
        from apps.ai_agents_center.models import CommercialOpportunity
        from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService

        payload = decision.agent_action_proposal.proposed_payload or {}
        opp_id = payload.get("commercial_opportunity_public_id") or decision.target_entity_id
        if not opp_id:
            raise ValueError("ID da oportunidade comercial ausente no payload.")

        try:
            opportunity = CommercialOpportunity.objects.get(public_id=opp_id)
        except (ValueError, CommercialOpportunity.DoesNotExist):
            opportunity = CommercialOpportunity.objects.get(id=opp_id)

        lead = OpportunityBuilderService.convert_to_lead(opportunity=opportunity, user=actor)
        return ActionHandlerResult(
            summary=f"Oportunidade {opportunity.company_name} convertida para o Lead {lead.company_name}.",
            related_entity_type="lead",
            related_entity_id=str(lead.public_id),
            payload={"opportunity_public_id": str(opportunity.public_id), "lead_public_id": str(lead.public_id)},
            rollback_supported=False,
        )


HANDLERS = [
    CreateWorkOrderHandler(),
    CreatePreventiveReviewTaskHandler(),
    MarkAssetAttentionHandler(),
    CreateScheduleAdjustmentHandler(),
    ReorderRouteProposalHandler(),
    AssignMarketplaceCandidateHandler(),
    FlagContractProfitabilityAttentionHandler(),
    CreateInvestigationTaskHandler(),
    EscalateOperationalAlertHandler(),
    ReviewCommercialOpportunityHandler(),
    EnrichCommercialOpportunityHandler(),
    ConvertCommercialOpportunityToLeadHandler(),
]


class DecisionHandlerRegistry:
    @classmethod
    def get_handler(cls, normalized_action_type: str):
        for handler in HANDLERS:
            if handler.supports(normalized_action_type):
                return handler
        return None
