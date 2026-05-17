from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.analytics_platform.models import AnalyticsSnapshot, OperationalMetrics, TechnicianPerformance
from apps.marketplace_technicians.models import TechnicianAssignment, TechnicianMatchingRecord, TechnicianProfile, TechnicianServiceRequest
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import RoutePlan, ScheduledVisit, TechnicianAvailabilityWindow, TechnicianSchedule
from apps.smart_system.services.scheduling_service import TechnicianRoutingService

User = get_user_model()


@dataclass
class SchedulingRecommendationDraft:
    recommendation_type: str
    severity: str
    priority: str
    title: str
    summary: str
    explanation: str
    evidence_summary: str
    suggested_action: str
    attention_score: int
    entity_type: str
    entity_id: str
    payload: dict
    requires_human_approval: bool = True


@dataclass
class SchedulingActionProposalDraft:
    action_type: str
    target_entity: str
    target_entity_id: str
    title: str
    summary: str
    proposed_payload: dict
    priority: str = "medium"
    approval_required: bool = True


class SchedulingOptimizationService:
    DEFAULT_THRESHOLDS = {
        "overload_jobs": 6,
        "overload_minutes": 600,
        "max_travel_minutes": 180,
        "max_idle_minutes": 180,
        "sla_risk_hours": 24,
        "unassigned_critical_hours": 24,
        "reorder_gain_minutes": 20,
        "reassignment_capacity_buffer": 90,
    }

    @classmethod
    def get_thresholds(cls, definition) -> dict:
        config = getattr(definition, "config", {}) or {}
        return {**cls.DEFAULT_THRESHOLDS, **config.get("heuristics", {})}

    @classmethod
    def build_scope_context(
        cls,
        *,
        company,
        site=None,
        technician=None,
        target_date=None,
        trigger_reference="",
        triggered_by=None,
        definition=None,
    ) -> dict:
        if company is None:
            raise ValueError("Scheduling agent requires a company context.")

        thresholds = cls.get_thresholds(definition)
        target_date = target_date or timezone.localdate()
        TechnicianRoutingService.refresh_plannable_visits(schedule_date=target_date, company=company, site=site)

        visits = ScheduledVisit.objects.select_related(
            "company",
            "operational_site",
            "asset",
            "asset__category",
            "work_order",
            "service_assignment",
            "maintenance_plan",
            "technician",
            "technician_profile",
            "technician_schedule",
            "route_plan",
        ).filter(company=company, scheduled_date=target_date)
        if site is not None:
            visits = visits.filter(operational_site=site)
        if technician is not None:
            visits = visits.filter(technician=technician)
        visits = list(visits.order_by("technician_id", "route_order", "scheduled_start", "created_at"))

        technician_ids = {visit.technician_id for visit in visits if visit.technician_id}
        if technician is not None:
            technician_ids.add(technician.id)

        schedules = TechnicianSchedule.objects.select_related("technician", "technician_profile").filter(company=company, date=target_date)
        if site is not None:
            schedules = schedules.filter(operational_site=site)
        if technician is not None:
            schedules = schedules.filter(technician=technician)
        schedule_by_technician = {schedule.technician_id: schedule for schedule in schedules}

        route_plans = RoutePlan.objects.select_related("technician", "technician_profile").filter(company=company, date=target_date)
        if site is not None:
            route_plans = route_plans.filter(operational_site=site)
        if technician is not None:
            route_plans = route_plans.filter(technician=technician)
        route_by_technician = {route.technician_id: route for route in route_plans}

        availability_qs = TechnicianAvailabilityWindow.objects.select_related("technician", "technician_profile").filter(company=company)
        if site is not None:
            availability_qs = availability_qs.filter(Q(operational_site=site) | Q(operational_site__isnull=True))
        availability_qs = availability_qs.filter(Q(blocked_date=target_date) | Q(weekday=target_date.isoweekday()))
        availability_by_technician = defaultdict(list)
        for item in availability_qs:
            availability_by_technician[item.technician_id].append(item)

        unassigned_visits = [visit for visit in visits if visit.technician_id is None]
        technician_contexts = []
        grouped_visits = defaultdict(list)
        for visit in visits:
            if visit.technician_id:
                grouped_visits[visit.technician_id].append(visit)

        candidate_technician_ids = set(technician_ids) | set(grouped_visits.keys()) | set(schedule_by_technician.keys())
        technician_profiles = {
            profile.user_id: profile
            for profile in TechnicianProfile.objects.select_related("user").filter(user_id__in=candidate_technician_ids)
        }
        users = {user.id: user for user in User.objects.filter(id__in=candidate_technician_ids)}
        for technician_id in sorted(candidate_technician_ids):
            visits_for_technician = grouped_visits.get(technician_id, [])
            technician_user = users.get(technician_id)
            technician_contexts.append(
                cls.build_technician_context(
                    technician=technician_user,
                    profile=technician_profiles.get(technician_id),
                    visits=visits_for_technician,
                    schedule=schedule_by_technician.get(technician_id),
                    route_plan=route_by_technician.get(technician_id),
                    availability=availability_by_technician.get(technician_id, []),
                    target_date=target_date,
                    thresholds=thresholds,
                )
            )

        return {
            "company_id": company.id,
            "company_slug": company.slug,
            "site_id": getattr(site, "id", None),
            "site_code": getattr(site, "code", ""),
            "technician_id": getattr(technician, "id", None),
            "target_date": target_date.isoformat(),
            "trigger_reference": trigger_reference,
            "triggered_by": getattr(triggered_by, "id", None),
            "thresholds": thresholds,
            "technicians": technician_contexts,
            "unassigned_visits": [cls.serialize_visit(visit) for visit in unassigned_visits],
            "day_summary": cls.build_day_summary(technician_contexts=technician_contexts, unassigned_visits=unassigned_visits, target_date=target_date),
            "analytics": cls.query_analytics(company=company),
        }

    @classmethod
    def build_technician_context(cls, *, technician, profile, visits, schedule, route_plan, availability, target_date, thresholds):
        total_duration = sum(visit.estimated_duration_minutes for visit in visits)
        total_travel = sum(visit.estimated_travel_minutes for visit in visits)
        total_minutes = total_duration + total_travel
        route_travel = cls.estimate_route_travel(visits)
        optimized_route = cls.simulate_route_reorder(visits=visits, target_date=target_date)
        availability_window = cls.select_primary_availability(availability, target_date=target_date)
        max_jobs = availability_window.max_daily_jobs if availability_window else thresholds["overload_jobs"]
        max_hours = availability_window.max_daily_hours if availability_window else 8
        capacity_minutes = max_hours * 60
        free_capacity = max(capacity_minutes - total_minutes, 0)
        conflicts = cls.detect_conflicts(visits)
        urgent_after_low = cls.detect_priority_inversion(visits)
        sla_risk_visits = cls.detect_sla_risk_visits(visits, thresholds=thresholds)
        return {
            "technician_id": getattr(technician, "id", None),
            "technician_public_id": "",
            "technician_name": getattr(profile, "display_name", "") or getattr(technician, "display_name", "") or getattr(technician, "email", "Tecnico"),
            "date": target_date.isoformat(),
            "visit_count": len(visits),
            "scheduled_minutes": total_duration,
            "travel_minutes": total_travel,
            "route_travel_minutes": route_travel,
            "optimized_travel_minutes": optimized_route["total_travel_minutes"],
            "optimized_travel_gain": max(route_travel - optimized_route["total_travel_minutes"], 0),
            "total_minutes": total_minutes,
            "capacity_minutes": capacity_minutes,
            "free_capacity_minutes": free_capacity,
            "max_jobs": max_jobs,
            "max_hours": max_hours,
            "has_conflicts": bool(conflicts),
            "conflicts": conflicts,
            "urgent_after_low": urgent_after_low,
            "sla_risk_visits": sla_risk_visits,
            "route_plan_public_id": str(route_plan.public_id) if route_plan else "",
            "schedule_public_id": str(schedule.public_id) if schedule else "",
            "availability": {
                "is_available": availability_window.is_available if availability_window else True,
                "blocked_date": availability_window.blocked_date.isoformat() if availability_window and availability_window.blocked_date else "",
                "start_time": availability_window.start_time.isoformat() if availability_window and availability_window.start_time else "",
                "end_time": availability_window.end_time.isoformat() if availability_window and availability_window.end_time else "",
            },
            "visits": [cls.serialize_visit(visit) for visit in visits],
            "optimized_order": optimized_route["ordered_public_ids"],
        }

    @classmethod
    def analyze_scope(cls, *, context: dict, definition=None):
        thresholds = context["thresholds"]
        recommendations = []
        proposals = []
        health_flags = []
        technician_contexts = context["technicians"]
        capacity_by_tech = {item["technician_id"]: item for item in technician_contexts if item["technician_id"]}

        for tech_context in technician_contexts:
            tech_recommendations, tech_proposals, tech_flags = cls.analyze_technician_context(
                technician_context=tech_context,
                thresholds=thresholds,
                capacity_by_tech=capacity_by_tech,
                unassigned_visits=context["unassigned_visits"],
            )
            recommendations.extend(tech_recommendations)
            proposals.extend(tech_proposals)
            health_flags.extend(tech_flags)

        day_recommendations, day_proposals, day_flags = cls.analyze_day_context(
            context=context,
            thresholds=thresholds,
            capacity_by_tech=capacity_by_tech,
        )
        recommendations.extend(day_recommendations)
        proposals.extend(day_proposals)
        health_flags.extend(day_flags)

        recommendations.sort(key=lambda item: (item.attention_score, cls._severity_rank(item.severity), cls._priority_rank(item.priority)), reverse=True)
        proposals.sort(key=lambda item: (cls._priority_rank(item.priority), item.action_type), reverse=True)
        summary = (
            f"Scheduling optimization completed for {context['target_date']}: "
            f"{len(recommendations)} recommendations and {len(proposals)} proposals."
        )
        return recommendations, proposals, health_flags, summary

    @classmethod
    def analyze_technician_context(cls, *, technician_context, thresholds, capacity_by_tech, unassigned_visits):
        recommendations = []
        proposals = []
        flags = []
        tech_id = technician_context["technician_id"]
        if tech_id is None:
            return recommendations, proposals, flags
        tech_name = technician_context["technician_name"]
        tech_entity_id = str(tech_id)
        evidence = cls._build_evidence(technician_context)

        overloaded = technician_context["visit_count"] > technician_context["max_jobs"] or technician_context["total_minutes"] > technician_context["capacity_minutes"]
        if overloaded:
            cls.log_signal(
                event_type="agent.scheduling.overload.detected",
                technician_context=technician_context,
                payload={"total_minutes": technician_context["total_minutes"], "capacity_minutes": technician_context["capacity_minutes"]},
            )
            summary = (
                f"Tecnico {tech_name} possui {technician_context['visit_count']} visitas com carga estimada de "
                f"{cls._format_minutes(technician_context['total_minutes'])}."
            )
            recommendations.append(
                SchedulingRecommendationDraft(
                    recommendation_type="technician_overload",
                    severity="high",
                    priority="high",
                    title=f"Sobrecarga operacional de {tech_name}",
                    summary=summary,
                    explanation="A soma de duracao estimada e deslocamento excede a capacidade configurada para o dia.",
                    evidence_summary=evidence,
                    suggested_action="Redistribuir parte das visitas e revisar a rota do tecnico.",
                    attention_score=88,
                    entity_type="user",
                    entity_id=tech_entity_id,
                    payload={"technician": technician_context, "signals": ["technician_overload"]},
                )
            )
            reassignment_candidates = cls.find_reassignment_candidates(source_context=technician_context, capacity_by_tech=capacity_by_tech)
            if reassignment_candidates:
                candidate = reassignment_candidates[0]
                proposals.append(
                    SchedulingActionProposalDraft(
                        action_type="reassign_visits_between_technicians",
                        target_entity="technician_schedule",
                        target_entity_id=technician_context["schedule_public_id"] or tech_entity_id,
                        title=f"Redistribuir agenda de {tech_name}",
                        summary=f"Sugerida redistribuicao para {candidate['technician_name']} com capacidade ociosa.",
                        proposed_payload={
                            "from_technician_id": tech_id,
                            "to_technician_id": candidate["technician_id"],
                            "date": technician_context["date"],
                        },
                        priority="high",
                    )
                )
            flags.append(cls.build_health_flag(technician_context=technician_context, flag_type="technician_overload", summary=summary, attention_score=88))

        if technician_context["has_conflicts"]:
            cls.log_signal(
                event_type="agent.scheduling.conflict.detected",
                technician_context=technician_context,
                payload={"conflicts": technician_context["conflicts"]},
            )
            recommendations.append(
                SchedulingRecommendationDraft(
                    recommendation_type="visit_reassignment",
                    severity="high",
                    priority="high",
                    title=f"Conflitos detectados na agenda de {tech_name}",
                    summary=f"{tech_name} possui {len(technician_context['conflicts'])} conflito(s) de agenda no dia.",
                    explanation="Foram observadas sobreposicoes, janela incompatível ou indisponibilidade do tecnico.",
                    evidence_summary=evidence,
                    suggested_action="Reprogramar ou redistribuir visitas conflitantes antes do inicio da rota.",
                    attention_score=84,
                    entity_type="user",
                    entity_id=tech_entity_id,
                    payload={"technician": technician_context, "signals": ["conflict"]},
                )
            )
            proposals.append(
                SchedulingActionProposalDraft(
                    action_type="block_schedule_for_review",
                    target_entity="technician_schedule",
                    target_entity_id=technician_context["schedule_public_id"] or tech_entity_id,
                    title=f"Bloquear agenda de {tech_name} para revisao",
                    summary="Agenda com conflito precisa de revisao operacional antes da execucao.",
                    proposed_payload={"technician_id": tech_id, "date": technician_context["date"], "conflicts": technician_context["conflicts"]},
                    priority="high",
                )
            )
            flags.append(cls.build_health_flag(technician_context=technician_context, flag_type="conflict", summary=f"Conflitos na agenda de {tech_name}", attention_score=84))

        if technician_context["optimized_travel_gain"] >= thresholds["reorder_gain_minutes"]:
            recommendations.append(
                SchedulingRecommendationDraft(
                    recommendation_type="route_reorder",
                    severity="medium",
                    priority="high",
                    title=f"Rota subotima para {tech_name}",
                    summary=f"A rota atual de {tech_name} pode reduzir {technician_context['optimized_travel_gain']} min com reordenacao.",
                    explanation="A sequencia atual nao aproveita a proximidade geográfica das visitas.",
                    evidence_summary=evidence,
                    suggested_action="Aplicar reordenacao proposta para reduzir deslocamento e folga operacional.",
                    attention_score=73,
                    entity_type="route_plan",
                    entity_id=technician_context["route_plan_public_id"] or tech_entity_id,
                    payload={"technician": technician_context, "signals": ["route_efficiency"], "optimized_order": technician_context["optimized_order"]},
                )
            )
            proposals.append(
                SchedulingActionProposalDraft(
                    action_type="reorder_route_plan",
                    target_entity="route_plan",
                    target_entity_id=technician_context["route_plan_public_id"] or tech_entity_id,
                    title=f"Reordenar rota de {tech_name}",
                    summary="Sequencia alternativa reduz deslocamento estimado.",
                    proposed_payload={"technician_id": tech_id, "date": technician_context["date"], "ordered_public_ids": technician_context["optimized_order"]},
                    priority="high",
                )
            )
            flags.append(cls.build_health_flag(technician_context=technician_context, flag_type="route_efficiency", summary=f"Rota ineficiente de {tech_name}", attention_score=73))

        if technician_context["sla_risk_visits"]:
            visit = technician_context["sla_risk_visits"][0]
            recommendations.append(
                SchedulingRecommendationDraft(
                    recommendation_type="sla_risk_alert",
                    severity="critical" if visit["priority"] == "urgent" else "high",
                    priority="immediate",
                    title=f"Visita com risco de SLA para {tech_name}",
                    summary=f"{visit['title']} esta em risco de atraso ou atendimento tardio na agenda de {tech_name}.",
                    explanation="Atendimento prioritario esta tarde na rota ou muito proximo do prazo operacional.",
                    evidence_summary=evidence,
                    suggested_action="Antecipar a visita critica ou reatribuir para tecnico com capacidade disponivel.",
                    attention_score=91,
                    entity_type="scheduled_visit",
                    entity_id=visit["public_id"],
                    payload={"technician": technician_context, "signals": ["sla_risk"], "visit": visit},
                )
            )
            proposals.append(
                SchedulingActionProposalDraft(
                    action_type="move_visit_to_earlier_slot",
                    target_entity="scheduled_visit",
                    target_entity_id=visit["public_id"],
                    title=f"Antecipar visita critica {visit['title']}",
                    summary="Visita em risco de SLA deve ganhar prioridade operacional imediata.",
                    proposed_payload={"visit_public_id": visit["public_id"], "technician_id": tech_id, "date": technician_context["date"]},
                    priority="immediate",
                )
            )
            flags.append(cls.build_health_flag(technician_context=technician_context, flag_type="sla_risk", summary=f"Risco de SLA para {tech_name}", attention_score=91))

        if technician_context["free_capacity_minutes"] >= thresholds["max_idle_minutes"] and unassigned_visits:
            visit = unassigned_visits[0]
            recommendations.append(
                SchedulingRecommendationDraft(
                    recommendation_type="idle_capacity_opportunity",
                    severity="medium",
                    priority="medium",
                    title=f"Capacidade livre de {tech_name}",
                    summary=f"{tech_name} possui {cls._format_minutes(technician_context['free_capacity_minutes'])} livres e pode absorver nova visita.",
                    explanation="Foi identificada folga operacional relevante no dia e backlog nao alocado pendente.",
                    evidence_summary=evidence,
                    suggested_action="Avaliar encaixe de visita nao alocada na agenda do tecnico.",
                    attention_score=64,
                    entity_type="user",
                    entity_id=tech_entity_id,
                    payload={"technician": technician_context, "signals": ["idle_capacity"], "candidate_visit": visit},
                )
            )
            proposals.append(
                SchedulingActionProposalDraft(
                    action_type="schedule_unassigned_visit",
                    target_entity="technician_schedule",
                    target_entity_id=technician_context["schedule_public_id"] or tech_entity_id,
                    title=f"Encaixar visita em agenda de {tech_name}",
                    summary=f"Sugerido encaixe da visita {visit['title']} na capacidade livre do tecnico.",
                    proposed_payload={"technician_id": tech_id, "visit_public_id": visit["public_id"], "date": technician_context["date"]},
                    priority="medium",
                )
            )
            flags.append(cls.build_health_flag(technician_context=technician_context, flag_type="idle_capacity", summary=f"Capacidade ociosa de {tech_name}", attention_score=64))

        return recommendations, proposals, flags

    @classmethod
    def analyze_day_context(cls, *, context, thresholds, capacity_by_tech):
        recommendations = []
        proposals = []
        flags = []
        if context["unassigned_visits"]:
            critical_visits = [visit for visit in context["unassigned_visits"] if visit["priority"] in {"urgent", "high"}]
            target_visit = critical_visits[0] if critical_visits else context["unassigned_visits"][0]
            candidate = cls.pick_best_capacity_candidate(target_visit=target_visit, capacity_by_tech=capacity_by_tech)
            marketplace_candidates = cls.query_marketplace_candidates(company_id=context["company_id"], visit_payload=target_visit)
            severity = "critical" if target_visit["priority"] == "urgent" else "high"
            recommendations.append(
                SchedulingRecommendationDraft(
                    recommendation_type="unassigned_visit_attention",
                    severity=severity,
                    priority="immediate" if target_visit["priority"] == "urgent" else "high",
                    title=f"Visita nao alocada em {context['target_date']}",
                    summary=f"{target_visit['title']} permanece sem tecnico alocado para {context['target_date']}.",
                    explanation="A visita segue pendente de alocacao, elevando risco operacional e de prazo.",
                    evidence_summary=f"visitas nao alocadas: {len(context['unassigned_visits'])}; prioridade: {target_visit['priority']}; site: {target_visit['site_name']}",
                    suggested_action="Encaixar imediatamente em tecnico com capacidade ou acionar alternativa via matching.",
                    attention_score=89 if target_visit["priority"] == "urgent" else 78,
                    entity_type="scheduled_visit",
                    entity_id=target_visit["public_id"],
                    payload={"signals": ["unassigned_visit"], "visit": target_visit, "suggested_technician": candidate, "marketplace_candidates": marketplace_candidates},
                )
            )
            proposals.append(
                SchedulingActionProposalDraft(
                    action_type="suggest_alternative_technician_via_matching",
                    target_entity="scheduled_visit",
                    target_entity_id=target_visit["public_id"],
                    title=f"Sugerir tecnico alternativo para {target_visit['title']}",
                    summary="Visita nao alocada requer encaixe ou remanejamento imediato.",
                    proposed_payload={"visit_public_id": target_visit["public_id"], "candidate": candidate, "marketplace_candidates": marketplace_candidates, "date": context["target_date"]},
                    priority="immediate" if target_visit["priority"] == "urgent" else "high",
                )
            )
            flags.append({
                "technician_id": candidate["technician_id"] if candidate else None,
                "schedule_date": context["target_date"],
                "flag_type": "unassigned_backlog",
                "summary": f"Backlog nao alocado em {context['target_date']}",
                "attention_score": 82,
                "risk_level": "high",
                "payload": {"visit": target_visit, "candidate": candidate},
            })
        return recommendations, proposals, flags

    @classmethod
    def build_day_summary(cls, *, technician_contexts, unassigned_visits, target_date):
        return {
            "date": target_date.isoformat(),
            "technicians": len(technician_contexts),
            "overloaded_technicians": sum(1 for item in technician_contexts if item["total_minutes"] > item["capacity_minutes"] or item["visit_count"] > item["max_jobs"]),
            "technicians_with_conflict": sum(1 for item in technician_contexts if item["has_conflicts"]),
            "idle_technicians": sum(1 for item in technician_contexts if item["free_capacity_minutes"] >= 180),
            "unassigned_visits": len(unassigned_visits),
            "sla_risk_visits": sum(len(item["sla_risk_visits"]) for item in technician_contexts),
        }

    @classmethod
    def query_analytics(cls, *, company):
        latest_metrics = OperationalMetrics.objects.filter(company=company).order_by("-period_start").first()
        productivity = list(
            TechnicianPerformance.objects.filter(company=company)
            .select_related("technician")
            .order_by("-period_start")[:10]
        )
        snapshot = AnalyticsSnapshot.objects.filter(
            snapshot_type__startswith=f"executive_company:{company.slug}",
        ).order_by("-snapshot_date", "-created_at").first()
        return {
            "operational_metrics": {
                "total_work_orders": getattr(latest_metrics, "total_work_orders", 0),
                "avg_execution_time": float(getattr(latest_metrics, "avg_execution_time", 0) or 0),
                "sla_compliance_rate": float(getattr(latest_metrics, "sla_compliance_rate", 0) or 0),
            },
            "technician_productivity": [
                {
                    "technician_id": item.technician_id,
                    "jobs_completed": item.jobs_completed,
                    "avg_execution_time": float(item.avg_execution_time or 0),
                    "total_response_minutes": item.total_response_minutes,
                }
                for item in productivity
            ],
            "snapshot": getattr(snapshot, "data_json", {}) or {},
        }

    @classmethod
    def serialize_visit(cls, visit: ScheduledVisit):
        related_priority = visit.priority
        opened_at = visit.work_order.opened_at if visit.work_order_id else None
        return {
            "public_id": str(visit.public_id),
            "title": visit.title,
            "priority": related_priority,
            "status": visit.status,
            "technician_id": visit.technician_id,
            "technician_name": getattr(visit.technician_profile, "display_name", "") or getattr(visit.technician, "display_name", "") or getattr(visit.technician, "email", ""),
            "site_name": getattr(visit.operational_site, "name", ""),
            "site_code": getattr(visit.operational_site, "code", ""),
            "city": visit.city,
            "state": visit.state,
            "route_order": visit.route_order,
            "estimated_duration_minutes": visit.estimated_duration_minutes,
            "estimated_travel_minutes": visit.estimated_travel_minutes,
            "scheduled_start": visit.scheduled_start.isoformat() if visit.scheduled_start else "",
            "scheduled_end": visit.scheduled_end.isoformat() if visit.scheduled_end else "",
            "window_start": visit.window_start.isoformat() if visit.window_start else "",
            "window_end": visit.window_end.isoformat() if visit.window_end else "",
            "conflict_flags": list(visit.conflict_flags or []),
            "work_order_public_id": str(visit.work_order.public_id) if visit.work_order_id else "",
            "work_order_number": getattr(visit.work_order, "order_number", ""),
            "opened_at": opened_at.isoformat() if opened_at else "",
            "source_type": visit.source_type,
        }

    @classmethod
    def estimate_route_travel(cls, visits):
        ordered = sorted(visits, key=lambda item: (item.route_order, item.scheduled_start or timezone.now()))
        total = 0
        previous = None
        for visit in ordered:
            total += TechnicianRoutingService._estimate_travel_minutes(previous, visit)
            previous = visit
        return total

    @classmethod
    def simulate_route_reorder(cls, *, visits, target_date):
        if not visits:
            return {"ordered_public_ids": [], "total_travel_minutes": 0}
        ordered = sorted(
            visits,
            key=lambda visit: (
                {"urgent": 0, "high": 1, "medium": 2, "low": 3}.get(visit.priority, 4),
                visit.window_start or TechnicianRoutingService.DEFAULT_START_TIME,
                visit.city or "",
                visit.location_label or "",
            ),
        )
        previous = None
        total = 0
        for visit in ordered:
            total += TechnicianRoutingService._estimate_travel_minutes(previous, visit)
            previous = visit
        return {"ordered_public_ids": [str(visit.public_id) for visit in ordered], "total_travel_minutes": total}

    @classmethod
    def simulate_visit_reassignment(cls, *, visit_payload, technician_context):
        return {
            "visit_public_id": visit_payload["public_id"],
            "technician_id": technician_context["technician_id"],
            "remaining_capacity_minutes": max(technician_context["free_capacity_minutes"] - visit_payload["estimated_duration_minutes"] - visit_payload["estimated_travel_minutes"], 0),
        }

    @classmethod
    def detect_conflicts(cls, visits):
        conflicts = []
        ordered = sorted(visits, key=lambda item: item.scheduled_start or timezone.now())
        for index, visit in enumerate(ordered):
            if visit.conflict_flags:
                conflicts.append({"visit_public_id": str(visit.public_id), "flags": list(visit.conflict_flags)})
            for other in ordered[index + 1 :]:
                if not visit.scheduled_start or not visit.scheduled_end or not other.scheduled_start or not other.scheduled_end:
                    continue
                if visit.scheduled_start < other.scheduled_end and visit.scheduled_end > other.scheduled_start:
                    conflicts.append({"visit_public_id": str(visit.public_id), "flags": ["overlap"]})
                    break
        return conflicts

    @classmethod
    def detect_priority_inversion(cls, visits):
        ordered = sorted(visits, key=lambda item: item.route_order or 999)
        seen_lower_before = False
        for visit in ordered:
            if visit.priority in {"low", "medium"}:
                seen_lower_before = True
            if seen_lower_before and visit.priority in {"urgent", "high"}:
                return True
        return False

    @classmethod
    def detect_sla_risk_visits(cls, visits, thresholds):
        risks = []
        now = timezone.now()
        ordered = sorted(visits, key=lambda item: (item.route_order, item.scheduled_start or now))
        for index, visit in enumerate(ordered):
            if visit.priority not in {"urgent", "high"}:
                continue
            opened_at = getattr(visit.work_order, "opened_at", None)
            hours_since_open = ((now - opened_at).total_seconds() / 3600) if opened_at else 0
            if index >= 2 or hours_since_open >= thresholds["sla_risk_hours"] or "after_window" in (visit.conflict_flags or []):
                risks.append(cls.serialize_visit(visit))
        return risks

    @classmethod
    def select_primary_availability(cls, availability_items, *, target_date):
        blocked = next((item for item in availability_items if item.blocked_date == target_date), None)
        if blocked:
            return blocked
        return next((item for item in availability_items if item.weekday == target_date.isoweekday()), None)

    @classmethod
    def find_reassignment_candidates(cls, *, source_context, capacity_by_tech):
        candidates = []
        for candidate in capacity_by_tech.values():
            if candidate["technician_id"] == source_context["technician_id"]:
                continue
            if candidate["free_capacity_minutes"] < cls.DEFAULT_THRESHOLDS["reassignment_capacity_buffer"]:
                continue
            if candidate["availability"]["is_available"] is False:
                continue
            candidates.append(candidate)
        candidates.sort(key=lambda item: (-item["free_capacity_minutes"], item["travel_minutes"], item["visit_count"]))
        return candidates

    @classmethod
    def pick_best_capacity_candidate(cls, *, target_visit, capacity_by_tech):
        candidates = []
        for candidate in capacity_by_tech.values():
            if candidate["free_capacity_minutes"] <= 0 or candidate["availability"]["is_available"] is False:
                continue
            city_match = 1 if any(visit["city"] == target_visit["city"] for visit in candidate["visits"]) else 0
            score = candidate["free_capacity_minutes"] + (120 if city_match else 0)
            candidates.append((score, candidate))
        candidates.sort(key=lambda item: item[0], reverse=True)
        if not candidates:
            return None
        winner = candidates[0][1]
        return {
            "technician_id": winner["technician_id"],
            "technician_name": winner["technician_name"],
            "free_capacity_minutes": winner["free_capacity_minutes"],
        }

    @classmethod
    def build_health_flag(cls, *, technician_context, flag_type, summary, attention_score):
        risk_level = "critical" if attention_score >= 90 else "high" if attention_score >= 75 else "medium"
        return {
            "technician_id": technician_context["technician_id"],
            "schedule_date": technician_context["date"],
            "flag_type": flag_type,
            "summary": summary,
            "attention_score": attention_score,
            "risk_level": risk_level,
            "payload": {"technician": technician_context},
        }

    @classmethod
    def query_marketplace_candidates(cls, *, company_id, visit_payload):
        queryset = TechnicianMatchingRecord.objects.select_related("technician_profile", "technician_profile__user").filter(
            technician_service_request__requester_company_id=company_id
        )
        if visit_payload.get("work_order_public_id"):
            queryset = queryset.filter(technician_service_request__related_service_order__public_id=visit_payload["work_order_public_id"])
        else:
            queryset = queryset.filter(
                Q(technician_service_request__city__iexact=visit_payload.get("city", ""))
                | Q(technician_service_request__state__iexact=visit_payload.get("state", ""))
            )
        return [
            {
                "technician_id": item.technician_profile.user_id,
                "technician_name": item.technician_profile.display_name,
                "match_score": float(item.match_score or 0),
                "ranking_position": item.ranking_position,
            }
            for item in queryset.order_by("ranking_position", "-match_score")[:3]
        ]

    @staticmethod
    def log_signal(*, event_type, technician_context, payload):
        SystemEventService.log_system_event(
            event_type=event_type,
            source_module="ai_agents_center",
            message="Scheduling intelligence signal detected.",
            entity_type="technician",
            entity_id=str(technician_context["technician_id"]),
            payload={"date": technician_context["date"], **payload},
        )

    @staticmethod
    def _build_evidence(technician_context):
        return "; ".join(
            [
                f"visitas: {technician_context['visit_count']}",
                f"duracao: {SchedulingOptimizationService._format_minutes(technician_context['scheduled_minutes'])}",
                f"deslocamento: {SchedulingOptimizationService._format_minutes(technician_context['travel_minutes'])}",
                f"capacidade: {SchedulingOptimizationService._format_minutes(technician_context['capacity_minutes'])}",
                f"conflitos: {len(technician_context['conflicts'])}",
                f"riscos SLA: {len(technician_context['sla_risk_visits'])}",
            ]
        )

    @staticmethod
    def _format_minutes(minutes):
        hours = minutes // 60
        remainder = minutes % 60
        return f"{hours}h{remainder:02d}"

    @staticmethod
    def _severity_rank(value):
        return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(value, 0)

    @staticmethod
    def _priority_rank(value):
        return {"low": 1, "medium": 2, "high": 3, "immediate": 4}.get(value, 0)
