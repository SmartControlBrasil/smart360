"""
Affiliation between a canonical Company and a Smart360 product module.

Persisted representation will live in infrastructure (Django ORM); this entity
captures the domain shape only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID

from ..value_objects.product_code import ProductCode


@dataclass
class CompanyProductRelation:
    """
    Declares that a company is entitled to / enrolled in a given product area.

    Attributes:
        company_id: Stable company identifier (typically Core public UUID).
        product_code: Target SaaS module (see ``ProductCode``).
        relation_type: Commercial or technical kind of link (e.g. ``customer``, ``partner``, ``trial``).
        status: Lifecycle state (e.g. ``active``, ``suspended``).
        metadata: Extensible bag for tier codes, seat limits, etc.
        activated_at: When the relation became effective (optional until first activation).
        deactivated_at: When the relation ended, if applicable.
    """

    company_id: UUID
    product_code: ProductCode
    relation_type: str
    status: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    activated_at: datetime | None = None
    deactivated_at: datetime | None = None
