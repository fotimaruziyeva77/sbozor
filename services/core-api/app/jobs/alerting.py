"""Alert supurgisi — YO'QLIKKA qo'yiladi, GURUHLANADI va bloklamaydi (FOUND-06).

=============================================================================
UCH QOIDA — VA ULARNING HAMMASI SHU FAYLNING SHAKLINI BELGILAYDI.

1. ALERT HOLATI XOTIRADA EMAS, `alert_events` JADVALIDA.

   «Oxirgi marta qachon yubordim?» degan savolga xotiradagi `dict` bilan
   javob berish — §A.2 ning aynan takrori: qiymat worker qayta ishga
   tushishidan OMON QOLMAYDI va deploy kuni admin bir xil xabarni
   qaytadan ola boshlaydi. Deploy esa aynan nosozlik ehtimoli yuqori
   bo'lgan payt.

   Debounce ning YAGONA DB kafolati — `alert_events` dagi qisman UNIQUE
   indeks (`uq_alert_events_market_id_alert_key_open`): bitta
   `(bozor, kalit, subyekt)` uchun AYNAN BITTA ochiq qator. Naqsh
   `nvr_discovery_runs` ning «bir vaqtda ikki skan yo'q» indeksi bilan
   bir xil (`0012_nvr_domain.py:409-415`).

2. GURUHLASH — MA'LUMOT YASHIRISH EMAS.

   Bo'g'ilgan takrorlar YO'QOLMAYDI: ular `occurrences` da sanaladi va
   UI ularni «So'nggi soatda yana 47 marta» qatori bilan KO'RSATADI
   (`04-UI-SPEC.md` §6.7 — o'sha qator MAJBURIY). Aks holda guruhlash
   foydalanuvchi uchun «tizim mendan nimadir yashiryapti» bo'lib ko'rinardi
   va u birinchi shubhadan keyin jurnalga o'tib ketardi.

   Xuddi shu sababdan `notified_at` `NULL` bo'lganda UI «Telegram xabari
   YUBORILMADI» qatorini YASHIRMAYDI.

3. ⛔ ALERT YUBORISH ASOSIY OQIMNI BLOKLAMAYDI.

   `discovery.py:529-556` naqshi: ALOHIDA, QISQA tranzaksiya va YUTILGAN
   xato + `log.warning`. Alert supurgisi kadr olishning yo'liga UMUMAN
   kirmaydi — u alohida cron vazifasi va u yiqilsa kadr olish DAVOM
   ETADI.

   Teskarisi — Telegram uzilishining kadr olishni to'xtatishi — kuzatuv
   vositasining kuzatilayotgan tizimni yiqitishi bo'lardi, ya'ni alert
   mexanizmi o'zi ogohlantirishi kerak bo'lgan zarardan kattaroq zarar
   keltirardi.
=============================================================================

=============================================================================
D-20 — ALERT MUVAFFAQIYAT SIGNALINING YO'QLIGIGA QO'YILADI.

CLAUDE.md ning bitta jumlasi («Alert on **absence of a success signal**,
not just on error exit codes») butun bu faylning arxitekturasini
belgilaydi. Uch xil JIMLIK bor va ular UCH XIL mexanizm talab qiladi:

  | Jimlik                        | Detektor                          |
  |-------------------------------|-----------------------------------|
  | Ish bajarildi, natija yomon   | `try/except` -> `capture_runs`    |
  | Ish UMUMAN bajarilmadi        | materializatsiya + watchdog (B.5) |
  | DETEKTORNING O'ZI bajarilmadi | heartbeat + BOSHQA jarayon        |

⚠⚠ IKKINCHISI SHU FAYLNING ENG MUHIM MANBAI VA U ISTISNODAN KELMAYDI.
   «06:00 sloti umuman olinmadi» holatida hech qanday hodisa YO'Q: xato
   yo'q, jurnal satri yo'q, Sentry yozuvi yo'q. Shuning uchun bu yerdagi
   manba `try/except` emas, `capture_runs` ning `missed` QATORI —
   `04-05`/`04-07` rejani AYNAN shuning uchun oldindan materializatsiya
   qiladi: yo'qlik QATORGA aylanadi va faqat o'shanda ko'rinadigan
   bo'ladi.

⚠ UCHINCHISI shu faylda TUG'ILMAYDI, u `core-api` ning
  `/internal/self-check` endpointida (04-09) — va uning butun ma'nosi
  shundaki, u BOSHQA KONTEYNERDA ishlaydi. Supurgi worker'da yashaydi,
  ya'ni worker o'lganda u ham jim bo'ladi.
=============================================================================

=============================================================================
D-22 — ALERT CHARCHOG'I VA UNING NARXI.

    Yomon kun: tunnel 07:00-08:00 da uzildi.
      25 kamera x 3 slot = 75 ta yiqilish
      Guruhlashsiz: 75 ta Telegram xabari

Telegram ning o'z chegarasi (rasmiy FAQ): guruhda daqiqasiga ~20 xabar,
undan keyin `429`. Ya'ni 75 xabar birinchi daqiqadayoq chegaraga uriladi
va ENG MUHIM xabarlar yo'qoladi.

Lekin texnik chegara IKKINCHI darajali. Asosiy muammo INSON: ketma-ket
75 ta xabar olgan admin ertasi kuni bildirishnomani o'chiradi va shundan
keyin HAQIQIY nosozlik ham ko'rinmay qoladi. Ya'ni guruhlashsiz alert
kanali birinchi yomon kunda O'LADI.

Shuning uchun: bozor bo'yicha BITTA xabar, `60` daqiqalik debounce va
eskalatsiya CHASTOTA emas, DARAJA bo'yicha.

⛔ LEKIN GURUHLASH HAMMA NARSAGA QO'LLANMAYDI. `NEVER_SUPPRESSED_ALERT_KEYS`
   dagi hodisalar debounce oynasi ichida ham DARHOL yuboriladi. Ro'yxat
   METADAN HOSILA (`nvr-errors.ts:139` uslubi) — qo'lda takrorlangan
   nusxa reyestr bilan bir kun ajralib ketardi va bo'g'ilmasligi kerak
   bo'lgan hodisa jimgina bo'g'ilardi.
=============================================================================

⚠ `taskiq` IMPORT QILINMAYDI (S-4, D-06) — bu modul sof `async def`.
⚠ Bu yerda kadr rasmi, obyekt kaliti yoki shaxsiy ma'lumot HECH QAYERGA
  yozilmaydi (D-19): `detail` ning kalitlari ALLOWLIST bilan cheklangan
  va `AlertSender` ning o'zida rasm biriktiruvchi metod umuman yo'q.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Final

import structlog
from sbozor_core.enums import ActorKind, AlertSeverity, CaptureRunStatus
from sbozor_core.models.ops import SystemHeartbeat
from sbozor_core.models.snapshot import (
    ALERT_OPEN_EXPR,
    ALERT_OPEN_PREDICATE,
    AlertEvent,
    CaptureRun,
    Snapshot,
)
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import business_date, now_tz
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.jobs.billing_close import BILLING_CLOSE_COMPONENT
from app.jobs.notifications import (
    DIGEST_EVENING_COMPONENT,
    DIGEST_MORNING_COMPONENT,
    OVERDUE_COMPONENT,
)
from app.jobs.outbox import OUTBOX_COMPONENT
from app.jobs.reconciliation import RECON_OPEN_COMPONENT
from app.jobs.retention import RETENTION_COMPONENT, active_market_ids, disk_usage_percent
from app.repositories.capture_repo import CaptureRepository
from app.services.capture_errors import (
    CAPTURE_AUTH_LOCKING_CODES,
    CAPTURE_CREDENTIAL_UNREADABLE,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.services.alerts import AlertSender

log = structlog.get_logger(__name__)

__all__ = [
    "ALERT_DETAIL_KEYS",
    "ALERT_META",
    "ALERT_SWEEP_COMPONENT",
    "BACKUP_COMPONENT",
    "NEVER_SUPPRESSED_ALERT_KEYS",
    "PLATFORM_SCOPED_ALERT_KEYS",
    "STORABLE_ALERT_KEYS",
    "DigestResult",
    "SweepResult",
    "alert_sweep",
    "daily_digest",
    "raise_alert",
]


ALERT_SWEEP_COMPONENT: Final[str] = "alert_sweep"
"""`system_heartbeats.component` — supurgining O'Z yurak urishi.

