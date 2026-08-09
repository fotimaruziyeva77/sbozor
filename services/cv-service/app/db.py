"""Baza qatlami — sessiya fabrikasi va FON-VAZIFANING O'Z tenant konteksti.

=============================================================================
PITFALL 13 — JOB TENANT KONTEKSTINI O'ZI O'RNATADI (§S-5).

`core-api/app/jobs/discovery.py:15-40` da yozilgan sabab bu servisda
KUCHLIROQ, chunki bu yerda HTTP qatlami UMUMAN YO'Q: `cv-service` — sof
worker (D-23), ya'ni `Request` dan `Principal` oladigan yo'l (`deps.py`)
bu kod bazasida mavjud emas va hech qachon bajarilmaydi.

Kontekstsiz RLS FAIL-CLOSED ishlaydi, lekin "fail" so'zi aldamchi:

    SELECT / UPDATE  ->  0 qator, ISTISNO YO'Q
    INSERT           ->  `WITH CHECK` buzilishi (bu esa KO'RINADI)

Ya'ni kontekstsiz `detect` kadr qatorini "topa olmaydi", zonalarni "topa
olmaydi" va HECH QANDAY xato bermaydi. Nosozlik `occupancy_events` da
JIMGINA 0 qator bo'lib ko'rinardi — bu esa "bozor bo'sh edi" degan
to'g'ri javobdan farq qilmaydi.

=============================================================================
⛔ `Principal` YO'Q — VA `actor_id` PARAMETRI HAM YO'Q.

`discovery.py::_system_transaction()` `actor_id` ni QABUL QILADI, chunki
kashfiyotni ODAM boshlagan ("buni X admin so'radi, bajargani esa tizim").
Aniqlashni esa hech kim so'ramaydi: u kadr saqlangandan keyin AVTOMATIK
ishga tushadi.

Parametrning YO'QLIGI — kelishuv emas, STRUKTURA (`go2rtc.py:193-197`
naqshi): u mavjud bo'lsa keyingi tahrirlovchi u yerga "kim bo'lsa ham"
degan qiymat berardi va D-12 ning "AI qarori — MASHINANING qarori,
nazoratchiniki ALOHIDA yozuv" ajratmasi audit jurnalida jimgina yo'qolardi.

=============================================================================
HAR CHAQIRUVDA YANGI TRANZAKSIYA — VA BITTA TRANZAKSIYADA BITTA BOZOR.

GUC'lar `SET LOCAL` bilan qo'yiladi, ya'ni ular har `COMMIT` da tozalanadi.
"Bir marta o'rnatib, keyin qayta ishlataman" yo'li fail-closed holatga
tushardi. Bitta tranzaksiyada ikki bozor — tenant sizib chiqishining eng
qisqa yo'li (§S-5, T-05-34).
=============================================================================
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sbozor_core.db import make_engine, make_sessionmaker
from sbozor_core.enums import ActorKind
from sbozor_core.tenancy import set_tenant_context

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.settings import Settings

__all__ = ["open_sessionmaker", "system_transaction"]


@asynccontextmanager
async def open_sessionmaker(settings: Settings) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Engine'ni ochadi, sessiya fabrikasini beradi va chiqishda YOPADI.

    ⚠ ENGINE — RESURS, MODUL GLOBALI EMAS (`sbozor_core/db.py` ning ochiq
      qoidasi). Worker uni `WORKER_STARTUP` da bir marta ochadi va
      `WORKER_SHUTDOWN` da yopadi; test esa o'z engine'ini beradi.

    ⚠ `DATABASE_URL` DA HAR DOIM `sbozor_app` (NOSUPERUSER, NOBYPASSRLS)
      bo'lishi shart — superuser bilan ulanilsa `FORCE ROW LEVEL SECURITY`
      ham to'xtata olmaydi va yuqoridagi butun kafolat yo'qoladi.
    """
    engine = make_engine(settings.database_url)
    try:
        yield make_sessionmaker(engine)
    finally:
        await engine.dispose()


@asynccontextmanager
async def system_transaction(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti O'RNATILGAN sessiya — `discovery.py:170-205` ning jufti.

    Uch farq bor va uchalasi ham modul docstringida:

      1. `Principal` YO'Q va `actor_id` PARAMETRI HAM YO'Q;
      2. `actor_kind=ActorKind.SYSTEM`;
      3. `HTTPException` YO'Q — worker'da javob beriladigan mijoz yo'q.

    Args:
        sessionmaker: sessiya fabrikasi. ARGUMENT, modul globali EMAS.
        market_id: tenant. U navbat xabaridan EMAS, `snapshots` QATORIDAN
            keladi (T-05-33): xabar faqat identifikator olib yuradi va
            soxta `market_id` yuborish yo'li shu bilan yopiladi.
        request_id: bitta kadr uchun barcha yozuvlarni BIR IPGA bog'laydigan
            deterministik satr (`detect.py::_request_id`).
    """
    # SIM117 (`async with` larni birlashtirish) `discovery.py:193-195` dagi
    # bilan AYNAN bir xil sababdan rad etilgan: ichki blok TRANZAKSIYA
    # chegarasi va u shu yerdagi butun xavfsizlik da'vosini ushlab turadi.
    async with sessionmaker() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=None,
                request_id=request_id,
                actor_kind=ActorKind.SYSTEM,
            )
            yield session
