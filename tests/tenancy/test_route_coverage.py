"""Marshrut qamrovi darvozasi — matritsaning O'ZINI himoya qiladi (T-01-78).

=============================================================================
BU FAYL ILOVANI EMAS, TESTNI SINAYDI.

`test_cross_tenant.py` marshrutlarni `app.routes` dan avtomatik oladi.
Avtomatik ro'yxatning kuchli tomoni — yangi endpoint o'zi qo'shiladi;
ZAIF tomoni — u JIMGINA bo'shab qolishi mumkin. Ikki yo'l bilan:

  1. Kimdir yangi marshrutni `EXEMPT_ROUTES` ga "vaqtincha" qo'shib
     qo'yadi va sabab yozmaydi;
  2. FastAPI ichki tuzilmasi o'zgaradi (0.140 da AYNAN shunday bo'ldi:
     `include_router()` natijasi endi `_IncludedRouter` o'ramida va
     `app.routes` TEKIS ro'yxat emas) — yurish kamroq marshrut topadi,
     matritsa qisqaradi va butun to'plam BARIBIR YASHIL qoladi.

Ikkalasi ham "test bor, lekin hech nimani tekshirmaydi" holatiga olib
keladi — bu testning umuman yo'qligidan YOMONROQ, chunki yashil CI
himoya bor degan ishonch beradi.

BU FAYLDA "KUTILGAN NOSOZLIK" VA "O'TKAZIB YUBORISH" MARKERLARI YO'Q —
ular ATAYIN ishlatilmaydi. Tasniflanmagan marshrut kutilgan nosozlik
emas: u qamrovdagi teshik va CI'ni YIQITISHI kerak. Marker qo'yilgan
darvoza esa qizarmaydi, ya'ni teshik ochiq qolib, hisobotda "o'tdi" deb
ko'rinadi.

(Bu qoida qabul mezonida grep bilan tekshiriladi, shuning uchun taqiqlangan
marker nomlari bu izohda ham LITERAL yozilmaydi — 01-01/01-03/01-05/01-06/
01-07 da aynan shu sinf xato besh marta takrorlangan.)
=============================================================================
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from app.main import app as fastapi_app

from tenancy.test_cross_tenant import (
    EXEMPT_REASON_PREFIXES,
    EXEMPT_ROUTES,
    PARAM_FILLERS,
    all_routes,
    parametrized_routes,
    tenant_resource_routes,
)

pytestmark = pytest.mark.tenancy

MINIMUM_MATRIX_ROUTES = 80
"""Matritsada kamida shuncha marshrut bo'lishi shart.

01-07 holatida qamrovda 7 marshrut bor edi (`/users` GET+POST,
`{user_id}` ning uchtasi, `/audit`, `/auth/me`) va chegara 3 edi.
02-08 unga 14 ta domen marshrutini qo'shdi (zonalar 4, toifalar 4,
rastalar 6) va chegara 12 ga ko'tarildi. 02-09 yana 8 tasini qo'shdi
(tariflar 4, kalendar 4) — chegara 20. 02-10 esa 7 tasini
(sotuvchilar 4, biriktirishlar 3), ya'ni amaldagi son 36 — chegara 28.
02-11 uchta usta marshrutini qo'shdi (`setup-status`, `activate`,
`DELETE /markets/{id}`) — amaldagi son 39, chegara 31. 02-12 to'rtta
import marshrutini qo'shdi (`template`, `stalls`, `vendors`,
`errors.xlsx`) — amaldagi son 43, chegara 34. 02-24 esa bittasini
(`POST /imports/staff`, MARKET-07) — amaldagi son 44, chegara 35.
03-06 yettita NVR marshrutini qo'shdi (`POST`/`GET /nvr-devices`,
`POST /test-connection`, `PATCH /{nvr_id}`, `POST /{nvr_id}/password`,
`POST /{nvr_id}/discover`, `GET /{nvr_id}/discovery-runs/{run_id}`) —
amaldagi son 51, chegara 42. 03-07 kameralarning oltitasini qo'shdi.
04-09 esa TO'QQIZTASINI: jadval beshta (`GET /today`, `GET ""`,
`POST ""`, `PATCH /{schedule_id}`, `DELETE /{schedule_id}`) va kadr
yuzasi to'rtta (`GET /capture-runs`, `GET /snapshots/{snapshot_id}`,
`GET /snapshots/{snapshot_id}/image`, `GET /alerts`) — chegara 48.
05-06 esa kamera zonalarining TO'RTTASINI qo'shdi (`GET /camera-zones`,
`PUT /camera-zones`, `GET /camera-zones/coverage`,
`DELETE /camera-zones/{camera_zone_id}`) — chegara 52. 05-10 nazoratchi
navbatining UCHTASINI (`GET /review/uncertain/next`, `GET /review/budget`,
`POST /review/{review_assignment_id}/answer`) — chegara 55. 05-11 esa ko'r
auditning IKKITASINI (`GET /review/blind/next`,
`POST /review/blind/{review_assignment_id}/answer`) — chegara 57.
05-12 bandlik hisobotining UCHTASINI qo'shdi (`GET /occupancy`,
`GET /occupancy/accuracy`, `GET /occupancy/round`) — chegara 60.

