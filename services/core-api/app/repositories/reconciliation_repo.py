"""Nomuvofiqlik case'lari — «raqamni jarayonga aylantirish» ning arifmetikasi (RECON-02).

=============================================================================
1. NOMUVOFIQLIK IKKI SINF VA ULAR BIR JADVALDAN KELMAYDI (Pattern 4).

    Sinf B — «ro'yxatga olinmagan savdo». Manba `billing_anomalies`
        QATORI, ya'ni o'zgarmas dalil allaqachon yozilgan va case unga
        MUZLATILGAN POINTER bilan bog'lanadi.

    Sinf A — «band, lekin to'lovsiz». Manba QATOR EMAS, HOSILA:
        `daily_charges` − `payments`. Hisob o'zgarmas, «to'landimi?»
        savolining javobi esa O'ZGARUVCHAN.

⛔ SINF A UCHUN TO'RTINCHI `AnomalyKind` QO'SHILMAYDI. `billing_close`
   04:10 da ishlaydi, o'sha kunning to'lovlari esa hali kelmagan —
   «to'lanmagan» ni o'sha paytda QATOR qilib yozish ertaga to'lov
   kelganda YOLG'ONGA aylanadigan saqlangan hosila bo'lardi (D-06/D-13
   aynan shu sinfni taqiqlaydi). Case esa JARAYON: uning o'zgarishi
   KUTILGAN va u o'zgarmas hisobga faqat KO'RSATKICH bilan bog'lanadi.

=============================================================================
2. ⛔ SINF A UCHUN KECHIKISH CHEGARASI MAJBURIY (Pattern 5).

Chegarasiz har ertalab HAR hisob uchun case ochilardi — to'lov kun
davomida keladi, ya'ni ertalabki holat hamma sotuvchini «qarzdor» deb
ko'rsatardi va navbat birinchi haftada SHOVQINGA aylanardi.
`app/jobs/alerting.py` bu nosozlik sinfini raqam bilan yozgan (D-22:
«75 ta xabar olgan admin ertasi kuni bildirishnomani o'chiradi»).

⛔ Chegara — `market_notification_settings.overdue_days`, ya'ni BOT-03
   (sotuvchi eslatmasi) bilan AYNAN BIR KNOB. Ikki alohida sozlama
   ajralib ketardi va sotuvchi eslatma OLMAGAN qarz uchun case
   ochilardi — u ogohlantirilmagan holda navbatga tushardi.

=============================================================================
3. ⛔ «TO'LANMAGAN» NING TA'RIFI SHU FAYLDA IXTIRO QILINMAYDI.

Sinf A predikati IKKI mahsulot funksiyasidan chiqadi va ikkalasi ham
`billing_repo` da yashaydi:

    `vendor_outstanding()`       — BILL-03 ning hisoblanadigan qoldig'i;
    `vendor_charge_allocation()` — D-24 ning `FIFO_OLDEST_SERVICE_DATE_FIRST`
                                   taqsimlashi, ya'ni «qaysi kun to'landi?».

Yangi SQL yozish ikkinchi haqiqat manbai bo'lardi: ikki joyda yozilgan
«to'lanmagan» ta'rifi BIR KUN ajralib ketardi va o'shanda bot bir sonni,
hisobot boshqa sonni ko'rsatardi — ikkalasi ham «to'g'ri» bo'lib.

=============================================================================
4. ⛔ `no_coverage_stall` GA CASE OCHILMAYDI (Pattern 4).

U KAMERA QAMROVI NUQSONI, tushum nomuvofiqligi EMAS. `06-UI-SPEC.md`
§11.4 u uchun dalil affordansini UMUMAN chizmaydi, ya'ni navbatga
tushgan qatorni nazoratchi TEKSHIRA OLMASDI ham. Uni qamrash navbatni
har kuni KO'R NUQTALAR bilan to'ldirardi va nazoratchining diqqati
(5-fazaning D-10 byudjeti) haqiqiy nomuvofiqlikdan chalg'irdi.

Ro'yxat literal EMAS — `CASE_WORTHY_ANOMALY_KINDS` `AnomalyKind` dan
ITERATSIYA bilan quriladi (pastdagi docstring).

=============================================================================
5. ⛔ HIT-RATE — HOSILA, USTUN EMAS (D-13). Nisbat `justified /
   (justified + unjustified)`; `new`/`in_review` maxrajga KIRMAYDI va
   o'lchov yo'q bo'lganda javob `None`, nol EMAS. Sabab `hit_rate()`
   docstringida.

=============================================================================
6. ⛔ HOLAT O'ZGARISHI HAR DOIM AUDIT QATORI BILAN JUFT (D-14):
   `reconciliation_case_events` ga YANGI QATOR yoziladi, mavjud qator
   TAHRIRLANMAYDI. Jadval `0023` ning o'zgarmaslik triggeri bilan
   qulflangan, ya'ni «tahrir qilaman» degan yo'l STRUKTURAVIY yopiq.

=============================================================================
⚠ PUL BU FAYLDA HISOBLANMAYDI. Summalar `billing_repo` dan keladi va bu
  modul faqat ULARNING NATIJASIDAN («qoplandimi?») foydalanadi. Saqlangan
  qoldiq ustuni ham, kasrli tip ham, yaxlitlash chaqiruvi ham bu yerga
  tarqamaydi (G7-8 buni AST bilan o'lchaydi).

⚠ DALIL — FAQAT IDENTIFIKATOR. `case_evidence()` bayt ham, imzolangan
  havola ham qaytarmaydi (D-03, T-06-81) — sabab o'sha funksiyaning
  docstringida.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Final

from sbozor_core.enums import AnomalyKind, ReconciliationCaseStatus, ReconciliationSubjectKind
from sqlalchemy import ARRAY, Date, DateTime, Integer, Text, bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.repositories.billing_repo import vendor_charge_allocation, vendor_outstanding

if TYPE_CHECKING:
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "CASE_PAGE_SIZE",
    "CASE_WORTHY_ANOMALY_KINDS",
    "NON_CASE_ANOMALY_KINDS",
    "CaseCursor",
    "CaseEvidence",
    "CaseListPage",
    "CaseRow",
    "CaseTransition",
    "HitRate",
    "OpenCasesResult",
    "case_evidence",
    "hit_rate",
    "list_cases",
    "open_cases",
    "transition",
]

_UUID = PgUuid(as_uuid=True)
_UUID_ARRAY = ARRAY(PgUuid(as_uuid=True))
_TEXT_ARRAY = ARRAY(Text())
_TIMESTAMPTZ = DateTime(timezone=True)

NON_CASE_ANOMALY_KINDS: Final[frozenset[AnomalyKind]] = frozenset({AnomalyKind.NO_COVERAGE_STALL})
"""⛔ NAVBATGA TUSHMAYDIGAN anomaliya sinflari — TAQIQ RO'YXATI, ruxsat emas.

