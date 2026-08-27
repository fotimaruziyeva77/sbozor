"""S3-mos obyekt-ombor — `core-api` nikining TOR nusxasi (§3.5, RESEARCH §E.13).

Shakl `core-api/app/services/storage.py` (530 q.) dan olinadi; farq YUZADA
va u qayta muhokama qilinmaydi.

=============================================================================
1. YUZA — IKKI AMAL. METODNING YO'QLIGI KELISHUV EMAS, STRUKTURA.

    get(key)                -> ✅  kadr S3 KALITI bo'yicha olinadi
    put_evidence(key, data) -> ✅  FAQAT dalil rasmi, FAQAT `evidence/` ostiga
    head / list_prefix / delete_many / create_bucket / delete_bucket -> ⛔ YO'Q

`core-api/app/services/storage.py:11-22` dagi mulohaza so'zma-so'z shu
yerga tegishli: metod MAVJUD bo'lsa keyingi tahrirlovchi uni "qulaylik
uchun" chaqirardi. Bu servisda narx aniq nomlanadi:

  * `list_prefix` bo'lsa — «shu kameraning kecha nechta kadri bor?» degan
    savol bazadan emas, OMBORDAN javob olardi va ombor almashishi
    (SeaweedFS -> AWS S3 -> O'zbekiston buluti) SO'ROVLARNI ham
    o'zgartirardi;
  * `delete_many` bo'lsa — retention IKKI joyda yashardi va ikkinchisi
    (bu yerdagi) `is_billable` filtridan bexabar bo'lardi;
  * `head` bo'lsa — `get` dan oldin "bormi?" tekshiruvi paydo bo'lardi va u
    har kadrga ikkinchi so'rov qo'shib, javobni HAM eskirtirardi.

⚠ REKVIZIT HAM TOR (T-05-06, RESEARCH §E.13): `ops/seaweedfs/s3.json` dagi
  `cv-service` rekviziti FAQAT O'QISH huquqli bo'lishi kerak; yozish esa
  AYNAN `EVIDENCE_PREFIX` ostiga cheklanadi. Shuning uchun quyidagi
  `put_evidence()` prefiksni O'ZI tekshiradi: rekvizitning tor bo'lishi
  `ops` ning va'dasi, prefiksning to'g'ri bo'lishi esa KODNING kafolati.

=============================================================================
2. ⛔ XATO SIRSIZ — VA OQISH YO'LI O'LCHANGAN, FARAZ QILINMAGAN.

`core-api` da 2026-08-04 da o'lchangan (aiobotocore 3.9.0 + SeaweedFS 4.40,
yetib bo'lmaydigan manzil):

    EndpointConnectionError:
    Could not connect to the endpoint URL:
    "http://ombor-yoq.invalid:8333/sbozor-snapshots/<market>/<sana>/…jpg"

Ya'ni `botocore` ning TARMOQ istisnolari to'liq manzilni — sxema, host,
port, bucket VA obyekt kalitini — matnda tashiydi.

⚠⚠ O'SHA O'LCHOV IKKINCHI, TESKARI FAKTNI HAM BERDI VA U TESTNI YOZISHDA
   HAL QILUVCHI: `ClientError` ning matni (`SignatureDoesNotMatch`,
   `NoSuchKey`) manzilni ham, rekvizitni ham TASHIMAYDI. Ya'ni FAQAT
   `ClientError` bilan yozilgan sirsizlik testi kod SIZAYOTGAN bo'lsa ham
   YASHIL bo'lardi — u tekshirayotgan istisno sinfida sir umuman yo'q.
   `tests/unit/test_storage_surface.py` shu sababdan IKKALA sinfni ham
   o'lchaydi.

Shuning uchun `_failure()` FAQAT uch fakt beradi: amal + istisno turi +
HTTP status. Va u `raise … from None` bilan ko'tariladi.

⚠ SHU SABAB SHU YERDA — `_failure()` NING TANASIDA EMAS, va bu ataylab:
  qabul mezoni o'sha funksiyaning tanasini MATN sifatida o'qiydi.

=============================================================================
3. KLIENT EGALIGI — BITTA VARIANT, CHUNKI `cv-service` SOF WORKER.

`core-api` da ikki variant bor (`storage.py:75-88`): worker jarayonida
uzoq umr, HTTP so'rovida esa `async with`. Bu servisda HTTP qatlami
YO'Q — klient `WORKER_STARTUP` da BIR MARTA ochiladi va
`WORKER_SHUTDOWN` da yopiladi. Ikkinchi variantning yo'qligi shu yerda
yozilgan, aks holda keyingi tahrirlovchi uni "izchillik uchun" qidirardi.

=============================================================================
4. ⛔ IMZO ZANJIRI QO'LDA QURILMAYDI (T-04-44) va `minio-py` TAQIQ:
   S3 API omborni SOZLAMA o'zgarishi qilib saqlaydi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import structlog
from aiobotocore.config import AioConfig
from aiobotocore.session import get_session
from botocore.exceptions import BotoCoreError, ClientError

from app.detector.annotate import EVIDENCE_PREFIX

if TYPE_CHECKING:
    from app.settings import Settings

__all__ = [
    "EVIDENCE_PREFIX_REQUIRED",
    "CvStorageClient",
    "FrameAbsent",
    "StorageError",
    "open",
]

log = structlog.get_logger(__name__)

_CONNECT_TIMEOUT_SECONDS = 5.0
_READ_TIMEOUT_SECONDS = 15.0
"""Ombor bilan muloqot chegaralari — CHEKSIZ KUTISH YO'Q.

