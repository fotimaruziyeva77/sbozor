"""Nazoratchi navbati — qulflab olish, kunlik byudjet va OCHIQ TANLANGAN ustuvorlik (AI-03).

=============================================================================
USTUVORLIK IKKI MAQSAD ORASIDA TANLOV VA U SHU YERDA OCHIQ YOZILGAN.

    Mahsulot qiymati  -> ko'rilishi HISOB-KITOBNI o'zgartiradigan bandlar
                         (biriktirilgan sotuvchisi bor rasta)
    Trening qiymati   -> chegaraga eng yaqin `confidence` (uncertainty
                         sampling)

Tanlov: **avval billing ta'siri, ichida chegaraga yaqinlik** (05-RESEARCH
§C.9). Sabab mahsulotning va'dasida: patta to'g'ri yig'ilishi BIRLAMCHI,
trening ma'lumoti esa shundan kelib chiqadigan YON MAHSULOT. Teskari
tartib nazoratchining cheklangan diqqatini modelni yaxshilashga sarflab,
BUGUNGI hisobni noto'g'ri qoldirardi — va nosozlik hech qanday xato
xabari bermasdi, chunki navbat «to'liq bajarildi» bo'lib ko'rinardi.

⚠ TANLOV KODDA KO'RINADIGAN JOYDA: `_PRIORITY_ORDER` bitta konstanta va
  ikkala so'rov (navbat qurish va band olish) undan foydalanadi. Ikki
  nusxa yozilganda navbatga TUSHADIGAN bandlar bilan navbatdan
  OLINADIGAN bandlar boshqa tartibda saralanardi: kunlik chegara eng
  qimmat bandlarni kesib tashlab, nazoratchi esa ularni umuman
  ko'rmasdi.
=============================================================================

`FOR UPDATE ... SKIP LOCKED` — NIMANI QOPLAYDI VA NIMANI QOPLAMAYDI.

Qoplaydi: IKKI nazoratchi AYNI PAYTDA `next` so'rasa ikkalasi ham bir xil
bandni olmaydi — ikkinchisining tranzaksiyasi qulflangan qatorni
o'tkazib yuboradi (kutmaydi ham, xato ham bermaydi).

⛔ QOPLAMAYDI: qulf `COMMIT` da TUSHADI. Ya'ni band javobsiz qolsa,
   KEYINGI so'rov (o'sha yoki boshqa nazoratchining) uni QAYTA oladi. Bu
   NOSOZLIK EMAS, KUTILGAN XULQ va u UI-SPEC §4.5 ning aynan talabi:
   «Sahifa yangilansa — server o'sha bandni qaytaradi (javob yozilmagan
   bo'lsa) yoki KEYINGISINI (yozilgan bo'lsa)». URL'da identifikator
   yo'q, ya'ni sessiya holatining yagona manbai — SERVER.

   Demak ikki nazoratchining bitta bandga IKKI javob yozishiga qarshi
   yagona haqiqiy kafolat — `UNIQUE (review_assignment_id)` va u
   chaqiruvchida `409 review_already_answered` ga aylanadi. `SKIP LOCKED`
   o'sha poygani KAMAYTIRADI, YO'Q QILMAYDI. Bu farq shu yerda yozildi,
   chunki teskari tasavvur («qulf bor, demak 409 kerak emas») bir satrlik
   «soddalashtirish» bilan kafolatni butunlay olib tashlardi.
=============================================================================

«TEKSHIR-KEYIN-YOZ» POYGASI DB'GA TOPSHIRILADI (`nvr_repo.py:509-517`).

`build_uncertain_queue()` «bu hodisa navbatdami?» degan tekshiruvni
KAFOLAT sifatida ishlatmaydi: ko'r audit tortish (05-11) va noaniq navbat
qurish ikki ALOHIDA yo'l va ular bir vaqtda ishlashi mumkin. Kafolat —
`UNIQUE (occupancy_event_id)` + `ON CONFLICT DO NOTHING`.

⚠ `NOT EXISTS` PREDIKATI SHUNGA QARAMAY BOR VA U BOSHQA VAZIFANI
  BAJARADI: usiz `LIMIT` allaqachon navbatda turgan bandlarni ham
  sanardi va kun davomida kelgan YANGI `uncertain` hodisalar navbatga
  HECH QACHON tushmasdi (birinchi chaqiruv limitni «yeb» qo'yardi).
  Ya'ni predikat POYGANI emas, `LIMIT` NING MA'NOSINI qo'riqlaydi.

=============================================================================
⛔ TARTIB MAJBURIY: KO'R AUDIT NAMUNASI AVVAL TORTILADI (§C.8.3).

`build_uncertain_queue()` HAR DOIM `audit_draw` DAN KEYIN chaqiriladi.
Teskari tartibda `UNIQUE (occupancy_event_id)` audit doirasidan aynan
`uncertain` hodisalarni CHIQARIB TASHLARDI — ya'ni xolis namuna model
IKKILANGAN holatlarsiz qolardi va o'lchangan aniqlik SUN'IY ko'tarilardi.

Bu modul tartibni O'ZI majburlay OLMAYDI (u ikki jobning chaqiruv
tartibi); u 05-11 ning darvozasi bo'ladi va shu sababdan bu yerda
YOZILGAN — kod tartibini o'zgartiruvchi odam sababni ko'rsin.
=============================================================================

TENANT FILTRI IKKI QATLAM: RLS policy'si himoya to'ri, `market_id =
:market_id` predikati esa aniq filtr. Xom `text()` da u QO'LDA, ko'rinadigan
joyda turadi (`capture_repo.py` bilan bir xil naqsh).

⚠ XOM `text()` DA BIND PARAMETRLARI TIPLANADI (`nvr_repo.py:29-41` da
  o'lchangan sinf): SQLAlchemy tipni ustundan CHIQARA OLMAYDI va tipsiz
  qiymat asyncpg'ga xom `str` bo'lib borardi. Bu modulda xavf aniq —
  `:business_date` (`date`), `:midpoint` (`numeric`), `:market_id`
  (`uuid`).

⛔ `market_id` METOD ARGUMENTI SIFATIDA OLINMAYDI (T-05-24,
   `camera_zone_repo.coverage()` da o'rnatilgan qoida): u
   `TenantScopedRepository.__init__` dan keladi va YAGONA manba
   bo'lib qoladi. Ikkinchi argument chaqiruvchiga boshqa bozorning
   identifikatorini berish yo'lini ochardi.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Final
from uuid import UUID

from sbozor_core.enums import OccupancyVerdict, ReviewPurpose, ReviewQueueKind
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import Date, Integer, Numeric, Text, bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid

if TYPE_CHECKING:
    from datetime import date, time

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "DEFAULT_MIDPOINT",
    "AnsweredReview",
    "ClaimedReview",
    "ReviewRepository",
]


# ===========================================================================
# NATIJA TIPLARI — chaqiruvchi xom `Row` bilan ishlamaydi
# ===========================================================================


@dataclass(frozen=True, slots=True)
class ClaimedReview:
    """`claim_next()` bergan BITTA band — nazoratchi uchun yetarli minimum.

    ⛔ `verdict`, `confidence`, `model_version` VA `thresholds_version`
       BU TIPDA UMUMAN YO'Q va bu javob sxemasining emas, REPOZITORIYNING
       darajasidagi qaror (UI-SPEC §7.5, T-05-45).

       Sabab mexanik: maydon bu yerda bo'lsa, keyingi ijrochi uni javobga
       qo'shishi uchun bir satr yozishi kifoya bo'lardi — va o'sha bir
       satr ankorlash yo'lini ochardi (05-RESEARCH §C.8: mustaqil
       qarorlarning ~7% i noto'g'ri maslahatdan TESKARISIGA o'zgargan).
       Maydonning YO'QLIGI — kelishuv emas, STRUKTURA
       (`services/storage.py:11-22`).

       Ustuvorlikni HISOBLASH uchun `confidence` kerak, LEKIN u SQL ning
       `ORDER BY` ida qoladi va Python tomonga UMUMAN chiqmaydi.

    `has_active_vendor` — «bu rastada sotuvchi biriktirilgan» bayrog'i.
    U MOTIVATSIYA, ankor EMAS (UI-SPEC §7.3): bayroq rastaning BAND yoki
    BO'SH ekani haqida hech nima demaydi, faqat javobning oqibati
    borligini aytadi.
    """

    assignment_id: UUID
    snapshot_id: UUID
    stall_id: UUID
    stall_code: str
    zone_name: str
    """Bozor hududining nomi (`zones.name`) — ekranda rasta raqami yonida.

    UUID nazoratchi uchun hech nima anglatmaydi; u «14-C · Sabzavot
    qatori» ni ko'radi (UI-SPEC §7.3). `JOIN` shu yerda bir marta
    bajariladi — aks holda frontend har band uchun ikkinchi so'rov
    yuborardi va u `audit_read` yuzasini ham kengaytirardi.
    """
    camera_name: str
    channel_no: int
    business_date: date
    slot_time: time
    polygon: list[Any]
    """NORMALANGAN (0..1) koordinatalar — klient konturni SVG bilan chizadi.

    ⚠ SERVERDA CHIZILMAYDI (UI-SPEC §7.4): bir xil kadr Y-2, Y-3 va Y-4
      da BITTA keshdan kelishi kerak. Serverda chizilgan kontur kadrni
      o'zgartirardi va uchala ekran uchta boshqa baytni yuklardi.
    """
    has_active_vendor: bool


@dataclass(frozen=True, slots=True)
class AnsweredReview:
    """`record_answer()` yozgan qator + OSHKOR qilinadigan ma'lumot.

    ⚠ `system_verdict` FAQAT SHU YERDA, ya'ni javob YOZILGANDAN KEYIN
      mavjud bo'ladi. `claim_next()` uni qaytarmaydi va hech qanday `GET`
      marshruti uni bermaydi — oldindan yuklab qo'yish (prefetch) yo'li
      shu bilan yopiladi (UI-SPEC §7.7).
    """

    review_id: UUID
    system_verdict: str
    queue_kind: str


# ===========================================================================
# USTUVORLIK — BITTA TA'RIF, IKKI SO'ROV
# ===========================================================================

_BILLING_IMPACT: Final[str] = """
    EXISTS (
        SELECT 1
          FROM stall_assignments sa
         WHERE sa.market_id = ev.market_id
           AND sa.stall_id  = cz.stall_id
           AND sa.period @> ev.business_date
    )
