"""Billing va kassir domenining xato taksonomiyasi — o'n to'rt kod, UCH SIRT.

=============================================================================
⛔⛔ BU FAYL NIMA UCHUN YANGI — VA NEGA KODLAR `occupancy_errors.py` GA
   QO'SHILMAYDI. Sabab MEXANIK, uslubiy emas.

`frontend/scripts/error-codes.test.mjs` bandlik reyestridan ANIQ SON talab
qiladi:

    assert.equal(occupancyConstants.size, 15)
    ZONE_ERROR_CODES   -> expected 9
    REVIEW_ERROR_CODES -> expected 6

Ya'ni `occupancy_errors.py` ga bitta konstanta qo'shish darvozani DARHOL
qizartirardi va uni «tuzatish» yagona yo'li — o'sha aniq sonni oshirish,
bu esa nazorat qiymatining butun ma'nosini yo'q qilardi (u aynan
«reyestrga jimgina kod qo'shildi» holatini ushlash uchun bor).

Shuning uchun 6-faza O'Z reyestrini va `error-codes.test.mjs` ga O'Z blokini
oladi — bandlik bloki TEGILMAYDI (§0.1 M-B).
=============================================================================

D-02: backend **KOD** beradi, matnni frontend uch tilda chizadi. Bu modulda
foydalanuvchi matni YO'Q va bo'lmaydi — u `frontend/messages/*.json` da
(`collect.errorCause.*` / `collect.errorFix.*` va `billing.errorCause.*` /
`billing.errorFix.*`).

=============================================================================
⛔ UCH SIRT REYESTRI — chunki ular UCH BOSHQA EKRAN:

    COLLECT_ERROR_CODES -> kassir yig'ish ekrani (`/collect`)
    SHIFT_ERROR_CODES   -> smena ekrani (`/collect/shift`)
    BILLING_ERROR_CODES -> direktor yuzasi (`/billing`)

⚠ REYESTR NOMI EKRANNI, MATN NAMESPACE'i esa YUZANI bildiradi va ular
  1:1 EMAS: `/collect/shift` — `/collect` ning bolasi, ya'ni SMENA kodlari
  ham `collect.*` namespace'ida yashaydi (§13.2 aynan ikkita xato
  namespace'ini e'lon qiladi: `collect.*` va `billing.*`). Bo'linish shu
  sababdan uch reyestrga qilingan: ekran granulyarligi 06-09 ning router
  bo'linishiga mos keladi, namespace esa foydalanuvchi YUZASIGA.

⚠ `ALL_BILLING_ERROR_CODES` — TO'RT reyestrning BIRLASHMASI, beshinchi
  qo'lda yozilgan ro'yxat EMAS (`OCCUPANCY_ERROR_CODES` bilan aynan bir xil
  qaror, §S-5). Qo'lda yozilgan nusxa bir kun ajralib ketardi va
  `app/schemas.py` allowlist'i reyestrdan kichik bo'lib qolardi: router kod
  bilan `HTTPException` ko'tarardi, allowlist uni tanimay `errors.generic`
  ga tushirardi.
=============================================================================

⚠ HTTP STATUSLARI SHU YERDA KODLANMAYDI, faqat har kodning docstringida
  yoziladi. Status — MARSHRUTNING qarori (06-09) va uni bu yerga qo'yish
  reyestrni router jadvaliga aylantirardi; bitta kod ikki marshrutda ikki
  status bilan qaytishi mumkin bo'lgan holat esa hech qachon
  ifodalanmasdi.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "ALL_BILLING_ERROR_CODES",
    "AMOUNT_UNAVAILABLE",
    "AMOUNT_UNAVAILABLE_REASONS",
    "BILLING_ERROR_CODES",
    "CHARGE_IMMUTABLE",
    "CLIENT_ONLY_ERROR_CODES",
    "COLLECT_ERROR_CODES",
    "IDEMPOTENCY_KEY_REUSED",
    "MARKET_CLOSED",
    "NETWORK_UNREACHABLE",
    "NO_OPEN_SHIFT",
    "OVERRIDE_NOT_APPLICABLE",
    "PAYMENT_ALREADY_REVERSED",
    "REASON_REQUIRED",
    "SERVER_BILLING_ERROR_CODES",
    "SHIFT_ALREADY_CLOSED",
    "SHIFT_ALREADY_OPEN",
    "SHIFT_ERROR_CODES",
    "STALL_NOT_ASSIGNED",
    "STALL_NOT_FOUND",
    "TARIFF_MISSING",
]


# ---------------------------------------------------------------------------
# 1-SIRT — KASSIR YIG'ISH EKRANI (CASH-01…CASH-03). Matn `collect.*` da.
# ---------------------------------------------------------------------------

STALL_NOT_FOUND: Final[str] = "stall_not_found"
"""Kiritilgan raqamda rasta topilmadi (**404**).

