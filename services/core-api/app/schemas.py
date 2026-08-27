"""HTTP kontrakt shakllari (Pydantic 2.13).

Chegara qoidalari shu yerda qulflanadi:

* **Telefon CHEGARADA normallashtiriladi** (D-01). `+998 90 123 45 67`,
  `998901234567` va `901234567` — uchtasi ham bitta foydalanuvchi. Agar
  normalizatsiya endpoint ichida qilinsa, bir kun kimdir uni unutadi va
  bitta odam ikkita hisob oladi (qarz tarixi ikkiga bo'linadi).
* **Parol siyosati BITTA joyda** — `validate_password_strength()`.

=============================================================================
FAYL ATAYIN BITTA MODUL BO'LIB QOLADI (02-08 qarori).

2-faza bu faylga ~30 ta domen shaklini qo'shadi va uni paketga bo'lish
(`schemas/` katalogi) o'zini oqlamaydi: mavjud `from app.schemas import ...`
importlari re-export qatlami bilan ushlab turilishi kerak bo'lardi va bu
faza o'rtasida qo'shimcha yuza ochardi. Fayl uzunligi o'qilishga hozircha
to'sqinlik qilmaydi — shakllar bo'lim izohlari ostida guruhlangan.
=============================================================================
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated, Any, Final, Literal, Self, get_args
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    AnomalyKind,
    CameraStatus,
    DiscoveryRunStatus,
    Locale,
    MapDayState,
    OccupancyVerdict,
    OutboxKind,
    OutboxRecipientKind,
    OutboxStatus,
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
    ReversalReason,
    Role,
    StallStatus,
)
from sbozor_core.money import MAX_SAFE_SOUM
from sbozor_core.phone import InvalidPhoneError, normalize_phone

from app.jobs.discovery import DISCOVERY_JOB_ERROR_CODES
from app.services.billing_errors import AMOUNT_UNAVAILABLE_REASONS, SERVER_BILLING_ERROR_CODES
from app.services.capture_errors import CAPTURE_JOB_ERROR_CODES
from app.services.isapi.errors import NVR_ERROR_CODES
from app.services.occupancy_errors import OCCUPANCY_ERROR_CODES

__all__ = [
    "ALERT_DETAIL_KEYS",
    "AUDIT_PAGE_SIZE_MAX",
    "AlertEventOut",
    "AlertListResponse",
    "AnomalyListResponse",
    "AnomalyRowResponse",
    "AssignmentCloseRequest",
    "AssignmentCreateRequest",
    "AssignmentItem",
    "AssignmentListResponse",
    "AuditEntry",
    "AuditListResponse",
    "AuditQuery",
    "BlockingItem",
    "CAMERA_PAGE_SIZE_MAX",
    "CalendarException",
    "CalendarExceptionRequest",
    "CalendarResponse",
    "CameraListResponse",
    "CameraQuery",
    "CameraRead",
    "CameraUpdateRequest",
    "CameraZoneItem",
    "CameraZoneListResponse",
    "CameraZoneRequest",
    "CameraZoneWrite",
    "CaptureDayOut",
    "CaptureRunOut",
    "CategoryItem",
    "CategoryListResponse",
    "CategoryRequest",
    "ChargeAdjustmentRow",
    "ChargeDetailResponse",
    "ChargeEvidenceRow",
    "ChargeListResponse",
    "ChargeRowResponse",
    "AnswerRequest",
    "AnswerResponse",
    "BlindItemResponse",
    "ChangePasswordRequest",
    "CreateUserRequest",
    "CreateUserResponse",
    "DaySummaryOut",
    "DiscoveryConflictResponse",
    "DiscoveryRunRead",
    "DiscoveryStartResponse",
    "IMPORT_ERROR_REPORT_MAX",
    "ISO_WEEKDAYS",
    "ImportErrorItem",
    "ImportErrorReportRequest",
    "ImportErrorResponse",
    "ImportResultResponse",
    "LiveTokenResponse",
    "LocaleResponse",
    "LoginRequest",
    "LoginResponse",
    "MARKET_ERROR_CODES",
    "MIN_PASSWORD_LENGTH",
    "MapCell",
    "MapDayStatusResponse",
    "MapDayStatusRow",
    "MapZone",
    "MarketCreateRequest",
    "MarketCreateResponse",
    "MarketListItem",
    "MarketRef",
    "MeResponse",
    "NvrDeviceCreateRequest",
    "NvrDeviceListResponse",
    "NvrDeviceRead",
    "NvrDeviceUpdateRequest",
    "NvrPasswordRequest",
    "NvrTestConnectionRequest",
    "NvrTestConnectionResponse",
    "OccupancyAccuracyResponse",
    "OccupancyDayResponse",
    "OccupancyRoundResponse",
    "OccupancyStallItem",
    "ConfusionMatrixOut",
    "PaymentCreateRequest",
    "PaymentResponse",
    "PaymentReverseRequest",
    "PendingLookupResponse",
    "PendingMarketResponse",
    "PendingStallResponse",
    "ProportionIntervalOut",
    "ProfileResponse",
    "QueueBudget",
    "RecentPaymentsResponse",
    "RefreshResponse",
    "ReviewBudgetResponse",
    "ReviewItemResponse",
    "ResetPasswordResponse",
    "SCHEDULE_NAME_MAX",
    "SCHEDULE_TIMES_PAYLOAD_MAX",
    "STALL_PAGE_SIZE_MAX",
    "ScheduleCreateIn",
    "ScheduleDayOut",
    "ScheduleItemOut",
    "ScheduleListResponse",
    "ScheduleProfileOut",
    "ScheduleSlotsIn",
    "ScheduleTodayOut",
    "SelectMarketRequest",
    "SessionResponse",
    "SetupStatusResponse",
    "ShiftCloseRequest",
    "ShiftCloseResponse",
    "ShiftOpenResponse",
    "ShiftReportResponse",
    "ShiftReportRow",
    "SnapshotDetailOut",
    "StaffCredentialItem",
    "StaffImportResponse",
    "StallCategoryRequest",
    "StallCreateRequest",
    "StallDetail",
    "StallListItem",
    "StallListResponse",
    "StallMapResponse",
    "StallQuery",
    "StallUpdateRequest",
    "TariffCreateRequest",
    "TariffItem",
    "TariffListResponse",
    "TariffUpdateRequest",
    "UpdateProfileRequest",
    "UserListItem",
    "UserListResponse",
    "VENDOR_PAGE_SIZE_MAX",
    "VENDOR_STALL_CODES_MAX",
    "VendorListItem",
    "VendorListResponse",
    "VendorQuery",
    "VendorRequest",
    "VendorUpdateRequest",
    "ZoneCoverageResponse",
    "ZoneItem",
    "ZoneListResponse",
    "ZoneRequest",
    # --- 07-10: nomuvofiqlik hisoboti va case yuzasi (RECON-01, RECON-02) ---
    "CaseDetailResponse",
    "CaseEventRow",
    "CaseListResponse",
    "CaseRowResponse",
    "CaseUpdateRequest",
    "HitRateResponse",
    "ReconciliationReportResponse",
    "ReconciliationReportRow",
    # --- 07-16: xabar yetkazilishi — direktor ko'radigan yozuv (BOT-04) ---
    "DeliveryListResponse",
    "DeliveryRow",
    # --- 10-01: anonim demo so'rovi (LAND-03) ---
    "DEMO_ERROR_CODES",
    "DemoRequestPayload",
    "DemoRequestResponse",
    "validate_password_strength",
]

MIN_PASSWORD_LENGTH = 10
"""Minimal parol uzunligi (ASVS V6 — uzunlik murakkablikdan muhimroq).

