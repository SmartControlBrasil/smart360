# Work Orders

## Visao Geral

O modulo de Ordens de Servico do `Smart System` foi implementado no `admin_shell` como a camada operacional de acompanhamento de corretivas, preventivas, inspeções, calibrações e diagnósticos.

Rotas principais:

- `/app/smart-system/work-orders/`
- `/app/smart-system/work-orders/<codigo>/`
- `/app/smart-system/work-orders/<codigo>/execute/`

## Estrutura

Arquivos centrais:

- `apps/admin_shell/services/smart_system_work_orders.py`
- `apps/admin_shell/templates/admin_shell/smart_system_work_orders_list.html`
- `apps/admin_shell/templates/admin_shell/smart_system_work_order_detail.html`

Componentes:

- `work_order_filter_bar.html`
- `work_order_kpi_card.html`
- `work_order_table.html`
- `work_order_status_badge.html`
- `work_order_priority_badge.html`
- `work_order_sla_badge.html`
- `work_order_summary_panel.html`
- `work_order_status_flow.html`
- `work_order_timeline.html`
- `work_order_alert_panel.html`
- `work_order_action_panel.html`

## Origem dos mocks

Os dados de OS estao centralizados em `smart_system_work_orders.py` e foram modelados para refletir:

- corretiva critica em HVAC
- preventiva planejada de laboratorio
- inspecao em automacao
- OS aguardando peca em ativo de alta demanda
- calibracao concluida com relatorio
- diagnostico em triagem sem responsavel

## Como evoluir para dados reais

Substituir gradualmente os mocks por agregacoes do bounded context `smart_system`:

- `ServiceOrder`
- `Asset`
- `FailureEvent`
- `WorkLog`
- `ServiceOrderChecklistResponse`
- `ServiceDocument`

O contrato visual do template pode ser preservado, trocando apenas a origem dos dados no service.

## Como adicionar novos status

O fluxo operacional usa `WORK_ORDER_STATUS_FLOW`.

Para adicionar uma etapa:

1. incluir a nova etapa na ordem correta do fluxo
2. atualizar os registros com o novo `status_flow`
3. adicionar tratamento visual se a nova etapa exigir destaque proprio

## Proximos passos

- criacao e edicao real de OS
- apontamento de mao de obra
- checklist de execucao
- anexos e evidencias
- modo tecnico de execucao em campo
- workflow de pecas e materiais
- encerramento tecnico e aprovacao
- reabertura e SLA real por tipo/criticidade
