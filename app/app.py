import json
import os
import time
from flask import Flask, jsonify, redirect, render_template, request, url_for
import psycopg2
import psycopg2.extras
import redis

app = Flask(__name__)

# Tiempo de inicio de la aplicación para calcular el uptime
UPTIME_START = time.time()

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "practica_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")

REDIS_HOST = os.getenv("REDIS_HOST", None)
REDIS_PORT = os.getenv("REDIS_PORT", "6379")


def check_db_health():
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
    """Recopila estadísticas técnicas del propio contenedor Docker."""
    pid = os.getpid()
    hostname = os.uname().nodename  # En Docker corresponde al Container ID corto

    # Lectura del consumo de memoria desde el pseudofichero del kernel Linux /proc
    mem_mb = "N/A"
    try:
        with open("/proc/self/statm", "r") as f:
            pages = int(f.read().split()[0])
            mem_mb = f"{round((pages * 4096) / (1024 * 1024), 1)} MB"
    except Exception:
        pass

    # Uptime en segundos
    uptime_sec = int(time.time() - UPTIME_START)

    return {
        "container_id": hostname[:12],
        "pid": pid,
        "mem_usage": mem_mb,
        "uptime": f"{uptime_sec}s",
    }


@app.route("/")
def index():
    entorno = "Producción (PROD)" if REDIS_HOST else "Desarrollo (DEV)"

    db_ok, db_status = check_db_health()
    redis_ok, redis_status = check_redis_health()

    pokemon_list = []
    fuente_datos = "Ninguna"
    cache_badge = "N/A"

    inicio = time.perf_counter()

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
                pokemon_list = json.loads(datos_cache)
                fuente_datos = "Caché Redis (Memoria RAM ⚡)"
                cache_badge = "HIT"
            elif db_ok:
                pokemon_list = fetch_pokemon_from_db()
                r.setex("cartas_pokemon", 30, json.dumps(pokemon_list))
                fuente_datos = "PostgreSQL (Guardado en Redis por 30s)"
                cache_badge = "MISS"
        except Exception:
            if db_ok:
                pokemon_list = fetch_pokemon_from_db()
                fuente_datos = "PostgreSQL (Fallback por fallo de caché)"
    elif db_ok:
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

        if REDIS_HOST:
            try:
                r = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT))
                r.delete("cartas_pokemon")
            except Exception:
                pass
    except Exception:
        pass

    return redirect(url_for("index"))


@app.route("/status")
@app.route("/health")
def status():
    db_ok, _ = check_db_health()
    redis_ok, _ = check_redis_health()
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)