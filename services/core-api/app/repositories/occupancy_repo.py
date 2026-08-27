"""Rasta darajasidagi bandlik — materializatsiya va besh hisoblagich (AI-05, AI-06, D-22).

=============================================================================
⛔ AGREGATSIYA QOIDASI BU YERDA YO'Q — U `sbozor_core.occupancy` DA.

Bu modul XOM qatorlarni beradi va TAYYOR qatorlarni yozadi; «birortasi
band desa band» qoidasi esa sof funksiyada yashaydi va `day_close`
tomonidan chaqiriladi. Qoidani SQL ga ko'chirish tezroq bo'lardi va
aynan shuning uchun rad etildi: o'shanda uni haqiqiy bazasiz sinab
bo'lmasdi va 120 holatli jadval testi (AI-05 ning YAGONA to'liq
isbotlanadigan qismi, §D.11) umuman yozilmasdi.

=============================================================================
⛔ «BESH HISOBLAGICH» — TO'RTTASI O'ZARO INKOR, BESHINCHISI KESISHUVCHI.

    occupied | empty | default_empty | no_coverage   -> yig'indisi = RASTA SONI
    human_confirmed                                  -> yig'indiga KIRMAYDI

`default_empty` `empty` ga QO'SHILMAYDI (D-19): qo'shilsa «nazoratchi
ulgurmadi» degan YAGONA signal yo'qolardi va bozor jimgina pul
yo'qotardi. `no_coverage` ham qo'shilmaydi (D-22): u rasta haqida
ma'lumot YO'QLIGI va uni «bo'sh» ga qo'shish o'lchovning yo'qligini
yaxshi natijaga aylantirardi.

⛔ BESHALASI HAM NOL BO'LGANDA HAM QAYTARILADI. Nol — NATIJA, uning
   yo'qligi emas (`RetentionResult` va `DaySummary` bilan bir xil qoida).

=============================================================================
⚠⚠ KUNLIK XULOSA RASTA DARAJASIDA — VA U BILLING QOIDASI EMAS.

`stall_slot_occupancy` (rasta x SLOT) dan kunlik xulosa (rasta x KUN)
chiqarish SLOTLARARO yig'ish demakdir. Bu sahifa «kun davomida kamida
bir marta band ko'rindi» deydi va bu KO'RSATISH yig'indisi.

⛔ «Kamida 2 slotda band, yoki 1 slot + nazoratchi tasdig'i» degan
   BILL-01 qoidasi bu yerda YO'Q va bo'lmaydi ham — u 6-fazaniki
   (§D.11). Shuning uchun bu yig'ish `sbozor_core` ga funksiya sifatida
   CHIQARILMAGAN: qayta ishlatiladigan shaklga aylansa 6-faza uni
   billing qoidasi deb o'qib, ikkinchi marta yozardi.

Kunlik bo'lakning qoidasi zona -> slot qoidasining AYNAN o'zi:

    band bo'lsa -> `occupied`;
    aks holda qamrov bo'lsa -> DALIL bormi? bor -> `empty`, yo'q ->
    `default_empty`;
    qamrov umuman bo'lmasa -> `no_coverage`.

⚠ INSON «aniq ayta olmadi» degan slot (`verdict = 'uncertain'`,
  `resolution_source = 'human'`) kunlik bo'lakda `empty` ga tushadi va
  `human_confirmed` ga ham kiradi. Bu ATAYIN: uning oqibati «bo'sh» bilan
  bir xil (patta yozilmaydi), lekin u «hech kim qaramadi» EMAS —
  `default_empty` ga qo'shilsa yo'qotish signali nazoratchi ISHLAGAN
  holatlar bilan shishirilardi.

=============================================================================
TENANT FILTRI IKKI QATLAM: RLS policy'si himoya to'ri, `market_id =
:market_id` predikati esa aniq filtr (`review_repo` bilan bir xil naqsh).

⛔ `market_id` METOD ARGUMENTI SIFATIDA OLINMAYDI (T-05-24): u
   `TenantScopedRepository.__init__` dan keladi va YAGONA manba bo'lib
   qoladi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final
from uuid import UUID

from sbozor_core.enums import OccupancyVerdict, ResolutionSource, StallStatus
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import Date, Text, Time, bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.services.accuracy_report import AccuracyRow

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date, datetime, time

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "OccupancyDaySummary",
    "OccupancyRepository",
    "RoundStatus",
    "SlotRow",
    "StallDay",
    "ZoneOutcome",
]

_UUID = PgUuid(as_uuid=True)

_OCCUPIED: Final[str] = OccupancyVerdict.OCCUPIED.value
"""`occupied` — so'rov PARAMETRI, so'rov MATNIDAGI literal emas.

