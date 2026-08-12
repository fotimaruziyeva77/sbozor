"""`notification_outbox` — APPEND-ONLY navbat, ijara va quiet-hours darvozasi.

=============================================================================
1-MAJBURIYAT: QATOR HECH QACHON O'CHIRILMAYDI (D-20).

Holat mashinasi `pending -> sent -> delivered | failed | blocked`, va har bir
o'tish `UPDATE`. Bu modulda o'chirish bayonoti UMUMAN YOZILMAYDI —
metodning yo'qligi kelishuv emas, STRUKTURA (`capture_repo.py` va
`nvr_repo.py` da o'rnatilgan qoida).

Sabab nizoda (D-02): outbox qatori «xabar yuborishga URINILDI» degan
da'voning yagona asosi. O'chirilgan qator «yetkazilmadi» ni
«umuman rejalashtirilmagan edi» ga aylantirardi va sotuvchi bilan
tortishuvda tizim tomonida hech qanday iz qolmasdi.

⚠ ASL NIYAT QATORI HAM O'ZGARMAYDI: `kind`, `payload`, `dedupe_key` va
  `recipient_kind` bir marta yoziladi. Qayta urinish faqat `attempt_count`,
  `next_attempt_at`, `lease_until` va xato ustunlariga tegadi.
=============================================================================

=============================================================================
2-MAJBURIYAT: `SKIP LOCKED` VA IJARA — IKKALASI HAM KERAK.

`capture_repo.py` ning 1-majburiyati AYNAN takrorlanadi va u yerda
o'lchangan: ular TURLI muddatni qoplaydi.

  * `FOR UPDATE ... SKIP LOCKED` — TRANZAKSIYA DAVOMIDA: ikki worker bir
    vaqtda `SELECT` qilganda ikkinchisi qulflangan qatorlarni o'tkazib
    yuboradi. Usiz bitta kvitansiya IKKI MARTA yuborilardi va sotuvchi ikki
    xil tasdiq olardi — D-02 ning aynan qarama-qarshi holati.
  * `lease_until` — COMMIT DAN KEYINGI muddat: worker qatorni `sent` ga
    o'tkazib COMMIT qilgach qulf TUSHADI. O'shandan keyin jarayon o'lsa
    qator MANGU `sent` bo'lib qolardi va xabar hech qachon ketmasdi.

⛔ YANGI QULF MEXANIZMI QURILMAYDI. Shakl `capture_repo.py::_CLAIM_DUE` dan
   olinadi, o'ylab topilmaydi.
=============================================================================

=============================================================================
3-MAJBURIYAT: BU MODUL O'Z TRANZAKSIYASINI OCHMAYDI.

Har funksiya `AsyncSession` ni ARGUMENT sifatida oladi. Sabab CASH-05 da:
kvitansiya niyati to'lov bilan AYNAN BIR TRANZAKSIYADA yozilishi shart.
Alohida tranzaksiya «to'lov yozildi, kvitansiya yozilmadi» oynasini ochardi
va u aynan eng band kunda birinchi marta ko'rinardi.

TENANT FILTRI IKKI QATLAM (`capture_repo.py` da o'rnatilgan qoida): RLS
policy'si himoya TO'RI, `market_id = :market_id` predikati esa ANIQ filtr.
Xom SQL'da u QO'LDA, ko'rinadigan joyda turadi.

⚠ ENG JIM XATO SINFI — TENANT KONTEKSTISIZ CHAQIRUV: RLS ostida `SELECT`
  va `UPDATE` **0 qator** qaytaradi va **istisno bermaydi**. Shuning uchun
  `claim()` bo'sh ro'yxat qaytarishi «navbat bo'sh» degani ham, «kontekst
  o'rnatilmagan» degani ham bo'lishi mumkin — ikkinchisi
  `test_outbox_repo.py` da ATAYIN o'lchanadi.
=============================================================================

=============================================================================
⛔ 4-MAJBURIYAT: `chat_id` VA TAYYOR MATN QATORDA SAQLANMAYDI.

`resolve_chat_id()` manzilni JO'NATISH PAYTIDA o'qiydi. Sabab D-26(c):
qayta ulanish (o'sha telefon, BOSHQA Telegram akkaunti) eski bog'lanishni
BEKOR QILADI. Manzil qatorga muzlatilgan bo'lsa navbatda turgan qarz
eslatmasi ESKI chatga ketardi — ya'ni sotuvchining moliyaviy ma'lumoti u
boshqarmaydigan akkauntga tushardi.

Matn esa `kind` + `payload` dan quriladi (Pitfall 6) va `payload` ning
kalitlari `notification_meta.NOTIFICATION_META` bilan cheklangan.
=============================================================================

⛔ `last_error_type` GA FAQAT `type(exc).__name__` (D-04). Chegara SHU
   MODULDA HAM tekshiriladi va bu «ikkinchi nusxa» emas, IKKINCHI QATLAM:
   Telegram Bot API ning URL'i BOT TOKENINI tashiydi (`alerts.py` ning
   2-taqig'i), ya'ni chaqiruvchi bir marta `str(exc)` yozsa token bazaga,
   u yerdan `pg_dump` -> restic -> TASHQI BUCKET ga chiqardi. Birinchi
   qatlam — jo'natuvchidagi AST darvozasi (07-09).

⛔ PUL BU MODULGA TUSHMAYDI: summa `payload` ning ichida KO'CHIRMA bo'lib
   turadi, manba esa `payments` / `daily_charges`. Bu faylda pul ustuni,
   pul arifmetikasi va kasrli tip YO'Q.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final
from uuid import UUID

from sbozor_core.enums import OutboxRecipientKind, OutboxStatus
from sqlalchemy import Integer, Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.jobs.notification_meta import (
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    NEVER_SUPPRESSED_OUTBOX_KINDS,
    NOTIFICATION_META,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "ERROR_TYPE_MAX_LENGTH",
    "OutboxClaim",
    "RecipientMismatch",
    "claim",
    "enqueue",
    "mark_blocked",
    "mark_delivered",
    "mark_failed",
    "release_expired_leases",
    "reschedule",
    "resolve_chat_id",
]

_UUID = PgUuid(as_uuid=True)

_PENDING: Final[str] = OutboxStatus.PENDING.value
_SENT: Final[str] = OutboxStatus.SENT.value
"""Holat qiymatlari — ENUMDAN, literal emas (`payment_repo._SHIFT_OPEN` naqshi).

