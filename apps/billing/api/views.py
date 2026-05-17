from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from apps.ai_agents_center.models import AgentRun
from apps.ai_agents_center.services.anomaly_triggers import AnomalyAgentTriggerService
from apps.ai_agents_center.services.profitability_triggers import ProfitabilityAgentTriggerService

from ..models import (
    BillingAddon,
    BillingCustomer,
    BillingLedgerEntry,
    BillingPlan,
    CommissionStatement,
    Contract,
    CreditTransaction,
    CreditWallet,
    Invoice,
    InvoiceItem,
    PaymentRecord,
    Subscription,
    SubscriptionAddon,
)
from ..services.billing_service import BillingDashboardService, ContractService, PaymentService, SubscriptionService
from .serializers import (
    BillingAddonSerializer,
    BillingCustomerSerializer,
    BillingLedgerEntrySerializer,
    BillingPlanSerializer,
    CommissionStatementSerializer,
    ContractSerializer,
    CreditTransactionSerializer,
    CreditWalletSerializer,
    InvoiceItemSerializer,
    InvoiceSerializer,
    PaymentRecordSerializer,
    SubscriptionAddonSerializer,
    SubscriptionSerializer,
)


class BillingBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class BillingCustomerViewSet(BillingBaseViewSet):
    queryset = BillingCustomer.objects.select_related("user", "company").all()
    serializer_class = BillingCustomerSerializer
    filterset_fields = ("customer_type", "status", "company", "user")
    search_fields = ("billing_email", "trade_name", "legal_name", "document_number", "external_reference")
    ordering_fields = ("created_at", "updated_at", "trade_name")


class BillingPlanViewSet(BillingBaseViewSet):
    queryset = BillingPlan.objects.all()
    serializer_class = BillingPlanSerializer
    filterset_fields = ("billing_interval", "currency", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "price_amount", "updated_at")


class BillingAddonViewSet(BillingBaseViewSet):
    queryset = BillingAddon.objects.all()
    serializer_class = BillingAddonSerializer
    filterset_fields = ("addon_type", "currency", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "price_amount", "updated_at")


class ContractViewSet(BillingBaseViewSet):
    queryset = Contract.objects.select_related("company", "billing_customer", "plan", "sales_owner").all()
    serializer_class = ContractSerializer
    filterset_fields = ("company", "plan", "billing_periodicity", "status")
    search_fields = ("contract_code", "company__name", "plan__name", "notes")
    ordering_fields = ("start_date", "renewal_date", "contracted_amount", "updated_at")

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            ProfitabilityAgentTriggerService.run_company_analysis(
                company=instance.company,
                trigger_type=AgentRun.TriggerType.EVENT,
                trigger_reference=f"date:{instance.start_date.isoformat()}",
            )
        except Exception:
            pass
        try:
            AnomalyAgentTriggerService.run_company_analysis(
                company=instance.company,
                trigger_type=AgentRun.TriggerType.EVENT,
                trigger_reference=f"date:{instance.start_date.isoformat()}",
            )
        except Exception:
            pass
        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            ProfitabilityAgentTriggerService.run_company_analysis(
                company=instance.company,
                trigger_type=AgentRun.TriggerType.EVENT,
                trigger_reference=f"date:{timezone.localdate().isoformat()}",
            )
        except Exception:
            pass
        try:
            AnomalyAgentTriggerService.run_company_analysis(
                company=instance.company,
                trigger_type=AgentRun.TriggerType.EVENT,
                trigger_reference=f"date:{timezone.localdate().isoformat()}",
            )
        except Exception:
            pass
        return instance

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        contract = self.get_object()
        updated = ContractService.suspend_contract(contract=contract, reason=request.data.get("reason", ""))
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        contract = self.get_object()
        updated = ContractService.cancel_contract(contract=contract, reason=request.data.get("reason", ""))
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def dashboard_summary(self, request):
        return Response(BillingDashboardService.get_summary(), status=status.HTTP_200_OK)


class SubscriptionViewSet(BillingBaseViewSet):
    queryset = Subscription.objects.select_related("billing_customer", "plan").all()
    serializer_class = SubscriptionSerializer
    filterset_fields = ("billing_customer", "plan", "status", "auto_renew")
    search_fields = ("billing_customer__billing_email", "plan__name", "notes")
    ordering_fields = ("started_at", "current_period_end", "updated_at")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        subscription = self.get_object()
        cancelled = SubscriptionService.cancel_subscription(subscription=subscription)
        return Response(self.get_serializer(cancelled).data, status=status.HTTP_200_OK)


