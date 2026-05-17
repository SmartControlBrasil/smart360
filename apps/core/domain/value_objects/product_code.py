"""
Product module identifier used for affiliation and contracts across Smart360.

This is not a Django ``ContentType``; it encodes the **commercial/product module**
slug agreed by the platform (see ``KNOWN_PRODUCT_CODES`` for examples).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Illustrative registry — extend as new SaaS modules are onboarded.
KNOWN_PRODUCT_CODES: frozenset[str] = frozenset(
    {
        "smart_site_factory",
        "caneca_de_garagem",
        "marketplace_technicians",
        "smart_system",
        "smart_labs",
    }
)


@dataclass(frozen=True)
class ProductCode:
    """
    Immutable value object for a product/module code (lowercase slug with underscores).

    Examples:
        ProductCode("smart_site_factory")
        ProductCode("caneca_de_garagem")
        ProductCode("marketplace_technicians")
    """

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        object.__setattr__(self, "value", normalized)
        if not _SLUG_PATTERN.match(normalized):
            raise ValueError(
                "ProductCode must match ^[a-z][a-z0-9_]*$ (got {!r})".format(normalized)
            )

    def __str__(self) -> str:
        return self.value