⚠ Bu TERISH xatosi va yagona to'g'ri javob — raqamni qayta kiritish. U
  pastdagi `STALL_NOT_ASSIGNED` dan ATAYIN ajratilgan: u yerda rasta BOR.
"""

TARIFF_MISSING: Final[str] = "tariff_missing"
"""Rastaning shu kunga tegishli tarifi belgilanmagan (**422**).

Tarif `business_date` bo'yicha `stall_category_periods` + `tariffs` orqali
yechiladi (D-09). Bo'shliq bo'lsa summa TAXMIN QILINMAYDI — «yo'q summa,
yo'q summa» (§9.4). Bu kod ayni paytda `amount_unavailable_reason` ning
QIYMATI hamdir (pastdagi `AMOUNT_UNAVAILABLE_REASONS`).
"""

AMOUNT_UNAVAILABLE: Final[str] = "amount_unavailable"
"""Server summani bermadi — TEXNIK nosozlik (**422**).

⛔ `MARKET_CLOSED` DAN ATAYIN AJRATILGAN. Bu kodning matni «Sahifani
   yangilang» deydi, ya'ni u NOSOZLIK deb o'qiladi — va o'sha o'qilish
   yopiq kun uchun BUTUNLAY noto'g'ri bo'lardi (pastga qarang).
"""

MARKET_CLOSED: Final[str] = "market_closed"
"""Bugun bozor yopiq va eski qarz ham yo'q — asoslangan summa UMUMAN yo'q (**422**).

=========================================================================
⛔ NEGA `AMOUNT_UNAVAILABLE` YARAMAYDI — VA NEGA BU KOD IKKI JOYDA YASHAYDI.

