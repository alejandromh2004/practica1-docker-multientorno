# Variables para simplificar los comandos de Compose
COMPOSE_DEV  = docker compose --env-file .env.dev -f docker-compose.dev.yml
COMPOSE_PROD = docker compose --env-file .env.prod -f docker-compose.prod.yml

.PHONY: help build up-dev dev up-prod prod down stop clean logs ps

# Comando por defecto: muestra la ayuda
help:
	@echo "Comandos disponibles:"
	@echo "  make up-dev (o make dev)   -> Levanta el entorno de Desarrollo (Flask + Postgres)"
	@echo "  make up-prod (o make prod) -> Levanta el entorno de Producción (Flask + Postgres + Redis)"
	@echo "  make down (o make stop)    -> Detiene los contenedores de ambos entornos"
	@echo "  make clean                 -> Detiene y BORRA volúmenes (reinicia la BD desde cero)"
	@echo "  make logs                  -> Muestra los logs en tiempo real"
	@echo "  make ps                    -> Muestra el estado de los contenedores activos"

# Construcción de imágenes
build:
	$(COMPOSE_DEV) build

# Entorno de Desarrollo (alias doble: make up-dev o make dev)
up-dev:
	$(COMPOSE_DEV) up --build -d

dev: up-dev

# Entorno de Producción (alias doble: make up-prod o make prod)
up-prod:
	$(COMPOSE_PROD) up --build -d

prod: up-prod

# Detener contenedores (apaga dev y prod por si acaso)
down:
	$(COMPOSE_DEV) down --remove-orphans
	$(COMPOSE_PROD) down --remove-orphans

stop: down

# Limpieza profunda: elimina también los volúmenes persistentes
clean:
	$(COMPOSE_DEV) down -v --remove-orphans
	$(COMPOSE_PROD) down -v --remove-orphans

# Ver logs de la aplicación
logs:
	$(COMPOSE_DEV) logs -f

# Ver contenedores en ejecución
ps:
	docker ps