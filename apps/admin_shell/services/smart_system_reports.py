from copy import deepcopy
from datetime import datetime
from io import BytesIO

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_IMPORT_ERROR = None
except ImportError as exc:
    colors = None
    A4 = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    mm = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None
    REPORTLAB_IMPORT_ERROR = exc

from apps.smart_system.services.signature_service import ServiceSignatureService

from .smart_system_assets import ASSET_RECORDS, get_asset_detail_context
from .smart_system_checklists import CHECKLIST_RECORDS, get_checklist_by_code, get_execution_context
from .smart_system_failures import FAILURE_EVENT_RECORDS, get_failure_detail_context
from .smart_system_preventives import PREVENTIVE_PLAN_RECORDS, get_preventive_detail_context
from .smart_system_work_order_execution import get_work_order_execution_context
from .smart_system_work_orders import get_work_order_detail_context


REPORT_TYPE_CONFIG = {
    "work-order": {
        "label": "Relatorio de Ordem de Servico",
        "prefix": "RT-OS",
    },
    "preventive": {
        "label": "Relatorio de Manutencao Preventiva",
        "prefix": "RT-PM",
    },
    "corrective": {
        "label": "Relatorio de Manutencao Corretiva",
        "prefix": "RT-COR",
    },
    "failure": {
        "label": "Relatorio de Evento de Falha / RCA",
        "prefix": "RT-FE",
    },
    "asset-summary": {
        "label": "Ficha Tecnica Resumida do Ativo",
        "prefix": "FT-ATV",
    },
}


REPORT_HISTORY_BLUEPRINT = [
    {"report_type": "work-order", "reference_code": "OS-2026-0148", "generated_by": "Carlos Mota", "generated_at": "12/03/2026 11:42", "status": "Disponivel", "version": "v1.0"},
    {"report_type": "corrective", "reference_code": "OS-2026-0151", "generated_by": "Ana Lopes", "generated_at": "12/03/2026 10:18", "status": "Disponivel", "version": "v1.1"},
    {"report_type": "preventive", "reference_code": "PP-2026-003", "generated_by": "Planner Fitness", "generated_at": "12/03/2026 07:10", "status": "Disponivel", "version": "v1.0"},
    {"report_type": "failure", "reference_code": "FE-2026-002", "generated_by": "Ana Lopes", "generated_at": "12/03/2026 09:56", "status": "Disponivel", "version": "v1.0"},
    {"report_type": "asset-summary", "reference_code": "CHILLER-UNID-A", "generated_by": "Smart System", "generated_at": "11/03/2026 18:30", "status": "Disponivel", "version": "v1.2"},
]


def _build_signature_block(service_order, *, prepared_by, review_note, report_type="", reference_code=""):
    summary = ServiceSignatureService.get_signature_summary(service_order)
    technician = summary["technician_signature"]
    client = summary["client_signature"]
    return {
        "prepared_by": prepared_by,
        "review_note": review_note,
        "technician_signature": technician,
        "client_signature": client,
        "has_signatures": bool(technician or client),
        "report_type": report_type,
        "reference_code": reference_code,
    }


def get_report_listing_context(tenant_context=None):
    history = get_report_history_entries(tenant_context=tenant_context)
    return {
        "report_history": history,
        "report_kpis": [
            {"label": "Modelos tecnicos", "value": str(len(REPORT_TYPE_CONFIG)), "meta": "OS, preventiva, corretiva, falha e ativo", "tone": "indigo"},
            {"label": "Relatorios gerados", "value": str(len(history)), "meta": "base historica inicial do Smart System", "tone": "sky"},
            {"label": "Com checklist", "value": str(sum(1 for item in history if item["has_checklist"])), "meta": "documentos com rotina executada", "tone": "emerald"},
            {"label": "Com materiais", "value": str(sum(1 for item in history if item["has_materials"])), "meta": "pecas e insumos consolidados", "tone": "amber"},
            {"label": "Prontos para PDF", "value": "100%", "meta": "layout documental padrao Smart System", "tone": "teal"},
            {"label": "Prontos para email", "value": "Base pronta", "meta": "historico e acoplamento futuro com notificacoes", "tone": "violet"},
        ],
        "report_groups": [
            {
                "title": "Relatorios tecnicos operacionais",
                "description": "Documentos focados em OS, corretivas, preventivas e falhas com dados de execucao, checklist e materiais.",
                "items": history[:4],
            },
            {
                "title": "Fichas e consolidacoes",
                "description": "Documentos resumidos para consulta rapida, visitas tecnicas e compartilhamento com cliente.",
                "items": history[4:],
            },
        ],
        "page_actions": [
            {"label": "Relatorio OS", "href": "/app/smart-system/reports/work-order/OS-2026-0148/", "permission_domain": "reports", "permission_action": "view"},
            {"label": "Relatorio corretivo", "href": "/app/smart-system/reports/corrective/OS-2026-0151/", "permission_domain": "reports", "permission_action": "view"},
            {"label": "Relatorio preventivo", "href": "/app/smart-system/reports/preventive/PP-2026-003/", "permission_domain": "reports", "permission_action": "view"},
            {"label": "Relatorio de falha", "href": "/app/smart-system/reports/failure/FE-2026-002/", "permission_domain": "reports", "permission_action": "view"},
            {"label": "Ficha de ativo", "href": "/app/smart-system/reports/asset-summary/CHILLER-UNID-A/", "permission_domain": "reports", "permission_action": "view"},
        ],
    }