D-10 bo'yicha yopiq kunda bugungi patta HISOBLANMAYDI. Lekin D-24 ning
«MEXANIZM MOSLASHTIRILDI» bandi buni kengaytiradi: to'lov endi SOTUVCHI
DARAJASIDAGI kredit, ya'ni yopiq kunda ham ESKI QARZNI olish mumkin
(§9.4: «To'lanadigan — faqat `outstanding_soum`»). Demak:

  * qarz BOR   -> so'rov RAD ETILMAYDI, to'lov **201** bilan yoziladi;
  * qarz YO'Q  -> yozadigan hech nima yo'q va AYNAN SHU kod qaytadi.

`amount_unavailable` ning matni «Server summani bermadi / Sahifani
yangilang» — u NOSOZLIK deb o'qiladi va kassir sahifani qayta-qayta
yangilardi, holbuki bu NORMAL kalendar holati.

⚠ IKKINCHI ISTE'MOLCHISI: bu satr `StallDayMoney.unavailable_reason`
  ning ham qiymati (§9.4) va `resolve_stall_day_money()` (06-06) uni
  pastdagi `AMOUNT_UNAVAILABLE_REASONS` dan IMPORT qiladi — literal
  ikkinchi marta YOZILMAYDI.
=========================================================================
"""

STALL_NOT_ASSIGNED: Final[str] = "stall_not_assigned"
"""Rasta bor, lekin unga sotuvchi biriktirilmagan (**409**).

=========================================================================
⛔ NEGA `STALL_NOT_FOUND` (404) YARAMAYDI.

404 kassirga «bunday rasta yo'q» deb YOLG'ON aytardi va u to'g'ri kodni
qayta-qayta kiritib, oxirida raqamni noto'g'ri deb hisoblardi. Aslida
rasta REESTRDA bor — `stall_assignments` da o'sha sanaga tegishli qator
yo'q (`vendor_id is None`).

Bu HOLAT, nosozlik emas, va uning yechimi BOSHQA EKRANDA: biriktirishlar
sahifasida sotuvchini biriktirish.

⚠ STRUKTURAVIY ASOSI: `Payment.vendor_id` `NOT NULL` (06-04), ya'ni bu
  so'rov uchun QATOR SHAKLI umuman yo'q — D-28 «kimdir qarzdor, lekin kim
  ekani noma'lum» yozuvini imkonsiz qiladi.

⛔ `REASON_REQUIRED` ham yaramaydi: u SUMMA haqida, bu esa TO'LOVCHI
   haqida.
=========================================================================
"""

OVERRIDE_NOT_APPLICABLE: Final[str] = "override_not_applicable"
"""Sabab yuborildi, lekin summa serverning taklifiga TENG (**422**).

=========================================================================
⛔ BU `REASON_REQUIRED` NING TESKARISI va ularni birlashtirish mumkin emas:

    `reason_required`         — summa CHETLASHGAN, sabab YO'Q;
    `override_not_applicable` — summa CHETLASHMAGAN, sabab BOR.

Sababni JIMGINA tashlab yuborish auditga ma'nosiz yozuv qoldirardi
(«direktor kechirdi» — hech narsa kechirilmagan holda) va D-02 ning
«nizoda qaysi yozuv dalil?» sharti buzilardi.

⚠ STRUKTURAVIY ASOSI: `payments` dagi
  `CHECK ((amount_soum = quote_soum) = (override_reason IS NULL))` (06-04)
  bunday qatorni IFODALAB BO'LMAYDIGAN qiladi — ya'ni kod sxemaning
  HTTP chegarasidagi ko'zgusi, qo'shimcha qoida emas.
=========================================================================
"""

REASON_REQUIRED: Final[str] = "reason_required"
"""Summa serverning taklifidan chetlashgan, lekin sabab-kod tanlanmagan (**422**).

D-19: summani o'zgartirish ATAYIN qimmat. Yopiq ro'yxatdan sabab tanlash —
o'sha narxning o'zi; uni ixtiyoriy qilish erkin summani qaytarib
keltirardi (spec §4.7 — korrupsiya teshigi).
"""

IDEMPOTENCY_KEY_REUSED: Final[str] = "idempotency_key_reused"
"""Bir xil kalit BOSHQA summa yoki boshqa rasta bilan qayta yuborildi (**409**).

⛔ TAKROR SO'ROVNING O'ZI XATO EMAS: D-21 bo'yicha AYNAN bir xil tana bilan
   kelgan takror so'rov **200** va o'sha to'lovni qaytaradi — tarmoq
   uzilishida qayta yuborish kassir uchun KO'RINMAS bo'lishi kerak.

Bu kod faqat KALIT O'SHA, TANA BOSHQA holatida qaytadi: u to'lov varag'i
qayta ishlatilganini bildiradi va yechimi — sahifani yangilab, YANGI kalit
bilan kiritish (§8.7 kalit hayot davri).
"""

PAYMENT_ALREADY_REVERSED: Final[str] = "payment_already_reversed"
"""Bu to'lov allaqachon bekor qilingan (**409**).

`payments` APPEND-ONLY (D-23): storno o'z QATORI bo'ladi va ikkinchi storno
ikkinchi manfiy qator yozib, qoldiqni IKKI MARTA kamaytirardi.
"""


# ---------------------------------------------------------------------------
# 2-SIRT — SMENA (CASH-04). Matn ham `collect.*` da (`/collect/shift`).
# ---------------------------------------------------------------------------

NO_OPEN_SHIFT: Final[str] = "no_open_shift"
"""To'lov yozish uchun ochiq smena yo'q (**409**).

Smena — kassir oqimining SHARTI, alohida ish emas (§4.2): ochiq smenasiz
yozilgan to'lov keyin hech qaysi ko'r deklaratsiyaga tushmasdi va variance
o'z maxrajini yo'qotardi.
"""

SHIFT_ALREADY_OPEN: Final[str] = "shift_already_open"
"""Kassirda allaqachon ochiq smena bor (**409**).

D-27: bir vaqtda AYNAN BITTA ochiq smena va u qisman `UNIQUE` indeks bilan
STRUKTURAVIY majburlanadi. Bu kod — o'sha indeksning HTTP chegarasidagi
ko'zgusi (ikki oynadan bir vaqtda ochish — POYGA holati).
"""

SHIFT_ALREADY_CLOSED: Final[str] = "shift_already_closed"
"""Bu smena allaqachon yopilgan (**409**).

⛔ QAYTA OCHISH YO'LI YO'Q va bu D-25 ning himoyasi: yopilgan smenani qayta
   ochish deklaratsiyani TIZIM SUMMASIGA moslashtirish imkonini berardi,
   ya'ni ko'r o'lchovning butun ma'nosi yo'qolardi.
"""


# ---------------------------------------------------------------------------
# 3-SIRT — DIREKTOR YUZASI (BILL-02, BILL-03). Matn `billing.*` da.
# ---------------------------------------------------------------------------

CHARGE_IMMUTABLE: Final[str] = "charge_immutable"
"""Yozilgan hisobni o'zgartirishga urinish (**409**).

D-07: `daily_charges` o'zgarmas — shartsiz `BEFORE UPDATE OR DELETE`
trigger (`zone_reviews` bilan aynan bir xil mexanizm). Tuzatish FAQAT
`charge_adjustments` orqali: sabab-kod, aktor va audit bilan, ALOHIDA
yozuv sifatida.
"""


# ---------------------------------------------------------------------------
# 4-SIRT — MIJOZ TOMONI. Matn `collect.*` da.
# ---------------------------------------------------------------------------

NETWORK_UNREACHABLE: Final[str] = "network_unreachable"
"""Tarmoq uzildi — so'rov serverga UMUMAN yetib bormadi.

=========================================================================
⛔ BU KOD SERVERDAN HECH QACHON QAYTMAYDI va shuning uchun u yuqoridagi
   UCH SIRT reyestridan TASHQARIDA turadi: uni `COLLECT_ERROR_CODES` ga
   qo'yish `app/schemas.py` allowlist'iga hech qachon kelmaydigan kodni
   kiritardi va reyestr «server nima qaytarishi mumkin» degan savolga
   noto'g'ri javob berardi.

   U `ALL_BILLING_ERROR_CODES` da BOR, chunki FRONTEND darvozasi uni
   talab qiladi: `lib/billing-errors.ts` unga `{tone, surface}` beradi va
   uchala tilda `errorCause`/`errorFix` juftligi bo'lishi shart (§13.7
   reyestrida u ham bor — toast №6 aynan shu kod).
