# Stage 1: Build
FROM node:24-alpine AS builder

# Proxy corporativo (opcional). Se pasan como build-arg desde docker-compose.yml
# (ver la sección `args` de cada servicio) para que npm pueda salir a internet
# cuando el build corre detrás de un proxy corporativo. Si no se define nada,
# quedan vacíos y no afectan builds sin proxy.
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
COPY package*.json .npmrc* ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build -- --configuration production

# Stage 2: Serve con Nginx
FROM nginx:1.27-alpine

COPY --from=builder /app/dist/poc-emision-frontend/browser /usr/share/nginx/html

# Configuración para SPA + proxy de /api hacia el backend (ver nginx.conf).
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80