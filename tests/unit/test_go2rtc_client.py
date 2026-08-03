"""go2rtc `src` allow-listi — RCE darvozasining testi (D-11, T-03-45).

=============================================================================
HAR RAD ETISH YO'LI ALOHIDA TEST (`test_jwt.py` da o'rnatilgan qoida).

Bitta parametrik test ham «hammasi rad etiladi» deb yashil bo'lardi,
lekin nosozlik xabarida QAYSI protokol o'tib ketgani ko'rinmasdi.
Bu yerda esa har yo'lning O'Z nomi bor va CI ro'yxatida
`test_rejects_exec_source` alohida qator bo'lib turadi —
`03-RESEARCH.md` D.13 aynan shu nomni talab qiladi.
=============================================================================

TAHDID: GHSA-wwww-5h25-jf98 (CVSS 9.1). Frigate `PUT /api/streams` ning
`src` parametrini go2rtc'ga filtrsiz uzatgan; `exec:` protokoli esa
ixtiyoriy tizim buyrug'ini oqim manbai qiladi — natijada ikkita HTTP
so'rovi bilan konteynerda root sifatida kod ijrosi.

⚠ BU FAYL KONFIGURATSIYANI HAM O'QIYDI. Allow-list — himoyaning faqat
BIR qatlami; qolgan ikkitasi `ops/nginx/nginx.conf` va `compose.yaml`
da yashaydi va ular Python testlariga KO'RINMAYDI. Konfiguratsiya
darvozalari `test_rate_limit_proxy.py:446-460` naqshida yozilgan:
fayl o'qiladi va taqiqlangan/majburiy satr izlanadi.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.services.go2rtc import (
    GO2RTC_STREAMS_PATH,
    LIVE_VIEW_PATH,
    UNSAFE_SOURCE,
    assert_safe_go2rtc_src,
    live_view_url,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
NGINX_CONF = REPO_ROOT / "ops" / "nginx" / "nginx.conf"
COMPOSE = REPO_ROOT / "compose.yaml"
GO2RTC_CONF = REPO_ROOT / "ops" / "go2rtc" / "go2rtc.yaml"

SAFE_SOURCE = "rtsp://192.168.1.64:554/Streaming/Channels/101"
"""Mahsulot yo'lidagi HAQIQIY shakl — `rtsp_url()` ning chiqishi."""

BLOCKED_API_PATHS = ("api/streams", "api/config", "api/restart")
"""nginx darajasida `403` oladigan go2rtc yo'llari (D-11)."""


# ---------------------------------------------------------------------------
# Allow-list — HAR RAD ETISH YO'LI ALOHIDA
# ---------------------------------------------------------------------------


def test_accepts_the_rtsp_source() -> None:
    """Mahsulot yo'lidagi `rtsp://` manba O'TADI.

    IJOBIY HOLAT MAJBURIY: usiz darvozani `raise ValueError` bilan
    almashtirib qo'yish mumkin edi va barcha rad etish testlari yashil
    qolardi — jonli ko'rish esa umuman ishlamasdi.
    """
    assert_safe_go2rtc_src(SAFE_SOURCE)


def test_rejects_exec_source() -> None:
    """`exec:` RAD ETILADI — GHSA-wwww-5h25-jf98 ning AYNAN mexanizmi.

    Bu testning NOMI `03-RESEARCH.md` D.13 da nomma-nom talab qilingan:
    CI ro'yxatidagi qator xavfni o'qiydigan odamga to'g'ridan-to'g'ri
    ko'rsatadi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("exec:whoami")


def test_rejects_ffmpeg_source() -> None:
    """`ffmpeg:` RAD ETILADI — u ham tashqi jarayon ishga tushiradi."""
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("ffmpeg:rtsp://x#video=copy")


def test_rejects_echo_source() -> None:
    """`echo:` RAD ETILADI — manbani BUYRUQ CHIQISHIDAN oladi."""
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("echo:/bin/sh -c id")


def test_rejects_http_source() -> None:
    """`http://` RAD ETILADI — u o'zi zararsiz, LEKIN allow-list QAT'IY.

    `http://` bilan RCE bo'lmaydi, shuning uchun uni «zararsiz» deb
    o'tkazish vasvasasi bor. Rad etish sababi boshqa: bu YAGONA
    yo'l orqali `core-api` SSRF vositasiga aylanardi (u ichki tarmoqda
    turadi va WireGuard tunneliga ulangan), va allow-listning har
    kengayishi keyingi kengayishni oqlaydi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("http://192.168.1.64/snapshot.jpg")


