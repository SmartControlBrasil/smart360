from copy import deepcopy

from .smart_system_assets import get_asset_by_code
from .smart_system_work_orders import get_work_order_by_code
from .tenant_scope import record_matches_scope


PART_RECORDS = [
    {
        "code": "PRT-0001",
        "name": "Sensor PT100",
        "description": "Sensor de temperatura industrial para monitoramento de utilidades e HVAC.",
        "manufacturer": "Novus",
        "model": "PT100 Class A",
        "category": "Instrumentacao",
        "unit": "un",
        "unit_cost": "R$ 184,00",
        "stock_current": 3,
        "stock_min": 4,
        "stock_max": 12,
        "location": "Almoxarifado HVAC A1",
        "status": "Estoque baixo",
        "supplier": "Instrumenta Sul",
        "notes": "Uso recorrente em chillers e camaras climaticas.",
        "asset_codes": ["CHILLER-UNID-A", "CAMARA-CLIMATICA-01"],
        "movements": [
            {"date": "12/03/2026 09:15", "type": "Saida", "quantity": "-1", "reference": "OS-2026-0148", "responsible": "Carlos Mota", "notes": "Reserva para substituicao de sensor de fluxo auxiliar."},
            {"date": "05/03/2026 14:22", "type": "Entrada", "quantity": "+4", "reference": "NF-4402", "responsible": "Compras MRO", "notes": "Reposicao de lote HVAC."},
        ],
        "usage": [
            {"order_code": "OS-2026-0148", "asset_code": "CHILLER-UNID-A", "technician": "Carlos Mota", "quantity": "1 un", "date": "12/03/2026 09:15"},
        ],
    },
    {
        "code": "PRT-0002",
        "name": "Contator 220V",
        "description": "Contator para painéis de acionamento e comandos de motores.",
        "manufacturer": "WEG",
        "model": "CWM18-22",
        "category": "Eletrica",
        "unit": "un",
        "unit_cost": "R$ 132,00",
        "stock_current": 7,
        "stock_min": 3,
        "stock_max": 10,
        "location": "Almoxarifado Eletrico B2",
        "status": "Saudavel",
        "supplier": "WEG Distribuicao",
        "notes": "Padrao para painéis de utilidades e automacao.",
        "asset_codes": ["INVERSOR-WEG-EST-03", "CLP-LINHA-ENV-02"],
        "movements": [
            {"date": "10/03/2026 11:05", "type": "Saida", "quantity": "-1", "reference": "OS-2026-0150", "responsible": "Equipe Automacao", "notes": "Troca preventiva em painel de envase."},
            {"date": "01/03/2026 08:40", "type": "Entrada", "quantity": "+5", "reference": "NF-4388", "responsible": "Compras MRO", "notes": "Reposicao mensal."},
        ],
        "usage": [
            {"order_code": "OS-2026-0150", "asset_code": "INVERSOR-WEG-EST-03", "technician": "Equipe Automacao", "quantity": "1 un", "date": "10/03/2026 11:05"},
        ],
    },
    {
        "code": "PRT-0003",
        "name": "Ventilador Axial",
        "description": "Ventilador axial para renovacao de ar em painéis e unidades HVAC.",
        "manufacturer": "Ebmpapst",
        "model": "AxiCool 120",
        "category": "Ventilacao",
        "unit": "un",
        "unit_cost": "R$ 246,00",
        "stock_current": 1,
        "stock_min": 2,
        "stock_max": 8,
        "location": "Almoxarifado HVAC B1",
        "status": "Critico",
        "supplier": "Cool Parts",
        "notes": "Baixo estoque para ativos de alta criticidade.",
        "asset_codes": ["HVAC-ACADEMIA-02", "CHILLER-UNID-A"],
        "movements": [
            {"date": "11/03/2026 16:10", "type": "Saida", "quantity": "-2", "reference": "Ajuste tecnico", "responsible": "Fernanda Pires", "notes": "Reposicao emergencial de rooftop norte."},
        ],
        "usage": [],
    },
    {
        "code": "PRT-0004",
        "name": "Filtro de Ar",
        "description": "Filtro de ar para HVAC, rooftop e sistemas de ventilacao predial.",
        "manufacturer": "AAF",
        "model": "MERV 8",
        "category": "Consumiveis",
        "unit": "un",
        "unit_cost": "R$ 58,00",
        "stock_current": 22,
        "stock_min": 10,
        "stock_max": 40,
        "location": "Almoxarifado Predial C3",
        "status": "Saudavel",
        "supplier": "Filtro Max",
        "notes": "Alto giro em manutencao preventiva de HVAC.",
        "asset_codes": ["HVAC-ACADEMIA-02"],
        "movements": [
            {"date": "12/03/2026 07:30", "type": "Saida", "quantity": "-4", "reference": "PP-2026-001", "responsible": "Carlos Mota", "notes": "Troca de filtros em preventiva mensal."},
            {"date": "02/03/2026 10:18", "type": "Entrada", "quantity": "+20", "reference": "NF-4371", "responsible": "Compras MRO", "notes": "Reposicao programada."},
        ],
        "usage": [
            {"order_code": "OS-2026-0148", "asset_code": "CHILLER-UNID-A", "technician": "Carlos Mota", "quantity": "2 un", "date": "12/03/2026 07:30"},
        ],
    },
    {
        "code": "PRT-0005",
        "name": "Inversor WEG CFW300",
        "description": "Inversor de frequencia usado em acionamento de motores e esteiras.",
        "manufacturer": "WEG",
        "model": "CFW300",
        "category": "Automacao",
        "unit": "un",
        "unit_cost": "R$ 1.480,00",
        "stock_current": 0,
        "stock_min": 1,
        "stock_max": 4,
        "location": "Reserva estrategica Automacao",
        "status": "Sem estoque",
        "supplier": "WEG Distribuicao",
        "notes": "Item de reposicao critica para inversores e esteiras de linha similar.",
        "asset_codes": ["INVERSOR-WEG-EST-03", "ESTEIRA-ERG-12"],
        "movements": [
            {"date": "08/03/2026 15:42", "type": "Saida", "quantity": "-1", "reference": "OS-2026-0151", "responsible": "Ana Lopes", "notes": "Uso emergencial em teste de bancada; reposicao pendente."},
        ],
        "usage": [
            {"order_code": "OS-2026-0151", "asset_code": "ESTEIRA-ERG-12", "technician": "Ana Lopes", "quantity": "1 un", "date": "08/03/2026 15:42"},
        ],
    },
]


