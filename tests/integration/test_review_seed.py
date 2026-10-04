"""Urug' rejimi — MODEL YO'Q PAYTDA nazoratchi navbatini to'ldirish.

=============================================================================
NEGA BU BOR.

`review_assignments.occupancy_event_id` — `NOT NULL`. Ya'ni nazoratchi
navbati AI hodisasisiz qurilmaydi, hodisani esa modeli bor `cv-service`
yozadi. Birinchi kunda model YO'Q va dataset ham yo'q:

    model -> hodisa -> navbat -> javob -> dataset -> model

Halqa yopiq va o'zi ochilmaydi. `review_seed.py` uni bir joyda kesadi:
hodisa MODELSIZ yoziladi, lekin `model_version='seed-v0'` va
`confidence=0` bilan — ya'ni u hech qachon model bashorati bilan
adashtirilmaydi.

⛔ ENG MUHIM DA'VO — oxirgi test: urug' javoblari ANIQLIK hisobiga
   TUSHMAYDI. Tushsa, model yo'q holatda «tizim aniqligi» degan son
   paydo bo'lardi va u nazoratchining javobini o'ziga solishtirgan
   bo'lardi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from app.repositories.review_repo import ReviewRepository
from app.services.review_seed import (
    SEED_CONFIDENCE,
    SEED_MODEL_VERSION,
    seed_snapshot,
)
from fixtures import TenantSessionFactory
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.enums import ReviewQueueKind


def _scalar(conn: Connection[TupleRow], sql: str, params: tuple[object, ...]) -> object:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return None if row is None else row[0]


def _zonali_ok_kadr(conn: Connection[TupleRow], market_id: UUID) -> UUID:
    """Zonasi CHIZILGAN kameraning yaroqli kadri.

    ⚠ IKKALA SHART HAM MAJBURIY: zonasiz kamera uchun urug' yozilmaydi
      (yozadigan narsa yo'q), yaroqsiz kadr uchun esa `occupancy_events`
      ning kompozit FK'si `(id, true)` juftligini topa olmaydi (D-21).
    """
    kadr = _scalar(
        conn,
        """
        SELECT s.id FROM snapshots s
          JOIN camera_zones cz
            ON cz.market_id = s.market_id
           AND cz.camera_id = s.camera_id
           AND cz.is_active
         WHERE s.market_id = %s AND s.quality_verdict = 'ok'
         ORDER BY s.captured_at
         LIMIT 1
        """,
        (market_id,),
    )
    assert kadr is not None, "fixture zonali yaroqli kadr bermadi"
    return kadr  # type: ignore[return-value]


@pytest.fixture
def zonali_kadr(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[UUID]:
    """Zonasi chizilgan kameraning yaroqli kadri — urug' uchun minimum.

    ⚠ `occupancy_rows` ZONALARNI ham yaratadi va shuning uchun kerak,
      garchi u yonida MODEL hodisalarini ham yozsa. Bu urug'ga XALAL
      BERMAYDI: `uq_occupancy_events_..._model` kalitida `model_version`
      bor, ya'ni `seed-v0` mavjud `demo-*` qatorining yoniga tushadi —
      va aynan shu narsa test qilinadigan holat (model paydo bo'lgan
      kunda ikkalasi bir vaqtda bo'lishi mumkin).
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps),
    ):
        yield _zonali_ok_kadr(sync_owner_conn, two_markets.market_a.id)


