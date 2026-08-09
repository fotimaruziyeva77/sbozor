"""Ko'r audit namunasi — HOSILA URUG', MUZLATILGAN DOIRA va 70/30 (AI-04, D-17).

=============================================================================
BU MODUL — MAHSULOTNING YAGONA XOLIS O'LCHOV ASBOBI.

Agar u noto'g'ri qurilsa, «aniqlik 94%» degan raqam chiqadi, u chiroyli
bo'ladi, u yaxshilanib boradi — VA U SOXTA. Bu 4-fazadagi «bo'sh katak»
muammosidan jiddiyroq, chunki u JIMROQ: buzilgan UI ko'rinadigan yolg'on
aytadi, buzilgan o'lchov esa ko'rinmaydigan yolg'on aytadi.
=============================================================================

URUG' TANLANMAYDI, HOSILA QILINADI.

    seed = sha256(market_id || '|' || business_date || '|' || round_no)

⛔ URUG' USTUN SIFATIDA SAQLANMAYDI (`AuditRound` klass docstringi):
   saqlangan qiymat o'zgartirilishi mumkin bo'lardi, hosila qiymat esa —
   yo'q. «Bu turda xato ko'p chiqdi, boshqa urug' bilan qaytadan
   tortaman» degan HARAKATNING O'ZI mumkin emas: uni bajarish uchun
   kunni yoki bozorni o'zgartirish kerak bo'lardi.

⚠ URUG' SQL DA HOSIL QILINADI, ILOVADA EMAS. `05-01` ning W0-3 zondi
  AYNAN shu yo'lni HAQIQIY `postgres:18.4` da o'lchagan
  (`AUDIT_SEED_SHA256_SUPPORTED = true`, `PGCRYPTO_ABSENT = true`), ya'ni
  yadro `sha256(bytea)` kengaytmasiz ishlaydi va `0018` yangi kengaytma
  talab qilmaydi. Ikkinchi (Python) nusxa ikki hisoblash manbai bo'lardi;
  MUSTAQIL qayta hisoblash esa TESTDA, `hashlib` bilan — ya'ni
  «qayta chiqariladi» da'vosi bir kod yo'lining o'zini takrorlab
  tasdiqlamaydi.

⚠ RAD ETILGAN MUQOBILLARNING NOMLARI BU FAYLDA UMUMAN YOZILMAYDI —
  na kodda, na izohda (03-07 da o'lchangan qoida: skanerlanadigan faylning
  izohidagi taqiqlangan token darvozani o'ziga qarshi qo'yadi va yagona
  «tuzatish» yo'li darvozani BO'SHATISH bo'lardi). Sabablar
  `tests/tenancy/test_audit_seed_probe.py` va
  `tests/integration/test_blind_audit.py` da. Bu fayl faqat IJOBIY
  shaklda yozadi: «tartib hosila urug'dan olingan `sha256` bo'yicha».

=============================================================================
DOIRA (FRAME) MUZLATILADI — VA U ENG QIYIN HOLATLARNI HAM QAMRAYDI.

Doira = shu bozorning shu KUNDAGI BARCHA `is_billable` zona-hodisalari:
`occupied`, `empty` VA `uncertain`. «Faqat ishonchli javoblarni
tekshiraylik» degan qisqartma o'lchovni ma'nosiz qiladi — model IKKILANGAN
holatlar o'lchovdan chiqib ketardi va aniqlik SUN'IY ko'tarilardi
(05-RESEARCH §C.8, 2-dushman).

Uch fakt `audit_rounds` qatorida muzlatiladi va ularning hammasi KEYIN
hisoblab bo'lmaydigan narsa:

    frame_size           — tortish PAYTIDA nechta nomzod bor edi
    frame_predicate_hash — nomzodlarni QAYSI shart tanladi
    drawn_at             — qachon tortilgani

=============================================================================
⛔⛔ TARTIB MAJBURIY VA U SHU MODULDA MAJBURLANADI (§C.8.3).

`daily_queue_tick()` AVVAL ko'r audit namunasini tortadi, KEYIN noaniq
navbatni quradi. Teskari tartibda `UNIQUE (occupancy_event_id)` audit
doirasidan aynan `uncertain` hodisalarni chiqarib tashlardi.

⚠⚠ VA AYNAN SHU SABABDAN IKKALASI BITTA JOB VA BITTA CRON:

    Noaniq navbatni SOAT SAYIN qurish o'z-o'zicha oqilona ko'rinadi
    (bandlar kun bo'yi qo'shiladi). Lekin o'shanda kun oxiriga borib
    BARCHA `uncertain` hodisalar allaqachon noaniq navbatda bo'lardi va
    ko'r audit namunasi ularni `ON CONFLICT DO NOTHING` bilan JIMGINA
    yo'qotardi — ya'ni cron JADVALI 2-dushmanni qaytadan ochardi va
    birorta test buni ko'rmasdi.

    Chaqiruv tartibini kod majburlaydi, CADENCE ni esa bitta job
    majburlaydi. Ikkalasi ham kerak.

⚠ TIK KUNNING OXIRGI SLOTIDAN KEYIN ISHLAYDI (`worker.py::QUEUE_TICK_CRON`).
  Kun o'rtasida tortilgan namuna faqat ERTALABKI slotlardan iborat
  bo'lardi va bu 2-dushmanning aynan o'zi («faqat kunduzgi slotlardan»).
  Nazoratchi kechagi navbatni bugun ko'radi — 05-10 ning byudjet qarori
  (`decided_at` bo'yicha sanash) aynan shuni nazarda tutgan.
=============================================================================

⚠ HAR BOZOR UCHUN ALOHIDA TRANZAKSIYA (§S-5, `discovery.py:170-205`).
  Bitta tranzaksiyada ikki bozor — tenant sizib chiqishining eng qisqa
  yo'li; qolaversa bitta bozordagi nosozlik qolganlarining namunasini ham
  yo'qotardi.

⚠ `taskiq` IMPORT QILINMAYDI (S-4, D-06) — bu modul sof `async def`.
"""

