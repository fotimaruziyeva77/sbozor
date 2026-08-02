"""Cross-tenant marshrut matritsasi — FOUND-02 ning yakuniy isboti (T-01-75…T-01-79).

=============================================================================
BU FAYLNING ENG MUHIM XUSUSIYATI: MARSHRUTLAR RO'YXATI QO'LDA YOZILMAYDI.

`tenant_resource_routes(app)` ro'yxatni **`app.routes`** dan oladi. Qo'lda
yozilgan ro'yxat bilan farq quyidagicha bo'lardi: 01-06 rejasi `GET
/api/v1/auth/me` ni REJADA BO'LMAGAN holda qo'shdi (deviatsiya #3). Qo'lda
yuritilgan ro'yxatga uni kim qo'shishi kerak edi? Hech kim — va u
tekshiruvdan TASHQARIDA qolardi, hech qanday test qizarmasdan. Avtomatik
ro'yxat esa uni o'sha kuniyoq qamrab oladi.

JAVOB HAR DOIM 404, 403 EMAS (T-01-76). 403 javobining O'ZI "bunday obyekt
bor, lekin sizniki emas" degan ma'lumotni oshkor qiladi — ya'ni hujumchi
mavjud ID'larni javob kodi bo'yicha sanab chiqa oladi. RLS ostida o'sha
qator boshqa bozor uchun MAVJUD EMAS, shuning uchun 404 yolg'on emas,
aynan haqiqat. Har testda `status != 403` ALOHIDA assert qilinadi.

TOKEN QO'LDA YASALMAYDI. Har bir sessiya `POST /auth/login` (+ kerak
bo'lsa `POST /auth/select-market`) orqali olinadi — ya'ni matritsa
mahsulot oqimining O'ZINI sinaydi. Qo'lda `encode_access()` bilan yasalgan
token login oqimidagi har qanday nosozlikni yashirardi. Yagona istisno —
muddati o'tgan token testi, u yerda `exp` ni boshqa yo'l bilan buzib
bo'lmaydi.
=============================================================================

QAMROV DARVOZASI `test_route_coverage.py` da: bu yerdagi yordamchilar
(`tenant_resource_routes`, `EXEMPT_ROUTES`, `PARAM_FILLERS`) o'sha faylda
qayta ishlatiladi va tasniflanmagan marshrut CI'ni yiqitadi.
"""

from __future__ import annotations

import io
from datetime import date, timedelta
from itertools import count
from typing import TYPE_CHECKING, Any, NamedTuple
from uuid import UUID

import pytest
import xlsxwriter
from app.main import app as fastapi_app
from fixtures.admin_api import AUDIT_URL, USERS_URL, bearer, session_headers
from fixtures.market_domain import A_CATEGORY_NAMES, A_ZONE_NAMES
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.security import encode_access

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures.market_domain import MarketDomainSeed
    from fixtures.two_markets import TwoMarketSeed

pytestmark = pytest.mark.tenancy

__all__ = [
    "BODY_FILLERS",
    "EXEMPT_ROUTES",
    "FILE_FILLERS",
    "PARAM_FILLERS",
    "RouteSpec",
    "TenantSeed",
    "all_routes",
    "parametrized_routes",
    "tenant_resource_routes",
]


class RouteSpec(NamedTuple):
    """Bitta HTTP marshrut: metod + shablon yo'l (`/api/v1/users/{user_id}/block`)."""

    method: str
    path: str

    @property
    def test_id(self) -> str:
        """`pytest -k` uchun o'qiladigan nom: `POST_/api/v1/users/{user_id}/block`."""
        return f"{self.method}_{self.path}"

    @property
    def param_names(self) -> tuple[str, ...]:
        """Yo'ldagi `{...}` parametrlarining nomlari."""
        return tuple(chunk.split("}", 1)[0] for chunk in self.path.split("{")[1:] if "}" in chunk)


class TenantSeed(NamedTuple):
    """Matritsa uchun IKKI qatlamli seed: a'zolik (1-faza) + domen (2-faza).

    NEGA BIRLASHTIRILDI: `PARAM_FILLERS` to'ldiruvchilari HAQIQIY B bozori
    obyektlarini qaytarishi shart, `user_id` esa `two_markets` da,
    `zone_id`/`category_id`/`stall_id` esa `market_domain` da yashaydi.
    Ikkita alohida argument bilan har bir filler ikkita seed qabul
    qilardi va imzo o'zgarganda o'nlab joy tahrirlanardi.

    `market_domain` `two_markets` USTIGA qatlanadi (u fixture argumenti
    sifatida oladi), ya'ni bu yerdagi ikkala maydon ham AYNI bozor
    UUID'lariga tegishli.
    """

    base: TwoMarketSeed
    domain: MarketDomainSeed


EXEMPT_ROUTES: dict[str, str] = {
    # --- health: autentifikatsiyasiz, hech qanday tenant ma'lumoti yo'q ---
    "/healthz": "health — autentifikatsiyasiz liveness, tenant ma'lumoti qaytarmaydi",
    "/readyz": "health — autentifikatsiyasiz readiness, tenant ma'lumoti qaytarmaydi",
    # --- OpenAPI/hujjat yuzasi: statik sxema, ma'lumot emas ---
    "/api/openapi.json": "global — statik OpenAPI sxemasi, tenant qatorlari yo'q",
    "/api/docs": "global — Swagger UI sahifasi, tenant qatorlari yo'q",
    "/docs/oauth2-redirect": "global — Swagger OAuth2 redirect stub, ma'lumot qaytarmaydi",
    "/redoc": "global — ReDoc sahifasi, tenant qatorlari yo'q",
    # --- auth bootstrap: bu yerda tenant konteksti HALI YO'Q ---
    "/api/v1/auth/login": "auth bootstrap — bozor login NATIJASIDA aniqlanadi (Pitfall 3)",
    "/api/v1/auth/select-market": "auth bootstrap — bozorni AYNAN shu endpoint tanlaydi (D-06)",
    "/api/v1/auth/refresh": "auth bootstrap — cookie kelganda bozor noma'lum, `mid` claim yo'q",
    "/api/v1/auth/logout": "auth bootstrap — sessiyani yopadi, tenant ma'lumoti qaytarmaydi",
    "/api/v1/auth/change-password": "auth bootstrap — parol PROFILGA tegishli, bozorga emas",
    # --- global: tenant chegarasidan tashqari ---
    "/api/v1/me": "global — profil (ism, til) bozorga tegishli emas va bozorsiz ishlaydi (D-13)",
    "/api/v1/markets": (
        "global — bozorlar ro'yxati FAQAT haqiqiy platforma adminiga "
        "(`users.is_platform_admin` bayrog'i) ochiladi, gibrid huquqli hisobga EMAS (CR-03); "
        "IKKALA metod ham shu istisnoga tushadi — `POST` yangi bozor yaratadi va o'sha "
        "chaqiruvda tenant konteksti PRINSIPIAL ravishda mavjud emas (identifikator aynan "
        "javob natijasida tug'iladi), ya'ni unda 'boshqa bozorning obyekti' tushunchasining "
        "o'zi yo'q"
    ),
    "/api/v1/audit/platform": (
        "global — platforma-global (`market_id IS NULL`) audit qatorlari, ya'ni "
        "HECH QAYSI bozorga tegishli bo'lmagan yozuvlar; tenant qatorlari undan "
        "hech qachon qaytmaydi va darvoza `users.is_platform_admin` bayrog'i"
    ),
}
"""Cross-tenant matritsasidan CHIQARILGAN marshrutlar — har biri SABAB bilan.

Sabab satri MAJBURIY (`test_exempt_routes_have_reason`). Sababsiz istisno
"bu yerda tekshirish qiyin edi" degan qarorni hujjatsiz qoldiradi va
keyingi o'qiyotgan odam uni xavfsiz deb qabul qiladi.

Uchta ruxsat etilgan sabab turi:
  * `auth bootstrap` — tenant konteksti hali mavjud emas;
  * `global`         — resurs tenant chegarasidan tashqarida;
  * `health`         — autentifikatsiyasiz, ma'lumot qaytarmaydi.

`/api/v1/markets` istisnosining SABABI 01-11 da qayta yozildi. Istisnoning
o'zi qonuniy va QOLADI (platforma admini barcha bozorlarni ko'rishi —
D-06 bozor tanlash yuzasi), lekin eski asos ("platforma admini uchun")
`MARKET_VIEW_ALL` HUQUQIGA tayangan edi, huquq esa a'zolik roli orqali
qo'lga kiritilardi (CR-03). Endi branch `users.is_platform_admin`
bayrog'ida va istisno faqat shu bayroqni qamraydi. Bayroqsiz, lekin
huquqli hisob uchun regressiya darvozasi —
`tests/integration/test_me_locale.py::test_market_view_all_without_the_flag_sees_only_its_own_market`.

DIQQAT — ISTISNO MARSHRUTNI MATRITSADAN TO'LIQ CHIQARADI, faqat
"404 qaytarsin" da'vosidan emas: tokensiz/buzilgan/muddati o'tgan token
testlari ham unga qo'llanmaydi. `/api/v1/audit/platform` uchun o'sha
qamrov `tests/integration/test_audit_platform.py` da AYNAN qayta
tiklangan (tokensiz -> 401; `is_platform_admin=false` -> 403; gibrid
`platform_admin` a'zolik roli -> 403; javobda tenant qatorlari YO'Q).
Istisno qo'shgan odam bu qamrovni ham ko'chirishi SHART — aks holda
marshrut "istisno" degan so'z bilan butunlay sinovsiz qolardi.
"""