def _normalize(value):
    return (value or "").strip().lower()


def _enrich_part(part):
    item = deepcopy(part)
    item["assets"] = [get_asset_by_code(code) or {"code": code, "name": code} for code in item["asset_codes"]]
    primary_asset = next((asset for asset in item["assets"] if asset and asset.get("client")), None)
    item["client"] = primary_asset.get("client", "-") if primary_asset else "-"
    item["site"] = primary_asset.get("site", "-") if primary_asset else "-"
    item["movements_count"] = len(item["movements"])
    item["usage_count"] = len(item["usage"])
    item["average_consumption"] = f"{max(item['usage_count'], 1)} un / mes"
    item["is_critical_stock"] = item["stock_current"] == 0 or item["stock_current"] < item["stock_min"]
    item["is_low_stock"] = item["stock_current"] <= item["stock_min"]
    return item


def get_part_options():
    return {
        "categories": sorted({item["category"] for item in PART_RECORDS}),
        "manufacturers": sorted({item["manufacturer"] for item in PART_RECORDS}),
        "suppliers": sorted({item["supplier"] for item in PART_RECORDS}),
        "locations": sorted({item["location"] for item in PART_RECORDS}),
        "statuses": sorted({item["status"] for item in PART_RECORDS}),
        "assets": sorted({code for item in PART_RECORDS for code in item["asset_codes"]}),
    }


def filter_parts(filters=None, tenant_context=None):
    filters = filters or {}
    search = _normalize(filters.get("search"))
    results = []
    for part in [_enrich_part(item) for item in PART_RECORDS]:
        if tenant_context and not any(record_matches_scope(asset, tenant_context) for asset in part["assets"] if asset.get("client")):
            continue
        haystack = " ".join(
            [
                part["code"],
                part["name"],
                part["category"],
                part["manufacturer"],
                part["supplier"],
                " ".join(part["asset_codes"]),
            ]
        ).lower()
        if search and search not in haystack:
            continue
        if filters.get("category") and part["category"] != filters["category"]:
            continue
        if filters.get("manufacturer") and part["manufacturer"] != filters["manufacturer"]:
            continue
        if filters.get("supplier") and part["supplier"] != filters["supplier"]:
            continue
        if filters.get("location") and part["location"] != filters["location"]:
            continue
        if filters.get("status") and part["status"] != filters["status"]:
            continue
        if filters.get("low_stock") == "yes" and not part["is_low_stock"]:
            continue
        if filters.get("asset") and filters["asset"] not in part["asset_codes"]:
            continue
        results.append(part)
    return results