def get_report_history_entries(tenant_context=None):
    entries = []
    for blueprint in REPORT_HISTORY_BLUEPRINT:
        report = build_report_payload(blueprint["report_type"], blueprint["reference_code"], tenant_context=tenant_context)
        if report is None:
            continue
        entries.append(
            {
                "report_code": report["report_code"],
                "report_type": report["document_type"],
                "reference_code": blueprint["reference_code"],
                "reference_title": report["subject_title"],
                "generated_at": blueprint["generated_at"],
                "generated_by": blueprint["generated_by"],
                "status": blueprint["status"],
                "version": blueprint["version"],
                "preview_url": report["preview_url"],
                "download_url": report["download_url"],
                "has_checklist": report["has_checklist"],
                "has_materials": report["has_materials"],
            }
        )
    return entries


def get_report_preview_context(report_type, reference_code, tenant_context=None):
    report = build_report_payload(report_type, reference_code, tenant_context=tenant_context)
    if report is None:
        return None
    related_entries = [item for item in get_report_history_entries(tenant_context=tenant_context) if item["reference_code"] != reference_code][:4]
    return {
        "report": report,
        "report_history": related_entries,
        "page_actions": [
            {"label": "Baixar PDF", "href": report["download_url"], "permission_domain": "reports", "permission_action": "export"},
            {"label": "Versao impressao", "href": f"{report['preview_url']}?print=1", "permission_domain": "reports", "permission_action": "view"},
            {"label": "Historico de relatorios", "href": "/app/smart-system/reports/", "permission_domain": "reports", "permission_action": "view"},
            {"label": "Abrir origem", "href": report["origin_url"], "permission_domain": report["origin_permission_domain"], "permission_action": "view"},
        ],
    }


def build_report_payload(report_type, reference_code, tenant_context=None):
    if report_type == "work-order":
        return _build_work_order_report(reference_code, corrective=False, tenant_context=tenant_context)
    if report_type == "corrective":
        return _build_work_order_report(reference_code, corrective=True, tenant_context=tenant_context)
    if report_type == "preventive":
        return _build_preventive_report(reference_code, tenant_context=tenant_context)
    if report_type == "failure":
        return _build_failure_report(reference_code, tenant_context=tenant_context)
    if report_type == "asset-summary":
        return _build_asset_summary_report(reference_code, tenant_context=tenant_context)
    return None


def generate_report_pdf(report_type, reference_code, tenant_context=None):
    report = build_report_payload(report_type, reference_code, tenant_context=tenant_context)
    if report is None:
        return None
    if REPORTLAB_IMPORT_ERROR is not None:
        raise RuntimeError("reportlab nao esta instalado no ambiente atual.") from REPORTLAB_IMPORT_ERROR

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=report["document_type"],
        author="SMART360 / Smart System",
    )
    styles = _build_pdf_styles()
    story = _build_pdf_story(report, styles)
    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_pdf_footer(canvas, doc, report),
        onLaterPages=lambda canvas, doc: _draw_pdf_footer(canvas, doc, report),
    )
    filename = f"{report['report_code'].lower()}.pdf"
    return {"report": report, "bytes": buffer.getvalue(), "filename": filename}


