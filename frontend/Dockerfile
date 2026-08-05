# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build -- --configuration production

# Stage 2: Serve con Nginx
FROM nginx:1.27-alpine

COPY --from=builder /app/dist/poc-emision-frontend/browser /usr/share/nginx/html

# Configuración para SPA (redirigir todas las rutas al index.html)
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
