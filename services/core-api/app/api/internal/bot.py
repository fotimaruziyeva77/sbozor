"""`bot-service` -> `core-api` ichki yuzasi — TOR, TOKENLI, SESSIYASIZ (D-01/D-10).

=============================================================================
⛔⛔ FAZANING ISHONCH CHEGARASI SHU FAYLDA OCHILADI (D-01).

1–6-fazalarda tizimdan ma'lumot oladigan HAR BIR foydalanuvchi
autentifikatsiya qilingan XODIM edi. Bu yerda birinchi marta SOTUVCHI —
xodim emas — o'z qarzini ko'radi.

=============================================================================
⛔⛔ BOT FOYDALANUVCHI SESSIYASINI TUG'DIRMAYDI — TAQIQ, EHTIYOTKORLIK EMAS
   (D-10, T-07-39).

Bu faylda:

  * `Principal` YARATILMAYDI;
  * JWT (access yoki refresh) CHIQARILMAYDI;
  * `Set-Cookie` QO'YILMAYDI;
  * RBAC dependency'si (`require_permission`) ISHLATILMAYDI.

Sabab: bot «bu Telegram ID — mana shu vendor» deb aytadi, qolganini
core-api RLS ostida hal qiladi. Sessiya tug'dirilsa bot IKKINCHI
autentifikatsiya tizimiga aylanardi — o'z muddati, o'z bekor qilish
yo'li va o'z huquq modeli bilan. O'sha ikkinchi tizim birinchisidan
jimgina ajralib ketardi va «kim nimani ko'ra oladi?» savoli ikki xil
javob bergan bo'lardi.

Darvoza `tests/integration/test_bot_internal_api.py` da: javob
sarlavhalarida `Set-Cookie` YO'Q va bu fayl manbasida token chiqaruvchi
nomlar UMUMAN uchramaydi.

=============================================================================
⛔ MARSHRUTLAR SXEMASIZ VA TASHQARIDAN ERISHIB BO'LMAYDI.

`include_in_schema=False` (router darajasida) — `live_authz.py` /
`self_check.py` bilan bir xil qaror: OpenAPI MIJOZLAR uchun yoziladi,
bu yerda esa brauzer mijozi YO'Q. Yuza bot-service uchun va uning
kontrakti shu faylning O'ZI.

nginx (`ops/nginx/nginx.conf`) tashqariga AYNAN IKKI `location` ni proxy
qiladi (`/api/` va `/`), core-api porti esa xostga publish qilinmaydi —
ya'ni `/internal/*` compose tarmog'idan tashqarida MAVJUD EMAS. Bu
tekshiruv MEXANIK: `tests/tenancy/test_route_coverage.py` uchala yo'lning
sxemadan chiqarilganini va ular ommaviy `/api/v1` yuzasiga tushmaganini
qulflaydi.

=============================================================================
⛔ RAD ETISH SABABI JAVOB TANASIDA AYTILMAYDI (V6, T-07-38).

Token noto'g'ri va token UMUMAN yo'q — IKKALASI HAM `401` va AYNI matn.
Ajratish hujumchiga «sarlavha shakli to'g'ri edi» degan foydali signal
berardi. Solishtiruv `hmac.compare_digest` bilan: `==` birinchi farqli
baytda to'xtaydi va javob vaqti tokenning necha bayti to'g'ri
topilganini oshkor qilardi.

⛔ SOZLANMAGAN TOKEN -> `503`, «hammaga ochiq» EMAS (fail-closed).
   Bo'sh sirni «tekshiruvsiz o'tkazish» deb o'qish avtorizatsiyani BIR
   QATOR bilan yo'q qilardi.
=============================================================================
"""

from __future__ import annotations

import hmac
from datetime import date
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sbozor_core.timeutil import business_today

from app.repositories import billing_repo, binding_repo
from app.repositories.binding_repo import ResolveStatus
from app.security.ratelimit import TooManyAttempts, check_bot_resolve_rate

