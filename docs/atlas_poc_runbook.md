# Atlas PoC Runbook - Execução Manual Controlada

## Objetivo

Rodar a PoC standalone do Atlas de forma controlada, usando o fluxo oficial do Smart360:

`PoC/CSV/API -> /api/v1/ai-agents/atlas/import-prospects/ -> CommercialOpportunity -> revisão humana -> Lead`

A PoC coleta prospects, enriquece dados quando houver chaves reais, aplica scoring, limita o volume por execução e envia apenas prospects qualificados para a fila `CommercialOpportunity`.

## Variáveis de Ambiente

| Variável | Obrigatória em production | Padrão | Observação |
| --- | --- | --- | --- |
| `ATLAS_ENV` | sim | `development` | Use `production` apenas para execução real controlada. |
| `ATLAS_API_BASE_URL` | sim | `http://127.0.0.1:8000` | Base interna/local do Smart360. |
| `ATLAS_API_TOKEN` | sim | vazio | Nunca usar `mock-token`, `default` ou valor placeholder em production. |
| `ATLAS_COMPANY_ID` | sim | `0` | Empresa que receberá as oportunidades. |
| `ATLAS_MIN_SCORE` | não | `5` | Score mínimo para enviar à API oficial. |
| `ATLAS_MAX_PROSPECTS_PER_RUN` | não | `10` | Limite operacional por execução. Manter baixo na PoC. |
| `ATLAS_SEGMENT` | não | `escola particular` | Query/segmento pesquisado. |
| `ATLAS_CITY` | não | `Vila Mariana` | Região/cidade pesquisada. |
| `GOOGLE_PLACES_API_KEY` | para busca real | vazio | Ausente em development ativa fallback mock do scraper. |
| `APOLLO_API_KEY` | para enriquecimento real | vazio | Ausente em development ativa fallback mock do enriquecimento. |
| `ATLAS_ENABLE_SHEETS` | não | `false` | Sheets fica desligado por padrão. |
| `ATLAS_ENABLE_MAILER` | não | `false` | Política fixa: mailer desligado. O `main.py` não chama o mailer. |

## Execução Development/Mock

```bash
ATLAS_ENV=development \
ATLAS_MAX_PROSPECTS_PER_RUN=5 \
ATLAS_SEGMENT="escola particular" \
ATLAS_CITY="Vila Mariana" \
.venv/bin/python -m apps.atlas_agent.main
```

Sem `GOOGLE_PLACES_API_KEY` e `APOLLO_API_KEY`, a PoC usa dados mockados. Sem `ATLAS_API_TOKEN`/`ATLAS_COMPANY_ID`, ela não sincroniza com o Smart360 e imprime essa decisão no resumo.

## Execução Production/Manual

```bash
ATLAS_ENV=production \
ATLAS_API_BASE_URL="https://smart360.seu-dominio-interno" \
ATLAS_API_TOKEN="token-real-seguro" \
ATLAS_COMPANY_ID="123" \
ATLAS_MAX_PROSPECTS_PER_RUN="10" \
ATLAS_MIN_SCORE="5" \
ATLAS_SEGMENT="escola particular" \
ATLAS_CITY="Vila Mariana" \
GOOGLE_PLACES_API_KEY="chave-real" \
APOLLO_API_KEY="chave-real" \
.venv/bin/python -m apps.atlas_agent.main
```

Production falha com erro claro se faltar `ATLAS_API_BASE_URL`, `ATLAS_API_TOKEN` ou `ATLAS_COMPANY_ID`, ou se o token for inseguro como `mock-token`.

## Limites Recomendados

- Começar com `ATLAS_MAX_PROSPECTS_PER_RUN=5`.
- Usar no máximo `10` por execução nesta fase.
- Validar o lote no Admin Shell antes de rodar novo lote.
- Não ativar envio de e-mail.
- Não criar Lead direto pela PoC.

## Checklist Antes de Rodar

- Confirmar que `ATLAS_ENV` está correto.
- Confirmar que o token real não aparece em logs, terminal compartilhado ou arquivo commitado.
- Confirmar `ATLAS_COMPANY_ID` da empresa correta.
- Confirmar limite baixo em `ATLAS_MAX_PROSPECTS_PER_RUN`.
- Confirmar que `ATLAS_ENABLE_SHEETS=false`, exceto em teste manual específico.
- Confirmar que cold mail permanece desligado.

## Revisão Após Execução

As oportunidades importadas devem ser revisadas em:

`Admin Shell -> Atlas Comercial -> /app/atlas/opportunities/`

Somente oportunidades aprovadas por humano podem ser convertidas para Lead no Growth Engine.

## Política

- Cold mail desligado.
- Revisão humana obrigatória.
- LGPD: usar apenas fontes permitidas, registrar origem e manter opt-out/comunicação comercial fora desta PoC.
- Não usar `AtlasLead`/`PendingAtlasLead` em novos fluxos.
- Não chamar endpoint legado `/api/v1/ai-agents/atlas-leads/ingest/`.
