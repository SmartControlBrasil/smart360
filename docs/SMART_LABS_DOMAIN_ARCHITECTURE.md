# Smart Labs — Domain Architecture

Technical architecture document for the **Smart Labs** product module inside the Smart360 ecosystem.  
This document defines vision, boundaries, bounded contexts, integrations, and implementation guidance.  
It does **not** prescribe concrete Django models or database schemas.

---

## 1. Product vision

**Smart Labs** is a **vertical analytical and laboratory platform** — not a generic horizontal marketplace. It combines:

- Deep **equipment intelligence** (models, symptoms, causes, procedures).
- A **technical knowledge base** curated for diagnostics and operations.
- A **supplier network** with validated capabilities and profiles.
- **Service** and **parts/product** marketplaces scoped to analytical and lab workflows.
- **AI-assisted diagnostics** grounded in structured domain knowledge.
- A **lead and demand engine** that turns technical signals into qualified opportunities.
- **Market intelligence** to understand demand, pricing, and supplier dynamics.

**Strategic positioning**

- Reuse **Smart360 Core Platform** for identity, directory (Company, Contact, User), commercial relationships (`CompanyProductRelation`), billing, files, notifications, analytics, AI orchestration, and Growth Engine.
- Own **lab-specific and equipment-specific** aggregates inside Smart Labs bounded contexts only.
- **Never** duplicate master data for companies, users, or contacts — always reference Core entities by **stable IDs**.

---

## 2. Domain boundaries

| Inside Smart Labs | Outside (Core or other products) |
|-------------------|-----------------------------------|
| Equipment taxonomy, error codes, symptoms, failure causes, troubleshooting graphs | Canonical `Company`, `Contact`, `User`, authentication, RBAC |
| Supplier **lab profile**, capabilities, certifications tied to Smart Labs | Generic CRM identity; billing accounts and invoices |
| Service catalog **for analytical/lab services**, requests, matching, assignments | Platform-wide `Billing`, `Subscription`, payment rails |
| Parts/consumables catalog **as lab commerce**, carts/orders **referencing** Core billing strategy | Duplicating `Company` / `Contact` rows |
| AI diagnostic **sessions**, explanations, suggested procedures **using** orchestration | Raw LLM infrastructure without policy (handled by Core AI orchestration) |
| Lead/opportunity **specific to lab demand** | Growth Engine campaigns and company-wide lead taxonomy (integrate via events/API) |

**Hard rule:** Smart Labs stores **foreign keys / UUID references** to Core entities only, plus domain-specific attributes that do not belong in the global directory.

---

## 3. Bounded contexts

Smart Labs is decomposed into eight initial bounded contexts. Each has its own ubiquitous language and lifecycle; integration happens through **application services**, **events**, and **explicit APIs** — not shared mutable aggregates across contexts.

| # | Bounded context | Responsibility |
|---|-----------------|----------------|
| 1 | **Equipment Intelligence** | Manufacturers, equipment models, specifications, compatibility, lifecycle metadata linked to diagnostic knowledge. |
| 2 | **Technical Knowledge** | Structured articles, procedures, diagnostic trees, cross-references to equipment and parts — editorial and versioning rules. |
| 3 | **Supplier Network** | Supplier profiles, credentials, regions, capabilities, trust signals — **not** duplicate Core companies; link `SupplierProfile` → `Company` (Core). |
| 4 | **Service Marketplace** | Discovery, quoting, booking, and fulfillment patterns for **analytical/lab services** (requests, matching, assignments, outcomes). |
| 5 | **Product / Parts Marketplace** | Catalog, availability, and transactions for parts and consumables **within lab workflows** (may integrate with Core billing and files for attachments). |
| 6 | **AI Diagnostics** | Diagnostic sessions, hypotheses, ranked causes, recommended procedures, safety disclaimers — orchestrated via Core AI, grounded on Knowledge + Equipment contexts. |
| 7 | **Lead & Demand Engine** | Inbound demand signals, qualification, routing to suppliers, `LeadOpportunity` alignment with Growth Engine where applicable. |
| 8 | **Market Intelligence** | Aggregated insights: demand trends, category heatmaps, supplier benchmarks — fed by Analytics events and internal facts (no PII duplication). |

