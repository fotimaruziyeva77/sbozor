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
from sqlalchemy import BigInteger, Date, DateTime, Integer, Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.jobs.notification_meta import (
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    NEVER_SUPPRESSED_OUTBOX_KINDS,
    NOTIFICATION_META,
)

if TYPE_CHECKING:
    from datetime import date, datetime

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "DELIVERY_PAGE_SIZE",
    "ERROR_TYPE_MAX_LENGTH",
    "DeliveryCursor",
    "DeliveryPage",
    "DeliveryRow",
    "OutboxClaim",
    "RecipientMismatch",
    "claim",
    "defer_unresolved",
    "enqueue",
    "list_deliveries",
    "mark_blocked",
    "mark_delivered",
    "mark_failed",
    "release_expired_leases",
    "reschedule",
    "resolve_chat_id",
]

_UUID = PgUuid(as_uuid=True)
_TIMESTAMPTZ = DateTime(timezone=True)

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

_ERROR_TYPE_FORBIDDEN: Final[tuple[str, ...]] = (" ", "://", "api.telegram.org", "/")
"""`last_error_type` da UCHRAMASLIGI kerak bo'lgan parchalar (D-04).

⛔ UZUNLIK YOLG'IZ O'ZI YETMAYDI: `str(exc)` ning BOSHLANG'ICH 64 belgisi
   ham tokenning bir qismini tashishi mumkin. Probel — «bu jumla, tur
   nomi emas» degan eng arzon belgi; sxema ajratgichi, xost nomi va `/`
   esa URL'ning o'zi.

=============================================================================
⛔⛔ `"http"` PARCHASI `"://"` GA ALMASHTIRILDI (07-09 da O'LCHANDI).

Eski ro'yxat `"http"` ni taqiqlagan, ya'ni u `str(exc)` ni emas, `httpx`
istisno SINFLARINING NOMLARINI rad etardi: `HTTPStatusError`,
`HTTPError`, `HTTPFrameError` — hammasi «http» bilan boshlanadi. Natijada
D-04 ga TO'LIQ MOS keladigan qiymat (`type(exc).__name__`) yozib
bo'lmasdi va Telegram ning HAR BIR status xatosi `ValueError` bilan
qaytardi — ya'ni qator yakuniy holatga UMUMAN o'tolmasdi va navbat
jimgina to'lib borardi.

⚠ DA'VO SUSAYMADI, KUCHAYDI: har qanday `http(s)` URL'i `"://"` ni ham,
  `"/"` ni ham o'z ichiga oladi (ikkalasi ham ro'yxatda qoldi), ya'ni
  o'sha URL avvalgidek rad etiladi. Ustiga `isidentifier()` SHAKL talabi
  qo'shildi — u denylist emas, ALLOWLIST: Python sinf nomi HAR DOIM
  identifikator, `str(exc)` esa (nuqta, ikki nuqta, qavs, probel bilan)
  HECH QACHON emas.
=============================================================================
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
    """URINISH SONI — ⛔ BU URINISHDAN OLDINGI hisob (birinchi olishda `0`).

    =========================================================================
    ⛔ QIYMAT `claim()` DA OSHIRILMAYDI VA BU O'LCHANGAN TUZATISH.

    Ilgari `_CLAIM_DUE` uni SHARTSIZ oshirardi, ya'ni HTTP so'rovi UMUMAN
    yuborilmagan holat (`UNRESOLVED` — sotuvchi hali botga ulanmagan) ham
    byudjetdan yechilardi. Hisob endi AYNAN jo'natish tugagan joyda —
    `mark_delivered()`, `mark_blocked()`, `mark_failed()` va `reschedule()`
    da — oshadi.

    ⚠ CHAQIRUVCHI UCHUN OQIBAT: hozir yozilayotgan urinish
      `attempt_count + 1` -inchisi. Backoff formulasi (DQ-3) va
      `MAX_ATTEMPTS` chegarasi shu arifmetikaga qaraydi va ikkalasi ham
      07-09 da (`app/jobs/outbox.py`) hisoblanadi — bu modul faqat
      USTUNLARNI boshqaradi.
    =========================================================================
    """
    created_at: datetime
    """Qator NAVBATGA TUSHGAN payt — ⛔ YOSH CHEGARASI uchun (`_settle()`).

    ⛔ QIYMAT QATORDAN KELADI, TIKDAN EMAS: manzilsiz qator `UNRESOLVED_MAX_
       AGE_HOURS` dan keyin terminal holatga chiqadi va bu qaror qatorning
       O'Z yoshiga tayanadi. Tikning `now` i «hozir soat nechi» ni biladi,
       «bu kvitansiya qachon tug'ilgan» ni emas.

    ⚠ USTUN YANGI EMAS: u `_CLAIM_DUE` da ALLAQACHON o'qilardi (`ORDER BY`
      uchun) — bu maydon faqat o'sha mavjud qiymatni chaqiruvchiga
      CHIQARADI. Migratsiya YO'Q.
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
    ),
    claimed AS (
        UPDATE notification_outbox o
           SET status = :sent,
               lease_until = :now + make_interval(secs => :lease_seconds),
               updated_at = now()
          FROM due
         WHERE o.market_id = :market_id
           AND o.id = due.id
        RETURNING o.id, o.market_id, o.kind, o.recipient_kind, o.vendor_id,
                  o.payload, o.attempt_count, o.created_at
    )
    SELECT id, market_id, kind, recipient_kind, vendor_id, payload, attempt_count,
           created_at
      FROM claimed
     ORDER BY created_at, id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("pending", type_=Text()),
    bindparam("sent", type_=Text()),
    bindparam("never_suppressed", type_=ARRAY(Text())),
    bindparam("batch", type_=Integer()),
    bindparam("lease_seconds", type_=Integer()),
    bindparam("now", type_=_TIMESTAMPTZ),
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

