"""Direktor dayjestlari (RECON-03) va qarz eslatmasi (BOT-03) — NIYAT YOZADI.

=============================================================================
1. ⛔⛔ UCHALA JOB HAM NAVBATGA NIYAT YOZADI, HECH BIRI JO'NATMAYDI
   (D-08/D-23).

Ular `outbox_repo.enqueue()` ni chaqiradi va Telegram bilan UMUMAN
gaplashmaydi: jo'natish `notify.outbox_tick` ning ishi va uning yagona
jo'natuvchi sinfi bu modulga IMPORT QILINMAYDI. Sabab mexanik — job
kechasi/ertalab bir marta yuguradi va tashqi xizmat o'sha daqiqada
javob bermasa, jo'natishni job ichida bajarish butun dayjestni
YO'QOTARDI; navbat qatori esa qoladi va keyingi tikda ketadi.

=============================================================================
2. ⛔⛔ IKKI DAYJEST — IKKI MANBA VA ULARNING SONLARI BIR XIL EMAS
   (D-15/D-16). BU NUQSON EMAS, DIZAYN.

    20:45  `digest_evening`  -> `billing_repo.pending_projection(as_of)`
                               «bugun KUTILAYOTGAN»
    08:00  `digest_morning`  -> `daily_charges` + `payments` (kechagi kun)
                               «kecha YOZILGAN»

Mexanik sabab: kunlik hisob D+1 ning 04:10 da tug'iladi, ya'ni KECHQURUN
`daily_charges` da bugungi kun HALI YO'Q. Farq xabar matnida OCHIQ
aytiladi (`07-UI-SPEC.md` §12.2 sifatlovchi kontrakti) — aks holda
direktor ikki raqamni ko'rib tizimga ishonchini yo'qotardi.

⛔ `pending_projection()` BU MODULDA QAYTA YOZILMAYDI. Agar bu yerda
   yangi proyeksiya SQL'i paydo bo'lsa, kechki xabar bilan KASSIR
   EKRANI ajralib ketardi: ikkalasi ham «bugun qancha patta kutilyapti?»
   degan BIR savolga javob beradi va javob BITTA funksiyadan chiqishi
   shart.

=============================================================================
3. ⛔ KUN — ARGUMENT, JOB ICHIDA HISOBLANMAYDI (D-12).

`billing_close(business_date=...)`, `day_close(business_date=...)` va
`reconciliation_open(business_date=...)` da o'rnatilgan qoidaning
beshinchi takrori: kunni QOBIQ (cron registratsiyasi, 07-14) hisoblaydi,
test esa AYNAN o'sha funksiyani BOSHQA kun bilan chaqiradi.

⛔ `digest_evening` GA BUGUNGI KUN BERILADI, KECHAGISI EMAS. Kechagi kun
   berilganda proyeksiya kechagi tarifni qaytarardi va kechki xabar
   ertalabki dayjest bilan AYNAN BIR XIL raqamni ko'rsatardi — D-15 ning
   butun mazmuni yo'qolardi va sifatlovchi kontrakti (§12.2) yolg'onga
   aylanardi.

⚠ CRON REGISTRATSIYASI BU FAYLDA EMAS va bu ATAYIN: qobiq
  (`app/worker.py`) 07-14 niki va u BESHALA jobni bir joyda ro'yxatga
  oladi. Bu modul faqat CHAQIRILADIGAN funksiyalarni beradi.

=============================================================================
4. ⛔ TARTIB KAFOLATI CRON SATRLARIGA TAYANMAYDI (D-16).

`digest_morning` `daily_charges` dan o'qiydi va o'sha jadval `04:10`
dan keyin to'ladi. Job TARTIBNI TALAB QILMAYDI: hisob hali yozilmagan
bo'lsa sonlar NOL bo'lib keladi va `charge_count` yurak urishining
`detail` ida ko'rinadi — ya'ni «hisob yo'q» bilan «job yugurmagan»
ajratiladi. Ikkala job ham IDEMPOTENT: `dedupe_key` da KUN bor, ya'ni
qayta yugurish ikkinchi xabar YOZMAYDI (D-21).

=============================================================================
5. ⛔ BOT-03 NING CHEGARASI `recon.open` BILAN AYNAN BIR KNOB (D-19,
   Pattern 5): `market_notification_settings.overdue_days`.

Ikki alohida sozlama ajralib ketardi va o'shanda direktor navbatida case
turgan, sotuvchi esa eslatma OLMAGAN holat tug'ilardi — ya'ni sotuvchi
ogohlantirilmagan qarz uchun nazoratchi navbatiga tushardi.

⛔ VA BU YERDA D-18 NING TESKARISI KUCHDA: eslatma quiet hours ga
   BO'YSUNADI (kvitansiyadan farqli). Bu HECH QANDAY qo'shimcha kod
   talab qilmaydi va aynan shuning uchun ochiq yozilyapti: bayroq
   `NOTIFICATION_META["overdue_reminder"].never_suppressed` da `False`
   va darvozaning o'zi `outbox_repo.claim()` ning SQL bandida. Keyingi
   ijrochi bu yerda «unutilgan» kod izlamasin.
=============================================================================

⚠ `taskiq` IMPORT QILINMAYDI (S-4) — bu modul sof `async def`.

⚠ ARIFMETIKA BU YERDA YO'Q: dayjestning har bir soni
  `app/repositories/digest_repo.py` va `billing_repo.pending_projection()`
  dan CHAQIRIB olinadi. Bu modul faqat TARTIBNI, SOZLAMANI va
  HISOBLAGICHLARNI biladi.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Final

import structlog
from sbozor_core.enums import ActorKind, OutboxKind, OutboxRecipientKind
from sbozor_core.models.ops import SystemHeartbeat
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import Integer, bindparam, func, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.jobs.notification_meta import DEFAULT_OVERDUE_DAYS, outbox_payload
from app.jobs.reconciliation import overdue_cutoff
from app.jobs.retention import active_market_ids
from app.repositories import digest_repo, outbox_repo
from app.repositories.billing_repo import pending_projection
from app.repositories.reconciliation_repo import list_cases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

log = structlog.get_logger(__name__)

__all__ = [
    "DIGEST_EVENING_COMPONENT",
    "DIGEST_MORNING_COMPONENT",
    "OVERDUE_COMPONENT",
    "DigestResult",
    "ReminderResult",
    "digest_evening",
    "digest_morning",
    "overdue_reminder",
]

_UUID = PgUuid(as_uuid=True)

_DIRECTOR: Final[str] = OutboxRecipientKind.MARKET_DIRECTOR.value
_VENDOR: Final[str] = OutboxRecipientKind.VENDOR.value

DIGEST_MORNING_COMPONENT: Final[str] = "notify_digest_morning"
"""`system_heartbeats.component` — ERTALABKI dayjestning YAKKA tashqi izi.

