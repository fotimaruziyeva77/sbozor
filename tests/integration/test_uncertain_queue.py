"""Noaniq navbat — byudjet, ustuvorlik va OMMAVIY ENDPOINTNING YO'QLIGI (AI-03, SC#3).

=============================================================================
BU FAYLNING ENG MUHIM TESTI BIRORTA MAHSULOT KODINI CHAQIRMAYDI.

`test_no_bulk_approve_endpoint` OpenAPI SXEMASINI skanerlaydi va massiv
qabul qiladigan `zone_reviews` yaratuvchi marshrut YO'QLIGINI tasdiqlaydi
(D-18). Bu UI qoidasi emas, API qoidasi: «hammasini tasdiqlash» tugmasini
olib tashlash YETARLI EMAS — har qatorda ikki tugmali ro'yxat aynan
o'sha tugma, faqat qadamlari ko'proq (UI-SPEC §7.3).

⛔ MARSHRUT NOMLARI RO'YXATI YOZILMAYDI. Aynan nomlar ro'yxati 04-12 ning
   darvozasini eskirtirgan edi (§S-10): ro'yxatda yo'q uchinchi jarayon
   struktura jihatidan ko'rinmasdi va darvoza ABADIY yashil edi. Bu yerda
   ham xuddi shunday bo'lardi — `POST /review/approve-many` deb emas,
   `POST /review/batch` deb nomlangan endpoint ro'yxatdan bemalol o'tardi.

⚠ QUYI CHEGARA MAJBURIY (`MINIMUM_SCANNED_ROUTES`): bo'sh sxemada
  «massiv qabul qiluvchi marshrut yo'q» asserti JIMGINA o'tardi va
  darvoza hech nimani o'lchamasdi.
=============================================================================

DA'VOLAR MEXANIZM EMAS, XULQ BILAN O'LCHANADI (`test_camera_zones_api.py`
da o'rnatilgan uslub, 03-07 ning o'lchovi):

    huquq da'vosi     -> `OCCUPANCY_REVIEW` siz so'rov **403** oladi VA
                         `audit_log` da soxta o'qish qatori QOLMAYDI;
    ankorlash da'vosi -> javob REKURSIV skanerlanadi (ma'lum kalit emas);
    byudjet da'vosi   -> endpoint navbat bo'shligidan BOSHQA kod beradi.

NAZORAT HOLATLARI JUFTLIGI: har «rad etiladi» testining yonida «qabul
qilinadi» jufti turadi. Usiz «endpoint umuman ishlamayapti» holati ham
yashil ko'rinardi.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import psycopg
import pytest
from app.main import app as fastapi_app
from app.repositories.review_repo import ReviewRepository
from app.schemas import AnswerRequest
from fixtures.admin_api import session_headers
from fixtures.auth_api import audit_rows
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import (
    CONFIDENCE_0_45,
    CONFIDENCE_0_59,
    OccupancyDomainSeed,
    SeededEvent,
    add_zone_with_event,
    has_active_vendor_on,
    occupancy_rows,
)
from fixtures.snapshot_domain import SEED_BUSINESS_DATE, snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.db import make_sessionmaker
from sbozor_core.enums import AuditAction, OccupancyVerdict, ReviewQueueKind
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import business_today
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    import httpx
    from fastapi import FastAPI
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

NEXT_URL = "/api/v1/review/uncertain/next"
BUDGET_URL = "/api/v1/review/budget"
REVIEW_URL = "/api/v1/review"

QUEUE_LIMIT = 50
"""`build_uncertain_queue()` ning test chegarasi — nomzodlar sonidan KATTA.