def test_rejects_empty_source() -> None:
    """Bo'sh satr RAD ETILADI.

    `if not src.startswith(...)` uni allaqachon ushlaydi, LEKIN test
    kerak: kimdir darvozani `if src and not src.startswith(...)` ga
    aylantirsa (masalan «bo'sh qiymatni o'tkazib yuboraylik» degan
    niyat bilan) bo'sh `src` go2rtc'ga borardi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("")


def test_rejects_leading_whitespace_source() -> None:
    """`" rtsp://..."` RAD ETILADI — BOSH BO'SHLIQ CHETLAB O'TISH YO'LI.

    ⚠ BU TEST DARVOZANING CHEGARASINI AYNAN O'LCHAYDI. Agar kimdir
      `assert_safe_go2rtc_src` ni `src.lstrip().startswith(...)` yoki
      `src.strip().startswith(...)` ga aylantirsa, bu holat YASHIL
      bo'lib qolardi — va o'sha normalizatsiya tekshiruv bilan
      iste'molchi (go2rtc) o'rtasida FARQ tug'dirardi. Aynan shu
      farqda chetlab o'tish yashaydi (ASVS V5.3).

      Bizning `src` imiz `rtsp_url()` ning chiqishi, ya'ni bo'shliqli
      qiymat KODDA XATO borligining belgisi va uni jimgina
      «tuzatib» o'tkazib yuborish xatoni ko'rinmas qilardi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src(" rtsp://192.168.1.64:554/Streaming/Channels/101")


def test_rejects_uppercase_scheme() -> None:
    """`RTSP://` RAD ETILADI — solishtiruv REGISTRGA SEZGIR.

    `lower()`/`casefold()` qo'shish yuqoridagi bilan bir xil sinf
    xato bo'lardi: u darvoza bilan go2rtc o'rtasida yana bitta
    talqin farqini tug'dirardi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("RTSP://192.168.1.64:554/Streaming/Channels/101")


def test_rejects_scheme_embedded_later_in_the_string() -> None:
    """`exec:...rtsp://...` RAD ETILADI — tekshiruv PREFIKS bo'yicha.

    `"rtsp://" in src` shaklidagi tekshiruv bu qiymatni O'TKAZIB
    YUBORARDI va u `exec:` bilan boshlangani uchun go2rtc uni buyruq
    deb bajarardi. Nazorat holati: darvoza `in` emas, `startswith`.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("exec:ffmpeg -i rtsp://192.168.1.64/x -f rtsp {output}")


# ---------------------------------------------------------------------------
# Jonli ko'rish manzili
# ---------------------------------------------------------------------------


def test_live_view_url_carries_the_stream_name_inside_the_url() -> None:
    """`stream_name` URL ICHIDA va manzil `/live/` prefiksi ostida (UI-SPEC §8.7)."""
    url = live_view_url("cam_deadbeef", "tok.en.value")

    assert url.startswith(LIVE_VIEW_PATH), url
    assert "src=cam_deadbeef" in url
    assert "t=tok.en.value" in url


def test_live_view_path_is_under_the_authorized_prefix() -> None:
    """Manzil `/live/` ostida — ya'ni nginx unga `auth_request` qo'yadi.

    Prefiks o'zgarsa (masalan `/stream/`) manzil nginx ning
    avtorizatsiya blokidan TASHQARIDA qolardi va so'rov `location /`
    orqali frontendga ketardi: jonli ko'rish ishlamasdi, lekin
    xavfsizlik nuqsoni ham tug'ilmasdi. Bu test o'sha jimgina
    uzilishning oldini oladi.
    """
    assert LIVE_VIEW_PATH.startswith("/live/")
    assert "/live/" in NGINX_CONF.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# KONFIGURATSIYA DARVOZALARI — qolgan ikki qatlam (T-03-45)
# ---------------------------------------------------------------------------


def _go2rtc_service_lines() -> list[str]:
    """`compose.yaml` dagi `go2rtc` xizmatining KOD qatorlari (izohlarsiz).

    ⚠ IZOHLAR OLIB TASHLANADI — VA BU SHU FAZADA UCHINCHI MARTA
      TAKRORLANGAN DARSNING NATIJASI. `test_no_sim_branching` darvozasi
      03-04, 03-05 va 03-06 da uch marta izohdagi matnga urildi, chunki
      grep KODNI IZOHDAN AJRATMAYDI.

      Bu yerda ziddiyat aynan teskari tomonga ishlaydi: `compose.yaml`
      dagi izoh D-11 ni TUSHUNTIRADI va u yerda `1984` soni ATAYIN
      yozilgan (o'qiyotgan odam qaysi port haqida gap ketayotganini
      bilishi kerak). Izohlarni filtrlamasa, darvoza o'z sababini
      tushuntirgani uchun qizarardi — ya'ni u yaxshi hujjatlashni
      JAZOLARDI.
    """
    lines: list[str] = []
    inside = False
    for raw in COMPOSE.read_text(encoding="utf-8").splitlines():
        if raw.startswith("  go2rtc:"):
            inside = True
            continue
        if inside and raw and not raw.startswith("   ") and not raw.lstrip().startswith("#"):
            break
        if inside and not raw.lstrip().startswith("#"):
            lines.append(raw)
    return lines


