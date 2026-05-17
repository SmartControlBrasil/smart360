# Orcamentos Tecnicos e Aprovacao do Cliente

O modulo de orcamentos do Smart System conecta manutencao, estoque, portal do cliente e fluxo comercial do atendimento.

## Entidades principais

- `ServiceQuote`
  - cabecalho comercial/tecnico do orcamento
  - vinculado a `company`, `operational_site`, `work_order` e `asset`
  - estados: `draft`, `sent`, `approved`, `rejected`, `expired`
- `QuoteItem`
  - itens do orcamento
  - tipos: `part`, `labor`, `service`
  - pode vincular item de estoque via `stock_item`

## Fluxo operacional

1. equipe interna cria o orcamento tecnico vinculado a uma `WorkOrder`
2. itens de pecas e mao de obra sao adicionados
3. totais de pecas, servico e valor geral sao recalculados automaticamente
4. o orcamento e enviado ao cliente
5. o cliente aprova ou rejeita no portal
6. se aprovado:
   - pecas vinculadas sao reservadas no estoque
   - a `WorkOrder` recebe `quote_status=approved`
   - a OS pode seguir para execucao
7. se rejeitado:
   - a OS entra em estado de espera operacional

## Integracao com OS

Campos adicionados em `ServiceOrder`:

- `quote_required`
- `quote_status`
- `quote_approved_at`

Estados refletidos:

- enviado: OS vai para `waiting_quote_approval`
- aprovado: OS retorna para fluxo planejado
- rejeitado: OS vai para `on_hold`

## Integracao com estoque

Quando um `QuoteItem` do tipo `part` possui `stock_item` e o orcamento e aprovado:

- o saldo do item e reservado
- e criada uma `StockMovement` com tipo `reserved`

Essa implementacao prepara a futura separacao entre reserva, consumo real e devolucao.

## Superficies entregues

### Shell interno

- `/app/smart-system/quotes/`
- `/app/smart-system/quotes/<quote_number>/`
- envio, aprovacao e rejeicao internos

### Portal do cliente

- `/portal/quotes/`
- `/portal/quotes/<quote_number>/`
- aprovacao e rejeicao digital do orcamento

### API interna

- `GET|POST /api/v1/smart-system/service-quotes/`
- `GET|PATCH /api/v1/smart-system/service-quotes/{id}/`
- `POST /api/v1/smart-system/service-quotes/{id}/send/`
- `POST /api/v1/smart-system/service-quotes/{id}/approve/`
- `POST /api/v1/smart-system/service-quotes/{id}/reject/`

## Auditoria e observabilidade

Eventos emitidos:

- `quote.created`
- `quote.updated`
- `quote.sent`
- `quote.approved`
- `quote.rejected`

Cada evento carrega `company`, `site`, `work_order`, `quote_number` e `total_value`.

## Limitacoes atuais

- ainda nao existe expiracao automatica do orcamento
- reserva de estoque ainda nao diferencia reserva parcial e consumo final
- nao ha assinatura digital dedicada para aprovacao do orcamento nesta rodada
- nao existe workflow de revisao de orcamento com multiplas versoes

## Evolucao recomendada

- versoes de orcamento e trilha comparativa
- assinatura digital do cliente no aceite do orcamento
- reserva, liberacao e consumo final de pecas separados
- envio automatico por notificacao/email/portal
- integracao com billing para cobranca complementar
