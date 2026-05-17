"""
Recurring or fixed-scope commercial service agreement tied to a company and product module.

Billing mechanics remain in the Billing bounded context; this entity holds the
domain contract shape and references an external billing anchor by id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping
from uuid import UUID

from ..value_objects.product_code import ProductCode


@dataclass
class ServiceContract:
    """
    Cross-product service agreement (retainers, maintenance, SLA bundles, etc.).

    Attributes:
        company_id: Canonical company identifier.
        product_code: Module whose scope this contract governs.
        contract_type: Commercial template key (e.g. ``retainer``, ``maintenance``, ``sla_bundle``).
        status: Lifecycle (e.g. ``draft``, ``active``, ``suspended``, ``ended``).
        scope: Structured description of included services (interpreted by product + billing).
        billing_reference_id: Opaque pointer to invoice schedule / subscription in Billing.
        start_date: Contract validity start (date-only boundary).
        end_date: Inclusive or exclusive end per billing policy (domain convention TBD).
        metadata: Extra attributes (renewal flags, auto-renew, legal refs).
    """

    company_id: UUID
    product_code: ProductCode
    contract_type: str
    status: str
    scope: Mapping[str, Any]
    billing_reference_id: str | None
    start_date: date
    end_date: date | None
    metadata: Mapping[str, Any] = field(default_factory=dict)
