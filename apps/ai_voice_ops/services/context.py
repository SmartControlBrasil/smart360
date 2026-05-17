from __future__ import annotations

from apps.ai_agents_center.services.client_portal_copilot import ClientPortalCopilotService
from apps.ai_agents_center.services.manager_copilot import ManagerCopilotService
from apps.ai_agents_center.services.technician_copilot import TechnicianCopilotService
from apps.ai_digital_twin.services.orchestrator import DigitalTwinOrchestrator
from apps.ai_knowledge_graph.services.graph import GraphInsightService
from apps.ai_voice_ops.services.intents import ParsedIntent
from apps.companies.services.tenant_scope import TenantScopeService
from apps.smart_system.models import Asset, OperationalSite, Part, ServiceOrder
from apps.smart_system.services.tenant_scope import SmartSystemScopeService
from apps.admin_shell.services.technician_mobile import get_technician_service_detail_context, get_technician_copilot_bootstrap


class VoiceContextResolver:
    @classmethod
    def resolve_tenant_context(cls, *, request, company_id=None, site_id=None) -> dict:
        scope = TenantScopeService.resolve_context(request)
        company = scope.company
        site = scope.site
        try:
            company_id = int(company_id) if company_id is not None else None
        except (TypeError, ValueError):
            company_id = None
        try:
            site_id = int(site_id) if site_id is not None else None
        except (TypeError, ValueError):
            site_id = None
        if company_id:
            company = next((item for item in scope.available_companies if item.id == company_id), company)
        if site_id:
            site = next((item for item in scope.available_sites if item.id == site_id), site)
        return {
            "company": company,
            "site": site,
            "company_options": scope.available_companies,
            "site_options": scope.available_sites,
        }

    @classmethod
    def resolve(cls, *, request, persona: str, parsed_intent: ParsedIntent, context_seed: dict | None = None, tenant_context: dict | None = None) -> dict:
        context_seed = context_seed or {}
        tenant_context = tenant_context or cls.resolve_tenant_context(request=request)
        if persona == "technician":
            return cls._resolve_technician_context(
                request=request,
                parsed_intent=parsed_intent,
                context_seed=context_seed,
                tenant_context=tenant_context,
            )
        if persona == "manager":
            return cls._resolve_manager_context(
                request=request,
                parsed_intent=parsed_intent,
                context_seed=context_seed,
                tenant_context=tenant_context,
            )
        return cls._resolve_client_context(
            request=request,
            parsed_intent=parsed_intent,
            context_seed=context_seed,
            tenant_context=tenant_context,
        )

    @classmethod
    def _resolve_technician_context(cls, *, request, parsed_intent: ParsedIntent, context_seed: dict, tenant_context: dict) -> dict:
        company = tenant_context.get("company")
        site = tenant_context.get("site")
        order_code = (
            context_seed.get("order_code")
            or parsed_intent.entities.get("order_code")
            or ""
        )
        service_payload = None
        if order_code:
            service_payload = get_technician_service_detail_context(request.user, tenant_context, order_code)
        if service_payload is None and parsed_intent.entities.get("asset_code"):
            asset = SmartSystemScopeService.scope_queryset(
                Asset.objects.select_related("operational_site", "category"),
                request,
            ).filter(asset_tag__iexact=parsed_intent.entities["asset_code"]).first()
            if asset:
                order = SmartSystemScopeService.scope_queryset(
                    ServiceOrder.objects.select_related("asset", "operational_site", "client"),
                    request,
                ).filter(asset=asset).order_by("-opened_at").first()
                if order:
                    order_code = order.order_number
                    service_payload = get_technician_service_detail_context(request.user, tenant_context, order_code)
        bootstrap = get_technician_copilot_bootstrap(service_payload) if service_payload else {"context": {}, "suggestions": []}
        asset_public_id = ""
        if service_payload and service_payload["service"].get("asset_code"):
            asset = SmartSystemScopeService.scope_queryset(Asset.objects, request).filter(
                asset_tag__iexact=service_payload["service"]["asset_code"]
            ).first()
            asset_public_id = str(asset.public_id) if asset else ""
        twin = None
        if asset_public_id and company:
            asset = SmartSystemScopeService.scope_queryset(
                Asset.objects.select_related("operational_site", "operational_site__maintenance_client"),
                request,
            ).filter(public_id=asset_public_id).first()
            if asset:
                twin = DigitalTwinOrchestrator.project_for_asset(asset=asset, snapshot=True)
        graph = GraphInsightService.insights_for_entity(company=company, entity_type="asset", entity_public_id=asset_public_id) if asset_public_id and company else {}
        return {
            "tenant_context": {
                "company_id": getattr(company, "id", None),
                "company_name": getattr(company, "name", ""),
                "site_id": getattr(site, "id", None),
                "site_name": getattr(site, "name", ""),
            },
            "asset_public_id": asset_public_id,
            "order_code": order_code,
            "service_payload": service_payload or {},
            "technician_copilot_bootstrap": bootstrap,
            "digital_twin": {
                "public_id": str(twin.public_id),
                "risk_level": twin.risk_level,
                "summary": twin.current_state_summary,
            } if twin else {},
            "graph_insight": graph,
        }

    @classmethod
    def _resolve_manager_context(cls, *, request, parsed_intent: ParsedIntent, context_seed: dict, tenant_context: dict) -> dict:
        payload = ManagerCopilotService.get_current_context_payload(
            user=request.user,
            tenant_context=tenant_context,
            context_seed=context_seed,
        )
        return {
            "tenant_context": {
                "company_id": getattr(tenant_context.get("company"), "id", None),
                "company_name": getattr(tenant_context.get("company"), "name", ""),
                "site_id": getattr(tenant_context.get("site"), "id", None),
                "site_name": getattr(tenant_context.get("site"), "name", ""),
            },
            "manager_copilot": {
                "session_public_id": str(payload["session"].public_id),
                "context": payload["context"],
                "suggestions": payload["suggestions"],
            },
        }

    @classmethod
    def _resolve_client_context(cls, *, request, parsed_intent: ParsedIntent, context_seed: dict, tenant_context: dict) -> dict:
        permission_map = getattr(request, "permission_map", None) or {}
        payload = ClientPortalCopilotService.get_current_context_payload(
            request=request,
            tenant_context=tenant_context,
            permission_map=permission_map,
            context_seed=context_seed,
        )
        return {
            "tenant_context": {
                "company_id": getattr(tenant_context.get("company"), "id", None),
                "company_name": getattr(tenant_context.get("company"), "name", ""),
                "site_id": getattr(tenant_context.get("site"), "id", None),
                "site_name": getattr(tenant_context.get("site"), "name", ""),
            },
            "permission_map": permission_map,
            "client_copilot": {
                "session_public_id": str(payload["session"].public_id),
                "context": payload["context"],
                "suggestions": payload["suggestions"],
            },
        }

    @classmethod
    def resolve_part(cls, *, request, company, entity_payload: dict):
        part_code = entity_payload.get("part_code") or ""
        if not part_code or not company:
            return None
        queryset = SmartSystemScopeService.scope_queryset(Part.objects.select_related("company", "operational_site"), request)
        return queryset.filter(company=company, code__iexact=part_code).first()

    @classmethod
    def resolve_order(cls, *, request, entity_payload: dict):
        order_code = entity_payload.get("order_code") or ""
        if not order_code:
            return None
        queryset = SmartSystemScopeService.scope_queryset(
            ServiceOrder.objects.select_related("client__company", "operational_site", "asset", "assigned_to"),
            request,
        )
        return queryset.filter(order_number__iexact=order_code).first()

    @classmethod
    def resolve_site(cls, *, request, company, site_code: str):
        if not site_code:
            return None
        queryset = SmartSystemScopeService.scope_queryset(
            OperationalSite.objects.select_related("maintenance_client", "maintenance_client__company"),
            request,
        )
        if company is not None:
            queryset = queryset.filter(maintenance_client__company=company)
        return queryset.filter(code__iexact=site_code).first()
