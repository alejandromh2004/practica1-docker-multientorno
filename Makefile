# Variables con nombres de proyecto independientes (-p)
COMPOSE_DEV  = docker compose -p practica_dev --env-file .env.dev -f docker-compose.dev.yml
COMPOSE_PROD = docker compose -p practica_prod --env-file .env.prod -f docker-compose.prod.yml

.PHONY: help build up-dev dev up-prod prod up-all all down stop clean logs ps

# Ayuda por defecto
help:
	@echo "Comandos disponibles:"
	@echo "  make dev (o up-dev)   -> Levanta Desarrollo en http://localhost:5000"
	@echo "  make prod (o up-prod) -> Levanta Producción en http://localhost:5001"
	@echo "  make all (o up-all)   -> Levanta AMBOS entornos simultáneamente"
	@echo "  make down (o stop)    -> Detiene todos los contenedores"
	@echo "  make clean            -> Detiene y BORRA todos los volúmenes (reset de BDs)"
	@echo "  make ps               -> Lista todos los contenedores en ejecución"

# Construcción
build:
	$(COMPOSE_DEV) build
	$(COMPOSE_PROD) build

# Entorno de Desarrollo (puerto 5000)
up-dev:
	$(COMPOSE_DEV) up --build -d

dev: up-dev

# Entorno de Producción (puerto 5001)
up-prod:
	$(COMPOSE_PROD) up --build -d

prod: up-prod

# Levantar ambos entornos al mismo tiempo
up-all: up-dev up-prod

all: up-all

# Detener todos los contenedores
down:
	$(COMPOSE_DEV) down --remove-orphans
	$(COMPOSE_PROD) down --remove-orphans

stop: down

# Limpieza profunda de contenedores y volúmenes
clean:
	$(COMPOSE_DEV) down -v --remove-orphans
	$(COMPOSE_PROD) down -v --remove-orphans

# Ver contenedores activos
ps:
	docker ps


# Ejecuta el script demostración
demo:
	@bash demo.sh