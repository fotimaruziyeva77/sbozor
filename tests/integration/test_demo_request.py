"""`POST /api/v1/public/demo-requests` — anonim kontraktning O'Z darvozalari (LAND-03).

=============================================================================
⛔⛔ BU FAYL `EXEMPT_ROUTES` ISTISNOSI OCHGAN QAMROVNI QAYTA TIKLAYDI.

`tests/tenancy/test_cross_tenant.py::EXEMPT_ROUTES` docstringi so'zma-so'z:
istisno marshrutni matritsadan TO'LIQ chiqaradi — tokensiz/buzilgan/muddati
o'tgan token testlari HAM qo'llanmaydi. Bu marshrut ANONIM, ya'ni token
da'volari unga printsipial jihatdan mos kelmaydi; lekin ularning o'rnini
anonim kontraktning O'Z da'volari egallashi SHART, aks holda marshrut
«istisno» degan so'z bilan butunlay sinovsiz qolardi (Tuzoq 7).

Yetti band — `10-01-PLAN.md` must_haves ro'yxatining o'zi:
  1. sessiyasiz POST -> 200 (marshrutning BUTUN ma'nosi);
  2. javobda `Set-Cookie` YO'Q;
  3. javob kalitlari to'plami AYNAN `{"delivered"}` (T-10-02);
  4. bir IP'dan 6-so'rov -> 429 `rate_limited` (T-10-01);
  5. yaroqsiz telefon -> 422 `invalid_phone` (T-10-11);
  6. honeypot -> 200, Telegram'ga AYNAN 0 chaqiruv;
  7. Telegram yiqilsa -> 502 `delivery_failed` VA DB'da 0 yangi qator
     (SPEC §12.5 «yubordik deb yolg'on aytilmaydi» + T-10-06).
=============================================================================

TELEGRAM `respx` BILAN TUTILADI (`test_alerting.py` naqshi): haqiqiy token
CI'ga BERILMAYDI (`alerts.py` 2-taqig'i) va o'lchanadigan narsa HTTP
kontrakti — nechta so'rov ketdi va tanasida nima bor.

«DB'DA 0 YANGI QATOR» HOSILA SANOQ BILAN O'LCHANADI: jadvallar ro'yxati
`pg_class` dan olinadi, ya'ni kelajakda qo'shiladigan n+1-jadval ham
avtomatik qamrovga tushadi — bitta jadvalni nomma-nom tekshirish uni
ko'rmasdi (04-13 darsi). Sanoq `sync_superuser_conn` bilan olinadi va bu
ATAYIN: `sbozor_owner` FORCE RLS ostida bo'sh GUC bilan tenant jadvalidan
0 qator ko'radi — ya'ni u bilan olingan «0 farq» hech nimani isbotlamasdi.
Superuser RLS'ni chetlab o'tadi va BARCHA qatorlarni sanaydi; bu yerda u
faqat O'QIYDI.

⚠ SEED YO'Q VA BU ATAYIN: marshrut anonim, unga bozor ham, foydalanuvchi
  ham kerak emas — `two_markets` zanjirini ko'chirish testni
  sekinlashtirardi va DB sanog'iga shovqin qo'shardi.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import respx
from app.services.alerts import TELEGRAM_API_BASE, TELEGRAM_SEND_METHOD, AlertSender
from psycopg import sql
from pydantic import SecretStr

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from redis.asyncio import Redis

pytestmark = pytest.mark.usefixtures("migrated")

DEMO_URL = "/api/v1/public/demo-requests"

TOKEN = "1234567890:TEST-TOKEN-NEVER-REAL"  # noqa: S105 - qalbaki, `respx` tutadi
CHAT_ID = "-1001234567890"
SEND_URL = f"{TELEGRAM_API_BASE}/bot{TOKEN}/{TELEGRAM_SEND_METHOD}"

RATE_IP = "203.0.113.77"
"""RFC 5737 hujjat diapazoni — rate-limit bandi O'Z IP kesimida yuguradi."""

RATE_KEY = f"rl:demo_request:{RATE_IP}"

CLIENT_PORT = 51_000


def _payload(**overrides: Any) -> dict[str, Any]:
    """Yaroqli tana; har test faqat O'ZI buzadigan maydonni almashtiradi."""
    body: dict[str, Any] = {
        "name": "Alisher Navoiy",
        "phone": "+998 90 123 45 67",
        "market_name": "Karmana dehqon bozori",
        "locale": "uz-Latn",
    }
    body.update(overrides)
    return body


def _telegram_ok() -> httpx.Response:
    return httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})


