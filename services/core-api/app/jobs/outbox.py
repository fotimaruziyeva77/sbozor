"""Chiquvchi xabar navbatini HAYDAYDIGAN tik (BOT-04, D-20…D-23, DQ-3).

=============================================================================
⛔⛔ 1-TAQIQ — BU MODUL FAQAT MATN YUBORADI.

Rasm, hujjat, media guruh va fayl biriktiruvchi Bot API metodlari bu yerda
ISHLATILMAYDI. Sabab `alerts.py` ning 1-taqig'ida to'liq yozilgan va u
huquqiy: dalil-kadr shaxsiy ma'lumot, Telegram serverlari esa O'zR
data-rezidentlik chegarasidan TASHQARIDA — bir marta yuborilgan baytni
qaytarib bo'lmaydi.

⚠ TAQIQLANGAN METOD NOMLARI BU YERDA LITERAL YOZILMAYDI (03-07 ning
  o'lchangan darsi, 07-02 uni `models/notification.py` da qaytadan to'lagan):
  sodda matn darvozasi IZOHNI KODDAN ajratmaydi, ya'ni taqiqni tushuntirish
  uchun yozilgan nom darvozani O'Z-O'ZIGA QARSHI qo'yardi. Taqiq shuning
  uchun TA'RIFLANADI, sanab chiqilmaydi; sanoq esa
  `tests/unit/test_outbox_surface.py` da, mahsulotdan MUSTAQIL literal
  ro'yxat bilan turadi.

⚠ DALIL MATNGA BAYT bo'lib EMAS, HAVOLA bo'lib boradi va havola
  AUTENTIFIKATSIYA ostidagi VEB SAHIFAGA ishora qiladi — tasvir uzatuvchi
  yo'lga emas. Ya'ni matnda ko'pi bilan `/reconciliation?day=...` shaklidagi
  sahifa manzili bo'ladi (D-03).
=============================================================================

=============================================================================
⛔⛔ 2-TAQIQ — ISTISNONING MATNI HECH QAYERGA YOZILMAYDI.

Telegram Bot API ning URL'i BOT TOKENINI tashiydi (`alerts.py` ning
2-taqig'i), ya'ni `httpx` istisnosining matni to'liq URL'ni o'z ichiga
oladi. Bitta `f"... {istisno}"` interpolyatsiyasi sirni jurnalga, jurnaldan
Sentry'ga va `last_error_type` USTUNIGA — u yerdan esa `pg_dump` -> restic
-> TASHQI BUCKET zanjiriga olib chiqardi. Bu 3-fazada `go2rtc.py` da
HAQIQATAN sodir bo'lgan yo'lning aynan takrori, faqat boshqa protokolda.

Shuning uchun bu modul istisno obyektini UMUMAN KO'RMAYDI: jo'natuvchi
`bool` qaytaradi va uch faktni (status, xato TURI, `retry_after`) sirsiz
`SendFailure` ga yig'adi. Darvoza IKKI QATLAMLI va ikkalasi ham majburiy:
struktura (`tests/unit/test_outbox_secrets.py` — AST) va xulq
(`tests/integration/test_outbox.py::test_failure_log_carries_no_token`).
=============================================================================

=============================================================================
⛔ 3-TAQIQ — JO'NATUVCHI BLOKLAMAYDI (D-23).

Kuzatuv va xabar vositasi kuzatilayotgan tizimni YIQITA OLMASLIGI kerak.
Telegram sekinlashsa yoki butunlay yiqilsa, pul yozuvi va case yuritish
DAVOM ETADI: bu modul hech qanday HTTP xatosini yuqoriga chiqarmaydi va
bitta qatorning yiqilishi butun tikni to'xtatmaydi (`_swallow()`).
=============================================================================

=============================================================================
⛔ `delivered` NING MA'NOSI — KAM HAM, KO'P HAM EMAS (Pitfall 2).

Bot API `sendMessage` faqat `Message` obyektini qaytaradi: YETKAZILGANLIK
yoki O'QILGANLIK kvitansiyasi YO'Q. Shuning uchun `delivered` =
«Telegram 200 qaytardi va `message_id` berdi», ya'ni xabar CHATGA
JOYLANDI. Kod bundan ORTIQ hech nima da'vo qilmaydi va nizoda (D-02)
tizim isbotlab bo'lmaydigan gapga majburlanmaydi.
=============================================================================

⛔ CRON REGISTRATSIYASI BU MODULDA EMAS. Job funksiya sifatida yoziladi va
   testda TO'G'RIDAN-TO'G'RI chaqiriladi; `worker.py` dagi jadval 07-14
   ning ishi. Sabab: bitta reja bitta qaror — «qachon yuguradi» savoli
   barcha beshta jobning jadvali bilan BIRGA ko'rilishi kerak.

⛔ PUL BU MODULDA HISOBLANMAYDI: summa `payload` ning ichida KO'CHIRMA
   bo'lib keladi va faqat `format_soum()` bilan chiziladi. Bu faylda pul
   arifmetikasi, kasrli tip va yaxlitlash YO'Q.
"""

from __future__ import annotations

import asyncio
import html
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

import structlog
from sbozor_core.enums import ActorKind, Locale, OutboxKind
from sbozor_core.models.ops import SystemHeartbeat
from sbozor_core.money import format_soum
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.jobs.retention import active_market_ids
from app.repositories import outbox_repo
from app.services.alerts import last_message_id

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.outbox_repo import OutboxClaim
    from app.services.alerts import AlertSender, SendFailure

log = structlog.get_logger(__name__)

__all__ = [
    "GLOBAL_RATE_PER_SECOND",
    "MAX_ATTEMPTS",
    "OUTBOX_BATCH_SIZE",
    "OUTBOX_COMPONENT",
    "OUTBOX_LEASE_SECONDS",
    "PER_CHAT_INTERVAL_SECONDS",
    "UNRESOLVED_RETRY_SECONDS",
    "OutboxDisposition",
    "OutboxFailure",
    "OutboxTickResult",
    "UnresolvedRecipient",
    "outbox_tick",
]


OUTBOX_COMPONENT: Final[str] = "outbox_tick"
"""`system_heartbeats.component` — tikning O'Z yurak urishi.

⚠ SATR 07-14 DAGI `EXPECTED_COMPONENTS` VA `watched` YOZUVLARI BILAN AYNAN
  BIR XIL bo'lishi SHART. Ikki joyda qo'lda yozilgan nom jimgina ajralib
  ketardi: jadval jobni yugurtirardi, kuzatuv esa boshqa nomni kutib
  «yurak urishi yo'q» alertini MANGU ko'tarib turardi (`alerting.py` ning
  `BACKUP_COMPONENT` bandi bilan aynan bir sinf).
"""