# ⚠ `date` VA `UUID` ISH VAQTIDA IMPORT QILINADI (`TYPE_CHECKING` ostida
#   EMAS): pydantic javob modellarini QURISH paytida annotatsiyalarni
#   HAQIQATAN hal qiladi va `from __future__ import annotations` ostida
#   ular satr bo'lib qoladi. Tipni faqat tekshiruvchi uchun import qilish
#   `PydanticUserError: ... is not fully defined` beradi — va u ISH
#   VAQTIDA, birinchi so'rovda chiqadi, `mypy` da emas.
if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.settings import Settings

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/internal/bot", include_in_schema=False)

_UNAUTHORIZED = "unauthorized"
"""⛔ YAGONA RAD ETISH MATNI — «token yo'q» va «token noto'g'ri» uchun BIR XIL."""

_UNAVAILABLE = "unavailable"
"""Token sozlanmagan (`503`). Bu HOLAT, sabab EMAS: qaysi sozlama
yetishmayotgani javobda aytilmaydi."""

_NOT_BOUND = "not_bound"
"""Telegram akkaunti hech qaysi sotuvchiga bog'lanmagan (`404`)."""

_TOO_MANY_ATTEMPTS = "too_many_attempts"


# ===========================================================================
# AUTENTIFIKATSIYA — SERVIS TOKENI, SESSIYA EMAS
# ===========================================================================


def _presented_token(request: Request) -> str:
    """`Authorization: Bearer <token>` dan xom qiymat.

    ⚠ SARLAVHA YO'Q BO'LSA BO'SH SATR QAYTADI, ISTISNO EMAS: bo'sh satr
      ham `compare_digest` ga BORADI, ya'ni «sarlavha yo'q» va «token
      noto'g'ri» yo'llari BIR XIL kodni bajaradi. Erta `return` qo'yilsa
      ikki yo'lning vaqti farq qilardi va tekshiruvning doimiy-vaqtliligi
      shu yerda yo'qolardi.
    """
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" else ""


async def _require_service_token(request: Request) -> None:
    """⛔ YUZANING YAGONA DARVOZASI — `Principal` TUG'DIRMAYDI (fayl docstringi).

    Bu funksiya HECH NIMA QAYTARMAYDI va bu ataylab: qaytarilgan obyekt
    (masalan `BotPrincipal`) marshrutlarga «kim so'rayapti?» degan
    tushunchani olib kirardi va u sekin-asta ikkinchi sessiya modeliga
    aylanardi. Bu yerda javob bitta: SERVIS so'rayapti.

    Raises:
        HTTPException: `503` — token sozlanmagan; `401` — mos kelmadi.
    """
    settings: Settings = request.app.state.settings
    expected = settings.bot_service_token.get_secret_value()
    if not expected:
        # ⛔ FAIL-CLOSED. Jurnalda sabab bor, javobda YO'Q.
        log.warning("bot_internal_token_not_configured", path=request.url.path)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_UNAVAILABLE)

    if not hmac.compare_digest(_presented_token(request).encode(), expected.encode()):
        # ⛔ TOKEN JURNALGA HAM YOZILMAYDI — na to'g'risi, na kelgani.
        log.warning("bot_internal_token_rejected", path=request.url.path)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED)


ServiceToken = Annotated[None, Depends(_require_service_token)]


# ===========================================================================
# JAVOB MODELLARI — ⛔ SHU FAYLDA, `app/schemas.py` DA EMAS
# ===========================================================================
#
# `app/schemas.py` — OMMAVIY API ning sxemasi va u OpenAPI'ga chiqadi.
# Bu yerdagi modellar esa bitta ichki iste'molchi (bot-service) uchun va
# ular sxemasiz yuzaning qismi. Ularni umumiy faylga qo'shish ommaviy
# kontraktni ichki ehtiyoj bilan kengaytirardi.


