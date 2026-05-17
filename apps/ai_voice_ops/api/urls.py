from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ai_voice_ops.api.views import VoiceCatalogView, VoiceInteractionViewSet, VoiceOpsProfileViewSet, VoiceProcessView


router = DefaultRouter()
router.register("interactions", VoiceInteractionViewSet, basename="voiceops-interaction")
router.register("profiles", VoiceOpsProfileViewSet, basename="voiceops-profile")


urlpatterns = router.urls + [
    path("process/", VoiceProcessView.as_view(), name="voiceops-process"),
    path("catalog/", VoiceCatalogView.as_view(), name="voiceops-catalog"),
]