=============================================================================
⛔⛔ TARTIB IKKI JOYDA YOZILGAN VA IKKALASI HAM MAJBURIY — BU O'LCHANGAN
    NUQSON (07-12 ning topilmasi, 07-14 da tuzatildi).

CTE ning `ORDER BY` i faqat ⛔ QAYSI qatorlar tanlanishini belgilaydi
(`LIMIT` bilan birga ishlaydi). Tashqi `UPDATE ... FROM due ... RETURNING`
ning CHIQISH TARTIBI esa PostgreSQL da ⛔ KAFOLATLANMAYDI: planer `due`
ni jadval bilan hash yoki merge join qiladi va natija tartibi rejaga
qarab o'zgaradi.

Oqibati AYNAN kuzatilgan: `test_the_oldest_row_is_claimed_first` to'liq
to'plamning 1-yugurishida QIZIL, 2-yugurishida YASHIL bo'ldi, yolg'iz
yugurtirilganda esa 21/21 yashil edi. Qatorlar TO'G'RI tanlangan —
faqat ularning TARTIBI o'zgargan.

⛔ TUZATISH TESTDA EMAS, SO'ROVDA: `UPDATE` `claimed` CTE siga o'raldi va
   yakuniy `SELECT` ⛔ O'Z `ORDER BY` ini oladi. `UPDATE ... RETURNING`
   ning O'ZIGA `ORDER BY` yozib bo'lmaydi (PostgreSQL grammatikasi buni
   qabul qilmaydi), shuning uchun tartib yakuniy proyeksiyada beriladi.
   `created_at` shu sababdan `RETURNING` ro'yxatida turadi — va u ENDI
   yakuniy `SELECT` ga ham chiqadi (`OutboxClaim.created_at`): ⛔ YANGI
   USTUN O'QILMADI, MAVJUD qiymat chaqiruvchiga uzatildi, ya'ni migratsiya
   YO'Q.
=============================================================================

=============================================================================
⛔⛔ `claimed` CTE SINING HISOB OSHIRUVCHI BANDI BU YERDAN OLIB TASHLANDI.

