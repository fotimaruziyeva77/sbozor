"""REAL Hikvision qurilmasi ustidagi ikkinchi to'plam — FAZANI BLOKLAMAYDI.

=============================================================================
BU MARKER FAZA DARVOZASINING BIR QISMI EMAS VA ATAYIN SHUNDAY.

SC#7 aynan shuni aytadi: *«butun oqim real uskunasiz, simulyatsiya
qilingan Hikvision NVR ustida uchidan-uchiga ishlaydi va CI'da
o'lchanadi»*. ROADMAP ning 2026-08-01 dagi self-service direktivasi esa
qoidani umumlashtiradi: **tashqi bog'liqlik hech qachon `Blocks:`
bo'lmaydi.** Ya'ni real qurilmaning kelishi fazani KUTTIRA OLMAYDI.

Shuning uchun bu fayl standart zanjirdan CHETDA turadi:

    npm run test        -> `-m "not hardware"` (pyproject `addopts`)
    npm run test:sim    -> `-m "sim and not slow"` — bu fayl `sim` emas
    npm run gate        -> ikkalasini ham chaqiradi, ya'ni CHETLAB O'TADI

Ishga tushirish (rekvizitlar kelganda, QO'LDA):

    REAL_NVR_URL=http://192.168.1.64 \\
    REAL_NVR_USER=sbozor \\
    REAL_NVR_PASSWORD=... \\
    docker compose --profile test run --rm tests pytest -m hardware
=============================================================================

⚠ `skip` BU YERDA TO'G'RI — VA `-m sim` DA NOTO'G'RI EDI. Farq bitta
jumlada: **simulyator CI'da BO'LISHI SHART, real qurilma esa YO'Q.**

  `fixtures/nvr_sim.py` -> CI'da `fail`  (sim ko'tarilmagan bo'lsa bu
                                          infratuzilma nosozligi va u
                                          jimgina o'tib ketmasligi kerak)
  bu fayl                -> HAR DOIM `skip` (rekvizit yo'qligi normal
                                          holat, nosozlik emas)

Ikki markerning siyosati ATAYIN har xil va ular bir joyda izohlanadi,
chunki «skip yomon» degan umumiy qoida bu yerda noto'g'ri xulosa berardi.

=============================================================================
NIMA O'LCHANADI VA NEGA AYNAN SHULAR.

Bu to'plam mahsulotni EMAS, **simulyatorning haqiqiyligini** o'lchaydi
(Pitfall 4 — `simulator-confirms-itself`). Har test sim fixture'lari
qanday shakl kutayotganini real qurilmadan SO'RAYDI:

  1. `deviceInfo`             — model/seriya/firmware maydonlari BORMI?
  2. `InputProxy/channels`    — kanal ro'yxati o'sha shaklda kelaimi?
  3. `adminAccesses`          — RTSP porti KASHF ETILADIMI?
  4. har kanaldan bitta kadr  — 4-fazaning snapshot yo'li bugun ishlaydimi?
  5. uchta bir vaqtdagi oqim  — sessiya limiti QAYERDA (D-05, hozircha
                                `03-VALIDATION.md` da «o'lchanmagan»)?

Farq topilsa — bu **sim'ning nuqsoni**, mahsulotning emas, va u fixture'ni
yangilash bilan tuzatiladi (`ops/docs/nvr-onboarding.md` §4).
=============================================================================
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
from app.services.isapi.client import IsapiClient
from app.services.isapi.parser import parse_device_info
from app.services.rtsp import stream_id

pytestmark = pytest.mark.hardware

ENV_URL = "REAL_NVR_URL"
ENV_USER = "REAL_NVR_USER"
ENV_PASSWORD = "REAL_NVR_PASSWORD"  # noqa: S105 - o'zgaruvchi NOMI, sir emas

# ⚠ YO'LLAR `/ISAPI` PREFIKSISIZ YOZILADI — uni `IsapiClient._url()` o'zi
#   qo'shadi (`ISAPI_PREFIX`). Prefiksni ikki marta yozish `/ISAPI/ISAPI/...`
#   beradi va qurilma `404` qaytaradi, klient esa uni `nvr_isapi_unavailable`
#   deb tasniflaydi — ya'ni xato «firmware'da ISAPI yo'q» bo'lib ko'rinardi.
#   O'LCHANDI: bu aynan shu faylning birinchi yugurishida sodir bo'ldi
#   (simulyatorga qaratib sinaganda, `ops/docs/nvr-onboarding.md` §4).
DEVICE_INFO_PATH = "System/deviceInfo"
ADMIN_ACCESSES_PATH = "Security/adminAccesses"
PICTURE_PATH = "Streaming/channels/{stream}/picture"

CONCURRENT_STREAMS = 3
"""Bir vaqtda ochiladigan oqimlar soni.

