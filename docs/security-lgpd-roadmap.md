# Roadmap de Segurança & LGPD - Smart360

Status: base inicial documental e técnica. Este documento não contém secrets, tokens, credenciais, dumps ou dados pessoais reais.

## 1. Escopo de Dados Pessoais Tratados

O Smart360 trata dados pessoais e dados corporativos em múltiplos módulos. O inventário inicial abaixo deve ser refinado por finalidade, base legal, prazo de retenção e operador/controlador em cada contrato.

| Área | Dados tratados | Finalidade principal | Observações LGPD |
| --- | --- | --- | --- |
| Site institucional e formulários | nome, e-mail, telefone, empresa, cidade, mensagem, interesse comercial | atendimento comercial, prospecção e relacionamento | exige aviso de privacidade e registro de consentimento/base legal quando aplicável |
| Lívia Assistente | mensagens do chat, intenção comercial/técnica, dados de lead capturados, histórico de conversa | atendimento automatizado, triagem comercial e suporte inicial | alto risco de coleta excessiva; precisa minimização, aviso claro e retenção definida |
| Portal do Cliente `/portal/` | nome/e-mail do usuário, empresa, unidade/site, chamados, descrições, ativos, visitas | abertura e acompanhamento de chamados | dados devem ficar isolados por empresa/unidade; descrições podem conter dados pessoais livres |
| Admin Shell e operação técnica | usuários internos, técnicos, clientes, OS, agenda, execução, assinaturas, evidências, logs | gestão operacional e auditoria | exige controle de acesso forte e trilha de auditoria |
| Growth Engine e Atlas | leads, oportunidades, propostas, origem, histórico comercial | prospecção, vendas e automação comercial | risco de enriquecimento/perfilamento; revisar origem e base legal |
| Agentes de IA | recomendações, propostas, flags, runs, contexto operacional, payloads | apoio à decisão, priorização e automação assistida | precisa governança de input/output, explicabilidade, aprovação humana e isolamento por tenant |
| APIs e integrações | payloads operacionais, leads n8n, dados públicos/privados conforme endpoint | integração com serviços externos | exigir autenticação, assinatura ou allowlist nos endpoints sensíveis |
| Observabilidade | logs, request IDs, user IDs, company/site IDs, métricas e erros | auditoria, suporte e segurança | evitar conteúdo sensível nos logs; aplicar retenção e mascaramento |

## 2. Riscos Principais

| Prioridade | Risco | Impacto | Mitigação inicial |
| --- | --- | --- | --- |
| P0 | DEBUG ou permissões abertas em ambiente produtivo | exposição de stack traces, dados e rotas internas | garantir `DEBUG=False`, `ALLOWED_HOSTS` restrito e DRF autenticado em produção |
| P0 | Cookies sem flag secure fora de produção | sessão/CSRF expostos em HTTP | manter `SESSION_COOKIE_SECURE=True` e `CSRF_COOKIE_SECURE=True` em staging/prod |
| P0 | Endpoints públicos de integração sem autenticação forte | ingestão indevida, spam, fraude, vazamento indireto | revisar `/api/integrations/n8n/leads/`, `/livia/chat/`, Atlas ingest e webhooks |
| P0 | Quebra de isolamento multi-tenant | cliente vê dados de outra empresa/unidade | testes permanentes por Company/Site e uso consistente dos scope services |
| P1 | Coleta livre de dados pessoais em chat e descrição de chamado | excesso de dados, sensíveis acidentais | avisos de minimização, filtragem/mascaramento e retenção |
| P1 | Agentes de IA usando payloads sem sanitização | exposição de dados internos em recomendações/propostas | política de payload mínimo e aprovação humana para ações |
| P1 | Falta de política formal de retenção/exclusão | descumprimento de direitos LGPD | mapear tabelas e criar rotina de anonimização/exclusão |
| P2 | Headers de segurança incompletos | clickjacking/MIME/referrer/SSL hardening parcial | completar HSTS e referrer policy após validação de proxy/HTTPS |
| P2 | Logs com dados pessoais ou técnicos sensíveis | vazamento em observabilidade/backups | mascarar campos e restringir acesso aos logs |

## 3. Checklist LGPD

- [ ] Definir controlador, operadores e subprocessadores por produto/módulo.
- [ ] Publicar/atualizar Aviso de Privacidade para site, portal, Lívia e clientes B2B.
- [ ] Mapear base legal por finalidade: execução de contrato, legítimo interesse, consentimento ou obrigação legal.
- [ ] Registrar origem de leads e consentimento/base legal quando aplicável.
- [ ] Criar inventário de dados por tabela crítica: users, companies, memberships, service orders, Livia conversations/leads, Atlas/Growth, agent payloads.
- [ ] Definir retenção para conversas da Lívia, logs, OS, evidências, propostas e runs de agentes.
- [ ] Implementar processo de atendimento a direitos do titular: acesso, correção, exclusão, portabilidade e revogação.
- [ ] Definir política de anonimização/pseudonimização para ambientes de teste e análise.
- [ ] Criar matriz de incidentes: detecção, contenção, notificação interna, avaliação ANPD/titular.
- [ ] Revisar contratos com clientes e fornecedores de IA, e-mail, hospedagem, analytics e automação.