Literal yozilganda enum o'zgargan kuni filtr JIMGINA hech nimaga tushmasdi:
so'rov ishlayverardi, faqat navbat abadiy bo'sh ko'rinardi.
"""

_VENDOR: Final[str] = OutboxRecipientKind.VENDOR.value

ERROR_TYPE_MAX_LENGTH: Final[int] = 64
"""`last_error_type` ning belgilardagi chegarasi — D-04 ning IKKINCHI qatlami.

⚠ SON TANLANMAGAN, HISOBLANGAN: Python istisno sinflarining eng uzun
nomlari ~30 belgi (`ConnectTimeout`, `RemoteProtocolError`), ya'ni 64
qonuniy qiymatlarning hammasini o'tkazadi va matnga o'xshagan hech nimani
o'tkazmaydi. `httpx` istisnosining MATNI esa to'liq URL'ni (ya'ni tokenni)
tashiydi va u har doim bu chegaradan uzun bo'ladi.
"""

_ERROR_TYPE_FORBIDDEN: Final[tuple[str, ...]] = (" ", "http", "api.telegram.org", "/")
"""`last_error_type` da UCHRAMASLIGI kerak bo'lgan parchalar (D-04).

⛔ UZUNLIK YOLG'IZ O'ZI YETMAYDI: `str(exc)` ning BOSHLANG'ICH 64 belgisi
   ham tokenning bir qismini tashishi mumkin. Probel — «bu jumla, tur
   nomi emas» degan eng arzon belgi; `http`, xost nomi va `/` esa
   URL'ning o'zi.
