"""Fazaning BESHTA muvaffaqiyat mezoni — ROADMAP matni bilan bog'langan YAGONA fayl.

=============================================================================
BU FAYL MAVJUD TESTLARNI TAKRORLAMAYDI — U ULARNI ZANJIR SIFATIDA BOG'LAYDI.

Har mezonning qismlari allaqachon qamralgan va ular o'z egasida qoladi:

  * `test_camera_zones_api.py`  (05-06) — versiyalash, qamrov, V5 geometriyasi;
  * `test_occupancy_immutable.py` (05-05) — `UPDATE`/`DELETE` qo'riqchilari;
  * `test_uncertain_queue.py`   (05-10) — qulflab olish, byudjet, ustuvorlik;
  * `test_blind_audit.py`       (05-11) — hosila urug', 70/30, ko'r serializer;
  * `test_aggregate_stall_slot.py` (05-12) — 120 holatli agregatsiya jadvali;
  * `test_day_close.py`         (05-12) — materializatsiya va `default_empty`;
  * `test_occupancy_report.py`  (05-12) — aniqlik hisoboti va `/occupancy` yuzasi.

Bu yerdagi savol boshqa va u faqat shu yerda beriladi: **ROADMAP'da yozilgan
jumla bugun rostmi?** Har test docstringi mezon matnini SO'ZMA-SO'Z olib
yuradi, ya'ni ROADMAP tahrirlanganda mos kelmaslik ko'zga tashlanadi.

=============================================================================
⛔⛔ CHOK QAYERDA — VA U DA'VO EMAS, CHEGARA.

SC#2 ning **arifmetik va idrok** qismi — xom ONNX tenzoridan
`sv.Detections` ga, undan zona verdiktiga — bu modulda O'LCHANMAYDI. U
`services/cv-service/tests/` da (`test_rfdetr_postprocess.py`,
`test_zone_verdict.py`, `test_detection_fixtures.py`) yashaydi va
`npm run gate` zanjiriga `npm run cv:test` bilan kiradi. Sabab mexanik:
`cv-service` — loyihaning IKKINCHI Python bog'liqlik to'plami (W0-2) va
uning kutubxonalari (`onnxruntime`, `supervision`, `opencv`) bu
konteynerda UMUMAN YO'Q.

Bu modul `sv.Detections` DAN KEYINGI hamma narsani o'lchaydi va u
HAQIQIY `postgres:18.4` da bo'ladi: zona geometriyasining saqlanishi va
versiyalanishi, hodisaning o'zgarmasligi, navbat oqimi, ko'r auditning
xolisligi, kameralararo agregatsiya va kun yopilishi.

=============================================================================
⛔⛔ BU FAZADA NIMA ISBOTLANMAYDI — VA U SHU YERDA OCHIQ YOZILADI (D-01).

  1. **DETEKTORNING ANIQLIGI.** «RF-DETR band/bo'sh qarorini qanchalik
     to'g'ri beradi» degan savolga bu faylda ham, butun to'plamda ham
     JAVOB YO'Q va bu kamchilik emas — HAQIQAT YO'Q: oltin to'plam
     (`tests/fixtures/golden_set/`) bo'sh, real Karmana kadri hali
     olinmagan. Darvoza QURILGAN va u UXLAB YOTADI (W0-9): `source=
     'karmana'` qatorlari paydo bo'lgan kuni u KODSIZ uyg'onadi.
     ⛔ Mexanika qatlamining yashilligi bilan aniqlik qatlamining
        yo'qligini yopish TAQIQLANADI. Sintetik verdiktlar MEXANIZMNI
        isbotlaydi, MODELNI emas.

  2. **REAL ONNX ARTEFAKTI.** `model` markerli bandlar bu modulda
     CHAQIRILMAYDI: CI'da `.onnx` fayli yo'q (W0-12 uni image'ga `COPY`
     bilan olib kiradi, yuklab OLMAYDI). Ya'ni «detektor haqiqiy
     og'irliklar bilan ishga tushadi» ham bu yerda o'lchanmaydi.

  3. **COCO SINFLARINING O'ZBEK BOZORI MOLLARIDA ISHLASHI.** Fazaning
     eng katta qoldiq xavfi va u faqat real kadrlarda ko'rinadi
     (`05-HUMAN-UAT.md` #2).

Uchalasi ham `05-HUMAN-UAT.md` da EGASI va TETIGI bilan yozilgan. Ular
fazani BLOKLAMAYDI (self-service direktivasi), lekin ularning natijasi
hech qayerda DA'VO QILINMAGAN.
=============================================================================

UCHTA DARVOZA VA UCHALASI HAM MUSTAQIL:

  1. **Mezon boshiga bitta test** — `test_sc1_`…`test_sc5_`, boshqasi yo'q.
  2. **Meta-test** — mezonlardan biri JIMGINA tushib qolmasin. Fayl qayta
     tashkil qilinganda yoki test vaqtincha o'chirilganda darvoza baribir
     yashil bo'lardi va «beshala mezon o'lchanadi» da'vosi ISBOTSIZ
     qolardi. Meta-testning O'Z nomida `sc<raqam>` YO'Q va bu ataylab.
  3. **Soxtalashtirishsiz o'lchov** — na detektor, na ombor, na baza
     almashtiriladi. Darvoza IKKI yo'ldan yuradi (`ast` daraxti VA
     `inspect.signature`), chunki soxtalashtirishning ikki shakli bor:
     kutubxona importi va fixture so'rovi. ⛔ «O'tkazib yuborish» yo'li
     ATAYIN YO'Q.
=============================================================================
"""

from __future__ import annotations

import ast
import inspect
import sys
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import psycopg
import pytest
from app.jobs.audit_draw import audit_draw
from app.jobs.day_close import day_close
from app.main import app as fastapi_app
from app.repositories.review_repo import ReviewRepository
from fixtures.admin_api import session_headers
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import (
    CONFIDENCE_0_45,
    CONFIDENCE_0_55,
    CONFIDENCE_0_59,
    SOURCE_HEIGHT,
    SOURCE_WIDTH,
    add_zone_with_event,
    occupancy_rows,
    square_polygon,
)
from fixtures.snapshot_domain import SEED_BUSINESS_DATE, snapshot_rows
from fixtures.two_markets import SEED_PASSWORD
from sbozor_core.enums import OccupancyVerdict, ResolutionSource, ReviewPurpose, ReviewQueueKind

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fastapi import FastAPI
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from fixtures.market_domain import MarketDomainSeed
    from fixtures.occupancy_domain import OccupancyDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_MODULE_PATH = Path(__file__)

ZONES_URL = "/api/v1/camera-zones"
REVIEW_URL = "/api/v1/review"
UNCERTAIN_NEXT_URL = "/api/v1/review/uncertain/next"
BLIND_NEXT_URL = "/api/v1/review/blind/next"
BUDGET_URL = "/api/v1/review/budget"
OCCUPANCY_URL = "/api/v1/occupancy"
ACCURACY_URL = "/api/v1/occupancy/accuracy"

_MOCK_ROOTS = frozenset(
    {
        "moto",
        "unittest",
        "mock",
        "respx",
        "aioresponses",
        "botocore",
        "pytest_mock",
        "responses",
    }
)
"""Bu modulda IMPORT QILINMAYDIGAN kutubxonalar — ro'yxat KODDA, matnda EMAS.

⚠ Docstringda sanalgan ro'yxat o'z izohida O'ZINI topib, darvozani hech
  qachon yashil qilmasdi (`test_phase4_criteria.py` da o'lchangan qaror).
"""