⚠ UCHALASI HAM `REPORT_VIEW` OSTIDA, ya'ni ular `INSPECTOR_ROUTES` ga
QO'SHILMAYDI: bozor admini sessiyasida bu huquq BOR va matritsa ularni
odatdagi yo'ldan yuradi. Nazoratchi esa ularga 403 oladi va bu AYNAN
kutilgan xulq — u `tests/integration/test_occupancy_report.py::
test_the_inspector_cannot_reach_the_report` da ALOHIDA o'lchanadi
(T-05-58: nazoratchi o'z aniqligini ko'rmasligi kerak).

⚠ Beshalasi ham `OCCUPANCY_REVIEW` talab qiladi, ya'ni ular matritsada
FAQAT `INSPECTOR_ROUTES` ro'yxati tufayli HAQIQIY yo'ldan yuradi. Ro'yxatga
qo'shilmagan yangi nazoratchi marshruti bozor admini sessiyasi bilan
chaqirilib **403** olardi va `test_cross_tenant_object_returns_404`
yiqilardi — ya'ni unutish JIMGINA emas, BALAND ovozda ko'rinadi.

⚠ To'rttadan FAQAT BITTASI (`DELETE`) 404 matritsasiga tushadi, chunki
faqat unda yo'l parametri bor. Qolgan uchtasida `camera_id` QUERY
parametri va matritsa uni to'ldirmaydi — ular 422 bilan javob beradi
va bu KUTILGAN: ularning tenant chegarasi
`tests/integration/test_camera_zones_api.py` da ALOHIDA o'lchanadi
(`test_cross_tenant_camera_returns_404`). Ular baribir matritsada
qoladi, ya'ni tokensiz/buzilgan/muddati o'tgan token da'volari va
«javobda B ning izi yo'q» tekshiruvi ular uchun ham bajariladi.

⚠ `camera_zone_id` matritsaga FAQAT `PARAM_FILLERS` ga B bozorining
HAQIQIY VA FAOL zonasi qo'shilgani uchun tushadi (`TenantSeed.occupancy`
qatlami). Eskirgan zona ko'rsatilsa 404 tenant chegarasi tufayli emas,
HOLAT tufayli qaytardi va matritsa boshqa narsani o'lchardi.

⚠ To'qqiztadan UCHTASI matritsaga FAQAT `PARAM_FILLERS` ga B bozorining
HAQIQIY `schedule_id` va `snapshot_id` qatorlari qo'shilgani uchun
tushadi. Ikkala qator ham `fixtures/snapshot_domain.py` seedida
mavjud va ular `TenantSeed.snapshot` qatlami orqali keladi.

⚠ `/internal/self-check` bu sanoqqa KIRMAYDI: u `EXEMPT_ROUTES` da va
sabab o'sha yerda yozilgan (`live-authz` bilan bir xil toifa).

