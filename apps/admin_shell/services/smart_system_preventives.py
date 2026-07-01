from copy import deepcopy

from django.urls import reverse

from .smart_system_assets import ASSET_RECORDS, get_asset_by_code
from .tenant_scope import filter_records_for_scope, record_matches_scope


PREVENTIVE_PLAN_RECORDS = [
    {
        "code": "PP-2026-001",
        "name": "Plano HVAC Chiller Unidade A",
        "description": "Rotina preventiva do chiller principal com inspeção de fluxo, limpeza térmica e validação de sensores.",
        "asset_code": "CHILLER-UNID-A",
        "maintenance_strategy": "Preventiva calendarizada",
        "preventive_type": "Inspecao mensal + limpeza tecnica trimestral",
        "frequency": 30,
        "frequency_unit": "dias",
        "recurrence_rule": "A cada 30 dias, com limpeza profunda a cada 90 dias",
        "last_execution": "27/02/2026",
        "next_execution": "16/03/2026",
        "status": "Ativo",
        "adherence": "82%",
        "adherence_score": 82,
        "checklist_name": "Checklist HVAC Critico",
        "checklist_items": 18,
        "checklist_status": "Ativo",
        "checklist_updated_at": "03/03/2026",
        "responsible": "Carlos Mota",
        "operational_window": "05:00-07:00",
        "delay_tolerance": "24 h",
        "auto_generate_os": True,
        "priority": "Alta",
        "technical_notes": "Revisar incrustação do evaporador e sensores de fluxo a cada ciclo mensal.",
        "overdue": False,
        "due_soon": True,
        "critical_delay": False,
        "without_checklist": False,
        "coverage_risk": "Alto",
        "on_time_executions": 9,
        "late_executions": 2,
        "coverage_status": "Cobertura ativa",
        "next_window_logic": "Proxima OS preventiva deve ser sugerida 3 dias antes da janela",
        "timeline": [
            {"timestamp": "03/03 09:20", "actor": "Carlos Mota", "event_type": "Checklist atualizado", "description": "Inclusao de validação adicional para sensor de fluxo.", "reference": "CHK-HVAC-18"},
            {"timestamp": "27/02 06:10", "actor": "Equipe HVAC", "event_type": "Preventiva executada", "description": "Limpeza de serpentina, checagem de fluxo e inspeção elétrica.", "reference": "PM-078"},
            {"timestamp": "24/02 15:45", "actor": "Planner HVAC", "event_type": "Preventiva programada", "description": "Janela reservada para execução antes do pico operacional.", "reference": "AGENDA-221"},
        ],
        "alerts": [
            {"severity": "warning", "title": "Ativo critico com aderencia abaixo da meta", "description": "Plano esta 8 pp abaixo da meta de aderencia do site."},
        ],
    },
    {
        "code": "PP-2026-002",
        "name": "Plano Camara Climatica Ensaios 1",
        "description": "Preventiva trimestral com calibração, inspeção de vedação e validação termo-higrométrica.",
        "asset_code": "CAMARA-CLIMATICA-01",
        "maintenance_strategy": "Preventiva baseada em tempo",
        "preventive_type": "Calibracao trimestral",
        "frequency": 90,
        "frequency_unit": "dias",
        "recurrence_rule": "A cada 90 dias com inspeção intermediaria quinzenal",
        "last_execution": "02/03/2026",
        "next_execution": "18/03/2026",
        "status": "Ativo",
        "adherence": "94%",
        "adherence_score": 94,
        "checklist_name": "Checklist Camara Climatica",
        "checklist_items": 24,
        "checklist_status": "Ativo",
        "checklist_updated_at": "01/03/2026",
        "responsible": "Fernanda Pires",
        "operational_window": "08:00-10:00",
        "delay_tolerance": "48 h",
        "auto_generate_os": True,
        "priority": "Alta",
        "technical_notes": "Validar sensores após qualquer oscilação acima da faixa de umidade.",
        "overdue": False,
        "due_soon": True,
        "critical_delay": False,
        "without_checklist": False,
        "coverage_risk": "Moderado",
        "on_time_executions": 11,
        "late_executions": 1,
        "coverage_status": "Cobertura estavel",
        "next_window_logic": "Gerar preventiva 5 dias antes da janela do laboratorio",
        "timeline": [
            {"timestamp": "02/03 08:00", "actor": "Equipe LAB", "event_type": "Preventiva executada", "description": "Checklist completo, limpeza interna e calibração térmica.", "reference": "PM-CC-12"},
            {"timestamp": "28/02 14:30", "actor": "Scheduler PM", "event_type": "OS preventiva gerada", "description": "Janela aberta para sábado sem impacto em ensaios.", "reference": "OS-2026-0149"},
        ],
        "alerts": [],
    },
    {
        "code": "PP-2026-003",
        "name": "Lubrificacao quinzenal das esteiras cardio",
        "description": "Rotina quinzenal de lubrificação, alinhamento e inspeção funcional das esteiras de alta demanda.",
        "asset_code": "ESTEIRA-ERG-12",
        "maintenance_strategy": "Preventiva por uso e tempo",
        "preventive_type": "Lubrificacao quinzenal",
        "frequency": 15,
        "frequency_unit": "dias",
        "recurrence_rule": "A cada 15 dias ou 220 h de uso, o que ocorrer primeiro",
        "last_execution": "14/02/2026",
        "next_execution": "13/03/2026",
        "status": "Vencido",
        "adherence": "76%",
        "adherence_score": 76,
        "checklist_name": "Checklist Cardio Floor",
        "checklist_items": 14,
        "checklist_status": "Ativo",
        "checklist_updated_at": "10/02/2026",
        "responsible": "Ana Lopes",
        "operational_window": "06:00-08:00",
        "delay_tolerance": "12 h",
        "auto_generate_os": False,
        "priority": "Alta",
        "technical_notes": "Revisar conjunto de placa e sistema de partida em ativos reincidentes do mesmo lote.",
        "overdue": True,
        "due_soon": False,
        "critical_delay": True,
        "without_checklist": False,
        "coverage_risk": "Alto",
        "on_time_executions": 6,
        "late_executions": 3,
        "coverage_status": "Cobertura degradada",
        "next_window_logic": "Gerar corretiva complementar se falha de partida persistir",
        "timeline": [
            {"timestamp": "12/03 08:24", "actor": "Juliana Costa", "event_type": "Preventiva vencida com corretiva associada", "description": "Falha de partida ocorreu com plano fora da janela.", "reference": "OS-2026-0151"},
            {"timestamp": "14/02 07:50", "actor": "Equipe Fitness", "event_type": "Preventiva executada", "description": "Lubrificacao, alinhamento e inspeção de correia.", "reference": "PM-CARDIO-12"},
            {"timestamp": "28/02 17:00", "actor": "Planner Fitness", "event_type": "Preventiva reprogramada", "description": "Janela perdida por alta ocupacao do cardio floor.", "reference": "REAG-038"},
        ],
        "alerts": [
            {"severity": "critical", "title": "Plano vencido em ativo com falha reincidente", "description": "Atraso preventivo associado a corretiva emergencial em equipamento de alta demanda."},
            {"severity": "warning", "title": "Geração automatica desabilitada", "description": "Plano depende de programação manual e perdeu a janela atual."},
        ],
    },
    {
        "code": "PP-2026-004",
        "name": "Inspecao termografica do inversor de envase",
        "description": "Inspecao mensal com termografia, reaperto e validacao de ventilacao do painel de automacao.",
        "asset_code": "INVERSOR-WEG-EST-03",
        "maintenance_strategy": "Preventiva por risco",
        "preventive_type": "Inspecao termografica mensal",
        "frequency": 30,
        "frequency_unit": "dias",
        "recurrence_rule": "Todo primeiro dia util do ciclo mensal",
        "last_execution": "18/02/2026",
        "next_execution": "20/03/2026",
        "status": "Ativo",
        "adherence": "92%",
        "adherence_score": 92,
        "checklist_name": "Checklist Painel de Automacao",
        "checklist_items": 16,
        "checklist_status": "Ativo",
        "checklist_updated_at": "05/03/2026",
        "responsible": "Bruno Salles",
        "operational_window": "13:00-15:00",
        "delay_tolerance": "24 h",
        "auto_generate_os": True,
        "priority": "Alta",
        "technical_notes": "Monitorar aquecimento em bornes e ventiladores de painel sob carga.",
        "overdue": False,
        "due_soon": False,
        "critical_delay": False,
        "without_checklist": False,
        "coverage_risk": "Moderado",
        "on_time_executions": 7,
        "late_executions": 1,
        "coverage_status": "Cobertura ativa",
        "next_window_logic": "Abrir ordem preventiva automatica 2 dias antes da janela",
        "timeline": [
            {"timestamp": "12/03 06:45", "actor": "Bruno Salles", "event_type": "OS preventiva gerada", "description": "Inspecao do painel gerada por risco termografico.", "reference": "OS-2026-0150"},
            {"timestamp": "18/02 11:10", "actor": "Equipe Automacao", "event_type": "Preventiva executada", "description": "Varredura termografica e reaperto geral do painel.", "reference": "PM-AUT-09"},
        ],
        "alerts": [],
    },
    {
        "code": "PP-2026-005",
        "name": "Revisao semanal do rooftop HVAC Norte",
        "description": "Rotina semanal de filtros, drenagem, bornes e medicao de corrente no rooftop da unidade norte.",
        "asset_code": "HVAC-ACADEMIA-02",
        "maintenance_strategy": "Preventiva de rotina",
        "preventive_type": "Limpeza tecnica semanal",
        "frequency": 7,
        "frequency_unit": "dias",
        "recurrence_rule": "Toda segunda-feira antes da abertura da unidade",
        "last_execution": "08/03/2026",
        "next_execution": "15/03/2026",
        "status": "Vencendo em breve",
        "adherence": "88%",
        "adherence_score": 88,
        "checklist_name": "Checklist Rooftop Norte",
        "checklist_items": 12,
        "checklist_status": "Ativo",
        "checklist_updated_at": "07/03/2026",
        "responsible": "Ana Lopes",
        "operational_window": "05:30-07:00",
        "delay_tolerance": "12 h",
        "auto_generate_os": True,
        "priority": "Media",
        "technical_notes": "Dar foco a drenagem e monitoramento de bandeja nas semanas de alta umidade.",
        "overdue": False,
        "due_soon": True,
        "critical_delay": False,
        "without_checklist": False,
        "coverage_risk": "Moderado",
        "on_time_executions": 10,
        "late_executions": 2,
        "coverage_status": "Cobertura estavel",
        "next_window_logic": "Proxima janela abre domingo a noite para equipe HVAC",
        "timeline": [
            {"timestamp": "10/03 14:20", "actor": "Ana Lopes", "event_type": "Preventiva reprogramada", "description": "Acesso ao telhado realocado para domingo.", "reference": "REAG-071"},
            {"timestamp": "08/03 06:25", "actor": "Equipe HVAC", "event_type": "Preventiva executada", "description": "Higienizacao de filtros e verificacao elétrica.", "reference": "PM-HVAC-07"},
        ],
        "alerts": [{"severity": "warning", "title": "Janela da semana muito curta", "description": "Plano entra em vencimento nas proximas 48 horas."}],
    },
    {
        "code": "PP-2026-006",
        "name": "Inspecao de vedacao do compressor de ar",
        "description": "Verificacao quinzenal de vazamentos, regulagem de pressão e integridade do kit de vedacao.",
        "asset_code": "COMPRESSOR-AR-01",
        "maintenance_strategy": "Preventiva por condição",
        "preventive_type": "Inspecao quinzenal",
        "frequency": 15,
        "frequency_unit": "dias",
        "recurrence_rule": "A cada 15 dias com reforco em caso de queda de pressao",
        "last_execution": "20/02/2026",
        "next_execution": "22/03/2026",
        "status": "Ativo",
        "adherence": "90%",
        "adherence_score": 90,
        "checklist_name": "",
        "checklist_items": 0,
        "checklist_status": "Nao vinculado",
        "checklist_updated_at": "-",
        "responsible": "",
        "operational_window": "09:00-11:00",
        "delay_tolerance": "24 h",
        "auto_generate_os": False,
        "priority": "Alta",
        "technical_notes": "Padronizar checklist e definir owner de utilidades para eliminar lacunas de cobertura.",
        "overdue": False,
        "due_soon": False,
        "critical_delay": False,
        "without_checklist": True,
        "coverage_risk": "Alto",
        "on_time_executions": 5,
        "late_executions": 1,
        "coverage_status": "Cobertura parcial",
        "next_window_logic": "Planejamento ainda manual, sem trigger automatico",
        "timeline": [
            {"timestamp": "12/03 09:05", "actor": "Lucas Neri", "event_type": "Falha associada ao plano", "description": "Queda de pressao reabriu discussao sobre padrao preventivo.", "reference": "OS-2026-0153"},
            {"timestamp": "20/02 08:45", "actor": "Equipe Utilidades", "event_type": "Preventiva executada", "description": "Inspecao visual e ajuste de regulagem.", "reference": "PM-UTIL-02"},
        ],
        "alerts": [
            {"severity": "warning", "title": "Plano sem checklist", "description": "Padrao preventivo ainda depende de memoria operacional da equipe."},
            {"severity": "warning", "title": "Sem responsavel definido", "description": "Necessario owner formal para garantir disciplina preventiva."},
        ],
    },
]


