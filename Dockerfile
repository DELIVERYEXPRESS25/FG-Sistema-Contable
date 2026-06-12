# ═══════════════════════════════════════════════════════════════════════
# Dockerfile - FG Sistema Contable
# ═══════════════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Variables de entorno del sistema
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ═══════════════════════════════════════════════════════════════════════
# Variables de entorno - Configuración de la aplicación
# ═══════════════════════════════════════════════════════════════════════

# Flask
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV SECRET_KEY=change-this-in-production
ENV HOST=0.0.0.0
ENV PORT=5000

# Base de datos
ENV DB_TYPE=sqlite
ENV DB_PATH=.colectivo_fg.db

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para cachear
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio para datos
RUN mkdir -p /app/data

# Exponer puerto
EXPOSE 5000

# Comando para ejecutar la app
CMD ["python", "main.py"]