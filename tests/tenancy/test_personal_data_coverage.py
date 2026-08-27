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
from app.security.audit import TABLE_VENDORS
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

BINARY_PERSONAL_ROUTES: dict[str, str] = {
    "/api/v1/snapshots/{snapshot_id}/image": (
        "dalil-kadr BAYTLARI — bozor tashrifchilarining tasviri, ya'ni O'zR "
        "shaxsiy ma'lumotlar qonuni ostidagi ma'lumot. Javob modeli YO'Q, "
        "shuning uchun `PERSONAL_FIELDS` uni HECH QACHON topa olmaydi."
    ),
    "/api/v1/reports/debtors.xlsx": (
        "qarzdorlik reestrining `.xlsx` HUJJATI — unda sotuvchi F.I.Sh. BOR "
        "(D-07: ism bu yuzada QONUNIY, chunki hujjat «kimdan undirish "
        "kerak?» savoliga javob beradi). Javob MODELI YO'Q — javob BAYT — "
        "shuning uchun `PERSONAL_FIELDS` uni HECH QACHON topa olmaydi, "
        "garchi AYNI ma'lumot JSON juftida (`/reports/debtors`) o'sha "
        "darvoza tomonidan topilsa ham. Bu ro'yxatsiz eksport auditsiz va "
        "`VENDOR_VIEW` siz qolardi va bu JSON dan ham xavfliroq: fayl "
        "tizimdan CHIQIB ketadi."
    ),
    "/api/v1/reports/compare.xlsx": (
        "uch tomonlama solishtiruvning IMZOLANADIGAN hujjati — unda RASTA "
        "va SOTUVCHI yonma-yon turadi (D-19, §12.6), ya'ni javob rasta <-> "
        "shaxs bog'lanishini ochadi. ⛔ JSON jufti (`/reports/compare`) esa "
        "bu ro'yxatga KIRMAYDI va bu ONGLI: uning javob modelida "
        "(`schemas.ThreeWayReportRow`) ism UMUMAN yo'q — klient kontrakti "
        "(`threeWayRowSchema`, `strictObject`) uni qabul qilmaydi. Ikki yuza, "
        "ikki qaror: ekrandagi jadval rasta kesimida ishlaydi, imzolangan "
        "varaq esa «kimdan so'raladi?» savoliga QOG'OZDA javob beradi. Fayl "
        "tizimdan CHIQIB ketadi va u boshqa odamning stolida yashashda "
        "davom etadi — shuning uchun `audit_read` majburiy."
    ),
}
"""Javobi MODEL EMAS, BAYT bo'lgan va o'sha baytlarning O'ZI shaxsiy ma'lumot.

=============================================================================
⛔ NEGA BU RO'YXAT KERAK — VA U 04-09 NING OCHIQ TOPILMASI EDI.

Yuqoridagi darvoza shaxsiy ma'lumotni `response_model` ning MAYDON NOMI
bo'yicha topadi (`vendor_name`, `phone`, `full_name`). Kadr rasmida esa
maydon YO'Q — shaxsiy ma'lumot BAYTLARNING O'ZI. `04-09` buni darvozaning
o'z funksiyalarini chaqirib O'LCHADI va xulq bilan tasdiqladi: `audit_read`
butunlay olib tashlanganda ham bu fayl YASHIL qolgan.

Ya'ni rasm marshrutining kafolati uchta NOMLANGAN testda yashardi
(`test_snapshot_api.py`) va DARVOZA ostida emas — testlar o'chirilsa yoki
qayta yozilsa kafolat jimgina yo'qolardi.

⚠ RO'YXAT O'ZI DRIFT MANBAI BO'LMASIN degan shart quyidagi YOPIQLIK
  testida: har bir `response_model` siz `GET` marshruti IKKALA ro'yxatdan
  BIRIDA bo'lishi SHART. Ya'ni yangi bayt-marshrut qo'shgan odam tanlov
  qilishga MAJBUR — «unutish» yo'li yopiq.
=============================================================================
"""

