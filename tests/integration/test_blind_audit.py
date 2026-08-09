"""Ko'r audit — HOSILA URUG', MUZLATILGAN DOIRA va BESH HIMOYA (AI-04, SC#4).

=============================================================================
BU FAYL BUTUN FAZANING HALOLLIGI TURADIGAN JOY.

Qolgan hamma narsa noto'g'ri bo'lsa ham tuzatib bo'ladi. Jimgina og'gan
audit esa O'LCHOVGA O'XSHAGAN, lekin o'lchov BO'LMAGAN raqam ishlab
chiqaradi — va uni hech kim sezmaydi, chunki u yaxshilanib boradi.

Shu sababdan bu yerdagi har bir da'vo IKKI TOMONLAMA o'lchanadi: «shunday
bo'lishi kerak» ning yoniga «aks holda nima QIZARADI» qo'yiladi.
=============================================================================

⚠ RAD ETILGAN MUQOBILLARNING NOMLARI SHU FAYLDA YASHAYDI, MAHSULOT
  KODIDA EMAS (05-01 da o'rnatilgan va 03-07 da o'lchangan qoida):

    `ORDER BY random()` — qayta chiqarilmaydi, ya'ni «tasodifiy» da'vosi
                          TEKSHIRIB BO'LMAYDIGAN da'voligicha qoladi;
    `setseed()`         — urug'ni SAQLASH yaxshiroq, lekin urug'ni
                          TANLAGAN odam uni bir necha marta sinab ko'rishi
                          mumkin («bu namunada xato ko'p chiqdi, boshqa
                          urug' bilan qaytadan tortaman»);
    `digest(...)`       — `pgcrypto` bazada YO'Q (05-01 W0-3:
                          `PGCRYPTO_ABSENT = true`) va uni o'rnatish
                          `0018` ga kengaytma talabini qo'shardi.

  `app/jobs/audit_draw.py` faqat IJOBIY shaklda yozadi va
  `test_the_draw_module_names_no_rejected_alternative` buni MEXANIK
  ushlab turadi.

=============================================================================
NAMUNA MUSTAQIL QAYTA HISOBLANADI — JOB IKKINCHI MARTA CHAQIRILMAYDI.

Jobni qayta chaqirish faqat uning O'Z DETERMINIZMINI o'lchardi
(«bir xil kod ikki marta bir xil javob berdi»). Bu yerdagi qayta hisoblash
`hashlib` bilan, PYTHON da bajariladi — ya'ni u SQL dagi formulani
MUSTAQIL takrorlaydi. Ikki mustaqil yo'l bir xil to'plamga kelsa,
«namuna qayta chiqariladi» da'vosi o'lchangan bo'ladi.
=============================================================================
"""

from __future__ import annotations

import hashlib
import inspect
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from app.jobs import audit_draw as draw_module
from app.jobs.audit_draw import (
    FIRST_ROUND_NO,
    FRAME_PREDICATE_HASH,
    QueueTickPolicy,
    audit_draw,
    daily_queue_tick,
    eval_quota,
)
from app.main import app as fastapi_app
from app.repositories.review_repo import ReviewRepository
from app.schemas import AnswerResponse, BlindItemResponse, ReviewItemResponse
from fixtures.admin_api import session_headers
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import (
    CONFIDENCE_0_45,
    CONFIDENCE_0_55,
    CONFIDENCE_0_59,
    OccupancyDomainSeed,
    SeededEvent,
    add_zone_with_event,
    occupancy_rows,
)
from fixtures.snapshot_domain import SEED_BUSINESS_DATE, snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import OccupancyVerdict, ReviewPurpose, ReviewQueueKind

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

BLIND_NEXT_URL = "/api/v1/review/blind/next"
BLIND_URL = "/api/v1/review/blind"
REVIEW_URL = "/api/v1/review"

SAMPLE_SIZE = 4
"""Test namunasining hajmi — doiradan ANCHA KICHIK.

⚠ SON MAHSULOT QIYMATIDAN (30) FARQ QILADI VA BU ATAYIN: `frame` va
  `sample` teng bo'lsa «tartib» degan tushunchaning O'ZI yo'qoladi —
  har qanday tartib bir xil to'plam berardi va urug'ning ta'sirini
  o'lchaydigan HOLAT umuman mavjud bo'lmasdi.
"""

EVAL_RATIO = 0.70
"""D-14 ning nisbati — mahsulot standarti bilan AYNAN bir xil son."""

FRAME_TARGET = 12
"""Doiradagi nomzodlar soni.

`C(12, 4) = 495` — ya'ni ikki xil tartib TASODIFAN ayni to'plamni berish
ehtimoli 1/495. Kichik doirada (masalan 5 nomzod) urug'siz tartib ham
bir xil to'plam berib qolishi mumkin edi va nazorat holati JIMGINA
kuchsizlanardi (05-01 zondining `_FRAME_COUNT = 40` qarori bilan bir xil
mulohaza).
"""

REJECTED_ORDER_PATTERNS = (
    r"(?<![a-z_])random\s*\(",
    r"(?<![a-z_])setseed\s*\(",
    r"(?<![a-z_])digest\s*\(",
)
"""Mahsulot kodida UCHRAMASLIGI shart bo'lgan chaqiruvlar (fayl docstringi).

⚠⚠ SODDA `in` TEKSHIRUVI O'LCHANDI VA U YOLG'ON-QIZIL BERDI: `hexdigest()`
   ichida `digest(` bor, ya'ni `hashlib.sha256(...).hexdigest()` yozilgan
   HAR QANDAY fayl darvozani qizartirardi. Chegara IDENTIFIKATOR
   chegarasiga qo'yildi (`(?<![a-z_])`), ya'ni u `digest(` ni ushlaydi,
   `hexdigest(` ni esa YO'Q.

   Bu darvozani BO'SHATISH emas, TO'G'RILASH: taqiqlangan narsa —
   `pgcrypto` ning `digest()` FUNKSIYASI, `hexdigest` esa `hashlib` ning
   metodi va ular umuman boshqa narsa. `test_the_boundary_rejects_the_
   real_call` ikkala yo'nalishni ham qulflaydi.
"""


# ===========================================================================
# Muhit
# ===========================================================================