from __future__ import annotations

import hashlib
import math
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Final
from uuid import UUID

import structlog
from sbozor_core.enums import ActorKind, ReviewPurpose, ReviewQueueKind
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import Date, Integer, SmallInteger, Text, bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.exc import SQLAlchemyError

from app.jobs.retention import active_market_ids
from app.repositories.review_repo import ReviewRepository

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from datetime import date

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

log = structlog.get_logger(__name__)

__all__ = [
    "FIRST_ROUND_NO",
    "FRAME_PREDICATE",
    "FRAME_PREDICATE_HASH",
    "DrawResult",
    "MarketDraw",
    "QueueTickPolicy",
    "TickResult",
    "audit_draw",
    "daily_queue_tick",
    "eval_quota",
]


FIRST_ROUND_NO: Final[int] = 1
"""Kunlik doiraning raqami — VA U SHU YERDA QOTIRILGAN.

⛔ «KEYINGI OCHIQ RAQAM» HISOBLANMAYDI VA BU D-17.1 NING BUTUN MAZMUNI.

`uq_audit_rounds_market_id_business_date_round_no` ikkinchi turni
sxema darajasida MUMKIN qiladi (byudjet oshirilgan kun uchun), lekin
uni yozadigan KOD YO'LI mavjud emas: bu job bir kunda bir marta
ishlaydi va kun uchun tur allaqachon bo'lsa bozorni O'TKAZIB YUBORADI.

`COALESCE(max(round_no), 0) + 1` shakli sintaktik jihatdan bir satr
qisqaroq bo'lardi va aynan o'sha bir satr «namunani qayta tortish»
yo'lini ochardi: jobni ikkinchi marta ishga tushirish YANGI urug' bilan
YANGI namuna berardi (05-01 W0-3 ning 4-fakti — boshqa `round_no`
kesishuvsiz to'plam beradi). Shuning uchun raqam KONSTANTA.
"""

