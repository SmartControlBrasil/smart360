"""Criação idempotente de unidade principal (OperationalSite) para cliente operacional."""

from __future__ import annotations

from apps.smart_system.models import MaintenanceClient, OperationalSite

# Nome estável por constraint uniq (maintenance_client, name) e UX de detalhe/listagem.
DEFAULT_PRINCIPAL_SITE_NAME = "Unidade Principal"


def ensure_default_operational_site_for_client(
    maintenance_client: MaintenanceClient,
    *,
    user=None,
) -> tuple[OperationalSite, bool]:
    """
    Se o cliente ainda não tiver nenhuma OperationalSite, cria a unidade principal.
    Replica contatos disponíveis no MaintenanceClient quando houver campo equivalente na unidade.

    Returns:
        (site, created): created é True apenas quando persistiu nova linha nesta chamada.

    Raises:
        ValueError: cliente ainda não salvo no banco.

    Nota: `user` é reservado para auditoria / extensões futuras.
    """
    if maintenance_client.pk is None:
        raise ValueError("MaintenanceClient deve estar persistido antes de criar unidade.")

    existing = OperationalSite.objects.filter(maintenance_client=maintenance_client).order_by("id").first()
    if existing is not None:
        return existing, False

    site = OperationalSite(
        maintenance_client=maintenance_client,
        name=DEFAULT_PRINCIPAL_SITE_NAME,
        code="",
        contact_name=maintenance_client.contact_name or "",
        contact_phone=maintenance_client.contact_phone or "",
        is_active=maintenance_client.is_active,
        notes="Criada automaticamente ao cadastrar o cliente.",
    )
    site.save()
    return site, True
