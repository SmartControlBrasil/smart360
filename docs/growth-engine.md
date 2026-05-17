# GROWTH ENGINE

## Visao do modulo

O Growth Engine e o motor de aquisicao e qualificacao de leads do ecossistema SMART360. Ele centraliza origem, pipeline, atribuicao, interacoes comerciais e score inicial.

## Entidades

- `LeadSource`
- `Lead`
- `LeadTag`
- `LeadInteraction`
- `LeadCampaign`
- `LeadQualification`
- `LeadAssignment`

## Fluxo inicial

1. Operacao cadastra fontes, tags e campanhas.
2. Comercial cria ou importa um lead.
3. O modulo calcula score inicial automaticamente.
4. O lead pode ser tagueado, qualificado e atribuido a um usuario.
5. Interacoes alimentam o historico do pipeline.

## Endpoints

- `GET|POST /api/v1/growth/sources/`
- `GET|POST /api/v1/growth/tags/`
- `GET|POST /api/v1/growth/campaigns/`
- `GET|POST /api/v1/growth/leads/`
- `POST /api/v1/growth/leads/{id}/assign/`
- `GET|POST /api/v1/growth/interactions/`
- `GET|POST /api/v1/growth/qualifications/`
- `GET|POST /api/v1/growth/assignments/`
