from django.test import TestCase

from apps.marketplace_ecom.models import TechnicalProduct
from apps.marketplace_ecom.services.catalog_seed import (
    catalog_entry_to_product_defaults,
    upsert_technical_product_from_catalog_entry,
)
from apps.marketplace_ecom.catalog import TECHNICAL_PRODUCTS


class CatalogSeedServiceTests(TestCase):
    def test_catalog_entry_maps_metadata_fields(self):
        entry = TECHNICAL_PRODUCTS[0]
        defaults = catalog_entry_to_product_defaults(entry, display_order=15)

        self.assertEqual(defaults["title"], entry["title"])
        self.assertEqual(defaults["metadata"]["product_type"], entry["product_type"])
        self.assertEqual(defaults["metadata"]["applications"], entry["applications"])
        self.assertEqual(defaults["metadata"]["catalog_image"], entry["image"])
        self.assertEqual(defaults["display_order"], 15)

    def test_upsert_does_not_duplicate_slug(self):
        entry = TECHNICAL_PRODUCTS[0]
        first, created_first = upsert_technical_product_from_catalog_entry(entry)
        second, created_second = upsert_technical_product_from_catalog_entry(entry)

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(TechnicalProduct.objects.filter(slug=entry["slug"]).count(), 1)
