from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.marketplace_technicians.models import TechnicianMatchingRecord, TechnicianProfile, TechnicianServiceRequest
from apps.smart_system.models import Asset, MaintenanceContract, MaintenancePlan, RoutePlan, ScheduledVisit, TechnicianSchedule
from apps.smart_system.services.scheduling_service import TechnicianRoutingService

User = get_user_model()
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class SimulationComputation:
    baseline_snapshot: dict
    summary: str
    impact_score: Decimal
    confidence_level: str
    risk_delta: Decimal
    cost_delta: Decimal
    sla_delta: Decimal
    profit_delta: Decimal
    travel_delta: Decimal
    workload_delta: Decimal
    recommendation: str
    result_payload: dict


class BaseSimulationHandler:
    simulation_type: str = ""

    def supports(self, simulation_type: str) -> bool:
        return simulation_type == self.simulation_type


class RouteReorderSimulationHandler(BaseSimulationHandler):
    simulation_type = "route_reorder_simulation"

    def run(self, *, company, site, input_payload):
        technician_id = input_payload.get("technician_id")
        target_date = timezone.datetime.strptime(input_payload["date"], "%Y-%m-%d").date() if input_payload.get("date") else timezone.localdate()
        TechnicianRoutingService.refresh_plannable_visits(schedule_date=target_date, company=company, site=site)
        visits = list(
            ScheduledVisit.objects.filter(company=company, scheduled_date=target_date, technician_id=technician_id)
            .select_related("operational_site")
            .order_by("route_order", "scheduled_start", "created_at")
        )
        before_travel = sum(visit.estimated_travel_minutes for visit in visits)
        optimized = TechnicianRoutingService._order_visits(visits) if visits else []
        after_travel = 0
        for index, visit in enumerate(optimized):
            if index == 0:
                continue
            after_travel += TechnicianRoutingService._estimate_travel_minutes(optimized[index - 1], visit)
        sla_before = Decimal(sum(1 for visit in visits if visit.priority in {"urgent", "high"} and (visit.route_order or 99) > 3))
        sla_after = Decimal(sum(1 for idx, visit in enumerate(optimized, start=1) if visit.priority in {"urgent", "high"} and idx > 3))
        delta = Decimal(before_travel - after_travel)
        confidence = "high" if len(visits) >= 3 else "medium"
        return SimulationComputation(
            baseline_snapshot={
                "visits": [{"public_id": str(v.public_id), "title": v.title, "route_order": v.route_order} for v in visits],
                "travel_minutes": before_travel,
                "critical_visits_late": float(sla_before),
            },
            summary=f"Rota simulada reduz {delta} min de deslocamento estimado." if delta >= 0 else f"Rota simulada adiciona {abs(delta)} min de deslocamento.",
            impact_score=delta,
            confidence_level=confidence,
            risk_delta=Decimal("-0.50") if sla_after <= sla_before else Decimal("0.75"),
            cost_delta=Decimal(after_travel - before_travel) * Decimal("1.20"),
            sla_delta=sla_before - sla_after,
            profit_delta=ZERO,
            travel_delta=Decimal(after_travel - before_travel),
            workload_delta=ZERO,
            recommendation="Aplicar reordenacao." if after_travel < before_travel else "Manter ordem atual.",
            result_payload={
                "current": {"travel_minutes": before_travel, "critical_visits_late": float(sla_before)},
                "proposed": {"travel_minutes": after_travel, "critical_visits_late": float(sla_after)},
                "gains": ["travel_reduction"] if after_travel < before_travel else [],
                "tradeoffs": ["possible_priority_delay"] if sla_after > sla_before else [],
            },
        )