def _build_work_order_report(order_code, corrective=False, tenant_context=None):
    order = get_work_order_detail_context(order_code, tenant_context=tenant_context)
    if order is None:
        return None

    execution_payload = get_work_order_execution_context(order_code, tenant_context=tenant_context) or {}
    execution = execution_payload.get("execution", {})
    asset = order["asset"]
    linked_failure = _find_failure_by_work_order(order_code, tenant_context=tenant_context)

    document_type = REPORT_TYPE_CONFIG["corrective" if corrective else "work-order"]["label"]
    report_type = "corrective" if corrective else "work-order"
    sections = [
        {
            "title": "Resumo executivo",
            "type": "fields",
            "items": [
                {"label": "Codigo da OS", "value": order["code"]},
                {"label": "Tipo de manutencao", "value": order["maintenance_type"]},
                {"label": "Status", "value": order["status"]},
                {"label": "Tecnico responsavel", "value": order["responsible"] or execution.get("executor") or "Nao atribuido"},
                {"label": "Abertura", "value": order["opened_at"]},
                {"label": "Inicio", "value": order["started_at"] or execution.get("started_at") or "Nao iniciado"},
                {"label": "Conclusao", "value": order["completed_at"] or execution.get("finished_at") or "Em andamento"},
                {"label": "SLA", "value": f"{order['sla_status']} - {order['sla_deadline']}"},
            ],
        },
        {
            "title": "Chamado e contexto operacional",
            "type": "fields",
            "items": [
                {"label": "Descricao do chamado", "value": order["description"]},
                {"label": "Origem", "value": order["origin"]},
                {"label": "Solicitante", "value": order["requester"]},
                {"label": "Cliente / site", "value": f"{order['client']} / {order['site']}"},
                {"label": "Localizacao", "value": order["sector"]},
                {"label": "Ativo", "value": f"{asset['code']} - {asset['name']}"},
            ],
        },
        {
            "title": "Diagnostico tecnico",
            "type": "fields",
            "items": [
                {"label": "Sintomas", "value": execution.get("diagnosis", {}).get("symptoms") or order["description"]},
                {"label": "Diagnostico", "value": execution.get("diagnosis", {}).get("technical_diagnosis") or order["diagnosis"]["technical_diagnosis"]},
                {"label": "Componentes envolvidos", "value": execution.get("diagnosis", {}).get("components") or order["diagnosis"]["materials"]},
                {"label": "Analise realizada", "value": execution.get("diagnosis", {}).get("analysis") or order["diagnosis"]["technical_notes"]},
            ],
        },
        {
            "title": "Acao executada e recomendacao",
            "type": "fields",
            "items": [
                {"label": "Intervencao realizada", "value": execution.get("executed_action", {}).get("intervention") or order["diagnosis"]["action_taken"]},
                {"label": "Componentes substituidos", "value": execution.get("executed_action", {}).get("components_replaced") or order["diagnosis"]["materials"]},
                {"label": "Ajustes e testes", "value": f"{execution.get('executed_action', {}).get('adjustments', '')} {execution.get('executed_action', {}).get('tests', '')}".strip() or order["diagnosis"]["technical_notes"]},
                {"label": "Resultado obtido", "value": execution.get("executed_action", {}).get("result") or order["impact"]},
                {"label": "Recomendacao tecnica", "value": execution.get("finalization", {}).get("recommendation") or order["diagnosis"]["recommendation"]},
            ],
        },
    ]

    if corrective:
        sections.insert(
            3,
            {
                "title": "Falha, sintomas e corretiva aplicada",
                "type": "fields",
                "items": [
                    {"label": "Falha relatada", "value": linked_failure["failure_mode"] if linked_failure else order["title"]},
                    {"label": "Sintomas", "value": ", ".join(linked_failure["symptoms"]) if linked_failure else execution.get("diagnosis", {}).get("symptoms", "-")},
                    {"label": "Causa aparente", "value": order["diagnosis"]["apparent_cause"]},
                    {"label": "Tempo de parada", "value": linked_failure["downtime"] if linked_failure else order["summary"].get("availability", "-")},
                    {"label": "Teste pos-intervencao", "value": execution.get("executed_action", {}).get("tests") or "Teste funcional registrado no encerramento tecnico."},
                    {"label": "Status final do equipamento", "value": asset["operational_status"]},
                ],
            },
        )

    sections.extend(
        [
            {
                "title": "Horas trabalhadas",
                "type": "table",
                "columns": ["Tecnico", "Inicio", "Fim", "Duracao", "Descricao"],
                "rows": [
                    [item["technician"], item["started_at"], item["finished_at"], item["duration"], item["description"]]
                    for item in execution.get("hours", [])
                ] or [["-", "-", "-", "-", "Sem apontamentos de horas nesta versao."]],
            },
            {
                "title": "Materiais e pecas utilizadas",
                "type": "table",
                "columns": ["Codigo", "Peca", "Quantidade", "Observacao"],
                "rows": [
                    [item.get("code", "-"), item["name"], item["quantity"], item["notes"]]
                    for item in execution.get("materials", [])
                ] or [["-", "-", "-", "Nenhum material consolidado nesta versao."]],
            },
        ]
    )

    checklist_section = _build_checklist_section(execution.get("checklist"), execution.get("checklist_execution"))
    if checklist_section:
        sections.append(checklist_section)

    sections.extend(
        [
            {
                "title": "Evidencias registradas",
                "type": "list",
                "items": [
                    f"{item['timestamp']} - {item['type']}: {item['description']}"
                    for item in execution.get("evidence", [])
                ] or ["Sem evidencias anexadas nesta versao."],
            },
            {
                "title": "Timeline da intervencao",
                "type": "timeline",
                "items": [
                    f"{item['timestamp']} - {item['actor']} - {item['event_type']} - {item['description']} ({item['reference']})"
                    for item in execution.get("timeline", order.get("timeline", []))
                ],
            },
            {
                "title": "Fechamento tecnico",
                "type": "fields",
                "items": [
                    {"label": "Status final", "value": execution.get("finalization", {}).get("final_status") or order["status"]},
                    {"label": "Diagnostico final", "value": execution.get("finalization", {}).get("final_diagnosis") or execution.get("diagnosis", {}).get("technical_diagnosis") or order["diagnosis"]["technical_diagnosis"]},
                    {"label": "Acao final", "value": execution.get("finalization", {}).get("final_action") or execution.get("executed_action", {}).get("intervention") or order["diagnosis"]["action_taken"]},
                    {"label": "Necessidade de retorno", "value": execution.get("finalization", {}).get("return_needed") or order["diagnosis"]["return_needed"]},
                    {"label": "Observacoes finais", "value": execution.get("finalization", {}).get("final_notes") or order["diagnosis"]["technical_notes"]},
                ],
            },
        ]
    )

    return _compose_report(
        report_type=report_type,
        reference_code=order_code,
        subject_title=order["title"],
        subject_subtitle=f"{asset['code']} - {asset['name']} • {order['client']} • {order['site']}",
        origin_url=f"/app/smart-system/work-orders/{order_code}/",
        origin_permission_domain="work_orders",
        client_name=order["client"],
        site_name=order["site"],
        location_name=order["sector"],
        asset_label=f"{asset['code']} - {asset['name']}",
        metadata=[
            ("Tipo do documento", document_type),
            ("Origem", order["code"]),
            ("Cliente", order["client"]),
            ("Site / unidade", order["site"]),
            ("Ativo", asset["code"]),
            ("Responsavel", order["responsible"] or execution.get("executor") or "Nao atribuido"),
            ("Status", order["status"]),
            ("Versao", "v1.0"),
        ],
        highlights=[
            ("Status", order["status"]),
            ("SLA", order["sla_status"]),
            ("Horas", execution.get("hours_total") or order["executed_hours"]),
            ("Materiais", str(len(execution.get("materials", [])))),
            ("Checklist", execution.get("checklist", {}).get("code") if execution.get("checklist") else "Sem checklist"),
            ("Evidencias", str(len(execution.get("evidence", [])))),
        ],
        sections=sections,
        signature_block=_build_signature_block(
            ServiceSignatureService.get_service_order(order_code),
            prepared_by=execution.get("executor") or order["responsible"] or "Equipe tecnica",
            review_note="Documento preparado pelo Smart System com trilha de assinatura operacional vinculada ao atendimento.",
            report_type=report_type,
            reference_code=order_code,
        ),
        has_checklist=bool(execution.get("checklist")),
        has_materials=bool(execution.get("materials")),
    )