Murakkablik qoidalari (katta harf/raqam/belgi) ATAYIN YO'Q: ular
foydalanuvchini `Parol123!` yozishga majburlaydi va entropiyani
oshirmaydi. D-02 bo'yicha vaqtinchalik parolni admin beradi va u birinchi
kirishda majburiy almashtiriladi.
"""


def validate_password_strength(value: str) -> bool:
    """Parol siyosatiga mos kelishini aytadi.

    Ikki qoida: (1) kamida `MIN_PASSWORD_LENGTH` belgi, (2) faqat bo'sh
    joydan iborat bo'lmasin. Ikkinchisi kerak, chunki `" " * 12` birinchi
    qoidadan o'tib ketardi.

    ATAYIN `bool` qaytaradi (`ValueError` ko'tarmaydi): chaqiruvchi
    endpoint uni `400 {"detail": "weak_password"}` ga aylantiradi. Agar
    tekshiruv Pydantic `field_validator` ichida bo'lganda, FastAPI 422
    qaytarardi va e'lon qilingan kontraktdan chetga chiqardi.
    """
    return len(value) >= MIN_PASSWORD_LENGTH and bool(value.strip())


class MarketRef(BaseModel):
    """Bozor havolasi — `id`, nom va BOZOR faolligi.

    `is_active = false` — usta tugallanmagan QORALAMA bozor (D-16:
    `is_active` faollashtirish bayrog'i, "kamera bor/yo'q" emas). Bozor
    tanlash ekrani uni `Qoralama` belgisi bilan ko'rsatadi va bosilganda
    birinchi tugallanmagan qadamga olib boradi (UI-SPEC §6.4).

    MAYDON MAJBURIY VA STANDART QIYMATI YO'Q — bu ataylab. `= True`
    standart qiymati har bir chaqiruvchiga "argumentni unutish" imkonini
    berardi va unutilgan joyda qoralama bozor JIMGINA "faol" deb
    yorliqlanardi. Aynan shu xato bugungi holatning sababi (UI-SPEC
    §12.1.1 X-2): a'zolik tarmog'ida qoralama bozor allaqachon ko'rinardi,
    lekin uni faoldan ajratadigan maydon javob shaklida umuman yo'q edi.
    Majburiy maydon esa manbani kengaytirishga MAJBURLAYDI — `Membership`
    va `MarketRow` ikkalasida ham `is_active` bor.

    FILTRLASH MAS'ULIYATI ISTE'MOLCHIDA (RESEARCH Pitfall 7): bu maydonning
    javobda bo'lishi aynan ANIQ filtrlashni mumkin qiladigan narsa. Har bir
    iste'molchi o'zi filtrlaydi (6-faza billing job `WHERE m.is_active`),
    "ro'yxat allaqachon toza" degan taxminga tayanmaydi.
    """

    id: UUID
    name: str
    is_active: bool


# ===========================================================================
# 10-FAZA: ANONIM DEMO SO'ROVI (LAND-03) — birinchi autentifikatsiyasiz yozuv
# ===========================================================================

DEMO_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        # IP kesimi 15 daqiqada 5 so'rovdan oshdi (T-10-01).
        "rate_limited",
        # `normalize_phone` (phonenumbers) raqamni o'qiy olmadi — YAGONA
        # haqiqat manbai serverda (T-10-11), klient regeks yozmaydi.
        "invalid_phone",
        # Pydantic chegaralaridan o'tmadi (name/market_name/locale/...).
        "validation_error",
        # Telegram xabarni QABUL QILMADI — «yubordik» deb yolg'on
        # aytilmaydi (SPEC §12.5, RESEARCH B-5).
        "delivery_failed",
    }
)
"""`POST /api/v1/public/demo-requests` xato kodlari — YOPIQ reyestr.

`MARKET_ERROR_CODES` bilan bir xil shakl: frontend'ning ko'zgu darvozasi
(`error-codes.test.mjs`, 10-08 da ulanadi) shu to'plamni literal nusxa
bilan solishtiradi — kod qo'shilsa/ayrilsa ikkala tomon birga o'zgaradi.
"""


class DemoRequestPayload(BaseModel):
    """`POST /api/v1/public/demo-requests` — anonim demo so'rovi (LAND-03).

    ⛔ `phone` uchun `field_validator` YO'Q va bu ATAYIN: `LoginRequest`
    naqshi FastAPI'ning standart 422 shakli (`{"detail":[{...}]}`) bilan
    yiqiladi, LAND-03 esa BITTA `"invalid_phone"` satrini talab qiladi.
    `validate_password_strength` (yuqorida) aynan shu sababdan
    `field_validator` dan qochadi — normalizatsiya marshrutda,
    `HTTPException(422, detail="invalid_phone")` bilan.

    ⛔ Har satr maydonda `max_length` BOR (T-10-03): chegarasiz maydon
    anonim yuzada payload-hajm DoS'iga aylanardi.

    `website` — HONEYPOT: ko'rinmas maydon; to'ldirilgan bo'lsa bot deb
    qaraladi va so'rov JIMGINA muvaffaqiyat bilan tashlab yuboriladi
    (Telegram'ga chaqiruv ketmaydi, xato kodi ham qaytmaydi — aks holda
    honeypot mavjudligi javob kodidan o'qilardi).
    """

    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=1, max_length=32)
    market_name: str = Field(min_length=2, max_length=160)
    stall_count: int | None = Field(default=None, ge=1, le=100_000)
    locale: Literal["uz-Latn", "uz-Cyrl", "ru"]
    website: str = Field(default="", max_length=200)


class DemoRequestResponse(BaseModel):
    """Demo so'rovi javobi — YAGONA maydon va boshqa HECH NIMA (T-10-02).

    ⛔ Bozor identifikatori, nomi yoki topologiyasi bu javobga HECH QACHON
    qo'shilmaydi: marshrut anonim va tenant kontekstiga umuman kirmaydi.
    Kalitlar to'plami `tests/integration/test_demo_request.py` da AYNAN
    `{"delivered"}` deb o'lchanadi.
    """

    delivered: bool


class LoginRequest(BaseModel):
    """`POST /auth/login` — telefon + parol (D-01)."""

    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        """E.164 ga keltiradi; o'qib bo'lmasa 422 (401 EMAS).

        Bu enumeration teshigi EMAS: 422 "raqam formati noto'g'ri" deydi,
        "bunday foydalanuvchi yo'q" demaydi. Mavjud bo'lmagan, lekin
        YAROQLI raqam odatdagi `401 invalid_credentials` ni oladi.
        """
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise ValueError(str(exc)) from exc


class LoginResponse(BaseModel):
    """`POST /auth/login` javobi.

    `market` `None` bo'lsa — bozor tanlanmagan (platforma admini yoki
    a'zoligi bir nechta bo'lgan foydalanuvchi); u holda `markets` ro'yxati
    to'ldiriladi va keyingi qadam `/auth/select-market`.
    """

    access_token: str
    # S105 — RFC 6750 dagi token TURI ("bearer"), sir emas: u har javobda
    # ochiq matnda ketadi va shunday bo'lishi kerak.
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    must_change_password: bool
    locale: str
    market: MarketRef | None
    markets: list[MarketRef]
    roles: list[str]
    is_platform_admin: bool


class SelectMarketRequest(BaseModel):
    """`POST /auth/select-market` (D-06)."""

    market_id: UUID


class SessionResponse(BaseModel):
    """`/auth/select-market` va `/auth/refresh` uchun umumiy javob shakli."""

    access_token: str
    # S105 — RFC 6750 dagi token TURI ("bearer"), sir emas: u har javobda
    # ochiq matnda ketadi va shunday bo'lishi kerak.
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    roles: list[str]
    market: MarketRef


RefreshResponse = SessionResponse
"""`/auth/refresh` javobi — `/select-market` bilan AYNAN bir xil shakl.

Ikkalasi ham "sessiya bozor kontekstiga bog'landi" degan bir xil faktni
qaytaradi, shuning uchun frontend uchun bitta tip yetarli.
"""


class ChangePasswordRequest(BaseModel):
    """`POST /auth/change-password` (D-02).

    `min_length=1` — uzunlik siyosati BU YERDA emas,
    `validate_password_strength()` da: kontrakt bo'yicha zaif parol
    `400 weak_password` beradi, Pydantic esa 422 berardi.
    """

    current_password: Annotated[str, Field(min_length=1)]
    new_password: Annotated[str, Field(min_length=1)]


class MeResponse(BaseModel):
    """`GET /auth/me` — joriy sessiya tavsifi (tenant kontekstidan o'qilgan)."""

    user_id: UUID
    market: MarketRef
    roles: list[str]
    permissions: list[str]
    is_platform_admin: bool


# ---------------------------------------------------------------------------
# Foydalanuvchi boshqaruvi (D-04, D-02, D-08)
# ---------------------------------------------------------------------------


class CreateUserRequest(BaseModel):
    """`POST /users` — ikki bosqichli yaratishning so'rov shakli (D-04).

    `roles` `Role` enum ustida: noma'lum rol nomi 422 beradi va u hech
    qachon `user_market_roles.roles` ga yetib bormaydi. KIM qaysi rolni
    bera olishi (rol berish DARAJASI) esa bu yerda EMAS — u endpoint
    mantiqida, chunki javob 403 bo'lishi kerak, 422 emas: so'rov shakli
    to'g'ri, huquq yetmaydi.
    """

    phone: str
    full_name: str | None = None
    roles: Annotated[list[Role], Field(min_length=1)]
    locale: Locale = Locale.UZ_LATN

    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        """E.164 ga keltiradi (D-01: telefon — yagona identifikator)."""
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise ValueError(str(exc)) from exc


class CreateUserResponse(BaseModel):
    """`POST /users` javobi — vaqtinchalik parol BIR MARTA ochiq qaytariladi.

    Parol DB'da faqat Argon2id hash sifatida yashaydi, ya'ni uni qaytadan
    ko'rsatish IMKONSIZ. Admin uni yo'qotsa yagona yo'l — `reset-password`
    bilan yangisini berish (D-02).
    """

    id: UUID
    temporary_password: str


class UpdateUserRolesRequest(BaseModel):
    """`PATCH /users/{user_id}/roles` — MAVJUD a'zoning rollari (D-04).

    Shakl `CreateUserRequest.roles` bilan AYNAN bir xil va bu ataylab:
    `Role` enum'i noma'lum rol nomini 422 bilan rad etadi, `min_length=1`
    esa bo'sh to'plamni. Rolsiz a'zolik qatori
    `ck_user_market_roles_roles_not_empty` bilan baribir rad etilardi,
    lekin o'shanda javob 500 bo'lardi.

    ⚠ TO'PLAM ALMASHTIRILADI, QO'SHILMAYDI. "Rol qo'sh"/"rolni olib
    tashla" shaklidagi ikki amal ikkita poyga oynasi tug'dirardi (ikki
    admin bir vaqtda tahrirlasa) va UI baribir butun to'plamni
    ko'rsatadi — ya'ni foydalanuvchi ko'rgan narsa aynan yuboriladi.

    KIM qaysi rolni bera olishi bu yerda EMAS — u `users.py` dagi ikki
    darvozada (JORIY rollar + YANGI to'plam).
    """

    roles: Annotated[list[Role], Field(min_length=1)]


class ResetPasswordResponse(BaseModel):
    """`POST /users/{id}/reset-password` javobi (D-02)."""

    temporary_password: str


class UserListItem(BaseModel):
    """`GET /users` ro'yxatining bir qatori.

    `password_hash` bu yerda YO'Q va bo'lishi ham mumkin emas: uni
    `auth_list_users()` umuman qaytarmaydi.
    """

    id: UUID
    phone: str
    full_name: str | None
    roles: list[str]
    is_active: bool
    must_change_password: bool
    locale: str
    created_at: datetime


class UserListResponse(BaseModel):
    """`GET /users` — joriy bozor a'zolari."""

    items: list[UserListItem]


# ---------------------------------------------------------------------------
# Profil va bozor konteksti (D-13, D-06)
# ---------------------------------------------------------------------------


class ProfileResponse(BaseModel):
    """`GET /api/v1/me` — profil + sessiya konteksti.

    `GET /auth/me` (01-06) dan FARQI: u sessiya tavsifi (bozor NOMI va
    huquqlar ro'yxati) va tenant konteksti O'RNATILGAN bo'lishini talab
    qiladi. Bu esa PROFIL: u bozor tanlanmagan holatda ham ishlaydi
    (`market_id: null`), chunki platforma admini bozor tanlashdan oldin ham
    o'z tilini va ismini ko'rishi kerak.
    """

    id: UUID
    phone: str
    full_name: str | None
    locale: str
    roles: list[str]
    market_id: UUID | None
    is_platform_admin: bool
    must_change_password: bool


class UpdateProfileRequest(BaseModel):
    """`PATCH /api/v1/me` — hozircha faqat til (D-13).

    `Locale` enum: `uz-Latn`, `uz-Cyrl`, `ru`. Boshqa qiymat 422 beradi va
    `frontend/src/i18n/routing.ts` dagi ro'yxat bilan AYNAN mos bo'lishi
    `tests/integration/test_me_locale.py` da qulflangan.
    """

    locale: Locale


class LocaleResponse(BaseModel):
    """`PATCH /api/v1/me` javobi — saqlangan til."""

    locale: str


class HeadlineResponse(BaseModel):
    """`GET /api/v1/me/headline` — ⛔ AYNAN BITTA SON VA BITTA i18n KALITI (D-29).

    =========================================================================
    ⛔⛔ UCHINCHI MAYDON QO'SHILMAYDI. `label`, `total`, `rows`,
        `secondary`, `unit` va `*_soum` bilan tugaydigan HAR QANDAY nom —
        ⛔ **TAQIQLANGAN**.

    Sabab «yuza toza bo'lsin» degan estetika emas. Bosh ekranning butun
    qarori (D-28/D-29) shundan iborat: foydalanuvchi BITTA raqamni
    ko'radi. Ikkinchi son qo'shilishi bilan komponent «qaysi biri
    asosiy?» degan savolga javob berishga majbur bo'ladi va o'sha javob
    ROLGA bog'liq bo'lardi — ya'ni klient rolni o'qishga qaytardi va
    D-28 ning server tomonidagi qarori IKKINCHI HAQIQAT MANBAI bilan
    dublikatlanardi.

    ⛔ `extra="forbid"` — yuzaning JIMGINA kengayishiga qarshi (T-07-15).
       Uning jufti testda: javob kalitlari to'plamining LITERAL tengligi
       (`set(body) == {"metric", "value"}`), `len()` EMAS.
    =========================================================================

    ⚠ `label` MAYDONINING YO'QLIGI ATAYIN. Server MATN emas, KALIT
      qaytaradi (`alerting.py:1003-1008` naqshi): matn qaytarsa server
      uchala locale'ni (`uz-Latn`, `uz-Cyrl`, `ru`) bilishi kerak
      bo'lardi va i18n IKKI joyda — serverda ham, klientda ham —
      yashardi. Tarjima klientda, `headline.*` kalitlari bo'yicha.

    ⚠ `value` ning MA'NOSI `metric` ga bog'liq va u SERVERDA hal
      qilinadi: `headline.revenue_today` — so'm, qolgan ikkitasi —
      DONA. Birlikni klient `HEADLINE_UNIT` reyestridan oladi; uni
      javobga qo'shish yuqoridagi «uchinchi maydon» taqiqiga tushardi.
    """

    model_config = ConfigDict(extra="forbid")

    metric: str
    """i18n KALITI — `headline.revenue_today` | `.review_queue` | `.receipts_written`."""
    value: int
    """⛔ Yagona son. Kassir uchun bu SANOQ (Pitfall 1) — `me.py::HEADLINE_ORDER`."""


class MarketListItem(BaseModel):
    """`GET /api/v1/markets` qatori (D-06)."""

    id: UUID
    name: str
    timezone: str
    is_active: bool


# ---------------------------------------------------------------------------
# Audit ko'rish (D-11, D-12)
# ---------------------------------------------------------------------------

AUDIT_PAGE_SIZE_MAX = 200
"""`GET /audit?limit=` ning yuqori chegarasi (T-01-57).

Chegarasiz so'rov bitta so'rovda butun jurnalni JSON'ga aylantirardi —
bu DoS emas, o'z-o'ziga DoS: jurnal o'sib boradi va bir kun bitta
"limit=1000000" so'rovi API'ni yiqitadi. Keyingi sahifa kursor bilan
olinadi — sahifa raqami bilan emas (sababi
`app/repositories/audit_repo.py` modul docstringida).
"""


class AuditQuery(BaseModel):
    """`GET /audit` query parametrlari (D-12).

    `from`/`to` — Python kalit so'zi bilan to'qnashadi, shuning uchun
    maydon nomi `date_from`/`date_to` va tashqi nom alias orqali beriladi.
    Filtr `business_date` USTUNI bo'yicha ishlaydi, vaqt tamg'asini
    yaxlitlovchi ifoda bilan emas: biznes-kun `Asia/Tashkent` bo'yicha DB
    tomonda hisoblanadi va uning ustida indeks bor.
    """

    date_from: date | None = Field(default=None, alias="from")
    date_to: date | None = Field(default=None, alias="to")
    actor_user_id: UUID | None = None
    action: str | None = None
    table_name: str | None = None
    limit: Annotated[int, Field(ge=1, le=AUDIT_PAGE_SIZE_MAX)] = 50
    cursor: str | None = None


class AuditEntry(BaseModel):
    """`audit_log` qatorining tashqi ko'rinishi (kim/qachon/nima/eski->yangi).

    `old_value`/`new_value` JSONB'lari qaytariladi, LEKIN sezgir kalitlar
    `app.repositories.audit_repo.mask_sensitive()` bilan `"***"` ga
    almashtiriladi (T-01-52).
    """

    id: int
    at: datetime
    business_date: date
    actor_user_id: UUID | None
    actor_label: str | None
    action: str
    table_name: str
    row_id: UUID | None
    changed_keys: list[str] | None
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    request_id: str | None
    source: str


class AuditListResponse(BaseModel):
    """`GET /audit` — sahifa + keyingi kursor (`null` bo'lsa oxirgi sahifa)."""

    items: list[AuditEntry]
    next_cursor: str | None


# ===========================================================================
# 2-FAZA: BOZOR DOMENI — zona / toifa / rasta / tarif / kalendar / sotuvchi
# ===========================================================================
#
# BU BO'LIM 2-FAZANING BUTUN HTTP SHARTNOMASINI BIR JOYDA E'LON QILADI.
# `02-09` (tarif/kalendar), `02-10` (sotuvchi/biriktirish), `02-11` (usta),
# `02-12` (import) va `02-13` (frontend kontrakti) shakl haqida QAYTA qaror
# qabul QILMAYDI — ular shu yerdagi modellarni import qiladi. Shakl bir
# rejada qotirilmaganda har bir keyingi reja "yana bitta maydon" qo'shib,
# frontend esa besh xil ro'yxat shakliga moslashishga majbur bo'lardi.
#
# ---------------------------------------------------------------------------
# MASS-ASSIGNMENT DARVOZASI (T-02-54) — LITERAL QOIDA:
#
# QUYIDAGI BIRORTA SO'ROV MODELIDA `market_id` MAYDONI YO'Q va hech qachon
# qo'shilmaydi. Bozor FAQAT `principal.market_id` dan olinadi
# (`_market_id(principal)`), so'rov tanasidan EMAS. Aks holda A bozorining
# admini `{"market_id": "<B>"}` yuborib B bozorida rasta yarata olardi va
# RLS `WITH CHECK` bu urinishni faqat POLICY darajasida to'sardi — ya'ni
# himoya bitta migratsiya xatosidan narida bo'lardi.
#
# Butun faylda `market_id` MAYDONI BOR yagona so'rov modeli —
# `SelectMarketRequest` (D-06). U auth bootstrap yuzasida yashaydi va
# uning butun VAZIFASI aynan bozorni tanlash, ya'ni u tenant chegarasidan
# TASHQARIDA turadi. Domen so'rovlarida bunday maydon yo'q.
# ---------------------------------------------------------------------------
#
# PUL: `int` (so'm) — kasrli tiplar TAQIQ (`sbozor_core.money` modul
# docstringi). Yuqori chegara `MAX_SAFE_SOUM`: qiymat JSON'da oddiy `number`
# bo'lib ketadi va JS xavfsiz butun son chegarasidan oshgani JIMGINA
# yaxlitlanardi.
#
# SANA: `date` — `datetime` EMAS. `valid_from` uchun "soat nechada?" degan
# savolning javobi yo'q: tarif va toifa KUN chegarasida kuchga kiradi.

MARKET_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        # --- zona / toifa reestrlari (02-08) ---
        "zone_name_taken",
        "zone_in_use",
        "category_name_taken",
        "category_in_use",
        # --- rasta reestri (02-08, D-01/D-02/D-04) ---
        "stall_code_taken",
        "stall_code_retired",
        "category_period_exists",
        "category_period_past_locked",
        # --- tarif (02-09, D-06/D-07) ---
        "tariff_already_set_for_date",
        "tariff_past_locked",
        # 0027 — majburiy xizmat haqi (tarozi). ⛔ TARIF KODLARI QAYTA
        #   ISHLATILMAYDI: xabar matni boshqa («tarif» emas, «xizmat
        #   haqi») va ekranda ular YONMA-YON turadi — bir xil matn
        #   qaysi maydon rad etilganini javobsiz qoldirardi.
        "service_fee_already_set_for_date",
        "service_fee_past_locked",
        "service_fee_label_blank",
        "valid_from_must_be_future",
        # --- kalendar (02-09, D-18) ---
        "calendar_exception_exists",
        # --- sotuvchi va biriktirish (02-10, D-09/D-12) ---
        "vendor_phone_taken",
        "assignment_period_overlaps",
        "assignment_not_open",
        "invalid_period",
        # --- usta (02-11, MARKET-01) ---
        "market_incomplete",
        # Jonli bozorni o'chirish yoki faol bozorni QAYTA faollashtirish.
        # `market_incomplete` dan ATAYIN ajratilgan: u "yana nima kerak"
        # deydi va `blocking[]` bilan keladi, bu esa "amal umuman
        # qo'llanmaydi" deydi va hech qanday yo'l ko'rsatmaydi.
        "market_is_active",
        # --- import (02-12, D-13/D-14/D-15) ---
        "import_validation_failed",
        "file_too_large",
        "file_too_complex",
        "unsupported_file_type",
        # Konstrayt buzilishi YOZISH paytida — ya'ni FAQAT poyga holati
        # (ikki admin bir vaqtda import qildi). Mazmun xatolari
        # `import_validation_failed` ostida, QATOR RAQAMI bilan keladi;
        # bu kod esa hech qanday qator ko'rsatmaydi va foydalanuvchi
        # uchun yagona ma'noli harakat — qayta urinish. Ikkalasini
        # birlashtirish 422 javobining `errors[]` shartnomasini
        # buzardi (bu yo'lda ro'yxat BO'SH bo'lardi).
        "import_conflict",
        # --- xodimlar rosteri (02-24, MARKET-07) ---
        #
        # `file_too_complex` DAN ATAYIN AJRATILGAN: u faylning TUZILISHI
        # haqida (varaq/ustun/qator soni, ZIP tuzilishi), bu esa HUJUM
        # YUZASINING chegarasi — bir so'rovda nechta hisob yaratilishi va
        # nechta telefonning band-emasligi oshkor bo'lishi mumkinligi
        # (T-02-181). Ikkalasini birlashtirish adminga "faylni
        # soddalashtiring" degan foydasiz maslahat berardi, holbuki
        # yagona to'g'ri harakat — ro'yxatni bo'laklarga bo'lish.
        "staff_roster_too_large",
        # --- NVR domeni (03-06, CAM-01/CAM-08) ---
        #
        # Bu to'rttasi HTTP chegarasida tug'iladi va ISAPI muloqotiga
        # umuman bog'liq emas — shuning uchun ular quyidagi IKKI
        # IMPORT QILINGAN to'plamdan alohida, literal sifatida turadi.
        "nvr_host_taken",
        "nvr_host_public_blocked",
        "discovery_already_running",
        "nvr_not_found",
        # `nvr_host_public_blocked` DAN ATAYIN AJRATILGAN (03-04 ning ochiq
        # talabi): `NvrAddressError` va `NvrHostNotPrivateError` ikki
        # ALOHIDA sinf, chunki admin uchun ular butunlay boshqa-boshqa
        # muammolar. "Manzilni o'qib bo'lmadi" — TERISH xatosi va yechimi
        # qayta yozish; "ommaviy IP taqiqlangan" — ARXITEKTURA qoidasi va
        # unga javob boshqa manzil sinash EMAS, tunnel ichidagi manzilni
        # topish. Bitta kod ikkalasiga ham noto'g'ri maslahat berardi.
        "nvr_address_invalid",
        # --- ISAPI taksonomiyasi (03-05) va job kodlari (03-06) ---
        #
        # ⚠ IKKALASI HAM IMPORT QILINADI, QO'LDA TAKRORLANMAYDI (§S-5).
        #   Nusxa ko'chirilganda ikki HAQIQAT MANBAI paydo bo'lardi: job
        #   bazaga `nvr_clock_drift` yozib, API uni tanimay `errors.generic`
        #   ko'rsatardi va nosozlik FAQAT foydalanuvchi ekranida ko'rinardi.
        *NVR_ERROR_CODES,
        *DISCOVERY_JOB_ERROR_CODES,
        # --- snapshot jadvali (04-09, CAM-04, D-05) ---
        #
        # To'rttasi HTTP chegarasida tug'iladi: repozitoriyning to'rt xato
        # sinfi (`schedule_repo`) shu kodlarga o'giriladi. Ular kadr olish
        # taksonomiyasiga TUSHMAYDI — o'sha reyestr `capture_runs.error_code`
        # ustuni uchun (§S-7 ning ikkilikka bo'lish qoidasi).
        "schedule_starts_too_soon",
        "schedule_slots_invalid",
        "schedule_not_editable",
        "schedule_period_overlaps",
        # --- kadr yuzasi (04-09, CAM-06) ---
        #
        # Kadr obyekti arxivdan CHIQARILGAN (`storage_tier='purged'`,
        # D-18): qator joyida, bayt yo'q. `not_found` DAN ATAYIN AJRATILGAN —
        # 404 «bunday kadr bo'lmagan» deydi va admin dalilni izlashda
        # davom etardi; bu kod esa «bor edi, 455 kun o'tdi» deydi.
        "snapshot_object_purged",
        "snapshot_storage_unavailable",
        # --- kadr olish taksonomiyasi (04-04) ---
        #
        # ⚠ IMPORT QILINADI, QO'LDA TAKRORLANMAYDI (§S-7). Nusxa
        #   ko'chirilganda job bazaga `capture_stream_limit` yozib, API uni
        #   tanimay `errors.generic` ko'rsatardi va sabab FAQAT
        #   foydalanuvchi ekranida yo'qolardi. Bu kodlar `capture_runs.
        #   error_code` ustunida yashaydi va kun jurnali (`CaptureRunOut`)
        #   ularni AYNAN shu satr bilan qaytaradi.
        *CAPTURE_JOB_ERROR_CODES,
        # --- bandlik domeni (05-04, AI-01/AI-03/AI-04) ---
        #
        # ⚠ IMPORT QILINADI, QO'LDA TAKRORLANMAYDI (§S-7). Bu reyestr
        #   oldingilaridan bitta narsa bilan farq qiladi: `occupancy_events`
        #   da xato ustuni YO'Q (u o'zgarmas hodisa jurnali, D-12), ya'ni bu
        #   kodlarning YAGONA iste'molchisi — aynan shu allowlist. Nusxa
        #   ko'chirilganda router `zone_polygon_self_intersecting` bilan
        #   `HTTPException` ko'tarardi, allowlist esa uni tanimay
        #   `errors.generic` ga tushirardi va admin poligonning QAYSI
        #   qoidasini buzganini bilmasdi.
        *OCCUPANCY_ERROR_CODES,
        # --- billing va kassir domeni (06-02, BILL-02/03, CASH-01…04) ---
        #
        # ⚠ IMPORT QILINADI, QO'LDA TAKRORLANMAYDI (§S-7) — yuqoridagi to'rt
        #   reyestr bilan aynan bir xil qoida.
        #
        # ⚠ AYNAN `SERVER_BILLING_ERROR_CODES`, `ALL_BILLING_ERROR_CODES`
        #   EMAS: ikkinchisida `network_unreachable` ham bor va u FAQAT
        #   mijoz tomonidagi kod — serverdan hech qachon qaytmaydi. Uni bu
        #   yerga kiritish allowlist'ni "server nima qaytarishi mumkin"
        #   degan savolga NOTO'G'RI javob beradigan qilardi.
        #
        # ⚠ KODLAR 06-02 DA REYESTRGA OLINDI, marshrutlar esa 06-09 da
        #   yoziladi. Allowlist AVVAL to'ldirildi ATAYIN: teskari tartibda
        #   router `stall_not_assigned` bilan `HTTPException` ko'tarardi,
        #   allowlist uni tanimay `errors.generic` ga tushirardi va kassir
        #   "bu rastaga sotuvchi biriktirilmagan" o'rniga umumiy xato
        #   matnini ko'rardi — nosozlik FAQAT dala sinovida ko'rinardi.
        *SERVER_BILLING_ERROR_CODES,
    }
)
"""2-faza qaytaradigan BARCHA `detail` kodlari — yigirma to'rtta.

⚠ JUFTINI YANGILASHNI UNUTMANG: bu ro'yxatning UI ko'zgusi
`frontend/src/lib/api-types.ts::ERROR_CODES` da yashaydi va u QO'LDA
sinxron saqlanadi (til chegarasi tufayli avtomatik tekshiruv yo'q —
`security/rbac.py` dagi matritsa bilan AYNAN bir xil holat). Ko'zguda
yo'q kod xavfsizlik teshigi EMAS: `api-client` uni `errors.generic` ga
tushiradi, ya'ni foydalanuvchi umumiy xato matnini ko'radi va aniq sabab
YO'QOLADI. Frontend tomonini `02-13`/`02-14` to'ldiradi.

Ro'yxatning O'ZI ham hujjat: u "bu fazada nima noto'g'ri ketishi mumkin"
savoliga to'liq javob beradi va yangi kod qo'shish shu yerda ko'rinadi.
"""

STALL_PAGE_SIZE_MAX = 200
"""`GET /stalls?limit=` ning yuqori chegarasi (T-02-59).

`AUDIT_PAGE_SIZE_MAX` bilan bir xil qiymat va bir xil sabab: chegarasiz
so'rov 1000 rastali bozorda butun reestrni bitta JSON'ga aylantirardi.
Keyingi sahifa KURSOR bilan olinadi — `OFFSET` umuman ishlatilmaydi
(`app/repositories/stall_repo.py` modul docstringi).
"""

VENDOR_PAGE_SIZE_MAX = 200
"""`GET /vendors?limit=` ning yuqori chegarasi (T-02-78).

`STALL_PAGE_SIZE_MAX` bilan bir xil qiymat, lekin ALOHIDA konstanta:
sotuvchi qatori rasta qatoridan qimmatroq (har biriga bugungi
biriktirishlar agregati hisoblanadi), ya'ni ikki yuza kelajakda turli
chegara talab qilishi mumkin. Bitta konstantani baham ko'rish o'sha
farqni jimgina yo'q qilardi.
"""

VENDOR_STALL_CODES_MAX = 20
"""Bitta sotuvchi uchun javobda qaytariladigan rasta KODLARINING chegarasi.

UI badge sifatida ko'rsatadi (UI-SPEC §8.2), ya'ni yigirmadan ortig'i
ekranda baribir sig'maydi. Ortiqchasi YO'QOLMAYDI — `stall_count`
to'liq sonni beradi va u alohida maydon. Chegarasiz agregat bitta
sotuvchiga yuzlab rasta biriktirilgan bozorda javobni cheksiz
o'stirardi (T-02-78).
"""

ISO_WEEKDAYS: Final[frozenset[int]] = frozenset(range(1, 8))
"""Haftalik jadval uchun ruxsat etilgan kun raqamlari (1=dushanba … 7=yakshanba).

`EXTRACT(ISODOW FROM ...)` bilan AYNAN bir xil asos — `market_is_open()`
da konversiya kerak emas (`sbozor_core.models.market.OPEN_WEEKDAYS_CHECK`).
"""

# ---------------------------------------------------------------------------
# Qayta ishlatiladigan matn cheklovlari.
#
# `StringConstraints` ATAYIN `Field` o'rniga ishlatiladi va IKKI sabab bor:
#   * `strip_whitespace` `Field()` da UMUMAN yo'q — u faqat shu yerda;
#   * cheklov ICHKI `str` ga qo'yiladi (`Annotated[str, ...] | None`), union
#     ustiga EMAS. Union ustidagi metadata Pydantic versiyalari orasida har
#     xil talqin qilinadi va "cheklov jimgina qo'llanmadi" holatini beradi —
#     ya'ni uzunlik chegarasi bor deb o'ylagan joyda hech qanday chegara
#     bo'lmasdi.
#
# Kesish (`strip_whitespace`) DB'dagi `length(btrim(name)) > 0` konstraytining
# jufti: `"  "` kesilgandan keyin bo'sh qoladi va `min_length=1` uni 422
# bilan rad etadi — konstraytgacha yetib bormaydi.
# ---------------------------------------------------------------------------

_NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
_LongNameStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
_CodeStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
_NoteStr = Annotated[str, StringConstraints(max_length=500)]
_ShortNoteStr = Annotated[str, StringConstraints(max_length=200)]
_SearchStr = Annotated[str, StringConstraints(max_length=64)]
_WeekdayList = Annotated[list[int], Field(min_length=1, max_length=7)]


def _normalized_weekdays(value: list[int]) -> list[int]:
    """`open_weekdays` ni tekshiradi va BARQAROR tartibda qaytaradi.

    Ikkala tekshiruv ham DB'dagi `OPEN_WEEKDAYS_CHECK` konstraytining
    jufti, lekin ular ILOVA chegarasida ham kerak: konstrayt buzilganda
    javob 500 (yoki global handler orqali 404) bo'lardi, bu yerda esa
    422 — ya'ni foydalanuvchi nima noto'g'ri ekanini ko'radi.

    TAKRORLANISH ALOHIDA rad etiladi: `[2,2,2]` konstrayt uchun mutlaqo
    yaroqli (`<@` dan o'tadi, uzunligi ham `NULL` emas), lekin u "bozor
    haftada bir kun ishlaydi" degani-yu, foydalanuvchi uchta kun
    tanlaganday ko'rinadi.
    """
    unknown = sorted(set(value) - ISO_WEEKDAYS)
    if unknown:
        raise ValueError(f"hafta kuni 1..7 oralig'ida bo'lishi kerak, berilgani: {unknown}")
    if len(set(value)) != len(value):
        raise ValueError("hafta kunlari takrorlanmasligi kerak")
    return sorted(value)


# ---------------------------------------------------------------------------
# Zonalar (D-03) — YASSI ro'yxat, ierarxiya yo'q
# ---------------------------------------------------------------------------


class ZoneItem(BaseModel):
    """`GET /zones` qatori va `POST`/`PATCH` javobi.

    `stall_count` ATAYIN javobda: u "bu zonani o'chira olamanmi?" savoliga
    oldindan javob beradi (D-03 — zona rastasi bo'lsa o'chirilmaydi) va UI
    tugmani bloklashi uchun ikkinchi so'rov qilishi shart emas.
    """

    id: UUID
    name: str
    stall_count: int


class ZoneListResponse(BaseModel):
    """`GET /zones` — TO'LIQ ro'yxat, sahifalash YO'Q.

    `next_cursor` maydoni ATAYIN yo'q (`StallListResponse` dan farqli):
    zona soni bozor bo'yicha 5–15 ta, ya'ni kursor mexanikasi hech qanday
    muammoni hal qilmasdi-yu, klientga "yana sahifa bormi?" degan doimiy
    savolni yuklardi. Chegara kutilmaganda o'sib ketsa — bu domen qarori
    o'zgargani, ya'ni kontrakt ham ochiq o'zgarishi kerak.
    """

    items: list[ZoneItem]


class ZoneRequest(BaseModel):
    """`POST /zones` va `PATCH /zones/{id}` tanasi.

    `_NameStr` DB'dagi `name_not_blank` konstraytining jufti: import zonani
    NOM bo'yicha bog'laydi (D-14), ya'ni faqat bo'shliqdan iborat nom hech
    qachon mos kelmaydi va jimgina "fantom" zona yaratardi.
    """

    name: _NameStr


# ---------------------------------------------------------------------------
# Toifalar (D-05) — tarif kalitining O'ZI
# ---------------------------------------------------------------------------


class CategoryItem(BaseModel):
    """`GET /categories` qatori.

    `current_tariff_soum` `None` bo'lishi MA'NOLI holat, nuqson emas
    (D-08): toifa yaratilgan, lekin unga hali narx berilmagan. UI aynan shu
    holatni "tarif kiritilmagan" ogohlantirishi bilan ko'rsatadi va usta
    4-qadami undan boshlanadi. `0` QAYTARILMAYDI — u "bepul toifa" degan
    yolg'on ma'no berardi va anomaliya hech qachon ko'rinmasdi.
    """

    id: UUID
    name: str
    stall_count: int
    current_tariff_soum: int | None


class CategoryListResponse(BaseModel):
    """`GET /categories` — sahifalashsiz (`ZoneListResponse` bilan bir xil sabab)."""

    items: list[CategoryItem]


class CategoryRequest(BaseModel):
    """`POST /categories` va `PATCH /categories/{id}` tanasi."""

    name: _NameStr


# ---------------------------------------------------------------------------
# Rastalar (D-01, D-02, D-03, D-04) — fazaning eng ko'p ishlatiladigan yuzasi
# ---------------------------------------------------------------------------


class StallListItem(BaseModel):
    """`GET /stalls` qatori — UI-SPEC §8.2 ustunlarining aynan manbai.

    UCHTA MAYDON `None` BO'LISHI MUMKIN va uchalasi ham HAR XIL holatni
    bildiradi — ularni aralashtirish 6-fazadagi anomaliya hisobini buzardi:

      * `category_id`/`category_name` — rastaga toifa davri yozilmagan
        (import chala o'tgan holat; usta uni to'ldirishga majburlaydi);
      * `vendor_id`/`vendor_name`     — bugun biriktirilgan sotuvchi yo'q
        (D-11: "band, lekin sotuvchisiz" — XATO EMAS, anomaliya alomati);
      * `tariff_soum`                 — toifa bor, lekin uning bugungi
        narxi yo'q (D-08 fail-closed).
    """

    id: UUID
    code: str
    zone_id: UUID
    zone_name: str
    category_id: UUID | None
    category_name: str | None
    status: StallStatus
    vendor_id: UUID | None
    vendor_name: str | None
    tariff_soum: int | None
    created_at: datetime


class StallDetail(StallListItem):
    """`GET /stalls/{id}` va yozuv endpointlarining javobi.

    Ro'yxat qatorining KENGAYTMASI: uchta qo'shimcha maydon faqat bitta
    rasta ochilganda kerak va ularni ro'yxatga qo'shish har bir qatorga
    ortiqcha shaxsiy ma'lumot (telefon) yuklardi.

    `phone` — sotuvchining telefoni, ya'ni SHAXSIY MA'LUMOT (D-09). U
    `vendor_id` bilan birga keladi yoki ikkalasi ham `None`.
    """

    phone: str | None
    assignment_from: date | None
    note: str | None


class StallListResponse(BaseModel):
    """`GET /stalls` — keyset sahifa (`next_cursor` `null` bo'lsa oxirgisi).

    Tartib SERVERDA hal qilinadi (`code_sort` — inson-raqamli: 2 < 10 < 100)
    va frontend uni QAYTA SARALAMAYDI (UI-SPEC §7.3). Klient tomonda
    saralash uchala tilda boshqacha natija berardi va xarita bilan ro'yxat
    ajralib ketardi.
    """

    items: list[StallListItem]
    next_cursor: str | None


class StallQuery(BaseModel):
    """`GET /stalls` query parametrlari (UI-SPEC §8.3 filtrlari).

    `q` — rasta KODI (prefiks) yoki SOTUVCHI ismi. D-01 tufayli raqam bozor
    bo'yicha yagona, ya'ni qidiruv zona tanlashni TALAB QILMAYDI — bu
    6-fazadagi kassir oqimining ("raqam bo'yicha topish") poydevori.

    `limit` ning yuqori chegarasi — `STALL_PAGE_SIZE_MAX` (T-02-59).
    """

    q: _SearchStr | None = None
    zone: UUID | None = None
    category: UUID | None = None
    status: StallStatus | None = None
    limit: Annotated[int, Field(ge=1, le=STALL_PAGE_SIZE_MAX)] = 50
    cursor: str | None = None


class StallCreateRequest(BaseModel):
    """`POST /stalls` tanasi.

    `zone_id` MAJBURIY (D-03): zona har rastada bo'lishi shart va DB'dagi
    `zone_id NOT NULL` ning jufti.

    `category_id` ham MAJBURIY, LEKIN u `stalls` jadvaliga YOZILMAYDI —
    `stalls.category_id` ustuni umuman yo'q (D-04). Uning o'rniga
    `create()` shu qiymat bilan BOSHLANG'ICH toifa davrini yozadi va
    davrning `valid_from` i `market_profile.operating_since` dan olinadi,
    so'rov tanasidan EMAS. Sana maydonining bu yerda YO'QLIGI — ataylab:
    u bo'lganda klient o'tmishdagi sanani tanlab, hisob tarixini surib
    qo'yardi (T-02-61a).

    `status` standart qiymati `active`: yangi rasta ishlaydi deb qaraladi.
    """

    code: _CodeStr
    zone_id: UUID
    category_id: UUID
    status: StallStatus = StallStatus.ACTIVE
    note: _NoteStr | None = None


class StallUpdateRequest(BaseModel):
    """`PATCH /stalls/{id}` tanasi — BERILGAN maydonlar tahrirlanadi.

    `category_id` MAYDONI ATAYIN YO'Q (D-04): toifa — SANADAN kuchga
    kiradigan atribut va uni oddiy `PATCH` bilan almashtirish o'tmishdagi
    hisobni qayta yozardi. Toifa uchun alohida endpoint bor:
    `POST /stalls/{id}/category`.

    `code` esa tahrirlanadi (D-02) — bo'shab qolgan kodni QAYTA ISHLATISHNI
    DB rad etadi (`stall_code_registry` + `trg_stall_code_claim`), ya'ni
    "12-rasta" hisobotda yillar davomida bitta jismoniy joyni anglatadi.
    """

    code: _CodeStr | None = None
    zone_id: UUID | None = None
    status: StallStatus | None = None
    note: _NoteStr | None = None


class StallCategoryRequest(BaseModel):
    """`POST /stalls/{id}/category` tanasi (D-04 — voris modeli).

    `valid_from` FAQAT KELAJAK bo'lishi mumkin va bu qoida ILOVA
    qatlamida majburlanadi (`stall_repo.StallRepository.set_category()`).
    Bugungi kun ham rad etiladi: 6-fazaning kunlik job'i bugungi hisobni
    allaqachon yozib bo'lgan bo'lishi mumkin, ya'ni "bugun" ham o'tmish.

    Pydantic bu yerda sanani KELAJAK deb tekshirmaydi — sababi ataylab:
    javob kodi **403** `category_period_past_locked` bo'lishi kerak, 422
    emas. So'rovning SHAKLI to'g'ri; rad etishning sababi — o'tmish hech
    kimga ochiq emas, ya'ni bu HUQUQ masalasi (02-09 dagi
    `tariff_past_locked` bilan bir xil mulohaza).
    """

    category_id: UUID
    valid_from: date


# ---------------------------------------------------------------------------
# Plan-xarita (MARKET-06, D-19/D-20)
# ---------------------------------------------------------------------------


class MapCell(BaseModel):
    """Xaritadagi bitta katak.

    ⚠ `tone` MAYDONI YO'Q va hech qachon qo'shilmaydi (D-20, RESEARCH
    Pattern 11 qoida 4). API `status` + `has_vendor` XOM faktlarini
    beradi, rangni esa frontend hosil qiladi (`stall-tone.ts`). Rang
    mantiqi serverda hisoblanganda 6-fazada "to'langan/qarzdor" manbai
    qo'shilishi API kontraktini o'zgartirishni talab qilardi; hosila
    funksiyada esa u bitta `switch` ga qo'shiladi.

    ⛔⛔ KOORDINATA QO'SHILDI — D-19 QAYTA KO'RIB CHIQILDI (260820).

    D-19 «koordinata YO'Q» derdi va sababi asosli edi: joylashuv
    avtomatik (CSS Grid), ya'ni hech kim rastalarni qo'lda
    joylashtirmaydi va saqlanadigan `x`/`y` eskirib qolmaydi.

    Foydalanuvchi talabi shuni o'zgartirdi: sxematik xarita bozorning
    HAQIQIY joylashuvini ifodalay olmaydi — qatorlar orasidagi yo'l,
    burchakdagi katta rasta, ikki blokka bo'lingan bozor. Ma'muriyat
    xaritani aynan shu tarzda o'qiydi.

    ⚠ «ESKIRIB QOLISH» xavfi TUG'ILMADI va sabab sxemada: koordinata
      rastaning O'Z QATORIDA yashaydi. Rasta o'chirilsa koordinata ham
      o'chadi, kodi o'zgarsa koordinata o'sha rastada qoladi — ya'ni
      «yo'q rastaning koordinatasi» holati mavjud emas.

    ⛔ IKKALASI HAM `None` BO'LISHI MUMKIN va u NORMAL holat:
      joylashtirilmagan rasta sxematik rejimda chiziladi. Ikki rejim
      yonma-yon yashaydi va bozor xohlaganda ko'chadi.
    """

    id: UUID
    code: str
    status: StallStatus
    has_vendor: bool
    plan_x: int | None
    plan_y: int | None


class MapZone(BaseModel):
    """Xaritadagi zona bloki — kataklar `code_sort` TARTIBIDA keladi.

    `name` — DB kontenti va TARJIMA QILINMAYDI (1-faza D-16).
    """

    id: UUID
    name: str
    cells: list[MapCell]


class StallPlanItem(BaseModel):
    """Bitta rastaning plan-xaritadagi joyi."""

    model_config = ConfigDict(extra="forbid")

    stall_id: UUID
    plan_x: int = Field(ge=0, lt=1000)
    plan_y: int = Field(ge=0, lt=1000)


class StallPlanRequest(BaseModel):
    """`PUT /stalls/plan` — plan-xaritani BIR MARTA saqlash.

    =======================================================================
    ⛔⛔ OMMAVIY, BITTALAB EMAS — VA BU MUHARRIRNING SHAKLIDAN KELIB
        CHIQADI.

    Muharrirda odam o'nlab rastani suradi, keyin bir marta «Saqlash»
    bosadi (kamera zonalari muharriri bilan bir xil naqsh). Har surish
    uchun alohida `PATCH` yuborish uch narsani buzardi:
      · yarim saqlangan plan — tarmoq uzilsa rastalarning bir qismi
        ko'chgan, bir qismi eski joyda qolardi;
      · 300 rastali bozorda 300 so'rov;
      · «bekor qilish» ma'nosini yo'qotardi.

    ⛔ `ochirilgan` MAYDONI BOR: joylashtirilgan rastani plandan
       CHIQARISH kerak bo'lishi mumkin (noto'g'ri qo'yilgan, yoki bozor
       sxematik rejimga qaytmoqchi). Uni `plan_x = null` bilan yuborish
       `Field(ge=0)` bilan ziddiyatga kirardi, shuning uchun alohida
       ro'yxat.
    =======================================================================
    """

    model_config = ConfigDict(extra="forbid")

    placed: list[StallPlanItem] = Field(default_factory=list, max_length=2000)
    cleared: list[UUID] = Field(default_factory=list, max_length=2000)


class StallPlanResponse(BaseModel):
    """Saqlangandan keyingi holat — SERVER sanaydi, klient emas."""

    model_config = ConfigDict(extra="forbid")

    placed_count: int
    cleared_count: int


class StallMapResponse(BaseModel):
    """`GET /stalls/map` — zonalar NOM tartibida (UI-SPEC §7.3).

    Ro'yxat endpointidan ALOHIDA: xarita butun bozorni bir marta oladi
    (sahifalashsiz) va har katak uchun atigi to'rt maydon qaytaradi, ya'ni
    1000 rastali bozorda ham javob kichik qoladi. `GET /stalls` ni
    `limit=1000` bilan chaqirish o'rniga aynan shu endpoint ishlatiladi.
    """

    zones: list[MapZone]


# ---------------------------------------------------------------------------
# Tariflar (02-09 to'ldiradi — bu yerda FAQAT shakl) — D-05/D-06/D-07
# ---------------------------------------------------------------------------


class TariffItem(BaseModel):
    """Tarif tarixining bitta qatori.

    `valid_to` DB'da USTUN EMAS (Pitfall 9) — u keyingi qatorning
    `valid_from` idan `LEAD()` bilan HISOBLANADI va oxirgi qator uchun
    `None` bo'ladi. Ustun sifatida saqlansa ikkinchi haqiqat manbai
    bo'lardi va ikkalasi bir kun ajralib ketardi.

    `is_past` — `valid_from <= business_today()`. UI shu bayroqqa qarab
    tahrir tugmasini KO'RSATMAYDI, lekin bu QULAYLIK: haqiqiy darvoza
    serverda (`trg_tariff_past_immutable`, D-07).
    """

    id: UUID
    category_id: UUID
    category_name: str
    amount_soum: int
    valid_from: date
    valid_to: date | None
    is_past: bool


class TariffCreateRequest(BaseModel):
    """`POST /tariffs` tanasi (D-06 — YANGI qator, `UPDATE` yo'q)."""

    category_id: UUID
    amount_soum: Annotated[int, Field(gt=0, le=MAX_SAFE_SOUM)]
    valid_from: date


class TariffUpdateRequest(BaseModel):
    """`PATCH /tariffs/{id}` tanasi — BERILGAN maydonlar tahrirlanadi (D-07).

    `category_id` MAYDONI ATAYIN YO'Q: tarif kaliti — aynan
    `(category_id, valid_from)` (D-05), ya'ni toifani almashtirish
    qatorni BOSHQA narx tarixiga ko'chirardi. Toifani "tuzatish" kerak
    bo'lsa eski qator o'chiriladi (faqat kelajakdagisi) va yangisi
    yoziladi — shunda ikkala tarix ham to'g'ri qoladi.

    `valid_from` bu yerda ham KELAJAK bo'lishi shart va sabab
    `TariffCreateRequest` dagidan farq qiladi: DB triggeri (`BEFORE
    UPDATE`) faqat `OLD.valid_from` ni tekshiradi, ya'ni kelajakdagi
    qatorni O'TMISHGA surish uning uchun butunlay qonuniy amal. Darvoza
    `TariffRepository.update_future()` da.
    """

    amount_soum: Annotated[int, Field(gt=0, le=MAX_SAFE_SOUM)] | None = None
    valid_from: date | None = None


class ServiceFeeItem(BaseModel):
    """`GET /service-fees` ning bitta qatori — majburiy xizmat haqi (0027).

    ⛔ `TariffItem` NING JUFTI, IKKI ATAYIN FARQ BILAN:

      * `category_id`/`category_name` YO'Q — xizmat haqi BOZORNING narxi,
        toifaga bog'liq emas (`0027` sarlavhasidagi asosiy qaror);
      * `label` BOR — kvitansiyada ko'rinadigan nom. U BOZOR KIRITGAN
        MATN, i18n kaliti EMAS: klient uni tarjima qilmaydi.

    `valid_to` `LEAD(valid_from)` bilan HISOBLANADI (DB'da bunday ustun
    yo'q); `is_past` esa SO'ROV PAYTIDAGI holat va u ham saqlanmaydi.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID
    amount_soum: int
    """`0` — bozorda xizmat haqi olinmaydi (`>= 0`, `> 0` EMAS)."""
    label: str
    valid_from: date
    valid_to: date | None
    is_past: bool


class ServiceFeeCreateRequest(BaseModel):
    """`POST /service-fees` tanasi (D-06 — YANGI qator, `UPDATE` yo'q)."""

    model_config = ConfigDict(extra="forbid")

    amount_soum: Annotated[int, Field(ge=0, le=MAX_SAFE_SOUM)]
    """⛔ `ge=0` — xizmat haqisiz bozor HAQIQIY holat va uni soxta
    «1 so'm» bilan ifodalashga majburlash mumkin emas."""
    label: Annotated[str, Field(min_length=1, max_length=64)]
    """⛔ `min_length=1` DB dagi `length(btrim(label)) > 0` NING JUFTI EMAS,
    UNING ZAIFROQ SHAKLI: Pydantic bo'shliqni qirqmaydi, ya'ni `"   "`
    bu yerdan o'tib DB'da `23514` bo'lardi. Shuning uchun marshrut
    qiymatni `strip()` qilib uzatadi — validatsiya ikki qatlamda."""
    valid_from: date


class ServiceFeeListResponse(BaseModel):
    """`GET /service-fees` — tarix + ruxsat etilgan eng erta sana.

    ⚠ `min_valid_from` `TariffListResponse` dagi bilan AYNI manbadan
      (`TariffRepository.tariff_window()`) keladi — ikki ekran bir xil
      sanani ko'rsatishi shu bilan kafolatlanadi.

    ⛔ `current_amount_soum` ATAYIN ALOHIDA: ro'yxatning birinchi qatori
       KELAJAKDAGI narx bo'lishi mumkin (tartib `valid_from DESC`), ya'ni
       «hozir amalda qancha?» savoliga ro'yxatdan javob olish klientda
       sana solishtirishni talab qilardi — pul haqidagi qarorni klientga
       surish esa D-20 ning aynan taqig'i.
    """

    model_config = ConfigDict(extra="forbid")

    items: list[ServiceFeeItem]
    min_valid_from: date
    current_amount_soum: int | None
    """Bugun amaldagi summa; `null` — hech qachon belgilanmagan."""
    current_label: str | None


class TariffListResponse(BaseModel):
    """`GET /tariffs` — tarif tarixi + ruxsat etilgan eng erta sana.

    ⚠ `next_cursor` YO'Q: tarif ro'yxati sahifalanmaydi (02-09). Toifa
    soni o'nlab, har toifada esa yiliga bir necha narx — ya'ni ro'yxat
    tabiiy ravishda kichik va uni kesish faqat "qaysi narx qachon amal
    qilgan" savolining javobini yashirardi.
    """

    items: list[TariffItem]
    min_valid_from: date
    """Klient tanlashi mumkin bo'lgan ENG ERTA `valid_from`.

    MAYDON MAJBURIY VA `| None` EMAS — bu ataylab (`MarketRef.is_active`
    bilan aynan bir xil sabab): standart qiymat har bir chaqiruvchiga uni
    "unutish" imkonini berardi va unutilgan joyda sana maydoni chegarasiz
    ochilib qolardi. Ro'yxat BO'SH bo'lganda ham qiymat keladi — usta
    4-qadami aynan bo'sh ro'yxatdan boshlanadi.

    Qiymatni **02-09** hisoblaydi: qoralama bozorda
    `market_profile.operating_since`, faol bozorda `business_today() + 1`.
    Bu rejada faqat SHAKL e'lon qilinadi.

    ⚠ BU DARVOZA EMAS — u KLIENT QULAYLIGI (sana maydonining `min`
    atributi, 02-15). Haqiqiy tekshiruv `add_tariff()` da va u DevTools
    bilan olib tashlanmaydi.
    """


# ---------------------------------------------------------------------------
# Ish kunlari kalendari (D-17/D-18) — 02-09 to'ldiradi
# ---------------------------------------------------------------------------


class CalendarException(BaseModel):
    """Haftalik jadvaldan chiqadigan alohida kun.

    `is_open` IKKI TOMONLAMA: `false` — bayram/yopiq kun, `true` — jadvalda
    dam olish bo'lgan, lekin ISHLAYDIGAN kun. Bitta jadval ikkalasini ham
    ifodalaydi, chunki `market_is_open()` da istisno HAR DOIM haftalik
    jadvaldan ustun turadi.
    """

    id: UUID
    exception_date: date
    is_open: bool
    note: str | None


class CalendarResponse(BaseModel):
    """`GET /calendar` — haftalik jadval + istisnolar (FAQAT bozor darajasida, D-18)."""

    open_weekdays: list[int]
    exceptions: list[CalendarException]


class WeekdaysRequest(BaseModel):
    """`PUT /calendar/weekdays` tanasi (D-17).

    `min_length=1` — BO'SH massiv rad etiladi. U DB konstraytidan ham
    o'tmasdi, lekin sabab muhimroq: bo'sh jadval "bozor hech qachon
    ochilmaydi" degani va tushum JIMGINA nolga tushardi.
    """

    open_weekdays: _WeekdayList

    @field_validator("open_weekdays")
    @classmethod
    def _weekdays(cls, value: list[int]) -> list[int]:
        return _normalized_weekdays(value)


class CalendarExceptionRequest(BaseModel):
    """`POST /calendar/exceptions` tanasi (D-18)."""

    exception_date: date
    is_open: bool
    note: _ShortNoteStr | None = None


# ---------------------------------------------------------------------------
# Sotuvchilar va biriktirishlar (D-09…D-12) — 02-10 to'ldiradi
# ---------------------------------------------------------------------------


class VendorListItem(BaseModel):
    """`GET /vendors` qatori — SHAXSIY MA'LUMOT (D-09: o'qish ham auditda).

    `stall_codes` ATAYIN `stall_count` bilan BIRGA: sanoq ro'yxatning qisqa
    ko'rinishi uchun (UI-SPEC §8.2 — `<640px` da faqat badge), kodlar esa
    kengroq ekranda ko'rsatiladi. Ikkinchi so'rov qilinmaydi.
    """

    id: UUID
    full_name: str
    phone: str
    stall_count: int
    stall_codes: list[str]
    created_at: datetime


class VendorRequest(BaseModel):
    """`POST /vendors` va `PATCH /vendors/{id}` tanasi (D-12).

    Telefon CHEGARADA normallashtiriladi — `CreateUserRequest` dagi shakl
    AYNAN takrorlanadi va sabab ham o'sha: normalizatsiya endpoint ichida
    qilinsa, bir kun kimdir uni unutadi va bitta sotuvchi ikkita qator
    oladi (qarz tarixi ikkiga bo'linadi).

    Unikalik BOZOR ICHIDA (`uq_vendors_market_id_phone_e164`), global EMAS:
    bir odam ikki bozorda savdo qilishi mumkin (D-12, T-02-44).
    """

    full_name: _LongNameStr
    phone: str

    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        """E.164 ga keltiradi; o'qib bo'lmasa 422."""
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise ValueError(str(exc)) from exc


class VendorUpdateRequest(BaseModel):
    """`PATCH /vendors/{id}` tanasi — BERILGAN maydonlar tahrirlanadi (D-12).

    `VendorRequest` dan farqi FAQAT majburiylikda: u yerda ikkala maydon
    ham shart (yangi sotuvchini ismsiz yoki telefonsiz yaratib bo'lmaydi),
    bu yerda esa faqat ismni tuzatish ("Aliyev Vali" -> "Aliev Vali")
    telefonni qayta yuborishni TALAB QILMASLIGI kerak — aks holda klient
    uni ekrandan qayta o'qib yuborardi va bir kun eskirgan qiymat bilan
    yuborib, telefonni jimgina orqaga qaytarardi.

    Cheklov `Annotated[str, StringConstraints(...)] | None` shaklida —
    union USTIGA emas (02-08 deviatsiya #7 ning qoidasi).

    Telefon bu yerda ham CHEGARADA normallashadi: `VendorRequest` bilan
    bir xil validator, ya'ni ikki yo'l bir xil E.164 shaklini yozadi.
    """

    full_name: _LongNameStr | None = None
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        """E.164 ga keltiradi; o'qib bo'lmasa 422."""
        if value is None:
            return None
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise ValueError(str(exc)) from exc


class VendorQuery(BaseModel):
    """`GET /vendors` query parametrlari (UI-SPEC §8.2).

    `q` — F.I.Sh. PREFIKSI yoki telefonning ISTALGAN qismi. Ikki xil
    naqsh ataylab: ism bo'yicha qidiruv alifbo tartibidagi ro'yxatni
    toraytiradi (prefiks), telefon esa odatda o'rtasidan eslab qolinadi
    ("...45 67 bilan tugaydigan").

    `limit` ning yuqori chegarasi — `VENDOR_PAGE_SIZE_MAX` (T-02-78).
    """

    q: _SearchStr | None = None
    limit: Annotated[int, Field(ge=1, le=VENDOR_PAGE_SIZE_MAX)] = 50
    cursor: str | None = None


class VendorListResponse(BaseModel):
    """`GET /vendors` — keyset sahifa (sotuvchi soni rastalar bilan o'sadi)."""

    items: list[VendorListItem]
    next_cursor: str | None


class AssignmentItem(BaseModel):
    """Rasta ↔ sotuvchi biriktirish DAVRI (D-09/D-10/D-11).

    `to_date` `None` — davr OCHIQ (sotuvchi hozir ham shu rastada).
    Chegara `[)`: almashinuv kuni YANGI sotuvchiga tegishli va o'sha
    kunning pattasi unga yoziladi (`sbozor_core.periods`).

    PUL MAYDONI YO'Q va bo'lmaydi (D-10): qarz `daily_charges` da tug'iladi
    va ESKI sotuvchida qoladi.
    """

    id: UUID
    stall_id: UUID
    stall_code: str
    vendor_id: UUID
    vendor_name: str
    from_date: date
    to_date: date | None


class AssignmentCreateRequest(BaseModel):
    """`POST /assignments` tanasi. Qoplanish DB'da rad etiladi (`23P01` → 409)."""

    stall_id: UUID
    vendor_id: UUID
    from_date: date
    to_date: date | None = None


class AssignmentCloseRequest(BaseModel):
    """`PATCH /assignments/{id}` tanasi — OCHIQ davrni yopadi.

    Yagona maydon `to_date` va bu ataylab: `from_date` ni tahrirlash
    o'tmishdagi kunlarning qarz egaligini boshqa sotuvchiga ko'chirardi
    (D-10) va `daily_charges` allaqachon yozilgan kunlarni qayta
    baholardi. Davrni "surish" uchun yagona qonuniy yo'l — eskisini
    yopib, yangisini ochish, ya'ni IKKI alohida audit izi.
    """

    to_date: date


class AssignmentListResponse(BaseModel):
    """`GET /stalls/{stall_id}/assignments` — rastaning biriktirish TARIXI.

    Sahifalash YO'Q: bir rastadagi davrlar soni yiliga bir necha marta
    o'sadi va butun tarix bitta ekranga sig'adi. Kursor mexanikasi bu
    yerda hech qanday muammoni hal qilmasdi-yu, "sotuvchi qachondan beri
    shu rastada" savolining javobini kesib qo'yardi.
    """

    items: list[AssignmentItem]


# ---------------------------------------------------------------------------
# "Yangi bozor" ustasi (MARKET-01, D-16) — 02-11 to'ldiradi
# ---------------------------------------------------------------------------


class MarketCreateRequest(BaseModel):
    """`POST /markets` tanasi — ustaning 1-qadami.

    `operating_since` MAJBURIY va bu A3 taxminining bevosita natijasi:
    barcha BOSHLANG'ICH `valid_from` lar (birinchi tarif va birinchi toifa
    davri) aynan shu sanadan olinadi. Import kuni qo'yilsa, 6-faza undan
    oldingi har bir kunni "tarifsiz" deb topib butun tarixni anomaliyaga
    aylantirardi.

    `tin` formati DB'da ham tekshiriladi (`tin_format`, 9 raqam — A2
    taxmini); bank rekvizitlari esa ATAYIN formatlanmaydi (A1 buyurtmachi
    bilan tasdiqlanmagan va noto'g'ri qat'iy format haqiqiy rekvizitni rad
    etardi).
    """

    name: _LongNameStr
    timezone: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    operating_since: date
    open_weekdays: _WeekdayList | None = None
    address: _NoteStr | None = None
    tin: Annotated[str, StringConstraints(pattern=r"^[0-9]{9}$")] | None = None
    bank_account: Annotated[str, StringConstraints(max_length=50)] | None = None
    bank_mfo: Annotated[str, StringConstraints(max_length=20)] | None = None
    contact_phone: Annotated[str, StringConstraints(max_length=32)] | None = None

    @field_validator("open_weekdays")
    @classmethod
    def _weekdays(cls, value: list[int] | None) -> list[int] | None:
        return None if value is None else _normalized_weekdays(value)


class MarketCreateResponse(BaseModel):
    """Bozor holatining qisqa javobi — `POST /markets` VA `POST /{id}/activate`.

    `is_active` yaratishda HAR DOIM `false` (D-16: yangi bozor QORALAMA),
    faollashtirishda esa HAR DOIM `true`. Maydon ikkala yo'lda ham
    qaytariladi va aynan shuning uchun bitta DTO ikkalasiga xizmat qiladi:
    klient bayroqni HECH QACHON taxmin qilmaydi, u har javobda o'qiladi va
    `MarketRef` bilan bir xil shaklda talqin qilinadi.

    ⚠ 02-11 gacha bu DTO faqat yaratish yo'liga tegishli edi. Ikkinchi,
    maydonlari AYNAN bir xil `MarketActivateResponse` yaratish frontendga
    bitta shaklning ikki nomini berardi va ular bir kun ajralib ketardi
    (02-10 dagi `GET /vendors/{id}` -> `VendorListItem` qarori bilan bir
    xil mulohaza).
    """

    id: UUID
    name: str
    is_active: bool


class BlockingItem(BaseModel):
    """Faollashtirishni to'sib turgan bitta sabab (UI-SPEC §6.6).

    `step` — ustaning QAYSI qadamiga qaytish kerakligi. Aynan shu maydon
    409 ni "xato" emas, "yo'l ko'rsatkichi" qiladi: UI foydalanuvchini
    to'g'ridan-to'g'ri chala qadamga olib boradi.
    """

    step: int
    code: str
    detail: str


class SetupStatusResponse(BaseModel):
    """`GET /markets/{id}/setup-status` — ustaning to'liqlik holati.

    SANOQLAR XOM HOLDA qaytariladi va UI ularni "3/5 toifada tarif bor"
    shaklida ko'rsatadi. `can_activate` esa SERVER qarori: klient uni
    sanoqlardan qayta hisoblamaydi, aks holda to'liqlik qoidasi ikki joyda
    yashab, bir kun ajralib ketardi (02-11 `activate` darvozasi bilan).

    `calendar_configured` — `bool`, sanoq emas: haftalik jadval BOR yoki
    YO'Q, "yarim sozlangan" holati yo'q (fail-closed narxi).
    """

    zones: int
    categories: int
    tariffs_covered: int
    categories_total: int
    stalls: int
    stalls_with_category: int
    vendors: int
    calendar_configured: bool
    cameras: int
    can_activate: bool
    blocking: list[BlockingItem]


# ---------------------------------------------------------------------------
# Excel import (D-13/D-14/D-15) — 02-12 to'ldiradi
# ---------------------------------------------------------------------------


class ImportResultResponse(BaseModel):
    """`POST /imports/*` muvaffaqiyatli javobi.

    `skipped` ALOHIDA maydon: "10 qator yozildi" javobi 12 qatorli fayl
    uchun foydalanuvchini chalg'itardi — u qolgan ikkitasi qayerga
    ketganini bilishi kerak.
    """

    inserted: int
    skipped: int


class ImportErrorItem(BaseModel):
    """Bitta qatordagi validatsiya xatosi.

    `row` — FAYLDAGI qator raqami (1 dan, sarlavha bilan birga), ya'ni
    foydalanuvchi Excel'da o'sha raqamga to'g'ridan-to'g'ri o'ta oladi.
    `message` DB xatosidan OLINMAYDI: RLS `DETAIL` ni o'chiradi (Pitfall 4)
    va xom konstrayt matni foydalanuvchiga hech nima aytmasdi.
    """

    row: int
    code: str
    message: str


class ImportErrorResponse(BaseModel):
    """`POST /imports/*` ning 422 javobi — D-14: validatsiya YOZISHDAN OLDIN.

    `error_counts` — `{kod: soni}`. 500 qatorli faylda 480 ta bir xil xato
    bo'lishi mumkin va ularning hammasini ro'yxatda ko'rsatish ekranni
    foydasiz qilardi; sanoq esa "asosiy muammo nima" savoliga bitta qatorda
    javob beradi (`errors` ro'yxati esa cheklangan namuna bo'ladi).
    """

    detail: str
    errors: list[ImportErrorItem]
    error_counts: dict[str, int]


class StaffCredentialItem(BaseModel):
    """Yaratilgan bitta hisob va uning BIR MARTALIK paroli (D-02, MARKET-07).

    `row` — FAYLDAGI qator raqami: admin javobni o'z faylining yonida
    o'qiydi va kimning paroli ekanini telefon bilan emas, KO'ZI bilan
    tekshiradi.

    ⚠ `temporary_password` DB'da faqat Argon2id hash sifatida yashaydi,
    ya'ni uni qaytadan ko'rsatish IMKONSIZ. Admin uni yo'qotsa yagona
    yo'l — `POST /users/{id}/reset-password`.
    """

    row: int
    phone: str
    full_name: str | None
    roles: list[str]
    temporary_password: str


class StaffImportResponse(BaseModel):
    """`POST /imports/staff` muvaffaqiyatli javobi (MARKET-07).

    ⚠ `ImportResultResponse` DAN MEROS OLMAYDI VA BU ATAYIN.

    `credentials` maydoni bu javobni MAXFIY qiladi (`Cache-Control:
    no-store`, klientda keshlanmaydi). Meros orqali u bir kun
    `stalls`/`vendors` javobiga ham oqib o'tishi mumkin edi — o'sha
    javoblar esa maxfiy emas va ularning yo'li boshqacha qo'riqlanadi.
    Ikkita maydonni takrorlash bu xavfdan ancha arzon.

    `skipped` — D-15 bo'yicha o'tkazib yuborilgan MAVJUD a'zolar soni.
    Ular uchun `credentials` da yozuv BO'LMAYDI: parol tiklanmagan,
    ya'ni ko'rsatadigan qiymat ham yo'q.
    """

    inserted: int
    skipped: int
    credentials: list[StaffCredentialItem]


IMPORT_ERROR_REPORT_MAX = 5_000
"""`POST /imports/errors.xlsx` qabul qiladigan eng ko'p xato soni (T-02-97).

`xlsx_reader.MAX_ROWS` bilan AYNAN bir xil: bitta fayl eng ko'pi bilan
shuncha qator beradi, ya'ni har qatorda bittadan xato bo'lgan holatda
ham ro'yxat shu chegaraga sig'adi.

⚠ CHEGARA MAJBURIY. Usiz endpoint o'z-o'ziga DoS bo'lardi: klient
o'nlab million elementli massiv yuborib, serverda o'nlab million
qatorli `.xlsx` qurdirardi. Kirish bu yerda MAHSULOT yo'lidan
kelmaydi — u 422 javobining NUSXASI, ya'ni uni hech kim tekshirmagan.
"""


class ImportErrorReportRequest(BaseModel):
    """`POST /imports/errors.xlsx` so'rov tanasi.

    Klient 422 javobining `errors` massivini AYNAN qaytarib yuboradi.
    Server uni SAQLAMAYDI: 300 qatorlik xato ro'yxatini bazaga yozish
    hech qanday savolga javob bermaydigan, lekin saqlash muddati va
    o'chirish yo'li talab qiladigan ma'lumot yaratardi.

    Uzunlik `IMPORT_ERROR_REPORT_MAX` bilan cheklangan (T-02-97).
    Cheklov `Field(max_length=...)` orqali — ya'ni u Pydantic
    darajasida, endpoint mantiqiga YETIB KELMASDAN qo'llanadi va
    ortiqcha massiv umuman xotiraga to'liq yig'ilmaydi.
    """

    errors: Annotated[list[ImportErrorItem], Field(max_length=IMPORT_ERROR_REPORT_MAX)]


# ---------------------------------------------------------------------------
# NVR qurilmalari va kashfiyot (03-06, CAM-01/CAM-08)
#
# =============================================================================
# PAROL MAYDONI JAVOB MODELLARIDA UMUMAN E'LON QILINMAYDI (SC#4, T-03-39).
#
# `Field(exclude=True)` YETARLI EMAS va bu farq nozik: `exclude` — bu
# SERIALIZATSIYA SOZLAMASI, kafolat emas. U `model_dump()` ning ayrim
# chaqiruvlarida (`model_dump(exclude=None)` yoki `mode="python"` bilan
# qo'lda yig'ilgan lug'atda) e'tiborsiz qolishi mumkin va o'shanda parol
# javobga tushardi. Maydonning UMUMAN BO'LMASLIGI esa yagona chegara:
# mavjud bo'lmagan maydon hech qanday sozlama bilan qaytmaydi.
#
# `has_password: bool` uning O'RNINI BOSADI — UI ga "parol saqlanganmi?"
# savoliga javob kerak, parolning O'ZI emas.
# =============================================================================
#
# =============================================================================
# `market_id` SO'ROV MODELLARIDA HAM YO'Q (T-03-44, `stalls.py:47-49`).
#
# Bozor FAQAT `principal.market_id` dan olinadi. Aks holda A bozorining
# admini `{"market_id": "<B>"}` yuborib B bozorida NVR yarata olardi va
# yagona to'siq RLS `WITH CHECK` bo'lardi — ya'ni himoya bitta migratsiya
# xatosidan narida qolardi.
# =============================================================================
# ---------------------------------------------------------------------------

_NVR_ADDRESS_MAX = 255
"""Manzil satrining chegarasi — `nvr_devices.host` `text` bo'lsa ham.

Chegara DB uchun emas, PARSER uchun: `split_address()` ga cheksiz satr
berish uni sababsiz ishga soladi va xato matni javobga xom kirishni
qaytarardi.
"""

_NvrAddressStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_NvrSecretStr = Annotated[str, StringConstraints(min_length=1, max_length=128)]
"""Parol maydoni — `strip_whitespace` ATAYIN YO'Q.

NVR paroli bo'shliq bilan boshlanishi yoki tugashi MUMKIN va uni
jimgina kesib tashlash "parol noto'g'ri" degan tushuntirib bo'lmaydigan
`401` beradi. Foydalanuvchi nomi bilan farq shu yerda: u ISAPI da
bo'shliqsiz.
"""


class NvrDeviceCreateRequest(BaseModel):
    """`POST /nvr-devices` tanasi — D-01 ning butun kirish yuzasi.

    ⚠ UCHTA MAYDON, BOSHQA HECH NIMA. Admin RTSP portini ham, kanal
      sonini ham, model nomini ham KIRITMAYDI — ularning hammasi
      kashfiyot natijasida to'ldiriladi (D-01: "muhandis aralashuvi
      talab qiladigan har qanday yechim fazani buzadi").

    `address` — XOM satr (`192.168.1.64`, `192.168.1.64:8080`,
    `https://nvr.local:8443`). Uni `host`/`port`/`use_tls` ga ajratish
    server tomonda (`app/services/nvr_host.py::split_address`), chunki
    klientdagi ajratish QULAYLIK, bu yerdagisi esa KONTRAKT.
    """

    address: Annotated[_NvrAddressStr, Field(max_length=_NVR_ADDRESS_MAX)]
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    password: _NvrSecretStr


class NvrDeviceUpdateRequest(BaseModel):
    """`PATCH /nvr-devices/{id}` tanasi.

    ⚠ `address` BU YERDA YO'Q (UI-SPEC §4.6): u `UNIQUE (market_id, host,
      port)` kalitining bir qismi va uni tahrirlash idempotentlik
      semantikasini ochib yuborardi — "bu o'sha qurilmami yoki
      boshqasimi?" savoliga javob qolmasdi. Manzil o'zgarsa NVR qayta
      qo'shiladi.

    ⚠ `tunnel_subnet` HAM BU YERDA YO'Q. D-07 uni bozorlar ARO noyob
      qiladi (qisman UNIQUE indeks), ya'ni uni tahrirlash `23505` ni va
      u bilan birga YANGI xato kodini keltirardi. Tunnel onboarding'i —
      WireGuard yuzasining bir qismi va u o'z rejasida keladi; shu
      fazada maydon FAQAT O'QISH uchun (`NvrDeviceRead`).

    Natijada bu modelda bitta maydon qoladi va bu ataylab: qolgan
    hamma narsa yo KASHFIYOT natijasi (model, seriya, portlar), yo
    o'zining ALOHIDA endpointi (parol) ostida.
    """

    username: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)] | None
    ) = None


