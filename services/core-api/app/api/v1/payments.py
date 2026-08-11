"""To'lov yozish — FAZANING **PUL YOZADIGAN** YUZASI (CASH-01…CASH-03).

=============================================================================
⛔⛔ UCH MARSHRUT — VA `PATCH`/`PUT`/`DELETE` **UMUMAN YOZILMAYDI** (D-23).

    POST /payments                        -> 201 (yangi) / 200 (takror)
    POST /payments/{payment_id}/reverse   -> 201 (storno qatori)
    GET  /payments/recent                 -> oxirgi 5, PARAMETRSIZ

`payments` APPEND-ONLY. Tuzatish ⛔ **FAQAT storno** — yangi qator,
`reverses_payment_id` bilan asl qatorga bog'langan. Nizoda IKKALA yozuv
ham ko'rinadi: «to'ladi» va «bekor qilindi, sababi shu» (D-02). To'lovni
tahrirlash yoki o'chirish yo'li «pul kelmagan» da'vosini ⛔ **IZSIZ**
qoldirardi (T-06-52) — shuning uchun bu modulda o'sha metodlar **umuman
e'lon qilinmagan** va OpenAPI to'plam tengligi buni qulflaydi.

=============================================================================
⛔⛔ HANDLERDA PUL ARIFMETIKASI YO'Q (D-16, D-20).

    asoslangan summalar -> `sbozor_core.billing.payment_quote_set()`  (06-01)
    yig'indi            -> `sbozor_core.billing.total_due_soum()`     (06-01)
    bugungi tarif       -> `billing_repo.resolve_stall_day_money()`   (06-06)
    eski qarz           -> `billing_repo.vendor_outstanding()`        (06-06)
    yozish/idempotentlik-> `payment_repo`                             (06-09)

⛔ **`amount + outstanding` SHAKLI BU FAYLDA YO'Q.** Qo'shish amali
   `total_due_soum()` da va u YAGONA (06-01 docstringi): ikki joyda
   yozilgan qo'shish bir kun ajralib ketardi va o'shanda ekrandagi
   «jami» bilan serverdagi «jami» **ikkalasi ham to'g'ri** bo'lardi.

=============================================================================
⛔⛔ 422 NING SHARTI — **BO'SH KVOTA TO'PLAMI**, «bugungi summa yo'q» EMAS.

UI-SPEC §9.4 ning to'lanadigan ustuni `market_closed` va `tariff_missing`
qatorlari uchun ⛔ **«Faqat `outstanding_soum`»** deb yozilgan va u tarmoq
xatosi qatoridagi «⛔ Hech nima» dan **ATAYIN** farqlangan.

⛔ **NEGA ESKI SHART (`amount_soum is None` -> 422) NOTO'G'RI EDI:** yopiq
   kunda qarzi bor sotuvchidan pul olish §9.4 da **ochiq ruxsat etilgan**,
   `POST /payments` esa CASH-01 ning ⛔ **yagona** kirish nuqtasi — ya'ni
   o'sha shart eski qarzni ⛔ **undirib bo'lmaydigan** qilardi va bu real,
   **takrorlanadigan** holat (har dushanba, har bayram).

Shuning uchun to'liq rad etishning ⛔ **YAGONA** yo'li — `payment_quote_set()`
ning **bo'sh** natijasi (`()`), ya'ni «bugun bu rastaga asoslangan summa
umuman yo'q» (yopiq kun **VA** qarz ham `<= 0`). Sabab esa ⛔ **ko'rinadi**:
`detail` da `market_closed` / `tariff_missing` / `amount_unavailable`.

=============================================================================
⛔ HUQUQ IMZO ALIASIDA, DEKORATORDA EMAS — VA `require_any_permission()`
   ISHLATILMAYDI (C-9).

`tests/tenancy/test_personal_data_coverage.py:691-706` o'sha darvozani
ko'targan marshrutlar to'plamini AYNAN
`("/api/v1/snapshots/{snapshot_id}/image",)` ga TENG bo'lishini talab
qiladi — to'plam YOPIQ va bu fayl unga tegmaydi.

`POST` marshrutlari `PAYMENT_CREATE` ostida (u ⛔ **YOLG'IZ kassirda**,
UI-SPEC §5.6), `GET /payments/recent` esa `BILLING_COLLECT_VIEW` ostida
(u kassir, bozor admini va direktorda BOR).

=============================================================================
⚠ `payments` `AUDITED_TABLES` DA **YO'Q** (append-only, hajm katta), ya'ni
  DB-trigger u yerda hech nima yozmaydi va `write_app_audit()` ⛔ **YAGONA**
  audit yo'li. Aynan shuning uchun `enums.py` `PAYMENT_OVERRIDE` va
  `PAYMENT_REVERSE` a'zolarini qo'shgan (CASH-02).
=============================================================================
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sbozor_core.billing import payment_quote_set
from sbozor_core.enums import AuditAction, PaymentKind
from sbozor_core.timeutil import business_today

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories import billing_repo, payment_repo
from app.schemas import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentReverseRequest,
    RecentPaymentsResponse,
)
from app.security.audit import write_app_audit
from app.security.rbac import Permission
from app.services.billing_errors import (
    AMOUNT_UNAVAILABLE,
    IDEMPOTENCY_KEY_REUSED,
    OVERRIDE_NOT_APPLICABLE,
    PAYMENT_ALREADY_REVERSED,
    REASON_REQUIRED,
    STALL_NOT_ASSIGNED,
    STALL_NOT_FOUND,
)

# ⚠ `UUID` ISH VAQTIDA IMPORT QILINADI, `TYPE_CHECKING` OSTIDA EMAS — VA BU
#   O'LCHANGAN ZARURIYAT (`occupancy.py:70-75`, `reviews.py`). `from
#   __future__ import annotations` ostida annotatsiyalar SATR bo'lib qoladi
#   va FastAPI ularni Pydantic uchun YECHA olmaydi: `PydanticUserError: ...
#   is not fully defined`. Nosozlik marshrutda emas, OpenAPI sxemasini
#   quruvchi meta-testda ko'rinadi.

log = structlog.get_logger(__name__)

__all__ = ["router"]

router = APIRouter(tags=["payments"])

PaymentWriterDep = Annotated[Principal, Depends(require_permission(Permission.PAYMENT_CREATE))]
"""⛔ `PAYMENT_CREATE` — D-07 matritsasida **YOLG'IZ kassirda** (§5.6).

