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

MINIMUM_MATRIX_ROUTES = 31
"""Matritsada kamida shuncha marshrut bo'lishi shart.

01-07 holatida qamrovda 7 marshrut bor edi (`/users` GET+POST,
`{user_id}` ning uchtasi, `/audit`, `/auth/me`) va chegara 3 edi.
02-08 unga 14 ta domen marshrutini qo'shdi (zonalar 4, toifalar 4,
rastalar 6) va chegara 12 ga ko'tarildi. 02-09 yana 8 tasini qo'shdi
(tariflar 4, kalendar 4) — chegara 20. 02-10 esa 7 tasini
(sotuvchilar 4, biriktirishlar 3), ya'ni amaldagi son 36 — chegara 28.
02-11 uchta usta marshrutini qo'shdi (`setup-status`, `activate`,
`DELETE /markets/{id}`) — amaldagi son 39, chegara 31.

⚠ `POST /api/v1/markets` bu sanoqqa KIRMAYDI: `/api/v1/markets` yo'li
`EXEMPT_ROUTES` da va istisno YO'L bo'yicha, metod bo'yicha emas. Uning
qamrovi `tests/integration/test_wizard_flow.py` da QAYTA tiklangan
(tokensiz -> 401; bozor admini -> 403; platforma admini -> 201) —
`EXEMPT_ROUTES` docstringidagi talab shuni buyuradi.

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
