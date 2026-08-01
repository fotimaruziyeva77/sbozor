"""Shaxsiy ma'lumot qaytaradigan `GET` marshrutlarining DARVOZASI (D-09, CR-02).

=============================================================================
BU FAYL BUGUNGI XATONI EMAS, UNING QAYTISHINI BLOKLAYDI.

CR-02 "e'lon qilinib tashlab qo'yilgan sim" sinfidagi xato edi:
`app/security/audit.py` da `TABLE_STALLS` konstantasi bor, uning
docstringi shu marshrutlarni nomma-nom sanaydi — va repo bo'yicha qidiruv
uni o'z ta'rifidan tashqari hech qayerda topmasdi. Ya'ni SABAB yozilgan,
KOD yozilmagan. Uchala marshrut o'n yetti reja davomida yashil CI ostida
sotuvchi F.I.Sh. va telefonini izsiz berib turdi va buni birorta ijrochi
o'z-o'zidan sezmadi — uni faqat mustaqil kod ko'rigi topdi.

Uchta marshrutni qo'lda tuzatish bir martalik ish. Bu test esa QOIDANI
kodga aylantiradi: javobiga `vendor_name` qo'shgan har qanday YANGI
marshrut, agar u o'qish auditini va `VENDOR_VIEW` ni e'lon qilmasa, CI'ni
qizartiradi. Yozgan odam sababni SHU YERDA o'qiydi — bir yildan keyin
ham.
=============================================================================

MARSHRUT GRAFI O'QILADI, MANBA MATNI EMAS. Muqobil yechim — fayllarni
regex bilan tirnash — dekorator shakli o'zgarganda (alias orqali berilsa,
boshqa qatorga ko'chirilsa, `functools.partial` ga o'ralsa) hech nima
topmasdi va darvoza JIMGINA yashil bo'lib qolardi. Ya'ni unutish xavfsiz
tomonga emas, XAVFLI tomonga ishlardi — `test_route_coverage.py` modul
docstringi aynan shu sinf nosozlikni tasvirlaydi.

Graf `require_permission()` va `audit_read()` qoldirgan introspektsiya
teglari (`required_permission` / `audit_resource`) orqali o'qiladi. Teglar
ish paytida HECH KIM tomonidan o'qilmaydi va xulqqa ta'sir qilmaydi —
ularning yagona iste'molchisi shu fayl.

BU FAYLDA "KUTILGAN NOSOZLIK" VA "O'TKAZIB YUBORISH" MARKERLARI YO'Q.
Qamrovdan chiqib qolgan marshrut kutilgan nosozlik emas: u shaxsiy
ma'lumotning izsiz o'qilishi va CI'ni YIQITISHI kerak.
"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Any

import pytest
from app.main import app as fastapi_app
from app.security.rbac import ROLE_PERMISSIONS, Permission
from fastapi.routing import APIRoute
from pydantic import BaseModel

from tenancy.test_cross_tenant import all_routes

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi import FastAPI
    from fastapi.dependencies.models import Dependant

pytestmark = pytest.mark.tenancy

PERSONAL_FIELDS = frozenset({"vendor_name", "phone", "full_name"})
"""Javobda ko'ringanda marshrutni D-09 qamroviga kiritadigan maydon nomlari.

AYNAN SHU UCHTASI, chunki ular KIMLIGINI ANIQLAYDI: `full_name` va
`vendor_name` — jismoniy shaxsning ismi, `phone` — O'zbekistonda amalda
yagona barqaror identifikator (D-01 tufayli tizimning O'ZI ham odamni shu
raqam bilan taniydi). CLAUDE.md data-rezidentlik bandi aynan bu
maydonlarni O'zR shaxsiy ma'lumotlar qonuni ostiga olib kiradi.

RO'YXAT ATAYIN QISQA. Uni "har ehtimolga qarshi" kengaytirish (masalan
`name`, `address`, `note`) darvozani deyarli HAR marshrutga yoyardi va u
holda yagona amaliy yechim istisnolar ro'yxatini shishirish bo'lardi —
ya'ni darvoza o'z-o'zini bekor qilardi (T-02-148 bilan bir xil mulohaza).

