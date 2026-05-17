# API Conventions

## Naming

- caminhos em kebab-case
- campos de payload em snake_case
- `slug` para identificadores legiveis quando fizer sentido
- `public_id` para exposicao segura de UUID

## Filtros e busca

Os endpoints usam combinacoes de:

- `page`
- `search`
- `ordering`
- filtros especificos por recurso

## Responses

- `200 OK`: leitura ou action bem-sucedida
- `201 Created`: criacao
- `202 Accepted`: operacao assicrona ou requisicao recebida
- `204 No Content`: operacao sem corpo de resposta
- `400 Bad Request`: validacao
- `401 Unauthorized`: autenticacao ausente ou invalida
- `403 Forbidden`: permissao negada
- `404 Not Found`: recurso inexistente

## Enums

Os principais enums de negocio sao expostos no schema OpenAPI a partir dos serializers e choices dos modelos.

## Erros comuns

- senha divergente em change/reset password
- token invalido ou expirado
- permissao negada por role/policy
- acao customizada sem payload obrigatorio

