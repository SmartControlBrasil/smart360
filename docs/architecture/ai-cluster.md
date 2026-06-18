# Cluster AI — Smart360

Documentação de governança do cluster de inteligência artificial.  
**Escopo:** inventariar, orientar e reduzir acoplamento invisível — **sem refatoração nesta fase**.

---

## Apps do cluster

| App | INSTALLED_APPS | DDD (d/a/i) | Papel esperado | Maturidade |
|-----|----------------|-------------|----------------|------------|
| `ai_automation_center` | Sim | Sim | **Gateway interno** de tarefas/prompts/execuções IA | Operacional (simulação interna) |
| `ai_agents_center` | Sim | Sim | Orquestração de agentes, copilots, triggers operacionais | Experimental |
| `ai_decision_engine` | Sim | Parcial | Classificação, políticas, aprovações de decisão | Experimental |
| `ai_simulation_engine` | Sim | Parcial | Cenários e simulações what-if | Experimental |
| `ai_optimization_loop` | Sim | Parcial | Feedback, propostas de otimização, learning loop | Experimental |
| `ai_policy_studio` | Sim | Parcial | Regras e avaliação de políticas | Experimental |
| `ai_experimentation_framework` | Sim | Parcial | A/B, variantes, métricas de experimento | Experimental |
| `ai_autonomous_ops` | Sim | Parcial | Execução autônoma com guardrails | Experimental |
| `ai_digital_twin` | Sim | Parcial | Gêmeos digitais de ativos/operação | Experimental |
| `ai_knowledge_graph` | Sim | Parcial | Projeção de grafo de conhecimento | Experimental |
| `ai_voice_ops` | Sim | Parcial | Interações de voz / voice ops | Experimental |
| `ai_shared` | **Não** | Não | **Biblioteca** de interfaces entre apps AI e domínio | Contratos |

---

## Rotas API expostas

| Prefixo | App |
|---------|-----|
| `/api/v1/ai/` | `ai_automation_center` |
| `/api/v1/ai-agents/` | `ai_agents_center` |
| `/api/v1/ai-decisions/` | `ai_decision_engine` |
| `/api/v1/ai-simulations/` | `ai_simulation_engine` |
| `/api/v1/ai-optimization/` | `ai_optimization_loop` |
| `/api/v1/ai-policies/` | `ai_policy_studio` |
| `/api/v1/ai-experiments/` | `ai_experimentation_framework` |
| `/api/v1/ai-autonomy/` | `ai_autonomous_ops` |
| `/api/v1/ai-digital-twins/` | `ai_digital_twin` |
| `/api/v1/ai-knowledge-graph/` | `ai_knowledge_graph` |
| `/api/v1/ai-voiceops/` | `ai_voice_ops` |

Painel interno: dezenas de views em `admin_shell/views.py` (prefixo `AI*`) espelham esses centers.

---

## Papel esperado de cada app

### `ai_automation_center` — gateway recomendado

- Modela `AITaskRequest`, `AITaskExecution`, `PromptTemplate`, `AutomationRule`.
- `AITaskService.run_task()` hoje **simula** saída (`internal-simulated`) — ponto natural para plugar provider real.
- **Deve ser o único ponto** de execução de tarefas LLM genéricas do painel/API.

### `ai_agents_center` — orquestração

- Agentes de manutenção, scheduling, profitability, marketplace, anomaly.
- Copilots: manager, technician, client portal.
- Depende de `ai_decision_engine`, `ai_policy_studio`, `ai_experimentation_framework`.

### `ai_decision_engine` — governança de decisão

- Classificação, políticas, aprovações, trilha de auditoria.
- Integra com `ai_autonomous_ops` via `ai_shared`.

### Apps de suporte analítico/simulação

- `ai_simulation_engine`, `ai_optimization_loop`, `ai_experimentation_framework`, `ai_policy_studio`: ciclo **simular → medir → otimizar → experimentar**.

