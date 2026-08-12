"""Bildirishnoma domenining seed'lari — `billing_domain.py` naqshi.

=============================================================================
⛔⛔ BU MODULNING ENG QIMMAT FUNKSIYASI — `seed_same_phone_in_two_markets()`.

`07-RESEARCH.md` Pitfall 10 buni raqam bilan yozgan: D-26(b) («bir nechta
moslik» -> ulanish YO'Q + anomaliya) testi BITTA bozorda **hech nimani
o'lchamaydi**, chunki `uq_vendors_market_id_phone_e164` (`models/market.py`)
bir bozor ichida ko'p moslikni **IMKONSIZ** qiladi.

Ya'ni «ko'p moslik» holati faqat **BOZORLAR ARO** yuz beradi va uni
o'lchashning yagona yo'li — `TwoMarketSeed` ustiga qurilgan seed. Usiz
07-08 ning testi yashil bo'lib turadi va **hech nimani isbotlamaydi**
(5-fazaning W-2/W-3 darsi: darvoza o'lchayotgan holatning MAVJUDLIGINI
isbotlashi kerak).

Shuning uchun o'sha funksiya **O'Z-O'ZINI TEKSHIRADI**: qaytishdan oldin
ikkala bozorda ham qator borligini va telefonlar TENG ekanini assert
qiladi. Seed jimgina buzilsa test emas, **fixture** qizaradi — va xato
xabari sababni ko'rsatadi.
=============================================================================
FIXTURE MAHSULOT QOIDASINI BUZA OLMAYDI — UCH JOYDA MEXANIK RAVISHDA.

  1. `seed_case()` `subject_kind` ni CHAQIRUVCHIDAN OLMAYDI — u nishondan
     HOSILA. Noto'g'ri juftlik (`subject_kind='anomaly'` + `charge_id`)
     seed qilingan bo'lsa, `ck_reconciliation_cases_subject_kind_matches_
     target` uni baribir rad etardi, lekin xato SEED paytida emas,
     TEST ichida chiqardi va sabab kod nuqsoni kabi ko'rinardi.
  2. `seed_case()` XOR ni O'ZI majburlaydi (`ValueError`): ikkala nishon
     ham berilgan yoki birortasi ham berilmagan chaqiruv DB'ga umuman
     yetib bormaydi.
  3. `seed_outbox_row()` `payload` kalitlarini ALLOWLIST bilan cheklaydi.
     Sabab Pitfall 6: tayyor matn (yoki dalil havolasi) `payload` ga
     kalit bo'lib kirsa, u ustun EMAS — ya'ni `07-04` ning G7-2 darvozasi
     uni KO'RMASDI, `pg_dump` -> restic -> tashqi bucket zanjiri esa uni
     baribir olib chiqardi.
=============================================================================
⚠ FIXTURE `app` IMPORTIGA BOG'LANMAYDI (`billing_domain.py` bilan bir xil
chegara): faqat xom SQL va `sbozor_core.enums` / `sbozor_core.phone`.
Enum QIYMATLARI — DB kontenti, ilova mantig'i emas.

⚠ SEED `sbozor_owner` AUTOCOMMIT ulanishi bilan yoziladi: ma'lumot
boshqa ulanishdagi (`sbozor_app`) testlarga DARHOL ko'rinishi shart.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Final
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.enums import (
    OutboxKind,
    OutboxRecipientKind,
    OutboxStatus,
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
)
from sbozor_core.phone import normalize_phone

from fixtures.two_markets import TwoMarketSeed, cleanup_two_markets, seed_two_markets

__all__ = [
    "ALLOWED_PAYLOAD_KEYS",
    "CLEANUP_ORDER",
    "DEFAULT_TELEGRAM_USER_ID",
    "TwoMarketPhoneSeed",
    "cleanup_case_targets",
    "cleanup_notification_domain",
    "cleanup_same_phone_in_two_markets",
    "seed_binding",
    "seed_case",
    "seed_case_event",
    "seed_no_coverage_anomaly",
    "seed_notification_settings",
    "seed_outbox_row",
    "seed_same_phone_in_two_markets",
]

DEFAULT_TELEGRAM_USER_ID: Final[int] = 7_600_000_000
"""Standart Telegram identifikatori — ⛔ `2**31` DAN KATTA.

