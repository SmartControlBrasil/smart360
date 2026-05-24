from __future__ import annotations

from apps.smart_system.models import InspectionDivision, PreventiveInspectionRoutine


def _division_is_available(division: InspectionDivision) -> bool:
    return division.is_active and division.archived_at is None


def _ordered_divisions_for_routine(routine_id: int):
    return list(
        InspectionDivision.objects.filter(routine_id=routine_id).order_by("sort_order", "pk")
    )


def get_next_eligible_inspection_division(routine: PreventiveInspectionRoutine) -> InspectionDivision | None:
    """
    Próxima divisão ativa sugerida pela rotina.

    - Ordena por `sort_order`, depois `pk`.
    - Ignora inativas ou arquivadas (`archived_at` preenchido).
    - Sem `next_division`: retorna a primeira ativa.
    - Com `next_division` ativa e pertencente à rotina: retorna ela.
    - Com `next_division` inválida/inativa: retorna a primeira ativa após ela na
      ordem completa (lista base), com wrap; se nada for encontrado, a primeira ativa.
    """
    ordered_all = _ordered_divisions_for_routine(routine.pk)
    active_in_order = [d for d in ordered_all if _division_is_available(d)]
    if not active_in_order:
        return None

    pointer = routine.next_division
    if pointer is None or pointer.routine_id != routine.pk:
        return active_in_order[0]

    if _division_is_available(pointer):
        return pointer

    try:
        idx = next(i for i, d in enumerate(ordered_all) if d.pk == pointer.pk)
    except StopIteration:
        return active_in_order[0]

    n = len(ordered_all)
    for step in range(1, n + 1):
        cand = ordered_all[(idx + step) % n]
        if _division_is_available(cand):
            return cand

    return active_in_order[0]