PREVENTIVE_SCHEDULE = [
    {
        "date": "12/03",
        "label": "Hoje",
        "items": [
            {"time": "06:00", "plan_code": "PP-2026-003", "title": "Lubrificacao quinzenal das esteiras cardio", "asset_code": "ESTEIRA-ERG-12", "site": "Unidade Centro", "responsible": "Ana Lopes", "status": "Vencido", "criticality": "Alta"},
            {"time": "13:00", "plan_code": "PP-2026-004", "title": "Inspecao termografica do inversor de envase", "asset_code": "INVERSOR-WEG-EST-03", "site": "Planta Maua", "responsible": "Bruno Salles", "status": "Programado", "criticality": "Critica"},
        ],
    },
    {
        "date": "13/03",
        "label": "Amanha",
        "items": [
            {"time": "08:30", "plan_code": "PP-2026-002", "title": "Plano Camara Climatica Ensaios 1", "asset_code": "CAMARA-CLIMATICA-01", "site": "Laboratorio Campinas", "responsible": "Fernanda Pires", "status": "Programado", "criticality": "Alta"},
        ],
    },
    {
        "date": "15/03",
        "label": "Domingo",
        "items": [
            {"time": "05:30", "plan_code": "PP-2026-005", "title": "Revisao semanal do rooftop HVAC Norte", "asset_code": "HVAC-ACADEMIA-02", "site": "Unidade Norte", "responsible": "Ana Lopes", "status": "Vencendo em breve", "criticality": "Alta"},
        ],
    },
]


