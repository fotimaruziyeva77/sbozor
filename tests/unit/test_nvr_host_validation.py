"""NVR manzilining xususiy-tarmoq validatsiyasi — SC#5 ning CI qismi (T-03-23).

=============================================================================
SC#5 UCHTA DA'VOGA BO'LINGAN (`03-RESEARCH.md` C.11) VA BU FAYL BIRINCHISI.

  1. NVR manzili XUSUSIY tarmoqda        -> shu fayl, uskunasiz, BUGUN
  2. `AllowedIPs` da `0.0.0.0/0` YO'Q    -> `ops/wireguard` konfiguratsiya testi
  3. Marshrut haqiqatan tunneldan ketadi -> VPS'dagi deploy smoke-testi (03-07)

Sodda «tunnelni o'chir, uzilishini ko'r» testi ATAYIN yozilmagan: CI'da
tunnel umuman yo'q, ya'ni bunday test HAR DOIM «uzildi» deb o'tardi va
hech nimani isbotlamasdi. 1-da'vo esa aynan REGRESSIYA xavfini tutadi —
kimdir keyinroq ommaviy IP kiritsa CI qizaradi.
=============================================================================

⚠ ENG MUHIM REGRESSIYA NISHONI — `nvr-sim`.
Validator hostname'ni QABUL QILISHI shart: simulyator compose tarmog'ida
DNS nomi bilan turadi va `.local`/`.internal` nomlari ham real
o'rnatmalarda uchraydi. Validator «qattiqlashtirilib» faqat IP qabul
qiladigan bo'lsa sim ishlamay qolardi va keyingi qadam — buni sezgan
odam validatorni BUTUNLAY o'chirib qo'yishi — SC#5 ning yagona CI'dagi
da'vosini yo'q qilardi. Shuning uchun sim nomi alohida, NOMLANGAN test
sifatida ham turadi.
"""

from __future__ import annotations

import pytest
from app.services.nvr_host import (
    NvrAddressError,
    NvrHostNotPrivateError,
    assert_private_host,
    split_address,
)

# ---------------------------------------------------------------------------
# Qabul qilinadigan manzillar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("host", "why"),
    [
        ("192.168.1.64", "RFC 1918 — eng ko'p uchraydigan uy/ofis subneti"),
        ("10.0.0.5", "RFC 1918 — /8"),
        ("172.20.0.3", "RFC 1918 — Docker bridge pulidan"),
        ("100.64.0.1", "CGNAT (RFC 6598) — bozor tomonidagi operator tarmog'i"),
        ("127.0.0.1", "loopback"),
        ("169.254.10.1", "link-local"),
        ("fd00::1", "IPv6 unique local"),
    ],
)
def test_private_addresses_are_accepted(host: str, why: str) -> None:
    """Xususiy va marshrutlanmaydigan manzillar o'tadi."""
    assert_private_host(host)


@pytest.mark.parametrize("host", ["nvr.local", "nvr.internal", "nvr01", "NVR.Local"])
def test_hostnames_are_accepted(host: str) -> None:
    """Hostname MARSHRUTLANADIGAN IP EMAS — u qabul qilinadi.

    Nom qanday manzilga yechilishini bu qatlam BILMAYDI va bilishga
    urinmaydi ham: DNS so'rovi validatorni tarmoqqa bog'lab qo'yardi
    (sekin, ishonchsiz va o'zi SSRF vektori). Haqiqiy marshrut kafolati —
    WireGuard ning `AllowedIPs` i (2-da'vo).
    """
    assert_private_host(host)


def test_the_simulator_hostname_is_accepted() -> None:
    """⚠ REGRESSIYA NISHONI: `nvr-sim` HAR DOIM o'tishi kerak.

    Bu test parametrizatsiyalangan ro'yxatga QO'SHILMAGAN va bu ataylab:
    u alohida nom bilan turganda CI xabari «sim sindirildi» deb aniq
    aytadi, «11 holatdan biri qizardi» deb emas. Validatorni
    «qattiqlashtirgan» odam sababni darhol ko'radi.
    """
    assert_private_host("nvr-sim")


# ---------------------------------------------------------------------------
# Rad etiladigan manzillar (T-03-23 — SSRF)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("host", "why"),
    [
        ("8.8.8.8", "ommaviy DNS"),
        ("93.184.216.34", "ommaviy veb-server"),
        ("1.1.1.1", "ommaviy DNS"),
        ("2606:4700:4700::1111", "ommaviy IPv6"),
    ],
)
def test_public_addresses_are_rejected(host: str, why: str) -> None:
    """Marshrutlanadigan ommaviy IP RAD ETILADI.

    Bu shunchaki konfiguratsiya tekshiruvi emas: server bu manzilga
    Digest so'rov YUBORADI, ya'ni maydon SSRF vektori (T-03-23). Ommaviy
    IP kiritilsa NVR internetga ochilgan bo'lardi va SC#5 buziladi.
    """
    with pytest.raises(NvrHostNotPrivateError):
        assert_private_host(host)


