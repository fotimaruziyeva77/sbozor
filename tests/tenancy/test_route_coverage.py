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

⚠ 07-03 BITTASINI QO'SHDI (`GET /me/headline`, RECON-06) va CHEGARANI
  ATAYIN KO'TARMADI — 06-08 ning yuqoridagi qarori bilan AYNAN bir xil
  sabab: shart `>=`, ya'ni yangi marshrut darvozani qizartirmaydi va
  ko'tarish D-32 intizomi bo'yicha faza OXIRIDA, yakuniy o'lchov bilan
  bajariladi.

⚠ 07-10 BESHTASINI (`GET /reconciliation/report` · `/cases` ·
  `/cases/{case_id}` · `PATCH /cases/{case_id}` · `GET /hit-rate`),
  07-16 esa BITTASINI (`GET /reconciliation/delivery`, BOT-04) qo'shdi
  — CHEGARA YANA KO'TARILMADI, sabab yuqoridagi bilan AYNI.

⛔ `GET /reconciliation/delivery` DA YO'L PARAMETRI YO'Q, ya'ni u
   `PARAM_FILLERS` ni TALAB QILMAYDI va matritsaga o'zi tushadi
   (`test_no_unclassified_routes` yashil qoladi). U `EXEMPT_ROUTES` ga
   ham QO'SHILMAYDI: marshrut to'liq tenant resursi — bozorsiz
   sessiyada `403`, begona bozor qatorlari esa RLS bilan 0 qator.
   Uning yozuv YO'QLIGI (`POST`/`PATCH`/`DELETE` — 0 ta) alohida,
   `tests/integration/test_delivery_surface.py` da OpenAPI ustidan
   o'lchanadi: bu fayl marshrutlar BOR-YO'QLIGINI emas, ularning
   TASNIFLANGANINI qo'riqlaydi.

⛔ `/api/v1/me/headline` `EXEMPT_ROUTES` GA QO'SHILMAYDI, garchi qo'shni
   `/api/v1/me` o'sha ro'yxatda bo'lsa ham. Istisno YO'L bo'yicha aniq
   moslikda ishlaydi va ikki marshrut BOSHQA toifada: `/me` — PROFIL
   (ism, til), u bozorga tegishli EMAS va bozorsiz ham ishlaydi (D-13);
   `/me/headline` esa BOZORNING soni (tushum / navbat / kvitansiya) va
   u bozorsiz `409` beradi. Ya'ni u to'liq tenant resursi va matritsaning
   uchala token da'vosi ham unga QO'LLANISHI SHART.

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
# `/internal/bot/*` — SXEMASIZ VA SHAXSIY MA'LUMOTSIZ (07-08, D-05/D-10)
# ===========================================================================

BOT_INTERNAL_PREFIX = "/internal/bot"
"""⛔ `bot-service` ning yuzasi — REYESTRDA QAYD ETILADI, «unutilgan» emas.

=============================================================================
⛔⛔ NEGA BU YERDA, MARSHRUT FAYLIDA EMAS.

07-08 fazaning ISHONCH CHEGARASINI ochadi (D-01): birinchi marta xodim
BO'LMAGAN shaxs — sotuvchi — tizim ma'lumotini oladi. Ikkita kafolat shu
qarorni ushlab turadi va ikkalasi ham marshrut faylida KO'RINMAYDI:

  (a) to'rtala yo'l OpenAPI'ga CHIQMAYDI (`include_in_schema=False`),
      ya'ni ular ommaviy mijoz kontraktining qismi emas;
  (b) to'rtala yo'l `PERSONAL_ROUTES` ga TUSHMAYDI (D-05, G7-6) — javob
      modellarida `vendor_name` / `phone` / `full_name` maydonlari YO'Q.

Ikkalasi ham `include_in_schema=False` ni yoki javob modelini bir qator
o'zgartirish bilan JIMGINA yo'qolishi mumkin edi va hech qaysi mavjud
darvoza buni ko'rmasdi: sxemadan chiqarish `documented <= walked` shartini
BUZMAYDI (ya'ni yuqoridagi test yashil qolardi), shaxsiy maydon qo'shish
esa `PERSONAL_ROUTES` ni O'STIRARDI — lekin o'sish darvozasi `>=` bilan
yozilgan, ya'ni u ham yashil qolardi.
=============================================================================
"""


def _bot_internal_routes() -> list[str]:
    """`/internal/bot` bilan boshlanadigan yo'llar — YURISHDAN, ro'yxatdan emas."""
    return sorted(
        {
            route.path
            for route in all_routes(fastapi_app)
            if route.path.startswith(BOT_INTERNAL_PREFIX)
        }
    )


