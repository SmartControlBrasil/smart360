from django.test import TestCase

from apps.smart_system.models import CustomerEquipment, EquipmentModel
from apps.smart_system.services.tenant_scope import SmartSystemScopeService
from tests.factories.core import CompanyFactory
from tests.factories.smart_system import AssetCategoryFactory, MaintenanceClientFactory, OperationalSiteFactory


class EquipmentCatalogFlowTests(TestCase):
    def test_equipment_model_and_customer_equipment_creation_with_tenant_scope(self):
        company = CompanyFactory(slug="equip-catalog-co")
        client = MaintenanceClientFactory(company=company)
        site = OperationalSiteFactory(maintenance_client=client)
        category = AssetCategoryFactory(name="Compressores")

        equipment_model = EquipmentModel.objects.create(
            company=company,
            name="Compressor XYZ",
            category=category,
            manufacturer_code="CMP-XYZ",
        )

        customer_equipment = CustomerEquipment.objects.create(
            company=company,
            site=site,
            equipment_model=equipment_model,
            customer_tag="CE-001",
            display_name="Compressor linha 1",
        )

        self.assertIn(EquipmentModel, SmartSystemScopeService.COMPANY_FIELD_MAP)
        self.assertIn(CustomerEquipment, SmartSystemScopeService.COMPANY_FIELD_MAP)
        self.assertEqual(
            EquipmentModel.objects.filter(company=company).get().id,
            equipment_model.id,
        )
        self.assertEqual(
            CustomerEquipment.objects.filter(company=company).get().id,
            customer_equipment.id,
        )
        self.assertEqual(customer_equipment.equipment_model_id, equipment_model.id)
