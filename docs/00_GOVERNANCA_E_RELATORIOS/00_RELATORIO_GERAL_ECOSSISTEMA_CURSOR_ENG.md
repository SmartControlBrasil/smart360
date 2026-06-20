# RELATÓRIO-MESTRE DO ECOSSISTEMA SMART CONTROL BRASIL / SMART360

**Arquivo sugerido:** `00_RELATORIO_GERAL_ECOSSISTEMA_CURSOR_ENG.md`  
**Data:** 19/06/2026  
**Responsável estratégico:** Marcelo Custodio  
**Uso recomendado:** entregar ao Cursor, Gemini, Codex, engenheiro auxiliar ou qualquer agente técnico antes de mexer no projeto.

---

## 1. Objetivo deste documento

Este documento consolida o estado geral do ecossistema **Smart Control Brasil / Smart360** para que um engenheiro, agente de IA ou desenvolvedor entre no projeto com contexto suficiente para tomar boas decisões técnicas.

O foco não é apenas listar módulos. O objetivo é explicar:

- o que é o projeto;
- qual é a estratégia de negócio;
- quais sistemas fazem parte do ecossistema;
- o que já foi implementado;
- onde estão os riscos;
- quais regras precisam ser respeitadas;
- quais próximos passos fazem sentido;
- como evitar retrabalho e alterações destrutivas.

Este relatório deve ser tratado como **documento de alinhamento técnico e estratégico**.

---

## 2. Visão geral do ecossistema

A **Smart Control Brasil** está evoluindo de uma empresa focada em manutenção, automação e soluções técnicas para um ecossistema digital com IA, CRM, marketplace B2B, atendimento inteligente, robótica, conteúdo técnico, automações comerciais e produtos digitais.

O núcleo tecnológico é o **Smart360**, um sistema Django que centraliza:

- site institucional;
- captação de leads;
- atendimento com IA pela LÍVIA;
- CRM / Growth Engine;
- marketplace B2B;
- base de conhecimento;
- portal de cliente;
- automações;
- integração futura com WhatsApp, n8n, Google Drive, Gemini e ferramentas de IA.

A estratégia é construir uma plataforma que venda e organize soluções de:

- automação industrial;
- manutenção e confiabilidade;
- robótica Xyron;
- IoT;
- engenharia embarcada;
- IA aplicada a negócios e indústria;
- serviços digitais;
- marketplaces especializados;
- conteúdo e SEO;
- automações comerciais.

---

## 3. Direção estratégica

A Smart Control Brasil não deve ser posicionada apenas como empresa de manutenção.

O posicionamento correto é:

> **Automação para máquinas mais produtivas e confiáveis.**

A manutenção existe, mas como parte de uma estratégia maior de engenharia, confiabilidade, automação e inovação.

### 3.1. Pilares principais

1. **Automação industrial**
   - CLP;
   - IHM;
   - inversores;
   - servos;
   - redes industriais;
   - retrofit;
   - integração de máquinas.

2. **Manutenção técnica e confiabilidade**
   - diagnóstico;
   - análise de falhas;
   - MTBF;
   - MTTR;
   - FMEA;
   - TPM;
   - plano de manutenção;
   - melhoria de disponibilidade.

3. **Robótica**
   - parceria Xyron Robotics;
   - robôs comerciais, educacionais, recepção, limpeza e segurança;
   - integração técnica e comercial.

4. **IA e automação digital**
   - LÍVIA como assistente comercial/técnica;
   - RAG;
   - atendimento consultivo;
   - qualificação de leads;
   - integração futura com WhatsApp;
   - n8n para automação comercial.

5. **Produtos digitais e marketplaces**
   - Smart360 como hub;
   - Caneca de Garagem;
   - marketplace B2B;
   - Smart Site Factory;
   - Smart Log;
   - Smart Analítico;
   - Smart English;
   - sistema de licitações.

---

## 4. Repositório e ambiente técnico principal

### 4.1. Projeto principal

O projeto principal é o **Smart360**, em Django.

Caminho local conhecido:

```bash
/home/marcelo/projetos/smart360
```

Caminho de deploy na VPS:

```bash
/home/smartcontrolbrasil.com.br/smart360_app
```

Branch principal usada:

```bash
main
```

Comandos comuns:

