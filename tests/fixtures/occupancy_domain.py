"""Ikki bozorli bandlik seed'i — `snapshot_domain` VA `market_domain` ustiga.

`fixtures/two_markets.py` bozor + foydalanuvchi qatlamini,
`fixtures/market_domain.py` rastalarni, `fixtures/nvr_domain.py` kameralarni,
`fixtures/snapshot_domain.py` esa kadrlarni beradi. Bu modul ularning ustiga
5-fazaning bandlik qatlamini qo'yadi: kamera zonalari (versiyalangan), AI
hodisalari, ko'r audit doirasi, navbat yozuvlari, nazoratchi javobi va rasta
darajasidagi agregat. Ikki bozor qoidasi shu yerda ham amal qiladi va sabab
bir xil: «0 qator qaytdi» javobi izolyatsiya ishlaganini ham, jadval
bo'shligini ham bildirishi mumkin.

=============================================================================
NOMLASH — FIZIK/GEOMETRIK FAKT, VERDIKT AKS-SADOSI EMAS (§S-9).

`fixtures/frames.py:3-29` da o'rnatilgan majburiyat bu yerda KUCHLIROQ
shaklda qaytadi, chunki bu fazada o'lchanadigan narsaning O'ZI verdikt:

    snapshot_with_ok_quality / snapshot_with_dark_quality      ✅
    zone_on_first_stall / superseded_zone                      ✅

    snapshot_that_passes_the_fence                             ❌
    zone_that_makes_the_stall_occupied                         ❌

Ikkinchi ustundagi nomlar fixture'ni TEKSHIRILAYOTGAN QOIDANING AKS-SADOSIGA
aylantiradi: «to'siqdan o'tadigan kadr» ni yasash uchun to'siqning
SHARTINI bilish kerak, ya'ni test shartni shartning O'ZI bilan tekshirardi
va shart noto'g'ri bo'lsa ham YASHIL qolardi.

Shu sababdan bu modul `sbozor_core.models.occupancy` dagi KONSTRAYT
ifodalarini (`BLIND_AUDIT_NOT_SHOWN_CHECK` va h.k.) UMUMAN import qilmaydi —
u faqat enum QIYMATLARINI oladi, chunki ular DB kontenti (`SnapshotQuality`
`snapshot_domain.py` da qanday ishlatilsa, shunday).
=============================================================================

SEED KONTRAKTI — HAR BIR ELEMENT ANIQ BIR TESTNI OZIQLANTIRADI.

  * **A bozorida UCHTA zona: bittasi ESKIRGAN.** `is_active = false`
    bo'lgan `version = 1` va uning o'rniga kelgan `version = 2` (D-07).
    Faqat faol zonalar bo'lsa `ix_camera_zones_active` qisman indeksining
    predikati hech nimani ajratmasdi va «tahrir yangi qator» da'vosi
    seed'da umuman ifodalanmasdi.

  * **A bozorida IKKITA hodisa va ular BOSHQA-BOSHQA verdiktda**
    (`occupied` va `uncertain`). Ikkalasi ham AYNAN BITTA kadrga
    (`snapshot_with_ok_quality`) osilgan, ya'ni
    `UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)` ning
    «zona bo'yicha ajraladi» xususiyati seed'ning o'zida sinaladi.

  * **Ko'r audit yozuvi JAVOBLI, noaniq navbat yozuvi JAVOBSIZ.** Ikkinchisi
    AI-06 ning («kun oxirigacha tasdiqlanmagan `uncertain`») kirish holati
    va u 05-12 uchun tayyor turadi. Javobsiz yozuvni seed'ga qo'shmaslik
    o'sha holatni har bir testda qayta yasashga majburlardi.

  * **`purpose` ikki xil:** ko'r auditda `eval`, noaniqda `train` (D-14).
    Ikkalasi bir xil bo'lsa `eval_needs_blind_audit` konstraytining
    manfiy tomoni seed'da umuman uchramasdi.

  * **A bozorining `stall_slot_occupancy` sida IKKI XIL manba:**
    `human` (g'olib hodisa BOR) va `default_empty` (g'olib hodisa YO'Q).
    `occupied_has_winning_event` konstraytining IKKALA yo'nalishi ham
    seed'da mavjud bo'ladi.

  * **A bozorining BIRINCHI rastasi IKKI KAMERADA.** `stall_ids[0]`
    uchun ikkinchi faol kamerada ham faol zona bor (D-20: «birortasi
    band desa — rasta band»). Usiz `uq_camera_zones_...` ning «kamera
    bo'yicha ajraladi» xususiyati seed'da umuman ifodalanmasdi va
    05-06 dagi «bir rastaga ikkinchi zona» taqiqi (u FAQAT bir kamera
    ichida amal qiladi) noto'g'ri kengaytirilishi mumkin edi.

  * **Ikkinchi kameradagi zona `640x480` kadrda chizilgan** (4:3),
    birinchisi esa `1920x1080` da (16:9). Nisbat farqi darvozasining
    (§6.8) kirish holati seed'da MAVJUD, ya'ni uni har testda qayta
    yasash shart emas.

  * **A bozorida ZONASI YO'Q faol rasta bor** (`stall_ids[2]`). D-22
    ning kirish holati: qamrovsiz rasta qonuniy va u `no_coverage`.
    Usiz `coverage().uncovered` hech qachon noldan farq qilmasdi.

  * **`market_delete_draft()` KASKADI UCHUN: B bozorida ham OLTALA
    jadvalda qator bor.** Cross-tenant nazorati («A o'chdi, B joyida»)
    B da qator BO'LMASA hech nimani o'lchamaydi.
=============================================================================

⚠ `business_date` va `slot_time` `snapshot_domain` DAN OLINADI, bu yerda
QAYTA HISOBLANMAYDI. `occupancy_events` da bu ustunlar `snapshots` ning
NUSXASI (`GENERATED` emas) va seed shu qoidaga bo'ysunishi shart — aks
holda «ikki mustaqil hisoblash manbai yo'q» invarianti seed'ning o'zida
buzilardi.

UUID'LAR DETERMINISTIK EMAS — HAR CHAQIRUVDA YANGI (`uuid4`).
`two_markets`/`nvr_domain`/`snapshot_domain` bilan aynan bir xil qaror.

Seed `sbozor_owner` autocommit ulanishi bilan yoziladi (yuqoridagi
qatlamlar bilan bir xil sabab): ma'lumot boshqa ulanishdagi `sbozor_app`
testlariga DARHOL ko'rinishi kerak.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import time
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.enums import (
    OccupancyVerdict,
    ResolutionSource,
    ReviewPurpose,
    ReviewQueueKind,
)

from fixtures.market_domain import MarketDomainSeed
from fixtures.snapshot_domain import SEED_BUSINESS_DATE, SnapshotDomainSeed
from fixtures.two_markets import TwoMarketSeed

__all__ = [
    "AUDIT_FRAME_PREDICATE_HASH",
    "CLEANUP_ORDER",
    "MODEL_VERSION",
    "NARROW_SOURCE_HEIGHT",
    "NARROW_SOURCE_WIDTH",
    "SEED_THRESHOLDS_VERSION",
    "SOURCE_HEIGHT",
    "SOURCE_WIDTH",
    "MarketOccupancyRows",
    "OccupancyDomainSeed",
    "cleanup_occupancy_domain",
    "occupancy_rows",
    "seed_occupancy_domain",
    "square_polygon",
]

MODEL_VERSION = "rfdetr-large-seed"
"""Seed hodisalarining `model_version` i — HAQIQIY model nomi EMAS, ATAYIN.