⚠ SUPURGI HAM KUZATILADI VA BU ATAYIN: detektorning o'zi o'lgan holat
  (D-20 ning uchinchi qatori) faqat shu qator orqali ko'rinadi. Uni
  `/internal/self-check` (04-09) BOSHQA JARAYONDAN o'qiydi.
"""

BACKUP_COMPONENT: Final[str] = "backup"
"""8-fazada (FOUND-07) quriladigan zaxira jarayonining yurak urishi.

⚠⚠ QATOR HOZIR UMUMAN YO'Q VA BU AYNAN O'LCHANADIGAN HOLAT. `backup_stale`
   alerti «yozuv bor, lekin eskirgan» dan tashqari «yozuv UMUMAN
   YOZILMAGAN» holatini ham qoplaydi — CLAUDE.md ning «alert on absence
   of a success signal» talabi aynan shuni bildiradi. Faqat eskirishni
   tekshiradigan variant zaxira HECH QACHON ishlamagan o'rnatmada MANGU
   jim qolardi.
"""

HEARTBEAT_STALE_HOURS: Final[int] = 26
"""Yurak urishining eskirish chegarasi — SUTKADAN KATTA.

⚠ 24 EMAS, 26. Zaxira ham, retention ham SUTKALIK jadval bilan ishlaydi,
  ya'ni ketma-ket ikki yugurish orasi tabiiy ravishda ~24 soat. Chegarani
  24 ga qo'yish har kuni chegaraga tegib turgan alertni tug'dirardi (yugurish
  bir daqiqa kechiksa ham). Ikki soatlik zaxira D-22 ning «yolg'on alert
  kanalni o'ldiradi» qoidasining bevosita qo'llanishi.
"""

DEBOUNCE_MINUTES: Final[int] = 60
"""Bir xil `(bozor, kalit, subyekt)` uchun xabarlar orasidagi eng qisqa oraliq."""

ESCALATION_HOURS: Final[int] = 3
"""Ochiq alert `warning` dan `critical` ga ko'tariladigan yosh.

⚠ ESKALATSIYA — DARAJA, CHASTOTA EMAS. Muammo davom etsa xabarlar
  TEZLASHMAYDI; ularning darajasi oshadi va matnda davomiylik ko'rsatiladi.
  Teskarisi (takroriy xabar yuborish) alert kanalini birinchi haftadayoq
  o'ldirardi.
"""

DISK_PRESSURE_PERCENT: Final[float] = 85.0
"""Disk to'lishining chegarasi (§D.11 ning bevosita natijasi).

Disk to'lganda Postgres ham, ombor ham to'xtaydi va o'shanda HECH QANDAY
alert yuborib bo'lmaydi — ya'ni bu chegara «kech qolmaslik» uchun.
"""

CAMERA_OFFLINE_SLOTS: Final[int] = 3
"""Kamera «offline» deb e'lon qilinadigan KETMA-KET yiqilish soni.

⛔ BITTA KAMERA BITTA SLOTDA YIQILISHI — ALERT EMAS. U jurnalda va kunlik
   dayjestda ko'rinadi. Har o'tkinchi tarmoq uzilishiga alert yuborish —
   alert kanalini birinchi haftadayoq o'ldirish yo'li (§E.13).
"""

SLOT_FAILURE_RATIO: Final[float] = 0.30
"""Bitta slotda yiqilgan kameralarning ulushi — bu chegaradan oshsa alert.

⚠ IKKINCHI, MUSTAQIL YO'L: 22 kamera BITTA slotda yiqilganda hech
  qaysisida «3 ketma-ket» to'planmaydi, lekin bozor amalda ko'r bo'ladi.
  Bu shox aynan shu holatni ushlaydi va u BITTA qator beradi (subyekt
  `NULL` — «butun bozor»), 22 ta emas.
"""

MARKET_BLIND_SLOTS: Final[int] = 2
"""Butun bozorda 0 % muvaffaqiyat bilan o'tgan KETMA-KET slotlar soni.

Bu «bir necha kamera» emas, BOZOR KO'R BO'LIB QOLDI: kunlik hisobning
butun asosi yo'qoladi. Shuning uchun `capture_stopped` HECH QACHON
bo'g'ilmaydi.
"""

ALERT_DETAIL_KEYS: Final[frozenset[str]] = frozenset(
    {"market_name", "camera_count", "error_code", "slot_time", "stale_hours", "disk_pct"}
)
"""`alert_events.detail` ga tushishi MUMKIN bo'lgan YAGONA kalitlar (D-19).

⛔ ALLOWLIST, DENYLIST EMAS. `04-UI-SPEC.md` §6.7 noma'lum kalitni render
   QILMAYDI, ya'ni ro'yxatdan tashqari qiymat jimgina ko'rinmas bo'lib
   qolardi — lekin u BAZAGA baribir yozilardi va u yerdan zaxiraga,
   zaxiradan esa tashqi bucketga chiqardi.

   Shuning uchun chegara YOZISH paytida qo'yiladi (`_detail()`): kadr
   havolasi, obyekt kaliti, kamera nomi yoki sotuvchi ma'lumoti bu
   jadvalga STRUKTURAVIY ravishda tusha olmaydi.
