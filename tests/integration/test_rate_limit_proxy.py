"""IP-kesim login sanagichi MIJOZ SCOPE'i bo'yicha ajraladi (CR-04).

=============================================================================
NEGA BU FAYL ALOHIDA YOZILGAN:

`auth.py::_client_ip` `X-Forwarded-For` ni ATAYIN o'qimaydi — sarlavhani har
kim yozishi mumkin, shuning uchun ishonch qarori DEPLOY qatlamiga (uvicorn
`--proxy-headers --forwarded-allow-ips`) topshirilgan. Bu to'g'ri qaror, lekin
u KOD ICHIDA ko'rinmaydi: compose'dagi bitta bayroq yo'qolsa, ilova jimgina
buziladi va HECH BIR mavjud test qizarmaydi.

Aynan shu bo'ldi ham: `compose.yaml` uvicornni bayroqsiz ishga tushirardi,
uvicorn esa standart bo'yicha faqat `127.0.0.1` ga ishonadi — nginx boshqa
konteyner manzilida turgani uchun uning sarlavhasi tashlab yuborilardi.
Natijada BUTUN PLATFORMA bitta `rl:login:ip:<proxy-ip>` sanagichiga tushardi;
chegara parol tekshiruvidan OLDIN ishlagani uchun muvaffaqiyatli login uni
tozalay olmasdi — ~51 anonim so'rov hammani 15 daqiqaga qulflardi.

Mavjud `test_login_rate_limit` buni ushlay olmasdi: u faqat TELEFON kesimini
sinaydi va `httpx.ASGITransport` standart `client` tuple'i bilan ishlaydi,
ya'ni har so'rov bitta IP'dan kelgandek ko'rinadi.

Bu yerdagi testlar ASGI scope'idagi `client` juftligini O'ZGARTIRADI — bu
uvicorn `--forwarded-allow-ips` bilan proxy sarlavhasini qabul qilganda
QO'YADIGAN aynan o'sha qiymat. Shu tariqa deploy-only folklor testga aylanadi.

-----------------------------------------------------------------------------
HOTFIX (01-13 regressiyasi): YUQORIDAGI YONDASHUVNING KO'R NUQTASI.

`_client_at()` scope'dagi `client` ni TO'G'RIDAN-TO'G'RI yozadi, ya'ni
`ProxyHeadersMiddleware` UMUMAN ISHGA TUSHMAYDI. Natijada middleware'ning
O'ZIDAGI nuqson bu testlarga KO'RINMAS edi — va aynan shunday nuqson ketdi:

  * `compose.yaml` `--forwarded-allow-ips *` bilan kelardi;
  * uvicorn 0.51.0 `_TrustedHosts.always_trust` holatida
    `get_trusted_client_address()` zanjirning BIRINCHI (chap) elementini
    qaytaradi;
  * nginx esa `$proxy_add_x_forwarded_for` bilan mijoz yuborgan qiymatga
    `$remote_addr` ni QO'SHARDI, ya'ni chap element MIJOZNIKI edi.

Zanjir: mijoz `X-Forwarded-For: 1.2.3.4` yuboradi -> nginx
`1.2.3.4, <haqiqiy peer>` qiladi -> uvicorn `1.2.3.4` ni oladi ->
`request.client.host` to'liq hujumchi nazoratida. Bu CR-04 yopmoqchi bo'lgan
DoS'dan og'irroq: rate-limit chetlab o'tiladi, istalgan qurbonni 15 daqiqaga
qulflash mumkin va `audit_log.ip` soxta yoziladi (FOUND-03 dalili).

Quyidagi `Hotfix` bo'limidagi testlar ilovani HAQIQIY
`ProxyHeadersMiddleware` ga o'raydi va uni SHIPPED konfiguratsiyadan
(`compose*.yml` + `ops/nginx/nginx.conf`) o'qilgan qiymatlar bilan haydaydi —
ya'ni ikkala qatlamdan biri orqaga qaytarilsa test QIZARADI.
=============================================================================
"""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx
import pytest
from app.security.ratelimit import IP_LIMIT, TooManyAttempts, check_login_rate

