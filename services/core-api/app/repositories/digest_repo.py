"""Dayjest sonlarining YAGONA so'rov manbai (RECON-03, BOT-03).

=============================================================================
⛔⛔ MODULNING OMMAVIY YUZASI — AYNAN TO'RT FUNKSIYA VA UCH NATIJA TIPI.
   HAR BIR IMPORT PASTKI CHIZIQ BILAN ALIASLANGAN VA BU USLUB EMAS,
   `headline_repo.py` DA O'LCHANGAN HIMOYANING AYNAN O'ZI.

`dir(digest_repo)` dagi pastki chiziqsiz FUNKSIYALAR ro'yxati AYNAN
`ledger_day`, `occupancy_percent`, `overdue_vendors`, `top_debtors` dan
iborat bo'lishi SHART. Bu modulning har bir soni TELEGRAM XABARIGA
tushadi, ya'ni u chegaradan chiqadi (D-01). Aliaslanmagan
`from app.repositories.vendor_repo import ...` modul nomlar fazosini
kengaytirardi va keyingi ijrochi `digest_repo.<ism qaytaradigan funksiya>`
ni jobdan chaqira olardi — ya'ni ism xabarga BITTA import bilan yetib
borardi.

⚠ SHU SABABDAN `from __future__ import annotations` HAM YO'Q
  (`headline_repo.py` da o'lchangan): u modulga `annotations` nomini
  bog'lab qo'yadi. Annotatsiyalar ish vaqtidagi HAQIQIY nomlarga
  (`_UUID`, `_date`, `_AsyncSession`) tayanadi.
=============================================================================

=============================================================================
⛔⛔ ISM VA IDENTIFIKATOR CHEGARADAN CHIQMAYDI (D-01/D-05).

`top_debtors()` — SON qaytaradi, ro'yxat emas. `overdue_vendors()` esa
`vendor_id` ni qaytaradi va u XABAR MANZILINI aniqlash uchun kerak
(`outbox_repo.resolve_chat_id()`), matnga tushmaydi: sotuvchi O'Z
qarzining sonini oladi, boshqa hech kimning ismini emas.

TOP-10 ning O'ZI direktorga VEB YUZASIDA, autentifikatsiya ostida
ko'rinadi; xabarda faqat SON va HAVOLA bo'ladi (D-03 naqshi: dalil
havola bo'lib boradi). Ism Telegram serverlariga chiqsa u
data-rezidentlik chegarasidan chiqardi va uni ORQAGA QAYTARIB
BO'LMASDI.
=============================================================================

=============================================================================
⛔ BU MODULDA YANGI ARIFMETIKA YO'Q — TO'RTALA FUNKSIYA HAM MAVJUD
   MAHSULOT FUNKSIYALARINI CHAQIRADI:

     `ledger_day().collected_soum`  -> `headline_repo.revenue_today_soum()`
     `occupancy_percent()`          -> `OccupancyRepository.day_summary()`
     `top_debtors()`                -> `billing_repo.vendor_outstanding()`
     `overdue_vendors()`            -> `vendor_outstanding()` +
                                       `vendor_charge_allocation()`

Ikkinchi ifoda yozilganda direktorning kechki xabari, ertalabki dayjesti
va bosh ekrandagi son SEKIN-ASTA ajralib ketardi va UCHALASI HAM
«to'g'ri» bo'lardi — bu loyihada takroran topilgan «ikki haqiqat manbai»
sinfi (D-32).
=============================================================================

⚠ PUL — BUTUN SO'M (`BIGINT` <-> `int`, D-07/D-11). Bu modulda kasrli tip
  ham, yaxlitlash ham YO'Q va bandlik foizi ham BUTUN SON bilan
  hisoblanadi (`occupancy_percent()` docstringi).
"""

from dataclasses import dataclass as _dataclass
from datetime import date as _date
from typing import Final as _Final
from uuid import UUID as _UUID

from sbozor_core.enums import AdjustmentDirection as _AdjustmentDirection
from sbozor_core.enums import PaymentKind as _PaymentKind
from sqlalchemy import Date as _Date
from sqlalchemy import Text as _Text
from sqlalchemy import bindparam as _bindparam
from sqlalchemy import text as _text
from sqlalchemy.dialects.postgresql import UUID as _PgUuid
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

