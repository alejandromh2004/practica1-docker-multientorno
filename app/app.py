import os
import psycopg2
import redis
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Leemos las credenciales desde variables de entorno (requisito de seguridad)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "practica_db")
DB_USER = os.getenv("DB_USER", "usuario")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_PORT = os.getenv("DB_PORT", "5432")

# Redis solo existirá si definimos REDIS_HOST (en producción)
REDIS_HOST = os.getenv("REDIS_HOST", None)
REDIS_PORT = os.getenv("REDIS_PORT", "6379")


def check_database():
    """Intenta conectarse a PostgreSQL y crear una tabla si no existe."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=3,
        )
        cur = conn.cursor()
        # Creamos una tabla simple para demostrar persistencia
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS visitas (
                id SERIAL PRIMARY KEY,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        # Registramos una visita
        cur.execute("INSERT INTO visitas DEFAULT VALUES;")
        conn.commit()

        # Contamos cuántas visitas hay guardadas en la BD
        cur.execute("SELECT COUNT(*) FROM visitas;")
        total = cur.fetchone()[0]

        cur.close()
        conn.close()
        return True, f"Conectado (Registros guardados en BD: {total})"
    except Exception as e:
        return False, f"Desconectado ({str(e)})"


def check_cache():
    """Intenta conectarse a Redis si está configurado."""
    if not REDIS_HOST:
        return False, "Desactivado (Entorno de desarrollo sin caché)"

    try:
        client = redis.Redis(
            host=REDIS_HOST, port=int(REDIS_PORT), socket_timeout=3
        )
        client.ping()
        # Demostramos el uso de caché sumando un contador rápido en memoria
        visitas_cache = client.incr("contador_visitas_cache")
        return True, f"Conectado (Visitas en caché Redis: {visitas_cache})"
    except Exception as e:
        return False, f"Desconectado ({str(e)})"


@app.route("/")
def index():
    """Página principal que muestra visualmente el estado de los servicios."""
    db_ok, db_msg = check_database()
    cache_ok, cache_msg = check_cache()

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Práctica 1 - Estado del Servicio</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f4f6f9; }}
            .card {{ background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); max-width: 600px; }}
            .status-ok {{ color: green; font-weight: bold; }}
            .status-err {{ color: red; font-weight: bold; }}
            .status-off {{ color: gray; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Panel de Estado - Práctica 1</h1>
            <p><strong>Base de Datos (PostgreSQL):</strong> 
               <span class="{'status-ok' if db_ok else 'status-err'}">{db_msg}</span>
            </p>
            <p><strong>Caché (Redis):</strong> 
               <span class="{'status-ok' if cache_ok else 'status-off'}">{cache_msg}</span>
            </p>
            <hr>
            <p><small>Consulta también el endpoint técnico en <code>/status</code></small></p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route("/status")
@app.route("/health")
def status():
    """Endpoint técnico exigido por la práctica para healthchecks y monitorización."""
    db_ok, db_msg = check_database()
    cache_ok, cache_msg = check_cache()

    estado_general = "ok" if db_ok else "degraded"

    return (
        jsonify(
            {
                "status": estado_general,
                "database": {"connected": db_ok, "details": db_msg},
                "cache": {
                    "enabled": bool(REDIS_HOST),
                    "connected": cache_ok,
                    "details": cache_msg,
                },
            }
        ),
        200 if db_ok else 500,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)