Chegarani nomzodlar sonidan kichik qilish har testni «limit ishladimi?»
degan IKKINCHI savol bilan aralashtirardi; limitning O'ZI alohida testda
o'lchanadi.
"""


# ===========================================================================
# Muhit
# ===========================================================================


class Env:
    """Besh qatlamli seed + nazoratchi — bitta obyektda."""

    def __init__(
        self,
        base: TwoMarketSeed,
        domain: MarketDomainSeed,
        occupancy: OccupancyDomainSeed,
        auth: AuthSeed,
    ) -> None:
        self.base = base
        self.domain = domain
        self.occupancy = occupancy
        self.auth = auth

    @property
    def market_a(self) -> UUID:
        return self.base.market_a.id

    @property
    def reviewer_id(self) -> UUID:
        return self.auth.inspector.user_id

    @property
    def camera_a(self) -> UUID:
        return self.occupancy.market_a.camera_id

    @property
    def snapshot_a(self) -> UUID:
        return self.occupancy.market_a.snapshot_with_ok_quality

    @property
    def assigned_stall(self) -> UUID:
        """Biriktirilgan sotuvchisi BOR rasta — HAR testda nazorat asserti bilan.

        Seed'dagi `uncertain` hodisa AYNAN shu rastada (`stall_ids[1]`),
        ya'ni navbat qurilganda u avtomatik nomzod bo'ladi.
        """
        stall_id = self.domain.market_a.gap_stall_id
        assert stall_id is not None, "nazorat: `market_domain` da `gap_stall_id` yo'q"
        return stall_id

    @property
    def unassigned_stall(self) -> UUID:
        """Biriktirilmagan VA zonasiz rasta (`stall_ids[2]`)."""
        stall_id = self.domain.market_a.unassigned_stall_id
        assert stall_id is not None, "nazorat: `market_domain` da `unassigned_stall_id` yo'q"
        return stall_id

    @property
    def seed_assignment(self) -> UUID:
        """Seed'dagi JAVOBSIZ noaniq navbat yozuvi."""
        assignment_id = self.occupancy.market_a.uncertain_assignment_id
        assert assignment_id is not None, "seed'da javobsiz noaniq yozuv yo'q"
        return assignment_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    auth_seed: AuthSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """Besh qatlamli seed; tozalash TESKARI tartibda (FK zanjiri bo'yicha).

    ⚠ `auth_seed` `market_domain` DAN OLDIN so'raladi va bu ATAYIN:
      pytest fixture'larni teskari tartibda yopadi, ya'ni nazoratchi
      foydalanuvchisi `zone_reviews` qatorlaridan KEYIN o'chiriladi.
      Teskari tartibda `fk_zone_reviews_reviewer_id_users` (`ondelete`
      YO'Q — javobi bor foydalanuvchini o'chirish RAD ETILADI) tozalashni
      yiqitardi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        yield Env(two_markets, market_domain, occupancy, auth_seed)


@pytest.fixture
async def inspector_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """A bozori nazoratchisining sessiyasi — unda AYNAN `OCCUPANCY_REVIEW` bor."""
    return await session_headers(api_client, env.auth.inspector.phone, SEED_PASSWORD)


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Direktor sessiyasi — `REPORT_VIEW` BOR, `OCCUPANCY_REVIEW` YO'Q (D-07)."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def duo_sessionmaker(
    app_url: str,
    _bootstrap_roles: None,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """IKKI ulanishli O'Z engine'i — parallel `claim_next` testi uchun.

    ⚠ `app_engine` BU YERDA ISHLAMAYDI: u `pool_size=1, max_overflow=0`
      bilan qurilgan (`tests/conftest.py:300`) va bu ATAYIN — GUC sizishini
      ochib berish uchun. `SKIP LOCKED` o'lchovi esa AYNAN IKKI OCHIQ
      tranzaksiyani talab qiladi: bitta ulanish bilan ikkinchi sessiya
      poolda kutib qolardi va test qulfni emas, POOL CHEGARASINI o'lchagan
      bo'lardi (bu birinchi urinishda AYNAN shunday bo'ldi —
      `QueuePool limit of size 1 ... timed out`).

    `test_capture_repo.py::duo_sessionmaker` ning aynan nusxasi va u
    ATAYIN `conftest.py` ga ko'chirilmagan: o'sha fayl parallel to'lqinning
    umumiy infratuzilmasi va ikki reja uni bir vaqtda tahrirlardi.
    """
    engine = create_async_engine(app_url, pool_size=2, max_overflow=0)
    try:
        yield make_sessionmaker(engine)
    finally:
        await engine.dispose()


# ===========================================================================
# Yordamchilar
# ===========================================================================


def repo(session: AsyncSession, market_id: UUID) -> ReviewRepository:
    return ReviewRepository(session, market_id)


async def build_queue(
    tenant_session: TenantSessionFactory, env: Env, *, limit: int = QUEUE_LIMIT
) -> int:
    """Navbatni quradi va HAQIQATAN yozilgan qatorlar sonini qaytaradi."""
    async with tenant_session(env.market_a) as session:
        return await repo(session, env.market_a).build_uncertain_queue(
            SEED_BUSINESS_DATE, limit=limit
        )


def add_candidate(
    conn: Connection[TupleRow],
    env: Env,
    *,
    stall_id: UUID,
    confidence: str,
    center: tuple[float, float],
    camera_id: UUID | None = None,
    verdict: str = OccupancyVerdict.UNCERTAIN.value,
    version: int = 1,
) -> SeededEvent:
    return add_zone_with_event(
        conn,
        market_id=env.market_a,
        camera_id=camera_id if camera_id is not None else env.camera_a,
        stall_id=stall_id,
        snapshot_id=env.snapshot_a,
        verdict=verdict,
        confidence=confidence,
        center=center,
        version=version,
    )


def _queued_verdicts(conn: Connection[TupleRow], market_id: UUID) -> list[str]:
    rows = conn.execute(
        "SELECT ev.verdict FROM review_assignments ra "
        "JOIN occupancy_events ev ON ev.id = ra.occupancy_event_id "
        "WHERE ra.market_id = %s AND ra.queue_kind = 'uncertain'",
        (str(market_id),),
    ).fetchall()
    return [str(row[0]) for row in rows]


def _assignment_of(conn: Connection[TupleRow], event_id: UUID) -> UUID:
    row = conn.execute(
        "SELECT id FROM review_assignments WHERE occupancy_event_id = %s",
        (str(event_id),),
    ).fetchone()
    assert row is not None, f"hodisa {event_id} navbatga tushmagan"
    return UUID(str(row[0]))


def _reviews_for(conn: Connection[TupleRow], assignment_id: UUID) -> int:
    row = conn.execute(
        "SELECT count(*) FROM zone_reviews WHERE review_assignment_id = %s",
        (str(assignment_id),),
    ).fetchone()
    assert row is not None
    return int(row[0])


def _answer_directly(conn: Connection[TupleRow], env: Env, assignment_id: UUID) -> None:
    """Topshiriqni navbatdan CHIQARADI — javob yozib.

    ⚠ `review_assignments` dan o'chirish YO'LI ATAYIN ISHLATILMAYDI: u
      `build_uncertain_queue()` uchun hodisani QAYTA nomzod qilardi va
      test o'zi qurgan holatni buzardi. Javob yozish — mahsulotning O'Z
      yo'li.
    """
    conn.execute(
        "INSERT INTO zone_reviews (market_id, review_assignment_id, queue_kind, "
        "shown_ai_verdict, human_verdict, reviewer_id) "
        "VALUES (%s, %s, 'uncertain', false, 'occupied', %s)",
        (str(env.market_a), str(assignment_id), str(env.base.market_a.admin_user_id)),
    )


def _delete_review(conn: Connection[TupleRow], review_id: UUID) -> None:
    """Seed'dagi javobni olib tashlaydi — QORALAMA bozor istisnosi orqali.

    `zone_reviews` SHARTSIZ o'zgarmas; yagona `DELETE` yo'li — bozorni
    qoralamaga tushirish (`cleanup_occupancy_domain()` bilan AYNAN bir xil
    mexanizm va bir xil sabab). Bayroq darhol qaytariladi.
    """
    market_row = conn.execute(
        "SELECT market_id FROM zone_reviews WHERE id = %s", (str(review_id),)
    ).fetchone()
    assert market_row is not None
    market_id = str(market_row[0])
    conn.execute("UPDATE markets SET is_active = false WHERE id = %s", (market_id,))
    conn.execute("DELETE FROM zone_reviews WHERE id = %s", (str(review_id),))
    conn.execute("UPDATE markets SET is_active = true WHERE id = %s", (market_id,))


# ===========================================================================
# 1. Navbat qurish — idempotentlik, filtr va chegara
# ===========================================================================


async def test_build_uncertain_queue_is_idempotent(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """Ikkinchi chaqiruv YANGI qator yozmaydi — `UNIQUE (occupancy_event_id)`.

    ⚠ NAZORAT: birinchi chaqiruv AYNAN BITTA qator yozishi ham
      tekshiriladi. Usiz «hech nima yozilmadi» holati idempotentlik deb
      o'qilardi — seed'dagi yagona `uncertain` hodisa ALLAQACHON navbatda
      turibdi, ya'ni yangi nomzodsiz ikkala chaqiruv ham 0 qaytarardi.
    """
    add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_45,
        center=(0.20, 0.70),
    )

    first = await build_queue(tenant_session, env)
    second = await build_queue(tenant_session, env)

    assert first == 1, "yangi nomzod navbatga tushmadi"
    assert second == 0, "ikkinchi chaqiruv qator yozdi — `ON CONFLICT DO NOTHING` ishlamayapti"


async def test_build_uncertain_queue_takes_only_uncertain_events(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """FAQAT `uncertain` hodisalar navbatga tushadi.

    ⛔ NOMZOD ATAYIN YANGI YOZILADI VA U BIRORTA TOPSHIRIQQA BOG'LANMAGAN.
       Seed'dagi `occupied` hodisa allaqachon ko'r audit yozuviga bog'langan,
       ya'ni uni `NOT EXISTS` predikati baribir chiqarib tashlardi — o'sha
       hodisa bilan yozilgan test `verdict` filtrini `NOT EXISTS` dan
       AJRATA OLMASDI va filtr olib tashlanganda ham YASHIL qolardi.
    """
    add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_59,
        center=(0.20, 0.70),
        verdict=OccupancyVerdict.OCCUPIED.value,
    )
    written = await build_queue(tenant_session, env)

    verdicts = _queued_verdicts(sync_owner_conn, env.market_a)

    assert written == 0, "`occupied` hodisa navbatga tushdi"
    assert verdicts, "navbat bo'sh — filtr testi hech nimani o'lchamaydi"
    assert set(verdicts) == {OccupancyVerdict.UNCERTAIN.value}


async def test_build_uncertain_queue_respects_the_limit(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """`limit` YANGI qatorlar sonini cheklaydi (nazorat: limitsiz ikkitasi tushardi)."""
    second_camera = env.occupancy.market_a.second_camera_id
    assert second_camera is not None, "nazorat: A bozorida ikkinchi kamera yo'q — seed o'zgargan"

    add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_45,
        center=(0.20, 0.70),
    )
    add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_59,
        center=(0.25, 0.75),
        camera_id=second_camera,
    )

    limited = await build_queue(tenant_session, env, limit=1)
    remaining = await build_queue(tenant_session, env)

    assert limited == 1
    assert remaining == 1, "chegaradan chiqib qolgan nomzod keyingi chaqiruvda ham tushmadi"


# ===========================================================================
# 2. Ustuvorlik — OCHIQ TANLOV
# ===========================================================================


async def test_claim_next_prefers_the_stall_with_a_vendor(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """Billing ta'siri chegaraga yaqinlikdan USTUN — literal test.

    ⛔ IKKI TARTIB ATAYIN ZID QILIB QO'YILGAN: biriktirilmagan rasta
       chegaraga AYNAN o'lchov nuqtasida (`0.45`, masofa 0), biriktirilgani
       esa undan uzoqroq (`0.554`). Ya'ni «faqat chegaraga yaqinlik»
       tartibi biriktirilmaganini birinchi qaytarardi va test QIZARARDI.
       Ikkalasi bir yo'nalishda bo'lganda test ikki tartibni AJRATA
       olmasdi — bu 05-06 sabotaj S4 ning aynan darsi.
    """
    assert has_active_vendor_on(
        sync_owner_conn,
        market_id=env.market_a,
        stall_id=env.assigned_stall,
        day=SEED_BUSINESS_DATE,
    ), "nazorat: `gap_stall` ga shu kunda biriktirish yo'q — `market_domain` o'zgargan"
    assert not has_active_vendor_on(
        sync_owner_conn,
        market_id=env.market_a,
        stall_id=env.unassigned_stall,
        day=SEED_BUSINESS_DATE,
    ), "nazorat: `unassigned_stall` biriktirilgan — `market_domain` o'zgargan"

    near = add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_45,
        center=(0.20, 0.70),
    )
    await build_queue(tenant_session, env)

    async with tenant_session(env.market_a) as session:
        item = await repo(session, env.market_a).claim_next()

    assert item is not None
    assert item.stall_id == env.assigned_stall, (
        "navbat chegaraga yaqinlikni billing ta'siridan ustun qo'ydi"
    )
    assert item.has_active_vendor is True
    assert item.stall_id != near.stall_id


async def test_closer_confidence_wins_within_the_same_billing_impact(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """Teng billing ta'sirida chegaraga YAQINROQ confidence oldin keladi.

    Ikkala nomzod ham AYNI biriktirilmagan rastada (ikki kamerada) —
    ya'ni birinchi mezon TENG va tartibni faqat ikkinchisi hal qiladi.
    Seed'dagi (biriktirilgan rastadagi) band javob bilan navbatdan
    chiqariladi, aks holda u birinchi mezon bo'yicha g'olib bo'lardi.
    """
    second_camera = env.occupancy.market_a.second_camera_id
    assert second_camera is not None, "nazorat: A bozorida ikkinchi kamera yo'q — seed o'zgargan"

    far = add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_59,
        center=(0.20, 0.70),
    )
    near = add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_45,
        center=(0.25, 0.75),
        camera_id=second_camera,
    )
    _answer_directly(sync_owner_conn, env, env.seed_assignment)
    await build_queue(tenant_session, env)

    async with tenant_session(env.market_a) as session:
        item = await repo(session, env.market_a).claim_next()

    assert item is not None
    assert item.assignment_id == _assignment_of(sync_owner_conn, near.event_id)
    assert item.assignment_id != _assignment_of(sync_owner_conn, far.event_id)


async def test_two_concurrent_claims_get_different_items(
    tenant_session: TenantSessionFactory,
    duo_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """`FOR UPDATE ... SKIP LOCKED` — ikki OCHIQ tranzaksiya turli band oladi.

    ⚠ TRANZAKSIYALAR BIR VAQTDA OCHIQ TURISHI SHART. Ketma-ket ochilgan
      ikki tranzaksiya AYNI bandni qaytarardi va bu ham TO'G'RI xulq
      (qulf `COMMIT` da tushadi, `review_repo` modul docstringi) — ya'ni
      ketma-ket yozilgan test `SKIP LOCKED` ni umuman o'lchamasdi.

    ⚠ `SET LOCAL statement_timeout` MAJBURIY va u testning YURAGI
      (`test_capture_repo.py` da o'rnatilgan naqsh): `SKIP LOCKED` olib
      tashlansa ikkinchi so'rov qulf ustida ABADIY bloklanadi va test
      qizarmasdan OSILIB qolardi. Timeout uni `QueryCanceled` ga
      aylantiradi.
    """
    add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_45,
        center=(0.20, 0.70),
    )
    await build_queue(tenant_session, env)

    async with duo_sessionmaker() as first_session, first_session.begin():
        await set_tenant_context(
            first_session, market_id=env.market_a, actor_id=None, request_id="pytest-a"
        )
        first = await repo(first_session, env.market_a).claim_next()

        # ⚠ BIRINCHI TRANZAKSIYA HALI OCHIQ — qulf TURIBDI.
        async with duo_sessionmaker() as second_session, second_session.begin():
            await set_tenant_context(
                second_session, market_id=env.market_a, actor_id=None, request_id="pytest-b"
            )
            await second_session.execute(text("SET LOCAL statement_timeout = '4000ms'"))
            second = await repo(second_session, env.market_a).claim_next()

    assert first is not None
    assert second is not None, "ikkinchi tranzaksiya bo'sh oldi — nomzodlar yetarli emas"
    assert first.assignment_id != second.assignment_id, (
        "ikki parallel tranzaksiya bir xil bandni oldi — `SKIP LOCKED` yo'q"
    )


async def test_claim_next_skips_answered_items(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """Javob yozilgan band QAYTA berilmaydi; boshqasi qolmasa `None`.

    NAZORAT: javobdan OLDIN band QAYTADI. Usiz `claim_next()` butunlay
    ishlamay qolganda ham test yashil bo'lardi.
    """
    await build_queue(tenant_session, env)

    async with tenant_session(env.market_a) as session:
        before = await repo(session, env.market_a).claim_next()

    assert before is not None
    _answer_directly(sync_owner_conn, env, before.assignment_id)

    async with tenant_session(env.market_a) as session:
        after = await repo(session, env.market_a).claim_next()

    assert after is None


# ===========================================================================
# 3. Javob — bitta topshiriqqa bitta qator
# ===========================================================================


async def test_second_record_answer_raises_integrity_error(
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """`UNIQUE (review_assignment_id)` ikkinchi javobni rad etadi."""
    async with tenant_session(env.market_a, env.reviewer_id) as session:
        first = await repo(session, env.market_a).record_answer(
            env.seed_assignment,
            queue_kind=ReviewQueueKind.UNCERTAIN.value,
            reviewer_id=env.reviewer_id,
            human_verdict=OccupancyVerdict.OCCUPIED.value,
            shown_ai_verdict=False,
            decision_ms=1200,
        )
    assert first is not None
    assert first.queue_kind == ReviewQueueKind.UNCERTAIN.value
    assert first.system_verdict == OccupancyVerdict.UNCERTAIN.value

    with pytest.raises(IntegrityError):
        async with tenant_session(env.market_a, env.reviewer_id) as session:
            await repo(session, env.market_a).record_answer(
                env.seed_assignment,
                queue_kind=ReviewQueueKind.UNCERTAIN.value,
                reviewer_id=env.reviewer_id,
                human_verdict=OccupancyVerdict.EMPTY.value,
                shown_ai_verdict=False,
                decision_ms=900,
            )


async def test_record_answer_copies_the_queue_kind_from_the_assignment(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """Yozilgan `queue_kind` KONSTANTA EMAS — u topshiriqning turiga ergashadi.

    =======================================================================
    ⚠ DA'VO ATAYIN SHU SHAKLDA VA U O'LCHANGANIDAN KENGROQ EMAS.

    «Server qiymatni QATORDAN o'qiydi (parametrdan emas)» degan kuchliroq
    da'voni bu test — va umuman HECH QANDAY test — o'lchay olmaydi:
    `_RECORD_ANSWER` ning `WHERE ra.queue_kind = :queue_kind` filtri
    ikkala manbani TENG qilib qo'yadi. Sabotaj bilan tasdiqlandi
    (05-10, sabotaj D): almashtirish 28 testni yashil qoldirdi.

    O'LCHANADIGANI esa bu: ko'r audit topshirig'iga javob yozilganda
    qator `blind_audit` bo'ladi, ya'ni yozilgan qiymat `'uncertain'`
    literaliga qadalmagan. Qadalgan bo'lsa
    `fk_zone_reviews_queue_kind_anchor` (05-05 deviatsiya #5) uni
    `23503` bilan rad etadi va test QIZARADI — bu ham sabotaj bilan
    tasdiqlandi (sabotaj D′).
    =======================================================================
    """
    market_b = env.base.market_b.id
    blind_id = env.occupancy.market_b.blind_assignment_id
    _delete_review(sync_owner_conn, env.occupancy.market_b.blind_review_id)

    async with tenant_session(market_b, env.base.market_b.admin_user_id) as session:
        answered = await repo(session, market_b).record_answer(
            blind_id,
            queue_kind=ReviewQueueKind.BLIND_AUDIT.value,
            reviewer_id=env.base.market_b.admin_user_id,
            human_verdict=OccupancyVerdict.EMPTY.value,
            shown_ai_verdict=False,
            decision_ms=None,
        )

    assert answered is not None
    assert answered.queue_kind == ReviewQueueKind.BLIND_AUDIT.value


async def test_record_answer_on_a_foreign_assignment_writes_nothing(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """Begona bozorning topshirig'i — `None` va BAZADA hech nima o'zgarmaydi (T-05-25)."""
    foreign = env.occupancy.market_b.blind_assignment_id

    async with tenant_session(env.market_a, env.reviewer_id) as session:
        answered = await repo(session, env.market_a).record_answer(
            foreign,
            queue_kind=ReviewQueueKind.BLIND_AUDIT.value,
            reviewer_id=env.reviewer_id,
            human_verdict=OccupancyVerdict.OCCUPIED.value,
            shown_ai_verdict=False,
            decision_ms=None,
        )

    assert answered is None
    assert _reviews_for(sync_owner_conn, foreign) == 1, (
        "begona topshiriqqa qator yozildi yoki mavjudi o'chdi"
    )


async def test_record_answer_on_an_unknown_assignment_returns_none(
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """Mavjud bo'lmagan topshiriq begona bozornikidan AJRATILMAYDI (T-05-25)."""
    async with tenant_session(env.market_a, env.reviewer_id) as session:
        answered = await repo(session, env.market_a).record_answer(
            uuid4(),
            queue_kind=ReviewQueueKind.UNCERTAIN.value,
            reviewer_id=env.reviewer_id,
            human_verdict=OccupancyVerdict.OCCUPIED.value,
            shown_ai_verdict=False,
            decision_ms=None,
        )

    assert answered is None


async def test_answered_row_is_immutable(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """`record_answer()` YOZGAN qator ham tahrirlanmaydi (D-17.4).

    ⚠ `test_occupancy_immutable.py::test_zone_review_cannot_be_updated_or_
      deleted` bilan TAKROR EMAS: u yerda qator SEED tomonidan yoziladi,
      bu yerda esa MAHSULOT KODI tomonidan. Farq ma'noli — qo'riqchi
      `BEFORE UPDATE` da turadi va u yozuv yo'liga bog'liq emas, LEKIN
      «bizning yo'l bilan yozilgan javob ham qulflangan» da'vosi shu
      fazaning O'Z darvozasi (SC#3).
    """
    async with tenant_session(env.market_a, env.reviewer_id) as session:
        answered = await repo(session, env.market_a).record_answer(
            env.seed_assignment,
            queue_kind=ReviewQueueKind.UNCERTAIN.value,
            reviewer_id=env.reviewer_id,
            human_verdict=OccupancyVerdict.OCCUPIED.value,
            shown_ai_verdict=False,
            decision_ms=None,
        )
    assert answered is not None

    with pytest.raises(psycopg.errors.RaiseException) as error:
        sync_owner_conn.execute(
            "UPDATE zone_reviews SET human_verdict = 'empty' WHERE id = %s",
            (str(answered.review_id),),
        )

    assert "append-only" in str(error.value)


# ===========================================================================
# 4. Byudjet hisoblagichi
# ===========================================================================


async def test_daily_answered_count_is_scoped_to_reviewer_and_queue(
    tenant_session: TenantSessionFactory,
    env: Env,
) -> None:
    """Hisoblagich nazoratchi VA navbat turi bo'yicha ajratadi.

    Seed'da A bozorining ko'r audit javobi BOR va uni bozor admini
    yozgan. Nazoratchining hisoblagichi shundan ta'sirlanmasligi kerak —
    aks holda «bugun 12 / 50» boshqa odamning ishini ko'rsatardi.
    """
    today = business_today()

    async with tenant_session(env.market_a, env.reviewer_id) as session:
        before = await repo(session, env.market_a).daily_answered_count(
            env.reviewer_id, today, queue_kind=ReviewQueueKind.UNCERTAIN.value
        )
        await repo(session, env.market_a).record_answer(
            env.seed_assignment,
            queue_kind=ReviewQueueKind.UNCERTAIN.value,
            reviewer_id=env.reviewer_id,
            human_verdict=OccupancyVerdict.OCCUPIED.value,
            shown_ai_verdict=False,
            decision_ms=None,
        )

    async with tenant_session(env.market_a, env.reviewer_id) as session:
        counter = repo(session, env.market_a)
        after = await counter.daily_answered_count(
            env.reviewer_id, today, queue_kind=ReviewQueueKind.UNCERTAIN.value
        )
        other_queue = await counter.daily_answered_count(
            env.reviewer_id, today, queue_kind=ReviewQueueKind.BLIND_AUDIT.value
        )
        other_reviewer = await counter.daily_answered_count(
            env.base.market_a.admin_user_id, today, queue_kind=ReviewQueueKind.UNCERTAIN.value
        )

    assert before == 0
    assert after == 1
    assert other_queue == 0, "ko'r audit hisoblagichi noaniq navbat javobini sanadi"
    assert other_reviewer == 0, "boshqa nazoratchining javobi hisoblagichga tushdi"


# ===========================================================================
# 5. HTTP yuzasi — bitta so'rov = bitta qaror
# ===========================================================================


async def test_next_item_is_served_to_the_inspector(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """NAZORAT HOLATI: nazoratchi bandni HAQIQATAN oladi.

    Usiz quyidagi rad etish testlari «endpoint umuman ishlamayapti»
    holatida ham yashil bo'lardi.
    """
    await build_queue(tenant_session, env)

    response = await api_client.get(NEXT_URL, headers=inspector_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stall_code"]
    assert body["zone_name"]
    assert UUID(body["snapshot_id"]) == env.snapshot_a
    assert body["has_active_vendor"] is True
    assert len(body["polygon"]) >= 3


async def test_director_cannot_reach_the_queue(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    director_headers: dict[str, str],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """`report_view` bor, `occupancy_review` yo'q -> **403** VA soxta audit qatori YO'Q.

    ⚠ DA'VO MEXANIZM EMAS, XULQ BILAN O'LCHANADI (03-07 ning darsi):
      «huquq dekoratorda turibdi» ni tekshiradigan test kafolatning IKKI
      mustaqil mexanizmidan faqat bittasini ko'rardi. Bu yerda rad etish
      NATIJASI va uning IZI o'lchanadi.

    NAZORAT: o'sha navbatni nazoratchi 200 bilan oladi.
    """
    await build_queue(tenant_session, env)
    before = await audit_rows(tenant_session, env.market_a, action=AuditAction.READ.value)

    denied = await api_client.get(NEXT_URL, headers=director_headers)
    allowed = await api_client.get(NEXT_URL, headers=inspector_headers)
    after = await audit_rows(tenant_session, env.market_a, action=AuditAction.READ.value)

    assert denied.status_code == 403, denied.text
    assert allowed.status_code == 200, allowed.text
    assert len(after) == len(before), "rad etilgan so'rov audit jurnalida iz qoldirdi"


def test_answer_request_declares_no_shown_ai_verdict() -> None:
    """⛔ `shown_ai_verdict` KLIENT MAYDONI SIFATIDA MAVJUD EMAS (D-17.3, T-05-44).

    `None` qilib yuborish YETARLI EMAS bo'lardi: maydon sxemada tursa,
    klient uni `true` deb yuborishi mumkin edi va DB `CHECK` i
    (`blind_audit_not_shown`) faqat KO'R auditni qamraydi — ya'ni noaniq
    navbat uchun yolg'on qiymat bemalol yozilardi.

    ⚠ `market_id` VA `decision_ms` HAM YO'Q va ular AYNAN shu sinfdagi
      maydonlar (T-05-24, T-05-46).
    """
    declared = set(AnswerRequest.model_fields)

    assert "shown_ai_verdict" not in declared
    assert "market_id" not in declared
    assert "decision_ms" not in declared
    assert "queue_kind" not in declared
    assert declared == {"human_verdict"}, f"kutilmagan maydon: {sorted(declared)}"


async def test_second_answer_returns_409(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """Ikkinchi javob -> **409** `review_already_answered` (poyga holati).

    ⛔ `blind_answer_locked` DAN AJRATILGAN va farq mahsulotda: bu yerda
       ikkinchi so'rov shunchaki KECH QOLGAN (ikki oyna, ikki bosish),
       ko'r auditda esa taqiq STRUKTURAVIY (`occupancy_errors.py`).
    """
    await build_queue(tenant_session, env)
    item = (await api_client.get(NEXT_URL, headers=inspector_headers)).json()
    target = f"{REVIEW_URL}/{item['assignment_id']}/answer"

    first = await api_client.post(
        target, json={"human_verdict": "occupied"}, headers=inspector_headers
    )
    second = await api_client.post(
        target, json={"human_verdict": "empty"}, headers=inspector_headers
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 409, second.text
    assert second.json()["detail"] == "review_already_answered"


async def test_answer_reveals_the_system_verdict_only_afterwards(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """Oshkor ma'lumot javob TANASIDA keladi va u to'rt maydondan iborat.

    Maydon nomlari `verdict`/`ai_verdict`/`confidence` EMAS va bu MEXANIK
    qaror: G-12 darvozasi `components/blind-audit/**` da o'sha nomlarning
    umuman uchramasligini talab qiladi (UI-SPEC §14.3).
    """
    await build_queue(tenant_session, env)
    item = (await api_client.get(NEXT_URL, headers=inspector_headers)).json()

    response = await api_client.post(
        f"{REVIEW_URL}/{item['assignment_id']}/answer",
        json={"human_verdict": "empty"},
        headers=inspector_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"system_answer", "human_answer", "matched", "locked"}
    assert body["system_answer"] == OccupancyVerdict.UNCERTAIN.value
    assert body["human_answer"] == OccupancyVerdict.EMPTY.value
    assert body["matched"] is False
    assert body["locked"] is True


async def test_answer_on_a_blind_assignment_is_not_found(
    api_client: httpx.AsyncClient,
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """KO'R AUDIT topshirig'i bu marshrutda **404** (begona bozor bilan bir xil).

    ⛔ 403 YOKI 409 BERILMAYDI: har ikkalasi ham «bunday topshiriq bor,
       lekin u boshqa navbatda» degan ma'lumotni oshkor qilardi va
       nazoratchi navbat a'zoligini javob kodi bo'yicha aniqlay olardi
       (D-14: `purpose` ham, navbat ham unga ko'rinmaydi).
    """
    blind_id = env.occupancy.market_a.blind_assignment_id

    response = await api_client.post(
        f"{REVIEW_URL}/{blind_id}/answer",
        json={"human_verdict": "occupied"},
        headers=inspector_headers,
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "not_found"


async def test_budget_endpoint_reports_both_queues(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """`GET /review/budget` ikkala navbatning uchligini beradi (UI-SPEC §7.2)."""
    await build_queue(tenant_session, env)
    item = (await api_client.get(NEXT_URL, headers=inspector_headers)).json()
    await api_client.post(
        f"{REVIEW_URL}/{item['assignment_id']}/answer",
        json={"human_verdict": "occupied"},
        headers=inspector_headers,
    )

    response = await api_client.get(BUDGET_URL, headers=inspector_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["day"] == business_today().isoformat()
    assert body["uncertain"] == {"answered": 1, "budget": 50, "remaining": 49}
    assert body["blind_audit"] == {"answered": 0, "budget": 30, "remaining": 30}


# ===========================================================================
# 6. SC#3 DARVOZALARI
# ===========================================================================

MINIMUM_SCANNED_ROUTES = 20
"""`test_no_bulk_approve_endpoint` skanerlashi SHART bo'lgan eng kam yozuv marshruti.

⛔ QUYI CHEGARASIZ DARVOZA JIMGINA BO'SHARDI: `app.openapi()` bir kun
   boshqacha tuzilma qaytarsa (yoki yurish nosozlansa) sxema bo'sh
   bo'lardi va «massiv qabul qiluvchi marshrut yo'q» asserti TRIVIAL
   ravishda o'tardi — aynan `test_runtime_deps.py::
   test_manifest_actually_parsed` va `test_sentry_processes.py` ning
   quyi chegarasi qo'riqlaydigan nosozlik sinfi.

Bugungi son — **44**; chegara ATAYIN pastroq qo'yilgan: u «sxema
o'qildimi?» ni o'lchaydi, marshrutlar SONINI emas. Aniq songa qadalganda
har yangi endpoint bu faylni tahrirlashni talab qilardi va darvoza
shovqinga aylanardi.
"""

REVIEW_ROUTER_MODULE = "app.api.v1.reviews"
"""Nazoratchi yuzasining MODULI — marshrut NOMLARI ro'yxati emas.

⚠ 04-12 ning darsi (§S-10): nomlar ro'yxati eskiradi va darvoza abadiy
  yashil bo'lib qoladi. Modul esa `main.py` da router sifatida ulanadi,
  ya'ni bu yuzaga qo'shilgan HAR QANDAY yangi marshrut — nomi qanday
  bo'lishidan qat'i nazar — darvozaga AVTOMATIK tushadi.
"""

FORBIDDEN_ITEM_KEYS = frozenset(
    {
        "verdict",
        "ai_verdict",
        "aiverdict",
        "system_verdict",
        "system_answer",
        "confidence",
        "model_version",
        "modelversion",
        "thresholds_version",
        "purpose",
        "queue_kind",
        "shown_ai_verdict",
        "effective_verdict",
        "resolution_source",
    }
)
"""Navbat payloadida uchramasligi SHART bo'lgan kalitlar (UI-SPEC §14.3).

⚠ BU RO'YXAT DARVOZANING YAGONA MEXANIZMI EMAS va bo'lishi ham mumkin
  emas: u faqat BILINGAN nomlarni ushlaydi.
  `test_next_item_has_no_system_answer` ning IKKINCHI qatlami — javob
  matnida verdikt SO'ZINING o'zini qidirish — nomdan MUSTAQIL va aynan
  shu ro'yxatda yo'q shakllarni (`meta.ai`, `debug.v`) qamraydi.
"""


def _resolve(schema: dict[str, Any], components: dict[str, Any], seen: frozenset[str]) -> Any:
    """`$ref` ni `components/schemas` dan ochadi (rekursiv havolaga chidamli)."""
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    name = ref.rsplit("/", 1)[-1]
    if name in seen:
        return {}
    return _resolve(components.get(name, {}), components, seen | {name})


def _array_carrying_names(
    schema: Any,
    components: dict[str, Any],
    seen: frozenset[str] = frozenset(),
    *,
    inside_array: bool = False,
) -> set[str]:
    """Massiv KO'TARADIGAN har bir nom — maydon nomi yoki `_ROOT`.

    Uchala shaklni ham qamraydi va ularning HAMMASI «ommaviy tasdiqlash»
    ning haqiqiy ko'rinishlari:

        {"answers": [{"human_verdict": ...}]}  -> `answers`, `human_verdict`
        {"assignment_ids": ["uuid", ...]}      -> `assignment_ids`
        [{"human_verdict": ...}]               -> `_ROOT`, `human_verdict`

    ⛔ FUNKSIYA QAROR QABUL QILMAYDI — u faqat TUZILMANI qaytaradi.
       Nomlar bilan solishtirish chaqiruvchida va u AYNAN IKKI predikat
       (`test_no_bulk_approve_endpoint`).
    """
    if not isinstance(schema, dict):
        return set()
    resolved = _resolve(schema, components, seen)
    if not isinstance(resolved, dict):
        return set()

    names: set[str] = set()
    if resolved.get("type") == "array" or "items" in resolved:
        names.add("_ROOT")
        names |= _array_carrying_names(
            resolved.get("items", {}), components, seen, inside_array=True
        )
        return names

    for keyword in ("anyOf", "oneOf", "allOf"):
        for option in resolved.get(keyword) or []:
            names |= _array_carrying_names(option, components, seen, inside_array=inside_array)

    for key, sub in (resolved.get("properties") or {}).items():
        child = _array_carrying_names(sub, components, seen, inside_array=inside_array)
        if inside_array or "_ROOT" in child:
            names.add(key)
        names |= child - {"_ROOT"}
    return names


def _write_operations(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """Sxemadagi har bir `POST`/`PUT`/`PATCH` amali."""
    return [
        (path, method.upper(), operation)
        for path, operations in spec["paths"].items()
        for method, operation in operations.items()
        if method.upper() in {"POST", "PUT", "PATCH"}
    ]


def _review_surface_paths() -> set[str]:
    """`REVIEW_ROUTER_MODULE` funksiyalariga tegishli YO'LLAR — ILOVADAN hosila."""
    found: set[str] = set()

    def _walk(routes: Any, prefix: str) -> None:
        for route in routes:
            included = getattr(route, "original_router", None)
            if included is not None:
                context = getattr(route, "include_context", None)
                _walk(included.routes, prefix + str(getattr(context, "prefix", "") or ""))
                continue
            endpoint = getattr(route, "endpoint", None)
            path = getattr(route, "path", None)
            if (
                endpoint is not None
                and path is not None
                and getattr(endpoint, "__module__", "") == REVIEW_ROUTER_MODULE
            ):
                found.add(prefix + path)

    _walk(fastapi_app.routes, "")
    return found


def test_no_bulk_approve_endpoint() -> None:
    """⛔ OMMAVIY TASDIQLASH ENDPOINTI YO'Q — OpenAPI SXEMASIDAN HOSILA (D-18).

    =======================================================================
    DARVOZA IKKI MUSTAQIL PREDIKATDAN IBORAT VA IKKALASI HAM NOMDAN
    EMAS, TUZILMADAN CHIQADI.

      (1) YUZA: nazoratchi routerining (`REVIEW_ROUTER_MODULE`) birorta
          yozuv marshruti massiv ko'taradigan tana QABUL QILMAYDI. Bu
          `POST /review/answer-many` ni ham, `POST /review/batch` ni ham,
          `PUT /review/answers` ni ham BIR XIL ushlaydi.

      (2) LUG'AT: butun API'da `AnswerRequest` ning maydoni MASSIV
          ICHIDA uchramaydi. Bu bulk yo'lni BOSHQA routerga ko'chirib
          yashirishni ham yopadi.

    ⛔ MARSHRUT NOMLARI RO'YXATI YOZILMAGAN va bu ataylab: aynan nomlar
       ro'yxati 04-12 ning darvozasini eskirtirgan edi (§S-10).
    =======================================================================
    """
    spec = fastapi_app.openapi()
    components = spec.get("components", {}).get("schemas", {})
    operations = _write_operations(spec)
    review_paths = _review_surface_paths()
    answer_field = next(iter(AnswerRequest.model_fields))

    assert len(operations) >= MINIMUM_SCANNED_ROUTES, (
        f"faqat {len(operations)} ta yozuv marshruti skanerlandi — sxema o'qilmadi"
    )
    assert review_paths, (
        f"`{REVIEW_ROUTER_MODULE}` dan birorta marshrut topilmadi — darvoza bo'sh yugurdi"
    )

    bulk_on_review_surface: list[str] = []
    bulk_answers_anywhere: list[str] = []
    for path, method, operation in operations:
        body = operation.get("requestBody", {}).get("content", {}).get("application/json", {})
        names = _array_carrying_names(body.get("schema", {}), components)
        if not names:
            continue
        if path in review_paths:
            bulk_on_review_surface.append(f"{method} {path}")
        if answer_field in names:
            bulk_answers_anywhere.append(f"{method} {path}")

    assert not bulk_on_review_surface, (
        "nazoratchi yuzasida massiv qabul qiluvchi marshrut paydo bo'ldi (D-18): "
        f"{sorted(bulk_on_review_surface)}"
    )
    assert not bulk_answers_anywhere, (
        f"`{answer_field}` massiv ichida qabul qilinmoqda (D-18): {sorted(bulk_answers_anywhere)}"
    )


def _all_keys(payload: Any) -> set[str]:
    """Ichma-ich joylashgan BARCHA kalitlar (`dict`/`list` bo'yicha rekursiv)."""
    keys: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.add(str(key).lower())
            keys |= _all_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            keys |= _all_keys(item)
    return keys


async def test_next_item_has_no_system_answer(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """⛔ JAVOB REKURSIV SKANERLANADI — MA'LUM MAYDON TEKSHIRILMAYDI (T-05-45).

    =======================================================================
    NEGA REKURSIV SKAN, NEGA `assert "verdict" not in body` EMAS.

    Ma'lum kalitni tekshiradigan test faqat O'ZI BILGAN nomni ko'radi.
    Tizim javobi `meta.verdict`, `debug.confidence` yoki `ai.value` bo'lib
    qaytsa u YASHIL qolardi — ya'ni darvoza o'zi qo'riqlayotgan xavfning
    eng ehtimolli shaklini ko'rmasdi.

    IKKI QATLAM VA ULAR MUSTAQIL:
      (a) ichma-ich HAR BIR kalit `FORBIDDEN_ITEM_KEYS` ga solishtiriladi;
      (b) javobning XOM MATNIDA verdikt SO'ZINING o'zi ham uchramaydi —
          navbatdagi HAR BANDNING verdikti `uncertain`, ya'ni bu so'z
          payloadda paydo bo'lsa u FAQAT tizim javobidan kelgan bo'lardi.
          Bu qatlam KALIT NOMIDAN mutlaqo mustaqil.
    =======================================================================
    """
    await build_queue(tenant_session, env)

    response = await api_client.get(NEXT_URL, headers=inspector_headers)

    assert response.status_code == 200, response.text
    leaked = sorted(FORBIDDEN_ITEM_KEYS & _all_keys(response.json()))
    assert not leaked, f"javobda tizim javobining kaliti bor: {leaked}"
    assert OccupancyVerdict.UNCERTAIN.value not in response.text.lower(), (
        "javob matnida tizim verdikti uchradi — payload ankor tashiydi"
    )


async def test_daily_budget_is_enforced(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """Byudjet tugagach **409 `review_budget_exhausted`** — «navbat bo'sh» EMAS.

    ⛔ IKKI KOD ATAYIN AJRATILGAN (UI-SPEC §8.3, S-7/S-8):
       `review_queue_empty` — ISH TUGADI;
       `review_budget_exhausted` — ISH QOLGAN BO'LISHI MUMKIN.
       Ularni bir xil ko'rsatish nazoratchida «hammasi bajarildi» degan
       YOLG'ON hosil qilardi.

    ⚠ NAZORAT: byudjet tugagan paytda navbatda BAND BOR (ikkinchi nomzod
      ataylab qo'shilgan) va byudjet qaytarilgach u HAQIQATAN beriladi.
      Usiz test byudjetni emas, navbat bo'shligini o'lchagan bo'lardi.
    """
    add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_45,
        center=(0.20, 0.70),
    )
    await build_queue(tenant_session, env)

    with _budget_of(api_app, uncertain=1):
        item = (await api_client.get(NEXT_URL, headers=inspector_headers)).json()
        answered = await api_client.post(
            f"{REVIEW_URL}/{item['assignment_id']}/answer",
            json={"human_verdict": "occupied"},
            headers=inspector_headers,
        )
        exhausted = await api_client.get(NEXT_URL, headers=inspector_headers)

    still_there = await api_client.get(NEXT_URL, headers=inspector_headers)

    assert answered.status_code == 200, answered.text
    assert exhausted.status_code == 409, exhausted.text
    assert exhausted.json()["detail"] == "review_budget_exhausted"
    assert still_there.status_code == 200, (
        "byudjet ko'tarilgach navbat bo'sh chiqdi — yuqoridagi 409 byudjetdan EMAS edi"
    )


async def test_empty_queue_uses_a_different_code_than_the_budget(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """Navbat bo'shligi `review_queue_empty` beradi — byudjet kodidan BOSHQA."""
    await build_queue(tenant_session, env)
    _answer_directly(sync_owner_conn, env, env.seed_assignment)

    response = await api_client.get(NEXT_URL, headers=inspector_headers)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "review_queue_empty"


async def test_priority_puts_billing_impact_first(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """HTTP yuzasida ham billing ta'siri BIRINCHI — SOZLAMA ulangani bilan.

    ⚠ `test_claim_next_prefers_the_stall_with_a_vendor` BILAN TAKROR EMAS:
      u repozitoriyni STANDART o'lchov nuqtasi bilan chaqiradi, bu esa
      `Settings.review_uncertain_midpoint` ning ROUTERGA ulanganini ham
      o'lchaydi.
    """
    add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_45,
        center=(0.20, 0.70),
    )
    await build_queue(tenant_session, env)

    response = await api_client.get(NEXT_URL, headers=inspector_headers)

    assert response.status_code == 200, response.text
    assert UUID(response.json()["stall_id"]) == env.assigned_stall


async def test_answer_is_recorded_once(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """Bitta javob = bitta qator; `shown_ai_verdict = false`, nusxa TOPSHIRIQDAN."""
    await build_queue(tenant_session, env)
    item = (await api_client.get(NEXT_URL, headers=inspector_headers)).json()

    response = await api_client.post(
        f"{REVIEW_URL}/{item['assignment_id']}/answer",
        json={"human_verdict": "occupied"},
        headers=inspector_headers,
    )

    assert response.status_code == 200, response.text
    rows = sync_owner_conn.execute(
        "SELECT queue_kind, shown_ai_verdict, human_verdict, reviewer_id "
        "FROM zone_reviews WHERE review_assignment_id = %s",
        (item["assignment_id"],),
    ).fetchall()
    assert len(rows) == 1
    queue_kind, shown, human, reviewer = rows[0]
    assert queue_kind == ReviewQueueKind.UNCERTAIN.value
    assert shown is False, "server `shown_ai_verdict` ni `true` yozdi"
    assert human == OccupancyVerdict.OCCUPIED.value
    assert UUID(str(reviewer)) == env.reviewer_id


async def test_decision_ms_is_server_measured(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """⛔ KLIENT YUBORGAN `decision_ms` E'TIBORSIZ QOLDIRILADI (T-05-46).

    Maydon `AnswerRequest` da UMUMAN e'lon qilinmagan, ya'ni Pydantic uni
    JIMGINA tashlaydi. Bazadagi qiymat SERVER o'lchovi bo'lishi kerak:
    testda band shu zahoti javoblanadi, ya'ni farq bir necha yuz
    millisekunddan oshmaydi.

    ⚠ NAZORAT: qiymat `NULL` HAM EMAS. Faqat «yuborilgan qiymat emas» ni
      tekshirish o'lchov BUTUNLAY ishlamay qolganda ham yashil bo'lardi —
      `NULL != 999999` ham rost.
    """
    client_value = 999_999
    await build_queue(tenant_session, env)
    item = (await api_client.get(NEXT_URL, headers=inspector_headers)).json()

    response = await api_client.post(
        f"{REVIEW_URL}/{item['assignment_id']}/answer",
        json={"human_verdict": "occupied", "decision_ms": client_value},
        headers=inspector_headers,
    )

    assert response.status_code == 200, response.text
    row = sync_owner_conn.execute(
        "SELECT decision_ms FROM zone_reviews WHERE review_assignment_id = %s",
        (item["assignment_id"],),
    ).fetchone()
    assert row is not None
    measured = row[0]
    assert measured != client_value, "klient yuborgan qiymat bazaga tushdi"
    assert measured is not None, "server o'lchovi bajarilmadi — qiymat NULL"
    assert 0 <= measured < 60_000, f"o'lchov mantiqsiz: {measured} ms"


async def test_uncertain_queue_excludes_events_already_in_blind_audit(
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """⛔ IKKI NAVBAT O'ZARO ISTISNO — `UNIQUE (occupancy_event_id)` (§C.8.3).

    Ko'r audit namunasi AVVAL tortiladi; noaniq navbat undan keyin
    quriladi va allaqachon tortilgan hodisani QAYTA olmaydi. Teskari
    tartibda xolis namuna aynan model IKKILANGAN holatlarsiz qolardi va
    o'lchangan aniqlik SUN'IY ko'tarilardi.
    """
    drawn = add_candidate(
        sync_owner_conn,
        env,
        stall_id=env.unassigned_stall,
        confidence=CONFIDENCE_0_45,
        center=(0.20, 0.70),
    )
    sync_owner_conn.execute(
        "INSERT INTO review_assignments "
        "(market_id, occupancy_event_id, audit_round_id, queue_kind, purpose) "
        "VALUES (%s, %s, %s, 'blind_audit', 'eval')",
        (str(env.market_a), str(drawn.event_id), str(env.occupancy.market_a.audit_round_id)),
    )

    written = await build_queue(tenant_session, env)

    assert written == 0, "ko'r auditga tortilgan hodisa noaniq navbatga ham tushdi"
    rows = sync_owner_conn.execute(
        "SELECT queue_kind FROM review_assignments WHERE occupancy_event_id = %s",
        (str(drawn.event_id),),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == ReviewQueueKind.BLIND_AUDIT.value


@contextmanager
def _budget_of(api_app: FastAPI, *, uncertain: int) -> Iterator[None]:
    """Kunlik byudjetni VAQTINCHA pasaytiradi.

    `test_settings` SESSIYA doirasida, ya'ni nusxa qaytariladi. Muqobil
    (haqiqatan 50 ta javob yozish) testni sekin va mo'rt qilardi va
    byudjetning SOZLAMA ekanini umuman o'lchamasdi.
    """
    original = api_app.state.settings
    api_app.state.settings = original.model_copy(
        update={"review_uncertain_daily_budget": uncertain}
    )
    try:
        yield
    finally:
        api_app.state.settings = original
