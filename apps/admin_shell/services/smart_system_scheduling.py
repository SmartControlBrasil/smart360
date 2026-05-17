from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from apps.companies.models import Membership, SiteMembership
from apps.marketplace_technicians.models import TechnicianProfile
from apps.smart_system.models import RoutePlan, ScheduledVisit, ServiceOrder, TechnicianSchedule
from apps.smart_system.services.scheduling_service import TechnicianRoutingService

User = get_user_model()


def _scope_visits(tenant_context, user=None):
    queryset = ScheduledVisit.objects.select_related(
        "company",
        "operational_site",
        "asset",
        "work_order",
        "service_assignment",
        "technician",
        "technician_profile",
        "route_plan",
    )
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    if company is not None:
        queryset = queryset.filter(company=company)
    elif user is not None and not getattr(user, "is_superuser", False):
        queryset = queryset.filter(company_id__in=Membership.objects.filter(user=user, status=Membership.Status.ACTIVE).values("company_id"))
    if site is not None:
        queryset = queryset.filter(operational_site=site)
    elif user is not None and not getattr(user, "is_superuser", False):
        allowed_sites = SiteMembership.objects.filter(user=user, status=SiteMembership.Status.ACTIVE).values("site_id")
        if allowed_sites.exists():
            queryset = queryset.filter(operational_site_id__in=allowed_sites)
    return queryset


def _scope_orders(tenant_context, user=None):
    queryset = ServiceOrder.objects.select_related("client__company", "operational_site", "asset", "assigned_to")
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    if company is not None:
        queryset = queryset.filter(client__company=company)
    elif user is not None and not getattr(user, "is_superuser", False):
        queryset = queryset.filter(client__company_id__in=Membership.objects.filter(user=user, status=Membership.Status.ACTIVE).values("company_id"))
    if site is not None:
        queryset = queryset.filter(operational_site=site)
    elif user is not None and not getattr(user, "is_superuser", False):
        allowed_sites = SiteMembership.objects.filter(user=user, status=SiteMembership.Status.ACTIVE).values("site_id")
        if allowed_sites.exists():
            queryset = queryset.filter(operational_site_id__in=allowed_sites)
    return queryset


def _scope_technicians(tenant_context):
    company = tenant_context.get("company")
    profiles = TechnicianProfile.objects.select_related("user").filter(is_active=True)
    if company is not None:
        profiles = profiles.filter(company=company) | profiles.filter(company__isnull=True)
    return profiles.distinct()


def _format_visit(visit):
    return {
        "public_id": str(visit.public_id),
        "title": visit.title,
        "company": getattr(visit.company, "name", ""),
        "site": getattr(visit.operational_site, "name", ""),
        "asset": getattr(visit.asset, "name", ""),
        "asset_code": getattr(visit.asset, "asset_tag", ""),
        "order_code": getattr(visit.work_order, "order_number", ""),
        "technician": (
            visit.technician_profile.display_name
            if visit.technician_profile
            else getattr(visit.technician, "display_name", "") or getattr(visit.technician, "email", "")
        ),
        "scheduled_date": visit.scheduled_date.strftime("%d/%m/%Y"),
        "scheduled_start": timezone.localtime(visit.scheduled_start).strftime("%H:%M") if visit.scheduled_start else "--:--",
        "scheduled_end": timezone.localtime(visit.scheduled_end).strftime("%H:%M") if visit.scheduled_end else "--:--",
        "estimated_duration_minutes": visit.estimated_duration_minutes,
        "estimated_travel_minutes": visit.estimated_travel_minutes,
        "priority": visit.get_priority_display(),
        "status": visit.get_status_display(),
        "route_order": visit.route_order,
        "location_label": visit.location_label,
        "source_type": visit.get_source_type_display(),
        "conflict_flags": list(visit.conflict_flags or []),
    }


