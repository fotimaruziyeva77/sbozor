"""Sentry ilmoqlari — sir ILOVA CHEGARASIDAN chiqmasligining darvozasi (T-03-89).

=============================================================================
NEGA BU ALOHIDA DARVOZA KERAK.

Sentry hodisasi UCHINCHI TOMON xizmatiga ketadi, ya'ni u `structlog` dan
FARQLI o'laroq bizning nazoratimizdan butunlay chiqadi. `censor_secrets`
(1-faza) faqat KALIT nomiga qaraydi va formatlangan satr ichidagi sirni
ko'rmaydi — bu chegara `test_logging.py::test_password_inside_a_formatted_
message_is_NOT_masked` da ochiq hujjatlashtirilgan.

03-13 dan boshlab jonli ko'rish yo'li go2rtc'ga REKVIZITLI RTSP manbaini
yuboradi (`?src=rtsp://admin:PAROL@nvr/...`), ya'ni sir Sentry hodisasiga
KAMIDA UCH joydan tushishi mumkin:

    exception.values[].value      — `httpx` istisnosining matni
    request.query_string          — kiruvchi so'rovning query satri
    stacktrace.frames[].vars      — freym lokallari (`include_local_variables`)

va bularning HAMMASIDAN OLDIN — breadcrumb sifatida, hodisa umuman yuz
bermasdan turib.
=============================================================================

⚠ BU FAYL ILMOQLARNI TO'G'RIDAN-TO'G'RI CHAQIRADI, `sentry_sdk.init()` NI
  EMAS. Haqiqiy SDK'ni ko'tarish tarmoq transporti va global holat
  qo'shardi; o'lchanayotgan narsa esa AYNAN ikkita sof funksiya.
  Ularning `init()` ga ULANGANI alohida test bilan qulflanadi.
"""

from __future__ import annotations

import inspect
from typing import Any, cast

import pytest
from app.main import _PII_KEYS, MASKED, _scrub_breadcrumb, _scrub_event, lifespan
from sentry_sdk.types import Breadcrumb, BreadcrumbHint, Event, Hint

SECRET = "Sekret123"  # noqa: S105 - test uskunasi

RAW_SOURCE = f"rtsp://admin:{SECRET}@nvr.invalid:554/Streaming/Channels/102"
"""XOM shakl — freym lokallarida aynan shunday turadi."""

ENCODED_QUERY = "name=cam_deadbeef&src=rtsp%3A%2F%2Fadmin%3A" + SECRET + "%40nvr.invalid%3A554%2Fx"
"""`httpx` CHIQUVCHI so'rovda hosil qiladigan shakl — O'LCHANGAN, taxmin emas.

⚠ AYNAN SHU SHAKL `rtsp://` naqshi bilan TOPILMAYDI: sxema ham, `@` ham
  percent-encoded. Shuning uchun query darajasidagi qoida (`src=` dan `&`
  gacha) MAJBURIY va uni `rtsp://` qoidasi bilan almashtirib bo'lmaydi.
"""

REQUEST_URL = f"http://go2rtc:1984/api/streams?{ENCODED_QUERY}"


def _event(**fields: Any) -> Event:
    return cast("Event", dict(fields))


def _crumb(**fields: Any) -> Breadcrumb:
    return cast("Breadcrumb", dict(fields))


def _hint() -> Hint:
    return cast("Hint", {})


def _breadcrumb_hint() -> BreadcrumbHint:
    return cast("BreadcrumbHint", {})


def _scrubbed(crumb: Breadcrumb) -> Breadcrumb:
    result = _scrub_breadcrumb(crumb, _breadcrumb_hint())
    assert result is not None, "breadcrumb butunlay tashlab yuborildi"
    return result


# ---------------------------------------------------------------------------
# `before_breadcrumb` — UCHINCHI OQISH YO'LI (T-03-89)
# ---------------------------------------------------------------------------


