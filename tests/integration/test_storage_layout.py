"""Kalit tartibi, ustiga yozish va prefiks skani — HAQIQIY SeaweedFS ustida (CAM-07, §D.9).

=============================================================================
⚠⚠ BU FAYLDA OMBOR MOCK QILINMAYDI — VA BU QOIDA `test_storage_layout_uses_no_mock`
   BILAN MEXANIK QULFLANGAN.

Sabab o'lchangan, farazga tayanmaydi. 03-14 da `go2rtc` ning
`PUT /api/streams` chaqiruvi mahsulot testlarida ALMASHTIRILGAN edi va
to'plam yashil turardi; birinchi MOCK'SIZ o'lchov esa go2rtc'ning haqiqiy
xulqini ochdi — u `:ro` konfiguratsiya bilan **400** qaytaradi, oqim esa
ro'yxatga OLINADI. Ya'ni mock ostidagi "kod media serveri bilan gaplasha
oladi" da'vosi butunlay isbotsiz edi.

Ombor qatlamida yashirinadigan narsa undan ham kattaroq:

  * **S3 imzosi** — mock'da UMUMAN hisoblanmaydi, ya'ni rekvizit,
    `region_name` va imzo versiyasi bo'yicha har qanday xato ko'rinmasdan
    qolardi;
  * **endpoint kelishuvi** — `path-style` va `virtual-host` manzillari
    o'rtasidagi farq faqat haqiqiy serverda bilinadi;
  * **sahifalash** — 1000 dan keyin kesish va davom etish tokeni ombor
    tomonining xulqi; mock uni "berilgan hammasini qaytar" deb soddalashtiradi.

Shuning uchun bu yerdagi har bir bayt haqiqiy `storage` konteyneriga boradi.
=============================================================================
⚠ TESTLAR KALITNI O'YLAB TOPMAYDI — UNI FABRIKADAN OLADI.

`object_key()` va `KEY_PREFIX_FOR_DAY()` — mahsulot kodi (04-04). O'z nomini
o'zi qurgan test `test_live_view_e2e.py` ning "nomlar mahsulotdan olinadi"
qoidasini buzardi va Pitfall 4 (simulyatorning o'zini o'zi tasdiqlashi)
bo'lardi: kalit tartibi o'zgarganda test emas, MAHSULOT sinishi kerak.
=============================================================================
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import sys
import traceback
from datetime import date, time
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from app.services import storage
from app.services.object_key import KEY_PREFIX_FOR_DAY, object_key
from app.services.storage import SnapshotStorage, StorageError
from botocore.exceptions import EndpointConnectionError  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from app.settings import Settings

pytestmark = [pytest.mark.sim]

FRAME = b"\xff\xd8\xff" + b"kadr-baytlari-" * 8
"""Sifat filtri EMAS, OMBOR o'lchanadi — shuning uchun tana sun'iy va qisqa.

Baytlarning JPEG bo'lishi bu yerda ahamiyatsiz: `storage.py` tanani
umuman ochmaydi. `\\xff\\xd8\\xff` faqat "bu kadr" degan o'quv belgisi.
"""

LONGER_FRAME = FRAME + b"-ustiga-yozilgan-ikkinchi-tana"
"""Ustiga yozish testi uchun BOSHQA UZUNLIKDAGI tana.

Uzunlik ataylab farq qiladi: bir xil uzunlikdagi ikki tana bilan
"ustiga yozildi" da'vosi `size_bytes` orqali o'lchanmasdi.
"""

DAY = date(2026, 9, 1)
NEXT_DAY = date(2026, 9, 2)

SLOTS = (time(6, 30), time(9, 0), time(12, 0))
"""Uchta slot — `04-CONTEXT.md` ning kunlik jadvali bilan bir oiladagi vaqtlar."""

PAGE_LIMIT = 1000
"""Bitta `ListObjectsV2` javobidagi kalitlar soni — O'LCHANDI, hujjatdan olinmadi.

2026-08-04, SeaweedFS 4.40: 1005 obyekt yozilgandan keyin xom `list_objects_v2`
`KeyCount=1000`, `IsTruncated=True` va davom etish tokenini qaytardi. Ya'ni
kesish shu omborga NISBATAN haqiqiy va sahifalash testi bo'sh urinish emas.
"""

OVER_ONE_PAGE = PAGE_LIMIT + 5
PAGE_WRITE_CONCURRENCY = 8
"""Sahifalash testining yozish parallelligi.