Taqiq ro'yxati ATAYIN: `AnomalyKind` ga kelajakda YANGI a'zo qo'shilsa u
AVTOMATIK ravishda case ochadigan bo'ladi. Teskarisi (ruxsat ro'yxati)
yangi a'zoni JIMGINA tashlab ketardi — nomuvofiqlik navbati o'sha kundan
boshlab bir sinfni umuman ko'rmay qo'yardi va sabab hech qayerda
ko'rinmasdi.

`no_coverage_stall` bu yerda YOLG'IZ va sabab modul docstringining
4-bandida: u kamera qamrovi nuqsoni, tushum nomuvofiqligi emas.
"""

CASE_WORTHY_ANOMALY_KINDS: Final[tuple[str, ...]] = tuple(
    kind.value for kind in AnomalyKind if kind not in NON_CASE_ANOMALY_KINDS
)
"""Case ochiladigan anomaliya sinflari — ⛔ ENUMDAN ITERATSIYA, literal EMAS.

Qo'lda yozilgan `('unassigned_occupied', 'closed_day_occupied')` kortej
`AnomalyKind` o'zgargan kuni JIMGINA eskirardi: so'rov ishlayverardi,
faqat natija bo'sh (yoki to'liqsiz) bo'lardi — `billing_repo._OCCUPIED`
docstringida o'lchangan aynan o'sha sinf.
"""

CASE_PAGE_SIZE: Final[int] = 50
"""Navbat sahifasining o'lchami (DQ-4) — `ChargeListResponse` naqshi bilan bir xil."""

_STATUS_NEW: Final[str] = ReconciliationCaseStatus.NEW.value
_STATUS_IN_REVIEW: Final[str] = ReconciliationCaseStatus.IN_REVIEW.value
_STATUS_JUSTIFIED: Final[str] = ReconciliationCaseStatus.JUSTIFIED.value
_STATUS_UNJUSTIFIED: Final[str] = ReconciliationCaseStatus.UNJUSTIFIED.value
"""Holat qiymatlari SO'ROV PARAMETRI bo'lib beriladi, so'rov MATNIDAGI literal emas.

`billing_repo._OCCUPIED` / `occupancy_repo` da o'rnatilgan qoida: matnga
yozilgan literal enum o'zgargan kuni filtr jimgina hech nimaga tushmasdi.
"""

_PENDING_STATUSES: Final[tuple[str, ...]] = (_STATUS_NEW, _STATUS_IN_REVIEW)
"""⛔ HIT-RATE MAXRAJIGA KIRMAYDIGAN holatlar (D-13) — `hit_rate()` docstringi."""

_SUBJECT_ANOMALY: Final[str] = ReconciliationSubjectKind.ANOMALY.value
_SUBJECT_UNPAID: Final[str] = ReconciliationSubjectKind.OCCUPIED_UNPAID.value


# ===========================================================================
# 1. CASE OCHISH — IKKI MUSTAQIL `INSERT ... SELECT`, BITTA TRANZAKSIYA
# ===========================================================================

