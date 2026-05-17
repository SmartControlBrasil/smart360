from django.http import Http404, HttpResponse
from django.db import models
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control_center.services.access_service import AccessAuditService
from apps.access_control_center.services.smart_system_access import SMART_SYSTEM_PERMISSION_KEYS, has_smart_system_permission
from apps.billing.services.billing_service import BillingAccessService
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import (
    Asset,
    Checklist,
    FailureEvent,
    MaintenancePlan,
    Part,
    PartAssetLink,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    StockMovement,
)
from apps.smart_system.services.maintenance_service import FailureEventService, ServiceOrderService
from apps.marketplace_technicians.models import (
    TechnicianAssignment,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRequest,
)
from apps.marketplace_technicians.services.access import MarketplaceAccessService
from apps.marketplace_technicians.services.marketplace_service import (
    TechnicianAssignmentService,
    TechnicianMatchingService,
    TechnicianServiceOfferService,
)

from .authentication import PublicApiAuthentication
from .pagination import PublicApiPagination
from .serializers import (
    PublicAssetSerializer,
    PublicChecklistExecutionSerializer,
    PublicChecklistSerializer,
    PublicCompanySerializer,
    PublicContextSerializer,
    PublicFailureSerializer,
    PublicMarketplaceAssignmentSerializer,
    PublicMarketplaceMatchSerializer,
    PublicMarketplaceOfferSerializer,
    PublicMarketplaceReviewSerializer,
    PublicMarketplaceServiceRequestSerializer,
    PublicMaintenancePlanSerializer,
    PublicPartAssetLinkSerializer,
    PublicPartSerializer,
    PublicReportMetadataSerializer,
    PublicServiceOrderSerializer,
    PublicSiteSerializer,
    PublicStockMovementSerializer,
    PublicTechnicianProfileSerializer,
)
from .services.reports import PublicReportService
from .services.scoping import PublicApiScopeService
from .throttling import PublicApiBurstRateThrottle, PublicApiSustainedRateThrottle
from shared_kernel.observability.context import set_request_context


class PublicApiBaseMixin:
    authentication_classes = [PublicApiAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PublicApiPagination
    throttle_classes = [PublicApiBurstRateThrottle, PublicApiSustainedRateThrottle]
    permission_domain = None
    permission_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "partial_update": "update",
        "update": "update",
        "destroy": "delete",
    }
    enforce_billing_access = True

    def handle_exception(self, exc):
        from .exceptions import smart360_exception_handler

        response = smart360_exception_handler(exc, {"view": self, "request": getattr(self, "request", None)})
        if response is not None:
            return response
        return super().handle_exception(exc)

    def get_scope(self):
        if not hasattr(self, "_public_scope"):
            self._public_scope = PublicApiScopeService.resolve_scope(self.request)
        return self._public_scope

    def get_permission_action(self):
        return self.permission_action_map.get(getattr(self, "action", self.request.method.lower()), "view")

    def _integration_scope_allows(self):
        credential = getattr(self.request, "integration_credential", None)
        if credential is None or not credential.allowed_scopes:
            return True
        exact_key = f"{self.permission_domain}.{self.get_permission_action()}"
        wildcard_key = f"{self.permission_domain}.*"
        return exact_key in credential.allowed_scopes or wildcard_key in credential.allowed_scopes or "*" in credential.allowed_scopes

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        scope = self.get_scope()
        raw_request = getattr(request, "_request", None)
        if raw_request is not None:
            raw_request.user = request.user
        set_request_context(
            user=request.user,
            user_id=getattr(request.user, "id", ""),
            company=scope.company,
            company_id=getattr(scope.company, "id", ""),
            site=scope.site,
            site_id=getattr(scope.site, "id", ""),
            path=request.path,
            method=request.method,
            module="public_api",
            origin="public_api",
        )
        if self.enforce_billing_access and scope.company is not None:
            billing_context = BillingAccessService.get_company_billing_context(scope.company)
            if not billing_context["access_allowed"] and not request.user.is_superuser:
                raise PermissionDenied(f"Tenant {scope.company.name} bloqueado por status financeiro {billing_context['access_status']}.")
        if self.permission_domain:
            if not self._integration_scope_allows():
                raise PermissionDenied("Integration credential scope does not allow this action.")
            allowed = has_smart_system_permission(
                request.user,
                self.permission_domain,
                self.get_permission_action(),
                company=scope.company,
                log_decision=True,
                resource_type=self.permission_domain,
                resource_id=str(self.kwargs.get("public_id", "")),
                reason=f"public_api:{self.permission_domain}.{self.get_permission_action()}",
            )
            if not allowed:
                raise PermissionDenied("You do not have permission to perform this action in the active scope.")

    def get_queryset(self):
        queryset = super().get_queryset()
        return PublicApiScopeService.scope_queryset(queryset, self.request)

    def _log_event(self, action, entity_type, entity_id, payload=None):
        scope = self.get_scope()
        SystemEventService.log_system_event(
            event_type=f"public_api.{entity_type}.{action}",
            source_module="public_api",
            message=f"Public API {entity_type} {action}.",
            entity_type=entity_type,
            entity_id=str(entity_id),
            user=self.request.user,
            company=scope.company,
            site=scope.site,
            payload=payload or {"path": self.request.path, "method": self.request.method},
        )

    def apply_active_scope(self, queryset, *, company_field=None, site_field=None):
        scope = self.get_scope()
        if company_field and scope.company is not None:
            queryset = queryset.filter(**{company_field: scope.company})
        if site_field and scope.site is not None:
            queryset = queryset.filter(**{site_field: scope.site})
        return queryset


