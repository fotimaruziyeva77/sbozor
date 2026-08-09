"""Bandlik domeni: kamera zonalari, AI hodisalari, nazoratchi javobi, agregat.

=============================================================================
BU FAYLDA OLTITA QAROR YASHAYDI VA HAMMASI KODDA EMAS, SXEMADA.
Ular "qulaylik uchun" buzilishi oson, shuning uchun sabablari shu yerda.

1. NOM TO'QNASHUVI (D-06): jadval `camera_zones`, `zones` EMAS. `zones`
   2-fazada bozor HUDUDLARI uchun band (`models/market.py::Zone`) va unga
   `stalls.zone_id NOT NULL` tayanadi. `zones` deb nomlash migratsiyani
   "jadval allaqachon mavjud" bilan to'qnashtirardi — yoki, bundan ham
   yomoni, mavjud jadvalga ikkinchi policy qo'yardi.

2. AUDIT ASSIMETRIYASI: trigger FAQAT `camera_zones` va `zone_reviews` ga
   ulanadi. `occupancy_events` CHIQARILGAN — 175 kadr/kun/bozor x ~30 zona
   ~ 5 000 qator/kun/bozor, VA jadval 3-band bo'yicha SHARTSIZ o'zgarmas:
   o'zgarmas jadval uchun audit faqat `INSERT` ni ko'rardi, ya'ni u o'sha
   ma'lumotning IKKINCHI NUSXASI bo'lardi. `zone_reviews` esa AUDITDA —
   u INSONNING moliyaviy oqibatli qarori (`tariffs` bilan bir oilada).

3. O'ZGARMASLIK SHARTSIZ (D-12), `tariffs` ning SHARTLI shakli EMAS.
   `occupancy_events` va `zone_reviews` ustidagi qo'riqchilar har qanday
   `UPDATE`/`DELETE` ni rad etadi. Shartli shakl (`tariff_past_immutable()`)
   faqat O'TMISHDAGI qatorni qulflaydi va u D-12 ni jimgina bo'shatishning
   eng oson yo'li bo'lardi: "bugungi" javob tahrirlanadigan bo'lib qolardi,
   holbuki aynan bugungi javob o'lchov natijasini belgilaydi.

4. BILLING LANGARI (D-21) — UCH SATR 4-FAZADAN AYNAN KO'CHIRILADI:

       snapshot_is_billable boolean NOT NULL DEFAULT true
       CHECK  (snapshot_is_billable)
       FOREIGN KEY (snapshot_id, snapshot_is_billable)
           REFERENCES snapshots (id, is_billable)

   Langar `uq_snapshots_billable_anchor` 4-fazada qo'yilgan va HAQIQIY
   `postgres:18.4` da o'lchangan (`tests/fixtures/billable_probe.py`,
   `BILLABLE_ANCHOR_SUPPORTED = true`). 5-faza uni FAQAT ISHLATADI, yangi
   mexanizm o'ylab TOPMAYDI. `CHECK` unutilsa butun kafolat yo'q bo'ladi:
   FK yolg'iz o'zi `(id, false)` juftligiga havolani ham QABUL QILARDI.

5. QAYTA ISHLASH — YANGI QATOR, TAHRIR EMAS:
   `UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)`.
   Ikkinchi model (§E.15 dagi `timm` krop-klassifikatori) o'sha kadr va
   o'sha zona uchun RAQOBATLASHUVCHI verdikt yozadi, eskisini o'chirmaydi —
   "yaxshilanishni o'lchash mashinasi" ning butun mexanizmi shu.

6. KO'R AUDIT `CHECK` (D-17.3):
   `CHECK (queue_kind <> 'blind_audit' OR shown_ai_verdict = false)`.
   U «ko'r audit, lekin AI javobi ko'rsatilgan» holatini IFODALAB
   BO'LMAYDIGAN qiladi. `zone_reviews.queue_kind` esa DENORMALIZATSIYA,
   ya'ni u yolg'on yozilishi mumkin bo'lardi — shuning uchun u
   `review_assignments (id, queue_kind)` ga KOMPOZIT FK bilan qadalgan
   (4-banddagi langar naqshining aynan takrori).
=============================================================================

OLTALA JADVAL HAM TENANT JADVALI (`05-PATTERNS.md` §S-1): `market_id` +
RLS `ENABLE` va `FORCE` + tenant policy + `market_id` bilan boshlanuvchi
domen konstraytlari + kompozit FK. `market_id` ustunida inline `ForeignKey`
YOZILMAYDI — sabab `models/base.py::market_fk_column()` docstringida.

⚠ PG `ENUM` TIPI ISHLATILMAYDI. Ustunlar `text` + enum'dan HOSILA `CHECK`
ifodasi (`models/snapshot.py:31-38` naqshi). Sabab ikkita: (a) PG enum
tipiga qiymat qo'shish tranzaksiya ichida bajarilmaydi; (b) loyihada
`cameras.status`, `capture_runs.status` va `stalls.status` allaqachon
`text`+`CHECK` — yangi shakl IKKINCHI konventsiya yaratardi.

⚠ `TimestampMixin` IKKI JADVALGA QO'YILMAYDI (`occupancy_events`,
`zone_reviews`) — `models/snapshot.py:650-653` bilan bir xil sabab:
`updated_at` «bu qatorni tahrirlash mumkin» degan YOLG'ON VA'DA berardi,
holbuki 3-band uni DB darajasida imkonsiz qiladi.

⚠ `business_date` va `slot_time` `snapshots` DAN NUSXALANADI, mustaqil
HISOBLANMAYDI va `GENERATED` EMAS. Ikki mustaqil hisoblash manbai yarim
tunda bir kun farq qilardi (Pitfall 3) — o'sha zona uchun dalil 6-fazada
"yo'q" bo'lib qolardi. `snapshots.business_date` ning O'ZI generated, ya'ni
haqiqat manbai BITTA va u yuqoriroq qatlamda.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Final
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.enums import (
    OccupancyVerdict,
    ResolutionSource,
    ReviewPurpose,
    ReviewQueueKind,
)
from sbozor_core.models.base import Base, TenantMixin, TimestampMixin, uuid_pk

__all__ = [
    "BLIND_AUDIT_NEEDS_ROUND_CHECK",
    "BLIND_AUDIT_NOT_SHOWN_CHECK",
    "CAMERA_ZONE_ACTIVE_INDEX",
    "CAMERA_ZONE_ACTIVE_PREDICATE",
    "EVAL_NEEDS_BLIND_AUDIT_CHECK",
    "HUMAN_VERDICT_CHECK",
    "NO_COVERAGE_IS_PAIRED_CHECK",
    "OCCUPANCY_UNCERTAIN_INDEX",
    "OCCUPANCY_UNCERTAIN_PREDICATE",
    "OCCUPANCY_VERDICT_CHECK",
    "OCCUPANCY_VERDICT_VALUES",
    "POLYGON_IS_ARRAY_CHECK",
    "POLYGON_MAX_VERTICES",
    "POLYGON_MAX_VERTICES_CHECK",
    "POLYGON_MIN_VERTICES",
    "POLYGON_MIN_VERTICES_CHECK",
    "RESOLUTION_SOURCE_CHECK",
    "RESOLUTION_SOURCE_VALUES",
    "REVIEW_PURPOSE_CHECK",
    "REVIEW_PURPOSE_VALUES",
    "REVIEW_QUEUE_KIND_CHECK",
    "REVIEW_QUEUE_KIND_VALUES",
    "SLOT_OCCUPIED_HAS_WINNER_CHECK",
    "SLOT_VERDICT_CHECK",
    "SLOT_VERDICT_VALUES",
    "SNAPSHOT_BILLABLE_ANCHOR",
    "AuditRound",
    "CameraZone",
    "OccupancyEvent",
    "ReviewAssignment",
    "StallSlotOccupancy",
    "ZoneReview",
]

SNAPSHOT_BILLABLE_ANCHOR: Final = "uq_snapshots_billable_anchor"
"""4-faza qo'ygan langarning nomi — `occupancy_events` AYNAN shunga osiladi.

