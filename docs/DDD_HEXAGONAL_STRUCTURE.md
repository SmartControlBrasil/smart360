# DDD + Hexagonal Folder Structure — Smart360 First Wave

This document describes the **domain-driven design (DDD)** and **hexagonal (ports & adapters)** layout used for the **first priority wave** aligned with `docs/reprioritization-architecture-plan.md`.

Scaffolding exists under:

| Django app | Role |
|------------|------|
| `apps.core` | Core platform additions (Company, Contact, User, ServiceContract, RBAC, Billing integration surface, Files hooks — **as implemented over time**) |
| `apps.smart_site_factory` | Smart Site Factory |
| `apps.caneca_de_garagem` | Caneca de Garagem |
| `apps.marketplace_technicians` | Technician Marketplace |

Legacy paths (`api/`, root `admin.py`, `models.py`, optional `services/` helpers) **remain** until gradually migrated into `interfaces/` and hexagonal layers.

---

## 1. Standard folder layout

```
<django_app>/
  domain/
    entities/
    value_objects/
    services/
    events/
    repositories/       # optional; repository *interfaces* — often mirrored in application/ports/
    exceptions/
  application/
    use_cases/
    commands/
    queries/
    dtos/
    ports/              # outbound port interfaces (repositories, event publisher, clock, etc.)
  infrastructure/
    persistence/        # Django ORM adapters, mappers
    repositories/       # concrete repository implementations
    adapters/
    integrations/
    tasks/               # Celery / async workers
  interfaces/
    api/
    admin/
    web/
    webhooks/
```

---

## 2. Folder purpose

| Layer | Purpose |
|-------|---------|
| **domain** | Pure business rules: aggregates, entities, value objects, domain services, domain events, domain exceptions. **No Django, DRF, Celery, or HTTP.** |
| **application** | Use cases orchestrating domain logic through **ports**. Commands/queries if using CQRS-style split. DTOs crossing the application boundary. |
| **infrastructure** | Technical implementations: ORM, repositories, outbound integrations, message publishing adapters, background tasks. |
| **interfaces** | Driving adapters: REST controllers (thin), Django admin wiring, server-rendered views, inbound webhooks. |

---

## 3. Dependency rules (dependency inversion)

Allowed direction:

```
interfaces → application → domain
     ↓              ↑
infrastructure ----┘   (implements ports defined in application)
```

- **Domain** depends on **nothing** outside itself (stdlib/types only).
- **Application** depends on **domain** and **port interfaces** (abstract).
- **Infrastructure** depends on **domain/application contracts** and frameworks (Django, Celery, HTTP clients).
- **Interfaces** depend on **application** (use cases), not on **infrastructure** directly (inject implementations via DI or Django wiring).

**Forbidden:** `domain` importing `django`, `rest_framework`, or product modules.

---

## 4. What may and may not live in each layer

### Domain — allowed

- Entity behavior, invariants, factories inside domain style.
- Value objects (immutable where possible).
- Domain events (types + constructors).
- Domain service pure logic spanning multiple entities.

### Domain — not allowed

- Django `models.Model` classes (those belong in **infrastructure/persistence** or legacy `models.py` until migrated).
- Serializer / HTTP / ORM calls.

### Application — allowed

- Use case classes / handlers.
- Command/query objects and handlers.
- DTOs for input/output of use cases.
- **Ports**: ABCs or Protocols for `EventPublisher`, `CompanyDirectory`, `BillingGateway`, etc.

### Application — not allowed

- Direct instantiation of Django ORM querysets (inject repository via port).

### Infrastructure — allowed

- Django models (if using active record boundary), repository implementations, Celery tasks calling use cases, adapters to Billing/Files/Notifications.

### Interfaces — allowed

- Thin views that parse HTTP → call one use case → map result to HTTP.
- URL routing, permission checks delegating to Core RBAC.

### Interfaces — not allowed

- Embedding business rules that belong in domain/application.

---

## 5. Referencing Core entities by stable IDs

Products **must not** duplicate canonical Company, Contact, or User rows.

- Persist **foreign identifiers** as opaque IDs (integer PK or UUID **issued by Core**), never rebuild parallel directories.
- Application layer receives IDs via DTOs; ports such as `CompanyResolver` may validate existence via Core APIs or read models.
- **ServiceContract**, billing accounts, and **CompanyProductRelation** remain **Core-aligned** concepts per `reprioritization-architecture-plan.md`.

Anti-pattern: copying legal name, tax ID, or email into product tables except as **explicit** denormalized projection with invalidation policy.

---

## 6. No direct product-to-product dependencies

- `smart_site_factory` **must not** import domain/use cases from `caneca_de_garagem` or `marketplace_technicians`, and vice versa.
- Shared kernels belong in **`apps.core`** or **`shared_kernel`** (technical cross-cutting only — avoid leaking product vocabulary into generic helpers).

---

## 7. Cross-product communication: Integration Bus & events

Use **`integration_bus`** (or equivalent platform messaging) and **domain events** payloads documented in the architecture plan:

- Publishers live in **infrastructure** (adapter implementing `EventPublisher` port).
- Subscribers in each product **never** import peer products; they subscribe to **topic contracts** and deserialize payloads by schema/version.

Examples: `WebsiteDelivered`, `OrderPlaced`, `TechnicianAssigned`, `ContractActivated` → Notifications, Analytics, Billing hooks, Audit, AI orchestration, Growth Engine — as described in the reprioritization doc.

---

## 8. Relationship to `reprioritization-architecture-plan.md`

Concepts such as **ServiceContract**, **ClientAccessState** (SSF), **ProductionCapacity** (Caneca), **JobType** (Technician Marketplace), and the **event catalog** should materialize primarily in **domain** + **application** layers; persistence arrives when models/migrations are intentionally introduced.

---

## 9. Smart Site Factory: in-memory repositories (dev / test only)

Under `apps/smart_site_factory/infrastructure/repositories/`, **`InMemoryWebsiteProjectRepository`** and **`InMemoryProjectBriefRepository`** satisfy the application ports with process-local, thread-safe dict storage. They exist for **local development, automated tests, and prototypes** — they do **not** survive restarts and are **not** a substitute for transactional persistence.

**Future Django ORM** (or other) repository implementations belong in the same `infrastructure/repositories/` package (or `infrastructure/persistence/` alongside mappers), wired from the composition root, without changing domain or application contracts.

---

## 10. Migration notes (future work, not done by scaffolding)

1. Move logic from legacy `services/` packages into `domain/services/` or `application/use_cases/` as appropriate.
2. Point DRF `views` under `api/` toward use cases; optionally relocate to `interfaces/api/`.
3. Keep **one Django app per product** unless bounded contexts split into separate deployables (out of scope for first wave).

---

*End of document.*
