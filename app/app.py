import json
import os
import time
from flask import Flask, jsonify, redirect, render_template, request, url_for
import psycopg2
import psycopg2.extras
import redis

# Inicialización de la aplicación Flask
app = Flask(__name__)

# Marca de tiempo global para calcular el Uptime (tiempo activo) del contenedor
UPTIME_START = time.time()

# ==============================================================================
# REQUISITO DE SEGURIDAD: Sin credenciales ni configuraciones "hardcodeadas"
# Se leen todas las variables de entorno inyectadas desde .env.dev / .env.prod
# ==============================================================================
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "practica_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")

# REDIS_HOST solo estará presente en el entorno de Producción (.env.prod)
REDIS_HOST = os.getenv("REDIS_HOST", None)
REDIS_PORT = os.getenv("REDIS_PORT", "6379")


# ==============================================================================
# REQUISITO REQUERIDO: Comprobación dinámica del estado de los servicios
# Evalúa la conexión con PostgreSQL en tiempo real sin bloquear la app
# ==============================================================================
def check_db_health():
    """Verifica si la base de datos PostgreSQL responde a peticiones."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=2,
        )
        conn.close()
        return True, "ONLINE"
    except Exception as e:
        return False, f"OFFLINE ({str(e)})"


def check_redis_health():
    """Verifica la salud del servicio de caché Redis (solo activo en PROD)."""
    if not REDIS_HOST:
        return False, "DESACTIVADO (DEV)"
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=int(REDIS_PORT),
            socket_timeout=2,
            decode_responses=True,
        )
        r.ping()
        return True, "ONLINE"
    except Exception as e:
        return False, f"OFFLINE ({str(e)})"


def fetch_pokemon_from_db():
    """Consulta la lista de Pokémon directamente en PostgreSQL."""
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        connect_timeout=2,
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, numero, nombre, tipo, hp, ataque, imagen_url FROM pokemon ORDER BY numero ASC;"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_container_metrics():
    """
    Métricas técnicas del propio contenedor Docker.
    Permite visualizar el ID del contenedor (Hostname), consumo RAM y PID.
    """
    pid = os.getpid()
    hostname = os.uname().nodename  # Corresponde al ID corto del contenedor en Docker

    # Lectura del uso de memoria en RAM desde el sistema de archivos del kernel Linux /proc
    mem_mb = "N/A"
    try:
        with open("/proc/self/statm", "r") as f:
            pages = int(f.read().split()[0])
            mem_mb = f"{round((pages * 4096) / (1024 * 1024), 1)} MB"
    except Exception:
        pass

    uptime_sec = int(time.time() - UPTIME_START)

    return {
        "container_id": hostname[:12],
        "pid": pid,
        "mem_usage": mem_mb,
        "uptime": f"{uptime_sec}s",
    }


# ==============================================================================
# RUTA PRINCIPAL (UI WEB)
# Muestra el estado del entorno, métricas y aplica la lógica de Caché (Redis)
# ==============================================================================
@app.route("/")
def index():
    entorno = "Producción (PROD)" if REDIS_HOST else "Desarrollo (DEV)"

    # Comprobación dinámica e independiente del estado de los servicios
    db_ok, db_status = check_db_health()
    redis_ok, redis_status = check_redis_health()

    pokemon_list = []
    fuente_datos = "Ninguna"
    cache_badge = "N/A"

    # Cronómetro para medir la latencia total de la consulta
    inicio = time.perf_counter()

    # REQUISITO CACHÉ: En PROD se intenta leer primero de Redis
    if REDIS_HOST and redis_ok:
        try:
            r = redis.Redis(
                host=REDIS_HOST,
                port=int(REDIS_PORT),
                socket_timeout=2,
                decode_responses=True,
            )
            datos_cache = r.get("cartas_pokemon")
            if datos_cache:
                # CACHE HIT: Datos servidos directamente desde la RAM de Redis (~1 ms)
                pokemon_list = json.loads(datos_cache)
                fuente_datos = "Caché Redis (Memoria RAM ⚡)"
                cache_badge = "HIT"
            elif db_ok:
                # CACHE MISS: Se lee de PostgreSQL y se guarda en Redis con TTL de 30s
                pokemon_list = fetch_pokemon_from_db()
                r.setex("cartas_pokemon", 30, json.dumps(pokemon_list))
                fuente_datos = "PostgreSQL (Guardado en Redis por 30s)"
                cache_badge = "MISS"
        except Exception:
            # FALLBACK DE SEGURIDAD: Si falla Redis, la app sigue viva leyendo de PostgreSQL
            if db_ok:
                pokemon_list = fetch_pokemon_from_db()
                fuente_datos = "PostgreSQL (Fallback por fallo de caché)"
    elif db_ok:
        # En DEV (o si Redis no está configurado), se consulta PostgreSQL directamente
        pokemon_list = fetch_pokemon_from_db()
        fuente_datos = "PostgreSQL (Directo de BD)"

    fin = time.perf_counter()
    tiempo_ms = round((fin - inicio) * 1000, 2)
    metrics = get_container_metrics()

    return render_template(
        "index.html",
        entorno=entorno,
        db_status=db_status,
        redis_status=redis_status,
        pokemon_list=pokemon_list,
        fuente_datos=fuente_datos,
        tiempo_ms=tiempo_ms,
        cache_badge=cache_badge,
        metrics=metrics,
    )


# ==============================================================================
# REQUISITO PERSISTENCIA Y ESCRITURA: Alta de nuevos registros
# Invalida la caché de Redis al escribir para garantizar consistencia de datos
# ==============================================================================
@app.route("/agregar", methods=["POST"])
def agregar_pokemon():
    numero = request.form.get("numero", type=int)
    nombre = request.form.get("nombre", type=str)
    tipo = request.form.get("tipo", type=str)
    hp = request.form.get("hp", type=int)
    ataque = request.form.get("ataque", type=int)
    imagen_url = request.form.get("imagen_url", type=str)

    if not imagen_url:
        imagen_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{numero}.png"

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=2,
        )
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO pokemon (numero, nombre, tipo, hp, ataque, imagen_url)
            VALUES (%s, %s, %s, %s, %s, %s);
        """,
            (numero, nombre, tipo, hp, ataque, imagen_url),
        )
        conn.commit()
        cur.close()
        conn.close()

        # INVALIDACIÓN DE CACHÉ: Al insertar en la BD, borramos la clave en Redis
        # para forzar que la siguiente lectura traiga los datos actualizados
        if REDIS_HOST:
            try:
                r = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT))
                r.delete("cartas_pokemon")
            except Exception:
                pass
    except Exception:
        pass

    return redirect(url_for("index"))


# ==============================================================================
# REQUISITO OBLIGATORIO: Endpoints técnicos /status y /health
# Utilizados por los Healthchecks de Docker y para monitoreo externo
# ==============================================================================
@app.route("/status")
@app.route("/health")
def status():
    """
    Devuelve un JSON con el estado de salud de los servicios dependientes.
    Si algún servicio crítico falla, responde con código HTTP 503 (Service Unavailable).
    """
    db_ok, _ = check_db_health()
    redis_ok, _ = check_redis_health()

    # En PROD ambos deben estar sanos; en DEV solo se requiere PostgreSQL
    sistema_sano = db_ok and (redis_ok if REDIS_HOST else True)

    return (
        jsonify(
            {
                "status": "healthy" if sistema_sano else "degraded",
                "database": "healthy" if db_ok else "unhealthy",
                "cache": (
                    "healthy"
                    if redis_ok
                    else ("disabled" if not REDIS_HOST else "unhealthy")
                ),
            }
        ),
        200 if sistema_sano else 503,
    )


# Punto de entrada de la aplicación en el puerto 5000 dentro del contenedor
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)