def _build_preventive_report(plan_code, tenant_context=None):
    plan = get_preventive_detail_context(plan_code, tenant_context=tenant_context)
    if plan is None:
        return None

    asset = plan["asset"]
    checklist = _find_checklist_by_plan(plan_code, tenant_context=tenant_context)
    execution = checklist["executions"][0] if checklist and checklist.get("executions") else None

    sections = [
        {
            "title": "Resumo executivo",
            "type": "fields",
            "items": [
                {"label": "Codigo do plano", "value": plan["code"]},
                {"label": "Status do plano", "value": plan["status"]},
                {"label": "Periodicidade", "value": plan["frequency_label"]},
                {"label": "Ultima execucao", "value": plan["last_execution"]},
                {"label": "Proxima execucao", "value": plan["next_execution"]},
                {"label": "Responsavel", "value": plan["responsible"] or "Nao atribuido"},
                {"label": "Aderencia", "value": plan["adherence"]},
                {"label": "Geracao automatica", "value": "Ativa" if plan["auto_generate_os"] else "Desabilitada"},
            ],
        },
        {
            "title": "Dados do plano preventivo",
            "type": "fields",
            "items": [
                {"label": "Nome do plano", "value": plan["name"]},
                {"label": "Descricao", "value": plan["description"]},
                {"label": "Estrategia preventiva", "value": plan["maintenance_strategy"]},
                {"label": "Tipo de preventiva", "value": plan["preventive_type"]},
                {"label": "Regra de recorrencia", "value": plan["recurrence_rule"]},
                {"label": "Janela operacional", "value": plan["operational_window"]},
                {"label": "Tolerancia de atraso", "value": plan["delay_tolerance"]},
                {"label": "Observacoes tecnicas", "value": plan["technical_notes"]},
            ],
        },
        {
            "title": "Ativo e contexto operacional",
            "type": "fields",
            "items": [
                {"label": "Ativo", "value": f"{asset['code']} - {asset['name']}"},
                {"label": "Cliente / site", "value": f"{asset['client']} / {asset['site']}"},
                {"label": "Localizacao", "value": asset["sector"]},
                {"label": "Criticidade", "value": asset["criticality"]},
                {"label": "Status operacional", "value": asset["operational_status"]},
                {"label": "Cobertura do ativo", "value": plan["coverage_status"]},
            ],
        },
        {
            "title": "Recorrencia, aderencia e cobertura",
            "type": "fields",
            "items": [
                {"label": "Frequencia", "value": plan["frequency_label"]},
                {"label": "Proxima janela", "value": plan["next_execution"]},
                {"label": "Atraso acumulado", "value": "Acima da tolerancia" if plan["overdue"] else "Dentro da janela"},
                {"label": "Execucoes no prazo", "value": str(plan["on_time_executions"])},
                {"label": "Execucoes atrasadas", "value": str(plan["late_executions"])},
                {"label": "Risco de cobertura", "value": plan["coverage_risk"]},
                {"label": "Logica de proxima execucao", "value": plan["next_window_logic"]},
            ],
        },
    ]

    checklist_section = _build_checklist_section(checklist, execution)
    if checklist_section:
        sections.append(checklist_section)

    anomaly_items = []
    if execution:
        anomaly_items = [response for response in execution["responses"] if response["response"] == "NOK"]

    sections.extend(
        [
            {
                "title": "Anomalias e recomendacoes",
                "type": "fields",
                "items": [
                    {"label": "Itens NOK", "value": str(execution["nok_count"]) if execution else "0"},
                    {"label": "Anomalias encontradas", "value": "; ".join(item["note"] for item in anomaly_items) if anomaly_items else "Nenhuma anomalia critica registrada na ultima execucao."},
                    {"label": "Recomendacao", "value": execution["recommendation"] if execution else plan["technical_notes"]},
                    {"label": "Acao corretiva futura", "value": "Sim, avaliar abertura automatica de OS para itens NOK." if anomaly_items else "Nao requerida neste ciclo."},
                ],
            },
            {
                "title": "Historico resumido",
                "type": "timeline",
                "items": [
                    f"{item['timestamp']} - {item['actor']} - {item['event_type']} - {item['description']} ({item['reference']})"
                    for item in plan["timeline"]
                ],
            },
        ]
    )

    return _compose_report(
        report_type="preventive",
        reference_code=plan_code,
        subject_title=plan["name"],
        subject_subtitle=f"{asset['code']} - {asset['name']} • {asset['client']} • {asset['site']}",
        origin_url=f"/app/smart-system/preventives/{plan_code}/",
        origin_permission_domain="preventive_plans",
        client_name=asset["client"],
        site_name=asset["site"],
        location_name=asset["sector"],
        asset_label=f"{asset['code']} - {asset['name']}",
        metadata=[
            ("Tipo do documento", REPORT_TYPE_CONFIG["preventive"]["label"]),
            ("Origem", plan["code"]),
            ("Cliente", asset["client"]),
            ("Site / unidade", asset["site"]),
            ("Ativo", asset["code"]),
            ("Checklist", checklist["code"] if checklist else "Nao vinculado"),
            ("Responsavel", plan["responsible"] or "Nao atribuido"),
            ("Versao", "v1.0"),
        ],
        highlights=[
            ("Status", plan["status"]),
            ("Aderencia", plan["adherence"]),
            ("Checklist", checklist["code"] if checklist else "Sem checklist"),
            ("Itens NOK", str(execution["nok_count"]) if execution else "0"),
            ("Auto OS", "Ativa" if plan["auto_generate_os"] else "Nao"),
            ("Criticidade", asset["criticality"]),
        ],
        sections=sections,
        signature_block=_build_signature_block(
            None,
            prepared_by=plan["responsible"] or "Planner PM",
            review_note="Relatorio preventivo preparado com base pronta para assinatura de execucao e aceite futuro por atendimento.",
            report_type="preventive",
            reference_code=plan_code,
        ),
        has_checklist=bool(checklist),
        has_materials=False,
    )