⚠ BAND SHU IZOHDA LITERAL YOZILMAYDI (`outbox.py` ning 1-taqig'idagi
  o'lchangan qoida): «bu yerda bo'lmasligi kerak» degan matnning O'ZI
  darvozani (`grep`) qizartirardi, ya'ni tushuntirish o'zi tushuntirayotgan
  qoidani buzardi. Shakl esa pastdagi uch bayonotda KO'RINADI.

Hisoblagich `claim()` da oshirilganda `_settle()` ning O'Z docstringi
e'lon qilgan kafolat — «⛔ BYUDJET FAQAT HAQIQIY URINISHGA QO'LLANADI» —
bajarilmasdi: `UNRESOLVED` shoxida HTTP so'rovi UMUMAN yuborilmagan
holatda ham byudjet yeyilardi.

O'lchangan oqibat: botga hali ulanmagan sotuvchining kvitansiyasi har 15
daqiqada qayta olinardi (`UNRESOLVED_RETRY_SECONDS`), ya'ni uch kunda
~288 «urinish» to'planardi. Sotuvchi ulangan kuni birinchi vaqtinchalik
`502` uni darhol `failed` ga tushirardi — Telegram bilan hech qanday
muammo bo'lmagan holda kvitansiya MANGU yo'qolardi.

⛔ ENDI URINISH AYNAN TUGAGAN JOYIDA SANALADI: `_MARK_DELIVERED`,
   `_MARK_TERMINAL` va `_RESCHEDULE`. Manzilsiz qatorning yo'li
   (`_DEFER_UNRESOLVED`) esa hisoblagichga UMUMAN tegmaydi —
   `_RELEASE_EXPIRED` bilan aynan bir sababdan.

⚠ NEGA TESTNI «yumshatish» RAD ETILDI: test tartibni ATAYIN o'lchaydi
  (yuqoridagi ⚠) va uni to'plam tengligiga aylantirish D-21 ning
  «kvitansiya cheksiz kutmaydi» da'vosini o'lchovsiz qoldirardi.
  Vaqti-vaqti bilan qizaradigan darvoza esa eng yomon sinf: u odamlarni
  QARASHGA emas, QAYTA YUGURTIRISHGA o'rgatadi.
=============================================================================

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

    ⛔ URINISH BU YERDA SANALMAYDI (`_CLAIM_DUE` docstringining oxirgi
       bandi): qaytarilgan `attempt_count` — bu urinishdan OLDINGI hisob.

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
            created_at=row.created_at,
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

    ⛔ SHAKL TALABI ALLOWLIST (`isidentifier()`), DENYLIST EMAS: Python
       sinf nomi HAR DOIM identifikator, `str(exc)` esa (nuqta, ikki
       nuqta, qavs va probel bilan) HECH QACHON emas. Denylist ro'yxati
       o'z joyida qoladi va u XATO XABARINI aniq qiladi — «nima noto'g'ri»
       degan savolga `isidentifier()` yolg'iz o'zi javob bera olmasdi.

    Raises:
        ValueError: qiymat tur nomiga o'xshamaganda (uzun, probelli,
            identifikator bo'lmagan yoki URL parchasini tashiganda).
    """
    lowered = error_type.lower()
    matched = sorted(token for token in _ERROR_TYPE_FORBIDDEN if token in lowered)
    if len(error_type) > ERROR_TYPE_MAX_LENGTH or matched or not error_type.isidentifier():
        raise ValueError(
            f"`last_error_type` faqat `type(exc).__name__` shaklidagi qisqa satrni "
            f"qabul qiladi (uzunligi <= {ERROR_TYPE_MAX_LENGTH}, probelsiz, "
            f"URL'siz va Python identifikatori shaklida). Berilgani: "
            f"uzunlik={len(error_type)}, identifikatormi={error_type.isidentifier()}, "
            f"taqiqlangan parcha(lar)={matched}. Telegram URL'i BOT TOKENINI "
            "tashiydi va istisno matni uni bazaga olib chiqardi (D-04)."
        )
    return error_type


_MARK_DELIVERED = text(
    """
    UPDATE notification_outbox
       SET status = 'delivered',
           provider_message_id = :provider_message_id,
           attempt_count = attempt_count + 1,
           lease_until = NULL,
           updated_at = now()
     WHERE market_id = :market_id
       AND id = :outbox_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("outbox_id", type_=_UUID),
    bindparam("provider_message_id", type_=BigInteger()),
)
"""⛔ `UPDATE`, `DELETE` EMAS (D-20). Yetkazilgan qator TARIXDA qoladi.

⛔ URINISH AYNAN SHU YERDA TUGADI VA SHU YERDA SANALADI: HTTP so'rovi
   ketdi, Telegram javob berdi. Hisoblagich `claim()` da emas, ijara
   OLINGANIDA emas — natija YOZILGANIDA oshadi.

⚠ `provider_message_id` TIPLANGAN (`BigInteger`): ustun `BIGINT` va
  Telegram ning identifikatorlari 32-bit diapazondan chiqib ketgan.
  Tipsiz bind `text()` da ustundan CHIQARILMAYDI (modulning 2-majburiyati)
  va qiymat asyncpg'ga xom holda borardi.

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
           attempt_count = attempt_count + 1,
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

⛔ URINISH AYNAN SHU YERDA TUGADI VA SHU YERDA SANALADI: ikkala holatga
   ham HTTP so'rovi ketgan (`403` yoki qayta urinib bo'lmaydigan status).
   `claim()` da sanash `UNRESOLVED` shoxini — ya'ni so'rov UMUMAN
   yuborilmagan holatni — ham byudjetdan yechardi.

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
           attempt_count = attempt_count + 1,
           lease_until = NULL,
           updated_at = now()
     WHERE market_id = :market_id
       AND id = :outbox_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("outbox_id", type_=_UUID),
    bindparam("pending", type_=Text()),
    bindparam("next_attempt_at", type_=_TIMESTAMPTZ),
    bindparam("error_type", type_=Text()),
    bindparam("status_code", type_=Integer()),
)
"""Qatorni navbatga QAYTARADI — ⛔ URINISH SHU YERDA SANALADI.

