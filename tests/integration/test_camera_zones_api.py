"""`camera_zones` HTTP yuzasi — versiyalash, V5 darvozasi va qamrov (AI-01).

=============================================================================
DA'VOLAR MEXANIZM EMAS, XULQ BILAN O'LCHANADI.

03-07 da o'lchangan holat bu faylning butun uslubini belgilaydi: huquq
talabini marshrut dekoratoridan imzo parametriga ko'chirish HECH NIMANI
qizartirmagan, chunki kafolatning IKKI mustaqil mexanizmi bor edi va
ikkinchisi (fon vazifasining yo'qligi) uni yolg'iz ushlab turardi. Ya'ni
«dekoratorda turibdi» ni tekshiradigan test MEXANIZMNI o'lchardi,
DA'VONI emas.

Shuning uchun bu yerdagi testlar so'rov yuboradi va NATIJANI o'lchaydi:

    huquq da'vosi   -> `CAMERA_MANAGE` siz `PUT` **403** oladi VA
                       `audit_log` da soxta o'qish qatori QOLMAYDI;
    audit da'vosi   -> muvaffaqiyatli `GET` dan keyin o'qish qatori YO'Q;
    versiya da'vosi -> eski qator BAZADA `is_active = false` bo'lib TURIBDI.

Birortasi ham dekorator matnini, bog'liqlik daraxtini yoki funksiya
imzosini o'qimaydi.
=============================================================================

NAZORAT HOLATLARI JUFTLIGI (`test_tariff_history.py` naqshi).

Har «rad etiladi» testining yonida «qabul qilinadi» jufti turadi. Usiz
«hamma narsa bloklangan» holati ham YASHIL ko'rinardi: `PUT` butunlay
ishlamay qolganda ham rad etish testlari o'tib ketardi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fixtures.admin_api import session_headers
from fixtures.auth_api import audit_rows
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import (
    NARROW_SOURCE_HEIGHT,
    NARROW_SOURCE_WIDTH,
    SOURCE_HEIGHT,
    SOURCE_WIDTH,
    OccupancyDomainSeed,
    occupancy_rows,
    square_polygon,
)
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import AuditAction

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow

ZONES_URL = "/api/v1/camera-zones"
COVERAGE_URL = "/api/v1/camera-zones/coverage"

TABLE_CAMERA_ZONES = "camera_zones"

_ZONE_ROW = (
    "SELECT version, is_active, source_width, source_height, polygon "
    "FROM camera_zones WHERE id = %s"
)
_ZONE_ROWS_FOR_STALL = (
    "SELECT id, version, is_active FROM camera_zones "
    "WHERE camera_id = %s AND stall_id = %s ORDER BY version"
)


class Env:
    """Bir testga kerak bo'ladigan hamma narsa — bitta obyektda.

    Fixture zanjiri to'rt qatlamli (`nvr_rows` -> `snapshot_rows` ->
    `occupancy_rows`) va uni har testda qayta yozish faylning yarmini
    takrorlash bo'lardi.
    """

    def __init__(
        self,
        base: TwoMarketSeed,
        domain: MarketDomainSeed,
        occupancy: OccupancyDomainSeed,
    ) -> None:
        self.base = base
        self.domain = domain
        self.occupancy = occupancy

    @property
    def market_a(self) -> UUID:
        return self.base.market_a.id

    @property
    def camera_a(self) -> UUID:
        return self.occupancy.market_a.camera_id

    @property
    def stalls_a(self) -> tuple[UUID, ...]:
        return self.domain.market_a.stall_ids


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """To'rt qatlamli seed; tozalash TESKARI tartibda (FK zanjiri bo'yicha)."""
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        yield Env(two_markets, market_domain, occupancy)


@pytest.fixture
async def admin_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """A bozori adminining sessiyasi — unda `CAMERA_MANAGE` BOR."""
    return await session_headers(
        api_client, env.base.market_a.admin_phone, env.base.market_a.admin_password
    )


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """Direktor sessiyasi — `CAMERA_VIEW` BOR, `CAMERA_MANAGE` YO'Q (D-07)."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


