from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.market_core.models import MarketplaceOrderItem, MarketplaceProduct, MarketplaceVendor
from tests.factories.market_core import (
    MarketplaceOrderFactory,
    MarketplaceOrderItemFactory,
    MarketplaceProductFactory,
    MarketplaceVendorFactory,
)


class MarketplaceCoreModelTests(TestCase):
    def test_vendor_and_product_creation(self):
        vendor = MarketplaceVendorFactory(name="Factory Vendor")
        product = MarketplaceProductFactory(vendor=vendor, sku="SKU-TEST-001")

        self.assertEqual(product.vendor_id, vendor.id)
        self.assertTrue(product.is_active)
        self.assertEqual(str(vendor), "Factory Vendor")

    def test_order_item_calculates_total_price_on_save(self):
        order = MarketplaceOrderFactory(total_amount=Decimal("0.00"))
        product = MarketplaceProductFactory(base_price=Decimal("50.00"))
        item = MarketplaceOrderItemFactory(
            order=order,
            product=product,
            quantity=3,
            unit_price=Decimal("50.00"),
        )

        self.assertEqual(item.total_price, Decimal("150.00"))
        self.assertEqual(item.vendor_id, product.vendor_id)

    def test_product_sku_must_be_unique(self):
        MarketplaceProductFactory(sku="UNIQUE-SKU")
        with self.assertRaises(IntegrityError):
            MarketplaceProduct.objects.create(
                vendor=MarketplaceVendorFactory(),
                name="Duplicate SKU Product",
                slug="duplicate-sku-product",
                sku="UNIQUE-SKU",
            )