Ro'yxat eskirmasligini `test_gate_covers_a_meaningful_number_of_routes`
qulflaydi: maydon nomlari o'zgarsa (masalan `vendor_name` -> `merchant`)
darvoza BO'SH to'plamni tekshirib yashil qolardi.
"""

EXEMPT_ROUTES: dict[str, str] = {
    "/api/v1/me": (
        "o'z profili — subyekt O'ZINING ma'lumotini o'qiydi, uchinchi shaxsning "
        "shaxsiy ma'lumoti oshkor bo'lmaydi. `VENDOR_VIEW` talab qilinsa har "
        "kassir va nazoratchi o'z ismini ko'ra olmay qolardi (ikkalasida ham bu "
        "huquq YO'Q), ya'ni darvoza mahsulotni buzardi."
    ),
    "/api/v1/users": (
        "XODIMLAR reestri (`USER_VIEW`), sotuvchilar emas: bu yerdagi telefon "
        "tizim foydalanuvchisiniki va u D-01 bo'yicha login identifikatori. "
        "`VENDOR_VIEW` ni talab qilish ikkita bog'liq bo'lmagan huquqni "
        "birlashtirardi. Xodim ma'lumotining o'qish auditi ALOHIDA qaror va u "
        "02-19 rejasining qamrovidan tashqarida — 02-19-SUMMARY.md ning "
        "'Threat Flags' bo'limida ochiq qayd etilgan."
    ),
}
"""Shaxsiy maydon qaytaradi, LEKIN D-09 ning rasta/sotuvchi yuzasiga kirmaydi.

Har istisno IKKI TOMONLAMA qulflangan: `test_exempt_routes_still_exist`
o'chirilgan yo'l qolib ketmasligini, `test_every_exemption_is_load_bearing`
esa istisno HAMON kerakligini tekshiradi. Ikkinchisisiz bu ro'yxat
"vaqtincha qo'shib qo'yaman" refleksining yashash joyiga aylanardi —
`test_route_coverage.py::EXEMPT_ROUTES` da o'rnatilgan qoida.
"""

MINIMUM_PERSONAL_ROUTES = 4
"""Darvoza kamida shuncha marshrutni QAMRAB TURISHI shart.

Amaldagi son 5 (`/stalls`, `/stalls/{id}`, `/stalls/{id}/assignments`,
`/vendors`, `/vendors/{id}`). Chegara ATAYIN pastroq: u "darvoza bo'shab
qolmadimi?" savoliga javob beradi, aniq sonni qulflamaydi. Aniq son
yozilganda har yangi endpoint bu faylni tahrirlashni talab qilardi va
darvoza shovqinga aylanib, "shunchaki raqamni oshiring" refleksini
tug'dirardi (`test_route_coverage.py::MINIMUM_MATRIX_ROUTES` bilan bir
xil mulohaza).
"""

MAP_ROUTE = "/api/v1/stalls/map"
"""NAZORAT MARSHRUTI: shaxsiy maydoni YO'Q va shuning uchun talabdan ozod.

