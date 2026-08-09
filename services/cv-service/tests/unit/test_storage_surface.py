"""Ombor YUZASINING darvozasi — «metodning yo'qligi STRUKTURA» ni O'LCHAYDI.

=============================================================================
⚠⚠ NEGA BU TEST FAQAT `ClientError` BILAN YOZILMAYDI — REJANING O'ZI
   AYTGAN YO'L YETARLI EMAS VA BUNI 04-06 NING O'LCHOVI KO'RSATADI.

`04-06` (2026-08-04, `aiobotocore 3.9.0` + SeaweedFS 4.40) ikki faktni
birga o'lchagan:

  (1) TARMOQ istisnolari (`EndpointConnectionError`, ya'ni `BotoCoreError`
      oilasi) matnda TO'LIQ MANZILNI tashiydi — sxema, host, port, bucket
      VA obyekt kaliti;
  (2) `ClientError` ning matni (`SignatureDoesNotMatch`, `NoSuchKey`)
      manzilni ham, rekvizitni ham TASHIMAYDI.

Ya'ni sirsizlikni FAQAT `ClientError` bilan tekshirgan test kod
sizayotgan bo'lsa ham YASHIL bo'ladi: u tekshirayotgan istisno sinfida
sizadigan narsaning O'ZI yo'q. Bu «test o'tdi» va «test o'zi so'ragan
narsani o'lchadi» farqining aynan o'sha sinfi (05-03 va 05-07 ning darsi).

Shu sababdan quyidagi testlar IKKALA sinfni ham beradi va HAL QILUVCHISI
ikkinchisi.
=============================================================================

⚠ Bu fayl HAQIQIY ombor talab QILMAYDI: istisnolar sun'iy quriladi va
  yuza `hasattr` bilan o'qiladi. Haqiqiy S3 bilan muloqotning o'zi
  `detect` ning integratsiya testida (haqiqiy SeaweedFS emas — u
  `core-api` ning `-m sim` to'plamida allaqachon o'lchangan).
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.detector.annotate import EVIDENCE_PREFIX
from app.services import storage as storage_module
from app.services.storage import (
    EVIDENCE_PREFIX_REQUIRED,
    CvStorageClient,
    FrameAbsent,
    StorageError,
)

# ---------------------------------------------------------------------------
# Sun'iy sirlar — testda TEKSHIRILADIGAN satrlar bir joyda.
# ---------------------------------------------------------------------------

SECRET_BUCKET = "sbozor-snapshots"
SECRET_KEY = "11111111-2222-3333-4444-555555555555/2026-08-09/cam-07/0600.jpg"
SECRET_HOST = "ombor-yoq.invalid"
SECRET_PORT = "8333"
SECRET_ENDPOINT = f"http://{SECRET_HOST}:{SECRET_PORT}/{SECRET_BUCKET}/{SECRET_KEY}"

FORBIDDEN_METHODS = ("head", "list_prefix", "delete_many", "create_bucket", "delete_bucket")
"""⛔ BU METODLAR `CvStorageClient` DA BO'LMASLIGI SHART.

