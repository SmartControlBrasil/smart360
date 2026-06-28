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
- nenhum `AgentRun` é criado no dry-run;
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

## Tela para abrir depois da execução

Abrir `/app/operations/health/` e conferir:

- recomendações abertas por agente;
- propostas pendentes de aprovação humana;
- flags abertas de manutenção e agenda;
- últimos `AgentRun` dos agentes operacionais.

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
6. Se a rotina automática já deveria ter rodado, conferir se Beat/worker Celery estão ativos e procurar logs da task `ai_agents_center.run_daily_operational_agents`.
7. Abrir `/app/operations/health/` novamente e verificar também as telas de Recomendações, Propostas, Runs, Maintenance Health e Scheduling Health.

## Dependências para piloto real

A utilidade das recomendações depende de dados reais e atualizados de cliente, principalmente:

- ativos, criticidade, planos preventivos e eventos de falha;
- ordens de serviço e histórico de intervenções;
- visitas agendadas, técnicos, disponibilidade e risco de SLA;
- vínculos corretos entre empresa, cliente de manutenção e sites ativos.