=============================================================================
⛔⛔ SATR UCH JOYDA O'QILADI VA UCHALASI HAM SHU KONSTANTANI IMPORT
   QILISHI SHART: bu modul uni YOZADI, `app/jobs/alerting.py` uning
   eskirganini o'lchaydi, `app/api/internal/self_check.py` esa uning
   UMUMAN yozilmaganini ko'rsatadi (`never_seen`).

Nom ayrilsa endpoint komponentni MANGU `never_seen` da ko'rsatardi,
holbuki job ishlab turardi — xato yo'q, jurnal yozuvi yo'q, faqat
sukunat (`self_check.py` ning o'lchangan darsi).
=============================================================================

=============================================================================
⛔⛔ 07-13 NING OCHIQ NARXI SHU YERDA YOPILDI (07-21, WR-10).

O'sha reja SUMMARY sining «Struktura bo'yicha ongli qarorlar» B bandi
ochiq yozgan edi: IKKALA dayjest ham BITTA `notify_digest` qatorini
yangilaydi va oqibati — «kechkisi ishlab, ertalabkisi o'lsa yurak urishi
HAMON YANGI ko'rinadi».

Narx endi TO'LANDI, chunki u D-20 ning yagona qoidasini YARIM ishlatardi:
alert MUVAFFAQIYAT SIGNALINING YO'QLIGIGA qo'yiladi — bitta qator esa
ikki jobning YO'QLIGINI bir signalga qo'shib yuborardi va yarim o'lgan
juftlik tirik ko'rinardi. Ikki komponent bilan `digest_stale` endi
ERTALABKISI o'lganda ham ko'tariladi, QAYSI BIRI o'lgani esa
`/internal/self-check` ning `stale` / `never_seen` ro'yxatlarida
NOMMA-NOM turadi.

⛔ ESKI `DIGEST_COMPONENT` ALIASI QOLDIRILMADI: qolgan alias eski nomni
   yozadigan YANGI chaqiruvchi uchun ochiq eshik bo'lardi va o'sha
   chaqiruvchi ikkala reyestrda ham ko'rinmasdi (nom `EXPECTED_COMPONENTS`
   da ham, `watched` da ham yo'q) — ya'ni bu reja yopgan bo'shliq
   jimgina qayta ochilardi.
=============================================================================
"""

DIGEST_EVENING_COMPONENT: Final[str] = "notify_digest_evening"
"""`system_heartbeats.component` — KECHKI dayjestning YAKKA tashqi izi.

⛔ `DIGEST_MORNING_COMPONENT` NING JUFTI VA UNING BUTUN SABABI O'SHA
   KONSTANTANING DOCSTRINGIDA. Ikkalasi ATAYIN ikki qator: bitta qator
   ikki jobni yashirardi.

⚠ IKKALASI HAM `digest_stale` ALERT KALITIGA BOG'LANADI va bu ONGLI
  qaror — sabab `alerting.py::_platform_signals` dagi `watched` korteji
  ustidagi izohda.
"""

OVERDUE_COMPONENT: Final[str] = "notify_overdue"
"""`system_heartbeats.component` — BOT-03 eslatmasining izi.

=============================================================================
⛔ TO'RTINCHI KOMPONENT ATAYIN QO'SHILDI VA BU TADQIQOTDAN CHETLANISH.

`07-RESEARCH.md` uchta komponentni sanaydi (`outbox_tick`,
`reconciliation_open`, `notify_digest`) — BOT-03 ning jobi o'sha
ro'yxatda YO'Q edi. D-17 esa «yangi cron joblar kuzatiladi» deydi va
`deferred-items.md` ning 2-bandidagi dars aynan RO'YXATGA OLINMAGAN
cronning JIMGINA o'lishi.

Kuzatilmagan job hech qanday xato bermaydi: sotuvchilar shunchaki
eslatma olmay qo'yadi va buni ma'muriyat OYLAR keyin, qarz o'sganda
sezadi.
=============================================================================
"""

_MARKET_OVERDUE_DAYS = text(
    """
    SELECT COALESCE(
               (SELECT s.overdue_days
                  FROM market_notification_settings s
                 WHERE s.market_id = :market_id),
               :fallback
           )::int AS overdue_days
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("fallback", type_=Integer()),
)
"""Bozorning kechikish chegarasi — ⛔ `recon.open` NIKI BILAN AYNAN BIR SO'ROV.

=============================================================================
⛔⛔ BU BAYONOT `app/jobs/reconciliation.py::_MARKET_OVERDUE_DAYS` NING
   SO'ZMA-SO'Z JUFTI VA IKKALASI AJRALSA D-19 BUZILADI.

Ajralish TESTDA o'lchanadi, taxmin qilinmaydi:
`test_overdue_reminder_shares_the_knob_with_case_opening` ikkala
mexanizmni ham ⛔ MAHSULOT QOBIQLARIDAN yuritadi va ularning
chegarasi BIR XIL bo'lishini talab qiladi (`test_outbox_repo.py` da
o'rnatilgan «bir qoidaning ikki ifodasi solishtiriladi» naqshi).

=============================================================================
⚠ SO'ROV — JUFT, LEKIN CHEGARA — IMPORT. VA BU FARQ 08-06 DA
  O'LCHANGAN (WR-06).

Bu BAYONOT (`_MARKET_OVERDUE_DAYS`) hamon JUFT: u SOZLAMA USTUNINI
o'qiydi, ya'ni ikki mustaqil jobning yagona umumiy narsasi — ustunning
o'zi (`market_notification_settings.overdue_days`), standart qiymat ham
bitta (`notification_meta.DEFAULT_OVERDUE_DAYS`, sxemadan hosila).

⛔ CHEGARANING ARIFMETIKASI ESA IMPORT QILINADI:
   `app.jobs.reconciliation.overdue_cutoff()`. Eski qaror («import emas,
   juft») aynan shu nuqtada YOLG'ON da'vo tug'dirgan edi — ikki
   mexanizm bir formulani ikki joyda yozardi va ularga kelgan
   `business_date` MAHSULOTDA bir kunga farq qilardi. Ya'ni «AYNI knob»
   faqat testda rost edi. Bog'lanish endi ATAYIN: qoida bitta bo'lsa,
   uning ta'rifi ham bitta bo'lishi SHART.
=============================================================================

⛔ `COALESCE` BILAN, IKKI SO'ROV BILAN EMAS: «avval qator bormi deb qara,
   keyin o'qi» shakli ikki borish talab qilardi va oradagi oynada sozlama
   o'zgarsa job ESKI qiymat bilan ishlardi.
"""


