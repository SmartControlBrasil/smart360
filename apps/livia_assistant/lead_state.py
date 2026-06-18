from __future__ import annotations

from dataclasses import dataclass


class LeadState:
    DISCOVERY = "discovery"
    OFFER_HANDOFF = "offer_handoff"
    COLLECT_NAME = "collect_name"
    COLLECT_COMPANY = "collect_company"
    COLLECT_CITY = "collect_city"
    COLLECT_PHONE = "collect_phone"
    COLLECT_EMAIL = "collect_email"
    QUALIFIED = "qualified"
    CLOSED = "closed"


STATE_ORDER = (
    LeadState.DISCOVERY,
    LeadState.OFFER_HANDOFF,
    LeadState.COLLECT_NAME,
    LeadState.COLLECT_COMPANY,
    LeadState.COLLECT_CITY,
    LeadState.COLLECT_PHONE,
    LeadState.COLLECT_EMAIL,
    LeadState.QUALIFIED,
    LeadState.CLOSED,
)


@dataclass(frozen=True)
class LeadStateSnapshot:
    state: str
    next_field: str
    is_terminal: bool


def field_for_state(state: str) -> str:
    return {
        LeadState.COLLECT_NAME: "name",
        LeadState.COLLECT_COMPANY: "company",
        LeadState.COLLECT_CITY: "city",
        LeadState.COLLECT_PHONE: "phone",
        LeadState.COLLECT_EMAIL: "email",
    }.get(state, "")


def normalize_state(raw_state: str) -> str:
    if raw_state in STATE_ORDER:
        return raw_state
    return LeadState.DISCOVERY


def resolve_state(
    *,
    has_intent: bool,
    has_name: bool,
    has_company: bool,
    has_city: bool,
    has_phone: bool,
    has_email: bool,
    city_skippable: bool = False,
    locked: bool = False,
) -> LeadStateSnapshot:
    if locked:
        return LeadStateSnapshot(state=LeadState.CLOSED, next_field="", is_terminal=True)
    if has_name and (has_phone or has_email):
        return LeadStateSnapshot(state=LeadState.QUALIFIED, next_field="", is_terminal=True)
    if not has_intent and not has_name and not has_company and not has_city and not has_phone and not has_email:
        return LeadStateSnapshot(state=LeadState.DISCOVERY, next_field="", is_terminal=False)
    if not has_name:
        return LeadStateSnapshot(state=LeadState.COLLECT_NAME, next_field="name", is_terminal=False)
    if not has_company:
        return LeadStateSnapshot(state=LeadState.COLLECT_COMPANY, next_field="company", is_terminal=False)
    if not has_city and not city_skippable:
        return LeadStateSnapshot(state=LeadState.COLLECT_CITY, next_field="city", is_terminal=False)
    if not (has_phone or has_email):
        return LeadStateSnapshot(state=LeadState.COLLECT_PHONE, next_field="phone", is_terminal=False)
    return LeadStateSnapshot(state=LeadState.OFFER_HANDOFF, next_field="", is_terminal=False)