def _format_load_card(schedule):
    technician_name = (
        schedule.technician_profile.display_name
        if schedule.technician_profile
        else schedule.technician.display_name or schedule.technician.email
    )
    return {
        "technician_id": schedule.technician_id,
        "technician_name": technician_name,
        "date": schedule.date.strftime("%d/%m/%Y"),
        "jobs": schedule.total_jobs,
        "duration_minutes": schedule.total_estimated_duration,
        "travel_minutes": schedule.total_estimated_travel,
        "conflicts": schedule.total_conflicts,
        "tone": "red" if schedule.total_conflicts else ("amber" if schedule.total_jobs >= 6 else "emerald"),
        "agenda_url": f"/app/smart-system/scheduling/technicians/{schedule.technician_id}/?date={schedule.date.isoformat()}",
    }


def get_scheduling_dashboard_context(*, tenant_context, user=None, date_value=None):
    target_date = date_value or timezone.localdate()
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    TechnicianRoutingService.refresh_plannable_visits(schedule_date=target_date, company=company, site=site)

    visits = _scope_visits(tenant_context, user=user).filter(scheduled_date=target_date)
    open_orders = _scope_orders(tenant_context, user=user).filter(status__in=[ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED])
    schedules = TechnicianSchedule.objects.select_related("technician", "technician_profile").filter(date=target_date)
    if company is not None:
        schedules = schedules.filter(company=company)
    if site is not None:
        schedules = schedules.filter(operational_site=site)
    route_plans = RoutePlan.objects.select_related("technician", "technician_profile").filter(date=target_date)
    if company is not None:
        route_plans = route_plans.filter(company=company)
    if site is not None:
        route_plans = route_plans.filter(operational_site=site)

    unassigned = visits.filter(technician__isnull=True)
    conflicts = [visit for visit in visits if visit.conflict_flags]
    completed_today = visits.filter(status=ScheduledVisit.Status.COMPLETED)

    return {
        "schedule_kpis": [
            {"label": "Visitas hoje", "value": visits.count(), "meta": "atendimentos planejados na data", "tone": "indigo"},
            {"label": "Nao alocadas", "value": unassigned.count(), "meta": "fila aguardando tecnico", "tone": "amber"},
            {"label": "Conflitos", "value": len(conflicts), "meta": "sobreposicoes ou indisponibilidades", "tone": "rose"},
            {"label": "Rotas geradas", "value": route_plans.count(), "meta": "roteiros consolidados", "tone": "emerald"},
            {"label": "OS pendentes", "value": open_orders.count(), "meta": "ordens operacionais abertas", "tone": "sky"},
        ],
        "target_date": target_date,
        "technician_load_cards": [_format_load_card(item) for item in schedules.order_by("-total_jobs", "-total_conflicts", "technician_id")],
        "today_visits": [_format_visit(item) for item in visits.order_by("route_order", "scheduled_start", "title")[:12]],
        "conflict_visits": [_format_visit(item) for item in conflicts[:8]],
        "unassigned_visits": [
            {
                **_format_visit(item["visit"]),
                "suggested_technician": (
                    item["suggested_technician"].display_name if item["suggested_technician"] else "A definir"
                ),
            }
            for item in TechnicianRoutingService.build_unassigned_queue(
                schedule_date=target_date,
                company=company,
                site=site,
            )[:8]
        ],
        "page_actions": [
            {"label": "Calendario", "href": "/app/smart-system/scheduling/calendar/"},
            {"label": "Nao alocadas", "href": "/app/smart-system/scheduling/unassigned/"},
        ],
        "operation_alerts": [
            {
                "title": "Conflitos detectados",
                "description": "Existem visitas com sobreposicao ou indisponibilidade na agenda do dia.",
                "tone": "rose",
            }
            for _ in ([1] if conflicts else [])
        ],
        "completed_today": completed_today.count(),
    }


