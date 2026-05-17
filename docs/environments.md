# Environments

## Development

- `DJANGO_SETTINGS_MODULE=config.settings.development`
- debug habilitado
- `runserver`
- email em console
- migracoes e `collectstatic` automaticos por padrao

Arquivo base:

- `deployment/env/.env.dev.example`

## Staging

- `DJANGO_SETTINGS_MODULE=config.settings.staging`
- debug desabilitado
- cookies seguros
- `gunicorn`
- mesmas integracoes estruturais de producao com menor rigor operacional

Arquivo base:

- `deployment/env/.env.staging.example`

## Production

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- debug desabilitado
- SSL redirect
- cookies seguros
- `gunicorn`
- bootstrap automatico desabilitado

Arquivo base:

- `deployment/env/.env.prod.example`

## Variaveis Principais

- `DJANGO_ENV`
- `DJANGO_SETTINGS_MODULE`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `POSTGRES_*`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `RUN_MIGRATIONS_ON_START`
- `RUN_COLLECTSTATIC_ON_START`
- `RUN_BOOTSTRAP_ON_START`
- `EMAIL_*`

## Recomendacao

- copiar os arquivos `.example` para `.env` real por ambiente
- nunca commitar secrets reais
- manter `development`, `staging` e `production` com valores explicitos
