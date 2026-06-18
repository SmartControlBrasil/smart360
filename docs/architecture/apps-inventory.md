# Inventário técnico dos apps — Smart360

Documento gerado para governança incremental do monorepo Django.  
**Total de pastas em `apps/`:** 48 módulos (excluindo `__init__.py` e `__pycache__`).  
**Registrados em `INSTALLED_APPS` (`LOCAL_APPS`):** 45.  
**Fora de `INSTALLED_APPS`:** `ai_shared`, `client_portal`, `visual_3d`.

Legenda de status sugerido:

| Status | Significado |
|--------|-------------|
| **core** | Plataforma multi-tenant, identidade, billing, infra |
| **receita** | Funil comercial, leads, site institucional |
| **produto** | Valor operacional entregue ao cliente |
| **suporte** | Painel, relatórios, busca, configuração |
| **experimental** | MVP, rota desativada ou cobertura mínima |
| **legado** | Mantido por compatibilidade |
| **biblioteca** | Contratos/interfaces, não é app Django |
| **stub** | Esqueleto sem produto completo |

---

## Tabela geral

| Nome | INSTALLED_APPS | urls.py | models reais | tests | DDD (d/a/i) | Rotas principais | Dependências aparentes | Status | Recomendação |
|------|----------------|---------|--------------|-------|-------------|------------------|------------------------|--------|--------------|
| `access_control_center` | Sim | API | Sim | Sim | Sim | `/api/v1/access-control/` | `identity`, `roles`, `smart_system` | suporte | manter |
| `admin_shell` | Sim | Sim | Não | Sim (1 arquivo) | Não | `/app/…` (painel interno) | Quase todos os módulos | suporte | documentar + fatiar views |
| `ai_agents_center` | Sim | API | Sim | Sim | Sim | `/api/v1/ai-agents/` | `ai_shared`, `ai_decision_engine`, `ai_policy_studio` | experimental | documentar + adicionar testes |
| `ai_automation_center` | Sim | API | Sim | Sim | Sim | `/api/v1/ai/` | Gateway interno de tarefas IA | experimental | manter como gateway |
| `ai_autonomous_ops` | Sim | API | Sim | Sim | Parcial | `/api/v1/ai-autonomy/` | `ai_decision_engine`, `ai_shared` | experimental | documentar |
| `ai_decision_engine` | Sim | API | Sim | Sim | Parcial | `/api/v1/ai-decisions/` | `ai_shared`, `smart_system` | experimental | manter |
| `ai_digital_twin` | Sim | API | Sim | Sim | Parcial | `/api/v1/ai-digital-twins/` | `smart_system` | experimental | documentar |
| `ai_experimentation_framework` | Sim | API | Sim | Sim | Parcial | `/api/v1/ai-experiments/` | `ai_policy_studio` | experimental | documentar |
| `ai_knowledge_graph` | Sim | API | Sim | Sim | Parcial | `/api/v1/ai-knowledge-graph/` | `knowledge_engine` | experimental | documentar |
| `ai_optimization_loop` | Sim | API | Sim | Sim | Parcial | `/api/v1/ai-optimization/` | `ai_agents_center`, `ai_simulation_engine` | experimental | documentar |
| `ai_policy_studio` | Sim | API | Sim | Sim | Parcial | `/api/v1/ai-policies/` | `ai_agents_center` | experimental | documentar |
| `ai_shared` | **Não** | Não | Não | **Não** | Não | — | `ai_agents_center`, `ai_decision_engine`, `smart_system` | biblioteca | manter como biblioteca |
| `ai_simulation_engine` | Sim | API | Sim | Sim | Parcial | `/api/v1/ai-simulations/` | `ai_optimization_loop` | experimental | documentar |
| `ai_voice_ops` | Sim | API | Sim | Sim | Parcial | `/api/v1/ai-voiceops/` | `companies`, `smart_system` | experimental | documentar |
| `analytics_platform` | Sim | API | Sim | Sim | Sim | `/api/v1/analytics/` | `billing`, `growth_engine` | suporte | manter |
| `audit` | Sim | Não | Sim | Sim | Não | — (serviço interno) | `core`, vários módulos | core | manter |
| `automation` | Sim | Sim | Sim | Sim (`tests.py`) | Não | `/automation/webhooks/<slug>/` | `growth_engine` | suporte | manter (testes existentes) |
| `backoffice` | Sim | API | Sim | Sim | Sim | `/api/v1/backoffice/` | `core`, `companies` | suporte | manter |
| `billing` | Sim | API | Sim | Sim | Sim | `/api/v1/billing/` | `companies` | core | manter |
| `caneca_de_garagem` | Sim | Web + API | Sim | Sim | Sim | `/caneca/`, `/caneca-de-garagem/`, `/api/v1/caneca-de-garagem/` | `market_core` | produto | manter |
| `client_portal` | **Não** | Não | Não | Sim (MVP) | Não | — (lógica em `admin_shell`) | `smart_system`, `admin_shell` | stub | fundir futuramente |
| `companies` | Sim | API | Sim | Sim | Não | `/api/v1/companies/` | `users`, `identity` | core | manter |
| `configuration_center` | Sim | API | Sim | Sim | Sim | `/api/v1/configuration/` | `core` | suporte | manter |
| `core` | Sim | API | Sim | Sim | Sim | `/api/v1/core/`, `/health/` | — (núcleo) | core | manter |
| `files_center` | Sim | API | Sim | Sim | Sim | `/api/v1/files/` | `core` | core | manter |
| `global_search` | Sim | API | Sim | Sim | Sim | `/api/v1/search/` | vários índices | suporte | manter |
| `growth_engine` | Sim | API + dashboard | Sim | Sim (7 arquivos) | Sim | `/api/v1/growth/` | `livia_assistant`, `companies` | receita | manter + E2E |
| `identity` | Sim | API | Sim | Sim | Sim | `/api/v1/auth/`, `/api/v1/identity/` | `users` | core | manter |
| `institutional` | Sim | Sim | Não | Sim | Não | `/`, `/solucoes/`, `/contato/`, etc. | — (público) | receita | manter |
| `integration_bus` | Sim | API | Sim | Sim | Sim | `/api/v1/integration-bus/` | `core` | core | manter |
| `knowledge_engine` | Sim | API | Sim | Sim | Sim | `/api/v1/knowledge/` | `livia_assistant` | suporte | manter |
| `livia_assistant` | Sim | Sim | Sim | Sim (14 arquivos) | Não | `/livia/` | `growth_engine`, `knowledge_engine` | receita | manter |
| `market_core` | Sim | Não | Sim | Sim | Não | — (hub de dados) | `companies`, `users` | produto | adicionar testes |
| `marketplace_analytical` | Sim | API | Sim | Sim | Sim | `/api/v1/marketplace-analytical/` | `market_core` | produto | manter |
| `marketplace_ecom` | Sim | Sim | Sim | Sim | Não | `/marketplace/` | `market_core` | produto | manter |
| `marketplace_technicians` | Sim | API | Sim | Sim | Sim | `/api/v1/marketplace-technicians/` | `market_core`, `ai_agents_center` | produto | manter |
| `media_library` | Sim | dashboard | Sim | Sim | Não | via `admin_shell` | `files_center` | suporte | manter |
| `notification_center` | Sim | API | Sim | Sim | Sim | `/api/v1/notifications/` | `core` | core | manter |
| `observability_center` | Sim | API | Sim | Sim | Sim | `/api/v1/observability/` | `core` | core | manter |
| `public_api` | Sim | Sim | Sim | Sim | Não | `/api/public/v1/` | `smart_system` | suporte | manter |
| `reporting_center` | Sim | API | Sim | Sim | Sim | `/api/v1/reporting/` | vários | suporte | manter |
| `roles` | Sim | API | Sim | Sim | Não | `/api/v1/roles/` | `identity`, `companies` | core | manter |
| `scheduling_center` | Sim | API | Sim | Sim | Sim | `/api/v1/scheduling/` | `smart_system` | suporte | manter |
| `smart_site_factory` | Sim | Web + API | Sim | Sim | Sim | `/api/v1/site-factory/` | `core` | produto | manter |
| `smart_system` | Sim | API + dashboard | Sim | Sim (7 arquivos) | Sim | `/api/v1/smart-system/` | `companies`, `ai_shared` | produto | adicionar testes |
| `technical_portal` | Sim | Sim | Sim | Sim | Não | `/portal/` | `smart_system` | legado | documentar |
| `users` | Sim | Sim + API | Sim | Sim | Não | `/login/`, `/api/v1/users/` | `identity`, `companies` | core | manter |
| `visual_3d` | **Não** | Sim | Não | Sim | Não | ~~`/visual-3d/`~~ (desativada) | `market_core`, `caneca_de_garagem` | experimental | remover rota / registrar futuramente |

