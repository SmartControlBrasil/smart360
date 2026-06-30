# Operational agents pilot

## Objetivo

Rotina operacional para alimentar o painel `/app/operations/health/` com sinais dos agentes existentes:

- `maintenance-agent`
- `scheduling-agent`

Os agentes continuam em nível `PROPOSE`, com aprovação humana obrigatória para qualquer proposta. A rotina não usa LLM e não cria novos agentes.

## Checklist antes do piloto

1. Confirmar que o sistema está íntegro:

```bash
.venv/bin/python manage.py check
```

2. Rodar o smoke test operacional sem depender de dados reais e validar o schedule do Celery Beat:

```bash
.venv/bin/python manage.py test apps.ai_agents_center.tests.test_operational_runner
```

Esse teste valida que:

- o registry contém `maintenance-agent` e `scheduling-agent`;
- `run_operational_agents --dry-run` planeja os dois agentes sem executar análise real;
- nenhum `AgentRun`, recomendação, proposta ou flag é criado no dry-run;
- o contexto de `/app/operations/health/` é montado sem erro;
- a task `ai_agents_center.run_daily_operational_agents` está registrada no Beat às 06:30.

3. Criar ou atualizar dados mínimos do piloto operacional, quando não houver dados reais seguros para demonstração:

```bash
.venv/bin/python manage.py seed_operational_pilot_data
```

Por padrão, o seed cria a empresa `Empresa Piloto Smart360`, o site `Unidade Piloto Operacional`, ativos `OPS-PILOT-*`, técnicos locais `@smart360.local`, ordens `OPS-PILOT-OS-*`, falhas recentes e visitas para o próximo dia. O command é idempotente: rodar duas vezes no mesmo dia atualiza os mesmos registros principais, sem duplicar empresa, site, ativos, OS ou visitas.

Opções úteis:

```bash
.venv/bin/python manage.py seed_operational_pilot_data --company-name "Empresa Piloto Cliente A" --site-name "Unidade Piloto Cliente A"
.venv/bin/python manage.py seed_operational_pilot_data --reset
```

Use `--reset` somente para remover dados identificáveis do próprio seed. Ele não recria dados na mesma execução e não deve ser usado sobre dados reais.

4. Fazer um dry-run manual da rotina:

```bash
.venv/bin/python manage.py run_operational_agents --dry-run
```

A saída esperada deve conter linhas `PLANNED maintenance-agent` e `PLANNED scheduling-agent` para cada site ativo encontrado.

## Rotina manual

Para preparar dados mínimos e executar manualmente a rotina real:

```bash
.venv/bin/python manage.py seed_operational_pilot_data
.venv/bin/python manage.py run_operational_agents --dry-run
.venv/bin/python manage.py run_operational_agents
```

Opções úteis:

```bash
.venv/bin/python manage.py run_operational_agents --dry-run
.venv/bin/python manage.py run_operational_agents --site-id 123
.venv/bin/python manage.py run_operational_agents --date 2026-06-29
.venv/bin/python manage.py run_operational_agents --force
```

Por padrão, a rotina:

- roda manutenção para os sites ativos no modo `daily_critical_assets`;
- roda agenda para o próximo dia operacional;
- pula execuções já concluídas para o mesmo site, agente e data;
- registra cada execução real em `AgentRun`;
- falha explicitamente se algum agente não executar.

Use `--force` apenas quando a intenção for reprocessar conscientemente a mesma janela operacional.


## Rotina automática via Celery Beat

O piloto operacional também fica agendado no Celery Beat pela entrada `ai-agents-operational-daily-0630`.

- Task: `ai_agents_center.run_daily_operational_agents`
- Horário: todos os dias às 06:30
- Runner usado: `OperationalAgentsRunner.run_daily`
- Agentes executados: `maintenance-agent` e `scheduling-agent`

A task registra logs mínimos de início, fim e erro. Se uma exceção inesperada ocorrer, ela registra `logger.exception` e retorna status `failed`, sem derrubar o worker inteiro.

A idempotência continua no runner: execuções já concluídas para o mesmo site, agente e janela operacional são puladas, salvo uso explícito de `--force` na rotina manual.

Para validar o agendamento no código:

