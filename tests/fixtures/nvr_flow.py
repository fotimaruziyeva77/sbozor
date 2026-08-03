"""Admin qo'lidan boshlanadigan NVR zanjiri — IKKI test moduli uchun BITTA nusxa.

=============================================================================
NEGA ALOHIDA MODUL, HAR FAYLDA O'Z NUSXASI EMAS.

Zanjir — «forma -> saqlash -> kashfiyot jobi -> poll -> kameralar ro'yxati»
— endi IKKI joyda kesib o'tiladi:

  * `tests/integration/test_phase3_criteria.py` — SC#1, SC#2, SC#7; zanjir
    jonli ko'rish CHIPTASIDA tugaydi va go2rtc MOCK bilan almashtiriladi;
  * `tests/integration/test_live_view_e2e.py`  — zanjir KADR kelganda
    tugaydi va birorta mock ishlatilmaydi.

Ikki nusxa jimgina AJRALIB KETARDI. Eng ehtimolli shakl: biri `run_id` ning
API'dan jobga uzatilishini tekshiradi, ikkinchisi esa `discover_nvr` ni
to'g'ridan-to'g'ri chaqiradi — o'shanda mock'siz o'lchov mahsulot
zanjirining BOSHQA, yumshoqroq variantini kesib o'tgan bo'lardi va uning
«uchidan-uchiga» da'vosi zaiflashardi. Bitta nusxa buni tuzilma
darajasida yopadi.

⚠ FIXTURE'LAR BU YERDA EMAS, `tests/integration/conftest.py` DA. Bu paket —
  MA'LUMOT va ZANJIR fabrikasi; conftest esa fixture REYESTRI
  (`tests/fixtures/__init__.py` da o'rnatilgan va butun repoda amal
  qiladigan qoida).

⚠ BU FAYLDA RTSP SXEMASINING LITERALI YOZILMAYDI. `test_phase3_criteria.py`
  ning SC#1 usul qulfi O'Z faylini skanerlaydi, ya'ni bu yerdagi literal
  darvozadan o'tib ketardi — lekin «qo'lda birorta RTSP URL yozilmaydi»
  da'vosi baribir buzilardi, chunki zanjirning O'ZI shu yerda yashaydi.
=============================================================================
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.jobs.discovery import discover_nvr

from fixtures.nvr_domain import CLEANUP_ORDER

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fastapi import FastAPI
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = [
    "CAMERAS_URL",
    "NVR_URL",
    "cleanup_api_nvr_rows",
    "create_device",
    "list_cameras",
    "record_enqueue",
    "run_discovery",
]

NVR_URL = "/api/v1/nvr-devices"
CAMERAS_URL = "/api/v1/cameras"


async def create_device(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    address: str,
    credentials: tuple[str, str],
) -> dict[str, Any]:
    """«Forma» — ADMIN YUBORADIGAN YAGONA UCH MAYDON.

    Tana shu yerda quriladi va uning kalitlari ALOHIDA assert bilan
    tekshiriladi: SC#1 «faqat manzil + login/parol» deydi, ya'ni to'rtinchi
    maydonning paydo bo'lishi mezonning buzilishi bo'lardi.
    """
    username, password = credentials
    payload = {"address": address, "username": username, "password": password}
    assert set(payload) == {"address", "username", "password"}, (
        f"forma tanasida ortiqcha maydon bor: {sorted(payload)} — SC#1 «FAQAT "
        "NVR manzili + login/parol» deydi"
    )
    response = await client.post(NVR_URL, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def run_discovery(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    nvr_id: UUID,
    enqueued_calls: list[dict[str, Any]],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> dict[str, Any]:
    """202 -> (worker) -> poll — MAHSULOT ZANJIRINING O'ZI.

    Uch bo'g'in ham bu yerda: HTTP tugmasi, fon vazifasi va poll javobi.
    Ularni ajratib olish (masalan `discover_nvr` ni to'g'ridan-to'g'ri
    chaqirish) `run_id` ning API'dan jobga UZATILISHINI sinovdan chiqarib
    yuborardi — aynan zanjirning eng nozik bo'g'ini.
    """
    started = await client.post(f"{NVR_URL}/{nvr_id}/discover", headers=headers)
    assert started.status_code == 202, started.text
    run_id = UUID(started.json()["run_id"])

    assert len(enqueued_calls) == 1, f"navbatga aynan bitta xabar kutilgan edi: {enqueued_calls}"
    message = enqueued_calls.pop()
    assert message["run_id"] == run_id, (
        f"navbatdagi `run_id` ({message['run_id']}) javobdagidan ({run_id}) FARQ QILADI — "
        "poll qiladigan mijoz boshqa yugurishni kuzatardi"
    )
    await discover_nvr(sessionmaker, **message)

    polled = await client.get(f"{NVR_URL}/{nvr_id}/discovery-runs/{run_id}", headers=headers)
    assert polled.status_code == 200, polled.text
    run: dict[str, Any] = polled.json()
    return run


async def list_cameras(
    client: httpx.AsyncClient, headers: dict[str, str], nvr_id: UUID
) -> list[dict[str, Any]]:
    """Kameralar reestri — kashfiyot YARATGAN qatorlar."""
    response = await client.get(CAMERAS_URL, params={"nvr_id": str(nvr_id)}, headers=headers)
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


@contextmanager
def record_enqueue(api_app: FastAPI) -> Iterator[list[dict[str, Any]]]:
    """Navbatga qo'yishni YOZIB OLADI — job javobdan KEYIN chaqiriladi.

    ⚠ JOB SO'ROV ICHIDA BAJARILMAYDI VA BU ATAYIN. `POST /discover`
      `queued` qatorini o'z tranzaksiyasida yozadi va u javob
      qaytarilgandagina COMMIT bo'ladi. Jobni so'rov ichida chaqirish
      boshqa ulanishdan hali ko'rinmaydigan qatorni o'qishga urinardi —
      ya'ni test HAQIQIY navbat semantikasidan (worker xabarni commitdan
      keyin oladi) chetga chiqib, o'zi yaratgan poygani o'lchagan bo'lardi.

    ⚠ TOZALASH MAJBURIY: `api_app` — modul darajasidagi YAGONA obyekt,
      qoldirilgan atribut boshqa test modullariga sizib o'tardi (03-06
      Issue 2).
    """
    calls: list[dict[str, Any]] = []

    async def _record(**kwargs: Any) -> None:
        calls.append(kwargs)

    api_app.state.enqueue_discovery = _record
    try:
        yield calls
    finally:
        del api_app.state.enqueue_discovery


def cleanup_api_nvr_rows(conn: Connection[TupleRow], market_ids: list[str]) -> None:
    """API orqali YARATILGAN NVR qatorlarini o'chiradi.

    ⚠ USIZ `cleanup_two_markets()` YIQILADI: u `DELETE FROM markets` bilan
      tugaydi, `nvr_devices` esa `markets` ga chet el kaliti bilan tayanadi.
      Ya'ni bu qulaylik emas — usiz zanjirni kesib o'tadigan har bir fayl
      birinchi testdan keyin bazani buzilgan holatda qoldirardi.

    Tozalash `fixtures.nvr_domain.cleanup_nvr_domain` bilan BIR XIL tartibda
    (`CLEANUP_ORDER`): tartib bu yerda QAYTA YOZILMAYDI, aks holda yangi
    jadval qo'shilganda ikki ro'yxat jimgina ajralib ketardi.
    """
    for table in CLEANUP_ORDER:
        # Jadval nomlari sobit ro'yxatdan keladi — tashqi kirish emas
        # (`fixtures/nvr_domain.py::cleanup_nvr_domain` bilan bir xil naqsh).
        conn.execute(
            f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
            (market_ids,),
        )
