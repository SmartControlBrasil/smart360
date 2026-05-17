# Checklists Executaveis do Smart System

O modulo de checklists executaveis foi estruturado como a camada operacional de inspecao, padronizacao e execucao tecnica do `Smart System` dentro do `admin_shell`.

## Superficies entregues

- Lista de checklists com KPIs, filtros e carteira operacional
- Detalhe do checklist com estrutura dos itens, vinculos e historico resumido
- Tela de execucao com respostas item a item, progresso e conclusao
- Detalhe da execucao com leitura consolidada de anomalias e observacoes

## Estrutura dos dados mockados

Os mocks estao centralizados em [smart_system_checklists.py](/home/marcelo/Projetos/smart360/apps/admin_shell/services/smart_system_checklists.py) e cobrem:

- cadastro do checklist
- itens do checklist
- execucoes realizadas
- respostas item a item

Cada checklist ja pode se relacionar com:

- ativo
- plano preventivo
- ordem de servico
- cliente e site

## Componentes principais

Os componentes do modulo foram criados em `apps/admin_shell/templates/admin_shell/components/`:

- `checklist_filter_bar.html`
- `checklist_kpi_card.html`
- `checklist_table.html`
- `checklist_status_badge.html`
- `checklist_summary_panel.html`
- `checklist_item_list.html`
- `checklist_history_table.html`
- `checklist_execution_header.html`
- `checklist_execution_progress.html`
- `checklist_execution_item.html`
- `checklist_execution_summary.html`
- `checklist_alert_panel.html`

## Evolucao para dados reais

O proximo passo tecnico natural e trocar o service mockado por query services ligados a entidades reais do bounded context `smart_system`, como:

- `Checklist`
- `ChecklistItem`
- `ChecklistExecution`
- `ChecklistExecutionItem`

## Preparacao para proximas rodadas

O desenho atual ja deixa espaco para:

- geracao automatica de OS corretiva por NOK
- foto/evidencia por item
- assinatura tecnica
- checklist com medicao numerica
- aprovacao e dupla checagem
- execucao mobile-first
- analytics de conformidade e anomalias