`AioConfig` ning standart ulanish puli 10 ta, ya'ni undan yuqori
parallellik navbatda kutardi va testni tezlashtirmasdi.
"""

UNREACHABLE_ENDPOINT = "http://ombor-yoq.invalid:8333"
"""Yetib bo'lmaydigan manzil — sirsizlik o'lchovi uchun.

`.invalid` — RFC 2606 bo'yicha HECH QACHON hal qilinmaydigan TLD, ya'ni
test tashqi tarmoqqa bog'lanmaydi va DNS javobi kutilmaydi.
"""

MIN_STORAGE_TESTS = 6
"""`s3_client` fixture'ini so'raydigan testlarning QUYI CHEGARASI.

Naqsh manbai `test_phase3_criteria.py:1120-1124`. Usiz kimdir testlarni
birma-bir mock'ga ko'chirsa (yoki o'chirsa) mock taqig'i YASHIL qolardi:
"bu faylda mock yo'q" da'vosi BO'SH faylda ham rost bo'ladi.
"""

_MOCK_MODULE_ROOTS = frozenset({"moto", "respx", "aioresponses", "mock", "unittest"})
"""Bu modulda IMPORT QILINISHI TAQIQLANGAN paket ildizlari (mock kutubxonalari).

⚠ Ro'yxat KOD ichida, docstringda emas — aks holda darvoza o'z izohida
  o'zini topib, hech qachon yashil bo'lmasdi.
"""

_MOCK_NAMES = frozenset({"Stubber", "patch", "MagicMock", "AsyncMock"})
"""Ildiz darajasida tutilmaydigan nomlar: ular ruxsat etilgan paketlar ichida yashaydi."""

_MODULE_PATH = Path(__file__)


async def _write_slots(
    client: SnapshotStorage,
    *,
    market_id: UUID,
    business_date: date,
    camera_id: UUID,
    slots: tuple[time, ...] = SLOTS,
) -> list[str]:
    """Bitta kameraning bir necha slotini yozadi va KALITLARNI qaytaradi."""
    keys = [
        object_key(
            market_id=market_id,
            business_date=business_date,
            camera_id=camera_id,
            slot_time=slot,
        )
        for slot in slots
    ]
    for key in keys:
        await client.put(key, FRAME)
    return keys


async def test_put_then_head_reports_the_size_and_etag(
    s3_client: SnapshotStorage, s3_markets: tuple[UUID, UUID]
) -> None:
    """Kadr omborga yoziladi va o'sha kalit bo'yicha TOPILADI (CAM-07 ning yarmi)."""
    key = object_key(
        market_id=s3_markets[0],
        business_date=DAY,
        camera_id=uuid4(),
        slot_time=SLOTS[0],
    )

    written = await s3_client.put(key, FRAME)
    assert written.size_bytes == len(FRAME)
    assert written.etag, "`put` bo'sh `etag` qaytardi"

    found = await s3_client.head(key)
    assert found is not None, "yozilgan kalit `head` da topilmadi"
    assert found.size_bytes == len(FRAME)
    assert found.etag == written.etag, "`put` va `head` ning `etag` lari mos kelmadi"


async def test_a_second_put_overwrites_the_same_object(
    s3_client: SnapshotStorage, s3_markets: tuple[UUID, UUID]
) -> None:
    """Bir xil kalitga qayta yozish — IDEMPOTENT va u kompensatsiya kodini keraksiz qiladi.

    §B.4 ning "yarim muvaffaqiyat" holati: obyekt yozildi, baza qatori esa
    yozilmadi. Kalit DETERMINISTIK bo'lgani uchun qayta bajarish O'SHA
    obyektni ustiga yozadi va izsiz tuzaladi — ya'ni "yetim obyektni topib
    o'chir, keyin qayta yoz" degan kompensatsiya kodi UMUMAN yozilmaydi.
    """
    key = object_key(
        market_id=s3_markets[0],
        business_date=DAY,
        camera_id=uuid4(),
        slot_time=SLOTS[0],
    )

    first = await s3_client.put(key, FRAME)
    second = await s3_client.put(key, LONGER_FRAME)

    assert second.size_bytes == len(LONGER_FRAME)
    assert second.etag != first.etag, "ikkinchi yozuvdan keyin `etag` o'zgarmadi"

    found = await s3_client.head(key)
    assert found is not None
    assert found.size_bytes == len(LONGER_FRAME), (
        "ustiga yozishdan keyin `head` ESKI hajmni ko'rsatdi — ikkinchi obyekt "
        "yaratilgan bo'lishi mumkin"
    )

    # ⚠ ATAYIN BOZOR PREFIKSI, KUN PREFIKSI EMAS. Bu test IDEMPOTENTLIKNI
    #   o'lchaydi; kun prefiksining o'zi esa alohida testda o'lchanadi. Kun
    #   prefiksi bu yerda ishlatilsa kalit TARTIBI o'zgarganda IKKALA test
    #   ham qizarardi va sabotaj natijasi "qaysi darvoza nimani o'lchaydi"
    #   savoliga javob bermasdi (04-04 ning 2a/2b darsi).
    keys = await s3_client.list_prefix(f"{s3_markets[0]}/")
    assert keys == [key], f"ustiga yozish {len(keys)} ta obyekt qoldirdi, bitta kutilgan edi"


async def test_get_returns_the_exact_bytes(
    s3_client: SnapshotStorage, s3_markets: tuple[UUID, UUID]
) -> None:
    """`get` — BAYT-BAYT o'sha tana. Dalil zanjiri shunga tayanadi (6-faza)."""
    key = object_key(
        market_id=s3_markets[0],
        business_date=DAY,
        camera_id=uuid4(),
        slot_time=SLOTS[1],
    )
    await s3_client.put(key, LONGER_FRAME)

    assert await s3_client.get(key) == LONGER_FRAME


async def test_the_day_prefix_finds_every_camera_of_that_day_only(
    s3_client: SnapshotStorage, s3_markets: tuple[UUID, UUID]
) -> None:
    """Kun prefiksi — retention'ning YAGONA skani (§D.9 kalit tartibi).

    ⚠ AYNAN SHU TEST `market/sana/kamera/slot` TARTIBINI o'lchaydi.
      Tartib `market/kamera/sana/slot` ga o'zgartirilsa kun prefiksi hech
      nima topmaydi va retention JIMGINA hech nima o'chirmasdi: xato yo'q,
      jurnal yozuvi yo'q, disk esa to'lib borardi.
    """
    market_id = s3_markets[0]
    first_camera, second_camera = uuid4(), uuid4()

    today_keys = await _write_slots(
        s3_client, market_id=market_id, business_date=DAY, camera_id=first_camera
    )
    today_keys += await _write_slots(
        s3_client,
        market_id=market_id,
        business_date=DAY,
        camera_id=second_camera,
        slots=(SLOTS[0],),
    )
    tomorrow_keys = await _write_slots(
        s3_client,
        market_id=market_id,
        business_date=NEXT_DAY,
        camera_id=first_camera,
        slots=(SLOTS[0],),
    )

    found = await s3_client.list_prefix(KEY_PREFIX_FOR_DAY(market_id=market_id, business_date=DAY))

    assert sorted(found) == sorted(today_keys), (
        "kun prefiksi o'sha kunning barcha kameralarini bermadi — kalit "
        "tartibi `market/sana/kamera/slot` emas"
    )
    assert not set(found) & set(tomorrow_keys), "kun prefiksi QO'SHNI kunning kalitini ushladi"


async def test_a_market_prefix_never_lists_another_market(
    s3_client: SnapshotStorage, s3_markets: tuple[UUID, UUID]
) -> None:
    """Prefiks izolyatsiyasi IKKI bozorli holatda o'lchanadi (§D.9, T-04-43).

    Bitta rekvizit BARCHA bozorlarning kadrlarini ochadi — bu QABUL QILINGAN
    xavf va u bazadagi ishonch modeli bilan bir xil (`sbozor_app` GUC bilan
    istalgan bozorga qaray oladi). Aynan shuning uchun izolyatsiya KALIT
    TARTIBIGA tayanadi va u o'lchanishi shart: bu yerda darvoza yo'q,
    struktura bor.
    """
    market_a, market_b = s3_markets
    keys_a = await _write_slots(s3_client, market_id=market_a, business_date=DAY, camera_id=uuid4())
    keys_b = await _write_slots(s3_client, market_id=market_b, business_date=DAY, camera_id=uuid4())

    found_a = await s3_client.list_prefix(f"{market_a}/")
    found_b = await s3_client.list_prefix(f"{market_b}/")

    assert sorted(found_a) == sorted(keys_a)
    assert sorted(found_b) == sorted(keys_b)
    assert not set(found_a) & set(keys_b), "A bozorining prefiksi B ning kalitini berdi"


async def test_head_returns_none_for_a_missing_key(
    s3_client: SnapshotStorage, s3_markets: tuple[UUID, UUID]
) -> None:
    """«YO'Q» va «AYTA OLMADIM» ARALASHTIRILMAYDI (`go2rtc.py:340-347` oilasi).

    Mavjud bo'lmagan kalit uchun `head` `None` beradi — istisno emas.
    Istisno faqat ombor javob bermaganda ko'tariladi, ya'ni chaqiruvchi bu
    ikki holatni ajrata oladi va "tekshira olmadim" ni "kadr yo'q" deb
    talqin qilib qo'ymaydi.
    """
    key = object_key(
        market_id=s3_markets[0],
        business_date=DAY,
        camera_id=uuid4(),
        slot_time=SLOTS[2],
    )

    assert await s3_client.head(key) is None


async def test_get_raises_a_storage_error_for_a_missing_key(
    s3_client: SnapshotStorage, s3_markets: tuple[UUID, UUID]
) -> None:
    """`get` esa YIQILADI — chunki "baytlar" savoliga bo'sh javob yo'q."""
    key = object_key(
        market_id=s3_markets[0],
        business_date=DAY,
        camera_id=uuid4(),
        slot_time=SLOTS[2],
    )

    with pytest.raises(StorageError):
        await s3_client.get(key)


@pytest.mark.slow
async def test_list_prefix_returns_every_key_beyond_the_first_page(
    s3_client: SnapshotStorage, s3_markets: tuple[UUID, UUID]
) -> None:
    """Sahifalash HAQIQIY omborda o'lchanadi — 1000 dan keyin kesish bor.

    ⚠ `slow` MARKERI ATAYIN: 1005 obyekt yozish `npm run test:sim` ning
      tez yo'lidan chetda qoladi, `pytest -q` (to'liq darvoza) esa uni
      BARIBIR bajaradi — ya'ni da'vo CI'da o'lchanadi, kundalik oqimda
      esa yo'lni to'smaydi.
    """
    market_id = s3_markets[0]
    camera_id = uuid4()
    keys = [
        f"{KEY_PREFIX_FOR_DAY(market_id=market_id, business_date=DAY)}{camera_id}/{index:05d}.jpg"
        for index in range(OVER_ONE_PAGE)
    ]
    semaphore = asyncio.Semaphore(PAGE_WRITE_CONCURRENCY)

    async def write(key: str) -> None:
        async with semaphore:
            await s3_client.put(key, b"x")

    await asyncio.gather(*(write(key) for key in keys))

    found = await s3_client.list_prefix(KEY_PREFIX_FOR_DAY(market_id=market_id, business_date=DAY))

    assert len(found) == OVER_ONE_PAGE, (
        f"{OVER_ONE_PAGE} obyektdan {len(found)} tasi qaytdi — sahifalash bir "
        f"sahifada ({PAGE_LIMIT}) to'xtab qolgan"
    )
    assert sorted(found) == sorted(keys)


async def test_a_storage_error_never_carries_the_endpoint_url(
    s3_settings: Settings,
) -> None:
    """`StorageError` OMBOR MANZILINI olib chiqmaydi — T-04-40 ning bevosita o'lchovi.

    ⚠⚠ NAZORAT HOLATI BIRINCHI: oqish yo'li HAQIQATAN mavjudligini
      o'lchamasdan "biz uni yopdik" deyish bo'sh da'vo bo'lardi.
      `EndpointConnectionError` ning O'Z matni to'liq manzilni — sxema,
      host, port, bucket va OBYEKT KALITI bilan — tashiydi (o'lchandi
      2026-08-04: `Could not connect to the endpoint URL: "http://…/…jpg"`).

    Bizning xabarimizda esa faqat UCH fakt qoladi: amal, istisno turi va
    status. Zanjir `from None` bilan uziladi, ya'ni `traceback` ham,
    Sentry ning zanjir yuruvchisi ham xom matnga bora olmaydi.
    """
    unreachable = s3_settings.model_copy(update={"s3_endpoint_url": UNREACHABLE_ENDPOINT})
    key = object_key(market_id=uuid4(), business_date=DAY, camera_id=uuid4(), slot_time=SLOTS[0])

    # NAZORAT: xom istisno manzilni HAQIQATAN tashiydi.
    raw = EndpointConnectionError(endpoint_url=f"{UNREACHABLE_ENDPOINT}/{key}")
    assert UNREACHABLE_ENDPOINT in str(raw), (
        "xom `EndpointConnectionError` manzilni tashimayapti — o'lchov o'z "
        "farazini tasdiqlayotgan bo'lardi"
    )

    async with storage.open(unreachable) as client:
        with pytest.raises(StorageError) as caught:
            await client.put(key, FRAME)

    error = caught.value
    message = str(error)
    chain = "".join(traceback.format_exception(error))

    assert UNREACHABLE_ENDPOINT not in message, "xato matnida ombor manzili qoldi"
    assert UNREACHABLE_ENDPOINT not in chain, "istisno zanjirida ombor manzili qoldi"
    assert key not in message and key not in chain, "xato matnida obyekt kaliti qoldi"
    assert s3_settings.s3_access_key not in message
    assert s3_settings.s3_secret_key.get_secret_value() not in chain
    assert error.__cause__ is None, "istisno zanjiri uzilmagan (`from None` yo'q)"
    assert error.__suppress_context__ is True
    assert "EndpointConnectionError" in message, (
        "xato matnida istisno TURI yo'q — diagnostikaning uchta faktidan biri yo'qolgan bo'lardi"
    )


def test_storage_layout_uses_no_mock() -> None:
    """MOCK'SIZ O'LCHOV DARVOZASI — §S-13.

    Ikki da'vo bir vaqtda tekshiriladi:

      1. bu modul mock kutubxonalarini IMPORT QILMAYDI;
      2. haqiqiy omborga boradigan testlar soni quyi chegaradan past emas.

    Ikkinchisisiz birinchisi ma'nosiz: testlarni birma-bir o'chirib
    yuborgan o'zgarish "mock yo'q" da'vosini BUZMASDI va darvoza bo'sh
    faylda ham yashil bo'lardi.

    Tekshiriladigan ro'yxat matnda emas, `ast` daraxtida o'qiladi: satr
    bo'yicha qidiruv izohni, docstringni va o'z konstantasini koddan
    ajrata olmasdi.
    """
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    roots: set[str] = set()
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
            imported_names |= {alias.name for alias in node.names}

    assert len(roots) >= 5, (
        f"faqat {len(roots)} ta import ildizi topildi — `ast` skaneri bo'sh "
        "daraxtda ishlayotgan bo'lsa bu darvoza JIMGINA yashil bo'lardi"
    )
    assert not roots & _MOCK_MODULE_ROOTS, (
        f"mock kutubxonasi import qilingan: {sorted(roots & _MOCK_MODULE_ROOTS)}. "
        "Bu fayl HAQIQIY SeaweedFS ustida o'lchaydi — modul docstringiga qarang"
    )
    assert not imported_names & _MOCK_NAMES, (
        f"mock vositasi import qilingan: {sorted(imported_names & _MOCK_NAMES)}"
    )

    module = sys.modules[__name__]
    users = [
        name
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_")
        and obj.__module__ == __name__
        and "s3_client" in inspect.signature(obj).parameters
    ]
    assert len(users) >= MIN_STORAGE_TESTS, (
        f"haqiqiy omborga boradigan testlar {len(users)} ta, kamida "
        f"{MIN_STORAGE_TESTS} kutilgan: {sorted(users)}"
    )
