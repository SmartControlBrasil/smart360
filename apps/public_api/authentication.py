from django.utils import timezone
from rest_framework import authentication, exceptions

from apps.identity.authentication import IdentityTokenAuthentication

from .models import IntegrationCredential


class IntegrationCredentialAuthentication(authentication.BaseAuthentication):
    keyword = "ApiKey"

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth:
            return None
        if auth[0].decode().lower() != self.keyword.lower():
            return None
        if len(auth) != 2:
            raise exceptions.AuthenticationFailed("Invalid API key header.")

        try:
            prefix, secret = auth[1].decode().split(".", 1)
        except ValueError as exc:
            raise exceptions.AuthenticationFailed("Malformed API key.") from exc

        credential = (
            IntegrationCredential.objects.select_related("user", "company")
            .filter(key_prefix=prefix, is_active=True)
            .first()
        )
        if credential is None or not credential.is_current or not credential.check_token(secret):
            raise exceptions.AuthenticationFailed("Invalid integration credential.")
        if not credential.user.is_active:
            raise exceptions.AuthenticationFailed("Integration user inactive.")

        credential.last_used_at = timezone.now()
        credential.save(update_fields=["last_used_at", "updated_at"])
        request.integration_credential = credential
        return credential.user, credential

    def authenticate_header(self, request):
        return self.keyword


class PublicApiAuthentication(authentication.BaseAuthentication):
    def __init__(self):
        self._strategies = [IntegrationCredentialAuthentication(), IdentityTokenAuthentication()]

    def authenticate(self, request):
        for strategy in self._strategies:
            result = strategy.authenticate(request)
            if result is not None:
                return result
        return None

    def authenticate_header(self, request):
        return "Bearer"
