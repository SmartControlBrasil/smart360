from rest_framework.routers import DefaultRouter

from .views import (
    AssetCategoryViewSet,
    AssetHistoryEventViewSet,
    AssetViewSet,
    ChecklistItemViewSet,
    ChecklistViewSet,
    ContractAssetViewSet,
    CustomerEquipmentViewSet,
    EquipmentModelPartViewSet,
    EquipmentModelViewSet,
    FailureEventViewSet,
    MaintenanceContractViewSet,
    MaintenanceClientViewSet,
    MaintenancePlanViewSet,
    OperationalSiteViewSet,
    RoutePlanViewSet,
    ScheduledVisitViewSet,
    ServiceSignatureViewSet,
    ServiceQuoteViewSet,
    ServiceDocumentViewSet,
    ServiceOrderChecklistResponseViewSet,
    ServiceOrderViewSet,
    TechnicianAvailabilityWindowViewSet,
    TechnicianScheduleViewSet,
    WorkLogViewSet,
)

router = DefaultRouter()
router.register("clients", MaintenanceClientViewSet, basename="smart-system-clients")
router.register("sites", OperationalSiteViewSet, basename="smart-system-sites")
router.register("asset-categories", AssetCategoryViewSet, basename="smart-system-asset-categories")
router.register("assets", AssetViewSet, basename="smart-system-assets")
router.register("equipment-models", EquipmentModelViewSet, basename="smart-system-equipment-models")
router.register("equipment-model-parts", EquipmentModelPartViewSet, basename="smart-system-equipment-model-parts")
router.register("customer-equipments", CustomerEquipmentViewSet, basename="smart-system-customer-equipments")
router.register("maintenance-contracts", MaintenanceContractViewSet, basename="smart-system-maintenance-contracts")
router.register("contract-assets", ContractAssetViewSet, basename="smart-system-contract-assets")
router.register("maintenance-plans", MaintenancePlanViewSet, basename="smart-system-maintenance-plans")
router.register("checklists", ChecklistViewSet, basename="smart-system-checklists")
router.register("checklist-items", ChecklistItemViewSet, basename="smart-system-checklist-items")
router.register("service-orders", ServiceOrderViewSet, basename="smart-system-service-orders")
router.register("service-order-checklist-responses", ServiceOrderChecklistResponseViewSet, basename="smart-system-so-checklist-responses")
router.register("failure-events", FailureEventViewSet, basename="smart-system-failure-events")
router.register("asset-history-events", AssetHistoryEventViewSet, basename="smart-system-asset-history-events")
router.register("work-logs", WorkLogViewSet, basename="smart-system-work-logs")
router.register("attachments", ServiceDocumentViewSet, basename="smart-system-attachments")
router.register("service-signatures", ServiceSignatureViewSet, basename="smart-system-service-signatures")
router.register("service-quotes", ServiceQuoteViewSet, basename="smart-system-service-quotes")
router.register("technician-availability", TechnicianAvailabilityWindowViewSet, basename="smart-system-technician-availability")
router.register("technician-schedules", TechnicianScheduleViewSet, basename="smart-system-technician-schedules")
router.register("route-plans", RoutePlanViewSet, basename="smart-system-route-plans")
router.register("scheduled-visits", ScheduledVisitViewSet, basename="smart-system-scheduled-visits")

urlpatterns = router.urls