def _build_failure_report(failure_code, tenant_context=None):
    failure = get_failure_detail_context(failure_code, tenant_context=tenant_context)
    if failure is None:
        return None

    asset = failure["asset"]
    sections = [
        {
            "title": "Resumo executivo do evento",
            "type": "fields",
            "items": [
                {"label": "Codigo da falha", "value": failure["code"]},
                {"label": "Data / hora do evento", "value": failure["occurred_at"]},
                {"label": "Modo de falha", "value": failure["failure_mode"]},
                {"label": "Severidade", "value": failure["severity"]},
                {"label": "Impacto operacional", "value": failure["impact_level"]},
                {"label": "Tempo de parada", "value": failure["downtime"]},
                {"label": "OS associada", "value": failure["work_order_code"]},
                {"label": "Responsavel", "value": failure["responsible"] or "Nao atribuido"},
            ],
        },
        {
            "title": "Diagnostico tecnico",
            "type": "fields",
            "items": failure["diagnosis_panel"],
        },
        {
            "title": "Causa raiz / RCA",
            "type": "fields",
            "items": failure["rca_panel"],
        },
        {
            "title": "Impacto operacional e risco",
            "type": "fields",
            "items": failure["impact_panel"],
        },
        {
            "title": "Historico e recorrencia",
            "type": "list",
            "items": [
                f"{item['timestamp']} - {item['type']} - {item['description']} ({item['reference']})"
                for item in failure["asset_history"]
            ],
        },
        {
            "title": "Timeline do evento",
            "type": "timeline",
            "items": [
                f"{item['timestamp']} - {item['actor']} - {item['event_type']} - {item['description']} ({item['reference']})"
                for item in failure["timeline"]
            ],
        },
    ]

    return _compose_report(
        report_type="failure",
        reference_code=failure_code,
        subject_title=failure["failure_mode"],
        subject_subtitle=f"{asset['code']} - {asset['name']} • {failure['client']} • {failure['site']}",
        origin_url=f"/app/smart-system/failures/{failure_code}/",
        origin_permission_domain="failures",
        client_name=failure["client"],
        site_name=failure["site"],
        location_name=failure["sector"],
        asset_label=f"{asset['code']} - {asset['name']}",
        metadata=[
            ("Tipo do documento", REPORT_TYPE_CONFIG["failure"]["label"]),
            ("Origem", failure["code"]),
            ("Cliente", failure["client"]),
            ("Site / unidade", failure["site"]),
            ("Ativo", asset["code"]),
            ("OS associada", failure["work_order_code"]),
            ("Recorrencia", failure["recurrence"]),
            ("Versao", "v1.0"),
        ],
        highlights=[
            ("Status", failure["status"]),
            ("Severidade", failure["severity"]),
            ("Impacto", failure["impact_level"]),
            ("Diagnostico", "Sim" if failure["has_diagnosis"] else "Nao"),
            ("RCA", "Sim" if failure["has_rca"] else "Nao"),
            ("Parada", failure["downtime"]),
        ],
        sections=sections,
        signature_block=_build_signature_block(
            ServiceSignatureService.get_service_order(failure["work_order_code"]) if failure.get("work_order_code") else None,
            prepared_by=failure["responsible"] or "Engenharia de manutencao",
            review_note="Relatorio de falha com trilha preparada para aceite documental e evolucao do RCA.",
            report_type="failure",
            reference_code=failure_code,
        ),
        has_checklist=False,
        has_materials=False,
    )


