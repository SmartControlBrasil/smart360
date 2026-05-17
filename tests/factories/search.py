import factory

from apps.global_search.models import SearchIndexEntry


class SearchIndexEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SearchIndexEntry

    source_module = "smart_system"
    item_type = "service_order"
    item_id = factory.Sequence(lambda n: str(n + 1))
    title = factory.Sequence(lambda n: f"Indexed Item {n}")
    subtitle = factory.Faker("sentence")
    body_text = factory.Faker("paragraph")
    search_text = factory.Faker("paragraph")
    status = "open"
    category = "operations"
    url_path = factory.Sequence(lambda n: f"/app/resource/{n}")
    metadata = factory.LazyFunction(dict)
    is_active = True

