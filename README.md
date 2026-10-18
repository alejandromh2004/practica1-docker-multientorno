# Práctica 1: Despliegue de Aplicaciones Multi-Entorno con Docker

**Asignatura:** Redes Avanzadas  
**Titulación:** Grado en Ingeniería Informática  
**Universidad:** Universitat de les Illes Balears (UIB)  

---

## 📋 Descripción del Proyecto

El objetivo de este proyecto es diseñar, orquestar y desplegar un servicio web completo basado en **Pokédex**, distribuido en contenedores Docker y diferenciado en dos entornos aislados:
* **Desarrollo (`DEV`):** Aplicación web (Flask) + Base de datos relacional (PostgreSQL).
* **Producción (`PROD`):** Aplicación web (Flask) + Base de datos relacional (PostgreSQL) + Servidor de caché en memoria (Redis).

El sistema demuestra la persistencia de datos mediante volúmenes, la orquestación multicontenedor mediante Docker Compose, el aislamiento de redes internas, la comprobación de salud activa (*healthchecks*) y el uso de caché para optimizar la latencia en lecturas.

---

## 🏛️ Arquitectura del Servicio

### Entorno de Desarrollo (DEV)
* **URL:** `http://localhost:5000`
* **Servicios:** `web` (Flask) y `db` (PostgreSQL 15).
* **Almacenamiento:** Volumen persistente `dev_db_data`.

```text
               Red Interna (practica_dev_network)
 ┌─────────────┐            ┌─────────────────────────┐
 │ Browser/Host│            │    Contenedor Web       │
 │ localhost   ├─(Port 5000)┼─►  practica_dev-web-1   │
 └─────────────┘            └────────────┬────────────┘
                                         │
                                         ▼
                            ┌─────────────────────────┐
                            │    Contenedor DB        │
                            │    practica_dev-db-1    │
                            └────────────┬────────────┘
                                         │
                                         ▼
                            ┌─────────────────────────┐
                            │  Volumen dev_db_data    │
                            └─────────────────────────┘
```

### Entorno de Producción (PROD)
* **URL:** `http://localhost:5001`
* **Servicios:** `web` (Flask), `db` (PostgreSQL 15) y `redis` (Redis 7).
* **Almacenamiento:** Volumen persistente `prod_db_data`.

```text
                     Red Interna (practica_prod_network)
 ┌─────────────┐            ┌─────────────────────────┐
 │ Browser/Host│            │    Contenedor Web       │
 │ localhost   ├─(Port 5001)┼─►  practica_prod-web-1  │
 └─────────────┘            └────┬────────────────┬───┘
                                 │                │
                        (Miss)   │                │ (Hit ⚡)
                                 ▼                ▼
                     ┌──────────────────┐  ┌─────────────────────┐
                     │  Contenedor DB   │  │  Contenedor Cache   │
                     │practica_prod-db-1│  │practica_prod-redis-1│
                     └─────────┬────────┘  └─────────────────────┘
                               │
                               ▼
                     ┌──────────────────┐
                     │Volumen prod_db...│
                     └──────────────────┘
```

---

## 🚀 Guía de Instalación y Ejecución

### Requisitos Previos
* Docker (Engine >= 20.10)
* Docker Compose (v2.x)
* GNU Make

### Configuración de Entornos (.env)
Nota para la evaluación:

Siguiendo las buenas prácticas de seguridad, los archivos de configuración real (.env.dev y .env.prod) están incluidos en .gitignore y no se versionan en GitHub. En el repositorio se proporciona la plantilla .env.example.

Para facilitar la corrección inmediata, la entrega comprimida (.zip) subida al Campus Digital incluye los archivos .env.dev y .env.prod preconfigurados para ejecutar make all directamente. Si se clona desde Git, bastará con copiar .env.example a .env.dev y .env.prod.

### Comandos del Makefile
El proyecto cuenta con tareas automatizadas mediante `Makefile`:

* **Levantar ambos entornos a la vez (DEV en :5000, PROD en :5001):**
  ```bash
  make all
  ```
* **Levantar entorno de Desarrollo:**
  ```bash
  make dev
  ```
* **Levantar entorno de Producción:**
  ```bash
  make prod
  ```
* **Probar conexiones a la Base de Datos y Caché:**
  ```bash
  make test-db-dev   # Comprueba pg_isready en DEV
  make test-db-prod  # Comprueba pg_isready en PROD
  make test-redis    # Comprueba ping en Redis (PROD)
  make test          # Consulta los endpoints /status de ambos entornos
  ```
* **Detener todos los contenedores:**
  ```bash
  make down
  ```