def _build_asset_summary_report(asset_code, tenant_context=None):
    asset = get_asset_detail_context(asset_code, tenant_context=tenant_context)
    if asset is None:
        return None

    recent_failures = _find_failures_by_asset(asset_code, tenant_context=tenant_context)[:3]
    sections = [
        {
            "title": "Identificacao do ativo",
            "type": "fields",
            "items": [
                {"label": "Ativo", "value": asset["name"]},
                {"label": "Codigo / tag", "value": asset["code"]},
                {"label": "Cliente / site", "value": f"{asset['client']} / {asset['site']}"},
                {"label": "Localizacao", "value": asset["sector"]},
                {"label": "Fabricante / modelo", "value": f"{asset['manufacturer']} / {asset['model']}"},
                {"label": "Serial", "value": asset["serial_number"]},
            ],
        },
        {
            "title": "Dados tecnicos e operacionais",
            "type": "fields",
            "items": [
                {"label": "Categoria", "value": f"{asset['category']} / {asset['subcategory']}"},
                {"label": "Criticidade", "value": asset["criticality"]},
                {"label": "Status operacional", "value": asset["operational_status"]},
                {"label": "Condicao", "value": asset["condition"]},
                {"label": "Instalacao", "value": asset["installation_date"]},
                {"label": "Comissionamento", "value": asset["commissioning_date"]},
                {"label": "Garantia", "value": asset["warranty"]},
                {"label": "Responsavel", "value": asset["owner"]},
            ],
        },
        {
            "title": "Indicadores de manutencao e confiabilidade",
            "type": "fields",
            "items": [
                {"label": "Ultima manutencao", "value": asset["last_maintenance"]},
                {"label": "Proxima manutencao", "value": asset["next_maintenance"]},
                {"label": "MTBF", "value": asset["mtbf"]},
                {"label": "MTTR", "value": asset["mttr"]},
                {"label": "Disponibilidade", "value": asset["availability"]},
                {"label": "OS abertas", "value": str(asset["open_work_orders"])},
                {"label": "Falhas recentes", "value": str(asset["recent_failures"])},
                {"label": "Aderencia preventiva", "value": asset["maintenance_summary"]["plan_adherence"]},
            ],
        },
        {
            "title": "Principais falhas recentes",
            "type": "list",
            "items": [
                f"{item['code']} - {item['failure_mode']} - {item['occurred_at']} - {item['status']}"
                for item in recent_failures
            ] or ["Sem falhas recentes registradas para este ativo."],
        },
        {
            "title": "Historico tecnico resumido",
            "type": "timeline",
            "items": [
                f"{item['timestamp']} - {item['type']} - {item['description']} ({item['reference']})"
                for item in asset["history"]
            ],
        },
        {
            "title": "Observacoes tecnicas",
            "type": "fields",
            "items": [
                {"label": "Impacto operacional", "value": asset["impact"]},
                {"label": "Nivel de risco", "value": asset["risk_level"]},
                {"label": "Reincidencia de falha", "value": asset["failure_recidivism"]},
                {"label": "Observacoes", "value": asset["technical_notes"]},
            ],
        },
    ]

    return _compose_report(
        report_type="asset-summary",
        reference_code=asset_code,
        subject_title=asset["name"],
        subject_subtitle=f"{asset['code']} • {asset['client']} • {asset['site']}",
        origin_url=f"/app/smart-system/assets/{asset_code}/",
        origin_permission_domain="assets",
        client_name=asset["client"],
        site_name=asset["site"],
        location_name=asset["sector"],
        asset_label=f"{asset['code']} - {asset['name']}",
        metadata=[
            ("Tipo do documento", REPORT_TYPE_CONFIG["asset-summary"]["label"]),
            ("Origem", asset["code"]),
            ("Cliente", asset["client"]),
            ("Site / unidade", asset["site"]),
            ("Categoria", asset["category"]),
            ("Criticidade", asset["criticality"]),
            ("Status", asset["operational_status"]),
            ("Versao", "v1.0"),
        ],
        highlights=[
            ("Status", asset["operational_status"]),
            ("Condicao", asset["condition"]),
            ("Disponibilidade", asset["availability"]),
            ("MTBF", asset["mtbf"]),
            ("MTTR", asset["mttr"]),
            ("Falhas", str(asset["recent_failures"])),
        ],
        sections=sections,
        signature_block=_build_signature_block(
            None,
            prepared_by=asset["owner"],
            review_note="Ficha pronta para consulta interna, visitas tecnicas e composicao futura de relatorios com branding por empresa.",
            report_type="asset-summary",
            reference_code=asset_code,
        ),
        has_checklist=False,
        has_materials=False,
    )


