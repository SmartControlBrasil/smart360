from copy import deepcopy

from .smart_system_assets import get_asset_by_code
from .smart_system_preventives import get_preventive_plan_by_code
from .smart_system_work_orders import get_work_order_by_code
from .tenant_scope import filter_records_for_scope, record_matches_scope


CHECKLIST_RECORDS = [
    {
        "code": "CHK-2026-001",
        "name": "Inspecao Preventiva de Camara Climatica",
        "description": "Checklist trimestral para validacao termo-higrometrica, vedacao e instrumentacao.",
        "category": "Laboratorio",
        "checklist_type": "Preventiva",
        "asset_code": "CAMARA-CLIMATICA-01",
        "asset_category": "Camara climatica",
        "client": "Laboratorio Exemplo",
        "site": "Laboratorio Campinas",
        "criticality": "Alta",
        "status": "Ativo",
        "version": "v1.4",
        "responsible": "Fernanda Pires",
        "items_count": 6,
        "preventive_plan_code": "PP-2026-002",
        "work_order_code": "OS-2026-0149",
        "suggested_periodicity": "Trimestral",
        "technical_notes": "Executar com janela controlada e validacao de sensores apos limpeza.",
        "high_nok_rate": False,
        "recent_execution": True,
        "execution_count": 12,
        "conformity_rate": "94%",
        "anomaly_rate": "8%",
        "last_execution": "11/03/2026 08:30",
        "items": [
            {
                "order": 1,
                "title": "Verificar integridade da vedacao da porta",
                "description": "Inspecionar vedacao frontal e pontos de fuga.",
                "instruction": "Realizar teste visual e de compressao da vedacao antes de iniciar os ensaios.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Vedacao integra e uniforme",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Registrar ponto exato de perda, se houver.",
            },
            {
                "order": 2,
                "title": "Validar leitura do sensor de umidade",
                "description": "Comparar leitura do equipamento com instrumento de referencia.",
                "instruction": "Executar comparativo em regime estabilizado por 10 min.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Desvio maximo de 2%",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Apontar desvio observado e necessidade de recalibracao.",
            },
            {
                "order": 3,
                "title": "Checar limpeza do condensador",
                "description": "Validar ausencia de incrustacao e obstrucao.",
                "instruction": "Inspecionar a superficie e registrar condicao geral.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Superficie limpa",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Descrever ponto de sujidade ou necessidade de limpeza.",
            },
            {
                "order": 4,
                "title": "Verificar alarmes ativos no controlador",
                "description": "Consultar historico de alarmes desde a ultima execucao.",
                "instruction": "Registrar alarmes anormais e frequencia.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Sem alarmes anormais",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Listar codigos e periodo dos alarmes encontrados.",
            },
            {
                "order": 5,
                "title": "Confirmar pontos de aterramento",
                "description": "Inspecionar conexoes eletricas e aterramento funcional.",
                "instruction": "Realizar verificacao visual e reaperto se necessario.",
                "response_type": "OK/NOK/N/A",
                "required": False,
                "expected_value": "Conexoes firmes",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Registrar conexoes frouxas ou sinais de oxidacao.",
            },
            {
                "order": 6,
                "title": "Registrar observacao final de estabilidade",
                "description": "Sintese tecnica da condicao do ativo apos a inspecao.",
                "instruction": "Concluir com resumo do estado e recomendacao.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Resumo registrado",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": False,
                "default_note": "Descrever condicao geral e proximos passos.",
            },
        ],
        "executions": [
            {
                "execution_code": "EX-CHK-001",
                "asset_code": "CAMARA-CLIMATICA-01",
                "work_order_code": "OS-2026-0149",
                "preventive_plan_code": "PP-2026-002",
                "executor": "Fernanda Pires",
                "started_at": "11/03/2026 08:30",
                "completed_at": "11/03/2026 09:28",
                "status": "Concluida",
                "progress": 100,
                "ok_count": 5,
                "nok_count": 1,
                "na_count": 0,
                "result": "Concluida com anomalia",
                "final_notes": "Sensor de umidade apresentou leve desvio e foi recomendado ajuste preventivo.",
                "recommendation": "Programar recalibracao em janela curta.",
                "responses": [
                    {"order": 1, "response": "OK", "note": "Vedacao integra.", "timestamp": "11/03 08:36"},
                    {"order": 2, "response": "NOK", "note": "Desvio de 3,1% na comparacao com padrao.", "timestamp": "11/03 08:42"},
                    {"order": 3, "response": "OK", "note": "Condensador limpo.", "timestamp": "11/03 08:51"},
                    {"order": 4, "response": "OK", "note": "Sem alarmes anormais.", "timestamp": "11/03 08:58"},
                    {"order": 5, "response": "OK", "note": "Conexoes firmes.", "timestamp": "11/03 09:06"},
                    {"order": 6, "response": "OK", "note": "Operacao estavel com recomendacao de recalibracao.", "timestamp": "11/03 09:18"},
                ],
            }
        ],
    },
    {
        "code": "CHK-2026-002",
        "name": "Verificacao Funcional de Esteira",
        "description": "Rotina de avaliacao funcional e eletrica para esteiras de alta demanda.",
        "category": "Fitness",
        "checklist_type": "Inspecao funcional",
        "asset_code": "ESTEIRA-ERG-12",
        "asset_category": "Esteira",
        "client": "Academia Exemplo",
        "site": "Unidade Centro",
        "criticality": "Alta",
        "status": "Ativo",
        "version": "v2.1",
        "responsible": "Ana Lopes",
        "items_count": 5,
        "preventive_plan_code": "PP-2026-003",
        "work_order_code": "OS-2026-0151",
        "suggested_periodicity": "Quinzenal / por uso",
        "technical_notes": "Base para detectar falhas de partida e desgaste de componentes do lote.",
        "high_nok_rate": True,
        "recent_execution": True,
        "execution_count": 9,
        "conformity_rate": "76%",
        "anomaly_rate": "28%",
        "last_execution": "12/03/2026 08:46",
        "items": [
            {
                "order": 1,
                "title": "Verificar tensao de alimentacao",
                "description": "Conferir estabilidade de alimentacao antes da partida.",
                "instruction": "Registrar condicao eletrica e variacao relevante.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "220 V estavel",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Apontar variacao e oscilacao identificada.",
            },
            {
                "order": 2,
                "title": "Inspecionar ruído anormal na partida",
                "description": "Verificar estalos, vibração ou travamento inicial.",
                "instruction": "Realizar partida controlada e registrar anomalias.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Sem ruido anormal",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Descrever ruido, momento e frequencia.",
            },
            {
                "order": 3,
                "title": "Conferir temperatura da placa de potencia",
                "description": "Validar aquecimento anormal no conjunto de acionamento.",
                "instruction": "Executar medicao apos teste funcional.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Temperatura dentro da faixa de operacao",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Registrar temperatura observada.",
            },
            {
                "order": 4,
                "title": "Checar alarmes ativos no console",
                "description": "Confirmar historico e estado atual de alarmes.",
                "instruction": "Anotar codigos exibidos, se houver.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Sem alarmes ativos",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Listar codigos e sintomas associados.",
            },
            {
                "order": 5,
                "title": "Registrar observacao final",
                "description": "Sintese funcional do equipamento.",
                "instruction": "Concluir com parecer rapido e recomendacao.",
                "response_type": "OK/NOK/N/A",
                "required": False,
                "expected_value": "Resumo final registrado",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": False,
                "default_note": "Informar se ha necessidade de corretiva.",
            },
        ],
        "executions": [
            {
                "execution_code": "EX-CHK-002",
                "asset_code": "ESTEIRA-ERG-12",
                "work_order_code": "OS-2026-0151",
                "preventive_plan_code": "PP-2026-003",
                "executor": "Ana Lopes",
                "started_at": "12/03/2026 08:46",
                "completed_at": "12/03/2026 09:21",
                "status": "Concluida",
                "progress": 100,
                "ok_count": 2,
                "nok_count": 3,
                "na_count": 0,
                "result": "Concluida com anomalias criticas",
                "final_notes": "Falha de partida confirmada com placa e capacitor fora da faixa.",
                "recommendation": "Gerar corretiva imediata e revisar lote semelhante.",
                "responses": [
                    {"order": 1, "response": "OK", "note": "Alimentacao estavel.", "timestamp": "12/03 08:48"},
                    {"order": 2, "response": "NOK", "note": "Estalo e desarme na partida.", "timestamp": "12/03 08:55"},
                    {"order": 3, "response": "NOK", "note": "Aquecimento acima do padrao.", "timestamp": "12/03 09:02"},
                    {"order": 4, "response": "NOK", "note": "Console com erro E-14.", "timestamp": "12/03 09:08"},
                    {"order": 5, "response": "OK", "note": "Recomendado reparo imediato.", "timestamp": "12/03 09:16"},
                ],
            },
            {
                "execution_code": "EX-CHK-002-B",
                "asset_code": "ESTEIRA-ERG-12",
                "work_order_code": "OS-2026-0151",
                "preventive_plan_code": "PP-2026-003",
                "executor": "Ana Lopes",
                "started_at": "12/03/2026 10:10",
                "completed_at": "",
                "status": "Em andamento",
                "progress": 60,
                "ok_count": 2,
                "nok_count": 1,
                "na_count": 0,
                "result": "Parcial",
                "final_notes": "",
                "recommendation": "",
                "responses": [
                    {"order": 1, "response": "OK", "note": "Alimentacao validada.", "timestamp": "12/03 10:12"},
                    {"order": 2, "response": "NOK", "note": "Persistencia do desarme.", "timestamp": "12/03 10:18"},
                    {"order": 3, "response": "OK", "note": "Sem nova elevacao apos isolamento.", "timestamp": "12/03 10:25"},
                ],
            },
        ],
    },
    {
        "code": "CHK-2026-003",
        "name": "Rotina de Inspecao de Chiller",
        "description": "Checklist funcional e operacional do chiller com foco em fluxo, alarmes e temperatura.",
        "category": "HVAC",
        "checklist_type": "Inspecao operacional",
        "asset_code": "CHILLER-UNID-A",
        "asset_category": "Chiller",
        "client": "Academia Exemplo",
        "site": "Unidade Centro",
        "criticality": "Critica",
        "status": "Ativo",
        "version": "v1.8",
        "responsible": "Carlos Mota",
        "items_count": 5,
        "preventive_plan_code": "PP-2026-001",
        "work_order_code": "OS-2026-0148",
        "suggested_periodicity": "Mensal",
        "technical_notes": "Usado tanto em preventiva quanto em corretiva com foco em estabilidade termica.",
        "high_nok_rate": False,
        "recent_execution": True,
        "execution_count": 15,
        "conformity_rate": "89%",
        "anomaly_rate": "11%",
        "last_execution": "12/03/2026 09:10",
        "items": [
            {
                "order": 1,
                "title": "Checar temperatura de ida e retorno",
                "description": "Confirmar estabilidade termica do circuito.",
                "instruction": "Registrar valores e comparar com setpoint.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Faixa dentro da operacao nominal",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Anotar divergencia relevante.",
            },
            {
                "order": 2,
                "title": "Validar sensor de fluxo",
                "description": "Verificar leitura, resposta e intermitencia.",
                "instruction": "Comparar com referencia local e historico recente.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Leitura consistente",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Registrar oscilacao, se houver.",
            },
            {
                "order": 3,
                "title": "Inspecionar incrustacao no evaporador",
                "description": "Avaliar condicao de limpeza e restricao parcial.",
                "instruction": "Executar inspeção visual e registrar nivel de sujidade.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Superficie sem restricao anormal",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Descrever area afetada.",
            },
            {
                "order": 4,
                "title": "Checar alarmes do sistema",
                "description": "Consultar alarmes ativos e historico imediato.",
                "instruction": "Registrar codigos e frequencia de alarme.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Sem alarmes anormais",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Listar alarmes relevantes.",
            },
            {
                "order": 5,
                "title": "Conclusao do estado operacional",
                "description": "Resumo tecnico da condicao atual.",
                "instruction": "Concluir com risco, impacto e recomendacao.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Conclusao registrada",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": False,
                "default_note": "Sintetizar necessidade de corretiva ou ajuste de plano.",
            },
        ],
        "executions": [],
    },
    {
        "code": "CHK-2026-004",
        "name": "Checklist Eletrico de Inversor WEG",
        "description": "Checklist de inspeção elétrica e termográfica para painéis com inversor de frequencia.",
        "category": "Automacao",
        "checklist_type": "Inspecao eletrica",
        "asset_code": "INVERSOR-WEG-EST-03",
        "asset_category": "Inversor de frequencia",
        "client": "Smart Control Brasil",
        "site": "Planta Maua",
        "criticality": "Critica",
        "status": "Ativo",
        "version": "v1.2",
        "responsible": "Bruno Salles",
        "items_count": 4,
        "preventive_plan_code": "PP-2026-004",
        "work_order_code": "OS-2026-0150",
        "suggested_periodicity": "Mensal",
        "technical_notes": "Checklist orientado a bornes, ventilacao e hotspots.",
        "high_nok_rate": False,
        "recent_execution": False,
        "execution_count": 6,
        "conformity_rate": "91%",
        "anomaly_rate": "9%",
        "last_execution": "18/02/2026 11:10",
        "items": [
            {
                "order": 1,
                "title": "Conferir aperto de bornes",
                "description": "Validar terminais e reaperto em painel.",
                "instruction": "Inspecionar bornes principais e secundários.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Sem folga detectada",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Registrar borne e nivel de aquecimento.",
            },
            {
                "order": 2,
                "title": "Inspecionar ventilacao do painel",
                "description": "Validar filtros, ventoinhas e limpeza interna.",
                "instruction": "Observar fluxo e obstrucao de passagem de ar.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Ventilacao livre",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Registrar componente comprometido.",
            },
            {
                "order": 3,
                "title": "Executar leitura termografica",
                "description": "Buscar hotspots em bornes e dissipadores.",
                "instruction": "Registrar area e temperatura anormal.",
                "response_type": "OK/NOK/N/A",
                "required": True,
                "expected_value": "Sem hotspots relevantes",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": True,
                "default_note": "Informar ponto de aquecimento.",
            },
            {
                "order": 4,
                "title": "Registrar observacao final",
                "description": "Conclusao tecnica do painel.",
                "instruction": "Consolidar estado geral do conjunto.",
                "response_type": "OK/NOK/N/A",
                "required": False,
                "expected_value": "Resumo final registrado",
                "min_limit": "",
                "max_limit": "",
                "alert_on_nok": False,
                "default_note": "Indicar se precisa abrir corretiva.",
            },
        ],
        "executions": [],
    },
]