⚠ Yettitasidan IKKITASI (`{nvr_id}` va `{run_id}`) matritsaga FAQAT
`PARAM_FILLERS` ga B bozorining HAQIQIY qatorlari qo'shilgani uchun
tushadi. `run_id` uchun qator seed'da YO'Q va uni `nvr_domain` fixture'i
o'zi yozadi — sabab `test_cross_tenant.TenantSeed.nvr` docstringida.

⚠ Import marshrutlarining UCHTASI `multipart/form-data` va ular
matritsaga FAQAT `FILE_FILLERS` tufayli haqiqiy yo'ldan tushadi. Filler
o'chirilsa marshrut ro'yxatda QOLADI (ya'ni bu chegara qizarmaydi),
lekin so'rov 422 da to'xtab, da'vo sinalmay qolardi — o'sha holatni
`test_file_fillers_point_at_live_routes` va matritsaning o'z testlari
ushlaydi.

⚠ `POST /api/v1/markets` bu sanoqqa KIRMAYDI: `/api/v1/markets` yo'li
`EXEMPT_ROUTES` da va istisno YO'L bo'yicha, metod bo'yicha emas. Uning
qamrovi `tests/integration/test_wizard_flow.py` da QAYTA tiklangan
(tokensiz -> 401; bozor admini -> 403; platforma admini -> 201) —
`EXEMPT_ROUTES` docstringidagi talab shuni buyuradi.

⛔ 06-14 CHEGARANI 60 -> 80 GA KO'TARDI VA SON O'LCHANGAN, TAXMIN
QILINMAGAN: `len(tenant_resource_routes(app))` = **88** (2026-08-11).
Ulardan AYNAN **11 tasi** 6-fazaniki va ular nomma-nom sanaladi:

    GET  /billing/pending · /billing/charges · /billing/charges/{charge_id}
         /billing/anomalies                                      (4)
    POST /payments · /payments/{payment_id}/reverse
    GET  /payments/recent                                        (3)
    POST /shifts · /shifts/{shift_id}/close
    GET  /shifts · /shifts/open                                  (4)

⚠ 06-08 CHEGARANI ATAYIN KO'TARMADI va u haq edi: shart `>=`, ya'ni
  yangi marshrut darvozani QIZARTIRMAYDI. Ko'tarish esa D-32 intizomi
  bo'yicha YAKUNIY o'lchov bilan, bir marta va SABAB bilan bajariladi —
  aynan shu yerda.

⚠ 60 dan 80 gacha bo'lgan farq 6-fazaning 11 marshrutidan KATTA va bu
  ham o'lchangan fakt: chegara 05-12 dan beri ko'tarilmagan, ya'ni u
  faza oxiriga kelib amaldagi sondan 17 ta orqada qolgan edi. Yangi
  qiymat faylning O'Z konventsiyasini tiklaydi (amaldagi sondan ~8-9
  past — 02-10 dan beri saqlanadigan masofa).