PREVENTIVE_CALENDAR = [
    {"day": "10", "count": 1, "tone": "done", "items": ["Calibracao FORNO-LAB-01"]},
    {"day": "11", "count": 2, "tone": "done", "items": ["Checklist HVAC Norte", "Inspecao compressor"]},
    {"day": "12", "count": 2, "tone": "critical", "items": ["PP-2026-003 vencido", "PP-2026-004 programado"]},
    {"day": "13", "count": 1, "tone": "planned", "items": ["PP-2026-002"]},
    {"day": "14", "count": 0, "tone": "empty", "items": []},
    {"day": "15", "count": 1, "tone": "warning", "items": ["PP-2026-005"]},
    {"day": "16", "count": 1, "tone": "warning", "items": ["PP-2026-001"]},
    {"day": "18", "count": 1, "tone": "planned", "items": ["PP-2026-002 janela"]},
    {"day": "20", "count": 1, "tone": "planned", "items": ["PP-2026-004"]},
    {"day": "22", "count": 1, "tone": "planned", "items": ["PP-2026-006"]},
]


def _normalize(value):
    return (value or "").strip().lower()


def _site_to_client(site_name):
    for asset in ASSET_RECORDS:
        if asset["site"] == site_name:
            return asset["client"]
    return ""


def get_preventive_options(records=None):
    records = records or _build_enriched_records()
    return {
        "clients": sorted({item["client"] for item in records}),
        "sites": sorted({item["site"] for item in records}),
        "categories": sorted({item["asset"]["category"] for item in records}),
        "criticalities": sorted({item["asset"]["criticality"] for item in records}),
        "statuses": sorted({item["status"] for item in records}),
        "frequencies": sorted({f"{item['frequency']} {item['frequency_unit']}" for item in records}),
        "responsibles": sorted({item["responsible"] for item in records if item["responsible"]}),
    }


