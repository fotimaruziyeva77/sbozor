"""Fazaning PUL MANTIG'I — bitta modul, yetti funksiya (BILL-01…BILL-05).

=============================================================================
⛔⛔ D-16 / C-8 — UMUMIY QILINADIGAN NARSA **PUL YECHIMI**, BANDLIK
   DARVOZASI EMAS. VA BU FARQ O'LCHANGAN, USLUBIY EMAS.

D-16 «kutilayotgan patta kun yopilishi bilan BITTA kod yo'lidan yuradi,
faqat parametri boshqa» deydi. C-8 uni o'lchadi va **so'zma-so'z
bajarilmasligini** ko'rsatdi: proyeksiya **bugungi** kun uchun ishlaydi,
`stall_slot_occupancy` esa bugun uchun **bo'sh** (u kechasi 03:40 da
`day_close` bilan to'ladi, C-3). Ya'ni bandlik darvozasini ham bo'lishish
proyeksiyani **har doim 0 rasta** ko'rsatadigan qilardi va BILL-05 ekrani
bo'sh turardi — hech qanday xatosiz.

BILL-05 ning matni buni allaqachon hal qilgan: «kutilayotgan patta =
bugungi tarif + eski qarz», **bandlik shartisiz**. Shuning uchun bo'linadigan
narsa aynan `resolve_stall_day_money(market_id, as_of)`:

    BILL-05 proyeksiyasi:  as_of = bugun            (+ qoldiq)
    billing_close (06-07): as_of = business_date    (+ bandlik darvozasi
                                                     + yopiq kun + biriktirish)

D-16 ning MAQSADI — «kassir yig'gan summa kechqurun yozilgan summadan farq
qilmasin» — shu bilan bajariladi: **summa bitta funksiyadan keladi** va
farq `tests/integration/test_billing_repo.py` da `==` bilan o'lchanadi.

=============================================================================
⛔ QOIDALAR BU YERDA QAYTA YOZILMAYDI, CHAQIRILADI.

    hisob sharti   -> `sbozor_core.billing.billable_from_slots()`   (06-01)
    taqsimlash     -> `sbozor_core.billing.allocate_charge_credit()` (06-01)
    qo'shish amali -> `sbozor_core.billing.total_due_soum()`         (06-01)
    kalendar       -> DB `market_is_open(market_id, date)`           (02-faza)
    pul chegarasi  -> `sbozor_core.money.assert_safe_soum()`
    xato kodlari   -> `app.services.billing_errors`                  (06-02)

SQL faqat **qatorlarni yig'ib beradi**. Predikat yoki arifmetika ikki joyda
(SQL va sof funksiya) yashasa ular **bir kun ajralib ketardi** va o'shanda
`tests/unit/test_billable_from_slots.py` / `test_payment_credit_rules.py`
jadval testlari **hech nimani kafolatlamasdi** — ular sof funksiyani
o'lchardi, mahsulot esa SQL dan yurardi.

=============================================================================
⛔ CHAQIRUVCHI UCHUN SHART: TENANT KONTEKSTI (Pitfall 9).

`market_is_open()` ATAYIN `SECURITY DEFINER` **emas** va fail-closed, ya'ni
`set_tenant_context()` o'rnatilmagan sessiyada RLS unga 0 qator ko'rsatadi
va u **har kunni yopiq** deb qaytaradi. O'shanda `billing_close` birorta
hisob yozmasdi va nosozlik faqat oyning oxirida, tushum nolga tushganda
ko'rinardi. Shuning uchun bu moduldagi HAR bir funksiya `set_tenant_context()`
ostidagi sessiyada chaqirilishi **shart** (`day_close.py::_tenant_session`
naqshi).

=============================================================================
⛔ PUL — BUTUN SO'M (`BIGINT` <-> `int`), D-11. Kasrli tiplar bu modulda
   umuman uchramaydi va bu 06-06 rejasining qabul mezoni bilan MEXANIK
   qulflangan (fayl matni grep qilinadi). Sabab mahsulotning o'zagida:
   yaxlitlanish drifti aynan SBOZOR oldini olish uchun mavjud bo'lgan
   nizoni tug'diradi (D-02).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sbozor_core.money import assert_safe_soum
from sqlalchemy import Date, Text, bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.services.billing_errors import (
    AMOUNT_UNAVAILABLE_REASONS,
    MARKET_CLOSED,
    TARIFF_MISSING,
)

if TYPE_CHECKING:
    from datetime import date

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "StallDayMoney",
    "resolve_stall_day_money",
]

_UUID = PgUuid(as_uuid=True)


# ===========================================================================
# 1. PUL YECHIMI — YAGONA FUNKSIYA (D-16, D-09, C-8, OQ-5)
# ===========================================================================

_STALL_DAY_MONEY = text(
    """
    WITH calendar AS MATERIALIZED (
        SELECT market_is_open(:market_id, :as_of) AS market_open
    )
    SELECT s.id            AS stall_id,
           s.code          AS stall_code,
           asg.vendor_id   AS vendor_id,
           tar.tariff_id   AS tariff_id,
           tar.amount_soum AS tariff_amount_soum,
           cal.market_open AS market_open
      FROM stalls s
      CROSS JOIN calendar cal
      LEFT JOIN LATERAL (
        SELECT p.category_id
        FROM stall_category_periods p
        WHERE p.market_id = s.market_id
          AND p.stall_id = s.id
          AND p.valid_from <= :as_of
        ORDER BY p.valid_from DESC
        LIMIT 1
      ) cur ON true
      LEFT JOIN LATERAL (
        SELECT t.id AS tariff_id, t.amount_soum
        FROM tariffs t
        WHERE t.market_id = s.market_id
          AND t.category_id = cur.category_id
          AND t.valid_from <= :as_of
        ORDER BY t.valid_from DESC
        LIMIT 1
      ) tar ON true
      LEFT JOIN LATERAL (
        SELECT sa.vendor_id
        FROM stall_assignments sa
        WHERE sa.market_id = s.market_id
          AND sa.stall_id = s.id
          AND sa.period @> :as_of
        LIMIT 1
      ) asg ON true
     WHERE s.market_id = :market_id
       AND (:stall_id IS NULL OR s.id = :stall_id)
       AND (:stall_code IS NULL OR s.code = :stall_code)
     ORDER BY s.code_sort, s.id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("as_of", type_=Date()),
    bindparam("stall_id", type_=_UUID),
    bindparam("stall_code", type_=Text()),
)
"""`stall_repo.py:602-629` ning KENGAYTMASI — verbatim, uch ATAYIN farq bilan.

=============================================================================
FARQLAR VA ULARNING SABABI:

  1. `:today` -> `:as_of`. Manba so'rov reyestr ekrani uchun «bugun» ni
     biladi; pul yechimi esa **argumentli kun** bilan ishlaydi (D-12/D-16).
  2. ⛔ `t.id` HAM olinadi (D-09). Yozilgan hisob `tariff_id` ni **ham**,
     summani **ham** saqlaydi: yolg'iz `tariff_id` kelajakdagi tahrirga
     ochiq bo'lardi va tarif keyin o'zgartirilganda o'tmishdagi hisob
     RETROAKTIV o'zgargandek ko'rinardi.
  3. `market_is_open()` MATERIALIZED CTE da — kalendar mantig'i
     TAKRORLANMAYDI (S-4) va u 1000 rasta uchun 1000 marta hisoblanmaydi.

=============================================================================
⛔ `valid_from <= :as_of` — D-09 NING IKKINCHI YARMI.

Kelajakdagi tarif qatori (`valid_from > as_of`) **olinmaydi**. Usiz
`ORDER BY ... DESC LIMIT 1` ertaga kuchga kiradigan narxni bugungi hisobga
yozardi. Seed buni AYNAN o'lchaydi: `D` kunida 15 000, `D + 1` dan 20 000.

⚠ `tariffs.valid_to` USTUNI YO'Q va uni izlab yurish shart emas: 2-faza
  amal qilish oynasini `LEAD(valid_from)` bilan hosila qiladi, ya'ni
  «joriy narx» = `valid_from <= kun` bo'yicha ENG SO'NGGI qator.

=============================================================================
⛔ `stall_code` bo'yicha filtr — ANIQ MOSLIK, prefiks EMAS.

Kassir `Enter` bosganda AYNAN BITTA natija kutiladi (02-UI-SPEC §6.9) va
prefiks semantikasi bu bo'g'inda «qaysi rastaning summasi?» savolini
javobsiz qoldirardi. Ko'p moslik holati BITTA qavat yuqorida —
`pending_projection()` da — hal qilinadi.

=============================================================================
⚠ ALMASHINUV KUNI (OQ-5): `sa.period @> :as_of` `[)` konventsiyasi tufayli
  YANGI sotuvchini beradi (`periods.py:19-33`). `LIMIT 1` da `ORDER BY`
  KERAK EMAS va bu tanlov emas, STRUKTURA: `ex_stall_assignments_no_overlap`
  bir kunda ikki biriktirishni **ifodalab bo'lmaydigan** qiladi
  (`models/market.py:619-625`). Kafolat konstraytda, so'rovda emas — va
  test buni konstraytni sinab isbotlaydi.

⚠ BO'SHLIQ (`vendor_id IS NULL`) XATO EMAS: `periods.py:29-33` uni ATAYIN
  ruxsat etadi va u aynan BILL-04/D-28 anomaliyasining manbai.
"""


