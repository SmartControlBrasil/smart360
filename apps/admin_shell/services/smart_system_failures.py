from copy import deepcopy

from .smart_system_assets import get_asset_by_code
from .smart_system_work_orders import get_work_order_by_code
from .tenant_scope import filter_records_for_scope, record_matches_scope


FAILURE_EVENT_RECORDS = [
    {
        "code": "FE-2026-001",
        "asset_code": "CHILLER-UNID-A",
        "work_order_code": "OS-2026-0148",
        "occurred_at": "12/03/2026 07:04",
        "failure_type": "Falha de processo",
        "failure_mode": "Sobreaquecimento / oscilacao termica",
        "severity": "Critica",
        "impact_level": "Alto",
        "status": "Em analise",
        "description": "Oscilacao de temperatura com queda de capacidade do chiller e perda de estabilidade no setpoint da area premium.",
        "responsible": "Carlos Mota",
        "downtime": "2,4 h",
        "recurrence": "Alta",
        "diagnosis_completed": True,
        "rca_completed": False,
        "with_work_order": True,
        "symptoms": [
            "alarme de temperatura no supervisório",
            "queda de eficiencia de resfriamento",
            "variacao de fluxo no circuito secundario",
        ],
        "components": ["sensor de fluxo", "evaporador", "linha secundaria"],
        "hypotheses": [
            "sensor de fluxo com leitura intermitente",
            "incrustacao parcial em evaporador",
            "restricao em circuito secundario",
        ],
        "evidences": [
            "historico de temperatura acima do setpoint nas ultimas 6 horas",
            "inspecao visual com indicio de incrustacao",
            "oscilacao no valor lido pelo sensor de fluxo",
        ],
        "root_cause": {
            "cause": "Incrustacao parcial no evaporador combinada com sensor de fluxo fora da faixa.",
            "category": "Condicao / instrumentacao",
            "corrective_action": "Limpeza do evaporador, substituicao preventiva do sensor e revisao da janela de monitoramento.",
            "preventive_recommendation": "Aumentar frequencia de inspeção de fluxo e revisar procedimento de limpeza trimestral.",
            "recurrence_probability": "Alta sem ajuste do plano preventivo",
            "systemic_impact": "Pode afetar outras unidades com mesmo padrao de limpeza insuficiente.",
        },
        "operational_impact": {
            "downtime": "2,4 h",
            "impact_summary": "Comprometeu conforto termico da area premium e exigiu contingencia operacional.",
            "financial_estimate": "R$ 4.800 estimados",
            "affected_output": "Reducao da capacidade operacional da unidade no horario de pico",
            "criticality": "Critica",
        },
        "timeline": [
            {"timestamp": "12/03 07:04", "actor": "Monitoramento operacional", "event_type": "Falha registrada", "description": "Temperatura acima da faixa e queda de eficiencia do chiller.", "reference": "SCADA-ALM-44"},
            {"timestamp": "12/03 07:18", "actor": "Central de operacoes", "event_type": "OS criada", "description": "Corretiva emergencial aberta para investigacao.", "reference": "OS-2026-0148"},
            {"timestamp": "12/03 09:12", "actor": "Carlos Mota", "event_type": "Diagnostico inserido", "description": "Confirmada oscilacao de fluxo e indicio de incrustacao parcial.", "reference": "DX-148"},
        ],
        "asset_history": [
            {"timestamp": "11/03 18:42", "type": "Falha anterior", "description": "Oscilacao termica com acionamento parcial do compressor.", "reference": "FE-0096"},
            {"timestamp": "27/02 09:00", "type": "Preventiva executada", "description": "Checklist de utilidades e limpeza de serpentina.", "reference": "PM-HVAC-01"},
            {"timestamp": "30/01 13:15", "type": "OS concluida", "description": "Revisao de sensor de temperatura e bornes do painel.", "reference": "OS-2026-0104"},
        ],
        "alerts": [
            {"severity": "critical", "title": "Falha recorrente em ativo critico", "description": "Terceira ocorrencia similar em menos de 45 dias."},
            {"severity": "warning", "title": "RCA ainda nao concluida", "description": "Evento critico segue sem causa raiz formalizada."},
        ],
    },
    {
        "code": "FE-2026-002",
        "asset_code": "ESTEIRA-ERG-12",
        "work_order_code": "OS-2026-0151",
        "occurred_at": "12/03/2026 08:10",
        "failure_type": "Falha eletrica",
        "failure_mode": "Falha de partida",
        "severity": "Alta",
        "impact_level": "Alto",
        "status": "Aguardando material",
        "description": "Esteira nao inicia corrida e desarma durante a partida em horario de pico.",
        "responsible": "Ana Lopes",
        "downtime": "6,0 h",
        "recurrence": "Alta",
        "diagnosis_completed": True,
        "rca_completed": True,
        "with_work_order": True,
        "symptoms": [
            "desarme na partida",
            "tela de erro no conjunto de acionamento",
            "odor de aquecimento na placa",
        ],
        "components": ["placa de potencia", "capacitor de partida", "conjunto de acionamento"],
        "hypotheses": [
            "falha intermitente na placa de potencia",
            "capacitor fora da faixa nominal",
            "desgaste acelerado por carga de pico",
        ],
        "evidences": [
            "medicao do capacitor abaixo do especificado",
            "registro de sobrecorrente em duas partidas consecutivas",
            "historico recente de corretivas similares no mesmo lote",
        ],
        "root_cause": {
            "cause": "Desgaste acelerado do conjunto de acionamento com capacitor degradado em equipamento de uso intensivo.",
            "category": "Componente / desgaste",
            "corrective_action": "Troca da placa de potencia e capacitor principal, com revisão do lote semelhante.",
            "preventive_recommendation": "Aumentar periodicidade de inspeção eletrica e reavaliar politica de substituição do lote.",
            "recurrence_probability": "Media apos troca do conjunto",
            "systemic_impact": "Outras esteiras do mesmo lote podem apresentar a mesma curva de falha.",
        },
        "operational_impact": {
            "downtime": "6,0 h",
            "impact_summary": "Equipamento indisponivel em area de alta demanda, com fila e redistribuicao de uso.",
            "financial_estimate": "R$ 2.300 estimados",
            "affected_output": "Reducao da capacidade da area cardio no horario de pico",
            "criticality": "Alta",
        },
        "timeline": [
            {"timestamp": "12/03 08:10", "actor": "Ana Lopes", "event_type": "Falha registrada", "description": "Falha de partida com desarme do equipamento.", "reference": "FE-2026-002"},
            {"timestamp": "12/03 08:24", "actor": "Juliana Costa", "event_type": "OS criada", "description": "Corretiva emergencial aberta para placa de potencia.", "reference": "OS-2026-0151"},
            {"timestamp": "12/03 09:18", "actor": "Ana Lopes", "event_type": "Diagnostico inserido", "description": "Falha de placa e capacitor principal fora da faixa.", "reference": "DX-151"},
            {"timestamp": "12/03 09:34", "actor": "Supply Desk", "event_type": "Peca solicitada", "description": "Pedido da placa RT250 e capacitor encaminhado ao almoxarifado.", "reference": "MAT-4021"},
        ],
        "asset_history": [
            {"timestamp": "14/02 07:50", "type": "Preventiva executada", "description": "Lubrificacao, alinhamento e inspeção de correia.", "reference": "PM-CARDIO-12"},
            {"timestamp": "20/01 08:16", "type": "Falha anterior", "description": "Desarme durante aceleracao em horario de pico.", "reference": "FE-0088"},
            {"timestamp": "10/12 16:20", "type": "OS concluida", "description": "Substituição de capacitor de partida.", "reference": "OS-2025-119"},
        ],
        "alerts": [
            {"severity": "critical", "title": "Ativo de alta demanda com reincidencia", "description": "Quarta falha relacionada ao sistema de partida em 60 dias."},
        ],
    },
    {
        "code": "FE-2026-003",
        "asset_code": "CAMARA-CLIMATICA-01",
        "work_order_code": "OS-2026-0149",
        "occurred_at": "09/02/2026 15:20",
        "failure_type": "Falha de processo",
        "failure_mode": "Oscilacao de umidade",
        "severity": "Alta",
        "impact_level": "Medio",
        "status": "Resolvida",
        "description": "Umidade acima da faixa operacional durante ensaio de estabilidade.",
        "responsible": "Fernanda Pires",
        "downtime": "1,6 h",
        "recurrence": "Media",
        "diagnosis_completed": True,
        "rca_completed": True,
        "with_work_order": True,
        "symptoms": ["umidade fora da faixa", "instabilidade do setpoint", "alarme de compensacao"],
        "components": ["sensor de umidade", "vedacao de porta"],
        "hypotheses": ["desvio de calibração", "microvazamento em vedacao", "compensacao incorreta do controlador"],
        "evidences": ["teste de vedação com pequena perda", "comparativo de leitura mostrou desvio do sensor"],
        "root_cause": {
            "cause": "Sensor de umidade fora de calibração com desgaste parcial da vedação frontal.",
            "category": "Instrumentacao / vedacao",
            "corrective_action": "Recalibracao do sensor e ajuste da vedação frontal.",
            "preventive_recommendation": "Incluir teste de vedacao em toda rotina trimestral.",
            "recurrence_probability": "Baixa",
            "systemic_impact": "Baixo impacto sistêmico; restrito ao ativo.",
        },
        "operational_impact": {
            "downtime": "1,6 h",
            "impact_summary": "Reprogramacao pontual de ensaio laboratorial.",
            "financial_estimate": "R$ 950 estimados",
            "affected_output": "Atraso de um ciclo de ensaio",
            "criticality": "Alta",
        },
        "timeline": [
            {"timestamp": "09/02 15:20", "actor": "Lucas Neri", "event_type": "Falha registrada", "description": "Oscilacao de umidade durante ensaio premium.", "reference": "FE-2026-003"},
            {"timestamp": "09/02 15:42", "actor": "Backoffice LAB", "event_type": "OS criada", "description": "Atendimento corretivo preventivo vinculado ao plano da camara.", "reference": "OS-2026-0149"},
            {"timestamp": "10/02 09:10", "actor": "Fernanda Pires", "event_type": "RCA concluida", "description": "Confirmada vedacao com pequena perda e sensor fora da faixa.", "reference": "RCA-CC-19"},
        ],
        "asset_history": [
            {"timestamp": "02/03 08:00", "type": "Preventiva executada", "description": "Checklist completo, limpeza interna e recalibracao.", "reference": "PM-CC-12"},
            {"timestamp": "21/11 10:30", "type": "Falha anterior", "description": "Leitura de umidade acima da faixa em ensaio noturno.", "reference": "FE-0071"},
        ],
        "alerts": [],
    },
    {
        "code": "FE-2026-004",
        "asset_code": "INVERSOR-WEG-EST-03",
        "work_order_code": "OS-2026-0150",
        "occurred_at": "11/03/2026 17:35",
        "failure_type": "Falha eletrica",
        "failure_mode": "Aquecimento em painel / bornes",
        "severity": "Critica",
        "impact_level": "Alto",
        "status": "Em observacao",
        "description": "Inspecao preliminar identificou hotspots em bornes e ventilacao insuficiente no painel do inversor.",
        "responsible": "Bruno Salles",
        "downtime": "0,8 h",
        "recurrence": "Media",
        "diagnosis_completed": False,
        "rca_completed": False,
        "with_work_order": True,
        "symptoms": ["aquecimento localizado", "odor leve de aquecimento", "alerta termografico"],
        "components": ["bornes de potencia", "ventilacao do painel", "ventilador interno"],
        "hypotheses": ["mau reaperto", "ventilacao insuficiente", "sujeira acumulada no painel"],
        "evidences": ["termografia com hotspot em borne superior", "tendencia de temperatura acima da media"],
        "root_cause": {
            "cause": "RCA em elaboracao.",
            "category": "Em analise",
            "corrective_action": "A definir apos inspeção termografica completa.",
            "preventive_recommendation": "A definir.",
            "recurrence_probability": "Indefinida",
            "systemic_impact": "Possivel extensao para outros painéis com mesmo padrão construtivo.",
        },
        "operational_impact": {
            "downtime": "0,8 h",
            "impact_summary": "Risco de parada da celula de envase se aquecimento aumentar.",
            "financial_estimate": "R$ 3.400 potenciais",
            "affected_output": "Throughput da linha em risco",
            "criticality": "Critica",
        },
        "timeline": [
            {"timestamp": "11/03 17:35", "actor": "Bruno Salles", "event_type": "Falha registrada", "description": "Hotspot termografico identificado em borne de painel.", "reference": "THERM-221"},
            {"timestamp": "12/03 06:45", "actor": "Planner Automacao", "event_type": "OS criada", "description": "Inspecao formal do painel aberta para equipe de automacao.", "reference": "OS-2026-0150"},
        ],
        "asset_history": [
            {"timestamp": "18/02 11:10", "type": "Preventiva executada", "description": "Varredura termografica e reaperto geral do painel.", "reference": "PM-AUT-09"},
            {"timestamp": "30/01 13:45", "type": "OS concluida", "description": "Troca de ventilador interno e atualização de parâmetros.", "reference": "OS-2026-0109"},
        ],
        "alerts": [
            {"severity": "warning", "title": "Diagnostico pendente", "description": "Evento relevante segue sem diagnostico consolidado."},
            {"severity": "warning", "title": "RCA nao preenchida", "description": "Falha critica ainda sem causa raiz formal."},
        ],
    },
    {
        "code": "FE-2026-005",
        "asset_code": "COMPRESSOR-AR-01",
        "work_order_code": "OS-2026-0153",
        "occurred_at": "12/03/2026 09:05",
        "failure_type": "Falha mecanica",
        "failure_mode": "Perda de pressao / vazamento",
        "severity": "Alta",
        "impact_level": "Medio",
        "status": "Aberta",
        "description": "Queda de pressao na rede de utilidades com impacto em ensaios pneumaticos e instabilidade na linha.",
        "responsible": "",
        "downtime": "1,1 h",
        "recurrence": "Media",
        "diagnosis_completed": False,
        "rca_completed": False,
        "with_work_order": True,
        "symptoms": ["queda de pressao", "variacao no regulador", "ruido de vazamento em linha secundaria"],
        "components": ["kit de vedacao", "regulador", "linha secundaria"],
        "hypotheses": ["microvazamento", "vedacao degradada", "regulador fora de ajuste"],
        "evidences": ["queda de pressao registrada em utilidades", "chamado da produção por perda de estabilidade"],
        "root_cause": {
            "cause": "Em investigacao.",
            "category": "Em analise",
            "corrective_action": "A definir apos triagem e inspeção com detector ultrassonico.",
            "preventive_recommendation": "A definir.",
            "recurrence_probability": "Media",
            "systemic_impact": "Pode afetar demais ensaios pneumaticos se a rede estiver degradada.",
        },
        "operational_impact": {
            "downtime": "1,1 h",
            "impact_summary": "Afetou ensaios pneumaticos e exigiu contingencia parcial.",
            "financial_estimate": "R$ 1.700 estimados",
            "affected_output": "Redução pontual da disponibilidade de utilidades",
            "criticality": "Alta",
        },
        "timeline": [
            {"timestamp": "12/03 09:05", "actor": "Lucas Neri", "event_type": "Falha registrada", "description": "Queda de pressao afetando testes pneumaticos.", "reference": "FE-2026-005"},
            {"timestamp": "12/03 09:17", "actor": "Backoffice tecnico", "event_type": "OS criada", "description": "Chamado encaminhado para fila de utilidades.", "reference": "OS-2026-0153"},
        ],
        "asset_history": [
            {"timestamp": "29/01 17:10", "type": "OS concluida", "description": "Substituicao de kit de vedacao e ajuste de pressão.", "reference": "OS-2026-0102"},
            {"timestamp": "20/02 08:45", "type": "Preventiva executada", "description": "Inspecao visual e ajuste de regulagem.", "reference": "PM-UTIL-02"},
        ],
        "alerts": [
            {"severity": "warning", "title": "Sem responsavel definido", "description": "Evento aberto sem tecnico individual atribuido."},
        ],
    },
]