MAX_ATTEMPTS: Final[int] = 5
"""Bitta xabar uchun urinishlar SONI — beshta va bu SON TANLANMAGAN, HISOBLANGAN.

⚠ ARIFMETIKA (DQ-3 formulasi bilan): 30 s + 2 daq + 8 daq + 32 daq = jami
  ~42 daqiqa, ya'ni oxirgi urinish birinchisidan bir soatdan KAM vaqt
  keyin bo'ladi.

  Chegaraning ikki tomoni ham o'lchangan:
    * KAMROQ urinish — kvitansiya bir necha daqiqalik Telegram uzilishida
      butunlay yo'qolardi;
    * CHEKSIZ urinish — bloklangan yoki mangu yiqilgan qator navbatni
      TO'LDIRARDI va tikning har yugurishi o'sha qatorlarga sarflanardi.

  Bir soatdan ko'p kechikkan kvitansiya esa ALLAQACHON «zudlik» emas:
  sotuvchi bozordan ketgan bo'ladi va xabar nizoni oldini olish
  vositasidan shunchaki eslatmaga aylanadi. `alerts.py:155-166` dagi
  «2 urinish x 5 s» arifmetikasi bilan aynan bir xil uslub.
"""

_BACKOFF_BASE_SECONDS: Final[int] = 30
"""Backoff formulasining birinchi hadi (DQ-3)."""

_BACKOFF_FACTOR: Final[int] = 4
"""Backoff ko'paytmasi (DQ-3): `30s -> 2daq -> 8daq -> 32daq`."""

_BACKOFF_CAP_SECONDS: Final[int] = 3600
"""Backoff ning TEPA CHEGARASI — bir soat.

⚠ CHEGARA BOR: usiz 5-urinish 2 soatga surilardi va navbatdagi qator
  butun ish kunini o'tkazib yuborardi. `MAX_ATTEMPTS` ning ~42 daqiqalik
  arifmetikasi aynan shu qirqishga tayanadi.
"""

PER_CHAT_INTERVAL_SECONDS: Final[float] = 1.0
"""BIR CHATGA ketma-ket xabarlar orasidagi eng qisqa oraliq.

⚠ TELEGRAM NING RASMIY CHEGARASI: bitta chatga ~1 xabar/soniya. Undan
  tez yuborish `429` beradi, `429` esa butun navbatni sekinlashtiradi —
  ya'ni chegarani buzish TEZLIKNI OSHIRMAYDI, kamaytiradi.
"""

GLOBAL_RATE_PER_SECOND: Final[int] = 25
"""Umumiy tezlik — Telegram ning rasmiy ~30 msg/s idan PASTROQ va ATAYIN.

⚠ RASMIY CHEGARA STATISTIK, QAT'IY EMAS: unga TIRAB ishlash `429` ni
  muqarrar qiladi va o'sha `429` navbatga qaytish + backoff narxini
  keltiradi. 25 — chegaraning ~83 % i, ya'ni burchakdagi burstlar ham
  ichkarida qoladi (T-07-49).
"""

OUTBOX_TICK_BUDGET_SECONDS: Final[int] = 20
"""Bitta tikning JO'NATISHGA sarflaydigan vaqt byudjeti.

⚠ DAQIQALIK JADVALNING UCHDAN BIRI: tik keyingi tik boshlanishidan oldin
  tugashi SHART, aks holda ikki nusxa bir vaqtda yugurib navbatni
  bir-biriga taqardi (ijara va `SKIP LOCKED` bunday holatda ham to'g'ri
  ishlaydi, lekin qatorlar keraksiz qulflanardi).
"""

OUTBOX_BATCH_SIZE: Final[int] = GLOBAL_RATE_PER_SECOND * OUTBOX_TICK_BUDGET_SECONDS
"""Bir bozordan bir tikda olinadigan qatorlar soni — ⛔ HISOBLANGAN, tanlanmagan.

`25 msg/s x 20 s = 500`. Ya'ni partiya AYNAN vaqt byudjetiga teng: undan
katta partiya byudjetdan oshib ketardi (va qatorlar ijara ostida osilib
qolardi), kichigi esa uzilishdan keyin to'plangan navbatni keraksiz sekin
bo'shatardi.
"""

OUTBOX_LEASE_SECONDS: Final[int] = 120
"""Ijara muddati — tik byudjetidan KATTA, jadval oralig'idan ham katta.

⚠ SON `OUTBOX_TICK_BUDGET_SECONDS` DAN OSHIQ BO'LISHI SHART: partiyaning
  oxirgi qatori byudjet tugagan paytda yuboriladi, ya'ni ijarasi hali
  amal qilib turishi kerak. Aks holda o'sha qator boshqa tik tomonidan
  IKKINCHI MARTA olinardi va sotuvchi ikkita kvitansiya olardi.
"""

UNRESOLVED_RETRY_SECONDS: Final[int] = 900
"""Sotuvchi hali botga ULANMAGAN qatorning kechiktirilishi — 15 daqiqa.

⚠ BACKOFF FORMULASIDAN ALOHIDA VA SABAB SEMANTIK: bu Telegram nosozligi
  EMAS, ya'ni «tezroq qayta urinish» hech nimani tuzatmaydi. Kutilayotgan
  hodisa — SOTUVCHINING BOTGA ULANISHI va u daqiqalar emas, kunlar
  masshtabida bo'ladi. Har daqiqada qayta so'rash bazani bekorga
  urardi; 15 daqiqa esa ulanishdan keyin xabarni tez yetkazadi.
"""


class OutboxDisposition(StrEnum):
    """Bitta urinish natijasining MARSHRUTI — yopiq to'plam.

    ⛔ `other` YO'Q: noma'lum natija JIMGINA «qayta urinish» ga tushib
       ketardi va bloklangan foydalanuvchining xabari mangu aylanardi.
    """

    DELIVERED = "delivered"
    """Telegram 200 qaytardi. ⛔ «O'qildi» EMAS (modul docstringi)."""

    BLOCKED = "blocked"
    """`403` — foydalanuvchi botni bloklagan. ⛔ QAYTA URINILMAYDI (D-22)."""

    FAILED = "failed"
    """Qayta urinib bo'lmaydigan xato (`400`/`401`/`404`) yoki byudjet tugadi."""

    RETRY = "retry"
    """Vaqtinchalik nosozlik (`429`, `5xx`, tarmoq) — navbatga qaytadi."""

    UNRESOLVED = "unresolved"
    """Manzil YO'Q — urinish UMUMAN QILINMADI.

    ⛔ `blocked` DAN QAT'IY AJRATILGAN (`resolve_chat_id()` ning qoidasi):
       «foydalanuvchi bizni bloklagan» va «foydalanuvchi hali ulanmagan»
       ikki BOSHQA fakt va ularni aralashtirish direktorning «aloqa
       uzildi» ro'yxatini hali ulanmaganlar bilan to'ldirardi.
    """


