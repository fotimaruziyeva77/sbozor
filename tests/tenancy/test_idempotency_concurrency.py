"""A1 O'LCHOVI — parallel get-or-create oynasi READ COMMITTED ostida (G-12, D-21).

=============================================================================
BU FAYL BIRORTA XULQNI HIMOYA QILMAYDI — U BITTA SAVOLGA JAVOB O'LCHAYDI.

D-21 kassir uchun bitta va'da beradi: *takror so'rov O'SHA to'lovni **200**
bilan qaytaradi, 409 emas* — tarmoq uzilishida qayta yuborish kassir uchun
KO'RINMAS bo'lishi kerak. Va'daning mexanizmi:

    payments  UNIQUE (market_id, idempotency_key)          <- qulf
    payment_repo  INSERT ... ON CONFLICT DO NOTHING RETURNING id
                  natija `None` bo'lsa -> ALOHIDA `SELECT ... WHERE key`

⛔ IKKINCHI BAYONOT MAJBURIY VA BU O'LCHANGAN FAKT EMAS, HUJJAT FAKTI:
   `ON CONFLICT DO NOTHING ... RETURNING` konfliktda HECH NIMA qaytaradi
   (`06-PATTERNS.md` §7 Gotcha 5). Repoda bu shaklning ikkinchi yarmi
   BIRORTA joyda yo'q (`06-PATTERNS.md` §5.1): `capture_repo.py:292-294`
   `RETURNING` ni oladi, lekin QAYTA O'QIMAYDI.

⚠ SAVOL — IKKINCHI BAYONOTNING KO'RISHI. READ COMMITTED har BAYONOT
  uchun yangi snapshot oladi, ya'ni yutqazgan sessiya konflikt qulfini
  kutib bo'lgach, keyingi bayonotida yutgan qatorni ko'rishi KERAK. Lekin
  bu PostgreSQL hujjatida shu SHAKL uchun ochiq yozilmagan (06-RESEARCH
  §Assumptions Log A1 uni `[ASSUMED]` deb belgilagan), o'lchash esa arzon.

⚠ NEGA MIGRATSIYADAN OLDIN. Javob `payment_repo` NING SHAKLINI belgilaydi:
  `False` chiqsa `IntegrityError` + `SAVEPOINT` yo'li (`nvr_repo.py:506-532`
  + `03-06` ning `begin_nested` darsi) MAJBURIY bo'ladi va u 06-09 ning
  KIRISH SHARTI. Buni `0020` yozilgandan keyin bilib olish repozitoriyni
  qayta yozish demakdir — shuning uchun zond Wave 0 da (A1 / G-12).

⛔ ZOND JAVOBI `False` CHIQSA HAM BU FAYL YASHIL QOLADI. Uning maqsadi
  «yashil» emas, O'LCHOV: natija `IDEMPOTENT_GET_OR_CREATE_SUPPORTED`
  markeriga yoziladi va testlar markerni O'LCHOV bilan solishtiradi.
  Qo'lda `True` yozib qo'yish shu solishtiruv tufayli IMKONSIZ.
=============================================================================
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final
from uuid import UUID, uuid4

import pytest
from fixtures.idempotency_probe import (
    COUNT_BY_KEY,
    CTE_UNION_ALL,
    INSERT_ON_CONFLICT,
    SELECT_BACKEND_PID,
    SELECT_BY_KEY,
    SELECT_WAIT_EVENT_TYPE,
    SHOW_ISOLATION,
    IdempotencyProbe,
    create_idempotency_probe,
    drop_idempotency_probe,
)
from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.db import make_sessionmaker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from migrations.entities import (
    IDEMPOTENT_GET_OR_CREATE_MEASURED_AT,
    IDEMPOTENT_GET_OR_CREATE_SUPPORTED,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

pytestmark = pytest.mark.tenancy

EXPECTED_ISOLATION: Final[str] = "read committed"
"""⛔ IZOLYATSIYA DARAJASI DA'VONING SHARTI, FON EMAS.

