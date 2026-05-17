from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from rest_framework.authtoken.models import Token


def authenticate_and_get_token(*, email: str, password: str):
    user = authenticate(username=email, password=password)
    if user is None:
        return None, None

    token, _ = Token.objects.get_or_create(user=user)
    update_last_login(sender=user.__class__, user=user)
    user.last_login_at = user.last_login
    user.save(update_fields=["last_login_at"])
    return user, token
