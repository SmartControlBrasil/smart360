import factory

from apps.backoffice.models import BackofficeAlert, BackofficeQueue, BackofficeTask
from tests.factories.core import UserFactory


class BackofficeQueueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BackofficeQueue

    name = factory.Sequence(lambda n: f"Queue {n}")
    queue_type = BackofficeQueue.QueueType.OPERATIONAL
    source_module = "smart_system"
    description = factory.Faker("sentence")
    is_active = True
    ordering = factory.Sequence(lambda n: n + 1)


class BackofficeAlertFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BackofficeAlert

    title = factory.Sequence(lambda n: f"Alert {n}")
    alert_type = BackofficeAlert.AlertType.OPERATIONAL
    source_module = "billing"
    severity = BackofficeAlert.Severity.WARNING
    status = BackofficeAlert.Status.OPEN
    summary = factory.Faker("sentence")
    details = factory.Faker("paragraph")


class BackofficeTaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BackofficeTask

    title = factory.Sequence(lambda n: f"Task {n}")
    task_type = BackofficeTask.TaskType.REVIEW
    source_module = "backoffice"
    assigned_to = factory.SubFactory(UserFactory)
    status = BackofficeTask.Status.PENDING
    priority = BackofficeTask.Priority.MEDIUM
    notes = factory.Faker("sentence")

