import logging
from time import perf_counter

from apps.companies.services.tenant_scope import TenantScopeService
from apps.observability_center.services.observability_service import ErrorIncidentService, RequestTraceService
from shared_kernel.observability.context import clear_request_context, set_correlation_id, set_request_context, set_request_id


logger = logging.getLogger("smart360.request")


class CorrelationIdMiddleware:
    header_name = "HTTP_X_CORRELATION_ID"
    response_header = "X-Correlation-ID"
    request_header_name = "HTTP_X_REQUEST_ID"
    request_response_header = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = perf_counter()
        correlation_id = set_correlation_id(request.META.get(self.header_name))
        request_id = set_request_id(request.META.get(self.request_header_name) or correlation_id)
        request.correlation_id = correlation_id
        request.request_id = request_id

        company = None
        site = None
        if getattr(request, "user", None) and getattr(request.user, "is_authenticated", False):
            tenant_context = TenantScopeService.resolve_context(request)
            company = tenant_context.company
            site = tenant_context.site

        set_request_context(
            correlation_id=correlation_id,
            request_id=request_id,
            user=getattr(request, "user", None) if getattr(getattr(request, "user", None), "is_authenticated", False) else None,
            user_id=getattr(getattr(request, "user", None), "id", ""),
            company=company,
            company_id=getattr(company, "id", ""),
            site=site,
            site_id=getattr(site, "id", ""),
            path=request.path,
            method=request.method,
            module=request.resolver_match.namespace if getattr(request, "resolver_match", None) else "",
            origin="http",
        )

        try:
            response = self.get_response(request)
        except Exception as exc:  # pragma: no cover - defensive runtime path
            duration_ms = max(int((perf_counter() - started_at) * 1000), 0)
            logger.exception(
                "request failed",
                extra={
                    "event": "http.request.failed",
                    "module_name": getattr(getattr(request, "resolver_match", None), "namespace", ""),
                    "payload": {"path": request.path, "method": request.method, "duration_ms": duration_ms},
                },
            )
            ErrorIncidentService.register_error_incident(
                incident_key=f"http:{request.method}:{request.path}",
                source_module="http",
                error_type=exc.__class__.__name__,
                message=f"Unhandled exception on {request.method} {request.path}",
                severity="high",
                traceback_text="",
                payload={"path": request.path, "method": request.method},
            )
            RequestTraceService.record_request(
                request_id=request_id,
                correlation_id=correlation_id,
                method=request.method,
                path=request.path,
                status_code=500,
                duration_ms=duration_ms,
                user=getattr(request, "user", None) if getattr(getattr(request, "user", None), "is_authenticated", False) else None,
                company=company,
                site=site,
                source_module=getattr(getattr(request, "resolver_match", None), "namespace", ""),
                ip_address=request.META.get("REMOTE_ADDR", ""),
                query_params=dict(request.GET),
            )
            clear_request_context()
            raise

        duration_ms = max(int((perf_counter() - started_at) * 1000), 0)
        response[self.response_header] = correlation_id
        response[self.request_response_header] = request_id
        if (
            (company is None or site is None)
            and getattr(request, "user", None)
            and getattr(request.user, "is_authenticated", False)
            and request.path.startswith("/api/public/")
        ):
            try:
                from apps.public_api.services.scoping import PublicApiScopeService

                public_scope = PublicApiScopeService.resolve_scope(request)
                company = company or public_scope.company
                site = site or public_scope.site
            except Exception:
                pass
        RequestTraceService.record_request(
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user=getattr(request, "user", None) if getattr(getattr(request, "user", None), "is_authenticated", False) else None,
            company=company,
            site=site,
            source_module=getattr(getattr(request, "resolver_match", None), "namespace", ""),
            ip_address=request.META.get("REMOTE_ADDR", ""),
            query_params=dict(request.GET),
        )
        logger.info(
            "request completed",
            extra={
                "event": "http.request.completed",
                "payload": {"path": request.path, "method": request.method, "status_code": response.status_code, "duration_ms": duration_ms},
            },
        )
        clear_request_context()
        return response