Chegara ATAYIN AMALDAGI SONDAN PAST — u "matritsa bo'shab qolmadimi?"
degan savolga javob beradi, aniq sonni qulflamaydi. Aniq son yozilganda
har yangi endpoint bu faylni tahrirlashni talab qilardi va darvoza
bezovta qiluvchi shovqinga aylanib, oxir-oqibat "shunchaki raqamni
oshiring" refleksini tug'dirardi — o'shanda u haqiqiy qisqarishni ham
o'tkazib yuborardi.
"""


def test_no_unclassified_routes() -> None:
    """HAR BIR marshrut yo istisno, yo TO'LIQ sinaladigan holatda bo'lishi shart.

    "Sinaladigan holat" — marshrutning har bir path parametri uchun
    `PARAM_FILLERS` da qiymat bor. Filler bo'lmasa matritsa o'sha
    marshrutni CHAQIRA OLMAYDI, ya'ni u ro'yxatda ko'rinib turib
    tekshirilmay qolardi.

    Yangi endpoint qo'shgan odam uchun bu shunday ko'rinadi: `/api/v1/
    stalls/{stall_id}` qo'shildi -> bu test yiqiladi -> `PARAM_FILLERS`
    ga `stall_id` (B bozorining rastasi) qo'shiladi -> matritsa o'sha
    marshrutni avtomatik qamraydi. Hech qanday test yozish shart emas.
    """
    unclassified: list[str] = []
    for route in tenant_resource_routes(fastapi_app):
        missing = [name for name in route.param_names if name not in PARAM_FILLERS]
        if missing:
            unclassified.append(f"{route.test_id} -> PARAM_FILLERS da yo'q: {', '.join(missing)}")

    assert not unclassified, (
        "Quyidagi marshrutlar cross-tenant matritsasida TASNIFLANMAGAN.\n"
        "Ularni yo `PARAM_FILLERS` ga (B bozori qiymati bilan), yo "
        "`EXEMPT_ROUTES` ga (sabab bilan) qo'shing:\n  " + "\n  ".join(unclassified)
    )


def test_exempt_routes_still_exist_in_the_app() -> None:
    """`EXEMPT_ROUTES` da o'chirilgan marshrut QOLIB KETMAGAN.

    Eskirgan istisno o'zi zararsiz, lekin u ro'yxatni ishonchsiz qiladi:
    keyingi o'qiyotgan odam "bu yerda 13 ta istisno bor" deb ko'radi va
    ularning nechtasi haqiqiy ekanini bilmaydi. Eng yomoni — o'chirilgan
    yo'l keyinchalik BOSHQA ma'noda qayta paydo bo'lsa, u tug'ilishidanoq
    istisno bo'lib turadi.
    """
    live_paths = {route.path for route in all_routes(fastapi_app)}
    stale = sorted(path for path in EXEMPT_ROUTES if path not in live_paths)

    assert not stale, f"`EXEMPT_ROUTES` da mavjud bo'lmagan marshrutlar qolgan: {stale}"


def test_exempt_routes_have_reason() -> None:
    """Har bir istisnoning bo'sh BO'LMAGAN va ma'lum toifadagi sababi bor."""
    for path, reason in EXEMPT_ROUTES.items():
        assert reason.strip(), f"{path}: istisno sababi bo'sh"
        assert reason.startswith(EXEMPT_REASON_PREFIXES), (
            f"{path}: sabab uchta ma'lum toifadan biri bilan boshlanishi kerak "
            f"({', '.join(EXEMPT_REASON_PREFIXES)}) — hozir: {reason}"
        )


def test_matrix_is_not_empty() -> None:
    """Matritsa bo'shab qolmagan — YOLG'ON-YASHIL ning eng jimgina shakli.

    `parametrize` bo'sh ro'yxat bilan chaqirilganda pytest hech qanday
    test yaratmaydi va to'plam "hammasi o'tdi" deb tugaydi.
    """
    matrix = tenant_resource_routes(fastapi_app)

    assert len(matrix) >= MINIMUM_MATRIX_ROUTES, (
        f"matritsada atigi {len(matrix)} marshrut bor — "
        f"`app.routes` yurishi yoki `EXEMPT_ROUTES` buzilgan"
    )


def test_object_routes_are_covered() -> None:
    """Path parametri bor marshrutlar HAM mavjud — "A tokeni + B obyekti" da'vosi ishlaydi.

    `test_matrix_is_not_empty` dan alohida: matritsa faqat ro'yxat
    endpointlaridan iborat bo'lib qolsa, "404 qaytaradi" degan ASOSIY
    da'vo umuman bajarilmasdi, lekin matritsa bo'sh ham bo'lmasdi.
    """
    object_routes = parametrized_routes(fastapi_app)

    assert object_routes, (
        "path parametri bor birorta tenant marshruti topilmadi — "
        "cross-tenant 404 da'vosi hech qayerda sinalmayapti"
    )


