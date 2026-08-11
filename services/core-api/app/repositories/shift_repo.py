"""Smena — ochish, KO'R DEKLARATSIYA bilan yopish va direktor hisoboti (CASH-04).

=============================================================================
⛔⛔ BU MODUL IKKI QATLAMNI XIZMAT QILADI VA ULARNING YUZASI BIR XIL EMAS.

    repository qaytaradi  ->  `ShiftRow` (`system_soum` BILAN)
    HTTP javobi beradi    ->  `ShiftCloseResponse` (`system_soum` SIZ)

Farq ATAYIN va u shu yerda YOZIB QO'YILDI, chunki keyingi ijrochi uchun
eng tabiiy qadam — `ShiftRow` ni to'g'ridan-to'g'ri `response_model` qilib
qo'yish bo'lardi va D-25 ⛔ **BITTA SATR** bilan buzilardi.

`system_soum` repository qatorida BOR, chunki u BAZAGA yoziladi
(`cashier_shifts.system_soum`) va `shift_report()` uni direktorga
qaytaradi. U HTTP ning `close` javobiga ⛔ **CHIQMAYDI** — serializator
uni `app/schemas.py::ShiftCloseResponse` da UMUMAN e'lon qilmaydi
(`BlindItemResponse` naqshi).

=============================================================================
⛔⛔ D-25 — KO'R DEKLARATSIYA VA UNING IKKI QATLAMI.

Kassir smenani yopayotganda kassadagi naqdni ⛔ **sanab** kiritadi —
tizim summasini ⛔ **ko'rmasdan**. Tizim summasi shu funksiya ichida,
⛔ **serverda** hisoblanadi (`payment_repo.shift_system_total()`) va
deklaratsiya ⛔ **yozilgandan keyin** ishlatiladi.

Ikki qatlam:

  * **ilova** — ikkinchi `close_shift()` `ShiftAlreadyClosed` beradi
    (marshrut **409**), ya'ni deklaratsiyani qayta yozish yo'li YO'Q;
  * **sxema** — `shift_declaration_immutable()` trigger (`0020`) `closed`
    smenaning HAR QANDAY `UPDATE` ini `23514` bilan rad etadi.

Ilova qatlami sxemaning ⛔ **ko'zgusi**, ikkinchi qoida emas.

=============================================================================
⛔⛔ D-26 — VARIANCE IKKI TOMONLAMA VA ⛔ TO'G'RILASH YUZASI OCHILMAYDI.

Bu modulda ⛔ **variance ni o'zgartiradigan, «to'g'rilaydigan» yoki
deklaratsiyani qayta yozadigan funksiya YO'Q va yozilmaydi.** Kamomad
(`< 0`) ham, ortiqcha (`> 0`) ham MA'NO tashiydi va ikkalasi ham
`shift_report()` da ⛔ **ishorasi bilan** qaytariladi.

⛔ Modul kattaligini oluvchi `abs` chaqiruvi bu faylda ⛔ **umuman
   uchramaydi** va bu MEXANIK qulflangan (`sbozor_core/billing.py` dagi
   `variance()` bilan aynan bir xil qaror: qabul mezoni fayl matnini
   grep qiladi). Ishorani yo'qotish D-26 ni bitta chaqiruv bilan bekor
   qilardi: «kamomad» va «ortiqcha» bir xil songa aylanardi va direktor
   ularni ⛔ **ajrata olmasdi**.

⛔ Variance ⛔ **saqlanmaydi** (Pitfall 7): `cashier_shifts` da unga ustun
   yo'q va bo'lmaydi ham. Sabab mexanik — `assert_safe_soum()` manfiy
   qiymatni ⛔ **rad etadi** (`money.py:65-85`), ya'ni kamomadni ustunga
   yozib bo'lmasdi. Saqlanadigan ikki son — `declared_soum` va
   `system_soum`; variance ularning ⛔ **hosilasi** va u
   `sbozor_core.billing.variance()` da ⛔ **YOLG'IZ** yashaydi.

=============================================================================
⛔⛔ VARIANCE CHEGARASI VA OGOHLANTIRISHI BU YERDA YOZILMAYDI (OQ-7/A6).

Chegara ⛔ **kelishilmagan** va u ⛔ **bozor bo'yicha sozlanadigan**
bo'lishi kerak: kodga qo'yilgan literal son ⛔ **barcha bozorlarga**
tarqalardi va Karmana uchun ma'noli qiymat Navoiyning katta bozorida
kunda o'nlab yolg'on signal berardi. Ogohlantirish kaliti ham, uning
reyestr yozuvi ham bu modulda ⛔ **YO'Q** — egasi **8-faza** (UI-SPEC
§17 O-06).

=============================================================================
⛔ D-27 — BIR KASSIRDA BIR VAQTDA AYNAN BITTA OCHIQ SMENA.

`open_shift()` ⛔ **«ochiq smena bormi?» deb TEKSHIRMAYDI.** Majburiyat
qisman `UNIQUE` indeksda (`uq_cashier_shifts_market_id_cashier_open`,
`status = 'open'` predikati bilan) va poyga ⛔ **DB ga topshiriladi** —
`nvr_repo.py:506-521` da o'rnatilgan qoidaning aynan takrori.

Oldindan tekshirish ⛔ **«tekshir-keyin-yoz» poygasini** tug'dirardi: ikki
oynadan bir vaqtda bosilgan «Smenani ochish» ikkalasiga ham bo'sh holatni
ko'rsatardi va kassir to'lovlarni ⛔ **ikki smenaga** bo'lib yozardi —
nomuvofiqlik ikkiga bo'linib ⛔ **YO'QOLARDI**.

=============================================================================
⛔ CHAQIRUVCHI UCHUN SHART: TENANT KONTEKSTI (`billing_repo` bilan bir xil).

Har funksiya `set_tenant_context()` ostidagi sessiyada chaqiriladi. RLS
`cashier_shifts` ga to'liq qo'llanadi, ya'ni begona bozorning `shift_id`
si bilan kelgan so'rov `close_shift()` da ⛔ **0 qator** ko'radi va
`ShiftNotFound` oladi (marshrut **404**).

=============================================================================
⛔ AUDIT BU YERDA YOZILMAYDI. `cashier_shifts` `AUDITED_TABLES` da, ya'ni
   `fn_audit_row()` trigger'i INSERT va UPDATE qatorlarini ⛔ **o'zi**
   yozadi. Ilova darajasidagi `write_app_audit()` chaqiruvi ⛔ **ikkinchi
   (dublikat)** jurnal qatorini qo'shardi.

=============================================================================
⛔ PUL — BUTUN SO'M (`BIGINT` <-> `int`), D-11. Kasrli tip bu modulda
   umuman uchramaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from sbozor_core.billing import variance
from sbozor_core.enums import PaymentKind, ShiftStatus
from sqlalchemy import BigInteger, Date, Text, bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.exc import IntegrityError

from app.repositories.payment_repo import shift_system_total
from app.repositories.stall_repo import sqlstate_of

if TYPE_CHECKING:
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "ShiftAlreadyClosed",
    "ShiftAlreadyOpen",
    "ShiftNotFound",
    "ShiftNotOwned",
    "ShiftReport",
    "ShiftReportRow",
    "ShiftRow",
    "close_shift",
    "open_shift",
    "open_shift_for",
    "shift_report",
]

_UUID = PgUuid(as_uuid=True)

_OPEN: Final[str] = ShiftStatus.OPEN.value
_CLOSED: Final[str] = ShiftStatus.CLOSED.value
"""Holat qiymatlari — ⛔ ENUMDAN, so'rov matnidagi LITERAL emas.

