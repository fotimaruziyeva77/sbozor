"""Davr hisobotlarining ARIFMETIKASI — uch hosila so'rov, bitta modul (RECON-04).

=============================================================================
⛔⛔ 1. BU MODUL YANGI JADVAL YARATMAYDI VA SAQLANGAN AGREGAT TUG'DIRMAYDI (D-03).

Uchala hisobot ham MAVJUD qatorlar ustidagi HOSILA so'rov:

    `daily_charges` · `payments` · `charge_adjustments` ·
    `vendor_outstanding()` · `reconciliation_cases` · `billing_anomalies`

6-faza D-07 va 7-faza D-06 saqlangan agregatni TAQIQLAYDI. Agregat qator
`daily_charges` bilan drift qiladi va nizoda «qaysi son to'g'ri?» savoli
javobsiz qoladi — bu SBOZOR mavjud bo'lish sababining AYNAN TESKARISI
(D-02). Shu sababdan bu faylda na yangi jadval e'loni, na oldindan
hisoblab qo'yilgan ko'rinish bor va bo'lmaydi ham.

⚠ VASVASA KEYINGI IJROCHIDA TUG'ILADI: «hisobot sekin, keling kunlik
  yig'indini jadvalga yozib qo'yamiz». Javob — YO'Q. Tezlik masalasi
  indeks bilan hal qilinadi (`DAILY_CHARGE_DAY_INDEX`,
  `PAYMENT_VENDOR_INDEX`), ikkinchi haqiqat manbai bilan emas.

=============================================================================
⛔⛔ 2. `_SIGNED_PAYMENT_EXPR` VA `_SIGNED_ADJUSTMENT_EXPR` `billing_repo` DAN
   IMPORT QILINADI, QAYTA YOZILMAYDI.

G-14 darvozasining BUTUN da'vosi shu ikki satrga tayanadi: `vendor_outstanding()`
va `vendor_charge_allocation()` AYNAN bir xil belgili ifodadan chiqadi, ya'ni
ular ajralib keta OLMAYDI. Bu yerda uchinchi nusxa yozilsa darvoza chetlab
o'tilardi va hisobotdagi tushum bilan ekrandagi qoldiq bir kun farq qilardi —
IKKALASI HAM «to'g'ri» bo'lgan holda.

=============================================================================
⛔⛔ 3. IKKI SANA IKKI SAVOLGA JAVOB BERADI VA ULAR ARALASHTIRILMAYDI (Pitfall 14).

    payments.business_date     — pul QACHON YIG'ILDI (kassa kuni)
    daily_charges.service_date — QAYSI KUNNING pattasi

Kassir bugun kechagi qarzni to'lasa: to'lov BUGUNGI `collected_soum` ga,
patta esa KECHAGI `charged_soum` ga tushadi. Ikkalasini bitta songa siqish
direktorga BOSHQA savolning javobini berardi — va farqning O'ZI RECON-04
ning qiymati (T-08-15).

=============================================================================
⚠ DAVR CHEGARASI BU QATLAMDA QO'YILMAYDI (T-08-16). `report_max_period_days`
  va `report_max_rows` CHAQIRUVCHI qatlamda (08-07) `422` ga aylanadi. Repo
  chegara qo'ysa u ikki joyda yashardi va HTTP javob kodi so'rov qatlamidan
  chiqib ketardi.

⚠ TENANT: har so'rovda `market_id = :market_id` sharti BOR va u RLS bilan
  JUFT ishlaydi (T-08-13). Ikkalasi ham majburiy: RLS — kafolat, aniq shart
  esa NIYAT (va u `EXPLAIN` da indeksga tushadi).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Final

from sbozor_core.enums import (
    AdjustmentDirection,
    AnomalyKind,
    PaymentKind,
    ReconciliationSubjectKind,
)
from sqlalchemy import BigInteger, Date, Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.repositories.billing_repo import (
    _SIGNED_ADJUSTMENT_EXPR,
    _SIGNED_PAYMENT_EXPR,
    vendor_charge_allocation,
    vendor_outstanding,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.import_validator import LedgerImportRow

__all__ = [
    "ARCHIVE_KIND_UNPAID",
    "ARCHIVE_KIND_UNREGISTERED",
    "AnomalyArchive",
    "AnomalyArchiveRow",
    "LedgerDay",
    "LedgerDayRow",
    "ReceivableRow",
    "RevenuePeriod",
    "RevenueRow",
    "anomaly_archive",
    "ledger_day",
    "ledger_upsert",
    "receivables",
    "revenue_by_day",
]

_UUID = PgUuid(as_uuid=True)
_UUID_ARRAY = ARRAY(PgUuid(as_uuid=True))
_BIGINT_ARRAY = ARRAY(BigInteger())

_REVERSAL: Final[str] = PaymentKind.REVERSAL.value
_INCREASE: Final[str] = AdjustmentDirection.INCREASE.value
"""Enum qiymatlari so'rov PARAMETRI, so'rov MATNIDAGI literal EMAS.

