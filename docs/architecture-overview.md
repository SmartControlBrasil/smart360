# SMART360 Architecture Overview

O SMART360 foi estruturado como um ecossistema modular em Django, com um `core` transversal e módulos de negócio isolados em `apps/`.

## Princípios adotados

- Python 3.12+
- Django 5+
- Django REST Framework como camada HTTP
- PostgreSQL como banco transacional
- Redis para cache e mensageria
- Celery para workloads assíncronos
- Docker para execução local consistente
- DDD pragmático com separação gradual por contexto
- arquitetura hexagonal nos módulos principais

## Organização macro

- `config/`: bootstrap do Django, settings por ambiente, URLs e Celery.
- `apps/`: bounded contexts e módulos do ecossistema.
- `shared_kernel/`: contratos, tipos compartilhados e componentes cross-cutting.
- `integration_bus/`: definição de eventos, contratos de integração e adaptadores futuros.
- `analytics_platform/`: projeções, read models e assets analíticos.
- `docs/`: documentação viva da arquitetura e do setup.

## Estratégia modular

Cada módulo principal pode evoluir internamente com os diretórios:

- `domain/`: entidades, regras e invariantes.
- `application/`: casos de uso e orquestração.
- `infrastructure/`: persistência, gateways e adaptadores.
- `api/`: camada HTTP quando o módulo expõe endpoints.

## Ambientes

- `config.settings.base`: defaults compartilhados.
- `config.settings.development`: desenvolvimento local com permissões abertas para a API.
- `config.settings.production`: endurecimento de segurança para produção.

## API base

- `GET /health/`: healthcheck simples da aplicação.
- `GET /api/v1/`: root da API com visão dos módulos registrados.
- `GET /api/schema/`: schema OpenAPI.
- `GET /api/docs/swagger/`: Swagger UI.
- `GET /api/docs/redoc/`: ReDoc.