class PublicApiContextView(PublicApiBaseMixin, APIView):
    permission_domain = None
    enforce_billing_access = False

    @extend_schema(
        tags=["Public Context"],
        summary="Contexto autenticado atual",
        parameters=[
            OpenApiParameter(name="company", type=str, location=OpenApiParameter.QUERY, description="Slug da empresa ativa."),
            OpenApiParameter(name="site", type=str, location=OpenApiParameter.QUERY, description="Codigo do site ativo."),
        ],
        responses={200: PublicContextSerializer},
    )
    def get(self, request, *args, **kwargs):
        scope = self.get_scope()
        billing_context = BillingAccessService.get_company_billing_context(scope.company)
        permission_map = [
            key
            for key in SMART_SYSTEM_PERMISSION_KEYS
            if has_smart_system_permission(request.user, *key.split(".", 1), company=scope.company, log_decision=False)
        ]
        auth_mode = "integration" if hasattr(request, "integration_credential") else "user"
        payload = {
            "user": {
                "public_id": str(request.user.public_id),
                "email": request.user.email,
                "display_name": request.user.display_name or request.user.email,
            },
            "authentication_mode": auth_mode,
            "active_company": scope.company,
            "active_site": scope.site,
            "companies": scope.companies,
            "sites": scope.sites,
            "permissions": permission_map,
            "billing": {
                "access_status": billing_context["access_status"],
                "access_allowed": billing_context["access_allowed"],
                "warning": billing_context["warning"],
                "plan": getattr(billing_context["plan"], "name", None),
            },
        }
        return Response(PublicContextSerializer(payload).data)