`billing_repo._OCCUPIED` da o'rnatilgan qoida: matnga yozilgan literal enum
o'zgargan kuni filtr JIMGINA hech nimaga tushmasdi — so'rov ishlayverardi,
faqat natija bo'sh bo'lardi.
"""


# ===========================================================================
# 1. TUSHUM — IKKI USTUN, IKKI SANA, NOL KUNLAR KO'RINADI
# ===========================================================================

_REVENUE_BY_DAY = text(
    f"""
    WITH days AS (
        SELECT gs::date AS business_date
          FROM generate_series(
                   CAST(:from_date AS date),
                   CAST(:to_date AS date),
                   '1 day'::interval
               ) AS gs
    ),
    per_day AS (
        SELECT d.business_date                         AS business_date,
               COALESCE(pay.collected_soum, 0)::bigint AS collected_soum,
               COALESCE(pay.payment_count, 0)::bigint  AS payment_count,
               COALESCE(chg.charged_soum, 0)::bigint   AS charged_soum,
               COALESCE(chg.charge_count, 0)::bigint   AS charge_count
          FROM days d
          LEFT JOIN LATERAL (
            SELECT sum({_SIGNED_PAYMENT_EXPR})::bigint AS collected_soum,
                   count(*)                            AS payment_count
              FROM payments p
             WHERE p.market_id = :market_id
               AND p.business_date = d.business_date
          ) pay ON true
          LEFT JOIN LATERAL (
            SELECT sum(ch.amount_soum + COALESCE(adj.total, 0))::bigint AS charged_soum,
                   count(*)                                             AS charge_count
              FROM daily_charges ch
              LEFT JOIN LATERAL (
                SELECT sum({_SIGNED_ADJUSTMENT_EXPR}) AS total
                  FROM charge_adjustments a
                 WHERE a.market_id = ch.market_id
                   AND a.charge_id = ch.id
              ) adj ON true
             WHERE ch.market_id = :market_id
               AND ch.service_date = d.business_date
          ) chg ON true
    )
    SELECT business_date,
           collected_soum,
           payment_count,
           charged_soum,
           charge_count,
           (sum(collected_soum) OVER ())::bigint AS total_collected_soum,
           (sum(charged_soum)   OVER ())::bigint AS total_charged_soum
      FROM per_day
     ORDER BY business_date
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("from_date", type_=Date()),
    bindparam("to_date", type_=Date()),
    bindparam("reversal", type_=Text()),
    bindparam("increase", type_=Text()),
)
"""Kunlik tushum — ⛔ `generate_series` MAJBURIY VA SABABI MEXANIK.

=============================================================================
⛔⛔ NEGA `generate_series`, NEGA YOLG'IZ `GROUP BY` EMAS.

`GROUP BY` faqat MAVJUD qatorlardan kun yasaydi, ya'ni birorta to'lov ham,
birorta hisob ham bo'lmagan kun natijadan BUTUNLAY tushib qolardi. Direktor
o'shanda ikki BUTUNLAY BOSHQA holatni ajrata olmasdi:

    «o'sha kuni tizim ishlamadi»   (kadr olinmadi, job yugurmadi)
    «o'sha kuni pul yig'ilmadi»    (bozor ishladi, tushum nol)

Bu 4-fazaning «YO'QLIKKA ALERT» prinsipining hisobotdagi ko'rinishi:
sukunat javob emas. Nol kun QATOR sifatida, ikkala summasi `0` bilan
chiqadi va shundagina «nol» aytilgan javob bo'ladi.

=============================================================================
⛔ `CAST(:from_date AS date)` — `:from_date::date` SHAKLI ISHLAMAYDI VA BU
   O'LCHANGAN (`sqlalchemy.exc.ArgumentError: This text() construct doesn't
   define a bound parameter named 'from_date'`).

`text()` ning bind-parametr regeksi nomdan KEYIN yana ikki nuqta kelishini
oldinga qarash (negative lookahead) bilan RAD ETADI, ya'ni `:from_date::date`
da parametr UMUMAN topilmaydi va `bindparams()` yig'ilish paytida
yiqiladi — modul IMPORT bo'lmaydi. 08-RESEARCH ning Pattern 1
namunasi aynan shu shaklda yozilgan — u hech qachon BAJARILMAGAN. Kast
`CAST(... AS date)` shaklida yoziladi; `gs::date` va `::bigint` esa
xavfsiz, chunki ular BIND PARAMETRIDAN keyin turmaydi.

=============================================================================
⛔ `gs::date` — ANIQ KAST VA U TUSHIRIB QOLDIRILMAYDI.

`generate_series(date, date, interval)` — `timestamp` qaytaradigan variant
(argumentlar `timestamp` ga ko'tariladi). Kastsiz qoldirilganda ustunning
tipi `timestamp` bo'lardi va Python tomonida `date` o'rniga `datetime`
kelardi — `RevenueRow.business_date` ning shartnomasi jimgina buzilardi va
uni faqat eksport bosqichida (sarlavha formatlashda) sezilardi.

=============================================================================
⛔ IKKI `LEFT JOIN LATERAL` — IKKI SANA (modul docstringining 3-bandi).

    `pay` -> `payments.business_date = d.business_date`   (kassa kuni)
    `chg` -> `daily_charges.service_date = d.business_date` (patta kuni)

⚠ `LEFT JOIN ... ON true` ATAYIN: agregat ichki so'rov qatorsiz holatda ham
  BITTA qator qaytaradi (`sum` -> `NULL`, `count` -> `0`), ya'ni `COALESCE`
  bilan birga nol kun kafolatlanadi. Ichki `JOIN` bilan kun yana yo'qolardi
  va `generate_series` ning butun foydasi bekor bo'lardi.

=============================================================================
⛔ HISOB TUZATISHLAR BILAN NETLANADI: `ch.amount_soum + COALESCE(adj.total, 0)`.

Xom `daily_charges.amount_soum` O'ZGARMAS (D-07) va tuzatish ALOHIDA qator
bo'ladi, ya'ni «amaldagi summa» HAR DOIM hisoblanadigan ko'rinish. Xom
ustunni o'qigan hisobot `charge_list()` ekranidagi son bilan farq qilardi.

=============================================================================
⛔ YIG'INDI SERVERDA — `sum(...) OVER ()` (UI-SPEC §8.2).

Klient `reduce` QILMAYDI. Oyna funksiyasi butun natija ustidan yig'indi
beradi va u AYNI so'rovdan, AYNI qatorlardan chiqadi: ikkinchi `SELECT`
bilan olingan yig'indi ikki so'rov orasida yozilgan yangi to'lov tufayli
qatorlar yig'indisidan FARQ QILARDI — ekranda «jami 3 000 000» yozuvi
ostida 2 900 000 lik qatorlar turardi (`anomaly_list()` da o'lchangan
aynan o'sha sinf).

=============================================================================
⛔ `S608` SHU SO'ROVDA O'CHIRILGAN VA SABAB TOR (`billing_repo._VENDOR_OUTSTANDING`
   bilan AYNAN bir xil): f-string ga tushadigan YAGONA qiymat — `billing_repo`
   dan IMPORT qilingan SOBIT `_SIGNED_*_EXPR` konstantalari. Tashqi kirish
   f-string ga umuman kelmaydi; har qiymat `bindparam(...)` bilan TIPLANGAN
   (T-08-14).
"""


@dataclass(frozen=True, slots=True)
class RevenueRow:
    """Bir KUNNING tushumi — ⛔ IKKI SUMMA IKKI ALOHIDA USTUNDA (T-08-15).

    `collected_soum` — o'sha KASSA KUNIDA yig'ilgan BELGILI pul
        (`payments.business_date`, storno MINUS bilan).
    `charged_soum`   — o'sha kunning HISOBLANGAN pattasi, tuzatishlar bilan
        netlangan (`daily_charges.service_date`).

    ⛔ UCHINCHI, «yagona tushum» MAYDONI YO'Q va qo'shilmaydi: ikki sonni
       bitta songa siqish nizoda «qaysi raqamni aytdingiz?» savolini
       tug'dirardi va farq — YIG'ILISH DARAJASI — aynan hisobotning
       qiymati (Pitfall 14).

    ⚠ `payment_count` `payments` ning QATORLARINI sanaydi, storno qatorini
      HAM. Storno — kassirning AMALI va u to'lovlar jurnalida ko'rinadi;
      sanoqdan chiqarish hisobotdagi qatorlar sonini jurnalnikidan farq
      qiladigan qilardi. Summa esa BELGILI, ya'ni bekor qilingan pul
      tushumga KIRMAYDI.
    """

    business_date: date
    collected_soum: int
    payment_count: int
    charged_soum: int
    charge_count: int


