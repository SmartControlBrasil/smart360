from rest_framework.views import exception_handler

from shared_kernel.observability.context import get_request_id


def smart360_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    payload = {
        "error": {
            "code": getattr(exc, "default_code", "error"),
            "detail": response.data.get("detail", response.data),
            "status_code": response.status_code,
            "request_id": get_request_id(),
        }
    }
    if isinstance(response.data, dict) and "detail" not in response.data:
        payload["error"]["fields"] = response.data
    response.data = payload
    return response

