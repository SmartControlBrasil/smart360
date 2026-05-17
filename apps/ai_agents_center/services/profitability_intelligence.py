from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from apps.analytics_platform.models import ClientProfitability, ContractProfitability, OperationalMetrics, TechnicianPerformance
from apps.analytics_platform.services.analytics_service import ExecutiveAnalyticsService
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import MaintenanceClient, MaintenanceContract, OperationalSite, ServiceOrder, ServiceQuote


User = get_user_model()
ZERO = Decimal("0.00")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _safe_div(numerator: Decimal, denominator: Decimal) -> Decimal:
    if not denominator:
        return ZERO
    return numerator / denominator


def _percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    if not denominator:
        return ZERO
    return ((_to_decimal(numerator) * Decimal("100")) / _to_decimal(denominator)).quantize(Decimal("0.01"))


def _json_ready(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


@dataclass
class ProfitabilityRecommendationDraft:
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
class ProfitabilityActionProposalDraft:
    action_type: str
    target_entity: str
    target_entity_id: str
    title: str
    summary: str
    proposed_payload: dict
    priority: str = "high"
    approval_required: bool = True


class ProfitabilityIntelligenceService:
    DEFAULT_THRESHOLDS = {
        "minimum_margin_percent": Decimal("12.00"),
        "critical_negative_margin_percent": Decimal("-10.00"),
        "negative_cycles_for_client_alert": 2,
        "cost_to_revenue_alert_ratio": Decimal("1.20"),
        "travel_share_warning": Decimal("0.25"),
        "parts_share_warning": Decimal("0.35"),
        "corrective_mix_warning": Decimal("0.60"),
        "technician_avg_profit_floor": Decimal("0.00"),
        "low_efficiency_vs_team_ratio": Decimal("0.60"),
        "minimum_orders_for_efficiency": 2,
    }

    @classmethod
    def get_thresholds(cls, definition) -> dict:
        config = getattr(definition, "config", {}) or {}
        thresholds = {**cls.DEFAULT_THRESHOLDS, **config.get("heuristics", {})}
        for key in (
            "minimum_margin_percent",
            "critical_negative_margin_percent",
            "cost_to_revenue_alert_ratio",
            "travel_share_warning",
            "parts_share_warning",
            "corrective_mix_warning",
            "technician_avg_profit_floor",
            "low_efficiency_vs_team_ratio",
        ):
            thresholds[key] = _to_decimal(thresholds[key])
        return thresholds

    @classmethod
    def build_scope_context(
        cls,
        *,
        company,
        site=None,
        client=None,
        contract=None,
        technician=None,
        target_date=None,
        trigger_reference="",
        triggered_by=None,
        definition=None,
    ) -> dict:
        if company is None:
            raise ValueError("Profitability agent requires a company context.")

        thresholds = cls.get_thresholds(definition)
        target_date = target_date or timezone.localdate()
        period = ExecutiveAnalyticsService.get_period(reference_date=target_date, period_type=OperationalMetrics.PeriodType.MONTHLY)
        previous_reference = period.start - timedelta(days=1)
        previous_period = ExecutiveAnalyticsService.get_period(
            reference_date=previous_reference,
            period_type=OperationalMetrics.PeriodType.MONTHLY,
        )
        ExecutiveAnalyticsService.refresh_company_snapshots(company=company, reference_date=target_date, period_type=OperationalMetrics.PeriodType.MONTHLY)

        orders_queryset = ServiceOrder.objects.filter(
            client__company=company,
            opened_at__date__gte=period.start,
            opened_at__date__lte=period.end,
        ).select_related("client", "operational_site", "asset", "maintenance_contract", "assigned_to")
        if site is not None:
            orders_queryset = orders_queryset.filter(operational_site=site)
        if client is not None:
            orders_queryset = orders_queryset.filter(client=client)
        if contract is not None:
            orders_queryset = orders_queryset.filter(maintenance_contract=contract)
        if technician is not None:
            orders_queryset = orders_queryset.filter(assigned_to=technician)
        orders = list(orders_queryset.order_by("-opened_at"))
        order_ids = [order.id for order in orders]

        order_revenue_map = ExecutiveAnalyticsService._order_revenue_map(company, period, orders)
        order_cost_map = ExecutiveAnalyticsService._order_cost_map(order_ids)
        labor_cost_map = ExecutiveAnalyticsService._labor_cost_for_orders(order_ids)
        parts_cost_map = ExecutiveAnalyticsService._stock_cost_for_orders(order_ids)
        travel_cost_map = ExecutiveAnalyticsService._travel_cost_for_orders(order_ids)
        quotes = {
            quote.work_order_id: quote
            for quote in ServiceQuote.objects.filter(
                company=company,
                work_order_id__in=order_ids,
                status=ServiceQuote.Status.APPROVED,
            ).select_related("work_order", "asset")
        }

        client_rows = list(
            ClientProfitability.objects.filter(company=company, period_type=period.period_type, period_start=period.start)
            .select_related("client")
            .order_by("margin", "profit")
        )
        contract_rows = list(
            ContractProfitability.objects.filter(company=company, period_type=period.period_type, period_start=period.start)
            .select_related("contract", "contract__client", "contract__operational_site")
            .order_by("margin", "profit")
        )
        previous_client_rows = {
            row.client_id: row
            for row in ClientProfitability.objects.filter(company=company, period_type=previous_period.period_type, period_start=previous_period.start)
        }
        previous_contract_rows = {
            row.contract_id: row
            for row in ContractProfitability.objects.filter(company=company, period_type=previous_period.period_type, period_start=previous_period.start)
        }
        technician_rows = list(
            TechnicianPerformance.objects.filter(company=company, period_type=period.period_type, period_start=period.start)
            .select_related("technician")
            .order_by("profit_generated", "-jobs_completed")
        )
        if technician is not None:
            technician_rows = [row for row in technician_rows if row.technician_id == technician.id]

        if client is not None:
            client_rows = [row for row in client_rows if row.client_id == client.id]
        if contract is not None:
            contract_rows = [row for row in contract_rows if row.contract_id == contract.id]

        client_ids = [row.client_id for row in client_rows]
        contract_ids = [row.contract_id for row in contract_rows]

        client_order_mix = {
            row["client_id"]: row
            for row in orders_queryset.values("client_id").annotate(
                total_orders=Count("id"),
                correctives=Count("id", filter=Q(maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE)),
                preventives=Count("id", filter=Q(maintenance_type=ServiceOrder.MaintenanceType.PREVENTIVE)),
            )
        }
        contract_order_mix = {
            row["maintenance_contract_id"]: row
            for row in orders_queryset.filter(maintenance_contract_id__isnull=False).values("maintenance_contract_id").annotate(
                total_orders=Count("id"),
                correctives=Count("id", filter=Q(maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE)),
                preventives=Count("id", filter=Q(maintenance_type=ServiceOrder.MaintenanceType.PREVENTIVE)),
            )
        }

        work_order_contexts = []
        for order in orders:
            revenue = order_revenue_map.get(order.id, ZERO)
            cost = order_cost_map.get(order.id, ZERO)
            travel_cost = travel_cost_map.get(order.id, ZERO)
            parts_cost = parts_cost_map.get(order.id, ZERO)
            labor_cost = labor_cost_map.get(order.id, ZERO)
            approved_quote = quotes.get(order.id)
            quote_value = _to_decimal(getattr(approved_quote, "total_value", ZERO))
            work_order_contexts.append(
                {
                    "id": order.id,
                    "public_id": str(order.public_id),
                    "order_number": order.order_number,
                    "client_id": order.client_id,
                    "contract_id": order.maintenance_contract_id,
                    "site_id": order.operational_site_id,
                    "technician_id": order.assigned_to_id,
                    "maintenance_type": order.maintenance_type,
                    "priority": order.priority,
                    "revenue": revenue,
                    "cost": cost,
                    "profit": revenue - cost,
                    "margin": _percent(revenue - cost, revenue),
                    "travel_cost": travel_cost,
                    "parts_cost": parts_cost,
                    "labor_cost": labor_cost,
                    "quote_value": quote_value,
                    "quote_gap_percent": _percent(cost - quote_value, quote_value) if quote_value else ZERO,
                }
            )

        site_rows = []
        for site_row in (
            orders_queryset.values("operational_site_id", "operational_site__name", "operational_site__code")
            .annotate(total_orders=Count("id"))
            .order_by("operational_site__name")
        ):
            site_orders = [order for order in work_order_contexts if order["site_id"] == site_row["operational_site_id"]]
            revenue = sum((item["revenue"] for item in site_orders), ZERO)
            travel_cost = sum((item["travel_cost"] for item in site_orders), ZERO)
            total_cost = sum((item["cost"] for item in site_orders), ZERO)
            site_rows.append(
                {
                    "site_id": site_row["operational_site_id"],
                    "site_name": site_row["operational_site__name"],
                    "site_code": site_row["operational_site__code"],
                    "total_orders": site_row["total_orders"],
                    "revenue": revenue,
                    "cost": total_cost,
                    "travel_cost": travel_cost,
                    "travel_share": _safe_div(travel_cost, revenue) if revenue else Decimal("1.00"),
                }
            )
        if site is not None:
            site_rows = [row for row in site_rows if row["site_id"] == site.id]

        current_metrics = OperationalMetrics.objects.filter(
            company=company, period_type=period.period_type, period_start=period.start
        ).first()

        return {
            "company_id": company.id,
            "company_slug": company.slug,
            "site_id": getattr(site, "id", None),
            "client_id": getattr(client, "id", None),
            "contract_id": getattr(contract, "id", None),
            "technician_id": getattr(technician, "id", None),
            "trigger_reference": trigger_reference,
            "triggered_by": getattr(triggered_by, "id", None),
            "period": {"type": period.period_type, "start": period.start.isoformat(), "end": period.end.isoformat()},
            "thresholds": _json_ready(thresholds),
            "current_operational_metrics": _json_ready(
                {
                    "total_work_orders": getattr(current_metrics, "total_work_orders", 0),
                    "total_revenue": getattr(current_metrics, "total_revenue", ZERO),
                    "total_cost": getattr(current_metrics, "total_cost", ZERO),
                    "total_profit": getattr(current_metrics, "total_profit", ZERO),
                    "sla_compliance_rate": getattr(current_metrics, "sla_compliance_rate", ZERO),
                }
            ),
            "client_rows": _json_ready([
                {
                    "client_id": row.client_id,
                    "client_public_id": str(row.client.public_id),
                    "client_name": row.client.display_name,
                    "revenue": row.revenue,
                    "cost": row.cost,
                    "profit": row.profit,
                    "margin": row.margin,
                    "total_work_orders": row.total_work_orders,
                    "total_assets": row.total_assets,
                    "previous_margin": getattr(previous_client_rows.get(row.client_id), "margin", None),
                    "previous_profit": getattr(previous_client_rows.get(row.client_id), "profit", None),
                    "order_mix": client_order_mix.get(row.client_id, {}),
                }
                for row in client_rows
                if row.client_id in client_ids or client is None
            ]),
            "contract_rows": _json_ready([
                {
                    "contract_id": row.contract_id,
                    "contract_public_id": str(row.contract.public_id),
                    "contract_number": row.contract.contract_number,
                    "client_name": row.contract.client.display_name,
                    "site_name": row.contract.operational_site.name if row.contract.operational_site else "",
                    "revenue": row.revenue,
                    "cost": row.cost,
                    "profit": row.profit,
                    "margin": row.margin,
                    "total_work_orders": row.total_work_orders,
                    "total_assets": row.total_assets,
                    "contract_value": row.contract.contract_value,
                    "previous_margin": getattr(previous_contract_rows.get(row.contract_id), "margin", None),
                    "previous_profit": getattr(previous_contract_rows.get(row.contract_id), "profit", None),
                    "order_mix": contract_order_mix.get(row.contract_id, {}),
                }
                for row in contract_rows
                if row.contract_id in contract_ids or contract is None
            ]),
            "technician_rows": _json_ready([
                {
                    "technician_id": row.technician_id,
                    "technician_name": row.technician.display_name or row.technician.email,
                    "profit_generated": row.profit_generated,
                    "jobs_completed": row.jobs_completed,
                    "jobs_in_progress": row.jobs_in_progress,
                    "avg_execution_time": row.avg_execution_time,
                    "total_labor_minutes": row.total_labor_minutes,
                    "avg_profit_per_job": _safe_div(row.profit_generated, Decimal(row.jobs_completed or 1)),
                }
                for row in technician_rows
            ]),
            "site_rows": _json_ready(site_rows),
            "work_orders": _json_ready(work_order_contexts),
        }

    @classmethod
    def analyze_scope(cls, *, context: dict, definition=None):
        thresholds = dict(context["thresholds"])
        for key in (
            "minimum_margin_percent",
            "critical_negative_margin_percent",
            "cost_to_revenue_alert_ratio",
            "travel_share_warning",
            "parts_share_warning",
            "corrective_mix_warning",
            "technician_avg_profit_floor",
            "low_efficiency_vs_team_ratio",
        ):
            thresholds[key] = _to_decimal(thresholds[key])
        recommendations: list[ProfitabilityRecommendationDraft] = []
        proposals: list[ProfitabilityActionProposalDraft] = []
        flags: list[dict] = []
        triggered_rules: list[str] = []

        team_avg_profit = ZERO
        technician_rows = context["technician_rows"]
        if technician_rows:
            team_avg_profit = sum((_to_decimal(row["avg_profit_per_job"]) for row in technician_rows), ZERO) / Decimal(len(technician_rows))

        for row in context["client_rows"]:
            row_profit = _to_decimal(row["profit"])
            row_margin = _to_decimal(row["margin"])
            row_revenue = _to_decimal(row["revenue"])
            row_cost = _to_decimal(row["cost"])
            previous_margin = _to_decimal(row.get("previous_margin"))
            previous_profit = _to_decimal(row.get("previous_profit"))
            negative_sequence = row_profit < 0 and previous_profit < 0
            if row_margin < thresholds["minimum_margin_percent"] or negative_sequence:
                triggered_rules.append("client_margin_alert")
                severity = "critical" if row_margin <= thresholds["critical_negative_margin_percent"] or negative_sequence else "high"
                summary = (
                    f"Cliente {row['client_name']} encerrou o periodo com margem {row_margin}% "
                    f"e lucro {row_profit}, pressionado por custo operacional acima da receita."
                )
                evidence = (
                    f"Receita {row_revenue} versus custo {row_cost}; "
                    f"{row['order_mix'].get('correctives', 0)} corretivas em {row['order_mix'].get('total_orders', row['total_work_orders'])} OS."
                )
                recommendations.append(
                    ProfitabilityRecommendationDraft(
                        recommendation_type="client_margin_alert" if row_profit < 0 else "profitability_watch",
                        severity=severity,
                        priority="immediate" if severity == "critical" else "high",
                        title=f"Cliente {row['client_name']} com erosao de margem",
                        summary=summary,
                        explanation="O agente cruzou receita, custo, mix corretivo/preventivo e historico recente de margem do cliente.",
                        evidence_summary=evidence,
                        suggested_action="Revisar contrato, pricing e desenho operacional do atendimento antes do proximo ciclo.",
                        attention_score=92 if severity == "critical" else 78,
                        entity_type="maintenance_client",
                        entity_id=row["client_public_id"],
                        payload=_json_ready(row),
                    )
                )
                proposals.append(
                    ProfitabilityActionProposalDraft(
                        action_type="review_client_in_management_committee",
                        target_entity="maintenance_client",
                        target_entity_id=row["client_public_id"],
                        title=f"Levar cliente {row['client_name']} para revisao gerencial",
                        summary="Cliente com margem pressionada e necessidade de acao comercial-operacional coordenada.",
                        proposed_payload=_json_ready(row),
                        priority="high",
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="client",
                        target_entity_type="maintenance_client",
                        target_entity_id=row["client_public_id"],
                        display_label=row["client_name"],
                        summary=summary,
                        risk_level="critical" if severity == "critical" else "high",
                        attention_score=92 if severity == "critical" else 78,
                        payload=_json_ready(row),
                        client_id=row["client_id"],
                    )
                )
                # Low-level pattern detection is logged for auditability and dashboard correlation.
                SystemEventService.log_system_event(
                    event_type="agent.profitability.margin_alert.detected",
                    source_module="ai_agents_center",
                    message="Client profitability alert detected.",
                    payload={"rule": "client_margin_alert", "client_id": row["client_id"]},
                )

        for row in context["contract_rows"]:
            row_profit = _to_decimal(row["profit"])
            row_margin = _to_decimal(row["margin"])
            row_cost = _to_decimal(row["cost"])
            row_revenue = _to_decimal(row["revenue"])
            corrective_share = _safe_div(
                Decimal(row["order_mix"].get("correctives", 0)),
                Decimal(row["order_mix"].get("total_orders", row["total_work_orders"]) or 1),
            )
            if row_profit < 0 or row_margin < thresholds["minimum_margin_percent"] or corrective_share >= thresholds["corrective_mix_warning"]:
                triggered_rules.append("contract_profitability_risk")
                severity = "critical" if row_profit < 0 else "high"
                summary = (
                    f"Contrato {row['contract_number']} opera com margem {row_margin}% "
                    f"e custo {row_cost} para receita {row_revenue}."
                )
                evidence = (
                    f"Cliente {row['client_name']}; {row['order_mix'].get('correctives', 0)} corretivas, "
                    f"{row['order_mix'].get('preventives', 0)} preventivas; valor contratual {row['contract_value']}."
                )
                rec_type = "contract_profitability_risk" if row_profit < 0 else "scope_review_recommendation"
                recommendations.append(
                    ProfitabilityRecommendationDraft(
                        recommendation_type=rec_type,
                        severity=severity,
                        priority="immediate" if severity == "critical" else "high",
                        title=f"Contrato {row['contract_number']} com risco de rentabilidade",
                        summary=summary,
                        explanation="O agente comparou custo real de execucao, valor contratual, mix de corretivas e historico recente do contrato.",
                        evidence_summary=evidence,
                        suggested_action="Renegociar preco, revisar escopo coberto ou elevar cobertura preventiva para reduzir corretivas caras.",
                        attention_score=90 if severity == "critical" else 76,
                        entity_type="maintenance_contract",
                        entity_id=row["contract_public_id"],
                        payload=_json_ready({**row, "corrective_share": str(corrective_share)}),
                    )
                )
                proposals.append(
                    ProfitabilityActionProposalDraft(
                        action_type="suggest_contract_repricing",
                        target_entity="maintenance_contract",
                        target_entity_id=row["contract_public_id"],
                        title=f"Propor revisao comercial do contrato {row['contract_number']}",
                        summary="Contrato com margem abaixo do saudavel e necessidade de ajuste comercial ou operacional.",
                        proposed_payload=_json_ready({**row, "corrective_share": str(corrective_share)}),
                        priority="high",
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="contract",
                        target_entity_type="maintenance_contract",
                        target_entity_id=row["contract_public_id"],
                        display_label=row["contract_number"],
                        summary=summary,
                        risk_level="critical" if severity == "critical" else "high",
                        attention_score=90 if severity == "critical" else 76,
                        payload=_json_ready({**row, "corrective_share": str(corrective_share)}),
                        contract_id=row["contract_id"],
                    )
                )

        for row in context["work_orders"]:
            revenue = _to_decimal(row["revenue"])
            if revenue <= ZERO:
                continue
            row_cost = _to_decimal(row["cost"])
            row_profit = _to_decimal(row["profit"])
            row_labor_cost = _to_decimal(row["labor_cost"])
            row_parts_cost = _to_decimal(row["parts_cost"])
            row_travel_cost = _to_decimal(row["travel_cost"])
            row_quote_value = _to_decimal(row["quote_value"])
            quote_gap = _to_decimal(row["quote_gap_percent"])
            cost_ratio = _safe_div(row_cost, revenue)
            parts_share = _safe_div(row_parts_cost, row_cost) if row_cost else ZERO
            travel_share = _safe_div(row_travel_cost, revenue)
            if cost_ratio >= thresholds["cost_to_revenue_alert_ratio"] or quote_gap >= Decimal("20.00"):
                triggered_rules.append("excessive_service_cost")
                summary = (
                    f"OS {row['order_number']} consumiu custo {row_cost} para receita {revenue}, "
                    f"com margem {_to_decimal(row['margin'])}%."
                )
                evidence = (
                    f"Mao de obra {row_labor_cost}, pecas {row_parts_cost}, deslocamento {row_travel_cost}; "
                    f"orcado/aprovado {row_quote_value}."
                )
                recommendations.append(
                    ProfitabilityRecommendationDraft(
                        recommendation_type="excessive_service_cost",
                        severity="high" if row_profit < 0 else "medium",
                        priority="high",
                        title=f"Atendimento {row['order_number']} com custo desproporcional",
                        summary=summary,
                        explanation="O agente confrontou receita atribuida, custo executado e desvio frente ao orcamento aprovado.",
                        evidence_summary=evidence,
                        suggested_action="Revisar formacao de preco, consumo de pecas e necessidade de corretiva estrutural/preventiva reforcada.",
                        attention_score=74 if row_profit < 0 else 62,
                        entity_type="service_order",
                        entity_id=row["public_id"],
                        payload=_json_ready({
                            **row,
                            "cost_ratio": str(cost_ratio),
                            "parts_share": str(parts_share),
                            "travel_share": str(travel_share),
                        }),
                    )
                )
                proposals.append(
                    ProfitabilityActionProposalDraft(
                        action_type="prioritize_preventive_to_reduce_corrective_cost",
                        target_entity="service_order",
                        target_entity_id=row["public_id"],
                        title=f"Revisar estrategia de custo para {row['order_number']}",
                        summary="Atendimento com consumo acima do previsto e necessidade de acao para proteger margem.",
                        proposed_payload=_json_ready({
                            **row,
                            "cost_ratio": str(cost_ratio),
                            "parts_share": str(parts_share),
                            "travel_share": str(travel_share),
                        }),
                        priority="high",
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="work_order",
                        target_entity_type="service_order",
                        target_entity_id=row["public_id"],
                        display_label=row["order_number"],
                        summary=summary,
                        risk_level="high" if row_profit < 0 else "medium",
                        attention_score=74 if row_profit < 0 else 62,
                        payload=_json_ready({
                            **row,
                            "cost_ratio": str(cost_ratio),
                            "parts_share": str(parts_share),
                            "travel_share": str(travel_share),
                        }),
                    )
                )

        for row in context["site_rows"]:
            row_revenue = _to_decimal(row["revenue"])
            row_travel_cost = _to_decimal(row["travel_cost"])
            row_travel_share = _to_decimal(row["travel_share"])
            if row_revenue <= ZERO:
                continue
            if row_travel_share >= thresholds["travel_share_warning"]:
                triggered_rules.append("route_margin_erosion")
                summary = (
                    f"Regiao/site {row['site_name']} consome deslocamento acima do saudavel para o faturamento do periodo."
                )
                evidence = (
                    f"Deslocamento estimado {row_travel_cost} para receita {row_revenue} "
                    f"em {row['total_orders']} atendimentos."
                )
                recommendations.append(
                    ProfitabilityRecommendationDraft(
                        recommendation_type="route_margin_erosion",
                        severity="high" if row_travel_share >= Decimal("0.40") else "medium",
                        priority="high",
                        title=f"Deslocamento corroendo margem em {row['site_name']}",
                        summary=summary,
                        explanation="O agente agregou custo de deslocamento e receita por regiao/site operacional.",
                        evidence_summary=evidence,
                        suggested_action="Consolidar visitas, revisar densidade de agenda e considerar redimensionamento regional.",
                        attention_score=72 if row_travel_share >= Decimal("0.40") else 58,
                        entity_type="operational_site",
                        entity_id=str(row["site_id"]),
                        payload=_json_ready({**row, "travel_share_percent": str((row_travel_share * Decimal('100')).quantize(Decimal('0.01')))}),
                    )
                )
                proposals.append(
                    ProfitabilityActionProposalDraft(
                        action_type="suggest_route_consolidation",
                        target_entity="operational_site",
                        target_entity_id=str(row["site_id"]),
                        title=f"Consolidar operacao da regiao {row['site_name']}",
                        summary="Deslocamento elevado esta reduzindo a margem operacional da regiao.",
                        proposed_payload=_json_ready(row),
                        priority="medium",
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="site",
                        target_entity_type="operational_site",
                        target_entity_id=str(row["site_id"]),
                        display_label=row["site_name"],
                        summary=summary,
                        risk_level="high" if row_travel_share >= Decimal("0.40") else "medium",
                        attention_score=72 if row_travel_share >= Decimal("0.40") else 58,
                        payload=_json_ready(row),
                        site_id=row["site_id"],
                    )
                )

        for row in technician_rows:
            if row["jobs_completed"] < thresholds["minimum_orders_for_efficiency"]:
                continue
            avg_profit_per_job = _to_decimal(row["avg_profit_per_job"])
            profit_generated = _to_decimal(row["profit_generated"])
            below_floor = avg_profit_per_job < thresholds["technician_avg_profit_floor"]
            below_team = team_avg_profit > ZERO and avg_profit_per_job <= (team_avg_profit * thresholds["low_efficiency_vs_team_ratio"])
            if below_floor or below_team:
                triggered_rules.append("technician_efficiency_attention")
                summary = (
                    f"{row['technician_name']} concluiu {row['jobs_completed']} OS, mas com profit medio por atendimento abaixo do esperado."
                )
                evidence = (
                    f"Profit gerado {profit_generated}; media por OS {avg_profit_per_job}; "
                    f"referencia do time {team_avg_profit.quantize(Decimal('0.01')) if team_avg_profit else ZERO}."
                )
                recommendations.append(
                    ProfitabilityRecommendationDraft(
                        recommendation_type="technician_efficiency_attention",
                        severity="medium",
                        priority="medium",
                        title=f"Eficiência econômica abaixo do esperado para {row['technician_name']}",
                        summary=summary,
                        explanation="O agente comparou profit gerado, quantidade de OS e rentabilidade media por atendimento do tecnico com a base comparavel.",
                        evidence_summary=evidence,
                        suggested_action="Revisar combinacao de agenda, deslocamento e retrabalho antes de escalar novos atendimentos similares.",
                        attention_score=55,
                        entity_type="user",
                        entity_id=str(row["technician_id"]),
                        payload=_json_ready({**row, "team_avg_profit_per_job": str(team_avg_profit.quantize(Decimal("0.01")) if team_avg_profit else ZERO)}),
                        requires_human_approval=False,
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="technician",
                        target_entity_type="user",
                        target_entity_id=str(row["technician_id"]),
                        display_label=row["technician_name"],
                        summary=summary,
                        risk_level="medium",
                        attention_score=55,
                        payload=_json_ready({**row, "team_avg_profit_per_job": str(team_avg_profit.quantize(Decimal("0.01")) if team_avg_profit else ZERO)}),
                        technician_id=row["technician_id"],
                    )
                )

        output_summary = (
            f"Profitability agent analyzed {len(context['client_rows'])} clients, "
            f"{len(context['contract_rows'])} contracts, {len(context['work_orders'])} work orders and "
            f"{len(context['site_rows'])} operational regions, generating {len(recommendations)} recommendations."
        )
        return recommendations, proposals, flags, output_summary

    @staticmethod
    def _build_flag(
        *,
        focus_type: str,
        target_entity_type: str,
        target_entity_id: str,
        display_label: str,
        summary: str,
        risk_level: str,
        attention_score: int,
        payload: dict,
        site_id=None,
        client_id=None,
        contract_id=None,
        technician_id=None,
    ) -> dict:
        return {
            "focus_type": focus_type,
            "target_entity_type": target_entity_type,
            "target_entity_id": target_entity_id,
            "display_label": display_label,
            "summary": summary,
            "risk_level": risk_level,
            "attention_score": attention_score,
            "payload": _json_ready(payload),
            "site_id": site_id,
            "client_id": client_id,
            "contract_id": contract_id,
            "technician_id": technician_id,
        }

    @classmethod
    def resolve_scope_from_trigger(cls, *, company, site=None, trigger_reference=""):
        client = None
        contract = None
        technician = None
        target_date = None
        if trigger_reference.startswith("client:"):
            client = MaintenanceClient.objects.filter(public_id=trigger_reference.split(":", 1)[1], company=company).first()
        elif trigger_reference.startswith("contract:"):
            contract = MaintenanceContract.objects.filter(public_id=trigger_reference.split(":", 1)[1], company=company).first()
        elif trigger_reference.startswith("technician:"):
            _, raw_technician, _, raw_date = (trigger_reference.split(":", 3) + ["", "", "", ""])[:4]
            technician = User.objects.filter(pk=raw_technician).first()
            if raw_date:
                target_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        elif trigger_reference.startswith("site:"):
            _, site_code = trigger_reference.split(":", 1)
            site = OperationalSite.objects.filter(code=site_code, maintenance_client__company=company).first() or site
        elif trigger_reference.startswith("date:"):
            target_date = datetime.strptime(trigger_reference.split(":", 1)[1], "%Y-%m-%d").date()
        return {"site": site, "client": client, "contract": contract, "technician": technician, "target_date": target_date}
