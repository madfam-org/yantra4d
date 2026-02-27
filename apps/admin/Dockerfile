# Frontend - Production Docker Image
# Multi-stage build for optimized production bundle
# Build context must be repo root (for packages/tokens access)

# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app/apps/admin
ARG VITE_API_BASE
ARG VITE_JANUA_BASE_URL
ARG VITE_JANUA_CLIENT_ID
ARG VITE_JANUA_REDIRECT_URI
ARG VITE_AUTH_ENABLED
ARG NPM_MADFAM_TOKEN
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_JANUA_BASE_URL=${VITE_JANUA_BASE_URL}
ENV VITE_JANUA_CLIENT_ID=${VITE_JANUA_CLIENT_ID}
ENV VITE_AUTH_ENABLED=${VITE_AUTH_ENABLED}
ENV NPM_MADFAM_TOKEN=${NPM_MADFAM_TOKEN}
COPY apps/admin/package.json apps/admin/package-lock.json apps/admin/.npmrc ./
RUN npm ci --legacy-peer-deps
# Clear token from environment after install
ENV NPM_MADFAM_TOKEN=""
COPY packages/ /app/packages/
COPY apps/admin/ ./
COPY apps/studio/ /app/apps/studio/
RUN ln -s /app/apps/admin/node_modules /app/node_modules
RUN npm run build

# Stage 2: Production Nginx Server
FROM nginx:alpine
COPY --from=builder /app/apps/admin/dist /usr/share/nginx/html
# We need an nginx.conf for admin too.
COPY apps/admin/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
