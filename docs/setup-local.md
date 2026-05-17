# SMART360 Local Setup

## Pré-requisitos

- Docker
- Docker Compose Plugin

## Passos

1. Copie o arquivo de ambiente:

```bash
cp .env.example .env
```

2. Suba os serviços:

```bash
docker compose up --build
```

3. Acesse:

- API root: `http://localhost:8000/api/v1/`
- Healthcheck: `http://localhost:8000/health/`
- Swagger: `http://localhost:8000/api/docs/swagger/`

## Comandos úteis

Executar management command:

```bash
docker compose exec web python manage.py showmigrations
```

Abrir shell Django:

```bash
docker compose exec web python manage.py shell
```

Subir worker separadamente:

```bash
docker compose up celery
```
