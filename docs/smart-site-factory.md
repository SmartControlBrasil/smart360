# SMART SITE FACTORY

## Visao do modulo

O Smart Site Factory e a linha de montagem digital do ecossistema SMART360 para venda e producao de sites nichados como produto padronizado.

## Entidades

- `Niche`: catalogo de nichos atendidos.
- `Template`: templates disponiveis por nicho.
- `ConfiguratorQuestion`: perguntas do configurador comercial.
- `ConfiguratorOption`: opcoes das perguntas.
- `TemplateRecommendationRule`: regra simples de recomendacao baseada em nicho e opcao.
- `SiteOrder`: pedido do cliente/empresa.
- `SiteOrderAnswer`: respostas do configurador associadas ao pedido.
- `SiteProjectIntake`: briefing estruturado do negocio.
- `ProductionTask`: acompanhamento operacional por etapa.
- `DeliveryRecord`: registro da entrega e aceite.

## Fluxo do pedido

1. Operacao cadastra nichos, templates, perguntas, opcoes e regras.
2. Cliente ou equipe cria um `SiteOrder`.
3. O modulo avalia respostas do configurador e sugere um template.
4. O pedido nasce com etapas padrao de producao.
5. O intake complementa os dados reais do negocio.
6. A equipe acompanha as tasks ate entrega.
7. A entrega gera `DeliveryRecord` e atualiza o status do pedido.

## Endpoints criados

- `GET|POST /api/v1/site-factory/niches/`
- `GET|POST /api/v1/site-factory/templates/`
- `GET|POST /api/v1/site-factory/questions/`
- `GET|POST /api/v1/site-factory/options/`
- `GET|POST /api/v1/site-factory/rules/`
- `GET|POST /api/v1/site-factory/orders/`
- `GET|POST /api/v1/site-factory/intakes/`
- `GET|POST /api/v1/site-factory/production/`
- `POST /api/v1/site-factory/production/{id}/start/`
- `POST /api/v1/site-factory/production/{id}/complete/`
- `GET|POST /api/v1/site-factory/deliveries/`
