# API Overview

## Visao geral

A API do SMART360 segue o prefixo principal `/api/v1/` e expõe bounded contexts independentes com contratos HTTP consistentes. A documentacao OpenAPI e gerada com `drf-spectacular`.

## Endpoints principais de documentacao

- `/api/schema/`
- `/api/docs/`
- `/api/redoc/`

Compatibilidade legada:

- `/api/docs/swagger/`
- `/api/docs/redoc/`

## Convencoes de URL

- prefixo por bounded context
- nomes de recursos em kebab-case
- actions customizadas como subpaths do recurso

Exemplos:

- `/api/v1/auth/login/`
- `/api/v1/smart-system/service-orders/`
- `/api/v1/billing/payment-records/{id}/mark_paid/`

## Autenticacao

O ecossistema usa autenticacao baseada em token de sessao:

- `Authorization: Bearer <token>`
- `Authorization: Token <token>`

Alguns endpoints publicos ficam liberados, como healthcheck, login, reset de senha e confirmacao de verificacao.

## Paginacao

Listagens usam `PageNumberPagination` com envelope padrao:

- `count`
- `next`
- `previous`
- `results`

## Formato geral de resposta

Recursos unitarios retornam o payload serializado diretamente.  
Listagens retornam envelope paginado.  
Actions customizadas podem retornar:

- payload do recurso atualizado
- resultado operacional simples
- `204 No Content` para operacoes sem corpo