"""


class RecipientMismatch(ValueError):
    """`recipient_kind` va `vendor_id` juftligi buzilgan (`enqueue` chegarasi).

    ⚠ TIP `ValueError` DAN: bu KIRISH xatosi, ya'ni chaqiruvchi noto'g'ri
      juftlik bergan. `ck_notification_outbox_recipient_matches_vendor`
      uni baribir rad etardi, lekin DB xatosi «qaysi qator» ni aytadi,
      bu istisno esa «kim noto'g'ri chaqirdi» ni.
    """


@dataclass(frozen=True, slots=True)
class OutboxClaim:
    """Ijara bilan olingan bitta navbat qatori.

    ⛔ `chat_id` BU YERDA YO'Q va u «keyin qo'shiladigan qulaylik» emas —
       modul docstringining 4-majburiyati. Manzil `resolve_chat_id()` bilan
       ALOHIDA chaqiruvda, jo'natishdan bevosita oldin o'qiladi.

    ⛔ TAYYOR MATN HAM YO'Q: matn `kind` + `payload` dan quriladi.
    """

    id: UUID
    market_id: UUID
    kind: str
    recipient_kind: str
    vendor_id: UUID | None
    payload: dict[str, Any]
    attempt_count: int
    """URINISH SONI — bu qator BILAN BIRGA oshirilgan qiymat.

    Ya'ni birinchi ijara `1` beradi, `0` emas. Backoff formulasi (DQ-3)
    aynan shu songa qaraydi va uni 07-09 hisoblaydi — bu modul faqat
    `next_attempt_at` USTUNINI boshqaradi.
    """


# ===========================================================================
# XOM SQL — ORM'da ifodalanmaydigan uch so'rov
#
# ⚠ HAR BIR BIND PARAMETRI TIPLANADI (`capture_repo.py` ning 2-majburiyati):
#   `text()` da SQLAlchemy tipni ustundan CHIQARA OLMAYDI va tipsiz qiymat
#   asyncpg'ga xom `str` bo'lib borardi.
# ===========================================================================

_ENQUEUE = text(
    """
    INSERT INTO notification_outbox
        (market_id, kind, recipient_kind, vendor_id, dedupe_key, payload)
    VALUES
        (:market_id, :kind, :recipient_kind, :vendor_id, :dedupe_key, :payload)
    ON CONFLICT ON CONSTRAINT uq_notification_outbox_market_id_dedupe_key
    DO NOTHING
    RETURNING id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("kind", type_=Text()),
    bindparam("recipient_kind", type_=Text()),
    bindparam("vendor_id", type_=_UUID),
    bindparam("dedupe_key", type_=Text()),
    bindparam("payload", type_=JSONB()),
)
"""Niyatni IDEMPOTENT yozadi (D-21).

⛔ BU «TEKSHIR-KEYIN-YOZ» EMAS. «Bu kvitansiya allaqachon navbatdami?»
   degan alohida `SELECT` yozilmaydi: takroriy `POST /payments` ikki
   parallel so'rovda o'sha tekshiruvni IKKALASI ham bo'sh ko'rardi va
   sotuvchi ikkita kvitansiya olardi. Poyga DB'ga topshiriladi —
   `payment_repo.py` va `capture_repo.py` dagi bilan aynan bir xil qaror.

⚠ KONFLIKT NISHONI — KONSTRAYT NOMI, ustunlar ro'yxati emas: nom
  `models/notification.py` da e'lon qilingan va ikkalasi ham bitta
  migratsiyadan (`0023`) keladi.
"""