def _normalize(value):
    return (value or "").strip().lower()


def _enrich_failure(item):
    failure = deepcopy(item)
    failure["asset"] = get_asset_by_code(item["asset_code"]) or {}
    failure["client"] = failure["asset"].get("client", "-")
    failure["site"] = failure["asset"].get("site", "-")
    failure["sector"] = failure["asset"].get("sector", "-")
    failure["work_order"] = get_work_order_by_code(item["work_order_code"]) if item.get("work_order_code") else None
    failure["has_diagnosis"] = item["diagnosis_completed"]
    failure["has_rca"] = item["rca_completed"]
    return failure


def get_failure_options(records=None):
    records = records or [_enrich_failure(item) for item in FAILURE_EVENT_RECORDS]
    return {
        "assets": sorted({item["asset_code"] for item in records}),
        "clients": sorted({item["client"] for item in records}),
        "sites": sorted({item["site"] for item in records}),
        "types": sorted({item["failure_type"] for item in records}),
        "severities": sorted({item["severity"] for item in records}),
        "recurrences": sorted({item["recurrence"] for item in records}),
        "responsibles": sorted({item["responsible"] for item in records if item["responsible"]}),
    }


def filter_failures(filters=None, tenant_context=None):
    filters = filters or {}
    search = _normalize(filters.get("search"))
    results = []
    for item in filter_records_for_scope(FAILURE_EVENT_RECORDS, tenant_context or {}):
        failure = _enrich_failure(item)
        haystack = " ".join(
            [
                failure["code"],
                failure["asset_code"],
                failure["asset"].get("name", ""),
                failure["failure_type"],
                failure["failure_mode"],
                failure["client"],
                failure["site"],
            ]
        ).lower()
        if search and search not in haystack:
            continue
        if filters.get("asset") and failure["asset_code"] != filters["asset"]:
            continue
        if filters.get("client") and failure["client"] != filters["client"]:
            continue
        if filters.get("site") and failure["site"] != filters["site"]:
            continue
        if filters.get("failure_type") and failure["failure_type"] != filters["failure_type"]:
            continue
        if filters.get("severity") and failure["severity"] != filters["severity"]:
            continue
        if filters.get("recurrence") and failure["recurrence"] != filters["recurrence"]:
            continue
        if filters.get("responsible") and failure["responsible"] != filters["responsible"]:
            continue
        if filters.get("with_work_order") == "yes" and not failure["with_work_order"]:
            continue
        if filters.get("without_diagnosis") == "yes" and failure["diagnosis_completed"]:
            continue
        results.append(failure)
    return results


