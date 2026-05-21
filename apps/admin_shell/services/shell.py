from copy import deepcopy

from apps.access_control_center.services.smart_system_access import filter_permissioned_items
from .tenant_scope import record_matches_scope


MODULE_PAGES = {
    "smart-system": {
        "title": "Smart System",
        "section": "Operacoes",
        "description": "Gestao operacional de manutencao, ativos, ordens de servico e confiabilidade.",
        "status": "CMMS operacional com agenda tecnica, roteirizacao, relatorios e execucao de campo.",
        "accent": "indigo",
    },
    "marketplace-technicians": {
        "title": "Marketplace Technicians",
        "section": "Marketplaces",
        "description": "Rede operacional de tecnicos, atribuicoes, matching e execucao de campo.",
        "status": "Painel pronto para fila de chamados e cobertura regional.",
        "accent": "emerald",
    },
    "marketplace-analytical": {
        "title": "Marketplace Analytical",
        "section": "Marketplaces",
        "description": "Operacao analitica B2B para laboratorios, laudos e servicos especializados.",
        "status": "Base pronta para requests, providers e relatorios tecnicos.",
        "accent": "cyan",
    },
    "caneca-de-garagem": {
        "title": "Caneca de Garagem",
        "section": "Marketplaces",
        "description": "Marketplace-first para personalizacao, producao e acompanhamento logistico.",
        "status": "Area preparada para pedidos, arte e fila de fabrica.",
        "accent": "amber",
    },
    "smart-site-factory": {
        "title": "Smart Site Factory",
        "section": "Growth & Sites",
        "description": "Linha de montagem digital para sites nichados, intake e producao.",
        "status": "Pronto para dashboards de pedidos, recomendacao e entrega.",
        "accent": "violet",
    },
    "growth-engine": {
        "title": "Growth Engine",
        "section": "Growth & Sites",
        "description": "Motor comercial e de aquisicao com leads, campanhas e pipeline.",
        "status": "Painel preparado para score, canais e produtividade comercial.",
        "accent": "rose",
    },
    "billing": {
        "title": "Billing",
        "section": "Governanca",
        "description": "Planos, assinaturas, faturas, creditos e trilha financeira do ecossistema.",
        "status": "Billing operacional com planos, contratos, assinaturas e faturamento SaaS.",
        "accent": "orange",
    },
    "analytics-platform": {
        "title": "Analytics Platform",
        "section": "Intelligence",
        "description": "Camada analitica transversal com metricas, dashboards e snapshots.",
        "status": "Estrutura pronta para cards executivos e leitura gerencial.",
        "accent": "sky",
    },
    "ai-agents-center": {
        "title": "AI Agents Center",
        "section": "Intelligence",
        "description": "Registry, recomendacoes, propostas de acao e governanca de agentes autonomos.",
        "status": "Camada pronta para autonomia progressiva com human-in-the-loop.",
        "accent": "violet",
    },
    "knowledge-engine": {
        "title": "Knowledge Engine",
        "section": "Intelligence",
        "description": "Base de conhecimento tecnica para troubleshooting, docs e taxonomia.",
        "status": "Painel pronto para navegar artigos, falhas, causas e acoes.",
        "accent": "teal",
    },
    "observability-center": {
        "title": "Observability Center",
        "section": "Infraestrutura",
        "description": "Logs estruturados, incidentes, metricas tecnicas e healthchecks.",
        "status": "Observabilidade ativa com health, traces, auditoria e jobs recentes.",
        "accent": "red",
    },
    "core-platform": {
        "title": "Core Platform",
        "section": "Administracao",
        "description": "Nucleo do ecossistema com usuarios, empresas, memberships e contratos internos.",
        "status": "Base pronta para governanca do core e navegacao transversal.",
        "accent": "slate",
    },
    "configuration-center": {
        "title": "Configuration Center",
        "section": "Governanca",
        "description": "Feature flags, system settings, profiles e runtime toggles.",
        "status": "Pronto para rollout controlado e governanca configuravel.",
        "accent": "fuchsia",
    },
}