@dataclass(slots=True)
class DigestResult:
    """Bitta dayjest yugurishining O'LCHANADIGAN natijasi.

    ⛔ NOL — NATIJA, uning yo'qligi emas (`BillingCloseResult` qoidasi):
    HAMMA maydon HAR DOIM qaytariladi.
    """

    markets: int = 0
    """Ko'rib chiqilgan FAOL bozorlar soni — xato bergani ham SHU SONDA."""
    enqueued: int = 0
    """Navbatga YANGI yozilgan xabarlar soni."""
    skipped_existing: int = 0
    """Xabar ALLAQACHON navbatda edi — IDEMPOTENTLIKNING o'lchovi, xato emas."""
    charges: int = 0
    """⛔ MANBANING O'Z-O'ZINI TEKSHIRUVI (fayl docstringining 4-bandi).

    Ertalabki dayjestda bu son `daily_charges` da o'sha kun uchun nechta
    qator borligini aytadi. NOL bo'lsa `billing_close` hali yugurmagan —
    va bu holat `system_heartbeats.detail` da KO'RINADI, ya'ni «hisob
    yo'q» bilan «dayjest yugurmagan» bir xil ko'rinmaydi.

    ⚠ Kechki dayjestda u HAR DOIM `0` va bu D-15 ning O'ZI: kechqurun
      bugungi kun `daily_charges` da hali yo'q.
    """
    errors: list[str] = field(default_factory=list)
    """⛔ XATO MATNI EMAS, TURI (`_swallow()` docstringi)."""


