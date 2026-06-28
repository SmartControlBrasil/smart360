from datetime import timedelta

import factory
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.smart_system.models import (
    Asset,
    AssetCategory,
    Checklist,
    ChecklistItem,
    FailureEvent,
    MaintenanceClient,
    MaintenanceContract,
    MaintenancePlan,
    OperationalSite,
    Part,
    RoutePlan,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    ServiceQuote,
    ScheduledVisit,
    StockMovement,
    TechnicianAvailabilityWindow,
    TechnicianSchedule,
    WorkLog,
)
from tests.factories.core import CompanyFactory, UserFactory


class MaintenanceClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MaintenanceClient

    company = factory.SubFactory(CompanyFactory)
    display_name = factory.Sequence(lambda n: f"Maintenance Client {n}")
    legal_name = factory.LazyAttribute(lambda obj: f"{obj.display_name} LTDA")
    document_number = factory.Sequence(lambda n: f"00.000.000/0001-{n:02d}")
    contact_name = factory.Faker("name")
    contact_email = factory.Sequence(lambda n: f"client{n}@smart360.local")
    contact_phone = factory.Sequence(lambda n: f"+55114020{n:04d}")
    is_active = True
    notes = factory.Faker("sentence")


class OperationalSiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OperationalSite

    maintenance_client = factory.SubFactory(MaintenanceClientFactory)
    name = factory.Sequence(lambda n: f"Operational Site {n}")
    code = factory.Sequence(lambda n: f"SITE-{n:03d}")
    address_line = "Rua Demo, 100"
    city = "Sao Paulo"
    state = "SP"
    zip_code = "01000-000"
    contact_name = factory.Faker("name")
    contact_phone = factory.Sequence(lambda n: f"+55113020{n:04d}")
    is_active = True


class AssetCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetCategory

    name = factory.Sequence(lambda n: f"Asset Category {n}")
    description = factory.Faker("sentence")
    is_active = True


class AssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asset

    operational_site = factory.SubFactory(OperationalSiteFactory)
    category = factory.SubFactory(AssetCategoryFactory)
    asset_tag = factory.Sequence(lambda n: f"AST-{n:05d}")
    name = factory.Sequence(lambda n: f"Asset {n}")
    manufacturer = "SMART360"
    model = "Model X"
    status = Asset.Status.OPERATING
    criticality = Asset.Criticality.MEDIUM
    is_active = True
    metadata = factory.LazyFunction(dict)


class ServiceOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceOrder

    class Params:
        company = factory.SubFactory(CompanyFactory)

    order_number = factory.Sequence(lambda n: f"SO-{n:05d}")
    client = factory.SubFactory(MaintenanceClientFactory, company=factory.SelfAttribute("..company"))
    operational_site = factory.SubFactory(OperationalSiteFactory, maintenance_client=factory.SelfAttribute("..client"))
    asset = factory.SubFactory(AssetFactory, operational_site=factory.SelfAttribute("..operational_site"))
    maintenance_type = ServiceOrder.MaintenanceType.CORRECTIVE
    priority = ServiceOrder.Priority.MEDIUM
    status = ServiceOrder.Status.OPEN
    source = ServiceOrder.Source.MANUAL
    title = factory.Sequence(lambda n: f"Service Order {n}")
    description = factory.Faker("sentence")
    scheduled_start = factory.LazyFunction(timezone.now)
    scheduled_end = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=2))
    requested_by = "pytest"
    assigned_to = factory.SubFactory(UserFactory)
    created_by = factory.SubFactory(UserFactory)
    notes = factory.Faker("sentence")


class FailureEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FailureEvent

    asset = factory.SubFactory(AssetFactory)
    service_order = factory.SubFactory(ServiceOrderFactory)
    detected_at = factory.LazyFunction(timezone.now)
    symptom = "Motor nao parte"
    probable_cause = "Capacitor"
    root_cause = "Capacitor defeituoso"
    severity = FailureEvent.Severity.HIGH
    downtime_minutes = 30
    status = FailureEvent.Status.ANALYZING
    notes = factory.Faker("sentence")


class ChecklistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Checklist

    company = factory.LazyAttribute(lambda obj: obj.operational_site.maintenance_client.company)
    operational_site = factory.SubFactory(OperationalSiteFactory)
    name = factory.Sequence(lambda n: f"Checklist {n}")
    description = factory.Faker("sentence")
    is_active = True


class ChecklistItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChecklistItem

    checklist = factory.SubFactory(ChecklistFactory)
    title = factory.Sequence(lambda n: f"Item {n}")
    description = factory.Faker("sentence")
    item_type = ChecklistItem.ItemType.BOOLEAN
    ordering = factory.Sequence(lambda n: n + 1)
    is_required = True
    is_active = True


class MaintenancePlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MaintenancePlan

    asset = factory.SubFactory(AssetFactory)
    company = factory.LazyAttribute(lambda obj: obj.asset.operational_site.maintenance_client.company)
    operational_site = factory.LazyAttribute(lambda obj: obj.asset.operational_site)
    checklist = factory.LazyAttribute(lambda obj: ChecklistFactory(operational_site=obj.operational_site, company=obj.company))
    name = factory.Sequence(lambda n: f"Plano Preventivo {n}")
    description = factory.Faker("sentence")
    frequency_type = MaintenancePlan.FrequencyType.MONTHLY
    frequency_value = 1
    estimated_duration_minutes = 90
    is_active = True
    notes = factory.Faker("sentence")
    next_due_date = factory.LazyFunction(lambda: timezone.localdate())


class MaintenanceContractFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MaintenanceContract

    company = factory.SubFactory(CompanyFactory)
    client = factory.SubFactory(MaintenanceClientFactory, company=factory.SelfAttribute("..company"))
    operational_site = factory.SubFactory(OperationalSiteFactory, maintenance_client=factory.SelfAttribute("..client"))
    contract_number = factory.Sequence(lambda n: f"MCT-{n:05d}")
    start_date = factory.LazyFunction(timezone.localdate)
    status = MaintenanceContract.Status.ACTIVE
    billing_frequency = MaintenanceContract.BillingFrequency.MONTHLY
    contract_value = 1000
    auto_generate_preventives = True
    metadata = factory.LazyFunction(dict)


class ServiceOrderChecklistResponseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceOrderChecklistResponse

    service_order = factory.SubFactory(ServiceOrderFactory)
    checklist_item = factory.SubFactory(ChecklistItemFactory)
    response_boolean = True
    response_text = ""
    response_choice = ""
    notes = factory.Faker("sentence")


class WorkLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkLog

    service_order = factory.SubFactory(ServiceOrderFactory)
    user = factory.SubFactory(UserFactory)
    started_at = factory.LazyFunction(timezone.now)
    ended_at = factory.LazyAttribute(lambda obj: obj.started_at + timedelta(minutes=obj.labor_minutes))
    labor_minutes = 120
    notes = factory.Faker("sentence")


class PartFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Part

    company = factory.SubFactory(CompanyFactory)
    operational_site = factory.SubFactory(OperationalSiteFactory, maintenance_client__company=factory.SelfAttribute("..company"))
    code = factory.Sequence(lambda n: f"PART-{n:05d}")
    name = factory.Sequence(lambda n: f"Peca {n}")
    unit = "un"
    unit_cost = 120
    current_stock = 10
    minimum_stock = 1
    status = Part.Status.ACTIVE
    metadata = factory.LazyFunction(dict)


class StockMovementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StockMovement

    company = factory.SubFactory(CompanyFactory)
    operational_site = factory.SubFactory(OperationalSiteFactory, maintenance_client__company=factory.SelfAttribute("..company"))
    part = factory.SubFactory(PartFactory, company=factory.SelfAttribute("..company"), operational_site=factory.SelfAttribute("..operational_site"))
    service_order = factory.SubFactory(ServiceOrderFactory, client__company=factory.SelfAttribute("..company"), operational_site=factory.SelfAttribute("..operational_site"))
    movement_type = StockMovement.MovementType.OUTBOUND
    quantity = 1
    performed_by = factory.SubFactory(UserFactory)


class ServiceQuoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceQuote

    company = factory.SubFactory(CompanyFactory)
    operational_site = factory.SubFactory(OperationalSiteFactory, maintenance_client__company=factory.SelfAttribute("..company"))
    work_order = factory.SubFactory(ServiceOrderFactory, client__company=factory.SelfAttribute("..company"), operational_site=factory.SelfAttribute("..operational_site"))
    asset = factory.LazyAttribute(lambda obj: obj.work_order.asset)
    quote_number = factory.Sequence(lambda n: f"QTE-{n:05d}")
    status = ServiceQuote.Status.APPROVED
    total_parts = 0
    total_labor = 0
    total_value = 500
    approved_at = factory.LazyFunction(timezone.now)
    metadata = factory.LazyFunction(dict)


class TechnicianAvailabilityWindowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianAvailabilityWindow

    company = factory.SubFactory(CompanyFactory)
    operational_site = factory.SubFactory(OperationalSiteFactory, maintenance_client__company=factory.SelfAttribute("..company"))
    technician = factory.SubFactory(UserFactory)
    weekday = factory.LazyFunction(lambda: timezone.localdate().isoweekday())
    start_time = timezone.datetime.strptime("08:00", "%H:%M").time()
    end_time = timezone.datetime.strptime("18:00", "%H:%M").time()
    is_available = True
    max_daily_jobs = 6
    max_daily_hours = 8
    notes = factory.Faker("sentence")
    metadata = factory.LazyFunction(dict)


class TechnicianScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianSchedule

    company = factory.SubFactory(CompanyFactory)
    operational_site = factory.SubFactory(OperationalSiteFactory, maintenance_client__company=factory.SelfAttribute("..company"))
    technician = factory.SubFactory(UserFactory)
    date = factory.LazyFunction(timezone.localdate)
    total_jobs = 0
    total_estimated_duration = 0
    total_estimated_travel = 0
    total_conflicts = 0
    notes = factory.Faker("sentence")
    metadata = factory.LazyFunction(dict)


class RoutePlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RoutePlan

    company = factory.SubFactory(CompanyFactory)
    operational_site = factory.SubFactory(OperationalSiteFactory, maintenance_client__company=factory.SelfAttribute("..company"))
    technician = factory.SubFactory(UserFactory)
    date = factory.LazyFunction(timezone.localdate)
    total_stops = 0
    total_estimated_duration = 0
    total_estimated_travel = 0
    optimization_status = RoutePlan.OptimizationStatus.GENERATED
    route_summary = factory.LazyFunction(dict)
    notes = factory.Faker("sentence")


class ScheduledVisitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduledVisit

    company = factory.SubFactory(CompanyFactory)
    operational_site = factory.SubFactory(OperationalSiteFactory, maintenance_client__company=factory.SelfAttribute("..company"))
    asset = factory.SubFactory(AssetFactory, operational_site=factory.SelfAttribute("..operational_site"))
    work_order = factory.SubFactory(ServiceOrderFactory, client__company=factory.SelfAttribute("..company"), operational_site=factory.SelfAttribute("..operational_site"), asset=factory.SelfAttribute("..asset"))
    technician = factory.SubFactory(UserFactory)
    technician_schedule = None
    route_plan = None
    source_type = ScheduledVisit.SourceType.WORK_ORDER
    title = factory.Sequence(lambda n: f"Visita {n}")
    scheduled_date = factory.LazyFunction(timezone.localdate)
    scheduled_start = factory.LazyFunction(timezone.now)
    scheduled_end = factory.LazyAttribute(lambda obj: obj.scheduled_start + timedelta(minutes=obj.estimated_duration_minutes))
    estimated_duration_minutes = 90
    estimated_travel_minutes = 20
    priority = ScheduledVisit.Priority.MEDIUM
    status = ScheduledVisit.Status.SCHEDULED
    route_order = factory.Sequence(lambda n: n + 1)
    city = "Sao Paulo"
    state = "SP"
    location_label = factory.LazyAttribute(lambda obj: obj.operational_site.name)
    conflict_flags = factory.LazyFunction(list)
    notes = factory.Faker("sentence")
    metadata = factory.LazyFunction(dict)