def _client_at(api_app: FastAPI, host: str) -> httpx.AsyncClient:
    """Berilgan manbadan kelayotgandek ko'rinadigan klient.

    `test_rate_limit_proxy.py::_client_at` naqshi: `ASGITransport(client=...)`
    scope'ga uvicorn `--proxy-headers` qo'yadigan juftlikni yozadi, ya'ni
    rate-limit bandi ilova ko'radigan HAQIQAT ustida yuguradi.
    """
    transport = httpx.ASGITransport(app=api_app, client=(host, CLIENT_PORT))
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def _row_counts(conn: Connection[TupleRow]) -> dict[str, int]:
    """`public` sxemasidagi HAR BIR jadvalning qator sanog'i — HOSILA ro'yxat.

    Ro'yxat `pg_class` dan tuziladi (nomma-nom emas): marshrut kelajakda
    qo'shiladigan istalgan jadvalga yozsa ham farq ko'rinadi (04-13 darsi).
    """
    tables = conn.execute(
        "SELECT c.relname FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind = 'r'"
    ).fetchall()
    counts: dict[str, int] = {}
    for (table,) in tables:
        query = sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("public", table))
        row = conn.execute(query).fetchone()
        assert row is not None
        counts[str(table)] = int(row[0])
    return counts


# ===========================================================================
# Fixture'lar
# ===========================================================================


@pytest.fixture
async def demo_sender(api_app: FastAPI) -> AsyncIterator[AlertSender]:
    """HAQIQIY `AlertSender` `app.state.sender` ga — `respx` faqat TARMOQNI tutadi.

    ⚠ MAHSULOT OBYEKTI ALMASHTIRILMAYDI (`test_alerting.py::sender` qarori):
      sirsizlik, `bool` kontrakti va HTML `parse_mode` AYNAN shu sinfning
      xulqi — soxta obyekt o'lchovni mahsulot yuzasidan uzardi.

    `api_app` fixture'i `lifespan` ni ishga tushirmaydi, shuning uchun
    `state.sender` ni prod'da lifespan to'ldirgan bo'lsa, testda SHU fixture
    to'ldiradi — `state.cache` bilan aynan bir xil almashtirish nuqtasi.
    """
    sender = AlertSender(token=SecretStr(TOKEN), chat_id=CHAT_ID, enabled=True)
    api_app.state.sender = sender
    try:
        yield sender
    finally:
        await sender.aclose()
        # `app` modul darajasidagi singleton — keyingi test moduliga
        # jo'natuvchi sizib o'tmasin.
        delattr(api_app.state, "sender")


# ===========================================================================
# 1-3. Anonim muvaffaqiyat — 200, cookie yo'q, yagona kalit
# ===========================================================================


async def test_an_anonymous_post_succeeds_without_any_session(
    api_client: httpx.AsyncClient,
    demo_sender: AlertSender,
    sync_superuser_conn: Connection[TupleRow],
) -> None:
    """Sessiyasiz, tokensiz, cookie'siz POST -> 200 `{"delivered": true}`.

    Bu marshrutning BUTUN ma'nosi: landing tashrifchisi tizimga kirmasdan
    yuboradi. Qo'shimcha nazorat — muvaffaqiyatli yo'l ham DB'ga HECH NIMA
    yozmaydi (T-10-06 faqat xato yo'liga tegishli emas).
    """
    before = _row_counts(sync_superuser_conn)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=_telegram_ok())
        response = await api_client.post(DEMO_URL, json=_payload())

    assert response.status_code == 200, response.text
    assert response.json() == {"delivered": True}
    assert route.call_count == 1, f"{route.call_count} ta Telegram chaqiruvi ketdi"
    assert _row_counts(sync_superuser_conn) == before, (
        "muvaffaqiyatli demo so'rovi DB'ga qator yozdi — marshrutning "
        "e'lon qilingan kafolati (ma'lumot saqlanmaydi) buzildi"
    )


async def test_the_response_sets_no_cookie(
    api_client: httpx.AsyncClient, demo_sender: AlertSender
) -> None:
    """Javobda `Set-Cookie` YO'Q — anonim so'rov sessiya TUG'DIRMAYDI.

    Refresh cookie faqat auth bootstrap yuzasiniki; bu yerda paydo bo'lishi
    «anonim» so'zini yolg'onga aylantirardi (T-10-02 ning cookie tomoni).
    """
    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=_telegram_ok())
        response = await api_client.post(DEMO_URL, json=_payload())

    assert response.status_code == 200, response.text
    assert "set-cookie" not in response.headers