def _build_filters(filters=None, records=None):
    filters = filters or {}
    options = get_failure_options(records)
    return [
        {"label": "Buscar falha / ativo", "name": "search", "type": "search", "value": filters.get("search", ""), "placeholder": "Codigo, ativo ou modo de falha"},
        {"label": "Ativo", "name": "asset", "type": "select", "value": filters.get("asset", ""), "options": options["assets"]},
        {"label": "Cliente", "name": "client", "type": "select", "value": filters.get("client", ""), "options": options["clients"]},
        {"label": "Site / unidade", "name": "site", "type": "select", "value": filters.get("site", ""), "options": options["sites"]},
        {"label": "Tipo de falha", "name": "failure_type", "type": "select", "value": filters.get("failure_type", ""), "options": options["types"]},
        {"label": "Severidade", "name": "severity", "type": "select", "value": filters.get("severity", ""), "options": options["severities"]},
        {"label": "Recorrencia", "name": "recurrence", "type": "select", "value": filters.get("recurrence", ""), "options": options["recurrences"]},
        {"label": "Tecnico responsavel", "name": "responsible", "type": "select", "value": filters.get("responsible", ""), "options": options["responsibles"]},
        {"label": "Com OS associada", "name": "with_work_order", "type": "toggle", "value": filters.get("with_work_order", ""), "toggle_label": "Somente com OS"},
        {"label": "Sem diagnostico", "name": "without_diagnosis", "type": "toggle", "value": filters.get("without_diagnosis", ""), "toggle_label": "Pendentes de diagnostico"},
        {"label": "Periodo", "name": "period", "type": "chips", "value": filters.get("period", "30 dias"), "options": ["Hoje", "7 dias", "30 dias", "Trimestre"]},
    ]


