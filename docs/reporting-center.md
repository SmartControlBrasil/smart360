# Reporting Center

## Visao do modulo

O `reporting_center` centraliza templates, requisicoes, execucoes, artefatos e historico de relatorios e exportacoes do ecossistema SMART360.

## Entidades

- `ReportTemplate`: definicao logica do relatorio
- `ReportRequest`: solicitacao de geracao
- `ReportArtifact`: artefato gerado
- `ExportProfile`: perfil reutilizavel de exportacao
- `ExportExecution`: execucao concreta
- `ReportLog`: log operacional
- `ScheduledReport`: relatorios agendados

## Fluxo de geracao de relatorio

1. criar `ReportRequest`
2. executar `run-report`
3. o request entra em `running`
4. um `ReportArtifact` JSON e gerado nesta rodada
5. o request vai para `completed`
6. `ReportLog` registra a execucao

## Fluxo de exportacao

1. criar `ExportProfile`
2. criar ou disparar `ExportExecution`
3. executar `run-export`
4. registrar logs e status

## Historico

- `GET /api/v1/reporting/report-history/`
- `GET /api/v1/reporting/export-history/`

## Agendamentos

`ScheduledReport` prepara o terreno para relatorios diarios, semanais, mensais e customizados, sem depender de Celery nesta rodada.

## Formatos suportados

- `csv`
- `xlsx`
- `json`
- `pdf_future`

## Integracao com os modulos do ecossistema

O modulo foi preparado para gerar relatorios para:

- `smart_system`
- `marketplace_technicians`
- `marketplace_analytical`
- `caneca_de_garagem`
- `smart_site_factory`
- `growth_engine`
- `billing`
- `analytics_platform`
- `backoffice`
- `files_center`

Sem acoplamento profundo nesta rodada. A evolucao natural e usar `integration_bus` para disparos e `files_center` para armazenamento mais sofisticado.

## Endpoints criados

- `GET|POST /api/v1/reporting/templates/`
- `GET|POST /api/v1/reporting/requests/`
- `POST /api/v1/reporting/requests/{id}/run/`
- `GET|POST /api/v1/reporting/artifacts/`
- `GET|POST /api/v1/reporting/export-profiles/`
- `GET|POST /api/v1/reporting/export-executions/`
- `POST /api/v1/reporting/export-executions/{id}/run/`
- `GET|POST /api/v1/reporting/logs/`
- `GET|POST /api/v1/reporting/scheduled-reports/`
- `POST /api/v1/reporting/run-report/`
- `POST /api/v1/reporting/run-export/`
- `GET /api/v1/reporting/report-history/`
- `GET /api/v1/reporting/export-history/`

## Proximos passos

- gerar CSV e XLSX reais
- integrar artifacts com `files_center`
- disparar geracao assincrona via Celery
- adicionar distribuicao automatica por `notification_center`
- evoluir para PDF e templates mais ricos