## 4. Auditoria Inicial de Settings Django

Arquivos auditados: `config/settings/base.py`, `config/settings/development.py`, `config/settings/staging.py`, `config/settings/production.py`, `config/settings/test.py`.

| Configuração | Status atual | Leitura de segurança | Ação recomendada |
| --- | --- | --- | --- |
| `DEBUG` | base via env default `False`; development `True`; staging/production/test `False` | adequado se ambiente produtivo usa settings production/staging | P0: monitorar deploy para impedir `DEBUG=True` fora de dev |
| `ALLOWED_HOSTS` | base via env default `localhost,127.0.0.1`; development `[*]`; test restrito | produção depende de env; dev aberto | P0: validar hosts reais em produção e staging |
| `CSRF_COOKIE_SECURE` | base env default `False`; staging/production default `True`; development `False` | correto para prod/staging, dev flexível | P0: manter `True` em HTTPS público |
| `SESSION_COOKIE_SECURE` | base env default `False`; staging/production default `True`; development `False` | correto para prod/staging | P0: manter `True` em HTTPS público |
| `SECURE_SSL_REDIRECT` | base env default `False`; staging/production default `True`; development `False` | depende de proxy/HTTPS | P0: validar `SECURE_PROXY_SSL_HEADER` no VPS/proxy antes de ativar universalmente |
| `SECURE_HSTS_SECONDS` | não localizado | faltante | P1: adicionar HSTS gradual após validar HTTPS, subdomínios e rollback; não ativar preload agora |
| `X_FRAME_OPTIONS` | `DENY` no base | presente | manter; revisar exceções caso haja embed controlado |
| `SECURE_CONTENT_TYPE_NOSNIFF` | `True` no base | presente | manter |
| `SECURE_REFERRER_POLICY` | não localizado | faltante | P1: definir política como `same-origin` ou `strict-origin-when-cross-origin` após validação |
| `SECURE_PROXY_SSL_HEADER` | presente com `HTTP_X_FORWARDED_PROTO=https` | bom para proxy reverso | validar Nginx/Traefik para não aceitar header externo indevido |
| `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES` | base `IsAuthenticated`; development sobrescreve para `AllowAny` | produção segura por padrão; dev é permissivo | P0: garantir que dev settings nunca sejam usados em produção |

Observação: não foi implementado HSTS preload nesta etapa, conforme critério de escopo. HSTS deve entrar em rollout controlado.

## 5. Rotas Públicas e Autenticadas

### Públicas intencionais

- Site institucional: rotas em `/` e páginas institucionais.
- `sitemap.xml`, `robots.txt`.
- Health checks: `/health/live/`, `/health/ready/`, `/health/`, `/health/details/`.
- Documentação/schema: `/api/schema/`, `/api/docs/`, `/api/redoc/` e variantes públicas. Avaliar se devem ficar públicas em produção.
- Auth/conta: `/login/`, `/logout/`, password reset e cadastro SaaS.
- Lívia widget: `/livia/chat/` é público e `csrf_exempt`; manter comportamento, mas classificar como P0 para rate limit, validação, retenção e aviso de privacidade.
- Marketplace e site Caneca: rotas públicas de catálogo/landing.
- Public API: `/api/public/v1/`.
- Webhooks/integrações: `/automation/webhooks/<slug>/`, `/api/integrations/n8n/leads/`, Atlas ingest. Exigem revisão de autenticação/assinatura.

### Autenticadas/sensíveis

- Admin Shell: `/ecossistema/`, `/app/...`, dashboards, Core Platform, Growth, AI Agents, operações, billing, observability.
- Portal do Cliente externo: `/portal/`, `/portal/chamados/`, `/portal/equipamentos/` exigem login e escopo por empresa/unidade.
- APIs internas `/api/v1/...`: default base é `IsAuthenticated`, com permissões específicas por módulo.
- APIs de IA/agentes: protegidas por permissões customizadas, exceto endpoints explicitamente custom/public que devem ser revisados.
- Django admin `/admin/`: restrito por `is_staff` padrão do Django.

## 6. Checklist Django/Security

