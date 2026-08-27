"""To'lov yozish — IDEMPOTENT get-or-create, STORNO va kassir oynasi (CASH-01…CASH-03).

=============================================================================
⛔⛔ A1 ZONDINING NATIJASI VA TANLANGAN SHOX — NOMMA-NOM.

`migrations/entities/__init__.py::IDEMPOTENT_GET_OR_CREATE_SUPPORTED`
qiymati **`True`** (o'lchov: **2026-08-10**, `PostgreSQL 18.4 (Debian
trixie)`, testcontainer; o'lchaydigan test
`tests/tenancy/test_idempotency_concurrency.py::
test_second_statement_sees_the_winner`).

O'sha o'lchov uchta da'voni **birga** yopdi: ikki mustaqil `AsyncSession`
`asyncio.Barrier` bilan bir vaqtda bir xil `(market_id, idempotency_key)`
juftligini yozganda jadvalda **AYNAN 1 qator** qoldi, ikkala korutina ham
**BIR XIL `id`** oldi va **birortasi istisno ko'tarmadi**.

⛔ **SHUNING UCHUN BU MODUL IKKI BAYONOTLI SHOXDAN YURADI:**

    1-bayonot: `INSERT ... ON CONFLICT DO NOTHING ... RETURNING`
    2-bayonot: `SELECT ... WHERE market_id = … AND idempotency_key = …`

⚠ **ZAXIRA SHOX BU YERDA YOZILMAGAN VA U KERAK EMAS.** Marker `False`
  bo'lganda (ya'ni ikkinchi bayonot yutgan qatorni **ko'rmasa**) yagona
  to'g'ri yo'l `IntegrityError` + `session.begin_nested()` (`SAVEPOINT`)
  bo'lardi — `nvr_repo.py:506-532` naqshi. `SAVEPOINT` o'sha shoxda
  **majburiy**: 03-06 darsi bo'yicha abort holatidagi tranzaksiyada
  keyingi har qanday bayonot yiqiladi va 409 javobi **500** ga aylanadi.
  Marker bugun `True`, ya'ni o'sha kod **o'lik shox** bo'lardi va o'lik
  shox sinalmaydi — shuning uchun u yozilmadi, faqat **nomlandi**.

=============================================================================
⛔⛔ NEGA IKKINCHI BAYONOT ORTIQCHA EMAS — VA CTE SHAKLI NEGA YARAMAYDI.

`ON CONFLICT DO NOTHING ... RETURNING` konfliktda **hech nima
qaytarmaydi** (`capture_repo.py:140` ning xulqiy jufti). Ya'ni «yutqazgan»
tranzaksiya birinchi bayonotdan `None` oladi va qatorni **o'qishi shart**.

06-01 uchinchi o'lchov sifatida bir bayonotli **CTE + `UNION ALL`**
shaklini ham sinadi va **RAD ETDI**: determinlashtirilgan interleavingda
(holder qulfni ushlab turadi -> challenger `pg_stat_activity.
wait_event_type = 'Lock'` bo'ladi -> holder commit qiladi) CTE ning
`SELECT` qismi **bo'sh** javob berdi, keyingi **alohida** bayonot esa
qatorni **ko'rdi**. Sabab: CTE ning hamma qismi **bitta bayonot
snapshotini** ko'radi.

⛔ **BU MODULDA `UNION ALL` YO'Q va bo'lmaydi.**

⚠ **IZOLYATSIYA DARAJASIGA BOG'LIQLIK OCHIQ YOZILADI:** ikkinchi bayonot
  `READ COMMITTED` da **yangi snapshot** oladi, ya'ni parallel yutgan
  tranzaksiyaning commit qilingan qatorini ko'radi. `REPEATABLE READ` ga
  o'tilsa bu naqsh **jimgina buziladi** — ikkinchi bayonot ham tranzaksiya
  boshidagi snapshotni ko'rib `None` qaytarardi va har parallel so'rov
  `RuntimeError` ga tushardi. 06-01 zondi `SHOW transaction_isolation`
  ni **ochiq assert** qiladi, ya'ni o'zgarish o'sha testda ushlanadi.

=============================================================================
⛔ PITFALL 3 — `None` NI XATO DEB **500** QILISH TAQIQLANADI.

Konflikt qatorni qaytarmaydi; `None` -> **majburiy** qayta `SELECT`. Agar
ikkinchi bayonot ham bo'sh bo'lsa — bu **invariant buzilishi** (`UNIQUE`
konstrayt bor, ya'ni konflikt bo'lgan qator MAVJUD bo'lishi shart) va
modul **aniq xato bilan yiqiladi**: `RuntimeError`. ⛔ Jimgina 200
qaytarish **EMAS** — u kassirga «to'lov yozildi» deb yolg'on aytardi.

=============================================================================
⛔ PITFALL 4 — BIR XIL KALIT, **BOSHQA** PAYLOAD.

D-21 faqat «**o'sha** to'lovni qaytar» deydi. Kassir kalitni saqlab
summani o'zgartirib qayta yuborsa server **eski** to'lovni 200 bilan
qaytarardi va yangi summa ⛔ **jimgina yo'qolardi**. Yechim:
`request_fingerprint()` — muhim maydonlar xeshi **qatorda** saqlanadi;
mos kelmasa `IdempotencyConflict` -> marshrutda **409
`idempotency_key_reused`**.

⚠ Bu D-21 ni **buzmaydi**: u faqat **aynan bir xil** so'rov uchun 200
  talab qiladi.

=============================================================================
⛔ D-23 — `payments` APPEND-ONLY. BU MODULDA `UPDATE` YO'Q.

Storno **yangi qator** (`kind='reversal'`), asl qator **tegilmaydi**.
`0020` unga shartsiz `BEFORE UPDATE OR DELETE` qo'riqchisini
(`payment_immutable()`) ulaydi, ya'ni ilova qatlamidagi taqiq
sxemadagining **ko'zgusi**, ikkinchi qoida emas.

=============================================================================
⛔ CHAQIRUVCHI UCHUN SHART: TENANT KONTEKSTI (`billing_repo` bilan bir xil).

Har funksiya `set_tenant_context()` ostidagi sessiyada chaqiriladi. RLS
`payments` ga to'liq qo'llanadi, ya'ni begona bozorning kaliti bilan
kelgan takror so'rov ikkinchi bayonotda **0 qator** ko'radi.

=============================================================================
⛔ PUL — BUTUN SO'M (`BIGINT` <-> `int`), D-11. Kasrli tip bu modulda
   umuman uchramaydi.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final
from uuid import UUID, uuid4

from sbozor_core.enums import PaymentKind, ShiftStatus
from sbozor_core.models import Payment, Stall
from sqlalchemy import Integer, Text, bindparam, select, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.dialects.postgresql import insert as pg_insert

if TYPE_CHECKING:
    from datetime import date, datetime

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "FINGERPRINT_FIELDS",
    "RECENT_PAYMENT_WINDOW",
    "IdempotencyConflict",
    "PaymentAlreadyReversed",
    "PaymentOwner",
    "PaymentRow",
    "PaymentWrite",
    "RecentPayment",
    "create_payment",
    "find_by_idempotency_key",
    "open_shift_id",
    "payment_owner",
    "recent_payments",
    "request_fingerprint",
    "reverse_payment",
    "shift_system_total",
]

_UUID = PgUuid(as_uuid=True)

_SHIFT_OPEN: Final[str] = ShiftStatus.OPEN.value
"""`cashier_shifts.status` ning ochiq qiymati — enumdan, LITERAL emas.

