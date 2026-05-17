# Files Center

## Visao do modulo

O `files_center` centraliza o ciclo de vida de arquivos e midias do SMART360. Ele oferece categorias, arquivos armazenados, vinculos genericos, midias enriquecidas, versionamento, logs de acesso e colecoes.

## Entidades

- `FileCategory`: categorias logicas de arquivo
- `StoredFile`: arquivo principal armazenado
- `FileLink`: vinculo transversal com qualquer item do ecossistema
- `MediaAsset`: representacao enriquecida para galerias e frontends
- `FileVersion`: versionamento simples de arquivos
- `FileAccessLog`: historico de upload, visualizacao, download e vinculo
- `FileCollection`: agrupamento logico
- `FileCollectionItem`: itens da colecao

## Fluxo de upload

1. criar `StoredFile`
2. registrar metadados, backend, visibilidade e categoria
3. gerar checksum quando possivel
4. registrar `FileAccessLog` de upload

## Vinculo com outros modulos

`FileLink` usa:

- `related_module`
- `related_item_type`
- `related_item_id`

Isso permite associar arquivos a `smart_site_factory`, `caneca_de_garagem`, `smart_system`, `trust_and_safety`, `marketplace_technicians`, `marketplace_analytical`, `knowledge_engine`, `billing`, `notification_center` e `backoffice` sem acoplamento direto.

## Storage

Nesta rodada o modulo usa `FileField` com storage local do Django. O dominio ja guarda `storage_backend` para futura troca por S3/MinIO sem quebrar a modelagem.

## Visibilidade

O modelo suporta:

- `private`
- `internal`
- `public`

## Versionamento

`FileVersion` permite manter revisoes simples para documentos e artefatos operacionais.

## Endpoints criados

- `GET|POST /api/v1/files/categories/`
- `GET|POST /api/v1/files/files/`
- `GET|POST /api/v1/files/file-links/`
- `GET|POST /api/v1/files/media-assets/`
- `GET|POST /api/v1/files/versions/`
- `GET|POST /api/v1/files/access-logs/`
- `GET|POST /api/v1/files/collections/`
- `GET|POST /api/v1/files/collection-items/`

## Proximos passos

- integrar politicas de acesso por papel e visibilidade
- adicionar adaptadores reais para S3/MinIO
- gerar thumbnails e derivados de imagem
- integrar eventos com `integration_bus`
- adicionar presigned URLs e auditoria de download
