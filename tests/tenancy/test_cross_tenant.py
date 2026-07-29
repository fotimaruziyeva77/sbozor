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

from typing import TYPE_CHECKING, Any, NamedTuple
from uuid import UUID

import pytest
from app.main import app as fastapi_app
from fixtures.admin_api import AUDIT_URL, USERS_URL, bearer, session_headers
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.security import encode_access

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures.two_markets import TwoMarketSeed

pytestmark = pytest.mark.tenancy

__all__ = [
    "EXEMPT_ROUTES",
    "PARAM_FILLERS",
    "RouteSpec",
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
        "(`users.is_platform_admin` bayrog'i) ochiladi, gibrid huquqli hisobga EMAS (CR-03)"
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
"""

EXEMPT_REASON_PREFIXES = ("auth bootstrap", "global", "health")
"""Ruxsat etilgan sabab toifalari (`test_exempt_reasons_use_a_known_category`)."""


PARAM_FILLERS: dict[str, Callable[[TwoMarketSeed], str]] = {
    "user_id": lambda seed: str(seed.market_b.cashier_user_id),
}
"""Yo'l parametri -> **B bozoridan** olingan qiymat.

Kelajakdagi parametr turlari (`stall_id`, `payment_id`, `vendor_id`, ...)
shu yerga qo'shiladi. Xaritada bo'lmagan parametr paydo bo'lsa
`test_all_path_params_have_fillers` va `test_no_unclassified_routes`
DARHOL yiqiladi — jimgina o'tkazib yuborish YO'Q.
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


def fill_path(route: RouteSpec, seed: TwoMarketSeed) -> str:
    """Yo'l parametrlarini **B bozori** qiymatlari bilan to'ldiradi."""
    path = route.path
    for name in route.param_names:
        path = path.replace("{" + name + "}", PARAM_FILLERS[name](seed))
    return path


def foreign_markers(seed: TwoMarketSeed) -> tuple[str, ...]:
    """B bozoriga tegishli, javobda HECH QACHON uchramasligi kerak bo'lgan satrlar.

    Faqat UUID va E.164 telefon: ular yetarlicha uzun va tasodifiy, ya'ni
    boshqa maydonga tasodifan mos kelmaydi. `audit_log.id` (butun son)
    ATAYIN bu ro'yxatda YO'Q — "42" kabi qiymat javobning istalgan
    joyidagi songa mos kelib YOLG'ON-QIZIL berardi; u
    `test_audit_list_never_leaks_the_other_market` da STRUKTURA bo'yicha
    (aynan `item["id"]` bilan) tekshiriladi.
    """
    market_b = seed.market_b
    return (
        str(market_b.id),
        *(str(user_id) for user_id in market_b.user_ids),
        *(str(role_id) for role_id in market_b.role_ids),
        *market_b.phones,
    )


def assert_no_foreign_data(response: httpx.Response, seed: TwoMarketSeed, label: str) -> None:
    """Javob tanasida B bozorining birorta identifikatori ham yo'q."""
    body = response.text
    for marker in foreign_markers(seed):
        assert marker not in body, f"{label}: javobda B bozorining `{marker}` qiymati sizib chiqdi"


@pytest.fixture
async def market_a_headers(
    api_client: httpx.AsyncClient, two_markets: TwoMarketSeed
) -> dict[str, str]:
    """A bozori adminining sessiyasi (a'zoligi bitta -> bozor avtomatik tanlanadi)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


# ===========================================================================
# T-01-75 / T-01-76 — A tokeni + B obyekti -> 404 (403 EMAS)
# ===========================================================================


@pytest.mark.parametrize("route", OBJECT_ROUTES, ids=_route_id)
async def test_cross_tenant_object_returns_404(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_a_headers: dict[str, str],
    route: RouteSpec,
) -> None:
    """A bozori tokeni + B bozori obyekti -> **404**, va AYNIQSA 403 EMAS.

    Ikkita alohida assert ATAYIN: birinchisi aynan 403 ga qarshi yozilgan,
    ikkinchisi kutilgan javobni qulflaydi. Faqat `== 404` bo'lganda
    kimdir kodni 403 ga o'zgartirsa xato xabari "404 kutilgan edi" deb
    chiqardi va sabab (information disclosure) ko'rinmasdi.
    """
    response = await api_client.request(
        route.method, fill_path(route, two_markets), headers=market_a_headers
    )

    assert response.status_code != 403, (
        f"{route.test_id}: 403 obyekt MAVJUDLIGINI tasdiqlaydi — 404 bo'lishi shart (T-01-76)"
    )
    assert response.status_code == 404, f"{route.test_id}: {response.status_code} — {response.text}"


@pytest.mark.parametrize("route", OBJECT_ROUTES, ids=_route_id)
async def test_cross_tenant_is_indistinguishable_from_unknown_id(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_a_headers: dict[str, str],
    route: RouteSpec,
) -> None:
    """Begona bozor ID'si va MAVJUD BO'LMAGAN ID — bayt-bayt bir xil javob.

    Status kodi yetarli emas: bir xil 404 ichida turli `detail` matni ham
    enumeration signali bo'lardi (`not_found` va `forbidden_market`).
    """
    unknown_path = route.path
    for name in route.param_names:
        unknown_path = unknown_path.replace("{" + name + "}", UNKNOWN_ID)

    foreign = await api_client.request(
        route.method, fill_path(route, two_markets), headers=market_a_headers
    )
    unknown = await api_client.request(route.method, unknown_path, headers=market_a_headers)

    assert foreign.status_code == unknown.status_code
    assert foreign.content == unknown.content, f"{route.test_id}: javob tanalari farq qiladi"


@pytest.mark.parametrize("route", MATRIX_ROUTES, ids=_route_id)
async def test_no_route_leaks_other_market_identifiers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_a_headers: dict[str, str],
    route: RouteSpec,
) -> None:
    """HAR BIR tenant marshruti: A tokeni bilan javobda B'ning izi ham yo'q.

    Bu — path parametri BO'LMAGAN marshrutlarni (`GET /users`,
    `GET /audit`, `GET /auth/me`) qamraydigan qism. Ular uchun "B obyektini
    so'rash" mumkin emas, ya'ni yagona ma'noli da'vo — javobda B'ning
    birorta identifikatori ham bo'lmasligi.
    """
    response = await api_client.request(
        route.method, fill_path(route, two_markets), headers=market_a_headers
    )

    assert_no_foreign_data(response, two_markets, route.test_id)


async def test_user_list_contains_no_other_market_members(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_a_headers: dict[str, str],
) -> None:
    """`GET /users` — A ning uchala a'zosi BOR, B ning birortasi ham YO'Q.

    Pozitiv qism ("A ko'rinadi") ham MAJBURIY: usiz ro'yxat butunlay bo'sh
    bo'lganda ham test yashil bo'lardi va hech nimani isbotlamasdi.
    """
    response = await api_client.get(USERS_URL, headers=market_a_headers)

    assert response.status_code == 200, response.text
    returned = {item["id"] for item in response.json()["items"]}
    assert {str(uid) for uid in two_markets.market_a.user_ids} <= returned
    assert returned & {str(uid) for uid in two_markets.market_b.user_ids} == set()


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
    two_markets: TwoMarketSeed,
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
    assert two_markets.market_b.audit_row_id not in ids, (
        f"{label}: B bozorining audit qatori A tokeni bilan ko'rindi"
    )
    assert_no_foreign_data(response, two_markets, f"GET {AUDIT_URL} ({label})")


async def test_audit_list_shows_the_own_market_probe_row(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
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
    assert two_markets.market_a.audit_row_id in ids


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
    two_markets: TwoMarketSeed,
    route: RouteSpec,
) -> None:
    """`Authorization` sarlavhasisiz har bir tenant marshruti 401 qaytaradi."""
    response = await api_client.request(route.method, fill_path(route, two_markets))

    assert response.status_code == 401, f"{route.test_id}: {response.status_code}"


@pytest.mark.parametrize("route", MATRIX_ROUTES, ids=_route_id)
async def test_malformed_token_is_rejected(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    route: RouteSpec,
) -> None:
    """Buzilgan token 401 — va sabab javobga CHIQMAYDI."""
    response = await api_client.request(
        route.method,
        fill_path(route, two_markets),
        headers=bearer("buzilgan.token.qiymati"),
    )

    assert response.status_code == 401, f"{route.test_id}: {response.status_code}"


@pytest.mark.parametrize("route", MATRIX_ROUTES, ids=_route_id)
async def test_expired_token_is_rejected(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
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
        user_id=two_markets.market_a.admin_user_id,
        market_id=two_markets.market_a.id,
        roles=["market_admin"],
        is_platform_admin=False,
        secret=test_settings.jwt_secret,
        issuer=test_settings.jwt_issuer,
        audience=test_settings.jwt_audience,
        ttl_minutes=-5,
    )

    response = await api_client.request(
        route.method, fill_path(route, two_markets), headers=bearer(expired)
    )

    assert response.status_code == 401, f"{route.test_id}: {response.status_code}"


# ===========================================================================
# Matritsaning O'ZINI himoya qiladigan da'volar
# ===========================================================================


def test_param_fillers_point_at_the_other_market(two_markets: TwoMarketSeed) -> None:
    """`PARAM_FILLERS` HAQIQATAN B bozorining qiymatlarini beradi.

    Agar biror filler bir kun A bozoriga (yoki tasodifiy UUID'ga)
    o'zgartirilsa, butun matritsa "404 keldi" deb YASHIL qolardi — 404
    o'sha holatda ham to'g'ri javob. Ya'ni matritsaning ma'nosi aynan shu
    yerda qulflanadi.
    """
    foreign_values = {
        str(value)
        for value in (
            two_markets.market_b.id,
            *two_markets.market_b.user_ids,
            *two_markets.market_b.role_ids,
        )
    }

    assert PARAM_FILLERS, "PARAM_FILLERS bo'sh — matritsa hech qanday obyektni sinamaydi"
    for name, filler in PARAM_FILLERS.items():
        value = filler(two_markets)
        assert value in foreign_values, f"`{name}` filleri B bozoriga tegishli emas: {value}"
        UUID(value)


def test_exempt_reasons_use_a_known_category() -> None:
    """Har bir istisno uchta ruxsat etilgan sabab turidan biriga tegishli.

    Erkin matn "vaqtincha o'tkazib yuborildi" kabi sababni ham qabul
    qilardi; toifalar ro'yxati esa yangi istisno qo'shmoqchi bo'lgan
    odamni uni UCHTA ma'lum sinfdan biriga joylashga majbur qiladi.
    """
    for path, reason in EXEMPT_ROUTES.items():
        assert reason.startswith(EXEMPT_REASON_PREFIXES), f"{path}: noma'lum sabab turi — {reason}"