FRAME_PREDICATE: Final[str] = """
      FROM occupancy_events ev
     WHERE ev.market_id = :market_id
       AND ev.business_date = :business_date
       AND ev.snapshot_is_billable
"""
"""DOIRANI TA'RIFLAYDIGAN YAGONA SHART — hamma uch so'rov shundan quriladi.

⚠ `verdict` BO'YICHA FILTR YO'Q VA UNING YO'QLIGI — QARORNING O'ZI.
  `occupied`, `empty` va `uncertain` — uchalasi ham doirada. Model
  IKKILANGAN holatlarni chiqarib tashlash aniqlikni sun'iy ko'taradi va
  buni hech kim sezmasdi (modul docstringi, 2-dushman).

⚠ `ev.snapshot_is_billable` BUGUN HAR DOIM ROST (`CHECK (snapshot_is_
  billable)`, 05-05) va u SHUNGA QARAMAY YOZILGAN. Sabab ikkita:
  (a) doiraning ta'rifi «BARCHA `is_billable` zona-hodisalari» va ta'rif
  shartning O'ZIDA ko'rinishi kerak; (b) shart `FRAME_PREDICATE_HASH` ga
  kiradi, ya'ni u bir kun bo'shatilsa xesh O'ZGARADI va eski turlar
  boshqa shart bilan tortilganini KEYIN ham aniqlash mumkin bo'ladi.

⚠ MATNNING O'ZI XESHLANADI (`FRAME_PREDICATE_HASH`), ya'ni bu satrni
  tahrirlash — hujjatlashtiriladigan hodisa. Bo'shliq o'zgarishi ham
  xeshni o'zgartiradi va bu KUTILGAN xulq: «shart o'zgardimi?» degan
  savolga «yo'q, faqat formatlash» degan javob YO'Q — formatlash ham
  o'zgarish.
"""

FRAME_PREDICATE_HASH: Final[str] = hashlib.sha256(FRAME_PREDICATE.encode()).hexdigest()
"""`audit_rounds.frame_predicate_hash` — SHARTNING matnidan HOSILA.

Doira keyin jimgina toraysa (masalan `verdict <> 'uncertain'` qo'shilsa)
eski turlarning xeshi yangilaridan FARQ QILADI va «o'sha kunlar boshqa
qoida bilan tortilgan» degan fakt hisobotda ko'rinadi. Qadalgan belgi
(`tests/fixtures/occupancy_domain.AUDIT_FRAME_PREDICATE_HASH`) bu
xususiyatga ega emas edi va u ATAYIN seed uchun qoldirilgan.
"""

_UUID = PgUuid(as_uuid=True)

_FRAME_SIZE = text(f"SELECT count(*) AS frame_size {FRAME_PREDICATE}").bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
)
"""Doiradagi nomzodlar SONI — tortish paytida.

⚠ TENANT KONTEKSTI ICHIDA, `SECURITY DEFINER` funksiya orqali EMAS
  (`audit_draw()` docstringidagi deviatsiya bandi): son `INSERT` bilan
  BIR tranzaksiyada o'lchanadi, ya'ni «o'lchadim -> yozdim» orasida yangi
  hodisa kelib `frame_size` yolg'on bo'lib qola olmaydi.
"""