def zone_body(
    stall_id: UUID,
    *,
    polygon: list[list[float]] | None = None,
    width: int = SOURCE_WIDTH,
    height: int = SOURCE_HEIGHT,
) -> dict[str, Any]:
    """`PUT` tanasining BITTA elementi — geometrik fakt bo'yicha (§S-9)."""
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
    *,
    extra: dict[str, Any] | None = None,
) -> httpx.Response:
    body: dict[str, Any] = {"zones": zones}
    if extra is not None:
        body.update(extra)
    return await client.put(
        ZONES_URL, params={"camera_id": str(camera_id)}, json=body, headers=headers
    )


# ===========================================================================
# 1. VERSIYALASH (D-07) — eski qator JOYIDA qoladi
# ===========================================================================


async def test_edit_creates_new_version(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Poligonni o'zgartirish YANGI `version` qatorini yaratadi.

    Seed'da birinchi rastaning konturi `version = 2` (undan oldin
    eskirgan `version = 1` bor), ya'ni tahrirdan keyin `version = 3`
    kutiladi. Bu son QO'LDA hisoblangan: `MAX(version) + 1`.
    """
    stall = env.stalls_a[0]

    response = await put_zones(
        api_client,
        admin_headers,
        env.camera_a,
        [zone_body(stall, polygon=square_polygon(0.6, 0.6))],
    )

    assert response.status_code == 200, response.text
    rows = sync_owner_conn.execute(_ZONE_ROWS_FOR_STALL, (str(env.camera_a), str(stall))).fetchall()

    versions = [(int(row[1]), bool(row[2])) for row in rows]
    assert versions == [(1, False), (2, False), (3, True)], (
        f"kutilgan versiya zanjiri (1,2 eskirgan; 3 faol), olindi: {versions}"
    )


async def test_old_version_survives_edit(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Eski qator O'CHIRILMAYDI — poligoni ham AYNAN o'zgarishsiz qoladi.

    ⛔ «Qator bor» yetarli emas: `is_active = false` qilib qo'yib,
       poligonni ustiga yozish ham mumkin edi va o'shanda
       `occupancy_events.zone_version` mavjud qatorga ishora qilib
       turardi-yu, u BOSHQA konturni ko'rsatardi — ya'ni tarix jimgina
       qayta yozilardi. Shuning uchun POLIGON ham solishtiriladi.
    """
    stall = env.stalls_a[0]
    superseded = env.occupancy.market_a.superseded_zone_id
    assert superseded is not None, "seed'da eskirgan zona yo'q — bu test hech nimani o'lchamaydi"

    before = sync_owner_conn.execute(_ZONE_ROW, (str(superseded),)).fetchone()
    assert before is not None

    response = await put_zones(
        api_client,
        admin_headers,
        env.camera_a,
        [zone_body(stall, polygon=square_polygon(0.7, 0.3))],
    )
    assert response.status_code == 200, response.text

    after = sync_owner_conn.execute(_ZONE_ROW, (str(superseded),)).fetchone()
    assert after is not None, "eskirgan zona O'CHIRILDI — tarix yo'qoldi"
    assert after == before, "eskirgan zona ustiga yozildi — tarix qayta yozildi"