```bash
git status -sb
git log --oneline --decorate -8
.venv/bin/python manage.py check
.venv/bin/python -m pytest
.venv/bin/python manage.py collectstatic --noinput
```

### 4.2. Stack principal

- Backend: Django;
- Linguagem: Python 3.12;
- Banco: conforme ambiente do projeto;
- Frontend institucional: templates Django;
- Servidor: VPS HostGator;
- Painel: CyberPanel / OpenLiteSpeed;
- Aplicação: Gunicorn por trás de proxy;
- IA: OpenAI / Gemini;
- Automação: n8n;
- Armazenamento e organização: Google Drive / Gemini / Workspace.

---

## 5. Regras obrigatórias para Cursor, Codex, Gemini ou engenheiro

Antes de qualquer alteração:

1. Rodar:

```bash
git status -sb
```

2. Entender o estado atual da branch.

3. Não alterar `.env`, tokens, credenciais, chaves ou configurações sensíveis sem autorização explícita.

4. Não criar migrations sem necessidade real.

5. Não remover arquivos sem auditoria.

6. Não mudar CSS global sem entender impacto visual.

7. Evitar refatorações grandes sem necessidade.

8. Preferir commits pequenos, objetivos e rastreáveis.

9. Após alterações Django, rodar:

```bash
.venv/bin/python manage.py check
```

10. Quando possível, rodar testes relacionados ao app alterado.

11. Toda mudança importante deve gerar resumo técnico.

12. O projeto tem valor comercial real. Não tratar como playground.

---

## 6. Smart Control Brasil — site institucional

### 6.1. Objetivo

O site institucional deve vender autoridade técnica, automação, robótica e inovação.

Deve deixar claro que a empresa atua com:

- automação industrial;
- integração de sistemas;
- robótica;
- manutenção técnica;
- retrofit;
- engenharia embarcada;
- IA aplicada;
- soluções para empresas.

### 6.2. Páginas importantes

Páginas e rotas relevantes:

- Home;
- Sobre;
- Soluções;
- Projetos;
- Blog;
- Contato;
- `/engenharia-embarcada/`;
- página Mitsubishi;
- página Xyron Robotics;
- páginas de serviços técnicos;
- páginas de projetos.

### 6.3. Direção recente

Foi decidido remover o foco de **refrigeração** do site principal e migrar esse tema para outro domínio ou estrutura própria no futuro.

O site principal deve priorizar:

- automação;
- robótica;
- IA;
- engenharia;
- sistemas;
- tecnologia embarcada.

### 6.4. SEO

O SEO é estratégico. O site deve ser preparado para:

- Google;
- WhatsApp preview;
- LinkedIn preview;
- compartilhamento profissional;
- indexação por serviços;
- autoridade técnica regional/nacional.

Pendências típicas:

- OG Image oficial;
- sitemap;
- robots.txt;
- metatags por página;
- canônicos;
- schema markup;
- artigos técnicos;
- páginas de solução com palavras-chave específicas.

---

## 7. Smart360 — plataforma principal

### 7.1. O que é

O **Smart360** é o núcleo digital da operação Smart Control Brasil.

Ele deve funcionar como:

- CRM;
- portal comercial;
- motor de atendimento;
- marketplace B2B;
- base de conhecimento;
- camada de IA;
- central de propostas;
- central de automações;
- futuro portal de cliente.

### 7.2. Apps principais conhecidos

Apps citados no projeto:

- `growth_engine`;
- `livia_assistant`;
- `institutional`;
- `marketplace_ecom`;
- `visual_3d`;
- `automation`;
- possíveis módulos futuros para Smart Log, Smart Analítico, Smart English e licitações.

### 7.3. Princípio de arquitetura

O Smart360 deve crescer de forma modular.

Cada módulo deve ter responsabilidade clara:

- captação;
- atendimento;
- CRM;
- catálogo;
- propostas;
- automações;
- relatórios;
- conhecimento;
- portal.

Evitar misturar regra comercial dentro de template ou view sem necessidade.

---

## 8. LÍVIA — assistente de IA

### 8.1. Objetivo

A **LÍVIA** é a assistente de atendimento e qualificação da Smart Control Brasil.

Ela deve:

- atender visitantes do site;
- responder perguntas técnicas e comerciais;
- entender intenção;
- coletar dados de lead;
- qualificar oportunidades;
- enviar dados ao CRM;
- disparar notificação interna;
- futuramente atender pelo WhatsApp.

### 8.2. Função estratégica

A LÍVIA não é apenas chatbot. Ela é o primeiro estágio da operação comercial consultiva.

Deve atuar como:

- SDR digital;
- triagem técnica;
- assistente comercial;
- organizadora de demanda;
- alimentadora de CRM;
- ponte entre site, WhatsApp, e-mail e equipe humana.

### 8.3. Coleta de lead

Fluxo esperado:

1. entender a necessidade;
2. fazer pergunta técnica curta;
3. coletar nome;
4. coletar empresa;
5. coletar telefone/WhatsApp;
6. coletar e-mail;
7. coletar descrição do problema/interesse;
8. qualificar;
9. registrar no CRM;
10. disparar e-mail interno.

### 8.4. Regra importante

A lógica desejada é mais restritiva para envio de notificação.

Não disparar e-mail interno cedo demais apenas porque o telefone apareceu.

Direção correta:

- coletar dados mínimos;
- evitar falso positivo;
- só registrar/avisar quando o lead estiver minimamente qualificado;
- preservar a conversa técnica depois do registro.

### 8.5. Base de conhecimento

A LÍVIA usa conhecimento interno e RAG.

Fontes importantes:

- Smart Control Brasil;
- Xyron Robotics;
- Mitsubishi;
- automação;
- manutenção industrial;
- TPM;
- FMEA;
- MTBF;
- MTTR;
- robótica educacional;
- robôs de limpeza;
- robôs de recepção;
- engenharia embarcada;
- materiais acadêmicos;
- PDFs e catálogos carregados.

### 8.6. Produtos Xyron conhecidos pela LÍVIA

Produtos citados:

- LIRO / Littlebot;
- NeoBot;
- Buddy;
- HygiBot;
- OrbitBot / Patrol;
- Duno / Dune;
- WaiterBot;
- HostBot / ConnectBot;
- CareBot;
- MowerBot.

### 8.7. Futuro da LÍVIA

Próximos passos desejáveis:

- melhorar base RAG;
- levar para WhatsApp;
- integrar com n8n;
- criar handoff humano;
- criar painel de conversas;
- medir conversões;
- treinar respostas por segmento;
- separar respostas comerciais, técnicas e institucionais.

---

## 9. Growth Engine / CRM

### 9.1. Objetivo

O **Growth Engine** é o CRM e motor comercial do Smart360.

Ele deve registrar:

- leads;
- interações;
- oportunidades;
- propostas;
- origem do lead;
- status comercial;
- histórico.

### 9.2. Entidades conhecidas

Modelos/módulos citados:

- `Lead`;
- `LeadInteraction`;
- `CommercialProposal`;
- `CommercialOpportunity`;
- importação de prospects;
- origem `livia_assistant`;
- origem CSV;
- integração n8n.

### 9.3. Estados comerciais

Estados citados ou esperados:

- new;
- contacted;
- proposal;
- won;
- lost;
- qualified;
- pending handoff.

### 9.4. Deduplicação

Foi implementada deduplicação em fluxos de lead.

Critérios relevantes:

- e-mail + source;
- telefone + source;
- empresa + contato + source quando não há e-mail/telefone.

Isso evita duplicar leads vindos da LÍVIA, n8n ou importadores.

### 9.5. Importação de prospects

Existe/importou-se lógica para prospects, especialmente visando listas de empresas.

Direção:

- importar CSV;
- validar linhas;
- normalizar dados;
- ignorar linhas sem nome de empresa;
- guardar erros por linha;
- preparar oportunidades sem disparar contato automático.

---

## 10. Marketplace B2B

### 10.1. Objetivo

O marketplace B2B não deve funcionar como loja comum com checkout direto neste momento.

Ele deve funcionar como catálogo técnico e comercial.

Fluxo desejado:

1. cliente visualiza produto ou solução;
2. clica em solicitar orçamento;
3. vira lead;
4. lead entra no CRM;
5. equipe ou LÍVIA continua qualificação;
6. proposta é criada manualmente ou semi-automaticamente.

### 10.2. Categorias possíveis