def get_failure_listing_context(filters=None, tenant_context=None):
    filters = filters or {}
    records = [_enrich_failure(item) for item in filter_records_for_scope(FAILURE_EVENT_RECORDS, tenant_context or {})]
    failures = filter_failures(filters, tenant_context=tenant_context)
    return {
        "page_actions": [
            {"label": "Registrar falha", "href": "#registrar-falha", "permission_domain": "failures", "permission_action": "create"},
            {"label": "Abrir OS", "route_name": "admin-shell:smart-system-work-orders", "permission_domain": "work_orders", "permission_action": "view"},
            {"label": "Ver ativos", "route_name": "admin-shell:smart-system-assets", "permission_domain": "assets", "permission_action": "view"},
            {"label": "Exportar lista", "href": "#exportar-falhas", "permission_domain": "failures", "permission_action": "export"},
            {"label": "Voltar ao dashboard", "route_name": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}, "permission_domain": "dashboard", "permission_action": "view"},
        ],
        "failure_filters": _build_filters(filters, records),
        "failure_kpis": [
            {"label": "Falhas no periodo", "value": str(len(records)), "context": "eventos registrados no ciclo atual", "trend": "concentracao em HVAC e cardio", "tone": "indigo"},
            {"label": "Falhas criticas", "value": str(sum(1 for item in records if item["severity"] == "Critica")), "context": "ativos de alto impacto", "trend": "2 com RCA pendente", "tone": "red"},
            {"label": "Falhas recorrentes", "value": str(sum(1 for item in records if item["recurrence"] == "Alta")), "context": "repeticao acima do baseline", "trend": "pedem revisao preventiva", "tone": "amber"},
            {"label": "Ativos com maior incidencia", "value": "CHILLER / ESTEIRA", "context": "top recorrencia do periodo", "trend": "foco de engenharia", "tone": "orange"},
            {"label": "Horas de parada", "value": "11,9 h", "context": "downtime acumulado", "trend": "maior parte em cardio e HVAC", "tone": "rose"},
            {"label": "Falhas resolvidas", "value": str(sum(1 for item in records if item["status"] == "Resolvida")), "context": "eventos encerrados", "trend": "RCA completa em laboratorio", "tone": "emerald"},
            {"label": "Falhas abertas", "value": str(sum(1 for item in records if item["status"] in {"Aberta", "Em analise", "Aguardando material", "Em observacao"})), "context": "seguem exigindo acao", "trend": "3 com risco operacional relevante", "tone": "sky"},
            {"label": "Tendencia de falhas", "value": "+12%", "context": "comparado ao ciclo anterior", "trend": "cardio e utilidades puxam alta", "tone": "violet"},
        ],
        "failures": failures,
    }