⚠ NOMNING O'ZI QIDIRILADIGAN BELGI (`models/snapshot.py:695-698`): u
konvensiyadan hosila EMAS (`uq_snapshots_id_is_billable` bo'lardi), chunki
`billable_anchor` nomi bu konstrayt TASODIFIY `UNIQUE` emas, ATAYIN
qo'yilgan langar ekanini aytadi.

Konstantaning O'ZI DDL'da ishlatilmaydi (FK NISHONNI ustunlar bo'yicha
topadi, nom bo'yicha emas) — u shu domenning 4-fazadagi qaysi konstraytga
tayanishini KODDA ko'rinadigan qiladi va meta-testlar uni shu yerdan oladi.
Langar yo'qolsa `0018` migratsiyasi «there is no unique constraint matching
given keys for referenced table "snapshots"» bilan yiqiladi — ya'ni
bog'lanish jimgina uzilmaydi.
"""

POLYGON_MIN_VERTICES: Final = 3
"""Poligonning eng kam uchi — uchburchak. Ikki nuqta YUZA bermaydi.

Ikki nuqtali "poligon" `sv.PolygonZone` da nol maydonli soha bo'lardi:
zonaga HECH QACHON hech narsa tushmasdi va rasta abadiy "bo'sh" ko'rinardi
— ya'ni nazoratni jimgina o'chirishning eng arzon yo'li.
"""

POLYGON_MAX_VERTICES: Final = 12
"""Poligonning eng ko'p uchi — DoS chegarasi (T-05-21).

Rasta konturi uchun 12 uch yetarlidan ko'p (odatda 4–6). Chegarasiz
JSON massivi ixtiyoriy kattalikda bo'lardi va har kadr uchun ~30 zona x
nuqtalar soni nuqta-poligon hisobiga aylanardi.
"""

OCCUPANCY_VERDICT_VALUES: tuple[str, ...] = tuple(v.value for v in OccupancyVerdict)
REVIEW_QUEUE_KIND_VALUES: tuple[str, ...] = tuple(k.value for k in ReviewQueueKind)
REVIEW_PURPOSE_VALUES: tuple[str, ...] = tuple(p.value for p in ReviewPurpose)
RESOLUTION_SOURCE_VALUES: tuple[str, ...] = tuple(s.value for s in ResolutionSource)

SLOT_VERDICT_VALUES: tuple[str, ...] = (
    *OCCUPANCY_VERDICT_VALUES,
    ResolutionSource.NO_COVERAGE.value,
)
"""`stall_slot_occupancy.verdict` — `OccupancyVerdict` NING SUPERSETI (D-22).

⚠ IKKI ENUM'DAN HOSILA, QO'LDA YOZILGAN RO'YXAT EMAS. Rasta darajasidagi
hukmda TO'RTINCHI holat bor va u zona darajasida MAVJUD BO'LA OLMAYDI:
`no_coverage` — «bu rastani birorta kamera zonasi qamramaydi».
`aggregate_stall_slot([])` aynan shuni qaytaradi (05-12).

⛔ UNI `empty` GA AYLANTIRISH TAQIQLANGAN (D-22): qamrovsiz rasta
"bo'sh" deb yozilsa u hisobotda YAXSHI natijaga o'xshab ko'rinardi,
holbuki bu — o'lchovning YO'QLIGI. Farq `resolution_source` bilan JUFTLIKDA
qulflangan (`no_coverage_is_paired` konstrayti).

Beshinchi enum yaratilmadi: `no_coverage` allaqachon `ResolutionSource` da
va ikkinchi ta'rif ikki ro'yxatni ajralib ketadigan qilardi.
"""


def _quoted(values: tuple[str, ...]) -> str:
    """SQL literal ro'yxati. Qiymatlar `StrEnum` a'zolari — tashqi kirish emas.

    `market.py`, `identity.py`, `nvr.py` va `snapshot.py` dagi jufti bilan
    bir xil ikki qatorli funksiya va u ATAYIN BESHINCHI marta takrorlanadi:
    umumiy modulga chiqarish `models/base.py` ning ommaviy yuzasini
    kengaytirardi, har bir chaqiruvchi esa baribir O'Z enum'i bilan
    qulflangan.
    """
    return ", ".join(f"'{value}'" for value in values)


OCCUPANCY_VERDICT_CHECK = f"verdict IN ({_quoted(OCCUPANCY_VERDICT_VALUES)})"
"""`occupancy_events.verdict` faqat ma'lum verdiktlardan biri (enum'dan HOSILA)."""

SLOT_VERDICT_CHECK = f"verdict IN ({_quoted(SLOT_VERDICT_VALUES)})"
"""`stall_slot_occupancy.verdict` — supersetdan (yuqoridagi docstring)."""

HUMAN_VERDICT_CHECK = f"human_verdict IN ({_quoted(OCCUPANCY_VERDICT_VALUES)})"
"""`zone_reviews.human_verdict` — AI bilan AYNAN BIR XIL to'plamdan (enum'dan HOSILA).

⚠ ATAYIN BIR XIL TO'PLAM. Inson javobi va model javobi 05-12 da
`effective_verdict()` orqali BIR USTUNGA quyiladi
(`COALESCE(review.human_verdict, event.verdict)` shakli), ya'ni ikki xil
domen ikkinchi aylantirish jadvalini talab qilardi.