NON_PERSONAL_BINARY_ROUTES: dict[str, str] = {
    "/api/v1/imports/template": (
        "BO'SH shablon — sarlavha qatori va namunaviy qator. Bozorning "
        "birorta qatori bu faylga tushmaydi, ya'ni shaxsiy ma'lumot YO'Q."
    ),
    "/internal/live-authz": (
        "nginx `auth_request` sub-so'rovi. Javob TANASIZ (204/403) va u "
        "brauzerga umuman yetib bormaydi."
    ),
    "/internal/self-check": (
        "yurak urishlari holati (`{ok, stale[]}`). Tenant ma'lumoti YO'Q va "
        "bu ALOHIDA test bilan qulflangan (`test_capture_schedule.py::"
        "test_self_check_needs_no_authentication_and_leaks_no_tenant_data`)."
    ),
    "/readyz": "DB/Valkey ping natijasi — sog'liq signali, ma'lumot emas.",
    "/api/v1/reports/revenue.xlsx": (
        "kun x summa — odamni aniqlaydigan maydon YO'Q (JSON juftida ham "
        "yo'q va `test_route_coverage.py` buni AYNAN o'lchaydi)."
    ),
    "/api/v1/reports/anomalies.xlsx": (
        "rasta KODI, sana, sinf nomi, case holati va kadr IDENTIFIKATORI — "
        "kadrning O'ZI ham, imzolangan havola ham faylga tushmaydi (07 D-03)."
    ),
    "/api/v1/reports/accuracy.xlsx": (
        "chalkashlik matritsasi va uch Wilson oralig'i — AGREGAT sonlar. "
        "Nazoratchining KIMLIGI hisobotga umuman kirmaydi (D-16: ichki "
        "moslik o'lchovi na son, na maydon sifatida mavjud)."
    ),
}
"""Javobi model EMAS, lekin shaxsiy ma'lumot ham EMAS — sabab bilan.

Har yozuv `BINARY_PERSONAL_ROUTES` ning teskarisi: u «audit kerak emas»
degan da'vo va u ham NOMLANADI. Ikkala ro'yxat birgalikda YOPIQ to'plam
hosil qiladi (pastdagi test).
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
    """Marshrut MAJBURIY talab qiladigan huquqlar (`require_permission` teglari).

    ⚠ «YO P, YO Q» DARVOZASI BU RO'YXATGA TUSHMAYDI va bu ATAYIN — pastdagi
      `required_any_permissions()` ga qarang. Ikkalasini bitta ro'yxatga
      qo'shish bu funksiyani YOLG'ON gapirtirardi: chaqiruvchilar undan
      «bu huquqsiz o'tib bo'lmaydi» degan ma'noni o'qiydi
      (`test_every_camera_get_route_requires_camera_view` shu ma'noga
      tayanadi), «yo P yo Q» da esa P siz ham o'tish MUMKIN.
    """
    tagged = [
        getattr(call, "required_permission", None) for call in dependency_calls(route.dependant)
    ]
    return [perm for perm in tagged if perm is not None]


def required_any_permissions(route: APIRoute) -> list[frozenset[Permission]]:
    """«Kamida bittasi» darvozalari (`require_any_permission` teglari).

    Har element BITTA darvozaning ruxsat etilgan to'plami. Ro'yxat
    bo'lishining sababi — bitta marshrutda bir nechta bunday darvoza
    bo'lishi mumkin (masalan dekoratorda va imzoda), va ular BIRGALIKDA
    `AND` bilan ishlaydi.
    """
    tagged = [
        getattr(call, "required_any_permissions", None)
        for call in dependency_calls(route.dependant)
    ]
    return [perms for perms in tagged if perms is not None]


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
# BAYT JAVOBLI MARSHRUTLAR — `response_model` YO'Q, ya'ni maydon nomi ham yo'q
# ---------------------------------------------------------------------------


def binary_routes(app: FastAPI) -> dict[str, APIRoute]:
    """`response_model` E'LON QILMAGAN `GET` marshrutlari.

    Aynan shu to'plam yuqoridagi maydon-nomi darvozasining KO'R NUQTASI:
    modeli yo'q javobda tekshiriladigan maydon ham yo'q.
    """
    return {path: route for path, route in get_routes(app).items() if route.response_model is None}


def test_every_binary_response_route_is_classified() -> None:
    """Model'siz har `GET` marshruti IKKI ro'yxatdan BIRIDA — YOPIQLIK sharti.

    =========================================================================
    ⛔ BU TESTSIZ `BINARY_PERSONAL_ROUTES` QO'LDA YOZILGAN RO'YXAT BO'LARDI
       va u BIRINCHI unutilgan marshrutda jimgina eskirardi — ya'ni
       darvoza 04-09 topgan bo'shliqni FAQAT BUGUNGI bitta marshrut uchun
       yopardi.

    Yopiqlik sharti tanlovni MAJBURIY qiladi: bayt qaytaradigan yangi
    `GET` qo'shgan odam yo uni shaxsiy deb belgilaydi (va audit + huquq
    talabini oladi), yo sababini yozib ozod qiladi. Uchinchi yo'l —
    «hech nima qilmaslik» — CI'ni qizartiradi.

    Ro'yxatlarning ESKIRISHI ham shu yerda tutiladi: o'chirilgan marshrut
    ro'yxatda qolib ketolmaydi.
    =========================================================================
    """
    found = set(binary_routes(fastapi_app))
    classified = set(BINARY_PERSONAL_ROUTES) | set(NON_PERSONAL_BINARY_ROUTES)

    assert found, (
        "birorta model'siz `GET` marshruti topilmadi — marshrut yurishi yoki "
        "`response_model` o'qilishi buzilgan bo'lsa bu darvoza BO'SH to'plam "
        "ustida jimgina yashil bo'lardi"
    )

    unclassified = sorted(found - classified)
    assert not unclassified, (
        "Quyidagi `GET` marshrutlari BAYT qaytaradi va tasniflanmagan:\n  "
        + "\n  ".join(unclassified)
        + "\n\nJavobning O'ZI shaxsiy ma'lumotmi? Ha -> `BINARY_PERSONAL_ROUTES` "
        "(va marshrutga `audit_read` + `CAMERA_VIEW`). Yo'q -> "
        "`NON_PERSONAL_BINARY_ROUTES` ga SABAB bilan."
    )

    stale = sorted(classified - found)
    assert not stale, (
        f"tasnif ro'yxatlarida MAVJUD BO'LMAGAN marshrutlar qoldi: {stale} — "
        "ro'yxat eskirgan va u endi hech nimani qo'riqlamaydi"
    )

    overlap = sorted(set(BINARY_PERSONAL_ROUTES) & set(NON_PERSONAL_BINARY_ROUTES))
    assert not overlap, f"marshrut IKKALA ro'yxatda ham: {overlap}"


def test_no_non_personal_claim_survives_a_vendor_data_guard() -> None:
    """⛔⛔ «NOMASHAXSIY» DA'VOSI MARSHRUTNING O'Z E'LONIGA ZID BO'LOLMAYDI.

    =========================================================================
    ⛔ BU TEST 08-12 NING MAJBURIY SABOTAJI TOPGAN BO'SHLIQNI YOPADI VA U
       «qo'shimcha ehtiyot chorasi» EMAS — O'LCHANGAN ZARURIYAT.

    SABOTAJ (reja Task 3, №1): `/api/v1/reports/debtors.xlsx` IKKALA
    reyestrdan ham `NON_PERSONAL_BINARY_ROUTES` ga ko'chirildi va butun
    `tests/tenancy` to'plami yugurtirildi:

        854 passed — BIRORTA TEST QIZARMADI.

    Ya'ni sotuvchi F.I.Sh. chiqadigan hujjatdan `audit_read` talabi
    JIMGINA yo'qoldi va yagona to'siq — o'sha ro'yxatga yozilgan
    izohning ROSTLIGI — ya'ni INSON INTIZOMI edi. Bu esa aynan 05-15
    ning darsi: sabotaj yetib borsa ham hech nima qizarmasa, tuzatish
    testda emas, HOLATDA.

    ⛔ SHUNING UCHUN TASNIF ENDI MEXANIK LANGARGA EGA: `VENDOR_VIEW`
       huquqi va `vendors` o'qish auditi MAHSULOT KODIDA e'lon qilinadi
       (`api/v1/reports.py`), ya'ni ular bu fayldagi ro'yxatdan MUSTAQIL
       dalil. Marshrut «menda shaxsiy ma'lumot yo'q» deb turib, o'sha
       ma'lumotni qo'riqlaydigan darvozani ko'tarib turolmaydi.

    ⚠ TESKARI YO'NALISH BU YERDA O'LCHANMAYDI («`VENDOR_VIEW` bor bo'lsa
      shaxsiy») — u yuqoridagi `BINARY_PERSONAL_ROUTES` darvozasining
      ishi. Bu yerdagi da'vo TOR va shuning uchun kuchli: nomashaxsiy
      DEB ATALGAN marshrut shaxsiy ma'lumot darvozalarini ko'tarmaydi.
    =========================================================================
    """
    routes = binary_routes(fastapi_app)

    for path in sorted(NON_PERSONAL_BINARY_ROUTES):
        # ⛔ `.get()` EMAS: yopiqlik testi (yuqorida) ro'yxatdagi HAR yo'l
        #    tirik ekanini ALLAQACHON kafolatlaydi, ya'ni `KeyError` shu
        #    kafolatning buzilgani haqidagi BALAND OVOZLI signal bo'ladi.
        route = routes[path]

        assert Permission.VENDOR_VIEW not in required_permissions(route), (
            f"{path} «shaxsiy ma'lumot YO'Q» deb tasniflangan, lekin `VENDOR_VIEW` "
            "darvozasini ko'taradi — bu huquq AYNAN sotuvchining shaxsiy ma'lumotini "
            "qo'riqlash uchun mavjud. Tasnif YOLG'ON: yo'lni "
            "`BINARY_PERSONAL_ROUTES` ga ko'chiring (va `BINARY_PERSONAL_ALLOWED` "
            "ga uning huquqlarini yozing)"
        )
        assert TABLE_VENDORS not in audit_resources(route), (
            f"{path} «shaxsiy ma'lumot YO'Q» deb tasniflangan, lekin `{TABLE_VENDORS}` "
            "ustidan o'qish auditini e'lon qiladi — audit AYNAN shaxsiy ma'lumot "
            "o'qilgani uchun yoziladi (D-09). Ikki e'lon bir-biriga ZID"
        )


EVIDENCE_FRAME_ALLOWED = frozenset({Permission.CAMERA_VIEW, Permission.OCCUPANCY_REVIEW})
"""DALIL-KADRNI KO'RISHI MUMKIN BO'LGAN HUQUQLARNING YOPIQ TO'PLAMI (05-15).