EXEMPT_REASON_PREFIXES = ("auth bootstrap", "global", "health")
"""Ruxsat etilgan sabab toifalari (`test_exempt_reasons_use_a_known_category`)."""


PARAM_FILLERS: dict[str, Callable[[TenantSeed], str]] = {
    "user_id": lambda seed: str(seed.base.market_b.cashier_user_id),
    # --- 2-faza domen obyektlari ---
    #
    # ⚠ HAR BIR QIYMAT B BOZORINING HAQIQIY OBYEKT ID'SI BO'LISHI SHART,
    # tasodifiy UUID EMAS. Sabab matritsaning butun ma'nosiga tegadi:
    # tasodifiy UUID uchun javob "bunday obyekt yo'q" degani bo'lardi va
    # 404 hech nimani isbotlamasdi — biz esa aynan "obyekt BOR, lekin
    # boshqa bozorniki" holatini sinayapmiz. `test_param_fillers_point_at
    # _the_other_market` bu qoidani doimiy qulflaydi.
    "zone_id": lambda seed: str(seed.domain.market_b.zone_ids[0]),
    "category_id": lambda seed: str(seed.domain.market_b.category_ids[0]),
    "stall_id": lambda seed: str(seed.domain.market_b.stall_ids[0]),
    "tariff_id": lambda seed: str(seed.domain.market_b.tariff_ids[0]),
    # B bozorining YAGONA kalendar istisnosi. A ga ATAYIN istisno
    # qo'shilmagan (`fixtures/market_domain.B_HOLIDAY` docstringi), ya'ni
    # bu filler haqiqatan "boshqa bozorning qatori" ni ko'rsatadi.
    "exception_id": lambda seed: str(seed.domain.market_b.calendar_exception_ids[0]),
    # --- 02-10: sotuvchi va biriktirish ---
    #
    # B bozorining YAGONA sotuvchisi va uning YAGONA OCHIQ biriktirish
    # davri (`B_ASSIGNMENT_START` dan boshlab). Davr ochiqligi ahamiyatli:
    # `PATCH /assignments/{id}` yopiq davr uchun 409 `assignment_not_open`
    # berardi va matritsa 404 kutayotgan joyda yiqilardi — ya'ni tenant
    # darvozasi emas, holat darvozasi sinalgan bo'lardi.
    "vendor_id": lambda seed: str(seed.domain.market_b.vendor_ids[0]),
    "assignment_id": lambda seed: str(seed.domain.market_b.assignment_ids[0]),
    # --- 02-11: usta (`setup-status` / `activate` / `DELETE`) ---
    #
    # Bu YAGONA filler bozorning O'ZIGA ishora qiladi, uning ichidagi
    # obyektga emas — `markets` da `market_id` ustuni yo'q, tenant kaliti
    # `id` ning o'zi (`MARKETS_PREDICATE`).
    "market_id": lambda seed: str(seed.base.market_b.id),
}
"""Yo'l parametri -> **B bozoridan** olingan qiymat.

Kelajakdagi parametr turlari (`vendor_id`, `assignment_id`, `payment_id`,
...) shu yerga qo'shiladi. Xaritada bo'lmagan parametr paydo bo'lsa
`test_all_path_params_have_fillers` va `test_no_unclassified_routes`
DARHOL yiqiladi — jimgina o'tkazib yuborish YO'Q.
"""

FUTURE_DAYS = 30
"""`valid_from` uchun "kelajak" oralig'i — SOBIT SANA EMAS.

02-07 deviatsiya #1 dagi bilan bir xil sabab: qotirilgan sana loyihaning
O'Z muddati ichida o'tmishga aylanadi va o'shanda toifa davri so'rovi
403 olib, matritsa 404 kutayotgan joyda yiqilardi. O'ttiz kun UTC va
Toshkent orasidagi bir kunlik farqdan ancha katta, ya'ni chegara
holati yuzaga kelmaydi.
"""


def _future_date() -> str:
    return (date.today() + timedelta(days=FUTURE_DAYS)).isoformat()


MATRIX_VENDOR_PHONE = "+998909990001"
"""Matritsa YARATADIGAN sotuvchining telefoni — seed diapazonlaridan TASHQARIDA.

`fixtures/market_domain.A_VENDOR_PHONES` `+99890111...` ni,
`fixtures/two_markets._next_phone()` esa `+99897...` ni ishlatadi. Bu
raqam ikkalasiga ham tegmaydi, ya'ni `POST /api/v1/vendors` matritsa
chaqiruvida kutilmagan `409 vendor_phone_taken` olmaydi — 409 esa
matritsani "404 kutilgan edi" o'rniga sababsiz yiqitardi.
"""


def _free_stall(seed: TenantSeed) -> str:
    """A bozorining HECH QACHON biriktirilmagan rastasi (D-11 ning ikkinchi shakli).

    `POST /api/v1/assignments` matritsa chaqiruvi HAQIQIY qator yozadi,
    ya'ni tanlangan rasta bo'sh bo'lishi shart: band rasta bilan javob
    409 `assignment_period_overlaps` bo'lardi va marshrut yana ham
    sinalmay qolardi (`BODY_FILLERS` docstringidagi umumiy sabab).
    """
    stall_id = seed.domain.market_a.unassigned_stall_id
    assert stall_id is not None, "seed `unassigned_stall_id` ni to'ldirmagan"
    return str(stall_id)