Real nom (`rfdetr-large-1.9.1`) yozilsa testlar model VERSIYASIGA bog'lanib
qolardi va detektor yangilangan kuni ular MAZMUNSIZ ravishda qizarardi.
Ustunning seed uchun ahamiyati bitta: u
`UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)` kalitining
bir qismi, ya'ni QIYMATI emas, MAVJUDLIGI muhim.
"""

SEED_THRESHOLDS_VERSION = 1
"""Chegara to'plamining versiyasi (D-11). `snapshot_domain` niki bilan bir xil son."""

AUDIT_FRAME_PREDICATE_HASH = "seed-frame-predicate"
"""Doira nomzodlarini tanlagan shartning xeshi o'rniga QADALGAN belgi.

Haqiqiy xesh 05-11 da hisoblanadi. Seed uchun muhimi ustunning `NOT NULL`
va bo'sh bo'lmasligi (`frame_predicate_hash_not_blank`), qiymatning O'ZI
emas — seed xesh ALGORITMINI bilishi kerak emas va bilmasligi ham kerak
(§S-9: fixture tekshirilayotgan mexanizmni takrorlamaydi).
"""

_UNIT = 0.1
"""Kvadrat poligonning yarim tomoni (normalangan koordinatada)."""


def square_polygon(cx: float, cy: float) -> list[list[float]]:
    """`(cx, cy)` markazli kvadrat — TO'RT uchli, 0..1 oralig'ida.

    GEOMETRIK FAKT bo'yicha nomlangan (§S-9): funksiya na `PolygonZone` ni,
    na `validate_polygon()` ni biladi va ularning chegaralarini import
    QILMAYDI. U faqat «markazi shu yerda bo'lgan kvadrat» ni qaytaradi.

    To'rt uch ATAYIN: u `polygon_min_vertices` (3) va `polygon_max_vertices`
    (12) chegaralarining ORASIDA turadi, ya'ni seed hech qaysi chegarani
    o'z chegarasi bilan tekshirmaydi.
    """
    return [
        [round(cx - _UNIT, 4), round(cy - _UNIT, 4)],
        [round(cx + _UNIT, 4), round(cy - _UNIT, 4)],
        [round(cx + _UNIT, 4), round(cy + _UNIT, 4)],
        [round(cx - _UNIT, 4), round(cy + _UNIT, 4)],
    ]