class PublicCompanyListView(PublicApiBaseMixin, APIView):
    permission_domain = None
    enforce_billing_access = False

    @extend_schema(tags=["Public Context"], summary="Empresas permitidas", responses={200: PublicCompanySerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return Response(PublicCompanySerializer(self.get_scope().companies, many=True).data)


class PublicSiteListView(PublicApiBaseMixin, APIView):
    permission_domain = None
    enforce_billing_access = False

    @extend_schema(tags=["Public Context"], summary="Sites permitidos", responses={200: PublicSiteSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return Response(PublicSiteSerializer(self.get_scope().sites, many=True).data)


class PublicAssetViewSet(PublicApiBaseMixin, viewsets.ModelViewSet):
    queryset = Asset.objects.select_related("operational_site", "category", "operational_site__maintenance_client__company").all()
    serializer_class = PublicAssetSerializer
    lookup_field = "public_id"
    permission_domain = "assets"
    filterset_fields = ("status", "criticality", "category__slug", "operational_site__code")
    search_fields = ("asset_tag", "name", "manufacturer", "model", "serial_number")
    ordering_fields = ("asset_tag", "name", "updated_at")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        instance = serializer.save()
        self._log_event("created", "assets", instance.public_id)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._log_event("updated", "assets", instance.public_id)


class PublicWorkOrderViewSet(PublicApiBaseMixin, viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.select_related("client", "operational_site", "asset", "maintenance_plan", "assigned_to").all()
    serializer_class = PublicServiceOrderSerializer
    lookup_field = "public_id"
    permission_domain = "work_orders"
    filterset_fields = ("status", "priority", "maintenance_type", "asset__asset_tag", "operational_site__code")
    search_fields = ("order_number", "title", "description", "requested_by")
    ordering_fields = ("opened_at", "scheduled_start", "updated_at")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        instance = ServiceOrderService.create_service_order(user=self.request.user, validated_data=serializer.validated_data)
        serializer.instance = instance
        self._log_event("created", "work_orders", instance.order_number)

    def perform_update(self, serializer):
        before_status = serializer.instance.status
        instance = ServiceOrderService.update_service_order(
            service_order=serializer.instance,
            validated_data=serializer.validated_data,
            user=self.request.user,
        )
        serializer.instance = instance
        self._log_event("updated", "work_orders", instance.order_number, payload={"before_status": before_status, "after_status": instance.status})

    @action(detail=True, methods=["post"])
    def assign(self, request, public_id=None):
        if not has_smart_system_permission(request.user, "work_orders", "assign", company=self.get_scope().company):
            raise PermissionDenied("You do not have permission to assign work orders.")
        instance = self.get_object()
        assigned_user = request.data.get("assigned_to_id")
        if not assigned_user:
            return Response({"error": {"code": "validation_error", "detail": {"assigned_to_id": ["This field is required."]}, "status_code": 400}}, status=400)
        serializer = self.get_serializer(instance, data={"assigned_to_id": assigned_user}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        AccessAuditService.log(
            user=request.user,
            action="work_order_assigned",
            domain="work_orders",
            resource_type="service_order",
            resource_id=instance.order_number,
            decision="allow",
            company=self.get_scope().company,
            site=self.get_scope().site,
            after_state={"assigned_to_id": assigned_user},
        )
        self._log_event("assigned", "work_orders", instance.order_number)
        return Response(self.get_serializer(instance).data)


class PublicPreventiveViewSet(PublicApiBaseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MaintenancePlan.objects.select_related("company", "operational_site", "asset", "checklist").all()
    serializer_class = PublicMaintenancePlanSerializer
    lookup_field = "public_id"
    permission_domain = "preventive_plans"
    filterset_fields = ("frequency_type", "is_active", "asset__asset_tag", "operational_site__code")
    search_fields = ("name", "description", "notes")
    ordering_fields = ("next_due_date", "updated_at", "name")

    @action(detail=False, methods=["get"], url_path="schedule")
    def schedule(self, request):
        queryset = self.filter_queryset(self.get_queryset()).exclude(next_due_date__isnull=True).order_by("next_due_date")
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class PublicFailureViewSet(PublicApiBaseMixin, viewsets.ModelViewSet):
    queryset = FailureEvent.objects.select_related("asset", "service_order", "asset__operational_site__maintenance_client__company").all()
    serializer_class = PublicFailureSerializer
    lookup_field = "public_id"
    permission_domain = "failures"
    filterset_fields = ("severity", "status", "asset__asset_tag")
    search_fields = ("symptom", "probable_cause", "root_cause")
    ordering_fields = ("detected_at", "updated_at", "downtime_minutes")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        instance = FailureEventService.create_failure_event(user=self.request.user, validated_data=serializer.validated_data)
        serializer.instance = instance
        self._log_event("created", "failures", instance.public_id)

    @action(detail=True, methods=["patch"], url_path="rca")
    def update_rca(self, request, public_id=None):
        if not has_smart_system_permission(request.user, "failures", "rca", company=self.get_scope().company):
            raise PermissionDenied("You do not have permission to update RCA data.")
        instance = self.get_object()
        before = {"probable_cause": instance.probable_cause, "root_cause": instance.root_cause}
        instance.probable_cause = request.data.get("probable_cause", instance.probable_cause)
        instance.root_cause = request.data.get("root_cause", instance.root_cause)
        instance.notes = request.data.get("notes", instance.notes)
        instance.save(update_fields=["probable_cause", "root_cause", "notes", "updated_at"])
        AccessAuditService.log(
            user=request.user,
            action="failure_rca_updated",
            domain="failures",
            resource_type="failure",
            resource_id=str(instance.public_id),
            decision="allow",
            company=self.get_scope().company,
            site=self.get_scope().site,
            before_state=before,
            after_state={"probable_cause": instance.probable_cause, "root_cause": instance.root_cause},
        )
        self._log_event("rca_updated", "failures", instance.public_id)
        return Response(self.get_serializer(instance).data)


class PublicChecklistViewSet(PublicApiBaseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Checklist.objects.prefetch_related("items").all()
    serializer_class = PublicChecklistSerializer
    lookup_field = "public_id"
    permission_domain = "checklists"
    filterset_fields = ("is_active", "operational_site__code")
    search_fields = ("name", "description")
    ordering_fields = ("name", "updated_at")


class PublicChecklistExecutionViewSet(PublicApiBaseMixin, viewsets.ModelViewSet):
    queryset = ServiceOrderChecklistResponse.objects.select_related("service_order", "checklist_item", "service_order__operational_site").all()
    serializer_class = PublicChecklistExecutionSerializer
    lookup_field = "public_id"
    permission_domain = "checklists"
    filterset_fields = ("service_order__order_number", "checklist_item__checklist__public_id")
    search_fields = ("service_order__order_number", "checklist_item__title", "response_text", "response_choice")
    ordering_fields = ("created_at", "updated_at")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permission_action(self):
        if getattr(self, "action", None) in {"create", "partial_update", "update"}:
            return "execute"
        return super().get_permission_action()

    def perform_create(self, serializer):
        instance = serializer.save()
        self._log_event("execution_recorded", "checklists", instance.public_id)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._log_event("execution_updated", "checklists", instance.public_id)


class PublicPartViewSet(PublicApiBaseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Part.objects.select_related("company", "operational_site").all()
    serializer_class = PublicPartSerializer
    lookup_field = "public_id"
    permission_domain = "inventory"
    filterset_fields = ("category", "manufacturer", "operational_site__code", "status")
    search_fields = ("code", "name", "manufacturer", "model", "location")
    ordering_fields = ("code", "name", "current_stock", "updated_at")

    @action(detail=True, methods=["get"], url_path="asset-links")
    def asset_links(self, request, public_id=None):
        instance = self.get_object()
        payload = PublicPartAssetLinkSerializer(instance.asset_links.select_related("asset"), many=True)
        return Response(payload.data)


class PublicStockMovementViewSet(PublicApiBaseMixin, viewsets.ModelViewSet):
    queryset = StockMovement.objects.select_related("part", "company", "operational_site", "service_order", "performed_by").all()
    serializer_class = PublicStockMovementSerializer
    lookup_field = "public_id"
    permission_domain = "inventory"
    filterset_fields = ("movement_type", "part__code", "operational_site__code")
    search_fields = ("part__code", "reference_type", "reference_id", "service_order__order_number")
    ordering_fields = ("occurred_at", "created_at", "quantity")
    http_method_names = ["get", "post", "head", "options"]

    def get_permission_action(self):
        if getattr(self, "action", None) == "create":
            return "adjust_stock"
        return super().get_permission_action()

    def perform_create(self, serializer):
        part = serializer.validated_data["part"]
        quantity = serializer.validated_data["quantity"]
        movement_type = serializer.validated_data["movement_type"]
        if movement_type == StockMovement.MovementType.OUTBOUND and part.current_stock < quantity:
            raise ValidationError({"quantity": ["Insufficient stock for outbound movement."]})
        if movement_type == StockMovement.MovementType.INBOUND:
            part.current_stock += quantity
        elif movement_type == StockMovement.MovementType.OUTBOUND:
            part.current_stock -= quantity
        else:
            part.current_stock = quantity
        part.save(update_fields=["current_stock", "updated_at"])
        instance = serializer.save(
            company=self.get_scope().company or part.company,
            operational_site=self.get_scope().site or part.operational_site,
            performed_by=self.request.user,
        )
        self._log_event("stock_movement_created", "inventory", instance.public_id)
        AccessAuditService.log(
            user=self.request.user,
            action="inventory_adjusted",
            domain="inventory",
            resource_type="part",
            resource_id=part.code,
            decision="allow",
            company=self.get_scope().company or part.company,
            site=self.get_scope().site or part.operational_site,
            after_state={"current_stock": str(part.current_stock), "movement_type": movement_type, "quantity": str(quantity)},
        )
        return instance


class PublicReportListView(PublicApiBaseMixin, APIView):
    permission_domain = "reports"

    @extend_schema(tags=["Public Reports"], summary="Listar relatorios disponiveis", responses={200: PublicReportMetadataSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return Response(PublicReportMetadataSerializer(PublicReportService.list_reports(request), many=True).data)


class PublicReportDetailView(PublicApiBaseMixin, APIView):
    permission_domain = "reports"

    @extend_schema(tags=["Public Reports"], summary="Detalhe metadata do relatorio", responses={200: PublicReportMetadataSerializer})
    def get(self, request, report_type, reference_code, *args, **kwargs):
        try:
            reference = PublicReportService.get_reference(report_type, reference_code, request)
        except Exception as exc:
            raise Http404("Report reference not found.") from exc
        payload = PublicReportService.build_report_metadata(report_type, reference, request)
        return Response(PublicReportMetadataSerializer(payload).data)


class PublicReportDownloadView(PublicApiBaseMixin, APIView):
    permission_domain = "reports"

    def get_permission_action(self):
        return "export"

    @extend_schema(tags=["Public Reports"], summary="Baixar PDF do relatorio", responses={200: OpenApiResponse(description="PDF binary")})
    def get(self, request, report_type, reference_code, *args, **kwargs):
        try:
            reference = PublicReportService.get_reference(report_type, reference_code, request)
        except Exception as exc:
            raise Http404("Report reference not found.") from exc
        pdf_bytes = PublicReportService.render_pdf(report_type, reference)
        AccessAuditService.log(
            user=request.user,
            action="reports_exported",
            domain="reports",
            resource_type="report",
            resource_id=f"{report_type}:{reference_code}",
            decision="allow",
            company=self.get_scope().company,
            site=self.get_scope().site,
            after_state={"report_type": report_type, "reference_code": reference_code},
        )
        self._log_event("exported", "reports", f"{report_type}:{reference_code}")
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{report_type}-{reference_code}.pdf"'
        return response


class PublicMarketplaceTechnicianViewSet(PublicApiBaseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = TechnicianProfile.objects.select_related("user", "company").prefetch_related("skill_assignments__skill").all()
    serializer_class = PublicTechnicianProfileSerializer
    lookup_field = "public_id"
    permission_domain = "marketplace_technicians"
    filterset_fields = ("marketplace_status", "verification_status", "company__slug")
    search_fields = ("display_name", "user__email", "bio")
    ordering_fields = ("display_name", "rating_average", "completed_jobs_count", "updated_at")

    def get_queryset(self):
        return MarketplaceAccessService.scope_profiles_queryset(self.request.user, super().get_queryset())


class PublicMarketplaceServiceRequestViewSet(PublicApiBaseMixin, viewsets.ModelViewSet):
    queryset = TechnicianServiceRequest.objects.select_related(
        "requester_company",
        "related_site",
        "related_asset",
        "related_service_order",
    ).annotate(offers_count=models.Count("offers", distinct=True))
    serializer_class = PublicMarketplaceServiceRequestSerializer
    lookup_field = "public_id"
    permission_domain = "marketplace_requests"
    filterset_fields = ("status", "priority", "service_type", "related_site__code", "requester_company__slug")
    search_fields = ("title", "description", "category", "city", "state")
    ordering_fields = ("created_at", "requested_date", "deadline_at", "updated_at")
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = MarketplaceAccessService.scope_requests_queryset(self.request.user, super().get_queryset())
        return self.apply_active_scope(
            queryset,
            company_field="requester_company",
            site_field="related_site",
        )

    def perform_create(self, serializer):
        if not MarketplaceAccessService.is_company_operator(self.request.user):
            raise PermissionDenied("Only company operators can publish marketplace service requests.")
        instance = serializer.save()
        self._log_event("created", "marketplace_requests", instance.public_id)

    @action(detail=True, methods=["get", "post"])
    def matching(self, request, public_id=None):
        service_request = self.get_object()
        if request.method.lower() == "post":
            if not MarketplaceAccessService.can_manage_request(request.user, service_request):
                raise PermissionDenied("Only the company operator can refresh matching in this scope.")
            TechnicianMatchingService.refresh_matches(service_request=service_request)
            self._log_event("matching_refreshed", "marketplace_requests", service_request.public_id)
        queryset = MarketplaceAccessService.scope_matching_queryset(
            request.user,
            service_request.matching_records.select_related("technician_profile", "technician_profile__user"),
        ).order_by("ranking_position", "-match_score")
        return Response(PublicMarketplaceMatchSerializer(queryset, many=True).data)


class PublicMarketplaceOfferViewSet(PublicApiBaseMixin, viewsets.ModelViewSet):
    queryset = TechnicianServiceOffer.objects.select_related(
        "service_request",
        "service_request__requester_company",
        "service_request__related_site",
        "technician_profile",
    ).all()
    serializer_class = PublicMarketplaceOfferSerializer
    lookup_field = "public_id"
    permission_domain = "marketplace_offers"
    filterset_fields = ("status", "service_request__public_id", "technician_profile__public_id")
    search_fields = ("service_request__title", "technician_profile__display_name", "message")
    ordering_fields = ("created_at", "updated_at", "proposed_amount")
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = MarketplaceAccessService.scope_offers_queryset(self.request.user, super().get_queryset())
        return self.apply_active_scope(
            queryset,
            company_field="service_request__requester_company",
            site_field="service_request__related_site",
        )

    def perform_create(self, serializer):
        service_request = serializer.validated_data["service_request"]
        technician_profile = serializer.validated_data["technician_profile"]
        if not MarketplaceAccessService.can_offer(self.request.user, service_request, technician_profile):
            raise PermissionDenied("Only the technician owner can submit this offer.")
        instance = serializer.save()
        self._log_event("created", "marketplace_offers", instance.public_id)

    def get_permission_action(self):
        if getattr(self, "action", None) in {"accept", "reject"}:
            return "manage"
        if getattr(self, "action", None) == "withdraw":
            return "create"
        return super().get_permission_action()

    @action(detail=True, methods=["post"])
    def accept(self, request, public_id=None):
        offer = self.get_object()
        if not MarketplaceAccessService.can_manage_request(request.user, offer.service_request):
            raise PermissionDenied("Only the company operator can accept offers in this scope.")
        assignment = TechnicianServiceOfferService.accept_offer(user=request.user, offer=offer)
        self._log_event("accepted", "marketplace_offers", offer.public_id)
        return Response(PublicMarketplaceAssignmentSerializer(assignment).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, public_id=None):
        offer = self.get_object()
        if not MarketplaceAccessService.can_manage_request(request.user, offer.service_request):
            raise PermissionDenied("Only the company operator can reject offers in this scope.")
        TechnicianServiceOfferService.reject_offer(user=request.user, offer=offer)
        self._log_event("rejected", "marketplace_offers", offer.public_id)
        return Response(self.get_serializer(offer).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, public_id=None):
        offer = self.get_object()
        if getattr(request.user, "technician_profile", None) is None or offer.technician_profile_id != request.user.technician_profile.id:
            raise PermissionDenied("Only the offer owner can withdraw this offer.")
        TechnicianServiceOfferService.withdraw_offer(user=request.user, offer=offer)
        self._log_event("withdrawn", "marketplace_offers", offer.public_id)
        return Response(self.get_serializer(offer).data)


class PublicMarketplaceAssignmentViewSet(PublicApiBaseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = TechnicianAssignment.objects.select_related(
        "technician_service_request",
        "technician_service_request__requester_company",
        "technician_service_request__related_site",
        "technician_profile",
        "service_offer",
    ).all()
    serializer_class = PublicMarketplaceAssignmentSerializer
    lookup_field = "public_id"
    permission_domain = "marketplace_assignments"
    filterset_fields = ("assignment_status", "technician_service_request__public_id", "technician_profile__public_id")
    search_fields = ("technician_service_request__title", "technician_profile__display_name")
    ordering_fields = ("assigned_at", "started_at", "completed_at", "updated_at")

    def get_queryset(self):
        queryset = MarketplaceAccessService.scope_assignments_queryset(self.request.user, super().get_queryset())
        return self.apply_active_scope(
            queryset,
            company_field="technician_service_request__requester_company",
            site_field="technician_service_request__related_site",
        )

    def get_permission_action(self):
        if getattr(self, "action", None) in {"start", "complete"}:
            return "execute"
        return super().get_permission_action()

    @action(detail=True, methods=["post"])
    def start(self, request, public_id=None):
        assignment = self.get_object()
        if not MarketplaceAccessService.can_manage_assignment(request.user, assignment):
            raise PermissionDenied("Assignment execution is outside your marketplace scope.")
        TechnicianAssignmentService.transition_status(
            assignment=assignment,
            status=TechnicianAssignment.AssignmentStatus.IN_PROGRESS,
        )
        self._log_event("started", "marketplace_assignments", assignment.public_id)
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, public_id=None):
        assignment = self.get_object()
        if not MarketplaceAccessService.can_manage_assignment(request.user, assignment):
            raise PermissionDenied("Assignment execution is outside your marketplace scope.")
        TechnicianAssignmentService.transition_status(
            assignment=assignment,
            status=TechnicianAssignment.AssignmentStatus.COMPLETED,
        )
        self._log_event("completed", "marketplace_assignments", assignment.public_id)
        return Response(self.get_serializer(assignment).data)


class PublicMarketplaceReviewViewSet(PublicApiBaseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = TechnicianReview.objects.select_related(
        "assignment",
        "assignment__technician_service_request",
        "assignment__technician_service_request__requester_company",
        "technician_profile",
        "reviewer_company",
    ).all()
    serializer_class = PublicMarketplaceReviewSerializer
    lookup_field = "public_id"
    permission_domain = "marketplace_reviews"
    filterset_fields = ("status", "rating", "technician_profile__public_id")
    search_fields = ("comment", "technician_profile__display_name")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        queryset = MarketplaceAccessService.scope_reviews_queryset(self.request.user, super().get_queryset())
        return self.apply_active_scope(
            queryset,
            company_field="assignment__technician_service_request__requester_company",
            site_field="assignment__technician_service_request__related_site",
        )