**Relationship to existing codebase:** The current `marketplace_analytical` Django app may evolve into or integrate with Smart Labs **Service Marketplace** and **Supplier Network**; naming and module boundaries should converge on this document in a later refactor phase (not part of this document’s scope).

---

## 4. Main entities

The following entity names are **conceptual** — they map to domain objects in the Smart Labs model, not necessarily one-to-one with future Django models.

### Core technical relationship chain

Canonical diagnostic and commerce trace:

```
Manufacturer
  → EquipmentModel
      → ErrorCode / Symptom
          → FailureCause
              → TroubleshootingProcedure
                  → Part / Consumable (via BOM or compatibility)
                  → ServiceType
                      → SupplierCapability
                          → SupplierProfile (→ Core Company)
                              → Proposal / LeadOpportunity
```

### By context (summary)

| Context | Main entities |
|---------|----------------|
| Equipment Intelligence | `Manufacturer`, `EquipmentModel`, `ModelVariant`, `SpecificationSnapshot` |
| Technical Knowledge | `KnowledgeArticle`, `TroubleshootingProcedure`, `DiagnosticPath`, `MediaReference` (files via Core) |
| Supplier Network | `SupplierProfile`, `SupplierCapability`, `Certification`, `ServiceRegion`, `SLAProfile` |
| Service Marketplace | `ServiceListing`, `ServiceRequest`, `MatchCandidate`, `Assignment`, `ServiceOutcome` |
| Parts Marketplace | `CatalogPart`, `StockListing`, `OrderLine`, `ShipmentRef` (commercial settlement via Core Billing) |
| AI Diagnostics | `DiagnosticSession`, `Hypothesis`, `Evidence`, `RecommendedAction` |
| Lead & Demand Engine | `DemandSignal`, `LeadOpportunity`, `QualificationRule`, `RoutingDecision` |
| Market Intelligence | `InsightSnapshot`, `DemandMetric`, `CategoryBenchmark` (often materialized views or analytics projections) |

---

## 5. Core Platform integrations

| Core capability | How Smart Labs uses it |
|-----------------|-------------------------|
| **Company** | Buyer organization, supplier organization (after onboarding). Reference `company_id` only. |
| **Contact** | Points of contact for requests, quotes, and deliveries. Reference `contact_id` only. |
| **User** | Actors (buyers, supplier users, internal ops). Reference `user_id`; roles via Core access control. |
| **CompanyProductRelation** | Which commercial relationship applies (e.g., Smart Labs entitlement, tier). Drives feature flags and billing alignment. |
| **Billing & subscriptions** | Contracts, invoices, usage — Smart Labs emits billable events or order lines; does not reimplement ledger. |
| **Files** | Reports, certificates, images, SDS sheets — store metadata in Smart Labs; binary in Files Center. |
| **Notifications** | Request updates, assignment alerts, proposal responses — trigger via Core notification APIs/events. |
| **Analytics** | Product events (`service.request.created`, `diagnostic.session.completed`, etc.) with `company_id` / context IDs. |
| **AI Orchestration** | Model routing, policy, audit of AI calls — Smart Labs supplies **prompt context** and **domain tools**, not raw infrastructure. |
| **Growth Engine** | Campaign attribution, lead source sync — `LeadOpportunity` may link to Growth entities by ID when both exist. |

**Anti-pattern:** copying company name, tax ID, or email into Smart Labs tables except as **denormalized cache** with explicit invalidation policy — default is **no duplicate**.

---

## 6. Conceptual data model

High-level aggregate boundaries:

- **EquipmentCatalog aggregate:** `Manufacturer` root → `EquipmentModel` children; versions and discontinuation rules stay consistent within this aggregate.
- **DiagnosticKnowledge aggregate:** `FailureCause` and `TroubleshootingProcedure` link to `EquipmentModel` and optionally to `Part`.
- **Supplier aggregate:** `SupplierProfile` (Smart Labs) references **one** Core `Company`; `SupplierCapability` links `ServiceType` and regions.
- **ServiceTransaction aggregate:** `ServiceRequest` → matching → `Assignment` → `ServiceOutcome`; references buyer `Company`/`Contact` from Core.
- **PartsTransaction aggregate:** listings and orders reference Core for settlement and Files for documents.
- **DiagnosticSession aggregate:** session-bound hypotheses and recommendations; immutable log of AI-assisted steps for audit.

