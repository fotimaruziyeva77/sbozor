"""Bosh ekran ko'rsatkichlari — UCHTA hosila son va boshqa hech nima (RECON-06).

=============================================================================
⛔⛔ MODULNING OMMAVIY YUZASI — AYNAN UCH FUNKSIYA. HAR BIR IMPORT
   PASTKI CHIZIQ BILAN ALIASLANGAN VA BU USLUB EMAS, HIMOYANING O'ZI.

`dir(headline_repo)` dagi pastki chiziqsiz nomlar ro'yxati AYNAN
`receipts_written_count`, `review_queue_count`, `revenue_today_soum` dan
iborat bo'lishi SHART. Sabab Pitfall 1 da: bu modul kassir sessiyasiga
xizmat qiladigan YAGONA o'qish manbai va u orqali PUL YIG'INDISINI
qaytaradigan birorta nomga yetib bo'lmasligi kerak.

Oddiy `from app.repositories.payment_repo import shift_system_total`
(yoki hatto `from sqlalchemy import text` kabi begunoh ko'rinadigan
import) modul nomlar fazosini kengaytiradi va keyingi ijrochi
`headline_repo.shift_system_total(...)` ni marshrutdan chaqira olardi —
ya'ni 6-fazaning uch qatlamli ko'rligi (T-06-53, T-06-59, `shifts.py:126`)
BITTA import bilan chetlab o'tilardi. Alias esa yo'lni STRUKTURAVIY
yopadi: modulda o'sha nom UMUMAN yo'q.

⚠ SHU SABABDAN `from __future__ import annotations` HAM YO'Q — u modulga
  `annotations` nomini bog'lab qo'yadi (o'lchandi). Annotatsiyalar shuning
  uchun ish vaqtidagi HAQIQIY nomlarga (`_UUID`, `_date`, `_AsyncSession`)
  tayanadi va `if TYPE_CHECKING:` bloki bu faylda ISHLATILMAYDI.
=============================================================================

⛔ KESH YO'Q, SAQLANGAN USTUN YO'Q. Uchala son ham HOSILA: ular har
   so'rovda qayta hisoblanadi. Saqlangan hisoblagich «bosh ekranda 12,
   navbatda 7» sinfidagi ajralishning klassik manbai — D-06 sinfi.

⛔ BELGILI PUL QOIDASI BITTA: `kind = 'reversal'` -> manfiy, ustun har
   doim musbat (C-5). `billing_repo._SIGNED_PAYMENT_EXPR` va
   `payment_repo._SHIFT_SYSTEM_TOTAL` bilan AYNI qoida; ifoda bu yerda
   ALOHIDA yozilgan, chunki u yerdagilar sotuvchi va smena kesimida
   (boshqa alias, boshqa `WHERE`), bu esa BOZOR-KUN kesimida.
"""

from datetime import date as _date
from typing import Final as _Final
from uuid import UUID as _UUID

from sbozor_core.enums import PaymentKind as _PaymentKind
from sbozor_core.enums import ReviewQueueKind as _ReviewQueueKind
from sqlalchemy import Date as _Date
from sqlalchemy import Text as _Text
from sqlalchemy import bindparam as _bindparam
from sqlalchemy import text as _text
from sqlalchemy.dialects.postgresql import UUID as _PgUuid
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

__all__ = ["receipts_written_count", "review_queue_count", "revenue_today_soum"]

_UUID_TYPE: _Final = _PgUuid(as_uuid=True)

_REVENUE_TODAY = _text(
    """
    SELECT COALESCE(
               sum(CASE WHEN p.kind = :reversal THEN -p.amount_soum ELSE p.amount_soum END),
               0
           )::bigint AS revenue_soum
      FROM payments p
     WHERE p.market_id = :market_id
       AND p.service_date = :business_date
    """
).bindparams(
    _bindparam("market_id", type_=_UUID_TYPE),
    _bindparam("business_date", type_=_Date()),
    _bindparam("reversal", type_=_Text()),
)
"""Bozorning KUNLIK tushumi — belgili yig'indi.

⛔ `COALESCE(..., 0)`: to'lovsiz kun uchun natija `NULL` emas, **0**.
   `NULL` klientda «ko'rsatkich yo'q» bo'lib chiqardi, holbuki «bugun hali
   birorta to'lov yo'q» — O'LCHANGAN javob (05-14 ning «o'lchanmagan
   sonning o'rniga NOL yozilmaydi» darsining TESKARISI: bu yerda nol
   HAQIQATAN o'lchangan).

⚠ FILTR `service_date` BO'YICHA, `business_date` BO'YICHA EMAS. Ikkalasi
  ham `payments` da bor va ular BOSHQA savolga javob beradi: `service_date`
  — «to'lov QAYSI KUN UCHUN», `business_date` — «qator QACHON yozilgan».
  Direktorning bosh ekrani birinchisini so'raydi (kechqurun kiritilgan
  bugungi patta bugungi tushum), `PAYMENT_STALL_INDEX` ham aynan
  `(market_id, stall_id, service_date)` ustida.
"""