def test_the_bot_internal_surface_is_exactly_four_routes() -> None:
    """DARVOZANING NAZORATI — pastdagi ikki test BO'SH to'plamda yashil bo'lmaydi.

    ⛔ Usiz «sxemada yo'q» va «shaxsiy maydon yo'q» da'volari router
       o'chirilgan yoki qayta nomlangan holatda TRIVIAL ravishda rost
       bo'lardi (05-16 ning W-2 darsi).

    ⛔ DA'VO SHAKLI TENGLIK BO'LIB QOLADI (`==`, `>=` EMAS) — 07-18 da son
       uchdan to'rtga o'sganda ham. `>=` ga bo'shatish yuzaning JIMGINA
       kengayishiga yo'l ochardi: yangi `/internal/bot/*` marshruti hech
       qanday qarorsiz qo'shilib ketardi, holbuki bu yuzaning HAR BIR
       yo'li `EXEMPT_ROUTES` ga sabab bilan yozilishi shart.

    ⚠ TO'RTINCHISI — `POST /internal/bot/director/resolve` (07-18): u
      `market_notification_settings.director_chat_id` ning YAGONA yozuv
      yo'li va usiz direktor dayjestni umuman olmasdi.
    """
    assert _bot_internal_routes() == [
        "/internal/bot/director/resolve",
        "/internal/bot/resolve",
        "/internal/bot/vendor/payments",
        "/internal/bot/vendor/summary",
    ]


def test_no_bot_internal_route_is_documented_in_openapi() -> None:
    """⛔ To'rtala marshrut OpenAPI'da YO'Q (`include_in_schema=False`).

    OpenAPI mijozlar uchun yoziladi va bu yerda brauzer mijozi YO'Q:
    kontrakt bot-service bilan va u `app/api/internal/bot.py` ning O'ZI.
    Sxemaga chiqarish yuzani `/api/docs` ni ochgan har qanday odamga
    ko'rsatardi.
    """
    documented = [
        path for path in fastapi_app.openapi()["paths"] if path.startswith(BOT_INTERNAL_PREFIX)
    ]

    assert documented == [], documented


def test_no_bot_internal_route_enters_the_personal_data_gate() -> None:
    """⛔ D-05 / G7-6: `PERSONAL_ROUTES` O'SMAYDI.

    Yuza FAQAT identifikator, rasta kodi va sonlar qaytaradi. Ismni
    qo'shish uni auditli `GET /api/v1/vendors` bilan bir toifaga olib
    kirardi va u yerdagi kafolatlar (o'qish auditi + `VENDOR_VIEW`)
    servis-servis yo'lida MAVJUD EMAS — ya'ni sotuvchi ismi izsiz
    o'qilardi.
    """
    from tenancy.test_personal_data_coverage import PERSONAL_ROUTES

    leaked = [path for path in PERSONAL_ROUTES if path.startswith(BOT_INTERNAL_PREFIX)]

    assert leaked == [], leaked


# ===========================================================================
# `/reconciliation/*` — OLTI MARSHRUT, IKKI HUQUQ
# (07-10: RECON-01/RECON-02 · 07-16: BOT-04)
# ===========================================================================

RECONCILIATION_PREFIX = "/api/v1/reconciliation"
"""⛔ Nomuvofiqlik yuzasi — REYESTRDA QAYD ETILADI, «unutilgan» emas.

=============================================================================
⛔⛔ NEGA BU YERDA, VA NEGA `/internal/bot/*` DAN BOSHQA SHAKLDA.

Bot yuzasi matritsadan CHIQARILGAN (`EXEMPT_ROUTES`), ya'ni uning
mavjudligini alohida qayd etish kerak edi. Bu yuza esa TO'LIQ tenant
resursi va u matritsaga AVTOMATIK tushadi — `test_no_unclassified_routes`
`case_id` uchun filler talab qiladi va u `PARAM_FILLERS` da B bozorining
HAQIQIY case'i bilan yozilgan.

Shunday bo'lsa ham quyidagi uch da'vo KERAK va ular avtomatik qamrovdan
CHIQIB QOLADI:

  (a) marshrutlar soni va nomlari — router jimgina o'chirilsa yoki qayta
      nomlansa (b) va (c) TRIVIAL ravishda rost bo'lardi (05-16 ning W-2
      darsi, `test_the_bot_internal_surface_is_exactly_three_routes` ning
      aynan sababi);
  (b) oltalasi ham OpenAPI'da BOR — bot yuzasidan ATAYIN TESKARI da'vo:
      bu yuzaning mijozi BRAUZER va kontrakt `frontend/src/lib/*` ga
      shu sxemadan ko'chiriladi (07-15/07-16);
  (c) oltalasi ham `PERSONAL_ROUTES` GA TUSHMAYDI (G7-6, D-05).
=============================================================================
"""

