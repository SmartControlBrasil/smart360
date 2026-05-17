from django.core.management.base import BaseCommand
from drf_spectacular.generators import SchemaGenerator


class Command(BaseCommand):
    help = "Valida a geracao basica do schema OpenAPI do SMART360."

    def handle(self, *args, **options):
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)
        paths_count = len((schema or {}).get("paths", {}))
        tags_count = len((schema or {}).get("tags", []))
        self.stdout.write(self.style.SUCCESS(f"Schema gerado com {paths_count} paths e {tags_count} tags."))

