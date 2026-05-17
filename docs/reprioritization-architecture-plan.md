# Smart360 — Reprioritization Architecture Plan (Enhanced)

Technical architecture plan for product delivery order: **Core Platform (MVP) → Smart Site Factory → Caneca de Garagem → Technician Marketplace**.  
This document extends the baseline plan with **ServiceContract**, **JobType**, **ProductionCapacity**, **ClientAccessState**, **domain events**, and **downstream event consumption**.  
**No code, models, or migrations** are prescribed here—only architecture and contracts.

---

## 1. Product priority and scope

| Priority | Product | Revenue focus |
|----------|---------|----------------|
| 1 | Core Platform (minimal viable) | Foundation for all commercial relationships |
| 2 | Smart Site Factory (SSF) | Service-based web projects, retainers, marketing services |
| 3 | Caneca de Garagem | Physical product, customization, order → production → delivery |
| 4 | Technician Marketplace | Technicians ↔ clients, requests, assignments, execution |

**Global rules (unchanged):** SSF is **not** a template download marketplace. Caneca is **not** a public multivendor marketplace in early phases. Technician Marketplace connects supply and demand for **field/technical services**.

---

## 2. Core Platform — minimal viable + ServiceContract

### 2.1 Core building blocks

| Concept | Role |
|---------|------|
| **Company** | Canonical organization (customer, partner, internal). |
| **Contact** | People linked to companies; operational and commercial touchpoints. |
| **User** | Platform identity; authentication and membership. |
| **CompanyProductRelation** | Product **affiliation**: which company is entitled to which product / tier. |
| **RBAC** | Basic roles and permissions (evolving toward a single system of record). |
| **Billing** | Invoices, payments, plans, usage lines—**not** reimplemented inside products. |
| **Files** | Binary storage and metadata; products reference `file_id`. |

### 2.2 ServiceContract (new Core concept)

**Purpose:** Represent **recurring or contracted services** in one place, across all products, so billing scope, product entitlement, and operational expectations stay aligned.

**Responsibilities:**

- Link **Company** to a **Product** (or product line) in the Smart360 sense—i.e. logical product module (SSF, Caneca, Technician, future).
- Reference **Billing** context: subscription, invoice schedule, line items, or usage model (exact billing mechanics stay in Billing; the contract **points** to the commercial instrument).
- Define **service scope**: structured payload (JSON or typed DTO) describing what is included—e.g. “monthly retainer hours,” “maintenance tier,” “N technician visits,” “marketing deliverables per month.”
- Support:
  - **Smart Site Factory:** maintenance plans, marketing retainers, hosting/support packages.
  - **Caneca de Garagem:** recurring supply, B2B standing orders (when applicable).
  - **Technician Marketplace:** prepaid bundles, SLAs, contracted response times.
  - **Future products:** same abstraction without new Core entities.

**Boundaries:**

- **ServiceContract** is **Core-owned aggregate** (or Core bounded context); products emit events when execution touches contracted scope; Billing activates/deactivates lines based on contract state.
- Products **do not** duplicate billing logic—they attach **work** (projects, orders, assignments) to a contract reference when the sale was contract-based.

**Illustrative fields (conceptual only):**

- `company_id`, `product_code` (SSF | CANECA | TECH | …), `billing_reference_id`, `status` (draft | active | suspended | ended), `scope` (structured), `valid_from`, `valid_to`.

---

## 3. Smart Site Factory — domain boundaries + ClientAccessState

### 3.1 Boundaries

| Inside SSF | Outside |
|------------|---------|
| Website projects, briefing, customization workflow, delivery, maintenance **execution** | Company, Contact, User, ServiceContract, Billing, Files |

**Forbidden:** public template downloads, marketplace-style catalog sales of ZIP/theme files.

### 3.2 ClientAccessState (new)

**Purpose:** Drive **client portal** experience, notifications, and automation with a single, explicit lifecycle visible to the customer.

**Examples (non-exhaustive):**

| State | Typical meaning |
|-------|------------------|
| `briefing_pending` | Waiting for client inputs or approval of brief. |
| `in_production` | Internal work in progress. |
| `waiting_approval` | Deliverable or milestone awaiting client sign-off. |
| `delivered` | Site/live delivery accepted or published per agreed definition. |
| `under_maintenance` | Active maintenance **ServiceContract** or equivalent engagement. |