@dataclass(frozen=True, slots=True)
class RevenuePeriod:
    """Davrning qatorlari VA server hisoblagan ikki yig'indisi.

    ⛔ NEGA `list[RevenueRow]` EMAS: yig'indi SERVERDA hisoblanib ALOHIDA
       qaytarilishi shart (UI-SPEC §8.2) va yalang'och ro'yxat buni
       IFODALAY OLMAYDI — chaqiruvchi baribir klientda `reduce` qilardi.
       Naqsh `AnomalyArchive` va `CaseListPage` bilan bir xil: envelope
       qatorlarni VA ular haqidagi javobni birga tashiydi.

    ⚠ BO'SH DAVR (`from_date > to_date`) — qatorsiz va NOL yig'indili
      natija. Bu HALOL javob: `generate_series` bunday oraliqda 0 qator
      beradi va uni xato deb e'lon qilish chaqiruvchi qatlamning ishi
      (08-07 ning `422` si).
    """

    rows: tuple[RevenueRow, ...]
    total_collected_soum: int
    total_charged_soum: int


async def revenue_by_day(
    session: AsyncSession,
    *,
    market_id: UUID,
    from_date: date,
    to_date: date,
) -> RevenuePeriod:
    """Davr kesimidagi tushum — HOSILA so'rov, kunlik qatorlar bilan.

    ⛔ CHAQIRUVCHI TENANT KONTEKSTINI O'RNATGAN BO'LISHI SHART
       (`TenantSessionDep`): so'rovdagi `market_id` sharti NIYAT, RLS esa
       KAFOLAT — `billing_repo` modul docstringidagi Pitfall 9 qoidasi.

    Args:
        market_id: tenant kaliti.
        from_date: davrning BIRINCHI kuni (kiradi).
        to_date: davrning OXIRGI kuni (kiradi).

    Returns:
        `RevenuePeriod` — kunlar `business_date` bo'yicha O'SISH tartibida,
        davrning HAR kuni uchun bittadan qator (to'lovsiz kun ham).
        Barcha pul qiymatlari Python `int` (D-11: butun so'm).
    """
    result = await session.execute(
        _REVENUE_BY_DAY,
        {
            "market_id": market_id,
            "from_date": from_date,
            "to_date": to_date,
            "reversal": _REVERSAL,
            "increase": _INCREASE,
        },
    )
    mapped = list(result.mappings())

    return RevenuePeriod(
        rows=tuple(
            RevenueRow(
                business_date=row["business_date"],
                collected_soum=int(row["collected_soum"]),
                payment_count=int(row["payment_count"]),
                charged_soum=int(row["charged_soum"]),
                charge_count=int(row["charge_count"]),
            )
            for row in mapped
        ),
        # ⛔ YIG'INDI SERVERDAN, `sum(...)` NING PYTHON NUSXASIDAN EMAS:
        #    ikkinchi joyda yozilgan qo'shish amali bir kun ajralib
        #    ketardi (`total_due_soum()` ning aynan o'sha darsi).
        total_collected_soum=int(mapped[0]["total_collected_soum"]) if mapped else 0,
        total_charged_soum=int(mapped[0]["total_charged_soum"]) if mapped else 0,
    )


# ===========================================================================
# 2. QARZDORLIK REESTRI — ISM SERVERDA JOINLANADI (06 `deferred-items.md` №9)
# ===========================================================================

_RECEIVABLE_ROWS = text(
    """
    WITH outstanding AS (
        SELECT u.vendor_id        AS vendor_id,
               u.outstanding_soum AS outstanding_soum
          FROM unnest(CAST(:vendor_ids AS uuid[]), CAST(:outstanding_soums AS bigint[]))
                 AS u(vendor_id, outstanding_soum)
         WHERE u.outstanding_soum <> 0
    )
    SELECT o.vendor_id                AS vendor_id,
           v.full_name                AS vendor_name,
           o.outstanding_soum         AS outstanding_soum,
           codes.stall_codes          AS stall_codes
      FROM outstanding o
      LEFT JOIN vendors v
        ON v.market_id = :market_id
       AND v.id = o.vendor_id
      LEFT JOIN LATERAL (
        SELECT string_agg(uniq.code, ', ' ORDER BY uniq.code_sort, uniq.code) AS stall_codes
          FROM (
            SELECT DISTINCT s.code AS code, s.code_sort AS code_sort
              FROM stall_assignments sa
              JOIN stalls s
                ON s.market_id = sa.market_id
               AND s.id = sa.stall_id
             WHERE sa.market_id = :market_id
               AND sa.vendor_id = o.vendor_id
               AND sa.period && daterange(:from_date, :to_date, '[]')
          ) uniq
      ) codes ON true
     ORDER BY o.outstanding_soum DESC, v.full_name, o.vendor_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("vendor_ids", type_=_UUID_ARRAY),
    bindparam("outstanding_soums", type_=_BIGINT_ARRAY),
    bindparam("from_date", type_=Date()),
    bindparam("to_date", type_=Date()),
)
"""Reestrning YUZASI — ⛔ ARIFMETIKA BU SO'ROVDA YO'Q.

=============================================================================
⛔⛔ QOLDIQ `unnest(...)` ORQALI KIRADI, SHU YERDA HISOBLANMAYDI.

Sonlar `billing_repo.vendor_outstanding()` DAN keladi (BILL-03) va ikkinchi
qoldiq formulasi bu faylda YOZILMAYDI. Ular ikki massiv bo'lib parametr
sifatida uzatiladi, so'rov esa faqat NOM, RASTA KODI va TARTIB qo'shadi.

⚠ NEGA MASSIV, NEGA PYTHON FILTRI EMAS: `outstanding_soum <> 0` sharti
  SO'ROVNING O'ZIDA turishi kerak — u reestrning ta'rifi («qarzi yo'q
  sotuvchi hujjatda umuman ko'rinmaydi»), ilova qatlamining qulayligi
  emas. Tartib ham SERVERDA: `.xlsx` eksporti (08-10) shu ro'yxatni
  bayt-bayt yozadi va ikkinchi saralash ekrandagi tartib bilan fayldagi
  tartibni ajratardi.

=============================================================================
⛔⛔ ISM SHU YERDA JOINLANADI VA BU 06 №9 NING YECHIMI.

Uch yo'l RAD ETILGAN edi va ular RAD ETILGANCHA QOLADI:

  (a) klientda hamma sahifani tortish (`fetchNextPage`) — `GET /vendors`
      HAR chaqiruvda `audit_read` yozadi (D-09) va 300–1000 rastali
      bozorda jurnal shovqinga to'lardi;
  (b) ommaviy nom marshruti (`?ids=`) — YANGI backend yuzasi, u
      `PERSONAL_ROUTES` reyestrini o'stirardi (C-10 buni ATAYIN taqiqlaydi);
  (c) moliyaviy JSON javobiga `vendor_name` qo'shish — 06 §5.5 ning aynan
      rad etgan yo'li; 07-10 buni SABOTAJ bilan o'lchagan (to'rt tenancy
      testi qizaradi).

Bu marshrut ULARDAN BOSHQA SINF: u OPERATIV emas, HUJJAT. U bitta
`audit_read` yozadi (sotuvchi boshiga emas) va uning butun mavjud bo'lish
sababi — qog'ozda «kimdan undirish kerak?» savoliga javob berish.

=============================================================================
⛔ `LEFT JOIN vendors`, ICHKI `JOIN` EMAS — VA BU O'LCHANGAN QAROR.

Ichki `JOIN` bilan ism topilmagan qator REESTRDAN BUTUNLAY YO'QOLARDI,
ya'ni QARZ hujjatdan tushib qolardi va buni hech kim sezmasdi. `NULL` ism
esa KO'RINADIGAN bo'shliq: qator turadi, rasta kodi turadi, faqat ism
yo'q. ⛔ Bo'sh satr ham, «Noma'lum» ham YOZILMAYDI (05-14 darsi:
o'lchanmagan qiymatning o'rniga hech nima to'qilmaydi).

=============================================================================
⛔ RASTA KODLARI `code_sort` BO'YICHA — LEKSIKOGRAFIK TARTIB EMAS.

Oddiy `ORDER BY code` «1, 10, 100, 11, 2» berardi va hujjatdagi ro'yxat
odam o'qiy olmaydigan tartibda chiqardi (`resolve_stall_day_money()` da
o'lchangan aynan o'sha sabab). `DISTINCT` esa MAJBURIY: bitta sotuvchida
bitta rastaga IKKI biriktirish davri bo'lishi NORMAL (bo'shliqdan keyin
qaytgan sotuvchi) va kod ikki marta chiqardi. Ikkalasini bitta agregatda
qo'shib bo'lmagani uchun `DISTINCT` ichki so'rovda, tartib esa tashqarida.

