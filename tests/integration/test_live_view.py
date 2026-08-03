"""Jonli ko'rishning uchidan-uchiga isboti — SC#6 ning darvozasi (CAM-03).

=============================================================================
SC#6: *«Direktor avtorizatsiyadan keyin jonli kamera tasvirini ko'radi;
avtorizatsiyasiz to'g'ridan-to'g'ri havola ISHLAMAYDI».*

Ikkinchi yarmi — «ishlamaydi» — bu fayldagi testlarning KO'PCHILIGI.
Sabab arifmetik: muvaffaqiyat yo'li BITTA, rad etish yo'llari esa
oltita va ularning HAR BIRI mustaqil ravishda buzilishi mumkin.

Rad etish matritsasi (`/internal/live-authz`):

    chipta yo'q            ->  403
    chipta takrorlangan    ->  403   (parameter pollution)
    `src` yo'q             ->  403
    ODDIY access token     ->  403   (auditoriya ajratilishi, T-03-48)
    muddati o'tgan chipta  ->  403   (D-08)
    boshqa kameraning oqimi->  403   (T-03-46 — chipta OQIMGA bog'langan)
=============================================================================

=============================================================================
UCHTA NAZORAT HOLATI — VA ULAR IXTIYORIY EMAS.

  (a) `test_forbidden_live_token_is_not_audited` — 403 olgan so'rovdan
      KEYIN `audit_log` da YANGI qator YO'Q. Bu «huquq dekoratorda,
      imzoda emas» kafolatining BEVOSITA o'lchovi: agar dependency
      imzoga ko'chirilsa, FastAPI `audit_read` ni OLDIN hal qiladi va
      ko'rmagan odam jurnalda «ko'rdi» bo'lib qolardi (T-03-49).

  (b) `test_live_token_is_not_an_api_token` va uning TESKARI jufti —
      auditoriya ajratilishi IKKI TOMONLAMA o'lchanadi. Faqat bitta
      tomonni sinash 60 soniyalik chiptaning 15 daqiqalik access
      tokenga aylanishini ochiq qoldirardi.

  (c) `test_token_does_not_work_for_another_cameras_stream` — chipta
      OQIM NOMIGA bog'langan. Usiz A bozori direktori O'Z kamerasi
      uchun haqiqiy chipta olib, `src` ni B bozori kamerasining oqim
      nomiga almashtirib yuborardi va tekshiruv baribir 204 berardi.
=============================================================================

⚠ HAQIQIY go2rtc KONTEYNERI KERAK EMAS. `Go2rtcClient` mock bilan
almashtiriladi (`go2rtc_calls` fixture'i) va bu ataylab: bu fayl
AVTORIZATSIYANI o'lchaydi, media serverining ishlashini emas. go2rtc
bilan haqiqiy muloqot 4-fazadagi kadr olish yo'lida sinaladi.

FON VAZIFASINI KUTISH MEXANIZMI O'YLAB TOPILMAYDI: `audit_read` yozuvni
`BackgroundTasks` orqali yuboradi, `httpx.ASGITransport` esa fon
vazifalarini javob qaytarilishidan OLDIN bajaradi — ya'ni `await
client.post(...)` tugagach yozuv allaqachon bazada
(`test_personal_data_audit.py` da o'rnatilgan qoida).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.security.tokens import LIVE_TOKEN_AUDIENCE, issue_live_token
from app.services.go2rtc import assert_safe_go2rtc_src
from fixtures.admin_api import bearer, session_headers
from fixtures.auth_api import audit_rows
from fixtures.nvr_domain import nvr_rows
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.enums import AuditAction
from sbozor_core.security import encode_live

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from app.settings import Settings
    from fixtures import TenantSessionFactory
    from fixtures.nvr_domain import NvrDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.usefixtures("migrated")

CAMERAS_URL = "/api/v1/cameras"
AUTHZ_URL = "/internal/live-authz"

TABLE_CAMERAS = "cameras"
LIVE_VIEW = "live_view"
CAMERA_VIEW = "camera_view"
"""Ikki `reason` ATAYIN har xil — «reestr varaqlandi» va «jonli tasvir
ochildi» ikki xil hodisa (`api/v1/cameras.py` dagi alias docstringlari).
Bir xil qiymat bilan jurnal bu farqni ko'rsata olmasdi."""


