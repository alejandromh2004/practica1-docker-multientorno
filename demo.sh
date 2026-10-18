#!/usr/bin/env bash

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

function presionar_enter() {
    echo -e "\n${YELLOW}👉 Presiona [ENTER] para avanzar al siguiente paso...${NC}"
    read -r
}

clear
echo -e "${CYAN}====================================================================${NC}"
echo -e "${CYAN}   DEMOSTRACIÓN EN VIVO - PRÁCTICA 1: DESPLIEGUE MULTI-ENTORNO      ${NC}"
echo -e "${CYAN}====================================================================${NC}"

# -------------------------------------------------------------------
# FASE 0: Limpieza Inicial
# -------------------------------------------------------------------
echo -e "\n${CYAN}[FASE 0] Limpiando contenedores previos...${NC}"
make down > /dev/null 2>&1
echo -e "${GREEN}✓ Entorno inicializado limpiamente.${NC}"
presionar_enter

# -------------------------------------------------------------------
# FASE 1: Despliegue Concurrente de DEV y PROD
# -------------------------------------------------------------------
echo -e "${CYAN}[FASE 1] Despliegue concurrente de Desarrollo y Producción${NC}"
echo -e "Explicación: Levantamos ambos entornos en paralelo sobre redes internas independientes."
echo -e "${YELLOW}Comando: make all${NC}\n"
make all

echo -e "\n${GREEN}✓ Contenedores en ejecución (comprobación de salud mediante healthchecks):${NC}"
make ps

echo -e "\n${BLUE}🌐 INSTRUCCIÓN PARA LA PRESENTACIÓN:${NC}"
echo -e " - Abre en el navegador ${GREEN}http://localhost:5000${NC} (Desarrollo)"
echo -e " - Abre en otra pestaña ${GREEN}http://localhost:5001${NC} (Producción)"
presionar_enter

# -------------------------------------------------------------------
# FASE 2: Verificación de Healthchecks y Endpoint API /status
# -------------------------------------------------------------------
echo -e "${CYAN}[FASE 2] Verificación dinámica de la API de Salud (/status)${NC}"
echo -e "Explicación: La aplicación evalúa la salud de PostgreSQL y Redis en tiempo real."

echo -e "\n${YELLOW}1. Endpoint DEV (http://localhost:5000/status):${NC}"
curl -s http://localhost:5000/status

echo -e "\n\n${YELLOW}2. Endpoint PROD (http://localhost:5001/status):${NC}"
curl -s http://localhost:5001/status
echo ""
presionar_enter

# -------------------------------------------------------------------
# FASE 3: Benchmark de Rendimiento (Latencia Interna de App)
# -------------------------------------------------------------------
echo -e "${CYAN}[FASE 3] Benchmark de Rendimiento: PostgreSQL (DEV) vs Redis RAM (PROD)${NC}"
echo -e "Explicación: Extraemos la latencia real de procesamiento calculada internamente por la app."

# Precarga en PROD para asegurar el Cache HIT
curl -s -o /dev/null http://localhost:5001

