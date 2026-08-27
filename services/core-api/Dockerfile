# syntax=docker/dockerfile:1

# SBOZOR core-api — multi-stage image.
#
# Baza: python:3.13-slim-trixie (Debian, glibc). musl-asosidagi yengil
# image'lar ISHLATILMAYDI — manylinux_2_28 g'ildiraklar glibc >= 2.28 talab
# qiladi, musl ostida esa ular manbadan qurilardi (onnxruntime, asyncpg...).
#
# Build konteksti — REPO ILDIZI (compose.yaml da `context: .`), chunki
# `packages/sbozor-core` editable bog'liqlik sifatida kerak.

FROM python:3.13-slim-trixie AS base

COPY --from=ghcr.io/astral-sh/uv:0.11.33 /uv /bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Faqat manifestlar — kod o'zgarganda bog'liqlik qatlami qayta qurilmasin.
COPY packages/ /app/packages/
COPY services/core-api/pyproject.toml services/core-api/uv.lock /app/services/core-api/


# ---------- dev: dev guruh bilan (pytest, ruff, mypy, testcontainers) ----------
FROM base AS dev

RUN uv sync --frozen --project services/core-api

# Testlar va Alembic repo ildizidan ishlaydi.
COPY . /app
WORKDIR /app


# ---------- runtime: dev bog'liqliklarisiz, non-root ----------
FROM base AS runtime

RUN uv sync --frozen --no-dev --project services/core-api

COPY services/core-api/app/ /app/services/core-api/app/

# Konteyner root bilan ishlamaydi (T-01-07).
RUN useradd --create-home --uid 10001 appuser
USER appuser

# `uvicorn app.main:app` aynan shu katalogdan hal bo'ladi.
WORKDIR /app/services/core-api
