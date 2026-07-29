"""core-api ASGI ilovasi.

`lifespan=` ishlatiladi — `@app.on_event` FastAPI 0.93+ da eskirgan.

Ikkita sog'liq endpointi ajratilgan:
  * `/healthz` — liveness: tashqi bog'liqliklarga TEGMAYDI, har doim 200.
                 Compose healthcheck va orkestrator shundan foydalanadi.
  * `/readyz`  — readiness: DB va Valkey ping; biri yiqilsa 503.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Ulanish pullarini ilova hayoti davomida bir marta ochadi va yopadi."""
    settings: Settings = get_settings()
    engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
    cache: Redis = Redis.from_url(settings.valkey_url)

    application.state.settings = settings
    application.state.engine = engine
    application.state.cache = cache
    try:
        yield
    finally:
        await cache.aclose()
        await engine.dispose()


app = FastAPI(
    title="SBOZOR core-api",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness — jarayon javob berayotganini bildiradi, boshqa hech narsani emas."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    """Readiness — DB va Valkey haqiqatan javob berayotganini tekshiradi."""
    checks: dict[str, str] = {}
    ready = True

    engine: AsyncEngine = request.app.state.engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - har qanday nosozlik = tayyor emas
        ready = False
        checks["database"] = f"error: {type(exc).__name__}"
    else:
        checks["database"] = "ok"

    cache: Redis = request.app.state.cache
    try:
        await cache.ping()
    except Exception as exc:  # noqa: BLE001 - har qanday nosozlik = tayyor emas
        ready = False
        checks["cache"] = f"error: {type(exc).__name__}"
    else:
        checks["cache"] = "ok"

    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ok" if ready else "degraded", "checks": checks},
    )