from fixtures.auth_api import LOGIN_URL
from tests.fixtures.nginx_conf import effective_nginx_conf
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI
    from redis.asyncio import Redis

IP_KEY_PREFIX = "rl:login:ip:"

# RFC 5737 hujjat diapazonlari — hech qachon haqiqiy marshrutlanmaydi.
CLIENT_A_IP = "203.0.113.10"
CLIENT_B_IP = "198.51.100.7"
SPOOFED_IP = "192.0.2.66"

CLIENT_PORT = 51_000

# --- Hotfix konstantalari -------------------------------------------------
# Repo ildizi: bu fayl `<root>/tests/integration/` da yotadi. Konteynerda ham
# (`working_dir: /app`, `.:/app`), xostda ham bir xil ishlaydi.
REPO_ROOT = Path(__file__).resolve().parents[2]
NGINX_CONF = REPO_ROOT / "ops" / "nginx" / "nginx.conf"
COMPOSE_FILES = (REPO_ROOT / "compose.yaml", REPO_ROOT / "compose.override.yml")

# nginx konteynerining compose bridge tarmog'idagi manzili (kuzatilgan
# `sbozor_default` = 172.19.0.0/16 ichidan). uvicorn uchun bu — PEER, ya'ni
# `--forwarded-allow-ips` ro'yxatida bo'lishi kerak bo'lgan tomon.
NGINX_PEER_IP = "172.19.0.5"

# Hujumchi `X-Forwarded-For` ga YOZMOQCHI bo'lgan qiymat.
ATTACKER_IP = SPOOFED_IP
# nginx `$remote_addr` da ko'radigan HAQIQIY peer (internetdagi mijoz).
REAL_CLIENT_IP = CLIENT_A_IP

_XFF_DIRECTIVE = re.compile(
    r"^\s*proxy_set_header\s+X-Forwarded-For\s+(?P<source>\S+?)\s*;",
    re.MULTILINE | re.IGNORECASE,
)
_ALLOW_IPS_DEFAULT = re.compile(r"\$\{FORWARDED_ALLOW_IPS:-(?P<default>[^}]*)\}")

# `+99893` — testlarda qo'llaniladigan yaroqli E.164 diapazoni. Bu raqamlarga
# foydalanuvchi YARATILMAYDI: login `401` beradi, lekin sanagich baribir
# oshadi (chegara autentifikatsiyadan oldin ishlaydi — CR-04 ning mohiyati).
PHONE_A = "+998939900001"
PHONE_B = "+998939900002"
PHONE_C = "+998939900003"

WRONG_PASSWORD = "noto-g-ri-parol"


def _client_at(api_app: FastAPI, host: str) -> httpx.AsyncClient:
    """Berilgan manbadan kelayotgandek ko'rinadigan HTTP klienti.

    `ASGITransport(client=...)` scope'ga aynan uvicorn `--proxy-headers` +
    `--forwarded-allow-ips` bilan qo'yadigan juftlikni yozadi, ya'ni test
    ilova ko'radigan HAQIQATNI takrorlaydi (sarlavhani emas).
    """
    transport = httpx.ASGITransport(app=api_app, client=(host, CLIENT_PORT))
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _failed_login(client: httpx.AsyncClient, phone: str) -> httpx.Response:
    return await client.post(LOGIN_URL, json={"phone": phone, "password": WRONG_PASSWORD})


async def _ip_keys(cache: Redis) -> list[str]:
    keys: list[bytes | str] = await cache.keys(f"{IP_KEY_PREFIX}*")
    return sorted(key.decode() if isinstance(key, bytes) else key for key in keys)


async def _counter(cache: Redis, ip: str) -> int | None:
    """`rl:login:ip:<ip>` sanagichining joriy qiymati (kalit yo'q bo'lsa `None`)."""
    raw: bytes | str | None = await cache.get(f"{IP_KEY_PREFIX}{ip}")
    return None if raw is None else int(raw)


# ---------------------------------------------------------------------------
# T-01-85: kesimlar ajraladi
# ---------------------------------------------------------------------------


