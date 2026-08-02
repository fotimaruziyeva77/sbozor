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

from datetime import date, datetime
from typing import Annotated, Any, Final
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator
from sbozor_core.enums import Locale, Role, StallStatus
from sbozor_core.money import MAX_SAFE_SOUM
from sbozor_core.phone import InvalidPhoneError, normalize_phone

__all__ = [
    "AUDIT_PAGE_SIZE_MAX",
    "IMPORT_ERROR_REPORT_MAX",
    "ISO_WEEKDAYS",
    "MARKET_ERROR_CODES",
    "MIN_PASSWORD_LENGTH",
    "STALL_PAGE_SIZE_MAX",
    "VENDOR_PAGE_SIZE_MAX",
    "VENDOR_STALL_CODES_MAX",
    "AssignmentCloseRequest",
    "AssignmentCreateRequest",
    "AssignmentItem",
    "AssignmentListResponse",
    "AuditEntry",
    "AuditListResponse",
    "AuditQuery",
    "BlockingItem",
    "CalendarException",
    "CalendarExceptionRequest",
    "CalendarResponse",
    "CategoryItem",
    "CategoryListResponse",
    "CategoryRequest",
    "ChangePasswordRequest",
    "CreateUserRequest",
    "CreateUserResponse",
    "ImportErrorItem",
    "ImportErrorReportRequest",
    "ImportErrorResponse",
    "ImportResultResponse",
    "LocaleResponse",
    "LoginRequest",
    "LoginResponse",
    "MapCell",
    "MapZone",
    "MarketCreateRequest",
    "MarketCreateResponse",
    "MarketListItem",
    "MarketRef",
    "MeResponse",
    "ProfileResponse",
    "RefreshResponse",
    "ResetPasswordResponse",
    "SelectMarketRequest",
    "SessionResponse",
    "SetupStatusResponse",
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
    "VendorListItem",
    "VendorListResponse",
    "VendorQuery",
    "VendorRequest",
    "VendorUpdateRequest",
    "ZoneItem",
    "ZoneListResponse",
    "ZoneRequest",
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

    ⚠ KOORDINATA HAM YO'Q (D-19): joylashuv avtomatik (CSS Grid), ya'ni
    hech kim rastalarni qo'lda joylashtirmaydi va saqlanadigan `x`/`y`
    bo'lmagani uchun ular eskirib ham qolmaydi.
    """

    id: UUID
    code: str
    status: StallStatus
    has_vendor: bool


class MapZone(BaseModel):
    """Xaritadagi zona bloki — kataklar `code_sort` TARTIBIDA keladi.

    `name` — DB kontenti va TARJIMA QILINMAYDI (1-faza D-16).
    """

    id: UUID
    name: str
    cells: list[MapCell]


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