class ResolveRequest(BaseModel):
    """Bog'lanish so'rovi — Telegram akkaunti va u yuborgan raqam."""

    telegram_user_id: int = Field(gt=0)
    phone: str = Field(min_length=1, max_length=32)
    """⚠ FORMAT BU YERDA TEKSHIRILMAYDI: normalizatsiya CHEGARADA va AYNAN
    BIR JOYDA (`binding_repo._normalize`, D-25). Ikkinchi regeks yozish
    formatni ikki marta ta'riflardi va ular ajralib ketardi."""


class VendorRefOut(BaseModel):
    """⛔ FAQAT IDENTIFIKATORLAR — ism, telefon va bozor NOMI yo'q (D-05)."""

    market_id: UUID
    vendor_id: UUID


class ResolveResponse(BaseModel):
    """⛔ `no_match` va `multiple_matches` AYNI SHAKLDA qaytadi.

    Ikkala holatda ham `vendor` `None` va qo'shimcha maydon YO'Q — bot
    ikkalasida ham BIR XIL matn ko'rsatadi. Shox faqat serverda
    yoziladi: `multiple_matches` `alert_events` ga qator qo'yadi
    (T-07-44a), sotuvchi esa reyestr nuqsonini bilishi SHART EMAS va
    bilishi ham kerak emas.
    """

    status: ResolveStatus
    vendor: VendorRefOut | None = None


class VendorSummaryOut(BaseModel):
    """Bitta bozordagi qoldiq — ⛔ HOSILA SON (D-06).

    ⛔ MAYDON NOMI `outstanding_soum` VA U «SAQLANGAN QOLDIQ» MA'NOSINI
       BERADIGAN NOMDAN ATAYIN FARQ QILADI: bunday ustun loyihada MAVJUD
       EMAS va uni nom darajasida ham tiklamaslik kerak. Son har
       chaqiruvda `billing_repo` ning hisoblanadigan ko'rinishidan keladi.

    ⚠ TAQIQLANGAN NOM BU FAYLDA LITERAL YOZILMAYDI — 03-07 / 07-02 darsi:
      sodda grep darvozasi IZOHNI KODDAN AJRATMAYDI va uni tushuntirish
      uchun yozish darvozani O'Z sababi bilan qizartirardi. Da'voning
      o'zi `tests/tenancy/test_billing_domain_meta.py` va `07-04` ning
      AST darvozasida o'lchanadi.
    """

    market_id: UUID
    vendor_id: UUID
    outstanding_soum: int
    as_of: date
    stall_codes: list[str]


class VendorSummaryResponse(BaseModel):
    """⚠ RO'YXAT, BITTA OBYEKT EMAS — birinchisi JIMGINA tanlanmaydi.

    Bir sotuvchi ikki bozorda savdo qilishi mumkin va ikkalasida ham o'z
    qarzini ko'rishi kerak (`BINDING_TELEGRAM_ACTIVE_INDEX` docstringi).
    Serverda birinchisini tanlash sotuvchiga qarzining BIR QISMINI
    ko'rsatib, «hammasi to'langan» degan xulosaga olib kelardi.
    """

    markets: list[VendorSummaryOut]


class ChargeRowOut(BaseModel):
    """Bir kunlik hisob va unga tushgan kredit — `ChargeAllocationRow` ning ko'zgusi."""

    service_date: date
    stall_code: str
    due_soum: int
    paid_soum: int
    settled: bool


class VendorPaymentsResponse(BaseModel):
    """⛔ TAQSIMLASH QOIDASI NATIJA BILAN BIRGA QAYTADI (`rule`).

    Hisobot yoki nizo hujjati «qaysi qoida bo'yicha?» degan savolga
    javobni YONIDA topadi (`ChargeCreditAllocation` docstringi).
    """

    market_id: UUID
    vendor_id: UUID
    rule: str
    rows: list[ChargeRowOut]
    next_cursor: str | None = None


# ===========================================================================
# YORDAMCHILAR
# ===========================================================================


