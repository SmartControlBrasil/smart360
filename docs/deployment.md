# Deployment

## Visao Geral

O SMART360 usa uma base operacional simples e repetivel para desenvolvimento, staging e producao:

- `web`: API Django
- `db`: PostgreSQL
- `redis`: cache e broker
- `worker`: Celery worker
- `beat`: Celery beat

Arquivos principais:

- `Dockerfile`
- `docker-compose.yml`
- `deployment/compose/docker-compose.dev.yml`
- `deployment/compose/docker-compose.staging.yml`
- `deployment/compose/docker-compose.prod.yml`
- `deployment/scripts/*.sh`
- `deployment/env/*.example`

## Servicos

### web

- espera PostgreSQL e Redis
- roda `migrate` e `collectstatic` quando habilitado
- em `development` usa `runserver`
- em `staging` e `production` usa `gunicorn`

### worker

- inicia `celery worker`
- compartilha a mesma imagem do `web`

### beat

- inicia `celery beat`
- prepara agendamentos do ecossistema

### db

- PostgreSQL 16 Alpine
- volume persistente dedicado

### redis

- Redis 7 Alpine
- configurado com `appendonly yes`

## Arquivos por Ambiente

- local padrao: `docker-compose.yml` com `.env`
- dev estruturado: `deployment/compose/docker-compose.dev.yml`
- staging: `deployment/compose/docker-compose.staging.yml`
- producao: `deployment/compose/docker-compose.prod.yml`

## Scripts Operacionais

- `deployment/scripts/wait-for-services.sh`
- `deployment/scripts/start-web.sh`
- `deployment/scripts/start-worker.sh`
- `deployment/scripts/start-beat.sh`
- `deployment/scripts/bootstrap-local.sh`
- `deployment/scripts/validate-compose.sh`

## Fluxo Seguro

Em staging/producao:

- nao habilitar `RUN_BOOTSTRAP_ON_START`
- preferir rodar `migrate` manualmente ou em pipeline
- manter secrets fora dos arquivos `.example`
