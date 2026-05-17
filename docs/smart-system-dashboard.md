# Smart System Dashboard

## Visao Geral

O dashboard do `Smart System` representa a home operacional do contexto de manutencao dentro do admin shell do SMART360.

Objetivos da tela:

- leitura executiva de manutencao
- visao operacional de OS e backlog
- monitoramento de preventivas
- semantica de confiabilidade, TPM, RCM e CMMS

## Estrutura da Tela

Blocos implementados:

- cabecalho contextual do modulo
- barra de filtros rapidos
- KPIs de manutencao
- saude operacional
- alertas e excecoes
- ordens de servico
- backlog de manutencao
- falhas e confiabilidade
- plano preventivo
- atividade recente
- atalhos operacionais
- visao por area / site / cliente

## Origem dos Mocks

Os dados mockados estao centralizados em:

- `apps/admin_shell/services/shell.py`

Funcao principal:

- `get_smart_system_dashboard_context()`

Os nomes, codigos e cenarios foram escritos para parecerem criveis em manutencao industrial, predial e fitness-tech.

## Componentes do Modulo

Componentes dedicados:

- `maintenance_filter_bar.html`
- `maintenance_kpi_card.html`
- `asset_health_widget.html`
- `work_order_list.html`
- `backlog_widget.html`
- `reliability_widget.html`
- `preventive_schedule_widget.html`
- `alert_widget.html`
- `activity_feed.html`
- `action_shortcuts.html`
- `site_status_table.html`

## Como Adicionar Novo Widget

1. adicionar os dados no contexto do modulo
2. criar um componente novo em `apps/admin_shell/templates/admin_shell/components/`
3. incluir o widget no template `smart_system_dashboard.html`
4. complementar estilos em `static/smart360/css/admin-shell.css`

## Como Trocar para Dados Reais

1. manter a interface do contexto usada pelos templates
2. mover agregacoes para services do bounded context `smart_system`
3. alimentar a view com dados reais por cliente, site e periodo
4. manter os componentes visuais como camada de apresentacao

## Navegacao complementar

O dashboard agora se conecta com paginas operacionais reais do modulo:

- Ativos: `/app/smart-system/assets/`
- Ordens de Servico: `/app/smart-system/work-orders/`
- Preventivas: `/app/smart-system/preventives/`
- Falhas: `/app/smart-system/failures/`
- Checklists: `/app/smart-system/checklists/`
- Pecas: `/app/smart-system/parts/`
- Relatorios: `/app/smart-system/reports/`

## Proximos Passos

- integrar filtros a querystring real
- conectar KPIs a `smart_system`, `analytics_platform` e `observability_center`
- adicionar drill-down de OS por ativo e por site
- conectar o dashboard de ativos implantado na rodada seguinte
- ligar acoes rapidas a rotas reais do modulo
- incorporar graficos e series historicas de disponibilidade, MTBF e MTTR
