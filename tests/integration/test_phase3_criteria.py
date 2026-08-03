"""Fazaning SAKKIZTA muvaffaqiyat mezoni — ROADMAP matni bilan bog'langan YAGONA fayl.

=============================================================================
BU FAYL MAVJUD TESTLARNI TAKRORLAMAYDI — U ULARNI ZANJIR SIFATIDA BOG'LAYDI.

Har mezonning qismlari allaqachon qamralgan va ular o'z egasida qoladi:

  * `test_nvr_sim.py`           (03-02) — simulyatorning O'ZI, haqiqiy TCP;
  * `test_nvr_repo.py`          (03-04) — upsert ning uch qoidasi;
  * `test_rtsp_url.py`          (03-04) — URL fabrikasi (u yerda `rtsp` sxemasi
                                          KUTILGAN CHIQISH sifatida yoziladi);
  * `test_nvr_errors.py`        (03-05) — o'n ikki xato kodining ajratilishi;
  * `test_nvr_discovery.py`     (03-05) — kashfiyot mexanikasi va idempotentlik;
  * `test_nvr_discovery_job.py` (03-06) — fon vazifasi va tenant konteksti;
  * `test_nvr_api.py`           (03-06) — HTTP shartnomasi va huquq darvozasi;
  * `test_live_view.py`         (03-07) — jonli ko'rishning rad etish matritsasi;
  * `test_market_delete_guard.py` (03-01/03-03) — kaskad va WR-02.

Bu yerdagi savol boshqa va u faqat shu yerda beriladi: **ROADMAP'da yozilgan
jumla bugun rostmi?** Har test docstringi mezon matnini SO'ZMA-SO'Z olib
yuradi, ya'ni ROADMAP tahrirlanganda mos kelmaslik ko'zga tashlanadi.

NEGA BU KERAK: mezon qismlarga bo'linganda har bir qism yashil bo'lib,
BUTUN da'vo baribir yolg'on bo'lishi mumkin. Eng ehtimolli shakl — qismlar
ORASIDAGI uzilish: `test_nvr_discovery.py` kashfiyotni SEED qatori ustida
o'lchaydi (qurilma allaqachon bazada), `test_live_view.py` esa chiptani
SEED kamerasi ustida. Ikkalasi ham yashil bo'la turib, ADMIN QO'LI BILAN
yaratilgan qurilmadan tug'ilgan kamera uchun jonli ko'rish ishlamasligi
mumkin — chunki bu yo'l birorta testda BOSHIDAN OXIRIGACHA kesib
o'tilmagan. SC#7 aynan shu zanjirni talab qiladi.
=============================================================================

⚠ BU FAYLDA RTSP SXEMASINING LITERALI YO'Q VA BU MEZONNING BIR QISMI.

SC#1 ning eng qimmatli da'vosi — «qo'lda birorta RTSP URL yozilmaydi».
Uni faqat NATIJA bo'yicha tekshirish zaif bo'lardi: test URL'ni o'zi yozib,
keyin uni bazada topib «isbotlagan» bo'lardi. Shuning uchun bu yerda USUL
ham qulflanadi — test O'Z MANBA MATNINI o'qiydi va unda sxema literalining
YO'QLIGINI tasdiqlaydi (`test_sc1_...` ning oxirgi asserti).

Izlanadigan satr shu faylda YOZILMAYDI — u MAHSULOT KODINING chiqishidan
olinadi (`FORBIDDEN_SCHEME`, pastda). Ya'ni bu «obfuskatsiya» emas: naqsh
`app/services/rtsp.py::rtsp_url()` ning O'Z sxemasi bo'lib qoladi va
fabrikaning sxemasi o'zgarsa tekshiruv ham o'zi bilan ko'chadi.

⚠ CHEGARA ANIQ: taqiq FAQAT SHU FAYL ustida amal qiladi.
`tests/unit/test_rtsp_url.py` (03-04) da o'sha literal KUTILGAN CHIQISH
sifatida yoziladi va bu ziddiyat emas — u yerda o'lchanayotgan narsa
fabrikaning O'ZI, bu yerda esa fabrikaning admin qo'liga TEGMASLIGI.
=============================================================================

⚠ SC#5 NING UCHINCHI DA'VOSI (`ip route get <nvr_ip>` -> `wg0`) BU YERDA
QO'LDA DEB BELGILANGAN va test uni bajarishga URINMAYDI. Sabab
`03-VALIDATION.md` § «Manual-Only Verifications» da yozilgan: CI'da tunnel
umuman yo'q, ya'ni bunday test HAR DOIM «tunnel uzilgan» shoxidan o'tardi
va hech nimani isbotlamasdi (Pitfall 10). Uning egasi (Ops) va tetigi
(VPS deploy'idan keyin) o'sha jadvalda.
"""

from __future__ import annotations

import inspect
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import psycopg
import pytest
from app.jobs.discovery import discover_nvr
from app.security.ratelimit import NVR_TEST_LIMIT
from app.services.rtsp import rtsp_url
from fixtures.admin_api import session_headers
from fixtures.auth_api import audit_rows
from fixtures.nvr_domain import CLEANUP_ORDER, add_discovery_run, nvr_rows
from fixtures.nvr_sim import sim_mode, sim_patch
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.enums import AuditAction, CameraStatus
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fastapi import FastAPI
    from fixtures import TenantSessionFactory
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = [pytest.mark.sim, pytest.mark.usefixtures("migrated")]

NVR_URL = "/api/v1/nvr-devices"
CAMERAS_URL = "/api/v1/cameras"
AUTHZ_URL = "/internal/live-authz"

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "services" / "core-api" / "app"
MESSAGES_ROOT = REPO_ROOT / "frontend" / "messages"
WG_EXAMPLE = REPO_ROOT / "ops" / "wireguard" / "wg0.conf.example"
TUNNEL_SCRIPT = REPO_ROOT / "ops" / "scripts" / "verify-tunnel.sh"

LOCALES = ("uz-Latn", "uz-Cyrl", "ru")
"""Uchala katalog — SC#3 ning «ko'rsatiladi» qismi bir tilda yashay olmaydi."""

SIM_CHANNEL_COUNT = 6
"""`DS-7616NI-K2` fixture'i beradigan kanallar soni (D-09: CI'da 6, 25 emas)."""

