# syntax=docker/dockerfile:1

# SBOZOR bot-service — multi-stage image (loyihaning UCHINCHI Python image'i).
#
# Baza: python:3.13-slim-trixie (Debian, glibc) — `core-api` va `cv-service`
# bilan AYNAN bir xil, va sabab BU YERDA HAM MEXANIK: `aiogram[fast]`
# `uvloop` va `aiodns` ni tortadi, `uvloop 0.22.1` esa faqat
# `manylinux_2_28_x86_64` g'ildiragini beradi.
#
# ⛔ ALPINE EMAS: musl ostida `uvloop` uchun g'ildirak YO'Q — u manbadan
#    qurilardi (libuv toolchain, uzoq build, mo'rt natija).
#
# ⚠ `uv.lock` XOSTDA EMAS, KONTEYNERDA generatsiya qilingan: `uvloop` ning
#   Windows g'ildiragi umuman yo'q va xostda `uv lock` manbadan qurishga
#   urinib yiqiladi. Bu XOST ARTEFAKTI, paket nuqsoni emas
#   (07-RESEARCH § Package Legitimacy Audit).
#
# Build konteksti — REPO ILDIZI (`compose.yaml` da `context: .`), `cv-service`
# bilan bir xil shakl. ⚠ `packages/` BU YERGA KO'CHIRILMAYDI va bu ATAYIN:
# `sbozor-core` bu servisning bog'liqligi EMAS (D-08/1 — u `models/` orqali
# SQLAlchemy'ni tortardi). Sabab `pyproject.toml` va `README.md` da yozilgan.

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
COPY services/bot-service/pyproject.toml services/bot-service/uv.lock /app/services/bot-service/


# ---------- dev: dev guruh bilan (pytest, ruff, mypy) ----------
FROM base AS dev

RUN uv sync --frozen --project services/bot-service

# Testlar repo ildizidan mount qilinadi (`compose.yaml`: `.:/app`), lekin
# image o'zi ham to'liq bo'lishi kerak — mount'siz `docker run` ham ishlasin.
#
# ⚠ `compose.yaml` ham SHU nusxadan o'qiladi: `tests/unit/
#   test_sentry_entrypoints.py` darvozasi repo ildizidagi `compose.yaml` ni
#   ochadi va u mount'siz ishga tushirishda ham topilishi kerak.
COPY . /app

WORKDIR /app/services/bot-service


# ---------- runtime: dev bog'liqliklarisiz, non-root ----------
FROM base AS runtime

RUN uv sync --frozen --no-dev --project services/bot-service

COPY services/bot-service/app/ /app/services/bot-service/app/

# Konteyner root bilan ishlamaydi (T-01-07).
RUN useradd --create-home --uid 10001 appuser
USER appuser

# `python -m app.main` aynan shu katalogdan hal bo'ladi.
WORKDIR /app/services/bot-service