Usiz butun fayl "hamma `GET` ga audit kerak" degan darvozadan
ajralmasdi — u holda test yashil bo'lib turib, D-09 ni emas, uning
qarama-qarshisini himoya qilardi.
"""


# ---------------------------------------------------------------------------
# Marshrut grafini o'qish
# ---------------------------------------------------------------------------


def _walk(routes: Any, *, prefix: str) -> Iterator[tuple[str, Any]]:
    """`app.routes` daraxtini yurib `(to'liq yo'l, marshrut)` juftlarini beradi.

    `tenancy.test_cross_tenant._walk` bilan BIR XIL mexanika (FastAPI
    0.140 `include_router()` natijasini `_IncludedRouter` o'ramiga
    joylaydi), lekin bu yerda marshrut OBYEKTI kerak — `response_model` va
    `dependant` faqat undan olinadi, `RouteSpec(method, path)` dan emas.

    Nusxaning jimgina ajralib ketishi `test_walk_matches_the_shared_walker`
    bilan bloklangan: ikkala yurish AYNAN bir xil (metod, yo'l) to'plamini
    berishi shart — shuning uchun bu yerda FILTR YO'Q, u chaqiruvchida.
    """
    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            context = getattr(route, "include_context", None)
            nested = str(getattr(context, "prefix", "") or "")
            yield from _walk(included.routes, prefix=prefix + nested)
            continue
        path = getattr(route, "path", None)
        if path is None:
            continue
        yield prefix + str(path), route


def _methods(route: Any) -> set[str]:
    """Marshrutning HAQIQIY metodlari (`HEAD`/`OPTIONS` — Starlette avtomati)."""
    return set(getattr(route, "methods", None) or {"GET"}) - {"HEAD", "OPTIONS"}


def get_routes(app: FastAPI) -> dict[str, APIRoute]:
    """Yo'l -> `GET` marshruti.

    `APIRoute` FILTRI MAJBURIY: `app.routes` da Starlette avtomatik
    qo'shadigan hujjat marshrutlari ham bor (`/api/docs`, `/redoc`,
    `/api/openapi.json`, `/docs/oauth2-redirect`). Ular oddiy
    `starlette.routing.Route` va ularda na `response_model`, na
    `dependant` bor — filtrsiz bu funksiya `AttributeError` bilan
    yiqilardi. Ular yo'qolib qolmasligi `test_walk_matches_the_shared_
    route_walker` da tekshiriladi (u FILTRSIZ yurishni solishtiradi).
    """
    return {
        path: route
        for path, route in _walk(app.routes, prefix="")
        if isinstance(route, APIRoute) and "GET" in _methods(route)
    }


def response_field_names(annotation: Any) -> frozenset[str]:
    """Javob modelining maydon nomlari — ICHMA-ICH yig'iladi.

    REKURSIYA MAJBURIY: shaxsiy maydon deyarli hech qachon yuqori
    darajada turmaydi. `StallListResponse.items: list[StallListItem]`
    da `vendor_name` IKKI qavat pastda, `StallDetail` esa `StallListItem`
    dan meros oladi. Faqat yuqori darajaga qaraydigan tekshiruv uchala
    nishon marshrutni ham "toza" deb ko'rsatardi.

    Sikl `seen` bilan to'silgan: o'ziga havola qiladigan model (masalan
    daraxt shaklidagi javob) rekursiyani cheksiz qilardi.
    """
    names: set[str] = set()
    _collect(annotation, names, set())
    return frozenset(names)


def _collect(annotation: Any, names: set[str], seen: set[type[Any]]) -> None:
    """Annotatsiya ichidagi har bir Pydantic modelining maydon nomlarini yig'adi."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if annotation in seen:
            return
        seen.add(annotation)
        for field_name, field in annotation.model_fields.items():
            names.add(field_name)
            _collect(field.annotation, names, seen)
        return
    # `list[X]`, `X | None`, `dict[str, X]` — argumentlar ichiga kiriladi.
    for argument in typing.get_args(annotation):
        _collect(argument, names, seen)


def dependency_calls(dependant: Dependant) -> list[Any]:
    """Bog'liqlik daraxtidagi BARCHA chaqiriladigan obyektlar (rekursiv).

    Marshrut dekoratoridagi `dependencies=[...]` ham shu daraxtda:
    FastAPI ularni `dependant.dependencies` ning BOSHIGA qo'yadi, ya'ni
    ular imzo parametrlaridan OLDIN hal bo'ladi (T-02-147 kafolatining
    manbai).
    """
    calls: list[Any] = []
    for sub in dependant.dependencies:
        calls.append(sub.call)
        calls.extend(dependency_calls(sub))
    return calls


def audit_resources(route: APIRoute) -> list[str]:
    """Marshrut e'lon qilgan o'qish-audit resurslari (`audit_read` teglari)."""
    tagged = [getattr(call, "audit_resource", None) for call in dependency_calls(route.dependant)]
    return [resource for resource in tagged if resource is not None]


def required_permissions(route: APIRoute) -> list[Permission]:
    """Marshrut talab qiladigan huquqlar (`require_permission` teglari)."""
    tagged = [
        getattr(call, "required_permission", None) for call in dependency_calls(route.dependant)
    ]
    return [perm for perm in tagged if perm is not None]


def personal_data_routes(app: FastAPI) -> dict[str, APIRoute]:
    """Javobida shaxsiy maydon BOR va istisno QILINMAGAN `GET` marshrutlari."""
    return {
        path: route
        for path, route in get_routes(app).items()
        if path not in EXEMPT_ROUTES
        and response_field_names(route.response_model) & PERSONAL_FIELDS
    }


PERSONAL_ROUTES = personal_data_routes(fastapi_app)
"""Darvoza qamrayotgan marshrutlar — import paytida bir marta hisoblanadi."""


def _personal_fields_of(path: str) -> frozenset[str]:
    """Marshrut javobidagi shaxsiy maydonlar — NOSOZLIK XABARI uchun.

    Xato xabari "qaysi marshrut" dan tashqari "qaysi maydon tufayli"
    savoliga ham javob berishi kerak: tuzatayotgan odam javob modelini
    qidirib topishga majbur bo'lmasin.
    """
    return response_field_names(PERSONAL_ROUTES[path].response_model) & PERSONAL_FIELDS


# ---------------------------------------------------------------------------
# Darvozaning O'ZI ishlayotganini tekshiruvchi testlar
# ---------------------------------------------------------------------------


def test_walk_matches_the_shared_route_walker() -> None:
    """Bu fayldagi yurish `test_cross_tenant.all_routes()` bilan BIR XIL natija beradi.

    NEGA KERAK: yurish FastAPI ning ICHKI tuzilmasiga tayanadi
    (`original_router`, `include_context.prefix`). U o'zgarganda yurish
    istisno KO'TARMAYDI — u shunchaki kamroq marshrut topadi, darvoza
    bo'shaydi va butun fayl jimgina yashil bo'lib qoladi.

    Ikkinchi yurish esa `test_route_coverage.py::
    test_route_walker_matches_openapi` orqali FastAPI ning OMMAVIY
    kontrakti (`app.openapi()`) bilan allaqachon solishtirilgan, ya'ni bu
    tekshiruv nusxani ishonchli zanjirga bog'laydi.
    """
    mine = {
        (method, path)
        for path, route in _walk(fastapi_app.routes, prefix="")
        for method in _methods(route)
    }
    shared = {(route.method, route.path) for route in all_routes(fastapi_app)}

    assert mine == shared, (
        "ikki yurish ajralib ketdi (FastAPI ichki tuzilmasi o'zgargan bo'lishi "
        f"mumkin): faqat bu yerda {sorted(mine - shared)}, faqat u yerda "
        f"{sorted(shared - mine)}"
    )


def test_gate_covers_a_meaningful_number_of_routes() -> None:
    """Darvoza BO'SH to'plamni tekshirmayapti — YOLG'ON-YASHIL ning eng jimgina shakli.

    `PERSONAL_FIELDS` dagi nom javob modelida qayta nomlansa (masalan
    `vendor_name` -> `merchant`), qolgan testlar hech nima topmay
    "hammasi joyida" deb tugardi.
    """
    assert len(PERSONAL_ROUTES) >= MINIMUM_PERSONAL_ROUTES, (
        f"darvoza atigi {len(PERSONAL_ROUTES)} marshrut topdi "
        f"({sorted(PERSONAL_ROUTES)}) — `PERSONAL_FIELDS` eskirgan yoki "
        "marshrut yurishi buzilgan"
    )


def test_map_route_is_free_of_the_requirement() -> None:
    """NAZORAT: shaxsiy maydoni yo'q marshrut talabdan OZOD (T-02-148).

    Bu test yuqoridagilarni "hamma `GET` ga audit kerak" degan darvozadan
    ajratadi. `GET /stalls/map` javobida `has_vendor` boolean'idan boshqa
    hech nima yo'q va unga audit qo'yish jurnalni har xarita ochilishida
    shovqin bilan to'ldirardi.
    """
    routes = get_routes(fastapi_app)

    assert MAP_ROUTE in routes, f"{MAP_ROUTE} umuman topilmadi — nazorat holati ma'nosini yo'qotdi"
    assert MAP_ROUTE not in PERSONAL_ROUTES, (
        f"{MAP_ROUTE} shaxsiy maydonli deb tasniflandi — `PERSONAL_FIELDS` "
        "haddan tashqari keng yoki javob modeliga shaxsiy maydon qo'shilgan"
    )
    assert not audit_resources(routes[MAP_ROUTE]), (
        f"{MAP_ROUTE} o'qish auditini e'lon qilibdi — jurnal shovqin bilan to'ladi"
    )


# ---------------------------------------------------------------------------
# ASOSIY DA'VO — D-09 ning ikki talabi, ALOHIDA o'lchanadi
# ---------------------------------------------------------------------------


def test_personal_data_routes_declare_read_audit() -> None:
    """Shaxsiy maydon qaytaradigan har `GET` o'qish auditini e'lon qiladi (D-09).

    `SELECT` uchun PostgreSQL'da trigger YO'Q, ya'ni bu izni faqat ilova
    qatlami qoldira oladi. E'lon qilinmasa hodisa umuman sodir
    bo'lmagandek ko'rinadi — CLAUDE.md ning "audit jurnali majburiy"
    cheklovi jimgina buziladi.
    """
    missing = sorted(path for path, route in PERSONAL_ROUTES.items() if not audit_resources(route))

    assert not missing, (
        "Quyidagi `GET` marshrutlari shaxsiy maydon qaytaradi, lekin o'qish "
        "auditini e'lon qilmaydi (D-09). Har biriga "
        "`Depends(audit_read(<resurs>, reason=...))` qo'shing:\n  "
        + "\n  ".join(f"{path} -> {sorted(_personal_fields_of(path))}" for path in missing)
    )


def test_personal_data_routes_require_vendor_view() -> None:
    """Shaxsiy maydon qaytaradigan har `GET` `VENDOR_VIEW` talab qiladi.

    AUDIT TALABIDAN ALOHIDA TEST, garchi ikkalasi ham bir xil marshrutlar
    ro'yxatini tekshirsa ham: ular IKKI MUSTAQIL da'vo. Audit "hodisa iz
    qoldirdimi?" deydi, huquq esa "hodisa umuman sodir bo'lishi kerakmidi?"
    deydi. Bittasini buzish ikkinchisini qizartirmasligi sabotaj bilan
    o'lchanadi.

    Talab bugungi kirish darajasini TORAYTIRMAYDI (pastdagi test buni
    matritsa ustida isbotlaydi) — u KELAJAKDAGI "faqat ko'rsin" rolini
    himoya qiladi: bunday rol shaxsiy ma'lumotni JIMGINA meros qilib
    olmaydi (CR-02 ning oxirgi xatboshi).
    """
    missing = sorted(
        path
        for path, route in PERSONAL_ROUTES.items()
        if Permission.VENDOR_VIEW not in required_permissions(route)
    )

    assert not missing, (
        "Quyidagi `GET` marshrutlari shaxsiy maydon qaytaradi, lekin "
        "`VENDOR_VIEW` talab qilmaydi. Dekoratorga "
        "`dependencies=[Depends(require_permission(Permission.VENDOR_VIEW))]` "
        "qo'shing (imzoga EMAS — 403 audit yozuvidan oldin bo'lishi kerak):\n  "
        + "\n  ".join(missing)
    )


def test_market_data_view_holders_already_have_vendor_view() -> None:
    """Yuqoridagi talab birorta AMALDAGI rolning kirishini toraytirmagan.

    Bu rejaning butun xavfsizligi shu invariantga tayanadi: agar biror
    rolda `MARKET_DATA_VIEW` bo'lib `VENDOR_VIEW` bo'lmasa, `VENDOR_VIEW`
    talabi o'sha rol uchun rasta reestrini BUTUNLAY yopib qo'yardi va bu
    xatolik faqat foydalanuvchi 403 ko'rganda ma'lum bo'lardi.

    Test matritsani O'ZGARTIRMAYDI — u faqat "o'zgartirish xavfsiz edi"
    da'vosini qulflaydi. Kelajakda kimdir yangi "faqat ko'rsin" rolini
    `MARKET_DATA_VIEW` bilan qo'shsa, bu test uni AYNAN shu joyda
    to'xtatadi va qaror ongli bo'ladi: yo `VENDOR_VIEW` ham beriladi, yo
    o'sha rol shaxsiy ma'lumotni ko'rmasligi ATAYIN tanlanadi (o'shanda
    bu test yangilanadi va sabab yoziladi).
    """
    offenders = sorted(
        str(role)
        for role, perms in ROLE_PERMISSIONS.items()
        if Permission.MARKET_DATA_VIEW in perms and Permission.VENDOR_VIEW not in perms
    )

    assert not offenders, (
        "Quyidagi rollarda `MARKET_DATA_VIEW` bor, lekin `VENDOR_VIEW` yo'q — "
        "ular uchun `GET /stalls` endi 403 beradi. Qarorni ONGLI qiling: yo "
        f"matritsaga `VENDOR_VIEW` qo'shing, yo bu testni sabab bilan "
        f"yangilang: {offenders}"
    )


# ---------------------------------------------------------------------------
# Istisnolar — IKKI TOMONLAMA qulflangan
# ---------------------------------------------------------------------------


def test_exempt_routes_still_exist_and_have_reasons() -> None:
    """Eskirgan istisno qolib ketmagan va har birining sababi bor.

    O'chirilgan yo'lning istisnosi o'zi zararsiz, lekin u ro'yxatni
    ishonchsiz qiladi: keyingi o'qiyotgan odam nechta istisno HAQIQIY
    ekanini bilmaydi. Eng yomoni — o'sha yo'l keyinchalik BOSHQA ma'noda
    qayta paydo bo'lsa, u tug'ilishidanoq istisno bo'lib turadi.
    """
    live = set(get_routes(fastapi_app))
    stale = sorted(path for path in EXEMPT_ROUTES if path not in live)

    assert not stale, f"`EXEMPT_ROUTES` da mavjud bo'lmagan `GET` marshrutlari qolgan: {stale}"
    for path, reason in EXEMPT_ROUTES.items():
        assert reason.strip(), f"{path}: istisno sababi bo'sh"


def test_every_exemption_is_load_bearing() -> None:
    """Har istisno HAMON kerak — ortiqchasi darvozani jimgina bo'shatardi.

    Marshrut shaxsiy maydonni qaytarishni to'xtatgan bo'lsa, uning
    istisnosi endi hech nimani ushlab turmaydi, lekin ro'yxatda "shaxsiy
    ma'lumot beradigan, lekin qamrovdan tashqaridagi yo'l" bo'lib
    ko'rinadi. Bunday yozuv keyingi tahrirlovchini chalg'itadi va
    "vaqtincha qo'shib qo'yaman" refleksini oqlaydi.
    """
    routes = get_routes(fastapi_app)
    useless = sorted(
        path
        for path in EXEMPT_ROUTES
        if path in routes
        and not (response_field_names(routes[path].response_model) & PERSONAL_FIELDS)
    )

    assert not useless, (
        "Quyidagi marshrutlar endi shaxsiy maydon qaytarmaydi — istisnoni "
        f"`EXEMPT_ROUTES` dan OLIB TASHLANG: {useless}"
    )