RECONCILIATION_ROUTES = (
    "/api/v1/reconciliation/cases",
    "/api/v1/reconciliation/cases/{case_id}",
    "/api/v1/reconciliation/delivery",
    "/api/v1/reconciliation/hit-rate",
    "/api/v1/reconciliation/report",
)
"""Besh YO'L, olti MARSHRUT: `cases/{case_id}` da `GET` VA `PATCH` bor.

⚠ 07-16 BITTASINI QO'SHDI — `GET /delivery` (BOT-04). ⛔ VA U YOLG'IZ
  `GET`: yetkazilganlik navbati APPEND-ONLY (D-20) va uning yagona
  yozuvchisi JO'NATUVCHI (`app/jobs/outbox.py`). Qayta yuborish yoki
  holatni qo'lda o'zgartirish marshruti ⛔ UMUMAN yozilmagan —
  quyidagi to'plam tengligi buni AYNAN o'lchaydi va yangi metod
  qo'shilgan zahoti qizaradi.
"""


def _reconciliation_paths() -> list[str]:
    """`/api/v1/reconciliation` bilan boshlanadigan yo'llar — YURISHDAN olinadi."""
    return sorted(
        {
            route.path
            for route in all_routes(fastapi_app)
            if route.path.startswith(RECONCILIATION_PREFIX)
        }
    )


def test_the_reconciliation_surface_is_exactly_six_routes() -> None:
    """DARVOZANING NAZORATI — pastdagi ikki test BO'SH to'plamda yashil bo'lmaydi.

    ⛔ To'plam TENGLIGI bilan (D-31), «kamida oltitasi» bilan EMAS: yettinchi
       marshrut qo'shilishi ONGLI qaror va u shu yerda ko'rinishi kerak —
       ayniqsa u `PATCH` yoki `DELETE` bo'lsa (case tarixi o'zgarmas,
       D-14; yetkazilganlik navbati append-only, D-20).

    ⛔⛔ VA AYNAN SHU YERDA `[Qayta yuborish]` NING SERVER YARMI
        QULFLANADI: `/delivery` yo'lida ⛔ FAQAT `GET` bor. Qo'lda
        yuborish `uq_notification_outbox_market_id_dedupe_key` (D-21)
        bilan to'qnashardi yoki uni aylanib o'tib sotuvchiga IKKINCHI
        kvitansiya yuborardi; qo'lda `delivered` qo'yish esa nizoda
        (D-02) SOXTA DALIL bo'lardi (07-UI-SPEC §17.2).
    """
    walked = {
        (route.method, route.path)
        for route in all_routes(fastapi_app)
        if route.path.startswith(RECONCILIATION_PREFIX)
    }

    assert _reconciliation_paths() == list(RECONCILIATION_ROUTES)
    assert walked == {
        ("GET", "/api/v1/reconciliation/report"),
        ("GET", "/api/v1/reconciliation/cases"),
        ("GET", "/api/v1/reconciliation/cases/{case_id}"),
        ("PATCH", "/api/v1/reconciliation/cases/{case_id}"),
        ("GET", "/api/v1/reconciliation/hit-rate"),
        ("GET", "/api/v1/reconciliation/delivery"),
    }, sorted(walked)


def test_every_reconciliation_route_is_documented_in_openapi() -> None:
    """⛔ Oltalasi ham OpenAPI'da BOR — `/internal/bot/*` dan TESKARI da'vo.

    Bu yuzaning mijozi BRAUZER: 07-15 (hisobot) va 07-16 (case navbati +
    yetkazilganlik) klient sxemasini shu kontraktdan oladi.
    `include_in_schema=False` bilan yozilgan marshrut frontend
    darvozalariga UMUMAN ko'rinmasdi va ikki tomon jimgina ajralib
    ketardi.
    """
    documented = {
        (method.upper(), path)
        for path, operations in fastapi_app.openapi()["paths"].items()
        for method in operations
        if path.startswith(RECONCILIATION_PREFIX)
    }

    assert len(documented) == 6, sorted(documented)
    assert {path for _, path in documented} == set(RECONCILIATION_ROUTES)


def test_no_reconciliation_route_enters_the_personal_data_gate() -> None:
    """⛔ G7-6 / D-05: `PERSONAL_ROUTES` O'SMAYDI.

    Case yuzasi 6-fazaning C-10 qoidasini ⛔ KENGAYTIRMAYDI: u ham faqat
    `vendor_id` qaytaradi. Ismni qo'shish moliyaviy-nomuvofiqlik yuzasini
    shaxsiy-ma'lumot yuzasiga aylantirardi va undan `audit_read` +
    `VENDOR_VIEW` talab qilinardi.

    ⚠ Da'vo `test_personal_data_coverage.py::
      test_reconciliation_routes_are_not_personal` da IKKINCHI, MUSTAQIL
      shaklda o'lchanadi (u javob MODELINING maydonlaridan yuradi).
      Bu yerdagisi MARSHRUT REYESTRIDAN yuradi — ikki yo'nalish ATAYIN.
    """
    from tenancy.test_personal_data_coverage import PERSONAL_ROUTES

    leaked = [path for path in PERSONAL_ROUTES if path.startswith(RECONCILIATION_PREFIX)]

    assert leaked == [], leaked


# ===========================================================================
# `/reports/*` — UCH MARSHRUT, IKKI HUQUQ, BITTA SHAXSIY YUZA
# (08-07: RECON-04 ning JSON yarmi)
# ===========================================================================

