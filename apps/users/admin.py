from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    ordering = ("email",)
    list_display = (
        "email",
        "display_name",
        "user_type",
        "is_active",
        "is_staff",
        "is_verified",
    )
    list_filter = ("user_type", "is_active", "is_staff", "is_verified")
    search_fields = ("email", "first_name", "last_name", "display_name", "phone_number")
    readonly_fields = ("public_id", "last_login", "last_login_at", "date_joined", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Profile",
            {
                "fields": (
                    "public_id",
                    "first_name",
                    "last_name",
                    "display_name",
                    "phone_number",
                    "job_title",
                    "department",
                    "user_type",
                )
            },
        ),
        ("Status", {"fields": ("is_active", "is_staff", "is_superuser", "is_verified")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "last_login_at", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )
