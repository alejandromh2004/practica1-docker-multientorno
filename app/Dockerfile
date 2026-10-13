FROM python:3.11-slim

WORKDIR /app

# Capa de dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos app.py y templates/
COPY . .

# Seguridad: Usuario no root
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 5000

CMD ["python", "app.py"]