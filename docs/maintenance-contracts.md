# Contratos de Manutencao Recorrente

## Visao geral

O modulo de contratos recorrentes do `smart_system` cobre:

- contrato de manutencao por empresa/cliente/unidade
- ativos cobertos por contrato
- recorrencia preventiva por ativo
- geracao automatica de OS preventivas
- integracao com agenda operacional
- geracao de cobranca recorrente via `billing`

## Entidades

### MaintenanceContract

- tenant operacional principal do contrato
- cliente e unidade atendida
- periodicidade de cobranca
- valor do contrato
- status do contrato
- proxima cobranca e ultima cobranca

### ContractAsset

- ativo coberto
- frequencia de manutencao
- proxima execucao
- ultima execucao
- duracao estimada

## Fluxo operacional

1. contrato e criado no Smart System
2. ativos sao vinculados ao contrato
3. contrato e ativado
4. o servico gera preventivas quando o ativo estiver vencido
5. a agenda operacional absorve a OS preventiva gerada
6. o ciclo financeiro gera fatura recorrente do contrato

## Integracao com preventivas

- cada `ContractAsset` pode gerar um `MaintenancePlan` vinculado
- quando chega a data de `next_execution`, o sistema gera `ServiceOrder` preventiva
- o `MaintenancePlan.next_due_date` e o `ContractAsset.next_execution` avancam para o proximo ciclo

## Integracao com faturamento

- a cobranca recorrente usa `Invoice` e `InvoiceItem` do modulo `billing`
- a fatura recebe metadados com `maintenance_contract_number`
- isso permite listar historico financeiro do contrato sem criar um billing paralelo

## Shell e portal

Shell interno:

- `/app/smart-system/contracts/`
- `/app/smart-system/contracts/<contract_number>/`

Portal do cliente:

- `/portal/contracts/`
- `/portal/contracts/<contract_number>/`

## API interna

- `GET|POST /api/v1/smart-system/maintenance-contracts/`
- `GET|PATCH /api/v1/smart-system/maintenance-contracts/{id}/`
- `POST /api/v1/smart-system/maintenance-contracts/{id}/activate/`
- `POST /api/v1/smart-system/maintenance-contracts/{id}/suspend/`
- `POST /api/v1/smart-system/maintenance-contracts/{id}/expire/`
- `POST /api/v1/smart-system/maintenance-contracts/{id}/generate-preventives/`
- `POST /api/v1/smart-system/maintenance-contracts/{id}/generate-billing/`
- `GET|POST /api/v1/smart-system/contract-assets/`

## Eventos relevantes

- `contract.created`
- `contract.activated`
- `contract.suspended`
- `contract.expired`
- `contract.preventives_generated`
- `contract.billing_generated`

## Limitacoes atuais

- a geracao automatica ainda depende de chamada explicita nesta rodada
- nao existe revisao/versionamento contratual
- a cobranca recorrente ainda nao cria assinatura de billing separada por contrato de manutencao

## Proximos passos recomendados

- job automatico diario para preventivas e faturamento
- renovacao e reajuste contratual
- SLA por contrato
- anexos e documentos contratuais
- portal financeiro do cliente com cobrancas do contrato
