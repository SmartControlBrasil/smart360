# Bootstrap SMART360

## Visao da estrategia

O bootstrap do SMART360 foi implementado com comandos de management em `apps/core/management/commands/` e seeders modulares em `apps/core/bootstrap/`. A estrategia privilegia:

- idempotencia com `get_or_create` e `update_or_create`
- cenarios coerentes entre bounded contexts
- dados de demo utilizaveis logo apos `migrate`
- rerun seguro como caminho principal em ambiente local

## Comandos disponiveis

- `python manage.py bootstrap_smart360`
- `python manage.py seed_core`
- `python manage.py seed_site_factory`
- `python manage.py seed_smart_system`
- `python manage.py seed_marketplaces`
- `python manage.py seed_growth`
- `python manage.py seed_knowledge`
- `python manage.py seed_billing`
- `python manage.py seed_backoffice`

Todos aceitam opcionalmente:

- `--demo-password`

## Ordem de execucao do bootstrap principal

1. core platform
2. files center
3. smart site factory
4. growth engine
5. market core e caneca de garagem
6. smart system
7. marketplace technicians
8. marketplace analytical
9. knowledge engine
10. analytics platform
11. billing
12. notification center
13. backoffice
14. global search
15. reporting center
16. configuration center
17. scheduling center
18. ai automation center

## Credenciais demo

Senha padrao local:

- `admin123!`

Usuarios:

- `admin@smart360.local`
- `ops@smart360.local`
- `comercial@smart360.local`
- `engenharia@smart360.local`
- `cliente@academia.local`

## Dados criados por modulo

- `core_platform`: roles, users, companies, memberships, sessions, onboarding, convites e audit log
- `smart_site_factory`: niches, templates, questions, options, recommendation rules, site orders, intake, answers, production tasks e delivery
- `growth_engine`: sources, tags, campaign, leads, interactions, qualification e assignments
- `market_core`: vendors, products, orders e order items
- `caneca_de_garagem`: creative profile, customization templates, request, artwork asset, production job, steps e shipment
- `smart_system`: client, site, asset category, asset, checklist, maintenance plan, service orders, failure, history, worklog e document
- `marketplace_technicians`: skills, profile, region, availability, request, matching, assignment, review e compensation
- `marketplace_analytical`: provider, category, service, capability, region, request, matching, assignment, report e review
- `knowledge_engine`: categorias, equipamento, sintoma, falha, causa, acao, artigo, documento, tags e mapas
- `analytics_platform`: events, metrics, values, dashboard, widget e snapshot
- `billing`: customer, plans, addon, subscription, invoice, payment, wallet, credit transaction, ledger e commission statement
- `notification_center`: channels, templates, preferences, event, message, in-app, delivery log e batch
- `backoffice`: queue, queue item, alert, task, quick action e widget
- `files_center`: category, stored file, link, media asset, version, access log e collection
- `global_search`: index entries, query log, saved filter, synonym e boost rule
- `reporting_center`: template, export profile, request, artifact, execution, log e scheduled report
- `configuration_center`: settings, flags, toggle e module profile
- `scheduling_center`: calendar, event, participant, recurrence, availability, reminder e task
- `ai_automation_center`: task types, model config, context profile, prompt, prompt version, task request/execution/artifact, automation rule e retrieval config

## Idempotencia

O bootstrap foi desenhado para rerun seguro no ambiente local. O caminho recomendado para atualizar demo data e:

1. ajustar os seeders
2. rodar `python manage.py bootstrap_smart360` novamente

Nao foi implementado um reset destrutivo generico nesta rodada para evitar apagar dados locais do usuario.

## Observacoes

- `trust_and_safety` e `crm_center` ainda nao existem como apps reais neste workspace atual. O bootstrap principal registra essa ausencia e segue sem falhar.
- Alguns escopos pedidos pelo briefing, como categorias/carrinhos/avaliacoes do `market_core`, nao existem no modelo atual e por isso foram adaptados aos agregados realmente disponiveis no codigo.