class TechnicianReassignmentSimulationHandler(BaseSimulationHandler):
    simulation_type = "technician_reassignment_simulation"

    def run(self, *, company, site, input_payload):
        visit_queryset = ScheduledVisit.objects.select_related("operational_site").filter(public_id=input_payload["visit_public_id"], company=company)
        if site is not None:
            visit_queryset = visit_queryset.filter(operational_site=site)
        visit = visit_queryset.get()
        from_tech = input_payload.get("from_technician_id") or visit.technician_id
        to_tech = input_payload["to_technician_id"]
        target_date = visit.scheduled_date
        from_schedule = TechnicianSchedule.objects.filter(company=company, technician_id=from_tech, date=target_date).first()
        to_schedule = TechnicianSchedule.objects.filter(company=company, technician_id=to_tech, date=target_date).first()
        from_jobs_before = Decimal(getattr(from_schedule, "total_jobs", 0))
        to_jobs_before = Decimal(getattr(to_schedule, "total_jobs", 0))
        visit_load = Decimal(visit.estimated_duration_minutes + visit.estimated_travel_minutes)
        travel_penalty = Decimal("15.00") if site and visit.operational_site_id != getattr(site, "id", None) else Decimal("5.00")
        return SimulationComputation(
            baseline_snapshot={
                "from_technician_id": from_tech,
                "to_technician_id": to_tech,
                "from_total_jobs": float(from_jobs_before),
                "to_total_jobs": float(to_jobs_before),
                "visit_minutes": float(visit_load),
            },
            summary="Reatribuicao reduz sobrecarga do tecnico origem e aumenta moderadamente a carga do destino.",
            impact_score=Decimal("8.50"),
            confidence_level="medium",
            risk_delta=Decimal("-0.80") if to_jobs_before <= from_jobs_before else Decimal("0.20"),
            cost_delta=travel_penalty,
            sla_delta=Decimal("0.50") if to_jobs_before < from_jobs_before else Decimal("-0.25"),
            profit_delta=ZERO,
            travel_delta=travel_penalty,
            workload_delta=visit_load,
            recommendation="Aprovar reatribuicao." if to_jobs_before + 1 <= Decimal("6.00") else "Revisar capacidade do tecnico destino.",
            result_payload={
                "current": {"from_jobs": float(from_jobs_before), "to_jobs": float(to_jobs_before)},
                "proposed": {"from_jobs": float(from_jobs_before - 1), "to_jobs": float(to_jobs_before + 1)},
                "gains": ["load_balance", "sla_relief"],
                "tradeoffs": ["extra_travel"],
            },
        )


class PreventiveFrequencySimulationHandler(BaseSimulationHandler):
    simulation_type = "preventive_frequency_change_simulation"

    def run(self, *, company, site, input_payload):
        asset_queryset = Asset.objects.all()
        if company is not None:
            asset_queryset = asset_queryset.filter(operational_site__maintenance_client__company=company)
        if site is not None:
            asset_queryset = asset_queryset.filter(operational_site=site)
        asset_public_id = input_payload.get("asset_public_id")
        if asset_public_id:
            asset_queryset = asset_queryset.filter(public_id=asset_public_id)
        asset = asset_queryset.get()
        plan = MaintenancePlan.objects.filter(asset=asset, is_active=True).order_by("created_at").first()
        failures = asset.failure_events.count()
        current_days = Decimal(plan.frequency_value * 30 if plan and plan.frequency_type == "monthly" else 30)
        proposed_days = Decimal(input_payload.get("proposed_frequency_days", 15))
        preventive_cost_increase = Decimal(plan.estimated_duration_minutes if plan else 90) * Decimal("2.40")
        risk_reduction = Decimal(min(failures, 6)) * Decimal("0.45")
        return SimulationComputation(
            baseline_snapshot={
                "current_frequency_days": float(current_days),
                "recent_failures": failures,
                "estimated_duration_minutes": getattr(plan, "estimated_duration_minutes", 90),
            },
            summary="Aumento de frequencia preventiva eleva custo previsivel, mas reduz risco e corretivas provaveis.",
            impact_score=Decimal("11.00"),
            confidence_level="medium" if failures >= 2 else "low",
            risk_delta=-risk_reduction,
            cost_delta=preventive_cost_increase,
            sla_delta=Decimal("0.40"),
            profit_delta=-preventive_cost_increase,
            travel_delta=Decimal("10.00"),
            workload_delta=Decimal("90.00"),
            recommendation="Adotar frequencia maior para ativo critico." if failures >= 2 else "Rodar piloto antes de alterar definitivamente.",
            result_payload={
                "current": {"frequency_days": float(current_days), "risk_index": failures * 10},
                "proposed": {"frequency_days": float(proposed_days), "risk_index": max((failures * 10) - float(risk_reduction * Decimal('10')), 0)},
                "assumptions": [
                    "historico de falhas recente pondera reducao de risco",
                    "custo preventivo escala com duracao estimada do plano",
                ],
            },
        )


