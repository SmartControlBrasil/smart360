# Failure Events / RCA / Confiabilidade

## Visao Geral

O modulo de `Eventos de Falha` do `Smart System` foi implementado no `admin_shell` como a primeira camada de engenharia de manutenção orientada a confiabilidade.

Rotas principais:

- `/app/smart-system/failures/`
- `/app/smart-system/failures/<codigo>/`

## Estrutura

Arquivos centrais:

- `apps/admin_shell/services/smart_system_failures.py`
- `apps/admin_shell/templates/admin_shell/smart_system_failures_list.html`
- `apps/admin_shell/templates/admin_shell/smart_system_failure_detail.html`

Componentes:

- `failure_filter_bar.html`
- `failure_kpi_card.html`
- `failure_table.html`
- `failure_severity_badge.html`
- `failure_summary_panel.html`
- `failure_rca_panel.html`
- `failure_timeline.html`
- `failure_alert_panel.html`

## Modelo atual

Cada evento foi estruturado com:

- vinculo ao ativo
- vinculo opcional a OS
- severidade
- impacto operacional
- diagnostico
- causa raiz
- acao corretiva
- tempo de parada
- recorrencia
- historico tecnico do ativo

Isso deixa a funcionalidade pronta para evoluir para confiabilidade e RCA estruturado.

## Evolucao futura

Base preparada para:

- 5 Whys
- Ishikawa
- FMEA
- MTBF automatico
- deteccao de reincidencia
- recomendacao de preventiva
- IA de diagnostico e RCA assistida

## Como migrar para dados reais

Trocar os mocks do service por agregacoes do bounded context `smart_system`:

- `FailureEvent`
- `Asset`
- `ServiceOrder`
- `AssetHistoryEvent`
- `WorkLog`
- `ServiceDocument`

Manter a interface dos templates e substituir apenas a camada de dados.
