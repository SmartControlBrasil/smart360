from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone

from apps.analytics_platform.models import ClientProfitability, ContractProfitability, OperationalMetrics, TechnicianPerformance
from apps.analytics_platform.services.analytics_service import ExecutiveAnalyticsService
from apps.marketplace_technicians.models import TechnicianAssignment, TechnicianServiceOffer, TechnicianServiceRequest
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import Asset, FailureEvent, MaintenanceClient, MaintenanceContract, OperationalSite, Part, ScheduledVisit, ServiceOrder, StockMovement


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


def _percent_change(current, baseline) -> Decimal:
    current_decimal = _to_decimal(current)
    baseline_decimal = _to_decimal(baseline)
    if baseline_decimal <= ZERO:
        if current_decimal <= ZERO:
            return ZERO
        return Decimal("999.00")
    return (((current_decimal - baseline_decimal) * Decimal("100")) / baseline_decimal).quantize(Decimal("0.01"))


def _json_ready(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


@dataclass
class AnomalyRecommendationDraft:
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
class AnomalyActionProposalDraft:
    action_type: str
    target_entity: str
    target_entity_id: str
    title: str
    summary: str
    proposed_payload: dict
    priority: str = "high"
    approval_required: bool = True


class AnomalyDetectionIntelligenceService:
    DEFAULT_THRESHOLDS = {
        "recent_window_days": 7,
        "baseline_window_days": 28,
        "failure_spike_multiplier": Decimal("1.80"),
        "minimum_failure_spike": 3,
        "backlog_growth_multiplier": Decimal("1.70"),
        "minimum_backlog_open": 6,
        "sla_drop_points": Decimal("15.00"),
        "critical_sla_rate": Decimal("75.00"),
        "parts_spike_multiplier": Decimal("2.50"),
        "minimum_parts_cost": Decimal("300.00"),
        "technician_drop_ratio": Decimal("0.50"),
        "minimum_assignment_cancellations": 3,
        "marketplace_acceptance_drop_points": Decimal("20.00"),
        "marketplace_unassigned_threshold": 3,
        "contract_margin_shift_points": Decimal("15.00"),
    }
    OPEN_BACKLOG_STATUSES = [
        ServiceOrder.Status.OPEN,
        ServiceOrder.Status.SCHEDULED,
        ServiceOrder.Status.IN_PROGRESS,
        ServiceOrder.Status.WAITING_PARTS,
        ServiceOrder.Status.WAITING_QUOTE_APPROVAL,
        ServiceOrder.Status.ON_HOLD,
    ]

    @classmethod
    def get_thresholds(cls, definition) -> dict:
        config = getattr(definition, "config", {}) or {}
        thresholds = {**cls.DEFAULT_THRESHOLDS, **config.get("heuristics", {})}
        for key in (
            "failure_spike_multiplier",
            "backlog_growth_multiplier",
            "sla_drop_points",
            "critical_sla_rate",
            "parts_spike_multiplier",
            "minimum_parts_cost",
            "technician_drop_ratio",
            "marketplace_acceptance_drop_points",
            "contract_margin_shift_points",
        ):
            thresholds[key] = _to_decimal(thresholds[key])
        return thresholds

    @classmethod
    def resolve_scope_from_trigger(cls, *, company, site=None, trigger_reference=""):
        scope = {
            "site": site,
            "asset": None,
            "client": None,
            "contract": None,
            "technician": None,
            "part": None,
            "target_date": None,
        }
        if not trigger_reference or company is None:
            return scope
        if trigger_reference.startswith("asset:"):
            scope["asset"] = Asset.objects.filter(
                public_id=trigger_reference.split(":", 1)[1],
                operational_site__maintenance_client__company=company,
            ).select_related("operational_site", "category").first()
        elif trigger_reference.startswith("site:"):
            site_token = trigger_reference.split(":", 1)[1]
            scope["site"] = OperationalSite.objects.filter(
                Q(code=site_token) | Q(public_id=site_token),
                maintenance_client__company=company,
            ).select_related("maintenance_client").first() or site
        elif trigger_reference.startswith("client:"):
            scope["client"] = MaintenanceClient.objects.filter(public_id=trigger_reference.split(":", 1)[1], company=company).first()
        elif trigger_reference.startswith("contract:"):
            scope["contract"] = MaintenanceContract.objects.filter(public_id=trigger_reference.split(":", 1)[1], company=company).select_related("client", "operational_site").first()
        elif trigger_reference.startswith("technician:"):
            try:
                technician_id = int(trigger_reference.split(":", 1)[1].split(":")[0])
            except (TypeError, ValueError):
                technician_id = None
            if technician_id:
                from django.contrib.auth import get_user_model

                scope["technician"] = get_user_model().objects.filter(id=technician_id).first()
        elif trigger_reference.startswith("part:"):
            scope["part"] = Part.objects.filter(public_id=trigger_reference.split(":", 1)[1], company=company).first()
        elif trigger_reference.startswith("date:"):
            scope["target_date"] = datetime.strptime(trigger_reference.split(":", 1)[1], "%Y-%m-%d").date()
        return scope

    @classmethod
    def build_scope_context(
        cls,
        *,
        company,
        site=None,
        asset=None,
        client=None,
        contract=None,
        technician=None,
        part=None,
        target_date=None,
        trigger_reference="",
        triggered_by=None,
        definition=None,
    ) -> dict:
        if company is None:
            raise ValueError("Anomaly agent requires a company context.")

        thresholds = cls.get_thresholds(definition)
        target_date = target_date or timezone.localdate()
        recent_end = target_date
        recent_start = recent_end - timedelta(days=thresholds["recent_window_days"] - 1)
        baseline_end = recent_start - timedelta(days=1)
        baseline_start = baseline_end - timedelta(days=thresholds["baseline_window_days"] - 1)

        ExecutiveAnalyticsService.refresh_company_snapshots(
            company=company,
            reference_date=target_date,
            period_type=OperationalMetrics.PeriodType.MONTHLY,
        )

        context = {
            "company_id": company.id,
            "company_slug": company.slug,
            "site_id": getattr(site, "id", None),
            "trigger_reference": trigger_reference,
            "triggered_by": getattr(triggered_by, "id", None),
            "thresholds": _json_ready(thresholds),
            "periods": {
                "recent_start": recent_start.isoformat(),
                "recent_end": recent_end.isoformat(),
                "baseline_start": baseline_start.isoformat(),
                "baseline_end": baseline_end.isoformat(),
            },
            "assets": cls.build_asset_contexts(
                company=company,
                site=site,
                asset=asset,
                client=client,
                contract=contract,
                recent_start=recent_start,
                recent_end=recent_end,
                baseline_start=baseline_start,
                baseline_end=baseline_end,
            ),
            "sites": cls.build_site_contexts(
                company=company,
                site=site,
                recent_start=recent_start,
                recent_end=recent_end,
                baseline_start=baseline_start,
                baseline_end=baseline_end,
            ),
            "parts": cls.build_part_contexts(
                company=company,
                site=site,
                part=part,
                recent_start=recent_start,
                recent_end=recent_end,
                baseline_start=baseline_start,
                baseline_end=baseline_end,
            ),
            "technicians": cls.build_technician_contexts(
                company=company,
                technician=technician,
                site=site,
                target_date=target_date,
            ),
            "contracts": cls.build_contract_contexts(company=company, contract=contract, client=client, target_date=target_date),
            "clients": cls.build_client_contexts(company=company, client=client, target_date=target_date),
            "marketplace": cls.build_marketplace_context(
                company=company,
                site=site,
                recent_start=recent_start,
                recent_end=recent_end,
                baseline_start=baseline_start,
                baseline_end=baseline_end,
            ),
        }
        return _json_ready(context)

    @classmethod
    def build_asset_contexts(cls, *, company, site=None, asset=None, client=None, contract=None, recent_start, recent_end, baseline_start, baseline_end):
        assets_queryset = Asset.objects.filter(operational_site__maintenance_client__company=company).select_related("operational_site", "category")
        if site is not None:
            assets_queryset = assets_queryset.filter(operational_site=site)
        if asset is not None:
            assets_queryset = assets_queryset.filter(pk=asset.pk)
        if client is not None:
            assets_queryset = assets_queryset.filter(operational_site__maintenance_client=client)
        if contract is not None:
            assets_queryset = assets_queryset.filter(service_orders__maintenance_contract=contract).distinct()

        assets = []
        for item in assets_queryset[:25]:
            recent_failures = item.failure_events.filter(detected_at__date__gte=recent_start, detected_at__date__lte=recent_end).count()
            baseline_failures_total = item.failure_events.filter(detected_at__date__gte=baseline_start, detected_at__date__lte=baseline_end).count()
            recent_correctives = item.service_orders.filter(
                opened_at__date__gte=recent_start,
                opened_at__date__lte=recent_end,
                maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            ).count()
            baseline_correctives_total = item.service_orders.filter(
                opened_at__date__gte=baseline_start,
                opened_at__date__lte=baseline_end,
                maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            ).count()
            if recent_failures == 0 and baseline_failures_total == 0 and recent_correctives == 0 and baseline_correctives_total == 0 and asset is None:
                continue
            assets.append(
                {
                    "asset_id": item.id,
                    "asset_public_id": str(item.public_id),
                    "asset_tag": item.asset_tag,
                    "name": item.name,
                    "site_id": item.operational_site_id,
                    "site_name": item.operational_site.name,
                    "criticality": item.criticality,
                    "recent_failures": recent_failures,
                    "baseline_failures_avg": _safe_div(_to_decimal(baseline_failures_total), Decimal("4")).quantize(Decimal("0.01")),
                    "recent_correctives": recent_correctives,
                    "baseline_correctives_avg": _safe_div(_to_decimal(baseline_correctives_total), Decimal("4")).quantize(Decimal("0.01")),
                }
            )
        return assets

    @classmethod
    def build_site_contexts(cls, *, company, site=None, recent_start, recent_end, baseline_start, baseline_end):
        sites_queryset = OperationalSite.objects.filter(maintenance_client__company=company).select_related("maintenance_client")
        if site is not None:
            sites_queryset = sites_queryset.filter(pk=site.pk)
        sites = []
        for item in sites_queryset[:25]:
            recent_failures = FailureEvent.objects.filter(
                asset__operational_site=item,
                detected_at__date__gte=recent_start,
                detected_at__date__lte=recent_end,
            ).count()
            baseline_failures_total = FailureEvent.objects.filter(
                asset__operational_site=item,
                detected_at__date__gte=baseline_start,
                detected_at__date__lte=baseline_end,
            ).count()
            recent_backlog = ServiceOrder.objects.filter(
                operational_site=item,
                status__in=cls.OPEN_BACKLOG_STATUSES,
                opened_at__date__gte=recent_start,
                opened_at__date__lte=recent_end,
            ).count()
            current_open_backlog = ServiceOrder.objects.filter(
                operational_site=item,
                status__in=cls.OPEN_BACKLOG_STATUSES,
            ).count()
            baseline_backlog_total = ServiceOrder.objects.filter(
                operational_site=item,
                status__in=cls.OPEN_BACKLOG_STATUSES,
                opened_at__date__gte=baseline_start,
                opened_at__date__lte=baseline_end,
            ).count()
            recent_orders = list(
                ServiceOrder.objects.filter(
                    operational_site=item,
                    opened_at__date__gte=recent_start,
                    opened_at__date__lte=recent_end,
                )
            )
            baseline_orders = list(
                ServiceOrder.objects.filter(
                    operational_site=item,
                    opened_at__date__gte=baseline_start,
                    opened_at__date__lte=baseline_end,
                )
            )
            recent_sla_rate = cls._calculate_sla_rate(recent_orders)
            baseline_sla_rate = cls._calculate_sla_rate(baseline_orders)
            recent_correctives = len([order for order in recent_orders if order.maintenance_type == ServiceOrder.MaintenanceType.CORRECTIVE])
            baseline_correctives_avg = _safe_div(
                _to_decimal(
                    len([order for order in baseline_orders if order.maintenance_type == ServiceOrder.MaintenanceType.CORRECTIVE])
                ),
                Decimal("4"),
            ).quantize(Decimal("0.01"))
            if (
                recent_failures == 0
                and baseline_failures_total == 0
                and current_open_backlog == 0
                and recent_sla_rate == ZERO
                and site is None
            ):
                continue
            sites.append(
                {
                    "site_id": item.id,
                    "site_public_id": str(item.public_id),
                    "site_code": item.code,
                    "site_name": item.name,
                    "client_id": item.maintenance_client_id,
                    "recent_failures": recent_failures,
                    "baseline_failures_avg": _safe_div(_to_decimal(baseline_failures_total), Decimal("4")).quantize(Decimal("0.01")),
                    "recent_backlog": recent_backlog,
                    "current_open_backlog": current_open_backlog,
                    "baseline_backlog_avg": _safe_div(_to_decimal(baseline_backlog_total), Decimal("4")).quantize(Decimal("0.01")),
                    "recent_sla_rate": recent_sla_rate,
                    "baseline_sla_rate": baseline_sla_rate,
                    "recent_correctives": recent_correctives,
                    "baseline_correctives_avg": baseline_correctives_avg,
                }
            )
        return sites

    @classmethod
    def build_part_contexts(cls, *, company, site=None, part=None, recent_start, recent_end, baseline_start, baseline_end):
        part_queryset = Part.objects.filter(company=company)
        if site is not None:
            part_queryset = part_queryset.filter(Q(operational_site=site) | Q(operational_site__isnull=True))
        if part is not None:
            part_queryset = part_queryset.filter(pk=part.pk)
        contexts = []
        for item in part_queryset[:25]:
            recent_movements = list(
                item.stock_movements.filter(
                    company=company,
                    movement_type__in=[StockMovement.MovementType.OUTBOUND, StockMovement.MovementType.RESERVED],
                    occurred_at__date__gte=recent_start,
                    occurred_at__date__lte=recent_end,
                )
            )
            baseline_movements = list(
                item.stock_movements.filter(
                    company=company,
                    movement_type__in=[StockMovement.MovementType.OUTBOUND, StockMovement.MovementType.RESERVED],
                    occurred_at__date__gte=baseline_start,
                    occurred_at__date__lte=baseline_end,
                )
            )
            recent_quantity = sum((_to_decimal(movement.quantity) for movement in recent_movements), ZERO)
            baseline_quantity_avg = _safe_div(sum((_to_decimal(movement.quantity) for movement in baseline_movements), ZERO), Decimal("4")).quantize(Decimal("0.01"))
            recent_cost = (recent_quantity * _to_decimal(item.unit_cost)).quantize(Decimal("0.01"))
            baseline_cost_avg = (baseline_quantity_avg * _to_decimal(item.unit_cost)).quantize(Decimal("0.01"))
            if recent_quantity == ZERO and baseline_quantity_avg == ZERO and part is None:
                continue
            contexts.append(
                {
                    "part_id": item.id,
                    "part_public_id": str(item.public_id),
                    "part_code": item.code,
                    "part_name": item.name,
                    "site_id": item.operational_site_id,
                    "recent_quantity": recent_quantity.quantize(Decimal("0.01")),
                    "baseline_quantity_avg": baseline_quantity_avg,
                    "recent_cost": recent_cost,
                    "baseline_cost_avg": baseline_cost_avg,
                }
            )
        return contexts

    @classmethod
    def build_technician_contexts(cls, *, company, technician=None, site=None, target_date=None):
        period = ExecutiveAnalyticsService.get_period(reference_date=target_date, period_type=OperationalMetrics.PeriodType.MONTHLY)
        previous_period = ExecutiveAnalyticsService.get_period(reference_date=period.start - timedelta(days=1), period_type=OperationalMetrics.PeriodType.MONTHLY)
        queryset = TechnicianPerformance.objects.filter(company=company, period_type=period.period_type, period_start=period.start).select_related("technician")
        previous_rows = {
            row.technician_id: row
            for row in TechnicianPerformance.objects.filter(company=company, period_type=previous_period.period_type, period_start=previous_period.start)
        }
        if technician is not None:
            queryset = queryset.filter(technician=technician)
        contexts = []
        for row in queryset[:25]:
            previous = previous_rows.get(row.technician_id)
            recent_conflicts = ScheduledVisit.objects.filter(
                company=company,
                technician=row.technician,
                scheduled_date__gte=target_date - timedelta(days=6),
                scheduled_date__lte=target_date,
            ).exclude(conflict_flags=[]).count() if target_date else 0
            if site is not None:
                recent_conflicts = ScheduledVisit.objects.filter(
                    company=company,
                    operational_site=site,
                    technician=row.technician,
                    scheduled_date__gte=target_date - timedelta(days=6),
                    scheduled_date__lte=target_date,
                ).exclude(conflict_flags=[]).count() if target_date else 0
            contexts.append(
                {
                    "technician_id": row.technician_id,
                    "technician_name": row.technician.display_name or row.technician.email,
                    "jobs_completed": row.jobs_completed,
                    "previous_jobs_completed": getattr(previous, "jobs_completed", 0),
                    "avg_execution_time": _to_decimal(row.avg_execution_time),
                    "previous_avg_execution_time": _to_decimal(getattr(previous, "avg_execution_time", ZERO)),
                    "profit_generated": _to_decimal(row.profit_generated),
                    "previous_profit_generated": _to_decimal(getattr(previous, "profit_generated", ZERO)),
                    "recent_conflicts": recent_conflicts,
                }
            )
        return contexts

    @classmethod
    def build_contract_contexts(cls, *, company, contract=None, client=None, target_date=None):
        period = ExecutiveAnalyticsService.get_period(reference_date=target_date, period_type=OperationalMetrics.PeriodType.MONTHLY)
        previous_period = ExecutiveAnalyticsService.get_period(reference_date=period.start - timedelta(days=1), period_type=OperationalMetrics.PeriodType.MONTHLY)
        queryset = ContractProfitability.objects.filter(company=company, period_type=period.period_type, period_start=period.start).select_related("contract", "contract__client", "contract__operational_site")
        if contract is not None:
            queryset = queryset.filter(contract=contract)
        if client is not None:
            queryset = queryset.filter(contract__client=client)
        previous_rows = {
            row.contract_id: row
            for row in ContractProfitability.objects.filter(company=company, period_type=previous_period.period_type, period_start=previous_period.start)
        }
        return [
            {
                "contract_id": row.contract_id,
                "contract_public_id": str(row.contract.public_id),
                "contract_number": row.contract.contract_number,
                "client_id": row.contract.client_id,
                "site_id": row.contract.operational_site_id,
                "margin": _to_decimal(row.margin),
                "previous_margin": _to_decimal(getattr(previous_rows.get(row.contract_id), "margin", ZERO)),
                "profit": _to_decimal(row.profit),
                "previous_profit": _to_decimal(getattr(previous_rows.get(row.contract_id), "profit", ZERO)),
                "revenue": _to_decimal(row.revenue),
                "cost": _to_decimal(row.cost),
            }
            for row in queryset[:25]
        ]

    @classmethod
    def build_client_contexts(cls, *, company, client=None, target_date=None):
        period = ExecutiveAnalyticsService.get_period(reference_date=target_date, period_type=OperationalMetrics.PeriodType.MONTHLY)
        previous_period = ExecutiveAnalyticsService.get_period(reference_date=period.start - timedelta(days=1), period_type=OperationalMetrics.PeriodType.MONTHLY)
        queryset = ClientProfitability.objects.filter(company=company, period_type=period.period_type, period_start=period.start).select_related("client")
        if client is not None:
            queryset = queryset.filter(client=client)
        previous_rows = {
            row.client_id: row
            for row in ClientProfitability.objects.filter(company=company, period_type=previous_period.period_type, period_start=previous_period.start)
        }
        return [
            {
                "client_id": row.client_id,
                "client_public_id": str(row.client.public_id),
                "client_name": row.client.display_name,
                "margin": _to_decimal(row.margin),
                "previous_margin": _to_decimal(getattr(previous_rows.get(row.client_id), "margin", ZERO)),
                "profit": _to_decimal(row.profit),
                "previous_profit": _to_decimal(getattr(previous_rows.get(row.client_id), "profit", ZERO)),
                "revenue": _to_decimal(row.revenue),
                "cost": _to_decimal(row.cost),
            }
            for row in queryset[:25]
        ]

    @classmethod
    def build_marketplace_context(cls, *, company, site=None, recent_start, recent_end, baseline_start, baseline_end):
        request_queryset = TechnicianServiceRequest.objects.filter(requester_company=company)
        if site is not None:
            request_queryset = request_queryset.filter(related_site=site)
        recent_requests = list(request_queryset.filter(created_at__date__gte=recent_start, created_at__date__lte=recent_end))
        baseline_requests = list(request_queryset.filter(created_at__date__gte=baseline_start, created_at__date__lte=baseline_end))
        recent_offers = list(
            TechnicianServiceOffer.objects.filter(
                service_request__requester_company=company,
                created_at__date__gte=recent_start,
                created_at__date__lte=recent_end,
            )
        )
        baseline_offers = list(
            TechnicianServiceOffer.objects.filter(
                service_request__requester_company=company,
                created_at__date__gte=baseline_start,
                created_at__date__lte=baseline_end,
            )
        )
        recent_cancelled_assignments = TechnicianAssignment.objects.filter(
            technician_service_request__requester_company=company,
            assigned_at__date__gte=recent_start,
            assigned_at__date__lte=recent_end,
            assignment_status=TechnicianAssignment.AssignmentStatus.CANCELLED,
        ).count()
        baseline_cancelled_assignments = TechnicianAssignment.objects.filter(
            technician_service_request__requester_company=company,
            assigned_at__date__gte=baseline_start,
            assigned_at__date__lte=baseline_end,
            assignment_status=TechnicianAssignment.AssignmentStatus.CANCELLED,
        ).count()
        recent_acceptance_rate = cls._offer_acceptance_rate(recent_offers)
        baseline_acceptance_rate = cls._offer_acceptance_rate(baseline_offers)
        current_unassigned = request_queryset.filter(
            status__in=[
                TechnicianServiceRequest.Status.OPEN,
                TechnicianServiceRequest.Status.MATCHING,
                TechnicianServiceRequest.Status.OFFERS_RECEIVED,
            ]
        ).count()
        return {
            "recent_requests": len(recent_requests),
            "baseline_requests_avg": _safe_div(_to_decimal(len(baseline_requests)), Decimal("4")).quantize(Decimal("0.01")),
            "recent_acceptance_rate": recent_acceptance_rate,
            "baseline_acceptance_rate": baseline_acceptance_rate,
            "recent_cancelled_assignments": recent_cancelled_assignments,
            "baseline_cancelled_assignments_avg": _safe_div(_to_decimal(baseline_cancelled_assignments), Decimal("4")).quantize(Decimal("0.01")),
            "current_unassigned": current_unassigned,
            "site_id": getattr(site, "id", None),
            "site_public_id": str(site.public_id) if site is not None else "",
            "site_name": site.name if site is not None else "",
        }

    @classmethod
    def analyze_scope(cls, *, context: dict, definition=None):
        thresholds = cls.get_thresholds(definition)
        recommendations = []
        proposals = []
        flags = []

        for asset_context in context.get("assets", []):
            baseline_failures = _to_decimal(asset_context["baseline_failures_avg"])
            if (
                asset_context["recent_failures"] >= thresholds["minimum_failure_spike"]
                and _to_decimal(asset_context["recent_failures"]) >= (baseline_failures * thresholds["failure_spike_multiplier"])
            ):
                deviation = _percent_change(asset_context["recent_failures"], baseline_failures)
                recommendations.append(
                    AnomalyRecommendationDraft(
                        recommendation_type="anomaly_failure_spike",
                        severity="high" if asset_context["criticality"] != "critical" else "critical",
                        priority="high" if asset_context["criticality"] != "critical" else "immediate",
                        title=f"Ativo {asset_context['asset_tag']} fora do padrao de falhas",
                        summary=(
                            f"{asset_context['asset_tag']} registrou {asset_context['recent_failures']} falhas recentes, acima do padrao historico da janela comparativa."
                        ),
                        explanation=(
                            f"O ativo foi comparado com a baseline operacional das quatro janelas anteriores equivalentes. "
                            f"A media anterior era {baseline_failures} falhas por janela e a ocorrencia recente subiu para {asset_context['recent_failures']}."
                        ),
                        evidence_summary=(
                            f"Falhas recentes: {asset_context['recent_failures']} | baseline media: {baseline_failures} | "
                            f"corretivas recentes: {asset_context['recent_correctives']}."
                        ),
                        suggested_action="Abrir investigacao tecnica prioritaria e acionar revisao especializada de manutencao.",
                        attention_score=min(100, 70 + int(asset_context["recent_failures"] * 5)),
                        entity_type="asset",
                        entity_id=asset_context["asset_public_id"],
                        payload={
                            **asset_context,
                            "deviation_percent": str(deviation),
                            "suggested_agent_follow_up": "maintenance-agent",
                        },
                    )
                )
                proposals.append(
                    AnomalyActionProposalDraft(
                        action_type="trigger_maintenance_specialist_review",
                        target_entity="asset",
                        target_entity_id=asset_context["asset_public_id"],
                        title=f"Investigar anomalia no ativo {asset_context['asset_tag']}",
                        summary="Disparar revisao tecnica especializada para validar falha fora do padrao e possivel agravamento operacional.",
                        proposed_payload={"asset_public_id": asset_context["asset_public_id"], "site_id": asset_context["site_id"]},
                        priority="high",
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="asset",
                        target_entity_type="asset",
                        target_entity_id=asset_context["asset_public_id"],
                        display_label=f"{asset_context['asset_tag']} - {asset_context['name']}",
                        site_id=asset_context["site_id"],
                        attention_score=min(100, 70 + int(asset_context["recent_failures"] * 5)),
                        summary="Ativo com spike de falhas acima da baseline recente.",
                        risk_level="critical" if asset_context["criticality"] == "critical" else "high",
                        payload={"baseline_failures_avg": str(baseline_failures), "recent_failures": asset_context["recent_failures"]},
                        asset_id=asset_context["asset_id"],
                    )
                )

        for site_context in context.get("sites", []):
            backlog_baseline = _to_decimal(site_context["baseline_backlog_avg"])
            failure_baseline = _to_decimal(site_context["baseline_failures_avg"])
            backlog_anomaly = (
                site_context["current_open_backlog"] >= thresholds["minimum_backlog_open"]
                and _to_decimal(site_context["current_open_backlog"]) >= (backlog_baseline * thresholds["backlog_growth_multiplier"])
            )
            failure_anomaly = (
                site_context["recent_failures"] >= thresholds["minimum_failure_spike"]
                and _to_decimal(site_context["recent_failures"]) >= (failure_baseline * thresholds["failure_spike_multiplier"])
            )
            sla_drop = (
                site_context["baseline_sla_rate"] > ZERO
                and site_context["baseline_sla_rate"] - site_context["recent_sla_rate"] >= thresholds["sla_drop_points"]
            ) or (site_context["recent_sla_rate"] and site_context["recent_sla_rate"] < thresholds["critical_sla_rate"])
            if backlog_anomaly:
                deviation = _percent_change(site_context["current_open_backlog"], backlog_baseline)
                recommendations.append(
                    AnomalyRecommendationDraft(
                        recommendation_type="anomaly_backlog_growth",
                        severity="critical",
                        priority="immediate",
                        title=f"Backlog fora do padrao em {site_context['site_name']}",
                        summary=(
                            f"O site {site_context['site_name']} acumula {site_context['current_open_backlog']} OS abertas, acima do ritmo historico esperado."
                        ),
                        explanation=(
                            f"A comparacao foi feita contra a media das quatro janelas anteriores equivalentes. "
                            f"A baseline do backlog era {backlog_baseline} e a operacao atual chegou a {site_context['current_open_backlog']}."
                        ),
                        evidence_summary=(
                            f"Backlog atual: {site_context['current_open_backlog']} | backlog recente: {site_context['recent_backlog']} | "
                            f"baseline media: {backlog_baseline}."
                        ),
                        suggested_action="Abrir investigacao operacional do site e priorizar redistribuicao do backlog critico.",
                        attention_score=min(100, 75 + site_context["current_open_backlog"]),
                        entity_type="operational_site",
                        entity_id=site_context["site_public_id"],
                        payload={**site_context, "deviation_percent": str(deviation), "suggested_agent_follow_up": "scheduling-agent"},
                    )
                )
                proposals.append(
                    AnomalyActionProposalDraft(
                        action_type="open_operational_investigation",
                        target_entity="operational_site",
                        target_entity_id=site_context["site_public_id"],
                        title=f"Abrir investigacao de backlog em {site_context['site_name']}",
                        summary="Escalar o backlog anomalo para coordenacao operacional com revisao de capacidade e prioridades.",
                        proposed_payload={"site_id": site_context["site_id"], "site_code": site_context["site_code"]},
                        priority="immediate",
                    )
                )
            if failure_anomaly or sla_drop:
                deviation = _percent_change(site_context["recent_failures"], failure_baseline)
                recommendations.append(
                    AnomalyRecommendationDraft(
                        recommendation_type="anomaly_site_risk_alert" if failure_anomaly else "anomaly_sla_drop",
                        severity="critical" if sla_drop else "high",
                        priority="immediate" if sla_drop else "high",
                        title=f"Site {site_context['site_name']} em atencao anomala",
                        summary=(
                            f"{site_context['site_name']} apresentou desvio relevante em falhas, SLA ou corretivas e saiu do comportamento operacional esperado."
                        ),
                        explanation=(
                            f"O site foi comparado com a baseline recente da propria operacao. "
                            f"Falhas recentes: {site_context['recent_failures']} contra media {failure_baseline}; "
                            f"SLA recente: {site_context['recent_sla_rate']}% contra baseline {site_context['baseline_sla_rate']}%."
                        ),
                        evidence_summary=(
                            f"Falhas: {site_context['recent_failures']} | corretivas recentes: {site_context['recent_correctives']} | "
                            f"SLA recente: {site_context['recent_sla_rate']}% | SLA baseline: {site_context['baseline_sla_rate']}%."
                        ),
                        suggested_action="Escalar alerta para coordenacao e revisar manutencao, agenda e capacidade local.",
                        attention_score=min(100, 72 + int(max(site_context["recent_failures"], site_context["current_open_backlog"]))),
                        entity_type="operational_site",
                        entity_id=site_context["site_public_id"],
                        payload={
                            **site_context,
                            "failure_deviation_percent": str(deviation),
                            "suggested_agent_follow_up": "maintenance-agent" if failure_anomaly else "scheduling-agent",
                        },
                    )
                )
                proposals.append(
                    AnomalyActionProposalDraft(
                        action_type="open_operational_attention_committee",
                        target_entity="operational_site",
                        target_entity_id=site_context["site_public_id"],
                        title=f"Escalar site {site_context['site_name']} para comite de atencao",
                        summary="Consolidar manutencao, operacao e agenda em uma resposta coordenada ao desvio detectado.",
                        proposed_payload={"site_id": site_context["site_id"], "site_code": site_context["site_code"]},
                        priority="immediate" if sla_drop else "high",
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="site",
                        target_entity_type="operational_site",
                        target_entity_id=site_context["site_public_id"],
                        display_label=f"{site_context['site_code']} - {site_context['site_name']}",
                        site_id=site_context["site_id"],
                        attention_score=min(100, 72 + int(max(site_context["recent_failures"], site_context["current_open_backlog"]))),
                        summary="Site com desvio anomalo em backlog, falhas ou SLA.",
                        risk_level="critical" if sla_drop else "high",
                        payload={
                            "recent_failures": site_context["recent_failures"],
                            "baseline_failures_avg": str(failure_baseline),
                            "current_open_backlog": site_context["current_open_backlog"],
                            "baseline_backlog_avg": str(backlog_baseline),
                            "recent_sla_rate": str(site_context["recent_sla_rate"]),
                            "baseline_sla_rate": str(site_context["baseline_sla_rate"]),
                        },
                    )
                )

        for part_context in context.get("parts", []):
            baseline_cost = _to_decimal(part_context["baseline_cost_avg"])
            if (
                part_context["recent_cost"] >= thresholds["minimum_parts_cost"]
                and part_context["recent_cost"] >= (baseline_cost * thresholds["parts_spike_multiplier"])
            ):
                deviation = _percent_change(part_context["recent_cost"], baseline_cost)
                recommendations.append(
                    AnomalyRecommendationDraft(
                        recommendation_type="anomaly_parts_consumption",
                        severity="high",
                        priority="high",
                        title=f"Consumo anomalo da peca {part_context['part_code']}",
                        summary=(
                            f"A peca {part_context['part_code']} saiu do padrao e consumiu custo recente acima da media historica."
                        ),
                        explanation=(
                            f"A baseline do custo por janela era {baseline_cost} e o custo recente chegou a {part_context['recent_cost']}. "
                            f"Esse desvio sugere falha sistemica, retrabalho ou divergencia de apontamento."
                        ),
                        evidence_summary=(
                            f"Quantidade recente: {part_context['recent_quantity']} | custo recente: {part_context['recent_cost']} | "
                            f"baseline media de custo: {baseline_cost}."
                        ),
                        suggested_action="Revisar consumo, validar causa operacional e checar associacao com ativos ou OS recorrentes.",
                        attention_score=min(100, 65 + int(part_context["recent_cost"] / Decimal("100"))),
                        entity_type="part",
                        entity_id=part_context["part_public_id"],
                        payload={**part_context, "deviation_percent": str(deviation)},
                    )
                )
                proposals.append(
                    AnomalyActionProposalDraft(
                        action_type="review_parts_consumption",
                        target_entity="part",
                        target_entity_id=part_context["part_public_id"],
                        title=f"Revisar consumo da peca {part_context['part_code']}",
                        summary="Validar se o aumento de consumo decorre de falha sistemica, desvio operacional ou necessidade real.",
                        proposed_payload={"part_public_id": part_context["part_public_id"], "site_id": part_context["site_id"]},
                        priority="high",
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="part",
                        target_entity_type="part",
                        target_entity_id=part_context["part_public_id"],
                        display_label=f"{part_context['part_code']} - {part_context['part_name']}",
                        site_id=part_context.get("site_id"),
                        attention_score=min(100, 65 + int(part_context["recent_cost"] / Decimal("100"))),
                        summary="Peca com consumo fora da faixa historica.",
                        risk_level="high",
                        payload={"recent_cost": str(part_context["recent_cost"]), "baseline_cost_avg": str(baseline_cost)},
                        part_id=part_context["part_id"],
                    )
                )

        for contract_context in context.get("contracts", []):
            margin_drop = contract_context["previous_margin"] - contract_context["margin"]
            if margin_drop >= thresholds["contract_margin_shift_points"] or (
                contract_context["profit"] < ZERO and contract_context["previous_profit"] >= ZERO
            ):
                recommendations.append(
                    AnomalyRecommendationDraft(
                        recommendation_type="anomaly_contract_margin_shift",
                        severity="high",
                        priority="high",
                        title=f"Contrato {contract_context['contract_number']} com piora abrupta de margem",
                        summary=(
                            f"O contrato {contract_context['contract_number']} saiu do padrao financeiro e apresentou piora relevante de margem."
                        ),
                        explanation=(
                            f"A margem atual caiu para {contract_context['margin']}% contra {contract_context['previous_margin']}% no periodo anterior. "
                            f"O lucro atual e {contract_context['profit']}."
                        ),
                        evidence_summary=(
                            f"Receita: {contract_context['revenue']} | custo: {contract_context['cost']} | "
                            f"margem atual: {contract_context['margin']}% | margem anterior: {contract_context['previous_margin']}%."
                        ),
                        suggested_action="Acionar analise gerencial imediata e revisar esforco operacional, corretivas e cobertura contratual.",
                        attention_score=min(100, 70 + int(abs(margin_drop))),
                        entity_type="maintenance_contract",
                        entity_id=contract_context["contract_public_id"],
                        payload={**contract_context, "margin_drop_points": str(margin_drop), "suggested_agent_follow_up": "profitability-agent"},
                    )
                )
                proposals.append(
                    AnomalyActionProposalDraft(
                        action_type="review_contract_profitability_shift",
                        target_entity="maintenance_contract",
                        target_entity_id=contract_context["contract_public_id"],
                        title=f"Reavaliar rentabilidade do contrato {contract_context['contract_number']}",
                        summary="Escalar a piora abrupta de margem para revisao financeira-operacional e decisao comercial.",
                        proposed_payload={"contract_public_id": contract_context["contract_public_id"], "client_id": contract_context["client_id"]},
                        priority="high",
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="contract",
                        target_entity_type="maintenance_contract",
                        target_entity_id=contract_context["contract_public_id"],
                        display_label=contract_context["contract_number"],
                        site_id=contract_context.get("site_id"),
                        attention_score=min(100, 70 + int(abs(margin_drop))),
                        summary="Contrato com deslocamento abrupto de margem frente ao historico.",
                        risk_level="high",
                        payload={
                            "margin": str(contract_context["margin"]),
                            "previous_margin": str(contract_context["previous_margin"]),
                            "profit": str(contract_context["profit"]),
                        },
                        contract_id=contract_context["contract_id"],
                    )
                )

        for client_context in context.get("clients", []):
            margin_drop = client_context["previous_margin"] - client_context["margin"]
            if margin_drop >= thresholds["contract_margin_shift_points"] or (
                client_context["profit"] < ZERO and client_context["previous_profit"] >= ZERO
            ):
                recommendations.append(
                    AnomalyRecommendationDraft(
                        recommendation_type="anomaly_contract_margin_shift",
                        severity="high",
                        priority="high",
                        title=f"Cliente {client_context['client_name']} com mudanca anomala de resultado",
                        summary=(
                            f"O cliente {client_context['client_name']} apresentou deterioracao financeira fora do padrao no periodo atual."
                        ),
                        explanation=(
                            f"A margem atual caiu para {client_context['margin']}% contra {client_context['previous_margin']}% no periodo anterior. "
                            f"O lucro atual e {client_context['profit']}."
                        ),
                        evidence_summary=(
                            f"Receita: {client_context['revenue']} | custo: {client_context['cost']} | "
                            f"margem atual: {client_context['margin']}% | margem anterior: {client_context['previous_margin']}%."
                        ),
                        suggested_action="Escalar o cliente para revisao gerencial e validar origem operacional da piora.",
                        attention_score=min(100, 68 + int(abs(margin_drop))),
                        entity_type="maintenance_client",
                        entity_id=client_context["client_public_id"],
                        payload={**client_context, "margin_drop_points": str(margin_drop), "suggested_agent_follow_up": "profitability-agent"},
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="client",
                        target_entity_type="maintenance_client",
                        target_entity_id=client_context["client_public_id"],
                        display_label=client_context["client_name"],
                        attention_score=min(100, 68 + int(abs(margin_drop))),
                        summary="Cliente com piora abrupta de margem e lucro.",
                        risk_level="high",
                        payload={
                            "margin": str(client_context["margin"]),
                            "previous_margin": str(client_context["previous_margin"]),
                            "profit": str(client_context["profit"]),
                        },
                        client_id=client_context["client_id"],
                    )
                )

        for technician_context in context.get("technicians", []):
            previous_jobs = technician_context["previous_jobs_completed"]
            current_jobs = technician_context["jobs_completed"]
            ratio = _safe_div(_to_decimal(current_jobs), _to_decimal(previous_jobs)) if previous_jobs else Decimal("1.00")
            if previous_jobs and ratio <= thresholds["technician_drop_ratio"] and technician_context["recent_conflicts"] >= 1:
                recommendations.append(
                    AnomalyRecommendationDraft(
                        recommendation_type="anomaly_technician_behavior",
                        severity="medium",
                        priority="medium",
                        title=f"Desvio operacional do tecnico {technician_context['technician_name']}",
                        summary="O tecnico saiu do padrao comparavel de produtividade e apresentou sinais recentes de conflito operacional.",
                        explanation=(
                            f"No periodo atual foram concluídos {current_jobs} jobs contra {previous_jobs} no periodo anterior comparavel, "
                            f"com {technician_context['recent_conflicts']} conflitos recentes de agenda."
                        ),
                        evidence_summary=(
                            f"Jobs atuais: {current_jobs} | jobs anteriores: {previous_jobs} | "
                            f"avg exec atual: {technician_context['avg_execution_time']}."
                        ),
                        suggested_action="Revisar agenda, capacidade e possivel necessidade de apoio da coordenacao.",
                        attention_score=58,
                        entity_type="user",
                        entity_id=str(technician_context["technician_id"]),
                        payload=technician_context,
                    )
                )
                flags.append(
                    cls._build_flag(
                        focus_type="technician",
                        target_entity_type="user",
                        target_entity_id=str(technician_context["technician_id"]),
                        display_label=technician_context["technician_name"],
                        attention_score=58,
                        summary="Tecnico com comportamento operacional abaixo do comparavel.",
                        risk_level="medium",
                        payload=technician_context,
                        technician_id=technician_context["technician_id"],
                    )
                )

        marketplace_context = context.get("marketplace") or {}
        acceptance_drop = _to_decimal(marketplace_context.get("baseline_acceptance_rate", ZERO)) - _to_decimal(
            marketplace_context.get("recent_acceptance_rate", ZERO)
        )
        if (
            acceptance_drop >= thresholds["marketplace_acceptance_drop_points"]
            or _to_decimal(marketplace_context.get("recent_cancelled_assignments", 0))
            >= max(_to_decimal(marketplace_context.get("baseline_cancelled_assignments_avg", ZERO)) * Decimal("2.00"), Decimal(thresholds["minimum_assignment_cancellations"]))
            or int(marketplace_context.get("current_unassigned", 0)) >= thresholds["marketplace_unassigned_threshold"]
        ):
            site_public_id = marketplace_context.get("site_public_id") or ""
            entity_id = site_public_id or context.get("company_slug", "")
            recommendations.append(
                AnomalyRecommendationDraft(
                    recommendation_type="anomaly_marketplace_signal",
                    severity="high",
                    priority="high",
                    title="Marketplace com sinal anomalo de cobertura ou aceite",
                    summary="A operacao do marketplace apresentou desvio relevante em aceite, cancelamentos ou requests sem alocacao.",
                    explanation=(
                        f"A taxa recente de aceite ficou em {marketplace_context.get('recent_acceptance_rate')}% contra "
                        f"{marketplace_context.get('baseline_acceptance_rate')}% na baseline. "
                        f"Requests sem alocacao agora: {marketplace_context.get('current_unassigned')}."
                    ),
                    evidence_summary=(
                        f"Aceite recente: {marketplace_context.get('recent_acceptance_rate')}% | "
                        f"aceite baseline: {marketplace_context.get('baseline_acceptance_rate')}% | "
                        f"cancelamentos recentes: {marketplace_context.get('recent_cancelled_assignments')}."
                    ),
                    suggested_action="Revisar cobertura regional, qualidade do matching e capacidade operacional do marketplace.",
                    attention_score=74,
                    entity_type="marketplace_queue",
                    entity_id=entity_id,
                    payload={**marketplace_context, "suggested_agent_follow_up": "marketplace-agent"},
                )
            )
            proposals.append(
                AnomalyActionProposalDraft(
                    action_type="review_marketplace_regional_coverage",
                    target_entity="marketplace_queue",
                    target_entity_id=entity_id,
                    title="Revisar cobertura do marketplace",
                    summary="Avaliar cobertura regional, aceite e fila aberta para reduzir risco estrutural do marketplace.",
                    proposed_payload=marketplace_context,
                    priority="high",
                )
            )
            flags.append(
                cls._build_flag(
                    focus_type="marketplace",
                    target_entity_type="marketplace_queue",
                    target_entity_id=entity_id,
                    display_label=marketplace_context.get("site_name") or "Marketplace company scope",
                    site_id=marketplace_context.get("site_id"),
                    attention_score=74,
                    summary="Marketplace com cobertura, aceite ou backlog fora do padrao.",
                    risk_level="high",
                    payload=marketplace_context,
                )
            )

        output_summary = (
            f"Anomaly detection analyzed {len(context.get('assets', []))} ativos, {len(context.get('sites', []))} sites, "
            f"{len(context.get('parts', []))} pecas, {len(context.get('contracts', []))} contratos, "
            f"{len(context.get('clients', []))} clientes e {len(context.get('technicians', []))} tecnicos."
        )
        return recommendations, proposals, flags, output_summary

    @classmethod
    def _calculate_sla_rate(cls, orders) -> Decimal:
        compliant = 0
        violated = 0
        for order in orders:
            if not (order.started_at or order.completed_at):
                continue
            target_minutes = ExecutiveAnalyticsService.SLA_TARGET_MINUTES.get(
                order.priority,
                ExecutiveAnalyticsService.SLA_TARGET_MINUTES[ServiceOrder.Priority.MEDIUM],
            )
            response_minutes = int(((order.started_at or order.completed_at) - order.opened_at).total_seconds() // 60)
            if response_minutes <= target_minutes:
                compliant += 1
            else:
                violated += 1
        total = compliant + violated
        if total == 0:
            return ZERO
        return ((_to_decimal(compliant) * Decimal("100")) / _to_decimal(total)).quantize(Decimal("0.01"))

    @classmethod
    def _offer_acceptance_rate(cls, offers) -> Decimal:
        if not offers:
            return ZERO
        accepted = len([offer for offer in offers if offer.status == TechnicianServiceOffer.Status.ACCEPTED])
        return ((_to_decimal(accepted) * Decimal("100")) / _to_decimal(len(offers))).quantize(Decimal("0.01"))

    @staticmethod
    def _build_flag(
        *,
        focus_type,
        target_entity_type,
        target_entity_id,
        display_label,
        attention_score,
        summary,
        risk_level,
        payload,
        site_id=None,
        asset_id=None,
        client_id=None,
        contract_id=None,
        technician_id=None,
        part_id=None,
    ):
        return {
            "focus_type": focus_type,
            "target_entity_type": target_entity_type,
            "target_entity_id": target_entity_id,
            "display_label": display_label,
            "site_id": site_id,
            "asset_id": asset_id,
            "client_id": client_id,
            "contract_id": contract_id,
            "technician_id": technician_id,
            "part_id": part_id,
            "attention_score": attention_score,
            "summary": summary,
            "risk_level": risk_level,
            "payload": _json_ready(payload),
        }