Bozor adminida ham, direktorda ham bu huquq YO'Q va bu tanlov emas,
mahsulot qarori: pul yig'ish — **kassirning ishi**, direktor esa uni
`report_view` bilan **ko'radi** (spec §4.7). Shuning uchun ikkala `POST`
marshrut ham cross-tenant matritsasida ⛔ **KASSIR sessiyasi** bilan
chaqiriladi (`CASHIER_ROUTES`) — odatdagi admin sessiyasi **403** olardi
va tenant darvozasi umuman sinalmasdi (OP-9).

⛔ `require_any_permission()` ISHLATILMAYDI — sabab modul docstringida.
"""

CollectViewerDep = Annotated[
    Principal, Depends(require_permission(Permission.BILLING_COLLECT_VIEW))
]
"""⛔ `PAYMENT_CREATE` EMAS — VA BU FARQ ATAYIN.

`GET /payments/recent` ni direktor ham ko'rishi mumkin (§5.6): u yozuvni
**o'qiydi**, yozmaydi. Huquq uch rolda (`cashier`, `market_admin`,
`director`), ya'ni bu marshrut matritsada ⛔ **odatdagi** sessiyadan
yuradi va `CASHIER_ROUTES` ga **tushmaydi**.
"""


_NOT_FOUND = "not_found"
"""Cross-tenant va mavjud bo'lmagan to'lov uchun BIR XIL javob (T-01-76).