def test_rejection_message_names_the_rule_not_the_address() -> None:
    """Xato QOIDANI aytadi.

    Admin `8.8.8.8` ni ataylab kiritmaydi — u odatda ommaviy IP'ni NVR'ning
    tashqi manzili deb o'ylaydi. Xabar «xato manzil» deb qolsa u boshqa
    ommaviy IP'ni sinab ko'rardi.
    """
    with pytest.raises(NvrHostNotPrivateError) as excinfo:
        assert_private_host("8.8.8.8")

    assert "8.8.8.8" in str(excinfo.value)


def test_error_is_a_value_error_subclass() -> None:
    """API qatlami uni umumiy validatsiya xatosi sifatida ham ushlay oladi.

    `phone.py::InvalidPhoneError` bilan bir xil qaror va bir xil sabab.
    """
    assert issubclass(NvrHostNotPrivateError, ValueError)


# ---------------------------------------------------------------------------
# `split_address` — UI-SPEC §4.1 jadvalining SERVER tomondagi zaxirasi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("192.168.1.64", ("192.168.1.64", 80, False)),
        ("192.168.1.64:8080", ("192.168.1.64", 8080, False)),
        ("http://192.168.1.64", ("192.168.1.64", 80, False)),
        ("https://192.168.1.64", ("192.168.1.64", 443, True)),
        ("https://192.168.1.64:8443", ("192.168.1.64", 8443, True)),
        ("nvr.local", ("nvr.local", 80, False)),
        # Ortiqcha bo'shliq va oxirgi `/` — forma maydonidan ko'chirib
        # qo'yilgan qiymatda odatiy holat.
        ("  https://nvr.local:8443/  ", ("nvr.local", 8443, True)),
        # IPv6 qavs ichida (RFC 3986) — usiz `:` ajratuvchi bilan
        # adashardi.
        ("[fd00::1]:8080", ("fd00::1", 8080, False)),
    ],
)
def test_split_address_matches_the_ui_spec_table(raw: str, expected: tuple[str, int, bool]) -> None:
    """UI-SPEC §4.1 jadvalining HAR BIR qatori.

    ⚠ Klientdagi ajratish (`zod .transform()`) — QULAYLIK; bu yerdagi —
      KONTRAKT. API to'g'ridan-to'g'ri chaqirilishi mumkin va u holda
      ajratish qoidasi ikkinchi joyda BO'LISHI shart, aks holda server
      `192.168.1.64:8080` ni butunlay hostname deb qabul qilardi.
    """
    assert split_address(raw) == expected


@pytest.mark.parametrize("raw", ["192.168.1.64:0", "192.168.1.64:70000", "192.168.1.64:-1"])
def test_split_address_rejects_out_of_range_ports(raw: str) -> None:
    """Port `1..65535` oralig'idan tashqarida bo'lsa rad etiladi."""
    with pytest.raises(NvrAddressError):
        split_address(raw)


@pytest.mark.parametrize("raw", ["", "   ", "://", "http://", "192.168.1.64:abc"])
def test_split_address_rejects_unparseable_input(raw: str) -> None:
    """O'qib bo'lmaydigan qiymat JIMGINA standart qiymatga tushmaydi.

    Bo'sh hostni `80` porti bilan qaytarish keyingi qadamda «ulanib
    bo'lmadi» xatosini berardi va sabab manzilda ekani ko'rinmasdi.
    """
    with pytest.raises(NvrAddressError):
        split_address(raw)


def test_split_address_rejects_unsupported_scheme() -> None:
    """`rtsp://` yoki `ftp://` — ISAPI manzili EMAS.

    ISAPI HTTP(S) ustida ishlaydi. `rtsp://` qabul qilinsa admin RTSP
    URL'ini NVR manzili deb kiritib, `use_tls` ni ham noto'g'ri olardi.
    """
    with pytest.raises(NvrAddressError):
        split_address("rtsp://192.168.1.64:554")


def test_split_address_does_not_validate_privacy() -> None:
    """Ajratish va tekshirish — IKKI ALOHIDA qadam.

    `split_address` ommaviy IP'ni ham ajratib beradi; rad etish
    `assert_private_host` ning ishi. Ikkalasini birlashtirish xato
    xabarini chalkashtirardi («manzilni o'qib bo'lmadi» va «ommaviy IP
    taqiqlangan» — bular admin uchun butunlay boshqa-boshqa muammolar).
    """
    assert split_address("8.8.8.8:8080") == ("8.8.8.8", 8080, False)

    with pytest.raises(NvrHostNotPrivateError):
        assert_private_host("8.8.8.8")
