"""
Agregações do dashboard Smart System (Admin Shell) com escopo multiempresa via SmartSystemScopeService.

Substitui conteúdos mockados de `get_smart_system_dashboard_context` por contagens/querysets escopadas.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.smart_system.models import (
    Asset,
    Checklist,
    FailureEvent,
    MaintenancePlan,
    OperationalSite,
    ScheduledVisit,
    ServiceOrder,
)
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


def _str_int(n: int) -> str:
    return str(int(n))


def _scoped_so_qs(request):
    return SmartSystemScopeService.scope_queryset(
        ServiceOrder.objects.select_related(
            "assigned_to",
            "asset",
            "operational_site",
            "client",
            "client__company",
        ),
        request,
    )


def _non_terminal_so_filter() -> Q:
    terminal = (
        ServiceOrder.Status.COMPLETED,
        ServiceOrder.Status.CANCELLED,
    )
    return ~Q(status__in=terminal)


def _maintenance_type_pt(value: str) -> str:
    mapping = {
        ServiceOrder.MaintenanceType.PREVENTIVE: "Preventiva",
        ServiceOrder.MaintenanceType.CORRECTIVE: "Corretiva",
        ServiceOrder.MaintenanceType.INSPECTION: "Inspecao",
        ServiceOrder.MaintenanceType.INSTALLATION: "Instalacao",
    }
    return mapping.get(value, value)


def _priority_pt(value: str) -> str:
    mapping = {
        ServiceOrder.Priority.LOW: "Baixa",
        ServiceOrder.Priority.MEDIUM: "Media",
        ServiceOrder.Priority.HIGH: "Alta",
        ServiceOrder.Priority.URGENT: "Urgente",
    }
    return mapping.get(value, value)


def _status_pt(value: str) -> str:
    mapping = {
        ServiceOrder.Status.OPEN: "Aberta",
        ServiceOrder.Status.SCHEDULED: "Programada",
        ServiceOrder.Status.IN_PROGRESS: "Em andamento",
        ServiceOrder.Status.WAITING_QUOTE_APPROVAL: "Aguardando orcamento",
        ServiceOrder.Status.WAITING_PARTS: "Aguardando peca",
        ServiceOrder.Status.ON_HOLD: "Em pausa",
        ServiceOrder.Status.COMPLETED: "Concluida",
        ServiceOrder.Status.CANCELLED: "Cancelada",
    }
    return mapping.get(value, value)


def _serialize_work_order(row: ServiceOrder) -> dict:
    owner = "—"
    if row.assigned_to_id:
        owner = row.assigned_to.display_name or row.assigned_to.full_name or row.assigned_to.email
    asset_code = row.asset.asset_tag if row.asset_id else "—"
    deadline = "—"
    if row.scheduled_end:
        deadline = timezone.localtime(row.scheduled_end).strftime("%d/%m %H:%M")
    tone = "sky"
    if row.priority == ServiceOrder.Priority.URGENT:
        tone = "red"
    elif row.priority == ServiceOrder.Priority.HIGH:
        tone = "amber"
    elif row.status == ServiceOrder.Status.COMPLETED:
        tone = "emerald"
    return {
        "code": row.order_number,
        "asset": asset_code,
        "type": _maintenance_type_pt(row.maintenance_type),
        "priority": _priority_pt(row.priority),
        "status": _status_pt(row.status),
        "owner": owner,
        "deadline": deadline,
        "tone": tone,
    }


def _client_company_label(row: ServiceOrder) -> str:
    client = getattr(row, "client", None)
    if not client:
        return "—"
    company_obj = getattr(client, "company", None)
    if company_obj is not None:
        return getattr(company_obj, "name", "") or str(company_obj.pk)
    return getattr(client, "display_name", None) or "Cliente"


def scoped_open_service_orders_count(request) -> int:
    """Contagem de OS nao terminadas para atalhos do dashboard principal (Executive)."""
    return _scoped_so_qs(request).filter(_non_terminal_so_filter()).count()


def build_operations_chart_data(request) -> dict:
    qs_base = _scoped_so_qs(request).filter(_non_terminal_so_filter())
    in_prog = qs_base.filter(status=ServiceOrder.Status.IN_PROGRESS).count()
    scheduled = qs_base.filter(
        status__in=(
            ServiceOrder.Status.SCHEDULED,
            ServiceOrder.Status.OPEN,
        ),
    ).count()
    waiting_parts = qs_base.filter(status=ServiceOrder.Status.WAITING_PARTS).count()
    no_owner = qs_base.filter(assigned_to__isnull=True).count()

    prev = qs_base.filter(maintenance_type=ServiceOrder.MaintenanceType.PREVENTIVE).count()
    corr = qs_base.filter(maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE).count()
    inspection = qs_base.filter(maintenance_type=ServiceOrder.MaintenanceType.INSPECTION).count()
    if prev + corr + inspection > 0 and prev == 0 and corr == 0:
        corr = qs_base.exclude(maintenance_type=ServiceOrder.MaintenanceType.PREVENTIVE).count()

    totals = []
    labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    today = timezone.localdate()
    start_week = today - timedelta(days=today.weekday())
    for i in range(7):
        day = start_week + timedelta(days=i)
        day_orders = SmartSystemScopeService.scope_queryset(
            ServiceOrder.objects.filter(
                opened_at__date__lte=day,
            ).filter(
                Q(completed_at__isnull=True) | Q(completed_at__date__gt=day),
            ).exclude(
                status=ServiceOrder.Status.CANCELLED,
            ),
            request,
        ).count()
        totals.append(day_orders)

    return {
        "status": {
            "labels": ["Em andamento", "Programada (+ aberta)", "Aguardando peça", "Sem responsável"],
            "series": [in_prog, scheduled, waiting_parts, no_owner],
        },
        "maintenanceMix": {
            "labels": ["Preventivas", "Corretivas", "Inspecoes"],
            "series": [prev, corr, inspection],
        },
        "weeklyBacklog": {
            "labels": labels,
            "series": totals,
        },
    }


def build_smart_system_dashboard_context(request, tenant_context=None):
    """
    Contexto completo dos templates Smart System do Admin Shell (overview, operacao, confiabilidade).
    """
    tenant_context = tenant_context or {}
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    scope = SmartSystemScopeService.resolve_scope(request)

    if company:
        scope_client = company.name
    elif scope.company_ids:
        scope_client = f"{len(scope.company_ids)} empresa(s) no escopo"
    else:
        scope_client = "Sem empresa vinculada"

    scope_site = site.name if site else "Todas as unidades permitidas"

    now = timezone.now()
    today = timezone.localdate()

    qs_so = _scoped_so_qs(request)
    qs_open = qs_so.filter(_non_terminal_so_filter())

    overdue = qs_open.filter(scheduled_end__lt=now)
    overdue_count = overdue.count()

    visit_qs = SmartSystemScopeService.scope_queryset(
        ScheduledVisit.objects.filter(scheduled_date=today).exclude(
            status__in=(ScheduledVisit.Status.COMPLETED, ScheduledVisit.Status.CANCELLED),
        ),
        request,
    )
    visits_today = visit_qs.count()
    visits_in_route = visit_qs.filter(status=ScheduledVisit.Status.IN_PROGRESS).count()

    tech_field = (
        qs_open.filter(status=ServiceOrder.Status.IN_PROGRESS, assigned_to__isnull=False)
        .values("assigned_to_id")
        .distinct()
        .count()
    )

    assets_qs = SmartSystemScopeService.scope_queryset(
        Asset.objects.filter(is_active=True),
        request,
    )
    assets_total = assets_qs.count()
    assets_critical = assets_qs.filter(criticality=Asset.Criticality.CRITICAL).count()

    failure_open = SmartSystemScopeService.scope_queryset(
        FailureEvent.objects.exclude(status=FailureEvent.Status.RESOLVED),
        request,
    ).count()

    plans_month = SmartSystemScopeService.scope_queryset(
        MaintenancePlan.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month,
        ),
        request,
    ).count()

    checklist_models = SmartSystemScopeService.scope_queryset(Checklist.objects.all(), request).count()

    operating = assets_qs.filter(status=Asset.Status.OPERATING).count()
    maint_assets = assets_qs.filter(status=Asset.Status.MAINTENANCE).count()
    stopped = assets_qs.filter(status=Asset.Status.STOPPED).count()
    total_dist = max(operating + maint_assets + stopped, 1)
    operational_health = {
        "distribution": [
            {
                "label": "Ativos em operacao",
                "value": operating,
                "percentage": round(100 * operating / total_dist),
                "tone": "emerald",
            },
            {
                "label": "Em manutencao",
                "value": maint_assets,
                "percentage": round(100 * maint_assets / total_dist),
                "tone": "amber",
            },
            {
                "label": "Parados / criticos",
                "value": stopped,
                "percentage": round(100 * stopped / total_dist),
                "tone": "red",
            },
        ],
        "focus_areas": [],
        "critical_orders": [
            {"label": "OS criticas abertas", "value": _str_int(qs_open.filter(priority=ServiceOrder.Priority.URGENT).count())},
            {"label": "OS atrasadas", "value": _str_int(overdue_count)},
            {"label": "Ativos criticos", "value": _str_int(assets_critical)},
        ],
    }

    sites_scoped = SmartSystemScopeService.scope_queryset(
        OperationalSite.objects.select_related("maintenance_client", "maintenance_client__company").filter(
            is_active=True,
        ),
        request,
    ).order_by("name")[:40]

    site_status = []
    for srow in sites_scoped:
        client_name = srow.maintenance_client.display_name if srow.maintenance_client_id else "—"
        open_at_site = qs_open.filter(operational_site_id=srow.id).count()
        delays = qs_open.filter(operational_site_id=srow.id, scheduled_end__lt=now).count()
        crit_at_site = assets_qs.filter(operational_site_id=srow.id, criticality=Asset.Criticality.CRITICAL).count()
        compliance = "—"
        tone = "emerald"
        if delays > 3:
            tone = "red"
        elif delays > 0:
            tone = "amber"
        site_status.append(
            {
                "client": client_name,
                "site": srow.name,
                "open_orders": _str_int(open_at_site),
                "delays": _str_int(delays),
                "critical_assets": _str_int(crit_at_site),
                "compliance": compliance,
                "status": "Sob controle" if delays == 0 else "Atencao",
                "tone": tone,
            }
        )

    work_orders = [_serialize_work_order(o) for o in qs_open.order_by("-opened_at")[:10]]

    backlog_total = qs_open.count()
    crit_agg = qs_open.values("priority").annotate(c=Count("id"))
    type_agg = qs_open.values("maintenance_type").annotate(c=Count("id"))
    by_crit = [{"label": _priority_pt(row["priority"]), "value": _str_int(row["c"])} for row in crit_agg.order_by("-c")]
    by_type = [
        {"label": _maintenance_type_pt(row["maintenance_type"]), "value": _str_int(row["c"])}
        for row in type_agg.order_by("-c")
    ]

    urgent_items = []
    for row in overdue.order_by("scheduled_end")[:5]:
        urgent_items.append(
            {
                "title": f"{row.order_number} atrasada",
                "meta": f"{row.title[:80]}",
            }
        )

    backlog = {
        "total": _str_int(backlog_total),
        "by_criticality": by_crit,
        "by_type": by_type,
        "urgent_items": urgent_items,
    }

    preventive_week = SmartSystemScopeService.scope_queryset(
        ScheduledVisit.objects.filter(
            scheduled_date__gte=today,
            scheduled_date__lte=today + timedelta(days=7),
        ).exclude(status__in=(ScheduledVisit.Status.COMPLETED, ScheduledVisit.Status.CANCELLED)),
        request,
    ).count()

    preventive_late = SmartSystemScopeService.scope_queryset(
        ScheduledVisit.objects.filter(
            scheduled_date__lt=today,
        ).exclude(status__in=(ScheduledVisit.Status.COMPLETED, ScheduledVisit.Status.CANCELLED)),
        request,
    ).count()

    preventive_done = SmartSystemScopeService.scope_queryset(
        ScheduledVisit.objects.filter(
            scheduled_date__gte=today.replace(day=1),
            status=ScheduledVisit.Status.COMPLETED,
        ),
        request,
    ).count()

    schedule_rows = []
    for v in (
        SmartSystemScopeService.scope_queryset(
            ScheduledVisit.objects.select_related("operational_site", "asset", "technician").filter(
                scheduled_date__gte=today,
            ),
            request,
        )
        .exclude(status__in=(ScheduledVisit.Status.COMPLETED, ScheduledVisit.Status.CANCELLED))
        .order_by("scheduled_date", "scheduled_start")[:6]
    ):
        asset_lbl = v.asset.asset_tag if v.asset_id else "—"
        owner = "—"
        if v.technician_id:
            owner = v.technician.get_full_name() or v.technician.email
        date_chunks = [v.scheduled_date.strftime("%d/%m")]
        if v.scheduled_start:
            date_chunks.append(timezone.localtime(v.scheduled_start).strftime("%H:%M"))
        schedule_rows.append(
            {
                "date": " ".join(date_chunks),
                "asset": asset_lbl,
                "activity": v.title[:120],
                "owner": owner,
                "status": v.get_status_display(),
            },
        )

    preventive_plan = {
        "headline": [
            {"label": "Programadas hoje", "value": _str_int(visits_today)},
            {"label": "Da semana", "value": _str_int(preventive_week)},
            {"label": "Atrasadas", "value": _str_int(preventive_late)},
            {"label": "Concluidas no mes", "value": _str_int(preventive_done)},
        ],
        "adherence": 100 - min(100, preventive_late * 5) if preventive_week + preventive_late else 100,
        "schedule": schedule_rows,
    }

    alerts = []
    for row in overdue.order_by("-priority", "scheduled_end")[:5]:
        alerts.append(
            {
                "title": f"OS {row.order_number} atrasada ({_client_company_label(row)})",
                "description": row.title[:200],
                "severity": "critical" if row.priority == ServiceOrder.Priority.URGENT else "warning",
            }
        )
    for row in qs_open.filter(assigned_to__isnull=True).order_by("-opened_at")[:3]:
        alerts.append(
            {
                "title": f"OS {row.order_number} sem responsavel",
                "description": row.title[:200],
                "severity": "warning",
            },
        )

    activity_feed = []
    for row in qs_so.order_by("-opened_at")[:8]:
        activity_feed.append(
            {
                "time": timezone.localtime(row.opened_at).strftime("%H:%M"),
                "actor": row.requested_by or "Sistema",
                "event": f"OS {row.order_number} ({_status_pt(row.status)})",
                "reference": f"{row.order_number}",
            },
        )

    top_failures = SmartSystemScopeService.scope_queryset(
        FailureEvent.objects.filter(asset__isnull=False),
        request,
    )
    agg = (
        top_failures.values("asset__asset_tag", "asset__name")
        .annotate(c=Count("id"))
        .order_by("-c")[:5]
    )
    top_assets_fb = [{"asset": row["asset__asset_tag"] or row["asset__name"], "failures": f"{row['c']} eventos", "trend": "—"} for row in agg]

    recent_fe = SmartSystemScopeService.scope_queryset(
        FailureEvent.objects.select_related("asset").order_by("-detected_at"),
        request,
    )[:6]
    recent_events = []
    for fe in recent_fe:
        ts = timezone.localtime(fe.detected_at).strftime("%H:%M") if fe.detected_at else "—"
        ref = ""
        pid = getattr(fe, "public_id", None)
        if pid:
            ref = pid.hex[:12].upper()
        recent_events.append(
            {
                "timestamp": ts,
                "event": (fe.symptom[:140] if fe.symptom else str(fe)),
                "reference": ref,
            },
        )

    reliability = {
        "recurring_failures": [],
        "top_assets": top_assets_fb,
        "recent_events": recent_events,
        "trend_text": (
            "Dados consolidados apenas do seu tenant Smart System."
            if not request.user.is_superuser
            else "Visao conforme permissao e escopo de sessao (superusuario)."
        ),
    }

    kpis = [
        {
            "label": "Ativos monitorados",
            "value": _str_int(assets_total),
            "context": f"{_str_int(assets_critical)} criticos no escopo",
            "trend": "—",
            "badge": "Ativos",
            "tone": "indigo",
        },
        {
            "label": "Ordens abertas",
            "value": _str_int(backlog_total),
            "context": f"{_str_int(qs_open.filter(status=ServiceOrder.Status.IN_PROGRESS).count())} em execucao",
            "trend": "—",
            "badge": "OS",
            "tone": "sky",
        },
        {
            "label": "OS atrasadas",
            "value": _str_int(overdue_count),
            "context": "fora da janela planejada",
            "trend": "—",
            "badge": "Prazo",
            "tone": "amber",
        },
        {
            "label": "Preventivas do mes",
            "value": _str_int(plans_month),
            "context": "planos cadastrados no mes",
            "trend": "—",
            "badge": "Plano",
            "tone": "emerald",
        },
        {
            "label": "Falhas criticas",
            "value": _str_int(failure_open),
            "context": "eventos nao resolvidos",
            "trend": "—",
            "badge": "Confiabilidade",
            "tone": "red",
        },
        {
            "label": "Backlog tecnico",
            "value": _str_int(backlog_total),
            "context": "pendencias OS nao encerradas",
            "trend": "—",
            "badge": "Backlog",
            "tone": "orange",
        },
        {
            "label": "Disponibilidade operacional",
            "value": f"{round(100 * operating / max(assets_total, 1), 1)}%",
            "context": "ativos em operacao / total monitorado",
            "trend": "—",
            "badge": "Uptime proxy",
            "tone": "emerald",
        },
        {
            "label": "MTTR",
            "value": "—",
            "context": "calcule a partir das OS concluidas",
            "trend": "—",
            "badge": "Futuro",
            "tone": "teal",
        },
        {
            "label": "MTBF",
            "value": "—",
            "context": "calcule a partir dos eventos",
            "trend": "—",
            "badge": "Futuro",
            "tone": "violet",
        },
        {
            "label": "Conformidade preventiva",
            "value": f"{preventive_plan['adherence']}%",
            "context": "aproximado por visitas atrasadas",
            "trend": "—",
            "badge": "Preventiva",
            "tone": "cyan",
        },
    ]

    operation_kpis = [
        {
            "label": "OS em andamento",
            "value": _str_int(qs_open.filter(status=ServiceOrder.Status.IN_PROGRESS).count()),
            "context": "status em execucao",
            "trend": "escopo atual",
            "badge": "Campo",
            "tone": "sky",
        },
        {
            "label": "OS aguardando peca",
            "value": _str_int(qs_open.filter(status=ServiceOrder.Status.WAITING_PARTS).count()),
            "context": "waiting_parts",
            "trend": "escopo atual",
            "badge": "Pecas",
            "tone": "amber",
        },
        {
            "label": "OS sem responsavel",
            "value": _str_int(qs_open.filter(assigned_to__isnull=True).count()),
            "context": "precisa atribuicao",
            "trend": "escopo atual",
            "badge": "Triagem",
            "tone": "red",
        },
        {
            "label": "Preventivas programadas",
            "value": _str_int(preventive_week),
            "context": "proximos 7 dias (visitas planejadas)",
            "trend": "escopo atual",
            "badge": "Planejado",
            "tone": "emerald",
        },
        {
            "label": "Visitas de hoje",
            "value": _str_int(visits_today),
            "context": f"{_str_int(visits_in_route)} em rota",
            "trend": "agenda Smart System",
            "badge": "Agenda",
            "tone": "indigo",
        },
        {
            "label": "Tecnicos em campo",
            "value": _str_int(tech_field),
            "context": "usuarios distintos com OS em execucao",
            "trend": "equipes",
            "badge": "Equipe",
            "tone": "teal",
        },
    ]

    tpm_indicators = [
        {
            "label": "Checklists modelo",
            "value": _str_int(checklist_models),
            "context": "templates ativos no escopo",
            "trend": "sem execucoes automaticas nesta vista",
            "badge": "Checklist",
            "tone": "amber",
        },
        {
            "label": "Ativos criticos monitorados",
            "value": _str_int(assets_critical),
            "context": "criticidade maxima cadastrada",
            "trend": "prioridade campo",
            "badge": "Risco",
            "tone": "red",
        },
        {
            "label": "Falhas abertas",
            "value": _str_int(failure_open),
            "context": "eventos sem resolucao",
            "trend": "confiabilidade",
            "badge": "RCA",
            "tone": "emerald",
        },
    ]

    payload = {
        "page_actions": [
            {"label": "Nova OS", "route_name": "admin-shell:smart-system-work-order-create", "permission_domain": "work_orders", "permission_action": "create"},
            {"label": "Nova preventiva", "href": "#nova-preventiva", "permission_domain": "preventive_plans", "permission_action": "create"},
            {"label": "Registrar falha", "href": "#registrar-falha", "permission_domain": "failures", "permission_action": "create"},
            {"label": "Ver ativos", "route_name": "admin-shell:smart-system-assets", "permission_domain": "assets", "permission_action": "view"},
            {"label": "Ordens de servico", "route_name": "admin-shell:smart-system-work-orders", "permission_domain": "work_orders", "permission_action": "view"},
            {"label": "Preventivas", "route_name": "admin-shell:smart-system-preventives", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Planos rotativos", "route_name": "admin-shell:smart-system-inspection-routines", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Falhas", "route_name": "admin-shell:smart-system-failures", "permission_domain": "failures", "permission_action": "view"},
            {"label": "Checklists", "route_name": "admin-shell:smart-system-checklists", "permission_domain": "checklists", "permission_action": "view"},
            {"label": "Relatorios", "route_name": "admin-shell:smart-system-reports", "permission_domain": "reports", "permission_action": "view"},
            {"label": "Exportar visao", "href": "#exportar", "permission_domain": "reports", "permission_action": "export"},
        ],
        "filter_groups": [
            {"label": "Periodo", "type": "chips", "options": ["Hoje", "7 dias", "30 dias", "Trimestre"], "active": "30 dias"},
            {"label": "Site / unidade", "type": "select", "value": scope_site},
            {"label": "Cliente", "type": "select", "value": scope_client},
            {"label": "Criticidade", "type": "select", "value": "Todas"},
            {"label": "Status da OS", "type": "select", "value": "Abertas e em andamento"},
            {"label": "Tipo", "type": "select", "value": "Preventiva + Corretiva"},
        ],
        "kpis": kpis,
        "operation_kpis": operation_kpis,
        "tpm_indicators": tpm_indicators,
        "operational_health": operational_health,
        "work_orders": work_orders,
        "backlog": backlog,
        "reliability": reliability,
        "preventive_plan": preventive_plan,
        "alerts": alerts,
        "activity_feed": activity_feed,
        "action_shortcuts": [
            {"label": "Abrir ordem de servico", "context": "Registro corretivo imediato", "route_name": "admin-shell:smart-system-work-order-create", "tone": "indigo"},
            {"label": "Cadastrar ativo", "context": "Novo equipamento legado", "route_name": "admin-shell:smart-system-assets", "tone": "sky"},
            {"label": "Registrar falha", "context": "Evento tecnico", "route_name": "admin-shell:smart-system-failures", "tone": "red"},
            {"label": "Checklists", "context": "Modelos e execucao", "route_name": "admin-shell:smart-system-checklists", "tone": "emerald"},
            {"label": "Consultar backlog", "context": "Filas de OS", "route_name": "admin-shell:smart-system-work-orders", "tone": "amber"},
            {"label": "Agenda", "context": "Visitas e roteiros", "route_name": "admin-shell:smart-system-scheduling", "tone": "violet"},
        ],
        "site_status": site_status,
    }
    return payload
