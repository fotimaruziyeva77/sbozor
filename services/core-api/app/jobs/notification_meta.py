"""Chiquvchi xabarlarning REYESTRI — `alerting.py::ALERT_META` ning jufti.

=============================================================================
⛔⛔ BU FAYL «SOZLAMA» EMAS, U IKKI QARORNING YAGONA MANBAI.

  1. QAYSI xabar to'xtatilmaydi (D-18) — `never_suppressed`;
  2. QAYSI kalitlar `notification_outbox.payload` ga tushishi mumkin
     (Pitfall 6) — `payload_keys`.

Ikkalasi ham reyestrdan HOSILA qilinadi. Qo'lda yozilgan ikkinchi ro'yxat
BUGUN to'g'ri qiymat berardi va ertaga jimgina ajralib ketardi —
`alerting.py` ning `NEVER_SUPPRESSED_ALERT_KEYS` i aynan shu sababdan
metadan hosila qilingan va 04-04 ning sabotaji buni o'lchagan.
=============================================================================

=============================================================================
⛔ D-18 — KVITANSIYA HECH QACHON TO'XTATILMAYDI.

Sotuvchi soat 20:30 da to'ladi. Quiet oyna 21:00–08:00. Eslatma ertaga
kelishi TO'G'RI, kvitansiya esa YO'Q: u sotuvchining HOZIRGINA to'laganini
isbotlaydigan yozuv va uni ertaga surish nizo modelini (D-02) buzardi —
kassir «yozdim» deydi, sotuvchida esa hech qanday tasdiq yo'q.

⚠ PITFALL 7 NING ANIQ SHAKLI: quiet-hours filtri `WHERE` bandiga
  qo'yiladi va `kind` bo'yicha istisno UNUTILADI. Unutish jimgina bo'ladi
  — so'rov ishlayveradi, faqat kvitansiya navbatda tunab qoladi.
  Shuning uchun istisno bu yerda BAYROQ, `outbox_repo` da esa SQL
  parametri: bitta manba, ikkita ishlatilish joyi.
=============================================================================

=============================================================================
⛔ TAYYOR MATN BU FAYLDA HAM, QATORDA HAM YO'Q (Pitfall 6).

Reyestr faqat `kind` va RUXSAT ETILGAN KALITLARNI biladi. Matn jo'natish
paytida `kind` + `payload` dan quriladi va summa `sbozor_core.money.
format_soum()` bilan chiziladi — bu faylda YANGI formatlash yozilmaydi.

Sabab zanjiri: tayyor matn sotuvchining ismini, rasta kodini va summani
BAZAGA yozardi, u yerdan `pg_dump` -> restic -> TASHQI BUCKET ga chiqardi.
Chegara shuning uchun YOZISH paytida qo'yiladi (`outbox_payload()`), render
paytida emas.
=============================================================================

⚠ PUL — BUTUN SO'M (`BIGINT` <-> `int`, D-11). Bu faylda pul QIYMATI
  umuman saqlanmaydi: `payload_keys` faqat KALIT NOMLARINI biladi, ya'ni
  kasrli tip va yaxlitlash chaqiruvlari bu yerga tarqamaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any, Final

from sbozor_core.enums import OutboxKind, OutboxRecipientKind
from sbozor_core.models.notification import MarketNotificationSettings

__all__ = [
    "DEFAULT_OVERDUE_DAYS",
    "DEFAULT_QUIET_HOURS_END",
    "DEFAULT_QUIET_HOURS_START",
    "NEVER_SUPPRESSED_OUTBOX_KINDS",
    "NOTIFICATION_META",
    "OUTBOX_PAYLOAD_KEYS",
    "NotificationMeta",
    "is_quiet_now",
    "is_suppressed_now",
    "outbox_payload",
]


@dataclass(frozen=True, slots=True)
class NotificationMeta:
    """Bitta `OutboxKind` ning REYESTR yozuvi (`alerting.py::AlertMeta` jufti).

    ⚠ REYESTR YAGONA MANBA: `NEVER_SUPPRESSED_OUTBOX_KINDS` va
      `OUTBOX_PAYLOAD_KEYS` undan HOSILA qilinadi. Yozuvni o'zgartirish
      ikkala hosilani ham BIR VAQTDA yangilaydi, ya'ni ular ajrala olmaydi.
    """

    kind: str
    """`sbozor_core.enums.OutboxKind` a'zosining qiymati — LITERAL emas.

    Literal yozilganda enum a'zosi o'zgargan kuni reyestr jimgina
    ajralardi: `NOTIFICATION_META[kind]` `KeyError` berardi va u aynan
    jo'natish paytida, mahsulotda birinchi marta ko'rinardi.
    """

    never_suppressed: bool
    """⛔ D-18: quiet hours ham, throttling ham bu xabarni USHLAB QOLMAYDI."""

    recipient_kind: str
    """Kimga ketadi — `OutboxRecipientKind` DAN.

    Qiymat `recipient_matches_vendor` `CHECK` i bilan juftlashadi:
    `vendor` uchun `vendor_id` MAJBURIY, `market_director` uchun esa u
    BO'LMASLIGI shart. `outbox_repo.enqueue()` mosligini Python
    darajasida ham tekshiradi — DB xatosi «qaysi qator» ni aytadi,
    Python xatosi esa «kim noto'g'ri chaqirdi» ni.
    """

    payload_keys: frozenset[str]
    """⛔ ALLOWLIST, DENYLIST EMAS (`alerting.py::ALERT_DETAIL_KEYS` naqshi).

    Ro'yxatdan tashqari kalit UI'da ko'rinmasdi, lekin BAZAGA baribir
    yozilardi va u yerdan zaxiraga, zaxiradan esa tashqi bucketga
    chiqardi. Chegara shuning uchun YOZISH paytida (`outbox_payload()`).
    """


NOTIFICATION_META: Final[dict[str, NotificationMeta]] = {
    meta.kind: meta
    for meta in (
        # -------------------------------------------------------------
        # ⛔ 1. KVITANSIYA — YAGONA TO'XTATILMAYDIGAN XABAR (D-18, CASH-05)
        # -------------------------------------------------------------
        NotificationMeta(
            kind=OutboxKind.PAYMENT_RECEIPT.value,
            never_suppressed=True,
            recipient_kind=OutboxRecipientKind.VENDOR.value,
            # ⛔ `cashier_name` ATAYIN VA OCHIQ ro'yxat yozuvi sifatida
            #   kiritilgan (Open Question 2 / A8) — tasodifan emas.
            #
            #   CASH-05 ning matni «kassir» deydi va sabab nizoda (D-02):
            #   sotuvchi «kimga to'ladim?» degan savolga javob olishi
            #   kerak, aks holda kvitansiya dalil emas, faqat kvitansiya
            #   ko'rinishidagi son bo'lardi.
            #
            #   ⚠ QIYMAT `PERSONAL_FIELDS` A'ZOSI (`full_name`) VA BU
            #     D-05 NI BUZMAYDI: D-05 ning o'lchovi `PERSONAL_ROUTES`
            #     ustida, ya'ni `/api/v1/*` MARSHRUTLARI ustida yuradi.
            #     Outbox marshrut emas — ism HTTP javobiga umuman
            #     qaytmaydi, u faqat sotuvchining O'Z Telegram matniga
            #     tushadi. Ya'ni `PERSONAL_ROUTES` O'SMAYDI (G7-6).
            payload_keys=frozenset({"amount_soum", "stall_code", "paid_at", "cashier_name"}),
        ),
        # -------------------------------------------------------------
        # 2. QARZ ESLATMASI — QUIET HOURS GA BO'YSUNADI (BOT-03)
        # -------------------------------------------------------------
        NotificationMeta(
            kind=OutboxKind.OVERDUE_REMINDER.value,
            never_suppressed=False,
            recipient_kind=OutboxRecipientKind.VENDOR.value,
            payload_keys=frozenset({"outstanding_soum", "overdue_days", "oldest_service_date"}),
        ),
        # -------------------------------------------------------------
        # 3. DIREKTOR DAYJESTLARI — IKKI MANBA, IKKI MA'NO (D-15/D-16)
        # -------------------------------------------------------------
        # Ertalabki: KECHAGI YOZILGAN kun (`daily_charges` + `payments`).
        NotificationMeta(
            kind=OutboxKind.DIGEST_MORNING.value,
            never_suppressed=False,
            recipient_kind=OutboxRecipientKind.MARKET_DIRECTOR.value,
            payload_keys=frozenset(
                {
                    "business_date",
                    "charged_soum",
                    "collected_soum",
                    "occupancy_pct",
                    "top_debtor_count",
                    "case_new_count",
                }
            ),
        ),
        # Kechki: BUGUNGI KUTILAYOTGAN holat (`pending_projection()`).
        # ⛔ Ikki dayjestning sonlari BIR XIL BO'LMASLIGI — nuqson emas,
        #   DIZAYN (D-15): manbalar boshqa va matn buni ochiq aytadi.
        NotificationMeta(
            kind=OutboxKind.DIGEST_EVENING.value,
            never_suppressed=False,
            recipient_kind=OutboxRecipientKind.MARKET_DIRECTOR.value,
            payload_keys=frozenset(
                {
                    "business_date",
                    "expected_soum",
                    "collected_soum",
                    "unpaid_stall_count",
                    "anomaly_count",
                }
            ),
        ),
    )
}
"""`OutboxKind` ning YAGONA reyestri — to'rtala a'zo ham yozuvga ega.

