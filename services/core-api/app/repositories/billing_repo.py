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
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final
from uuid import UUID

from sbozor_core.billing import (
    ChargeCreditAllocation,
    ChargeDue,
    allocate_charge_credit,
    billable_from_slots,
    total_due_soum,
)
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    AnomalyKind,
    OccupancyVerdict,
    PaymentKind,
    ResolutionSource,
)
from sbozor_core.models import BillingAnomaly, ChargeAdjustment, ChargeEvidence, DailyCharge
from sbozor_core.models.billing import LATE_REVIEW_ADJUSTMENT_PREDICATE
from sbozor_core.money import assert_safe_soum
from sqlalchemy import Date, Integer, Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.repositories.stall_repo import like_term
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
    "AnomalyCounts",
    "AnomalyRow",
    "ChargeAdjustmentItem",
    "ChargeDetail",
    "ChargeEvidenceItem",
    "ChargeRow",
    "ExistingCharge",
    "PendingMarket",
    "PendingProjection",
    "PendingStall",
    "SlotEvidenceRow",
    "StallDayMoney",
    "StallSlotVerdict",
    "anomaly_list",
    "billable_stalls",
    "charge_detail",
    "charge_list",
    "event_snapshots",
    "market_day_charges",
    "pending_projection",
    "resolve_stall_day_money",
    "vendor_charge_allocation",
    "vendor_outstanding",
    "write_anomaly",
    "write_charge",
    "write_evidence",
    "write_late_review_adjustment",
]

_UUID = PgUuid(as_uuid=True)
_UUID_ARRAY = ARRAY(PgUuid(as_uuid=True))

_OCCUPIED: Final[str] = OccupancyVerdict.OCCUPIED.value
_HUMAN: Final[str] = ResolutionSource.HUMAN.value
"""Qiymatlar so'rov PARAMETRI, so'rov MATNIDAGI literal emas.

`occupancy_repo.py:94-101` da o'rnatilgan qoida: literal yozilganda enum
o'zgargan kuni filtr jimgina hech nimaga tushmasdi — so'rov ishlayverardi,
faqat natija bo'sh bo'lardi.
"""


# ===========================================================================
# BELGILI PUL IFODALARI — HAR BIRI AYNAN BIR MARTA YOZILGAN (C-5, G-14)
# ===========================================================================

_SIGNED_PAYMENT_EXPR: Final[str] = (
    "CASE WHEN p.kind = :reversal THEN -p.amount_soum ELSE p.amount_soum END"
)
"""To'lovning BELGILI qiymati — ustun har doim MUSBAT, belgi KO'RINISHDA (C-5).

=============================================================================
⛔⛔ BU KONSTANTA IKKI FUNKSIYA TOMONIDAN ISHLATILADI VA IKKINCHI NUSXA
   YOZILMAYDI: `vendor_outstanding()` (hisoblanadigan qoldiq, BILL-03) va
   `vendor_charge_allocation()` (hosila FIFO ko'rinish, D-24).

G-14 ning butun da'vosi shu satrga tayanadi: ikki hosila ko'rinish AYNAN
bir xil kredit sonidan chiqadi, ya'ni ular **ajralib keta olmaydi**. Ikki
nusxa yozilganda ekrandagi qarz bilan hisobotdagi qarz bir kun farq
qilardi va **ikkalasi ham «to'g'ri»** bo'lardi — bu loyihada takroran
topilgan «ikki haqiqat manbai» sinfi.

⚠ `payments.amount_soum` da `CHECK (> 0)` bor (C-5), ya'ni storno manfiy
  summa bilan EMAS, `kind = 'reversal'` bilan yoziladi va belgi faqat shu
  ifodada tug'iladi.
"""

_SIGNED_ADJUSTMENT_EXPR: Final[str] = (
    "CASE WHEN a.direction = :increase THEN a.amount_soum ELSE -a.amount_soum END"
)
"""Tuzatishning BELGILI qiymati — `_SIGNED_PAYMENT_EXPR` bilan bir xil qaror.

`charge_adjustments.amount_soum` ham har doim musbat; kamaytirish
`direction = 'decrease'` bilan ifodalanadi. Ustun nomi ATAYIN `amount_soum`
(`delta_soum` EMAS): `test_meta.py` ning moliyaviy darvozasi AYNAN shu
nomni izlaydi (C-5).
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


async def event_snapshots(
    session: AsyncSession, *, market_id: UUID, event_ids: Sequence[UUID]
) -> dict[UUID, UUID]:
    """`occupancy_event_id -> snapshot_id` — dalil nusxasining YAGONA manbai.

    ⛔ IKKI CHAQIRUVCHI, BITTA SO'ROV: `write_evidence()` (hisobning
       rasm-dalili) va `billing_close` (anomaliyaning dalili — D-29 hisob
       YOZILMAGANDA ham kadr talab qiladi). Ikkinchi nusxa yozilganda
       ular bir kun ajralib ketardi va anomaliya boshqa kadrga ishora
       qilardi — nizoda ikkala rasm ham «to'g'ri» bo'lardi.

    Returns:
        Faqat TOPILGAN juftliklar. Yo'q hodisa lug'atga KIRMAYDI va bu
        HALOL javob: chaqiruvchi `None` bilan anomaliya yozishga urinsa
        `write_anomaly()` uni `ValueError` bilan rad etadi (D-29).
    """
    if not event_ids:
        return {}
    result = await session.execute(
        _EVIDENCE_SNAPSHOTS, {"market_id": market_id, "event_ids": list(event_ids)}
    )
    return {row["occupancy_event_id"]: row["snapshot_id"] for row in result.mappings()}


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

    snapshot_by_event = await event_snapshots(
        session,
        market_id=market_id,
        event_ids=[
            event_id for row in winners if (event_id := row.winning_occupancy_event_id) is not None
        ],
    )

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


_MARKET_DAY_CHARGES = text(
    """
    SELECT c.stall_id    AS stall_id,
           c.id          AS charge_id,
           c.amount_soum AS amount_soum
      FROM daily_charges c
     WHERE c.market_id = :market_id
       AND c.service_date = :service_date
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("service_date", type_=Date()),
)
"""Shu kunga ALLAQACHON yozilgan hisoblar — rasta kesimida.

⛔ NEGA KERAK: `write_charge()` konfliktda `None` qaytaradi (Pitfall 3),
   ya'ni «bor» degan javobdan hisobning `id` si ham, summasi ham CHIQMAYDI.
   Kech kelgan tasdiq shoxi (Pitfall 5c) esa AYNAN shu ikkalasini talab
   qiladi: tuzatish qatori mavjud hisobga osiladi va uning TO'LIQ
   summasini kamaytiradi.

⚠ `service_date` bo'yicha, `business_date` bo'yicha EMAS — ikki ustunning
  ikki ma'nosi `_BILLABLE_SLOT_ROWS` docstringida (Pitfall 1). Job D + 1
  da yuguradi, ya'ni `business_date` bo'yicha qidiruv NORMAL kunda 0 qator
  berardi va kech tasdiq shoxi HECH QACHON ishlamasdi.
"""