**Identifiers:** Prefer UUID `public_id` per aggregate root for external APIs; internal bigint PKs acceptable inside infrastructure.

---

## 7. Knowledge graph model

Smart Labs benefits from a **semantic layer** connecting equipment, symptoms, causes, procedures, parts, services, and suppliers.

**Node families (conceptual)**

- **Equipment:** Manufacturer, EquipmentModel, subsystem tags.
- **Observation:** Symptom, ErrorCode, measurement threshold.
- **Root cause:** FailureCause, fault mode.
- **Action:** TroubleshootingProcedure, recommended Part replacement, ServiceType.
- **Supply side:** SupplierProfile (edge to Core Company), SupplierCapability.
- **Demand:** LeadOpportunity, ServiceRequest.

**Edges (examples)**

- `EquipmentModel` —`manifests_as`→ `Symptom`
- `Symptom` —`often_caused_by`→ `FailureCause`
- `FailureCause` —`resolved_by`→ `TroubleshootingProcedure`
- `TroubleshootingProcedure` —`requires`→ `Part` / `Consumable`
- `ServiceType` —`delivered_by`→ `SupplierCapability`
- `LeadOpportunity` —`targets`→ `EquipmentModel` / `ServiceType`

**Implementation options (later):** dedicated graph store projection, or reuse platform **AI Knowledge Graph** components with Smart Labs–scoped node types — decision deferred to infrastructure phase.

---

## 8. Main user journeys

1. **Buyer: diagnose before buying** — Select equipment → describe symptoms → AI suggests causes/procedures → optional parts or service request → supplier proposals.
2. **Buyer: direct service request** — Create `ServiceRequest` from asset/context → matching → assignment → report uploaded → notification → billing event.
3. **Supplier: onboarding** — Core `Company` exists or is created → Smart Labs `SupplierProfile` + capabilities + compliance docs (Files).
4. **Supplier: respond to demand** — Receive qualified lead or request → submit `Proposal` → negotiate → accept → fulfill.
5. **Ops: knowledge maintenance** — Author/update procedures and equipment links; version and publish; Analytics on consumption.
6. **Analyst: market intelligence** — Dashboards on categories, regions, conversion — sourced from Analytics + aggregated Smart Labs facts.

---

## 9. AI diagnostic assistant responsibilities

- **In scope:** Interpret user symptom descriptions; map to `EquipmentModel` context; rank `FailureCause` hypotheses with explainability; suggest `TroubleshootingProcedure` steps; flag missing measurement data; reference approved knowledge articles only.
- **Orchestration:** Use Core **AI Orchestration** for model selection, safety policies, logging, and PII handling.
- **Grounding:** Retrieval from **Technical Knowledge** + **Equipment Intelligence**; no unconstrained fabrication of safety-critical steps.
- **Out of scope (initial):** autonomous ordering or contractual commitments without human confirmation; replacing certified lab judgment for regulated conclusions.

---

## 10. Supplier network responsibilities

- Maintain **Smart Labs–specific** supplier identity: capabilities, certifications, regions, turnaround times, equipment specialties.
- **Link** every supplier organization to exactly one Core `Company` (or explicit subsidiary rules documented in Core).
- Support **discovery** (who can run which `ServiceType`) and **trust** (reviews, completion metrics — domain-specific, not duplicating global reputation if Core owns a unified score later).
- Coordinate with **Service Marketplace** for acceptance workflows and SLA clocks.

---

## 11. Service request and proposal flow

**Happy path (conceptual)**

