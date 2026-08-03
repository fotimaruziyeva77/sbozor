"""`nvr-sim` fixture'larining KELIB CHIQISHI darvozasi (Pitfall 4).

=============================================================================
BU DARVOZA NIMANI USHLAYDI:

`03-RESEARCH.md` Pitfall 4 — **`simulator-confirms-itself`**: agar sim XML'i
bizning parserimiz kutgan shaklda qo'lda yozilsa, test faqat «kod o'z
taxminiga mos» ekanini isbotlaydi. CI yashil bo'ladi, real qurilma esa qora.

Ya'ni ushlanadigan holat — **«kimdir XML'ni parserga moslab tuzatib qo'ydi»**.
Uni ko'rinadigan qiladigan uchta belgi bor va uchalasi ham shu yerda o'lchanadi:

  1. fayl haqiqiy XML bo'lib qolgani (parse bo'ladi),
  2. ildizi Hikvision oilasidagi ISAPI namespace'ida ekani — «juda toza»,
     namespace'siz XML qo'lda yozilganlikning eng ko'p uchraydigan alomati,
  3. faylda MANBA izohi borligi (repozitoriy nomi bilan).

Sim ISHGA TUSHIRILMAYDI: test faqat fayllarni o'qiydi, shuning uchun u
`tests/unit/` da va konteynerdan tashqarida ham ishlaydi.
=============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from defusedxml.ElementTree import fromstring as xml_fromstring

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "services" / "nvr-sim" / "fixtures"
README = FIXTURES_DIR / "README.md"

MIN_FIXTURES = 5
"""Darvozaning QUYI CHEGARASI.

Usiz katalog bo'shab qolganda parametrizatsiya nol testga aylanardi va
darvoza jimgina yashil bo'lib turaverardi — 03-01 da o'rnatilgan qoida:
har manifest darvozasining quyi chegarasi majburiy.
"""

ISAPI_NAMESPACES = frozenset(
    {
        "http://www.hikvision.com/ver20/XMLSchema",
        "http://www.isapi.org/ver20/XMLSchema",
    }
)
"""IKKI namespace ham HAQIQIY — bu dumpdan o'lchandi, taxmin emas.

⚠ Reja bu yerda `hikvision.com/ver20/XMLSchema` ni YAGONA qiymat deb kutgan
edi. `DS-7732NI-M4` ning yozib olingan dumpi (`@version="2.0"`) esa
`isapi.org/ver20/XMLSchema` ni ishlatadi. Fixture'ni «to'g'rilab» bitta
namespace'ga keltirish aynan Pitfall 4 ning o'zi bo'lardi: biz real
qurilmaning javobini o'z kutganimizga moslab yozgan bo'lardik va parserning
namespace-agnostik bo'lishi shartligi (Pitfall 2) sinalmasdan qolardi.

Shuning uchun mezonning NIYATI bajariladi (namespace'siz fixture yo'q), va
`test_both_isapi_namespaces_survive` ikkalasining ham korpusda qolishini
qulflaydi.
"""

EXPECTED_NAMESPACE: dict[str, str] = {
    "DS-7616NI-K2-deviceInfo.xml": "http://www.hikvision.com/ver20/XMLSchema",
    "DS-7616NI-K2-inputProxyChannels.xml": "http://www.hikvision.com/ver20/XMLSchema",
    "DS-7616NI-K2-adminAccesses.xml": "http://www.hikvision.com/ver20/XMLSchema",
    "DS-7732NI-M4-deviceInfo.xml": "http://www.isapi.org/ver20/XMLSchema",
    "DS-7732NI-M4-inputProxyChannels.xml": "http://www.isapi.org/ver20/XMLSchema",
    "DS-2CD2346G2-ISU-deviceInfo.xml": "http://www.hikvision.com/ver20/XMLSchema",
    "DS-2CD2346G2-ISU-videoInputChannels.xml": "http://www.hikvision.com/ver20/XMLSchema",
}
"""HAR FAYL uchun dumpda YOZIB OLINGAN namespace — o'zgarish darvozasi.

⚠ Korpus darajasidagi tekshiruv («ikkalasi ham bor») YETARLI EMAS: bitta faylni
`isapi.org` dan `hikvision.com` ga «to'g'rilash» korpusda ikkala qiymatni ham
qoldiradi va darvoza JIMGINA yashil bo'lib turaverardi (o'lchandi). Shuning
uchun har fayl o'z qiymati bilan qulflanadi — bu «kimdir XML'ni parserga moslab
tuzatib qo'ydi» holatini FAYL darajasida ko'rinadigan qiladi.