BODY_FILLERS: dict[RouteSpec, Callable[[TenantSeed], dict[str, Any]]] = {
    RouteSpec("POST", "/api/v1/zones"): lambda _: {"name": "Matritsa zonasi"},
    RouteSpec("PATCH", "/api/v1/zones/{zone_id}"): lambda _: {"name": "Matritsa zonasi"},
    RouteSpec("POST", "/api/v1/categories"): lambda _: {"name": "Matritsa toifasi"},
    RouteSpec("PATCH", "/api/v1/categories/{category_id}"): lambda _: {"name": "Matritsa toifasi"},
    RouteSpec("POST", "/api/v1/stalls"): lambda seed: {
        "code": "9001",
        "zone_id": str(seed.domain.market_a.zone_ids[0]),
        "category_id": str(seed.domain.market_a.category_ids[0]),
    },
    RouteSpec("PATCH", "/api/v1/stalls/{stall_id}"): lambda _: {"note": "matritsa"},
    RouteSpec("POST", "/api/v1/stalls/{stall_id}/category"): lambda seed: {
        # Toifa **A** bozoridan: matritsa YO'L PARAMETRINI (B ning rastasi)
        # sinaydi, tana emas. A ning toifasi bilan so'rov 404 gacha yetib
        # boradi va javobda B ning birorta identifikatori ham bo'lmaydi —
        # 422 validatsiya javobi kirish qiymatini AKS ETTIRADI, ya'ni
        # tanaga B ning ID'sini qo'yish `test_no_route_leaks_...` ni
        # o'z-o'zidan yiqitishi mumkin edi.
        "category_id": str(seed.domain.market_a.category_ids[0]),
        "valid_from": _future_date(),
    },
    # --- 02-09: tarif va kalendar ---
    RouteSpec("POST", "/api/v1/tariffs"): lambda seed: {
        "category_id": str(seed.domain.market_a.category_ids[0]),
        "amount_soum": 15_000,
        "valid_from": _future_date(),
    },
    # `valid_from` ATAYIN YO'Q: u berilganda so'rov avval `market_profile`
    # oynasini o'qiydi va sana darvozasidan o'tadi, ya'ni matritsa 404
    # o'rniga 422 yoki 409 olishi mumkin edi. Tana faqat marshrutni
    # ISHLAB KETTIRISHI kerak — chegara holatlari `test_tariffs_api.py` da.
    RouteSpec("PATCH", "/api/v1/tariffs/{tariff_id}"): lambda _: {"amount_soum": 15_000},
    RouteSpec("PUT", "/api/v1/calendar/weekdays"): lambda _: {"open_weekdays": [1, 2, 3, 4, 5]},
    RouteSpec("POST", "/api/v1/calendar/exceptions"): lambda _: {
        "exception_date": _future_date(),
        "is_open": False,
        "note": "matritsa",
    },
    # --- 02-10: sotuvchi va biriktirish ---
    RouteSpec("POST", "/api/v1/vendors"): lambda _: {
        "full_name": "Matritsa Sotuvchisi",
        "phone": MATRIX_VENDOR_PHONE,
    },
    # `phone` ATAYIN YO'Q: `PATCH` yo'lida u faqat unikalik konstraytiga
    # olib borardi va matritsa 404 o'rniga 409 olishi mumkin edi. Tana
    # marshrutni ISHLAB KETTIRISHI kifoya — telefon chegara holatlari
    # `test_vendors_api.py` da.
    RouteSpec("PATCH", "/api/v1/vendors/{vendor_id}"): lambda _: {
        "full_name": "Matritsa Sotuvchisi",
    },
    RouteSpec("POST", "/api/v1/assignments"): lambda seed: {
        # Rasta ham, sotuvchi ham **A** bozoridan: bu marshrutda yo'l
        # parametri YO'Q, ya'ni u faqat "javobda B'ning izi yo'q"
        # da'vosiga tushadi. Tanaga B ning ID'sini qo'yish 422 javobini
        # tug'dirardi va o'sha javob kirish qiymatini AKS ETTIRIB
        # `test_no_route_leaks_...` ni o'z-o'zidan yiqitardi
        # (`POST /stalls/{id}/category` bilan bir xil mulohaza).
        "stall_id": _free_stall(seed),
        "vendor_id": str(seed.domain.market_a.vendor_ids[0]),
        "from_date": _future_date(),
    },
    RouteSpec("PATCH", "/api/v1/assignments/{assignment_id}"): lambda _: {
        "to_date": _future_date(),
    },
    # --- 02-12: import ---
    #
    # Xato ro'yxati BO'SH: marshrut faylni QAYTARADI, ya'ni matritsa
    # uchun ahamiyatlisi uning ISHLAB KETISHI. Bo'sh ro'yxat ham yaroqli
    # `.xlsx` beradi (`test_empty_error_report_is_still_a_valid_file`).
    RouteSpec("POST", "/api/v1/imports/errors.xlsx"): lambda _: {"errors": []},
}
"""Tana TALAB QILADIGAN marshrutlar uchun YAROQLI so'rov tanasi.

NEGA KERAK: FastAPI dependency'larni tanadan OLDIN hal qiladi, lekin
tanani undan keyin tekshiradi. Ya'ni tanasiz `PATCH`/`POST` so'rovi
autentifikatsiyadan o'tib, so'ng **422** bilan tugardi — endpoint
mantiqi UMUMAN ishlamasdi va "cross-tenant obyekt 404 beradi" degan
asosiy da'vo hech qachon sinalmasdi (matritsa yashil bo'lib turardi).

`valid_from` KELAJAKDA (`_future_date()`): o'tmishdagi sana 403
`category_period_past_locked` berardi va matritsa 404 kutayotgan joyda
yiqilardi. Bu chegara holati o'zi ALOHIDA uchta test bilan qamralgan
(`tests/integration/test_stall_registry.py`).

`RouteSpec` bo'yicha kalitlanadi (yo'l bo'yicha EMAS): bitta yo'lda bir
necha metod bo'ladi (`PATCH` va `DELETE`) va `DELETE` ga tana yuborish
noto'g'ri signal berardi.
"""


XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

MATRIX_STALL_CODE = "9101"
"""Matritsa import qiladigan rasta kodi — seed diapazonidan TASHQARIDA.

Seed kodlari `2, 3, 7, 10, 55, 100`. Ular bilan to'qnashsa javob D-15
bo'yicha `skipped` bo'lardi — bu ham 200, ya'ni matritsa buzilmasdi,
lekin marshrutning YOZISH yo'li umuman sinalmasdi.
"""

MATRIX_IMPORT_PHONE = "+998909990002"
"""Matritsa import qiladigan sotuvchi telefoni — barcha seed'lardan tashqarida.

`MATRIX_VENDOR_PHONE` (`...0001`) `POST /vendors` uchun band, seed'lar
esa `+99890111...` va `+99897...` ni ishlatadi.
"""