class UnresolvedRecipient(LookupError):
    """Faol Telegram bog'lanishi topilmadi — ⛔ XATO EMAS, HOLAT.

    Sinf faqat `last_error_type` ustuniga yoziladigan SIRSIZ TUR NOMINI
    berish uchun mavjud: u KO'TARILMAYDI. Nomning o'zi ekranda «sotuvchi
    hali botga ulanmagan» degan sababni aniq beradi va u
    `outbox_repo._validate_error_type()` ning shakl talabiga
    (qisqa, probelsiz, URL'siz) to'liq mos keladi.
    """


@dataclass(frozen=True, slots=True)
class OutboxFailure:
    """Jo'natuvchining SIRSIZ natijasi + uning MARSHRUTI (`_classify()` chiqishi).

    ⛔ ISTISNO OBYEKTI HAM, UNING MATNI HAM BU YERDA YO'Q — modul
       docstringining 2-taqig'i. Uch fakt `SendFailure` dan KO'CHIRMA bo'lib
       keladi, to'rtinchisi (`disposition`) esa AYNAN status kodidan
       hisoblanadi.
    """

    error_type: str
    """⛔ AYNAN `type(exc).__name__` (jo'natuvchida yig'ilgan) yoki
    `UnresolvedRecipient.__name__`. Boshqa hech qanday shakl emas."""

    status_code: int | None
    retry_after: int | None
    disposition: OutboxDisposition


_UNRESOLVED_FAILURE: Final[OutboxFailure] = OutboxFailure(
    error_type=UnresolvedRecipient.__name__,
    status_code=None,
    retry_after=None,
    disposition=OutboxDisposition.UNRESOLVED,
)
"""«URINISH UMUMAN QILINMADI» — SOBIT, chunki unda o'zgaruvchi fakt YO'Q.

⚠ IKKI YO'L SHU YAGONA NATIJAGA KELADI va ikkalasi ham bir xil ma'noni
  beradi:

  1. `resolve_chat_id()` `None` qaytardi — sotuvchi hali botga ULANMAGAN;
  2. `send_message()` `False` qaytardi, lekin `last_failure` `None` —
     ya'ni jo'natuvchi O'CHIQ yoki manzil bo'sh va so'rov UMUMAN
     yuborilmagan (`alerts.py::last_failure` docstringi buni ATAYIN
     shunday qoldiradi).

⛔ IKKALASI HAM `blocked` EMAS: Telegram bilan hech qanday muammo yo'q va
   «aloqa uzildi» ro'yxatini hali ulanmaganlar bilan to'ldirish direktordan
   HAQIQIY bloklarni yashirardi (D-22).
"""

_MESSAGE_ID_UNKNOWN: Final[int] = 0
"""`provider_message_id` uchun sentinel — Telegram identifikatorlari 1 dan boshlanadi.

⚠ FAQAT BITTA SHOXDA: Telegram `200` qaytardi (ya'ni xabar CHATGA
  JOYLANDI), lekin javob tanasidan identifikator o'qilmadi. Bunday
  qatorni `retry` ga tushirish xabarni IKKINCHI MARTA yuborardi —
  yetkazilgan xabarni «yetkazilmadi» deb o'qish D-21 ning teskarisi.
  Nol qiymat esa haqiqiy identifikator bilan HECH QACHON aralashmaydi.
"""

_RECONCILIATION_PATH: Final[str] = "/reconciliation?day="
"""Kechki dayjestdagi DALIL HAVOLASI — ⛔ SAHIFA, tasvir emas (D-03).

⚠ MANZIL NISBIY VA ATAYIN: u autentifikatsiya ostidagi veb yuzaga ishora
  qiladi, ya'ni dalilni ko'rish uchun direktor tizimga KIRISHI kerak.
  Kadr bayti Telegram'ga hech qachon chiqmaydi va obyekt kaliti ham
  matnga tushmaydi.
"""

_LOCALE: Final[str] = Locale.UZ_LATN.value
"""Matn tili — hozircha BITTA va bu ochiq yozilgan CHEGARA.

⚠ `vendors` da til ustuni YO'Q (2-faza sxemasi), ya'ni «sotuvchining tili»
  bugun BILINMAYDI. Uni bu yerda taxmin qilish (masalan bozor
  sozlamasidan) yolg'on aniqlik berardi. Funksiyalar `locale` ni ARGUMENT
  sifatida oladi — til ustuni qo'shilgan kun o'zgarish CHAQIRUV JOYIDA
  bo'ladi, matn quruvchisida emas.
"""


@dataclass(slots=True)
class OutboxTickResult:
    """Bitta tikning O'LCHANADIGAN natijasi.

    ⛔ NOL — NATIJA, uning yo'qligi emas (`SweepResult` bilan bir xil qoida).
    """

    markets: int = 0
    released: int = 0
    """Muddati o'tgan ijaradan qaytarilgan qatorlar."""
    claimed: int = 0
    delivered: int = 0
    blocked: int = 0
    failed: int = 0
    rescheduled: int = 0
    unresolved: int = 0
    """Manzili topilmagan qatorlar — urinish QILINMADI (`OutboxDisposition`)."""
    errors: list[str] = field(default_factory=list)


# ===========================================================================
# TASNIF — istisnoni EMAS, SIRSIZ FAKTNI o'qiydi
# ===========================================================================


def _classify(failure: SendFailure | None) -> OutboxFailure:
    """Jo'natuvchining sirsiz natijasini MARSHRUTGA aylantiradi (D-22, DQ-3).

    =========================================================================
    ⛔ KOD STATUS KODIGA QARAYDI, XATO MATNIGA EMAS.

    Telegram `403 Forbidden: bot was blocked by the user` matnini istalgan
    kuni o'zgartirishi mumkin (bu matn LOW-confidence manba), status kodi
    esa protokol kontrakti. Matn bo'yicha aniqlash bir kun JIMGINA ishlamay
    qolardi: bloklangan foydalanuvchi `retry` shoxiga tushib, byudjetini
    yeb, `failed` bo'lardi — ya'ni «aloqa uzildi» fakti direktorga
    KO'RINMASDI (T-07-52).
    =========================================================================

    Marshrutlar:
      * `403` -> `BLOCKED` — ⛔ QAYTA URINISH YO'Q. Bu MA'LUMOT, xato emas
        (D-22): blok o'z-o'zidan tuzalmaydi va har urinish chegarani
        qattiqroq urardi.
      * `400` / `401` / `404` -> `FAILED` — konfiguratsiya nosozligi
        (noto'g'ri token, o'chirilgan chat, buzuq matn). Qayta urinish uni
        TUZATMAYDI.
      * `429` -> `RETRY` va `retry_after` ⛔ FORMULADAN USTUN.
      * `5xx` va boshqa statuslar -> `RETRY` — Telegram tomonidagi
        vaqtinchalik nosozlik.
      * status YO'Q (tarmoq/timeout) -> `RETRY`.

    Args:
        failure: `AlertSender.last_failure` ning qiymati. `None` — so'rov
            UMUMAN yuborilmagan (jo'natuvchi o'chiq yoki manzil bo'sh).
    """
    if failure is None:
        return _UNRESOLVED_FAILURE

    status = failure.status
    if status == 403:
        disposition = OutboxDisposition.BLOCKED
    elif status in {400, 401, 404}:
        disposition = OutboxDisposition.FAILED
    else:
        disposition = OutboxDisposition.RETRY

    return OutboxFailure(
        error_type=failure.error_type,
        status_code=status,
        retry_after=failure.retry_after,
        disposition=disposition,
    )