REPORTS_PREFIX = "/api/v1/reports"
"""⛔ Davr hisobotlarining yuzasi — REYESTRDA QAYD ETILADI.

=============================================================================
⛔⛔ NEGA BU YERDA VA NEGA `/reconciliation/*` DAN FARQLI DA'VO BILAN.

Nomuvofiqlik yuzasi haqidagi uchinchi da'vo — «oltalasi ham
`PERSONAL_ROUTES` GA TUSHMAYDI» (G7-6). Bu yuzada esa u ⛔ **TESKARI**:
`/debtors` javobida sotuvchi F.I.Sh. BOR va u to'plamga ⛔ **TUSHISHI
SHART**.

⛔ FARQ «yumshatish» EMAS, IKKI BOSHQA SINF (D-07 ↔ Pitfall 1):

    `/billing/charges`, `/reconciliation/cases` — OPERATIV moliyaviy
        JSON. Ekranda ishlatiladi, ism `GET /vendors` dan KLIENTDA
        joinlanadi (C-10, §5.5). Ularga ism qo'shish TAQIQ.

    `/reports/debtors` — HUJJAT. «Kimdan undirish kerak?» savoliga
        qog'ozda javob beradi, ism SERVERDA joinlanadi va marshrut
        BITTA `audit_read` yozadi (sotuvchi boshiga emas).

Ya'ni `PERSONAL_ROUTES` ning bu yerda O'SISHI KUTILGAN va u
`MINIMUM_PERSONAL_ROUTES` (QUYI chegara, `>=`) ni buzmaydi. Pastdagi
uchinchi test o'sishni AYNAN BITTA marshrut bilan cheklaydi — ya'ni
to'rtinchi hisobot marshrutiga ism qo'shish ONGLI qaror bo'lib qoladi.
=============================================================================
"""

LEDGER_IMPORT_ROUTE = "/api/v1/reports/compare/ledger"
"""⛔ BU PREFIKSDAGI YAGONA YOZUV MARSHRUTI (D-17, 08-14).

Nom KLIENT KONTRAKTIDAN: `report-queries.ts::uploadLedger()` AYNAN
`${REPORTS_PATH}/compare/ledger?day=` ga boradi (08-03, TO'LQIN 1).
Reja `/three-way/ledger` degan edi — sabab va tanlov `reports.py` ning
5-bo'limida LITERAL yozilgan.

⛔ U «hisobotni tuzatish» yo'li EMAS va shuning uchun D-03 taqig'i ostiga
   tushmaydi: daftar TIZIMDA UMUMAN YO'Q — u tashqi qog'ozdan keladigan
   UCHINCHI manba, ya'ni bu marshrut KIRISH yo'li, hosila hisobotning
   tahriri emas.
"""

REPORTS_ROUTES = (
    "/api/v1/reports/accuracy.xlsx",
    "/api/v1/reports/anomalies",
    "/api/v1/reports/anomalies.xlsx",
    LEDGER_IMPORT_ROUTE,
    "/api/v1/reports/debtors",
    "/api/v1/reports/debtors.xlsx",
    "/api/v1/reports/revenue",
    "/api/v1/reports/revenue.xlsx",
)
"""Sakkiz YO'L, sakkiz MARSHRUT — yettitasi `GET`, BITTASI `POST`.

⛔ NOMLAR KLIENT KONTRAKTIDAN (`REPORT_KINDS`, 08-03; UI-SPEC §12.1,
   G-43a): `report-queries.ts::buildReportDataPath()` yo'lni AYNAN
   reyestr a'zosidan quradi, `buildReportPath()` esa o'sha a'zoga
   `.xlsx` qo'shadi. 08-07 rejasi `/receivables` va `/discrepancies`,
   08-12 rejasi esa `/receivables.xlsx` va `/discrepancies.xlsx` degan
   edi — sabab va tanlov `app/api/v1/reports.py` modul docstringining
   2-bandida.

⛔⛔ TO'RT EKSPORT MARSHRUTI HAM `GET` — VA BU DARVOZA MASALASI (R-3).

`POST` qilingan eksport `test_personal_data_coverage.py::get_routes()`
dan (u FAQAT `GET` ni yuradi) JIMGINA chiqib ketardi, ya'ni
`debtors.xlsx` na shaxsiy, na nomashaxsiy ro'yxatga tushardi va
yopiqlik testi ham uni ko'rmasdi. Ya'ni «bayt-marshrut tasniflanmay
qolmaydi» kafolati AYNAN eng xavfli marshrutda teshilardi.

⛔ `PATCH`/`DELETE` UMUMAN YO'Q: hisobot HOSILA (D-03) va uni
   «tuzatish» mumkin bo'lsa u ikkinchi haqiqat manbaiga aylanardi.
   Quyidagi to'plam tengligi buni AYNAN o'lchaydi.

⛔⛔ YAGONA `POST` — DAFTAR IMPORTI, VA UNING SABABI YUQORIDA
    (`LEDGER_IMPORT_ROUTE`). Metodlar to'plami MARSHRUT BO'YICHA
    qulflanadi, umumiy «hammasi GET» da'vosi bilan EMAS: aks holda
    ikkinchi `POST` (masalan «hisobotni qayta hisoblash») JIMGINA
    qo'shilib ketardi.

⚠ `/accuracy` JSON marshruti bu ro'yxatda YO'Q va bu KUTILGAN: aniqlik
  hisobining JSON yuzasi `GET /occupancy/accuracy` da yashaydi (05-12)
  va eksport AYNAN o'sha xizmatni chaqiradi. Ikkinchi JSON marshruti
  ikkinchi haqiqat manbai bo'lardi.

⚠ SON TEST NOMIDA YOZILGAN va u har safar QO'LDA yangilanadi (R-11
  darsi: chetlash JIMGINA, ONGLI yangilash esa NOMDA ko'rinadi).
  08-16 solishtiruvning O'QISH yuzasini qo'shadi — o'shanda bu test
  nomi ham, ro'yxat ham yana o'zgaradi.
"""