_OPEN_ANOMALY_CASES = text(
    """
    WITH candidates AS (
        SELECT a.id           AS anomaly_id,
               a.service_date AS service_date
          FROM billing_anomalies a
         WHERE a.market_id = :market_id
           AND a.service_date = :business_date
           AND a.kind = ANY(:case_kinds)
    ), inserted AS (
        INSERT INTO reconciliation_cases
                    (market_id, subject_kind, anomaly_id, service_date, status)
        SELECT :market_id, :subject_kind, c.anomaly_id, c.service_date, :status_new
          FROM candidates c
        ON CONFLICT (market_id, anomaly_id) WHERE anomaly_id IS NOT NULL
        DO NOTHING
        RETURNING 1 AS written
    )
    SELECT (SELECT count(*) FROM candidates)::int AS candidates,
           (SELECT count(*) FROM inserted)::int   AS inserted
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
    bindparam("case_kinds", type_=_TEXT_ARRAY),
    bindparam("subject_kind", type_=Text()),
    bindparam("status_new", type_=Text()),
)
"""SINF B — «ro'yxatga olinmagan savdo» case'lari.

⛔ IDEMPOTENTLIK KONSTRAYTDA, ILOVA INTIZOMIDA EMAS (D-21). `ON CONFLICT
   ... DO NOTHING` nishoni — `uq_reconciliation_cases_anomaly` QISMAN
   indeksi, shuning uchun predikat (`WHERE anomaly_id IS NOT NULL`)
   inferensiyada ham TAKRORLANADI: usiz PG indeksni topa olmasdi.

⛔ «TEKSHIR-KEYIN-YOZ» EMAS (`capture_repo` da o'rnatilgan majburiyat):
   alohida `SELECT` yo'q, ya'ni poyga oynasi ham yo'q. `recon.open`
   KONVERGENT — o'sha kun uchun qayta-qayta yugurishi NORMAL holat va
   ikki parallel yugurish ikkinchi case'ni STRUKTURAVIY yoza olmaydi.

⚠ IKKI SON BITTA BORISHDA: `candidates` — nomzodlar, `inserted` —
  HAQIQATAN yozilganlar. Farqi `skipped_existing`. Sanoqni ikkinchi
  so'rov bilan olish qayta yugurishda BOSHQA oynani o'lchagan bo'lardi.

⚠ `service_date` NOMZOD QATORDAN (`a.service_date`), argumentdan EMAS:
  ikki manba bir kun ajralib ketardi va case «boshqa kunning» dalilini
  ko'rsatardi.
"""

_OVERDUE_CHARGES = text(
    """
    SELECT c.id           AS charge_id,
           c.vendor_id    AS vendor_id,
           c.service_date AS service_date,
           s.code         AS stall_code
      FROM daily_charges c
      JOIN stalls s
        ON s.market_id = c.market_id
       AND s.id = c.stall_id
     WHERE c.market_id = :market_id
       AND c.vendor_id = ANY(:vendor_ids)
       AND c.service_date <= :cutoff
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("vendor_ids", type_=_UUID_ARRAY),
    bindparam("cutoff", type_=Date()),
)
"""KECHIKKAN hisoblar va ularning `(sotuvchi, kun, rasta kodi)` kaliti.

⚠ `stall_code` KERAK, chunki `vendor_charge_allocation()` natijasi AYNAN
  shu kalit bilan qaytadi (`ChargeDue` — `stall_code`, `stall_id` EMAS:
  UUID tartibni tasodifiy qilardi). Ya'ni bu so'rov taqsimlash
  natijasini `daily_charges.id` ga qaytarib bog'laydigan YAGONA ko'prik.

⚠ FILTR SHU YERDA: kechikmagan hisob xaritaga umuman KIRMAYDI, ya'ni
  taqsimlash uni «to'lanmagan» deb ko'rsatsa ham case ochilmaydi.
  Chegara Pattern 5 ning butun mazmuni (modul docstringining 2-bandi).

⚠ `vendor_id IS NULL` bo'lgan hisob `= ANY(...)` bilan CHIQIB KETADI va
  bu to'g'ri: sotuvchisi noma'lum bandlik D-28 ning anomaliyasi, ya'ni u
  SINF B dan keladi.
"""

_OPEN_UNPAID_CASES = text(
    """
    WITH candidates AS (
        SELECT c.id           AS charge_id,
               c.service_date AS service_date
          FROM daily_charges c
         WHERE c.market_id = :market_id
           AND c.id = ANY(:charge_ids)
    ), inserted AS (
        INSERT INTO reconciliation_cases
                    (market_id, subject_kind, charge_id, service_date, status)
        SELECT :market_id, :subject_kind, c.charge_id, c.service_date, :status_new
          FROM candidates c
        ON CONFLICT (market_id, charge_id) WHERE charge_id IS NOT NULL
        DO NOTHING
        RETURNING 1 AS written
    )
    SELECT (SELECT count(*) FROM candidates)::int AS candidates,
           (SELECT count(*) FROM inserted)::int   AS inserted
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("charge_ids", type_=_UUID_ARRAY),
    bindparam("subject_kind", type_=Text()),
    bindparam("status_new", type_=Text()),
)
"""SINF A — «band, lekin to'lovsiz» case'lari.

⛔ NISHONLAR RO'YXATI SHU SO'ROVDA HISOBLANMAYDI: u
   `vendor_outstanding()` + `vendor_charge_allocation()` dan keladi
   (modul docstringining 3-bandi). Bu so'rov faqat YOZADI — «to'lanmagan»
   ning ta'rifi bu yerda IXTIRO QILINMAYDI.

⛔ Idempotentlik jufti — `uq_reconciliation_cases_charge` qisman
   indeksi; sabab `_OPEN_ANOMALY_CASES` docstringi bilan bir xil.
"""


@dataclass(slots=True)
class OpenCasesResult:
    """Bitta bozorning bitta yugurishi — ⛔ NOL — NATIJA.

    HAMMA maydon HAR DOIM qaytariladi (`BillingCloseResult` /
    `DayCloseResult` qoidasi): chaqiruvchi «nega case yo'q?» savoliga
    javobni YONIDA topadi va ikkinchi so'rov yubormaydi.
    """

    anomaly_cases: int = 0
    """SINF B — `billing_anomalies` dan ochilgan YANGI case'lar."""
    unpaid_cases: int = 0
    """SINF A — kechikkan to'lanmagan hisoblar uchun ochilgan YANGI case'lar."""
    skipped_existing: int = 0
    """⛔ Case ALLAQACHON bor edi — qisman UNIQUE indeks konfliktga urildi.

    ⚠ BU XATO EMAS, KONVERGENTLIKNING O'LCHOVI: `recon.open` o'sha kun
      uchun qayta yugurishi NORMAL holat va bu son aynan «qayta yugurish
      hech nimani buzmadi» degan da'voni raqamga aylantiradi. Uni
      `anomaly_cases` ga qo'shish kunlik dayjestda case sonini OSHIRIB
      ko'rsatardi.
    """


async def open_cases(
    session: AsyncSession,
    *,
    market_id: UUID,
    business_date: date,
    overdue_days: int,
) -> OpenCasesResult:
    """Ikkala sinf uchun ham case ochadi — IDEMPOTENT, bitta tranzaksiyada.

    Args:
        market_id: bozor; sessiyada tenant konteksti O'RNATILGAN bo'lishi
            shart (RLS beshala jadvalda `FORCE` bilan yoqilgan).
        business_date: qaysi kun tekshiriladi. ⛔ ARGUMENT, funksiya
            ichida hisoblanmaydi (`billing_close` / `day_close` qoidasi).
        overdue_days: SINF A ning kechikish chegarasi —
            `market_notification_settings.overdue_days`. ⛔ MAJBURIY va
            standart qiymati YO'Q: chaqiruvchi uni bozor sozlamasidan
            o'qishi SHART (modul docstringining 2-bandi). Standart
            argument bu yerda «chegara unutilgan» holatini «chegara
            qo'yilgan» dan ajratib bo'lmas qilardi.

    Returns:
        `OpenCasesResult` — ikki sinfning sanog'i va o'tkazib yuborilgan
        (allaqachon mavjud) case'lar.

    Raises:
        ValueError: `overdue_days` musbat bo'lmaganda. Sxema uni
            `ck_market_notification_settings_overdue_days_positive` bilan
            allaqachon qulflagan, lekin funksiya `COALESCE` orqali kelgan
            kod standartini ham SHU YERDA rad etadi — aks holda noldagi
            chegara butun navbatni shovqinga aylantirardi va sabab
            sozlamada emas, KODDA bo'lardi.
    """
    if overdue_days < 1:
        raise ValueError(
            f"`overdue_days` musbat bo'lishi shart (berilgani: {overdue_days}). "
            "Nol yoki manfiy chegara HAR hisob uchun case ochardi — to'lov kun "
            "davomida keladi, ya'ni ertalabki holat hamma sotuvchini qarzdor "
            "deb ko'rsatardi va navbat birinchi haftada shovqinga aylanardi "
            "(Pattern 5 / D-22)."
        )

    anomaly_written, anomaly_skipped = await _open_anomaly_cases(
        session, market_id=market_id, business_date=business_date
    )
    unpaid_written, unpaid_skipped = await _open_unpaid_cases(
        session, market_id=market_id, business_date=business_date, overdue_days=overdue_days
    )
    return OpenCasesResult(
        anomaly_cases=anomaly_written,
        unpaid_cases=unpaid_written,
        skipped_existing=anomaly_skipped + unpaid_skipped,
    )


async def _open_anomaly_cases(
    session: AsyncSession, *, market_id: UUID, business_date: date
) -> tuple[int, int]:
    """SINF B — `_OPEN_ANOMALY_CASES` ning qobig'i.

    Returns:
        `(yozilgan, o'tkazib yuborilgan)`.
    """
    row = (
        (
            await session.execute(
                _OPEN_ANOMALY_CASES,
                {
                    "market_id": market_id,
                    "business_date": business_date,
                    "case_kinds": list(CASE_WORTHY_ANOMALY_KINDS),
                    "subject_kind": _SUBJECT_ANOMALY,
                    "status_new": _STATUS_NEW,
                },
            )
        )
        .mappings()
        .one()
    )
    written = int(row["inserted"])
    return written, int(row["candidates"]) - written


async def _open_unpaid_cases(
    session: AsyncSession, *, market_id: UUID, business_date: date, overdue_days: int
) -> tuple[int, int]:
    """SINF A — «to'lanmagan» ning ta'rifi MAHSULOT FUNKSIYALARIDAN chiqadi.

    =======================================================================
    ⛔ UCH QADAM VA HECH BIRIDA YANGI ARIFMETIKA YO'Q:

      1. `vendor_outstanding()` — qaysi sotuvchida qoldiq bor (BILL-03).
         Qoldig'i musbat bo'lmagan sotuvchi keyingi qadamga UMUMAN
         kirmaydi, ya'ni to'liq to'lagan sotuvchida case ochilmaydi.
      2. `vendor_charge_allocation()` — o'sha sotuvchining KREDITI QAYSI
         KUNLARNI yopdi (`FIFO_OLDEST_SERVICE_DATE_FIRST`, D-24). Yopilgan
         kun case ochmaydi.
      3. `_OVERDUE_CHARGES` — taqsimlash natijasini `daily_charges.id` ga
         qaytarib bog'laydi VA kechikish chegarasini qo'llaydi.

    ⚠ IKKINCHI QADAM SOTUVCHI KESIMIDA VA U N+1 SO'ROV BERADI. Narx ONGLI
      QABUL QILINGAN: yagona muqobil — taqsimlash qoidasini oyna funksiyasi
      bilan SQL da qayta yozish, ya'ni `FIFO_OLDEST_SERVICE_DATE_FIRST`
      ning IKKINCHI NUSXASI. `allocate_charge_credit()` docstringi bu
      vasvasani nomma-nom taqiqlaydi, `sbozor_core.billing.ALLOCATION_RULE`
      esa qoidaning YAGONA egasi. Job kechasi bir marta yuguradi va
      qarzdorlar soni bozordagi sotuvchilar sonidan katta emas.

    ⚠ QADAMLARNING TARTIBI HAM MUHIM: chegara ENG OXIRIDA qo'llanadi.
      Uni birinchi qadamga surish qoldiqni FAQAT eski hisoblardan
      hisoblardi va bugungi to'lov eski qarzni yopgan sotuvchi baribir
      qarzdor bo'lib ko'rinardi (`_VENDOR_OUTSTANDING` ning `as_of`
      bandidagi bilan aynan bir xil tuzoq).
    =======================================================================

    Returns:
        `(yozilgan, o'tkazib yuborilgan)`.
    """
    outstanding = await vendor_outstanding(session, market_id=market_id)
    debtors = [vendor_id for vendor_id, soum in outstanding.items() if soum > 0]
    if not debtors:
        return 0, 0

    cutoff = business_date - timedelta(days=overdue_days)
    rows = (
        await session.execute(
            _OVERDUE_CHARGES,
            {"market_id": market_id, "vendor_ids": debtors, "cutoff": cutoff},
        )
    ).mappings()
    overdue: dict[tuple[UUID, date, str], UUID] = {
        (row["vendor_id"], row["service_date"], str(row["stall_code"])): row["charge_id"]
        for row in rows
    }
    if not overdue:
        return 0, 0

    charge_ids: list[UUID] = []
    for vendor_id in debtors:
        allocation = await vendor_charge_allocation(
            session, market_id=market_id, vendor_id=vendor_id
        )
        for allocated in allocation.rows:
            if allocated.unpaid_soum <= 0:
                # Kredit bu kunni TO'LIQ yopgan — case ochilmaydi.
                continue
            charge_id = overdue.get((vendor_id, allocated.service_date, allocated.stall_code))
            if charge_id is None:
                # Hisob KECHIKMAGAN (yoki bu bozorniki emas) — Pattern 5.
                continue
            charge_ids.append(charge_id)

    if not charge_ids:
        return 0, 0

    row = (
        (
            await session.execute(
                _OPEN_UNPAID_CASES,
                {
                    "market_id": market_id,
                    "charge_ids": charge_ids,
                    "subject_kind": _SUBJECT_UNPAID,
                    "status_new": _STATUS_NEW,
                },
            )
        )
        .mappings()
        .one()
    )
    written = int(row["inserted"])
    return written, int(row["candidates"]) - written


# ===========================================================================
# 2. NAVBAT RO'YXATI — KUN KESIMI + KEYSET (DQ-4)
# ===========================================================================

_CASE_ROWS = text(
    """
    SELECT rc.id               AS case_id,
           rc.subject_kind     AS subject_kind,
           rc.anomaly_id       AS anomaly_id,
           rc.charge_id        AS charge_id,
           rc.service_date     AS service_date,
           rc.status           AS status,
           rc.assignee_user_id AS assignee_user_id,
           rc.resolution_note  AS resolution_note,
           rc.created_at       AS created_at
      FROM reconciliation_cases rc
     WHERE rc.market_id = :market_id
       AND rc.service_date = :day
       AND (:status IS NULL OR rc.status = :status)
       AND (
             :cursor_created_at IS NULL
             OR (rc.created_at, rc.id) < (:cursor_created_at, :cursor_case_id)
           )
     ORDER BY rc.created_at DESC, rc.id DESC
     LIMIT :page_limit
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("day", type_=Date()),
    bindparam("status", type_=Text()),
    bindparam("cursor_created_at", type_=_TIMESTAMPTZ),
    bindparam("cursor_case_id", type_=_UUID),
    bindparam("page_limit", type_=Integer()),
)
"""Navbatning bir sahifasi — ⛔ KEYSET, `OFFSET` EMAS (DQ-4).

⛔ `OFFSET` ISHLATILMAYDI VA SABAB O'LCHANADIGAN: case ro'yxati KUN
   DAVOMIDA O'SADI (`recon.open` qayta yugurishi ham, nazoratchining
   ishlashi ham qatorlarni siljitadi). Offset bilan sahifalaganda
   nazoratchi bir case'ni IKKI MARTA ko'rib, ikkinchisini UMUMAN
   ko'rmasdi — va u buni SEZMASDI ham.

⚠ TARTIB `(created_at DESC, id DESC)` va u `CASE_KEYSET_INDEX` bilan
  AYNAN mos. `id` tenglik uzgichi sifatida MAJBURIY: `created_at`
  bir xil bo'lgan ikki case (bitta `INSERT ... SELECT` hammasini bir
  vaqtda yozadi!) tartibsiz qolardi va kursor ular ustidan sakrab
  o'tardi.

⚠ QATOR SOLISHTIRUVI (`(a, b) < (x, y)`) ATAYIN — ikki ustunli `OR`
  zanjiri bilan yozilgan shart indeksdan foydalana olmasdi.
"""

_CASE_COUNTS = text(
    """
    SELECT count(*) FILTER (WHERE rc.status = :new)::int         AS new_count,
           count(*) FILTER (WHERE rc.status = :in_review)::int   AS in_review_count,
           count(*) FILTER (WHERE rc.status = :justified)::int   AS justified_count,
           count(*) FILTER (WHERE rc.status = :unjustified)::int AS unjustified_count
      FROM reconciliation_cases rc
     WHERE rc.market_id = :market_id
       AND rc.service_date = :day
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("day", type_=Date()),
    bindparam("new", type_=Text()),
    bindparam("in_review", type_=Text()),
    bindparam("justified", type_=Text()),
    bindparam("unjustified", type_=Text()),
)
"""Kunning TO'RT hisoblagichi — ⛔ `status` FILTRIDAN MUSTAQIL.

Hisoblagichlar sahifaga emas, KUNGA tegishli: nazoratchi «yangi»
filtrini yoqqanda ham «bugun nechta case yopildi?» savolining javobi
o'zgarmasligi kerak. Filtrni bu so'rovga ham qo'llash tanlangan
holatdan boshqa uchtasini NOLGA tushirardi va u «bugun hech nima
yopilmadi» bilan MEXANIK ravishda bir xil ko'rinardi.
"""


