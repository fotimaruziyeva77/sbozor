"""Bandlik hisoboti yuzasi — DIREKTORNIKI, NAZORATCHINIKI EMAS (AI-04…AI-06).

=============================================================================
BU FAYL SOF FUNKSIYANING TESTINI TAKRORLAMAYDI.

`accuracy_report()` ning arifmetikasi `tests/unit/test_accuracy_report.py`
da, QO'LDA hisoblangan nazorat qiymatlari bilan o'lchangan. Bu yerda
faqat HAQIQIY BAZA ustida o'lchanadigan da'volar bor:

  1. HUQUQ — nazoratchi bu yuzani UMUMAN ocha olmaydi (T-05-58);
  2. `purpose = 'train'` filtri MAHSULOT YO'LIDA ishlaydimi (D-14);
  3. besh hisoblagich javobda BOR va nol bo'lganda ham chiqadimi;
  4. tur holati javobsizlarni SANAYDIMI va urug'ni ko'rsatmaydimi;
  5. javobda D-16 maydoni ham, patta/summa maydoni ham YO'Q.

⚠ `queue_kind` FILTRI BU YERDA O'LCHANMAYDI VA SABAB O'LCHANGAN:
  `ck_review_assignments_eval_needs_blind_audit` (05-05) `eval` +
  `uncertain` juftligini RAD ETADI, ya'ni ikki filtrni ajratadigan
  qatorni bazaga YOZIB BO'LMAYDI. U sof funksiya chegarasida
  (`test_uncertain_queue_rows_excluded`) o'lchanadi va da'vo o'sha yerda
  TORAYTIRILGAN.
=============================================================================
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.jobs.day_close import day_close
from fixtures.admin_api import session_headers
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import (
    OccupancyDomainSeed,
    add_zone_with_event,
    occupancy_rows,
)
from fixtures.snapshot_domain import SEED_BUSINESS_DATE, snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import OccupancyVerdict, ReviewPurpose, ReviewQueueKind

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

OCCUPANCY_URL = "/api/v1/occupancy"
ACCURACY_URL = "/api/v1/occupancy/accuracy"
ROUND_URL = "/api/v1/occupancy/round"

HIGH_CONFIDENCE = "0.9200"

EVAL_PAIRS = 20
"""Matritsaga tushadigan javoblar soni — AYNAN chegara (`MIN_SAMPLE_FOR_PERCENT`).

⚠ 20 TANLANGAN, 25 emas: chegaraning O'ZIDA `measured is True` bo'lishi
  «>=» va «>» ni ajratadi. Undan katta son bu farqni jimgina yo'qotardi.
