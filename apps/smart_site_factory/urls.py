from django.urls import path

from .views import (
    SiteFactoryDashboardView,
    SiteFactoryIntakeView,
    SiteFactoryOrderCommercialOpportunityView,
    SiteFactoryOrderCreateView,
    SiteFactoryOrderDetailView,
    SiteFactoryOrderListView,
    SiteFactoryOrderProposalApproveView,
    SiteFactoryOrderProposalRejectView,
    SiteFactoryOrderProposalSendEmailView,
    SiteFactoryOrderProposalView,
    SiteFactoryTaskListView,
    SiteFactoryTaskStatusView,
)


urlpatterns = [
    path("", SiteFactoryDashboardView.as_view(), name="site-factory-dashboard"),
    path("orders/", SiteFactoryOrderListView.as_view(), name="site-factory-orders"),
    path("orders/new/", SiteFactoryOrderCreateView.as_view(), name="site-factory-order-new"),
    path("orders/<int:pk>/commercial-opportunity/", SiteFactoryOrderCommercialOpportunityView.as_view(), name="site-factory-order-commercial"),
    path("orders/<int:pk>/proposal/approve/", SiteFactoryOrderProposalApproveView.as_view(), name="site-factory-order-proposal-approve"),
    path("orders/<int:pk>/proposal/reject/", SiteFactoryOrderProposalRejectView.as_view(), name="site-factory-order-proposal-reject"),
    path("orders/<int:pk>/proposal/send-email/", SiteFactoryOrderProposalSendEmailView.as_view(), name="site-factory-order-proposal-send-email"),
    path("orders/<int:pk>/proposal/", SiteFactoryOrderProposalView.as_view(), name="site-factory-order-proposal"),
    path("orders/<int:pk>/", SiteFactoryOrderDetailView.as_view(), name="site-factory-order-detail"),
    path("orders/<int:pk>/intake/", SiteFactoryIntakeView.as_view(), name="site-factory-order-intake"),
    path("orders/<int:pk>/tasks/", SiteFactoryTaskListView.as_view(), name="site-factory-order-tasks"),
    path("orders/<int:pk>/tasks/<int:task_pk>/status/", SiteFactoryTaskStatusView.as_view(), name="site-factory-task-status"),
]