_CLAIM_DUE = text(
    """
    WITH due AS (
        SELECT o.id
          FROM notification_outbox o
          JOIN markets m
            ON m.id = o.market_id
          LEFT JOIN market_notification_settings s
            ON s.market_id = o.market_id
         CROSS JOIN LATERAL (
               SELECT (:now AT TIME ZONE m.timezone)::time      AS local_time,
                      COALESCE(s.quiet_hours_start, :quiet_start) AS quiet_start,
                      COALESCE(s.quiet_hours_end,   :quiet_end)   AS quiet_end
         ) w
         WHERE o.market_id = :market_id
           AND o.status = :pending
           AND o.next_attempt_at <= :now
           AND (
                 o.kind = ANY(:never_suppressed)
                 OR NOT CASE
                        WHEN w.quiet_start = w.quiet_end THEN false
                        WHEN w.quiet_start <  w.quiet_end
                             THEN w.local_time >= w.quiet_start
                              AND w.local_time <  w.quiet_end
                        ELSE w.local_time >= w.quiet_start
                          OR w.local_time <  w.quiet_end
                    END
               )
         ORDER BY o.created_at, o.id
         LIMIT :batch
         FOR UPDATE OF o SKIP LOCKED
    )
    UPDATE notification_outbox o
       SET status = :sent,
           attempt_count = o.attempt_count + 1,
           lease_until = :now + make_interval(secs => :lease_seconds),
           updated_at = now()
      FROM due
     WHERE o.market_id = :market_id
       AND o.id = due.id
    RETURNING o.id, o.market_id, o.kind, o.recipient_kind, o.vendor_id,
              o.payload, o.attempt_count
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("pending", type_=Text()),
    bindparam("sent", type_=Text()),
    bindparam("never_suppressed", type_=ARRAY(Text())),
    bindparam("batch", type_=Integer()),
    bindparam("lease_seconds", type_=Integer()),
)
"""Muddati kelgan qatorlarni IJARA bilan oladi — `capture_repo._CLAIM_DUE` shakli.

=============================================================================
⛔⛔ QUIET-HOURS DARVOZASI VA D-18 NING ISTISNOSI — AYNAN SHU `WHERE` BANDIDA.

`o.kind = ANY(:never_suppressed)` — istisno `NEVER_SUPPRESSED_OUTBOX_KINDS`
dan keladi, ya'ni REYESTRDAN HOSILA. Pitfall 7 aynan bu bandning
unutilishini tasvirlaydi: filtr yoziladi, `kind` bo'yicha istisno esa
UNUTILADI va 20:00 dan keyin to'lagan sotuvchi kvitansiyani ERTASI KUNI
olardi — jimgina, xatosiz, «to'g'ri ishlagan» so'rov bilan.
=============================================================================

⛔ SOZLAMA `LEFT JOIN` + `COALESCE` BILAN. `market_notification_settings`
   qatori YO'Q bo'lishi QONUNIY holat (`models/notification.py`: 1:1 va
   qator MAJBURIY EMAS). `JOIN` yozilganda sozlamasiz bozorning butun
   navbati JIMGINA ko'rinmas bo'lardi — xabarlar to'planardi, xato esa
   umuman bo'lmasdi.

⛔ YARIM TUNNI KESIB O'TISH SHOXI OCHIQ YOZILGAN (`quiet_start > quiet_end`).
   Standart oyna 21:00 -> 08:00, ya'ni `local_time BETWEEN start AND end`
   shakli unda HECH QACHON rost bo'lmasdi va quiet hours AMALDA
   ishlamasdi. Uchinchi shox (`start = quiet_end`) «tinch soat YO'Q»
   degani — teskari o'qish eslatmani butunlay o'chirardi.

⚠ OYNA CHEGARALARI YARIM YOPIQ (`>= start`, `< end`) va bu
  `notification_meta.is_quiet_now()` bilan AYNAN bir xil qoida. Ikkalasi
  bir qoidaning IKKI IFODASI: bu yerda SQL (sozlama har bozorda va
  navbatni xotiraga tortib bo'lmaydi), u yerda esa SPETSIFIKATSIYA.
  Ajralish `test_outbox_repo.py` da o'lchanadi — o'sha yerda HAQIQIY
  natija shu funksiyaning bashorati bilan solishtiriladi.

⚠ MINTAQA `markets.timezone` DAN, LITERALDAN EMAS (`capture_repo.
  _ENSURE_PLAN` naqshi): quiet hours — DEVOR SOATI tushunchasi va uni
  UTC da baholash oynani besh soatga siljitardi.

⚠ TARTIB `created_at, id` — ENG ESKI BIRINCHI. Aks holda partiya
  chegarasiga (`LIMIT`) urilgan navbatda eski qator har tikda ORQAGA
  surilardi va kvitansiya cheksiz kutardi.

⚠ `FOR UPDATE OF o` — FAQAT navbat qatori qulflanadi. `markets` va
  `market_notification_settings` O'QISH uchun qo'shilgan; ularni qulflash
  bir bozorning tikini boshqa jarayonlar bilan to'qnashtirardi (va
  `LEFT JOIN` ning nullable tomonini qulflash PG da umuman taqiqlangan).
"""

_RESOLVE_VENDOR_CHAT = text(
    """
    SELECT b.telegram_user_id
      FROM vendor_telegram_bindings b
     WHERE b.market_id = :market_id
       AND b.vendor_id = :vendor_id
       AND b.revoked_at IS NULL
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("vendor_id", type_=_UUID),
)
"""FAOL bog'lanishning manzili (D-26c).

⚠ `revoked_at IS NULL` — `BINDING_ACTIVE_PREDICATE` ning AYNAN o'zi va
  `uq_vendor_telegram_bindings_vendor_active` qisman indeksi natija BITTA
  qator bo'lishini KAFOLATLAYDI. `LIMIT 1` shuning uchun yozilmagan: u
  ikkinchi faol qator paydo bo'lganda uni JIMGINA yashirardi, holbuki
  bunday holat cheklov buzilganini bildiradi.
"""

