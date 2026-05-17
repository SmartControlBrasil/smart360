"""Mutacoes de OS no shell (POST) — ServiceOrderService, WorkLog, checklist."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from apps.smart_system.models import ChecklistItem, ServiceOrder, ServiceOrderChecklistResponse, WorkLog
from apps.smart_system.services.maintenance_service import ServiceOrderService, WorkLogService

from .smart_system_work_orders_domain import get_scoped_service_order, log_status_change_event


def _redirect_execution(order_code: str):
    return redirect("admin-shell:smart-system-work-order-execution", order_code=order_code)


def _redirect_detail(order_code: str):
    return redirect("admin-shell:smart-system-work-order-detail", order_code=order_code)


def post_service_order_named_transition(*, request, order_code: str, transition: str):
    so = get_scoped_service_order(order_code=order_code, request=request, tenant_context=None)
    if so is None:
        messages.error(request, "Ordem nao encontrada ou fora do escopo.")
        return redirect("admin-shell:smart-system-work-orders")
    return _apply_transition(request, so, order_code, transition)


def post_service_order_transition(*, request, order_code: str):
    transition = (request.POST.get("transition") or "").strip().lower()
    return post_service_order_named_transition(request=request, order_code=order_code, transition=transition)


def post_service_order_complete(*, request, order_code: str):
    return post_service_order_named_transition(request=request, order_code=order_code, transition="complete")


def _apply_transition(request, so, order_code: str, transition: str):
    prev = so.status
    data: dict = {}

    if transition == "start":
        if prev in (ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.ON_HOLD):
            data["status"] = ServiceOrder.Status.IN_PROGRESS
    elif transition == "pause":
        if prev == ServiceOrder.Status.IN_PROGRESS:
            data["status"] = ServiceOrder.Status.ON_HOLD
    elif transition == "resume":
        if prev == ServiceOrder.Status.ON_HOLD:
            data["status"] = ServiceOrder.Status.IN_PROGRESS
    elif transition == "parts_ready":
        if prev == ServiceOrder.Status.WAITING_PARTS:
            data["status"] = ServiceOrder.Status.IN_PROGRESS
    elif transition == "quote_ready":
        if prev == ServiceOrder.Status.WAITING_QUOTE_APPROVAL:
            data["status"] = ServiceOrder.Status.IN_PROGRESS
    elif transition == "cancel":
        if prev not in (ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED):
            data["status"] = ServiceOrder.Status.CANCELLED
    elif transition == "complete":
        if prev in (ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED):
            messages.info(request, "Esta OS ja esta encerrada.")
            return _redirect_detail(order_code)
        if prev in (ServiceOrder.Status.WAITING_PARTS, ServiceOrder.Status.WAITING_QUOTE_APPROVAL):
            messages.warning(
                request,
                "Retome a execucao (pecas disponiveis ou orcamento aprovado) antes de concluir a OS.",
            )
            return _redirect_execution(order_code)
        obs = (request.POST.get("final_observations") or "").strip()
        if not obs:
            messages.error(
                request,
                "Informe as observacoes finais antes de concluir a OS. "
                "Descreva o servico executado, o estado do equipamento e recomendacoes para auditoria.",
            )
            return _redirect_execution(order_code)
        data["status"] = ServiceOrder.Status.COMPLETED
        data["final_observations"] = obs

    if not data:
        messages.error(request, "Transicao invalida para o status atual.")
        return _redirect_execution(order_code)

    ServiceOrderService.update_service_order(service_order=so, validated_data=data, user=request.user)
    so.refresh_from_db()
    log_status_change_event(so, request.user, prev, so.status)
    messages.success(request, "Ordem de servico atualizada.")
    if transition == "complete":
        return _redirect_detail(order_code)
    return _redirect_execution(order_code)


def post_service_order_worklog(*, request, order_code: str):
    so = get_scoped_service_order(order_code=order_code, request=request, tenant_context=None)
    if so is None:
        messages.error(request, "Ordem nao encontrada ou fora do escopo.")
        return redirect("admin-shell:smart-system-work-orders")

    notes = (request.POST.get("notes") or "").strip()
    if not notes:
        messages.error(request, "Informe o comentario do apontamento.")
        return _redirect_detail(order_code)

    try:
        hours = Decimal(str(request.POST.get("hours", "0") or "0"))
    except Exception:
        hours = Decimal("0")
    if hours < 0:
        hours = Decimal("0")

    minutes = int(hours * 60)
    end_at = timezone.now()
    start_at = end_at - timedelta(minutes=max(minutes, 0)) if minutes else end_at

    tech_id = request.POST.get("technician_id")
    user = request.user
    if tech_id:
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            user = User.objects.filter(pk=int(tech_id)).first() or request.user
        except (TypeError, ValueError):
            pass

    wl = WorkLog.objects.create(
        service_order=so,
        user=user,
        started_at=start_at,
        ended_at=end_at,
        labor_minutes=max(minutes, 0),
        notes=notes[:5000],
    )
    WorkLogService.sync_labor_minutes(work_log=wl)
    messages.success(request, "Apontamento registrado.")
    if (request.POST.get("return_to") or "").strip().lower() == "execution":
        return _redirect_execution(order_code)
    return _redirect_detail(order_code)


def post_service_order_checklist_responses(*, request, order_code: str):
    so = get_scoped_service_order(order_code=order_code, request=request, tenant_context=None)
    if so is None:
        messages.error(request, "Ordem nao encontrada ou fora do escopo.")
        return redirect("admin-shell:smart-system-work-orders")

    plan = so.maintenance_plan
    if not plan or not plan.checklist_id:
        messages.error(request, "Esta OS nao possui checklist vinculado ao plano.")
        return _redirect_execution(order_code)

    checklist_id = int(request.POST.get("checklist_id") or plan.checklist_id)
    if checklist_id != plan.checklist_id:
        messages.error(request, "Checklist invalido.")
        return _redirect_execution(order_code)

    items = ChecklistItem.objects.filter(checklist_id=checklist_id, is_active=True)
    saved = 0
    for item in items:
        prefix = f"item_{item.pk}_"
        if item.item_type == ChecklistItem.ItemType.BOOLEAN:
            val = (request.POST.get(f"{prefix}response") or "").strip().upper()
            if val not in ("OK", "NOK", "NA", "N/A"):
                continue
            rb = True if val == "OK" else False if val == "NOK" else None
            note = (request.POST.get(f"{prefix}note") or "").strip()
            ServiceOrderChecklistResponse.objects.update_or_create(
                service_order=so,
                checklist_item=item,
                defaults={
                    "response_boolean": rb,
                    "response_text": "",
                    "response_number": None,
                    "response_choice": "",
                    "notes": note[:2000],
                },
            )
            saved += 1
        else:
            text = (request.POST.get(f"{prefix}text") or "").strip()
            num_raw = (request.POST.get(f"{prefix}number") or "").strip()
            choice = (request.POST.get(f"{prefix}choice") or "").strip()
            note = (request.POST.get(f"{prefix}note") or "").strip()
            if not text and not num_raw and not choice:
                continue
            num = None
            if num_raw:
                try:
                    num = Decimal(num_raw)
                except Exception:
                    num = None
            ServiceOrderChecklistResponse.objects.update_or_create(
                service_order=so,
                checklist_item=item,
                defaults={
                    "response_boolean": None,
                    "response_text": text[:4000],
                    "response_number": num,
                    "response_choice": choice[:120],
                    "notes": note[:2000],
                },
            )
            saved += 1

    if saved:
        messages.success(request, f"Checklist atualizado ({saved} itens).")
    else:
        messages.info(request, "Nenhuma resposta de checklist enviada.")
    return _redirect_execution(order_code)


def post_service_order_progress_notes(*, request, order_code: str):
    so = get_scoped_service_order(order_code=order_code, request=request, tenant_context=None)
    if so is None:
        messages.error(request, "Ordem nao encontrada ou fora do escopo.")
        return redirect("admin-shell:smart-system-work-orders")

    note = (request.POST.get("progress_notes") or "").strip()
    if not note:
        messages.info(request, "Nenhuma nota informada.")
        return _redirect_execution(order_code)

    existing = (so.notes or "").strip()
    stamp = timezone.now().strftime("%d/%m/%Y %H:%M")
    line = f"[{stamp}] {request.user.get_full_name() or request.user.email}: {note}"
    new_notes = f"{existing}\n{line}".strip() if existing else line
    ServiceOrderService.update_service_order(
        service_order=so,
        validated_data={"notes": new_notes[:8000]},
        user=request.user,
    )
    messages.success(request, "Andamento registrado nas observacoes da OS.")
    return _redirect_execution(order_code)
