from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.integration_bus.models import IntegrationEvent
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import Asset, OperationalSite

from ..models import DigitalTwin, DigitalTwinProjection, DigitalTwinSignal, DigitalTwinSnapshot
from .projectors import AssetOperationalTwinProjector, SiteOperationalTwinProjector


class DigitalTwinOrchestrator:
    @classmethod
    def _sync_signals(cls, *, digital_twin, projected_signals):
        current_refs = {f"{item['signal_type']}::{item['source_reference']}" for item in projected_signals}
        for signal in digital_twin.signals.filter(is_active=True):
            signal_key = f"{signal.signal_type}::{signal.source_reference}"
            if signal_key not in current_refs:
                signal.is_active = False
                signal.cleared_at = timezone.now()
                signal.save(update_fields=["is_active", "cleared_at", "updated_at"])
                SystemEventService.log_system_event(
                    event_type="twin.signal.cleared",
                    source_module="ai_digital_twin",
                    message="Sinal do twin removido da projecao ativa.",
                    entity_type="digital_twin",
                    entity_id=str(digital_twin.public_id),
                    company=digital_twin.company,
                    site=digital_twin.site,
                    payload={"signal_type": signal.signal_type, "signal_public_id": str(signal.public_id)},
                )
        for item in projected_signals:
            signal, created = DigitalTwinSignal.objects.update_or_create(
                digital_twin=digital_twin,
                signal_type=item["signal_type"],
                source_reference=item["source_reference"],
                defaults={
                    "source_type": item["source_type"],
                    "severity": item["severity"],
                    "title": item["title"],
                    "summary": item["summary"],
                    "signal_payload": item.get("signal_payload", {}),
                    "occurred_at": item["occurred_at"],
                    "is_active": True,
                    "cleared_at": None,
                },
            )
            if created:
                SystemEventService.log_system_event(
                    event_type="twin.signal.added",
                    source_module="ai_digital_twin",
                    message="Novo sinal adicionado ao twin.",
                    entity_type="digital_twin",
                    entity_id=str(digital_twin.public_id),
                    company=digital_twin.company,
                    site=digital_twin.site,
                    payload={"signal_type": signal.signal_type, "signal_public_id": str(signal.public_id)},
                )

    @classmethod
    def _upsert_projection(cls, *, digital_twin, projection_type, payload, source_window_start, source_window_end):
        DigitalTwinProjection.objects.update_or_create(
            digital_twin=digital_twin,
            projection_type=projection_type,
            defaults={
                "projection_status": DigitalTwinProjection.ProjectionStatus.ACTIVE,
                "source_window_start": source_window_start,
                "source_window_end": source_window_end,
                "projection_payload": payload,
            },
        )

    @classmethod
    def ensure_site_twin(cls, *, site):
        company = site.maintenance_client.company
        twin, created = DigitalTwin.objects.get_or_create(
            twin_type=DigitalTwin.TwinType.SITE_OPERATIONAL,
            company=company,
            site=site,
            defaults={
                "external_reference": site.code or str(site.public_id),
                "status": DigitalTwin.Status.ACTIVE,
            },
        )
        if created:
            SystemEventService.log_system_event(
                event_type="twin.created",
                source_module="ai_digital_twin",
                message="Twin de unidade criado.",
                entity_type="digital_twin",
                entity_id=str(twin.public_id),
                company=company,
                site=site,
                payload={"twin_type": twin.twin_type},
            )
        return twin

    @classmethod
    def ensure_asset_twin(cls, *, asset):
        company = asset.operational_site.maintenance_client.company
        twin, created = DigitalTwin.objects.get_or_create(
            twin_type=DigitalTwin.TwinType.ASSET_OPERATIONAL,
            company=company,
            asset=asset,
            defaults={
                "site": asset.operational_site,
                "external_reference": asset.asset_tag,
                "status": DigitalTwin.Status.ACTIVE,
            },
        )
        if created:
            SystemEventService.log_system_event(
                event_type="twin.created",
                source_module="ai_digital_twin",
                message="Twin de ativo criado.",
                entity_type="digital_twin",
                entity_id=str(twin.public_id),
                company=company,
                site=asset.operational_site,
                payload={"twin_type": twin.twin_type},
            )
        return twin

    @classmethod
    @transaction.atomic
    def project_twin(cls, *, digital_twin, snapshot=True, trigger_event=None):
        if digital_twin.twin_type == DigitalTwin.TwinType.SITE_OPERATIONAL and digital_twin.site_id:
            result = SiteOperationalTwinProjector.project(site=digital_twin.site)
        elif digital_twin.twin_type == DigitalTwin.TwinType.ASSET_OPERATIONAL and digital_twin.asset_id:
            result = AssetOperationalTwinProjector.project(asset=digital_twin.asset)
        else:
            raise ValueError("Twin sem contexto projetavel.")

        digital_twin.risk_level = result.risk_level
        digital_twin.status = (
            DigitalTwin.Status.ATTENTION
            if result.risk_level == "medium"
            else DigitalTwin.Status.CRITICAL
            if result.risk_level in {"high", "critical"}
            else DigitalTwin.Status.ACTIVE
        )
        digital_twin.current_state_summary = result.state_summary
        digital_twin.state_payload = result.state_payload
        digital_twin.risk_payload = result.risk_payload
        digital_twin.timeline_payload = result.timeline_payload
        digital_twin.summary_payload = result.summary_payload
        digital_twin.last_projected_at = timezone.now()
        digital_twin.save(
            update_fields=[
                "risk_level",
                "status",
                "current_state_summary",
                "state_payload",
                "risk_payload",
                "timeline_payload",
                "summary_payload",
                "last_projected_at",
                "updated_at",
            ]
        )
        cls._upsert_projection(
            digital_twin=digital_twin,
            projection_type=DigitalTwinProjection.ProjectionType.STATE,
            payload=result.state_payload,
            source_window_start=result.source_window_start,
            source_window_end=result.source_window_end,
        )
        cls._upsert_projection(
            digital_twin=digital_twin,
            projection_type=DigitalTwinProjection.ProjectionType.RISK,
            payload=result.risk_payload,
            source_window_start=result.source_window_start,
            source_window_end=result.source_window_end,
        )
        cls._upsert_projection(
            digital_twin=digital_twin,
            projection_type=DigitalTwinProjection.ProjectionType.TIMELINE,
            payload={"items": result.timeline_payload},
            source_window_start=result.source_window_start,
            source_window_end=result.source_window_end,
        )
        cls._upsert_projection(
            digital_twin=digital_twin,
            projection_type=DigitalTwinProjection.ProjectionType.INSIGHT,
            payload=result.summary_payload,
            source_window_start=result.source_window_start,
            source_window_end=result.source_window_end,
        )
        cls._sync_signals(digital_twin=digital_twin, projected_signals=result.signals)
        if snapshot:
            DigitalTwinSnapshot.objects.create(
                digital_twin=digital_twin,
                snapshot_time=timezone.now(),
                state_payload=result.state_payload,
                risk_payload=result.risk_payload,
                summary=result.summary_payload,
            )
            SystemEventService.log_system_event(
                event_type="twin.snapshot.created",
                source_module="ai_digital_twin",
                message="Snapshot do twin persistido.",
                entity_type="digital_twin",
                entity_id=str(digital_twin.public_id),
                company=digital_twin.company,
                site=digital_twin.site,
                payload={"twin_type": digital_twin.twin_type},
            )
        SystemEventService.log_system_event(
            event_type="twin.projected",
            source_module="ai_digital_twin",
            message="Twin projetado com sucesso.",
            entity_type="digital_twin",
            entity_id=str(digital_twin.public_id),
            company=digital_twin.company,
            site=digital_twin.site,
            payload={
                "twin_type": digital_twin.twin_type,
                "risk_level": digital_twin.risk_level,
                "trigger_event": str(getattr(trigger_event, "public_id", "")),
            },
        )
        SystemEventService.log_system_event(
            event_type="twin.risk.updated",
            source_module="ai_digital_twin",
            message="Perfil de risco do twin atualizado.",
            entity_type="digital_twin",
            entity_id=str(digital_twin.public_id),
            company=digital_twin.company,
            site=digital_twin.site,
            payload={"risk_level": digital_twin.risk_level, "risk_payload": digital_twin.risk_payload},
        )
        return digital_twin

    @classmethod
    def project_for_site(cls, *, site, snapshot=True):
        twin = cls.ensure_site_twin(site=site)
        return cls.project_twin(digital_twin=twin, snapshot=snapshot)

    @classmethod
    def project_for_asset(cls, *, asset, snapshot=True):
        twin = cls.ensure_asset_twin(asset=asset)
        return cls.project_twin(digital_twin=twin, snapshot=snapshot)

    @classmethod
    def project_from_event(cls, *, integration_event: IntegrationEvent):
        target_twins = []
        if integration_event.site_id:
            target_twins.append(cls.project_for_site(site=integration_event.site, snapshot=True))
        asset_public_id = integration_event.payload.get("asset_public_id") or integration_event.metadata.get("asset_public_id") or integration_event.aggregate_id if integration_event.aggregate_type == "asset" else ""
        if asset_public_id:
            asset = Asset.objects.filter(public_id=asset_public_id).select_related("operational_site", "operational_site__maintenance_client").first()
            if asset:
                target_twins.append(cls.project_for_asset(asset=asset, snapshot=True))
        elif integration_event.aggregate_type == "failure_event":
            asset = Asset.objects.filter(failure_events__public_id=integration_event.aggregate_id).select_related("operational_site", "operational_site__maintenance_client").first()
            if asset:
                target_twins.append(cls.project_for_asset(asset=asset, snapshot=True))
        return target_twins

    @classmethod
    def top_attention_twins(cls, *, company=None, site=None, limit=8):
        queryset = DigitalTwin.objects.select_related("company", "site", "asset").order_by("-last_projected_at")
        if company is not None:
            queryset = queryset.filter(company=company)
        if site is not None:
            queryset = queryset.filter(site=site)
        return list(queryset.filter(risk_level__in=["high", "critical"])[:limit])

    @classmethod
    def view(cls, *, digital_twin, user=None):
        SystemEventService.log_system_event(
            event_type="twin.viewed",
            source_module="ai_digital_twin",
            message="Twin visualizado.",
            entity_type="digital_twin",
            entity_id=str(digital_twin.public_id),
            user=user,
            company=digital_twin.company,
            site=digital_twin.site,
            payload={"twin_type": digital_twin.twin_type},
        )