⛔ CHAQIRUV SHARTI: bu bayonot FAQAT haqiqiy jo'natishdan keyin ishlaydi
   (`429`, `5xx`, tarmoq uzilishi), ya'ni urinish AMALDA bo'lgan va u shu
   yerda tugadi. Manzilsiz qatorning yo'li BOSHQA — `_DEFER_UNRESOLVED` —
   va u hisoblagichga tegmaydi.

⚠ `next_attempt_at` CHAQIRUVCHIDAN: backoff formulasi (DQ-3) va Telegram
  ning `retry_after` qiymati 07-09 da hisoblanadi. Bu modul faqat
  USTUNNI boshqaradi — arifmetikani ikki joyga bo'lish ularni ajratardi.
"""

_DEFER_UNRESOLVED = text(
    """
    UPDATE notification_outbox
       SET status = :pending,
           next_attempt_at = :next_attempt_at,
           last_error_type = :error_type,
           last_status_code = NULL,
           lease_until = NULL,
           updated_at = now()
     WHERE market_id = :market_id
       AND id = :outbox_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("outbox_id", type_=_UUID),
    bindparam("pending", type_=Text()),
    bindparam("next_attempt_at", type_=_TIMESTAMPTZ),
    bindparam("error_type", type_=Text()),
)
"""Manzilsiz qatorni navbatga qaytaradi — ⛔ `attempt_count` OSHIRILMAYDI.

=============================================================================
⛔⛔ NEGA ALOHIDA BAYONOT, `_RESCHEDULE` GA BAYROQ EMAS.

Farq BITTA ustunda, lekin MA'NOSI butunlay boshqa: `_RESCHEDULE` «urinish
bo'ldi va yiqildi» ni yozadi, bu esa «urinish UMUMAN bo'lmadi» ni. Bayroqli
bitta funksiya (`reschedule(..., count=False)`) chaqiruv joyida
`True`/`False` bo'lib adashardi va o'sha adashuv JIMGINA — sotuvchining
byudjeti yeyilganini faqat kvitansiya yo'qolganda ko'rinardi.

⚠ `last_status_code` ATAYIN `NULL`: HTTP javobi UMUMAN bo'lmagan. Oldingi
  urinishning kodini qoldirish direktorning ekranida «Telegram 500 berdi»
  degan YOLG'ON sabab ko'rsatardi.

⛔ QOIDA `_RELEASE_EXPIRED` NIKI BILAN AYNAN BIR XIL: u ham urinishni
   sanamaydi, chunki u ham so'rov YUBORILMAGAN holatni yozadi.
=============================================================================
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
    bindparam("now", type_=_TIMESTAMPTZ),
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
    """Telegram 200 qaytardi va `message_id` berdi (`_MARK_DELIVERED` docstringi).

    ⛔ URINISH SHU YERDA SANALADI: so'rov ketdi va javob keldi.
    """
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

    ⛔ URINISH SHU YERDA SANALADI: `403` — Telegram ning HAQIQIY javobi,
       ya'ni so'rov yuborilgan.
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

    ⛔ URINISH SHU YERDA SANALADI — ⚠ VA BITTA ISTISNO BILAN: manzili
       topilmagan qator yosh chegarasidan (`UNRESOLVED_MAX_AGE_HOURS`)
       o'tganda ham SHU funksiya bilan yopiladi. U holatda oxirgi «urinish»
       ham amalda bo'lmagan, lekin bu ⛔ YAKUNIY yozuv: qator navbatdan
       CHIQADI, ya'ni hisob boshqa hech qachon o'qilmaydi va byudjetni
       hech nimadan yechmaydi.
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
    """Qatorni navbatga qaytaradi va URINISHNI SANAYDI (`_RESCHEDULE` docstringi).

    ⛔ FAQAT HAQIQIY JO'NATISHDAN KEYIN: manzil topilmagan qator uchun
       `defer_unresolved()` chaqiriladi — u hisoblagichga tegmaydi.
    """
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


async def defer_unresolved(
    session: AsyncSession,
    *,
    market_id: UUID,
    outbox_id: UUID,
    next_attempt_at: datetime,
    error_type: str,
) -> None:
    """Manzilsiz qatorni kechiktiradi — ⛔ URINISH SANALMAYDI.

    `reschedule()` bilan AYNI shakl, BITTA farq bilan: `attempt_count`
    OSHIRILMAYDI. Sabab `_DEFER_UNRESOLVED` docstringida: HTTP so'rovi
    UMUMAN yuborilmagan, ya'ni byudjetdan yechadigan urinish YO'Q.

    Args:
        session: chaqiruvchining OCHIQ tranzaksiyasidagi sessiya.
        market_id: tenant kaliti (RLS ustidagi ikkinchi qatlam).
        outbox_id: kechiktirilayotgan qator.
        next_attempt_at: keyingi urinish payti — CHAQIRUVCHIDAN
            (`UNRESOLVED_RETRY_SECONDS` arifmetikasi 07-09 da).
        error_type: ⛔ AYNAN `UnresolvedRecipient.__name__` shakli;
            `_validate_error_type()` dan O'TADI (D-04).

    Raises:
        ValueError: `error_type` tur nomiga o'xshamaganda.
    """
    await session.execute(
        _DEFER_UNRESOLVED,
        {
            "market_id": market_id,
            "outbox_id": outbox_id,
            "pending": _PENDING,
            "next_attempt_at": next_attempt_at,
            "error_type": _validate_error_type(error_type),
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


# ===========================================================================
# ⛔⛔ 5-MAJBURIYAT: FAQAT-O'QISH YUZASI — DIREKTORNING «XABAR BORDIMI?»
#     SAVOLI (BOT-04, 07-UI-SPEC §11).
#
# Bu bo'lim navbatga YOZMAYDI va uni O'ZGARTIRMAYDI. Yozuv yo'li shu
# fayldagi to'rtta terminal funksiyada (`mark_*`, `reschedule`) va u
# JO'NATUVCHIGA tegishli — ekran uchun yo'l ⛔ UMUMAN OCHILMAYDI (D-20
# append-only; qo'lda `delivered` qo'yish nizoda SOXTA DALIL bo'lardi).
#
# ⛔⛔ VA JAVOBGA CHIQMAYDIGANLAR — HAR BIRI O'Z SABABI BILAN:
#
#   `payload`             — unda summa va rasta kodi bor. U ⛔ XABAR uchun,
#                           ekran uchun EMAS: ekranda takrorlash IKKINCHI
#                           PUL YUZASI bo'lardi va u yig'indiga olib
#                           borardi (07-UI-SPEC §11.3).
#   `chat_id`             — ⛔ USTUNNING O'ZI YO'Q (4-majburiyat). Manzil
#                           jo'natish paytida o'qiladi, qatorda
#                           saqlanmaydi.
#   tayyor MATN           — ⛔ SAQLANMAYDI (Pitfall 6): matn `kind` +
#                           `payload` dan jo'natish paytida quriladi.
#   `provider_message_id` — Telegram ning ICHKI identifikatori. Direktorga
#                           hech nima aytmaydi va nizoda ham ishlatib
#                           bo'lmaydi — u faqat Bot API ning o'zi uchun.
#   `lease_until`         — IJARA, ya'ni ichki qulf mexanizmi. Ekranda u
#                           «xabar bordimi?» savoliga javob bermaydi.
#   `dedupe_key`          — u `<kind>:<manba-id>` shaklida MANBA
#                           identifikatorini tashiydi (`receipt:<payment_
#                           id>`) va uni ekranga chiqarish to'lov
#                           identifikatorini yetkazilganlik yuzasiga
#                           ko'chirardi.
#
# ⚠ `last_error_type` — ⛔ TUR NOMI, xato MATNI EMAS (D-04). Ustunga
#   yozilayotgan qiymat `_validate_error_type()` dan o'tgan, ya'ni bu
#   yerda ikkinchi filtr QO'YILMAYDI: qo'yilsa, chegara ikki joyda
#   yashab, ular ajralib ketardi.
# ===========================================================================

DELIVERY_PAGE_SIZE: Final[int] = 50
"""Bir sahifadagi eng ko'p yetkazilganlik qatori (DQ-4, `CASE_PAGE_SIZE` naqshi).

