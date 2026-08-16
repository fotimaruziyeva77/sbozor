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
from typing import TYPE_CHECKING, Final

from sbozor_core.enums import AdjustmentDirection, PaymentKind
from sqlalchemy import Date, Text, bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.repositories.billing_repo import _SIGNED_ADJUSTMENT_EXPR, _SIGNED_PAYMENT_EXPR

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "RevenuePeriod",
    "RevenueRow",
    "revenue_by_day",
]

_UUID = PgUuid(as_uuid=True)

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