def _row_cursor(row: ChargeRowOut) -> str:
    """Keyset kaliti — `(service_date, stall_code)`, taqsimlash TARTIBI bilan bir xil.

    ⛔ TARTIB SHU YERDA QAYTA E'LON QILINMAYDI: u `sbozor_core.billing.
       allocate_charge_credit()` ning `sorted()` ida yashaydi va qatorlar
       shu tartibda keladi. Ikkinchi `sorted()` yozish qoidani IKKI JOYGA
       bo'lardi.
    """
    return f"{row.service_date.isoformat()}|{row.stall_code}"


async def _single_binding(
    request: Request, *, telegram_user_id: int, market_id: UUID
) -> binding_repo.BindingRef:
    """Berilgan bozordagi FAOL bog'lanish; topilmasa `404`.

    ⛔ `404`, `403` EMAS — `main.py::rls_violation_handler` bilan bir xil
       qaror: «bunday bog'lanish yo'q» va «bor, lekin sizniki emas»
       farqini javobda ochish bog'lanishlarni sanash yo'lini berardi.
    """
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    for binding in await binding_repo.active_bindings(
        sessionmaker, telegram_user_id=telegram_user_id
    ):
        if binding.market_id == market_id:
            return binding
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_BOUND)


# ===========================================================================
# MARSHRUTLAR
# ===========================================================================


@router.post("/resolve")
async def resolve_binding(
    request: Request,
    payload: ResolveRequest,
    _token: ServiceToken,
) -> ResolveResponse:
    """BOT-01 — «bu Telegram ID kimning akkaunti?» (D-26).

    ⛔ RATE-LIMIT `telegram_user_id` KESIMIDA VA U ISHNING O'ZIDAN OLDIN.
       Sabab `binding_repo` ning modul docstringida: D-26(a) javobi
       neytral bo'lsa ham, cheksiz urinish tayming farqini statistik
       ravishda ochardi. Ikkinchi qatlam — tsiklda erta `break` ning
       YO'QLIGI.

    ⛔ SESSIYA TUG'ILMAYDI: javob faqat holat va (muvaffaqiyatda)
       identifikatorlar (fayl docstringi, D-10).
    """
    cache: Redis = request.app.state.cache
    try:
        await check_bot_resolve_rate(cache, telegram_user_id=payload.telegram_user_id)
    except TooManyAttempts as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=_TOO_MANY_ATTEMPTS
        ) from exc

    outcome = await binding_repo.resolve(
        request.app.state.sessionmaker,
        raw_phone=payload.phone,
        telegram_user_id=payload.telegram_user_id,
    )
    vendor = (
        VendorRefOut(market_id=outcome.vendor.market_id, vendor_id=outcome.vendor.vendor_id)
        if outcome.vendor is not None
        else None
    )
    return ResolveResponse(status=outcome.status, vendor=vendor)