* **Resetear volúmenes (Limpieza profunda):**
  ```bash
  make clean
  ```

---

## 🩺 Explicación de los Healthchecks y Endpoint `/status`

### Configuración en Docker Compose
Cada servicio define una comprobación periódica de salud (*healthcheck*):
* **PostgreSQL:** Executa `pg_isready -U <USER> -d <DB_NAME>` cada 5 segundos.
* **Redis:** Ejecuta `redis-cli ping` cada 5 segundos.
* **Flask Web:** Lanza un script de verificación en Python llamando internamente a `http://localhost:5000/status`.

Los contenedores web utilizan la directiva `depends_on` con la condición `service_healthy`, garantizando que la aplicación web solo intente arrancar cuando la base de datos y la caché estén 100% listas para aceptar conexiones.

### Endpoint HTTP `/status`
La aplicación expone una API REST técnica en `/status` (o `/health`) que devuelve una respuesta JSON indicando el estado en tiempo real de los servicios dependientes:

```json
{
  "status": "healthy",
  "database": "healthy",
  "cache": "healthy"
}
```

Si alguno de los servicios cae (por ejemplo, al detener el contenedor de la base de datos mediante `docker stop`), la aplicación detecta la desconexión de forma dinámica en tiempo real y responde con código HTTP `503 Service Unavailable`.

---

## 🧪 Verificación de Resultados y Pruebas

### 1. Demostración de Persistencia de Datos
1. Se levanta el entorno con `make dev`.
2. A través del formulario web en `http://localhost:5000`, se registra un nuevo Pokémon (ejemplo: *Mewtwo*, Nº 150, Tipo *Psíquico*).
3. Se detienen y eliminan los contenedores mediante `make down`.
4. Se vuelve a iniciar el entorno con `make dev`.
5. Se verifica en el navegador que *Mewtwo* sigue presente. Los datos se mantienen gracias al volumen `dev_db_data` administrado por Docker.

### 2. Demostración de Optimización mediante Caché (Redis)
1. En producción (`http://localhost:5001`), la primera petición realiza la lectura sobre PostgreSQL. La interfaz indica `Estado de Caché: MISS` con una latencia de **12–20 ms**.
2. Al recargar la página inmediatamente después, la lectura se realiza desde la memoria RAM de Redis. La interfaz indica `Estado de Caché: HIT ⚡` con una latencia de **1–2 ms** (reducción >80% en tiempo de respuesta).
3. Al insertar un nuevo registro, la aplicación invalida la clave en Redis (`r.delete("cartas_pokemon")`), asegurando consistencia de datos en la siguiente lectura.

---

## 🔒 Seguridad e Higiene del Entorno

1. **Aislamiento de Red:** Solo la aplicación web expone su puerto hacia el host (`5000` en DEV / `5001` en PROD). La base de datos PostgreSQL y la caché Redis no exponen puertos al exterior y son accesibles únicamente desde la red virtual privada de Docker.
2. **Usuario sin privilegios de root:** El contenedor de Flask ejecuta la aplicación bajo un usuario dedicado sin privilegios (`USER appuser`) definido dentro del `Dockerfile`.
3. **Gestión de variables de entorno:** Ninguna contraseña ni credencial está integrada (*hardcodeada*) dentro del código fuente Python o en los archivos `docker-compose.yml`. Todo se inyecta mediante archivos `.env`.
   * *Nota académica:* Siguiendo las buenas prácticas, los archivos `.env` reales deben incluirse en `.gitignore`. Para facilitar la evaluación inmediata del profesor mediante `make all` sin exigir configuración manual previa, se incluyen `.env.dev` y `.env.prod` con credenciales ficticias de prueba en el repositorio.

---

## 🤖 Declaración de Uso de Herramientas de Inteligencia Artificial

Cumpliendo con los requisitos de citación y transparencia de la asignatura:

* **Herramienta y Versión:** ChatGPT / Google Gemini (Modelos LLM de asistencia en código) y GitHub Copilot.
* **Finalidad:**
  * Asistencia en el diseño estructurado de plantillas HTML/CSS para la interfaz visual.
  * Asesoramiento en la sintaxis de *healthchecks* nativos de Docker Compose y reglas avanzadas del Makefile.
  * Revisión y optimización de las mejores prácticas de seguridad en la construcción del `Dockerfile` (usuario no-root, limpieza de capas).
* **Partes del trabajo donde se ha aplicado:** 
  * Refactorización del código de medición de latencia en `app/app.py`.
  * Redacción de la estructura general de este archivo `README.md` y diagramas de arquitectura ASCII.