from __future__ import annotations

from apps.core.bootstrap.seed_business import seed_growth, seed_marketplaces, seed_smart_site_factory
from apps.core.bootstrap.seed_core import seed_core_platform
from apps.core.bootstrap.seed_operations import (
    seed_knowledge,
    seed_marketplace_analytical,
    seed_marketplace_technicians,
    seed_smart_system,
)
from apps.core.bootstrap.seed_transversal import (
    seed_ai_automation,
    seed_ai_agents_center,
    seed_analytics,
    seed_backoffice,
    seed_billing,
    seed_configuration,
    seed_files_center,
    seed_global_search,
    seed_notification_center,
    seed_reporting,
    seed_scheduling,
    seed_smart_system_access_control,
)


SEED_SEQUENCE = [
    ("core_platform", seed_core_platform),
    ("files_center", seed_files_center),
    ("smart_site_factory", seed_smart_site_factory),
    ("growth_engine", seed_growth),
    ("marketplaces", seed_marketplaces),
    ("smart_system", seed_smart_system),
    ("marketplace_technicians", seed_marketplace_technicians),
    ("marketplace_analytical", seed_marketplace_analytical),
    ("knowledge_engine", seed_knowledge),
    ("analytics_platform", seed_analytics),
    ("billing", seed_billing),
    ("notification_center", seed_notification_center),
    ("backoffice", seed_backoffice),
    ("global_search", seed_global_search),
    ("reporting_center", seed_reporting),
    ("configuration_center", seed_configuration),
    ("scheduling_center", seed_scheduling),
    ("ai_automation_center", seed_ai_automation),
    ("ai_agents_center", seed_ai_agents_center),
    ("smart_system_access_control", seed_smart_system_access_control),
]


def run_bootstrap(ctx):
    for _, seeder in SEED_SEQUENCE:
        seeder(ctx)
    ctx.log("[bootstrap] Optional modules not installed and skipped: trust_and_safety, crm_center")