def test_http_breadcrumb_url_loses_the_rtsp_credentials() -> None:
    """CHIQUVCHI so'rov breadcrumb'idagi URL'dan sir OLIB TASHLANADI.

    =======================================================================
    ⚠⚠ SABOTAJ NISHONI (S4). Bu ilmoq olib tashlansa parol Sentry'ga
      hodisa YUZ BERMASDAN TURIB ketardi: breadcrumb muvaffaqiyatli
      chaqiruvda ham yoziladi va keyingi ISTALGAN xato bilan birga
      yuboriladi.
    =======================================================================
    """
    crumb = _crumb(
        type="http",
        category="httplib",
        data={"method": "PUT", "url": REQUEST_URL, "status_code": 400},
    )

    result = _scrubbed(crumb)

    data = result["data"]
    assert isinstance(data, dict)
    assert SECRET not in str(data["url"]), "breadcrumb URL'ida parol qoldi (T-03-89)"
    assert MASKED in str(data["url"])
    # Diagnostika SAQLANADI: qaysi metod, qaysi status, qaysi yo'l.
    assert data["method"] == "PUT"
    assert data["status_code"] == 400
    assert "/api/streams" in str(data["url"])


def test_http_breadcrumb_query_field_is_masked_too() -> None:
    """`http.query` ALOHIDA maydon sifatida ham keladi va u ham tozalanadi.

    ⚠ NAZORAT: `sentry-sdk` httpx integratsiyasi URL'ni query'siz, query'ni
      esa ALOHIDA kalitda yozishi mumkin. Faqat `url` ni tozalash o'sha
      shaklda hech nimani himoya qilmasdi.
    """
    crumb = _crumb(
        type="http",
        category="httplib",
        data={"url": "http://go2rtc:1984/api/streams", "http.query": ENCODED_QUERY},
    )

    result = _scrubbed(crumb)

    data = result["data"]
    assert isinstance(data, dict)
    assert SECRET not in str(data["http.query"])


def test_breadcrumb_message_is_masked() -> None:
    """Matnli breadcrumb'da ham xom `rtsp://user:pass@` shakli maskalanadi."""
    crumb = _crumb(type="http", message=f"PUT {RAW_SOURCE}")

    result = _scrubbed(crumb)

    assert SECRET not in str(result["message"])
    assert "rtsp://***@" in str(result["message"])


def test_non_http_breadcrumb_passes_through_untouched() -> None:
    """NAZORAT HOLATI: `http` bo'lmagan breadcrumb O'ZGARMAYDI.

    Usiz ilmoqni `return None` bilan almashtirish (ya'ni HAMMA
    breadcrumb'ni tashlab yuborish) yuqoridagi testlarni ham yashil
    qoldirardi — va Sentry'dagi diagnostika butunlay yo'qolardi.
    """
    crumb = _crumb(type="default", category="navigation", message="src=nimadir")

    result = _scrubbed(crumb)

    assert result["message"] == "src=nimadir"


def test_sentry_init_wires_both_hooks() -> None:
    """`lifespan` `before_send` VA `before_breadcrumb` ni BIRGA ulaydi.

    ⚠ FUNKSIYALARNING O'ZI to'g'ri ishlashi yetarli emas: ulanmagan ilmoq
      har bir testda yashil bo'lib, mahsulotda umuman chaqirilmasdi. Bu
      `test_go2rtc_client.py` dagi konfiguratsiya darvozalari bilan bir
      xil naqsh — manba matni o'qiladi va majburiy satr izlanadi.
    """
    source = inspect.getsource(lifespan)

    assert "before_send=_scrub_event" in source
    assert "before_breadcrumb=_scrub_breadcrumb" in source


# ---------------------------------------------------------------------------
# `before_send` — mavjud xulq (03-13 dan OLDIN ham shunday edi)
# ---------------------------------------------------------------------------


def test_request_body_and_cookies_are_dropped() -> None:
    """So'rov tanasi va cookie'lar Sentry'ga UMUMAN bormaydi (ASVS V14)."""
    event = _event(request={"data": {"password": SECRET}, "cookies": {"session": "x"}})

    result = _scrub_event(event, _hint())

    request = result["request"]
    assert isinstance(request, dict)
    assert "data" not in request
    assert "cookies" not in request


