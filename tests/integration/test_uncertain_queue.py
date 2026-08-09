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

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from app.repositories.review_repo import ReviewRepository
from fixtures.admin_api import session_headers
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
from sbozor_core.enums import OccupancyVerdict, ReviewQueueKind
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import business_today
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    import httpx
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
        return self.domain.market_a.gap_stall_id

    @property
    def unassigned_stall(self) -> UUID:
        """Biriktirilmagan VA zonasiz rasta (`stall_ids[2]`)."""
        return self.domain.market_a.unassigned_stall_id

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
    """`queue_kind` TOPSHIRIQ QATORIDAN yoziladi — chaqiruvchi uni bera olmaydi.

    Ko'r audit topshirig'iga javob yozilganda qator `blind_audit` bo'lishi
    SHART: aks holda `fk_zone_reviews_queue_kind_anchor` uni rad etardi.
    Test AYNAN shu yo'lni yuradi — ya'ni u langarning ishlashini emas,
    SERVER TO'G'RI NUSXA olayotganini o'lchaydi (05-05 deviatsiya #5 ning
    05-10 dagi ochiq bandi).
    """
    market_b = env.base.market_b.id
    blind_id = env.occupancy.market_b.blind_assignment_id
    _delete_review(sync_owner_conn, env.occupancy.market_b.blind_review_id)

    async with tenant_session(market_b, env.base.market_b.admin_user_id) as session:
        answered = await repo(session, market_b).record_answer(
            blind_id,
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