"""
"""«Bu rastaning shu KUNDA biriktirilgan sotuvchisi bormi?»

⚠ `period @> ev.business_date` — HODISANING kuni bo'yicha, `now()` bo'yicha
  EMAS. Kechagi hodisani bugun ko'rayotgan nazoratchi uchun ahamiyatli
  savol «o'sha kuni kimdir hisob to'lashi kerakmidi?» va u faqat
  hodisaning kuni bilan javob oladi. `now()` bilan solishtirish rasta
  bugun bo'shatilgan bo'lsa kechagi hisobni JIMGINA ustuvorlikdan
  chiqarardi.

⚠ `sa.market_id` PREDIKATI BOR: `stall_assignments` RLS ostida bo'lsa
  ham, ikkinchi qatlam filtri xom SQL'da QO'LDA yoziladi (modul
  docstringi).
"""

_PRIORITY_ORDER: Final[str] = f"""
    ORDER BY {_BILLING_IMPACT} DESC,
             abs(ev.confidence - :midpoint) ASC,
             ev.id
"""
"""Navbatning YAGONA saralash ta'rifi — modul docstringidagi tanlov.

Uchinchi mezon (`ev.id`) BARQARORLIK uchun: `uuidv7()` vaqt-tartiblangan,
ya'ni teng ustuvorlikdagi bandlar KELIB TUSHISH tartibida beriladi.
Usiz PostgreSQL tartibni kafolatlamasdi va bir xil so'rov ikki marta
BOSHQA band qaytarishi mumkin edi — «sahifani yangilash o'sha bandni
qaytaradi» (UI-SPEC §4.5) da'vosi jimgina yolg'on bo'lardi.
"""


# ===========================================================================
# XOM SO'ROVLAR
# ===========================================================================

# ⚠ `S608` SHU IKKI SO'ROVDA O'CHIRILGAN VA SABAB TOR: f-string ga tushadigan
#   YAGONA qiymatlar — shu moduldagi SOBIT konstantalar (`_PRIORITY_ORDER`,
#   `_BILLING_IMPACT`). Tashqi kirish f-string ga UMUMAN kelmaydi: har bir
#   foydalanuvchi qiymati `bindparam(...)` orqali TIPLANGAN parametr bo'lib
#   ketadi. Muqobil — ustuvorlik ifodasini ikki marta yozish — aynan modul
#   docstringi taqiqlagan ikki nusxani tug'dirardi (`tests/fixtures/
#   occupancy_domain.py` dagi jufti bilan bir xil qaror).
_BUILD_QUEUE = text(
    f"""
    INSERT INTO review_assignments
        (market_id, occupancy_event_id, audit_round_id, queue_kind, purpose)
    SELECT ev.market_id, ev.id, NULL, :queue_kind, :purpose
      FROM occupancy_events ev
      JOIN camera_zones cz
        ON cz.market_id = ev.market_id
       AND cz.id = ev.camera_zone_id
     WHERE ev.market_id = :market_id
       AND ev.business_date = :business_date
       AND ev.verdict = :uncertain
       AND NOT EXISTS (
           SELECT 1
             FROM review_assignments ra
            WHERE ra.occupancy_event_id = ev.id
       )
     {_PRIORITY_ORDER}
     LIMIT :limit
    ON CONFLICT (occupancy_event_id) DO NOTHING
    RETURNING id
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("business_date", type_=Date()),
    bindparam("uncertain", type_=Text()),
    bindparam("queue_kind", type_=Text()),
    bindparam("purpose", type_=Text()),
    bindparam("midpoint", type_=Numeric(5, 4)),
    bindparam("limit", type_=Integer()),
)
"""Bugungi `uncertain` hodisalardan navbat yozuvlari — ustuvorlik BO'YICHA.

⚠ `audit_round_id` ATAYIN `NULL`: noaniq navbat doiraga tegishli emas
  (`blind_audit_needs_round` konstrayti faqat ko'r auditdan talab qiladi).

⚠ `purpose` — `train`, `eval` EMAS va bu D-14 ning sxemadagi shakli
  (`ck_review_assignments_eval_needs_blind_audit`): noaniq navbat
  TANLANGAN namuna, ya'ni uning javoblari bilan aniqlik o'lchash raqamni
  SHISHIRARDI. Qiymat shu yerda LITERAL berilgan (`server_default` ga
  tayanilmaydi): standart o'zgarsa bu yo'l JIMGINA `eval` yoza boshlardi.

⚠ `id` BERILMAYDI — `uuidv7()` `server_default` i yozadi. `gen_random_
  uuid()` ni bu yerda chaqirish IKKINCHI kalit manbai bo'lardi va
  `ev.id` bo'yicha barqaror tartib vaqt-tartiblanganini yo'qotardi.
"""

