"""Kunlik reja, ijara va `SKIP LOCKED` — orkestratsiyaning butun DB yuzasi.

=============================================================================
1-MAJBURIYAT: `SKIP LOCKED` VA IJARA — IKKALASI HAM KERAK.

`SELECT ... FOR UPDATE SKIP LOCKED` faqat TRANZAKSIYA DAVOMIDA himoya
qiladi. Worker qatorni `running` ga o'tkazib COMMIT qilgach qulf TUSHADI —
o'shandan keyin jarayon o'lsa `SKIP LOCKED` hech nima qilmaydi va qator
MANGU `running` bo'lib qolardi. O'sha slot uchun na kadr, na alert, na
hisobot qatori bo'lardi, ya'ni nosozlik JIMGINA o'tib ketardi (D-20 aynan
shuni taqiqlaydi).

Ijara (`locked_until`) esa AYNAN o'sha muddatni qoplaydi va o'z navbatida
konkurentlikni qoplamaydi: ikki worker bir vaqtda `SELECT` qilsa ikkalasi
ham bir xil qatorni ko'rardi va bitta slot IKKI MARTA bajarilardi —
dublikat dalil va 6-fazada ikki marta hisob (T-04-33).

Ikkala mexanizm TURLI muddatni qoplaydi. Bittasini «soddalashtirish
uchun» tashlab yuborish ikkinchisining qoplagan muddatini OCHIQ qoldiradi.
Shuning uchun ular ALOHIDA testlar bilan o'lchanadi va bittasini o'chirish
ikkinchisini yashil qoldiradi — bu farqning o'zi ham
`tests/integration/test_capture_repo.py` da qulflangan.

⚠ LOYIHADA BU NAQSHNING PRECEDENTI YO'Q (`04-PATTERNS.md` §4.1: grep ikkita
  natija beradi va ikkalasi ham IZOH). Eng yaqin strukturaviy qo'shni —
  `nvr_repo.py:534-565` (shartli holat o'tishi), lekin unda QULF yo'q.
  Shuning uchun `claim_due()` ning shakli `04-RESEARCH.md` §A.2 dan
  AYNAN olinadi, o'ylab topilmaydi.
=============================================================================

=============================================================================
2-MAJBURIYAT: XOM `text()` DA BIND PARAMETRLARI TIPLANADI.

`nvr_repo.py:29-41` da o'lchangan sinf: `text()` da SQLAlchemy tipni
ustundan CHIQARA OLMAYDI va tipsiz qiymat asyncpg'ga xom `str` bo'lib
borardi. Bu modulda xavf aniq: `:business_date` — `date`, `:grace_seconds`
— `int` (u `make_interval(secs => ...)` ga tushadi), `:market_id` —
`uuid`. Shuning uchun HAR BIR xom so'rov `bindparam(..., type_=...)`
bilan e'lon qilinadi.

Qolgan hamma joyda SQLAlchemy Core ishlatiladi (`insert()`/`update()`) —
u tipni MODEL USTUNIDAN oladi, ya'ni tiplashni unutadigan qadam umuman
yo'q. Xom `text()` FAQAT ikki joyda va ikkalasi ham ORM'da ifodalanmaydi:
`INSERT ... SELECT ... ON CONFLICT` va `claim_due()` ning
`WITH ... UPDATE ... FROM ... RETURNING` CTE'si.
=============================================================================

=============================================================================
3-MAJBURIYAT: «TEKSHIR-KEYIN-YOZ» ATAYIN QILINMAYDI.

`ensure_plan()` «bugungi reja bormi?» deb SO'RAMAYDI. Ikki parallel tik
(taskiq'ning hujjatlashtirilgan yiqilish rejimi: planer qayta ko'tarildi
va tikni takrorladi) o'sha tekshiruvda IKKALASI ham bo'sh holatni ko'rardi
va bitta slot uchun IKKITA qator tug'ilardi — 6-fazada bu bitta kunni ikki
marta hisoblash degani.

Poyga DB'ga topshiriladi: `uq_capture_runs_market_id_camera_id_business_
date_slot_time` + `ON CONFLICT DO NOTHING`. Bu `nvr_repo.py:509-517`
mulohazasining aynan takrori.
=============================================================================

TENANT FILTRI IKKI QATLAM (`sbozor_core/tenancy.py`): RLS policy'si himoya
to'ri, `market_id = :market_id` predikati esa aniq filtr. Xom SQL'da u
QO'LDA, ko'rinadigan joyda turadi (`tariff_repo.py` va `stall_repo.py`
bilan bir xil naqsh).

⚠ ENG JIM XATO SINFI — TENANT KONTEKSTISIZ CHAQIRUV. RLS ostida
  `SELECT`/`UPDATE` **0 qator** qaytaradi va **istisno bermaydi**. Fon
  vazifasi kontekstni o'rnatishni unutsa butun kunlik reja
  materializatsiya qilinmagan bo'lib qolardi va yagona belgi «ertaga kadr
  yo'q» bo'lardi. Bu holat ATAYIN o'lchanadi
  (`test_ensure_plan_without_tenant_context_writes_nothing_and_never_raises`).

⛔ QATOR HECH QACHON O'CHIRILMAYDI. Reja qatori — DALIL: u «bu slot
  kutilgan edi» degan da'voning yagona asosi. O'chirilgan qator
  «bajarilmadi» ni «rejalashtirilmagan edi» ga aylantirardi va D-20 ning
  butun mazmuni yo'qolardi. Bu modulda o'chirish metodi UMUMAN yozilmaydi
  — metodning yo'qligi kelishuv emas, STRUKTURA (`nvr_repo.py:48-61`
  bilan bir xil qaror).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sbozor_core.enums import CaptureRunStatus, SnapshotQuality
from sbozor_core.models import CaptureRun, Snapshot
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import (
    Date,
    Integer,
    SmallInteger,
    Text,
    and_,
    bindparam,
    case,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.repositories.audit_repo import mask_sensitive
from app.services.capture_errors import (
    CAPTURE_AUTH_LOCKING_CODES,
    CAPTURE_DEFER_CODES,
    CAPTURE_ERROR_CODES,
    CAPTURE_ERROR_META,
    CAPTURE_PLAN_CREATED_LATE,
    CAPTURE_SLOT_MISSED,
    CAPTURE_WORKER_LOST,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "CaptureRepository",
    "ClaimedRun",
    "DaySummary",
    "MissedSlot",
    "PlanResult",
    "RunRow",
]


# ===========================================================================
# NATIJA TIPLARI — chaqiruvchi xom `Row` bilan ishlamaydi
# ===========================================================================


@dataclass(frozen=True, slots=True)
class PlanResult:
    """`ensure_plan()` ning natijasi — IKKI son, bittasi emas.

    `created` — HAQIQATAN yozilgan qatorlar soni (`ON CONFLICT DO NOTHING`
    o'tkazib yuborganlari kirmaydi). Ikkinchi tik uchun u `0`.

    `skipped` — o'sha yangi qatorlarning nechtasi `skipped` holatida
    TUG'ILGANI (`capture_plan_created_late`). Ya'ni `created - skipped` —
    haqiqatan bajariladigan slotlar soni.

    ⚠ IKKI SON KERAK, chunki ular IKKI XIL savolga javob beradi: `created`
      «reja tuzildimi?», `skipped` esa «bozor kech ulandimi?». Bittasiga
      yig'ish yangi bozorning birinchi kunini «hammasi joyida» yoki
      «hammasi yo'qoldi» deb ko'rsatardi — ikkalasi ham yolg'on.
    """

    created: int
    skipped: int


@dataclass(frozen=True, slots=True)
class ClaimedRun:
    """`claim_due()` bergan BITTA ish — worker uchun yetarli minimum.

    `nvr_id` bor, chunki fan-out AYNAN shu ustun bo'yicha guruhlanadi:
    konkurentlik chegarasi NVR ga tegishli (D-04/D-08), kameraga emas.

    Butun `CaptureRun` ORM obyekti QAYTARILMAYDI: worker uni tranzaksiya
    tugagandan KEYIN ishlatadi va detached obyektning har bir atributi
    `DetachedInstanceError` xavfini olib yurardi. Frozen dataclass esa
    tranzaksiyaga bog'lanmagan qiymat.
    """

    id: UUID
    camera_id: UUID
    nvr_id: UUID
    slot_time: time
    scheduled_at: datetime
    business_date: date
    attempts: int


@dataclass(frozen=True, slots=True)
class MissedSlot:
    """`mark_missed()` yopgan slot — ALERTNING YAGONA MANBAI (D-20).

    Qator faqat o'zgartirilib qaytarilmasa, «bugun 12 slot umuman
    bajarilmadi» xabari hech qayerdan kelmasdi: yo'qlik HODISA
    qoldirmaydi, ya'ni uni faqat SHU qaytish qiymati ko'rinadigan qiladi.
    """

    market_id: UUID
    camera_id: UUID
    business_date: date
    slot_time: time


@dataclass(frozen=True, slots=True)
class DaySummary:
    """`04-UI-SPEC.md` §6.3 ning oltala hisoblagichi + `planned` va `done`.

    ⛔ NOL QIYMAT — NATIJA, UNING YO'QLIGI EMAS. Barcha maydonlar HAR DOIM
    to'ldiriladi, chunki ular `GROUP BY` natijasidan emas, aniq
    `count(*) FILTER (WHERE ...)` ifodalaridan keladi. `GROUP BY` bilan
    yig'ilganda nol hisoblagich UMUMAN qatorsiz qolardi va UI'da «buzuq
    kadr yo'q» bilan «buzuq kadr sanalmagan» bir xil ko'rinardi — bu
    3-fazadagi «uch hisoblagich» qoidasining aynan buzilishi.
    """

    planned: int
    done: int
    ok: int
    dark: int
    blank: int
    corrupt: int
    failed: int
    missed: int


@dataclass(frozen=True, slots=True)
class RunRow:
    """Jurnal matritsasining BITTA hujayrasi (`04-UI-SPEC.md` §6.4).

    ⚠ ARXIVLANGAN KAMERANING QATORLARI HAM QAYTADI va bu ATAYIN. Ular
      `ensure_plan()` da endi YARATILMAYDI, lekin keyinroq arxivlangan
      kameraning O'TMISHDAGI qatorlari joyida qoladi — dalil hech qachon
      yashirilmaydi. Ularni bu yerda filtrlash matritsani `day_summary()`
      bilan ZID qilardi: xulosa «175 rejalashtirildi» deb turib, jadvalda
      168 hujayra bo'lardi. Filtrlash qarori UI qatlamida (`is_archived`
      bayrog'i aynan shuning uchun qaytariladi).
    """

    run_id: UUID
    camera_id: UUID
    channel_no: int
    camera_name: str
    is_archived: bool
    slot_time: time
    scheduled_at: datetime
    status: str
    attempts: int
    error_code: str | None
    quality_verdict: str | None
    snapshot_id: UUID | None


# ===========================================================================
# XOM SQL — FAQAT ORM'DA IFODALANMAYDIGAN IKKI SO'ROV
# ===========================================================================

_ENSURE_PLAN = text(
    """
    INSERT INTO capture_runs
        (market_id, camera_id, nvr_id, slot_time, scheduled_at,
         status, error_code, is_market_open)
    SELECT :market_id,
           cam.id,
           cam.nvr_id,
           slot.slot_time,
           plan.scheduled_at,
           CASE WHEN late.is_late THEN 'skipped' ELSE 'pending' END,
           CASE WHEN late.is_late THEN :late_code ELSE NULL END,
           market_is_open(:market_id, :business_date)
      FROM cameras cam
      JOIN markets m
        ON m.id = cam.market_id
      JOIN snapshot_schedules sch
        ON sch.market_id = cam.market_id
       AND sch.period @> :business_date
      JOIN snapshot_schedule_slots slot
        ON slot.market_id = sch.market_id
       AND slot.schedule_id = sch.id
     CROSS JOIN LATERAL (
           SELECT ((:business_date + slot.slot_time) AT TIME ZONE m.timezone)
                  AS scheduled_at
     ) plan
     CROSS JOIN LATERAL (
           SELECT plan.scheduled_at + make_interval(secs => :grace_seconds) < now()
                  AS is_late
     ) late
     WHERE cam.market_id = :market_id
       AND cam.is_archived = false
       AND (
             NOT EXISTS (
                 SELECT 1 FROM capture_runs r
                  WHERE r.market_id = :market_id
                    AND r.business_date = :business_date
             )
             OR EXISTS (
                 SELECT 1 FROM capture_runs r
                  WHERE r.market_id = :market_id
                    AND r.business_date = :business_date
                    AND r.slot_time = slot.slot_time
             )
           )
    ON CONFLICT ON CONSTRAINT uq_capture_runs_market_id_camera_id_business_date_slot_time
    DO NOTHING
    RETURNING status
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("business_date", type_=Date()),
    bindparam("grace_seconds", type_=Integer()),
    bindparam("late_code", type_=Text()),
)
"""Kunlik rejani IDEMPOTENT materializatsiya qiladi (CAM-05).

MANBA — `cameras x snapshot_schedule_slots`, shu kunni QOPLAYDIGAN profil
bo'yicha (`sch.period @> :business_date`). Bo'shliq (qoplanmagan kun)
ATAYIN mumkin: o'sha kunga umuman slot yo'q, ya'ni bu so'rov 0 qator
yozadi va bu XATO EMAS (mavsumiy yopiladigan bozor). Lekin u UI'da
KO'RINISHI shart — `schedule_repo.uncovered_days()` aynan shuning uchun bor.

⚠ ARXIVLANGAN KAMERA REJAGA KIRMAYDI (`cam.is_archived = false`).
  `04-UI-SPEC.md` §6.4: uning `capture_runs` qatorlari YARATILMAYDI ham.
  Predikatsiz arxivlangan kanal har kuni 7 ta yo'qlik yozuvi olardi, ular
  grace oynasidan keyin `missed` bo'lardi va HAR KUNI alert berardi — ya'ni
  D-10 ning soft-delete'i alert kanalini shovqinga to'ldirardi.

⚠ `scheduled_at` BOZORNING O'Z MINTAQASIDAN (`m.timezone`), `business_date`
  esa GENERATED ustunda LITERAL mintaqadan hisoblanadi. Assimetriya
  `models/snapshot.py::CAPTURE_BUSINESS_DATE_EXPR` da hujjatlashtirilgan va
  `test_meta.py::test_markets_all_use_tashkent_timezone` bilan
  qo'riqlanadi: ikkinchi mintaqadagi bozor qo'shilgan kuni test qizaradi.

⚠ `AT TIME ZONE` YO'NALISHI: `timestamp AT TIME ZONE 'Asia/Tashkent'` naive
  vaqtni Toshkent devor-soati sifatida talqin qilib `timestamptz` beradi.
  Teskarisi (`timestamptz AT TIME ZONE ...`) naive qiymat qaytarardi va
  ustun tipi bilan mos kelmasdi.

⚠ T-04-38 — `is_late` shoxi. Bozor kunning o'rtasida faollashtirilsa o'sha
  kunning o'tib ketgan slotlari `pending` emas, `skipped` bo'lib TUG'ILADI
  va alert bermaydi. Ular hisobotda ko'rinadi (shaffoflik), lekin nosozlik
  sifatida sanalmaydi. Bu shox FAQAT qator YARATILAYOTGAN paytda ishlaydi:
  uzoq uzilishdan keyin qatorlar allaqachon bor va ular `mark_missed()`
  bilan `missed` bo'ladi — bu TO'G'RI natija (§B.5).

⚠ `market_is_open()` QAYTA ISHLATILADI, kalendar mantig'i TAKRORLANMAYDI
  (D-10). Funksiya `SECURITY DEFINER` EMAS, ya'ni RLS unga to'liq
  qo'llanadi va begona bozorning kalendari ko'rinmaydi (T-02-22).

⚠ `ON CONFLICT` NISHONI — KONSTRAYT NOMI, ustunlar ro'yxati emas:
  `business_date` HISOBLANADIGAN ustun va uni `ON CONFLICT (...)` ifodasida
  qayta yozish ifodani ikkinchi marta ta'riflashni talab qilardi.

⛔ D-05 — SLOT O'LCHOVI BO'YICHA MUZLATISH (`AND (NOT EXISTS ... OR EXISTS ...)`).

  `capture_tick` HAR DAQIQADA ishlaydi va uning 1-qadami aynan shu so'rov
  (`04-PATTERNS.md` §3.3). Ya'ni admin soat 12:00 da jadvalga `10:00`
  vaqtini qo'shsa, keyingi tik uni BUGUNGI rejaga yozib qo'yardi — D-05
  esa buni ochiq TAQIQLAYDI («jadval kun o'rtasida o'zgartirilsa bugungi
  rejaga ta'sir qilmaydi») va SC#1 aynan shunga tayanadi («**ertasi kuni**
  aynan o'sha slotlarda»). UI ham DL-1 da doimiy izoh chizadi: «Yangi
  vaqtlar ERTADAN boshlab ishlaydi».

  Shart AYNAN SLOT o'lchovida, kun o'lchovida EMAS — va bu farq ataylab:

    * kun BO'SH bo'lsa (birinchi tik) — hamma narsa yoziladi;
    * kun ALLAQACHON materializatsiya qilingan bo'lsa — faqat BUGUNGI
      rejada MAVJUD BO'LGAN `slot_time` lar uchun yoziladi.

  Ikkinchi shox mid-day kashf etilgan KAMERANI qamrab qoladi: u bugungi
  slotlarni oladi (o'tib ketganlari `skipped` bo'lib tug'iladi va alert
  bermaydi), lekin YANGI VAQT ertagacha kutadi. Kun o'lchovidagi muzlatish
  bunday kamerani butun kunga ko'rinmas qilardi.

⚠ BU «TEKSHIR-KEYIN-YOZ» EMAS va 3-majburiyatga ZID KELMAYDI. Shart
  so'rovning O'ZI ichida — alohida `SELECT` yo'q, ya'ni poyga oynasi ham
  yo'q. Ikki parallel tik: ikkalasi ham bo'sh kunni ko'rsa ikkalasi ham
  yozadi va `ON CONFLICT` dublikatni yutadi; biri qatorlarni ko'rsa u
  yangi vaqt yozmaydi. Uchala interleaving ham to'g'ri natija beradi.
  Idempotentlik hamon `UNIQUE` konstraytida, bu shartda EMAS.

⚠ `:business_date` DA XOM `::date` KASTI YO'Q VA U QO'SHILMASLIGI KERAK
  (o'lchandi). SQLAlchemy ning `text()` bind-parametr regexida `(?!:)`
  lookahead bor — ya'ni `:` bilan boshlanuvchi kastdan OLDIN turgan
  parametr UMUMAN parametr deb tanilmaydi va `:business_date::date` xom
  matn bo'lib asyncpg'ga borib, `syntax error at or near ":"` beradi.
  Kast KERAK EMAS ham: `bindparam(..., type_=Date())` allaqachon
  `$3::DATE` ni chiqaradi. Bu — modul docstringidagi 2-majburiyatning
  amaliy foydasi.
"""