⚠ `sa.period && daterange(:from_date, :to_date, '[]')` — DAVR ICHIDA
  KESISHGAN biriktirishlar. Yopiq oraliq (`'[]'`) ATAYIN: `to_date` ning
  O'ZI davrga kiradi va foydalanuvchi tanlagan oxirgi kun hisobotdan
  tushib qolmaydi.
"""


@dataclass(frozen=True, slots=True)
class ReceivableRow:
    """Qarzdorlik reestrining bitta qatori — ⛔ HUJJAT, operativ javob EMAS.

    `vendor_name` — ⛔ `str | None`. `None` = ism TOPILMADI («ismi yo'q»
        EMAS): sotuvchi qatori o'chirilgan yoki biriktirilmagan bo'lishi
        mumkin. Bo'shliq KO'RINADI va u to'ldirilmaydi (`_RECEIVABLE_ROWS`
        docstringining oxirgi bandi).

    `oldest_unpaid_date` — eng eski TO'LANMAGAN `daily_charges.service_date`,
        `FIFO_OLDEST_SERVICE_DATE_FIRST` qoidasidan. `None` = to'lanmagan
        hisob YO'Q (masalan sotuvchida AVANS bor, ya'ni qoldiq manfiy).

    `stall_codes` — davr ichida biriktirilgan rastalar, vergul bilan.
        `None` = davrda birorta biriktirish yo'q. ⚠ Bu maydon ismdan
        MUSTAQIL manbadan keladi va aynan shu sababdan nizoda ish beradi:
        ism yo'qolsa ham «qaysi rasta?» savoli javobsiz qolmaydi.
    """

    vendor_id: UUID
    vendor_name: str | None
    outstanding_soum: int
    oldest_unpaid_date: date | None
    stall_codes: str | None


async def receivables(
    session: AsyncSession,
    *,
    market_id: UUID,
    from_date: date,
    to_date: date,
) -> list[ReceivableRow]:
    """Davr kesimidagi qarzdorlik reestri — ⛔ ARIFMETIKA `billing_repo` DAN.

    =========================================================================
    ⛔ IKKI SANANING IKKI VAZIFASI VA ULAR BIR XIL EMAS:

      `to_date` — REESTR KESIMI. Qoldiq `to_date` kuni OXIRIDAGI holat,
          ya'ni `vendor_outstanding(as_of=to_date + 1 kun)`. `as_of`
          hisoblarni `service_date < as_of` bilan cheklaydi (to'lovlarni
          EMAS — `_VENDOR_OUTSTANDING` docstringi), shuning uchun bir kun
          qo'shilishi MAJBURIY: usiz `to_date` ning O'Z pattasi reestrdan
          tushib qolardi va direktor «kecha hisob yozilgan, lekin qarz
          o'smabdi» degan xulosaga kelardi.

      `from_date` — HUJJAT DAVRI. U `stall_codes` ni cheklaydi
          (davrda kesishgan biriktirishlar), ⛔ LEKIN `oldest_unpaid_date`
          ni CHEKLAMAYDI: eng eski to'lanmagan kun davrdan OLDIN bo'lishi
          MUMKIN va uni davr bilan kesish QARZNING YOSHINI yashirardi —
          holbuki reestr aynan shu savolga javob berish uchun bor.

    =========================================================================
    ⛔ `oldest_unpaid_date` `vendor_charge_allocation()` DAN — SOTUVCHI
       BOSHIGA BITTA CHAQIRUV, VA BU NARX ONGLI.

    «Qaysi kun to'lanmagan?» savolining javobi USTUNDA emas, NOMLANGAN
    QOIDADA yashaydi (`FIFO_OLDEST_SERVICE_DATE_FIRST`, D-24) —
    `payments.charge_id` MAVJUD EMAS (C-4). Qoidani SQL da qayta yozish
    IKKINCHI arifmetika bo'lardi va u bir kun `vendor_charge_allocation()`
    dan ajralib ketardi: bot bir kunni, hisobot boshqa kunni aytardi.

    ⚠ NARX: har QARZDOR sotuvchi uchun ikkita indeksli so'rov. Bu HUJJAT
      marshruti (kuniga bir necha marta), operativ yuza emas; qatorlar
      soni esa chaqiruvchi qatlamda chegaralanadi (`report_max_rows`,
      T-08-16). Chegara bu yerda QO'YILMAYDI.

    Returns:
        Qarzi NOLDAN FARQLI sotuvchilar, qarz bo'yicha KAMAYISH tartibida
        (teng bo'lsa `full_name`, so'ng `vendor_id`). ⛔ Bo'sh ro'yxat —
        HALOL javob: «bu davrda qarzdor yo'q».
    """
    # ⛔ `+ 1 kun` — funksiya docstringining birinchi bandi. `as_of` IKKALA
    #    chaqiruvda ham AYNAN bir xil, aks holda `vendor_outstanding()` va
    #    `vendor_charge_allocation()` bir kunni boshqacha sanardi va G-14
    #    ning tengligi buzilardi.
    as_of = to_date + timedelta(days=1)
    balances = await vendor_outstanding(session, market_id=market_id, as_of=as_of)
    if not balances:
        return []

    result = await session.execute(
        _RECEIVABLE_ROWS,
        {
            "market_id": market_id,
            "vendor_ids": list(balances.keys()),
            "outstanding_soums": list(balances.values()),
            "from_date": from_date,
            "to_date": to_date,
        },
    )

    rows: list[ReceivableRow] = []
    for row in result.mappings():
        vendor_id: UUID = row["vendor_id"]
        allocation = await vendor_charge_allocation(
            session, market_id=market_id, vendor_id=vendor_id, as_of=as_of
        )
        # ⛔ `min(...)`, `rows[0]` EMAS: eng eski kun QIYMATDAN chiqadi,
        #    kortejning TARTIBIDAN emas. Tartibga tayangan kod
        #    `allocate_charge_credit()` ning ichki saralashi o'zgargan kuni
        #    JIMGINA boshqa kunni ko'rsatardi.
        oldest_unpaid = min(
            (item.service_date for item in allocation.rows if item.unpaid_soum > 0),
            default=None,
        )
        name = row["vendor_name"]
        codes = row["stall_codes"]
        rows.append(
            ReceivableRow(
                vendor_id=vendor_id,
                vendor_name=None if name is None else str(name),
                outstanding_soum=int(row["outstanding_soum"]),
                oldest_unpaid_date=oldest_unpaid,
                stall_codes=None if codes is None else str(codes),
            )
        )
    return rows


# ===========================================================================
# 3. NOMUVOFIQLIK ARXIVI — IKKI SINF, IKKI SANOQ (D-05, 08-RESEARCH OQ-4)
# ===========================================================================

ARCHIVE_KIND_UNPAID: Final[str] = ReconciliationSubjectKind.OCCUPIED_UNPAID.value
"""«Band, lekin to'lovsiz» sinfi — ⛔ QIYMAT ENUMDAN, YANGI LITERAL EMAS.