```bash
.venv/bin/python manage.py test apps.ai_agents_center.tests.test_operational_runner
```

## Rotina diária de revisão

1. O Celery Beat roda a task `ai_agents_center.run_daily_operational_agents` às 06:30.
2. O operador abre `/app/operations/review/`.
3. Revisa recomendações abertas e propostas pendentes dos agentes `maintenance-agent` e `scheduling-agent`.
4. Aprova ou rejeita propostas pelo fluxo interno de decisão humana.
5. Marca recomendações como revisadas quando a triagem operacional estiver concluída.
6. Acompanha `/app/operations/health/` para visão de saúde, flags e runs recentes.

A Operational Review Queue aprova/rejeita pelo `AgentCoordinatorService`, que encaminha a proposta para o AI Decision Engine. Quando o `action_type` normalizado tem handler válido, a aprovação humana pode materializar uma alteração operacional controlada, como criação de OS, flag de atenção, ajuste de agenda ou registro auditável. Quando não há handler válido, a proposta fica apenas aprovada/rastreável e a ausência de execução é registrada no audit trail/event log. A fila não envia e-mail, não aciona LLM e não altera sistemas externos.

## Action types e execução downstream

Os agentes operacionais geram aliases de `action_type`. O AI Decision Engine normaliza esses aliases antes de decidir se existe execução downstream.

Action types operacionais com execução real quando aprovados e com payload válido:

- `open_inspection_work_order` -> `create_work_order_proposal`: cria uma `ServiceOrder` controlada.
- `review_preventive_plan` e `reevaluate_preventive_frequency` -> `create_preventive_review_task`: cria OS/tarefa de revisão preventiva.
- `mark_asset_under_watch` -> `mark_asset_attention`: atualiza `AgentAssetAttentionFlag`.
- `create_technical_analysis` e `review_checklist_strategy` -> `create_investigation_task`: registra investigação/evento operacional auditável.
- `reassign_visits_between_technicians`, `block_schedule_for_review`, `move_visit_to_earlier_slot` e `schedule_unassigned_visit` -> `create_schedule_adjustment_proposal`: ajusta visita/agenda controlada.
- `reorder_route_plan` -> `reorder_route_proposal`: marca `RoutePlan` para revisão com ordem proposta.
- `suggest_alternative_technician_via_matching` -> `assign_marketplace_candidate_proposal`: tenta alocação via marketplace quando houver solicitação/candidato válidos.

Action types apenas rastreáveis no piloto:

- Qualquer `action_type` sem policy/handler válido no AI Decision Engine. A aprovação não deve quebrar a fila; ela registra status aprovado e evento `decision.execution.not_available`, sem alterar estado operacional.
- Propostas cujo handler existe, mas o payload não resolve o alvo operacional, podem falhar na execução e ficam auditadas como `decision.execution.failed`; nesse caso houve tentativa real, mas sem materialização.

Diferença prática:

- Proposta apenas rastreável: muda status/auditoria da proposta e da decisão, mas não cria/edita OS, visita, rota, flag ou evento operacional.
- Proposta que altera estado operacional: passa por policy, aprovação humana e handler do Decision Engine; depois cria ou atualiza o artefato operacional correspondente.

## Alertas internos do piloto

O painel `/app/operations/health/` exibe alertas internos simples do piloto operacional. A fila `/app/operations/review/` também mostra um resumo desses alertas para apoiar a rotina diária.

Esses alertas são apenas informativos e internos. Eles não enviam e-mail, não enviam WhatsApp, não executam manutenção, não alteram agenda externa e não acionam LLM.

Alertas atuais:

- Task diária sem execução registrada hoje: nenhum `AgentRun` operacional foi encontrado na data; pode indicar Beat/worker parado ou ausência de execução manual.
- `maintenance-agent` sem run hoje: o agente de manutenção ainda não registrou execução no dia.
- `scheduling-agent` sem run hoje: o agente de agenda ainda não registrou execução no dia.
- Último run de agente falhou: o run mais recente do agente terminou com status `failed` e deve ter seus logs revisados.
- Proposta pendente antiga: existe proposta aguardando decisão humana há mais de 24h; acima de 48h o alerta fica crítico.
- Recomendação aberta antiga: existe recomendação aberta há mais de 48h, sinal de triagem parada.