`core-api` dagi qiymatlarning AYNAN o'zi va sabab ham bir xil: ombor
compose tarmog'ining ichida, bitta kadr ~60 KB. Chegarasiz chaqiruv esa
`taskiq` worker'ining bitta ilmog'ini abadiy band qilib, navbatni jimgina
to'xtatib qo'yardi.
"""

_MAX_ATTEMPTS = 3
_RETRY_MODE = "standard"
"""`botocore` ning O'Z retry siyosati — ikkinchi qatlam USTIGA QO'YILMAYDI."""

_OP_GET = "GET"
_OP_PUT = "PUT"

_S3_REGION = "us-east-1"
"""SeaweedFS mintaqani E'TIBORSIZ qoldiradi, `botocore` esa uni TALAB qiladi.

Qiymat `core-api/app/settings.py:184` dagi `s3_region` ning standarti bilan
AYNAN bir xil va u `compose.yaml` da hech qachon berilmaydi. Shu sababdan
u bu servisda SOZLAMA emas, KOD konstantasi: muhitga chiqarilsa ikkala
servis bir xil bucketni ikki xil imzo qamrovi (`SigV4` scope) bilan
so'rashi mumkin bo'lardi va nosozlik faqat HAQIQIY AWS S3 ga ko'chganda —
ya'ni eng qimmat paytda — ochilardi.
"""

_ABSENT_ERROR_CODES = frozenset({"404", "NoSuchKey", "NotFound"})
"""«Obyekt YO'Q» degan javobning uchala shakli — `core-api` da O'LCHANGAN ro'yxat.

