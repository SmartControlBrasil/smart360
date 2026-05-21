from django.urls import path

from .views import (
    Smart360LoginView,
    Smart360LogoutView,
    Smart360PasswordResetCompleteView,
    Smart360PasswordResetConfirmView,
    Smart360PasswordResetDoneView,
    Smart360PasswordResetView,
)

app_name = "users"

urlpatterns = [
    path("login/", Smart360LoginView.as_view(), name="login"),
    path("logout/", Smart360LogoutView.as_view(), name="logout"),
    path("password-reset/", Smart360PasswordResetView.as_view(), name="password-reset"),
    path("password-reset/done/", Smart360PasswordResetDoneView.as_view(), name="password-reset-done"),
    path("reset/<uidb64>/<token>/", Smart360PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("reset/done/", Smart360PasswordResetCompleteView.as_view(), name="password-reset-complete"),
]