@router.get("/vendor/summary")
async def vendor_summary(
    request: Request,
    _token: ServiceToken,
    telegram_user_id: Annotated[int, Query(gt=0)],
) -> VendorSummaryResponse:
    """BOT-02 (1/2) — sotuvchining qoldig'i, HAR BOZOR uchun alohida.

    ⛔ SON `billing_repo.vendor_outstanding()` DAN KELADI (D-06). Yangi SQL
       yozish IKKINCHI HAQIQAT MANBAI tug'dirardi: bir kun bot bir sonni,
       qarzdorlik reestri boshqasini ko'rsatardi va ikkalasi ham
       «to'g'ri» bo'lardi — bu aynan SBOZOR mavjud bo'lish sababining
       (D-02) teskarisi.

    ⚠ `as_of` — BUGUNGI BIZNES-KUN va u `vendor_charge_allocation()` ga
      ham AYNAN shu qiymat bilan beriladi. Ikki chegara ajralsa ikki
      ko'rinish bir kunni boshqacha sanardi (G-14 tengligi).
    """
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    as_of = business_today()

    summaries: list[VendorSummaryOut] = []
    for binding in await binding_repo.active_bindings(
        sessionmaker, telegram_user_id=telegram_user_id
    ):
        async with binding_repo.tenant_session(
            sessionmaker, market_id=binding.market_id, request_id=None
        ) as session:
            outstanding = await billing_repo.vendor_outstanding(
                session,
                market_id=binding.market_id,
                vendor_ids=[binding.vendor_id],
                as_of=as_of,
            )
            codes = await binding_repo.stall_codes_by_vendor(
                session,
                market_id=binding.market_id,
                vendor_ids=[binding.vendor_id],
                business_date=as_of,
            )
        summaries.append(
            VendorSummaryOut(
                market_id=binding.market_id,
                vendor_id=binding.vendor_id,
                # ⚠ `.get(..., 0)` — qatori umuman yo'q sotuvchi lug'atga
                #   KIRMAYDI (`vendor_outstanding()` docstringi).
                outstanding_soum=outstanding.get(binding.vendor_id, 0),
                as_of=as_of,
                stall_codes=list(codes.get(binding.vendor_id, ())),
            )
        )

    if not summaries:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_BOUND)
    return VendorSummaryResponse(markets=summaries)


@router.get("/vendor/payments")
async def vendor_payments(
    request: Request,
    _token: ServiceToken,
    telegram_user_id: Annotated[int, Query(gt=0)],
    market_id: Annotated[UUID, Query()],
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> VendorPaymentsResponse:
    """BOT-02 (2/2) — «qaysi kunning pattasi to'landi?» (D-24).

    ⛔ ARIFMETIKA `billing_repo.vendor_charge_allocation()` DAN KELADI va
       6-faza uni ATAYIN iste'molchisiz qoldirgan («to'lov tarixi keyingi
       fazaniki») — ⛔ BU FAZA UNING ISTE'MOLCHISI. Yangi taqsimlash
       arifmetikasi YOZILMAYDI: `FIFO_OLDEST_SERVICE_DATE_FIRST` qoidasi
       `sbozor_core.billing` da yashaydi va u natija bilan birga
       qaytariladi.

    ⛔ `market_id` MAJBURIY VA BU ONGLI: bir Telegram ID ikki bozorda faol
       bo'lishi mumkin va serverda «birinchisini tanlash» sotuvchiga
       BOSHQA bozorning tarixini ko'rsatardi. Bot qiymatni
       `GET /vendor/summary` javobidan oladi — ya'ni tanlovni FOYDALANUVCHI
       qiladi, server emas.

    ⚠ SAHIFALASH TAQSIMLANGAN NATIJA USTIDA, SQL DA EMAS: taqsimlash
      BUTUN tarixni ko'rishi shart (kredit eng eski kundan boshlab
      tarqatiladi), ya'ni `LIMIT` ni SQL ga tushirish natijani
      O'ZGARTIRARDI.
    """
    binding = await _single_binding(request, telegram_user_id=telegram_user_id, market_id=market_id)
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    as_of = business_today()

    async with binding_repo.tenant_session(
        sessionmaker, market_id=binding.market_id, request_id=None
    ) as session:
        allocation = await billing_repo.vendor_charge_allocation(
            session,
            market_id=binding.market_id,
            vendor_id=binding.vendor_id,
            as_of=as_of,
        )

    rows = [
        ChargeRowOut(
            service_date=row.service_date,
            stall_code=row.stall_code,
            due_soum=row.due_soum,
            paid_soum=row.paid_soum,
            settled=row.settled,
        )
        for row in allocation.rows
    ]
    if cursor is not None:
        rows = [row for row in rows if _row_cursor(row) > cursor]

    page = rows[:limit]
    return VendorPaymentsResponse(
        market_id=binding.market_id,
        vendor_id=binding.vendor_id,
        rule=allocation.rule,
        rows=page,
        next_cursor=_row_cursor(page[-1]) if len(rows) > limit and page else None,
    )
