FROM node:22-alpine AS builder
WORKDIR /app/apps/landing
COPY apps/landing/package*.json ./
RUN npm ci
COPY packages/ /app/packages/
COPY apps/landing/ ./
ARG PUBLIC_STUDIO_URL
ENV PUBLIC_STUDIO_URL=$PUBLIC_STUDIO_URL
# Cloudflare Web Analytics site token. Empty (the default) ships no beacon.
ARG PUBLIC_CF_BEACON_TOKEN=
ENV PUBLIC_CF_BEACON_TOKEN=$PUBLIC_CF_BEACON_TOKEN
# First-party tier beacon (src/lib/rum.ts). Off until the API accepts the event.
ARG PUBLIC_RUM_BEACON=0
ENV PUBLIC_RUM_BEACON=$PUBLIC_RUM_BEACON
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/apps/landing/dist /usr/share/nginx/html
COPY apps/landing/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
