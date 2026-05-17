from apps.ai_digital_twin.models import DigitalTwin
from apps.ai_digital_twin.services.orchestrator import DigitalTwinOrchestrator
from apps.ai_knowledge_graph.services.graph import GraphInsightService, GraphQueryService


def get_ai_digital_twin_context(*, tenant_context, twin_public_id=None):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    queryset = DigitalTwin.objects.select_related(
        "company",
        "site",
        "asset",
        "asset__category",
        "contract",
    ).prefetch_related("signals", "snapshots", "projections").order_by("-last_projected_at", "-updated_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    if site is not None:
        queryset = queryset.filter(site=site)
    selected_twin = queryset.filter(public_id=twin_public_id).first() if twin_public_id else queryset.first()
    if selected_twin is not None:
        DigitalTwinOrchestrator.view(digital_twin=selected_twin)
    graph_context = {}
    if selected_twin is not None and selected_twin.asset_id:
        graph_context = GraphInsightService.insights_for_entity(
            company=selected_twin.company,
            entity_type="asset",
            entity_public_id=selected_twin.asset.public_id,
        )
    elif selected_twin is not None and selected_twin.site_id:
        graph_context = GraphInsightService.insights_for_entity(
            company=selected_twin.company,
            entity_type="site",
            entity_public_id=selected_twin.site.public_id,
        )
    high_attention = queryset.filter(risk_level__in=["high", "critical"])[:8]
    return {
        "company": company,
        "site": site,
        "digital_twins": list(queryset[:30]),
        "selected_twin": selected_twin,
        "selected_twin_signals": list(selected_twin.signals.filter(is_active=True).order_by("-occurred_at")[:12]) if selected_twin else [],
        "selected_twin_snapshots": list(selected_twin.snapshots.order_by("-snapshot_time")[:12]) if selected_twin else [],
        "selected_twin_projections": list(selected_twin.projections.order_by("projection_type")) if selected_twin else [],
        "selected_twin_graph_context": graph_context,
        "digital_twin_high_attention": list(high_attention),
    }
