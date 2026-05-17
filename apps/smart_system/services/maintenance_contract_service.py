from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.ai_shared.interfaces.triggers import get_anomaly_agent_trigger_service, get_profitability_agent_trigger_service
from apps.billing.models import BillingCustomer, Invoice, InvoiceItem
from apps.billing.services.billing_service import InvoiceService
from apps.observability_center.services.observability_service import SystemEventService

from ..models import ContractAsset, MaintenanceContract, MaintenancePlan, ServiceOrder
from .maintenance_service import ServiceOrderService
from .scheduling_service import TechnicianRoutingService


@dataclass(frozen=True)
class PreventiveGenerationResult:
    contract: MaintenanceContract
    generated_orders: list[ServiceOrder]
    skipped_assets: list[ContractAsset]


class MaintenanceContractNumberGenerator:
    @staticmethod
    def generate() -> str:
        prefix = timezone.now().strftime("MCT-%Y%m")
        latest = (
            MaintenanceContract.objects.filter(contract_number__startswith=prefix)
            .order_by("-contract_number")
            .first()
        )
        sequence = int(latest.contract_number.split("-")[-1]) + 1 if latest else 1
        return f"{prefix}-{sequence:04d}"


class MaintenanceContractService:
    BILLING_DAYS = {
        MaintenanceContract.BillingFrequency.MONTHLY: 30,
        MaintenanceContract.BillingFrequency.BIMONTHLY: 60,
        MaintenanceContract.BillingFrequency.QUARTERLY: 90,
        MaintenanceContract.BillingFrequency.SEMIANNUAL: 180,
        MaintenanceContract.BillingFrequency.YEARLY: 365,
    }

    MAINTENANCE_DAYS = {
        ContractAsset.MaintenanceFrequency.MONTHLY: 30,
        ContractAsset.MaintenanceFrequency.BIMONTHLY: 60,
        ContractAsset.MaintenanceFrequency.QUARTERLY: 90,
        ContractAsset.MaintenanceFrequency.SEMIANNUAL: 180,
        ContractAsset.MaintenanceFrequency.YEARLY: 365,
    }

    @classmethod
    def _billing_days(cls, contract: MaintenanceContract) -> int:
        if contract.billing_frequency == MaintenanceContract.BillingFrequency.CUSTOM_DAYS:
            return max(contract.billing_frequency_days or 30, 1)
        return cls.BILLING_DAYS.get(contract.billing_frequency, 30)

    @classmethod
    def _maintenance_days(cls, contract_asset: ContractAsset) -> int:
        if contract_asset.maintenance_frequency == ContractAsset.MaintenanceFrequency.CUSTOM_DAYS:
            return max(contract_asset.maintenance_frequency_days or 30, 1)
        return cls.MAINTENANCE_DAYS.get(contract_asset.maintenance_frequency, 30)

    @staticmethod
    def _log_event(contract: MaintenanceContract, event_type: str, message: str, *, user=None, payload=None):
        SystemEventService.log_system_event(
            event_type=event_type,
            source_module="smart_system",
            message=message,
            user=user,
            company=contract.company,
            site=contract.operational_site,
            entity_type="maintenance_contract",
            entity_id=contract.contract_number,
            payload=payload or {},
        )

    @classmethod
    @transaction.atomic
    def create_contract(cls, *, validated_data, user=None) -> MaintenanceContract:
        if not validated_data.get("contract_number"):
            validated_data["contract_number"] = MaintenanceContractNumberGenerator.generate()
        if not validated_data.get("next_billing_date"):
            validated_data["next_billing_date"] = validated_data["start_date"] + timedelta(
                days=cls.BILLING_DAYS.get(validated_data.get("billing_frequency"), validated_data.get("billing_frequency_days", 30))
            )
        contract = MaintenanceContract.objects.create(**validated_data)
        AuditService.log(
            action="smart_system.contract.created",
            entity="maintenance_contract",
            entity_id=str(contract.public_id),
            user=user,
            company=contract.company,
            payload={"contract_number": contract.contract_number, "status": contract.status},
        )
        cls._log_event(
            contract,
            "contract.created",
            f"Contrato {contract.contract_number} criado.",
            user=user,
        )
        return contract

    @classmethod
    @transaction.atomic
    def activate_contract(cls, *, contract: MaintenanceContract, user=None) -> MaintenanceContract:
        contract.status = MaintenanceContract.Status.ACTIVE
        if not contract.next_billing_date:
            contract.next_billing_date = contract.start_date + timedelta(days=cls._billing_days(contract))
        contract.save(update_fields=["status", "next_billing_date", "updated_at"])
        AuditService.log(
            action="smart_system.contract.activated",
            entity="maintenance_contract",
            entity_id=str(contract.public_id),
            user=user,
            company=contract.company,
            payload={"contract_number": contract.contract_number},
        )
        cls._log_event(contract, "contract.activated", f"Contrato {contract.contract_number} ativado.", user=user)
        try:
            profitability_trigger_service = get_profitability_agent_trigger_service()
            profitability_trigger_service.run_contract_analysis(contract=contract, user=user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.run_contract_analysis(contract=contract, user=user)
        except Exception:
            pass
        return contract

    @classmethod
    @transaction.atomic
    def suspend_contract(cls, *, contract: MaintenanceContract, user=None, reason: str = "") -> MaintenanceContract:
        contract.status = MaintenanceContract.Status.SUSPENDED
        contract.notes = f"{contract.notes}\n{reason}".strip()
        contract.save(update_fields=["status", "notes", "updated_at"])
        AuditService.log(
            action="smart_system.contract.suspended",
            entity="maintenance_contract",
            entity_id=str(contract.public_id),
            user=user,
            company=contract.company,
            payload={"contract_number": contract.contract_number, "reason": reason},
        )
        cls._log_event(contract, "contract.suspended", f"Contrato {contract.contract_number} suspenso.", user=user, payload={"reason": reason})
        try:
            profitability_trigger_service = get_profitability_agent_trigger_service()
            profitability_trigger_service.run_contract_analysis(contract=contract, user=user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.run_contract_analysis(contract=contract, user=user)
        except Exception:
            pass
        return contract

    @classmethod
    @transaction.atomic
    def expire_contract(cls, *, contract: MaintenanceContract, user=None, reason: str = "") -> MaintenanceContract:
        contract.status = MaintenanceContract.Status.EXPIRED
        contract.notes = f"{contract.notes}\n{reason}".strip()
        contract.save(update_fields=["status", "notes", "updated_at"])
        AuditService.log(
            action="smart_system.contract.expired",
            entity="maintenance_contract",
            entity_id=str(contract.public_id),
            user=user,
            company=contract.company,
            payload={"contract_number": contract.contract_number, "reason": reason},
        )
        cls._log_event(contract, "contract.expired", f"Contrato {contract.contract_number} expirado.", user=user, payload={"reason": reason})
        try:
            profitability_trigger_service = get_profitability_agent_trigger_service()
            profitability_trigger_service.run_contract_analysis(contract=contract, user=user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.run_contract_analysis(contract=contract, user=user)
        except Exception:
            pass
        return contract

    @classmethod
    def sync_contract_asset_schedule(cls, contract_asset: ContractAsset) -> ContractAsset:
        if not contract_asset.next_execution:
            base_date = contract_asset.contract.start_date
            contract_asset.next_execution = base_date
        contract_asset.save(update_fields=["next_execution", "updated_at"])
        return contract_asset

    @classmethod
    def _ensure_maintenance_plan(cls, contract_asset: ContractAsset) -> MaintenancePlan:
        defaults = {
            "company": contract_asset.contract.company,
            "operational_site": contract_asset.contract.operational_site or contract_asset.asset.operational_site,
            "asset": contract_asset.asset,
            "name": f"Contrato {contract_asset.contract.contract_number} - {contract_asset.asset.name}",
            "description": f"Plano preventivo recorrente do contrato {contract_asset.contract.contract_number}.",
            "frequency_type": MaintenancePlan.FrequencyType.CUSTOM,
            "frequency_value": cls._maintenance_days(contract_asset),
            "estimated_duration_minutes": contract_asset.estimated_duration_minutes,
            "is_active": contract_asset.is_active,
            "next_due_date": contract_asset.next_execution,
            "notes": contract_asset.notes,
        }
        plan, _ = MaintenancePlan.objects.update_or_create(
            maintenance_contract=contract_asset.contract,
            contract_asset=contract_asset,
            defaults=defaults,
        )
        return plan

    @classmethod
    @transaction.atomic
    def generate_due_preventives(
        cls,
        *,
        contract: MaintenanceContract,
        target_date=None,
        generated_by=None,
    ) -> PreventiveGenerationResult:
        target_date = target_date or timezone.localdate()
        generated_orders: list[ServiceOrder] = []
        skipped_assets: list[ContractAsset] = []
        if contract.status != MaintenanceContract.Status.ACTIVE or not contract.auto_generate_preventives:
            return PreventiveGenerationResult(contract=contract, generated_orders=[], skipped_assets=list(contract.covered_assets.all()))

        for contract_asset in contract.covered_assets.select_related("asset", "asset__operational_site").filter(is_active=True):
            cls.sync_contract_asset_schedule(contract_asset)
            if not contract_asset.next_execution or contract_asset.next_execution > target_date:
                skipped_assets.append(contract_asset)
                continue

            existing_order = ServiceOrder.objects.filter(
                maintenance_contract=contract,
                contract_asset=contract_asset,
                maintenance_type=ServiceOrder.MaintenanceType.PREVENTIVE,
                status__in=[
                    ServiceOrder.Status.OPEN,
                    ServiceOrder.Status.SCHEDULED,
                    ServiceOrder.Status.IN_PROGRESS,
                    ServiceOrder.Status.WAITING_PARTS,
                    ServiceOrder.Status.WAITING_QUOTE_APPROVAL,
                ],
            ).first()
            if existing_order:
                skipped_assets.append(contract_asset)
                continue

            maintenance_plan = cls._ensure_maintenance_plan(contract_asset)
            order = ServiceOrderService.create_service_order(
                user=generated_by,
                validated_data={
                    "client": contract.client,
                    "operational_site": contract.operational_site or contract_asset.asset.operational_site,
                    "asset": contract_asset.asset,
                    "maintenance_contract": contract,
                    "contract_asset": contract_asset,
                    "maintenance_plan": maintenance_plan,
                    "maintenance_type": ServiceOrder.MaintenanceType.PREVENTIVE,
                    "priority": ServiceOrder.Priority.MEDIUM,
                    "status": ServiceOrder.Status.OPEN,
                    "source": ServiceOrder.Source.PLAN,
                    "title": f"Preventiva contratual - {contract_asset.asset.name}",
                    "description": f"OS preventiva gerada automaticamente pelo contrato {contract.contract_number}.",
                    "scheduled_start": timezone.make_aware(
                        timezone.datetime.combine(contract_asset.next_execution, timezone.datetime.min.time())
                    ),
                    "requested_by": "Contrato recorrente",
                    "notes": f"Gerado automaticamente pelo contrato {contract.contract_number}.",
                },
            )
            generated_orders.append(order)
            maintenance_plan.next_due_date = contract_asset.next_execution + timedelta(days=cls._maintenance_days(contract_asset))
            maintenance_plan.last_generated_at = timezone.now()
            maintenance_plan.save(update_fields=["next_due_date", "last_generated_at", "updated_at"])
            contract_asset.last_execution = contract_asset.next_execution
            contract_asset.next_execution = contract_asset.next_execution + timedelta(days=cls._maintenance_days(contract_asset))
            contract_asset.save(update_fields=["last_execution", "next_execution", "updated_at"])

        if generated_orders:
            TechnicianRoutingService.refresh_plannable_visits(
                schedule_date=target_date,
                company=contract.company,
                site=contract.operational_site,
                generated_by=generated_by,
            )
        cls._log_event(
            contract,
            "contract.preventives_generated",
            f"Contrato {contract.contract_number} processado para geracao de preventivas.",
            user=generated_by,
            payload={"generated_orders": [order.order_number for order in generated_orders]},
        )
        return PreventiveGenerationResult(contract=contract, generated_orders=generated_orders, skipped_assets=skipped_assets)

    @classmethod
    @transaction.atomic
    def generate_billing_cycle(cls, *, contract: MaintenanceContract, generated_by=None) -> Invoice | None:
        if contract.status != MaintenanceContract.Status.ACTIVE:
            return None
        due_date = contract.next_billing_date or timezone.localdate()
        if due_date > timezone.localdate():
            return None

        existing_invoice = Invoice.objects.filter(
            company=contract.company,
            metadata__maintenance_contract_number=contract.contract_number,
            due_at__date=due_date,
            status__in=[Invoice.Status.DRAFT, Invoice.Status.OPEN, Invoice.Status.OVERDUE, Invoice.Status.PAID],
        ).first()
        if existing_invoice:
            return existing_invoice

        billing_customer, _ = BillingCustomer.objects.get_or_create(
            company=contract.company,
            defaults={
                "trade_name": contract.company.name,
                "legal_name": contract.company.legal_name or contract.client.legal_name or contract.client.display_name,
                "billing_email": contract.company.email or contract.client.contact_email or f"financeiro@{contract.company.slug}.local",
                "customer_type": BillingCustomer.CustomerType.COMPANY,
                "status": BillingCustomer.Status.ACTIVE,
                "document_number": contract.company.tax_id or contract.client.document_number,
            },
        )
        invoice = InvoiceService.create_invoice(
            billing_customer=billing_customer,
            company=contract.company,
            status=Invoice.Status.OPEN,
            subtotal_amount=Decimal(contract.contract_value),
            total_amount=Decimal(contract.contract_value),
            due_at=timezone.make_aware(
                timezone.datetime.combine(due_date, timezone.datetime.min.time())
            ),
            notes=f"Cobranca recorrente do contrato {contract.contract_number}.",
            metadata={
                "maintenance_contract_number": contract.contract_number,
                "maintenance_contract_id": str(contract.public_id),
                "maintenance_client": contract.client.display_name,
            },
        )
        InvoiceService.add_item(
            invoice=invoice,
            item_type=InvoiceItem.ItemType.ONE_TIME,
            reference_type="maintenance_contract",
            reference_id=contract.contract_number,
            description=f"Contrato de manutencao recorrente {contract.contract_number}",
            quantity=Decimal("1.00"),
            unit_amount=Decimal(contract.contract_value),
        )
        contract.last_billing_date = due_date
        contract.next_billing_date = due_date + timedelta(days=cls._billing_days(contract))
        contract.save(update_fields=["last_billing_date", "next_billing_date", "updated_at"])
        AuditService.log(
            action="smart_system.contract.billing_generated",
            entity="maintenance_contract",
            entity_id=str(contract.public_id),
            user=generated_by,
            company=contract.company,
            payload={"contract_number": contract.contract_number, "invoice_number": invoice.invoice_number},
        )
        cls._log_event(
            contract,
            "contract.billing_generated",
            f"Fatura recorrente gerada para o contrato {contract.contract_number}.",
            user=generated_by,
            payload={"invoice_number": invoice.invoice_number},
        )
        try:
            ProfitabilityAgentTriggerService.run_contract_analysis(contract=contract, user=generated_by)
        except Exception:
            pass
        try:
            AnomalyAgentTriggerService.run_contract_analysis(contract=contract, user=generated_by)
        except Exception:
            pass
        return invoice