@dataclass(frozen=True, slots=True)
class ExistingCharge:
    """Yozilgan hisobning tuzatish uchun YETARLI minimumi.

    ⚠ `service_date` YO'Q va bu ataylab: qator `market_day_charges()` ning
      AYNAN bitta kuni uchun olinadi, ya'ni kunni qatorga takrorlash
      «qaysi kun?» savoliga ikkinchi javob manbai bo'lardi.
    """

    charge_id: UUID
    amount_soum: int


async def market_day_charges(
    session: AsyncSession, *, market_id: UUID, service_date: date
) -> dict[UUID, ExistingCharge]:
    """Shu kunning yozilgan hisoblari — `{stall_id: ExistingCharge}`.

    Bo'sh lug'at — NATIJA («bu kunga hali hisob yozilmagan»), uning
    yo'qligi emas.
    """
    result = await session.execute(
        _MARKET_DAY_CHARGES, {"market_id": market_id, "service_date": service_date}
    )
    return {
        row["stall_id"]: ExistingCharge(
            charge_id=row["charge_id"], amount_soum=int(row["amount_soum"])
        )
        for row in result.mappings()
    }


async def write_late_review_adjustment(
    session: AsyncSession, *, market_id: UUID, charge: ExistingCharge
) -> UUID | None:
    """KECH KELGAN TASDIQ — hisob BEKOR QILINMAYDI, KAMAYTIRILADI (Pitfall 5c).

    =======================================================================
    ⛔⛔ D-07 NING AMALDAGI SHAKLI VA BILL-02 NING YAGONA PRODUCER'I.

    Nazoratchi D + 1 kunduzida «bo'sh» degach `day_close` qayta yuguradi va
    o'sha kunning materializatsiyasi o'zgaradi. Yozilgan hisob esa
    O'ZGARMAS (`daily_charges` da `UPDATE`/`DELETE` triggeri bor, 0020) —
    va bu TO'G'RI: sotuvchi ko'rgan summa kechasi jimgina o'zgarmasligi
    kerak. Tuzatish ALOHIDA QATOR bo'lib tug'iladi va nizoda IKKALA yozuv
    ham ko'rinadi.

    ⛔ `actor_user_id` YOZILMAYDI (`NULL` = tizim, `0022`). Odam
       ko'rsatilgan qator «kim qaror qildi?» savoliga YOLG'ON javob
       bo'lardi — model qaror qildi, odam esa faqat bandlikni tuzatdi.

    ⛔ `write_app_audit()` CHAQIRILMAYDI: `charge_adjustments`
       `BILLING_AUDITED_TABLES` da, ya'ni audit qatorini DB-TRIGGER
       (`fn_audit_row()`) yozadi va ilova qatlamidagi ikkinchi yozuv
       DUBLIKAT bo'lardi (`enums.py::AuditAction` ning `charge_adjust`
       a'zosi aynan shu sababdan YO'Q).

    ⛔ IDEMPOTENTLIK STRUKTURAVIY: `LATE_REVIEW_ADJUSTMENT_INDEX` qisman
       UNIQUE indeksi `(market_id, charge_id) WHERE reason_code =
       'late_review'` ni qamraydi. Job KONVERGENT, ya'ni bir kunni
       qayta-qayta yugurish NORMAL — ilova qatlamidagi «avval tekshir,
       keyin yoz» ikkita parallel yugurishda IKKI marta to'liq summani
       ayirardi va hisobning nettosi MANFIY bo'lib qolardi.
    =======================================================================

    Returns:
        Yangi tuzatish qatorining `id` si, yoki `None` — ⛔ XATO EMAS:
        «bu hisobga `late_review` tuzatishi ALLAQACHON yozilgan».
    """
    stmt = (
        pg_insert(ChargeAdjustment)
        .values(
            market_id=market_id,
            charge_id=charge.charge_id,
            direction=AdjustmentDirection.DECREASE.value,
            reason_code=AdjustmentReason.LATE_REVIEW.value,
            # ⛔ TO'LIQ SUMMA: kech tasdiq «bu rasta band EMAS edi» deydi,
            #   ya'ni hisobning bir qismi emas, HAMMASI o'rinsiz.
            amount_soum=assert_safe_soum(charge.amount_soum),
            actor_user_id=None,
        )
        .on_conflict_do_nothing(
            index_elements=["market_id", "charge_id"],
            index_where=text(LATE_REVIEW_ADJUSTMENT_PREDICATE),
        )
        .returning(ChargeAdjustment.id)
    )
    adjustment_id: UUID | None = (await session.execute(stmt)).scalar_one_or_none()
    return adjustment_id


# ===========================================================================
# 4. QOLDIQ — HISOBLANADIGAN, SAQLANMAYDIGAN (BILL-03, C-4, C-5)
# ===========================================================================

_VENDOR_OUTSTANDING = text(
    f"""
    WITH parts AS (
        SELECT c.vendor_id AS vendor_id,
               c.amount_soum AS signed_soum
          FROM daily_charges c
         WHERE c.market_id = :market_id
           AND (:as_of IS NULL OR c.service_date < :as_of)
           AND (:vendor_ids IS NULL OR c.vendor_id = ANY(:vendor_ids))
        UNION ALL
        SELECT c2.vendor_id,
               {_SIGNED_ADJUSTMENT_EXPR}
          FROM charge_adjustments a
          JOIN daily_charges c2
            ON c2.market_id = a.market_id
           AND c2.id = a.charge_id
         WHERE a.market_id = :market_id
           AND (:as_of IS NULL OR c2.service_date < :as_of)
           AND (:vendor_ids IS NULL OR c2.vendor_id = ANY(:vendor_ids))
        UNION ALL
        SELECT p.vendor_id,
               -({_SIGNED_PAYMENT_EXPR})
          FROM payments p
         WHERE p.market_id = :market_id
           AND (:vendor_ids IS NULL OR p.vendor_id = ANY(:vendor_ids))
    )
    SELECT vendor_id,
           sum(signed_soum)::bigint AS outstanding_soum
      FROM parts
     GROUP BY vendor_id
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("as_of", type_=Date()),
    bindparam("vendor_ids", type_=_UUID_ARRAY),
    bindparam("increase", type_=Text()),
    bindparam("reversal", type_=Text()),
)
"""BILL-03 — qoldiq SO'ROV, saqlangan ustun EMAS.

=============================================================================
⛔ `S608` SHU SO'ROVDA O'CHIRILGAN VA SABAB TOR (`occupancy_repo.py:414-418`
   bilan aynan bir xil): f-string ga tushadigan YAGONA qiymat — shu
   moduldagi SOBIT `_SIGNED_*_EXPR` konstantalari. Tashqi kirish f-string ga
   umuman kelmaydi; har qiymat `bindparam(...)` orqali TIPLANGAN parametr.

=============================================================================
⛔⛔ QOLDIQ NEGA SOTUVCHI KESIMIDA (C-4), RASTA KESIMIDA EMAS.

To'lov — SOTUVCHI darajasidagi kredit (`payments.charge_id` YO'Q) va bitta
to'lov BIR NECHA kunlik qarzni yopadi (UI-SPEC §9.6). Rasta kesimida
hisoblash bir sotuvchining ikki rastasi bo'lganda qarzni IKKIGA BO'LIB
yuborardi va u **hech qaysi rastada to'liq ko'rinmasdi** — kassir har
ekranda qarzning yarmini ko'rib «hammasi to'langan» degan xulosaga kelardi.

