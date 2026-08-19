# Stage 1: Build
FROM node:24-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build -- --configuration production

# Stage 2: Serve con Nginx
FROM nginx:1.27-alpine

COPY --from=builder /app/dist/poc-emision-frontend/browser /usr/share/nginx/html

# Configuración para SPA + proxy de /api hacia el backend (ver nginx.conf).
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80