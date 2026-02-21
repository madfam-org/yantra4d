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
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_JANUA_BASE_URL=${VITE_JANUA_BASE_URL}
ENV VITE_JANUA_CLIENT_ID=${VITE_JANUA_CLIENT_ID}
COPY apps/admin/package.json apps/admin/package-lock.json apps/admin/.npmrc ./
# Check project root for .npmrc if needed. studio/Dockerfile copies it from apps/studio/.npmrc
# If admin doesn't have .npmrc, npm ci might fail if packages are private?
# Let's assume standard npm usage for now or check if admin has .npmrc
# COPY apps/admin/.npmrc ./ 
RUN npm ci --legacy-peer-deps
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