_MATRIX_STAFF_PHONES = count(909_990_100)
"""Xodim rosteri fillerи uchun O'SUVCHI raqam manbai (02-24).

⚠ QATTIQ YOZILGAN RAQAM BU YERDA ISHLAMAYDI VA BU O'LCHANGAN XAVF.

Filler lambda'si HAR SO'ROVDA qayta chaqiriladi (matritsa bitta
marshrutni bir necha token bilan uradi), sotuvchi importidan farqli
o'laroq esa `POST /imports/staff` GLOBAL `users` jadvaliga yozadi —
ya'ni ikkinchi chaqiruv `phone_taken` (422) olardi. 422 esa
`test_file_routes_actually_execute` ning AYNAN tekshiradigan qiymati,
ya'ni test "filler yo'q" deb YOLG'ON qizarardi va sabab butunlay
boshqa joyda ko'rinardi.

`+99890999xxxx` diapazoni barcha seed'lardan (`+99890111…`, `+99897…`,
`+99893…`) tashqarida.
"""


def _matrix_staff_file() -> bytes:
    """Matritsa yuboradigan YAROQLI xodim `.xlsx`.

    Rol `cashier` — u D-04 ning IKKALA darajasida ham ruxsat etilgan,
    ya'ni matritsa qaysi token bilan chaqirsa ham javob `role_not_allowed`
    bo'lib qolmaydi.
    """
    return _write_xlsx(
        "Xodimlar",
        ["F.I.Sh.", "telefon", "rol"],
        ["Matritsa Xodim", f"+998{next(_MATRIX_STAFF_PHONES)}", "cashier"],
    )


def _matrix_stall_file() -> bytes:
    """Matritsa yuboradigan YAROQLI rasta `.xlsx` — A bozorining O'Z lug'ati bilan.

    Zona va toifa **A** bozoridan olinadi (`POST /stalls/{id}/category`
    tanasidagi bilan bir xil mulohaza): B ning nomini yozish 422
    javobini tug'dirardi va o'sha javob kirish qiymatini AKS ETTIRIB
    `test_no_route_leaks_other_market_identifiers` ni o'z-o'zidan
    yiqitardi.
    """
    return _write_xlsx(
        "Rastalar",
        ["kod", "zona", "toifa", "holat", "izoh"],
        [MATRIX_STALL_CODE, A_ZONE_NAMES[0], A_CATEGORY_NAMES[0], "active", ""],
    )


def _matrix_vendor_file() -> bytes:
    """Matritsa yuboradigan YAROQLI sotuvchi `.xlsx`.

    Rasta kodi ATAYIN BO'SH: biriktirish yozilsa matritsa har
    chaqiruvda o'sha rastaga yangi davr qo'shib, `EXCLUDE` konstraytiga
    urilardi va marshrut 404 kutilgan joyda 409 berardi.
    """
    return _write_xlsx(
        "Sotuvchilar",
        ["F.I.Sh.", "telefon", "rasta kodi", "boshlanish sanasi"],
        ["Matritsa Import", MATRIX_IMPORT_PHONE, "", ""],
    )


def _write_xlsx(sheet: str, header: list[str], row: list[str]) -> bytes:
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet(sheet)
    worksheet.write_row(0, 0, header)
    worksheet.write_row(1, 0, row)
    workbook.close()
    return buffer.getvalue()


FILE_FILLERS: dict[RouteSpec, Callable[[TenantSeed], dict[str, tuple[str, bytes, str]]]] = {
    RouteSpec("POST", "/api/v1/imports/stalls"): lambda _: {
        "file": ("rastalar.xlsx", _matrix_stall_file(), XLSX_MEDIA_TYPE)
    },
    RouteSpec("POST", "/api/v1/imports/vendors"): lambda _: {
        "file": ("sotuvchilar.xlsx", _matrix_vendor_file(), XLSX_MEDIA_TYPE)
    },
    RouteSpec("POST", "/api/v1/imports/staff"): lambda _: {
        "file": ("xodimlar.xlsx", _matrix_staff_file(), XLSX_MEDIA_TYPE)
    },
}
"""`multipart/form-data` TALAB QILADIGAN marshrutlar uchun HAQIQIY fayl.

NEGA `BODY_FILLERS` YETMAYDI: u `json=` bilan yuboradi, fayl
endpointi esa `multipart/form-data` kutadi. JSON tanali so'rov
`UploadFile` maydonini topa olmay **422** bilan tugardi — ya'ni
endpoint mantiqi UMUMAN ishlamasdi va "javobda B bozorining izi yo'q"
degan da'vo bu ikkala marshrut uchun HECH QACHON sinalmasdi, matritsa
esa yashil bo'lib turardi. Bu 02-08 deviatsiya #4 (`BODY_FILLERS` ning
o'zi) bilan AYNAN bir xil sinf xato, faqat kontent tipi darajasida.

Ikkala xarita ham bir vaqtda berilmaydi: `call_route()` avval
`FILE_FILLERS` ga qaraydi va topsa `json=` ni umuman ishlatmaydi.
"""

PLATFORM_ADMIN_ROUTES: frozenset[RouteSpec] = frozenset(
    {
        RouteSpec("DELETE", "/api/v1/markets/{market_id}"),
        RouteSpec("POST", "/api/v1/markets/{market_id}/activate"),
    }
)
"""Matritsa KUCHAYTIRILGAN sessiya bilan chaqiradigan marshrutlar (02-11).

=============================================================================
NEGA BU RO'YXAT MATRITSANI ZAIFLASHTIRMAYDI, AKSINCHA — KUCHAYTIRADI.

Ikkala marshrut ham `MARKET_MANAGE` talab qiladi, u esa D-07 matritsasida
FAQAT `platform_admin` da bor. Ya'ni odatdagi `market_a_headers` (bozor
admini) sessiyasi bilan javob **403** bo'lardi va
`test_cross_tenant_object_returns_404` aynan 403 ga qarshi yozilgan
assertion'da yiqilardi.

"Yiqilmasin" deb 403 ni ruxsat etish eng yomon yechim bo'lardi: o'shanda
HUQUQ darvozasi TENANT darvozasini butunlay YOPIB qo'yardi va "begona
bozorni faollashtirib bo'lmaydi" degan da'vo HECH QACHON sinalmasdi —
matritsa yashil bo'lib turardi, chunki so'rov tenant tekshiruvigacha
umuman yetib bormasdi. Bu 02-10 dagi "bo'sh 200 tenant teshigini
yashiradi" holatining aynan boshqa ko'rinishi.

Shuning uchun bu marshrutlar `MARKET_MANAGE` GA EGA sessiya bilan (A
bozorini tanlagan platforma admini) chaqiriladi — ya'ni so'rov huquq
darvozasidan O'TADI va tenant darvozasi HAQIQATAN sinaladi. Bu D-06 ning
asosiy da'vosining bevosita davomi: platforma admini "hamma narsani
qiladigan" rol emas, u bozor TANLAB kiradi.

`test_platform_admin_routes_really_need_the_elevated_session` esa ro'yxatga
qo'shilgan har bir marshrut uchun bozor admini ROSTDAN 403 olishini
qulflaydi — aks holda kimdir bir kun oddiy marshrutni bu yerga qo'shib,
uni kuchsizroq sessiyadan olib chiqib ketardi.

⚠ `GET /markets/{market_id}/setup-status` bu ro'yxatda ATAYIN YO'Q: u
`MARKET_DATA_VIEW` talab qiladi va bozor adminida u BOR, ya'ni u odatdagi
sessiya bilan tenant darvozasigacha yetib boradi.
=============================================================================
"""

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
"""Mavjud BO'LMAGAN ID — cross-tenant javob u bilan bayt-bayt taqqoslanadi."""