⚠ RO'YXAT SHU YERDA IKKINCHI MARTA YOZILADI va bu ATAYIN — `snapshots.py`
  dagi `EVIDENCE_FRAME_PERMISSIONS` dan IMPORT QILINMAYDI. Import qilingan
  darvoza o'z tekshirayotgan qiymatini tekshirayotgan bo'lardi: kimdir
  mahsulot konstantasiga `PAYMENT_CREATE` qo'shsa, darvoza JIMGINA
  kengayib, yashil qolardi. Ikki nusxa ajralganda test QIZARADI va bu
  aynan kerakli xulq — qaror bu yerda ham ONGLI ravishda takrorlanishi
  kerak (§S-9 ning «fixture mexanizmni takrorlamaydi» qoidasining
  darvoza tomonidagi jufti).
"""

BINARY_PERSONAL_ALLOWED: dict[str, frozenset[Permission]] = {
    "/api/v1/snapshots/{snapshot_id}/image": EVIDENCE_FRAME_ALLOWED,
    "/api/v1/reports/debtors.xlsx": frozenset({Permission.REPORT_VIEW, Permission.VENDOR_VIEW}),
    "/api/v1/reports/compare.xlsx": frozenset({Permission.REPORT_VIEW, Permission.VENDOR_VIEW}),
}
"""HAR bayt-shaxsiy marshrutning O'Z ruxsat etilgan huquqlar to'plami.

=============================================================================
⛔⛔ NEGA PER-ROUTE XARITA, VA NEGA QOLGAN UCH YO'L XATO EDI (08-12).

05-15 gacha bu ro'yxat BITTA marshrutdan iborat edi va darvoza
`granted <= EVIDENCE_FRAME_ALLOWED` deb yozilgandi — ya'ni «bayt-shaxsiy
marshrut» bilan «dalil-kadr marshruti» AYNI narsa deb faraz qilingan.
08-12 ikkinchi bayt-shaxsiy marshrutni (`debtors.xlsx`) qo'shdi va u
`REPORT_VIEW` + `VENDOR_VIEW` talab qiladi, ya'ni eski shart QIZARARDI.

Uch «tuzatish» yo'li bor edi va UCHALASI HAM DARVOZANI BO'SHATARDI:

  1. `EVIDENCE_FRAME_ALLOWED` GA `REPORT_VIEW` QO'SHISH — dalil-kadr
     marshruti hisobot huquqi bilan OCHILARDI. Direktor (`REPORT_VIEW`
     BOR) bozor tashrifchilarining tasvirini ko'ra boshlardi va 05-15
     ning butun ishi bekor bo'lardi. ⛔ Shuning uchun
     `EVIDENCE_FRAME_ALLOWED` ning O'ZI ⛔ TEGILMAGAN va u AYNAN
     `{CAMERA_VIEW, OCCUPANCY_REVIEW}` bo'lib qoladi;

  2. EKSPORTNI `POST` QILISH — `get_routes()` faqat `GET` ni yuradi,
     ya'ni marshrut yopiqlik testidan ham, bu darvozadan ham JIMGINA
     chiqib ketardi. Bu «tuzatish» emas, DARVOZANI CHETLASH bo'lardi;

  3. SHAXSIY EKSPORTNI `NON_PERSONAL_BINARY_ROUTES` GA YOZISH — yolg'on
     tasnif. U `audit_read` talabini butunlay o'chirardi va sotuvchi
     F.I.Sh. IZSIZ fayl bo'lib chiqardi.

To'g'ri javob — savolni ANIQROQ qo'yish: «bu marshrut huquqsiz
qolmasinmi?» emas, «BU marshrut QAYSI huquqlar bilan ochiladi?».

⛔ `SNAPSHOT_EVIDENCE_FRAME_ROUTES` HAM TEGILMAGAN: u «yo P yo Q»
   darvozasini ko'tarishga haqli marshrutlarni sanaydi va u BITTA
   elementli bo'lib qoladi. `debtors.xlsx` ikki huquqni **VA** bilan
   talab qiladi, ya'ni u o'sha ro'yxatga umuman tegishli emas.
=============================================================================

⚠ KALITLAR `BINARY_PERSONAL_ROUTES` NIKI BILAN AYNAN TENG bo'lishi SHART
  va u ALOHIDA assert bilan qulflangan (pastdagi test). Usiz ikki ro'yxat
  ajralib ketardi va yangi marshrut `KeyError` o'rniga JIMGINA
  tekshirilmay o'tardi.
"""

SNAPSHOT_SURFACE_MODULE = "app.api.v1.snapshots"
"""Dalil-kadr yuzasining MANBA MODULI — yopiqlik shu yerdan HOSILA qilinadi.