@dataclass(frozen=True, slots=True)
class CaseRow:
    """Navbatdagi bitta case — ⛔ FAQAT IDENTIFIKATORLAR VA HOLAT.

    Sotuvchining ismi, rasta kodi va summa BU YERDA YO'Q: ular
    `daily_charges` / `billing_anomalies` ning O'Z marshrutlaridan
    olinadi (C-10 — «identifikator, ism emas»). Ularni bu qatorga
    ko'chirish navbat ro'yxatini ikkinchi haqiqat manbaiga aylantirardi.
    """

    case_id: UUID
    subject_kind: str
    """`ReconciliationSubjectKind` — case QAYSI SINFDAN (Pattern 4)."""
    anomaly_id: UUID | None
    charge_id: UUID | None
    """⛔ XOR: ikkalasidan AYNAN BITTASI to'ldirilgan (DQ-5)."""
    service_date: date
    status: str
    assignee_user_id: UUID | None
    resolution_note: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CaseCursor:
    """Keyset kursori — `(created_at, id)` JUFTLIGI, yolg'iz vaqt EMAS.

    Yolg'iz `created_at` bilan yozilgan kursor bir xil vaqtda yozilgan
    case'lar ustidan sakrab o'tardi va `INSERT ... SELECT` AYNAN shunday
    yozadi (bir tranzaksiya — bir `now()`).
    """

    created_at: datetime
    case_id: UUID