=========================================================================
"""


COLLECT_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        STALL_NOT_FOUND,
        TARIFF_MISSING,
        AMOUNT_UNAVAILABLE,
        MARKET_CLOSED,
        STALL_NOT_ASSIGNED,
        OVERRIDE_NOT_APPLICABLE,
        REASON_REQUIRED,
        IDEMPOTENCY_KEY_REUSED,
        PAYMENT_ALREADY_REVERSED,
    }
)
"""Kassir yig'ish ekranining kodlari — matni `collect.errorCause.*` / `errorFix.*`."""

SHIFT_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        NO_OPEN_SHIFT,
        SHIFT_ALREADY_OPEN,
        SHIFT_ALREADY_CLOSED,
    }
)
"""Smena ekranining kodlari — matni ham `collect.*` da (`/collect/shift`)."""

BILLING_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        CHARGE_IMMUTABLE,
    }
)
"""Direktor yuzasining kodlari — matni `billing.errorCause.*` / `errorFix.*`."""

CLIENT_ONLY_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        NETWORK_UNREACHABLE,
    }
)
"""Serverdan HECH QACHON qaytmaydigan kodlar — matni `collect.*` da.

⚠ ALOHIDA REYESTR, chunki `app/schemas.py` ning allowlist'i «server nima
  qaytarishi mumkin» degan savolga javob beradi va bu kod o'sha savolning
  javobi EMAS. Frontend darvozasi esa uni TALAB qiladi.
"""