SOURCE_WIDTH = 1920
SOURCE_HEIGHT = 1080
"""Poligon chizilgan kadr o'lchami — `cameras.capture_stream = 'main'` odatiysi."""

NARROW_SOURCE_WIDTH = 640
NARROW_SOURCE_HEIGHT = 480
"""IKKINCHI kameradagi zonaning kadr o'lchami — 4:3, yuqoridagisi 16:9.

⚠ FIZIK FAKT BO'YICHA NOMLANGAN (§S-9): `640x480` — kadr o'lchami, va
  bu modul undan chiqadigan VERDIKTNI (`needs_review`, `zone_aspect_
  mismatch`) bilmaydi. `mismatched_zone_id` deb nomlash fixture'ni
  `aspect_ratio_matches()` ning aks-sadosiga aylantirardi: «mos
  kelmaydigan» kadrni yasash uchun tolerans QIYMATINI bilish kerak
  bo'lardi va tolerans noto'g'ri qo'yilganda ham test YASHIL qolardi.

  4:3 va 16:9 nisbati o'rtasidagi farq 0,44 — har qanday oqilona
  toleransdan ancha katta, ya'ni seed hech qanday chegarani o'z
  chegarasi bilan tekshirmaydi.
"""

CLEANUP_ORDER: tuple[str, ...] = (
    "stall_slot_occupancy",
    "zone_reviews",
    "review_assignments",
    "audit_rounds",
    "occupancy_events",
    "camera_zones",
)
"""O'CHIRISH TARTIBI — `migrations.entities.OCCUPANCY_DELETE_ORDER` bilan BIR XIL.

Tasodif emas: ikkalasi ham bir xil FK zanjiridan kelib chiqadi.

⚠ REYESTRDAN IMPORT QILINMAYDI va bu ATAYIN (`snapshot_domain.py` dagi
jufti bilan bir xil qaror): `tests/fixtures/` `migrations` paketiga
bog'lanmaydi, va — muhimrog'i — reyestrdan olingan ro'yxat reyestrning
O'ZI xato bo'lganda test bilan BIRGA xato bo'lardi. Ikkala ro'yxatning
MOSLIGI kaskad testining O'ZIDA o'lchanadi: noto'g'ri tartib `DELETE` ni
FK buzilishi bilan yiqitadi.
"""