"""


@dataclass(frozen=True, slots=True)
class AlertMeta:
    """Bitta alert kalitining REYESTR yozuvi.

    ⚠ REYESTR YAGONA MANBA: `NEVER_SUPPRESSED_ALERT_KEYS` va
      `PLATFORM_SCOPED_ALERT_KEYS` undan HOSILA qilinadi
      (`capture_errors.py::CAPTURE_AUTH_LOCKING_CODES` va
      `nvr-errors.ts:139` bilan aynan bir xil naqsh). Qo'lda yozilgan
      ikkinchi ro'yxat bugun to'g'ri qiymat berardi va ertaga jimgina
      ajralib ketardi.
    """

    key: str
    """i18n KALITI, matn emas (`capture_runs.error_code` bilan bir xil qaror)."""

    severity: str
    """Tug'ilish darajasi. Eskalatsiya uni `critical` ga ko'taradi."""

    never_suppressed: bool
    """⛔ D-22: debounce oynasi ichida ham DARHOL yuboriladi."""

    platform_scoped: bool
    """Qator HAR BOZORGA yoziladi, xabar esa bozorlar bo'ylab BITTA bo'ladi."""

    storable: bool = True
    """`alert_events` ga qator sifatida yoziladimi.

    `capture_recovered` — YAGONA `False`: u ochiq ish emas, ochiq ishning
    YOPILISHI haqidagi xabar. Uni qator qilib yozish «tiklanish» ni ham
    yopilishi kerak bo'lgan muammoga aylantirardi.
    """


ALERT_META: Final[dict[str, AlertMeta]] = {
    meta.key: meta
    for meta in (
        # -------------------------------------------------------------
        # 1-GURUH — KADR OLISHNING YO'QLIGI (D-20 ning yuragi)
        # -------------------------------------------------------------
        # Slot rejalashtirildi, grace oynasi o'tdi, hech kim bajarmadi.
        AlertMeta("capture_missed", AlertSeverity.WARNING.value, False, False),
        # Butun bozor ketma-ket ikki slotda 0 % — BOZOR KO'R BO'LDI.
        AlertMeta("capture_stopped", AlertSeverity.CRITICAL.value, True, False),
        # Kamera uzoq vaqt javob bermayapti (3 ketma-ket slot yoki >=30 %).
        AlertMeta("camera_offline", AlertSeverity.WARNING.value, True, False),
        # -------------------------------------------------------------
        # 2-GURUH — KONFIGURATSIYA. O'Z-O'ZIDAN HECH QACHON TUZALMAYDI.
        # -------------------------------------------------------------
        AlertMeta("capture_credential_unreadable", AlertSeverity.CRITICAL.value, True, False),
        # Vaqt sezgir: qulf oynasi bor va uni kutish kerak — bo'g'ilgan
        # xabar adminni aynan o'sha oyna davomida kechiktirardi.
        AlertMeta("nvr_account_locked", AlertSeverity.CRITICAL.value, True, False),
        # -------------------------------------------------------------
        # 3-GURUH — PLATFORMA. Qator har bozorga, xabar BITTA.
        # -------------------------------------------------------------
        AlertMeta("backup_stale", AlertSeverity.CRITICAL.value, True, True),
        AlertMeta("retention_stale", AlertSeverity.WARNING.value, False, True),
        AlertMeta("disk_pressure", AlertSeverity.CRITICAL.value, True, True),
        # ⛔ `critical` VA BO'G'ILMAYDI — `retention_stale` (`warning`) DAN
        #   FARQI ONGLI: saqlash siyosati bir kun o'tkazib yuborilsa disk
        #   biroz to'ladi, patta hisobi o'tkazib yuborilsa esa O'SHA
        #   KUNNING TUSHUMI umuman yozilmaydi va u kunlik hisobotdan
        #   JIMGINA tushib qoladi. Bu `backup_stale` bilan bir sinf:
        #   yo'qotish QAYTARIB BO'LMAYDIGAN emas (job konvergent), lekin
        #   uni sezmaslik oyning oxirigacha cho'zilardi.
        AlertMeta("billing_close_stale", AlertSeverity.CRITICAL.value, True, True),
        # ⛔ `critical` VA BO'G'ILMAYDI — VA BU 7-FAZANING ENG QIMMAT
        #   SUKUNATI. Navbat to'xtasa KVITANSIYA ham ketmaydi (CASH-05),
        #   ya'ni sotuvchi to'laganini isbotlay olmaydi — D-02 ning
        #   AYNAN o'zi. Qolgan uchtasi (pastda) `warning`, chunki ular
        #   HISOBOTNI kechiktiradi; bu esa NIZODAGI DALILNI yo'qotadi.
        #   `never_suppressed`: to'xtagan navbat o'z-o'zidan tuzalmaydi va
        #   debounce oynasi xabarni bir soatga kechiktirardi — o'sha bir
        #   soatda esa butun savdo kunining kvitansiyalari to'planardi.
        AlertMeta("outbox_stale", AlertSeverity.CRITICAL.value, True, True),
        # ⚠ `warning`: case ochilmasa nomuvofiqlik YO'QOLMAYDI — job
        #   IDEMPOTENT va ertangi yugurish o'sha kunni ham qamraydi
        #   (`reconciliation_open` ning `ON CONFLICT DO NOTHING` i).
        #   Yo'qotish QAYTARIB BO'LADIGAN, ya'ni `retention_stale` bilan
        #   bir sinf, `billing_close_stale` bilan emas.
        AlertMeta("reconciliation_stale", AlertSeverity.WARNING.value, False, True),
        # ⚠ `warning`: o'tkazib yuborilgan dayjest — O'QILMAGAN XABAR,
        #   yo'qotilgan MA'LUMOT emas. Sonlar bazada turaveradi va
        #   direktor ularni veb yuzasida ko'radi. `critical` daraja bu
        #   yerda D-22 ning teskarisi bo'lardi: kuniga ikki marta
        #   ishlaydigan job uchun shoshilinch signal shovqinga aylanardi.
        AlertMeta("digest_stale", AlertSeverity.WARNING.value, False, True),
        # ⚠ `warning` va sabab `digest_stale` niki bilan bir xil: eslatma
        #   kechiksa qarz O'SMAYDI — u allaqachon mavjud va veb yuzasida
        #   ko'rinadi. Lekin komponent kuzatilishi SHART: kuzatilmagan
        #   eslatma jobi hech qanday xato bermaydi va uning o'limini
        #   ma'muriyat OYLAR keyin sezardi (`deferred-items.md` 2-bandi).
        AlertMeta("overdue_stale", AlertSeverity.WARNING.value, False, True),
        # -------------------------------------------------------------
        # 4-GURUH — XABAR, OCHIQ ISH EMAS.
        # -------------------------------------------------------------
        AlertMeta("capture_recovered", AlertSeverity.INFO.value, False, False, storable=False),
        # -------------------------------------------------------------
        # 5-GURUH — REYESTR NUQSONI (7-faza, D-26b / T-07-44a).
        # -------------------------------------------------------------
        # ⛔ SUPURGI EMAS, HODISA TUG'DIRADI: bu kalit
        #   `binding_repo.resolve()` ning «bir nechta moslik» shoxidan
        #   keladi, ya'ni u so'rov yo'lida tug'iladi. Ro'yxatga OLINMASA
        #   `_upsert()` `ALERT_META[key]` ustida `KeyError` berardi va
        #   (xato yutilsa) anomaliya JIMGINA yo'qolardi — aynan D-26(b)
        #   oldini olmoqchi bo'lgan nosozlik.
        #
        # * `WARNING`, `CRITICAL` EMAS: reyestr nuqsoni pul yig'ishni
        #   TO'XTATMAYDI va bozorni ko'r qilmaydi — u BITTA sotuvchining
        #   ulanishini to'sadi. `CRITICAL` daraja `capture_stopped` /
        #   `billing_close_stale` sinfi uchun saqlanadi (qaytarib
        #   bo'lmaydigan yoki butun kunni yo'qotadigan hodisalar).
        # * `never_suppressed=False`: sotuvchi tugmani qayta-qayta bosishi
        #   mumkin va debounce oynasi AYNAN SHU YERDA kerak — aks holda
        #   bitta dublikat raqam adminga o'nlab xabar yuborardi (yuqoridagi
        #   D-22 «75 ta xabar» sinfi).
        # * `platform_scoped=False`: to'qnashuv IKKALA bozorning reyestriga
        #   tegishli va har bozor direktori O'Z qatorini ko'rishi kerak.
        #   `True` bo'lsa xabar bozorlar bo'ylab BITTA bo'lib birlashardi
        #   va ikkinchi bozor ma'muriyati hech nima ko'rmasdi.
        AlertMeta(
            "vendor_binding_conflict",
            AlertSeverity.WARNING.value,
            never_suppressed=False,
            platform_scoped=False,
        ),
    )
}
"""Alert kalitlarining YAGONA reyestri — `04-UI-SPEC.md` §11.9 bilan mos."""

NEVER_SUPPRESSED_ALERT_KEYS: Final[frozenset[str]] = frozenset(
    key for key, meta in ALERT_META.items() if meta.never_suppressed
)
"""⛔ D-22 — debounce BU KALITLARGA QO'LLANMAYDI.