Arxiv sinf nomini O'YLAB TOPMAYDI: u `reconciliation_cases.subject_kind`
ning AYNAN o'sha qiymatini qaytaradi. Yangi lug'at (`"unpaid"`) kiritilsa
javobdagi nom bilan bazadagi qiymat ajralib ketardi va nizoda «bu qaysi
sinf edi?» savoli ikki lug'at o'rtasida qolardi.
"""

ARCHIVE_KIND_UNREGISTERED: Final[str] = AnomalyKind.UNASSIGNED_OCCUPIED.value
"""«Ro'yxatga olinmagan savdo» sinfi — `billing_anomalies.kind` DAN.

`ARCHIVE_KIND_UNPAID` bilan aynan bir xil qaror va bir xil sabab.
"""

_ANOMALY_ARCHIVE = text(
    f"""
    WITH unpaid AS (
        SELECT rc.service_date                                     AS service_date,
               CAST(:kind_unpaid AS text)                          AS kind,
               s.code                                              AS stall_code,
               s.code_sort                                         AS code_sort,
               rc.status                                           AS case_status,
               (c.amount_soum + COALESCE(adj.total, 0))::bigint     AS amount_soum,
               ev.snapshot_id                                       AS evidence_snapshot_id
          FROM reconciliation_cases rc
          JOIN daily_charges c
            ON c.market_id = rc.market_id
           AND c.id = rc.charge_id
          JOIN stalls s
            ON s.market_id = c.market_id
           AND s.id = c.stall_id
          LEFT JOIN LATERAL (
            SELECT sum({_SIGNED_ADJUSTMENT_EXPR}) AS total
              FROM charge_adjustments a
             WHERE a.market_id = c.market_id
               AND a.charge_id = c.id
          ) adj ON true
          LEFT JOIN LATERAL (
            SELECT ce.snapshot_id AS snapshot_id
              FROM charge_evidence ce
             WHERE ce.market_id = c.market_id
               AND ce.charge_id = c.id
             ORDER BY ce.slot_time, ce.snapshot_id
             LIMIT 1
          ) ev ON true
         WHERE rc.market_id = :market_id
           AND rc.subject_kind = :subject_unpaid
           AND rc.service_date BETWEEN :from_date AND :to_date
    ),
    unregistered AS (
        SELECT ba.service_date  AS service_date,
               CAST(:kind_unregistered AS text) AS kind,
               s.code           AS stall_code,
               s.code_sort      AS code_sort,
               opened.status    AS case_status,
               CAST(NULL AS bigint) AS amount_soum,
               ba.snapshot_id   AS evidence_snapshot_id
          FROM billing_anomalies ba
          JOIN stalls s
            ON s.market_id = ba.market_id
           AND s.id = ba.stall_id
          LEFT JOIN LATERAL (
            SELECT rc2.status AS status
              FROM reconciliation_cases rc2
             WHERE rc2.market_id = ba.market_id
               AND rc2.anomaly_id = ba.id
             ORDER BY rc2.created_at DESC, rc2.id DESC
             LIMIT 1
          ) opened ON true
         WHERE ba.market_id = :market_id
           AND ba.kind = :anomaly_unregistered
           AND ba.service_date BETWEEN :from_date AND :to_date
    ),
    archive AS (
        SELECT * FROM unpaid
        UNION ALL
        SELECT * FROM unregistered
    )
    SELECT service_date,
           kind,
           stall_code,
           case_status,
           amount_soum,
           evidence_snapshot_id
      FROM archive
     ORDER BY service_date, kind, code_sort, stall_code
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("from_date", type_=Date()),
    bindparam("to_date", type_=Date()),
    bindparam("kind_unpaid", type_=Text()),
    bindparam("kind_unregistered", type_=Text()),
    bindparam("subject_unpaid", type_=Text()),
    bindparam("anomaly_unregistered", type_=Text()),
    bindparam("increase", type_=Text()),
)
"""Davr xronologiyasi — IKKI MANBA, BITTA RO'YXAT, IKKI SANOQ.

=============================================================================
⛔⛔ 1. IKKI SINF HECH QACHON QO'SHILMAYDI (6-faza D-05, `AnomalyCounts` naqshi).

`unpaid_count` va `unregistered_count` ALOHIDA qaytadi va ularning
yig'indisi javobda MAYDON sifatida MAVJUD EMAS. «Band, lekin to'lovsiz»
(hisob yozilgan, pul kelmagan) bilan «ro'yxatga olinmagan savdo» (rasta
band, sotuvchi biriktirilmagan) IKKI BOSHQA qarordan chiqadi va ikki
BOSHQA harakatni talab qiladi: birinchisi undirishni, ikkinchisi
RO'YXATGA OLISHNI. Bitta songa siqilgan hisobot qaysi sinf o'sganini
YASHIRARDI.

=============================================================================
⛔⛔ 2. XRONOLOGIYA BITTA RO'YXATDA, `kind` USTUNI BILAN (UI-SPEC §8.5).

Ikki alohida jadval bir hodisani IKKI JOYDA qidirtirardi: «shu rasta bilan
o'sha kuni nima bo'ldi?» degan savolga javob ikki ro'yxatdan qo'lda
yig'ilardi. Sinf USTUN bo'lganda esa u ham ko'rinadi, ham filtrlanadi.

=============================================================================
⛔⛔ 3. DALIL — FAQAT IDENTIFIKATOR (07 D-03, T-06-81).

`evidence_snapshot_id` — `UUID`. Kadr baytlari na javobda, na eksportda;
ombor kaliti ham, imzolangan havola ham YO'Q. Sabab huquqiy va u
muzokara qilinmaydi: kadrda tashrifchilar yuzi bor (O'zR shaxsiy
ma'lumotlar qonuni). Klient identifikatorni MAVJUD, autentifikatsiya
ostidagi kadr marshrutiga beradi.

=============================================================================
⛔ «TO'LANMAGAN» TA'RIFI BU YERDA IXTIRO QILINMAYDI.

`unpaid` shoxining manbai — `reconciliation_cases` (`subject_kind =
'occupied_unpaid'`), ya'ni `recon.open` ALLAQACHON qo'llagan predikat.
`daily_charges` − `payments` ni bu yerda qayta hisoblash UCHINCHI ta'rif
bo'lardi va u `reconciliation_repo` modul docstringining 3-bandi bilan
TAQIQLANGAN: bot bir sonni, hisobot boshqa sonni ko'rsatardi.

⚠ OQIBATI OCHIQ YOZILADI: `recon.open` yugurmagan kun uchun `unpaid`
  qatori BO'LMAYDI. Bu HALOL — arxiv ANIQLANGAN nomuvofiqliklarning
  hujjati, hisob-kitobning qayta bajarilishi emas.

=============================================================================
⚠ ARXIVDA UCHINCHI VA TO'RTINCHI SINF YO'Q VA BU NOMLANGAN QAROR:

    `closed_day_occupied` — yopiq kunda savdo (D-10);
    `no_coverage_stall`   — qamrovsiz rasta (D-05).

Ular kunlik ekranda `anomaly_list()` ning O'Z hisoblagichlari bilan
ko'rinadi. Davr arxivi RECON-04 ning IKKI nomlangan savoliga javob beradi
va uchinchi sinfni qo'shish uchinchi hisoblagichni ham talab qilardi —
ya'ni javobning shakli o'zgarardi. Band `deferred-items.md` da.

=============================================================================
⛔ `S608` — sabab `_REVENUE_BY_DAY` dagi bilan AYNAN bir xil: f-string ga
   faqat `billing_repo` dan import qilingan SOBIT `_SIGNED_ADJUSTMENT_EXPR`
   tushadi, har tashqi qiymat esa `bindparam(...)` bilan TIPLANGAN (T-08-14).
"""