@dataclass(slots=True)
class ReminderResult:
    """BOT-03 yugurishining natijasi."""

    markets: int = 0
    vendors: int = 0
    """Chegaradan o'tgan qarzdor sotuvchilar soni."""
    enqueued: int = 0
    skipped_existing: int = 0
    """⛔ Sotuvchi BUGUN allaqachon eslatma olgan — D-22 ning o'lchovi."""
    errors: list[str] = field(default_factory=list)


async def digest_morning(
    sessionmaker: async_sessionmaker[AsyncSession], *, business_date: date
) -> DigestResult:
    """⛔ «KECHA YOZILGAN» dayjesti — YOZILGAN HISOBDAN o'qiydi (D-16).

    =======================================================================
    ⛔⛔ MANBA `daily_charges` + `payments`, PROYEKSIYA EMAS.

    Bu xabar «kecha nima YOZILDI?» degan savolga javob beradi va uning
    soni kechki xabarникidan FARQ QILADI — bu nuqson emas, DIZAYN
    (fayl docstringining 2-bandi). Proyeksiyadan o'qish ikki xabarni
    bir xil raqamga aylantirardi va direktor «nega ikki marta bir xil
    xabar?» deb ikkalasini ham o'qimay qo'yardi.
    =======================================================================

    ⛔ TOP-10 QARZDORNING ISMI XABARGA TUSHMAYDI (D-01/D-05):
       `digest_repo.top_debtors()` faqat SON qaytaradi va ro'yxatning
       O'ZI direktorga veb yuzasida, autentifikatsiya ostida ko'rinadi.

    Args:
        business_date: qaysi kunning YOZILGAN hisobi (`Asia/Tashkent`).
            ⛔ ARGUMENT — qobiq (07-14) unga KECHAGI kunni beradi.

    Returns:
        `DigestResult` — sonlar va YUTILGAN xatolarning TURLARI.
    """
    result = DigestResult()
    request_id = f"job-digest-morning-{business_date.isoformat()}"

    market_ids = await _active_markets(sessionmaker, event="digest_morning")
    if market_ids is None:
        return result
    result.markets = len(market_ids)

    for market_id in market_ids:
        try:
            await _morning_market(
                sessionmaker,
                market_id=market_id,
                request_id=request_id,
                business_date=business_date,
                result=result,
            )
        except Exception as exc:  # noqa: BLE001 - bir bozor qolganlarini to'xtatmaydi
            _swallow(result.errors, "digest_morning_failed", exc, market_id=market_id)

    await _write_heartbeat(
        sessionmaker,
        component=DIGEST_MORNING_COMPONENT,
        detail={
            "markets": result.markets,
            "enqueued": result.enqueued,
            "skipped_existing": result.skipped_existing,
            "charges": result.charges,
            "errors": len(result.errors),
        },
    )
    log.info(
        "digest_morning_done",
        business_date=business_date.isoformat(),
        markets=result.markets,
        enqueued=result.enqueued,
        skipped_existing=result.skipped_existing,
        errors=len(result.errors),
    )
    return result


