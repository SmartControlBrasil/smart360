# SMART360 Project Structure

## Root

- `manage.py`: entrypoint de management commands.
- `Dockerfile`: imagem base de desenvolvimento.
- `docker-compose.yml`: stack local com Django, PostgreSQL, Redis e Celery.
- `requirements/`: dependências segmentadas por ambiente.

## Configuração

- `config/settings/base.py`: defaults compartilhados.
- `config/settings/development.py`: ambiente local.
- `config/settings/production.py`: ambiente produtivo.
- `config/celery.py`: bootstrap da fila.
- `config/urls.py`: rotas globais.

## Aplicações

- `apps/core/`: núcleo técnico inicial, healthcheck e registro de módulos.
- `apps/users/`, `apps/companies/`, `apps/roles/`, `apps/audit/`: contextos transversais base.
- `apps/smart_site_factory/`
- `apps/growth_engine/`
- `apps/caneca_de_garagem/`
- `apps/smart_system/`
- `apps/marketplace_technicians/`
- `apps/marketplace_analytical/`
- `apps/knowledge_engine/`

## Plataformas de apoio

- `shared_kernel/`: contratos e componentes compartilhados.
- `integration_bus/`: eventos, contratos e futuras integrações.
- `analytics_platform/`: modelos analíticos e projeções.
- `scripts/`: bootstrap e automações operacionais.
