FROM node:20-alpine AS builder
WORKDIR /app/apps/landing
COPY apps/landing/package*.json ./
RUN npm ci
COPY packages/ /app/packages/
COPY commons/ /app/commons/
COPY apps/landing/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/apps/landing/dist /usr/share/nginx/html
COPY apps/landing/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
