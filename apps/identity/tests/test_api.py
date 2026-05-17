from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company, Membership
from apps.roles.models import Role
from apps.users.models import User

from ..models import AuthEventLog, CompanyInvitation, EmailVerificationRequest, PasswordResetRequest, UserSession


class IdentityApiTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123"
        self.user = User.objects.create_user(
            email="identity@smart360.local",
            password=self.password,
            first_name="Identity",
        )
        self.company = Company.objects.create(name="Identity Co", slug="identity-co", status=Company.Status.ACTIVE)
        self.role = Role.objects.create(code="company_admin", label="Company Admin", scope=Role.Scope.COMPANY, is_system=True)

    def _auth_header(self, token):
        return {"HTTP_AUTHORIZATION": f"Token {token}"}

    def test_login_creates_session_and_auth_event(self):
        response = self.client.post(
            reverse("auth-login"),
            {"email": self.user.email, "password": self.password, "device_label": "Chrome"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserSession.objects.filter(user=self.user, is_active=True).exists())
        self.assertTrue(AuthEventLog.objects.filter(user=self.user, event_type=AuthEventLog.EventType.LOGIN_SUCCEEDED).exists())

    def test_refresh_rotates_token(self):
        login_response = self.client.post(
            reverse("auth-login"),
            {"email": self.user.email, "password": self.password},
            format="json",
        )
        token = login_response.data["token"]
        response = self.client.post(reverse("auth-refresh"), {}, format="json", **self._auth_header(token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data["token"], token)

    def test_password_reset_request_and_confirm(self):
        request_response = self.client.post(
            reverse("auth-password-reset-request"),
            {"email": self.user.email},
            format="json",
        )
        self.assertEqual(request_response.status_code, status.HTTP_202_ACCEPTED)
        reset_request = PasswordResetRequest.objects.get(user=self.user)

        confirm_response = self.client.post(
            reverse("auth-password-reset-confirm"),
            {"token": reset_request.token, "new_password": "NewStrongPass123", "new_password_confirm": "NewStrongPass123"},
            format="json",
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_email_verification_flow(self):
        login_response = self.client.post(
            reverse("auth-login"),
            {"email": self.user.email, "password": self.password},
            format="json",
        )
        token = login_response.data["token"]
        request_response = self.client.post(reverse("auth-email-verification-request"), {}, format="json", **self._auth_header(token))
        self.assertEqual(request_response.status_code, status.HTTP_202_ACCEPTED)
        verification = EmailVerificationRequest.objects.get(user=self.user)

        confirm_response = self.client.post(
            reverse("auth-email-verification-confirm"),
            {"token": verification.token},
            format="json",
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_invitation_accept_creates_membership(self):
        inviter = User.objects.create_user(email="owner@smart360.local", password="StrongPass123", first_name="Owner")
        create_response = self.client.post(
            reverse("identity-invitations-list"),
            {
                "company": self.company.id,
                "invited_email": "invitee@smart360.local",
                "invited_role": self.role.id,
                "message": "Join the workspace",
            },
            format="json",
            HTTP_AUTHORIZATION="Token invalid",
        )
        self.assertEqual(create_response.status_code, status.HTTP_401_UNAUTHORIZED)

        login_response = self.client.post(
            reverse("auth-login"),
            {"email": inviter.email, "password": "StrongPass123"},
            format="json",
        )
        inviter_token = login_response.data["token"]
        create_response = self.client.post(
            reverse("identity-invitations-list"),
            {
                "company": self.company.id,
                "invited_email": "invitee@smart360.local",
                "invited_role": self.role.id,
                "message": "Join the workspace",
            },
            format="json",
            **self._auth_header(inviter_token),
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        invitation = CompanyInvitation.objects.get(invited_email="invitee@smart360.local")

        accept_response = self.client.post(
            reverse("identity-invitations-accept"),
            {
                "token": invitation.token,
                "first_name": "Invitee",
                "password": "InviteePass123",
            },
            format="json",
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        invited_user = User.objects.get(email="invitee@smart360.local")
        self.assertTrue(Membership.objects.filter(user=invited_user, company=self.company).exists())