from app.repositories.billing_repo import vendor_charge_allocation as _vendor_charge_allocation
from app.repositories.billing_repo import vendor_outstanding as _vendor_outstanding
from app.repositories.headline_repo import revenue_today_soum as _revenue_today_soum
from app.repositories.occupancy_repo import OccupancyRepository as _OccupancyRepository

__all__ = [
    "LedgerDay",
    "OverdueVendor",
    "TopDebtors",
    "ledger_day",
    "occupancy_percent",
    "overdue_vendors",
    "top_debtors",
]

_UUID_TYPE: _Final = _PgUuid(as_uuid=True)

_TOP_DEBTOR_LIMIT: _Final[int] = 10
"""TOP ro'yxatining uzunligi — xabarga faqat SANOG'I tushadi.

⚠ Chegaraning O'ZI xabarda ko'rinmaydi: «10 ta eng katta qarzdor»
  degan jumla direktorni ro'yxatni SO'RASHGA undardi va o'sha so'rov
  ismlarni Telegramga olib chiqadigan yagona yo'l bo'lardi. Xabarda
  «qarzdor: N» va veb havolasi turadi.
"""

_SIGNED_PAYMENT_EXPR: _Final[str] = (
    "CASE WHEN p.kind = :reversal THEN -p.amount_soum ELSE p.amount_soum END"
)
"""To'lovning BELGILI qiymati — ustun har doim MUSBAT, belgi KO'RINISHDA (C-5).

=============================================================================
⛔ BU IFODA BU YERDA FAQAT RASTA KESIMI UCHUN YOZILGAN.

BOZOR x KUN yig'indisi bu modulda QAYTA YOZILMAYDI: u
`headline_repo.revenue_today_soum()` dan CHAQIRIB olinadi va
`ledger_day().collected_soum` aynan o'sha funksiyaning natijasi. Ya'ni
direktorning ertalabki dayjesti va bosh ekrandagi «bugungi tushum»
AJRALA OLMAYDI.

Rasta kesimi esa boshqa savol («qaysi rasta to'lamadi?») va u boshqa
`GROUP BY` talab qiladi — `headline_repo.py` ning modul docstringi bu
farqni allaqachon nomlagan (`billing_repo._SIGNED_PAYMENT_EXPR` sotuvchi
kesimida, `payment_repo._SHIFT_SYSTEM_TOTAL` smena kesimida).
=============================================================================

⚠ `payments.amount_soum` da `CHECK (> 0)` bor: storno manfiy summa bilan
  EMAS, `kind = 'reversal'` bilan yoziladi va belgi faqat shu ifodada
  tug'iladi.
"""

_SIGNED_ADJUSTMENT_EXPR: _Final[str] = (
    "CASE WHEN a.direction = :increase THEN a.amount_soum ELSE -a.amount_soum END"
)
"""Tuzatishning BELGILI qiymati — `billing_repo` dagi jufti bilan bir xil qoida.

⛔ TUZATISHLAR `charged_soum` GA KIRADI VA BU TANLOV EMAS, MOSLIKNING
   SHARTI: `vendor_outstanding()` qoldiqni AYNAN `hisob + belgili
   tuzatish - belgili to'lov` deb hisoblaydi. Tuzatishni tashlab
   ketganda ertalabki dayjestdagi «yozilgan» son bilan o'sha kunning
   qarzdorlik sanog'i BIR-BIRIGA MOS KELMASDI — direktor ikkita ichki
   ziddiyatli raqamni bir xabarda ko'rardi.
"""