def _compose_report(
    report_type,
    reference_code,
    subject_title,
    subject_subtitle,
    origin_url,
    origin_permission_domain,
    client_name,
    site_name,
    location_name,
    asset_label,
    metadata,
    highlights,
    sections,
    signature_block,
    has_checklist,
    has_materials,
):
    config = REPORT_TYPE_CONFIG[report_type]
    report_code = f"{config['prefix']}-{reference_code}"
    issued_at = _issued_timestamp()
    preview_url = f"/app/smart-system/reports/{report_type}/{reference_code}/"
    download_url = f"/app/smart-system/reports/{report_type}/{reference_code}/download/"
    return {
        "report_type": report_type,
        "document_type": config["label"],
        "report_code": report_code,
        "reference_code": reference_code,
        "issued_at": issued_at,
        "version": "v1.0",
        "status": "Disponivel",
        "subject_title": subject_title,
        "subject_subtitle": subject_subtitle,
        "client_name": client_name,
        "site_name": site_name,
        "location_name": location_name,
        "asset_label": asset_label,
        "system_name": "SMART360 Ecosystem",
        "module_name": "Smart System",
        "origin_url": origin_url,
        "origin_permission_domain": origin_permission_domain,
        "preview_url": preview_url,
        "download_url": download_url,
        "metadata": metadata,
        "highlights": highlights,
        "sections": sections,
        "signature_block": signature_block,
        "has_checklist": has_checklist,
        "has_materials": has_materials,
    }


def _build_checklist_section(checklist, execution):
    if not checklist:
        return None
    items = []
    if execution and execution.get("responses"):
        for response in execution["responses"]:
            checklist_item = next((item for item in checklist["items"] if item["order"] == response["order"]), None)
            title = checklist_item["title"] if checklist_item else f"Item {response['order']}"
            items.append(
                {
                    "item": f"{response['order']:02d}. {title}",
                    "status": response["response"],
                    "note": response["note"],
                }
            )
    return {
        "title": "Checklist executado",
        "type": "checklist",
        "summary": [
            ("Checklist", checklist["code"]),
            ("Nome", checklist["name"]),
            ("Itens", str(checklist["items_count"])),
            ("OK", str(execution["ok_count"]) if execution else "0"),
            ("NOK", str(execution["nok_count"]) if execution else "0"),
            ("N/A", str(execution["na_count"]) if execution else "0"),
        ],
        "rows": items[:12] or [{"item": "Checklist vinculado sem respostas consolidadas nesta versao.", "status": "-", "note": "-"}],
    }


def _find_failure_by_work_order(order_code, tenant_context=None):
    from apps.smart_system.models import FailureEvent

    fe = FailureEvent.objects.filter(service_order__order_number=order_code).order_by("-detected_at").first()
    if fe is None:
        return None
    return {
        "failure_mode": fe.get_status_display(),
        "symptoms": [fe.symptom] if fe.symptom else [],
        "downtime": str(fe.downtime_minutes) if fe.downtime_minutes is not None else "—",
    }


def _find_failures_by_asset(asset_code, tenant_context=None):
    matches = [
        get_failure_detail_context(item["code"], tenant_context=tenant_context)
        for item in FAILURE_EVENT_RECORDS
        if item.get("asset_code") == asset_code
    ]
    matches = [item for item in matches if item is not None]
    return sorted(matches, key=lambda item: item["occurred_at"], reverse=True)


def _find_checklist_by_plan(plan_code, tenant_context=None):
    for item in CHECKLIST_RECORDS:
        if item.get("preventive_plan_code") == plan_code:
            checklist = get_checklist_by_code(item["code"], tenant_context=tenant_context)
            if checklist is not None:
                return deepcopy(checklist)
    return None


