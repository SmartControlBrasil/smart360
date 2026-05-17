from __future__ import annotations

from dataclasses import dataclass

from apps.access_control_center.models import (
    PermissionAction,
    PermissionDomain,
    Role,
    RolePermission,
    UserRoleAssignment,
)
from apps.access_control_center.services.access_service import AccessControlService
from apps.companies.models import Membership


SMART_SYSTEM_DOMAINS = {
    "dashboard": {
        "name": "Dashboard",
        "description": "Visao executiva e operacional do Smart System.",
        "module_name": "smart_system",
        "actions": ["view"],
    },
    "assets": {
        "name": "Ativos",
        "description": "Carteira, criticidade e ciclo de vida de ativos.",
        "module_name": "smart_system",
        "actions": ["view", "create", "update", "delete", "export"],
    },
    "work_orders": {
        "name": "Ordens de Servico",
        "description": "Planejamento, atribuicao, execucao e encerramento de OS.",
        "module_name": "smart_system",
        "actions": ["view", "create", "update", "assign", "execute", "close", "export"],
    },
    "preventive_plans": {
        "name": "Planos Preventivos",
        "description": "Cobertura preventiva, recorrencia, agenda e aderencia.",
        "module_name": "smart_system",
        "actions": ["view", "create", "update", "manage", "execute", "export"],
    },
    "failures": {
        "name": "Falhas e RCA",
        "description": "Registro de falhas, diagnostico, RCA e confiabilidade.",
        "module_name": "smart_system",
        "actions": ["view", "create", "update", "rca", "export"],
    },
    "checklists": {
        "name": "Checklists",
        "description": "Modelagem e execucao de checklists tecnicos.",
        "module_name": "smart_system",
        "actions": ["view", "create", "update", "execute", "approve"],
    },
    "work_execution": {
        "name": "Execucao Tecnica",
        "description": "Execucao de OS em campo, horas, materiais e evidencias.",
        "module_name": "smart_system",
        "actions": ["view", "execute", "close", "log_hours", "log_materials", "log_evidence"],
    },
    "scheduling": {
        "name": "Agenda e Roteirizacao",
        "description": "Agenda operacional, distribuicao de visitas, conflito e rota sugerida.",
        "module_name": "smart_system",
        "actions": ["view", "create", "update", "assign", "manage"],
    },
    "service_signatures": {
        "name": "Assinaturas de Servico",
        "description": "Captura e consulta de assinatura operacional de tecnico e cliente.",
        "module_name": "smart_system",
        "actions": ["view", "capture", "export"],
    },
    "inventory": {
        "name": "Pecas e Estoque",
        "description": "MRO, sobressalentes, movimentacoes e consumo em OS.",
        "module_name": "smart_system",
        "actions": ["view", "create", "update", "adjust_stock", "consume", "export"],
    },
    "reports": {
        "name": "Relatorios",
        "description": "Relatorios tecnicos, PDFs e exportacao documental.",
        "module_name": "smart_system",
        "actions": ["view", "generate_report", "export"],
    },
    "quotes": {
        "name": "Orcamentos Tecnicos",
        "description": "Orcamentos, aprovacao de pecas e aceite comercial da OS.",
        "module_name": "smart_system",
        "actions": ["view", "create", "update", "send", "approve", "reject", "export"],
    },
    "maintenance_contracts": {
        "name": "Contratos Recorrentes",
        "description": "Contratos de manutencao, cobertura de ativos, preventivas automaticas e cobranca recorrente.",
        "module_name": "smart_system",
        "actions": ["view", "create", "update", "manage", "generate", "export"],
    },
    "users": {
        "name": "Usuarios e Perfis",
        "description": "Gestao de perfis e governanca operacional do Smart System.",
        "module_name": "smart_system",
        "actions": ["view", "manage"],
    },
    "smart_system_settings": {
        "name": "Configuracoes do Smart System",
        "description": "Parametros sensiveis e configuracoes operacionais do modulo.",
        "module_name": "smart_system",
        "actions": ["view", "manage"],
    },
    "billing_admin": {
        "name": "Billing da Plataforma",
        "description": "Planos, contratos, assinaturas, faturamento e operacao financeira SaaS.",
        "module_name": "billing",
        "actions": ["view", "manage", "export"],
    },
    "analytics_admin": {
        "name": "Analytics Executivo",
        "description": "Rentabilidade operacional, produtividade, contratos, SLA e leitura executiva da plataforma.",
        "module_name": "analytics_platform",
        "actions": ["view", "manage", "export"],
    },
    "ai_agents_admin": {
        "name": "AI Agents Center",
        "description": "Registry, runs, recommendations, action proposals e controle de agentes autonomos.",
        "module_name": "ai_agents_center",
        "actions": ["view", "manage", "approve"],
    },
    "observability_admin": {
        "name": "Observabilidade da Plataforma",
        "description": "Saude da plataforma, request traces, incidentes e auditoria sensivel.",
        "module_name": "observability",
        "actions": ["view", "manage"],
    },
    "marketplace_dashboard": {
        "name": "Marketplace Dashboard",
        "description": "Visao executiva do marketplace de tecnicos.",
        "module_name": "marketplace_technicians",
        "actions": ["view"],
    },
    "marketplace_requests": {
        "name": "Marketplace Requests",
        "description": "Demandas de servico publicadas pelas empresas no marketplace.",
        "module_name": "marketplace_technicians",
        "actions": ["view", "create", "assign"],
    },
    "marketplace_offers": {
        "name": "Marketplace Offers",
        "description": "Ofertas enviadas por tecnicos e decisao comercial.",
        "module_name": "marketplace_technicians",
        "actions": ["view", "create", "manage"],
    },
    "marketplace_matching": {
        "name": "Marketplace Matching",
        "description": "Ranking inteligente de tecnicos, score e sugestoes automaticas.",
        "module_name": "marketplace_technicians",
        "actions": ["view", "manage"],
    },
    "marketplace_technicians": {
        "name": "Marketplace Technicians",
        "description": "Perfis tecnicos, especialidades, verificacao e cobertura regional.",
        "module_name": "marketplace_technicians",
        "actions": ["view", "update"],
    },
    "marketplace_assignments": {
        "name": "Marketplace Assignments",
        "description": "Atribuicoes de servicos e execucao em campo no marketplace.",
        "module_name": "marketplace_technicians",
        "actions": ["view", "execute", "manage"],
    },
    "marketplace_reviews": {
        "name": "Marketplace Reviews",
        "description": "Avaliacoes pos-servico e reputacao operacional do marketplace.",
        "module_name": "marketplace_technicians",
        "actions": ["view", "create", "manage"],
    },
    "client_portal_dashboard": {
        "name": "Client Portal Dashboard",
        "description": "Dashboard executivo e contextual do portal do cliente.",
        "module_name": "client_portal",
        "actions": ["view"],
    },
    "client_portal_assets": {
        "name": "Client Portal Assets",
        "description": "Consulta de ativos e status operacional no portal.",
        "module_name": "client_portal",
        "actions": ["view"],
    },
    "client_portal_work_orders": {
        "name": "Client Portal Work Orders",
        "description": "Consulta de ordens de servico no portal.",
        "module_name": "client_portal",
        "actions": ["view"],
    },
    "client_portal_preventives": {
        "name": "Client Portal Preventives",
        "description": "Consulta de preventivas e agenda do cliente.",
        "module_name": "client_portal",
        "actions": ["view"],
    },
    "client_portal_reports": {
        "name": "Client Portal Reports",
        "description": "Consulta e download de relatorios para o cliente.",
        "module_name": "client_portal",
        "actions": ["view", "export"],
    },
    "client_portal_quotes": {
        "name": "Client Portal Quotes",
        "description": "Consulta e decisao de aprovacao/rejeicao de orcamentos pelo cliente.",
        "module_name": "client_portal",
        "actions": ["view", "approve", "reject"],
    },
    "client_portal_contracts": {
        "name": "Client Portal Contracts",
        "description": "Consulta de contratos ativos, ativos cobertos e historico preventivo do cliente.",
        "module_name": "client_portal",
        "actions": ["view"],
    },
    "client_portal_requests": {
        "name": "Client Portal Requests",
        "description": "Abertura e acompanhamento de solicitacoes do cliente.",
        "module_name": "client_portal",
        "actions": ["view", "create"],
    },
    "client_portal_sites": {
        "name": "Client Portal Sites",
        "description": "Consulta de unidades e contexto operacional do cliente.",
        "module_name": "client_portal",
        "actions": ["view"],
    },
    "client_portal_profile": {
        "name": "Client Portal Profile",
        "description": "Meu perfil, contatos e contexto do usuario do portal.",
        "module_name": "client_portal",
        "actions": ["view"],
    },
}

