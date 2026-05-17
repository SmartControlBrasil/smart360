from rest_framework.routers import DefaultRouter

from .views import (
    BillingAddonViewSet,
    BillingCustomerViewSet,
    BillingLedgerEntryViewSet,
    BillingPlanViewSet,
    CommissionStatementViewSet,
    ContractViewSet,
    CreditTransactionViewSet,
    CreditWalletViewSet,
    InvoiceItemViewSet,
    InvoiceViewSet,
    PaymentRecordViewSet,
    SubscriptionAddonViewSet,
    SubscriptionViewSet,
)

router = DefaultRouter()
router.register("customers", BillingCustomerViewSet, basename="billing-customers")
router.register("plans", BillingPlanViewSet, basename="billing-plans")
router.register("addons", BillingAddonViewSet, basename="billing-addons")
router.register("contracts", ContractViewSet, basename="billing-contracts")
router.register("subscriptions", SubscriptionViewSet, basename="billing-subscriptions")
router.register("subscription-addons", SubscriptionAddonViewSet, basename="billing-subscription-addons")
router.register("invoices", InvoiceViewSet, basename="billing-invoices")
router.register("invoice-items", InvoiceItemViewSet, basename="billing-invoice-items")
router.register("payment-records", PaymentRecordViewSet, basename="billing-payment-records")
router.register("wallets", CreditWalletViewSet, basename="billing-wallets")
router.register("credit-transactions", CreditTransactionViewSet, basename="billing-credit-transactions")
router.register("ledger-entries", BillingLedgerEntryViewSet, basename="billing-ledger-entries")
router.register("commission-statements", CommissionStatementViewSet, basename="billing-commission-statements")

urlpatterns = router.urls