`payment_repo._SHIFT_OPEN` va `billing_repo._OCCUPIED` bilan aynan bir xil
sabab: literal yozilganda enum o'zgargan kuni filtr jimgina hech nimaga
tushmasdi — so'rov ishlayverardi, faqat natija bo'sh bo'lardi.
"""

_UNIQUE_VIOLATION: Final[str] = "23505"
"""`uq_cashier_shifts_market_id_cashier_open` buzilishining SQLSTATE i.

⚠ KONSTRAYT NOMI BO'YICHA EMAS, SQLSTATE BO'YICHA aniqlanadi va sabab
  `stall_repo.sqlstate_of()` docstringida: asyncpg o'ramida
  `constraint_name` `None` bo'ladi va RLS yoqilgan jadvalda Postgres
  xatoning `DETAIL` qatorini ham o'chiradi.

⚠ BU JADVALDA `23505` NING BOSHQA MANBAI YO'Q: yagona `UNIQUE` lar —
  `uq_cashier_shifts_market_id_id` (`(market_id, id)`, `id` esa
  `uuidv7()` dan) va o'sha qisman indeks. Ya'ni `INSERT` yo'lida bu kod
  bir ma'noli.
"""


class ShiftAlreadyOpen(RuntimeError):
    """Bu kassirda allaqachon ochiq smena bor (D-27).

    Marshrut buni ⛔ **409 `shift_already_open`** ga aylantiradi.

    ⚠ TIP `RuntimeError` DAN, `ValueError` DAN EMAS — `payment_repo`
      dagi bilan bir xil qaror: bu dastur mantig'idagi holat, kirish
      validatsiyasi emas, va `ValueError` uni Pydantic xatolari bilan
      bitta sinfga qo'shib yuborardi.
    """


class ShiftAlreadyClosed(RuntimeError):
    """Smena allaqachon yopilgan — deklaratsiya ⛔ **O'ZGARMAS** (D-25).

    Marshrut buni ⛔ **409 `shift_already_closed`** ga aylantiradi va
    qator ⛔ **TEGILMAYDI**: `close_shift()` ning `UPDATE` i
    `status = 'open'` sharti bilan yuradi, ya'ni ikkinchi urinish
    ⛔ **0 qator** yozadi.
    """


class ShiftNotOwned(RuntimeError):
    """Smena BOSHQA kassirniki — marshrut **403** qiladi.

    ⛔ 404 EMAS VA BU FARQ ATAYIN: qator MAVJUDLIGI allaqachon
       tasdiqlangan (u so'rovchining O'Z bozorida, RLS undan o'tkazdi),
       ya'ni 404 hech qanday ma'lumot yashirmasdi — faqat kassirga
       noto'g'ri yo'l ko'rsatardi. Begona BOZOR ning smenasi esa
       `ShiftNotFound` beradi va u **404** — T-01-76 saqlanadi.

    ⛔ NEGA UMUMAN DARVOZA KERAK: begona smenani yopish o'sha kassirning
       ⛔ **ko'r deklaratsiyasini** boshqa odam nomidan yozardi va
       variance hisobotida sababi topilmaydigan farq chiqardi.
    """


class ShiftNotFound(RuntimeError):
    """Bunday smena yo'q — yoki u BOSHQA bozorniki (marshrut **404**).

    ⚠ IKKALA HOLAT HAM BIR XIL JAVOB (T-01-76): RLS ostida begona
      bozorning qatori shu sessiya uchun MAVJUD EMAS, ya'ni 404 yolg'on
      emas — aynan haqiqat. Ularni ajratish `shift_id` larni javob kodi
      bo'yicha sanab chiqish yo'lini ochardi.
    """


@dataclass(frozen=True, slots=True)
class ShiftRow:
    """Smena qatori — ⛔ **TO'LIQ**, ya'ni `system_soum` BILAN.

    ⛔⛔ BU DATAKLASS `response_model` QILIB QO'YILMAYDI. Modul
        docstringining birinchi bandi: `system_soum` bu yerda BOR (u
        bazaga yoziladi va direktor hisobotida qaytariladi), lekin
        `POST /shifts/{id}/close` javobida ⛔ **UMUMAN e'lon
        qilinmaydi** (D-25). Serializator — `app/schemas.py::
        ShiftCloseResponse`, va u AYNAN to'rt kalitli.

    ⚠ `declared_soum` / `system_soum` / `closed_at` ochiq smenada `None`:
      ustun `NULL` bo'lgani — smena hali OCHIQ degani, «kassir
      kiritmadi» degani EMAS.
    """

    shift_id: UUID
    cashier_id: UUID
    status: str
    opened_at: datetime
    closed_at: datetime | None
    declared_soum: int | None
    system_soum: int | None


@dataclass(frozen=True, slots=True)
class ShiftReportRow:
    """Direktor hisobotidagi bitta smena — ⛔ variance BILAN.

    ⛔ KASSIRNING ISMI YO'Q, faqat `cashier_id` (C-10 + UI-SPEC §5.5).
       Ism klientda, MAVJUD va AUDIT QILINGAN `GET /users` dan
       joinlanadi: moliyaviy marshrutga shaxsiy-ma'lumot maydonini
       qo'shish `PERSONAL_ROUTES` ni o'stirardi va keyingi ijrochi
       ko'chiradigan naqsh bo'lardi.

    ⚠ `declared_soum`/`system_soum`/`closed_at` bu yerda `None` EMAS va
      bu tasodif emas: hisobot ⛔ **faqat yopilgan** smenalarni
      qaytaradi, `ck_cashier_shifts_closed_has_declaration` esa
      `declared_soum IS NOT NULL <-> status = 'closed'` ni MAJBURLAYDI.
    """

    shift_id: UUID
    cashier_id: UUID
    opened_at: datetime
    closed_at: datetime
    declared_soum: int
    system_soum: int
    variance_soum: int
    """⛔ `declared - system` — BELGILI son (D-26).

    Manfiy = **kamomad**, musbat = **ortiqcha**, nol = **mos keldi**.
    `sbozor_core.billing.variance()` dan keladi va SQL da ⛔ **ikkinchi
    marta hisoblanmaydi**: ikki joyda yozilgan ayirish bir kun ajralib
    ketardi va o'shanda ekrandagi son bilan hisobotdagi son
    ⛔ **ikkalasi ham to'g'ri** bo'lardi.
    """


@dataclass(frozen=True, slots=True)
class ShiftReport:
    """Kun kesimidagi smenalar + ⛔ SMENASIZ to'lovlarning ALOHIDA sanog'i.

    =======================================================================
    ⛔⛔ §11.5 FLAG'I — «SMENASIZ TO'LOVLAR» NOMLANADI (OQ-6/A5).

    `shift_id IS NULL` bo'lgan to'lovlar birorta kassir qutisiga
    ⛔ **tushmagan**, ya'ni ular variance hisobiga ⛔ **KIRMAYDI** va bu
    ⛔ **to'g'ri**. Ammo ular ⛔ **PUL**: ko'rsatilmasa, ular hisobotdan
    ⛔ **JIMGINA yo'qolardi** va kun yig'indisi sababsiz kamayardi
    (D-14 ruhi: o'lchanadigan miqdor ⛔ **nomlanadi**).

    Shuning uchun ikkala son ham ALOHIDA maydon: sanog'i ⛔ **va**
    summasi. Faqat summani berish «bitta katta to'lovmi yoki ellikta
    kichikmi?» savolini javobsiz qoldirardi.
    =======================================================================

    ⛔ **NOL — NATIJA:** birorta smena yopilmagan kunda ham uchala
       maydon QAYTADI (`rows=()`, ikkala hisoblagich `0`). «Bu kunda
       smena yo'q» bilan «hisoblagich ishlamayapti» bir xil
       ko'rinmasligi kerak (`occupancy.py:122-124` prinsipi).
    """

    rows: tuple[ShiftReportRow, ...]
    shiftless_payment_count: int
    shiftless_payment_soum: int


_SHIFT_COLUMNS: Final[str] = (
    "id, cashier_id, status, opened_at, closed_at, declared_soum, system_soum"
)
"""Uchala so'rov ham AYNAN shu ustunlarni AYNAN shu tartibda oladi.

⚠ RO'YXAT BITTA: `INSERT ... RETURNING`, `SELECT` va `UPDATE ...
  RETURNING` bir xil shaklni berishi SHART, aks holda `_row()` ikki xil
  kortejni ochishga urinardi va nosozlik faqat bitta yo'lda — ya'ni
  kamdan-kam — ko'rinardi (`payment_repo._PAYMENT_COLUMNS` naqshi).

⛔ `S608` QUYIDAGI BESH SO'ROVDA O'CHIRILGAN VA SABAB TOR
   (`billing_repo.py:1501` va `review_repo.py:231-237` naqshi):
   f-string ga tushadigan YAGONA qiymat — AYNAN shu konstanta, ya'ni
   modul darajasidagi USTUN NOMLARI ro'yxati. Foydalanuvchi kiritmasi
   so'rovga faqat `bindparam()` orqali kiradi va bittasi ham
   interpolatsiya qilinmaydi.
"""


def _row(raw: dict[str, object]) -> ShiftRow:
    """Mappingdan `ShiftRow` — `NULL` lar `None` bo'lib qoladi."""
    declared = raw["declared_soum"]
    system = raw["system_soum"]
    return ShiftRow(
        shift_id=raw["id"],  # type: ignore[arg-type]
        cashier_id=raw["cashier_id"],  # type: ignore[arg-type]
        status=str(raw["status"]),
        opened_at=raw["opened_at"],  # type: ignore[arg-type]
        closed_at=raw["closed_at"],  # type: ignore[arg-type]
        declared_soum=None if declared is None else int(declared),  # type: ignore[call-overload]
        system_soum=None if system is None else int(system),  # type: ignore[call-overload]
    )


_INSERT_SHIFT = text(
    f"""
    INSERT INTO cashier_shifts (market_id, cashier_id, status)
    VALUES (:market_id, :cashier_id, :open)
    RETURNING {_SHIFT_COLUMNS}
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("cashier_id", type_=_UUID),
    bindparam("open", type_=Text()),
)
"""Smenani ochish — ⛔ **OLDINDAN TEKSHIRUVSIZ** (D-27, modul docstringi).

⚠ `id` BERILMAYDI: ustun `uuidv7()` server-defaultidan to'ladi
  (`0020._uuid_pk()`), ya'ni identifikator vaqt-tartiblangan va ilovada
  ikkinchi UUID manbai paydo bo'lmaydi.

⚠ `declared_soum` VA `system_soum` HAM BERILMAYDI — ikkalasi ham `NULL`
  va bu «smena hali ochiq» ning YAGONA ifodasi
  (`ck_cashier_shifts_closed_is_paired` uni majburlaydi).
"""

_SELECT_OPEN_SHIFT = text(
    f"""
    SELECT {_SHIFT_COLUMNS}
      FROM cashier_shifts
     WHERE market_id = :market_id
       AND cashier_id = :cashier_id
       AND status = :open
     LIMIT 1
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("cashier_id", type_=_UUID),
    bindparam("open", type_=Text()),
)
"""So'rovchining OCHIQ smenasi — `GET /shifts/open` uchun.

⚠ `LIMIT 1` da `ORDER BY` KERAK EMAS va bu tanlov emas, **struktura**:
  qisman `UNIQUE` indeks bir kassirda ikki ochiq smenani ⛔ **ifodalab
  bo'lmaydigan** qiladi (`payment_repo._OPEN_SHIFT` bilan aynan bir xil
  qaror).

⛔ BU SO'ROV `open_shift()` DAN CHAQIRILMAYDI. U `open_shift_for()` ning
   O'ZI, ya'ni **o'qish** yuzasi. Uni yozish yo'liga oldindan tekshiruv
   sifatida qo'shish D-27 ning butun mulohazasini bekor qilardi.
"""

_SELECT_SHIFT = text(
    f"""
    SELECT {_SHIFT_COLUMNS}
      FROM cashier_shifts
     WHERE market_id = :market_id
       AND id = :shift_id
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("shift_id", type_=_UUID),
)
"""Yopish oldidan smenani o'qish — UCH darvoza uchun (404 / 403 / 409)."""

_CLOSE_SHIFT = text(
    f"""
    UPDATE cashier_shifts
       SET status = :closed,
           closed_at = now(),
           declared_soum = :declared_soum,
           system_soum = :system_soum
     WHERE market_id = :market_id
       AND id = :shift_id
       AND status = :open
    RETURNING {_SHIFT_COLUMNS}
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("shift_id", type_=_UUID),
    bindparam("declared_soum", type_=BigInteger()),
    bindparam("system_soum", type_=BigInteger()),
    bindparam("open", type_=Text()),
    bindparam("closed", type_=Text()),
)
"""Yopish — ⛔ **AYNAN BITTA `UPDATE`**, va bu O'LCHANGAN ZARURAT.

=============================================================================
⛔⛔ IKKI `UPDATE` YOZISH MUMKIN EMAS EDI.

Tabiiy ko'rinadigan shakl — avval `status='closed', closed_at=now()`,
keyin `declared_soum`/`system_soum` — sxema tomonidan ⛔ **RAD ETILADI**:
`shift_declaration_immutable()` ning birinchi shoxi `OLD.status =
'closed'` bo'lgan HAR QANDAY `UPDATE` ni `23514` bilan to'xtatadi, ya'ni
ikkinchi bayonot ⛔ **hech qachon** o'tmasdi (06-04 T3 da o'lchangan).

Teskari tartib (avval summalar, keyin status) `ck_cashier_shifts_
closed_is_paired` va `closed_has_declaration` juftlangan `CHECK` lariga
urilardi — ular `declared_soum IS NOT NULL` va `status = 'closed'` ni
⛔ **bir vaqtda** talab qiladi.

Ya'ni yagona ifodalanadigan shakl — ⛔ **hamma ustun bitta bayonotda**.

=============================================================================
⛔ `AND status = :open` — POYGA DB GA TOPSHIRILADI (D-27 ning mulohazasi).

Ikki bir vaqtdagi «Yopish» bosishi: birinchisi qatorni `closed` qiladi,
ikkinchisi ⛔ **0 qator** yozadi va `ShiftAlreadyClosed` oladi. Shartsiz
`UPDATE` ikkinchisini sxema qo'riqchisiga olib borardi va kassir aniq
409 o'rniga ⛔ **500** ko'rardi — nosozlik esa faqat ikki oynali holatda,
ya'ni dala sinovida chiqardi.

⚠ Shart ilova qatlamidagi `status != 'open'` tekshiruvini ALMASHTIRMAYDI:
  u foydalanuvchiga ANIQ sabab beradi (409 `shift_already_closed`), bu
  yerdagisi esa POYGANI yopadi. Ikkalasi ham kerak.
"""

_SHIFT_REPORT_ROWS = text(
    f"""
    SELECT {_SHIFT_COLUMNS}
      FROM cashier_shifts
     WHERE market_id = :market_id
       AND business_date = :day
       AND status = :closed
     ORDER BY opened_at, id
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("day", type_=Date()),
    bindparam("closed", type_=Text()),
)
"""Kun kesimidagi YOPILGAN smenalar — direktor yuzasi.

⛔ **FAQAT `closed`.** Ochiq smenaning variance i ⛔ **ma'nosiz**:
   deklaratsiya hali yozilmagan (`NULL`), tizim summasi esa hamon
   o'sib turibdi. Uni «0 farq» deb ko'rsatish `NULL` ni nol deb yozish
   bo'lardi — D-14 ning aynan taqiqlaydigan narsasi.

⛔ **KUN — `business_date`, `service_date` EMAS** (C-2). Savol «qaysi
   kunda kassa hisobi olindi», «qaysi kun UCHUN pul yig'ildi» emas:
   kechagi qarzni bugun to'lagan sotuvchining puli ⛔ **bugungi**
   kassirning qutisiga tushadi va uning deklaratsiyasiga kiradi.
   `service_date` bo'yicha guruhlash o'sha pulni kechagi kunga
   yuborardi va ikkala kunning variance i ham noto'g'ri chiqardi.

⚠ `ORDER BY opened_at, id` — ikkinchi kalit DETERMINIZM uchun: bir
  tranzaksiyada yozilgan ikki qator `now()` ning BIR XIL qiymatini oladi
  (`payment_repo._RECENT_PAYMENTS` da o'rnatilgan qoida).
"""

_SHIFTLESS_PAYMENTS = text(
    """
    SELECT count(*)::bigint AS shiftless_payment_count,
           COALESCE(
               sum(CASE WHEN p.kind = :reversal THEN -p.amount_soum ELSE p.amount_soum END),
               0
           )::bigint AS shiftless_payment_soum
      FROM payments p
     WHERE p.market_id = :market_id
       AND p.business_date = :day
       AND p.shift_id IS NULL
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("day", type_=Date()),
    bindparam("reversal", type_=Text()),
)
"""⛔ SMENASIZ to'lovlar — §11.5 FLAG'ining o'lchovi (OQ-6/A5).

⚠ BELGI IFODASI `payment_repo._SHIFT_SYSTEM_TOTAL` BILAN BIR XIL
  QOIDADAN (`kind = 'reversal'` -> manfiy, ustun har doim musbat — C-5).
  Konstanta import qilinmaydi: o'sha so'rov `shift_id` kesimida, bu esa
  `shift_id IS NULL` kesimida, va ikkalasini bitta matnga bog'lash
  modullarning SQL aliaslarini bir-biriga bog'lardi.

⛔ `count(*)` VA `sum(...)` BIRGA, IKKI SO'ROV EMAS: ular AYNI qatorlar
   ustidan hisoblanadi va ikkinchi so'rov ikkalasini bir-biridan
   ajratib qo'yishi mumkin bo'lardi (oradagi yangi to'lov).

⛔ `COALESCE(..., 0)`: smenasiz to'lov bo'lmagan kunda natija `NULL`
   emas, **0** — «to'lov yo'q» ni «o'lchov yo'q» dan ajratmaydigan
   `NULL` klientda bo'sh katak bo'lib ko'rinardi.
"""


async def open_shift(session: AsyncSession, *, market_id: UUID, cashier_id: UUID) -> ShiftRow:
    """Smenani ochadi — ⛔ **OLDINDAN TEKSHIRUVSIZ** (D-27).

    =======================================================================
    ⛔⛔ «OCHIQ SMENA BORMI?» BU YERDA TEKSHIRILMAYDI.

    `INSERT` bajariladi va qisman `UNIQUE` indeksning buzilishi
    (`uq_cashier_shifts_market_id_cashier_open`, SQLSTATE `23505` —
    `UniqueViolation`) domen istisnosi `ShiftAlreadyOpen` ga
    aylantiriladi.

    Sabab `nvr_repo.py:506-521` da o'rnatilgan: oldindan tekshirish
    ⛔ **«tekshir-keyin-yoz» poygasini** tug'dirardi — ikki so'rov bir
    vaqtda bo'sh holatni ko'rib, ikkalasi ham smena ochardi va kassir
    to'lovlarni ikki smenaga bo'lib yozardi. O'shanda variance
    ⛔ **har ikkalasida ham kichik** ko'rinardi, ya'ni nomuvofiqlik
    ikkiga bo'linib YO'QOLARDI (T-06-63).
    =======================================================================

    ⛔ **`SAVEPOINT` MAJBURIY VA BU O'LCHANGAN FAKT, EHTIYOTKORLIK EMAS.**
       `IntegrityError` Postgres tranzaksiyasini ABORT holatiga qo'yadi va
       undan keyingi har qanday bayonot `InFailedSqlTransaction` beradi —
       ya'ni 409 javobi jimgina **500** ga aylanardi (`nvr.py:562-577`
       dagi aynan o'sha dars, 03-06 da o'lchangan). `begin_nested()`
       konstrayt buzilishini SAVEPOINT ichida ushlab qoladi, tashqi
       tranzaksiya esa TIRIK qoladi.

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        cashier_id: smena EGASI. ⛔ Marshrut buni **so'rovchining
            o'zidan** oladi (`principal.user_id`), mijozdan EMAS —
            boshqa kassir nomidan smena ochish yo'li YO'Q.

    Returns:
        Yangi ochilgan smena (`status='open'`, summalar `None`).

    Raises:
        ShiftAlreadyOpen: bu kassirda allaqachon ochiq smena bor.
    """
    try:
        async with session.begin_nested():
            result = await session.execute(
                _INSERT_SHIFT,
                {"market_id": market_id, "cashier_id": cashier_id, "open": _OPEN},
            )
            row = result.mappings().one()
    except IntegrityError as exc:
        if sqlstate_of(exc) != _UNIQUE_VIOLATION:
            # ⛔ BOSHQA KONSTRAYT — JIMGINA 409 QILINMAYDI. FK buzilishi
            #    (`cashier_id` bunday foydalanuvchi yo'q) «smena
            #    allaqachon ochiq» EMAS va uni shunday deb ko'rsatish
            #    nosozlikni butunlay boshqa joyga yuborardi.
            raise
        raise ShiftAlreadyOpen(
            f"cashier_id={cashier_id} da bu bozorda allaqachon ochiq smena bor (D-27)"
        ) from exc
    return _row(dict(row))


async def open_shift_for(
    session: AsyncSession, *, market_id: UUID, cashier_id: UUID
) -> ShiftRow | None:
    """So'rovchining OCHIQ smenasi — `GET /shifts/open` uchun (`None` — yo'q).

    ⚠ `None` XATO EMAS VA U **404 GA AYLANMAYDI** (UI-SPEC §10.1): «ochiq
      smena yo'q» — ekranning ikki holatidan BIRI (`EmptyState` +
      `[Smenani ochish]`), uchinchisi yo'q. 404 klientni «tarmoq/server
      nosozligi» shoxiga yuborardi va kassir smenani umuman ochа
      olmasdi.

    ⛔ BU FUNKSIYA `open_shift()` DAN CHAQIRILMAYDI — sabab `open_shift()`
       docstringida (D-27: poyga DB ga topshiriladi).
    """
    result = await session.execute(
        _SELECT_OPEN_SHIFT,
        {"market_id": market_id, "cashier_id": cashier_id, "open": _OPEN},
    )
    row = result.mappings().one_or_none()
    if row is None:
        return None
    return _row(dict(row))


async def close_shift(
    session: AsyncSession,
    *,
    market_id: UUID,
    shift_id: UUID,
    cashier_id: UUID,
    declared_soum: int,
) -> ShiftRow:
    """Smenani KO'R deklaratsiya bilan yopadi — ⛔ **BITTA `UPDATE`** (D-25).

    =======================================================================
    ⛔⛔ QADAMLAR TARTIBI MAJBURIY:

      1. smenani o'qish            -> topilmasa `ShiftNotFound`   (**404**)
      2. `status != 'open'`        -> `ShiftAlreadyClosed`        (**409**)
      3. `cashier_id` mos emas     -> `ShiftNotOwned`             (**403**)
      4. tizim summasi ⛔ SERVERDA -> `shift_system_total()`
      5. ⛔ BITTA `UPDATE`         -> `status`+`closed_at`+ikki summa

    Teskari tartib (masalan avval yozib, keyin tekshirish) deklaratsiyani
    yozib bo'lib rad etardi — `shift_declaration_immutable()` esa uni
    ortga qaytarishga YO'L QO'YMASDI.
    =======================================================================

    ⛔ **4-QADAM SERVERDA VA U JAVOBGA CHIQMAYDI.** `system_soum`
       `payment_repo.shift_system_total()` dan keladi va u ⛔ **HTTP
       javobiga hech qachon kirmaydi** (o'sha funksiyaning docstringidagi
       TAQIQ). Kassir uni ko'rsa (yoki bir necha so'rovdan **yig'ib
       olsa**) deklaratsiyani o'sha songa ⛔ **moslashtirib** yozardi va
       variance har doim NOL chiqardi — butun nazorat mexanizmi jimgina
       o'lardi, hisobot esa uni «hammasi joyida» deb ko'rsatardi.

    ⛔ **`declared_soum = 0` RUXSAT ETILADI** (UI-SPEC §10.2): butun
       smena terminal orqali o'tgan kun ⛔ **REAL holat**. `> 0` sharti
       kassirni SOXTA naqd summa yozishga majburlardi. Manfiy qiymat esa
       chegarada rad etiladi — `assert_safe_soum()` (marshrutda,
       `soumSchema` orqali) va `ck_cashier_shifts_declared_soum_non_
       negative` (sxemada).

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        shift_id: yopilayotgan smena.
        cashier_id: SO'ROVCHI (`principal.user_id`) — egalik darvozasi.
        declared_soum: kassir SANAB kiritgan naqd (0 RUXSAT).

    Returns:
        Yopilgan smena qatori — ⛔ **`system_soum` bilan**, lekin
        serializator uni E'LON QILMAYDI (klass docstringi).

    Raises:
        ShiftNotFound: qator yo'q yoki begona bozorniki (**404**).
        ShiftAlreadyClosed: allaqachon yopilgan (**409**), qator TEGILMAGAN.
        ShiftNotOwned: boshqa kassirning smenasi (**403**).
    """
    existing = await session.execute(_SELECT_SHIFT, {"market_id": market_id, "shift_id": shift_id})
    current = existing.mappings().one_or_none()
    if current is None:
        raise ShiftNotFound(f"shift_id={shift_id} bu bozorda topilmadi")

    if str(current["status"]) != _OPEN:
        # ⛔ D-25: DEKLARATSIYA O'ZGARMAS. Bu shox `UPDATE` gacha yetib
        #    bormaydi, ya'ni qator BAYT-BAYT tegilmagan qoladi.
        raise ShiftAlreadyClosed(f"shift_id={shift_id} allaqachon yopilgan (D-25)")

    if current["cashier_id"] != cashier_id:
        raise ShiftNotOwned(f"shift_id={shift_id} boshqa kassirning smenasi")

    # ---- 4-QADAM: tizim summasi ⛔ SERVERDA (D-25).
    system_soum = await shift_system_total(session, market_id=market_id, shift_id=shift_id)

    # ---- 5-QADAM: ⛔ BITTA bayonot (`_CLOSE_SHIFT` docstringi).
    result = await session.execute(
        _CLOSE_SHIFT,
        {
            "market_id": market_id,
            "shift_id": shift_id,
            "declared_soum": declared_soum,
            "system_soum": system_soum,
            "open": _OPEN,
            "closed": _CLOSED,
        },
    )
    closed = result.mappings().one_or_none()
    if closed is None:
        # ⛔ POYGA: yuqoridagi o'qishdan keyin BOSHQA so'rov smenani yopib
        #    ulgurdi (`AND status = :open` sharti 0 qator qaytardi).
        #    Javob AYNI: 409 — kassir uchun holat bir xil.
        raise ShiftAlreadyClosed(
            f"shift_id={shift_id} parallel so'rov tomonidan yopildi (D-25/D-27)"
        )
    return _row(dict(closed))


async def shift_report(session: AsyncSession, *, market_id: UUID, day: date) -> ShiftReport:
    """Kun kesimidagi smenalar va variance — ⛔ **YAGONA** variance yuzasi.

    =======================================================================
    ⛔⛔ VARIANCE FAQAT SHU FUNKSIYADAN CHIQADI (UI-SPEC §10.4).

    Marshruti `GET /shifts?day=` va u `report_view` ostida — kassirda bu
    huquq ⛔ **YO'Q** va berilmaydi. Sabab: `system = declared − variance`,
    ya'ni ⛔ **bitta ayirish** — variance ni kassirga qaytarish
    `system_soum` ni qaytarish bilan ⛔ **matematik jihatdan bir xil** va
    D-25 ni hisob-kitob bilan buzardi.

    ⚠ 06-RESEARCH SC#5(d) ning «`declared > system` holatida ham
      qaytariladi» talabi AYNAN shu marshrutda bajariladi va o'lchanadi.
    =======================================================================

    ⛔ **VARIANCE `sbozor_core.billing.variance()` DAN** — SQL da ikkinchi
       marta hisoblanmaydi va modul kattaligi ⛔ **OLINMAYDI** (D-26,
       Pitfall 7). Ishora MA'NO tashiydi: `< 0` kamomad, `> 0` ortiqcha, `= 0` mos
       keldi. «Ortiqcha naqdni jimgina yutish kamomadni yashirish bilan
       BIR XIL xato.»

    ⛔ **BU YERDA «TO'G'RILASH» YO'LI YO'Q** (D-26): variance ni
       o'zgartiradigan, tasdiqlaydigan yoki kechiradigan funksiya bu
       modulda ⛔ **umuman yozilmagan** va marshruti ham yo'q.

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        day: hisobot kuni (`business_date` — `_SHIFT_REPORT_ROWS`
            docstringidagi C-2 bandi).

    Returns:
        ⛔ **NOL — NATIJA:** bo'sh kunda ham `rows=()` va ikkala
        hisoblagich `0` bilan qaytadi.
    """
    shifts = await session.execute(
        _SHIFT_REPORT_ROWS, {"market_id": market_id, "day": day, "closed": _CLOSED}
    )
    rows = tuple(
        ShiftReportRow(
            shift_id=raw["id"],
            cashier_id=raw["cashier_id"],
            opened_at=raw["opened_at"],
            closed_at=raw["closed_at"],
            declared_soum=int(raw["declared_soum"]),
            system_soum=int(raw["system_soum"]),
            # ⛔ SOF FUNKSIYA QAYTA ISHLATILADI — ayirish bu yerda
            #    YOZILMAYDI (D-16 ning shakli: bitta haqiqat manbai).
            variance_soum=variance(int(raw["declared_soum"]), int(raw["system_soum"])),
        )
        for raw in shifts.mappings()
    )

    shiftless = await session.execute(
        _SHIFTLESS_PAYMENTS,
        {"market_id": market_id, "day": day, "reversal": PaymentKind.REVERSAL.value},
    )
    aggregate = shiftless.mappings().one()

    return ShiftReport(
        rows=rows,
        shiftless_payment_count=int(aggregate["shiftless_payment_count"]),
        shiftless_payment_soum=int(aggregate["shiftless_payment_soum"]),
    )
