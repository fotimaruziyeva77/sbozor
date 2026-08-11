"""Smena va ⛔⛔ KO'R NAQD DEKLARATSIYASI — CASH-04 ning HTTP yuzasi.

=============================================================================
⛔⛔ TO'RT MARSHRUT VA ULARNING IKKI YUZASI:

    POST /shifts                  -> 201, `ShiftOpenResponse`   (kassir)
    GET  /shifts/open             -> 200, `... | null`          (kassir)
    POST /shifts/{shift_id}/close -> 200, `ShiftCloseResponse`  (kassir)
    GET  /shifts?day=             -> 200, `ShiftReportResponse` (direktor)

Birinchi uchtasi `SHIFT_MANAGE` ostida (kassir + bozor admini),
to'rtinchisi `REPORT_VIEW` ostida (bozor admini + direktor, ⛔ kassirda
u YO'Q). Ular bitta faylda yashaydi, chunki bitta DOMEN; huquq esa IMZO
ALIASI bilan marshrut darajasida ajratilgan (`billing.py` naqshi).

=============================================================================
⛔⛔ D-25 NING SERVERDAGI YARMI — MAYDONNI E'LON QILMASLIK.

`POST /shifts/{shift_id}/close` javobi kalitlari to'plami ⛔ **AYNAN**
`{id, status, declared_soum, closed_at}` (UI-SPEC §10.3). Tizim summasi
`shift_repo.close_shift()` ichida ⛔ **hisoblanadi va bazaga yoziladi**,
lekin `ShiftCloseResponse` uni ⛔ **UMUMAN e'lon qilmaydi**.

⛔ REPOSITORY QATORINI (`ShiftRow`) TO'G'RIDAN-TO'G'RI `response_model`
   QILIB QO'YISH — AYNAN SHU HIMOYANI BUZADIGAN BIR SATRLIK O'ZGARISH.
   Sabab `shift_repo.ShiftRow` docstringida ham yozilgan; bu yerdagi
   handler qiymatlarni MAYDONMA-MAYDON ko'chiradi.

=============================================================================
⛔⛔ VARIANCE FAQAT `GET /shifts?day=` DA (UI-SPEC §10.4).

`system = declared − variance` — ⛔ **bitta ayirish**, ya'ni variance ni
kassirga qaytarish `system_soum` ni qaytarish bilan MATEMATIK JIHATDAN
BIR XIL. Shuning uchun u FAQAT `report_view` ostidagi hisobot
marshrutida, va o'sha huquq kassirda ⛔ **yo'q** (`rbac.py`, D-07).

⚠ 06-RESEARCH SC#5(d) ning «`declared > system` holatida ham
  qaytariladi» talabi AYNAN o'sha marshrutda bajariladi va o'lchanadi —
  `close` javobida yo'q maydonni izlagan test YOLG'ON-QIZIL bo'lardi.

=============================================================================
⛔ AUDIT BU FAYLDA YOZILMAYDI VA BU `payments.py` DAN FARQ QILADI.

`cashier_shifts` ⛔ **`AUDITED_TABLES` da**, ya'ni `fn_audit_row()`
DB-trigger'i smena ochilishi va yopilishini ⛔ **O'ZI** yozadi (aktor
`app.actor_id` GUC'idan). Ilova darajasidagi `write_app_audit()`
chaqiruvi ⛔ **IKKINCHI (dublikat)** jurnal qatorini qo'shardi va nizoda
«ikki marta yopilganmi?» degan yolg'on savol tug'ilardi.

⚠ `payments` esa `AUDITED_TABLES` da YO'Q (append-only, hajm katta) —
  aynan shuning uchun `payments.py` da `write_app_audit()` BOR va bu
  yerda YO'Q. Farq jadval xossasida, e'tiborsizlikda emas.

=============================================================================
⛔ HUQUQ IMZO ALIASIDA, DEKORATORDA EMAS — VA `require_any_permission()`
   ISHLATILMAYDI (C-9).

`tests/tenancy/test_personal_data_coverage.py:691-706` o'sha darvozani
ko'targan marshrutlar to'plamini AYNAN
`("/api/v1/snapshots/{snapshot_id}/image",)` ga TENG bo'lishini talab
qiladi — to'plam YOPIQ va bu fayl unga tegmaydi.

=============================================================================
⛔ `cashier_id` HAR DOIM SO'ROVCHINING O'ZI (`principal.user_id`),
   MIJOZDAN OLINMAYDI. Boshqa kassir nomidan smena ochish ham, uni
   yopish ham yo'li YO'Q: birinchisi mijoz maydonining YO'QLIGI bilan,
   ikkinchisi `ShiftNotOwned` -> **403** bilan (T-06-62).
=============================================================================
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sbozor_core.timeutil import business_today

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories import shift_repo
from app.schemas import (
    ShiftCloseRequest,
    ShiftCloseResponse,
    ShiftOpenResponse,
    ShiftReportResponse,
    ShiftReportRow,
)
from app.security.rbac import Permission
from app.services.billing_errors import SHIFT_ALREADY_CLOSED, SHIFT_ALREADY_OPEN

# ⚠ `date` VA `UUID` ISH VAQTIDA IMPORT QILINADI, `TYPE_CHECKING` OSTIDA
#   EMAS — VA BU O'LCHANGAN ZARURIYAT (`billing.py:80-86`, `payments.py`,
#   `occupancy.py:70-75`). `from __future__ import annotations` ostida
#   annotatsiyalar SATR bo'lib qoladi va FastAPI ularni Pydantic uchun
#   YECHA olmaydi: `PydanticUserError: ... is not fully defined`.
#   Nosozlik marshrutda emas, OpenAPI sxemasini quruvchi meta-testda
#   ko'rinadi.

log = structlog.get_logger(__name__)

__all__ = ["router"]

router = APIRouter(tags=["shifts"])

ShiftManagerDep = Annotated[Principal, Depends(require_permission(Permission.SHIFT_MANAGE))]
"""⛔ `SHIFT_MANAGE` — kassir VA bozor adminida (UI-SPEC §5.6, D-07).

