from copy import deepcopy

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema


SMART360_TAGS = [
    {"name": "Auth", "description": "Autenticacao, sessoes, onboarding e identidade do ecossistema."},
    {"name": "Core Platform", "description": "Saude da API, root endpoint e capacidades centrais do ecossistema."},
    {"name": "Users", "description": "Usuarios e memberships do core platform."},
    {"name": "Companies", "description": "Empresas e workspaces do ecossistema."},
    {"name": "Roles", "description": "Roles legadas do core platform."},
    {"name": "Smart Site Factory", "description": "Linha de montagem digital de sites nichados."},
    {"name": "Growth Engine", "description": "Leads, campanhas, interacoes e pipeline comercial."},
    {"name": "Caneca de Garagem", "description": "Marketplace-first de produtos personalizados e fila de producao."},
    {"name": "Smart System", "description": "Gestao de manutencao, ativos, OS, falhas e historico."},
    {"name": "Marketplace Technicians", "description": "Marketplace operacional de tecnicos e prestadores."},
    {"name": "Marketplace Analytical", "description": "Marketplace B2B de analises, laudos e servicos tecnicos."},
    {"name": "Knowledge Engine", "description": "Base de conhecimento tecnica estruturada do ecossistema."},
    {"name": "Analytics Platform", "description": "Eventos, metricas, dashboards e snapshots."},
    {"name": "Integration Bus", "description": "Eventos, workflows, automacoes e dead letters internos."},
    {"name": "Billing", "description": "Planos, assinaturas, invoices, pagamentos, creditos e ledger."},
    {"name": "Notification Center", "description": "Notificacoes in-app, email, templates e entregas."},
    {"name": "Backoffice", "description": "Cockpit operacional interno com filas, alertas e tarefas."},
    {"name": "Files Center", "description": "Arquivos, midias, versionamento, colecoes e vinculos transversais."},
    {"name": "Global Search", "description": "Busca unificada, indices e historico de consultas."},
    {"name": "Reporting Center", "description": "Templates de relatorio, exportacoes e historico."},
    {"name": "Configuration Center", "description": "System settings, feature flags, profiles e toggles operacionais."},
    {"name": "Scheduling Center", "description": "Calendarios, eventos, recorrencias, disponibilidade e lembretes."},
    {"name": "AI Automation Center", "description": "Prompts, tasks, automacoes, artefatos e readiness para IA."},
    {"name": "Access Control", "description": "RBAC, policies, escopos, aprovacoes sensiveis e auditoria de acesso."},
    {"name": "Observability", "description": "Logs estruturados, incidentes, metricas tecnicas, job traces e healthchecks."},
    {"name": "Public Context", "description": "Contexto autenticado, empresas e sites permitidos da API publica."},
    {"name": "Public Assets", "description": "Ativos expostos pela API publica com escopo por tenant e site."},
    {"name": "Public Work Orders", "description": "Ordens de servico expostas pela API publica."},
    {"name": "Public Preventives", "description": "Planos preventivos e agenda expostos pela API publica."},
    {"name": "Public Failures", "description": "Falhas, RCA e confiabilidade expostas pela API publica."},
    {"name": "Public Checklists", "description": "Checklists e execucoes acessiveis pela API publica."},
    {"name": "Public Inventory", "description": "Pecas, estoque e movimentacoes da API publica."},
    {"name": "Public Reports", "description": "Metadados e downloads de relatorios tecnicos da API publica."},
    {"name": "Trust & Safety", "description": "Reservado para verificacoes, elegibilidade e seguranca futura."},
    {"name": "CRM Center", "description": "Reservado para contas, oportunidades e relacionamento futuro."},
]

