# --- Stage 1: Build the Frontend ---
FROM node:20-alpine AS build-stage
WORKDIR /app

# Path relative to repo root
COPY frontend/package*.json ./
RUN npm install

# Path relative to repo root
COPY frontend/ .
RUN npm run build

# --- Stage 2: Final Gateway Image ---
FROM nginx:stable-alpine

RUN apk add --no-cache python3 py3-pip && pip3 install --no-cache-dir redis asyncio --break-system-packages

WORKDIR /opt/watcher

# Paths relative to repo root
COPY backend/gateway/watcher.py .
COPY backend/gateway/entrypoint.sh .
RUN chmod +x entrypoint.sh

# Path relative to repo root
COPY backend/gateway/nginx-master.conf /etc/nginx/nginx.conf
COPY backend/gateway/nginx.conf /etc/nginx/conf.d/default.conf

# Inject compiled static frontend from Stage 1
COPY --from=build-stage /app/dist /usr/share/nginx/html

ENTRYPOINT ["/opt/watcher/entrypoint.sh"]