_CLAIM_DUE = text(
    """
    WITH due AS (
        SELECT id
          FROM capture_runs
         WHERE market_id = :market_id
           AND status = 'pending'
           AND scheduled_at <= now()
           AND scheduled_at > now() - make_interval(secs => :grace_seconds)
           AND (locked_until IS NULL OR locked_until <= now())
         ORDER BY scheduled_at
         LIMIT :batch
         FOR UPDATE SKIP LOCKED
    )
    UPDATE capture_runs c
       SET status = 'running',
           attempts = c.attempts + 1,
           locked_until = now() + make_interval(secs => :lease_seconds),
           locked_by = :worker_id,
           started_at = COALESCE(c.started_at, now())
      FROM due
     WHERE c.market_id = :market_id
       AND c.id = due.id
    RETURNING c.id, c.camera_id, c.nvr_id, c.slot_time,
              c.scheduled_at, c.business_date, c.attempts
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("grace_seconds", type_=Integer()),
    bindparam("lease_seconds", type_=Integer()),
    bindparam("batch", type_=Integer()),
    bindparam("worker_id", type_=Text()),
)
"""Muddati kelgan ishlarni QULFLAB oladi — `04-RESEARCH.md` §A.2 ning shakli.

⛔ `FOR UPDATE SKIP LOCKED` — modul docstringidagi 1-majburiyat. Ikki
   worker bir vaqtda `SELECT` qilsa ikkinchisi qulflangan qatorlarni
   O'TKAZIB YUBORADI (kutmaydi ham, xato ham bermaydi). Uni olib tashlash
   ikkinchi tranzaksiyani BLOKLAYDI va bitta slot ikki marta bajarilardi.

OYNA IKKI TOMONLAMA VA IKKALA TOMONI HAM MAJBURIY:

  * `scheduled_at <= now()` — vaqti kelmagan slot olinmaydi (aks holda
    butun kunlik reja birinchi tikda navbatga tushardi);
  * `scheduled_at > now() - grace` — oynadan CHIQQAN slot ham olinmaydi.
    Sabab MAHSULOTDA: 06:00 sloti 07:05 da olingan kadr «06:00 da rasta
    band edimi?» savoliga javob bermaydi, LEKIN javob berganday ko'rinadi.
    Kechikkan kadr yo'q kadrdan YOMONROQ. Bunday slotni `mark_missed()`
    yopadi.

⚠ `locked_until` PREDIKATI `defer()` NING YAGONA MEXANIZMI (T-04-35).
  `capture_stream_limit` da qator `pending` bo'lib qoladi va faqat
  `locked_until` keyingi tikni kechiktiradi. Bu predikatsiz `defer()`
  butunlay no-op bo'lardi: keyingi tik qatorni DARHOL qayta olib, NVR ni
  o'sha zahoti qaytadan bosardi. `04-RESEARCH.md` §A.2 dagi eskizda bu
  predikat YO'Q — u kechiktirish siyosati kiritilishidan oldin yozilgan.

⚠ `started_at` `COALESCE` bilan: ikkinchi urinishda u QAYTA YOZILMAYDI —
  «kadr olish qachon boshlandi» savolining javobi BIRINCHI urinish
  (`nvr_repo.start_run` ning `started_at` qarori bilan bir xil sabab).

⚠ `attempts` HAR OLISHDA oshadi, `finish_*` da emas: qator olinib, worker
  o'lgan holat ham urinish bo'lib SANALISHI kerak — aks holda o'lik worker
  byudjetni umuman yemasdi va slot cheksiz aylanardi.
"""

_MARK_MISSED = text(
    """
    UPDATE capture_runs
       SET status = 'missed',
           finished_at = now(),
           error_code = :missed_code
     WHERE market_id = :market_id
       AND status = 'pending'
       AND scheduled_at < now() - make_interval(secs => :grace_seconds)
    RETURNING market_id, camera_id, business_date, slot_time
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("grace_seconds", type_=Integer()),
    bindparam("missed_code", type_=Text()),
)
"""Grace oynasidan chiqqan va HECH QACHON boshlanmagan slotlar (§B.5, 1-so'rov).

⛔ `missed` VA `failed` NI ARALASHTIRMANG. `missed` — «BIZNING tizimimiz
   ishlamadi» (urinish umuman bo'lmagan), `failed` — «NVR javob bermadi»
   (urinish BO'LGAN va `error_code` sababni aytadi). Ikkalasini bitta
   kodga yig'ish dala diagnostikasini o'ldiradi: «bugun 12 slot yiqildi»
   xabari operatorga VPS'ga qarash kerakmi yoki bozorga borish kerakmi
   degan savolga javob bermasdi.

`RETURNING` — ALERTNING YAGONA MANBAI. Qatorni faqat o'zgartirib
qaytarmaslik yo'qlikni yana ko'rinmas qilardi.
"""