⚠ `SERVER_BILLING_ERROR_CODES` REYESTRIGA QO'SHILMAYDI — `billing.py:115`
  bilan aynan bir xil qaror: reyestr DOMEN kodlari uchun («bu amalni nega
  bajarib bo'lmadi»), bu esa STRUKTURAVIY javob va u hech qanday yo'l
  ko'rsatmaydi — ko'rsatishi ham mumkin emas.
"""

_FORBIDDEN = "forbidden"
"""Boshqa smenaning to'lovini bekor qilishga urinish (**403**).

⛔ REYESTRGA QO'SHILMAYDI VA BU ONGLI: `ALL_BILLING_ERROR_CODES` ning
   soni `frontend/scripts/error-codes.test.mjs` tomonidan uchala
   locale'dagi `errorCause`/`errorFix` juftligi bilan SOLISHTIRILADI,
   ya'ni matnsiz yangi kod o'sha darvozani DARHOL qizartirardi (06-08
   ning `day_in_future` bandi bilan aynan bir xil holat).

⚠ Bu holat KLIENT YO'LIDA yuz bermaydi: `GET /payments/recent` faqat
  so'rovchining O'Z ochiq smenasining qatorlarini qaytaradi, ya'ni
  06-11 ning [Bekor qilish] tugmasi begona `payment_id` ni umuman
  ko'rsatmaydi. Shakl `imports.py:206` dan olingan.
"""


def _market_id(principal: Principal) -> UUID:
    """Sessiyadagi bozor — `billing.py:137-144` dagi jufti bilan bir xil shakl."""
    market_id = principal.market_id
    if market_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail={"error_code": "market_not_selected"}
        )
    return market_id


def _reject(code: str, http_status: int) -> HTTPException:
    """`detail` ⛔ **SATR**, lug'at EMAS — va bu klient kontrakti.

    `frontend/src/lib/api-client.ts::detailOf()` `detail` ni AYNAN satr
    deb o'qiydi (`typeof parsed.data.detail === "string"`); lug'at
    yuborilganda u bo'sh satr qaytaradi va `billing-errors.ts` kodni
    tanimay `errors.generic` matnini chizadi — ya'ni kassir «bu rastaga
    sotuvchi biriktirilmagan» o'rniga umumiy xato ko'rardi va nosozlik
    FAQAT dala sinovida ko'rinardi.

    ⚠ Shakl `billing.py::_report_day()` dagi 422 bilan bir xil
      (`detail=_DAY_IN_FUTURE`), `_market_id()` dagi lug'at bilan emas:
      o'sha lug'at 01-fazadan meros va u KLIENT YO'LIDA yuz bermaydi
      (bozor tanlanmagan sessiya kassir panelini umuman ochmaydi).
    """
    return HTTPException(status_code=http_status, detail=code)


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreateRequest,
    principal: PaymentWriterDep,
    session: TenantSessionDep,
    response: Response,
) -> PaymentResponse:
    """To'lovni qayd etish — CASH-01 ning ⛔ **YAGONA** kirish nuqtasi.

    =======================================================================
    ⛔⛔ QADAMLAR TARTIBI MAJBURIY — ENG ARZON RAD ETISHDAN ENG QIMMATIGA.

      1. bozor yechimi                          -> 403
      2. `stall_code` -> rasta va bugungi pul    -> 404 `stall_not_found`
      2.5 TAKROR SO'ROV (D-21)                   -> 200 / 409
      3. `vendor_id is None`                     -> 409 `stall_not_assigned`
      4. asoslangan summalar to'plami (SERVERDA) -> 422 (bo'sh to'plam)
      5. `quote_soum` tanlovi + sabab darvozasi  -> 422
      6. idempotent yozish                       -> 201 / 200 / 409
      7. CASH-02 auditi                          -> `payment_override`

    Teskari tartib (masalan avval yozib, keyin tekshirish) qatorni
    yozib bo'lib rad etardi — `payments` esa APPEND-ONLY, ya'ni uni
    ORTGA QAYTARIB bo'lmasdi.

    ⛔ **2.5-QADAM 3/4/5 DAN OLDIN TURADI VA BU TARTIB D-21 NING O'ZI.**

    Uchala darvoza ham birinchi so'rov O'ZGARTIRGAN holatdan hosila:
    `vendor_outstanding()` hamma to'lovni ayiradi va `as_of` bilan
    filtrlanmaydi, ya'ni retryda `payment_quote_set()` **boshqa**
    to'plam qaytaradi. Misol (tarif 15 000, qarz 45 000, `[Qarzni ham
    olish]` -> 60 000):

        so'rov 1  qoldiq  45 000   kvotalar (15000, 45000, 60000) -> 201
        retry     qoldiq −15 000   kvotalar (15000,)              -> 422

    Ya'ni pul YOZILGAN bo'lsa ham kassir qattiq xato ko'rardi va
    `[Qayta yuborish]` o'sha 422 ni qayta-qayta olardi — pul yo'lidagi
    chiqishsiz tugun. Kalitni narxlashdan OLDIN qarash bu shoxni
    umuman ochmaydi.
    =======================================================================

    ⛔ **3-QADAM: `vendor_id is None` -> 409 `stall_not_assigned` VA BOSHQA
       HECH QANDAY SHOX YO'Q.**

    Rasta **BOR**, lekin `stall_assignments` bo'shlig'ida —
    `sbozor_core/periods.py:29-33` bo'shliqni ⛔ **ATAYIN ruxsat etadi**
    (sotuvchi ketdi, yangisi hali topilmadi). `Payment.vendor_id` esa
    `NOT NULL` (06-04), ya'ni ⛔ **bu so'rov uchun QATOR SHAKLI mavjud
    emas**: `vendor_id` ni `NULL` bilan yozish D-28 ning «kimdir
    qarzdor, lekin kim ekani noma'lum» yozuvini tug'dirardi va qarz
    hisoboti (BILL-03) uni hech qaysi sotuvchiga bog'lay olmasdi.

    ⛔ **404 `stall_not_found` ISHLATILMAYDI:** u kassirga «bunday rasta
       yo'q» deb **yolg'on** aytardi va u to'g'ri kodni qayta-qayta
       terib, oxirida raqamni noto'g'ri deb hisoblardi (D-28 ning nizo
       modeli). Kod 06-02 ning **14 kodli** reyestrida ALLAQACHON bor —
       bu marshrut reyestrga ⛔ **hech nima qo'shmaydi**.

    ⚠ Bu holat 06-07 da ⛔ **anomaliya** qatorini ham tug'diradi
      (`unassigned_occupied`), ya'ni javob «yo'q» bo'lsa ham **hodisa
      yozilgan** bo'ladi va 7-faza uni case sifatida oladi.

    =======================================================================
    ⛔ **5-QADAM — CASH-02 / D-19 DARVOZASI, IKKI TOMONLAMA:**

      `amount_soum in quotes`      -> `quote_soum = amount_soum`;
                                      sabab BERILGAN bo'lsa ⛔ **422
                                      `override_not_applicable`**
      `amount_soum not in quotes`  -> `quote_soum = quotes[0]` (ustuvorlik
                                      tartibidagi BIRINCHI); sabab YO'Q
                                      bo'lsa ⛔ **422 `reason_required`**

    ⛔ Sababni **jimgina tashlab yuborish TAQIQLANADI**: auditga ma'nosiz
       yozuv qolardi («direktor kechirdi» — hech narsa kechirilmagan
       holda) va D-02 ning «nizoda qaysi yozuv dalil?» sharti buzilardi.
       06-04 ning juftlangan `CHECK` i bunday qatorni ⛔ **ifodalab
       bo'lmaydigan** qiladi, ya'ni bu kod sxemaning **ko'zgusi**.

    ⚠ **Qisman VA ortiqcha to'lov shu shoxdan o'tadi** (OQ-4/A4): ular
      **ruxsat**, lekin sabab-kod **talab qiladi** — §8.6 ning «ATAYIN
      QIMMAT» qarori. ⛔ `[Qarzni ham olish]` esa sabab ⛔ **talab
      qilmaydi**: u `quotes` ning **uchinchi** elementi (§9.6 — bir
      qo'shimcha bosish, sabab dialogi EMAS).

    =======================================================================
    ⛔ **6-QADAM — D-21: TAKROR SO'ROV KASSIR UCHUN KO'RINMAS.**

    Aynan bir xil tana bilan kelgan ikkinchi so'rov ⛔ **200** va
    **O'SHA** `payment_id` oladi (409 EMAS). Bir xil kalit + **boshqa**
    tana esa ⛔ **409 `idempotency_key_reused`** — aks holda yangi summa
    **jimgina yo'qolardi** (Pitfall 4).

    ⚠ Bu qadam 2.5 dan KEYIN ham qoladi va IKKALASI HAM kerak: 2.5
      so'rovlar KETMA-KET kelganini (retry), 6 esa ular PARALLEL
      kelganini (`SELECT` bilan `INSERT` orasidagi poyga) hal qiladi.
    =======================================================================
    """
    market_id = _market_id(principal)
    as_of = business_today()
    override_reason = None if payload.reason_code is None else payload.reason_code.value

    # ---- 2-QADAM: rasta va bugungi pul — IKKALASI BITTA so'rovdan (D-16).
    matches = await billing_repo.resolve_stall_day_money(
        session, market_id=market_id, as_of=as_of, stall_code=payload.stall_code
    )
    if not matches:
        raise _reject(STALL_NOT_FOUND, status.HTTP_404_NOT_FOUND)
    money = matches[0]

    # ---- 2.5-QADAM: TAKROR SO'ROV ⛔ PUL QAYTA NARXLANMASDAN yopiladi (D-21).
    replayed = await payment_repo.find_by_idempotency_key(
        session, market_id=market_id, idempotency_key=payload.idempotency_key
    )
    if replayed is not None:
        # ⛔ `quote_soum` — QATORNING O'ZINIKI, qayta hisoblangani EMAS.
        #    Yangi kvota to'plami birinchi so'rovdan KEYINGI qoldiqdan
        #    tug'iladi, ya'ni uni xeshga qo'shish bir xil tanali qayta
        #    yuborishni 409 ga aylantirardi (docstringdagi jadval).
        #
        # ⚠ Qolgan maydonlar SO'ROVDAN olinadi (`money.stall_id`,
        #   `payload.*`), qatordan EMAS: aks holda o'sha kalit bilan
        #   BOSHQA rastaga yuborilgan so'rov jimgina birinchi to'lovni
        #   tasdiqlardi — kassir noto'g'ri rastani to'langan deb ko'rardi.
        if replayed.request_fingerprint != payment_repo.request_fingerprint(
            stall_id=money.stall_id,
            service_date=as_of,
            amount_soum=payload.amount_soum,
            quote_soum=replayed.quote_soum,
            method=payload.method,
            override_reason=override_reason,
        ):
            log.info("payment_idempotency_key_reused", stall_code=payload.stall_code)
            raise _reject(IDEMPOTENCY_KEY_REUSED, status.HTTP_409_CONFLICT)
        response.status_code = status.HTTP_200_OK
        return PaymentResponse(
            payment_id=replayed.payment_id,
            stall_code=money.stall_code,
            service_date=replayed.service_date,
            amount_soum=replayed.amount_soum,
            kind=replayed.kind,  # type: ignore[arg-type]
            method=replayed.method,  # type: ignore[arg-type]
            created_at=replayed.created_at,
            # ⛔ 6-QADAMDAGI qaytish bilan AYNI: storno o'z marshrutidan
            #    o'tadi va o'sha holatda kassir ro'yxatni qayta oladi.
            reversed=False,
        )

    # ---- 3-QADAM: biriktirilmagan rasta — BITTA aniq javob (D-28).
    if money.vendor_id is None:
        log.info("payment_stall_not_assigned", stall_code=payload.stall_code, as_of=str(as_of))
        raise _reject(STALL_NOT_ASSIGNED, status.HTTP_409_CONFLICT)
    vendor_id = money.vendor_id

    # ---- 4-QADAM: asoslangan summalar — ⛔ SERVERDA, arifmetikasiz.
    outstanding = (
        await billing_repo.vendor_outstanding(
            session, market_id=market_id, vendor_ids=[vendor_id], as_of=as_of
        )
    ).get(vendor_id, 0)
    quotes = payment_quote_set(money.amount_soum, outstanding)
    if not quotes:
        # ⛔ YAGONA TO'LIQ RAD ETISH YO'LI. Sabab NOMLANGAN va u
        #    KO'RINADI: yopiq kun / tarif yo'qligi -> o'sha kod; texnik
        #    holat (tarif bor, qarz nol, summa nol) -> `amount_unavailable`.
        reason = money.unavailable_reason or AMOUNT_UNAVAILABLE
        log.info("payment_no_justified_amount", stall_code=payload.stall_code, reason=reason)
        raise _reject(reason, status.HTTP_422_UNPROCESSABLE_CONTENT)

    # ---- 5-QADAM: `quote_soum` tanlovi va sabab darvozasi (D-19).
    if payload.amount_soum in quotes:
        quote_soum = payload.amount_soum
        if payload.reason_code is not None:
            raise _reject(OVERRIDE_NOT_APPLICABLE, status.HTTP_422_UNPROCESSABLE_CONTENT)
    else:
        quote_soum = quotes[0]
        if payload.reason_code is None:
            raise _reject(REASON_REQUIRED, status.HTTP_422_UNPROCESSABLE_CONTENT)

    # ---- Smena ⛔ SERVERDA yechiladi (`PaymentCreateRequest` docstringi).
    shift_id = await payment_repo.open_shift_id(
        session, market_id=market_id, cashier_id=principal.user_id
    )

    # ---- 6-QADAM: idempotent yozish (A1 zondi — ikki bayonot).
    try:
        row, created = await payment_repo.create_payment(
            session,
            market_id=market_id,
            payload=payment_repo.PaymentWrite(
                idempotency_key=payload.idempotency_key,
                stall_id=money.stall_id,
                vendor_id=vendor_id,
                service_date=as_of,
                amount_soum=payload.amount_soum,
                quote_soum=quote_soum,
                method=payload.method,
                override_reason=override_reason,
                shift_id=shift_id,
                cashier_id=principal.user_id,
            ),
        )
    except payment_repo.IdempotencyConflict as exc:
        log.info("payment_idempotency_key_reused", stall_code=payload.stall_code)
        raise _reject(IDEMPOTENCY_KEY_REUSED, status.HTTP_409_CONFLICT) from exc

    # ---- 7-QADAM: CASH-02 auditi — ⛔ FAQAT CHETLANISHDA.
    if created and override_reason is not None:
        await write_app_audit(
            session,
            action=AuditAction.PAYMENT_OVERRIDE,
            table_name="payments",
            row_id=row.payment_id,
            principal=principal,
            new={
                "quote_soum": quote_soum,
                "amount_soum": payload.amount_soum,
                "reason_code": override_reason,
                "stall_code": money.stall_code,
                # ⛔ TAKLIF MAYDONINING O'ZI — `quote_soum` YOLG'IZ
                #    tanlangan variantni ko'rsatadi. Nizoda «server qanday
                #    summalarni taklif qilgan edi?» savoliga javob
                #    QATORDAN chiqishi kerak (D-02) va u boshqa hech
                #    qayerda saqlanmaydi.
                "quotes": list(quotes),
            },
        )

    # ⛔ TAKROR SO'ROV -> **200**, yangi -> **201** (D-21).
    if not created:
        response.status_code = status.HTTP_200_OK

    return PaymentResponse(
        payment_id=row.payment_id,
        stall_code=money.stall_code,
        service_date=row.service_date,
        amount_soum=row.amount_soum,
        kind=row.kind,  # type: ignore[arg-type]
        method=row.method,  # type: ignore[arg-type]
        created_at=row.created_at,
        # ⛔ YANGI YOZILGAN QATOR HECH QACHON STORNO QILINMAGAN. Takror
        #    so'rovda ham `False`: storno o'z marshrutidan o'tadi va o'sha
        #    holatda kassir ro'yxatni (`/payments/recent`) qayta oladi.
        reversed=False,
    )


@router.post(
    "/{payment_id}/reverse", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED
)
async def reverse_payment(
    payment_id: UUID,
    payload: PaymentReverseRequest,
    principal: PaymentWriterDep,
    session: TenantSessionDep,
) -> PaymentResponse:
    """To'lovni bekor qilish — ⛔ **YANGI QATOR**, tahrirlash EMAS (D-23).

    =======================================================================
    ⛔ UCH RAD ETISH — UCH BOSHQA JAVOB, va ular BIRLASHTIRILMAYDI:

        qator yo'q (yoki begona bozorniki)  -> **404**
        boshqa smenaning to'lovi            -> **403**
        allaqachon bekor qilingan / storno  -> **409**

    404 va 403 ni bitta 409 ga siqish kassirga noto'g'ri yo'l
    ko'rsatardi; 404 o'rniga 403 esa obyekt MAVJUDLIGINI tasdiqlab,
    begona bozorning `payment_id` larini javob kodi bo'yicha sanab
    chiqish yo'lini ochardi (T-01-76).
    =======================================================================

    ⛔ **KASSIR FAQAT O'Z OCHIQ SMENASIDAGI TO'LOVNI BEKOR QILADI**
       (§8.8) — `market_admin` uchun ham. Eski to'lovni bekor qilish
       yuzasi 6-fazada ⛔ **qurilmaydi** (egasi 7-faza, §16.1): u
       boshqa oqim (kim so'radi, kim tasdiqladi, qaysi smenaning
       variance i qayta hisoblanadi) va uni jimgina shu marshrutga
       qo'shish yopilgan smenaning deklaratsiyasini RETROAKTIV
       o'zgartirardi (D-25).

    ⚠ `reason_code` MAJBURIY va uning yo'qligi Pydantic darajasida
      **422** beradi — qo'lda tekshiruv yozilmaydi.
    """
    market_id = _market_id(principal)

    owner = await payment_repo.payment_owner(session, market_id=market_id, payment_id=payment_id)
    if owner is None:
        raise _reject(_NOT_FOUND, status.HTTP_404_NOT_FOUND)

    if owner.kind == PaymentKind.REVERSAL.value:
        # Storno qatorining O'ZINI bekor qilib bo'lmaydi (D-23).
        raise _reject(PAYMENT_ALREADY_REVERSED, status.HTTP_409_CONFLICT)

    shift_id = await payment_repo.open_shift_id(
        session, market_id=market_id, cashier_id=principal.user_id
    )
    if shift_id is None or owner.shift_id != shift_id:
        # ⛔ 403, 404 EMAS: qator MAVJUDLIGI allaqachon tasdiqlangan (u
        #    so'rovchining O'Z bozorida) — ya'ni bu yerda 404 hech qanday
        #    ma'lumot yashirmasdi, faqat kassirga noto'g'ri yo'l
        #    ko'rsatardi («bunday to'lov yo'q» -> u qayta izlardi).
        log.info("payment_reverse_foreign_shift", payment_id=str(payment_id))
        raise _reject(_FORBIDDEN, status.HTTP_403_FORBIDDEN)

    try:
        row = await payment_repo.reverse_payment(
            session,
            market_id=market_id,
            payment_id=payment_id,
            reason_code=payload.reason_code.value,
            cashier_id=principal.user_id,
            shift_id=shift_id,
        )
    except payment_repo.PaymentAlreadyReversed as exc:
        raise _reject(PAYMENT_ALREADY_REVERSED, status.HTTP_409_CONFLICT) from exc

    await write_app_audit(
        session,
        action=AuditAction.PAYMENT_REVERSE,
        table_name="payments",
        row_id=row.payment_id,
        principal=principal,
        new={
            "reverses_payment_id": str(payment_id),
            "reason_code": payload.reason_code.value,
            "amount_soum": row.amount_soum,
        },
    )

    return PaymentResponse(
        payment_id=row.payment_id,
        # ⚠ KOD `payment_owner()` DAN — ikkinchi so'rov yozilmaydi
        #   (`PaymentOwner` docstringi).
        stall_code=owner.stall_code,
        service_date=row.service_date,
        amount_soum=row.amount_soum,
        kind=row.kind,  # type: ignore[arg-type]
        method=row.method,  # type: ignore[arg-type]
        created_at=row.created_at,
        # ⛔ STORNO QATORINING O'ZI STORNO QILINMAGAN — va qilinmaydi ham
        #    (yuqoridagi `kind` darvozasi). `True` yozish uni ekranda
        #    «bekor qilingan bekor qilish» deb ko'rsatardi.
        reversed=False,
    )


@router.get("/recent", response_model=RecentPaymentsResponse)
async def recent_payments(
    principal: CollectViewerDep,
    session: TenantSessionDep,
) -> RecentPaymentsResponse:
    """Smenaning OXIRGI 5 to'lovi — ⛔ **PARAMETRSIZ** (§8.8, §10.3).

    =======================================================================
    ⛔⛔ `limit` / `offset` / `cursor` / `page` — BIRORTASI E'LON
        QILINMAGAN va bu himoyaning O'ZI.

    Kassir o'zi yozgan to'lovlarni ko'rishi KERAK (bekor qilish uchun).
    Lekin u smenasining **hamma** to'lovini ko'rsa, ularni **qo'shib**
    tizim summasini chiqarib olardi va smena yopilishidagi ⛔ **ko'r
    deklaratsiya** (D-25) arifmetika bilan buzilardi — variance har doim
    nol chiqardi va butun nazorat mexanizmi **jimgina** o'lardi.

    Oyna `payment_repo.RECENT_PAYMENT_WINDOW` konstantasida va
    `recent_payments()` imzosida ⛔ **`limit` argumenti yo'q**, ya'ni bu
    marshrut uni o'tkazib yubora **olmaydi** ham.
    =======================================================================

    ⛔ **OCHIQ SMENA BO'LMASA — BO'SH RO'YXAT, 404 EMAS.** Bo'sh ro'yxat
       «natija»: direktorda smena umuman bo'lmaydi (OQ-6/A5) va unga
       «topilmadi» deyish yolg'on bo'lardi.
    """
    market_id = _market_id(principal)

    shift_id = await payment_repo.open_shift_id(
        session, market_id=market_id, cashier_id=principal.user_id
    )
    if shift_id is None:
        return RecentPaymentsResponse(items=[])

    rows = await payment_repo.recent_payments(session, market_id=market_id, shift_id=shift_id)
    return RecentPaymentsResponse(
        items=[
            PaymentResponse(
                payment_id=row.payment_id,
                stall_code=row.stall_code,
                service_date=row.service_date,
                amount_soum=row.amount_soum,
                kind=row.kind,  # type: ignore[arg-type]
                method=row.method,  # type: ignore[arg-type]
                created_at=row.created_at,
                reversed=row.reversed,
            )
            for row in rows
        ]
    )