⚠ Buning ONGLI narxi: bir sotuvchining ikki rastasi bo'lsa kassir HAR
  IKKALASIDA ham O'SHA qoldiqni ko'radi. Bu TO'G'RI — qarz sotuvchining,
  rastaning emas (UI-SPEC §13.1 «Eski qarz» atamasi ham shunday o'qiladi).

=============================================================================
⛔ `as_of` FAQAT HISOBLARNI CHEKLAYDI (`service_date < :as_of`), to'lovlarni
   EMAS. Sabab: «ESKI qarz» aynan eski bo'lishi kerak — bugungi patta
   proyeksiyada ALOHIDA maydon (`amount_soum`) bo'lib chiqadi va uni
   qoldiqqa ham qo'shish `total_due_soum` ni IKKI MARTA sanardi. To'lovlar
   esa cheklanmaydi: bugun to'langan pul eski qarzni AYNAN bugun yopadi.

=============================================================================
⛔ MANFIY NATIJA (AVANS) RUXSAT ETILADI va kattalikka AYLANTIRILMAYDI
   (OQ-4/A4, UI-SPEC §9.6). Ortiqcha to'lovni bloklash kassirni pulni
   UMUMAN YOZMASLIKKA majburlardi — ya'ni himoya o'zi himoya qilayotgan
   yozuvni yo'q qilardi.
"""


async def vendor_outstanding(
    session: AsyncSession,
    *,
    market_id: UUID,
    vendor_ids: Sequence[UUID] | None = None,
    as_of: date | None = None,
) -> dict[UUID, int]:
    """Sotuvchi kesimidagi HISOBLANADIGAN qoldiq (BILL-03).

    `hisoblar + belgili tuzatishlar − belgili to'lovlar`, sotuvchi
    kesimida. ⛔ SAQLANGAN BALANS USTUNI HECH QAYERDA YO'Q va u
    qo'shilmaydi: drift nizoga aylanadi va aynan shu nizo SBOZOR mavjud
    bo'lish sababidir (D-02).

    Args:
        vendor_ids: filtr; `None` — bozorning HAMMA sotuvchisi.
        as_of: berilsa hisoblar `service_date < as_of` bilan cheklanadi.

    Returns:
        `{vendor_id: outstanding_soum}`. ⚠ Qatori umuman yo'q sotuvchi
        lug'atga KIRMAYDI — chaqiruvchi `.get(vendor_id, 0)` bilan oladi
        va bu «0» ni «ma'lumot yo'q» dan ajratmaydigan yolg'on aniqlikdan
        saqlaydi.
    """
    result = await session.execute(
        _VENDOR_OUTSTANDING,
        {
            "market_id": market_id,
            "as_of": as_of,
            "vendor_ids": None if vendor_ids is None else list(vendor_ids),
            "increase": AdjustmentDirection.INCREASE.value,
            "reversal": PaymentKind.REVERSAL.value,
        },
    )
    return {row["vendor_id"]: int(row["outstanding_soum"]) for row in result.mappings()}


# ===========================================================================
# 5. D-24 — «QAYSI KUNNING PATTASI TO'LANDI?» (HOSILA KO'RINISH)
# ===========================================================================

_VENDOR_CHARGE_DUES = text(
    f"""
    SELECT c.service_date AS service_date,
           s.code         AS stall_code,
           (c.amount_soum + COALESCE(adj.total, 0))::bigint AS due_soum
      FROM daily_charges c
      JOIN stalls s
        ON s.market_id = c.market_id
       AND s.id = c.stall_id
      LEFT JOIN LATERAL (
        SELECT sum({_SIGNED_ADJUSTMENT_EXPR}) AS total
        FROM charge_adjustments a
        WHERE a.market_id = c.market_id
          AND a.charge_id = c.id
      ) adj ON true
     WHERE c.market_id = :market_id
       AND c.vendor_id = :vendor_id
       AND (:as_of IS NULL OR c.service_date < :as_of)
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("vendor_id", type_=_UUID),
    bindparam("as_of", type_=Date()),
    bindparam("increase", type_=Text()),
)
"""Sotuvchining hisoblari, tuzatishlar bilan NETLANGAN holda.

⛔ TARTIB SO'ROVDA E'LON QILINMAYDI va bu ATAYIN: taqsimlash tartibi
   (`FIFO_OLDEST_SERVICE_DATE_FIRST`) `sbozor_core.billing` ning
   `sorted()` ida yashaydi. SQL da `ORDER BY` yozish qoidani IKKI JOYGA
   bo'lardi va `tests/unit/test_payment_credit_rules.py` ning jadvali
   mahsulot yo'lini o'lchamay qo'yardi.

⚠ `stall_code` `stalls` dan JOIN bilan olinadi, chunki 06-01 ning
  kontraktida tenglik uzgichi AYNAN KOD (`stall_id` EMAS): UUID tartibni
  tasodifiy qilardi va nizoda «qaysi rasta?» savoliga odam o'qiydigan
  javob bo'lmasdi.
"""