O'lchov (2026-08-04, SeaweedFS 4.40):

    head_object(yo'q kalit)  -> Error.Code = "404"        (HTTP 404)
    get_object(yo'q kalit)   -> Error.Code = "NoSuchKey"  (HTTP 404)

Bu servisda `head` UMUMAN yo'q, ya'ni `"404"` ni faqat `get` yo'li uchun
qoldirish mumkindek tuyuladi. U ATAYIN qoldirildi: ro'yxat `core-api`
nikidan HOSILA emas, NUSXA, va ikkala nusxaning bir xil bo'lishi ombor
almashganda (AWS S3 `"NotFound"` beradi) ikkala servisning bir xil
talqin qilishini ta'minlaydi.

⚠ `NoSuchBucket` BU RO'YXATDA ATAYIN YO'Q — u ham 404 beradi, lekin
  ma'nosi butunlay boshqa: bucket yo'qligi KONFIGURATSIYA nosozligi va uni
  "kadr yo'q" deb talqin qilish butun kunlik aniqlashni jimgina bo'sh
  qoldirardi. Fail-closed yo'nalish: u `StorageError` ga aylanadi.
"""

EVIDENCE_PREFIX_REQUIRED = "storage_evidence_prefix_required"
"""`ValueError` ning matni — testda ham, jurnalda ham AYNAN shu satr."""


class StorageError(Exception):
    """Ombor javob bermadi yoki amalni rad etdi.

    ⚠ MATNIGA `botocore` ISTISNOSI INTERPOLYATSIYA QILINMAYDI (T-05-37).
      Sabab modul docstringining 2-bandida.
    """


class FrameAbsent(StorageError):
    """Kalit omborda YO'Q — bu TANILGAN sabab, kutilmagan nosozlik EMAS.

    Alohida sinf bo'lishi `detect.py` ning xato zanjiriga kerak: "kadr
    o'chirilgan" (retention allaqachon supurgan, yoki obyekt hech qachon
    yozilmagan) `log.info` bilan yopiladi, "ombor javob bermadi" esa
    `log.warning` bilan. Ikkalasini bitta sinfga yig'ish ombor uzilishini
    kunlik shovqin ichida ko'rinmas qilardi.

    ⚠ `StorageError` NING VORISI: chaqiruvchi farqni BILISHI SHART emas —
      ikkalasi ham "hodisa yozilmaydi" degan bir xil natijaga olib keladi.
    """


def _failure(op: str, exc: Exception) -> StorageError:
    """`botocore` istisnosini SIRSIZ `StorageError` ga aylantiradi (T-05-37).

    Diagnostika uchun UCH fakt yetadi va uchalasi ham sirsiz: qaysi AMAL,
    qaysi ISTISNO TURI, qaysi HTTP STATUS. "Qaysi kalit" savoliga
    chaqiruvchining jurnal qatori javob beradi — u kalitni O'ZI biladi.

    ⚠ ISTISNO MATNINING INTERPOLYATSIYASI YO'Q va sabab shu funksiyaning
      tanasida EMAS (modul docstringi, 2-band): qabul mezoni aynan shu
      tanani MATN sifatida o'qiydi.
    """
    status: int | None = None
    if isinstance(exc, ClientError):
        metadata = exc.response.get("ResponseMetadata") or {}
        code = metadata.get("HTTPStatusCode")
        status = code if isinstance(code, int) else None
    detail = f"status={status}" if status is not None else "javob yo'q"
    return StorageError(f"ombor `{op}` amali yiqildi: {type(exc).__name__} ({detail})")


def _absent(op: str, exc: ClientError) -> FrameAbsent:
    """«Kalit yo'q» javobi — SIRSIZ shakli `_failure()` bilan bir xil."""
    return FrameAbsent(f"ombor `{op}`: obyekt topilmadi ({type(exc).__name__})")


def _is_absent(exc: ClientError) -> bool:
    """Xato «obyekt yo'q» degan javobmi (`_ABSENT_ERROR_CODES` docstringi)."""
    error = exc.response.get("Error") or {}
    return str(error.get("Code", "")) in _ABSENT_ERROR_CODES


async def _call(op: str, request: Awaitable[Any]) -> Any:
    """Bitta ombor chaqiruvi — istisno sirsiz shaklga o'giriladi, zanjir UZILADI.

    ⚠ `raise` BLOKDAN TASHQARIDA va bu `core-api/app/services/storage.py:213-227`
      dagi bilan AYNAN bir xil nozik qaror: `except` ichida ko'tarilgan yangi
      istisnoning `__context__` i XOM istisno bo'lib qolardi va uning matni
      (tarmoq sinfida) to'liq ombor manzilini tashiydi. Blok tugagach
      kontekst tozalanadi, `from None` esa uni `__cause__` da ham
      qoldirmaydi.
    """
    failure: StorageError | None = None
    try:
        return await request
    except ClientError as exc:
        failure = _absent(op, exc) if _is_absent(exc) else _failure(op, exc)
    except (BotoCoreError, TimeoutError) as exc:
        failure = _failure(op, exc)
    raise failure from None


class CvStorageClient:
    """S3 klienti ustidagi YUPQA qobiq — IKKI amal, boshqa hech nima.

    ⚠ `head`, `list_prefix`, `delete_many`, `create_bucket`, `delete_bucket`
      UMUMAN YO'Q. Sabab modul docstringining 1-bandida va u qayta
      ochilmaydi; `tests/unit/test_storage_surface.py` buni `hasattr` bilan
      MEXANIK tekshiradi.

    ⚠ XOM KLIENT TASHQARIGA CHIQARILMAYDI: `__getattr__` yo'q va klient
      maydoni yopiq. Aks holda "faqat bitta chaqiruv uchun" degan yo'l
      ochilardi va u yerdan yuqoridagi hamma taqiq bemalol o'tardi.
    """

    def __init__(self, client: Any, *, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def get(self, key: str) -> bytes:
        """Kadrning baytlari — KALIT bo'yicha (RESEARCH §E.13).

        Navbat xabari `snapshot_id` olib yuradi, BAYTLARNI emas: ~500 KB x
        175 kadr Valkey brokerini bo'g'ardi va 4-fazaning Valkey'i
        `--save "" --appendonly no` bilan ishlaydi, ya'ni unga hech qanday
        muhim ma'lumot ishonib topshirilmaydi.

        Raises:
            FrameAbsent: kalit omborda yo'q (retention supurgan yoki obyekt
                hech qachon yozilmagan).
            StorageError: ombor javob bermadi yoki amalni rad etdi.
        """
        response = await _call(_OP_GET, self._client.get_object(Bucket=self._bucket, Key=key))
        body = await _call(_OP_GET, response["Body"].read())
        return bytes(body)

    async def put_evidence(self, key: str, data: bytes, *, content_type: str = "image/jpeg") -> str:
        """Dalil rasmini `EVIDENCE_PREFIX` ostiga yozadi va `ETag` ni qaytaradi.

        ⛔ PREFIKS TEKSHIRUVI SHU YERDA VA U «QO'SHIMCHA HIMOYA» EMAS.
           Asl kadr `snapshots.object_key` da yashaydi va u HECH QACHON
           qayta yozilmasligi kerak (T-05-32): ko'r auditning butun dalil
           zanjiri "nazoratchi ko'rgan rasm — bo'yalmagan asl kadr" degan
           da'voga tayanadi. Prefikssiz `put` bitta xato kalit bilan o'sha
           da'voni JIMGINA yolg'onga chiqarardi — hech qanday xatosiz.

        ⚠ METOD NOMI `put` EMAS: "faqat dalil rasmi" cheklovi nomda ham,
          tanada ham turadi. `put` deb nomlansa u umumiy yozish yuzasi
          bo'lib ko'rinardi va prefiks tekshiruvi "keraksiz to'siq" deb
          olib tashlanishi mumkin bo'lardi.

        Raises:
            ValueError: kalit `EVIDENCE_PREFIX` bilan boshlanmasa. Tip
                ataylab oddiy `ValueError` — bunday chaqiruv mahsulot
                yo'lidan HECH QACHON kelmaydi va u kelishi KODDAGI xatoni
                bildiradi (`assert_safe_go2rtc_src` bilan bir xil qaror).
            StorageError: ombor amalni rad etdi.
        """
        if not key.startswith(EVIDENCE_PREFIX):
            raise ValueError(EVIDENCE_PREFIX_REQUIRED)
        response = await _call(
            _OP_PUT,
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            ),
        )
        return str(response["ETag"])


@asynccontextmanager
async def open(settings: Settings) -> AsyncIterator[CvStorageClient]:
    """Ombor klientini ochadi va chiqishda YOPADI.

    ⚠ NOM `open` — VA U O'RNAShGAN `builtins.open` NI SOYALAYDI (`core-api`
      bilan aynan bir xil qaror): modul har doim `storage.open(settings)`
      shaklida chaqiriladi va bu fayl `builtins.open` ga muhtoj emas.

    Klient `async with` ichida yashaydi: `aiobotocore` ning ulanish puli
    jimgina yopilmaydi va yopilmagan pul `aiohttp` ning "Unclosed
    connector" ogohlantirishi bilan tugardi — resurs oqishi FAQAT jurnalda
    ko'rinadigan shaklda qolardi.
    """
    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        # ⚠ OCHIQ QIYMATGA BORISH SHU YERDA VA BOSHQA HECH QAYERDA
        #   (`core-api/app/services/storage.py:417-421` bilan bir xil
        #   qoida): bitta, grep bilan topiladigan, ko'zga tashlanadigan
        #   qadam.
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        region_name=_S3_REGION,
        config=AioConfig(
            connect_timeout=_CONNECT_TIMEOUT_SECONDS,
            read_timeout=_READ_TIMEOUT_SECONDS,
            retries={"max_attempts": _MAX_ATTEMPTS, "mode": _RETRY_MODE},
        ),
    ) as client:
        yield CvStorageClient(client, bucket=settings.s3_bucket)
