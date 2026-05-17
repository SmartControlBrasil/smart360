import factory

from apps.reporting_center.models import ReportRequest, ReportTemplate
from tests.factories.core import CompanyFactory, UserFactory


class ReportTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportTemplate

    name = factory.Sequence(lambda n: f"Report Template {n}")
    source_module = "smart_system"
    report_type = ReportTemplate.ReportType.OPERATIONAL
    description = factory.Faker("sentence")
    output_format_default = ReportTemplate.OutputFormat.JSON
    config_json = factory.LazyFunction(dict)
    is_active = True


class ReportRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportRequest

    template = factory.SubFactory(ReportTemplateFactory)
    requested_by = factory.SubFactory(UserFactory)
    requested_for_company = factory.SubFactory(CompanyFactory)
    source_module = "smart_system"
    status = ReportRequest.Status.PENDING
    output_format = ReportRequest.OutputFormat.JSON
    filters_json = factory.LazyFunction(dict)

