# =============================================================================
# GarimpoGov Frontend - Dockerfile para Railway
# Stage 1: build da aplicacao React/Vite
# Stage 2: servir com Nginx
# =============================================================================

# ---- Build Stage ----
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# VITE_API_URL sera injetada como build arg pelo Railway
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ---- Serve Stage ----
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
