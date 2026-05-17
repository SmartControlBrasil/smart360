# Smart System Tenancy

## Visao geral

O Smart System agora opera com escopo logico em dois niveis:

- `company`: tenant operacional / cliente
- `site`: unidade operacional dentro da empresa

Permissao e escopo trabalham juntos:

- o backend valida permissao por perfil
- o backend restringe querysets ao tenant e ao site permitidos
- o frontend apenas reflete o que o backend autorizou

## Modelo adotado

Entidades principais:

- `Company`
- `Membership`
- `SiteMembership`
- `MaintenanceClient`
- `OperationalSite`

Regra de escopo:

- toda consulta relevante do Smart System respeita empresa
- quando o usuario possui `SiteMembership`, a consulta tambem respeita site
- se houver contexto ativo selecionado, a consulta e refinada para empresa/site ativos
- acesso fora do escopo retorna negacao segura

## Contexto ativo

O contexto ativo fica na sessao:

- `smart_system_active_company_id`
- `smart_system_active_site_id`

O seletor do topo do `admin_shell` permite:

- trocar a empresa ativa
- trocar o site ativo
- operar em “todos os sites permitidos” dentro da empresa ativa

## Entidades escopadas nesta rodada

- ativos
- ordens de servico
- planos preventivos
- agenda e calendario preventivo
- falhas / RCA
- checklists e execucoes
- pecas / estoque / movimentacoes
- relatorios do Smart System
- dashboard e agregacoes do shell

## Como aplicar escopo em novas entidades

1. adicionar referencia coerente a `company` e/ou `site`
2. registrar o modelo em `SmartSystemScopeService.COMPANY_FIELD_MAP`
3. registrar o modelo em `SmartSystemScopeService.SITE_FIELD_MAP` quando aplicavel
4. usar `SmartSystemScopeService.scope_queryset(...)` nas views/API
5. usar `scope_related_queryset(...)` para FKs em serializers/forms
6. refletir o contexto ativo no frontend apenas como UX, nunca como fonte unica da regra

## Relacao entre permissao e escopo

Exemplo:

- um tecnico com `work_orders.execute` ainda nao pode executar OS de outra empresa
- um gestor com `reports.export` ainda nao pode exportar relatorio de outro tenant
- um almoxarife com `inventory.adjust_stock` ainda nao pode ajustar estoque de site fora do seu escopo

## Seeds iniciais

O bootstrap passa a criar:

- empresas:
  - Smart Control Brasil
  - Panobianco
  - Academia Exemplo
- sites:
  - Unidade Centro
  - Unidade Norte
  - Panobianco Cumbica
  - Panobianco Centro
  - Demo Plant A
  - Demo Plant B

Tambem sao criadas memberships por empresa e por site para usuarios demo.

## Limites atuais

- o scoping forte foi aplicado nas camadas principais do Smart System e no `admin_shell`
- a UI ainda nao tem tela dedicada para administrar memberships por site fora do Django admin
- branding por tenant em PDF ainda e preparacao estrutural

## Proximos passos

- aplicar o mesmo padrao aos demais bounded contexts do ecossistema
- adicionar escopo por site diretamente ao RBAC
- restringir tecnico por OS atribuida alem de tenant/site
- evoluir para feature flags e workflows por tenant
- preparar branding e billing por empresa/site
