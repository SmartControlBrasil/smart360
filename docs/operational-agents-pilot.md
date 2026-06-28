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

2. Rodar o smoke test operacional sem depender de dados reais:

```bash
.venv/bin/python manage.py test apps.ai_agents_center.tests.test_operational_runner
```

Esse teste valida que:

- o registry contém `maintenance-agent` e `scheduling-agent`;
- `run_operational_agents --dry-run` planeja os dois agentes sem executar análise real;
- nenhum `AgentRun` é criado no dry-run;
- o contexto de `/app/operations/health/` é montado sem erro.

3. Fazer um dry-run manual da rotina:

```bash
.venv/bin/python manage.py run_operational_agents --dry-run
```

A saída esperada deve conter linhas `PLANNED maintenance-agent` e `PLANNED scheduling-agent` para cada site ativo encontrado.

## Como rodar a rotina real

```bash
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

## Como interpretar o painel

- Recomendações abertas indicam pontos para triagem operacional. Elas não executam ação sozinhas.
- Propostas pendentes exigem revisão humana antes de qualquer alteração operacional.
- Flags de manutenção destacam ativos em atenção, criticidade ou recorrência de falha.
- Flags de agenda destacam sobrecarga, conflito, risco de SLA ou capacidade ociosa.
- Runs recentes mostram se a rotina executou ou se ainda há apenas planejamento/dry-run.

## Se o dashboard vier vazio

Um painel vazio não significa falha obrigatória. Conferir nesta ordem:

1. Rodar `.venv/bin/python manage.py run_operational_agents --dry-run` e confirmar os dois agentes planejados.
2. Verificar se existem sites ativos para a empresa do usuário logado.
3. Rodar a rotina real sem `--dry-run` para a janela desejada.
4. Confirmar se há dados operacionais suficientes para gerar recomendações, propostas ou flags.
5. Abrir `/app/operations/health/` novamente e verificar também as telas de Recomendações, Propostas, Runs, Maintenance Health e Scheduling Health.

## Dependências para piloto real

A utilidade das recomendações depende de dados reais e atualizados de cliente, principalmente:

- ativos, criticidade, planos preventivos e eventos de falha;
- ordens de serviço e histórico de intervenções;
- visitas agendadas, técnicos, disponibilidade e risco de SLA;
- vínculos corretos entre empresa, cliente de manutenção e sites ativos.
