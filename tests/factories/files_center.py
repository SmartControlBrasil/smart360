import factory
from django.core.files.base import ContentFile

from apps.files_center.models import FileCategory, FileLink, StoredFile
from tests.factories.core import UserFactory


class FileCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileCategory

    name = factory.Sequence(lambda n: f"File Category {n}")
    description = factory.Faker("sentence")
    is_active = True
    ordering = factory.Sequence(lambda n: n + 1)


class StoredFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StoredFile

    original_name = factory.Sequence(lambda n: f"file-{n}.txt")
    mime_type = "text/plain"
    category = factory.SubFactory(FileCategoryFactory)
    storage_backend = StoredFile.StorageBackend.LOCAL
    visibility = StoredFile.Visibility.INTERNAL
    is_active = True
    uploaded_by = factory.SubFactory(UserFactory)
    metadata = factory.LazyFunction(dict)

    @factory.post_generation
    def file(self, create, extracted, **kwargs):
        if not create or self.file:
            return
        self.file.save(self.original_name, ContentFile(b"file content"), save=True)


class FileLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileLink

    stored_file = factory.SubFactory(StoredFileFactory)
    related_module = "smart_system"
    related_item_type = "service_order"
    related_item_id = "1"
    relation_type = "attachment"
    is_primary = True