Qiymat `stall_slot_occupancy.verdict` ustunida yashaydi va u
`OccupancyVerdict` dan HOSILA. Literal yozilganda enum o'zgargan kuni
hisoblagich jimgina nolga tushardi: so'rov ishlayverardi, faqat birorta
qator FILTRGA tushmasdi.
"""


# ===========================================================================
# NATIJA TIPLARI
# ===========================================================================


@dataclass(frozen=True, slots=True)
class ZoneOutcome:
    """Bitta ZONANING bitta slotdagi XOM natijasi — hosila HALI qilinmagan.

    ⚠ `effective_verdict` BU YERDA CHAQIRILMAYDI: repozitoriy bazadan
      nima o'qigan bo'lsa shuni beradi va hosila `day_close` da, sof
      funksiya bilan qilinadi. Aks holda qoida ikki joyda (SQL `CASE` va
      Python) yashab, ular ajralib ketishi mumkin bo'lardi.
    """

    stall_id: UUID
    slot_time: time
    event_id: UUID
    event_verdict: str
    review_verdict: str | None
    """`zone_reviews.human_verdict` yoki javob yozilmagan bo'lsa `None`.

    ⚠ NAVBAT TURI BO'YICHA FILTR YO'Q va bu D-15: ko'r audit javobi
      bandlikni HAM TUZATADI, faqat o'lchamaydi. Filtr ANIQLIK
      hisobotida bor (`accuracy_report`) va u boshqa savolga javob
      beradi.
    """


@dataclass(frozen=True, slots=True)
class SlotRow:
    """`stall_slot_occupancy` ga yoziladigan BITTA qator."""

    stall_id: UUID
    slot_time: time
    verdict: str
    resolution_source: str
    winning_occupancy_event_id: UUID | None
    """`occupied` bo'lganda MAJBURIY, aks holda `None`.

    ⛔ YANGI MEXANIZM EMAS: `CHECK ((verdict='occupied') =
       (winning_occupancy_event_id IS NOT NULL))` buni sxemada
       majburlaydi, FK esa dalilni `occupancy_events` orqali
       `snapshots (id, is_billable)` ga ULAYDI. Ya'ni yaroqsiz kadr
       bandlik hisobiga TRANZITIV ravishda yeta olmaydi (D-21).
    """


@dataclass(frozen=True, slots=True)
class OccupancyDaySummary:
    """Kunlik xulosa — BESH hisoblagich va ularning YIG'INDI GUVOHI.

    ⛔ `stalls` OLTINCHI HISOBLAGICH EMAS: u to'rt o'zaro inkor
       bo'lakning yig'indisi bilan solishtiriladigan MUSTAQIL son
       (UI-SPEC §11.4 dagi «Rasta 300 ta»). Nomuvofiqlik shu bilan
       darhol ko'rinadi — o'quvchi qo'lda jamlashi shart emas.
    """

    occupied: int
    empty: int
    default_empty: int
    no_coverage: int
    human_confirmed: int
    stalls: int


@dataclass(frozen=True, slots=True)
class StallDay:
    """Bitta rastaning kunlik holati — ro'yxat qatori (UI-SPEC §11.7)."""

    stall_id: UUID
    stall_code: str
    zone_name: str
    bucket: str
    """`occupied` / `empty` / `default_empty` / `no_coverage` — `_PER_STALL_CTE` dan.

    ⛔ XULOSADAGI HISOBLAGICH BILAN BIR MANBADAN: ro'yxat va xulosa bir
       xil `CASE` dan chiqadi, ya'ni ular ajralib keta olmaydi.
    """
    slots: int
    occupied_slots: int
    human_confirmed: bool


