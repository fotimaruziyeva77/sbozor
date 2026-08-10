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
from typing import TYPE_CHECKING, Final
from uuid import UUID

from sbozor_core.billing import billable_from_slots
from sbozor_core.enums import AnomalyKind, OccupancyVerdict
from sbozor_core.models import BillingAnomaly, ChargeEvidence, DailyCharge
from sbozor_core.money import assert_safe_soum
from sqlalchemy import Date, Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.services.billing_errors import (
    AMOUNT_UNAVAILABLE_REASONS,
    MARKET_CLOSED,
    TARIFF_MISSING,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date, time

    from sbozor_core.billing import BillableDecision
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "SlotEvidenceRow",
    "StallDayMoney",
    "StallSlotVerdict",
    "billable_stalls",
    "resolve_stall_day_money",
    "write_anomaly",
    "write_charge",
    "write_evidence",
]

_UUID = PgUuid(as_uuid=True)
_UUID_ARRAY = ARRAY(PgUuid(as_uuid=True))

_OCCUPIED: Final[str] = OccupancyVerdict.OCCUPIED.value
"""Qiymat so'rov PARAMETRI, so'rov MATNIDAGI literal emas.

`occupancy_repo.py:94-101` da o'rnatilgan qoida: literal yozilganda enum
o'zgargan kuni filtr jimgina hech nimaga tushmasdi — so'rov ishlayverardi,
faqat natija bo'sh bo'lardi.
"""


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


# ===========================================================================
# 2. BANDLIK — FAQAT O'QISH (D-03, D-04, C-6)
# ===========================================================================