Ro'yxat `core-api` ning `SnapshotStorage` idan HOSILA emas, MUSTAQIL:
`core-api` da `head`/`list_prefix`/`delete_many` QONUNIY (retention va
yetim obyekt supurgisi ularga tayanadi), bu servisda esa ular
mavjudligining O'ZI xato. Hosila ro'yxat `core-api` metodni qo'shganda
bu darvozani jimgina bo'shatardi.
"""


def _client_error(code: str, status: int) -> ClientError:
    """`ClientError` — `Message` ga kalit ATAYIN qo'yilgan, va bu O'LCHOVGA ASOSLANGAN.

    ⚠⚠ HAQIQIY `ClientError` KALITNI TASHIMAYDI (04-06 ning 2-fakti). Ya'ni
       bu funksiya haqiqiy xulqni EMAS, undan KUCHLIROQ holatni yasaydi.
       Sabab shu faylning yuqorisidagi o'lchovda: 2026-08-09 da
       `_failure()` ga `{exc}` interpolyatsiyasi kiritilib o'lchandi —

           realistik (kalitsiz) `ClientError` bilan  ->  test YASHIL QOLDI
           `EndpointConnectionError` bilan           ->  test QIZARDI

       Ya'ni `ClientError` yo'li YOLG'IZ O'ZI hech nimani qo'riqlamaydi.
       Kalit `Message` ga qo'yilgach u KELAJAKKA qarshi turadigan darvozaga
       aylanadi: `botocore` yoki SeaweedFS bir kun kalitni xato tanasiga
       qo'sha boshlasa, sirsizlik da'vosi shu yerda qizaradi.
    """
    return ClientError(
        {
            "Error": {"Code": code, "Message": f"{code} for {SECRET_KEY}"},
            "ResponseMetadata": {"HTTPStatusCode": status},
        },
        "GetObject",
    )


def _network_error() -> EndpointConnectionError:
    """`BotoCoreError` oilasi — matnida TO'LIQ MANZIL BOR (04-06 ning 1-fakti)."""
    return EndpointConnectionError(endpoint_url=SECRET_ENDPOINT)


class _FakeBody:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def read(self) -> bytes:
        raise self._exc


class _FailingS3:
    """Har chaqiruvda berilgan istisnoni tashlaydigan minimal S3 klienti.

    ⚠ BU OMBORNING SOXTA AMALGA OSHIRILISHI EMAS: u hech qanday obyekt
      saqlamaydi va hech qachon MUVAFFAQIYAT qaytarmaydi. Uning yagona
      vazifasi — istisnoni `CvStorageClient` ning ichiga OLIB KIRISH.
    """

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def get_object(self, **_kw: Any) -> dict[str, Any]:
        raise self._exc

    async def put_object(self, **_kw: Any) -> dict[str, Any]:
        raise self._exc


# ===========================================================================
# 1. YUZA — METODNING YO'QLIGI
# ===========================================================================


@pytest.mark.parametrize("name", FORBIDDEN_METHODS)
def test_forbidden_method_is_absent_from_the_class(name: str) -> None:
    """`hasattr` — `dir()` EMAS: `__getattr__` orqali kelgan nom ham ushlanadi."""
    assert not hasattr(CvStorageClient, name), (
        f"`CvStorageClient.{name}` MAVJUD. `services/storage.py` modul "
        "docstringining 1-bandi: metodning yo'qligi kelishuv emas, STRUKTURA."
    )


def test_the_surface_is_exactly_two_public_methods() -> None:
    """Yuza SANOQ bilan ham qulflanadi — yangi metod jimgina qo'shilmaydi.

    ⚠ Yuqoridagi ro'yxat NOMLARNI taqiqlaydi, bu test esa SONNI: taqiq
      ro'yxatida bo'lmagan yangi nom (`copy_object`, `presign`, ...)
      birinchisidan bemalol o'tardi.
    """
    public = sorted(
        name
        for name, value in inspect.getmembers(CvStorageClient)
        if not name.startswith("_") and callable(value)
    )
    assert public == ["get", "put_evidence"], (
        f"`CvStorageClient` ning ommaviy yuzasi o'zgardi: {public}. "
        "Yangi metod qo'shish modul docstringining 1-bandini qayta ochadi."
    )


def test_the_raw_client_is_not_reachable_through_getattr() -> None:
    """`__getattr__` yo'q — aks holda hamma taqiq bitta yo'ldan o'tardi."""
    assert "__getattr__" not in vars(CvStorageClient)
    instance = CvStorageClient(_FailingS3(_network_error()), bucket=SECRET_BUCKET)
    with pytest.raises(AttributeError):
        _ = instance.list_prefix  # type: ignore[attr-defined]


# ===========================================================================
# 2. XATO SIRSIZ — IKKALA ISTISNO SINFI HAM
# ===========================================================================


