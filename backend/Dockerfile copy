FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Instala Poetry
RUN pip install "poetry==${POETRY_VERSION}"

# Copia manifiestos para aprovechar cache de capas
COPY pyproject.toml poetry.lock* ./

# Instala solo dependencias de runtime (sin entorno virtual y sin paquete raíz)
RUN poetry install --only main --no-root --no-ansi

# Copia código fuente
COPY app ./app

# Crea carpeta temporal de uploads esperada por la app
RUN mkdir -p /app/tmp/uploads

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