def test_all_path_params_have_fillers() -> None:
    """Matritsadagi HAR BIR path parametri uchun `PARAM_FILLERS` da qiymat bor.

    `test_no_unclassified_routes` bilan bir xil invariantni TESKARI
    tomondan tekshiradi: u marshrutdan parametrga qaraydi, bu esa
    matritsa yig'ib bergan parametrlar to'plamini xarita bilan
    solishtiradi. Ikkalasi ham bo'lishi kerak, chunki birinchisi
    `tenant_resource_routes()` buzilib bo'shab qolsa jimgina o'tib
    ketardi.
    """
    required = {name for route in parametrized_routes(fastapi_app) for name in route.param_names}

    assert required <= set(PARAM_FILLERS), (
        f"`PARAM_FILLERS` da yo'q parametrlar: {sorted(required - set(PARAM_FILLERS))}"
    )


def test_route_walker_matches_openapi() -> None:
    """`app.routes` yurishi FastAPI ning OMMAVIY kontrakti bilan mos.

    NEGA KERAK: yurish FastAPI ning ICHKI tuzilmasiga tayanadi
    (`_IncludedRouter.original_router`, `include_context.prefix`). U
    o'zgarganda yurish istisno KO'TARMAYDI — u shunchaki kamroq marshrut
    topadi, `parametrize` qisqaradi va butun matritsa jimgina yo'qoladi.

    `app.openapi()` esa hujjatlashtirilgan, barqaror yuza. Undagi har bir
    (yo'l, metod) yurish natijasida BO'LISHI SHART. Teskari yo'nalish
    tekshirilmaydi: `/api/docs`, `/redoc` va `openapi.json` OpenAPI
    sxemasida ATAYIN yo'q.
    """
    walked = {(route.method, route.path) for route in all_routes(fastapi_app)}
    documented = {
        (method.upper(), path)
        for path, operations in fastapi_app.openapi()["paths"].items()
        for method in operations
    }

    assert documented <= walked, (
        "`app.routes` yurishi OpenAPI'dagi marshrutlarni topa olmadi "
        f"(FastAPI ichki tuzilmasi o'zgargan bo'lishi mumkin): {sorted(documented - walked)}"
    )


def test_no_route_is_both_exempt_and_in_the_matrix() -> None:
    """Istisno va matritsa to'plamlari KESISHMAYDI (yurish mantiqi to'g'ri).

    Kesishuv bo'lsa filtr ishlamayotgan bo'lardi va istisno qilingan
    marshrutlar ham 401/404 da'volari ostiga tushib, sabablari
    noaniq nosozliklar berardi.
    """
    matrix_paths = {route.path for route in tenant_resource_routes(fastapi_app)}

    assert matrix_paths & set(EXEMPT_ROUTES) == set()


# ===========================================================================
# BILLING DOMENINING `detail` KONVENSIYASI (CR-04 / WR-06)
# ===========================================================================

V1_ROUTER_DIR = Path(__file__).resolve().parents[2] / "services" / "core-api" / "app" / "api" / "v1"
"""Marshrut modullari — MANBA sifatida o'qiladi, import qilinmaydi.

⚠ `HTTPException(detail=...)` ning SHAKLI ish vaqtida ko'rinmaydi: u
  faqat istisno KO'TARILGANDA tug'iladi va o'sha shox ko'pincha
  testlarda umuman ochilmaydi (CR-04 aynan shunday yashiringan edi —
  `/pending` ning 404 i uchun test bor edi, lekin u `detail` ning
  TURINI o'lchamasdi). Shuning uchun darvoza AST ustidan yuradi.
"""

_BILLING_ERRORS_MODULE = "app.services.billing_errors"
"""Domen a'zoligi shu import bilan aniqlanadi — QO'LDA YOZILGAN RO'YXAT EMAS.

⛔ D-32: darvoza qamrovi HOSILA bo'lishi shart. `billing_errors` dan kod
   import qilgan HAR QANDAY yangi marshrut moduli darvozaga O'ZI kiradi;
   qo'lda yozilgan uchtalik esa to'rtinchi router qo'shilgan kuni jimgina
   eskirardi.

⚠ QAMROV ATAYIN 6-FAZA BILAN CHEKLANGAN: `occupancy.py`, `nvr.py` va
  boshqa eski marshrutlar hamon lug'at shaklini ishlatadi va ularni
  o'zgartirish bu fazaning ishi EMAS — o'sha modullar `billing_errors`
  ni import qilmaydi, ya'ni ular bu darvozaga tushmaydi.
"""


