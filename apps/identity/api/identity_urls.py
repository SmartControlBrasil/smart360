from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import AuthEventLogViewSet, CompanyInvitationViewSet, MyOnboardingView, UserSessionViewSet

router = DefaultRouter()
router.register("sessions", UserSessionViewSet, basename="identity-sessions")
router.register("invitations", CompanyInvitationViewSet, basename="identity-invitations")
router.register("auth-events", AuthEventLogViewSet, basename="identity-auth-events")

urlpatterns = router.urls + [
    path("onboarding/me/", MyOnboardingView.as_view(), name="identity-onboarding-me"),
]