class SubscriptionAddonViewSet(BillingBaseViewSet):
    queryset = SubscriptionAddon.objects.select_related("subscription", "addon").all()
    serializer_class = SubscriptionAddonSerializer
    filterset_fields = ("subscription", "addon", "status")
    search_fields = ("subscription__billing_customer__billing_email", "addon__name")
    ordering_fields = ("started_at", "updated_at")


class InvoiceViewSet(BillingBaseViewSet):
    queryset = Invoice.objects.select_related("billing_customer", "subscription").all()
    serializer_class = InvoiceSerializer
    filterset_fields = ("billing_customer", "subscription", "status", "currency")
    search_fields = ("invoice_number", "billing_customer__billing_email", "notes")
    ordering_fields = ("issued_at", "due_at", "paid_at", "total_amount", "updated_at")

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.company_id:
            try:
                ProfitabilityAgentTriggerService.run_company_analysis(
                    company=instance.company,
                    trigger_type=AgentRun.TriggerType.EVENT,
                    trigger_reference=f"date:{instance.issued_at.date().isoformat()}",
                )
            except Exception:
                pass
            try:
                AnomalyAgentTriggerService.run_company_analysis(
                    company=instance.company,
                    trigger_type=AgentRun.TriggerType.EVENT,
                    trigger_reference=f"date:{instance.issued_at.date().isoformat()}",
                )
            except Exception:
                pass
        return instance


class InvoiceItemViewSet(BillingBaseViewSet):
    queryset = InvoiceItem.objects.select_related("invoice").all()
    serializer_class = InvoiceItemSerializer
    filterset_fields = ("invoice", "item_type", "reference_type")
    search_fields = ("invoice__invoice_number", "description", "reference_type", "reference_id")
    ordering_fields = ("created_at", "updated_at", "total_amount")


class PaymentRecordViewSet(BillingBaseViewSet):
    queryset = PaymentRecord.objects.select_related("invoice", "invoice__billing_customer").all()
    serializer_class = PaymentRecordSerializer
    filterset_fields = ("invoice", "provider", "payment_method", "status", "currency")
    search_fields = ("invoice__invoice_number", "provider_reference", "notes")
    ordering_fields = ("created_at", "updated_at", "paid_at", "amount")

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        payment = self.get_object()
        updated = PaymentService.mark_paid(payment=payment)
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)


class CreditWalletViewSet(BillingBaseViewSet):
    queryset = CreditWallet.objects.select_related("billing_customer").all()
    serializer_class = CreditWalletSerializer
    filterset_fields = ("billing_customer", "wallet_type", "currency", "is_active")
    search_fields = ("billing_customer__billing_email",)
    ordering_fields = ("created_at", "updated_at", "balance")


class CreditTransactionViewSet(BillingBaseViewSet):
    queryset = CreditTransaction.objects.select_related("wallet", "wallet__billing_customer").all()
    serializer_class = CreditTransactionSerializer
    filterset_fields = ("wallet", "transaction_type", "reference_type")
    search_fields = ("wallet__billing_customer__billing_email", "reference_type", "reference_id", "description")
    ordering_fields = ("created_at", "updated_at", "amount")


class BillingLedgerEntryViewSet(BillingBaseViewSet):
    queryset = BillingLedgerEntry.objects.select_related("billing_customer").all()
    serializer_class = BillingLedgerEntrySerializer
    filterset_fields = ("billing_customer", "entry_type", "currency", "reference_type")
    search_fields = ("billing_customer__billing_email", "reference_type", "reference_id", "description")
    ordering_fields = ("occurred_at", "created_at", "updated_at", "amount")


class CommissionStatementViewSet(BillingBaseViewSet):
    queryset = CommissionStatement.objects.select_related("billing_customer", "related_company").all()
    serializer_class = CommissionStatementSerializer
    filterset_fields = ("billing_customer", "related_company", "statement_type", "status", "currency")
    search_fields = ("billing_customer__billing_email", "related_company__name", "notes")
    ordering_fields = ("created_at", "updated_at", "net_amount")