def get_navigation(current_url_name="", current_module_slug="", permission_map=None):
    sections = [
        {
            "label": "Dashboard",
            "items": [
                {"label": "Executivo", "icon": "grid", "url_name": "admin-shell:dashboard", "children": []},
            ],
        },
        {
            "label": "Operacoes",
            "items": [
                {
                    "label": "Smart System",
                    "icon": "activity",
                    "children": [
                        {
                            "label": "Dashboard",
                            "icon": "grid",
                            "url_name": "admin-shell:module-page",
                            "slug": "smart-system",
                            "match_names": ["admin-shell:module-page"],
                            "permission_domain": "dashboard",
                            "permission_action": "view",
                        },
                        {"label": "Operacao", "icon": "activity", "url_name": "admin-shell:smart-system-operations", "match_names": ["admin-shell:smart-system-operations"], "permission_domain": "dashboard", "permission_action": "view"},
                        {"label": "Engenharia & TPM", "icon": "pulse", "url_name": "admin-shell:smart-system-reliability", "match_names": ["admin-shell:smart-system-reliability"], "permission_domain": "dashboard", "permission_action": "view"},
                    ],
                },
                {
                    "label": "Cadastros",
                    "icon": "settings",
                    "children": [
                        {
                            "label": "Clientes / Sites",
                            "icon": "building",
                            "url_name": "admin-shell:smart-system-customers",
                            "match_names": [
                                "admin-shell:smart-system-customers",
                                "admin-shell:smart-system-customer-create",
                                "admin-shell:smart-system-customer-detail",
                                "admin-shell:smart-system-customer-update",
                                "admin-shell:smart-system-site-create",
                            ],
                            "permission_domain": "assets",
                            "permission_action": "view",
                        },
                        {
                            "label": "Ativos",
                            "icon": "building",
                            "url_name": "admin-shell:smart-system-assets",
                            "match_names": ["admin-shell:smart-system-assets", "admin-shell:smart-system-asset-detail"],
                            "permission_domain": "assets",
                            "permission_action": "view",
                        },
                        {
                            "label": "Modelos de equipamento",
                            "icon": "grid",
                            "url_name": "admin-shell:smart-system-equipment-models",
                            "match_names": [
                                "admin-shell:smart-system-equipment-models",
                                "admin-shell:smart-system-equipment-model-create",
                                "admin-shell:smart-system-equipment-model-detail",
                                "admin-shell:smart-system-equipment-model-update",
                            ],
                            "permission_domain": "assets",
                            "permission_action": "view",
                        },
                        {
                            "label": "Inventario do cliente",
                            "icon": "list",
                            "url_name": "admin-shell:smart-system-customer-equipments",
                            "match_names": [
                                "admin-shell:smart-system-customer-equipments",
                                "admin-shell:smart-system-customer-equipment-create",
                                "admin-shell:smart-system-customer-equipment-detail",
                                "admin-shell:smart-system-customer-equipment-update",
                            ],
                            "permission_domain": "assets",
                            "permission_action": "view",
                        },
                        {
                            "label": "Pecas",
                            "icon": "box",
                            "url_name": "admin-shell:smart-system-parts",
                            "match_names": [
                                "admin-shell:smart-system-parts",
                                "admin-shell:smart-system-part-detail",
                                "admin-shell:smart-system-stock-movements",
                            ],
                            "permission_domain": "inventory",
                            "permission_action": "view",
                        },
                    ],
                },
                {
                    "label": "Manutencao",
                    "icon": "briefcase",
                    "children": [
                        {
                            "label": "Ordens de Servico",
                            "icon": "briefcase",
                            "url_name": "admin-shell:smart-system-work-orders",
                            "match_names": [
                                "admin-shell:smart-system-work-orders",
                                "admin-shell:smart-system-work-order-create",
                                "admin-shell:smart-system-work-order-create-preventive",
                                "admin-shell:smart-system-work-order-detail",
                                "admin-shell:smart-system-work-order-execution",
                                "admin-shell:smart-system-work-order-start-execution",
                                "admin-shell:smart-system-work-order-save-progress",
                                "admin-shell:smart-system-work-order-complete-execution",
                                "admin-shell:smart-system-work-order-transition",
                                "admin-shell:smart-system-work-order-worklog",
                                "admin-shell:smart-system-work-order-checklist-save",
                                "admin-shell:smart-system-work-order-technician-signature",
                                "admin-shell:smart-system-work-order-client-signature",
                            ],
                            "permission_domain": "work_orders",
                            "permission_action": "view",
                        },
                        {
                            "label": "Preventivas",
                            "icon": "calendar",
                            "url_name": "admin-shell:smart-system-preventives",
                            "match_names": [
                                "admin-shell:smart-system-preventives",
                                "admin-shell:smart-system-preventives-schedule",
                                "admin-shell:smart-system-preventives-calendar",
                                "admin-shell:smart-system-preventive-detail",
                            ],
                            "permission_domain": "preventive_plans",
                            "permission_action": "view",
                        },
                        {
                            "label": "Checklists",
                            "icon": "check",
                            "url_name": "admin-shell:smart-system-checklists",
                            "match_names": [
                                "admin-shell:smart-system-checklists",
                                "admin-shell:smart-system-checklist-detail",
                                "admin-shell:smart-system-checklist-execution",
                                "admin-shell:smart-system-checklist-execution-detail",
                            ],
                            "permission_domain": "checklists",
                            "permission_action": "view",
                        },
                        {
                            "label": "Falhas",
                            "icon": "pulse",
                            "url_name": "admin-shell:smart-system-failures",
                            "match_names": [
                                "admin-shell:smart-system-failures",
                                "admin-shell:smart-system-failure-detail",
                            ],
                            "permission_domain": "failures",
                            "permission_action": "view",
                        },
                        {
                            "label": "Agenda & Rotas",
                            "icon": "calendar",
                            "url_name": "admin-shell:smart-system-scheduling",
                            "match_names": [
                                "admin-shell:smart-system-scheduling",
                                "admin-shell:smart-system-scheduling-calendar",
                                "admin-shell:smart-system-technician-agenda",
                                "admin-shell:smart-system-unassigned-visits",
                            ],
                            "permission_domain": "scheduling",
                            "permission_action": "view",
                        },
                    ],
                },
                {
                    "label": "Gestao",
                    "icon": "report",
                    "children": [
                        {
                            "label": "Contratos",
                            "icon": "briefcase",
                            "url_name": "admin-shell:smart-system-contracts",
                            "match_names": [
                                "admin-shell:smart-system-contracts",
                                "admin-shell:smart-system-contract-detail",
                            ],
                            "permission_domain": "maintenance_contracts",
                            "permission_action": "view",
                        },
                        {
                            "label": "Orcamentos",
                            "icon": "wallet",
                            "url_name": "admin-shell:smart-system-quotes",
                            "match_names": [
                                "admin-shell:smart-system-quotes",
                                "admin-shell:smart-system-quote-detail",
                            ],
                            "permission_domain": "quotes",
                            "permission_action": "view",
                        },
                        {
                            "label": "Relatorios",
                            "icon": "report",
                            "url_name": "admin-shell:smart-system-reports",
                            "match_names": [
                                "admin-shell:smart-system-reports",
                                "admin-shell:smart-system-report-preview",
                                "admin-shell:smart-system-report-download",
                            ],
                            "permission_domain": "reports",
                            "permission_action": "view",
                        },
                    ],
                },
                {"label": "Scheduling Center", "icon": "calendar", "url_name": "admin-shell:module-page", "slug": "configuration-center"},
                {"label": "CRM Center", "icon": "briefcase", "children": [{"label": "Dashboard", "icon": "grid", "url_name": "admin-shell:module-page", "slug": "growth-engine", "match_names": ["admin-shell:module-page"]}, {"label": "Leads da Lívia", "icon": "spark", "url_name": "admin-shell:growth-livia-leads", "match_names": ["admin-shell:growth-livia-leads", "admin-shell:growth-lead-detail"]}]},
            ],
        },
        {
            "label": "Marketplaces",
            "items": [
                {
                    "label": "Marketplace Technicians",
                    "icon": "users",
                    "children": [
                        {
                            "label": "Dashboard",
                            "icon": "grid",
                            "url_name": "admin-shell:marketplace-technicians-dashboard",
                            "match_names": ["admin-shell:marketplace-technicians-dashboard"],
                            "permission_domain": "marketplace_dashboard",
                            "permission_action": "view",
                        },
                        {
                            "label": "Service Requests",
                            "icon": "briefcase",
                            "url_name": "admin-shell:marketplace-technicians-requests",
                            "match_names": ["admin-shell:marketplace-technicians-requests"],
                            "permission_domain": "marketplace_requests",
                            "permission_action": "view",
                        },
                        {
                            "label": "Offers",
                            "icon": "wallet",
                            "url_name": "admin-shell:marketplace-technicians-offers",
                            "match_names": ["admin-shell:marketplace-technicians-offers"],
                            "permission_domain": "marketplace_offers",
                            "permission_action": "view",
                        },
                        {
                            "label": "Matching",
                            "icon": "activity",
                            "url_name": "admin-shell:marketplace-technicians-matching",
                            "match_names": ["admin-shell:marketplace-technicians-matching"],
                            "permission_domain": "marketplace_matching",
                            "permission_action": "view",
                        },
                        {
                            "label": "Technicians",
                            "icon": "users",
                            "url_name": "admin-shell:marketplace-technicians-technicians",
                            "match_names": [
                                "admin-shell:marketplace-technicians-technicians",
                                "admin-shell:marketplace-technicians-technician-detail",
                            ],
                            "permission_domain": "marketplace_technicians",
                            "permission_action": "view",
                        },
                        {
                            "label": "Assignments",
                            "icon": "activity",
                            "url_name": "admin-shell:marketplace-technicians-assignments",
                            "match_names": ["admin-shell:marketplace-technicians-assignments"],
                            "permission_domain": "marketplace_assignments",
                            "permission_action": "view",
                        },
                        {
                            "label": "Reviews",
                            "icon": "check",
                            "url_name": "admin-shell:marketplace-technicians-reviews",
                            "match_names": ["admin-shell:marketplace-technicians-reviews"],
                            "permission_domain": "marketplace_reviews",
                            "permission_action": "view",
                        },
                    ],
                },
                {"label": "Marketplace Analytical", "icon": "flask", "url_name": "admin-shell:module-page", "slug": "marketplace-analytical"},
                {"label": "Caneca de Garagem", "icon": "bag", "url_name": "admin-shell:module-page", "slug": "caneca-de-garagem"},
            ],
        },
        {
            "label": "Growth & Sites",
            "items": [
                {
                    "label": "Smart Site Factory",
                    "icon": "layout",
                    "children": [
                        {
                            "label": "Dashboard",
                            "icon": "grid",
                            "url_name": "admin-shell:site-factory-dashboard",
                            "match_names": [
                                "admin-shell:site-factory-dashboard",
                            ],
                        },
                        {
                            "label": "Projetos",
                            "icon": "briefcase",
                            "url_name": "admin-shell:site-factory-orders",
                            "match_names": [
                                "admin-shell:site-factory-orders",
                                "admin-shell:site-factory-order-detail",
                                "admin-shell:site-factory-order-commercial",
                                "admin-shell:site-factory-order-proposal",
                                "admin-shell:site-factory-order-proposal-approve",
                                "admin-shell:site-factory-order-proposal-reject",
                                "admin-shell:site-factory-order-proposal-send-email",
                                "admin-shell:site-factory-order-intake",
                                "admin-shell:site-factory-order-tasks",
                                "admin-shell:site-factory-task-status",
                            ],
                        },
                        {
                            "label": "Novo Projeto",
                            "icon": "check",
                            "url_name": "admin-shell:site-factory-order-new",
                            "match_names": ["admin-shell:site-factory-order-new"],
                        },
                    ],
                },
                {"label": "Growth Engine", "icon": "trend", "children": [{"label": "Dashboard", "icon": "grid", "url_name": "admin-shell:module-page", "slug": "growth-engine", "match_names": ["admin-shell:module-page"]}, {"label": "Leads da Lívia", "icon": "spark", "url_name": "admin-shell:growth-livia-leads", "match_names": ["admin-shell:growth-livia-leads", "admin-shell:growth-lead-detail"]}]},
            ],
        },
        {
            "label": "Intelligence",
            "items": [
                {
                    "label": "Analytics Platform",
                    "icon": "chart",
                    "url_name": "admin-shell:analytics-executive-dashboard",
                    "match_names": ["admin-shell:analytics-executive-dashboard"],
                    "permission_domain": "analytics_admin",
                    "permission_action": "view",
                },
                {
                    "label": "AI Agents Center",
                    "icon": "spark",
                    "url_name": "admin-shell:ai-agents-dashboard",
                    "match_names": [
                        "admin-shell:ai-agents-dashboard",
                        "admin-shell:ai-agents-recommendations",
                        "admin-shell:ai-agents-runs",
                        "admin-shell:ai-agents-proposals",
                    ],
                    "permission_domain": "ai_agents_admin",
                    "permission_action": "view",
                },
                {
                    "label": "Lívia Assistente",
                    "icon": "spark",
                    "url_name": "admin-shell:livia-dashboard",
                    "match_names": [
                        "admin-shell:livia-dashboard",
                        "admin-shell:livia-conversations",
                        "admin-shell:livia-conversation-detail",
                        "admin-shell:livia-leads",
                        "admin-shell:livia-handoffs",
                    ],
                    "permission_domain": "ai_agents_admin",
                    "permission_action": "view",
                },
                {"label": "Knowledge Engine", "icon": "book", "url_name": "admin-shell:module-page", "slug": "knowledge-engine"},
                {"label": "AI Automation Center", "icon": "spark", "url_name": "admin-shell:module-page", "slug": "analytics-platform"},
                {"label": "Reporting Center", "icon": "report", "url_name": "admin-shell:module-page", "slug": "analytics-platform"},
            ],
        },
        {
            "label": "Infraestrutura",
            "items": [
                {"label": "Notification Center", "icon": "bell", "url_name": "admin-shell:module-page", "slug": "core-platform"},
                {"label": "Files Center", "icon": "folder", "url_name": "admin-shell:module-page", "slug": "core-platform"},
                {"label": "Integration Bus", "icon": "link", "url_name": "admin-shell:module-page", "slug": "core-platform"},
                {
                    "label": "Observability Center",
                    "icon": "pulse",
                    "url_name": "admin-shell:observability-dashboard",
                    "permission_domain": "observability_admin",
                    "permission_action": "view",
                    "match_names": ["admin-shell:observability-dashboard"],
                },
            ],
        },
        {
            "label": "Platform Admin",
            "items": [
                {
                    "label": "Billing",
                    "icon": "wallet",
                    "children": [
                        {
                            "label": "Dashboard",
                            "icon": "grid",
                            "url_name": "admin-shell:billing-dashboard",
                            "match_names": ["admin-shell:billing-dashboard"],
                            "permission_domain": "billing_admin",
                            "permission_action": "view",
                        },
                        {
                            "label": "Planos",
                            "icon": "chart",
                            "url_name": "admin-shell:billing-plans",
                            "match_names": ["admin-shell:billing-plans"],
                            "permission_domain": "billing_admin",
                            "permission_action": "view",
                        },
                        {
                            "label": "Contratos",
                            "icon": "briefcase",
                            "url_name": "admin-shell:billing-contracts",
                            "match_names": [
                                "admin-shell:billing-contracts",
                                "admin-shell:billing-contract-detail",
                                "admin-shell:billing-contract-suspend",
                                "admin-shell:billing-contract-cancel",
                            ],
                            "permission_domain": "billing_admin",
                            "permission_action": "view",
                        },
                        {
                            "label": "Faturas",
                            "icon": "report",
                            "url_name": "admin-shell:billing-invoices",
                            "match_names": [
                                "admin-shell:billing-invoices",
                                "admin-shell:billing-invoice-mark-paid",
                                "admin-shell:billing-invoice-cancel",
                            ],
                            "permission_domain": "billing_admin",
                            "permission_action": "view",
                        },
                    ],
                },
            ],
        },
        {
            "label": "Governanca",
            "items": [
                {
                    "label": "Access Control Center",
                    "icon": "shield",
                    "url_name": "admin-shell:module-page",
                    "slug": "core-platform",
                    "permission_domain": "users",
                    "permission_action": "manage",
                },
                {
                    "label": "Configuration Center",
                    "icon": "settings",
                    "url_name": "admin-shell:module-page",
                    "slug": "configuration-center",
                    "permission_domain": "smart_system_settings",
                    "permission_action": "manage",
                },
                {"label": "Trust & Safety", "icon": "check", "url_name": "admin-shell:module-page", "slug": "observability-center"},
            ],
        },
        {
            "label": "Administracao",
            "items": [
                {
                    "label": "Core Platform",
                    "icon": "core",
                    "url_name": "admin-shell:module-page",
                    "slug": "core-platform",
                    "permission_domain": "users",
                    "permission_action": "view",
                },
                {
                    "label": "Usuarios",
                    "icon": "user",
                    "url_name": "admin-shell:module-page",
                    "slug": "core-platform",
                    "permission_domain": "users",
                    "permission_action": "manage",
                },
                {
                    "label": "Empresas",
                    "icon": "building",
                    "url_name": "admin-shell:module-page",
                    "slug": "core-platform",
                    "permission_domain": "users",
                    "permission_action": "view",
                },
                {"label": "Perfil", "icon": "avatar", "url_name": "admin-shell:module-page", "slug": "core-platform"},
            ],
        },
    ]
    enriched = deepcopy(sections)
    if permission_map is not None:
        enriched = filter_permissioned_items(enriched, permission_map)
    for section in enriched:
        section_active = False
        for item in section["items"]:
            child_active = False
            for child in item.get("children", []):
                match_names = child.get("match_names", [child.get("url_name")])
                child["active"] = current_url_name in match_names and (
                    not child.get("slug") or child.get("slug") == current_module_slug
                )
                if child["active"]:
                    child_active = True
            item["active"] = current_url_name == item.get("url_name") and not item.get("slug")
            item["expanded"] = child_active
            if item.get("slug") and current_url_name == item.get("url_name") and item["slug"] == current_module_slug:
                item["active"] = True
            if child_active:
                item["active"] = True
            if item["active"]:
                section_active = True
        section["active"] = section_active
    return enriched