SMART_SYSTEM_ROLE_MATRIX = {
    "super-admin": {
        "name": "Super Admin",
        "role_type": Role.RoleType.SYSTEM,
        "description": "Acesso total ao Smart360 e ao Smart System.",
        "permissions": {
            domain_slug: list(config["actions"])
            for domain_slug, config in SMART_SYSTEM_DOMAINS.items()
        },
    },
    "company-admin": {
        "name": "Admin da Empresa",
        "role_type": Role.RoleType.COMPANY,
        "description": "Governanca operacional ampla do Smart System dentro da empresa.",
        "permissions": {
            domain_slug: list(config["actions"])
            for domain_slug, config in SMART_SYSTEM_DOMAINS.items()
            if domain_slug not in {"billing_admin", "observability_admin"}
        },
    },
    "maintenance-manager": {
        "name": "Gestor de Manutencao",
        "role_type": Role.RoleType.INTERNAL,
        "description": "Gerencia ativos, OS, preventivas, falhas, checklists e relatorios.",
        "permissions": {
            "dashboard": ["view"],
            "assets": ["view", "create", "update", "delete", "export"],
            "work_orders": ["view", "create", "update", "assign", "execute", "close", "export"],
            "preventive_plans": ["view", "create", "update", "manage", "execute", "export"],
            "failures": ["view", "create", "update", "rca", "export"],
            "checklists": ["view", "create", "update", "execute", "approve"],
            "work_execution": ["view", "execute", "close", "log_hours", "log_materials", "log_evidence"],
            "scheduling": ["view", "create", "update", "assign", "manage"],
            "service_signatures": ["view", "capture", "export"],
            "inventory": ["view", "consume", "export"],
            "reports": ["view", "generate_report", "export"],
            "quotes": ["view", "create", "update", "send", "approve", "reject", "export"],
            "maintenance_contracts": ["view", "create", "update", "manage", "generate", "export"],
            "analytics_admin": ["view", "export"],
            "ai_agents_admin": ["view", "manage", "approve"],
            "users": ["view"],
            "smart_system_settings": ["view"],
            "marketplace_dashboard": ["view"],
            "marketplace_requests": ["view", "create", "assign"],
            "marketplace_offers": ["view", "manage"],
            "marketplace_matching": ["view", "manage"],
            "marketplace_technicians": ["view"],
            "marketplace_assignments": ["view", "execute", "manage"],
            "marketplace_reviews": ["view", "create", "manage"],
        },
    },
    "planner": {
        "name": "Planejador",
        "role_type": Role.RoleType.INTERNAL,
        "description": "Planeja OS, preventivas e acompanha cobertura operacional.",
        "permissions": {
            "dashboard": ["view"],
            "assets": ["view"],
            "work_orders": ["view", "create", "update", "assign", "export"],
            "preventive_plans": ["view", "create", "update", "manage", "export"],
            "failures": ["view"],
            "checklists": ["view"],
            "work_execution": ["view"],
            "scheduling": ["view", "create", "update", "assign"],
            "service_signatures": ["view"],
            "inventory": ["view"],
            "reports": ["view", "generate_report", "export"],
            "quotes": ["view", "create", "update", "send", "export"],
            "maintenance_contracts": ["view", "create", "update", "manage", "generate", "export"],
            "analytics_admin": ["view"],
            "ai_agents_admin": ["view"],
            "marketplace_dashboard": ["view"],
            "marketplace_requests": ["view", "create", "assign"],
            "marketplace_offers": ["view", "manage"],
            "marketplace_matching": ["view"],
            "marketplace_technicians": ["view"],
            "marketplace_assignments": ["view"],
            "marketplace_reviews": ["view"],
        },
    },
    "technician": {
        "name": "Tecnico",
        "role_type": Role.RoleType.TECHNICIAN,
        "description": "Executa OS, checklists, diagnostico e registros tecnicos em campo.",
        "permissions": {
            "dashboard": ["view"],
            "assets": ["view"],
            "work_orders": ["view", "execute"],
            "preventive_plans": ["view", "execute"],
            "failures": ["view", "create", "update"],
            "checklists": ["view", "execute"],
            "work_execution": ["view", "execute", "log_hours", "log_materials", "log_evidence"],
            "scheduling": ["view"],
            "service_signatures": ["view", "capture"],
            "inventory": ["view", "consume"],
            "reports": ["view"],
            "quotes": ["view"],
            "maintenance_contracts": ["view"],
            "marketplace_dashboard": ["view"],
            "marketplace_requests": ["view"],
            "marketplace_offers": ["view", "create"],
            "marketplace_matching": ["view"],
            "marketplace_technicians": ["view", "update"],
            "marketplace_assignments": ["view", "execute"],
            "marketplace_reviews": ["view"],
        },
    },
    "inventory-clerk": {
        "name": "Almoxarife / Estoque",
        "role_type": Role.RoleType.INTERNAL,
        "description": "Opera entradas, saidas, ajustes e disponibilidade de MRO.",
        "permissions": {
            "dashboard": ["view"],
            "assets": ["view"],
            "work_orders": ["view"],
            "scheduling": ["view", "assign", "manage"],
            "service_signatures": ["view"],
            "inventory": ["view", "create", "update", "adjust_stock", "consume", "export"],
            "reports": ["view", "export"],
            "quotes": ["view"],
            "maintenance_contracts": ["view"],
            "marketplace_dashboard": ["view"],
            "marketplace_requests": ["view"],
            "marketplace_offers": ["view"],
            "marketplace_matching": ["view"],
            "marketplace_technicians": ["view"],
            "marketplace_assignments": ["view"],
            "marketplace_reviews": ["view"],
        },
    },
    "auditor-readonly": {
        "name": "Auditor / Leitura",
        "role_type": Role.RoleType.INTERNAL,
        "description": "Consulta operacional sem alteracoes e sem exportacoes sensiveis.",
        "permissions": {
            "dashboard": ["view"],
            "assets": ["view"],
            "work_orders": ["view"],
            "preventive_plans": ["view"],
            "failures": ["view"],
            "checklists": ["view"],
            "work_execution": ["view"],
            "scheduling": ["view"],
            "service_signatures": ["view"],
            "inventory": ["view"],
            "reports": ["view"],
            "quotes": ["view"],
            "analytics_admin": ["view"],
            "ai_agents_admin": ["view"],
            "marketplace_dashboard": ["view"],
            "marketplace_requests": ["view"],
            "marketplace_offers": ["view"],
            "marketplace_matching": ["view"],
            "marketplace_technicians": ["view"],
            "marketplace_assignments": ["view"],
            "marketplace_reviews": ["view"],
        },
    },
    "finance-readonly": {
        "name": "Financeiro / Leitura Operacional",
        "role_type": Role.RoleType.INTERNAL,
        "description": "Consulta restrita a documentos e contexto operacional resumido.",
        "permissions": {
            "dashboard": ["view"],
            "work_orders": ["view"],
            "scheduling": ["view"],
            "service_signatures": ["view"],
            "reports": ["view"],
            "quotes": ["view"],
            "maintenance_contracts": ["view"],
            "billing_admin": ["view", "export"],
            "analytics_admin": ["view", "export"],
            "ai_agents_admin": ["view"],
            "marketplace_dashboard": ["view"],
            "marketplace_requests": ["view"],
            "marketplace_matching": ["view"],
            "marketplace_assignments": ["view"],
            "marketplace_reviews": ["view"],
        },
    },
    "client-admin": {
        "name": "Cliente Admin",
        "role_type": Role.RoleType.COMPANY,
        "description": "Administrador do portal do cliente com visao completa do tenant.",
        "permissions": {
            "client_portal_dashboard": ["view"],
            "client_portal_assets": ["view"],
            "client_portal_work_orders": ["view"],
            "client_portal_preventives": ["view"],
            "client_portal_reports": ["view", "export"],
            "client_portal_quotes": ["view", "approve", "reject"],
            "client_portal_contracts": ["view"],
            "client_portal_requests": ["view", "create"],
            "client_portal_sites": ["view"],
            "client_portal_profile": ["view"],
        },
    },
    "client-manager": {
        "name": "Cliente Gestor",
        "role_type": Role.RoleType.COMPANY,
        "description": "Gestor do cliente com acompanhamento de ativos, OS, preventivas e relatorios.",
        "permissions": {
            "client_portal_dashboard": ["view"],
            "client_portal_assets": ["view"],
            "client_portal_work_orders": ["view"],
            "client_portal_preventives": ["view"],
            "client_portal_reports": ["view", "export"],
            "client_portal_quotes": ["view", "approve", "reject"],
            "client_portal_contracts": ["view"],
            "client_portal_requests": ["view", "create"],
            "client_portal_sites": ["view"],
            "client_portal_profile": ["view"],
        },
    },
    "client-readonly": {
        "name": "Cliente Leitura",
        "role_type": Role.RoleType.COMPANY,
        "description": "Consulta operacional do portal sem abertura de novas solicitacoes.",
        "permissions": {
            "client_portal_dashboard": ["view"],
            "client_portal_assets": ["view"],
            "client_portal_work_orders": ["view"],
            "client_portal_preventives": ["view"],
            "client_portal_reports": ["view"],
            "client_portal_quotes": ["view"],
            "client_portal_contracts": ["view"],
            "client_portal_requests": ["view"],
            "client_portal_sites": ["view"],
            "client_portal_profile": ["view"],
        },
    },
    "requester": {
        "name": "Solicitante",
        "role_type": Role.RoleType.COMPANY,
        "description": "Usuario do cliente focado em abrir e acompanhar solicitacoes.",
        "permissions": {
            "client_portal_dashboard": ["view"],
            "client_portal_assets": ["view"],
            "client_portal_work_orders": ["view"],
            "client_portal_preventives": ["view"],
            "client_portal_reports": ["view"],
            "client_portal_quotes": ["view"],
            "client_portal_contracts": ["view"],
            "client_portal_requests": ["view", "create"],
            "client_portal_sites": ["view"],
            "client_portal_profile": ["view"],
        },
    },
}