- [x] `DEBUG=False` por padrão fora de development.
- [x] `X_FRAME_OPTIONS=DENY`.
- [x] `SECURE_CONTENT_TYPE_NOSNIFF=True`.
- [x] Cookies secure em production/staging por default.
- [x] SSL redirect em production/staging por default.
- [x] DRF base com `IsAuthenticated` por default.
- [x] Testes adicionados para autenticação em rotas internas críticas.
- [ ] Definir `SECURE_HSTS_SECONDS` com rollout gradual.
- [ ] Definir `SECURE_REFERRER_POLICY`.
- [ ] Confirmar `CSRF_TRUSTED_ORIGINS` para domínios reais HTTPS.
- [ ] Revisar exposição de `/api/docs/` e `/api/schema/` em produção.
- [ ] Padronizar rate limit para login, Lívia, webhooks e APIs de IA.
- [ ] Garantir que `development.py` nunca seja usado em deploy público.
- [ ] Revisar logs para não incluir conteúdo de chat, tokens, senhas, payloads sensíveis ou dados pessoais livres.

## 7. Checklist Infraestrutura VPS

- [ ] HTTPS obrigatório no proxy reverso, com renovação automática de certificados.
- [ ] Redirecionamento HTTP -> HTTPS no Nginx/Traefik, alinhado a `SECURE_SSL_REDIRECT`.
- [ ] Firewall permitindo apenas portas necessárias: 80/443 público, SSH restrito, banco/Redis privados.
- [ ] SSH com chave, sem senha, sem root direto quando possível.
- [ ] Backups criptografados e testados para banco, media e configurações.
- [ ] Rotação de secrets e uso de `.env` fora do repositório.
- [ ] Observabilidade com retenção definida e acesso restrito.
- [ ] Atualizações de SO, Python, dependências e imagens com rotina mensal ou emergencial.
- [ ] Monitoramento de disco, CPU, memória, filas Celery e Redis.
- [ ] Plano de resposta a incidente com responsáveis, contatos e procedimentos.

## 8. Checklist Segurança de Agentes de IA

- [ ] Classificar dados permitidos em prompt/contexto por agente.
- [ ] Impedir que payloads de agentes carreguem dados pessoais desnecessários.
- [ ] Manter aprovação humana para propostas com impacto operacional/comercial.
- [ ] Registrar `AgentRun`, recomendação, proposta, decisão e usuário aprovador.
- [ ] Separar contexto por tenant usando Company/Site em todas as consultas.
- [ ] Criar testes contra vazamento entre empresas em recommendations/proposals/flags.
- [ ] Sanitizar respostas da Lívia e copilots para não expor notas internas ou dados de outros tenants.
- [ ] Definir política de retenção para `AgentRun.input_context`, `output_summary`, payloads e logs.
- [ ] Revisar endpoints de ingestão Atlas/importação para autenticação, rate limit e origem confiável.
- [ ] Criar kill switch/feature flag para execução automática antes de elevar autonomia.

## 9. Plano de Implementação por Prioridade

### P0 - Antes de expandir agentes

1. Confirmar settings de produção: `DEBUG=False`, `ALLOWED_HOSTS` restrito, cookies secure e SSL redirect ativos.
2. Revisar endpoints públicos de ingestão: Lívia, n8n, automation webhooks, Atlas ingest.
3. Adicionar rate limiting e autenticação/assinatura para integrações sensíveis.
4. Garantir testes de isolamento multi-tenant para Portal, Admin Shell e AI Agents.
5. Documentar aviso de privacidade mínimo para Lívia/site/portal.
6. Proibir uso de settings development em deploy público.

### P1 - Hardening controlado

1. Definir `SECURE_REFERRER_POLICY`.
2. Ativar HSTS gradual sem preload após validação de HTTPS/subdomínios.
3. Revisar exposição de Swagger/Redoc/schema em produção.
4. Criar política de retenção e anonimização para chat, leads, logs e agent payloads.
5. Criar mascaramento de logs para dados pessoais livres.
6. Criar matriz de permissões por módulo sensível.

### P2 - Governança contínua

1. DPIA/relatório de impacto para Lívia, Atlas e agentes com perfilamento/recomendação.
2. Processo formal de atendimento ao titular.
3. Treinamento interno sobre LGPD, engenharia segura e uso de IA.
4. Auditoria periódica de dependências e vulnerabilidades.
5. Revisão contratual com operadores/subprocessadores.

## 10. Testes Adicionados Nesta Etapa

Arquivo: `apps/admin_shell/tests/test_security_authentication.py`.

Cobertura inicial:

- `/ecossistema/` exige autenticação.
- `/app/operations/health/` exige autenticação.
- `/app/core-platform/client-users/` exige autenticação.
- Dashboard interno da Lívia exige autenticação.
- `/portal/` exige autenticação.
- `/api/v1/users/me/` exige autenticação.
- `/api/v1/ai-agents/manual-run/` exige autenticação.

Resultado local do recorte: `7 passed`.

## 11. Observações de Não Escopo

- Não foi alterado comportamento da Lívia.
- Não foi criado novo app.
- Não foi ativado HSTS preload.
- Não foram adicionados secrets ou dados reais à documentação/testes.
- Este documento é base inicial; ainda não substitui política de privacidade, DPIA, contrato ou parecer jurídico.