_BILLABLE_SLOT_ROWS = text(
    """
    SELECT sso.stall_id                   AS stall_id,
           s.code                         AS stall_code,
           sso.id                         AS stall_slot_occupancy_id,
           sso.slot_time                  AS slot_time,
           sso.verdict                    AS verdict,
           sso.resolution_source          AS resolution_source,
           sso.winning_occupancy_event_id AS winning_occupancy_event_id
      FROM stall_slot_occupancy sso
      JOIN stalls s
        ON s.market_id = sso.market_id
       AND s.id = sso.stall_id
     WHERE sso.market_id = :market_id
       AND sso.business_date = :service_date
     ORDER BY s.code_sort, sso.stall_id, sso.slot_time
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("service_date", type_=Date()),
)
"""XOM slot qatorlari — ⛔ QAROR SQL DA EMAS (C-6, D-04).

=============================================================================
⛔⛔ NEGA `bool_or(...)` SHU YERDA HISOBLANMAYDI.

`occupancy_repo.py:364-384` dagi `_PER_STALL_CTE` bo'lakni SQL da
hisoblaydi va bu **hisobot uchun to'g'ri**. Billing esa qarorni
`sbozor_core.billing.billable_from_slots()` (06-01) bilan **Pythonda**
chiqaradi va sabab O'LCHOV: predikat ikki joyda (SQL va sof funksiya)
yashasa ular bir kun ajralib ketardi va
`tests/unit/test_billable_from_slots.py` ning jadval testi **hech nimani
kafolatlamasdi**.

⚠ MIQYOS ARZON: 1000 rasta x 5 slot = 5000 qator/bozor/kun. Bu Pythonga
  olib kelinadigan hajm sifatida ahamiyatsiz, SQL ga ko'chirishdan
  yutiladigan vaqt esa yuqoridagi xavfni to'lamaydi.

=============================================================================
⛔ IKKI USTUN NOMINING IKKI MA'NOSI (Pitfall 1) — YONMA-YON:

    stall_slot_occupancy.business_date  = MA'LUMOT TEGISHLI kun
                                          (`snapshots` dan NUSXALANADI)
    daily_charges.business_date         = QATOR YOZILGAN kun
                                          (`created_at` dan GENERATED)

Shuning uchun bu so'rov `sso.business_date = :service_date` bo'yicha
filtrlaydi: hisobning domen ustuni `service_date` deb ATAYIN boshqa
nomlangan. Ikkalasini `business_date` bo'yicha join qilish normal kunda
**0 qator** berardi (job D+1 da yuguradi) — hisobot bo'sh, xato yo'q.

=============================================================================
⛔ SLOT QATORI UMUMAN BO'LMAGAN RASTA BU RO'YXATGA KIRMAYDI va bu Pitfall 2
   ning o'lchov nuqtasi: `billing_close(D)` ni `day_close(D)` dan OLDIN
   yugurtirganda natija bo'sh bo'ladi va chaqiruvchi buni `no_slot_rows`
   deb SANAYDI — «hammasi bo'sh» degan yolg'on hisobot bermaydi.
"""


@dataclass(frozen=True, slots=True)
class SlotEvidenceRow:
    """Bitta slot qatori — qaror uchun JUFTLIK, dalil uchun UCHLIK.

    ⛔ `winning_occupancy_event_id` — D-08 ning MUZLATILGAN pointeri (C-7);
       `stall_slot_occupancy_id` esa faqat AUDIT havolasi, chunki o'sha
       qator MUTABLE (`_MATERIALIZE_SLOT` `DO UPDATE` ishlatadi).
    """

    stall_slot_occupancy_id: UUID
    slot_time: time
    verdict: str
    resolution_source: str
    winning_occupancy_event_id: UUID | None


@dataclass(frozen=True, slots=True)
class StallSlotVerdict:
    """Bir rastaning bir kundagi slotlari va ulardan chiqqan QAROR."""

    stall_id: UUID
    stall_code: str
    rows: tuple[SlotEvidenceRow, ...]
    decision: BillableDecision


async def billable_stalls(
    session: AsyncSession, *, market_id: UUID, service_date: date
) -> list[StallSlotVerdict]:
    """Shu kunning slot qatorlari + D-04 qarori — ⛔ FAQAT O'QISH (D-03).

    ⛔ `occupancy_events` DAN QAYTA AGREGATSIYA TAQIQLANADI: agregatsiya
       5-fazada tugagan va ikkinchi marta qilinsa u **ikkinchi haqiqat
       manbai** bo'lardi — direktor bandlik sahifasida bitta son, patta
       hisobida boshqa son ko'rardi va ikkalasi ham «to'g'ri» bo'lardi.

    Returns:
        `code_sort` tartibida, faqat SLOT QATORI BOR rastalar. Ro'yxatga
        kirmagan rasta — `no_slot_rows` holati (Pitfall 2).
    """
    result = await session.execute(
        _BILLABLE_SLOT_ROWS, {"market_id": market_id, "service_date": service_date}
    )

    order: list[UUID] = []
    codes: dict[UUID, str] = {}
    grouped: dict[UUID, list[SlotEvidenceRow]] = {}
    for row in result.mappings():
        stall_id: UUID = row["stall_id"]
        if stall_id not in grouped:
            order.append(stall_id)
            grouped[stall_id] = []
            codes[stall_id] = str(row["stall_code"])
        grouped[stall_id].append(
            SlotEvidenceRow(
                stall_slot_occupancy_id=row["stall_slot_occupancy_id"],
                slot_time=row["slot_time"],
                verdict=str(row["verdict"]),
                resolution_source=str(row["resolution_source"]),
                winning_occupancy_event_id=row["winning_occupancy_event_id"],
            )
        )

    return [
        StallSlotVerdict(
            stall_id=stall_id,
            stall_code=codes[stall_id],
            rows=tuple(grouped[stall_id]),
            # ⛔ QAROR 06-01 DAN — predikat ikkinchi marta O'YLAB TOPILMAYDI.
            decision=billable_from_slots(
                [(row.verdict, row.resolution_source) for row in grouped[stall_id]]
            ),
        )
        for stall_id in order
    ]


# ===========================================================================
# 3. YOZISH — HISOB, DALIL, ANOMALIYA (D-06, D-08, D-28, C-12)
# ===========================================================================


async def write_charge(
    session: AsyncSession,
    *,
    market_id: UUID,
    stall_id: UUID,
    service_date: date,
    money: StallDayMoney,
) -> UUID | None:
    """Kunlik pattani IDEMPOTENT yozadi — ⛔ `DO NOTHING`, `DO UPDATE` EMAS.

    =======================================================================
    ⛔ D-06/D-07 — YOZILGAN HISOB O'ZGARMAS VA QAYTA YUGURISH UNGA TEGMAYDI.

    `DO UPDATE` shakli `occupancy_repo._MATERIALIZE_SLOT` da TO'G'RI
    (u HOSILA jadval), bu yerda esa TESKARI qaror: `daily_charges` — pul
    yozuvi va uni jimgina yangilash sotuvchining bilgan summasini kechasi
    o'zgartirardi. Naqshni ko'chirish aynan shu xatoga olib borardi
    (`06-PATTERNS.md` Gotcha 1).

    ⚠ `index_elements` ISHLATILADI, konstrayt NOMI emas: kalitning uchala
      ustuni ham ODDIY (`market_id`, `stall_id`, `service_date`).
      `capture_repo.py:338-341` da konstrayt nomi kerak edi, chunki u
      yerda kalitda HISOBLANADIGAN ustun bor.
    =======================================================================
    ⛔ D-28 — `vendor_id` YO'Q BO'LSA BU FUNKSIYA UMUMAN CHAQIRILMAYDI.

    «Kimdir qarzdor, lekin kim ekani noma'lum» yozuvi qarz hisobotini
    buzardi: summa jamida ko'rinardi, lekin birorta sotuvchining qarziga
    tushmasdi. Chaqiruvchi buning o'rniga `unassigned_occupied` anomaliyasi
    yozadi. Shart shu yerda ham majburlanadi, chunki `ValueError` xato
    TURINI saqlaydi — `IntegrityError` esa uni yo'qotib, jobda
    «billing_close_failed» bo'lib ko'rinardi.
    =======================================================================

    Returns:
        Yangi yozilgan hisobning `id` si, yoki `None` — ⛔ **XATO EMAS**:
        «bu rasta-kunga hisob ALLAQACHON bor» (Pitfall 3). Chaqiruvchi
        buni `skipped_existing` deb sanaydi.
    """
    if money.vendor_id is None:
        raise ValueError(
            f"write_charge(): {money.stall_code!r} rastasiga {service_date} kunida "
            "sotuvchi biriktirilmagan — hisob YOZILMAYDI (D-28). Chaqiruvchi "
            f"{AnomalyKind.UNASSIGNED_OCCUPIED.value!r} anomaliyasini yozishi kerak."
        )
    if money.tariff_id is None or money.amount_soum is None:
        raise ValueError(
            f"write_charge(): {money.stall_code!r} rastasi uchun {service_date} kunida "
            f"summa yo'q ({money.unavailable_reason!r}) — hisob YOZILMAYDI. Yopiq kun "
            "va tarifsiz rasta anomaliya yo'lidan ketadi (D-10 / TARIFF_MISSING)."
        )

    stmt = (
        pg_insert(DailyCharge)
        .values(
            market_id=market_id,
            stall_id=stall_id,
            service_date=service_date,
            vendor_id=money.vendor_id,
            tariff_id=money.tariff_id,
            # ⛔ D-09: IKKALASI HAM. `tariff_id` yolg'iz kelajakdagi
            #   tahrirga ochiq, summa yolg'iz esa «qaysi tarifdan?»
            #   savolini javobsiz qoldirardi.
            tariff_amount_soum=money.amount_soum,
            amount_soum=money.amount_soum,
        )
        .on_conflict_do_nothing(index_elements=["market_id", "stall_id", "service_date"])
        .returning(DailyCharge.id)
    )
    charge_id: UUID | None = (await session.execute(stmt)).scalar_one_or_none()
    return charge_id


_EVIDENCE_SNAPSHOTS = text(
    """
    SELECT ev.id          AS occupancy_event_id,
           ev.snapshot_id AS snapshot_id
      FROM occupancy_events ev
     WHERE ev.market_id = :market_id
       AND ev.id = ANY(:event_ids)
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("event_ids", type_=_UUID_ARRAY),
)
"""Kadrga yo'l — ⛔ NUSXA OLINADI, so'rov sifatida saqlanmaydi (D-08/C-7).

`charge_evidence.snapshot_id` `occupancy_events` dan **bir marta** olinadi
va hisob bilan birga muzlaydi. `occupancy_events` shartsiz o'zgarmas
(`0018`), ya'ni nusxa hech qachon eskirmaydi — `stall_slot_occupancy` esa
MUTABLE va uning `id` si kech kelgan tasdiqdan keyin **boshqa hodisaga**
ishora qilishi mumkin.
"""