_VENDOR_CREDIT = text(
    f"""
    SELECT COALESCE(sum({_SIGNED_PAYMENT_EXPR}), 0)::bigint AS credit_soum
      FROM payments p
     WHERE p.market_id = :market_id
       AND p.vendor_id = :vendor_id
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("vendor_id", type_=_UUID),
    bindparam("reversal", type_=Text()),
)
"""Sotuvchining BELGILI to'lov yig'indisi — ⛔ `vendor_outstanding()` BILAN
AYNI IFODADAN (`_SIGNED_PAYMENT_EXPR`). G-14 shu tenglikni o'lchaydi.

⚠ `COALESCE(..., 0)` — to'lovsiz sotuvchi ham qator beradi: «0» natija,
  uning yo'qligi emas.
"""


async def vendor_charge_allocation(
    session: AsyncSession,
    *,
    market_id: UUID,
    vendor_id: UUID,
    as_of: date | None = None,
) -> ChargeCreditAllocation:
    """⛔ D-24 NING JAVOBI — HOSILA KO'RINISH, hech nima saqlanmaydi.

    =======================================================================
    ⛔⛔ NIMA UCHUN BU FUNKSIYA UMUMAN BOR.

    `payments.charge_id` YO'Q (C-4) va u bo'lishi ham mumkin emas: kassir
    bugungi pattani KUN DAVOMIDA yig'adi, hisob esa ertasi kuni 04:10 da
    tug'iladi (C-3). `service_date` yolg'iz ham yetarli emas —
    `[Qarzni ham olish]` (UI-SPEC §9.6) da bitta to'lov bugungi tarif VA
    eski qarzni yopadi, `service_date` esa BUGUN bo'lib qoladi.

    Ya'ni «qaysi kunning pattasi to'landi?» savolining javobi USTUNDA emas,
    NOMLANGAN QOIDADA yashaydi: `FIFO_OLDEST_SERVICE_DATE_FIRST`. Bu
    funksiya o'sha qoidani HAQIQIY qatorlar ustida qo'llaydi.

    =======================================================================
    ⛔⛔ TAQIQ — KEYINGI IJROCHI UCHUN, CHUNKI VASVASA AYNAN UNDA TUG'ILADI:

      * natijani jadvalga YOZISH taqiqlanadi (ettinchi jadval qo'shilmaydi);
      * `payments` ga `allocated_*` ustuni QO'SHILMAYDI;
      * natijani KESHLASH taqiqlanadi.

    Uchalasi ham D-07/BILL-03 ning «saqlangan balans YO'Q» shartini
    buzardi va ikkinchi haqiqat manbai tug'dirardi.

    =======================================================================
    ⚠ 6-FAZADA BU FUNKSIYANING HTTP ISTE'MOLCHISI YO'Q va bu KUTILGAN:
      sotuvchi kesimidagi to'lov tarixi 8-fazaniki (UI-SPEC §16.1). Qoida
      BUGUN tasdiq bilan qulflanadi, yuza keyin qo'shiladi — ⛔ shuning
      uchun bu «o'lik kod» EMAS va o'chirilmaydi (06-02 ning `AuditAction`
      bandi bilan aynan bir xil naqsh).

    =======================================================================
    ⛔ QAROR SQL DA EMAS: `allocate_charge_credit()` (06-01) CHAQIRILADI.
       `billable_stalls()` bilan aynan bir xil majburiyat.

    Args:
        as_of: berilsa hisoblar `service_date < as_of` bilan cheklanadi —
            ⛔ `vendor_outstanding()` BILAN BIR XIL CHEGARA, aks holda ikki
            ko'rinish bir xil kunni boshqacha sanardi va G-14 ning tengligi
            buzilardi.
    """
    dues = await session.execute(
        _VENDOR_CHARGE_DUES,
        {
            "market_id": market_id,
            "vendor_id": vendor_id,
            "as_of": as_of,
            "increase": AdjustmentDirection.INCREASE.value,
        },
    )
    charges = [
        ChargeDue(
            service_date=row["service_date"],
            stall_code=str(row["stall_code"]),
            due_soum=int(row["due_soum"]),
        )
        for row in dues.mappings()
    ]

    credit = await session.execute(
        _VENDOR_CREDIT,
        {
            "market_id": market_id,
            "vendor_id": vendor_id,
            "reversal": PaymentKind.REVERSAL.value,
        },
    )
    credit_soum = int(credit.scalar_one())

    return allocate_charge_credit(charges, credit_soum)


# ===========================================================================
# 6. KUTILAYOTGAN PATTA — PROYEKSIYA (BILL-05, D-16, D-17)
# ===========================================================================

_STALL_CODE_MATCHES = text(
    """
    SELECT s.code AS stall_code
      FROM stalls s
     WHERE s.market_id = :market_id
       AND s.code LIKE :prefix
     ORDER BY s.code_sort, s.id
     LIMIT :limit
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("prefix", type_=Text()),
    bindparam("limit", type_=Integer()),
)
"""Kassir tergan kodning MOSLIKLARI — 02-UI-SPEC §6.9 ning server yarmi.

⚠ `LIKE` naqshi `stall_repo.like_term()` bilan QOCHIRILADI, qo'lda emas:
  `%` bilan kelgan so'rov butun reyestrni qaytarardi va `_` har bir bir
  belgili kodga mos kelardi (`stall_repo.py:560-579`).
"""

MATCH_LIMIT: Final[int] = 20
"""Ro'yxat uzunligining chegarasi — kassir ekrani uchun (UI-SPEC §8.3).

Chegaradan oshgan natija ham «ko'p moslik» bo'lib qoladi, ya'ni oqim
o'zgarmaydi: kassir aniqroq kod teradi.
"""


@dataclass(frozen=True, slots=True)
class PendingStall:
    """⛔ UI-SPEC §9.2 NING AYNAN YETTI MAYDONI — na kam, na ko'p.

    =======================================================================
    ⛔ YO'Q VA YO'QLIGI O'LCHANADIGAN MAYDONLAR (G-22/G-23):

        charge_id      — D-17: proyeksiya HISOB EMAS, ya'ni hisob
                         identifikatori MAVJUD EMAS (yashirilgan emas);
        tariff_id      — D-20 ning KUCHLI shakli: klientda tarif kirish
                         ma'lumoti YO'Q, ya'ni summani hisoblash
                         taqiqlanmaydi — IMKONSIZ;
        vendor_id      — C-10: kassir yuzasida shaxsiy ma'lumot yo'q;
        occupied_slots — §9.1: «bugun band» BILINMAYDI (C-3);
        balance_soum   — BILL-03: saqlangan balans yo'q, NOMI ham yo'q.

    ⚠ To'plam tengligi bilan o'lchanadi (`dataclasses.fields()`), inkor
      tasdiq bilan EMAS (D-31): `not.toContain("charge_id")` faqat AYNAN
      o'sha nomni ushlardi va `chargeId` jimgina o'tib ketardi.
    """

    stall_code: str
    service_date: date
    market_open: bool
    amount_soum: int | None
    amount_unavailable_reason: str | None
    outstanding_soum: int
    total_due_soum: int


@dataclass(frozen=True, slots=True)
class PendingMarket:
    """Bozor kesimi (direktor, UI-SPEC §9.5) — ⛔ NOL HAM NATIJA.

    Uchala son NOL bo'lganda ham qaytariladi: «hisobot yo'q» bilan
    «hammasi nol» ni ajratmaydigan javob direktorni ma'lumot yo'qolgan deb
    o'ylashga majburlardi (`occupancy.py:122-124` da o'rnatilgan qoida).

    `fetched_at` — UI-SPEC §9.5 ning «oxirgi olingan vaqt» i. Avtomatik
    taymer YO'Q: direktor raqamni o'qib turganda uni jimgina o'zgartirib
    qo'yadigan yangilanish «men boshqa raqam ko'rgandim» degan nizoning
    manbai.

    ⚠ `market_open` — `StallDayMoney` dagi bilan AYNAN bir xil sabab
      (06-06 deviatsiya #1): UI-SPEC §9.5/§9.2 uni MUSTAQIL maydon
      sifatida talab qiladi va uni rastalar ro'yxatidan hosila qilish
      RASTASIZ bozorda (yoki tarifsiz kunda) javobsiz qolardi. Shuning
      uchun u AYNI `as_of` bilan alohida so'raladi — `now()` bilan emas,
      ya'ni yarim tunda ikki maydon ikki xil kunni ko'rsata olmaydi.
    """

    market_open: bool
    pending_amount_soum: int
    outstanding_soum: int
    pending_stall_count: int
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class PendingProjection:
    """Proyeksiyaning UCH SHAKLI — har biri ALOHIDA maydon bilan.

    `stall`   — aynan bitta moslik (to'liq proyeksiya);
    `matches` — ko'p moslik (faqat KODLAR, `code_sort` tartibida);
    `market`  — bozor kesimi (`stall_code` berilmaganda).

    ⚠ Uch shaklni bitta «bo'sh qiymatlar» to'plamiga siqish «summa
      hisoblanmadi» bilan «summa nol» ni ajratmaydigan javob berardi — bu
      esa aynan §9.4 ning oldini olayotgan xatosi.
    """

    stall: PendingStall | None
    matches: tuple[str, ...]
    market: PendingMarket | None


async def pending_projection(
    session: AsyncSession,
    *,
    market_id: UUID,
    as_of: date,
    stall_code: str | None = None,
) -> PendingProjection:
    """BILL-05 — kutilayotgan patta = ⛔ bugungi tarif + eski qarz.

    =======================================================================
    ⛔ SUMMA `resolve_stall_day_money(as_of=as_of)` DAN KELADI (D-16), ya'ni
       kassir ko'rgan son bilan kechqurun yozilgan son AYNAN BIR
       FUNKSIYADAN chiqadi. Farq testda `==` bilan o'lchanadi.

    ⛔ `total_due_soum` SERVERDA hisoblanadi va ⛔ ARIFMETIKA BU FAYLDA
       YOZILMAYDI: `sbozor_core.billing.total_due_soum()` (06-01)
       chaqiriladi. Aynan shu qo'shish amali `POST /payments` da (06-09,
       kvota to'plami) ham kerak bo'ladi va ikki joyda yozilsa ular BIR KUN
       ajralib ketardi — §9.6 ning «klientda arifmetika yo'q» qarori
       serverda IKKI HAQIQAT MANBAI bilan almashardi, ya'ni xato
       klientdan serverga KO'CHARDI, yo'qolmasdi.

    =======================================================================
    ⛔ KO'P MOSLIK — VA ANIQ MOSLIKNING USTUNLIGI (02-UI-SPEC §6.9).

    Kod PREFIKS sifatida qidiriladi. Bir nechta rasta mos kelsa summa
    HISOBLANMAYDI va faqat kodlar ro'yxati qaytadi; kassir aniq kodni
    tanlagach IKKINCHI chaqiruv bo'ladi.

    ⚠ IKKINCHI CHAQIRUV TUGASHI UCHUN ANIQ MOSLIK USTUN: `"1"` va `"12"`
      kodlari bor bozorda prefiks semantikasi `"1"` uchun HAR DOIM ikki
      natija berardi va kassir ro'yxatdan `"1"` ni tanlaganda o'sha ro'yxat
      QAYTA chiqardi — oqim hech qachon `ready` holatiga yetmasdi. Shuning
      uchun tergan kod moslashlar orasida AYNAN bo'lsa, u yagona natija
      sifatida qabul qilinadi.
    """
    if stall_code is None:
        return PendingProjection(
            stall=None, matches=(), market=await _market_projection(session, market_id, as_of)
        )

    matched = await session.execute(
        _STALL_CODE_MATCHES,
        {
            "market_id": market_id,
            "prefix": f"{like_term(stall_code)}%",
            "limit": MATCH_LIMIT,
        },
    )
    codes = tuple(str(row["stall_code"]) for row in matched.mappings())

    if stall_code in codes:
        exact: str | None = stall_code
    elif len(codes) == 1:
        exact = codes[0]
    else:
        # Nol moslik ham, ko'p moslik ham SUMMASIZ qaytadi — «yo'q summa
        # yo'q summa» (UI-SPEC §9.4), taxminiy summa KO'RSATILMAYDI.
        return PendingProjection(stall=None, matches=codes, market=None)

    money = await resolve_stall_day_money(
        session, market_id=market_id, as_of=as_of, stall_code=exact
    )
    if not money:
        return PendingProjection(stall=None, matches=(), market=None)

    row = money[0]
    outstanding = 0
    if row.vendor_id is not None:
        balances = await vendor_outstanding(
            session, market_id=market_id, vendor_ids=[row.vendor_id], as_of=as_of
        )
        outstanding = balances.get(row.vendor_id, 0)

    return PendingProjection(
        stall=PendingStall(
            stall_code=row.stall_code,
            service_date=as_of,
            market_open=row.market_open,
            amount_soum=row.amount_soum,
            amount_unavailable_reason=row.unavailable_reason,
            outstanding_soum=outstanding,
            total_due_soum=total_due_soum(row.amount_soum, outstanding),
        ),
        matches=(),
        market=None,
    )


async def _market_projection(session: AsyncSession, market_id: UUID, as_of: date) -> PendingMarket:
    """Bozor kesimi — `resolve_stall_day_money()` ning AYNI natijasidan.

    ⚠ RASTA HOLATI (`status`) BO'YICHA FILTR ATAYIN YO'Q: `maintenance`
      deb belgilangan rasta savdo qilsa ham patta to'laydi va «qaysi rasta
      hisob oladi?» savoliga BANDLIK darvozasi javob beradi (D-04), holat
      ustuni emas. Bu yerdagi sanoq esa «bugun qancha patta KUTILYAPTI»
      degan boshqa savol.
    """
    rows = await resolve_stall_day_money(session, market_id=market_id, as_of=as_of)
    priced = [row.amount_soum for row in rows if row.amount_soum is not None]
    balances = await vendor_outstanding(session, market_id=market_id, as_of=as_of)
    market_open = await session.execute(_MARKET_OPEN, {"market_id": market_id, "as_of": as_of})
    return PendingMarket(
        market_open=bool(market_open.scalar_one()),
        pending_amount_soum=sum(priced),
        # ⛔⛔ HAR SOTUVCHI ALOHIDA QIRQILADI, KEYIN QO'SHILADI (WR-02).
        #
        # `vendor_outstanding()` BELGILI balans qaytaradi va manfiy qiymat
        # ATAYIN ruxsat etilgan (avans, OQ-4/A4). Xom `sum()` esa bir
        # sotuvchining avansini boshqasining qarzi bilan NETLARDI:
        #
        #     A 500 000 qarzdor, B 500 000 avans -> outstanding_soum = 0
        #
        # Ya'ni direktorning §9.5 panelida qarz JIMGINA kamayib
        # ko'rinardi — bozor bo'yicha avanslar yig'indisi qadar. Bu
        # mahsulot AYNAN fosh qilish uchun mavjud bo'lgan raqam.
        #
        # ⛔ NOM O'ZGARMADI VA BU ATAYIN: ekranda ustun `collect.oldDebt`
        #    («Eski qarz») bilan chiziladi (`pending-summary.tsx`), ya'ni
        #    maydon ALLAQACHON qarz deb o'qiladi. Uni `net_balance_soum`
        #    ga qayta nomlash javob kalitlari to'plamini, klient
        #    sxemasini va uchala locale matnini birdan siljitardi —
        #    darvozalar esa to'plam TENGLIGI bilan qulflangan.
        #
        # ⚠ AVANS YO'QOLMAYDI: u sotuvchi kesimida hamon BELGILI
        #   (`PendingStall.outstanding_soum` manfiy bo'lishi mumkin) va
        #   §9.6 ning kvota to'plami o'sha belgili qiymatdan tug'iladi.
        #   Qirqish FAQAT bozor yig'indisida va u «qancha qarz bor?»
        #   degan boshqa savolga javob beradi.
        outstanding_soum=sum(balance for balance in balances.values() if balance > 0),
        pending_stall_count=len(priced),
        fetched_at=datetime.now(tz=UTC),
    )


_MARKET_OPEN = text(
    """
    SELECT market_is_open(:market_id, :as_of) AS market_open
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("as_of", type_=Date()),
)
"""Kalendar javobi — ⛔ ILOVA QATLAMIDA QAYTA HISOBLANMAYDI (D-10, T-06-34).

`open_weekdays` va `market_calendar_exceptions` mantig'i 2-fazadagi DB
funksiyasida yashaydi va bu modul uni HECH QAYERDA takrorlamaydi
(`grep open_weekdays` -> 0). Ikkinchi nusxa bir kun ajralib ketardi va
o'shanda kassir ekrani «bozor ochiq», hisobot esa «yopiq kun» degan
bo'lardi.

⚠ INVOKER va fail-closed: tenant konteksti o'rnatilmagan sessiyada RLS 0
  qator ko'rsatadi va funksiya HAR KUNNI YOPIQ deb qaytaradi (modul
  docstringidagi Pitfall 9).
"""


# ===========================================================================
# 7. DIREKTOR YUZASINING O'QISH SO'ROVLARI (BILL-02, BILL-03, BILL-04)
#
# ⛔⛔ MARSHRUT PUL MANTIG'I YOZMAYDI — U SHU YERGA KELADI (D-16 ning
#    marshrut qatlamidagi shakli).
#
# `api/v1/billing.py` ning uchala direktor marshruti ham FAQAT quyidagi
# uch funksiyani chaqiradi. Sabab 06-06 modul docstringi bilan bir xil:
# arifmetika ikki joyda (SQL va handler) yashasa ular BIR KUN ajralib
# ketardi va o'shanda ekrandagi son bilan hisobotdagi son farq qilardi —
# IKKALASI HAM «to'g'ri» bo'lgan holda.
#
# ⛔ NETLANGAN SUMMA BITTA IFODADAN (`_SIGNED_ADJUSTMENT_EXPR`): ro'yxat
#    ham, tafsilot ham, qoldiq ham AYNI konstantani ishlatadi. Bu C-5/G-14
#    ning aynan o'sha mexanizmi — ikki hosila ko'rinish ajralib keta
#    OLMAYDI, chunki manba satr BITTA.
# ===========================================================================

_CHARGE_ADJUSTMENT_TOTAL = f"""
        SELECT sum({_SIGNED_ADJUSTMENT_EXPR}) AS total
          FROM charge_adjustments a
         WHERE a.market_id = c.market_id
           AND a.charge_id = c.id
"""  # noqa: S608
"""Bitta hisobning BELGILI tuzatish yig'indisi — LATERAL ichida ishlatiladi.

⚠ FRAGMENT KONSTANTA, chunki uni ikki so'rov (`_CHARGE_ROWS` va
  `_CHARGE_DETAIL`) ishlatadi. Nusxa ko'chirilganda ro'yxatdagi summa
  bilan tafsilotdagi summa bir kun farq qilardi va direktor dialogni
  ochib «jadvalda boshqa son turgan edi» degan xulosaga kelardi.