_INSERT_ZONE = (
    "INSERT INTO camera_zones "
    "(id, market_id, camera_id, stall_id, version, polygon, "
    " source_width, source_height, is_active) "
    "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)"
)
_INSERT_EVENT = (
    "INSERT INTO occupancy_events "
    "(id, market_id, snapshot_id, camera_zone_id, business_date, slot_time, "
    " verdict, confidence, model_version, thresholds_version, zone_version) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_ROUND = (
    "INSERT INTO audit_rounds "
    "(id, market_id, business_date, round_no, frame_size, frame_predicate_hash) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)
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
_INSERT_SLOT = (
    "INSERT INTO stall_slot_occupancy "
    "(id, market_id, stall_id, business_date, slot_time, verdict, "
    " resolution_source, winning_occupancy_event_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
)


@dataclass(frozen=True)
class MarketOccupancyRows:
    """Bitta bozorning bandlik qatorlari."""

    market_id: UUID
    superseded_zone_id: UUID | None
    """`is_active = false` bo'lgan ESKI versiya (D-07). B bozorida `None`."""
    second_camera_id: UUID | None
    """A bozorining IKKINCHI faol kamerasi (arxivlanmagan). B da `None`."""
    second_camera_zone_id: UUID | None
    """BIRINCHI rastaning IKKINCHI kameradagi zonasi. B bozorida `None`.

    ⛔ BIR RASTA IKKI KAMERADA — BU NORMAL HOLAT, XATO EMAS, va u D-20
       ning butun asosi («birortasi band desa — rasta band»). Seed'da
       bo'lmasa `uq_camera_zones_market_id_camera_id_stall_id_version`
       ning «kamera bo'yicha ajraladi» xususiyati umuman ifodalanmasdi
       va «bir rastaga ikkinchi zona» taqiqi (u faqat BIR KAMERA ichida
       amal qiladi) noto'g'ri kengaytirilib qo'yilishi mumkin edi.

    Zona `640x480` kadrda chizilgan, birinchisi esa `1920x1080` da —
    ya'ni bitta rasta ikki xil nisbatdagi ikki kadrda ko'rinadi.
    """
    stall_without_zone_id: UUID | None
    """Birorta `camera_zones` qatori BO'LMAGAN faol rasta. B da `None`.

    Bu D-22 ning kirish holati: qamrovsiz rasta MUTLAQO QONUNIY va u
    `no_coverage` bo'ladi — «bo'sh» EMAS. Seed'da bunday rasta bo'lmasa
    `coverage()` ning `uncovered` shoxi HECH QACHON noldan farq
    qilmasdi va u nol qaytargan holatda ham yashil bo'lardi.
    """
    active_zone_ids: tuple[UUID, ...]
    occupied_event_id: UUID
    """`verdict` i `occupied` bo'lgan hodisa — g'olib hodisa sifatida ishlatiladi."""
    uncertain_event_id: UUID | None
    """`verdict` i `uncertain` bo'lgan hodisa. B bozorida `None`."""
    event_ids: tuple[UUID, ...]
    audit_round_id: UUID
    blind_assignment_id: UUID
    """`queue_kind = 'blind_audit'`, `purpose = 'eval'` (A) / `'train'` (B)."""
    uncertain_assignment_id: UUID | None
    """JAVOBSIZ qolgan noaniq navbat yozuvi (AI-06 kirishi). B da `None`."""
    blind_review_id: UUID
    slot_ids: tuple[UUID, ...]
    snapshot_with_ok_quality: UUID
    """`quality_verdict = 'ok'` kadr — bandlik dalili AYNAN shunga osiladi."""
    snapshot_with_dark_quality: UUID | None
    """`quality_verdict = 'dark'` kadr. A bozorida bor, B da YO'Q.

    Billing to'sig'i testi undan foydalanadi: yaroqsiz kadrga hodisa
    yozishga urinish `ForeignKeyViolation` berishi kerak. Seed uni O'ZI
    ISHLATMAYDI — bu ataylab, aks holda seed o'zi rad etilardi.
    """


@dataclass(frozen=True)
class OccupancyDomainSeed:
    """Ikki bozorning bandlik qatlami."""

    market_a: MarketOccupancyRows
    market_b: MarketOccupancyRows

    @property
    def markets(self) -> tuple[MarketOccupancyRows, MarketOccupancyRows]:
        return (self.market_a, self.market_b)

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return (self.market_a.market_id, self.market_b.market_id)


def _snapshot_slot_time(conn: Connection[TupleRow], snapshot_id: UUID) -> time:
    """Kadrning `slot_time` i — BAZADAN o'qiladi, qayta hisoblanmaydi.

    `occupancy_events.slot_time` `snapshots` ning NUSXASI (modul
    docstringidagi ⚠). Seed uni o'zi qursa ikkinchi hisoblash manbai paydo
    bo'lardi — ya'ni seed aynan o'zi qo'riqlayotgan invariantni buzardi.
    """
    row = conn.execute(
        "SELECT slot_time FROM snapshots WHERE id = %s", (str(snapshot_id),)
    ).fetchone()
    assert row is not None, f"kadr {snapshot_id} topilmadi — snapshot seed'i ishlamagan"
    slot_time: time = row[0]
    return slot_time


def _seed_market_occupancy(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    camera_id: UUID,
    second_camera_id: UUID | None,
    stall_ids: tuple[UUID, ...],
    snapshot_ok: UUID,
    snapshot_dark: UUID | None,
    reviewer_id: UUID,
    with_uncertain: bool,
) -> MarketOccupancyRows:
    """Bitta bozorning bandlik qatlamini yozadi.

    `with_uncertain` — A bozori uchun `True`: u eskirgan zona, ikkinchi
    faol zona, `uncertain` hodisa va JAVOBSIZ navbat yozuvini qo'shadi.
    B bozorida `False`, chunki uning yagona vazifasi cross-tenant nazorati
    va unga to'liq holat qamrovi kerak emas (sonlar ATAYIN farqli —
    `snapshot_domain.py::B_RUN_PLAN` bilan bir xil qoida).
    """
    slot_time = _snapshot_slot_time(conn, snapshot_ok)

    superseded_zone_id: UUID | None = None
    if with_uncertain:
        # D-07: ESKIRGAN kontur. `version = 1`, `is_active = false` va u
        # JOYIDA QOLADI — o'tmishdagi dalil unga tayanadi.
        superseded_zone_id = uuid4()
        conn.execute(
            _INSERT_ZONE,
            (
                str(superseded_zone_id),
                str(market_id),
                str(camera_id),
                str(stall_ids[0]),
                1,
                _as_json(square_polygon(0.30, 0.30)),
                SOURCE_WIDTH,
                SOURCE_HEIGHT,
                False,
            ),
        )

    # Birinchi rastaning AMALDAGI konturi. A bozorida u `version = 2`
    # (yuqoridagi eskirganning o'rniga kelgan), B da `version = 1`.
    primary_zone_id = uuid4()
    primary_version = 2 if with_uncertain else 1
    conn.execute(
        _INSERT_ZONE,
        (
            str(primary_zone_id),
            str(market_id),
            str(camera_id),
            str(stall_ids[0]),
            primary_version,
            _as_json(square_polygon(0.32, 0.31)),
            SOURCE_WIDTH,
            SOURCE_HEIGHT,
            True,
        ),
    )

    active_zone_ids = [primary_zone_id]
    secondary_zone_id: UUID | None = None
    if with_uncertain:
        secondary_zone_id = uuid4()
        conn.execute(
            _INSERT_ZONE,
            (
                str(secondary_zone_id),
                str(market_id),
                str(camera_id),
                str(stall_ids[1]),
                1,
                _as_json(square_polygon(0.70, 0.55)),
                SOURCE_WIDTH,
                SOURCE_HEIGHT,
                True,
            ),
        )
        active_zone_ids.append(secondary_zone_id)

    # BIRINCHI rastaning IKKINCHI kameradagi konturi — bir rasta ikki
    # kamerada (D-20). Kadr o'lchami 4:3, birinchisiniki 16:9.
    second_camera_zone_id: UUID | None = None
    if with_uncertain and second_camera_id is not None:
        second_camera_zone_id = uuid4()
        conn.execute(
            _INSERT_ZONE,
            (
                str(second_camera_zone_id),
                str(market_id),
                str(second_camera_id),
                str(stall_ids[0]),
                1,
                _as_json(square_polygon(0.55, 0.45)),
                NARROW_SOURCE_WIDTH,
                NARROW_SOURCE_HEIGHT,
                True,
            ),
        )
        active_zone_ids.append(second_camera_zone_id)

    occupied_event_id = uuid4()
    conn.execute(
        _INSERT_EVENT,
        (
            str(occupied_event_id),
            str(market_id),
            str(snapshot_ok),
            str(primary_zone_id),
            SEED_BUSINESS_DATE,
            slot_time,
            OccupancyVerdict.OCCUPIED.value,
            "0.9310",
            MODEL_VERSION,
            SEED_THRESHOLDS_VERSION,
            primary_version,
        ),
    )
    event_ids = [occupied_event_id]

    uncertain_event_id: UUID | None = None
    if with_uncertain and secondary_zone_id is not None:
        uncertain_event_id = uuid4()
        conn.execute(
            _INSERT_EVENT,
            (
                str(uncertain_event_id),
                str(market_id),
                str(snapshot_ok),
                str(secondary_zone_id),
                SEED_BUSINESS_DATE,
                slot_time,
                OccupancyVerdict.UNCERTAIN.value,
                "0.5540",
                MODEL_VERSION,
                SEED_THRESHOLDS_VERSION,
                1,
            ),
        )
        event_ids.append(uncertain_event_id)

    audit_round_id = uuid4()
    conn.execute(
        _INSERT_ROUND,
        (
            str(audit_round_id),
            str(market_id),
            SEED_BUSINESS_DATE,
            1,
            len(event_ids),
            AUDIT_FRAME_PREDICATE_HASH,
        ),
    )

    # KO'R AUDIT yozuvi — doiraga bog'langan (`blind_audit_needs_round`).
    # `purpose`: A da `eval` (xolis o'lchov), B da `train`. Ikkalasi ham
    # `eval_needs_blind_audit` ni qanoatlantiradi, lekin ikki xil qiymat
    # seed'da IKKALA yo'lni ham ifodalaydi.
    blind_assignment_id = uuid4()
    conn.execute(
        _INSERT_ASSIGNMENT,
        (
            str(blind_assignment_id),
            str(market_id),
            str(occupied_event_id),
            str(audit_round_id),
            ReviewQueueKind.BLIND_AUDIT.value,
            (ReviewPurpose.EVAL if with_uncertain else ReviewPurpose.TRAIN).value,
        ),
    )

    uncertain_assignment_id: UUID | None = None
    if uncertain_event_id is not None:
        # ⚠ JAVOBSIZ QOLADI — AI-06 ning kirish holati («kun oxirigacha
        #   tasdiqlanmagan `uncertain`»). `audit_round_id` `NULL`, ya'ni
        #   noaniq navbat doiraga tegishli emas.
        uncertain_assignment_id = uuid4()
        conn.execute(
            _INSERT_ASSIGNMENT,
            (
                str(uncertain_assignment_id),
                str(market_id),
                str(uncertain_event_id),
                None,
                ReviewQueueKind.UNCERTAIN.value,
                ReviewPurpose.TRAIN.value,
            ),
        )

    # ⚠ `shown_ai_verdict = false` — ko'r auditda BOSHQACHA bo'la olmaydi
    #   (`blind_audit_not_shown`). Seed uni LITERAL yozadi, konstraytdan
    #   HISOBLAMAYDI.
    blind_review_id = uuid4()
    conn.execute(
        _INSERT_REVIEW,
        (
            str(blind_review_id),
            str(market_id),
            str(blind_assignment_id),
            ReviewQueueKind.BLIND_AUDIT.value,
            False,
            OccupancyVerdict.OCCUPIED.value,
            str(reviewer_id),
            4200,
        ),
    )

    # Rasta darajasidagi agregat: birinchi rasta BAND (g'olib hodisa BOR,
    # manba `human` — nazoratchi tasdiqladi).
    slot_ids = [uuid4()]
    conn.execute(
        _INSERT_SLOT,
        (
            str(slot_ids[0]),
            str(market_id),
            str(stall_ids[0]),
            SEED_BUSINESS_DATE,
            slot_time,
            OccupancyVerdict.OCCUPIED.value,
            ResolutionSource.HUMAN.value,
            str(occupied_event_id),
        ),
    )
    if with_uncertain:
        # Ikkinchi rasta: tasdiqlanmagan `uncertain` -> `empty`, manba
        # `default_empty` (AI-06/D-19). G'olib hodisa YO'Q, ya'ni
        # `occupied_has_winning_event` ning IKKINCHI yo'nalishi ham
        # seed'da mavjud.
        slot_ids.append(uuid4())
        conn.execute(
            _INSERT_SLOT,
            (
                str(slot_ids[1]),
                str(market_id),
                str(stall_ids[1]),
                SEED_BUSINESS_DATE,
                slot_time,
                OccupancyVerdict.EMPTY.value,
                ResolutionSource.DEFAULT_EMPTY.value,
                None,
            ),
        )

    # ⚠ QAMROVSIZ RASTA HISOBLANMAYDI, TANLANADI: zonasi bor rastalar
    #   yuqorida NOMMA-NOM yozilgan (`stall_ids[0]` va `stall_ids[1]`),
    #   ya'ni uchinchisi ta'rifi bo'yicha qamrovsiz. Uni `coverage()` yoki
    #   `camera_zones` so'rovi bilan topish seed'ni AYNAN o'sha
    #   so'rovning aks-sadosiga aylantirardi.
    stall_without_zone_id = stall_ids[2] if with_uncertain and len(stall_ids) > 2 else None

    return MarketOccupancyRows(
        market_id=market_id,
        superseded_zone_id=superseded_zone_id,
        second_camera_id=second_camera_id if with_uncertain else None,
        second_camera_zone_id=second_camera_zone_id,
        stall_without_zone_id=stall_without_zone_id,
        active_zone_ids=tuple(active_zone_ids),
        occupied_event_id=occupied_event_id,
        uncertain_event_id=uncertain_event_id,
        event_ids=tuple(event_ids),
        audit_round_id=audit_round_id,
        blind_assignment_id=blind_assignment_id,
        uncertain_assignment_id=uncertain_assignment_id,
        blind_review_id=blind_review_id,
        slot_ids=tuple(slot_ids),
        snapshot_with_ok_quality=snapshot_ok,
        snapshot_with_dark_quality=snapshot_dark,
    )


def _as_json(points: list[list[float]]) -> str:
    """Poligonni `jsonb` parametri uchun matnga aylantiradi."""
    inner = ", ".join(f"[{x}, {y}]" for x, y in points)
    return f"[{inner}]"


def seed_occupancy_domain(
    conn: Connection[TupleRow],
    base: TwoMarketSeed,
    domain: MarketDomainSeed,
    snapshots: SnapshotDomainSeed,
) -> OccupancyDomainSeed:
    """`snapshot_domain` + `market_domain` ustiga bandlik qatlamini yozadi.

    `conn` `sbozor_owner` bilan ochilgan va AUTOCOMMIT rejimida bo'lishi
    kerak — yuqoridagi qatlamlar bilan aynan bir xil talab.

    ⚠ TO'RT QATLAM KERAK va ularning har biri BOSHQA narsani beradi:
    `base` — nazoratchi (`reviewer_id` uchun HAQIQIY foydalanuvchi, chunki
    `zone_reviews` `users` ga FK bilan tayanadi); `domain` — rastalar;
    `snapshots` — kadrlar va ular orqali kameralar.
    """
    # ⚠ KADRLARNI SIFATI BO'YICHA AJRATISH — `A_RUN_PLAN` NING TARTIBIGA
    #   TAYANMAYDI. Tartibga tayanish seed'ni qo'shni faylning ro'yxat
    #   tartibiga bog'lab qo'yardi va o'sha ro'yxat qayta tartiblangan kuni
    #   bu yerda «ok» o'rniga «dark» kadr ishlatilardi — billing to'sig'i
    #   esa uni RAD ETARDI va nosozlik butunlay boshqa joyda ko'rinardi.
    a_ok, a_dark = _split_by_quality(conn, snapshots.market_a.snapshot_ids)
    b_ok, b_dark = _split_by_quality(conn, snapshots.market_b.snapshot_ids)

    a_camera = _camera_of(conn, a_ok)
    market_a = _seed_market_occupancy(
        conn,
        market_id=snapshots.market_a.market_id,
        camera_id=a_camera,
        second_camera_id=_other_active_camera(conn, snapshots.market_a.market_id, a_camera),
        stall_ids=domain.market_a.stall_ids,
        snapshot_ok=a_ok,
        snapshot_dark=a_dark,
        reviewer_id=base.market_a.admin_user_id,
        with_uncertain=True,
    )
    market_b = _seed_market_occupancy(
        conn,
        market_id=snapshots.market_b.market_id,
        camera_id=_camera_of(conn, b_ok),
        second_camera_id=None,
        stall_ids=domain.market_b.stall_ids,
        snapshot_ok=b_ok,
        snapshot_dark=b_dark,
        reviewer_id=base.market_b.admin_user_id,
        with_uncertain=False,
    )
    return OccupancyDomainSeed(market_a=market_a, market_b=market_b)


def _split_by_quality(
    conn: Connection[TupleRow], snapshot_ids: tuple[UUID, ...]
) -> tuple[UUID, UUID | None]:
    """`(yaroqli kadr, yaroqsiz kadr)` — HUKM BAZADAN o'qiladi.

    ⚠ `is_billable` BO'YICHA emas, `quality_verdict` BO'YICHA ajratiladi va
    farq ma'noli: `is_billable` — TEKSHIRILAYOTGAN kafolatning o'zi
    (`GENERATED ALWAYS AS (quality_verdict = 'ok')`). Undan foydalanish
    seed'ni o'sha kafolatning aks-sadosiga aylantirardi.
    """
    ok_id: UUID | None = None
    bad_id: UUID | None = None
    for snapshot_id in snapshot_ids:
        row = conn.execute(
            "SELECT quality_verdict FROM snapshots WHERE id = %s", (str(snapshot_id),)
        ).fetchone()
        assert row is not None, f"kadr {snapshot_id} topilmadi"
        if row[0] == "ok":
            ok_id = ok_id or snapshot_id
        else:
            bad_id = bad_id or snapshot_id
    assert ok_id is not None, (
        "snapshot seed'ida `quality_verdict = 'ok'` kadr yo'q — bandlik "
        "dalili umuman yozib bo'lmasdi"
    )
    return ok_id, bad_id


def _camera_of(conn: Connection[TupleRow], snapshot_id: UUID) -> UUID:
    """Kadr QAYSI kameradan olingani — bazadan.

    `camera_zones` `cameras (market_id, id)` ga kompozit FK bilan tayanadi,
    ya'ni zona AYNAN o'sha kameraga bog'lanishi kerak; `nvr_domain` ning
    kamera ro'yxatidan indeks bo'yicha olish ikkinchi haqiqat manbai
    bo'lardi.
    """
    row = conn.execute(
        "SELECT camera_id FROM snapshots WHERE id = %s", (str(snapshot_id),)
    ).fetchone()
    assert row is not None, f"kadr {snapshot_id} topilmadi"
    camera_id: UUID = row[0]
    return camera_id


def _other_active_camera(conn: Connection[TupleRow], market_id: UUID, exclude: UUID) -> UUID | None:
    """Shu bozorning BOSHQA arxivlanmagan kamerasi — BAZADAN.

    ⚠ `nvr_domain` NING RO'YXAT TARTIBIGA TAYANMAYDI (`_camera_of()` va
      `_split_by_quality()` bilan aynan bir xil qoida). Indeks bo'yicha
      olish qo'shni faylning kanal ro'yxati qayta tartiblangan kuni
      ARXIVLANGAN kamerani tanlashi mumkin edi va o'shanda qamrov
      sanog'i (u arxivlanganlarni chiqarib tashlaydi) seed bilan mos
      kelmay, sabab butunlay boshqa faylda ko'rinardi.

    `channel_no` bo'yicha tartib — DETERMINIZM uchun: tartibsiz `LIMIT 1`
    har ishga tushirishda boshqa kamerani tanlab, seed'ni beqaror
    qilardi.
    """
    row = conn.execute(
        "SELECT id FROM cameras "
        "WHERE market_id = %s AND id <> %s AND is_archived = false "
        "ORDER BY channel_no LIMIT 1",
        (str(market_id), str(exclude)),
    ).fetchone()
    return None if row is None else UUID(str(row[0]))


def cleanup_occupancy_domain(conn: Connection[TupleRow], seed: OccupancyDomainSeed) -> None:
    """Bandlik qatlamini FK tartibida o'chiradi.

    =========================================================================
    ⚠ AVVAL BOZORLAR QORALAMAGA QAYTARILADI VA BUSIZ TOZALASH YIQILADI.

    `0018` `occupancy_events` va `zone_reviews` ga SHARTSIZ (vaqt shartisiz)
    o'zgarmaslik qo'riqchisini qo'yadi. `DELETE` uchun yagona istisno —
    QORALAMA bozor (`is_active = false`), ya'ni `market_delete_draft()` ning
    yo'li. Faol bozorda `DELETE FROM occupancy_events` `RAISE EXCEPTION`
    beradi va tozalash birinchi qadamda yiqilardi.

    Bu YANGI naqsh EMAS: `cleanup_market_domain()` aynan shu qadamni
    `tariffs`/`stall_category_periods` uchun 02-04 dan beri bajaradi va
    `cleanup_two_markets()` uni `markets` ning O'ZI uchun takrorlaydi.
    Bayroqni tushirish bu yerda semantik jihatdan HALOL: qator bir necha
    satr keyin butunlay o'chiriladi.

    ALTERNATIVALAR VA NEGA ULAR EMAS:
      * `ALTER TABLE ... DISABLE TRIGGER` — qo'riqchini butunlay o'chiradi,
        ya'ni u ROSTDAN buzilgan holatni ham yashirardi;
      * qo'riqchini `UPDATE` bilan cheklash — `0019` kaskadini imkonsiz
        qilardi (u ikkala jadvaldan ham `DELETE` qiladi).
    =========================================================================
    """
    market_ids = [str(market_id) for market_id in seed.market_ids]

    conn.execute(
        "UPDATE markets SET is_active = false WHERE id = ANY(%s::uuid[])",
        (market_ids,),
    )
    for table in CLEANUP_ORDER:
        # Jadval nomlari shu moduldagi SOBIT `CLEANUP_ORDER` dan keladi —
        # tashqi kirish emas, ya'ni f-string bu yerda xavfsiz
        # (`snapshot_domain.py` dagi jufti bilan bir xil naqsh).
        conn.execute(
            f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
            (market_ids,),
        )


@contextmanager
def occupancy_rows(
    conn: Connection[TupleRow],
    base: TwoMarketSeed,
    domain: MarketDomainSeed,
    snapshots: SnapshotDomainSeed,
) -> Iterator[OccupancyDomainSeed]:
    """`seed_occupancy_domain()` + kafolatlangan tozalash — `with` bloki uchun.

    ATAYIN pytest fixture EMAS, `contextmanager` (`snapshot_rows()` bilan
    bir xil naqsh va bir xil sabab): fixture `tests/conftest.py` da
    yashashi kerak bo'lardi, o'sha faylni esa boshqa rejalar ham
    tahrirlaydi.

    ⚠ TARTIB MUHIM: bu kontekst menejeri `snapshot_rows(...)` NING ICHIDA
    ishlatiladi. Teskari joylashuv `snapshot_domain` ning tozalashini
    `snapshots` ga hali `occupancy_events` tayanib turgan paytda ishga
    tushirardi va u FK buzilishi bilan yiqilardi.

    ⚠ TOZALASH BLOK O'CHIRILGAN BOZOR USTIDA HAM XAVFSIZ:
    `market_delete_draft()` ni sinaydigan test bozorni butunlay o'chiradi
    va o'shanda `DELETE ... WHERE market_id = ...` shunchaki 0 qatorga
    tegadi.
    """
    seed = seed_occupancy_domain(conn, base, domain, snapshots)
    try:
        yield seed
    finally:
        cleanup_occupancy_domain(conn, seed)