def test_authorization_and_cookie_headers_are_masked() -> None:
    """`Authorization` va `Cookie` sarlavhalari maskalanadi, qolganlari qoladi."""
    event = _event(
        request={"headers": {"Authorization": "Bearer abc", "Cookie": "s=1", "X-Request-ID": "r1"}}
    )

    result = _scrub_event(event, _hint())

    request = result["request"]
    assert isinstance(request, dict)
    headers = request["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == MASKED
    assert headers["Cookie"] == MASKED
    assert headers["X-Request-ID"] == "r1", "zararsiz sarlavha ham yo'qoldi"


@pytest.mark.parametrize("key", ["password", "token", "phone", "src", "source"])
def test_pii_keys_in_extra_are_masked(key: str) -> None:
    """`extra` dagi sir kalitlari maskalanadi — `src`/`source` 03-13 da qo'shildi."""
    event = _event(extra={key: SECRET, "camera_id": "c1"})

    result = _scrub_event(event, _hint())

    extra = result["extra"]
    assert isinstance(extra, dict)
    assert extra[key] == MASKED
    assert extra["camera_id"] == "c1"


def test_pii_key_registry_covers_the_stream_source() -> None:
    """`src` reyestrda BOR — `PUT /api/streams` ning parametri endi sir tashiydi."""
    assert "src" in _PII_KEYS
    assert all(key == key.lower() for key in _PII_KEYS), (
        "taqqoslash `key.lower()` bilan — reyestrdagi kalit ham kichik bo'lishi shart"
    )


# ---------------------------------------------------------------------------
# `before_send` — 03-13 ning YANGI qatlami: matn darajasidagi maskalash
# ---------------------------------------------------------------------------


def test_exception_value_loses_the_request_url() -> None:
    """BIRINCHI OQISH YO'LI: `httpx` istisnosining matni.

    `go2rtc.py::_failure()` uni allaqachon tozalaydi; bu esa IKKINCHI
    qatlam va u birinchisining kelajakdagi regressiyasidan mustaqil.
    """
    event = _event(
        exception={
            "values": [
                {"type": "HTTPStatusError", "value": f"Client error for url '{REQUEST_URL}'"}
            ]
        }
    )

    result = _scrub_event(event, _hint())

    rendered = str(result["exception"])
    assert SECRET not in rendered
    assert "HTTPStatusError" in rendered, "istisno TURI ham yo'qoldi — diagnostika qolmadi"


def test_request_query_string_is_masked() -> None:
    """IKKINCHI OQISH YO'LI: kiruvchi so'rovning query satri."""
    event = _event(request={"query_string": ENCODED_QUERY})

    result = _scrub_event(event, _hint())

    request = result["request"]
    assert isinstance(request, dict)
    assert SECRET not in str(request["query_string"])
    assert "name=cam_deadbeef" in str(request["query_string"]), (
        "sirsiz parametr ham yo'qoldi — maskalash butun query'ni yeb qo'ydi"
    )


def test_stack_frame_locals_lose_the_raw_source() -> None:
    """UCHINCHI OQISH YO'LI: freym lokallari (`include_local_variables`).

    ⚠ BU YERDA QIYMAT `src=` SIZ, YALANG'OCH SATR SIFATIDA turadi —
      ya'ni query qoidasi uni TOPMAYDI va `rtsp://user:pass@` qoidasi
      MAJBURIY. Ikkala qoida bir-birini almashtira olmaydi.
    """
    event = _event(
        exception={
            "values": [
                {
                    "stacktrace": {
                        "frames": [
                            {
                                "function": "ensure_stream",
                                "vars": {"source": RAW_SOURCE, "stream_name": "cam_x"},
                            }
                        ]
                    }
                }
            ]
        }
    )

    result = _scrub_event(event, _hint())

    rendered = str(result["exception"])
    assert SECRET not in rendered, "freym lokalidagi ochiq manba Sentry'ga ketdi"
    assert "rtsp://***@nvr.invalid" in rendered, (
        "xost ham yo'qoldi — nosozlikni qaysi NVR'da qidirish noma'lum qolardi"
    )
    assert "cam_x" in rendered, "sirsiz lokal ham yo'qoldi"


def test_masking_leaves_credential_free_sources_alone() -> None:
    """NAZORAT: rekvizitsiz `rtsp://` manzil O'ZGARMAYDI.

    Usiz maskalashni «har `rtsp://` ni `***` qil» deb yozish mumkin edi va
    hamma sir testlari yashil qolardi — Sentry'dagi hodisadan esa qaysi
    NVR haqida gap ketayotgani butunlay yo'qolardi.
    """
    clean = "rtsp://nvr.invalid:554/Streaming/Channels/102"
    event = _event(extra={"detail": clean})

    result = _scrub_event(event, _hint())

    extra = result["extra"]
    assert isinstance(extra, dict)
    assert extra["detail"] == clean