class ContractRepricingSimulationHandler(BaseSimulationHandler):
    simulation_type = "contract_repricing_simulation"

    def run(self, *, company, site, input_payload):
        contract = MaintenanceContract.objects.get(public_id=input_payload["contract_public_id"], company=company)
        current_value = Decimal(contract.contract_value)
        proposed_value = Decimal(str(input_payload.get("proposed_value", current_value * Decimal("1.08"))))
        margin_before = Decimal(str(input_payload.get("current_margin", "12.00")))
        cost_base = current_value * (Decimal("1.00") - (margin_before / Decimal("100.00")))
        margin_after = ((proposed_value - cost_base) / proposed_value) * Decimal("100.00") if proposed_value else ZERO
        return SimulationComputation(
            baseline_snapshot={
                "current_contract_value": str(current_value),
                "current_margin_percent": str(margin_before.quantize(Decimal("0.01"))),
            },
            summary=f"Reajuste projetado altera margem de {margin_before:.2f}% para {margin_after:.2f}%.",
            impact_score=(margin_after - margin_before).quantize(Decimal("0.01")),
            confidence_level="high",
            risk_delta=Decimal("-0.30") if margin_after > margin_before else Decimal("0.20"),
            cost_delta=ZERO,
            sla_delta=ZERO,
            profit_delta=(proposed_value - current_value).quantize(Decimal("0.01")),
            travel_delta=ZERO,
            workload_delta=ZERO,
            recommendation="Levar para aprovacao comercial." if margin_after > margin_before else "Nao reajustar neste formato.",
            result_payload={
                "current": {"contract_value": str(current_value), "margin_percent": str(margin_before.quantize(Decimal("0.01")))},
                "proposed": {"contract_value": str(proposed_value), "margin_percent": str(margin_after.quantize(Decimal("0.01")))},
                "tradeoffs": ["possible_client_resistance"],
            },
        )


class RouteConsolidationSimulationHandler(BaseSimulationHandler):
    simulation_type = "route_consolidation_simulation"

    def run(self, *, company, site, input_payload):
        target_date = timezone.datetime.strptime(input_payload["date"], "%Y-%m-%d").date() if input_payload.get("date") else timezone.localdate()
        visits = ScheduledVisit.objects.filter(company=company, scheduled_date=target_date)
        if site is not None:
            visits = visits.filter(operational_site=site)
        total = list(visits)
        same_city = sum(1 for visit in total if visit.city == (site.city if site else visit.city))
        baseline_travel = sum(visit.estimated_travel_minutes for visit in total)
        proposed_travel = max(baseline_travel - (same_city * 8), 0)
        cost_delta = Decimal(proposed_travel - baseline_travel) * Decimal("1.20")
        return SimulationComputation(
            baseline_snapshot={"visit_count": len(total), "travel_minutes": baseline_travel, "same_city_visits": same_city},
            summary="Consolidacao regional reduz deslocamento e melhora densidade operacional.",
            impact_score=Decimal(baseline_travel - proposed_travel),
            confidence_level="medium",
            risk_delta=Decimal("-0.40"),
            cost_delta=cost_delta,
            sla_delta=Decimal("0.30"),
            profit_delta=-cost_delta,
            travel_delta=Decimal(proposed_travel - baseline_travel),
            workload_delta=ZERO,
            recommendation="Consolidar visitas da mesma regiao." if proposed_travel < baseline_travel else "Ganho pequeno; manter plano atual.",
            result_payload={"current": {"travel_minutes": baseline_travel}, "proposed": {"travel_minutes": proposed_travel}},
        )


class WorkloadRedistributionSimulationHandler(BaseSimulationHandler):
    simulation_type = "workload_redistribution_simulation"

    def run(self, *, company, site, input_payload):
        target_date = timezone.datetime.strptime(input_payload["date"], "%Y-%m-%d").date() if input_payload.get("date") else timezone.localdate()
        schedules = list(TechnicianSchedule.objects.filter(company=company, date=target_date))
        if not schedules:
            before = [0, 0]
        else:
            before = [schedule.total_jobs for schedule in schedules]
        avg_jobs = Decimal(sum(before) / max(len(before), 1))
        max_jobs = Decimal(max(before) if before else 0)
        post_peak = max(avg_jobs.quantize(Decimal("0.01")), Decimal("0.00"))
        return SimulationComputation(
            baseline_snapshot={"job_distribution": before, "avg_jobs": float(avg_jobs)},
            summary="Redistribuicao tende a equilibrar carga e reduzir pico de sobrecarga.",
            impact_score=(max_jobs - post_peak).quantize(Decimal("0.01")),
            confidence_level="medium",
            risk_delta=Decimal("-0.60"),
            cost_delta=ZERO,
            sla_delta=Decimal("0.40"),
            profit_delta=ZERO,
            travel_delta=Decimal("5.00"),
            workload_delta=(max_jobs - post_peak).quantize(Decimal("0.01")),
            recommendation="Aplicar redistribuicao gradual." if max_jobs > avg_jobs else "Distribuicao ja esta equilibrada.",
            result_payload={"current": {"distribution": before}, "proposed": {"peak_jobs": str(post_peak)}},
        )