1. **Create demand** — Buyer (Core `User`/`Company`) opens `ServiceRequest` or qualified `LeadOpportunity` from Lead Engine.
2. **Triage** — Rule engine sets priority, category, required capabilities, geography.
3. **Match** — Candidate suppliers via `SupplierCapability` + availability signals.
4. **Proposal** — Suppliers submit `Proposal` (price, scope, timeline); buyer compares in Smart Labs UI.
5. **Award** — Selection creates or updates commercial obligation; Core **Billing** receives order/contract signal per platform rules.
6. **Fulfill** — `Assignment` lifecycle; deliverables stored in **Files**; outcome recorded for Analytics.
7. **Close** — Feedback loop to Market Intelligence and supplier scorecards.

**Events (examples):** `smart_labs.service_request.submitted`, `smart_labs.proposal.received`, `smart_labs.assignment.completed`.

---

## 12. Market intelligence layer

**Purpose:** Aggregate **non-sensitive** trends to guide suppliers and internal teams: category demand, geographic gaps, price bands, conversion rates, diagnostic frequency by equipment family.

**Inputs:** Analytics events, anonymized counts, optional third-party feeds (adapters in infrastructure).

**Outputs:** Dashboards, periodic snapshots (`InsightSnapshot`), alerts for demand spikes.

**Boundaries:** Does not replace Growth Engine for campaign execution; may **feed** Growth with segments via Core-approved integrations.

---

## 13. DDD + Hexagonal folder structure recommendation

Recommended layout for the Smart Labs Django app (or package split per bounded context if the codebase grows):

```
apps/smart_labs/                    # example package name
  domain/
    equipment/
    knowledge/
    supplier/
    service_marketplace/
    parts_marketplace/
    ai_diagnostics/
    lead_demand/
    market_intelligence/
    shared/                         # value objects, domain events
  application/
    commands/
    queries/
    ports/                          # repositories, gateways, message bus, AI facade
    dtos/
  infrastructure/
    persistence/
    repositories/
    integrations/                   # external lab APIs, payment webhooks, etc.
    messaging/                      # Celery tasks, event consumers
  interfaces/
    api/
    admin/
    web/
    webhooks/
```

**Rules**

- `domain/` — pure Python; no Django imports.
- Use cases live in `application/` and depend on `ports/` abstractions.
- ORM models and repositories live in `infrastructure/persistence/`.

---

## 14. What must NOT be implemented yet

- Concrete Django models, migrations, or database tables for Smart Labs aggregates.
- Production integrations with third-party LIMS/ELN systems without a signed integration spec.
- Full graph database deployment — optional phase after relational MVP.
- Duplicate Core entities (local `Company`/`User`/`Contact` tables).
- Broad horizontal “anything goes” marketplace features unrelated to analytical/lab vertical.
- Final SLA for AI diagnostics without legal/compliance review.

---

## 15. Recommended implementation roadmap

Phases are **sequential recommendations**; parallel work possible where dependencies allow.

| Phase | Focus |
|-------|--------|
| **0 — Governance** | Confirm glossary; align with Core IDs for Company/Contact/User/`CompanyProductRelation`; define event naming for Integration Bus. |
| **1 — Equipment Intelligence + Knowledge MVP** | Manufacturer → EquipmentModel → Symptom/ErrorCode → FailureCause → TroubleshootingProcedure; minimal read APIs; Files for attachments. |
| **2 — Supplier Network** | SupplierProfile linked to Core Company; SupplierCapability; admin onboarding flows. |
| **3 — Service Marketplace** | ServiceRequest → match → Assignment → outcome; notifications and Analytics hooks. |
| **4 — Parts Marketplace** | Catalog and checkout aligned with Core Billing; strict separation from service fulfillment aggregates. |
| **5 — AI Diagnostics** | Retrieval-augmented diagnostic assistant using orchestration policies; audit trail. |
| **6 — Lead & Demand Engine** | Qualification, routing rules; integration with Growth Engine for attribution. |
| **7 — Market Intelligence** | Aggregations, dashboards, scheduled snapshots. |
| **8 — Hardening** | Performance, observability, contract tests with Core; optional graph projection. |

---

## Document control

| Item | Value |
|------|--------|
| Audience | Engineering, product, architecture |
| Status | Draft — domain alignment |
| Language | English (technical standard for this document) |

---

*End of document.*