_LEDGER_DAY = _text(
    f"""
    WITH charged AS (
        SELECT c.stall_id AS stall_id,
               (c.amount_soum + COALESCE(adj.total, 0))::bigint AS due_soum
          FROM daily_charges c
          LEFT JOIN LATERAL (
              SELECT sum({_SIGNED_ADJUSTMENT_EXPR}) AS total
                FROM charge_adjustments a
               WHERE a.market_id = c.market_id
                 AND a.charge_id = c.id
          ) adj ON true
         WHERE c.market_id = :market_id
           AND c.service_date = :business_date
    ),
    paid AS (
        SELECT p.stall_id AS stall_id,
               sum({_SIGNED_PAYMENT_EXPR})::bigint AS paid_soum
          FROM payments p
         WHERE p.market_id = :market_id
           AND p.service_date = :business_date
         GROUP BY p.stall_id
    )
    SELECT COALESCE(sum(charged.due_soum), 0)::bigint AS charged_soum,
           count(*)::int AS charge_count,
           count(*) FILTER (
               WHERE COALESCE(paid.paid_soum, 0) < charged.due_soum
           )::int AS unpaid_stall_count,
           (SELECT count(*) FROM paid WHERE paid.paid_soum > 0)::int AS paid_stall_count
      FROM charged
      LEFT JOIN paid
        ON paid.stall_id = charged.stall_id
    """  # noqa: S608
).bindparams(
    _bindparam("market_id", type_=_UUID_TYPE),
    _bindparam("business_date", type_=_Date()),
    _bindparam("increase", type_=_Text()),
    _bindparam("reversal", type_=_Text()),
)
"""YOZILGAN kunning to'rt soni — D-16 ning manbai.

=============================================================================
⛔ SO'ROV `daily_charges` DAN BOSHLANADI, `payments` DAN EMAS.

Ertalabki dayjest «kecha NIMA YOZILDI?» degan savolga javob beradi.
`payments` dan boshlangan so'rov hisobsiz to'lovni ham sanardi (avans,
eski qarzning yopilishi) va «kecha yozilgan patta» soni kechagi kunga
umuman tegishli bo'lmagan pulni o'z ichiga olardi.
=============================================================================

⛔ `LEFT JOIN paid` — `JOIN` EMAS. To'lovsiz rasta AYNAN o'lchanadigan
   holat (`unpaid_stall_count`); ichki `JOIN` uni butunlay yo'qotardi va
   sanoq HAR DOIM nol bo'lardi — jimgina, xatosiz.

⛔ `COALESCE(paid.paid_soum, 0) < charged.due_soum` — QAT'IY KICHIK.
   `<=` yozilganda to'liq to'langan rasta ham «to'lanmagan» bo'lib
   ko'rinardi va sanoq har kuni bozordagi hamma rastani ko'rsatardi.

⛔ `paid_stall_count` `charged` DAN MUSTAQIL (skalyar quyi so'rov) VA BU
   MAJBURIY: kechqurun `charged` BO'SH bo'ladi (D-15 — bugungi hisob hali
   yozilmagan), ya'ni `LEFT JOIN` orqali hisoblangan sanoq HAR DOIM nol
   chiqardi. Kechki dayjest esa aynan shu songa tayanadi: «bugun patta
   kutilayotgan rasta» MINUS «bugun to'lov yozilgan rasta».

⚠ BO'SH KUN ham BITTA qator qaytaradi (agregat + `COALESCE`): to'rtala
  son `0` bo'lib keladi. «Hisob yo'q» bilan «so'rov ishlamadi» ni
  ajratmaydigan javob direktorni ma'lumot yo'qolgan deb o'ylashga
  majburlardi (`PendingMarket` da o'rnatilgan qoida).
"""


@_dataclass(frozen=True, slots=True)
class LedgerDay:
    """YOZILGAN kunning sonlari (D-16) — ertalabki dayjestning kirishi.

    ⛔ NOL — NATIJA, uning yo'qligi emas: hamma maydon HAR DOIM
       qaytariladi.
    """

    business_date: _date
    charged_soum: int
    """`daily_charges` + belgili tuzatishlar (`_SIGNED_ADJUSTMENT_EXPR`)."""
    collected_soum: int
    """⛔ `headline_repo.revenue_today_soum()` NING AYNAN NATIJASI.

    Ikkinchi ifoda YOZILMAYDI (modul docstringining 3-bandi): dayjest
    kechagi kunni, bosh ekran esa bugungisini so'raydi — ikkalasi ham
    AYNI funksiyadan chiqadi va ajrala olmaydi.
    """
    charge_count: int
    unpaid_stall_count: int
    """Hisob BOR, belgili to'lov uni QOPLAMAGAN rastalar soni.

    ⚠ Kechqurun bu son HAR DOIM `0` va bu D-15 ning O'ZI: bugungi hisob
      `daily_charges` da hali yo'q. Kechki dayjest shuning uchun
      `paid_stall_count` ni proyeksiyaning rasta sanog'idan ayiradi.
    """
    paid_stall_count: int
    """O'sha kun uchun BELGILI to'lovi MUSBAT bo'lgan rastalar soni.

    ⛔ HISOBDAN MUSTAQIL: kechqurun hisob yo'q, to'lov esa BOR va aynan
       shu son «bugun qaysi rastadan patta yig'ildi?» degan savolga
       javob beradi (mahsulotning asosiy savoli).

    ⚠ OCHIQ NARX: faqat ESKI QARZINI to'lagan sotuvchining rastasi ham
      shu sanoqqa kiradi. Ya'ni son «kassir bu rastaga BORDIMI?» ni
      o'lchaydi — bugungi patta to'liq yopilganini emas. Aniqroq savol
      («hisob to'liq qoplandimi?») ertalabki dayjestda, `daily_charges`
      yozilgandan KEYIN javob oladi (`unpaid_stall_count`).
    """


