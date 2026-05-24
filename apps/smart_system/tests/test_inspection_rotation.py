from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.companies.models import Company

from apps.smart_system.models import (
    Asset,
    AssetCategory,
    Checklist,
    InspectionDivision,
    InspectionDivisionEquipment,
    MaintenanceClient,
    OperationalSite,
    PreventiveInspectionRoutine,
)
from apps.smart_system.services.inspection_routine_service import get_next_eligible_inspection_division


class InspectionRotationPhase1Tests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Empresa Alfa", slug="empresa-alfa")
        self.mc = MaintenanceClient.objects.create(display_name="Cliente Alfa", company=self.company)
        self.site = OperationalSite.objects.create(maintenance_client=self.mc, name="Unidade 01")
        self.checklist = Checklist.objects.create(
            company=self.company,
            operational_site=self.site,
            name="Checklist teste",
            is_active=True,
        )
        self.category = AssetCategory.objects.create(name="Categoria demo")
        self.asset = Asset.objects.create(
            operational_site=self.site,
            category=self.category,
            asset_tag="TAG-001",
            name="Equipamento 1",
        )

    def test_create_routine(self):
        routine = PreventiveInspectionRoutine.objects.create(
            company=self.company,
            operational_site=self.site,
            checklist=self.checklist,
            name="Rotina mensal",
            is_active=True,
        )
        self.assertEqual(routine.operational_site_id, self.site.id)
        self.assertTrue(routine.pk)

    def test_divisions_ordered(self):
        routine = PreventiveInspectionRoutine.objects.create(
            company=self.company,
            operational_site=self.site,
            checklist=self.checklist,
            name="Rotina",
        )
        d2 = InspectionDivision.objects.create(routine=routine, name="B", sort_order=20)
        d1 = InspectionDivision.objects.create(routine=routine, name="A", sort_order=10)
        ordered = list(InspectionDivision.objects.filter(routine=routine).order_by("sort_order", "id"))
        self.assertEqual([d1.pk, d2.pk], [ordered[0].pk, ordered[1].pk])

    def test_duplicate_equipment_raises(self):
        routine = PreventiveInspectionRoutine.objects.create(
            company=self.company,
            operational_site=self.site,
            checklist=self.checklist,
            name="Rotina",
        )
        div = InspectionDivision.objects.create(routine=routine, name="Lote 1", sort_order=1)
        InspectionDivisionEquipment.objects.create(division=div, asset=self.asset)
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                InspectionDivisionEquipment.objects.create(division=div, asset=self.asset)

    def test_next_without_pointer_is_first_active(self):
        routine = PreventiveInspectionRoutine.objects.create(
            company=self.company,
            operational_site=self.site,
            checklist=self.checklist,
            name="Rotina",
        )
        InspectionDivision.objects.create(routine=routine, name="S1", sort_order=1, is_active=True)
        InspectionDivision.objects.create(routine=routine, name="S2", sort_order=2, is_active=True)
        self.assertIsNone(routine.next_division_id)
        nxt = get_next_eligible_inspection_division(routine)
        self.assertIsNotNone(nxt)
        self.assertEqual(nxt.name, "S1")

    def test_next_skips_inactive(self):
        routine = PreventiveInspectionRoutine.objects.create(
            company=self.company,
            operational_site=self.site,
            checklist=self.checklist,
            name="Rotina",
        )
        InspectionDivision.objects.create(routine=routine, name="A", sort_order=10, is_active=True)
        d2 = InspectionDivision.objects.create(routine=routine, name="B", sort_order=20, is_active=False)
        InspectionDivision.objects.create(routine=routine, name="C", sort_order=30, is_active=True)
        routine.next_division = d2
        routine.save(update_fields=("next_division",))
        nxt = get_next_eligible_inspection_division(routine)
        self.assertEqual(nxt.name, "C")

    def test_next_returns_pointer_when_active(self):
        routine = PreventiveInspectionRoutine.objects.create(
            company=self.company,
            operational_site=self.site,
            checklist=self.checklist,
            name="Rotina",
        )
        active = InspectionDivision.objects.create(routine=routine, name="Ativa", sort_order=1, is_active=True)
        InspectionDivision.objects.create(routine=routine, name="Outra", sort_order=2, is_active=True)
        routine.next_division = active
        routine.save(update_fields=("next_division",))
        self.assertEqual(get_next_eligible_inspection_division(routine).pk, active.pk)

    def test_archived_division_skipped(self):
        routine = PreventiveInspectionRoutine.objects.create(
            company=self.company,
            operational_site=self.site,
            checklist=self.checklist,
            name="Rotina",
        )
        archived = InspectionDivision.objects.create(routine=routine, name="Arq", sort_order=1, is_active=True)
        archived.archived_at = timezone.now()
        archived.save(update_fields=("archived_at",))
        nxt_eligible = InspectionDivision.objects.create(routine=routine, name="Seguinte", sort_order=2, is_active=True)
        routine.next_division = archived
        routine.save(update_fields=("next_division",))
        self.assertEqual(get_next_eligible_inspection_division(routine).pk, nxt_eligible.pk)

    def test_deactivate_division_keeps_record(self):
        routine = PreventiveInspectionRoutine.objects.create(
            company=self.company,
            operational_site=self.site,
            checklist=self.checklist,
            name="Rotina",
        )
        div = InspectionDivision.objects.create(routine=routine, name="Antiga", sort_order=1, is_active=True)
        pk = div.pk
        div.is_active = False
        div.save(update_fields=("is_active",))
        div.refresh_from_db()
        self.assertFalse(div.is_active)
        self.assertEqual(div.pk, pk)