_CLAIM_NEXT = text(
    f"""
    SELECT ra.id                         AS assignment_id,
           ev.snapshot_id                AS snapshot_id,
           ev.business_date              AS business_date,
           ev.slot_time                  AS slot_time,
           cz.stall_id                   AS stall_id,
           cz.polygon                    AS polygon,
           st.code                       AS stall_code,
           z.name                        AS zone_name,
           cam.name                      AS camera_name,
           cam.channel_no                AS channel_no,
           {_BILLING_IMPACT}             AS has_active_vendor
      FROM review_assignments ra
      JOIN occupancy_events ev
        ON ev.market_id = ra.market_id
       AND ev.id = ra.occupancy_event_id
      JOIN camera_zones cz
        ON cz.market_id = ev.market_id
       AND cz.id = ev.camera_zone_id
      JOIN stalls st
        ON st.market_id = cz.market_id
       AND st.id = cz.stall_id
      JOIN zones z
        ON z.market_id = st.market_id
       AND z.id = st.zone_id
      JOIN cameras cam
        ON cam.market_id = cz.market_id
       AND cam.id = cz.camera_id
     WHERE ra.market_id = :market_id
       AND ra.queue_kind = :queue_kind
       AND NOT EXISTS (
           SELECT 1
             FROM zone_reviews zr
            WHERE zr.review_assignment_id = ra.id
       )
     {_PRIORITY_ORDER}
     LIMIT 1
    FOR UPDATE OF ra SKIP LOCKED
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("queue_kind", type_=Text()),
    bindparam("midpoint", type_=Numeric(5, 4)),
)
"""JAVOBSIZ bandlardan BITTASINI qulflab oladi.

⛔ `FOR UPDATE OF ra` — FAQAT `review_assignments`. Qolgan beshta jadval
   (`occupancy_events`, `camera_zones`, `stalls`, `zones`, `cameras`)
   O'QISH uchun birikadi va ularni qulflash butun bozorning zona
   muharririni bloklardi: admin poligon saqlay olmasdi, chunki
   nazoratchi navbatni ochib qo'ygan edi.

⚠ `INNER JOIN` LARNING HAMMASI MAJBURIY VA BU `LEFT JOIN` DAN AFZAL:
  har bog'lanish `NOT NULL` ustun + kompozit FK bilan qo'riqlangan, ya'ni
  `LEFT JOIN` hech qachon boshqa natija bermasdi-yu, `NULL` holatini
  boshqarish uchun O'LIK kod talab qilardi (`camera_zone_repo._rows()`
  da o'rnatilgan qoida).
"""

_DAILY_ANSWERED = text(
    """
    SELECT count(*) AS answered
      FROM zone_reviews zr
     WHERE zr.market_id = :market_id
       AND zr.reviewer_id = :reviewer_id
       AND zr.queue_kind = :queue_kind
       AND ((zr.decided_at AT TIME ZONE 'Asia/Tashkent')::date) = :business_date
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("reviewer_id", type_=PgUuid(as_uuid=True)),
    bindparam("queue_kind", type_=Text()),
    bindparam("business_date", type_=Date()),
)
"""Nazoratchi shu KUNDA nechta javob yozgani — byudjet hisoblagichi.

=============================================================================
⛔ KUN `decided_at` DAN OLINADI, `occupancy_events.business_date` DAN EMAS.

Ikki o'qish mumkin va ular BOSHQA narsani o'lchaydi:

  `decided_at`   — nazoratchi BUGUN qancha ish qildi. Byudjet aynan
                   shuni cheklaydi: u DIQQAT chegarasi, ya'ni INSON
                   resursiga qo'yilgan.
  `business_date`— ko'rilgan bandlar QAYSI kunga tegishli.

Ikkinchisi tanlansa, kechagi qoldiqni bugun ko'rayotgan nazoratchi
KECHAGI byudjetni yeb, bugungisini to'liq bo'sh qoldirardi — ya'ni u bir
kunda ikki barobar ish qila olardi va byudjetning butun mazmuni
yo'qolardi. UI-SPEC §7.2 dagi «Bugun: 12 / 50» ham aynan birinchi
o'qish.

⚠ `AT TIME ZONE 'Asia/Tashkent'` — `snapshots.business_date` GENERATED
  ifodasining AYNAN o'zi. UTC kuni bilan solishtirish yarim tunda (05:00
  UTC gacha) byudjetni «kechagi» deb sanardi va nazoratchi ertalab ishga
  kelganda hisoblagich to'lgan bo'lardi (Pitfall 3).
=============================================================================
"""