@dataclass(frozen=True, slots=True)
class RoundStatus:
    """Kunlik ko'r audit turi — o'lchovning O'ZI haqidagi ma'lumot.

    ⛔ URUG' YO'Q va `decision_ms` XOM qiymatlar bo'lib keladi: «tez
       qaror» sanog'i `accuracy_report.is_fast_decision()` bilan, YAGONA
       joyda hisoblanadi (`_ROUND_STATUS` docstringi).
    """

    round_no: int
    drawn_at: datetime
    frame_size: int
    drawn: int
    answered: int
    dont_know: int
    decision_ms: tuple[int, ...]

    @property
    def unanswered(self) -> int:
        """⛔ JAVOBSIZLAR — NAMUNADAN CHIQMAYDI, SANALADI (§C.8, 4-dushman)."""
        return self.drawn - self.answered


# ===========================================================================
# SO'ROVLAR
# ===========================================================================

_ZONE_OUTCOMES = text(
    """
    SELECT cz.stall_id      AS stall_id,
           ev.slot_time     AS slot_time,
           ev.id            AS event_id,
           ev.verdict       AS event_verdict,
           zr.human_verdict AS review_verdict
      FROM occupancy_events ev
      JOIN camera_zones cz
        ON cz.market_id = ev.market_id
       AND cz.id = ev.camera_zone_id
      LEFT JOIN review_assignments ra
        ON ra.market_id = ev.market_id
       AND ra.occupancy_event_id = ev.id
      LEFT JOIN zone_reviews zr
        ON zr.market_id = ra.market_id
       AND zr.review_assignment_id = ra.id
     WHERE ev.market_id = :market_id
       AND ev.business_date = :business_date
     ORDER BY cz.stall_id, ev.slot_time, ev.camera_zone_id, ev.id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
)
"""Shu kunning BARCHA zona-hodisalari va ularga yozilgan inson javobi.

=============================================================================
⚠ ZONA ARXIVLANGAN BO'LSA HAM QATOR CHIQADI (`cz.is_active` filtri YO'Q).

Hodisa yozilgan paytda zona FAOL edi — `detect` faqat faol zonalarni
ko'radi (05-08). Keyin zona qayta chizilsa (D-07: eski versiya
`is_active = false` bo'ladi) filtr o'sha kunning dalilini RETROAKTIV
ravishda yo'q qilardi: kecha o'lchangan rasta bugun «qamrovsiz» bo'lib
qolardi va hisobot O'TMISHNI o'zgartirardi.

⚠ TARTIB DETERMINISTIK VA U KERAK: g'olib zona `aggregate_stall_slot()`
  ning chiqishi bo'yicha topiladi, ya'ni bir xil kirish har safar bir
  xil `winning_occupancy_event_id` berishi shart. `ORDER BY` bo'lmasa
  qayta hisoblash o'sha rastaga BOSHQA dalil kadrini biriktirishi mumkin
  edi — idempotentlik testi buni ko'rardi-yu, sabab tasodifiy bo'lardi.

