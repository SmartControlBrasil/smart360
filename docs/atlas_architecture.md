# RELATÓRIO DE ESCOPO TÉCNICO E COMERCIAL: PROJETO SMART360
**Módulo:** Inteligência Comercial Avançada (PoC - São Paulo & Grande SP)
**Agente Operacional de IA:** Atlas

**Objetivo:** Captação, qualificação e abordagem automatizada de leads B2B no setor educacional para a linha de robótica Xyron (LIRO / LittleBot).

## 1. ARQUITETURA DE INFRAESTRUTURA E BLINDAGEM DE DOMÍNIO
Para garantir que a operação de e-mails em lote não afete a reputação do domínio principal da corporação (`smartcontrolbrasil.com.br`), o Atlas gerencia uma estrutura de isolamento total.

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
Os dados estruturados pelo Atlas são injetados diretamente em tempo real em uma Planilha Matriz de Leads via Webhooks ou integrações de API no Google Sheets.

**Estrutura de Atributos do Objeto (Campos):**
Instituição | Tipo (Pública/Privada) | Cidade | Região | Nome do Decisor | Cargo | E-mail de Contato | Telefone | Status da Abordagem | Lead Scoring | Notas

## 4. RÉGUA DE ABORDAGEM (COLD MAILING) E LGPD
O sistema de envios coordenado pelo Atlas utilizará templates de conversão rápida e direta, garantindo conformidade com a LGPD através de gatilhos explícitos de Opt-Out.

*   **Gatilho de Saída (LGPD):** Inclusão obrigatória de tag de remoção voluntária ao final de cada e-mail ("Caso não deseje receber mais comunicações, responda com Descadastrar").
*   **Modelos de Mensagem:** Mensagens altamente customizadas usando variáveis dinâmicas extraídas pelo raspador (`[Nome do Diretor]`, `[Nome da Escola]`, `[Cidade]`), focando nos desafios pedagógicos da BNCC e nos robôs LIRO e LittleBot como escopos principais de aplicação tecnológica.

## 5. FLUXO DE GESTÃO DE RESPOSTAS E QUALIFICAÇÃO (PIPELINE COMERCIAL)
Definição dos estados de transição do lead após a interação com o sistema.

**Ação de Resposta Positiva:** Notificação do Atlas para resposta imediata do operador (SLA < 4 horas) propondo duas opções de horários fechados via Google Meet.

**Chamada de Diagnóstico (15 minutos):**
*   **Minutos 1-3:** Alinhamento de agenda.
*   **Minutos 3-8:** Perguntas de sondagem (Dores com concorrência, implementação maker, treinamento de professores).
*   **Minutos 8-12:** Demonstração visual rápida das plataformas LIRO/LittleBot.
*   **Minutos 12-15:** Fechamento do escopo e ancoragem para proposta comercial formalizada.