@_dataclass(frozen=True, slots=True)
class TopDebtors:
    """⛔ FAQAT IKKI SON — ISM HAM, IDENTIFIKATOR HAM YO'Q (D-01/D-05).

    Bu dataklassga `vendor_id` / `vendor_name` / `phone` maydonini
    qo'shish TAQIQLANADI: natija direktorning Telegram xabariga tushadi,
    ya'ni u data-rezidentlik chegarasidan chiqadi. Taqiq
    `dataclasses.fields()` ustidagi to'plam tengligi bilan o'lchanadi —
    grep emas, chunki grep yangi nom o'ylab topilganda jimgina yashil
    qolardi.
    """

    count: int
    """Ro'yxatdagi qarzdorlar soni (`<= limit`)."""
    outstanding_soum: int
    """⛔ FAQAT RO'YXATDAGILARNING yig'indisi, bozorning JAMI qarzi EMAS."""


@_dataclass(frozen=True, slots=True)
class OverdueVendor:
    """BOT-03 eslatmasining bitta manzili.

    ⛔ `vendor_name` va `phone` YO'Q (D-05). `vendor_id` esa MANZILNI
       aniqlash uchun (`outbox_repo.resolve_chat_id()`) va u xabar
       MATNIGA tushmaydi.
    """

    vendor_id: _UUID
    outstanding_soum: int
    oldest_service_date: _date
    """Eng eski TO'LANMAGAN kun — `FIFO_OLDEST_SERVICE_DATE_FIRST` dan."""


async def ledger_day(
    session: _AsyncSession, *, market_id: _UUID, business_date: _date
) -> LedgerDay:
    """YOZILGAN kunning hisobi (D-16) — ertalabki dayjestning YAGONA manbai.

    =======================================================================
    ⛔⛔ MAJBURIYAT: `collected_soum` `headline_repo.revenue_today_soum()`
        DAN KELADI VA BU FUNKSIYADA IKKINCHI «BOZOR x KUN» YIG'INDISI
        YOZILMAYDI.

    Ikki ifoda bugun bir xil son berardi va ertaga — masalan storno
    qoidasi o'zgarganda yoki `service_date` / `business_date` filtri
    almashganda — JIMGINA ajralardi. O'shanda direktorning ertalabki
    xabari bilan bosh ekrandagi son farq qilardi va ikkalasi ham xatosiz
    ko'rinardi.
    =======================================================================

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti (RLS ustidagi ikkinchi qatlam).
        business_date: qaysi kunning YOZILGAN hisobi (`Asia/Tashkent`).
            ⛔ ARGUMENT — job uni o'zi hisoblamaydi.

    Returns:
        `LedgerDay` — besh son, hammasi HAR DOIM to'ldirilgan.
    """
    row = (
        await session.execute(
            _LEDGER_DAY,
            {
                "market_id": market_id,
                "business_date": business_date,
                "increase": _AdjustmentDirection.INCREASE.value,
                "reversal": _PaymentKind.REVERSAL.value,
            },
        )
    ).mappings()
    numbers = row.one()
    collected = await _revenue_today_soum(session, market_id=market_id, business_date=business_date)
    return LedgerDay(
        business_date=business_date,
        charged_soum=int(numbers["charged_soum"]),
        collected_soum=collected,
        charge_count=int(numbers["charge_count"]),
        unpaid_stall_count=int(numbers["unpaid_stall_count"]),
        paid_stall_count=int(numbers["paid_stall_count"]),
    )


