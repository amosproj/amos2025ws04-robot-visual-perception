# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

ARG VITE_BACKEND_URL=http://host.docker.internal:8001
ARG VITE_ORCHESTRATOR_URL=http://host.docker.internal:8002
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
ENV VITE_ORCHESTRATOR_URL=$VITE_ORCHESTRATOR_URL

RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

