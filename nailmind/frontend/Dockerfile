FROM node:20-alpine AS builder

WORKDIR /app
ARG NEXT_PUBLIC_BACKEND_ORIGIN=http://localhost:8004
ARG NEXT_PUBLIC_AI_SERVICE_ORIGIN=http://localhost:8003
ARG NEXT_PUBLIC_API_BASE_URL=/api
COPY package*.json ./
RUN npm ci

COPY . .
ENV NEXT_PUBLIC_BACKEND_ORIGIN=$NEXT_PUBLIC_BACKEND_ORIGIN
ENV NEXT_PUBLIC_AI_SERVICE_ORIGIN=$NEXT_PUBLIC_AI_SERVICE_ORIGIN
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
