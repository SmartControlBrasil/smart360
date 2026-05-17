# Admin Shell

## Visao Geral

O `admin_shell` fornece a base visual administrativa do SMART360. Ele nao substitui o Django Admin nem o `backoffice`; funciona como shell enterprise para dashboards, navegacao modular e futuras telas operacionais do ecossistema.

## Estrutura

- `apps/admin_shell/views.py`: views do dashboard e paginas base
- `apps/admin_shell/services/shell.py`: navegacao, mocks realistas e definicao dos modulos
- `apps/admin_shell/templates/admin_shell/`: layout, paginas e componentes reutilizaveis
- `static/smart360/css/admin-shell.css`: tema e design tokens
- `static/smart360/js/admin-shell.js`: interacoes base do shell

## Como Adicionar Item na Sidebar

Editar `apps/admin_shell/services/shell.py`:

1. adicionar ou ajustar um item em `MODULE_PAGES`
2. incluir a entrada na secao correta de `get_navigation`
3. apontar o `slug` para a rota `admin-shell:module-page`

## Como Criar Nova Pagina

1. adicione o `slug` em `MODULE_PAGES`
2. se a tela for placeholder, a `ModulePageView` ja cobre o caso
3. se a tela precisar de layout proprio, crie um template novo estendendo `admin_shell/base.html`

## Componentes Reutilizaveis

- sidebar
- topbar
- page header
- breadcrumb
- stat card
- info card
- widget container
- recent activity list
- quick action button
- module shortcut card
- status badge

## Tema

O CSS usa tokens simples em `:root`:

- cores base
- radii
- espacos
- tons auxiliares por contexto

## Proximos Passos

- ligar a busca global ao `global_search`
- conectar notificacoes reais ao `notification_center`
- substituir mocks por queries agregadas reais
- criar dashboards especificos por bounded context

## Smart System Dashboard

O `Smart System` agora possui um dashboard proprio dentro do shell, com foco em:

- ativos monitorados
- ordens de servico
- backlog
- confiabilidade
- plano preventivo
- alertas
- atividade recente
- visao por site

Mocks tecnicos ficam centralizados em `apps/admin_shell/services/shell.py`, na funcao `get_smart_system_dashboard_context()`.

### Como adicionar um widget novo no Smart System

1. adicionar os dados na funcao `get_smart_system_dashboard_context()`
2. criar um componente em `apps/admin_shell/templates/admin_shell/components/`
3. incluir o widget em `smart_system_dashboard.html`
4. complementar estilos em `static/smart360/css/admin-shell.css`

### Como substituir mocks por dados reais

1. manter a estrutura das chaves do contexto
2. trocar a origem em `get_smart_system_dashboard_context()` por services reais do modulo `smart_system`
3. preservar os componentes visuais e a semantica operacional