@dataclass(frozen=True, slots=True)
class StallDayMoney:
    """Bir RASTANING bir KUNDAGI puli — ⛔ NOL EMAS, NATIJA.

    Hamma maydon HAR DOIM qaytariladi (`day_close.DayCloseResult` qoidasi):
    chaqiruvchi «nega summa yo'q?» degan savolga javobni **yonida** topadi
    va ikkinchi so'rov yubormaydi.

    ⛔ JUFTLANGAN INVARIANT (UI-SPEC §9.2 ning SERVER yarmi):

        (amount_soum is None) == (unavailable_reason is not None)

    «Sababsiz yo'q summa» ham, «summasi bor sabab» ham **ifodalab
    bo'lmaydi**. Naqsh `NO_COVERAGE_IS_PAIRED_CHECK` dan
    (`models/occupancy.py:333-344`) — ikki tomonlama tenglik ikkala
    nosozlikni ham yopadi.

    ⚠ `market_open` ALOHIDA maydon va u `unavailable_reason` dan HOSILA
      QILINMAYDI: UI-SPEC §9.2 uni mustaqil maydon sifatida talab qiladi
      va uni ikkinchi so'rov bilan olish yarim tunda **boshqa kunning**
      javobini berardi. Bu yerda u AYNI so'rovdan, AYNI `as_of` bilan
      keladi.
    """

    stall_id: UUID
    stall_code: str
    vendor_id: UUID | None
    tariff_id: UUID | None
    amount_soum: int | None
    unavailable_reason: str | None
    market_open: bool