def _build_filters(filters=None):
    filters = filters or {}
    options = get_part_options()
    return [
        {"label": "Buscar peca", "name": "search", "type": "search", "value": filters.get("search", ""), "placeholder": "Codigo, nome ou fabricante"},
        {"label": "Categoria", "name": "category", "type": "select", "value": filters.get("category", ""), "options": options["categories"]},
        {"label": "Fabricante", "name": "manufacturer", "type": "select", "value": filters.get("manufacturer", ""), "options": options["manufacturers"]},
        {"label": "Fornecedor", "name": "supplier", "type": "select", "value": filters.get("supplier", ""), "options": options["suppliers"]},
        {"label": "Localizacao", "name": "location", "type": "select", "value": filters.get("location", ""), "options": options["locations"]},
        {"label": "Status", "name": "status", "type": "select", "value": filters.get("status", ""), "options": options["statuses"]},
        {"label": "Ativo associado", "name": "asset", "type": "select", "value": filters.get("asset", ""), "options": options["assets"]},
        {"label": "Estoque baixo", "name": "low_stock", "type": "toggle", "value": filters.get("low_stock", ""), "toggle_label": "Somente baixo/critico"},
    ]


def get_part_listing_context(filters=None, tenant_context=None):
    filters = filters or {}
    records = filter_parts({}, tenant_context=tenant_context)
    return {
        "page_actions": [
            {"label": "Nova peca", "route_name": "admin-shell:smart-system-part-create", "permission_domain": "inventory", "permission_action": "create"},
            {"label": "Registrar entrada", "route_name": "admin-shell:smart-system-stock-movements", "permission_domain": "inventory", "permission_action": "adjust_stock"},
            {"label": "Registrar saida", "route_name": "admin-shell:smart-system-stock-movements", "permission_domain": "inventory", "permission_action": "consume"},
            {"label": "Ajustar estoque", "route_name": "admin-shell:smart-system-stock-movements", "permission_domain": "inventory", "permission_action": "adjust_stock"},
            {"label": "Abrir dashboard", "route_name": "admin-shell:module-page", "route_kwargs": {"module_slug": "smart-system"}, "permission_domain": "dashboard", "permission_action": "view"},
        ],
        "part_filters": _build_filters(filters),
        "part_kpis": [
            {"label": "Total de itens", "value": str(len(records)), "context": "catalogo MRO ativo", "trend": "cobertura basica de HVAC, eletrica e automacao", "tone": "indigo"},
            {"label": "Estoque critico", "value": str(sum(1 for item in records if item["stock_current"] == 0)), "context": "sem disponibilidade imediata", "trend": "reposicao urgente em itens de automacao", "tone": "red"},
            {"label": "Estoque baixo", "value": str(sum(1 for item in records if item["is_low_stock"] and item["stock_current"] > 0)), "context": "abaixo do minimo", "trend": "monitorar sensores e ventilacao", "tone": "amber"},
            {"label": "Sem movimentacao", "value": "1", "context": "baixo giro recente", "trend": "avaliar obsolescencia ou ajuste de maximo", "tone": "sky"},
            {"label": "Mais utilizadas", "value": "Filtro / Sensor", "context": "top consumo no periodo", "trend": "uso puxado por HVAC e utilidades", "tone": "emerald"},
            {"label": "Consumo no periodo", "value": "10 un", "context": "ultimos 30 dias", "trend": "2 OS consumiram itens criticos", "tone": "violet"},
        ],
        "parts": filter_parts(filters, tenant_context=tenant_context),
    }


def get_part_by_code(part_code, tenant_context=None):
    target = _normalize(part_code)
    for part in PART_RECORDS:
        if _normalize(part["code"]) == target:
            enriched = _enrich_part(part)
            if tenant_context and not any(record_matches_scope(asset, tenant_context) for asset in enriched["assets"] if asset.get("client")):
                return None
            return enriched
    return None