async def test_distinct_client_scopes_get_independent_ip_keys(
    api_app: FastAPI, valkey_client: Redis
) -> None:
    """Ikki turli mijoz — IKKITA mustaqil `rl:login:ip:*` kaliti."""
    async with (
        _client_at(api_app, CLIENT_A_IP) as client_a,
        _client_at(api_app, CLIENT_B_IP) as client_b,
    ):
        assert (await _failed_login(client_a, PHONE_A)).status_code == 401
        assert (await _failed_login(client_b, PHONE_B)).status_code == 401

    assert await _ip_keys(valkey_client) == sorted(
        [f"{IP_KEY_PREFIX}{CLIENT_A_IP}", f"{IP_KEY_PREFIX}{CLIENT_B_IP}"]
    )
    assert await _counter(valkey_client, CLIENT_A_IP) == 1
    assert await _counter(valkey_client, CLIENT_B_IP) == 1


async def test_shared_client_scope_collapses_into_one_counter(
    api_app: FastAPI, valkey_client: Redis
) -> None:
    """Buzilgan deploy qanday ko'rinishini QAYD ETADI.

    Bayroqsiz uvicorn ostida har bir so'rov bitta manzildan (nginx'dan)
    kelgandek ko'rinardi — natija aynan shu: uchta turli telefon, bitta
    umumiy sanagich. Ya'ni platforma-keng qulflash uchun bitta mijoz yetardi.
    """
    async with _client_at(api_app, CLIENT_A_IP) as client:
        for phone in (PHONE_A, PHONE_B, PHONE_C):
            assert (await _failed_login(client, phone)).status_code == 401

    assert await _ip_keys(valkey_client) == [f"{IP_KEY_PREFIX}{CLIENT_A_IP}"]
    assert await _counter(valkey_client, CLIENT_A_IP) == 3


async def test_forwarded_header_alone_does_not_move_the_counter(
    api_app: FastAPI, valkey_client: Redis
) -> None:
    """Sarlavhaning O'ZI sanagichni ko'chira olmaydi (T-01-85 teskari tomoni).

    Bu qulf ataylab: CR-04 ni "kodda `X-Forwarded-For` ni o'qiymiz" deb
    yopishga urinish sanagichni SOXTALASHTIRISH mumkin bo'lgan qiymatga
    bog'lardi — har bir hujumchi so'rov boshiga yangi IP yozib chegaradan
    butunlay qutulardi. Ishonch qarori uvicorn (`--forwarded-allow-ips`)
    da qolishi kerak: u sarlavhani FAQAT ishonchli manbadan qabul qilib,
    scope'dagi `client` ni almashtiradi.
    """
    async with _client_at(api_app, CLIENT_A_IP) as client:
        response = await client.post(
            LOGIN_URL,
            json={"phone": PHONE_A, "password": WRONG_PASSWORD},
            headers={"X-Forwarded-For": SPOOFED_IP, "X-Real-IP": SPOOFED_IP},
        )

    assert response.status_code == 401
    assert await _ip_keys(valkey_client) == [f"{IP_KEY_PREFIX}{CLIENT_A_IP}"]
    assert await _counter(valkey_client, SPOOFED_IP) is None


# ---------------------------------------------------------------------------
# T-01-85: chegara faqat O'Z kesimini yopadi
# ---------------------------------------------------------------------------


async def test_ip_limit_on_one_scope_does_not_lock_out_another(
    api_app: FastAPI, valkey_client: Redis
) -> None:
    """Bir kesim chegaraga yetganda ikkinchisi OCHIQ qoladi (HTTP chegarasida).

    Sanagich oldindan `IP_LIMIT` ga qo'yiladi — 51 ta HTTP so'rov yuborish
    bir xil narsani isbotlab, testni Argon2 hisobiga o'nlab soniya cho'zardi.
    """
    await valkey_client.set(f"{IP_KEY_PREFIX}{CLIENT_A_IP}", IP_LIMIT)

    async with (
        _client_at(api_app, CLIENT_A_IP) as client_a,
        _client_at(api_app, CLIENT_B_IP) as client_b,
    ):
        blocked = await _failed_login(client_a, PHONE_A)
        other = await _failed_login(client_b, PHONE_B)

    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "too_many_attempts"}
    # Boshqa mijoz odatdagi `401` oladi — ya'ni qulflanmagan.
    assert other.status_code == 401


