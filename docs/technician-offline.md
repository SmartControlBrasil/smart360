# Offline Real do App Tecnico

## Objetivo
O PWA tecnico agora opera em modo offline-first para execucao de campo, com persistencia local, fila de mutations pendentes e sincronizacao posterior com o backend do Smart System.

## Componentes principais
- `IndexedDB` no frontend:
  - `serviceBundles`: bundle local dos atendimentos autorizados
  - `serviceDrafts`: rascunhos por ordem de servico
  - `pendingOps`: fila de acoes pendentes de sync
  - `syncMeta`: ultimo sync, erros e metadados do dispositivo
- `Service Worker`:
  - cache do shell do app
  - cache das telas principais do tecnico
  - fallback offline para navegacao em `/field/`
- Backend:
  - `FieldExecutionSnapshot`
  - `FieldSyncOperation`
  - `FieldOfflineSyncService`
  - endpoints:
    - `/field/api/offline-bundle/`
    - `/field/api/offline-sync/`

## Fluxos offline implementados
- inicio de atendimento offline
- salvamento offline de checklist
- salvamento offline de diagnostico e acao executada
- salvamento offline de materiais
- registro offline de evidencias com data URL e upload posterior
- captura offline de assinatura do tecnico
- captura offline de assinatura do cliente ou justificativa de ausencia
- conclusao offline com sincronizacao posterior
- painel de sincronizacao com pendencias, conflitos e ultimo sync

## Estrategia de sincronizacao
1. o tecnico salva localmente no PWA
2. a mutation entra em `pendingOps`
3. ao voltar a conexao, o app envia o lote para `/field/api/offline-sync/`
4. o backend processa em ordem logica:
   - `start_execution`
   - `save_execution`
   - `save_checklist`
   - `save_materials`
   - `upload_evidence`
   - `capture_signature`
   - `complete_execution`
5. o backend grava `FieldSyncOperation` e consolida `FieldExecutionSnapshot`
6. itens sincronizados saem da fila local

## Politica de conflito v1
- a ordem nao pode ser alterada offline se ja estiver `completed` ou `cancelled` no servidor
- se a ordem nao estiver mais atribuida ao tecnico, a sync falha com conflito
- conflitos nao sobrescrevem dados criticos automaticamente
- itens em conflito ficam locais com status `conflict`

## Politica de consistencia
- backend continua sendo a fonte final de verdade
- frontend salva primeiro e sincroniza depois
- operacoes de rascunho sao substituiveis localmente para evitar fila inflada
- operacoes criticas usam `client_operation_id` para idempotencia

## Seguranca
- apenas dados do escopo atual do tecnico sao baixados
- o armazenamento local fica segmentado por `user + company + site`
- o app nao persiste segredos adicionais
- o sync respeita permissao, tenant e site autorizados

## Observabilidade
Eventos relevantes emitidos:
- `sync.started`
- `sync.succeeded`
- `sync.failed`
- `sync.conflict_detected`
- `offline.payload.queued`
- `checklist.saved_offline`
- `signature.technician.captured`
- `signature.client.captured`

## Limitacoes atuais
- resolucao de conflito ainda e manual/simples
- materiais offline ainda consolidam snapshot antes de baixa MRO completa
- evidencias usam data URL; uploads grandes exigem evolucao posterior
- nao ha background sync avancado nativo do browser nesta versao

## Proximos passos
- sync incremental por entidade
- retry/backoff mais sofisticado
- resolucao assistida de conflitos
- fila dedicada para anexos pesados
- roteirizacao e geolocalizacao offline
- motor de sync compartilhado com app nativo futuro