def _next_attempt_at(attempt: int, *, now: datetime, retry_after: int | None) -> datetime:
    """Keyingi urinish payti — DQ-3 ning formulasi, `retry_after` ustunligi bilan.

    `next_attempt_at = now + min(30s * 4**(attempt-1), 1 soat)`

    | urinish | kutish |
    |---------|--------|
    | 1       | 30 s   |
    | 2       | 2 daq  |
    | 3       | 8 daq  |
    | 4       | 32 daq |
    | 5       | 1 soat (chegara bilan QIRQILGAN) |

    ⛔ `retry_after` FORMULADAN USTUN: Telegram `429` bilan ANIQ soniya
       qaytarganda o'sha qiymat ishlatiladi. Formulaga tayanish chegarani
       QATTIQROQ urardi — bu `alerts.py` ning «`429` ga retry qilish
       holatni yomonlashtiradi» qoidasining aynan takrori.

    Args:
        attempt: qatorning `attempt_count` i (⛔ `claim()` da allaqachon
            oshirilgan, ya'ni birinchi urinishda u `1`).
        now: tikning payti — ARGUMENT, `now()` EMAS (test soatni
            siljitmasdan o'lchaydi).
        retry_after: Telegram bergan soniya yoki `None`.
    """
    if retry_after is not None:
        return now + timedelta(seconds=retry_after)
    exponent = max(attempt - 1, 0)
    seconds = min(_BACKOFF_BASE_SECONDS * _BACKOFF_FACTOR**exponent, _BACKOFF_CAP_SECONDS)
    return now + timedelta(seconds=seconds)


# ===========================================================================
# MATN — QURILADI, qatordan O'QILMAYDI (Pitfall 6)
# ===========================================================================


def _text(value: object) -> str:
    """Matn qiymatini xabarga QO'YISHGA tayyorlaydi — ⛔ `html.escape()` MAJBURIY.

    =========================================================================
    ⛔ BU FUNKSIONAL VA XAVFSIZLIK BANDI, IKKALASI BIRGA (T-07-51).

    `alerts.py` `parse_mode="HTML"` ni tanlagan (Markdown bozor nomidagi
    `_` va `*` da butun xabarni rad etardi). Ya'ni sotuvchi yoki kassir
    ismida `<` belgisi bo'lsa Telegram butun xabarni PARSE XATOSI bilan
    rad etardi — va u aynan o'sha ismli odamning kvitansiyasida, mangu
    takrorlanardi. Escape bo'lmaganda esa ism ichidagi teg xabarning
    ko'rinishini o'zgartirishi mumkin edi.
    =========================================================================
    """
    return html.escape(str(value))


def _soum(payload: dict[str, Any], key: str, *, locale: str) -> str:
    """Pul kalitini chizadi — ⛔ `format_soum()` bilan, YANGI formatlash YO'Q (D-07).

    ⚠ QIYMAT YO'Q bo'lsa `-` qaytadi: `payload` allowlist bilan cheklangan,
      lekin kalitning MAVJUDLIGI majburiy emas (`outbox_payload()` `None`
      qiymatlarni tashlaydi). Matn quruvchisi shuning uchun «kalit bormi?»
      degan BITTA savol bilan ishlaydi.
    """
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        return "-"
    return _text(format_soum(value, locale))


def _plain(payload: dict[str, Any], key: str) -> str:
    """Matn/son kalitini escape bilan chizadi (`-` — kalit yo'q)."""
    value = payload.get(key)
    return "-" if value is None else _text(value)


def _build_text(kind: str, payload: dict[str, Any], *, locale: str) -> str:
    """Xabar matnini `kind` + `payload` DAN QURADI (Pitfall 6).

    =========================================================================
    ⛔ TAYYOR MATN QATORDA SAQLANMAYDI VA BU SAQLASH JOYINING TANLOVI EMAS.

    Tayyor matn sotuvchining ismini, rasta kodini va summani BAZAGA
    yozardi, u yerdan `pg_dump` -> restic -> TASHQI BUCKET zanjiriga
    chiqardi. Chegara shuning uchun YOZISH paytida (`outbox_payload()`
    allowlisti), matn esa faqat JO'NATISH paytida, xotirada quriladi.
    =========================================================================

    ⛔ MATNDA DALIL BAYTI YO'Q (D-03): tasvir manzili, obyekt kaliti va
       imzolangan havola bu funksiyadan CHIQMAYDI. Kechki dayjest ko'pi
       bilan AUTENTIFIKATSIYA ostidagi sahifaga nisbiy havola beradi.

    ⚠ HAR MATN QIYMATI `html.escape()` DAN O'TADI (`_text()` docstringi).

    Args:
        kind: `OutboxKind` a'zosining qiymati.
        payload: allowlist bilan cheklangan kalitlar (`NOTIFICATION_META`).
        locale: matn tili — ARGUMENT (`_LOCALE` docstringi).

    ⚠ `locale` SHU YERDA NORMALIZATSIYA QILINADI (`_normalize_locale()`):
      quyi funksiyalarning hammasi — yorliq jadvallari ham, `format_soum()`
      ham — YECHILGAN qiymatni oladi. Noma'lum `kind` esa aksincha,
      QATTIQ yiqiladi (pastdagi `Raises`): til KO'RINISH tanlovi, `kind`
      esa xabarning MAZMUNI.

    Raises:
        KeyError: `kind` noma'lum bo'lganda. ⛔ QATTIQ: enumga a'zo
            qo'shilib matn quruvchisi unutilgan bo'lsa, xabar BO'SH ketardi.
    """
    builder = _BUILDERS[kind]
    return builder(payload, _normalize_locale(locale))


def _receipt_text(payload: dict[str, Any], locale: str) -> str:
    """Kvitansiya (CASH-05) — «qancha, qaysi rastaga, kim qabul qildi» (D-02).

    ⚠ `cashier_name` ATAYIN MATNDA: nizoda sotuvchi «kimga to'ladim?»
      savoliga javob olishi kerak, aks holda kvitansiya dalil emas, faqat
      kvitansiya ko'rinishidagi son bo'lardi (`NOTIFICATION_META` ning
      o'sha bandi).
    """
    lines = [
        "<b>Patta qabul qilindi</b>",
        f"Summa: {_soum(payload, 'amount_soum', locale=locale)}",
        f"Rasta: {_plain(payload, 'stall_code')}",
        f"Vaqt: {_plain(payload, 'paid_at')}",
        f"Kassir: {_plain(payload, 'cashier_name')}",
    ]
    return "\n".join(lines)