async def test_the_response_carries_exactly_one_key(
    api_client: httpx.AsyncClient, demo_sender: AlertSender
) -> None:
    """Javob JSON kalitlari to'plami AYNAN `{"delivered"}` (T-10-02).

    ⛔ `in` bilan tekshirilmaydi, TENGLIK bilan: «`delivered` bormi?» degan
       da'vo yoniga qo'shilgan `market_id` ni KO'RMASDI — to'plam tengligi
       esa har qanday qo'shimcha kalitda qizaradi.
    """
    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=_telegram_ok())
        response = await api_client.post(DEMO_URL, json=_payload())

    assert response.status_code == 200, response.text
    assert set(response.json()) == {"delivered"}


# ===========================================================================
# 4. Rate-limit — bir IP'dan 6-so'rov 429
# ===========================================================================


async def test_the_sixth_request_from_one_ip_is_rate_limited(
    api_app: FastAPI, demo_sender: AlertSender, valkey_client: Redis
) -> None:
    """Bir IP 15 daqiqada 5 so'rov yuboradi; 6-chisi 429 `rate_limited`.

    IP kesimi `_client_at` bilan beriladi (`test_rate_limit_proxy.py`
    naqshi) — `X-Forwarded-For` sarlavhasi EMAS: ishonch qarori deploy
    qatlamida va sarlavhaning o'zi sanagichni ko'chira olmaydi.
    """
    async with respx.mock(assert_all_called=False) as router:
        router.post(SEND_URL).mock(return_value=_telegram_ok())
        async with _client_at(api_app, RATE_IP) as client:
            for attempt in range(5):
                ok = await client.post(DEMO_URL, json=_payload())
                assert ok.status_code == 200, f"{attempt + 1}-so'rov: {ok.text}"

            blocked = await client.post(DEMO_URL, json=_payload())

    try:
        assert blocked.status_code == 429, blocked.text
        assert blocked.json() == {"detail": "rate_limited"}
    finally:
        # Sanagich kaliti TOZALANADI: `valkey_client` har testda `flushdb`
        # qiladi, lekin bu modulning boshqa bandi shu fixture'siz yugursa
        # qolgan kalit unga yolg'on-429 berardi — arzon himoya.
        await valkey_client.delete(RATE_KEY)


# ===========================================================================
# 5. Yaroqsiz telefon — 422 `invalid_phone`
# ===========================================================================


async def test_a_bad_phone_returns_invalid_phone(
    api_client: httpx.AsyncClient, demo_sender: AlertSender
) -> None:
    """`+998 12` -> 422 va `detail == "invalid_phone"` — BITTA satr (LAND-03).

    Normalizatsiya SERVERDA, `phonenumbers` bilan (T-10-11): klientdagi
    qattiq regeks yolg'on rad/yolg'on qabul berardi. Kod Pydantic'ning
    standart 422 ro'yxati EMAS — marshrut qo'lda `HTTPException` ko'taradi
    (`validate_password_strength` docstringidagi qaror).

    Qo'shimcha nazorat: buzuq telefon Telegram'ga UMUMAN yetmaydi.
    """
    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=_telegram_ok())
        response = await api_client.post(DEMO_URL, json=_payload(phone="+998 12"))

    assert response.status_code == 422, response.text
    assert response.json() == {"detail": "invalid_phone"}
    assert route.call_count == 0, "buzuq telefonli so'rov Telegram'ga yetdi"


# ===========================================================================
# 6. Honeypot — jim muvaffaqiyat, Telegram'ga AYNAN 0 chaqiruv
# ===========================================================================


async def test_a_honeypot_submission_never_reaches_telegram(
    api_client: httpx.AsyncClient, demo_sender: AlertSender
) -> None:
    """`website` to'ldirilgan so'rov 200 oladi, LEKIN Telegram'ga 0 chaqiruv.

    Bot javobdan honeypot borligini o'qiy olmasligi kerak: rad kodi ham,
    boshqa javob shakli ham YO'Q — tashqaridan bu ODDIY muvaffaqiyat.
    """
    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=_telegram_ok())
        response = await api_client.post(
            DEMO_URL, json=_payload(website="http://spam.example/offer")
        )

    assert response.status_code == 200, response.text
    assert response.json() == {"delivered": True}
    assert route.call_count == 0, (
        f"honeypot so'rovi Telegram'ga {route.call_count} chaqiruv yubordi — "
        "bot endi admin kanalini spam bilan to'ldira oladi"
    )