class NvrPasswordRequest(BaseModel):
    """`POST /nvr-devices/{id}/password` tanasi.

    ⚠ ESKI PAROL SO'RALMAYDI (UI-SPEC §4.6) va bu ataylab: u bizda ochiq
      matnda YO'Q, ya'ni uni tekshirish uchun avval deshifrlash kerak
      bo'lardi. Darvoza boshqa joyda — `CAMERA_MANAGE` huquqi.
    """

    password: _NvrSecretStr


class NvrTestConnectionRequest(BaseModel):
    """`POST /nvr-devices/test-connection` tanasi — YOZUV YARATMAYDI.

    Shakli `NvrDeviceCreateRequest` bilan bir xil va bu ataylab: UI
    aynan bir xil formadan ikkala endpointni ham chaqiradi (§4.3).
    Meros olinmaydi — ikkala model mustaqil o'zgarishi mumkin va
    "tekshiruv" ning kirishi "yaratish" ning kirishiga BOG'LANIB
    qolmasligi kerak.
    """

    address: Annotated[_NvrAddressStr, Field(max_length=_NVR_ADDRESS_MAX)]
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    password: _NvrSecretStr


class NvrDeviceRead(BaseModel):
    """`GET`/`POST`/`PATCH` javobi — QURILMA PASPORTI, sirsiz.

    ⚠ `password` NOMLI MAYDON BU YERDA YO'Q va u hech qachon
      qo'shilmaydi (bo'lim boshidagi izoh). `test_password_never_in_any_
      response` buni HAR marshrut uchun XOM javob tanasida tekshiradi.

    `rtsp_port` `None` — hali skan qilinmagan; `rtsp_port_assumed=True` —
    554 fallback ishlatilgan va u jonli ko'rish yiqilganda BIRINCHI
    tekshiriladigan gumondor (UI-SPEC §4.6).
    """

    id: UUID
    host: str
    port: int
    use_tls: bool
    username: str
    model: str | None
    serial_number: str | None
    firmware_version: str | None
    device_type: str | None
    rtsp_port: int | None
    rtsp_port_assumed: bool
    tunnel_subnet: str | None
    last_discovery_at: datetime | None
    has_password: bool


class NvrDeviceListResponse(BaseModel):
    """`GET /nvr-devices` — TO'LIQ ro'yxat, sahifalash YO'Q.

    `ZoneListResponse` bilan bir xil qaror: bozorda NVR soni bir-ikkita
    (Karmanada bitta), ya'ni kursor mexanikasi hech qanday muammoni hal
    qilmasdi-yu, klientga doimiy "yana sahifa bormi?" savolini yuklardi.
    """

    items: list[NvrDeviceRead]


class NvrTestConnectionResponse(BaseModel):
    """`POST /nvr-devices/test-connection` javobi — HAR DOIM HTTP 200.

    ⚠ XATO HOLATIDA HAM 200 (UI-SPEC §4.3/§7): UI xatoni FORMA ICHIDAGI
      blok sifatida chizadi va unda sabab + tuzatish yo'li bo'ladi
      (D-02). HTTP xatosi bo'lganda TanStack Query uni tarmoq nosozligi
      deb qayta urinardi — aynan D-03 taqiqlagan xulq.

    Muvaffaqiyatda TO'RTALA maydon ham MAJBURIY (UI-SPEC §4.5):
    `model`, `device_type`, `channels_preview`, `clock_drift_seconds`.
    Kanallar soni adminning "to'g'ri qurilmaga ulandimmi?" savoliga
    YAGONA javobi; soat farqi esa 300 s dan kichik bo'lsa ham
    ko'rsatiladi — 250 soniyalik farq bugun ishlaydi va ertaga sinadi.
    """

    ok: bool
    model: str | None = None
    device_type: str | None = None
    serial_number: str | None = None
    channels_preview: int | None = None
    clock_drift_seconds: float | None = None
    rtsp_port: int | None = None
    rtsp_port_assumed: bool = False
    error_code: str | None = None
    error_detail: dict[str, Any] | None = None
    auth_locked: bool = False
    """`error_code ∈ AUTH_LOCKING_CODES` (UI-SPEC §4.4 ning backend tomoni).

    Bayroq BACKENDDA hisoblanadi, frontendda EMAS: to'plamning o'zi
    `app/services/isapi/errors.py` da yashaydi va uni klientda qayta
    yozish ikkinchi haqiqat manbai bo'lardi. `true` bo'lganda UI "Qayta
    urinish" affordansini RENDER QILMAYDI (yashirmaydi — u umuman
    yo'q).
    """


class DiscoveryStartResponse(BaseModel):
    """`POST /nvr-devices/{id}/discover` javobi (202).

    Yagona maydon — `run_id`. Mijoz undan keyin
    `GET /nvr-devices/{id}/discovery-runs/{run_id}` ni poll qiladi
    (UI-SPEC §5.3: 2 soniyada bir, terminal holatda TO'XTAYDI).
    """

    run_id: UUID


class DiscoveryConflictResponse(BaseModel):
    """`409 discovery_already_running` javobining TANASI — `run_id` BILAN.

    ⚠ UI-SPEC §5.6 [TALAB]: javob tanasi MAVJUD yugurishning `run_id`
      sini o'z ichiga OLISHI SHART. Aks holda UI ikkinchi so'rov qilishga
      majbur bo'lardi — poyga holatining o'zida yana bitta poyga.

    UI buni XATO deb ko'rsatmaydi: ikki admin (yoki bitta admin ikki
    tabda) tugmani bir vaqtda bosishi normal ish jarayoni. U shunchaki
    qaytgan `run_id` ni poll qila boshlaydi.

    ⚠ MODEL FAQAT OPENAPI UCHUN E'LON QILINGAN — `HTTPException` javob
      modelidan o'tmaydi. Shakl `main.py` dagi global handler bilan mos
      bo'lishi uchun `detail` kalitini SAQLAYDI va `run_id` uning
      YONIDA turadi, ICHIDA emas: `detail` ni obyektga aylantirish
      frontendning mavjud `detail: string` shartnomasini buzardi
      (`lib/market-errors.ts`).
    """

    detail: str
    run_id: UUID


class DiscoveryRunRead(BaseModel):
    """`GET /nvr-devices/{id}/discovery-runs/{run_id}` — poll javobi.

    Oltita UI holati (UI-SPEC §5.2) AYNAN shu maydonlardan hosil bo'ladi::

        S1  queued
        S2a running + channels_found IS NULL   ("qurilma aniqlanmoqda")
        S2b running + channels_found > 0       ("{n} kanal topildi")
        S3  succeeded
        S4  failed
        S5  180 s ichida terminal holat kelmadi (KLIENT tomonda)

    ⚠ `channels_found` `None` bo'la OLISHI SHART — u S2a va S2b ni
      ajratadigan YAGONA belgi. Nolga tenglashtirish "0 ta kanal
      topildi" degan YOLG'ON natija berardi.
    """

    id: UUID
    nvr_id: UUID
    status: DiscoveryRunStatus
    started_at: datetime
    finished_at: datetime | None
    channels_found: int | None
    channels_added: int | None
    channels_marked_offline: int | None
    error_code: str | None
    error_detail: dict[str, Any] | None
    """Xom diagnostika — FAQAT `ERROR_DETAIL_KEYS` dagi kalitlar (UI-SPEC §7.4).

    ⚠ MASKALASH VA FILTRLASH BACKENDNING KAFOLATI, UI NING ISHI EMAS.
      Ikkita mustaqil qatlam:

        1. `NvrError` KONSTRUKTORI allowlist'dan tashqari kalitni
           `ValueError` bilan rad etadi (`errors.py`);
        2. `nvr_repo.finish_run()` yozishdan OLDIN `mask_sensitive()`
           dan o'tkazadi (§S-7, T-03-28).

      UI noma'lum kalitni RENDER QILMAYDI, lekin u FILTRGA aylanmasligi
      kerak: filtrni klientga topshirish "backend nima yozsa ham
      xavfsiz" degan yolg'on xotirjamlik berardi.
    """