"""

_CHARGE_ROWS = text(
    f"""
    SELECT c.id                 AS charge_id,
           s.code               AS stall_code,
           c.vendor_id          AS vendor_id,
           c.service_date       AS service_date,
           c.tariff_amount_soum AS tariff_amount_soum,
           (c.amount_soum + COALESCE(adj.total, 0))::bigint AS amount_soum
      FROM daily_charges c
      JOIN stalls s
        ON s.market_id = c.market_id
       AND s.id = c.stall_id
      LEFT JOIN LATERAL ({_CHARGE_ADJUSTMENT_TOTAL}) adj ON true
     WHERE c.market_id = :market_id
       AND c.service_date = :day
     ORDER BY s.code_sort, s.id
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("day", type_=Date()),
    bindparam("increase", type_=Text()),
)
"""Kun kesimidagi yozilgan hisoblar (UI-SPEC §11.2).

⛔ `S608` TOR SABAB BILAN: f-string ga tushadigan YAGONA qiymat — shu
   moduldagi SOBIT fragment konstantalari. Tashqi kirish `bindparam`
   orqali TIPLANGAN parametr bo'lib keladi.

⛔ FILTR `service_date` USTIDA, `business_date` USTIDA EMAS (C-2/D-06):
   direktor «qaysi KUN uchun patta yozildi?» deb so'raydi, «qaysi kuni
   yozildi?» deb emas. Ikkalasi D+1 04:10 da BIR KUN farq qiladi va
   `business_date` bo'yicha filtr sahifani HAR DOIM bir kun oldingi
   ma'lumot bilan ko'rsatardi.

⚠ TARTIB `code_sort` bo'yicha — SERVERDA. `ORDER BY s.code` «1, 10, 100,
  11, 2» berardi (`models/market.py:154-183`).
"""