_OPEN_ROUND = text(
    """
    INSERT INTO audit_rounds
        (market_id, business_date, round_no, frame_size, frame_predicate_hash)
    SELECT :market_id, :business_date, :round_no, :frame_size, :frame_predicate_hash
     WHERE NOT EXISTS (
         SELECT 1
           FROM audit_rounds ar
          WHERE ar.market_id = :market_id
            AND ar.business_date = :business_date
     )
    RETURNING id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
    bindparam("round_no", type_=SmallInteger()),
    bindparam("frame_size", type_=Integer()),
    bindparam("frame_predicate_hash", type_=Text()),
)
"""Kunlik doirani OCHADI — yoki 0 qator qaytaradi (allaqachon ochilgan).

⛔ `NOT EXISTS` SHU YERDA VA U ISTISNO O'RNIGA EMAS, ISTISNODAN OLDIN.
   `uq_audit_rounds_market_id_business_date_round_no` ikkinchi urinishni
   baribir `23505` bilan rad etardi — lekin o'shanda job HAR TIKDA istisno
   ko'targan bo'lardi va jurnal shovqinga to'lardi. Shart uni tikdan OLDIN
   chiqarib tashlaydi, kafolat esa `UNIQUE` da QOLADI.

⚠ SHART `round_no` NI KO'RMAYDI — «shu kunda BIRORTA tur» deydi. Ya'ni
  ikkinchi tur bu yo'ldan `round_no` ni o'zgartirib ham o'ta olmaydi
  (`FIRST_ROUND_NO` docstringi).
"""

# ⚠ `S608` SHU SO'ROVDA O'CHIRILGAN VA SABAB TOR (`review_repo.py:231-237`
#   bilan aynan bir xil): f-string ga tushadigan YAGONA qiymat — shu
#   moduldagi SOBIT `FRAME_PREDICATE` konstantasi. Tashqi kirish f-string
#   ga umuman kelmaydi, har bir qiymat `bindparam(...)` orqali TIPLANGAN
#   parametr bo'lib ketadi.
_DRAW_SAMPLE = text(
    f"""
    WITH derived_seed AS (
        SELECT encode(
            sha256((
                (:market_id)::uuid::text || '|' ||
                to_char((:business_date)::date, 'YYYY-MM-DD') || '|' ||
                (:round_no)::int::text
            )::bytea),
            'hex'
        ) AS value
    ), sample AS (
        SELECT picked.id AS event_id, seed.value AS seed
          FROM derived_seed seed
         CROSS JOIN LATERAL (
            SELECT ev.id
              {FRAME_PREDICATE}
             ORDER BY sha256((ev.id::text || seed.value)::bytea)
             LIMIT :sample_size
         ) AS picked
    ), ranked AS (
        SELECT sample.event_id,
               count(*) OVER () AS drawn,
               row_number() OVER (
                   ORDER BY sha256((sample.event_id::text || sample.seed || '|purpose')::bytea)
               ) AS purpose_rank
          FROM sample
    )
    INSERT INTO review_assignments
        (market_id, occupancy_event_id, audit_round_id, queue_kind, purpose)
    SELECT :market_id,
           ranked.event_id,
           :round_id,
           :queue_kind,
           CASE
               WHEN ranked.purpose_rank
                    <= ceil((:eval_ratio)::text::numeric * ranked.drawn)
               THEN :eval
               ELSE :train
           END
      FROM ranked
    ON CONFLICT (occupancy_event_id) DO NOTHING
    RETURNING id, purpose
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
    bindparam("round_no", type_=SmallInteger()),
    bindparam("round_id", type_=_UUID),
    bindparam("queue_kind", type_=Text()),
    bindparam("eval", type_=Text()),
    bindparam("train", type_=Text()),
    bindparam("eval_ratio", type_=Text()),
    bindparam("sample_size", type_=Integer()),
)
"""Namunani tortadi va HAR BANDGA `purpose` ni O'SHA PAYTDA qo'yadi.

=============================================================================
UCH BOSQICH, UCHALASI HAM HOSILA URUG'DAN.

  1. `derived_seed` — urug'ning O'ZI. `(:market_id)::text` va
     `(:business_date)::text` AYNAN predikatga ketadigan qiymatlardan
     olinadi, ya'ni urug' bilan doira BIR MANBADAN chiqadi. Alohida matn
     parametrlari berilsa ular jimgina ajralib ketishi mumkin edi
     («urug' kechagi kun, doira bugungi kun»).

  2. `sample` — tartib `sha256((id || urug'))` bo'yicha va `LIMIT`.
     `LATERAL` MAJBURIY: `LIMIT` doirani KESISHI kerak, urug' bilan
     birlashtirilgan natijani emas.

  3. `ranked` — `purpose` uchun IKKINCHI, MUSTAQIL tartib
     (`... || '|purpose'`). Birinchi tartibni qayta ishlatish `eval`
     ulushini namunaning BOSHIGA yopishtirardi, ya'ni «birinchi
     tortilganlar baholanadi» degan tizimli bog'liqlik tug'ilardi.
=============================================================================

⛔ `purpose` — KVOTA, TANGA TASHLASH EMAS.

`ceil(eval_ratio * drawn)` aniq 70/30 beradi (30 banddan 21 tasi `eval`).
Har bandga MUSTAQIL «tanga» tashlash ham deterministik bo'lardi, lekin
natija Binomial(30, 0.7) bo'lib, standart chetlanishi ~2,5 band — ya'ni
kunlik nisbat 60% dan 80% gacha sakrardi va D-14 ning «QAT'IY nisbat»
talabi (05-RESEARCH §C.9) bajarilmasdi.

⚠⚠ KVOTA `numeric` DA HISOBLANADI, `float8` DA EMAS — VA DA'VONING
   SHAKLI O'LCHOV BILAN TORAYTIRILGAN.

   BUGUNGI standart nisbatda (0,70) ikkala arifmetika ham AYNAN bir xil
   javob beradi — bu o'lchandi (n = 1..200 uchun birorta farq yo'q), ya'ni
   `float8` bugun ZARAR KELTIRMAYDI va teskarisini yozish yolg'on bo'lardi.

   Da'vo NISBAT SOZLANADIGAN bo'lgani uchun kuchda: `review_blind_eval_
   ratio` (0, 1] oralig'idagi HAR QANDAY qiymatni qabul qiladi va IEEE754
   ularning bir qismida boshqa javob beradi — o'lchangan misollar:

       ceil(0.28 * 25)  -> float8: 8   numeric: 7
       ceil(0.55 * 100) -> float8: 56  numeric: 55

   Ya'ni sozlamani o'zgartirgan kun kvota JIMGINA bir band suriladi va
   hisobotdagi `eval` ulushi e'lon qilinganidan farq qilardi. Shuning
   uchun nisbat MATN sifatida keladi va `::text::numeric` bilan yechiladi:
   `float8` PostgreSQL tomonida UMUMAN paydo bo'lmaydi. `eval_quota()` —
   shu ifodaning Python jufti va u ham `Decimal(str(...))` dan yuradi.

⚠ ⛔ TIP KASTLARI (`::uuid`, `::date`, `::int`, `::text`) BEZAK EMAS.
   `asyncpg` parametr tipini SO'ROV KONTEKSTIDAN chiqaradi: kastsiz
   `SELECT $1` uni `text` deb baholab, `UUID` obyektini RAD ETARDI.
   Kast tipni PINLAYDI, ya'ni `bindparam(...)` dagi e'lon bilan bir
   yo'nalishda ishlaydi (`nvr_repo.py:29-41` da o'lchangan sinf).

⚠ `eval` FAQAT KO'R AUDITDAN KELISHI MUMKIN va buni sxema majburlaydi
  (`ck_review_assignments_eval_needs_blind_audit`, 05-05). Bu yerdagi
  `:queue_kind` har doim `blind_audit`, ya'ni ikki qatlam bir yo'nalishda
  ishlaydi.

⚠ `ON CONFLICT (occupancy_event_id) DO NOTHING` — hodisa ALLAQACHON
  boshqa navbatda bo'lsa. `RETURNING` HAQIQATAN yozilgan qatorlarni
  beradi, ya'ni yo'qotish SANALADI va `MarketDraw.skipped` da KO'RINADI.
  Jimgina qisqargan namuna — 4-dushmanning eng arzon shakli.

⚠ SO'ROV DOIRADAN NOMZODLARNI CHIQARIB TASHLAMAYDI («allaqachon
  navbatda» filtri YO'Q) va bu ATAYIN: filtr namunani doiradan qayta
  hisoblab bo'lmaydigan qilardi, ya'ni «qayta chiqariladi» da'vosi
  bazadagi navbat holatiga bog'lanib qolardi.
"""