REPORTS_ROUTE_METHODS: dict[str, str] = {path: "GET" for path in REPORTS_ROUTES} | {
    LEDGER_IMPORT_ROUTE: "POST"
}
"""Yo'l -> UNING YAGONA metodi.

⛔ XARITA, UMUMIY DA'VO EMAS: 08-12 gacha bu yerda «hammasi `GET`» degan
   bitta jumla turardi va u to'g'ri edi. Endi bittasi `POST`, ya'ni o'sha
   jumlani «`GET` yoki `POST`» ga yumshatish IKKINCHI yozuv marshrutini
   ham jimgina o'tkazib yuborardi — xarita esa har marshrutning metodini
   NOM bilan qulflaydi.
"""


def _reports_paths() -> list[str]:
    """`/api/v1/reports` bilan boshlanadigan yo'llar — YURISHDAN olinadi."""
    return sorted(
        {route.path for route in all_routes(fastapi_app) if route.path.startswith(REPORTS_PREFIX)}
    )


def test_the_reports_surface_is_exactly_eight_routes() -> None:
    """DARVOZANING NAZORATI — pastdagi testlar BO'SH to'plamda yashil bo'lmaydi.

    ⛔ To'plam TENGLIGI bilan (D-31), «kamida sakkiztasi» bilan EMAS:
       to'qqizinchi marshrut qo'shilishi ONGLI qaror va u shu yerda
       ko'rinishi kerak — ayniqsa u YOZUV metodi bo'lsa.

    ⚠ SON 3 -> 7 (08-12: to'rt `.xlsx` eksporti) -> 8 (08-14: daftar
      importi) tarzida ONGLI ravishda oshirildi va HAR SAFAR TEST NOMI
      bilan birga. Nom sonni aytadi, ya'ni o'sish diff'da ko'rinadi.

    ⛔ METODLAR MARSHRUT BO'YICHA o'lchanadi (`REPORTS_ROUTE_METHODS`):
       `POST` bo'lgan EKSPORT bayt-tasnif darvozasidan jimgina chetlab
       o'tardi (`get_routes()` faqat `GET` ni yuradi), shuning uchun
       «hammasi `GET`» qoidasi FAQAT daftar importi uchun, NOM bilan
       yumshatilgan.
    """
    walked = {
        (route.method, route.path)
        for route in all_routes(fastapi_app)
        if route.path.startswith(REPORTS_PREFIX)
    }

    assert _reports_paths() == sorted(REPORTS_ROUTES)
    assert walked == {(method, path) for path, method in REPORTS_ROUTE_METHODS.items()}, sorted(
        walked
    )
    assert sum(1 for method in REPORTS_ROUTE_METHODS.values() if method != "GET") == 1, (
        "hisobot yuzasida BIRDAN ORTIQ yozuv marshruti paydo bo'ldi — "
        "hisobot HOSILA (D-03) va uni «tuzatish» ikkinchi haqiqat manbaini tug'dirardi"
    )


def test_every_reports_route_is_documented_in_openapi() -> None:
    """⛔ Sakkizalasi ham OpenAPI'da BOR — mijoz BRAUZER (`/reconciliation` naqshi).

    08-13/08-15 klient sxemasini shu kontraktdan oladi.
    `include_in_schema=False` bilan yozilgan marshrut frontend
    darvozalariga UMUMAN ko'rinmasdi va ikki tomon jimgina ajralib
    ketardi.

    ⚠ `.xlsx` marshrutlarining `response_model` i YO'Q (javob — BAYT),
      lekin ular ham hujjatlanadi: klient ularning MAVJUDLIGINI va
      so'rov parametrlarini shu kontraktdan biladi.

    ⚠ Daftar importi (`POST /compare/ledger`) ham shu yerda: uning
      `multipart/form-data` shakli va MAJBURIY `day` parametri klientga
      AYNAN shu kontraktdan ko'rinadi.
    """
    documented = {
        (method.upper(), path)
        for path, operations in fastapi_app.openapi()["paths"].items()
        for method in operations
        if path.startswith(REPORTS_PREFIX)
    }

    assert len(documented) == 8, sorted(documented)
    assert {path for _, path in documented} == set(REPORTS_ROUTES)


