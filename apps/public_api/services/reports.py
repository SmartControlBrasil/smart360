from __future__ import annotations

from io import BytesIO

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - depends on env
    colors = None
    A4 = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None
    REPORTLAB_IMPORT_ERROR = exc

from apps.smart_system.models import Asset, FailureEvent, MaintenancePlan, ServiceOrder

from .scoping import PublicApiScopeService


REPORT_TYPE_LABELS = {
    "work-order": "Relatorio de Ordem de Servico",
    "preventive": "Relatorio de Manutencao Preventiva",
    "corrective": "Relatorio de Manutencao Corretiva",
    "failure": "Relatorio de Evento de Falha / RCA",
    "asset-summary": "Ficha Tecnica Resumida do Ativo",
}


class PublicReportService:
    @staticmethod
    def list_reports(request):
        scope = PublicApiScopeService.resolve_scope(request)
        items = []

        for order in PublicApiScopeService.scope_queryset(ServiceOrder.objects.select_related("client", "operational_site", "asset"), request)[:20]:
            report_type = "corrective" if order.maintenance_type == ServiceOrder.MaintenanceType.CORRECTIVE else "work-order"
            items.append(
                {
                    "report_type": report_type,
                    "reference_code": str(order.public_id),
                    "document_type": REPORT_TYPE_LABELS[report_type],
                    "reference_label": order.order_number,
                    "company": getattr(order.client.company, "name", ""),
                    "site": order.operational_site.name,
                }
            )

        for plan in PublicApiScopeService.scope_queryset(MaintenancePlan.objects.select_related("company", "operational_site", "asset"), request)[:20]:
            items.append(
                {
                    "report_type": "preventive",
                    "reference_code": str(plan.public_id),
                    "document_type": REPORT_TYPE_LABELS["preventive"],
                    "reference_label": plan.name,
                    "company": getattr(plan.company, "name", ""),
                    "site": getattr(plan.operational_site, "name", ""),
                }
            )

        for failure in PublicApiScopeService.scope_queryset(FailureEvent.objects.select_related("asset__operational_site__maintenance_client__company"), request)[:20]:
            items.append(
                {
                    "report_type": "failure",
                    "reference_code": str(failure.public_id),
                    "document_type": REPORT_TYPE_LABELS["failure"],
                    "reference_label": str(failure.public_id),
                    "company": getattr(failure.asset.operational_site.maintenance_client.company, "name", ""),
                    "site": failure.asset.operational_site.name,
                }
            )

        for asset in PublicApiScopeService.scope_queryset(Asset.objects.select_related("operational_site__maintenance_client__company"), request)[:20]:
            items.append(
                {
                    "report_type": "asset-summary",
                    "reference_code": str(asset.public_id),
                    "document_type": REPORT_TYPE_LABELS["asset-summary"],
                    "reference_label": asset.asset_tag,
                    "company": getattr(asset.operational_site.maintenance_client.company, "name", ""),
                    "site": asset.operational_site.name,
                }
            )

        return items

    @staticmethod
    def get_reference(report_type, reference_code, request):
        if report_type in {"work-order", "corrective"}:
            return PublicApiScopeService.scope_queryset(ServiceOrder.objects.select_related("client", "operational_site", "asset"), request).get(public_id=reference_code)
        if report_type == "preventive":
            return PublicApiScopeService.scope_queryset(MaintenancePlan.objects.select_related("company", "operational_site", "asset", "checklist"), request).get(public_id=reference_code)
        if report_type == "failure":
            return PublicApiScopeService.scope_queryset(FailureEvent.objects.select_related("asset", "service_order", "asset__operational_site__maintenance_client__company"), request).get(public_id=reference_code)
        if report_type == "asset-summary":
            return PublicApiScopeService.scope_queryset(Asset.objects.select_related("operational_site", "category", "operational_site__maintenance_client__company"), request).get(public_id=reference_code)
        raise Asset.DoesNotExist

    @staticmethod
    def build_report_metadata(report_type, reference, request):
        if report_type in {"work-order", "corrective"}:
            return {
                "report_type": report_type,
                "document_type": REPORT_TYPE_LABELS[report_type],
                "reference_code": str(reference.public_id),
                "reference_label": reference.order_number,
                "company": getattr(reference.client.company, "name", ""),
                "site": reference.operational_site.name,
                "download_url": request.build_absolute_uri(f"/api/public/v1/reports/{report_type}/{reference.public_id}/download/"),
            }
        if report_type == "preventive":
            return {
                "report_type": report_type,
                "document_type": REPORT_TYPE_LABELS[report_type],
                "reference_code": str(reference.public_id),
                "reference_label": reference.name,
                "company": getattr(reference.company, "name", ""),
                "site": getattr(reference.operational_site, "name", ""),
                "download_url": request.build_absolute_uri(f"/api/public/v1/reports/{report_type}/{reference.public_id}/download/"),
            }
        if report_type == "failure":
            return {
                "report_type": report_type,
                "document_type": REPORT_TYPE_LABELS[report_type],
                "reference_code": str(reference.public_id),
                "reference_label": reference.asset.asset_tag,
                "company": getattr(reference.asset.operational_site.maintenance_client.company, "name", ""),
                "site": reference.asset.operational_site.name,
                "download_url": request.build_absolute_uri(f"/api/public/v1/reports/{report_type}/{reference.public_id}/download/"),
            }
        return {
            "report_type": report_type,
            "document_type": REPORT_TYPE_LABELS[report_type],
            "reference_code": str(reference.public_id),
            "reference_label": reference.asset_tag,
            "company": getattr(reference.operational_site.maintenance_client.company, "name", ""),
            "site": reference.operational_site.name,
            "download_url": request.build_absolute_uri(f"/api/public/v1/reports/{report_type}/{reference.public_id}/download/"),
        }

    @staticmethod
    def render_pdf(report_type, reference):
        if REPORTLAB_IMPORT_ERROR is not None:
            raise RuntimeError("reportlab nao esta instalado no ambiente atual.") from REPORTLAB_IMPORT_ERROR
        buffer = BytesIO()
        document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=32, leftMargin=32, topMargin=32, bottomMargin=32)
        styles = getSampleStyleSheet()
        heading = ParagraphStyle("Heading", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=24)
        normal = styles["BodyText"]

        content = [
            Paragraph("SMART360 / Smart System", heading),
            Spacer(1, 12),
            Paragraph(REPORT_TYPE_LABELS[report_type], styles["Heading2"]),
            Spacer(1, 12),
        ]

        if report_type in {"work-order", "corrective"}:
            rows = [
                ["OS", reference.order_number],
                ["Tipo", reference.maintenance_type],
                ["Cliente", reference.client.display_name],
                ["Site", reference.operational_site.name],
                ["Ativo", getattr(reference.asset, "asset_tag", "")],
                ["Status", reference.status],
                ["Descricao", reference.description or "-"],
                ["Observacoes finais", reference.final_observations or "-"],
            ]
        elif report_type == "preventive":
            rows = [
                ["Plano", reference.name],
                ["Frequencia", f"{reference.frequency_value} {reference.frequency_type}"],
                ["Empresa", getattr(reference.company, "name", "")],
                ["Site", getattr(reference.operational_site, "name", "")],
                ["Ativo", getattr(reference.asset, "asset_tag", "")],
                ["Proxima execucao", str(reference.next_due_date or "-")],
                ["Checklist", getattr(reference.checklist, "name", "-")],
                ["Notas", reference.notes or "-"],
            ]
        elif report_type == "failure":
            rows = [
                ["Falha", str(reference.public_id)],
                ["Ativo", reference.asset.asset_tag],
                ["Severidade", reference.severity],
                ["Status", reference.status],
                ["Sintoma", reference.symptom],
                ["Causa provavel", reference.probable_cause or "-"],
                ["Causa raiz", reference.root_cause or "-"],
                ["Downtime", str(reference.downtime_minutes or 0)],
            ]
        else:
            rows = [
                ["Ativo", reference.asset_tag],
                ["Nome", reference.name],
                ["Categoria", reference.category.name],
                ["Site", reference.operational_site.name],
                ["Fabricante", reference.manufacturer or "-"],
                ["Modelo", reference.model or "-"],
                ["Serial", reference.serial_number or "-"],
                ["Criticidade", reference.criticality],
            ]

        table = Table(rows, colWidths=[140, 360])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2ff")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d7e2")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        content.append(table)
        content.append(Spacer(1, 16))
        content.append(Paragraph("Documento gerado automaticamente pela API publica do SMART360.", normal))

        document.build(content)
        return buffer.getvalue()