def eval_quota(drawn: int, eval_ratio: float) -> int:
    """`eval` bandlarining SONI — `_DRAW_SAMPLE` dagi ifodaning Python jufti.

    ⚠ MAHSULOT YO'LIDA CHAQIRILMAYDI: kvota SQL da hisoblanadi va bu
      funksiya faqat chaqiruvchiga (jurnal, hisobot, test) o'sha sonni
      IKKINCHI marta yozmasdan berish uchun. Ikki nusxa yozilganda ular
      ajralib ketardi va nosozlik faqat hisobotda ko'rinardi.

    ⚠ `Decimal(str(...))` — SQL dagi `::text::numeric` NING AYNAN JUFTI.
      Bugungi standart nisbatda (0,70) `math.ceil(0.70 * n)` ham bir xil
      javob beradi; farq BOSHQA sozlangan nisbatlarda chiqadi
      (`ceil(0.28 * 25)`: `float` 8, `Decimal` 7). Ikki hisoblash yo'li
      HAR QANDAY nisbatda mos kelishi uchun ikkalasi ham o'nlik
      arifmetikada bo'lishi SHART (`_DRAW_SAMPLE` docstringi).
    """
    return math.ceil(Decimal(str(eval_ratio)) * drawn)


@dataclass(frozen=True, slots=True)
class MarketDraw:
    """Bitta bozorning tortish natijasi.

    ⛔ NAMUNANING O'ZI (identifikatorlar ro'yxati) BU TIPDA YO'Q va bu
       `ClaimedReview` dagi bilan bir xil qaror: chaqiruvchiga namunaning
       KIMLIGI kerak emas, faqat SONLAR kerak. Ro'yxat qaytarilsa u
       jurnalga, jurnaldan esa «qaysi rastalar baholanmoqda» degan
       oldindan ko'rish yuzasiga aylanardi.
    """

    market_id: UUID
    round_id: UUID | None
    """`None` — tur ochilmadi (doira bo'sh yoki tur allaqachon bor)."""
    frame_size: int
    drawn: int
    eval_count: int
    skipped: int
    """Namunaga tushgan, lekin ALLAQACHON navbatda bo'lgan bandlar soni.

    Nolga teng bo'lishi KUTILGAN holat (tik kun oxirida bir marta
    ishlaydi va ko'r audit noaniq navbatdan OLDIN tortiladi). Noldan
    farqli qiymat — cadence buzilganining YAGONA ko'rinadigan izi.
    """