Kichik bozorda bozor admini kassirni ⛔ **ALMASHTIRADI**: kassir kasal
bo'lgan kuni smenani ochadigan va yopadigan odam bo'lmasa kun umuman
yopilmasdi va o'sha kunning variance i ⛔ **hech qachon** hisoblanmasdi.

⛔ **DIREKTORGA BERILMAGAN** va bu tanlov: u variance ni `REPORT_VIEW`
   ostidagi kun hisobotida KO'RADI, smenani o'zi ochmaydi ham, yopmaydi
   ham. D-26 bo'yicha variance HECH QACHON «to'g'rilanmaydi», ya'ni
   direktorga smena ustida YOZUV yuzasi umuman kerak emas.

⚠ SHUNING UCHUN BU UCH MARSHRUT cross-tenant matritsasida ⛔ **ODATDAGI**
  (bozor admini) sessiyasidan yuradi va `CASHIER_ROUTES` ga
  ⛔ **TUSHMAYDI** — `payment_create` dan farqli o'laroq (u YOLG'IZ
  kassirda). Ularni o'sha ro'yxatga qo'shish marshrutni kuchsizroq
  sessiyaga olib chiqib ketardi, ya'ni matritsani ZAIFLASHTIRARDI.
"""

ReportViewerDep = Annotated[Principal, Depends(require_permission(Permission.REPORT_VIEW))]
"""⛔ `SHIFT_MANAGE` EMAS — VA BU FARQ D-25 NING O'ZI.

Variance FAQAT shu darvoza ortida. Kassirda `report_view` ⛔ **YO'Q**
(`rbac.py::Role.CASHIER` — aynan uch huquq), ya'ni u `GET /shifts` ni
chaqirsa **403** oladi va tizim summasini ⛔ **ayirish bilan** chiqarib
ololmaydi. Bu marshrutni `SHIFT_MANAGE` ostiga qo'yish D-25 ni
⛔ **bitta so'rov** bilan bekor qilardi.
"""


_NOT_FOUND = "not_found"
"""Cross-tenant va mavjud bo'lmagan smena uchun BIR XIL javob (T-01-76).