Yangi fixture qo'shilganda bu jadvalga ham qator qo'shiladi; unutilsa test
aytadi.
"""

SOURCE_MARKER = "hikvision_next"
"""Manba izohidagi majburiy satr — yozib olingan dumpning repozitoriysi."""

COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)


def _fixtures() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.xml"))


FIXTURES = _fixtures()


def test_fixture_directory_is_not_empty() -> None:
    """Quyi chegara: katalog bo'shab qolsa quyidagi testlar NOL marta ishlardi."""
    assert len(FIXTURES) >= MIN_FIXTURES, (
        f"`{FIXTURES_DIR}` da {len(FIXTURES)} ta `.xml` bor, kamida {MIN_FIXTURES} kutilgan. "
        "Fixture'lar yo'qolgan bo'lsa sim real dumpdan emas, o'z taxminidan javob beradi."
    )


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_fixture_parses_as_xml(fixture: Path) -> None:
    """Fayl haqiqiy XML — sim uni javob sifatida yuborishi mumkin."""
    xml_fromstring(fixture.read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_fixture_root_is_in_an_isapi_namespace(fixture: Path) -> None:
    """Ildiz tegi ISAPI namespace'ida — namespace'siz XML qo'lda yozilganlik alomati.

    Pitfall 2: `ElementTree` yorliqlarni `{ns}tag` qiladi va namespace
    e'tiborsiz qoldirilsa `find("deviceType")` **`None`** qaytaradi — kashfiyot
    esa "ulanish muvaffaqiyatli, 0 kanal topildi" deydi.
    """
    root = xml_fromstring(fixture.read_text(encoding="utf-8"))
    namespace = root.tag.partition("}")[0].lstrip("{") if root.tag.startswith("{") else ""
    assert namespace in ISAPI_NAMESPACES, (
        f"{fixture.name}: ildiz namespace'i {namespace!r} — kutilganlar: "
        f"{sorted(ISAPI_NAMESPACES)}. Namespace'siz yoki begona namespace'li fixture "
        "real qurilmadan olinmagan degani."
    )
    expected = EXPECTED_NAMESPACE.get(fixture.name)
    assert expected is not None, (
        f"{fixture.name} `EXPECTED_NAMESPACE` jadvalida yo'q. Yangi fixture qo'shilganda "
        "uning DUMPDAGI namespace'i ham qulflanadi."
    )
    assert namespace == expected, (
        f"{fixture.name}: namespace {namespace!r}, dumpda esa {expected!r} edi. "
        "Fixture TAHRIRLANGAN — bu Pitfall 4 ning aynan o'zi (`simulator-confirms-itself`). "
        "Manba bilan solishtiring: `fixtures/README.md`."
    )


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_fixture_declares_its_source(fixture: Path) -> None:
    """Faylda MANBA izohi bor — kelib chiqishi hujjatlashtirilmagan fixture qabul qilinmaydi."""
    text = fixture.read_text(encoding="utf-8")
    comments = COMMENT_RE.findall(text)
    assert comments, f"{fixture.name}: XML izohi umuman yo'q — manba qayd etilmagan"
    assert any(SOURCE_MARKER in comment for comment in comments), (
        f"{fixture.name}: izohda {SOURCE_MARKER!r} yo'q. Fixture yozib olingan dumpdan "
        "kelishi SHART (Pitfall 4); dump olinmasa taxmin OCHIQ belgilanishi kerak."
    )


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_readme_documents_every_fixture(fixture: Path) -> None:
    """`README.md` da har fixture uchun bitta qator — jadval fayllar bilan birga o'sadi."""
    readme = README.read_text(encoding="utf-8")
    assert f"`{fixture.name}`" in readme, (
        f"{fixture.name} `fixtures/README.md` jadvalida yo'q. Yangi fixture qo'shilganda "
        "manba/sana/model qatori ham qo'shiladi — aks holda kelib chiqishi yo'qoladi."
    )


def test_both_isapi_namespaces_survive() -> None:
    """Ikkala namespace ham korpusda QOLADI — «bir xillashtirish» bloklanadi.

    `DS-7616NI-K2` `hikvision.com` ni, `DS-7732NI-M4` esa `isapi.org` ni
    ishlatadi. Kimdir ularni bitta qiymatga keltirsa, parserning
    namespace-agnostik bo'lishi shartligi sinalmasdan qolardi va xato faqat
    real qurilmada ko'rinardi.
    """
    seen = set()
    for fixture in FIXTURES:
        root = xml_fromstring(fixture.read_text(encoding="utf-8"))
        if root.tag.startswith("{"):
            seen.add(root.tag.partition("}")[0].lstrip("{"))
    assert seen == ISAPI_NAMESPACES, (
        f"korpusda topilgan namespace'lar: {sorted(seen)}; kutilgan: {sorted(ISAPI_NAMESPACES)}. "
        "Ikkalasi ham HAQIQIY qurilma javobidan — birini o'chirish real farqni yashiradi."
    )


def test_device_info_fixtures_carry_the_discovery_fields() -> None:
    """A.1: `deviceInfo` dan to'rtta maydon kashfiyotga BEVOSITA kiradi.

    `deviceType` — tarmoqlanish nuqtasi (NVR -> `InputProxy`, IPCamera ->
    standalone yo'li); `model` — UI'da ko'rsatiladi; `serialNumber` — IP
    o'zgarganda ham qurilmani taniydigan barqaror identifikator;
    `firmwareVersion` — diagnostika.
    """
    required = {"model", "serialNumber", "firmwareVersion", "deviceType"}
    device_info = [f for f in FIXTURES if f.name.endswith("-deviceInfo.xml")]
    assert device_info, "birorta `*-deviceInfo.xml` fixture'i yo'q"

    device_types = set()
    for fixture in device_info:
        root = xml_fromstring(fixture.read_text(encoding="utf-8"))
        present = {child.tag.rpartition("}")[2]: (child.text or "") for child in root}
        missing = required - set(present)
        assert not missing, f"{fixture.name}: {sorted(missing)} maydon(lar)i yo'q"
        device_types.add(present["deviceType"])

    assert "NVR" in device_types, f"NVR fixture'i yo'q; topilganlar: {sorted(device_types)}"
    assert "IPCamera" in device_types, (
        f"standalone IP-kamera fixture'i yo'q; topilganlar: {sorted(device_types)}. "
        "A.1 2-qadam-B ikkinchi kashfiyot yo'lini talab qiladi."
    )


def test_admin_accesses_fixture_advertises_rtsp_with_a_port() -> None:
    """A.2: RTSP porti `adminAccesses` dan KASHF ETILADI, 554 deb taxmin qilinmaydi."""
    fixture = FIXTURES_DIR / "DS-7616NI-K2-adminAccesses.xml"
    root = xml_fromstring(fixture.read_text(encoding="utf-8"))
    protocols = {}
    for element in root:
        fields = {child.tag.rpartition("}")[2]: (child.text or "") for child in element}
        protocols[fields.get("protocol", "")] = fields.get("portNo", "")
    assert "RTSP" in protocols, f"`adminAccesses` da RTSP yo'q; topilganlar: {sorted(protocols)}"
    assert protocols["RTSP"].isdigit(), f"RTSP `portNo` raqam emas: {protocols['RTSP']!r}"


def test_input_proxy_fixture_carries_the_source_descriptor() -> None:
    """A.1: `InputProxy` — NVR'da AVTORITETLI ro'yxat; unda manba kamera tavsifi bor."""
    fixture = FIXTURES_DIR / "DS-7616NI-K2-inputProxyChannels.xml"
    root = xml_fromstring(fixture.read_text(encoding="utf-8"))
    channels = [c for c in root if c.tag.rpartition("}")[2] == "InputProxyChannel"]
    assert channels, "birorta `InputProxyChannel` yo'q"

    first = {child.tag.rpartition("}")[2]: child for child in channels[0]}
    assert "id" in first and "name" in first, f"kanal maydonlari: {sorted(first)}"
    descriptor = first.get("sourceInputPortDescriptor")
    assert descriptor is not None, "`sourceInputPortDescriptor` yo'q"
    descriptor_fields = {child.tag.rpartition("}")[2] for child in descriptor}
    assert "ipAddress" in descriptor_fields, (
        f"`ipAddress` yo'q; mavjudlari: {sorted(descriptor_fields)}. A.4 uni kalit EMAS, "
        "kuzatiladigan ATRIBUT sifatida ishlatadi (`camera_source_changed` signali)."
    )


def test_channel_list_size_attribute_is_not_trusted_by_the_corpus() -> None:
    """Real qurilma `size` atributiga ZID qiymat yuborishi mumkin — bu dumpda o'lchandi.

    `DS-7732NI-M4` da `size="14"`, `InputProxyChannel` esa **18 ta**. Bu fakt
    fixture'da SAQLANADI: kashfiyot kodi elementlarni sanashi kerak, atributga
    ishonmasligi. Kimdir «to'g'rilab» qo'ysa, bu test aytadi nima yo'qolganini.
    """
    fixture = FIXTURES_DIR / "DS-7732NI-M4-inputProxyChannels.xml"
    root = xml_fromstring(fixture.read_text(encoding="utf-8"))
    declared = root.attrib.get("size")
    actual = len([c for c in root if c.tag.rpartition("}")[2] == "InputProxyChannel"])
    assert declared is not None, "`size` atributi yo'qolgan"
    assert int(declared) != actual, (
        f"`size`={declared}, kanallar={actual} — ular endi MOS. Yuqori oqim dumpida ular "
        "zid edi (14 vs 18) va aynan shu nomuvofiqlik `size` ga ishonmaslik qoidasining "
        "yagona dalili. Fixture o'zgartirilgan bo'lsa, manba bilan solishtiring."
    )
