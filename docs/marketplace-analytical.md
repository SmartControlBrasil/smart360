# MARKETPLACE ANALYTICAL

## Visao do modulo

O Marketplace Analytical e a plataforma B2B de servicos tecnicos especializados, conectando clientes industriais a laboratorios, consultores e especialistas para analises, diagnosticos, inspecoes e laudos tecnicos.

## Entidades

- `AnalyticalProvider`
- `AnalyticalServiceCategory`
- `AnalyticalService`
- `AnalyticalServiceCapability`
- `AnalyticalServiceRegion`
- `AnalyticalRequest`
- `AnalyticalMatchingRecord`
- `AnalyticalAssignment`
- `AnalyticalReport`
- `AnalyticalReview`

## Fluxo de servico

1. Providers especializados se cadastram e publicam servicos.
2. O cliente abre uma demanda analitica diretamente ou a partir do Smart System.
3. O sistema registra providers elegiveis por matching.
4. Um provider recebe assignment e executa o servico.
5. O resultado tecnico e entregue via relatorio formal.

## Fluxo de analise

1. A demanda define categoria, prioridade, local e referencias tecnicas.
2. Providers com categoria aderente entram na base de matching.
3. O assignment segue ciclo de aceite, execucao e conclusao.

## Fluxo de relatorio tecnico

1. Provider conclui o assignment.
2. O modulo permite anexar `AnalyticalReport`.
3. O cliente pode registrar review, alimentando reputacao do provider.

## Integracoes com smart_system

- `AnalyticalRequest` aceita vinculo com `Asset`, `OperationalSite` e `ServiceOrder`.
- A origem `smart_system` deixa o modulo preparado para conversao futura de eventos operacionais em demanda analitica.

## Endpoints criados

- `GET|POST /api/v1/marketplace-analytical/providers/`
- `GET|POST /api/v1/marketplace-analytical/service-categories/`
- `GET|POST /api/v1/marketplace-analytical/services/`
- `GET|POST /api/v1/marketplace-analytical/capabilities/`
- `GET|POST /api/v1/marketplace-analytical/service-regions/`
- `GET|POST /api/v1/marketplace-analytical/requests/`
- `GET|POST /api/v1/marketplace-analytical/matching-records/`
- `GET|POST /api/v1/marketplace-analytical/assignments/`
- `POST /api/v1/marketplace-analytical/assignments/{id}/accept/`
- `POST /api/v1/marketplace-analytical/assignments/{id}/decline/`
- `POST /api/v1/marketplace-analytical/assignments/{id}/start/`
- `POST /api/v1/marketplace-analytical/assignments/{id}/complete/`
- `GET|POST /api/v1/marketplace-analytical/reports/`
- `GET|POST /api/v1/marketplace-analytical/reviews/`