> **DDD (d/a/i):** possui pastas `domain/`, `application/` e/ou `infrastructure/`.

---

## Apps com atenção especial

### `admin_shell`

- **Papel:** shell visual Attex do painel interno; concentra rotas `/app/…`.
- **Risco:** `views.py` com ~4.962 linhas e ~100 classes/funções; apenas 1 arquivo de teste.
- **Dependências:** importa views de `growth_engine`, `livia_assistant`, `smart_system`, `caneca_de_garagem`, `companies`, `media_library` e dezenas de views locais.
- **Recomendação:** fatiamento incremental documentado em `admin-shell-split-plan.md`; expandir `admin_shell/services/` e `selectors/`.

### `smart_system`

- **Papel:** núcleo TPM/manutenção (OS, equipamentos, contratos, preventivas).
- **Arquitetura:** DDD parcial (`domain/`, `application/`, `infrastructure/`).
- **Escopo tenant:** `SmartSystemScopeService` maduro.
- **Recomendação:** mais testes de fluxo crítico (equipamento, OS, tenant); evoluir use cases.

### `livia_assistant`

- **Papel:** assistente consultivo + coleta de lead.
- **Testes:** melhor cobertura relativa do projeto (14 arquivos).
- **Recomendação:** manter; extrair `domain/` só quando regras de lead crescerem.

