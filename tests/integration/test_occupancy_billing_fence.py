"""BILLING CHEGARASI — yaroqsiz kadr bandlik dalilini YARATA OLMAYDI (D-21).

=============================================================================
BU FAYLDA MOCK YO'Q VA BO'LISHI HAM MUMKIN EMAS.

Tekshirilayotgan kafolat ILOVA QATLAMIDA umuman yashamaydi: u
`snapshots (id, is_billable)` langari, kompozit chet el kaliti va
`CHECK (snapshot_is_billable)` uchligining natijasi. Mock'langan
repozitoriy yoki soxta sessiya bu uchlikning MAVJUDLIGINI ham,
ISHLASHINI ham o'lchay olmaydi — u faqat testning o'z tasavvurini
tekshirardi.

Shuning uchun har bir da'vo HAQIQIY `postgres:18.4` da, HAQIQIY
`INSERT` bilan o'lchanadi va kutilgan natija — SQLSTATE.
=============================================================================

UCH DA'VO VA UCHALASI HAM ALOHIDA BUZILISHI MUMKIN:

  1. `quality_verdict <> 'ok'` KADRGA hodisa yozib bo'lmaydi ->
     `ForeignKeyViolation` (`23503`). `(id, true)` juftligi jadvalda
     UMUMAN MAVJUD EMAS.
  2. `snapshot_is_billable = false` bilan yozib bo'lmaydi ->
     `CheckViolation` (`23514`). Bu juftlikning IKKINCHI YARMI: FK
     yolg'iz o'zi `(id, false)` juftligiga havolani QABUL QILARDI, chunki
     u ham HAQIQIY juftlik.
  3. Kafolat TRANZITIV: `stall_slot_occupancy` mavjud bo'lmagan hodisaga
     ishora qila olmaydi va `occupied` hukmi g'olib hodisasiz yozilmaydi.
     Ya'ni zanjir `stall_slot_occupancy -> occupancy_events -> snapshots`
     bo'ylab uzilmaydi va oxirgi halqa AYNAN billing langari.

TO'RTINCHI — NAZORAT HOLATI: YAROQLI kadrga hodisa BEMALOL yoziladi.
Usiz uchala inkor da'vosi ham «hech nima yozib bo'lmaydi» holatida
YASHIL qolardi va biz butunlay boshqa nosozlikni «kafolat ishlayapti»
deb o'qigan bo'lardik.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import psycopg
import pytest
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import MODEL_VERSION, OccupancyDomainSeed, occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from psycopg import Connection
from psycopg.rows import TupleRow

_INSERT_EVENT = """
INSERT INTO occupancy_events
    (market_id, snapshot_id, snapshot_is_billable, camera_zone_id,
     business_date, slot_time, verdict, confidence, model_version,
     thresholds_version, zone_version)
VALUES (%s, %s, %s, %s, %s, %s, 'occupied', 0.9000, %s, 1, %s)
"""

_INSERT_SLOT = """
INSERT INTO stall_slot_occupancy
    (market_id, stall_id, business_date, slot_time, verdict,
     resolution_source, winning_occupancy_event_id)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""


def _zone_context(
    conn: Connection[TupleRow], occupancy: OccupancyDomainSeed
) -> tuple[UUID, object, object, int]:
    """Seed hodisasidan zona, biznes-kun, slot va zona versiyasini oladi.

    Qiymatlar BAZADAN o'qiladi, testda qayta qurilmaydi: `business_date`
    va `slot_time` `snapshots` ning NUSXASI va ularni test o'zi hisoblasa
    IKKINCHI hisoblash manbai paydo bo'lardi — ya'ni test aynan o'zi
    qo'riqlayotgan invariantni buzardi (`snapshot_domain.py::
    scheduled_at_for` da o'rnatilgan qoida).
    """
    row = conn.execute(
        "SELECT camera_zone_id, business_date, slot_time, zone_version "
        "FROM occupancy_events WHERE id = %s",
        (str(occupancy.market_a.occupied_event_id),),
    ).fetchone()
    assert row is not None, "seed hodisasi topilmadi"
    return row[0], row[1], row[2], int(row[3])