_RELEASE_LOST = text(
    """
    UPDATE capture_runs
       SET status = 'pending',
           locked_until = NULL,
           locked_by = NULL
     WHERE market_id = :market_id
       AND status = 'running'
       AND locked_until < now()
       AND attempts < :max_attempts
    RETURNING id
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("max_attempts", type_=SmallInteger()),
)
"""Ijarasi tugagan, LEKIN byudjeti qolgan qator QAYTARILADI (§B.5, 3-so'rov).

⚠ `attempts` TIKLANMAYDI: urinish HAQIQATAN bo'lgan (worker qatorni olgan
  va NVR ga borgan bo'lishi mumkin). Uni nolga qaytarish byudjetni
  ma'nosiz qilardi — cheksiz aylanadigan qator NVR ga cheksiz borardi.
"""

_RELEASE_EXHAUSTED = text(
    """
    UPDATE capture_runs
       SET status = 'failed',
           finished_at = now(),
           error_code = COALESCE(error_code, :lost_code)
     WHERE market_id = :market_id
       AND status = 'running'
       AND locked_until < now()
       AND attempts >= :max_attempts
    RETURNING id
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("max_attempts", type_=SmallInteger()),
    bindparam("lost_code", type_=Text()),
)
"""Ijarasi tugagan VA byudjeti tugagan qator YOPILADI (§B.5, 2-so'rov).

⚠ IKKI SO'ROV, BITTA `CASE` EMAS — `04-RESEARCH.md` §B.5 ning shakli
  saqlangan. Predikatlar `attempts` bo'yicha AJRALGAN (`<` va `>=`), ya'ni
  bir qator ikkalasiga ham tushmaydi va tartib ahamiyatsiz. Ikkalasi
  chaqiruvchining BITTA tranzaksiyasida bajariladi.

⚠ `COALESCE(error_code, ...)`: worker o'lishidan OLDIN sabab yozib
  ulgurgan bo'lsa o'sha sabab SAQLANADI. `capture_worker_lost` bilan
  bosib ketish aniqroq diagnostikani umumiyroq bilan almashtirardi.
"""

_LIST_DAY = text(
    """
    SELECT r.id            AS run_id,
           r.camera_id,
           cam.channel_no,
           cam.name        AS camera_name,
           cam.is_archived,
           r.slot_time,
           r.scheduled_at,
           r.status,
           r.attempts,
           r.error_code,
           s.quality_verdict,
           r.snapshot_id
      FROM capture_runs r
      JOIN cameras cam
        ON cam.market_id = r.market_id
       AND cam.id = r.camera_id
      LEFT JOIN snapshots s
        ON s.market_id = r.market_id
       AND s.capture_run_id = r.id
     WHERE r.market_id = :market_id
       AND r.business_date = :business_date
     ORDER BY cam.channel_no, r.slot_time
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("business_date", type_=Date()),
)
"""Kunning matritsasi — kamera x slot (`04-UI-SPEC.md` §6.4).

`LEFT JOIN snapshots`: kadri yo'q qatorda `quality_verdict` `NULL` bo'ladi
va hujayra C5–C9 holatlaridan birini oladi. `JOIN` (ichki) yozilsa
`missed`/`failed` qatorlar UMUMAN ko'rinmasdi — ya'ni matritsada bo'shliq
paydo bo'lardi va «ko'radigan narsa yo'q» degan taassurot berardi, holbuki
C6 aynan BIRINCHI DARAJALI holat.

TARTIB `channel_no` bo'yicha — `/cameras` sahifasi bilan BIR XIL
(`03-UI-SPEC.md` §6.1). Kamera nomini ikkinchi manbadan olish ikki
sahifada ikki xil tartib berardi.
"""

_DEFER = text(
    """
    UPDATE capture_runs
       SET status = 'pending',
           locked_until = now() + make_interval(secs => :seconds),
           locked_by = NULL,
           error_code = COALESCE(:code, error_code)
     WHERE market_id = :market_id
       AND id = :run_id
       AND status = 'running'
    RETURNING id
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("run_id", type_=PgUuid(as_uuid=True)),
    bindparam("seconds", type_=Integer()),
    bindparam("code", type_=Text()),
)
"""Kechiktirish — `scheduled_at` GA TEGMASDAN (T-04-35).

⚠ `COALESCE(:code, error_code)`: kod berilmasa mavjud sabab SAQLANADI.
  Uni `NULL` bilan bosib ketish oldingi urinishning diagnostikasini
  jimgina o'chirardi va operator «nega bu slot hamon kutmoqda?» degan
  savolga javob topolmasdi.

⚠ VAQT DB SOATIDAN (`now()`), ilova soatidan EMAS — modul tanlovi.
  `claim_due()` `locked_until` ni AYNAN DB `now()` bilan taqqoslaydi, ya'ni
  ikkinchi soat kiritish ikki mashinada kechikishni siljitardi.
  (`nvr_repo.finish_run` ilova soatini ishlatadi — u yerda hech qanday
  taqqoslash yo'q, faqat yozuv.)
"""


class CaptureRepository(TenantScopedRepository):
    """`capture_runs` ustidagi butun orkestratsiya yuzasi.

    Metodlar tik oqimining tartibida joylashgan: materializatsiya ->
    watchdog (ijara + yo'qlik) -> qulflab olish -> yakunlash -> o'qish.
    Tartib ATAYIN, chunki `04-PATTERNS.md` §3.3 dagi tik ham AYNAN shu
    ketma-ketlikda ishlaydi va kod uni o'qib chiqiladigan qilib qoldiradi.

    ⛔ O'CHIRISH METODI YO'Q — modul docstringining oxirgi bandiga qarang.
    """

    # ------------------------------------------------------------------
    # 1. Materializatsiya — yo'qlikni ko'rinadigan qiladigan YAGONA qadam
    # ------------------------------------------------------------------

    async def ensure_plan(self, business_date: date, *, grace_seconds: int) -> PlanResult:
        """Kunning `kamera x slot` rejasini IDEMPOTENT yozadi (CAM-05).

        Ikkinchi chaqiruv HECH NARSA yaratmaydi va istisno ham bermaydi:
        poyga `ON CONFLICT DO NOTHING` bilan DB'ga topshirilgan (modul
        docstringidagi 3-majburiyat).

        ⚠ TENANT KONTEKSTISIZ CHAQIRILSA `PlanResult(0, 0)` QAYTADI VA
          ISTISNO BO'LMAYDI — RLS `cameras`/`markets` ni ko'rsatmaydi, ya'ni
          `INSERT ... SELECT` manbasi bo'sh bo'ladi. Bu modul docstringidagi
          «eng jim xato sinfi» va u alohida test bilan o'lchanadi.

        Args:
            business_date: reja tuzilayotgan BIZNES-KUN. Bugun ham,
                ertaga ham bo'lishi mumkin — tik uni O'ZI beradi.
            grace_seconds: `skipped` chegarasi. `scheduled_at + grace <
                now()` bo'lgan slot `skipped` holatida tug'iladi.

        Returns:
            `PlanResult(created, skipped)` — ikkinchi son BIRINCHISINING
            ichida (`created >= skipped`).
        """
        result = await self.session.execute(
            _ENSURE_PLAN,
            {
                "market_id": self.market_id,
                "business_date": business_date,
                "grace_seconds": grace_seconds,
                "late_code": CAPTURE_PLAN_CREATED_LATE,
            },
        )
        statuses = [str(row.status) for row in result]
        return PlanResult(
            created=len(statuses),
            skipped=sum(status == CaptureRunStatus.SKIPPED.value for status in statuses),
        )

    # ------------------------------------------------------------------
    # 2. Watchdog — tikning BIRINCHI qadami, alohida job EMAS (§B.5)
    # ------------------------------------------------------------------

    async def release_expired(self, *, max_attempts: int) -> int:
        """Ijarasi tugagan `running` qatorlarni hal qiladi (§B.5, 2- va 3-so'rov).

        Byudjeti qolgani `pending` ga QAYTADI, tugagani esa `failed` +
        `capture_worker_lost` bilan YOPILADI. Ikkinchi shox majburiy: usiz
        «ijara qaytaradi» qoidasi cheksiz aylanishga aylanardi.

        ⛔ BU METOD `SKIP LOCKED` NING O'RNINI BOSMAYDI VA AKSINCHA — modul
           docstringidagi 1-majburiyatga qarang.

        Returns:
            Tegilgan qatorlarning UMUMIY soni (qaytarilgan + yopilgan).
            Ajratma kerak bo'lsa u `day_summary()` dan o'qiladi — bu
            metodning vazifasi holatni tozalash, hisobot berish emas.
        """
        requeued = await self.session.execute(
            _RELEASE_LOST, {"market_id": self.market_id, "max_attempts": max_attempts}
        )
        exhausted = await self.session.execute(
            _RELEASE_EXHAUSTED,
            {
                "market_id": self.market_id,
                "max_attempts": max_attempts,
                "lost_code": CAPTURE_WORKER_LOST,
            },
        )
        return len(requeued.all()) + len(exhausted.all())

    async def mark_missed(self, *, grace_seconds: int) -> list[MissedSlot]:
        """Grace oynasidan chiqqan `pending` slotlarni `missed` qiladi (§B.5, 1-so'rov).

        Qaytgan ro'yxat — ALERTNING YAGONA MANBAI (D-20). Bo'sh ro'yxat
        «hammasi joyida» degani va bu ma'lumot ham qimmatli: kunlik dayjest
        aynan shu nolga tayanadi.
        """
        result = await self.session.execute(
            _MARK_MISSED,
            {
                "market_id": self.market_id,
                "grace_seconds": grace_seconds,
                "missed_code": CAPTURE_SLOT_MISSED,
            },
        )
        return [
            MissedSlot(
                market_id=row.market_id,
                camera_id=row.camera_id,
                business_date=row.business_date,
                slot_time=row.slot_time,
            )
            for row in result
        ]

    # ------------------------------------------------------------------
    # 3. Qulflab olish — fazaning markaziy primitivi
    # ------------------------------------------------------------------

    async def claim_due(
        self,
        *,
        grace_seconds: int,
        lease_seconds: int,
        batch: int,
        worker_id: str,
    ) -> list[ClaimedRun]:
        """Muddati kelgan ishlarni QULFLAB oladi va `running` ga o'tkazadi.

        ⛔ CHAQIRUVCHI NATIJANI TRANZAKSIYA TUGAGANDAN KEYIN ISHLATADI.
           `04-PATTERNS.md` §3.3: navbatga qo'yish tranzaksiya ICHIDA
           bo'lsa, `COMMIT` yiqilganda vazifa allaqachon yuborilgan bo'lardi
           va worker mavjud bo'lmagan `running` qatorni izlardi. Shuning
           uchun bu metod ORM obyekti emas, tranzaksiyaga bog'lanmagan
           frozen dataclass qaytaradi.

        Args:
            grace_seconds: oynaning PASTKI chegarasi (undan chiqqan slot
                olinmaydi va `mark_missed()` uni yopadi).
            lease_seconds: ijara muddati. `grace_seconds` dan KICHIK
                bo'lishi kerak, aks holda yiqilgan worker slotni oyna
                tugagunicha ushlab turardi.
            batch: bitta tikdagi chegara — bazani uzoq bloklamaslik uchun.
            worker_id: FAQAT diagnostika uchun. Qulflash qarori
                `locked_until` ga tayanadi, bu qiymatga EMAS: nom bo'yicha
                qulflash worker qayta nomlanganda jimgina buzilardi.
        """
        result = await self.session.execute(
            _CLAIM_DUE,
            {
                "market_id": self.market_id,
                "grace_seconds": grace_seconds,
                "lease_seconds": lease_seconds,
                "batch": batch,
                "worker_id": worker_id,
            },
        )
        return [
            ClaimedRun(
                id=row.id,
                camera_id=row.camera_id,
                nvr_id=row.nvr_id,
                slot_time=row.slot_time,
                scheduled_at=row.scheduled_at,
                business_date=row.business_date,
                attempts=row.attempts,
            )
            for row in result
        ]

    # ------------------------------------------------------------------
    # 4. Yakunlash — shartli o'tish, `nvr_repo.start_run` naqshi
    # ------------------------------------------------------------------

    async def finish_succeeded(self, run_id: UUID, *, snapshot_id: UUID, method: str) -> bool:
        """`running` -> `succeeded` va kadr havolasi.

        ⚠ `status == 'running'` SHARTI DARVOZA, TOZALIK EMAS
          (`nvr_repo.start_run:534-565` bilan aynan bir xil mulohaza):
          navbat vazifani «kamida bir marta» yetkazadi, ya'ni bir xil
          `run_id` bilan ikkinchi chaqiruv MUMKIN. Shartsiz `UPDATE`
          yakunlangan qatorning `snapshot_id` ini qayta yozib, «qaysi biri
          dalil?» savolini javobsiz qoldirardi.

        ⚠ AVVAL S3 `PUT`, KEYIN `snapshots` qatori, KEYIN BU METOD (§B.4).
          Qator obyekt BORLIGINI tasdiqlaydi; teskari tartib 6-fazaga
          mavjud bo'lmagan dalilga havola berardi (BILL-02 uni ko'tara
          olmaydi).

        Returns:
            Qator `running` holatda topilib o'tgan bo'lsa `True`. `False` —
            qator yo'q, boshqa holatda yoki (tenant konteksti
            o'rnatilmagan bo'lsa) RLS uni ko'rsatmadi.
        """
        result = await self.session.execute(
            update(CaptureRun)
            .where(
                CaptureRun.market_id == self.market_id,
                CaptureRun.id == run_id,
                CaptureRun.status == CaptureRunStatus.RUNNING.value,
            )
            .values(
                status=CaptureRunStatus.SUCCEEDED.value,
                # ⚠ VAQT DB SOATIDAN. Bu modulda BARCHA vaqt tamg'alari
                #   `now()` dan olinadi, chunki watchdog so'rovlari ham
                #   AYNAN o'sha soatga qarab qaror qiladi — ikkinchi soat
                #   (ilovaniki) ikki mashinada chegaralarni siljitardi.
                finished_at=func.now(),
                snapshot_id=snapshot_id,
                capture_method=method,
                locked_until=None,
                locked_by=None,
                error_code=None,
                error_detail=None,
            )
            .returning(CaptureRun.id)
        )
        return result.scalar_one_or_none() is not None

    async def finish_failed(
        self,
        run_id: UUID,
        code: str,
        detail: dict[str, Any] | None = None,
        *,
        max_attempts: int,
    ) -> bool:
        """Urinish yiqildi: kodga qarab QAYTA URINISH yoki DARHOL YOPISH.

        ⛔ T-04-34 — `CAPTURE_AUTH_LOCKING_CODES` DAGI KOD BYUDJETNI TO'LIQ
           YOQADI. Arifmetika shafqatsiz: tik har DAQIQADA ishlaydi, 25
           kamera x 10 tik = 250 muvaffaqiyatsiz autentifikatsiya va
           Hikvision hisobni ~5 urinishdan keyin 30 daqiqaga QULFLAYDI —
           undan keyin TO'G'RI PAROL HAM ishlamaydi. Tizim o'zining
           tuzatish yo'lini o'zi yopib qo'yardi va buni butun bozorning har
           bir kamerasi uchun qilardi.

        ⚠ QOLGAN KODLARDA byudjet qarori `attempts` NING JORIY qiymatiga
          qarab SQL ICHIDA hal qilinadi. Uni Python'da hal qilish avval
          o'qishni talab qilardi va o'sha o'qish bilan yozish orasida
          `release_expired()` qatorni qaytarib yuborishi mumkin edi.

        ⚠ `error_detail` YOZISHDAN OLDIN `mask_sensitive()` DAN O'TADI
          (T-04-39, §S-7). Bu `jsonb` ga diagnostika uchun xom javob
          tushadi va unda rekvizit qoldig'i bo'lishi mumkin. Filtr FAQAT
          kalit nomiga qaraydi (ichma-ich obyektlarni ham qamraydi), ya'ni
          parol bu yerga NOMLANGAN kalit sifatida tushishi shart —
          formatlangan matn ichida hech qachon.

        Raises:
            ValueError: `code` reyestrda bo'lmasa. Kod bazaga tushib ketsa
                API uni tanimay `errors.generic` qaytarardi va sabab FAQAT
                foydalanuvchi ekranida yo'qolardi (§S-5).
        """
        _require_known_code(code)

        values: dict[str, Any] = {
            "locked_until": None,
            "locked_by": None,
            "error_code": code,
            "error_detail": mask_sensitive(detail) if detail is not None else None,
        }
        if code in CAPTURE_AUTH_LOCKING_CODES:
            # ⛔ QAYTA URINISH TAQIQLANADI: byudjet TO'LIQ yoqiladi, ya'ni
            #    `release_expired()` ham, keyingi tik ham bu qatorga
            #    qaytmaydi. Shart Python'da hal bo'ladi va bu to'g'ri —
            #    u qator holatiga emas, KODNING O'ZIGA bog'liq.
            values["attempts"] = max_attempts
            values["status"] = CaptureRunStatus.FAILED.value
            values["finished_at"] = func.now()
        else:
            # Byudjet qarori esa qatorning JORIY `attempts` iga bog'liq,
            # ya'ni u SQL ichida hal bo'lishi SHART: avval o'qib, keyin
            # yozish orasida `release_expired()` qatorni qaytarib yuborishi
            # mumkin edi.
            terminal = CaptureRun.attempts >= max_attempts
            values["status"] = case(
                (terminal, CaptureRunStatus.FAILED.value),
                else_=CaptureRunStatus.PENDING.value,
            )
            values["finished_at"] = case((terminal, func.now()), else_=None)

        result = await self.session.execute(
            update(CaptureRun)
            .where(
                CaptureRun.market_id == self.market_id,
                CaptureRun.id == run_id,
                CaptureRun.status == CaptureRunStatus.RUNNING.value,
            )
            .values(**values)
            .returning(CaptureRun.id)
        )
        return result.scalar_one_or_none() is not None

    async def defer(self, run_id: UUID, seconds: int, *, code: str | None = None) -> bool:
        """Qatorni `pending` da QOLDIRIB, keyingi tikni kechiktiradi (T-04-35).

        ⛔ `scheduled_at` O'ZGARMAYDI VA BU BANDNING YURAGI. Uni surish
           slotning biznes identitetini buzardi: `business_date` aynan shu
           ustundan hosila va 06:00 sloti hisobotda boshqa vaqt bo'lib
           chiqardi. Kechikish FAQAT `locked_until` orqali beriladi va uni
           `claim_due()` ning `locked_until` predikati hurmat qiladi.

        ⚠ NEGA `failed` EMAS: `capture_stream_limit` da NVR shunchaki band.
          Oqim bo'shagach kadr olish MUVAFFAQIYATLI bo'ladi, ya'ni slotni
          tashlab yuborish «NVR band edi» sababini «kadr yo'q» ga
          aylantirardi.

        ⚠ `attempts` KAMAYTIRILMAYDI: kechiktirish ham urinish sarfi.
          Chegara baribir grace oynasi — oyna tugagach slot `mark_missed()`
          bilan yopiladi va cheksiz aylanish mumkin emas.

        Args:
            seconds: keyingi tikgacha bo'lgan kechikish.
            code: ixtiyoriy diagnostika kodi. Berilsa u
                `CAPTURE_DEFER_CODES` da bo'lishi SHART.

        Raises:
            ValueError: kod reyestrda yo'q yoki u kechiktirish kodi emas.
                Ikkinchi shart darvoza: `capture_bad_credentials` ni
                kechiktirish T-04-34 ning butun himoyasini bitta noto'g'ri
                chaqiruv bilan chetlab o'tardi.
        """
        if code is not None:
            _require_known_code(code)
            if code not in CAPTURE_DEFER_CODES:
                raise ValueError(
                    f"error_code={code!r} kechiktirish kodi emas. Ruxsat etilganlar: "
                    f"{sorted(CAPTURE_DEFER_CODES)}. Qulflovchi kod uchun "
                    "`finish_failed()` ishlatiladi."
                )

        result = await self.session.execute(
            _DEFER,
            {
                "market_id": self.market_id,
                "run_id": run_id,
                "seconds": seconds,
                "code": code,
            },
        )
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    # 5. O'qish — UI va dayjest
    # ------------------------------------------------------------------

    async def day_summary(self, business_date: date) -> DaySummary:
        """Kunning oltala hisoblagichi + `planned`/`done` (`04-UI-SPEC.md` §6.3).

        ⛔ NOL HISOBLAGICH HAM QAYTARILADI. Ifodalar `count(*) FILTER
           (WHERE ...)` shaklida quriladi (`func.count().filter(...)`), ya'ni
           natija HAR DOIM bitta qator va har bir maydon to'ldirilgan.
           `GROUP BY status` bilan yig'ilgan variant nol hisoblagichni
           umuman qatorsiz qoldirardi va UI'da «buzuq kadr yo'q» bilan
           «buzuq kadr sanalmagan» bir xil ko'rinardi.

        ⚠ VERDIKTLAR `snapshots` DAN, `capture_runs` DAN EMAS: `succeeded`
          qator kadr OLINGANINI aytadi, uning YAROQLILIGINI esa faqat
          `quality_verdict` aytadi. Ikkalasini bir ustunga yig'ish D-16
          ning `is_billable` ilgagini ma'nosiz qilardi.

        ⚠ ARXIVLANGAN KAMERA CHIQARILMAYDI — `list_day()` bilan bir xil
          qaror va bir xil sabab (`RunRow` docstringi): xulosa va matritsa
          BIR XIL to'plamni sanashi shart.
        """
        joined = (
            select(
                func.count().label("planned"),
                _count_where(CaptureRun.status == CaptureRunStatus.SUCCEEDED.value, "done"),
                _count_where(Snapshot.quality_verdict == SnapshotQuality.OK.value, "ok"),
                _count_where(Snapshot.quality_verdict == SnapshotQuality.DARK.value, "dark"),
                _count_where(Snapshot.quality_verdict == SnapshotQuality.BLANK.value, "blank"),
                _count_where(Snapshot.quality_verdict == SnapshotQuality.CORRUPT.value, "corrupt"),
                _count_where(CaptureRun.status == CaptureRunStatus.FAILED.value, "failed"),
                _count_where(CaptureRun.status == CaptureRunStatus.MISSED.value, "missed"),
            )
            .select_from(CaptureRun)
            .outerjoin(
                Snapshot,
                and_(
                    Snapshot.market_id == CaptureRun.market_id,
                    Snapshot.capture_run_id == CaptureRun.id,
                ),
            )
            .where(
                CaptureRun.market_id == self.market_id,
                CaptureRun.business_date == business_date,
            )
        )
        row = (await self.session.execute(joined)).one()
        return DaySummary(
            planned=int(row.planned),
            done=int(row.done),
            ok=int(row.ok),
            dark=int(row.dark),
            blank=int(row.blank),
            corrupt=int(row.corrupt),
            failed=int(row.failed),
            missed=int(row.missed),
        )

    async def list_day(self, business_date: date) -> list[RunRow]:
        """Kunning matritsa qatorlari, `channel_no` bo'yicha (`04-UI-SPEC.md` §6.4)."""
        result = await self.session.execute(
            _LIST_DAY, {"market_id": self.market_id, "business_date": business_date}
        )
        return [
            RunRow(
                run_id=row.run_id,
                camera_id=row.camera_id,
                channel_no=row.channel_no,
                camera_name=row.camera_name,
                is_archived=bool(row.is_archived),
                slot_time=row.slot_time,
                scheduled_at=row.scheduled_at,
                status=row.status,
                attempts=row.attempts,
                error_code=row.error_code,
                quality_verdict=row.quality_verdict,
                snapshot_id=row.snapshot_id,
            )
            for row in result
        ]

    async def cameras_in_plan(self, business_date: date) -> Sequence[UUID]:
        """Shu kunning rejasidagi NOYOB kameralar — dayjest va alert uchun.

        Alohida metod, chunki `list_day()` ni chaqirib Python'da noyoblash
        175 qatorni tarmoqdan olib kelardi; savol esa faqat «qaysi
        kameralar?» edi.
        """
        result = await self.session.execute(
            select(CaptureRun.camera_id)
            .where(
                CaptureRun.market_id == self.market_id,
                CaptureRun.business_date == business_date,
            )
            .distinct()
            .order_by(CaptureRun.camera_id)
        )
        return list(result.scalars().all())


def _count_where(condition: Any, label: str) -> Any:
    """`count(*) FILTER (WHERE <condition>) AS <label>`.

    Alohida yordamchi, chunki u `day_summary()` da SAKKIZ marta uchraydi va
    takror `.filter(...)` zanjirining bittasida `filter` ni unutish
    hisoblagichni JIMGINA `planned` ga tenglashtirardi — ya'ni xato
    natijaga o'xshab ko'rinardi, xatoga emas.
    """
    return func.count().filter(condition).label(label)


def _require_known_code(code: str) -> None:
    """Kod reyestrda bo'lishi SHART (§S-5).

    `assert` EMAS, `ValueError`: `assert` `python -O` bilan o'chib ketadi va
    u holda allowlist aynan ishlab chiqarishda jimgina yo'qolardi
    (`CaptureError.__init__` bilan bir xil qaror va bir xil sabab).
    """
    if code not in CAPTURE_ERROR_META:
        raise ValueError(
            f"noma'lum error_code={code!r}. Ruxsat etilganlar reyestri: "
            f"`app/services/capture_errors.py::CAPTURE_ERROR_CODES` "
            f"({len(CAPTURE_ERROR_CODES)} ta)."
        )