def _money_from_row(
    *,
    stall_id: UUID,
    stall_code: str,
    vendor_id: UUID | None,
    tariff_id: UUID | None,
    tariff_amount_soum: int | None,
    market_open: bool,
) -> StallDayMoney:
    """Xom qatordan `StallDayMoney` — juftlangan invariant SHU YERDA majburlanadi.

    ⛔ TARTIB AHAMIYATLI: yopiq kun tarifning yo'qligidan USTUN. Yopiq
       kunda tarif belgilanmagan bo'lsa ham kassirga «bugun bozor yopiq»
       deyish kerak, «tarif belgilanmagan» emas — ikkinchisi uni tarif
       sahifasiga yuborardi va u yerda tuzatadigan hech nima yo'q edi
       (UI-SPEC §9.4 ning ikki qatori aynan shu farqni chizadi).

    ⚠ `assert` BAYONOTI ISHLATILMAYDI: ruff `S101` uni mahsulot kodida
      taqiqlaydi va `python -O` uni butunlay olib tashlardi — ya'ni
      nazorat aynan ishlab chiqarish rejimida yo'qolardi
      (`sbozor_core.billing` da o'rnatilgan qoida).
    """
    amount: int | None
    reason: str | None
    if not market_open:
        amount, reason = None, MARKET_CLOSED
    elif tariff_amount_soum is None:
        amount, reason = None, TARIFF_MISSING
    else:
        amount, reason = assert_safe_soum(int(tariff_amount_soum)), None

    if (amount is None) != (reason is not None):
        raise AssertionError(
            "resolve_stall_day_money(): juftlangan invariant buzildi — "
            f"amount_soum={amount!r}, unavailable_reason={reason!r}"
        )
    if reason is not None and reason not in AMOUNT_UNAVAILABLE_REASONS:
        raise AssertionError(
            f"resolve_stall_day_money(): {reason!r} yopiq to'plamda yo'q. "
            f"Yangi sabab `AMOUNT_UNAVAILABLE_REASONS` reyestriga qo'shilishi "
            f"SHART (D-32): {sorted(AMOUNT_UNAVAILABLE_REASONS)}"
        )

    return StallDayMoney(
        stall_id=stall_id,
        stall_code=stall_code,
        vendor_id=vendor_id,
        tariff_id=tariff_id,
        amount_soum=amount,
        unavailable_reason=reason,
        market_open=market_open,
    )


async def resolve_stall_day_money(
    session: AsyncSession,
    *,
    market_id: UUID,
    as_of: date,
    stall_id: UUID | None = None,
    stall_code: str | None = None,
) -> list[StallDayMoney]:
    """⛔ FAZANING YAGONA PUL YECHIMI — proyeksiya ham, kun yopilishi ham SHU YERDAN.

    Tartib `stalls.code_sort` bo'yicha (SERVERDA, klientda emas): kod
    `text` va oddiy `ORDER BY code` «1, 10, 100, 11, 2» berardi, ya'ni
    kassir qidirayotgan rasta ko'z bilan topilmaydigan joyga tushardi
    (`models/market.py:154-183`).

    ⛔ CHAQIRUVCHI TENANT KONTEKSTINI O'RNATGAN BO'LISHI SHART (modul
       docstringi): `market_is_open()` INVOKER va fail-closed.

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        as_of: pul yechiladigan kun — tarif ham, biriktirish ham, kalendar
            ham AYNAN shu kunga qaraydi.
        stall_id: bitta rasta bo'yicha filtr (ixtiyoriy).
        stall_code: ANIQ kod bo'yicha filtr (ixtiyoriy, prefiks EMAS).

    Returns:
        `code_sort` tartibidagi `StallDayMoney` ro'yxati. Bo'sh ro'yxat —
        «bunday rasta yo'q» degan HALOL javob.
    """
    result = await session.execute(
        _STALL_DAY_MONEY,
        {
            "market_id": market_id,
            "as_of": as_of,
            "stall_id": stall_id,
            "stall_code": stall_code,
        },
    )
    return [
        _money_from_row(
            stall_id=row["stall_id"],
            stall_code=str(row["stall_code"]),
            vendor_id=row["vendor_id"],
            tariff_id=row["tariff_id"],
            tariff_amount_soum=row["tariff_amount_soum"],
            market_open=bool(row["market_open"]),
        )
        for row in result.mappings()
    ]
