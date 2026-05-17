import factory
from django.core.files.base import ContentFile

from apps.knowledge_engine.models import (
    EquipmentReference,
    FailureReference,
    KnowledgeCategory,
    SymptomReference,
    TechnicalDocument,
    TroubleshootingArticle,
)
from tests.factories.core import UserFactory


class KnowledgeCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = KnowledgeCategory

    name = factory.Sequence(lambda n: f"Knowledge Category {n}")
    description = factory.Faker("sentence")
    is_active = True
    ordering = factory.Sequence(lambda n: n + 1)


class EquipmentReferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EquipmentReference

    name = factory.Sequence(lambda n: f"Equipment {n}")
    manufacturer = "SMART360"
    model = factory.Sequence(lambda n: f"Model-{n}")
    equipment_type = "treadmill"
    description = factory.Faker("sentence")
    is_active = True
    metadata = factory.LazyFunction(dict)


class SymptomReferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SymptomReference

    name = factory.Sequence(lambda n: f"Symptom {n}")
    description = factory.Faker("sentence")
    severity_level = SymptomReference.SeverityLevel.MEDIUM
    is_active = True


class FailureReferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FailureReference

    name = factory.Sequence(lambda n: f"Failure {n}")
    description = factory.Faker("sentence")
    failure_code = factory.Sequence(lambda n: f"FLR-{n:03d}")
    criticality = FailureReference.Criticality.MEDIUM
    is_active = True


class TroubleshootingArticleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TroubleshootingArticle

    title = factory.Sequence(lambda n: f"Troubleshooting Article {n}")
    category = factory.SubFactory(KnowledgeCategoryFactory)
    summary = factory.Faker("sentence")
    content = factory.Faker("paragraph")
    status = TroubleshootingArticle.Status.PUBLISHED
    created_by = factory.SubFactory(UserFactory)
    reviewed_by = factory.SubFactory(UserFactory)
    is_active = True


class TechnicalDocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicalDocument

    title = factory.Sequence(lambda n: f"Technical Document {n}")
    document_type = TechnicalDocument.DocumentType.MANUAL
    category = factory.SubFactory(KnowledgeCategoryFactory)
    equipment_reference = factory.SubFactory(EquipmentReferenceFactory)
    manufacturer = "SMART360"
    version = "1.0"
    summary = factory.Faker("sentence")
    status = TechnicalDocument.Status.PUBLISHED
    is_active = True
    created_by = factory.SubFactory(UserFactory)

    @factory.post_generation
    def file(self, create, extracted, **kwargs):
        if not create or self.file:
            return
        self.file.save("technical-document.txt", ContentFile(b"technical document"), save=True)

