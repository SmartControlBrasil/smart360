from __future__ import annotations

import csv
import io
from typing import Any

from apps.ai_agents_center.models import CommercialOpportunity, EduardoProspectImportBatch
from apps.ai_agents_center.services.commercial_intelligence import UNCONFIRMED, CommercialIntelligenceService
from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService


class EduardoImporterService:
    OUTREACH_SENDER_EMAIL = "comercial@mcautomation.com.br"
    OUTREACH_DOMAIN = "mcautomation.com.br"
    VALID_SOURCES = {choice[0] for choice in CommercialOpportunity.Source.choices}

    @classmethod
    def import_rows(
        cls,
        *,
        rows: list[dict[str, Any]],
        company,
        source: str = "manual",
        filename: str = "",
        created_by=None,
    ) -> EduardoProspectImportBatch:
        batch_source = source if source in cls.VALID_SOURCES else CommercialOpportunity.Source.MANUAL
        batch = EduardoProspectImportBatch.objects.create(
            company=company,
            created_by=created_by,
            source=batch_source,
            filename=filename or "",
            total_rows=len(rows),
            status=EduardoProspectImportBatch.Status.PROCESSING,
        )
        errors: list[dict[str, Any]] = []
        created_opportunities = 0
        skipped_duplicates = 0
        skipped_empty_rows = 0
        processed_rows = 0

        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                errors.append({"row": index, "error": "Linha invalida: esperado objeto JSON."})
                continue

            company_name = cls._extract_company_name(row)
            if not company_name:
                skipped_empty_rows += 1
                continue

            processed_rows += 1
            try:
                row_source = cls._resolve_row_source(row, batch_source)
                payload = cls._row_to_opportunity_payload(row, company_name=company_name)
                context = {"public_opportunity": CommercialIntelligenceService.normalize_opportunity(payload)}
                analysis = CommercialIntelligenceService.analyze(context=context)
                opportunity = OpportunityBuilderService.build_from_analysis(
                    analysis=analysis,
                    company=company,
                    source=row_source,
                )
                cls._apply_outreach_preparation(opportunity=opportunity, batch=batch, payload=payload)
                if opportunity.metadata.get("deduplicated"):
                    skipped_duplicates += 1
                else:
                    created_opportunities += 1
            except Exception as exc:  # noqa: BLE001 - lote continua mesmo com erro pontual
                errors.append({"row": index, "company_name": company_name, "error": str(exc)})

        batch.processed_rows = processed_rows
        batch.created_opportunities = created_opportunities
        batch.skipped_duplicates = skipped_duplicates
        batch.skipped_empty_rows = skipped_empty_rows
        batch.errors = errors
        if processed_rows > 0 and created_opportunities == 0 and skipped_duplicates == 0 and errors:
            batch.status = EduardoProspectImportBatch.Status.FAILED
        else:
            batch.status = EduardoProspectImportBatch.Status.COMPLETED
        batch.save()
        return batch

    @classmethod
    def import_csv(
        cls,
        *,
        file_content,
        company,
        filename: str = "",
        created_by=None,
    ) -> EduardoProspectImportBatch:
        if isinstance(file_content, bytes):
            file_content = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(file_content))
        rows = [dict(row) for row in reader]
        return cls.import_rows(
            rows=rows,
            company=company,
            source=CommercialOpportunity.Source.CSV,
            filename=filename,
            created_by=created_by,
        )

    @classmethod
    def _extract_company_name(cls, row: dict[str, Any]) -> str:
        for key in ("company_name", "empresa", "nome"):
            value = row.get(key)
            if value is None:
                continue
            cleaned = str(value).strip()
            if cleaned:
                return cleaned[:180]
        return ""

    @classmethod
    def _resolve_row_source(cls, row: dict[str, Any], batch_source: str) -> str:
        row_source = str(row.get("source") or "").strip().lower()
        if row_source in cls.VALID_SOURCES:
            return row_source
        return batch_source

    @classmethod
    def _row_to_opportunity_payload(cls, row: dict[str, Any], *, company_name: str) -> dict[str, Any]:
        city = cls._normalize_city(row.get("city") or row.get("cidade"))
        state = cls._normalize_state(row.get("state") or row.get("estado"))
        notes = str(row.get("notes") or row.get("notas") or "").strip()
        contact_email = str(row.get("contact_email") or row.get("email") or "").strip()
        contact_phone = str(row.get("contact_phone") or row.get("phone") or row.get("telefone") or "").strip()
        contact_name = str(row.get("contact_name") or row.get("contato") or "").strip()

        contacts: list[str] = []
        if contact_email:
            contacts.append(contact_email)
        if contact_phone:
            contacts.append(contact_phone)
        if contact_name and contact_name not in " ".join(contacts):
            contacts.append(f"Contato: {contact_name}")

        problems = [notes] if notes else [UNCONFIRMED]
        evidence = [f"Notas da importacao EDU: {notes}"] if notes else []

        return {
            "company_name": company_name,
            "segment": str(row.get("segment") or row.get("segmento") or "").strip(),
            "city": city,
            "state": state,
            "website": str(row.get("website") or row.get("site") or "").strip(),
            "institutional_contacts": contacts,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "problems": problems,
            "evidence": evidence,
            "source": row.get("source") or "",
        }

    @staticmethod
    def _normalize_city(value) -> str:
        cleaned = " ".join(part.strip() for part in str(value or "").split() if part.strip())
        return cleaned.title()[:100]

    @staticmethod
    def _normalize_state(value) -> str:
        cleaned = str(value or "").strip().upper()
        return cleaned[:100]

    @classmethod
    def _apply_outreach_preparation(cls, *, opportunity, batch, payload: dict[str, Any]):
        metadata = {
            **(opportunity.metadata or {}),
            "import_batch_public_id": str(batch.public_id),
            "contact_name": payload.get("contact_name") or "",
            "contact_email": payload.get("contact_email") or "",
            "contact_phone": payload.get("contact_phone") or "",
            "outreach_prepared": True,
            "outreach_compliance": "Canal comercial isolado (mcautomation.com.br). Sem envio automatico nesta fase.",
        }
        opportunity.outreach_channel = CommercialOpportunity.OutreachChannel.NONE
        opportunity.outreach_sender_email = cls.OUTREACH_SENDER_EMAIL
        opportunity.outreach_domain = cls.OUTREACH_DOMAIN
        opportunity.outreach_status = CommercialOpportunity.OutreachStatus.NOT_STARTED
        opportunity.metadata = metadata
        opportunity.save(
            update_fields=[
                "outreach_channel",
                "outreach_sender_email",
                "outreach_domain",
                "outreach_status",
                "metadata",
                "updated_at",
            ]
        )