def _build_pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f1729"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1d4ed8"),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.6,
            leading=11,
            textColor=colors.HexColor("#172033"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
            textColor=colors.HexColor("#475569"),
        )
    )
    return styles


def _build_pdf_story(report, styles):
    story = [
        Paragraph("SMART360 Ecosystem | Smart System", styles["ReportSmall"]),
        Paragraph(report["document_type"], styles["ReportTitle"]),
        Paragraph(
            f"{report['report_code']} • Emitido em {report['issued_at']} • {report['client_name']} • {report['site_name']}",
            styles["ReportSubtitle"],
        ),
        Paragraph(report["subject_title"], styles["Heading3"]),
        Paragraph(report["subject_subtitle"], styles["ReportSubtitle"]),
        Spacer(1, 4),
        _pdf_table(
            [["Documento", report["document_type"]], ["Codigo", report["report_code"]], ["Origem", report["reference_code"]], ["Ativo", report["asset_label"]]],
            col_widths=[40 * mm, 125 * mm],
            header=False,
        ),
        Spacer(1, 6),
        Paragraph("Indicadores-chave", styles["ReportSection"]),
        _pdf_table([["Indicador", "Valor"]] + [[label, value] for label, value in report["highlights"]], col_widths=[70 * mm, 95 * mm]),
        Spacer(1, 6),
        Paragraph("Metadados do documento", styles["ReportSection"]),
        _pdf_table([["Campo", "Valor"]] + [[label, value] for label, value in report["metadata"]], col_widths=[60 * mm, 105 * mm]),
    ]

    for section in report["sections"]:
        story.append(Spacer(1, 6))
        story.append(Paragraph(section["title"], styles["ReportSection"]))
        if section["type"] == "fields":
            story.append(
                _pdf_table(
                    [["Campo", "Valor"]] + [[item["label"], item["value"]] for item in section["items"]],
                    col_widths=[55 * mm, 110 * mm],
                )
            )
        elif section["type"] == "table":
            story.append(_pdf_table([section["columns"]] + section["rows"], col_widths=_table_widths(len(section["columns"]))))
        elif section["type"] == "checklist":
            story.append(_pdf_table([["Resumo", "Valor"]] + [[label, value] for label, value in section["summary"]], col_widths=[55 * mm, 110 * mm]))
            story.append(Spacer(1, 4))
            story.append(_pdf_table([["Item", "Status", "Observacao"]] + [[row["item"], row["status"], row["note"]] for row in section["rows"]], col_widths=[70 * mm, 22 * mm, 73 * mm]))
        elif section["type"] in {"list", "timeline"}:
            for item in section["items"]:
                story.append(Paragraph(f"• {item}", styles["ReportBody"]))
                story.append(Spacer(1, 2))

    story.extend(
        [
            Spacer(1, 8),
            Paragraph("Preparacao documental", styles["ReportSection"]),
            _pdf_table(
                _signature_rows(report["signature_block"]),
                col_widths=[40 * mm, 125 * mm],
                header=False,
            ),
        ]
    )
    return story


def _pdf_table(rows, col_widths=None, header=True):
    table = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    styles = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe4f0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf2ff") if header else colors.HexColor("#f8fbff")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172033")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    table.setStyle(TableStyle(styles))
    return table


def _table_widths(column_count):
    width_map = {
        2: [65 * mm, 100 * mm],
        3: [72 * mm, 22 * mm, 71 * mm],
        4: [24 * mm, 67 * mm, 25 * mm, 49 * mm],
        5: [28 * mm, 28 * mm, 28 * mm, 20 * mm, 61 * mm],
    }
    return width_map.get(column_count, [165 * mm / max(column_count, 1)] * column_count)


def _draw_pdf_footer(canvas, document, report):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#dbe4f0"))
    canvas.line(16 * mm, 12 * mm, A4[0] - 16 * mm, 12 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(16 * mm, 8 * mm, f"{report['report_code']} | SMART360 Smart System")
    canvas.drawRightString(A4[0] - 16 * mm, 8 * mm, f"Pagina {document.page}")
    canvas.restoreState()


def _issued_timestamp():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _signature_rows(signature_block):
    rows = [
        ["Preparado por", signature_block["prepared_by"]],
        ["Observacao", signature_block["review_note"]],
    ]
    technician = signature_block.get("technician_signature")
    client = signature_block.get("client_signature")
    if technician:
        rows.append(
            [
                "Assinatura do tecnico",
                f"{technician.signer_name} • {technician.signed_at.strftime('%d/%m/%Y %H:%M')}" + (" • assinatura grafica registrada" if technician.signature_data else ""),
            ]
        )
    if client:
        if client.signature_data:
            client_value = f"{client.signer_name} • {client.signed_at.strftime('%d/%m/%Y %H:%M')} • aceite registrado"
        else:
            client_value = f"{client.signer_name} • {client.signed_at.strftime('%d/%m/%Y %H:%M')} • sem assinatura: {client.get_missing_reason_display()}"
        rows.append(["Aceite do cliente", client_value])
    return rows