⛔ CHEGARA IKKI QATLAMDA: HTTP `le=` va bu funksiyaning `min()` i. Klient
   bir so'rov bilan kunning butun navbatini tortib ololmasligi kerak —
   Karmana konvertida bir kunda ~1000 kvitansiya bo'lishi mumkin.
"""


@dataclass(frozen=True, slots=True)
class DeliveryRow:
    """Direktor ekranidagi bitta yetkazilganlik qatori — ⛔ HOLAT VA VAQT.

    ⛔ BU `OutboxClaim` NING NUSXASI EMAS va ikkalasi BIRLASHTIRILMAYDI:
       `OutboxClaim` JO'NATUVCHI uchun (`payload` bor, chunki matn
       shundan quriladi), bu esa EKRAN uchun (`payload` YO'Q). Bitta
       dataclass ikkalasiga xizmat qilganda `payload` maydoni ekran
       yo'lida ham mavjud bo'lardi va uni javobga qo'shish bir qatorlik
       «qulaylik» bo'lib qolardi.

    ⚠ `updated_at` — ⛔ OXIRGI HOLAT O'ZGARISHI, va u `last_attempt_at`
      DEB NOMLANMAYDI: bunday USTUN jadvalda ⛔ UMUMAN YO'Q. Holatni
      o'zgartiradigan har bir bayonot (`_CLAIM_DUE`, `_MARK_DELIVERED`,
      `_MARK_TERMINAL`, `_RESCHEDULE`, `_RELEASE_EXPIRED`) `updated_at`
      ni yangilaydi, ya'ni u aynan «oxirgi marta nima bo'ldi?» savoliga
      javob beradi. Yangi ustun qo'shish MIGRATSIYA bo'lardi va u
      mavjud qiymatdan ko'proq narsa AYTMASDI.
    """

    outbox_id: UUID
    kind: str
    recipient_kind: str
    vendor_id: UUID | None
    """⛔ IDENTIFIKATOR, ISM EMAS: yorliq klientda `GET /vendors` bilan joinlanadi."""
    status: str
    """`OutboxStatus` a'zosining qiymati — besh a'zoli YOPIQ to'plam."""
    attempt_count: int
    """⛔ HAQIQIY JO'NATISH URINISHLARI SONI — «navbatdan olingan marta» EMAS.

    ⚠ QIYMATNING MA'NOSI O'ZGARDI (T-07-108): ilgari hisoblagich `claim()`
      da oshardi, ya'ni manzili topilmagan qator har 15 daqiqada bittadan
      «urinish» to'plardi va direktor ekranda `288` kabi sonni ko'rardi —
      holbuki Telegram'ga BIRORTA so'rov ketmagan edi. Endi son faqat
      jo'natish TUGAGANDA oshadi, ya'ni u `MAX_ATTEMPTS` byudjeti bilan
      bir xil o'lchovda.
    """
    created_at: datetime
    updated_at: datetime
    last_error_type: str | None
    """⛔ `type(exc).__name__` — xato MATNI HECH QACHON (D-04)."""
    last_status_code: int | None