METADAN HOSILA, qo'lda sanalmagan. Bo'g'ilmasligi kerak bo'lgan hodisani
bo'g'ish — debounce YO'Q bo'lishidan YOMONROQ: admin tizim ishlayapti deb
o'ylab turadi, holbuki zaxira uch kundan beri yozilmayapti.
"""

PLATFORM_SCOPED_ALERT_KEYS: Final[frozenset[str]] = frozenset(
    key for key, meta in ALERT_META.items() if meta.platform_scoped
)
"""Bozorga tegishli BO'LMAGAN, lekin bozor sahifasida ko'rinadigan kalitlar.

=============================================================================
NEGA QATOR HAR BOZORGA, XABAR ESA BITTA.

`alert_events` — TENANT jadvali (`market_id NOT NULL`, 04-01 qarori), ya'ni
platforma darajasidagi hodisani `market_id = NULL` bilan yozib bo'lmaydi.
Va bu to'g'ri: UI ogohlantirishni BOZOR SAHIFASIDA ko'rsatadi
(`04-UI-SPEC.md` §11.9) — «zaxira eskirgan» xabari aynan o'sha bozor
ma'muriyatiga ham tegishli.

Lekin Telegram tomonida teskari xato paydo bo'lardi: bitta zaxira
nosozligi N ta bozor uchun N ta xabar berardi va D-22 ning butun
guruhlashi bir zarbada yo'qolardi. Shuning uchun jo'natuvchi bu kalitlarni
bozorlar bo'ylab BIRLASHTIRADI va AYNAN BITTA xabar qiladi.
=============================================================================
"""

STORABLE_ALERT_KEYS: Final[frozenset[str]] = frozenset(
    key for key, meta in ALERT_META.items() if meta.storable
)
"""`alert_events` ga qator sifatida tushadigan kalitlar — reyestrdan HOSILA."""

RECOVERED_KEY: Final[str] = "capture_recovered"
"""Tiklanish xabarining kaliti.

⛔ QO'LDA YOPISH YO'Q (`04-UI-SPEC.md` §6.7): ochiq alertni yopadigan
   YAGONA narsa — manbaning yo'qolishi. Yopish tugmasi adminga muammoni
   ko'rmasdan yashirish imkonini berardi va bu D-22 ning teskarisi
   bo'lardi.