def _normalize(value):
    return (value or "").strip().lower()


def _enrich_checklist(item):
    checklist = deepcopy(item)
    checklist["asset"] = get_asset_by_code(item["asset_code"]) or {}
    checklist["preventive_plan"] = get_preventive_plan_by_code(item["preventive_plan_code"]) if item.get("preventive_plan_code") else None
    checklist["work_order"] = get_work_order_by_code(item["work_order_code"]) if item.get("work_order_code") else None
    checklist["linked_assets"] = [checklist["asset"]] if checklist["asset"] else []
    checklist["linked_clients"] = [checklist["client"]]
    checklist["linked_sites"] = [checklist["site"]]
    checklist["application_type"] = _normalize_application_type(checklist.get("application_type") or checklist.get("checklist_type") or "general")
    checklist["application_label"] = _application_label(checklist["application_type"])
    checklist["status_slug"] = "active" if _normalize(checklist.get("status")) == "ativo" else "inactive"
    return checklist


def get_checklist_options(records=None):
    records = records or [_enrich_checklist(item) for item in CHECKLIST_RECORDS]
    return {
        "categories": sorted({item["category"] for item in records}),
        "types": sorted({item["application_type"] for item in records}),
        "assets": sorted({item["asset_code"] for item in records}),
        "clients": sorted({item["client"] for item in records}),
        "sites": sorted({item["site"] for item in records}),
        "statuses": ["active", "inactive"],
        "criticalities": sorted({item["criticality"] for item in records}),
    }


