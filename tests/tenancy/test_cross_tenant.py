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
from dataclasses import replace
from datetime import date, timedelta
from itertools import count
from typing import TYPE_CHECKING, Any, NamedTuple
from uuid import UUID

import pytest
import xlsxwriter
from app.main import app as fastapi_app
from fixtures.admin_api import (
    AUDIT_URL,
    TEST_PHONE_PREFIX,
    USERS_URL,
    bearer,
    session_headers,
)
from fixtures.billing_domain import add_daily_charge
from fixtures.market_domain import A_CATEGORY_NAMES, A_ZONE_NAMES
from fixtures.nvr_domain import add_discovery_run, nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.security import encode_access

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures.auth_users import AuthSeed
    from fixtures.market_domain import MarketDomainSeed
    from fixtures.nvr_domain import NvrDomainSeed
    from fixtures.occupancy_domain import OccupancyDomainSeed
    from fixtures.snapshot_domain import SnapshotDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

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


class MatrixBillingRows(NamedTuple):
    """Matritsa yozadigan billing qatorlari (06-08).

    `service_date` HAM saqlanadi, chunki `add_daily_charge()` uni BAZADAN
    oladi (`CURRENT_DATE - 1`) va uni ikkinchi marta hisoblash IKKINCHI
    manba bo'lardi — yarim tunda ikkalasi bir kun farq qilardi.
    """

    charge_id: UUID
    service_date: date


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
    nvr: NvrDomainSeed
    """3-faza qatlami: NVR qurilmasi, kameralar va kashfiyot yugurishlari.

    ⚠ B BOZORIDA KASHFIYOT YUGURISHI SEED'DA YO'Q (`fixtures/nvr_domain.py`
      ataylab asimmetrik: «yugurishlar ro'yxati bo'sh» holati ham
      sinalishi kerak). Matritsaga esa `run_id` uchun HAQIQIY B qatori
      KERAK — tasodifiy UUID bilan 404 hech nimani isbotlamasdi. Shuning
      uchun uni `nvr_domain` fixture'i O'ZI qo'shadi (`add_discovery_run`),
      seed'ning asimmetriyasi esa saqlanadi.
    """

    snapshot: SnapshotDomainSeed
    """4-faza qatlami: mavsumiy profil, kunlik reja, kadrlar va alertlar.

    ⚠ B BOZORIDA HAM QATOR BOR va bu MAJBURIY: `schedule_id` va
      `snapshot_id` fillerlari HAQIQIY B qatorlarini ko'rsatishi kerak.
      Tasodifiy UUID bilan 404 hech nimani isbotlamasdi — biz aynan
      «obyekt BOR, lekin boshqa bozorniki» holatini sinayapmiz
      (`PARAM_FILLERS` docstringidagi umumiy qoida).
    """

    auth: AuthSeed
    """1-faza qatlami: maxsus holatdagi foydalanuvchilar (`AuthSeed`).

    ⚠ FAQAT BITTA A'ZOSI UCHUN KERAK — `inspector`. `OCCUPANCY_REVIEW`
      huquqi D-07 matritsasida FAQAT o'sha rolda bor va `two_markets`
      seed'ida bunday foydalanuvchi YO'Q. Uni `two_markets` ga qo'shish
      o'sha seed'ga tayanadigan o'nlab testning a'zolik manzarasini
      o'zgartirardi; `auth_seed` esa AYNAN shu maqsad uchun mavjud
      (`INSPECTOR_ROUTES` docstringi).
    """

    occupancy: OccupancyDomainSeed
    """5-faza qatlami: kamera zonalari, bandlik hodisalari va ko'rib chiqish.

    ⚠ `camera_zone_id` uchun B bozorida HAQIQIY FAOL zona bor
      (`fixtures/occupancy_domain.py` ikkala bozorga ham yozadi), ya'ni
      `DELETE /camera-zones/{camera_zone_id}` matritsada «obyekt BOR,
      lekin boshqa bozorniki» holatini o'lchaydi. Tasodifiy UUID bilan
      404 tenant chegarasi haqida HECH NIMA aytmasdi — u shunchaki
      «bunday zona yo'q» bo'lardi.

    ⚠ FAOL zona kerak: `deactivate()` ATAYIN `is_active = true` shartini
      qo'yadi, ya'ni eskirgan qatorni ko'rsatish 404 ni tenant chegarasi
      tufayli emas, HOLAT tufayli beradigan qilib qo'yardi va matritsa
      yashil bo'lib turib, boshqa narsani o'lchardi.
    """

    billing: MatrixBillingRows
    """6-faza qatlami: B bozorining HAQIQIY `daily_charges` qatori (06-08).

    ⚠ QATOR SEEDDA YO'Q va bu ATAYIN (`fixtures/billing_domain.py` ning
      «QATOR YOZUVCHI YORDAMCHILAR SEEDNING O'ZIGA QO'SHILMAYDI» bandi):
      seed `billing_close` ning KIRISHINI ta'riflaydi, CHIQISHINI emas.
      Matritsaga esa `charge_id` uchun HAQIQIY B qatori KERAK — TO'QILGAN
      UUID bilan 404 «bunday hisob umuman yo'q» degani bo'lardi va tenant
      da'vosi BO'SH qolardi. Shuning uchun uni `billing_rows` fixture'i
      O'ZI yozadi (`nvr_domain` ning `run_id` bandi bilan AYNAN bir xil
      naqsh).
    """


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
    "/internal/live-authz": (
        "global — nginx `auth_request` nishoni: uni FOYDALANUVCHI emas, proxy "
        "chaqiradi va unda `Authorization` sarlavhasi UMUMAN bo'lmaydi. Kontrakti "
        "ham boshqa: 204 yoki 403, hech qachon 401/404 emas — ya'ni matritsaning "
        "uchala token da'vosi (tokensiz/buzilgan/muddati o'tgan -> 401) bu yerda "
        "MA'NOSIZ bo'lardi. Bozor konteksti imzolangan CHIPTADAN keladi, tokendan "
        "emas. QAMROVI TO'LIQ QAYTA TIKLANGAN: `tests/integration/test_live_view.py` "
        "tokensiz -> 403, muddati o'tgan -> 403, ODDIY access token -> 403, begona "
        "bozor kamerasi -> 403 va boshqa kameraning oqim nomi -> 403 holatlarini "
        "alohida o'lchaydi"
    ),
    "/internal/self-check": (
        "global — TASHQI KUZATUVCHI (healthchecks.io / UptimeRobot) chaqiradigan "
        "o'z-o'zini kuzatish nishoni: unda `Authorization` sarlavhasi UMUMAN "
        "bo'lmaydi va u ATAYIN autentifikatsiyasiz. Kontrakti ham boshqa — 200 "
        "yoki 503, hech qachon 401/404 emas, ya'ni matritsaning uchala token "
        "da'vosi bu yerda MA'NOSIZ bo'lardi. Javobda bozor identifikatori, nomi "
        "yoki topologiyasi UMUMAN yo'q (faqat komponent nomlari va bayroq), ya'ni "
        "cross-tenant sizish yuzasi ham yo'q. QAMROVI TO'LIQ QAYTA TIKLANGAN: "
        "`tests/integration/test_capture_schedule.py` yangi heartbeat -> 200, "
        "eskirgan -> 503, hech qachon yozilmagan -> 503, javob yuzasining torligi "
        "va konteyner healthcheck'iga ULANMAGANI holatlarini alohida o'lchaydi"
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
    # --- 03-06: NVR qurilmasi va kashfiyot yugurishi ---
    #
    # ⚠ IKKALASI HAM B BOZORINING HAQIQIY QATORI. `run_id` uchun qator
    # `nvr_domain` fixture'ida qo'shiladi (`TenantSeed.nvr` docstringi):
    # seed B ga ATAYIN yugurish yozmaydi va u asimmetriya saqlanadi.
    "nvr_id": lambda seed: str(seed.nvr.market_b.nvr_id),
    "run_id": lambda seed: str(seed.nvr.market_b.discovery_run_ids[0]),
    # --- 03-07: kamera ---
    #
    # ⚠ B bozorining BIRINCHI (va yagona) kanali — u ARXIVLANMAGAN
    # (`fixtures/nvr_domain.py`: arxivlash faqat ko'p kanalli bozorda).
    # Arxivlangan qatorni ko'rsatish `POST /{id}/restore` ni matritsada
    # boshqa yo'ldan yuborardi va 404 ning sababi tenant chegarasi emas,
    # holat bo'lib qolardi.
    "camera_id": lambda seed: str(seed.nvr.market_b.camera_ids[0]),
    # --- 04-09: snapshot jadvali va kadr ---
    #
    # ⚠ IKKALASI HAM B BOZORINING HAQIQIY QATORI (`fixtures/
    # snapshot_domain.py`): profil `[SEED_BUSINESS_DATE, ∞)` davri bilan
    # va `B_RUN_PLAN` ning YAGONA `succeeded` qatoriga biriktirilgan kadr.
    #
    # ⚠ `snapshot_id` uchun kadr MAVJUD bo'lishi ayniqsa muhim:
    # `GET /snapshots/{id}/image` marshruti begona bozorning kadri uchun
    # 404 berishi shart, «bunday kadr yo'q» uchun ham AYNAN o'sha 404 —
    # ikkalasi farq qilsa javobning O'ZI enumeration signali bo'lardi.
    "schedule_id": lambda seed: str(seed.snapshot.market_b.schedule_id),
    "snapshot_id": lambda seed: str(seed.snapshot.market_b.snapshot_ids[0]),
    # --- 05-06: kamera zonasi ---
    #
    # ⚠ B bozorining HAQIQIY va FAOL zonasi (`TenantSeed.occupancy`
    # docstringi). `DELETE /camera-zones/{camera_zone_id}` uchun ikkala
    # shart ham majburiy: eskirgan qator 404 ni TENANT chegarasi emas,
    # HOLAT tufayli berardi.
    "camera_zone_id": lambda seed: str(seed.occupancy.market_b.active_zone_ids[0]),
    # --- 05-10: nazoratchi navbatining topshirig'i ---
    #
    # ⚠ NOM `assignment_id` EMAS va bu ATAYIN: o'sha kalit `PATCH
    # /assignments/{assignment_id}` (RASTA-SOTUVCHI biriktirishi)
    # tomonidan BAND. Ikkala marshrut bir kalitni bo'lishsa, filler
    # `POST /review/.../answer` ga BEGONA OBYEKT TURINI berardi —
    # javob 404 bo'lardi-yu, sababi tenant chegarasi emas, «bunday
    # topshiriq umuman yo'q» bo'lardi va matritsa yashil turib HECH
    # NIMANI o'lchamasdi.
    #
    # ⚠ B bozorida FAQAT ko'r audit topshirig'i bor (`uncertain_
    # assignment_id` A ga xos — `fixtures/occupancy_domain.py` ning
    # asimmetriyasi ATAYIN). Bu marshrut uchun u baribir to'g'ri
    # qiymat: begona bozorning topshirig'i RLS ostida 0 qator beradi
    # va javob 404 bo'ladi — AYNAN o'lchanayotgan holat.
    "review_assignment_id": lambda seed: str(seed.occupancy.market_b.blind_assignment_id),
    # --- 06-08: yozilgan kunlik patta hisobi ---
    #
    # ⚠ B BOZORINING HAQIQIY `daily_charges.id` SI, to'qilgan UUID EMAS.
    # Farq bu marshrutda AYNIQSA ma'noli: `GET /billing/charges/{id}` ikki
    # holatda ham 404 beradi, lekin to'qilgan qiymat bilan sabab «bunday
    # hisob umuman yo'q» bo'lardi va «hisob BOR, lekin boshqa bozorniki»
    # da'vosi HECH QACHON sinalmasdi.
    #
    # ⚠ QATORNI `billing_rows` fixture'i YOZADI, seed EMAS
    # (`TenantSeed.billing` docstringi).
    "charge_id": lambda seed: str(seed.billing.charge_id),
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


MATRIX_NVR_PASSWORD = "MatritsaNvr123"  # noqa: S105 - test uskunasi, sir emas
"""Matritsa yuboradigan NVR paroli — hech qanday haqiqiy qurilmaga tegishli emas."""

_MATRIX_NVR_PORTS = count(9001)
"""NVR manzillari uchun O'SUVCHI port — `_MATRIX_STAFF_PHONES` bilan bir xil sabab.

Filler lambda'si HAR SO'ROVDA qayta chaqiriladi va `POST /nvr-devices`
HAQIQIY qator yozadi. Qotirilgan port ikkinchi chaqiruvda
`409 nvr_host_taken` berardi (`uq_nvr_devices_market_id_host_port`) va
marshrutning YOZISH yo'li faqat birinchi testda bajarilardi.
"""


_MATRIX_SCHEDULE_DAYS = count(200)
"""Mavsumiy profilning `starts_on` i uchun O'SUVCHI kun siljishi.

`_MATRIX_NVR_PORTS` bilan bir xil sabab (filler lambda'si HAR SO'ROVDA
qayta chaqiriladi), ikki qo'shimcha shart bilan: (1) 200-kundan
boshlanadi, ya'ni seedning ochiq oxirli profilidan ancha uzoqda va
undan qisqartirish qadamiga tushmaydi; (2) qadam 5 kun, ya'ni ketma-ket
chaqiruvlar bir-birining davriga kirmaydi.
"""


def _matrix_schedule_start() -> str:
    return (date.today() + timedelta(days=next(_MATRIX_SCHEDULE_DAYS) * 5)).isoformat()


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


MATRIX_STAFF_PHONE = f"{TEST_PHONE_PREFIX}9990001"
"""Matritsa YARATADIGAN xodimning telefoni (`POST /api/v1/users`).

⚠ `TEST_PHONE_PREFIX` (`+99893`) DIAPAZONIDA va bu ATAYIN: shu prefiksdagi
  qatorlarni `fixtures/admin_api.cleanup_test_users()` supurib ketadi,
  ya'ni matritsa yozgan foydalanuvchi bazada abadiy qolib ketmaydi.

⚠ QIYMAT SOBIT (o'suvchi emas — `_MATRIX_NVR_PORTS` dan farqli): ikkinchi
  chaqiruv `409 phone_taken` beradi va bu MATRITSA UCHUN YETARLI —
  da'vo «so'rov 422 da to'xtamadi», «har safar yangi qator yozildi» emas.
  O'suvchi telefon esa har testda yangi foydalanuvchi qoldirardi.
"""


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
    # --- 03-06: NVR qurilmalari ---
    #
    # `address` HAR CHAQIRUVDA BOSHQA (`_MATRIX_NVR_PORTS`): marshrut
    # HAQIQIY qator yozadi va `uq_nvr_devices_market_id_host_port` ikkinchi
    # chaqiruvda `409 nvr_host_taken` berardi. 409 matritsani yiqitmasdi,
    # lekin `POST` ning YOZISH yo'li faqat birinchi testda bajarilardi —
    # ya'ni "javobda B ning izi yo'q" da'vosi qolganlarida shakli boshqa
    # javob ustida tekshirilardi (`MATRIX_STALL_CODE` bilan bir xil sinf).
    RouteSpec("POST", "/api/v1/nvr-devices"): lambda _: {
        "address": f"192.168.77.7:{next(_MATRIX_NVR_PORTS)}",
        "username": "matritsa",
        "password": MATRIX_NVR_PASSWORD,
    },
    RouteSpec("PATCH", "/api/v1/nvr-devices/{nvr_id}"): lambda _: {"username": "matritsa"},
    # 03-07: nom o'zgartirish. `name_overridden` ATAYIN yuborilmaydi — u
    # nomning HOSILASI (`api/v1/cameras.py::update_camera`) va yolg'iz
    # yuborilganda 422 berardi, ya'ni matritsa 404 kutayotgan joyda
    # validatsiya darvozasiga urilardi.
    RouteSpec("PATCH", "/api/v1/cameras/{camera_id}"): lambda _: {"name": "Matritsa kamerasi"},
    RouteSpec("POST", "/api/v1/nvr-devices/{nvr_id}/password"): lambda _: {
        "password": MATRIX_NVR_PASSWORD,
    },
    # ⚠ `test-connection` MATRITSADAN CHIQARILMAYDI — VA BU O'YLANGAN QAROR.
    #
    # Reja uni `EXEMPT_ROUTES` ga qo'yishga ruxsat bergan («u resurs `id`
    # si qabul qilmaydi, ya'ni cross-tenant ma'nosi yo'q»), lekin istisno
    # marshrutni matritsadan TO'LIQ chiqarardi: tokensiz -> 401, buzilgan
    # token -> 401 va "javobda B ning izi yo'q" da'volari ham yo'qolardi.
    # Ular esa BU marshrut uchun juda ma'noli — u parol qabul qiladi.
    #
    # Buning o'rniga manzil ATAYIN DARHOL RAD ETILADIGAN qilib tanlandi:
    # `127.0.0.1:1` xususiylik darvozasidan o'tadi (loopback global emas)
    # va TCP darajasida DARHOL `ECONNREFUSED` beradi. Natija — 200 +
    # `ok=false` + `nvr_unreachable`, hech qanday tarmoq kutishi yo'q va
    # simulyatorga bog'liqlik ham yo'q.
    RouteSpec("POST", "/api/v1/nvr-devices/test-connection"): lambda _: {
        "address": "127.0.0.1:1",
        "username": "matritsa",
        "password": MATRIX_NVR_PASSWORD,
    },
    # --- 04-09: snapshot jadvali ---
    #
    # `starts_on` HAR CHAQIRUVDA BOSHQA (`_MATRIX_SCHEDULE_STARTS`) —
    # `_MATRIX_NVR_PORTS` bilan aynan bir xil sabab: `POST` HAQIQIY
    # profil yozadi va bir xil sana ikkinchi chaqiruvda
    # `409 schedule_period_overlaps` berardi (`create_seasonal()`
    # `starts_on` da BOSHLANADIGAN profilni rad etadi). O'shanda `POST`
    # ning YOZISH yo'li faqat birinchi testda bajarilardi.
    #
    # ⚠ Sana KELAJAKDA (`_future_date()` dan ham uzoqroq): `starts_on <=
    #   bugun` D-05 darvozasiga urilib 422 berardi va matritsa 404
    #   kutayotgan joyda validatsiya xatosini ko'rardi.
    RouteSpec("POST", "/api/v1/snapshot-schedules"): lambda _: {
        "name": "Matritsa jadvali",
        "starts_on": _matrix_schedule_start(),
        "times": ["06:00", "18:00"],
    },
    RouteSpec("PATCH", "/api/v1/snapshot-schedules/{schedule_id}"): lambda _: {
        "times": ["06:00", "18:00"],
    },
    # --- 05-10: nazoratchi javobi ---
    #
    # ⚠ TANADA AYNAN BITTA MAYDON BOR va bu D-18 ning aksi: `AnswerRequest`
    #   massiv ham, `market_id` ham, `shown_ai_verdict` ham qabul qilmaydi.
    #   Matritsa uchun muhimi — so'rov 422 da to'xtamasdan tenant
    #   darvozasigacha YETIB BORISHI.
    RouteSpec("POST", "/api/v1/review/{review_assignment_id}/answer"): lambda _: {
        "human_verdict": "occupied",
    },
    # --- 05-11: ko'r audit javobi ---
    #
    # ⚠ TANA AYNAN BIR XIL va bu ATAYIN: ikki marshrut BITTA
    #   `AnswerRequest` ni ishlatadi (ikkinchi sxema YOZILMAGAN). Alohida
    #   tana yozilsa matritsa ikki lug'atni solishtirib turardi va
    #   ulardan biri jimgina eskirardi.
    #
    # ⚠⚠ BU MARSHRUT UCHUN `review_assignment_id` FILLERI AYNAN TO'G'RI
    #   TURDAGI OBYEKT: B bozorining KO'R AUDIT topshirig'i
    #   (`market_b.blind_assignment_id`). Ya'ni 404 «bunday topshiriq
    #   yo'q» dan emas, TENANT chegarasidan keladi va matritsa haqiqatan
    #   o'lchaydi (05-10 deviatsiya #2 ogohlantirgan holat bu yerda
    #   MAVJUD EMAS).
    RouteSpec("POST", "/api/v1/review/blind/{review_assignment_id}/answer"): lambda _: {
        "human_verdict": "occupied",
    },
    # --- 01-05: foydalanuvchi yaratish ---
    #
    # ⚠⚠ BU YOZUV 06-08 DA QO'SHILDI VA U YANGI DARVOZANING BIRINCHI
    #   TOPILMASI (`test_no_matrix_route_returns_422`). Marshrut
    #   matritsada 01-05 dan beri turgan, lekin tanasi BO'LMAGANI uchun
    #   HAR SAFAR **422** olardi: ya'ni «javobda B ning izi yo'q» da'vosi
    #   validatsiya xatosi ustida tekshirilardi va marshrutning YOZISH
    #   yo'li UMUMAN ishlamasdi. Bu 02-08 deviatsiya #4 bilan aynan bir
    #   xil sinf va u bu yerda uch faza davomida JIMGINA yashiringan edi.
    #
    # ⚠ ROL `cashier` — matritsadagi ENG PAST daraja. `market_admin` yoki
    #   `platform_admin` so'ralsa javob rol-berish darvozasidan **403**
    #   olardi va marshrutning yozish yo'li yana sinalmay qolardi.
    RouteSpec("POST", "/api/v1/users"): lambda _: {
        "phone": MATRIX_STAFF_PHONE,
        "full_name": "Matritsa Xodimi",
        "roles": ["cashier"],
    },
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

INSPECTOR_ROUTES: frozenset[RouteSpec] = frozenset(
    {
        RouteSpec("GET", "/api/v1/review/uncertain/next"),
        RouteSpec("GET", "/api/v1/review/budget"),
        RouteSpec("POST", "/api/v1/review/{review_assignment_id}/answer"),
        # --- 05-11: ko'r audit ---
        RouteSpec("GET", "/api/v1/review/blind/next"),
        RouteSpec("POST", "/api/v1/review/blind/{review_assignment_id}/answer"),
    }
)
"""Matritsa NAZORATCHI sessiyasi bilan chaqiradigan marshrutlar (05-10).

=============================================================================
`PLATFORM_ADMIN_ROUTES` BILAN AYNAN BIR XIL MULOHAZA, BOSHQA ROL.

Uchala marshrut ham `OCCUPANCY_REVIEW` talab qiladi, u esa D-07
matritsasida FAQAT `inspector` da bor — bozor adminida ham, platforma
adminida ham YO'Q. Ya'ni odatdagi `market_a_headers` sessiyasi bilan
javob **403** bo'lardi va `test_cross_tenant_object_returns_404` aynan
403 ga qarshi yozilgan assertion'da yiqilardi.

"Yiqilmasin" deb 403 ni ruxsat etish eng yomon yechim bo'lardi: o'shanda
HUQUQ darvozasi TENANT darvozasini butunlay YOPIB qo'yardi va "begona
bozorning topshirig'iga javob yozib bo'lmaydi" degan da'vo HECH QACHON
sinalmasdi.

⚠ NAZORATCHI `auth_seed` DAN KELADI (`AuthSeed.inspector`): `two_markets`
  seed'ida bu rol YO'Q va uni o'sha faylga qo'shish beshta boshqa
  to'plamning a'zolik sanoqlariga tegardi.
=============================================================================
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
    nvr_b = seed.nvr.market_b
    snapshot_b = seed.snapshot.market_b
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
        # --- 03-06: NVR qatlami ---
        #
        # `stream_names` ATAYIN QO'SHILMAYDI: ular kamera qatorining
        # ichida `cam_<uuid>` shaklida va `camera_ids` allaqachon o'sha
        # UUID'ni qamraydi — ikkinchi marker bir xil qiymatni ikki xil
        # shaklda sanardi va nosozlik xabari chalkash bo'lardi.
        str(nvr_b.nvr_id),
        *(str(camera_id) for camera_id in nvr_b.camera_ids),
        *(str(run_id) for run_id in nvr_b.discovery_run_ids),
        # --- 04-09: snapshot qatlami ---
        #
        # `slot_ids` ATAYIN QO'SHILMAYDI: slot qatorining identifikatori
        # HECH QANDAY javobda ko'rinmaydi (jadval javobi `times` ni
        # beradi, `id` ni emas), ya'ni marker hech qachon ishlamaydigan
        # tekshiruv bo'lib qolardi (`stream_names` bilan bir xil qaror).
        str(snapshot_b.schedule_id),
        *(str(run_id) for run_id in snapshot_b.run_ids),
        *(str(snapshot_id) for snapshot_id in snapshot_b.snapshot_ids),
        str(snapshot_b.open_alert_id),
        str(snapshot_b.resolved_alert_id),
        # --- 06-08: billing qatlami ---
        #
        # ⚠ `service_date` MARKER EMAS va bo'la olmaydi: u SANA
        # (`CURRENT_DATE - 1`) va A bozorining o'z javoblarida ham AYNAN
        # o'sha qiymat uchraydi — ya'ni u YOLG'ON-QIZIL generatori
        # bo'lardi (`audit_log.id` bilan bir xil qaror).
        str(seed.billing.charge_id),
    )


def assert_no_foreign_data(response: httpx.Response, seed: TenantSeed, label: str) -> None:
    """Javob tanasida B bozorining birorta identifikatori ham yo'q."""
    body = response.text
    for marker in foreign_markers(seed):
        assert marker not in body, f"{label}: javobda B bozorining `{marker}` qiymati sizib chiqdi"


@pytest.fixture
def nvr_domain(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
) -> Iterator[NvrDomainSeed]:
    """`two_markets` USTIGA 3-fazaning NVR qatlami (CAM-01/CAM-08).

    `market_domain` bilan aynan bir xil naqsh va aynan bir xil sabab:
    `two_markets` ARGUMENT sifatida olinadi, ya'ni pytest fixture'larni
    teskari tartibda yopganda NVR qatlami bozorlardan OLDIN tozalanadi
    (aks holda `DELETE FROM markets` composite FK bilan yiqilardi).

    ⚠ B BOZORIGA KASHFIYOT YUGURISHI SHU YERDA QO'SHILADI. Seed unga
      ataylab yozmaydi («yugurishlar ro'yxati bo'sh» holati ham sinalishi
      kerak — `fixtures/nvr_domain.py` modul docstringi), matritsaga esa
      `run_id` uchun HAQIQIY B qatori kerak. Holat `succeeded`: `queued`/
      `running` qoldirilsa `0012` dagi qisman UNIQUE indeks shu NVR uchun
      har qanday yangi yugurishni bloklardi va 409 stsenariysi umuman
      sinalmasdi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        run_id = add_discovery_run(sync_owner_conn, seed.market_b, status="succeeded")
        # `MarketNvrRows` — MUZLATILGAN dataclass, ya'ni nusxa
        # `dataclasses.replace()` bilan olinadi. Qatorni yozib, uni
        # seed obyektiga QO'SHMASLIK eng jimgina xato bo'lardi:
        # `PARAM_FILLERS["run_id"]` bo'sh kortejga murojaat qilib
        # `IndexError` berardi va sabab matritsa mantig'ida ko'rinardi.
        yield replace(
            seed,
            market_b=replace(seed.market_b, discovery_run_ids=(run_id,)),
        )


@pytest.fixture
def snapshot_domain(
    sync_owner_conn: Connection[TupleRow],
    nvr_domain: NvrDomainSeed,
) -> Iterator[SnapshotDomainSeed]:
    """`nvr_domain` USTIGA 4-fazaning snapshot qatlami (04-09).

    ⚠ `nvr_domain` ARGUMENT sifatida olinadi va bu TARTIB MASALASI, uslub
      emas: pytest fixture'larni TESKARI tartibda yopadi, ya'ni bu
      qatlamning tozalashi NVR qatlamidan OLDIN ishlaydi. Teskari
      joylashuvda `cameras` hali `capture_runs` va `snapshots` tayanib
      turganda o'chirilardi va teardown FK buzilishi bilan yiqilardi
      (`fixtures/snapshot_domain.py::snapshot_rows` docstringidagi
      «TARTIB MUHIM» bandi).
    """
    with snapshot_rows(sync_owner_conn, nvr_domain) as seed:
        yield seed


@pytest.fixture
def occupancy_domain(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    snapshot_domain: SnapshotDomainSeed,
) -> Iterator[OccupancyDomainSeed]:
    """`snapshot_domain` USTIGA 5-fazaning bandlik qatlami (05-05/05-06).

    ⚠ `snapshot_domain` ARGUMENT sifatida olinadi va bu TARTIB masalasi,
      uslub emas (yuqoridagi uchala qatlam bilan bir xil sabab): pytest
      fixture'larni TESKARI tartibda yopadi, ya'ni bandlik qatlamining
      tozalashi kadrlar qatlamidan OLDIN ishlaydi. Teskari joylashuvda
      `snapshots` hali `occupancy_events` tayanib turganda o'chirilardi
      va teardown FK buzilishi bilan yiqilardi.

    ⚠ `market_domain` HAM KERAK va u `two_markets` ustiga qatlangan:
      `camera_zones` `stalls (market_id, id)` ga kompozit FK bilan
      tayanadi, ya'ni rastalarsiz birorta zona yozib bo'lmasdi.
    """
    with occupancy_rows(sync_owner_conn, two_markets, market_domain, snapshot_domain) as seed:
        yield seed


@pytest.fixture
def billing_rows(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> Iterator[MatrixBillingRows]:
    """B bozoriga BITTA `daily_charges` qatori — `charge_id` filleri uchun.

    =========================================================================
    ⛔ QATOR HAQIQIY BO'LISHI SHART (`PARAM_FILLERS` docstringidagi umumiy
       qoida). To'qilgan UUID bilan `GET /billing/charges/{id}` baribir 404
       berardi, lekin sababi TENANT chegarasi emas, «bunday hisob umuman
       yo'q» bo'lardi — ya'ni matritsa yashil turib HECH NIMANI o'lchamasdi.

    ⚠ `market_domain` ARGUMENT sifatida olinadi va bu TARTIB masalasi
      (`nvr_domain`/`snapshot_domain` bilan aynan bir xil sabab): pytest
      fixture'larni TESKARI tartibda yopadi, ya'ni bu qator rastalar va
      tariflardan OLDIN o'chiriladi va kompozit FK buzilmaydi.
    =========================================================================

    ⚠ O'CHIRISHDAN OLDIN BOZOR QORALAMAGA QAYTARILADI VA BUSIZ TOZALASH
      YIQILADI: `0020` `daily_charges` ga SHARTSIZ `BEFORE UPDATE OR
      DELETE` qo'riqchisini qo'yadi (D-07) va `DELETE` uchun yagona istisno
      — qoralama bozor. Naqsh `cleanup_billing_domain()` dan olingan;
      bayroq keyin ASL QIYMATIGA qaytariladi, ya'ni fixture o'zidan keyin
      hech qanday holat qoldirmaydi.
    """
    market_b = two_markets.market_b
    domain_b = market_domain.market_b
    charge_id, service_date = add_daily_charge(
        sync_owner_conn,
        market_id=market_b.id,
        stall_id=domain_b.stall_ids[0],
        vendor_id=domain_b.vendor_ids[0],
        tariff_id=domain_b.tariff_ids[0],
    )
    try:
        yield MatrixBillingRows(charge_id=charge_id, service_date=service_date)
    finally:
        row = sync_owner_conn.execute(
            "SELECT is_active FROM markets WHERE id = %s", (str(market_b.id),)
        ).fetchone()
        was_active = bool(row[0]) if row is not None else False
        sync_owner_conn.execute(
            "UPDATE markets SET is_active = false WHERE id = %s", (str(market_b.id),)
        )
        sync_owner_conn.execute("DELETE FROM daily_charges WHERE id = %s", (str(charge_id),))
        if was_active:
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = true WHERE id = %s", (str(market_b.id),)
            )


@pytest.fixture
def tenant_seed(
    two_markets: TwoMarketSeed,
    auth_seed: AuthSeed,
    market_domain: MarketDomainSeed,
    nvr_domain: NvrDomainSeed,
    snapshot_domain: SnapshotDomainSeed,
    occupancy_domain: OccupancyDomainSeed,
    billing_rows: MatrixBillingRows,
) -> TenantSeed:
    """A'zolik, domen, NVR, snapshot, bandlik va billing qatlamlarini bog'laydi.

    Har qatlam o'zidan pastdagisini O'ZI argument sifatida oladi, ya'ni
    oltalasi AYNI bozorlarni tavsiflaydi va teardown tartibi ham to'g'ri
    qoladi (har qatlam o'zidan pastdagisidan OLDIN tozalanadi).
    """
    return TenantSeed(
        base=two_markets,
        auth=auth_seed,
        domain=market_domain,
        nvr=nvr_domain,
        snapshot=snapshot_domain,
        occupancy=occupancy_domain,
        billing=billing_rows,
    )


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
async def market_a_inspector_headers(
    api_client: httpx.AsyncClient, tenant_seed: TenantSeed
) -> dict[str, str]:
    """A bozori NAZORATCHISINING sessiyasi (`OCCUPANCY_REVIEW` bilan).

    A'zoligi bitta -> bozor avtomatik tanlanadi. `must_change_password`
    bayrog'i `false` (`AuthSeed.inspector` docstringi), ya'ni parol
    darvozasi bu sessiyada UMUMAN qatnashmaydi va 403 ning sababi bir
    ma'noli qoladi.
    """
    return await session_headers(api_client, tenant_seed.auth.inspector.phone, SEED_PASSWORD)


@pytest.fixture
def headers_for(
    market_a_headers: dict[str, str],
    market_a_admin_headers: dict[str, str],
    market_a_inspector_headers: dict[str, str],
) -> Callable[[RouteSpec], dict[str, str]]:
    """Marshrutga MOS keladigan A-bozor sessiyasini tanlaydi.

    Tanlov IKKI ro'yxat bo'yicha (`PLATFORM_ADMIN_ROUTES`,
    `INSPECTOR_ROUTES`) va boshqa hech qanday shart yo'q: sessiya HAR
    DOIM **A bozoriga** tegishli, ya'ni "begona bozor obyekti -> 404"
    da'vosi o'zgarmaydi. Farq faqat HUQUQ darajasida.
    """

    def _pick(route: RouteSpec) -> dict[str, str]:
        if route in PLATFORM_ADMIN_ROUTES:
            return market_a_admin_headers
        if route in INSPECTOR_ROUTES:
            return market_a_inspector_headers
        return market_a_headers

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
    nvr_b = tenant_seed.nvr.market_b
    snapshot_b = tenant_seed.snapshot.market_b
    occupancy_b = tenant_seed.occupancy.market_b
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
            # --- 03-06 ---
            nvr_b.nvr_id,
            *nvr_b.camera_ids,
            *nvr_b.discovery_run_ids,
            # --- 04-09 ---
            #
            # ⚠ RO'YXAT `foreign_markers()` DAN MUSTAQIL TUZILGAN va bu
            # ATAYIN: u yerdagi ro'yxat «javobda uchramasin» uchun,
            # bu yerdagisi esa «filler AYNAN B ni ko'rsatsin» uchun.
            # Ikkalasini bitta funksiyaga birlashtirish darvozani
            # o'z-o'zini tekshiradigan holga keltirardi.
            snapshot_b.schedule_id,
            *snapshot_b.snapshot_ids,
            # --- 05-06 ---
            #
            # ⚠ FAQAT FAOL zonalar sanaladi. `superseded_zone_id` ATAYIN
            # yo'q: eskirgan zonani filler qilib qo'yish `DELETE` uchun
            # 404 ni TENANT chegarasi emas, HOLAT tufayli beradigan
            # qilardi (`deactivate()` `is_active = true` shartini qo'yadi)
            # va matritsa yashil bo'lib turib, boshqa narsani o'lchardi.
            *occupancy_b.active_zone_ids,
            # --- 05-10 ---
            occupancy_b.blind_assignment_id,
            # --- 06-08 ---
            #
            # ⚠ Qatorni `billing_rows` fixture'i yozadi; bu yerdagi da'vo
            # esa AYNAN o'sha qiymat filler'ga tushganini qulflaydi.
            tenant_seed.billing.charge_id,
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


BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})
"""Tana YUBORISH mumkin bo'lgan metodlar — `test_no_matrix_route_returns_422` ning doirasi.

`DELETE` ATAYIN yo'q: matritsa unga tana yubormaydi va yubormasligi ham
kerak (`BODY_FILLERS` docstringi).
"""

MIN_BODY_ROUTES = 30
"""Matritsada tana yuborish mumkin bo'lgan marshrutlarning QUYI CHEGARASI.

=============================================================================
⛔ BUSIZ YANGI DARVOZA BO'SH TO'PLAM USTIDA JIMGINA ROST BO'LARDI (S-6).

`test_no_matrix_route_returns_422` «hech bir marshrut 422 olmaydi» deydi.
Agar `tenant_resource_routes()` yurishi bir kun buzilib bo'shab qolsa (yoki
filtr noto'g'ri yozilsa) da'vo NOL marshrut ustida bajarilardi va darvoza
YASHIL bo'lib qolardi — ya'ni u aynan o'zi qo'riqlayotgan nosozlik sinfiga
tushardi (`test_matrix_is_not_empty` bilan bir xil mulohaza).

