import factory

from apps.notification_center.models import InAppNotification, NotificationChannel, NotificationMessage, NotificationTemplate
from tests.factories.core import CompanyFactory, UserFactory


class NotificationChannelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationChannel

    name = factory.Sequence(lambda n: f"Channel {n}")
    channel_type = NotificationChannel.ChannelType.IN_APP
    description = factory.Faker("sentence")
    is_active = True
    config_json = factory.LazyFunction(dict)


class NotificationTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationTemplate

    name = factory.Sequence(lambda n: f"Template {n}")
    channel = factory.SubFactory(NotificationChannelFactory)
    template_key = factory.Sequence(lambda n: f"template_key_{n}")
    subject_template = "Subject"
    body_template = "Body {{ value }}"
    description = factory.Faker("sentence")
    is_active = True
    metadata = factory.LazyFunction(dict)


class NotificationMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationMessage

    event_key = "service_order_created"
    channel = factory.SubFactory(NotificationChannelFactory)
    template = factory.SubFactory(NotificationTemplateFactory)
    recipient_user = factory.SubFactory(UserFactory)
    recipient_company = factory.SubFactory(CompanyFactory)
    recipient_address = factory.Sequence(lambda n: f"dest{n}@smart360.local")
    subject_rendered = "Rendered subject"
    body_rendered = "Rendered body"
    payload = factory.LazyFunction(dict)
    status = NotificationMessage.Status.PENDING


class InAppNotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InAppNotification

    user = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"InApp Notification {n}")
    body = factory.Faker("sentence")
    notification_type = InAppNotification.NotificationType.INFO
    status = InAppNotification.Status.UNREAD

