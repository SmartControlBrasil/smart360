from django.test import TestCase

from apps.marketplace_ecom.services.catalog_seed import seed_technical_catalog_from_static


class MarketplaceCatalogTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_technical_catalog_from_static()