def _build_enriched_records(tenant_context=None):
    records = []
    for item in PREVENTIVE_PLAN_RECORDS:
        record = deepcopy(item)
        record["asset"] = get_asset_by_code(item["asset_code"], tenant_context=tenant_context) or {}
        record["client"] = record["asset"].get("client", "-")
        record["site"] = record["asset"].get("site", "-")
        record["sector"] = record["asset"].get("sector", "-")
        record["frequency_label"] = f"{record['frequency']} {record['frequency_unit']}"
        records.append(record)
    return filter_records_for_scope(records, tenant_context or {})


def filter_preventive_plans(filters=None, tenant_context=None):
    filters = filters or {}
    records = _build_enriched_records(tenant_context)
    search = _normalize(filters.get("search"))
    results = []
    for item in records:
        haystack = " ".join(
            [item["code"], item["name"], item["asset_code"], item["asset"].get("name", ""), item["client"], item["site"]]
        ).lower()
        if search and search not in haystack:
            continue
        if filters.get("client") and item["client"] != filters["client"]:
            continue
        if filters.get("site") and item["site"] != filters["site"]:
            continue
        if filters.get("category") and item["asset"].get("category") != filters["category"]:
            continue
        if filters.get("criticality") and item["asset"].get("criticality") != filters["criticality"]:
            continue
        if filters.get("status") and item["status"] != filters["status"]:
            continue
        if filters.get("frequency") and item["frequency_label"] != filters["frequency"]:
            continue
        if filters.get("responsible") and item["responsible"] != filters["responsible"]:
            continue
        if filters.get("overdue") == "yes" and not item["overdue"]:
            continue
        if filters.get("due_soon") == "yes" and not item["due_soon"]:
            continue
        if filters.get("auto_generate") == "yes" and not item["auto_generate_os"]:
            continue
        results.append(item)
    return results