def all_routes(app: FastAPI) -> tuple[RouteSpec, ...]:
    """`app.routes` dagi BARCHA marshrutlar (metod bo'yicha yoyilgan).

    FastAPI 0.140 `include_router()` natijasini `_IncludedRouter` o'ramiga
    joylaydi: `app.routes` endi TEKIS ro'yxat EMAS — o'ram ichidagi
    marshrutlar `original_router.routes` da, prefiks esa
    `include_context.prefix` da yashaydi. Shuning uchun rekursiv yurish
    kerak.

    Bu ichki tuzilma kelajakda yana o'zgarishi mumkin va o'shanda yurish
    JIMGINA kamroq marshrut topib qolardi — matritsa bo'shab, baribir
    yashil bo'lardi. Aynan shuning uchun
    `test_route_walker_matches_openapi` yurish natijasini `app.openapi()`
    bilan solishtiradi: OpenAPI — FastAPI ning OMMAVIY kontrakti.
    """
    return tuple(sorted(set(_walk(app.routes, prefix=""))))


def _walk(routes: Any, *, prefix: str) -> Iterator[RouteSpec]:
    """Marshrut daraxtini aylanib chiqadi (prefikslarni to'plagan holda)."""
    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            context = getattr(route, "include_context", None)
            nested_prefix = str(getattr(context, "prefix", "") or "")
            yield from _walk(included.routes, prefix=prefix + nested_prefix)
            continue

        path = getattr(route, "path", None)
        if path is None:
            continue

        # `HEAD`/`OPTIONS` — Starlette avtomatik qo'shadi, alohida xulq emas.
        methods = set(getattr(route, "methods", None) or {"GET"}) - {"HEAD", "OPTIONS"}
        for method in methods:
            yield RouteSpec(method=method, path=prefix + path)


def tenant_resource_routes(app: FastAPI) -> tuple[RouteSpec, ...]:
    """Cross-tenant matritsasi QAMRAYDIGAN marshrutlar = istisno bo'lmagan hammasi.

    Ro'yxat POZITIV emas, NEGATIV tuziladi: yangi endpoint qo'shilganda u
    avtomatik matritsaga TUSHADI. Teskarisi (qo'lda "qamrasin" deb
    belgilash) yangi marshrutni jimgina tashqarida qoldirardi — ya'ni
    unutish xavfsiz tomonga emas, XAVFLI tomonga ishlardi.
    """
    return tuple(route for route in all_routes(app) if route.path not in EXEMPT_ROUTES)


def parametrized_routes(app: FastAPI) -> tuple[RouteSpec, ...]:
    """Path parametri BOR marshrutlar — 404 matritsasining o'zi."""
    return tuple(route for route in tenant_resource_routes(app) if route.param_names)


MATRIX_ROUTES = tenant_resource_routes(fastapi_app)
"""Matritsa qamrayotgan marshrutlar — `parametrize` uchun import paytida hisoblanadi."""

OBJECT_ROUTES = parametrized_routes(fastapi_app)
"""Path parametri bor marshrutlar — "A tokeni + B obyekti" testlari uchun."""


def _route_id(route: RouteSpec) -> str:
    return route.test_id


def fill_path(route: RouteSpec, seed: TenantSeed) -> str:
    """Yo'l parametrlarini **B bozori** qiymatlari bilan to'ldiradi."""
    path = route.path
    for name in route.param_names:
        path = path.replace("{" + name + "}", PARAM_FILLERS[name](seed))
    return path


async def call_route(
    client: httpx.AsyncClient,
    route: RouteSpec,
    seed: TenantSeed,
    *,
    headers: dict[str, str] | None = None,
    path: str | None = None,
) -> httpx.Response:
    """Marshrutni chaqiradi va (kerak bo'lsa) YAROQLI tana yoki FAYL yuboradi.

    Barcha matritsa testlari SHU yordamchidan o'tadi. Har testda alohida
    `client.request(...)` yozilganda tana faqat ba'zilariga qo'shilardi va
    "nega bu test 422 oldi?" savoli har safar qaytadan tekshirilardi.

    JSON va FAYL bir-birini ISTISNO qiladi: `multipart/form-data`
    marshrutiga JSON yuborish 422 berardi va marshrut mantiqi umuman
    ishlamasdi (`FILE_FILLERS` docstringi).
    """
    files = FILE_FILLERS.get(route)
    if files is not None:
        return await client.request(
            route.method,
            fill_path(route, seed) if path is None else path,
            headers=headers,
            files=files(seed),
        )

    body = BODY_FILLERS.get(route)
    return await client.request(
        route.method,
        fill_path(route, seed) if path is None else path,
        headers=headers,
        json=None if body is None else body(seed),
    )


def foreign_markers(seed: TenantSeed) -> tuple[str, ...]:
    """B bozoriga tegishli, javobda HECH QACHON uchramasligi kerak bo'lgan satrlar.

    Faqat UUID va E.164 telefon: ular yetarlicha uzun va tasodifiy, ya'ni
    boshqa maydonga tasodifan mos kelmaydi. `audit_log.id` (butun son)
    ATAYIN bu ro'yxatda YO'Q — "42" kabi qiymat javobning istalgan
    joyidagi songa mos kelib YOLG'ON-QIZIL berardi; u
    `test_audit_list_never_leaks_the_other_market` da STRUKTURA bo'yicha
    (aynan `item["id"]` bilan) tekshiriladi.

    ⚠ SOTUVCHI TELEFONI RO'YXATGA QO'SHILMAYDI: `fixtures/market_domain.py`
    B bozorining sotuvchisiga A ning telefonini ATAYIN beradi (D-12 —
    unikalik bozor ICHIDA). Uni marker sifatida olish A bozorining O'Z
    javobini "sizish" deb belgilab, yolg'on-qizil berardi. Domen
    obyektlarining UUID'lari esa bozorlar orasida hech qachon
    takrorlanmaydi va shuning uchun ular ro'yxatda BOR.
    """
    market_b = seed.base.market_b
    domain_b = seed.domain.market_b
    return (
        str(market_b.id),
        *(str(user_id) for user_id in market_b.user_ids),
        *(str(role_id) for role_id in market_b.role_ids),
        *market_b.phones,
        *(str(zone_id) for zone_id in domain_b.zone_ids),
        *(str(category_id) for category_id in domain_b.category_ids),
        *(str(stall_id) for stall_id in domain_b.stall_ids),
        *(str(vendor_id) for vendor_id in domain_b.vendor_ids),
        *(str(tariff_id) for tariff_id in domain_b.tariff_ids),
        *(str(exception_id) for exception_id in domain_b.calendar_exception_ids),
        *(str(assignment_id) for assignment_id in domain_b.assignment_ids),
    )


def assert_no_foreign_data(response: httpx.Response, seed: TenantSeed, label: str) -> None:
    """Javob tanasida B bozorining birorta identifikatori ham yo'q."""
    body = response.text
    for marker in foreign_markers(seed):
        assert marker not in body, f"{label}: javobda B bozorining `{marker}` qiymati sizib chiqdi"


