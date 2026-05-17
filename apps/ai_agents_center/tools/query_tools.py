from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.analytics_platform.models import ClientProfitability, ContractProfitability, OperationalMetrics, TechnicianPerformance
from apps.analytics_platform.services.analytics_service import ExecutiveAnalyticsService
from apps.marketplace_technicians.models import TechnicianAssignment, TechnicianMatchingRecord, TechnicianServiceOffer, TechnicianServiceRequest
from apps.reporting_center.models import ReportRequest
from apps.smart_system.models import Asset, MaintenanceContract, MaintenancePlan, RoutePlan, ScheduledVisit, ServiceDocument, ServiceOrder, ServiceOrderChecklistResponse, ServiceQuote, StockMovement, TechnicianAvailabilityWindow, TechnicianSchedule, WorkLog


def get_technician_routing_service():
    from apps.smart_system.services.scheduling_service import TechnicianRoutingService

    return TechnicianRoutingService


class AgentToolbox:
    @staticmethod
    def query_asset_profile(*, asset):
        return {
            "asset_tag": asset.asset_tag,
            "name": asset.name,
            "status": asset.status,
            "criticality": asset.criticality,
            "site": getattr(asset.operational_site, "name", ""),
            "category": getattr(asset.category, "name", ""),
        }

    @staticmethod
    def query_asset_failures(*, asset, days=45):
        return list(asset.failure_events.filter(detected_at__gte=timezone.now() - timedelta(days=days)).order_by("-detected_at"))

    @staticmethod
    def query_asset_work_orders(*, asset, days=45):
        return list(asset.service_orders.filter(opened_at__gte=timezone.now() - timedelta(days=days)).order_by("-opened_at"))

    @staticmethod
    def query_asset_preventives(*, asset):
        return list(asset.maintenance_plans.filter(is_active=True).order_by("next_due_date", "name"))

    @staticmethod
    def query_asset_checklists(*, asset):
        return list(
            ServiceOrderChecklistResponse.objects.filter(service_order__asset=asset)
            .select_related("service_order", "checklist_item")
            .order_by("-service_order__opened_at", "-created_at")[:20]
        )

    @staticmethod
    def query_asset_reliability_metrics(*, asset):
        recent_failures = list(asset.failure_events.order_by("-detected_at")[:10])
        downtime = sum(failure.downtime_minutes or 0 for failure in recent_failures)
        return {
            "recent_failures": len(recent_failures),
            "downtime_minutes": downtime,
            "open_work_orders": asset.service_orders.filter(status__in=["open", "in_progress", "on_hold"]).count(),
        }

    @staticmethod
    def query_asset_reports(*, asset):
        report_documents = list(
            ServiceDocument.objects.filter(service_order__asset=asset, document_type=ServiceDocument.DocumentType.REPORT)
            .select_related("service_order")
            .order_by("-created_at")[:5]
        )
        report_requests = list(
            ReportRequest.objects.filter(source_module="smart_system", filters_json__asset_id=str(asset.id)).order_by("-created_at")[:3]
        )
        return {"documents": report_documents, "report_requests": report_requests}

    @staticmethod
    def create_maintenance_recommendation(*, recommendation_type, asset, payload):
        return {
            "recommendation_type": recommendation_type,
            "asset_public_id": str(asset.public_id),
            "payload": payload,
        }

    @staticmethod
    def create_maintenance_action_proposal(*, action_type, asset, payload):
        return {
            "action_type": action_type,
            "asset_public_id": str(asset.public_id),
            "payload": payload,
        }

    @staticmethod
    def mark_asset_attention_flag(*, asset, score, payload):
        return {
            "asset_public_id": str(asset.public_id),
            "attention_score": score,
            "payload": payload,
        }

    @staticmethod
    def query_problematic_assets(*, company, site=None):
        queryset = Asset.objects.filter(operational_site__maintenance_client__company=company)
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return list(
            queryset.annotate(
                failure_count=Count("failure_events"),
                open_work_orders=Count("service_orders", filter=Q(service_orders__status__in=["open", "in_progress"])),
            )
            .filter(Q(failure_count__gte=2) | Q(open_work_orders__gte=2))
            .order_by("-failure_count", "-open_work_orders")[:10]
        )

    @staticmethod
    def query_contract_profitability(*, company):
        return ContractProfitability.objects.filter(company=company).select_related("contract", "contract__client").order_by("margin", "profit")[:10]

    @staticmethod
    def query_client_profitability(*, company):
        return ClientProfitability.objects.filter(company=company).select_related("client").order_by("margin", "profit")[:10]

    @staticmethod
    def query_operational_metrics(*, company):
        return OperationalMetrics.objects.filter(company=company).order_by("-period_start").first()

    @staticmethod
    def query_technician_load(*, company, target_date=None):
        target_date = target_date or timezone.localdate()
        return ScheduledVisit.objects.filter(company=company, scheduled_date=target_date).values("technician_id", "technician__first_name", "technician__last_name").annotate(
            total_visits=Count("id"),
            avg_duration=Avg("estimated_duration_minutes"),
        ).order_by("-total_visits")

    @staticmethod
    def query_technician_schedule(*, company, technician, target_date, site=None):
        queryset = ScheduledVisit.objects.filter(company=company, technician=technician, scheduled_date=target_date)
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return list(queryset.select_related("operational_site", "asset", "work_order", "route_plan").order_by("route_order", "scheduled_start"))

    @staticmethod
    def query_day_visits(*, company, target_date, site=None):
        queryset = ScheduledVisit.objects.filter(company=company, scheduled_date=target_date)
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return list(queryset.select_related("technician", "operational_site", "asset", "work_order").order_by("technician_id", "route_order", "scheduled_start"))

    @staticmethod
    def query_unassigned_visits(*, company, target_date, site=None):
        routing_service = get_technician_routing_service()
        return routing_service.build_unassigned_queue(schedule_date=target_date, company=company, site=site)

    @staticmethod
    def query_route_plan(*, company, technician, target_date):
        return RoutePlan.objects.filter(company=company, technician=technician, date=target_date).select_related("technician", "operational_site").first()

    @staticmethod
    def query_technician_capacity(*, company, technician, target_date):
        schedule = TechnicianSchedule.objects.filter(company=company, technician=technician, date=target_date).first()
        availability = TechnicianAvailabilityWindow.objects.filter(
            company=company,
            technician=technician,
        ).filter(Q(blocked_date=target_date) | Q(weekday=target_date.isoweekday())).order_by("-is_available").first()
        return {"schedule": schedule, "availability": availability}

    @staticmethod
    def query_technician_availability(*, company, technician, target_date):
        return list(
            TechnicianAvailabilityWindow.objects.filter(company=company, technician=technician)
            .filter(Q(blocked_date=target_date) | Q(weekday=target_date.isoweekday()))
            .order_by("blocked_date", "weekday", "start_time")
        )

    @staticmethod
    def query_sla_risk_visits(*, company, target_date, site=None):
        queryset = ScheduledVisit.objects.filter(company=company, scheduled_date=target_date, priority__in=["urgent", "high"])
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return list(queryset.select_related("work_order", "technician", "operational_site").order_by("-priority", "route_order", "scheduled_start"))

    @staticmethod
    def query_marketplace_alternatives(*, company, city="", state="", related_service_order=None):
        queryset = TechnicianMatchingRecord.objects.select_related("technician_profile", "technician_service_request").filter(
            technician_service_request__requester_company=company
        )
        if related_service_order is not None:
            queryset = queryset.filter(technician_service_request__related_service_order=related_service_order)
        elif city or state:
            queryset = queryset.filter(
                Q(technician_service_request__city__iexact=city) | Q(technician_service_request__state__iexact=state)
            )
        return list(queryset.order_by("ranking_position", "-match_score")[:10])

    @staticmethod
    def query_marketplace_matches(*, company):
        return TechnicianMatchingRecord.objects.filter(
            technician_service_request__requester_company=company,
            technician_service_request__status__in=[
                TechnicianServiceRequest.Status.OPEN,
                TechnicianServiceRequest.Status.OFFERS_RECEIVED,
            ],
        ).select_related("technician_profile", "technician_service_request").order_by("technician_service_request_id", "ranking_position")[:20]

    @staticmethod
    def query_service_request(*, company, service_request=None):
        queryset = TechnicianServiceRequest.objects.filter(requester_company=company).select_related(
            "related_site",
            "related_asset",
            "related_service_order",
        )
        if service_request is not None:
            queryset = queryset.filter(pk=service_request.pk)
        return list(queryset.order_by("-created_at")[:20])

    @staticmethod
    def query_marketplace_candidates(*, service_request):
        return list(
            service_request.matching_records.select_related("technician_profile", "technician_profile__user")
            .order_by("ranking_position", "-match_score")[:10]
        )

    @staticmethod
    def query_matching_scores(*, service_request):
        return [
            {
                "technician_profile_id": str(record.technician_profile.public_id),
                "technician_name": record.technician_profile.display_name,
                "match_score": record.match_score,
                "score_specialty": record.score_specialty,
                "score_distance": record.score_distance,
                "score_rating": record.score_rating,
                "score_experience": record.score_experience,
                "score_availability": record.score_availability,
                "distance_km": record.distance_km,
            }
            for record in service_request.matching_records.select_related("technician_profile").order_by("ranking_position", "-match_score")[:10]
        ]

    @staticmethod
    def query_assignment_history(*, service_request=None, technician_profile=None):
        from apps.marketplace_technicians.models import TechnicianAssignment

        queryset = TechnicianAssignment.objects.select_related("technician_service_request", "technician_profile")
        if service_request is not None:
            queryset = queryset.filter(technician_service_request=service_request)
        if technician_profile is not None:
            queryset = queryset.filter(technician_profile=technician_profile)
        return list(queryset.order_by("-assigned_at")[:20])

    @staticmethod
    def query_sla_context(*, service_request):
        now = timezone.now()
        hours_remaining = None
        if service_request.deadline_at:
            hours_remaining = round((service_request.deadline_at - now).total_seconds() / 3600, 2)
        return {
            "priority": service_request.priority,
            "deadline_at": service_request.deadline_at.isoformat() if service_request.deadline_at else "",
            "hours_remaining": hours_remaining,
            "requested_date": service_request.requested_date.isoformat() if service_request.requested_date else "",
        }

    @staticmethod
    def query_overdue_preventives(*, company, site=None):
        queryset = MaintenancePlan.objects.filter(company=company, next_due_date__lt=timezone.localdate(), is_active=True)
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return list(queryset.select_related("asset", "operational_site").order_by("next_due_date")[:10])

    @staticmethod
    def query_backlog(*, company, site=None):
        queryset = ServiceOrder.objects.filter(client__company=company, status__in=["open", "in_progress"])
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return list(queryset.select_related("asset", "operational_site").order_by("-priority", "opened_at")[:20])

    @staticmethod
    def query_technician_performance(*, company):
        return TechnicianPerformance.objects.filter(company=company).select_related("technician").order_by("-profit_generated", "-jobs_completed")[:10]

    @staticmethod
    def query_profitability_payload(*, company):
        return ExecutiveAnalyticsService.get_profitability_payload(company=company)

    @staticmethod
    def query_work_order_costs(*, company, work_order=None):
        if work_order is not None:
            orders = [work_order]
        else:
            period = ExecutiveAnalyticsService.get_period(reference_date=timezone.localdate(), period_type=OperationalMetrics.PeriodType.MONTHLY)
            orders = list(
                ServiceOrder.objects.filter(
                    client__company=company,
                    opened_at__date__gte=period.start,
                    opened_at__date__lte=period.end,
                ).select_related("client", "asset", "maintenance_contract")[:30]
            )
        order_ids = [order.id for order in orders]
        revenue_map = ExecutiveAnalyticsService._order_revenue_map(company, ExecutiveAnalyticsService.get_period(), orders)
        cost_map = ExecutiveAnalyticsService._order_cost_map(order_ids)
        return [
            {
                "work_order_id": str(order.public_id),
                "order_number": order.order_number,
                "revenue": revenue_map.get(order.id, Decimal("0.00")),
                "cost": cost_map.get(order.id, Decimal("0.00")),
            }
            for order in orders
        ]

    @staticmethod
    def query_parts_consumption_cost(*, company, work_order=None):
        queryset = StockMovement.objects.filter(company=company, movement_type__in=[StockMovement.MovementType.OUTBOUND, StockMovement.MovementType.RESERVED]).select_related("part", "service_order")
        if work_order is not None:
            queryset = queryset.filter(service_order=work_order)
        movements = []
        for movement in queryset[:50]:
            unit_cost = Decimal(str(getattr(movement.part, "unit_cost", 0) or 0))
            movements.append(
                {
                    "service_order_id": str(movement.service_order.public_id) if movement.service_order_id else "",
                    "part_code": movement.part.code,
                    "quantity": movement.quantity,
                    "total_cost": unit_cost * movement.quantity,
                }
            )
        return movements

    @staticmethod
    def query_technician_profitability(*, company):
        return TechnicianPerformance.objects.filter(company=company).select_related("technician").order_by("profit_generated", "-jobs_completed")[:15]

    @staticmethod
    def query_route_cost_impact(*, company, site=None):
        period = ExecutiveAnalyticsService.get_period(reference_date=timezone.localdate(), period_type=OperationalMetrics.PeriodType.MONTHLY)
        orders = list(
            ServiceOrder.objects.filter(
                client__company=company,
                opened_at__date__gte=period.start,
                opened_at__date__lte=period.end,
            ).select_related("operational_site")
        )
        if site is not None:
            orders = [order for order in orders if order.operational_site_id == site.id]
        order_ids = [order.id for order in orders]
        travel_map = ExecutiveAnalyticsService._travel_cost_for_orders(order_ids)
        revenue_map = ExecutiveAnalyticsService._order_revenue_map(company, period, orders)
        rows = {}
        for order in orders:
            key = order.operational_site_id
            rows.setdefault(
                key,
                {
                    "site_id": key,
                    "site_name": order.operational_site.name,
                    "travel_cost": Decimal("0.00"),
                    "revenue": Decimal("0.00"),
                    "total_orders": 0,
                },
            )
            rows[key]["travel_cost"] += travel_map.get(order.id, Decimal("0.00"))
            rows[key]["revenue"] += revenue_map.get(order.id, Decimal("0.00"))
            rows[key]["total_orders"] += 1
        return list(rows.values())

    @staticmethod
    def query_budget_vs_execution_cost(*, company):
        period = ExecutiveAnalyticsService.get_period(reference_date=timezone.localdate(), period_type=OperationalMetrics.PeriodType.MONTHLY)
        orders = list(
            ServiceOrder.objects.filter(
                client__company=company,
                opened_at__date__gte=period.start,
                opened_at__date__lte=period.end,
            ).select_related("client")
        )
        quotes = {
            quote.work_order_id: quote
            for quote in ServiceQuote.objects.filter(company=company, work_order_id__in=[order.id for order in orders], status=ServiceQuote.Status.APPROVED)
        }
        cost_map = ExecutiveAnalyticsService._order_cost_map([order.id for order in orders])
        return [
            {
                "order_number": order.order_number,
                "approved_quote_value": getattr(quotes.get(order.id), "total_value", Decimal("0.00")),
                "execution_cost": cost_map.get(order.id, Decimal("0.00")),
            }
            for order in orders
            if order.id in quotes
        ]

    @staticmethod
    def query_recurring_contract_effort(*, company):
        period = ExecutiveAnalyticsService.get_period(reference_date=timezone.localdate(), period_type=OperationalMetrics.PeriodType.MONTHLY)
        rows = []
        for contract in MaintenanceContract.objects.filter(company=company, status=MaintenanceContract.Status.ACTIVE).select_related("client", "operational_site")[:20]:
            orders = list(
                ServiceOrder.objects.filter(
                    maintenance_contract=contract,
                    opened_at__date__gte=period.start,
                    opened_at__date__lte=period.end,
                )
            )
            rows.append(
                {
                    "contract_number": contract.contract_number,
                    "contract_public_id": str(contract.public_id),
                    "client_name": contract.client.display_name,
                    "contract_value": contract.contract_value,
                    "total_orders": len(orders),
                    "correctives": sum(1 for order in orders if order.maintenance_type == ServiceOrder.MaintenanceType.CORRECTIVE),
                }
            )
        return rows

    @staticmethod
    def create_profitability_recommendation(*, recommendation_type, target_entity_type, target_entity_id, payload=None):
        return {
            "recommendation_type": recommendation_type,
            "target_entity_type": target_entity_type,
            "target_entity_id": target_entity_id,
            "payload": payload or {},
        }

    @staticmethod
    def create_profitability_action_proposal(*, action_type, target_entity, target_entity_id, payload=None):
        return {
            "action_type": action_type,
            "target_entity": target_entity,
            "target_entity_id": target_entity_id,
            "payload": payload or {},
        }

    @staticmethod
    def flag_profitability_attention(*, focus_type, target_entity_type, target_entity_id, payload=None):
        return {
            "focus_type": focus_type,
            "target_entity_type": target_entity_type,
            "target_entity_id": target_entity_id,
            "payload": payload or {},
        }

    @staticmethod
    def query_failure_timeseries(*, company, asset=None, site=None, days=35):
        queryset = FailureEvent.objects.filter(
            asset__operational_site__maintenance_client__company=company,
            detected_at__date__gte=timezone.localdate() - timedelta(days=days - 1),
        )
        if asset is not None:
            queryset = queryset.filter(asset=asset)
        if site is not None:
            queryset = queryset.filter(asset__operational_site=site)
        return list(
            queryset.extra(select={"event_date": "date(detected_at)"})
            .values("event_date")
            .annotate(total=Count("id"))
            .order_by("event_date")
        )

    @staticmethod
    def query_work_order_timeseries(*, company, site=None, days=35):
        queryset = ServiceOrder.objects.filter(
            client__company=company,
            opened_at__date__gte=timezone.localdate() - timedelta(days=days - 1),
        )
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return list(
            queryset.extra(select={"event_date": "date(opened_at)"})
            .values("event_date")
            .annotate(
                total=Count("id"),
                correctives=Count("id", filter=Q(maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE)),
            )
            .order_by("event_date")
        )

    @staticmethod
    def query_backlog_metrics(*, company, site=None):
        queryset = ServiceOrder.objects.filter(client__company=company, status__in=["open", "scheduled", "in_progress", "waiting_parts", "waiting_quote_approval", "on_hold"])
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return {
            "open_backlog": queryset.count(),
            "critical_backlog": queryset.filter(priority__in=[ServiceOrder.Priority.HIGH, ServiceOrder.Priority.URGENT]).count(),
            "corrective_backlog": queryset.filter(maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE).count(),
        }

    @staticmethod
    def query_sla_metrics(*, company, site=None):
        queryset = ServiceOrder.objects.filter(client__company=company)
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        queryset = queryset.exclude(started_at__isnull=True, completed_at__isnull=True)
        compliant = 0
        violated = 0
        for order in queryset[:200]:
            response_minutes = max(int((((order.started_at or order.completed_at) - order.opened_at).total_seconds()) // 60), 0)
            target = ExecutiveAnalyticsService.SLA_TARGET_MINUTES.get(order.priority, ExecutiveAnalyticsService.SLA_TARGET_MINUTES[ServiceOrder.Priority.MEDIUM])
            if response_minutes <= target:
                compliant += 1
            else:
                violated += 1
        total = compliant + violated
        return {
            "compliant": compliant,
            "violated": violated,
            "compliance_rate": (Decimal(compliant) * Decimal("100") / Decimal(total)).quantize(Decimal("0.01")) if total else Decimal("0.00"),
        }

    @staticmethod
    def query_parts_consumption_metrics(*, company, part=None, site=None, days=35):
        queryset = StockMovement.objects.filter(
            company=company,
            movement_type__in=[StockMovement.MovementType.OUTBOUND, StockMovement.MovementType.RESERVED],
            occurred_at__date__gte=timezone.localdate() - timedelta(days=days - 1),
        ).select_related("part", "operational_site")
        if part is not None:
            queryset = queryset.filter(part=part)
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        rows = []
        for movement in queryset[:100]:
            unit_cost = Decimal(str(getattr(movement.part, "unit_cost", 0) or 0))
            rows.append(
                {
                    "part_public_id": str(movement.part.public_id),
                    "part_code": movement.part.code,
                    "site_id": movement.operational_site_id,
                    "quantity": movement.quantity,
                    "cost": unit_cost * movement.quantity,
                    "occurred_at": movement.occurred_at,
                }
            )
        return rows

    @staticmethod
    def query_technician_performance_metrics(*, company, technician=None):
        queryset = TechnicianPerformance.objects.filter(company=company).select_related("technician").order_by("-period_start")
        if technician is not None:
            queryset = queryset.filter(technician=technician)
        return list(queryset[:20])

    @staticmethod
    def query_marketplace_operational_metrics(*, company, site=None):
        requests = TechnicianServiceRequest.objects.filter(requester_company=company)
        if site is not None:
            requests = requests.filter(related_site=site)
        offers = TechnicianServiceOffer.objects.filter(service_request__requester_company=company)
        assignments = TechnicianAssignment.objects.filter(technician_service_request__requester_company=company)
        return {
            "open_requests": requests.filter(status__in=[TechnicianServiceRequest.Status.OPEN, TechnicianServiceRequest.Status.MATCHING, TechnicianServiceRequest.Status.OFFERS_RECEIVED]).count(),
            "offers_received": offers.count(),
            "offers_accepted": offers.filter(status=TechnicianServiceOffer.Status.ACCEPTED).count(),
            "assignments_cancelled": assignments.filter(assignment_status=TechnicianAssignment.AssignmentStatus.CANCELLED).count(),
        }

    @staticmethod
    def query_contract_profitability_metrics(*, company, contract=None, client=None):
        rows = ContractProfitability.objects.filter(company=company).select_related("contract", "contract__client").order_by("-period_start")
        if contract is not None:
            rows = rows.filter(contract=contract)
        if client is not None:
            rows = rows.filter(contract__client=client)
        return list(rows[:20])

    @staticmethod
    def query_baseline_comparison(*, current_value, baseline_value):
        current_decimal = Decimal(str(current_value or 0))
        baseline_decimal = Decimal(str(baseline_value or 0))
        if baseline_decimal == 0:
            return {"current": current_decimal, "baseline": baseline_decimal, "deviation_percent": Decimal("0.00")}
        return {
            "current": current_decimal,
            "baseline": baseline_decimal,
            "deviation_percent": (((current_decimal - baseline_decimal) * Decimal("100")) / baseline_decimal).quantize(Decimal("0.01")),
        }

    @staticmethod
    def create_anomaly_recommendation(*, recommendation_type, target_entity_type, target_entity_id, payload=None):
        return {
            "recommendation_type": recommendation_type,
            "target_entity_type": target_entity_type,
            "target_entity_id": target_entity_id,
            "payload": payload or {},
        }

    @staticmethod
    def create_anomaly_action_proposal(*, action_type, target_entity, target_entity_id, payload=None):
        return {
            "action_type": action_type,
            "target_entity": target_entity,
            "target_entity_id": target_entity_id,
            "payload": payload or {},
        }

    @staticmethod
    def flag_anomaly_attention(*, focus_type, target_entity_type, target_entity_id, payload=None):
        return {
            "focus_type": focus_type,
            "target_entity_type": target_entity_type,
            "target_entity_id": target_entity_id,
            "payload": payload or {},
        }

    @staticmethod
    def create_schedule_recommendation(*, recommendation_type, technician=None, payload=None):
        return {
            "recommendation_type": recommendation_type,
            "technician_id": getattr(technician, "id", None),
            "payload": payload or {},
        }

    @staticmethod
    def create_schedule_action_proposal(*, action_type, technician=None, payload=None):
        return {
            "action_type": action_type,
            "technician_id": getattr(technician, "id", None),
            "payload": payload or {},
        }

    @staticmethod
    def create_marketplace_recommendation(*, recommendation_type, service_request, payload=None):
        return {
            "recommendation_type": recommendation_type,
            "service_request_public_id": str(service_request.public_id),
            "payload": payload or {},
        }

    @staticmethod
    def create_marketplace_action_proposal(*, action_type, service_request, payload=None):
        return {
            "action_type": action_type,
            "service_request_public_id": str(service_request.public_id),
            "payload": payload or {},
        }

    @staticmethod
    def simulate_assignment_candidate(*, service_request, technician_profile):
        return {
            "service_request_public_id": str(service_request.public_id),
            "technician_profile_public_id": str(technician_profile.public_id),
            "technician_name": technician_profile.display_name,
        }

    @staticmethod
    def simulate_alternative_allocation(*, service_request, candidates):
        return {
            "service_request_public_id": str(service_request.public_id),
            "candidate_count": len(candidates),
            "candidate_names": [candidate.technician_profile.display_name for candidate in candidates[:3]],
        }

    @staticmethod
    def simulate_route_reorder(*, visits, target_date):
        routing_service = get_technician_routing_service()
        previous = None
        total = 0
        for visit in visits:
            total += routing_service._estimate_travel_minutes(previous, visit)
            previous = visit
        return {"visit_count": len(visits), "travel_minutes": total, "date": target_date.isoformat()}

    @staticmethod
    def simulate_visit_reassignment(*, visit, technician):
        return {
            "visit_public_id": str(visit.public_id),
            "technician_id": getattr(technician, "id", None),
            "estimated_duration_minutes": visit.estimated_duration_minutes,
        }