async def digest_evening(
    sessionmaker: async_sessionmaker[AsyncSession], *, as_of: date
) -> DigestResult:
    """⛔ «BUGUN KUTILAYOTGAN» dayjesti — PROYEKSIYADAN o'qiydi (D-15).

    =======================================================================
    ⛔⛔ `billing_repo.pending_projection()` CHAQIRILADI — IKKINCHI
        IMPLEMENTATSIYA YOZILMAYDI.

    Kassirning ekrani ham AYNI funksiyani chaqiradi. Bu yerda yangi
    proyeksiya SQL'i paydo bo'lsa, kechki xabar bilan kassir ekrani
    ajralib ketardi va IKKALASI HAM «to'g'ri» ko'rinardi — bu loyihada
    takroran topilgan «ikki haqiqat manbai» sinfi. Tenglik testda
    ⛔ `==` bilan o'lchanadi, «yaqin» bilan emas.
    =======================================================================

    ⛔ `as_of` — BUGUNGI KUN. Kechagi kun berilganda xabar ertalabki
       dayjest bilan bir xil raqamni qaytarardi (fayl docstringining
       3-bandi).

    ⚠ `unpaid_stall_count` IKKI MANBANING FARQI: proyeksiyaning
      «bugun patta kutilayotgan rasta» soni MINUS bugun to'lov YOZILGAN
      rastalar soni. Ya'ni u «qaysi rastadan patta HALI yig'ilmagan?»
      degan mahsulotning asosiy savoliga javob beradi. ⚠ Ochiq narxi:
      faqat ESKI QARZINI to'lagan sotuvchi ham «yig'ilgan» tomonga
      tushadi — kassir o'sha rastaga BORGAN, ya'ni sanoq «kassir
      yetmagan rasta» ni o'lchaydi.

    Args:
        as_of: BUGUNGI biznes-kun (`Asia/Tashkent`) — ⛔ ARGUMENT.

    Returns:
        `DigestResult` — `charges` maydoni bu yerda HAR DOIM `0` (D-15).
    """
    result = DigestResult()
    request_id = f"job-digest-evening-{as_of.isoformat()}"

    market_ids = await _active_markets(sessionmaker, event="digest_evening")
    if market_ids is None:
        return result
    result.markets = len(market_ids)

    for market_id in market_ids:
        try:
            await _evening_market(
                sessionmaker,
                market_id=market_id,
                request_id=request_id,
                as_of=as_of,
                result=result,
            )
        except Exception as exc:  # noqa: BLE001 - bir bozor qolganlarini to'xtatmaydi
            _swallow(result.errors, "digest_evening_failed", exc, market_id=market_id)

    await _write_heartbeat(
        sessionmaker,
        component=DIGEST_EVENING_COMPONENT,
        detail={
            "markets": result.markets,
            "enqueued": result.enqueued,
            "skipped_existing": result.skipped_existing,
            "charges": result.charges,
            "errors": len(result.errors),
        },
    )
    log.info(
        "digest_evening_done",
        as_of=as_of.isoformat(),
        markets=result.markets,
        enqueued=result.enqueued,
        skipped_existing=result.skipped_existing,
        errors=len(result.errors),
    )
    return result


async def overdue_reminder(
    sessionmaker: async_sessionmaker[AsyncSession], *, business_date: date
) -> ReminderResult:
    """BOT-03 — kechikkan qarz uchun sotuvchiga eslatma NIYATI.

    =======================================================================
    ⛔⛔ SOTUVCHI KUNIGA ENG KO'PI BILAN BITTA ESLATMA OLADI.

    `dedupe_key` da KUN bor (`overdue:<vendor>:<kun>`), ya'ni job qayta
    yugurganda ikkinchi qator YOZILMAYDI. Sabab `alerting.py` ning D-22
    bandida o'lchangan: «75 ta xabar olgan admin bildirishnomani
    o'chiradi» — o'chirilgan bildirishnoma esa BUTUN kanalni yo'q
    qiladi, ya'ni himoya o'zi himoya qilayotgan narsani buzardi.
    =======================================================================

    ⛔ ESLATMA QUIET HOURS GA BO'YSUNADI — D-18 NING TESKARISI, VA BU
       YERDA HECH QANDAY QO'SHIMCHA KOD YO'Q.

    `never_suppressed` bayrog'i `NOTIFICATION_META` da `False` va
    darvozaning O'ZI `outbox_repo.claim()` ning SQL bandida. Ya'ni bu
    funksiya quiet hours haqida HECH NIMA bilmaydi va bilishi ham
    KERAK EMAS: bilsa, qoidaning ikkinchi ifodasi tug'ilardi. Bu izoh
    aynan shuning uchun yozilgan — keyingi ijrochi bu yerda «unutilgan»
    tekshiruv izlamasin.

    ⛔ CHEGARA `recon.open` BILAN AYNI KNOB (`_MARKET_OVERDUE_DAYS`).

    Args:
        business_date: eslatma QAYSI KUN uchun yozilyapti — kechikish
            chegarasi SHU kundan orqaga hisoblanadi va `dedupe_key` ga
            ham SHU kun tushadi.

    Returns:
        `ReminderResult`.
    """
    result = ReminderResult()
    request_id = f"job-overdue-{business_date.isoformat()}"

    market_ids = await _active_markets(sessionmaker, event="overdue_reminder")
    if market_ids is None:
        return result
    result.markets = len(market_ids)

    for market_id in market_ids:
        try:
            await _overdue_market(
                sessionmaker,
                market_id=market_id,
                request_id=request_id,
                business_date=business_date,
                result=result,
            )
        except Exception as exc:  # noqa: BLE001 - bir bozor qolganlarini to'xtatmaydi
            _swallow(result.errors, "overdue_reminder_failed", exc, market_id=market_id)

    await _write_heartbeat(
        sessionmaker,
        component=OVERDUE_COMPONENT,
        detail={
            "markets": result.markets,
            "vendors": result.vendors,
            "enqueued": result.enqueued,
            "skipped_existing": result.skipped_existing,
            "errors": len(result.errors),
        },
    )
    log.info(
        "overdue_reminder_done",
        business_date=business_date.isoformat(),
        markets=result.markets,
        vendors=result.vendors,
        enqueued=result.enqueued,
        errors=len(result.errors),
    )
    return result