@pytest.fixture
def tenant_seed(two_markets: TwoMarketSeed, market_domain: MarketDomainSeed) -> TenantSeed:
    """A'zolik va domen qatlamlarini bitta obyektga bog'laydi.

    `market_domain` `two_markets` ni O'ZI argument sifatida oladi, ya'ni
    ikkalasi AYNI bozorlarni tavsiflaydi va teardown tartibi ham to'g'ri
    qoladi (domen qatlami bozorlardan OLDIN tozalanadi).
    """
    return TenantSeed(base=two_markets, domain=market_domain)


@pytest.fixture
async def market_a_headers(
    api_client: httpx.AsyncClient, tenant_seed: TenantSeed
) -> dict[str, str]:
    """A bozori adminining sessiyasi (a'zoligi bitta -> bozor avtomatik tanlanadi)."""
    market_a = tenant_seed.base.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def market_a_admin_headers(
    api_client: httpx.AsyncClient, tenant_seed: TenantSeed
) -> dict[str, str]:
    """A bozorini TANLAGAN platforma adminining sessiyasi (`MARKET_MANAGE` bilan).

    `test_platform_admin_cannot_reach_the_unselected_market` bilan aynan
    bir xil sessiya: bozor tanlangandan keyin platforma admini oddiy
    tenant sifatida ishlaydi (D-06). Bu yerda u faqat `PLATFORM_ADMIN_
    ROUTES` uchun ishlatiladi — sabab o'sha konstantaning docstringida.
    """
    return await session_headers(
        api_client,
        tenant_seed.base.platform_admin_phone,
        SEED_PASSWORD,
        market_id=tenant_seed.base.market_a.id,
    )


@pytest.fixture
def headers_for(
    market_a_headers: dict[str, str],
    market_a_admin_headers: dict[str, str],
) -> Callable[[RouteSpec], dict[str, str]]:
    """Marshrutga MOS keladigan A-bozor sessiyasini tanlaydi.

    Tanlov `PLATFORM_ADMIN_ROUTES` bo'yicha va boshqa hech qanday shart
    yo'q: sessiya HAR DOIM **A bozoriga** tegishli, ya'ni "begona bozor
    obyekti -> 404" da'vosi o'zgarmaydi. Farq faqat HUQUQ darajasida.
    """

    def _pick(route: RouteSpec) -> dict[str, str]:
        return market_a_admin_headers if route in PLATFORM_ADMIN_ROUTES else market_a_headers

    return _pick


# ===========================================================================
# T-01-75 / T-01-76 — A tokeni + B obyekti -> 404 (403 EMAS)
# ===========================================================================


@pytest.mark.parametrize("route", OBJECT_ROUTES, ids=_route_id)
async def test_cross_tenant_object_returns_404(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    headers_for: Callable[[RouteSpec], dict[str, str]],
    route: RouteSpec,
) -> None:
    """A bozori tokeni + B bozori obyekti -> **404**, va AYNIQSA 403 EMAS.

    Ikkita alohida assert ATAYIN: birinchisi aynan 403 ga qarshi yozilgan,
    ikkinchisi kutilgan javobni qulflaydi. Faqat `== 404` bo'lganda
    kimdir kodni 403 ga o'zgartirsa xato xabari "404 kutilgan edi" deb
    chiqardi va sabab (information disclosure) ko'rinmasdi.
    """
    response = await call_route(api_client, route, tenant_seed, headers=headers_for(route))

    assert response.status_code != 403, (
        f"{route.test_id}: 403 obyekt MAVJUDLIGINI tasdiqlaydi — 404 bo'lishi shart (T-01-76)"
    )
    assert response.status_code == 404, f"{route.test_id}: {response.status_code} — {response.text}"


@pytest.mark.parametrize("route", OBJECT_ROUTES, ids=_route_id)
async def test_cross_tenant_is_indistinguishable_from_unknown_id(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    headers_for: Callable[[RouteSpec], dict[str, str]],
    route: RouteSpec,
) -> None:
    """Begona bozor ID'si va MAVJUD BO'LMAGAN ID — bayt-bayt bir xil javob.

    Status kodi yetarli emas: bir xil 404 ichida turli `detail` matni ham
    enumeration signali bo'lardi (`not_found` va `forbidden_market`).
    """
    unknown_path = route.path
    for name in route.param_names:
        unknown_path = unknown_path.replace("{" + name + "}", UNKNOWN_ID)

    headers = headers_for(route)
    foreign = await call_route(api_client, route, tenant_seed, headers=headers)
    unknown = await call_route(api_client, route, tenant_seed, headers=headers, path=unknown_path)

    assert foreign.status_code == unknown.status_code
    assert foreign.content == unknown.content, f"{route.test_id}: javob tanalari farq qiladi"


@pytest.mark.parametrize("route", MATRIX_ROUTES, ids=_route_id)
async def test_no_route_leaks_other_market_identifiers(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    headers_for: Callable[[RouteSpec], dict[str, str]],
    route: RouteSpec,
) -> None:
    """HAR BIR tenant marshruti: A tokeni bilan javobda B'ning izi ham yo'q.

    Bu — path parametri BO'LMAGAN marshrutlarni (`GET /users`,
    `GET /audit`, `GET /stalls`, `GET /stalls/map`) qamraydigan qism. Ular
    uchun "B obyektini so'rash" mumkin emas, ya'ni yagona ma'noli da'vo —
    javobda B'ning birorta identifikatori ham bo'lmasligi.

    `BODY_FILLERS` tufayli yozuv marshrutlari ham HAQIQIY yo'ldan o'tadi
    (422 da to'xtab qolmaydi), ya'ni bu da'vo ular uchun ham ma'noli.
    """
    response = await call_route(api_client, route, tenant_seed, headers=headers_for(route))

    assert_no_foreign_data(response, tenant_seed, route.test_id)


async def test_user_list_contains_no_other_market_members(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    market_a_headers: dict[str, str],
) -> None:
    """`GET /users` — A ning uchala a'zosi BOR, B ning birortasi ham YO'Q.

    Pozitiv qism ("A ko'rinadi") ham MAJBURIY: usiz ro'yxat butunlay bo'sh
    bo'lganda ham test yashil bo'lardi va hech nimani isbotlamasdi.
    """
    response = await api_client.get(USERS_URL, headers=market_a_headers)

    assert response.status_code == 200, response.text
    returned = {item["id"] for item in response.json()["items"]}
    assert {str(uid) for uid in tenant_seed.base.market_a.user_ids} <= returned
    assert returned & {str(uid) for uid in tenant_seed.base.market_b.user_ids} == set()


# ===========================================================================
# T-01-75 — audit ro'yxati har qanday filtr ostida ham sizdirmaydi
# ===========================================================================

AUDIT_FILTERS: tuple[tuple[str, dict[str, str]], ...] = (
    ("filtrsiz", {}),
    ("jadval", {"table_name": "user_market_roles"}),
    ("amal", {"action": "insert"}),
    ("sana-oraligi", {"from": "1970-01-01", "to": "2100-01-01"}),
    ("maksimal-chegara", {"limit": "200"}),
)
"""Filtr kombinatsiyalari — har biri boshqa SQL yo'lini (indeks, predikat) yoqadi."""