def get_part_detail_context(part_code, tenant_context=None):
    part = get_part_by_code(part_code, tenant_context=tenant_context)
    if part is None:
        return None
    part["page_actions"] = [
        {"label": "Registrar entrada", "route_name": "admin-shell:smart-system-stock-movements", "permission_domain": "inventory", "permission_action": "adjust_stock"},
        {"label": "Registrar saida", "route_name": "admin-shell:smart-system-stock-movements", "permission_domain": "inventory", "permission_action": "consume"},
        {"label": "Ajustar estoque", "route_name": "admin-shell:smart-system-stock-movements", "permission_domain": "inventory", "permission_action": "adjust_stock"},
        {"label": "Abrir historico", "href": "#historico-estoque", "permission_domain": "inventory", "permission_action": "view"},
    ]
    part["summary_cards"] = [
        {"label": "Estoque atual", "value": str(part["stock_current"]), "meta": part["unit"]},
        {"label": "Estoque minimo", "value": str(part["stock_min"]), "meta": "gatilho de reposicao"},
        {"label": "Estoque maximo", "value": str(part["stock_max"]), "meta": "capacidade planejada"},
        {"label": "Consumo medio", "value": part["average_consumption"], "meta": "janela recente"},
        {"label": "Status", "value": part["status"], "meta": part["location"]},
    ]
    part["general_info"] = [
        {"label": "Descricao", "value": part["description"]},
        {"label": "Categoria", "value": part["category"]},
        {"label": "Fabricante", "value": part["manufacturer"]},
        {"label": "Modelo", "value": part["model"]},
        {"label": "Unidade", "value": part["unit"]},
        {"label": "Custo unitario", "value": part["unit_cost"]},
        {"label": "Fornecedor principal", "value": part["supplier"]},
        {"label": "Observacoes", "value": part["notes"]},
    ]
    part["alerts"] = []
    if part["stock_current"] == 0:
        part["alerts"].append({"severity": "critical", "title": "Sem estoque", "description": "A peca esta indisponivel e pode bloquear execucoes corretivas."})
    elif part["stock_current"] < part["stock_min"]:
        part["alerts"].append({"severity": "warning", "title": "Abaixo do estoque minimo", "description": "Recomendado acionar reposicao antes do proximo consumo."})
    if len(part["usage"]) >= 1:
        part["alerts"].append({"severity": "info", "title": "Consumo ativo em OS", "description": "O item ja foi aplicado em ordens recentes e deve ser monitorado."})
    return part


def get_stock_movement_context(tenant_context=None):
    records = []
    for part in PART_RECORDS:
        enriched = _enrich_part(part)
        if tenant_context and not any(record_matches_scope(asset, tenant_context) for asset in enriched["assets"] if asset.get("client")):
            continue
        for movement in part["movements"]:
            records.append(
                {
                    "part_code": part["code"],
                    "part_name": part["name"],
                    "category": part["category"],
                    **movement,
                }
            )
    records.sort(key=lambda item: item["date"], reverse=True)
    return {
        "page_actions": [
            {"label": "Entrada de estoque", "href": "#entrada-estoque", "permission_domain": "inventory", "permission_action": "adjust_stock"},
            {"label": "Saida de estoque", "href": "#saida-estoque", "permission_domain": "inventory", "permission_action": "consume"},
            {"label": "Ajuste manual", "href": "#ajuste-manual", "permission_domain": "inventory", "permission_action": "adjust_stock"},
            {"label": "Voltar para pecas", "route_name": "admin-shell:smart-system-parts", "permission_domain": "inventory", "permission_action": "view"},
        ],
        "movement_kpis": [
            {"label": "Movimentacoes", "value": str(len(records)), "context": "historico recente", "trend": "entradas, saidas e ajustes", "tone": "sky"},
            {"label": "Saidas para OS", "value": str(sum(1 for item in records if item["type"] == "Saida")), "context": "consumo tecnico", "trend": "ligacao direta com manutencao", "tone": "orange"},
            {"label": "Entradas", "value": str(sum(1 for item in records if item["type"] == "Entrada")), "context": "reposicoes recebidas", "trend": "suporte ao estoque minimo", "tone": "emerald"},
            {"label": "Ajustes", "value": str(sum(1 for item in records if item["type"] == "Ajuste")), "context": "correcao de inventario", "trend": "sem ajustes relevantes", "tone": "violet"},
        ],
        "movements": records,
        "movement_forms": [
            {"title": "Entrada de estoque", "fields": ["Peca", "Quantidade", "Fornecedor / NF", "Responsavel"]},
            {"title": "Saida de estoque", "fields": ["Peca", "Quantidade", "OS / referencia", "Responsavel"]},
            {"title": "Ajuste manual", "fields": ["Peca", "Novo saldo", "Motivo", "Responsavel"]},
        ],
    }
