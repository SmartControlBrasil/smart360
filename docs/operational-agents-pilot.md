# Operational agents pilot

## Objetivo

Rotina operacional para alimentar o painel `/app/operations/health/` com sinais dos agentes existentes:

- `maintenance-agent`
- `scheduling-agent`

Os agentes continuam em nível `PROPOSE`, com aprovação humana obrigatória para qualquer proposta. A rotina não usa LLM e não cria novos agentes.

## Como rodar

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

## Verificação depois da execução

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

## Dependências para piloto real

A utilidade das recomendações depende de dados reais e atualizados de cliente, principalmente:

- ativos, criticidade, planos preventivos e eventos de falha;
- ordens de serviço e histórico de intervenções;
- visitas agendadas, técnicos, disponibilidade e risco de SLA;
- vínculos corretos entre empresa, cliente de manutenção e sites ativos.
