# SMART360 Core Platform

O Core Platform concentra os componentes compartilhados de identidade, organização, papéis e auditoria.

## Módulos

- `users`: usuário customizado com autenticação por e-mail.
- `companies`: empresas e vínculos multiempresa por membership.
- `roles`: catálogo inicial de papéis organizacionais.
- `audit`: trilha de auditoria para ações críticas.

## Fluxos iniciais

- Login por `email + password` retorna token DRF.
- Usuário autenticado pode consultar o próprio perfil.
- Usuário autenticado pode listar suas memberships.
- Usuário autenticado pode listar roles ativas.
- Usuário autenticado pode listar/criar companies.

## Endpoints

- `POST /api/v1/users/auth/login/`
- `GET /api/v1/users/me/`
- `GET /api/v1/users/memberships/`
- `GET /api/v1/companies/`
- `POST /api/v1/companies/`
- `GET /api/v1/roles/`
- `GET /health/`
- `GET /api/v1/`