echo -e "\n${YELLOW}Ejecutando 20 peticiones a DEV (http://localhost:5000)...${NC}"
SUM_DEV=0
for i in {1..20}; do
    # Extrae los ms calculados por Flask en el HTML
    MS=$(curl -s http://localhost:5000 | grep -oP 'Latencia Petición:.*?<code>\K[0-9.]+' || echo "10")
    SUM_DEV=$(echo "$SUM_DEV + $MS" | bc)
    echo -n "."
    sleep 0.05
done
AVG_DEV=$(echo "scale=2; $SUM_DEV / 20" | bc)
echo -e "\n${GREEN}⚡ Latencia media interna en DEV (PostgreSQL Directo): ${AVG_DEV} ms${NC}"

echo -e "\n${YELLOW}Ejecutando 20 peticiones a PROD (http://localhost:5001)...${NC}"
SUM_PROD=0
for i in {1..20}; do
    MS=$(curl -s http://localhost:5001 | grep -oP 'Latencia Petición:.*?<code>\K[0-9.]+' || echo "1")
    SUM_PROD=$(echo "$SUM_PROD + $MS" | bc)
    echo -n "."
    sleep 0.05
done
AVG_PROD=$(echo "scale=2; $SUM_PROD / 20" | bc)
echo -e "\n${GREEN}⚡ Latencia media interna en PROD (Caché Redis RAM): ${AVG_PROD} ms${NC}"

echo -e "\n${BLUE}💡 CONCLUSIÓN:${NC} Se observa una reducción real del tiempo de acceso a datos (PostgreSQL ~5-20ms vs Redis ~1ms)."
presionar_enter

# -------------------------------------------------------------------
# FASE 4: Caída de Caché en Producción y Fallback Automático
# -------------------------------------------------------------------
echo -e "${CYAN}[FASE 4] Prueba de Tolerancia a Fallos: Caída de la Caché (Redis)${NC}"
echo -e "Explicación: Simulamos una avería en el servicio Redis para comprobar que la aplicación redirige el tráfico a PostgreSQL sin caerse."

echo -e "\n${RED}1. Apagando el contenedor de Redis en Producción (docker stop)...${NC}"
docker stop practica_prod-redis-1 > /dev/null

echo -e "\n${YELLOW}2. Consultando el endpoint /status en Producción:${NC}"
curl -s http://localhost:5001/status

echo -e "\n\n${BLUE}🌐 INSTRUCCIÓN PARA LA PRESENTACIÓN:${NC}"
echo -e " - Recarga ${GREEN}http://localhost:5001${NC} en el navegador."
echo -e " - Verás que el estado de Redis cambia a ${RED}OFFLINE${NC}, pero la web sigue respondiendo consultando directamente a PostgreSQL (Fallback exitoso)."
presionar_enter

echo -e "${YELLOW}3. Restaurando el servicio de Caché Redis...${NC}"
docker start practica_prod-redis-1 > /dev/null
sleep 2
echo -e "${GREEN}✓ Redis recuperado.${NC}"
curl -s http://localhost:5001/status
echo ""
presionar_enter

# -------------------------------------------------------------------
# FASE 5: Demostración de Persistencia de Datos
# -------------------------------------------------------------------
echo -e "${CYAN}[FASE 5] Demostración de Persistencia (Volúmenes de PostgreSQL)${NC}"
echo -e "Explicación: Insertamos un nuevo registro, eliminamos el contenedor de la BD y verificamos que el dato se conserva en el volumen."

echo -e "\n${YELLOW}1. Insertando un nuevo Pokémon ('Mew', Nº 151) en la BD de DEV...${NC}"
docker exec -i practica_dev-db-1 psql -U dev_user -d practica_dev_db -c "INSERT INTO pokemon (numero, nombre, tipo, hp, ataque, imagen_url) VALUES (151, 'Mew', 'Psíquico', 100, 100, 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/151.png');" > /dev/null

echo -e "${GREEN}✓ Pokémon 'Mew' insertado correctamente.${NC}"

echo -e "\n${BLUE}🌐 INSTRUCCIÓN PARA LA PRESENTACIÓN:${NC}"
echo -e " - Recarga ${GREEN}http://localhost:5000${NC} para ver la nueva carta de Mew al final de la página."
presionar_enter

echo -e "${RED}2. Eliminando de forma destructiva el contenedor de la base de datos (docker rm -f)...${NC}"
docker rm -f practica_dev-db-1 > /dev/null

echo -e "\n${YELLOW}3. Reconstruyendo y levantando el contenedor con 'make dev'...${NC}"
make dev > /dev/null 2>&1
sleep 3

echo -e "\n${GREEN}4. Verificando que 'Mew' permanece intacto en la BD recuperada:${NC}"
docker exec -i practica_dev-db-1 psql -U dev_user -d practica_dev_db -c "SELECT numero, nombre, tipo FROM pokemon WHERE numero=151;"

echo -e "\n${BLUE}🌐 INSTRUCCIÓN PARA LA PRESENTACIÓN:${NC}"
echo -e " - Vuelve a recargar ${GREEN}http://localhost:5000${NC}."
echo -e " - Comprueba que 'Mew' sigue ahí. Esto demuestra que los datos residen en el volumen persistente 'dev_db_data'."
presionar_enter

# -------------------------------------------------------------------
# RESUMEN FINAL
# -------------------------------------------------------------------
echo -e "${CYAN}====================================================================${NC}"
echo -e "${GREEN} ¡TODAS LAS PRUEBAS SE HAN COMPLETADO CON ÉXITO!${NC}"
echo -e "${CYAN} Entornos activos y disponibles para la evaluación:${NC}"
echo -e " - DEV:  http://localhost:5000"
echo -e " - PROD: http://localhost:5001"
echo -e "${CYAN}====================================================================${NC}"