- Robôs Xyron;
- automação industrial;
- componentes Mitsubishi;
- soluções de retrofit;
- serviços técnicos;
- consultorias;
- HVAC/refrigeração em domínio separado futuramente;
- kits e produtos digitais.

### 10.3. Cuidados

Não transformar em e-commerce B2C cedo demais.

O público principal é empresa, prefeitura, escola, indústria, condomínio, clínica, shopping, limpeza profissional e integradores.

---

## 11. Xyron Robotics

### 11.1. Papel no ecossistema

A Xyron é uma frente comercial estratégica.

A Smart Control Brasil atua como representante/integrador aprovado.

Produtos Xyron ajudam a abrir portas em:

- educação;
- limpeza;
- segurança;
- recepção;
- eventos;
- clínicas;
- supermercados;
- shoppings;
- condomínios;
- prefeituras;
- feiras tecnológicas.

### 11.2. Produtos prioritários

#### LIRO / Littlebot

Robô educacional e interativo.

Aplicações:

- escolas;
- APAEs;
- clínicas multidisciplinares;
- robótica pedagógica;
- inclusão;
- feiras de tecnologia.

#### NeoBot

Robô de recepção e atendimento.

Aplicações:

- empresas;
- eventos;
- recepção;
- demonstração tecnológica;
- atendimento com IA.

#### Buddy

Robô quadrúpede/cão robô.

Aplicações:

- demonstrações;
- segurança;
- inspeção;
- marketing;
- eventos;
- patrulhamento leve.

#### Duno / Dune / HygiBot

Robôs ligados a limpeza profissional.

Aplicações:

- empresas de limpeza;
- hospitais;
- shoppings;
- condomínios;
- escolas;
- supermercados.

#### Patrol / OrbitBot

Robôs ligados a patrulhamento e segurança.

Aplicações:

- rondas;
- visão noturna/térmica;
- monitoramento;
- segurança patrimonial.

#### HostBot / ConnectBot

Robôs de recepção, atendimento e presença digital.

Aplicações:

- eventos;
- recepção corporativa;
- atendimento multilíngue;
- demonstrações.

### 11.3. Estratégia comercial

Prioridade: vender e gerar caixa.

Canais:

- telefone;
- WhatsApp;
- e-mail;
- LinkedIn;
- visitas;
- demonstrações;
- conteúdo em vídeo;
- SEO;
- landing pages.

---

## 12. Smart Log

### 12.1. Visão

O **Smart Log** deve ser pensado como um módulo/logbook inteligente do ecossistema.

Ele pode registrar eventos técnicos, comerciais e operacionais.

Possíveis usos:

- histórico de atendimento;
- logs de manutenção;
- registros de falha;
- histórico de conversas;
- histórico de ações dos agentes de IA;
- auditoria operacional;
- trilha de decisões;
- acompanhamento de chamados.

### 12.2. Papel estratégico

O Smart Log pode virar o “diário de bordo” da operação.

Nada pior que projeto crescendo e ninguém saber quem mexeu em quê. Smart Log existe para evitar esse samba do commit doido.

### 12.3. Funcionalidades futuras

- registro automático de eventos;
- filtros por cliente, ativo, lead, proposta ou módulo;
- tags;
- severidade;
- vínculo com CRM;
- vínculo com chamados;
- exportação PDF;
- painel de auditoria;
- integração com IA para resumir eventos.

---

## 13. Smart Analítico

### 13.1. Visão

O **Smart Analítico** deve ser o módulo de inteligência de dados.

Objetivo:

- transformar dados do Smart360 em indicadores;
- apoiar decisão comercial;
- apoiar manutenção;
- medir conversão;
- medir eficiência de atendimento;
- medir canais;
- criar dashboards.

### 13.2. Indicadores possíveis

Comerciais:

- leads por origem;
- taxa de conversão;
- tempo até primeiro contato;
- oportunidades abertas;
- propostas enviadas;
- propostas ganhas/perdidas;
- ticket médio;
- produtos mais consultados.

LÍVIA:

- conversas iniciadas;
- conversas qualificadas;
- dados faltantes;
- dúvidas frequentes;
- intenção por segmento;
- taxa de handoff.

Manutenção/serviços:

- MTBF;
- MTTR;
- reincidência;
- chamados por cliente;
- criticidade;
- tempo de atendimento;
- tipo de falha.