_MOCK_NAMES = frozenset({"AsyncMock", "MagicMock", "Mock", "patch", "mock_open", "seal"})
"""`from … import …` bilan olib kiriladigan soxtalashtirish VOSITALARI."""

_FAKE_FIXTURES = frozenset(
    {
        "monkeypatch",
        "mocker",
        "enqueued",
        "telegram_calls",
        "respx_mock",
        "httpx_mock",
        "go2rtc_mock",
    }
)
"""Test imzosida UCHRAMASLIGI shart bo'lgan fixture nomlari.

=============================================================================
⛔ NEGA IKKINCHI YO'L KERAK — VA U 05-11 DA O'LCHANGAN.

Import skani soxtalashtirishning FAQAT BIR shaklini ko'radi. Ikkinchisi —
`monkeypatch` yoki loyihaning O'Z spy fixture'i (`enqueued` broker'ni
almashtiradi) — birorta yangi import TALAB QILMAYDI, ya'ni `ast` daraxti
uni UMUMAN ko'rmasdi va darvoza jimgina yashil qolardi.

`enqueued` ATAYIN ro'yxatda: u «soxta kutubxona» emas, LOYIHANING O'Z
fixture'i — va aynan shuning uchun eng xavfli. Mezon moduli
`capture_tick -> detect` zanjirini o'lchayotgandek ko'rinib, aslida
broker'ga BORGAN so'rovlarni sanab turardi.
=============================================================================
"""


# ===========================================================================
# Muhit — besh qatlamli seed
# ===========================================================================


class Env:
    """Bir testga kerak bo'ladigan hamma narsa — bitta obyektda."""

    def __init__(
        self,
        base: TwoMarketSeed,
        domain: MarketDomainSeed,
        occupancy: OccupancyDomainSeed,
        auth: AuthSeed,
    ) -> None:
        self.base = base
        self.domain = domain
        self.occupancy = occupancy
        self.auth = auth

    @property
    def market_a(self) -> UUID:
        return self.base.market_a.id

    @property
    def camera_a(self) -> UUID:
        return self.occupancy.market_a.camera_id

    @property
    def second_camera(self) -> UUID:
        camera_id = self.occupancy.market_a.second_camera_id
        assert camera_id is not None, "nazorat: seed'da ikkinchi faol kamera yo'q"
        return camera_id

    @property
    def stalls_a(self) -> tuple[UUID, ...]:
        return self.domain.market_a.stall_ids

    @property
    def snapshot_a(self) -> UUID:
        return self.occupancy.market_a.snapshot_with_ok_quality


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    auth_seed: AuthSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """Besh qatlamli seed; tozalash TESKARI tartibda (FK zanjiri bo'yicha).

    ⚠ `auth_seed` `market_domain` DAN OLDIN so'raladi va bu ATAYIN
      (`test_uncertain_queue.py` / `test_blind_audit.py` dagi juftlari
      bilan bir xil sabab): pytest fixture'larni teskari tartibda
      yopadi, ya'ni nazoratchi foydalanuvchisi `zone_reviews`
      qatorlaridan KEYIN o'chiriladi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        yield Env(two_markets, market_domain, occupancy, auth_seed)


@pytest.fixture
async def admin_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Bozor adminining sessiyasi — `CAMERA_MANAGE` bor (SC#1 ning aktyori)."""
    return await session_headers(
        api_client, env.base.market_a.admin_phone, env.base.market_a.admin_password
    )


