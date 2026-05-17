from django.urls import path

from .views import (
    ChangePasswordView,
    EmailVerificationConfirmView,
    EmailVerificationRequestView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshTokenView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="auth-password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("email-verification/request/", EmailVerificationRequestView.as_view(), name="auth-email-verification-request"),
    path("email-verification/confirm/", EmailVerificationConfirmView.as_view(), name="auth-email-verification-confirm"),
]