_RESOLVE_DIRECTOR_CHAT = text(
    "SELECT s.director_chat_id FROM market_notification_settings s WHERE s.market_id = :market_id"
).bindparams(bindparam("market_id", type_=_UUID))
"""Direktorning manzili — sozlama qatoridan.

⚠ QATOR YO'Q ham, `director_chat_id` `NULL` ham QONUNIY: direktor hali
  botga ulanmagan. Ikkala holat ham `None` beradi va bu XATO EMAS.
"""


async def enqueue(
    session: AsyncSession,
    *,
    market_id: UUID,
    kind: str,
    recipient_kind: str,
    vendor_id: UUID | None,
    dedupe_key: str,
    payload: dict[str, Any],
) -> UUID | None:
    """Niyatni navbatga yozadi — CHAQIRUVCHINING tranzaksiyasida (CASH-05).

    ⛔ KONFLIKT `None` QAYTARADI VA BU XATO EMAS (D-21). Takroriy so'rovda
       ikkinchi qator YOZILMAYDI va himoya ILOVA SHARTIDA emas,
       `uq_notification_outbox_market_id_dedupe_key` CHEKLOVIDA. Chaqiruvchi
       `None` ni «xabar allaqachon navbatda» deb o'qishi kerak —
       `payment_repo` ning Pitfall 3 qoidasi bu yerda TESKARI: u yerda
       `None` invariant buzilishi edi, bu yerda esa NORMAL natija.

    ⛔ `payload` IKKI QATLAMDA TEKSHIRILADI. Chaqiruvchi uni
       `notification_meta.outbox_payload()` dan o'tkazishi SHART, lekin bu
       funksiya kalitlarni QAYTA tekshiradi: unutilgan chaqiruv jimgina
       o'tib ketsa tayyor matn (yoki sotuvchining ismi) bazaga tushardi va
       u yerdan zaxiraga, zaxiradan esa tashqi bucketga chiqardi
       (Pitfall 6).

    ⛔ `recipient_kind` <-> `vendor_id` MOSLIGI HAM SHU YERDA. Qoida
       `ck_notification_outbox_recipient_matches_vendor` bilan AYNAN bir
       xil, lekin xato Python darajasida ANIQ xabar beradi.

    Args:
        session: chaqiruvchining OCHIQ tranzaksiyasidagi sessiya.
        market_id: tenant kaliti (RLS ustidagi ikkinchi qatlam).
        kind: `OutboxKind` a'zosining qiymati.
        recipient_kind: `OutboxRecipientKind` a'zosining qiymati.
        vendor_id: sotuvchi xabari uchun MAJBURIY, direktorniki uchun
            `None` bo'lishi SHART.
        dedupe_key: `"<kind>:<manba-id>"` shakli (masalan
            `receipt:<payment_id>`). Kalitni ILOVA quradi, NOYOBLIGINI esa
            faqat `UNIQUE` cheklov kafolatlaydi.
        payload: allowlist bilan cheklangan kalitlar.

    Returns:
        Yangi qatorning `id` si, yoki `None` — qator ALLAQACHON mavjud.

    Raises:
        KeyError: `kind` reyestrda bo'lmaganda.
        ValueError: `payload` da ruxsat etilmagan kalit bo'lganda.
        RecipientMismatch: `recipient_kind` va `vendor_id` mos kelmaganda.
    """
    meta = NOTIFICATION_META[kind]
    unknown = sorted(set(payload) - meta.payload_keys)
    if unknown:
        raise ValueError(
            f"`{kind}` uchun ruxsat etilmagan payload kalit(lar)i: {unknown}. "
            f"Ruxsat etilganlari: {sorted(meta.payload_keys)}. Chegara YOZISH "
            "paytida qo'yiladi — noma'lum qiymat UI'da ko'rinmasdi, lekin bazaga, "
            "u yerdan zaxiraga va tashqi bucketga chiqardi (Pitfall 6)."
        )

    if (recipient_kind == _VENDOR) != (vendor_id is not None):
        raise RecipientMismatch(
            f"`recipient_kind={recipient_kind!r}` va `vendor_id={vendor_id!r}` mos "
            f"emas: `{_VENDOR}` uchun `vendor_id` MAJBURIY, direktor xabari uchun "
            "esa u BO'LMASLIGI shart. Birinchi holatda xabar jo'natish paytida "
            "manzilsiz qolardi, ikkinchisida esa direktorning xabari sotuvchi "
            "bog'lanishiga bog'lanardi."
        )

    result = await session.execute(
        _ENQUEUE,
        {
            "market_id": market_id,
            "kind": kind,
            "recipient_kind": recipient_kind,
            "vendor_id": vendor_id,
            "dedupe_key": dedupe_key,
            "payload": payload,
        },
    )
    row = result.first()
    return None if row is None else UUID(str(row.id))