def filter_checklists(filters=None, tenant_context=None):
    filters = filters or {}
    search = _normalize(filters.get("search"))
    results = []
    for item in filter_records_for_scope(CHECKLIST_RECORDS, tenant_context or {}):
        checklist = _enrich_checklist(item)
        haystack = " ".join(
            [
                checklist["code"],
                checklist["name"],
                checklist["category"],
                checklist["description"],
            ]
        ).lower()
        if search and search not in haystack:
            continue
        if filters.get("category") and checklist["category"] != filters["category"]:
            continue
        if filters.get("application_type") and checklist["application_type"] != filters["application_type"]:
            continue
        if filters.get("status") and checklist["status_slug"] != filters["status"]:
            continue
        results.append(checklist)
    return results


def _build_filters(filters=None, records=None):
    filters = filters or {}
    return [
        {"label": "Busca", "name": "search", "type": "search", "value": filters.get("search", ""), "placeholder": "Nome ou descrição"},
        {
            "label": "Status",
            "name": "status",
            "type": "select",
            "value": filters.get("status", ""),
            "options": [
                {"value": "active", "label": "Ativo"},
                {"value": "inactive", "label": "Inativo"},
            ],
        },
        {
            "label": "Aplicação",
            "name": "application_type",
            "type": "select",
            "value": filters.get("application_type", ""),
            "options": [
                {"value": "equipment", "label": "Equipamento"},
                {"value": "equipment_model", "label": "Modelo de equipamento"},
                {"value": "service", "label": "Serviço"},
                {"value": "preventive", "label": "Preventiva"},
                {"value": "general", "label": "Geral"},
            ],
        },
    ]


