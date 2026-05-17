# AI VoiceOps

O VoiceOps adiciona interacao operacional por voz para tecnico, gestor e cliente.

## Pipeline

`audio/texto -> transcricao -> intent parsing -> resolucao de contexto -> acao/resposta -> auditoria`

## Personas

- `technician`
- `manager`
- `client`

## Intents iniciais

- `start_work_order`
- `complete_work_order`
- `report_issue`
- `add_part`
- `mark_checklist_nok`
- `request_help`
- `query_status`
- `query_summary`
- `query_schedule`
- `query_risk`

## Integracoes

- tecnico: `TechnicianCopilotService` e `FieldOfflineSyncService`
- gestor: `ManagerCopilotService`
- cliente: `ClientPortalCopilotService`
- contexto: `DigitalTwinOrchestrator` e `GraphInsightService`

## Observabilidade

Eventos emitidos:

- `voice.input.received`
- `voice.transcribed`
- `voice.intent.detected`
- `voice.action.executed`
- `voice.response.generated`

## Limitacoes atuais

- STT usa transcricao do navegador/fallback, sem provider externo servidor-side
- TTS usa `speechSynthesis` do browser
- acoes por voz estao focadas nas rotinas seguras do tecnico

