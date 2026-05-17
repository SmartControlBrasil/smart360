# Portal do Cliente

## Visao Geral

O portal do cliente entrega uma experiencia separada do admin interno, focada em:

- transparencia operacional
- consulta de ativos, OS, preventivas e relatorios
- abertura e acompanhamento de solicitacoes
- leitura por empresa e unidade
- baixo atrito para usuarios de negocio do cliente

As rotas foram publicadas dentro do `admin_shell`, mas com shell, navegacao, permissao e templates proprios:

- `/portal/`
- `/portal/assets/`
- `/portal/work-orders/`
- `/portal/preventives/`
- `/portal/reports/`
- `/portal/requests/`
- `/portal/sites/`
- `/portal/profile/`

## Arquitetura

### Camadas principais

- `apps/admin_shell/security.py`
  - `ClientPortalAccessMixin`
  - `ClientPortalShellAccessMixin`
- `apps/admin_shell/services/client_portal.py`
  - navegacao do portal
  - montagem de contexto
  - consultas escopadas
  - criacao de solicitacao
  - integracao com relatorios
- `apps/admin_shell/forms.py`
  - `ClientPortalRequestForm`
- `apps/admin_shell/templates/client_portal/*`
  - shell e paginas do portal
- `apps/smart_system/models.py`
  - `ClientPortalRequest`

### Modelo de acesso

O portal reutiliza o RBAC e o tenant scoping ja existentes.

Permissoes do portal:

- `client_portal_dashboard.view`
- `client_portal_assets.view`
- `client_portal_work_orders.view`
- `client_portal_preventives.view`
- `client_portal_reports.view`
- `client_portal_reports.export`
- `client_portal_requests.view`
- `client_portal_requests.create`
- `client_portal_sites.view`
- `client_portal_profile.view`

Perfis iniciais:

- `client-admin`
- `client-manager`
- `client-readonly`
- `requester`

## Escopo

O portal respeita o mesmo contexto ativo de empresa e site usado pelo Smart System:

- empresa ativa
- site ativo ou todos os sites permitidos

O backend faz o isolamento real com `SmartSystemScopeService`. O frontend apenas reflete esse contexto.

## Fluxo de solicitacao

`ClientPortalRequest` e a base inicial de chamados do cliente.

Campos principais:

- protocolo
- empresa
- unidade
- ativo opcional
- categoria
- prioridade
- descricao
- contato
- data desejada
- OS relacionada opcional
- referencia futura ao marketplace opcional

O fluxo atual:

1. cliente abre a solicitacao
2. portal gera protocolo
3. equipe interna acompanha e pode vincular a OS
4. cliente acompanha o andamento no detalhe da solicitacao

## Politica de exposicao

O portal nao mostra:

- notas internas sensiveis
- trilhas de auditoria internas
- configuracoes administrativas
- campos tecnicos irrelevantes para o cliente
- detalhes internos de permissao

O detalhe do ativo, da OS e da preventiva foi reduzido para consulta executiva e operacional do cliente.

## Integracoes

### Smart System

- ativos
- ordens de servico
- planos preventivos
- relatorios
- solicitacoes do portal

### Billing

O portal usa o contexto de billing para:

- exibir status de assinatura no perfil
- respeitar bloqueio de acesso por tenant quando aplicavel

### Observabilidade

Acoes relevantes ja registradas:

- criacao de solicitacao
- exportacao de relatorio no portal
- tentativas fora de escopo

## Como evoluir

### Novas entidades no portal

1. criar query/context builder em `services/client_portal.py`
2. aplicar `SmartSystemScopeService`
3. expor em view protegida por dominio `client_portal_*`
4. renderizar em template proprio do portal

### Novas permissoes

1. adicionar dominio/acao em `apps/access_control_center/services/smart_system_access.py`
2. seedar com `bootstrap_smart_system_access()`
3. usar o dominio na view e nos botoes

### Fluxos futuros recomendados

- chat com suporte e tecnico
- aprovacao de visita/orcamento
- notificacoes em tempo real
- assinatura do cliente
- area financeira do cliente
- agenda de visitas
- white-label por tenant premium
- abertura de solicitacao integrada ao marketplace de tecnicos
