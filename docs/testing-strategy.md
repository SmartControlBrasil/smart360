# Testing Strategy

## Stack adotada

O SMART360 passa a adotar uma base de testes com:

- `pytest`
- `pytest-django`
- `factory_boy`
- `Faker`
- `rest_framework.test.APIClient`

Os testes Django legados por app continuam validos. A nova camada adiciona fundacao compartilhada e reutilizavel para crescimento do ecossistema.

## Configuracao

- `pytest.ini` define descoberta, markers e `DJANGO_SETTINGS_MODULE`
- `config/settings/test.py` usa SQLite, cache local em memoria, email locmem e hash de senha rapido

## Organizacao

- `tests/conftest.py` concentra fixtures compartilhadas
- `tests/helpers.py` concentra helpers utilitarios
- `tests/factories/` concentra factories reutilizaveis por bounded context
- `tests/smoke/` concentra validacoes rapidas de disponibilidade
- `tests/api/` concentra testes transversais de API
- `apps/<modulo>/tests/` continua sendo o lugar natural para testes especificos de dominio, service e regressao

## Factories

Factories implementadas nesta rodada cobrem os principais modelos existentes do workspace:

- core: user, company, role, membership
- identity: session, invitation, password reset
- smart_site_factory: niche, template, site order, intake
- growth: source, lead, interaction
- market_core: vendor, product, order, order item
- caneca_de_garagem: creative profile, customization request, production job
- smart_system: client, site, asset category, asset, service order, failure event
- marketplace_technicians: profile, skill, request, assignment
- marketplace_analytical: provider, category, request, assignment
- knowledge_engine: category, equipment, symptom, failure, article, document
- analytics_platform: event, metric, metric value
- billing: customer, plan, subscription, invoice, payment
- notification_center: channel, template, message, in-app notification
- backoffice: queue, alert, task
- files_center: category, stored file, file link
- global_search: index entry
- reporting_center: template, request
- configuration_center: system setting, feature flag
- scheduling_center: calendar, calendar event, task
- ai_automation_center: task type, prompt template, task request, execution, artifact
- access_control_center: permission domain, action, role permission, assignment

## Fixtures compartilhadas

Fixtures principais:

- `api_client`
- `authenticated_api_client`
- `admin_user`
- `authenticated_admin_client`
- `demo_user`
- `internal_company`
- `demo_company`
- `membership`
- `role_permission_context`
- `marketplace_scenario`
- `smart_system_scenario`

## Smoke tests

Smoke tests implementados:

- healthcheck responde
- API root responde
- schema, Swagger e ReDoc respondem

## Testes de API incluidos

Cobertura basica adicionada para:

- auth / identity
- smart_site_factory
- growth_engine
- smart_system
- market_core via endpoints do modulo `caneca_de_garagem`
- billing
- notification_center
- access_control_center

## Modulos ainda ausentes no workspace

Os seguintes contextos foram citados no briefing, mas nao existem como apps reais no codigo atual:

- `trust_and_safety`
- `crm_center`

Por isso nao receberam factories concretas nesta rodada.

`MarketplaceCategoryFactory` foi tratada apenas como factory de compatibilidade em memoria, porque `market_core` atual nao possui modelo persistido de categoria.

## Como rodar

Instalar dependencias de desenvolvimento:

```bash
pip install -r requirements/dev.txt
```

Rodar tudo:

```bash
pytest
```

Rodar smoke tests:

```bash
pytest -m smoke
```

Rodar um modulo especifico:

```bash
pytest apps/smart_system/tests/
```

Rodar a camada nova de API:

```bash
pytest tests/api -q
```

Rodar com parada rapida:

```bash
pytest --maxfail=1 -q
```

## Proximos passos

- migrar testes legados baseados em `APITestCase` gradualmente para pytest
- adicionar model tests e service tests por bounded context
- criar marcadores para suites lentas e integracao inter-modular
- incluir cobertura de bootstrap, OpenAPI e comandos de management
- conectar CI para rodar smoke + API critica a cada push
