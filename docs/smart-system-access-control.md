# Smart System Access Control

## Visao Geral

O hardening operacional do `Smart System` usa o `access_control_center` como fonte unica de autorizacao. A camada foi aplicada em duas frentes:

- backend: views e acoes sensiveis verificam permissao real antes de executar
- frontend: sidebar, atalhos, page actions e paineis escondem o que o perfil nao pode usar

O principio adotado e `deny by default`.

## Modelagem Reutilizada

O modulo reaproveita as entidades existentes:

- `PermissionDomain`
- `PermissionAction`
- `Role`
- `RolePermission`
- `UserRoleAssignment`
- `AccessAuditLog`

Nenhum schema novo foi necessario nesta rodada. O foco foi preencher a matriz operacional do Smart System e aplicá-la no shell.

## Dominios do Smart System

- `dashboard`
- `assets`
- `work_orders`
- `preventive_plans`
- `failures`
- `checklists`
- `work_execution`
- `inventory`
- `reports`
- `users`
- `smart_system_settings`

## Acoes Principais

- `view`
- `create`
- `update`
- `delete`
- `assign`
- `execute`
- `close`
- `manage`
- `rca`
- `adjust_stock`
- `consume`
- `generate_report`
- `export`
- `log_hours`
- `log_materials`
- `log_evidence`

## Perfis Iniciais

- `super-admin`
- `company-admin`
- `maintenance-manager`
- `planner`
- `technician`
- `inventory-clerk`
- `auditor-readonly`
- `finance-readonly`

## Matriz Inicial Resumida

### Super Admin

- acesso total a todos os dominios e acoes do Smart System

### Admin da Empresa

- acesso total dentro do escopo operacional do Smart System

### Gestor de Manutencao

- gerencia ativos, OS, preventivas, falhas, checklists e relatorios
- pode concluir OS
- pode executar fluxo tecnico
- visualiza estoque e consumo, mas nao ajusta saldo manual

### Planejador

- cria e edita OS e preventivas
- atribui OS
- ve ativos, falhas, checklists, estoque e relatorios
- nao fecha OS
- nao ajusta estoque

### Tecnico

- ve ativos, OS e preventivas
- executa OS
- executa checklist
- registra horas, materiais e evidencias
- registra/atualiza falhas
- nao ajusta estoque manual
- nao exporta PDF
- nao gerencia usuarios

### Almoxarife / Estoque

- gerencia pecas, entradas, saidas e ajustes
- ve OS e ativos relacionados ao consumo
- exporta visoes de estoque
- nao fecha OS

### Auditor / Leitura

- leitura operacional
- sem edicao
- sem exportacao sensivel

### Financeiro / Leitura Operacional

- leitura resumida de dashboard, OS e relatorios
- sem alteracoes operacionais

## Seed Inicial

Comando idempotente:

```bash
python manage.py seed_smart_system_access
```

O bootstrap geral do ambiente agora tambem executa essa matriz.

## Como Proteger Novas Telas

Para novas views do shell:

1. herdar de `ShellContextMixin` ou `SmartSystemAccessMixin`
2. declarar `permission_domain`
3. declarar `permission_action`
4. marcar botoes/menus com `permission_domain` e `permission_action`

Exemplo:

```python
class MyView(ShellContextMixin, TemplateView):
    permission_domain = "assets"
    permission_action = "view"
```

Exemplo de action:

```python
{
    "label": "Exportar",
    "href": "#exportar",
    "permission_domain": "reports",
    "permission_action": "export",
}
```

## Trilha Minima de Acoes Sensiveis

As seguintes acoes passaram a registrar rastreabilidade minima:

- exportacao de relatorio
- inicio de execucao de OS
- salvamento de progresso da execucao
- conclusao tecnica da OS
- decisoes de autorizacao com `log_decision`

Campos relevantes:

- usuario
- dominio
- acao
- entidade afetada
- id da entidade
- timestamp

## Limites Atuais

- o escopo por empresa/site ainda esta preparado, mas nao aprofundado no shell mockado
- politicas ABAC e aprovacao em dois niveis continuam para a proxima fase
- o backend real do `smart_system` ainda precisa aplicar a mesma politica nas APIs de dominio

## Proximos Passos

- escopo por empresa, cliente e unidade
- politicas por atribuicao de OS
- aprovacao de encerramento tecnico
- assinatura tecnica e auditoria ampliada
- sincronizacao da matriz com APIs do bounded context real