SMART_SYSTEM_PERMISSION_KEYS = [
    f"{domain_slug}.{action_slug}"
    for domain_slug, config in SMART_SYSTEM_DOMAINS.items()
    for action_slug in config["actions"]
]

PERMISSION_METADATA_KEYS = {"permission_domain", "permission_action"}


@dataclass(frozen=True)
class SmartSystemPermission:
    domain: str
    action: str

    @property
    def key(self) -> str:
        return f"{self.domain}.{self.action}"


def bootstrap_smart_system_access():
    created_domains = 0
    created_actions = 0
    created_roles = 0
    updated_links = 0

    domains = {}
    actions = {}
    for domain_slug, domain_config in SMART_SYSTEM_DOMAINS.items():
        domain, created = PermissionDomain.objects.update_or_create(
            slug=domain_slug,
            defaults={
                "name": domain_config["name"],
                "description": domain_config["description"],
                "module_name": domain_config["module_name"],
                "is_active": True,
            },
        )
        domains[domain_slug] = domain
        if created:
            created_domains += 1
        for action_slug in domain_config["actions"]:
            action, action_created = PermissionAction.objects.update_or_create(
                domain=domain,
                action_name=action_slug,
                defaults={
                    "slug": f"{domain.slug}-{action_slug}",
                    "description": f"{action_slug} em {domain_config['name']}.",
                    "is_active": True,
                },
            )
            actions[(domain_slug, action_slug)] = action
            if action_created:
                created_actions += 1

    for role_slug, role_config in SMART_SYSTEM_ROLE_MATRIX.items():
        role, created = Role.objects.update_or_create(
            slug=role_slug,
            defaults={
                "name": role_config["name"],
                "role_type": role_config["role_type"],
                "description": role_config["description"],
                "is_system_role": True,
                "is_active": True,
            },
        )
        if created:
            created_roles += 1
        allowed_keys = {
            (domain_slug, action_slug)
            for domain_slug, action_slugs in role_config["permissions"].items()
            for action_slug in action_slugs
        }
        for domain_slug, domain_config in SMART_SYSTEM_DOMAINS.items():
            for action_slug in domain_config["actions"]:
                _, _created = RolePermission.objects.update_or_create(
                    role=role,
                    permission_domain=domains[domain_slug],
                    permission_action=actions[(domain_slug, action_slug)],
                    defaults={"is_allowed": (domain_slug, action_slug) in allowed_keys},
                )
                updated_links += 1

    return {
        "domains": len(domains),
        "created_domains": created_domains,
        "actions": len(actions),
        "created_actions": created_actions,
        "roles": len(SMART_SYSTEM_ROLE_MATRIX),
        "created_roles": created_roles,
        "role_permission_links_updated": updated_links,
    }


