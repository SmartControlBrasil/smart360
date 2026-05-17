from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.ai_agents_center.tools.query_tools import AgentToolbox
from apps.marketplace_technicians.models import TechnicianAssignment, TechnicianMatchingRecord, TechnicianProfile, TechnicianServiceOffer, TechnicianServiceRequest
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import ScheduledVisit, TechnicianAvailabilityWindow


ZERO = Decimal("0.00")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _json_ready(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


@dataclass
class MarketplaceRecommendationDraft:
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
class MarketplaceActionProposalDraft:
    action_type: str
    target_entity: str
    target_entity_id: str
    title: str
    summary: str
    proposed_payload: dict
    priority: str = "high"
    approval_required: bool = True


class MarketplaceAllocationIntelligenceService:
    DEFAULT_THRESHOLDS = {
        "max_urgent_distance_km": Decimal("30.00"),
        "max_high_distance_km": Decimal("60.00"),
        "max_daily_jobs": 6,
        "max_daily_minutes": 600,
        "request_stale_hours": 6,
        "minimum_viability_score": Decimal("55.00"),
        "low_acceptance_penalty_threshold": Decimal("0.50"),
    }

    @classmethod
    def get_thresholds(cls, definition) -> dict:
        config = getattr(definition, "config", {}) or {}
        thresholds = {**cls.DEFAULT_THRESHOLDS, **config.get("heuristics", {})}
        for key in ("max_urgent_distance_km", "max_high_distance_km", "minimum_viability_score", "low_acceptance_penalty_threshold"):
            thresholds[key] = _to_decimal(thresholds[key])
        return thresholds

    @classmethod
    def resolve_scope_from_trigger(cls, *, company, site=None, trigger_reference=""):
        service_request = None
        target_date = None
        category = ""
        if trigger_reference.startswith("request:"):
            service_request = TechnicianServiceRequest.objects.filter(public_id=trigger_reference.split(":", 1)[1], requester_company=company).select_related("related_site", "related_asset", "related_service_order").first()
        elif trigger_reference.startswith("site:"):
            site_code = trigger_reference.split(":", 1)[1]
            from apps.smart_system.models import OperationalSite

            site = OperationalSite.objects.filter(code=site_code, maintenance_client__company=company).first() or site
        elif trigger_reference.startswith("category:"):
            category = trigger_reference.split(":", 1)[1]
        elif trigger_reference.startswith("date:"):
            target_date = datetime.strptime(trigger_reference.split(":", 1)[1], "%Y-%m-%d").date()
        return {"service_request": service_request, "site": site, "category": category, "target_date": target_date}

    @classmethod
    def build_scope_context(
        cls,
        *,
        company,
        site=None,
        service_request=None,
        category="",
        target_date=None,
        trigger_reference="",
        triggered_by=None,
        definition=None,
    ) -> dict:
        if company is None:
            raise ValueError("Marketplace agent requires a company context.")
        thresholds = cls.get_thresholds(definition)
        queryset = TechnicianServiceRequest.objects.filter(
            requester_company=company,
            status__in=[
                TechnicianServiceRequest.Status.OPEN,
                TechnicianServiceRequest.Status.MATCHING,
                TechnicianServiceRequest.Status.OFFERS_RECEIVED,
            ],
        ).select_related("related_site", "related_asset", "related_service_order", "requester_company")
        if site is not None:
            queryset = queryset.filter(related_site=site)
        if service_request is not None:
            queryset = queryset.filter(pk=service_request.pk)
        if category:
            queryset = queryset.filter(category__iexact=category)
        if target_date is not None:
            queryset = queryset.filter(Q(requested_date__date=target_date) | Q(deadline_at__date=target_date))
        requests = list(queryset.order_by("deadline_at", "-priority", "-created_at")[:25])
        request_contexts = [cls.build_request_context(service_request=item, thresholds=thresholds) for item in requests]
        return {
            "company_id": company.id,
            "company_slug": company.slug,
            "site_id": getattr(site, "id", None),
            "trigger_reference": trigger_reference,
            "triggered_by": getattr(triggered_by, "id", None),
            "thresholds": _json_ready(thresholds),
            "requests": request_contexts,
            "queue_summary": cls.build_queue_summary(request_contexts),
        }

    @classmethod
    def build_request_context(cls, *, service_request, thresholds: dict) -> dict:
        request_date = service_request.requested_date.date() if service_request.requested_date else timezone.localdate()
        matches = list(
            service_request.matching_records.select_related("technician_profile", "technician_profile__user")
            .order_by("ranking_position", "-match_score")[:6]
        )
        offers = list(service_request.offers.select_related("technician_profile").order_by("-created_at")[:5])
        active_assignments = list(
            service_request.assignments.select_related("technician_profile", "technician_profile__user")
            .order_by("-assigned_at")[:5]
        )
        candidates = [cls.build_candidate_context(record=record, service_request=service_request, target_date=request_date, thresholds=thresholds) for record in matches]
        return _json_ready(
            {
                "service_request_id": service_request.id,
                "service_request_public_id": str(service_request.public_id),
                "title": service_request.title,
                "category": service_request.category,
                "priority": service_request.priority,
                "status": service_request.status,
                "city": service_request.city,
                "state": service_request.state,
                "site_id": service_request.related_site_id,
                "site_name": getattr(service_request.related_site, "name", ""),
                "requested_date": service_request.requested_date.isoformat() if service_request.requested_date else "",
                "deadline_at": service_request.deadline_at.isoformat() if service_request.deadline_at else "",
                "sla_hours_remaining": cls._sla_hours_remaining(service_request),
                "open_hours": cls._request_open_hours(service_request),
                "offers_count": len(offers),
                "active_assignments_count": len(
                    [item for item in active_assignments if item.assignment_status in {TechnicianAssignment.AssignmentStatus.ASSIGNED, TechnicianAssignment.AssignmentStatus.ACCEPTED, TechnicianAssignment.AssignmentStatus.IN_PROGRESS}]
                ),
                "has_assignment": bool(active_assignments),
                "candidates": candidates,
            }
        )

    @classmethod
    def build_candidate_context(cls, *, record: TechnicianMatchingRecord, service_request: TechnicianServiceRequest, target_date, thresholds: dict) -> dict:
        profile = record.technician_profile
        user = getattr(profile, "user", None)
        day_visits = list(
            ScheduledVisit.objects.filter(
                company=service_request.requester_company,
                technician=user,
                scheduled_date=target_date,
            ).order_by("route_order", "scheduled_start")
        ) if user else []
        total_minutes = sum((visit.estimated_duration_minutes + visit.estimated_travel_minutes for visit in day_visits), 0)
        schedule_jobs = len(day_visits)
        schedule = AgentToolbox.query_technician_capacity(company=service_request.requester_company, technician=user, target_date=target_date) if user else {"schedule": None, "availability": None}
        smart_availability = schedule.get("availability")
        marketplace_availability = list(
            profile.availabilities.filter(weekday=target_date.isoweekday(), is_available=True)
        )
        assignments = profile.assignments.filter(assignment_status__in=[TechnicianAssignment.AssignmentStatus.ASSIGNED, TechnicianAssignment.AssignmentStatus.ACCEPTED, TechnicianAssignment.AssignmentStatus.IN_PROGRESS])
        acceptance_rate = cls._acceptance_rate(profile)
        distance_km = _to_decimal(record.distance_km)
        viability_penalties = []
        viable = True
        if profile.verification_status != TechnicianProfile.VerificationStatus.APPROVED:
            viable = False
            viability_penalties.append("perfil_nao_verificado")
        if profile.marketplace_status not in {TechnicianProfile.MarketplaceStatus.AVAILABLE, TechnicianProfile.MarketplaceStatus.BUSY}:
            viable = False
            viability_penalties.append("perfil_indisponivel")
        if not marketplace_availability and smart_availability is None:
            viable = False
            viability_penalties.append("sem_janela_disponivel")
        if schedule_jobs >= thresholds["max_daily_jobs"] or total_minutes >= thresholds["max_daily_minutes"]:
            viable = False
            viability_penalties.append("sobrecarga_agenda")
        if service_request.priority == TechnicianServiceRequest.Priority.URGENT and distance_km > thresholds["max_urgent_distance_km"]:
            viable = False
            viability_penalties.append("distancia_incompativel_sla_urgente")
        if service_request.priority == TechnicianServiceRequest.Priority.HIGH and distance_km > thresholds["max_high_distance_km"]:
            viability_penalties.append("distancia_arriscada")
        if acceptance_rate < thresholds["low_acceptance_penalty_threshold"]:
            viability_penalties.append("historico_baixo_aceite")

        viability_score = _to_decimal(record.match_score)
        if "sobrecarga_agenda" in viability_penalties:
            viability_score -= Decimal("25.00")
        if "sem_janela_disponivel" in viability_penalties:
            viability_score -= Decimal("30.00")
        if "distancia_incompativel_sla_urgente" in viability_penalties:
            viability_score -= Decimal("35.00")
        if "distancia_arriscada" in viability_penalties:
            viability_score -= Decimal("15.00")
        if "historico_baixo_aceite" in viability_penalties:
            viability_score -= Decimal("10.00")
        if profile.marketplace_status == TechnicianProfile.MarketplaceStatus.BUSY:
            viability_score -= Decimal("8.00")
        viability_score = max(viability_score, ZERO)
        if viability_score < thresholds["minimum_viability_score"]:
            viable = False
        return {
            "technician_profile_id": profile.id,
            "technician_profile_public_id": str(profile.public_id),
            "technician_name": profile.display_name,
            "technician_user_id": getattr(user, "id", None),
            "match_score": _to_decimal(record.match_score),
            "ranking_position": record.ranking_position,
            "distance_km": distance_km,
            "rating_average": _to_decimal(profile.rating_average),
            "completed_jobs_count": profile.completed_jobs_count,
            "schedule_jobs": schedule_jobs,
            "schedule_minutes": total_minutes,
            "active_assignments": assignments.count(),
            "acceptance_rate": acceptance_rate,
            "viable": viable,
            "viability_score": viability_score.quantize(Decimal("0.01")),
            "viability_penalties": viability_penalties,
            "availability_sources": {
                "marketplace_slots": len(marketplace_availability),
                "smart_schedule_window": bool(smart_availability),
            },
        }

    @classmethod
    def build_queue_summary(cls, request_contexts: list[dict]) -> dict:
        return {
            "total_requests": len(request_contexts),
            "urgent_requests": sum(1 for item in request_contexts if item["priority"] == TechnicianServiceRequest.Priority.URGENT),
            "without_viable_candidate": sum(1 for item in request_contexts if not any(candidate["viable"] for candidate in item["candidates"])),
            "sla_risk_requests": sum(1 for item in request_contexts if _to_decimal(item["sla_hours_remaining"]) <= Decimal("6.00") if item["sla_hours_remaining"] is not None),
        }

    @classmethod
    def analyze_scope(cls, *, context: dict, definition=None):
        thresholds = {**context["thresholds"]}
        thresholds["minimum_viability_score"] = _to_decimal(thresholds["minimum_viability_score"])
        recommendations: list[MarketplaceRecommendationDraft] = []
        proposals: list[MarketplaceActionProposalDraft] = []
        flags: list[dict] = []

        for request_context in context["requests"]:
            candidates = request_context["candidates"]
            if not candidates:
                recommendations.append(
                    MarketplaceRecommendationDraft(
                        recommendation_type="no_viable_candidate_alert",
                        severity="critical",
                        priority="immediate",
                        title=f"Request {request_context['title']} sem candidatos do marketplace",
                        summary="Nenhum candidato foi encontrado pelo matching para a solicitacao em aberto.",
                        explanation="O agente nao recebeu candidatos ranqueados para combinar aderencia tecnica com agenda real.",
                        evidence_summary="Matching vazio para a solicitacao analisada.",
                        suggested_action="Expandir busca regional ou acionar fallback operacional imediato.",
                        attention_score=95,
                        entity_type="technician_service_request",
                        entity_id=request_context["service_request_public_id"],
                        payload=request_context,
                    )
                )
                proposals.append(
                    MarketplaceActionProposalDraft(
                        action_type="activate_marketplace_fallback",
                        target_entity="technician_service_request",
                        target_entity_id=request_context["service_request_public_id"],
                        title=f"Acionar fallback para {request_context['title']}",
                        summary="Solicitacao sem cobertura imediata no marketplace.",
                        proposed_payload=request_context,
                        priority="immediate",
                    )
                )
                flags.append(cls._build_flag(request_context=request_context, summary="Sem candidatos ranqueados para alocacao.", risk_level="critical", attention_score=95))
                SystemEventService.log_system_event(
                    event_type="agent.marketplace.no_candidate.detected",
                    source_module="ai_agents_center",
                    message="Marketplace request without candidate.",
                    payload={"service_request_id": request_context["service_request_id"]},
                )
                continue

            theoretical_top = candidates[0]
            viable_candidates = [candidate for candidate in candidates if candidate["viable"]]
            viable_candidates = sorted(viable_candidates, key=lambda item: (_to_decimal(item["viability_score"]), _to_decimal(item["match_score"])), reverse=True)
            chosen = viable_candidates[0] if viable_candidates else None
            alternatives = viable_candidates[1:3]

            if chosen is None:
                summary = (
                    f"Request {request_context['title']} possui candidatos teóricos, mas nenhum deles e operacionalmente viavel no horizonte atual."
                )
                recommendations.append(
                    MarketplaceRecommendationDraft(
                        recommendation_type="no_viable_candidate_alert",
                        severity="critical",
                        priority="immediate",
                        title=f"Sem candidato viavel para {request_context['title']}",
                        summary=summary,
                        explanation="O agente comparou score de matching com disponibilidade, agenda, carga, distancia e risco de SLA.",
                        evidence_summary=f"Melhor score teorico: {theoretical_top['technician_name']} ({theoretical_top['match_score']}) com restricoes {', '.join(theoretical_top['viability_penalties']) or 'nao informadas'}.",
                        suggested_action="Replanejar janela, redistribuir agenda ou acionar fallback operacional/humano.",
                        attention_score=94,
                        entity_type="technician_service_request",
                        entity_id=request_context["service_request_public_id"],
                        payload={**request_context, "theoretical_top": theoretical_top},
                    )
                )
                proposals.append(
                    MarketplaceActionProposalDraft(
                        action_type="activate_marketplace_fallback",
                        target_entity="technician_service_request",
                        target_entity_id=request_context["service_request_public_id"],
                        title=f"Fallback operacional para {request_context['title']}",
                        summary="Nenhum tecnico atende simultaneamente matching, agenda e SLA da solicitacao.",
                        proposed_payload={**request_context, "theoretical_top": theoretical_top},
                        priority="immediate",
                    )
                )
                flags.append(cls._build_flag(request_context=request_context, summary=summary, risk_level="critical", attention_score=94))
                SystemEventService.log_system_event(
                    event_type="agent.marketplace.no_candidate.detected",
                    source_module="ai_agents_center",
                    message="Marketplace request without viable candidate.",
                    payload={"service_request_id": request_context["service_request_id"]},
                )
                continue

            payload = {
                **request_context,
                "recommended_candidate": chosen,
                "alternative_candidates": alternatives,
                "theoretical_top": theoretical_top,
            }
            recommendations.append(
                MarketplaceRecommendationDraft(
                    recommendation_type="technician_allocation_recommendation",
                    severity="high" if request_context["priority"] in {TechnicianServiceRequest.Priority.HIGH, TechnicianServiceRequest.Priority.URGENT} else "medium",
                    priority="immediate" if request_context["priority"] == TechnicianServiceRequest.Priority.URGENT else "high",
                    title=f"Melhor alocacao para {request_context['title']}",
                    summary=(
                        f"{chosen['technician_name']} e o melhor candidato viavel para a solicitacao, "
                        f"com score de matching {chosen['match_score']} e viabilidade {chosen['viability_score']}."
                    ),
                    explanation="O agente combinou matching tecnico com agenda real, disponibilidade declarada, carga, distancia e pressao de SLA.",
                    evidence_summary=(
                        f"Candidatos comparados: {', '.join(candidate['technician_name'] for candidate in candidates[:3])}. "
                        f"Alternativas: {', '.join(item['technician_name'] for item in alternatives) or 'nenhuma'}."
                    ),
                    suggested_action="Criar assignment para o tecnico recomendado e manter alternativas prontas para contingencia.",
                    attention_score=82 if request_context["priority"] == TechnicianServiceRequest.Priority.URGENT else 68,
                    entity_type="technician_service_request",
                    entity_id=request_context["service_request_public_id"],
                    payload=payload,
                )
            )
            proposals.append(
                MarketplaceActionProposalDraft(
                    action_type="assign_recommended_marketplace_technician",
                    target_entity="technician_service_request",
                    target_entity_id=request_context["service_request_public_id"],
                    title=f"Criar assignment para {chosen['technician_name']}",
                    summary="Alocacao sugerida com melhor equilibrio entre aderencia tecnica, disponibilidade real e SLA.",
                    proposed_payload=payload,
                    priority="high",
                )
            )

            if theoretical_top["technician_profile_id"] != chosen["technician_profile_id"]:
                recommendations.append(
                    MarketplaceRecommendationDraft(
                        recommendation_type="technician_unavailable_conflict",
                        severity="high",
                        priority="high",
                        title=f"Melhor score teorico indisponivel em {request_context['title']}",
                        summary=(
                            f"{theoretical_top['technician_name']} lidera o matching, mas {chosen['technician_name']} foi escolhido por maior viabilidade operacional."
                        ),
                        explanation="O melhor score teorico perdeu devido a indisponibilidade, sobrecarga ou distancia incompatível com o contexto do request.",
                        evidence_summary=f"Restricoes do lider teorico: {', '.join(theoretical_top['viability_penalties']) or 'sem restricoes registradas'}.",
                        suggested_action="Reavaliar o candidato teorico apenas se houver reorganizacao de agenda ou mudanca de janela.",
                        attention_score=74,
                        entity_type="technician_service_request",
                        entity_id=request_context["service_request_public_id"],
                        payload=payload,
                    )
                )
                proposals.append(
                    MarketplaceActionProposalDraft(
                        action_type="reassess_candidate_due_unavailability",
                        target_entity="technician_service_request",
                        target_entity_id=request_context["service_request_public_id"],
                        title=f"Registrar conflito de disponibilidade em {request_context['title']}",
                        summary="O lider teorico nao e viavel no curto prazo; manter alternativa operacional como principal.",
                        proposed_payload=payload,
                        priority="medium",
                    )
                )

            if request_context["sla_hours_remaining"] is not None and _to_decimal(request_context["sla_hours_remaining"]) <= Decimal("6.00"):
                recommendations.append(
                    MarketplaceRecommendationDraft(
                        recommendation_type="sla_allocation_risk",
                        severity="critical" if request_context["priority"] == TechnicianServiceRequest.Priority.URGENT else "high",
                        priority="immediate",
                        title=f"Risco de SLA para {request_context['title']}",
                        summary="A solicitacao esta proxima do vencimento e exige decisao de alocacao imediata.",
                        explanation="O request possui janela curta para resposta e demanda priorizacao operacional do melhor candidato viavel.",
                        evidence_summary=f"SLA restante estimado: {request_context['sla_hours_remaining']}h. Candidato recomendado: {chosen['technician_name']}.",
                        suggested_action="Aprovar assignment imediatamente ou escalar fallback se houver nova indisponibilidade.",
                        attention_score=91,
                        entity_type="technician_service_request",
                        entity_id=request_context["service_request_public_id"],
                        payload=payload,
                    )
                )

            if not alternatives:
                recommendations.append(
                    MarketplaceRecommendationDraft(
                        recommendation_type="marketplace_request_attention",
                        severity="medium",
                        priority="medium",
                        title=f"Baixa redundancia de cobertura para {request_context['title']}",
                        summary="A solicitacao tem tecnico recomendado, mas sem segunda linha forte de contingencia.",
                        explanation="A fila marketplace mostra cobertura estreita para esta combinacao de regiao, especialidade e prazo.",
                        evidence_summary=f"Apenas um candidato viavel foi identificado entre {len(candidates)} analisados.",
                        suggested_action="Monitorar aceite do candidato principal e preparar escalonamento humano se necessario.",
                        attention_score=57,
                        entity_type="technician_service_request",
                        entity_id=request_context["service_request_public_id"],
                        payload=payload,
                    )
                )

            flags.append(
                cls._build_flag(
                    request_context=request_context,
                    summary=f"Request analisado com candidato recomendado {chosen['technician_name']}.",
                    risk_level="high" if request_context["priority"] in {TechnicianServiceRequest.Priority.HIGH, TechnicianServiceRequest.Priority.URGENT} else "medium",
                    attention_score=82 if request_context["priority"] == TechnicianServiceRequest.Priority.URGENT else 68,
                    best_candidate_profile_id=chosen["technician_profile_id"],
                    payload=payload,
                )
            )

        output_summary = (
            f"Marketplace allocation agent analyzed {len(context['requests'])} request(s), "
            f"generating {len(recommendations)} recommendations and {len(proposals)} proposals."
        )
        return recommendations, proposals, flags, output_summary

    @staticmethod
    def _sla_hours_remaining(service_request: TechnicianServiceRequest):
        if not service_request.deadline_at:
            return None
        delta = service_request.deadline_at - timezone.now()
        return round(delta.total_seconds() / 3600, 2)

    @staticmethod
    def _request_open_hours(service_request: TechnicianServiceRequest):
        delta = timezone.now() - service_request.created_at
        return round(delta.total_seconds() / 3600, 2)

    @staticmethod
    def _acceptance_rate(profile: TechnicianProfile) -> Decimal:
        aggregate = profile.assignments.aggregate(
            total=Count("id"),
            accepted=Count("id", filter=Q(assignment_status__in=[TechnicianAssignment.AssignmentStatus.ACCEPTED, TechnicianAssignment.AssignmentStatus.IN_PROGRESS, TechnicianAssignment.AssignmentStatus.COMPLETED])),
        )
        total = aggregate["total"] or 0
        if not total:
            return Decimal("1.00")
        return (Decimal(aggregate["accepted"] or 0) / Decimal(total)).quantize(Decimal("0.01"))

    @staticmethod
    def _build_flag(*, request_context, summary, risk_level, attention_score, best_candidate_profile_id=None, payload=None):
        return {
            "service_request_id": request_context["service_request_id"],
            "service_request_public_id": request_context["service_request_public_id"],
            "site_id": request_context.get("site_id"),
            "summary": summary,
            "risk_level": risk_level,
            "attention_score": attention_score,
            "best_candidate_profile_id": best_candidate_profile_id,
            "payload": _json_ready(payload or request_context),
        }
