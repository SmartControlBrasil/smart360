# Asset Management

## Visao Geral

O primeiro recorte real de Asset Management do Smart System foi implementado dentro do `admin_shell`, com:

- lista operacional de ativos
- filtros e busca
- KPIs da carteira
- ficha tecnica individual do ativo
- resumo de manutencao e confiabilidade
- historico resumido
- alertas e acoes rapidas

## Estrutura

Arquivos principais:

- `apps/admin_shell/services/smart_system_assets.py`
- `apps/admin_shell/templates/admin_shell/smart_system_assets_list.html`
- `apps/admin_shell/templates/admin_shell/smart_system_asset_detail.html`
- componentes `asset_*` em `apps/admin_shell/templates/admin_shell/components/`

## Mocks

Os mocks foram escritos para parecer operacao real de CMMS/EAM, com ativos de:

- academia
- laboratorio
- planta industrial
- HVAC
- fitness
- utilidades
- automacao

## Como Adicionar Novo Campo ao Ativo

1. adicionar o campo em `ASSET_RECORDS`
2. refletir o uso no contexto de lista ou detalhe
3. atualizar o componente visual correspondente

## Como Substituir por Dados Reais

1. manter a interface publica das funcoes:
   - `get_asset_listing_context`
   - `get_asset_detail_context`
2. trocar os mocks por services reais do bounded context `smart_system`
3. preservar os componentes de apresentacao e badges

## Componentes Criados

- `asset_filter_bar`
- `asset_kpi_card`
- `asset_table`
- `asset_status_badge`
- `asset_condition_badge`
- `asset_criticality_badge`
- `asset_summary_panel`
- `asset_technical_info`
- `asset_risk_panel`
- `asset_maintenance_reliability`
- `asset_history_timeline`
- `asset_alert_panel`
- `asset_action_panel`

## Proximos Passos

- edicao e cadastro real de ativo
- vinculo com OS e FailureEvent reais
- anexos do ativo via `files_center`
- criticidade parametrizavel por site/cliente
- historico completo com filtros e timeline expandida