Diagnóstico recomendado:

1. Abrir `/app/operations/health/` e conferir a seção de alertas internos.
2. Abrir `/app/operations/review/` e revisar propostas/recomendações pendentes.
3. Rodar `.venv/bin/python manage.py run_operational_agents --dry-run` para validar registry, sites e planejamento.
4. Checar logs do Celery worker e do Celery Beat, especialmente a task `ai_agents_center.run_daily_operational_agents`.
5. Se o dry-run estiver correto e a janela operacional já deveria ter rodado, executar manualmente `.venv/bin/python manage.py run_operational_agents`.

## Métricas do piloto operacional

A fila `/app/operations/review/` mostra métricas simples para medir se o piloto está virando decisão humana rastreável:

- Propostas pendentes: decisões que ainda precisam de aprovação ou rejeição humana.
- Propostas aprovadas: propostas aprovadas internamente no período filtrado, sem execução automática de manutenção ou agenda externa.
- Propostas rejeitadas: propostas recusadas pelo operador, idealmente com motivo registrado.
- Recomendações abertas: itens de triagem ainda não revisados.
- Recomendações revisadas: recomendações em status `reviewed`, `accepted`, `dismissed` ou `applied`, conforme campos já existentes.
- Runs no dia: execuções dos agentes no período filtrado.
- Runs com sucesso/falha: leitura rápida para confirmar se a rotina rodou e se algum agente falhou.
- Idade média pendente: tempo médio que propostas pendentes estão aguardando decisão.
- Pendente mais antiga: maior fila parada; quando cresce, normalmente indica falha no processo humano de revisão, não necessariamente falha do agente.
- Última execução por agente: confirmação operacional de que `maintenance-agent` e `scheduling-agent` executaram recentemente.

Use os filtros da Review Queue para ler as métricas por agente, status, data ou site quando necessário. Na rotina diária, a pergunta principal é: existe proposta pendente antiga demais para uma decisão do operador?

## Telas para abrir depois da execução

Abrir `/app/operations/review/` para responder: o que preciso revisar hoje no piloto operacional? Conferir:

- propostas pendentes com ações de aprovar/rejeitar;
- recomendações abertas com ação de marcar como revisada;
- flags relevantes de manutenção e agenda;
- runs de hoje e ontem.

Abrir `/app/operations/health/` para acompanhar saúde operacional agregada:

- recomendações abertas por agente;
- propostas pendentes de aprovação humana;
- flags abertas de manutenção e agenda;
- últimos `AgentRun` dos agentes operacionais.

Diferença prática: a Review Queue é a fila diária de trabalho humano; o Operations Health é o painel de acompanhamento e diagnóstico.

As telas detalhadas permanecem as existentes:

- Recomendações
- Propostas
- Runs
- Maintenance Health
- Scheduling Health

## Dados mínimos para uma demonstração útil

A rotina não exige dados reais para o smoke test, mas uma demo com cliente fica útil quando existem:

- empresa e site operacional ativos;
- cliente de manutenção vinculado à empresa;
- ativos, categorias, criticidade e histórico de falhas ou intervenções;
- ordens de serviço e visitas futuras;
- técnicos e agenda com disponibilidade ou risco de SLA.

Quando usar o seed, trate os registros como massa de demonstração. Eles são marcados por nomes/prefixos estáveis como `Empresa Piloto Smart360`, `Unidade Piloto Operacional`, `OPS-PILOT-*`, `OPS-PILOT-OS-*`, e-mails `@smart360.local` e `metadata.seed_key=operational_pilot` nos models que suportam metadata. Não misture esses registros com dados de cliente real em validações comerciais.

## Como interpretar o painel

- Recomendações abertas indicam pontos para triagem operacional. Elas não executam ação sozinhas.
- Propostas pendentes exigem revisão humana antes de qualquer alteração operacional.
- Flags de manutenção destacam ativos em atenção, criticidade ou recorrência de falha.
- Flags de agenda destacam sobrecarga, conflito, risco de SLA ou capacidade ociosa.
- Runs recentes mostram se a rotina executou ou se ainda há apenas planejamento/dry-run.
- Após 06:30, a ausência de runs novos indica que vale checar Beat, worker Celery e logs da task `ai_agents_center.run_daily_operational_agents`.