async def test_exhausted_ip_scope_leaves_other_scope_open(valkey_client: Redis) -> None:
    """Sanagich darajasidagi to'liq isbot: `IP_LIMIT` FAQAT o'z kalitiga tegishli.

    Har urinishda YANGI telefon ishlatiladi, aks holda telefon kesimi (10)
    IP kesimidan (50) oldin ishga tushib, test aslida boshqa narsani
    sinardi.
    """
    for attempt in range(IP_LIMIT):
        await check_login_rate(valkey_client, phone=f"+9989391{attempt:06d}", ip=CLIENT_A_IP)

    with pytest.raises(TooManyAttempts) as excinfo:
        await check_login_rate(valkey_client, phone="+998939200001", ip=CLIENT_A_IP)
    assert excinfo.value.scope == "ip"

    # Ikkinchi kesim TEGILMAGAN — istisno ko'tarilmaydi.
    await check_login_rate(valkey_client, phone="+998939200002", ip=CLIENT_B_IP)
    assert await _counter(valkey_client, CLIENT_B_IP) == 1


# ===========================================================================
# HOTFIX: `X-Forwarded-For` SOXTALASHTIRISHI (01-13 regressiyasi)
#
# Yuqoridagi testlar `ProxyHeadersMiddleware` ni CHETLAB O'TADI (scope'dagi
# `client` to'g'ridan-to'g'ri yoziladi). Quyidagilar esa aksincha: ilova
# HAQIQIY middleware'ga o'raladi va SHIPPED konfiguratsiya bilan haydaladi.
# ===========================================================================


def _strip_comments(text: str) -> str:
    """`#` bilan boshlanadigan qatorlarni olib tashlaydi.

    MAJBURIY: `nginx.conf` dagi tushuntirish bloki `$proxy_add_x_forwarded_for`
    ni ATAYLAB tilga oladi (nega taqiqlanganini yozadi). Taqiq esa matnga
    emas, DIREKTIVAGA tegishli — izohlarni sanamaslik kerak.
    """
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _nginx_effective_conf() -> str:
    """`nginx.conf` + u `include` qilgan fayllar — IZOHSIZ, BITTA matn.

    =======================================================================
    ⛔⛔ NEGA `include` KUZATILADI (260818, uchta test qizardi).

    Marshrutlar `ops/nginx/app.inc` ga chiqarildi (dev va prod bitta
    manbadan o'qisin degan sabab bilan). Shundan keyin bu darvoza
    `nginx.conf` ni o'qib `X-Forwarded-For` ni TOPMAY qoldi.

    ⛔ Bu darvozaning eng xavfli buzilish shakli — YASHIL qolib ko'r
       bo'lish edi: qoida boshqa faylga ko'chsa, `finditer` bo'sh
       ro'yxat qaytarardi va `assert sources` bo'lmaganida testlar
       hech nimani o'lchamay yashil turaverardi. Shuning uchun
       `assert sources` O'Z KUCHIDA qoladi VA endi include ham
       kuzatiladi: qoida qayerga ko'chsa ham, darvoza uni ko'radi.

    ⚠ Faqat REPO ICHIDAGI nisbiy include'lar o'qiladi. Konteyner
      yo'llari (`/etc/nginx/app.inc`) repo yo'liga o'giriladi —
      compose ularni shu fayllardan mount qiladi.
    =======================================================================
    """
    parts = [_strip_comments(NGINX_CONF.read_text(encoding="utf-8"))]

    for match in re.finditer(r"^\s*include\s+(?P<path>\S+);", parts[0], re.MULTILINE):
        raw = match.group("path")
        name = Path(raw).name
        candidate = NGINX_CONF.parent / name
        if candidate.is_file():
            parts.append(_strip_comments(candidate.read_text(encoding="utf-8")))

    return "\n".join(parts)