FORBIDDEN_SCHEME = rtsp_url("nvr.invalid", 554, 1).split("//", maxsplit=1)[0] + "//"
"""Bu faylda UCHRAMASLIGI kerak bo'lgan satr — MAHSULOT chiqishidan olingan.

`rtsp_url()` ning o'zi `<sxema>://<host>:<port>/...` beradi, ya'ni bu
ifoda fabrikaning SXEMASINI qaytaradi. Literal shu faylda yozilmagani
uchun `test_sc1_...` ning oxirgi asserti o'z-o'zini yolg'on-yashil
qilmaydi va sxema o'zgarsa naqsh ham o'zi bilan ko'chadi.
"""

SIM_LEAK_NEEDLES = ("nvr-sim", "__sim__", "SIM_")
"""SC#7 ning «kod o'zgarishi emas» yarmi — ilova kodida sim izi BO'LMAYDI.

`test_no_sim_branching.py` (03-02) buni o'z darvozasi sifatida o'lchaydi;
bu yerda u MEZON darajasida qayta tasdiqlanadi, chunki SC#7 ning ikkinchi
yarmi («real qurilmaga o'tish — sozlama o'zgarishi») aynan shu faktga
tayanadi.
"""


# ---------------------------------------------------------------------------
# Zanjir yordamchilari
# ---------------------------------------------------------------------------


@pytest.fixture
def nvr_cleanup(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
) -> Iterator[None]:
    """API orqali YARATILGAN NVR qatorlarini o'chiradi.

    ⚠ USIZ `cleanup_two_markets()` YIQILADI: u `DELETE FROM markets` bilan
      tugaydi, `nvr_devices` esa `markets` ga chet el kaliti bilan tayanadi.
      Ya'ni bu fixture qulaylik emas — usiz butun fayl birinchi testdan
      keyin bazani buzilgan holatda qoldirardi.

    Tozalash `fixtures.nvr_domain.CLEANUP_ORDER` bilan: tartib SHU YERDA
    QAYTA YOZILMAYDI, aks holda yangi jadval qo'shilganda ikki ro'yxat
    jimgina ajralib ketardi.
    """
    try:
        yield
    finally:
        market_ids = [str(market.id) for market in two_markets.markets]
        for table in CLEANUP_ORDER:
            # Jadval nomlari sobit ro'yxatdan keladi — tashqi kirish emas
            # (`fixtures/nvr_domain.py::cleanup_nvr_domain` bilan bir xil naqsh).
            sync_owner_conn.execute(
                f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
                (market_ids,),
            )


@pytest.fixture
def enqueued(api_app: FastAPI) -> Iterator[list[dict[str, Any]]]:
    """Navbatga qo'yishni YOZIB OLADI — job javobdan KEYIN chaqiriladi.

    ⚠ JOB SO'ROV ICHIDA BAJARILMAYDI VA BU ATAYIN. `POST /discover`
      `queued` qatorini o'z tranzaksiyasida yozadi va u javob
      qaytarilgandagina COMMIT bo'ladi. Jobni so'rov ichida chaqirish
      boshqa ulanishdan hali ko'rinmaydigan qatorni o'qishga urinardi —
      ya'ni test HAQIQIY navbat semantikasidan (worker xabarni commitdan
      keyin oladi) chetga chiqib, o'zi yaratgan poygani o'lchagan bo'lardi.

    ⚠ TOZALASH MAJBURIY: `api_app` — modul darajasidagi YAGONA obyekt,
      qoldirilgan atribut boshqa test modullariga sizib o'tardi (03-06
      Issue 2).
    """
    calls: list[dict[str, Any]] = []

    async def _record(**kwargs: Any) -> None:
        calls.append(kwargs)

    api_app.state.enqueue_discovery = _record
    try:
        yield calls
    finally:
        del api_app.state.enqueue_discovery


@pytest.fixture
def go2rtc_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """`Go2rtcClient` ni YOZIB OLUVCHI soxta bilan almashtiradi.

    ⚠ NEGA MOCK: bu fayl AVTORIZATSIYA zanjirini o'lchaydi, media
      serverining ishlashini emas. Haqiqiy klient `settings.go2rtc_url` ga
      boradi va test muhitida u yerda hech kim yo'q — har chaqiruv 5
      soniya kutib 503 berardi, ya'ni SC#6 va SC#7 zanjiri media
      serverining mavjudligiga bog'lanib qolardi.

    ⚠ NUSXA `test_live_view.py` DAN IMPORT QILINMAYDI: test moduli boshqa
      test modulining fixture'ini import qilishi ikki fayl orasida yashirin
      bog'liqlik hosil qilardi va o'sha fayl qayta tashkil qilinganda bu
      fayl sababsiz qizarardi. Takrorlanish ~15 qator va u ATAYIN.
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
            calls.append((stream_name, src))
            return True

    monkeypatch.setattr("app.api.v1.cameras.Go2rtcClient", _RecordingClient)
    return calls


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`CAMERA_MANAGE` + `CAMERA_VIEW`)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def director_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori DIREKTORI — `CAMERA_VIEW` bor, `CAMERA_MANAGE` yo'q (D-07)."""
    return await session_headers(api_client, two_markets.market_a.director_phone, SEED_PASSWORD)