@dataclass(frozen=True, slots=True)
class CaseListPage:
    """`ChargeListResponse` NAQSHI — ⛔ hisoblagichlar HAR DOIM qaytadi.

    Kun bo'sh bo'lishi NORMAL holat, lekin «bu kunda case yo'q» bilan
    «hisoblagich ishlamayapti» bir xil ko'rinsa direktor tizimni buzuq
    deb hisoblardi (`ChargeListResponse` docstringidagi aynan qaror).

    `day` javobda ATAYIN bor: standart kun SERVERDA hisoblanadi va klient
    qaysi kunni ko'rayotganini javobning O'ZIDAN biladi.
    """

    day: date
    rows: tuple[CaseRow, ...]
    new_count: int
    in_review_count: int
    justified_count: int
    unjustified_count: int
    next_cursor: CaseCursor | None
    """Keyingi sahifaning kaliti; `None` — sahifa TO'LMADI, ya'ni oxiri.

    ⚠ MAYDON REJADAGI ENVELOPE'GA QO'SHILDI va usiz keyset SAHIFALASH
      IFODALAB BO'LMAS bo'lardi: klient kursorni o'zi qurishi uchun
      oxirgi qatorning `created_at` ini O'QISHI kerak bo'lardi, ya'ni
      sahifalash qoidasi SERVERDAN KLIENTGA ko'chardi va ikki tomonda
      ajralib ketardi.
    """