def test_only_the_debtors_route_carries_personal_data() -> None:
    """⛔⛔ SHAXSIY YUZA AYNAN BITTA — `/debtors`, VA U TO'PLAMDA BO'LISHI SHART.

    =======================================================================
    ⛔ IKKI TOMONLAMA DA'VO VA IKKALASI HAM MAJBURIY.

    (a) `/debtors` `PERSONAL_ROUTES` DA BOR. Bu «sizib chiqish» emas,
        D-07 ning O'ZI: reestr HUJJAT va ism unda QONUNIY. Marshrut
        to'plamga tushgani uchun undan `audit_read` VA `VENDOR_VIEW`
        AVTOMATIK talab qilinadi — ya'ni himoya reja intizomiga emas,
        MEXANIKAGA tayanadi. Agar u to'plamdan CHIQIB KETSA (masalan
        kimdir `vendor_name` ni `merchant` deb qayta nomlasa), o'sha
        ikki talab ham JIMGINA yo'qolardi va bu test buni aytadi.

    (b) QOLGAN IKKITASI TO'PLAMDA YO'Q. Tushum kun × summa, arxiv esa
        rasta kodi × sinf — ikkalasida ham odamni aniqlaydigan maydon
        YO'Q. `/revenue` yoki `/anomalies` ga «qulaylik uchun» ism
        qo'shilishi ularni ham audit talabiga tortardi va jurnal har
        tushum so'rovida qator olardi (`audit.py` da ATAYIN rad etilgan
        «blanket» holatining aynan sinfi).
    =======================================================================

    ⚠ Da'vo `test_personal_data_coverage.py::
      test_personal_data_routes_declare_read_audit` va
      `..._require_vendor_view` da IKKINCHI, MUSTAQIL shaklda
      o'lchanadi (ular javob MODELIDAN yuradi). Bu yerdagisi MARSHRUT
      REYESTRIDAN yuradi — ikki yo'nalish ATAYIN
      (`test_no_reconciliation_route_enters_the_personal_data_gate`
      bilan bir xil juftlik).

    ⚠⚠ TO'RT `.xlsx` MARSHRUTI BU TO'PLAMDA YO'Q VA BU KUTILGAN:
      `PERSONAL_ROUTES` javob MODELIDAN hosila bo'ladi, eksportning
      javobi esa BAYT — modeli umuman yo'q. Ular BOSHQA darvoza
      ostida: `test_personal_data_coverage.py::BINARY_PERSONAL_ROUTES`
      (`debtors.xlsx`) va `NON_PERSONAL_BINARY_ROUTES` (qolgan
      uchtasi). Ya'ni bu test «uchtadan bittasi shaxsiy» degan JSON
      da'vosini o'lchaydi va u eksport qo'shilgach ham AYNAN o'sha
      da'vo bo'lib qoladi.
    """
    from tenancy.test_personal_data_coverage import PERSONAL_ROUTES

    personal = sorted(path for path in PERSONAL_ROUTES if path.startswith(REPORTS_PREFIX))

    assert personal == ["/api/v1/reports/debtors"], personal


