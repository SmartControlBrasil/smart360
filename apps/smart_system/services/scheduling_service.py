from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.access_control_center.services.access_service import AccessAuditService
from apps.ai_shared.interfaces.triggers import get_scheduling_agent_trigger_service
from apps.marketplace_technicians.models import (
    TechnicianAssignment,
    TechnicianMatchingRecord,
    TechnicianProfile,
    TechnicianServiceRegion,
)
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import (
    MaintenancePlan,
    RoutePlan,
    ScheduledVisit,
    ServiceOrder,
    TechnicianAvailabilityWindow,
    TechnicianSchedule,
)

User = get_user_model()


@dataclass
class SchedulingConflict:
    code: str
    message: str
    visit_public_id: str | None = None


class TechnicianRoutingService:
    DEFAULT_START_TIME = time(hour=8, minute=0)
    DEFAULT_END_TIME = time(hour=18, minute=0)
    DEFAULT_TRAVEL_SAME_SITE = 10
    DEFAULT_TRAVEL_SAME_CITY = 25
    DEFAULT_TRAVEL_SAME_STATE = 55
    DEFAULT_TRAVEL_OTHER_STATE = 95

    PRIORITY_WEIGHTS = {
        ScheduledVisit.Priority.URGENT: 100,
        ScheduledVisit.Priority.HIGH: 80,
        ScheduledVisit.Priority.MEDIUM: 60,
        ScheduledVisit.Priority.LOW: 40,
    }

    @classmethod
    def refresh_plannable_visits(cls, *, schedule_date: date, company=None, site=None) -> list[ScheduledVisit]:
        visits: list[ScheduledVisit] = []
        visits.extend(cls._sync_service_orders(schedule_date=schedule_date, company=company, site=site))
        visits.extend(cls._sync_marketplace_assignments(schedule_date=schedule_date, company=company, site=site))
        visits.extend(cls._sync_preventive_due_visits(schedule_date=schedule_date, company=company, site=site))
        return visits

    @classmethod
    def _base_order_queryset(cls, *, schedule_date: date, company=None, site=None):
        queryset = ServiceOrder.objects.select_related(
            "client",
            "client__company",
            "operational_site",
            "asset",
            "maintenance_plan",
            "assigned_to",
        ).filter(
            status__in=[
                ServiceOrder.Status.OPEN,
                ServiceOrder.Status.SCHEDULED,
                ServiceOrder.Status.IN_PROGRESS,
                ServiceOrder.Status.ON_HOLD,
            ]
        )
        queryset = queryset.filter(
            Q(scheduled_start__date=schedule_date)
            | Q(scheduled_start__isnull=True, opened_at__date=schedule_date)
        )
        if company is not None:
            queryset = queryset.filter(client__company=company)
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return queryset

    @classmethod
    def _sync_service_orders(cls, *, schedule_date: date, company=None, site=None) -> list[ScheduledVisit]:
        visits = []
        for order in cls._base_order_queryset(schedule_date=schedule_date, company=company, site=site):
            visit, _ = ScheduledVisit.objects.update_or_create(
                work_order=order,
                defaults={
                    "company": order.client.company,
                    "operational_site": order.operational_site,
                    "asset": order.asset,
                    "technician": order.assigned_to,
                    "technician_profile": cls._resolve_profile(order.assigned_to),
                    "source_type": ScheduledVisit.SourceType.WORK_ORDER,
                    "title": order.title or order.order_number,
                    "scheduled_date": schedule_date,
                    "scheduled_start": order.scheduled_start,
                    "scheduled_end": order.scheduled_end,
                    "window_start": cls._time_or_default(order.scheduled_start, cls.DEFAULT_START_TIME),
                    "window_end": cls._time_or_default(order.scheduled_end, cls.DEFAULT_END_TIME),
                    "estimated_duration_minutes": cls._estimate_order_duration(order),
                    "priority": cls._map_order_priority(order.priority),
                    "status": cls._map_order_status(order.status, technician=order.assigned_to),
                    "city": order.operational_site.city,
                    "state": order.operational_site.state,
                    "location_label": order.operational_site.name,
                    "metadata": {
                        "source": "service_order",
                        "order_number": order.order_number,
                    },
                },
            )
            visits.append(visit)
        return visits

    @classmethod
    def _sync_marketplace_assignments(cls, *, schedule_date: date, company=None, site=None) -> list[ScheduledVisit]:
        queryset = TechnicianAssignment.objects.select_related(
            "technician_service_request",
            "technician_service_request__requester_company",
            "technician_service_request__related_site",
            "technician_service_request__related_asset",
            "technician_service_request__related_service_order",
            "technician_profile",
            "technician_profile__user",
        ).filter(
            assignment_status__in=[
                TechnicianAssignment.AssignmentStatus.ASSIGNED,
                TechnicianAssignment.AssignmentStatus.ACCEPTED,
                TechnicianAssignment.AssignmentStatus.IN_PROGRESS,
            ]
        )
        queryset = queryset.filter(
            Q(technician_service_request__requested_date__date=schedule_date)
            | Q(assigned_at__date=schedule_date)
        )
        if company is not None:
            queryset = queryset.filter(technician_service_request__requester_company=company)
        if site is not None:
            queryset = queryset.filter(technician_service_request__related_site=site)

        visits = []
        for assignment in queryset:
            request = assignment.technician_service_request
            related_order = request.related_service_order
            visit, _ = ScheduledVisit.objects.update_or_create(
                service_assignment=assignment,
                defaults={
                    "company": request.requester_company,
                    "operational_site": request.related_site,
                    "asset": request.related_asset,
                    "work_order": related_order,
                    "technician": assignment.technician_profile.user,
                    "technician_profile": assignment.technician_profile,
                    "source_type": ScheduledVisit.SourceType.MARKETPLACE,
                    "title": request.title,
                    "scheduled_date": schedule_date,
                    "scheduled_start": request.requested_date,
                    "scheduled_end": cls._derive_end_at(request.requested_date, 120),
                    "window_start": cls._time_or_default(request.requested_date, cls.DEFAULT_START_TIME),
                    "window_end": cls.DEFAULT_END_TIME,
                    "estimated_duration_minutes": 120,
                    "priority": cls._map_marketplace_priority(request.priority),
                    "status": cls._map_assignment_status(assignment.assignment_status),
                    "city": request.city,
                    "state": request.state,
                    "location_label": request.location_label or getattr(request.related_site, "name", ""),
                    "metadata": {
                        "source": "marketplace_assignment",
                        "request_public_id": str(request.public_id),
                    },
                },
            )
            visits.append(visit)
        return visits

    @classmethod
    def _sync_preventive_due_visits(cls, *, schedule_date: date, company=None, site=None) -> list[ScheduledVisit]:
        queryset = MaintenancePlan.objects.select_related("company", "operational_site", "asset").filter(
            is_active=True,
            next_due_date=schedule_date,
        )
        if company is not None:
            queryset = queryset.filter(company=company)
        if site is not None:
            queryset = queryset.filter(operational_site=site)

        visits = []
        for plan in queryset:
            visit, _ = ScheduledVisit.objects.update_or_create(
                maintenance_plan=plan,
                work_order__isnull=True,
                defaults={
                    "company": plan.company,
                    "operational_site": plan.operational_site,
                    "asset": plan.asset,
                    "technician": None,
                    "technician_profile": None,
                    "source_type": ScheduledVisit.SourceType.PREVENTIVE,
                    "title": plan.name,
                    "scheduled_date": schedule_date,
                    "scheduled_start": datetime.combine(schedule_date, cls.DEFAULT_START_TIME, tzinfo=timezone.get_current_timezone()),
                    "scheduled_end": datetime.combine(schedule_date, cls.DEFAULT_START_TIME, tzinfo=timezone.get_current_timezone())
                    + timedelta(minutes=plan.estimated_duration_minutes or 90),
                    "window_start": cls.DEFAULT_START_TIME,
                    "window_end": cls.DEFAULT_END_TIME,
                    "estimated_duration_minutes": plan.estimated_duration_minutes or 90,
                    "priority": ScheduledVisit.Priority.MEDIUM,
                    "status": ScheduledVisit.Status.PENDING_ASSIGNMENT,
                    "city": getattr(plan.operational_site, "city", ""),
                    "state": getattr(plan.operational_site, "state", ""),
                    "location_label": getattr(plan.operational_site, "name", ""),
                    "metadata": {
                        "source": "maintenance_plan",
                        "plan_public_id": str(plan.public_id),
                    },
                },
            )
            visits.append(visit)
        return visits

    @classmethod
    def generate_route_for_technician(cls, *, technician, schedule_date: date, company, site=None, generated_by=None):
        cls.refresh_plannable_visits(schedule_date=schedule_date, company=company, site=site)
        visits = list(
            ScheduledVisit.objects.select_related("operational_site", "asset", "company", "work_order")
            .filter(company=company, technician=technician, scheduled_date=schedule_date)
            .order_by("route_order", "scheduled_start", "created_at")
        )
        if site is not None:
            visits = [visit for visit in visits if visit.operational_site_id == site.id]

        ordered = cls._order_visits(visits)
        route_plan, _ = RoutePlan.objects.update_or_create(
            company=company,
            technician=technician,
            date=schedule_date,
            defaults={
                "operational_site": site,
                "technician_profile": cls._resolve_profile(technician),
                "optimization_status": RoutePlan.OptimizationStatus.GENERATED,
            },
        )
        schedule, _ = TechnicianSchedule.objects.update_or_create(
            company=company,
            technician=technician,
            date=schedule_date,
            defaults={
                "operational_site": site,
                "technician_profile": cls._resolve_profile(technician),
            },
        )

        running_start = datetime.combine(schedule_date, cls.DEFAULT_START_TIME, tzinfo=timezone.get_current_timezone())
        total_duration = 0
        total_travel = 0
        previous = None
        for index, visit in enumerate(ordered, start=1):
            travel = cls._estimate_travel_minutes(previous, visit)
            start_at = visit.scheduled_start or (running_start + timedelta(minutes=travel))
            if visit.window_start:
                window_dt = datetime.combine(schedule_date, visit.window_start, tzinfo=timezone.get_current_timezone())
                if start_at < window_dt:
                    start_at = window_dt
            end_at = start_at + timedelta(minutes=visit.estimated_duration_minutes)
            visit.route_order = index
            visit.estimated_travel_minutes = travel
            visit.scheduled_start = start_at
            visit.scheduled_end = end_at
            visit.route_plan = route_plan
            visit.technician_schedule = schedule
            visit.conflict_flags = cls.detect_visit_conflicts(visit=visit, other_visits=ordered)
            visit.save(
                update_fields=[
                    "route_order",
                    "estimated_travel_minutes",
                    "scheduled_start",
                    "scheduled_end",
                    "route_plan",
                    "technician_schedule",
                    "conflict_flags",
                    "updated_at",
                ]
            )
            total_duration += visit.estimated_duration_minutes
            total_travel += travel
            running_start = end_at
            previous = visit

        route_plan.total_stops = len(ordered)
        route_plan.total_estimated_duration = total_duration
        route_plan.total_estimated_travel = total_travel
        route_plan.route_summary = {
            "generated_at": timezone.now().isoformat(),
            "stops": [
                {
                    "visit_public_id": str(visit.public_id),
                    "title": visit.title,
                    "route_order": visit.route_order,
                    "scheduled_start": visit.scheduled_start.isoformat() if visit.scheduled_start else "",
                    "scheduled_end": visit.scheduled_end.isoformat() if visit.scheduled_end else "",
                }
                for visit in ordered
            ],
        }
        route_plan.save(
            update_fields=[
                "total_stops",
                "total_estimated_duration",
                "total_estimated_travel",
                "route_summary",
                "optimization_status",
                "updated_at",
            ]
        )

        schedule.total_jobs = len(ordered)
        schedule.total_estimated_duration = total_duration
        schedule.total_estimated_travel = total_travel
        schedule.total_conflicts = sum(1 for visit in ordered if visit.conflict_flags)
        schedule.metadata = {
            "route_plan_public_id": str(route_plan.public_id),
            "generated_at": timezone.now().isoformat(),
        }
        schedule.save(
            update_fields=[
                "total_jobs",
                "total_estimated_duration",
                "total_estimated_travel",
                "total_conflicts",
                "metadata",
                "updated_at",
            ]
        )
        SystemEventService.log_system_event(
            event_type="route.generated",
            source_module="smart_system",
            message="Route plan generated for technician.",
            entity_type="route_plan",
            entity_id=str(route_plan.public_id),
            user=generated_by,
            company=company,
            site=site,
            payload={
                "technician_id": technician.id,
                "date": schedule_date.isoformat(),
                "stops": len(ordered),
                "travel_minutes": total_travel,
            },
        )
        if generated_by:
            AccessAuditService.log(
                user=generated_by,
                action="route_generated",
                domain="scheduling",
                decision="allow",
                resource_type="route_plan",
                resource_id=str(route_plan.public_id),
                company=company,
                site=site,
                metadata={"date": schedule_date.isoformat(), "technician_id": technician.id},
            )
        return route_plan

    @classmethod
    def reorder_route(cls, *, technician, company, schedule_date: date, ordered_visit_public_ids: list[str], updated_by=None):
        visits = {
            str(visit.public_id): visit
            for visit in ScheduledVisit.objects.filter(
                company=company,
                technician=technician,
                scheduled_date=schedule_date,
            )
        }
        with transaction.atomic():
            previous = None
            current_start = datetime.combine(schedule_date, cls.DEFAULT_START_TIME, tzinfo=timezone.get_current_timezone())
            total_travel = 0
            for index, public_id in enumerate(ordered_visit_public_ids, start=1):
                visit = visits.get(str(public_id))
                if visit is None:
                    continue
                travel = cls._estimate_travel_minutes(previous, visit)
                start_at = current_start + timedelta(minutes=travel)
                end_at = start_at + timedelta(minutes=visit.estimated_duration_minutes)
                visit.route_order = index
                visit.estimated_travel_minutes = travel
                visit.scheduled_start = start_at
                visit.scheduled_end = end_at
                visit.conflict_flags = cls.detect_visit_conflicts(visit=visit, other_visits=list(visits.values()))
                visit.save(
                    update_fields=[
                        "route_order",
                        "estimated_travel_minutes",
                        "scheduled_start",
                        "scheduled_end",
                        "conflict_flags",
                        "updated_at",
                    ]
                )
                total_travel += travel
                previous = visit
                current_start = end_at
        SystemEventService.log_system_event(
            event_type="schedule.visit.updated",
            source_module="smart_system",
            message="Scheduled route reordered manually.",
            entity_type="scheduled_visit_route",
            entity_id=f"{technician.id}:{schedule_date.isoformat()}",
            user=updated_by,
            company=company,
            payload={"ordered_ids": ordered_visit_public_ids},
        )
        try:
            scheduling_agent_trigger_service = get_scheduling_agent_trigger_service()
            scheduling_agent_trigger_service.run_technician_analysis(
                company=company,
                technician=technician,
                target_date=schedule_date,
                trigger_type="event",
            )
        except Exception:
            pass

    @classmethod
    def detect_visit_conflicts(cls, *, visit: ScheduledVisit, other_visits: list[ScheduledVisit] | None = None) -> list[str]:
        conflicts: list[str] = []
        availability = cls._get_availability_for_visit(visit)
        if availability and not availability.is_available:
            conflicts.append("technician_unavailable")
        if availability and availability.blocked_date == visit.scheduled_date:
            conflicts.append("blocked_period")
        if visit.window_start and visit.scheduled_start and visit.scheduled_start.time() < visit.window_start:
            conflicts.append("before_window")
        if visit.window_end and visit.scheduled_end and visit.scheduled_end.time() > visit.window_end:
            conflicts.append("after_window")
        comparable = other_visits or []
        for other in comparable:
            if other.pk == visit.pk or other.technician_id != visit.technician_id:
                continue
            if not visit.scheduled_start or not visit.scheduled_end or not other.scheduled_start or not other.scheduled_end:
                continue
            if visit.scheduled_start < other.scheduled_end and visit.scheduled_end > other.scheduled_start:
                conflicts.append("overlap")
                break
        if availability:
            same_day_jobs = sum(1 for item in comparable if item.technician_id == visit.technician_id)
            if availability.max_daily_jobs and same_day_jobs > availability.max_daily_jobs:
                conflicts.append("daily_jobs_exceeded")
            same_day_minutes = sum(item.estimated_duration_minutes for item in comparable if item.technician_id == visit.technician_id)
            if availability.max_daily_hours and same_day_minutes > availability.max_daily_hours * 60:
                conflicts.append("daily_hours_exceeded")
        if conflicts:
            SystemEventService.log_system_event(
                event_type="schedule.conflict.detected",
                source_module="smart_system",
                message="Scheduling conflict detected.",
                entity_type="scheduled_visit",
                entity_id=str(visit.public_id),
                user=None,
                company=visit.company,
                site=visit.operational_site,
                payload={"conflicts": conflicts},
            )
        return sorted(set(conflicts))

    @classmethod
    def build_unassigned_queue(cls, *, schedule_date: date, company=None, site=None):
        cls.refresh_plannable_visits(schedule_date=schedule_date, company=company, site=site)
        visits = ScheduledVisit.objects.select_related(
            "company",
            "operational_site",
            "asset",
            "work_order",
            "service_assignment",
            "maintenance_plan",
        ).filter(
            scheduled_date=schedule_date,
            technician__isnull=True,
        )
        if company is not None:
            visits = visits.filter(company=company)
        if site is not None:
            visits = visits.filter(operational_site=site)
        return [
            {
                "visit": visit,
                "suggested_technician": cls.suggest_best_technician(
                    company=visit.company,
                    site=visit.operational_site,
                    category=visit._meta.model_name if visit.source_type == ScheduledVisit.SourceType.PREVENTIVE else "",
                    city=visit.city,
                    state=visit.state,
                ),
            }
            for visit in visits.order_by("-priority", "scheduled_start", "created_at")
        ]

    @classmethod
    def suggest_best_technician(cls, *, company, site=None, category="", city="", state=""):
        profiles = TechnicianProfile.objects.select_related("user").filter(
            is_active=True,
            marketplace_status__in=[
                TechnicianProfile.MarketplaceStatus.AVAILABLE,
                TechnicianProfile.MarketplaceStatus.BUSY,
            ],
        )
        if site is not None:
            profiles = profiles.filter(
                Q(company=company) | Q(company__isnull=True) | Q(service_regions__service_region__city__iexact=site.city)
            ).distinct()
        scored = []
        for profile in profiles:
            region_bonus = cls._profile_region_score(profile, city=city or getattr(site, "city", ""), state=state or getattr(site, "state", ""))
            load_penalty = min(profile.user.scheduled_visits.filter(scheduled_date=timezone.localdate()).count() * 6, 30)
            rating = float(profile.rating_average or Decimal("0"))
            score = max(0, 40 + region_bonus + min(profile.completed_jobs_count, 25) + int(rating * 5) - load_penalty)
            scored.append((score, profile))
        scored.sort(key=lambda item: (-item[0], -(item[1].completed_jobs_count), -float(item[1].rating_average or 0)))
        return scored[0][1] if scored else None

    @classmethod
    def get_technician_agenda(cls, *, technician, schedule_date: date, company=None, site=None):
        cls.refresh_plannable_visits(schedule_date=schedule_date, company=company, site=site)
        queryset = ScheduledVisit.objects.select_related(
            "company",
            "operational_site",
            "asset",
            "work_order",
            "service_assignment",
            "route_plan",
        ).filter(technician=technician, scheduled_date=schedule_date)
        if company is not None:
            queryset = queryset.filter(company=company)
        if site is not None:
            queryset = queryset.filter(operational_site=site)
        return list(queryset.order_by("route_order", "scheduled_start", "created_at"))

    @classmethod
    def _order_visits(cls, visits: list[ScheduledVisit]) -> list[ScheduledVisit]:
        def sort_key(visit: ScheduledVisit):
            priority_score = cls.PRIORITY_WEIGHTS.get(visit.priority, 0)
            window_key = visit.window_start or cls.DEFAULT_START_TIME
            city_key = visit.city or ""
            return (-priority_score, window_key, city_key, visit.title)

        return sorted(visits, key=sort_key)

    @classmethod
    def _estimate_travel_minutes(cls, previous: ScheduledVisit | None, current: ScheduledVisit) -> int:
        if previous is None:
            return 0
        if previous.operational_site_id and current.operational_site_id and previous.operational_site_id == current.operational_site_id:
            return cls.DEFAULT_TRAVEL_SAME_SITE
        if previous.city and current.city and previous.city.lower() == current.city.lower():
            return cls.DEFAULT_TRAVEL_SAME_CITY
        if previous.state and current.state and previous.state.lower() == current.state.lower():
            return cls.DEFAULT_TRAVEL_SAME_STATE
        return cls.DEFAULT_TRAVEL_OTHER_STATE

    @classmethod
    def _estimate_order_duration(cls, order: ServiceOrder) -> int:
        if order.maintenance_plan and order.maintenance_plan.estimated_duration_minutes:
            return order.maintenance_plan.estimated_duration_minutes
        if order.maintenance_type == ServiceOrder.MaintenanceType.PREVENTIVE:
            return 90
        if order.priority == ServiceOrder.Priority.URGENT:
            return 180
        return 120

    @classmethod
    def _time_or_default(cls, value: datetime | None, default: time) -> time:
        if value is None:
            return default
        return timezone.localtime(value).time() if timezone.is_aware(value) else value.time()

    @classmethod
    def _derive_end_at(cls, start: datetime | None, duration: int) -> datetime | None:
        if start is None:
            return None
        return start + timedelta(minutes=duration)

    @classmethod
    def _map_order_priority(cls, priority: str) -> str:
        mapping = {
            ServiceOrder.Priority.LOW: ScheduledVisit.Priority.LOW,
            ServiceOrder.Priority.MEDIUM: ScheduledVisit.Priority.MEDIUM,
            ServiceOrder.Priority.HIGH: ScheduledVisit.Priority.HIGH,
            ServiceOrder.Priority.URGENT: ScheduledVisit.Priority.URGENT,
        }
        return mapping.get(priority, ScheduledVisit.Priority.MEDIUM)

    @classmethod
    def _map_marketplace_priority(cls, priority: str) -> str:
        mapping = {
            "low": ScheduledVisit.Priority.LOW,
            "medium": ScheduledVisit.Priority.MEDIUM,
            "high": ScheduledVisit.Priority.HIGH,
            "urgent": ScheduledVisit.Priority.URGENT,
        }
        return mapping.get(priority, ScheduledVisit.Priority.MEDIUM)

    @classmethod
    def _map_order_status(cls, status: str, technician=None) -> str:
        mapping = {
            ServiceOrder.Status.OPEN: ScheduledVisit.Status.PENDING_ASSIGNMENT if technician is None else ScheduledVisit.Status.SCHEDULED,
            ServiceOrder.Status.SCHEDULED: ScheduledVisit.Status.SCHEDULED,
            ServiceOrder.Status.IN_PROGRESS: ScheduledVisit.Status.IN_PROGRESS,
            ServiceOrder.Status.COMPLETED: ScheduledVisit.Status.COMPLETED,
            ServiceOrder.Status.CANCELLED: ScheduledVisit.Status.CANCELLED,
        }
        return mapping.get(status, ScheduledVisit.Status.SCHEDULED)

    @classmethod
    def _map_assignment_status(cls, status: str) -> str:
        mapping = {
            TechnicianAssignment.AssignmentStatus.ASSIGNED: ScheduledVisit.Status.SCHEDULED,
            TechnicianAssignment.AssignmentStatus.ACCEPTED: ScheduledVisit.Status.CONFIRMED,
            TechnicianAssignment.AssignmentStatus.IN_PROGRESS: ScheduledVisit.Status.IN_PROGRESS,
            TechnicianAssignment.AssignmentStatus.COMPLETED: ScheduledVisit.Status.COMPLETED,
            TechnicianAssignment.AssignmentStatus.CANCELLED: ScheduledVisit.Status.CANCELLED,
        }
        return mapping.get(status, ScheduledVisit.Status.SCHEDULED)

    @classmethod
    def _resolve_profile(cls, technician):
        if technician is None:
            return None
        return TechnicianProfile.objects.filter(user=technician).first()

    @classmethod
    def _get_availability_for_visit(cls, visit: ScheduledVisit):
        queryset = TechnicianAvailabilityWindow.objects.filter(
            company=visit.company,
            technician=visit.technician,
        )
        if visit.operational_site_id:
            queryset = queryset.filter(Q(operational_site=visit.operational_site) | Q(operational_site__isnull=True))
        blocked = queryset.filter(blocked_date=visit.scheduled_date).order_by("-is_available").first()
        if blocked:
            return blocked
        return queryset.filter(weekday=visit.scheduled_date.isoweekday()).order_by("-is_available").first()

    @classmethod
    def _profile_region_score(cls, profile: TechnicianProfile, *, city: str, state: str) -> int:
        if not city and not state:
            return 10
        regions = TechnicianServiceRegion.objects.select_related("service_region").filter(technician_profile=profile)
        for item in regions:
            region = item.service_region
            if city and region.city and region.city.lower() == city.lower():
                return 30
            if state and region.state.lower() == state.lower():
                return 18
        return 5
