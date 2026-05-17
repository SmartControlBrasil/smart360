COMPOSE ?= docker compose
COMPOSE_FILE ?= deployment/compose/docker-compose.dev.yml

.PHONY: build up down logs ps migrate shell createsuperuser bootstrap test worker beat

build:
	$(COMPOSE) -f $(COMPOSE_FILE) build

up:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build

down:
	$(COMPOSE) -f $(COMPOSE_FILE) down

logs:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f --tail=200

ps:
	$(COMPOSE) -f $(COMPOSE_FILE) ps

migrate:
	$(COMPOSE) -f $(COMPOSE_FILE) exec web python manage.py migrate

shell:
	$(COMPOSE) -f $(COMPOSE_FILE) exec web python manage.py shell

createsuperuser:
	$(COMPOSE) -f $(COMPOSE_FILE) exec web python manage.py createsuperuser

bootstrap:
	$(COMPOSE) -f $(COMPOSE_FILE) exec web python manage.py bootstrap_smart360 --demo-password admin123!

test:
	$(COMPOSE) -f $(COMPOSE_FILE) exec web pytest

worker:
	$(COMPOSE) -f $(COMPOSE_FILE) exec worker sh

beat:
	$(COMPOSE) -f $(COMPOSE_FILE) exec beat sh