# ---------------------------------------------------------------------------
# Kameralar (03-07, CAM-02/CAM-03) — o'qish yuzasi va jonli ko'rish chiptasi
#
# =============================================================================
# IKKITA MAYDON BU YERDA UMUMAN E'LON QILINMAYDI — VA IKKALASI BOSHQA-BOSHQA
# SABABDAN (UI-SPEC §8.7).
#
#   `stream_name`  go2rtc'dagi oqimning BEVOSITA nishoni. U javobda
#                  ko'ringan zahoti UI'da ko'rsatiladi, nusxa olinadi va
#                  ertami-kechmi `/live/...?src=<nom>` shaklida qo'lda
#                  yig'iladi — ya'ni avtorizatsiya darvozasi (auth_request)
#                  o'z ma'nosini yo'qotadi. Nom FAQAT token javobidagi
#                  opaque URL ichida bo'ladi.
#
#   `rtsp_url`     D-01: RTSP URL UI'da HECH QACHON ko'rsatilmaydi va
#                  HECH QACHON kiritilmaydi. `cameras` jadvalida bunday
#                  ustun ham yo'q (`sbozor_core.models.nvr.Camera`
#                  docstringi) — u sof funksiyada hosil qilinadi va
#                  ilova chegarasidan chiqmaydi.
#
# Ikkalasining ham darvozasi `tests/tenancy/test_camera_route_coverage.py`
# da: u javob modellarini REKURSIV skanerlaydi va bu nomlarni izlaydi,
# ya'ni ular ichma-ich modelga qo'shilganda ham ushlanadi.
# =============================================================================
# ---------------------------------------------------------------------------

_CameraNameStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
"""Kamera nomi — `cameras.name_not_blank` CHECK'ining jufti.

`_NameStr` bilan bir xil shakl, LEKIN alohida alias: `_NameStr` 2-fazaning
zona/toifa nomlariga tegishli va ularning chegarasi bu yerdagidan
mustaqil o'zgarishi mumkin. Umumiy aliasni qayta ishlatish ikki domenning
validatsiyasini jimgina bir-biriga bog'lab qo'yardi.
"""

CAMERA_PAGE_SIZE_MAX = 200
"""`GET /cameras` sahifasining yuqori chegarasi.

`STALL_PAGE_SIZE_MAX` dan KICHIK va bu ataylab: bitta NVR eng ko'pi 32
kanal beradi (UI-SPEC §6.1 — «16/32 kanalli NVR da eng ko'pi 32 qator»),
bir bozorda esa bir-ikkita NVR bo'ladi. Chegara so'ralgan hajmni
o'lchamdan chiqarib yuborishni bloklaydi, mahsulot yo'lini esa umuman
cheklamaydi.
"""


class CameraRead(BaseModel):
    """`GET /cameras` qatori va kamera amallarining javobi.

    Maydonlar UI-SPEC §6.1 dagi qator tuzilishidan KELIB CHIQADI:
    kanal raqami, nom, `name_overridden` bayrog'i (qalam ikonkasi),
    holat badge'i va meta qatori (IP · model · oxirgi ko'rilgan).

    ⚠ `stream_name` VA `rtsp_url` BU YERDA YO'Q — sabab bo'lim boshidagi
      izohda.

    `source_ip` — `cameras.source_ip` (`inet`) ning NORMALLASHTIRILGAN
    ko'rinishi: bazada qiymat `192.168.1.10/32` bo'lib yotadi
    (03-04 `threat_flag: value-format`, `test_source_ip_is_stored_as_a_
    host_prefixed_inet` bilan qulflangan), UI esa prefikssiz manzil
    kutadi. Normalizatsiya `api/v1/cameras.py::_source_ip` da.
    """

    id: UUID
    nvr_id: UUID
    channel_no: int
    name: str
    name_overridden: bool
    status: CameraStatus
    is_archived: bool
    has_substream: bool
    source_ip: str | None
    source_model: str | None
    last_seen_at: datetime


class CameraListResponse(BaseModel):
    """`GET /cameras` — keyset sahifa (`next_cursor` `null` bo'lsa oxirgisi).

    Tartib SERVERDA `channel_no` bo'yicha o'sish tartibida hal qilinadi va
    frontend uni QAYTA SARALAMAYDI (UI-SPEC §6.1: «Saralash boshqaruvi
    YO'Q» — kanal raqami NVR dagi jismoniy uyaga mos keladi va admin uni
    NVR monitoridagi bilan bir xil tartibda ko'radi).
    """

    items: list[CameraRead]
    next_cursor: str | None = None


class CameraQuery(BaseModel):
    """`GET /cameras` query parametrlari (UI-SPEC §6.1 filtrlari).

    `archived` UCH HOLATLI (`None` / `False` / `True`), ikki emas:
    `None` — standart, ya'ni arxivlanganlar YASHIRIN;
    `True` — arxivlanganlar HAM ko'rinadi (checkbox yoqilgan).
    `False` esa aniq «faqat faollar» degani va u standart bilan bir xil
    natija beradi — farq FILTR TAVSIFIDA (`audit_log.new_value.filters`)
    ko'rinadi: «admin checkbox'ni ataylab o'chirdi» va «umuman tegmadi»
    ikki xil hodisa.
    """

    nvr_id: UUID | None = None
    status: CameraStatus | None = None
    archived: bool | None = None
    limit: Annotated[int, Field(ge=1, le=CAMERA_PAGE_SIZE_MAX)] = 100
    cursor: str | None = None


class CameraUpdateRequest(BaseModel):
    """`PATCH /cameras/{camera_id}` tanasi — nom va uning bayrog'i.

    IKKALA MAYDON HAM IXTIYORIY va so'rov `exclude_unset=True` bilan
    o'qiladi: `{"name": "..."}` nomni o'zgartiradi (va `name_overridden`
    ni `true` qiladi), `{"name_overridden": false}` esa «NVR qurilmasidagi
    nomga qaytarish» (UI-SPEC §6.5) amalini bajaradi.

    ⚠ `name_overridden: true` ni YOLG'IZ yuborish MA'NOSIZ va u rad
      etiladi: bayroq nomning HOSILASI — u qo'lda qo'yilgan nom bilan
      BIRGA, bitta operatorda yoziladi (`nvr_repo.rename_camera`
      docstringi: ajratilsa oradagi skan nomni bosib ketardi).

    `is_archived` BU YERDA YO'Q (D-10): arxivlash — ALOHIDA, nomlangan
    amal (`POST /{id}/archive`), umumiy tahrirlashning bir maydoni emas.
    Fe'lning o'zi ham UI-SPEC §9.1 ning darvozasi ostida.
    """

    name: _CameraNameStr | None = None
    name_overridden: bool | None = None


class LiveTokenResponse(BaseModel):
    """`POST /cameras/{camera_id}/live-token` javobi — ULANISH CHIPTASI.

    ⚠ `url` OPAQUE: unda `stream_name` va qisqa muddatli token bor,
      lekin ikkalasi ham UI uchun TUZILMASIZ satr. UI uni `<video>`
      manbaiga beradi, ekranga chiqarmaydi va ulashish tugmasini
      RENDER QILMAYDI (UI-SPEC §8.7).

    ⚠ `expires_in` — TOKENNING muddati, SESSIYANING emas (UI-SPEC §8.3).
      60 soniyalik token 60 soniyalik ko'rish sessiyasini ANGLATMAYDI:
      WebRTC'da signalling bir marta bo'ladi va media UDP orqali
      nginx'dan TASHQARIDA oqadi, HLS'da esa har segment `auth_request`
      dan o'tadi. Sessiya chegarasini (5 daqiqa) UI o'zi qo'yadi, ya'ni
      ikkala transport ham bir xil ishlaydi.

    `transport_hint` — birinchi sinaladigan transport. go2rtc ning
    veb-komponenti baribir avtomatik tanlaydi (WebRTC -> MSE -> HLS);
    maslahat faqat UI ning badge'ini boshlang'ich holatga qo'yadi.
    """

    url: str
    expires_in: int
    transport_hint: str


# ===========================================================================
# 4-FAZA — SNAPSHOT JADVALI, KUN JURNALI VA KADR DETALI (04-09)
# ===========================================================================
#
# ⛔⛔ BU BO'LIMDAGI BIRORTA MODELDA `object_key` MAYDONI YO'Q VA HECH
#     QACHON QO'SHILMAYDI (`04-UI-SPEC.md` §14.3).
#
# Ombor (SeaweedFS) manzili, bucket nomi va obyekt kaliti brauzerga
# HECH QANDAY KO'RINISHDA chiqmaydi — na maydon, na sarlavha, na
# `<details>` bloki sifatida. Kadr FAQAT `GET /snapshots/{id}/image`
# proxysi orqali beriladi.
#
# To'rt sabab (`app/api/v1/snapshots.py` modul docstringida to'liq):
# auditni buzadi, RLS'ni chetlab o'tadi, ombor manzilini oshkor qiladi
# va data-rezidentlik ko'chishini refaktoringga aylantiradi.
#
# Mexanik darvoza: `SnapshotDetailOut.model_fields` da `object_key`
# yo'qligi 04-09 ning qabul mezonida tekshiriladi.
# ===========================================================================

SCHEDULE_NAME_MAX = 40
"""Mavsumiy profil nomining uzunligi (`04-UI-SPEC.md` §4.7)."""

SCHEDULE_TIMES_PAYLOAD_MAX = 100
"""So'rov tanasidagi vaqtlar ro'yxatining SUISTE'MOL shifti.

⚠ BU BIZNES CHEGARASI EMAS. Kunlik slot chegarasi —
  `Settings.snapshot_max_times_per_day` va u `ScheduleRepository.
  _normalize()` da majburlanadi (`04-UI-SPEC.md` §4.6 `[TALAB]`).

Ikkisi ATAYIN ajratilgan: agar DTO ning O'ZI `MAX_TIMES_PER_DAY` bilan
chegaralansa, sozlama PASAYTIRILGANDA (masalan 5 ga) haqiqiy darvoza
UMUMAN ISHGA TUSHMASDI — Pydantic 12 tagacha ruxsat berardi va
sozlamaga tayangan tekshiruv o'lik kod bo'lib qolardi. Bu yerdagi son
esa faqat cheksiz ro'yxat bilan xotira yeyishni to'sadi.
"""

_ScheduleNameStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=SCHEDULE_NAME_MAX),
]

ALERT_DETAIL_KEYS: Final[frozenset[str]] = frozenset(
    {"market_name", "camera_count", "error_code", "slot_time", "stale_hours", "disk_pct"}
)
"""`alert_events.detail` dan UI'ga CHIQADIGAN kalitlar — ALLOWLIST (§6.7).

⚠ ALLOWLIST, DENYLIST EMAS. `detail` — `jsonb` ustuni, ya'ni unga
  kelajakdagi har qanday alert yozuvchisi istalgan kalitni yozishi
  mumkin. Denylist bilan har yangi kalit UI'ga JIMGINA chiqib ketardi
  va D-19 ning «faqat matn va sonlar» qoidasi birinchi e'tiborsizlikda
  buzilardi.

Filtr `AlertEventOut` ning O'ZIDA (`_filter_detail` validatori),
marshrutda EMAS: marshrutda bo'lsa ikkinchi chaqiruvchi uni chetlab
o'tardi.
"""


class ScheduleProfileOut(BaseModel):
    """Bitta mavsumiy profil (`04-UI-SPEC.md` §4.3 ning `profile` obyekti).

    `mode` HISOBLANADI, ustunda saqlanmaydi (`schedule_repo._mode_of`):
    profil faqat davrni biladi, «o'tmishmi yoki kelajakmi» esa BUGUNGA
    nisbatan aniqlanadi. Ustun sifatida saqlansa har kuni yarim tunda
    migratsiya talab qilardi.

    `ends_on` `None` — ochiq oxirli («hozircha amaldagi profil»).
    """

    id: UUID
    name: str
    starts_on: date
    ends_on: date | None
    mode: Literal["past", "active", "future"]


class ScheduleDayOut(BaseModel):
    """Bitta kunning vaqtlari — SANA va VAQTLAR BIRGA.

    Sana ATAYIN shu obyektning ichida (`schedule_repo.DayPlan` bilan bir
    xil qaror): `times` yolg'iz qaytarilsa UI uning QAYSI kunga tegishli
    ekanini o'zi hisoblab olardi va yarim tunda server bilan bir kun
    farq qilardi.
    """

    date: date
    times: list[time]


class ScheduleTodayOut(BaseModel):
    """`GET /snapshot-schedules/today` — BITTA so'rovdagi butun holat.

    =======================================================================
    ⛔ «BUGUN» VA «ERTAGA» BITTA JAVOBDA — VA BU SHAKLNING BUTUN SABABI.

    Ikki so'rovga bo'linsa ular TURLI lahzada olinardi va yarim tun
    atrofida ikkalasi BIR KUNNI ko'rsatib qolardi. Ya'ni D-05 ning yagona
    ko'rsatkichi («bugun 7 slot · ertaga 5 slot») aynan eng muhim
    daqiqada yolg'on bo'lardi — va admin jadvalni tahrirlagandan keyin
    «o'zgarish qachon kuchga kiradi?» savoliga noto'g'ri javob olardi.

    Repozitoriy tomonda bu kafolat BITTA `SELECT` bilan qulflangan
    (`schedule_repo._TODAY_AND_TOMORROW`: ikkala sana ham AYNI `now()` dan).
    =======================================================================

    `profile` `None` bo'lishi mumkin — bozorda birorta profil bo'lmasa.
    Bugun QOPLANMAGAN bo'lsa `profile` eng yaqin profilni beradi va `mode`
    uning qaysi tomonda ekanini aytadi, shunda UI «keyingi jadval {sana}
    da boshlanadi» deya oladi.

    `differs` PROFIL bo'yicha hisoblanadi, vaqtlar ro'yxati bo'yicha emas:
    ikki profilning vaqtlari tasodifan bir xil bo'lishi mumkin, lekin UI
    ogohlantirishi «jadval o'zgaradi» haqida.
    """

    profile: ScheduleProfileOut | None
    today: ScheduleDayOut
    tomorrow: ScheduleDayOut
    differs: bool
    capture_on_closed_days: bool
    uncovered_days: int
    uncovered_horizon_days: int


class ScheduleItemOut(ScheduleProfileOut):
    """Ro'yxat elementi — profil + uning vaqtlari (DL-2, `04-UI-SPEC.md` §4.4).

    `ScheduleProfileOut` dan MEROS OLADI, nusxa emas: `/today` va ro'yxat
    bir xil profil shaklini ko'rsatishi kerak, aks holda UI ikki xil
    obyektga moslashardi.
    """

    times: list[time]


class ScheduleListResponse(BaseModel):
    """Bozorning BARCHA profillari — davr boshlanishi bo'yicha o'sish tartibida.

    Sahifalash YO'Q: mavsumiy profil yiliga bir necha marta qo'shiladi
    («Qishki», «Ramazon»), ya'ni ro'yxat tabiiy ravishda o'nlab qatorda
    qoladi. Kursorli sahifalash bu yerda faqat klient murakkabligini
    oshirardi (`TariffListResponse` bilan bir xil qaror).
    """

    items: list[ScheduleItemOut]


class ScheduleCreateIn(BaseModel):
    """`POST /snapshot-schedules` tanasi — mavsumiy profil (`04-UI-SPEC.md` §4.7).

    ⚠ `market_id` MAYDONI YO'Q (T-02-54 ning literal qoidasi): bozor
      FAQAT `principal.market_id` dan olinadi.

    ⚠ `starts_on` ENG ERTA ERTAGA (D-05). Bugundan boshlanadigan profil
      bugungi rejani IKKI XIL holatda qoldirardi — ertalabki slotlar eski
      jadvaldan, kechkilari yangisidan — va o'sha kunning hisoboti hech
      qaysi profil bilan tushuntirilmasdi. Darvoza SERVERDA
      (`ScheduleRepository.create_seasonal`), bu yerda EMAS: sana
      taqqoslash «bugun» ni bilishni talab qiladi va u bozor
      mintaqasidan keladi.

    `ends_on` `None` — ochiq oxirli profil.
    """

    model_config = ConfigDict(extra="forbid")

    name: _ScheduleNameStr
    starts_on: date
    ends_on: date | None = None
    times: Annotated[list[time], Field(min_length=1, max_length=SCHEDULE_TIMES_PAYLOAD_MAX)]


class ScheduleSlotsIn(BaseModel):
    """`PATCH /snapshot-schedules/{id}` tanasi — FAQAT vaqtlar (`04-UI-SPEC.md` §4.5).

    =======================================================================
    ⛔ `extra="forbid"` — VA U SHU YERDAGI YAGONA MEXANIZM.

    `active` profilda faqat VAQTLAR tahrirlanadi: davrni siljitish
    o'tmishdagi `capture_runs` qatorlarini tushuntirmay qo'yardi («o'sha
    kuni nega faqat 5 kadr bor?» savolining javobi aynan profilning
    davri).

    `extra="forbid"` bo'lmasa `{"times": [...], "starts_on": "2026-01-01"}`
    so'rovi 200 qaytarardi va `starts_on` JIMGINA e'tiborsiz qolardi —
    ya'ni klient «davrni o'zgartirdim» deb o'ylab, hech nima
    o'zgarmagan bo'lardi. Jim e'tiborsizlik — rad etishdan yomonroq.
    =======================================================================
    """

    model_config = ConfigDict(extra="forbid")

    times: Annotated[list[time], Field(min_length=1, max_length=SCHEDULE_TIMES_PAYLOAD_MAX)]


class CaptureRunOut(BaseModel):
    """Kun jurnali matritsasining BITTA hujayrasi (`04-UI-SPEC.md` §6.4).

    ⛔ TO'QQIZTA HUJAYRA HOLATINING HAMMASI SHU YERDAN CHIZILADI va
       ulardan biri — `missed` — YO'QLIK yozuvi: qator MAVJUD, lekin unda
       hech qachon urinish bo'lmagan. Aynan shu holat SC#2 ning o'zagi:
       «bizning tizimimiz ishlamadi» (`missed`) bilan «NVR javob
       bermadi» (`failed`) operatsion jihatdan butunlay boshqa va ular
       BIR XIL ko'rinishi dala diagnostikasini o'ldirardi.

    Ya'ni javob NIMA SODIR BO'LGANINI emas, NIMA SODIR BO'LISHI KERAK
    EDIni ham ifodalaydi — `status` + `quality_verdict` juftligi UI'ga
    to'qqizala holatni ajratish uchun yetadi:

        succeeded + ok      -> olindi       succeeded + dark    -> qorong'i
        succeeded + blank   -> bo'sh        succeeded + corrupt -> buzuq
        failed              -> xato         missed              -> OLINMADI
        pending             -> kutilmoqda   running             -> olinmoqda
        skipped             -> rejaga kirmagan

    `tone` va ikonka BU YERDA YO'Q (D-20 naqshi): API xom faktlarni
    beradi, ko'rinishni frontend hosil qiladi.

    `is_archived` HAM YO'Q — arxivlangan kameraning qatorlari javobga
    umuman kirmaydi va uning O'RNIGA `CaptureDayOut.archived_present`
    bayrog'i turadi.
    """

    run_id: UUID
    camera_id: UUID
    channel_no: int
    camera_name: str
    slot_time: time
    scheduled_at: datetime
    status: str
    attempts: int
    error_code: str | None
    quality_verdict: str | None
    snapshot_id: UUID | None


class DaySummaryOut(BaseModel):
    """Kunning OLTALA hisoblagichi + `planned`/`done` (`04-UI-SPEC.md` §6.3).

    ⛔ NOL QIYMAT — NATIJA, UNING YO'QLIGI EMAS. Barcha maydonlar HAR
       DOIM to'ldiriladi va ixtiyoriy EMAS: `corrupt: 0` bilan «corrupt
       umuman sanalmagan» UI'da bir xil ko'rinishi 3-fazadagi «uch
       hisoblagich» qoidasining aynan buzilishi bo'lardi.

    Repozitoriy tomonda bu `count(*) FILTER (WHERE ...)` bilan
    kafolatlangan (`capture_repo.day_summary`), `GROUP BY` bilan emas.
    """

    planned: int
    done: int
    ok: int
    dark: int
    blank: int
    corrupt: int
    failed: int
    missed: int


class CaptureDayOut(BaseModel):
    """`GET /capture-runs?day=...` — kun jurnali (xulosa + matritsa qatorlari).

    ⚠ `archived_present` — BAYROQ, RO'YXAT EMAS. Arxivlangan kameraning
      qatorlari `rows` da YO'Q (ular xulosa sanog'iga ham kirmaydi:
      `day_summary()` va `list_day()` BIR XIL to'plamni ko'radi), lekin
      ularning MAVJUDLIGI aytiladi — UI «Arxivlangan kameralar hisobga
      kirmaydi» qatorini aynan shundan chizadi (`04-UI-SPEC.md` §6.4).

      Bayroqsiz admin «kecha 25 kamera bor edi, bugun 24» farqini
      ko'rib, uni nosozlik deb o'ylardi.
    """

    day: date
    summary: DaySummaryOut
    rows: list[CaptureRunOut]
    archived_present: bool


class SnapshotDetailOut(BaseModel):
    """Bitta kadrning METAMA'LUMOTI (DL-3, `04-UI-SPEC.md` §6.6).

    =======================================================================
    ⛔ `object_key` MAYDONI BU MODELDA YO'Q VA QO'SHILMAYDI (§14.3).

    Ombor yuzasi foydalanuvchiga HECH QANDAY KO'RINISHDA chiqmaydi.
    Kadr baytlari faqat `GET /snapshots/{id}/image` proxysi orqali
    keladi va o'sha marshrut `audit_read` yozuvini qoldiradi — imzolangan
    havola esa muddati tugagunicha AUDIT YOZUVISIZ ishlab turardi.

    Mexanik darvoza: `"object_key" not in SnapshotDetailOut.model_fields`.
    =======================================================================

    ⚠ UCHALA O'LCHOV HAM (`quality_mean`/`quality_stddev`/
      `quality_saturation`) `None` BO'LISHI MUMKIN va bu AYNAN BITTA
      holatni anglatadi: `corrupt` kadr (`0016` migratsiyasi). Buzuq JPEG
      dekodlanmaydi, ya'ni o'lchovni OLIB BO'LMAYDI. Sentinel `0` bazada
      «o'lchandi va nol chiqdi» ma'nosini berardi va D-15 ning
      `percentile_cont` bilan chegara chiqarish yo'lini jimgina buzardi.

      UI ularni `<details>` «Texnik tafsilot» blokida FAQAT qiymat
      mavjud bo'lganda chizadi.
    """

    id: UUID
    camera_id: UUID
    business_date: date
    slot_time: time
    scheduled_at: datetime
    captured_at: datetime
    size_bytes: int
    width: int | None
    height: int | None
    quality_verdict: str
    light_mode: str
    capture_method: str
    storage_tier: str
    is_billable: bool
    quality_mean: float | None
    quality_stddev: float | None
    quality_saturation: float | None
    quality_thresholds_version: int


