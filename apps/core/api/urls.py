from django.urls import path

from .views import ApiRootView, HealthCheckDetailsView, HealthCheckView, HealthLiveView, HealthReadyView

urlpatterns = [
    path("", ApiRootView.as_view(), name="core-api-root"),
    path("health/live/", HealthLiveView.as_view(), name="core-api-health-live"),
    path("health/ready/", HealthReadyView.as_view(), name="core-api-health-ready"),
    path("health/", HealthCheckView.as_view(), name="core-api-health"),
    path("health/details/", HealthCheckDetailsView.as_view(), name="core-api-health-details"),
]