`REPEATABLE READ` ga o'tilsa ikkinchi bayonot O'Z TRANZAKSIYASI boshidagi
snapshotni ko'rar va yutgan qatorni TOPMASDI — ya'ni D-21 JIMGINA
buzilardi va sabab `payment_repo` da emas, engine sozlamasida bo'lardi.
"""

SAVEPOINT_FALLBACK: Final[str] = (
    "ZAXIRA VARIANT (D-21, 06-09 ning KIRISH SHARTI): `payment_repo` "
    "ikki bayonotli get-or-create O'RNIGA `IntegrityError` + `SAVEPOINT` "
    "(`session.begin_nested()`) yo'lidan yuradi — `nvr_repo.py:506-532` "
    "naqshi + `03-06` ning o'lchangan darsi (abort holatidagi tranzaksiya "
    "409+id ni 500 ga aylantirardi). Bu satrni `06-09` o'qiydi."
)

_LOCK_WAIT_TIMEOUT_S: Final[float] = 10.0
_LOCK_POLL_INTERVAL_S: Final[float] = 0.05


@dataclass(frozen=True)
class ProbeKey:
    """Bitta o'lchovning `(market_id, idempotency_key)` juftligi.

    Har test YANGI juftlik oladi: zond jadvali test doirasida qayta
    yaratilsa ham, umumiy kalit testlarni bir-biriga bog'lab qo'yardi va
    nosozlik «flaky» bo'lib ko'rinardi.
    """

    market_id: UUID
    idempotency_key: str

    def params(self, amount_soum: int = 15_000) -> dict[str, object]:
        return {
            "market_id": self.market_id,
            "idempotency_key": self.idempotency_key,
            "amount_soum": amount_soum,
        }


@dataclass(frozen=True)
class GetOrCreateOutcome:
    """Bitta korutinaning get-or-create natijasi — IKKI YARIM ham kerak.

    `row_id` yolg'iz o'zi «ikkalasi bir xil javob oldi» ni ko'rsatadi,
    lekin `inserted` bo'lmasa BIR MARTA yozilgani ko'rinmasdi: ikkala
    korutina ham `inserted=True` bo'lsa `UNIQUE` umuman ishlamagan
    bo'lardi va sanoq baribir 1 chiqishi mumkin edi (masalan biri
    rollback bo'lsa).
    """

    row_id: UUID | None
    inserted: bool
    isolation: str


@pytest.fixture
def probe(
    sync_owner_conn: Connection[TupleRow],
    migrated: None,
) -> Iterator[IdempotencyProbe]:
    """Zond jadvali — har testdan keyin tozalanadi (`billable_probe` naqshi)."""
    created = create_idempotency_probe(sync_owner_conn)
    try:
        yield created
    finally:
        drop_idempotency_probe(sync_owner_conn)


@pytest.fixture
async def probe_sessions(
    app_url: str,
    probe: IdempotencyProbe,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """⛔ ALOHIDA ENGINE — `app_engine` BU O'LCHOVDA ISHLATIB BO'LMAYDI.

    `tests/conftest.py::app_engine` ATAYIN `pool_size=1, max_overflow=0`
    bilan quriladi (GUC sizishini ochib berish uchun). Bitta ulanishli
    pulda ikki korutina KETMA-KET yugurardi: birinchisi ulanishni
    bo'shatmaguncha ikkinchisi umuman boshlanmasdi, ya'ni POYGA HECH
    QACHON YUZ BERMASDI va zond «hammasi joyida» degan BO'SH javob
    berardi. Shuning uchun bu yerda o'z engine'i — uch mustaqil ulanish
    (yozuvchi, raqib, kuzatuvchi) bir vaqtda kerak.

    Rol baribir `sbozor_app`: o'lchov ilova roli ko'radigan xulq haqida.
    """
    engine = create_async_engine(app_url, pool_size=5, max_overflow=0)
    try:
        yield make_sessionmaker(engine)
    finally:
        await engine.dispose()


@pytest.fixture
def probe_key() -> ProbeKey:
    return ProbeKey(market_id=uuid4(), idempotency_key=f"probe-{uuid4()}")


async def _get_or_create(
    sessionmaker: async_sessionmaker[AsyncSession],
    key: ProbeKey,
    barrier: asyncio.Barrier,
) -> GetOrCreateOutcome:
    """⛔ `payment_repo` NING KUTILAYOTGAN SHAKLI — AYNAN BITTA TRANZAKSIYADA.

    «Commit qilib, keyin o'qiymiz» varianti ATAYIN o'lchanmaydi: HTTP
    so'rovi bitta tranzaksiya ichida yopiladi va ikkinchi bayonot o'sha
    tranzaksiyada bajariladi. Zond mahsulot shaklini o'lchashi kerak,
    qulayroq shaklni emas.

    `barrier` ikkala korutinani AYNI nuqtaga olib keladi. Usiz
    `asyncio.gather` birinchi korutinani to'liq bajarib, ikkinchisini
    keyin boshlashi mumkin edi — natija bir xil bo'lardi, lekin u
    KETMA-KET holatning natijasi bo'lardi va zond hech nimani
    o'lchamasdi.
    """
    async with sessionmaker() as session, session.begin():
        isolation = (await session.execute(text(SHOW_ISOLATION))).scalar_one()

        await barrier.wait()

        inserted = (
            await session.execute(text(INSERT_ON_CONFLICT), key.params())
        ).scalar_one_or_none()
        if inserted is not None:
            return GetOrCreateOutcome(row_id=inserted, inserted=True, isolation=str(isolation))

        existing = (await session.execute(text(SELECT_BY_KEY), key.params())).scalar_one_or_none()
        return GetOrCreateOutcome(row_id=existing, inserted=False, isolation=str(isolation))


async def _wait_until_lock_blocked(
    sessionmaker: async_sessionmaker[AsyncSession],
    pid: int,
) -> None:
    """Berilgan backend `Lock` kutayotganini KUTADI — `sleep()` bilan TAXMIN QILMAYDI.

    Qat'iy `asyncio.sleep(0.2)` yozish vasvasasi aniq va u rad etiladi:
    sekin xostda raqib hali qulfga yetmagan bo'lardi, `holder.commit()`
    esa allaqachon bo'lib o'tardi — va o'lchov «CTE qatorni KO'RDI»
    degan TESKARI natija berardi. Ya'ni flaky test emas, YOLG'ON javob.
    """
    deadline = asyncio.get_running_loop().time() + _LOCK_WAIT_TIMEOUT_S
    seen: str | None = None
    while asyncio.get_running_loop().time() < deadline:
        async with sessionmaker() as watcher:
            seen = (
                await watcher.execute(text(SELECT_WAIT_EVENT_TYPE), {"pid": pid})
            ).scalar_one_or_none()
        if seen == "Lock":
            return
        await asyncio.sleep(_LOCK_POLL_INTERVAL_S)

    pytest.fail(
        f"raqib backend (pid={pid}) {_LOCK_WAIT_TIMEOUT_S} s ichida qulfga "
        f"kirmadi (oxirgi `wait_event_type` = {seen!r}). Bu o'lchov natijasi "
        "EMAS — bu zond uskunasining nosozligi: `pg_stat_activity` ustunlari "
        "faqat AYNI ROL backendlari uchun ko'rinadi, ya'ni kuzatuvchi sessiya "
        "ham `sbozor_app` bilan ulangan bo'lishi shart."
    )


# ===========================================================================
# 1-O'LCHOV — Gotcha 5 ning XULQIY isboti
# ===========================================================================


async def test_conflict_returns_no_row(
    probe_sessions: async_sessionmaker[AsyncSession],
    probe_key: ProbeKey,
) -> None:
    """`ON CONFLICT DO NOTHING ... RETURNING` konfliktda HECH NIMA qaytaradi.

    Bugun repoda bu fakt HECH QAYERDA yozilmagan: `capture_repo.py`
    `RETURNING status` ni oladi, lekin bo'sh natijaning MA'NOSINI
    o'lchamaydi. Usiz 06-09 «`None` — bu xato» deb o'ylab, D-21 ni
    to'g'ridan-to'g'ri buzardi (Pitfall 3).

    ⚠ IKKALA `INSERT` HAM BITTA SESSIYADA: bu yerda poyga YO'Q va u
      kerak emas — o'lchanayotgan narsa `RETURNING` ning konfliktdagi
      qiymati, konkurentlik emas. Poyga 2-o'lchovda.
    """
    async with probe_sessions() as session, session.begin():
        first = (
            await session.execute(text(INSERT_ON_CONFLICT), probe_key.params())
        ).scalar_one_or_none()
        assert first is not None, (
            "birinchi `INSERT` qator qaytarmadi — zond uskunasi buzuq "
            "(bo'sh jadvalda konflikt bo'lishi mumkin emas)"
        )

        second = (
            await session.execute(text(INSERT_ON_CONFLICT), probe_key.params())
        ).scalar_one_or_none()

    assert second is None, (
        f"konfliktdagi `RETURNING` qator QAYTARDI: {second!r}. Kutilgani — "
        "`None`. Agar PostgreSQL bu shaklda qator qaytaradigan bo'lsa, "
        "get-or-create uchun ikkinchi bayonot KERAK EMAS va 06-09 ni "
        "soddalashtirish mumkin."
    )


# ===========================================================================
# 2-O'LCHOV — ZONDNING ASOSIY SAVOLI (A1 / G-12)
# ===========================================================================


async def test_second_statement_sees_the_winner(
    probe_sessions: async_sessionmaker[AsyncSession],
    probe_key: ProbeKey,
    probe: IdempotencyProbe,
) -> None:
    """⚠ BU O'LCHOV — A1 ning yagona savoli va D-21 ning shartи.

    Ikki MUSTAQIL sessiya bir xil `idempotency_key` bilan `asyncio.gather`
    ostida yozadi. Yutqazgan sessiya AYNI tranzaksiyasida alohida `SELECT`
    bajaradi. Uchta da'vo, uchalasi ham kerak:

      (a) jadvalda AYNAN 1 qator — `UNIQUE` ishladi;
      (b) ikkala korutina ham BIR XIL `id` oldi — D-21 ning «o'sha
          to'lovni qaytaradi» qismi;
      (c) birorta korutina istisno KO'TARMADI — 409/500 yo'li ochilmadi.

    Natija `IDEMPOTENT_GET_OR_CREATE_SUPPORTED` markeri bilan
    solishtiriladi: marker o'lchovdan AJRALIB KETA OLMAYDI.
    """
    barrier = asyncio.Barrier(2)
    outcomes = await asyncio.gather(
        _get_or_create(probe_sessions, probe_key, barrier),
        _get_or_create(probe_sessions, probe_key, barrier),
        return_exceptions=True,
    )

    failures = [item for item in outcomes if isinstance(item, BaseException)]
    results = [item for item in outcomes if isinstance(item, GetOrCreateOutcome)]

    async with probe_sessions() as session:
        stored = (await session.execute(text(COUNT_BY_KEY), probe_key.params())).scalar_one()

    returned_ids = [item.row_id for item in results]
    measured = (
        not failures
        and stored == 1
        and len(returned_ids) == 2
        and None not in returned_ids
        and len(set(returned_ids)) == 1
        and sum(1 for item in results if item.inserted) == 1
    )

    # --- Markerning o'lchovdan ajralib keta olmasligi ---
    assert IDEMPOTENT_GET_OR_CREATE_SUPPORTED is measured, (
        f"marker (`IDEMPOTENT_GET_OR_CREATE_SUPPORTED = "
        f"{IDEMPOTENT_GET_OR_CREATE_SUPPORTED}`) O'LCHOV natijasidan "
        f"({measured}) ajralib ketdi.\n"
        f"O'lchov sanasi markerda: {IDEMPOTENT_GET_OR_CREATE_MEASURED_AT}\n"
        f"PostgreSQL: {probe.server_version}\n"
        f"Istisnolar: {failures}\n"
        f"Qaytgan id'lar: {returned_ids}\n"
        f"Jadvaldagi qator: {stored}\n\n" + SAVEPOINT_FALLBACK
    )

    # --- Izolyatsiya darajasi — DA'VONING SHARTI ---
    for item in results:
        assert item.isolation == EXPECTED_ISOLATION, (
            f"tranzaksiya izolyatsiyasi {item.isolation!r}, kutilgani "
            f"{EXPECTED_ISOLATION!r}. Bu naqsh har-BAYONOT snapshotiga "
            "tayanadi; boshqa darajada ikkinchi `SELECT` yutgan qatorni "
            "KO'RMASDI va D-21 jimgina buzilardi."
        )

    # --- Mazmun (marker `True` bo'lgan holat) ---
    if IDEMPOTENT_GET_OR_CREATE_SUPPORTED:
        assert not failures, f"korutina istisno ko'tardi: {failures}"
        assert stored == 1, f"jadvalda {stored} qator — `UNIQUE` ishlamadi"
        assert len(set(returned_ids)) == 1, (
            f"ikki korutina IKKI XIL javob oldi: {returned_ids}. D-21 "
            "«takror so'rov o'sha to'lovni qaytaradi» deydi."
        )
        assert sum(1 for item in results if item.inserted) == 1, (
            "AYNAN bitta korutina yozgan bo'lishi kerak, ikkinchisi esa "
            f"qayta o'qigan: {[item.inserted for item in results]}"
        )


# ===========================================================================
# 3-O'LCHOV — «ikki bayonot ortiqcha emasmi?» savolining NAZORATI
# ===========================================================================


async def test_cte_union_all_shape_is_rejected(
    probe_sessions: async_sessionmaker[AsyncSession],
    probe_key: ProbeKey,
) -> None:
    """⛔ BIR BAYONOTLI CTE SHAKLI PARALLEL YOZILGAN QATORNI TOPMAYDI.

    Vasvasa aniq: `WITH ins AS (INSERT ... RETURNING id) SELECT id FROM ins
    UNION ALL SELECT id FROM ...` — bitta bayonot, bitta round-trip.
    Ketma-ket holatda u ISHLAYDI, ya'ni testsiz u to'g'ri ko'rinadi.

    Interleaving ATAYIN determinlashtirilgan (`sleep` bilan taxmin
    qilinmaydi):

      1. `holder` qatorni yozadi va tranzaksiyani OCHIQ qoldiradi;
      2. `challenger` CTE ni yuboradi -> u `holder` ning qulfida qotadi;
      3. `holder` COMMIT qiladi -> `challenger` ning `INSERT` i
         `DO NOTHING` bilan tugaydi;
      4. CTE ning `SELECT` qismi esa BAYONOT snapshotini ko'radi —
         snapshot 2-qadamda olingan, ya'ni commit'dan OLDIN.

    Natija: bo'sh javob. Va aynan shu sabab ikkinchi ALOHIDA bayonot
    (yangi snapshot bilan) MAJBURIY — bu testning ikkinchi yarmi buni
    NAZORAT sifatida ko'rsatadi.
    """
    async with probe_sessions() as holder, probe_sessions() as challenger:
        await holder.execute(text(INSERT_ON_CONFLICT), probe_key.params())

        pid = (await challenger.execute(text(SELECT_BACKEND_PID))).scalar_one()
        task = asyncio.create_task(challenger.execute(text(CTE_UNION_ALL), probe_key.params()))
        try:
            await _wait_until_lock_blocked(probe_sessions, int(pid))
            await holder.commit()
            blind = (await task).scalars().all()
        finally:
            if not task.done():
                task.cancel()

        assert list(blind) == [], (
            f"bir bayonotli CTE shakli parallel yozilgan qatorni TOPDI: "
            f"{list(blind)!r}. Bu KUTILMAGAN natija — u holda 06-09 "
            "get-or-create ni bitta bayonotga siqishi mumkin va ikkinchi "
            "`SELECT` ortiqcha bo'lardi."
        )

        # NAZORAT: ALOHIDA bayonot (yangi snapshot) yutgan qatorni KO'RADI.
        seen = (await challenger.execute(text(SELECT_BY_KEY), probe_key.params())).scalars().all()
        await challenger.rollback()

    assert len(list(seen)) == 1, (
        f"alohida `SELECT` ham qatorni ko'rmadi ({list(seen)!r}) — bu 2-o'lchov "
        "bilan ZID va u holda `IDEMPOTENT_GET_OR_CREATE_SUPPORTED` "
        "o'lchovining o'zi qayta ko'rib chiqilishi kerak.\n\n" + SAVEPOINT_FALLBACK
    )
