"""Minimal HTTP yuzasi — `cv-service` HTTP XIZMATI EMAS (D-23).

=============================================================================
⛔ QOIDA 1 — BU YUZA KENGAYMAYDI.

`cv-service` — `taskiq` WORKER. Bu yerda AYNAN BITTA marshrut bor
(`/healthz`) va yangisi qo'shilmaydi: dalil rasmini ko'rsatish, zona CRUD
va hisobotlar — hammasi `core-api` ning ishi (04-09 proxy endpointi,
05-06 marshrutlari). Ikkinchi HTTP yuzasi ikkinchi RBAC, ikkinchi audit va
ikkinchi tenant kontekstini talab qilardi.

=============================================================================
⚠⚠ BUGUN BU KIRISH NUQTASINI BIRORTA KONTEYNER YURITMAYDI — VA BU ATAYIN.

`compose.yaml` dagi `cv-service` `taskiq worker app.worker:broker` ni
yuritadi (05-08: «`cv-service` — sof worker, ya'ni FAQAT shu variant»).
Unga `nc -z` yoki `/healthz` healthcheck QO'YILMAGAN, chunki jarayon
tirikligi «aniqlash bajarilyaptimi?» savoliga JAVOB BERMAYDI — bu
`compose.yaml` dagi `scheduler` blokining so'zma-so'z o'lchangan qarori
(RESEARCH Pitfall 14).

Yagona ishonchli signal — BAZADAGI natija: `cv_detect` yurak urishi
(`system_heartbeats`) va uni O'QIYDIGAN `/internal/self-check`
(`core-api`, `EXPECTED_COMPONENTS` da). Komponent bugundan reyestrda
turadi va u `never_seen` holatida — 05-08 uni yozadigan qiladi.

Ya'ni bu modul HOZIR ishlatilmaydi va u soxta healthcheck uchun
konteynerga chiqarilmaydi: aynan shunday chiqarish «sog'lom» degan
YOLG'ON ISHONCH berardi (o'z portiga o'zi javob beradigan yuza). U D-23
talab qilgan health yuzasi sifatida saqlanadi va uning `init_sentry()`
chaqiruvi `services/cv-service/tests/unit/test_sentry_entrypoints.py` da
obyekt darajasida o'lchanadi — ya'ni u SINALMAGAN kod emas.
=============================================================================
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sbozor_core.logging import configure_logging

from app.observability import init_sentry
from app.settings import Settings, get_settings

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Jurnal va Sentry — `core-api/app/main.py::lifespan` bilan bir xil shakl.

    ⚠ ULANISH PULI OCHILMAYDI: bu yuza bazaga ham, omborga ham tegmaydi.
      `/healthz` — LIVENESS va u ta'rifi bo'yicha tashqi bog'liqliklarga
      TEGMASLIGI kerak (`core-api/app/main.py:6` bilan bir xil qoida).
    """
    settings: Settings = get_settings()
    configure_logging(settings.log_level)
    log.info("sentry", enabled=init_sentry(settings.sentry_dsn))

    application.state.settings = settings
    yield


app = FastAPI(
    title="SBOZOR cv-service",
    version="0.1.0",
    # ⚠ OpenAPI CHIQARILMAYDI: bu yuzada mijoz yo'q va sxema faqat yangi
    #   marshrut qo'shish taklifiga aylanardi (QOIDA 1).
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness — jarayon javob berayotganini bildiradi, boshqa hech narsani emas."""
    return {"status": "ok"}
