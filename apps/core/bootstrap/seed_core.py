from __future__ import annotations

from django.utils import timezone

from apps.audit.models import AuditLog
from apps.companies.models import Company, Membership
from apps.core.models import SystemModule
from apps.identity.models import (
    AuthEventLog,
    CompanyInvitation,
    EmailVerificationRequest,
    OnboardingProfile,
    UserSession,
)
from apps.roles.models import Role
from apps.users.models import User

from .common import metadata_payload, set_password


def seed_core_platform(ctx):
    ctx.section("Seeding core platform")

    role_specs = [
        ("platform_admin", "Platform Admin", Role.Scope.PLATFORM),
        ("company_admin", "Company Admin", Role.Scope.COMPANY),
        ("operations", "Operations", Role.Scope.COMPANY),
        ("sales", "Sales", Role.Scope.COMPANY),
        ("engineering", "Engineering", Role.Scope.COMPANY),
    ]
    for code, label, scope in role_specs:
        role, _ = Role.objects.update_or_create(
            code=code,
            defaults={
                "label": label,
                "scope": scope,
                "description": f"Bootstrap role {label}",
                "is_system": True,
                "is_active": True,
                "metadata": metadata_payload(scope=scope),
            },
        )
        ctx.put("roles", code, role)

    module_specs = [
        ("core_platform", "Core Platform"),
        ("smart_site_factory", "Smart Site Factory"),
        ("growth_engine", "Growth Engine"),
        ("market_core", "Market Core"),
        ("caneca_de_garagem", "Caneca de Garagem"),
        ("smart_system", "Smart System"),
        ("marketplace_technicians", "Marketplace Technicians"),
        ("marketplace_analytical", "Marketplace Analytical"),
        ("knowledge_engine", "Knowledge Engine"),
        ("analytics_platform", "Analytics Platform"),
        ("integration_bus", "Integration Bus"),
        ("billing", "Billing"),
        ("notification_center", "Notification Center"),
        ("backoffice", "Backoffice"),
        ("files_center", "Files Center"),
        ("global_search", "Global Search"),
        ("reporting_center", "Reporting Center"),
        ("configuration_center", "Configuration Center"),
        ("scheduling_center", "Scheduling Center"),
        ("ai_automation_center", "AI Automation Center"),
    ]
    for code, name in module_specs:
        SystemModule.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": f"{name} bootstrap module", "is_active": True},
        )

    company_specs = [
        ("smart360-internal", "Smart360 Internal", "Smart360 Internal LTDA"),
        ("caneca-de-garagem", "Caneca de Garagem", "Caneca de Garagem Personalizados LTDA"),
        ("smart-control-brasil", "Smart Control Brasil", "Smart Control Brasil Engenharia LTDA"),
        ("laboratorio-exemplo", "Laboratorio Exemplo", "Laboratorio Exemplo Diagnosticos LTDA"),
        ("academia-exemplo", "Academia Exemplo", "Academia Exemplo Fitness LTDA"),
        ("panobianco", "Panobianco", "Panobianco Operacoes Fitness LTDA"),
    ]
    for slug, name, legal_name in company_specs:
        company, _ = Company.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "legal_name": legal_name,
                "status": Company.Status.ACTIVE,
                "email": f"contato@{slug}.local".replace("-",""),
                "phone_number": "+55 11 99999-0000",
                "website": f"https://{slug}.smart360.local",
                "metadata": metadata_payload(company_slug=slug),
            },
        )
        ctx.put("companies", slug, company)

    user_specs = [
        ("admin@smart360.local", "Admin", "Master", User.UserType.INTERNAL, True, True),
        ("ops@smart360.local", "Ops", "Center", User.UserType.INTERNAL, True, False),
        ("comercial@smart360.local", "Comercial", "Team", User.UserType.INTERNAL, True, False),
        ("engenharia@smart360.local", "Engenharia", "Team", User.UserType.INTERNAL, True, False),
        ("cliente@academia.local", "Cliente", "Academia", User.UserType.CLIENT, False, False),
    ]
    for email, first_name, last_name, user_type, is_staff, is_superuser in user_specs:
        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "user_type": user_type,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
                "is_active": True,
                "is_verified": True,
                "phone_number": "+55 11 98888-0000",
                "department": "Bootstrap",
                "job_title": "Demo User",
            },
        )
        set_password(user, ctx.demo_password)
        ctx.put("users", email, user)

    membership_specs = [
        ("admin@smart360.local", "smart360-internal", ["platform_admin", "company_admin"]),
        ("ops@smart360.local", "smart360-internal", ["operations"]),
        ("comercial@smart360.local", "smart360-internal", ["sales"]),
        ("engenharia@smart360.local", "smart360-internal", ["engineering"]),
        ("cliente@academia.local", "academia-exemplo", ["company_admin"]),
        ("ops@smart360.local", "academia-exemplo", ["operations"]),
        ("ops@smart360.local", "panobianco", ["operations"]),
        ("engenharia@smart360.local", "academia-exemplo", ["engineering"]),
        ("engenharia@smart360.local", "panobianco", ["engineering"]),
        ("engenharia@smart360.local", "smart-control-brasil", ["engineering"]),
    ]
    for user_email, company_slug, roles in membership_specs:
        membership, _ = Membership.objects.update_or_create(
            user=ctx.get("users", user_email),
            company=ctx.get("companies", company_slug),
            defaults={
                "status": Membership.Status.ACTIVE,
                "is_primary": True,
                "joined_at": timezone.now(),
                "metadata": metadata_payload(source="bootstrap"),
            },
        )
        membership.roles.set([ctx.get("roles", code) for code in roles])

    for email in ["admin@smart360.local", "ops@smart360.local", "comercial@smart360.local", "engenharia@smart360.local"]:
        user = ctx.get("users", email)
        OnboardingProfile.objects.update_or_create(
            user=user,
            defaults={
                "onboarding_status": OnboardingProfile.Status.COMPLETED,
                "current_step": "completed",
                "profile_completed": True,
                "company_setup_completed": True,
                "email_verified": True,
                "accepted_terms_at": timezone.now(),
                "completed_at": timezone.now(),
                "metadata": metadata_payload(),
            },
        )
        UserSession.objects.update_or_create(
            user=user,
            device_label="Bootstrap Browser",
            defaults={
                "session_key": f"bootstrap-{user.id}",
                "token_identifier": f"bootstrap-token-{user.id}",
                "ip_address": "127.0.0.1",
                "user_agent": "SMART360 Bootstrap",
                "is_active": True,
                "last_seen_at": timezone.now(),
            },
        )
        EmailVerificationRequest.objects.update_or_create(
            user=user,
            email_snapshot=user.email,
            defaults={
                "status": EmailVerificationRequest.Status.VERIFIED,
                "requested_at": timezone.now(),
                "verified_at": timezone.now(),
            },
        )
        AuthEventLog.objects.create(
            user=user,
            event_type=AuthEventLog.EventType.LOGIN_SUCCEEDED,
            success=True,
            metadata=metadata_payload(email=user.email),
        )

    CompanyInvitation.objects.update_or_create(
        company=ctx.get("companies", "smart360-internal"),
        invited_email="demo-invite@smart360.local",
        defaults={
            "invited_role": ctx.get("roles", "operations"),
            "invited_by": ctx.get("users", "admin@smart360.local"),
            "status": CompanyInvitation.Status.PENDING,
            "message": "Bootstrap invitation for local demo.",
        },
    )

    AuditLog.objects.create(
        user=ctx.get("users", "admin@smart360.local"),
        company=ctx.get("companies", "smart360-internal"),
        action="bootstrap_completed",
        entity="core_platform",
        entity_id="bootstrap",
        payload=metadata_payload(),
    )
