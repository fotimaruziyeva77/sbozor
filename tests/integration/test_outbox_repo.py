"""`outbox_repo` — idempotentlik, ijara, quiet-hours darvozasi va append-only.

=============================================================================
BU FAYL 07-04 NING SXEMA DARVOZALARINING O'RNINI BOSMAYDI — USTIGA QURILADI.

`tests/tenancy/test_notification_domain_meta.py` SXEMA darajasida
isbotlaydi: `UNIQUE (market_id, dedupe_key)` bazada MAVJUD va taqiqlangan
ustunlar YO'Q. Bu yerdagi savol boshqa — **ILOVA o'sha cheklovlardan qanday
foydalanadi**: ikkinchi `enqueue()` HAQIQATAN `None` qaytaradimi, ikki
parallel `claim()` bir qatorni ikki marta beradimi, quiet oyna ichida
kvitansiya HAQIQATAN o'tadimi.

⛔ BAZA HAQIQIY (`postgres:18.4`) VA BU MAJBURIY: `SKIP LOCKED`, qisman
   UNIQUE indeks, `LEFT JOIN` + `COALESCE` va `AT TIME ZONE` — hammasi
   FAQAT Postgres'da mavjud. Mock ostida o'lchash «navbat ishlayapti»
   degan yolg'on ishonch berardi.
=============================================================================

=============================================================================
⛔⛔ VAQT SILJITILMAYDI — U ARGUMENT (`claim(..., now=...)`).

Quiet-hours darvozasi aynan `now` ga qaraydi, ya'ni «22:30 da nima
bo'ladi?» savoli soatni almashtirmasdan, `freezegun`siz va yangi
bog'liqliksiz o'lchanadi (`alert_sweep(..., now=...)` bilan aynan bir xil
qaror).
=============================================================================

⛔ IKKI QATLAM SOLISHTIRILADI: quiet-hours qoidasi SQL da (darvoza) va
  `notification_meta.is_quiet_now()` da (spetsifikatsiya) yozilgan.
  `test_the_sql_gate_agrees_with_the_specification` ularni HAR BIR o'lchov
  nuqtasida taqqoslaydi — ajralish jimgina emas, QIZIL bo'ladi.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from app.jobs.notification_meta import (
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    is_suppressed_now,
    outbox_payload,
)
from app.repositories import outbox_repo
from app.repositories.outbox_repo import RecipientMismatch
from fixtures.notification_domain import (
    cleanup_notification_domain,
    seed_binding,
    seed_notification_settings,
    seed_outbox_row,
)
from sbozor_core.db import make_sessionmaker
from sbozor_core.enums import OutboxKind, OutboxRecipientKind, OutboxStatus
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import MARKET_TZ
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from fixtures import TenantSessionFactory
    from fixtures.market_domain import MarketDomainSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

RECEIPT = OutboxKind.PAYMENT_RECEIPT.value
OVERDUE = OutboxKind.OVERDUE_REMINDER.value
VENDOR = OutboxRecipientKind.VENDOR.value
DIRECTOR = OutboxRecipientKind.MARKET_DIRECTOR.value

LEASE = 120
"""Ijara muddati — sekundlarda. Qiymat testning O'ZIDA, sozlamada emas:
repozitoriy uni ARGUMENT sifatida oladi (`capture_repo` bilan bir xil qoida).
"""

QUIET_MOMENT = datetime(2026, 8, 12, 22, 30, tzinfo=MARKET_TZ)
"""⛔ D-18 NING O'LCHOV NUQTASI — standart oyna (21:00-08:00) ICHIDA.

Sana QOTIRILGAN va bu xavfsiz: `claim()` ning butun arifmetikasi `now`
argumentiga qaraydi, ya'ni test kalendarga umuman bog'liq emas.
"""

LOUD_MOMENT = datetime(2026, 8, 12, 9, 0, tzinfo=MARKET_TZ)
"""Oynadan TASHQARIDAGI payt — `COALESCE` ning nazorat o'lchovi.

⛔ USIZ «SOZLAMASIZ BOZOR» TESTI HECH NIMANI ISBOTLAMASDI. `COALESCE`
   olib tashlansa `quiet_start` `NULL` bo'lardi, `CASE` `NULL` qaytarardi,
   `NOT NULL` ham `NULL` — ya'ni qator `WHERE` dan CHIQIB ketardi. Quiet
   oyna ICHIDA bu «to'g'ri» natija bilan bir xil ko'rinadi; oynadan
   TASHQARIDA esa farq ochiladi: `COALESCE` bilan qator OLINADI, usiz —
   YO'Q.