`2**31 - 1` = 2 147 483 647 va Telegram ning haqiqiy identifikatorlari bu
chegaradan ALLAQACHON oshib ketgan. Ustun `BIGINT` deb e'lon qilingan
(`models/notification.py`), lekin STANDART SEED QIYMATI ham katta bo'lishi
SHART: 32-bit diapazondagi qiymat bilan yozilgan test `INTEGER` ga
qaytarilgan ustunni ham o'tkazib yuborardi — ya'ni tip qarori faqat
migratsiyada qolib, test darajasida umuman sinalmasdi.

⚠ QIYMAT BIR XIL BO'LGANI UCHUN BIR BOZORDA IKKI FAOL BOG'LANISHGA
YARAMAYDI: `uq_vendor_telegram_bindings_telegram_active` (qisman UNIQUE)
uni rad etadi. Bir necha bog'lanish kerak bo'lganda chaqiruvchi
`telegram_user_id` ni ANIQ beradi — va bu yaxshi, chunki o'sha holatda
qaysi akkaunt qaysi sotuvchiga tegishli ekani testda KO'RINADI.
"""

ALLOWED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "amount_soum",
        "stall_code",
        "created_at",
        "service_date",
        "overdue_days",
        "total_due_soum",
    }
)
"""⛔ `payload` GA YOZISH MUMKIN BO'LGAN KALITLAR — Pitfall 6 ning fixture yarmi.

`notification_outbox` da tayyor MATN ustuni yo'q (G7-2 uni
`information_schema` to'plam tengligi bilan qulflaydi), lekin `payload`
`jsonb` — ya'ni matnni USTUN sifatida emas, KALIT sifatida kiritish yo'li
ochiq qolardi va darvoza uni KO'RMASDI. O'sha kalit sotuvchining ismini
va summasini bazaga yozardi, u yerdan `pg_dump` -> restic -> TASHQI
BUCKET ga chiqardi.

Shuning uchun bu fixture ham xuddi mahsulot kodi kabi allowlist bilan
ishlaydi: ro'yxatdan tashqari kalit `ValueError` beradi — «kodda xato,
ma'lumot xatosi emas» (`alerting.py::_detail()` naqshi).

⚠ BU RO'YXAT VAQTINCHALIK VA U 07-05 DA O'RNINI BO'SHATADI: haqiqiy
manba `NOTIFICATION_META[<kind>].payload_keys` bo'ladi (har `kind` uchun
O'Z ro'yxati). O'sha kun kelganda bu konstanta undan HOSILA qilinishi
kerak, NUSXA emas — aks holda ikki ro'yxat jimgina ajralib ketardi
(D-32 ning aynan sinfi).
"""

CLEANUP_ORDER: tuple[str, ...] = (
    "reconciliation_case_events",
    "reconciliation_cases",
    "notification_outbox",
    "vendor_telegram_bindings",
    "market_notification_settings",
)
"""Bildirishnoma jadvallarining O'CHIRISH TARTIBI — FK bo'yicha bolalardan yuqoriga.

⚠ REYESTRDAN (`migrations.entities.NOTIFICATION_DELETE_ORDER`) IMPORT
QILINMAYDI va bu ATAYIN (`billing_domain.CLEANUP_ORDER` bilan aynan bir
xil qaror): `tests/fixtures/` `migrations` paketiga bog'lanmaydi, va —
muhimrog'i — reyestrdan olingan ro'yxat reyestrning O'ZI xato bo'lganda
test bilan BIRGA xato bo'lardi, ya'ni tozalash darvozasi o'z manbasini
tekshirgan bo'lardi.