⚠ TO'PLAM YOPIQ: enum a'zosi qo'shilib bu yerga yozuv yozilmasa
`outbox_payload()` va `outbox_repo.enqueue()` `KeyError` beradi — ya'ni
unutish JO'NATISH paytida emas, YOZISH paytida ko'rinadi.
"""

NEVER_SUPPRESSED_OUTBOX_KINDS: Final[frozenset[str]] = frozenset(
    kind for kind, meta in NOTIFICATION_META.items() if meta.never_suppressed
)
"""⛔ D-18 — quiet hours BU TURLARGA QO'LLANMAYDI.

METADAN HOSILA, qo'lda sanalmagan (`alerting.py::NEVER_SUPPRESSED_ALERT_KEYS`
bilan aynan bir xil shakl va aynan bir xil sabab).

Bu to'plam IKKI joyda ishlatiladi va ikkalasi ham SHU manbadan oziqlanadi:
`outbox_repo.claim()` ning SQL darvozasi (`kind = ANY(:never_suppressed)`)
va `test_outbox_policy.py` ning jadval testi. Uchinchi, qo'lda yozilgan
nusxa bugun `{"payment_receipt"}` berardi va ertaga — yangi
to'xtatilmaydigan tur qo'shilganda — jimgina eskirardi.
"""

OUTBOX_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
    key for meta in NOTIFICATION_META.values() for key in meta.payload_keys
)
"""BARCHA turlarning ruxsat etilgan kalitlari — reyestrdan HOSILA.