def _build_filters(filters=None, records=None):
    filters = filters or {}
    options = get_preventive_options(records)
    return [
        {"label": "Buscar plano / ativo", "name": "search", "type": "search", "value": filters.get("search", ""), "placeholder": "Codigo, plano ou ativo"},
        {"label": "Cliente", "name": "client", "type": "select", "value": filters.get("client", ""), "options": options["clients"]},
        {"label": "Site / unidade", "name": "site", "type": "select", "value": filters.get("site", ""), "options": options["sites"]},
        {"label": "Categoria", "name": "category", "type": "select", "value": filters.get("category", ""), "options": options["categories"]},
        {"label": "Criticidade", "name": "criticality", "type": "select", "value": filters.get("criticality", ""), "options": options["criticalities"]},
        {"label": "Status do plano", "name": "status", "type": "select", "value": filters.get("status", ""), "options": options["statuses"]},
        {"label": "Frequencia", "name": "frequency", "type": "select", "value": filters.get("frequency", ""), "options": options["frequencies"]},
        {"label": "Responsavel", "name": "responsible", "type": "select", "value": filters.get("responsible", ""), "options": options["responsibles"]},
        {"label": "Com atraso", "name": "overdue", "type": "toggle", "value": filters.get("overdue", ""), "toggle_label": "Somente vencidos"},
        {"label": "Vencendo em breve", "name": "due_soon", "type": "toggle", "value": filters.get("due_soon", ""), "toggle_label": "Proximos da janela"},
        {"label": "Geração automatica", "name": "auto_generate", "type": "toggle", "value": filters.get("auto_generate", ""), "toggle_label": "Com auto OS ativa"},
        {"label": "Periodo", "name": "period", "type": "chips", "value": filters.get("period", "30 dias"), "options": ["Hoje", "7 dias", "30 dias", "Trimestre"]},
    ]


