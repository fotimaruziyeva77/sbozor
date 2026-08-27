# syntax=docker/dockerfile:1
#
# SBOZOR frontend — Next 16 standalone.
# Baza: node:24-alpine (Next 16 `engines.node >= 20.9.0`; Node 24 LTS 2028-04 gacha).

# ---- deps: faqat bog'liqliklar (Docker qatlam keshi uchun alohida) ----------
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- builder: `output: standalone` build ------------------------------------
FROM node:24-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- runner: minimal, non-root ----------------------------------------------
FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# BusyBox `adduser` sintaksisi (alpine) — GNU uzun bayroqlari qo'llab-quvvatlanmaydi.
RUN addgroup -g 1001 -S nodejs \
 && adduser -u 1001 -S -G nodejs nextjs

COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
