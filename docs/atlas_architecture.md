# RELATÓRIO DE ESCOPO TÉCNICO E COMERCIAL: PROJETO SMART360
**Módulo:** Inteligência Comercial Avançada (PoC - São Paulo & Grande SP)
**Agente Operacional de IA:** Atlas

**Objetivo:** Captação e qualificação de prospects B2B no setor educacional para revisão humana no Smart360 antes de qualquer conversão comercial.

## Status operacional atual no Smart360

O Atlas opera em duas camadas conectadas, com revisão humana obrigatória:

1. A PoC em `apps/atlas_agent/` coleta, enriquece e pontua prospects públicos.
2. O cliente `apps/atlas_agent/api_client.py` envia prospects qualificados para `POST /api/v1/ai-agents/atlas/import-prospects/`.
3. A API cria `CommercialOpportunity` em `READY_FOR_REVIEW`, preservando origem, lote, contatos institucionais e dados de auditoria em `AtlasProspectImportBatch`.
4. Um humano aprova ou rejeita a oportunidade no Smart360.
5. Somente oportunidades `APPROVED` podem ser convertidas manualmente para `Lead` no Growth Engine.

Não há criação direta de Lead pela PoC e não há envio automático de e-mail nesta etapa. O cold mail permanece documentado como capacidade experimental desativada, não como rotina de produção.

### Comandos seguros

```bash
# validação geral
.venv/bin/python manage.py check

# testes focados Atlas
.venv/bin/python manage.py test apps.ai_agents_center.tests.test_atlas_importer apps.ai_agents_center.tests.test_atlas_opportunity_review apps.ai_agents_center.tests.test_atlas_standalone_integration apps.ai_agents_center.tests.test_atlas_opportunities
```

### Variáveis de ambiente da PoC

- `ATLAS_ENV`: mantém dry-run quando diferente de `production`.
- `ATLAS_API_BASE_URL`: URL do Smart360 interno/local.
- `ATLAS_API_TOKEN`: token de API; não deve ser commitado.
- `ATLAS_COMPANY_ID`: empresa alvo da fila de oportunidades.
- `ATLAS_MIN_SCORE`: score mínimo para enviar à API oficial.

Se `ATLAS_API_TOKEN` ou `ATLAS_COMPANY_ID` estiverem ausentes, a PoC pula a sincronização oficial em modo seguro. O pipeline principal imprime que cold mail está desativado e não instancia envio SMTP.

## 1. ARQUITETURA DE INFRAESTRUTURA E BLINDAGEM DE DOMÍNIO
Caso a capacidade de e-mail seja retomada no futuro, ela deve ficar isolada do domínio principal da corporação (`smartcontrolbrasil.com.br`). Nesta etapa, o domínio dedicado é apenas referência/configuração segura, sem disparo real.

*   **Domínio de Prospecção Dedicado:** `mcautomation.com.br` (Registrado no Registro.br).
*   **Servidor de E-mail:** Google Workspace (Plano Business Starter).
*   **Camada de Segurança e Entregabilidade (DNS):**
    *   **MX:** Apontamento unificado para `SMTP.GOOGLE.COM.` para recepção estável.
    *   **SPF (TXT):** Declaração de autorização de envio (`v=spf1 include:_spf.google.com ~all`) para evitar filtros de spoofing.
    *   **DKIM (TXT):** Assinatura criptografada (Seletor: `google`, 2048 bits). *Nota Técnica: A ativação da assinatura na API do Google Admin exige um delay de maturação de até 24 horas após a criação da conta do Workspace. Isso evita que o script trate a ausência temporária da chave como um erro crítico de DNS.*
*   **Redirecionamento Web:** O tráfego HTTP/HTTPS do domínio de prospecção redireciona automaticamente para a URL principal da empresa para passar autoridade aos leads que pesquisarem a marca.

## 2. ENGINE DE CAPTAÇÃO E ENRIQUECIMENTO AUTOMATIZADO (SCRAPING)
O motor de busca do Atlas operará de forma modular, dividindo a coleta e o tratamento de dados em microsserviços.

### Fluxo do Pipeline de Dados do Atlas:
**Módulo de Geolocalização e Alvos (Fase 1 - SP & Grande SP):**
*   Conexão via APIs de mapas e listagens públicas para varredura em lote por quadrantes estruturados.
*   **Queries de Busca:** "escola particular", "colégio privado", "secretaria de educação", "escola técnica".
*   **Bairros Foco (Capital):** Vila Mariana, Moema, Pinheiros, Perdizes, Tatuapé, Morumbi.
*   **Cidades Foco (Grande SP):** ABC Paulista, Guarulhos, Osasco, Barueri (Alphaville), Itapevi.

**Módulo de Enriquecimento B2B (Data Enrichment):**
*   O Atlas captura o domínio do site da escola e executa chamadas de API em bancos de dados corporativos integrados (ex: Apollo, Hunter ou Lusha) para mapear o organograma da instituição.
*   **Campos prioritários de extração:** Nome do Decisor, Cargo (Diretor Pedagógico, Mantenedor, Secretário), E-mail Corporativo Direto e Telefone/WhatsApp.

**Filtro e Lead Scoring Automatizado:**
*   O Atlas aplica filtros baseados na grade ofertada pela escola. Instituições que possuem apenas Berçário/Educação Infantil são descartadas via código.
*   **Priorização máxima (Score 5)** para escolas com Ensino Fundamental II e Ensino Médio (público-alvo do LittleBot e LIRO).

## 3. ARMAZENAMENTO E MATRIZ DE LEADS
Os dados estruturados pela PoC podem ser espelhados em uma Planilha Matriz de Leads para conferência operacional, mas a fila oficial de revisão é a API do Smart360 em `CommercialOpportunity`.

**Estrutura de Atributos do Objeto (Campos):**
Instituição | Tipo (Pública/Privada) | Cidade | Região | Nome do Decisor | Cargo | E-mail de Contato | Telefone | Status da Abordagem | Lead Scoring | Notas

## 4. RÉGUA DE ABORDAGEM (COLD MAILING) E LGPD
O envio automático de e-mails está desativado no fluxo atual. A PoC pode manter templates e testes em dry-run para avaliação interna, mas produção não deve disparar cold mail nem criar campanhas automaticamente.

*   **Sem envio automático:** prospects importados viram `CommercialOpportunity`, não mensagem enviada.
*   **Revisão humana obrigatória:** apenas oportunidades aprovadas podem virar `Lead` no Growth Engine.
*   **Domínio dedicado:** `mcautomation.com.br` permanece apenas como referência/configuração segura de isolamento; não ativar disparo real nesta etapa.
*   **LGPD futura:** qualquer retomada de e-mail exigirá opt-out explícito, revisão jurídica/comercial e configuração separada de produção.

## 5. FLUXO DE GESTÃO DE RESPOSTAS E QUALIFICAÇÃO (PIPELINE COMERCIAL)
Definição dos estados de transição do lead após a interação com o sistema.

**Ação de Resposta Positiva:** Notificação do Atlas para resposta imediata do operador (SLA < 4 horas) propondo duas opções de horários fechados via Google Meet.

**Chamada de Diagnóstico (15 minutos):**
*   **Minutos 1-3:** Alinhamento de agenda.
*   **Minutos 3-8:** Perguntas de sondagem (Dores com concorrência, implementação maker, treinamento de professores).
*   **Minutos 8-12:** Demonstração visual rápida das plataformas LIRO/LittleBot.
*   **Minutos 12-15:** Fechamento do escopo e ancoragem para proposta comercial formalizada.
