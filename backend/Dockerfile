FROM python:3.11-slim

WORKDIR /app

# Instalar Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Copiar archivos de dependencias
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias sin crear entorno virtual (ya estamos en container)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev

# Copiar código fuente
COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