⚠ `snapshot_is_billable` FILTRI YO'Q va u KERAK EMAS: `CHECK
  (snapshot_is_billable)` (05-05) yaroqsiz kadrli hodisaning MAVJUD
  bo'lishini imkonsiz qiladi. Ikkinchi, kod tomondagi nusxa kafolatni
  ikkiga bo'lardi.
=============================================================================
"""

_ACTIVE_STALL_IDS = text(
    """
    SELECT s.id AS stall_id
      FROM stalls s
     WHERE s.market_id = :market_id
       AND s.status = :status
     ORDER BY s.id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("status", type_=Text()),
)
"""Materializatsiya qamraydigan rastalar — FAQAT `active`.

⚠ `closed`/`maintenance` rastalar ATAYIN chetda: 2-fazaning A4 qarori
  bo'yicha ularga 6-fazada hisob YOZILMAYDI, ya'ni ularni `no_coverage`
  sifatida materializatsiya qilish «qamrovsiz rasta» sonini yopiq
  rastalar bilan shishirardi va direktor mavjud bo'lmagan muammoni
  quvlardi.
"""

_DAY_SLOT_TIMES = text(
    """
    SELECT DISTINCT sn.slot_time AS slot_time
      FROM snapshots sn
     WHERE sn.market_id = :market_id
       AND sn.business_date = :business_date
     ORDER BY sn.slot_time
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
)
"""Kunning slotlari — `snapshots` DAN, `occupancy_events` DAN EMAS.

=============================================================================
⛔⛔ FARQ D-22 NING O'ZI VA U JIM NOSOZLIKNI YOPADI.

`occupancy_events` dan olish tabiiy ko'rinadi va aynan shu holatni
yo'qotardi: kamera qorong'i bo'lgan (`quality_verdict <> 'ok'`) yoki
birorta zona chizilmagan slotda HODISA YOZILMAYDI (05-08 ning ikkala
sababi ham xato emas). O'sha slot butunlay g'oyib bo'lardi — ya'ni
«hech kim ko'rmagan» slot hisobotda UMUMAN ko'rinmasdi, `no_coverage`
esa nol bo'lib turardi.

Kadr olingan slot esa HAR DOIM `snapshots` da bor — sifati yaroqsiz
bo'lsa ham. Shuning uchun doira SHUNDAN quriladi.

⚠ KADR UMUMAN OLINMAGAN KUN 0 SLOT BERADI va bu KUTILGAN: bunday kun
  4-fazaning `alert_events` i orqali ALLAQACHON ko'rinadi (`audit_draw`
  ning bo'sh doira qarori bilan bir xil mulohaza) — ikkinchi signal
  kerak emas.
=============================================================================
"""

_MATERIALIZE_SLOT = text(
    """
    INSERT INTO stall_slot_occupancy
        (market_id, stall_id, business_date, slot_time,
         verdict, resolution_source, winning_occupancy_event_id)
    VALUES
        (:market_id, :stall_id, :business_date, :slot_time,
         :verdict, :resolution_source, :winning_occupancy_event_id)
    ON CONFLICT (market_id, stall_id, business_date, slot_time)
    DO UPDATE SET verdict = EXCLUDED.verdict,
                  resolution_source = EXCLUDED.resolution_source,
                  winning_occupancy_event_id = EXCLUDED.winning_occupancy_event_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("stall_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
    bindparam("slot_time", type_=Time()),
    bindparam("verdict", type_=Text()),
    bindparam("resolution_source", type_=Text()),
    bindparam("winning_occupancy_event_id", type_=_UUID),
)
"""Idempotent materializatsiya — `DO UPDATE`, `DO NOTHING` EMAS.

=============================================================================
⚠ IKKI SHAKLNING FARQI O'LCHANADIGAN VA U `occupancy_events` DAGIDAN
  TESKARI.

`occupancy_events` — DALIL, ya'ni u `append-only` va u yerda
`DO NOTHING` yagona to'g'ri shakl (05-08). `stall_slot_occupancy` esa
DALIL EMAS, u HOSILA: nazoratchi kechagi kunga javob yozsa, kunning
materializatsiyasi o'sha javobni AKS ETTIRISHI shart. `DO NOTHING`
birinchi hisobni MUZLATARDI va inson javobi hisobotga hech qachon
yetib bormasdi (D-15 buzilardi).

⛔ `created_at` YANGILANMAYDI: qator qachon TUG'ILGANI o'zgarmaydi.
   `updated_at` esa jadvalda umuman yo'q (05-05) — qayta hisoblash
   kunlik jobning odatiy ishi, «kimdir tahrirladi» emas.

⚠ QATOR HECH QACHON O'CHIRILMAYDI. Rasta keyin `closed` ga o'tsa uning
  o'tgan kunlari joyida qoladi: o'chirish o'tmishdagi hisobotni
  o'zgartirardi va 6-fazaning dalil havolasini uzardi.
=============================================================================
"""

_PER_STALL_CTE = """
    per_stall AS (
        SELECT sso.stall_id,
               count(*)                                        AS slots,
               count(*) FILTER (WHERE sso.verdict = :occupied)  AS occupied_slots,
               bool_or(sso.resolution_source = :human)          AS human_confirmed,
               CASE
                   WHEN bool_or(sso.verdict = :occupied)
                        THEN :occupied
                   WHEN NOT bool_or(sso.verdict <> :no_coverage)
                        THEN :no_coverage
                   WHEN bool_or(sso.resolution_source IN (:ai, :human))
                        THEN :empty
                   ELSE :default_empty
               END                                              AS bucket
          FROM stall_slot_occupancy sso
         WHERE sso.market_id = :market_id
           AND sso.business_date = :business_date
         GROUP BY sso.stall_id
    )
"""
"""RASTA x KUN bo'lagi — VA U AYNAN BIR MARTA YOZILGAN.

=============================================================================
⛔⛔ BITTA `CASE`, IKKI ISTE'MOLCHI (`_DAY_SUMMARY` va `_DAY_STALLS`).

Xulosadagi hisoblagich bilan ro'yxatdagi badge BIR XIL savolga javob
beradi: «bu rasta bugun qaysi bo'lakda?». Ikki nusxa yozilganda ular
sekin-asta ajralib ketardi va nosozlik ENG YOMON shaklda ko'rinardi —
xulosada «Bo'sh 68», ro'yxatda esa 69 ta bo'sh rasta, ikkalasi ham
xatosiz.

BO'LAK QOIDASI ZONA -> SLOT QOIDASINING AYNAN O'ZI:

    band bo'lsa                       -> `occupied`
    birorta sloti qamralmagan bo'lsa  -> `no_coverage`
    DALIL bo'lsa (`ai`/`human`)       -> `empty`
    aks holda                         -> `default_empty`

⚠ TARTIB MAJBURIY: `occupied` birinchi (D-20), `no_coverage` ikkinchi.
  `no_coverage` ni yuqoriga ko'tarish qamrovsiz SLOTI bor band rastani
  «qamrovsiz» qilib ko'rsatardi.

⚠ INSON «aniq ayta olmadi» degan slot (`verdict='uncertain'`,
  `resolution_source='human'`) `empty` bo'lagiga tushadi va
  `human_confirmed` ga ham kiradi — modul docstringidagi bandning
  mexanizmi aynan shu `CASE` da.
=============================================================================
"""

# ⚠ `S608` SHU IKKI SO'ROVDA O'CHIRILGAN VA SABAB TOR (`audit_draw.py:232`
#   bilan aynan bir xil): f-string ga tushadigan YAGONA qiymat — shu
#   moduldagi SOBIT `_PER_STALL_CTE` konstantasi. Tashqi kirish f-string
#   ga umuman kelmaydi, har bir qiymat `bindparam(...)` orqali TIPLANGAN
#   parametr bo'lib ketadi.
_DAY_SUMMARY = text(
    f"""
    WITH {_PER_STALL_CTE}
    SELECT
        count(*) FILTER (WHERE bucket = :occupied)      AS occupied,
        count(*) FILTER (WHERE bucket = :empty)         AS empty,
        count(*) FILTER (WHERE bucket = :default_empty) AS default_empty,
        count(*) FILTER (WHERE bucket = :no_coverage)   AS no_coverage,
        count(*) FILTER (WHERE human_confirmed)         AS human_confirmed,
        count(*)                                        AS stalls
      FROM per_stall
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
    bindparam("occupied", type_=Text()),
    bindparam("empty", type_=Text()),
    bindparam("default_empty", type_=Text()),
    bindparam("no_coverage", type_=Text()),
    bindparam("ai", type_=Text()),
    bindparam("human", type_=Text()),
)
"""Besh hisoblagich — TO'RTTASI o'zaro inkor, BESHINCHISI kesishuvchi.

⚠ TASHQI `SELECT` AGREGAT, ya'ni `per_stall` BO'SH bo'lganda ham AYNAN
  BITTA qator qaytadi va beshala son `0` bo'ladi. `GROUP BY` qo'yilsa
  bo'sh kun UMUMAN qator bermasdi va chaqiruvchi «hisobot yo'q» bilan
  «hammasi nol» ni ajrata olmasdi — modul docstringidagi «nol —
  NATIJA» qoidasi aynan shu yerda mexanik bo'ladi.

⚠ BO'LAK `_PER_STALL_CTE` DAN KELADI — bu yerda qayta hisoblanmaydi.
"""

_DAY_STALLS = text(
    f"""
    WITH {_PER_STALL_CTE}
    SELECT s.id          AS stall_id,
           s.code        AS stall_code,
           z.name        AS zone_name,
           ps.bucket     AS bucket,
           ps.slots      AS slots,
           ps.occupied_slots AS occupied_slots,
           ps.human_confirmed AS human_confirmed
      FROM per_stall ps
      JOIN stalls s
        ON s.market_id = :market_id
       AND s.id = ps.stall_id
      JOIN zones z
        ON z.market_id = s.market_id
       AND z.id = s.zone_id
     ORDER BY z.name, s.code_sort, s.id
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
    bindparam("occupied", type_=Text()),
    bindparam("empty", type_=Text()),
    bindparam("default_empty", type_=Text()),
    bindparam("no_coverage", type_=Text()),
    bindparam("ai", type_=Text()),
    bindparam("human", type_=Text()),
)
"""Rastalar ro'yxati — xulosadagi bo'lak bilan AYNAN BIR MANBADAN.

⚠ TARTIB `/stalls` BILAN BIR XIL (UI-SPEC §11.7): bozor zonasi ->
  `code_sort`. `code_sort` DB tomonda hisoblanadi (2-faza), ya'ni ro'yxat
  va xarita bir xil tartibda chiqadi. `s.id` — uchinchi, DETERMINIZM
  uchun: bir zonada bir xil `code_sort` bo'lishi mumkin emas, lekin
  tartib butunlay aniq bo'lishi sahifalash kelgan kunda ham kerak.
"""

_ACCURACY_ROWS = text(
    """
    SELECT ra.purpose      AS purpose,
           ra.queue_kind   AS queue_kind,
           ev.verdict      AS system_verdict,
           zr.human_verdict AS human_verdict
      FROM review_assignments ra
      JOIN occupancy_events ev
        ON ev.market_id = ra.market_id
       AND ev.id = ra.occupancy_event_id
      LEFT JOIN zone_reviews zr
        ON zr.market_id = ra.market_id
       AND zr.review_assignment_id = ra.id
     WHERE ra.market_id = :market_id
       AND ev.business_date >= :from_date
       AND ev.business_date <= :to_date
     ORDER BY ev.business_date, ra.id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("from_date", type_=Date()),
    bindparam("to_date", type_=Date()),
)
"""Davr ichidagi BARCHA topshiriqlar — javobsizlari HAM.

=============================================================================
⛔⛔ SO'ROVDA `purpose`/`queue_kind` FILTRI ATAYIN YO'Q.

Filtr `accuracy_report()` da yashaydi va u YAGONA joyda bo'lishi shart:
SQL ga ko'chirilsa kafolat IKKI joyda bo'lardi va sof funksiyaning 120
qatorlik testi mahsulot yo'lini qo'riqlamay qolardi (bugungi filtr
so'rovda bo'lardi, test esa funksiyani o'lchardi).

⛔ `LEFT JOIN` — JAVOBSIZ BANDLAR CHIQADI (§C.8, 4-dushman). `INNER JOIN`
   yozish eng tabiiy qisqartma va u aynan qisman bajarilgan auditni
   TO'LIQ ko'rsatardi: javobsizlar so'rov darajasida yo'qolib, hisobot
   ularni sanay olmasdi.

⚠ DAVR `occupancy_events.business_date` BO'YICHA, `zone_reviews.
  decided_at` BO'YICHA EMAS: hisobot «shu KUNLARDAGI bandlik qanchalik
  to'g'ri o'lchandi?» degan savolga javob beradi, «nazoratchi shu
  kunlarda nima qildi?» degan savolga emas (u byudjet savoli, 05-10).
=============================================================================
"""

_ROUND_STATUS = text(
    """
    SELECT ar.round_no      AS round_no,
           ar.drawn_at      AS drawn_at,
           ar.frame_size    AS frame_size,
           count(ra.id)     AS drawn,
           count(zr.id)     AS answered,
           count(*) FILTER (WHERE zr.human_verdict = :uncertain) AS dont_know,
           array_remove(array_agg(zr.decision_ms), NULL) AS decision_ms
      FROM audit_rounds ar
      LEFT JOIN review_assignments ra
        ON ra.market_id = ar.market_id
       AND ra.audit_round_id = ar.id
      LEFT JOIN zone_reviews zr
        ON zr.market_id = ra.market_id
       AND zr.review_assignment_id = ra.id
     WHERE ar.market_id = :market_id
       AND ar.business_date = :business_date
     GROUP BY ar.round_no, ar.drawn_at, ar.frame_size
     ORDER BY ar.round_no
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
    bindparam("uncertain", type_=Text()),
)
"""Kunlik ko'r audit turining holati — O'LCHOVNING O'ZINI ko'rsatadi.

⛔ URUG' QAYTARILMAYDI VA U USTUN SIFATIDA UMUMAN MAVJUD EMAS
   (`audit_rounds` da bunday ustun yo'q — 05-11). Ko'rsatish «tanlash
   mumkin» degan taassurot berardi.

⛔ «TEZ QAROR» SANOG'I SO'ROVDA HISOBLANMAYDI — xom `decision_ms`
   qiymatlari qaytadi va sanoq `accuracy_report.is_fast_decision()` bilan
   qilinadi. Chegara (2000 ms) VA `NULL` qoidasi shu bilan AYNAN BITTA
   joyda qoladi; SQL ga ko'chirilsa ikkinchi nusxa tug'ilardi va
   `NULL` ni «tez» deb sanaydigan variant jimgina paydo bo'lishi mumkin
   edi.

⚠ `array_remove(..., NULL)` — `NULL` lar OLIB TASHLANADI, `0` GA
  AYLANTIRILMAYDI: nol millisekund «juda tez», `NULL` esa
  «O'LCHANMAGAN».

⚠ `answered` `count(zr.id)` bilan sanaladi (`count(*)` EMAS): `LEFT
  JOIN` da javobsiz topshiriq ham qator beradi va `count(*)` ularni
  «javob berilgan» deb sanardi.
"""


class OccupancyRepository(TenantScopedRepository):
    """Bandlik materializatsiyasi va hisobot yuzasi ustidagi yagona DB yuzasi.

    ⛔ O'CHIRISH METODI YOZILMAGAN va bu STRUKTURA
       (`review_repo`/`capture_repo` bilan bir xil qaror): kunlik
       materializatsiya `ON CONFLICT DO UPDATE` bilan qayta hisoblanadi,
       ya'ni «avval o'chiraman, keyin yozaman» yo'liga EHTIYOJ YO'Q. Metod
       mavjud bo'lsa keyingi tahrirlovchi uni «tozalash uchun» chaqirardi
       va o'sha chaqiruv o'tgan kunning hisobotini yo'q qilardi.
    """

    def __init__(self, session: AsyncSession, market_id: UUID) -> None:
        super().__init__(session, market_id)

    # ------------------------------------------------------------------
    # 1. Kun yopilishining KIRISHI
    # ------------------------------------------------------------------

    async def zone_outcomes(self, business_date: date) -> list[ZoneOutcome]:
        """Shu kunning barcha zona-hodisalari + ularga yozilgan inson javobi."""
        result = await self.session.execute(
            _ZONE_OUTCOMES, {"market_id": self.market_id, "business_date": business_date}
        )
        return [
            ZoneOutcome(
                stall_id=row["stall_id"],
                slot_time=row["slot_time"],
                event_id=row["event_id"],
                event_verdict=row["event_verdict"],
                review_verdict=row["review_verdict"],
            )
            for row in result.mappings()
        ]

    async def active_stall_ids(self) -> list[UUID]:
        """Materializatsiya qamraydigan rastalar (`_ACTIVE_STALL_IDS` docstringi)."""
        result = await self.session.execute(
            _ACTIVE_STALL_IDS, {"market_id": self.market_id, "status": StallStatus.ACTIVE.value}
        )
        return [row.stall_id for row in result]

    async def day_slot_times(self, business_date: date) -> list[time]:
        """Kunning slotlari — `snapshots` dan (`_DAY_SLOT_TIMES` docstringi)."""
        result = await self.session.execute(
            _DAY_SLOT_TIMES, {"market_id": self.market_id, "business_date": business_date}
        )
        return [row.slot_time for row in result]

    # ------------------------------------------------------------------
    # 2. Kun yopilishining CHIQISHI
    # ------------------------------------------------------------------

    async def materialize(self, business_date: date, rows: Sequence[SlotRow]) -> int:
        """`stall_slot_occupancy` ga yozadi — idempotent (`_MATERIALIZE_SLOT`).

        Returns:
            Yozilgan (yoki yangilangan) qatorlar soni — kirish uzunligi.
            `ON CONFLICT DO UPDATE` da `rowcount` yangi va yangilangan
            qatorni AJRATMAYDI, ya'ni undan «nechta yangi qator» degan
            savolga javob CHIQMAYDI va uni qaytarish yolg'on aniqlik
            bo'lardi.
        """
        if not rows:
            return 0

        await self.session.execute(
            _MATERIALIZE_SLOT,
            [
                {
                    "market_id": self.market_id,
                    "stall_id": row.stall_id,
                    "business_date": business_date,
                    "slot_time": row.slot_time,
                    "verdict": row.verdict,
                    "resolution_source": row.resolution_source,
                    "winning_occupancy_event_id": row.winning_occupancy_event_id,
                }
                for row in rows
            ],
        )
        return len(rows)

    # ------------------------------------------------------------------
    # 3. O'QISH TOMONI
    # ------------------------------------------------------------------

    def _bucket_params(self, business_date: date) -> dict[str, object]:
        """`_PER_STALL_CTE` ning parametrlari — IKKALA so'rov uchun BIR marta.

        ⚠ Qiymatlar ENUM DAN hosila: literal yozilganda `CASE` jimgina
          birorta shoxga tushmay qolardi va butun bo'lak `default_empty`
          bo'lardi — hech qanday xatosiz.
        """
        return {
            "market_id": self.market_id,
            "business_date": business_date,
            "occupied": _OCCUPIED,
            "empty": OccupancyVerdict.EMPTY.value,
            "default_empty": ResolutionSource.DEFAULT_EMPTY.value,
            "no_coverage": ResolutionSource.NO_COVERAGE.value,
            "ai": ResolutionSource.AI.value,
            "human": ResolutionSource.HUMAN.value,
        }

    async def day_summary(self, business_date: date) -> OccupancyDaySummary:
        """Besh hisoblagich — NOL bo'lganda ham beshalasi qaytadi."""
        result = await self.session.execute(_DAY_SUMMARY, self._bucket_params(business_date))
        row = result.mappings().one()
        return OccupancyDaySummary(
            occupied=int(row["occupied"]),
            empty=int(row["empty"]),
            default_empty=int(row["default_empty"]),
            no_coverage=int(row["no_coverage"]),
            human_confirmed=int(row["human_confirmed"]),
            stalls=int(row["stalls"]),
        )

    async def day_stalls(self, business_date: date) -> list[StallDay]:
        """Rastalar ro'yxati — xulosadagi bo'lak bilan BIR MANBADAN."""
        result = await self.session.execute(_DAY_STALLS, self._bucket_params(business_date))
        return [
            StallDay(
                stall_id=row["stall_id"],
                stall_code=row["stall_code"],
                zone_name=row["zone_name"],
                bucket=row["bucket"],
                slots=int(row["slots"]),
                occupied_slots=int(row["occupied_slots"]),
                human_confirmed=bool(row["human_confirmed"]),
            )
            for row in result.mappings()
        ]

    async def accuracy_rows(self, from_date: date, to_date: date) -> list[AccuracyRow]:
        """Davr ichidagi BARCHA topshiriqlar — filtrsiz (`_ACCURACY_ROWS`)."""
        result = await self.session.execute(
            _ACCURACY_ROWS,
            {"market_id": self.market_id, "from_date": from_date, "to_date": to_date},
        )
        return [
            AccuracyRow(
                purpose=row["purpose"],
                queue_kind=row["queue_kind"],
                system_verdict=row["system_verdict"],
                human_verdict=row["human_verdict"],
            )
            for row in result.mappings()
        ]

    async def round_status(self, business_date: date) -> RoundStatus | None:
        """Shu kunning ko'r audit turi — tortilmagan bo'lsa `None`.

        ⚠ `None` — «namuna TORTILMAGAN», «hammasi bajarildi» EMAS
          (`review_repo._HAS_ANY_ROUND` ning aynan farqi). Chaqiruvchi
          ikkalasini ajratib ko'rsatishi shart.
        """
        result = await self.session.execute(
            _ROUND_STATUS,
            {
                "market_id": self.market_id,
                "business_date": business_date,
                "uncertain": OccupancyVerdict.UNCERTAIN.value,
            },
        )
        row = result.mappings().first()
        if row is None:
            return None
        return RoundStatus(
            round_no=int(row["round_no"]),
            drawn_at=row["drawn_at"],
            frame_size=int(row["frame_size"]),
            drawn=int(row["drawn"]),
            answered=int(row["answered"]),
            dont_know=int(row["dont_know"]),
            decision_ms=tuple(int(value) for value in row["decision_ms"]),
        )