@pytest.mark.asyncio
async def test_network_failure_message_carries_no_endpoint_bucket_or_key() -> None:
    """⚠ HAL QILUVCHI TEST: sizadigan istisno sinfi AYNAN shu (04-06, 1-fakt)."""
    client = CvStorageClient(_FailingS3(_network_error()), bucket=SECRET_BUCKET)

    with pytest.raises(StorageError) as excinfo:
        await client.get(SECRET_KEY)

    message = str(excinfo.value)
    for secret in (SECRET_BUCKET, SECRET_KEY, SECRET_HOST, SECRET_PORT, SECRET_ENDPOINT):
        assert secret not in message, (
            f"xato matnida `{secret}` bor: {message!r}. `_failure()` FAQAT "
            "amal + istisno turi + status berishi kerak (T-05-37)."
        )
    assert "GET" in message
    assert "EndpointConnectionError" in message


@pytest.mark.asyncio
async def test_client_error_message_carries_no_bucket_or_key() -> None:
    """`ClientError` yo'li — o'zi sir tashimaydi, lekin qoida IKKALASIGA ham qo'llanadi."""
    failing = _FailingS3(_client_error("SignatureDoesNotMatch", 403))
    client = CvStorageClient(failing, bucket=SECRET_BUCKET)

    with pytest.raises(StorageError) as excinfo:
        await client.get(SECRET_KEY)

    message = str(excinfo.value)
    assert SECRET_KEY not in message
    assert SECRET_BUCKET not in message
    assert "status=403" in message


@pytest.mark.asyncio
async def test_the_exception_chain_is_broken_in_both_directions() -> None:
    """XOM istisno `__cause__` da ham, `__context__` da ham QOLMAYDI.

    Zanjirda qolgan xom istisno `traceback`, Sentry ning zanjir yuruvchisi
    va har qanday `format_exc()` orqali BARIBIR chop etilardi — ya'ni
    `_failure()` ning butun mehnati bekor bo'lardi.

    ⚠⚠ BU TEST `from None` NI EMAS, `raise` NING JOYINI QULFLAYDI — VA FARQ
       O'LCHANGAN (2026-08-09):

           `from None` OLIB TASHLANDI, `raise` bloqdan tashqarida  -> YASHIL
           `from None` QOLDI,  `raise` `except` ICHIGA ko'chirildi  -> QIZIL

       Sabab: `from None` faqat `__suppress_context__` ni qo'yadi, ya'ni
       `__context__` NING O'ZI joyida qoladi va u yerda to'liq ombor
       manzili turadi. Kontekst faqat `except` bloki TUGAGANDAN keyin
       tozalanadi. `core-api/app/services/storage.py:213-227` ning
       «`raise` BLOKDAN TASHQARIDA» izohi shu sababdan nozik qaror.
    """
    client = CvStorageClient(_FailingS3(_network_error()), bucket=SECRET_BUCKET)

    with pytest.raises(StorageError) as excinfo:
        await client.get(SECRET_KEY)

    assert excinfo.value.__cause__ is None
    assert excinfo.value.__context__ is None


@pytest.mark.asyncio
async def test_a_leak_from_the_response_body_is_covered_too() -> None:
    """Tana o'qilayotganda chiqqan tarmoq istisnosi ham SIRSIZ bo'ladi.

    `get()` IKKI chaqiruv qiladi (`get_object`, keyin `Body.read()`) va
    ikkinchisi birinchisidan keyin uziladigan ulanishda yiqiladi. Faqat
    birinchisini o'rash sirni ikkinchi yo'ldan chiqarardi.
    """
    body = _FakeBody(_network_error())

    class _PartialS3:
        async def get_object(self, **_kw: Any) -> dict[str, Any]:
            return {"Body": body}

    client = CvStorageClient(_PartialS3(), bucket=SECRET_BUCKET)

    with pytest.raises(StorageError) as excinfo:
        await client.get(SECRET_KEY)

    assert SECRET_ENDPOINT not in str(excinfo.value)


