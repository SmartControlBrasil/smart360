# Billing

## Visao do modulo

O `billing` e o bounded context transversal de monetizacao do ecossistema SMART360. Ele suporta assinaturas, cobrancas avulsas, addons, pagamentos, carteiras de credito, ledger financeiro e preparacao para comissionamento.

## Entidades

- `BillingCustomer`: cliente financeiro ligado a `User` e/ou `Company`
- `BillingPlan`: plano recorrente
- `BillingAddon`: complemento comercial
- `Subscription`: assinatura do cliente
- `SubscriptionAddon`: addons vinculados a uma assinatura
- `Invoice`: fatura ou cobranca
- `InvoiceItem`: itens da fatura com referencias livres para outros modulos
- `PaymentRecord`: registro de pagamento preparado para gateway
- `CreditWallet`: carteira de creditos
- `CreditTransaction`: movimentacao de creditos
- `BillingLedgerEntry`: trilha financeira minima
- `CommissionStatement`: preparacao para repasses e comissoes

## Fluxo de assinatura

1. criar `BillingCustomer`
2. cadastrar `BillingPlan`
3. abrir `Subscription`
4. opcionalmente vincular `SubscriptionAddon`
5. gerar `Invoice` recorrente ou avulsa

## Fluxo de cobranca

1. criar `Invoice`
2. adicionar `InvoiceItem`
3. registrar `PaymentRecord`
4. quando o pagamento for marcado como pago:
   - a invoice muda para `paid`
   - o ledger recebe um registro de pagamento

## Fluxo de creditos

1. criar `CreditWallet`
2. registrar `CreditTransaction`
3. o saldo e atualizado automaticamente
4. o ledger recebe entrada correspondente

## Fluxo de comissao

`CommissionStatement` prepara o terreno para:

- repasse marketplace
- comissao por indicacao
- fee de plataforma
- producao interna

## Integracao com modulos do ecossistema

O modulo foi preparado para atender:

- `smart_site_factory`
- `caneca_de_garagem`
- `marketplace_technicians`
- `marketplace_analytical`
- `smart_system`
- `growth_engine`

As referencias em `InvoiceItem`, `CreditTransaction` e `BillingLedgerEntry` usam `reference_type` e `reference_id` para manter desacoplamento dos demais bounded contexts.

## Endpoints criados

- `GET|POST /api/v1/billing/customers/`
- `GET|POST /api/v1/billing/plans/`
- `GET|POST /api/v1/billing/addons/`
- `GET|POST /api/v1/billing/subscriptions/`
- `POST /api/v1/billing/subscriptions/{id}/cancel/`
- `GET|POST /api/v1/billing/subscription-addons/`
- `GET|POST /api/v1/billing/invoices/`
- `GET|POST /api/v1/billing/invoice-items/`
- `GET|POST /api/v1/billing/payment-records/`
- `POST /api/v1/billing/payment-records/{id}/mark_paid/`
- `GET|POST /api/v1/billing/wallets/`
- `GET|POST /api/v1/billing/credit-transactions/`
- `GET|POST /api/v1/billing/ledger-entries/`
- `GET|POST /api/v1/billing/commission-statements/`

## Proximos passos

- integrar com gateway real de pagamento
- gerar cobrancas recorrentes via Celery
- adicionar reconciliation e refund flows
- emitir eventos para `integration_bus` e `analytics_platform`
- evoluir com regras de imposto, split e comissionamento automatico