Marketplace:

- produtos mais vistos;
- solicitações de orçamento;
- categorias mais buscadas;
- abandono de contato.

### 13.3. Futuro

Pode evoluir para:

- dashboards internos;
- relatórios automáticos;
- análise preditiva;
- recomendação comercial;
- priorização de leads;
- inteligência de manutenção;
- análise de funil.

---

## 14. Smart English

### 14.1. Visão

O **Smart English** é uma frente de apoio ao desenvolvimento profissional e comercial.

Objetivo inicial:

- ajudar Marcelo e equipe com inglês técnico;
- preparar comunicação internacional;
- melhorar leitura de documentação;
- apoiar contato com fornecedores;
- preparar apresentações;
- destravar oportunidades internacionais.

### 14.2. Aplicações

- inglês para engenharia;
- inglês para automação;
- inglês para manutenção;
- inglês para vendas técnicas;
- inglês para reuniões;
- inglês para documentação;
- respostas profissionais para fornecedores;
- treinamento pessoal.

### 14.3. Futuro

Pode virar produto interno ou externo:

- curso técnico;
- microaulas;
- flashcards;
- assistente de inglês;
- trilhas por área;
- prática com IA;
- inglês para automação e robótica.

---

## 15. Smart Site Factory

### 15.1. Visão

O **Smart Site Factory** é uma possível fábrica de sites e landing pages.

Objetivo:

- criar sites rápidos para projetos próprios;
- criar landing pages para produtos Xyron;
- criar páginas de captação;
- criar sites para clientes;
- reaproveitar templates;
- integrar com CRM e LÍVIA.

### 15.2. Aplicações

- landing page de robôs de limpeza;
- landing page LIRO para escolas;
- landing page de automação industrial;
- landing page de manutenção;
- landing page para licitações;
- sites de nicho;
- sites para parceiros.

### 15.3. Regras

Cada site/página deve já nascer com:

- SEO básico;
- CTA claro;
- formulário;
- integração com CRM;
- WhatsApp;
- OG Image;
- responsividade;
- tracking futuro.

---

## 16. Caneca de Garagem

### 16.1. Visão

O **Caneca de Garagem** é um marketplace/projeto paralelo voltado a produtos personalizados, especialmente canecas e itens POD.

Domínio conhecido:

```text
canecadegaragem.com.br
```

### 16.2. Conceito

Cliente cria ou escolhe arte. Produtor local imprime.

Possíveis produtos:

- caneca;
- long drink;
- chopp;
- boné;
- chinelo;
- azulejo;
- baldinho;
- produtos personalizados.

### 16.3. Módulo visual

Existe ideia/protótipo de editor visual usando recursos como:

- Three.js;
- Fabric.js;
- pré-visualização 2D/3D;
- upload de imagem;
- aplicação de arte no produto.

### 16.4. Mascotes

Mascotes citados:

- Ziggy Prisma;
- Polly Paris.

### 16.5. Estratégia

Caneca de Garagem pode funcionar como laboratório de:

- marketplace;
- editor visual;
- geração de artes com IA;
- funil B2C;
- impressão sob demanda;
- SEO de nicho;
- automação de pedidos.

Não misturar demais com Smart Control Brasil, pois os públicos são diferentes.

---

## 17. Sistema de Licitações

### 17.1. Visão

Existe intenção de criar um sistema interno para operar oportunidades de licitação.

Objetivo:

- localizar compras públicas;
- organizar oportunidades;
- comparar editais;
- apoiar montagem de proposta;
- monitorar robótica, educação, automação e tecnologia;
- atuar como consultoria/intermediação.

### 17.2. Caso Mirassol

Oportunidade conhecida:

- município de Mirassol;
- professor de robótica;
- interesse em LIRO / Littlebot;
- foco em oficina de robótica para 4º e 5º anos;
- prefeitura exige licitação;
- possibilidade de edital direcionado por especificação técnica;
- necessidade de três orçamentos;
- feira tecnológica anual como motivador.

### 17.3. Futuro do módulo

Funcionalidades possíveis:

- cadastro de oportunidades;
- importação de editais;
- leitura automática de PDF;
- classificação por segmento;
- alerta de prazos;
- checklist documental;
- cadastro de concorrentes;
- histórico de preços;
- geração de relatório;
- IA para resumo de edital.