async def _create_device(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    address: str,
    credentials: tuple[str, str],
) -> dict[str, Any]:
    """«Forma» — ADMIN YUBORADIGAN YAGONA UCH MAYDON.

    Tana shu yerda quriladi va uning kalitlari testda ALOHIDA assert bilan
    tekshiriladi: SC#1 «faqat manzil + login/parol» deydi, ya'ni to'rtinchi
    maydonning paydo bo'lishi mezonning buzilishi bo'lardi.
    """
    username, password = credentials
    payload = {"address": address, "username": username, "password": password}
    assert set(payload) == {"address", "username", "password"}, (
        f"forma tanasida ortiqcha maydon bor: {sorted(payload)} — SC#1 «FAQAT "
        "NVR manzili + login/parol» deydi"
    )
    response = await client.post(NVR_URL, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def _discover(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    nvr_id: UUID,
    enqueued_calls: list[dict[str, Any]],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> dict[str, Any]:
    """202 -> (worker) -> poll — MAHSULOT ZANJIRINING O'ZI.

    Uch bo'g'in ham bu yerda: HTTP tugmasi, fon vazifasi va poll javobi.
    Ularni ajratib olish (masalan `discover_nvr` ni to'g'ridan-to'g'ri
    chaqirish) `run_id` ning API'dan jobga UZATILISHINI sinovdan chiqarib
    yuborardi — aynan zanjirning eng nozik bo'g'ini.
    """
    started = await client.post(f"{NVR_URL}/{nvr_id}/discover", headers=headers)
    assert started.status_code == 202, started.text
    run_id = UUID(started.json()["run_id"])

    assert len(enqueued_calls) == 1, f"navbatga aynan bitta xabar kutilgan edi: {enqueued_calls}"
    message = enqueued_calls.pop()
    assert message["run_id"] == run_id, (
        f"navbatdagi `run_id` ({message['run_id']}) javobdagidan ({run_id}) FARQ QILADI — "
        "poll qiladigan mijoz boshqa yugurishni kuzatardi"
    )
    await discover_nvr(sessionmaker, **message)

    polled = await client.get(f"{NVR_URL}/{nvr_id}/discovery-runs/{run_id}", headers=headers)
    assert polled.status_code == 200, polled.text
    run: dict[str, Any] = polled.json()
    return run


async def _cameras(
    client: httpx.AsyncClient, headers: dict[str, str], nvr_id: UUID
) -> list[dict[str, Any]]:
    response = await client.get(CAMERAS_URL, params={"nvr_id": str(nvr_id)}, headers=headers)
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


async def _device(
    client: httpx.AsyncClient, headers: dict[str, str], nvr_id: UUID
) -> dict[str, Any]:
    response = await client.get(NVR_URL, headers=headers)
    assert response.status_code == 200, response.text
    for item in response.json()["items"]:
        if item["id"] == str(nvr_id):
            entry: dict[str, Any] = item
            return entry
    raise AssertionError(f"{nvr_id} ro'yxatda yo'q: {response.text}")


async def _audit_blobs(
    tenant_session: TenantSessionFactory, market_id: UUID
) -> list[tuple[str, str]]:
    """Bozorning HAR audit qatori -> `(jadval, JSON matni)`.

    ⚠ `fixtures.auth_api.audit_rows()` ISHLATILMAYDI: u `old_value` ni
      TANLAMAYDI (ustunlar ro'yxati sobit). SC#4 esa aynan «eski -> yangi»
      juftligining IKKALA tomonini ham tekshirishi kerak — parol
      almashtirilganda eski qiymat `old_value` ga tushishi eng ehtimolli
      sizish shakli bo'lardi.

    O'qish ILOVA roli va tenant konteksti bilan (audit ekrani aynan shu
    yo'ldan ma'lumot oladi) — superuser bilan emas.
    """
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT table_name, action, changed_keys, old_value, new_value "
                "FROM audit_log WHERE market_id = :market_id ORDER BY id"
            ),
            {"market_id": str(market_id)},
        )
        return [
            (
                row.table_name,
                json.dumps(
                    {
                        "action": row.action,
                        "changed_keys": row.changed_keys,
                        "old": row.old_value,
                        "new": row.new_value,
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            )
            for row in result
        ]


def _read(path: Path) -> str:
    """Fayl matni — SINXRON yordamchi.

    ⚠ ATAYIN ALOHIDA FUNKSIYA: `ruff` ning `ASYNC240` qoidasi `async def`
      ichidagi `pathlib` chaqiruvini bloklaydi (event loop'ni bloklaydi
      degan asosda). Bu yerda o'qilayotgan narsa — repozitoriyning O'Z
      fayllari (bir necha kilobayt, lokal disk), ya'ni qoida amalda
      qo'llanmaydi; lekin uni `noqa` bilan o'chirish har chaqiruvda
      takrorlanardi. Yagona sinxron yordamchi ikkalasini ham hal qiladi.
    """
    return path.read_text(encoding="utf-8")


def _catalog(locale: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(_read(MESSAGES_ROOT / f"{locale}.json"))
    return data


def _app_sources() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def _sim_leaks() -> list[str]:
    """Ilova kodidagi simulyator izlari — `(fayl, naqsh)` juftliklari."""
    sources = _app_sources()
    assert sources, f"{APP_ROOT} da birorta `.py` topilmadi — skaner bo'sh ishladi"
    found: list[str] = []
    for path in sources:
        text = _read(path)
        relative = path.relative_to(REPO_ROOT)
        found.extend(f"{relative}: {needle}" for needle in SIM_LEAK_NEEDLES if needle in text)
    return found


# ===========================================================================
# SC#1
# ===========================================================================


async def test_sc1_admin_enters_only_the_address_and_credentials(
    sim: str,
    sim_credentials: tuple[str, str],
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    enqueued: list[dict[str, Any]],
    api_sessionmaker: async_sessionmaker[AsyncSession],
    nvr_cleanup: None,
) -> None:
    """SC#1 — «Bozor admini **faqat** NVR manzili + login/parolni kiritadi va
    "kameralarni topish" tugmasini bosadi; tizim ISAPI orqali qurilma modelini
    aniqlaydi, barcha kanallarni sanaydi va har biri uchun kamera yozuvini
    (nom, kanal raqami, asosiy/sub oqim URL'i) **avtomat** yaratadi — qo'lda
    birorta RTSP URL yozilmaydi».

    MEZON TO'RT NARSANI SANAYDI VA TO'RTALASI HAM ALOHIDA O'LCHANADI:

      1. **kirish yuzasi uchta maydon** — `_create_device()` tanani o'zi
         quradi va kalitlar to'plamini tekshiradi;
      2. **model aniqlanadi** — qurilma pasportidagi `model`/`device_type`
         forma tanasida YO'Q edi, ya'ni ular ISAPI'dan keldi;
      3. **barcha kanallar sanaladi va har biriga yozuv tug'iladi** —
         `channels_found == channels_added == 6` va reestrda 6 qator;
      4. **URL avtomat quriladi** — RTSP porti KASHF ETILDI
         (`rtsp_port_assumed is False`) va manba satri BAZADAGI qiymatlardan
         fabrika bilan quriladi.

    OXIRGI ASSERT USULNI QULFLAYDI: bu fayl o'z manba matnida RTSP
    sxemasining literalini SAQLAMAYDI. Usiz «qo'lda URL yozilmaydi» da'vosi
    natija bo'yicha yashil bo'lib, testning o'zi URL yozib turgan holatda
    ham o'tib ketardi (fayl boshidagi izoh).
    """
    created = await _create_device(api_client, admin_headers, sim, sim_credentials)
    nvr_id = UUID(created["id"])

    # --- 2-da'vo: model FORMA TANASIDA YO'Q edi ---
    assert created["model"] is None, (
        "qurilma pasporti model bilan tug'ildi — u forma tanasida yo'q edi, "
        "ya'ni kimdir uni taxmin qilib yozgan"
    )

    run = await _discover(api_client, admin_headers, nvr_id, enqueued, api_sessionmaker)
    assert run["status"] == "succeeded", run
    assert run["error_code"] is None, run

    # --- 3-da'vo: barcha kanallar ---
    assert run["channels_found"] == SIM_CHANNEL_COUNT, run
    assert run["channels_added"] == SIM_CHANNEL_COUNT, (
        f"qurilma yangi edi, ya'ni topilgan {SIM_CHANNEL_COUNT} kanalning HAMMASI "
        f"qo'shilishi kerak: {run}"
    )

    cameras = await _cameras(api_client, admin_headers, nvr_id)
    assert [row["channel_no"] for row in cameras] == list(range(1, SIM_CHANNEL_COUNT + 1))
    assert all(row["name"] for row in cameras), (
        f"nomsiz kamera yozuvi bor — mezon «nom» ni ochiq sanaydi: {cameras}"
    )
    assert all(row["name_overridden"] is False for row in cameras), (
        "yangi yozuv `name_overridden=true` bilan tug'ildi — NVR nomi bosib o'tilgan"
    )

    # --- 2-da'vo (davomi): model va seriya ISAPI'dan keldi ---
    device = await _device(api_client, admin_headers, nvr_id)
    assert device["model"] == "DS-7616NI-K2", device
    assert device["device_type"] == "NVR", device
    assert device["serial_number"], device
    assert device["last_discovery_at"] is not None, device

    # --- 4-da'vo: RTSP porti KASHF ETILDI, taxmin QILINMADI ---
    assert device["rtsp_port"] == 554, device
    assert device["rtsp_port_assumed"] is False, (
        "RTSP porti taxmin qilindi — «avtomat» da'vosi zaxira qiymat ustida yashil bo'lardi"
    )

    # --- 4-da'vo (davomi): manba satri BAZADAN quriladi, testdan emas ---
    source = rtsp_url(
        device["host"],
        device["rtsp_port"],
        cameras[0]["channel_no"],
        substream=cameras[0]["has_substream"],
    )
    assert source.startswith(FORBIDDEN_SCHEME), source
    assert device["host"] in source, source

    # --- USUL: bu faylda RTSP literali YO'Q ---
    own_source = _read(Path(__file__))
    assert FORBIDDEN_SCHEME not in own_source, (
        "bu faylda RTSP sxemasining literali paydo bo'ldi — «qo'lda birorta RTSP "
        "URL yozilmaydi» da'vosi endi testning O'ZI yozgan satr ustida yashil bo'ladi"
    )


# ===========================================================================
# SC#2
# ===========================================================================


async def test_sc2_rescan_is_idempotent(
    sim: str,
    sim_credentials: tuple[str, str],
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    enqueued: list[dict[str, Any]],
    api_sessionmaker: async_sessionmaker[AsyncSession],
    nvr_cleanup: None,
) -> None:
    """SC#2 — «Qayta skanerlash idempotent: yangi kanal qo'shiladi, yo'qolgani
    `offline` deb belgilanadi, mavjudi tegilmaydi — takroriy kamera yozuvi
    yaratilmaydi».

    UCH QOIDA VA ULAR BIR SESSIYADA, KETMA-KET O'LCHANADI:

      * **ikkinchi skan 0 qo'shadi** va qator `id` lari o'zgarmaydi —
        «takroriy yozuv yaratilmaydi» ning yagona kuchli shakli
        (`channels_added == 0` yolg'iz o'zi qatorlarni o'chirib qayta
        yaratgan kodni ham o'tkazib yuborardi);
      * **yo'qolgan kanal `offline`** bo'ladi va QATOR SONI KAMAYMAYDI;
      * **admin qo'ygan nom saqlanadi** — bu yerda nom MAHSULOT YO'LIDAN
        (`PATCH /cameras/{id}`) qo'yiladi, seed'dan emas.

    ⚠ NOM O'ZGARTIRISH KANALI ATAYIN 1: yo'qoladigan kanal (5) bilan
      to'qnashmaydi, ya'ni ikki qoida bir-birining natijasini niqoblamaydi.
    """
    created = await _create_device(api_client, admin_headers, sim, sim_credentials)
    nvr_id = UUID(created["id"])

    first = await _discover(api_client, admin_headers, nvr_id, enqueued, api_sessionmaker)
    assert first["channels_added"] == SIM_CHANNEL_COUNT, first
    before = {row["channel_no"]: row for row in await _cameras(api_client, admin_headers, nvr_id)}

    # --- Admin nomni O'ZGARTIRADI (mahsulot yo'li) ---
    renamed = await api_client.patch(
        f"{CAMERAS_URL}/{before[1]['id']}",
        json={"name": "Sabzavot qatori"},
        headers=admin_headers,
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name_overridden"] is True

    # --- Ikkinchi skan: HECH NIMA O'ZGARMAYDI ---
    second = await _discover(api_client, admin_headers, nvr_id, enqueued, api_sessionmaker)
    assert second["channels_added"] == 0, f"ikkinchi skan yangi kamera qo'shdi: {second}"
    assert second["channels_found"] == SIM_CHANNEL_COUNT, second

    middle = {row["channel_no"]: row for row in await _cameras(api_client, admin_headers, nvr_id)}
    assert len(middle) == len(before), "qator soni o'zgardi — takroriy yoki yo'qolgan yozuv"
    for channel_no, row in before.items():
        assert middle[channel_no]["id"] == row["id"], f"kanal {channel_no}: `id` o'zgardi"

    # --- Uchinchi skan: 5-kanal NVR'dan yo'qoldi ---
    sim_patch(sim, mode="channel_removed", removed_channels=[5])
    third = await _discover(api_client, admin_headers, nvr_id, enqueued, api_sessionmaker)
    assert third["channels_found"] == SIM_CHANNEL_COUNT - 1, third
    assert third["channels_marked_offline"] == 1, third

    after = {row["channel_no"]: row for row in await _cameras(api_client, admin_headers, nvr_id)}
    assert len(after) == len(before), (
        f"qator soni {len(before)} -> {len(after)} ga kamaydi — kamera O'CHIRILDI, "
        "holbuki 4- va 5-fazalar `cameras.id` ga tayanadi"
    )
    assert after[5]["status"] == CameraStatus.OFFLINE.value, after[5]
    assert after[5]["id"] == before[5]["id"], "qator o'chirilib qayta yaratilgan"

    # --- Admin qarori IKKI SKANDAN keyin ham joyida ---
    assert after[1]["name"] == "Sabzavot qatori", (
        f"qayta skan admin qo'ygan nomni bosib ketdi: {after[1]}"
    )
    assert after[1]["name_overridden"] is True, after[1]
    # NAZORAT: bayroqsiz kanal NVR nomini OLADI va u admin nomidan FARQ QILADI.
    assert after[2]["name"] != after[1]["name"], after


# ===========================================================================
# SC#3
# ===========================================================================


async def test_sc3_failure_names_the_cause_and_the_fix(
    sim: str,
    sim_credentials: tuple[str, str],
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """SC#3 — «Ulanish muvaffaqiyatsiz bo'lsa, xato **sababi va tuzatish yo'li**
    ko'rsatiladi (parol xato / NVR soati >5 daq farq qilyapti → NTP / firmware
    `digest/basic` talab qiladi / kanal offline / bir vaqtdagi sessiya limitiga
    yetildi) — "ulanmadi" degan quruq xabar qabul qilinmaydi».

    MEZON IKKI TOMONGA TEGISHLI VA IKKALASI HAM SHU YERDA O'LCHANADI:

      * **backend** sababni KOD bilan qaytaradi (`error_code`), «ulanmadi»
        degan bo'sh bayroq bilan emas;
      * **frontend** o'sha kod uchun SABAB va TUZATISH matnini UCHALA
        katalogda saqlaydi (`cameras.errorCause.*` + `cameras.errorFix.*`).

    Birinchisi yolg'iz o'zi yetarli emas: nomlanmagan kod ekranda «xato
    yuz berdi» bo'lib chiqardi, ya'ni mezon buzilgan holicha qolardi.
    Ikkinchisi ham yolg'iz yetarli emas: hech qachon kelmaydigan kod uchun
    saqlangan matn hech nimani ko'rsatmaydi.

    ⚠ UCHTA REJIM `NVR_TEST_LIMIT` GA SIG'ADI va bu ALOHIDA assert bilan
      qulflangan: chegara pasaytirilsa test «rate-limit» sababidan
      qizarardi va sabab mezonda emas, sozlamada bo'lardi.

    ⚠ HAR REJIM `drift_seconds` NI ANIQ QO'YADI. `POST /__sim__/state` —
      QISMAN yangilash (03-02): berilmagan maydon TEGILMAYDI. Ya'ni
      `clock_drift` dan keyingi `basic_only` rejimida 420 soniyalik farq
      SAQLANIB qolardi va diagnostika (soat farqi autentifikatsiyadan
      OLDIN tekshiriladi — 03-05) `nvr_clock_drift` ni qaytarardi. O'lchandi:
      aynan shu holat birinchi yugurishda YUZ BERDI va test uni ushladi.
    """
    cases = (
        ("bad_password", 0, "nvr_bad_credentials"),
        ("clock_drift", 420, "nvr_clock_drift"),
        ("basic_only", 0, "nvr_auth_mode_basic_only"),
    )
    assert len(cases) <= NVR_TEST_LIMIT, (
        f"«ulanishni tekshirish» chegarasi {NVR_TEST_LIMIT} — {len(cases)} ta rejim "
        "sig'maydi va test rate-limit sababidan qizarardi"
    )

    username, password = sim_credentials
    catalogs = {locale: _catalog(locale) for locale in LOCALES}
    seen: dict[str, str] = {}

    for mode, drift, expected in cases:
        sim_mode(sim, mode, drift_seconds=drift)
        response = await api_client.post(
            f"{NVR_URL}/test-connection",
            json={"address": sim, "username": username, "password": password},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ok"] is False, f"rejim {mode!r} da ulanish MUVAFFAQIYATLI bo'ldi: {body}"
        assert body["error_code"] == expected, (
            f"rejim {mode!r} -> {body['error_code']!r}, kutilgani {expected!r}"
        )
        seen[mode] = body["error_code"]

        # --- FRONTEND TOMONI: sabab VA tuzatish, uchala tilda ---
        for locale, catalog in catalogs.items():
            cameras = catalog["cameras"]
            cause = cameras["errorCause"].get(expected)
            fix = cameras["errorFix"].get(expected)
            assert isinstance(cause, str) and cause.strip(), (
                f"{locale}: `cameras.errorCause.{expected}` yo'q yoki bo'sh — "
                "ekranda «ulanmadi» degan quruq xabar qolardi"
            )
            assert isinstance(fix, str) and fix.strip(), (
                f"{locale}: `cameras.errorFix.{expected}` yo'q yoki bo'sh — "
                "sabab aytilib, tuzatish yo'li aytilmasdi"
            )

    assert len(set(seen.values())) == len(cases), (
        f"uch rejim bir xil kodga yig'ildi: {seen} — sabab AJRATILMAGAN"
    )
    # `bad_password` autentifikatsiya urinishini oshiradi, ya'ni «Qayta
    # urinish» affordansi BO'LMASLIGI kerak (UI-SPEC §4.4 backend tomoni).
    sim_mode(sim, "ok")


# ===========================================================================
# SC#4
# ===========================================================================


async def test_sc4_password_never_leaves_the_cipher(
    sim: str,
    sim_credentials: tuple[str, str],
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    enqueued: list[dict[str, Any]],
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
    nvr_cleanup: None,
) -> None:
    """SC#4 — «RTSP login/parollari bazada Fernet bilan shifrlangan saqlanadi —
    bazaga kirgan odam ham ochiq matn parol ko'rmaydi; parol hech qachon API
    javobida yoki jurnalda ko'rinmaydi».

    UCH JOY, UCHALASI HAM MUSTAQIL SIZISH YO'LI:

      1. **baza** — `nvr_credentials.password_encrypted` XOM BAYTLARI
         o'qiladi (ORM emas: model qiymatni deshifrlab berishi mumkin);
      2. **API javobi** — NVR yo'lidagi HAR javobning XOM TANASI;
      3. **audit jurnali** — bozorning BARCHA qatorlari, `old_value` va
         `new_value` birga.

    ⚠ AUDITDA SHIFRLANGAN QIYMAT HAM QIDIRILADI. «Ochiq matn yo'q» yolg'iz
      o'zi yetarli emas: shifrlangan token jurnalga tushib qolsa, kalit
      buzilgan kunda jurnal TARIXIY parollarni ochib berardi (T-03-13).
    """
    market_a = two_markets.market_a
    username, _ = sim_credentials
    secret = f"ParolFaqatShuTestda-{uuid4().hex}"  # noqa: S105 - test uskunasi

    created = await _create_device(api_client, admin_headers, sim, (username, secret))
    nvr_id = UUID(created["id"])

    # --- 1. BAZA: xom bayt ---
    row = sync_owner_conn.execute(
        "SELECT password_encrypted FROM nvr_credentials WHERE market_id = %s AND nvr_id = %s",
        (str(market_a.id), str(nvr_id)),
    ).fetchone()
    assert row is not None, "rekvizit qatori yozilmadi"
    stored: bytes = bytes(row[0])
    assert secret.encode() not in stored, "parol bazada OCHIQ MATN holida yotibdi"
    assert stored, "shifrlangan qiymat bo'sh"

    # --- 2. API: har javobning XOM tanasi ---
    #     Rekvizit bilan ishlaydigan MARSHRUTLAR ro'yxati — javob modeliga
    #     emas, XOM MATNGA qaraladi (`exclude=True` bilan yashirilgan maydon
    #     ham serializatsiyada qaytib chiqishi mumkin edi).
    listing = await api_client.get(NVR_URL, headers=admin_headers)
    assert listing.status_code == 200, listing.text
    raw_bodies = [json.dumps(created, ensure_ascii=False), listing.text]

    # ⚠ KASHFIYOT ATAYIN YIQILADI: parol sim'niki EMAS, ya'ni ISAPI `401`
    #   beradi va yugurish qatoriga `error_detail` yoziladi. Aynan shu —
    #   parolning sizib ketishi uchun eng qulay joy (03-05 uni allowlist
    #   ostiga oldi), shuning uchun MUVAFFAQIYATLI yo'l emas, XATO yo'li
    #   o'lchanadi.
    run = await _discover(api_client, admin_headers, nvr_id, enqueued, api_sessionmaker)
    assert run["status"] == "failed", (
        f"soxta parol bilan kashfiyot MUVAFFAQIYATLI bo'ldi: {run} — bu holda "
        "`error_detail` umuman yozilmasdi va sizish yo'li o'lchanmasdi"
    )
    assert run["error_code"] == "nvr_bad_credentials", run
    raw_bodies.append(json.dumps(run, ensure_ascii=False))

    cameras = await api_client.get(
        CAMERAS_URL, params={"nvr_id": str(nvr_id)}, headers=admin_headers
    )
    raw_bodies.append(cameras.text)

    for raw in raw_bodies:
        assert secret not in raw, f"parol API javobida ko'rindi: {raw[:200]}"
        assert stored.hex() not in raw, "shifrlangan qiymat API javobida ko'rindi"

    # --- 3. AUDIT: bozorning BARCHA qatorlari, `old` va `new` birga ---
    audited = await _audit_blobs(tenant_session, market_a.id)
    assert audited, "audit jurnali bo'sh — «jurnalda ko'rinmaydi» da'vosi o'lchanmasdi"

    encoded = stored.decode("utf-8", errors="ignore")
    for table_name, blob in audited:
        assert secret not in blob, f"parol audit jurnalida: {table_name}"
        assert not (encoded and encoded in blob), (
            f"SHIFRLANGAN parol audit jurnalida: {table_name} — kalit buzilgan "
            "kunda jurnal tarixiy parollarni ochib berardi (T-03-13)"
        )


# ===========================================================================
# SC#5
# ===========================================================================


async def test_sc5_the_nvr_is_reachable_only_through_the_tunnel(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """SC#5 — «Server NVR'ga faqat WireGuard tunnel orqali kiradi; tunnel
    o'chirilsa ulanish uziladi va NVR internetdan to'g'ridan-to'g'ri ochiq emas».

    IKKI DA'VO AVTOMATLASHTIRILGAN, UCHINCHISI QO'LDA:

      1. **ommaviy manzil RAD ETILADI** — marshrutlanadigan IP `host`
         sifatida qabul qilinmaydi, ya'ni «internetdan to'g'ridan-to'g'ri»
         yo'li mahsulotda umuman ochilmaydi (T-03-23);
      2. **tunnel TO'LIQ EMAS** — `wg0.conf.example` da butun-internet
         CIDR'i yo'q, ya'ni VPS ning butun chiqish trafigi bozorning DSL
         kanaliga tushmaydi;
      3. **`ip route get <nvr_ip>` -> `wg0`** — QO'LDA (fayl boshidagi
         izoh va `03-VALIDATION.md` § «Manual-Only Verifications»). Bu
         test uni BAJARMAYDI va bajarishga urinmaydi; o'rniga uni
         bajaradigan skriptning MAVJUDLIGI tekshiriladi.

    ⚠ UCHINCHI BANDNI CI'DA BAJARISHGA URINISH ZARARLI BO'LARDI: konteynerda
      `wg0` interfeysi umuman yo'q, ya'ni test har doim «tunnel uzilgan»
      shoxidan o'tib YASHIL bo'lardi va hech nimani isbotlamasdi
      (Pitfall 10).
    """
    # --- 1. Ommaviy IP rad etiladi ---
    rejected = await api_client.post(
        NVR_URL,
        json={"address": "8.8.8.8", "username": "sbozor", "password": "x" * 12},
        headers=admin_headers,
    )
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["detail"] == "nvr_host_public_blocked", rejected.text

    # --- 2. Tunnel SPLIT, to'liq emas ---
    assert WG_EXAMPLE.is_file(), f"{WG_EXAMPLE} yo'q"
    config = _read(WG_EXAMPLE)
    allowed = [line for line in config.splitlines() if line.strip().startswith("AllowedIPs")]
    assert allowed, "`wg0.conf.example` da birorta `AllowedIPs` qatori yo'q"
    full_tunnel = "0.0.0.0/" + "0"
    assert full_tunnel not in config, (
        "`wg0.conf.example` da BUTUN-INTERNET CIDR'i bor — VPS ning butun chiqish "
        "trafigi bozorning DSL kanaliga tushardi (Telegram, Let's Encrypt, "
        "foydalanuvchilar birga uzilardi)"
    )

    # --- 3. Uchinchi da'voning VOSITASI mavjud (bajarilishi QO'LDA) ---
    assert TUNNEL_SCRIPT.is_file(), f"{TUNNEL_SCRIPT} yo'q"
    first_line = _read(TUNNEL_SCRIPT).splitlines()[0]
    assert first_line.startswith("#!"), (
        f"`verify-tunnel.sh` shebang bilan boshlanmaydi ({first_line!r}) — u qo'lda "
        "ishga tushiriladigan skript sifatida e'lon qilinmagan"
    )
    assert os.access(TUNNEL_SCRIPT, os.X_OK), "`verify-tunnel.sh` bajariladigan emas"


# ===========================================================================
# SC#6
# ===========================================================================


async def test_sc6_live_view_requires_authorization(
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    two_markets: TwoMarketSeed,
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    go2rtc_calls: list[tuple[str, str]],
) -> None:
    """SC#6 — «Direktor avtorizatsiyadan keyin panelda jonli kamera tasvirini
    ko'radi; avtorizatsiyasiz to'g'ridan-to'g'ri havola ishlamaydi».

    UCH DA'VO, UCHALASI HAM MEZONNING BIR QISMI:

      1. **direktor chipta oladi** va bu hodisa AUDITDA `reason='live_view'`
         bilan qoladi — «ko'rdi» faktining yagona dalili;
      2. **chiptasiz havola ishlamaydi** — `/internal/live-authz` 403;
      3. **begona bozor uchun 404** — B bozori direktori A ning kamerasiga
         chipta so'raganda «topilmadi» oladi (mavjudlik ham sizmaydi).

    ⚠ SEED QATORI ATAYIN: bu test ZANJIRNI emas, AVTORIZATSIYANI o'lchaydi.
      Zanjirning o'zi (yaratilgan qurilmadan tug'ilgan kamera uchun chipta)
      SC#7 da kesib o'tiladi va ikkalasini bir testga yig'ish qaysi bo'g'in
      buzilganini ayta olmas holga keltirardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        market_a = seed.market_a
        camera_id = market_a.active_camera_ids[0]

        # --- 1. Direktor chipta oladi ---
        issued = await api_client.post(
            f"{CAMERAS_URL}/{camera_id}/live-token", headers=director_headers
        )
        assert issued.status_code == 200, issued.text
        body = issued.json()
        assert body["url"].startswith("/live/"), body
        assert "stream_name" not in body, body
        assert go2rtc_calls, "oqim go2rtc'da ro'yxatga olinmadi"

        reads = await audit_rows(tenant_session, market_a.market_id, action=str(AuditAction.READ))
        live_rows = [
            row
            for row in reads
            if row.table_name == "cameras" and (row.new_value or {}).get("reason") == "live_view"
        ]
        assert len(live_rows) == 1, (
            f"`reason='live_view'` qatori {len(live_rows)} ta — «direktor ko'rdi» "
            "faktining yagona dalili shu qator"
        )

        # --- 2. Chiptasiz havola ishlamaydi ---
        anonymous = await api_client.get(AUTHZ_URL, params={"src": "cam_anything"})
        assert anonymous.status_code == 403, anonymous.text

        # --- 3. Begona bozor uchun 404 ---
        foreign = await session_headers(
            api_client, two_markets.market_b.director_phone, SEED_PASSWORD
        )
        cross = await api_client.post(f"{CAMERAS_URL}/{camera_id}/live-token", headers=foreign)
        assert cross.status_code == 404, (
            f"begona bozor direktori {cross.status_code} oldi — 404 dan boshqa har qanday "
            "javob kameraning MAVJUDLIGINI oshkor qilardi"
        )


# ===========================================================================
# SC#7
# ===========================================================================


async def test_sc7_the_whole_flow_runs_against_a_simulator(
    sim: str,
    sim_credentials: tuple[str, str],
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    director_headers: dict[str, str],
    enqueued: list[dict[str, Any]],
    api_sessionmaker: async_sessionmaker[AsyncSession],
    go2rtc_calls: list[tuple[str, str]],
    nvr_cleanup: None,
) -> None:
    """SC#7 — «**Butun yuqoridagi oqim real uskunasiz, simulyatsiya qilingan
    Hikvision NVR ustida uchidan-uchiga ishlaydi va CI'da o'lchanadi** — real
    qurilmaga o'tish sozlama o'zgarishi bo'ladi, kod o'zgarishi emas».

    BU FAYLDAGI YAGONA TEST, U ZANJIRNING HAMMA BO'G'INIDAN BIR SESSIYADA
    O'TADI:

        forma -> saqlash -> kashfiyot jobi -> poll -> kameralar ro'yxati
        -> jonli ko'rish chiptasi

    Har bo'g'in alohida allaqachon o'lchangan (fayl boshidagi ro'yxat).
    Bu yerdagi savol boshqa: **oraliqdagi holat uzatiladimi?** Eng ehtimolli
    nosozlik shakli — admin qo'li bilan yaratilgan qurilmadan tug'ilgan
    kamera uchun jonli ko'rish yiqilishi (masalan `rtsp_port` NULL qolgani
    yoki `stream_name` yozilmagani sababli), va bu holat SEED qatori ustida
    ishlaydigan testlarning BIRORTASIDA ham ko'rinmasdi.

    IKKINCHI DA'VO — «kod o'zgarishi emas» — MEXANIK: ilova kodida
    simulyatorning izi (nomi, control-plane yo'li, muhit prefiksi)
    BO'LMASLIGI kerak. Aks holda «real qurilmaga o'tish» kodni tahrirlashni
    talab qilardi. `test_no_sim_branching.py` (03-02) buni o'z darvozasi
    sifatida o'lchaydi; bu yerda u MEZON darajasida qayta tasdiqlanadi.
    """
    # --- Zanjir: forma -> ... -> jonli ko'rish ---
    created = await _create_device(api_client, admin_headers, sim, sim_credentials)
    nvr_id = UUID(created["id"])

    run = await _discover(api_client, admin_headers, nvr_id, enqueued, api_sessionmaker)
    assert run["status"] == "succeeded", run

    cameras = await _cameras(api_client, admin_headers, nvr_id)
    assert len(cameras) == SIM_CHANNEL_COUNT, cameras

    # ⚠ CHIPTANI DIREKTOR SO'RAYDI, ADMIN EMAS: mezon aynan direktorni
    #   nomlaydi va `CAMERA_VIEW` `CAMERA_MANAGE` dan AJRATILGAN (D-07).
    issued = await api_client.post(
        f"{CAMERAS_URL}/{cameras[0]['id']}/live-token", headers=director_headers
    )
    assert issued.status_code == 200, issued.text
    assert issued.json()["url"].startswith("/live/"), issued.text

    # Oqim manbasi KASHF ETILGAN qiymatlardan qurildi — «sozlama o'zgarishi»
    # da'vosining bevosita o'lchovi: manzil ham, port ham bazadan keladi.
    assert len(go2rtc_calls) == 1, go2rtc_calls
    _stream_name, source = go2rtc_calls[0]
    assert source.startswith(FORBIDDEN_SCHEME), source
    assert created["host"] in source, (
        f"oqim manbasida admin kiritgan host yo'q: {source} — manzil qayerdandir "
        "BOSHQA joydan kelgan"
    )

    # --- «Kod o'zgarishi emas»: ilova kodida sim izi YO'Q ---
    leaks = _sim_leaks()
    assert leaks == [], (
        f"ilova kodida simulyatorning izi topildi: {leaks} — real qurilmaga o'tish "
        "KOD o'zgarishini talab qilardi va SC#7 buzilardi"
    )


# ===========================================================================
# SC#8
# ===========================================================================


def test_sc8_the_delete_guard_lives_in_the_schema(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    migrated: None,
) -> None:
    """SC#8 — «**WR-02 (2-fazadan eskalatsiya, YUQORI ustuvorlik):**
    `market_delete_draft()` o'n ikki jadval bo'ylab kaskad o'chiradi va uning
    yagona chegarasi ilova qatlamida — DB darajasida hech narsa uni
    to'xtatmaydi. Bu fazada u migratsiya bilan DB darajasida cheklanadi
    (qoralama bo'lmagan bozorni o'chirish imkonsiz bo'lishi test bilan
    isbotlanadi)».

    IKKI DA'VO VA ULAR TESKARI YO'NALISHDA:

      * **qoralama bozor to'rtala YANGI jadval bilan birga o'chadi** —
        kaskad `0012` qo'shgan jadvallarni ham qamraydi;
      * **faol bozorni o'chirish DB DARAJASIDA rad etiladi** — urinish
        ilova qatlamini BUTUNLAY chetlab o'tadi (`DELETE FROM markets`,
        `sbozor_owner` roli bilan) va baribir `23514` bilan tugaydi.

    ⚠ IKKINCHI DA'VO `market_delete_draft()` NI CHAQIRMAYDI. `0013` gacha
      kafolat faqat o'sha funksiyaning tanasidagi `IF` da yashardi va uni
      chetlab o'tish uchun funksiyani chaqirmaslik kifoya edi — ya'ni
      kafolat SXEMADA emas, ilova qatlamining odob-axloqida edi.

    ⚠ BU TEST `sim` KONTEYNERIGA TEGMAYDI (modul markeri ostida bo'lsa ham):
      SC#8 sxema haqidagi da'vo va uni simulyator bilan bog'lash sabab
      zanjirini uzun qilardi.
    """
    nvr_tables = tuple(CLEANUP_ORDER)

    with nvr_rows(sync_owner_conn, two_markets) as seed:
        a, b = seed.market_a, seed.market_b
        # Seed B ga ATAYIN yugurish yozmaydi — cross-tenant nazorati
        # to'rtala jadvalda ham qator talab qiladi.
        add_discovery_run(sync_owner_conn, b)

        for table in nvr_tables:
            assert _count(sync_owner_conn, table, a.market_id) > 0, (
                f"seed `{table}` ga A bozori uchun qator yozmagan — test o'chirishni "
                "emas, bo'sh jadvalni o'lchagan bo'lardi"
            )

        # --- 2-da'vo AVVAL: FAOL bozor DB darajasida himoyalangan ---
        with pytest.raises(psycopg.errors.CheckViolation):
            sync_owner_conn.execute("DELETE FROM markets WHERE id = %s", (str(a.market_id),))
        # `psycopg` tranzaksiyani abort holatida qoldiradi — keyingi
        # operatorlar uchun uni bo'shatish SHART.
        sync_owner_conn.rollback()

        # --- 1-da'vo: QORALAMA bozor to'rtala jadval bilan birga o'chadi ---
        sync_owner_conn.execute(
            "UPDATE markets SET is_active = false WHERE id = %s", (str(a.market_id),)
        )
        deleted = sync_owner_conn.execute(
            "SELECT market_delete_draft(%s)", (str(a.market_id),)
        ).fetchone()
        assert deleted is not None and bool(deleted[0]) is True

        for table in nvr_tables:
            remaining = _count(sync_owner_conn, table, a.market_id)
            assert remaining == 0, f"`{table}` da A bozorining {remaining} ta YETIM qatori qoldi"

        # NAZORAT: B bozori BUTUNLAY tegilmagan.
        for table in nvr_tables:
            assert _count(sync_owner_conn, table, b.market_id) > 0, (
                f"`{table}` da B bozorining qatorlari ham o'chdi — kaskad "
                "`WHERE market_id = ...` predikatini yo'qotgan bo'lishi mumkin"
            )


def _count(conn: Connection[TupleRow], table: str, market_id: UUID) -> int:
    row = conn.execute(
        f"SELECT count(*) FROM {table} WHERE market_id = %s",  # noqa: S608
        (str(market_id),),
    ).fetchone()
    assert row is not None
    return int(row[0])


# ===========================================================================
# META — mezonlardan birortasi JIMGINA tushib qolmasin
# ===========================================================================


def test_every_criterion_has_its_own_test() -> None:
    """Sakkizala mezon uchun AYNAN BITTA nomlangan test mavjud.

    USIZ MEZONLARDAN BIRI JIMGINA TUSHIB QOLARDI: fayl qayta tashkil
    qilinganda yoki test vaqtincha o'chirilganda darvoza baribir yashil
    bo'lardi va «sakkizala mezon o'lchanadi» da'vosi isbotsiz qolardi.

    ⚠ META-TESTNING O'Z NOMIDA `sc<raqam>` YO'Q va bu ataylab: qabul
      mezoni `--collect-only` chiqishida `sc[1-8]` naqshini SANAYDI, ya'ni
      meta-testning o'zi sanoqqa kirib ketmasligi kerak.
    """
    module = sys.modules[__name__]
    names = sorted(
        name
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    )

    for number in range(1, 9):
        owned = [name for name in names if name.startswith(f"test_sc{number}_")]
        assert len(owned) == 1, (
            f"SC#{number} uchun {len(owned)} ta test topildi ({owned}) — har mezonning "
            "egasi AYNAN BITTA nomlangan test bo'lishi kerak"
        )

    criteria = [name for name in names if name.startswith("test_sc")]
    assert len(criteria) == 8, f"mezon testlari soni 8 emas: {criteria}"