**Rules:**

- **ClientAccessState** is an SSF (or project-level) **derived/cursor** state—it should be computable from project facts but **exposed** as a first-class concept for portal UX and event emission.
- Transitions trigger **domain events** (see §6) for automation and downstream systems.

### 3.3 Main entities (conceptual)

WebsiteProject, Briefing, ProductionWorkItem/Milestone, DeliveryRecord, MaintenancePlan (linked to **ServiceContract** where recurring), MarketingServiceLine (service semantics, not file SKUs).

### 3.4 DDD bounded contexts (SSF)

- **Project & Briefing**
- **Production Workflow**
- **Delivery & Acceptance**
- **Service Catalog (SSF)** — packages aligned with Billing / ServiceContract
- **Client Portal (presentation)** — reads **ClientAccessState** and permitted actions

---

## 4. Caneca de Garagem — domain boundaries + ProductionCapacity

### 4.1 Boundaries

| Inside | Outside |
|--------|---------|
| Catalog, customization rules, orders, production queue, fulfillment | Company, Contact, User, ServiceContract (B2B/recurring if needed), Billing, Files |

**Early phases:** direct commerce and production; **marketplace** discovery deferred.

### 4.2 ProductionCapacity (new)

**Purpose:** Encode **operational reality** so the system does not **oversell** or promise impossible delivery dates.

**Conceptual attributes:**

- **Daily production limits** (units per day per line/sku or global cap).
- **Queue limits** (max WIP orders or max queue depth before blocking new promise dates).
- **Lead time** (minimum offset from order confirmation to “ready to ship” under normal load).
- **Constraints** (blackout dates, material shortages flags, shift models—extensible metadata).

**Behavior:**

- **Order promise dates** and **checkout availability** must consult **ProductionCapacity** projections (rule engine or calculator in application layer).
- When capacity is exceeded, the domain responds with **deferral** or **waitlist** behavior—product decision, but **must not** silently accept impossible dates.

### 4.3 Main entities (conceptual)

ProductCatalogItem/SKU, CustomizationSpec, CustomerOrder, OrderLine, ProductionJob, ShipmentRef, **ProductionCapacity** (configuration aggregate).

### 4.4 DDD bounded contexts (Caneca)

- **Catalog & Customization**
- **Order Management**
- **Production & Fulfillment** — owns capacity checks and queue semantics

---

## 5. Technician Marketplace — domain boundaries + JobType

### 5.1 Boundaries

| Inside | Outside |
|--------|---------|
| Technician profile extensions, job taxonomy, requests, assignments, execution | User, Company, Contact, ServiceContract (prepaid/SLA), Billing, Files |

### 5.2 JobType (new)

**Purpose:** Normalize **what kind of work** is requested so matching, SLA, pricing, and analytics stay consistent.

**Examples:**

- Installation  
- Maintenance  
- Repair  
- Inspection  
- Emergency  
- Consulting  

**Rules:**

- **ServiceRequest** **must** reference **JobType** (foreign conceptual link).
- **JobType** drives:
  - **Matching** (technician skills ↔ job type).
  - **SLA** templates (response time, resolution window) — optionally overridden by **ServiceContract**.
  - **Pricing** hints (base tariffs, surge rules for emergency).
  - **Analytics** dimensions (volume by job type, region, SLA breach rate).

### 5.3 Main entities (conceptual)

TechnicianProfile, **JobType**, ServiceRequest (**→ JobType**), Assignment, ExecutionRecord/Evidence.

### 5.4 DDD bounded contexts (Technician)

- **Technician Identity & Availability**
- **Demand & Matching** — uses JobType for routing rules
- **Assignment & Execution**

---

## 6. Domain events (cross-product)

Events are **facts** that already happened in a bounded context. Names are **past tense** or **completed transition** style where applicable.

### 6.1 Smart Site Factory

| Event | Role |
|-------|------|
| `ProjectCreated` | New website project opened for a company/client context. |
| `BriefingSubmitted` | Client or PM finalized a briefing tranche. |
| `WebsiteDelivered` | Delivery record satisfied (URL, acceptance criteria). |