_REVIEW_QUEUE = _text(
    """
    SELECT count(*)::bigint AS pending
      FROM review_assignments ra
     WHERE ra.market_id = :market_id
       AND ra.queue_kind = :queue_kind
       AND NOT EXISTS (
           SELECT 1
             FROM zone_reviews zr
            WHERE zr.review_assignment_id = ra.id
       )
    """
).bindparams(
    _bindparam("market_id", type_=_UUID_TYPE),
    _bindparam("queue_kind", type_=_Text()),
)
"""Nazoratchi navbatining SANOG'I — ⛔ predikat `review_repo` nikidan NUSXA.

=============================================================================
⛔⛔ SHART `review_repo._CLAIM_TEMPLATE` NING `WHERE` I BILAN SO'ZMA-SO'Z
   BIR XIL: `ra.market_id`, `ra.queue_kind` va `NOT EXISTS (zone_reviews)`.
   `JOIN` zanjiri, `ORDER BY`, `LIMIT 1` va `FOR UPDATE ... SKIP LOCKED`
   olib tashlangan — ular BAND OLISH mexanikasi, navbat A'ZOLIGI emas.

Ikkinchi predikat O'YLAB TOPILMAYDI. Ajralib ketishning narxi aniq:
bosh ekranda «12» ko'rinib, navbatni ochganda 7 ta ish chiqishi —
nazoratchi tizimni buzuq deb hisoblardi va sanoqqa boshqa ishonmasdi.
Tenglik `tests/integration/test_headline.py` da XULQIY o'lchanadi:
sanoq nolga tushgan payt `claim_next()` ning `None` qaytargan payti
bilan AYNAN BIR XIL bo'lishi shart.
=============================================================================

⛔ `queue_kind` — FAQAT `uncertain`, `blind_audit` SANOQQA KIRMAYDI [QAROR].
   Ko'r audit namunasining hajmi nazoratchiga OSHKOR QILINMAYDI: bosh
   ekrandagi son «bugun 30 ta audit bandi bor» deb aytib qo'yardi va
   xolis namuna o'z ta'rifini yo'qotardi (05-RESEARCH §C.8 — javob
   ankorlanishi). Nazoratchining ASOSIY ishi noaniq navbat; ko'r audit
   unga ALOHIDA marshrutdan (`GET /review/blind/next`) keladi.

⚠ `market_id` SHARTI RLS USTIGA QO'SHILGAN (ortiqcha emas, ATAYIN): butun
  loyihada tenant filtri so'rovda ham, siyosatda ham yoziladi — bittasi
  buzilganda ikkinchisi ushlab qoladi.
"""

_RECEIPTS_WRITTEN = _text(
    """
    SELECT count(*)::bigint AS receipts
      FROM payments p
     WHERE p.market_id = :market_id
       AND p.service_date = :business_date
       AND p.cashier_id = :cashier_id
       AND p.kind = :payment
    """
).bindparams(
    _bindparam("market_id", type_=_UUID_TYPE),
    _bindparam("business_date", type_=_Date()),
    _bindparam("cashier_id", type_=_UUID_TYPE),
    _bindparam("payment", type_=_Text()),
)
"""Kassir bugun yozgan kvitansiyalar SONI — ⛔ `count(*)`, YIG'INDI EMAS.

=============================================================================
⛔⛔ BU SO'ROVGA PUL USTUNI KIRITILMAYDI. Sabab pastdagi funksiya
   docstringida to'liq yozilgan (Pitfall 1) va u shu yerda TAKRORLANMAYDI —
   ikki nusxa ajralib ketardi.

⛔ `kind = 'payment'`: storno SANOQQA KIRMAYDI. Sabab arifmetik emas,
   MA'NOVIY — bekor qilingan kvitansiya «yozilgan ish» emas. Belgili
   yig'indi qoidasi (`reversal` -> manfiy) bu yerda ISHLAMAYDI: u pul
   uchun, sanoq uchun emas.
=============================================================================
"""


async def revenue_today_soum(
    session: _AsyncSession, *, market_id: _UUID, business_date: _date
) -> int:
    """Bozorning BERILGAN kundagi tushumi (so'm) — `REPORT_VIEW` ko'rsatkichi.

    ⛔ `int`, kasrli tip EMAS (D-07/D-11): so'm butun sonda saqlanadi va
       bu funksiya bo'ylab hech qanday o'girish yo'q.

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        business_date: `Asia/Tashkent` biznes-kuni — ⛔ CHAQIRUVCHI uni
            `business_today()` dan oladi, so'rov parametridan EMAS.

    Returns:
        Belgili `int` (so'm). To'lovsiz kun uchun **0**.
    """
    result = await session.execute(
        _REVENUE_TODAY,
        {
            "market_id": market_id,
            "business_date": business_date,
            "reversal": _PaymentKind.REVERSAL.value,
        },
    )
    return int(result.mappings().one()["revenue_soum"])


