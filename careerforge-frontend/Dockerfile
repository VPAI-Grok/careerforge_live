# ── CareerForge Frontend — Cloud Run Dockerfile ───────────────────────────────
# Multi-stage build: build static assets with Node, serve with nginx

# Stage 1: Build
FROM node:20-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Build-time env var — the backend Cloud Run URL
# This gets baked into the static JS bundle at build time
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy built assets to nginx html dir
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config for SPA routing (all routes → index.html)
RUN echo 'server { \
    listen 8080; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location /assets/ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