async def list_cases(
    session: AsyncSession,
    *,
    market_id: UUID,
    day: date,
    status: str | None = None,
    cursor: CaseCursor | None = None,
    limit: int = CASE_PAGE_SIZE,
) -> CaseListPage:
    """Kun kesimidagi navbat — keyset bilan sahifalangan.

    Args:
        day: `reconciliation_cases.service_date` — nomuvofiqlik QAYSI KUN
            uchun aniqlangan. ⚠ Bu case QACHON OCHILGANI emas: `recon.open`
            kechagi kunni bugun tekshiradi.
        status: ixtiyoriy filtr; ⚠ hisoblagichlarga TA'SIR QILMAYDI
            (`_CASE_COUNTS` docstringi).
        cursor: oldingi sahifaning `next_cursor` i.
        limit: sahifa o'lchami; `CASE_PAGE_SIZE` dan katta qiymat SHU
            chegaraga qisqartiriladi — klient bir so'rov bilan butun
            navbatni tortib ololmasligi kerak.

    Returns:
        `CaseListPage` — qatorlar, kunning to'rt hisoblagichi va kursor.
    """
    page_limit = max(1, min(limit, CASE_PAGE_SIZE))
    rows = (
        await session.execute(
            _CASE_ROWS,
            {
                "market_id": market_id,
                "day": day,
                "status": status,
                "cursor_created_at": None if cursor is None else cursor.created_at,
                "cursor_case_id": None if cursor is None else cursor.case_id,
                "page_limit": page_limit,
            },
        )
    ).mappings()
    items = tuple(
        CaseRow(
            case_id=row["case_id"],
            subject_kind=str(row["subject_kind"]),
            anomaly_id=row["anomaly_id"],
            charge_id=row["charge_id"],
            service_date=row["service_date"],
            status=str(row["status"]),
            assignee_user_id=row["assignee_user_id"],
            resolution_note=row["resolution_note"],
            created_at=row["created_at"],
        )
        for row in rows
    )

    counts = (
        (
            await session.execute(
                _CASE_COUNTS,
                {
                    "market_id": market_id,
                    "day": day,
                    "new": _STATUS_NEW,
                    "in_review": _STATUS_IN_REVIEW,
                    "justified": _STATUS_JUSTIFIED,
                    "unjustified": _STATUS_UNJUSTIFIED,
                },
            )
        )
        .mappings()
        .one()
    )

    next_cursor = None
    if len(items) == page_limit:
        # ⚠ SAHIFA TO'LGANDA kursor beriladi — «yana bor» degan DA'VO emas,
        #   «tekshirib ko'r» degan taklif. Qo'shimcha `count(*)` so'rovi
        #   bilan aniq javob berish navbat kun davomida o'sgani uchun
        #   BARIBIR eskirardi.
        last = items[-1]
        next_cursor = CaseCursor(created_at=last.created_at, case_id=last.case_id)

    return CaseListPage(
        day=day,
        rows=items,
        new_count=int(counts["new_count"]),
        in_review_count=int(counts["in_review_count"]),
        justified_count=int(counts["justified_count"]),
        unjustified_count=int(counts["unjustified_count"]),
        next_cursor=next_cursor,
    )


# ===========================================================================
# 3. HIT-RATE — HOSILA, SAQLANMAYDI (D-13)
# ===========================================================================

_HIT_RATE_COUNTS = text(
    """
    SELECT count(*) FILTER (WHERE rc.status = :justified)::int    AS justified,
           count(*) FILTER (WHERE rc.status = :unjustified)::int  AS unjustified,
           count(*) FILTER (WHERE rc.status = ANY(:pending))::int AS pending
      FROM reconciliation_cases rc
     WHERE rc.market_id = :market_id
       AND rc.service_date BETWEEN :date_from AND :date_to
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("date_from", type_=Date()),
    bindparam("date_to", type_=Date()),
    bindparam("justified", type_=Text()),
    bindparam("unjustified", type_=Text()),
    bindparam("pending", type_=_TEXT_ARRAY),
)
"""Uch sanoq — ⛔ NISBAT SO'ROVDA HISOBLANMAYDI.

`pending` (`new` + `in_review`) ATAYIN ALOHIDA qaytariladi: u maxrajga
KIRMAYDI, lekin YASHIRILMAYDI ham. Yashirilganda «hit-rate 100 %» degan
javob «hamma case ko'rildi» bilan «faqat bittasi ko'rildi, qolgan 74 tasi
navbatda» ni MEXANIK ravishda bir xil ko'rsatardi.
"""


@dataclass(frozen=True, slots=True)
class HitRate:
    """Navbatning aniqligi — ⛔ NISBAT `None` BO'LISHI MUMKIN VA BU JAVOB.

    `rate is None` = «hali O'LCHOV YO'Q», nol EMAS. Farq 5-fazaning
    Wilson qarori bilan bir xil sinfda: o'lchanmagan sonning o'rniga nol
    yozish «tizim aniqligi nol» degan YOLG'ON da'vo bo'lardi va u
    direktorning birinchi haftadagi qaroriga bevosita ta'sir qilardi.
    """

    justified: int
    unjustified: int
    pending: int
    """⛔ MAXRAJGA KIRMAYDI (D-13) — `_HIT_RATE_COUNTS` docstringi."""
    rate: float | None


async def hit_rate(
    session: AsyncSession,
    *,
    market_id: UUID,
    date_from: date,
    date_to: date,
) -> HitRate:
    """RECON-01 ning ko'rsatkichi — ⛔ HOSILA, saqlangan ustun EMAS.

    =======================================================================
    ⛔ MAXRAJ D-13 DA QULFLANGAN: `justified + unjustified`. `new` va
       `in_review` KIRMAYDI va sabab mexanik — hali ko'rilmagan case
       metrikani PASAYTIRARDI, ya'ni navbatni tez ko'rib chiqmaslik
       ko'rsatkichni yomonlashtirardi va ko'rsatkich o'z jarayonini
       o'lchash o'rniga uning KECHIKISHINI o'lchardi.

    ⛔ MAXRAJ NOL BO'LGANDA JAVOB `None` — `NULLIF` semantikasi.
       Nol yozish 5-fazaning darsini takrorlardi: o'lchanmagan qiymat
       o'lchangan nolga aylanardi va ikkalasi hisobotda BIR XIL
       ko'rinardi.

    ⛔ USTUN SIFATIDA SAQLANMAYDI (`ReconciliationCase` docstringi):
       saqlangan hosila D-06 taqiqlagan qoldiq ustuni bilan AYNAN bir
       sinfda bo'lardi — ikkinchi haqiqat manbai birinchisidan jimgina
       ajralib ketardi.
    =======================================================================

    Args:
        date_from: `service_date` ning quyi chegarasi (INKLYUZIV).
        date_to: yuqori chegarasi (INKLYUZIV).

    Returns:
        `HitRate` — uchala sanoq VA nisbat (yoki `None`).
    """
    row = (
        (
            await session.execute(
                _HIT_RATE_COUNTS,
                {
                    "market_id": market_id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "justified": _STATUS_JUSTIFIED,
                    "unjustified": _STATUS_UNJUSTIFIED,
                    "pending": list(_PENDING_STATUSES),
                },
            )
        )
        .mappings()
        .one()
    )

    justified = int(row["justified"])
    unjustified = int(row["unjustified"])
    denominator = justified + unjustified
    return HitRate(
        justified=justified,
        unjustified=unjustified,
        pending=int(row["pending"]),
        rate=None if denominator == 0 else justified / denominator,
    )


# ===========================================================================
# 4. HOLAT O'ZGARISHI — IKKI YOZUV, BITTA TRANZAKSIYA (D-14)
# ===========================================================================

_CASE_STATUS_FOR_UPDATE = text(
    """
    SELECT rc.status AS status
      FROM reconciliation_cases rc
     WHERE rc.market_id = :market_id
       AND rc.id = :case_id
     FOR UPDATE
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("case_id", type_=_UUID),
)
"""⛔ ESKI QIYMAT YOZUVDAN OLDIN O'QILADI (`me.py::update_profile` darsi).

Keyin o'qilsa jurnal «new -> new» degan MA'NOSIZ qator olardi — ya'ni
`EVENT_STATUS_TRANSITION_CHECK` uni rad etardi va o'tish HECH QACHON
yozilmasdi. Xato esa «case o'zgarmadi» emas, «konstrayt buzuq» bo'lib
ko'rinardi.

⚠ `FOR UPDATE` — ikki nazoratchi bir case'ni bir vaqtda ko'rganda
  ikkinchisi birinchisining natijasini KO'RADI. Usiz ikkalasi ham
  `new` ni o'qib, ikkita `new -> ...` qatori yozardi va tarixda bir
  o'tish IKKI MARTA ko'rinardi.
"""