@pytest.mark.parametrize(("label", "params"), AUDIT_FILTERS, ids=[f[0] for f in AUDIT_FILTERS])
async def test_audit_list_never_leaks_the_other_market(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    market_a_headers: dict[str, str],
    label: str,
    params: dict[str, str],
) -> None:
    """`GET /audit` beshta filtr kombinatsiyasida ham B qatorini qaytarmaydi.

    B bozorida OLDINDAN yozilgan qator bor (`MarketSeed.audit_row_id`) —
    ya'ni bu "hech narsa qaytmadi" degan bo'sh da'vo emas: tekshirilayotgan
    qator MAVJUD va u baribir ko'rinmaydi.
    """
    response = await api_client.get(AUDIT_URL, params=params, headers=market_a_headers)

    assert response.status_code == 200, f"{label}: {response.text}"
    ids = {item["id"] for item in response.json()["items"]}
    assert tenant_seed.base.market_b.audit_row_id not in ids, (
        f"{label}: B bozorining audit qatori A tokeni bilan ko'rindi"
    )
    assert_no_foreign_data(response, tenant_seed, f"GET {AUDIT_URL} ({label})")


async def test_audit_list_shows_the_own_market_probe_row(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    market_a_headers: dict[str, str],
) -> None:
    """NAZORAT HOLATI: A ning O'Z qatori ko'rinadi.

    Usiz yuqoridagi beshta test `GET /audit` umuman bo'sh qaytargan
    holatda ham yashil bo'lardi — ya'ni ular izolyatsiyani emas,
    endpointning ishlamayotganini "isbot" qilardi.
    """
    response = await api_client.get(AUDIT_URL, params={"limit": "200"}, headers=market_a_headers)

    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()["items"]}
    assert tenant_seed.base.market_a.audit_row_id in ids


# ===========================================================================
# T-01-77 — D-06: platforma admini uchun ham bypass yo'li YO'Q
# ===========================================================================


