# Roadmap incremental de refatoração — Smart360

Plano conservador alinhado ao `.cursorrules`: evolução por módulos, sem big bang, preservando produção e testes.

---

## Curto prazo (0–30 dias)

### Governança dos apps

- [x] Publicar `apps-inventory.md` com status de cada módulo.
- [x] Publicar `ai-cluster.md` com grafo e regra de gateway.
- [ ] Revisar inventário com o time e marcar apps **deprecado** explicitamente (se houver).

### Resolver órfãos

- [x] Desativar rota `/visual-3d/` com comentário em `config/urls.py`.
- [x] Teste garantindo que rotas `visual_3d` retornam 404.
- [ ] Decidir destino de `client_portal` (stub → feature do shell).
- [ ] Documentar `ai_shared` como biblioteca (não registrar como app).

### Testes mínimos

- [x] `automation` — já coberto em `tests.py` (webhook completo).
- [x] `market_core` — models centrais (`tests/test_models.py`).
- [x] `smart_system` — catálogo `EquipmentModel` + `CustomerEquipment`.
- [ ] Expandir smoke tests do `admin_shell` (1–2 rotas por grupo).

### Iniciar fatiamento `admin_shell`

- [x] Plano em `admin-shell-split-plan.md`.
- [ ] Fase 1: extrair mixins + `dashboard.py` (próximo PR).

---

## Médio prazo (30–90 dias)

### Fortalecer `smart_system`

- Testes de OS corretiva/preventiva com escopo tenant.
- Mover lógica de `dashboard_views.py` para use cases quando crescer.
- Completar migração conceitual `Asset` → `EquipmentModel` + `CustomerEquipment`.

### Funil comercial E2E

- Teste integrado: lead Lívia → proposta `growth_engine` → encaminhamento operacional.
- Sem alterar regras consultivas da Lívia.

### `market_core` com testes e contratos

- Testes de pedido multi-item e vendor.
- Documentar API interna usada por `caneca_de_garagem` e `marketplace_ecom`.

### Documentação AI cluster

- [x] `ai-cluster.md` publicado.
- [ ] Auditoria de chamadas diretas a LLM fora de `livia_assistant` e `ai_automation_center`.
- [ ] Mover `ai_shared` → `shared_kernel/ai/` com reexports.

### Fatiamento `admin_shell` (fases 2–3)

- Billing, marketplace, AI em arquivos separados.
- Criar `selectors/` para queries pesadas.

---

## Longo prazo (90+ dias)

### Consolidar IA

- Reduzir superfície dos 11 apps apenas onde houver duplicação comprovada.
- Gateway único de execução LLM em `ai_automation_center`.
- Métricas de custo e timeout centralizados.

### Evoluir marketplace

- Unificar URLs legadas `/caneca/` e `/caneca-de-garagem/` com redirecionamento 301.
- Escalar `marketplace_technicians` após `market_core` estável.

### Frontend institucional — fase 2

- Extrair inline styles restantes de `index.html`.
- Alinhar meta/title com copy atual.
- **Somente com tarefa explícita de frontend.**

### Smart System como produto SaaS principal

- Dashboards separados: Visão Geral, Operação, Engenharia & TPM.
- TPM, confiabilidade (MTTR/MTBF), PMOC como diferenciais comerciais.
- Onboarding tenant → primeiro equipamento → primeira OS em fluxo guiado.

---

## O que não fazer agora

- **Não** refatorar todos os apps para DDD perfeito de uma vez.
- **Não** fundir os 11 apps AI sem mapa de dependências validado.
- **Não** criar novos apps “center” para CRUD simples.
- **Não** duplicar billing, files, identity ou core_platform.
- **Não** mexer no frontend institucional sem tarefa específica.
- **Não** remover funcionalidades do painel para “limpar” o monólito.
- **Não** registrar `visual_3d` em produção sem testes e decisão de produto.

---

## Métricas de sucesso

| Indicador | Meta curto prazo |
|-----------|------------------|
| `manage.py check` | Sempre verde |
| Testes dos módulos tocados | 100% passando |
| Rotas órfãs | Zero |
| `admin_shell/views.py` | Plano Fase 1 executado |
| Documentos em `docs/architecture/` | 4 arquivos mantidos |

---

## Referências

- `docs/architecture/apps-inventory.md`
- `docs/architecture/ai-cluster.md`
- `docs/architecture/admin-shell-split-plan.md`
- `.cursorrules` — regras de arquitetura progressiva