⚠ MODUL BO'YICHA, PREFIKS BO'YICHA EMAS va bu ATAYIN. `snapshots.py`
  bitta faylda UCH router saqlaydi va ularning yo'l prefikslari
  BOSHQA-BOSHQA (`/capture-runs`, `/snapshots`, `/alerts`). Prefiks
  ro'yxati yana QO'LDA YOZILGAN ro'yxat bo'lardi — ya'ni W-3 ni bir
  qavat pastga ko'chirardi, yopmasdi. Modul nomi esa marshrutning
  QAYERDA TUG'ILGANINI aytadi va u faylga qo'shilgan har qanday yangi
  marshrutni AVTOMATIK qamrab oladi.
"""

SNAPSHOT_EVIDENCE_FRAME_ROUTES = ("/api/v1/snapshots/{snapshot_id}/image",)
"""«Yo P yo Q» darvozasini KO'TARISHGA HAQLI marshrutlar — 05-15 qarori.

Ro'yxat bitta elementdan iborat va u SHUNDAY QOLISHI kerak: 05-15
kengaytmasi AYNAN dalil-kadr baytlari uchun edi. Ikkinchi element
qo'shilishi — ongli qaror va u shu yerda ko'rinadi.
"""

OCCUPANCY_DUAL_ROLE_ROUTES = (
    "/api/v1/occupancy",
    "/api/v1/occupancy/round",
)
"""IKKINCHI, ALOHIDA e'lon — kunlik BANDLIK yuzasi (260827).

=========================================================================
⛔ NEGA `SNAPSHOT_EVIDENCE_FRAME_ROUTES` GA QO'SHILMADI: o'sha ro'yxat
   05-15 ning DALIL-KADR baytlari haqidagi qarorini nom bilan saqlaydi va
   uning yuqoridagi docstringi «ro'yxat bitta elementdan iborat va u
   SHUNDAY QOLISHI kerak» deb turadi. Boshqa domenning marshrutini o'sha
   nom ostiga tiqish ikkala qarorni ham o'qib bo'lmas qilardi.

BU YERDAGI QAROR BOSHQA: 260820 da klient qatlami nazoratchiga bandlik
sahifasini ochdi (menyu + sahifa darvozasi), server esa o'shanda
yangilanmagan — natijada menyu KO'RINARDI, sahifa OCHILARDI va so'rov
**403** olardi. 260827 da server klientga moslashtirildi.

⛔ `/api/v1/occupancy/accuracy` BU RO'YXATDA YO'Q va bo'lmaydi ham:
   T-05-58 ning sababi (nazoratchi o'z ANIQLIGINI ko'rsa raqamni
   yaxshilashga urinardi) aynan aniqlik yuzasiga tegishli. Uch marshrutdan
   ikkitasi ochildi, uchinchisi — YO'Q.
=========================================================================
"""

ANY_PERMISSION_GATE_ROUTES = SNAPSHOT_EVIDENCE_FRAME_ROUTES + OCCUPANCY_DUAL_ROLE_ROUTES
"""«Yo P yo Q» darvozasi ko'tarilishi mumkin bo'lgan TO'LIQ to'plam."""

SNAPSHOT_CAMERA_ONLY_ROUTES = (
    "/api/v1/capture-runs",
    "/api/v1/snapshots/{snapshot_id}",
    "/api/v1/alerts",
)
"""NAZORAT — `SnapshotViewerDep` ning QOLGAN uchta marshruti.