_CHARGE_DETAIL = text(
    f"""
    SELECT c.id                 AS charge_id,
           c.service_date       AS service_date,
           s.code               AS stall_code,
           c.tariff_amount_soum AS tariff_amount_soum,
           (c.amount_soum + COALESCE(adj.total, 0))::bigint AS amount_soum
      FROM daily_charges c
      JOIN stalls s
        ON s.market_id = c.market_id
       AND s.id = c.stall_id
      LEFT JOIN LATERAL ({_CHARGE_ADJUSTMENT_TOTAL}) adj ON true
     WHERE c.market_id = :market_id
       AND c.id = :charge_id
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("charge_id", type_=_UUID),
    bindparam("increase", type_=Text()),
)
"""DL-3 ning 1 va 2-bo'limi (UI-SPEC §11.3).

⛔ `tariff_id` SELECT DA UMUMAN YO'Q — javob modeli uni e'lon qilmaydi va
   so'rov ham uni olib kelmaydi. Ustunni «baribir kerak bo'lar» deb
   qoldirish keyingi ijrochiga uni javobga qo'shishni BIR SATRLIK
   o'zgartirish qilib qo'yardi.

⚠ BEGONA BOZORNING `charge_id` SI 0 QATOR BERADI — RLS tufayli, `WHERE`
  sharti tufayli emas. Ikkalasi ham 404 beradi va javob BAYT-BAYT bir xil
  bo'ladi (`test_cross_tenant_is_indistinguishable_from_unknown_id`).
"""

_CHARGE_ADJUSTMENTS = text(
    """
    SELECT a.id            AS adjustment_id,
           a.direction     AS direction,
           a.amount_soum   AS amount_soum,
           a.reason_code   AS reason_code,
           a.actor_user_id AS actor_user_id,
           a.created_at    AS created_at
      FROM charge_adjustments a
     WHERE a.market_id = :market_id
       AND a.charge_id = :charge_id
     ORDER BY a.created_at, a.id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("charge_id", type_=_UUID),
)
"""DL-3 ning 4-bo'limi — tuzatishlar, YOZILISH tartibida.

⛔ `actor_user_id` QAYTADI, ISM EMAS (C-10 + §5.5): ism `GET /users` dan
   klientda joinlanadi va o'sha marshrut `audit_read` YOZADI. Ismni bu
   yerga qo'shish moliyaviy so'rovni shaxsiy-ma'lumot so'roviga
   aylantirardi.

⚠ TENGLIK UZGICHI `a.id`: bir hisobga bir tranzaksiyada ikki tuzatish
  yozilsa `created_at` bir xil bo'lishi mumkin va tartib SO'ROVDAN
  SO'ROVGA o'zgarardi — dialog har ochilganda boshqa ketma-ketlik
  ko'rsatardi.
"""