# ===========================================================================
# BIR BOZORNING BIR KUNI — o'qish VA yozish BIR TRANZAKSIYADA
# ===========================================================================


async def _morning_market(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    business_date: date,
    result: DigestResult,
) -> None:
    """Ertalabki dayjestning bitta bozori.

    ⚠ SANOQLAR TRANZAKSIYA YOPILGANDAN KEYIN QO'SHILADI (`_open_market()`
      da o'rnatilgan qoida): blok ichida qo'shilsa `COMMIT` yiqilgan
      holatda hisoblagich YOZILMAGAN xabarni sanardi va o'sha son yurak
      urishiga tushardi.
    """
    async with _tenant_session(sessionmaker, market_id=market_id, request_id=request_id) as session:
        ledger = await digest_repo.ledger_day(
            session, market_id=market_id, business_date=business_date
        )
        occupancy = await digest_repo.occupancy_percent(
            session, market_id=market_id, business_date=business_date
        )
        # ⛔ `as_of = business_date + 1 kun` — `vendor_outstanding()`
        #   hisoblarni `service_date < as_of` bilan KESADI. `as_of =
        #   business_date` berilganda AYNAN o'sha kunning hisobi qarzga
        #   kirmasdi va dayjest qarzdorlarni KAM ko'rsatardi — ya'ni
        #   xabar tinchlantiruvchi yolg'on aytardi.
        debtors = await digest_repo.top_debtors(
            session, market_id=market_id, as_of=_next_day(business_date)
        )
        cases = await list_cases(session, market_id=market_id, day=business_date)

        payload = outbox_payload(
            OutboxKind.DIGEST_MORNING.value,
            business_date=business_date.isoformat(),
            charged_soum=ledger.charged_soum,
            collected_soum=ledger.collected_soum,
            # ⛔ `None` PAYLOADGA UMUMAN TUSHMAYDI (`outbox_payload()`
            #   qoidasi): rastasiz kunda «bandlik 0 %» YOLG'ON bo'lardi.
            occupancy_pct=occupancy,
            top_debtor_count=debtors.count,
            case_new_count=cases.new_count,
        )
        written = await outbox_repo.enqueue(
            session,
            market_id=market_id,
            kind=OutboxKind.DIGEST_MORNING.value,
            recipient_kind=_DIRECTOR,
            vendor_id=None,
            dedupe_key=f"digest_morning:{business_date.isoformat()}",
            payload=payload,
        )

    result.charges += ledger.charge_count
    _count_enqueue(result, written=written is not None)


async def _evening_market(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    as_of: date,
    result: DigestResult,
) -> None:
    """Kechki dayjestning bitta bozori — proyeksiya VA yozilgan to'lovlar."""
    async with _tenant_session(sessionmaker, market_id=market_id, request_id=request_id) as session:
        # ⛔ YAGONA IMPLEMENTATSIYA CHAQIRILADI (funksiya docstringi).
        projection = await pending_projection(session, market_id=market_id, as_of=as_of)
        market = projection.market
        if market is None:  # pragma: no cover - `stall_code=None` da to'ldiriladi
            raise RuntimeError(
                "`pending_projection(stall_code=None)` bozor kesimini qaytarmadi. "
                "Kontrakt o'zgargan bo'lsa kechki dayjest jimgina bo'sh xabar "
                "yozardi — shuning uchun bu shox YIQILADI, nolga tushmaydi."
            )

        ledger = await digest_repo.ledger_day(session, market_id=market_id, business_date=as_of)
        # ===================================================================
        # ⛔⛔ KECHAGI KUN, BUGUNGISI EMAS — VA BU STRUKTURAVIY NOLNI YOPADI
        #    (07-21, WR-10 ning jufti WR-02).
        #
        # `list_cases(day=...)` `reconciliation_cases.service_date = :day`
        # bo'yicha filtrlaydi. Bugungi `service_date` li case esa faqat
        # ERTAGA 04:25 da (`RECON_OPEN_CRON`) tug'iladi — ya'ni 20:45 dagi
        # so'rov har kuni, ISTISNOSIZ `0` qaytarardi. O'lchanmagan holat
        # o'lchangan nol bo'lib chiqardi va direktor «bugun nomuvofiqlik
        # yo'q» degan YOLG'ON xulosani ko'rardi.
        #
        # Kecha esa `recon.open` ALLAQACHON yugurgan kun, ya'ni son YOZILGAN
        # guruhga tegishli. §12.2 ning sifatlovchi kontrakti BUZILMAYDI:
        # `expected_soum` (proyeksiya) va `unpaid_stall_count` hamon
        # BUGUNGI kutilayotgan holatni aytadi — yorliq esa bu sonning
        # KECHAGI kunga tegishli ekanini matnda OCHIQ aytadi
        # (`outbox.py::_EVENING_TEXT["prev_anomalies"]`).
        # ===================================================================
        cases = await list_cases(session, market_id=market_id, day=as_of - timedelta(days=1))

        payload = outbox_payload(
            OutboxKind.DIGEST_EVENING.value,
            business_date=as_of.isoformat(),
            expected_soum=market.pending_amount_soum,
            collected_soum=ledger.collected_soum,
            # ⛔ `unpaid_stall_count` PROYEKSIYADAN (D-15) VA U TEGILMADI:
            #   kechki xabarning ASOSIY nomuvofiqlik raqami shu bo'lib
            #   qoladi, `prev_day_case_count` esa uning yonidagi TARIXIY
            #   kontekst.
            unpaid_stall_count=max(0, market.pending_stall_count - ledger.paid_stall_count),
            prev_day_case_count=(
                cases.new_count
                + cases.in_review_count
                + cases.justified_count
                + cases.unjustified_count
            ),
        )
        written = await outbox_repo.enqueue(
            session,
            market_id=market_id,
            kind=OutboxKind.DIGEST_EVENING.value,
            recipient_kind=_DIRECTOR,
            vendor_id=None,
            dedupe_key=f"digest_evening:{as_of.isoformat()}",
            payload=payload,
        )

    result.charges += ledger.charge_count
    _count_enqueue(result, written=written is not None)