async def test_platform_admin_cannot_reach_the_unselected_market(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> None:
    """A ni tanlagan platforma admini B obyektiga 404 oladi; B ni tanlagach — 200.

    AYNAN BIR XIL marshrut, AYNAN BIR XIL obyekt; farq faqat TANLANGAN
    bozorda. Bu D-06 ning asosiy da'vosi: platforma admini "hamma narsani
    ko'radigan" rol EMAS — u bozor TANLAB kiradi va tanlagandan keyin
    oddiy tenant kontekstida ishlaydi (`BYPASSRLS` atributli rol umuman
    mavjud emas — `tests/tenancy/test_meta.py`).
    """
    target = f"{USERS_URL}/{two_markets.market_b.cashier_user_id}/reset-password"

    with_a = await session_headers(
        api_client,
        two_markets.platform_admin_phone,
        SEED_PASSWORD,
        market_id=two_markets.market_a.id,
    )
    denied = await api_client.post(target, headers=with_a)

    with_b = await session_headers(
        api_client,
        two_markets.platform_admin_phone,
        SEED_PASSWORD,
        market_id=two_markets.market_b.id,
    )
    allowed = await api_client.post(target, headers=with_b)

    assert denied.status_code != 403
    assert denied.status_code == 404, denied.text
    assert allowed.status_code == 200, allowed.text


# ===========================================================================
# T-01-79 — tokensiz, buzilgan va muddati o'tgan token -> 401
# ===========================================================================


@pytest.mark.parametrize("route", MATRIX_ROUTES, ids=_route_id)
async def test_missing_token_is_rejected(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    route: RouteSpec,
) -> None:
    """`Authorization` sarlavhasisiz har bir tenant marshruti 401 qaytaradi.

    Tana YUBORILADI (`call_route`), lekin javob baribir 401 bo'lishi shart:
    FastAPI dependency'larni tanani tekshirishdan OLDIN hal qiladi. Agar
    biror marshrut bu yerda 422 qaytarsa, u autentifikatsiyadan OLDIN
    tanani o'qiyapti degani va bu holat alohida ko'rinishi kerak.
    """
    response = await call_route(api_client, route, tenant_seed)

    assert response.status_code == 401, f"{route.test_id}: {response.status_code}"


@pytest.mark.parametrize("route", MATRIX_ROUTES, ids=_route_id)
async def test_malformed_token_is_rejected(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    route: RouteSpec,
) -> None:
    """Buzilgan token 401 — va sabab javobga CHIQMAYDI."""
    response = await call_route(
        api_client, route, tenant_seed, headers=bearer("buzilgan.token.qiymati")
    )

    assert response.status_code == 401, f"{route.test_id}: {response.status_code}"


@pytest.mark.parametrize("route", MATRIX_ROUTES, ids=_route_id)
async def test_expired_token_is_rejected(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    test_settings: Settings,
    route: RouteSpec,
) -> None:
    """MUDDATI O'TGAN token 401.

    Token MAHSULOT funksiyasi (`encode_access`) bilan, faqat manfiy TTL
    bilan chiqariladi — ya'ni imzo HAQIQIY va rad etishning yagona sababi
    `exp`. Qo'lda yig'ilgan "yaroqsiz" satr buni isbotlamasdi: u imzo
    bosqichidayoq yiqilardi va muddat tekshiruvi umuman ishlamayotgan
    bo'lsa ham test yashil qolardi.
    """
    expired = encode_access(
        user_id=tenant_seed.base.market_a.admin_user_id,
        market_id=tenant_seed.base.market_a.id,
        roles=["market_admin"],
        is_platform_admin=False,
        secret=test_settings.jwt_secret,
        issuer=test_settings.jwt_issuer,
        audience=test_settings.jwt_audience,
        ttl_minutes=-5,
    )

    response = await call_route(api_client, route, tenant_seed, headers=bearer(expired))

    assert response.status_code == 401, f"{route.test_id}: {response.status_code}"


# ===========================================================================
# Matritsaning O'ZINI himoya qiladigan da'volar
# ===========================================================================


def test_param_fillers_point_at_the_other_market(tenant_seed: TenantSeed) -> None:
    """`PARAM_FILLERS` HAQIQATAN B bozorining qiymatlarini beradi.

    Agar biror filler bir kun A bozoriga (yoki tasodifiy UUID'ga)
    o'zgartirilsa, butun matritsa "404 keldi" deb YASHIL qolardi — 404
    o'sha holatda ham to'g'ri javob. Ya'ni matritsaning ma'nosi aynan shu
    yerda qulflanadi.
    """
    market_b = tenant_seed.base.market_b
    domain_b = tenant_seed.domain.market_b
    foreign_values = {
        str(value)
        for value in (
            market_b.id,
            *market_b.user_ids,
            *market_b.role_ids,
            *domain_b.zone_ids,
            *domain_b.category_ids,
            *domain_b.stall_ids,
            *domain_b.vendor_ids,
            *domain_b.tariff_ids,
            *domain_b.calendar_exception_ids,
            *domain_b.assignment_ids,
        )
    }

    assert PARAM_FILLERS, "PARAM_FILLERS bo'sh — matritsa hech qanday obyektni sinamaydi"
    for name, filler in PARAM_FILLERS.items():
        value = filler(tenant_seed)
        assert value in foreign_values, f"`{name}` filleri B bozoriga tegishli emas: {value}"
        UUID(value)


def test_body_fillers_point_at_live_routes() -> None:
    """`BODY_FILLERS` da o'chirilgan marshrut QOLIB KETMAGAN.

    `EXEMPT_ROUTES` uchun `test_exempt_routes_still_exist_in_the_app` bilan
    AYNAN bir xil sabab: eskirgan yozuv o'zi zararsiz, lekin u ro'yxatni
    ishonchsiz qiladi va marshrut boshqa ma'noda qayta paydo bo'lganda
    tug'ilishidanoq noto'g'ri tana bilan chaqirilardi.
    """
    live = set(all_routes(fastapi_app))
    stale = sorted(route.test_id for route in BODY_FILLERS if route not in live)

    assert not stale, f"`BODY_FILLERS` da mavjud bo'lmagan marshrutlar qolgan: {stale}"


def test_file_fillers_point_at_live_routes() -> None:
    """`FILE_FILLERS` da o'chirilgan marshrut QOLIB KETMAGAN (02-12).

    `BODY_FILLERS` bilan aynan bir xil sabab. Qo'shimcha xavf shu yerda
    KUCHLIROQ: fayl fillerи eskirsa marshrut JSON yo'liga tushib
    ketardi va 422 bilan tugab, "javobda B ning izi yo'q" da'vosini
    jimgina sinamay qo'yardi.
    """
    live = set(all_routes(fastapi_app))
    stale = sorted(route.test_id for route in FILE_FILLERS if route not in live)

    assert not stale, f"`FILE_FILLERS` da mavjud bo'lmagan marshrutlar qolgan: {stale}"


@pytest.mark.parametrize("route", sorted(FILE_FILLERS), ids=_route_id)
async def test_file_routes_actually_execute(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    market_a_headers: dict[str, str],
    route: RouteSpec,
) -> None:
    """Fayl marshruti HAQIQATAN ishga tushadi — 422 da to'xtab qolmaydi.

    =======================================================================
    BU TEST `FILE_FILLERS` MEXANIZMINI YUK KO'TARUVCHI QILADI — VA U
    SABOTAJ BILAN O'LCHANGANDAN KEYIN QO'SHILDI.

    `call_route()` dan `FILE_FILLERS` olib tashlanganda butun tenancy
    to'plami (307 test) YASHIL qoldi. Sabab: JSON tanali so'rov
    `multipart/form-data` endpointida **422** beradi, 422 esa
    matritsaning birorta da'vosini buzmaydi — u 403 emas, B bozorining
    identifikatorini ham sizdirmaydi (javob faqat "file maydoni
    yetishmayapti" deydi) va tokensiz so'rov baribir 401 oladi.

    Ya'ni mexanizm to'g'ri, lekin uning YO'QLIGINI hech nima
    KO'RSATMASDI: ikkala import marshruti matritsada "bor" bo'lib
    turib, endpoint mantiqi UMUMAN ishlamasdi. Bu 02-08 deviatsiya #4
    (`BODY_FILLERS` ning o'zi) bilan AYNAN bir xil sinf xato va u
    o'sha yerda ham aynan shunday jimgina yashiringan edi.

    Shuning uchun bu yerda ALOHIDA, POZITIV da'vo: so'rov 422 BILAN
    TUGAMASLIGI shart. Aniq status kodi qulflanmaydi (u 200 ham, 409
    ham bo'lishi mumkin — matritsa qatorlarni HAQIQATAN yozadi va
    ketma-ket ishga tushishda ikkinchisi konfliktga tushishi mumkin);
    yagona ma'noli da'vo — endpoint YUKLAMANI QABUL QILDI.
    =======================================================================
    """
    response = await call_route(api_client, route, tenant_seed, headers=market_a_headers)

    assert response.status_code != 422, (
        f"{route.test_id}: yuklama qabul qilinmadi ({response.text}) — "
        "`FILE_FILLERS` yozuvi yo'q yoki `call_route()` uni ishlatmayapti"
    )
    assert response.status_code != 403, f"{route.test_id}: {response.text}"


def test_file_and_body_fillers_do_not_overlap() -> None:
    """Bitta marshrut IKKALA xaritada ham bo'lmaydi.

    `call_route()` avval `FILE_FILLERS` ga qaraydi, ya'ni kesishuv
    bo'lsa `BODY_FILLERS` yozuvi JIMGINA e'tiborsiz qolardi — va uni
    qo'shgan odam "tana yuborilyapti" deb o'ylab yurardi.
    """
    assert set(FILE_FILLERS) & set(BODY_FILLERS) == set()


def test_platform_admin_routes_point_at_live_routes() -> None:
    """`PLATFORM_ADMIN_ROUTES` da o'chirilgan marshrut QOLIB KETMAGAN.

    `BODY_FILLERS` va `EXEMPT_ROUTES` bilan bir xil sabab: eskirgan yozuv
    o'zi zararsiz, lekin marshrut BOSHQA ma'noda qayta paydo bo'lganda u
    tug'ilishidanoq kuchaytirilgan sessiya bilan chaqirilardi.
    """
    live = set(all_routes(fastapi_app))
    stale = sorted(route.test_id for route in PLATFORM_ADMIN_ROUTES if route not in live)

    assert not stale, f"`PLATFORM_ADMIN_ROUTES` da mavjud bo'lmagan marshrutlar: {stale}"


@pytest.mark.parametrize("route", sorted(PLATFORM_ADMIN_ROUTES), ids=_route_id)
async def test_platform_admin_routes_really_need_the_elevated_session(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    market_a_headers: dict[str, str],
    route: RouteSpec,
) -> None:
    """Ro'yxatdagi marshrut bozor admini uchun ROSTDAN 403 beradi.

    Bu — `PLATFORM_ADMIN_ROUTES` ning O'ZINI himoya qiladigan darvoza.
    Usiz kimdir oddiy (bozor adminiga ochiq) marshrutni ro'yxatga qo'shib,
    uni kuchsizroq sessiyadan olib chiqib ketardi va matritsa buni
    umuman sezmasdi — ikkala sessiya ham A bozoriga tegishli, ya'ni 404
    baribir kelardi.

    So'rov **A bozorining O'Z** identifikatori bilan yuboriladi: aks
    holda 404 (tenant darvozasi) 403 dan OLDIN kelib, huquq darvozasi
    umuman sinalmay qolardi.
    """
    own_path = route.path
    for name in route.param_names:
        own_path = own_path.replace("{" + name + "}", str(tenant_seed.base.market_a.id))

    response = await call_route(
        api_client, route, tenant_seed, headers=market_a_headers, path=own_path
    )

    assert response.status_code == 403, (
        f"{route.test_id}: bozor admini uchun 403 kutilgan edi — bu marshrut "
        f"`PLATFORM_ADMIN_ROUTES` da bo'lishi shart emas ({response.status_code})"
    )


def test_exempt_reasons_use_a_known_category() -> None:
    """Har bir istisno uchta ruxsat etilgan sabab turidan biriga tegishli.

    Erkin matn "vaqtincha o'tkazib yuborildi" kabi sababni ham qabul
    qilardi; toifalar ro'yxati esa yangi istisno qo'shmoqchi bo'lgan
    odamni uni UCHTA ma'lum sinfdan biriga joylashga majbur qiladi.
    """
    for path, reason in EXEMPT_ROUTES.items():
        assert reason.startswith(EXEMPT_REASON_PREFIXES), f"{path}: noma'lum sabab turi — {reason}"
