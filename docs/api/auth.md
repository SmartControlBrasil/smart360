# API Auth

## Fluxo principal

1. `POST /api/v1/auth/login/`
2. usar token retornado em `Authorization`
3. consultar perfil em `GET /api/v1/auth/me/`
4. renovar token em `POST /api/v1/auth/refresh/`
5. encerrar sessao em `POST /api/v1/auth/logout/`

## Recuperacao de senha

- `POST /api/v1/auth/password-reset/request/`
- `POST /api/v1/auth/password-reset/confirm/`

## Verificacao de email

- `POST /api/v1/auth/email-verification/request/`
- `POST /api/v1/auth/email-verification/confirm/`

## Sessoes e identidade

- `GET /api/v1/identity/sessions/`
- `POST /api/v1/identity/sessions/{id}/revoke/`
- `POST /api/v1/identity/sessions/revoke_others/`
- `GET|POST /api/v1/identity/invitations/`
- `POST /api/v1/identity/invitations/accept/`
- `GET /api/v1/identity/auth-events/`
- `GET|PATCH /api/v1/identity/onboarding/me/`

## Headers

Header recomendado:

```http
Authorization: Bearer <token>
```

Compatibilidade adicional:

```http
Authorization: Token <token>
```

