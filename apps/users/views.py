from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import reverse_lazy

from .access import get_post_login_redirect_url
from .forms import Smart360AuthenticationForm


class Smart360LoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = Smart360AuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return get_post_login_redirect_url(
            self.request.user,
            self.get_redirect_url(),
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )

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