async def occupancy_percent(
    session: _AsyncSession, *, market_id: _UUID, business_date: _date
) -> int | None:
    """Kunlik bandlik foizi — ⛔ BUTUN SON (0..100), `float` EMAS.

    =======================================================================
    ⛔ BUTUN BO'LINMA (`//`) VA SABAB D-07 DA: loyihada pul turi `int`
       qilib qulflangan va kasrli tip hamda yaxlitlash chaqiruvlari yangi
       modullarga TARQAMAYDI — G7-8 darvozasi aynan shu tarqalishni
       o'lchaydi va u IZOHNI KODDAN AJRATMAYDI (03-07 ning o'lchangan
       darsi), shuning uchun taqiqlangan chaqiruvlar bu yerda NOMMA-NOM
       yozilmaydi. Direktor uchun «bandlik 72 %» yetarli aniqlik;
       «71.8 %» esa xabarda uchala locale'da boshqacha yaxlitlanardi va
       bir xil ko'rinmasdi.

    ⛔ MAXRAJ NOL BO'LGANDA JAVOB `None`, ⛔ `0` EMAS (05-14 ning darsi).
       «Bozorda rasta yo'q» bilan «hech biri band emas» bir xil
       ko'rinsa, direktor kadr olinmagan kunni «hammasi bo'sh» deb
       o'qirdi — ya'ni O'LCHANMAGAN holat O'LCHANGAN nol bo'lib
       ko'rinardi.
    =======================================================================

    ⛔ MAXRAJ `OccupancyRepository.day_summary()` DAN: `stalls` — to'rt
       o'zaro inkor bo'lakning MUSTAQIL guvohi (`OccupancyDaySummary`
       docstringi). Bu yerda yangi `count(*)` yozilsa u `_PER_STALL_CTE`
       ning doirasidan (kadr olingan slotlar) ajralib ketardi.

    Returns:
        `0..100` oralig'idagi butun son, yoki `None` — o'sha kunda
        materializatsiya qilingan rasta UMUMAN yo'q.
    """
    summary = await _OccupancyRepository(session, market_id).day_summary(business_date)
    if summary.stalls == 0:
        return None
    return summary.occupied * 100 // summary.stalls


async def top_debtors(
    session: _AsyncSession,
    *,
    market_id: _UUID,
    as_of: _date,
    limit: int = _TOP_DEBTOR_LIMIT,
) -> TopDebtors:
    """Eng katta qarzdorlarning SANOG'I va yig'indisi — ⛔ ISM YO'Q (D-01).

    =======================================================================
    ⛔⛔ TAQIQ: BU FUNKSIYA HECH QACHON SOTUVCHINING ISMINI, TELEFONINI
        YOKI `vendor_id` SINI QAYTARMAYDI.

    Natija direktorning TELEGRAM xabariga tushadi. Telegram serverlari
    O'zbekistondan tashqarida, ya'ni ism u yerga chiqsa u
    data-rezidentlik chegarasidan chiqardi va uni ORQAGA QAYTARIB
    BO'LMASDI (D-01). TOP-10 ning O'ZI direktorga veb yuzasida,
    autentifikatsiya ostida ko'rinadi va xabarda faqat HAVOLA bo'ladi —
    bu D-03 ning naqshi: dalil havola bo'lib boradi, nusxa bo'lib emas.
    =======================================================================

    ⛔ QOLDIQ `vendor_outstanding()` DAN (BILL-03) — yangi SQL
       YOZILMAYDI. Ikkinchi ifoda kassir ekranidagi qarz bilan
       direktorning sanog'ini ajratardi.

    ⚠ FAQAT MUSBAT QOLDIQ SANALADI. Avans (manfiy qoldiq) qarzdor EMAS
      va uni ro'yxatga qo'shish `outstanding_soum` ni KAMAYTIRARDI —
      `_market_projection()` da o'lchangan aynan shu tuzoq.

    Args:
        as_of: `vendor_outstanding()` ning chegarasi — hisoblar
            `service_date < as_of` bilan cheklanadi.
        limit: ro'yxatning uzunligi.

    Returns:
        `TopDebtors(count, outstanding_soum)` — qarzdor yo'q bozorda
        ikkala son ham `0` va bu O'LCHANGAN javob.
    """
    outstanding = await _vendor_outstanding(session, market_id=market_id, as_of=as_of)
    ranked = sorted((soum for soum in outstanding.values() if soum > 0), reverse=True)
    listed = ranked[:limit]
    return TopDebtors(count=len(listed), outstanding_soum=sum(listed))


