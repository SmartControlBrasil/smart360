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
| `ATLAS_SOURCE` | não | `mock` (`google_places` em production por padrão) | Fonte da coleta: `mock` ou `google_places`. |
| `ATLAS_MIN_SCORE` | não | `5` | Score mínimo para enviar à API oficial. |
| `ATLAS_MAX_PROSPECTS_PER_RUN` | não | `10` | Limite operacional por execução. Manter baixo na PoC. |
| `ATLAS_SEGMENT` | não | `escola particular` | Query/segmento pesquisado. |
| `ATLAS_CITY` | não | `Vila Mariana` | Região/cidade pesquisada. |
| `GOOGLE_PLACES_API_KEY` | para busca real | vazio | Ausente em development ativa fallback mock do scraper. |
| `APOLLO_API_KEY` | para enriquecimento real | vazio | Ausente em development ativa fallback mock do enriquecimento. |
| `ATLAS_ENABLE_SHEETS` | não | `false` | Sheets fica desligado por padrão. |
| `ATLAS_SPREADSHEET_ID` | quando Sheets ativo | vazio | ID da planilha Google Sheets (preferencial, evita lookup por título). |
| `GOOGLE_APPLICATION_CREDENTIALS` | quando Sheets ativo | vazio | Caminho do JSON de service account, fora do repositório. |
| `ATLAS_ENABLE_MAILER` | não | `false` | Política fixa: mailer desligado. O `main.py` não chama o mailer. |

## Execução local segura

Use este fluxo para rodar localmente sem expor segredos:

1. Mantenha o JSON fora do repositório, por exemplo:
   - `~/.smart360/secrets/atlas-gcp-credentials.json`
2. Exporte as variáveis no shell atual:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/home/marcelo/.smart360/secrets/atlas-gcp-credentials.json"
export ATLAS_API_TOKEN="$(grep '^ATLAS_API_TOKEN=' .env | cut -d= -f2-)"
export ATLAS_ENABLE_SHEETS=true
.venv/bin/python -m apps.atlas_agent.main
```

Regras de segurança:
- Nunca colar JSON/token em chat, issue, commit ou print.
- Nunca commitar `.env` nem arquivos JSON de credenciais.
- Manter cold mail desligado e fluxo oficial via `import-prospects`.

## Execução Development/Mock

```bash
ATLAS_ENV=development \
ATLAS_SEGMENT="escola particular" \
ATLAS_CITY="Vila Mariana" \
ATLAS_MIN_SCORE="70" \
ATLAS_MAX_PROSPECTS_PER_RUN="5" \
ATLAS_ENABLE_MAILER="false" \
.venv/bin/python -m apps.atlas_agent.main
```

Sem `GOOGLE_PLACES_API_KEY` e `APOLLO_API_KEY`, a PoC usa dados mockados. Sem `ATLAS_API_TOKEN`/`ATLAS_COMPANY_ID`, ela não sincroniza com o Smart360 e imprime essa decisão no resumo.

## Execução Production/Manual

```bash
ATLAS_ENV=production \
ATLAS_SOURCE=google_places \
ATLAS_API_BASE_URL="https://smart360.seu-dominio-interno" \
ATLAS_API_TOKEN="token-real-seguro" \
ATLAS_COMPANY_ID="123" \
ATLAS_MAX_PROSPECTS_PER_RUN="10" \
ATLAS_MIN_SCORE="70" \
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

## Rodada real manual com Google Places

Esta seção serve como guia e checklist para a primeira rodada piloto controlada usando dados reais.

## Primeira rodada real controlada

Use esta configuração para a primeira rodada real com baixo risco operacional:

```bash
ATLAS_ENV=production \
ATLAS_SOURCE=google_places \
ATLAS_API_BASE_URL="http://127.0.0.1:8000" \
ATLAS_API_TOKEN="token-real-seguro" \
ATLAS_COMPANY_ID="1" \
ATLAS_MAX_PROSPECTS_PER_RUN="5" \
ATLAS_MIN_SCORE="70" \
ATLAS_SEGMENT="escola particular" \
ATLAS_CITY="Vila Mariana" \
ATLAS_ENABLE_SHEETS=true \
GOOGLE_PLACES_API_KEY="chave-google-real" \
.venv/bin/python -m apps.atlas_agent.main
```

Critérios desta primeira rodada:
- no máximo 5 prospects;
- zero envio de e-mail (cold mail continua desligado);
- revisão humana obrigatória em `/app/atlas/opportunities/`.

### Checklist Antes de Executar

- [ ] Validar a configuração do ambiente usando o comando de pré-validação.
- [ ] Confirmar que `ATLAS_ENV=production` está definido no ambiente.
- [ ] Confirmar que `ATLAS_SOURCE=google_places` está definido para rodada real.
- [ ] Confirmar que a chave `GOOGLE_PLACES_API_KEY` é válida e ativa.
- [ ] Confirmar que o `ATLAS_API_TOKEN` é seguro (não usar tokens inseguros como `mock-token`).
- [ ] Confirmar que o `ATLAS_COMPANY_ID` aponta para o ID da empresa correta.
- [ ] Verificar que o limite `ATLAS_MAX_PROSPECTS_PER_RUN` está definido para um valor seguro (máximo 10 no piloto).
- [ ] Garantir que cold mail e envio de e-mails permanecem desabilitados (`ATLAS_ENABLE_MAILER=false`).

