from django.db.models import Q

from apps.ai_knowledge_graph.models import GraphNode, GraphProjectionRun
from apps.ai_knowledge_graph.services.graph import GraphInsightService, GraphQueryService


def get_ai_knowledge_graph_context(*, tenant_context, node_public_id=None):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    nodes = GraphNode.objects.select_related("company", "site").filter(company=company) if company is not None else GraphNode.objects.none()
    if site is not None:
        nodes = nodes.filter(Q(site=site) | Q(site__isnull=True))
    nodes = nodes.order_by("node_type", "label")
    selected_node = nodes.filter(public_id=node_public_id).first() if node_public_id else nodes.first()
    insights = {}
    neighbors = []
    if selected_node is not None:
        insights = GraphInsightService.insights_for_entity(company=selected_node.company, entity_type=selected_node.node_type, entity_public_id=selected_node.source_id)
        neighbors = GraphQueryService.neighbors(company=selected_node.company, node_public_id=selected_node.public_id, hops=2)
    runs = GraphProjectionRun.objects.filter(company=company).order_by("-created_at")[:12] if company is not None else []
    return {
        "company": company,
        "site": site,
        "graph_nodes": list(nodes[:40]),
        "selected_graph_node": selected_node,
        "selected_graph_neighbors": neighbors[:20],
        "selected_graph_insights": insights,
        "graph_projection_runs": list(runs),
    }