async def _overdue_market(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    business_date: date,
    result: ReminderResult,
) -> None:
    """Bitta bozorning kechikkan qarzdorlari — sozlama VA yozuv bir tranzaksiyada."""
    async with _tenant_session(sessionmaker, market_id=market_id, request_id=request_id) as session:
        overdue_days = await _overdue_days(session, market_id=market_id)
        vendors = await digest_repo.overdue_vendors(
            session,
            market_id=market_id,
            # ⛔ CHEGARA SHU YERDA HISOBLANADI, REPO ICHIDA EMAS (WR-06):
            #   `overdue_cutoff()` — qoidaning YAGONA ta'rifi va
            #   `recon.open` ham AYNAN shu funksiyani chaqiradi.
            cutoff=overdue_cutoff(business_date, overdue_days),
        )

        written = 0
        skipped = 0
        for vendor in vendors:
            payload = outbox_payload(
                OutboxKind.OVERDUE_REMINDER.value,
                outstanding_soum=vendor.outstanding_soum,
                overdue_days=overdue_days,
                oldest_service_date=vendor.oldest_service_date.isoformat(),
            )
            row_id = await outbox_repo.enqueue(
                session,
                market_id=market_id,
                kind=OutboxKind.OVERDUE_REMINDER.value,
                recipient_kind=_VENDOR,
                vendor_id=vendor.vendor_id,
                # ⛔ KUN KALITDA — sotuvchi kuniga BITTA eslatma oladi.
                dedupe_key=f"overdue:{vendor.vendor_id}:{business_date.isoformat()}",
                payload=payload,
            )
            if row_id is None:
                skipped += 1
            else:
                written += 1

    result.vendors += len(vendors)
    result.enqueued += written
    result.skipped_existing += skipped


async def _overdue_days(session: AsyncSession, *, market_id: UUID) -> int:
    """Bozorning kechikish chegarasi — `_MARKET_OVERDUE_DAYS` ning qobig'i."""
    row = await session.execute(
        _MARKET_OVERDUE_DAYS, {"market_id": market_id, "fallback": DEFAULT_OVERDUE_DAYS}
    )
    return int(row.scalar_one())


def _next_day(day: date) -> date:
    """`day + 1` — `vendor_outstanding(as_of=...)` ning YARIM OCHIQ chegarasi.

    Alohida funksiya ATAYIN: chaqiruv joyida yozilgan `timedelta(days=1)`
    o'qiyotgan odamga «nega bir kun qo'shildi?» degan savolni qoldirardi
    va javob faqat `_VENDOR_OUTSTANDING` ning docstringida bo'lardi.
    """
    return day + timedelta(days=1)


def _count_enqueue(result: DigestResult, *, written: bool) -> None:
    """`enqueue()` ning `None` javobi — XATO EMAS, IDEMPOTENTLIK (D-21)."""
    if written:
        result.enqueued += 1
    else:
        result.skipped_existing += 1


# ===========================================================================
# UMUMIY QISM — `alerting.py` / `reconciliation.py` naqshining takrori
# ===========================================================================