@dataclass(frozen=True, slots=True)
class DeliveryCursor:
    """Keyset kursori — `(created_at, id)` JUFTLIGI (`CaseCursor` naqshi).

    Yolg'iz `created_at` bilan yozilgan kursor bir xil vaqtda yozilgan
    qatorlar ustidan SAKRAB o'tardi va outbox aynan shunday yozadi:
    kunlik dayjest ikkala qatorni ham BITTA tranzaksiyada (bir `now()`)
    qo'yadi.
    """

    created_at: datetime
    outbox_id: UUID


@dataclass(frozen=True, slots=True)
class DeliveryPage:
    """Kunning yetkazilganligi — qatorlar, ⛔ BESHALA hisoblagich va kursor.

    ⛔ BESHALA HISOBLAGICH HAM NOL BO'LGANDA HAM QAYTADI
       (`CaseListPage` va `ChargeListResponse` bilan AYNAN bir xil
       qaror): «bu kunda bloklangan sotuvchi yo'q» bilan «hisoblagich
       ishlamayapti» bir xil ko'rinsa, direktor D-02 nizosida noto'g'ri
       xulosaga kelardi.

    ⚠ HISOBLAGICHLAR SAHIFAGA EMAS, KUNGA (+ sotuvchi filtriga) tegishli:
      ikkinchi sahifaga o'tganda «bugun nechta xabar yetdi?» savolining
      javobi O'ZGARMASLIGI kerak.
    """

    day: date
    rows: tuple[DeliveryRow, ...]
    pending_count: int
    sent_count: int
    delivered_count: int
    failed_count: int
    blocked_count: int
    next_cursor: DeliveryCursor | None