@dataclass(slots=True)
class DrawResult:
    """Butun tortishning O'LCHANADIGAN natijasi.

    ⛔ NOL — NATIJA, uning yo'qligi emas (`SweepResult` bilan bir xil qoida).
    """

    markets: int = 0
    rounds: int = 0
    drawn: int = 0
    eval_count: int = 0
    train_count: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class QueueTickPolicy:
    """`Settings` -> tik argumentlari (`RetentionPolicy` bilan bir xil qaror).

    Job sozlamalar obyektining butun yuzasini KO'RMAYDI, ya'ni uni testda
    qurish bitta qatorga tushadi va `DATABASE_URL`/`JWT_SECRET` talab
    qilmaydi.
    """

    sample_size: int
    """Kunlik ko'r audit namunasi (D-13). `review_blind_daily_budget` dan."""
    eval_ratio: float
    """`eval` ulushi (D-14)."""
    uncertain_limit: int
    """Noaniq navbatga bir tikda qo'shiladigan YANGI bandlar soni."""
    midpoint: float
    """Noaniq oynaning o'rtasi — ustuvorlikning o'lchov nuqtasi."""


@dataclass(slots=True)
class TickResult:
    """Kunlik tikning natijasi — IKKI QADAM, TARTIBI MAJBURIY."""

    draw: DrawResult = field(default_factory=DrawResult)
    queued: int = 0
    """Noaniq navbatga YOZILGAN yangi bandlar soni."""
    errors: list[str] = field(default_factory=list)


@asynccontextmanager
async def _tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """`discovery.py::_system_transaction()` ning shu moduldagi jufti.

    ⚠ HAR BOZOR UCHUN YANGI TRANZAKSIYA VA YANGI KONTEKST. GUC'lar
      `SET LOCAL` bilan qo'yiladi, ya'ni `COMMIT` da tozalanadi.
    """
    # SIM117 — ichki blok TRANZAKSIYA chegarasi (`alerting.py:447`).
    async with sessionmaker() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=None,
                request_id=request_id,
                actor_kind=ActorKind.SYSTEM,
            )
            yield session