AMOUNT_UNAVAILABLE_REASONS: Final[frozenset[str]] = frozenset(
    {
        MARKET_CLOSED,
        TARIFF_MISSING,
    }
)
"""`StallDayMoney.unavailable_reason` ning YOPIQ qiymat to'plami (§9.4).

=========================================================================
⛔ BU YUZA REYESTRI EMAS va u `ALL_BILLING_ERROR_CODES` ga KIRMAYDI —
   ikkala kod ham allaqachon `COLLECT_ERROR_CODES` da. Bu to'plamning
   vazifasi boshqa: u proyeksiya javobidagi «nega summa yo'q?» maydonining
   RUXSAT ETILGAN qiymatlarini nomlaydi.

Ikki iste'molchisi bor va ikkalasi ham LITERALNI TAKRORLAMAYDI:

  * `resolve_stall_day_money()` (06-06) shu to'plamdan IMPORT qiladi —
    `"market_closed"` satri kodda ikkinchi marta yozilmaydi;
  * `pendingStallSchema` dagi `z.enum(["market_closed","tariff_missing"])`
    (06-03) — shu to'plamning frontend yarmi.

⚠ NEGA AYNAN SHU IKKITASI: qolgan o'n ikki kod so'rovni RAD ETADI, bu
  ikkitasi esa javobni BERADI («summa yo'q, sababi shu») — ya'ni ular
  javob TANASIDA yashaydi, `detail` da emas. Aralashtirish proyeksiyani
  har qanday xato bilan «summasiz» qilib qo'yardi.
=========================================================================
"""


SERVER_BILLING_ERROR_CODES: Final[frozenset[str]] = (
    COLLECT_ERROR_CODES | SHIFT_ERROR_CODES | BILLING_ERROR_CODES
)
"""Serverdan `detail` sifatida qaytishi MUMKIN bo'lgan kodlar — o'n uchta.

⚠ `app/schemas.py::MARKET_ERROR_CODES` AYNAN SHU to'plamni import qiladi,
  `ALL_BILLING_ERROR_CODES` ni EMAS: allowlist «server nima qaytarishi
  mumkin» degan savolga javob beradi va `network_unreachable` o'sha
  savolning javobi emas (yuqoridagi `CLIENT_ONLY_ERROR_CODES` ga qarang).

⚠ Ajratish ATAYIN va u TANLOVNI YO'Q QILADI: 06-09 marshrutlarni yozganda
  «qaysi to'plamni import qilay?» degan savol tug'ilmaydi — bu yerda
  allaqachon nomlangan.
"""

ALL_BILLING_ERROR_CODES: Final[frozenset[str]] = (
    SERVER_BILLING_ERROR_CODES | CLIENT_ONLY_ERROR_CODES
)
"""Billing domenining BARCHA kodlari — o'n to'rtta.

⚠ HOSILA, qo'lda yozilgan ro'yxat EMAS (`OCCUPANCY_ERROR_CODES` bilan aynan
  bir xil qaror, §S-5).

⚠ ISTE'MOLCHISI — FRONTEND darvozasi (`scripts/error-codes.test.mjs`): u
  `lib/billing-errors.ts` jadvalining kalitlarini va uchala locale'dagi
  `errorCause`/`errorFix` juftligini AYNAN shu son bilan solishtiradi.
  Server tomonda esa `SERVER_BILLING_ERROR_CODES` ishlatiladi.
"""
