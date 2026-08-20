FROM python:3.11-slim

# Proxy corporativo (opcional). Se pasan como build-arg desde docker-compose.yml
# para que pip/poetry puedan salir a internet cuando el build corre detrás de
# un proxy corporativo. Si no se define nada, quedan vacíos y no afectan
# builds sin proxy.
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=$HTTP_PROXY \
    HTTPS_PROXY=$HTTPS_PROXY \
    NO_PROXY=$NO_PROXY \
    http_proxy=$HTTP_PROXY \
    https_proxy=$HTTPS_PROXY \
    no_proxy=$NO_PROXY

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