_CHARGE_EVIDENCE_ROWS = text(
    """
    SELECT e.snapshot_id AS snapshot_id,
           e.slot_time   AS slot_time
      FROM charge_evidence e
     WHERE e.market_id = :market_id
       AND e.charge_id = :charge_id
     ORDER BY e.slot_time, e.id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("charge_id", type_=_UUID),
)
"""DL-3 ning 5-bo'limi — MUZLATILGAN dalil kadrlari (BILL-02, D-08).

⚠ `charge_evidence.snapshot_id` SXEMADA `NOT NULL`, ya'ni bu so'rov
  bugun `null` QAYTARMAYDI. Kontrakt (`ChargeEvidenceRow.snapshot_id`)
  baribir nullable bo'lib qoladi va bu ATAYIN: 05-14 ning darsi
  bo'yicha marshrut bermagan qator UMUMAN chizilmaydi — ya'ni klientda
  «kadr yo'q» shoxi MAVJUD bo'lishi kerak. Uni server tomondan
  `NOT NULL` deb e'lon qilish o'sha shoxni o'lik kod qilib qo'yardi va
  kelajakda `no_coverage` sinfidagi dalil qo'shilganda klient PARSE
  PAYTIDA yiqilardi.

⛔ KADRNING O'ZI BU MARSHRUTDAN KELMAYDI: rasm `GET /snapshots/{id}/image`
   proxysidan olinadi va AYNAN o'sha marshrut `audit_read` yozadi
   (§11.3, M-8). Presigned URL berilmaydi va so'ralmaydi.
"""

_ANOMALY_ROWS = text(
    """
    SELECT b.id           AS anomaly_id,
           b.kind         AS kind,
           s.code         AS stall_code,
           b.service_date AS service_date,
           b.snapshot_id  AS snapshot_id
      FROM billing_anomalies b
      JOIN stalls s
        ON s.market_id = b.market_id
       AND s.id = b.stall_id
     WHERE b.market_id = :market_id
       AND b.service_date = :day
     ORDER BY b.kind, s.code_sort, s.id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("day", type_=Date()),
)
"""Kun kesimidagi anomaliyalar (BILL-04, §11.4).

⛔ SO'ROV `kind` BO'YICHA GURUHLAMAYDI va yagona sanoq BERMAYDI — u
   QATORLARNI qaytaradi, sanoqni esa `anomaly_list()` uch ALOHIDA
   hisoblagichga ajratadi (D-05). SQL da `count(*)` yozish uchala turni
   bitta songa qo'shishni BIR SATRLIK o'zgartirish qilib qo'yardi.
"""


@dataclass(frozen=True, slots=True)
class ChargeRow:
    """Hisoblar jadvalining bitta qatori (UI-SPEC §11.2).

    ⛔ `vendor_name` YO'Q, `vendor_id` BOR (C-10): ism MAVJUD, AUDIT
       QILINGAN `GET /vendors` dan KLIENTDA joinlanadi.

    ⚠ `amount_soum` — TUZATISHLAR BILAN NETLANGAN summa. Xom
      `daily_charges.amount_soum` o'zgarmas (D-07) va tuzatish ALOHIDA
      qator bo'ladi, ya'ni «amaldagi summa» har doim HISOBLANADIGAN
      ko'rinish (`ChargeAdjustment` klass docstringi).
    """

    charge_id: UUID
    stall_code: str
    vendor_id: UUID
    service_date: date
    tariff_amount_soum: int
    amount_soum: int
    outstanding_soum: int


@dataclass(frozen=True, slots=True)
class ChargeAdjustmentItem:
    """Bitta tuzatish yozuvi — DL-3 ning 4-bo'limi.

    ⛔ `actor_user_id` — `None` = TIZIM (`0022`): `late_review`
       tuzatishini `billing_close` job'i yozadi, odam emas
       (`write_late_review_adjustment()` docstringi).
    """

    adjustment_id: UUID
    direction: str
    amount_soum: int
    reason_code: str
    actor_user_id: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ChargeEvidenceItem:
    """Bitta dalil kadri — DL-3 ning 5-bo'limi."""

    snapshot_id: UUID | None
    slot_time: time


@dataclass(frozen=True, slots=True)
class ChargeDetail:
    """DL-3 ning BESH bo'limi bitta natijada (§11.3).

    ⛔ `tariff_id` YO'Q (§11.3, 2-bo'lim) va `vendor_id` ham YO'Q:
       sarlavhada rasta KODI turadi. Tafsilot dialogi sotuvchi nomini
       jadval qatoridan oladi — ikkinchi shaxsiy-ma'lumot yo'li
       ochilmaydi.
    """

    charge_id: UUID
    service_date: date
    stall_code: str
    tariff_amount_soum: int
    amount_soum: int
    adjustments: tuple[ChargeAdjustmentItem, ...]
    evidence: tuple[ChargeEvidenceItem, ...]


