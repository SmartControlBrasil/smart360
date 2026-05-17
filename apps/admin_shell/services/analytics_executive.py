from apps.analytics_platform.models import OperationalMetrics
from apps.analytics_platform.services.analytics_service import ExecutiveAnalyticsService


def get_analytics_executive_context(*, user, tenant_context, filters=None):
    filters = filters or {}
    period_type = filters.get("period_type", OperationalMetrics.PeriodType.MONTHLY)
    company = tenant_context.get("company") or ExecutiveAnalyticsService.resolve_company_scope(user=user)
    if company is None:
        return {
            "company": None,
            "has_company_context": False,
            "dashboard_cards": [],
            "revenue_series": [],
            "profit_series": [],
            "top_clients": [],
            "top_contracts": [],
            "technician_leaderboard": [],
            "asset_analysis": [],
            "sla_summary": {},
            "analytics_alerts": [],
            "api_endpoints": [],
        }

    payload = ExecutiveAnalyticsService.build_executive_dashboard(
        company=company,
        period_type=period_type,
    )
    return {
        "company": company,
        "has_company_context": True,
        "dashboard_cards": payload["kpis"],
        "revenue_series": payload["revenue_series"],
        "profit_series": payload["profit_series"],
        "max_revenue_value": max((point["revenue"] for point in payload["revenue_series"]), default=1),
        "max_profit_value": max((point["profit"] for point in payload["profit_series"]), default=1),
        "top_clients": payload["top_clients"],
        "top_contracts": payload["top_contracts"],
        "technician_leaderboard": payload["technician_leaderboard"],
        "asset_analysis": payload["asset_analysis"],
        "sla_summary": payload["sla_summary"],
        "analytics_alerts": payload["alerts"],
        "analytics_period": payload["period"],
        "api_endpoints": [
            "/api/v1/analytics/executive/overview/",
            "/api/v1/analytics/revenue/",
            "/api/v1/analytics/profitability/",
            "/api/v1/analytics/technicians/",
            "/api/v1/analytics/assets/",
        ],
    }
