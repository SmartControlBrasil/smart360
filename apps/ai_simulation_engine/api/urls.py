from rest_framework.routers import DefaultRouter

from apps.ai_simulation_engine.api.views import SimulationRunViewSet, SimulationScenarioViewSet, SimulationTypeViewSet

router = DefaultRouter()
router.register("types", SimulationTypeViewSet, basename="ai-simulation-type")
router.register("scenarios", SimulationScenarioViewSet, basename="ai-simulation-scenario")
router.register("runs", SimulationRunViewSet, basename="ai-simulation-run")

urlpatterns = router.urls

