# Identity and Auth

## Visao da camada de identidade

O `identity` centraliza autenticacao, sessoes, refresh token por rotacao, reset de senha, verificacao de email, convites de empresa, onboarding e trilha de eventos de autenticacao do SMART360.

## Fluxos de login e logout

1. `POST /api/v1/auth/login/`
2. autentica por email e senha
3. cria `UserSession` com token proprio
4. registra `AuthEventLog`
5. `POST /api/v1/auth/logout/` revoga a sessao atual

## Recuperacao de senha

1. `POST /api/v1/auth/password-reset/request/`
2. gera `PasswordResetRequest` com expiracao
3. opcionalmente dispara notificacao se existir template/canal configurado
4. `POST /api/v1/auth/password-reset/confirm/` aplica a troca e invalida o token

## Verificacao de e-mail

1. `POST /api/v1/auth/email-verification/request/`
2. gera `EmailVerificationRequest`
3. `POST /api/v1/auth/email-verification/confirm/`
4. marca `User.is_verified` e atualiza onboarding

## Convites

1. `POST /api/v1/identity/invitations/`
2. gera `CompanyInvitation`
3. `POST /api/v1/identity/invitations/accept/`
4. associa usuario existente ou cria um novo usuario e membership

## Sessoes

Suporta:

- listar sessoes ativas do usuario
- revogar uma sessao especifica
- revogar todas as outras sessoes
- rotacionar token da sessao atual via refresh

## Endpoints criados

- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/logout/`
- `POST /api/v1/auth/refresh/`
- `GET /api/v1/auth/me/`
- `POST /api/v1/auth/change-password/`
- `POST /api/v1/auth/password-reset/request/`
- `POST /api/v1/auth/password-reset/confirm/`
- `POST /api/v1/auth/email-verification/request/`
- `POST /api/v1/auth/email-verification/confirm/`
- `GET /api/v1/identity/sessions/`
- `POST /api/v1/identity/sessions/{id}/revoke/`
- `POST /api/v1/identity/sessions/revoke_others/`
- `GET|POST /api/v1/identity/invitations/`
- `GET /api/v1/identity/invitations/{id}/`
- `POST /api/v1/identity/invitations/accept/`
- `GET /api/v1/identity/auth-events/`
- `GET|PATCH /api/v1/identity/onboarding/me/`

## Integracoes

- `users`: usa o `User` customizado existente
- `companies` e `roles`: aceita convites e cria `Membership`
- `notification_center`: preparado para disparar mensagens de reset, verificacao e convite
- `audit`: registra eventos relevantes de identidade

## Proximos passos de seguranca

- MFA/TOTP e recovery codes
- rate limiting de login e reset
- device trust e score de risco
- invalidacao em massa de sessoes por politica
- notificacao de login suspeito