async def test_urug_hodisa_va_navbat_YARATADI(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    zonali_kadr: UUID,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """Halqa kesildi: modelsiz ham kadr nazoratchi navbatiga tushadi."""
    market_id = two_markets.market_a.id
    kadr = zonali_kadr

    async with tenant_session(market_id) as session:
        natija = await seed_snapshot(session, market_id=market_id, snapshot_id=kadr)

    assert natija.seeded >= 1, "urug' hodisa yozilmadi"

    navbat = _scalar(
        sync_owner_conn,
        """
        SELECT count(*) FROM review_assignments ra
          JOIN occupancy_events oe ON oe.id = ra.occupancy_event_id
         WHERE ra.market_id = %s AND oe.model_version = %s
           AND ra.queue_kind = 'uncertain' AND ra.purpose = 'train'
        """,
        (market_id, SEED_MODEL_VERSION),
    )
    assert navbat == natija.seeded, "hodisa yozildi, lekin navbatga tushmadi"


async def test_hodisa_MODEL_DEB_KORINMAYDI(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    zonali_kadr: UUID,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """⛔ UCH MAYDON BIRGA: `uncertain` + `0.0` + `seed-v0`.

    `verdict='uncertain'` yolg'iz yetmaydi — model ham `uncertain`
    berishi mumkin. Ajratuvchi belgi `model_version` va u hisobotda
    KO'RINADI: `seed-v0` qatorini ko'rgan odam uni bashorat deb o'qiy
    olmaydi. `confidence=0` esa «taxmin ham qilinmagan» deydi.
    """
    market_id = two_markets.market_a.id
    kadr = zonali_kadr

    async with tenant_session(market_id) as session:
        await seed_snapshot(session, market_id=market_id, snapshot_id=kadr)

    qator = _scalar(
        sync_owner_conn,
        """
        SELECT count(*) FROM occupancy_events
         WHERE market_id = %s AND snapshot_id = %s
           AND model_version = %s AND verdict = 'uncertain' AND confidence = %s
        """,
        (market_id, kadr, SEED_MODEL_VERSION, SEED_CONFIDENCE),
    )
    assert isinstance(qator, int) and qator >= 1, (
        "urug' hodisasi kutilgan uch maydon bilan yozilmadi"
    )


async def test_IDEMPOTENT_ikkinchi_yugurish_dublikat_yaratmaydi(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    zonali_kadr: UUID,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """Kadr ikki marta qayta ishlansa ham nazoratchi bir marta ko'radi.

    Kadr qayta ishlanishi NORMAL: job qayta urinishi mumkin. Ikkinchi
    hodisa nazoratchiga o'sha rasmni IKKINCHI marta ko'rsatardi va
    dataset'da bir kadr ikki javob bilan yotardi.
    """
    market_id = two_markets.market_a.id
    kadr = zonali_kadr

    async with tenant_session(market_id) as session:
        birinchi = await seed_snapshot(session, market_id=market_id, snapshot_id=kadr)
    async with tenant_session(market_id) as session:
        ikkinchi = await seed_snapshot(session, market_id=market_id, snapshot_id=kadr)

    assert birinchi.seeded >= 1
    assert ikkinchi.seeded == 0, "ikkinchi yugurish navbatga dublikat qo'shdi"
    assert ikkinchi.events_created == 0, "ikkinchi yugurish hodisa dublikatini yozdi"


async def test_ANIQLIK_HISOBIGA_TUSHMAYDI(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    zonali_kadr: UUID,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """⛔⛔ ENG MUHIM DA'VO.

    Aniqlik FAQAT `blind_audit` + `purpose='eval'` dan hisoblanadi
    (`accuracy_report.py`). Urug' esa `uncertain` + `train` yozadi.

    Agar urug' javoblari aniqlikka tushsa, model YO'Q holatda «tizim
    aniqligi 87%» degan son paydo bo'lardi — nazoratchi o'z javobini
    o'ziga solishtirgan bo'lardi va bu son hech nimani o'lchamasdi.
    """
    market_id = two_markets.market_a.id
    kadr = zonali_kadr

    async with tenant_session(market_id) as session:
        await seed_snapshot(session, market_id=market_id, snapshot_id=kadr)

    eval_soni = _scalar(
        sync_owner_conn,
        """
        SELECT count(*) FROM review_assignments ra
          JOIN occupancy_events oe ON oe.id = ra.occupancy_event_id
         WHERE ra.market_id = %s AND oe.model_version = %s
           AND (ra.purpose = 'eval' OR ra.queue_kind = 'blind_audit')
        """,
        (market_id, SEED_MODEL_VERSION),
    )
    assert eval_soni == 0, (
        "urug' hodisasi eval/ko'r audit navbatiga tushgan — aniqlik "
        "hisoboti modelsiz son chiqarardi"
    )


async def test_navbat_yoqolsa_KEYINGI_YUGURISH_TIKLAYDI(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    zonali_kadr: UUID,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """⛔ HODISA BOR, NAVBAT YO'Q — kadr NAVBATSIZ QOLMASLIGI kerak.

    260828 da jonli o'lchandi: `INSERT ... RETURNING` faqat YANGI
    qatorlarni beradi, ya'ni hodisa allaqachon bor bo'lsa navbat
    umuman yozilmasdi. Kadr o'shanda ko'rinmas bo'lib qolardi —
    hech qayerda «bu kadr ko'rilmagan» degan belgi yo'q edi.
    """
    market_id = two_markets.market_a.id
    kadr = zonali_kadr

    async with tenant_session(market_id) as session:
        birinchi = await seed_snapshot(session, market_id=market_id, snapshot_id=kadr)
    assert birinchi.seeded >= 1

    # Navbat yo'qoldi (hodisa esa o'zgarmas — uni o'chirib bo'lmaydi).
    with sync_owner_conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM review_assignments
             WHERE occupancy_event_id IN (
                 SELECT id FROM occupancy_events
                  WHERE market_id = %s AND model_version = %s)
            """,
            (market_id, SEED_MODEL_VERSION),
        )
    sync_owner_conn.commit()

    async with tenant_session(market_id) as session:
        tiklash = await seed_snapshot(session, market_id=market_id, snapshot_id=kadr)

    assert tiklash.events_created == 0, "hodisa qayta yozildi"
    assert tiklash.seeded == birinchi.seeded, (
        "navbat tiklanmadi — kadr nazoratchiga hech qachon ko'rinmasdi"
    )


# =============================================================================
# EKRANDAGI SON — TUGMA ORTIDAGI SAHIFA BILAN BITTA HAQIQAT (261003).
#
# `available_count()` nazoratchining uyidagi «Navbatda N ta» sonini beradi va
# N == 0 bo'lsa tugma O'LADI. Demak sanoq bilan `claim_next()` ning ROZILIGI —
# UI da'vosining o'zi, bezak emas: sanoq 0 ko'rsatib claim band bersa, haqiqiy
# ish ko'rinmay qolardi; sanoq musbat bo'lib claim bo'sh qaytarsa, nazoratchi
# bosib bo'sh ekranga tushardi. Ikkinchisi JONLI SERVERDA aynan shunday edi.
# =============================================================================


async def test_sanoq_CLAIM_bilan_rozi(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    zonali_kadr: UUID,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """Sanoq bazadagi haqiqat bilan teng, va claim u bilan kelishadi."""
    market_id = two_markets.market_a.id

    async with tenant_session(market_id) as session:
        natija = await seed_snapshot(session, market_id=market_id, snapshot_id=zonali_kadr)
    assert natija.seeded >= 1, "urug' navbatni to'ldirmadi — testning sharti yo'q"

    # --- Oracle: sanoqni TAKRORLAMAYDI, bazadan XOM holda oladi -------------
    #     Repo'ning SQL'ini test ichida qayta yozsak, ikkisi birga xato
    #     bo'lardi va test buni ko'rmasdi.
    xom = _scalar(
        sync_owner_conn,
        """
        SELECT count(*) FROM review_assignments ra
         WHERE ra.market_id = %s AND ra.queue_kind = 'uncertain'
           AND NOT EXISTS (
               SELECT 1 FROM zone_reviews zr
                WHERE zr.review_assignment_id = ra.id
           )
        """,
        (market_id,),
    )
    assert isinstance(xom, int) and xom >= 1

    async with tenant_session(market_id) as session:
        repo = ReviewRepository(session, market_id)
        noaniq = await repo.available_count(queue_kind=ReviewQueueKind.UNCERTAIN.value)
        kor = await repo.available_count(queue_kind=ReviewQueueKind.BLIND_AUDIT.value)
        band = await repo.claim_next(queue_kind=ReviewQueueKind.UNCERTAIN.value)
        kor_band = await repo.claim_next_blind()

    # ⛔ 1. Sanoq JOIN'larda ish yo'qotmaydi. Zonasi yoki rastasi yo'q band
    #       claim'ga tushmaydi, ya'ni sanoqqa ham kirmasligi kerak — lekin
    #       bu urug'da hammasi zonali, demak ikki son TENG bo'lishi shart.
    #       Teng bo'lmasa JOIN zanjiri sanoqdan ko'proq/kamroq kesyapti.
    assert noaniq == xom, f"sanoq {noaniq}, bazada {xom} ta javobsiz band"

    # ⛔ 2. ASOSIY DA'VO: son musbat -> claim BAND BERADI.
    assert noaniq > 0
    assert band is not None, "sanoq musbat, claim esa bo'sh — tugma bo'sh ekranga olib borardi"

    # ⛔ 3. TESKARI TOMON, va aynan shu jonli serverda buzilgan edi: ko'r
    #       audit navbati BO'SH (namuna `audit_draw` siz tortilmaydi).
    #       Sanoq 0 bermasa, tugma faol turardi va bosilardi.
    assert kor == 0, f"ko'r audit navbati bo'sh, sanoq esa {kor} berdi"
    assert kor_band is None, "sanoq 0, claim esa band berdi — son yolg'on"