## Se o dashboard vier vazio

Um painel vazio não significa falha obrigatória. Conferir nesta ordem:

1. Rodar `.venv/bin/python manage.py seed_operational_pilot_data` se não houver massa real segura para demo.
2. Rodar `.venv/bin/python manage.py run_operational_agents --dry-run` e confirmar os dois agentes planejados.
3. Verificar se existem sites ativos para a empresa do usuário logado.
4. Rodar a rotina real sem `--dry-run` para a janela desejada.
5. Confirmar se há dados operacionais suficientes para gerar recomendações, propostas ou flags.
6. Abrir `/app/operations/review/` para revisar a fila do dia.
7. Se a rotina automática já deveria ter rodado, conferir se Beat/worker Celery estão ativos e procurar logs da task `ai_agents_center.run_daily_operational_agents`.
8. Abrir `/app/operations/health/` novamente e verificar também as telas de Recomendações, Propostas, Runs, Maintenance Health e Scheduling Health.

## Checklist real de produção

Antes de considerar o piloto operacional ativo em produção, confirmar:

1. O serviço principal está de pé:

```bash
systemctl status smart360.service
```

2. Se o deploy expõe units separados, confirmar worker e Beat também.

Exemplos comuns:

```bash
systemctl status smart360-celery-worker.service
systemctl status smart360-celery-beat.service
```

3. Revisar logs do serviço e, quando houver units separadas, acompanhar worker e Beat:

```bash
journalctl -u smart360.service -f
journalctl -u smart360-celery-worker.service -f
journalctl -u smart360-celery-beat.service -f
```

4. Rodar a checagem geral da aplicação:

```bash
.venv/bin/python manage.py check
```

5. Rodar a checagem de runtime operacional, se o command estiver disponível:

```bash
.venv/bin/python manage.py check_operational_agents_runtime
```

6. Validar o smoke manual do piloto:

```bash
.venv/bin/python manage.py run_operational_agents --dry-run
.venv/bin/python manage.py run_operational_agents
```

7. Abrir as telas operacionais:

- `/app/operations/health/`
- `/app/operations/review/`

8. Conferir o fluxo humano diário:

- revisar propostas pendentes na Review Queue;
- aprovar ou rejeitar apenas o que tiver contexto claro;
- tratar propostas aprovadas como decisão rastreável, e não como garantia de execução real;
- confirmar na Health se houve `AgentRun`, flags ou recomendações esperadas depois da janela das 06:30.

9. Interpretar o tipo de problema pela evidência disponível:

- Problema de aplicação Django: `manage.py check` falha, views/commands falham localmente ou o command de runtime acusa registry/config ausentes.
- Problema de worker Celery: o Django responde, mas não aparecem execuções reais após a janela agendada e os logs do worker não mostram a task.
- Problema de Beat/agendamento: a task existe e o worker está saudável, mas o Beat não agenda `ai_agents_center.run_daily_operational_agents` às 06:30 ou a entrada não aparece na configuração.
- Problema de dados vazios: o command de runtime mostra registry e Beat OK, mas não há `AgentRun` recentes nem propostas pendentes; nesse caso o ambiente está pronto, só falta massa operacional.

10. Interpretar a aprovação humana:

- status `approved` sem execução significa decisão rastreável;
- status `executed` com decisão e `DecisionExecution.succeeded` indicam alteração operacional real;
- quando o handler não existe, a aprovação segue sem quebrar a fila e o evento fica registrado como ausência de execução downstream.

11. Se a janela automática já deveria ter rodado, procurar primeiro o log da task `ai_agents_center.run_daily_operational_agents` e depois revisar se Beat e worker estão ativos.

## Dependências para piloto real

A utilidade das recomendações depende de dados reais e atualizados de cliente, principalmente:

- ativos, criticidade, planos preventivos e eventos de falha;
- ordens de serviço e histórico de intervenções;
- visitas agendadas, técnicos, disponibilidade e risco de SLA;
- vínculos corretos entre empresa, cliente de manutenção e sites ativos.