⚠ `SERVER_BILLING_ERROR_CODES` REYESTRIGA QO'SHILMAYDI — `billing.py:115`
  va `payments.py:139` bilan aynan bir xil qaror: reyestr DOMEN kodlari
  uchun («bu amalni nega bajarib bo'lmadi»), bu esa STRUKTURAVIY javob
  va u hech qanday yo'l ko'rsatmaydi.
"""

_FORBIDDEN = "forbidden"
"""Boshqa kassirning smenasini yopishga urinish (**403**).

⛔ REYESTRGA QO'SHILMAYDI VA BU ONGLI: `ALL_BILLING_ERROR_CODES` ning
   soni `frontend/scripts/error-codes.test.mjs` tomonidan uchala
   locale'dagi `errorCause`/`errorFix` juftligi bilan SOLISHTIRILADI,
   ya'ni matnsiz yangi kod o'sha darvozani DARHOL qizartirardi
   (`payments.py::_FORBIDDEN` bilan aynan bir xil holat).

⚠ Bu holat KLIENT YO'LIDA yuz bermaydi: `GET /shifts/open` faqat
  so'rovchining O'Z smenasini qaytaradi, ya'ni 06-12 ning [Smenani
  yopish] tugmasi begona `shift_id` ni umuman ko'rsatmaydi.
"""

_DAY_IN_FUTURE = "day_in_future"
"""Kelajak kuni uchun hisobot so'raldi (**422**).

⚠ REYESTRGA QO'SHILMAYDI — `billing.py:124-134` dagi bilan AYNAN bir xil
  sabab va u yerda to'liq yozilgan. Klientda bu holat yuz bermaydi: kun
  tanlagichning maksimumi BUGUN (§11.1).
"""


_MARKET_NOT_SELECTED = "market_not_selected"
"""Sessiyada bozor tanlanmagan (**403**).

⛔ REYESTRGA QO'SHILMAYDI (`_DAY_IN_FUTURE` bilan aynan bir xil sabab).
   Kod `api-types.ts` ning O'Z ro'yxatida ALLAQACHON bor (u 01-fazadan).