"""


@pytest.fixture
def bed(
    sync_owner_conn: Connection[TupleRow],
    market_domain: MarketDomainSeed,
) -> Iterator[MarketDomainSeed]:
    """Domen qatlami + KAFOLATLANGAN tozalash.

    ⚠ `market_domain` ARGUMENT sifatida olinadi, faqat «oldin ishlasin»
      uchun emas: pytest fixture'larni TESKARI tartibda yopadi, ya'ni
      bildirishnoma qatorlari sotuvchilar va bozorlar o'chirilishidan
      OLDIN tozalanadi. Teskari holatda kompozit FK buzilardi.
    """
    try:
        yield market_domain
    finally:
        cleanup_notification_domain(sync_owner_conn, market_ids=list(market_domain.market_ids))


@pytest.fixture
async def duo_sessionmaker(
    app_url: str,
    _bootstrap_roles: None,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """IKKI ulanishli O'Z engine'i — parallel `claim()` testi uchun.

    ⚠ `app_engine` BU YERDA ISHLAMAYDI: u `pool_size=1, max_overflow=0`
      bilan qurilgan (GUC sizishini ochib berish uchun). `SKIP LOCKED`
      o'lchovi esa AYNAN IKKI OCHIQ tranzaksiyani talab qiladi — bitta
      ulanish bilan ikkinchi sessiya poolda kutib qolardi va test qulfni
      emas, pool chegarasini o'lchagan bo'lardi (`test_capture_repo.py`
      dagi jufti bilan bir xil qaror).
    """
    engine = create_async_engine(app_url, pool_size=2, max_overflow=0)
    try:
        yield make_sessionmaker(engine)
    finally:
        await engine.dispose()


def _count(conn: Connection[TupleRow], market_id: UUID) -> int:
    row = conn.execute(
        "SELECT count(*) FROM notification_outbox WHERE market_id = %s", (str(market_id),)
    ).fetchone()
    assert row is not None
    return int(row[0])


def _row(conn: Connection[TupleRow], outbox_id: UUID) -> dict[str, object]:
    row = conn.execute(
        "SELECT status, attempt_count, lease_until, provider_message_id, last_error_type, "
        "last_status_code, next_attempt_at FROM notification_outbox WHERE id = %s",
        (str(outbox_id),),
    ).fetchone()
    assert row is not None, f"qator YO'QOLDI: {outbox_id} — D-20 append-only buzilgan"
    return {
        "status": row[0],
        "attempt_count": row[1],
        "lease_until": row[2],
        "provider_message_id": row[3],
        "last_error_type": row[4],
        "last_status_code": row[5],
        "next_attempt_at": row[6],
    }


def _created_at(conn: Connection[TupleRow], outbox_id: UUID) -> datetime:
    """Qatorning `created_at` i — ⛔ `OutboxClaim` ning YOSH CHEGARASI uchun.

    `_settle()` manzilsiz qatorni AYNAN shu qiymatga qarab terminal holatga
    chiqaradi (`UNRESOLVED_MAX_AGE_HOURS`), ya'ni `claim()` uni qatordan
    OLIB CHIQISHI shart. Tikning `now` i bu savolga javob bera olmasdi: u
    «hozir soat nechi» ni biladi, «bu qator qachon tug'ilgan» ni emas.
    """
    row = conn.execute(
        "SELECT created_at FROM notification_outbox WHERE id = %s", (str(outbox_id),)
    ).fetchone()
    assert row is not None, f"qator YO'QOLDI: {outbox_id}"
    created_at = row[0]
    assert isinstance(created_at, datetime)
    return created_at


def _set_quiet_window(conn: Connection[TupleRow], market_id: UUID, *, start: str, end: str) -> None:
    """Sozlama qatoriga BOSHQA oyna yozadi (fixture ATAYIN bermaydi).

    `seed_notification_settings()` `quiet_hours_*` ni argument qilmaydi va
    sabab uning docstringida: fixture mahsulot standartini qayta yozsa
    testlar standartning O'ZINI emas, fixture nusxasini o'lchardi. Bu yerda
    esa o'lchanadigan narsa boshqa: BOZOR QATORI standartdan USTUN
    kelishi. Shuning uchun qiymat testning O'ZIDA turadi.
    """
    conn.execute(
        "UPDATE market_notification_settings SET quiet_hours_start = %s, quiet_hours_end = %s "
        "WHERE market_id = %s",
        (start, end, str(market_id)),
    )


# ---------------------------------------------------------------------------
# 1. `enqueue` — D-21 ning STRUKTURAVIY idempotentligi
# ---------------------------------------------------------------------------


async def test_a_repeated_enqueue_writes_no_second_row(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ D-21 — takroriy niyat IKKINCHI qator BERMAYDI va bu XATO EMAS.

    Bir to'lov uchun ikki kvitansiya 6-fazaning T-06-49 bilan AYNAN bir
    sinfdagi xato bo'lardi. Himoya ILOVA SHARTIDA emas,
    `uq_notification_outbox_market_id_dedupe_key` CHEKLOVIDA — ya'ni ikki
    parallel `POST /payments` ham ikkinchi xabarni yoza olmaydi.
    """
    market = bed.market_a
    dedupe_key = f"receipt:{uuid4()}"
    payload = outbox_payload(RECEIPT, amount_soum=15_000, stall_code=market.stall_codes[0])

    async with tenant_session(market.market_id) as session:
        first = await outbox_repo.enqueue(
            session,
            market_id=market.market_id,
            kind=RECEIPT,
            recipient_kind=VENDOR,
            vendor_id=market.vendor_ids[0],
            dedupe_key=dedupe_key,
            payload=payload,
        )
        second = await outbox_repo.enqueue(
            session,
            market_id=market.market_id,
            kind=RECEIPT,
            recipient_kind=VENDOR,
            vendor_id=market.vendor_ids[0],
            dedupe_key=dedupe_key,
            payload=payload,
        )

    assert first is not None, "birinchi niyat yozilmadi — test o'z farazini tasdiqlamadi"
    assert second is None, (
        "takroriy `enqueue()` ikkinchi qator yozdi yoki istisno berdi — sotuvchi "
        "bir to'lov uchun IKKI kvitansiya olardi (D-21)"
    )
    assert _count(sync_owner_conn, market.market_id) == 1