class MarketplaceCandidateSwapSimulationHandler(BaseSimulationHandler):
    simulation_type = "marketplace_candidate_swap_simulation"

    def run(self, *, company, site, input_payload):
        service_request_public_id = input_payload.get("service_request_public_id")
        current_candidate = input_payload.get("current_candidate_public_id")
        proposed_candidate = input_payload.get("proposed_candidate_public_id")

        if not service_request_public_id:
            return SimulationComputation(
                baseline_snapshot={
                    "status": "skipped",
                    "reason": "missing_service_request_public_id",
                },
                summary="Simulacao ignorada: service_request_public_id ausente.",
                impact_score=ZERO,
                confidence_level="low",
                risk_delta=ZERO,
                cost_delta=ZERO,
                sla_delta=ZERO,
                profit_delta=ZERO,
                travel_delta=ZERO,
                workload_delta=ZERO,
                recommendation="Manter fluxo atual: nao ha solicitacao de marketplace vinculada para simular troca de candidato.",
                result_payload={
                    "status": "skipped",
                    "reason": "missing_service_request_public_id",
                },
            )

        service_request = TechnicianServiceRequest.objects.filter(
            public_id=service_request_public_id,
            requester_company=company,
        ).first()

        if service_request is None:
            return SimulationComputation(
                baseline_snapshot={
                    "status": "skipped",
                    "reason": "service_request_not_found",
                    "service_request_public_id": str(service_request_public_id),
                },
                summary="Simulacao ignorada: TechnicianServiceRequest nao encontrada para o public_id informado.",
                impact_score=ZERO,
                confidence_level="low",
                risk_delta=ZERO,
                cost_delta=ZERO,
                sla_delta=ZERO,
                profit_delta=ZERO,
                travel_delta=ZERO,
                workload_delta=ZERO,
                recommendation="Manter fluxo atual: nao foi possivel localizar a solicitacao de marketplace para comparar candidatos.",
                result_payload={
                    "status": "skipped",
                    "reason": "service_request_not_found",
                    "service_request_public_id": str(service_request_public_id),
                },
            )

        if not proposed_candidate:
            return SimulationComputation(
                baseline_snapshot={
                    "status": "skipped",
                    "reason": "missing_proposed_candidate_public_id",
                    "request_priority": service_request.priority,
                },
                summary="Simulacao ignorada: proposed_candidate_public_id ausente.",
                impact_score=ZERO,
                confidence_level="low",
                risk_delta=ZERO,
                cost_delta=ZERO,
                sla_delta=ZERO,
                profit_delta=ZERO,
                travel_delta=ZERO,
                workload_delta=ZERO,
                recommendation="Manter candidato atual: nao ha candidato proposto para comparar.",
                result_payload={
                    "status": "skipped",
                    "reason": "missing_proposed_candidate_public_id",
                },
            )

        proposed_profile = TechnicianProfile.objects.filter(
            public_id=proposed_candidate,
        ).first()

        if proposed_profile is None:
            return SimulationComputation(
                baseline_snapshot={
                    "status": "skipped",
                    "reason": "proposed_candidate_not_found",
                    "request_priority": service_request.priority,
                },
                summary="Simulacao ignorada: TechnicianProfile proposto nao encontrado.",
                impact_score=ZERO,
                confidence_level="low",
                risk_delta=ZERO,
                cost_delta=ZERO,
                sla_delta=ZERO,
                profit_delta=ZERO,
                travel_delta=ZERO,
                workload_delta=ZERO,
                recommendation="Manter candidato atual: candidato proposto nao foi localizado.",
                result_payload={
                    "status": "skipped",
                    "reason": "proposed_candidate_not_found",
                    "proposed_candidate_public_id": str(proposed_candidate),
                },
            )

        current_score = Decimal("70.00")

        if current_candidate:
            current_match = TechnicianMatchingRecord.objects.filter(
                technician_service_request=service_request,
                technician_profile__public_id=current_candidate,
            ).first()

            if current_match and current_match.match_score is not None:
                current_score = Decimal(current_match.match_score)

        proposed_match = TechnicianMatchingRecord.objects.filter(
            technician_service_request=service_request,
            technician_profile=proposed_profile,
        ).first()

        proposed_score = (
            Decimal(proposed_match.match_score)
            if proposed_match and proposed_match.match_score is not None
            else Decimal("82.00")
        )

        risk_delta = Decimal("-0.70") if proposed_score > current_score else Decimal("0.25")

        sla_delta = (
            Decimal("0.55")
            if proposed_profile.marketplace_status == TechnicianProfile.MarketplaceStatus.AVAILABLE
            else Decimal("-0.20")
        )

        return SimulationComputation(
            baseline_snapshot={
                "current_match_score": str(current_score),
                "request_priority": service_request.priority,
            },
            summary=(
                "Troca de candidato melhora aderencia tecnica e disponibilidade estimada."
                if proposed_score > current_score
                else "Troca de candidato nao melhora o matching atual."
            ),
            impact_score=(proposed_score - current_score).quantize(Decimal("0.01")),
            confidence_level="medium",
            risk_delta=risk_delta,
            cost_delta=ZERO,
            sla_delta=sla_delta,
            profit_delta=ZERO,
            travel_delta=Decimal("-8.00") if proposed_match and proposed_match.distance_km else Decimal("0.00"),
            workload_delta=ZERO,
            recommendation="Trocar candidato." if proposed_score > current_score else "Manter candidato atual.",
            result_payload={
                "current": {
                    "match_score": str(current_score),
                },
                "proposed": {
                    "match_score": str(proposed_score),
                    "candidate": proposed_profile.display_name,
                },
            },
        )