Uchta — 4-fazaning eng katta bir vaqtdagi ehtiyoji (jonli ko'rish +
snapshot + zaxira). Hikvision NVR'lari odatda 6–16 masofaviy sessiyani
qo'llaydi, ya'ni uchta chegaradan ANCHA past — test «limit qayerda?»
degan savolga javob bermaydi, u «uchtasi ishlaydimi?» degan savolga
javob beradi. Haqiqiy chegara `ops/scripts/verify-real-nvr.sh` bilan
o'lchanadi.
"""

RTSP_HANDSHAKE_TIMEOUT = 10.0

JPEG_MAGIC = b"\xff\xd8\xff"
"""JPEG ning sehrli baytlari — `Content-Type` ga ISHONILMAYDI.

Hikvision xato holatida ham `image/jpeg` sarlavhasi bilan XML qaytarishi
mumkin; sarlavhaga qarab qaror qilish «kadr keldi» degan yolg'on xulosa
berardi.
"""

MIN_REAL_FRAME_BYTES = 1024
"""Shu chegaradan kichik kadr — HAQIQIY tasvir emas.

Real sub-oqim kadri (704×576, q=2) odatda 20–60 KB. Simulyatorning
`TINY_JPEG` i esa 160 bayt — ya'ni bu chegara sim va real qurilmani
ATAYIN ajratadi (izoh testning docstringida).
"""


@pytest.fixture(scope="session")
def real_nvr() -> tuple[str, str, str]:
    """`(base_url, username, password)` — muhitdan.

    ⚠ SKIP MODUL DARAJASIDA EMAS, FIXTURE'DA. `pytest.skip(...,
      allow_module_level=True)` testlarni YIG'ILISHDAN ham chiqarib
      yuborardi, ya'ni `pytest -m hardware --collect-only` BO'SH natija
      berardi va «to'plam mavjud» da'vosini tekshirib bo'lmasdi.
      Fixture'dagi skip esa yig'ishga tegmaydi: to'plam KO'RINADI,
      lekin bajarilmaydi.
    """
    url = os.environ.get(ENV_URL, "").strip()
    username = os.environ.get(ENV_USER, "").strip()
    password = os.environ.get(ENV_PASSWORD, "")

    if not (url and username and password):
        pytest.skip(
            f"real NVR rekvizitlari yo'q ({ENV_URL} / {ENV_USER} / {ENV_PASSWORD}). "
            "Bu FAZANI BLOKLAMAYDI — tartib `ops/docs/nvr-onboarding.md` §4 da."
        )
    return url, username, password


@pytest.fixture
async def client(real_nvr: tuple[str, str, str]) -> AsyncIterator[IsapiClient]:
    """Mahsulot klientining O'ZI — test uchun alohida nusxa YOZILMAYDI.

    ⚠ Bu qoida bu yerda eng muhim: agar test o'z HTTP klientini yozsa, u
      Digest handshake'ini, retry siyosatini va xato taksonomiyasini
      QAYTA amalga oshirardi — ya'ni real qurilmada MAHSULOT emas, testning
      o'z nusxasi sinalgan bo'lardi.
    """
    url, username, password = real_nvr
    async with IsapiClient(url, username, password) as isapi:
        yield isapi


async def test_device_info_is_readable(client: IsapiClient) -> None:
    """`/ISAPI/System/deviceInfo` o'qiladi va PASPORT maydonlarini beradi.

    Sim fixture'lari (`DS-7616NI-K2`, `DS-7732NI-M4`) `model` va
    `serialNumber` ni beradi, `DS-7732NI-M4` esa `manufacturer` ni
    UMUMAN BERMAYDI (03-05 ning topilmasi va u `device_not_supported`
    shartini belgilagan). Bu test o'sha topilmani REAL qurilmada
    tasdiqlaydi yoki rad etadi.
    """
    payload = await client.get_xml(DEVICE_INFO_PATH)
    device = parse_device_info(payload)

    assert device.model, f"`model` bo'sh — kashfiyot qurilmani ATAY OLMAYDI: {payload[:400]!r}"
    assert device.serial_number, "`serialNumber` bo'sh"
    print(  # dala hisoboti
        f"\nREAL deviceInfo: model={device.model!r} type={device.device_type!r} "
        f"serial={device.serial_number!r} firmware={device.firmware_version!r} "
        f"manufacturer={'BOR' if device.manufacturer else 'YO`Q'}"
    )