TAG_GROUPS = [
    {"name": "Foundation", "tags": ["Auth", "Core Platform", "Users", "Companies", "Roles", "Access Control"]},
    {"name": "Business Contexts", "tags": ["Smart Site Factory", "Growth Engine", "Caneca de Garagem", "Smart System"]},
    {
        "name": "Marketplaces",
        "tags": ["Marketplace Technicians", "Marketplace Analytical", "Trust & Safety", "CRM Center"],
    },
    {
        "name": "Shared Intelligence",
        "tags": ["Knowledge Engine", "Analytics Platform", "Global Search", "AI Automation Center"],
    },
    {
        "name": "Operational Platform",
        "tags": ["Integration Bus", "Billing", "Notification Center", "Backoffice", "Files Center", "Reporting Center", "Configuration Center", "Scheduling Center", "Observability"],
    },
    {
        "name": "Public API",
        "tags": ["Public Context", "Public Assets", "Public Work Orders", "Public Preventives", "Public Failures", "Public Checklists", "Public Inventory", "Public Reports"],
    },
]

PATH_TAG_MAP = {
    "/api/v1/auth/": "Auth",
    "/api/v1/identity/": "Auth",
    "/api/v1/core/": "Core Platform",
    "/health/": "Core Platform",
    "/api/v1/users/": "Users",
    "/api/v1/companies/": "Companies",
    "/api/v1/roles/": "Roles",
    "/api/v1/site-factory/": "Smart Site Factory",
    "/api/v1/growth/": "Growth Engine",
    "/api/v1/caneca-de-garagem/": "Caneca de Garagem",
    "/api/v1/smart-system/": "Smart System",
    "/api/v1/marketplace-technicians/": "Marketplace Technicians",
    "/api/v1/marketplace-analytical/": "Marketplace Analytical",
    "/api/v1/knowledge/": "Knowledge Engine",
    "/api/v1/analytics/": "Analytics Platform",
    "/api/v1/integration-bus/": "Integration Bus",
    "/api/v1/billing/": "Billing",
    "/api/v1/notifications/": "Notification Center",
    "/api/v1/backoffice/": "Backoffice",
    "/api/v1/files/": "Files Center",
    "/api/v1/search/": "Global Search",
    "/api/v1/reporting/": "Reporting Center",
    "/api/v1/configuration/": "Configuration Center",
    "/api/v1/scheduling/": "Scheduling Center",
    "/api/v1/ai/": "AI Automation Center",
    "/api/v1/access-control/": "Access Control",
    "/api/v1/observability/": "Observability",
    "/api/public/v1/context/": "Public Context",
    "/api/public/v1/companies/": "Public Context",
    "/api/public/v1/sites/": "Public Context",
    "/api/public/v1/assets/": "Public Assets",
    "/api/public/v1/work-orders/": "Public Work Orders",
    "/api/public/v1/preventives/": "Public Preventives",
    "/api/public/v1/failures/": "Public Failures",
    "/api/public/v1/checklists/": "Public Checklists",
    "/api/public/v1/checklist-executions/": "Public Checklists",
    "/api/public/v1/parts/": "Public Inventory",
    "/api/public/v1/stock-movements/": "Public Inventory",
    "/api/public/v1/reports/": "Public Reports",
}


class Smart360AutoSchema(AutoSchema):
    def get_tags(self):
        for prefix, tag in PATH_TAG_MAP.items():
            if self.path.startswith(prefix):
                return [tag]
        return super().get_tags()


class IdentityTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.identity.authentication.IdentityTokenAuthentication"
    name = "IdentityTokenAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "Token",
            "description": "Use `Authorization: Bearer <token>` ou `Authorization: Token <token>`.",
        }


class IntegrationCredentialAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.public_api.authentication.IntegrationCredentialAuthentication"
    name = "PublicApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Use `Authorization: ApiKey <prefix.secret>` para credenciais de integracao.",
        }


class PublicApiAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.public_api.authentication.PublicApiAuthentication"
    name = "PublicApiAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Aceita `Bearer <token>`, `Token <token>` ou `ApiKey <prefix.secret>`.",
        }


def smart360_postprocess_schema(result, generator, request, public):
    schema = deepcopy(result)
    schema["x-tagGroups"] = TAG_GROUPS
    return schema