async def claim(
    session: AsyncSession,
    *,
    market_id: UUID,
    batch_size: int,
    lease_seconds: int,
    now: datetime,
) -> list[OutboxClaim]:
    """Muddati kelgan qatorlarni IJARA bilan oladi (`_CLAIM_DUE` docstringi).

    ⛔ BIR BAYONOT: `SELECT ... FOR UPDATE SKIP LOCKED` va `UPDATE` bitta
       CTE ichida. Ikki bayonotga bo'lish orada oyna ochardi va ikki worker
       bir qatorni ikki marta olardi.

    ⚠ `now` ARGUMENT, `now()` EMAS: quiet-hours darvozasi aynan shu
      qiymatga qaraydi, ya'ni «22:30 da nima bo'ladi?» savoli soatni
      siljitmasdan, `freezegun`siz o'lchanadi (`alert_sweep(..., now=...)`
      bilan bir xil qaror).

    ⚠ `market_id` ARGUMENT BO'LISHI SHART: RLS himoya TO'RI, aniq filtr
      esa so'rovning O'ZIDA turadi (modul docstringining 3-majburiyati).

    Returns:
        Ijara olingan qatorlar. Bo'sh ro'yxat — «navbat bo'sh» YOKI
        «tenant konteksti o'rnatilmagan»: RLS ikkinchi holatda ham 0 qator
        beradi va istisno KO'TARMAYDI.
    """
    result = await session.execute(
        _CLAIM_DUE,
        {
            "market_id": market_id,
            "pending": _PENDING,
            "sent": _SENT,
            "never_suppressed": sorted(NEVER_SUPPRESSED_OUTBOX_KINDS),
            "batch": batch_size,
            "lease_seconds": lease_seconds,
            "now": now,
            "quiet_start": DEFAULT_QUIET_HOURS_START,
            "quiet_end": DEFAULT_QUIET_HOURS_END,
        },
    )
    return [
        OutboxClaim(
            id=row.id,
            market_id=row.market_id,
            kind=row.kind,
            recipient_kind=row.recipient_kind,
            vendor_id=row.vendor_id,
            payload=row.payload,
            attempt_count=row.attempt_count,
        )
        for row in result
    ]


async def resolve_chat_id(
    session: AsyncSession,
    *,
    market_id: UUID,
    recipient_kind: str,
    vendor_id: UUID | None,
) -> int | None:
    """Manzilni JO'NATISH PAYTIDA o'qiydi — qatordan EMAS (D-26c).

    =========================================================================
    ⛔ NEGA `chat_id` OUTBOX QATORIDA SAQLANMAYDI.

    Qayta ulanish QONUNIY shox: o'sha telefon, BOSHQA Telegram akkaunti
    (telefon almashtirildi, akkaunt o'g'irlandi, oila a'zosiniki edi). U
    eski bog'lanishni BEKOR QILADI (`revoked_at`). Manzil qatorga
    muzlatilgan bo'lsa, navbatda turgan qarz eslatmasi ESKI chatga ketardi
    — ya'ni sotuvchining moliyaviy ma'lumoti u ENDI BOSHQARMAYDIGAN
    akkauntga tushardi.
    =========================================================================

    ⛔ `None` — QONUNIY natija, xato EMAS: sotuvchi hali botga ulanmagan
       yoki direktorning chati sozlanmagan. Chaqiruvchi bunday qatorni
       `blocked` ga o'tkazmasligi kerak — `blocked` «foydalanuvchi botni
       BLOKLADI» degan BOSHQA fakt (D-22) va ikkalasini aralashtirish
       ekrandagi «aloqa uzildi» ro'yxatini ulanmaganlar bilan to'ldirardi.
    """
    if recipient_kind == _VENDOR:
        if vendor_id is None:
            raise RecipientMismatch(
                f"`{_VENDOR}` uchun `vendor_id` MAJBURIY — u `None` bo'lsa "
                "bog'lanishni topadigan kalit umuman yo'q."
            )
        result = await session.execute(
            _RESOLVE_VENDOR_CHAT, {"market_id": market_id, "vendor_id": vendor_id}
        )
    else:
        result = await session.execute(_RESOLVE_DIRECTOR_CHAT, {"market_id": market_id})

    row = result.first()
    return None if row is None else row[0]