Plus transitions implied by **ClientAccessState** when useful as separate fine-grained events (e.g. `ClientAccessStateChanged` with from/to).

### 6.2 Caneca de Garagem

| Event | Role |
|-------|------|
| `OrderPlaced` | Order committed (post-validation; may await payment). |
| `CustomizationApproved` | Art/proof approved for production. |
| `ProductionStarted` | Job entered production floor / queue. |
| `ProductionCompleted` | Ready for packing/ship. |
| `ShipmentCreated` | Carrier label or handoff initiated. |

### 6.3 Technician Marketplace

| Event | Role |
|-------|------|
| `TechnicianAssigned` | Assignment accepted and bound to request. |
| `ServiceStarted` | On-site or remote work started. |
| `ServiceCompleted` | Work closed with outcome. |

### 6.4 Core / commercial

| Event | Role |
|-------|------|
| `ContractActivated` | **ServiceContract** became effective (often after Billing confirmation). |

**Transport:** Integration Bus (or equivalent) with namespaced topics—e.g. `smart360.ssf.project.created`, `smart360.caneca.order.placed`—exact naming is an implementation decision.

**Idempotency:** Consumers must tolerate duplicates; **event_id** and **causation** metadata recommended in the eventual schema.

---

## 7. How events feed platform capabilities

| Capability | How events are used |
|------------|---------------------|
| **Notifications** | Trigger templates (email, in-app, SMS) on state changes—e.g. `BriefingSubmitted` → notify PM; `WebsiteDelivered` → notify client; `ProductionCompleted` → notify sales/ops. |
| **Analytics** | Ingest event stream into Analytics Platform: funnels (order → production → ship), SSF project lifecycle, technician SLA by **JobType**. |
| **Billing** | `OrderPlaced` / `ContractActivated` / milestone events drive invoices, usage lines, or revenue recognition hooks—Billing remains authoritative for money. |
| **Audit** | Persist immutable audit records for security-sensitive transitions (`TechnicianAssigned`, `ContractActivated`, payment-adjacent events). |
| **AI Orchestration** | Events enqueue **context refresh** for copilots (e.g. summarize project status after `BriefingSubmitted`); optional agent steps **never** bypass Billing or human approval for commercial commits. |
| **Growth Engine** | Attribution and nurture: e.g. `WebsiteDelivered` → upsell campaign eligibility; `OrderPlaced` (Caneca) → repeat purchase segment; technician completion → NPS/referral workflows. |

**Principles:**

1. **Products publish** domain events; **Core services subscribe** where appropriate—avoid circular imports from product apps into Billing internals; use bus + stable payloads.
2. **PII minimization** in event payloads—prefer IDs; fetch detail in consumer if needed.
3. **ServiceContract** lifecycle events (`ContractActivated`, renewals, suspension) are **Core**-adjacent and should be visible to all products that depend on contracted scope.

---

## 8. Connection matrix — products to Core

| Product | Company | Contact | User | CompanyProductRelation | ServiceContract | Billing | Files |
|---------|-----------|---------|------|------------------------|-----------------|---------|-------|
| SSF | Client org | Stakeholders | PM, client portal | Entitlement | Retainers, maintenance, marketing | Projects + recurring lines | Assets, deliverables |
| Caneca | Buyer | Shipping/contact | Shop/admin | Product access | B2B recurring (optional) | Orders, invoices | Artwork, proofs |
| Technician | Client org | Site contact | Tech, client | Product access | SLA bundles | Service fees | Photos, signatures |

---

## 9. Implementation order (recommended)

1. **Core MVP** — Company, Contact, User, CompanyProductRelation, RBAC, Billing, Files, plus **ServiceContract** model and lifecycle rules aligned with Billing.
2. **Smart Site Factory** — Projects, briefing, production, delivery, **ClientAccessState**, events; link retainers/maintenance to **ServiceContract**.
3. **Caneca de Garagem** — Orders, customization, **ProductionCapacity**, production/fulfillment events.
4. **Technician Marketplace** — Profiles, **JobType** catalog, ServiceRequest → Assignment → execution events; optional **ServiceContract** for enterprise SLAs.

---

## 10. Documentation control

| Item | Value |
|------|--------|
| Status | Architecture plan — enhanced |
| Language | English |
| Code changes | None required by this document |

---

*End of document.*