def get_failure_by_code(failure_code, tenant_context=None):
    target = _normalize(failure_code)
    for item in FAILURE_EVENT_RECORDS:
        if _normalize(item["code"]) == target and record_matches_scope(
            {"client": _enrich_failure(item)["client"], "site": _enrich_failure(item)["site"]},
            tenant_context or {},
        ):
            return _enrich_failure(item)
    return None


def get_failure_detail_context(failure_code, tenant_context=None):
    failure = get_failure_by_code(failure_code, tenant_context=tenant_context)
    if failure is None:
        return None
    asset = failure["asset"]
    failure["page_actions"] = [
        {"label": "Abrir OS", "route_name": "admin-shell:smart-system-work-order-detail", "route_kwargs": {"order_code": failure['work_order_code']}, "permission_domain": "work_orders", "permission_action": "view"},
        {"label": "Editar evento", "href": "#editar-falha", "permission_domain": "failures", "permission_action": "update"},
        {"label": "Registrar diagnostico", "href": "#registrar-diagnostico", "permission_domain": "failures", "permission_action": "update"},
        {"label": "Registrar causa raiz", "href": "#registrar-rca", "permission_domain": "failures", "permission_action": "rca"},
        {"label": "Anexar evidencia", "href": "#anexar-evidencia", "permission_domain": "work_execution", "permission_action": "log_evidence"},
        {"label": "Relatorio RCA", "href": f"/app/smart-system/reports/failure/{failure['code']}/", "permission_domain": "reports", "permission_action": "view"},
        {"label": "Baixar PDF", "href": f"/app/smart-system/reports/failure/{failure['code']}/download/", "permission_domain": "reports", "permission_action": "export"},
        {"label": "Abrir ativo", "route_name": "admin-shell:smart-system-asset-detail", "route_kwargs": {"asset_code": asset['code']}, "permission_domain": "assets", "permission_action": "view"},
    ]
    failure["summary_cards"] = [
        {"label": "Status", "value": failure["status"], "meta": "situacao do evento"},
        {"label": "Severidade", "value": failure["severity"], "meta": failure["failure_mode"]},
        {"label": "Impacto", "value": failure["impact_level"], "meta": failure["operational_impact"]["impact_summary"]},
        {"label": "Parada", "value": failure["downtime"], "meta": "tempo acumulado"},
        {"label": "Responsavel", "value": failure["responsible"] or "Sem responsavel", "meta": "owner tecnico"},
        {"label": "OS vinculada", "value": failure["work_order_code"], "meta": failure["work_order"]["title"] if failure["work_order"] else "Sem OS"},
        {"label": "Diagnostico", "value": "Preenchido" if failure["has_diagnosis"] else "Pendente", "meta": "base tecnica do evento"},
        {"label": "RCA", "value": "Preenchido" if failure["has_rca"] else "Pendente", "meta": "causa raiz formal"},
    ]
    failure["diagnosis_panel"] = [
        {"label": "Descricao do diagnostico", "value": failure["description"]},
        {"label": "Sintomas", "value": ", ".join(failure["symptoms"])},
        {"label": "Componentes envolvidos", "value": ", ".join(failure["components"])},
        {"label": "Hipoteses avaliadas", "value": ", ".join(failure["hypotheses"])},
        {"label": "Evidencias", "value": ", ".join(failure["evidences"])},
    ]
    failure["rca_panel"] = [
        {"label": "Causa raiz", "value": failure["root_cause"]["cause"]},
        {"label": "Categoria da causa", "value": failure["root_cause"]["category"]},
        {"label": "Acao corretiva", "value": failure["root_cause"]["corrective_action"]},
        {"label": "Recomendacao preventiva", "value": failure["root_cause"]["preventive_recommendation"]},
        {"label": "Recorrencia provavel", "value": failure["root_cause"]["recurrence_probability"]},
        {"label": "Impacto sistemico", "value": failure["root_cause"]["systemic_impact"]},
    ]
    failure["impact_panel"] = [
        {"label": "Tempo de parada", "value": failure["operational_impact"]["downtime"]},
        {"label": "Impacto na operacao", "value": failure["operational_impact"]["impact_summary"]},
        {"label": "Impacto financeiro estimado", "value": failure["operational_impact"]["financial_estimate"]},
        {"label": "Producao / servico afetado", "value": failure["operational_impact"]["affected_output"]},
        {"label": "Criticidade", "value": failure["operational_impact"]["criticality"]},
    ]
    failure["action_panel"] = [
        {"label": "Abrir OS", "route_name": "admin-shell:smart-system-work-order-detail", "route_kwargs": {"order_code": failure["work_order_code"]}, "permission_domain": "work_orders", "permission_action": "view"},
        {"label": "Registrar diagnostico", "href": "#diagnostico", "permission_domain": "failures", "permission_action": "update"},
        {"label": "Registrar RCA", "href": "#rca", "permission_domain": "failures", "permission_action": "rca"},
        {"label": "Anexar evidencia", "href": "#evidencia", "permission_domain": "work_execution", "permission_action": "log_evidence"},
        {"label": "Abrir ativo", "route_name": "admin-shell:smart-system-asset-detail", "route_kwargs": {"asset_code": asset["code"]}, "permission_domain": "assets", "permission_action": "view"},
        {"label": "Exportar relatorio", "href": "#exportar-relatorio", "permission_domain": "reports", "permission_action": "export"},
    ]
    return failure