⚠ DB `uncertain` ni RAD ETMAYDI, UI esa uni TAKLIF QILMAYDI (05-10:
nazoratchiga faqat «band»/«bo'sh» tugmasi ko'rsatiladi). Bu 2-fazadagi
`open_weekdays` qarori bilan bir xil sinf: sxema xulqni TAXMIN QILMAYDI,
u faqat mumkin bo'lgan qiymatlar to'plamini belgilaydi. Teskarisi —
`CHECK (human_verdict <> 'uncertain')` — «bilmayman» javobini yozib
bo'lmaydigan qilardi va nazoratchini TAXMIN QILISHGA majburlardi, ya'ni
xolis o'lchovga ataylab shovqin qo'shardi.
"""

REVIEW_QUEUE_KIND_CHECK = f"queue_kind IN ({_quoted(REVIEW_QUEUE_KIND_VALUES)})"
"""`queue_kind` — IKKI JADVALDA bir xil ifoda (`review_assignments`, `zone_reviews`)."""

REVIEW_PURPOSE_CHECK = f"purpose IN ({_quoted(REVIEW_PURPOSE_VALUES)})"
"""`review_assignments.purpose` faqat `eval`/`train` (enum'dan HOSILA)."""

RESOLUTION_SOURCE_CHECK = f"resolution_source IN ({_quoted(RESOLUTION_SOURCE_VALUES)})"
"""`stall_slot_occupancy.resolution_source` (enum'dan HOSILA)."""

BLIND_AUDIT_NOT_SHOWN_CHECK = (
    f"queue_kind <> '{ReviewQueueKind.BLIND_AUDIT.value}' OR shown_ai_verdict = false"
)
"""D-17.3 — «KO'R AUDIT, LEKIN JAVOB KO'RSATILGAN» QATORI MAVJUD BO'LA OLMAYDI.

Bu fazadagi eng nozik kafolat, chunki uni buzish uchun hech narsani
"buzish" kerak emas: yetarli bo'lardi ko'r audit sahifasiga AI javobini
ko'rsatib qo'yish va qatorni odatdagidek yozish. O'shanda nazoratchi javobi
ANKORLANARDI (u model bilan rozi bo'lish tomon siljirdi) va aniqlik
hisoboti o'z-o'zini tasdiqlardi — nosozlik esa hech qayerda ko'rinmasdi,
chunki hamma qator "to'g'ri" bo'lardi.

Ifoda `ReviewQueueKind.BLIND_AUDIT` dan HOSILA: a'zo qiymati o'zgarsa
konstrayt jimgina hech nimani qamramay qolardi.
"""

BLIND_AUDIT_NEEDS_ROUND_CHECK = (
    f"queue_kind <> '{ReviewQueueKind.BLIND_AUDIT.value}' OR audit_round_id IS NOT NULL"
)
"""Ko'r audit qatori DOIRAGA tegishli bo'lishi SHART (D-17.1).

Doirasiz («yakka») ko'r audit yozuvi namunani qayta chizib bo'lmasligi
kafolatini yo'q qilardi: `audit_rounds` qatori `frame_size`,
`frame_predicate_hash` va `drawn_at` ni MUZLATIB saqlaydi, ya'ni tortish
KEYINCHALIK tekshirilishi mumkin. Doirasiz qator esa qayerdan kelganini
hech qachon isbotlay olmasdi.
"""

EVAL_NEEDS_BLIND_AUDIT_CHECK = (
    f"purpose <> '{ReviewPurpose.EVAL.value}' OR queue_kind = '{ReviewQueueKind.BLIND_AUDIT.value}'"
)
"""D-14 — `eval` NAMUNASI FAQAT KO'R AUDITDAN KELISHI MUMKIN.

Noaniq navbat TANLANGAN (biased) namuna: unga faqat model IKKILANGAN
zonalar tushadi. O'sha javoblarni aniqlik hisobotiga qo'shish foizni
sun'iy PASAYTIRARDI yoki OSHIRARDI (yo'nalish ma'lumotga bog'liq) —
ikkala holatda ham raqam MODELNING UMUMIY ANIQLIGI bo'lmasdi.

Konstrayt kelajakdagi «hamma javoblar hisobga kirsin, ma'lumot isrof
bo'lmasin» degan oqilona ko'rinuvchi o'zgarishni DB darajasida to'xtatadi.
D-15 (inson javobi bandlikni HAM tuzatadi) buzilmaydi: tuzatish
`stall_slot_occupancy` orqali boradi va u `purpose` ga umuman qaramaydi.
"""

POLYGON_IS_ARRAY_CHECK = "jsonb_typeof(polygon) = 'array'"
"""`polygon` — JSON MASSIV. Obyekt yoki satr yozilishi imkonsiz."""

_POLYGON_VERTEX_COUNT = (
    f"CASE WHEN {POLYGON_IS_ARRAY_CHECK} THEN jsonb_array_length(polygon) ELSE -1 END"
)
"""Uchlar soni — MASSIV BO'LMAGAN qiymat uchun `-1`.

⚠ `CASE` MAJBURIY, oddiy `jsonb_array_length(polygon) >= 3` YETARLI EMAS.
PostgreSQL `CHECK` konstraytlarini ANIQLANMAGAN tartibda baholaydi, ya'ni
`{"a": 1}` yozilganda `polygon_is_array` dan OLDIN uzunlik ifodasi
baholanishi mumkin va u `22023 cannot get array length of a non-array`
bilan yiqilardi — ya'ni rad etish `CheckViolation` emas, boshqa sinf xato
bo'lardi va chaqiruvchi uni 409 ga aylantira olmasdi. `CASE` bilan har
qanday kirish `polygon_min_vertices` da TOZA `23514` beradi.
"""

POLYGON_MIN_VERTICES_CHECK = f"{_POLYGON_VERTEX_COUNT} >= {POLYGON_MIN_VERTICES}"
"""Kamida uchburchak (yuqoridagi `POLYGON_MIN_VERTICES` docstringi)."""

POLYGON_MAX_VERTICES_CHECK = f"{_POLYGON_VERTEX_COUNT} <= {POLYGON_MAX_VERTICES}"
"""Ko'pi bilan 12 uch (T-05-21)."""

SLOT_OCCUPIED_HAS_WINNER_CHECK = (
    f"(verdict = '{OccupancyVerdict.OCCUPIED.value}') = (winning_occupancy_event_id IS NOT NULL)"
)
"""D-21 NING TRANZITIV YARIMI — `models/snapshot.py:709-712` ning aynan shakli.

`stall_slot_occupancy` YANGI MEXANIZM O'YLAB TOPMAYDI: u billing kafolatini
`winning_occupancy_event_id` orqali DAVOM ETTIRADI —

    stall_slot_occupancy -> occupancy_events -> snapshots (id, is_billable)

Ikki tomonlama tenglik (`=`, `->` emas) IKKALA nosozlikni ham yopadi:
  * `occupied`, lekin g'olib hodisa YO'Q -> hisobga dalilsiz qator tushardi;
  * `empty`, lekin g'olib hodisa BOR   -> dalil hukmga zid bo'lardi va
    "qaysi biri rost?" savoli javobsiz qolardi.
"""

NO_COVERAGE_IS_PAIRED_CHECK = (
    f"(verdict = '{ResolutionSource.NO_COVERAGE.value}') "
    f"= (resolution_source = '{ResolutionSource.NO_COVERAGE.value}')"
)
"""D-22 — «QAMROVSIZ» IKKALA USTUNDA BIRDAN, YOKI UMUMAN YO'Q.

Usiz `(verdict='empty', resolution_source='no_coverage')` qatori mumkin
bo'lardi va u hisobotda "bo'sh" hisoblagichiga tushardi — ya'ni D-22
konventsiyaga aylanardi. Teskarisi ham yopiladi:
`(verdict='no_coverage', resolution_source='ai')` "model qamrovsizlikni
aniqladi" degan ma'nosiz da'vo bo'lardi.
"""


# ===========================================================================
# QISMAN INDEKS NOMLARI — MODEL VA MIGRATSIYA UCHUN YAGONA MANBA
# ===========================================================================
#
# ⚠ NEGA INDEKSLAR MODELDA HAM E'LON QILINADI (o'lchangan, 03-03):
# `op.create_index(...)` yolg'iz o'zi yetarli EMAS. Alembic autogenerate
# model metadata'sini baza bilan solishtiradi va modelda e'lon qilinmagan
# indeksni "o'chirilgan" deb hisoblaydi — `test_autogenerate_is_empty`
# `remove_index` bilan QIZARADI. Ya'ni migratsiyada indeks yaratish uni
# sxemaga qo'shadi, LEKIN keyingi `alembic revision --autogenerate` uni
# O'CHIRISHNI taklif qilardi va kimdir buni "tozalash" deb qabul qilishi
# mumkin edi.

CAMERA_ZONE_ACTIVE_INDEX = "ix_camera_zones_active"
OCCUPANCY_UNCERTAIN_INDEX = "ix_occupancy_events_uncertain"

CAMERA_ZONE_ACTIVE_PREDICATE = "is_active"
"""Faol zonalar indeksining predikati.

⚠ BU PREDIKAT ENUM'DAN HOSILA EMAS va bo'la ham olmaydi — `is_active`
boolean ustun, uning ortida enum yo'q. "Hosila" talabining MAZMUNI esa
baribir bajarilyapti: predikat BITTA joyda e'lon qilinadi va model ham,
`0018` ham SHU KONSTANTADAN oladi. Ikki literal yozilganda ular ajralib
ketishi mumkin edi (`is_active = true` va `is_active`) va o'shanda indeks
ta'rifi bazada va modelda farq qilib, `alembic check` har safar soxta diff
berardi.
"""

OCCUPANCY_UNCERTAIN_PREDICATE = f"verdict = '{OccupancyVerdict.UNCERTAIN.value}'"
"""Noaniq navbatning issiq yo'li — predikat `OccupancyVerdict` DAN HOSILA.

`DISCOVERY_RUN_ACTIVE_PREDICATE` (`models/nvr.py`) va
`CAPTURE_DUE_PREDICATE` (`models/snapshot.py`) bilan bir xil qoida va bir
xil sabab: qo'lda ko'chirilgan literal enum bilan ajralib ketganda indeks
JIMGINA hech nimani qamramay qolardi va noaniq navbat kunlik jadvalning
to'liq skaniga o'tardi.
"""


class CameraZone(Base, TenantMixin, TimestampMixin):
    """Kamera kadridagi rasta konturi — NORMALANGAN va VERSIYALANGAN (AI-01).

    =========================================================================
    ⚠ NOM: `camera_zones`, `zones` EMAS (D-06). `zones` — BOZOR HUDUDI
    (`models/market.py::Zone`), unga `stalls.zone_id NOT NULL` tayanadi.
    Ikki tushuncha uch tilda ham KVALIFIKATOR bilan ajratiladi («bozor
    zonasi» / «kamera zonasi»); kvalifikatorsiz «zona» so'zi na kodda, na
    tarjimada ishlatilmaydi.
    =========================================================================

    KOORDINATALAR NORMALANGAN (0..1) VA BU IKKI XIL NOSOZLIKNI YOPADI:
    kamera qayta kashf qilinganda (kanal ko'chdi) va ruxsati o'zgarganda
    (`main` -> `sub` oqim) piksel koordinatalari jimgina noto'g'ri joyni
    ko'rsatardi — poligon "biroz siljigan" bo'lardi va aynan chegaradagi
    rastalar noto'g'ri hisoblanardi. `source_width`/`source_height` esa
    poligon QAYSI kadr o'lchamida chizilganini yozadi, ya'ni nisbat
    o'zgarganini aniqlash mumkin (`aspect_ratio_matches`, 05-06).

    VERSIYALANGAN — TAHRIR `UPDATE` EMAS, YANGI QATOR (D-07). Eskisi
    `is_active = false` bo'ladi va JOYIDA QOLADI:
    `occupancy_events.zone_version` o'sha paytdagi poligonga ishora qiladi,
    ya'ni o'tmishdagi dalil "qaysi kontur bo'yicha" degan savolga javob
    beradi. Poligonni joyida tahrirlash butun tarixni RETROAKTIV qayta
    talqin qilardi — `tariffs` ning o'tmishdagi narxi bilan bir xil sinf
    xavf (T-05-26).

    JADVAL AUDIT OSTIDA (`AUDITED_TABLES`): poligonni jimgina siljitish —
    o'sha rastaning «band, lekin to'lovsiz» dalilini YO'Q QILISHNING eng
    arzon yo'li. `cameras.is_archived` bilan aynan bir xil nazoratni
    jimgina o'chirish vektori.

    IKKITA KOMPOZIT FK (`cameras` VA `stalls`) — tenant chegarasi SXEMADA
    yopiladi: A bozorining kamerasi B bozorining rastasiga bog'lana
    OLMAYDI, va bu RLS emas, chet el kaliti.
    """

    __tablename__ = "camera_zones"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_camera_zones_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "camera_id"],
            ["cameras.market_id", "cameras.id"],
            name="fk_camera_zones_market_id_camera_id_cameras",
        ),
        ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_camera_zones_market_id_stall_id_stalls",
        ),
        # Bitta kamera + bitta rasta uchun bitta VERSIYA. Dublikat versiya
        # «qaysi kontur amalda?» savolini javobsiz qoldirardi va 05-08
        # tasodifiy birini tanlardi. `market_id` BIRINCHI — tenant
        # invarianti #5.
        UniqueConstraint(
            "market_id",
            "camera_id",
            "stall_id",
            "version",
            name="uq_camera_zones_market_id_camera_id_stall_id_version",
        ),
        # KOMPOZIT FK NISHONI: `occupancy_events` `(market_id,
        # camera_zone_id)` ga havola qiladi.
        UniqueConstraint("market_id", "id", name="uq_camera_zones_market_id_id"),
        CheckConstraint(POLYGON_IS_ARRAY_CHECK, name="polygon_is_array"),
        CheckConstraint(POLYGON_MIN_VERTICES_CHECK, name="polygon_min_vertices"),
        CheckConstraint(POLYGON_MAX_VERTICES_CHECK, name="polygon_max_vertices"),
        # Nol yoki manfiy o'lcham nisbat tekshiruvini (05-06) nolga bo'lish
        # bilan yiqitardi va zona hech qachon denormalizatsiya qilinmasdi.
        CheckConstraint("source_width > 0", name="source_width_positive"),
        CheckConstraint("source_height > 0", name="source_height_positive"),
        CheckConstraint("version > 0", name="version_positive"),
        # ⚠ FAOL ZONALARNING ISSIQ YO'LI. `market_id` bilan BOSHLANADI:
        #   05-08 har kadr uchun «shu kameraning FAOL zonalari» ni tenant
        #   konteksti ostida so'raydi. Qisman: eski versiyalar (vaqt
        #   o'tgani sari ularning soni faol zonalardan ko'p bo'ladi)
        #   indeksga umuman tushmaydi.
        Index(
            CAMERA_ZONE_ACTIVE_INDEX,
            "market_id",
            "camera_id",
            postgresql_where=text(CAMERA_ZONE_ACTIVE_PREDICATE),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    camera_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    stall_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # 1 dan boshlanadi va HAR TAHRIRDA oshadi (D-07). `occupancy_events`
    # bu sonni NUSXALAB oladi, ya'ni dalil o'z konturini nomma-nom biladi.
    version: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("1"))
    # `[[x, y], ...]`, har biri 0..1 oralig'ida (`list[tuple[float, float]]`).
    # Diapazon va o'z-o'zi bilan kesishish SERVERDA tekshiriladi
    # (`validate_polygon`, 05-06) — frontend tekshiruvi TAKROR, ishonch emas.
    polygon: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False)
    # Poligon QAYSI kadr o'lchamida chizilgan. Kamera ruxsati o'zgarsa
    # nisbat farqi shu yerdan aniqlanadi va zona «tekshirilishi kerak»
    # deb belgilanadi — poligon JIMGINA noto'g'ri joyni ko'rsatmaydi.
    source_width: Mapped[int] = mapped_column(Integer(), nullable=False)
    source_height: Mapped[int] = mapped_column(Integer(), nullable=False)
    # ⚠ SOFT-DELETE EMAS, VERSIYA BAYROG'I: `false` = «eskirgan kontur,
    #   tarixdagi dalil unga tayanadi». Qator hech qachon o'chirilmaydi
    #   (`cameras.is_archived` bilan bir xil qaror).
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=text("true"))