def _billing_router_sources() -> dict[str, ast.Module]:
    """`billing_errors` ni import qilgan `api/v1/*.py` modullari — {nom: AST}."""
    found: dict[str, ast.Module] = {}
    for path in sorted(V1_ROUTER_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports_registry = any(
            isinstance(node, ast.ImportFrom) and node.module == _BILLING_ERRORS_MODULE
            for node in ast.walk(tree)
        )
        if imports_registry:
            found[path.name] = tree
    return found


def test_the_billing_router_scan_actually_finds_the_routers() -> None:
    """DARVOZANING NAZORATI — hosila ro'yxat BO'SHAB QOLMAGAN (W-2 darsi).

    ⛔ USIZ PASTDAGI TEST ABADIY YASHIL BO'LARDI: `_BILLING_ERRORS_MODULE`
       nomi o'zgarsa yoki fayllar ko'chirilsa skan **nol** modul topardi
       va «birorta lug'at yo'q» degan da'vo TRIVIAL bajarilardi. Bu 05-16
       ning W-2/W-3 sinfidagi aynan o'sha nosozlik.

    ⚠ TENGLIK EMAS, QAMRAB OLISH: yangi billing routeri qo'shilsa bu test
      qizarmasligi kerak (aks holda hosilalik ma'nosini yo'qotardi) —
      lekin uchtasining YO'QOLISHI qizartiradi.
    """
    modules = set(_billing_router_sources())

    assert {"billing.py", "payments.py", "shifts.py"} <= modules, (
        f"6-fazaning marshrut modullari skanga tushmadi: topilgani {sorted(modules)}"
    )


def test_every_billing_http_exception_sends_a_string_detail() -> None:
    """⛔ CR-04 / WR-06: billing marshrutlarida `detail` — SATR, LUG'AT EMAS.

    =======================================================================
    ⛔⛔ NEGA BU DARVOZA KERAK — DA'VO KLIENT TOMONDA O'LCHANADI.

    `frontend/src/lib/api-client.ts::detailOf()` `detail` ni FAQAT satr
    bo'lganda o'qiydi (`typeof parsed.data.detail === "string"`), aks
    holda `""` qaytaradi. Ya'ni lug'at yuborilgan har bir kod klientga
    UMUMAN yetib bormaydi va `billing-errors.ts` uni tanimay
    `errors.generic` chizadi.

    O'lchangan oqibat (CR-04): `GET /billing/pending` ning 404 i lug'at
    yuborardi, `collect-session.tsx::notFound` HAR DOIM `false` bo'lardi,
    `collectState()` ning `"not-found"` holati va `StallLookup` ning
    «Rasta topilmadi» shoxi — O'LIK KOD. Kassir noto'g'ri kod tergan
    bo'lsa «yuklab bo'lmadi» + [Qayta urinish] ko'rardi va har urinish
    o'sha 404 ni qaytarardi.

    ⛔ TESTLAR BU HOLATNI KO'RMAGANDI: `test_payments_api.py::_detail()`
       `detail` ning satr ekanini TASDIQLAYDI, lekin u faqat `payments`
       marshrutlaridan o'tadi. `billing`/`shifts` ning `_market_id()`
       shoxi esa hech qaysi testda umuman ochilmaydi.
    =======================================================================
    """
    offenders: list[str] = []
    for name, tree in _billing_router_sources().items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Name) and func.id == "HTTPException"):
                continue
            for keyword in node.keywords:
                if keyword.arg == "detail" and isinstance(keyword.value, ast.Dict):
                    offenders.append(f"{name}:{keyword.value.lineno}")

    assert not offenders, (
        "Billing marshrutlarida `detail` LUG'AT bilan yuborilgan — klient uni "
        "o'qiy olmaydi va kod `errors.generic` ga tushadi. `_reject(kod, status)` "
        f"ishlating: {offenders}"
    )
