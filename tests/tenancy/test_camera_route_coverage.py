"""Kamera yuzasining IKKI STRUKTURAVIY darvozasi (SC#4, SC#6, D-11).

=============================================================================
BU FAYL IKKITA MUSTAQIL DA'VONI QULFLAYDI VA ULAR ATAYIN AJRATILGAN.

  (a) HUQUQ — `cameras`/`nvr-devices` yuzasidagi har `GET` marshruti
      `CAMERA_VIEW` ni e'lon qiladi. Savol: «bu hodisa umuman sodir
      bo'lishi kerakmidi?»

  (b) SIZIB CHIQISH — o'sha yuzadagi HECH BIR javob modelida (ichma-ich
      ham) `password`, `password_encrypted`, `rtsp_url` yoki
      `stream_name` nomli maydon YO'Q. Savol: «javobda nima bor?»

Bittasini buzish ikkinchisini qizartirmaydi — shuning uchun ular ikki
alohida test. `test_personal_data_coverage.py` da o'rnatilgan qoida.

⚠ MARSHRUT GRAFI O'QILADI, MANBA MATNI EMAS. Fayllarni regex bilan
tirnash dekorator shakli o'zgarganda (alias orqali berilsa, boshqa
qatorga ko'chirilsa) hech nima topmasdi va darvoza JIMGINA yashil bo'lib
qolardi — ya'ni unutish xavfsiz tomonga emas, XAVFLI tomonga ishlardi.
=============================================================================

NEGA (b) STRUKTURAVIY DARVOZA, KELISHUV EMAS:

`stream_name` — go2rtc'dagi oqimning BEVOSITA nishoni (UI-SPEC §8.7).
U javobda ko'ringan zahoti UI'da ko'rsatiladi, nusxa olinadi va
ertami-kechmi `/live/...?src=<nom>` shaklida qo'lda yig'iladi — o'shanda
`auth_request` darvozasi o'z ma'nosini yo'qotadi. `rtsp_url` esa D-01
ning to'g'ridan-to'g'ri buzilishi: RTSP URL UI'da HECH QACHON
ko'rsatilmaydi. `password` — SC#4.

Uchalasi ham BUGUN javoblarda yo'q. Bu fayl bugungi xatoni emas,
UNING QAYTISHINI bloklaydi: kimdir «qulaylik uchun» maydon qo'shsa,
CI aynan shu yerda qizaradi va sababni SHU YERDA o'qiydi.

BU FAYLDA "KUTILGAN NOSOZLIK" VA "O'TKAZIB YUBORISH" MARKERLARI YO'Q.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from app.main import app as fastapi_app
from app.security.rbac import Permission
from fastapi.routing import APIRoute

from tenancy.test_cross_tenant import all_routes
from tenancy.test_personal_data_coverage import (
    _walk,
    audit_resources,
    required_permissions,
    response_field_names,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

pytestmark = pytest.mark.tenancy

CAMERA_SURFACE_PREFIXES = ("/api/v1/cameras", "/api/v1/nvr-devices")
"""Darvoza qamraydigan yo'l prefikslari.

IKKALASI HAM KERAK: `stream_name` `cameras` yuzasida tug'iladi, `password`
esa `nvr-devices` yuzasida. Faqat bittasini qamrash ikkinchisidagi
regressiyani ochiq qoldirardi va aynan shu ikkisi bir-birining eng yaqin
qo'shnisi — yangi maydon bir yuzadan ikkinchisiga ko'chib o'tishi oson.
"""

_FORBIDDEN = ("password", "password_encrypted", "rtsp_url", "stream_name")
FORBIDDEN_RESPONSE_FIELDS = frozenset(_FORBIDDEN)
"""Kamera/NVR yuzasidagi javob modellarida BO'LMASLIGI shart maydonlar.

Har biri BOSHQA-BOSHQA sabab bilan (fayl boshidagi izoh):
`password`/`password_encrypted` — SC#4; `rtsp_url` — D-01;
`stream_name` — UI-SPEC §8.7 va D-11 ning UI tomoni.

RO'YXAT ATAYIN QISQA VA ANIQ NOMLI. Uni «har ehtimolga qarshi»
kengaytirish (`url`, `token`, `secret`) darvozani shovqinga aylantirardi
va yagona amaliy yechim istisnolar ro'yxatini shishirish bo'lardi —
ya'ni darvoza o'z-o'zini bekor qilardi (T-02-148 bilan bir xil mulohaza).
"""

MINIMUM_CAMERA_ROUTES = 5
"""Darvoza kamida shuncha marshrutni QAMRASHI shart.

Amaldagi son 11 (yettita `nvr-devices` + to'rtta `cameras`). Chegara
ATAYIN pastroq: u «darvoza bo'shab qolmadimi?» savoliga javob beradi,
aniq sonni qulflamaydi. Aniq son yozilganda har yangi endpoint bu faylni
tahrirlashni talab qilardi va darvoza «shunchaki raqamni oshiring»
refleksini tug'dirardi (`test_personal_data_coverage.py::
MINIMUM_PERSONAL_ROUTES` bilan bir xil qoida).
"""

CONTROL_ROUTE = "/api/v1/nvr-devices/{nvr_id}/discovery-runs/{run_id}"
"""NAZORAT MARSHRUTI: `CAMERA_VIEW` talab qiladi, LEKIN o'qish auditini E'LON QILMAYDI.

Usiz bu fayl jimgina «kamera yuzasidagi har `GET` ga audit kerak» degan
darvozaga aylanardi va o'sha holda u D-09 ni emas, uning
QARAMA-QARSHISINI himoya qilardi.

Bu marshrutni UI HAR IKKI SONIYADA chaqiradi (UI-SPEC §5.3), ya'ni bitta
kashfiyot ~30 ta o'qish yozuvi qoldirardi va haqiqiy o'qish hodisalari
o'sha shovqin ichida ko'milardi — `api/v1/nvr.py` fayl boshidagi izohda
sabab to'liq yozilgan. `stalls.py` dagi `GET /map` nazorat holatining
aynan jufti.
"""

EXEMPT_ROUTES: dict[str, str] = {}
"""Kamera yuzasidagi, LEKIN `CAMERA_VIEW` talabidan ozod `GET` marshrutlari.

HOZIRCHA BO'SH — va bu ataylab hujjatlashtiriladi: yuzadagi hamma `GET`
huquq ostida. Ro'yxat SHAKLDA turadi, chunki uning yo'qligi keyingi
tahrirlovchini «istisno qilish mumkin emas ekan» degan xulosaga
olib kelardi va u huquqni imzoga ko'chirish kabi yomonroq yechim
tanlardi. Istisno qo'shilganda SABAB majburiy
(`test_exempt_routes_are_live_and_have_reasons`).
"""


def camera_surface_routes(app: FastAPI) -> dict[tuple[str, str], APIRoute]:
    """`(metod, yo'l)` -> kamera/NVR yuzasidagi marshrut.

    Ro'yxat NEGATIV tuziladi (prefiks bo'yicha), ya'ni yangi endpoint
    darvozaga AVTOMATIK tushadi. Pozitiv ro'yxat (qo'lda «qamrasin» deb
    belgilash) yangi marshrutni jimgina tashqarida qoldirardi.
    """
    found: dict[tuple[str, str], APIRoute] = {}
    for path, route in _walk(app.routes, prefix=""):
        if not isinstance(route, APIRoute) or not path.startswith(CAMERA_SURFACE_PREFIXES):
            continue
        for method in set(route.methods or set()) - {"HEAD", "OPTIONS"}:
            found[method, path] = route
    return found


SURFACE_ROUTES = camera_surface_routes(fastapi_app)
"""Import paytida bir marta hisoblanadi — `parametrize` va quyi chegara uchun."""

GET_ROUTES = {
    (method, path): route
    for (method, path), route in SURFACE_ROUTES.items()
    if method == "GET" and path not in EXEMPT_ROUTES
}


# ---------------------------------------------------------------------------
# Darvozaning O'ZI ishlayotganini tekshiruvchi testlar
# ---------------------------------------------------------------------------


def test_gate_covers_a_meaningful_number_of_routes() -> None:
    """Darvoza BO'SH to'plamni tekshirmayapti — YOLG'ON-YASHILning eng jimgina shakli.

    Prefiks o'zgarsa (masalan `/api/v1/cameras` -> `/api/v1/camera`)
    qolgan testlar hech nima topmay «hammasi joyida» deb tugardi.
    """
    assert len(SURFACE_ROUTES) >= MINIMUM_CAMERA_ROUTES, (
        f"darvoza atigi {len(SURFACE_ROUTES)} marshrut topdi "
        f"({sorted(SURFACE_ROUTES)}) — `CAMERA_SURFACE_PREFIXES` eskirgan "
        "yoki marshrut yurishi buzilgan"
    )
    assert GET_ROUTES, "yuzada birorta `GET` marshruti topilmadi — darvoza (a) bo'sh"


def test_walk_matches_the_shared_route_walker() -> None:
    """Bu yerdagi yurish `test_cross_tenant.all_routes()` bilan BIR XIL natija beradi.

    Yurish FastAPI ning ICHKI tuzilmasiga tayanadi (`original_router`,
    `include_context.prefix`). U o'zgarganda yurish istisno KO'TARMAYDI —
    u shunchaki kamroq marshrut topadi va butun fayl jimgina yashil
    bo'lib qoladi.
    """
    shared = {
        (route.method, route.path)
        for route in all_routes(fastapi_app)
        if route.path.startswith(CAMERA_SURFACE_PREFIXES)
    }

    assert set(SURFACE_ROUTES) == shared, (
        "ikki yurish ajralib ketdi: faqat bu yerda "
        f"{sorted(set(SURFACE_ROUTES) - shared)}, faqat u yerda "
        f"{sorted(shared - set(SURFACE_ROUTES))}"
    )


def test_exempt_routes_are_live_and_have_reasons() -> None:
    """Eskirgan istisno qolib ketmagan va har birining sababi bor."""
    live = {path for _, path in SURFACE_ROUTES}
    stale = sorted(path for path in EXEMPT_ROUTES if path not in live)

    assert not stale, f"`EXEMPT_ROUTES` da mavjud bo'lmagan marshrutlar qolgan: {stale}"
    for path, reason in EXEMPT_ROUTES.items():
        assert reason.strip(), f"{path}: istisno sababi bo'sh"


# ---------------------------------------------------------------------------
# (a) HUQUQ — har `GET` `CAMERA_VIEW` ostida
# ---------------------------------------------------------------------------


def test_every_camera_get_route_requires_camera_view() -> None:
    """Kamera/NVR yuzasidagi har `GET` `CAMERA_VIEW` ni E'LON QILADI (D-07).

    Talab DEKORATORDA bajarilishi kerak, imzoda emas — sabab
    `api/v1/cameras.py` modul docstringida (403 `audit_read` gacha yetib
    bormasligi). Bu test ikkalasini AJRATMAYDI (graf ikkalasini ham
    ko'radi); e'lon TARTIBI `test_live_view.py::
    test_forbidden_live_token_is_not_audited` da xulq bilan o'lchanadi.
    """
    missing = sorted(
        f"{method} {path}"
        for (method, path), route in GET_ROUTES.items()
        if Permission.CAMERA_VIEW not in required_permissions(route)
    )

    assert not missing, (
        "Quyidagi `GET` marshrutlari kamera yuzasida turibdi, lekin "
        "`CAMERA_VIEW` talab qilmaydi. Dekoratorga "
        "`dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))]` "
        "qo'shing (imzoga EMAS):\n  " + "\n  ".join(missing)
    )


def test_control_route_declares_no_read_audit() -> None:
    """NAZORAT: poll marshruti `CAMERA_VIEW` ostida, LEKIN auditsiz (T-02-148).

    Bu test yuqoridagini «hamma `GET` ga audit kerak» degan darvozadan
    AJRATADI. Usiz darvoza o'z qarama-qarshisini himoya qilardi.
    """
    route = GET_ROUTES.get(("GET", CONTROL_ROUTE))

    assert route is not None, (
        f"{CONTROL_ROUTE} umuman topilmadi — nazorat holati ma'nosini yo'qotdi"
    )
    assert Permission.CAMERA_VIEW in required_permissions(route), (
        f"{CONTROL_ROUTE} `CAMERA_VIEW` ni yo'qotdi — nazorat holati "
        "«huquqsiz marshrut» ga aylanib qoldi"
    )
    assert not audit_resources(route), (
        f"{CONTROL_ROUTE} o'qish auditini e'lon qilibdi — bitta kashfiyot ~30 ta "
        "yozuv qoldiradi va haqiqiy o'qish hodisalari shovqin ichida ko'miladi"
    )


def test_camera_list_declares_the_read_audit() -> None:
    """IJOBIY JUFT: kameralar reestrining o'qilishi jurnalga tushadi (D-09).

    Nazorat holati YOLG'IZ qolganda darvoza «auditni umuman qo'ymang»
    degan ma'noga siljib ketardi. Bu test uning qarshi tomonini ushlab
    turadi: yuzada AUDITLI marshrut ham bo'lishi shart.
    """
    route = GET_ROUTES.get(("GET", "/api/v1/cameras"))

    assert route is not None, "`GET /api/v1/cameras` topilmadi"
    assert "cameras" in audit_resources(route), (
        "`GET /api/v1/cameras` o'qish auditini e'lon qilmaydi — "
        "`Depends(audit_read(TABLE_CAMERAS, reason='camera_view'))` qo'shing"
    )


# ---------------------------------------------------------------------------
# (b) SIZIB CHIQISH — javob modellarining REKURSIV skani
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    sorted(SURFACE_ROUTES),
    ids=lambda value: str(value),
)
def test_no_secret_field_in_the_response_model(method: str, path: str) -> None:
    """Javob modelida (ICHMA-ICH ham) taqiqlangan maydon yo'q (SC#4, D-01, §8.7).

    REKURSIYA MAJBURIY: maydon deyarli hech qachon yuqori darajada
    turmaydi. `CameraListResponse.items: list[CameraRead]` da har qanday
    yangi maydon IKKI qavat pastda bo'ladi va faqat yuqori darajaga
    qaraydigan tekshiruv uni «toza» deb ko'rsatardi.
    """
    fields = response_field_names(SURFACE_ROUTES[method, path].response_model)
    leaked = sorted(fields & FORBIDDEN_RESPONSE_FIELDS)

    assert not leaked, (
        f"{method} {path} javob modelida taqiqlangan maydon(lar) bor: {leaked}. "
        "`password` — SC#4; `rtsp_url` — D-01; `stream_name` — UI-SPEC §8.7 "
        "(u go2rtc'dagi oqimning bevosita nishoni va avtorizatsiya "
        "darvozasini ma'nosiz qilardi)."
    )


def test_the_forbidden_field_scan_actually_inspects_models() -> None:
    """Skaner HAQIQATAN maydon ko'ryapti — bo'sh to'plamda yashil emas.

    Yuqoridagi test har marshrut uchun `fields & FORBIDDEN` ni tekshiradi
    va BO'SH `fields` bilan ham o'tardi (masalan `response_model` `None`
    bo'lsa yoki rekursiya buzilsa). Bu yerda ma'lum bir maydon nomining
    HAQIQATAN topilishi tekshiriladi — ya'ni mexanizmning o'zi tirik.
    """
    fields = response_field_names(SURFACE_ROUTES["GET", "/api/v1/cameras"].response_model)

    assert "channel_no" in fields, (
        "`CameraRead.channel_no` topilmadi — rekursiv skaner ishlamayapti va "
        "taqiqlangan maydon testi BO'SH to'plamda yashil bo'lib turibdi"
    )
    assert "has_password" in response_field_names(
        SURFACE_ROUTES["GET", "/api/v1/nvr-devices"].response_model
    ), "`NvrDeviceRead.has_password` topilmadi — NVR yuzasida skaner ishlamayapti"


# ---------------------------------------------------------------------------
# D-10 — qattiq o'chirish marshruti UMUMAN yo'q
# ---------------------------------------------------------------------------


def test_no_delete_route_exists_on_the_camera_surface() -> None:
    """`DELETE` kamera yuzasida UMUMAN yo'q (D-10, T-03-53).

    Tekshiruv `app.routes` ustida, MANBA MATNI ustida emas: marshrut
    boshqa faylda e'lon qilinsa yoki `api_route(methods=["DELETE"])`
    bilan yozilsa ham bu yerda ko'rinadi.

    ⚠ `cameras` yuzasida `DELETE` bo'lishi shunchaki nomuvofiqlik emas:
      `cameras.id` ga 4-fazadagi snapshotlar va 5-fazadagi zonalar
      bog'lanadi, ya'ni qatorning o'chirilishi TARIXIY DALILNI yo'q
      qilardi. O'rniga `POST /{id}/archive` va `POST /{id}/restore`.
    """
    deletes = sorted(path for method, path in SURFACE_ROUTES if method == "DELETE")

    assert not deletes, (
        f"Kamera/NVR yuzasida `DELETE` marshruti paydo bo'ldi: {deletes}. "
        "D-10 qattiq o'chirishni TAQIQLAYDI — `archive`/`restore` ishlating."
    )


def test_archive_and_restore_are_both_present() -> None:
    """Arxivlashning JUFTI ham bor — aks holda amal qaytarib bo'lmas edi.

    `restore` siz `archive` amalda qattiq o'chirishga teng bo'lardi
    (foydalanuvchi uchun qaytish yo'li yo'q) va UI-SPEC §9.2 bo'yicha
    2-darajali tasdiq talab qilinardi. Ikkalasi BIRGA tekshiriladi.
    """
    paths = {path for _, path in SURFACE_ROUTES}

    assert "/api/v1/cameras/{camera_id}/archive" in paths, "arxivlash marshruti yo'q"
    assert "/api/v1/cameras/{camera_id}/restore" in paths, (
        "arxivdan qaytarish marshruti yo'q — arxivlash qaytarib bo'lmaydigan bo'lib qoldi"
    )