def _overdue_text(payload: dict[str, Any], locale: str) -> str:
    """Qarz eslatmasi (BOT-03) — sonlar, tahdid emas."""
    lines = [
        "<b>Qarzdorlik eslatmasi</b>",
        f"Qoldiq: {_soum(payload, 'outstanding_soum', locale=locale)}",
        f"Kunlar: {_plain(payload, 'overdue_days')}",
        f"Eng eski kun: {_plain(payload, 'oldest_service_date')}",
    ]
    return "\n".join(lines)


QUALIFIER_EXPECTED: Final[str] = "expected"
QUALIFIER_RECORDED: Final[str] = "recorded"
QUALIFIER_VOCAB: Final[frozenset[str]] = frozenset({QUALIFIER_EXPECTED, QUALIFIER_RECORDED})
"""⛔ G-35 ning YOPIQ LUG'ATI (`07-UI-SPEC.md` §12.2/§12.3).

Ikki sifatlovchi, ikkitasi ham MAJBURIY va ular ⛔ ARALASHMASLIGI shart:
har xabarda AYNAN BITTASI bo'ladi.
"""

_QUALIFIER_WORDS: Final[dict[str, dict[str, str]]] = {
    Locale.UZ_LATN.value: {
        QUALIFIER_EXPECTED: "kutilayotgan",
        QUALIFIER_RECORDED: "yozilgan",
    },
    Locale.UZ_CYRL.value: {
        QUALIFIER_EXPECTED: "кутилаётган",
        QUALIFIER_RECORDED: "ёзилган",
    },
    Locale.RU.value: {
        QUALIFIER_EXPECTED: "ожидаемый",
        QUALIFIER_RECORDED: "записанный",
    },
}
"""⛔ `recon.qualifier.*` — `07-UI-SPEC.md` §12.2 jadvalining KOD tomoni.

=============================================================================
⛔⛔ SIFATLOVCHI RAQAM BILAN BIR JUMLADA TURADI, SARLAVHADA EMAS (§12.2).

    ✅  «Bugun KUTILAYOTGAN patta: 4 200 000 so'm»
    ⛔  «Kechki hisobot ⏎ Patta: 4 200 000 so'm»

Sabab MEXANIK, uslubiy emas: Telegram bildirishnomasining QISQARTIRILGAN
ko'rinishida sarlavha kesilib qoladi va foydalanuvchi FAQAT RAQAMNI
ko'radi. Sifatlovchisiz esa direktor kechqurun 4 200 000, ertalab
3 950 000 ko'radi, sababini TOPA OLMAYDI va uchinchi kuni ikkala xabarni
ham o'qimay qo'yadi (§12.1).
=============================================================================

⚠ TIL DASTGOHI FAQAT SHU IKKI DAYJESTGA QO'YILDI va bu CHEGARA OCHIQ:
  kvitansiya (CASH-05) va qarz eslatmasi (BOT-03) matnlari hamon BITTA
  tilda. Sabab — egalik: ularning uch tilli varianti 07-09 ning ochiq
  bandida (bot matnlari, BOT-01 doirasi) va u `vendors` dagi til
  ustuniga bog'liq. Bu yerda esa til ustuni KERAK EMAS: G-35 ning
  o'lchovi `locale` ni ARGUMENT sifatida beradi, ya'ni uchala variant
  ham BUGUN o'lchanadi (`tests/unit/test_digest_qualifiers.py`).
"""

_MORNING_TEXT: Final[dict[str, dict[str, str]]] = {
    Locale.UZ_LATN.value: {
        "header": "Ertalabki hisobot",
        "day": "Kun",
        "charged": "Kecha {qualifier} patta",
        "collected": "Yig'ildi",
        "occupancy": "Bandlik",
        "debtors": "Qarzdorlar",
        "cases": "Yangi nomuvofiqliklar",
    },
    Locale.UZ_CYRL.value: {
        "header": "Эрталабки ҳисобот",
        "day": "Кун",
        "charged": "Кеча {qualifier} патта",
        "collected": "Йиғилди",
        "occupancy": "Бандлик",
        "debtors": "Қарздорлар",
        "cases": "Янги номувофиқликлар",
    },
    Locale.RU.value: {
        "header": "Утренний отчёт",
        "day": "День",
        "charged": "{qualifier} вчера патта",
        "collected": "Собрано",
        "occupancy": "Занятость",
        "debtors": "Должники",
        "cases": "Новые расхождения",
    },
}
"""Ertalabki dayjestning yorliqlari — uchala locale.

⚠ ATAMALAR GLOSSARIYDAN (`ops/i18n/glossary.json`): `patta` / `патта` /
  `патт` o'zagi va `qarz` / `қарз` / `долг`. Taqiqlangan sinonimlar
  (`yig'im`, `йиғим`, `лавк`, `магазин`) bu yerda YO'Q.

⚠ «case» SO'ZI MATNGA CHIQMAYDI (`07-UI-SPEC.md` §8.5 bilan bir xil
  qoida): foydalanuvchiga ko'rinadigan atama — «nomuvofiqlik». `case`
  faqat KOD va API qiymati bo'lib qoladi.
"""

_EVENING_TEXT: Final[dict[str, dict[str, str]]] = {
    Locale.UZ_LATN.value: {
        "header": "Kechki holat",
        "day": "Kun",
        "expected": "Bugun {qualifier} patta",
        "collected": "Yig'ildi",
        "unpaid": "To'lovsiz rastalar",
        "anomalies": "Anomaliyalar",
        "details": "Batafsil",
    },
    Locale.UZ_CYRL.value: {
        "header": "Кечки ҳолат",
        "day": "Кун",
        "expected": "Бугун {qualifier} патта",
        "collected": "Йиғилди",
        "unpaid": "Тўловсиз расталар",
        "anomalies": "Аномалиялар",
        "details": "Батафсил",
    },
    Locale.RU.value: {
        "header": "Вечернее состояние",
        "day": "День",
        "expected": "{qualifier} сегодня патта",
        "collected": "Собрано",
        "unpaid": "Места без оплаты",
        "anomalies": "Аномалии",
        "details": "Подробнее",
    },
}
"""Kechki dayjestning yorliqlari — uchala locale (`_MORNING_TEXT` naqshi)."""

_SUPPORTED_LOCALES: Final[frozenset[str]] = frozenset(member.value for member in Locale)
"""Qo'llab-quvvatlanadigan tillar — ⛔ ENUMDAN HOSILA, qo'lda sanalmagan.

⚠ To'plam `sbozor_core.money` ning locale jadvali bilan AYNAN bir xil
  bo'lishi SHART va u shu sababdan ikkalasi ham `Locale` dan quriladi:
  pul formatlovchisi noma'lum tilda `ValueError` KO'TARADI, ya'ni yorliq
  jadvali kengroq bo'lsa matn baribir yiqilardi.
"""


