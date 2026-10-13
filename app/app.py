import json
import os
import time
from flask import Flask, jsonify, redirect, render_template, request, url_for
import psycopg2
import psycopg2.extras
import redis

app = Flask(__name__)

# Configuración por variables de entorno
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "practica_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")

REDIS_HOST = os.getenv("REDIS_HOST", None)
REDIS_PORT = os.getenv("REDIS_PORT", "6379")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        connect_timeout=3,
    )


def fetch_pokemon_from_db():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, numero, nombre, tipo, hp, ataque, imagen_url FROM pokemon ORDER BY id ASC;"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


@app.route("/")
def index():
    entorno = "Producción (PROD)" if REDIS_HOST else "Desarrollo (DEV)"
    db_status = "ONLINE"
    redis_status = "DESACTIVADO (DEV)"
    pokemon_list = []
    fuente_datos = "PostgreSQL"
    cache_badge = "MISS"

    inicio = time.perf_counter()

    if REDIS_HOST:
        try:
            r = redis.Redis(
                host=REDIS_HOST,
                port=int(REDIS_PORT),
                socket_timeout=3,
                decode_responses=True,
            )
            r.ping()
            redis_status = "ONLINE"

            datos_cache = r.get("cartas_pokemon")
            if datos_cache:
                pokemon_list = json.loads(datos_cache)
                fuente_datos = "Caché Redis (Memoria RAM ⚡)"
                cache_badge = "HIT"
            else:
                pokemon_list = fetch_pokemon_from_db()
                r.setex("cartas_pokemon", 30, json.dumps(pokemon_list))
                fuente_datos = "PostgreSQL (Guardado en Redis por 30s)"
                cache_badge = "MISS"
        except Exception as e:
            redis_status = f"OFFLINE ({str(e)})"
            try:
                pokemon_list = fetch_pokemon_from_db()
            except Exception as dbe:
                db_status = f"OFFLINE ({str(dbe)})"
    else:
        try:
            pokemon_list = fetch_pokemon_from_db()
            fuente_datos = "PostgreSQL (Directo de BD)"
        except Exception as e:
            db_status = f"OFFLINE ({str(e)})"

    fin = time.perf_counter()
    tiempo_ms = round((fin - inicio) * 1000, 2)

    return render_template(
        "index.html",
        entorno=entorno,
        db_status=db_status,
        redis_status=redis_status,
        pokemon_list=pokemon_list,
        fuente_datos=fuente_datos,
        tiempo_ms=tiempo_ms,
        cache_badge=cache_badge,
    )


@app.route("/agregar", methods=["POST"])
def agregar_pokemon():
    """Inserta un nuevo Pokémon y limpia la caché para reflejar el cambio inmediato."""
    numero = request.form.get("numero", type=int)
    nombre = request.form.get("nombre", type=str)
    tipo = request.form.get("tipo", type=str)
    hp = request.form.get("hp", type=int)
    ataque = request.form.get("ataque", type=int)
    imagen_url = request.form.get("imagen_url", type=str)

    # Imagen por defecto si no se introduce ninguna
    if not imagen_url:
        imagen_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{numero}.png"

    # 1. Guardar en PostgreSQL
    conn = get_db_connection()
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

    # 2. Invalidación de caché en Redis (si estamos en producción)
    if REDIS_HOST:
        try:
            r = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT))
            r.delete("cartas_pokemon")
        except Exception:
            pass

    return redirect(url_for("index"))


@app.route("/status")
@app.route("/health")
def status():
    db_ok = False
    try:
        conn = get_db_connection()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    redis_ok = False
    if REDIS_HOST:
        try:
            r = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), socket_timeout=3)
            r.ping()
            redis_ok = True
        except Exception:
            redis_ok = False

    salud_general = db_ok and (redis_ok if REDIS_HOST else True)

    return (
        jsonify(
            {
                "status": "healthy" if salud_general else "unhealthy",
                "database": "healthy" if db_ok else "unhealthy",
                "cache": (
                    "healthy"
                    if redis_ok
                    else ("disabled" if not REDIS_HOST else "unhealthy")
                ),
            }
        ),
        200 if salud_general else 500,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)