@dataclass(frozen=True, slots=True)
class AnomalyArchiveRow:
    """Arxivning bitta qatori — ⛔ MAYDONLAR TO'PLAMI SHARTNOMA.

    `kind` — `ARCHIVE_KIND_UNPAID` yoki `ARCHIVE_KIND_UNREGISTERED`.
    `case_status` — `ReconciliationCaseStatus` ning YOPIQ to'rt a'zosidan
        biri, yoki `None` = case hali OCHILMAGAN («noma'lum» emas).
    `amount_soum` — `None` = HISOB YOZILMAGAN (D-28: biriktirilmagan
        rastaga hisob yozilmaydi). ⛔ Nol YOZILMAYDI: «summa yo'q» bilan
        «summa nol» ikki boshqa javob (UI-SPEC §9.4 ning aynan farqi).
    `evidence_snapshot_id` — kadrga KO'RSATKICH, `None` = dalil qatori yo'q.

    ⛔ KADR BAYTI, OMBOR KALITI VA IMZOLANGAN HAVOLA UCHUN MAYDON YO'Q va
       qo'shilmaydi (`_ANOMALY_ARCHIVE` docstringining 3-bandi). Yuzaning
       kengayishi aynan shu yerdan, bitta «qulaylik uchun» maydondan
       boshlanardi.
    """

    service_date: date
    kind: str
    stall_code: str
    case_status: str | None
    amount_soum: int | None
    evidence_snapshot_id: UUID | None


@dataclass(frozen=True, slots=True)
class AnomalyArchive:
    """Davr arxivi — ⛔ AYNAN UCH MAYDON: qatorlar VA IKKI ALOHIDA SANOQ.

    ⛔ TO'RTINCHI, «yig'indi» MAYDONI YO'Q va qo'shilmaydi (D-05). U mavjud
       bo'lsa ekran uni ko'rsatardi va ikki sinfning farqi matn darajasida
       yo'qolardi — `AnomalyCounts` da o'rnatilgan aynan o'sha qaror.

    ⚠ NOL SANOQ HAM NATIJA: uchala maydon ham har doim qaytadi. «Bu davrda
      nomuvofiqlik yo'q» bilan «hisoblagich ishlamayapti» bir xil
      ko'rinmasligi kerak (`occupancy.py:122-124` qoidasi).
    """

    rows: tuple[AnomalyArchiveRow, ...]
    unpaid_count: int
    unregistered_count: int


