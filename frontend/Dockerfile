# ---- build stage ----
FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Uses the "production" configuration (angular.json defaultConfiguration),
# which swaps in src/environments/environment.prod.ts (apiUrl = /api)
RUN npm run build

# ---- serve stage ----
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

EXPOSE 80