def _nginx_xff_sources() -> list[str]:
    """Shipped konfiguratsiyadagi har bir `X-Forwarded-For` manba o'zgaruvchisi."""
    return [
        str(match.group("source"))
        for match in _XFF_DIRECTIVE.finditer(_nginx_effective_conf())
    ]


def _nginx_forwards(client_supplied: str | None, *, remote_addr: str) -> str:
    """nginx SIMGA QO'YADIGAN `X-Forwarded-For` — shipped direktivadan hisoblanadi.

    Bu funksiya qiymatni QATTIQ YOZMAYDI, balki `nginx.conf` dagi haqiqiy
    o'zgaruvchidan keltirib chiqaradi. Shu sababli kimdir direktivani
    `$proxy_add_x_forwarded_for` ga qaytarsa, quyidagi testlar yangi
    (soxtalashtiriladigan) haqiqat bilan ishlaydi va QIZARADI.
    """
    sources = _nginx_xff_sources()
    assert sources, f"{NGINX_CONF} da `X-Forwarded-For` direktivasi topilmadi"
    assert len(set(sources)) == 1, f"location'lar bir-biriga zid: {sources}"

    source = sources[0]
    if source == "$remote_addr":
        # USTIGA YOZADI — mijoz yuborgan har qanday qiymat tashlanadi.
        return remote_addr
    if source == "$proxy_add_x_forwarded_for":
        # QO'SHADI — mijoz zanjirning chap tomonini o'zi to'ldiradi.
        return f"{client_supplied}, {remote_addr}" if client_supplied else remote_addr
    raise AssertionError(f"noma'lum `X-Forwarded-For` manbasi: {source!r}")


def _compose_allow_ips() -> dict[str, str]:
    """Har bir compose faylidagi `--forwarded-allow-ips` STANDART qiymati."""
    defaults: dict[str, str] = {}
    for path in COMPOSE_FILES:
        match = _ALLOW_IPS_DEFAULT.search(path.read_text(encoding="utf-8"))
        assert match is not None, f"{path.name} da `FORWARDED_ALLOW_IPS` standarti yo'q"
        defaults[path.name] = str(match.group("default"))
    return defaults


def _shipped_allow_ips() -> str:
    """Ikkala compose fayli KELISHGAN qiymat.

    `command` compose'da MERGE QILINMAYDI — u butunlay almashadi, ya'ni
    qiymat ikki joyda takrorlanadi va ular ajralib ketishi mumkin. Ajralsa —
    dev va prod turli xavfsizlik holatida qoladi.
    """
    defaults = _compose_allow_ips()
    assert len(set(defaults.values())) == 1, f"compose fayllari zid: {defaults}"
    return next(iter(defaults.values()))


def _proxied_client(api_app: FastAPI, *, trusted_hosts: str, peer_ip: str) -> httpx.AsyncClient:
    """Ilovani HAQIQIY `ProxyHeadersMiddleware` ga o'ragan klient.

    uvicorn aynan shunday qiladi: middleware ENG TASHQI qatlam bo'ladi va
    `scope["client"]` ni ilova ko'rishidan OLDIN almashtiradi. `peer_ip` —
    TCP darajasidagi haqiqiy qo'shni (compose tarmog'idagi nginx konteyneri).
    """
    proxied = ProxyHeadersMiddleware(cast("Any", api_app), trusted_hosts=trusted_hosts)
    transport = httpx.ASGITransport(app=cast("Any", proxied), client=(peer_ip, CLIENT_PORT))
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _login_through_proxy(
    api_app: FastAPI, *, forwarded_for: str, trusted_hosts: str
) -> httpx.Response:
    """`peer -> ProxyHeadersMiddleware -> ilova` zanjiri orqali muvaffaqiyatsiz login."""
    async with _proxied_client(
        api_app, trusted_hosts=trusted_hosts, peer_ip=NGINX_PEER_IP
    ) as client:
        return await client.post(
            LOGIN_URL,
            json={"phone": PHONE_A, "password": WRONG_PASSWORD},
            headers={"X-Forwarded-For": forwarded_for},
        )