"""

_INSERT_ASSIGNMENT = (
    "INSERT INTO review_assignments "
    "(id, market_id, occupancy_event_id, audit_round_id, queue_kind, purpose) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)
_INSERT_REVIEW = (
    "INSERT INTO zone_reviews "
    "(id, market_id, review_assignment_id, queue_kind, shown_ai_verdict, "
    " human_verdict, reviewer_id, decision_ms) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
)


class Env:
    """Besh qatlamli seed — `test_day_close.Env` shakli."""

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
    def camera_a(self) -> UUID:
        return self.occupancy.market_a.camera_id

    @property
    def snapshot_a(self) -> UUID:
        return self.occupancy.market_a.snapshot_with_ok_quality

    @property
    def spare_stall(self) -> UUID:
        stall_id = self.occupancy.market_a.stall_without_zone_id
        assert stall_id is not None, "nazorat: seed'da qamrovsiz rasta yo'q"
        return stall_id

    @property
    def audit_round(self) -> UUID:
        return self.occupancy.market_a.audit_round_id

    @property
    def reviewer_id(self) -> UUID:
        return self.base.market_a.admin_user_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    auth_seed: AuthSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """⚠ `auth_seed` `market_domain` DAN OLDIN — `test_blind_audit.env` qoidasi.

    pytest fixture'larni teskari tartibda yopadi, ya'ni nazoratchi
    foydalanuvchisi `zone_reviews` qatorlaridan KEYIN o'chiriladi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        yield Env(two_markets, market_domain, occupancy, auth_seed)


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Direktor — `REPORT_VIEW` BOR, `OCCUPANCY_REVIEW` YO'Q (D-07)."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def inspector_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Nazoratchi — `OCCUPANCY_REVIEW` BOR, `REPORT_VIEW` YO'Q."""
    return await session_headers(api_client, env.auth.inspector.phone, SEED_PASSWORD)


def add_answered_eval_item(
    conn: Connection[TupleRow],
    env: Env,
    *,
    version: int,
    system_verdict: str,
    human_verdict: str,
    purpose: str = ReviewPurpose.EVAL.value,
) -> None:
    """Zona + hodisa + KO'R AUDIT topshirig'i + inson javobi — bitta yo'lda.

    ⚠ `version` HAR CHAQIRUVDA BOSHQA:
      `uq_camera_zones_market_id_camera_id_stall_id_version` bir kamerada
      bir rastaga ikkinchi zonani faqat boshqa versiya bilan qabul
      qiladi.

    ⚠ `audit_round_id` MAJBURIY (`blind_audit_needs_round`) va u seed'ning
      turi — ya'ni qatorlar HAQIQIY doiraga bog'lanadi.
    """
    seeded = add_zone_with_event(
        conn,
        market_id=env.market_a,
        camera_id=env.camera_a,
        stall_id=env.spare_stall,
        snapshot_id=env.snapshot_a,
        verdict=system_verdict,
        confidence=HIGH_CONFIDENCE,
        center=(0.15 + 0.001 * version, 0.80),
        version=version,
    )
    assignment_id = uuid4()
    conn.execute(
        _INSERT_ASSIGNMENT,
        (
            str(assignment_id),
            str(env.market_a),
            str(seeded.event_id),
            str(env.audit_round),
            ReviewQueueKind.BLIND_AUDIT.value,
            purpose,
        ),
    )
    conn.execute(
        _INSERT_REVIEW,
        (
            str(uuid4()),
            str(env.market_a),
            str(assignment_id),
            ReviewQueueKind.BLIND_AUDIT.value,
            False,
            human_verdict,
            str(env.reviewer_id),
            1200,
        ),
    )


def fill_eval_sample(conn: Connection[TupleRow], env: Env, *, count: int, purpose: str) -> None:
    """`count` ta javob berilgan band — hammasi TO'G'RI (tizim = inson).

    ⚠ Hammasi to'g'ri bo'lgani ATAYIN: `train` qatorlar qo'shilganda
      raqam KO'TARILISHI kerak edi. Ular hisobga kirmasa, raqam
      O'ZGARMAYDI va farq o'lchanadigan bo'ladi.
    """
    for index in range(count):
        verdict = OccupancyVerdict.OCCUPIED.value if index % 2 else OccupancyVerdict.EMPTY.value
        add_answered_eval_item(
            conn,
            env,
            version=100 + index if purpose == ReviewPurpose.EVAL.value else 500 + index,
            system_verdict=verdict,
            human_verdict=verdict,
            purpose=purpose,
        )


async def accuracy(client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    """Seed kunini QAMRAYDIGAN davr — standart 30 kunlik oyna emas.

    ⚠ Seed kuni (`SEED_BUSINESS_DATE`) BUGUNDAN uzoq bo'lishi mumkin,
      ya'ni standart oyna uni qamramasligi mumkin edi va test JIMGINA
      bo'sh hisobot ustida yashil bo'lardi.
    """
    response = await client.get(
        ACCURACY_URL,
        headers=headers,
        params={
            "from": (SEED_BUSINESS_DATE - timedelta(days=1)).isoformat(),
            "to": (SEED_BUSINESS_DATE + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    payload: dict[str, Any] = response.json()
    return payload


# ===========================================================================
# 1. HUQUQ — T-05-58
# ===========================================================================


@pytest.mark.parametrize("url", [OCCUPANCY_URL, ACCURACY_URL, ROUND_URL])
async def test_the_inspector_cannot_reach_the_report(
    api_client: httpx.AsyncClient, inspector_headers: dict[str, str], url: str
) -> None:
    """⛔ NAZORATCHI O'Z ANIQLIGINI KO'RMAYDI — UCHALA marshrut ham 403.

    Sabab maxfiylikda emas: ko'rsa u RAQAMNI YAXSHILASHGA urinardi va
    o'lchov o'zi o'lchayotgan narsani o'zgartirardi. «Tez qaror» sanog'i
    esa aynan shu urinishning izi bo'lib qolardi.

    ⚠ UCHALA MARSHRUT HAM ALOHIDA sinaladi: bitta marshrutni sinash
      keyingi ijrochi qo'shadigan to'rtinchisini qamramasdi va huquq
      darvozasi marshrut bo'yicha «esdan chiqadigan» narsaga aylanardi.
    """
    response = await api_client.get(url, headers=inspector_headers)

    assert response.status_code == 403, f"{url}: {response.status_code} — {response.text}"


async def test_the_director_can_reach_the_report(
    api_client: httpx.AsyncClient, director_headers: dict[str, str]
) -> None:
    """NAZORAT: 403 huquqdan chiqyaptimi, marshrutning yo'qligidan emas.

    ⚠ USIZ YUQORIDAGI TEST MARSHRUT UMUMAN QAYD ETILMAGAN holatda ham
      yashil bo'lardi (404 emas, 403 — chunki huquq tekshiruvi
      routerdan oldin ishlaydi... yoki ishlamasdi va farq ko'rinmasdi).
    """
    response = await api_client.get(OCCUPANCY_URL, headers=director_headers)

    assert response.status_code == 200, response.text


# ===========================================================================
# 2. BESH HISOBLAGICH — NOL BO'LGANDA HAM
# ===========================================================================


async def test_the_day_report_returns_five_counters_even_at_zero(
    api_client: httpx.AsyncClient, director_headers: dict[str, str]
) -> None:
    """⛔ Beshala hisoblagich HAR DOIM javobda — hodisasi bo'lmagan kunda ham."""
    quiet_day = SEED_BUSINESS_DATE - timedelta(days=45)

    response = await api_client.get(
        OCCUPANCY_URL, headers=director_headers, params={"day": quiet_day.isoformat()}
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    for field in ("occupied", "empty", "default_empty", "no_coverage", "human_confirmed"):
        assert payload[field] == 0, f"`{field}` maydoni yo'q yoki noldan farq qiladi"
    assert payload["stalls"] == 0
    assert payload["items"] == []


async def test_the_day_report_matches_the_materialized_day(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """Kun yopilgandan keyin to'rt bo'lak YIG'INDISI rasta soniga teng.

    ⛔ NOMUVOFIQLIK DARVOZASI: `default_empty` yoki `no_coverage`
       `empty` ga qo'shilib ketsa yig'indi rasta sonidan OSHIB ketardi
       va bu darhol ko'rinadi (§11.4 ning «Rasta N ta» qatori).
    """
    sync_owner_conn.execute(
        "DELETE FROM stall_slot_occupancy WHERE market_id = %s", (str(env.market_a),)
    )
    await day_close(app_sessionmaker, business_date=SEED_BUSINESS_DATE)

    response = await api_client.get(
        OCCUPANCY_URL, headers=director_headers, params={"day": SEED_BUSINESS_DATE.isoformat()}
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    total = (
        payload["occupied"] + payload["empty"] + payload["default_empty"] + payload["no_coverage"]
    )

    assert total == payload["stalls"], f"to'rt bo'lak {total}, rasta soni {payload['stalls']}"
    assert len(payload["items"]) == payload["stalls"]
    assert payload["no_coverage"] >= 1, "nazorat: qamrovsiz rasta seed'da bor edi"
    assert payload["default_empty"] >= 1, "nazorat: javobsiz `uncertain` seed'da bor edi"


async def test_the_report_surface_declares_no_money_field(
    api_client: httpx.AsyncClient, director_headers: dict[str, str], env: Env
) -> None:
    """⛔ PATTA/SUMMA JAVOBDA YO'Q — 6-faza (§16.1).

    Bo'lsa direktor bu raqamni kunlik daromad deb o'qib, 6-faza kelganda
    IKKI XIL son ko'rardi.
    """
    response = await api_client.get(
        OCCUPANCY_URL, headers=director_headers, params={"day": SEED_BUSINESS_DATE.isoformat()}
    )
    body = response.text.lower()

    for forbidden in ("amount", "soum", "patta", "charge", "price"):
        assert forbidden not in body, f"hisobot javobida `{forbidden}` maydoni paydo bo'ldi"


# ===========================================================================
# 3. ANIQLIK — `train` FILTRI MAHSULOT YO'LIDA
# ===========================================================================


async def test_train_rows_do_not_change_the_number_on_the_real_path(
    sync_owner_conn: Connection[TupleRow],
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """⛔ `purpose = 'train'` qatorlar hisobotga KIRMAYDI — HAQIQIY baza ustida (D-14).

    ⚠ QO'SHILGAN `train` QATORLAR ATAYIN «MUKAMMAL» (tizim = inson):
      kirsalar `n` ham, `correct` ham KO'TARILARDI. Ular hisobga
      kirmasa — hech nima o'zgarmaydi va farq o'lchanadigan bo'ladi.

    ⚠ BU TEST SOF FUNKSIYA TESTINING TAKRORI EMAS: u yerda `train`
      qatorlari QO'LDA qurilgan dataclass edi, bu yerda esa ular
      HAQIQIY `review_assignments` qatorlari — ya'ni so'rov ularni
      olib kelayotganini va filtr AYNAN mahsulot yo'lida ishlayotganini
      o'lchaydi.
    """
    fill_eval_sample(sync_owner_conn, env, count=EVAL_PAIRS, purpose=ReviewPurpose.EVAL.value)
    before = await accuracy(api_client, director_headers)

    assert before["n"] >= EVAL_PAIRS, f"nazorat: `eval` namunasi yig'ilmadi ({before['n']})"
    assert before["measured"] is True

    fill_eval_sample(sync_owner_conn, env, count=8, purpose=ReviewPurpose.TRAIN.value)
    after = await accuracy(api_client, director_headers)

    assert after == before, "trening qatorlari aniqlik raqamini o'zgartirdi (D-14 buzilgan)"


async def test_no_percentage_below_the_threshold(
    api_client: httpx.AsyncClient, director_headers: dict[str, str], env: Env
) -> None:
    """⛔ `n < 20` da BIRORTA foiz maydoni `null`, xom sonlar esa QAYTADI.

    Seed'da AYNAN bitta javobli ko'r audit bandi bor, ya'ni bu holat
    qo'shimcha qurilmasdan mavjud.
    """
    payload = await accuracy(api_client, director_headers)

    assert payload["n"] < payload["min_sample"], f"nazorat: namuna kutilganidan katta ({payload})"
    assert payload["measured"] is False
    assert payload["base_rate"] is None
    for name in ("correct", "false_occupied", "false_empty"):
        assert payload[name] == {"point": None, "lower": None, "upper": None}, name

    # ⚠ XOM SONLAR BARIBIR QAYTADI: «hisobot yo'q» va «hali o'lchanmadi»
    #   bir xil ko'rinmasligi kerak.
    assert payload["matrix"]["true_occupied"] >= 1
    assert payload["drawn"] >= 1


async def test_the_accuracy_response_declares_no_self_consistency(
    api_client: httpx.AsyncClient, director_headers: dict[str, str], env: Env
) -> None:
    """⛔⛔ NAZORATCHINING ICHKI MOSLIGI (D-16) JAVOBDA YO'Q — na son, na maydon.

    05-11 o'lchadi: takroriy band bugungi sxemada IFODALAB BO'LMAYDI
    (`uq_review_assignments_occupancy_event_id` va
    `uq_zone_reviews_review_assignment_id`), ya'ni MEXANIZM QURILMAGAN.

    Uni `100 %` qilib ko'rsatish o'lchanmagan miqdorni o'lchangan qilib
    ko'rsatardi (T-05-04); bo'sh maydon qoldirish esa keyingi ijrochini
    unga son yozishga undardi. Shuning uchun MAYDONNING O'ZI yo'q.

    ⚠ IKKALA JAVOB HAM SKANERLANADI (`/accuracy` va `/round`): moslik
      «namuna holati» blokiga ham tabiiy ravishda yozilib qolishi mumkin
      edi (UI-SPEC §11.6 uni AYNAN o'sha blokda so'raydi).
    """
    forbidden = ("self_consistency", "consistency", "agreement", "repeat", "seed")

    for url in (ACCURACY_URL, ROUND_URL):
        response = await api_client.get(url, headers=director_headers)
        assert response.status_code == 200, response.text
        keys = set(response.json())
        for token in forbidden:
            assert not any(token in key for key in keys), (
                f"{url}: `{token}` ma'nosidagi maydon paydo bo'ldi — "
                "bu miqdor O'LCHANMAGAN (D-16) yoki KO'RSATILMASLIGI kerak (urug')"
            )


# ===========================================================================
# 4. TUR HOLATI — JAVOBSIZLAR SANALADI
# ===========================================================================


async def test_the_round_status_counts_unanswered_items(
    sync_owner_conn: Connection[TupleRow],
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """⛔ JAVOBSIZ BAND NAMUNADAN CHIQMAYDI — u «javobsiz» bo'lib sanaladi.

    Seed'ning turida bitta JAVOBLI band bor; bu test unga bitta
    JAVOBSIZ band qo'shadi va ikkala son ham alohida ko'rinishini
    o'lchaydi.
    """
    seeded = add_zone_with_event(
        sync_owner_conn,
        market_id=env.market_a,
        camera_id=env.camera_a,
        stall_id=env.spare_stall,
        snapshot_id=env.snapshot_a,
        verdict=OccupancyVerdict.OCCUPIED.value,
        confidence=HIGH_CONFIDENCE,
        center=(0.90, 0.90),
        version=900,
    )
    sync_owner_conn.execute(
        _INSERT_ASSIGNMENT,
        (
            str(uuid4()),
            str(env.market_a),
            str(seeded.event_id),
            str(env.audit_round),
            ReviewQueueKind.BLIND_AUDIT.value,
            ReviewPurpose.EVAL.value,
        ),
    )

    response = await api_client.get(
        ROUND_URL, headers=director_headers, params={"day": SEED_BUSINESS_DATE.isoformat()}
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["drawn"] is True
    assert payload["sample_size"] == 2
    assert payload["answered"] == 1
    assert payload["unanswered"] == 1, "javobsiz band sanoqdan tushib qoldi"
    assert payload["frame_size"] >= 1
    assert payload["round_no"] == 1


async def test_a_day_without_a_round_is_not_a_finished_one(
    api_client: httpx.AsyncClient, director_headers: dict[str, str], env: Env
) -> None:
    """⛔ «TUR TORTILMAGAN» va «HAMMASI BAJARILDI» BIR XIL KO'RINMAYDI.

    Ikkalasini bir kodga yig'ish tortish jobi butunlay o'lgan kunni
    muvaffaqiyat bo'lib ko'rsatardi — ya'ni O'LCHOV ASBOBINING YO'QLIGI
    yaxshi natijaga aylanardi (`review_repo._HAS_ANY_ROUND` qoidasi).
    """
    quiet_day = SEED_BUSINESS_DATE - timedelta(days=45)

    response = await api_client.get(
        ROUND_URL, headers=director_headers, params={"day": quiet_day.isoformat()}
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["drawn"] is False
    for name in ("round_no", "drawn_at", "frame_size", "sample_size", "answered", "unanswered"):
        assert payload[name] is None, f"tur tortilmagan kunda `{name}` son bilan qaytdi"


async def test_a_missing_decision_time_is_not_a_fast_decision(
    sync_owner_conn: Connection[TupleRow],
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """⛔ `decision_ms IS NULL` «tez qaror» sanog'iga KIRMAYDI (05-10 #7).

    Valkey uzilishi `decision_ms` ni `NULL` qoldiradi. Ularni «tez» deb
    sanash DIAGNOSTIKA nosozligini nazoratchining AYBIGA aylantirardi.

    ⚠ NAZORAT: seed'ning javobi `decision_ms = 4200` (sekin), ya'ni
      boshlang'ich sanoq NOL bo'lishi kerak — usiz «qo'shildi/qo'shilmadi»
      farqi ko'rinmasdi.
    """
    baseline = await api_client.get(
        ROUND_URL, headers=director_headers, params={"day": SEED_BUSINESS_DATE.isoformat()}
    )
    assert baseline.json()["fast_decisions"] == 0, "nazorat: seed'da tez qaror bor ekan"

    seeded = add_zone_with_event(
        sync_owner_conn,
        market_id=env.market_a,
        camera_id=env.camera_a,
        stall_id=env.spare_stall,
        snapshot_id=env.snapshot_a,
        verdict=OccupancyVerdict.EMPTY.value,
        confidence=HIGH_CONFIDENCE,
        center=(0.88, 0.12),
        version=910,
    )
    assignment_id = uuid4()
    sync_owner_conn.execute(
        _INSERT_ASSIGNMENT,
        (
            str(assignment_id),
            str(env.market_a),
            str(seeded.event_id),
            str(env.audit_round),
            ReviewQueueKind.BLIND_AUDIT.value,
            ReviewPurpose.EVAL.value,
        ),
    )
    sync_owner_conn.execute(
        _INSERT_REVIEW,
        (
            str(uuid4()),
            str(env.market_a),
            str(assignment_id),
            ReviewQueueKind.BLIND_AUDIT.value,
            False,
            OccupancyVerdict.EMPTY.value,
            str(env.reviewer_id),
            None,
        ),
    )

    response = await api_client.get(
        ROUND_URL, headers=director_headers, params={"day": SEED_BUSINESS_DATE.isoformat()}
    )
    payload = response.json()

    assert payload["answered"] == 2, "nazorat: yangi javob yozilmadi"
    assert payload["fast_decisions"] == 0, "`NULL` o'lchov «tez qaror» deb sanaldi"