async def test_enqueue_rejects_a_payload_key_outside_the_allowlist(
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ Pitfall 6 — allowlist REPO DARAJASIDA ham qo'yiladi (ikkinchi qatlam).

    Chaqiruvchi `outbox_payload()` ni unutsa ham tayyor matn bazaga
    tushmaydi: u yerdan `pg_dump` -> restic -> TASHQI BUCKET zanjiri
    ochilardi.
    """
    market = bed.market_a
    async with tenant_session(market.market_id) as session:
        with pytest.raises(ValueError, match="ruxsat etilmagan payload"):
            await outbox_repo.enqueue(
                session,
                market_id=market.market_id,
                kind=RECEIPT,
                recipient_kind=VENDOR,
                vendor_id=market.vendor_ids[0],
                dedupe_key=f"receipt:{uuid4()}",
                payload={"message_text": "Hurmatli sotuvchi, 15 000 so'm qabul qilindi"},
            )


async def test_enqueue_rejects_a_recipient_and_vendor_mismatch(
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`recipient_kind` <-> `vendor_id` juftligi IKKI TOMONLAMA majburlanadi.

    ⚠ Xato Python darajasida CHAQIRUV JOYINI ko'rsatadi;
      `ck_notification_outbox_recipient_matches_vendor` esa uni baribir
      rad etardi, lekin xabar «qaysi qator» haqida bo'lardi.
    """
    market = bed.market_a
    async with tenant_session(market.market_id) as session:
        with pytest.raises(RecipientMismatch):
            await outbox_repo.enqueue(
                session,
                market_id=market.market_id,
                kind=RECEIPT,
                recipient_kind=VENDOR,
                vendor_id=None,
                dedupe_key=f"receipt:{uuid4()}",
                payload={"amount_soum": 1},
            )
        with pytest.raises(RecipientMismatch):
            await outbox_repo.enqueue(
                session,
                market_id=market.market_id,
                kind=OutboxKind.DIGEST_MORNING.value,
                recipient_kind=DIRECTOR,
                vendor_id=market.vendor_ids[0],
                dedupe_key=f"digest:{uuid4()}",
                payload={"business_date": "2026-08-12"},
            )


# ---------------------------------------------------------------------------
# 2. ⛔ D-18 — QUIET-HOURS DARVOZASI SQL DARAJASIDA
# ---------------------------------------------------------------------------


async def test_the_quiet_window_holds_the_reminder_but_never_the_receipt(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔⛔ D-18 NING SQL DARAJASIDAGI O'LCHOVI — FAZANING ENG QIMMAT DA'VOSI.

    =======================================================================
    IKKI QATOR AYNAN BIR XIL, FARQ FAQAT `kind` DA.

    Ikkalasi ham `pending`, ikkalasining ham `next_attempt_at` o'tgan,
    ikkalasi ham bir bozorda va bir vaqtda baholanadi. Shuning uchun
    natijadagi farq FAQAT quiet-hours istisnosidan kelib chiqishi mumkin.

    ⛔ Pitfall 7 aynan shu bandning unutilishini tasvirlaydi: filtr
       yoziladi, `kind` bo'yicha istisno esa UNUTILADI — va 20:00 dan
       keyin to'lagan sotuvchi kvitansiyani ERTASI KUNI olardi. Xatosiz,
       jimgina, «to'g'ri ishlagan» so'rov bilan.
    =======================================================================
    """
    market = bed.market_a
    receipt_id = seed_outbox_row(
        sync_owner_conn,
        market_id=market.market_id,
        kind=RECEIPT,
        vendor_id=market.vendor_ids[0],
        payload={"amount_soum": 15_000, "stall_code": market.stall_codes[0]},
        next_attempt_at=QUIET_MOMENT - timedelta(hours=1),
    )
    overdue_id = seed_outbox_row(
        sync_owner_conn,
        market_id=market.market_id,
        kind=OVERDUE,
        vendor_id=market.vendor_ids[0],
        payload={"overdue_days": 3},
        next_attempt_at=QUIET_MOMENT - timedelta(hours=1),
    )

    async with tenant_session(market.market_id) as session:
        claimed = await outbox_repo.claim(
            session,
            market_id=market.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=QUIET_MOMENT,
        )

    claimed_ids = {row.id for row in claimed}
    assert receipt_id in claimed_ids, (
        "⛔ D-18 BUZILDI: kvitansiya quiet oyna ichida USHLAB QOLINDI. Sotuvchi "
        "hozirgina to'lagan pulining tasdig'ini ERTAGA olardi va nizo modelining "
        "(D-02) butun asosi yo'qolardi."
    )
    assert overdue_id not in claimed_ids, (
        "qarz eslatmasi quiet oyna ichida yuborildi — nazorat bandi qulab tushdi, "
        "ya'ni yuqoridagi da'vo «darvoza umuman yo'q» holatida ham yashil bo'lardi"
    )


async def test_a_market_without_a_settings_row_falls_back_to_the_code_defaults(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ `LEFT JOIN` + `COALESCE` — sozlamasiz bozor JIMGINA o'chib qolmaydi.

    =======================================================================
    ⛔⛔ NAZORAT BANDI TESTNING YURAGI — VA U OYNADAN TASHQARIDA.

    `COALESCE` olib tashlansa `quiet_start` `NULL` bo'lardi, `CASE` `NULL`
    qaytarardi va `NOT NULL` ham `NULL` — ya'ni qator `WHERE` dan CHIQIB
    ketardi. Quiet oyna ICHIDA bu «to'g'ri» natija bilan AYNAN bir xil
    ko'rinadi, ya'ni faqat 22:30 ni o'lchagan test hech nimani
    isbotlamasdi.

    Farq oynadan TASHQARIDA ochiladi: standart bilan qator OLINADI,
    `NULL` bilan esa YO'Q.
    =======================================================================

    ⚠ SOZLAMA QATORI ATAYIN YOZILMAYDI: `market_notification_settings` —
      1:1 va qator MAJBURIY EMAS (`models/notification.py`). `JOIN`
      yozilganda sozlamasiz bozorning butun navbati ko'rinmas bo'lardi.
    """
    market = bed.market_b
    quiet_id = seed_outbox_row(
        sync_owner_conn,
        market_id=market.market_id,
        kind=OVERDUE,
        vendor_id=market.vendor_ids[0],
        payload={"overdue_days": 3},
        next_attempt_at=QUIET_MOMENT - timedelta(hours=1),
    )

    async with tenant_session(market.market_id) as session:
        inside = await outbox_repo.claim(
            session,
            market_id=market.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=QUIET_MOMENT,
        )
    assert quiet_id not in {row.id for row in inside}, (
        "sozlamasiz bozorda kod standarti (21:00-08:00) qo'llanmadi — eslatma tunda ketardi"
    )

    async with tenant_session(market.market_id) as session:
        outside = await outbox_repo.claim(
            session,
            market_id=market.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=LOUD_MOMENT + timedelta(days=1),
        )
    assert quiet_id in {row.id for row in outside}, (
        "⛔ NAZORAT QULADI: sozlamasiz bozorning qatori oynadan TASHQARIDA ham "
        "olinmadi. Bu `COALESCE` ning yo'qligi belgisi — `NULL` oyna butun "
        "navbatni JIMGINA to'sib qo'yadi va bozor hech qachon xabar olmasdi."
    )


async def test_the_settings_row_overrides_the_code_default(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Bozor qatori standartdan USTUN keladi (D-19 — multi-tenant va'dasi).

    ⚠ Oyna ATAYIN yarim tunni KESMAYDI (12:00-14:00): standart shakl
      (`start > end`) bilan yozilgan implementatsiya ikkinchi shoxni
      umuman bajarmasdi va u testda hech qachon ko'rinmasdi.
    """
    market = bed.market_a
    seed_notification_settings(sync_owner_conn, market_id=market.market_id)
    _set_quiet_window(sync_owner_conn, market.market_id, start="12:00", end="14:00")

    day_moment = datetime(2026, 8, 12, 13, 0, tzinfo=MARKET_TZ)
    row_id = seed_outbox_row(
        sync_owner_conn,
        market_id=market.market_id,
        kind=OVERDUE,
        vendor_id=market.vendor_ids[0],
        payload={"overdue_days": 3},
        next_attempt_at=day_moment - timedelta(hours=2),
    )

    async with tenant_session(market.market_id) as session:
        inside = await outbox_repo.claim(
            session,
            market_id=market.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=day_moment,
        )
    assert row_id not in {row.id for row in inside}, (
        "bozorning O'Z oynasi (12:00-14:00) e'tiborga olinmadi — sozlama qatori "
        "kod standartidan ustun kelishi D-19 ning butun mazmuni"
    )

    async with tenant_session(market.market_id) as session:
        outside = await outbox_repo.claim(
            session,
            market_id=market.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=QUIET_MOMENT,
        )
    assert row_id in {row.id for row in outside}, (
        "22:30 — bozorning oynasidan TASHQARIDA, lekin qator olinmadi: demak "
        "kod standarti (21:00-08:00) sozlama qatoridan ustun keldi"
    )


async def test_the_sql_gate_agrees_with_the_specification(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ IKKI QATLAM SOLISHTIRILADI: SQL darvozasi va Python spetsifikatsiyasi.

    Qoida ikki joyda ifodalangan va bu ONGLI: darvoza SQL da bo'lishi
    SHART (oyna har bozorda, `LEFT JOIN` bilan olinadi va navbatni
    xotiraga tortib bo'lmaydi), spetsifikatsiya esa jadval testi bilan
    qulflanadi (`test_outbox_policy.py`).

    ⚠ IKKI IFODA AJRALISHI MUMKIN VA AYNAN SHU TEST BUNI TO'SADI: har bir
      o'lchov nuqtasida HAQIQIY natija `is_suppressed_now()` ning
      bashorati bilan solishtiriladi.
    """
    market = bed.market_a
    moments = (
        QUIET_MOMENT,
        LOUD_MOMENT + timedelta(days=1),
        datetime(2026, 8, 13, 2, 0, tzinfo=MARKET_TZ),
        datetime(2026, 8, 12, 20, 45, tzinfo=MARKET_TZ),
    )
    seeded = {
        kind: seed_outbox_row(
            sync_owner_conn,
            market_id=market.market_id,
            kind=kind,
            vendor_id=market.vendor_ids[0],
            payload={"amount_soum": 1} if kind == RECEIPT else {"overdue_days": 3},
            next_attempt_at=datetime(2026, 8, 12, 6, 0, tzinfo=MARKET_TZ),
        )
        for kind in (RECEIPT, OVERDUE)
    }

    for moment in moments:
        async with tenant_session(market.market_id) as session:
            claimed = {
                row.id
                for row in await outbox_repo.claim(
                    session,
                    market_id=market.market_id,
                    batch_size=50,
                    lease_seconds=LEASE,
                    now=moment,
                )
            }
        # Har o'lchovdan keyin qatorlar navbatga QAYTARILADI — aks holda
        # ikkinchi nuqta allaqachon `sent` bo'lgan qatorni ko'rmasdi va
        # taqqoslash BO'SH ROST bo'lardi.
        sync_owner_conn.execute(
            "UPDATE notification_outbox SET status = %s, lease_until = NULL WHERE market_id = %s",
            (OutboxStatus.PENDING.value, str(market.market_id)),
        )

        for kind, outbox_id in seeded.items():
            predicted = not is_suppressed_now(
                kind,
                moment=moment.timetz().replace(tzinfo=None),
                start=DEFAULT_QUIET_HOURS_START,
                end=DEFAULT_QUIET_HOURS_END,
            )
            assert (outbox_id in claimed) is predicted, (
                f"SQL darvozasi spetsifikatsiyadan ajraldi: `{kind}` @ {moment:%H:%M} "
                f"— SQL «{'oldi' if outbox_id in claimed else 'olmadi'}», "
                f"`is_suppressed_now()` esa «{'yuboriladi' if predicted else 'kutadi'}» "
                "deydi. Bir qoidaning ikki ifodasi ajralganda ular JIMGINA "
                "ajraladi va farq faqat mahsulotda ko'rinardi."
            )


# ---------------------------------------------------------------------------
# 3. Ijara va `SKIP LOCKED` — IKKI TURLI MUDDAT
# ---------------------------------------------------------------------------


async def test_two_open_transactions_never_get_the_same_row_skip_locked(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    duo_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """⛔ `FOR UPDATE ... SKIP LOCKED` — IKKI OCHIQ TRANZAKSIYADA o'lchanadi.

    =======================================================================
    ⚠ IKKINCHI SESSIYA BIRINCHISI COMMIT QILISHIDAN OLDIN chaqiriladi.

    Aks holda test qulfni emas, `status = 'pending'` predikatini o'lchagan
    bo'lardi (birinchi tranzaksiya qatorlarni allaqachon `sent` qilib
    qo'ygan bo'lardi) va `SKIP LOCKED` olib tashlanganda ham YASHIL
    qolardi. Shu sababdan `asyncio.gather` ISHLATILMAYDI: u tartibni
    kafolatlamaydi va ketma-ket bajarilgan ikki chaqiruv ham «kesishmadi»
    deb yashil bo'lardi.

    ⚠ `SET LOCAL statement_timeout` MAJBURIY va u testning IKKINCHI yarmi:
      `SKIP LOCKED` bo'lmasa ikkinchi so'rov qulf ustida ABADIY
      bloklanadi. Timeout uni `QueryCanceled` ga aylantiradi, ya'ni
      sabotaj testni OSILTIRMAYDI — aynan qizartiradi.
    =======================================================================
    """
    market = bed.market_a
    seeded = {
        seed_outbox_row(
            sync_owner_conn,
            market_id=market.market_id,
            kind=RECEIPT,
            vendor_id=market.vendor_ids[0],
            payload={"amount_soum": 1_000 + index},
            next_attempt_at=QUIET_MOMENT - timedelta(hours=1),
        )
        for index in range(4)
    }

    async with duo_sessionmaker() as first, first.begin():
        await set_tenant_context(
            first, market_id=market.market_id, actor_id=None, request_id="pytest-a"
        )
        claimed_first = await outbox_repo.claim(
            first,
            market_id=market.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=QUIET_MOMENT,
        )

        # ⚠ BIRINCHI TRANZAKSIYA HALI OCHIQ — qulflar TURIBDI.
        async with duo_sessionmaker() as second, second.begin():
            await set_tenant_context(
                second, market_id=market.market_id, actor_id=None, request_id="pytest-b"
            )
            await second.execute(text("SET LOCAL statement_timeout = '4000ms'"))
            claimed_second = await outbox_repo.claim(
                second,
                market_id=market.market_id,
                batch_size=50,
                lease_seconds=LEASE,
                now=QUIET_MOMENT,
            )

    first_ids = {row.id for row in claimed_first}
    second_ids = {row.id for row in claimed_second}
    assert seeded <= first_ids, "birinchi worker o'z partiyasini olishi shart"
    assert first_ids & second_ids == set(), (
        "bitta qator IKKI worker'ga berildi — sotuvchi bir to'lov uchun IKKI kvitansiya olardi"
    )
    assert second_ids == set()


async def test_claim_takes_a_lease_without_counting_an_attempt(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔⛔ IJARA OLINADI, URINISH ESA `claim()` DA SANALMAYDI.

    =======================================================================
    ⛔ HISOBLAGICH JO'NATISH JOYIGA KO'CHDI VA BU O'LCHANGAN TUZATISH.

    Ilgari `_CLAIM_DUE` `attempt_count` ni SHARTSIZ oshirardi — ya'ni HTTP
    so'rovi UMUMAN yuborilmagan holat (`UNRESOLVED`: sotuvchi hali botga
    ulanmagan) ham byudjetdan yechilardi. Kech ulangan sotuvchi navbatga
    ~288 «urinish» bilan kelardi va birinchi vaqtinchalik `502` uni darhol
    `failed` ga tushirardi: kvitansiya MANGU yo'qolardi, holbuki Telegram
    bilan hech qanday muammo bo'lmagan edi.

    ⚠ NAZORAT SHU YERDA: bayonot ISHLAGANI holat va ijara bilan
      isbotlanadi. Usiz «hisoblagich oshmadi» natijasi `UPDATE` umuman
      bajarilmagan holatda ham yashil bo'lardi.
    =======================================================================

    ⛔ IKKINCHI DA'VO — `created_at` CLAIMGA CHIQADI: `_settle()` manzilsiz
       qatorning YOSHINI aynan shu qiymatdan hisoblaydi. U ⛔ QATORDAN
       keladi, tikning `now` idan emas.
    """
    market = bed.market_a
    outbox_id = seed_outbox_row(
        sync_owner_conn,
        market_id=market.market_id,
        kind=RECEIPT,
        vendor_id=market.vendor_ids[0],
        payload={"amount_soum": 15_000},
        next_attempt_at=QUIET_MOMENT - timedelta(hours=1),
    )

    async with tenant_session(market.market_id) as session:
        claimed = await outbox_repo.claim(
            session,
            market_id=market.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=QUIET_MOMENT,
        )

    assert [row.id for row in claimed] == [outbox_id]
    assert claimed[0].attempt_count == 0, (
        f"`claim()` urinishni SANADI ({claimed[0].attempt_count}). Qaytarilgan son "
        "bu urinishdan OLDINGI hisob bo'lishi shart — birinchi olishda `0`"
    )
    assert claimed[0].created_at == _created_at(sync_owner_conn, outbox_id), (
        "`OutboxClaim.created_at` qatorning haqiqiy tug'ilish payti emas — yosh "
        "chegarasi (`UNRESOLVED_MAX_AGE_HOURS`) noto'g'ri qiymatdan hisoblanardi"
    )

    row = _row(sync_owner_conn, outbox_id)
    assert row["attempt_count"] == 0, (
        f"`claim()` bazadagi hisoblagichni oshirdi: {row['attempt_count']}. Urinish "
        "AYNAN jo'natish joyida (terminal yozuvchilarda) sanaladi"
    )
    # NAZORAT — bayonotning O'ZI ishladi.
    assert row["status"] == OutboxStatus.SENT.value
    assert row["lease_until"] == QUIET_MOMENT + timedelta(seconds=LEASE)


async def test_release_expired_leases_does_not_burn_an_attempt(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ IJARA `SKIP LOCKED` NING O'RNINI BOSMAYDI VA AKSINCHA.

    Worker qatorni `sent` ga o'tkazib COMMIT qilgach qulf TUSHADI. Agar u
    o'shandan keyin o'lsa, `SKIP LOCKED` hech nima qilmaydi — qator MANGU
    `sent` bo'lib qolardi va xabar hech qachon ketmasdi.

    ⛔ `attempt_count` OSHIRILMAYDI: urinish AMALDA QILINMAGAN. Oshirish
       har worker qulashini sotuvchining byudjetidan yechardi va uchta
       qayta ishga tushirish xabarni `failed` ga tushirardi — holbuki
       Telegram bilan hech qanday muammo yo'q edi.
    """
    market = bed.market_a
    outbox_id = seed_outbox_row(
        sync_owner_conn,
        market_id=market.market_id,
        kind=RECEIPT,
        vendor_id=market.vendor_ids[0],
        payload={"amount_soum": 15_000},
        status=OutboxStatus.SENT.value,
        attempt_count=1,
        next_attempt_at=QUIET_MOMENT - timedelta(hours=2),
    )
    sync_owner_conn.execute(
        "UPDATE notification_outbox SET lease_until = %s WHERE id = %s",
        (QUIET_MOMENT - timedelta(minutes=5), str(outbox_id)),
    )

    async with tenant_session(market.market_id) as session:
        released = await outbox_repo.release_expired_leases(
            session, market_id=market.market_id, now=QUIET_MOMENT
        )

    assert released == 1
    row = _row(sync_owner_conn, outbox_id)
    assert row["status"] == OutboxStatus.PENDING.value
    assert row["lease_until"] is None
    assert row["attempt_count"] == 1, (
        "ijara qaytarilganda urinish SANALDI — worker qulashi sotuvchining byudjetidan yechildi"
    )


# ---------------------------------------------------------------------------
# 4. ⛔ D-20 — APPEND-ONLY VA D-04 — SIRSIZ XATO TURI
# ---------------------------------------------------------------------------


async def test_every_terminal_transition_keeps_the_row(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ D-20 — uchala yakuniy o'tish ham `UPDATE`, hech biri `DELETE` EMAS.

    Qator «xabar yuborishga URINILDI» degan da'voning yagona asosi.
    O'chirilgan qator nosozlikni «umuman rejalashtirilmagan edi» ga
    aylantirardi va nizoda (D-02) tizim tomonida hech qanday iz
    qolmasdi.
    """
    market = bed.market_a
    ids = [
        seed_outbox_row(
            sync_owner_conn,
            market_id=market.market_id,
            kind=RECEIPT,
            vendor_id=market.vendor_ids[0],
            payload={"amount_soum": 2_000 + index},
            status=OutboxStatus.SENT.value,
            attempt_count=1,
        )
        for index in range(3)
    ]
    before = _count(sync_owner_conn, market.market_id)

    async with tenant_session(market.market_id) as session:
        await outbox_repo.mark_delivered(
            session,
            market_id=market.market_id,
            outbox_id=ids[0],
            provider_message_id=9_007_199_254_740,
        )
        await outbox_repo.mark_blocked(
            session, market_id=market.market_id, outbox_id=ids[1], error_type="TelegramForbidden"
        )
        await outbox_repo.mark_failed(
            session,
            market_id=market.market_id,
            outbox_id=ids[2],
            error_type="ConnectTimeout",
            status_code=500,
        )

    assert _count(sync_owner_conn, market.market_id) == before, "qator O'CHIRILDI (D-20)"
    assert _row(sync_owner_conn, ids[0])["status"] == OutboxStatus.DELIVERED.value
    assert _row(sync_owner_conn, ids[0])["provider_message_id"] == 9_007_199_254_740
    assert _row(sync_owner_conn, ids[1])["status"] == OutboxStatus.BLOCKED.value
    assert _row(sync_owner_conn, ids[2])["status"] == OutboxStatus.FAILED.value
    assert _row(sync_owner_conn, ids[2])["last_status_code"] == 500


async def test_reschedule_counts_the_attempt_it_just_finished(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ Qayta rejalashtirish urinishni SANAYDI — u AYNAN shu joyda tugadi.

    =======================================================================
    ⛔ HISOB `claim()` DAN KO'CHDI VA IKKI JOYDA SANALMAYDI.

    `reschedule()` FAQAT haqiqiy jo'natishdan keyin chaqiriladi (Telegram
    `429`/`5xx` yoki tarmoq uzilishi), ya'ni urinish HAQIQATAN bo'lgan.
    Manzilsiz qatorning yo'li esa BOSHQA funksiya — `defer_unresolved()` —
    va u hisoblagichga TEGMAYDI. Ikki nomning bo'lishi chaqiruv joyida
    NIYATNI aytadi; bitta bayroqli funksiya `True`/`False` bo'lib adashardi.
    =======================================================================

    ⚠ `next_attempt_at` CHAQIRUVCHIDAN: backoff arifmetikasi (DQ-3) va
      Telegram ning `retry_after` qiymati 07-09 da hisoblanadi. Uni ikki
      joyga bo'lish ikkita, jimgina ajraladigan formulani tug'dirardi.
    """
    market = bed.market_a
    outbox_id = seed_outbox_row(
        sync_owner_conn,
        market_id=market.market_id,
        kind=RECEIPT,
        vendor_id=market.vendor_ids[0],
        payload={"amount_soum": 15_000},
        status=OutboxStatus.SENT.value,
        attempt_count=2,
    )
    retry_at = QUIET_MOMENT + timedelta(minutes=8)

    async with tenant_session(market.market_id) as session:
        await outbox_repo.reschedule(
            session,
            market_id=market.market_id,
            outbox_id=outbox_id,
            next_attempt_at=retry_at,
            error_type="ReadTimeout",
            status_code=None,
        )

    row = _row(sync_owner_conn, outbox_id)
    assert row["status"] == OutboxStatus.PENDING.value
    assert row["attempt_count"] == 3, (
        f"urinish sanalmadi: {row['attempt_count']}, kutilgani 3. Hisob `claim()` "
        "dan jo'natish joyiga ko'chdi — aks holda `MAX_ATTEMPTS` chegarasi HECH "
        "QACHON ishlamasdi va qator mangu aylanardi"
    )
    assert row["next_attempt_at"] == retry_at
    assert row["lease_until"] is None


async def test_every_terminal_writer_counts_exactly_one_attempt(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ UCHALA TERMINAL YOZUVCHI HAM urinishni AYNAN BIR MARTA sanaydi.

    =======================================================================
    ⛔ NEGA UCHALASI BIR TESTDA VA UCHALASI HAM MAJBURIY.

    Hisob `claim()` dan ko'chgach, u BARCHA yakuniy yo'llarga qo'yilishi
    shart. Bitta yo'lda unutilsa chegara JIMGINA ajralardi: masalan
    `mark_failed()` sanamasa, `5xx` bilan yiqilayotgan qator har tikda
    hisobni O'SHA joyda qoldirib, `MAX_ATTEMPTS` ga HECH QACHON yetmasdi.

    ⚠ HAR YOZUVCHI O'Z QATORINI OLADI: bittasini uchala funksiyadan
      o'tkazish «oshdi» ni «kim oshirdi» dan ajrata olmasdi.
    =======================================================================
    """
    market = bed.market_a
    ids = [
        seed_outbox_row(
            sync_owner_conn,
            market_id=market.market_id,
            kind=RECEIPT,
            vendor_id=market.vendor_ids[0],
            payload={"amount_soum": 4_000 + index},
            status=OutboxStatus.SENT.value,
            attempt_count=1,
        )
        for index in range(3)
    ]

    async with tenant_session(market.market_id) as session:
        await outbox_repo.mark_delivered(
            session, market_id=market.market_id, outbox_id=ids[0], provider_message_id=987_654_321
        )
        await outbox_repo.mark_blocked(
            session, market_id=market.market_id, outbox_id=ids[1], error_type="TelegramForbidden"
        )
        await outbox_repo.mark_failed(
            session,
            market_id=market.market_id,
            outbox_id=ids[2],
            error_type="HTTPStatusError",
            status_code=500,
        )

    counted = {
        "mark_delivered": _row(sync_owner_conn, ids[0])["attempt_count"],
        "mark_blocked": _row(sync_owner_conn, ids[1])["attempt_count"],
        "mark_failed": _row(sync_owner_conn, ids[2])["attempt_count"],
    }
    assert counted == {"mark_delivered": 2, "mark_blocked": 2, "mark_failed": 2}, (
        f"terminal yozuvchi(lar) urinishni sanamadi: {counted} (har biri 1 -> 2 "
        "bo'lishi kerak edi). Urinish AYNAN shu joyda tugaydi va shu joyda sanaladi"
    )


async def test_defer_unresolved_returns_the_row_without_counting_an_attempt(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔⛔ MANZILSIZ QATOR NAVBATGA QAYTADI VA BYUDJETI YEYILMAYDI.

    =======================================================================
    ⛔ URINISH UMUMAN QILINMAGAN: sotuvchi hali botga ULANMAGAN, ya'ni HTTP
       so'rovi YUBORILMAGAN. Uni hisobga qo'shish botga uch kunda ulangan
       sotuvchining butun byudjetini yeb qo'yardi va birinchi HAQIQIY
       urinishdayoq kvitansiya `failed` bo'lardi.

    ⚠ ALOHIDA FUNKSIYA, BAYROQ EMAS (`reschedule(count=False)` EMAS):
      bayroq chaqiruv joyida `True`/`False` bo'lib adashishi mumkin, alohida
      nom esa niyatni O'QIYOTGAN odamga aytadi.
    =======================================================================

    ⛔ `last_error_type` HAMON `_validate_error_type()` DAN O'TADI (D-04):
       yangi yo'l ochilishi sir chegarasini aylanib o'tish yo'li bo'lmasligi
       kerak.
    """
    market = bed.market_a
    outbox_id = seed_outbox_row(
        sync_owner_conn,
        market_id=market.market_id,
        kind=RECEIPT,
        vendor_id=market.vendor_ids[0],
        payload={"amount_soum": 15_000},
        status=OutboxStatus.SENT.value,
        attempt_count=0,
    )
    defer_to = QUIET_MOMENT + timedelta(minutes=15)

    async with tenant_session(market.market_id) as session:
        await outbox_repo.defer_unresolved(
            session,
            market_id=market.market_id,
            outbox_id=outbox_id,
            next_attempt_at=defer_to,
            error_type="UnresolvedRecipient",
        )

    row = _row(sync_owner_conn, outbox_id)
    assert row["status"] == OutboxStatus.PENDING.value
    assert row["attempt_count"] == 0, (
        f"manzilsiz qator urinish sarfladi: {row['attempt_count']}. HTTP so'rovi "
        "UMUMAN yuborilmagan — byudjet faqat HAQIQIY urinishga qo'llanadi"
    )
    assert row["next_attempt_at"] == defer_to
    assert row["lease_until"] is None
    assert row["last_error_type"] == "UnresolvedRecipient"

    # ⛔ SIR CHEGARASI YANGI YO'LDA HAM KUCHDA (D-04).
    async with tenant_session(market.market_id) as session:
        with pytest.raises(ValueError, match="last_error_type"):
            await outbox_repo.defer_unresolved(
                session,
                market_id=market.market_id,
                outbox_id=outbox_id,
                next_attempt_at=defer_to,
                error_type="https://api.telegram.org/bot123:ABC/sendMessage",
            )


@pytest.mark.parametrize(
    "error_type",
    [
        "https://api.telegram.org/bot123:ABC/sendMessage",
        "Client error '401 Unauthorized' for url https://api.telegram.org/bot123:ABC",
        "TelegramForbidden: bot was blocked by the user",
        "A" * 65,
        "",
    ],
)
async def test_a_leaky_error_type_is_rejected_at_the_repository(
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
    error_type: str,
) -> None:
    """⛔ D-04 NING IKKINCHI QATLAMI — chaqiruvchi adashsa ham token bazaga tushmaydi.

    Telegram Bot API ning URL'i BOT TOKENINI tashiydi va `httpx`
    istisnosining MATNI to'liq URL'ni o'z ichiga oladi (`alerts.py` ning
    2-taqig'i). Bitta `str(exc)` sirni bazaga, u yerdan `pg_dump` ->
    restic -> TASHQI BUCKET ga olib chiqardi.

    ⚠ RO'YXATDA PROBELLI, LEKIN URL'SIZ qator ham bor
      (`"TelegramForbidden: bot was blocked..."`): `str(exc)` ning har
      qanday shakli rad etilishi kerak, faqat URL tashigani emas — aks
      holda chegara «URL detektori» bo'lib qolardi va u aylanib
      o'tilardi.
    """
    market = bed.market_a
    async with tenant_session(market.market_id) as session:
        with pytest.raises(ValueError, match="last_error_type"):
            await outbox_repo.mark_failed(
                session,
                market_id=market.market_id,
                outbox_id=uuid4(),
                error_type=error_type,
                status_code=None,
            )


# ---------------------------------------------------------------------------
# 5. `resolve_chat_id` — manzil JO'NATISH PAYTIDA o'qiladi (D-26c)
# ---------------------------------------------------------------------------


async def test_resolve_chat_id_follows_the_active_binding_not_the_revoked_one(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ D-26(c) — qayta ulanishdan keyin xabar YANGI chatga ketadi.

    =======================================================================
    AYNAN SHU SABABDAN `chat_id` OUTBOX QATORIDA SAQLANMAYDI.

    Qayta ulanish QONUNIY shox: o'sha telefon, BOSHQA Telegram akkaunti.
    Manzil qatorga muzlatilgan bo'lsa, navbatda turgan qarz eslatmasi
    ESKI chatga ketardi — ya'ni sotuvchining moliyaviy ma'lumoti u ENDI
    BOSHQARMAYDIGAN akkauntga tushardi.
    =======================================================================
    """
    market = bed.market_a
    vendor_id = market.vendor_ids[0]
    old_chat, new_chat = 7_600_000_001, 7_600_000_002
    seed_binding(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=vendor_id,
        telegram_user_id=old_chat,
        revoked_at=QUIET_MOMENT - timedelta(days=1),
        revoked_reason="rebind",
    )
    seed_binding(
        sync_owner_conn,
        market_id=market.market_id,
        vendor_id=vendor_id,
        telegram_user_id=new_chat,
    )

    async with tenant_session(market.market_id) as session:
        resolved = await outbox_repo.resolve_chat_id(
            session, market_id=market.market_id, recipient_kind=VENDOR, vendor_id=vendor_id
        )
        unbound = await outbox_repo.resolve_chat_id(
            session,
            market_id=market.market_id,
            recipient_kind=VENDOR,
            vendor_id=market.vendor_ids[1],
        )
        director = await outbox_repo.resolve_chat_id(
            session, market_id=market.market_id, recipient_kind=DIRECTOR, vendor_id=None
        )

    assert resolved == new_chat, (
        "bekor qilingan bog'lanish qaytdi — sotuvchining qarzi u boshqarmaydigan "
        "akkauntga ketardi (D-26c)"
    )
    assert unbound is None, "ulanmagan sotuvchi uchun `None` QONUNIY natija, xato emas"
    assert director is None, "sozlama qatori yo'q bozorda direktor manzili ham `None`"


async def test_resolve_chat_id_reads_the_director_seat_from_the_settings_row(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Direktorning manzili — sozlama qatoridan, bog'lanish jadvalidan EMAS."""
    market = bed.market_a
    seed_notification_settings(
        sync_owner_conn, market_id=market.market_id, director_chat_id=7_600_000_777
    )

    async with tenant_session(market.market_id) as session:
        resolved = await outbox_repo.resolve_chat_id(
            session, market_id=market.market_id, recipient_kind=DIRECTOR, vendor_id=None
        )

    assert resolved == 7_600_000_777


# ---------------------------------------------------------------------------
# 6. RLS — eng JIM xato sinfi
# ---------------------------------------------------------------------------


async def test_claim_without_tenant_context_returns_nothing_and_never_raises(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ RLS FAIL-CLOSED: kontekstsiz chaqiruv 0 qator beradi va YIQILMAYDI.

    Bu eng jim xato sinfi: fon vazifasi kontekstni o'rnatishni unutsa
    navbat abadiy bo'sh ko'rinardi va yagona belgi «sotuvchilar xabar
    olmayapti» bo'lardi — bir necha kundan keyin.

    ⚠ NAZORAT: AYNAN o'sha qator TO'G'RI kontekstda OLINADI, ya'ni
      bo'shlik kontekstdan, qatorning yo'qligidan emas.
    """
    market = bed.market_a
    outbox_id = seed_outbox_row(
        sync_owner_conn,
        market_id=market.market_id,
        kind=RECEIPT,
        vendor_id=market.vendor_ids[0],
        payload={"amount_soum": 15_000},
        next_attempt_at=QUIET_MOMENT - timedelta(hours=1),
    )

    async with tenant_session(None) as session:
        blind = await outbox_repo.claim(
            session,
            market_id=market.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=QUIET_MOMENT,
        )
    assert blind == [], "RLS kontekstsiz chaqiruvga qator berdi"

    async with tenant_session(market.market_id) as session:
        seen = await outbox_repo.claim(
            session,
            market_id=market.market_id,
            batch_size=50,
            lease_seconds=LEASE,
            now=QUIET_MOMENT,
        )
    assert [row.id for row in seen] == [outbox_id], (
        "nazorat qulab tushdi: qator TO'G'RI kontekstda ham olinmadi, ya'ni "
        "yuqoridagi bo'shliq RLS ning emas, seed'ning natijasi edi"
    )


async def test_the_oldest_row_is_claimed_first(
    sync_owner_conn: Connection[TupleRow],
    bed: MarketDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Tartib `created_at, id` — ENG ESKI BIRINCHI.

    Aks holda partiya chegarasiga (`LIMIT`) urilgan navbatda eski qator
    har tikda ORQAGA surilardi va kvitansiya cheksiz kutardi.
    """
    market = bed.market_a
    ids = [
        seed_outbox_row(
            sync_owner_conn,
            market_id=market.market_id,
            kind=RECEIPT,
            vendor_id=market.vendor_ids[0],
            payload={"amount_soum": 3_000 + index},
            next_attempt_at=QUIET_MOMENT - timedelta(hours=1),
        )
        for index in range(3)
    ]
    for offset, outbox_id in enumerate(ids):
        sync_owner_conn.execute(
            "UPDATE notification_outbox SET created_at = %s WHERE id = %s",
            (QUIET_MOMENT - timedelta(minutes=30 - offset * 10), str(outbox_id)),
        )

    async with tenant_session(market.market_id) as session:
        claimed = await outbox_repo.claim(
            session,
            market_id=market.market_id,
            batch_size=2,
            lease_seconds=LEASE,
            now=QUIET_MOMENT,
        )

    assert [row.id for row in claimed] == ids[:2], (
        "partiya eng eski qatorlardan boshlanmadi — navbat oxiridagi kvitansiya "
        "har tikda orqaga surilardi"
    )