### Apps de operação avançada

- `ai_autonomous_ops`: execução com guards e incidentes.
- `ai_digital_twin`, `ai_knowledge_graph`, `ai_voice_ops`: capacidades especializadas, ainda experimentais.

---

## Onde `ai_shared` é usado

`ai_shared` expõe factories lazy para evitar import circular:

| Interface | Implementação real |
|-----------|------------------|
| `get_agent_coordinator()` | `ai_agents_center.services.orchestrator.AgentCoordinatorService` |
| `get_decision_orchestrator()` | `ai_decision_engine` |
| `get_decision_execution_service()` | `ai_decision_engine` |
| `get_autonomous_operations_service()` | `ai_autonomous_ops` |
| `get_*_agent_trigger_service()` | triggers em `ai_agents_center` |

**Consumidores diretos:**

- `smart_system` — `maintenance_service`, `scheduling_service`, `quote_service`, `maintenance_contract_service`
- `ai_agents_center` — orchestrator, triggers
- `ai_decision_engine` — orchestrator, approvals
- `ai_autonomous_ops` — orchestrator
- `marketplace_technicians` — `marketplace_service`

**Risco:** `ai_shared` em `apps/` sem testes e sem registro Django confunde onboarding. Tratar como **biblioteca compartilhada**.

---

## Risco de acoplamento

1. **Grafo denso:** `ai_agents_center` importa decision, policy, experimentation; `smart_system` dispara triggers via `ai_shared`.
2. **UI monolítica:** `admin_shell/views.py` concentra ~25 views `AI*` acopladas ao shell.
3. **Testes smoke:** maioria dos apps AI tem `test_api.py` genérico — pouca cobertura de orquestração cruzada.
4. **LLM fora do gateway:** `livia_assistant` possui `OpenAILiviaAIClient` próprio (provider configurável). Isso é aceitável para o produto Lívia, mas deve permanecer isolado — **outros módulos não devem replicar o padrão**.

---

## Regra recomendada — gateway de IA

> **Nenhum app de domínio ou center deve chamar provider LLM (OpenAI, Anthropic, etc.) diretamente.**

Exceções documentadas:

- **`livia_assistant`:** cliente IA dedicado ao widget consultivo, com fallback e settings próprios (`LIVIA_AI_PROVIDER`, `OPENAI_API_KEY`).
- **`ai_automation_center`:** ponto central para tarefas genéricas do ecossistema.

Demais módulos devem:

1. Montar payload de tarefa (`task_type`, `input_payload`, `source_module`).
2. Chamar `ai_automation_center` (serviço ou API interna).
3. Tratar timeout, fallback e logs sem dados sensíveis.

---

## Fluxo recomendado

```text
smart_system / livia_assistant / growth_engine
        │
        ▼
  gateway/serviço interno de IA
  (ai_automation_center · AITaskService)
        │
        ▼
  provider externo (OpenAI, etc.)
        │
        ▼
  resposta normalizada + auditoria
```

Para **agentes autônomos** com aprovação humana:

```text
trigger (smart_system / marketplace)
        → ai_agents_center (trigger service)
        → ai_decision_engine (classificação + política)
        → aprovação no admin_shell
        → ai_autonomous_ops (execução com guards)
```

---

## Próximos passos (sem refatorar agora)

1. Auditar imports de `openai` / `anthropic` no repositório; listar exceções permitidas.
2. Documentar contrato de `AITaskService.run_task()` como API interna estável.
3. Mover `ai_shared` para `shared_kernel/ai/` em tarefa futura (com reexports temporários).
4. Adicionar teste de integração mínimo: trigger maintenance → decision stub → sem execução externa.
5. Não fundir os 11 apps até o grafo acima estar validado em produção/staging.
6. Novos recursos AI: preferir estender `ai_automation_center` + `ai_agents_center` antes de criar app `ai_*` novo.