async def test_channel_list_has_the_expected_shape(client: IsapiClient) -> None:
    """Kanal ro'yxati o'qiladi va HAR kanalda raqam bor.

    ⚠ `@size` ATRIBUTIGA ISHONILMAYDI: `DS-7732NI-M4` dumpida
      `InputProxyChannelList size="14"`, elementlar esa 18 ta (03-02
      topilmasi). Kashfiyot elementlarni SANAYDI va bu test o'sha
      qarorni real qurilmada tasdiqlaydi.
    """
    device = parse_device_info(await client.get_xml(DEVICE_INFO_PATH))
    channels = await client.list_channels(device)

    assert channels, "kanal ro'yxati BO'SH — kashfiyot birorta kamera yaratmasdi"
    numbers = [channel.channel_no for channel in channels]
    assert all(number > 0 for number in numbers), numbers
    assert len(set(numbers)) == len(numbers), f"kanal raqamlari TAKRORLANDI: {numbers}"
    print(f"\nREAL kanallar: {len(channels)} ta -> {sorted(numbers)}")


async def test_rtsp_port_is_discovered_not_assumed(client: IsapiClient) -> None:
    """`/ISAPI/Security/adminAccesses` RTSP portini beradi.

    Bu SC#1 ning «avtomat» da'vosining eng mo'rt bo'g'ini: port topilmasa
    mahsulot 554 ga tushadi va `rtsp_port_assumed = true` qo'yadi — ya'ni
    jonli ko'rish yiqilganda BIRINCHI gumondor aynan shu (UI-SPEC §4.6).
    """
    result = await client.probe()

    assert result.ok, f"probe yiqildi: {result.error_code} / {result.error_detail}"
    assert result.rtsp_port is not None, "RTSP porti umuman qaytmadi"
    print(
        f"\nREAL RTSP porti: {result.rtsp_port} "
        f"(taxmin={'HA' if result.rtsp_port_assumed else 'YO`Q'})"
    )
    assert not result.rtsp_port_assumed, (
        f"RTSP porti TAXMIN qilindi ({result.rtsp_port}) — `{ADMIN_ACCESSES_PATH}` "
        "bu firmware'da mavjud emas yoki boshqa shaklda javob beradi. Bu SIM'NING "
        "NUQSONI: fixture portni beradi, real qurilma esa bermaydi."
    )