### `growth_engine`

- **Papel:** leads, propostas comerciais, integração n8n, dashboards.
- **Recomendação:** testes E2E lead → proposta → encaminhamento operacional.

### `institutional`

- **Papel:** site público Smart Control Brasil (`index.html`, páginas de serviço).
- **Recomendação:** manter enxuto; frontend em tarefa dedicada.

### `market_core`

- **Papel:** hub de vendor/produto/pedido compartilhado por marketplace e caneca.
- **Recomendação:** testes de models (adicionados nesta tarefa); não escalar marketplace sem estabilizar.

### `marketplace_ecom`

- **Papel:** vitrine e-commerce (`/marketplace/`).
- **Recomendação:** manter; depende de `market_core`.

### `visual_3d`

- **Estado:** app experimental, **não** em `INSTALLED_APPS`; rota pública **desativada** em `config/urls.py`.
- **Recomendação:** reativar somente após registrar em `LOCAL_APPS` + testes de rota.

### `ai_shared`

- **Estado:** biblioteca de interfaces (`agent_coordinator`, `decision_engine`, `triggers`, `autonomous_ops`).
- **Usado por:** `smart_system`, `ai_agents_center`, `ai_decision_engine`, `marketplace_technicians`.
- **Recomendação:** manter como biblioteca; migrar para `shared_kernel/` no médio prazo.

### `automation`

- **Papel:** webhooks de automação (`/automation/webhooks/<slug>/`).
- **Testes:** `tests.py` cobre models, token, JSON inválido e fluxo de lead.
- **Recomendação:** manter; não duplicar pasta `tests/` (conflito com `tests.py`).

### `client_portal`

- **Estado:** stub; UI real vive em `admin_shell/views.py` + `admin_shell/services/client_portal.py`.
- **Recomendação:** fundir futuramente como feature do shell ou virar app quando houver models próprios.

### Cluster `ai_*` (11 apps instalados + `ai_shared`)

Ver detalhamento em `ai-cluster.md`. Recomendação geral: **documentar dependências; não fundir sem mapa; usar `ai_automation_center` como gateway.**

---

## Decisões recomendadas para os próximos 30 dias

1. **Manter rota `/visual-3d/` desativada** até decisão explícita de produto e registro em `INSTALLED_APPS`.
2. **Não criar novos apps** — usar módulos existentes e `admin_shell/services/`.
3. **Iniciar fatiamento do `admin_shell`** pelo grupo `dashboard.py` (3 views simples) na próxima iteração segura.
4. **Testes** em `smart_system` (equipamento/tenant) e `market_core` — concluído nesta tarefa; `automation` já tinha `tests.py`.
5. **Publicar e revisar** `ai-cluster.md` com o time antes de qualquer consolidação AI.
6. **Funil comercial:** um teste E2E `institutional → livia → growth_engine` (sem alterar regras de negócio).
7. **Documentar** alias `core_platform` → `apps.core` no onboarding (README ou wiki interna).
8. **Não mexer** no frontend institucional sem tarefa específica de copy/CSS.
9. **Tratar `client_portal`** como feature do shell até existir bounded context próprio.
10. **Revisar duplicidade** `/caneca/` vs `/caneca-de-garagem/` — documentar como legado, unificar só com redirecionamento 301 planejado.