def get_preventive_listing_context(filters=None, tenant_context=None):
    filters = filters or {}
    all_plans = _build_enriched_records(tenant_context)
    plans = filter_preventive_plans(filters, tenant_context=tenant_context)
    covered_assets = {plan["asset_code"] for plan in all_plans}
    total_assets = len(ASSET_RECORDS)
    return {
        "page_actions": [
            {"label": "Nova OS preventiva", "route_name": "admin-shell:smart-system-work-order-create-preventive", "permission_domain": "work_orders", "permission_action": "create"},
            {"label": "Novo plano preventivo", "href": "#novo-plano", "permission_domain": "preventive_plans", "permission_action": "create"},
            {"label": "Programar preventiva", "href": "#programar-preventiva", "permission_domain": "preventive_plans", "permission_action": "manage"},
            {"label": "Abrir calendario", "route_name": "admin-shell:smart-system-preventives-calendar", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Exportar lista", "href": "#exportar-preventivas", "permission_domain": "preventive_plans", "permission_action": "export"},
            {"label": "Ver ativos sem plano", "href": "#ativos-sem-plano", "permission_domain": "assets", "permission_action": "view"},
            {"label": "Voltar ao dashboard", "route_name": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}, "permission_domain": "dashboard", "permission_action": "view"},
        ],
        "preventive_filters": _build_filters(filters, all_plans),
        "preventive_kpis": [
            {"label": "Planos ativos", "value": str(sum(1 for plan in all_plans if plan["status"] != "Inativo")), "context": "carteira preventiva", "trend": "foco em cobertura critica", "tone": "indigo"},
            {"label": "Programadas no periodo", "value": "14", "context": "agenda dos proximos 7 dias", "trend": "6 em ativos criticos", "tone": "sky"},
            {"label": "Preventivas vencidas", "value": str(sum(1 for plan in all_plans if plan["overdue"])), "context": "fora da janela de execucao", "trend": "concentradas no cardio floor", "tone": "red"},
            {"label": "Concluidas", "value": "11", "context": "ultimos 30 dias", "trend": "disciplina acima do mes anterior", "tone": "emerald"},
            {"label": "Aderencia preventiva", "value": "87%", "context": "media da carteira", "trend": "abaixo da meta em HVAC/cardio", "tone": "violet"},
        {"label": "Ativos cobertos", "value": str(len(covered_assets)), "context": f"{len(covered_assets)}/{total_assets} ativos mapeados", "trend": "cobertura no escopo ativo", "tone": "teal"},
        {"label": "Ativos sem plano", "value": str(max(total_assets - len(covered_assets), 0)), "context": "lacunas de cobertura preventiva", "trend": "ativos sem cobertura no contexto atual", "tone": "amber"},
            {"label": "Planos criticos em atraso", "value": str(sum(1 for plan in all_plans if plan["critical_delay"])), "context": "ativos de alto impacto", "trend": "agir antes da reincidencia", "tone": "orange"},
            {"label": "Execucao no prazo", "value": "84%", "context": "taxa de cumprimento dentro da janela", "trend": "+4 pp vs ciclo anterior", "tone": "cyan"},
            {"label": "Backlog preventivo", "value": str(sum(1 for plan in all_plans if plan["overdue"] or plan["due_soon"])), "context": "janela curta ou vencida", "trend": "3 itens exigem acao imediata", "tone": "rose"},
        ],
        "preventive_plans": plans,
    }


def get_preventive_schedule_context(tenant_context=None):
    scoped_groups = []
    for group in PREVENTIVE_SCHEDULE:
        items = [item for item in group["items"] if record_matches_scope({"client": _site_to_client(item["site"]), "site": item["site"]}, tenant_context or {})]
        if items:
            scoped_groups.append({**group, "items": items})
    return {
        "page_actions": [
            {"label": "Voltar aos planos", "route_name": "admin-shell:smart-system-preventives", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Abrir calendario", "route_name": "admin-shell:smart-system-preventives-calendar", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Programar preventiva", "href": "#programar", "permission_domain": "preventive_plans", "permission_action": "manage"},
        ],
        "schedule_groups": deepcopy(scoped_groups),
        "schedule_headline": [
            {"label": "Hoje", "value": "2 atividades"},
            {"label": "Semana", "value": "5 atividades"},
            {"label": "Atrasadas", "value": "1 atividade"},
            {"label": "Concluidas recentes", "value": "4 atividades"},
        ],
    }


