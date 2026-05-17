# Local Runbook

## Subir o Ambiente

Opcao simples:

```bash
cp .env.example .env
docker compose up --build
```

Opcao com compose dedicado:

```bash
docker compose -f deployment/compose/docker-compose.dev.yml up -d --build
```

## Migracoes

```bash
docker compose exec web python manage.py migrate
```

## Bootstrap de Demo

```bash
docker compose exec web python manage.py bootstrap_smart360 --demo-password admin123!
```

Ou:

```bash
sh deployment/scripts/bootstrap-local.sh
```

## Logs

```bash
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f beat
```

## Acessar Shell

```bash
docker compose exec web python manage.py shell
docker compose exec web bash
```

## Criar Superusuario

```bash
docker compose exec web python manage.py createsuperuser
```

## Parar

```bash
docker compose down
```

## Resetar Ambiente Local

```bash
docker compose down -v
rm -rf staticfiles media
```

## Validar Compose

```bash
sh deployment/scripts/validate-compose.sh
```

## Com Makefile

```bash
make up
make migrate
make bootstrap
make logs
make down
```