def assign_smart_system_role(user, role_slug: str, company=None, assigned_by=None, is_active: bool = True):
    role = Role.objects.get(slug=role_slug)
    assignment, _ = UserRoleAssignment.objects.update_or_create(
        user=user,
        role=role,
        company=company,
        scope_type=UserRoleAssignment.ScopeType.COMPANY if company else UserRoleAssignment.ScopeType.GLOBAL,
        scope_reference=(company.slug if company else ""),
        defaults={
            "assigned_by": assigned_by,
            "is_active": is_active,
        },
    )
    return assignment


def get_default_company_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return None
    membership = (
        Membership.objects.select_related("company")
        .filter(user=user, status=Membership.Status.ACTIVE)
        .order_by("-is_primary", "created_at")
        .first()
    )
    return membership.company if membership else None


def has_smart_system_permission(
    user,
    domain_slug: str,
    action_slug: str,
    *,
    company=None,
    log_decision: bool = False,
    resource_type: str = "",
    resource_id: str = "",
    reason: str = "",
):
    resolved_company = company or get_default_company_for_user(user)
    payload = {}
    if resolved_company is not None:
        payload["company_id"] = resolved_company.id
        payload["user_company_id"] = resolved_company.id
        payload["assignment_company_ids"] = [resolved_company.id]
    return AccessControlService.check_permission(
        user=user,
        domain_slug=domain_slug,
        action_slug=action_slug,
        company=resolved_company,
        context=payload or None,
        log_decision=log_decision,
        resource_type=resource_type,
        resource_id=resource_id,
    )