async def test_identical_polygon_creates_no_new_version(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """AYNAN o'sha poligon bilan ikkinchi saqlash yangi versiya YARATMAYDI.

    ⛔ Aks holda muharrirda hech nima o'zgartirmasdan `[Saqlash]` bosish
       tarixni shishirardi: bir kunda o'nlab bir-biridan farq qilmaydigan
       versiya paydo bo'lib, `zone_version` «qaysi kontur?» savoliga
       javob bera olmay qolardi.
    """
    stall = env.stalls_a[0]
    polygon = square_polygon(0.45, 0.45)

    first = await put_zones(
        api_client, admin_headers, env.camera_a, [zone_body(stall, polygon=polygon)]
    )
    assert first.status_code == 200, first.text
    after_first = sync_owner_conn.execute(
        _ZONE_ROWS_FOR_STALL, (str(env.camera_a), str(stall))
    ).fetchall()

    second = await put_zones(
        api_client, admin_headers, env.camera_a, [zone_body(stall, polygon=polygon)]
    )
    assert second.status_code == 200, second.text
    after_second = sync_owner_conn.execute(
        _ZONE_ROWS_FOR_STALL, (str(env.camera_a), str(stall))
    ).fetchall()

    assert after_second == after_first, (
        "bir xil poligon bilan ikkinchi saqlash qatorlarni o'zgartirdi"
    )


async def test_delete_marks_the_zone_inactive_and_keeps_the_row(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """`DELETE` — 204 va qator JOYIDA (`is_active = false`), qattiq o'chirish YO'Q."""
    zone_id = env.occupancy.market_a.active_zone_ids[0]

    response = await api_client.delete(f"{ZONES_URL}/{zone_id}", headers=admin_headers)

    assert response.status_code == 204, response.text
    row = sync_owner_conn.execute(_ZONE_ROW, (str(zone_id),)).fetchone()
    assert row is not None, "zona QATTIQ o'chirildi — dalil zanjiri uziladi"
    assert row[1] is False

    # Ikkinchi chaqiruv 404: allaqachon eskirgan zona uchun 204 qaytarish
    # «o'chirdim» degan yolg'on tasdiq bo'lardi.
    again = await api_client.delete(f"{ZONES_URL}/{zone_id}", headers=admin_headers)
    assert again.status_code == 404


# ===========================================================================
# 2. KO'P KAMERA (D-20) va NISBAT (§6.8)
# ===========================================================================


async def test_stall_can_be_covered_by_two_cameras(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Bir rasta IKKI kamerada faol zonaga ega bo'lishi mumkin (D-20).

    Bu taqiq EMAS, mahsulotning ASOSI: «birortasi band desa — rasta
    band». Seed shu holatni allaqachon yozgan; test uni IKKALA kameraning
    javobida ham ko'rinishini o'lchaydi.
    """
    second_camera = env.occupancy.market_a.second_camera_id
    assert second_camera is not None, "seed'da ikkinchi kamera yo'q"
    stall = env.stalls_a[0]

    first = await api_client.get(
        ZONES_URL, params={"camera_id": str(env.camera_a)}, headers=admin_headers
    )
    second = await api_client.get(
        ZONES_URL, params={"camera_id": str(second_camera)}, headers=admin_headers
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert str(stall) in {item["stall_id"] for item in first.json()["items"]}
    assert str(stall) in {item["stall_id"] for item in second.json()["items"]}


async def test_second_zone_for_the_same_stall_on_one_camera_is_rejected(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """BIR KAMERADA bir rastaga ikkinchi zona — 409.

    Yuqoridagi testning JUFTI va u aynan chegarani ko'rsatadi: taqiq
    faqat bitta kamera ICHIDA amal qiladi. Ikki kontur bir kadrda bir
    rastaga ikki qarama-qarshi verdikt berardi va qaysi biri hisobga
    kirishini aniqlab bo'lmasdi.
    """
    stall = env.stalls_a[0]

    response = await put_zones(
        api_client,
        admin_headers,
        env.camera_a,
        [
            zone_body(stall, polygon=square_polygon(0.3, 0.3)),
            zone_body(stall, polygon=square_polygon(0.7, 0.7)),
        ],
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "zone_stall_already_covered"


async def test_aspect_change_flags_zone(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Nisbati JORIY kadrnikidan farq qiladigan zona `needs_review` oladi.

    ⛔ VA U SAQLANADI, RAD ETILMAYDI: avtomatik to'g'rilash QILINMAYDI
       (§6.8) — cho'zilganmi yoki kesilganmi, bilib bo'lmaydi.

    Nazorat juftligi bitta testda: bir xil kamerada IKKI zona bor —
    biri 16:9 (kadr bilan mos), ikkinchisi 4:3. Faqat ikkinchisi
    belgilanishi SHART. Yagona zonali test «hamma zona belgilandi»
    holatida ham yashil bo'lardi.
    """
    stall_matching, stall_narrow = env.stalls_a[0], env.stalls_a[1]

    saved = await put_zones(
        api_client,
        admin_headers,
        env.camera_a,
        [
            zone_body(stall_matching, width=SOURCE_WIDTH, height=SOURCE_HEIGHT),
            zone_body(
                stall_narrow,
                polygon=square_polygon(0.7, 0.7),
                width=NARROW_SOURCE_WIDTH,
                height=NARROW_SOURCE_HEIGHT,
            ),
        ],
    )

    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["frame_width"] is not None, (
        "kadr o'lchami noma'lum — bu holatda `needs_review` hech qachon "
        "ko'tarilmaydi va test hech nimani o'lchamasdi"
    )

    flags = {item["stall_id"]: item["needs_review"] for item in body["items"]}
    assert flags[str(stall_narrow)] is True, "4:3 da chizilgan zona belgilanmadi"
    assert flags[str(stall_matching)] is False, (
        "16:9 da chizilgan zona ham belgilandi — bayroq HAR zonaga qo'yilyapti"
    )


# ===========================================================================
# 3. V5 DARVOZASI — server ISHONCH MANBAI
# ===========================================================================


async def test_self_intersecting_polygon_is_rejected(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """«Kapalak» poligon 422 + `zone_polygon_self_intersecting` oladi."""
    bowtie = [[0.1, 0.1], [0.9, 0.9], [0.9, 0.1], [0.1, 0.9]]

    response = await put_zones(
        api_client, admin_headers, env.camera_a, [zone_body(env.stalls_a[0], polygon=bowtie)]
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "zone_polygon_self_intersecting"


async def test_polygon_out_of_range_is_rejected(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Xom PIKSEL koordinatasi 422 + `zone_polygon_out_of_range` oladi.

    Eng ehtimoliy haqiqiy xato — klient normalashni unutishi. Chegarasiz
    bunday zona saqlanardi va denormalashdan keyin kadr chetidan uzoqqa
    tushardi: ko'rinmas, lekin baribir «qamrovda» deb sanaladigan zona.
    """
    pixels = [[640.0, 360.0], [900.0, 360.0], [900.0, 500.0]]

    response = await put_zones(
        api_client, admin_headers, env.camera_a, [zone_body(env.stalls_a[0], polygon=pixels)]
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "zone_polygon_out_of_range"


async def test_valid_polygon_is_accepted(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """NAZORAT: yaroqli poligon SAQLANADI.

    Usiz yuqoridagi ikkala rad etish testi ham `PUT` butunlay ishlamay
    qolgan holatda yashil bo'lardi.
    """
    response = await put_zones(
        api_client,
        admin_headers,
        env.camera_a,
        [zone_body(env.stalls_a[0], polygon=square_polygon(0.25, 0.75))],
    )

    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 1


async def test_zone_limit_is_enforced_server_side(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Chegaradan ortiq zona 409 `zone_limit_reached` oladi.

    ⚠ KLIENTDAGI CHEGARA (`MAX_ZONES_PER_CAMERA = 60`) QULAYLIK: bu
      so'rov brauzerni umuman ko'rmaydi. Chegara SERVERDA majburlanadi
      va aynan shu test uni o'lchaydi.

    Har zonaga BOSHQA `stall_id` kerak (aks holda `zone_stall_already_
    covered` oldinroq qaytardi va chegara sinalmay qolardi), shuning
    uchun mavjud bo'lmagan rastalar ishlatiladi: sanoq tekshiruvi
    rastalarni O'QIMASDAN, birinchi bo'lib ishlaydi.
    """
    too_many = [zone_body(uuid4()) for _ in range(61)]

    response = await put_zones(api_client, admin_headers, env.camera_a, too_many)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "zone_limit_reached"


# ===========================================================================
# 4. TENANT CHEGARASI — HAR DOIM 404
# ===========================================================================


async def test_cross_tenant_zone_returns_404(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """B bozorining zonasi bilan `DELETE` -> **404**, 403 EMAS.

    Ikkita alohida assert ATAYIN: birinchisi aynan 403 ga qarshi
    yozilgan. Faqat `== 404` bo'lganda kimdir kodni 403 ga o'zgartirsa
    xato xabari «404 kutilgan edi» deb chiqardi va SABAB (mavjudlikning
    oshkor bo'lishi) ko'rinmasdi.

    Uchinchi assert javob TANASINI ham solishtiradi: bir xil 404 ichida
    turli `detail` matni ham identifikator sanab chiqish signali bo'lardi.
    """
    foreign_zone = env.occupancy.market_b.active_zone_ids[0]
    unknown_zone = uuid4()

    foreign = await api_client.delete(f"{ZONES_URL}/{foreign_zone}", headers=admin_headers)
    unknown = await api_client.delete(f"{ZONES_URL}/{unknown_zone}", headers=admin_headers)

    assert foreign.status_code != 403, "403 zona MAVJUDLIGINI tasdiqlaydi (T-05-25)"
    assert foreign.status_code == 404, foreign.text
    assert foreign.content == unknown.content, "begona va mavjud bo'lmagan zona javobi farq qiladi"


async def test_cross_tenant_camera_returns_404(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """B bozorining `camera_id` si -> **404**, BO'SH RO'YXAT EMAS.

    ⛔ BU FARQ AMALIY, formal emas. `camera_id` — QUERY parametri, ya'ni
       u cross-tenant matritsasiga TUSHMAYDI va uni faqat shu test
       qamraydi. Kamera mavjudligi tekshirilmasa RLS 0 qator qaytarardi
       va admin o'z kamerasini «zonasiz» deb ko'rib, hammasini
       QAYTADAN chizishga tushardi — mavjud zonalar esa joyida turardi.
    """
    foreign_camera = env.occupancy.market_b.camera_id

    listed = await api_client.get(
        ZONES_URL, params={"camera_id": str(foreign_camera)}, headers=admin_headers
    )
    written = await put_zones(api_client, admin_headers, foreign_camera, [])

    assert listed.status_code == 404, listed.text
    assert written.status_code == 404, written.text


async def test_market_id_in_body_is_ignored(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Tanadagi `market_id` HECH QANDAY ta'sir qilmaydi (T-05-24).

    ⚠ MAYDON SXEMADA UMUMAN E'LON QILINMAGAN, ya'ni Pydantic uni tashlab
      yuboradi va router uni ko'rmaydi ham. Test shunga qaramay yozilgan
      va u MEXANIZMNI emas, DA'VONI o'lchaydi: qator B bozoriga emas,
      A bozoriga yozilishi kerak. Kimdir bir kun `model_config` ga
      `extra="allow"` qo'shsa yoki maydonni «qulaylik uchun» e'lon qilsa,
      darvoza AYNAN shu yerda qizaradi.
    """
    stall = env.stalls_a[0]
    foreign_market = env.base.market_b.id

    response = await put_zones(
        api_client,
        admin_headers,
        env.camera_a,
        [{**zone_body(stall, polygon=square_polygon(0.2, 0.8)), "market_id": str(foreign_market)}],
        extra={"market_id": str(foreign_market)},
    )

    assert response.status_code == 200, response.text
    rows = sync_owner_conn.execute(
        "SELECT DISTINCT market_id FROM camera_zones WHERE camera_id = %s",
        (str(env.camera_a),),
    ).fetchall()

    assert [row[0] for row in rows] == [env.market_a], (
        "so'rov tanasidagi `market_id` yozuvga ta'sir qildi"
    )


# ===========================================================================
# 5. HUQUQ — DA'VO o'lchanadi, dekorator emas
# ===========================================================================


async def test_director_cannot_replace_zones(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    env: Env,
    director_headers: dict[str, str],
) -> None:
    """`CAMERA_VIEW` bor, `CAMERA_MANAGE` yo'q -> `PUT` **403** (D-07).

    =======================================================================
    ⛔ TEST IKKI DA'VONI O'LCHAYDI, BITTASINI EMAS — VA SABAB 03-07 DA
       O'LCHANGAN.

    O'sha rejada huquq talabini dekoratordan imzoga ko'chirish HECH
    NIMANI qizartirmagan: kafolatning ikkinchi mexanizmi uni yolg'iz
    ushlab turardi. Ya'ni «403 keldi» yolg'iz o'zi huquq darvozasi
    QAYERDA turganini aytmaydi.

    Shuning uchun ikkinchi assert: rad etilgan so'rov `audit_log` da
    HECH QANDAY iz qoldirmasligi kerak. Bu FUNKSIONAL da'vo — «kim
    nimani o'zgartirdi» jurnalida bajarilmagan amal ko'rinmasligi.

    ⚠ NAZORAT: o'sha sessiya `GET` ni MUVAFFAQIYATLI bajaradi. Usiz
      test direktorning tokeni umuman ishlamayotgan holatda ham yashil
      bo'lardi va u huquq ajratmasini emas, buzilgan sessiyani
      «isbot» qilardi.
    """
    before = await audit_rows(tenant_session, env.market_a, action=AuditAction.UPDATE.value)

    forbidden = await put_zones(
        api_client, director_headers, env.camera_a, [zone_body(env.stalls_a[0])]
    )
    readable = await api_client.get(
        ZONES_URL, params={"camera_id": str(env.camera_a)}, headers=director_headers
    )

    assert forbidden.status_code == 403, forbidden.text
    assert readable.status_code == 200, "NAZORAT yiqildi: direktor o'qiy olmadi"

    after = await audit_rows(tenant_session, env.market_a, action=AuditAction.UPDATE.value)
    assert len(after) == len(before), "rad etilgan `PUT` audit jurnalida iz qoldirdi"


async def test_get_writes_no_read_audit_row(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """MUVAFFAQIYATLI `GET` dan keyin `audit_log` da o'qish yozuvi YO'Q.

    =======================================================================
    ⛔ BU DA'VO XULQ BILAN O'LCHANADI, DEKORATOR MATNI BILAN EMAS.

    `camera_zones` shaxsiy ma'lumot qaytarmaydi (na sotuvchi ismi, na
    telefoni), ya'ni D-09 uni QAMRAMAYDI. Zona muharriri esa ro'yxatni
    har surish-tortishda qayta so'raydi — auditni bu yerga yopishtirish
    jurnalni SHOVQIN bilan to'ldirib, haqiqiy o'qish hodisalarini
    (`vendor_view`, `stall_view`) ko'mib yuborardi.

    ⚠ NAZORAT JUFTI: `GET /camera-zones` HAQIQATAN ma'lumot qaytardi.
      Bo'sh javob ustida «audit qatori yo'q» da'vosi hech nimani
      isbotlamasdi — hech nima o'qilmagan bo'lsa yozuv ham bo'lmaydi.
    =======================================================================
    """
    before = await audit_rows(tenant_session, env.market_a, action=AuditAction.READ.value)

    response = await api_client.get(
        ZONES_URL, params={"camera_id": str(env.camera_a)}, headers=admin_headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["items"], "NAZORAT yiqildi: javob bo'sh, ya'ni hech nima o'qilmadi"

    after = await audit_rows(tenant_session, env.market_a, action=AuditAction.READ.value)
    assert len(after) == len(before), (
        "`GET /camera-zones` o'qish auditi yozdi — jurnal shovqin bilan to'ladi"
    )


async def test_zone_change_is_audited(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Yuqoridagining JUFTI: jadval O'ZGARISHI auditda QOLADI.

    ⛔ Ikkalasi birga bitta qarorni ifodalaydi: «o'qish auditlanmaydi,
       o'zgarish auditlanadi». Faqat birinchisi yozilsa, keyingi ijrochi
       uni «`camera_zones` audit qilinmaydi» deb o'qishi va DB
       triggerini olib tashlashi mumkin edi — o'shanda poligonni
       jimgina siljitish izsiz qolardi va bu «band, lekin to'lovsiz»
       dalilini yo'q qilishning eng arzon yo'li bo'lardi.
    """
    before = await audit_rows(tenant_session, env.market_a, action=AuditAction.INSERT.value)

    response = await put_zones(
        api_client,
        admin_headers,
        env.camera_a,
        [zone_body(env.stalls_a[0], polygon=square_polygon(0.15, 0.85))],
    )
    assert response.status_code == 200, response.text

    after = await audit_rows(tenant_session, env.market_a, action=AuditAction.INSERT.value)
    tables = {row.table_name for row in after}
    assert len(after) > len(before), "yangi versiya qatori auditda ko'rinmadi"
    assert TABLE_CAMERA_ZONES in tables


# ===========================================================================
# 6. QAMROV (D-22) — `no_coverage` «bo'sh» EMAS
# ===========================================================================


async def test_coverage_reports_uncovered_stalls(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Zonasi yo'q rasta `uncovered` da sanaladi va u «bo'sh» EMAS.

    Seed'da A bozorida olti faol rasta bor, ulardan ikkitasida zona
    chizilgan — ya'ni `covered = 2`, `uncovered = 4`. Sonlar QO'LDA
    hisoblangan va literal.
    """
    response = await api_client.get(COVERAGE_URL, headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["covered"] == 2
    assert body["uncovered"] == 4
    assert "empty" not in body, "D-22: qamrovsiz rasta «bo'sh» deb nomlanmaydi"

    # Seed nomlagan qamrovsiz rasta HAQIQATAN qamrovsiz — usiz yuqoridagi
    # sonlar shunchaki ikkita literal bo'lardi.
    assert env.occupancy.market_a.stall_without_zone_id is not None


async def test_coverage_returns_all_three_counts_when_nothing_is_uncovered(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """`uncovered == 0` bo'lganda ham UCHALA son qaytadi (UI-SPEC §6.9).

    ⛔ «Nol bo'lsa ko'rsatmaslik» tabiiy ko'rinadi va aynan jim
       yiqilishni tug'dirardi. Bu yerda teskari yo'nalish o'lchanadi:
       hamma rasta qamrab olingandan keyin ham javob TO'LIQ qoladi.

    Barcha faol rastalar bitta `PUT` bilan qamrab olinadi — ya'ni test
    holatni O'ZI quradi va seedning bugungi sonlariga bog'lanmaydi.
    """
    zones = [
        zone_body(stall, polygon=square_polygon(0.2 + 0.1 * index, 0.2))
        for index, stall in enumerate(env.stalls_a)
    ]

    saved = await put_zones(api_client, admin_headers, env.camera_a, zones)
    assert saved.status_code == 200, saved.text

    response = await api_client.get(COVERAGE_URL, headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {
        "covered": len(env.stalls_a),
        "uncovered": 0,
        "cameras_without_zones": body["cameras_without_zones"],
    }
    assert body["uncovered"] == 0
    assert isinstance(body["cameras_without_zones"], int), (
        "nol `uncovered` da uchinchi son tushib qoldi"
    )


async def test_coverage_counts_cameras_without_zones(
    api_client: httpx.AsyncClient,
    env: Env,
    admin_headers: dict[str, str],
) -> None:
    """Zonasi yo'q KAMERA alohida sanaladi (uchinchi son).

    Ikkinchi kameraning zonalari bo'sh ro'yxat bilan olib tashlanadi va
    sanoq O'SISHI kerak. Statik seed qiymatini tekshirish o'rniga
    O'TISHNI o'lchash sonni kamera sonidan mustaqil qiladi.
    """
    second_camera = env.occupancy.market_a.second_camera_id
    assert second_camera is not None

    before = await api_client.get(COVERAGE_URL, headers=admin_headers)
    assert before.status_code == 200, before.text

    cleared = await put_zones(api_client, admin_headers, second_camera, [])
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["items"] == []

    after = await api_client.get(COVERAGE_URL, headers=admin_headers)
    assert after.status_code == 200, after.text
    assert after.json()["cameras_without_zones"] == (before.json()["cameras_without_zones"] + 1)
