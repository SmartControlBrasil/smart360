# Plano de fatiamento — `admin_shell`

Análise do monólito `apps/admin_shell/views.py` e proposta incremental de divisão **sem quebrar rotas**.

---

## Métricas atuais

| Métrica | Valor |
|---------|-------|
| Linhas em `views.py` | ~4.962 |
| Classes/funções públicas | ~100 |
| Arquivos de teste | 1 (`tests/test_views.py`) |
| Arquivos em `services/` | ~30 (padrão correto já iniciado) |
| `urls.py` | ~557 linhas (imports extensos) |

---

## Grupos identificados em `views.py`

### 1. Mixins e infraestrutura (~linhas 202–353)

- `ShellContextMixin`, `CMMSOperationalShellMixin`
- `ClientPortalContextMixin`, `ClientPortalScopedResourceTemplateView`
- `TechnicianAppContextMixin`, `TechnicianScopedTemplateView`
- `ScopedResourceTemplateView`, `SetActiveContextView`

**Risco ao mover:** alto — base de quase todas as views.

### 2. App técnico / campo (~linhas 354–1028)

- Login/logout técnico, dashboard, execução de OS, assinaturas, offline sync, copilot técnico, service worker (~25 classes)

### 3. Portal do cliente (~linhas 1029–1669)

- Dashboard, ativos, OS, preventivas, relatórios, orçamentos, contratos, solicitações, copilot (~30 classes)

### 4. Marketplace técnicos (~linhas 1670–1862)

- Dashboard, requests, offers, matching, assignments, reviews (~9 classes)

### 5. Analytics executivo (~linhas 1863–1975)

- `AnalyticsExecutiveDashboardView`, `ExecutiveWarRoom*`, refresh (~5 classes)

### 6. Cluster AI (~linhas 1976–2512)

- Dashboard agentes, copilot manager, briefings, health views, centers (simulation, optimization, policy, etc.), approve/reject (~25 classes)

### 7. Billing admin (~linhas 2513–2734)

- Planos, contratos, faturas, ações de status (~9 classes)

### 8. Shell geral (~linhas 2735–2916)

- `ObservabilityDashboardView`, `DashboardView`, `ModulePageView`

### 9. Smart System CMMS (~linhas 2917–4962)

- Operações, confiabilidade, ativos, catálogo `EquipmentModel`, `CustomerEquipment`, clientes, sites, scheduling, peças, estoque, relatórios, orçamentos, contratos, OS, preventivas, falhas, checklists (~55 classes)

---

## Riscos do monólito

1. **Conflitos de merge** frequentes em qualquer feature do painel.
2. **Imports circulares** se fatiar sem extrair mixins primeiro.
3. **Testes insuficientes** — regressão visual/permissão difícil de detectar.
4. **`urls.py` frágil** — lista gigante de imports de `.views`.
5. **Lógica já parcialmente extraída** para `services/` — views ainda orquestram demais.

---

## Estrutura futura proposta

```text
apps/admin_shell/
├── views/
│   ├── __init__.py          # reexporta símbolos para compatibilidade com urls.py
│   ├── mixins.py            # ShellContextMixin, CMMS*, ClientPortal*, Technician*
│   ├── dashboard.py         # DashboardView, ModulePageView, ObservabilityDashboardView
│   ├── smart_system.py      # SmartSystem* views
│   ├── growth.py            # (futuro) se views voltarem do growth_engine dashboard
│   ├── marketplace.py       # MarketplaceTechnicians* views
│   ├── ai.py                # AI* views
│   ├── client_portal.py     # ClientPortal* views
│   ├── technician.py        # Technician* views
│   └── billing.py           # Billing* views
├── selectors/               # NOVO — queries read-only complexas
│   ├── __init__.py
│   ├── dashboard.py
│   ├── smart_system.py
│   └── growth.py
└── services/                # MANTER e expandir (já existe)
```

---

## Plano incremental (sem big bang)

### Fase 0 — Documentação e baseline (esta tarefa)

- [x] Inventariar grupos e riscos
- [ ] Garantir smoke tests das rotas críticas do shell (expandir `tests/test_views.py` gradualmente)

### Fase 1 — Mixins + dashboard (baixo risco)

1. Criar `views/mixins.py` — mover apenas mixins e helpers privados pequenos.
2. Criar `views/dashboard.py` — extrair `DashboardView`, `ModulePageView`, `ObservabilityDashboardView` (~90 linhas).
3. Em `views/__init__.py`, reexportar tudo: `from .dashboard import *` etc.
4. Manter `from .views import X` em `urls.py` funcionando via `__init__.py`.

**Por que começar aqui:** grupo pequeno, poucas dependências de forms, services já isolados (`get_dashboard_context`, `get_observability_dashboard_context`).

### Fase 2 — Billing e marketplace (risco médio)

- Extrair `billing.py` e `marketplace.py`.
- Mover selectors de listagem para `selectors/`.

### Fase 3 — AI cluster (risco médio)

- Extrair `ai.py`; depende só de `ShellContextMixin` + services em `services/ai_*`.

### Fase 4 — Client portal e technician (risco alto)

- Muitos forms e mixins específicos; exige mixins já estáveis na Fase 1.

### Fase 5 — Smart System (maior bloco)

- Extrair por subdomínio: `smart_system_work_orders.py`, `smart_system_assets.py`, etc., **ou** um único `smart_system.py` inicial.
- Priorizar views que só delegam para `services/smart_system_*`.

---

## Decisão desta tarefa

**Código não foi movido** — os mixins (`ShellContextMixin` na linha 202) são dependência de todos os grupos. Mover só o dashboard sem extrair mixins primeiro criaria import circular ou duplicação.

A **Fase 1** é a próxima ação segura recomendada (estimativa: 1 PR pequeno, ~150 linhas movidas + reexports).

---

## Compatibilidade de rotas

- `apps/admin_shell/urls.py` usa `from .views import ClassName`.
- Solução: `views/__init__.py` reexporta símbolos; **nenhuma URL name precisa mudar**.
- Validar com `python manage.py check` e `pytest apps/admin_shell/tests/test_views.py`.

---

## Critérios de pronto por fase

| Fase | Critério |
|------|----------|
| 1 | 3 views de dashboard em arquivo próprio; testes shell passando |
| 2 | Billing + marketplace isolados; `urls.py` inalterado em paths |
| 3 | Views `AI*` em `ai.py`; sem novo acoplamento a providers LLM |
| 4 | Portal cliente e técnico separados; forms permanecem em `forms.py` |
| 5 | `views.py` original < 2.000 linhas ou removido |
