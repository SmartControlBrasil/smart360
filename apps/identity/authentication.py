from rest_framework import authentication, exceptions

from .models import UserSession


class IdentityTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Token"
    alt_keyword = "Bearer"

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth:
            return None
        if auth[0].decode().lower() not in {self.keyword.lower(), self.alt_keyword.lower()}:
            return None
        if len(auth) != 2:
            raise exceptions.AuthenticationFailed("Invalid authentication header.")

        token = auth[1].decode()
        session = (
            UserSession.objects.select_related("user")
            .filter(token_identifier=token, is_active=True, revoked_at__isnull=True)
            .first()
        )
        if session is None:
            raise exceptions.AuthenticationFailed("Invalid or expired token.")
        if not session.user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")

        session.last_seen_at = session.last_seen_at or session.created_at
        session.save(update_fields=["last_seen_at", "updated_at"])
        return (session.user, session)

    def authenticate_header(self, request):
        return self.keyword