# ---------------------------------------------------------------------------
# Hotfix: SHIPPED konfiguratsiya bo'yicha xulq-atvor
# ---------------------------------------------------------------------------


async def test_spoofed_forwarded_for_cannot_set_client_host(
    api_app: FastAPI, valkey_client: Redis
) -> None:
    """Mijoz yuborgan `X-Forwarded-For` `request.client.host` ni BOSHQARA OLMAYDI.

    Bu — hotfix'ning asosiy da'vosi. Zanjir shipped konfiguratsiyadan
    yig'iladi: sarlavha `ops/nginx/nginx.conf` direktivasidan hisoblanadi,
    ishonch ro'yxati esa `compose*.yml` dan o'qiladi. Ikkala qatlamdan biri
    orqaga qaytarilsa, bu test ATTACKER_IP ni ko'radi va yiqiladi.
    """
    on_the_wire = _nginx_forwards(ATTACKER_IP, remote_addr=REAL_CLIENT_IP)

    response = await _login_through_proxy(
        api_app, forwarded_for=on_the_wire, trusted_hosts=_shipped_allow_ips()
    )

    assert response.status_code == 401
    # Hujumchi tanlagan kalit UMUMAN yaratilmagan — ya'ni na chegarani
    # chetlab o'tish, na qurbonni qulflash, na soxta `audit_log.ip` mumkin.
    assert await _counter(valkey_client, ATTACKER_IP) is None
    assert await _ip_keys(valkey_client) == [f"{IP_KEY_PREFIX}{REAL_CLIENT_IP}"]


async def test_trusted_hop_still_sets_the_real_client_host(
    api_app: FastAPI, valkey_client: Redis
) -> None:
    """Zanjir SOG'LOM bo'lganda proxy bergan qiymat ISHLATILADI (CR-04 saqlanadi).

    Hotfix "hech kimga ishonmaslik" emas: nginx qo'ygan haqiqiy peer baribir
    `request.client.host` ga tushishi kerak, aks holda 01-13 tuzatgan nuqson
    (butun platforma bitta `rl:login:ip:<proxy-ip>` sanagichida) qaytardi.
    """
    on_the_wire = _nginx_forwards(None, remote_addr=REAL_CLIENT_IP)

    response = await _login_through_proxy(
        api_app, forwarded_for=on_the_wire, trusted_hosts=_shipped_allow_ips()
    )

    assert response.status_code == 401
    assert await _ip_keys(valkey_client) == [f"{IP_KEY_PREFIX}{REAL_CLIENT_IP}"]
    assert await _counter(valkey_client, REAL_CLIENT_IP) == 1
    # Proxy'ning O'Z manzili sanagich bo'lib qolmadi.
    assert await _counter(valkey_client, NGINX_PEER_IP) is None


# ---------------------------------------------------------------------------
# Hotfix: qatlamlarning MUSTAQILLIGI (defense in depth) + 01-13 qaydi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nginx_appends", "trusted_hosts", "expected_ip"),
    [
        # Ikkala qatlam joyida — asosiy holat.
        pytest.param(False, "172.16.0.0/12", REAL_CLIENT_IP, id="overwrite+cidr"),
        # FAQAT nginx qatlami: wildcard qaytarilsa ham hujumchi yuta olmaydi,
        # chunki chap element endi mijozniki emas.
        pytest.param(False, "*", REAL_CLIENT_IP, id="overwrite+wildcard"),
        # FAQAT uvicorn qatlami: nginx qo'shsa ham, aniq ro'yxat bilan uvicorn
        # zanjirni o'ngdan chapga yurib birinchi ishonchsiz hop'da to'xtaydi.
        pytest.param(True, "172.16.0.0/12", REAL_CLIENT_IP, id="append+cidr"),
        # 01-13 QAYDI: aynan shu kombinatsiya ketgan edi — hujumchi G'OLIB.
        pytest.param(True, "*", ATTACKER_IP, id="append+wildcard-REGRESSION"),
    ],
)
async def test_proxy_layers_are_independently_sufficient(
    api_app: FastAPI,
    valkey_client: Redis,
    *,
    nginx_appends: bool,
    trusted_hosts: str,
    expected_ip: str,
) -> None:
    """Har bir qatlam YAKKA O'ZI yetarli ekanini isbotlaydi.

    Qiymatlar bu yerda ATAYLAB qattiq yozilgan — bu test shipped
    konfiguratsiyani emas, MEXANIKANI qayd etadi. Oxirgi holat (`append` +
    `*`) yashil bo'lib qoladi va 01-13 dagi teshik haqiqatan ishlaganini
    hujjatlashtiradi: usul ishlamayotgani uchun emas, kombinatsiya xavfli
    bo'lgani uchun.
    """
    on_the_wire = f"{ATTACKER_IP}, {REAL_CLIENT_IP}" if nginx_appends else REAL_CLIENT_IP

    response = await _login_through_proxy(
        api_app, forwarded_for=on_the_wire, trusted_hosts=trusted_hosts
    )

    assert response.status_code == 401
    assert await _ip_keys(valkey_client) == [f"{IP_KEY_PREFIX}{expected_ip}"]