⚠ `reconciliation_case_events` BIRINCHI: u `reconciliation_cases` ga
kompozit FK bilan tayanadi. Qolgan uchtasi o'zaro bog'lanmagan — ular
faqat `markets` va `vendors` ga qaraydi.
"""

# ---------------------------------------------------------------------------
# XOM SQL — jadval nomlari LITERAL (`financial.py` da o'rnatilgan qoida)
# ---------------------------------------------------------------------------

_INSERT_ANOMALY = (
    "INSERT INTO billing_anomalies (id, market_id, kind, stall_id, service_date) "
    "VALUES (%s, %s, %s, %s, %s)"
)

_INSERT_CASE = (
    "INSERT INTO reconciliation_cases "
    "(id, market_id, subject_kind, anomaly_id, charge_id, service_date, status, "
    " assignee_user_id, resolution_note) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

_INSERT_CASE_EVENT = (
    "INSERT INTO reconciliation_case_events "
    "(id, market_id, case_id, from_status, to_status, actor_user_id, note) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)

_INSERT_OUTBOX = (
    "INSERT INTO notification_outbox "
    "(id, market_id, kind, recipient_kind, vendor_id, dedupe_key, payload, status, "
    " attempt_count, next_attempt_at) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, now()))"
)
"""⚠ `next_attempt_at` `COALESCE(..., now())` BILAN, Python `datetime.now()`
BILAN EMAS: standart qiymat SERVER soatidan kelishi kerak. Test jarayoni
va Postgres konteyneri turli soat mintaqalarida bo'lishi mumkin va o'sha
farq «tik qatorni ko'rmadi» shaklidagi flaky testni tug'dirardi."""

_INSERT_BINDING = (
    "INSERT INTO vendor_telegram_bindings "
    "(id, market_id, vendor_id, telegram_user_id, revoked_at, revoked_reason) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)

_INSERT_SETTINGS = (
    "INSERT INTO market_notification_settings (market_id, overdue_days, director_chat_id) "
    "VALUES (%s, %s, %s)"
)

_INSERT_VENDOR = (
    "INSERT INTO vendors (id, market_id, full_name, phone_e164) VALUES (%s, %s, %s, %s)"
)

_VENDORS_BY_PHONE = "SELECT market_id, phone_e164 FROM vendors WHERE phone_e164 = %s"

_VENDOR_PHONE_COUNTER = 79_000_000
"""`two_markets._next_phone()` NING DIAPAZONIDAN TASHQARIDA boshlanadi.