async def write_evidence(
    session: AsyncSession,
    *,
    market_id: UUID,
    charge_id: UUID,
    slot_rows: Sequence[SlotEvidenceRow],
) -> int:
    """Hisobning rasm-dalilini MUZLATIB yozadi (D-08, C-7, D-29).

    =======================================================================
    ⛔ DALIL — SO'ROV EMAS, NUSXA. Keyin qayta hisoblangan so'rov boshqa
       javob bersa ham, nizoda ko'rsatiladigan kadr O'ZGARMAYDI. Bu
       5-fazaning `audit_rounds.frame_size` «muzlatilgan doira» qarorining
       aynan o'zi.

    ⛔ FAQAT `occupied` VA G'OLIB HODISASI BOR QATORLAR yoziladi.
       `SLOT_OCCUPIED_HAS_WINNER_CHECK` (`models/occupancy.py:317-331`)
       bo'yicha g'olib hodisa AYNAN `occupied` da mavjud, ya'ni
       `winning_occupancy_event_id IS NULL` bo'lgan qator dalil BERA
       OLMAYDI va uni o'tkazib yuborish yagona to'g'ri xulq — `NULL` bilan
       yozishga urinish `charge_evidence` ning `NOT NULL` iga urilardi.

    ⛔ `on_conflict_do_nothing` — job qayta yugurishi dublikat dalil
       yaratmaydi va «nechta slotda band edi?» sanog'ini SHISHIRMAYDI.
    =======================================================================

    Returns:
        YANGI yozilgan dalil qatorlari soni. Nol — natija (qayta yugurish).
    """
    winners = [
        row
        for row in slot_rows
        if row.verdict == _OCCUPIED and row.winning_occupancy_event_id is not None
    ]
    if not winners:
        return 0

    lookup = await session.execute(
        _EVIDENCE_SNAPSHOTS,
        {
            "market_id": market_id,
            "event_ids": [row.winning_occupancy_event_id for row in winners],
        },
    )
    snapshot_by_event: dict[UUID, UUID] = {
        row["occupancy_event_id"]: row["snapshot_id"] for row in lookup.mappings()
    }

    values = [
        {
            "market_id": market_id,
            "charge_id": charge_id,
            "stall_slot_occupancy_id": row.stall_slot_occupancy_id,
            "occupancy_event_id": row.winning_occupancy_event_id,
            "snapshot_id": snapshot_by_event[event_id],
            "slot_time": row.slot_time,
        }
        for row in winners
        if (event_id := row.winning_occupancy_event_id) in snapshot_by_event
    ]
    if not values:
        return 0

    stmt = (
        pg_insert(ChargeEvidence)
        .values(values)
        .on_conflict_do_nothing(
            index_elements=["market_id", "charge_id", "stall_slot_occupancy_id"]
        )
        .returning(ChargeEvidence.id)
    )
    return len((await session.execute(stmt)).all())


