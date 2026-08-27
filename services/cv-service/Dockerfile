# syntax=docker/dockerfile:1

# SBOZOR cv-service — multi-stage image (loyihaning IKKINCHI Python image'i).
#
# Baza: python:3.13-slim-trixie (Debian, glibc) — `core-api` bilan AYNAN bir
# xil va sabab BU YERDA YANADA QAT'IY: `onnxruntime` faqat manylinux_2_28
# g'ildiraklarini beradi (glibc >= 2.28) va musl ostida g'ildirak UMUMAN
# YO'Q — u manbadan qurilardi (soatlab build, LLVM/protobuf toolchain).
#
# ⚠ `opencv-python-headless` ATAYIN (`-headless`): oddiy `opencv-python`
#   GTK/X11 ni tortadi (~70 MB) va slim image'da klassik
#   `ImportError: libGL.so.1` beradi.
#
# Build konteksti — REPO ILDIZI (`compose.yaml` da `context: .`), chunki
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
COPY services/cv-service/pyproject.toml services/cv-service/uv.lock /app/services/cv-service/


# ---------- dev: dev guruh bilan (pytest, ruff, mypy) ----------
FROM base AS dev

RUN uv sync --frozen --project services/cv-service

# Testlar repo ildizidan mount qilinadi (`compose.yaml`: `.:/app`), lekin
# image o'zi ham to'liq bo'lishi kerak — mount'siz `docker run` ham ishlasin.
COPY . /app

# ⚠⚠ MODEL BU BOSQICHGA KO'CHIRILMAYDI — VA BU ATAYIN.
#    `cv-tests` `-m "not model"` bilan yuradi, ya'ni butun to'plam HAQIQIY
#    artefaktsiz ishlaydi. Modelni bu yerga ham ko'chirish «testlar modelni
#    sinayapti» degan YOLG'ON taassurot berardi: aslida ular mexanikani
#    sinaydi, aniqlikni EMAS (D-01, 05-VALIDATION ikki qatlam).
WORKDIR /app/services/cv-service


# ---------- runtime: dev bog'liqliklarisiz, non-root ----------
FROM base AS runtime

RUN uv sync --frozen --no-dev --project services/cv-service

COPY services/cv-service/app/ /app/services/cv-service/app/

# =========================================================================
# ⚠⚠ ONNX ARTEFAKTI BUILD PAYTIDA KIRADI — ISH PAYTIDA YUKLAB OLINMAYDI (D-24).
#
# Katalogda kamida `README.md` bor, ya'ni artefakt QO'YILMAGAN bo'lsa ham
# BUILD O'TADI. Artefaktning yo'qligi ISHGA TUSHISHDA ko'rinadi:
# `app/settings.py` ning `field_validator` i `CV_MODEL_PATH` ni tekshiradi
# va konteyner sabab bilan yiqiladi (§4.1 — «birinchi kadrda emas»).
#
# `.gitignore` da `ops/models/*.onnx` bor, `.dockerignore` da esa YO'Q —
# ya'ni artefakt repoda saqlanmaydi, lekin build konteksti uni ko'radi.
# =========================================================================
COPY ops/models/ /app/models/

# Konteyner root bilan ishlamaydi (T-01-07).
RUN useradd --create-home --uid 10001 appuser
USER appuser

# `taskiq worker app.worker:broker` aynan shu katalogdan hal bo'ladi.
WORKDIR /app/services/cv-service