`billing_repo._OCCUPIED` bilan aynan bir xil sabab: literal yozilganda
enum o'zgargan kuni filtr jimgina hech nimaga tushmasdi — so'rov
ishlayverardi, faqat natija bo'sh bo'lardi.
"""

RECENT_PAYMENT_WINDOW: Final[int] = 5
"""Kassir ko'radigan oxirgi to'lovlar soni — ⛔ **SERVERDA QAT'IY** (§8.8).

=============================================================================
⛔⛔ `recent_payments()` `limit` ARGUMENTINI **QABUL QILMAYDI** VA BU
   TANLOV EMAS, HIMOYANING O'ZI.

UI-SPEC §8.8 va §10.3 ning ikkinchi yarmi: kassir smenasining **hamma**
to'lovini ko'rsa, ularni **qo'shib** tizim summasini chiqarib olardi va
smena yopilishidagi **ko'r deklaratsiya** ⛔ **arifmetika bilan**
buzilardi — ya'ni variance o'lchovining butun ma'nosi yo'qolardi.

Argument bo'lganda marshrut uni **o'tkazib yuborishi** mumkin bo'lardi
(bitta `Query()` e'loni yetardi). Yig'indi yo'lini **maydon yashirish**
emas, ⛔ **marshrutning imkoniyati** to'sadi — shuning uchun oyna shu
yerda **konstanta** va funksiya imzosida undan ⛔ **kirish yo'li yo'q**.
"""

FINGERPRINT_FIELDS: Final[tuple[str, ...]] = (
    "stall_id",
    "service_date",
    "amount_soum",
    "quote_soum",
    "method",
    "override_reason",
)
"""`request_fingerprint()` xeshiga kiradigan maydonlar — ⛔ TARTIB QAT'IY.

=============================================================================
⛔ `idempotency_key` BU RO'YXATDA **YO'Q** va bo'lmaydi: u xeshning
   **kaliti**, tarkibi emas. Kalitni xeshga qo'shish har kalit uchun
   boshqa barmoq izi berardi va Pitfall 4 ning butun taqqoslashi
   **ma'nosiz** bo'lardi (ikki xil kalit hech qachon solishtirilmaydi).

⛔ `cashier_id` va `shift_id` ham **ATAYIN yo'q**: takror so'rov o'sha
   kassirdan, o'sha smenadan keladi va ularni xeshga qo'shish hech qanday
   yangi holatni ushlamasdi. Aksincha — direktor smenasiz kiritgan to'lov
   (OQ-6/A5) qayta yuborilganda `shift_id` `NULL` bo'lib qolardi va xesh
   **bir xil** chiqardi, ya'ni maydon shovqin qo'shib hech nima
   qo'riqlamasdi.

⚠ **KEYINGI FAZA UCHUN OCHIQ SHART:** bu ro'yxatga maydon
  qo'shilsa/olib tashlansa xesh ⛔ **O'ZGARADI** va o'sha paytda
  bazadagi ESKI qatorlarning barmoq izi yangi hisob bilan **mos
  kelmaydi** — takror so'rov 409 `idempotency_key_reused` olardi.
  Kalitning hayot davri qisqa (§8.7: bitta to'lov varag'i), ya'ni amalda
  bu deploy oynasidagi bir necha daqiqaga tegadi — LEKIN o'zgartirish
  ONGLI bo'lishi shart va shuning uchun bu yerda **yozib qo'yilgan**.

⚠ **ALGORITM: `sha256`** (stdlib `hashlib`, yangi paket **yo'q** —
  T-06-SC). Bu **kriptografik imzo emas**, ya'ni sir ham, tuz ham yo'q:
  vazifasi «bu aynan o'sha so'rovmi?» degan savolga javob berish.
"""

_FINGERPRINT_SEPARATOR: Final[str] = "\x1f"
"""Maydonlar orasidagi ajratgich — ⛔ **ASCII Unit Separator**, vergul EMAS.

Vergul (yoki `|`) qiymatning **ichida** uchrashi mumkin va o'shanda ikki
boshqa so'rov bir xil xesh berardi (`("a,b", "c")` va `("a", "b,c")`).
`\\x1f` esa `stall_id` (UUID), `service_date` (ISO sana), summalar (o'nlik
raqamlar) va enum qiymatlarining birortasida **uchramaydi**.
"""


class IdempotencyConflict(RuntimeError):
    """Bir xil `idempotency_key`, ⛔ **BOSHQA** so'rov tanasi (Pitfall 4).

    Marshrut buni **409 `idempotency_key_reused`** ga aylantiradi.

    ⚠ TIP `RuntimeError` DAN, `Exception` DAN EMAS: bu dastur
      mantig'idagi holat, kirish validatsiyasi emas — `ValueError` uni
      Pydantic xatolari bilan bir sinfga qo'shib yuborardi.
    """


class PaymentAlreadyReversed(RuntimeError):
    """Bu to'lov allaqachon bekor qilingan yoki uning O'ZI storno (D-23).

    Marshrut buni **409 `payment_already_reversed`** ga aylantiradi.

    ⚠ IKKALA HOLAT HAM SHU ISTISNO BILAN: «asl qatorda allaqachon storno
      bor» va «bu qatorning o'zi `kind='reversal'`». Ular kassir uchun
      **bir xil** javob beradi — «bu yozuvni bekor qilib bo'lmaydi» — va
      ikkinchi kod qo'shish 06-02 ning **14 kodli** reyestriga tegardi.
    """


@dataclass(frozen=True, slots=True)
class PaymentWrite:
    """`create_payment()` ning kirish payloadi — ⛔ HAMMA MAYDON MAJBURIY.

    ⚠ `quote_soum` **chaqiruvchidan** keladi, lekin u ⛔ **mijozdan
      EMAS**: marshrut uni `payment_quote_set()` (06-01) natijasidan
      tanlaydi (D-20). `PaymentCreateRequest` da bunday maydon **umuman
      yo'q** — aks holda kassir uni yuborib `OVERRIDE_IS_PAIRED_CHECK` ni
      chetlab o'tardi.

    ⚠ `charge_id` **YO'Q** (D-24/C-4): to'lov hisobga bog'lanmaydi. «Qaysi
      kunning pattasi yopildi» savoli `allocate_charge_credit()` ning
      `FIFO_OLDEST_SERVICE_DATE_FIRST` hosila qoidasidan chiqadi va
      **hech qayerda saqlanmaydi**.
    """

    idempotency_key: str
    stall_id: UUID
    vendor_id: UUID
    service_date: date
    amount_soum: int
    quote_soum: int
    method: str
    override_reason: str | None
    shift_id: UUID | None
    cashier_id: UUID


@dataclass(frozen=True, slots=True)
class PaymentRow:
    """Yozilgan yoki qayta o'qilgan to'lov qatori — ⛔ NOL EMAS, NATIJA.

    ⚠ `vendor_id` bu **qaytish** shaklida ham bor, LEKIN u HTTP javobiga
      chiqmaydi (C-10): `PaymentResponse` da `vendor_*` maydonlari yo'q.
      Bu yerda u `reverse_payment()` uchun kerak — storno qatori asl
      qatordan **nusxa** oladi.
    """

    payment_id: UUID
    stall_id: UUID
    vendor_id: UUID
    service_date: date
    amount_soum: int
    quote_soum: int
    kind: str
    method: str
    override_reason: str | None
    reverses_payment_id: UUID | None
    reversal_reason: str | None
    request_fingerprint: str
    shift_id: UUID | None
    cashier_id: UUID
    created_at: datetime


def request_fingerprint(
    *,
    stall_id: UUID,
    service_date: date,
    amount_soum: int,
    quote_soum: int,
    method: str,
    override_reason: str | None,
) -> str:
    """So'rov tanasining BARMOQ IZI — Pitfall 4 ning yagona mexanizmi.

    Xesh `sha256`, kirish esa `FINGERPRINT_FIELDS` tartibida
    normallashgan satrlar (`\\x1f` bilan ajratilgan). Maydonlar ro'yxati,
    ajratgichning sababi va «keyingi faza maydon qo'shsa xesh
    O'ZGARADI» ogohlantirishi ⛔ **`FINGERPRINT_FIELDS` docstringida**
    sanab yozilgan — ikkinchi nusxa bu yerda yozilmaydi.

    ⛔ **NORMALLASHTIRISH:** `None` -> bo'sh satr, `UUID` -> `str(...)`,
       `date` -> `isoformat()`, `int` -> o'nlik. Ya'ni bir xil ma'noli
       so'rov har doim bir xil xesh beradi, `repr()` shakli o'zgarsa ham.

    Args:
        stall_id: rasta — kalit bilan birga «qaysi rasta» ni qulflaydi.
        service_date: to'lov QAYSI KUN uchun kiritildi.
        amount_soum: AMALDA olingan summa — Pitfall 4 ning asosiy maydoni.
        quote_soum: server bergan summa (D-20). ⚠ U ham xeshda va u
            ⛔ **PARALLEL** so'rovlarni ajratadi, TAKROR so'rovni emas:
            takror so'rovda marshrut xeshga qatorning O'Z `quote_soum`
            ini qaytarib beradi (`find_by_idempotency_key()` docstringi).
            Aks holda birinchi so'rov o'zgartirgan qoldiq ikkinchisiga
            **boshqa** kvota berardi va bir xil tanali qayta yuborish
            409 olardi — D-21 ning teskarisi.
        method: `cash` / `terminal`.
        override_reason: chetlanish sababi yoki `None`.

    Returns:
        64 belgili o'n oltilik `sha256` digesti.
    """
    parts = (
        str(stall_id),
        service_date.isoformat(),
        str(amount_soum),
        str(quote_soum),
        method,
        override_reason or "",
    )
    if len(parts) != len(FINGERPRINT_FIELDS):
        raise AssertionError(
            "request_fingerprint(): xesh tarkibi `FINGERPRINT_FIELDS` dan ajralib "
            f"ketdi — {len(parts)} qiymat, {len(FINGERPRINT_FIELDS)} maydon nomi. "
            "Ikkalasi BIRGA o'zgartiriladi (docstringdagi ogohlantirish)."
        )
    return hashlib.sha256(_FINGERPRINT_SEPARATOR.join(parts).encode("utf-8")).hexdigest()


_PAYMENT_COLUMNS = (
    Payment.id,
    Payment.stall_id,
    Payment.vendor_id,
    Payment.service_date,
    Payment.amount_soum,
    Payment.quote_soum,
    Payment.kind,
    Payment.method,
    Payment.override_reason,
    Payment.reverses_payment_id,
    Payment.reversal_reason,
    Payment.request_fingerprint,
    Payment.shift_id,
    Payment.cashier_id,
    Payment.created_at,
)
"""Ikkala bayonot ham AYNAN shu ustunlarni oladi.

⚠ RO'YXAT BITTA: `RETURNING` va qayta `SELECT` bir xil shaklni berishi
  SHART, aks holda `_row()` ikki xil kortejni ochishga urinardi va
  nosozlik faqat konflikt yo'lida — ya'ni **kamdan-kam** — ko'rinardi.
"""


def _row(raw: tuple[object, ...]) -> PaymentRow:
    """Kortejdan `PaymentRow` — tartib `_PAYMENT_COLUMNS` bilan bir xil."""
    (
        payment_id,
        stall_id,
        vendor_id,
        service_date,
        amount_soum,
        quote_soum,
        kind,
        method,
        override_reason,
        reverses_payment_id,
        reversal_reason,
        fingerprint,
        shift_id,
        cashier_id,
        created_at,
    ) = raw
    return PaymentRow(
        payment_id=payment_id,  # type: ignore[arg-type]
        stall_id=stall_id,  # type: ignore[arg-type]
        vendor_id=vendor_id,  # type: ignore[arg-type]
        service_date=service_date,  # type: ignore[arg-type]
        amount_soum=int(amount_soum),  # type: ignore[call-overload]
        quote_soum=int(quote_soum),  # type: ignore[call-overload]
        kind=str(kind),
        method=str(method),
        override_reason=None if override_reason is None else str(override_reason),
        reverses_payment_id=reverses_payment_id,  # type: ignore[arg-type]
        reversal_reason=None if reversal_reason is None else str(reversal_reason),
        request_fingerprint=str(fingerprint),
        shift_id=shift_id,  # type: ignore[arg-type]
        cashier_id=cashier_id,  # type: ignore[arg-type]
        created_at=created_at,  # type: ignore[arg-type]
    )


async def find_by_idempotency_key(
    session: AsyncSession, *, market_id: UUID, idempotency_key: str
) -> PaymentRow | None:
    """Kalit bo'yicha ALLAQACHON yozilgan qator, yoki `None` — D-21 ning 0-qadami.

    =========================================================================
    ⛔⛔ NEGA MARSHRUT BUNI NARXLASHDAN **OLDIN** CHAQIRADI.

    `create_payment()` ning ichidagi idempotentlik `quote_soum` ni
    ALLAQACHON hisoblangan holda oladi, ya'ni u FAQAT yozish poygasini
    hal qiladi. Takror so'rov esa boshqa muammo: **birinchi so'rov
    narxlash kirishini O'ZGARTIRGAN** bo'ladi — `vendor_outstanding()`
    hamma to'lovni ayiradi va `as_of` bilan filtrlanmaydi, ya'ni
    `payment_quote_set()` retryda BOSHQA to'plam qaytaradi. O'sha
    to'plamda asl summa endi yo'q va marshrut 422 `reason_required`
    berardi — D-21 ning aynan teskarisi.

    Shuning uchun kalit narxlash darvozalaridan OLDIN qaraladi va
    solishtirishga qatorning O'Z `quote_soum` i kiradi (marshrutdagi
    izoh). ⛔ Bu `create_payment()` ning ichki tekshiruvini ALMASHTIRMAYDI:
    u SELECT bilan INSERT orasidagi poygani (ikki parallel so'rov, bitta
    kalit) hamon qo'riqlaydi va shuning uchun IKKALASI HAM qoladi.

    ⚠ Storno qatorlari bu yo'lda uchramaydi: ular kalitni SERVERDA
      tug'diradi (`reversal:{uuid4}`), mijoznikidan mustaqil.
    =========================================================================

    Returns:
        `PaymentRow` yoki `None` — ⛔ NATIJA («bu kalit hali ishlatilmagan»),
        xato emas.
    """
    result = await session.execute(
        select(*_PAYMENT_COLUMNS).where(
            Payment.market_id == market_id,
            Payment.idempotency_key == idempotency_key,
        )
    )
    found = result.one_or_none()
    return None if found is None else _row(tuple(found))


async def create_payment(
    session: AsyncSession, *, market_id: UUID, payload: PaymentWrite
) -> tuple[PaymentRow, bool]:
    """⛔ IDEMPOTENT get-or-create — **IKKI BAYONOT** (D-21, A1 zondi).

    Qadamlar modul docstringidagi tartibda:

      1. `INSERT ... ON CONFLICT DO NOTHING ... RETURNING` -> `one_or_none()`;
      2. `None` bo'lsa ⛔ **ALOHIDA** `SELECT` (yangi snapshot, READ
         COMMITTED — modul docstringidagi izolyatsiya bandi);
      3. ikkinchi bayonot ham bo'sh bo'lsa ⛔ `RuntimeError` (Pitfall 3);
      4. barmoq izi mos kelmasa ⛔ `IdempotencyConflict` (Pitfall 4).

    ⛔ **`ON CONFLICT` NISHONI — USTUNLAR RO'YXATI** (`index_elements`),
       konstrayt nomi emas. `capture_repo.py:338-341` da teskarisi
       tanlangan va sabab o'sha yerda: u yerdagi nishon `business_date`
       **hisoblanadigan** ustunni o'z ichiga oladi va uni ifoda sifatida
       qayta yozish kerak bo'lardi. Bu yerda esa nishon
       `(market_id, idempotency_key)` — ikkala ustun ham **oddiy**, ya'ni
       ro'yxat shakli ishlaydi va u konstrayt nomining o'zgarishiga
       bog'liq emas.

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        payload: to'lov maydonlari (`PaymentWrite`).

    Returns:
        `(row, created)`. `created=True` -> marshrut **201**;
        `created=False` -> marshrut ⛔ **200** va **o'sha** `payment_id`
        (D-21: takror so'rov kassir uchun **ko'rinmas**).

    Raises:
        IdempotencyConflict: kalit o'sha, barmoq izi **boshqa**.
        RuntimeError: konflikt bo'ldi-yu, qator topilmadi (invariant).
    """
    fingerprint = request_fingerprint(
        stall_id=payload.stall_id,
        service_date=payload.service_date,
        amount_soum=payload.amount_soum,
        quote_soum=payload.quote_soum,
        method=payload.method,
        override_reason=payload.override_reason,
    )

    # ---- 1-BAYONOT: yozishga urinish. Poyga DB'GA topshiriladi.
    inserted = await session.execute(
        pg_insert(Payment)
        .values(
            market_id=market_id,
            stall_id=payload.stall_id,
            vendor_id=payload.vendor_id,
            service_date=payload.service_date,
            amount_soum=payload.amount_soum,
            quote_soum=payload.quote_soum,
            kind=PaymentKind.PAYMENT.value,
            method=payload.method,
            override_reason=payload.override_reason,
            idempotency_key=payload.idempotency_key,
            request_fingerprint=fingerprint,
            shift_id=payload.shift_id,
            cashier_id=payload.cashier_id,
        )
        .on_conflict_do_nothing(index_elements=["market_id", "idempotency_key"])
        .returning(*_PAYMENT_COLUMNS)
    )
    won = inserted.one_or_none()
    if won is not None:
        return _row(tuple(won)), True

    # ---- 2-BAYONOT: ⛔ ALOHIDA `SELECT`. Modul docstringidagi izolyatsiya
    #      bandi: READ COMMITTED da bu bayonot YANGI snapshot oladi va
    #      parallel yutgan tranzaksiyaning qatorini KO'RADI. CTE ichiga
    #      qo'yish (bir bayonot) uni KO'RMASDI — 06-01 o'lchagan.
    existing = await session.execute(
        select(*_PAYMENT_COLUMNS).where(
            Payment.market_id == market_id,
            Payment.idempotency_key == payload.idempotency_key,
        )
    )
    found = existing.one_or_none()
    if found is None:
        # ⛔ PITFALL 3: jimgina 200 EMAS. `ON CONFLICT` otildi, ya'ni
        #    `uq_payments_market_id_idempotency_key` ni buzadigan qator
        #    MAVJUD. Uni ko'rmaslik ikki narsadan biri: izolyatsiya
        #    darajasi o'zgargan yoki tenant konteksti (RLS) noto'g'ri
        #    o'rnatilgan. Ikkalasi ham JIMGINA davom ettirilmaydi.
        raise RuntimeError(
            "idempotency invariant buzildi: `ON CONFLICT` otildi, lekin "
            f"(market_id={market_id}, idempotency_key={payload.idempotency_key!r}) "
            "qatori qayta o'qishda TOPILMADI. Sabab izolyatsiya darajasi "
            "(READ COMMITTED kutilgan) yoki tenant konteksti bo'lishi mumkin — "
            "jimgina 200 qaytarish TAQIQLANADI (Pitfall 3)."
        )

    row = _row(tuple(found))
    if row.request_fingerprint != fingerprint:
        # ⛔ PITFALL 4: kalit o'sha, tana BOSHQA. Eski to'lovni 200 bilan
        #    qaytarish YANGI summani JIMGINA yo'qotardi.
        raise IdempotencyConflict(
            f"idempotency_key={payload.idempotency_key!r} boshqa so'rov tanasi bilan "
            "qayta ishlatilgan (barmoq izi mos kelmadi)"
        )
    return row, False


_REVERSE_PAYMENT = text(
    """
    INSERT INTO payments
        (id, market_id, stall_id, vendor_id, service_date, amount_soum, quote_soum,
         kind, method, reverses_payment_id, reversal_reason, override_reason,
         idempotency_key, request_fingerprint, shift_id, cashier_id)
    SELECT :new_id,
           o.market_id,
           o.stall_id,
           o.vendor_id,
           o.service_date,
           o.amount_soum,
           o.quote_soum,
           :reversal,
           o.method,
           o.id,
           :reason_code,
           NULL,
           :idempotency_key,
           :fingerprint,
           :shift_id,
           :cashier_id
      FROM payments o
     WHERE o.market_id = :market_id
       AND o.id = :payment_id
       AND o.kind = :payment
       AND NOT EXISTS (
             SELECT 1
               FROM payments r
              WHERE r.market_id = o.market_id
                AND r.reverses_payment_id = o.id
           )
    RETURNING id, stall_id, vendor_id, service_date, amount_soum, quote_soum,
              kind, method, override_reason, reverses_payment_id, reversal_reason,
              request_fingerprint, shift_id, cashier_id, created_at
    """
).bindparams(
    bindparam("new_id", type_=_UUID),
    bindparam("market_id", type_=_UUID),
    bindparam("payment_id", type_=_UUID),
    bindparam("reversal", type_=Text()),
    bindparam("payment", type_=Text()),
    bindparam("reason_code", type_=Text()),
    bindparam("idempotency_key", type_=Text()),
    bindparam("fingerprint", type_=Text()),
    bindparam("shift_id", type_=_UUID),
    bindparam("cashier_id", type_=_UUID),
)
"""Storno — ⛔ **BITTA BAYONOT**, «tekshir-keyin-yoz» EMAS.

