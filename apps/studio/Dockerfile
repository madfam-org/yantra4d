# Frontend - Production Docker Image
# Multi-stage build for optimized production bundle
# Build context must be repo root (for packages/tokens access)

# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app/apps/studio
ARG VITE_API_BASE
ARG VITE_JANUA_BASE_URL
ARG VITE_JANUA_CLIENT_ID
ARG VITE_JANUA_REDIRECT_URI
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_JANUA_BASE_URL=${VITE_JANUA_BASE_URL}
ENV VITE_JANUA_CLIENT_ID=${VITE_JANUA_CLIENT_ID}
ENV VITE_JANUA_REDIRECT_URI=${VITE_JANUA_REDIRECT_URI}
COPY apps/studio/package.json apps/studio/package-lock.json apps/studio/.npmrc ./
# --legacy-peer-deps: @janua/react-sdk requires react@^18, project uses React 19
RUN npm ci --legacy-peer-deps
COPY packages/ /app/packages/
COPY apps/studio/ ./
RUN npm run build

# Stage 2: Production Nginx Server
FROM nginx:alpine
COPY --from=builder /app/apps/studio/dist /usr/share/nginx/html
COPY apps/studio/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