def test_invalid_frame_cannot_carry_occupancy_evidence(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """`quality_verdict <> 'ok'` kadrga hodisa -> `ForeignKeyViolation` (D-21).

    =========================================================================
    LANGAR 4-FAZADA QO'YILGAN VA 5-FAZA UNI FAQAT ISHLATADI.

    `snapshots.is_billable` — `GENERATED ALWAYS AS (quality_verdict = 'ok')
    STORED`. `'dark'` kadr uchun bu ustun `false`, ya'ni FK talab qiladigan
    `(id, true)` juftligi JADVALDA UMUMAN MAVJUD EMAS va havola qurib
    bo'lmaydi.

    Bu ILOVA QATLAMIDAGI FILTRNI ORTIQCHA QILMAYDI (§E.13: yaroqsiz kadr
    uchun `detect` umuman ishga tushmaydi — «oldindan filtrlash mumkin
    bo'lgan xatoni imkonsiz xatoga aylantirishdan yaxshiroq»). Farq shu:
    filtr KODDA yashaydi va uni xom `INSERT`, migratsiya yoki kelajakdagi
    ikkinchi yozuvchi chetlab o'tadi; kafolat esa SXEMADA va u hamma
    yo'ldan o'tadi.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        a = occupancy.market_a
        assert a.snapshot_with_dark_quality is not None, (
            "seed'da yaroqsiz kadr yo'q — bu test hech nimani o'lchamaydi"
        )
        zone_id, business_date, slot_time, zone_version = _zone_context(sync_owner_conn, occupancy)

        with pytest.raises(psycopg.errors.ForeignKeyViolation) as error:
            sync_owner_conn.execute(
                _INSERT_EVENT,
                (
                    str(a.market_id),
                    str(a.snapshot_with_dark_quality),
                    True,
                    str(zone_id),
                    business_date,
                    slot_time,
                    f"{MODEL_VERSION}-fence",
                    zone_version,
                ),
            )
        assert error.value.sqlstate == "23503", (
            f"kutilgan `23503` (foreign_key_violation), olindi {error.value.sqlstate}"
        )
        assert "billable" in str(error.value), (
            f"xato boshqa chet el kalitidan keldi: {error.value!r} — billing "
            "langari emas, boshqa konstrayt ishlagan bo'lishi mumkin"
        )


def test_billable_flag_cannot_be_written_false(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """`snapshot_is_billable = false` -> `CheckViolation` (juftlikning IKKINCHI YARMI).

    =========================================================================
    ⚠ USIZ BUTUN KONSTRUKSIYA MA'NOSIZ BO'LARDI VA BU O'LCHANGAN
    (`tests/fixtures/billable_probe.py:87-104`).

    `snapshots` da HAR IKKALA juftlik ham mavjud: `(id, true)` yaroqli
    kadrlar uchun, `(id, false)` yaroqsizlar uchun. Ya'ni kompozit FK
    yolg'iz o'zi `snapshot_is_billable = false` bilan yozilgan qatorni
    BEMALOL qabul qilardi — u ham HAQIQIY juftlikka ishora qiladi va
    yaroqsiz kadr bandlik dalilini KO'TARIB KETARDI.

    `CHECK` `false` ni butunlay taqiqlaydi, ya'ni yagona mumkin bo'lgan
    havola — `is_billable = true` bo'lgan kadrga.

    ⚠ URINISH AYNAN YAROQSIZ KADRGA qilinadi: shunda FK ham, `CHECK` ham
    qarshi turadi va biz `CHECK` ning HAQIQATAN ishlashini ko'ramiz
    (`23514`, `23503` emas). Yaroqli kadrga `false` yozish ham `CHECK` ni
    otardi, lekin u holda «FK o'tkazib yubordi, `CHECK` ushladi» degan
    ketma-ketlik ko'rinmasdi.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        a = occupancy.market_a
        assert a.snapshot_with_dark_quality is not None
        zone_id, business_date, slot_time, zone_version = _zone_context(sync_owner_conn, occupancy)

        with pytest.raises(psycopg.errors.CheckViolation) as error:
            sync_owner_conn.execute(
                _INSERT_EVENT,
                (
                    str(a.market_id),
                    str(a.snapshot_with_dark_quality),
                    False,
                    str(zone_id),
                    business_date,
                    slot_time,
                    f"{MODEL_VERSION}-fence-false",
                    zone_version,
                ),
            )
        assert error.value.sqlstate == "23514", (
            f"kutilgan `23514` (check_violation), olindi {error.value.sqlstate}"
        )


def test_valid_frame_carries_evidence(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """NAZORAT HOLATI: YAROQLI kadrga hodisa BEMALOL yoziladi.

    Usiz yuqoridagi ikkala inkor da'vosi ham «bu jadvalga umuman hech nima
    yozib bo'lmaydi» holatida YASHIL qolardi — masalan `CHECK` xato yozilib
    HAR QANDAY qatorni rad etganda. O'shanda 05-08 birorta hodisa yoza
    olmasdi va nosozlik faqat kunlik hisobot bo'sh chiqqanda ko'rinardi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        a = occupancy.market_a
        zone_id, business_date, slot_time, zone_version = _zone_context(sync_owner_conn, occupancy)

        sync_owner_conn.execute(
            _INSERT_EVENT,
            (
                str(a.market_id),
                str(a.snapshot_with_ok_quality),
                True,
                str(zone_id),
                business_date,
                slot_time,
                f"{MODEL_VERSION}-control",
                zone_version,
            ),
        )

        row = sync_owner_conn.execute(
            "SELECT count(*) FROM occupancy_events WHERE market_id = %s AND model_version = %s",
            (str(a.market_id), f"{MODEL_VERSION}-control"),
        ).fetchone()
        assert row is not None and int(row[0]) == 1, (
            "yaroqli kadrga hodisa yozilmadi — kafolat emas, butun jadval ishlamayapti"
        )


def test_stall_slot_occupancy_cannot_point_at_a_missing_event(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """TRANZITIV KAFOLAT: rasta agregati mavjud bo'lmagan hodisaga ishora qila olmaydi.

    =========================================================================
    ZANJIR UCH HALQALI VA U UZILMASLIGI SHART:

        stall_slot_occupancy -> occupancy_events -> snapshots (id, is_billable)

    `stall_slot_occupancy` YANGI MEXANIZM O'YLAB TOPMAYDI — u zanjirni
    `winning_occupancy_event_id` orqali DAVOM ETTIRADI. Ikkinchi (mustaqil)
    tekshiruv yozib qo'yish kafolatni ikkiga bo'lardi va ular ajralib
    ketishi mumkin bo'lardi.

    IKKINCHI DA'VO — `CHECK ((verdict = 'occupied') =
    (winning_occupancy_event_id IS NOT NULL))`: «band» hukmi HAR DOIM aniq
    bir hodisaga, ya'ni aniq bir YAROQLI kadrga ishora qiladi. Usiz hisobga
    DALILSIZ «band» qatori tushardi va 6-faza unga patta yozardi.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        a = occupancy.market_a
        _, business_date, slot_time, _ = _zone_context(sync_owner_conn, occupancy)
        stall_id = market_domain.market_a.stall_ids[2]

        # (1) MAVJUD BO'LMAGAN hodisaga havola -> FK rad etadi.
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            sync_owner_conn.execute(
                _INSERT_SLOT,
                (
                    str(a.market_id),
                    str(stall_id),
                    business_date,
                    slot_time,
                    "occupied",
                    "ai",
                    str(uuid4()),
                ),
            )

        # (2) `occupied`, LEKIN g'olib hodisasiz -> `CHECK` rad etadi.
        with pytest.raises(psycopg.errors.CheckViolation) as error:
            sync_owner_conn.execute(
                _INSERT_SLOT,
                (
                    str(a.market_id),
                    str(stall_id),
                    business_date,
                    slot_time,
                    "occupied",
                    "ai",
                    None,
                ),
            )
        assert error.value.sqlstate == "23514"

        # (3) NAZORAT: g'olib hodisa bilan AYNAN o'sha qator O'TADI.
        sync_owner_conn.execute(
            _INSERT_SLOT,
            (
                str(a.market_id),
                str(stall_id),
                business_date,
                slot_time,
                "occupied",
                "ai",
                str(a.occupied_event_id),
            ),
        )
        row = sync_owner_conn.execute(
            "SELECT count(*) FROM stall_slot_occupancy WHERE stall_id = %s",
            (str(stall_id),),
        ).fetchone()
        assert row is not None and int(row[0]) == 1, (
            "g'olib hodisali qator ham yozilmadi — `CHECK` ifodasi teskari yozilgan bo'lishi mumkin"
        )