def _normalize_locale(locale: str) -> str:
    """Noma'lum tilni standart tilga TUSHIRADI — xabarni yiqitmaydi.

    =========================================================================
    ⛔ NEGA `KeyError` EMAS — VA BU O'LCHANGAN, USLUBIY QAROR EMAS.

    `_deliver()` matn qurilmaganda qatorni ⛔ `failed` ga tushiradi va
    qayta urinmaydi. Ya'ni bitta noto'g'ri til qiymati (masalan `vendors`
    ga til ustuni qo'shilgan kun kelgan eski yoki buzuq qiymat)
    sotuvchining KVITANSIYASINI butunlay yo'qotardi — holbuki kvitansiya
    D-02 ning dalili.

    Til — KO'RINISH tanlovi, MA'LUMOT emas: standart tilda yetkazilgan
    xabar axborotning hech qismini yo'qotmaydi, yetkazilmagan xabar esa
    hammasini yo'qotadi.

    ⚠ NORMALIZATSIYA `_build_text()` DA, BITTA JOYDA. Quyi funksiyalarning
      har biri o'z fallbackini qilsa, `format_soum()` (u noma'lum tilda
      `ValueError` beradi) baribir yiqilardi va fallback YARIM bo'lardi —
      bu nosozlik ijro paytida HAQIQATAN ko'rildi.
    =========================================================================
    """
    return locale if locale in _SUPPORTED_LOCALES else _LOCALE


def _digest_morning_text(payload: dict[str, Any], locale: str) -> str:
    """Ertalabki dayjest — KECHAGI YOZILGAN kun (D-16).

    ⚠ MATN MANBANI OCHIQ AYTADI: ertalabki va kechki sonlar bir xil
      bo'lmasligi NUQSON EMAS, DIZAYN (D-15) va direktor buni matndan
      bilishi kerak — aks holda u ikki raqamni ko'rib tizimga ishonchini
      yo'qotardi.

    ⛔ SIFATLOVCHI (`recorded`) RAQAM BILAN BIR QATORDA (§12.2) va u
       xabarda YAKKA: `expected` bu matnga TUSHMASLIGI shart, aks holda
       aralashuv direktorni chalkashtirardi (G-35 to'plam tengligi).
    """
    label = _MORNING_TEXT[locale]
    charged = label["charged"].format(qualifier=_QUALIFIER_WORDS[locale][QUALIFIER_RECORDED])
    lines = [
        f"<b>{label['header']}</b>",
        f"{label['day']}: {_plain(payload, 'business_date')}",
        f"{charged}: {_soum(payload, 'charged_soum', locale=locale)}",
        f"{label['collected']}: {_soum(payload, 'collected_soum', locale=locale)}",
        f"{label['occupancy']}: {_plain(payload, 'occupancy_pct')}%",
        f"{label['debtors']}: {_plain(payload, 'top_debtor_count')}",
        f"{label['cases']}: {_plain(payload, 'case_new_count')}",
    ]
    return "\n".join(lines)


def _digest_evening_text(payload: dict[str, Any], locale: str) -> str:
    """Kechki dayjest — BUGUNGI KUTILAYOTGAN holat (D-15).

    ⛔ DALIL HAVOLA BO'LIB BORADI, BAYT BO'LIB EMAS (D-03): matnda
       autentifikatsiya ostidagi SAHIFA manzili turadi.

    ⛔ SIFATLOVCHI (`expected`) RAQAM BILAN BIR QATORDA (§12.2) va u
       xabarda YAKKA — `recorded` bu matnga TUSHMAYDI.
    """
    label = _EVENING_TEXT[locale]
    day = _plain(payload, "business_date")
    expected = label["expected"].format(qualifier=_QUALIFIER_WORDS[locale][QUALIFIER_EXPECTED])
    lines = [
        f"<b>{label['header']}</b>",
        f"{label['day']}: {day}",
        f"{expected}: {_soum(payload, 'expected_soum', locale=locale)}",
        f"{label['collected']}: {_soum(payload, 'collected_soum', locale=locale)}",
        f"{label['unpaid']}: {_plain(payload, 'unpaid_stall_count')}",
        f"{label['anomalies']}: {_plain(payload, 'anomaly_count')}",
        f"{label['details']}: {_RECONCILIATION_PATH}{day}",
    ]
    return "\n".join(lines)


_BUILDERS: Final[dict[str, Callable[[dict[str, Any], str], str]]] = {
    OutboxKind.PAYMENT_RECEIPT.value: _receipt_text,
    OutboxKind.OVERDUE_REMINDER.value: _overdue_text,
    OutboxKind.DIGEST_MORNING.value: _digest_morning_text,
    OutboxKind.DIGEST_EVENING.value: _digest_evening_text,
}
"""`kind` -> matn quruvchisi. ⛔ TO'PLAM YOPIQ va `NOTIFICATION_META` bilan
juftlashgan: enumga a'zo qo'shilib bu yerga yozuv yozilmasa `KeyError`
JO'NATISH paytida chiqadi va u testda ushlanadi (`test_outbox.py`)."""


# ===========================================================================
# THROTTLING — chegara HURMAT QILINADI, unga tirab ishlanmaydi
# ===========================================================================


@dataclass(slots=True)
class _Throttle:
    """Per-chat va umumiy tezlik chegaralarini ushlab turadigan PACER.

    =========================================================================
    ⛔ SOAT VA UYQU ARGUMENT — TESTDA HAQIQIY `sleep` KUTILMAYDI.

    Chegara sekundlar bilan o'lchanadi, ya'ni haqiqiy uyqu bilan yozilgan
    test bir necha DAQIQA yugurardi va birinchi kunidan `-m slow` ga
    surilardi — ya'ni amalda HECH QACHON yugurmasdi. Soat va uyquni
    argument qilish o'lchovni ARZON qiladi va aynan shu sababdan qoida
    O'LCHANADI, kelishuv bo'lib qolmaydi.
    =========================================================================
    """

    monotonic: Callable[[], float]
    sleep: Callable[[float], Awaitable[None]]
    per_chat_interval: float = PER_CHAT_INTERVAL_SECONDS
    global_interval: float = 1.0 / GLOBAL_RATE_PER_SECOND
    _chat_ready_at: dict[str, float] = field(default_factory=dict)
    _global_ready_at: float = 0.0

    async def wait(self, chat_key: str) -> None:
        """Chegaralar ruxsat bergunicha kutadi va navbatdagi paytni belgilaydi."""
        moment = self.monotonic()
        ready_at = max(self._global_ready_at, self._chat_ready_at.get(chat_key, 0.0))
        delay = ready_at - moment
        if delay > 0:
            await self.sleep(delay)
            moment = ready_at
        self._global_ready_at = moment + self.global_interval
        self._chat_ready_at[chat_key] = moment + self.per_chat_interval