class OccupancyEvent(Base, TenantMixin):
    """AI ning BITTA zona uchun bergan javobi — dalil zanjirining ikkinchi halqasi.

    =========================================================================
    IKKI QAT'IY KAFOLAT, IKKALASI HAM SXEMADA.

    **(a) YAROQSIZ KADR BANDLIK DALILI YARATA OLMAYDI (D-21).** Uch satr
    4-fazadan aynan ko'chirilgan:

        snapshot_is_billable boolean NOT NULL DEFAULT true
        CHECK  (snapshot_is_billable)
        FOREIGN KEY (snapshot_id, snapshot_is_billable)
            REFERENCES snapshots (id, is_billable)

    `snapshots.is_billable` — `GENERATED ALWAYS AS (quality_verdict = 'ok')
    STORED`, ya'ni `quality_verdict <> 'ok'` kadr uchun kerak bo'lgan
    `(id, true)` juftligi JADVALDA UMUMAN MAVJUD BO'LMAYDI. `CHECK` esa
    juftlikning IKKINCHI YARMI va usiz FK yolg'iz o'zi `(id, false)` ga
    havolani ham qabul qilardi. Kafolat KELISHUV emas, DB RAD ETISHI.

    ⚠ KADR AVVAL FILTRLANADI (§E.13): `quality_verdict <> 'ok'` kadr uchun
    `detect` UMUMAN ishga tushmaydi. Bu konstraytni ortiqcha QILMAYDI —
    «oldindan filtrlash mumkin bo'lgan xatoni imkonsiz xatoga
    aylantirishdan yaxshiroq», lekin filtr KODDA, kafolat esa SXEMADA
    yashaydi va ikkinchisi birinchisidan omon qoladi.

    **(b) QATOR HECH QACHON TAHRIRLANMAYDI (D-12).** `0018` bu jadvalga
    SHARTSIZ `BEFORE UPDATE OR DELETE` qo'riqchisini ulaydi. Qayta ishlash
    — YANGI QATOR: `UNIQUE (market_id, snapshot_id, camera_zone_id,
    model_version)`. Ikkinchi model (§E.15 `timm`) o'sha kadr va o'sha
    zona uchun raqobatlashuvchi verdikt yozadi, eskisini o'chirmaydi.
    Aks holda «model yaxshilandimi?» savolini o'lchash uchun solishtiradigan
    narsa qolmasdi.
    =========================================================================

    JADVAL AUDIT TRIGGERIDAN CHIQARILGAN — IKKI MUSTAQIL SABAB:
      (a) HAJM: 175 kadr/kun/bozor x ~30 zona ~ 5 000 qator/kun/bozor —
          4-fazadagi ~525 audit qatorining o'n barobari. `audit_log`
          append-only, ya'ni u hech qachon kichraymaydi;
      (b) jadval yuqoridagi (b) bandi bo'yicha SHARTSIZ o'zgarmas — audit
          faqat `INSERT` ni ko'rardi va bu o'sha ma'lumotning IKKINCHI
          NUSXASI bo'lardi.

    `TimestampMixin` YO'Q: hodisa o'zgarmaydi. `updated_at` «bu qatorni
    tahrirlash mumkin» degan yolg'on va'da berardi — o'zgarmaslik triggeri
    esa uni DARHOL yolg'onga chiqarardi.

    ⚠ `business_date` va `slot_time` `snapshots` DAN NUSXALANADI va
    `GENERATED` EMAS. Ikki mustaqil hisoblash manbai yarim tunda bir kun
    farq qilardi (Pitfall 3): kadr `snapshots` da 09-01 ga, dalil esa
    09-02 ga tushardi va 6-faza uni "yo'q" deb ko'rardi.
    """

    __tablename__ = "occupancy_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_occupancy_events_market_id_markets"
        ),
        # TENANT chegarasi: A bozorining hodisasi B bozorining kadriga
        # bog'lana olmaydi.
        ForeignKeyConstraint(
            ["market_id", "snapshot_id"],
            ["snapshots.market_id", "snapshots.id"],
            name="fk_occupancy_events_market_id_snapshot_id_snapshots",
        ),
        # ⚠⚠ D-21 NING BUTUN KAFOLATI — `uq_snapshots_billable_anchor` GA
        #   OSILADI (klass docstringidagi (a) bandi). NOM QO'LDA berilgan:
        #   konvensiya 70 belgilik nom berardi, PostgreSQL esa
        #   identifikatorni 63 baytga JIMGINA kesadi va model/baza nomlari
        #   farq qilib `alembic check` soxta diff berardi.
        ForeignKeyConstraint(
            ["snapshot_id", "snapshot_is_billable"],
            ["snapshots.id", "snapshots.is_billable"],
            name="fk_occupancy_events_snapshot_billable",
        ),
        ForeignKeyConstraint(
            ["market_id", "camera_zone_id"],
            ["camera_zones.market_id", "camera_zones.id"],
            name="fk_occupancy_events_market_id_camera_zone_id_camera_zones",
        ),
        # ⚠ QAYTA ISHLASH — YANGI QATOR (klass docstringidagi (b) bandi).
        #   `model_version` KALITGA KIRADI, ya'ni ikkinchi model bir xil
        #   kadr+zona uchun o'z qatorini yozadi va ular SOLISHTIRILADI.
        #   Nom qisqartirilgan: to'liq ustun ro'yxati 70 belgi berardi.
        UniqueConstraint(
            "market_id",
            "snapshot_id",
            "camera_zone_id",
            "model_version",
            name="uq_occupancy_events_market_id_snapshot_zone_model",
        ),
        # KOMPOZIT FK NISHONI: `review_assignments` va
        # `stall_slot_occupancy` `(market_id, id)` ga havola qiladi.
        UniqueConstraint("market_id", "id", name="uq_occupancy_events_market_id_id"),
        # ⚠ JUFTLIKNING IKKINCHI YARMI — USIZ FK MA'NOSIZ.
        CheckConstraint("snapshot_is_billable", name="snapshot_is_billable"),
        CheckConstraint(OCCUPANCY_VERDICT_CHECK, name="verdict_allowed"),
        # Ishonch 0..1: chegaralar (`thresholds_version`) shu shkalada
        # taqqoslanadi. Diapazondan tashqaridagi qiymat `uncertain` oynasini
        # ma'nosiz qilardi.
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_in_unit_range"),
        CheckConstraint("zone_version > 0", name="zone_version_positive"),
        CheckConstraint("thresholds_version > 0", name="thresholds_version_positive"),
        CheckConstraint("length(btrim(model_version)) > 0", name="model_version_not_blank"),
        # ⚠ NOANIQ NAVBATNING ISSIQ YO'LI. `market_id` bilan BOSHLANADI —
        #   navbat HAR DOIM bitta bozor kontekstida quriladi. Qisman:
        #   `occupied`/`empty` qatorlar (odatda ~90%) indeksga umuman
        #   tushmaydi, ya'ni indeks kichik qoladi.
        Index(
            OCCUPANCY_UNCERTAIN_INDEX,
            "market_id",
            "business_date",
            postgresql_where=text(OCCUPANCY_UNCERTAIN_PREDICATE),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    snapshot_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # ⚠ HOSILA EMAS, LANGAR: qiymat HAR DOIM `true` (`CHECK` boshqasini
    #   rad etadi) va uning YAGONA vazifasi kompozit FK'ning ikkinchi
    #   ustuni bo'lish. `DEFAULT true` — chaqiruvchi uni yozishi shart
    #   emas, ya'ni kafolat "eslab qolinadigan" narsaga aylanmaydi.
    snapshot_is_billable: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("true")
    )
    camera_zone_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # ⚠ `snapshots.business_date` DAN NUSXALANADI (klass docstringi).
    business_date: Mapped[date] = mapped_column(Date(), nullable=False)
    # ⚠ `snapshots.slot_time` DAN NUSXALANADI — mustaqil hisoblanmaydi.
    slot_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    # `sbozor_core.enums.OccupancyVerdict`. YOZISH PAYTIDA qo'yiladi va
    # hech qachon qayta baholanmaydi — `snapshots.quality_verdict` bilan
    # bir xil qaror (T-04-23) va bir xil sabab: chegarani sozlash
    # o'tmishdagi hukmlarni RETROAKTIV o'zgartirardi.
    verdict: Mapped[str] = mapped_column(Text(), nullable=False)
    # O'LCHOVNING O'ZI SAQLANADI, FAQAT HUKM EMAS: real Karmana kadrlari
    # kelganda chegaralar SQL bilan sozlanadi (`percentile_cont`), qayta
    # aniqlash bilan emas.
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    # QAYSI model yozgan (`rfdetr-large-1.9.1`, keyinroq `timm-crop-v1`).
    # Kalitga kiradi — raqobatlashuvchi verdikt YANGI qator bo'ladi.
    model_version: Mapped[str] = mapped_column(Text(), nullable=False)
    # ⚠ CHEGARALAR QATORDA YASHAYDI (D-11) — `quality_thresholds_version`
    #   naqshi. Sozlash SQL bilan bo'ladi, migratsiya bilan EMAS, va
    #   o'tmishdagi hukmlar o'z chegara to'plamini eslab qoladi.
    thresholds_version: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    # `camera_zones.version` DAN NUSXALANADI: dalil qaysi kontur bo'yicha
    # olinganini nomma-nom biladi (D-07, T-05-26).
    zone_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditRound(Base, TenantMixin):
    """Ko'r auditning BITTA tortish doirasi — MUZLATILGAN dalil (D-13/D-17.1).

    =========================================================================
    DOIRA NEGA JADVAL, NEGA SHUNCHAKI «30 TA QATOR TORTILDI» EMAS.

    Xolis aniqlik da'vosi TORTISHNING O'ZI tekshirilishi mumkin bo'lgandagina
    ma'noga ega. Uch fakt shu qatorda MUZLATILADI:

      `frame_size`           — doira TORTILGAN PAYTDA nechta nomzod bor edi.
                               Keyin hisoblab bo'lmaydi: kun davomida yangi
                               hodisalar qo'shiladi va "30 tadan 30 tasi"
                               bilan "5000 tadan 30 tasi" butunlay boshqa
                               kuchdagi da'vo.
      `frame_predicate_hash` — nomzodlar QAYSI shart bilan tanlangani.
                               Shart jimgina o'zgarsa (masalan faqat
                               "ishonchli" hodisalar qolsa) namuna
                               XOLISLIGINI yo'qotardi va buni hech kim
                               sezmasdi.
      `drawn_at`             — qachon tortilgani. Kun yopilgandan KEYIN
                               tortilgan doira boshqa ma'noga ega.

    URUG' USTUN SIFATIDA SAQLANMAYDI va bu ataylab: u
    `f(market_id, business_date, round_no)` dan HOSILA (D-17.1). Saqlangan
    urug' o'zgartirilishi mumkin bo'lardi, hosila urug' esa — yo'q:
    doirani qayta tortish uchun kunni yoki bozorni o'zgartirish kerak
    bo'lardi.

    ⚠ URUG' YO'LI O'LCHANGAN (`05-01` / W0-3): tartib YADRO `sha256(bytea)`
    bilan hosil qilinadi (`AUDIT_SEED_SHA256_SUPPORTED = true`) va
    `pgcrypto` bazada YO'Q (`PGCRYPTO_ABSENT = true`), ya'ni `digest()`
    ISHLATILMAYDI va `0018` yangi kengaytma TALAB QILMAYDI.
    =========================================================================

    Audit triggeridan CHIQARILGAN: doira — hodisa jurnali va u o'z faktini
    O'ZIDA muzlatib saqlaydi, ya'ni audit ikkinchi nusxani yozardi.

    `TimestampMixin` YO'Q va `created_at` ham yo'q: `drawn_at` AYNAN o'sha
    ma'noni beradi (`alert_events.first_seen_at` bilan bir xil qaror) —
    ikkinchi vaqt juftligi faqat chalkashlik qo'shardi.
    """

    __tablename__ = "audit_rounds"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_audit_rounds_market_id_markets"
        ),
        # Bir kunda bir raqamli doira BIR MARTA. Dublikat doira bir xil
        # urug'dan bir xil namunani qayta tortardi va o'sha zonalar ikki
        # marta hisobga tushardi.
        UniqueConstraint(
            "market_id",
            "business_date",
            "round_no",
            name="uq_audit_rounds_market_id_business_date_round_no",
        ),
        # KOMPOZIT FK NISHONI: `review_assignments` `(market_id,
        # audit_round_id)` ga havola qiladi.
        UniqueConstraint("market_id", "id", name="uq_audit_rounds_market_id_id"),
        CheckConstraint("round_no > 0", name="round_no_positive"),
        # Nol nomzodli doira MUMKIN (kun bo'sh o'tdi), manfiy — yo'q.
        CheckConstraint("frame_size >= 0", name="frame_size_non_negative"),
        CheckConstraint(
            "length(btrim(frame_predicate_hash)) > 0", name="frame_predicate_hash_not_blank"
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    business_date: Mapped[date] = mapped_column(Date(), nullable=False)
    # 1 dan boshlanadi. Kun ichida ikkinchi doira kerak bo'lsa (byudjet
    # oshirildi) u BOSHQA urug' beradi — `05-01` ning W0-3 zondi buni
    # kesishuvsizlik bilan o'lchagan.
    round_no: Mapped[int] = mapped_column(SmallInteger(), nullable=False, server_default=text("1"))
    # Nomzodlar SONI tortish paytida (klass docstringi).
    frame_size: Mapped[int] = mapped_column(Integer(), nullable=False)
    # Nomzodlarni tanlagan SHARTNING xeshi — shart jimgina o'zgarganini
    # keyin ham aniqlash mumkin bo'lishi uchun.
    frame_predicate_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    drawn_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReviewAssignment(Base, TenantMixin):
    """Nazoratchi navbatidagi BITTA yozuv — hodisa va inson orasidagi bog'lanish.

    =========================================================================
    BITTA HODISA IKKI NAVBATDA BO'LA OLMAYDI: `UNIQUE (occupancy_event_id)`.

    Poyga DB'GA TOPSHIRILADI, ilova qatlamida "avval tekshir, keyin yoz"
    QILINMAYDI (`nvr_repo.py:509-517` naqshi): ko'r audit tortish va noaniq
    navbat qurish IKKI ALOHIDA job va ular bir vaqtda ishlashi mumkin.
    "Tekshir-keyin-yoz" ikkalasiga ham bo'sh holatni ko'rsatardi va bitta
    hodisa uchun IKKITA yozuv tug'ilardi — o'shanda nazoratchi bir zonani
    ikki marta ko'rardi va uning ikkinchi javobi aniqlik hisobotiga
    IKKINCHI marta kirardi.

    ⚠ KONSTRAYT `market_id` BILAN BOSHLANMAYDI va bu ATAYIN — sabab
    `test_meta.py::INDEX_EXCEPTIONS` da yozilgan: da'vo «hodisa ENG KO'PI
    BILAN BITTA navbatda» va u tenant chegarasiga bog'liq BO'LMASLIGI
    kerak. `(market_id, occupancy_event_id)` shakli bugun bir xil natija
    berardi (`occupancy_events.id` global noyob), lekin u kafolatni
    IKKINCHI faktga bog'lab qo'yardi.

    ⚠ TARTIB MAJBURIY (§C.8.3): avval ko'r audit namunasi tortiladi, KEYIN
    noaniq navbat quriladi. Teskari tartibda `UNIQUE` audit doirasidan
    "noaniq" larni chiqarib tashlardi — ya'ni xolis namuna aynan model
    ikkilangan holatlarsiz qolardi va o'lchangan aniqlik sun'iy
    ko'tarilardi.
    =========================================================================

    `purpose` TORTISH PAYTIDA to'ladi (D-14, 70/30) va `eval` FAQAT ko'r
    auditdan kelishi mumkin (`eval_needs_blind_audit` konstrayti). Noaniq
    navbatning javoblari `train` bo'ladi: ular tanlangan namuna, ya'ni
    ular bilan o'lchash raqamni shishirardi.

    Audit triggeridan CHIQARILGAN: navbat yozuvi — hodisa jurnali.
    """

    __tablename__ = "review_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_review_assignments_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "occupancy_event_id"],
            ["occupancy_events.market_id", "occupancy_events.id"],
            name="fk_review_assignments_occupancy_event",
        ),
        ForeignKeyConstraint(
            ["market_id", "audit_round_id"],
            ["audit_rounds.market_id", "audit_rounds.id"],
            name="fk_review_assignments_audit_round",
        ),
        # ⚠ KLASS DOCSTRINGIDAGI BIRINCHI BLOK — `market_id` SIZ, ATAYIN.
        UniqueConstraint("occupancy_event_id", name="uq_review_assignments_occupancy_event_id"),
        # KOMPOZIT FK NISHONI: `zone_reviews` `(market_id,
        # review_assignment_id)` ga havola qiladi.
        UniqueConstraint("market_id", "id", name="uq_review_assignments_market_id_id"),
        # ⚠⚠ D-17.3 NING IKKINCHI YARMI — `zone_reviews.queue_kind` NI
        #   HALOL QILADIGAN LANGAR.
        #
        #   `zone_reviews` da `queue_kind` DENORMALIZATSIYA: `CHECK` boshqa
        #   jadvalni o'qiy olmaydi, ya'ni ko'r audit sharti u yerda o'z
        #   nusxasiga tayanishi kerak. Nusxa esa YOLG'ON yozilishi mumkin
        #   bo'lardi — «bu yozuv aslida `uncertain` navbatidan» deb
        #   belgilash `shown_ai_verdict = true` ga yo'l ochardi.
        #
        #   Shuning uchun `zone_reviews` `(review_assignment_id, queue_kind)`
        #   juftligiga kompozit FK qo'yadi va u AYNAN shu langarga tushadi.
        #   Bu 4-fazadagi `uq_snapshots_billable_anchor` naqshining aynan
        #   takrori: denormalizatsiya tenant/haqiqat chegarasini bo'shatish
        #   uchun bahona emas.
        UniqueConstraint("id", "queue_kind", name="uq_review_assignments_queue_anchor"),
        CheckConstraint(REVIEW_QUEUE_KIND_CHECK, name="queue_kind_allowed"),
        CheckConstraint(REVIEW_PURPOSE_CHECK, name="purpose_allowed"),
        CheckConstraint(BLIND_AUDIT_NEEDS_ROUND_CHECK, name="blind_audit_needs_round"),
        CheckConstraint(EVAL_NEEDS_BLIND_AUDIT_CHECK, name="eval_needs_blind_audit"),
    )

    id: Mapped[UUID] = uuid_pk()
    occupancy_event_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # `NULL` = noaniq navbat. Ko'r audit uchun MAJBURIY
    # (`blind_audit_needs_round`).
    audit_round_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    # `sbozor_core.enums.ReviewQueueKind`.
    queue_kind: Mapped[str] = mapped_column(Text(), nullable=False)
    # `sbozor_core.enums.ReviewPurpose` — TORTISH PAYTIDA (D-14).
    # Standart `train`: noaniq navbat uchun to'g'ri javob va u xolis
    # o'lchovga tasodifan kirib qolmaydi (`eval` ATAYIN qo'yiladi).
    purpose: Mapped[str] = mapped_column(
        Text(), nullable=False, server_default=text(f"'{ReviewPurpose.TRAIN.value}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ZoneReview(Base, TenantMixin):
    """Nazoratchining javobi — ALOHIDA QATOR, AI javobining TAHRIRI EMAS (D-12).

    =========================================================================
    NEGA `INSERT`, NEGA `UPDATE` EMAS.

    AI javobi va inson javobi IKKI XIL DALIL. Ularni bitta ustunga yozish
    (`occupancy_events.verdict` ni yangilash) modelning ASL javobini
    o'chirardi — ya'ni «model qanchalik to'g'ri edi?» savoliga javob
    beradigan yagona ma'lumot yo'q bo'lardi. Yakuniy hukm esa HISOBLANADIGAN
    KO'RINISH: `COALESCE(review.human_verdict, event.verdict)` (§B.5.2) —
    2-fazadagi «qoldiq har doim hisoblanadigan ko'rinish» qoidasining
    takrori.

    JAVOB HAM O'ZGARMAS (D-17.4). `0018` bu jadvalga SHARTSIZ `BEFORE
    UPDATE OR DELETE` qo'riqchisini ulaydi: ko'r audit javobi OSHKOR
    QILINGANDAN KEYIN (ya'ni nazoratchi AI javobini ko'rgach) tahrirlanishi
    mumkin bo'lsa, xolis o'lchov ma'nosini butunlay yo'qotardi — javobni
    "to'g'rilash" mumkin bo'lgan o'lchov o'lchov emas.

    ⚠ JADVALDA IKKALA TRIGGER HAM BOR (audit + o'zgarmaslik) va Postgres
    ning tartib qoidasi aynan kerakli natijani beradi: `BEFORE` `AFTER`
    dan oldin yuradi, ya'ni qo'riqchi RAD ETGAN `UPDATE` `audit_log` ga
    qator QOLDIRMAYDI. Rad etilgan urinish "o'zgardi" deb yozilmasin.

    `TimestampMixin` YO'Q va `created_at` ham yo'q: `decided_at` AYNAN
    o'sha ma'noni beradi.
    =========================================================================

    `queue_kind` — DENORMALIZATSIYA, LEKIN QADALGAN. `CHECK` boshqa
    jadvalni o'qiy olmaydi, shuning uchun D-17.3 sharti shu yerdagi nusxaga
    tayanadi. Nusxa yolg'on bo'lmasligi uchun u `(review_assignment_id,
    queue_kind)` kompozit FK bilan `review_assignments (id, queue_kind)` ga
    qadalgan — `snapshots (id, is_billable)` langari bilan bir xil naqsh.

    JADVAL AUDIT OSTIDA (`AUDITED_TABLES`): nazoratchining verdikti kunlik
    patta hisobini o'zgartiradi, ya'ni u `tariffs` va `stall_assignments`
    bilan BIR OILADA — insonning moliyaviy oqibatli qarori.
    """

    __tablename__ = "zone_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_zone_reviews_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "review_assignment_id"],
            ["review_assignments.market_id", "review_assignments.id"],
            name="fk_zone_reviews_review_assignment",
        ),
        # ⚠⚠ KO'R AUDIT LANGARI (klass docstringi): `queue_kind` NUSXASI
        #   MANBASIGA QADALADI. Usiz D-17.3 ning `CHECK` i o'z nusxasiga
        #   ishonardi va nusxani yolg'on yozish uni chetlab o'tardi.
        ForeignKeyConstraint(
            ["review_assignment_id", "queue_kind"],
            ["review_assignments.id", "review_assignments.queue_kind"],
            name="fk_zone_reviews_queue_kind_anchor",
        ),
        # ⚠ `users` GA FK BOR va u `user_market_roles` / `refresh_tokens`
        #   bilan bir xil naqsh. Sabab dalil zanjirida: mavjud bo'lmagan
        #   foydalanuvchiga ishora qiladigan javob DALIL EMAS — «kim
        #   qaradi?» savoli javobsiz qolardi.
        #   ⛔ `ondelete` YO'Q (NO ACTION): javobi bor foydalanuvchini
        #   o'chirish RAD ETILADI. `CASCADE` bo'lganda bitta `DELETE FROM
        #   users` nazoratchining butun tarixini o'chirib yuborardi — bu
        #   aynan `market_delete_draft()` da `audit_log` ni kaskadga
        #   qo'shmaslik qarori bilan bir xil sinf (3-fazada o'lchangan).
        ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name="fk_zone_reviews_reviewer_id_users"
        ),
        # Bitta topshiriqqa BITTA javob. Ikkinchi javob "qaysi biri
        # hisobga kiradi?" savolini javobsiz qoldirardi va o'zgarmaslik
        # triggerini `INSERT` orqali chetlab o'tish yo'li bo'lardi:
        # tahrirlash o'rniga ikkinchi qator yoziladi.
        # ⚠ `market_id` SIZ — `uq_review_assignments_occupancy_event_id`
        #   bilan bir xil sabab va u `INDEX_EXCEPTIONS` da yozilgan.
        UniqueConstraint("review_assignment_id", name="uq_zone_reviews_review_assignment_id"),
        # ⚠⚠ D-17.3 — «KO'R, LEKIN KO'RSATILGAN» IFODALAB BO'LMAYDI.
        CheckConstraint(BLIND_AUDIT_NOT_SHOWN_CHECK, name="blind_audit_not_shown"),
        CheckConstraint(REVIEW_QUEUE_KIND_CHECK, name="queue_kind_allowed"),
        CheckConstraint(HUMAN_VERDICT_CHECK, name="human_verdict_allowed"),
        CheckConstraint("decision_ms IS NULL OR decision_ms >= 0", name="decision_ms_non_negative"),
    )

    id: Mapped[UUID] = uuid_pk()
    review_assignment_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # DENORMALIZATSIYA, LEKIN QADALGAN (klass docstringi).
    queue_kind: Mapped[str] = mapped_column(Text(), nullable=False)
    # ⚠ SERVER HISOBLAYDI, KLIENT YUBORMAYDI (05-10: `AnswerRequest` da bu
    #   maydon UMUMAN e'lon qilinmagan). Ko'r auditda HAR DOIM `false` va
    #   buni `blind_audit_not_shown` konstrayti majburlaydi — klient
    #   qatlami buzilgan taqdirda ham.
    shown_ai_verdict: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    # `sbozor_core.enums.OccupancyVerdict` — AI bilan bir xil to'plamdan.
    human_verdict: Mapped[str] = mapped_column(Text(), nullable=False)
    reviewer_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Nazoratchi zonaga qancha vaqt qaragani — FAQAT DIAGNOSTIKA (D-16
    # ishonchlilik o'lchovining kirishi). `NULL` = klient o'lchamadi;
    # kafolat unga TAYANMAYDI, shuning uchun `NOT NULL` qilinmadi.
    decision_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)


