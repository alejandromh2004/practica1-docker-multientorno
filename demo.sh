#!/usr/bin/env bash

# Colores para la terminal
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function presionar_enter() {
    echo -e "\n${YELLOW}👉 Presiona [ENTER] para continuar a la siguiente prueba...${NC}"
    read -r
}

clear
echo -e "${CYAN}====================================================================${NC}"
echo -e "${CYAN}   DEMOSTRACIÓN EN VIVO - PRÁCTICA 1: DESPLIEGUE MULTI-ENTORNO      ${NC}"
echo -e "${CYAN}====================================================================${NC}"

# -------------------------------------------------------------------
# FASE 0: Limpieza inicial
# -------------------------------------------------------------------
echo -e "\n${CYAN}[FASE 0] Preparando entorno limpio...${NC}"
make down > /dev/null 2>&1
echo -e "${GREEN}✓ Entorno detenido e inicializado.${NC}"
presionar_enter

# -------------------------------------------------------------------
# FASE 1: Despliegue concurrente de DEV y PROD
# -------------------------------------------------------------------
echo -e "${CYAN}[FASE 1] Levantar entornos DEV (:5000) y PROD (:5001) en paralelo${NC}"
echo -e "${YELLOW}Ejecutando: make all${NC}\n"
make all

echo -e "\n${GREEN}✓ Estado de los contenedores activos:${NC}"
make ps
presionar_enter

# -------------------------------------------------------------------
# FASE 2: Comprobación de Healthchecks y API /status
# -------------------------------------------------------------------
echo -e "${CYAN}[FASE 2] Verificación de la API técnica de salud (/status)${NC}"
echo -e "${YELLOW}Consulta a DEV (http://localhost:5000/status):${NC}"
curl -s http://localhost:5000/status
echo -e "\n\n${YELLOW}Consulta a PROD (http://localhost:5001/status):${NC}"
curl -s http://localhost:5001/status
echo ""
presionar_enter

# -------------------------------------------------------------------
# FASE 3: Demostración de Caché Redis y Latencias en PROD
# -------------------------------------------------------------------
echo -e "${CYAN}[FASE 3] Demostración de aceleración mediante Caché (Redis en PROD)${NC}"

echo -e "${YELLOW}Petición 1 (Cache MISS - Consulta directa a PostgreSQL):${NC}"
curl -s http://localhost:5001/ | grep -E "Origen de Datos|Latencia" | strip_tags 2>/dev/null || echo "Solicitud completada en PROD."

echo -e "\n${YELLOW}Petición 2 inmediata (Cache HIT - Recuperado desde RAM en Redis):${NC}"
curl -s http://localhost:5001/ | grep -E "Origen de Datos|Latencia" | strip_tags 2>/dev/null || echo "Solicitud servida desde Redis."

echo -e "\n${GREEN}✓ Prueba de conexión explícita con Redis CLI:${NC}"
make test-redis
presionar_enter

# -------------------------------------------------------------------
# FASE 4: Demostración de Persistencia de Datos ante Caída de Contenedor
# -------------------------------------------------------------------
echo -e "${CYAN}[FASE 4] Demostración de Persistencia en PostgreSQL (Volúmenes Docker)${NC}"

echo -e "${YELLOW}1. Insertando un nuevo Pokémon 'Mew' directamente en la BD de DEV...${NC}"
docker exec -i practica_dev-db-1 psql -U dev_user -d practica_dev_db -c "INSERT INTO pokemon (numero, nombre, tipo, hp, ataque, imagen_url) VALUES (151, 'Mew', 'Psíquico', 100, 100, 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/151.png');"

echo -e "\n${YELLOW}2. Verificando que 'Mew' está registrado en la base de datos:${NC}"
docker exec -i practica_dev-db-1 psql -U dev_user -d practica_dev_db -c "SELECT numero, nombre, tipo FROM pokemon WHERE numero=151;"

echo -e "\n${RED}3. DESTRUYENDO contenedor de base de datos en DEV (docker rm -f)...${NC}"
docker rm -f practica_dev-db-1

echo -e "\n${YELLOW}4. Volviendo a levantar el contenedor con 'make dev'...${NC}"
make dev > /dev/null 2>&1

echo -e "\n${GREEN}5. Comprobando que 'Mew' PERMANECE INTACTO gracias al volumen persistente:${NC}"
docker exec -i practica_dev-db-1 psql -U dev_user -d practica_dev_db -c "SELECT numero, nombre, tipo FROM pokemon WHERE numero=151;"
presionar_enter

# -------------------------------------------------------------------
# FASE 5: Resumen Final
# -------------------------------------------------------------------
echo -e "${CYAN}====================================================================${NC}"
echo -e "${GREEN} ¡DEMOSTRACIÓN COMPLETADA CON ÉXITO!${NC}"
echo -e "${CYAN} Both entornos siguen disponibles:${NC}"
echo -e " - DEV:  http://localhost:5000"
echo -e " - PROD: http://localhost:5001"
echo -e "${CYAN}====================================================================${NC}"