=============================================================================
⛔⛔ NEGA `NOT EXISTS` SO'ROVNING **ICHIDA**.

`capture_repo.py:363-368` ning majburiyati: shart alohida `SELECT` bilan
tekshirilib, keyin `INSERT` yozilsa **poyga oynasi** ochilardi — ikki
parallel «bekor qilish» bosishi **ikkita** storno qatori yozardi va
qoldiq ⛔ **ikki marta** kamayardi (`PAYMENT_ALREADY_REVERSED`
docstringidagi aynan o'sha nosozlik).

Bu yerda shart `INSERT ... SELECT` ning `WHERE` ida, ya'ni Postgres uni
qator qulfi ostida baholaydi va **0 qator** yozish — «allaqachon storno
qilingan» ning halol javobi.

⚠ **YUQORI CHEGARA HAMON `payments` NING O'ZIDA:** `NOT EXISTS` ikki
  bir vaqtdagi tranzaksiyaning ikkalasiga ham «yo'q» deb javob berishi
  nazariy jihatdan mumkin (ikkalasi ham commit dan oldingi holatni
  ko'radi). Amalda bu holat kassir yuzasida yuz bermaydi (bitta oyna,
  bitta bosish) va uning oqibati **ko'rinadi** — ikkinchi storno qatori
  jurnalda turadi. Sxema darajasidagi qat'iy kafolat
  (`UNIQUE (market_id, reverses_payment_id)`) 06-04 ning qaroriga
  tegardi va bu reja migratsiyaga ⛔ **TEGMAYDI**.

=============================================================================
⛔ USTUNLAR ASL QATORDAN **NUSXA**: `stall_id`, `vendor_id`,
   `service_date`, `amount_soum`, `quote_soum`, `method`.

`amount_soum` ⛔ **MUSBAT KATTALIK** (C-5): `payments.amount_soum` da
`CHECK (> 0)` bor va belgi faqat `billing_repo._SIGNED_PAYMENT_EXPR`
ifodasida — `kind = 'reversal'` bo'yicha — tug'iladi. Manfiy summa
yozish ikkinchi haqiqat manbai bo'lardi.

`override_reason` ⛔ **`NULL`**: `REVERSAL_HAS_NO_OVERRIDE_CHECK` uni
majburlaydi. Storno chetlanish emas — u **bekor qilish**, sababi esa
`reversal_reason` da.

⚠ `idempotency_key` **SERVER TOMONDA** (`uuid4`): storno so'rovi kassirdan
  kalit olmaydi (§8.7 kaliti to'lov varag'iga bog'langan) va `NOT NULL`
  ustunni bo'sh qoldirib bo'lmaydi. Takroriylikni bu yerda `NOT EXISTS`
  qo'riqlaydi, kalit emas.
"""


async def reverse_payment(
    session: AsyncSession,
    *,
    market_id: UUID,
    payment_id: UUID,
    reason_code: str,
    cashier_id: UUID,
    shift_id: UUID | None,
) -> PaymentRow:
    """Storno — ⛔ **YANGI QATOR**, asl qator TEGILMAYDI (D-23).

    ⛔ **BU FUNKSIYADA `UPDATE` YO'Q.** `payments` append-only va `0020`
       unga shartsiz `BEFORE UPDATE OR DELETE` qo'riqchisi ulangan. Nizoda
       IKKALA yozuv ham ko'rinadi — «to'ladi» va «bekor qilindi, sababi
       shu» (D-02).

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        payment_id: bekor qilinayotgan ASL to'lov.
        reason_code: `sbozor_core.enums.ReversalReason` qiymati —
            ⛔ **MAJBURIY** (D-19).
        cashier_id: storno qatorining aktori.
        shift_id: storno QAYSI smenaga yoziladi (`None` ruxsat — OQ-6/A5).

    Returns:
        Yozilgan **storno** qatori (`kind='reversal'`).

    Raises:
        PaymentAlreadyReversed: asl qator topilmadi, uning o'zi storno,
            yoki unga allaqachon storno yozilgan. ⚠ Uchala holat ham
            marshrutda **409** bo'ladi; «topilmadi» ni 404 qilish uchun
            marshrut mavjudlikni ALOHIDA tekshiradi (`payments.py`).
    """
    result = await session.execute(
        _REVERSE_PAYMENT,
        {
            "new_id": uuid4(),
            "market_id": market_id,
            "payment_id": payment_id,
            "reversal": PaymentKind.REVERSAL.value,
            "payment": PaymentKind.PAYMENT.value,
            "reason_code": reason_code,
            "idempotency_key": f"reversal:{uuid4()}",
            "fingerprint": f"reversal:{payment_id}",
            "shift_id": shift_id,
            "cashier_id": cashier_id,
        },
    )
    written = result.one_or_none()
    if written is None:
        raise PaymentAlreadyReversed(
            f"payment_id={payment_id} bekor qilib bo'lmadi: qator yo'q, uning o'zi "
            "storno, yoki unga allaqachon storno yozilgan"
        )
    return _row(tuple(written))


@dataclass(frozen=True, slots=True)
class PaymentOwner:
    """Asl to'lovning smenasi, turi va rasta KODI — storno darvozalari uchun.

    ⚠ MARSHRUT UCHUN KERAK, `reverse_payment()` UCHUN EMAS: storno so'rovi
      uch xil rad etilishi mumkin va ular UCH BOSHQA javob beradi —
      «qator yo'q» (**404**), «boshqa smenaning to'lovi» (**403**, UI-SPEC
      §8.8) va «allaqachon bekor qilingan» (**409**). Ularni bitta 409 ga
      siqish kassirga noto'g'ri yo'l ko'rsatardi.

    ⚠ `stall_code` SHU YERDA OLINADI VA IKKINCHI SO'ROV YOZILMAYDI:
      marshrut storno javobida rasta kodini qaytaradi (§5.5 — kassir
      yuzasida UUID yo'q), qator esa bu tekshiruv uchun ALLAQACHON
      o'qilyapti. Alohida `SELECT` bir so'rovda ikki marta o'sha
      jadvalga borardi.
    """

    shift_id: UUID | None
    kind: str
    stall_code: str


async def payment_owner(
    session: AsyncSession, *, market_id: UUID, payment_id: UUID
) -> PaymentOwner | None:
    """Asl to'lov bormi, qaysi smenaga tegishli va qaysi rastaniki (`None` — yo'q).

    ⚠ RLS ostida begona bozorning qatori ham `None` beradi va bu
      **to'g'ri**: marshrut ikkala holatda ham **404** qaytaradi (T-01-76 —
      403 obyekt MAVJUDLIGINI tasdiqlardi).
    """
    result = await session.execute(
        select(Payment.shift_id, Payment.kind, Stall.code).where(
            Payment.market_id == market_id,
            Payment.id == payment_id,
            Stall.market_id == Payment.market_id,
            Stall.id == Payment.stall_id,
        )
    )
    row = result.one_or_none()
    if row is None:
        return None
    return PaymentOwner(shift_id=row[0], kind=str(row[1]), stall_code=str(row[2]))


_RECENT_PAYMENTS = text(
    """
    SELECT p.id            AS id,
           p.stall_id      AS stall_id,
           p.vendor_id     AS vendor_id,
           p.service_date  AS service_date,
           p.amount_soum   AS amount_soum,
           p.quote_soum    AS quote_soum,
           p.kind          AS kind,
           p.method        AS method,
           p.override_reason      AS override_reason,
           p.reverses_payment_id  AS reverses_payment_id,
           p.reversal_reason      AS reversal_reason,
           p.request_fingerprint  AS request_fingerprint,
           p.shift_id      AS shift_id,
           p.cashier_id    AS cashier_id,
           p.created_at    AS created_at,
           s.code          AS stall_code,
           EXISTS (
               SELECT 1
                 FROM payments r
                WHERE r.market_id = p.market_id
                  AND r.reverses_payment_id = p.id
           )               AS reversed
      FROM payments p
      JOIN stalls s
        ON s.market_id = p.market_id
       AND s.id = p.stall_id
     WHERE p.market_id = :market_id
       AND p.shift_id = :shift_id
     ORDER BY p.created_at DESC, p.id DESC
     LIMIT :window
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("shift_id", type_=_UUID),
    bindparam("window", type_=Integer()),
)
"""Kassir oynasi — ⛔ `LIMIT` **KODDAGI KONSTANTADAN** (§8.8).

⚠ `:window` parametr ko'rinishida, LEKIN uning **yagona** manbai
  `RECENT_PAYMENT_WINDOW` va `recent_payments()` imzosida `limit`
  argumenti ⛔ **YO'Q** — sabab o'sha konstantaning docstringida.

⚠ `ORDER BY created_at DESC, id DESC` — ikkinchi kalit **determinizm**
  uchun: `created_at` `timestamptz` va bir tranzaksiyada yozilgan ikki
  qator `now()` ning **bir xil** qiymatini oladi (`now()` tranzaksiya
  boshlanishida muzlaydi). Ikkinchi kalitsiz oyna chegarasidagi qator
  har yugurishda o'zgarardi.

⚠ `reversed` — ⛔ **HOSILA**, saqlangan ustun emas: storno o'z qatori
  bo'lgani uchun «bu to'lov bekor qilinganmi?» savoli mavjudlik so'rovi
  bilan javob oladi (D-23).

⚠ `stall_code` JOIN dan: kassir yuzasida rasta ⛔ **kod** bilan
  ko'rinadi, UUID bilan emas (§5.5).
"""


@dataclass(frozen=True, slots=True)
class RecentPayment:
    """Kassir oynasidagi bitta qator — ⛔ `vendor_name`/`phone` YO'Q (C-10)."""

    payment_id: UUID
    stall_code: str
    service_date: date
    amount_soum: int
    kind: str
    method: str
    created_at: datetime
    reversed: bool


async def recent_payments(
    session: AsyncSession, *, market_id: UUID, shift_id: UUID
) -> list[RecentPayment]:
    """Smenaning OXIRGI `RECENT_PAYMENT_WINDOW` (=5) to'lovi — §8.8.

    ⛔ **`limit` ARGUMENTI YO'Q VA QO'SHILMAYDI.** Sabab
       `RECENT_PAYMENT_WINDOW` docstringida: parametr bo'lganda marshrut
       uni o'tkazib yuborishi mumkin bo'lardi va kassir smenasining hamma
       to'lovini yig'ib **tizim summasini** chiqarib olardi — ko'r
       deklaratsiya (D-25) arifmetika bilan buzilardi.

    ⛔ **FAQAT BERILGAN SMENA:** kassir **o'z** smenasini ko'radi.
       `shift_id = NULL` bilan yozilgan to'lov (direktor kiritgan, OQ-6/A5)
       bu ro'yxatga ⛔ **umuman tushmaydi** — `p.shift_id = :shift_id`
       `NULL` ga hech qachon `true` bermaydi va bu **to'g'ri**: u
       kassirning smenasiga tegishli emas.

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        shift_id: kassirning OCHIQ smenasi.

    Returns:
        `created_at DESC` tartibida, ko'pi bilan **5** qator.
    """
    result = await session.execute(
        _RECENT_PAYMENTS,
        {"market_id": market_id, "shift_id": shift_id, "window": RECENT_PAYMENT_WINDOW},
    )
    return [
        RecentPayment(
            payment_id=row["id"],
            stall_code=str(row["stall_code"]),
            service_date=row["service_date"],
            amount_soum=int(row["amount_soum"]),
            kind=str(row["kind"]),
            method=str(row["method"]),
            created_at=row["created_at"],
            reversed=bool(row["reversed"]),
        )
        for row in result.mappings()
    ]


_SHIFT_SYSTEM_TOTAL = text(
    """
    SELECT COALESCE(
               sum(CASE WHEN p.kind = :reversal THEN -p.amount_soum ELSE p.amount_soum END),
               0
           )::bigint AS system_soum
      FROM payments p
     WHERE p.market_id = :market_id
       AND p.shift_id = :shift_id
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("shift_id", type_=_UUID),
    bindparam("reversal", type_=Text()),
)
"""Smenaning TIZIM SUMMASI — `Σ signed(payments)`.

⚠ Belgi ifodasi `billing_repo._SIGNED_PAYMENT_EXPR` bilan **bir xil
  qoidadan** chiqadi (`kind = 'reversal'` -> manfiy), lekin u yerdagi
  konstanta `p.amount_soum` ga `p` aliasi bilan bog'langan va **sotuvchi**
  kesimida ishlatiladi. Bu yerdagi so'rov **smena** kesimida va uni o'sha
  konstantadan import qilish ikki modulning SQL aliaslarini bir-biriga
  bog'lab qo'yardi. ⚠ Qoida bitta bo'lib qoladi: `kind='reversal'` ->
  manfiy, ustun har doim musbat (C-5).

⛔ `COALESCE(..., 0)`: birorta to'lovi yo'q smena uchun natija `NULL` emas,
   **0** — «to'lov bo'lmagan» ni «o'lchov yo'q» dan ajratmaydigan `NULL`
   deklaratsiya bilan solishtirishda `NULL` variance berardi.
"""


async def shift_system_total(session: AsyncSession, *, market_id: UUID, shift_id: UUID) -> int:
    """Smenaning TIZIM SUMMASI — ⛔ **HTTP JAVOBIGA HECH QACHON KIRMAYDI** (D-25).

    =======================================================================
    ⛔⛔ TAQIQ: BU QIYMAT BIRORTA `response_model` MAYDONIGA, `detail` GA
        YOKI LOG XABARIGA ⛔ **CHIQMAYDI** — u faqat **06-10** dagi smena
        yopilishida, deklaratsiya ⛔ **YOZILGANDAN KEYIN** ishlatiladi.

    Sabab UI-SPEC §10.3 va D-25: kassir smenani yopayotganda kassadagi
    pulni ⛔ **ko'r** sanaydi — tizim summasini ko'rmasdan. Agar bu son
    biror javobda ko'rinsa (yoki uni bir necha so'rovdan **yig'ib olish**
    mumkin bo'lsa) deklaratsiya o'sha songa **moslashtirib** yozilardi va
    variance o'lchovi har doim **nol** chiqardi — ya'ni butun nazorat
    mexanizmi jimgina o'lardi va hisobot uni «hammasi joyida» deb
    ko'rsatardi.

    ⚠ AYNAN SHU SABABDAN `GET /payments/recent` oynasi ham serverda
      qat'iy 5 (`RECENT_PAYMENT_WINDOW`): yig'indi yo'li **ikki tomondan**
      to'silgan — bu funksiya javobga chiqmaydi, oyna esa arifmetikaga
      yetarli ma'lumot bermaydi.
    =======================================================================

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        shift_id: yopilayotgan smena.

    Returns:
        Belgili `int` (so'm). To'lovsiz smena uchun **0**.
    """
    result = await session.execute(
        _SHIFT_SYSTEM_TOTAL,
        {
            "market_id": market_id,
            "shift_id": shift_id,
            "reversal": PaymentKind.REVERSAL.value,
        },
    )
    row = result.mappings().one()
    return int(row["system_soum"])


_OPEN_SHIFT = text(
    """
    SELECT sh.id AS id
      FROM cashier_shifts sh
     WHERE sh.market_id = :market_id
       AND sh.cashier_id = :cashier_id
       AND sh.status = :open
     LIMIT 1
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("cashier_id", type_=_UUID),
    bindparam("open", type_=Text()),
)
"""So'rovchining OCHIQ smenasi — `uq_cashier_shifts_..._open` bo'yicha AYNAN BITTA.

⚠ `LIMIT 1` da `ORDER BY` KERAK EMAS va bu tanlov emas, **struktura**:
  qisman `UNIQUE` indeks bir kassirda ikki ochiq smenani **ifodalab
  bo'lmaydigan** qiladi (D-27). Kafolat indeksda, so'rovda emas —
  `billing_repo._STALL_DAY_MONEY` dagi `sa.period @> :as_of` bilan aynan
  bir xil qaror.
"""


async def stall_paid_today(
    session: AsyncSession,
    *,
    market_id: UUID,
    stall_id: UUID,
    service_date: date,
) -> int:
    """Rastaning SHU kun bo'yicha sof to'lovi (storno ayirilgan).

    2026-08-25 (buyurtmachi №10): «bitta rastaga 2-marta to'lov qilish
    mumkin bo'lyapti» — kvota to'plami bugungi to'lovlarni bilmasdi.
    Bu yig'indi 4.5-qadam qulfining YAGONA manbai: to'liq to'langan
    rasta-kunga sababsiz ikkinchi to'lov 409 `stall_already_paid` oladi.

    ⛔ ARIFMETIKA SHU YERDA, marshrutta emas (D-20 ruhi): `payment` qo'shadi,
       `reversal` ayiradi — xuddi `_STALL_PAID_AT_TODAY` (roster) kabi.
    """
    result = await session.execute(
        text(
            """
            SELECT COALESCE(
                     SUM(CASE WHEN kind = 'payment' THEN amount_soum
                              ELSE -amount_soum END),
                     0)
              FROM payments
             WHERE market_id = :market_id
               AND stall_id = :stall_id
               AND service_date = :service_date
            """
        ),
        {"market_id": market_id, "stall_id": stall_id, "service_date": service_date},
    )
    return int(result.scalar_one())


async def open_shift_id(session: AsyncSession, *, market_id: UUID, cashier_id: UUID) -> UUID | None:
    """Foydalanuvchining OCHIQ smenasi (`None` — yo'q).

    ⚠ `None` XATO EMAS: direktor smenasiz to'lov kiritishi mumkin
      (OQ-6/A5), `GET /payments/recent` esa ochiq smena bo'lmasa
      **bo'sh ro'yxat** qaytaradi (404 emas — bo'sh ro'yxat «natija»).
    """
    result = await session.execute(
        _OPEN_SHIFT,
        {"market_id": market_id, "cashier_id": cashier_id, "open": _SHIFT_OPEN},
    )
    row = result.mappings().one_or_none()
    if row is None:
        return None
    shift_id: UUID = row["id"]
    return shift_id
