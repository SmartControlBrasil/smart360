# AI Policy Studio

O `Policy Studio` e a camada central de governanca da IA do SMART360. Ele centraliza regras, escopos, versoes, avaliacoes e simulacoes de policy para agentes, copilots, Decision Engine, Simulation Engine e Auto-Optimization Loop.

## Objetivo

- definir governanca de IA por tenant, site, modulo, acao, agente e risco
- controlar autonomia e necessidade de aprovacao
- versionar e simular mudancas de policy
- auditar toda avaliacao aplicada em runtime

## Arquitetura

O modulo esta em `apps/ai_policy_studio` e foi dividido em:

- `models.py`: policies, scopes, rules, versions, evaluations e simulations
- `services/engine.py`: matching central e decisao `allow`, `deny`, `require_approval`, `escalate`
- `services/versioning.py`: snapshot e historico de versoes
- `services/simulation.py`: simulacao basica de impacto da policy sobre a operacao recente
- `api/`: CRUD, avaliacao e simulacao

## Modelo

### `Policy`

Container principal da governanca, com:

- `tenant_scope`
- `is_global`
- `status`
- `version`

### `PolicyScope`

Escopo de aplicacao da policy:

- company
- site
- module
- action_type
- agent_slug
- copilot_key
- priority

### `PolicyRule`

Regra efetiva avaliada pelo engine:

- `action_type`
- `risk_level`
- `autonomy_level`
- `requires_approval`
- `allowed`
- `result`
- `approver_roles`
- `conditions`

### `PolicyVersion`

Snapshot versionado da configuracao da policy e suas regras.

### `PolicyEvaluation`

Trilha auditavel das avaliacoes feitas em runtime.

### `PolicySimulationRun`

Persistencia de simulacao de impacto antes de aplicar mudancas de policy.

## Engine de avaliacao

O `PolicyStudioEngine`:

1. resolve scopes ativos que combinam com tenant/site/modulo/acao/agente/copilot
2. ordena por especificidade e prioridade
3. encontra a primeira regra compativel
4. retorna um resultado estruturado com:
   - `allow`
   - `deny`
   - `require_approval`
   - `escalate`
5. registra `PolicyEvaluation`
6. emite observabilidade

Se nenhuma policy ativa casar, o comportamento default nesta rodada e `deny`.

## Integracoes em runtime

### Agents Center

- `run_agent` passa por `PolicyStudioEngine`
- proposals geradas pelos agentes sao filtradas pelo studio antes de entrarem no Decision Engine

### Decision Engine

- toda action proposal classificada passa pelo `PolicyStudioEngine`
- o studio pode:
  - bloquear
  - exigir aprovacao
  - escalonar
  - complementar explainability

### Simulation Engine

- simulacoes disparadas por decisoes passam pelo `PolicyStudioEngine`
- tenant pode bloquear tipos de simulacao especificos

### Auto-Optimization Loop

- approval de `OptimizationProposal` passa por `PolicyStudioEngine`
- nenhuma alteracao supervisionada e aplicada sem policy valida

## Policies seed desta rodada

### `global-decision-governance`

- `mark_asset_attention` low risk -> `allow`
- `create_work_order_proposal` high risk -> `require_approval`
- qualquer acao `critical` -> `escalate`

### `global-agent-governance`

- `run_agent` -> `allow`
- `assign_marketplace_candidate_proposal` high risk -> `require_approval`

### `global-optimization-governance`

- `approval_requirement_adjustment` -> `require_approval`
- `heuristic_config_adjustment` -> `require_approval`

## Versionamento

Toda policy pode gerar snapshots versionados por API ou por atualizacao.

Snapshot inclui:

- dados principais da policy
- scopes
- rules

## Simulacao de policy

Foi implementada a base de simulacao de impacto antes da aplicacao:

- quantas decisoes recentes seriam afetadas
- distribuicao de status observada
- indice de risco operacional
- volume de autoexecucao atual

## Observabilidade

Eventos emitidos:

- `policy.evaluated`
- `policy.applied`
- `policy.denied`
- `policy.overridden`

## API

Base: `/api/v1/ai-policies/`

- `GET/POST /policies/`
- `PATCH /policies/{public_id}/`
- `POST /policies/{public_id}/version/`
- `POST /policies/{public_id}/simulate/`
- `POST /policies/evaluate/`
- `GET/POST /rules/`
- `GET/POST /scopes/`
- `GET /versions/`
- `GET /evaluations/`
- `GET /simulations/`

## Admin Shell

Tela:

- `/app/ai-agents/policies/`

Contem:

- policies ativas
- scopes e regras
- historico de versoes
- simulacoes de policy
- logs de avaliacao

## Limitacoes atuais

- simulacao de impacto ainda usa agregacao operacional simples
- rollback automatico para versao anterior ainda nao foi exposto como acao dedicada
- conditions suportam matching simples por igualdade
- copilots ainda usam apenas governanca central de engine, sem editor visual especializado por resposta

## Proximos passos

- rollback direto de versao
- multi-step approval por policy
- conditions mais ricas
- compliance packs por setor/tenant
- exportacao de auditoria para revisao externa