async def overdue_vendors(
    session: _AsyncSession,
    *,
    market_id: _UUID,
    cutoff: _date,
) -> list[OverdueVendor]:
    """BOT-03 eslatmasining manzillari — ⛔ `recon.open` BILAN AYNI PREDIKAT.

    =======================================================================
    ⛔⛔ UCH QADAM VA HECH BIRIDA YANGI ARIFMETIKA YO'Q —
        `reconciliation_repo._open_unpaid_cases()` NING AYNAN QADAMLARI
        (D-19, Pattern 5):

      1. `vendor_outstanding()` — qoldig'i MUSBAT sotuvchilar;
      2. `vendor_charge_allocation()` — kredit QAYSI KUNLARNI yopdi
         (`FIFO_OLDEST_SERVICE_DATE_FIRST`, D-24). ⛔ IKKINCHI
         TAQSIMLASH YOZILMAYDI: `allocate_charge_credit()` ning
         docstringi bu vasvasani nomma-nom taqiqlaydi;
      3. kechikish chegarasi ENG OXIRIDA qo'llanadi.
         ⛔ CHEGARA BU YERDA HISOBLANMAYDI: `cutoff` ARGUMENT bo'lib
         keladi (`app.jobs.reconciliation.overdue_cutoff()`), ya'ni
         `recon.open` bilan AYNAN bir qiymatdan yuradi (WR-06). 07-fazada
         bu yerda o'z ayirish ifodasi bor edi va u `recon.open` nikidan
         MAHSULOTDA bir kunga ajralib turardi.

    ⛔ QADAMLARNING TARTIBI MAJBURIY. Chegarani birinchi qadamga surish
       qoldiqni FAQAT eski hisoblardan hisoblardi va bugungi to'lovi
       bilan eski qarzini yopgan sotuvchi baribir eslatma olardi.

    ⛔ TAQQOSLASH `<=`, `<` EMAS — `_OVERDUE_CHARGES` ning
       `c.service_date <= :cutoff` bandi bilan AYNAN bir xil. `<`
       yozilganda chegaradagi kun bir mexanizmda case ochib, ikkinchisida
       eslatma BERMASDI: sotuvchi ogohlantirilmagan holda nazoratchi
       navbatiga tushardi va bu D-19 ning butun mazmunini buzardi.
    =======================================================================

    ⚠ N+1 SO'ROV ONGLI QABUL QILINGAN (07-07 ning aynan qarori): yagona
      muqobil — taqsimlash qoidasini SQL da qayta yozish, ya'ni
      nomlangan qoidaning IKKINCHI NUSXASI. Job kechasi bir marta
      yuguradi va qarzdorlar soni bozordagi sotuvchilar sonidan katta
      emas.

    Args:
        cutoff: eng kech «kechikkan» sanaladigan kun — ⛔ `recon.open`
            ning `open_cases(cutoff=...)` iga uzatilgan qiymat bilan
            AYNI. Ikkalasi ham `overdue_cutoff(business_date,
            market_notification_settings.overdue_days)` dan chiqadi.

    Returns:
        `(oldest_service_date, vendor_id)` bo'yicha saralangan ro'yxat —
        tartib DETERMINISTIK, aks holda navbatga yozilish tartibi har
        yugurishda o'zgarardi va takroriylikni faqat `dedupe_key`
        ushlab turardi.
    """
    outstanding = await _vendor_outstanding(session, market_id=market_id)
    debtors = sorted((vendor_id for vendor_id, soum in outstanding.items() if soum > 0), key=str)
    if not debtors:
        return []

    found: list[OverdueVendor] = []
    for vendor_id in debtors:
        allocation = await _vendor_charge_allocation(
            session, market_id=market_id, vendor_id=vendor_id
        )
        unpaid_days = [row.service_date for row in allocation.rows if row.unpaid_soum > 0]
        if not unpaid_days:
            # Kredit hamma kunni TO'LIQ yopgan — qoldiq boshqa manbadan.
            continue
        oldest = min(unpaid_days)
        if oldest > cutoff:
            # Hisob hali KECHIKMAGAN — Pattern 5 ning chegarasi.
            continue
        found.append(
            OverdueVendor(
                vendor_id=vendor_id,
                outstanding_soum=outstanding[vendor_id],
                oldest_service_date=oldest,
            )
        )
    return sorted(found, key=lambda item: (item.oldest_service_date, str(item.vendor_id)))
