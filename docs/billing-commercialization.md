# Billing, Contratos e Comercializacao

O modulo de billing do SMART360 passou a cobrir a base comercial da plataforma SaaS, com foco em:

- catalogo de planos
- contratos por empresa
- assinatura ativa vinculada ao contrato
- historico de faturas
- leitura financeira executiva
- bloqueio operacional por status financeiro

## Modelo adotado

Relacoes principais:

- `Company` -> tenant operacional da plataforma
- `BillingCustomer` -> identidade financeira da empresa
- `BillingPlan` -> catalogo comercial
- `Contract` -> compromisso comercial vigente entre empresa e plano
- `Subscription` -> estado operacional da assinatura
- `Invoice` -> cobranca emitida para a empresa

Fluxo base:

1. a empresa entra com um `BillingCustomer`
2. um `Contract` vincula empresa + plano + periodicidade
3. uma `Subscription` reflete o estado recorrente da assinatura
4. `Invoice` registra a cobranca do periodo
5. `BillingAccessService` decide se o tenant segue liberado, em aviso ou bloqueado

## Superficie administrativa no shell

Rotas principais:

- `/app/platform-admin/billing/`
- `/app/platform-admin/billing/plans/`
- `/app/platform-admin/billing/contracts/`
- `/app/platform-admin/billing/contracts/<contract_code>/`
- `/app/platform-admin/billing/invoices/`

O shell exibe:

- dashboard financeiro com MRR, inadimplencia e carteira ativa
- lista de planos
- lista de contratos
- detalhe do contrato com assinatura e historico de faturas
- lista de faturas com operacoes administrativas

## Permissoes

Foi criado o dominio `billing_admin` no `access_control_center`.

Acoes iniciais:

- `billing_admin.view`
- `billing_admin.manage`
- `billing_admin.export`

Perfis iniciais:

- `super-admin`: acesso total ao billing
- `finance-readonly`: leitura e exportacao
- demais perfis operacionais do Smart System: sem acesso por padrao

## Bloqueio por assinatura

`BillingAccessService` centraliza a decisao de acesso por tenant:

- `active`: acesso normal
- `trial`: acesso normal
- `overdue`: acesso com aviso
- `suspended`, `cancelled`, `expired`: acesso bloqueado

No `admin_shell`, o bloqueio e aplicado aos modulos operacionais via `SmartSystemAccessMixin`. As telas administrativas de billing nao sofrem esse bloqueio para permitir regularizacao financeira pelo operador autorizado.

## Seeds

O bootstrap comercial agora cria:

- planos `Starter`, `Professional`, `Enterprise`
- cliente financeiro para empresa demo
- contrato ativo
- assinatura ativa
- invoice aberta
- wallet e lancamentos iniciais

O comando permanece idempotente dentro do bootstrap do projeto.

## Como evoluir

Para adicionar novo tipo de plano:

1. criar ou atualizar `BillingPlan`
2. ajustar `enabled_features` e limites
3. refletir o novo posicionamento comercial no shell se necessario

Para adicionar gateway:

1. criar adaptador de provider em `apps/billing/services`
2. persistir `external_reference` em assinatura/fatura/pagamento
3. acoplar webhooks ao `integration_bus`
4. refletir conciliacao e falhas via `observability_center`

## Proximos passos recomendados

- portal do cliente para autoatendimento
- upgrade/downgrade de plano
- trial automatizado
- cobranca recorrente por gateway
- notas fiscais e conciliacao
- branding e documentos financeiros por tenant