"""


def _market_id(principal: Principal) -> UUID:
    """Sessiyadagi bozor — `payments.py` dagi jufti bilan bir xil shakl.

    ⛔ `detail` — **SATR** (`_reject()` orqali). Lug'at shakli 01-fazadan
       meros edi; uning klientda ko'rinmasligi `/pending` ning 404 ida
       O'LCHANGAN (CR-04).
    """
    market_id = principal.market_id
    if market_id is None:
        raise _reject(_MARKET_NOT_SELECTED, status.HTTP_403_FORBIDDEN)
    return market_id


def _reject(code: str, http_status: int) -> HTTPException:
    """`detail` ⛔ **SATR**, lug'at EMAS — va bu klient kontrakti.

    `frontend/src/lib/api-client.ts::detailOf()` `detail` ni AYNAN satr
    deb o'qiydi; lug'at yuborilganda u bo'sh satr qaytaradi va
    `billing-errors.ts` kodni tanimay `errors.generic` matnini chizadi —
    ya'ni kassir «bu smena allaqachon yopilgan» o'rniga umumiy xato
    ko'rardi va nosozlik FAQAT dala sinovida ko'rinardi
    (`payments.py::_reject()` docstringi).
    """
    return HTTPException(status_code=http_status, detail=code)


def _report_day(day: date | None) -> date:
    """Hisobot kunini yechadi — ⛔ STANDARTI **BUGUN** (kecha EMAS).

    =======================================================================
    ⛔⛔ NEGA `billing.py::_report_day()` DAN FARQ QILADI.

    O'sha funksiyaning standarti ⛔ **KECHA** va sabab C-3: hisob **D+1
    04:10** da tug'iladi, ya'ni bugungi kun uchun hisob hali YO'Q va
    sahifa har doim bo'sh ochilardi.

    Smena esa ⛔ **BUGUN** yopiladi. Direktor variance ni ⛔ **shu kuni**
    ko'radi — naqd topshirilayotgan payt aynan o'sha kun kechqurun va
    D-02 ning nizo modeli ikki tomon ⛔ **birga turganda** ishlaydi.
    Standarti kecha bo'lsa, bugun yopilgan smena hisobotda
    ⛔ **ko'rinmasdi** va direktor uni qidirib topa olmasdi.

    ⚠ ZIDDIYAT YO'Q: UI-SPEC §11.2 jadvali `E` blokini (smena variance)
      ⛔ **IKKALA kunda ham** ko'rsatadi (`day = bugun` va `day <
      bugun`), `C`/`D` bloklarini esa faqat o'tmish kunida. Ya'ni
      sahifaning standart kuni (kecha) va bu marshrutning standart kuni
      (bugun) BOSHQA savollarga javob beradi; klient kunni HAR DOIM
      OCHIQ yuboradi (`?day=`), standart esa marshrutni yolg'iz
      chaqirganda ma'noli bo'lib qoladi.
    =======================================================================

    ⛔ KELAJAK KUNI **422**: kelajakda yopilgan smena MAVJUD EMAS
       (`business_date` `created_at` dan hosila), ya'ni so'rov bazagacha
       borib BO'SH ro'yxat qaytarardi — «kelajakda smena yo'q» degan
       ma'nosiz javob «bu kunda smena yopilmagan» bilan bir xil
       ko'rinardi.
    """
    today = business_today()
    resolved = today if day is None else day
    if resolved > today:
        # ⚠ `HTTP_422_UNPROCESSABLE_CONTENT` — RFC 9110 dagi joriy nom
        #   (`audit.py:184-187` da o'rnatilgan qoida).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_DAY_IN_FUTURE
        )
    return resolved


@router.post("", response_model=ShiftOpenResponse, status_code=status.HTTP_201_CREATED)
async def open_shift(
    principal: ShiftManagerDep,
    session: TenantSessionDep,
) -> ShiftOpenResponse:
    """Smenani ochadi — ⛔ TANASIZ so'rov (UI-SPEC §10.1).

    ⛔ **SO'ROV TANASI YO'Q VA `cashier_id` MIJOZDAN OLINMAYDI.** Smena
       HAR DOIM so'rovchining O'ZIGA ochiladi (`principal.user_id`) —
       boshqa kassir nomidan ochish yo'li ⛔ **umuman yo'q**. Uni
       maydon sifatida qabul qilish o'sha kassirning ko'r
       deklaratsiyasini begona pul bilan ifloslantirish yo'lini
       ochardi (T-06-62, `payments.py` dagi `shift_id` bilan aynan bir
       xil sinf).

    ⛔ **«OCHIQ SMENA BORMI?» TEKSHIRILMAYDI** (D-27) — sabab
       `shift_repo.open_shift()` docstringida: poyga qisman `UNIQUE`
       indeksga topshiriladi va ilova qatlamidagi oldindan tekshiruv
       «tekshir-keyin-yoz» poygasini tug'dirardi.

    ⛔ **AUDIT SHU YERDA YOZILMAYDI** — `cashier_shifts` `AUDITED_TABLES`
       da va DB-trigger qatorni O'ZI yozadi (modul docstringi).
    """
    market_id = _market_id(principal)

    try:
        row = await shift_repo.open_shift(
            session, market_id=market_id, cashier_id=principal.user_id
        )
    except shift_repo.ShiftAlreadyOpen as exc:
        log.info("shift_already_open", cashier_id=str(principal.user_id))
        raise _reject(SHIFT_ALREADY_OPEN, status.HTTP_409_CONFLICT) from exc

    return ShiftOpenResponse(
        id=row.shift_id,
        status=row.status,  # type: ignore[arg-type]
        opened_at=row.opened_at,
    )


@router.get("/open", response_model=ShiftOpenResponse | None)
async def open_shift_state(
    principal: ShiftManagerDep,
    session: TenantSessionDep,
) -> ShiftOpenResponse | None:
    """So'rovchining OCHIQ smenasi — ⛔ yo'q bo'lsa **`null`**, 404 EMAS.

    ⛔ **404 QAYTARILMAYDI VA BU KONTRAKT** (§10.1): ekranning IKKI
       holati bor — `EmptyState` + `[Smenani ochish]`, yoki smena
       kartasi. Uchinchisi yo'q. 404 klientni «server nosoz» shoxiga
       yuborardi va kassir kun boshida smenani UMUMAN ocha olmasdi;
       `useOpenShift()` esa `retry: false` bilan yozilgan (06-03), ya'ni
       xato holat ekranda QOLIB KETARDI.

    ⛔ **KARTADA YIG'INDI YO'Q** — sabab `ShiftOpenResponse` docstringida
       (to'lovlar soni, yig'ilgan summa, o'rtacha: har biri yig'indiga
       olib boradi va §10.3 ning ko'rligini arifmetika bilan buzardi).
    """
    market_id = _market_id(principal)

    row = await shift_repo.open_shift_for(
        session, market_id=market_id, cashier_id=principal.user_id
    )
    if row is None:
        return None

    return ShiftOpenResponse(
        id=row.shift_id,
        status=row.status,  # type: ignore[arg-type]
        opened_at=row.opened_at,
    )


@router.post("/{shift_id}/close", response_model=ShiftCloseResponse)
async def close_shift(
    shift_id: UUID,
    payload: ShiftCloseRequest,
    principal: ShiftManagerDep,
    session: TenantSessionDep,
) -> ShiftCloseResponse:
    """Ko'r naqd deklaratsiyasi — ⛔⛔ JAVOBDA TIZIM SUMMASI YO'Q (D-25).

    =======================================================================
    ⛔⛔ JAVOB KALITLARI TO'PLAMI AYNAN TO'RTTA:

        {id, status, declared_soum, closed_at}

    `system_soum` shu handler chaqirgan `shift_repo.close_shift()` ichida
    ⛔ **hisoblanadi va bazaga yoziladi**, lekin `ShiftCloseResponse`
    uni ⛔ **UMUMAN e'lon qilmaydi** — sabab o'sha modelning
    docstringida (Pitfall 6: brauzerga yetgan maydon O'QILADI; `null`
    esa maydonning BORLIGINI tasdiqlaydi).

    ⛔ **`ShiftRow` NI `response_model` QILIB QO'YISH — AYNAN SHU
       HIMOYANI BUZADIGAN BIR SATRLIK O'ZGARISH.** Qiymatlar bu yerda
       MAYDONMA-MAYDON ko'chiriladi va `system_soum` ⛔ **ko'chirilmaydi**.
    =======================================================================

    ⛔ **UCH RAD ETISH — UCH BOSHQA JAVOB, va ular BIRLASHTIRILMAYDI:**

        qator yo'q (yoki begona BOZORNIKI)  -> **404** (T-01-76)
        boshqa KASSIRNING smenasi           -> **403**
        allaqachon yopilgan                 -> **409**

    404 o'rniga 403 begona bozorning `shift_id` larini javob kodi
    bo'yicha sanab chiqish yo'lini ochardi; 403 o'rniga 404 esa o'z
    bozoridagi kassirga «bunday smena yo'q» deb YOLG'ON aytardi.

    ⛔ **IKKINCHI `close` -> 409 VA QATOR TEGILMAYDI** (D-25): ilova
       shoxi `UPDATE` gacha yetib bormaydi, `UPDATE` ning o'zi esa
       `AND status = 'open'` sharti bilan yuradi va sxemada
       `shift_declaration_immutable()` uchinchi qatlam sifatida turadi.

    ⛔ **`declared_soum = 0` O'TADI** (§10.2): butun smena terminal
       bo'lgan kun REAL holat. Chegara `ShiftCloseRequest` da (`ge=0`).

    ⛔ **AUDIT SHU YERDA YOZILMAYDI** — DB-trigger qatorni O'ZI yozadi
       (modul docstringi). `write_app_audit()` ikkinchi, DUBLIKAT yozuv
       qo'shardi.
    """
    market_id = _market_id(principal)

    try:
        row = await shift_repo.close_shift(
            session,
            market_id=market_id,
            shift_id=shift_id,
            cashier_id=principal.user_id,
            declared_soum=payload.declared_soum,
        )
    except shift_repo.ShiftNotFound as exc:
        raise _reject(_NOT_FOUND, status.HTTP_404_NOT_FOUND) from exc
    except shift_repo.ShiftNotOwned as exc:
        log.info("shift_close_foreign_cashier", shift_id=str(shift_id))
        raise _reject(_FORBIDDEN, status.HTTP_403_FORBIDDEN) from exc
    except shift_repo.ShiftAlreadyClosed as exc:
        raise _reject(SHIFT_ALREADY_CLOSED, status.HTTP_409_CONFLICT) from exc

    # ⛔ `closed_at` `None` BO'LA OLMAYDI: `_CLOSE_SHIFT` uni `now()` bilan
    #    to'ldiradi va `ck_cashier_shifts_closed_is_paired` juftlikni
    #    MAJBURLAYDI. Tekshiruv NAZORAT sifatida yoziladi — `None` bo'lsa
    #    bu sxema drifti va u JIMGINA `null` bo'lib ketmasligi kerak.
    if row.closed_at is None or row.declared_soum is None:  # pragma: no cover - sxema kafolati
        raise RuntimeError(
            f"shift_id={shift_id} yopildi, lekin `closed_at`/`declared_soum` bo'sh — "
            "sxema kafolati (`closed_is_paired` / `closed_has_declaration`) buzilgan"
        )

    return ShiftCloseResponse(
        id=row.shift_id,
        status=row.status,  # type: ignore[arg-type]
        declared_soum=row.declared_soum,
        closed_at=row.closed_at,
        # ⛔ `system_soum` BU YERGA KO'CHIRILMAYDI VA MODELDA UNGA MAYDON
        #    YO'Q — `row.system_soum` mavjud, lekin u D-25 ning aynan
        #    to'sayotgan qiymati (§10.3, §10.4).
    )


@router.get("", response_model=ShiftReportResponse)
async def shift_report(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    day: Annotated[date | None, Query()] = None,
) -> ShiftReportResponse:
    """Kun kesimidagi smenalar va ⛔ IKKI TOMONLAMA variance (§11.5, D-26).

    =======================================================================
    ⛔⛔ BU — VARIANCE QAYTARILADIGAN YAGONA MARSHRUT (UI-SPEC §10.4).

    Kassir uni ko'rmaydi: `report_view` unda ⛔ **yo'q**. Direktor esa
    ⛔ **ikki tomonlama** ko'radi — kamomad ham, ortiqcha ham, ishorasi
    bilan. «Ortiqcha naqdni jimgina yutish kamomadni yashirish bilan
    BIR XIL xato» (D-26).
    =======================================================================

    ⛔ **YOZUV YUZASI AYNAN NOL** (§11.5): variance ni to'g'rilash,
       tasdiqlash, izohlash yoki kechirish uchun ⛔ **birorta marshrut
       yo'q** va bu fazada ochilmaydi. D-26: variance HECH QACHON
       avtomatik to'g'rilanmaydi, qo'lda to'g'rilash yo'li ham
       QURILMAYDI.

    ⛔ **VARIANCE CHEGARASI VA OGOHLANTIRISHI YO'Q** (OQ-7/A6): chegara
       kelishilmagan va u bozor bo'yicha SOZLANADIGAN bo'lishi kerak —
       kodga qo'yilgan literal son barcha bozorlarga tarqalardi. Egasi
       8-faza (§17 O-06).

    ⛔ **STANDART KUN — BUGUN** (`_report_day()` docstringidagi to'rt
       band; `billing.py` dagi KECHA dan ATAYIN farq qiladi).

    ⛔ **SMENASIZ TO'LOVLAR ALOHIDA SANOQ BILAN** (§11.5 FLAG, OQ-6/A5):
       ular variance ga KIRMAYDI, lekin ⛔ **ko'rinadi** — aks holda
       jimgina yo'qolardi.

    ⚠ `cashier_id` QAYTADI, ISM EMAS (C-10 + §5.5): kassir nomi MAVJUD
      `GET /users` dan klientda joinlanadi. Bu bitta qo'shimcha
      so'rovning ONGLI narxi.
    """
    market_id = _market_id(principal)
    business_date = _report_day(day)

    report = await shift_repo.shift_report(session, market_id=market_id, day=business_date)

    return ShiftReportResponse(
        day=business_date,
        rows=[
            ShiftReportRow(
                id=row.shift_id,
                cashier_id=row.cashier_id,
                opened_at=row.opened_at,
                closed_at=row.closed_at,
                declared_soum=row.declared_soum,
                system_soum=row.system_soum,
                variance_soum=row.variance_soum,
            )
            for row in report.rows
        ],
        # ⛔ NOL BO'LGANDA HAM QAYTADI — «smenasiz to'lov yo'q» bilan
        #    «hisoblagich ishlamayapti» bir xil ko'rinmasligi kerak.
        shiftless_payment_count=report.shiftless_payment_count,
        shiftless_payment_soum=report.shiftless_payment_soum,
    )