"""


# ===========================================================================
# Natija tiplari
# ===========================================================================


@dataclass(slots=True)
class SweepResult:
    """Bitta supurgining O'LCHANADIGAN natijasi.

    ⛔ NOL — NATIJA, uning yo'qligi emas (`DaySummary` bilan bir xil qoida).
    """

    markets: int = 0
    raised: int = 0
    """Yangi ochilgan yoki takrori sanalgan alertlar."""
    escalated: int = 0
    resolved: int = 0
    notified: int = 0
    """YUBORILGAN Telegram xabarlari soni — alertlar soni EMAS.

    Ikkalasining farqi guruhlashning O'ZI: 22 kameralik yiqilish bitta
    alert va bitta xabar beradi, 5 xil sabab esa bitta xabar va besh
    qator.
    """
    suppressed: int = 0
    """Debounce oynasi ichida qolgan (xabarsiz) alertlar."""
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DigestResult:
    """Kunlik dayjestning natijasi."""

    markets: int = 0
    sent: int = 0
    errors: list[str] = field(default_factory=list)


# ===========================================================================
# Ichki tiplar
# ===========================================================================


@dataclass(frozen=True, slots=True)
class _Signal:
    """«Hozir shu bozorda shu muammo BOR» degan fakt — qator EMAS."""

    key: str
    subject_id: UUID | None
    detail: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _Due:
    """Xabar talab qiladigan alert (yangi, eskalatsiya yoki tiklanish)."""

    alert_id: UUID | None
    key: str
    severity: str
    occurrences: int
    first_seen_at: datetime | None
    detail: dict[str, Any]
    kind: str


def _detail(**values: Any) -> dict[str, Any]:
    """`alert_events.detail` ni ALLOWLIST ostida quradi (D-19).

    ⚠ `ValueError` ATAYIN QATTIQ: ro'yxatdan tashqari kalit KODDAGI xato,
      ma'lumot xatosi emas — va u jimgina o'tib ketsa shaxsiy ma'lumot
      bazaga, u yerdan zaxiraga va tashqi bucketga chiqardi.
    """
    unknown = sorted(set(values) - ALERT_DETAIL_KEYS)
    if unknown:
        raise ValueError(f"`alert_events.detail` uchun ruxsat etilmagan kalit(lar): {unknown}")
    return {key: value for key, value in values.items() if value is not None}


@asynccontextmanager
async def _tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """`discovery.py::_system_transaction()` ning shu moduldagi jufti."""
    # SIM117 — ichki blok TRANZAKSIYA chegarasi (`discovery.py:194-196`).
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


# ===========================================================================
# SUPURGI
# ===========================================================================


async def alert_sweep(
    sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    *,
    now: datetime | None = None,
    disk_path: str = "/",
) -> SweepResult:
    """Yo'qlikni topadi, guruhlaydi, bo'g'adi, eskalatsiya qiladi va yuboradi.

    Args:
        sessionmaker: sessiya fabrikasi (ARGUMENT, modul globali emas).
        sender: Telegram jo'natuvchisi. ARGUMENT — testda `respx` bilan
            o'lchanadi va mahsulotda `TaskiqState` dan keladi.
        now: joriy payt. ARGUMENT — debounce va eskalatsiya arifmetikasi
            aynan shu qiymatga qaraydi, ya'ni ularni soatni siljitmasdan
            o'lchash mumkin bo'ladi.
        disk_path: disk to'lishi o'lchanadigan yo'l.

    Returns:
        `SweepResult` — sonlar va yutilgan xato TURLARI.
    """
    moment = now if now is not None else now_tz()
    today = business_date(moment)
    request_id = f"job-alert-{today.isoformat()}-{moment.strftime('%H%M')}"
    result = SweepResult()

    try:
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        log.exception("alert_sweep_market_list_failed")
        market_ids = []
    result.markets = len(market_ids)

    platform_signals = await _platform_signals(sessionmaker, moment=moment, disk_path=disk_path)

    # ⚠ PLATFORMA XABARLARI BOZORLAR BO'YLAB YIG'ILADI va oxirida BITTA
    #   xabar bo'lib chiqadi (`PLATFORM_SCOPED_ALERT_KEYS` docstringi).
    platform_due: dict[str, _Due] = {}

    for market_id in market_ids:
        try:
            market_signals = await _market_signals(
                sessionmaker, market_id=market_id, request_id=request_id, today=today
            )
        except SQLAlchemyError as exc:
            _swallow(result, "alert_sweep_market_scan_failed", exc, market_id=market_id)
            continue

        signals = [*market_signals, *platform_signals]
        try:
            due = await _reconcile(
                sessionmaker,
                market_id=market_id,
                request_id=request_id,
                signals=signals,
                moment=moment,
                result=result,
            )
        except SQLAlchemyError as exc:
            _swallow(result, "alert_sweep_reconcile_failed", exc, market_id=market_id)
            continue

        market_due = [item for item in due if item.key not in PLATFORM_SCOPED_ALERT_KEYS]
        for item in due:
            if item.key in PLATFORM_SCOPED_ALERT_KEYS:
                # Bir xil kalit N bozorda takrorlanadi — birinchisi yetadi.
                platform_due.setdefault(item.key, item)

        if market_due:
            await _notify(
                sessionmaker,
                sender,
                market_id=market_id,
                request_id=request_id,
                due=market_due,
                moment=moment,
                result=result,
            )

    if platform_due and market_ids:
        await _notify(
            sessionmaker,
            sender,
            market_id=market_ids[0],
            request_id=request_id,
            due=list(platform_due.values()),
            moment=moment,
            result=result,
            platform=True,
        )

    await _write_heartbeat(ALERT_SWEEP_COMPONENT, sessionmaker, _sweep_detail(result))
    log.info(
        "alert_sweep_done",
        markets=result.markets,
        raised=result.raised,
        escalated=result.escalated,
        resolved=result.resolved,
        notified=result.notified,
        suppressed=result.suppressed,
        errors=len(result.errors),
    )
    return result


def _sweep_detail(result: SweepResult) -> dict[str, Any]:
    return {
        "markets": result.markets,
        "raised": result.raised,
        "resolved": result.resolved,
        "notified": result.notified,
    }


# ===========================================================================
# MANBALAR — platforma darajasi
# ===========================================================================


async def _platform_signals(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    moment: datetime,
    disk_path: str,
) -> list[_Signal]:
    """Bozorga bog'liq BO'LMAGAN signallar — bir marta o'lchanadi.

    ⚠ TENANT KONTEKSTI YO'Q: `system_heartbeats` — GLOBAL jadval, unda
      `market_id` ustuni umuman yo'q (`ops.py::SystemHeartbeat`). Uni
      tenant-scoped qilish D-20 ning aynan buziladigan joyi bo'lardi: tik
      umuman ishlamayotgan bo'lsa uning yo'qligini bozor kontekstida
      qidirish 0 qator berardi va sukunat «hammasi joyida» bilan bir xil
      ko'rinardi.
    """
    signals: list[_Signal] = []

    try:
        seen = await _heartbeats(sessionmaker)
    except SQLAlchemyError:
        log.exception("alert_sweep_heartbeat_read_failed")
        seen = {}

    stale_after = timedelta(hours=HEARTBEAT_STALE_HOURS)
    watched = (
        (BACKUP_COMPONENT, "backup_stale"),
        (RETENTION_COMPONENT, "retention_stale"),
        # ⛔⛔ 06-07 QO'SHDI — VA BU O'LCHANGAN KO'RLIKNI YOPADI.
        #   `billing.close` cron jadvali `import` PAYTIDA olinadi
        #   (`worker.py:55-58`), ya'ni `scheduler` konteyneri qayta ishga
        #   tushirilmasa vazifa RO'YXATGA OLINMAYDI: job hech qachon
        #   ishlamaydi, patta hisobi yozilmaydi va HECH QANDAY xato
        #   chiqmaydi. Buni birorta test ushlamaydi — pastdagi `None ham
        #   eskirish` qoidasi esa AYNAN shu holatni alertga aylantiradi.
        (BILLING_CLOSE_COMPONENT, "billing_close_stale"),
        # ⛔⛔ 07-14 QO'SHDI — BESHALA YANGI CRON O'SHA KO'RLIK OSTIDA EDI.
        #   Yuqoridagi `billing.close` bandi bilan AYNAN bir xil sabab va u
        #   endi BESH vazifaga tegishli: jadval `import` PAYTIDA olinadi,
        #   ya'ni `scheduler` qayta ishga tushirilmasa vazifa RO'YXATGA
        #   OLINMAYDI va HECH QANDAY xato chiqmaydi.
        #
        # ⛔ KOMPONENT NOMLARI IMPORT QILINADI, literal yozilmaydi
        #   (`BILLING_CLOSE_COMPONENT` naqshi): qo'lda yozilgan ikkinchi
        #   nusxa jimgina ajralib ketardi — job yurak urishini BIR nom
        #   bilan yozardi, supurgi esa BOSHQA nomni kutib «yo'q» alertini
        #   MANGU ko'tarib turardi.
        #
        # ⛔⛔ BESHTA JUFTLIK, BESHTA VAZIFA — 07-13 NING ONGLI NARXI
        #   07-21 DA YOPILDI (WR-10). Ilgari ikkala dayjest BITTA
        #   `notify_digest` qatorini yangilardi, ya'ni kechkisi ishlab
        #   ertalabkisi o'lganda yurak urishi HAMON YANGI ko'rinardi va
        #   `digest_stale` HECH QACHON ko'tarilmasdi — D-20 ning «alert
        #   MUVAFFAQIYAT SIGNALINING YO'QLIGIGA qo'yiladi» qoidasi yarim
        #   ishlardi.
        #
        # ⛔ ALERT KALITI BITTA QOLADI (`digest_stale`) VA BU ONGLI QAROR,
        #   UNUTISH EMAS. Ikkinchi kalit `ALERT_META` reyestriga,
        #   frontend ning `ALERT_TITLE_KEYS` xaritasiga va uchala locale
        #   matniga tegardi — ya'ni ikkita frontend faylni sof backend
        #   o'zgarishiga tortardi. Operatorga kerakli FAKT («dayjest
        #   o'lgan») bitta kalit bilan ham to'liq yetadi; QAYSI BIRI
        #   o'lgani esa `/internal/self-check` ning `stale` va
        #   `never_seen` ro'yxatlarida NOMMA-NOM ko'rinadi.
        #
        # ⚠ `_upsert()` NING DEBOUNCE'I IKKI SIGNALNI BITTA QATORGA
        #   YIG'ADI (`occurrences` o'sadi) — bu MAVJUD va O'LCHANGAN xulq
        #   (`uq_alert_events_market_id_alert_key_open` qisman UNIQUE
        #   indeksi), ya'ni ikkala dayjest ham o'lgan kunda admin IKKI
        #   emas, BITTA xabar oladi.
        (OUTBOX_COMPONENT, "outbox_stale"),
        (RECON_OPEN_COMPONENT, "reconciliation_stale"),
        (DIGEST_MORNING_COMPONENT, "digest_stale"),
        (DIGEST_EVENING_COMPONENT, "digest_stale"),
        (OVERDUE_COMPONENT, "overdue_stale"),
    )
    for component, key in watched:
        last_seen = seen.get(component)
        # ⚠⚠ `None` HAM ESKIRISH: qator UMUMAN yozilmagan holat (zaxira
        #    8-fazada quriladi, ya'ni bugun u AYNAN shunday) alertga
        #    aylanishi SHART — «alert on absence of a success signal».
        if last_seen is None or moment - last_seen >= stale_after:
            stale_hours = (
                None if last_seen is None else int((moment - last_seen).total_seconds() // 3600)
            )
            signals.append(_Signal(key, None, _detail(stale_hours=stale_hours)))

    used = disk_usage_percent(disk_path)
    if used >= DISK_PRESSURE_PERCENT:
        signals.append(_Signal("disk_pressure", None, _detail(disk_pct=used)))

    return signals


async def _heartbeats(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> dict[str, datetime]:
    """Barcha yurak urishlari — komponent -> oxirgi payt."""
    async with sessionmaker() as session, session.begin():
        rows = await session.execute(
            select(SystemHeartbeat.component, SystemHeartbeat.last_seen_at)
        )
        return {row.component: row.last_seen_at for row in rows}


# ===========================================================================
# MANBALAR — bozor darajasi (D-20 ning yuragi)
# ===========================================================================


async def _market_signals(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    today: date,
) -> list[_Signal]:
    """Bugungi `capture_runs` dan chiqadigan signallar.

    ⚠⚠ MANBA — QATOR, ISTISNO EMAS (D-20). «Slot umuman bajarilmadi»
       holatida hech qanday istisno yo'q; uni faqat `mark_missed()` yozgan
       `missed` qatori ko'rinadigan qiladi.
    """
    async with _tenant_session(sessionmaker, market_id=market_id, request_id=request_id) as session:
        rows = (
            await session.execute(
                select(
                    CaptureRun.camera_id,
                    CaptureRun.slot_time,
                    CaptureRun.status,
                    CaptureRun.error_code,
                )
                .where(CaptureRun.market_id == market_id, CaptureRun.business_date == today)
                .order_by(CaptureRun.slot_time, CaptureRun.camera_id)
            )
        ).all()

    return _signals_from_runs(rows)


def _signals_from_runs(rows: Sequence[Any]) -> list[_Signal]:
    """Bugungi qatorlardan signallarni CHIQARADI — sof funksiya.

    Sof, chunki chegaralar (3 ketma-ket slot, >=30 %, 2 ko'r slot)
    qarorlarning O'ZI va ular bazasiz o'lchanishi kerak.

    ⚠ `skipped` YIQILISH EMAS: bozor o'sha kuni yopiq bo'lgan (D-10) va
      uni yiqilish deb sanash har dam olish kunida alert berardi.
      `pending`/`running` esa HALI yakunlanmagan — ular ham hisobga
      olinmaydi.
    """
    failed_statuses = {CaptureRunStatus.FAILED.value, CaptureRunStatus.MISSED.value}
    terminal = {*failed_statuses, CaptureRunStatus.SUCCEEDED.value}

    by_slot: dict[Any, list[Any]] = defaultdict(list)
    for row in rows:
        if row.status in terminal:
            by_slot[row.slot_time].append(row)

    signals: list[_Signal] = []
    slots = sorted(by_slot)

    # --- 1. Yo'qlik: `missed` qatorlari -----------------------------------
    missed = [row for row in rows if row.status == CaptureRunStatus.MISSED.value]
    if missed:
        signals.append(
            _Signal(
                "capture_missed",
                None,
                _detail(
                    camera_count=len({row.camera_id for row in missed}),
                    slot_time=min(row.slot_time for row in missed).strftime("%H:%M"),
                ),
            )
        )

    # --- 2. Bozor ko'r bo'ldi: ketma-ket 2 slot 0 % -----------------------
    blind = 0
    for slot in reversed(slots):
        entries = by_slot[slot]
        if all(row.status in failed_statuses for row in entries):
            blind += 1
            continue
        break
    if blind >= MARKET_BLIND_SLOTS:
        signals.append(
            _Signal(
                "capture_stopped",
                None,
                _detail(
                    camera_count=len({row.camera_id for row in by_slot[slots[-1]]}),
                    slot_time=slots[-1].strftime("%H:%M"),
                ),
            )
        )

    # --- 3. Kamera offline: 3 ketma-ket YOKI bitta slotda >=30 % ----------
    worst = _worst_slot_ratio(by_slot, slots, failed_statuses)
    if worst is not None and worst[1] >= SLOT_FAILURE_RATIO:
        slot, _ratio, count = worst
        signals.append(
            _Signal(
                "camera_offline",
                None,
                _detail(camera_count=count, slot_time=slot.strftime("%H:%M")),
            )
        )
    signals.extend(_offline_cameras(by_slot, slots, failed_statuses))

    # --- 4. Konfiguratsiya kodlari ---------------------------------------
    codes = {row.error_code for row in rows if row.error_code}
    if CAPTURE_CREDENTIAL_UNREADABLE in codes:
        signals.append(
            _Signal(
                "capture_credential_unreadable",
                None,
                _detail(error_code=CAPTURE_CREDENTIAL_UNREADABLE),
            )
        )
    # ⚠ QULFLOVCHI KODLAR REYESTRDAN HOSILA (`capture_errors.py`), qo'lda
    #   sanalmagan: reyestrga yangi qulflovchi kod qo'shilsa bu shox uni
    #   AVTOMATIK ko'radi.
    locking = sorted(codes & CAPTURE_AUTH_LOCKING_CODES)
    if locking:
        signals.append(_Signal("nvr_account_locked", None, _detail(error_code=locking[0])))

    return signals


def _worst_slot_ratio(
    by_slot: dict[Any, list[Any]], slots: Sequence[Any], failed: set[str]
) -> tuple[Any, float, int] | None:
    """Eng ko'p kamera yiqilgan slot — `(slot, ulush, soni)`."""
    worst: tuple[Any, float, int] | None = None
    for slot in slots:
        entries = by_slot[slot]
        if not entries:
            continue
        broken = [row for row in entries if row.status in failed]
        ratio = len(broken) / len(entries)
        if worst is None or ratio > worst[1]:
            worst = (slot, ratio, len({row.camera_id for row in broken}))
    return worst


def _offline_cameras(
    by_slot: dict[Any, list[Any]], slots: Sequence[Any], failed: set[str]
) -> list[_Signal]:
    """KETMA-KET `CAMERA_OFFLINE_SLOTS` ta slotda yiqilgan kameralar."""
    streak: dict[UUID, int] = defaultdict(int)
    alive: set[UUID] = set()
    for slot in slots:
        for row in by_slot[slot]:
            if row.status in failed:
                streak[row.camera_id] += 1
            else:
                streak[row.camera_id] = 0
                alive.add(row.camera_id)
    return [
        _Signal("camera_offline", camera_id, _detail(camera_count=1))
        for camera_id, count in sorted(streak.items(), key=lambda item: str(item[0]))
        if count >= CAMERA_OFFLINE_SLOTS
    ]


# ===========================================================================
# HOLAT MASHINASI — upsert, eskalatsiya, tiklanish
# ===========================================================================


async def _reconcile(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str,
    signals: Sequence[_Signal],
    moment: datetime,
    result: SweepResult,
) -> list[_Due]:
    """Signallarni `alert_events` bilan solishtiradi va XABAR RO'YXATINI beradi."""
    due: list[_Due] = []
    debounce_before = moment - timedelta(minutes=DEBOUNCE_MINUTES)
    escalate_before = moment - timedelta(hours=ESCALATION_HOURS)

    async with _tenant_session(sessionmaker, market_id=market_id, request_id=request_id) as session:
        seen: set[tuple[str, UUID | None]] = set()
        for signal in signals:
            if signal.key not in STORABLE_ALERT_KEYS:  # pragma: no cover - reyestr darvozasi
                continue
            seen.add((signal.key, signal.subject_id))
            row = await _upsert(session, market_id=market_id, signal=signal)
            result.raised += 1

            escalated = (
                row.severity == AlertSeverity.WARNING.value and row.first_seen_at <= escalate_before
            )
            if escalated:
                await session.execute(
                    update(AlertEvent)
                    .where(AlertEvent.market_id == market_id, AlertEvent.id == row.id)
                    .values(severity=AlertSeverity.CRITICAL.value)
                )
                result.escalated += 1

            never_suppressed = signal.key in NEVER_SUPPRESSED_ALERT_KEYS
            fresh = row.notified_at is None or row.notified_at <= debounce_before
            if escalated or fresh or never_suppressed:
                due.append(
                    _Due(
                        alert_id=row.id,
                        key=signal.key,
                        severity=(AlertSeverity.CRITICAL.value if escalated else row.severity),
                        occurrences=row.occurrences,
                        first_seen_at=row.first_seen_at,
                        detail=signal.detail,
                        kind="escalated" if escalated else "raised",
                    )
                )
            else:
                result.suppressed += 1

        # --- Tiklanish: manbasi yo'qolgan OCHIQ alertlar ------------------
        open_rows = (
            await session.execute(
                select(AlertEvent.id, AlertEvent.alert_key, AlertEvent.subject_id)
                .where(AlertEvent.market_id == market_id)
                .where(text(ALERT_OPEN_PREDICATE))
            )
        ).all()
        for row in open_rows:
            if (row.alert_key, row.subject_id) in seen:
                continue
            await session.execute(
                update(AlertEvent)
                .where(AlertEvent.market_id == market_id, AlertEvent.id == row.id)
                .values(resolved_at=func.now())
            )
            result.resolved += 1
            due.append(
                _Due(
                    alert_id=None,
                    key=RECOVERED_KEY,
                    severity=AlertSeverity.INFO.value,
                    occurrences=1,
                    first_seen_at=None,
                    detail=_detail(error_code=row.alert_key),
                    kind="resolved",
                )
            )

    return due


async def _upsert(session: AsyncSession, *, market_id: UUID, signal: _Signal) -> Any:
    """Ochiq alertni yaratadi yoki uning TAKRORINI sanaydi.

    ⚠⚠ DEBOUNCE NING YAGONA DB KAFOLATI — QISMAN UNIQUE INDEKS. `ON
       CONFLICT` ifodasi indeksning AYNAN o'zidan (`ALERT_OPEN_EXPR` +
       `ALERT_OPEN_PREDICATE`) quriladi, ya'ni ular jimgina ajralib keta
       olmaydi. Qo'lda yozilgan `SELECT ... THEN INSERT` ikki parallel
       supurgida ikkalasi ham bo'sh holatni ko'rardi va bitta muammo uchun
       IKKITA ochiq qator tug'ilardi.

    ⚠ `first_seen_at` YANGILANMAYDI — u eskalatsiya arifmetikasining
      langari. `last_seen_at` esa DB SOATIDAN.
    """
    statement = pg_insert(AlertEvent).values(
        market_id=market_id,
        alert_key=signal.key,
        severity=ALERT_META[signal.key].severity,
        subject_id=signal.subject_id,
        detail=signal.detail,
    )
    upsert = statement.on_conflict_do_update(
        index_elements=[AlertEvent.market_id, AlertEvent.alert_key, text(ALERT_OPEN_EXPR)],
        index_where=text(ALERT_OPEN_PREDICATE),
        set_={
            # ⚠ BO'G'ILGAN TAKROR YO'QOLMAYDI — u shu yerda sanaladi va UI
            #   uni «So'nggi soatda yana N marta» qatori bilan ko'rsatadi
            #   (2-qoida).
            "occurrences": AlertEvent.__table__.c.occurrences + 1,
            "last_seen_at": func.now(),
            "detail": statement.excluded.detail,
        },
    ).returning(
        AlertEvent.id,
        AlertEvent.severity,
        AlertEvent.occurrences,
        AlertEvent.first_seen_at,
        AlertEvent.notified_at,
    )
    return (await session.execute(upsert)).one()


async def raise_alert(
    session: AsyncSession,
    *,
    market_id: UUID,
    key: str,
    subject_id: UUID | None = None,
    **detail: Any,
) -> None:
    """SUPURGIDAN TASHQARIDAGI yagona alert ochish yuzasi (7-faza, D-26b).

    =======================================================================
    ⛔⛔ NEGA BU FUNKSIYA BOR — VA NEGA U `_upsert()` NI QAYTA YOZMAYDI.

    Supurgi (`alert_sweep`) alertni SIGNALDAN tug'diradi: u holatni
    o'qiydi va «hozir shu muammo bor» degan xulosaga keladi. D-26(b) esa
    HODISA — u `resolve()` ning bir shoxida, so'rov yo'lida yuz beradi va
    keyingi supurgi uni QAYTA TOPA OLMAYDI (moslik telefon bilan
    qidirilgan, hech qayerda saqlanmagan). Ya'ni bu yo'l uchun supurgi
    NAMUNASI mavjud emas.

    Qolgan yagona savol — qatorni KIM yozadi. `_upsert()` ni qayta yozish
    TAQIQLANADI va sabab uning O'Z docstringida: debounce ning yagona DB
    kafolati — qisman UNIQUE indeks, va `ON CONFLICT` ifodasi indeksning
    AYNAN o'zidan quriladi. Qo'lda yozilgan `SELECT ... THEN INSERT` ikki
    parallel chaqiruvda ikkalasi ham bo'sh holatni ko'rardi va bitta
    muammo uchun IKKITA ochiq qator tug'ilardi.

    ⚠ BU `alert_repo` NING «YOZISH METODI YO'Q» QOIDASINI BUZMAYDI. O'sha
      qoida FOYDALANUVCHI yuzasi haqida: `POST`/`PATCH`/`DELETE /alerts`
      marshruti yo'q va qo'lda yopish tugmasi qurilmaydi (T-04-73 regex
      darvozasi). Bu yerda foydalanuvchi ham, marshrut ham yo'q — chaqiruv
      `/internal/*` ostidagi servis-servis yo'lidan keladi.
    =======================================================================

    ⛔ `detail` `_detail()` ALLOWLISTIDAN o'tadi (D-19): ro'yxatdan
       tashqari kalit `ValueError` beradi. Telefon raqami yoki sotuvchi
       ismi uchun ruxsat etilgan kalit YO'Q va qo'shilmaydi.

    ⚠ SESSIYADA TENANT KONTEKSTI O'RNATILGAN BO'LISHI SHART: `alert_events`
      RLS `FORCE` ostida va kontekstsiz `INSERT` `WITH CHECK` da
      yiqilardi.
    """
    if key not in ALERT_META:  # pragma: no cover - reyestr darvozasi
        raise KeyError(f"`ALERT_META` da ro'yxatga olinmagan alert kaliti: {key!r}")
    await _upsert(
        session,
        market_id=market_id,
        signal=_Signal(key, subject_id, _detail(**detail)),
    )


# ===========================================================================
# XABAR — guruhlangan, rasmsiz, bloklamaydigan
# ===========================================================================


async def _notify(
    sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    *,
    market_id: UUID,
    request_id: str,
    due: Sequence[_Due],
    moment: datetime,
    result: SweepResult,
    platform: bool = False,
) -> None:
    """BITTA guruhlangan xabar yuboradi va `notified_at` ni yangilaydi.

    ⛔ XATO YUTILADI VA ALOHIDA, QISQA TRANZAKSIYADA (`discovery.py:529-556`
       naqshi). Telegram yiqilsa `alert_events` qatori BARIBIR yozilgan
       bo'ladi va `notified_at` `NULL` bo'lib qoladi — UI aynan shu
       holatni «Telegram xabari YUBORILMADI» deb ko'rsatadi va uni
       YASHIRMAYDI (3-qoida va `04-UI-SPEC.md` §6.7).

    ⛔ XABARDA RASM YO'Q (D-19). Matn faqat kalitlar va sonlardan quriladi;
       `AlertSender` da rasm biriktiruvchi metodning O'ZI mavjud emas.
    """
    text_body = _compose(due, moment=moment, platform=platform)
    try:
        delivered = await sender.send_message(text_body)
    except Exception as exc:  # noqa: BLE001 - kuzatuv vositasi tizimni yiqita olmaydi
        _swallow(result, "alert_send_crashed", exc, market_id=market_id)
        return

    if not delivered:
        # `notified_at` `NULL` bo'lib QOLADI — «alert bor deb o'ylash»
        # yolg'oni aynan shu yerda tug'ilardi.
        return

    result.notified += 1
    ids = [item.alert_id for item in due if item.alert_id is not None]
    if not ids:
        return
    try:
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            await session.execute(
                update(AlertEvent)
                .where(AlertEvent.market_id == market_id, AlertEvent.id.in_(ids))
                .values(notified_at=func.now())
            )
    except SQLAlchemyError as exc:
        _swallow(result, "alert_notified_at_not_written", exc, market_id=market_id)


def _compose(due: Sequence[_Due], *, moment: datetime, platform: bool) -> str:
    """Guruhlangan xabar matni — HAR KALIT BIR MARTA, soni bilan.

    ⚠ MATN i18n KALITLARIDAN quriladi, tarjimadan emas: bu xabar
      platforma admini uchun va u operatsion, foydalanuvchi matni emas.
      Tarjima UI tomonida (`04-UI-SPEC.md` §11.9).
    """
    scope = "PLATFORMA" if platform else "BOZOR"
    lines = [f"[{scope}] {moment.strftime('%Y-%m-%d %H:%M')}"]
    for item in sorted(due, key=lambda entry: entry.key):
        parts = [f"- {item.key} ({item.severity})"]
        if item.occurrences > 1:
            parts.append(f"x{item.occurrences}")
        if item.first_seen_at is not None:
            age = int((moment - item.first_seen_at).total_seconds() // 60)
            parts.append(f"{age} daq")
        if item.detail:
            parts.append(" ".join(f"{key}={value}" for key, value in sorted(item.detail.items())))
        lines.append(" · ".join(parts))
    return "\n".join(lines)


# ===========================================================================
# KUNLIK DAYJEST — asosiy kuzatuv sirti, alertlar emas
# ===========================================================================


async def daily_digest(
    sessionmaker: async_sessionmaker[AsyncSession],
    sender: AlertSender,
    *,
    business_date: date,
) -> DigestResult:
    """Har bozor uchun BITTA kunlik xulosa xabari.

    =====================================================================
    BU YAGONA XABAR KUNLIK HOLATNING 90 % INI BERADI.

    To'g'ri sozlangan tizimda ALERT KAMDAN-KAM KELADI — va aynan shu
    narsa uni ishonchli qiladi. Dayjest esa HAR KUNI keladi, ya'ni uning
    KELMAGANI ham signal: bu «insonga tayangan» dead-man's switch
    pog'onasi (§E.12) va u butun stek o'lik bo'lgan holatni qoplaydi.
    Narxi nolga yaqin, ishonchliligi zaif — ikkalasi ham ochiq yozilgan
    (`ops/docs/monitoring.md`).
    =====================================================================

    ⛔ RASM YO'Q, HAVOLA YO'Q (D-19) — faqat sonlar.
    """
    request_id = f"job-digest-{business_date.isoformat()}"
    result = DigestResult()

    try:
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        log.exception("daily_digest_market_list_failed")
        return result
    result.markets = len(market_ids)

    for market_id in market_ids:
        try:
            async with _tenant_session(
                sessionmaker, market_id=market_id, request_id=request_id
            ) as session:
                summary = await CaptureRepository(session, market_id).day_summary(business_date)
                stored = (
                    await session.execute(
                        select(func.coalesce(func.sum(Snapshot.size_bytes), 0)).where(
                            Snapshot.market_id == market_id,
                            Snapshot.business_date == business_date,
                        )
                    )
                ).scalar_one()
        except SQLAlchemyError as exc:
            _swallow(result, "daily_digest_read_failed", exc, market_id=market_id)
            continue

        body = (
            f"[DAYJEST] {business_date.isoformat()} · {market_id}\n"
            f"kadrlar: {summary.done}/{summary.planned}\n"
            f"ok={summary.ok} dark={summary.dark} blank={summary.blank} "
            f"corrupt={summary.corrupt}\n"
            f"failed={summary.failed} missed={summary.missed}\n"
            f"ombor: {int(stored)} bayt"
        )
        try:
            if await sender.send_message(body):
                result.sent += 1
        except Exception as exc:  # noqa: BLE001 - dayjest jobni yiqita olmaydi
            _swallow(result, "daily_digest_send_crashed", exc, market_id=market_id)

    log.info("daily_digest_done", markets=result.markets, sent=result.sent)
    return result


# ===========================================================================
# Yurak urishi va xato yutish
# ===========================================================================


def _swallow(
    result: SweepResult | DigestResult,
    event: str,
    exc: Exception,
    *,
    market_id: UUID,
) -> None:
    """Xatoni YUTADI va uni SANOQQA aylantiradi — MATNINI EMAS, TURINI.

    Istisno matni ombor manzilini yoki bot tokenini tashishi mumkin
    (04-06 va T-04-59 ning o'lchovlari).
    """
    name = type(exc).__name__
    result.errors.append(f"{event}:{name}")
    log.warning(event, market_id=str(market_id), error=name)


async def _write_heartbeat(
    component: str,
    sessionmaker: async_sessionmaker[AsyncSession],
    detail: dict[str, Any],
) -> None:
    """`system_heartbeats[component]` — ALOHIDA, QISQA tranzaksiya.

    ⚠ `except Exception` — `SQLAlchemyError` EMAS. Sabab 04-07 da
      o'lchangan: yangi ulanish ochilganda `socket.gaierror`
      `SQLAlchemyError` ga O'RALMAYDI va butun supurgini ENG OXIRIDA
      yiqitardi.
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
    except Exception as exc:  # noqa: BLE001 - yurak urishi supurgini yiqita olmaydi
        log.warning("alert_sweep_heartbeat_not_written", error=type(exc).__name__)