def _validate_error_type(error_type: str) -> str:
    """`last_error_type` ni tekshiradi — D-04 ning REPO DARAJASIDAGI qatlami.

    ⛔ CHAQIRUVCHI ADASHSA HAM TOKEN BAZAGA TUSHMAYDI. Telegram Bot API
       ning URL'i bot tokenini tashiydi va `httpx` istisnosining MATNI
       to'liq URL'ni o'z ichiga oladi (`alerts.py` ning 2-taqig'i), ya'ni
       bitta `str(exc)` sirni bazaga, u yerdan `pg_dump` -> restic ->
       TASHQI BUCKET ga olib chiqardi.

    Raises:
        ValueError: qiymat tur nomiga o'xshamaganda (uzun, probelli yoki
            URL parchasini tashiganda).
    """
    lowered = error_type.lower()
    matched = sorted(token for token in _ERROR_TYPE_FORBIDDEN if token in lowered)
    if len(error_type) > ERROR_TYPE_MAX_LENGTH or matched or not error_type:
        raise ValueError(
            f"`last_error_type` faqat `type(exc).__name__` shaklidagi qisqa satrni "
            f"qabul qiladi (uzunligi <= {ERROR_TYPE_MAX_LENGTH}, probelsiz va "
            f"URL'siz). Berilgani: uzunlik={len(error_type)}, taqiqlangan "
            f"parcha(lar)={matched}. Telegram URL'i BOT TOKENINI tashiydi va "
            "istisno matni uni bazaga olib chiqardi (D-04)."
        )
    return error_type


_MARK_DELIVERED = text(
    """
    UPDATE notification_outbox
       SET status = 'delivered',
           provider_message_id = :provider_message_id,
           lease_until = NULL,
           updated_at = now()
     WHERE market_id = :market_id
       AND id = :outbox_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("outbox_id", type_=_UUID),
)
"""⛔ `UPDATE`, `DELETE` EMAS (D-20). Yetkazilgan qator TARIXDA qoladi.

⚠ `delivered` — «Telegram 200 qaytardi va `message_id` berdi», ya'ni xabar
  CHATGA JOYLANDI. U foydalanuvchi xabarni O'QIGANINI bildirmaydi va
  bunday da'vo nizoda (D-02) tizimni isbotlab bo'lmaydigan gapga
  majburlardi (`enums.py::OutboxStatus` docstringi).
"""

_MARK_TERMINAL = text(
    """
    UPDATE notification_outbox
       SET status = :status,
           last_error_type = :error_type,
           last_status_code = :status_code,
           lease_until = NULL,
           updated_at = now()
     WHERE market_id = :market_id
       AND id = :outbox_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("outbox_id", type_=_UUID),
    bindparam("status", type_=Text()),
    bindparam("error_type", type_=Text()),
    bindparam("status_code", type_=Integer()),
)
"""`blocked` va `failed` — BITTA bayonot, ikki chaqiruvchi.

⚠ IKKI HOLAT IKKI FUNKSIYADA, LEKIN BIR SQL: farq faqat `status` da,
  ya'ni ikkinchi bayonot yozish ikkala yo'lni ham alohida yangilashni
  talab qilardi va ular jimgina ajralib ketardi. MA'NO farqi esa
  funksiyalarning docstringlarida — u yerda u KO'RINADI.
"""

_RESCHEDULE = text(
    """
    UPDATE notification_outbox
       SET status = :pending,
           next_attempt_at = :next_attempt_at,
           last_error_type = :error_type,
           last_status_code = :status_code,
           lease_until = NULL,
           updated_at = now()
     WHERE market_id = :market_id
       AND id = :outbox_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("outbox_id", type_=_UUID),
    bindparam("pending", type_=Text()),
    bindparam("error_type", type_=Text()),
    bindparam("status_code", type_=Integer()),
)
"""Qatorni navbatga QAYTARADI — `attempt_count` TEGILMAYDI.

⚠ URINISH `claim()` DA SANALGAN, ya'ni uni bu yerda yana oshirish har
  yiqilishni IKKI marta hisoblardi va byudjet ikki barobar tez tugardi.

⚠ `next_attempt_at` CHAQIRUVCHIDAN: backoff formulasi (DQ-3) va Telegram
  ning `retry_after` qiymati 07-09 da hisoblanadi. Bu modul faqat
  USTUNNI boshqaradi — arifmetikani ikki joyga bo'lish ularni ajratardi.
"""

_RELEASE_EXPIRED = text(
    """
    UPDATE notification_outbox
       SET status = :pending,
           lease_until = NULL,
           updated_at = now()
     WHERE market_id = :market_id
       AND status = :sent
       AND lease_until IS NOT NULL
       AND lease_until < :now
    RETURNING id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("pending", type_=Text()),
    bindparam("sent", type_=Text()),
)
"""O'lgan worker qoldirgan ijarani qaytaradi (`capture_repo.release_expired` jufti).

⛔ `attempt_count` OSHIRILMAYDI VA BU ATAYIN: urinish AMALDA QILINMAGAN —
   worker qatorni `sent` ga o'tkazib, HTTP so'rovni yubormasdan o'lgan.
   Oshirish har worker qulashini sotuvchining byudjetidan yechardi va
   uchta qayta ishga tushirish xabarni `failed` ga tushirardi — holbuki
   Telegram bilan hech qanday muammo yo'q edi.

⚠ `lease_until IS NOT NULL` SHARTI OCHIQ YOZILGAN: `NULL < :now` `NULL`
  beradi va u qatorni baribir chetlab o'tardi, lekin niyat ko'rinmasdi.
"""