_RECORD_ANSWER = text(
    """
    WITH src AS (
        SELECT ra.id         AS assignment_id,
               ra.market_id  AS market_id,
               ra.queue_kind AS queue_kind,
               ev.verdict    AS system_verdict
          FROM review_assignments ra
          JOIN occupancy_events ev
            ON ev.market_id = ra.market_id
           AND ev.id = ra.occupancy_event_id
         WHERE ra.market_id = :market_id
           AND ra.id = :assignment_id
           AND ra.queue_kind = :queue_kind
    ), written AS (
        INSERT INTO zone_reviews
            (market_id, review_assignment_id, queue_kind, shown_ai_verdict,
             human_verdict, reviewer_id, decision_ms)
        SELECT src.market_id, src.assignment_id, src.queue_kind, :shown_ai_verdict,
               :human_verdict, :reviewer_id, :decision_ms
          FROM src
        RETURNING id
    )
    SELECT written.id AS review_id, src.system_verdict, src.queue_kind
      FROM written
     CROSS JOIN src
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("assignment_id", type_=PgUuid(as_uuid=True)),
    bindparam("queue_kind", type_=Text()),
    bindparam("reviewer_id", type_=PgUuid(as_uuid=True)),
    bindparam("human_verdict", type_=Text()),
    bindparam("decision_ms", type_=Integer()),
)
"""BITTA javob qatori + oshkor qilinadigan tizim verdikti — BIR so'rovda.

=============================================================================
⛔⛔ `:queue_kind` — FILTR, YOZILADIGAN QIYMAT EMAS. IKKISI ADASHTIRILMASIN.

`WHERE ra.queue_kind = :queue_kind` chaqiruvchi QAYSI navbatga xizmat
qilayotganini bildiradi: noaniq navbat marshruti ko'r audit topshirig'iga
javob yoza OLMAYDI va aksincha. Ikki marshrut ikki xil xato kodini
beradi (`review_already_answered` va `blind_answer_locked`, 05-11) va
ular AYNAN shu chegara tufayli aralashib ketmaydi.

`INSERT` ga esa **`src.queue_kind`** ketadi — QATORDAN o'qilgan qiymat.
Uni `:queue_kind` bilan almashtirish «soddalashtirish» bo'lib ko'rinardi
(«baribir teng-ku») va DENORMALIZATSIYA MANBAINI chaqiruvchiga
ko'chirardi: filtrni bo'shatgan kun (yoki ikki navbat uchun bitta
marshrut yozilgan kun) yolg'on nusxa yozish yo'li OCHILARDI. Farq
sabotaj bilan o'lchanadi.
=============================================================================

=============================================================================
⛔⛔ `queue_kind` TOPSHIRIQ QATORIDAN O'QILADI, CHAQIRUVCHIDAN OLINMAYDI.

`zone_reviews.queue_kind` — DENORMALIZATSIYA va u `review_assignments
(id, queue_kind)` LANGARIGA kompozit FK bilan qadalgan (05-05
deviatsiya #5). Ya'ni YOLG'ON nusxa DB tomonidan rad etiladi.

Lekin langar «yolg'on nusxa YOZILMASIN» ni kafolatlamaydi — u faqat
yozilganini USHLAYDI. Bu `SELECT` esa yolg'on nusxa MANBAINI umuman yo'q
qiladi: qiymat chaqiruvchining argumentida MAVJUD EMAS, ya'ni uni
noto'g'ri berish uchun avval bu SQL ni o'zgartirish kerak bo'ladi.

⛔ `shown_ai_verdict` HAM MAYDON EMAS, PARAMETR — LEKIN KLIENTNIKI EMAS.
   Uni chaqiruvchi (router) SERVERDA hisoblaydi; `AnswerRequest` sxemasida
   bunday maydon UMUMAN e'lon qilinmagan (D-17.3, T-05-44). Klient uni
   yubora olsa YOLG'ON gapira olardi va `blind_audit_not_shown` `CHECK` i
   aldangan bo'lardi.
=============================================================================

⚠ NOL QATOR = «topshiriq topilmadi YOKI begona bozorniki». Ikkalasi
  ATAYIN ajratilmaydi va chaqiruvchi ikkalasiga ham 404 beradi (T-05-25):
  farqlash javob kodi bo'yicha identifikator sanab chiqish yo'lini
  ochardi.

⚠ IKKINCHI JAVOB `UNIQUE (review_assignment_id)` bilan rad etiladi
  (`23505`) va chaqiruvchi uni 409 ga aylantiradi. Oldindan «javob
  bormi?» deb so'rash IKKI so'rovni bir xil bo'sh holatni ko'rgan holda
  o'tkazib yuborardi (`nvr_repo.py:509-517` naqshi).

⚠ `CROSS JOIN src` — `written` bo'sh bo'lsa natija ham bo'sh. `LEFT JOIN`
  qilinsa qator qaytardi-yu, `review_id` `NULL` bo'lardi va chaqiruvchi
  «yozildi» deb o'ylardi.
"""


DEFAULT_MIDPOINT: Final[Decimal] = Decimal("0.45")
"""`Settings.review_uncertain_midpoint` NING JUFTI — repozitoriy standarti.

⚠ REPOZITORIY `Settings` NI IMPORT QILMAYDI (§S-8, `zone_geometry.py` da
  o'rnatilgan qoida): qiymatni chaqiruvchi konstruktorga beradi. Bu
  yerdagi standart sozlamani bermagan chaqiruvchi (test, kelajakdagi fon
  vazifasi) ham MA'NOLI tartib olishi uchun — tasodifiy emas.

`Decimal` — `numeric(5,4)` bilan bir shkalada. `float` berilsa asyncpg
uni `double precision` deb yuborardi va `abs(numeric - double)` har
qatorda kast talab qilardi.
"""


class ReviewRepository(TenantScopedRepository):
    """Noaniq navbat va nazoratchi javoblari ustidagi yagona DB yuzasi.

    ⛔ O'CHIRISH METODI UMUMAN YOZILMAGAN va bu KELISHUV EMAS, STRUKTURA
       (`capture_repo.py:74-79` bilan bir xil qaror). `zone_reviews` —
       insonning moliyaviy oqibatli qarori va u `AUDITED_TABLES` da;
       `0018` unga SHARTSIZ `BEFORE UPDATE OR DELETE` qo'riqchisini
       ulaydi. Metod mavjud bo'lsa keyingi tahrirlovchi uni «testni
       soddalashtirish uchun» chaqirardi va DB rad etganda uni «g'alati
       cheklov» deb chetlab o'tish yo'lini izlardi.
    """

    def __init__(
        self,
        session: AsyncSession,
        market_id: UUID,
        *,
        midpoint: float | Decimal = DEFAULT_MIDPOINT,
    ) -> None:
        super().__init__(session, market_id)
        self.midpoint = Decimal(str(midpoint))

    # ------------------------------------------------------------------
    # 1. Navbatni qurish (chaqiruvchisi — 05-11 ning `audit_draw` jobi)
    # ------------------------------------------------------------------

    async def build_uncertain_queue(self, business_date: date, *, limit: int) -> int:
        """Bugungi `uncertain` hodisalardan navbat yozuvlari yaratadi.

        ⛔ CHAQIRUV TARTIBI MAJBURIY: bu metod ko'r audit namunasi
           TORTILGANDAN KEYIN chaqiriladi (modul docstringi). Tartib bu
           yerda majburlanmaydi — u ikki jobning chaqiruv ketma-ketligi
           va uning darvozasi 05-11 da.

        Args:
            business_date: qaysi kunning hodisalari (`Asia/Tashkent`).
            limit: bitta chaqiruvda qo'shiladigan YANGI yozuvlar soni.
                Allaqachon navbatda turgan bandlar bu sanoqqa KIRMAYDI
                (modul docstringidagi ⚠).

        Returns:
            HAQIQATAN yozilgan qatorlar soni (`RETURNING` bo'yicha,
            `rowcount` bo'yicha EMAS — `ON CONFLICT DO NOTHING` da ular
            ajraladi).
        """
        result = await self.session.execute(
            _BUILD_QUEUE,
            {
                "market_id": self.market_id,
                "business_date": business_date,
                "uncertain": OccupancyVerdict.UNCERTAIN.value,
                "queue_kind": ReviewQueueKind.UNCERTAIN.value,
                "purpose": ReviewPurpose.TRAIN.value,
                "midpoint": self.midpoint,
                "limit": limit,
            },
        )
        return len(result.fetchall())

    # ------------------------------------------------------------------
    # 2. Band olish
    # ------------------------------------------------------------------

    async def claim_next(
        self,
        *,
        queue_kind: str = ReviewQueueKind.UNCERTAIN.value,
    ) -> ClaimedReview | None:
        """Ustuvorlik bo'yicha KEYINGI javobsiz bandni qulflab oladi.

        ⚠ `reviewer_id` ARGUMENTI ATAYIN YO'Q (reja imzosidan farq).
          Saralash unga TAYANMAYDI va tayanishi ham kerak emas: navbat
          BOZORNIKI, nazoratchiniki emas. Ishlatilmaydigan argument
          «nazoratchiga biriktirilgan navbat bor» degan YOLG'ON va'da
          berardi — holbuki bir band ikki nazoratchiga ham berilishi
          mumkin va bu ATAYIN (modul docstringidagi `SKIP LOCKED` bandi).

        Returns:
            `None` — javobsiz band QOLMADI. Bu chaqiruvchida «navbat
            bo'sh» (`review_queue_empty`) bo'ladi va u byudjet
            tugashidan ATAYIN ajratilgan: birinchisi ISH TUGADI, ikkinchisi
            ISH QOLGAN BO'LISHI MUMKIN degani.
        """
        result = await self.session.execute(
            _CLAIM_NEXT,
            {
                "market_id": self.market_id,
                "queue_kind": queue_kind,
                "midpoint": self.midpoint,
            },
        )
        row = result.mappings().first()
        if row is None:
            return None
        return ClaimedReview(
            assignment_id=row["assignment_id"],
            snapshot_id=row["snapshot_id"],
            stall_id=row["stall_id"],
            stall_code=row["stall_code"],
            zone_name=row["zone_name"],
            camera_name=row["camera_name"],
            channel_no=row["channel_no"],
            business_date=row["business_date"],
            slot_time=row["slot_time"],
            polygon=list(row["polygon"]),
            has_active_vendor=bool(row["has_active_vendor"]),
        )

    # ------------------------------------------------------------------
    # 3. Byudjet
    # ------------------------------------------------------------------

    async def daily_answered_count(
        self,
        reviewer_id: UUID,
        business_date: date,
        *,
        queue_kind: str,
    ) -> int:
        """Nazoratchi shu kunda shu navbatda nechta javob yozgan."""
        result = await self.session.execute(
            _DAILY_ANSWERED,
            {
                "market_id": self.market_id,
                "reviewer_id": reviewer_id,
                "queue_kind": queue_kind,
                "business_date": business_date,
            },
        )
        return int(result.scalar_one())

    # ------------------------------------------------------------------
    # 4. Javob
    # ------------------------------------------------------------------

    async def record_answer(
        self,
        assignment_id: UUID,
        *,
        queue_kind: str,
        reviewer_id: UUID,
        human_verdict: str,
        shown_ai_verdict: bool,
        decision_ms: int | None,
    ) -> AnsweredReview | None:
        """BITTA `zone_reviews` qatori yozadi va oshkor ma'lumotni qaytaradi.

        Args:
            queue_kind: chaqiruvchi QAYSI navbatga xizmat qilyapti —
                FILTR. Yoziladigan qiymat QATORDAN o'qiladi
                (`_RECORD_ANSWER` docstringi).
            shown_ai_verdict: SERVER hisoblagan qiymat. Klient uni
                yubormaydi va `AnswerRequest` da bunday maydon UMUMAN
                yo'q (D-17.3).
            decision_ms: server O'LCHAGAN farq yoki `None` (o'lchov
                topilmadi). Klient qiymati BU YERGA YETIB KELMAYDI.

        Returns:
            `None` — topshiriq topilmadi, begona bozorniki yoki BOSHQA
            navbatniki (uchalasi ham 404 — farqlash navbat a'zoligini
            javob kodi bilan oshkor qilardi).

        Raises:
            IntegrityError: bu topshiriqqa javob ALLAQACHON yozilgan
                (`23505`) — chaqiruvchi 409 ga aylantiradi.
        """
        result = await self.session.execute(
            _RECORD_ANSWER,
            {
                "market_id": self.market_id,
                "assignment_id": assignment_id,
                "queue_kind": queue_kind,
                "reviewer_id": reviewer_id,
                "human_verdict": human_verdict,
                "shown_ai_verdict": shown_ai_verdict,
                "decision_ms": decision_ms,
            },
        )
        row = result.mappings().first()
        if row is None:
            return None
        return AnsweredReview(
            review_id=row["review_id"],
            system_verdict=row["system_verdict"],
            queue_kind=row["queue_kind"],
        )