_UPDATE_CASE_STATUS = text(
    """
    UPDATE reconciliation_cases
       SET status = :to_status,
           assignee_user_id = COALESCE(:actor_user_id, assignee_user_id),
           resolution_note = COALESCE(:note, resolution_note),
           updated_at = now()
     WHERE market_id = :market_id
       AND id = :case_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("case_id", type_=_UUID),
    bindparam("to_status", type_=Text()),
    bindparam("actor_user_id", type_=_UUID),
    bindparam("note", type_=Text()),
)
"""Case'ning JORIY holati — tarix EMAS, KO'RINISH.

⚠ `COALESCE` IKKALA USTUNDA HAM: berilmagan qiymat mavjudini
  O'CHIRMAYDI. Mas'ulni tozalash uchun `NULL` yuborish yo'li ATAYIN
  yo'q — «case egasiz qoldi» holati ilova qatlamining qarori va u
  bugungi oqimda mavjud emas.

⚠ `assignee_user_id` — O'TISHNI QILGAN ODAM. Ya'ni case'ni oxirgi marta
  qo'lga olgan kishi uning egasi bo'lib qoladi; tizim o'tishlari
  (`actor_user_id IS NULL`) egani O'ZGARTIRMAYDI.

⚠ `updated_at` OCHIQ YOZILADI: bu so'rov ORM orqali emas, xom SQL bilan
  ketadi va `onupdate` hodisasi bu yo'lda UMUMAN ishlamasdi.
"""

_INSERT_CASE_EVENT = text(
    """
    INSERT INTO reconciliation_case_events
                (market_id, case_id, from_status, to_status, actor_user_id, note)
    VALUES (:market_id, :case_id, :from_status, :to_status, :actor_user_id, :note)
    RETURNING id AS event_id, created_at AS created_at
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("case_id", type_=_UUID),
    bindparam("from_status", type_=Text()),
    bindparam("to_status", type_=Text()),
    bindparam("actor_user_id", type_=_UUID),
    bindparam("note", type_=Text()),
)
"""Tarix qatori — ⛔ YANGI QATOR, TAHRIR EMAS (D-14).

`charge_adjustments` ning aynan naqshi: jadval `0023` ning
o'zgarmaslik triggeri bilan qulflangan, ya'ni «tuzataman» yo'li
STRUKTURAVIY yopiq va nizoda (D-02) «kim, qachon, qaysi holatdan»
savoliga javob beradigan yagona qator YO'QOLMAYDI.
"""


@dataclass(frozen=True, slots=True)
class CaseTransition:
    """Bitta o'tishning natijasi — case VA u tug'dirgan tarix qatori."""

    case_id: UUID
    from_status: str
    to_status: str
    event_id: UUID
    """⛔ HAR CHAQIRUV AYNAN BITTA qator yozadi — «juftlik» ning o'lchovi."""
    created_at: datetime


async def transition(
    session: AsyncSession,
    *,
    market_id: UUID,
    case_id: UUID,
    to_status: str,
    actor_user_id: UUID | None = None,
    note: str | None = None,
) -> CaseTransition:
    """Case holatini o'zgartiradi — ⛔ IKKI YOZUV, BITTA TRANZAKSIYA (D-14).

    =======================================================================
    ⛔ YOPILGAN HOLATDAN QAYTISH RUXSAT ETILADI (`justified` ->
       `in_review`) va bu ATAYIN ochiq aytiladi: nazoratchi xato yopgan
       case'ni qayta ochishi HAQIQIY holat va uni taqiqlash odamni
       IKKINCHI case ochishga majburlardi — o'shanda hit-rate maxraji
       (D-13) sun'iy shishardi. Qaytish ham YANGI QATOR yozadi, ya'ni
       tarixda ikkala qadam ham ko'rinadi.

    ⛔ BIR XIL HOLATGA O'TISH RAD ETILADI (`ValueError`). Sxema uni
       `EVENT_STATUS_TRANSITION_CHECK` bilan allaqachon to'sadi, lekin
       u yerdagi xato `IntegrityError` bo'lib chiqardi va sabab «kodda
       xato» emas, «baza buzuq» kabi ko'rinardi. Nol o'tish tarixni
       shovqin bilan to'ldirardi: «case necha marta qo'ldan qo'lga
       o'tdi?» savoli noto'g'ri javob berardi.
    =======================================================================

    Args:
        to_status: `ReconciliationCaseStatus` a'zosining qiymati. Yopiq
            to'rtlikdan tashqari qiymatni sxemaning `CHECK` i rad etadi —
            bu yerda TAKRORLANMAYDI (nusxa jimgina ajralib ketardi).
        actor_user_id: ⛔ `None` = TIZIM, «noma'lum» EMAS (`0022` qarori).
        note: erkin izoh; tarix qatoriga VA case'ning yechim matniga
            yoziladi. Uzunlik chegarasi sxemada
            (`RESOLUTION_NOTE_LENGTH_CHECK`).

    Returns:
        `CaseTransition` — eski holat, yangi holat va tug'ilgan tarix
        qatorining identifikatori.

    Raises:
        LookupError: case bu bozorda topilmaganda. ⛔ JIM `return`
            QILINMAYDI: chaqiruvchi «o'zgardi» deb hisoblardi va
            nazoratchi ekranida hech nima o'zgarmasdi.
        ValueError: `from_status == to_status` bo'lganda.
    """
    current = (
        await session.execute(_CASE_STATUS_FOR_UPDATE, {"market_id": market_id, "case_id": case_id})
    ).scalar_one_or_none()
    if current is None:
        raise LookupError(
            f"case topilmadi: market_id={market_id}, case_id={case_id}. "
            "Boshqa bozorning case'i RLS ostida ham, `market_id` filtri "
            "ostida ham KO'RINMAYDI — ya'ni bu javob «yo'q» degani, "
            "«ruxsat yo'q» degani emas."
        )

    from_status = str(current)
    if from_status == to_status:
        raise ValueError(
            f"case {case_id} allaqachon `{to_status}` holatida. Nol o'tish "
            "tarixga MA'NOSIZ qator yozardi va «case necha marta qo'ldan "
            "qo'lga o'tdi?» savoli noto'g'ri javob berardi (D-14)."
        )

    await session.execute(
        _UPDATE_CASE_STATUS,
        {
            "market_id": market_id,
            "case_id": case_id,
            "to_status": to_status,
            "actor_user_id": actor_user_id,
            "note": note,
        },
    )
    event = (
        (
            await session.execute(
                _INSERT_CASE_EVENT,
                {
                    "market_id": market_id,
                    "case_id": case_id,
                    "from_status": from_status,
                    "to_status": to_status,
                    "actor_user_id": actor_user_id,
                    "note": note,
                },
            )
        )
        .mappings()
        .one()
    )

    return CaseTransition(
        case_id=case_id,
        from_status=from_status,
        to_status=to_status,
        event_id=event["event_id"],
        created_at=event["created_at"],
    )