def get_checklist_listing_context(filters=None, tenant_context=None):
    filters = filters or {}
    records = [_enrich_checklist(item) for item in filter_records_for_scope(CHECKLIST_RECORDS, tenant_context or {})]
    return {
        "page_actions": [
            {"label": "Novo checklist", "route_name": "admin-shell:smart-system-checklist-create", "permission_domain": "checklists", "permission_action": "create"},
        ],
        "checklist_filters": _build_filters(filters, records),
        "checklists": filter_checklists(filters, tenant_context=tenant_context),
    }


def get_checklist_by_code(checklist_code, tenant_context=None):
    target = _normalize(checklist_code)
    for item in CHECKLIST_RECORDS:
        if _normalize(item["code"]) == target and record_matches_scope(item, tenant_context or {}):
            return _enrich_checklist(item)
    return None


def get_checklist_detail_context(checklist_code, tenant_context=None):
    checklist = get_checklist_by_code(checklist_code, tenant_context=tenant_context)
    if checklist is None:
        return None
    checklist["page_actions"] = [
        {"label": "Editar checklist", "route_name": "admin-shell:smart-system-checklist-update", "route_kwargs": {"checklist_code": checklist["code"]}, "permission_domain": "checklists", "permission_action": "update"},
        {"label": "Desativar", "route_name": "admin-shell:smart-system-checklist-deactivate", "route_kwargs": {"checklist_code": checklist["code"]}, "permission_domain": "checklists", "permission_action": "update"},
    ]
    checklist["summary_cards"] = [
        {"label": "Status", "value": checklist["status"], "meta": checklist["version"]},
        {"label": "Itens", "value": str(checklist["items_count"]), "meta": checklist["checklist_type"]},
        {"label": "Execucoes recentes", "value": str(len(checklist["executions"])), "meta": checklist["last_execution"]},
        {"label": "Conformidade", "value": checklist["conformity_rate"], "meta": "media de OK"},
        {"label": "Taxa de NOK", "value": checklist["anomaly_rate"], "meta": "anomalias detectadas"},
        {"label": "Vinculos", "value": "Preventiva + OS" if checklist["preventive_plan_code"] and checklist["work_order_code"] else "Parcial", "meta": checklist["asset_code"]},
        {"label": "Criticidade", "value": checklist["criticality"], "meta": checklist["asset"]["name"]},
        {"label": "Ultima execucao", "value": checklist["last_execution"], "meta": checklist["responsible"]},
    ]
    checklist["general_info"] = [
        {"label": "Descricao", "value": checklist["description"]},
        {"label": "Categoria", "value": checklist["category"]},
        {"label": "Tipo", "value": checklist["checklist_type"]},
        {"label": "Versao", "value": checklist["version"]},
        {"label": "Responsavel", "value": checklist["responsible"]},
        {"label": "Aplicabilidade", "value": f"{checklist['asset_category']} / {checklist['asset']['name']}"},
        {"label": "Periodicidade sugerida", "value": checklist["suggested_periodicity"]},
        {"label": "Observacoes tecnicas", "value": checklist["technical_notes"]},
    ]
    checklist["operational_links"] = [
        {"label": "Ativo", "value": checklist["asset"]["name"], "route_name": "admin-shell:smart-system-asset-detail", "route_kwargs": {"asset_code": checklist["asset_code"]}},
        {"label": "Plano preventivo", "value": checklist["preventive_plan_code"] or "Nao vinculado", "route_name": "admin-shell:smart-system-preventive-detail", "route_kwargs": {"plan_code": checklist["preventive_plan_code"]} if checklist["preventive_plan_code"] else {}},
        {"label": "OS relacionada", "value": checklist["work_order_code"] or "Nao vinculada", "route_name": "admin-shell:smart-system-work-order-detail", "route_kwargs": {"order_code": checklist["work_order_code"]} if checklist["work_order_code"] else {}},
        {"label": "Cliente / site", "value": f"{checklist['client']} • {checklist['site']}"},
    ]
    checklist["execution_history"] = [
        {
            "execution_code": execution["execution_code"],
            "date": execution["completed_at"] or execution["started_at"],
            "asset_code": execution["asset_code"],
            "executor": execution["executor"],
            "result": execution["result"],
            "nok_count": execution["nok_count"],
            "status": execution["status"],
        }
        for execution in checklist["executions"]
    ]
    checklist["alerts"] = []
    if checklist["status"] != "Ativo":
        checklist["alerts"].append(
            {
                "severity": "warning",
                "title": "Checklist fora do ciclo ativo",
                "description": "A rotina nao esta operacionalmente ativa e pode deixar o ativo sem padronizacao recente.",
            }
        )
    if checklist["high_nok_rate"]:
        checklist["alerts"].append(
            {
                "severity": "critical",
                "title": "Indice elevado de NOK",
                "description": "As ultimas execucoes apontaram anomalias recorrentes. Vale revisar plano preventivo e corretiva associada.",
            }
        )
    if not checklist["preventive_plan_code"]:
        checklist["alerts"].append(
            {
                "severity": "warning",
                "title": "Sem vinculo preventivo",
                "description": "O checklist ainda nao esta ligado a um plano preventivo, o que limita programacao recorrente.",
            }
        )
    if checklist["criticality"] in {"Alta", "Critica"} and not checklist["recent_execution"]:
        checklist["alerts"].append(
            {
                "severity": "critical",
                "title": "Ativo critico sem execucao recente",
                "description": "A frequencia de execucao precisa ser revisada para manter cobertura de um ativo sensivel.",
            }
        )
    return checklist