_DELIVERY_ROWS = text(
    """
    SELECT o.id              AS outbox_id,
           o.kind            AS kind,
           o.recipient_kind  AS recipient_kind,
           o.vendor_id       AS vendor_id,
           o.status          AS status,
           o.attempt_count   AS attempt_count,
           o.created_at      AS created_at,
           o.updated_at      AS updated_at,
           o.last_error_type AS last_error_type,
           o.last_status_code AS last_status_code
      FROM notification_outbox o
      JOIN markets m
        ON m.id = o.market_id
     WHERE o.market_id = :market_id
       AND (o.created_at AT TIME ZONE m.timezone)::date = :day
       AND (:vendor_id IS NULL OR o.vendor_id = :vendor_id)
       AND (
             :cursor_created_at IS NULL
             OR (o.created_at, o.id) < (:cursor_created_at, :cursor_outbox_id)
           )
     ORDER BY o.created_at DESC, o.id DESC
     LIMIT :page_limit
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("day", type_=Date()),
    bindparam("vendor_id", type_=_UUID),
    bindparam("cursor_created_at", type_=_TIMESTAMPTZ),
    bindparam("cursor_outbox_id", type_=_UUID),
    bindparam("page_limit", type_=Integer()),
)
"""Kunning bir sahifasi — ⛔ KEYSET, `OFFSET` EMAS (DQ-4).

⛔ USTUNLAR RO'YXATI TO'LIQ EMAS VA BU ATAYIN: `payload`, `dedupe_key`,
   `lease_until` va `provider_message_id` bu `SELECT` da ⛔ UMUMAN
   YO'Q. `SELECT o.*` yozish ularni javob shaklidan bir qatorlik
   e'tiborsizlik bilan ajratardi — bo'lim izohidagi to'rt taqiq
   shundan keyin faqat INTIZOMGA tayanardi.

⛔ KUN CHEGARASI BOZORNING MINTAQASIDA (`markets.timezone`), UTC da
   EMAS — `_CLAIM_DUE` ning `AT TIME ZONE m.timezone` qarori bilan
   AYNAN bir xil. UTC da baholangan chegara Toshkent yarim tunidan
   keyingi besh soatdagi kvitansiyalarni OLDINGI kunga yozardi, ya'ni
   kechqurun to'lagan sotuvchining xabari direktorning bugungi
   ekranida UMUMAN ko'rinmasdi.

⚠ TARTIB `(created_at DESC, id DESC)` — eng YANGISI birinchi. Bu
  `_CLAIM_DUE` ning teskarisi va ikkalasi ham to'g'ri: jo'natuvchiga
  eng eski qator kerak (navbat), direktorga esa eng yangisi (hozir
  nima bo'lyapti).

⚠ QATOR SOLISHTIRUVI (`(a, b) < (x, y)`) ATAYIN — ikki ustunli `OR`
  zanjiri bilan yozilgan shart indeksdan foydalana olmasdi.

⚠ ALOHIDA INDEKS QO'SHILMADI va bu O'LCHANGAN qaror: `OUTBOX_DUE_INDEX`
  navbat uchun (`next_attempt_at`, qisman predikat bilan) va u bu
  so'rovga TUSHMAYDI. Yangi indeks MIGRATSIYA bo'lardi; kunlik hajm esa
  strukturaviy jihatdan chegaralangan (bir kunda ko'pi bilan bir necha
  ming qator: kvitansiya + eslatma + ikki dayjest). Chegara oshsa —
  to'g'ri tuzatish `(market_id, created_at DESC)` indeksi, sahifani
  kattalashtirish EMAS.
"""

_DELIVERY_COUNTS = text(
    """
    SELECT count(*) FILTER (WHERE o.status = :pending)::int   AS pending_count,
           count(*) FILTER (WHERE o.status = :sent)::int      AS sent_count,
           count(*) FILTER (WHERE o.status = :delivered)::int AS delivered_count,
           count(*) FILTER (WHERE o.status = :failed)::int    AS failed_count,
           count(*) FILTER (WHERE o.status = :blocked)::int   AS blocked_count
      FROM notification_outbox o
      JOIN markets m
        ON m.id = o.market_id
     WHERE o.market_id = :market_id
       AND (o.created_at AT TIME ZONE m.timezone)::date = :day
       AND (:vendor_id IS NULL OR o.vendor_id = :vendor_id)
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("day", type_=Date()),
    bindparam("vendor_id", type_=_UUID),
    bindparam("pending", type_=Text()),
    bindparam("sent", type_=Text()),
    bindparam("delivered", type_=Text()),
    bindparam("failed", type_=Text()),
    bindparam("blocked", type_=Text()),
)
"""Kunning BESH hisoblagichi — ⛔ SAHIFADAN MUSTAQIL (`_CASE_COUNTS` naqshi).

⛔ `count(*) FILTER (...)` ⛔ `GROUP BY status` DAN AFZAL VA SABAB
   MEXANIK: `GROUP BY` faqat MAVJUD holatlarni qaytaradi, ya'ni
   bloklangan sotuvchi bo'lmagan kunda `blocked_count` javobda UMUMAN
   bo'lmasdi va uni Python tomonda nol bilan to'ldirish kerak bo'lardi.
   O'sha to'ldirish unutilganda «bu kunda blok yo'q» bilan «hisoblagich
   yo'q» bir xil ko'rinardi — aynan shu darvoza qarshi turgan nosozlik.

⚠ HOLAT QIYMATLARI ENUMDAN, LITERAL EMAS: literal yozilganda enum
  o'zgargan kuni filtr JIMGINA hech nimaga tushmasdi va hisoblagich
  abadiy nol bo'lib qolardi.
"""


async def list_deliveries(
    session: AsyncSession,
    *,
    market_id: UUID,
    day: date,
    vendor_id: UUID | None = None,
    cursor: DeliveryCursor | None = None,
    limit: int = DELIVERY_PAGE_SIZE,
) -> DeliveryPage:
    """Kunning yetkazilganlik yozuvi — ⛔ FAQAT O'QISH (BOT-04, §11).

    ⛔ BU FUNKSIYA NAVBATGA TEGMAYDI: `SELECT` dan boshqa bayonot
       yo'q, ya'ni ekran yo'li orqali qatorni o'zgartirish
       STRUKTURAVIY jihatdan imkonsiz. Qo'lda `delivered` qo'yish
       nizoda (D-02) SOXTA DALIL bo'lardi.

    ⛔ JAVOBGA CHIQMAYDIGANLAR VA SABABLARI — bo'lim izohida (`payload`,
       `chat_id`, tayyor matn, `provider_message_id`, `lease_until`,
       `dedupe_key`).

    Args:
        session: chaqiruvchining tranzaksiyasidagi sessiya.
        market_id: tenant kaliti (RLS ustidagi ikkinchi qatlam).
        day: BIZNES-KUNI; chegara bozorning mintaqasida baholanadi.
        vendor_id: ixtiyoriy filtr — bitta sotuvchining xabarlari.
            ⚠ Hisoblagichlarga ham QO'LLANADI: filtr QAMROVNI
            toraytiradi (holatni emas), ya'ni «shu sotuvchiga bugun
            nechta xabar yetdi?» savoli o'z sanog'ini olishi kerak.
        cursor: oldingi sahifaning `next_cursor` i.
        limit: sahifa o'lchami; `DELIVERY_PAGE_SIZE` dan katta qiymat
            SHU chegaraga qisqartiriladi.

    Returns:
        `DeliveryPage` — qatorlar, ⛔ beshala hisoblagich va kursor.
    """
    page_limit = max(1, min(limit, DELIVERY_PAGE_SIZE))

    rows = (
        await session.execute(
            _DELIVERY_ROWS,
            {
                "market_id": market_id,
                "day": day,
                "vendor_id": vendor_id,
                "cursor_created_at": None if cursor is None else cursor.created_at,
                "cursor_outbox_id": None if cursor is None else cursor.outbox_id,
                "page_limit": page_limit,
            },
        )
    ).mappings()

    items = tuple(
        DeliveryRow(
            outbox_id=row["outbox_id"],
            kind=str(row["kind"]),
            recipient_kind=str(row["recipient_kind"]),
            vendor_id=row["vendor_id"],
            status=str(row["status"]),
            attempt_count=int(row["attempt_count"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_error_type=row["last_error_type"],
            last_status_code=row["last_status_code"],
        )
        for row in rows
    )

    counts = (
        (
            await session.execute(
                _DELIVERY_COUNTS,
                {
                    "market_id": market_id,
                    "day": day,
                    "vendor_id": vendor_id,
                    "pending": _PENDING,
                    "sent": _SENT,
                    "delivered": OutboxStatus.DELIVERED.value,
                    "failed": OutboxStatus.FAILED.value,
                    "blocked": OutboxStatus.BLOCKED.value,
                },
            )
        )
        .mappings()
        .one()
    )

    next_cursor = None
    if len(items) == page_limit:
        # ⚠ SAHIFA TO'LGANDA kursor beriladi — «yana bor» degan DA'VO
        #   emas, «tekshirib ko'r» degan taklif (`list_cases()` bilan
        #   aynan bir xil qaror).
        last = items[-1]
        next_cursor = DeliveryCursor(created_at=last.created_at, outbox_id=last.outbox_id)

    return DeliveryPage(
        day=day,
        rows=items,
        pending_count=int(counts["pending_count"]),
        sent_count=int(counts["sent_count"]),
        delivered_count=int(counts["delivered_count"]),
        failed_count=int(counts["failed_count"]),
        blocked_count=int(counts["blocked_count"]),
        next_cursor=next_cursor,
    )