# ---------------------------------------------------------------------------
# Seed, sessiyalar va go2rtc mock'i
# ---------------------------------------------------------------------------


@pytest.fixture
def nvr_seed(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
) -> Iterator[NvrDomainSeed]:
    """`two_markets` ustiga NVR + kamera qatlami."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        yield seed


@pytest.fixture
def go2rtc_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """`Go2rtcClient` ni YOZIB OLUVCHI soxta bilan almashtiradi.

    ⚠ NEGA ALMASHTIRISH KERAK: haqiqiy klient `settings.go2rtc_url` ga
      HTTP so'rov yuboradi va test muhitida u yerda hech kim yo'q —
      har chaqiruv 5 soniya kutib, keyin 503 berardi.

    ⚠ ALMASHTIRISH `monkeypatch` BILAN, QO'LDA EMAS: u atributni
      TIKLAYDI, o'chirmaydi (03-06 Issue 2 ning aynan takrori —
      `app.api.v1.cameras` modul darajasidagi YAGONA obyekt va
      qoldirilgan atribut boshqa test modullariga sizib o'tardi).
      Nishon SATR bilan beriladi, chunki `cameras.py` `Go2rtcClient` ni
      RE-EXPORT qilmaydi (mypy `--no-implicit-reexport`) — atributga
      to'g'ridan-to'g'ri murojaat tip xatosi berardi.
    """
    calls: list[tuple[str, str]] = []

    class _RecordingClient:
        def __init__(self, base_url: str, **_: Any) -> None:
            self.base_url = base_url

        async def __aenter__(self) -> _RecordingClient:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def ensure_stream(self, stream_name: str, src: str) -> bool:
            # ⚠ ALLOW-LIST MOCK'DA HAM QO'LLANADI. Aks holda test
            #   `assert_safe_go2rtc_src` ni butunlay chetlab o'tardi va
            #   «mahsulot yo'li xavfsiz `src` yuboradi» da'vosi
            #   sinalmasdan qolardi.
            assert_safe_go2rtc_src(src)
            calls.append((stream_name, src))
            return True

    monkeypatch.setattr("app.api.v1.cameras.Go2rtcClient", _RecordingClient)
    return calls


@pytest.fixture
async def viewer_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    nvr_seed: NvrDomainSeed,
) -> dict[str, str]:
    """A bozori DIREKTORI — `CAMERA_VIEW` bor, `CAMERA_MANAGE` yo'q (D-07)."""
    return await session_headers(api_client, two_markets.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def cashier_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    nvr_seed: NvrDomainSeed,
) -> dict[str, str]:
    """A bozori KASSIRI — `CAMERA_VIEW` YO'Q (rbac matritsasi: faqat `PAYMENT_CREATE`)."""
    return await session_headers(api_client, two_markets.market_a.cashier_phone, SEED_PASSWORD)


async def _camera_reads(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
    *,
    reason: str,
) -> list[Any]:
    """`action='read'` + `table_name='cameras'` + berilgan `reason` qatorlari.

    Superuser bilan O'QILMAYDI: audit ekrani (D-11) aynan shu yo'ldan
    ma'lumot oladi, ya'ni test MAHSULOT yo'lini sinaydi
    (`test_personal_data_audit.py::_stall_reads` bilan bir xil qoida).
    """
    rows = await audit_rows(tenant_session, market_id, action=str(AuditAction.READ))
    return [
        row
        for row in rows
        if row.table_name == TABLE_CAMERAS and (row.new_value or {}).get("reason") == reason
    ]


def _token_url(camera_id: UUID) -> str:
    return f"{CAMERAS_URL}/{camera_id}/live-token"


# ---------------------------------------------------------------------------
# MUVAFFAQIYAT YO'LI — SC#6 ning birinchi yarmi
# ---------------------------------------------------------------------------