O'sha hisoblagich `70 000 000` dan yuradi va `users.phone_e164` ni
to'ldiradi. Sotuvchi telefoni ALOHIDA diapazondan olinadi, ya'ni test
xatosini o'qiyotgan odam raqamga qarab uning QAYSI jadvaldan ekanini
darhol ajratadi. Ikkala diapazon ham `+9989 7…` prefiksini beradi — bu
haqiqiy O'zbekiston mobil prefiksi va `normalize_phone()` uni QABUL
QILADI (pastdagi `_next_vendor_phone()` da o'lchanadi).
"""


@dataclass(frozen=True)
class TwoMarketPhoneSeed:
    """IKKALA bozorda bir xil `phone_e164` bilan yozilgan ikki sotuvchi.

    D-26(b) ning YAGONA bajariladigan shakli — modul docstringining
    birinchi bandi.
    """

    markets: TwoMarketSeed
    phone_e164: str
    vendor_a_id: UUID
    vendor_b_id: UUID

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return (self.markets.market_a.id, self.markets.market_b.id)

    @property
    def vendor_ids(self) -> tuple[UUID, ...]:
        return (self.vendor_a_id, self.vendor_b_id)


def _next_vendor_phone() -> str:
    """Testlar orasida to'qnashmaydigan E.164 sotuvchi telefoni.

    ⛔ RAQAM `normalize_phone()` DAN O'TKAZILADI, QO'LDA YASALMAYDI.
    Fixture DB'ga to'g'ridan-to'g'ri yozadi (`vendors.phone_e164` da
    format `CHECK` i YO'Q — normalizatsiya CHEGARADA bajariladi), ya'ni
    qalbaki satr jimgina o'tib ketardi. O'shanda D-26 testlari mahsulot
    HECH QACHON ko'rmaydigan shakl ustidan yugurgan bo'lardi.
    """
    global _VENDOR_PHONE_COUNTER
    _VENDOR_PHONE_COUNTER += 1
    return normalize_phone(f"+9989{_VENDOR_PHONE_COUNTER:08d}")


def seed_no_coverage_anomaly(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    stall_id: UUID,
    service_date: date,
) -> UUID:
    """Case uchun QONUNIY nishon — `no_coverage_stall` anomaliyasi.

    =========================================================================
    ⚠ NEGA AYNAN SHU `kind` VA NEGA BOSHQASI EMAS.

    `billing_anomalies` da ikki juftlangan `CHECK` bor:

        (kind = 'no_coverage_stall') = (occupancy_event_id IS NULL)
        (occupancy_event_id IS NULL) = (snapshot_id IS NULL)

    Ya'ni AYNAN `no_coverage_stall` — dalil ustunlari `NULL` bo'lishi
    TALAB QILINADIGAN yagona sinf. Qolgan `kind` lar bandlik hodisasini
    VA kadrni talab qiladi, ular esa butun `occupancy_domain` +
    `snapshot_domain` zanjirini (kamera, zona, yugurish, sifat verdikti)
    olib kelardi — case testining narxi o'n barobar oshardi va u aslida
    bandlik qatlamini sinagan bo'lardi.

    ⛔ BU YERDA HECH QANDAY MAHSULOT QARORI QAYTA IXTIRO QILINMAYDI: case
    `no_coverage_stall` ga OCHILMAYDI (Pattern 4 — u kamera qamrovi
    nuqsoni, tushum nomuvofiqligi emas) va bu taqiq `recon.open` ning
    TANLOV SHARTIDA yashaydi, sxemada emas. Ya'ni bu funksiya sxema
    ruxsat beradigan, lekin mahsulot oqimi tug'dirmaydigan qatorni
    yasaydi — u faqat STRUKTURAVIY testlar (o'zgarmaslik, tozalash,
    kompozit FK) uchun.
    =========================================================================
    """
    anomaly_id = uuid4()
    conn.execute(
        _INSERT_ANOMALY,
        (str(anomaly_id), str(market_id), "no_coverage_stall", str(stall_id), service_date),
    )
    return anomaly_id


def seed_case(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    service_date: date,
    anomaly_id: UUID | None = None,
    charge_id: UUID | None = None,
    status: str = ReconciliationCaseStatus.NEW.value,
    assignee_user_id: UUID | None = None,
    resolution_note: str | None = None,
) -> UUID:
    """Bitta `reconciliation_cases` qatori — ⛔ IKKI SHOXLI VA XOR MAJBURIY.

    =========================================================================
    ⛔ `subject_kind` CHAQIRUVCHIDAN OLINMAYDI — U NISHONDAN HOSILA.

    Fixture DQ-5 ni BUZA OLMASLIGI kerak. Diskriminatorni argument qilish
    «`anomaly` deyman, lekin `charge_id` beraman» shaklidagi seed'ga yo'l
    ochardi va o'sha qator DB tomonidan rad etilardi — lekin xato SEED
    paytida emas, TESTNING o'rtasida chiqardi va sabab mahsulot nuqsoni
    kabi ko'rinardi.

    ⛔ XOR SHU YERDA HAM MAJBURLANADI (`ValueError`), FAQAT DB'DA EMAS.
    `ck_reconciliation_cases_subject_is_exclusive` ikkala nosozlikni ham
    rad etadi, lekin fixture darajasidagi tekshiruv XATONI CHAQIRUV
    JOYIDA ko'rsatadi. Bu ikkinchi himoya emas, BOSHQA QATLAMDAGI
    himoya: DB nima uchun rad etganini aytadi, fixture esa KIM noto'g'ri
    chaqirganini.

    Raises:
        ValueError: nishonlarning ikkalasi ham berilganda yoki
            birortasi ham berilmaganda.
    =========================================================================
    """
    if (anomaly_id is None) == (charge_id is None):
        raise ValueError(
            "`seed_case()` AYNAN BITTA nishon talab qiladi: `anomaly_id` YOKI "
            f"`charge_id` (berilgani: anomaly_id={anomaly_id!r}, "
            f"charge_id={charge_id!r}). Ikkalasi ham berilgan case ikki xil "
            "dalilga ishora qilardi, birortasi ham berilmagani esa umuman "
            "dalilsiz bo'lardi (DQ-5)."
        )

    subject_kind = (
        ReconciliationSubjectKind.ANOMALY.value
        if anomaly_id is not None
        else ReconciliationSubjectKind.OCCUPIED_UNPAID.value
    )
    case_id = uuid4()
    conn.execute(
        _INSERT_CASE,
        (
            str(case_id),
            str(market_id),
            subject_kind,
            str(anomaly_id) if anomaly_id is not None else None,
            str(charge_id) if charge_id is not None else None,
            service_date,
            status,
            str(assignee_user_id) if assignee_user_id is not None else None,
            resolution_note,
        ),
    )
    return case_id


def seed_case_event(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    case_id: UUID,
    to_status: str,
    from_status: str | None = None,
    actor_user_id: UUID | None = None,
    note: str | None = None,
) -> UUID:
    """Bitta `reconciliation_case_events` qatori — case tarixining bo'g'ini (D-14).

    ⚠ `from_status` STANDART `None` va bu «case TUG'ILDI» degani, «noma'lum»
      EMAS: birinchi hodisada oldingi holat FIZIK ravishda yo'q.
      `EVENT_STATUS_TRANSITION_CHECK` (`from_status IS DISTINCT FROM
      to_status`) nol o'tishni rad etadi, ya'ni `from_status=to_status`
      bilan chaqirish DB darajasida yiqiladi — bu QASDDAN: shovqin bilan
      to'lgan tarix «case necha marta qo'ldan qo'lga o'tdi?» savoliga
      noto'g'ri javob berardi.

    ⚠ `actor_user_id=None` = TIZIM (`recon.open` cron), «noma'lum» EMAS.
    """
    event_id = uuid4()
    conn.execute(
        _INSERT_CASE_EVENT,
        (
            str(event_id),
            str(market_id),
            str(case_id),
            from_status,
            to_status,
            str(actor_user_id) if actor_user_id is not None else None,
            note,
        ),
    )
    return event_id


def seed_outbox_row(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    kind: str = OutboxKind.PAYMENT_RECEIPT.value,
    recipient_kind: str | None = None,
    vendor_id: UUID | None = None,
    dedupe_key: str | None = None,
    payload: dict[str, Any] | None = None,
    status: str = OutboxStatus.PENDING.value,
    attempt_count: int = 0,
    next_attempt_at: datetime | None = None,
) -> UUID:
    """Bitta `notification_outbox` qatori (BOT-04, D-20/D-21).

    =========================================================================
    ⛔ `payload` ALLOWLIST BILAN CHEKLANADI — sabab `ALLOWED_PAYLOAD_KEYS`
       docstringida. Qisqasi: G7-2 USTUN nomlarini qo'riqlaydi, `payload`
       esa `jsonb` — ya'ni tayyor matn u yerga KALIT bo'lib kirsa darvoza
       uni KO'RMASDI.

    ⚠ `recipient_kind` STANDARTI `vendor_id` DAN HOSILA, lekin ARGUMENT
      bo'lib qoladi. Ikkisi ham kerak: hosila standart chaqiruvni qisqa
      qiladi, ochiq argument esa `recipient_matches_vendor` `CHECK` ini
      ATAYIN buzadigan (ya'ni uni O'LCHAYDIGAN) testni yozish imkonini
      beradi. Standartni majburiy qilish o'sha testni IFODALAB
      BO'LMAYDIGAN qilardi.

    ⚠ `dedupe_key` STANDARTI `"<kind>:<uuid>"` — mahsulotdagi shakl
      (`receipt:<payment_id>`) bilan bir xil, lekin HAR CHAQIRUVDA
      YANGI. Sobit standart `uq_notification_outbox_market_id_dedupe_key`
      tufayli ikkinchi chaqiruvni yiqitardi va D-21 ni o'lchamoqchi
      bo'lgan test o'z seed'ida qulab tushardi.

    Raises:
        ValueError: `payload` da allowlistdan tashqari kalit bo'lganda.
    =========================================================================
    """
    resolved_payload = {"amount_soum": 15_000, "stall_code": "A-01"} if payload is None else payload
    unknown = sorted(set(resolved_payload) - ALLOWED_PAYLOAD_KEYS)
    if unknown:
        raise ValueError(
            f"`payload` da allowlistdan tashqari kalit(lar): {unknown}. "
            f"Ruxsat etilganlari: {sorted(ALLOWED_PAYLOAD_KEYS)}. Tayyor matn "
            "yoki dalil havolasi `payload` ga KALIT bo'lib kirsa, G7-2 "
            "darvozasi (u USTUN nomlarini o'qiydi) uni KO'RMASDI — "
            "`pg_dump` -> restic -> tashqi bucket zanjiri esa uni baribir "
            "olib chiqardi (Pitfall 6)."
        )

    if recipient_kind is None:
        recipient_kind = (
            OutboxRecipientKind.VENDOR.value
            if vendor_id is not None
            else OutboxRecipientKind.MARKET_DIRECTOR.value
        )

    outbox_id = uuid4()
    conn.execute(
        _INSERT_OUTBOX,
        (
            str(outbox_id),
            str(market_id),
            kind,
            recipient_kind,
            str(vendor_id) if vendor_id is not None else None,
            dedupe_key if dedupe_key is not None else f"{kind}:{uuid4()}",
            json.dumps(resolved_payload),
            status,
            attempt_count,
            next_attempt_at,
        ),
    )
    return outbox_id


def seed_binding(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    vendor_id: UUID,
    telegram_user_id: int = DEFAULT_TELEGRAM_USER_ID,
    revoked_at: datetime | None = None,
    revoked_reason: str | None = None,
) -> UUID:
    """Bitta `vendor_telegram_bindings` qatori (D-26c/D-27).

    ⚠ `telegram_user_id` STANDARTI `2**31` DAN KATTA — sabab
      `DEFAULT_TELEGRAM_USER_ID` docstringida.

    ⚠ BEKOR QILISH JUFTLIKDA: `revoked_at` va `revoked_reason` ikkalasi
      birga beriladi yoki ikkalasi ham berilmaydi
      (`ck_vendor_telegram_bindings_revocation_is_paired`). Fixture buni
      QAYTA TEKSHIRMAYDI va bu ONGLI chegara: `seed_case()` dan farqli
      o'laroq bu yerda HOSILA qilinadigan qiymat yo'q (sabab matni faqat
      chaqiruvchiga ma'lum), ya'ni tekshiruv `CHECK` ning NUSXASI bo'lardi
      va ikkalasi jimgina ajralib ketishi mumkin edi.
    """
    binding_id = uuid4()
    conn.execute(
        _INSERT_BINDING,
        (
            str(binding_id),
            str(market_id),
            str(vendor_id),
            telegram_user_id,
            revoked_at,
            revoked_reason,
        ),
    )
    return binding_id


def seed_notification_settings(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    overdue_days: int = 3,
    director_chat_id: int | None = DEFAULT_TELEGRAM_USER_ID,
) -> None:
    """Bitta `market_notification_settings` qatori (D-19).

    ⚠ QATOR MAJBURIY EMAS (`market_id` PK, 1:1 va u YO'Q bo'lishi
      QONUNIY): o'quvchilar `COALESCE` bilan kod standartlariga tushadi.
      Shuning uchun bu seed HECH QAYERDA avtomatik chaqirilmaydi — uni
      faqat «sozlama BOR» shoxini o'lchayotgan test chaqiradi.

    ⛔⛔ `director_chat_id` NING MAHSULOT YO'LI — `POST /internal/bot/
       director/resolve` (07-18). BU SEED U EMAS va u bilan
       ALMASHTIRILMAYDI.

       Farq 07-VERIFICATION gap #1 da o'lchangan: `test_sc3` sozlama
       qatorini shu fixture bilan yozgan paytida YASHIL edi, holbuki
       ustunga yozadigan MAHSULOT yo'li butun repoda YO'Q edi — ya'ni
       produksiyada `resolve_chat_id()` har doim `None` qaytarardi va
       direktor dayjestni HECH QACHON olmasdi. Endi `test_sc3` o'sha
       marshrutga boradi va natijani BAZADAN o'qiydi; bu fixture esa
       `overdue_days` (D-19) shoxi uchun qoladi.

    ⚠ `quiet_hours_*` ATAYIN ARGUMENT EMAS: ikkala ustun ham
      `server_default` bilan keladi va standartning O'ZI [ASSUMED] qaror
      (A2). Fixture ularni qayta yozsa, testlar mahsulot standartini
      emas, fixture'ning nusxasini o'lchagan bo'lardi.
    """
    conn.execute(_INSERT_SETTINGS, (str(market_id), overdue_days, director_chat_id))


def seed_same_phone_in_two_markets(conn: Connection[TupleRow]) -> TwoMarketPhoneSeed:
    """⛔⛔ D-26(b) NING YAGONA BAJARILADIGAN SHAKLI — modul docstringiga qarang.

    =========================================================================
    IKKALA BOZORGA AYNAN BIR XIL `phone_e164` BILAN BITTA SOTUVCHI YOZADI.

    `uq_vendors_market_id_phone_e164` bir bozor ICHIDA ko'p moslikni
    IMKONSIZ qiladi, ya'ni «bir nechta moslik» shoxi faqat BOZORLAR ARO
    yuz beradi. Bitta bozorli seed bilan yozilgan D-26(b) testi YASHIL
    bo'lib turadi va HECH NIMANI o'lchamaydi (Pitfall 10).

    ⛔ FUNKSIYA O'Z-O'ZINI TEKSHIRADI: qaytishdan oldin bazadan o'qib,
    (a) AYNAN 2 qator borligini, (b) ular IKKI XIL bozorda ekanini va
    (c) saqlangan telefonlar TENG ekanini assert qiladi. Seed jimgina
    buzilsa (masalan `INSERT` `ON CONFLICT DO NOTHING` bilan yozilsa)
    TEST emas, FIXTURE qizaradi — va bu farq muhim: fixture xatosi
    «o'lchov asbobi buzuq» degani, test xatosi esa «mahsulot buzuq».
    =========================================================================
    """
    markets = seed_two_markets(conn)
    phone = _next_vendor_phone()
    vendor_a_id, vendor_b_id = uuid4(), uuid4()

    for vendor_id, market in ((vendor_a_id, markets.market_a), (vendor_b_id, markets.market_b)):
        conn.execute(
            _INSERT_VENDOR,
            (str(vendor_id), str(market.id), f"{market.name} sotuvchisi", phone),
        )

    rows = conn.execute(_VENDORS_BY_PHONE, (phone,)).fetchall()
    found = {UUID(str(row[0])): str(row[1]) for row in rows}
    expected_markets = {markets.market_a.id, markets.market_b.id}

    assert len(rows) == 2, (
        f"`{phone}` telefoni bilan {len(rows)} qator topildi, kutilgani 2. "
        "D-26(b) ning «bir nechta moslik» shoxi AYNAN ikki qator bilan "
        "ifodalanadi — bittasi bilan test hech nimani o'lchamasdi."
    )
    assert set(found) == expected_markets, (
        f"qatorlar kutilgan bozorlarda emas: {sorted(map(str, found))} "
        f"(kutilgani {sorted(map(str, expected_markets))}). Ikkala qator "
        "BIR bozorda bo'lsa `uq_vendors_market_id_phone_e164` ularni "
        "baribir rad etardi, ya'ni bu holat seed'ning buzilganini bildiradi."
    )
    assert set(found.values()) == {phone}, (
        f"saqlangan telefonlar TENG emas: {sorted(set(found.values()))}. "
        "Moslik telefon bo'yicha qidiriladi, ya'ni farqli satrlar bilan "
        "D-26(b) shoxi HECH QACHON bajarilmasdi."
    )

    return TwoMarketPhoneSeed(
        markets=markets,
        phone_e164=phone,
        vendor_a_id=vendor_a_id,
        vendor_b_id=vendor_b_id,
    )


def cleanup_notification_domain(conn: Connection[TupleRow], *, market_ids: list[UUID]) -> None:
    """Beshala bildirishnoma jadvalini `market_id` bo'yicha tozalaydi.

    =========================================================================
    ⚠ AVVAL BOZORLAR QORALAMAGA QAYTARILADI VA BUSIZ TOZALASH YIQILADI.

    `0023` `reconciliation_case_events` ga SHARTSIZ o'zgarmaslik
    qo'riqchisini qo'yadi va u `DELETE` ni FAQAT bozor NOFAOL bo'lganda
    o'tkazadi (`market_delete_draft()` ning yo'li). Faol bozorda birinchi
    `DELETE` darhol `P0001` bilan yiqilardi.

    Naqsh YANGI EMAS: `cleanup_billing_domain()` va
    `cleanup_market_domain()` aynan shu qadamni 02-04 dan beri bajaradi.
    Bayroqni tushirish semantik jihatdan HALOL: qatorlar bir necha satr
    keyin butunlay o'chiriladi va bozorlarni quyi qatlamlar baribir
    o'chiradi.

    ⛔ `billing_anomalies` BU YERDA TOZALANMAYDI va bu ATAYIN: case
    NISHONI billing domenida yashaydi va uni bu funksiyaga qo'shish
    `billing_domain` seed'ining qatorlarini ham jimgina o'chirardi.
    Nishonlar uchun `cleanup_case_targets()` bor.
    =========================================================================
    """
    ids = [str(market_id) for market_id in market_ids]
    if not ids:
        return

    conn.execute("UPDATE markets SET is_active = false WHERE id = ANY(%s::uuid[])", (ids,))
    for table in CLEANUP_ORDER:
        # Jadval nomlari shu moduldagi SOBIT `CLEANUP_ORDER` dan keladi —
        # tashqi kirish emas, ya'ni f-string bu yerda xavfsiz
        # (`billing_domain.py` dagi jufti bilan bir xil naqsh).
        conn.execute(
            f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
            (ids,),
        )


def cleanup_case_targets(conn: Connection[TupleRow], *, market_ids: list[UUID]) -> None:
    """`seed_no_coverage_anomaly()` yozgan qatorlarni o'chiradi.

    ⛔ ALOHIDA FUNKSIYA VA U `cleanup_notification_domain()` DAN KEYIN
      chaqiriladi: `reconciliation_cases` anomaliyaga kompozit FK bilan
      tayanadi (`ondelete` YO'Q, ya'ni NO ACTION) — case'i bor
      anomaliyani o'chirish RAD ETILADI.

    ⚠ TOZALASH `market_id` BO'YICHA: agar shu bozorda `billing_domain`
      seed'i ham anomaliya yozgan bo'lsa, ular ham o'chadi. Shuning uchun
      bu funksiya faqat bildirishnoma testlarining O'Z bozorlarida
      chaqiriladi — billing seed'i bilan bir testda ARALASHTIRILMAYDI.
    """
    ids = [str(market_id) for market_id in market_ids]
    if not ids:
        return
    conn.execute("DELETE FROM billing_anomalies WHERE market_id = ANY(%s::uuid[])", (ids,))


def cleanup_same_phone_in_two_markets(conn: Connection[TupleRow], seed: TwoMarketPhoneSeed) -> None:
    """`seed_same_phone_in_two_markets()` ni to'liq qaytaradi.

    ⚠ TARTIB: sotuvchilar AVVAL, bozorlar KEYIN. `vendors` `markets` ga
      FK bilan tayanadi, ya'ni teskari tartibda `cleanup_two_markets()`
      ning oxirgi `DELETE FROM markets` i FK buzilishi bilan yiqilardi.

    ⚠ BOZOR QORALAMAGA QAYTARILADI: `vendors` — 2-fazaning domen jadvali
      va faol bozorda undan `DELETE` qilish o'zgarmaslik qo'riqchilariga
      urilishi mumkin. `cleanup_two_markets()` keyin ayni qadamni
      TAKRORLAYDI va bu xavfsiz (idempotent).
    """
    ids = [str(market_id) for market_id in seed.market_ids]
    conn.execute("UPDATE markets SET is_active = false WHERE id = ANY(%s::uuid[])", (ids,))
    conn.execute(
        "DELETE FROM vendors WHERE id = ANY(%s::uuid[])",
        ([str(vendor_id) for vendor_id in seed.vendor_ids],),
    )
    cleanup_two_markets(conn, seed.markets)
