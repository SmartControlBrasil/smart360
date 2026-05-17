from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.billing.services.billing_service import BillingAccessService
from apps.ai_agents_center.models import AgentRun
from apps.ai_agents_center.services.anomaly_triggers import AnomalyAgentTriggerService
from apps.ai_agents_center.services.scheduling_triggers import SchedulingAgentTriggerService
from apps.ai_agents_center.services.profitability_triggers import ProfitabilityAgentTriggerService
from apps.observability_center.services.observability_service import SystemEventService
from ..models import (
    Asset,
    AssetCategory,
    AssetHistoryEvent,
    Checklist,
    ChecklistItem,
    ContractAsset,
    CustomerEquipment,
    EquipmentModel,
    EquipmentModelPart,
    FailureEvent,
    MaintenanceContract,
    MaintenanceClient,
    MaintenancePlan,
    OperationalSite,
    ServiceQuote,
    RoutePlan,
    ScheduledVisit,
    ServiceSignature,
    ServiceDocument,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    TechnicianAvailabilityWindow,
    TechnicianSchedule,
    WorkLog,
)
from ..services.scheduling_service import TechnicianRoutingService
from ..services.maintenance_contract_service import MaintenanceContractService
from apps.ai_agents_center.services.maintenance_triggers import MaintenanceAgentTriggerService
from ..services.quote_service import ServiceQuoteService
from ..services.tenant_scope import SmartSystemScopeService
from .serializers import (
    AssetCategorySerializer,
    AssetHistoryEventSerializer,
    AssetSerializer,
    ChecklistItemSerializer,
    ChecklistSerializer,
    ContractAssetSerializer,
    CustomerEquipmentSerializer,
    EquipmentModelPartSerializer,
    EquipmentModelSerializer,
    FailureEventSerializer,
    MaintenanceContractSerializer,
    MaintenanceClientSerializer,
    MaintenancePlanSerializer,
    OperationalSiteSerializer,
    ServiceQuoteSerializer,
    RoutePlanSerializer,
    ScheduledVisitSerializer,
    ServiceSignatureSerializer,
    ServiceDocumentSerializer,
    ServiceOrderChecklistResponseSerializer,
    ServiceOrderSerializer,
    TechnicianAvailabilityWindowSerializer,
    TechnicianScheduleSerializer,
    WorkLogSerializer,
)

User = get_user_model()


class SmartSystemBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    event_module = ""

    def get_queryset(self):
        return SmartSystemScopeService.scope_queryset(super().get_queryset(), self.request)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        company = SmartSystemScopeService.resolve_scope(request).company
        access = BillingAccessService.get_company_billing_context(company)
        if company is not None and not access["access_allowed"] and not request.user.is_superuser:
            raise PermissionDenied(
                detail=f"Tenant {company.name} bloqueado por status financeiro {access['access_status']}."
            )

    def _resource_identifier(self, instance):
        for field_name in ("order_number", "asset_tag", "name", "code", "id"):
            value = getattr(instance, field_name, "")
            if value:
                return str(value)
        return str(instance.pk)

    def _log_event(self, action, instance):
        if not self.event_module:
            return
        scope = SmartSystemScopeService.resolve_scope(self.request)
        SystemEventService.log_system_event(
            event_type=f"{self.event_module}.{action}",
            source_module="smart_system",
            message=f"{self.event_module} {action} via API.",
            entity_type=self.event_module,
            entity_id=self._resource_identifier(instance),
            user=self.request.user,
            company=scope.company,
            site=scope.site,
            payload={"path": self.request.path, "method": self.request.method},
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        self._log_event("created", instance)
        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        self._log_event("updated", instance)
        return instance

    def perform_destroy(self, instance):
        self._log_event("deleted", instance)
        instance.delete()


class MaintenanceClientViewSet(SmartSystemBaseViewSet):
    event_module = "clients"
    queryset = MaintenanceClient.objects.select_related("company").all()
    serializer_class = MaintenanceClientSerializer
    filterset_fields = ("company", "is_active")
    search_fields = ("display_name", "legal_name", "document_number", "contact_name", "contact_email")
    ordering_fields = ("display_name", "updated_at")


class OperationalSiteViewSet(SmartSystemBaseViewSet):
    event_module = "sites"
    queryset = OperationalSite.objects.select_related("maintenance_client").all()
    serializer_class = OperationalSiteSerializer
    filterset_fields = ("maintenance_client", "city", "state", "is_active")
    search_fields = ("name", "code", "city", "state", "contact_name")
    ordering_fields = ("name", "updated_at")


class AssetCategoryViewSet(SmartSystemBaseViewSet):
    event_module = "asset_categories"
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at")


class AssetViewSet(SmartSystemBaseViewSet):
    event_module = "assets"
    queryset = Asset.objects.select_related("operational_site", "category").all()
    serializer_class = AssetSerializer
    filterset_fields = ("operational_site", "category", "status", "criticality", "is_active")
    search_fields = ("asset_tag", "name", "serial_number", "manufacturer", "model")
    ordering_fields = ("asset_tag", "name", "updated_at")

    def perform_update(self, serializer):
        previous_criticality = serializer.instance.criticality
        instance = super().perform_update(serializer)
        if previous_criticality != instance.criticality and instance.criticality == Asset.Criticality.CRITICAL:
            try:
                MaintenanceAgentTriggerService.run_asset_analysis(
                    asset=instance,
                    user=None,
                    trigger_type=AgentRun.TriggerType.EVENT,
                )
            except Exception:
                pass
        try:
            AnomalyAgentTriggerService.run_asset_analysis(asset=instance, user=self.request.user, trigger_type=AgentRun.TriggerType.EVENT)
        except Exception:
            pass
        return instance


class EquipmentModelViewSet(SmartSystemBaseViewSet):
    event_module = "equipment_models"
    queryset = EquipmentModel.objects.select_related("company", "category").prefetch_related("parts", "parts__part").all()
    serializer_class = EquipmentModelSerializer
    filterset_fields = ("company", "category", "status", "is_pmoc_applicable")
    search_fields = ("name", "manufacturer", "manufacturer_code", "equipment_type")
    ordering_fields = ("name", "updated_at")


class EquipmentModelPartViewSet(SmartSystemBaseViewSet):
    event_module = "equipment_model_parts"
    queryset = EquipmentModelPart.objects.select_related("company", "equipment_model", "part").all()
    serializer_class = EquipmentModelPartSerializer
    filterset_fields = ("company", "equipment_model", "part")
    search_fields = ("equipment_model__name", "part__name", "part__code")
    ordering_fields = ("updated_at",)


class CustomerEquipmentViewSet(SmartSystemBaseViewSet):
    event_module = "customer_equipments"
    queryset = CustomerEquipment.objects.select_related("company", "site", "equipment_model", "equipment_model__category").all()
    serializer_class = CustomerEquipmentSerializer
    filterset_fields = ("company", "site", "equipment_model", "status", "preventive_group", "is_pmoc_applicable")
    search_fields = ("customer_tag", "display_name", "internal_code", "serial_number", "location")
    ordering_fields = ("customer_tag", "display_name", "updated_at")


class MaintenancePlanViewSet(SmartSystemBaseViewSet):
    event_module = "preventive"
    queryset = MaintenancePlan.objects.select_related("asset", "category", "checklist").all()
    serializer_class = MaintenancePlanSerializer
    filterset_fields = ("asset", "category", "frequency_type", "is_active", "checklist")
    search_fields = ("name", "description", "notes")
    ordering_fields = ("name", "next_due_date", "updated_at")


class MaintenanceContractViewSet(SmartSystemBaseViewSet):
    event_module = "contracts"
    queryset = MaintenanceContract.objects.select_related(
        "company",
        "client",
        "operational_site",
    ).prefetch_related("covered_assets", "covered_assets__asset").all()
    serializer_class = MaintenanceContractSerializer
    filterset_fields = ("company", "client", "operational_site", "status", "billing_frequency", "auto_generate_preventives")
    search_fields = ("contract_number", "client__display_name", "notes")
    ordering_fields = ("created_at", "start_date", "end_date", "contract_value", "updated_at")

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        contract = MaintenanceContractService.activate_contract(contract=self.get_object(), user=request.user)
        try:
            ProfitabilityAgentTriggerService.run_contract_analysis(contract=contract, user=request.user, trigger_type=AgentRun.TriggerType.EVENT)
        except Exception:
            pass
        try:
            AnomalyAgentTriggerService.run_contract_analysis(contract=contract, user=request.user, trigger_type=AgentRun.TriggerType.EVENT)
        except Exception:
            pass
        return Response(self.get_serializer(contract).data)

    @action(detail=True, methods=["post"], url_path="suspend")
    def suspend(self, request, pk=None):
        contract = MaintenanceContractService.suspend_contract(
            contract=self.get_object(),
            user=request.user,
            reason=request.data.get("reason", ""),
        )
        try:
            ProfitabilityAgentTriggerService.run_contract_analysis(contract=contract, user=request.user, trigger_type=AgentRun.TriggerType.EVENT)
        except Exception:
            pass
        try:
            AnomalyAgentTriggerService.run_contract_analysis(contract=contract, user=request.user, trigger_type=AgentRun.TriggerType.EVENT)
        except Exception:
            pass
        return Response(self.get_serializer(contract).data)

    @action(detail=True, methods=["post"], url_path="expire")
    def expire(self, request, pk=None):
        contract = MaintenanceContractService.expire_contract(
            contract=self.get_object(),
            user=request.user,
            reason=request.data.get("reason", ""),
        )
        return Response(self.get_serializer(contract).data)

    @action(detail=True, methods=["post"], url_path="generate-preventives")
    def generate_preventives(self, request, pk=None):
        result = MaintenanceContractService.generate_due_preventives(
            contract=self.get_object(),
            generated_by=request.user,
        )
        return Response(
            {
                "contract": self.get_serializer(result.contract).data,
                "generated_orders": ServiceOrderSerializer(result.generated_orders, many=True, context=self.get_serializer_context()).data,
                "skipped_assets": ContractAssetSerializer(result.skipped_assets, many=True, context=self.get_serializer_context()).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="generate-billing")
    def generate_billing(self, request, pk=None):
        invoice = MaintenanceContractService.generate_billing_cycle(
            contract=self.get_object(),
            generated_by=request.user,
        )
        if invoice:
            try:
                ProfitabilityAgentTriggerService.run_contract_analysis(contract=self.get_object(), user=request.user, trigger_type=AgentRun.TriggerType.EVENT)
            except Exception:
                pass
        return Response(
            {
                "invoice_number": getattr(invoice, "invoice_number", ""),
                "status": getattr(invoice, "status", ""),
                "generated": bool(invoice),
            }
        )

    @action(detail=True, methods=["get"], url_path="assets")
    def assets(self, request, pk=None):
        contract = self.get_object()
        serializer = ContractAssetSerializer(
            contract.covered_assets.select_related("asset").all(),
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="preventives")
    def preventives(self, request, pk=None):
        contract = self.get_object()
        queryset = ServiceOrder.objects.filter(
            maintenance_contract=contract,
            maintenance_type=ServiceOrder.MaintenanceType.PREVENTIVE,
        ).select_related("asset", "operational_site")
        serializer = ServiceOrderSerializer(queryset.order_by("-opened_at"), many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class ContractAssetViewSet(SmartSystemBaseViewSet):
    event_module = "contracts"
    queryset = ContractAsset.objects.select_related(
        "contract",
        "contract__company",
        "contract__client",
        "contract__operational_site",
        "asset",
    ).all()
    serializer_class = ContractAssetSerializer
    filterset_fields = ("contract", "asset", "maintenance_frequency", "is_active")
    search_fields = ("contract__contract_number", "asset__asset_tag", "asset__name", "notes")
    ordering_fields = ("next_execution", "last_execution", "updated_at")


class ChecklistViewSet(SmartSystemBaseViewSet):
    event_module = "checklists"
    queryset = Checklist.objects.prefetch_related("items").all()
    serializer_class = ChecklistSerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "description")
    ordering_fields = ("name", "updated_at")


class ChecklistItemViewSet(SmartSystemBaseViewSet):
    event_module = "checklists"
    queryset = ChecklistItem.objects.select_related("checklist").all()
    serializer_class = ChecklistItemSerializer
    filterset_fields = ("checklist", "item_type", "is_required", "is_active")
    search_fields = ("title", "description", "checklist__name")
    ordering_fields = ("ordering", "updated_at")


class ServiceOrderViewSet(SmartSystemBaseViewSet):
    event_module = "work_orders"
    queryset = ServiceOrder.objects.select_related(
        "client",
        "operational_site",
        "asset",
        "maintenance_plan",
        "assigned_to",
        "created_by",
    ).all()
    serializer_class = ServiceOrderSerializer
    filterset_fields = ("client", "operational_site", "asset", "maintenance_type", "priority", "status", "source", "assigned_to")
    search_fields = ("order_number", "title", "description", "requested_by")
    ordering_fields = ("opened_at", "scheduled_start", "completed_at", "updated_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service_order = self.perform_create(serializer)
        try:
            ProfitabilityAgentTriggerService.trigger_for_service_order(service_order=service_order, user=request.user)
        except Exception:
            pass
        try:
            AnomalyAgentTriggerService.trigger_for_service_order(service_order=service_order, user=request.user)
        except Exception:
            pass
        output = ServiceOrderSerializer(service_order, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        service_order = self.perform_update(serializer)
        try:
            ProfitabilityAgentTriggerService.trigger_for_service_order(service_order=service_order, user=request.user)
        except Exception:
            pass
        try:
            AnomalyAgentTriggerService.trigger_for_service_order(service_order=service_order, user=request.user)
        except Exception:
            pass
        output = ServiceOrderSerializer(service_order, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)


class ServiceOrderChecklistResponseViewSet(SmartSystemBaseViewSet):
    event_module = "checklists"
    queryset = ServiceOrderChecklistResponse.objects.select_related("service_order", "checklist_item").all()
    serializer_class = ServiceOrderChecklistResponseSerializer
    filterset_fields = ("service_order", "checklist_item")
    search_fields = ("service_order__order_number", "checklist_item__title", "response_text", "response_choice")
    ordering_fields = ("created_at", "updated_at")

    def perform_create(self, serializer):
        instance = super().perform_create(serializer)
        if instance and (
            instance.response_boolean is False
            or (instance.response_text or "").strip().upper() == "NOK"
            or (instance.response_choice or "").strip().upper() == "NOK"
        ):
            try:
                MaintenanceAgentTriggerService.trigger_for_service_order(service_order=instance.service_order, user=self.request.user)
            except Exception:
                pass
        return instance


class FailureEventViewSet(SmartSystemBaseViewSet):
    event_module = "failures"
    queryset = FailureEvent.objects.select_related("asset", "service_order").all()
    serializer_class = FailureEventSerializer
    filterset_fields = ("asset", "service_order", "severity", "status")
    search_fields = ("symptom", "probable_cause", "root_cause", "asset__asset_tag")
    ordering_fields = ("detected_at", "downtime_minutes", "updated_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failure_event = self.perform_create(serializer)
        try:
            AnomalyAgentTriggerService.trigger_for_failure(failure_event=failure_event, user=request.user)
        except Exception:
            pass
        output = FailureEventSerializer(failure_event, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class AssetHistoryEventViewSet(SmartSystemBaseViewSet):
    event_module = "assets"
    queryset = AssetHistoryEvent.objects.select_related("asset", "related_service_order", "related_failure_event", "created_by").all()
    serializer_class = AssetHistoryEventSerializer
    filterset_fields = ("asset", "event_type", "created_by")
    search_fields = ("asset__asset_tag", "title", "description")
    ordering_fields = ("occurred_at", "updated_at")


class WorkLogViewSet(SmartSystemBaseViewSet):
    event_module = "execution"
    queryset = WorkLog.objects.select_related("service_order", "user").all()
    serializer_class = WorkLogSerializer
    filterset_fields = ("service_order", "user")
    search_fields = ("service_order__order_number", "user__email", "notes")
    ordering_fields = ("started_at", "ended_at", "labor_minutes", "updated_at")

    def perform_create(self, serializer):
        instance = super().perform_create(serializer)
        try:
            ProfitabilityAgentTriggerService.trigger_for_service_order(service_order=instance.service_order, user=self.request.user)
        except Exception:
            pass
        try:
            AnomalyAgentTriggerService.trigger_for_service_order(service_order=instance.service_order, user=self.request.user)
        except Exception:
            pass
        return instance

    def perform_update(self, serializer):
        instance = super().perform_update(serializer)
        try:
            ProfitabilityAgentTriggerService.trigger_for_service_order(service_order=instance.service_order, user=self.request.user)
        except Exception:
            pass
        try:
            AnomalyAgentTriggerService.trigger_for_service_order(service_order=instance.service_order, user=self.request.user)
        except Exception:
            pass
        return instance


class ServiceDocumentViewSet(SmartSystemBaseViewSet):
    event_module = "reports"
    queryset = ServiceDocument.objects.select_related("service_order", "uploaded_by").all()
    serializer_class = ServiceDocumentSerializer
    filterset_fields = ("service_order", "document_type", "uploaded_by")
    search_fields = ("service_order__order_number", "title", "uploaded_by__email")
    ordering_fields = ("created_at", "updated_at")


class ServiceSignatureViewSet(SmartSystemBaseViewSet):
    event_module = "signatures"
    http_method_names = ["get", "head", "options"]
    queryset = ServiceSignature.objects.select_related("company", "operational_site", "service_order", "signer_user").all()
    serializer_class = ServiceSignatureSerializer
    filterset_fields = ("service_order", "signature_type", "signer_role", "company", "operational_site", "is_current")
    search_fields = ("signer_name", "signer_document", "service_order__order_number", "report_reference_code")
    ordering_fields = ("signed_at", "created_at", "updated_at")


class ServiceQuoteViewSet(SmartSystemBaseViewSet):
    event_module = "quotes"
    queryset = ServiceQuote.objects.select_related(
        "company",
        "operational_site",
        "work_order",
        "asset",
        "approved_by_user",
        "created_by",
        "updated_by",
    ).prefetch_related("items").all()
    serializer_class = ServiceQuoteSerializer
    filterset_fields = ("company", "operational_site", "work_order", "asset", "status")
    search_fields = ("quote_number", "work_order__order_number", "notes", "approved_by_name")
    ordering_fields = ("created_at", "sent_at", "approved_at", "total_value", "updated_at")

    @action(detail=True, methods=["post"], url_path="send")
    def send_quote(self, request, pk=None):
        quote = ServiceQuoteService.send_quote(quote=self.get_object(), user=request.user)
        return Response(self.get_serializer(quote).data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_quote(self, request, pk=None):
        quote = ServiceQuoteService.approve_quote(
            quote=self.get_object(),
            approver_name=request.data.get("approved_by_name") or request.user.display_name or request.user.email,
            approver_user=request.user,
            notes=request.data.get("approval_notes", ""),
        )
        try:
            ProfitabilityAgentTriggerService.trigger_for_service_order(service_order=quote.work_order, user=request.user)
        except Exception:
            pass
        return Response(self.get_serializer(quote).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_quote(self, request, pk=None):
        quote = ServiceQuoteService.reject_quote(
            quote=self.get_object(),
            approver_name=request.data.get("approved_by_name") or request.user.display_name or request.user.email,
            approver_user=request.user,
            reason=request.data.get("rejection_reason", ""),
        )
        return Response(self.get_serializer(quote).data)


class TechnicianAvailabilityWindowViewSet(SmartSystemBaseViewSet):
    event_module = "schedule"
    queryset = TechnicianAvailabilityWindow.objects.select_related(
        "company",
        "operational_site",
        "technician",
        "technician_profile",
    ).all()
    serializer_class = TechnicianAvailabilityWindowSerializer
    filterset_fields = ("company", "operational_site", "technician", "weekday", "blocked_date", "is_available")
    search_fields = ("technician__email", "technician__first_name", "technician__last_name", "notes")
    ordering_fields = ("blocked_date", "weekday", "updated_at")

    def perform_create(self, serializer):
        instance = super().perform_create(serializer)
        target_date = instance.blocked_date or timezone.localdate()
        try:
            SchedulingAgentTriggerService.run_technician_analysis(
                company=instance.company,
                technician=instance.technician,
                target_date=target_date,
                site=instance.operational_site,
                trigger_type=AgentRun.TriggerType.EVENT,
            )
        except Exception:
            pass
        return instance

    def perform_update(self, serializer):
        instance = super().perform_update(serializer)
        target_date = instance.blocked_date or timezone.localdate()
        try:
            SchedulingAgentTriggerService.run_technician_analysis(
                company=instance.company,
                technician=instance.technician,
                target_date=target_date,
                site=instance.operational_site,
                trigger_type=AgentRun.TriggerType.EVENT,
            )
        except Exception:
            pass
        return instance


class TechnicianScheduleViewSet(SmartSystemBaseViewSet):
    event_module = "schedule"
    http_method_names = ["get", "head", "options"]
    queryset = TechnicianSchedule.objects.select_related(
        "company",
        "operational_site",
        "technician",
        "technician_profile",
    ).all()
    serializer_class = TechnicianScheduleSerializer
    filterset_fields = ("company", "operational_site", "technician", "date")
    search_fields = ("technician__email", "technician__first_name", "technician__last_name", "notes")
    ordering_fields = ("date", "total_jobs", "total_conflicts", "updated_at")


class RoutePlanViewSet(SmartSystemBaseViewSet):
    event_module = "schedule"
    http_method_names = ["get", "post", "head", "options"]
    queryset = RoutePlan.objects.select_related(
        "company",
        "operational_site",
        "technician",
        "technician_profile",
    ).all()
    serializer_class = RoutePlanSerializer
    filterset_fields = ("company", "operational_site", "technician", "date", "optimization_status")
    search_fields = ("technician__email", "technician__first_name", "technician__last_name", "notes")
    ordering_fields = ("date", "total_stops", "updated_at")

    def create(self, request, *args, **kwargs):
        technician_id = request.data.get("technician")
        visit_date = request.data.get("date")
        if not technician_id or not visit_date:
            return Response({"detail": "technician e date sao obrigatorios."}, status=status.HTTP_400_BAD_REQUEST)
        technician = User.objects.filter(pk=technician_id).first()
        if technician is None:
            return Response({"detail": "Tecnico nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        scope = SmartSystemScopeService.resolve_scope(request)
        if scope.company is None and not request.user.is_superuser:
            raise PermissionDenied(detail="Selecione uma empresa ativa para gerar rotas.")
        route_plan = TechnicianRoutingService.generate_route_for_technician(
            technician=technician,
            schedule_date=timezone.datetime.fromisoformat(visit_date).date() if "T" in visit_date else timezone.datetime.strptime(visit_date, "%Y-%m-%d").date(),
            company=scope.company,
            site=scope.site,
            generated_by=request.user,
        )
        serializer = self.get_serializer(route_plan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ScheduledVisitViewSet(SmartSystemBaseViewSet):
    event_module = "schedule"
    queryset = ScheduledVisit.objects.select_related(
        "company",
        "operational_site",
        "asset",
        "work_order",
        "service_assignment",
        "maintenance_plan",
        "technician_schedule",
        "route_plan",
        "technician",
        "technician_profile",
    ).all()
    serializer_class = ScheduledVisitSerializer
    filterset_fields = ("company", "operational_site", "technician", "scheduled_date", "status", "priority", "source_type")
    search_fields = ("title", "location_label", "city", "state", "work_order__order_number")
    ordering_fields = ("scheduled_date", "scheduled_start", "route_order", "updated_at")

    def perform_create(self, serializer):
        instance = super().perform_create(serializer)
        try:
            SchedulingAgentTriggerService.run_for_visit(visit=instance, trigger_type=AgentRun.TriggerType.EVENT)
        except Exception:
            pass
        return instance

    def perform_update(self, serializer):
        instance = super().perform_update(serializer)
        try:
            SchedulingAgentTriggerService.run_for_visit(visit=instance, trigger_type=AgentRun.TriggerType.EVENT)
        except Exception:
            pass
        return instance

    @action(detail=False, methods=["get"], url_path="by-technician")
    def by_technician(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        technician_id = request.query_params.get("technician")
        if technician_id:
            queryset = queryset.filter(technician_id=technician_id)
        visit_date = request.query_params.get("date")
        if visit_date:
            queryset = queryset.filter(scheduled_date=visit_date)
        serializer = self.get_serializer(queryset.order_by("scheduled_date", "route_order", "scheduled_start"), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="by-date")
    def by_date(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        visit_date = request.query_params.get("date")
        if visit_date:
            queryset = queryset.filter(scheduled_date=visit_date)
        serializer = self.get_serializer(queryset.order_by("technician_id", "route_order", "scheduled_start"), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="unassigned")
    def unassigned(self, request):
        scope = SmartSystemScopeService.resolve_scope(request)
        if scope.company is None and not request.user.is_superuser:
            raise PermissionDenied(detail="Selecione uma empresa ativa para consultar visitas nao alocadas.")
        visit_date = request.query_params.get("date")
        schedule_date = timezone.localdate() if not visit_date else timezone.datetime.strptime(visit_date, "%Y-%m-%d").date()
        queue = TechnicianRoutingService.build_unassigned_queue(
            schedule_date=schedule_date,
            company=scope.company,
            site=scope.site,
        )
        payload = [
            {
                "visit": self.get_serializer(item["visit"]).data,
                "suggested_technician": {
                    "id": item["suggested_technician"].user_id,
                    "display_name": item["suggested_technician"].display_name,
                    "rating_average": item["suggested_technician"].rating_average,
                }
                if item["suggested_technician"]
                else None,
            }
            for item in queue
        ]
        return Response(payload)

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        technician_id = request.data.get("technician")
        visit_date = request.data.get("date")
        ordered_visits = request.data.get("ordered_visits") or []
        if not technician_id or not visit_date or not ordered_visits:
            return Response({"detail": "technician, date e ordered_visits sao obrigatorios."}, status=status.HTTP_400_BAD_REQUEST)
        technician = User.objects.filter(pk=technician_id).first()
        if technician is None:
            return Response({"detail": "Tecnico nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        scope = SmartSystemScopeService.resolve_scope(request)
        if scope.company is None and not request.user.is_superuser:
            raise PermissionDenied(detail="Selecione uma empresa ativa para reordenar rotas.")
        TechnicianRoutingService.reorder_route(
            technician=technician,
            company=scope.company,
            schedule_date=timezone.datetime.strptime(visit_date, "%Y-%m-%d").date(),
            ordered_visit_public_ids=ordered_visits,
            updated_by=request.user,
        )
        queryset = self.get_queryset().filter(technician=technician, scheduled_date=visit_date).order_by("route_order", "scheduled_start")
        try:
            SchedulingAgentTriggerService.run_technician_analysis(
                company=scope.company,
                technician=technician,
                target_date=timezone.datetime.strptime(visit_date, "%Y-%m-%d").date(),
                site=scope.site,
                trigger_type=AgentRun.TriggerType.EVENT,
            )
        except Exception:
            pass
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