def _application_label(value):
    mapping = {
        "equipment": "Equipamento",
        "equipment_model": "Modelo de equipamento",
        "service": "Serviço",
        "preventive": "Preventiva",
        "general": "Geral",
        "preventiva": "Preventiva",
        "inspecao funcional": "Serviço",
        "inspecao operacional": "Serviço",
        "inspecao eletrica": "Serviço",
    }
    return mapping.get(_normalize(value), "Geral")


def _normalize_application_type(value):
    normalized = _normalize(value)
    mapping = {
        "equipment": "equipment",
        "equipamento": "equipment",
        "equipment_model": "equipment_model",
        "modelo de equipamento": "equipment_model",
        "service": "service",
        "servico": "service",
        "serviço": "service",
        "preventive": "preventive",
        "preventiva": "preventive",
        "general": "general",
        "geral": "general",
        "inspecao funcional": "service",
        "inspeção funcional": "service",
        "inspecao operacional": "service",
        "inspeção operacional": "service",
        "inspecao eletrica": "service",
        "inspeção elétrica": "service",
    }
    return mapping.get(normalized, "general")


def get_execution_context(checklist_code, execution_code=None, tenant_context=None):
    checklist = get_checklist_by_code(checklist_code, tenant_context=tenant_context)
    if checklist is None:
        return None
    if execution_code:
        execution = next((deepcopy(item) for item in checklist["executions"] if item["execution_code"] == execution_code), None)
    else:
        execution = next((deepcopy(item) for item in checklist["executions"] if item["status"] == "Em andamento"), None)
    if execution is None:
        execution = {
            "execution_code": f"EX-{checklist['code']}",
            "asset_code": checklist["asset_code"],
            "work_order_code": checklist["work_order_code"],
            "preventive_plan_code": checklist["preventive_plan_code"],
            "executor": checklist["responsible"],
            "started_at": "12/03/2026 10:10",
            "completed_at": "",
            "status": "Em andamento",
            "progress": 0,
            "ok_count": 0,
            "nok_count": 0,
            "na_count": 0,
            "result": "Parcial",
            "final_notes": "",
            "recommendation": "",
            "responses": [],
        }
    responses_by_order = {item["order"]: item for item in execution["responses"]}
    execution_items = []
    for item in checklist["items"]:
        existing = responses_by_order.get(item["order"], {})
        execution_items.append(
            {
                **deepcopy(item),
                "response": existing.get("response", ""),
                "note": existing.get("note", ""),
                "timestamp": existing.get("timestamp", ""),
            }
        )
    responded = sum(1 for item in execution_items if item["response"])
    execution["total_items"] = len(execution_items)
    execution["responded_count"] = responded
    execution["pending_count"] = execution["total_items"] - responded
    execution["progress"] = int((responded / execution["total_items"]) * 100) if execution["total_items"] else 0
    execution["items"] = execution_items
    execution["asset"] = checklist["asset"]
    execution["work_order"] = checklist["work_order"]
    execution["preventive_plan"] = checklist["preventive_plan"]
    execution["page_actions"] = [
        {"label": "Salvar andamento", "href": "#salvar-andamento", "permission_domain": "checklists", "permission_action": "execute"},
        {"label": "Concluir execucao", "href": "#concluir-execucao", "permission_domain": "checklists", "permission_action": "execute"},
        {"label": "Cancelar execucao", "href": "#cancelar-execucao", "permission_domain": "checklists", "permission_action": "execute"},
    ]
    execution["summary_cards"] = [
        {"label": "Total de itens", "value": str(execution["total_items"]), "meta": "escopo da execucao"},
        {"label": "Respondidos", "value": str(execution["responded_count"]), "meta": "itens com retorno"},
        {"label": "Pendentes", "value": str(execution["pending_count"]), "meta": "faltam concluir"},
        {"label": "OK", "value": str(execution["ok_count"]), "meta": "conformes"},
        {"label": "NOK", "value": str(execution["nok_count"]), "meta": "anomalias encontradas"},
        {"label": "N/A", "value": str(execution["na_count"]), "meta": "nao aplicaveis"},
        {"label": "Progresso", "value": f"{execution['progress']}%", "meta": execution["status"]},
        {"label": "Resultado", "value": execution["result"], "meta": execution["executor"]},
    ]
    execution["alerts"] = []
    if execution["nok_count"]:
        execution["alerts"].append(
            {
                "severity": "critical",
                "title": "Itens NOK encontrados",
                "description": f"{execution['nok_count']} item(ns) com anomalia identificada durante a execucao.",
            }
        )
    if execution["pending_count"]:
        execution["alerts"].append(
            {
                "severity": "warning",
                "title": "Checklist ainda incompleto",
                "description": f"Faltam {execution['pending_count']} item(ns) para concluir a rotina com rastreabilidade total.",
            }
        )
    if checklist["criticality"] in {"Alta", "Critica"} and execution["nok_count"]:
        execution["alerts"].append(
            {
                "severity": "critical",
                "title": "Anomalia em ativo de alta criticidade",
                "description": "Avaliar geracao de corretiva e acao imediata para evitar impacto operacional.",
            }
        )
    return {"checklist": checklist, "execution": execution}