async def review_queue_count(session: _AsyncSession, *, market_id: _UUID) -> int:
    """Javobsiz noaniq navbat bandlari soni — `OCCUPANCY_REVIEW` ko'rsatkichi.

    ⚠ `business_date` ARGUMENTI ATAYIN YO'Q. Navbat KUNGA BOG'LANMAGAN:
      bandlar kun oxirida tortiladi va nazoratchi ularni ERTASI kuni
      ko'radi (`review_repo._HAS_ANY_ROUND` docstringidagi ⚠). Kun filtri
      qo'yilsa bosh ekran har ertalab «0» ko'rsatib, navbatda ish turgan
      bo'lardi.

    ⚠ `reviewer_id` ham YO'Q va sabab `claim_next()` niki bilan bir xil:
      navbat BOZORNIKI, nazoratchiniki emas.

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.

    Returns:
        Javob yozilmagan `uncertain` topshiriqlar soni. Navbat bo'sh
        bo'lsa **0** — «ish tugadi» ham O'LCHANGAN javob.
    """
    result = await session.execute(
        _REVIEW_QUEUE,
        {"market_id": market_id, "queue_kind": _ReviewQueueKind.UNCERTAIN.value},
    )
    return int(result.mappings().one()["pending"])


async def receipts_written_count(
    session: _AsyncSession, *, market_id: _UUID, business_date: _date, cashier_id: _UUID
) -> int:
    """Kassir bugun yozgan kvitansiyalar SONI — `PAYMENT_CREATE` ko'rsatkichi.

    =======================================================================
    ⛔⛔ TAQIQ: BU FUNKSIYA HECH QACHON PUL QIYMATINI QAYTARMAYDI VA UNING
        NOMIDA `soum` BO'LMASLIGI SHART. Qaytadigan qiymat — QATORLAR
        SONI.

    Sabab Pitfall 1 da o'lchangan. 6-faza kassirning ko'rligini UCH
    MUSTAQIL QATLAMDA qurgan:

      * `ShiftCloseResponse` da `system_*` maydoni UMUMAN e'lon
        qilinmagan (T-06-59);
      * `GET /payments/recent` oynasi serverda QAT'IY 5 qator
        (`payment_repo.RECENT_PAYMENT_WINDOW`, T-06-53) — ya'ni kassir
        o'z smenasining qatorlarini qo'shib chiqara olmaydi;
      * `variance_soum` faqat `REPORT_VIEW` ostida (`shifts.py:126`).

    Bosh ekranga PUL chiqarish uchalasini ham BIR QATORDA bekor qilardi:
    kassir o'sha sonni o'qib, smena yopishda AYNAN uni deklaratsiya
    qilardi va variance HAR DOIM nol chiqardi. CASH-04 ning ko'r
    deklaratsiyasi arifmetika bilan buzilardi va hisobot buni «hammasi
    joyida» deb ko'rsatardi — ya'ni nazorat asbobi JIMGINA o'lardi.

    ⚠ TALAB BUZILMAYDI: RECON-06 «o'ziga mos bitta asosiy raqam» deydi,
      «yig'im» demaydi. «Bugun 47 ta patta» — kassir uchun haqiqiy va
      foydali ko'rsatkich, D-29 ning «bitta son» shartiga to'liq mos.
    =======================================================================

    Args:
        session: tenant konteksti o'rnatilgan ochiq sessiya.
        market_id: tenant kaliti.
        business_date: `Asia/Tashkent` biznes-kuni (serverda hisoblanadi).
        cashier_id: ⛔ SO'ROVCHINING O'ZI — marshrut uni `principal.user_id`
            dan beradi, so'rov parametridan EMAS: aks holda kassir boshqa
            kassirning kunini so'ray olardi.

    Returns:
        Bugun yozilgan (⛔ BEKOR QILINGANI HAM KIRADIGAN) kvitansiyalar
        soni. Ishlamagan kun uchun **0**.

        ⚠ IZOH TUZATILDI, SO'ROV EMAS (quick 260816-75c). Bu yerda ilgari
          «bekor qilinmagan kvitansiyalar soni» deb yozilgandi va bu
          YOLG'ON edi: `_RECEIPTS_WRITTEN` faqat `kind = 'payment'`
          bo'yicha filtrlaydi va `reversed` holatini UMUMAN ko'rmaydi.
          Yolg'on izoh yo'qligidan YOMONROQ — keyingi o'quvchi mavjud
          bo'lmagan xulqqa ishonardi va sanoqni «nega kamaymadi?» deb
          nosozlik hisoblardi. Sanoqning O'ZI to'g'ri va u
          o'zgartirilmaydi (yuqoridagi ma'noviy sabab), ekrandagi YORLIQ
          esa endi nimani sanayotganini AYTADI.
    """
    result = await session.execute(
        _RECEIPTS_WRITTEN,
        {
            "market_id": market_id,
            "business_date": business_date,
            "cashier_id": cashier_id,
            "payment": _PaymentKind.PAYMENT.value,
        },
    )
    return int(result.mappings().one()["receipts"])
