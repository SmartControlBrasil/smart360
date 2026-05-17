from drf_spectacular.utils import OpenApiExample


LOGIN_REQUEST_EXAMPLE = OpenApiExample(
    "Login request",
    value={"email": "admin@smart360.local", "password": "admin123!", "device_label": "Chrome Mac"},
    request_only=True,
)

LOGIN_RESPONSE_EXAMPLE = OpenApiExample(
    "Login response",
    value={
        "token": "tok_demo_123",
        "user": {
            "id": 1,
            "public_id": "7d6b8760-f0d5-4b4e-9f7e-6d61ec3e4ab1",
            "email": "admin@smart360.local",
            "first_name": "SMART360",
            "last_name": "Admin",
        },
    },
    response_only=True,
)

VALIDATION_ERROR_EXAMPLE = OpenApiExample(
    "Validation error",
    value={"new_password_confirm": ["Passwords do not match."]},
    response_only=True,
)

UNAUTHORIZED_EXAMPLE = OpenApiExample(
    "Unauthorized",
    value={"detail": "Authentication credentials were not provided."},
    response_only=True,
)

FORBIDDEN_EXAMPLE = OpenApiExample(
    "Forbidden",
    value={"detail": "You do not have permission to perform this action."},
    response_only=True,
)

NOT_FOUND_EXAMPLE = OpenApiExample(
    "Not found",
    value={"detail": "Not found."},
    response_only=True,
)