05-15 `GET /snapshots/{id}/image` ni «`CAMERA_VIEW` YOKI `OCCUPANCY_REVIEW`»
ga kengaytirdi. `snapshots.py` bitta faylda UCH router saqlaydi (kun
jurnali, kadr metama'lumoti, alertlar) va ular AVVAL bitta
`SnapshotViewerDep` ni bo'lishardi — 05-13 aynan shuni «to'rtta marshrut»
deb o'lchagan. Bu ro'yxat kengayishning O'SHA BITTA MARSHRUT BILAN
CHEGARALANGANINI ushlab turadi: alias bo'shatilsa yoki «yo P yo Q»
darvozasi qo'shniga ko'chirilsa, nazoratchi kun jurnalini, kadr
metama'lumotini va alert oqimini ham olardi — ya'ni «faqat rasm» qarori
jimgina «butun kuzatuv yuzasi» ga aylanardi.

⚠ RO'YXATNING O'ZI YOPIQ EMAS EDI — 05-VERIFICATION W-3. U eskirishni
  ushlardi (`route is None`), lekin `snapshots.py` ga YANGI marshrut
  qo'shilib unga «yo P yo Q» berilsa, birorta test qizarmasdi: yangi
  yo'l bu uchlikda yo'q, ya'ni sikl unga umuman yetib bormasdi. Yopiqlik
  endi `test_the_snapshot_surface_is_a_closed_set` da va u
  `BINARY_PERSONAL_ROUTES` ning naqshini AYNAN takrorlaydi.
"""


def snapshot_surface_routes(app: FastAPI) -> dict[str, APIRoute]:
    """`snapshots.py` da TUG'ILGAN barcha marshrutlar — metodidan qat'i nazar.

    ⚠ `GET` FILTRI YO'Q va bu ATAYIN. Yuqoridagi `get_routes()` faqat
      `GET` ni beradi, chunki D-09 O'QISH haqida. Bu yerdagi savol esa
      boshqa: «bu faylga qo'shilgan marshrut huquq darvozasi bo'yicha
      TASNIFLANGANMI?» — va `POST` ga berilgan «yo P yo Q» ham xuddi
      shunday kengaytma bo'lardi. Filtr qo'yilsa, darvoza o'z nomidagi
      va'dadan tor bo'lib qolardi.
    """
    return {
        path: route
        for path, route in _walk(app.routes, prefix="")
        if isinstance(route, APIRoute)
        and getattr(route.endpoint, "__module__", "") == SNAPSHOT_SURFACE_MODULE
    }


def test_the_two_binary_personal_registries_have_identical_keys() -> None:
    """⛔ IKKI LUG'ATNING KALITLARI AYNAN TENG — DARVOZANING POYDEVORI.

    =======================================================================
    Pastdagi test `BINARY_PERSONAL_ALLOWED[path]` ni TO'G'RIDAN-TO'G'RI
    indekslaydi (⛔ `.get()` EMAS), ya'ni yetishmayotgan kalit `KeyError`
    bilan BALAND OVOZDA yiqiladi. `.get()` bo'lganda esa u jimgina
    `frozenset()` qaytarardi va `granted <= frozenset()` sharti — ya'ni
    «bu marshrut HECH QANDAY huquq bilan ochilmasin» — tasodifan
    QIZARARDI yoki, agar standart qiymat keng tanlansa, jimgina
    YASHIL qolardi. Ikkala natija ham yolg'on.

    Bu test o'sha `KeyError` dan OLDIN turadi va sababni ANIQ aytadi:
    «yangi bayt-shaxsiy marshrut qo'shdingiz, ruxsat xaritasini
    to'ldiring» — `KeyError: '/api/v1/...'` degan xom xabar o'rniga.
    =======================================================================
    """
    mapped = set(BINARY_PERSONAL_ALLOWED)
    listed = set(BINARY_PERSONAL_ROUTES)

    assert mapped == listed, (
        "`BINARY_PERSONAL_ALLOWED` va `BINARY_PERSONAL_ROUTES` kalitlari ajralib "
        f"ketdi: faqat xaritada {sorted(mapped - listed)}, "
        f"faqat ro'yxatda {sorted(listed - mapped)}"
    )


def test_the_evidence_frame_allowance_stayed_exactly_as_05_15_left_it() -> None:
    """⛔ `EVIDENCE_FRAME_ALLOWED` KENGAYMAGAN — 08-12 ning eng qimmat da'vosi.

    =======================================================================
    08-12 ikkinchi bayt-shaxsiy marshrutni qo'shdi (`debtors.xlsx`,
    `REPORT_VIEW` + `VENDOR_VIEW`) va eng oson «tuzatish» yo'li
    `EVIDENCE_FRAME_ALLOWED` ga `REPORT_VIEW` qo'shish bo'lardi — bir
    qatorlik o'zgarish, butun to'plam darhol yashil.

    ⛔ VA U DALIL-KADR MARSHRUTINI HISOBOT HUQUQI BILAN OCHARDI:
       direktorda `REPORT_VIEW` BOR, ya'ni u bozor tashrifchilarining
       tasvirini ko'ra boshlardi. Bu O'zR shaxsiy ma'lumotlar qonuni
       ostidagi ma'lumot va 05-15 uni ATAYIN ikki huquq bilan
       chegaralagan.

    Bu test o'sha bir qatorlik «tuzatish» ni MEXANIK ravishda to'sadi:
    to'plam TENGLIGI bilan o'lchanadi, «ichida bormi?» bilan emas.
    =======================================================================

    ⚠ `snapshots.py::EVIDENCE_FRAME_PERMISSIONS` dan IMPORT QILINMAYDI
      (ro'yxat docstringi): import qilingan darvoza o'z tekshirayotgan
      qiymatini tekshirgan bo'lardi.
    """
    as_05_15_left_it = frozenset({Permission.CAMERA_VIEW, Permission.OCCUPANCY_REVIEW})

    # ⚠ TENGLIKNING TARTIBI `SIM300` (Yoda condition) TALABI: ruff KATTA
    #   HARFLI nomni konstanta deb biladi va uni O'NG tomonda ko'rishni
    #   kutadi. Da'vo tarafsiz — bu TENGLIK, kirish emas.
    assert as_05_15_left_it == EVIDENCE_FRAME_ALLOWED, sorted(EVIDENCE_FRAME_ALLOWED)
    assert BINARY_PERSONAL_ALLOWED["/api/v1/snapshots/{snapshot_id}/image"] == (
        EVIDENCE_FRAME_ALLOWED
    )
    assert SNAPSHOT_EVIDENCE_FRAME_ROUTES == ("/api/v1/snapshots/{snapshot_id}/image",), (
        "«yo P yo Q» darvozasini ko'tarishga haqli marshrutlar ro'yxati o'zgardi — "
        "08-12 unga TEGMASLIGI kerak edi: `debtors.xlsx` ikki huquqni **VA** bilan "
        "talab qiladi va u bu ro'yxatga umuman tegishli emas"
    )


def test_binary_personal_routes_declare_read_audit_and_permission() -> None:
    """Bayt-shaxsiy marshrut o'qish auditini VA O'Z huquqlarini e'lon qiladi.

    ⚠ IKKI DA'VO BITTA TESTDA va bu yuqoridagi juftlikdan ATAYIN farq
      qiladi: u yerda ikkalasi ALOHIDA o'lchanadi, chunki ro'yxatda beshta
      marshrut bor va «qaysi biri qaysi talabni bajarmadi» savoli amaliy.
      Bu yerda xabar yo'lni O'ZI aytadi, ya'ni ajratish faqat ikkinchi
      nusxa berardi.

    =======================================================================
    ⛔⛔ 08-12: SHART `EVIDENCE_FRAME_ALLOWED` DAN PER-ROUTE XARITAGA
        KO'CHDI — VA BU KENGAYTIRISH, BO'SHATISH EMAS.

    Ilgari HAR bayt-shaxsiy marshrutdan `granted <= EVIDENCE_FRAME_ALLOWED`
    talab qilinardi. O'sha shart 05-15 da AYNAN BITTA marshrut (dalil-kadr)
    uchun yozilgan edi va u «bayt-shaxsiy» ni «dalil-kadr» bilan
    tenglashtirardi. Qarzdorlik eksporti esa `REPORT_VIEW` + `VENDOR_VIEW`
    talab qiladi — ya'ni eski shart uni RAD ETARDI.

    ⛔ TUZATISH `EVIDENCE_FRAME_ALLOWED` NI KENGAYTIRISH EMAS (u dalil-kadr
       marshrutini hisobot huquqiga ochardi — yuqoridagi test buni mexanik
       to'sadi), balki SAVOLNI ANIQROQ QO'YISH: har marshrutning O'Z
       ruxsat to'plami bor va u `BINARY_PERSONAL_ALLOWED` da NOMLANGAN.

    ⛔ `.get()` ISHLATILMAYDI: yetishmayotgan kalit `KeyError` bilan
       BALAND OVOZDA yiqilishi kerak. Sabab yuqoridagi kalit-tengligi
       testida to'liq yozilgan.
    =======================================================================

    `CAMERA_VIEW`/`OCCUPANCY_REVIEW` — dalil-kadr uchun `VENDOR_VIEW` EMAS:
    kadr sotuvchining reyestr yozuvi emas, kamera tasviri. `VENDOR_VIEW` ni
    talab qilish ikkita bog'liq bo'lmagan huquqni birlashtirardi
    (`EXEMPT_ROUTES` dagi `/users` mulohazasi bilan bir xil).
    """
    routes = binary_routes(fastapi_app)

    for path in sorted(BINARY_PERSONAL_ROUTES):
        route = routes[path]
        allowed = BINARY_PERSONAL_ALLOWED[path]

        assert audit_resources(route), (
            f"{path} shaxsiy BAYT qaytaradi, lekin o'qish auditini e'lon "
            "qilmaydi — `Depends(audit_read(<resurs>, reason=...))` qo'shing"
        )

        strict = set(required_permissions(route))
        any_gates = required_any_permissions(route)
        granted = strict.union(*any_gates) if any_gates else strict

        assert granted, (
            f"{path} birorta huquq darvozasini e'lon qilmaydi — shaxsiy baytlar huquqsiz o'qilardi"
        )
        assert granted <= allowed, (
            f"{path} shaxsiy baytlarni {sorted(granted - allowed)} huquqiga ham ochib "
            "qo'ydi. Ruxsat etilgan to'plam — `BINARY_PERSONAL_ALLOWED[path]` va u HAR "
            "MARSHRUT UCHUN ALOHIDA: dalil-kadr hisobot huquqi bilan, qarzdorlik "
            "hujjati esa kamera huquqi bilan OCHILMAYDI"
        )


def test_the_evidence_frame_widening_stops_at_the_image_route() -> None:
    """NAZORAT — 05-15 kengaytmasi QO'SHNI marshrutlarga o'tmagan.

    =======================================================================
    ⛔ BU TEST YUQORIDAGINING TAKRORI EMAS — U TESKARI TOMONNI O'LCHAYDI.

    Yuqoridagi darvoza «dalil-kadr HUQUQSIZ qolmasin» deydi va u
    kengaytmadan KEYIN ham yashil bo'lardi, agar kengaytma butun
    `snapshots.py` ga yoyilsa. Aynan shu — 05-13 o'lchagan (b) varianti:
    `SnapshotViewerDep` TO'RTTA marshrutda ishlatiladi va uni bo'shatish
    eng oson «tuzatish» yo'li edi.

    Bu yerdagi savol boshqa: «kengaytma QAYERDA TO'XTADI?» Uchala qo'shni
    marshrut hamon AYNAN `CAMERA_VIEW` MAJBURIY ostida bo'lishi kerak,
    ya'ni ularda «yo P yo Q» darvozasi BO'LMASLIGI kerak.
    =======================================================================
    """
    routes = {path: route for path, route in get_routes(fastapi_app).items()}

    for path in SNAPSHOT_CAMERA_ONLY_ROUTES:
        route = routes.get(path)
        assert route is not None, (
            f"{path} umuman topilmadi — nazorat ro'yxati eskirgan va bu test endi "
            "hech nimani ushlab turmaydi"
        )
        assert Permission.CAMERA_VIEW in required_permissions(route), (
            f"{path} `CAMERA_VIEW` ni MAJBURIY talab qilmay qo'ydi — dalil-kadr "
            "kengaytmasi qo'shni marshrutga oqib o'tgan"
        )
        assert not required_any_permissions(route), (
            f"{path} da «kamida bittasi» darvozasi paydo bo'ldi: "
            f"{required_any_permissions(route)} — 05-15 qarori AYNAN BITTA "
            "marshrut uchun edi"
        )


def test_the_snapshot_surface_is_a_closed_set() -> None:
    """`snapshots.py` ning HAR marshruti IKKI ro'yxatdan BIRIDA — YOPIQLIK.

    =======================================================================
    ⛔ 05-VERIFICATION W-3 — YUQORIDAGI TEST ESKIRISHNI USHLARDI, KENGAYISHNI
       EMAS.

    `test_the_evidence_frame_widening_stops_at_the_image_route`
    `SNAPSHOT_CAMERA_ONLY_ROUTES` BO'YICHA aylanadi, ya'ni u faqat NOM
    BILAN yozilgan uchta marshrutga qaraydi. `snapshots.py` ga to'rtinchi
    qo'shni qo'shib unga `require_any_permission(...)` berilsa, yangi yo'l
    bu uchlikda YO'Q — sikl unga umuman yetib bormaydi va butun fayl
    yashil qoladi. «Kengaytma aynan bitta marshrutda» degan kafolat esa
    o'sha payt allaqachon buzilgan bo'lardi.

    Yopiqlik `BINARY_PERSONAL_ROUTES` naqshi bo'yicha: to'plam MARSHRUT
    GRAFIDAN hosila qilinadi (`__module__`), tasnif esa qo'lda — va
    ikkalasining AYIRMASI ikkala yo'nalishda ham tekshiriladi. Yangi
    marshrut qo'shgan odam tanlov qilishga MAJBUR; «hech nima qilmaslik»
    CI'ni qizartiradi.
    =======================================================================
    """
    found = set(snapshot_surface_routes(fastapi_app))
    classified = set(SNAPSHOT_CAMERA_ONLY_ROUTES) | set(SNAPSHOT_EVIDENCE_FRAME_ROUTES)

    assert found, (
        f"`{SNAPSHOT_SURFACE_MODULE}` dan birorta marshrut topilmadi — modul "
        "ko'chirilgan yoki qayta nomlangan bo'lsa, bu darvoza BO'SH to'plam "
        "ustida jimgina yashil bo'lardi (`SNAPSHOT_SURFACE_MODULE` ni yangilang)"
    )

    unclassified = sorted(found - classified)
    assert not unclassified, (
        "`snapshots.py` ga tasniflanmagan marshrut(lar) qo'shildi:\n  "
        + "\n  ".join(unclassified)
        + "\n\nHuquq darvozasi qanday? Qat'iy `CAMERA_VIEW` -> "
        "`SNAPSHOT_CAMERA_ONLY_ROUTES`. «Yo P yo Q» -> "
        "`SNAPSHOT_EVIDENCE_FRAME_ROUTES` — ⛔ LEKIN 05-15 qarori AYNAN BITTA "
        "marshrut (dalil-kadr baytlari) uchun edi, ya'ni ikkinchi element "
        "qo'shish ONGLI qaror va u nazoratchiga kuzatuv yuzasini kengaytiradi."
    )

    stale = sorted(classified - found)
    assert not stale, (
        f"tasnif ro'yxatlarida MAVJUD BO'LMAGAN marshrutlar qoldi: {stale} — "
        "ro'yxat eskirgan va u endi hech nimani qo'riqlamaydi"
    )

    overlap = sorted(set(SNAPSHOT_CAMERA_ONLY_ROUTES) & set(SNAPSHOT_EVIDENCE_FRAME_ROUTES))
    assert not overlap, f"marshrut IKKALA ro'yxatda ham: {overlap}"


# ---------------------------------------------------------------------------
# G7-6 — 07-10 NING BESH MARSHRUTI DARVOZAGA TUSHMAYDI (D-05, RECON-01/02)
# ---------------------------------------------------------------------------

RECONCILIATION_PREFIX = "/api/v1/reconciliation"
"""Nomuvofiqlik yuzasining prefiksi — to'plam MARSHRUT GRAFIDAN hosila.

⚠ PREFIKS BO'YICHA, QO'LDA YOZILGAN RO'YXAT BO'YICHA EMAS: oltinchi
  marshrut qo'shilsa u darvozaga O'ZI kiradi. Nomlar reyestri esa
  `test_route_coverage.py::RECONCILIATION_ROUTES` da va u BOSHQA
  savolga javob beradi («yuza qanchaligicha qoldimi?»).
"""

TELEGRAM_IDENTIFIER_FIELDS = frozenset({"chat_id", "telegram_user_id", "telegram_username"})
"""⛔ `PERSONAL_FIELDS` USHLAMAYDIGAN, LEKIN ODAMNI ANIQLAYDIGAN NOMLAR.

=============================================================================
⛔⛔ NEGA ALOHIDA RO'YXAT VA NEGA U `PERSONAL_FIELDS` GA QO'SHILMAYDI.

`PERSONAL_FIELDS` ning butun kuchi TORLIGIDA (o'sha konstantaning
docstringi): uni kengaytirish darvozani deyarli har marshrutga yoyardi
va yagona amaliy yechim istisnolar ro'yxatini shishirish bo'lardi.
Bundan tashqari bu uchtasi BOSHQA talabga ega — ular `audit_read` +
`VENDOR_VIEW` bilan «qonuniylashtirilmaydi», ular javobda ⛔ UMUMAN
BO'LMAYDI (07-UI-SPEC §5.5, D-01: ular odamni TASHQI tizimda aniqlaydi
va chegaradan CHIQIB BO'LGAN).

Frontend tomonda o'sha taqiq **G-36** bilan yopilgan; bu — uning
SERVER yarmi va u shu fazaning yuzasi bilan CHEKLANGAN: eski
marshrutlarni qamrash bu rejaning ishi emas.
=============================================================================
"""


def reconciliation_routes(app: FastAPI) -> dict[str, APIRoute]:
    """`/api/v1/reconciliation` ostidagi BARCHA marshrutlar — metodidan qat'i nazar.

    ⚠ `GET` FILTRI YO'Q va bu ATAYIN (`snapshot_surface_routes()` bilan
      aynan bir xil qaror): `PATCH /cases/{id}` ham JAVOB qaytaradi va
      uning modeli ham shaxsiy maydondan xoli bo'lishi shart. Faqat
      `GET` ga qarash yozuv marshrutining javobini darvozadan chiqarib
      yuborardi.
    """
    return {
        path: route
        for path, route in _walk(app.routes, prefix="")
        if isinstance(route, APIRoute) and path.startswith(RECONCILIATION_PREFIX)
    }


def test_the_reconciliation_gate_sees_the_routes() -> None:
    """DARVOZANING NAZORATI — pastdagi uch test BO'SH to'plamda yashil bo'lmaydi.

    ⛔ Usiz «shaxsiy maydon yo'q» da'vosi router o'chirilgan yoki qayta
       nomlangan holatda TRIVIAL ravishda rost bo'lardi (05-16 ning W-2
       darsi va `test_gate_covers_a_meaningful_number_of_routes` ning
       aynan mulohazasi).

    ⛔ SON ANIQ VA U ATAYIN «>=» EMAS: bu da'vo qamrovni emas,
       YUZANING O'LCHAMINI qulflaydi. Yangi marshrut qo'shgan odam bu
       yerga kelib sonni oshiradi va o'shanda ⛔ pastdagi uch da'voning
       (shaxsiy maydon / Telegram identifikatori / binar tasnif) uning
       marshrutini ham qamrab olganini KO'RADI.

    ⚠ 07-16 BITTASINI QO'SHDI (`GET /delivery`, BOT-04): to'rt YO'L ->
      BESH YO'L. ⚠ «Yo'l», «marshrut» EMAS: `GET` va `PATCH`
      `/cases/{case_id}` da BITTA yo'lni bo'lishadi, ya'ni lug'atning
      kaliti oltita marshrut uchun beshta.
    """
    found = reconciliation_routes(fastapi_app)

    assert len(found) == 5, sorted(found)
    assert f"{RECONCILIATION_PREFIX}/report" in found
    assert f"{RECONCILIATION_PREFIX}/cases/{{case_id}}" in found
    assert f"{RECONCILIATION_PREFIX}/delivery" in found


def test_reconciliation_routes_are_not_personal() -> None:
    """⛔ G7-6: beshala marshrut ham `PERSONAL_ROUTES` GA TUSHMAYDI (D-05).

    =========================================================================
    ⛔⛔ DARVOZA YANGI MARSHRUTLARNI AVTOMATIK QAMRAYDI — BU TEST UNI
        QAYTA YOZMAYDI, UNING NATIJASINI QULFLAYDI.

    `personal_data_routes()` butun marshrut grafi bo'ylab yuradi, ya'ni
    `ReconciliationReportRow` ga `vendor_name` qo'shilsa `PERSONAL_ROUTES`
    o'sardi va `test_personal_data_routes_declare_read_audit` +
    `test_personal_data_routes_require_vendor_view` IKKALASI ham
    qizarardi. Bu test o'sha zanjirni AYNAN shu yuza uchun NOMLAB
    qo'yadi: nosozlik xabari «qaysi marshrut, qaysi maydon» deb
    javob beradi va tuzatayotgan odam sababni shu yerda o'qiydi.

    ⚠ IKKI DA'VO ATAYIN: birinchisi javob MODELIDAN yuradi (maydon
      nomlari), ikkinchisi DARVOZANING NATIJASIDAN. Faqat ikkinchisi
      bo'lsa `EXEMPT_ROUTES` ga qo'shib qo'yish yo'li ochiq qolardi —
      u ham testni yashil qilardi, lekin ismni javobga CHIQARARDI.
    =========================================================================
    """
    offenders = {
        path: sorted(response_field_names(route.response_model) & PERSONAL_FIELDS)
        for path, route in reconciliation_routes(fastapi_app).items()
        if response_field_names(route.response_model) & PERSONAL_FIELDS
    }

    assert not offenders, (
        "Nomuvofiqlik yuzasi shaxsiy maydon qaytaryapti (G7-6 / D-05). Ism "
        "klientda MAVJUD va AUDIT QILINGAN `GET /api/v1/vendors` bilan "
        f"joinlanadi, javobga QO'SHILMAYDI: {offenders}"
    )

    leaked = sorted(path for path in PERSONAL_ROUTES if path.startswith(RECONCILIATION_PREFIX))
    assert leaked == [], leaked


def test_no_reconciliation_route_exposes_a_telegram_identifier() -> None:
    """⛔ 07-UI-SPEC §5.5 — C-10 DARVOZASI USHLAMAYDIGAN BO'SHLIQ (D-01).

    `chat_id` / `telegram_user_id` / `telegram_username` `PERSONAL_FIELDS`
    da YO'Q, ya'ni yuqoridagi darvoza ularni KO'RMAYDI. Ular esa odamni
    TASHQI tizimda (Telegram) aniqlaydi va chegaradan chiqib bo'lgan
    identifikator — ularni hisobot javobiga qo'yish sotuvchining
    Telegram hisobini bozor xodimining ekraniga olib chiqardi.

    ⚠ QAMROV SHU FAZANING YUZASI BILAN CHEKLANGAN va bu ONGLI: eski
      marshrutlarni qamrash bu rejaning ishi emas va ularda bunday
      maydon UMUMAN yo'q (bog'lanishlar jadvali 07-02 da tug'ilgan).
    """
    offenders = {
        path: sorted(response_field_names(route.response_model) & TELEGRAM_IDENTIFIER_FIELDS)
        for path, route in reconciliation_routes(fastapi_app).items()
        if response_field_names(route.response_model) & TELEGRAM_IDENTIFIER_FIELDS
    }

    assert not offenders, (
        "Nomuvofiqlik javobida Telegram identifikatori bor. U `PERSONAL_FIELDS` "
        "da YO'Q, ya'ni C-10 darvozasi uni ushlamaydi — lekin u odamni tashqi "
        f"tizimda ANIQLAYDI (D-01, §5.5): {offenders}"
    )


def test_reconciliation_routes_never_enter_the_binary_classification() -> None:
    """⛔ Beshalasi ham `response_model` E'LON QILADI — bayt-ro'yxatlar TEGILMAYDI.

    =========================================================================
    ⛔⛔ REJA «yangi marshrutlar `NON_PERSONAL_BINARY_ROUTES` ga
        qo'shiladi» degan edi. AMALDA BUNING TESKARISI TO'G'RI VA U
        SHU YERDA O'LCHANADI.

    `binary_routes()` FAQAT `response_model` I YO'Q `GET` larni
    to'playdi. Beshala marshrut ham modelini e'lon qiladi, ya'ni ular
    o'sha to'plamga UMUMAN tushmaydi — va ularni tasnif ro'yxatiga
    qo'shish `test_every_binary_response_route_is_classified` ning
    ESKIRISH tekshiruvini (`classified - found`) QIZARTIRARDI.

    ⚠ DA'VO KUCHLIROQ: model YO'QLIGI shaxsiy-ma'lumot darvozasini
      KO'R qiladi (`BINARY_PERSONAL_ROUTES` docstringi — 04-09 ning
      topilmasi). Model BORLIGI esa yuqoridagi maydon-nomi darvozasini
      HAQIQATAN ishlatadi. Ya'ni bu test «tasniflanmadi» degan bo'shliq
      emas, darvozaning ISHLAYOTGANINING sharti.
    =========================================================================
    """
    modelless = sorted(
        path
        for path, route in reconciliation_routes(fastapi_app).items()
        if route.response_model is None
    )

    assert modelless == [], (
        "Nomuvofiqlik marshruti javob modelisiz qoldi — o'shanda maydon-nomi "
        f"darvozasi u uchun KO'R bo'lardi (04-09 topilmasi): {modelless}"
    )

    classified = set(BINARY_PERSONAL_ROUTES) | set(NON_PERSONAL_BINARY_ROUTES)
    assert not {path for path in classified if path.startswith(RECONCILIATION_PREFIX)}, (
        "Nomuvofiqlik marshruti BAYT tasnifi ro'yxatiga qo'shilgan — u yerda "
        "faqat `response_model` I YO'Q marshrutlar bo'ladi va ortiqcha yozuv "
        "`test_every_binary_response_route_is_classified` ni qizartiradi"
    )


def test_the_any_permission_gate_exists_nowhere_else_in_the_app() -> None:
    """«Yo P yo Q» darvozasi BUTUN ilovada faqat e'lon qilingan marshrut(lar)da.

    =======================================================================
    ⛔ BU YUQORIDAGI YOPIQLIKNING TASHQI HALQASI.

    `test_the_snapshot_surface_is_a_closed_set` `snapshots.py` ni
    qo'riqlaydi. Lekin «yo P yo Q» darvozasi BOSHQA faylda tug'ilsa —
    masalan kimdir `occupancy.py` ga `require_any_permission(CAMERA_VIEW,
    OCCUPANCY_REVIEW)` yozsa — modul filtri unga yetib bormaydi.

    05-VERIFICATION §1 buni `grep` bilan tasdiqlagan edi. `grep` —
    o'lchov, darvoza emas: u tekshirilgan kunda rost gapiradi va ertasiga
    hech nimani ushlab turmaydi. Bu test o'sha grep ni MARSHRUT GRAFI
    ustidagi yopiq to'plamga aylantiradi.
    =======================================================================
    """
    gated = sorted(
        path
        for path, route in _walk(fastapi_app.routes, prefix="")
        if isinstance(route, APIRoute) and required_any_permissions(route)
    )

    assert gated == sorted(ANY_PERMISSION_GATE_ROUTES), (
        "«kamida bittasi» darvozasini ko'targan marshrutlar to'plami "
        f"o'zgardi.\n  Topildi:   {gated}\n  E'lon qilingan: "
        f"{sorted(ANY_PERMISSION_GATE_ROUTES)}\n\n"
        "Yangi «yo P yo Q» darvozasi qo'shilgan bo'lsa — u huquq talabini "
        "BO'SHASHTIRADI (P siz ham o'tish mumkin) va shuning uchun u "
        "`SNAPSHOT_EVIDENCE_FRAME_ROUTES` da NOM BILAN e'lon qilinishi kerak. "
        "Darvoza olib tashlangan bo'lsa — dalil-kadr endi nazoratchiga "
        "yopiq, ya'ni 05-15 ning butun mazmuni yo'qolgan."
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