def get_preventive_calendar_context(tenant_context=None):
    scoped_days = []
    for day in PREVENTIVE_CALENDAR:
        events = [
            event
            for event in day.get("events", [])
            if record_matches_scope({"client": _site_to_client(event["site"]), "site": event["site"]}, tenant_context or {})
        ]
        if events:
            scoped_days.append({**day, "events": events})
    return {
        "page_actions": [
            {"label": "Voltar aos planos", "route_name": "admin-shell:smart-system-preventives", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Abrir agenda", "route_name": "admin-shell:smart-system-preventives-schedule", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Exportar calendario", "href": "#exportar-calendario", "permission_domain": "preventive_plans", "permission_action": "export"},
        ],
        "calendar_month": "Março 2026",
        "calendar_days": deepcopy(scoped_days),
        "calendar_legend": [
            {"label": "Programado", "tone": "planned"},
            {"label": "Concluido", "tone": "done"},
            {"label": "Vencendo", "tone": "warning"},
            {"label": "Critico / vencido", "tone": "critical"},
        ],
    }


def get_preventive_plan_by_code(plan_code, tenant_context=None):
    target = _normalize(plan_code)
    for item in _build_enriched_records(tenant_context):
        if _normalize(item["code"]) == target:
            return deepcopy(item)
    return None