async def audit_draw(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    business_date: date,
    sample_size: int,
    eval_ratio: float,
) -> DrawResult:
    """Har faol bozor uchun kunlik ko'r audit namunasini tortadi.

    =======================================================================
    ⚠ BOZORLAR RO'YXATI `active_market_ids()` DAN, `audit_draw_due_
      markets()` DAN EMAS — VA BU REJADAN OG'ISH (deviatsiya, SUMMARY da).

    `0018` ning `SECURITY DEFINER` funksiyasi ikki narsani qiladi: bozorni
    tanlaydi va `frame_size` ni oldindan sanaydi. Ikkalasi ham bu yo'lda
    ISHLAMAYDI:

      1. Funksiya kunni `now()` dan oladi va uni ARGUMENT qilib bo'lmaydi.
         Bu job esa `business_date` ni argument sifatida oladi —
         `retention_daily(today=...)` va `daily_digest(business_date=...)`
         da o'rnatilgan qoida: mahsulot yo'li `business_today()` beradi,
         test esa AYNAN o'sha funksiyani boshqa kun bilan chaqiradi.
         Ikki YO'L yozish (bugun -> funksiya, boshqa kun -> so'rov)
         mahsulot yo'lini TESTSIZ qoldirardi.

      2. `frame_size` `INSERT` bilan BIR tranzaksiyada o'lchanishi kerak.
         Tashqarida o'lchangan son «o'lchadim -> yozdim» oynasida
         eskirardi va `audit_rounds` MUZLATILGAN dalil bo'lish o'rniga
         TAXMIN yozardi.

    `active_market_ids()` — `alert_sweep` va `retention_daily` ishlatadigan
    AYNAN o'sha yagona RLS-chetlab o'tuvchi yuza (`retention.py:347-368`),
    ya'ni yangi xavfsizlik yuzasi OCHILMAYDI.
    =======================================================================

    Args:
        business_date: doira qaysi kunning hodisalaridan quriladi.
        sample_size: kunlik namuna hajmi (D-13 — 30).
        eval_ratio: `eval` ulushi (D-14 — 0,70).

    Returns:
        `DrawResult` — sonlar va YUTILGAN xatolarning TURLARI.
    """
    request_id = f"job-audit-draw-{business_date.isoformat()}"
    result = DrawResult()

    try:
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        log.exception("audit_draw_market_list_failed")
        return result
    result.markets = len(market_ids)

    for market_id in market_ids:
        try:
            draw = await _draw_for_market(
                sessionmaker,
                market_id=market_id,
                request_id=request_id,
                business_date=business_date,
                sample_size=sample_size,
                eval_ratio=eval_ratio,
            )
        except SQLAlchemyError as exc:
            # Xatoning MATNI emas, TURI (`alerting.py::_swallow()` qoidasi).
            result.errors.append(f"audit_draw_failed:{type(exc).__name__}")
            log.warning("audit_draw_failed", market_id=str(market_id), error=type(exc).__name__)
            continue

        if draw.round_id is None:
            continue
        result.rounds += 1
        result.drawn += draw.drawn
        result.eval_count += draw.eval_count
        result.train_count += draw.drawn - draw.eval_count
        result.skipped += draw.skipped

    log.info(
        "audit_draw_done",
        business_date=business_date.isoformat(),
        markets=result.markets,
        rounds=result.rounds,
        drawn=result.drawn,
        eval_count=result.eval_count,
        train_count=result.train_count,
        skipped=result.skipped,
        errors=len(result.errors),
    )
    return result


async def _draw_for_market(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    business_date: date,
    sample_size: int,
    eval_ratio: float,
) -> MarketDraw:
    """Bitta bozorning doirasini ochadi va namunani tortadi — BIR tranzaksiyada.

    ⛔ UCHALA QADAM HAM BITTA TRANZAKSIYADA: doirani sanash, turni ochish
       va namunani yozish. Bo'lingan holatda ikkinchi jarayon oraliqda
       tur ochib, ikkalasi ham «men ochdim» deb namunani IKKI marta
       yozardi — `UNIQUE (occupancy_event_id)` ikkinchisini rad etardi-yu,
       birinchi turning `frame_size` i boshqa oniy holatdan olingan
       bo'lardi.
    """
    async with _tenant_session(sessionmaker, market_id=market_id, request_id=request_id) as session:
        params = {"market_id": market_id, "business_date": business_date}
        frame_size = int((await session.execute(_FRAME_SIZE, params)).scalar_one())

        if frame_size == 0:
            # ⚠ BO'SH KUNGA DOIRA TORTILMAYDI (`AUDIT_DRAW_DUE_MARKETS`
            #   docstringidagi birinchi shartning aynan o'zi): nomzodsiz
            #   tur `frame_size = 0` bilan yozilardi va hisobotda
            #   «tortildi, lekin hech nima chiqmadi» qatorlari to'planardi.
            #   Kadr olinmagan kun `alert_events` orqali ALLAQACHON
            #   ko'rinadi (4-faza) — ikkinchi signal kerak emas.
            log.info("audit_draw_empty_frame", market_id=str(market_id))
            return MarketDraw(market_id, None, 0, 0, 0, 0)

        round_row = (
            await session.execute(
                _OPEN_ROUND,
                {
                    **params,
                    "round_no": FIRST_ROUND_NO,
                    "frame_size": frame_size,
                    "frame_predicate_hash": FRAME_PREDICATE_HASH,
                },
            )
        ).first()
        if round_row is None:
            log.info("audit_draw_already_drawn", market_id=str(market_id))
            return MarketDraw(market_id, None, frame_size, 0, 0, 0)
        round_id = UUID(str(round_row.id))

        written = (
            await session.execute(
                _DRAW_SAMPLE,
                {
                    **params,
                    "round_no": FIRST_ROUND_NO,
                    "round_id": round_id,
                    "queue_kind": ReviewQueueKind.BLIND_AUDIT.value,
                    "eval": ReviewPurpose.EVAL.value,
                    "train": ReviewPurpose.TRAIN.value,
                    # ⚠ MATN — `_DRAW_SAMPLE` docstringidagi `numeric` bandi.
                    "eval_ratio": str(eval_ratio),
                    "sample_size": sample_size,
                },
            )
        ).all()

    drawn = len(written)
    eval_count = sum(1 for row in written if row.purpose == ReviewPurpose.EVAL.value)
    # Namuna doiraning KICHIGI bilan cheklanadi; undan kam yozilgan bo'lsa
    # farq `ON CONFLICT` da yo'qolgan bandlar (`_DRAW_SAMPLE` docstringi).
    skipped = min(sample_size, frame_size) - drawn
    if skipped:
        log.warning(
            "audit_draw_sample_shrank",
            market_id=str(market_id),
            skipped=skipped,
            drawn=drawn,
        )
    return MarketDraw(market_id, round_id, frame_size, drawn, eval_count, skipped)