async def test_every_channel_returns_one_frame(client: IsapiClient) -> None:
    """Har kanaldan BITTA kadr olinadi — 4-fazaning snapshot yo'lining zondi.

    ⚠ BU TEST 3-FAZANING MEZONIDA YO'Q va ataylab shu yerda: 4-faza
      «kadr olish usuli» ni ochiq savol sifatida olib yuribdi (ISAPI
      `/picture` vs go2rtc `frame.jpeg` vs ffmpeg) va javob FAQAT real
      qurilmada o'lchanadi. Rekvizit kelgan kunning O'ZIDA bu savolga
      javob bo'lgani 4-fazani bir necha kunga tezlashtiradi.

    IKKI ALOHIDA DA'VO:

      1. **protokol** — javob HAQIQATAN JPEG (sehrli baytlar). Bu da'vo
         simulyatorda ham, real qurilmada ham bajarilishi kerak;
      2. **mazmun** — kadr PLASTMASSA emas. Simulyator `TINY_JPEG`
         (160 bayt) qaytaradi va bu ATAYIN: sim protokolni modellaydi,
         piksellarni emas. Ya'ni bu assert simulyatorga qaratilganda
         QIZARADI — va bu TO'G'RI natija: u aynan «sim'da o'lchab
         bo'lmaydigan narsa» ni nomlaydi (4-faza uchun band).
    """
    device = parse_device_info(await client.get_xml(DEVICE_INFO_PATH))
    channels = await client.list_channels(device)
    assert channels, "kanal ro'yxati bo'sh"

    sizes: dict[int, int] = {}
    failures: dict[int, str] = {}
    not_jpeg: dict[int, str] = {}
    for channel in channels:
        path = PICTURE_PATH.format(stream=stream_id(channel.channel_no, substream=False))
        try:
            frame = await client.get_xml(path)
        except Exception as exc:  # noqa: BLE001 - dala hisoboti: HAR kanal alohida
            failures[channel.channel_no] = f"{type(exc).__name__}: {exc}"
            continue
        sizes[channel.channel_no] = len(frame)
        if not frame.startswith(JPEG_MAGIC):
            not_jpeg[channel.channel_no] = repr(frame[:80])

    print(f"\nREAL kadrlar: {sizes}")
    if failures:
        print(f"REAL kadr XATOLARI: {failures}")

    # --- 1-da'vo: protokol ---
    assert sizes, f"BIRORTA kanaldan kadr olinmadi: {failures}"
    assert not not_jpeg, (
        f"javob JPEG emas (xato XML'i bo'lishi mumkin): {not_jpeg} — `/picture` "
        "yo'li bu firmware'da boshqa shaklda javob beradi"
    )

    # --- 2-da'vo: mazmun ---
    tiny = {channel: size for channel, size in sizes.items() if size < MIN_REAL_FRAME_BYTES}
    assert not tiny, (
        f"kadr(lar) {MIN_REAL_FRAME_BYTES} baytdan kichik: {tiny}. Simulyatorda bu "
        "KUTILGAN natija (`TINY_JPEG` — protokol modeli, piksel emas); REAL "
        "qurilmada esa bu kamera oqim bermayotganini bildiradi."
    )


async def test_three_concurrent_rtsp_sessions(
    client: IsapiClient, real_nvr: tuple[str, str, str]
) -> None:
    """Uchta bir vaqtdagi RTSP sessiyasi ochiladi (D-05 ning dala o'lchovi).

    ⚠ TO'LIQ RTSP KLIENTI YOZILMAYDI: `OPTIONS` so'rovi sessiya ochish
      uchun YETARLI va u qurilmaning ulanish hisoblagichini aynan shu
      tarzda oshiradi. `DESCRIBE` rekvizit talab qilardi va test bu
      yerda AUTENTIFIKATSIYANI emas, ULANISH SONINI o'lchaydi.

    Natija `03-VALIDATION.md` § «Manual-Only Verifications» ning
    «Bir vaqtdagi sessiya limiti (real qiymat)» bandiga yoziladi.
    """
    result = await client.probe()
    assert result.ok, f"probe yiqildi: {result.error_code}"
    port = result.rtsp_port or 554

    host = real_nvr[0].split("://", maxsplit=1)[-1].split("/", maxsplit=1)[0]
    host = host.split(":", maxsplit=1)[0]

    async def _open(index: int) -> str:
        reader, writer = await asyncio.open_connection(host, port)
        try:
            writer.write(f"OPTIONS rtsp://{host}:{port} RTSP/1.0\r\nCSeq: {index}\r\n\r\n".encode())
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), timeout=RTSP_HANDSHAKE_TIMEOUT)
            # Ulanish OCHIQ qoldiriladi: uchalasi BIR VAQTDA turishi kerak,
            # aks holda test ketma-ket uchta ulanishni o'lchagan bo'lardi.
            await asyncio.sleep(0.5)
            return line.decode(errors="replace").strip()
        finally:
            writer.close()
            await writer.wait_closed()

    answers = await asyncio.gather(
        *(_open(index) for index in range(1, CONCURRENT_STREAMS + 1)),
        return_exceptions=True,
    )
    print(f"\nREAL {CONCURRENT_STREAMS} ta bir vaqtdagi RTSP javobi: {answers}")

    failed = [answer for answer in answers if isinstance(answer, BaseException)]
    assert not failed, (
        f"{len(failed)}/{CONCURRENT_STREAMS} ulanish yiqildi: {failed} — sessiya limiti "
        "kutilganidan PAST bo'lishi mumkin (D-05). Bu 4-faza uchun BLOKLOVCHI: "
        "snapshot va jonli ko'rish bir vaqtda ishlashi kerak."
    )
    assert all("RTSP/1.0" in str(answer) for answer in answers), answers