class MaintenanceActionPlanSimulationHandler(BaseSimulationHandler):
    simulation_type = "maintenance_action_plan_simulation"

    def run(self, *, company, site, input_payload):
        asset_queryset = Asset.objects.filter(public_id=input_payload["asset_public_id"])
        if company is not None:
            asset_queryset = asset_queryset.filter(operational_site__maintenance_client__company=company)
        if site is not None:
            asset_queryset = asset_queryset.filter(operational_site=site)
        asset = asset_queryset.get()
        failures = asset.failure_events.count()
        open_orders = asset.service_orders.filter(status__in=["open", "scheduled", "in_progress", "on_hold"]).count()
        additional_cost = Decimal("240.00") + (Decimal(open_orders) * Decimal("35.00"))
        risk_reduction = Decimal(min(failures + open_orders, 8)) * Decimal("0.55")
        return SimulationComputation(
            baseline_snapshot={"recent_failures": failures, "open_orders": open_orders, "criticality": asset.criticality},
            summary="Plano extra de manutencao reduz risco operacional no ativo critico ao custo de maior carga preventiva.",
            impact_score=(risk_reduction * Decimal("10.00")).quantize(Decimal("0.01")),
            confidence_level="medium" if failures or open_orders else "low",
            risk_delta=-risk_reduction,
            cost_delta=additional_cost,
            sla_delta=Decimal("0.35"),
            profit_delta=-additional_cost,
            travel_delta=Decimal("15.00"),
            workload_delta=Decimal("120.00"),
            recommendation="Executar plano extraordinario." if asset.criticality in {"high", "critical"} else "Priorizar somente se houver capacidade.",
            result_payload={
                "current": {"risk_index": failures + open_orders, "preventive_extra": False},
                "proposed": {"risk_index": max((failures + open_orders) - float(risk_reduction), 0), "preventive_extra": True},
                "assumptions": ["efeito preventivo heuristico com base em backlog e falhas"],
            },
        )


SIMULATION_HANDLERS = [
    RouteReorderSimulationHandler(),
    TechnicianReassignmentSimulationHandler(),
    PreventiveFrequencySimulationHandler(),
    ContractRepricingSimulationHandler(),
    RouteConsolidationSimulationHandler(),
    WorkloadRedistributionSimulationHandler(),
    MarketplaceCandidateSwapSimulationHandler(),
    MaintenanceActionPlanSimulationHandler(),
]


class SimulationHandlerRegistry:
    @classmethod
    def get_handler(cls, simulation_type: str):
        for handler in SIMULATION_HANDLERS:
            if handler.supports(simulation_type):
                return handler
        return None
