# Global Search

## Visao do modulo

O `global_search` centraliza indexacao e busca textual transversal no ecossistema SMART360. Ele permite registrar entradas genericas de busca, consultar resultados unificados, salvar filtros, manter sinonimos e aplicar regras simples de boost.

## Entidades

- `SearchIndexEntry`: item indexado principal
- `SearchQueryLog`: historico de consultas
- `SearchSavedFilter`: filtros salvos por usuario ou empresa
- `SearchSynonym`: sinonimos para expandir consultas
- `SearchBoostRule`: regras simples de prioridade

## Fluxo de indexacao

1. um modulo cria ou atualiza `SearchIndexEntry`
2. `search_text` concentra o texto pesquisavel
3. metadados e URL ajudam navegacao futura
4. o modulo fica pronto para receber atualizacoes vindas de eventos

## Fluxo de busca

1. cliente chama `GET /api/v1/search/query/`
2. a query pode ser expandida por sinonimos
3. filtros por modulo, tipo, status e categoria sao aplicados
4. boost rules elevam prioridades simples
5. `SearchQueryLog` registra a consulta

## Filtros

Suporta:

- `q`
- `source_module`
- `item_type`
- `status`
- `category`
- `ordering`

## Autocomplete

`GET /api/v1/search/autocomplete/` faz busca simples em `title` e `search_text` para sugerir resultados rapidos.

## Integracao com os demais modulos

O modulo foi preparado para indexar entidades de:

- `smart_system`
- `marketplace_technicians`
- `marketplace_analytical`
- `caneca_de_garagem`
- `smart_site_factory`
- `growth_engine`
- `knowledge_engine`
- `billing`
- `files_center`
- `backoffice`

Sem acoplamento profundo nesta rodada. A indexacao futura pode ser disparada por `integration_bus`.

## Endpoints criados

- `GET|POST /api/v1/search/index-entries/`
- `GET /api/v1/search/query-logs/`
- `GET|POST /api/v1/search/saved-filters/`
- `GET|POST /api/v1/search/synonyms/`
- `GET|POST /api/v1/search/boost-rules/`
- `GET /api/v1/search/query/`
- `GET /api/v1/search/autocomplete/`

## Proximos passos

- criar indexadores por bounded context
- integrar com `integration_bus` para reindexacao automatica
- evoluir ranking, stemming e relevancia
- preparar troca para engine externa
- adicionar busca semantica futura
