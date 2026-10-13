# 1. Imagen base oficial de Python fijando versión ligera (slim)
FROM python:3.11-slim

# 2. Directorio dentro del contenedor donde se guardará todo
WORKDIR /app

# 3. Copiamos SOLO los requerimientos primero (para aprovechar la caché de Docker)
COPY requirements.txt .

# 4. Instalamos librerías sin guardar archivos temporales del instalador
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos el resto del código de la aplicación
COPY app.py .

# 6. Seguridad: Creamos un usuario sin privilegios para no correr como root
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 7. Documentamos el puerto que usa Flask
EXPOSE 5000

# 8. Comando para arrancar el servidor web
CMD ["python", "app.py"]