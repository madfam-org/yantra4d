# Frontend - Production Docker Image
# Multi-stage build for optimized production bundle

# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
ARG VITE_API_BASE
ARG VITE_JANUA_BASE_URL
ARG VITE_JANUA_CLIENT_ID
ARG VITE_JANUA_REDIRECT_URI
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_JANUA_BASE_URL=${VITE_JANUA_BASE_URL}
ENV VITE_JANUA_CLIENT_ID=${VITE_JANUA_CLIENT_ID}
ENV VITE_JANUA_REDIRECT_URI=${VITE_JANUA_REDIRECT_URI}
COPY package*.json ./
RUN npm ci --silent
COPY . .
RUN npm run build

# Stage 2: Production Nginx Server
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