def test_failure_body_never_interpolates_the_exception() -> None:
    """`_failure()` ning TANASI matn sifatida o'qiladi (`core-api` ning qarori).

    Sabab ATAYIN funksiya tanasida emas, modul docstringida — ya'ni tana
    faqat uch faktni yig'adi va uni matn sifatida tekshirish MA'NOLI
    qoladi.
    """
    body = inspect.getsource(storage_module._failure)
    for banned in ("{exc}", "str(exc)", "exc!r", "{exc!s}", "repr(exc)"):
        assert banned not in body, (
            f"`_failure()` tanasida `{banned}` bor — istisno matni "
            "interpolyatsiya qilinmoqda (T-05-37)."
        )
    assert "type(exc).__name__" in body


# ===========================================================================
# 3. «OBYEKT YO'Q» — ALOHIDA SINF, VA `NoSuchBucket` UNGA KIRMAYDI
# ===========================================================================


@pytest.mark.parametrize("code", ["404", "NoSuchKey", "NotFound"])
@pytest.mark.asyncio
async def test_absent_key_becomes_frame_absent(code: str) -> None:
    """Uchala shakl ham «kadr yo'q» — `head` va `get` boshqa kod beradi (04-06)."""
    client = CvStorageClient(_FailingS3(_client_error(code, 404)), bucket=SECRET_BUCKET)
    with pytest.raises(FrameAbsent):
        await client.get(SECRET_KEY)


@pytest.mark.asyncio
async def test_missing_bucket_is_not_treated_as_a_missing_frame() -> None:
    """⚠ `NoSuchBucket` FAIL-CLOSED: u konfiguratsiya nosozligi.

    Uni «kadr yo'q» deb talqin qilish butun kunlik aniqlashni jimgina
    bo'sh qoldirardi va hisobot «hamma rasta bo'sh» deb ko'rsatardi.
    """
    client = CvStorageClient(_FailingS3(_client_error("NoSuchBucket", 404)), bucket=SECRET_BUCKET)
    with pytest.raises(StorageError) as excinfo:
        await client.get(SECRET_KEY)
    assert not isinstance(excinfo.value, FrameAbsent)


# ===========================================================================
# 4. DALIL RASMI — ALOHIDA PREFIKS
# ===========================================================================


@pytest.mark.asyncio
async def test_writing_outside_the_evidence_prefix_is_rejected() -> None:
    """Asl kadr yo'liga yozish IMKONSIZ — T-05-32 ning kod tomondagi yarmi."""
    client = CvStorageClient(_FailingS3(_network_error()), bucket=SECRET_BUCKET)
    with pytest.raises(ValueError, match=EVIDENCE_PREFIX_REQUIRED):
        await client.put_evidence(SECRET_KEY, b"x")


@pytest.mark.asyncio
async def test_the_evidence_prefix_itself_reaches_the_storage_call() -> None:
    """Prefiksli kalit tekshiruvdan O'TADI — taqiq hamma yozishni bloklamaydi.

    ⚠ Bu testsiz `put_evidence` HAR DOIM `ValueError` beradigan qilib
      yozilgan bo'lsa ham yuqoridagi test yashil bo'lardi.
    """
    recorded: dict[str, Any] = {}

    class _RecordingS3:
        async def put_object(self, **kw: Any) -> dict[str, Any]:
            recorded.update(kw)
            return {"ETag": '"abc"'}

    client = CvStorageClient(_RecordingS3(), bucket=SECRET_BUCKET)
    etag = await client.put_evidence(f"{EVIDENCE_PREFIX}m/2026-08-09/z.jpg", b"x")

    assert etag == '"abc"'
    assert recorded["Key"].startswith(EVIDENCE_PREFIX)
    assert recorded["Bucket"] == SECRET_BUCKET


def test_the_module_names_the_evidence_prefix_instead_of_repeating_it() -> None:
    """Prefiks IMPORT qilinadi, satr sifatida QAYTA YOZILMAYDI.

    Ikkinchi nusxa yozuvchi (bu modul) bilan o'quvchini (`core-api` rasm
    proxysi) jimgina boshqa yo'llarga qaratardi — 05-07 ning
    `EVIDENCE_PREFIX` qarori aynan shu haqda.
    """
    source = inspect.getsource(storage_module)
    assert "EVIDENCE_PREFIX" in source
    assert f'"{EVIDENCE_PREFIX}"' not in source