async def test_director_receives_a_live_token(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    go2rtc_calls: list[tuple[str, str]],
) -> None:
    """`CAMERA_VIEW` bilan 200 + opaque URL; `stream_name` OCHIQ KO'RINMAYDI.

    Ikkita ALOHIDA da'vo (UI-SPEC §8.7): chipta berildi VA oqim nomi
    javobning alohida maydonida EMAS — u faqat URL ichida. Alohida
    maydon UI'da ko'rsatilardi va nusxa olinardi.
    """
    camera_id = nvr_seed.market_a.active_camera_ids[0]

    response = await api_client.post(_token_url(camera_id), headers=viewer_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["url"].startswith("/live/"), body["url"]
    assert body["expires_in"] == 60, "D-08: chipta 60 soniyadan uzoq yashamaydi"
    assert set(body) == {"url", "expires_in", "transport_hint"}, (
        f"javobda kutilmagan maydon bor: {sorted(body)} — `stream_name` yoki "
        "`rtsp_url` sizib chiqmaganini tekshiring"
    )


async def test_live_token_is_audited_with_its_own_reason(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    tenant_session: TenantSessionFactory,
    go2rtc_calls: list[tuple[str, str]],
) -> None:
    """Jonli ko'rish `reason='live_view'` bilan jurnalga tushadi (RESEARCH E.15).

    ⚠ `reason` REESTR O'QISHIDAN AJRATILGAN: nizo paytida «kim jonli
      tasvirni ochdi» va «kim ro'yxatni varaqladi» ikki xil savol.
      Nazorat bandi: bu chaqiruvdan keyin `camera_view` qatorlari
      soni O'ZGARMAYDI.
    """
    market_id = nvr_seed.market_a.market_id
    camera_id = nvr_seed.market_a.active_camera_ids[0]
    before_live = len(await _camera_reads(tenant_session, market_id, reason=LIVE_VIEW))
    before_list = len(await _camera_reads(tenant_session, market_id, reason=CAMERA_VIEW))

    response = await api_client.post(_token_url(camera_id), headers=viewer_headers)
    assert response.status_code == 200, response.text

    after_live = await _camera_reads(tenant_session, market_id, reason=LIVE_VIEW)
    after_list = await _camera_reads(tenant_session, market_id, reason=CAMERA_VIEW)

    assert len(after_live) == before_live + 1, "jonli ko'rish jurnalga tushmadi"
    assert len(after_list) == before_list, (
        "jonli ko'rish `camera_view` qatorini ham yozdi — ikki hodisa jurnalda ajralmay qoldi"
    )
    assert after_live[-1].new_value["filters"]["camera_id"] == str(camera_id)


async def test_stream_registered_dynamically(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    go2rtc_calls: list[tuple[str, str]],
) -> None:
    """Oqim go2rtc'ga RESTART'SIZ, ko'rish so'ralganda qo'shiladi (RESEARCH D.13).

    Restart QABUL QILIB BO'LMAYDI: u boshqa bozorlarning ko'rishini
    uzardi. Shuning uchun ro'yxatga olish LAZY va `PUT /api/streams`
    orqali.

    ⚠ UZATILGAN `src` `rtsp://` BILAN BOSHLANADI — bu D-11 ning
      MAHSULOT YO'LIDAGI isboti: `assert_safe_go2rtc_src` ning unit
      testi funksiyani sinaydi, bu esa uni haqiqatan CHAQIRILISHINI.
    """
    camera_id = nvr_seed.market_a.active_camera_ids[0]

    response = await api_client.post(_token_url(camera_id), headers=viewer_headers)
    assert response.status_code == 200, response.text

    assert len(go2rtc_calls) == 1, f"`ensure_stream` chaqirilmadi: {go2rtc_calls}"
    stream_name, src = go2rtc_calls[0]
    assert stream_name in nvr_seed.market_a.stream_names
    assert src.startswith("rtsp://"), src
    assert "@" not in src, "RTSP URL'ida userinfo bo'limi paydo bo'ldi (T-03-24)"


# ---------------------------------------------------------------------------
# RAD ETISH — chipta BERILISHI bosqichida
# ---------------------------------------------------------------------------


async def test_forbidden_live_token_is_not_audited(
    api_client: httpx.AsyncClient,
    cashier_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """NAZORAT: 403 olgan so'rov jurnalga YOLG'ON DALIL yozmaydi (T-03-49).

    ⚠ BU TEST «HUQUQ DEKORATORDA» QARORINING BEVOSITA O'LCHOVI. Agar
      `require_permission(CAMERA_VIEW)` dekoratordan imzo parametriga
      ko'chirilsa, FastAPI `audit_read` ni OLDIN hal qiladi va kassir
      403 olishiga qaramay jurnalda «jonli tasvirni ko'rdi» qatori
      qolardi. Nizoda bu dalil YOLG'ON bo'lardi.
    """
    market_id = nvr_seed.market_a.market_id
    camera_id = nvr_seed.market_a.active_camera_ids[0]
    before = len(await _camera_reads(tenant_session, market_id, reason=LIVE_VIEW))

    response = await api_client.post(_token_url(camera_id), headers=cashier_headers)

    assert response.status_code == 403, response.text
    after = len(await _camera_reads(tenant_session, market_id, reason=LIVE_VIEW))
    assert after == before, (
        "403 olgan so'rov `audit_log` ga yozdi — huquq dependency'si "
        "imzoga ko'chib qolgan bo'lishi mumkin (§S-4)"
    )


async def test_other_markets_camera_is_not_found(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
) -> None:
    """A bozori direktori B bozori kamerasi uchun chipta so'rasa — **404** (T-03-46).

    404, 403 EMAS: 403 javobning O'ZI «bunday kamera bor, lekin sizniki
    emas» degan ma'lumotni oshkor qilardi.
    """
    foreign_camera = nvr_seed.market_b.camera_ids[0]

    response = await api_client.post(_token_url(foreign_camera), headers=viewer_headers)

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "not_found"


async def test_archived_camera_has_no_live_token(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
) -> None:
    """Arxivlangan kamera uchun chipta so'ralganda **404** (UI-SPEC §8.5).

    Arxivlangan kanalning oqimi go2rtc'da ro'yxatga OLINMAYDI (§6.6),
    ya'ni chipta berish ishlamaydigan URL qaytarardi va UI xatoni
    «transport nosozligi» deb ko'rsatardi — admin esa sababni topa
    olmasdi.
    """
    archived = nvr_seed.market_a.archived_camera_id
    assert archived is not None, "seed'da arxivlangan kamera yo'q — test ma'nosini yo'qotdi"

    response = await api_client.post(_token_url(archived), headers=viewer_headers)

    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# RAD ETISH — `auth_request` bosqichida
# ---------------------------------------------------------------------------


async def test_live_authz_without_a_token_is_denied(
    api_client: httpx.AsyncClient,
    nvr_seed: NvrDomainSeed,
) -> None:
    """Tokensiz so'rov **403** va javob TANASIZ.

    Bu marshrut nginx'da `internal;` bilan ham himoyalangan, LEKIN
    tekshiruv shu yerda ham bo'lishi SHART: himoya proxy
    konfiguratsiyasiga BOG'LIQ bo'lmasligi kerak.
    """
    response = await api_client.get(AUTHZ_URL, params={"src": "cam_yoq"})

    assert response.status_code == 403
    assert response.content == b"", "javob tanasi nginx jurnaliga sizib ketishi mumkin"


async def test_live_authz_without_a_stream_is_denied(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    test_settings: Settings,
) -> None:
    """`src` siz so'rov **403** — chipta haqiqiy bo'lsa ham.

    `src` ni ixtiyoriy qilish chiptani oqimga bog'lash imkonini
    YO'QOTARDI: tekshiruv «token haqiqiy» degan yagona da'vo bilan
    qolardi va go2rtc istalgan oqimni berardi.
    """
    market = nvr_seed.market_a
    token = issue_live_token(
        camera_id=market.active_camera_ids[0],
        market_id=market.market_id,
        user_id=uuid4(),
        settings=test_settings,
    )

    response = await api_client.get(AUTHZ_URL, params={"t": token})

    assert response.status_code == 403


async def test_valid_ticket_and_stream_are_allowed(
    api_client: httpx.AsyncClient,
    nvr_seed: NvrDomainSeed,
    test_settings: Settings,
) -> None:
    """Haqiqiy chipta + mos oqim nomi -> **204**, tanasiz.

    IJOBIY HOLAT MAJBURIY: usiz barcha rad etish testlari `return 403`
    bilan almashtirilgan darvoza ustida ham yashil qolardi va jonli
    ko'rish umuman ishlamasdi.
    """
    market = nvr_seed.market_a
    index = market.camera_ids.index(market.active_camera_ids[0])
    token = issue_live_token(
        camera_id=market.active_camera_ids[0],
        market_id=market.market_id,
        user_id=uuid4(),
        settings=test_settings,
    )

    response = await api_client.get(
        AUTHZ_URL,
        params={"t": token, "src": market.stream_names[index]},
    )

    assert response.status_code == 204, response.text
    assert response.content == b""


async def test_expired_live_token_is_rejected(
    api_client: httpx.AsyncClient,
    nvr_seed: NvrDomainSeed,
    test_settings: Settings,
) -> None:
    """Muddati o'tgan chipta **403** — D-08 ning butun mazmuni.

    D-08 bekor qilish mexanizmidan ATAYIN voz kechgan: 60 soniyalik
    muddat uning O'RNINI bosadi. Ya'ni bu tekshiruv buzilsa, jonli
    ko'rish havolasi CHEKSIZ ishlaydigan bo'lib qolardi va uni
    ulashish mumkin bo'lardi (T-03-47).

    Token MAHSULOT funksiyasi bilan, faqat MANFIY TTL bilan chiqariladi
    (`test_cross_tenant::test_expired_token_is_rejected` naqshi) — ya'ni
    imzo HAQIQIY va rad etishning yagona sababi muddat.
    """
    market = nvr_seed.market_a
    index = market.camera_ids.index(market.active_camera_ids[0])
    expired = encode_live(
        user_id=uuid4(),
        market_id=market.market_id,
        camera_id=market.active_camera_ids[0],
        secret=test_settings.jwt_secret,
        issuer=test_settings.jwt_issuer,
        audience=LIVE_TOKEN_AUDIENCE,
        ttl_seconds=-60,
    )

    response = await api_client.get(
        AUTHZ_URL,
        params={"t": expired, "src": market.stream_names[index]},
    )

    assert response.status_code == 403


async def test_repeated_token_parameter_is_rejected(
    api_client: httpx.AsyncClient,
    nvr_seed: NvrDomainSeed,
    test_settings: Settings,
) -> None:
    """`?t=<haqiqiy>&t=<yolg'on>` **403** — parameter pollution.

    HTTP parametrni ikki marta berishga ruxsat beradi va turli qatlamlar
    turli qiymatni tanlaydi (nginx birinchisini, go2rtc oxirgisini).
    Bitta qiymatni «tanlab olish» biz tekshirgan chipta go2rtc
    ishlatadigan chipta BO'LMASLIGI xavfini ochardi.
    """
    market = nvr_seed.market_a
    index = market.camera_ids.index(market.active_camera_ids[0])
    token = issue_live_token(
        camera_id=market.active_camera_ids[0],
        market_id=market.market_id,
        user_id=uuid4(),
        settings=test_settings,
    )

    response = await api_client.get(
        f"{AUTHZ_URL}?t={token}&t=soxta&src={market.stream_names[index]}"
    )

    assert response.status_code == 403


async def test_token_does_not_work_for_another_cameras_stream(
    api_client: httpx.AsyncClient,
    nvr_seed: NvrDomainSeed,
    test_settings: Settings,
) -> None:
    """Chipta OQIM NOMIGA bog'langan — `src` almashtirilsa **403** (T-03-46).

    ⚠ BU TEST BUTUN DARVOZANING MA'NOSINI USHLAB TURADI. Chipta
      oqimga bog'lanmasa, A bozori direktori O'Z kamerasi uchun
      HAQIQIY chipta olib, `src` ni B bozori kamerasining oqim nomiga
      almashtirib yuborardi — tekshiruv 204 berardi (chipta haqiqiy!)
      va go2rtc B bozorining tasvirini uzatardi.
    """
    market = nvr_seed.market_a
    token = issue_live_token(
        camera_id=market.active_camera_ids[0],
        market_id=market.market_id,
        user_id=uuid4(),
        settings=test_settings,
    )

    response = await api_client.get(
        AUTHZ_URL,
        params={"t": token, "src": nvr_seed.market_b.stream_names[0]},
    )

    assert response.status_code == 403


async def test_ticket_for_an_archived_camera_is_rejected(
    api_client: httpx.AsyncClient,
    nvr_seed: NvrDomainSeed,
    test_settings: Settings,
) -> None:
    """Arxivlangan kameraning chiptasi `auth_request` da ham **403**.

    Chipta arxivlashdan OLDIN berilgan bo'lishi mumkin: 60 soniyalik
    oyna admin qaroridan keyin ham ochiq qolardi. Ikkala qatlam ham
    (chipta berish va `auth_request`) arxiv holatini MUSTAQIL
    tekshiradi.
    """
    market = nvr_seed.market_a
    archived = market.archived_camera_id
    assert archived is not None
    index = market.camera_ids.index(archived)
    token = issue_live_token(
        camera_id=archived,
        market_id=market.market_id,
        user_id=uuid4(),
        settings=test_settings,
    )

    response = await api_client.get(
        AUTHZ_URL,
        params={"t": token, "src": market.stream_names[index]},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# AUDITORIYA AJRATILISHI — IKKI TOMONLAMA (T-03-48)
# ---------------------------------------------------------------------------


async def test_live_token_is_not_an_api_token(
    api_client: httpx.AsyncClient,
    nvr_seed: NvrDomainSeed,
    test_settings: Settings,
) -> None:
    """Jonli chipta bilan oddiy API so'rovi RAD ETILADI (`aud` ajratilgan).

    Bir xil auditoriya bilan `/live/` uchun berilgan 60 soniyalik chipta
    butun API'ga kirish huquqiga aylanardi: u imzolangan va `sub` si bor,
    ya'ni `get_current_principal` uni access token deb qabul qilardi.
    """
    market = nvr_seed.market_a
    token = issue_live_token(
        camera_id=market.active_camera_ids[0],
        market_id=market.market_id,
        user_id=uuid4(),
        settings=test_settings,
    )

    response = await api_client.get(CAMERAS_URL, headers=bearer(token))

    assert response.status_code == 401, response.text


async def test_api_token_is_not_a_live_ticket(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    nvr_seed: NvrDomainSeed,
    viewer_headers: dict[str, str],
) -> None:
    """TESKARI JUFT: ODDIY access token `auth_request` da **403**.

    Bu tomon usiz 15 daqiqalik token bilan olingan jonli havola D-08
    ning butun «qisqa muddat bekor qilishni keraksiz qiladi»
    mulohazasini bekor qilardi.

    Token `viewer_headers` dan olinadi, ya'ni u HAQIQIY va o'sha
    foydalanuvchida `CAMERA_VIEW` BOR — rad etishning yagona sababi
    auditoriya.
    """
    market = nvr_seed.market_a
    access_token = viewer_headers["Authorization"].removeprefix("Bearer ")

    response = await api_client.get(
        AUTHZ_URL,
        params={"t": access_token, "src": market.stream_names[0]},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Reestr yuzasi — o'qish auditi va soft-delete
# ---------------------------------------------------------------------------


async def test_camera_list_is_audited_and_hides_archived_rows(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`GET /cameras` — arxivlanganlarsiz + `reason='camera_view'` yozuvi.

    Ikkita da'vo bir testda, chunki ular BIR chaqiruvning ikki tomoni:
    javob mazmuni (D-10 soft-delete UI'da ko'rinmaydi) va uning izi
    (D-09).
    """
    market = nvr_seed.market_a
    before = len(await _camera_reads(tenant_session, market.market_id, reason=CAMERA_VIEW))

    response = await api_client.get(CAMERAS_URL, headers=viewer_headers)

    assert response.status_code == 200, response.text
    returned = {UUID(item["id"]) for item in response.json()["items"]}
    assert returned == set(market.active_camera_ids), (
        "standart ro'yxat arxivlangan kanalni ham qaytardi (D-10)"
    )

    after = await _camera_reads(tenant_session, market.market_id, reason=CAMERA_VIEW)
    assert len(after) == before + 1
    assert after[-1].new_value["result_count"] == len(market.active_camera_ids)


async def test_archived_rows_appear_only_when_asked(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
) -> None:
    """NAZORAT: `?archived=true` bilan arxivlangan qator KO'RINADI (UI-SPEC §6.6).

    Usiz yuqoridagi test «ro'yxat har doim kam qator qaytaradi» degan
    xato bilan ham yashil bo'lardi — masalan filtr butun `nvr_id`
    bo'yicha noto'g'ri ishlaganda.
    """
    market = nvr_seed.market_a

    response = await api_client.get(
        CAMERAS_URL, params={"archived": "true"}, headers=viewer_headers
    )

    assert response.status_code == 200, response.text
    returned = {UUID(item["id"]) for item in response.json()["items"]}
    assert returned == set(market.camera_ids)
    assert market.archived_camera_id in returned


async def test_source_ip_is_serialised_without_the_inet_prefix(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """`source_ip` javobda `/32` prefiksisiz (03-04 `threat_flag: value-format`).

    PostgreSQL `inet` ustuni qiymatni `192.168.1.10/32` bo'lib qaytaradi
    va 03-04 buni ATAYIN tuzatmasdan, normalizatsiyani serializatsiya
    chegarasiga topshirgan. UI meta qatorida (`UI-SPEC §6.1`) prefiks
    admin uchun tushunarsiz shovqin bo'lardi.
    """
    market = nvr_seed.market_a
    camera_id = market.active_camera_ids[0]
    sync_owner_conn.execute(
        "UPDATE cameras SET source_ip = %s WHERE id = %s",
        ("192.168.1.10", str(camera_id)),
    )

    response = await api_client.get(CAMERAS_URL, headers=viewer_headers)

    assert response.status_code == 200, response.text
    row = next(item for item in response.json()["items"] if item["id"] == str(camera_id))
    assert row["source_ip"] == "192.168.1.10", (
        f"`source_ip` xom `inet` ko'rinishida qaytdi: {row['source_ip']!r}"
    )


async def test_archive_keeps_the_row(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    nvr_seed: NvrDomainSeed,
    api_client_admin_headers: dict[str, str],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """Arxivlash qatorni O'CHIRMAYDI va `restore` uni qaytaradi (D-10).

    `SELECT count(*)` chaqiruvdan OLDIN va KEYIN bir xil: bu D-10 ning
    yagona mexanik dalili — `is_archived=true` ni tekshirish qator
    o'chirilgan holatda ham (0 qator qaytganda) chalkash natija berardi.
    """
    market = nvr_seed.market_a
    camera_id = market.active_camera_ids[0]
    count_sql = "SELECT count(*) FROM cameras WHERE market_id = %s"
    before = sync_owner_conn.execute(count_sql, (str(market.market_id),)).fetchone()

    archived = await api_client.post(
        f"{CAMERAS_URL}/{camera_id}/archive", headers=api_client_admin_headers
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["is_archived"] is True

    after = sync_owner_conn.execute(count_sql, (str(market.market_id),)).fetchone()
    assert before == after, "arxivlash qatorni o'chirdi — D-10 buzildi"

    restored = await api_client.post(
        f"{CAMERAS_URL}/{camera_id}/restore", headers=api_client_admin_headers
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["is_archived"] is False


@pytest.fixture
async def api_client_admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    nvr_seed: NvrDomainSeed,
) -> dict[str, str]:
    """A bozori ADMINI — `CAMERA_MANAGE` bor (arxivlash uchun)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)
