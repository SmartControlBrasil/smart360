from rest_framework.routers import DefaultRouter

from .views import GraphEdgeViewSet, GraphNodeViewSet, GraphProjectionRunViewSet

router = DefaultRouter()
router.register("nodes", GraphNodeViewSet, basename="knowledge-graph-node")
router.register("edges", GraphEdgeViewSet, basename="knowledge-graph-edge")
router.register("projection-runs", GraphProjectionRunViewSet, basename="knowledge-graph-projection-run")

urlpatterns = router.urls

