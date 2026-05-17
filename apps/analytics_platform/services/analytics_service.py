from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from apps.access_control_center.services.access_service import AccessAuditService
from apps.billing.models import Contract as BillingContract
from apps.billing.models import Invoice
from apps.companies.models import Company, Membership
from apps.marketplace_technicians.models import TechnicianReview
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import (
    Asset,
    FailureEvent,
    MaintenanceClient,
    MaintenanceContract,
    Part,
    ScheduledVisit,
    ServiceOrder,
    ServiceQuote,
    StockMovement,
    WorkLog,
)

from ..models import (
    AnalyticsEvent,
    AnalyticsMetricValue,
    AnalyticsSnapshot,
    ClientProfitability,
    ContractProfitability,
    OperationalMetrics,
    TechnicianPerformance,
)


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
    return _safe_div(numerator * Decimal("100.00"), denominator).quantize(Decimal("0.01"))


def _minutes_between(start, end) -> int:
    if not start or not end:
        return 0
    return max(int((end - start).total_seconds() // 60), 0)


@dataclass(frozen=True)
class AnalyticsPeriod:
    period_type: str
    start: date
    end: date
    label: str


class AnalyticsEventService:
    @staticmethod
    def record_event(**validated_data):
        return AnalyticsEvent.objects.create(**validated_data)


class AnalyticsMetricService:
    @staticmethod
    @transaction.atomic
    def record_metric_value(**validated_data):
        return AnalyticsMetricValue.objects.create(**validated_data)


class ExecutiveAnalyticsService:
    DEFAULT_LABOR_HOURLY_RATE = Decimal("85.00")
    DEFAULT_TRAVEL_HOURLY_RATE = Decimal("28.00")
    PROBLEMATIC_ASSET_FAILURE_THRESHOLD = 3
    OVERLOADED_TECHNICIAN_JOBS = 5
    SLA_TARGET_MINUTES = {
        ServiceOrder.Priority.LOW: 1440,
        ServiceOrder.Priority.MEDIUM: 480,
        ServiceOrder.Priority.HIGH: 240,
        ServiceOrder.Priority.URGENT: 120,
    }

    @classmethod
    def get_period(cls, *, reference_date: date | None = None, period_type: str = OperationalMetrics.PeriodType.MONTHLY) -> AnalyticsPeriod:
        reference_date = reference_date or timezone.localdate()
        if period_type == OperationalMetrics.PeriodType.DAILY:
            start = end = reference_date
            label = start.strftime("%d/%m/%Y")
        elif period_type == OperationalMetrics.PeriodType.QUARTERLY:
            quarter = ((reference_date.month - 1) // 3) + 1
            start_month = ((quarter - 1) * 3) + 1
            start = reference_date.replace(month=start_month, day=1)
            if start_month == 10:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start_month + 3, day=1) - timedelta(days=1)
            label = f"T{quarter}/{start.year}"
        elif period_type == OperationalMetrics.PeriodType.YEARLY:
            start = reference_date.replace(month=1, day=1)
            end = reference_date.replace(month=12, day=31)
            label = str(reference_date.year)
        else:
            start = reference_date.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            label = start.strftime("%m/%Y")
        return AnalyticsPeriod(period_type=period_type, start=start, end=end, label=label)

    @staticmethod
    def get_accessible_companies(user):
        if getattr(user, "is_superuser", False):
            return Company.objects.all()
        return Company.objects.filter(memberships__user=user).distinct()

    @classmethod
    def resolve_company_scope(cls, *, user, company_id=None):
        companies = cls.get_accessible_companies(user)
        if company_id:
            return companies.filter(id=company_id).first()
        membership = Membership.objects.filter(user=user, is_primary=True).select_related("company").first()
        if membership and companies.filter(id=membership.company_id).exists():
            return membership.company
        return companies.order_by("name").first()

    @classmethod
    def _active_contracts_queryset(cls, company, period: AnalyticsPeriod):
        return MaintenanceContract.objects.filter(
            company=company,
            status=MaintenanceContract.Status.ACTIVE,
            start_date__lte=period.end,
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=period.start))

    @classmethod
    def _service_orders_queryset(cls, company, period: AnalyticsPeriod):
        return ServiceOrder.objects.filter(
            client__company=company,
            opened_at__date__gte=period.start,
            opened_at__date__lte=period.end,
        ).select_related("client", "asset", "assigned_to", "maintenance_contract")

    @classmethod
    def _approved_quotes_queryset(cls, company, period: AnalyticsPeriod):
        return ServiceQuote.objects.filter(
            company=company,
            status=ServiceQuote.Status.APPROVED,
            approved_at__date__gte=period.start,
            approved_at__date__lte=period.end,
        )

    @classmethod
    def _invoice_queryset(cls, company, period: AnalyticsPeriod):
        return Invoice.objects.filter(
            company=company,
            issued_at__date__gte=period.start,
            issued_at__date__lte=period.end,
        ).exclude(status__in=[Invoice.Status.CANCELLED, Invoice.Status.VOID])

    @classmethod
    def _stock_cost_for_orders(cls, order_ids):
        rows = (
            StockMovement.objects.filter(
                service_order_id__in=order_ids,
                movement_type__in=[StockMovement.MovementType.OUTBOUND, StockMovement.MovementType.RESERVED],
            )
            .select_related("part")
        )
        per_order = {}
        for movement in rows:
            unit_cost = _to_decimal(getattr(movement.part, "unit_cost", 0))
            movement_cost = _to_decimal(movement.quantity) * unit_cost
            per_order[movement.service_order_id] = per_order.get(movement.service_order_id, ZERO) + movement_cost
        return per_order

    @classmethod
    def _labor_cost_for_orders(cls, order_ids):
        rows = WorkLog.objects.filter(service_order_id__in=order_ids)
        per_order = {}
        for row in rows:
            cost = (_to_decimal(row.labor_minutes) / Decimal("60")) * cls.DEFAULT_LABOR_HOURLY_RATE
            per_order[row.service_order_id] = per_order.get(row.service_order_id, ZERO) + cost
        return per_order

    @classmethod
    def _travel_cost_for_orders(cls, order_ids):
        rows = ScheduledVisit.objects.filter(work_order_id__in=order_ids)
        per_order = {}
        for row in rows:
            cost = (_to_decimal(row.estimated_travel_minutes) / Decimal("60")) * cls.DEFAULT_TRAVEL_HOURLY_RATE
            per_order[row.work_order_id] = per_order.get(row.work_order_id, ZERO) + cost
        return per_order

    @classmethod
    def _response_minutes_by_order(cls, orders):
        return {
            order.id: _minutes_between(order.opened_at, order.started_at or order.completed_at)
            for order in orders
        }

    @classmethod
    def _execution_minutes_by_order(cls, orders):
        return {
            order.id: _minutes_between(order.started_at or order.opened_at, order.completed_at)
            for order in orders
        }

    @classmethod
    def _sla_stats(cls, orders):
        compliant = 0
        violated = 0
        response_minutes = []
        execution_minutes = []
        for order in orders:
            response = _minutes_between(order.opened_at, order.started_at or order.completed_at)
            execution = _minutes_between(order.started_at or order.opened_at, order.completed_at)
            if response:
                response_minutes.append(response)
                target = cls.SLA_TARGET_MINUTES.get(order.priority, cls.SLA_TARGET_MINUTES[ServiceOrder.Priority.MEDIUM])
                if response <= target:
                    compliant += 1
                else:
                    violated += 1
            if execution:
                execution_minutes.append(execution)
        return {
            "avg_response": _to_decimal(sum(response_minutes) / len(response_minutes)) if response_minutes else ZERO,
            "avg_execution": _to_decimal(sum(execution_minutes) / len(execution_minutes)) if execution_minutes else ZERO,
            "sla_compliant": compliant,
            "sla_violated": violated,
            "sla_rate": _percent(_to_decimal(compliant), _to_decimal(compliant + violated)),
        }

    @classmethod
    def _maintenance_contract_revenue(cls, company, period: AnalyticsPeriod):
        return sum((contract.contract_value for contract in cls._active_contracts_queryset(company, period)), ZERO)

    @classmethod
    def _quote_revenue(cls, company, period: AnalyticsPeriod):
        return cls._approved_quotes_queryset(company, period).aggregate(total=Sum("total_value"))["total"] or ZERO

    @classmethod
    def _billing_mrr(cls, company):
        return (
            BillingContract.objects.filter(company=company, status=BillingContract.Status.ACTIVE).aggregate(
                total=Sum("contracted_amount")
            )["total"]
            or ZERO
        )

    @classmethod
    def _order_revenue_map(cls, company, period: AnalyticsPeriod, orders):
        revenue_map = {order.id: ZERO for order in orders}
        quotes = cls._approved_quotes_queryset(company, period).filter(work_order_id__in=revenue_map.keys())
        for quote in quotes:
            revenue_map[quote.work_order_id] = revenue_map.get(quote.work_order_id, ZERO) + _to_decimal(quote.total_value)

        grouped_contract_orders = {}
        for order in orders:
            if order.maintenance_contract_id and revenue_map.get(order.id, ZERO) == ZERO:
                grouped_contract_orders.setdefault(order.maintenance_contract_id, []).append(order.id)

        contract_revenue_map = {
            contract.id: _to_decimal(contract.contract_value)
            for contract in cls._active_contracts_queryset(company, period).filter(id__in=grouped_contract_orders.keys())
        }
        for contract_id, order_ids in grouped_contract_orders.items():
            if not order_ids:
                continue
            allocated = _safe_div(contract_revenue_map.get(contract_id, ZERO), Decimal(len(order_ids)))
            for order_id in order_ids:
                revenue_map[order_id] = revenue_map.get(order_id, ZERO) + allocated
        return revenue_map

    @classmethod
    def _order_cost_map(cls, order_ids):
        labor = cls._labor_cost_for_orders(order_ids)
        stock = cls._stock_cost_for_orders(order_ids)
        travel = cls._travel_cost_for_orders(order_ids)
        totals = {}
        for order_id in order_ids:
            totals[order_id] = labor.get(order_id, ZERO) + stock.get(order_id, ZERO) + travel.get(order_id, ZERO)
        return totals

    @classmethod
    def _top_problematic_assets(cls, company, period: AnalyticsPeriod):
        orders = cls._service_orders_queryset(company, period).filter(asset__isnull=False)
        order_ids = list(orders.values_list("id", flat=True))
        cost_map = cls._order_cost_map(order_ids)
        failure_counts = {
            row["asset_id"]: row["total_failures"]
            for row in FailureEvent.objects.filter(
                asset__operational_site__maintenance_client__company=company,
                detected_at__date__gte=period.start,
                detected_at__date__lte=period.end,
            )
            .values("asset_id")
            .annotate(total_failures=Count("id"))
        }
        assets = []
        for asset in Asset.objects.filter(operational_site__maintenance_client__company=company):
            asset_orders = [order.id for order in orders if order.asset_id == asset.id]
            maintenance_cost = sum((cost_map.get(order_id, ZERO) for order_id in asset_orders), ZERO)
            assets.append(
                {
                    "asset_id": asset.public_id,
                    "asset_tag": asset.asset_tag,
                    "asset_name": asset.name,
                    "site_name": asset.operational_site.name,
                    "failure_count": failure_counts.get(asset.id, 0),
                    "maintenance_cost": maintenance_cost,
                    "total_orders": len(asset_orders),
                }
            )
        assets.sort(key=lambda entry: (entry["failure_count"], entry["maintenance_cost"]), reverse=True)
        return assets[:8]

    @classmethod
    @transaction.atomic
    def refresh_company_snapshots(cls, *, company, reference_date: date | None = None, period_type: str = OperationalMetrics.PeriodType.MONTHLY, user=None):
        period = cls.get_period(reference_date=reference_date, period_type=period_type)
        orders = list(cls._service_orders_queryset(company, period))
        order_ids = [order.id for order in orders]
        order_cost_map = cls._order_cost_map(order_ids)
        order_revenue_map = cls._order_revenue_map(company, period, orders)

        contract_revenue = cls._maintenance_contract_revenue(company, period)
        quote_revenue = cls._quote_revenue(company, period)
        total_revenue = contract_revenue + quote_revenue
        total_cost = sum((order_cost_map.get(order.id, ZERO) for order in orders), ZERO)
        total_profit = total_revenue - total_cost
        sla_stats = cls._sla_stats(orders)

        operational_metrics, _ = OperationalMetrics.objects.update_or_create(
            company=company,
            period_type=period.period_type,
            period_start=period.start,
            defaults={
                "period_end": period.end,
                "total_work_orders": len(orders),
                "total_preventives": sum(1 for order in orders if order.maintenance_type == ServiceOrder.MaintenanceType.PREVENTIVE),
                "total_correctives": sum(1 for order in orders if order.maintenance_type == ServiceOrder.MaintenanceType.CORRECTIVE),
                "total_revenue": total_revenue,
                "total_cost": total_cost,
                "total_profit": total_profit,
                "avg_response_time": sla_stats["avg_response"],
                "avg_execution_time": sla_stats["avg_execution"],
                "sla_compliance_rate": sla_stats["sla_rate"],
                "total_sla_compliant": sla_stats["sla_compliant"],
                "total_sla_violated": sla_stats["sla_violated"],
                "metadata": {
                    "billing_mrr_total": str(cls._billing_mrr(company)),
                    "contract_revenue": str(contract_revenue),
                    "quote_revenue": str(quote_revenue),
                    "top_problematic_assets": cls._top_problematic_assets(company, period),
                },
                "calculated_at": timezone.now(),
            },
        )

        for client in MaintenanceClient.objects.filter(company=company):
            client_orders = [order for order in orders if order.client_id == client.id]
            client_revenue = sum((order_revenue_map.get(order.id, ZERO) for order in client_orders), ZERO)
            client_cost = sum((order_cost_map.get(order.id, ZERO) for order in client_orders), ZERO)
            ClientProfitability.objects.update_or_create(
                client=client,
                period_type=period.period_type,
                period_start=period.start,
                defaults={
                    "company": company,
                    "period_end": period.end,
                    "revenue": client_revenue,
                    "cost": client_cost,
                    "profit": client_revenue - client_cost,
                    "margin": _percent(client_revenue - client_cost, client_revenue),
                    "total_work_orders": len(client_orders),
                    "total_assets": Asset.objects.filter(operational_site__maintenance_client=client).count(),
                    "metadata": {
                        "sites": list(client.operational_sites.values_list("name", flat=True)),
                    },
                    "calculated_at": timezone.now(),
                },
            )

        for contract in cls._active_contracts_queryset(company, period):
            contract_orders = [order for order in orders if order.maintenance_contract_id == contract.id]
            contract_cost = sum((order_cost_map.get(order.id, ZERO) for order in contract_orders), ZERO)
            contract_revenue_value = _to_decimal(contract.contract_value)
            ContractProfitability.objects.update_or_create(
                contract=contract,
                period_type=period.period_type,
                period_start=period.start,
                defaults={
                    "company": company,
                    "period_end": period.end,
                    "revenue": contract_revenue_value,
                    "cost": contract_cost,
                    "profit": contract_revenue_value - contract_cost,
                    "margin": _percent(contract_revenue_value - contract_cost, contract_revenue_value),
                    "total_work_orders": len(contract_orders),
                    "total_assets": contract.covered_assets.filter(is_active=True).count(),
                    "metadata": {
                        "site": contract.operational_site.name if contract.operational_site else "",
                        "client": contract.client.display_name,
                    },
                    "calculated_at": timezone.now(),
                },
            )

        technicians = {order.assigned_to for order in orders if order.assigned_to_id}
        for technician in technicians:
            technician_orders = [order for order in orders if order.assigned_to_id == technician.id]
            completed_orders = [order for order in technician_orders if order.status == ServiceOrder.Status.COMPLETED]
            in_progress_orders = [
                order
                for order in technician_orders
                if order.status in {ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.IN_PROGRESS}
            ]
            execution_minutes = [
                _minutes_between(order.started_at or order.opened_at, order.completed_at)
                for order in completed_orders
                if order.completed_at
            ]
            rating = (
                TechnicianReview.objects.filter(
                    technician_profile__user=technician,
                    assignment__technician_service_request__requester_company=company,
                ).aggregate(avg=Avg("rating"))["avg"]
                or 0
            )
            TechnicianPerformance.objects.update_or_create(
                company=company,
                technician=technician,
                period_type=period.period_type,
                period_start=period.start,
                defaults={
                    "period_end": period.end,
                    "jobs_completed": len(completed_orders),
                    "jobs_in_progress": len(in_progress_orders),
                    "avg_execution_time": _to_decimal(sum(execution_minutes) / len(execution_minutes)) if execution_minutes else ZERO,
                    "customer_rating": _to_decimal(rating),
                    "profit_generated": sum(
                        (order_revenue_map.get(order.id, ZERO) - order_cost_map.get(order.id, ZERO) for order in technician_orders),
                        ZERO,
                    ),
                    "total_labor_minutes": sum(
                        log.labor_minutes
                        for log in WorkLog.objects.filter(service_order_id__in=[order.id for order in technician_orders])
                    ),
                    "total_response_minutes": sum(
                        _minutes_between(order.opened_at, order.started_at or order.completed_at)
                        for order in technician_orders
                    ),
                    "metadata": {
                        "completed_order_numbers": [order.order_number for order in completed_orders[:10]],
                    },
                    "calculated_at": timezone.now(),
                },
            )

        snapshot_payload = {
            "company_name": company.name,
            "period": {"type": period.period_type, "start": str(period.start), "end": str(period.end), "label": period.label},
            "operational_metrics": {
                "total_work_orders": operational_metrics.total_work_orders,
                "total_revenue": str(operational_metrics.total_revenue),
                "total_cost": str(operational_metrics.total_cost),
                "total_profit": str(operational_metrics.total_profit),
                "sla_compliance_rate": str(operational_metrics.sla_compliance_rate),
            },
        }
        AnalyticsSnapshot.objects.update_or_create(
            snapshot_type=f"executive_company:{company.slug}:{period.period_type}",
            snapshot_date=period.start,
            defaults={"data_json": snapshot_payload},
        )
        AccessAuditService.log(
            user=user,
            action="analytics_snapshot_refreshed",
            domain="analytics_admin",
            decision="allow",
            resource_type="company",
            resource_id=company.slug,
            metadata={"period_type": period.period_type, "period_start": str(period.start)},
            company=company,
        )
        SystemEventService.log_system_event(
            event_type="analytics.snapshot_refreshed",
            source_module="analytics_platform",
            company=company,
            message=f"Snapshot executivo atualizado para {company.name}.",
            entity_type="company",
            entity_id=company.slug,
            payload={"period_type": period.period_type, "period_start": str(period.start)},
            user=user,
        )
        return operational_metrics

    @classmethod
    def build_executive_dashboard(cls, *, company, reference_date: date | None = None, period_type: str = OperationalMetrics.PeriodType.MONTHLY):
        period = cls.get_period(reference_date=reference_date, period_type=period_type)
        metrics = cls.refresh_company_snapshots(company=company, reference_date=reference_date, period_type=period_type)
        client_rows = list(
            ClientProfitability.objects.filter(company=company, period_type=period.period_type, period_start=period.start)
            .select_related("client")
            .order_by("-profit", "-revenue")[:6]
        )
        contract_rows = list(
            ContractProfitability.objects.filter(company=company, period_type=period.period_type, period_start=period.start)
            .select_related("contract", "contract__client")
            .order_by("-profit", "-revenue")[:6]
        )
        technician_rows = list(
            TechnicianPerformance.objects.filter(company=company, period_type=period.period_type, period_start=period.start)
            .select_related("technician")
            .order_by("-jobs_completed", "-profit_generated")[:8]
        )
        asset_rows = cls._top_problematic_assets(company, period)
        contracts_active = cls._active_contracts_queryset(company, period).count()
        overdue_preventives = ServiceOrder.objects.filter(
            client__company=company,
            maintenance_type=ServiceOrder.MaintenanceType.PREVENTIVE,
            status__in=[ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.IN_PROGRESS],
            scheduled_start__date__lt=timezone.localdate(),
        ).count()

        alerts = []
        for row in client_rows[:3]:
            if row.profit < 0:
                alerts.append(
                    {
                        "level": "critical",
                        "title": "Cliente nao lucrativo",
                        "description": f"{row.client.display_name} encerrou o periodo com margem negativa.",
                    }
                )
        for row in contract_rows[:3]:
            if row.profit < 0:
                alerts.append(
                    {
                        "level": "warning",
                        "title": "Contrato deficitario",
                        "description": f"{row.contract.contract_number} operou abaixo do ponto de equilibrio.",
                    }
                )
        for row in technician_rows[:3]:
            if row.jobs_in_progress > cls.OVERLOADED_TECHNICIAN_JOBS:
                alerts.append(
                    {
                        "level": "warning",
                        "title": "Tecnico sobrecarregado",
                        "description": f"{row.technician.display_name or row.technician.email} esta com carga acima do esperado.",
                    }
                )
        for row in asset_rows[:2]:
            if row["failure_count"] >= cls.PROBLEMATIC_ASSET_FAILURE_THRESHOLD:
                alerts.append(
                    {
                        "level": "warning",
                        "title": "Ativo problematico",
                        "description": f"{row['asset_tag']} concentrou falhas recorrentes no periodo.",
                    }
                )

        return {
            "period": {"label": period.label, "start": period.start, "end": period.end, "type": period.period_type},
            "company": company,
            "kpis": [
                {"label": "Receita operacional", "value": metrics.total_revenue, "tone": "emerald", "helper": "Contratos recorrentes + orcamentos aprovados", "format": "currency"},
                {"label": "Lucro operacional", "value": metrics.total_profit, "tone": "sky", "helper": "Receita menos mao de obra, pecas e deslocamento", "format": "currency"},
                {"label": "Contratos ativos", "value": contracts_active, "tone": "violet", "helper": "Cobertura recorrente vigente", "format": "count"},
                {"label": "MRR total", "value": cls._billing_mrr(company), "tone": "amber", "helper": "Receita mensal recorrente de billing SaaS", "format": "currency"},
                {"label": "SLA medio", "value": metrics.sla_compliance_rate, "tone": "cyan", "helper": "Percentual de atendimentos no prazo", "format": "percentage"},
                {"label": "Tempo medio de resposta", "value": metrics.avg_response_time, "tone": "rose", "helper": "Minutos ate inicio do atendimento", "format": "duration"},
            ],
            "revenue_series": cls.get_revenue_series(company=company, period_type=period_type, reference_date=reference_date),
            "profit_series": cls.get_profit_series(company=company, period_type=period_type, reference_date=reference_date),
            "top_clients": [
                {
                    "name": row.client.display_name,
                    "revenue": row.revenue,
                    "cost": row.cost,
                    "profit": row.profit,
                    "margin": row.margin,
                    "work_orders": row.total_work_orders,
                }
                for row in client_rows
            ],
            "top_contracts": [
                {
                    "contract_number": row.contract.contract_number,
                    "client_name": row.contract.client.display_name,
                    "revenue": row.revenue,
                    "cost": row.cost,
                    "profit": row.profit,
                    "margin": row.margin,
                }
                for row in contract_rows
            ],
            "technician_leaderboard": [
                {
                    "name": row.technician.display_name or row.technician.full_name or row.technician.email,
                    "jobs_completed": row.jobs_completed,
                    "jobs_in_progress": row.jobs_in_progress,
                    "avg_execution_time": row.avg_execution_time,
                    "customer_rating": row.customer_rating,
                    "profit_generated": row.profit_generated,
                }
                for row in technician_rows
            ],
            "asset_analysis": asset_rows,
            "sla_summary": {
                "compliant": metrics.total_sla_compliant,
                "violated": metrics.total_sla_violated,
                "compliance_rate": metrics.sla_compliance_rate,
                "avg_response_time": metrics.avg_response_time,
                "avg_execution_time": metrics.avg_execution_time,
                "overdue_preventives": overdue_preventives,
            },
            "alerts": alerts[:8],
        }

    @classmethod
    def get_revenue_series(cls, *, company, period_type: str, reference_date: date | None = None, points: int = 6):
        series = []
        anchor = cls.get_period(reference_date=reference_date, period_type=period_type).start
        for offset in range(points - 1, -1, -1):
            if period_type == OperationalMetrics.PeriodType.YEARLY:
                period_date = anchor.replace(year=anchor.year - offset)
            elif period_type == OperationalMetrics.PeriodType.QUARTERLY:
                period_date = anchor - timedelta(days=90 * offset)
            else:
                period_date = (anchor.replace(day=1) - timedelta(days=32 * offset)).replace(day=1)
            metrics = cls.refresh_company_snapshots(company=company, reference_date=period_date, period_type=period_type)
            current_period = cls.get_period(reference_date=period_date, period_type=period_type)
            series.append({"label": current_period.label, "revenue": metrics.total_revenue})
        return series

    @classmethod
    def get_profit_series(cls, *, company, period_type: str, reference_date: date | None = None, points: int = 6):
        series = []
        anchor = cls.get_period(reference_date=reference_date, period_type=period_type).start
        for offset in range(points - 1, -1, -1):
            if period_type == OperationalMetrics.PeriodType.YEARLY:
                period_date = anchor.replace(year=anchor.year - offset)
            elif period_type == OperationalMetrics.PeriodType.QUARTERLY:
                period_date = anchor - timedelta(days=90 * offset)
            else:
                period_date = (anchor.replace(day=1) - timedelta(days=32 * offset)).replace(day=1)
            metrics = cls.refresh_company_snapshots(company=company, reference_date=period_date, period_type=period_type)
            current_period = cls.get_period(reference_date=period_date, period_type=period_type)
            series.append({"label": current_period.label, "profit": metrics.total_profit, "cost": metrics.total_cost})
        return series

    @classmethod
    def get_profitability_payload(cls, *, company, reference_date: date | None = None, period_type: str = OperationalMetrics.PeriodType.MONTHLY):
        dashboard = cls.build_executive_dashboard(company=company, reference_date=reference_date, period_type=period_type)
        return {
            "company": {"id": company.public_id, "name": company.name, "slug": company.slug},
            "period": dashboard["period"],
            "clients": dashboard["top_clients"],
            "contracts": dashboard["top_contracts"],
            "alerts": dashboard["alerts"],
        }

    @classmethod
    def get_technician_payload(cls, *, company, reference_date: date | None = None, period_type: str = OperationalMetrics.PeriodType.MONTHLY):
        dashboard = cls.build_executive_dashboard(company=company, reference_date=reference_date, period_type=period_type)
        return {
            "company": {"id": company.public_id, "name": company.name, "slug": company.slug},
            "period": dashboard["period"],
            "technicians": dashboard["technician_leaderboard"],
        }

    @classmethod
    def get_asset_payload(cls, *, company, reference_date: date | None = None, period_type: str = OperationalMetrics.PeriodType.MONTHLY):
        dashboard = cls.build_executive_dashboard(company=company, reference_date=reference_date, period_type=period_type)
        return {
            "company": {"id": company.public_id, "name": company.name, "slug": company.slug},
            "period": dashboard["period"],
            "assets": dashboard["asset_analysis"],
        }