async def write_anomaly(
    session: AsyncSession,
    *,
    market_id: UUID,
    stall_id: UUID,
    service_date: date,
    kind: AnomalyKind,
    occupancy_event_id: UUID | None = None,
    snapshot_id: UUID | None = None,
) -> UUID | None:
    """Uchala anomaliya turi uchun BITTA funksiya (D-05, D-10, D-28, C-12).

    =======================================================================
    ⛔ JUFTLANGAN SHART ILOVA QATLAMIDA HAM MAJBURLANADI — `CHECK` BILAN
       BIRGA, IKKI QATLAM:

        no_coverage_stall   -> dalil YO'Q  (`occupancy_event_id` None)
        unassigned_occupied -> dalil BOR
        closed_day_occupied -> dalil BOR

    `CHECK` ni `IntegrityError` bilan ushlash xato TURINI yo'qotardi va
    06-07 uni `billing_close_failed` deb yozib qo'yardi — ya'ni dasturchi
    xatosi ish vaqti nosozligiga aylanardi.

    =======================================================================
    ⛔ D-05 NING ANIQ MA'NOSI: `no_coverage_stall` — BILL-04 ANOMALIYASI
       EMAS. U alohida `kind` va hisobotda ALOHIDA sanaladi. «Ko'ra
       olmadik» != «band, lekin biriktirilmagan»; ikkisini qo'shish
       KO'R NUQTADAN TUSHUM DA'VOSI TO'QISH bo'lardi (0-fazadagi ~10 %
       qamrovsizlik aynan shu bayroq ostida ko'rinadi).

    Returns:
        Yangi qator `id` si, yoki `None` — allaqachon yozilgan (job qayta
        yugurdi). ⛔ Bu ham XATO EMAS.
    """
    needs_evidence = kind is not AnomalyKind.NO_COVERAGE_STALL
    if needs_evidence and (occupancy_event_id is None or snapshot_id is None):
        raise ValueError(
            f"write_anomaly(): {kind.value!r} DALIL bilan yoziladi (D-29) — "
            f"occupancy_event_id={occupancy_event_id!r}, snapshot_id={snapshot_id!r}. "
            "Dalilsiz «band, lekin to'lovsiz» da'vosi rasm-dalilsiz qolardi."
        )
    if not needs_evidence and (occupancy_event_id is not None or snapshot_id is not None):
        raise ValueError(
            f"write_anomaly(): {kind.value!r} da dalil BO'LMAYDI (C-12) — "
            f"occupancy_event_id={occupancy_event_id!r}, snapshot_id={snapshot_id!r}. "
            "«Ko'ra olmadik» da'vosi ko'rilgan kadr bilan kelsa u YOLG'ON bo'lardi."
        )

    stmt = (
        pg_insert(BillingAnomaly)
        .values(
            market_id=market_id,
            stall_id=stall_id,
            service_date=service_date,
            kind=kind.value,
            occupancy_event_id=occupancy_event_id,
            snapshot_id=snapshot_id,
        )
        .on_conflict_do_nothing(index_elements=["market_id", "stall_id", "service_date", "kind"])
        .returning(BillingAnomaly.id)
    )
    anomaly_id: UUID | None = (await session.execute(stmt)).scalar_one_or_none()
    return anomaly_id