class StallSlotOccupancy(Base, TenantMixin):
    """RASTA darajasidagi hukm — ko'p kamerali agregatsiyaning natijasi (AI-05).

    =========================================================================
    JADVAL YANGI KAFOLAT MEXANIZMI O'YLAB TOPMAYDI (D-21, tranzitiv).

    Bandlik dalilining billing chegarasi UCH HALQALI zanjir:

        stall_slot_occupancy -> occupancy_events -> snapshots (id, is_billable)

    Bu jadval zanjirni `winning_occupancy_event_id` orqali DAVOM ETTIRADI
    va `CHECK ((verdict = 'occupied') = (winning_occupancy_event_id IS NOT
    NULL))` uni MAJBURLAYDI: "band" hukmi HAR DOIM aniq bir hodisaga —
    ya'ni aniq bir YAROQLI kadrga — ishora qiladi. Ikkinchi (mustaqil)
    tekshiruv yozib qo'yish kafolatni ikkiga bo'lardi va ular ajralib
    ketishi mumkin bo'lardi.
    =========================================================================

    USTUVORLIK TALABDAGIDAN UZUNROQ (D-20 + D-22):
    `occupied > uncertain > empty > no_coverage`. Bitta kamera "band"
    desa rasta BAND (D-20) — ko'rish burchagi tufayli bir kamera savdoni
    ko'rmasligi mumkin, ya'ni "hammasi rozi bo'lsin" qoidasi bandlikni
    tizimli ravishda KAM ko'rsatardi.

    ⚠ `no_coverage` — «BO'SH» EMAS (D-22). Uni `empty` ga aylantirish
    o'lchovning YO'QLIGINI yaxshi natijaga aylantirardi. Farq ikkala
    ustunda birdan yashaydi va `no_coverage_is_paired` konstrayti ularni
    bir-biriga bog'laydi.

    ⚠ `default_empty` — «HECH KIM QARAMADI» (AI-06/D-19), «nazoratchi bo'sh
    dedi» EMAS. `zone_reviews` ga SOXTA qator YOZILMAYDI: tizim yolg'on
    gapirardi va o'sha yolg'on keyin trening datasetiga tushardi.

    `TimestampMixin` YO'Q: jadval MATERIALIZATSIYA, ya'ni u
    `ON CONFLICT DO UPDATE` bilan qayta hisoblanadi. `updated_at` "kimdir
    tahrirladi" degan ma'no berardi, holbuki qayta hisoblash — kunlik
    jobning odatiy ishi va uning izi `occupancy_events` da allaqachon bor.
    `business_date` va `slot_time` esa yuqori qatlamdan NUSXALANADI.
    """

    __tablename__ = "stall_slot_occupancy"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_slot_occupancy_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_stall_slot_occupancy_stall",
        ),
        # ⚠ NULLABLE FK: `occupied` bo'lmagan qatorda g'olib hodisa YO'Q
        #   (`occupied_has_winning_event` uni MAJBURLAYDI). Kompozit shakl
        #   tenant chegarasini shu yerda ham yopadi.
        ForeignKeyConstraint(
            ["market_id", "winning_occupancy_event_id"],
            ["occupancy_events.market_id", "occupancy_events.id"],
            name="fk_stall_slot_occupancy_winning_event",
        ),
        # IDEMPOTENTLIK KALITI: kunlik job `ON CONFLICT DO UPDATE` bilan
        # yozadi va o'tgan kunni qayta hisoblash natijani O'ZGARTIRMAYDI.
        # Dublikat qator 6-fazada bitta slotni ikki marta hisoblardi.
        UniqueConstraint(
            "market_id",
            "stall_id",
            "business_date",
            "slot_time",
            name="uq_stall_slot_occupancy_market_id_stall_id_business_date_slot_time",
        ),
        CheckConstraint(SLOT_VERDICT_CHECK, name="verdict_allowed"),
        CheckConstraint(RESOLUTION_SOURCE_CHECK, name="resolution_source_allowed"),
        CheckConstraint(SLOT_OCCUPIED_HAS_WINNER_CHECK, name="occupied_has_winning_event"),
        CheckConstraint(NO_COVERAGE_IS_PAIRED_CHECK, name="no_coverage_is_paired"),
    )

    id: Mapped[UUID] = uuid_pk()
    stall_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # ⚠ `occupancy_events` DAN (u esa `snapshots` dan) NUSXALANADI —
    #   mustaqil HISOBLANMAYDI. Uchala qatlamda bitta manba.
    business_date: Mapped[date] = mapped_column(Date(), nullable=False)
    slot_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    # `SLOT_VERDICT_VALUES` — `OccupancyVerdict` + `no_coverage`.
    verdict: Mapped[str] = mapped_column(Text(), nullable=False)
    # `sbozor_core.enums.ResolutionSource` — hukm QAYERDAN keldi.
    resolution_source: Mapped[str] = mapped_column(Text(), nullable=False)
    # `occupied` bo'lganda MAJBURIY, aks holda `NULL` bo'lishi SHART
    # (`occupied_has_winning_event`). Bu — dalil havolasi: 6-faza hisob
    # yozuviga aynan shu hodisaning kadrini biriktiradi.
    winning_occupancy_event_id: Mapped[UUID | None] = mapped_column(
        PgUuid(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