Chegara AMALDAGI SONDAN PAST (o'lchandi 2026-08-10: 38 marshrut):
`MINIMUM_MATRIX_ROUTES` bilan aynan bir xil qaror — u «bo'shab qolmadimi?»
degan savolga javob beradi, aniq sonni qulflamaydi.
=============================================================================
"""

QUERY_PARAM_ROUTES: frozenset[RouteSpec] = frozenset(
    {
        RouteSpec("PUT", "/api/v1/camera-zones"),
    }
)
"""MAJBURIY QUERY parametri bor va matritsa uni TO'LDIRMAYDIGAN marshrutlar.

=============================================================================
BULAR UCHUN **422** KUTILGAN JAVOB — VA U `BODY_FILLERS` NING YO'QLIGIDAN
KELMAYDI.

`PUT /api/v1/camera-zones` `camera_id` ni QUERY parametri sifatida oladi
(`main.py:213-218`: yo'l parametri bo'lsa u `cameras/coverage` shabloniga
tushib qolardi). Matritsa esa faqat YO'L parametrlarini to'ldiradi, ya'ni
so'rov tanadan qat'i nazar validatsiya darvozasida to'xtaydi.

⚠ ISTISNO RO'YXAT BO'LIB E'LON QILINADI, `try/except` yoki «422 ham
  mayli» degan yumshatish bilan EMAS: yumshatish butun darvozani
  ma'nosiz qilardi (aynan o'sha status kod qo'riqlanayapti). Ro'yxatga
  qo'shilgan har marshrutning tenant chegarasi BOSHQA joyda o'lchanishi
  SHART — bu holatda `tests/integration/test_camera_zones_api.py::
  test_cross_tenant_camera_returns_404` da (`test_route_coverage.py`
  ning `MINIMUM_MATRIX_ROUTES` docstringida ham shu yozilgan).
=============================================================================
"""


def test_query_param_routes_point_at_live_routes() -> None:
    """`QUERY_PARAM_ROUTES` da o'chirilgan marshrut QOLIB KETMAGAN.

    `BODY_FILLERS`/`FILE_FILLERS` ning staleness darvozalari bilan aynan
    bir xil sabab, bitta qo'shimcha xavf bilan: eskirgan istisno YANGI
    marshrutga jimgina tegib, uning 422 sini QONUNIY qilib ko'rsatardi.
    """
    live = set(all_routes(fastapi_app))
    stale = sorted(route.test_id for route in QUERY_PARAM_ROUTES if route not in live)

    assert not stale, f"`QUERY_PARAM_ROUTES` da mavjud bo'lmagan marshrutlar qolgan: {stale}"


BODY_ROUTES = tuple(
    sorted(
        route
        for route in MATRIX_ROUTES
        if route.method in BODY_METHODS and route not in QUERY_PARAM_ROUTES
    )
)
"""`test_no_matrix_route_returns_422` ning DOIRASI — hosila, qo'lda yozilgan emas.

⛔ ISTISNO PARAMETRIZATSIYADAN CHIQARILADI, test ICHIDA o'tkazib
   yuborilmaydi: bu fayl (va `test_route_coverage.py`) «kutilgan nosozlik»
   va «o'tkazib yuborish» markerlarini ATAYIN ishlatmaydi — marker
   qo'yilgan darvoza qizarmaydi, ya'ni teshik ochiq qolib hisobotda
   «o'tdi» bo'lib ko'rinardi.
"""


def test_matrix_has_enough_body_routes() -> None:
    """Tana yuboriladigan marshrutlar to'plami BO'SHAB QOLMAGAN (S-6).

    `test_no_matrix_route_returns_422` ning maxraji — ya'ni bu test
    o'sha darvozaning BO'SH TO'PLAM ustida rost bo'lib qolishiga
    qarshi (`MIN_BODY_ROUTES` docstringi).
    """
    assert len(BODY_ROUTES) >= MIN_BODY_ROUTES, (
        f"matritsada atigi {len(BODY_ROUTES)} ta tana yuboriladigan marshrut bor "
        f"(kamida {MIN_BODY_ROUTES} kutilgan) — `app.routes` yurishi yoki "
        "`EXEMPT_ROUTES` buzilgan bo'lishi mumkin"
    )


@pytest.mark.parametrize("route", BODY_ROUTES, ids=_route_id)
async def test_no_matrix_route_returns_422(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    headers_for: Callable[[RouteSpec], dict[str, str]],
    route: RouteSpec,
) -> None:
    """Tana talab qiladigan HAR BIR matritsa marshruti 422 DA TO'XTAMAYDI.

    =======================================================================
    ⛔⛔ BU DARVOZA MEXANIK KO'RLIKNI YOPADI — VA KO'RLIK O'LCHANGAN
        (`06-PATTERNS.md` §6, OP-8).

    Mavjud darvozalar `BODY_FILLERS` ning YETISHMASLIGINI ushlamaydi:

      * `test_body_fillers_point_at_live_routes` faqat ESKIRGAN yozuvni
        ushlaydi («xaritada bor, marshrutda yo'q») — teskarisini EMAS;
      * `test_cross_tenant_object_returns_404` faqat YO'L PARAMETRI BOR
        marshrutlarga tegadi, ya'ni `POST /api/v1/users` yoki
        `POST /api/v1/zones` uning doirasiga UMUMAN kirmaydi;
      * `test_no_route_leaks_other_market_identifiers` esa **422**
        javobida ham YASHIL qoladi: validatsiya xatosida B bozorining
        birorta identifikatori bo'lmaydi va da'vo BO'SH bajariladi.

    Natija: tanasi yozilmagan marshrut matritsada «bor» bo'lib turadi,
    endpoint mantiqi esa UMUMAN ishlamaydi — hech qanday test
    qizarmasdan. Bu 02-08 deviatsiya #4 (`BODY_FILLERS` ning O'ZI) va
    02-12 deviatsiya (`FILE_FILLERS`) bilan AYNAN bir xil sinf; ikkalasi
    ham sabotaj bilan topilgan, ya'ni uchinchi marta kutish kerak emas.

    ⛔ ANIQ STATUS QULFLANMAYDI (`test_file_routes_actually_execute` bilan
       bir xil qaror): javob 200, 201, 204, 403, 404 yoki 409 bo'lishi
       MUMKIN — matritsa qatorlarni HAQIQATAN yozadi va ketma-ket
       chaqiruvlar konfliktga tushishi qonuniy. Yagona ma'noli da'vo —
       ENDPOINT YUKLAMANI QABUL QILDI.
    =======================================================================

    Yangi POST/PUT/PATCH marshruti qo'shgan odam uchun bu shunday
    ko'rinadi: marshrut qo'shildi -> bu test qizardi -> `BODY_FILLERS` ga
    yaroqli tana qo'shildi -> tenant da'vosi o'sha kuniyoq ishlay
    boshladi. Hech qanday test yozish shart emas (D-32).
    """
    response = await call_route(api_client, route, tenant_seed, headers=headers_for(route))

    assert response.status_code != 422, (
        f"{route.test_id}: so'rov VALIDATSIYA darvozasida to'xtadi ({response.text}).\n"
        "Ya'ni endpoint mantiqi UMUMAN ishlamadi va bu marshrutning tenant "
        "da'vosi SINALMAY qoldi.\n"
        f"Tuzatish: `BODY_FILLERS[{route.test_id}]` ga yaroqli tana qo'shing "
        "(yoki fayl marshruti bo'lsa `FILE_FILLERS` ga). Majburiy QUERY "
        "parametri sababli 422 bo'lsa — `QUERY_PARAM_ROUTES` ga SABAB bilan."
    )


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


def test_inspector_routes_point_at_live_routes() -> None:
    """`INSPECTOR_ROUTES` da o'chirilgan marshrut QOLIB KETMAGAN.

    `PLATFORM_ADMIN_ROUTES` bilan aynan bir xil sabab: eskirgan yozuv
    o'zi zararsiz, lekin marshrut BOSHQA ma'noda qayta paydo bo'lganda u
    tug'ilishidanoq nazoratchi sessiyasi bilan chaqirilardi.
    """
    live = set(all_routes(fastapi_app))
    stale = sorted(route.test_id for route in INSPECTOR_ROUTES if route not in live)

    assert not stale, f"`INSPECTOR_ROUTES` da mavjud bo'lmagan marshrutlar: {stale}"


@pytest.mark.parametrize("route", sorted(INSPECTOR_ROUTES), ids=_route_id)
async def test_inspector_routes_really_need_the_review_permission(
    api_client: httpx.AsyncClient,
    tenant_seed: TenantSeed,
    market_a_headers: dict[str, str],
    route: RouteSpec,
) -> None:
    """Ro'yxatdagi marshrut bozor admini uchun ROSTDAN 403 beradi.

    Bu — `INSPECTOR_ROUTES` ning O'ZINI himoya qiladigan darvoza va u
    `test_platform_admin_routes_really_need_the_elevated_session` ning
    aynan jufti. Usiz kimdir hammaga ochiq marshrutni ro'yxatga qo'shib,
    uni kuchsizroq sessiyadan olib chiqib ketardi va matritsa buni
    umuman sezmasdi — ikkala sessiya ham A bozoriga tegishli, ya'ni javob
    baribir kelardi.

    ⚠ SO'ROV **A BOZORINING O'Z** topshirig'i bilan yuboriladi: begona
      identifikator bilan 404 (tenant darvozasi) 403 dan OLDIN kelib,
      huquq darvozasi umuman sinalmay qolardi.
    """
    own_assignment = tenant_seed.occupancy.market_a.blind_assignment_id
    own_path = route.path
    for name in route.param_names:
        own_path = own_path.replace("{" + name + "}", str(own_assignment))

    response = await call_route(
        api_client, route, tenant_seed, headers=market_a_headers, path=own_path
    )

    assert response.status_code == 403, (
        f"{route.test_id}: bozor admini {response.status_code} oldi — "
        "marshrut `INSPECTOR_ROUTES` da bo'lishi shart emas"
    )


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
