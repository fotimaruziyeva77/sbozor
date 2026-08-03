"""SC#5 ning **2-DA'VOSI**: `AllowedIPs` da `0.0.0.0/0` YO'Q (D-13, T-03-51).

=============================================================================
NEGA DA'VO UCHGA BO'LINGAN — PITFALL 10.

SC#5: *«tunnel o'chirilsa ulanish uziladi va NVR internetdan
to'g'ridan-to'g'ri ochiq emas».*

Sodda test — «tunnelni o'chir, ulanish uzilishini ko'r» — **CI'da
bajarilmaydi va YOLG'ON ISHONCH beradi**: CI konteynerida tunnel umuman
yo'q, ya'ni bunday test HAR DOIM «uzildi» deb o'tadi va HECH NIMA
isbotlamaydi. U yashil bo'lib turib, aslida hech qanday regressiyani
ushlamaydi — bu testning umuman yo'qligidan YOMONROQ.

Shuning uchun da'vo uchta MUSTAQIL qismga ajratilgan:

    1-da'vo  NVR manzili xususiy    tests/unit/test_nvr_host_validation.py  ✅ CI
    2-da'vo  AllowedIPs toza        ← SHU FAYL                              ✅ CI
    3-da'vo  Marshrut wg0 dan       ops/scripts/verify-tunnel.sh            ⚠ VPS

Ikkitasi BUGUN, USKUNASIZ o'lchanadi va aynan REGRESSIYA xavfini tutadi:
kimdir keyinroq `AllowedIPs` ni «ishlamayapti» deb kengaytirsa, CI shu
yerda qizaradi.
=============================================================================

NIMANI YO'QOTISH XAVFI BOR: `AllowedIPs = 0.0.0.0/0` VPS'ning BUTUN
chiquvchi trafigini bozor DSL'idan o'tkazadi — Telegram, Let's Encrypt
va foydalanuvchilar trafigi BIRGA o'ladi. Sertifikat yangilanmasa
platforma HTTPS'siz qoladi (T-03-51).

⚠ IKKALA TOMON HAM TEKSHIRILADI. VPS konfiguratsiyasi
`wg0.conf.example` da, bozor tomoni esa `README.md` §2 dagi `ini`
blokida (ikkita `[Interface]` bo'lgan fayl `wg-quick` uchun YAROQSIZ —
sabab `wg0.conf.example` boshida). Faqat birinchisini tekshirish bozor
tomonida `0.0.0.0/0` yozilishini ochiq qoldirardi va o'shanda bozorning
butun trafigi VPS kanaliga bog'lanib qolardi.

Naqsh manbai: `tests/integration/test_rate_limit_proxy.py` dagi
grep-darvoza — konfiguratsiya matnini o'qib taqiqlangan qiymat izlanadi.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WG_DIR = REPO_ROOT / "ops" / "wireguard"
WG_EXAMPLE = WG_DIR / "wg0.conf.example"
WG_README = WG_DIR / "README.md"
VERIFY_SCRIPT = REPO_ROOT / "ops" / "scripts" / "verify-tunnel.sh"

FULL_TUNNEL_MARKERS = ("0.0.0.0/0", "::/0")
"""TAQIQLANGAN `AllowedIPs` qiymatlari — IPv4 va IPv6.

`::/0` ni unutish klassik xato: IPv4 tomonini to'g'ri yozib, IPv6
tomonidan butun trafikni o'tkazib yuborish mumkin va nosozlik faqat
IPv6 yoqilgan xostda ko'rinadi.
"""

MINIMUM_PEERS = 2
"""Topilishi SHART bo'lgan eng kam `[Peer]` bloki soni.

