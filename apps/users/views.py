from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import reverse_lazy

from .forms import Smart360AuthenticationForm


class Smart360LoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = Smart360AuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me")
        if not remember_me:
            self.request.session.set_expiry(0)
        return super().form_valid(form)


class Smart360LogoutView(LogoutView):
    next_page = reverse_lazy("users:login")


class Smart360PasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("users:password-reset-done")


class Smart360PasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class Smart360PasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("users:password-reset-complete")


class Smart360PasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
