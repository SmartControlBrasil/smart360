from rest_framework.routers import DefaultRouter

from .views import DigitalTwinSignalViewSet, DigitalTwinSnapshotViewSet, DigitalTwinViewSet

router = DefaultRouter()
router.register("twins", DigitalTwinViewSet, basename="digital-twin")
router.register("signals", DigitalTwinSignalViewSet, basename="digital-twin-signal")
router.register("snapshots", DigitalTwinSnapshotViewSet, basename="digital-twin-snapshot")

urlpatterns = router.urls