async def _active_markets(
    sessionmaker: async_sessionmaker[AsyncSession], *, event: str
) -> list[UUID] | None:
    """Faol bozorlar — ⛔ D-15: YAGONA chetlab o'tuvchi yuza IMPORT QILINADI.

    `active_market_ids()` RLS'ni chetlab o'tadi, ya'ni u xavfsizlik YUZASI
    va yuzaning AYNAN BITTA chaqiruv nuqtasi bo'lishi kerak. Ikkinchi
    nusxa yozilganda yuzani toraytirish BIR nusxada bajarilardi va
    ikkinchisi jimgina eskirardi (T-06-37).

    Returns:
        Bozorlar ro'yxati, yoki `None` — yugurish BOSHLANA olmadi.
    """
    try:
        return await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        # Iz jurnalda qoladi; joblar KONVERGENT — o'sha kunni qayta
        # yugurtirish mumkin va `dedupe_key` takroriylikni ushlaydi.
        log.exception(f"{event}_market_list_failed")
        return None


@asynccontextmanager
async def _tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """`reconciliation.py::_tenant_session()` ning shu moduldagi JUFTI.

    ⚠ NUSXA EMAS, JUFT (`retention.py` da o'rnatilgan qoida): import
      yo'nalishi ikki mustaqil jobni bir-biriga bog'lardi va biri
      o'zgarganda ikkinchisi jimgina o'zgarardi.

    ⛔ `actor_kind = SYSTEM` va `actor_id = None`: `notification_outbox`
       append-only qo'riqchi ostida va DB-triggeri AYNAN shu GUC'lardan
       o'qiydi. Kontekstsiz yozuv EGASIZ qolardi, holbuki «xabar qachon
       va nima sababdan navbatga tushdi?» savoli nizoda (D-02) dalil
       bo'ladi.
    """
    # SIM117 — ichki blok TRANZAKSIYA chegarasi (`billing_close.py` naqshi).
    async with sessionmaker() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=None,
                request_id=request_id,
                actor_kind=ActorKind.SYSTEM,
            )
            yield session


def _swallow(errors: list[str], event: str, exc: Exception, *, market_id: UUID) -> None:
    """Xatoni YUTADI va uni SANOQQA aylantiradi — MATNINI EMAS, TURINI.

    `alerting.py::_swallow()` ning aynan shakli va aynan sababi: istisno
    matni ombor manzilini, sotuvchining telefonini yoki bot tokenini
    tashishi mumkin (04-06 va T-04-59 ning o'lchovlari). Turi esa
    ma'muriyatga «nima sinfdagi nosozlik?» degan javobni beradi va hech
    qanday shaxsiy ma'lumot tashimaydi.

    ⛔ `SQLAlchemyError` EMAS, `Exception`: repo qatlami buzilgan
       ma'lumotda `ValueError` beradi (masalan hisobdan katta kamaytirish
       -> manfiy qoldiq) va o'sha istisno BAZA xatosi emas. Torroq blok
       bilan bitta bozorning nuqsoni butun navbatni bo'sh qoldirardi.
    """
    name = type(exc).__name__
    errors.append(f"{event}:{name}")
    log.warning(event, market_id=str(market_id), error=name)


async def _write_heartbeat(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    component: str,
    detail: dict[str, Any],
) -> None:
    """`system_heartbeats[component]` — ALOHIDA, QISQA tranzaksiya.

    ⚠ `except Exception` — `SQLAlchemyError` EMAS. Sabab 04-07 da
      o'lchangan: yangi ulanish ochilganda `socket.gaierror`
      `SQLAlchemyError` ga O'RALMAYDI va butun jobni ENG OXIRIDA
      yiqitardi.

    ⚠ TENANT KONTEKSTI YO'Q: `system_heartbeats` — GLOBAL jadval, ya'ni
      `detail` ga FAQAT SANOQLAR yoziladi. `market_id`, sotuvchi yoki
      rasta kodi bu yerga tushsa u hamma uchun ko'rinadigan joyda
      qolardi.

    ⚠ YURAK URISHI XATOLAR BO'LGANDA HAM YOZILADI: job ISHLADI — faqat
      ba'zi bozorlar chetda qoldi va bu `detail.errors` da KO'RINADI.
      Yugurishning YO'QLIGI va QISMAN muvaffaqiyati ikki BOSHQA savol.
    """
    try:
        async with sessionmaker() as session, session.begin():
            statement = pg_insert(SystemHeartbeat).values(component=component, detail=detail)
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[SystemHeartbeat.component],
                    set_={"last_seen_at": func.now(), "detail": statement.excluded.detail},
                )
            )
    except Exception as exc:  # noqa: BLE001 - yurak urishi jobni yiqita olmaydi
        log.warning("notify_heartbeat_not_written", component=component, error=type(exc).__name__)
