from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import User

from .models import OnboardingProfile


@receiver(post_save, sender=User)
def ensure_onboarding_profile(sender, instance, created, **kwargs):
    if created:
        OnboardingProfile.objects.create(
            user=instance,
            email_verified=instance.is_verified,
        )

