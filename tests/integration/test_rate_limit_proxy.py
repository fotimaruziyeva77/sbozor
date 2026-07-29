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
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from app.security.ratelimit import IP_LIMIT, TooManyAttempts, check_login_rate
from fixtures.auth_api import LOGIN_URL

if TYPE_CHECKING:
    from fastapi import FastAPI
    from redis.asyncio import Redis

IP_KEY_PREFIX = "rl:login:ip:"

# RFC 5737 hujjat diapazonlari — hech qachon haqiqiy marshrutlanmaydi.
CLIENT_A_IP = "203.0.113.10"
CLIENT_B_IP = "198.51.100.7"
SPOOFED_IP = "192.0.2.66"

CLIENT_PORT = 51_000

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