def _apply_tenant_context_to_dashboard(payload, tenant_context=None):
    tenant_context = tenant_context or {}
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    scope_label = site.name if site else company.name if company else "Todas as operacoes autorizadas"

    if company or site:
        payload["summary_cards"][1]["value"] = "1" if company and not site else payload["summary_cards"][1]["value"]
        payload["summary_cards"][1]["delta"] = scope_label
        payload["operational_stream"][0]["description"] = f"Contexto ativo: {scope_label}."
        payload["operational_stream"][1]["description"] = f"Leitura limitada ao escopo autorizado de {scope_label}."

    return payload


def get_dashboard_context(tenant_context=None):
    payload = {
        "summary_cards": [
            {"label": "Modulos ativos", "value": "23", "delta": "+3 nesta sprint", "tone": "indigo"},
            {"label": "Empresas e clientes", "value": "148", "delta": "+12 onboarding", "tone": "emerald"},
            {"label": "Jobs e processos", "value": "964", "delta": "87 em execucao", "tone": "amber"},
            {"label": "Alertas ativos", "value": "17", "delta": "4 criticos", "tone": "red"},
        ],
        "platform_health": [
            {"label": "API e shell", "status": "Saudavel", "value": 99, "tone": "emerald"},
            {"label": "Workers e filas", "status": "Atencao", "value": 72, "tone": "amber"},
            {"label": "Billing e jobs", "status": "Saudavel", "value": 91, "tone": "indigo"},
            {"label": "Observability", "status": "Critico controlado", "value": 43, "tone": "red"},
        ],
        "recent_activity": [
            {"title": "Smart System sincronizou 12 ordens de servico", "meta": "ha 6 min • integration_bus"},
            {"title": "Billing marcou invoice INV-2026-00194 como paga", "meta": "ha 18 min • billing"},
            {"title": "Marketplace Technicians recebeu novo aceite de tecnico", "meta": "ha 24 min • marketplace"},
            {"title": "Growth Engine gerou 8 leads qualificados da campanha Fitness", "meta": "ha 41 min • growth"},
            {"title": "Observability consolidou incidentes recorrentes de notificacao", "meta": "ha 58 min • observability"},
        ],
        "module_shortcuts": [
            {"slug": "smart-system", "title": "Smart System", "metric": "32 OS abertas", "tone": "indigo"},
            {"slug": "marketplace-technicians", "title": "Marketplace Technicians", "metric": "11 tecnicos elegiveis", "tone": "emerald"},
            {"slug": "growth-engine", "title": "Growth Engine", "metric": "74 leads no pipeline", "tone": "rose"},
            {"slug": "billing", "route_name": "admin-shell:billing-dashboard", "title": "Billing", "metric": "9 invoices vencidas", "tone": "orange"},
            {"slug": "analytics-platform", "title": "Analytics Platform", "metric": "14 dashboards prontos", "tone": "sky"},
            {"slug": "observability-center", "route_name": "admin-shell:observability-dashboard", "title": "Observability Center", "metric": "4 incidentes abertos", "tone": "red"},
        ],
        "operational_stream": [
            {"label": "Fila operacional", "items": "26 pendencias", "description": "Backoffice, billing e verificacoes em andamento."},
            {"label": "Eventos do ecossistema", "items": "182 eventos hoje", "description": "Integration bus e automacoes com alto volume controlado."},
            {"label": "Atalhos rapidos", "items": "7 acoes", "description": "Bootstrap, observability, billing e configuracoes de rollout."},
        ],
        "quick_actions": [
            {"label": "Executive War Room", "route_name": "admin-shell:executive-war-room", "permission_domain": "dashboard", "permission_action": "view"},
            {"label": "Abrir Smart System", "slug": "smart-system", "permission_domain": "dashboard", "permission_action": "view"},
            {"label": "Ativos criticos", "route_name": "admin-shell:smart-system-assets", "permission_domain": "assets", "permission_action": "view"},
            {"label": "Ordens de servico", "route_name": "admin-shell:smart-system-work-orders", "permission_domain": "work_orders", "permission_action": "view"},
            {"label": "Ver alertas criticos", "route_name": "admin-shell:observability-dashboard", "permission_domain": "observability_admin", "permission_action": "view"},
            {"label": "Revisar billing", "route_name": "admin-shell:billing-dashboard", "permission_domain": "billing_admin", "permission_action": "view"},
            {"label": "Entrar em configuracoes", "slug": "configuration-center"},
        ],
    }
    return _apply_tenant_context_to_dashboard(payload, tenant_context=tenant_context)