⚠ BU RO'YXAT `outbox_payload()` NING CHEGARASI EMAS. Chegara HAR TUR
UCHUN ALOHIDA (`NOTIFICATION_META[kind].payload_keys`): birlashma bilan
tekshirish `payment_receipt` ga `anomaly_count` yozishga ruxsat berardi
va matn quruvchisi o'sha kalitni umuman kutmasdi.

To'plam faqat STRUKTURAVIY darvozalar uchun: `tests/fixtures/
notification_domain.py::ALLOWED_PAYLOAD_KEYS` (07-04 ning VAQTINCHALIK
ro'yxati) shundan HOSILA qilinishi kerak — NUSXA emas.
"""

DEFAULT_QUIET_HOURS_START: Final[time] = time(21, 0)
"""[ASSUMED] A2 — quiet oynaning boshi, `Asia/Tashkent` devor-soati.

⚠ BU GLOBAL SOZLAMA EMAS, `COALESCE` NING IKKINCHI ARGUMENTI.
Haqiqiy sozlash nuqtasi — `market_notification_settings` jadvalidagi
QATOR (D-19: «yangi bozor kod yozmasdan wizard orqali ulanadi»). Qator
YO'Q bo'lishi QONUNIY holat va o'shanda o'quvchilar shu qiymatga
tushadi; qator BOR bo'lsa u USTUN keladi.

Sabab (A2): sotuvchilar erta boshlaydi — kadr olishning birinchi sloti
06:00. Eslatma savdo boshlanishidan OLDIN kelmasligi kerak, kechki
chegara esa oilaviy vaqtni himoya qiladi.

⚠ QIYMAT `models/notification.py` NING `server_default` I BILAN BIR XIL
va bu NUSXA emas, IKKI QATLAM: sxema xom SQL yo'lini qoplaydi, bu
konstanta esa sozlama qatori YO'Q bo'lgan bozorni. Ularning ajralishi
`test_outbox_repo.py` da o'lchanadi (sozlamasiz bozorning tanlovi).
"""

DEFAULT_QUIET_HOURS_END: Final[time] = time(8, 0)
"""[ASSUMED] A2 — quiet oynaning oxiri (`DEFAULT_QUIET_HOURS_START` jufti).

⚠ OYNA YARIM TUNNI KESIB O'TADI (`start > end`) va bu ATAYIN tanlangan
STANDART: shox SQL da OCHIQ yozilishi shart, aks holda `now BETWEEN
start AND end` shakli tunda HECH QACHON rost bo'lmasdi va quiet hours
amalda ISHLAMASDI — jimgina.
"""


def _schema_default_overdue_days() -> int:
    """Kechikish chegarasining kod standarti — ⛔ SXEMADAN HOSILA, literal EMAS.

    =========================================================================
    ⛔⛔ QIYMAT SHU YERDA QAYTA YOZILMAYDI. Uning yagona manbai —
       `MarketNotificationSettings.overdue_days` ning `server_default` i
       (A3, `models/notification.py` da sabablangan). Python tomonda
       literal yozilganda ikki standart JIMGINA ajralib ketardi: sozlama
       qatori BOR bozor bir chegarani, sozlamasi YO'Q bozor boshqasini
       olardi va IKKALASI HAM «standart» deb atalardi (D-32 ning aynan
       sinfi).

    ⚠ SHAKL BUZILSA FUNKSIYA YIQILADI, NOLGA TUSHMAYDI: jim standart
      qiymat chegarani bir kun jimgina o'chirib qo'yardi va nazoratchi
      navbati shovqinga aylanardi.
    =========================================================================
    """
    default = MarketNotificationSettings.__table__.c.overdue_days.server_default
    literal = getattr(getattr(default, "arg", None), "text", None)
    if literal is None:
        raise RuntimeError(
            "`market_notification_settings.overdue_days` ustunida o'qib "
            "bo'ladigan `server_default` yo'q — kechikish chegarasining kod "
            "standarti SXEMADAN olinadi va uni bu yerda literal bilan "
            "almashtirish ikkinchi standart yaratardi."
        )
    return int(literal)


DEFAULT_OVERDUE_DAYS: Final[int] = _schema_default_overdue_days()
"""[ASSUMED] A3 — qarz eslatmasi va case ochilishi uchun BIR knob (D-19).

Kichikroq qiymat case navbatini SHOVQINGA aylantirardi — bu
`alerting.py` ning D-22 bandidagi «75 ta xabar olgan admin
bildirishnomani o'chiradi» sinfi va u loyihada allaqachon bir marta
o'lchangan.

⛔ BOT-03 (sotuvchi eslatmasi) VA `recon.open` (case tug'ilishi) AYNAN
   SHU qiymatdan yuradi. Ikki alohida sozlama ajralib ketardi va
   sotuvchi eslatma OLMAGAN qarz uchun case ochilardi — ya'ni u
   ogohlantirilmagan holda navbatga tushardi.

=============================================================================
⛔⛔ QIYMAT LITERAL EMAS, SXEMADAN HOSILA — VA BU 07-13 DA TUZATILGAN
   D-32 NUQSONI.

07-06 bu konstantani `3` literali bilan yozgan, 07-07 esa
`app/jobs/reconciliation.py` da AYNI nomni sxemadan HOSILA qilib
e'lon qilgan. Ikkalasi merge bo'lgach bazada IKKI MUSTAQIL e'lon
qoldi: `market_notification_settings.overdue_days` ning
`server_default` i o'zgargan kuni bu nusxa JIMGINA eskirardi va
eslatma noto'g'ri kunda yonardi, holbuki case to'g'ri kunda ochilardi
— ya'ni bir knob ikkiga bo'linardi (D-19 ning aynan buzilishi).

⚠ YO'NALISH ATAYIN SHU TOMONGA: reyestr (bu modul) SXEMANI o'qiydi va
  u LEAF bo'lib qoladi. Teskarisi — bu modulning
  `app.jobs.reconciliation` dan import qilishi — `outbox_repo` ni
  `reconciliation_repo` ga tranzitiv bog'lab qo'yardi va
  `reconciliation_repo` bir kun outboxga yozadigan bo'lsa (case
  ochildi -> xabar) import HALQASI yopilardi.

⛔ KEYINGI QADAM (bu rejaning `files_modified` idan TASHQARIDA, shuning
   uchun BAJARILMADI): `app/jobs/reconciliation.py` o'zining
   `_schema_default_overdue_days()` ini o'chirib, `DEFAULT_OVERDUE_DAYS`
   ni SHU MODULDAN import qilishi kerak — o'shanda o'quvchi ham BITTA
   bo'ladi. Bugun manba bitta (sxema), o'quvchi ikkita va ularning
   ajralishi `test_notifications.py` da IKKI darvoza bilan qulflangan:
   qiymat tengligi VA har ikki modulda literal QAYTA PAYDO BO'LMASLIGI
   (AST bilan, grep bilan emas).
=============================================================================
"""


def is_quiet_now(moment: time, *, start: time, end: time) -> bool:
    """Devor-soati quiet oyna ICHIDAMI — oyna YARIM YOPIQ: `[start, end)`.

    =========================================================================
    ⛔ BU FUNKSIYA QOIDANING SPETSIFIKATSIYASI, JO'NATISH YO'LI EMAS.

    Haqiqiy darvoza `outbox_repo.claim()` ning SQL bandida va u SQL da
    bo'lishi SHART: oyna HAR BOZOR uchun `market_notification_settings`
    dan `LEFT JOIN` bilan olinadi, ya'ni qoidani Python tomonga ko'chirish
    butun navbatni xotiraga tortardi.

    ⚠ IKKI QATLAM — NAZORATSIZ EMAS. Ularning ajralishi
      `tests/integration/test_outbox_repo.py` da o'lchanadi: o'sha yerda
      HAQIQIY `claim()` natijasi shu funksiyaning bashorati bilan
      solishtiriladi, ya'ni SQL va spetsifikatsiya ayrilsa test qizaradi.
      Jadval testi esa (`tests/unit/test_outbox_policy.py`) qoidaning
      O'ZINI literal jadval bilan qulflaydi.
    =========================================================================

    ⛔ CHEGARALAR: `start` — ICHKARIDA, `end` — TASHQARIDA. Ikkalasini ham
       ichkariga olish 08:00 ni jimgina «tinch» qilardi va ertalabki
       eslatma bir daqiqa kechikardi; ikkalasini ham tashqariga chiqarish
       esa 21:00 da yuborishga ruxsat berardi.

    ⛔ `start == end` — OYNA BO'SH, ya'ni «tinch soat YO'Q». Teskari
       o'qish («butun sutka tinch») eslatmani AMALDA o'chirardi va
       direktor buni sozlama sifatida ko'rmasdi — u xabarlarning
       yo'qolishi bo'lib ko'rinardi.

    Args:
        moment: bozorning DEVOR-SOATI (`Asia/Tashkent`), UTC EMAS.
        start: oynaning boshi.
        end: oynaning oxiri.
    """
    if start == end:
        return False
    if start < end:
        return start <= moment < end
    # ⛔ YARIM TUNNI KESIB O'TISH — STANDART HOLAT (21:00 -> 08:00).
    #   `start <= moment < end` shakli bu oynada HECH QACHON rost
    #   bo'lmasdi va quiet hours JIMGINA ishlamay qolardi.
    return moment >= start or moment < end


def is_suppressed_now(kind: str, *, moment: time, start: time, end: time) -> bool:
    """Shu tur SHU paytda navbatda USHLAB QOLINADIMI (D-18 istisnosi bilan).

    ⛔ ISTISNO REYESTRDAN (`NEVER_SUPPRESSED_OUTBOX_KINDS`), qo'lda
       yozilgan `kind == "..."` solishtiruvidan EMAS. Literal solishtiruv
       bugun to'g'ri javob berardi va ertaga — yangi to'xtatilmaydigan tur
       qo'shilganda — jimgina eskirardi (Pitfall 7).
    """
    if kind in NEVER_SUPPRESSED_OUTBOX_KINDS:
        return False
    return is_quiet_now(moment, start=start, end=end)


def outbox_payload(kind: str, **values: Any) -> dict[str, Any]:
    """`notification_outbox.payload` ni ALLOWLIST ostida quradi (Pitfall 6).

    `alerting.py::_detail()` bilan AYNAN bir xil shakl va bir xil qattiqlik.

    ⚠ `ValueError` ATAYIN QATTIQ: ro'yxatdan tashqari kalit KODDAGI xato,
      ma'lumot xatosi emas. Jimgina o'tib ketsa tayyor matn (yoki
      sotuvchining ismi, yoki dalil havolasi) bazaga tushardi va u yerdan
      `pg_dump` -> restic -> TASHQI BUCKET zanjiriga kirardi.

    ⚠ CHEGARA HAR TUR UCHUN ALOHIDA (`OUTBOX_PAYLOAD_KEYS` emas, ya'ni
      birlashma emas): `payment_receipt` ga dayjestning kaliti kirsa matn
      quruvchisi uni umuman kutmasdi va xabar yarim bo'sh chiqardi.

    ⚠ `None` QIYMATLAR TASHLANADI (`_detail()` bilan bir xil qoida): bo'sh
      maydon `jsonb` da `null` bo'lib turishdan ko'ra UMUMAN bo'lmagani
      yaxshi — matn quruvchisi «kalit bormi?» degan BITTA savol bilan
      ishlaydi.

    Raises:
        KeyError: `kind` reyestrda bo'lmaganda (enumga a'zo qo'shilib
            reyestrga yozuv yozilmagan).
        ValueError: `payload` da o'sha tur uchun ruxsat etilmagan kalit
            bo'lganda.
    """
    allowed = NOTIFICATION_META[kind].payload_keys
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValueError(
            f"`{kind}` uchun ruxsat etilmagan payload kalit(lar)i: {unknown}. "
            f"Ruxsat etilganlari: {sorted(allowed)}. Chegara YOZISH paytida "
            "qo'yiladi: ro'yxatdan tashqari qiymat UI'da ko'rinmasdi, lekin "
            "bazaga, u yerdan zaxiraga va tashqi bucketga chiqardi (Pitfall 6)."
        )
    return {key: value for key, value in values.items() if value is not None}