# ===========================================================================
# 5. DALIL — ⛔ FAQAT IDENTIFIKATOR (D-03, T-06-81)
# ===========================================================================

_CASE_EVIDENCE = text(
    """
    WITH target AS (
        SELECT rc.id           AS case_id,
               rc.market_id    AS market_id,
               rc.subject_kind AS subject_kind,
               rc.anomaly_id   AS anomaly_id,
               rc.charge_id    AS charge_id
          FROM reconciliation_cases rc
         WHERE rc.market_id = :market_id
           AND rc.id = :case_id
    )
    SELECT t.subject_kind AS subject_kind,
           ev.snapshot_id AS snapshot_id
      FROM target t
      LEFT JOIN LATERAL (
            SELECT a.snapshot_id AS snapshot_id
              FROM billing_anomalies a
             WHERE a.market_id = t.market_id
               AND a.id = t.anomaly_id
               AND a.snapshot_id IS NOT NULL
            UNION ALL
            SELECT ce.snapshot_id
              FROM charge_evidence ce
             WHERE ce.market_id = t.market_id
               AND ce.charge_id = t.charge_id
               AND ce.snapshot_id IS NOT NULL
      ) ev ON true
     ORDER BY ev.snapshot_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("case_id", type_=_UUID),
)
"""Case'ning dalil KO'RSATKICHLARI — ikki sinf, bitta so'rov.

⚠ `LEFT JOIN LATERAL` ATAYIN, ichki `JOIN` EMAS: dalilsiz case (masalan
  hisob uchun `charge_evidence` yozilmagan) ham BITTA qator qaytaradi va
  `subject_kind` baribir ma'lum bo'ladi. Ichki `JOIN` bilan bunday case
  «topilmadi» bilan MEXANIK ravishda bir xil ko'rinardi.

⚠ `ORDER BY` MAJBURIY: `UNION ALL` tartibni KAFOLATLAMAYDI va nizo
  hujjatiga tushadigan ro'yxat har chaqiruvda boshqa tartibda chiqardi.
"""


@dataclass(frozen=True, slots=True)
class CaseEvidence:
    """Case'ning dalili — ⛔ FAQAT IDENTIFIKATORLAR.

    =======================================================================
    ⛔⛔ BU YERDA BAYT, OMBOR KALITI VA IMZOLANGAN HAVOLA YO'Q (D-03,
       T-06-81). Klient `snapshot_ids` ni MAVJUD kadr marshrutiga —
       AUTENTIFIKATSIYA ostidagi yuzaga — beradi.

    Sabab huquqiy va u muzokara qilinmaydi: kadrda tashrifchilar yuzi bor
    (O'zR shaxsiy ma'lumotlar qonuni). Dalil-kadr yuzasining KENGAYISHI
    aynan shu yerdan boshlanardi — bitta «qulaylik uchun» maydon
    qo'shilardi va u keyin bot xabariga ham, hisobot eksportiga ham
    ko'chib o'tardi.
    =======================================================================

    ⚠ BO'SH KORTEJ — NORMAL JAVOB: `no_coverage_stall` dan case
      ochilmasa ham, hisobning dalili `day_close` yugurmagani uchun
      yozilmagan bo'lishi mumkin. Klient bu holatda dalil bo'limini
      UMUMAN chizmaydi (05-14 darsi: to'qilgan placeholder ham, «bo'sh»
      degan yorliq ham noto'g'ri).
    """

    case_id: UUID
    subject_kind: str
    snapshot_ids: tuple[UUID, ...]


async def case_evidence(session: AsyncSession, *, market_id: UUID, case_id: UUID) -> CaseEvidence:
    """Case'ning dalil ko'rsatkichlari — ⛔ FAQAT `UUID` (klass docstringi).

    Returns:
        `CaseEvidence`; dalil topilmasa `snapshot_ids` BO'SH kortej.

    Raises:
        LookupError: case bu bozorda topilmaganda — `transition()` bilan
            aynan bir xil qaror va bir xil sabab.
    """
    rows = list(
        (await session.execute(_CASE_EVIDENCE, {"market_id": market_id, "case_id": case_id}))
        .mappings()
        .all()
    )
    if not rows:
        raise LookupError(
            f"case topilmadi: market_id={market_id}, case_id={case_id}. "
            "Javob «yo'q» degani, «ruxsat yo'q» degani emas."
        )

    return CaseEvidence(
        case_id=case_id,
        subject_kind=str(rows[0]["subject_kind"]),
        snapshot_ids=tuple(row["snapshot_id"] for row in rows if row["snapshot_id"] is not None),
    )