def test_only_the_ledger_import_needs_a_query_param_exemption() -> None:
    """⛔ ISTISNO AYNAN BITTA — VA SABAB METODDA, KELISHUVDA EMAS.

    =======================================================================
    ⛔⛔ YETTI `GET` MARSHRUTI ISTISNOSIZ QOLADI — O'LCHANGAN.

    Ularning hammasida `from`/`to` MAJBURIY query parametrlari bor va
    cross-tenant matritsasi query parametrlarini TO'LDIRMAYDI
    (`call_route()` faqat YO'L parametrlarini va tanani beradi), ya'ni
    so'rov validatsiya darvozasida **422** bilan to'xtaydi.

    ⛔ LEKIN 422 ULAR UCHUN HECH NIMANI BUZMAYDI: `QUERY_PARAM_ROUTES`
       ning YAGONA iste'molchisi — `test_no_matrix_route_returns_422`, u
       esa `BODY_ROUTES` (`POST`/`PUT`/`PATCH`) ustidan yuradi. `GET`
       marshruti o'sha to'plamga UMUMAN tushmaydi. Bu `GET /api/v1/
       reconciliation/hit-rate` ning AYNAN holati.

    =======================================================================
    ⛔⛔ DAFTAR IMPORTI (`POST`) ESA O'SHA TO'PLAMGA TUSHADI VA SHUNING
        UCHUN ISTISNOGA YOZILADI (08-14).

    Marshrut IKKI narsani talab qiladi va matritsa ikkalasini ham
    berolmaydi: MAJBURIY `?day=` (query parametri) va `multipart/form-
    data` FAYLI. `BODY_FILLERS` JSON yuboradi, `FILE_FILLERS` esa query
    parametrini qo'sha olmaydi, ya'ni javob HAR HOLDA 422 bo'lardi.

    ⛔ «422 ham mayli» DEB YUMSHATISH TAQIQ (`QUERY_PARAM_ROUTES`
       docstringi): yumshatish butun darvozani ma'nosiz qilardi. Istisno
       RO'YXATDA turadi va uning TENANT CHEGARASI BOSHQA joyda
       o'lchanadi — `tests/integration/test_three_way.py::
       test_the_other_markets_admin_cannot_write_into_market_a` (B
       bozorining admini A ning kuniga daftar yozolmaydi).

    =======================================================================
    ⚠ Yetti `GET` ning TENANT CHEGARASI ham ALOHIDA o'lchanadi:
      `tests/integration/test_reports_api.py::
      test_the_other_markets_director_never_sees_market_a_rows` —
      B bozorining direktori A ning davrini HAQIQIY parametrlar bilan
      so'raydi va javobda A ning izi YO'Q (nazorat holati bilan).
    =======================================================================
    """
    from tenancy.test_cross_tenant import QUERY_PARAM_ROUTES

    matrix = {route.path for route in tenant_resource_routes(fastapi_app)}
    exempted = sorted(
        route.test_id for route in QUERY_PARAM_ROUTES if route.path.startswith(REPORTS_PREFIX)
    )

    assert set(REPORTS_ROUTES) <= matrix, (
        "hisobot marshrutlari cross-tenant matritsasidan tushib qolgan — tokensiz/"
        "buzilgan token da'volari va «javobda B ning izi yo'q» tekshiruvi ular "
        f"uchun BAJARILMAYDI: {sorted(set(REPORTS_ROUTES) - matrix)}"
    )
    # ⛔ TO'PLAM TENGLIGI, «kamida bittasi» EMAS: ikkinchi istisno ONGLI
    #    qaror bo'lishi va shu qatorda ko'rinishi kerak.
    assert exempted == [f"POST_{LEDGER_IMPORT_ROUTE}"], exempted


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


# ===========================================================================
# REYESTRDAGI KODNING YETIB BORISHI (WR-08)
# ===========================================================================

BILLING_ERRORS_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "core-api"
    / "app"
    / "services"
    / "billing_errors.py"
)

UNREACHABLE_BY_DESIGN: dict[str, str] = {
    "CHARGE_IMMUTABLE": (
        "6-fazada hisobni O'ZGARTIRADIGAN marshrut UMUMAN yo'q (D-07: tuzatish "
        "faqat `charge_adjustments` orqali va uning yozuv yuzasi 7-fazaniki). "
        "Ya'ni bu kodning produseri hali TUG'ILMAGAN — u `daily_charges` ning "
        "`P0001` triggeri uchun OLDINDAN nomlangan. Reyestrdan olib tashlash "
        "`error-codes.test.mjs` ning uch qatlamli darvozasini (aniq son 14, "
        "`SERVER_BILLING_ERROR_CODES` ning tuzilish regeksi, `BILLING_ERROR_CODES` "
        "uchun `expected: 1`) va uchala locale matnini birdan siljitardi."
    ),
}
"""⛔ REYESTRDA BOR, LEKIN HALI HECH QAYSI MARSHRUT KO'TARMAYDIGAN KODLAR.

=============================================================================
⛔⛔ NEGA ISTISNO RO'YXATI, «hammasi yetib borsin» degan qat'iy shart EMAS.

Naqsh `EXEMPT_ROUTES` dan: yetib bormaslik O'ZI xato emas — SABABSIZ
yetib bormaslik xato. WR-08 o'lchagan holat aynan ikkinchisi edi: kod
qo'shildi, uchala tilga tarjima qilindi, `billing-errors.ts` ga
ko'zgulandi va HECH QAYERDAN qaytmasdi. Frontend darvozasi esa faqat
SONNI va matn qamrovini o'lchaydi, ya'ni u bunday kodni ko'ra olmasdi.

⚠ SABAB MAJBURIY VA U O'QILADI (`test_unreachable_codes_have_reason`):
  bo'sh satr bilan «istisno qildim» deb qo'yish yo'li yopiq.
=============================================================================
"""


_SERVER_REGISTRY_NAMES = ("COLLECT_ERROR_CODES", "SHIFT_ERROR_CODES", "BILLING_ERROR_CODES")
"""⛔ `SERVER_BILLING_ERROR_CODES` ning UCH tarkibiy qismi.

`CLIENT_ONLY_ERROR_CODES` ATAYIN yo'q: `network_unreachable` serverdan
HECH QACHON qaytmaydi va uni bu darvozaga qo'shish reyestrning O'Z
ta'rifiga («server nima qaytarishi mumkin») zid bo'lardi.
"""