# ---------------------------------------------------------------------------
# Hotfix: shipped konfiguratsiya DARVOZALARI
# ---------------------------------------------------------------------------


def test_nginx_overwrites_forwarded_for_instead_of_appending() -> None:
    """`nginx.conf` mijoz sarlavhasini USTIGA yozadi, unga QO'SHMAYDI."""
    sources = _nginx_xff_sources()

    assert sources, f"{NGINX_CONF} da `X-Forwarded-For` direktivasi yo'q"
    # Har bir `location` uchun bittadan — biri unutilsa teshik ochiq qoladi.
    assert len(sources) == 2, f"kutilgan 2 ta direktiva, topildi: {sources}"
    assert set(sources) == {"$remote_addr"}, (
        "`X-Forwarded-For` `$remote_addr` bilan USTIGA yozilishi shart. "
        f"Topildi: {sources}. `$proxy_add_x_forwarded_for` mijozga zanjirning "
        "chap elementini yozish imkonini beradi — uvicorn `always_trust` "
        "ostida aynan o'sha element `request.client.host` ga tushadi."
    )


def test_compose_never_trusts_every_proxy() -> None:
    """`--forwarded-allow-ips` HECH QACHON `*` bo'lmaydi va CIDR sifatida yaroqli.

    `*` uvicornni `always_trust` rejimiga o'tkazadi — u holda zanjir
    O'NGDAN CHAPGA yurilmaydi, balki BIRINCHI element olinadi. Aniq tarmoq
    berilganda esa uvicorn ishonchsiz hop'ni to'g'ri topadi.
    """
    defaults = _compose_allow_ips()

    for name, value in defaults.items():
        assert value != "*", (
            f"{name}: `--forwarded-allow-ips` `*` ga qaytarilgan — "
            "bu `X-Forwarded-For` soxtalashtirishni ochadi (01-13 regressiyasi)."
        )
        # `ip_network` yaroqsiz qiymatda ValueError beradi; uvicorn esa uni
        # jimgina "literal" deb qabul qilib, HECH KIMGA ishonmay qo'yardi.
        ipaddress.ip_network(value)

    assert len(set(defaults.values())) == 1, (
        f"compose fayllari zid: {defaults}. `command` merge qilinmaydi — "
        "qiymat ikkala faylda bir xil bo'lishi shart."
    )


def test_env_example_does_not_ship_the_wildcard() -> None:
    """`.env.example` ham `*` tarqatmaydi — u har bir dev'ning `.env` iga ko'chadi."""
    env_example = REPO_ROOT / ".env.example"
    assignments = [
        line.split("=", 1)[1].strip()
        for line in _strip_comments(env_example.read_text(encoding="utf-8")).splitlines()
        if line.startswith("FORWARDED_ALLOW_IPS=")
    ]

    assert assignments, "`.env.example` da `FORWARDED_ALLOW_IPS` yo'q"
    for value in assignments:
        assert value != "*", "`.env.example` `*` tarqatmasligi shart"
        ipaddress.ip_network(value)
