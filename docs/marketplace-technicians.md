# Marketplace de Tecnicos

## Visao do modulo

O `marketplace_technicians` conecta empresas com demandas operacionais a tecnicos externos ou parceiros, mantendo o fluxo integrado ao Smart System. A demanda nasce no marketplace, passa por ofertas e aceite comercial, gera atribuicao e cria ou vincula uma `ServiceOrder` operacional.

## Entidades principais

- `TechnicianProfile`
- `TechnicianServiceRequest`
- `TechnicianServiceOffer`
- `TechnicianAssignment`
- `TechnicianReview`

Entidades auxiliares ja aproveitadas:

- `TechnicianSkill`
- `TechnicianSkillAssignment`
- `ServiceRegion`
- `TechnicianServiceRegion`
- `TechnicianAvailability`
- `TechnicianMatchingRecord`
- `TechnicianWorkReport`
- `TechnicianCompensationRecord`

## Motor de matching inteligente

O ranking persistido usa `TechnicianMatchingRecord` como cache do score calculado por request/tecnico. O score detalhado fica salvo para auditoria operacional e transparencia do algoritmo.

Fatores considerados na versao atual:

- especialidade tecnica
- distancia/regiao atendida
- avaliacao media
- experiencia previa
- disponibilidade atual
- tempo medio de resposta

Pesos da versao `v1`:

- `0.30` especialidade
- `0.25` distancia
- `0.20` avaliacao
- `0.15` experiencia
- `0.10` disponibilidade

Campos de breakdown persistidos:

- `match_score`
- `score_specialty`
- `score_distance`
- `score_rating`
- `score_experience`
- `score_availability`
- `score_response_time`
- `distance_km`
- `ranking_position`
- `scoring_version`
- `calculation_context`

## Fluxo operacional

1. Empresa cria `TechnicianServiceRequest`.
2. `TechnicianMatchingService.refresh_matches` calcula o ranking tecnico por especialidade, regiao, disponibilidade, reputacao, experiencia e tempo de resposta.
3. Tecnicos elegiveis enviam `TechnicianServiceOffer`.
4. Empresa aceita uma oferta.
5. O sistema cria `TechnicianAssignment`.
6. O assignment cria ou vincula uma `ServiceOrder` do Smart System.
7. O tecnico executa o servico.
8. A empresa registra `TechnicianReview`.

## Integracao com Smart System

- `TechnicianServiceRequest.related_asset`
- `TechnicianServiceRequest.related_site`
- `TechnicianServiceRequest.related_client`
- `TechnicianServiceRequest.related_service_order`

Ao aceitar uma oferta, `TechnicianAssignmentService.ensure_related_service_order` garante que exista uma OS operacional para o atendimento do marketplace.

## Regras de acesso

- usuario de empresa: cria request, enxerga requests/offers/assignments/reviews da propria empresa e aceita ofertas
- tecnico: enxerga oportunidades abertas, cria oferta no proprio perfil, executa apenas assignments proprios
- shell: integrado ao RBAC via dominios
  - `marketplace_dashboard.view`
  - `marketplace_requests.view|create|assign`
  - `marketplace_offers.view|create|manage`
  - `marketplace_matching.view|manage`
  - `marketplace_technicians.view|update`
  - `marketplace_assignments.view|execute|manage`
  - `marketplace_reviews.view|create|manage`

## Admin Shell

Rotas internas:

- `/app/marketplace/technicians/`
- `/app/marketplace/technicians/requests/`
- `/app/marketplace/technicians/matching/`
- `/app/marketplace/technicians/offers/`
- `/app/marketplace/technicians/profiles/`
- `/app/marketplace/technicians/profiles/<uuid>/`
- `/app/marketplace/technicians/assignments/`
- `/app/marketplace/technicians/reviews/`

Componentes reutilizaveis:

- `technician_card`
- `service_request_card`
- `offer_table`
- `technician_rating`
- `marketplace_dashboard_widget`
- `marketplace_match_table`

## APIs

API interna DRF:

- `GET|POST /api/v1/marketplace-technicians/service-requests/`
- `GET|POST /api/v1/marketplace-technicians/service-requests/{id}/matching/`
- `GET|POST /api/v1/marketplace-technicians/service-offers/`
- `GET /api/v1/marketplace-technicians/matching-records/`
- `POST /api/v1/marketplace-technicians/service-offers/{id}/accept/`
- `POST /api/v1/marketplace-technicians/service-offers/{id}/reject/`
- `POST /api/v1/marketplace-technicians/service-offers/{id}/withdraw/`
- `GET|POST /api/v1/marketplace-technicians/assignments/`
- `POST /api/v1/marketplace-technicians/assignments/{id}/start/`
- `POST /api/v1/marketplace-technicians/assignments/{id}/complete/`
- `GET|POST /api/v1/marketplace-technicians/reviews/`

API publica:

- `GET /api/public/v1/marketplace/technicians/`
- `GET|POST /api/public/v1/marketplace/service-requests/`
- `GET|POST /api/public/v1/marketplace/service-requests/{public_id}/matching/`
- `GET|POST /api/public/v1/marketplace/offers/`
- `POST /api/public/v1/marketplace/offers/{public_id}/accept/`
- `POST /api/public/v1/marketplace/offers/{public_id}/reject/`
- `POST /api/public/v1/marketplace/offers/{public_id}/withdraw/`
- `GET /api/public/v1/marketplace/assignments/`
- `POST /api/public/v1/marketplace/assignments/{public_id}/start/`
- `POST /api/public/v1/marketplace/assignments/{public_id}/complete/`
- `GET /api/public/v1/marketplace/reviews/`

## Como evoluir

- adicionar pesos configuraveis por categoria/regiao/SLA
- notificar automaticamente os tecnicos top-ranked
- recalcular ranking em eventos de perfil, disponibilidade e aceite
- cruzar agenda real e backlog para penalizacao mais precisa
- enriquecer experiencia por tipo de ativo, cliente e reincidencia
- adicionar disputa estruturada com ranking de ofertas e SLA
- integrar billing para comissao por assignment aceito/concluido
- evoluir disponibilidade para agenda real e bloqueio de capacidade
- adicionar notificacoes e webhooks de oportunidade
- criar payout e conciliacao financeira no billing