def _server_registry_members() -> set[str]:
    """Uch server reyestrining a'zo KONSTANTA NOMLARI — AST dan HOSILA."""
    tree = ast.parse(BILLING_ERRORS_SOURCE.read_text(encoding="utf-8"))
    members: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        if node.target.id not in _SERVER_REGISTRY_NAMES or node.value is None:
            continue
        members.update(inner.id for inner in ast.walk(node.value) if isinstance(inner, ast.Name))
    return members


def _names_used_in_production_code() -> set[str]:
    """`app/` ostidagi ishlab chiqarish kodida NOMI bo'yicha ishlatilgan identifikatorlar.

    ⛔ `billing_errors.py` NING O'ZI CHIQARILADI: u konstantalarni
       ta'riflaydi va reyestr to'plamlarida qayta nomlaydi, ya'ni uni
       qo'shish HAR kodni «ishlatilgan» qilib ko'rsatardi va darvoza
       hech nimani o'lchamasdi.

    ⚠ QAMROV MARSHRUTLARDAN KENG va bu ONGLI: `market_closed` /
      `tariff_missing` marshrutga NOM sifatida emas, MA'LUMOT sifatida
      keladi (`billing_repo.resolve_stall_day_money()` ularni
      `unavailable_reason` ga yozadi, marshrut esa uni `_reject()` ga
      uzatadi). Faqat `_reject(NOM, ...)` shaklini izlaydigan darvoza
      ularni «yetib bormaydi» deb YOLG'ON ayblardi.
    """
    app_root = V1_ROUTER_DIR.parents[1]
    used: set[str] = set()
    for path in sorted(app_root.rglob("*.py")):
        if path.name == BILLING_ERRORS_SOURCE.name:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        used.update(node.id for node in ast.walk(tree) if isinstance(node, ast.Name))
    return used


def test_the_billing_error_registry_scan_is_not_empty() -> None:
    """DARVOZANING NAZORATI — parser reyestrni HAQIQATAN o'qidi.

    ⛔ Usiz pastdagi ikki test parser singanda ham YASHIL qolardi: bo'sh
       reyestrda «yetib bormaydigan kod yo'q» TRIVIAL ravishda rost
       bo'lardi (05-16 ning W-2 darsi).
    """
    members = _server_registry_members()

    assert len(members) >= 13, f"uch reyestrdan atigi {len(members)} a'zo o'qildi: {members}"
    assert {"NO_OPEN_SHIFT", "STALL_NOT_FOUND", "CHARGE_IMMUTABLE"} <= members, members
    assert "NETWORK_UNREACHABLE" not in members, (
        "`network_unreachable` SERVER reyestriga kirib qolgan — u mijoz tomonining kodi"
    )


def test_unreachable_codes_have_reason() -> None:
    """Har bir istisnoning bo'sh BO'LMAGAN sababi bor (`EXEMPT_ROUTES` naqshi)."""
    members = _server_registry_members()
    for name, reason in UNREACHABLE_BY_DESIGN.items():
        assert reason.strip(), f"{name}: yetib bormaslik sababi bo'sh"
        assert name in members, f"{name}: server reyestrida bunday a'zo YO'Q — istisno eskirgan"


def test_every_registered_billing_code_is_reachable_or_declared() -> None:
    """⛔ WR-08: reyestrdagi kod yo MARSHRUTDAN qaytadi, yo SABAB bilan e'lon qilinadi.

    =======================================================================
    ⛔⛔ NEGA MAVJUD DARVOZA BUNI KO'RA OLMASDI.

    `frontend/scripts/error-codes.test.mjs` uchta narsani o'lchaydi:
    aniq SON (14), reyestrlarning TUZILISHI va uchala locale'dagi
    `errorCause`/`errorFix` juftligi. Ularning birortasi ham «bu kodni
    kimdir QAYTARADIMI?» degan savolni bermaydi — ya'ni kod qo'shilib,
    tarjima qilinib, ko'zgulanib, HECH QAYERDAN qaytmasligi mumkin.
    WR-08 ikkita shunday kodni topdi (`no_open_shift`, `charge_immutable`)
    va birinchisi shu ish doirasida ULANDI (WR-01).

    ⚠ TO'PLAM TENGLIGI, «kamida bittasi» EMAS (D-31): ortiqcha e'lon
      qilingan istisno ham qizartiradi, ya'ni kod ulangach uni ro'yxatda
      unutib qo'yib bo'lmaydi.
    =======================================================================
    """
    unreachable = _server_registry_members() - _names_used_in_production_code()

    assert unreachable == set(UNREACHABLE_BY_DESIGN), (
        "Billing xato reyestri va ishlab chiqarish kodi AJRALIB KETDI.\n"
        f"  hech qayerda ishlatilmagan kodlar: {sorted(unreachable)}\n"
        f"  e'lon qilingan istisnolar:         {sorted(UNREACHABLE_BY_DESIGN)}\n"
        "Kodni marshrutga ULANG, yoki `UNREACHABLE_BY_DESIGN` ga SABAB bilan qo'shing."
    )
