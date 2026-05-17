# Core Domain Contracts — Smart360

This document describes the **framework-agnostic** domain and application contracts introduced under `apps/core` for the first Smart360 wave (see also `docs/reprioritization-architecture-plan.md`).

---

## Why pure domain / application contracts?

- **Domain layer** (`apps/core/domain/`) expresses **business vocabulary and invariants** without coupling to Django ORM, HTTP, or Celery. Modules here use **stdlib only** (for example `dataclasses`, `datetime`, `typing`) — no `django` imports.
- **Application ports** (`apps/core/application/ports/`) define **interfaces** that use cases depend on; **infrastructure** provides Django-backed implementations later. Ports stay **framework-agnostic** (for example `abc.ABC` + abstract methods).
- This preserves **Hexagonal Architecture**: the Core remains testable and stable while persistence and messaging evolve.

---

## Why no database schema yet?

These types are **conceptual contracts** and **integration boundaries**:

- Adding Django `models.Model` classes and migrations would prematurely fix column types, indexes, and polymorphism strategies before product modules consume them.
- **Company** / **Contact** persistence may already evolve elsewhere; `CompanyProductRelation` and `ServiceContract` must align with that roadmap without forcing a schema in this step.
- Teams can agree on **UUID vs integer** storage, **JSON scope** columns, and **outbox tables** in a dedicated persistence iteration.

Until then, **no migrations** and **no schema change** are implied by this folder.

---

## How future Django models and repositories will adapt

| Contract | Typical infrastructure mapping |
|----------|-------------------------------|
| `ProductCode` | Stored as `CharField` / slug; validated on write using the same rules as the value object. |
| `CompanyProductRelation` | ORM model with `company_id` FK or UUID referencing Core `Company`; `product_code` string; indexes on `(company_id, product_code)`. Repository maps row ↔ entity. |
| `ServiceContract` | ORM model with date fields, JSONField for `scope` / `metadata`, nullable `billing_reference_id`; repository loads dataclass instances. |
| `DomainEvent` | Serialized to Integration Bus payload; optional **outbox** row (`event_id`, `payload`, `published_at`). |
| `EventBus` port | Implementation calls `integration_bus`, Celery chain, or transactional outbox publisher. |

Repositories belong in `apps/core/infrastructure/repositories/` and implement ports defined alongside or in `application/ports/` as the codebase grows.

---

## In-memory EventBus (development adapter only)

`apps/core/infrastructure/messaging/in_memory_event_bus.py` provides **`InMemoryEventBus`**, the first concrete adapter for the `EventBus` port. It keeps published `DomainEvent` instances in a process-local list (with a thread-safe lock), optionally logs **`event_name`** (and minimal correlation fields) via Python **`logging`**, and exposes **`snapshot()`** / **`clear()`** for inspection and tests.

**This adapter is for local development and automated tests only.** It does not persist events, does not integrate with Celery, and does not deliver to cross-product consumers. Events are lost when the process exits and are not shared across workers.

**Future production-style adapters** may instead (or in combination) use Django signals, Celery tasks, Redis or Kafka producers, or a **database outbox** pattern for reliable, transactional publishing—without changing the domain or application port contracts.

### EventBus provider (composition root)

The **`EventBusProvider`** port (`apps/core/application/ports/event_bus_provider.py`) exposes **`get_event_bus()`** so use cases depend on an abstraction, not on `InMemoryEventBus` or import paths under `infrastructure/`. The default implementation (`apps/core/infrastructure/messaging/event_bus_provider_impl.py`) holds a **module-level singleton** `InMemoryEventBus` and a **`get_event_bus()`** function (plus **`InMemoryEventBusProvider`** for explicit injection). Later, the same port can be satisfied by a **DI container**, **Django settings–based factory**, or **request-scoped** wiring without touching domain code.

---

## How product modules must use `CompanyProductRelation` and `ServiceContract`

1. **Affiliation:** Before treating a company as an active customer of **smart_site_factory**, **caneca_de_garagem**, **marketplace_technicians**, etc., product code should expect a **CompanyProductRelation** (or equivalent read model) keyed by `(company_id, ProductCode)` with `status == active` where applicable.
2. **Commercial scope:** Retainers, maintenance, SLA bundles, and marketing packages attach to **ServiceContract** — products reference `company_id`, `ProductCode`, and optionally `billing_reference_id`; they **do not** duplicate subscription logic inside each app.
3. **Stable IDs:** Products store **foreign identifiers** to Core entities only; never fork parallel `Company` rows.

---

## How events will feed platform capabilities (later wiring)

When `EventBus.publish` / `EventBus.publish_many` are implemented, `DomainEvent` instances (raised from Core or product modules **after** persistence of their aggregate) will enable:

| Capability | Role |
|------------|------|
| **Notifications** | Trigger templates from `event_name` + payload (e.g. contract activated). |
| **Analytics** | Ingest structured events for funnels and KPIs (`aggregate_type`, product hints in metadata). |
| **Billing** | React to lifecycle events to create invoices or reconcile usage (subscriber in Billing BC). |
| **Audit** | Append-only audit log for security-sensitive transitions (`metadata.actor_user_id`). |
| **AI Orchestration** | Optional summarization / routing based on event streams (policy-controlled). |
| **Growth Engine** | Attribution and nurture campaigns from qualified events (e.g. affiliation activated). |

Subscribers attach via **Integration Bus** contracts — product modules **publish** events; they do not import each other’s Django apps.

---

## File reference

| Path | Description |
|------|-------------|
| `apps/core/domain/events/domain_event.py` | `DomainEvent` envelope. |
| `apps/core/domain/value_objects/product_code.py` | `ProductCode` + `KNOWN_PRODUCT_CODES`. |
| `apps/core/domain/entities/company_product_relation.py` | `CompanyProductRelation` entity. |
| `apps/core/domain/entities/service_contract.py` | `ServiceContract` entity. |
| `apps/core/application/ports/event_bus.py` | `EventBus` abstract port. |
| `apps/core/application/ports/event_bus_provider.py` | `EventBusProvider` port (`get_event_bus`). |
| `apps/core/infrastructure/messaging/in_memory_event_bus.py` | `InMemoryEventBus` — dev/test adapter (see section above). |
| `apps/core/infrastructure/messaging/event_bus_provider_impl.py` | Singleton `get_event_bus()` + `InMemoryEventBusProvider`. |

---

*End of document.*