---

## 18. n8n

### 18.1. Objetivo

O n8n entra como camada de automação comercial e operacional.

Usos previstos:

- buscar contatos;
- organizar listas;
- disparar fluxos;
- integrar formulários;
- receber leads;
- enviar dados ao Smart360;
- automatizar follow-up;
- integrar WhatsApp/e-mail futuramente.

### 18.2. Ambiente

Subdomínio conhecido:

```text
automacao.smartcontrolbrasil.com.br
```

Rodando em VPS com Docker Compose.

Pontos já tratados:

- autenticação básica;
- SSL;
- push backend;
- websocket/SSE;
- integração com endpoint do Smart360;
- webhook inbound para leads.

### 18.3. Cuidado

Houve dificuldade com conexão, OpenLiteSpeed/CyberPanel e proxy.

Evitar ficar rodando em círculos no n8n quando o gargalo for infraestrutura.

Priorizar automações simples e úteis antes de fluxos complexos.

---

## 19. Google Drive / Gemini / Workspace

### 19.1. Papel estratégico

Google/Gemini entra como apoio ao ecossistema:

- armazenamento de 5 TB;
- organização documental;
- base de conhecimento;
- SEO;
- vídeos;
- documentos;
- planilhas;
- integração com Gmail;
- integração com Agenda;
- apoio criativo;
- apoio em pesquisa.

### 19.2. Pasta raiz

Pasta conhecida:

```text
SMART CONTROL BRASIL - ECOSSISTEMA
```

Subpastas citadas:

```text
01_SMART360
02_LIVIA_IA
05_XYRON_ROBOTICS
20_AGENTES_IA_CURSOR_GEMINI
99_ARQUIVO_BRUTO_A_CLASSIFICAR
```

### 19.3. Arquivos relevantes

Arquivos já localizados/esperados:

```text
00_RELATORIO_GERAL_SMART360.md
README.md
2026-06-16_CONTROLE_AGENTES_CURSOR_GEMINI.md
09_AUDITORIA_FRONTEND_INDEX_CSS.md
```

Também há pasta:

```text
06_RELATORIOS_DE_AUDITORIA
```

### 19.4. Estratégia

Quando Cursor/Codex estiverem limitados, focar em:

- SEO;
- organização documental;
- conteúdo;
- vídeos;
- Google Drive;
- base RAG;
- documentação;
- prompts;
- análise de mercado.

---

## 20. Infraestrutura VPS / domínio / e-mail

### 20.1. Domínios

Domínios conhecidos:

```text
smartcontrolbrasil.com.br
www.smartcontrolbrasil.com.br
automacao.smartcontrolbrasil.com.br
canecadegaragem.com.br
```

### 20.2. VPS

Ambiente:

- HostGator VPS;
- CyberPanel;
- OpenLiteSpeed;
- Gunicorn;
- Django;
- SSL Let's Encrypt.

### 20.3. E-mail

E-mails citados:

```text
contato@smartcontrolbrasil.com.br
engenharia@smartcontrolbrasil.com.br
robotica@smartcontrolbrasil.com.br
comercial@mcautomation.com.br
```

### 20.4. Problema conhecido

Houve problema de blacklist/Spamhaus envolvendo IP da VPS e envio para Outlook/Microsoft.

Atenção:

- não usar envio massivo direto da VPS;
- preferir provedor transacional no futuro;
- cuidar SPF/DKIM/DMARC;
- evitar automação comercial agressiva por e-mail;
- e-mail frio deve ser feito com muito cuidado.

---

## 21. Atlas / importador de prospects

### 21.1. Visão

Existe frente de importação de prospects, chamada internamente de **Atlas** (agente de inteligência comercial).

Objetivo:

- importar listas CSV;
- gerar oportunidades comerciais;
- estruturar dados;
- preparar outreach futuro;
- não enviar e-mail automático no primeiro momento.

### 21.2. Campos e regras citadas

Campos de auditoria:

- contadores;
- erros;
- status;
- origem;
- linhas válidas/inválidas.

Campos de outreach em oportunidade:

- canal;
- e-mail remetente;
- domínio;
- status;
- notas.

Conta/domínio preparado:

```text
comercial@mcautomation.com.br
mcautomation.com.br
```

Regra importante:

- sem envio automático por padrão.

---

## 22. Conteúdo e marketing

### 22.1. Estratégia geral

A Smart Control Brasil precisa gerar conteúdo para:

- autoridade;
- SEO;
- vendas;
- robótica;
- automação;
- manutenção;
- educação;
- limpeza;
- segurança;
- IA industrial.

### 22.2. Conteúdos prioritários

Temas fortes:

- robôs de limpeza para empresas;
- LIRO para escolas e APAEs;
- Buddy para segurança e demonstração;
- NeoBot para recepção;
- automação para reduzir paradas;
- FMEA explicado;
- MTBF e MTTR;
- retrofit de máquinas;
- CLP/IHM;
- engenharia embarcada;
- IA no atendimento comercial;
- n8n para automação;
- Smart360 como plataforma.

### 22.3. Vídeos

Ferramentas e ideias citadas:

- Veo;
- CapCut;
- Canva;
- Gemini;
- Flow;
- imagens animadas;
- família de robôs Xyron em estilo mascote/anime.

Objetivo:

- criar vídeos curtos;
- divulgar robôs;
- vender soluções;
- alimentar Facebook, Instagram, LinkedIn e WhatsApp.

---

## 23. Estado atual resumido

### 23.1. O que já está andando

- Site institucional ativo;
- Smart360 em Django;
- LÍVIA em evolução;
- CRM recebendo leads;
- notificação interna por e-mail funcionando em cenários testados;
- integração n8n iniciada;
- Google Drive/Gemini entrando como apoio;
- Xyron como frente comercial prioritária;
- páginas institucionais sendo melhoradas;
- SEO começando a ser estruturado;
- RAG da LÍVIA em expansão;
- materiais Xyron carregados;
- conteúdos acadêmicos e técnicos sendo usados como base.

### 23.2. O que ainda precisa cuidado

- evitar disparo prematuro de lead;
- organizar documentação no Drive;
- consolidar CSS e templates;
- melhorar SEO;
- melhorar UX da home;
- estruturar funil comercial;
- integrar WhatsApp;
- estabilizar n8n;
- evitar e-mail frio pela VPS;
- criar rotina de auditoria;
- separar bem domínios/projetos;
- não deixar o projeto virar um polvo sem cérebro central.

---

## 24. Backlog estratégico

### 24.1. Curto prazo

1. Consolidar documentação do ecossistema.
2. Criar/atualizar README principal.
3. Organizar pasta Drive.
4. Finalizar página principal para não parecer inacabada.
5. Reforçar SEO básico.
6. Melhorar fluxo da LÍVIA.
7. Validar lógica AND para lead qualificado.
8. Criar landing pages Xyron prioritárias.
9. Criar lista controlada de prospects.
10. Criar rotina de follow-up manual/semi-automático.

### 24.2. Médio prazo

1. LÍVIA no WhatsApp.
2. Dashboard comercial.
3. Smart Analítico MVP.
4. Smart Log MVP.
5. Portal do cliente.
6. Marketplace B2B mais robusto.
7. Sistema de licitações MVP.
8. Smart Site Factory.
9. Conteúdo SEO recorrente.
10. Automação n8n com segurança.

### 24.3. Longo prazo

1. Plataforma comercial inteligente.
2. IA treinada por histórico real.
3. RAG robusto por área.
4. Múltiplos domínios especializados.
5. Rede de representantes/parceiros.
6. Catálogo B2B com preço por perfil.
7. Portal de clientes e representantes.
8. Sistema de propostas semi-automático.
9. Treinamento técnico/comercial com IA.
10. Ecossistema vendável como SaaS/serviço.

---

## 25. Prompt recomendado para o Cursor / engenheiro

Use este prompt antes de pedir alterações:

```text
Você está atuando no projeto Smart360 / Smart Control Brasil.

Antes de alterar qualquer arquivo, leia o relatório:
00_RELATORIO_GERAL_ECOSSISTEMA_CURSOR_ENG.md

Regras:
- Não altere .env, tokens ou credenciais.
- Não crie migrations sem necessidade real.
- Não remova arquivos sem auditoria.
- Não faça refatoração grande sem explicar.
- Preserve o posicionamento estratégico da Smart Control Brasil: automação, robótica, IA, manutenção técnica e confiabilidade.
- Rode git status -sb antes de propor mudanças.
- Rode manage.py check após alterações Django.
- Prefira commits pequenos e rastreáveis.
- Ao final, entregue resumo com arquivos alterados, testes executados e riscos.
```