def get_preventive_detail_context(plan_code, tenant_context=None):
    plan = get_preventive_plan_by_code(plan_code, tenant_context=tenant_context)
    if plan is None:
        return None
    asset = plan["asset"]
    plan["page_actions"] = [
        {"label": "Programar execucao", "href": "#programar-execucao", "permission_domain": "preventive_plans", "permission_action": "manage"},
        {"label": "Gerar OS preventiva", "href": reverse("admin-shell:smart-system-work-order-create-preventive"), "permission_domain": "work_orders", "permission_action": "create"},
        {"label": "Abrir checklist", "href": f"/app/smart-system/checklists/?search={plan['asset_code']}", "permission_domain": "checklists", "permission_action": "view"},
        {"label": "Editar plano", "href": "#editar-plano", "permission_domain": "preventive_plans", "permission_action": "update"},
        {"label": "Abrir calendario", "route_name": "admin-shell:smart-system-preventives-calendar", "permission_domain": "preventive_plans", "permission_action": "view"},
        {"label": "Relatorio preventivo", "href": f"/app/smart-system/reports/preventive/{plan['code']}/", "permission_domain": "reports", "permission_action": "view"},
        {"label": "Baixar PDF", "href": f"/app/smart-system/reports/preventive/{plan['code']}/download/", "permission_domain": "reports", "permission_action": "export"},
        {"label": "Abrir ativo", "route_name": "admin-shell:smart-system-asset-detail", "route_kwargs": {"asset_code": asset["code"]}, "permission_domain": "assets", "permission_action": "view"},
    ]
    plan["summary_cards"] = [
        {"label": "Status atual", "value": plan["status"], "meta": "situacao do plano"},
        {"label": "Frequencia", "value": plan["frequency_label"], "meta": plan["preventive_type"]},
        {"label": "Ultima execucao", "value": plan["last_execution"], "meta": "ultima janela realizada"},
        {"label": "Proxima execucao", "value": plan["next_execution"], "meta": "janela futura"},
        {"label": "Atraso atual", "value": "3 dias" if plan["overdue"] else "Dentro da janela", "meta": plan["delay_tolerance"]},
        {"label": "Aderencia", "value": plan["adherence"], "meta": "disciplina preventiva"},
        {"label": "Responsavel", "value": plan["responsible"] or "Sem responsavel", "meta": "owner do plano"},
        {"label": "Checklist", "value": plan["checklist_name"] or "Nao vinculado", "meta": f"{plan['checklist_items']} itens"},
        {"label": "Geracao automatica", "value": "Ativa" if plan["auto_generate_os"] else "Desabilitada", "meta": "trigger de OS preventiva"},
        {"label": "Criticidade do ativo", "value": asset.get("criticality", "-"), "meta": asset.get("name", "-")},
    ]
    plan["plan_info"] = [
        {"label": "Nome do plano", "value": plan["name"]},
        {"label": "Descricao", "value": plan["description"]},
        {"label": "Estrategia preventiva", "value": plan["maintenance_strategy"]},
        {"label": "Tipo de manutencao", "value": plan["preventive_type"]},
        {"label": "Frequencia", "value": plan["frequency_label"]},
        {"label": "Regra de recorrencia", "value": plan["recurrence_rule"]},
        {"label": "Tolerancia", "value": plan["delay_tolerance"]},
        {"label": "Janela operacional", "value": plan["operational_window"]},
        {"label": "Prioridade", "value": plan["priority"]},
        {"label": "Observacoes tecnicas", "value": plan["technical_notes"]},
    ]
    plan["asset_info"] = [
        {"label": "Ativo", "value": asset.get("name", "-")},
        {"label": "Tag / codigo", "value": asset.get("code", "-")},
        {"label": "Categoria", "value": f"{asset.get('category', '-')} / {asset.get('subcategory', '-')}"},
        {"label": "Cliente", "value": asset.get("client", "-")},
        {"label": "Site", "value": asset.get("site", "-")},
        {"label": "Setor / localizacao", "value": asset.get("sector", "-")},
        {"label": "Criticidade do ativo", "value": asset.get("criticality", "-")},
        {"label": "Status operacional", "value": asset.get("operational_status", "-")},
    ]
    plan["recurrence_panel"] = {
        "frequency": plan["frequency_label"],
        "periodicity": plan["preventive_type"],
        "rule_summary": plan["recurrence_rule"],
        "next_window": plan["next_execution"],
        "delay_accumulated": "3 dias" if plan["overdue"] else "0 dia",
        "next_logic": plan["next_window_logic"],
    }
    plan["adherence_panel"] = {
        "adherence": plan["adherence"],
        "on_time_executions": plan["on_time_executions"],
        "late_executions": plan["late_executions"],
        "coverage": plan["coverage_status"],
        "risk": plan["coverage_risk"],
        "impact": "Nao executar na janela aumenta risco de falha e reduz disciplina preventiva do ativo.",
    }
    plan["checklist_panel"] = {
        "name": plan["checklist_name"] or "Checklist nao vinculado",
        "items": plan["checklist_items"],
        "status": plan["checklist_status"],
        "updated_at": plan["checklist_updated_at"],
        "actions": [
            {"label": "Visualizar checklist", "href": "#ver-checklist"},
            {"label": "Vincular checklist", "href": "#vincular-checklist"},
        ],
    }
    plan["action_panel"] = [
        {"label": "Programar preventiva", "href": "#programar", "permission_domain": "preventive_plans", "permission_action": "manage"},
        {"label": "Gerar ordem de servico", "href": reverse("admin-shell:smart-system-work-order-create-preventive"), "permission_domain": "work_orders", "permission_action": "create"},
        {"label": "Registrar execucao", "href": "#registrar-execucao", "permission_domain": "preventive_plans", "permission_action": "execute"},
        {"label": "Abrir checklist", "href": f"/app/smart-system/checklists/?search={asset['code']}", "permission_domain": "checklists", "permission_action": "view"},
        {"label": "Reprogramar", "href": "#reprogramar", "permission_domain": "preventive_plans", "permission_action": "manage"},
        {"label": "Editar plano", "href": "#editar", "permission_domain": "preventive_plans", "permission_action": "update"},
        {"label": "Vincular checklist", "href": "#checklist", "permission_domain": "checklists", "permission_action": "update"},
        {"label": "Pausar plano", "href": "#pausar", "permission_domain": "preventive_plans", "permission_action": "manage"},
        {"label": "Abrir ativo", "route_name": "admin-shell:smart-system-asset-detail", "route_kwargs": {"asset_code": asset["code"]}, "permission_domain": "assets", "permission_action": "view"},
    ]
    return plan
