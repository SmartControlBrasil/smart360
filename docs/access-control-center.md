# Access Control Center

## Visao do modulo

O `access_control_center` centraliza governanca de acesso do ecossistema SMART360 com base em RBAC extensivel, escopos granulares, policies complementares e trilha de auditoria. O modulo foi desenhado para coexistir com o `apps.roles` legado do core sem substitui-lo diretamente.

## Arquitetura de RBAC

O modelo principal segue:

- `Role`
- `PermissionDomain`
- `PermissionAction`
- `RolePermission`
- `UserRoleAssignment`

O acesso efetivo e calculado por:

1. roles ativas do usuario
2. escopo da atribuicao
3. permissoes `role -> domain -> action`
4. policies adicionais
5. log de auditoria da decisao

## Dominios e acoes

Exemplos de dominios esperados:

- `smart_system`
- `billing`
- `marketplace_technicians`
- `backoffice`
- `configuration_center`

Acoes suportadas:

- `create`
- `view`
- `update`
- `delete`
- `approve`
- `assign`
- `export`
- `configure`
- `execute`

## Roles

O modulo suporta multiplos papeis por usuario e multiplas atribuicoes por escopo:

- `global`
- `company`
- `module`
- `resource`

Isso permite cenarios como:

- gerente financeiro por empresa
- operador apenas do modulo billing
- tecnico com acesso somente a um recurso especifico

## Policies

`AccessPolicy` complementa o RBAC com regras JSON simples. Nesta rodada, o avaliador suporta operadores como:

- `eq`
- `ne`
- `in`
- `contains`
- `truthy`
- `falsy`
- `equals_user_id`
- `equals_company_id`

## Escopos

`UserRoleAssignment` suporta:

- `global`
- `company`
- `module`
- `resource`

`scope_reference` pode armazenar nome do modulo ou referencia logica de recurso, como `service_order:123`.

## Auditoria

`AccessAuditLog` registra decisoes `allow` e `deny` com:

- usuario
- dominio
- acao
- recurso
- motivo
- metadados

## Acoes sensiveis

`SensitiveActionApproval` prepara fluxos como:

- cancelar invoice
- remover tecnico aprovado
- alterar configuracoes globais
- executar acoes administrativas criticas

## Endpoints

- `GET|POST /api/v1/access-control/permission-domains/`
- `GET|POST /api/v1/access-control/permission-actions/`
- `GET|POST /api/v1/access-control/roles/`
- `GET|POST /api/v1/access-control/role-permissions/`
- `GET|POST /api/v1/access-control/user-role-assignments/`
- `GET|POST /api/v1/access-control/access-policies/`
- `GET|POST /api/v1/access-control/policy-assignments/`
- `GET /api/v1/access-control/audit-logs/`
- `GET|POST /api/v1/access-control/sensitive-approvals/`
- `POST /api/v1/access-control/sensitive-approvals/{id}/approve/`
- `POST /api/v1/access-control/sensitive-approvals/{id}/reject/`
- `POST /api/v1/access-control/check-permission/`
- `GET /api/v1/access-control/my-roles/`
- `GET /api/v1/access-control/my-permissions/`
- `POST /api/v1/access-control/policy-evaluation/`

## Integracoes

O modulo se integra com:

- `core_platform`: `User` e `Company`
- `billing`: aprovacoes e governanca financeira
- `smart_system`: regras de escopo por OS e ativos
- `marketplace_technicians`: acessos operacionais de tecnicos e equipe
- `backoffice`: quick approvals e trilha administrativa
- `reporting_center`: controle de exportacoes e visibilidade
- `configuration_center`: controle de alteracoes globais
- `ai_automation_center`: governanca de execucao e aprovacoes futuras

## Proximos passos

- criar permissions shared por bounded context e seed inicial
- integrar enforcement em endpoints sensiveis dos demais modulos
- adicionar cache de resolucao de permissoes
- evoluir policy engine para cenarios ABAC mais ricos
- integrar com `access_control_center` no bootstrap de demo data
