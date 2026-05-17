import contextvars
import uuid


_correlation_id_var = contextvars.ContextVar("smart360_correlation_id", default="")
_request_id_var = contextvars.ContextVar("smart360_request_id", default="")
_request_meta_var = contextvars.ContextVar("smart360_request_meta", default={})


def get_correlation_id() -> str:
    return _correlation_id_var.get("")


def get_request_id() -> str:
    return _request_id_var.get("")


def set_correlation_id(value: str | None = None) -> str:
    correlation_id = value or str(uuid.uuid4())
    _correlation_id_var.set(correlation_id)
    return correlation_id


def set_request_id(value: str | None = None) -> str:
    request_id = value or str(uuid.uuid4())
    _request_id_var.set(request_id)
    return request_id


def set_request_context(**kwargs):
    current = dict(_request_meta_var.get({}))
    current.update({key: value for key, value in kwargs.items() if value not in (None, "")})
    _request_meta_var.set(current)
    return current


def get_request_context():
    context = dict(_request_meta_var.get({}))
    if "correlation_id" not in context and get_correlation_id():
        context["correlation_id"] = get_correlation_id()
    if "request_id" not in context and get_request_id():
        context["request_id"] = get_request_id()
    return context


def clear_request_context():
    _request_meta_var.set({})
    _correlation_id_var.set("")
    _request_id_var.set("")