@pytest.fixture
async def inspector_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Nazoratchining sessiyasi — huquqi AYNAN `OCCUPANCY_REVIEW` (SC#3/SC#4)."""
    return await session_headers(api_client, env.auth.inspector.phone, SEED_PASSWORD)


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Direktor sessiyasi — `REPORT_VIEW` bor (SC#4/SC#5 hisoboti)."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


# ===========================================================================
# Yordamchilar
# ===========================================================================


def zone_body(
    stall_id: UUID,
    *,
    polygon: list[list[float]] | None = None,
    width: int = SOURCE_WIDTH,
    height: int = SOURCE_HEIGHT,
) -> dict[str, Any]:
    """`PUT /camera-zones` tanasining BITTA elementi — geometrik fakt bo'yicha."""
    return {
        "stall_id": str(stall_id),
        "polygon": polygon if polygon is not None else square_polygon(0.4, 0.4),
        "source_width": width,
        "source_height": height,
    }


async def put_zones(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    camera_id: UUID,
    zones: list[dict[str, Any]],
) -> httpx.Response:
    return await client.put(
        ZONES_URL, params={"camera_id": str(camera_id)}, json={"zones": zones}, headers=headers
    )


def clear_review_state(conn: Connection[TupleRow], market_id: UUID) -> None:
    """Navbat/tur qatorlarini olib tashlaydi — HODISALARGA TEGMASDAN.

    Seed kunni allaqachon «tortilgan» holatda beradi, `audit_draw` ning
    presharti esa buning teskarisi (`test_blind_audit.py` dagi jufti).
    `zone_reviews` uchun qoralama-bozor istisnosi ishlatiladi: javob
    SHARTSIZ o'zgarmas va yagona `DELETE` yo'li shu.
    """
    market = str(market_id)
    conn.execute("UPDATE markets SET is_active = false WHERE id = %s", (market,))
    conn.execute("DELETE FROM zone_reviews WHERE market_id = %s", (market,))
    conn.execute("UPDATE markets SET is_active = true WHERE id = %s", (market,))
    conn.execute("DELETE FROM review_assignments WHERE market_id = %s", (market,))
    conn.execute("DELETE FROM audit_rounds WHERE market_id = %s", (market,))


def slot_rows(conn: Connection[TupleRow], market_id: UUID, stall_id: UUID) -> list[tuple[str, str]]:
    """`(verdict, resolution_source)` — bitta rastaning kun bo'yicha slotlari."""
    rows = conn.execute(
        "SELECT verdict, resolution_source FROM stall_slot_occupancy "
        "WHERE market_id = %s AND stall_id = %s AND business_date = %s ORDER BY slot_time",
        (str(market_id), str(stall_id), SEED_BUSINESS_DATE),
    ).fetchall()
    return [(str(row[0]), str(row[1])) for row in rows]


def all_keys(payload: Any) -> set[str]:
    """JSON daraxtidagi BARCHA kalitlar — ichma-ich."""
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.add(str(key))
            found |= all_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            found |= all_keys(item)
    return found


@contextmanager
def budget_of(api_app: FastAPI, *, uncertain: int) -> Iterator[None]:
    """Kunlik byudjetni VAQTINCHA pasaytiradi — SOZLAMA yo'li bilan.

    ⚠ BU SOXTALASHTIRISH EMAS: byudjet mahsulotning O'Z sozlamasi
      (`Settings.review_uncertain_daily_budget`) va bu yerda AYNAN o'sha
      sozlama o'zgartiriladi. Muqobil — haqiqatan 50 ta javob yozish —
      testni sekin va mo'rt qilardi va byudjetning SOZLAMA ekanini
      umuman o'lchamasdi (`test_uncertain_queue.py::_budget_of` qarori).
    """
    original = api_app.state.settings
    api_app.state.settings = original.model_copy(
        update={"review_uncertain_daily_budget": uncertain}
    )
    try:
        yield
    finally:
        api_app.state.settings = original


async def accuracy(client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    """Aniqlik hisoboti — SEED KUNINI QAMRAYDIGAN davr bilan.

    ⚠ STANDART 30 KUNLIK OYNA ISHLAMAYDI: seed kuni (`SEED_BUSINESS_DATE`)
      bugundan uzoq bo'lishi mumkin, ya'ni oyna uni qamramay qolardi va
      test BO'SH hisobot ustida jimgina yashil bo'lardi
      (`test_occupancy_report.py` da o'lchangan qaror).
    """
    response = await client.get(
        ACCURACY_URL,
        headers=headers,
        params={
            "from": (SEED_BUSINESS_DATE - timedelta(days=1)).isoformat(),
            "to": (SEED_BUSINESS_DATE + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    payload: dict[str, Any] = response.json()
    return payload


# ===========================================================================
# SC#1
# ===========================================================================


async def test_sc1_polygons_are_normalized_versioned_and_multi_camera(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    admin_headers: dict[str, str],
    env: Env,
) -> None:
    """MEZON #1: «Bozor admini kamera kadrida rasta zonalarini poligon qilib
    chizadi va saqlaydi; koordinatalar normalangan (0..1), poligon
    versiyalangan, bitta rasta bir necha kameraga bog'lanadi».

    =======================================================================
    TO'RT DA'VO, TO'RTALASI HAM MAHSULOT YO'LIDAN (`PUT`/`GET`):

      1. SAQLANADI      — admin chizgan kontur qaytib keladi;
      2. NORMALANGAN    — javobdagi har koordinata 0..1 da VA chegaradan
                          tashqaridagi qiymat RAD ETILADI;
      3. VERSIYALANGAN  — tahrir YANGI qator yaratadi, eskisi JOYIDA
                          qoladi va `is_active = false` bo'ladi;
      4. IKKI KAMERADA  — bitta rasta ikkala kameraning ham FAOL zonasi
                          bo'lib turadi.

    ⚠ 2-DA'VONING IKKINCHI YARMI YUK KO'TARADI. «Javobdagi sonlar 0..1
      da» yolg'iz o'zi BO'SH da'vo bo'lardi: kim 0..1 da son yuborsa,
      o'sha qaytib keladi. Rad etish o'lchanmasa, normalanish
      KELISHUV bo'lib qolardi, DARVOZA emas — va piksel koordinatasi
      yuborgan birinchi klient uni jimgina buzardi.

    ⚠ 3-DA'VODAGI SON QO'LDA HISOBLANGAN: seed birinchi rastaga
      `version = 1` (eskirgan) va `version = 2` (faol) qatorlarini
      beradi, ya'ni tahrirdan keyin `version = 3` kutiladi.
    =======================================================================
    """
    stall = env.stalls_a[0]
    drawn = square_polygon(0.62, 0.31)

    saved = await put_zones(
        api_client, admin_headers, env.camera_a, [zone_body(stall, polygon=drawn)]
    )

    # (2b) Piksel koordinatasi — RAD ETILADI, jimgina qirqilmaydi.
    pixel = await put_zones(
        api_client,
        admin_headers,
        env.camera_a,
        [zone_body(stall, polygon=[[10.0, 10.0], [1900.0, 10.0], [1900.0, 1000.0]])],
    )

    # (4) O'sha rasta IKKINCHI kamerada ham.
    second = await put_zones(
        api_client,
        admin_headers,
        env.second_camera,
        [zone_body(stall, polygon=square_polygon(0.5, 0.5), width=640, height=480)],
    )

    first_list = await api_client.get(
        ZONES_URL, params={"camera_id": str(env.camera_a)}, headers=admin_headers
    )
    second_list = await api_client.get(
        ZONES_URL, params={"camera_id": str(env.second_camera)}, headers=admin_headers
    )

    assert saved.status_code == 200, saved.text
    assert second.status_code == 200, second.text
    assert first_list.status_code == 200, first_list.text
    assert second_list.status_code == 200, second_list.text

    # (1) Chizilgan kontur AYNAN qaytadi.
    stored = [item for item in first_list.json()["items"] if item["stall_id"] == str(stall)]
    assert len(stored) == 1, f"rasta {stall} uchun faol zona {len(stored)} ta: {stored}"
    assert [list(point) for point in stored[0]["polygon"]] == drawn, (
        "saqlangan kontur chizilganidan farq qiladi"
    )

    # (2a) Har koordinata 0..1 da — IKKALA kamerada ham.
    for payload in (first_list.json(), second_list.json()):
        for item in payload["items"]:
            for point in item["polygon"]:
                assert all(0.0 <= float(value) <= 1.0 for value in point), (
                    f"normalangan bo'lmagan koordinata: {point} (zona {item['id']})"
                )

    # (2b) Chegaradan tashqaridagi qiymat rad etildi.
    assert pixel.status_code == 422, (
        f"piksel koordinatasi qabul qilindi ({pixel.status_code}) — «normalangan» "
        "DARVOZA emas, KELISHUV bo'lib qolardi"
    )

    # (3) Versiyalash — eski qator JOYIDA.
    versions = sync_owner_conn.execute(
        "SELECT version, is_active FROM camera_zones "
        "WHERE camera_id = %s AND stall_id = %s ORDER BY version",
        (str(env.camera_a), str(stall)),
    ).fetchall()
    history = [(int(row[0]), bool(row[1])) for row in versions]
    assert history == [(1, False), (2, False), (3, True)], (
        f"versiya tarixi kutilganidan farq qiladi: {history}"
    )

    # (4) Bitta rasta — ikki kamerada, ikkalasi ham FAOL.
    cameras = sync_owner_conn.execute(
        "SELECT camera_id FROM camera_zones WHERE stall_id = %s AND is_active",
        (str(stall),),
    ).fetchall()
    assert {UUID(str(row[0])) for row in cameras} == {env.camera_a, env.second_camera}, (
        "rasta ikki kamerada bir vaqtda FAOL zonaga ega emas — AI-05 ning kirish "
        "holati umuman tug'ilmasdi"
    )


# ===========================================================================
# SC#2
# ===========================================================================


async def test_sc2_every_zone_gets_a_confidence_and_the_answer_is_immutable(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """MEZON #2: «Har kadrda har zona band/bo'sh/noaniq bahosini confidence
    bilan oladi; AI javobi hech qachon tahrirlanmaydi — nazoratchi qarori
    alohida yozuv sifatida ustiga qo'yiladi».

    =======================================================================
    ⚠⚠ CHOKNING BU TOMONI — VA U FAYL BOSHIDAGI CHEGARANING AMALIY SHAKLI.

    «Har KADRDA har ZONA baho oladi» jumlasining FAN-OUT qismi (bitta
    kadr -> N ta zona -> N ta hodisa) `jobs/detect.py` ning ishi va u
    `cv-tests` da o'lchanadi — bu yerda ONNX ham, ombor ham YO'Q.

    Bu yerda o'lchanadigan narsa — o'sha bahoning SAQLANISH KONTRAKTI va
    uning uch qismi mahsulot da'vosining O'ZI:

      1. UCHALA BAHO HAM IFODALANADI (`occupied`/`empty`/`uncertain`) va
         HAR BIRIDA `confidence` bor — `NULL` bilan yozib bo'lmaydi;
      2. YOZILGAN JAVOB TAHRIRLANMAYDI — `UPDATE` baza darajasida rad
         etiladi (ilova qatlamida emas: ilova chetlab o'tilishi mumkin);
      3. NAZORATCHI QARORI USTIGA QO'YILADI, LEKIN BOSHQA QATORDA —
         `zone_reviews` da yangi qator paydo bo'ladi va `occupancy_events`
         qatori BAYT-BAYT o'zgarmaydi.

    ⚠ 2-DA'VO XOM `psycopg` BILAN O'LCHANADI, ORM ORQALI EMAS: qo'riqchi
      `sbozor_owner` ulanishida ham ishlashi kerak. ORM orqali o'lchash
      «SQLAlchemy `UPDATE` yubormadi» degan ancha zaif da'voni berardi.
    =======================================================================
    """
    market = env.occupancy.market_a
    graded = [
        add_zone_with_event(
            sync_owner_conn,
            market_id=env.market_a,
            camera_id=env.camera_a,
            stall_id=env.stalls_a[index],
            snapshot_id=env.snapshot_a,
            verdict=verdict,
            confidence=confidence,
            center=(0.15 + 0.2 * index, 0.8),
            # ⚠ `version` SEED BILAN TO'QNASHMASLIGI UCHUN: birinchi rastada
            #   1 va 2, ikkinchisida 1 allaqachon band
            #   (`uq_camera_zones_market_id_camera_id_stall_id_version`).
            version=5,
        )
        for index, (verdict, confidence) in enumerate(
            (
                (OccupancyVerdict.OCCUPIED.value, CONFIDENCE_0_59),
                (OccupancyVerdict.EMPTY.value, CONFIDENCE_0_45),
                (OccupancyVerdict.UNCERTAIN.value, CONFIDENCE_0_55),
            )
        )
    ]

    # (1) Uchala baho ham `confidence` bilan yozilgan.
    stored = sync_owner_conn.execute(
        "SELECT verdict, confidence FROM occupancy_events WHERE id = ANY(%s)",
        ([str(seeded.event_id) for seeded in graded],),
    ).fetchall()
    assert {str(row[0]) for row in stored} == {
        OccupancyVerdict.OCCUPIED.value,
        OccupancyVerdict.EMPTY.value,
        OccupancyVerdict.UNCERTAIN.value,
    }, f"uchala baho ham ifodalanmadi: {stored}"
    assert all(row[1] is not None and 0 <= float(row[1]) <= 1 for row in stored), (
        f"baho `confidence` siz yoki 0..1 dan tashqarida saqlandi: {stored}"
    )

    with pytest.raises(psycopg.errors.RaiseException):
        sync_owner_conn.execute(
            "UPDATE occupancy_events SET verdict = %s WHERE id = %s",
            (OccupancyVerdict.EMPTY.value, str(market.occupied_event_id)),
        )

    with pytest.raises(psycopg.errors.RaiseException):
        sync_owner_conn.execute(
            "UPDATE occupancy_events SET confidence = 0.99 WHERE id = %s",
            (str(market.occupied_event_id),),
        )

    # (3) Nazoratchi qarori — ALOHIDA qator.
    async with tenant_session(env.market_a) as session:
        await ReviewRepository(session, env.market_a).build_uncertain_queue(
            SEED_BUSINESS_DATE, limit=50
        )

    item = (await api_client.get(UNCERTAIN_NEXT_URL, headers=inspector_headers)).json()

    # ⚠ HODISA IDENTIFIKATORI JAVOBDA YO'Q VA BU ATAYIN (`ReviewItemResponse`
    #   — nazoratchi ko'radigan maydonlar ro'yxati tor). U topshiriq orqali
    #   BAZADAN olinadi, ya'ni test payloadga yangi maydon qo'shishni TALAB
    #   QILMAYDI — aks holda darvoza mahsulot yuzasini kengaytirardi.
    event_row = sync_owner_conn.execute(
        "SELECT occupancy_event_id FROM review_assignments WHERE id = %s",
        (str(item["assignment_id"]),),
    ).fetchone()
    assert event_row is not None, "topshiriq bazada topilmadi"
    event_id = UUID(str(event_row[0]))
    before = sync_owner_conn.execute(
        "SELECT verdict, confidence, model_version FROM occupancy_events WHERE id = %s",
        (str(event_id),),
    ).fetchone()
    answer = await api_client.post(
        f"{REVIEW_URL}/{item['assignment_id']}/answer",
        json={"human_verdict": OccupancyVerdict.OCCUPIED.value},
        headers=inspector_headers,
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["system_answer"] == OccupancyVerdict.UNCERTAIN.value
    assert body["human_answer"] == OccupancyVerdict.OCCUPIED.value

    review_rows = sync_owner_conn.execute(
        "SELECT human_verdict, queue_kind, shown_ai_verdict FROM zone_reviews "
        "WHERE review_assignment_id = %s",
        (str(item["assignment_id"]),),
    ).fetchall()
    assert len(review_rows) == 1, (
        f"nazoratchi qarori {len(review_rows)} qator qoldirdi — qaror AYNAN BITTA "
        "ALOHIDA yozuv bo'lishi kerak"
    )
    assert str(review_rows[0][0]) == OccupancyVerdict.OCCUPIED.value, (
        f"inson javobi noto'g'ri yozildi: {review_rows[0]}"
    )
    assert str(review_rows[0][1]) == ReviewQueueKind.UNCERTAIN.value
    # ⚠ `shown_ai_verdict` — BOOLEAN va u «AI javobi javobdan OLDIN
    #   ko'rsatildimi?» degan savolga javob beradi, verdiktning NUSXASI
    #   emas. Noaniq navbatda ham u `false`: tizim javobi FAQAT javobdan
    #   keyin oshkor bo'ladi (D-17.3), ya'ni ankor umuman tug'ilmaydi.
    assert bool(review_rows[0][2]) is False, (
        "javob yozilganda `shown_ai_verdict` `true` bo'lib qoldi — nazoratchiga "
        "tizim javobi javobdan OLDIN ko'rsatilgan bo'lardi"
    )

    after = sync_owner_conn.execute(
        "SELECT verdict, confidence, model_version FROM occupancy_events WHERE id = %s",
        (str(event_id),),
    ).fetchone()
    assert before is not None, "nazorat: javobdan OLDIN hodisa o'qilmadi"
    assert after == before, (
        f"nazoratchi javobidan keyin AI hodisasi o'zgardi ({before} -> {after}) — "
        "«ustiga qo'yiladi» da'vosi «tahrirlanadi» ga aylanib ketgan"
    )


# ===========================================================================
# SC#3
# ===========================================================================


async def test_sc3_uncertain_queue_has_budget_priority_and_no_bulk_endpoint(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    env: Env,
) -> None:
    """MEZON #3: «Nazoratchi kunlik byudjet doirasidagi ustuvorlashtirilgan
    "noaniq" navbatini ko'rib chiqadi; "hammasini tasdiqlash" tugmasi yo'q
    va tasdiqlangan javoblar fine-tuning dataseti sifatida yig'iladi».

    =======================================================================
    TO'RT DA'VO:

      1. NAVBAT NOAINIQDAN IBORAT — unga faqat `uncertain` tushadi;
      2. USTUVORLASHTIRILGAN — biriktirilgan sotuvchisi BOR rasta oldin
         keladi (billing ta'siri), ya'ni tartib TASODIFIY emas;
      3. BYUDJET AMALDA — chegara tugagach 409 `review_budget_exhausted`
         va u «navbat bo'sh» dan BOSHQA kod;
      4. OMMAVIY TASDIQLASH YO'Q — nazoratchi yuzasining birorta marshruti
         MASSIV qabul qilmaydi (OpenAPI sxemasi bo'yicha), ya'ni «hammasini
         tasdiqlash» tugmasini QURIB BO'LMAYDI;
      5. JAVOBLAR YIG'ILADI — javob `purpose='train'` bilan yoziladi va u
         fine-tuning to'plamining manbai.

    ⚠ 4-DA'VO SXEMADAN O'QILADI, MARSHRUT NOMLARIDAN EMAS (§S-10): nomlar
      ro'yxati eskiradi va darvoza abadiy yashil bo'lib qolardi. Sxemaning
      BO'SH bo'lib qolishi ham qoplangan — quyi chegara bor.
    =======================================================================
    """
    # (2) ning kirish holati: biriktirilmagan rastaga IKKINCHI nomzod.
    unassigned = env.domain.market_a.unassigned_stall_id
    assert unassigned is not None, "nazorat: seed'da biriktirilmagan rasta yo'q"
    add_zone_with_event(
        sync_owner_conn,
        market_id=env.market_a,
        camera_id=env.camera_a,
        stall_id=unassigned,
        snapshot_id=env.snapshot_a,
        verdict=OccupancyVerdict.UNCERTAIN.value,
        confidence=CONFIDENCE_0_55,
        center=(0.25, 0.75),
    )

    async with tenant_session(env.market_a) as session:
        await ReviewRepository(session, env.market_a).build_uncertain_queue(
            SEED_BUSINESS_DATE, limit=50
        )

    # ⚠ `build_uncertain_queue()` NING QAYTARGAN SONI EMAS, NAVBATNING O'ZI
    #   sanaladi: seed kunni allaqachon BITTA javobsiz topshiriq bilan
    #   beradi (AI-06 ning kirish holati), ya'ni funksiya faqat YANGI
    #   qatorni yozadi va `1` qaytaradi. Ustuvorlik esa navbatning
    #   TO'LIQ tarkibida o'lchanadi.
    queued_total = sync_owner_conn.execute(
        "SELECT count(*) FROM review_assignments WHERE market_id = %s AND queue_kind = %s",
        (str(env.market_a), ReviewQueueKind.UNCERTAIN.value),
    ).fetchone()
    assert queued_total is not None and int(queued_total[0]) >= 2, (
        f"navbatda {queued_total} band — ustuvorlik o'lchanmasdi"
    )

    # (1) Navbatga FAQAT noaniq tushdi.
    queued = sync_owner_conn.execute(
        "SELECT DISTINCT ev.verdict FROM review_assignments ra "
        "JOIN occupancy_events ev ON ev.id = ra.occupancy_event_id "
        "WHERE ra.market_id = %s AND ra.queue_kind = %s",
        (str(env.market_a), ReviewQueueKind.UNCERTAIN.value),
    ).fetchall()
    assert {str(row[0]) for row in queued} == {OccupancyVerdict.UNCERTAIN.value}, (
        f"noaniq navbatida boshqa verdikt bor: {queued}"
    )

    # (2) Birinchi band — biriktirilgan sotuvchisi BOR rasta.
    first = (await api_client.get(UNCERTAIN_NEXT_URL, headers=inspector_headers)).json()
    first_stall = sync_owner_conn.execute(
        "SELECT cz.stall_id FROM review_assignments ra "
        "JOIN occupancy_events ev ON ev.id = ra.occupancy_event_id "
        "JOIN camera_zones cz ON cz.id = ev.camera_zone_id WHERE ra.id = %s",
        (str(first["assignment_id"]),),
    ).fetchone()
    assert first_stall is not None
    assert UUID(str(first_stall[0])) != unassigned, (
        "navbat biriktirilmagan rastadan boshladi — ustuvorlik billing ta'siriga "
        "tayanmayapti va tartib TASODIFIY bo'lib qolgan"
    )

    # (5) Javob `purpose='train'` bilan yig'iladi.
    answered = await api_client.post(
        f"{REVIEW_URL}/{first['assignment_id']}/answer",
        json={"human_verdict": OccupancyVerdict.OCCUPIED.value},
        headers=inspector_headers,
    )
    assert answered.status_code == 200, answered.text
    purpose = sync_owner_conn.execute(
        "SELECT purpose FROM review_assignments WHERE id = %s",
        (str(first["assignment_id"]),),
    ).fetchone()
    assert purpose is not None
    assert str(purpose[0]) == ReviewPurpose.TRAIN.value, (
        f"javob `{purpose[0]}` bilan yozildi — fine-tuning to'plami `train` "
        "qatorlaridan yig'iladi va bu qator unga tushmasdi"
    )

    # (3) Byudjet — SOZLAMA va u AMALDA.
    with budget_of(api_app, uncertain=1):
        exhausted = await api_client.get(UNCERTAIN_NEXT_URL, headers=inspector_headers)
    restored = await api_client.get(UNCERTAIN_NEXT_URL, headers=inspector_headers)

    assert exhausted.status_code == 409, exhausted.text
    assert exhausted.json()["detail"] == "review_budget_exhausted"
    assert restored.status_code == 200, (
        "byudjet ko'tarilgach navbat bo'sh chiqdi — yuqoridagi 409 byudjetdan EMAS edi"
    )

    budget = await api_client.get(BUDGET_URL, headers=inspector_headers)
    assert budget.status_code == 200, budget.text
    assert budget.json()["uncertain"]["answered"] == 1

    # (4) Ommaviy tasdiqlash marshruti YO'Q.
    schema = fastapi_app.openapi()
    write_paths = {
        (path, method)
        for path, operations in schema["paths"].items()
        for method, operation in operations.items()
        if method in {"post", "put", "patch", "delete"} and isinstance(operation, dict)
    }
    assert len(write_paths) >= 20, (
        f"sxemada faqat {len(write_paths)} ta yozuv marshruti topildi — skaner BO'SH "
        "sxemada ishlayotgan bo'lsa bu darvoza JIMGINA yashil bo'lardi"
    )
    bulk = sorted(
        f"{method.upper()} {path}"
        for path, method in write_paths
        if path.startswith(REVIEW_URL) and _accepts_array(schema, path, method)
    )
    assert not bulk, (
        f"nazoratchi yuzasida MASSIV qabul qiluvchi marshrut bor: {bulk} — "
        "«hammasini tasdiqlash» tugmasi shundan qurilardi"
    )


def _accepts_array(schema: dict[str, Any], path: str, method: str) -> bool:
    """Marshrutning tanasi massivmi — `$ref` zanjiri ochib ko'riladi."""
    body = schema["paths"][path][method].get("requestBody")
    if not isinstance(body, dict):
        return False
    for media in body.get("content", {}).values():
        node = media.get("schema", {})
        if node.get("type") == "array":
            return True
        ref = node.get("$ref")
        if isinstance(ref, str):
            name = ref.rsplit("/", 1)[-1]
            model = schema["components"]["schemas"].get(name, {})
            if any(field.get("type") == "array" for field in model.get("properties", {}).values()):
                return True
    return False


# ===========================================================================
# SC#4
# ===========================================================================


async def test_sc4_blind_audit_hides_the_system_answer_and_report_uses_only_that_sample(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """MEZON #4: «Nazoratchi ko'r audit navbatida AI javobini ko'rmasdan
    tasodifiy tanlangan zonalarni baholaydi — aniqlik hisoboti faqat shu
    namunadan chiqadi».

    =======================================================================
    IKKI DA'VO VA ULAR MUSTAQIL — SHUNING UCHUN IKKALASI HAM O'LCHANADI:

      1. KO'RMASDAN — payloadda tizim javobi YO'Q. ⛔ «Yashirilgan» EMAS,
         UMUMAN YO'Q: maydon e'lon qilinmaydi, ya'ni uni `null` deb
         qaytarish yo'li ham yopiq. Ikki qatlam o'lchanadi — KALIT
         nomlari va XOM MATN (verdikt so'zining o'zi).
      2. FAQAT SHU NAMUNADAN — aniqlik hisoboti `purpose='eval'` +
         `queue_kind='blind_audit'` qatorlaridan chiqadi. Nazorat:
         noaniq navbatiga javob YOZILADI va hisobotning soni
         O'ZGARMAYDI. ⛔ Usiz test hisobotning FILTRINI emas, uning
         mavjudligini o'lchagan bo'lardi.

    ⚠ NAMUNA `audit_draw` BILAN TORTILADI, QO'LDA YOZILMAYDI: qo'lda
      yozilgan namuna «tasodifiy tanlangan» jumlasini butunlay chetlab
      o'tardi.
    =======================================================================
    """
    clear_review_state(sync_owner_conn, env.market_a)
    for index in range(6):
        add_zone_with_event(
            sync_owner_conn,
            market_id=env.market_a,
            camera_id=env.camera_a,
            stall_id=env.stalls_a[index % len(env.stalls_a)],
            snapshot_id=env.snapshot_a,
            verdict=OccupancyVerdict.OCCUPIED.value
            if index % 2 == 0
            else OccupancyVerdict.UNCERTAIN.value,
            confidence=CONFIDENCE_0_59 if index % 2 == 0 else CONFIDENCE_0_55,
            center=(0.1 + 0.12 * index, 0.15),
            # Seed bilan ham, bir-biri bilan ham to'qnashmaydigan versiyalar.
            version=20 + index,
        )

    drawn = await audit_draw(
        app_sessionmaker, business_date=SEED_BUSINESS_DATE, sample_size=4, eval_ratio=0.70
    )
    assert drawn.drawn > 0, f"namuna tortilmadi: {drawn}"

    item = await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)
    assert item.status_code == 200, item.text

    # (1a) Tizim javobining birorta kaliti YO'Q.
    forbidden = frozenset(
        {
            "verdict",
            "ai_verdict",
            "system_verdict",
            "system_answer",
            "confidence",
            "model_version",
            "thresholds_version",
            "purpose",
            "queue_kind",
            "shown_ai_verdict",
            "effective_verdict",
        }
    )
    leaked = sorted(forbidden & all_keys(item.json()))
    assert not leaked, f"ko'r payloadda tizim javobining kaliti bor: {leaked}"

    # (1b) Xom matnda ham verdikt so'zi yo'q — KALIT NOMIDAN mustaqil qatlam.
    lowered = item.text.lower()
    for word in (
        OccupancyVerdict.OCCUPIED.value,
        OccupancyVerdict.EMPTY.value,
        OccupancyVerdict.UNCERTAIN.value,
    ):
        assert word not in lowered, f"ko'r payload matnida `{word}` uchradi — u ANKOR tashiydi"

    # (2a) BUTUN namuna javoblanadi — `eval` ham, `train` ham.
    #
    # ⚠⚠ BU SABOTAJ O'LCHOVIDAN KEYIN KENGAYTIRILDI VA SABAB YOZILADI.
    #    Avval AYNAN BITTA band javoblanardi va `and` -> `or` sabotaji
    #    (`accuracy_report.py:396`) darvozani UMUMAN qizartirmagan:
    #    noaniq navbatidagi javobda ikkala shart ham (`purpose='train'`,
    #    `queue_kind='uncertain'`) YOLG'ON, ya'ni `or` ham uni chetda
    #    qoldirardi. Ya'ni test filtrning IKKI shartini emas, faqat
    #    bittasini o'lchayotgan edi.
    #
    #    Ajratuvchi holat KO'R namunaning ICHIDA: D-14 ning 70/30
    #    kvotasi `queue_kind='blind_audit'` bo'lgan, LEKIN
    #    `purpose='train'` bo'lgan qatorlarni ham yaratadi. `or` ostida
    #    ular hisobotga TUSHARDI. Shuning uchun ikkala guruh ham
    #    javoblanadi va hisobotdagi son `eval` lar soniga TENG bo'lishi
    #    tekshiriladi.
    purposes: dict[str, int] = {}
    current = item
    while current.status_code == 200:
        assignment_id = current.json()["assignment_id"]
        row = sync_owner_conn.execute(
            "SELECT purpose FROM review_assignments WHERE id = %s",
            (str(assignment_id),),
        ).fetchone()
        assert row is not None, f"topshiriq {assignment_id} bazada yo'q"
        purposes[str(row[0])] = purposes.get(str(row[0]), 0) + 1

        answered = await api_client.post(
            f"{REVIEW_URL}/blind/{assignment_id}/answer",
            json={"human_verdict": OccupancyVerdict.OCCUPIED.value},
            headers=inspector_headers,
        )
        assert answered.status_code == 200, answered.text
        current = await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)

    assert current.status_code == 409, (
        f"ko'r navbat 200/409 dan boshqa kod berdi: {current.status_code}"
    )
    assert purposes.get(ReviewPurpose.EVAL.value, 0) > 0, (
        f"namunada `eval` bandi yo'q: {purposes} — hisobotning manbai umuman tug'ilmasdi"
    )
    assert purposes.get(ReviewPurpose.TRAIN.value, 0) > 0, (
        f"namunada `train` bandi yo'q: {purposes} — 70/30 kvotasining IKKINCHI "
        "yarmi tug'ilmagan va filtrning `purpose` sharti O'LCHANMAY qolardi"
    )

    baseline = await accuracy(api_client, director_headers)
    measured_n = baseline["n"]
    assert measured_n == purposes[ReviewPurpose.EVAL.value], (
        f"hisobot {measured_n} ta javobni sanadi, `eval` esa "
        f"{purposes[ReviewPurpose.EVAL.value]} ta ({purposes}) — hisobot ko'r "
        "namunaning `train` yarmini ham o'lchovga qo'shib yuborgan"
    )

    # (2) NAZORAT: noaniq navbatidagi javob hisobotni O'ZGARTIRMAYDI.
    async with tenant_session(env.market_a) as session:
        await ReviewRepository(session, env.market_a).build_uncertain_queue(
            SEED_BUSINESS_DATE, limit=50
        )
    uncertain = await api_client.get(UNCERTAIN_NEXT_URL, headers=inspector_headers)
    assert uncertain.status_code == 200, uncertain.text
    train_answer = await api_client.post(
        f"{REVIEW_URL}/{uncertain.json()['assignment_id']}/answer",
        json={"human_verdict": OccupancyVerdict.EMPTY.value},
        headers=inspector_headers,
    )
    assert train_answer.status_code == 200, train_answer.text

    after = await accuracy(api_client, director_headers)
    assert after["n"] == measured_n, (
        f"noaniq navbatidagi javob aniqlik hisobotini o'zgartirdi "
        f"({measured_n} -> {after['n']}) — hisobot KO'R NAMUNADAN TASHQARIDAGI "
        "javoblarni ham sanayapti va aniqlik da'vosi yolg'on bo'lardi"
    )


# ===========================================================================
# SC#5
# ===========================================================================


async def test_sc5_any_camera_occupied_wins_and_unreviewed_uncertain_defaults_to_empty(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """MEZON #5: «Rasta bir necha kamerada ko'rinsa birortasi "band" desa rasta
    band; kun oxirigacha tasdiqlanmagan "noaniq" esa "bo'sh" bo'ladi va
    hisobotda alohida belgilanadi».

    =======================================================================
    UCH DA'VO:

      1. AGREGATSIYA — bitta rasta ikki kamerada. Birinchi kamera IKKI
         zonada ham `empty` deydi, ikkinchisi BITTA zonada `occupied`.
         Kun yopilgach rasta-slot `occupied` bo'ladi va manbasi `ai`.
         ⛔ IKKI `empty` ATAYIN: bitta bo'lganda «birinchi zona g'olib»
            va «kamera A g'olib» degan buzuq implementatsiyalar ham
            YASHIL qolardi. Ko'pchilik `empty` tomonda bo'lgani uchun
            «ko'pchilik ovozi» varianti ham rad etiladi.
      2. JAVOBSIZ NOAINIQ -> BO'SH — `verdict='empty'`, LEKIN
         `resolution_source='default_empty'`.
      3. HISOBOTDA ALOHIDA — `GET /occupancy` `default_empty` ni
         `empty` dan AJRATIB beradi, ya'ni «bo'sh» va «ko'rilmagani
         uchun bo'sh» bir xil raqamga qo'shilmaydi.

    ⚠ 2-DA'VO 1-DA'VONING NAZORAT QUTBI HAM: u AYNI YUGURISHDA `occupied`
      BO'LMAGAN qatorlar borligini ko'rsatadi. Usiz «hamma narsani
      `occupied` qilib qo'yish» ham 1-da'voni yashil qilardi.

    ⚠ 2 va 3 BIR-BIRINI ALMASHTIRMAYDI: birinchisi materializatsiyaning
      USTUNI haqida, ikkinchisi HISOBOT YUZASI haqida. Ustun to'g'ri
      to'lib, hisobot uni `empty` ga qo'shib yuborsa, mezon jumlasining
      IKKINCHI yarmi («hisobotda alohida belgilanadi») buzilgan bo'lardi
      va birinchi da'vo buni KO'RMASDI.

    ⚠ RASTA TANLOVI YUK KO'TARADI: `stall_without_zone_id` da seed'ning
      BIRORTA zonasi ham yo'q, ya'ni uning kun hukmi FAQAT shu testda
      yozilgan hodisalardan chiqadi. Seed hodisasi bor rastani olish
      «birinchi kamera `occupied` dedi» holatini yashirib, testni
      o'z-o'zini tasdiqlovchi qilardi.
    =======================================================================
    """
    shared_stall = env.occupancy.market_a.stall_without_zone_id
    assert shared_stall is not None, "nazorat: seed'da zonasiz rasta yo'q"

    # (1) Bitta rasta — ikki kamera. Kamera A: IKKI zona, ikkalasi ham `empty`.
    for index, center in enumerate(((0.30, 0.30), (0.70, 0.20))):
        add_zone_with_event(
            sync_owner_conn,
            market_id=env.market_a,
            camera_id=env.camera_a,
            stall_id=shared_stall,
            snapshot_id=env.snapshot_a,
            verdict=OccupancyVerdict.EMPTY.value,
            confidence=CONFIDENCE_0_45,
            center=center,
            version=30 + index,
        )
    # Kamera B: BITTA zona, `occupied` — va u YOLG'IZ o'zi g'olib bo'lishi kerak.
    add_zone_with_event(
        sync_owner_conn,
        market_id=env.market_a,
        camera_id=env.second_camera,
        stall_id=shared_stall,
        snapshot_id=env.snapshot_a,
        verdict=OccupancyVerdict.OCCUPIED.value,
        confidence=CONFIDENCE_0_59,
        center=(0.55, 0.55),
        version=30,
    )

    result = await day_close(app_sessionmaker, business_date=SEED_BUSINESS_DATE)
    assert result.markets >= 1, f"kun yopilishi birorta bozorni ko'rmadi: {result}"

    shared = slot_rows(sync_owner_conn, env.market_a, shared_stall)

    assert shared, "umumiy rasta uchun slot qatori tug'ilmadi"
    assert any(
        verdict == OccupancyVerdict.OCCUPIED.value and source == ResolutionSource.AI.value
        for verdict, source in shared
    ), (
        f"ikki kameradan biri `occupied` desa ham rasta band bo'lmadi (yoki manba "
        f"`ai` emas): {shared} — AI-05 ning agregatsiya qoidasi bajarilmagan"
    )

    # (2) Javobsiz noaniq -> `empty` + `default_empty`.
    defaulted = sync_owner_conn.execute(
        "SELECT count(*) FROM stall_slot_occupancy WHERE market_id = %s "
        "AND business_date = %s AND resolution_source = %s AND verdict = %s",
        (
            str(env.market_a),
            SEED_BUSINESS_DATE,
            ResolutionSource.DEFAULT_EMPTY.value,
            OccupancyVerdict.EMPTY.value,
        ),
    ).fetchone()
    assert defaulted is not None and int(defaulted[0]) > 0, (
        "javobsiz `uncertain` uchun `default_empty` qatori tug'ilmadi — AI-06 ning "
        "yo'li umuman bajarilmagan. ⚠ Bu assert 1-da'voning NAZORAT QUTBI ham: "
        "u ayni yugurishda `occupied` BO'LMAGAN qatorlar borligini ko'rsatadi"
    )

    # (3) Hisobotda ALOHIDA.
    report = await api_client.get(
        OCCUPANCY_URL, params={"day": SEED_BUSINESS_DATE.isoformat()}, headers=director_headers
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert "default_empty" in body, (
        "hisobotda `default_empty` maydoni YO'Q — «ko'rilmagani uchun bo'sh» oddiy "
        "`empty` ichida ko'milib ketardi"
    )
    assert body["default_empty"] > 0, (
        f"hisobot `default_empty` ni 0 deb beryapti, baza esa {defaulted[0]} qator "
        "ko'ryapti — hisobot materializatsiyadan ajralib qolgan"
    )
    assert body["occupied"] >= 1, f"hisobotda band rasta ko'rinmadi: {body}"


# ===========================================================================
# META — mezonlardan birortasi JIMGINA tushib qolmasin
# ===========================================================================


def test_every_criterion_has_its_own_test() -> None:
    """Beshala mezon uchun AYNAN BITTA nomlangan test mavjud.

    USIZ MEZONLARDAN BIRI JIMGINA TUSHIB QOLARDI: fayl qayta tashkil
    qilinganda yoki test vaqtincha o'chirilganda darvoza baribir yashil
    bo'lardi va «beshala mezon o'lchanadi» da'vosi isbotsiz qolardi.

    ⚠ META-TESTNING O'Z NOMIDA `sc<raqam>` YO'Q va bu ataylab: darvoza
      `sc[1-5]` naqshini SANAYDI, ya'ni meta-testning o'zi sanoqqa kirib
      ketmasligi kerak.
    """
    module = sys.modules[__name__]
    names = sorted(
        name
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    )

    for number in range(1, 6):
        owned = [name for name in names if name.startswith(f"test_sc{number}_")]
        assert len(owned) == 1, (
            f"SC#{number} uchun {len(owned)} ta test topildi ({owned}) — har mezonning "
            "egasi AYNAN BITTA nomlangan test bo'lishi kerak"
        )

    criteria = [name for name in names if name.startswith("test_sc")]
    assert len(criteria) == 5, f"mezon testlari soni 5 emas: {criteria}"


def test_criteria_module_uses_no_fakes() -> None:
    """SOXTALASHTIRISHSIZ O'LCHOV DARVOZASI — IKKI MUSTAQIL YO'L.

    =======================================================================
    NEGA IKKI YO'L KERAK VA NEGA BIRI YETMAYDI.

    Soxtalashtirishning ikki shakli bor va ular BOSHQA-BOSHQA izda
    qoladi:

      1. KUTUBXONA IMPORTI (`unittest.mock`, `respx`, `moto`) — `ast`
         daraxtida ko'rinadi. Satr bo'yicha qidiruv izohni koddan ajrata
         olmasdi, shuning uchun daraxt o'qiladi.
      2. FIXTURE SO'ROVI (`monkeypatch`, yoki loyihaning O'Z spy
         fixture'i `enqueued`) — birorta IMPORT talab qilmaydi, ya'ni
         birinchi yo'l uni UMUMAN ko'rmasdi. U `inspect.signature` bilan
         topiladi (`test_phase3_criteria.py:1120-1124` shakli).

    ⚠ UCHINCHI DA'VO — DARAXTNING BO'SH BO'LMASLIGI. Skaner nosozlansa
      yoki fayl qayta nomlansa ikkala to'plam ham bo'sh chiqib, darvoza
      TRIVIAL ravishda yashil bo'lardi.

    ⛔ «O'TKAZIB YUBORISH» YO'LI ATAYIN YO'Q: bu yerda `skipif` ham,
       `xfail` ham yo'q. Soxtalashtirilgan mezon — «faza tugadi» degan
       da'voning eng arzon yolg'on shakli.
    =======================================================================
    """
    module_path: Path = _MODULE_PATH
    tree = ast.parse(module_path.read_text(encoding="utf-8"))

    roots: set[str] = set()
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
            imported_names |= {alias.name for alias in node.names}

    assert len(roots) >= 10, (
        f"faqat {len(roots)} ta import ildizi topildi — `ast` skaneri bo'sh daraxtda "
        "ishlayotgan bo'lsa bu darvoza JIMGINA yashil bo'lardi"
    )
    assert not roots & _MOCK_ROOTS, (
        f"soxtalashtirish kutubxonasi import qilingan: {sorted(roots & _MOCK_ROOTS)} — "
        "bu fayl HAQIQIY `postgres:18.4` va HAQIQIY marshrut grafi ustida o'lchaydi"
    )
    assert not imported_names & _MOCK_NAMES, (
        f"soxtalashtirish vositasi import qilingan: {sorted(imported_names & _MOCK_NAMES)}"
    )

    module = sys.modules[__name__]
    tests = [
        (name, obj)
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    ]
    assert len(tests) >= 7, (
        f"modulda faqat {len(tests)} ta test topildi — imzo skaneri BO'SH ro'yxatda "
        "ishlayotgan bo'lsa bu darvoza ham jimgina yashil bo'lardi"
    )

    faked = sorted(
        f"{name}({', '.join(sorted(_FAKE_FIXTURES & set(inspect.signature(obj).parameters)))})"
        for name, obj in tests
        if _FAKE_FIXTURES & set(inspect.signature(obj).parameters)
    )
    assert faked == [], (
        f"quyidagi testlar soxtalashtiruvchi fixture so'rayapti: {faked} — mezon "
        "moduli na detektorni, na omborni, na brokerni almashtiradi"
    )


def test_the_criteria_module_claims_no_accuracy_number() -> None:
    """⛔ D-01 NING MEXANIK SHAKLI — bu modulda ANIQLIK RAQAMI YOZILMAYDI.

    =======================================================================
    NEGA BU DARVOZA MAVJUD.

    Fazaning eng oson yolg'oni — mexanika qatlamining yashilligini
    aniqlik da'vosi bilan yakunlash: «beshala mezon yashil, demak
    detektor ishlaydi». Loyiha bu shaklni IKKI marta rad etgan
    (2-fazaning o'zini o'zi tasdiqlovchi shabloni, 3-fazaning
    «simulyatordan kadr olib tekshiramiz» taklifi).

    Darvoza `n`/`measured` kabi HISOBOT MAYDONLARINI taqiqlamaydi —
    ular o'lchangan qatorlarning SONI, aniqlik DA'VOSI emas. Taqiq
    aniqlikni FOIZ yoki nisbat sifatida e'lon qiladigan identifikator
    nomlariga qo'yilgan.

    ⚠ Darvoza `ast` daraxtidan NOM sifatida o'qiydi, matndan EMAS: bu
      docstringning O'ZI «accuracy» so'zini ishlatadi va matn skani
      o'zini o'zi qizartirardi.
    =======================================================================
    """
    module_path: Path = _MODULE_PATH
    tree = ast.parse(module_path.read_text(encoding="utf-8"))

    banned = {"precision", "recall", "f1", "map50", "accuracy_percent", "map"}
    named: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            named.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            named.add(node.attr.lower())

    assert named, "`ast` daraxtida birorta nom topilmadi — skaner bo'sh ishlayapti"
    claimed = sorted(banned & named)
    assert not claimed, (
        f"mezon modulida aniqlik metrikasi nomi bor: {claimed} — bu fayl "
        "MEXANIKANI o'lchaydi, DETEKTORNI emas; aniqlik o'lchovi oltin to'plam "
        "kelguncha UXLAB YOTADI (`05-HUMAN-UAT.md` #1)"
    )


def test_the_module_names_a_market_that_the_seed_actually_owns(
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """NAZORAT — seed HAQIQATAN yozilgan va testlar bo'sh bazada yugurmayapti.

    ⛔ USIZ BUTUN FAYL «BO'SH TO'PLAM USTIDA YASHIL» BO'LARDI: har
       `assert` ning kirish holati seed'dan keladi va seed jimgina
       yozilmay qolsa, ko'pchilik da'vo trivial ravishda o'tardi.
    """
    counts = {
        table: int(
            (
                sync_owner_conn.execute(
                    f"SELECT count(*) FROM {table} WHERE market_id = %s",  # noqa: S608
                    (str(env.market_a),),
                ).fetchone()
                or (0,)
            )[0]
        )
        for table in ("camera_zones", "occupancy_events", "review_assignments")
    }

    assert all(value > 0 for value in counts.values()), (
        f"seed to'liq yozilmagan: {counts} — mezon testlari bo'sh holatda yugurardi"
    )