@dataclass(frozen=True, slots=True)
class AnomalyRow:
    """Bitta anomaliya qatori (BILL-04).

    ⛔ JUFTLANGAN INVARIANT C-12 ning DB `CHECK` ida va javob modelida
       ikki marta majburlanadi; bu yerda u QAYTA TEKSHIRILMAYDI —
       uchinchi nusxa uchinchi haqiqat manbai bo'lardi.
    """

    anomaly_id: UUID
    kind: str
    stall_code: str
    service_date: date
    snapshot_id: UUID | None


@dataclass(frozen=True, slots=True)
class AnomalyCounts:
    """Uch ALOHIDA sanoq — ⛔ HECH QACHON QO'SHILMAYDI (D-05).

    «Ko'ra olmadik» (`no_coverage`) ≠ «band, lekin biriktirilmagan»
    (`unassigned`). Yagona `total` maydoni ATAYIN yo'q: u mavjud bo'lsa
    ekran uni ko'rsatardi va farq matn darajasida yo'qolardi — bu esa
    KO'R NUQTADAN TUSHUM DA'VOSI to'qish bo'lardi.
    """

    unassigned: int
    closed_day: int
    no_coverage: int


async def charge_list(
    session: AsyncSession, *, market_id: UUID, day: date
) -> tuple[ChargeRow, ...]:
    """Kun kesimidagi yozilgan hisoblar + sotuvchi kesimidagi qoldiq.

    ⛔ QOLDIQ `vendor_outstanding()` DAN keladi va bu yerda QAYTA
       HISOBLANMAYDI (BILL-03, G-14): saqlangan balans ustuni yo'q va
       ikkinchi arifmetika ikkinchi haqiqat manbai bo'lardi.

    ⚠ `as_of` BERILMAYDI (ya'ni `None`): jadvaldagi «Qoldiq» ustuni
      sotuvchining BUGUNGI to'liq qarzini ko'rsatadi. `as_of=day` bilan
      chaqirish o'sha kunning O'Z hisobini qoldiqdan CHIQARIB
      tashlagan bo'lardi va direktor «hisob yozilgan, lekin qarz
      o'smabdi» degan xulosaga kelardi.

    Returns:
        `code_sort` tartibidagi qatorlar. ⛔ Bo'sh kortej — NORMAL javob
        (C-3: hisob D+1 04:10 da tug'iladi), nosozlik EMAS.
    """
    result = await session.execute(
        _CHARGE_ROWS,
        {
            "market_id": market_id,
            "day": day,
            "increase": AdjustmentDirection.INCREASE.value,
        },
    )
    rows = list(result.mappings())
    if not rows:
        return ()

    balances = await vendor_outstanding(
        session,
        market_id=market_id,
        vendor_ids=[row["vendor_id"] for row in rows],
    )
    return tuple(
        ChargeRow(
            charge_id=row["charge_id"],
            stall_code=str(row["stall_code"]),
            vendor_id=row["vendor_id"],
            service_date=row["service_date"],
            tariff_amount_soum=int(row["tariff_amount_soum"]),
            amount_soum=int(row["amount_soum"]),
            outstanding_soum=balances.get(row["vendor_id"], 0),
        )
        for row in rows
    )


async def charge_detail(
    session: AsyncSession, *, market_id: UUID, charge_id: UUID
) -> ChargeDetail | None:
    """Bitta hisobning tafsiloti — tuzatishlar va MUZLATILGAN dalil bilan.

    Returns:
        `None` — hisob bu bozorda YO'Q. ⛔ Begona bozorning hisobi ham
        AYNAN shu javobni beradi (RLS 0 qator ko'rsatadi), ya'ni
        chaqiruvchi 404 ni ikkala holatda ham bir xil qaytaradi va
        javobning O'ZI enumeration signali bo'lmaydi (T-01-76).
    """
    head = await session.execute(
        _CHARGE_DETAIL,
        {
            "market_id": market_id,
            "charge_id": charge_id,
            "increase": AdjustmentDirection.INCREASE.value,
        },
    )
    row = head.mappings().one_or_none()
    if row is None:
        return None

    params = {"market_id": market_id, "charge_id": charge_id}
    adjustments = await session.execute(_CHARGE_ADJUSTMENTS, params)
    evidence = await session.execute(_CHARGE_EVIDENCE_ROWS, params)

    return ChargeDetail(
        charge_id=row["charge_id"],
        service_date=row["service_date"],
        stall_code=str(row["stall_code"]),
        tariff_amount_soum=int(row["tariff_amount_soum"]),
        amount_soum=int(row["amount_soum"]),
        adjustments=tuple(
            ChargeAdjustmentItem(
                adjustment_id=item["adjustment_id"],
                direction=str(item["direction"]),
                amount_soum=int(item["amount_soum"]),
                reason_code=str(item["reason_code"]),
                actor_user_id=item["actor_user_id"],
                created_at=item["created_at"],
            )
            for item in adjustments.mappings()
        ),
        evidence=tuple(
            ChargeEvidenceItem(snapshot_id=item["snapshot_id"], slot_time=item["slot_time"])
            for item in evidence.mappings()
        ),
    )


async def anomaly_list(
    session: AsyncSession, *, market_id: UUID, day: date
) -> tuple[tuple[AnomalyRow, ...], AnomalyCounts]:
    """Kun kesimidagi anomaliyalar va ⛔ UCH ALOHIDA sanoq (BILL-04, D-05).

    ⛔ SANOQ QATORLARDAN HOSILA, ikkinchi `count(*)` so'rovi bilan EMAS:
       ikki so'rov orasida yangi qator yozilsa ro'yxat bilan sanoq
       ajralib ketardi va ekranda «3 ta anomaliya» yozuvi ostida 2 qator
       turardi.

    Returns:
        `(qatorlar, sanoqlar)`. ⛔ Uchala sanoq ham NOL bo'lganda ham
        qaytadi — nol NATIJA (`occupancy.py:122-124` qoidasi).
    """
    result = await session.execute(_ANOMALY_ROWS, {"market_id": market_id, "day": day})
    rows = tuple(
        AnomalyRow(
            anomaly_id=row["anomaly_id"],
            kind=str(row["kind"]),
            stall_code=str(row["stall_code"]),
            service_date=row["service_date"],
            snapshot_id=row["snapshot_id"],
        )
        for row in result.mappings()
    )
    return rows, AnomalyCounts(
        unassigned=sum(1 for row in rows if row.kind == AnomalyKind.UNASSIGNED_OCCUPIED.value),
        closed_day=sum(1 for row in rows if row.kind == AnomalyKind.CLOSED_DAY_OCCUPIED.value),
        no_coverage=sum(1 for row in rows if row.kind == AnomalyKind.NO_COVERAGE_STALL.value),
    )