# ===========================================================================
# TIK
# ===========================================================================


@asynccontextmanager
async def _tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """`alerting.py::_tenant_session()` ning shu moduldagi JUFTI, nusxasi emas.

    ⚠ TAKRORLASH ONGLI (`retention.py` da yozilgan qoida): import
      yo'nalishi `outbox -> alerting` bo'lardi va u ikki mustaqil jobni
      bir-biriga bog'lardi. Shakl bir xil, EGASI boshqa.
    """
    # SIM117 — ichki blok TRANZAKSIYA chegarasi (`alerting.py` bilan bir xil).
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


def _swallow(result: OutboxTickResult, event: str, exc: Exception, *, market_id: UUID) -> None:
    """Xatoni YUTADI va uni SANOQQA aylantiradi — MATNINI EMAS, TURINI.

    ⛔ 3-TAQIQNING BAJARILISH JOYI: bitta qatorning yiqilishi butun tikni
       to'xtatmaydi va hech qanday istisno yuqoriga chiqmaydi (D-23).

    ⛔ ISTISNO MATNI YOZILMAYDI (modul docstringining 2-taqig'i): u
       Telegram URL'ini, ya'ni bot tokenini tashishi mumkin.
    """
    result.errors.append(f"{event}:{type(exc).__name__}")
    log.warning(event, market_id=str(market_id), error_type=type(exc).__name__)


def _tick_detail(result: OutboxTickResult) -> dict[str, Any]:
    """Yurak urishining detali — ⛔ FAQAT SANOQLAR.

    ⚠ `chat_id`, sotuvchi ismi, telefon va xabar matni BU YERGA
      TUSHMAYDI: `system_heartbeats.detail` `jsonb` va u `pg_dump` ->
      restic -> TASHQI BUCKET zanjirida yashaydi (T-07-54 / D-01).
    """
    return {
        "markets": result.markets,
        "released": result.released,
        "claimed": result.claimed,
        "delivered": result.delivered,
        "blocked": result.blocked,
        "failed": result.failed,
        "rescheduled": result.rescheduled,
        "unresolved": result.unresolved,
        "errors": len(result.errors),
    }


async def _write_heartbeat(
    component: str,
    sessionmaker: async_sessionmaker[AsyncSession],
    detail: dict[str, Any],
) -> None:
    """`system_heartbeats[component]` — ALOHIDA, QISQA tranzaksiya.

    ⚠ `except Exception` — `SQLAlchemyError` EMAS (04-07 ning o'lchovi):
      yangi ulanish ochilganda `socket.gaierror` `SQLAlchemyError` ga
      O'RALMAYDI va butun tikni ENG OXIRIDA yiqitardi.
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
    except Exception as exc:  # noqa: BLE001 - yurak urishi tikni yiqita olmaydi
        log.warning("outbox_tick_heartbeat_not_written", error_type=type(exc).__name__)


async def outbox_tick(
    sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    *,
    now: datetime,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> OutboxTickResult:
    """Navbatni haydaydi: ijara -> matn -> jo'natish -> holat (BOT-04).

    =========================================================================
    ⛔ IJARA COMMIT QILINADI, JO'NATISH ESA TRANZAKSIYADAN TASHQARIDA.

    `claim()` alohida, QISQA tranzaksiyada bajariladi va COMMIT qilinadi —
    ya'ni `lease_until` va `attempt_count` HTTP so'rovidan OLDIN diskda
    bo'ladi. Aks holda tik yiqilganda tranzaksiya rollback bo'lardi,
    urinish sanoqqa tushmasdi va o'sha qator keyingi tikda QAYTA
    yuborilardi — sotuvchi ikkita kvitansiya olardi.

    Tashqi chaqiruvni tranzaksiya ICHIDA ushlab turish esa bundan ham
    yomon: ulanish Telegram javob bergunicha band bo'lib turardi va
    partiya butun poolni yeb qo'yardi.
    =========================================================================

    ⛔ HAR XATO YUTILADI (`_swallow()`): bitta bozorning yoki bitta
       qatorning nosozligi qolgan hammasini to'xtatmaydi (D-23).

    Args:
        sessionmaker: sessiya fabrikasi — ARGUMENT, modul globali emas.
        sender: Telegram jo'natuvchisi. ARGUMENT: testda `respx` bilan
            o'lchanadi, mahsulotda `TaskiqState` dan keladi.
        now: tikning payti. ⛔ ARGUMENT: quiet-hours darvozasi ham, backoff
            arifmetikasi ham aynan shu qiymatga qaraydi, ya'ni «22:30 da
            nima bo'ladi?» savoli soatni siljitmasdan o'lchanadi.
        monotonic: throttling soati — FAQAT test almashtiradi.
        sleep: throttling uyqusi — FAQAT test almashtiradi.
    """
    result = OutboxTickResult()
    throttle = _Throttle(monotonic=monotonic, sleep=sleep)
    request_id = f"job-outbox-{now.isoformat()}"

    try:
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        # ⚠ MARKET RO'YXATI YIQILSA TIK TUGAYDI, LEKIN ISTISNO CHIQMAYDI:
        #   yurak urishi baribir yoziladi va nol sanoqlar «tik yugurdi,
        #   hech nima qilmadi» degan FAKTNI beradi.
        log.exception("outbox_tick_market_list_failed")
        await _write_heartbeat(OUTBOX_COMPONENT, sessionmaker, _tick_detail(result))
        return result

    result.markets = len(market_ids)
    for market_id in market_ids:
        claims = await _claim_batch(
            sessionmaker, market_id=market_id, request_id=request_id, now=now, result=result
        )
        for claim in claims:
            await _deliver(
                sessionmaker,
                sender,
                throttle,
                market_id=market_id,
                request_id=request_id,
                claim=claim,
                now=now,
                result=result,
            )

    await _write_heartbeat(OUTBOX_COMPONENT, sessionmaker, _tick_detail(result))
    log.info("outbox_tick_done", **_tick_detail(result))
    return result


async def _claim_batch(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    now: datetime,
    result: OutboxTickResult,
) -> list[OutboxClaim]:
    """Muddati o'tgan ijarani qaytaradi va yangi partiyani IJARA bilan oladi.

    ⚠ IKKALASI BIR TRANZAKSIYADA: bo'shatilgan qator AYNAN SHU tikda qayta
      olinishi kerak, aks holda o'lgan worker qoldirgan xabar keyingi
      daqiqani kutardi.
    """
    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            released = await outbox_repo.release_expired_leases(
                session, market_id=market_id, now=now
            )
            claims = await outbox_repo.claim(
                session,
                market_id=market_id,
                batch_size=OUTBOX_BATCH_SIZE,
                lease_seconds=OUTBOX_LEASE_SECONDS,
                now=now,
            )
    except SQLAlchemyError as exc:
        _swallow(result, "outbox_claim_failed", exc, market_id=market_id)
        return []

    result.released += released
    result.claimed += len(claims)
    return claims


async def _deliver(
    sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    throttle: _Throttle,
    *,
    market_id: UUID,
    request_id: str,
    claim: OutboxClaim,
    now: datetime,
    result: OutboxTickResult,
) -> None:
    """Bitta qatorni yuboradi va natijasini yozadi — ⛔ ISTISNO CHIQARMAYDI.

    ⚠ MANZIL JO'NATISHDAN BEVOSITA OLDIN O'QILADI (D-26c): qayta ulanish
      eski bog'lanishni bekor qiladi va navbatda turgan xabar ESKI chatga
      ketmasligi kerak.
    """
    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            chat_id = await outbox_repo.resolve_chat_id(
                session,
                market_id=market_id,
                recipient_kind=claim.recipient_kind,
                vendor_id=claim.vendor_id,
            )
    except SQLAlchemyError as exc:
        _swallow(result, "outbox_chat_lookup_failed", exc, market_id=market_id)
        return

    if chat_id is None:
        # ⛔ `blocked` EMAS: sotuvchi hali botga ULANMAGAN va bu QONUNIY
        #   holat (`resolve_chat_id()` docstringi). Urinish UMUMAN
        #   qilinmadi — HTTP so'rovi yo'q — shuning uchun byudjet
        #   tekshiruvi ham qo'llanmaydi (pastdagi `_settle`).
        await _settle(
            sessionmaker,
            market_id=market_id,
            request_id=request_id,
            claim=claim,
            outcome=_UNRESOLVED_FAILURE,
            now=now,
            result=result,
        )
        return

    try:
        body = _build_text(claim.kind, claim.payload, locale=_LOCALE)
    except (KeyError, TypeError, ValueError) as exc:
        # ⚠ MATN QURILMADI — bu KODDAGI xato (noma'lum `kind` yoki kutilmagan
        #   qiymat tipi). Qator `failed` ga o'tadi: qayta urinish uni
        #   tuzatmaydi va cheksiz urinish navbatni to'ldirardi.
        _swallow(result, "outbox_text_not_built", exc, market_id=market_id)
        await _settle(
            sessionmaker,
            market_id=market_id,
            request_id=request_id,
            claim=claim,
            outcome=OutboxFailure(
                error_type=type(exc).__name__,
                status_code=None,
                retry_after=None,
                disposition=OutboxDisposition.FAILED,
            ),
            now=now,
            result=result,
        )
        return

    await throttle.wait(str(chat_id))
    try:
        accepted = await sender.send_message(body, chat_id=str(chat_id))
    except Exception as exc:  # noqa: BLE001 - jo'natuvchi tikni yiqita olmaydi (D-23)
        _swallow(result, "outbox_send_crashed", exc, market_id=market_id)
        await _settle(
            sessionmaker,
            market_id=market_id,
            request_id=request_id,
            claim=claim,
            outcome=OutboxFailure(
                error_type=type(exc).__name__,
                status_code=None,
                retry_after=None,
                disposition=OutboxDisposition.RETRY,
            ),
            now=now,
            result=result,
        )
        return

    if accepted:
        await _mark_delivered(
            sessionmaker,
            market_id=market_id,
            request_id=request_id,
            claim=claim,
            result=result,
        )
        return

    await _settle(
        sessionmaker,
        market_id=market_id,
        request_id=request_id,
        claim=claim,
        outcome=_classify(sender.last_failure),
        now=now,
        result=result,
    )


async def _mark_delivered(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    claim: OutboxClaim,
    result: OutboxTickResult,
) -> None:
    """`delivered` — «Telegram QABUL QILDI», ⛔ «o'qildi» EMAS (Pitfall 2)."""
    message_id = last_message_id()
    if message_id is None:
        # Telegram `200` qaytardi, ya'ni xabar CHATGA JOYLANDI — qayta
        # yuborish uni IKKILANTIRARDI (`_MESSAGE_ID_UNKNOWN` docstringi).
        log.warning("outbox_message_id_unreadable", market_id=str(market_id))
        message_id = _MESSAGE_ID_UNKNOWN

    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            await outbox_repo.mark_delivered(
                session,
                market_id=market_id,
                outbox_id=claim.id,
                provider_message_id=message_id,
            )
    except SQLAlchemyError as exc:
        _swallow(result, "outbox_mark_delivered_failed", exc, market_id=market_id)
        return

    result.delivered += 1