class Env:
    """To'rt qatlamli seed — bitta obyektda (`test_uncertain_queue.Env` shakli)."""

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
    def market_b(self) -> UUID:
        return self.base.market_b.id

    @property
    def camera_a(self) -> UUID:
        return self.occupancy.market_a.camera_id

    @property
    def snapshot_a(self) -> UUID:
        return self.occupancy.market_a.snapshot_with_ok_quality

    @property
    def stall_a(self) -> UUID:
        """Qo'shimcha nomzodlar yoziladigan rasta.

        ⚠ `unassigned_stall_id` TANLANGAN: unga sotuvchi biriktirilmagan,
          ya'ni ko'r audit tartibini `_BILLING_IMPACT` bilan ADASHTIRIB
          bo'lmaydi — namuna tartibi FAQAT urug'dan chiqishi kerak.
        """
        stall_id = self.domain.market_a.unassigned_stall_id
        assert stall_id is not None, "nazorat: `market_domain` da `unassigned_stall_id` yo'q"
        return stall_id

    @property
    def assigned_stall(self) -> UUID:
        """Biriktirilgan sotuvchisi BOR rasta — ustuvorlik testining zid qutbi."""
        stall_id = self.domain.market_a.gap_stall_id
        assert stall_id is not None, "nazorat: `market_domain` da `gap_stall_id` yo'q"
        return stall_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    auth_seed: AuthSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """Besh qatlamli seed; tozalash TESKARI tartibda (FK zanjiri bo'yicha).

    ⚠ `auth_seed` `market_domain` DAN OLDIN so'raladi va bu ATAYIN
      (`test_uncertain_queue.py` dagi jufti bilan bir xil sabab): pytest
      fixture'larni teskari tartibda yopadi, ya'ni nazoratchi
      foydalanuvchisi `zone_reviews` qatorlaridan KEYIN o'chiriladi.
      Teskari tartibda `fk_zone_reviews_reviewer_id_users` tozalashni
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


# ===========================================================================
# Yordamchilar — namunani MUSTAQIL qayta hisoblash
# ===========================================================================


def derived_seed(market_id: UUID, business_date: date, round_no: int) -> str:
    """Urug'ning PYTHON dagi mustaqil hosilasi.

    ⛔ MAHSULOT KODIDAN IMPORT QILINMAYDI VA BU BUTUN TESTNING MA'NOSI.
       Urug' SQL da hosil qilinadi (05-01 W0-3 o'lchagan yo'l); bu yerdagi
       shakl esa `hashlib` bilan qayta yoziladi. Import qilinganda ikkala
       tomon bitta xatoni birga qilardi va «qayta chiqariladi» da'vosi
       o'zini o'zi tasdiqlardi.

    Formula SQL dagi ifodaning aynan jufti:
        sha256(market_id::text || '|' || to_char(day, 'YYYY-MM-DD') || '|' || round::text)
    """
    payload = f"{market_id}|{business_date.isoformat()}|{round_no}"
    return hashlib.sha256(payload.encode()).hexdigest()


def expected_sample(event_ids: set[UUID], seed: str, size: int) -> list[UUID]:
    """Hosila urug' bo'yicha tortilishi KERAK bo'lgan namuna — tartibi bilan.

    Ro'yxat (to'plam emas) qaytadi: chaqiruvchi to'plam tengligini ham,
    kerak bo'lsa TARTIB tengligini ham o'lchay olsin (05-01
    `sample_ids()` bilan bir xil qaror).
    """
    ordered = sorted(event_ids, key=lambda item: hashlib.sha256(f"{item}{seed}".encode()).digest())
    return ordered[:size]


def expected_purposes(sample: list[UUID], seed: str, eval_ratio: float) -> dict[UUID, str]:
    """Har banddagi `purpose` — IKKINCHI, MUSTAQIL tartib bo'yicha kvota.

    ⚠ TARTIB NAMUNANIKIDAN BOSHQA (`|purpose` qo'shimchasi bilan): birinchi
      tartibni qayta ishlatish `eval` ulushini namunaning BOSHIGA
      yopishtirardi.
    """
    ranked = sorted(
        sample, key=lambda item: hashlib.sha256(f"{item}{seed}|purpose".encode()).digest()
    )
    quota = eval_quota(len(sample), eval_ratio)
    return {
        event_id: (ReviewPurpose.EVAL if index < quota else ReviewPurpose.TRAIN).value
        for index, event_id in enumerate(ranked)
    }


# ===========================================================================
# Yordamchilar — baza holati
# ===========================================================================


def clear_review_state(conn: Connection[TupleRow], market_id: UUID) -> None:
    """Bozorning navbat/tur qatorlarini olib tashlaydi — HODISALARGA TEGMASDAN.

    =======================================================================
    NEGA KERAK: SEED KUNNI ALLAQACHON «TORTILGAN» HOLATDA BERADI.

    `fixtures/occupancy_domain.py` `SEED_BUSINESS_DATE` uchun bitta
    `audit_rounds` qatori, ikkita `review_assignments` va bitta javob
    yozadi (05-05 ning AI-06 kirish holati). `audit_draw` ning
    PRESHARTI esa aynan buning teskarisi: kun uchun tur HALI YO'Q.

    Ya'ni tortishning O'ZINI o'lchash uchun kunni haqiqiy kun holatiga
    qaytarish kerak. `occupancy_events` TEGILMAYDI — u DOIRA va u
    o'zgarmas.
    =======================================================================

    ⚠ `zone_reviews` uchun QORALAMA BOZOR ISTISNOSI ishlatiladi
      (`cleanup_occupancy_domain()` bilan AYNAN bir xil mexanizm va bir
      xil sabab): javob SHARTSIZ o'zgarmas va yagona `DELETE` yo'li
      shu. Bayroq darhol qaytariladi.

    ⚠ `review_assignments` va `audit_rounds` da qo'riqchi YO'Q — ular
      bayroqsiz o'chiriladi va bu farq ATAYIN ko'rsatilgan: o'zgarmaslik
      INSON QARORIGA qo'yilgan, navbat yozuviga emas.
    """
    market = str(market_id)
    conn.execute("UPDATE markets SET is_active = false WHERE id = %s", (market,))
    conn.execute("DELETE FROM zone_reviews WHERE market_id = %s", (market,))
    conn.execute("UPDATE markets SET is_active = true WHERE id = %s", (market,))
    conn.execute("DELETE FROM review_assignments WHERE market_id = %s", (market,))
    conn.execute("DELETE FROM audit_rounds WHERE market_id = %s", (market,))


def frame_event_ids(conn: Connection[TupleRow], market_id: UUID, day: date) -> set[UUID]:
    """Doiradagi BARCHA hodisalar — verdiktdan QAT'I NAZAR.

    ⚠ `verdict` FILTRI ATAYIN YO'Q: doira `occupied`, `empty` VA
      `uncertain` ni qamraydi va bu testning kutishi mahsulot kodining
      shartini TAKRORLAMAYDI — u shartning NIYATINI yozadi.
    """
    rows = conn.execute(
        "SELECT id FROM occupancy_events WHERE market_id = %s AND business_date = %s",
        (str(market_id), day),
    ).fetchall()
    return {UUID(str(row[0])) for row in rows}


def blind_assignments(conn: Connection[TupleRow], market_id: UUID) -> dict[UUID, str]:
    """Ko'r audit topshiriqlari — `occupancy_event_id` -> `purpose`."""
    rows = conn.execute(
        "SELECT occupancy_event_id, purpose FROM review_assignments "
        "WHERE market_id = %s AND queue_kind = %s",
        (str(market_id), ReviewQueueKind.BLIND_AUDIT.value),
    ).fetchall()
    return {UUID(str(row[0])): str(row[1]) for row in rows}


def queued_event_ids(conn: Connection[TupleRow], market_id: UUID, queue_kind: str) -> set[UUID]:
    rows = conn.execute(
        "SELECT occupancy_event_id FROM review_assignments "
        "WHERE market_id = %s AND queue_kind = %s",
        (str(market_id), queue_kind),
    ).fetchall()
    return {UUID(str(row[0])) for row in rows}


def audit_round_row(conn: Connection[TupleRow], market_id: UUID, day: date) -> TupleRow | None:
    """Turning xom qatori — `(id, round_no, frame_size, predicate_hash, drawn_at)`."""
    row = conn.execute(
        "SELECT id, round_no, frame_size, frame_predicate_hash, drawn_at "
        "FROM audit_rounds WHERE market_id = %s AND business_date = %s",
        (str(market_id), day),
    ).fetchone()
    return row


def grow_frame(conn: Connection[TupleRow], env: Env, *, total: int) -> list[SeededEvent]:
    """Doirani `total` ta hodisagacha kengaytiradi — VERDIKTLARI ARALASH.

    ⚠ UCHALA VERDIKT HAM BO'LADI (`occupied`, `empty`, `uncertain`).
      Faqat bitta verdikt bilan to'ldirilgan doira «doira barcha
      verdiktlarni qamraydi» degan da'voni sinab ko'ra olmasdi.

    ⚠ HAR HODISA O'Z ZONASIDA: `version` oshiriladi, ya'ni
      `uq_camera_zones_market_id_camera_id_stall_id_version` ham,
      `uq_occupancy_events_market_id_snapshot_zone_model` ham
      qanoatlantiriladi va nomzodlar BIR kadrga osilib qoladi.
    """
    verdicts = (
        (OccupancyVerdict.UNCERTAIN.value, CONFIDENCE_0_55),
        (OccupancyVerdict.OCCUPIED.value, CONFIDENCE_0_59),
        (OccupancyVerdict.EMPTY.value, CONFIDENCE_0_45),
    )
    existing = len(frame_event_ids(conn, env.market_a, SEED_BUSINESS_DATE))
    created: list[SeededEvent] = []
    for index in range(existing, total):
        verdict, confidence = verdicts[index % len(verdicts)]
        created.append(
            add_zone_with_event(
                conn,
                market_id=env.market_a,
                camera_id=env.camera_a,
                stall_id=env.stall_a,
                snapshot_id=env.snapshot_a,
                verdict=verdict,
                confidence=confidence,
                # Markaz har zonada boshqa — poligonlar ustma-ust
                # tushmasin (geometrik fakt, verdikt bilan bog'liq emas).
                center=(0.15 + 0.05 * (index % 8), 0.15 + 0.05 * (index // 8)),
                # ⚠ `version` MAVJUD SONDAN boshlanadi, noldan EMAS:
                #   `grow_frame()` IKKI MARTA chaqirilganda (doiraning
                #   muzlashi testi) ikkinchi chaqiruv o'sha versiyalarni
                #   qayta yozib `uq_camera_zones_...` ni buzardi.
                version=index + 10,
            )
        )
    return created


def add_candidate(
    conn: Connection[TupleRow],
    env: Env,
    *,
    stall_id: UUID,
    center: tuple[float, float],
    verdict: str = OccupancyVerdict.OCCUPIED.value,
    confidence: str = CONFIDENCE_0_59,
    version: int = 90,
) -> SeededEvent:
    """BITTA nomzod — `grow_frame()` dan farqli, aynan bitta va nomlangan."""
    return add_zone_with_event(
        conn,
        market_id=env.market_a,
        camera_id=env.camera_a,
        stall_id=stall_id,
        snapshot_id=env.snapshot_a,
        verdict=verdict,
        confidence=confidence,
        center=center,
        version=version,
    )


def _open_round(conn: Connection[TupleRow], env: Env) -> UUID:
    """QO'LDA ochilgan tur — tartib testi tortish jobiga tayanmasligi uchun.

    ⚠ Job topshiriqlarni HOSILA URUG' tartibida yozadi, ya'ni test
      ularning YOZILISH tartibini boshqara olmasdi. `ORDER BY ra.id`
      da'vosi esa aynan yozilish tartibiga qarshi o'lchanadi.
    """
    row = conn.execute(
        "INSERT INTO audit_rounds "
        "(market_id, business_date, round_no, frame_size, frame_predicate_hash) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (str(env.market_a), SEED_BUSINESS_DATE, FIRST_ROUND_NO, 2, FRAME_PREDICATE_HASH),
    ).fetchone()
    assert row is not None
    return UUID(str(row[0]))


def _add_blind_assignment(
    conn: Connection[TupleRow], env: Env, round_id: UUID, event_id: UUID
) -> UUID:
    """Ko'r audit topshirig'i — `purpose = 'train'` (kvota testidan MUSTAQIL)."""
    row = conn.execute(
        "INSERT INTO review_assignments "
        "(market_id, occupancy_event_id, audit_round_id, queue_kind, purpose) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (
            str(env.market_a),
            str(event_id),
            str(round_id),
            ReviewQueueKind.BLIND_AUDIT.value,
            ReviewPurpose.TRAIN.value,
        ),
    ).fetchone()
    assert row is not None
    return UUID(str(row[0]))


async def draw(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    day: date = SEED_BUSINESS_DATE,
    sample_size: int = SAMPLE_SIZE,
    eval_ratio: float = EVAL_RATIO,
) -> draw_module.DrawResult:
    return await audit_draw(
        sessionmaker,
        business_date=day,
        sample_size=sample_size,
        eval_ratio=eval_ratio,
    )


# ===========================================================================
# 1. NAMUNA QAYTA CHIQARILADI — VA URUG' YUK KO'TARADI
# ===========================================================================


async def test_sample_is_reproducible(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """Namuna PYTHON da qayta hisoblanadi va bazadagi to'plamga AYNAN teng.

    ⛔ JOB IKKINCHI MARTA CHAQIRILMAYDI (fayl docstringi): u faqat o'z
       determinizmini o'lchardi. Bu yerda formulaning O'ZI ikkinchi,
       MUSTAQIL implementatsiyada takrorlanadi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    frame = frame_event_ids(sync_owner_conn, env.market_a, SEED_BUSINESS_DATE)
    assert len(frame) == FRAME_TARGET, "nazorat: doira kutilgan hajmda emas"

    result = await draw(app_sessionmaker)

    seed = derived_seed(env.market_a, SEED_BUSINESS_DATE, FIRST_ROUND_NO)
    expected = expected_sample(frame, seed, SAMPLE_SIZE)
    written = blind_assignments(sync_owner_conn, env.market_a)

    assert result.rounds == 1, f"tur ochilmadi: {result}"
    assert result.drawn == SAMPLE_SIZE
    assert set(written) == set(expected), "bazadagi namuna qayta hisoblangani bilan mos emas"


async def test_a_different_round_number_draws_a_different_sample(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """⚠ NAZORAT HOLATI — URUG' HAQIQATAN TARTIBGA TA'SIR QILADIMI.

    =======================================================================
    BU TEST 05-01 DA O'LCHANGAN NOSOZLIK SINFINI QO'RIQLAYDI.

    O'shanda `ORDER BY` dan urug'ni olib tashlash «ikki sessiyada bir xil
    namuna» testini YASHIL qoldirgan edi: urug'siz tartib ham
    determinstik, ya'ni «qayta chiqariladi» da'vosi aslida «urug' umuman
    ishlamaydi» degani bo'lishi mumkin edi.

    Shuning uchun yuqoridagi test YOLG'IZ YETARLI EMAS. Bu yerda BOSHQA
    tur raqami bilan hisoblangan namuna bazadagisidan FARQ QILISHI
    tekshiriladi — ya'ni urug' natijaga KIRADI.
    =======================================================================
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    frame = frame_event_ids(sync_owner_conn, env.market_a, SEED_BUSINESS_DATE)

    await draw(app_sessionmaker)

    written = set(blind_assignments(sync_owner_conn, env.market_a))
    other_round = set(
        expected_sample(
            frame, derived_seed(env.market_a, SEED_BUSINESS_DATE, FIRST_ROUND_NO + 1), SAMPLE_SIZE
        )
    )
    other_day = set(
        expected_sample(
            frame,
            derived_seed(env.market_a, SEED_BUSINESS_DATE + timedelta(days=1), FIRST_ROUND_NO),
            SAMPLE_SIZE,
        )
    )

    assert written != other_round, "tur raqami namunani o'zgartirmadi — urug' `ORDER BY` da emas"
    assert written != other_day, "kun namunani o'zgartirmadi — urug' `ORDER BY` da emas"


async def test_the_sample_query_orders_by_the_derived_seed() -> None:
    """Kompilyatsiya qilingan SQL matni — `sha256(` BOR, rad etilganlar YO'Q.

    ⚠ GREP EMAS, KOMPILYATSIYA: `str(stmt.compile())` AYNAN bazaga
      ketadigan matnni beradi, ya'ni izohdagi yoki qo'shni funksiyadagi
      tasodifiy uchrash darvozani chalg'ita olmaydi.
    """
    sql = str(draw_module._DRAW_SAMPLE.compile()).lower()  # noqa: SLF001

    assert "sha256(" in sql, "namuna tartibi `sha256` dan olinmagan"
    assert "order by" in sql
    leaked = _rejected_calls(sql)
    assert not leaked, f"namuna so'rovida rad etilgan tartib manbai bor: {leaked}"


def _rejected_calls(body: str) -> list[str]:
    """Matndagi rad etilgan CHAQIRUVLAR — identifikator chegarasi bilan."""
    return [pattern for pattern in REJECTED_ORDER_PATTERNS if re.search(pattern, body)]


def test_the_draw_module_names_no_rejected_alternative() -> None:
    """⛔ MAHSULOT MODULI RAD ETILGAN NOMLARNI IZOHDA HAM YOZMAYDI (03-07).

    Skanerlanadigan faylning izohida taqiqlangan token yozilsa darvoza
    O'ZINI O'ZI qizartiradi va yagona «tuzatish» yo'li darvozani
    BO'SHATISH bo'lardi. Sabablar shu faylning docstringida yashaydi —
    u skanerlanadigan to'plamda YO'Q.
    """
    source = inspect.getsource(draw_module).lower()

    leaked = _rejected_calls(source)
    assert not leaked, f"`audit_draw.py` da rad etilgan muqobilning nomi bor: {leaked}"
    assert "sha256" in source, "nazorat: modul umuman o'qilmadi"


def test_the_boundary_rejects_the_real_call() -> None:
    """⚠ CHEGARANING IKKALA YO'NALISHI — IJOBIY VA SALBIY NAZORAT.

    Darvoza `hexdigest(` ni o'tkazishi SHART (u `hashlib` ning metodi va
    shu faylning O'ZIDA ishlatiladi), `digest(` ni esa RAD ETISHI shart
    (u `pgcrypto` ning funksiyasi). Nazoratsiz «tuzatish» darvozani
    jimgina bo'shatgan bo'lardi.
    """
    assert not _rejected_calls("hashlib.sha256(payload).hexdigest()")
    assert not _rejected_calls("randomized_label = 1")

    assert _rejected_calls("order by digest(id::text, 'sha256')")
    assert _rejected_calls("order by random()")
    assert _rejected_calls("select setseed(0.5)")


# ===========================================================================
# 2. DOIRA — ENG QIYIN HOLATLARNI HAM QAMRAYDI, KEYIN MUZLAYDI
# ===========================================================================


async def test_frame_includes_uncertain(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """⛔ DOIRA `uncertain` HODISALARNI HAM QAMRAYDI — LITERAL TEST.

    «Faqat ishonchli javoblarni tekshiraylik» degan qisqartma model
    IKKILANGAN holatlarni o'lchovdan chiqarardi va aniqlik SUN'IY
    ko'tarilardi (05-RESEARCH §C.8, 2-dushman).

    ⚠ NAMUNA DOIRADAN KATTA OLINADI (`sample_size = frame_size`), ya'ni
      «tasodifan tushmadi» ehtimoli YO'Q: doiradagi HAR BIR hodisa
      tortilishi shart va tekshiruv LITERAL bo'ladi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    frame = frame_event_ids(sync_owner_conn, env.market_a, SEED_BUSINESS_DATE)

    uncertain_ids = {
        UUID(str(row[0]))
        for row in sync_owner_conn.execute(
            "SELECT id FROM occupancy_events "
            "WHERE market_id = %s AND business_date = %s AND verdict = %s",
            (str(env.market_a), SEED_BUSINESS_DATE, OccupancyVerdict.UNCERTAIN.value),
        ).fetchall()
    }
    assert uncertain_ids, "nazorat: doirada birorta `uncertain` hodisa yo'q"

    result = await draw(app_sessionmaker, sample_size=FRAME_TARGET)

    written = set(blind_assignments(sync_owner_conn, env.market_a))
    assert result.rounds == 1
    assert written == frame, "doira to'liq tortilmadi"
    assert uncertain_ids <= written, "`uncertain` hodisalar namunaga tushmadi"


async def test_the_round_freezes_the_frame(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """`frame_size`, `frame_predicate_hash` va `drawn_at` TO'LDIRILGAN va MUZLAGAN.

    ⚠ MUZLASH XULQ BILAN O'LCHANADI: tortishdan KEYIN yangi hodisa
      qo'shiladi va `frame_size` O'ZGARMASLIGI tekshiriladi. Faqat
      «ustun bo'sh emas» ni tekshiradigan test doira KEYIN qayta
      hisoblanadigan holatda ham yashil qolardi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)

    await draw(app_sessionmaker)

    row = audit_round_row(sync_owner_conn, env.market_a, SEED_BUSINESS_DATE)
    assert row is not None, "tur qatori yozilmadi"
    _round_id, round_no, frame_size, predicate_hash, drawn_at = row

    grow_frame(sync_owner_conn, env, total=FRAME_TARGET + 3)
    after = audit_round_row(sync_owner_conn, env.market_a, SEED_BUSINESS_DATE)
    assert after is not None

    assert round_no == FIRST_ROUND_NO
    assert frame_size == FRAME_TARGET
    assert predicate_hash == FRAME_PREDICATE_HASH
    assert drawn_at is not None
    assert after[2] == FRAME_TARGET, "doira KEYIN o'zgardi — u muzlatilmagan"
    assert len(frame_event_ids(sync_owner_conn, env.market_a, SEED_BUSINESS_DATE)) == (
        FRAME_TARGET + 3
    ), "nazorat: yangi hodisalar yozilmadi, ya'ni test hech nimani o'lchamadi"


async def test_the_predicate_hash_is_derived_from_the_predicate_text() -> None:
    """Xesh — SHARTNING matnidan hosila, qadalgan belgi EMAS.

    Doira jimgina toraysa (masalan `verdict <> 'uncertain'` qo'shilsa)
    eski turlarning xeshi yangilaridan FARQ QILADI va «o'sha kunlar
    boshqa qoida bilan tortilgan» degan fakt hisobotda ko'rinadi.
    """
    expected = hashlib.sha256(draw_module.FRAME_PREDICATE.encode()).hexdigest()

    assert expected == FRAME_PREDICATE_HASH
    assert len(FRAME_PREDICATE_HASH) == 64
    assert "verdict" not in draw_module.FRAME_PREDICATE, (
        "doira verdikt bo'yicha filtrlanmoqda — 2-dushman ochilgan"
    )


# ===========================================================================
# 3. 70/30 — TORTISH PAYTIDA, KVOTA BILAN
# ===========================================================================


async def test_purpose_is_a_quota_fixed_at_draw_time(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """`purpose` 70/30 kvotasi bo'yicha va u QAYTA HISOBLANADI (D-14).

    ⛔ HAR BANDNING QIYMATI TEKSHIRILADI, FAQAT ULUSH EMAS: ulush to'g'ri
       bo'lib, taqsimot boshqa qoidadan chiqqan holat (masalan «birinchi
       yettitasi `eval`») ulush testida YASHIL qolardi va o'shanda
       tortilish TARTIBI bilan baholanish TARTIBI bog'lanib qolardi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    frame = frame_event_ids(sync_owner_conn, env.market_a, SEED_BUSINESS_DATE)

    result = await draw(app_sessionmaker, sample_size=10)

    seed = derived_seed(env.market_a, SEED_BUSINESS_DATE, FIRST_ROUND_NO)
    sample = expected_sample(frame, seed, 10)
    expected = expected_purposes(sample, seed, EVAL_RATIO)
    written = blind_assignments(sync_owner_conn, env.market_a)

    assert result.drawn == 10
    assert result.eval_count == 7, f"70/30 kvotasi buzildi: {result}"
    assert written == expected, "har banddagi `purpose` qayta hisoblangani bilan mos emas"


DIVERGENT_RATIO = 0.28
DIVERGENT_DRAWN = 25
"""IEEE754 va o'nlik arifmetika HAQIQATAN farq qiladigan juftlik.

⚠⚠ BU JUFTLIK TANLANMADI, O'LCHANDI. Dastlab da'vo standart nisbatga
   (0,70) yozilgan edi va u YOLG'ON chiqdi: `math.ceil(0.70 * n)` bilan
   `math.ceil(Decimal("0.70") * n)` n = 1..200 oralig'ida BIRORTA joyda
   farq qilmaydi. Ya'ni «`numeric` bugun zarur» degan da'vo o'lchov bilan
   RAD ETILDI (05-03 sabotaj S2 ning aynan sinfidagi topilma: test o'z
   farazini tasdiqlayotgan edi).

   Da'vo TORAYTIRILDI va shu bilan KUCHAYDI: nisbat SOZLANADI
   (`review_blind_eval_ratio` (0, 1] ni qabul qiladi) va farq boshqa
   qiymatlarda CHIQADI. `0.28 x 25` — o'lchangan 27 ta ajralish
   holatidan biri.
"""


def test_eval_quota_uses_decimal_arithmetic() -> None:
    """⚠ RAD ETILGAN ARIFMETIKANING O'ZI ISHLATILIB, FARQI ISBOTLANADI.

    05-03 ning «fixture haqiqiyligi» asserti bilan bir xil naqsh: agar
    o'lchov nuqtasida ikkala yo'l bir xil javob bersa, test o'zi
    qo'riqlayotgan xususiyatni UMUMAN o'lchamagan bo'lardi.
    """
    import math

    assert math.ceil(DIVERGENT_RATIO * DIVERGENT_DRAWN) == 8, (
        "nazorat: rad etilgan arifmetika bu juftlikda boshqa javob bermayapti"
    )
    assert math.ceil(Decimal(str(DIVERGENT_RATIO)) * DIVERGENT_DRAWN) == 7

    assert eval_quota(DIVERGENT_DRAWN, DIVERGENT_RATIO) == 7, "kvota `float` yo'lidan yurdi"
    assert eval_quota(30, EVAL_RATIO) == 21
    assert eval_quota(10, EVAL_RATIO) == 7
    assert eval_quota(1, EVAL_RATIO) == 1, "bitta bandli namuna baholanmay qolmasin"


async def test_the_sql_quota_matches_the_decimal_one(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """⛔ O'LCHOV MAHSULOT YO'LIDA: kvota BAZADA ham o'nlik arifmetikada.

    `eval_quota()` ning yashil bo'lishi SQL haqida hech nima demaydi —
    kvota `_DRAW_SAMPLE` ning `ceil((:eval_ratio)::text::numeric * drawn)`
    ifodasida hisoblanadi. `float8` yo'li bu juftlikda **8** `eval`
    yozardi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=DIVERGENT_DRAWN)

    result = await draw(app_sessionmaker, sample_size=DIVERGENT_DRAWN, eval_ratio=DIVERGENT_RATIO)

    written = blind_assignments(sync_owner_conn, env.market_a)
    from_db = sum(1 for purpose in written.values() if purpose == ReviewPurpose.EVAL.value)

    assert result.drawn == DIVERGENT_DRAWN
    assert from_db == 7, f"SQL kvotasi `float8` yo'lidan yurdi: {from_db}"
    assert result.eval_count == eval_quota(DIVERGENT_DRAWN, DIVERGENT_RATIO)


# ===========================================================================
# 4. TAKRORLANMASLIK, BO'SH KUN VA TENANT CHEGARASI
# ===========================================================================


async def test_a_second_draw_on_the_same_day_changes_nothing(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """⛔ NAMUNANI QAYTA TORTISH YO'LI YO'Q (D-17.1).

    Ikkinchi chaqiruv YANGI tur ham, YANGI topshiriq ham yaratmaydi.
    Nazorat: birinchi chaqiruv HAQIQATAN tortgani ham tekshiriladi —
    usiz «hech nima bo'lmadi» holati idempotentlik deb o'qilardi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)

    first = await draw(app_sessionmaker)
    written_once = set(blind_assignments(sync_owner_conn, env.market_a))
    second = await draw(app_sessionmaker)
    written_twice = set(blind_assignments(sync_owner_conn, env.market_a))

    assert first.rounds == 1, "birinchi chaqiruv tur ochmadi"
    assert first.drawn == SAMPLE_SIZE
    assert second.rounds == 0, "ikkinchi chaqiruv YANGI tur ochdi"
    assert second.drawn == 0
    assert written_twice == written_once


async def test_an_empty_frame_opens_no_round(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """Nomzodsiz kunga doira TORTILMAYDI — `frame_size = 0` qatori yozilmaydi.

    Kadr olinmagan kun `alert_events` orqali ALLAQACHON ko'rinadi
    (4-faza); bu yerda ikkinchi signal kerak emas va u hisobotda
    «tortildi, lekin hech nima chiqmadi» qatorlarini to'plardi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    empty_day = SEED_BUSINESS_DATE + timedelta(days=7)
    assert not frame_event_ids(sync_owner_conn, env.market_a, empty_day), (
        "nazorat: tanlangan kun bo'sh emas"
    )

    result = await draw(app_sessionmaker, day=empty_day)

    assert result.rounds == 0
    assert audit_round_row(sync_owner_conn, env.market_a, empty_day) is None


async def test_the_draw_stays_inside_its_market(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """A bozorining namunasida B bozorining hodisasi YO'Q.

    ⚠ NAZORAT: B bozorida shu kunda hodisalar HAQIQATAN bor — aks holda
      bo'sh to'plamlarning kesishmasligi hech nimani o'lchamasdi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    foreign_frame = frame_event_ids(sync_owner_conn, env.market_b, SEED_BUSINESS_DATE)
    assert foreign_frame, "nazorat: B bozorida shu kunda hodisa yo'q"

    await draw(app_sessionmaker)

    written = set(blind_assignments(sync_owner_conn, env.market_a))
    assert written and not (written & foreign_frame)


# ===========================================================================
# 5. TARTIB — AVVAL KO'R AUDIT, KEYIN NOANIQ NAVBAT (§C.8.3)
# ===========================================================================


async def test_the_blind_draw_runs_before_the_uncertain_queue(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """⛔⛔ TARTIB XULQ BILAN O'LCHANADI, KOD O'QIB EMAS.

    =======================================================================
    O'LCHOVNING SHAKLI: DOIRA `uncertain` LARDAN TOZALANMAGANMI.

    Namuna doiraning HAMMASINI oladi (`sample_size = frame_size`), ya'ni
    to'g'ri tartibda BARCHA `uncertain` hodisalar KO'R AUDITGA tushadi va
    noaniq navbat BO'SH qoladi.

    Teskari tartibda noaniq navbat ularni oldin olib qo'yardi va ko'r
    audit ularni `ON CONFLICT DO NOTHING` bilan JIMGINA yo'qotardi —
    ya'ni xolis namuna aynan model IKKILANGAN holatlarsiz qolardi.

    ⚠ KOD TARTIBINING STATIK TEKSHIRUVI ALOHIDA TESTDA va u bu yerda
      YETARLI EMAS: matn tartibi to'g'ri turib, chaqiruv `await` siz
      yoki shartli bo'lishi mumkin edi.
    =======================================================================
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    frame = frame_event_ids(sync_owner_conn, env.market_a, SEED_BUSINESS_DATE)
    uncertain_ids = {
        UUID(str(row[0]))
        for row in sync_owner_conn.execute(
            "SELECT id FROM occupancy_events "
            "WHERE market_id = %s AND business_date = %s AND verdict = %s",
            (str(env.market_a), SEED_BUSINESS_DATE, OccupancyVerdict.UNCERTAIN.value),
        ).fetchall()
    }
    assert uncertain_ids, "nazorat: doirada `uncertain` hodisa yo'q"

    result = await daily_queue_tick(
        app_sessionmaker,
        business_date=SEED_BUSINESS_DATE,
        policy=QueueTickPolicy(
            sample_size=FRAME_TARGET,
            eval_ratio=EVAL_RATIO,
            uncertain_limit=50,
            midpoint=0.45,
        ),
    )

    blind = queued_event_ids(sync_owner_conn, env.market_a, ReviewQueueKind.BLIND_AUDIT.value)
    uncertain_queue = queued_event_ids(
        sync_owner_conn, env.market_a, ReviewQueueKind.UNCERTAIN.value
    )

    assert result.draw.drawn == FRAME_TARGET
    assert blind == frame, "ko'r audit doirani to'liq olmadi"
    assert uncertain_ids <= blind, "`uncertain` hodisalar ko'r auditga tushmadi"
    assert not uncertain_queue, "noaniq navbat ko'r auditdan OLDIN qurilgan"
    assert result.queued == 0


def test_the_tick_calls_the_draw_first_in_source_order() -> None:
    """Kod tartibi — `daily_queue_tick` ning MANBASIDAN o'lchanadi.

    ⚠ XULQ TESTINING JUFTI, O'RNI EMAS: xulq testi bugungi natijani
      o'lchaydi, bu esa NIYATNI qulflaydi — noaniq navbat qurish
      chaqiruvi ko'r audit chaqiruvidan OLDINGA ko'chirilsa darvoza
      qizaradi, hatto o'sha kuni ma'lumot holati farqni ko'rsatmasa ham.
    """
    source = inspect.getsource(daily_queue_tick)
    draw_at = source.index("audit_draw(")
    queue_at = source.index("_build_uncertain_queues(")

    assert draw_at < queue_at, "noaniq navbat ko'r audit tortishidan OLDIN chaqirilmoqda"
    assert re.search(r"result\.draw\s*=\s*await audit_draw\(", source), (
        "ko'r audit `await` bilan chaqirilmayapti"
    )


# ===========================================================================
# 6. KO'R SERIALIZER — MAYDONNING UMUMAN YO'QLIGI (D-17.2)
# ===========================================================================


FORBIDDEN_BLIND_KEYS = frozenset(
    {
        "verdict",
        "ai_verdict",
        "aiverdict",
        "system_verdict",
        "system_answer",
        "confidence",
        "aiconfidence",
        "model_version",
        "modelversion",
        "thresholds_version",
        "thresholdsversion",
        "purpose",
        "queue_kind",
        "shown_ai_verdict",
        "effective_verdict",
        "resolution_source",
        "round_no",
        "seed",
        "matched",
    }
)
"""Ko'r payloadda uchramasligi SHART bo'lgan kalitlar (UI-SPEC §14.3).

⚠ RO'YXAT DARVOZANING YAGONA MEXANIZMI EMAS va bo'lishi ham mumkin emas:
  u faqat BILINGAN nomlarni ushlaydi. Ikkinchi qatlam — javobning XOM
  MATNIDA verdikt SO'ZINING o'zini qidirish — kalit NOMIDAN mutlaqo
  mustaqil va `meta.v`, `debug.x` kabi shakllarni ham qamraydi.

⚠ `round_no`/`seed` — 05-11 QO'SHGAN nomlar (UI-SPEC §7.5: tur raqami va
  urug' Y-4 hisobotining yuzasi, sessiyaniki EMAS). `matched` esa OSHKOR
  javobning maydoni: u `POST` javobida QONUNIY, `GET` da esa oldindan
  yuklab qo'yish (prefetch) yo'lining ochilgani bo'lardi.
"""


def all_keys(payload: object) -> set[str]:
    """Ichma-ich joylashgan BARCHA kalitlar (`dict`/`list` bo'yicha rekursiv)."""
    keys: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.add(str(key).lower())
            keys |= all_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            keys |= all_keys(item)
    return keys


async def test_payload_has_no_verdict_keys(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """⛔ 1-INVARIANT — JAVOB REKURSIV SKANERLANADI, MA'LUM MAYDON EMAS.

    =======================================================================
    NEGA SKANER, NEGA `assert "verdict" not in body` EMAS.

    Ma'lum kalitni tekshiradigan test faqat O'ZI BILGAN nomni ko'radi.
    Tizim javobi `meta.verdict`, `debug.confidence` yoki `ai.value` bo'lib
    qaytsa u YASHIL qolardi — ya'ni darvoza o'zi qo'riqlayotgan xavfning
    eng ehtimolli shaklini ko'rmasdi. Bu 4-fazadagi «alertga kadr rasmi
    biriktirilmaydi» testining aynan shakli.

    IKKI MUSTAQIL QATLAM:
      (a) ichma-ich HAR BIR kalit reyestrga solishtiriladi;
      (b) javobning XOM MATNIDA verdikt so'zlarining O'ZI qidiriladi —
          bu qatlam kalit nomidan MUTLAQO mustaqil.
    =======================================================================
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    await draw(app_sessionmaker)

    response = await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    leaked = sorted(FORBIDDEN_BLIND_KEYS & all_keys(body))
    assert not leaked, f"ko'r payloadda tizim javobining kaliti bor: {leaked}"

    lowered = response.text.lower()
    verdict_words = sorted(value.value for value in OccupancyVerdict if value.value in lowered)
    assert not verdict_words, f"javob matnida verdikt so'zi uchradi: {verdict_words}"

    assert body["stall_code"], "nazorat: payload bo'sh — skan hech nimani o'lchamadi"
    assert len(body["polygon"]) >= 3


def test_the_blind_item_declares_none_of_the_eight_fields() -> None:
    """`BlindItemResponse` da SAKKIZALA maydonning BIRORTASI ham yo'q.

    ⚠ RUNTIME SKANIDAN MUSTAQIL IKKINCHI QATLAM: skan faqat SHU
      chaqiruvdagi qiymatni ko'radi, bu esa TIPNI ko'radi — ya'ni maydoni
      `None` bo'lib qaytgan holat ham ushlanadi.
    """
    declared = set(BlindItemResponse.model_fields)

    for field in (
        "verdict",
        "confidence",
        "model_version",
        "thresholds_version",
        "effective_verdict",
        "resolution_source",
        "shown_ai_verdict",
        "purpose",
    ):
        assert field not in declared, f"`BlindItemResponse` da `{field}` e'lon qilingan"

    assert declared == {
        "assignment_id",
        "snapshot_id",
        "stall_id",
        "stall_code",
        "zone_name",
        "camera_name",
        "channel_no",
        "business_date",
        "slot_time",
        "polygon",
    }, f"kutilmagan maydon to'plami: {sorted(declared)}"
    assert "has_active_vendor" in ReviewItemResponse.model_fields, (
        "nazorat: `has_active_vendor` noaniq navbatda ham yo'q — farq o'lchanmayapti"
    )


def test_the_blind_route_is_visible_in_the_schema() -> None:
    """⛔ MARSHRUT SXEMADAN YASHIRILMAGAN — YASHIRISH HIMOYA EMAS.

    `include_in_schema=False` faqat hujjatni o'zgartiradi, BAYTLARNI emas:
    marshrut baribir javob berardi va payloadning shakli o'zgarmasdi.
    Himoya maydonning UMUMAN yo'qligida, ya'ni sxemani yashirish yo'liga
    o'tish YOLG'ON xotirjamlik berardi.
    """
    paths = fastapi_app.openapi()["paths"]

    assert BLIND_NEXT_URL in paths, "ko'r audit marshruti sxemadan yashirilgan"
    assert "get" in paths[BLIND_NEXT_URL]
    assert "/api/v1/review/blind/{review_assignment_id}/answer" in paths


def _resolve(
    schema: dict[str, Any], components: dict[str, Any], seen: frozenset[str]
) -> dict[str, Any]:
    """`$ref` ni `components/schemas` dan ochadi (rekursiv havolaga chidamli)."""
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    name = ref.rsplit("/", 1)[-1]
    if name in seen:
        return {}
    resolved = components.get(name, {})
    return _resolve(resolved, components, seen | {name}) if isinstance(resolved, dict) else {}


def _schema_property_names(
    schema: object, components: dict[str, Any], seen: frozenset[str] = frozenset()
) -> set[str]:
    """Sxemadagi BARCHA maydon nomlari — ichma-ich va `$ref` lar bo'ylab."""
    if not isinstance(schema, dict):
        return set()
    resolved = _resolve(schema, components, seen)
    if not isinstance(resolved, dict):
        return set()
    ref = schema.get("$ref")
    seen = seen | {ref.rsplit("/", 1)[-1]} if isinstance(ref, str) else seen

    names: set[str] = set()
    for key, sub in (resolved.get("properties") or {}).items():
        names.add(str(key))
        names |= _schema_property_names(sub, components, seen)
    for keyword in ("items", "additionalProperties"):
        names |= _schema_property_names(resolved.get(keyword), components, seen)
    for keyword in ("anyOf", "oneOf", "allOf"):
        for option in resolved.get(keyword) or []:
            names |= _schema_property_names(option, components, seen)
    return names


def test_no_get_route_returns_the_reveal() -> None:
    """⛔ OSHKOR MA'LUMOT BIRORTA `GET` JAVOBIDA YO'Q — OpenAPI SKANI.

    =======================================================================
    NEGA BU DARVOZA KERAK: PREFETCH YO'LI.

    Tizim javobi nazoratchi javob YOZGANDAN KEYIN oshkor bo'ladi. Agar
    biror `GET` marshrut o'sha ma'lumotni qaytarsa, klient uni javobdan
    OLDIN yuklab qo'ya olardi (`useQuery` + `prefetch`) — ya'ni 2-himoya
    UI qatlamida buzilardi va server tomonda hech nima qizarmasdi
    (UI-SPEC §7.7).

    ⚠ KUTILGAN NOMLAR RO'YXATI YOZILMAGAN: nomlar `AnswerResponse` ning
      O'ZIDAN olinadi, ya'ni sxemaga yangi maydon qo'shilsa darvoza uni
      AVTOMATIK qo'riqlaydi (§S-5).
    =======================================================================
    """
    spec = fastapi_app.openapi()
    components = spec.get("components", {}).get("schemas", {})
    reveal_fields = set(AnswerResponse.model_fields) - {"locked"}
    assert reveal_fields, "nazorat: oshkor javobning maydonlari topilmadi"

    scanned = 0
    leaking: list[str] = []
    for path, operations in spec["paths"].items():
        operation = operations.get("get")
        if operation is None:
            continue
        scanned += 1
        for response in (operation.get("responses") or {}).values():
            schema = (response.get("content") or {}).get("application/json", {}).get("schema", {})
            if reveal_fields & _schema_property_names(schema, components):
                leaking.append(f"GET {path}")

    assert scanned >= 20, f"faqat {scanned} ta `GET` marshruti skanerlandi — sxema o'qilmadi"
    assert not leaking, f"oshkor ma'lumot `GET` javobida qaytmoqda: {sorted(set(leaking))}"


async def test_the_second_answer_is_locked_not_a_race(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """Ikkinchi javob -> **409 `blind_answer_locked`** (`review_already_answered` EMAS).

    ⛔ KOD AJRATILGAN VA FARQ MAHSULOTDA: noaniq navbatda ikkinchi so'rov
       shunchaki KECH QOLGAN (ikki oyna), ko'r auditda esa taqiq
       STRUKTURAVIY va UI qayta urinish tugmasi BERMAYDI (UI-SPEC §4.5).

    ⚠ NAZORAT: birinchi javob 200 va u OSHKOR ma'lumotni tashiydi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    await draw(app_sessionmaker)

    item = (await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)).json()
    target = f"{BLIND_URL}/{item['assignment_id']}/answer"

    first = await api_client.post(
        target, json={"human_verdict": "occupied"}, headers=inspector_headers
    )
    second = await api_client.post(
        target, json={"human_verdict": "empty"}, headers=inspector_headers
    )

    assert first.status_code == 200, first.text
    assert set(first.json()) == {"system_answer", "human_answer", "matched", "locked"}
    assert first.json()["locked"] is True
    assert second.status_code == 409, second.text
    assert second.json()["detail"] == "blind_answer_locked"


async def test_blind_rows_never_show_the_ai_verdict(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """`shown_ai_verdict` SERVERDA hisoblanadi va u BAZADAN o'qib tekshiriladi.

    ⚠ KLIENT QIYMATI YUBORILADI VA U TASHLANISHI KERAK: `AnswerRequest`
      da bunday maydon umuman e'lon qilinmagan, ya'ni Pydantic uni
      JIMGINA tashlaydi (05-10 deviatsiya #9 — `extra="forbid"` ATAYIN
      qo'yilmagan).
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    await draw(app_sessionmaker)

    item = (await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)).json()
    response = await api_client.post(
        f"{BLIND_URL}/{item['assignment_id']}/answer",
        json={"human_verdict": "occupied", "shown_ai_verdict": True},
        headers=inspector_headers,
    )

    assert response.status_code == 200, response.text
    rows = sync_owner_conn.execute(
        "SELECT shown_ai_verdict, queue_kind FROM zone_reviews WHERE market_id = %s",
        (str(env.market_a),),
    ).fetchall()
    assert rows, "nazorat: javob umuman yozilmadi"
    assert all(row[0] is False for row in rows), "ko'r yozuvda `shown_ai_verdict` rost"
    assert {str(row[1]) for row in rows} == {ReviewQueueKind.BLIND_AUDIT.value}


async def test_an_undrawn_market_says_so_instead_of_done(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """Namuna TORTILMAGAN bo'lsa -> `review_sample_not_drawn`, «tugadi» EMAS.

    ⛔ IKKALASINI BITTA KODGA YIG'ISH tortish jobi butunlay o'lgan kunni
       «hammasi bajarildi» bilan bir xil ko'rsatardi — o'lchov asbobining
       YO'QLIGI muvaffaqiyat bo'lib ko'rinardi.

    ⚠ NAZORAT JUFTI QUYIDA (`test_a_finished_sample_says_done`).
    """
    clear_review_state(sync_owner_conn, env.market_a)

    response = await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "review_sample_not_drawn"


async def test_a_finished_sample_says_done(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """Namuna tortilgan va TUGATILGAN bo'lsa -> `review_queue_empty`.

    ⚠ YUQORIDAGI TESTNING NAZORAT JUFTI: usiz `review_sample_not_drawn`
      HAR DOIM qaytadigan holat ham yashil bo'lardi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    await draw(app_sessionmaker, sample_size=1)

    item = (await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)).json()
    answered = await api_client.post(
        f"{BLIND_URL}/{item['assignment_id']}/answer",
        json={"human_verdict": "empty"},
        headers=inspector_headers,
    )
    exhausted = await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)

    assert answered.status_code == 200, answered.text
    assert exhausted.status_code == 409, exhausted.text
    assert exhausted.json()["detail"] == "review_queue_empty"


async def test_the_blind_queue_has_no_priority(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """⛔ KO'R NAVBAT USTUVORLIKKA EGA EMAS — `_PRIORITY_ORDER` ISHLATILMAYDI.

    =======================================================================
    IKKI TARTIB ATAYIN ZID QILIB QO'YILGAN.

    Biriktirilmagan rastaning topshirig'i BIRINCHI yoziladi (`uuidv7()`
    monoton, ya'ni uning `id` i kichik), biriktirilgani esa IKKINCHI.
    `_BLIND_ORDER` (`ORDER BY ra.id`) birinchisini beradi;
    `_PRIORITY_ORDER` esa billing ta'siri bo'yicha IKKINCHISINI berardi.

    NEGA MUHIM: nazoratchi ulgurmasa javobsiz QUYRUQ hisobotga
    «javobsiz» bo'lib kiradi. Quyruq billing ta'siri bo'yicha saralangan
    bo'lsa, u TIZIMLI ravishda sotuvchisi YO'Q rastalardan iborat
    bo'lardi va aniqlik faqat biriktirilgan rastalarda o'lchanardi.
    =======================================================================
    """
    clear_review_state(sync_owner_conn, env.market_a)
    round_id = _open_round(sync_owner_conn, env)

    unassigned = add_candidate(sync_owner_conn, env, stall_id=env.stall_a, center=(0.60, 0.20))
    assigned = add_candidate(sync_owner_conn, env, stall_id=env.assigned_stall, center=(0.20, 0.60))
    _add_blind_assignment(sync_owner_conn, env, round_id, unassigned.event_id)
    _add_blind_assignment(sync_owner_conn, env, round_id, assigned.event_id)

    async with tenant_session(env.market_a) as session:
        claimed = await ReviewRepository(session, env.market_a).claim_next_blind()

    assert claimed is not None
    assert claimed.has_active_vendor is False, (
        "ko'r navbat billing ta'siri bo'yicha saraladi — `_PRIORITY_ORDER` ishlatilmoqda"
    )
    assert claimed.stall_id == unassigned.stall_id
    assert assigned.stall_id != unassigned.stall_id, "nazorat: ikki rasta bir xil"


async def test_the_uncertain_route_cannot_answer_a_blind_item(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """Ko'r topshirig'i NOANIQ marshrutda **404** va aksincha ham.

    ⛔ 403 YOKI 409 EMAS: har ikkalasi ham «bunday topshiriq bor, lekin u
       boshqa navbatda» degan ma'lumotni oshkor qilardi va nazoratchi
       navbat a'zoligini javob KODI bo'yicha aniqlay olardi (D-14).
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    await draw(app_sessionmaker)
    blind_item = (await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)).json()

    wrong_route = await api_client.post(
        f"{REVIEW_URL}/{blind_item['assignment_id']}/answer",
        json={"human_verdict": "occupied"},
        headers=inspector_headers,
    )
    right_route = await api_client.post(
        f"{BLIND_URL}/{blind_item['assignment_id']}/answer",
        json={"human_verdict": "occupied"},
        headers=inspector_headers,
    )

    assert wrong_route.status_code == 404, wrong_route.text
    assert wrong_route.json()["detail"] == "not_found"
    assert right_route.status_code == 200, right_route.text


async def test_the_director_cannot_reach_the_blind_queue(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    director_headers: dict[str, str],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """`report_view` bor, `occupancy_review` yo'q -> **403**.

    NAZORAT: o'sha navbatni nazoratchi 200 bilan oladi — usiz «endpoint
    umuman ishlamayapti» holati ham yashil bo'lardi.
    """
    clear_review_state(sync_owner_conn, env.market_a)
    grow_frame(sync_owner_conn, env, total=FRAME_TARGET)
    await draw(app_sessionmaker)

    denied = await api_client.get(BLIND_NEXT_URL, headers=director_headers)
    allowed = await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)

    assert denied.status_code == 403, denied.text
    assert allowed.status_code == 200, allowed.text