---

## 26. Organização sugerida no Drive

Sugestão de estrutura:

```text
SMART CONTROL BRASIL - ECOSSISTEMA/
├── 00_GOVERNANCA_E_RELATORIOS/
│   ├── 00_RELATORIO_GERAL_ECOSSISTEMA_CURSOR_ENG.md
│   ├── 01_ROADMAP_GERAL.md
│   ├── 02_DECISOES_ESTRATEGICAS.md
│   └── 03_REGRAS_PARA_AGENTES_IA.md
├── 01_SMART360/
│   ├── arquitetura/
│   ├── deploy/
│   ├── backend/
│   ├── frontend/
│   ├── testes/
│   └── auditorias/
├── 02_LIVIA_IA/
│   ├── base_conhecimento/
│   ├── prompts/
│   ├── rag/
│   ├── logs/
│   └── testes/
├── 03_SMART_CONTROL_BRASIL_SITE/
├── 04_XYRON_ROBOTICS/
├── 05_MARKETPLACE_B2B/
├── 06_SMART_LOG/
├── 07_SMART_ANALITICO/
├── 08_SMART_ENGLISH/
├── 09_SMART_SITE_FACTORY/
├── 10_CANECA_DE_GARAGEM/
├── 11_LICITACOES/
├── 12_N8N_AUTOMACOES/
├── 13_SEO_MARKETING_CONTEUDO/
├── 20_AGENTES_IA_CURSOR_GEMINI/
└── 99_ARQUIVO_BRUTO_A_CLASSIFICAR/
```

---

## 27. Observações finais para o engenheiro

Este projeto tem várias frentes, mas todas precisam obedecer a uma lógica central:

> captar oportunidade, organizar informação, qualificar com IA, gerar proposta, vender solução e aprender com o histórico.

A tentação será sair criando módulo para todo lado. Não faça isso.

Prioridade técnica:

1. estabilidade;
2. clareza;
3. rastreabilidade;
4. documentação;
5. integração;
6. venda;
7. automação.

Prioridade comercial:

1. Xyron;
2. automação industrial;
3. manutenção/confiabilidade;
4. IA comercial;
5. marketplace B2B;
6. licitações;
7. conteúdo e SEO.

Se houver dúvida entre fazer algo bonito e fazer algo que vende, faça primeiro o que vende — mas sem quebrar a casa.

---

## 28. Resumo executivo de uma página

A Smart Control Brasil está construindo um ecossistema técnico-comercial chamado Smart360.

O Smart360 é uma plataforma Django que centraliza site institucional, CRM, assistente de IA LÍVIA, marketplace B2B, automações, base de conhecimento, robótica Xyron, atendimento comercial e futuras ferramentas analíticas.

A LÍVIA é a assistente de IA responsável por atender visitantes, responder perguntas técnicas, qualificar leads e alimentar o CRM. Ela deve evoluir para WhatsApp e usar RAG com materiais técnicos, catálogos Xyron, conteúdos de automação, manutenção, TPM, FMEA, MTBF e MTTR.

A frente Xyron Robotics é prioridade comercial para gerar caixa, com robôs como LIRO, NeoBot, Buddy, Duno/HygiBot, Orbit/Patrol, Host/ConnectBot e outros.

O site Smart Control Brasil deve focar automação, robótica, IA, engenharia embarcada e confiabilidade, deixando refrigeração para estrutura separada.

O ecossistema também inclui projetos/futuras frentes: Smart Log, Smart Analítico, Smart English, Smart Site Factory, Caneca de Garagem, marketplace B2B e sistema de licitações.

A infraestrutura usa VPS HostGator, CyberPanel/OpenLiteSpeed, Django/Gunicorn, n8n, Google Drive/Gemini e integrações com OpenAI.

O engenheiro ou agente deve preservar governança, evitar alterações destrutivas, rodar testes, documentar mudanças e sempre lembrar que o objetivo final é transformar engenharia, IA e robótica em venda organizada e escalável.

---