def get_smart_system_permission_map(user, company=None):
    resolved_company = company or get_default_company_for_user(user)
    permission_map = {}
    for permission_key in SMART_SYSTEM_PERMISSION_KEYS:
        domain_slug, action_slug = permission_key.split(".", 1)
        permission_map[permission_key] = has_smart_system_permission(
            user,
            domain_slug,
            action_slug,
            company=resolved_company,
            log_decision=False,
        )
    return permission_map


def is_permissioned_item_allowed(item, permission_map):
    domain_slug = item.get("permission_domain")
    action_slug = item.get("permission_action")
    if not domain_slug or not action_slug:
        return True
    return permission_map.get(f"{domain_slug}.{action_slug}", False)


def filter_permissioned_items(items, permission_map):
    filtered = []
    for item in items:
        if not is_permissioned_item_allowed(item, permission_map):
            continue
        clean_item = {
            key: value
            for key, value in item.items()
            if key not in PERMISSION_METADATA_KEYS
        }
        if "children" in clean_item:
            clean_item["children"] = filter_permissioned_items(clean_item["children"], permission_map)
            if not clean_item["children"] and not clean_item.get("url_name"):
                continue
        if "items" in clean_item:
            clean_item["items"] = filter_permissioned_items(clean_item["items"], permission_map)
            if not clean_item["items"]:
                continue
        filtered.append(clean_item)
    return filtered
