# Assinatura Digital Operacional de Servico

## Visao geral

O SMART360 agora suporta assinatura digital operacional para fechamento de atendimento tecnico.

Escopos cobertos nesta rodada:

- assinatura do tecnico executor
- aceite do cliente ou representante
- justificativa formal de ausencia de assinatura do cliente
- vinculacao com ordem de servico
- exibicao no modo tecnico, shell e relatorios
- trilha auditavel com request id, tenant e site

Nao se trata ainda de assinatura eletronica qualificada ICP-Brasil. O objetivo atual e gerar evidencia operacional consistente, rastreavel e pronta para evolucao juridica futura.

## Modelo principal

Entidade: `apps.smart_system.models.ServiceSignature`

Campos principais:

- `signature_type`
- `signer_role`
- `signer_name`
- `signer_title`
- `signer_document`
- `signer_user`
- `company`
- `operational_site`
- `service_order`
- `signed_at`
- `signature_data`
- `acceptance_notes`
- `missing_reason`
- `missing_reason_notes`
- `signed_ip`
- `device_info`
- `request_id`
- `correlation_id`
- `version`
- `is_current`
- `metadata`

## Tipos suportados

- `technician_completion`
- `client_acceptance`
- `supervisor_validation`
- `report_acknowledgement`

Os dois primeiros estao operacionais nesta rodada. Os demais ficaram preparados para expansao futura.

## Fluxo atual

### 1. Tecnico assina no fechamento

No PWA e no modo tecnico do shell:

1. tecnico entra na execucao da OS
2. preenche checklist, diagnostico, materiais e evidencias
3. registra a assinatura do tecnico em canvas touch
4. a assinatura fica vinculada a `ServiceOrder`

### 2. Cliente assina ou tem ausencia justificada

No mesmo fluxo:

1. o dispositivo pode ser entregue ao cliente/representante
2. o cliente assina em canvas touch
3. se nao houver assinatura, o tecnico registra motivo
4. o atendimento so pode ser concluido quando houver:
   - assinatura do tecnico
   - assinatura do cliente **ou** justificativa formal da ausencia

## Regras de negocio

- a assinatura do tecnico e obrigatoria para conclusao formal
- o cliente pode:
  - assinar
  - ter ausencia justificada
- nova assinatura do mesmo tipo nao sobrescreve silenciosamente a anterior
  - a anterior e marcada como `is_current=False`
  - a nova recebe incremento de `version`

## UX / telas impactadas

### PWA tecnico

Rotas:

- `/field/services/<order_code>/execute/`
- `/field/services/<order_code>/sign-technician/`
- `/field/services/<order_code>/sign-client/`

### Shell operacional

Rotas:

- `/app/smart-system/work-orders/<order_code>/execute/`
- `/app/smart-system/work-orders/<order_code>/capture-technician-signature/`
- `/app/smart-system/work-orders/<order_code>/capture-client-signature/`

### Relatorios

Os relatorios tecnicos passam a incluir bloco documental com:

- nome do tecnico assinante
- data/hora da assinatura
- nome do cliente assinante, quando houver
- justificativa de ausencia, quando aplicavel

## Integracao com observabilidade e auditoria

Eventos registrados:

- `signature.technician.captured`
- `signature.client.captured`
- `signature.client.missing_reason_recorded`

Auditoria funcional:

- dominio `service_signatures`
- tipo do recurso: `service_order`
- vinculo com empresa/site e `request_id`

## Permissoes

Novo dominio RBAC:

- `service_signatures.view`
- `service_signatures.capture`
- `service_signatures.export`

Perfis principais:

- `maintenance-manager`: view, capture, export
- `technician`: view, capture
- `planner`, `inventory-clerk`, `auditor-readonly`, `finance-readonly`: view

## API interna

Endpoint adicional do `smart_system`:

- `/api/v1/smart-system/service-signatures/`

Objetivo:

- consulta interna de assinaturas por OS, tipo e escopo

## Limitacoes atuais

- a assinatura e armazenada como `data_url` em `TextField`
- nao ha hashing documental nem selo criptografico nesta rodada
- o PDF inclui bloco documental com a assinatura registrada e o contexto, mas ainda nao faz cadeia de validacao juridica robusta
- aceite remoto via portal do cliente ficou preparado, mas nao capturado diretamente no portal nesta rodada

## Evolucao recomendada

- assinatura remota no portal do cliente
- OTP / dupla confirmacao
- hash da assinatura e do documento fechado
- QR code de verificacao
- selagem documental
- assinatura de supervisor
- assinatura de orcamento e contrato
- politica de retencao e storage dedicado de evidencias
