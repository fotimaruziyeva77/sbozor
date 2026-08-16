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

from sbozor_core.enums import AdjustmentDirection, PaymentKind
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
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "ReceivableRow",
    "RevenuePeriod",
    "RevenueRow",
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