async def _settle(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    claim: OutboxClaim,
    outcome: OutboxFailure,
    now: datetime,
    result: OutboxTickResult,
) -> None:
    """Yiqilgan (yoki umuman qilinmagan) urinishning holatini yozadi.

    ⛔ BYUDJET FAQAT HAQIQIY URINISHGA QO'LLANADI: `unresolved` shoxida
       HTTP so'rovi UMUMAN yuborilmagan, ya'ni uni `MAX_ATTEMPTS` ga
       hisoblash sotuvchining byudjetini u hali BOTGA ULANMAGANI uchun
       yeb qo'yardi — kvitansiya `failed` bo'lardi va Telegram bilan hech
       qanday muammo bo'lmasdi (`release_expired_leases()` ning aynan o'sha
       qoidasi).
    """
    disposition = outcome.disposition
    if disposition is OutboxDisposition.RETRY and claim.attempt_count >= MAX_ATTEMPTS:
        disposition = OutboxDisposition.FAILED

    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            if disposition is OutboxDisposition.BLOCKED:
                await outbox_repo.mark_blocked(
                    session,
                    market_id=market_id,
                    outbox_id=claim.id,
                    error_type=outcome.error_type,
                )
            elif disposition is OutboxDisposition.FAILED:
                await outbox_repo.mark_failed(
                    session,
                    market_id=market_id,
                    outbox_id=claim.id,
                    error_type=outcome.error_type,
                    status_code=outcome.status_code,
                )
            else:
                next_attempt_at = (
                    now + timedelta(seconds=UNRESOLVED_RETRY_SECONDS)
                    if disposition is OutboxDisposition.UNRESOLVED
                    else _next_attempt_at(
                        claim.attempt_count, now=now, retry_after=outcome.retry_after
                    )
                )
                await outbox_repo.reschedule(
                    session,
                    market_id=market_id,
                    outbox_id=claim.id,
                    next_attempt_at=next_attempt_at,
                    error_type=outcome.error_type,
                    status_code=outcome.status_code,
                )
    except (SQLAlchemyError, ValueError) as exc:
        _swallow(result, "outbox_state_not_written", exc, market_id=market_id)
        return

    if disposition is OutboxDisposition.BLOCKED:
        result.blocked += 1
    elif disposition is OutboxDisposition.FAILED:
        result.failed += 1
    elif disposition is OutboxDisposition.UNRESOLVED:
        result.unresolved += 1
    else:
        result.rescheduled += 1