async def daily_queue_tick(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    business_date: date,
    policy: QueueTickPolicy,
) -> TickResult:
    """⛔ AVVAL KO'R AUDIT NAMUNASI, KEYIN NOANIQ NAVBAT (§C.8.3).

    =======================================================================
    IKKI QADAMNING TARTIBI — SHU FUNKSIYANING YAGONA SABABI.

    Teskari tartibda `UNIQUE (occupancy_event_id)` audit doirasidan aynan
    `uncertain` hodisalarni chiqarib tashlardi: xolis namuna model
    IKKILANGAN holatlarsiz qolardi va o'lchangan aniqlik SUN'IY
    ko'tarilardi — eng qiyin holatlar o'lchovdan chiqib ketardi.

    ⚠ NOSOZLIK TARTIBNI BUZMAYDI: `audit_draw()` xatolarni bozor
      darajasida YUTADI va `DrawResult.errors` ga yozadi, ya'ni bir
      bozorning nosozligi qolganlarining namunasini ham, keyingi qadamni
      ham to'xtatmaydi. Lekin BUTUN birinchi qadam yiqilsa (bozorlar
      ro'yxati o'qilmadi) ikkinchi qadam BARIBIR ishlaydi va bu ATAYIN:
      noaniq navbatsiz kun nazoratchini butunlay ishsiz qoldirardi,
      holbuki o'sha kunning ko'r audit namunasi ertaga baribir
      tortilmaydi (kun o'tgan).
    =======================================================================
    """
    result = TickResult()
    result.draw = await audit_draw(
        sessionmaker,
        business_date=business_date,
        sample_size=policy.sample_size,
        eval_ratio=policy.eval_ratio,
    )
    result.queued = await _build_uncertain_queues(
        sessionmaker,
        business_date=business_date,
        limit=policy.uncertain_limit,
        midpoint=policy.midpoint,
        errors=result.errors,
    )
    log.info(
        "daily_queue_tick_done",
        business_date=business_date.isoformat(),
        drawn=result.draw.drawn,
        queued=result.queued,
        errors=len(result.errors) + len(result.draw.errors),
    )
    return result


async def _build_uncertain_queues(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    business_date: date,
    limit: int,
    midpoint: float,
    errors: list[str],
) -> int:
    """Har bozor uchun noaniq navbatni quradi — ALOHIDA tranzaksiyada."""
    request_id = f"job-uncertain-queue-{business_date.isoformat()}"
    try:
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError as exc:
        errors.append(f"uncertain_queue_market_list_failed:{type(exc).__name__}")
        log.exception("uncertain_queue_market_list_failed")
        return 0

    queued = 0
    for market_id in market_ids:
        try:
            async with _tenant_session(
                sessionmaker, market_id=market_id, request_id=request_id
            ) as session:
                repo = ReviewRepository(session, market_id, midpoint=midpoint)
                queued += await repo.build_uncertain_queue(business_date, limit=limit)
        except SQLAlchemyError as exc:
            errors.append(f"uncertain_queue_failed:{type(exc).__name__}")
            log.warning(
                "uncertain_queue_failed", market_id=str(market_id), error=type(exc).__name__
            )
    return queued