async def anomaly_archive(
    session: AsyncSession,
    *,
    market_id: UUID,
    from_date: date,
    to_date: date,
) -> AnomalyArchive:
    """Davr kesimidagi nomuvofiqlik arxivi — HOSILA so'rov, ikki manbadan.

    ⛔ CHAQIRUVCHI TENANT KONTEKSTINI O'RNATGAN BO'LISHI SHART: so'rovdagi
       `market_id` sharti NIYAT, RLS esa KAFOLAT (T-08-13).

    Args:
        market_id: tenant kaliti.
        from_date: davrning BIRINCHI kuni (kiradi).
        to_date: davrning OXIRGI kuni (kiradi).

    Returns:
        `AnomalyArchive` — qatorlar `service_date`, so'ng sinf, so'ng rasta
        kodining TABIIY tartibida (`code_sort`). Sanoqlar QATORLARDAN
        hosila.
    """
    result = await session.execute(
        _ANOMALY_ARCHIVE,
        {
            "market_id": market_id,
            "from_date": from_date,
            "to_date": to_date,
            "kind_unpaid": ARCHIVE_KIND_UNPAID,
            "kind_unregistered": ARCHIVE_KIND_UNREGISTERED,
            "subject_unpaid": ARCHIVE_KIND_UNPAID,
            "anomaly_unregistered": ARCHIVE_KIND_UNREGISTERED,
            "increase": _INCREASE,
        },
    )

    rows = tuple(
        AnomalyArchiveRow(
            service_date=row["service_date"],
            kind=str(row["kind"]),
            stall_code=str(row["stall_code"]),
            case_status=None if row["case_status"] is None else str(row["case_status"]),
            amount_soum=None if row["amount_soum"] is None else int(row["amount_soum"]),
            evidence_snapshot_id=row["evidence_snapshot_id"],
        )
        for row in result.mappings()
    )

    # ⛔ SANOQ QATORLARDAN HOSILA, IKKINCHI `count(*)` SO'ROVI BILAN EMAS
    #    (`anomaly_list()` da o'rnatilgan qoida): ikki so'rov orasida yangi
    #    qator yozilsa ro'yxat bilan sanoq ajralib ketardi va ekranda «3 ta»
    #    yozuvi ostida 2 qator turardi.
    return AnomalyArchive(
        rows=rows,
        unpaid_count=sum(1 for row in rows if row.kind == ARCHIVE_KIND_UNPAID),
        unregistered_count=sum(1 for row in rows if row.kind == ARCHIVE_KIND_UNREGISTERED),
    )


# ===========================================================================
# 4. QOG'OZ DAFTAR — YOZUV VA O'QISH YO'LI (D-17, Pattern 6, 08-14)
#
# ⛔⛔ BU BO'LIM MODUL DOCSTRINGINING 1-BANDIGA ZID EMAS.
#
# Yuqoridagi uch bo'lim HOSILA so'rov: ular mavjud qatorlardan hisoblaydi
# va hech nima yozmaydi. Daftar esa TASHQI MANBA — u tizimda umuman yo'q
# va uni hisoblab chiqarib bo'lmaydi, ya'ni «saqlangan agregat» taqig'i
# (D-03) bu jadvalga TEGISHLI EMAS: bu agregat emas, KIRISH ma'lumoti.
#
# ⚠ Aynan shu farq `ledger_entries` ni `daily_charges` dan ajratadi va u
#   `sbozor_core.models.ledger` modul docstringida uch band bilan
#   yozilgan.
# ===========================================================================