@pytest.mark.parametrize("blocked", BLOCKED_API_PATHS)
def test_nginx_blocks_the_go2rtc_api_path(blocked: str) -> None:
    """`/api/streams|config|restart` nginx'da `403` oladi (D-11, 2-qatlam).

    Bloklar `return 403` bilan bo'lishi SHART: `deny all` 403 beradi,
    lekin `proxy_pass` bo'lgan blokda ishlamasdi va «bloklandi» degan
    yolg'on ishonch qolardi.
    """
    text = NGINX_CONF.read_text(encoding="utf-8")

    assert blocked in text, f"`{blocked}` `nginx.conf` da umuman uchramaydi"
    blocks = [
        chunk for chunk in text.split("location") if blocked in chunk and "return 403" in chunk
    ]
    assert blocks, f"`{blocked}` uchun `return 403` bo'lgan `location` bloki topilmadi"


def test_nginx_blocks_the_api_path_through_the_live_prefix() -> None:
    """`/live/api/streams` HAM bloklangan — prefiks orqali chetlab o'tish yo'li.

    ⚠ BU IKKINCHI BLOK ALOHIDA KERAK. `/live/` bloki go2rtc'ga so'rovni
      prefiksni OLIB TASHLAB uzatadi, ya'ni `/live/api/streams`
      go2rtc'ning `/api/streams` iga yetib borardi va birinchi blok
      (`^/api/...` ga langar tashlagan) uni UMUMAN ko'rmasdi.
    """
    text = NGINX_CONF.read_text(encoding="utf-8")
    blocks = [
        chunk for chunk in text.split("location") if "/live/api/" in chunk and "return 403" in chunk
    ]

    assert blocks, (
        "`/live/api/(streams|config|restart)` uchun `return 403` bloki yo'q — "
        "go2rtc API'si `/live/` prefiksi orqali ochiq qoladi"
    )


def test_nginx_declares_the_auth_request_target() -> None:
    """`/live/` bloki `auth_request` bilan darvozalangan (SC#6)."""
    text = NGINX_CONF.read_text(encoding="utf-8")

    assert "auth_request /internal/live-authz;" in text, (
        "`/live/` bloki `auth_request` e'lon qilmaydi — jonli oqim avtorizatsiyasiz ochiq qolardi"
    )
    assert "internal;" in text, (
        "`/internal/live-authz` nginx blokida `internal;` yo'q — nishonni "
        "foydalanuvchi to'g'ridan-to'g'ri chaqira olardi"
    )


def test_compose_does_not_publish_the_go2rtc_api_port() -> None:
    """go2rtc xost portiga PUBLISH QILINMAYDI (D-11, 1-qatlam).

    Uchala qatlamdan ENG MUHIMI: nginx bloklari ham, allow-list ham
    port ochiq bo'lganda hech nimani himoya qilmasdi — hujumchi
    to'g'ridan-to'g'ri `1984` ga borardi.
    """
    lines = _go2rtc_service_lines()

    assert lines, "`compose.yaml` da `go2rtc` xizmati topilmadi"
    assert not any(line.strip().startswith("ports:") for line in lines), (
        "`go2rtc` xizmatida `ports:` bandi paydo bo'ldi — bu API'ni "
        "(va u bilan birga RCE yuzasini) xostga ochadi"
    )
    assert not any("1984" in line for line in lines), (
        "go2rtc ning API porti (1984) compose'ning KODIDA ko'rinib qoldi"
    )


def test_production_go2rtc_config_has_no_exec_source() -> None:
    """Prod konfiguratsiyasida `exec:` YO'Q (sim konfiguratsiyasidan farqli).

    `go2rtc.sim.yaml` da `exec:` BOR va u xavfsiz: u `--profile sim`
    ortidagi sintetik oqim. Prod fayl esa WireGuard tunneliga ulangan
    xostda ishlaydi — u yerdagi ixtiyoriy buyruq ijrosi butun NVR
    tarmog'iga ochilgan darvoza bo'lardi.
    """
    text = GO2RTC_CONF.read_text(encoding="utf-8")
    offending = [
        line for line in text.splitlines() if "exec:" in line and not line.lstrip().startswith("#")
    ]

    assert not offending, f"prod go2rtc konfiguratsiyasida `exec:` bor: {offending}"


def test_go2rtc_streams_path_matches_the_blocked_path() -> None:
    """Kod konstantasi va nginx bloki AYNAN bir yo'lni ko'rsatadi.

    Ikkalasi jimgina ajralib ketsa (masalan go2rtc yo'lni o'zgartirsa va
    faqat kod yangilansa) nginx bloki eskirgan yo'lni himoya qilib,
    yangisini ochiq qoldirardi.
    """
    assert GO2RTC_STREAMS_PATH == "/api/streams"
    assert GO2RTC_STREAMS_PATH.lstrip("/") in BLOCKED_API_PATHS
