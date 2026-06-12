from django.urls import path

from .views import receive_webhook


urlpatterns = [
    path("webhooks/<slug:slug>/", receive_webhook, name="automation_webhook_receive"),
]