def get_schedule_calendar_context(*, tenant_context, user=None, date_value=None):
    target_date = date_value or timezone.localdate()
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    TechnicianRoutingService.refresh_plannable_visits(schedule_date=target_date, company=company, site=site)
    start_week = target_date - timedelta(days=target_date.weekday())
    days = []
    for offset in range(7):
        day = start_week + timedelta(days=offset)
        day_visits = _scope_visits(tenant_context, user=user).filter(scheduled_date=day).order_by("scheduled_start", "route_order")
        days.append(
            {
                "date": day,
                "label": day.strftime("%d/%m"),
                "weekday": day.strftime("%A"),
                "visits": [_format_visit(item) for item in day_visits[:6]],
                "count": day_visits.count(),
            }
        )
    return {
        "calendar_days": days,
        "calendar_title": target_date.strftime("%B %Y"),
        "target_date": target_date,
    }


def get_technician_agenda_context(*, tenant_context, user=None, technician_id, date_value=None):
    target_date = date_value or timezone.localdate()
    technician = User.objects.filter(id=technician_id).first()
    if technician is None:
        return None
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    TechnicianRoutingService.generate_route_for_technician(
        technician=technician,
        schedule_date=target_date,
        company=company,
        site=site,
    )
    visits = TechnicianRoutingService.get_technician_agenda(
        technician=technician,
        schedule_date=target_date,
        company=company,
        site=site,
    )
    schedule = TechnicianSchedule.objects.filter(company=company, technician=technician, date=target_date).first()
    route_plan = RoutePlan.objects.filter(company=company, technician=technician, date=target_date).first()
    return {
        "technician": technician,
        "agenda_date": target_date,
        "agenda_visits": [_format_visit(item) for item in visits],
        "schedule_summary": _format_load_card(schedule) if schedule else None,
        "route_plan": route_plan,
    }


def get_unassigned_visits_context(*, tenant_context, user=None, date_value=None):
    target_date = date_value or timezone.localdate()
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    queue = TechnicianRoutingService.build_unassigned_queue(
        schedule_date=target_date,
        company=company,
        site=site,
    )
    return {
        "queue_date": target_date,
        "unassigned_rows": [
            {
                **_format_visit(item["visit"]),
                "suggested_technician": (
                    item["suggested_technician"].display_name if item["suggested_technician"] else "Sem sugestao"
                ),
                "suggested_technician_id": item["suggested_technician"].user_id if item["suggested_technician"] else None,
            }
            for item in queue
        ],
    }


def get_technician_mobile_schedule_context(*, user, tenant_context, date_value=None):
    target_date = date_value or timezone.localdate()
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    visits = TechnicianRoutingService.get_technician_agenda(
        technician=user,
        schedule_date=target_date,
        company=company,
        site=site,
    )
    if not visits:
        assigned_orders = _scope_orders(tenant_context, user=user).filter(assigned_to=user).order_by("scheduled_start", "opened_at")[:6]
        cards = [
            {
                "order_code": order.order_number,
                "title": order.title,
                "site": order.operational_site.name,
                "asset": getattr(order.asset, "name", ""),
                "scheduled_start": timezone.localtime(order.scheduled_start).strftime("%H:%M") if order.scheduled_start else "--:--",
                "status": order.get_status_display(),
                "detail_url": f"/field/services/{order.order_number}/",
            }
            for order in assigned_orders
        ]
    else:
        cards = [
            {
                "order_code": item["order_code"],
                "title": item["title"],
                "site": item["site"],
                "asset": item["asset"],
                "scheduled_start": item["scheduled_start"],
                "status": item["status"],
                "detail_url": f"/field/services/{item['order_code']}/" if item["order_code"] else "/field/services/",
                "route_order": item["route_order"],
            }
            for item in [_format_visit(visit) for visit in visits]
        ]
    return {
        "agenda_date": target_date.isoformat(),
        "agenda_date_label": target_date.strftime("%d/%m/%Y"),
        "today_route_cards": cards,
        "next_visit": cards[0] if cards else None,
        "pending_sync_visits": sum(1 for card in cards if card.get("status") not in {"Completed", "Concluida"}),
    }