async def test_a_honeypot_submission_skips_phone_validation(
    api_client: httpx.AsyncClient, demo_sender: AlertSender
) -> None:
    """⛔ TARTIB ISBOTI: honeypot + BUZUQ telefon ham 200 beradi, 422 EMAS.

    Honeypot tekshiruvi normalizatsiyadan OLDIN turadi (public.py 3-qadam):
    aks holda bot buzuq telefon yuborib 422 olar va honeypot mavjudligini
    javob kodidan o'qir edi — keyin maydonni chetlab o'tishni o'rganardi.
    """
    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=_telegram_ok())
        response = await api_client.post(
            DEMO_URL,
            json=_payload(phone="bu telefon emas", website="http://spam.example"),
        )

    assert response.status_code == 200, response.text
    assert response.json() == {"delivered": True}
    assert route.call_count == 0


# ===========================================================================
# 7. Telegram yiqildi — 502 `delivery_failed` VA DB'da 0 yangi qator
# ===========================================================================


async def test_a_telegram_failure_is_reported_honestly_and_writes_nothing(
    api_client: httpx.AsyncClient,
    demo_sender: AlertSender,
    sync_superuser_conn: Connection[TupleRow],
) -> None:
    """Telegram 500 qaytarsa foydalanuvchi 502 `delivery_failed` oladi.

    ⛔ «Yubordik» deb yolg'on aytilmaydi (SPEC §12.5): frontend bu kodda
       foydalanuvchiga admin telefonini ko'rsatadi — yolg'on 200 esa
       so'rovni izsiz yo'qotardi (RESEARCH B-5 aynan shu ziddiyatni yopdi).

    VA: xato yo'li ham DB'ga hech nima yozmaydi — «keyin qayta yuborish
    uchun saqlab qo'yish» kabi qulaylik T-10-06 ning buzilishi bo'lardi.
    Sanoq HOSILA (`_row_counts` docstringi) — n+1-jadval ham ko'rinadi.
    """
    before = _row_counts(sync_superuser_conn)

    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=httpx.Response(500))
        response = await api_client.post(DEMO_URL, json=_payload())

    assert response.status_code == 502, response.text
    assert response.json() == {"detail": "delivery_failed"}
    # `500` tarmoq sinfi EMAS (`_should_retry`) — qayta urinish yo'q.
    assert route.call_count == 1
    assert _row_counts(sync_superuser_conn) == before, (
        "Telegram yiqilganda so'rov DB'ga yozildi — demo so'rovi hech "
        "qanday holatda saqlanmasligi kerak (T-10-06)"
    )


# ===========================================================================
# Task 2 xulqi: Telegram matnida foydalanuvchi maydonlari HTML-qochirilgan
# ===========================================================================


async def test_user_fields_are_html_escaped_in_the_telegram_text(
    api_client: httpx.AsyncClient, demo_sender: AlertSender
) -> None:
    """⛔ T-10-04: `<b>` kiritmasi Telegram matnida `&lt;b&gt;` bo'lib chiqadi.

    `AlertSender` `parse_mode: "HTML"` bilan yuboradi (`alerts.py`), ya'ni
    anonim foydalanuvchi boshqaradigan `name` va `market_name` — HTML
    in'yeksiya yuzasi: qochirilmagan `<b>` Telegram tomonida talqin
    qilinardi, buzuq teg esa BUTUN xabarni rad ettirardi (DoS).

    Telefon esa matnga NORMALIZATSIYA qilingan E.164 shaklida tushadi —
    admin ko'radigan raqam har doim bitta yozilishda bo'ladi.
    """
    async with respx.mock(assert_all_called=False) as router:
        route = router.post(SEND_URL).mock(return_value=_telegram_ok())
        response = await api_client.post(
            DEMO_URL,
            json=_payload(
                name="<b>Zafar</b>",
                market_name='<a href="http://evil.example">Bozor</a>',
            ),
        )

    assert response.status_code == 200, response.text
    body = json.loads(route.calls.last.request.content)
    text = body["text"]

    assert "&lt;b&gt;Zafar&lt;/b&gt;" in text
    assert "&lt;a href=" in text
    # ⛔ XOM TEG UMUMAN QOLMAGAN: sarlavha va yorliqlar `<` ishlatmaydi,
    #   ya'ni matndagi HAR QANDAY `<` — qochirilmagan foydalanuvchi kirishi.
    assert "<" not in text, f"Telegram matnida xom HTML qoldi: {text!r}"
    # Normalizatsiya izi: kirishdagi `+998 90 123 45 67` E.164 bo'lib yetdi.
    assert "+998901234567" in text
    assert body["parse_mode"] == "HTML"
