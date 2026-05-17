# Preventive Maintenance

## Visao Geral

O modulo de `Manutencao Preventiva` do `Smart System` foi implementado no `admin_shell` como camada operacional de planejamento, recorrencia, agenda e cobertura preventiva.

Rotas principais:

- `/app/smart-system/preventives/`
- `/app/smart-system/preventives/schedule/`
- `/app/smart-system/preventives/calendar/`
- `/app/smart-system/preventives/<codigo>/`

## Estrutura

Arquivos centrais:

- `apps/admin_shell/services/smart_system_preventives.py`
- `apps/admin_shell/templates/admin_shell/smart_system_preventives_list.html`
- `apps/admin_shell/templates/admin_shell/smart_system_preventives_schedule.html`
- `apps/admin_shell/templates/admin_shell/smart_system_preventives_calendar.html`
- `apps/admin_shell/templates/admin_shell/smart_system_preventive_detail.html`

Componentes:

- `preventive_filter_bar.html`
- `preventive_kpi_card.html`
- `preventive_plan_table.html`
- `preventive_status_badge.html`
- `preventive_adherence_badge.html`
- `preventive_schedule_list.html`
- `preventive_calendar_widget.html`
- `preventive_summary_panel.html`
- `preventive_recurrence_panel.html`
- `preventive_timeline.html`
- `preventive_alert_panel.html`
- `preventive_action_panel.html`

## Origem dos mocks

Os dados estao em `smart_system_preventives.py` e cobrem cenarios plausiveis:

- plano saudavel e automatizado
- plano vencido em ativo com falha reincidente
- plano com baixa aderencia
- plano critico prestes a vencer
- plano sem checklist
- agenda operacional da semana
- calendario mensal resumido

## Evolucao para dados reais

Substitua gradualmente por dados do bounded context `smart_system`:

- `MaintenancePlan`
- `Checklist`
- `ChecklistItem`
- `ServiceOrder`
- `ScheduledReminder`
- `CalendarEvent`

O service atual ja separa:

- listagem
- agenda
- calendario
- detalhe do plano

Isso facilita trocar os mocks por query services reais sem alterar a camada de templates.

## Evolucao da recorrencia

Hoje a recorrencia e apresentada de forma estruturada e visual.

Proximos passos naturais:

1. derivar proximas janelas a partir de `MaintenancePlan`
2. suportar regras por tempo, uso e condicao
3. acionar geracao automatica de OS preventiva
4. integrar agenda com `scheduling_center`
5. medir aderencia historica real

## Geração futura de OS preventiva

O detalhe do plano ja modela:

- gatilho de geracao automatica
- janela operacional
- tolerancia
- cobertura do ativo
- status do checklist

Essa estrutura deixa o modulo pronto para evoluir para workflow real de OS preventiva.
