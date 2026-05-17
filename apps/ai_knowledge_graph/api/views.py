from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access_control_center.services.access_service import AccessControlService
from apps.ai_knowledge_graph.api.serializers import GraphEdgeSerializer, GraphNodeSerializer, GraphProjectionRunSerializer
from apps.ai_knowledge_graph.models import GraphEdge, GraphNode, GraphProjectionRun
from apps.ai_knowledge_graph.services.graph import GraphInsightService, GraphProjectionService, GraphQueryService
from apps.companies.models import Company, Membership
from apps.smart_system.models import OperationalSite


class KnowledgeGraphPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        company = None
        company_id = request.query_params.get("company") or request.data.get("company")
        if company_id:
            membership = Membership.objects.filter(user=request.user, company_id=company_id).select_related("company").first()
            company = membership.company if membership else None
        allowed, _ = AccessControlService.check_permission(
            user=request.user,
            domain_slug="ai_agents_admin",
            action_slug=getattr(view, "permission_action", "view"),
            company=company,
            module_name="ai_knowledge_graph",
            resource_type="ai_knowledge_graph_endpoint",
            resource_id=request.path,
            log_decision=False,
        )
        return allowed


class ScopedGraphMixin:
    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))

    def _apply_company_scope(self, queryset, field="company_id"):
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(Q(**{f"{field}__in": company_ids}) | Q(**{f"{field}__isnull": True}))

    def _resolve_company(self):
        company_id = self.request.query_params.get("company") or self.request.data.get("company")
        if company_id:
            membership = Membership.objects.filter(user=self.request.user, company_id=company_id).select_related("company").first()
            return membership.company if membership else None
        if getattr(self.request.user, "is_superuser", False):
            return Company.objects.order_by("id").first()
        membership = Membership.objects.filter(user=self.request.user, is_primary=True).select_related("company").first()
        if membership:
            return membership.company
        fallback = Membership.objects.filter(user=self.request.user).select_related("company").first()
        return fallback.company if fallback else None


class GraphNodeViewSet(ScopedGraphMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = GraphNodeSerializer
    permission_classes = [KnowledgeGraphPermission]
    lookup_field = "public_id"
    filterset_fields = ("node_type", "company", "site")
    search_fields = ("label", "source_type", "source_id")

    def get_queryset(self):
        return self._apply_company_scope(GraphNode.objects.select_related("company", "site"))

    @action(detail=True, methods=["get"])
    def neighbors(self, request, *args, **kwargs):
        node = self.get_object()
        hops = int(request.query_params.get("hops", "1"))
        edge_type = request.query_params.get("edge_type") or None
        payload = GraphQueryService.neighbors(company=node.company, node_public_id=node.public_id, edge_type=edge_type, hops=hops)
        return Response(
            [
                {
                    "edge_type": item["edge_type"],
                    "weight": item["weight"],
                    "node": GraphNodeSerializer(item["node"]).data,
                }
                for item in payload
            ]
        )

    @action(detail=True, methods=["get"])
    def insights(self, request, *args, **kwargs):
        node = self.get_object()
        payload = GraphInsightService.insights_for_entity(company=node.company, entity_type=node.node_type, entity_public_id=node.source_id)
        return Response(
            {
                "summary": payload.get("summary", ""),
                "top_relations": payload.get("top_relations", []),
                "clusters": payload.get("clusters", []),
                "context_count": payload.get("context_count", 0),
            }
        )

    @action(detail=False, methods=["get"], url_path="context")
    def context(self, request, *args, **kwargs):
        company = self._resolve_company()
        entity_type = request.query_params.get("entity_type", "")
        entity_public_id = request.query_params.get("entity_id", "")
        payload = GraphQueryService.entity_context(company=company, entity_type=entity_type, entity_public_id=entity_public_id)
        node = payload.get("node")
        if node is None:
            return Response({"detail": "Contexto nao encontrado."}, status=404)
        return Response(
            {
                "node": GraphNodeSerializer(node).data,
                "neighbors": [
                    {
                        "edge_type": item["edge_type"],
                        "weight": item["weight"],
                        "node": GraphNodeSerializer(item["node"]).data,
                    }
                    for item in payload["neighbors"]
                ],
                "by_relation": payload["by_relation"],
            }
        )

    @action(detail=False, methods=["get"], url_path="explanation-path")
    def explanation_path(self, request, *args, **kwargs):
        company = self._resolve_company()
        from_id = request.query_params.get("from_node")
        to_id = request.query_params.get("to_node")
        hops = int(request.query_params.get("max_hops", "3"))
        path = GraphQueryService.explanation_path(company=company, from_public_id=from_id, to_public_id=to_id, max_hops=hops)
        return Response(
            [
                {
                    "edge_type": item["edge_type"],
                    "weight": item["weight"],
                    "from": GraphNodeSerializer(item["from"]).data,
                    "to": GraphNodeSerializer(item["to"]).data,
                }
                for item in path
            ]
        )

    @action(detail=False, methods=["get"], url_path="subgraph")
    def subgraph(self, request, *args, **kwargs):
        company = self._resolve_company()
        entity_type = request.query_params.get("entity_type", "")
        entity_public_id = request.query_params.get("entity_id", "")
        context = GraphQueryService.entity_context(company=company, entity_type=entity_type, entity_public_id=entity_public_id)
        node = context.get("node")
        if node is None:
            return Response({"detail": "Subgrafo nao encontrado."}, status=404)
        node_ids = {node.id}
        for item in context["neighbors"]:
            node_ids.add(item["node"].id)
        edges = GraphEdge.objects.select_related("from_node", "to_node").filter(company=company).filter(Q(from_node_id__in=node_ids) | Q(to_node_id__in=node_ids))[:40]
        return Response(
            {
                "center": GraphNodeSerializer(node).data,
                "nodes": GraphNodeSerializer(GraphNode.objects.filter(id__in=node_ids), many=True).data,
                "edges": GraphEdgeSerializer(edges, many=True).data,
            }
        )


class GraphEdgeViewSet(ScopedGraphMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = GraphEdgeSerializer
    permission_classes = [KnowledgeGraphPermission]
    lookup_field = "public_id"
    filterset_fields = ("edge_type", "company", "site")

    def get_queryset(self):
        return self._apply_company_scope(GraphEdge.objects.select_related("company", "site", "from_node", "to_node"))


class GraphProjectionRunViewSet(ScopedGraphMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = GraphProjectionRunSerializer
    permission_classes = [KnowledgeGraphPermission]
    lookup_field = "public_id"

    def get_queryset(self):
        return self._apply_company_scope(GraphProjectionRun.objects.select_related("company", "site"))

    @action(detail=False, methods=["post"])
    def rebuild(self, request, *args, **kwargs):
        company = self._resolve_company()
        if company is None:
            return Response({"detail": "Empresa nao encontrada no escopo."}, status=status.HTTP_400_BAD_REQUEST)
        site = None
        site_id = request.data.get("site")
        if site_id:
            site = OperationalSite.objects.filter(maintenance_client__company=company, public_id=site_id).first()
        run = GraphProjectionService.project_company_graph(company=company, site=site, projection_type=GraphProjectionRun.ProjectionType.TARGETED)
        return Response(GraphProjectionRunSerializer(run).data, status=status.HTTP_201_CREATED)