_LEDGER_UPSERT = text(
    """
    INSERT INTO ledger_entries (market_id, business_date, stall_id, amount_soum, imported_by)
    SELECT :market_id,
           CAST(:business_date AS date),
           u.stall_id,
           u.amount_soum,
           :imported_by
      FROM unnest(CAST(:stall_ids AS uuid[]), CAST(:amounts AS bigint[]))
             AS u(stall_id, amount_soum)
        ON CONFLICT (market_id, business_date, stall_id) DO UPDATE
       SET amount_soum = EXCLUDED.amount_soum,
           imported_by = EXCLUDED.imported_by,
           updated_at  = now()
 RETURNING (xmax = 0) AS inserted
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
    bindparam("stall_ids", type_=_UUID_ARRAY),
    bindparam("amounts", type_=_BIGINT_ARRAY),
    bindparam("imported_by", type_=_UUID),
)
"""Kunlik daftarni YOZADI — ⛔ `DO UPDATE`, `DO NOTHING` EMAS.

=============================================================================
⛔⛔ 1. IKKINCHI FAYL BIRINCHISINI ALMASHTIRADI (Pattern 6, D-17).

Daftar KUN ICHIDA tuzatiladi: kassir xato yozdi, keyin to'g'riladi va
ma'muriyat faylni QAYTA yuboradi. `DO NOTHING` birinchi (XATO) qiymatni
MUZLATIB qo'yardi va tuzatilgan daftar tizimga UMUMAN yetib bormasdi —
solishtiruv esa bilib turib noto'g'ri songa tayanardi.

⛔ BU `daily_charges` NING O'ZGARMASLIK QOIDASINI BUZMAYDI va sabab
   ikkalasining TABIATIDA: hisob — tizimning O'Z qarori (o'zgarmas,
   tuzatish alohida `charge_adjustments` qatori bo'ladi), daftar esa
   TASHQI QOG'OZNING NUSXASI. Nusxa manba o'zgarganda yangilanadi;
   qaror esa yangilanmaydi. Farq `sbozor_core.models.ledger` modul
   docstringining 2-bandida ham yozilgan.

=============================================================================
⛔ 2. IDEMPOTENTLIK DB KAFOLATI, ILOVA INTIZOMI EMAS.

Konflikt nishoni — `uq_ledger_entries_market_day_stall`
(`UNIQUE (market_id, business_date, stall_id)`, 0024). Ilova qatlamidagi
«avval tekshir, keyin yoz» ikki parallel import yugurishida IKKITA qator
yozardi (D-21 ning `notification_outbox` dagi bilan aynan bir sinf).

=============================================================================
⛔ 3. `xmax = 0` — «bu qator YANGI YARATILDIMI?» faktining yagona arzon
   manbai (`binding_repo._BIND_DIRECTOR_CHAT` da o'rnatilgan naqsh).
   `DO UPDATE` shoxida qator versiyasi yangilanadi va `xmax` noldan
   farqli bo'ladi, ya'ni ALMASHTIRILGAN qatorlarni SANASH uchun ikkinchi
   `SELECT` kerak emas — u yerda poyga oynasi ochilardi.

=============================================================================
⚠ `market_id` FAYLDAN OLINMAYDI (T-02-54 / T-08-60): u chaqiruvchining
  sessiyasidan keladi va shablonda bunday ustun umuman yo'q. Begona
  bozorning rastasi esa kompozit FK (`fk_ledger_entries_stall`) bilan
  STRUKTURAVIY imkonsiz — RLS o'chib qolgan holatda ham.

⚠ `unnest(...)` — qator boshiga bitta `INSERT` EMAS: 1000 rastali bozorda
  u 1000 ta borish-kelish bo'lardi. Ikki massiv bitta so'rovda ketadi va
  ikkalasi ham `bindparam(...)` bilan TIPLANGAN (T-08-14).
"""

_LEDGER_DAY = text(
    """
    SELECT le.stall_id   AS stall_id,
           s.code        AS stall_code,
           le.amount_soum AS amount_soum
      FROM ledger_entries le
      JOIN stalls s
        ON s.market_id = le.market_id
       AND s.id = le.stall_id
     WHERE le.market_id = :market_id
       AND le.business_date = CAST(:business_date AS date)
     ORDER BY s.code_sort, s.code
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("business_date", type_=Date()),
)
"""Bir KUNNING daftar qatorlari — ⛔ TARTIB `code_sort` BO'YICHA.

Oddiy `ORDER BY code` «1, 10, 100, 11, 2» berardi va imzolanadigan
varaqdagi ro'yxat odam o'qiy olmaydigan tartibda chiqardi
(`_RECEIVABLE_ROWS` da o'lchangan aynan o'sha sabab).

⚠ `JOIN stalls` ICHKI va bu XAVFSIZ: `fk_ledger_entries_stall` kompozit
  FK, ya'ni rastasi yo'q daftar qatori STRUKTURAVIY mavjud bo'la olmaydi.
  `LEFT JOIN` bu yerda hech qachon yuzaga kelmaydigan holatni qamragan
  bo'lardi va o'quvchini «demak kod `NULL` bo'lishi mumkin ekan» degan
  noto'g'ri xulosaga olib borardi.
"""


@dataclass(frozen=True, slots=True)
class LedgerDayRow:
    """Daftarning bir kun × bir rasta qatori (08-16 uch tomonlama solishtiruvi).

    `amount_soum` — ⛔ `0` QONUNIY qiymat va u «yozuv yo'q» DEGANI EMAS:
        «bu rastadan bugun hech nima yig'ilmadi» SC#5 ning eng muhim
        holati. «Yozuv yo'q» holati qatorning O'ZI bo'lmasligi bilan
        ifodalanadi.
    """

    stall_id: UUID
    stall_code: str
    amount_soum: int


@dataclass(frozen=True, slots=True)
class LedgerDay:
    """Kunning daftari — ⛔ QATORLAR **VA** «DAFTAR BORMI?» FAKTI.

    =========================================================================
    ⛔⛔ `has_ledger` YALANG'OCH RO'YXAT BILAN IFODALANMAYDI — VA BU
        UI-SPEC §10.6 NING BUTUN MAZMUNI.

    Daftar YUKLANMAGAN kunda uch ustunli jadvalni «hamma farq 0» bilan
    chizish MUVAFFAQIYATLI solishtiruv bo'lib ko'rinardi va IMZOLANARDI —
    ya'ni parallel rejimning butun maqsadi (SC#5) JIMGINA yo'qolardi.
    Chaqiruvchi shu sababdan `if not rows` emas, `has_ledger` ni o'qiydi:
    savol ikkita va ular BOSHQA javob talab qiladi —

        `has_ledger is False` -> «bu kun uchun daftar yuklanmagan»
        `has_ledger and not rows` -> «daftarda bu kun uchun qator yo'q»

    ⚠ BUGUNGI KUNDA IKKINCHI HOLAT YUZAGA KELMAYDI va bu ONGLI: import
      hodisasining O'Z jadvali YO'Q (08-02 ATAYIN faqat `ledger_entries`
      ni tug'dirgan), ya'ni «daftar bor» fakti qatorlarning MAVJUDLIGIDAN
      hosila. Maydon baribir ALOHIDA e'lon qilinadi, chunki chaqiruvchi
      (08-16, 08-18) SAVOLGA javob berishi kerak, ro'yxat uzunligini
      talqin qilishi emas — talqin ikki ekranda ikki xil yozilardi.
    =========================================================================
    """

    rows: tuple[LedgerDayRow, ...]
    has_ledger: bool


async def ledger_upsert(
    session: AsyncSession,
    *,
    market_id: UUID,
    business_date: date,
    rows: Sequence[LedgerImportRow],
    imported_by: UUID,
) -> int:
    """Kunlik daftarni yozadi (upsert); ALMASHTIRILGAN qatorlar sonini qaytaradi.

    ⛔ CHAQIRUVCHI TENANT KONTEKSTINI O'RNATGAN BO'LISHI SHART
       (`TenantSessionDep`): so'rovdagi `market_id` NIYAT, RLS esa
       KAFOLAT (`revenue_by_day()` dagi bilan aynan bir qoida).

    ⛔ TRANZAKSIYA BU YERDA OCHILMAYDI: sessiya allaqachon tranzaksiya
       ichida keladi va all-or-nothing shundan TEKIN keladi
       (`app/api/v1/imports.py` modul docstringi).

    Args:
        market_id: tenant kaliti.
        business_date: daftar QAYSI KUNGA yozilgan (DOMEN sanasi, import
            sanasi EMAS — model docstringi).
        rows: `validate_ledger_rows()` qabul qilgan qatorlar.
        imported_by: importni bajargan foydalanuvchi. ⚠ `users.id` ga FK
            YO'Q (model docstringi) — bu qiymat SESSIYADAN keladi, fayldan
            emas.

    Returns:
        ALMASHTIRILGAN (ya'ni allaqachon mavjud bo'lgan) qatorlar soni.
        `0` — hammasi yangi. Chaqiruvchi shundan «bu kun uchun daftar
        qayta yuklandimi?» degan javobni oladi va uni javobga ham,
        auditga ham yozadi.
    """
    if not rows:
        # Bo'sh ro'yxatda `unnest` baribir nol qator berardi, lekin so'rovni
        # umuman yubormaslik ARZONROQ va u «bo'sh massiv» tipini
        # aniqlashtirish savolini ham yo'q qiladi.
        return 0

    result = await session.execute(
        _LEDGER_UPSERT,
        {
            "market_id": market_id,
            "business_date": business_date,
            "stall_ids": [row.stall_id for row in rows],
            "amounts": [row.amount_soum for row in rows],
            "imported_by": imported_by,
        },
    )
    return sum(1 for row in result if not row.inserted)


async def ledger_day(
    session: AsyncSession,
    *,
    market_id: UUID,
    business_date: date,
) -> LedgerDay:
    """Kun uchun daftar qatorlari VA «daftar bormi?» fakti (UI-SPEC §10.6).

    ⛔ CHAQIRUVCHI TENANT KONTEKSTINI O'RNATGAN BO'LISHI SHART.

    Returns:
        `LedgerDay` — qatorlar rasta kodining TABIIY tartibida
        (`code_sort`). ⛔ Bo'sh natija HALOL javob: «bu kun uchun daftar
        yuklanmagan» va u `has_ledger is False` bilan AYTILADI, ro'yxat
        uzunligi bilan emas (klass docstringi).
    """
    result = await session.execute(
        _LEDGER_DAY,
        {"market_id": market_id, "business_date": business_date},
    )

    rows = tuple(
        LedgerDayRow(
            stall_id=row["stall_id"],
            stall_code=str(row["stall_code"]),
            amount_soum=int(row["amount_soum"]),
        )
        for row in result.mappings()
    )
    return LedgerDay(rows=rows, has_ledger=bool(rows))
