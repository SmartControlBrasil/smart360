# Public API

## Visao geral

A API publica do SMART360 foi publicada em:

- `/api/public/v1/`

Objetivos desta primeira versao:

- acesso autenticado por usuario
- base pronta para integracao por credencial de integracao
- versionamento explicito
- scoping por empresa e site
- autorizacao por perfil
- integracao com billing e observabilidade

## Autenticacao

Modos suportados:

1. User API Access
- `Authorization: Bearer <token>`
- ou `Authorization: Token <token>`
- usa `UserSession` da camada de identidade

2. Integration Access
- `Authorization: ApiKey <prefix.secret>`
- credencial vinculada a um usuario e opcionalmente a uma empresa
- primeira base estrutural para integracoes servidor-servidor
- `allowed_scopes` da credencial pode restringir domínios/acoes como `assets.view`, `work_orders.*` ou `*`

## Contexto ativo

O contexto da chamada pode ser refinado por request com:

- header `X-Company-Slug`
- header `X-Site-Code`

ou via query params:

- `company`
- `site`

Se omitidos, a API usa o primeiro contexto permitido do usuario autenticado.
Quando a credencial de integracao estiver vinculada a uma empresa, o contexto nao pode escapar desse tenant.

## Paginacao, filtros e ordenacao

Padrao:

- `page`
- `page_size`
- filtros por querystring conforme endpoint
- `ordering`
- `search`

Throttling inicial:

- burst: `60/minute`
- sustained: `1000/day`

Os valores podem ser ajustados por:

- `PUBLIC_API_BURST_RATE`
- `PUBLIC_API_SUSTAINED_RATE`

## Erros

As respostas de erro seguem estrutura:

```json
{
  "error": {
    "code": "permission_denied",
    "detail": "You do not have permission to perform this action in the active scope.",
    "status_code": 403,
    "request_id": "..."
  }
}
```

## Endpoints iniciais

- `GET /api/public/v1/context/`
- `GET /api/public/v1/companies/`
- `GET /api/public/v1/sites/`
- `GET|POST|PATCH /api/public/v1/assets/`
- `GET|POST|PATCH /api/public/v1/work-orders/`
- `POST /api/public/v1/work-orders/{public_id}/assign/`
- `GET /api/public/v1/preventives/`
- `GET /api/public/v1/preventives/schedule/`
- `GET|POST|PATCH /api/public/v1/failures/`
- `PATCH /api/public/v1/failures/{public_id}/rca/`
- `GET /api/public/v1/checklists/`
- `GET|POST|PATCH /api/public/v1/checklist-executions/`
- `GET /api/public/v1/parts/`
- `GET /api/public/v1/parts/{public_id}/asset-links/`
- `GET|POST /api/public/v1/stock-movements/`
- `GET /api/public/v1/reports/`
- `GET /api/public/v1/reports/{report_type}/{reference_code}/`
- `GET /api/public/v1/reports/{report_type}/{reference_code}/download/`
- `GET|POST /api/public/v1/marketplace/service-requests/{public_id}/matching/`

## Seguranca

- autorizacao por RBAC do Smart System
- scoping multiempresa/multisite obrigatorio
- bloqueio por billing para tenants suspensos
- request id e correlation id integrados
- eventos auditaveis em exportacao e acoes sensiveis
- `X-Request-ID` e `X-Correlation-ID` retornados nas respostas

## OpenAPI

Docs dedicadas da API publica:

- `/api/public/schema/`
- `/api/public/docs/`
- `/api/public/redoc/`

## Evolucao recomendada

- matching configuravel por categoria, distancia e SLA
- webhooks
- SDKs
- OAuth
- portal do cliente
- API keys com scopes mais finos
- relatorios em lote
- endpoints de execucao tecnica e mobile offline