QUYI CHEGARA MAJBURIY: parser noto'g'ri yozilganda (yoki fayl
ko'chirilganda) u BO'SH to'plam qaytarardi va yuqoridagi «hech qayerda
`0.0.0.0/0` yo'q» assert'i JIMGINA o'tib ketardi — darvoza o'z
mavjudligini yo'qotgan holda yashil bo'lib turaverardi. Bu 03-01 da
o'rnatilgan qoida (`test_no_sim_branching::MIN_SCANNED_FILES`).

Amaldagi son 2: VPS tomonidagi Karmana peer'i va `README.md` §2 dagi
bozor tomoni. Chegara AYNAN 2 — ikkala TOMON ham qamralishi shart va
bittasi yo'qolsa darvoza yarim ishlagan bo'lardi.
"""


@dataclass(frozen=True)
class Peer:
    """Parse qilingan `[Peer]` bloki — manba nomi bilan.

    `source` NOSOZLIK XABARI uchun: ikki fayl parse qilinadi va
    tuzatayotgan odam qaysi biriga qarashni bilishi kerak.
    """

    source: str
    body: str

    @property
    def allowed_ips(self) -> list[str]:
        """`AllowedIPs` qiymatlari — izohlar TASHLANGAN holda.

        ⚠ IZOH QATORLARI FILTRLANADI. `wg0.conf.example` ning izohlari
          `0.0.0.0/0` ni ATAYIN eslatadi («HECH QACHON yozilmaydi») —
          ya'ni xom matn bo'yicha qidiruv darvozani O'Z SABABI uchun
          qizartirardi. Bu shu fazada UCHINCHI marta takrorlangan sinf:
          `test_no_sim_branching` 03-04, 03-05 va 03-06 da aynan
          shu tarzda izohga urildi. Farq shundaki, u yerda izohni
          tuzatish to'g'ri edi, bu yerda esa — parserni.
        """
        values: list[str] = []
        for line in self.body.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            match = re.match(r"AllowedIPs\s*=\s*(.+)$", stripped)
            if match is None:
                continue
            # Qator oxiridagi izoh (`... # sabab`) ham tashlanadi.
            payload = match.group(1).split("#", 1)[0]
            values.extend(item.strip() for item in payload.split(",") if item.strip())
        return values


def _peers_of(source: str, text: str) -> list[Peer]:
    """Matndagi har `[Peer]` blokini ajratadi.

    Blok `[Peer]` dan keyingi navbatdagi bo'lim sarlavhasigacha
    (`[Interface]` / `[Peer]`) yoki matn oxirigacha davom etadi.
    """
    peers: list[Peer] = []
    chunks = re.split(r"^\s*\[Peer\]\s*$", text, flags=re.MULTILINE)
    for chunk in chunks[1:]:
        body = re.split(r"^\s*\[[A-Za-z]+\]\s*$", chunk, flags=re.MULTILINE)[0]
        peers.append(Peer(source=source, body=body))
    return peers


def _readme_ini_blocks() -> str:
    """`README.md` dagi ```ini fenced bloklarining birlashmasi.

    Bozor tomonidagi konfiguratsiya AYNAN shu yerda yashaydi va u
    darvozadan CHETDA qolmasligi kerak. Faqat `ini` bloklari o'qiladi:
    `yaml` bloki (compose bandi) ham shu faylda va u WireGuard
    konfiguratsiyasi EMAS.
    """
    return "\n".join(re.findall(r"```ini\n(.*?)```", WG_README.read_text(encoding="utf-8"), re.S))


def _all_peers() -> list[Peer]:
    return [
        *_peers_of("wg0.conf.example", WG_EXAMPLE.read_text(encoding="utf-8")),
        *_peers_of("README.md (bozor tomoni)", _readme_ini_blocks()),
    ]


PEERS = _all_peers()


# ---------------------------------------------------------------------------
# Darvozaning O'ZI ishlayotganini tekshiruvchi test
# ---------------------------------------------------------------------------


def test_parser_finds_both_sides_of_the_tunnel() -> None:
    """Parser IKKALA tomonni ham topdi — BO'SH to'plamda yashil emas.

    Bu assert qolgan hamma narsani ushlab turadi: parser buzilsa yoki
    fayl ko'chirilsa, quyidagi «taqiq» testlari bo'sh ro'yxat ustida
    ishlab, jimgina o'tib ketardi.
    """
    assert len(PEERS) >= MINIMUM_PEERS, (
        f"faqat {len(PEERS)} ta `[Peer]` topildi ({[p.source for p in PEERS]}) — "
        "parser buzilgan yoki konfiguratsiya namunasi yo'qolgan"
    )
    sources = {peer.source for peer in PEERS}
    assert len(sources) >= 2, (
        f"peer'lar bitta manbadan keldi ({sources}) — tunnelning ikkinchi tomoni "
        "darvozadan tashqarida qoldi"
    )


# ---------------------------------------------------------------------------
# ASOSIY DA'VO — SC#5 ning 2-qismi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("marker", FULL_TUNNEL_MARKERS)
def test_no_peer_allows_the_full_tunnel(marker: str) -> None:
    """Birorta `[Peer]` ham `0.0.0.0/0` (yoki `::/0`) e'lon qilmaydi (D-13).

    To'liq tunnel VPS'ning BUTUN chiquvchi trafigini bozor DSL'iga
    yo'naltiradi va Telegram, Let's Encrypt hamda foydalanuvchilar
    trafigi BIRGA o'ladi (T-03-51).
    """
    offenders = [
        f"{peer.source}: {peer.allowed_ips}" for peer in PEERS if marker in peer.allowed_ips
    ]

    assert not offenders, (
        f"`AllowedIPs` da `{marker}` topildi — bu TO'LIQ TUNNEL va u "
        "platformaning butun chiquvchi trafigini bozor internetiga bog'lab "
        f"qo'yadi (D-13):\n  " + "\n  ".join(offenders)
    )


def test_every_peer_declares_at_least_one_cidr() -> None:
    """Har peer'da kamida bitta CIDR bor.

    Bo'sh `AllowedIPs` `0.0.0.0/0` qadar xavfli EMAS (u aksincha, hech
    nimani o'tkazmaydi), lekin u konfiguratsiya xatosi: tunnel jimgina
    ishlamay qoladi va sabab «NVR javob bermayapti» bo'lib ko'rinadi.
    """
    empty = [peer.source for peer in PEERS if not peer.allowed_ips]

    assert not empty, f"`AllowedIPs` bo'sh yoki yo'q bo'lgan peer(lar): {empty}"


def test_every_allowed_ip_is_a_valid_private_cidr() -> None:
    """Har CIDR yaroqli VA xususiy diapazonda.

    IKKI DA'VO BIR TESTDA va ikkalasi ham bir xil manbadan: qiymat
    `ipaddress` bilan parse qilinadi (yaroqsiz yozuv WireGuard'ni ishga
    tushirishda yiqitardi) va natija `is_private` bo'lishi tekshiriladi.

    ⚠ IKKINCHISI `0.0.0.0/0` DAN KENGROQ DARVOZA: `128.0.0.0/1` ham
      internetning yarmini o'tkazadi va u `FULL_TUNNEL_MARKERS` ga
      tushmaydi. Ommaviy diapazonning tunnelga kiritilishi hech qanday
      qonuniy sababga ega emas — NVR ta'rifi bo'yicha xususiy tarmoqda
      (SC#5 ning 1-da'vosi).
    """
    offenders: list[str] = []
    for peer in PEERS:
        for value in peer.allowed_ips:
            try:
                network = ipaddress.ip_network(value, strict=False)
            except ValueError:
                offenders.append(f"{peer.source}: `{value}` — yaroqsiz CIDR")
                continue
            if not network.is_private:
                offenders.append(f"{peer.source}: `{value}` — OMMAVIY diapazon")

    assert not offenders, "\n  ".join(["`AllowedIPs` da muammo:", *offenders])


def test_vps_peer_has_no_endpoint() -> None:
    """VPS peer'ida `Endpoint` YO'Q — CGNAT topologiyasining mohiyati (D-14).

    Bozorning ommaviy IP'si yo'q va u o'zgaruvchan: VPS peer manzilini
    handshake'dan O'RGANADI. `Endpoint` yozilsa VPS mavjud bo'lmagan
    manzilga urinib turardi va tunnel FAQAT statik IP'li bozorlarda
    ishlardi — ya'ni Karmanada umuman ishlamasdi.
    """
    vps_peers = [peer for peer in PEERS if peer.source == "wg0.conf.example"]

    assert vps_peers, "VPS tomonida birorta peer topilmadi"
    for peer in vps_peers:
        code = [
            line.strip()
            for line in peer.body.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert not any(line.startswith("Endpoint") for line in code), (
            "VPS peer'ida `Endpoint` yozilgan — CGNAT ostidagi bozor uchun bu "
            "tunnelni butunlay ishlamas qiladi (D-14)"
        )


def test_market_side_keeps_the_nat_alive() -> None:
    """Bozor tomonida `PersistentKeepalive = 25` bor (D-14).

    Bu CGNAT'ni yengadigan YAGONA qator: har 25 soniyada bo'sh paket NAT
    yozuvini tirik saqlaydi (odatiy timeout 30–120 s). Usiz VPS bozorga
    umuman ulana olmasdi va nosozlik «bir necha daqiqa ishlaydi, keyin
    o'ladi» ko'rinishida chiqardi.
    """
    market = _readme_ini_blocks()
    values = re.findall(r"^\s*PersistentKeepalive\s*=\s*(\d+)", market, re.MULTILINE)

    assert values, "`README.md` dagi bozor namunasida `PersistentKeepalive` yo'q"
    for raw in values:
        assert 0 < int(raw) <= 30, (
            f"`PersistentKeepalive = {raw}` — NAT yozuvi (odatda 30–120 s) "
            "tirik qolmasligi mumkin; tavsiya etilgan qiymat 25"
        )


def test_no_real_key_material_is_committed() -> None:
    """Namunada FAQAT o'rin egallovchi kalitlar bor.

    WireGuard kaliti — 44 belgilik base64 (`wg genkey` chiqishi). Agar
    kimdir haqiqiy kalitni namunaga ko'chirsa, u gitga tushib qolardi va
    tunnel butunlay ochilardi. Namuna kalitlari `<...>` shaklida.
    """
    text = WG_EXAMPLE.read_text(encoding="utf-8") + _readme_ini_blocks()
    assignments = re.findall(r"^\s*(?:PrivateKey|PublicKey)\s*=\s*(\S+)", text, re.MULTILINE)

    assert assignments, "namunada birorta kalit maydoni yo'q — fayl shakli o'zgargan"
    for value in assignments:
        assert value.startswith("<") and value.endswith(">"), (
            f"kalit maydonida o'rin egallovchi emas, HAQIQIY qiymat bo'lishi mumkin: {value!r}"
        )


# ---------------------------------------------------------------------------
# 3-DA'VONING MAVJUDLIGI (skriptning O'ZI CI'da BAJARILMAYDI)
# ---------------------------------------------------------------------------


def test_verify_tunnel_script_exists_and_checks_the_route() -> None:
    """Deploy smoke-testi mavjud va u `ip route get` ni ishlatadi (3-da'vo).

    ⚠ SKRIPT BU YERDA BAJARILMAYDI. CI konteynerida `wg0` yo'q, ya'ni
      uni ishga tushirish HAR DOIM «tunnel yo'q» deb yiqilardi. Test
      faqat da'voning MAVJUDLIGINI qulflaydi: skript o'chirilsa yoki
      tekshiruv mexanikasi yo'qolsa, SC#5 ning uchinchi qismi jimgina
      hujjatsiz qolardi (Pitfall 10 ning boshqa tomoni).
    """
    assert VERIFY_SCRIPT.exists(), "`ops/scripts/verify-tunnel.sh` yo'q — 3-da'vo yo'qoldi"

    text = VERIFY_SCRIPT.read_text(encoding="utf-8")
    assert "ip route get" in text, "skript `ip route get` ni ishlatmaydi"
    assert "dev $WG_IFACE" in text, (
        "skript chiquvchi interfeysni tekshirmaydi — u marshrutning "
        "TUNNELDAN ketishini isbotlay olmaydi"
    )
    assert text.startswith("#!"), "skriptda shebang yo'q"