async def mark_delivered(
    session: AsyncSession,
    *,
    market_id: UUID,
    outbox_id: UUID,
    provider_message_id: int,
) -> None:
    """Telegram 200 qaytardi va `message_id` berdi (`_MARK_DELIVERED` docstringi)."""
    await session.execute(
        _MARK_DELIVERED,
        {
            "market_id": market_id,
            "outbox_id": outbox_id,
            "provider_message_id": provider_message_id,
        },
    )


async def mark_blocked(
    session: AsyncSession,
    *,
    market_id: UUID,
    outbox_id: UUID,
    error_type: str,
) -> None:
    """Foydalanuvchi botni BLOKLADI (`403`) — MA'LUMOT, xato emas (D-22).

    ⛔ QAYTA URINILMAYDI: blok o'z-o'zidan tuzalmaydi va har urinish
       chegarani qattiqroq urardi. Holat `failed` DAN AJRATILGAN — uni
       texnik nosozlik shovqiniga qo'shish direktordan «bu sotuvchi bilan
       aloqa uzildi» faktini YASHIRARDI.
    """
    await session.execute(
        _MARK_TERMINAL,
        {
            "market_id": market_id,
            "outbox_id": outbox_id,
            "status": OutboxStatus.BLOCKED.value,
            "error_type": _validate_error_type(error_type),
            "status_code": None,
        },
    )


async def mark_failed(
    session: AsyncSession,
    *,
    market_id: UUID,
    outbox_id: UUID,
    error_type: str,
    status_code: int | None,
) -> None:
    """Urinishlar tugadi yoki qayta urinib bo'lmaydigan xato.

    ⚠ QATOR O'CHIRILMAYDI (D-20): «yuborilmadi» — bu ham FAKT va u
      direktorning ekranida ko'rinishi kerak. O'chirilgan qator nosozlikni
      «xabar umuman rejalashtirilmagan edi» ga aylantirardi.
    """
    await session.execute(
        _MARK_TERMINAL,
        {
            "market_id": market_id,
            "outbox_id": outbox_id,
            "status": OutboxStatus.FAILED.value,
            "error_type": _validate_error_type(error_type),
            "status_code": status_code,
        },
    )


async def reschedule(
    session: AsyncSession,
    *,
    market_id: UUID,
    outbox_id: UUID,
    next_attempt_at: datetime,
    error_type: str,
    status_code: int | None,
) -> None:
    """Qatorni navbatga qaytaradi (`_RESCHEDULE` docstringi)."""
    await session.execute(
        _RESCHEDULE,
        {
            "market_id": market_id,
            "outbox_id": outbox_id,
            "pending": _PENDING,
            "next_attempt_at": next_attempt_at,
            "error_type": _validate_error_type(error_type),
            "status_code": status_code,
        },
    )


async def release_expired_leases(
    session: AsyncSession,
    *,
    market_id: UUID,
    now: datetime,
) -> int:
    """Muddati o'tgan ijarani `pending` ga qaytaradi (`_RELEASE_EXPIRED` docstringi).

    Returns:
        Qaytarilgan qatorlar SONI — nol ham NATIJA, uning yo'qligi emas.
    """
    result = await session.execute(
        _RELEASE_EXPIRED,
        {"market_id": market_id, "pending": _PENDING, "sent": _SENT, "now": now},
    )
    return len(result.fetchall())