class AlertEventOut(BaseModel):
    """Ochiq yoki yopilgan ogohlantirish (`04-UI-SPEC.md` §6.7, D-22).

    ⛔ `snapshot_id` VA RASM HAVOLASI BU YERDA YO'Q (D-19) — jadvalda ham
       bunday ustun yo'q. Dalil-kadrlar bozor tashrifchilarining shaxsiy
       ma'lumoti, Telegram serverlari esa loyiha zimmasiga olgan O'zR
       data-rezidentlik chegarasidan tashqarida.

    ⚠ `notified_at` `None` BO'LSA HAM QAYTARILADI va UI uni YASHIRMAYDI:
      «Telegram xabari yuborilmadi» qatori aynan shu joyda tug'iladigan
      «alert bor deb o'ylash» yolg'onining oldini oladi.

    `occurrences > 1` — bo'g'ilgan takrorlar soni. D-22 ning guruhlashi
    ma'lumot YO'QOTMAYDI: son qaytadi va UI «so'nggi soatda yana {n}
    marta» deb chizadi.
    """

    id: UUID
    alert_key: str
    severity: str
    subject_id: UUID | None
    first_seen_at: datetime
    last_seen_at: datetime
    occurrences: int
    notified_at: datetime | None
    resolved_at: datetime | None
    detail: dict[str, Any]

    @field_validator("detail", mode="before")
    @classmethod
    def _filter_detail(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        """`ALERT_DETAIL_KEYS` dan tashqaridagi kalitlarni TASHLAB YUBORADI.

        ⚠ FILTR MODELDA, MARSHRUTDA EMAS. Marshrutda bo'lsa ikkinchi
          chaqiruvchi (masalan kelajakdagi dayjest endpointi) uni chetlab
          o'tardi va `detail` ning yangi kaliti UI'ga jimgina chiqib
          ketardi.

        `None` -> bo'sh `dict`: `detail` javobda HAR DOIM obyekt bo'ladi
        va UI `null` bilan `{}` ni ajratishga majbur emas.
        """
        if not value:
            return {}
        return {key: item for key, item in value.items() if key in ALERT_DETAIL_KEYS}


class AlertListResponse(BaseModel):
    """`GET /alerts?closed=0|1` javobi — `last_seen_at` bo'yicha kamayish tartibida.

    ⛔ YOPISH/BOSTIRISH MARSHRUTI YO'Q (`04-UI-SPEC.md` §6.7): ogohlantirishni
       faqat TIKLANISH yopadi (`resolved_at` ni fon jarayoni qo'yadi).
       Qo'lda yopish tugmasi adminga muammoni KO'RMASDAN yashirish
       imkonini berardi — va aynan shu bosqichda «hammasi yaxshi»
       ko'rinishi mahsulotning butun mazmunini yo'q qilardi.
    """

    items: list[AlertEventOut]


# ---------------------------------------------------------------------------
# 5-FAZA — KAMERA ZONALARI (05-06, AI-01, D-07/D-22)
#
# ⚠ `market_id` MAYDONI BU BO'LIMDA UMUMAN E'LON QILINMAGAN (T-05-24).
#   `zones.py` / `stalls.py` bo'limlaridagi bilan AYNAN bir xil qaror:
#   bozor identifikatori faqat `_market_id(principal)` dan keladi. Maydon
#   e'lon qilinmagani uchun uni «e'tiborsiz qoldirish» kodi ham kerak
#   emas — Pydantic uni tashlab yuboradi va router uni HECH QACHON
#   ko'rmaydi. Bu «filtrlaymiz» dan kuchliroq kafolat: filtrni unutish
#   mumkin, mavjud bo'lmagan maydonni esa yo'q.
#
# ⚠ `version` HAM YO'Q va sabab boshqa: versiyani SERVER hisoblaydi
#   (`camera_zone_repo.replace_for_camera()`). Klientga versiya
#   yozdirish D-07 ning butun kafolatini klientning to'g'ri ishlashiga
#   bog'lab qo'yardi — eski qator ustiga yozish bir satrlik xato bo'lardi.
# ---------------------------------------------------------------------------


class CameraZoneItem(BaseModel):
    """Bitta zona — `polygon` NORMALANGAN (0..1), piksel EMAS (D-07).

    `stall_code` javobda ATAYIN bor: UUID admin uchun hech nima
    anglatmaydi, u (B) ro'yxatida «14-A» ni ko'radi (UI-SPEC §6.4).
    Kodni bu yerga qo'shmaslik frontendni har zona uchun alohida
    so'rovga majburlardi.

    `needs_review` — HOSILA, saqlanadigan ustun EMAS (§6.8): u zonaning
    `source_width`/`source_height` i bilan JORIY kadr o'lchamini
    solishtirishdan chiqadi. Ustun sifatida saqlansa kamera ruxsati
    o'zgargan kuni u eskirib qolardi va bayroq JIMGINA yolg'on bo'lardi.

    ⛔ Bayroq zonani RAD ETMAYDI va AVTOMATIK TO'G'RILASH ham yo'q
       (§6.8): cho'zilganmi yoki kesilganmi — bilib bo'lmaydi va
       noto'g'ri tuzatish jimgina noto'g'ri hisob berardi.
    """

    id: UUID
    camera_id: UUID
    stall_id: UUID
    stall_code: str
    version: int
    polygon: list[tuple[float, float]]
    source_width: int
    source_height: int
    needs_review: bool


class CameraZoneListResponse(BaseModel):
    """`GET /camera-zones?camera_id=…` javobi.

    SAHIFALASH YO'Q: bitta kameradagi zonalar soni `ZONE_MAX_PER_CAMERA`
    (60) bilan SERVERDA cheklangan, ya'ni javob hech qachon o'smaydi va
    kursor mexanikasi hech qanday muammoni hal qilmasdi
    (`ZoneListResponse` da o'rnatilgan qoida).

    `frame_width`/`frame_height` — poligonlar ustiga chiziladigan JORIY
    kadrning o'lchami. Ular javobda ATAYIN bor: `needs_review` bayrog'i
    aynan shu ikki songa tayanadi va ularni ko'rsatmaslik adminni
    «nega tekshirish kerak?» savoliga javobsiz qoldirardi.

    ⚠ `None` — kamerada HALI YAROQLI KADR YO'Q. Bu NOSOZLIK EMAS: yangi
      ulangan kamera birinchi slotgacha aynan shu holatda bo'ladi.
      O'shanda `needs_review` HAR ZONADA `false` — solishtiradigan
      narsa yo'q, ya'ni «farq qiladi» degan da'vo asossiz bo'lardi.
    """

    items: list[CameraZoneItem]
    frame_width: int | None = None
    frame_height: int | None = None


class CameraZoneWrite(BaseModel):
    """`PUT /camera-zones` tanasidagi BITTA zona.

    `polygon` — `list[tuple[float, float]]`, ya'ni har element AYNAN ikki
    sonli. Erkin `list[list[float]]` uch komponentli «nuqta» ni ham
    qabul qilardi va u `supervision.PolygonZone` ga yetib borib, u yerda
    tushunarsiz xato berardi.

    ⚠ CHEGARA TEKSHIRUVI (`min_length`) BU YERDA ATAYIN YO'Q. Pydantic
      uni 422 bilan rad etardi, 422 esa `detail` da xato KODINI emas,
      Pydantic ning ichki tuzilmasini qaytaradi — ya'ni frontend
      `zone_polygon_too_few_points` matnini KO'RSATA OLMASDI va admin
      «Kutilmagan xato» ni o'qirdi. Poligon qoidalari `validate_polygon()`
      da tekshiriladi va 422 emas, NOMLANGAN kod bilan rad etiladi.
    """

    stall_id: UUID
    polygon: list[tuple[float, float]]
    source_width: Annotated[int, Field(gt=0)]
    source_height: Annotated[int, Field(gt=0)]


class CameraZoneRequest(BaseModel):
    """`PUT /camera-zones?camera_id=…` tanasi — kameraning TO'LIQ holati.

    ⛔ QISMAN SAQLASH YO'Q (UI-SPEC §6.6): ro'yxat butun kameraning
       yangi holati va unda YO'Q faol zona eskirgan deb belgilanadi.
       Yarim saqlangan kamera bandlik hisobini JIMGINA buzardi — bir
       qism rasta yangi kontur bilan, qolgani eskisi bilan o'lchanardi.

    ⚠ BO'SH RO'YXAT QONUNIY va u «bu kameradagi hamma zonani olib
      tashla» degani. Rad etish adminni zonalarni bittalab o'chirishga
      majburlardi va oxirgisida baribir shu holatga kelardi.

    ⚠ `camera_id` TANADA EMAS, QUERY PARAMETRIDA: u RESURSNI aniqlaydi,
      ya'ni yo'lning bir qismi. Tanada bo'lganda bitta `PUT` ikki xil
      kameraga yozish niyatini ifodalay olardi (query'da bittasi,
      tanada boshqasi) va qaysi biri ustun ekani kodni o'qimasdan
      ko'rinmasdi.
    """

    zones: list[CameraZoneWrite]


class ZoneCoverageResponse(BaseModel):
    """`GET /camera-zones/coverage` — D-22 uchligi (UI-SPEC §6.9).

    ⛔ `uncovered` MAYDONI «bo'sh» DEB NOMLANMAYDI va bu farq
       mahsulotning yuragi: qamrovsiz rasta bo'sh EMAS — u haqida
       MA'LUMOT YO'Q. «Bo'sh» deb sanalgan qamrovsiz rasta hisobotda
       «to'lovsiz emas» bo'lib ko'rinardi, ya'ni tizim o'zi KO'RMAGAN
       narsani «joyida» deb e'lon qilardi — aynan shu mahsulot fosh
       qilishi kerak bo'lgan holat.

    ⚠ UCHALA SON HAM HAR DOIM QAYTADI, nol bo'lganda ham. Ixtiyoriy
      qilinsa birorta zona chizilmagan bozorda karta UMUMAN chiqmasdi
      va admin «hammasi joyida» deb o'qirdi.
    """

    covered: int
    uncovered: int
    cameras_without_zones: int


# ---------------------------------------------------------------------------
# 5-FAZA — NAZORATCHI NAVBATI (05-10, AI-03, D-13/D-18)
#
# ⛔⛔ BU BO'LIMDA TIZIMNING JAVOBI YO'Q — VA U «YASHIRILGAN» EMAS,
#     E'LON QILINMAGAN (D-17.2, T-05-45).
#
#   `verdict`, `confidence`, `model_version`, `thresholds_version`,
#   `purpose`, `queue_kind`, `shown_ai_verdict` — bu maydonlarning
#   BIRORTASI HAM `ReviewItemResponse` da yo'q. `None` qilib yuborish
#   YETARLI EMAS bo'lardi: kalitning O'ZI javobda turgan bo'lsa, uni
#   to'ldirish bir satrlik o'zgarish bo'lardi.
#
#   ⚠ SABAB AI-03 TALAB QILGANIDAN QATTIQROQ VA U O'LCHANGAN: band
#   navbatga tushgan bo'lsa tizim ALLAQACHON ishonchsiz, ya'ni uning
#   moyilligi deyarli MA'LUMOT TASHIMAYDI, lekin TO'LIQ ankorlash
#   kuchiga ega (05-RESEARCH §C.8 — mustaqil qarorlarning ~7% i
#   noto'g'ri maslahatdan teskarisiga o'zgargan). Yashirishning narxi
#   NOL, foydasi — TOZA YORLIQLAR.
#
# ⛔ `market_id` HAM, `shown_ai_verdict` HAM, `decision_ms` HAM
#   `AnswerRequest` DA E'LON QILINMAGAN (T-05-24, T-05-44, T-05-46).
#   Birinchisi — tenant chegarasi; ikkinchisi klient YOLG'ON gapira
#   oladigan yagona maydon bo'lardi va DB `CHECK` i aldangan bo'lardi;
#   uchinchisi esa nazoratchi «shoshib bosish» o'lchovini o'zi yozib
#   qo'ya olardi.
#
# ⚠ `extra="forbid"` ATAYIN QO'YILMAGAN. U noma'lum maydonni 422 bilan
#   RAD ETARDI — ya'ni eskirgan klient nazoratchini javob BERISHDAN
#   to'sib qo'yardi. Javob — mahsulot, `decision_ms` esa DIAGNOSTIKA:
#   nosozlikning narxi ikkalasida bir xil emas. Pydantic'ning standarti
#   (`extra="ignore"`) qiymatni JIMGINA tashlaydi va uning shu tarzda
#   tashlanishi test bilan o'lchanadi (`ScheduleCreateIn` dagi
#   `extra="forbid"` boshqa sinf: u USTA formasining kontrakti).
# ---------------------------------------------------------------------------


class ReviewItemResponse(BaseModel):
    """`GET /review/uncertain/next` — nazoratchi ko'radigan BITTA band.

    Maydonlarning har biri ekranda BOR (UI-SPEC §7.3): dalil kadri,
    rasta raqami va hududi, sana/vaqt/kanal, kontur va «sotuvchi
    biriktirilgan» qatori. Ortiqcha maydon YO'Q — bu bo'lim izohidagi
    sabab.

    `snapshot_id` — kadr HAVOLASINING manbai. Klient uni
    `GET /api/v1/snapshots/{id}/image` proxysiga aylantiradi; imzolangan
    (presigned) URL BERILMAYDI va so'ralmaydi (UI-SPEC §14.2, T-05-47).

    `polygon` NORMALANGAN (0..1): klient konturni kadr ustiga SVG bilan
    chizadi, ya'ni AYNI kadr Y-2, Y-3 va Y-4 da bitta keshdan keladi.
    """

    assignment_id: UUID
    snapshot_id: UUID
    stall_id: UUID
    stall_code: str
    zone_name: str
    camera_name: str
    channel_no: int
    business_date: date
    slot_time: time
    polygon: list[tuple[float, float]]
    has_active_vendor: bool


class BlindItemResponse(BaseModel):
    """`GET /review/blind/next` — KO'R audit bandi (AI-04, D-17.2).

    =======================================================================
    ⛔⛔ SAKKIZ MAYDONNING BIRORTASI HAM E'LON QILINMAGAN VA BU
        «YASHIRISH» EMAS.

        verdict · confidence · model_version · thresholds_version
        effective_verdict · resolution_source · shown_ai_verdict · purpose

    `None` qilib yuborish YETARLI EMAS bo'lardi: kalit javobda tursa uni
    to'ldirish BIR SATRLIK o'zgarish bo'lardi. Sxemadan YASHIRISH
    (`include_in_schema=False`) esa umuman himoya emas — u faqat
    hujjatni o'zgartiradi, baytlarni emas.

    ⚠ MARSHRUTNING O'ZI SXEMADA KO'RINADI VA BU ATAYIN: himoya
      payloadning SHAKLIDA, hujjatning yo'qligida emas. `test_the_blind_
      route_is_visible_in_the_schema` buni qulflaydi — yashirish yo'liga
      o'tish darvozani qizartiradi.
    =======================================================================

    ⛔ `purpose` HAM RO'YXATDA (D-14). `eval`/`train` belgisi ko'rinsa,
       «bu baholash uchun ekan» degan E'TIBOR FARQI tug'ilardi va 70/30
       bo'linishining butun ma'nosi yo'qolardi.

    ⛔ `has_active_vendor` BU YERDA YO'Q — VA U `ReviewItemResponse` DA BOR.

       Farq ataylab va u DEVIATSIYA sifatida yozilgan. Noaniq navbatda
       o'sha qator MOTIVATSIYA: band ustuvorlik bo'yicha tanlangan, ya'ni
       «bu qarorning oqibati bor» degan xabar HALOL. Ko'r auditda esa
       band TASODIFIY tanlangan va o'sha qator namunaning bir qismiga
       ko'proq, qolganiga kamroq e'tibor beriladigan holat yaratardi —
       ya'ni DIQQAT namuna bo'ylab notekis taqsimlanardi. Xolis
       namunadagi notekis diqqat — o'lchov asbobining O'ZIDAGI og'ish.

    ⛔ TUR RAQAMI, URUG', TAKRORIYLIK BELGISI VA KUNLIK HISOBLAGICH HAM
       YO'Q (UI-SPEC §7.5): ular Y-4 hisobotining yuzasi.
    """

    assignment_id: UUID
    snapshot_id: UUID
    stall_id: UUID
    stall_code: str
    zone_name: str
    camera_name: str
    channel_no: int
    business_date: date
    slot_time: time
    polygon: list[tuple[float, float]]


class AnswerRequest(BaseModel):
    """`POST /review/{id}/answer` tanasi — AYNAN BITTA maydon.

    ⛔ MASSIV QABUL QILADIGAN VARIANTI YO'Q va bo'lmaydi (D-18). Bitta
       so'rov = bitta qaror; buni `tests/integration/test_uncertain_
       queue.py::test_no_bulk_approve_endpoint` OpenAPI sxemasidan
       skanerlab tasdiqlaydi.

    `human_verdict` `OccupancyVerdict` DAN HOSILA, literal ro'yxat EMAS:
    domen enum'da yashaydi va `zone_reviews.human_verdict` ning `CHECK`
    i ham o'sha enum'dan chiqadi (§S-5).

    ⚠ `uncertain` QIYMATI QONUNIY va u «Aniq ayta olmayman» tugmasi
      (UI-SPEC §7.3). Uni rad etish nazoratchini TAXMIN QILISHGA
      majburlardi va xolis o'lchovga ataylab shovqin qo'shardi
      (`HUMAN_VERDICT_CHECK` docstringi).
    """

    human_verdict: OccupancyVerdict


class AnswerResponse(BaseModel):
    """Javob YOZILGANDAN KEYINGI oshkor ma'lumot (UI-SPEC §7.7).

    ⛔ BU MA'LUMOT BIRORTA `GET` MARSHRUTIDAN OLINMAYDI. U FAQAT shu
       `POST` ning javobida mavjud — oldindan yuklab qo'yish (prefetch)
       yo'li shu bilan yopiladi. Klient uni `useMutation` ning `data`
       sidan oladi, `useQuery` dan EMAS.

    ⛔ MAYDON NOMLARI ATAYIN `verdict`/`ai_verdict`/`confidence` EMAS.
       Sabab MEXANIK: G-12 darvozasi `components/blind-audit/**` da o'sha
       nomlarning UMUMAN uchramasligini talab qiladi (UI-SPEC §14.3),
       ya'ni oshkor panelining tipi ularni olib kirsa darvoza O'ZINI
       O'ZI qizartirardi va yagona «tuzatish» yo'li darvozani
       BO'SHATISH bo'lardi.

    `locked` — «bu javobni endi o'zgartirib bo'lmaydi». Bezak emas:
    qiymat IKKI strukturaviy mexanizmdan chiqadi
    (`UNIQUE (review_assignment_id)` + `BEFORE UPDATE` qo'riqchisi) va
    ularning ikkalasi ham test bilan o'lchanadi.

    ⚠ `confidence` BU YERDA HAM YO'Q (UI-SPEC §7.5): u nazoratchi uchun
      ma'nosiz («0,42 nimani anglatadi?») va keyingi bandga ankor
      bo'lardi.
    """

    system_answer: OccupancyVerdict
    human_answer: OccupancyVerdict
    matched: bool
    locked: bool


class QueueBudget(BaseModel):
    """Bitta navbatning kunlik hisoblagichi (UI-SPEC §7.2 dagi «12 / 50»).

    ⚠ UCHALA SON HAM QAYTADI. `remaining` ni klientga hisoblatish ikki
      joyda ikki formula tug'dirardi (`max(0, budget - answered)` yoki
      shunchaki ayirma) va nazoratchi MANFIY qoldiqni ko'rishi mumkin
      edi — byudjet sozlamasi kun o'rtasida pasaytirilsa aynan shunday
      bo'lardi.
    """

    answered: int
    budget: int
    remaining: int


class ReviewBudgetResponse(BaseModel):
    """`GET /review/budget?day=…` — IKKALA navbat uchun (UI-SPEC §7.2).

    ⚠ BITTA SO'ROVDA IKKALASI: `/review` uyi ikkala kartani ham BIR
      VAQTDA ko'rsatadi (byudjeti tugagan kartani ham). Ikki alohida
      so'rov ikkita yuklanish holatini yaratardi va kartalar navbatma-
      navbat «sakrab» chiqardi.

    ⛔ `blind_audit` HISOBLAGICHI BU YERDA, LEKIN TORTISH 05-11 DA.
       Ya'ni bugun bu son `0 / 30` bo'lib turishi MUMKIN va bu NOSOZLIK
       EMAS — namuna hali tortilmagan bo'lsa javob ham yo'q.
    """

    day: date
    uncertain: QueueBudget
    blind_audit: QueueBudget


# ===========================================================================
# 05-12 — BANDLIK HISOBOTI (AI-04, AI-05, AI-06)
#
# ⛔⛔ BU YUZA `REPORT_VIEW` OSTIDA VA NAZORATCHIDA BU HUQUQ YO'Q.
#
# Nazoratchi o'z aniqligini KO'RMAYDI (T-05-58): ko'rsa u raqamni
# yaxshilashga urinardi va o'lchov o'zi o'lchayotgan narsani o'zgartirardi
# — «tez qaror» sanog'i esa aynan shu urinishning izi bo'lib qolardi.
#
# ⛔ «NAMUNANI QAYTA TORTISH» MARSHRUTI YO'Q (D-17.1) va uning yo'qligi
#    05-11 ning OpenAPI skani bilan o'lchanadi.
# ===========================================================================


class ProportionIntervalOut(BaseModel):
    """Nisbat va uning Wilson oralig'i — UCHALA maydon ham `null` bo'lishi mumkin.

    ⛔ MAYDON JAVOBDAN CHIQIB KETMAYDI: `null` «hali o'lchanmagan»
       degani, maydonning YO'QLIGI esa klientda «eski server» yoki
       «xato» deb o'qilardi.
    """

    point: float | None
    lower: float | None
    upper: float | None


class ConfusionMatrixOut(BaseModel):
    """2x2 chalkashlik matritsasi — «musbat» AYNAN `occupied`.

    ⛔ TO'RT KATAK HAM XOM SON. Foizga aylantirish SERVERDA
       qilinmaydi-yu, bu yerda ham qilinmaydi: `n < 20` da foiz UMUMAN
       chizilmaydi va xom sonlar HAR DOIM ko'rinadi (§11.5).
    """

    true_occupied: int
    """Tizim band dedi, nazoratchi ham band dedi."""
    false_occupied: int
    """⚠ Tizim band dedi, nazoratchi BO'SH dedi -> SOTUVCHI BILAN NIZO xavfi."""
    false_empty: int
    """⚠ Tizim bo'sh dedi, nazoratchi BAND dedi -> YIG'ILMAGAN PATTA."""
    true_empty: int


class OccupancyAccuracyResponse(BaseModel):
    """`GET /occupancy/accuracy` — matritsa, uch oraliq va BAZAVIY ULUSH.

    =======================================================================
    ⛔ «ANIQLIK» YOLG'IZ QAYTARILMAYDI. `base_rate` — MAJBURIY maydon:
       rastalarning 90 % i band bo'lsa, «har doim band» deydigan soxta
       model 90 % oladi va usiz bu ko'rinmasdi (§C.8.4).

    ⛔ `measured is False` bo'lganda BARCHA foiz maydonlari `null`, xom
       sonlar esa QAYTADI: «hisobot yo'q» bilan «hali o'lchanmadi» bir
       xil ko'rinmasligi kerak.

    ⛔ NAZORATCHINING ICHKI MOSLIGI (D-16) BU YERDA YO'Q — na son, na
       maydon sifatida. 05-11 o'lchadi: takroriy band bugungi sxemada
       ifodalab bo'lmaydi, ya'ni MEXANIZM QURILMAGAN. Uni `100 %` qilib
       ko'rsatish o'lchanmagan miqdorni o'lchangan qilib ko'rsatardi
       (T-05-04), bo'sh maydon qoldirish esa keyingi ijrochini unga son
       yozishga undardi.
    =======================================================================
    """

    from_date: date
    to_date: date
    drawn: int
    """Namunaga tushgan `eval` bandlari — JAVOBSIZLARI BILAN."""
    answered: int
    unanswered: int
    """⛔ JAVOBSIZ BANDLAR NAMUNADAN CHIQMAYDI (§C.8, 4-dushman)."""
    dont_know: int
    """«Aniq ayta olmadi» — matritsadan TASHQARIDA (O-06)."""
    matrix: ConfusionMatrixOut
    n: int
    """Matritsaga tushgan javoblar soni — `drawn` dan KICHIK bo'lishi normal."""
    measured: bool
    min_sample: int
    """Foiz chizilishi uchun zarur eng kichik `n` — klient uni O'ZI YOZMAYDI."""
    base_rate: float | None
    correct: ProportionIntervalOut
    false_occupied: ProportionIntervalOut
    false_empty: ProportionIntervalOut


class OccupancyStallItem(BaseModel):
    """Rastalar ro'yxatining bitta qatori (UI-SPEC §11.7).

    ⛔ PATTA/SUMMA YO'Q — 6-faza (§16.1).
    """

    stall_id: UUID
    stall_code: str
    zone_name: str
    status: str
    """`occupied` / `empty` / `default_empty` / `no_coverage`."""
    slots: int
    occupied_slots: int
    human_confirmed: bool


class OccupancyDayResponse(BaseModel):
    """`GET /occupancy?day=…` — BESH hisoblagich va rastalar ro'yxati.

    ⛔ TO'RTTA BO'LAK O'ZARO INKOR VA ULARNING YIG'INDISI `stalls` GA
       TENG; `human_confirmed` — KESISHUVCHI o'lcham va yig'indiga
       KIRMAYDI (§11.4).

    ⛔ BESHALASI HAM NOL BO'LGANDA HAM QAYTADI: nol — NATIJA, uning
       yo'qligi emas.
    """

    day: date
    stalls: int
    occupied: int
    empty: int
    default_empty: int
    """⛔ `empty` GA QO'SHILMAYDI (D-19) — «nazoratchi ulgurmadi» signali."""
    no_coverage: int
    """⛔ `empty` GA QO'SHILMAYDI (D-22) — bu rasta haqida ma'lumot YO'Q."""
    human_confirmed: int
    items: list[OccupancyStallItem]


class OccupancyRoundResponse(BaseModel):
    """`GET /occupancy/round?day=…` — o'lchovning O'ZI haqidagi ma'lumot (§11.6).

    ⛔ URUG' QAYTARILMAYDI: u foydalanuvchi uchun ma'nosiz va uni
       ko'rsatish «tanlash mumkin» degan taassurot berardi (D-17.1).

    ⛔ `drawn` TORTILGANLAR SONI (`round_no`/`drawn_at`/`frame_size`
       bilan birga) — namuna QANDAY qurilganini ko'rsatadi.

    ⚠ `drawn = false` bo'lganda («tur tortilmagan») qolgan maydonlar
      `null`. Bu «hammasi bajarildi» DAN ATAYIN ajratilgan: asbobning
      YO'QLIGI muvaffaqiyat bo'lib ko'rinmasligi kerak
      (`review_repo._HAS_ANY_ROUND` bilan bir xil qaror).
    """

    day: date
    drawn: bool
    round_no: int | None
    drawn_at: datetime | None
    frame_size: int | None
    sample_size: int | None
    answered: int | None
    unanswered: int | None
    """⛔ NOL BO'LGANDA HAM QAYTADI (§11.6)."""
    dont_know: int | None
    fast_decisions: int | None
    """«2 soniyadan tez» javoblar. ⚠ `decision_ms` `NULL` bo'lganlar bu
    sanoqqa KIRMAYDI: `NULL` — o'lchovning YO'QLIGI, «tez» EMAS."""


# ---------------------------------------------------------------------------
# 06-08: BILLING VA KASSIRNING O'QISH YUZASI (BILL-02…BILL-05)
#
# ⛔⛔ BU BO'LIMNING ENG QIMMAT QARORI — MAYDONNI E'LON QILMASLIK.
#
# Naqsh yuqoridagi `BlindItemResponse` DAN VERBATIM olingan va uning
# uch bandi shu yerda ham to'liq kuchda:
#
#   * `None` qilib yuborish YETARLI EMAS — kalit javobda tursa uni
#     to'ldirish BIR SATRLIK o'zgarish bo'lardi;
#   * `include_in_schema=False` UMUMAN HIMOYA EMAS — u hujjatni
#     o'zgartiradi, BAYTLARNI emas;
#   * marshrutning O'ZI sxemada ko'rinadi va bu ATAYIN: himoya
#     payloadning SHAKLIDA.
#
# ⛔ HAR MODELDA `extra="forbid"` (V5 Input Validation): server tomonda
#    ham qattiqlik. Bu javob modellari uchun ham ma'noli — `model_
#    construct()` yoki noto'g'ri `**kwargs` bilan qo'shilgan maydon
#    JIMGINA o'tib ketmasin.
# ---------------------------------------------------------------------------

AmountUnavailableReason = Literal[
    "market_closed",
    "tariff_missing",
    "fair_stall",
    # 2026-08-25 (buyurtmachi): yopiq/ta'mirdagi rastadan patta olinmaydi.
    "stall_closed",
    "stall_maintenance",
]
"""`amount_soum is None` bo'lganda uning NOMLANGAN sababi (UI-SPEC §9.2).

⚠ Literal SATRLARI shu yerda YOZILGAN, lekin ular REYESTRDAN AJRALIB
  KETA OLMAYDI: quyidagi import-vaqti darvozasi ikki to'plamni
  solishtiradi. Literal'ni `AMOUNT_UNAVAILABLE_REASONS` dan DINAMIK
  qurish mumkin emas (`Literal[*frozenset]` statik tekshiruvchi uchun
  tip emas), ya'ni yagona halol yechim — nusxani MEXANIK qulflash.

⛔ NEGA UMUMAN LITERAL: klient `z.enum([...])` bilan o'qiydi va OpenAPI
   sxemasida bu maydon ENUM bo'lib ko'rinishi kerak. `str` tipi uni
   ochiq matnga aylantirardi va yopiq to'plam da'vosi kontraktdan
   yo'qolardi.
"""

if set(get_args(AmountUnavailableReason)) != AMOUNT_UNAVAILABLE_REASONS:
    raise AssertionError(  # pragma: no cover - import-vaqti darvozasi
        "`AmountUnavailableReason` va `billing_errors.AMOUNT_UNAVAILABLE_REASONS` "
        f"ajralib ketdi: {sorted(get_args(AmountUnavailableReason))} != "
        f"{sorted(AMOUNT_UNAVAILABLE_REASONS)}. Yangi sabab IKKALA joyda ham "
        "e'lon qilinishi SHART (D-32) — aks holda server reyestrda bo'lmagan "
        "qiymat qaytarib, klient sxemasi PARSE PAYTIDA yiqilardi."
    )


class PendingStallResponse(BaseModel):
    """`GET /billing/pending?stall_code=…` — BITTA rastaning proyeksiyasi (BILL-05).

    =======================================================================
    ⛔⛔ KALITLAR TO'PLAMI AYNAN TO'QQIZTA (UI-SPEC §9.2) VA QUYIDAGILAR
        E'LON QILINMAGAN — YASHIRILGAN EMAS:

        charge_id                        — D-17;
        tariff_id · category_id · valid_from — D-20;
        vendor_id · vendor_name · phone  — C-10 + §5.5;
        occupied_slots · is_billable     — §9.1 (C-8);
        balance · balance_soum           — BILL-03.

    `charge_id` YO'Q, chunki **proyeksiya hisob EMAS**: hisob D+1 04:10
    da tug'iladi (C-3), ya'ni bugungi kun uchun hisob identifikatori
    MAVJUD EMAS. Uni `null` bilan e'lon qilish «hisob bor, faqat hozir
    bo'sh» degan yolg'on aytardi va ekran uni kvitansiya deb chizardi.

    `tariff_id`/`category_id`/`valid_from` YO'Q — D-20 ning KUCHLI
    shakli: klientda tarifning KIRISH MA'LUMOTI yo'q, ya'ni summani
    qayta hisoblash *taqiqlanmaydi* — U IMKONSIZ. `total_due_soum` ham
    shuning uchun SERVERDA (§9.6): aks holda `[Qarzni ham olish]`
    tugmasi D-20 ni BITTA QO'SHISH AMALI bilan buzardi.

    `vendor_id`/`vendor_name`/`phone` YO'Q — kassirda `vendor_view`
    yo'q va ism marshrut darajasida emas, HUQUQ darajasida yo'q (§5.5).
    Bu maydonlardan birortasini qo'shish `PERSONAL_ROUTES` ni
    o'stirardi va moliyaviy yuzaga shaxsiy-ma'lumot qo'riqchisini
    o'rnatardi (C-10). ⛔ Nom bilan aylanib o'tish (`vendor_label`,
    `payer`, `who`) ham TAQIQLANADI.

    `occupied_slots`/`is_billable` YO'Q — bugungi kun uchun
    `stall_slot_occupancy` BO'SH (C-8), ya'ni «bugun band» BILINMAYDI
    va ko'rsatilgan har qanday sanoq SOXTA KO'RSATKICH bo'lardi.

    `balance`/`balance_soum` YO'Q — saqlangan balans yo'q (BILL-03),
    NOMI ham yo'q: nom bir kun ustunga aylanardi.
    =======================================================================

    ⚠ To'plam tengligi bilan o'lchanadi (D-31), inkor tasdiq bilan EMAS:
      `not in` faqat AYNAN o'sha nomni ushlaydi va `chargeId` jimgina
      o'tib ketardi.
    """

    model_config = ConfigDict(extra="forbid")

    stall_code: str
    """⛔ Kassir yuzasidagi YAGONA identifikator (§5.5)."""
    service_date: date
    """«Qaysi kun uchun» — C-4 ning javobi."""
    market_open: bool
    """`market_is_open(market, as_of)` natijasi — ⛔ xato kodidan HOSILA emas."""
    amount_soum: int | None
    """Bugungi TO'LIQ patta: rasta puli + xizmat haqi (tarozi).

    `null` — FAQAT nomlangan sabab bilan.
    """
    stall_amount_soum: int | None
    """Rasta pulining O'ZI — xizmat haqi belgisi olib tashlanganda to'lanadi.

    ⛔ NEGA SERVERDAN: `amount_soum − fee_amount_soum` ni klientda
       hisoblash PULNI KLIENTDA hisoblash bo'lardi. Bu javobning butun
       falsafasi shunga qarshi — yuqoridagi blok `tariff_id` ni aynan
       shu sababdan chiqarib tashlagan (D-20 ning kuchli shakli: qayta
       hisoblash *taqiqlanmagan*, IMKONSIZ).

    ⚠ Bu summa ham `payment_quote_set()` ning TAKLIFLAR to'plamida —
      ya'ni u bilan to'lash sabab kodi TALAB QILMAYDI (06-09 ning
      5-qadami). Xizmat haqini olib tashlash NORMAL yo'l, istisno emas.
    """
    fee_amount_soum: int | None
    """Xizmat haqi ulushi. `0` — bozorda belgilanmagan; `null` — summa yo'q.

    ⛔ IKKI QIYMAT ARALASHTIRILMAYDI: `0` da belgi UMUMAN chizilmaydi
       («bu bozorda tarozi yo'q»), `null` da esa summaning o'zi yo'q
       (yopiq kun / tarifsiz rasta).
    """
    fee_label: str | None
    """Kvitansiyadagi nom («Tarozi xizmati») — ⛔ BOZOR KIRITGAN MATN.

    Klient uni TARJIMA QILMAYDI va o'zi qotirib qo'ymaydi: har bozor
    xizmatini o'z nomi bilan ataydi. `null` — xizmat haqi yo'q.
    """
    amount_unavailable_reason: AmountUnavailableReason | None
    outstanding_soum: int
    """Eski qarz — HISOBLANADIGAN qoldiq (BILL-03), saqlangan ustun emas."""
    total_due_soum: int
    """⛔ SERVERDA hisoblangan yig'indi (§9.6) — klientda qo'shish YO'Q."""
    stall_status: StallStatus
    """`stalls.status` reyestr ustuni — ⛔ `str` EMAS, ENUM.

    Enum bo'lgani uchun OpenAPI ham YOPIQ to'plamni e'lon qiladi va
    klientdagi `z.enum(STALL_STATUSES)` ko'zgusi kontraktga langarlanadi.
    `str` bo'lganda server bir kun to'rtinchi qiymatni jimgina yuborardi.

    ⛔ BU MAYDON HISOB YOZILISHI HAQIDA DA'VO QILMAYDI (`is_billable`
       EMAS): kunlik hisob `status` bo'yicha filtrlanMAYDI.
    """
    vendor_assigned: bool
    """Bugungi kunda biriktirish BORMI — ⛔ BUL, identifikator EMAS.

    Ma'lumot kassirga submit'da ALLAQACHON oshkor (409
    `stall_not_assigned`); bu yerda faqat uning VAQTI oldinga suriladi.
    `vendor_id`/`vendor_name`/`phone` esa yuqoridagi taqiqda QOLADI.
    """

    @model_validator(mode="after")
    def _amount_and_reason_are_paired(self) -> Self:
        """⛔ JUFTLANGAN INVARIANT (§9.2, `NO_COVERAGE_IS_PAIRED_CHECK` naqshi).

            (amount_soum is None) == (amount_unavailable_reason is not None)

        «Sababsiz yo'q summa» ham, «summasi bor sabab» ham IFODALAB
        BO'LMAYDI. Ikki yo'nalish ikki ALOHIDA xabar bilan: ular ikki
        boshqa server nosozligi va bitta umumiy matn «qaysi yarim
        buzildi?» savolini javobsiz qoldirardi.
        """
        if self.amount_soum is None and self.amount_unavailable_reason is None:
            raise ValueError(
                "SABABSIZ YO'Q SUMMA: `amount_soum` null, lekin sabab berilmagan. "
                "Ekran «summa yo'q» deb ko'rsatardi va kassir NIMA UCHUN "
                "yo'qligini bilmasdi — D-20 aynan buni taqiqlaydi (§9.4)."
            )
        if self.amount_soum is not None and self.amount_unavailable_reason is not None:
            raise ValueError(
                "SUMMASI BOR SABAB: `amount_soum` bor, lekin yo'qlik sababi ham "
                "kelgan. Ikkalasi bir vaqtda rost bo'la olmaydi va bu holat "
                "ekranda «yopiq kun, lekin to'la» bo'lib chizilardi."
            )
        return self


class PendingLookupResponse(BaseModel):
    """`GET /billing/pending?stall_code=…` ning KO'P MOSLIK javobi (§8.3).

    =======================================================================
    ⛔ IKKI SHAKL, ULARDAN AYNAN BITTASI — VA BU O'LCHANADI.

    Kassir kodni PREFIKS sifatida teradi. `"1"` kodi bozorda YO'Q, lekin
    `"10"` va `"100"` bor bo'lsa summa HISOBLANMAYDI: taxminiy summa
    ko'rsatish §9.4 ning aynan taqiqlagan xatosi. O'shanda javob faqat
    KODLAR ro'yxati bo'ladi (`stalls.code_sort` tartibida — inson-raqamli
    tartib serverda, klientda emas).

    ⚠ ANIQ MOSLIK holatida marshrut BU MODELNI EMAS, `PendingStall
      Response` ni (tekis, yetti kalit) qaytaradi — §9.2 ning to'plam
      tengligi AYNAN o'sha tekis payload ustida o'lchanadi (G-23) va
      klient sxemasi (`billing-pending-queries.ts::pendingStallSchema`)
      ham aynan shuni `z.strictObject` bilan kutadi. `stall` maydoni shu
      sababdan «bitta moslik» slotini NOM BILAN band qilib turadi: u
      bo'lmasa ikki shakl orasidagi bog'liqlik kontraktda emas, faqat
      izohda qolardi.
    =======================================================================
    """

    model_config = ConfigDict(extra="forbid")

    matches: list[str]
    """⛔ FAQAT KODLAR — `code_sort` tartibida. Summa, sotuvchi, tarif YO'Q."""
    stall: PendingStallResponse | None
    """«Aynan bitta moslik» sloti — ko'p moslikda `null`."""

    @model_validator(mode="after")
    def _exactly_one_shape(self) -> Self:
        """⛔ `stall` va `matches` BIR VAQTDA to'lgan bo'la olmaydi.

        Ikkalasi ham to'lgan javob ekranga «ro'yxat ham bor, summa ham
        bor» deb kelardi va kassir ro'yxatdan boshqa rastani tanlab,
        ekranda TURGAN summani to'lardi — §9.4 ning «eski summa yangi
        rasta ostida» xatosi, faqat bir so'rov ichida.
        """
        if self.stall is not None and self.matches:
            raise ValueError(
                "IKKI SHAKL BIR VAQTDA: `stall` to'lgan va `matches` ham bo'sh "
                "emas. Aynan bitta moslikda ro'yxat BO'SH bo'ladi, ko'p "
                "moslikda esa summa UMUMAN hisoblanmaydi (§8.3, §9.4)."
            )
        return self


class PendingMarketResponse(BaseModel):
    """`GET /billing/pending` (rasta parametrisiz) — BOZOR kesimi (§9.5).

    ⛔ NOL — NATIJA: uchala son nol bo'lganda ham qaytariladi
       (`occupancy.py:122-124` da o'rnatilgan qoida). «Bugun hech nima
       kutilmayapti» bilan «hisoblagich ishlamayapti» bir xil
       KO'RINMASLIGI kerak.

    ⛔ Bu yerda ham hisob identifikatori YO'Q: bozor kesimi
       proyeksiyaning YIG'INDISI, hisoblar RO'YXATI emas.

    `fetched_at` ATAYIN payloadda: §9.5 avtomatik taymerni RAD ETADI va
    uning o'rniga `[Yangilash]` tugmasi + vaqt tamg'asini qo'yadi —
    «men boshqa raqam ko'rgandim» nizosining manbai jimgina o'zgaradigan
    raqam edi.
    """

    model_config = ConfigDict(extra="forbid")

    service_date: date
    market_open: bool
    pending_amount_soum: int
    outstanding_soum: int
    pending_stall_count: int
    fetched_at: datetime
    row_prefixes: list[str]
    """Bozorda MAVJUD qator harflari — kassir tugmalari uchun (260820).

    =======================================================================
    ⛔⛔ NEGA SERVERDAN: kassirda `MARKET_DATA_VIEW` YO'Q, ya'ni u
        rastalar ro'yxatini ham, xaritani ham ko'ra olmaydi (C-10).
        Klient qator harflarini o'zi bila olmaydi.

        Frontendda ular `["A","B","C","D"]` deb QOTIRIB qo'yilgandi.
        Oqibati ikki tomonlama:
          · Karmanada faqat A va B bor -> ikkita O'LIK tugma;
          · qatori E dan boshlanadigan bozorda kassirga YORDAM YO'Q,
            u kodni yoddan terishi kerak.

        Endi ro'yxat bozorning O'Z rastalaridan hosil bo'ladi: kod
        boshidagi harf(lar), takrorsiz, alifbo tartibida.

    ⛔ RAQAMLI KODLAR («23») HARF BERMAYDI va ro'yxatga tushmaydi —
       ular uchun tugma ham ma'nosiz bo'lardi.
    """


class CollectRosterRowResponse(BaseModel):
    """Kassir ro'yxatining bitta qatori — ⛔ SUMMASIZ (0027).

    =======================================================================
    ⛔⛔ SUMMA MAYDONI YO'Q VA U QO'SHILMAYDI — KO'R SMENA SANOG'I
        (D-25/D-26). Sabab to'liq `billing_repo.CollectRosterRow`
        docstringida: `GET /payments/recent` serverda BESHTA qator bilan
        chegaralangan, ya'ni kassir yig'indini qo'shib chiqara olmasin.
        Bu ro'yxat esa TO'LIQ — unga summa qo'shilsa chegaralashning
        butun ma'nosi yo'qolardi.

    ⛔ `amount_soum` / `paid_soum` / `outstanding_soum` — uchalasi ham
       TAQIQLANADI, nom bilan aylanib o'tish (`total`, `sum`, `value`) ham.

    ⛔ `vendor_id` / ism / telefon YO'Q — C-10: kassir yuzasi
       shaxsiy-ma'lumot yuzasiga aylanmaydi.
    =======================================================================
    """

    model_config = ConfigDict(extra="forbid")

    stall_code: str
    """⛔ Kassir yuzasidagi YAGONA identifikator (§5.5)."""
    vendor_assigned: bool
    """Bugun biriktirish BORMI — ⛔ BUL, identifikator EMAS.

    To'lanmagan ro'yxatda MUHIM: sotuvchisiz rastadan patta olib
    bo'lmaydi (409 `stall_not_assigned`) va kassir behuda urinmasin.
    """
    paid_at: datetime | None
    """Oxirgi to'lov vaqti — FAQAT to'langan qatorlarda.

    ⚠ SUMMA EMAS va shuning uchun ruxsat etiladi: «bu rastadan qachon
      oldim?» — kassirning o'z ishi haqidagi savol, undan yig'indi
      chiqarib bo'lmaydi.
    """


class CollectRosterResponse(BaseModel):
    """`GET /billing/collect-roster` — to'langan yoki to'lanmagan rastalar.

    ⛔ IKKALA SANOQ HAM HAR IKKALA SO'ROVDA QAYTADI (`paid_count` va
       `unpaid_count`): klient «12 / 38» yozuvini ikkinchi so'rov
       yubormasdan chizadi. Nol ham QAYTADI — «ro'yxat bo'sh» bilan
       «hisoblagich ishlamayapti» bir xil ko'rinmasligi kerak.

    ⚠ `page_count` SERVERDA hisoblanadi: klientda `ceil(total/per_page)`
      yozish sahifalash chegarasini ikki joyda saqlardi va bo'sh
      to'plamda (`total = 0`) ular ajralib ketardi — server `1` beradi
      («bitta bo'sh sahifa»), klient esa `0` chizib, sahifa raqamlarini
      umuman yo'qotardi.
    """

    model_config = ConfigDict(extra="forbid")

    service_date: date
    state: Literal["unpaid", "paid", "unassigned"]
    """⛔ So'rovdagi filtr javobda TAKRORLANADI: klient qaysi ro'yxatni
    ko'rayotganini javobning O'ZIDAN biladi, so'rovni qayta o'qib emas
    (`ChargeListResponse.day` bilan bir xil qaror)."""
    rows: list[CollectRosterRowResponse]
    total: int
    """Shu filtr bo'yicha JAMI qator — sahifadagi emas."""
    page: int
    per_page: int
    page_count: int
    paid_count: int
    unpaid_count: int
    unassigned_count: int
    """Sotuvchisiz rastalar — ⛔ `unpaid_count` GA KIRMAYDI (O'-01).

    Ular yig'ish rejasini SUN'IY oshirardi: ulardan patta olib bo'lmaydi
    (`POST /payments` -> 409 `stall_not_assigned`), ya'ni kassir har kuni
    «bajarilmagan» ko'rsatkich bilan qolardi.

    ⛔ RO'YXATDAN OLIB TASHLANMAYDI, AJRATILADI: sotuvchisiz band rasta —
       mahsulot fosh qiladigan anomaliya («ro'yxatga olinmagan savdo»).
    """
    fetched_at: datetime
    """«Oxirgi olingan vaqt» — §9.5 dagi bilan bir xil: avtomatik taymer
    emas, [Yangilash] tugmasi + vaqt tamg'asi."""


class MapDayStatusRow(BaseModel):
    """`GET /billing/map` ning bitta KATAGI (MARKET-06, D-C1).

    =======================================================================
    ⛔ RANG SERVERDAN KELADI, KLIENTDA HISOBLANMAYDI.

    `state` — YOPIQ enum (`MapDayState`) va ustuvorlik qoidasi
    `billing_repo._map_day_state()` da BIR MARTA bajariladi. Klient uni
    faqat CSS sinfiga MAPS qiladi. Qoidani ikki tilda yozish ularni bir
    kun ajratardi va xaritadagi rang bilan hisobotdagi holat FARQ
    qilardi — ikkalasi ham «to'g'ri» bo'lgan holda.

    =======================================================================
    ⛔ YO'Q VA YO'QLIGI O'LCHANADIGAN MAYDONLAR:

        stall_code         — katak `id` bo'yicha bog'lanadi va kod
                             `GET /stalls/map` da ALLAQACHON bor;
        vendor_id · nom    — C-10: bu marshrut `VENDOR_VIEW` yuzasini
                             KENGAYTIRMAYDI va `audit_read` yozmaydi;
        charge_id          — D-17 + `test_billing_api.py` ning butun
                             `/billing/*` yuzasi bo'ylab mexanik skani;
        vendor_outstanding — D-C6: bu RASTA darajasidagi miqdor EMAS. Bir
                             sotuvchining uch rastasida takrorlanib, ko'z
                             bilan qo'shilganda UCH BAROBAR ko'rinardi.

    =======================================================================
    ⚠ `open_case_service_date` `open_case_id` BILAN JUFT: «ochiq
      nomuvofiqlik» bugungi kunniki bo'lmasligi mumkin (D-C5 ning
      istisnosi) va uni bugungi deb ko'rsatish YOLG'ON bo'lardi.
    """

    model_config = ConfigDict(extra="forbid")

    stall_id: UUID
    state: MapDayState
    """⛔ `str` EMAS, ENUM — OpenAPI yopiq to'plamni e'lon qiladi va
    klientdagi `z.enum(...)` ko'zgusi kontraktga langarlanadi."""
    amount_soum: int | None
    """Bugungi patta. `null` — FAQAT nomlangan sabab bilan."""
    unavailable_reason: AmountUnavailableReason | None
    paid_soum: int
    """Bugun shu rastaga tushgan BELGILI to'lov — ⛔ nol ham NATIJA."""
    remaining_soum: int | None
    """Bugun QOLGAN qarz — ⛔ SERVERDA ayirilgan (D-20).

    Klient uni O'ZI hisoblay olardi (ikkala qo'shiluvchi ham javobda),
    lekin o'shanda kartadagi son bilan katakning rangi IKKI BOSHQA
    ayirishdan chiqardi va ular bir kun ajralib ketardi. Sabab to'liq
    `billing_repo.MapDayStallStatus.remaining_soum` docstringida.
    """
    open_case_id: UUID | None
    open_case_service_date: date | None

    @model_validator(mode="after")
    def _amount_and_reason_are_paired(self) -> Self:
        """⛔ `StallDayMoney` NING JUFTLANGAN INVARIANTI — HTTP chegarasida ham.

            (amount_soum is None) == (unavailable_reason is not None)
            (amount_soum is None) == (remaining_soum is None)

        `PendingStallResponse` dagi jufti bilan AYNAN bir xil shakl: ikki
        yo'nalish ikki ALOHIDA xabar bilan, chunki ular ikki boshqa server
        nosozligi.
        """
        if (self.amount_soum is None) != (self.remaining_soum is None):
            raise ValueError(
                "SUMMA VA QOLDIQ AJRALDI: hisob yo'q kunda «qolgan qarz» "
                "MA'NOSIZ va nol yozish uni «to'liq to'langan» bilan bir xil "
                f"ko'rsatardi (amount_soum={self.amount_soum!r}, "
                f"remaining_soum={self.remaining_soum!r})."
            )
        if self.amount_soum is None and self.unavailable_reason is None:
            raise ValueError(
                "SABABSIZ YO'Q SUMMA: `amount_soum` null, lekin sabab berilmagan. "
                "Katak rangsiz qolardi va legenda NIMA UCHUN rangsizligini "
                "ayta olmasdi (D-C2 ning 2-qatori)."
            )
        if self.amount_soum is not None and self.unavailable_reason is not None:
            raise ValueError(
                "SUMMASI BOR SABAB: `amount_soum` bor, lekin yo'qlik sababi ham "
                "kelgan. Ikkalasi bir vaqtda rost bo'la olmaydi va katak "
                "«hisob yo'q, lekin 15 000 so'm» bo'lib chizilardi."
            )
        return self

    @model_validator(mode="after")
    def _the_case_pointer_is_paired(self) -> Self:
        """⛔ `open_case_id` VA `open_case_service_date` BIRGA keladi.

        Sanasiz case havolasi kartada «qaysi kunning nomuvofiqligi?»
        savolini javobsiz qoldirardi; case'siz sana esa hech qayerga
        ishora qilmaydigan yorliq bo'lardi.
        """
        if (self.open_case_id is None) != (self.open_case_service_date is None):
            raise ValueError(
                "CASE KO'RSATKICHI YARIM: `open_case_id` va "
                "`open_case_service_date` faqat BIRGA to'ladi "
                f"(open_case_id={self.open_case_id!r}, "
                f"open_case_service_date={self.open_case_service_date!r})."
            )
        return self


class MapDayStatusResponse(BaseModel):
    """`GET /billing/map` — xarita qatlamining butun javobi.

    ⛔ `market_open` — `bool | null`, VA `null` «O'LCHANMADI» DEGANI.

    Qoralama bozorda (`market_active = false`) kalendar UMUMAN
    so'ralmaydi, ya'ni server «yopiq» ham, «ochiq» ham DEYA OLMAYDI.
    `false` yozish o'lchanmagan miqdorni o'lchangan qilib ko'rsatardi —
    05-14 da qulflangan taqiq (nol/yolg'on o'rniga YO'QLIK).

    ⛔ QORALAMA BOZORDA `rows` BO'SH: yolg'on qizil YO'Q. Sabab
    `billing_repo._MARKET_IS_ACTIVE` docstringida.
    """

    model_config = ConfigDict(extra="forbid")

    service_date: date
    market_active: bool
    market_open: bool | None
    rows: list[MapDayStatusRow]


class ChargeRowResponse(BaseModel):
    """`GET /billing/charges?day=…` ning bitta qatori (UI-SPEC §11.2).

    ⛔ `vendor_name` YO'Q, `vendor_id` BOR (C-10 + §5.5). Sotuvchi nomi
       ekranda KERAK, lekin u MAVJUD, AUDIT QILINGAN `GET /vendors`
       marshrutidan olinib KLIENTDA joinlanadi. Nomni bu javobga
       qo'shish `PERSONAL_ROUTES` ni o'stirardi va o'sha marshrutdan
       `audit_read(...)` talab qilinardi — ya'ni moliyaviy yuza
       shaxsiy-ma'lumot yuzasiga aylanardi.

    ⛔ `balance` NOMLI maydon HECH QAYERDA yo'q (BILL-03): qoldiq —
       HISOBLANADIGAN ko'rinish va uning nomi ham `outstanding_soum`.

    ⚠ `amount_soum` — TUZATISHLAR BILAN NETLANGAN summa
      (`amount_soum + Σ(increase) − Σ(decrease)`). `tariff_amount_soum`
      dan FARQ QILISHI aynan tuzatish bo'lganini aytadi (§11.2) va
      arifmetika SERVERDA bajariladi: klient ikki ustunni ayirib
      «tuzatish bormi?» degan xulosaga kelmasligi kerak.
    """

    model_config = ConfigDict(extra="forbid")

    charge_id: UUID
    stall_code: str
    vendor_id: UUID
    service_date: date
    tariff_amount_soum: int
    """Tarif BERGAN summa (D-09) — retroaktiv o'zgarishdan himoyalangan."""
    amount_soum: int
    outstanding_soum: int
    """Sotuvchi kesimidagi qoldiq (BILL-03) — rasta kesimida EMAS (C-4)."""


class ChargeListResponse(BaseModel):
    """`GET /billing/charges?day=…` — kun kesimidagi yozilgan hisoblar.

    ⛔ IKKALA HISOBLAGICH HAM HAR DOIM QAYTADI, nol bo'lganda ham. Kun
       bo'sh bo'lishi NORMAL holat (C-3: hisob D+1 04:10 da tug'iladi),
       lekin «bu kunda hisob yo'q» bilan «hisoblagich ishlamayapti» bir
       xil ko'rinsa direktor tizimni buzuq deb hisoblardi.

    ⚠ `day` javobda ATAYIN bor: standart kun SERVERDA hisoblanadi
      (KECHA — §11.1) va klient qaysi kunni ko'rayotganini javobning
      O'ZIDAN biladi, so'rovni qayta o'qib emas.
    """

    model_config = ConfigDict(extra="forbid")

    day: date
    rows: list[ChargeRowResponse]
    charge_count: int
    charged_soum: int


class ChargeAdjustmentRow(BaseModel):
    """DL-3 ning 4-bo'limi — hisob tuzatishi (§11.3).

    ⛔ `actor_user_id` — IDENTIFIKATOR, ism EMAS (C-10 + §5.5). Ism
       `GET /users` dan klientda joinlanadi.

    ⛔ Bo'sh massiv YASHIRILMAYDI: dialog «Tuzatish yo'q» jumlasini
       ko'rsatadi — nol NATIJA, yo'qlik emas.
    """

    model_config = ConfigDict(extra="forbid")

    adjustment_id: UUID
    direction: AdjustmentDirection
    """`increase` / `decrease` — ⛔ BELGILI summa emas, kattalik + yo'nalish (C-5)."""
    amount_soum: int
    reason_code: AdjustmentReason
    """YOPIQ ro'yxat (D-19) — `other` a'zosi YO'Q."""
    actor_user_id: UUID | None
    """⛔ `NULL` = TIZIM (`0022` ustunni ATAYIN nullable qildi).

    `late_review` tuzatishini `billing_close` job'i yozadi
    (`billing_repo.write_late_review_adjustment()` → `actor_user_id=None`)
    va unga odam biriktirish «kim qaror qildi?» savoliga YOLG'ON javob
    bo'lardi. Bu yerda `UUID` (non-Optional) e'lon qilish javobni
    `ResponseValidationError` bilan **500** ga aylantirardi — aynan
    nizoli, ya'ni tuzatilgan hisoblar uchun. Klient sxemasi
    (`billing-charge-queries.ts`) `null` ni ALLAQACHON kutadi.
    """
    created_at: datetime


class ChargeEvidenceRow(BaseModel):
    """DL-3 ning 5-bo'limi — dalil kadri (§11.3, BILL-02).

    ⛔ `snapshot_id` `null` bo'lgan element QAYTARILISHI MUMKIN va klient
       uni UMUMAN CHIZMAYDI: na placeholder, na «yuklanmadi». Bu 05-14
       ning darsi — marshrut bermagan qatorni to'qish (stub) ham, bo'sh
       jadval (placeholder) ham RAD ETILGAN.

    ⛔ `tariff_id` bu yerda ham, `ChargeDetailResponse` da ham YO'Q:
       direktorga ham ma'nosiz identifikator (§11.3, 2-bo'lim).
    """

    model_config = ConfigDict(extra="forbid")

    snapshot_id: UUID | None
    slot_time: time


class ChargeDetailResponse(BaseModel):
    """`GET /billing/charges/{charge_id}` — DL-3 ning besh bo'limi (§11.3).

    ⛔ `tariff_id` E'LON QILINMAGAN. `tariff_amount_soum` BOR va u
       ma'noli son; tarifning identifikatori esa ekranda hech nimani
       ochmaydi va uni berish D-20 ning kirish ma'lumotini direktor
       yuzasidan kassir yuzasiga ko'chirish yo'lini ochardi.

    ⛔ `vendor_name` ham YO'Q (C-10): sarlavhada rasta KODI turadi,
       sotuvchi nomi esa `GET /vendors` dan klientda joinlanadi.

    ⚠ 3-bo'lim («Bu hisob o'zgartirilmaydi») — MATN, ya'ni u payloadda
      YO'Q va bo'lishi ham shart emas: u har doim ko'rinadi va
      serverdan kelgan bayroqqa bog'liq emas (§11.3).
    """

    model_config = ConfigDict(extra="forbid")

    charge_id: UUID
    service_date: date
    stall_code: str
    tariff_amount_soum: int
    amount_soum: int
    """⛔ TUZATISHLAR BILAN NETLANGAN — `ChargeRowResponse` bilan AYNI arifmetika."""
    adjustments: list[ChargeAdjustmentRow]
    evidence: list[ChargeEvidenceRow]


class AnomalyRowResponse(BaseModel):
    """`GET /billing/anomalies?day=…` ning bitta qatori (BILL-04, §11.4).

    =======================================================================
    ⛔ JUFTLANGAN INVARIANT — C-12 ning DB `CHECK` ining AYNAN takrori:

        (kind = 'no_coverage_stall') = (snapshot_id IS NULL)

    «Qamrovsiz rasta» dalilsiz, qolgan ikki tur esa dalil BILAN keladi.
    Ikkala yo'nalish ham ifodalab bo'lmaydigan qilinadi: «qamrovsiz,
    lekin kadri bor» — KO'R NUQTADAN dalil da'vosi; «band, lekin
    kadrsiz» — hukmning dalilsiz qolishi.
    =======================================================================
    """

    model_config = ConfigDict(extra="forbid")

    anomaly_id: UUID
    kind: AnomalyKind
    stall_code: str
    service_date: date
    snapshot_id: UUID | None

    @model_validator(mode="after")
    def _no_coverage_is_paired(self) -> Self:
        """C-12 ning serializator qatlamidagi takrori."""
        if (self.kind is AnomalyKind.NO_COVERAGE_STALL) != (self.snapshot_id is None):
            raise ValueError(
                "C-12 JUFTLIGI BUZILDI: `no_coverage_stall` dalilsiz, qolgan "
                "turlar esa dalil bilan kelishi SHART. "
                f"kind={self.kind.value!r}, snapshot_id={self.snapshot_id!r}"
            )
        return self


class AnomalyListResponse(BaseModel):
    """`GET /billing/anomalies?day=…` — kun kesimidagi anomaliyalar.

    =======================================================================
    ⛔⛔ UCH ALOHIDA SANOQ VA ULAR HECH QACHON QO'SHILMAYDI (D-05).

    «Ko'ra olmadik» (`no_coverage_stall`) ≠ «band, lekin biriktirilmagan»
    (`unassigned_occupied`). Ikkisini bitta «anomaliya soni» ga qo'shish
    KO'R NUQTADAN TUSHUM DA'VOSI TO'QISH bo'lardi — ya'ni hisobot
    kamerasiz rastani ham «yo'qotilgan pul» deb ko'rsatardi.

    Shuning uchun bu yerda `anomaly_count` NOMLI maydon YO'Q va u
    qo'shilmaydi: yagona son mavjud bo'lsa ekran uni ko'rsatardi va
    farq matn darajasida yo'qolardi (G-26 ning sababi).
    =======================================================================

    ⛔ UCHALA SANOQ HAM NOL BO'LGANDA HAM QAYTADI — nol NATIJA.
    """

    model_config = ConfigDict(extra="forbid")

    day: date
    rows: list[AnomalyRowResponse]
    unassigned_count: int
    """`unassigned_occupied` — «Ro'yxatga olinmagan savdo» (D-28)."""
    closed_day_count: int
    """`closed_day_occupied` — «Yopiq kunda savdo» (D-10)."""
    no_coverage_count: int
    """`no_coverage_stall` — «Qamrovsiz rasta» (D-05). ⛔ Yuqoridagilarga QO'SHILMAYDI."""


# ---------------------------------------------------------------------------
# 06-09: KASSIRNING YOZUV YUZASI (CASH-01…CASH-03)
#
# ⛔⛔ YUQORIDAGI 06-08 BLOKINING «E'LON QILMASLIK» NAQSHI SHU YERDA HAM
#    TO'LIQ KUCHDA — VA U ENDI **SO'ROV** MODELLARIGA HAM QO'LLANADI.
#
# `PaymentCreateRequest` da `quote_soum` maydoni YO'Q. Bu D-20 ning
# so'rov tomonidagi shakli: server bergan summani MIJOZ yubora olsa,
# `payments` dagi juftlangan `CHECK ((amount_soum = quote_soum) =
# (override_reason IS NULL))` ⛔ **CHETLAB O'TILARDI** — kassir
# `quote_soum = amount_soum` deb yuborib har qanday summani sababsiz
# yozardi va D-19 ning butun narxi bekor bo'lardi. Maydonni `None`
# standarti bilan e'lon qilish ham YETARLI EMAS: keyingi bosqich BIR
# SATRLIK bo'lardi.
#
# ⛔ `charge_id` HAM YO'Q — na so'rovda, na javobda (D-24/C-4): to'lov
#    hisobga bog'lanmaydi va bog'lanish uchun narsaning O'ZI yo'q (hisob
#    D+1 04:10 da tug'iladi, to'lov esa BUGUN yoziladi).
#
# ⛔ `shift_id` HAM SO'ROVDA YO'Q va bu 06-09 ning ONGLI chetlanishi —
#    sabab `PaymentCreateRequest` docstringida (T-06-57).
# ---------------------------------------------------------------------------


class PaymentCreateRequest(BaseModel):
    """`POST /payments` tanasi — ⛔ MIJOZ PUL MAYDONI YUBORMAYDI (D-20).

    =======================================================================
    ⛔⛔ E'LON QILINMAGAN MAYDONLAR — NOM BILAN:

        quote_soum   — D-20; server `payment_quote_set()` dan tanlaydi
        charge_id    — D-24/C-4; to'lov hisobga bog'lanmaydi
        shift_id     — T-06-57; server SO'ROVCHINING ochiq smenasini
                       o'zi yechadi
        service_date — kun `business_today()`; o'tmish kuniga to'lov
                       yozish yuzasi 6-fazada QURILMAYDI
        vendor_id    — u `stall_code` dan yechiladi (D-28); mijozdan
                       olish begona sotuvchiga to'lov yozish yo'lini
                       ochardi
    =======================================================================

    ⛔ **`shift_id` NEGA MIJOZDAN OLINMAYDI** (rejadan ONGLI chetlanish):
       uni qabul qilish kassirga **boshqa kassirning** ochiq smenasiga
       to'lov yozish imkonini berardi va o'sha smenaning ko'r
       deklaratsiyasi (D-25) begona pul bilan ifloslanardi — variance
       hisobotida sababi topilmaydigan farq chiqardi. Bu `quote_soum`
       bilan **AYNAN BIR XIL** sinf: server o'zi biladigan qiymatni
       mijozdan olmaydi. Server `payment_repo.open_shift_id()` bilan
       yechadi; ochiq smena bo'lmasa `NULL` (OQ-6/A5 — direktor smenasiz
       kiritishi mumkin).

    ⚠ **MAYDON NOMI `reason_code`, `override_reason` EMAS** — va bu
      KLIENT KONTRAKTIDAN keladi: `frontend/src/lib/payment-queries.ts`
      ning `PaymentInput` tipi (06-03, allaqachon merge qilingan) aynan
      shu nomni yuboradi. `extra="forbid"` ostida ikkinchi nom **422**
      berardi va 06-11 ning kassir paneli birinchi bosishdayoq
      yiqilardi. Ustun nomi `payments.override_reason` bo'lib qoladi;
      ikki nom orasidagi ko'chirish ⛔ **AYNAN BITTA joyda** —
      `api/v1/payments.py` handlerida.
    """

    model_config = ConfigDict(extra="forbid")

    idempotency_key: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    """D-21 ning kaliti — ⛔ MIJOZ BERADI va u sahifa holatida yashaydi (§8.7).

    ⚠ Uzunlik chegarasi bor, SHAKLI esa YO'Q (UUID talab qilinmaydi):
      kalit server uchun **shaffof satr** va uning ma'nosi faqat
      «bu o'sha so'rovmi?» — formatni majburlash klientni server
      tanlagan shaklga bog'lab qo'yardi.
    """
    stall_code: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    """⛔ Kassir yuzasidagi YAGONA identifikator (§5.5) — `stall_id` EMAS."""
    method: Literal["cash", "terminal"]
    """`payments.method`. ⛔ Uchinchi tur YO'Q (`PaymentMethod` docstringi)."""
    amount_soum: int = Field(gt=0, le=MAX_SAFE_SOUM)
    """AMALDA olinadigan summa. ⛔ `> 0` — nol to'lov to'lov emas."""
    reason_code: AdjustmentReason | None = None
    """Server taklifidan CHETLANISH sababi (D-19).

    ⛔ IKKI TOMONLAMA MAJBURIY: chetlanish bor-u sabab yo'q -> **422
       `reason_required`**; chetlanish yo'q-u sabab bor -> **422
       `override_not_applicable`**. Shart handlerda, juftlangan `CHECK`
       esa sxemada — himoya IKKI QATLAM (06-04).
    """


class PaymentReverseRequest(BaseModel):
    """`POST /payments/{payment_id}/reverse` tanasi — sabab ⛔ MAJBURIY (D-23).

    ⚠ `reason_code` `ReversalReason` DAN, `AdjustmentReason` DAN EMAS: ular
      ikki BOSHQA yopiq to'plam (`payments.reversal_reason` va
      `payments.override_reason` ustunlari ham alohida `CHECK` bilan
      qulflangan). Birlashtirish «bekor qilish sababi» bilan «summa
      o'zgarishi sababi» ni bir hisobotda aralashtirardi.

    ⛔ MAYDON IXTIYORIY EMAS: standart qiymat berilsa birinchi shoshilinch
       tuzatishda u bo'sh ketardi va hisobotda «sababsiz storno» guruhi
       paydo bo'lardi (D-19 ning aynan oldini olayotgan holati).
    """

    model_config = ConfigDict(extra="forbid")

    reason_code: ReversalReason


class PaymentResponse(BaseModel):
    """Yozilgan to'lov qatori — ⛔ KALITLAR TO'PLAMI AYNAN SAKKIZTA (§8.8).

    =======================================================================
    ⛔⛔ E'LON QILINMAGAN MAYDONLAR — NOM BILAN (yashirilgan EMAS):

        charge_id                       — D-24/C-4
        vendor_id · vendor_name · phone — C-10 + §5.5
        quote_soum · override_reason    — D-20; ular «server qancha taklif
                                          qilgan edi?» savolining KIRISH
                                          ma'lumoti va u nizoda AUDITDAN
                                          o'qiladi, ekrandan emas
        shift_id · cashier_id           — kassir o'z yozuvini ko'radi;
                                          identifikatorlar unga ma'nosiz
        shift_total · running_total     — ⛔ D-25: har qanday YIG'INDI
                                          maydoni ko'r deklaratsiyani
                                          arifmetika bilan buzardi
    =======================================================================

    ⚠ To'plam `frontend/src/lib/payment-queries.ts::paymentResponseSchema`
      (`z.strictObject`, 06-03) bilan AYNAN bir xil — test ikkalasini
      solishtiradi.

    ⚠ `reversed` — ⛔ HOSILA, saqlangan ustun EMAS: storno o'z qatori
      bo'lgani uchun «bu to'lov bekor qilinganmi?» savoli mavjudlik
      so'rovi bilan javob oladi (D-23).
    """

    model_config = ConfigDict(extra="forbid")

    payment_id: UUID
    stall_code: str
    service_date: date
    """⛔ «Qaysi kun UCHUN kiritildi», «qaysi kunning pattasi YOPILDI» EMAS.

    Ikkinchisi `allocate_charge_credit()` ning `FIFO_OLDEST_SERVICE_DATE_
    FIRST` hosila qoidasidan chiqadi va HECH QAYERDA saqlanmaydi (D-24).
    """
    amount_soum: int
    kind: Literal["payment", "reversal"]
    method: Literal["cash", "terminal"]
    created_at: datetime
    reversed: bool


class RecentPaymentsResponse(BaseModel):
    """`GET /payments/recent` — ⛔ OYNA SERVERDA QAT'IY 5 (§8.8, §10.3).

    =======================================================================
    ⛔⛔ NA YIG'INDI, NA UMUMIY SANOQ, NA KEYINGI SAHIFA BELGISI.

    Kassir o'zi yozgan to'lovlarni ko'rishi KERAK (bekor qilish uchun).
    Lekin u smenasining HAMMA to'lovini ko'rsa, ularni **qo'shib** tizim
    summasini chiqarib olardi va §10.3 ning ko'r deklaratsiyasi
    ⛔ **ARIFMETIKA BILAN** buzilardi.

    Shuning uchun bu modelda `total`/`count`/`next_cursor` NOMLI maydon
    YO'Q, marshrutda esa `limit`/`offset`/`cursor` **parametri** yo'q —
    yig'indi yo'lini **maydon yashirish** emas, ⛔ **marshrutning
    imkoniyati** to'sadi.
    =======================================================================

    ⚠ Bo'sh `items` — «natija», nosozlik emas: ochiq smenasi bo'lmagan
      foydalanuvchi (direktor) bo'sh ro'yxat oladi, **404 emas**.
    """

    model_config = ConfigDict(extra="forbid")

    items: list[PaymentResponse]


# ---------------------------------------------------------------------------
# 06-10: SMENA VA ⛔⛔ KO'R NAQD DEKLARATSIYASI (CASH-04, D-25, D-26)
#
# ⛔⛔ BU BO'LIMDA IKKI YUZA BOR VA ULARNING KALITLAR TO'PLAMI ATAYIN
#    BOSHQA — «yo'qlik» BITTA modelda, «borlik» ikkinchisida:
#
#      ShiftCloseResponse  (kassir)   -> variance YO'Q, tizim summasi YO'Q
#      ShiftReportRow      (direktor) -> ikkalasi ham BOR
#
# Bir modelni ikkinchisiga «umumlashtirish» (ixtiyoriy maydonlar bilan
# bitta model) D-25 ni ⛔ BIR SATRDA buzardi: ixtiyoriy maydon javobda
# `null` bo'lib turardi va uni to'ldirish bitta topshiriq bo'lardi.
#
# ⛔ HAR MODELDA `extra="forbid"` — 06-08/06-09 bloklarida o'rnatilgan
#    qoida (`model_construct()` yoki noto'g'ri `**kwargs` bilan qo'shilgan
#    maydon JIMGINA o'tib ketmasin).
# ---------------------------------------------------------------------------


class ShiftOpenResponse(BaseModel):
    """`POST /shifts` va `GET /shifts/open` — AYNAN UCH kalit (UI-SPEC §10.1).

    =======================================================================
    ⛔⛔ OCHIQ SMENA KARTASIDA YIG'INDI KO'RINMAYDI — «HECH QANDAY
        SHAKLDA» (§10.1 ning so'zma-so'z talabi).

    E'LON QILINMAGAN maydonlar — NOM bilan:

        payment_count · collected_soum · average_soum · today_total
        system_soum   · system_total_soum

    Ular «bugungi natija» ko'rinishida ⛔ ZARARSIZ tuyuladi, lekin har
    biri ⛔ **yig'indiga olib boradi** va smena yopilishidagi ko'r
    deklaratsiyani (§10.3) ARIFMETIKA bilan buzardi. Kassir kartani kun
    davomida ko'radi, ya'ni u sanashdan OLDIN son ko'rgan bo'lardi.
    =======================================================================

    ⚠ `GET /shifts/open` ochiq smena bo'lmasa ⛔ **`null`** qaytaradi,
      **404 EMAS**: §10.1 da ekranning IKKI holati bor (`EmptyState` +
      `[Smenani ochish]`, yoki karta), uchinchisi yo'q. 404 klientni
      «server nosoz» shoxiga yuborardi.

    ⚠ To'plam `frontend/src/lib/shift-queries.ts::shiftOpenSchema`
      (`z.strictObject`, 06-03) bilan AYNAN bir xil.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: Literal["open", "closed"]
    opened_at: datetime


class ShiftCloseRequest(BaseModel):
    """`POST /shifts/{shift_id}/close` tanasi — ⛔ AYNAN BITTA maydon.

    =======================================================================
    ⛔⛔ `system_soum` VA `variance_soum` QABUL QILINMAYDI.

    Ular D-25 ning so'rov tomonidagi shakli: mijoz tizim summasini
    yubora olsa, u avval uni ⛔ **BILISHI** kerak bo'lardi — ya'ni
    maydonning MAVJUDLIGI o'zi «bu son klientda bor» degan taxminni
    kontraktga yozib qo'yardi va keyingi ijrochi uni to'ldiradigan
    `GET` marshrutini qidirardi.

    ⛔ `shift_id` HAM TANADA YO'Q — u YO'L parametri; ikki joyda
       berilishi ularni bir-biriga zid qilib yuborish yo'lini ochardi.
    =======================================================================

    ⛔ **`0` RUXSAT ETILADI** (§10.2, `ge=0`, `gt=0` EMAS): butun smena
       terminal orqali o'tgan kun ⛔ **REAL holat** va uni rad etish
       kassirni SOXTA naqd summa yozishga majburlardi. Manfiy qiymat
       shu yerda **422** bo'ladi va u `ck_cashier_shifts_declared_soum_
       non_negative` ning HTTP qatlamidagi jufti.
    """

    model_config = ConfigDict(extra="forbid")

    declared_soum: int = Field(ge=0, le=MAX_SAFE_SOUM)
    """Kassir SANAB kiritgan naqd — ⛔ `0` ham qonuniy qiymat."""


class ShiftCloseResponse(BaseModel):
    """`POST /shifts/{shift_id}/close` — ⛔⛔ KALITLAR TO'PLAMI AYNAN TO'RTTA.

    =======================================================================
    ⛔⛔ SAKKIZ MAYDONNING BIRORTASI HAM E'LON QILINMAGAN VA BU
        «YASHIRISH» EMAS (naqsh `BlindItemResponse` DAN VERBATIM):

        system_soum · system_total_soum · expected_soum
        variance_soum · variance
        payment_count · cash_count · terminal_soum

    (a) ⛔ **BRAUZERGA YETGAN MAYDON O'QILADI** (Pitfall 6): DevTools,
        tarmoq paneli, React DevTools, `JSON.stringify`. CSS ham,
        shartli render ham mexanizm EMAS — «ko'rsatmayapmiz» kod-ko'rik
        DA'VOSI, ⛔ **o'lchov emas**.

    (b) ⛔ **`null` QILIB YUBORISH HAM YARAMAYDI:** `null` maydonning
        ⛔ **BORLIGINI** tasdiqlaydi va keyingi ijrochi uni to'ldirardi —
        o'zgarish BIR SATRLIK bo'lardi. `include_in_schema=False` esa
        umuman himoya emas: u hujjatni o'zgartiradi, ⛔ **baytlarni
        emas**.

    (c) ⛔ **VARIANCE FAQAT `GET /shifts?day=` DA** (UI-SPEC §10.4).
        Sabab matematik: `system = declared − variance` — ⛔ **bitta
        ayirish**, ya'ni variance ni qaytarish `system_soum` ni
        qaytarish bilan AYNI narsa. Qo'shimcha ikki sabab: har kuni
        variance ko'rgan kassir ⛔ **langar** hosil qiladi va sanashdan
        oldin TAXMIN qiladi; va bu smenada tuzatish yo'li ⛔ **YO'Q**
        (deklaratsiya o'zgarmas, variance to'g'rilanmaydi) — ya'ni
        ko'rsatish ⛔ **hech qanday harakatni ochmaydi**.
    =======================================================================

    **Kassir yopgandan keyin ko'radigan narsa AYNAN UCHTA** (§10.3):
    `Badge tone="success"` «Deklaratsiya yozildi» · kiritilgan summa
    (`font-mono`) · `[Yangi smena ochish]`.

    ⚠ To'plam TENGLIGI bilan o'lchanadi (D-31), inkor tasdiq bilan EMAS:
      `not in` faqat AYNAN o'sha nomni ushlaydi va `systemSoum` jimgina
      o'tib ketardi. Ikkinchi, MUSTAQIL qatlam — `app.openapi()` dan
      hosila skan (D-32), uchinchisi esa klientdagi `z.strictObject`.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: Literal["open", "closed"]
    declared_soum: int
    closed_at: datetime


class ShiftReportRow(BaseModel):
    """`GET /shifts?day=` jadvalining bitta qatori — ⛔ variance BILAN (§11.5).

    ⛔ **KASSIRNING ISMI YO'Q** (C-10 + §5.5): `cashier_id` qaytadi, ism
       esa klientda MAVJUD va AUDIT QILINGAN `GET /users` dan
       joinlanadi. `cashier_name`/`full_name` qo'shish moliyaviy
       marshrutga shaxsiy-ma'lumot qo'riqchisini o'rnatardi va
       `PERSONAL_ROUTES` ni o'stirardi. ⛔ Nom bilan aylanib o'tish
       (`cashier_label`, `who`) ham TAQIQLANADI.

    ⛔ **`variance_soum` BELGILI VA MODUL KATTALIGIGA AYLANTIRILMAYDI**
       (D-26, Pitfall 7): `< 0` kamomad, `> 0` ortiqcha, `= 0` mos
       keldi. «Ortiqcha naqdni jimgina yutish kamomadni yashirish bilan
       BIR XIL xato» — shuning uchun ikkala yo'nalish ham qaytariladi.

    ⚠ `closed_at`/`declared_soum` ⛔ **`None` EMAS** va bu ATAYIN:
      hisobot FAQAT yopilgan smenalarni qaytaradi
      (`shift_repo._SHIFT_REPORT_ROWS`), `ck_cashier_shifts_closed_has_
      declaration` esa juftlikni MAJBURLAYDI. Ularni ixtiyoriy qilish
      «ochiq smenani ham qo'shsak bo'ladi» degan taklifni kontraktga
      yozib qo'yardi — o'shanda variance MA'NOSIZ bo'lardi (deklaratsiya
      hali yozilmagan, tizim summasi hamon o'syapti).

    ⚠ Klientning `shiftReportRowSchema` si (06-03) ikkalasini
      `nullable()` deb o'qiydi — bu KENGROQ shart, ya'ni bu javob unga
      to'liq mos keladi.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID
    cashier_id: UUID
    opened_at: datetime
    closed_at: datetime
    declared_soum: int
    system_soum: int
    variance_soum: int
    """⛔ SERVERDA hisoblangan (`sbozor_core.billing.variance()`).

    Klientda AYIRISH qilinmaydi va bu 05-14 ning darsi: klientdagi qayta
    hisob xato bo'lib emas, ⛔ **IKKINCHI JAVOB** bo'lib chiqadi.
    """


class ShiftReportResponse(BaseModel):
    """`GET /shifts?day=` — ⛔ SMENASIZ to'lovlar NOMLANGAN maydon (§11.5).

    =======================================================================
    ⛔⛔ §11.5 FLAG'I SHU YERDA YOPILADI (06-RESEARCH OQ-6 / A5).

    `shift_id IS NULL` bo'lgan to'lovlar birorta kassir qutisiga
    ⛔ **tushmagan**, ya'ni ular variance hisobiga ⛔ **KIRMAYDI** va bu
    ⛔ **to'g'ri**. Ammo ular PUL: ko'rsatilmasa, hisobotdan ⛔ **JIMGINA
    yo'qolardi** va kun yig'indisi sababsiz kamayardi (D-14 ruhi —
    o'lchanadigan miqdor NOMLANADI).

    ⛔ SANOQ VA SUMMA — IKKALASI HAM: faqat summa «bitta katta to'lovmi
       yoki ellikta kichikmi?» savolini javobsiz qoldirardi.
    =======================================================================

    ⛔ **NOL — NATIJA:** birorta smena yopilmagan kunda ham uchala maydon
       QAYTADI (`rows=[]`, ikkala hisoblagich `0`). «Bu kunda smena
       yo'q» bilan «hisoblagich ishlamayapti» bir xil ko'rinmasligi
       kerak (`AnomalyListResponse` bilan aynan bir xil qaror).

    ⚠ `day` — ⛔ **YECHILGAN** kun, so'rovdagi (ixtiyoriy) parametr emas:
      klient uni yubormasa server BUGUN ni tanlaydi va javob QAYSI kun
      ekanini o'zi aytadi. `ChargeListResponse`/`AnomalyListResponse`
      bilan aynan bir xil shakl — usiz klient «men so'ragan kun» ni
      taxmin qilardi va sana chegarasida (Toshkent yarim tuni) ekran
      boshqa kunning sarlavhasi bilan chizilardi.
    """

    model_config = ConfigDict(extra="forbid")

    day: date
    rows: list[ShiftReportRow]
    shiftless_payment_count: int
    shiftless_payment_soum: int


# ---------------------------------------------------------------------------
# 07-10: NOMUVOFIQLIK HISOBOTI VA CASE YUZASI (RECON-01, RECON-02)
#
# ⛔⛔ BU BO'LIMDAGI HAR BEsh MODELDA UCH TAQIQ BIR VAQTDA KUCHDA:
#
#   (a1) `chat_id` / `telegram_user_id` / `telegram_username` maydoni
#        ⛔ **YO'Q**. Ular `PERSONAL_FIELDS` da BO'LMAGANI uchun C-10
#        darvozasi (`tests/tenancy/test_personal_data_coverage.py`) ularni
#        ⛔ **USHLAMAYDI** — ya'ni bu yerda darvoza emas, INTIZOM ishlaydi.
#        Ular odamni TASHQI tizimda aniqlaydi va chegaradan CHIQIB BO'LGAN
#        (D-01); `07-UI-SPEC.md` §5.5 shu bo'shliqni frontend tomonda
#        **G-36** bilan yopadi.
#
#   (a)  `vendor_name` / `phone` / `full_name` maydoni ⛔ **YO'Q** (D-05,
#        06-UI-SPEC §5.5). Ism klientda MAVJUD va AUDIT QILINGAN
#        `GET /vendors` bilan joinlanadi. Nomni qo'shish `PERSONAL_ROUTES`
#        ni o'stirardi va moliyaviy yuza shaxsiy-ma'lumot yuzasiga
#        aylanardi. ⛔ Nom bilan aylanib o'tish (`vendor_label`, `who`,
#        `payer`) ham TAQIQLANADI.
#
#   (b)  Dalil — ⛔ **IDENTIFIKATOR**. `evidence_snapshot_ids` tipi
#        `list[UUID]`; imzolangan havola, obyekt kaliti yoki bayt YO'Q
#        (D-03, T-06-81). `list[str]` bo'lganda «bir marta imzolangan
#        havola qo'yaman» yo'li TIP darajasida ochiq qolardi — `UUID`
#        bilan u ⛔ **IMKONSIZ**.
# ---------------------------------------------------------------------------

RESOLUTION_NOTE_MAX = 2000
"""Yechim matnining server tomondagi uzunlik chegarasi (T-07-57).

⚠ QIYMAT SXEMANING `RESOLUTION_NOTE_LENGTH_CHECK` I BILAN BIR XIL BO'LISHI
  SHART. Bu yerda u HTTP qatlamining jufti: chegarasiz matn bazagacha
  borib `IntegrityError` bilan qaytardi va sabab «kodda xato» emas,
  «baza buzuq» kabi ko'rinardi (`transition()` ning nol-o'tish qarori
  bilan aynan bir xil mulohaza).

⛔ XSS BU YERDA HAL QILINMAYDI va u qilinishi ham kerak emas: React
   matnni avtomatik escape qiladi va `dangerouslySetInnerHTML`
   frontendda ISHLATILMAYDI (07-16). Serverda HTML tozalash uchinchi
   haqiqat manbai bo'lardi — «tozalangan» matn nizo hujjatida ASL
   matndan farq qilardi.
"""


class ReconciliationReportRow(BaseModel):
    """Kunlik hisobotning bitta nomuvofiqlik qatori (RECON-01, §8.1).

    =======================================================================
    ⛔⛔ IKKI SINF BITTA JADVALDA, LEKIN `subject_kind` BILAN AJRALGAN.

    `occupied_unpaid` — «band, lekin to'lovsiz»: hisob YOZILGAN, to'lov
    esa yetmagan. `anomaly` — «ro'yxatga olinmagan savdo»: hisob UMUMAN
    yozilmagan, chunki rasta biriktirilmagan (yoki kun yopiq edi).

    Farq maydonlarda ham KO'RINADI va bu ATAYIN: `anomaly` qatorida
    `expected_soum` ⛔ **`None`** — kutilgan summa mavjud EMAS, nol emas.
    Nol yozish «bu savdodan hech nima kutilmagan» degan YOLG'ON da'vo
    bo'lardi, holbuki haqiqat «qancha kutilishini tizim BILMAYDI»
    (D-13 ning `hit_rate is None` qarori bilan aynan bir sinf).
    =======================================================================

    ⚠ `case_id` / `status` `None` BO'LISHI MUMKIN va bu kontraktning
      ochiq e'tirofi: nomuvofiqlikning O'ZI `recon.open` yugurishidan
      OLDIN ham mavjud bo'ladi. Bugun hisobot qatorlari FAQAT case'lardan
      quriladi, ya'ni ikkala maydon ham to'lgan keladi; `| None` esa
      «case hali ochilmagan» holatini kontraktni buzmasdan qo'shish
      yo'lini ochiq qoldiradi.

    ⛔ `evidence_snapshot_ids` — modul izohidagi (b) taqig'i. Klient
       ularni ⛔ **MAVJUD** `GET /snapshots/{snapshot_id}/image`
       marshrutiga beradi va o'sha marshrut har ochilishda `audit_read`
       yozadi (04-11 qarori). ⛔ YANGI TASVIR MARSHRUTI OCHILMAYDI —
       5-fazada dalil-kadr yuzasi ATAYIN bitta marshrutda qulflangan
       (T-06-81) va bu faza uni KENGAYTIRMAYDI.
    """

    model_config = ConfigDict(extra="forbid")

    subject_kind: ReconciliationSubjectKind
    """⛔ YOPIQ DISKRIMINATOR (DQ-5) — «qaysi ustun bo'sh?» mantig'i EMAS."""
    case_id: UUID | None
    status: ReconciliationCaseStatus | None
    service_date: date
    stall_code: str
    vendor_id: UUID | None
    """⛔ IDENTIFIKATOR, ISM EMAS (modul izohidagi (a) taqig'i).

    `anomaly` sinfida `None` va bu MA'NOLI: `unassigned_occupied` ning
    butun mazmuni — rasta hech kimga biriktirilmagani.
    """
    expected_soum: int | None
    """Netlangan hisob summasi; `anomaly` sinfida ⛔ `None` (klass docstringi)."""
    paid_soum: int | None
    """`FIFO_OLDEST_SERVICE_DATE_FIRST` taqsimlagan qism (D-24).

    ⛔ HISOBLANMAYDI, BERILADI: qiymat `billing_repo.
    vendor_charge_allocation()` dan keladi. Uni bu yerda (yoki klientda)
    ayirish bilan chiqarish «to'landimi?» savolining IKKINCHI javobini
    tug'dirardi.
    """
    evidence_snapshot_ids: list[UUID]
    """⛔ FAQAT `UUID` — imzolangan havola, obyekt kaliti va bayt YO'Q."""


class ReconciliationReportResponse(BaseModel):
    """`GET /reconciliation/report?day=` — kunlik nomuvofiqlik hisoboti.

    ⛔ UCHALA HISOBLAGICH HAM NOL BO'LGANDA HAM QAYTADI
    (`ChargeListResponse` / `AnomalyListResponse` bilan AYNAN bir xil
    qaror): «bu kunda nomuvofiqlik yo'q» bilan «hisoblagich ishlamayapti»
    bir xil ko'rinsa direktor tizimni buzuq deb hisoblardi — va bu
    mahsulotning butun va'dasiga («raqamlar bilan ko'rsatamiz») zid
    bo'lardi.

    ⛔ IKKI SANOQ HECH QACHON QO'SHILMAYDI. `unpaid_count` va
       `unregistered_count` — IKKI BOSHQA hodisa (`AnomalyListResponse`
       ning D-05 qarori): birinchisi «pul kelmadi», ikkinchisi «savdo
       umuman yozilmadi». Yagona `total` maydoni ATAYIN yo'q, aks holda
       ekran uni ko'rsatardi va farq matn darajasida yo'qolardi.

    ⚠ `unpaid_expected_soum` FAQAT `occupied_unpaid` sinfi ustida
      yig'iladi va sabab yuqoridagi bilan bir xil: `anomaly` qatorining
      kutilgan summasi MAVJUD EMAS, ya'ni uni yig'indiga qo'shish
      KO'RINMAGAN HISOBDAN TUSHUM DA'VOSI to'qish bo'lardi.

    ⚠ `day` javobda ATAYIN bor: standart kun SERVERDA hisoblanadi
      (KECHA — §11.1) va klient qaysi kunni ko'rayotganini javobning
      O'ZIDAN biladi.
    """

    model_config = ConfigDict(extra="forbid")

    day: date
    rows: list[ReconciliationReportRow]
    unpaid_count: int
    """`occupied_unpaid` qatorlari soni — «band, lekin to'lovsiz»."""
    unregistered_count: int
    """`anomaly` qatorlari soni — «ro'yxatga olinmagan savdo». ⛔ QO'SHILMAYDI."""
    unpaid_expected_soum: int
    """FAQAT `occupied_unpaid` sinfining kutilgan summalari yig'indisi."""


class CaseRowResponse(BaseModel):
    """`GET /reconciliation/cases?day=` navbatining bitta qatori (RECON-02).

    ⛔ FAQAT IDENTIFIKATORLAR VA HOLAT (`reconciliation_repo.CaseRow`
       docstringining HTTP qatlamidagi jufti). Rasta kodi, sotuvchi nomi
       va summa BU YERDA YO'Q: ular hisobot marshrutidan yoki
       `daily_charges` / `billing_anomalies` ning O'Z marshrutlaridan
       olinadi. Ularni bu qatorga ko'chirish navbat ro'yxatini IKKINCHI
       haqiqat manbaiga aylantirardi.

    ⚠ `anomaly_id` / `charge_id` — ⛔ XOR: ikkalasidan AYNAN BITTASI
      to'ldirilgan (DQ-5, `ck_reconciliation_cases_subject_is_exclusive`).
      Klient shoxni `subject_kind` bo'yicha tanlaydi, «qaysi ustun
      bo'sh?» bo'yicha EMAS.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    subject_kind: ReconciliationSubjectKind
    anomaly_id: UUID | None
    charge_id: UUID | None
    service_date: date
    status: ReconciliationCaseStatus
    assignee_user_id: UUID | None
    """⛔ IDENTIFIKATOR, ISM EMAS. `None` = case hali hech kimga biriktirilmagan."""
    created_at: datetime


class CaseListResponse(BaseModel):
    """`GET /reconciliation/cases?day=` — kun kesimidagi navbat (DQ-4).

    =======================================================================
    ⛔⛔ ENVELOPE `ChargeListResponse` BILAN AYNAN BIR SHAKLDA: `day` +
        `rows` + hisoblagichlar (+ keyset kursori).

    Sabab `deferred-items.md` ning 2/4-bandida O'LCHANGAN: klient
    envelope'i serverdan orqada qolganda `z.strictObject` xatoni
    RENDER paytida emas, PARSE paytida beradi va ekran butunlay bo'sh
    qoladi. Ikki marshrut oilasi bir xil shaklda bo'lsa klient sxemasi
    birinchi kundan mos keladi.
    =======================================================================

    ⛔ TO'RTALA HISOBLAGICH HAM HAR DOIM QAYTADI va ular ⛔ `status`
       FILTRIDAN MUSTAQIL (`reconciliation_repo._CASE_COUNTS`
       docstringi): nazoratchi «yangi» filtrini yoqqanda «bugun nechta
       case yopildi?» savolining javobi o'zgarmasligi kerak. Filtrni
       hisoblagichlarga ham qo'llash tanlangan holatdan boshqa uchtasini
       NOLGA tushirardi va u «bugun hech nima yopilmadi» bilan MEXANIK
       ravishda bir xil ko'rinardi.

    ⚠ `next_cursor` — ATAYIN UNUMSIZ SATR (klient uni PARSE QILMAYDI):
      u serverga o'zgarmasdan qaytariladi. Kursorning ichki shakli
      (`created_at` + `id` juftligi) SERVER qarori va uni klientga
      ochish sahifalash qoidasini ikkiga bo'lardi.
    """

    model_config = ConfigDict(extra="forbid")

    day: date
    rows: list[CaseRowResponse]
    new_count: int
    in_review_count: int
    justified_count: int
    unjustified_count: int
    next_cursor: str | None
    """Keyingi sahifa kaliti; `None` — sahifa to'lmadi, ya'ni oxiri."""


class CaseEventRow(BaseModel):
    """Case tarixining bitta bo'g'ini (D-14).

    ⛔ TARIX — YANGI QATORLAR KETMA-KETLIGI, tahrirlangan qator EMAS.
       Jadval `0023` ning o'zgarmaslik triggeri bilan qulflangan, ya'ni
       nizoda (D-02) «kim, qachon, qaysi holatdan» savoliga javob
       beradigan qator YO'QOLMAYDI.

    ⛔ `actor_user_id` `None` = ⛔ **TIZIM**, «noma'lum» EMAS (`0022`
       qarori): case'ni `recon.open` cron'i ochadi va unga odam
       biriktirish «kim qaror qildi?» savoliga YOLG'ON javob bo'lardi.
       Ism `GET /users` dan klientda joinlanadi (modul izohidagi (a)).
    """

    model_config = ConfigDict(extra="forbid")

    from_status: ReconciliationCaseStatus | None
    """`None` = case TUG'ILDI: birinchi hodisada oldingi holat FIZIK ravishda yo'q."""
    to_status: ReconciliationCaseStatus
    actor_user_id: UUID | None
    note: str | None
    created_at: datetime


class CaseDetailResponse(BaseModel):
    """`GET /reconciliation/cases/{case_id}` — case + tarix + dalil.

    ⛔ DALIL — IDENTIFIKATOR (modul izohidagi (b) taqig'i). ⛔ BO'SH
       ro'yxat NORMAL JAVOB: hisobning dalili `day_close` yugurmagani
       uchun yozilmagan bo'lishi mumkin va klient bu holatda dalil
       bo'limini UMUMAN chizmaydi — na placeholder, na «bo'sh» yorlig'i
       (05-14 darsi).

    ⚠ `resolution_note` case'ning JORIY yechim matni; tarixdagi har bir
      `note` esa O'SHA QADAMNIKI. Ikkalasi bir-birini almashtirmaydi:
      matn qayta yozilganda eski qadamning izohi tarixda QOLADI.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    subject_kind: ReconciliationSubjectKind
    anomaly_id: UUID | None
    charge_id: UUID | None
    service_date: date
    status: ReconciliationCaseStatus
    assignee_user_id: UUID | None
    created_at: datetime
    resolution_note: str | None
    events: list[CaseEventRow]
    evidence_snapshot_ids: list[UUID]


class CaseUpdateRequest(BaseModel):
    """`PATCH /reconciliation/cases/{case_id}` tanasi (D-12, D-14).

    =======================================================================
    ⛔⛔ HOLAT — YOPIQ RO'YXAT, YECHIM MATNI — ERKIN. IKKISI ARALASHMAYDI.

    `ReconciliationCaseStatus` da `other` a'zosi ⛔ YO'Q va qo'shilmaydi,
    ya'ni erkin matn holat sifatida ⛔ KIRA OLMAYDI. Sabab
    `AdjustmentReason` (6-faza D-19 / T-06-07) bilan AYNAN bir sinfda:
    erkin matnli a'zo hisobotda GURUHLANMAYDI — u AMALDA eng katta guruh
    bo'lib qolardi va nomuvofiqlik navbatining haqiqiy natijasi HECH
    QACHON o'lchanmasdi (D-13 ning hit-rate maxraji ham shu yerda
    qulflanadi).

    Erkin matn esa `resolution_note` da yashaydi va u hisobotda
    GURUHLANMAYDI ham, o'lchanmaydi ham — u NIZO hujjati uchun.
    =======================================================================

    ⛔ `assignee_user_id` — IDENTIFIKATOR, ISM EMAS. `None` = «mas'ulni
       O'ZGARTIRMA», «egasiz qoldir» EMAS: `transition()` uni `COALESCE`
       bilan yangilaydi (07-07 SUMMARY, 5-ochiq band). Biriktirishni
       BEKOR QILISH amali bugun YO'Q va u qo'shilganda ALOHIDA argument
       bilan keladi.
    """

    model_config = ConfigDict(extra="forbid")

    status: ReconciliationCaseStatus
    resolution_note: Annotated[str, StringConstraints(max_length=RESOLUTION_NOTE_MAX)] | None = None
    assignee_user_id: UUID | None = None


class HitRateResponse(BaseModel):
    """`GET /reconciliation/hit-rate?from=&to=` — navbatning aniqligi (D-13).

    =======================================================================
    ⛔⛔ `hit_rate` — HOSILA, SAQLANGAN USTUN ⛔ EMAS.

    Nisbat `justified / (justified + unjustified)`. Maxrajga `new` va
    `in_review` ⛔ KIRMAYDI va sabab mexanik: hali ko'rilmagan case
    metrikani PASAYTIRARDI, ya'ni navbatni tez ko'rib chiqmaslik
    ko'rsatkichni yomonlashtirardi va ko'rsatkich o'z JARAYONINI o'lchash
    o'rniga uning KECHIKISHINI o'lchardi.

    ⛔ O'LCHOV YO'Q BO'LGANDA JAVOB `null`, `0.0` ⛔ EMAS. «Hali o'lchov
       yo'q» ≠ «nol aniqlik» — 5-fazaning Wilson qarori bilan aynan bir
       sinfda: o'lchanmagan sonning o'rniga nol yozish direktorning
       birinchi haftadagi qaroriga bevosita ta'sir qilardi.

    ⛔ `open_cases` YASHIRILMAYDI: usiz «hit-rate 100 %» javobi «hamma
       case ko'rildi» bilan «faqat bittasi ko'rildi, qolgan 74 tasi
       navbatda» ni MEXANIK ravishda bir xil ko'rsatardi.
    =======================================================================

    ⚠⚠ `hit_rate` — bu bo'limdagi ⛔ YAGONA `float` maydon va u ⛔ PUL
      EMAS, NISBAT. D-07 pul uchun `BIGINT` so'm ↔ `int` ni majburlaydi
      (kasrli tip tushum hisobida drift beradi va nizoga olib keladi);
      nisbat esa hech qachon jamlanmaydi va hech qachon so'mga
      aylantirilmaydi. Istisno shu yerda OCHIQ yoziladi, aks holda
      G7-8 darvozasining o'quvchisi uni D-07 buzilishi deb o'qirdi.
    """

    model_config = ConfigDict(extra="forbid")

    date_from: date
    date_to: date
    justified: int
    unjustified: int
    open_cases: int
    """`new` + `in_review` — ⛔ MAXRAJGA KIRMAYDI, lekin YASHIRILMAYDI ham."""
    hit_rate: float | None
    """⛔ `None` — «hali o'lchov yo'q». `0.0` bilan ALMASHTIRILMAYDI."""


# ---------------------------------------------------------------------------
# 07-16: XABAR YETKAZILISHI — DIREKTOR KO'RADIGAN YOZUV (BOT-04)
#
# ⛔⛔ BU IKKI MODELDA YUQORIDAGI UCH TAQIQ (a1)/(a)/(b) KUCHDA QOLADI VA
#     ULARGA TO'RTINCHISI QO'SHILADI:
#
#   (c) ⛔ XABARNING O'ZI JAVOBDA YO'Q. Na `payload` (unda summa va rasta
#       kodi bor), na tayyor MATN (u umuman SAQLANMAYDI — matn `kind` +
#       `payload` dan JO'NATISH paytida quriladi, Pitfall 6), na
#       `provider_message_id` (Telegram ning ichki identifikatori).
#
#       Sabab MAHSULOT darajasida: kvitansiya matnini yetkazilganlik
#       jadvalida takrorlash ⛔ IKKINCHI PUL YUZASI bo'lardi va u
#       yig'indiga olib borardi (07-UI-SPEC §11.3). `chat_id` esa
#       USTUN bo'lib ham mavjud emas (`outbox_repo` ning 4-majburiyati).
# ---------------------------------------------------------------------------


class DeliveryRow(BaseModel):
    """Yetkazilganlik jadvalining bitta qatori — ⛔ HOLAT VA VAQT (§11.3).

    =======================================================================
    ⛔⛔ MATN VA HOLAT ⛔ IKKI BOSHQA NARSA, VA JAVOBDA FAQAT HOLAT BOR.

    Bot API ning `sendMessage` javobi — `Message` obyekti (`message_id`,
    `date`); Telegram yetkazilganlik yoki o'qilganlik kvitansiyasini
    ⛔ UMUMAN BERMAYDI (Pitfall 2). Ya'ni `delivered` = «Telegram
    **200** qaytardi», ⛔ «foydalanuvchi o'qidi» EMAS. Shuning uchun bu
    modelda ⛔ `label` / `title` / `text` maydoni YO'Q: matn KLIENTDA,
    `recon.deliveryState.*` kalitlaridan quriladi va u uchala locale'da
    «Telegram qabul qildi» ma'nosini beradi (G-34).

    ⛔ SERVERDAN TAYYOR YORLIQ QAYTARISH TAQIQLANADI: matn serverga
       ko'chganda uch tilning biri backendda, ikkitasi frontendda
       yashardi — va `alerting.py:1003-1008` bu qarorni loyihada
       ALLAQACHON o'rnatgan (server i18n KALITINI beradi, matnni emas).
    =======================================================================

    ⚠ `updated_at` — OXIRGI HOLAT O'ZGARISHI. ⛔ `last_attempt_at` DEB
      NOMLANMAYDI: bunday USTUN `notification_outbox` da YO'Q va uni
      qo'shish migratsiya bo'lardi, holbuki mavjud qiymat aynan shu
      savolga javob beradi (`outbox_repo.DeliveryRow` docstringi).
    """

    model_config = ConfigDict(extra="forbid")

    outbox_id: UUID
    kind: OutboxKind
    """⛔ YOPIQ TO'PLAM — yorliq klientda, `NOTIFICATION_KINDS` reyestridan."""
    recipient_kind: OutboxRecipientKind
    vendor_id: UUID | None
    """⛔ IDENTIFIKATOR, ISM EMAS (modul izohidagi (a) taqig'i).

    `None` = direktorning xabari (`recipient_matches_vendor` buni ikki
    tomonlama majburlaydi).
    """
    status: OutboxStatus
    """⛔ YOPIQ ENUM — besh a'zo (D-20). `label` maydoni ⛔ YO'Q."""
    attempt_count: int
    created_at: datetime
    updated_at: datetime
    error_type: str | None
    """⛔ TUR NOMI (`type(exc).__name__`), xato MATNI ⛔ HECH QACHON (D-04).

    Telegram Bot API ning URL'i BOT TOKENINI tashiydi va `httpx`
    istisnosining matni to'liq URL'ni o'z ichiga oladi. Chegara
    `outbox_repo._validate_error_type()` da YOZISH paytida qo'yiladi,
    ya'ni bu ustunga matn UMUMAN tusha olmaydi.

    =======================================================================
    ⛔⛔ SIM USTUNI `last_error_type`, SIM MAYDONI `error_type` — VA FARQ
        ATAYIN, «unutish» EMAS.

    07-UI-SPEC §16.6 (**G-36**) `last_error` tokenini nomuvofiqlik
    yuzasida ⛔ **0** ga qulflaydi va taqiqning SABABI aynan ⛔ **xom
    istisno MATNI** (u bot tokenini tashiydi). Darvoza esa tokenni
    ⛔ **PREFIKS** sifatida qidiradi, ya'ni u `last_error_type` ni
    `last_error` dan ⛔ **AJRATA OLMAYDI**: xavfsiz maydon nomining
    O'ZI darvozani qizartirardi.

    ⛔ DARVOZAGA ISTISNO YOZILMADI (07-15 ning `hitRate*` -> `accuracy*`
       pretsedenti): «... dan tashqari» degan carve-out keyingi ijrochi
       tomonidan kengaytirilardi va reyestr asta-sekin bo'shashardi.
       Nomni o'zgartirish darvozani ⛔ **ISTISNOSIZ** qoldiradi.

    ⚠ Va yangi nom MAZMUNAN ham aniqroq: maydon «oxirgi xato» emas,
      «xatoning TURI» — `_type` qo'shimchasi bilan `last_` prefiksi
      bir narsani ikki marta aytardi.
    =======================================================================
    """
    error_status_code: int | None
    """HTTP status kodi (`429`, `400`, …). ⛔ `403` -> `blocked` (D-22).

    ⚠ Nomi `error_type` bilan JUFTLASHTIRILGAN: bir manbadan kelgan ikki
      maydon ikki xil prefiks bilan turishi o'quvchida «ular boshqa
      hodisadan» degan noto'g'ri taassurot qoldirardi.
    """


class DeliveryListResponse(BaseModel):
    """`GET /reconciliation/delivery?day=` — kunning yetkazilganlik yozuvi.

    =======================================================================
    ⛔⛔ BESHALA HISOBLAGICH HAM NOL BO'LGANDA HAM QAYTADI.

    `CaseListResponse` / `ChargeListResponse` / `AnomalyListResponse`
    bilan AYNAN bir xil qaror: «bu kunda bloklangan sotuvchi yo'q»
    bilan «hisoblagich ishlamayapti» bir xil ko'rinsa, direktor D-02
    nizosida («xabar kelmadi») noto'g'ri xulosaga kelardi — va aynan
    o'sha nizo uchun bu yuza qurilgan.

    ⛔ `blocked_count` ALOHIDA va u `failed_count` GA QO'SHILMAYDI
       (D-22): blok — sotuvchining HUQUQI va qarz undirish jarayonining
       bir qismi, texnik nosozlik EMAS. Ikkalasini bitta songa qo'shish
       aloqa uzilishini nosozlik shovqiniga ko'mib yuborardi va
       direktor «bevosita bog'laning» degan yagona foydali qadamni
       topa olmasdi.
    =======================================================================

    ⛔ YOZISH MARSHRUTI YO'Q: bu yo'lda `POST` / `PATCH` / `DELETE`
       ⛔ UMUMAN yozilmagan (append-only, D-20). Qo'lda `delivered`
       qo'yish nizoda SOXTA DALIL bo'lardi, `[Qayta yuborish]` esa
       `uq_notification_outbox_market_id_dedupe_key` bilan
       to'qnashardi yoki uni aylanib o'tib IKKINCHI kvitansiya
       yuborardi (07-UI-SPEC §17.2).

    ⚠ `day` javobda ATAYIN bor: standart kun SERVERDA hisoblanadi
      (⛔ **BUGUN** — §4.4/§5.4: kvitansiya HOZIR ketadi va nizo O'SHA
      KUNI chiqadi) va klient qaysi kunni ko'rayotganini javobning
      O'ZIDAN biladi. ⚠ Bu `GET /reconciliation/report` DAN farq
      qiladi (u yerda standart KECHA) va farq MAHSULOT qarori:
      hisobot D+1 04:10 da tug'iladi, yetkazilganlik esa BUGUN kerak.
    """

    model_config = ConfigDict(extra="forbid")

    day: date
    rows: list[DeliveryRow]
    pending_count: int
    sent_count: int
    delivered_count: int
    failed_count: int
    blocked_count: int
    """⛔ `failed_count` GA QO'SHILMAYDI — klass docstringi (D-22)."""
    next_cursor: str | None
    """Keyingi sahifa kaliti; `None` — sahifa to'lmadi, ya'ni oxiri."""


# ---------------------------------------------------------------------------
# 08-07: DAVR HISOBOTLARINING JAVOB O'RAMLARI (RECON-04)
#
# =============================================================================
# ⛔⛔ MAYDON NOMLARI FRONTEND KONTRAKTIDAN, «tabiiy» tanlovdan EMAS.
#
# `frontend/src/lib/api-types.ts` (08-03, TO'LQIN 1) uchala o'ramni ham
# ⛔ `z.strictObject` bilan e'lon qilgan, ya'ni javobda KUTILMAGAN maydon
# bo'lsa klient PARSE CHEGARASIDA yiqiladi va direktor hisobot o'rniga
# BO'SH EKRAN ko'radi. Shuning uchun bu yerdagi har maydon o'sha
# sxemaning AYNAN jufti — ortiqchasi ham, kamchisi ham nosozlik.
#
# ⚠ Ya'ni `report_repo` BERADIGAN, lekin kontraktda YO'Q maydonlar
#   (`payment_count`, `charge_count`, arxivning `amount_soum` i) bu
#   yuzada ATAYIN E'LON QILINMAYDI. Ular repo qatlamida qoladi va
#   `.xlsx` eksporti (08-12) ularni bu DTO'dan emas, repodan oladi.
#
# =============================================================================
# ⛔ `from_date` / `to_date` UCHALA O'RAMDA HAM MAJBURIY (UI-SPEC §8.7, G-39).
#
# Ekran davr jumlasini SERVERNING javobidan chizadi, `nuqs` holatidan
# EMAS: server so'ralgan davrni qisqartirgan bo'lsa, so'ralganini chizish
# «men oktyabrni so'radim, oktyabr ko'rsatildi» degan YOLG'ON tasdiq
# berardi — va u ekranda tuzatiladigan, FAYLDA esa tarqaladigan xato.
#
# ⛔ `row_count` — BUTUN DAVRNIKI, `shown_count` — ko'rinayotgan sahifaniki
#    (§8.6). Ikkalasi ham MAJBURIY: usiz direktor ekrandagi qatorlarni
#    butun davr deb o'qirdi. Yig'indi maydonlari ham SERVERDAN — klient
#    `reduce` QILMAYDI (D-03).
# ---------------------------------------------------------------------------


class RevenueReportRow(BaseModel):
    """Tushum hisobotining bir KUNI (§8.2).

    ⛔ `diff_soum` SERVERDAN keladi va klientda `collected − charged`
       QAYTA HISOBLANMAYDI (D-03). Klientdagi qayta hisob xato bo'lib
       emas, IKKINCHI JAVOB bo'lib chiqadi — va nizoda «qaysi son
       to'g'ri?» savoli javobsiz qolardi.

    ⚠ BELGI KONVENSIYASI: manfiy — KAM yig'ilgan (patta yozilgan, pul
      kelmagan); musbat — ortiqcha to'lov (u ham HOLAT, xato emas:
      sotuvchi eski qarzini yopgan bo'lishi mumkin).

    ⛔ `payment_count` / `charge_count` bu yerda E'LON QILINMAGAN garchi
       `report_repo.RevenueRow` ularni BERSA ham — blok boshidagi
       birinchi bandning sababi.
    """

    model_config = ConfigDict(extra="forbid")

    business_date: date
    collected_soum: int
    charged_soum: int
    diff_soum: int


class RevenueReportResponse(BaseModel):
    """`GET /reports/revenue?from=&to=` — davr tushumi.

    ⛔ IKKI YIG'INDI ALOHIDA va UCHINCHI, «yagona tushum» maydoni YO'Q
       (`report_repo.RevenueRow` docstringi, T-08-15): `collected` —
       KASSA kuni, `charged` — PATTA kuni. Farqning O'ZI RECON-04 ning
       qiymati.
    """

    model_config = ConfigDict(extra="forbid")

    from_date: date
    to_date: date
    rows: list[RevenueReportRow]
    total_collected_soum: int
    total_charged_soum: int
    row_count: int
    shown_count: int


class LiveRevenueResponse(BaseModel):
    """`GET /reports/live?from=&to=` — ⛔ PANEL uchun, HUJJAT uchun EMAS.

    =======================================================================
    ⛔⛔ NEGA `GET /reports/revenue` DAN AYRIM MARSHRUT.

    `/reports/revenue` BUGUNGI kunni **422 `report_period_future`** bilan
    rad etadi va bu TO'G'RI: `daily_charges` D+1 04:10 da tug'iladi
    (`BILLING_CLOSE_CRON`, C-3), ya'ni bugunni qamragan hisobot bugungi
    TO'LOVNI ko'rsatib, bugungi PATTANI ko'rsatmasdi — natija kam
    ko'rsatilgan `charged_soum` va sun'iy musbat farq bo'lardi. Va u
    ekranda qolmasdi: aynan o'sha javob imzolanadigan `.xlsx` ga tushadi.

    Lekin DIREKTOR PANELI boshqa savolga javob beradi — «hozir qanday
    ketyapti». Panelning «Bugun / 7 kun / 30 kun» filtrlari BUGUN bilan
    tugaydi, ya'ni to'rttadan uchtasi hech qachon pul ko'rsata olmasdi
    va panel buzuq bo'lib ko'rinardi [jonli o'lchandi 260819].

    ⛔ SHUNING UCHUN AJRATILDI, CHEGARA YUMSHATILMADI:
       · `/reports/revenue` VA uning `.xlsx` juftlari TEGILMAGAN —
         imzolanadigan hujjat hamon faqat YOPILGAN kunlardan quriladi;
       · bu marshrutning `.xlsx` JUFTI YO'Q va u QO'SHILMAYDI. Shu
         sabab «ekranda tuzatilgan xato faylda tarqaydi» xavfi bu
         yerda strukturaviy ravishda mavjud emas.

    ⛔ `charged_complete` — JAVOBNING O'ZI ROSTGO'YLIGINI AYTADI.
       Davr bugunni qamrasa u `false` bo'ladi va klient patta
       yig'ilish DARAJASINI (yig'ilgan / hisoblangan) CHIZMASLIGI
       kerak: nomukammal maxrajdan chiqqan foiz hokimga ko'rsatiladigan
       ekrandagi eng qimmat yolg'on bo'lardi. Yig'ilgan pul esa
       to'lovlardan real vaqtda o'qiladi va u HALOL.
    =======================================================================
    """

    model_config = ConfigDict(extra="forbid")

    from_date: date
    to_date: date
    total_collected_soum: int
    total_charged_soum: int
    charged_complete: bool


class ReceivablesReportRow(BaseModel):
    """Qarzdorlik reestrining bir qatori — ⛔ SOTUVCHI kesimida (§8.3).

    =======================================================================
    ⛔⛔ `vendor_name` BOR VA U BU YUZADA QONUNIY — 7-FAZADAGI TAQIQNING
        TESKARISI (§5.5 ↔ D-07).

    `/billing/charges` va `/reconciliation/cases` — OPERATIV moliyaviy
    javoblar va ularga ism QO'SHILMAYDI (C-10). Bu esa HUJJAT: uning
    butun mavjud bo'lish sababi «kimdan undirish kerak?» savoliga
    qog'ozda javob berish. Shuning uchun ism SERVERDA joinlanadi va
    marshrut `VENDOR_VIEW` + `audit_read` talab qiladi.

    ⛔ `phone` YO'Q va qo'shilmaydi (UI-SPEC O-03): telefon — ALOQA
       ma'lumoti, u hujjatga tushib fayl bo'lib tarqalardi. Qarz
       undirish oqimi ALLAQACHON bot eslatmasi (BOT-03).
    =======================================================================

    ⛔ `vendor_name` `None` bo'lishi MUMKIN va u ekranda BO'SH KATAK
       bo'lib chiziladi (D-08): na «—», na «Noma'lum», na «Sotuvchi
       #123». To'qilgan qiymat ma'lumot bordek ko'rinadi va EKSPORTGA
       ham tushadi — chop etilgan varaqda «Noma'lum» qatori buxgalter
       uchun HAQIQIY nom bo'lib o'qilardi (05-14 darsi).

    ⚠ `stall_codes` — ⛔ RO'YXAT, vergul bilan yopishtirilgan SATR EMAS.
      `report_repo` uni `string_agg` bilan bitta satr qilib beradi
      (`code_sort` tartibida), klient esa har kodni ALOHIDA element
      sifatida chizadi — satrni klientda `split` qilish tartibni ham,
      bo'sh holatni ham klient qaroriga qoldirardi.
    """

    model_config = ConfigDict(extra="forbid")

    vendor_id: UUID | None
    vendor_name: str | None
    stall_codes: list[str]
    outstanding_soum: int
    oldest_debt_date: date | None
    """Eng eski TO'LANMAGAN `service_date` — `None` = to'lanmagan hisob yo'q.

    ⚠ Davr bilan CHEKLANMAYDI (`report_repo.receivables()` docstringi):
      eng eski to'lanmagan kun davrdan OLDIN bo'lishi mumkin va uni
      kesish QARZNING YOSHINI yashirardi.
    """


class ReceivablesReportResponse(BaseModel):
    """`GET /reports/debtors?from=&to=` — qarzdorlik reestri.

    ⛔ Qarzi NOLDAN FARQLI sotuvchilar, qarz bo'yicha KAMAYISH
       tartibida (tartib SERVERDA — `.xlsx` eksporti shu ro'yxatni
       bayt-bayt yozadi va ikkinchi saralash ekrandagi tartib bilan
       fayldagi tartibni ajratardi).
    """

    model_config = ConfigDict(extra="forbid")

    from_date: date
    to_date: date
    rows: list[ReceivablesReportRow]
    total_outstanding_soum: int
    row_count: int
    shown_count: int


class AnomalyArchiveRowResponse(BaseModel):
    """Nomuvofiqlik arxivining bir qatori (§8.5).

    ⛔ DALIL — IDENTIFIKATOR, KADR EMAS (07 D-03, T-06-81):
       `snapshot_id` bor, baytlar YO'Q; ombor kaliti ham, imzolangan
       havola ham yo'q. Sabab huquqiy va u muzokara qilinmaydi: kadrda
       tashrifchilar yuzi bor (O'zR shaxsiy ma'lumotlar qonuni).

    ⚠ `kind` — `report_repo.ARCHIVE_KIND_UNPAID` yoki
      `ARCHIVE_KIND_UNREGISTERED`; qiymat ENUMDAN keladi, bu yerda
      yangi lug'at IXTIRO QILINMAYDI.

    ⚠ `case_status` `None` = case hali OCHILMAGAN («noma'lum» emas).
    """

    model_config = ConfigDict(extra="forbid")

    business_date: date
    """⛔ Manbada u `service_date` — PATTA kuni, kassa kuni EMAS.

    Nom klient kontraktidan (`anomalyArchiveRowSchema`); ma'no esa
    `report_repo` niki va u aralashtirilmaydi (Pitfall 14).
    """
    kind: str
    stall_code: str
    snapshot_id: UUID | None
    case_status: str | None


class AnomalyArchiveResponse(BaseModel):
    """`GET /reports/anomalies?from=&to=` — nomuvofiqlik arxivi.

    ⛔⛔ IKKI SANOQ ALOHIDA va ularning YIG'INDISI maydon sifatida
        MAVJUD EMAS (6-faza D-05, `AnomalyCounts` naqshi). «Band, lekin
        to'lovsiz» UNDIRISHNI, «ro'yxatga olinmagan savdo» esa
        RO'YXATGA OLISHNI talab qiladi — bitta songa siqilgan hisobot
        qaysi sinf o'sganini YASHIRARDI.

    ⛔ NOL SANOQ HAM NATIJA: ikkala hisoblagich ham har doim qaytadi.
    """

    model_config = ConfigDict(extra="forbid")

    from_date: date
    to_date: date
    rows: list[AnomalyArchiveRowResponse]
    unpaid_count: int
    unregistered_count: int
    row_count: int
    shown_count: int


class ThreeWayReportRow(BaseModel):
    """Uch tomonlama solishtiruvning bir qatori (§10.4, D-18).

    =========================================================================
    ⛔⛔ MAYDONLAR TO'PLAMI KLIENT KONTRAKTIDAN: `api-types.ts::
        threeWayRowSchema` — `z.strictObject`. Unda `vendor_name` ham,
        `stall_id` ham YO'Q va ikkalasi ham bu yerga QO'SHILMAYDI:
        `strictObject` ortiqcha maydonni RAD ETADI, ya'ni «qulaylik
        uchun» qo'shilgan ustun butun sahifani PARSE chegarasida
        yiqitardi (nosozlik faqat jonli ekranda ko'rinardi).

    ⛔ SOTUVCHI ISMI FAQAT `.xlsx` HUJJATIGA CHIQADI va bu ONGLI qaror
       (D-07 ning aynan shakli): ekrandagi jadval rasta kesimida
       ishlaydi, imzolanadigan hujjatda esa «kimdan so'raladi?» savoli
       qog'ozda javob olishi kerak. Ismni bu modelga qo'shish marshrutni
       `PERSONAL_ROUTES` ga ham tortardi — ya'ni har hisobot ochilishida
       `audit_read` yozilardi va HAQIQIY o'qish hodisasi (`/debtors`)
       shovqin ichida ko'milardi.
    =========================================================================

    `ai_expected_soum` — ⛔ `None` va `0` IKKI XIL NARSA (§10.4):
        `0` = «AI rastani BO'SH dedi» (O'LCHANGAN);
        `None` = «o'sha kun uchun bandlik ma'lumoti yo'q» (O'LCHANMAGAN).
        Ekranda birinchisi chizilgan nol, ikkinchisi BO'SH KATAK.

    `diff_class` — ⛔ `None` = BADGE YO'Q. Klient reyestri
        (`DIFF_CLASSES`) AYNAN UCH a'zoli va `match` unda ATAYIN yo'q:
        mos qator bezak OLMAYDI (§13.4). Serverdagi to'rtinchi sinf
        (`report_repo.DIFF_MATCH`) shu sababdan `None` ga o'giriladi va
        o'girish `api/v1/reports.py` da, BIR joyda bajariladi.
    """

    model_config = ConfigDict(extra="forbid")

    stall_code: str
    ledger_soum: int
    system_soum: int
    ai_expected_soum: int | None
    diff_class: str | None


class ThreeWayReportResponse(BaseModel):
    """`GET /reports/compare?day=` — kunning uch tomonlama solishtiruvi (SC#5).

    =========================================================================
    ⛔⛔ «JAMI FARQ» MAYDONI YO'Q VA QO'SHILMAYDI (D-18, UI-SPEC §10.5).

    Uch farq sinfi uch BOSHQA harakatni talab qiladi — «pulni qidiring»
    (`ledger_over`), «daftarni tuzating» (`system_over`), «detektorni
    tekshiring» (`ai_mismatch`). Bitta songa siqilgan hisobot qaysi sinf
    o'sganini YASHIRARDI va solishtiruvni foydasiz qilardi (6-faza D-05
    va 07 Pattern 4 ning aynan sinfi).

    ⚠ TO'RT SANOQNING YIG'INDISI `len(rows)` GA TENG EMAS va bu
      NOSOZLIK EMAS: AI-kutilgani o'lchanmagan, daftar va tizimi mos
      qator BIRORTA sanoqqa tushmaydi (`report_repo._THREE_WAY`).
    =========================================================================

    ⛔ `has_ledger is False` — jadval UMUMAN chizilmaydi (§10.6) va
       `rows` BO'SH keladi. Daftar yuklanmagan kunda uch ustunli
       jadvalni «hamma farq 0» bilan chizish MUVAFFAQIYATLI solishtiruv
       bo'lib ko'rinardi va IMZOLANARDI — SC#5 ning butun maqsadi
       jimgina yo'qolardi.

    ⛔ SAHIFALASH YO'Q (R-8): `limit`/`offset` parametrlari ATAYIN
       mavjud emas va shuning uchun `row_count`/`shown_count` juftligi
       ham yo'q (davr hisobotlaridan FARQLI). Kun bitta javobda keladi,
       sig'masa `422 report_too_large` bilan RAD ETILADI —
       sahifalangan hujjatni IMZOLAB bo'lmaydi.
    """

    model_config = ConfigDict(extra="forbid")

    day: date
    has_ledger: bool
    rows: list[ThreeWayReportRow]
    ledger_over_count: int
    system_over_count: int
    ai_mismatch_count: int
    matched_count: int


class LedgerImportResponse(BaseModel):
    """`POST /reports/compare/ledger?day=` — kunlik daftar importining natijasi (D-17).

    ⛔⛔ MAYDONLAR TO'PLAMI KLIENT KONTRAKTIDAN: `api-types.ts::
        ledgerImportResultSchema` — `z.strictObject({day, rows, replaced})`.
        `strictObject` ORTIQCHA maydonni ham RAD ETADI, ya'ni bu yerga
        «qulaylik uchun» qo'shilgan to'rtinchi maydon klientda import
        muvaffaqiyatli bo'lgan holatda ham XATO bo'lib ko'rinardi.

    ⛔ `replaced` — MANTIQIY (`bool`), SANOQ EMAS. Ekranda javob bitta
       savolga kerak: «shu kun uchun daftar ALMASHTIRILDIMI?» (§14.8 dagi
       tasdiq dialogining natijasi). Almashtirilgan qatorlarning SONI
       auditga yoziladi — u yerda savol boshqa: «nima o'zgardi?».

    ⚠ `rows` — YOZILGAN qatorlar soni, fayldagi qatorlar soni EMAS.
      Bugungi kunda ular teng (validator xato bo'lsa HECH NARSA
      yozilmaydi), lekin nom YOZILGANNI aytadi va u shunday qoladi.
    """

    model_config = ConfigDict(extra="forbid")

    day: date
    rows: int
    replaced: bool