### Variáveis Obrigatórias

- `ATLAS_ENV`: Definir como `production`.
- `ATLAS_API_BASE_URL`: URL base do Smart360 (ex: `http://127.0.0.1:8000`).
- `ATLAS_SOURCE`: Definir como `google_places` para coleta real.
- `ATLAS_API_TOKEN`: Token de autenticação seguro.
- `ATLAS_COMPANY_ID`: ID da empresa receptora das oportunidades.
- `GOOGLE_PLACES_API_KEY`: Chave de API ativa do Google Places.
- `ATLAS_MAX_PROSPECTS_PER_RUN`: Limite operacional de registros (máximo 10 recomendado).
- `ATLAS_MIN_SCORE`: Score mínimo para importação (ex: `70`).

### Comando de Pré-Validação

Permite validar todas as configurações sem fazer buscas no Google Places, sem realizar chamadas de rede ou registrar oportunidades:

```bash
ATLAS_VALIDATE_ONLY=true \
ATLAS_ENV=production \
ATLAS_SOURCE=google_places \
ATLAS_API_BASE_URL="http://127.0.0.1:8000" \
ATLAS_API_TOKEN="token-real-seguro" \
ATLAS_COMPANY_ID="1" \
GOOGLE_PLACES_API_KEY="chave-google-real" \
ATLAS_MAX_PROSPECTS_PER_RUN="10" \
.venv/bin/python -m apps.atlas_agent.main
```

### Comando de Execução Real Manual

Após a validação bem-sucedida, execute o comando abaixo para iniciar a rodada controlada:

```bash
ATLAS_ENV=production \
ATLAS_SOURCE=google_places \
ATLAS_API_BASE_URL="http://127.0.0.1:8000" \
ATLAS_API_TOKEN="token-real-seguro" \
ATLAS_COMPANY_ID="1" \
GOOGLE_PLACES_API_KEY="chave-google-real" \
ATLAS_MAX_PROSPECTS_PER_RUN="10" \
ATLAS_MIN_SCORE="70" \
ATLAS_SEGMENT="escola particular" \
ATLAS_CITY="São Paulo/SP" \
.venv/bin/python -m apps.atlas_agent.main
```

### Limites Recomendados

- No máximo **10 prospects** por execução na primeira rodada.
- O limite máximo absoluto configurado é de **50 prospects** (a PoC travará e falhará se um limite maior for fornecido).

### Onde Revisar Oportunidades

Após a importação bem-sucedida, os dados de prospects estarão visíveis para revisão humana em:

`Admin Shell -> Atlas Comercial -> /app/atlas/opportunities/`

A aprovação ou rejeição de cada oportunidade deve ser feita de forma estritamente manual antes de converter o prospect qualificado em Lead oficial.

### Como Interromper em Caso de Erro

- Pressione `Ctrl + C` no terminal para abortar o processo imediatamente.
- Como a execução não utiliza Celery ou filas de background demoradas, a interrupção no terminal cessará qualquer interação instantaneamente.

### Política LGPD e Conformidade

- **Zero envio de e-mails**: A PoC não envia e-mails automáticos (`ATLAS_ENABLE_MAILER` fixado em `false`).
- **Revisão humana obrigatória**: Nenhum Lead é criado diretamente; as oportunidades exigem aprovação manual no Admin Shell.
- **Mínimo necessário**: A coleta armazena apenas dados públicos da instituição e tomador de decisão para fins comerciais B2B legítimos.

## Critérios de sucesso do piloto

Registrar após a execução:

- Quantidade coletada.
- Quantidade enriquecida.
- Quantidade acima do score mínimo.
- Quantidade importada para `CommercialOpportunity`.
- Duplicados ignorados pela API oficial.
- Oportunidades prontas para revisão.
- Oportunidades aprovadas.
- Leads convertidos após revisão humana.
- Zero e-mails enviados.

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

## Como analisar o resultado da rodada

Após executar a rodada manual controlada da PoC, o operador pode auditar e avaliar o lote de importação diretamente através do painel do Admin Shell.

### Passos para Análise

1. **Acessar a Listagem de Importações**:
   Navegue no menu principal do Admin Shell até `Atlas Comercial` > `Importações` (ou diretamente em `/app/atlas/imports/`). Aqui você verá o histórico de lotes processados pelo agente.

2. **Avaliar Indicadores Globais**:
   Cada lote exibe:
   - **Total Linhas**: Quantidade total de prospects processados pelo pipeline standalone.
   - **Criados**: Quantidade de oportunidades comerciais geradas e salvas com sucesso.
   - **Duplicados**: Quantidade de registros repetidos (já existentes) ignorados de forma graciosa.
   - **Erros**: Quantidade de linhas que falharam durante a extração ou análise de inteligência.

3. **Análise de Oportunidades Filtradas**:
   Ao lado de cada lote, clique no botão **"Ver Oportunidades"** para abrir a fila de oportunidades filtrada exclusivamente com os registros importados daquela rodada específica.

4. **Auditoria de Detalhes e Falhas**:
   Clique em **"Detalhes"** em um lote específico para visualizar:
   - Os metadados de auditoria completos (UUID, arquivos, data de execução, etc.).
   - A tabela detalhada contendo o índice de cada linha falha com a respectiva mensagem descritiva de erro técnico, ajudando a identificar ausência de chaves de contato, inconsistência de dados ou limites operacionais estourados.