def get_smart_system_dashboard_context(tenant_context=None):
    tenant_context = tenant_context or {}
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    scope_client = company.name if company else "Academia Exemplo"
    scope_site = site.name if site else "Todos os sites permitidos"

    site_status = [
        {"client": "Academia Exemplo", "site": "Unidade Centro", "open_orders": "18", "delays": "3", "critical_assets": "4", "compliance": "93%", "status": "Sob controle", "tone": "emerald"},
        {"client": "Academia Exemplo", "site": "Unidade Norte", "open_orders": "11", "delays": "4", "critical_assets": "6", "compliance": "84%", "status": "Atencao", "tone": "amber"},
        {"client": "Laboratorio Exemplo", "site": "Laboratorio Campinas", "open_orders": "7", "delays": "2", "critical_assets": "2", "compliance": "96%", "status": "Saudavel", "tone": "sky"},
        {"client": "Panobianco", "site": "Academia Premium Sul", "open_orders": "16", "delays": "5", "critical_assets": "7", "compliance": "79%", "status": "Critico", "tone": "red"},
    ]
    scoped_site_status = [
        item
        for item in site_status
        if record_matches_scope(item, tenant_context, client_key="client", site_key="site")
    ] or site_status

    payload = {
        "page_actions": [
            {"label": "Nova OS", "route_name": "admin-shell:smart-system-work-order-create", "permission_domain": "work_orders", "permission_action": "create"},
            {"label": "Nova preventiva", "href": "#nova-preventiva", "permission_domain": "preventive_plans", "permission_action": "create"},
            {"label": "Registrar falha", "href": "#registrar-falha", "permission_domain": "failures", "permission_action": "create"},
            {"label": "Ver ativos", "route_name": "admin-shell:smart-system-assets", "permission_domain": "assets", "permission_action": "view"},
            {"label": "Ordens de servico", "route_name": "admin-shell:smart-system-work-orders", "permission_domain": "work_orders", "permission_action": "view"},
            {"label": "Preventivas", "route_name": "admin-shell:smart-system-preventives", "permission_domain": "preventive_plans", "permission_action": "view"},
            {"label": "Falhas", "route_name": "admin-shell:smart-system-failures", "permission_domain": "failures", "permission_action": "view"},
            {"label": "Checklists", "route_name": "admin-shell:smart-system-checklists", "permission_domain": "checklists", "permission_action": "view"},
            {"label": "Relatorios", "route_name": "admin-shell:smart-system-reports", "permission_domain": "reports", "permission_action": "view"},
            {"label": "Exportar visao", "href": "#exportar", "permission_domain": "reports", "permission_action": "export"},
        ],
        "filter_groups": [
            {"label": "Periodo", "type": "chips", "options": ["Hoje", "7 dias", "30 dias", "Trimestre"], "active": "30 dias"},
            {"label": "Site / unidade", "type": "select", "value": scope_site},
            {"label": "Cliente", "type": "select", "value": scope_client},
            {"label": "Criticidade", "type": "select", "value": "Todas"},
            {"label": "Status da OS", "type": "select", "value": "Abertas e em andamento"},
            {"label": "Tipo", "type": "select", "value": "Preventiva + Corretiva"},
        ],
        "kpis": [
            {"label": "Ativos monitorados", "value": "284", "context": "31 sob plano premium", "trend": "+4,1% vs mes anterior", "badge": "Cobertura alta", "tone": "indigo"},
            {"label": "Ordens abertas", "value": "52", "context": "18 em execucao", "trend": "-7 ordens vs ontem", "badge": "Fluxo controlado", "tone": "sky"},
            {"label": "OS atrasadas", "value": "9", "context": "4 sem responsavel", "trend": "+2 nas ultimas 24h", "badge": "Atencao", "tone": "amber"},
            {"label": "Preventivas do mes", "value": "118", "context": "96 concluidas", "trend": "81% aderencia mensal", "badge": "Planejado", "tone": "emerald"},
            {"label": "Falhas criticas", "value": "6", "context": "3 reincidentes", "trend": "-1 evento vs semana anterior", "badge": "Risco moderado", "tone": "red"},
            {"label": "Backlog tecnico", "value": "34", "context": "12 de alta criticidade", "trend": "+8 itens acumulados", "badge": "Pressao em campo", "tone": "orange"},
            {"label": "Disponibilidade operacional", "value": "96,8%", "context": "chillers e esteiras lideram uptime", "trend": "+0,6 pp", "badge": "Saudavel", "tone": "emerald"},
            {"label": "MTTR", "value": "3,4 h", "context": "tempo medio corretivo", "trend": "-18 min", "badge": "Melhorando", "tone": "teal"},
            {"label": "MTBF", "value": "186 h", "context": "ativos criticos", "trend": "+9 h", "badge": "Estavel", "tone": "violet"},
            {"label": "Conformidade preventiva", "value": "91%", "context": "janela do ciclo atual", "trend": "+3 pp", "badge": "Acima da meta", "tone": "cyan"},
        ],
        "operational_health": {
            "distribution": [
                {"label": "Ativos saudaveis", "value": 224, "percentage": 79, "tone": "emerald"},
                {"label": "Em atencao", "value": 42, "percentage": 15, "tone": "amber"},
                {"label": "Criticos", "value": 18, "percentage": 6, "tone": "red"},
            ],
            "focus_areas": [
                {"area": "HVAC - Unidade Centro", "summary": "4 ativos com alarme de temperatura e 2 corretivas pendentes", "tone": "red"},
                {"area": "Cardio Floor", "summary": "Esteiras com desgaste acelerado e backlog de pecas", "tone": "amber"},
                {"area": "Utilidades Prediais", "summary": "Disponibilidade acima da meta, sem OS criticas abertas", "tone": "emerald"},
            ],
            "critical_orders": [
                {"label": "OS criticas abertas", "value": "5"},
                {"label": "Paradas de ativo", "value": "2"},
                {"label": "Areas com maior incidencia", "value": "HVAC / Cardio"},
            ],
        },
        "work_orders": [
            {"code": "OS-2026-0148", "asset": "CHILLER-UNID-A", "type": "Corretiva", "priority": "Critica", "status": "Em andamento", "owner": "Carlos Mota", "deadline": "Hoje 18:00", "tone": "red"},
            {"code": "OS-2026-0151", "asset": "ESTEIRA-ERG-12", "type": "Preventiva", "priority": "Media", "status": "Programada", "owner": "Ana Lopes", "deadline": "Amanha 09:00", "tone": "sky"},
            {"code": "OS-2026-0154", "asset": "COMP-AR-01", "type": "Corretiva", "priority": "Alta", "status": "Aguardando peca", "owner": "Equipe HVAC", "deadline": "Hoje 16:30", "tone": "amber"},
            {"code": "OS-2026-0143", "asset": "CAMARA-CLIMATICA-01", "type": "Inspecao", "priority": "Alta", "status": "Atrasada", "owner": "Bruno Salles", "deadline": "Ontem 14:00", "tone": "red"},
            {"code": "OS-2026-0137", "asset": "QGBT-ACADEMIA-C", "type": "Preventiva", "priority": "Media", "status": "Concluida", "owner": "Juliana Costa", "deadline": "Concluida hoje", "tone": "emerald"},
        ],
        "backlog": {
            "total": "34",
            "by_criticality": [
                {"label": "Alta criticidade", "value": "12"},
                {"label": "Media criticidade", "value": "15"},
                {"label": "Baixa criticidade", "value": "7"},
            ],
            "by_type": [
                {"label": "Corretiva", "value": "16"},
                {"label": "Preventiva", "value": "11"},
                {"label": "Inspecao", "value": "7"},
            ],
            "urgent_items": [
                {"title": "CHILLER-UNID-A com parada parcial", "meta": "OS-2026-0148 • 6h em aberto"},
                {"title": "COMP-AR-01 aguardando kit de vedacao", "meta": "OS-2026-0154 • aguardando peca ha 2 dias"},
                {"title": "HVAC-ACADEMIA-02 sem inspeção trimestral", "meta": "preventiva P-332 atrasada ha 5 dias"},
            ],
        },
        "reliability": {
            "recurring_failures": [
                {"title": "Falha de partida em esteiras cardio", "meta": "9 ocorrencias • modo: capacitor / chave magnetica"},
                {"title": "Oscilacao termica em chillers", "meta": "4 ocorrencias • modo: sensor / fluxo"},
                {"title": "Perda de pressao em compressores", "meta": "3 ocorrencias • modo: vazamento / vedacao"},
            ],
            "top_assets": [
                {"asset": "ESTEIRA-ERG-12", "failures": "5 falhas", "trend": "MTBF 72h"},
                {"asset": "CHILLER-UNID-A", "failures": "4 falhas", "trend": "MTBF 96h"},
                {"asset": "COMP-AR-01", "failures": "3 falhas", "trend": "MTBF 104h"},
            ],
            "recent_events": [
                {"timestamp": "08:10", "event": "Falha de partida registrada em ESTEIRA-ERG-12", "reference": "FailureEvent FE-0093"},
                {"timestamp": "09:24", "event": "Inspecao termografica indicou aquecimento em QGBT-ACADEMIA-C", "reference": "OS-2026-0150"},
                {"timestamp": "11:42", "event": "RCM sugeriu revisão do plano do CHILLER-UNID-A", "reference": "Plano PM-078"},
            ],
            "trend_text": "Confiabilidade melhorou em utilidades, mas cardio floor continua concentrando reincidencia corretiva.",
        },
        "preventive_plan": {
            "headline": [
                {"label": "Programadas hoje", "value": "14"},
                {"label": "Da semana", "value": "38"},
                {"label": "Atrasadas", "value": "7"},
                {"label": "Concluidas", "value": "96"},
            ],
            "adherence": 91,
            "schedule": [
                {"date": "Hoje 08:00", "asset": "HVAC-ACADEMIA-02", "activity": "Limpeza e medicao de corrente", "owner": "Equipe HVAC", "status": "Em execucao"},
                {"date": "Hoje 10:30", "asset": "ESTEIRA-ERG-08", "activity": "Inspecao de correia e lubrificacao", "owner": "Ana Lopes", "status": "Programada"},
                {"date": "Amanha 07:00", "asset": "CHILLER-UNID-A", "activity": "Checklist semanal de utilidades", "owner": "Carlos Mota", "status": "Confirmada"},
                {"date": "Qui 14:00", "asset": "COMP-AR-01", "activity": "Troca preventiva de vedacao", "owner": "Bruno Salles", "status": "Atrasada"},
            ],
        },
        "alerts": [
            {"title": "OS vencida sem responsavel definido", "description": "OS-2026-0143 para CAMARA-CLIMATICA-01 segue sem aceite tecnico.", "severity": "critical"},
            {"title": "Preventiva critica atrasada", "description": "Plano PM-332 do HVAC-ACADEMIA-02 excedeu janela em 5 dias.", "severity": "warning"},
            {"title": "Ativo parado em area premium", "description": "CHILLER-UNID-A impacta conforto térmico da unidade A.", "severity": "critical"},
            {"title": "Aguardando peca acima do SLA", "description": "COMP-AR-01 aguarda kit de vedacao ha 49h.", "severity": "warning"},
            {"title": "Equipamento sem inspeção recente", "description": "QGBT-ACADEMIA-C sem inspeção termográfica há 46 dias.", "severity": "info"},
        ],
        "activity_feed": [
            {"time": "12:14", "actor": "Carlos Mota", "event": "concluiu intervenção corretiva", "reference": "OS-2026-0137 • QGBT-ACADEMIA-C"},
            {"time": "11:42", "actor": "Motor de regras", "event": "reprogramou preventiva semanal", "reference": "PM-078 • CHILLER-UNID-A"},
            {"time": "10:08", "actor": "Ana Lopes", "event": "registrou falha reincidente", "reference": "FE-0093 • ESTEIRA-ERG-12"},
            {"time": "09:31", "actor": "Bruno Salles", "event": "abriu OS aguardando peca", "reference": "OS-2026-0154 • COMP-AR-01"},
            {"time": "08:55", "actor": "Juliana Costa", "event": "atualizou criticidade do ativo", "reference": "HVAC-ACADEMIA-02 • criticidade alta"},
        ],
        "action_shortcuts": [
            {"label": "Abrir ordem de servico", "context": "Registro corretivo imediato", "route_name": "admin-shell:smart-system-work-order-create", "tone": "indigo"},
            {"label": "Cadastrar ativo", "context": "Novo equipamento ou substituicao", "href": "#ativos", "tone": "sky"},
            {"label": "Registrar falha", "context": "Evento tecnico e confiabilidade", "href": "#registrar-falha", "tone": "red"},
            {"label": "Lancar inspecao", "context": "Checklist e ronda operacional", "href": "#inspecao", "tone": "emerald"},
            {"label": "Consultar backlog", "context": "Pendencias e aging", "href": "#backlog", "tone": "amber"},
            {"label": "Ver indicadores", "context": "MTBF, MTTR e disponibilidade", "href": "#indicadores", "tone": "violet"},
        ],
        "site_status": scoped_site_status,
    }
    if company or site:
        payload["alerts"] = [
            alert
            for alert in payload["alerts"]
            if (not site and scope_client in alert["description"]) or (site and scope_site in alert["description"]) or "QGBT" not in alert["description"]
        ] or payload["alerts"][:3]
    return payload


def build_module_page_context(module_slug):
    page = MODULE_PAGES[module_slug].copy()
    page["highlights"] = [
        {"label": "Widgets prontos", "value": "Base shell pronta"},
        {"label": "Integração futura", "value": "APIs e cards dinamicos"},
        {"label": "Estado da tela", "value": page["status"]},
    ]
    return page
