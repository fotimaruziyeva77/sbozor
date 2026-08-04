"""S3-mos obyekt-ombor — `aiobotocore` ustidagi YUPQA qobiq (CAM-07, §D.9).

Loyihada obyekt-ombor SHU FAYLGACHA umuman yo'q edi (`04-PATTERNS.md` §4.2 —
o'lchov 2026-08-04: `aiobotocore|boto3|minio|seaweed` bo'yicha NOL natija), ya'ni
bu qatlamning ANALOGI yo'q. Struktura `go2rtc.py` dan olinadi: yupqa qobiq,
sirsiz xato fabrikasi, uzilgan istisno zanjiri.

=============================================================================
TO'RT MAJBURIYAT — TO'RTALASI HAM QAYTA MUHOKAMA QILINMAYDI.

1. YUPQA QOBIQ, VA METODNING YO'QLIGI — KELISHUV EMAS, STRUKTURA.

   `create_bucket` va `delete_bucket` UMUMAN yozilmagan. `ops/seaweedfs/
   s3.json` da `Admin` amali BERILMAGAN (§D.9): rekvizit aynan bitta bucketga
   qadalgan. Bucket o'rnatishda BIR MARTA, qo'lda yaratiladi
   (`ops/seaweedfs/README.md` §3).

   Metod MAVJUD bo'lsa keyingi tahrirlovchi uni "qulaylik uchun" — masalan
   testni soddalashtirish uchun — chaqirardi va o'shanda rekvizitga `Admin`
   qo'shishga majbur bo'lardi, ya'ni butun o'rnatmaning ombor huquqi bitta
   qulaylik uchun kengayardi. `go2rtc.py:193-197` bilan aynan bir xil
   mulohaza: "metodning yo'qligi — kelishuv emas, STRUKTURA".

2. ⛔ S3 HECH QACHON SO'ROV MEXANIZMI EMAS.

   `list_prefix` FAQAT ikki iste'molchi uchun: retention (`04-08`) va yetim
   obyekt supurgisi. Har qanday FOYDALANUVCHI so'rovi — "shu kameraning
   kadrlari", "shu kunning hisoboti" — BAZADAN javob oladi.

   Sabab arxitekturaviy va u `object_key.py` ning 2-fakti bilan bir xil:
   ombor almashishi (SeaweedFS -> AWS S3 -> O'zbekiston buluti) SOZLAMA
   o'zgarishi bo'lib qolishi kerak. S3 listing so'rov semantikasiga aylansa,
   ombor almashishi SO'ROVLARNI ham o'zgartirardi va migratsiya arzon
   bo'lmasdi. `sbozor_core/security.py:6-11` uslubidagi "bu yo'l ATAYIN
   yo'q" izohi.

3. ⛔ XATO SIRSIZ — VA OQISH YO'LI O'LCHANGAN, FARAZ QILINMAGAN.

   O'lchov (2026-08-04, `aiobotocore 3.9.0` + SeaweedFS 4.40, yetib
   bo'lmaydigan manzilga `put_object`):

       EndpointConnectionError:
       Could not connect to the endpoint URL:
       "http://ombor-yoq.invalid:8333/sbozor-snapshots/<market>/<sana>/…jpg"

   Ya'ni `botocore` ning TARMOQ istisnolari to'liq manzilni — sxema, host,
   port, bucket VA obyekt kalitini — matnda tashiydi. Bitta
   `log.error(error=str(exc))` butun ichki topologiyani jurnalga, u yerdan
   Sentry'ga chiqarardi (T-04-40, D-12 ning bevosita buzilishi).

   Xuddi shu o'lchov IKKINCHI faktni ham berdi va u halol yozilishi kerak:
   `ClientError` ning matni (`SignatureDoesNotMatch`, `InvalidAccessKeyId`,
   `NoSuchKey`) manzilni ham, rekvizitni ham TASHIMAYDI. Ya'ni xavf butun
   `botocore` istisnolar oilasiga emas, TARMOQ sinfiga tegishli — lekin
   qoida ikkalasiga ham bir xil qo'llanadi, chunki chaqiruvchi qaysi sinf
   kelganini bilmaydi va bilishi ham shart emas.

   Shuning uchun `_failure()` FAQAT uch fakt beradi: amal + istisno turi +
   HTTP status. Va u `raise … from None` bilan ko'tariladi: zanjirda qolgan
   istisno `traceback`, Sentry ning zanjir yuruvchisi va har qanday
   `format_exc()` orqali baribir chop etilardi (`go2rtc.py:324-330` bilan
   aynan bir xil mulohaza).

   ⚠ SHU SABAB SHU YERDA — `_failure()` NING TANASIDA EMAS, va bu ataylab:
     qabul mezoni o'sha funksiyaning tanasini MATN sifatida o'qiydi.

4. ⛔ IMZO ZANJIRI QO'LDA QURILMAYDI.

   Kanonik so'rov qurish va imzolash — xavfsizlikka tegishli kod;
   `aiobotocore` uni allaqachon bajaradi ("Don't Hand-Roll" ro'yxatining
   birinchi qatori, T-04-44). `aioboto3` esa O'RNATIB BO'LMAYDI (D-17,
   §D.9.2) va `minio-py` TAQIQLANGAN — S3 API omborni sozlama o'zgarishi
   qilib saqlaydi.
=============================================================================
KLIENT `app.state` DA SAQLANMAYDI — IKKI QATLAM IKKI XIL EGALIK OLADI.

  * WORKER jarayonida klient `WORKER_STARTUP` da BIR MARTA ochiladi va
    `WORKER_SHUTDOWN` da yopiladi (`worker.py:181-207` naqshi, ulanishi
    `04-07` da). Sabab miqdorda: kadr olish SIYRAK EMAS — 175 chaqiruv/kun/
    bozor va cho'qqida bir daqiqada 25 ta. Har chaqiruvda yangi sessiya
    ochish TCP va imzo tayyorgarligini 175 marta takrorlardi.

  * HTTP qatlamida (rasm proxysi, `04-09`) klient SO'ROV DAVOMIDA `async
    with` bilan ochiladi. U yerda muloqot HAQIQATAN siyrak (admin rasmni
    ochganda) va `go2rtc.py:199-203` dagi bilan bir xil qaror ishlaydi.

Farq atayin va u shu yerda yozilgan — aks holda keyingi tahrirlovchi ikkala
joyda bir xil shaklni "izchillik uchun" majburlardi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aiobotocore.config import AioConfig  # type: ignore[import-untyped]
from aiobotocore.session import get_session  # type: ignore[import-untyped]
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from app.settings import Settings

__all__ = [
    "HeadResult",
    "PutResult",
    "SnapshotStorage",
    "StorageError",
    "open",
]

_CONNECT_TIMEOUT_SECONDS = 5.0
_READ_TIMEOUT_SECONDS = 15.0
"""Ombor bilan muloqot chegaralari — CHEKSIZ KUTISH YO'Q.

Ombor compose tarmog'ining ichida turadi va bitta kadr ~60 KB, ya'ni ikkala
chegara ham juda saxiy. Chegarasiz chaqiruv esa `capture_grace_seconds`
(600 s) oynasini butunlay yeb, slotni `missed` ga aylantirardi — kadr
olingan, lekin hech qayerga yozilmagan holatda.
"""

_MAX_ATTEMPTS = 3
"""`botocore` ning O'Z retry siyosati — `tenacity` USTIGA QO'YILMAYDI.

Ikki qatlamni ustma-ust qo'yish urinishlar sonini KO'PAYTIRARDI (3 x 3 = 9)
va umumiy vaqt byudjetini hech kim hisoblab chiqmasdi. `isapi/client.py`
dagi "ikki qatlam aralashtirilmaydi" qoidasining aynan o'zi, boshqa yo'lda.
"""

_RETRY_MODE = "standard"
"""`legacy` EMAS: `standard` rejim qaysi xato sinflari qayta urinishga
loyiqligini ANIQ ro'yxat bilan belgilaydi va urinishlar kvotasini yuritadi."""

_DELETE_BATCH = 1000
"""`DeleteObjects` ning bir so'rovdagi chegarasi (S3 API).

Undan kattaroq to'plam `MalformedXML` bilan rad etilardi, ya'ni bo'lish
optimallashtirish emas, PROTOKOL talabi.
"""

_OP_PUT = "PUT"
_OP_HEAD = "HEAD"
_OP_GET = "GET"
_OP_LIST = "LIST"
_OP_DELETE = "DELETE"

_ABSENT_ERROR_CODES = frozenset({"404", "NoSuchKey", "NotFound"})
"""«Obyekt YO'Q» degan javobning uchala shakli — O'LCHANGAN ro'yxat.

O'lchov (2026-08-04, SeaweedFS 4.40):

    head_object(yo'q kalit)  -> Error.Code = "404"        (HTTP 404)
    get_object(yo'q kalit)   -> Error.Code = "NoSuchKey"  (HTTP 404)

`HEAD` javobida TANA yo'q, ya'ni `botocore` kodni XATO TANASIDAN o'qiy
olmaydi va uni status kodidan hosil qiladi — shuning uchun `"404"` va
`"NoSuchKey"` ikkalasi ham ro'yxatda. `"NotFound"` — AWS S3 ning shu
holatdagi kodi; u yozilgan, chunki ombor almashishi SOZLAMA o'zgarishi
bo'lib qolishi kerak.

⚠ `NoSuchBucket` BU RO'YXATDA ATAYIN YO'Q. U ham 404 beradi, lekin ma'nosi
  butunlay boshqa: "bucket yo'q" — bu KONFIGURATSIYA nosozligi va uni
  "kadr yo'q" deb talqin qilish butun kunlik reja bo'yicha jimgina bo'sh
  javob berardi. Fail-closed yo'nalish: u `StorageError` ga aylanadi.
"""


class StorageError(Exception):
    """Ombor javob bermadi yoki amalni rad etdi.

    `botocore` istisnolaridan ALOHIDA sinf: chaqiruvchi (kadr olish jobi)
    uni "kadr olindi, lekin saqlanmadi" degan ANIQ holatga aylantirishi
    kerak — `capture_errors.py` dagi kod aynan shundan qo'yiladi.

    ⚠ MATNIGA `botocore` ISTISNOSI INTERPOLYATSIYA QILINMAYDI (T-04-40).
      Sabab modul docstringining 3-majburiyatida.
    """


def _failure(op: str, exc: Exception) -> StorageError:
    """`botocore` istisnosini SIRSIZ `StorageError` ga aylantiradi (T-04-40).

    Diagnostika uchun UCH fakt yetadi va uchalasi ham sirsiz: qaysi AMAL,
    qaysi ISTISNO TURI, qaysi HTTP STATUS. "Qaysi kalit" savoliga
    chaqiruvchining jurnal qatori javob beradi — u kalitni O'ZI biladi va
    uni istisno matnidan olishi shart emas.

    ⚠ ISTISNO MATNINING INTERPOLYATSIYASI YO'Q va sabab shu funksiyaning
      tanasida EMAS (modul docstringi, 3-majburiyat): qabul mezoni aynan
      shu tanani matn sifatida o'qiydi.
    """
    status: int | None = None
    if isinstance(exc, ClientError):
        metadata = exc.response.get("ResponseMetadata") or {}
        code = metadata.get("HTTPStatusCode")
        status = code if isinstance(code, int) else None
    detail = f"status={status}" if status is not None else "javob yo'q"
    return StorageError(f"ombor `{op}` amali yiqildi: {type(exc).__name__} ({detail})")


async def _call(op: str, request: Awaitable[Any]) -> Any:
    """Bitta ombor chaqiruvi — istisno sirsiz shaklga o'giriladi, zanjir UZILADI.

    ⚠ `raise` BLOKDAN TASHQARIDA va bu `go2rtc.py:315-332` dagi bilan bir
      xil nozik qaror: `except` ichida ko'tarilgan yangi istisnoning
      `__context__` i XOM istisno bo'lib qolardi va uning matni (tarmoq
      sinfida) to'liq ombor manzilini tashiydi. Blok tugagach kontekst
      tozalanadi, ya'ni zanjir HAQIQATAN uziladi — `from None` esa uni
      `__cause__` da ham qoldirmaydi.
    """
    try:
        return await request
    except (ClientError, BotoCoreError, TimeoutError) as exc:
        failure = _failure(op, exc)
    raise failure from None


def _is_absent(exc: ClientError) -> bool:
    """Xato «obyekt yo'q» degan javobmi (`_ABSENT_ERROR_CODES` docstringi)."""
    error = exc.response.get("Error") or {}
    return str(error.get("Code", "")) in _ABSENT_ERROR_CODES


@dataclass(frozen=True, slots=True)
class PutResult:
    """Yozilgan obyektning ombor tomonidan tasdiqlangan holati.

    `size_bytes` YOZILGAN tananing uzunligi: SeaweedFS `PutObject` javobida
    hajmni qaytarmaydi (o'lchandi — javobda faqat `ETag` va `ChecksumCRC32`
    bor), ya'ni uni ombor tomonidan tasdiqlash uchun `head()` kerak bo'lardi
    va bu har yuklashga ikkinchi so'rov qo'shardi.
    """

    etag: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class HeadResult:
    """Omborda MAVJUD obyektning metama'lumoti (`head` `None` bermaganda)."""

    etag: str
    size_bytes: int


class SnapshotStorage:
    """S3 klienti ustidagi YUPQA qobiq — besh amal, boshqa hech nima.

    ⚠ `create_bucket` VA `delete_bucket` UMUMAN YO'Q. Sabab modul
      docstringining 1-majburiyatida va u qayta ochilmaydi.

    ⚠ XOM KLIENT TASHQARIGA CHIQARILMAYDI: `__getattr__` yo'q va klient
      maydoni yopiq. Aks holda "faqat bitta chaqiruv uchun" degan yo'l
      ochilardi va u yerdan `create_bucket` ham, erkin prefiksli listing
      ham bemalol o'tardi.
    """

    def __init__(self, client: Any, *, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def put(self, key: str, data: bytes, *, content_type: str = "image/jpeg") -> PutResult:
        """Kadrni DETERMINISTIK kalit bilan yozadi (ustiga yozish IDEMPOTENT).

        ⚠ TARTIB: avval SHU chaqiruv, KEYIN baza qatori (§B.4). Teskari
          tartib 6-fazaga MAVJUD BO'LMAGAN dalilga havola berardi.

        ⚠ "Yarim muvaffaqiyat" (obyekt bor, qator yo'q) uchun KOMPENSATSIYA
          KODI YOZILMAYDI: kalit deterministik, ya'ni qayta bajarish
          O'SHA obyektni ustiga yozadi va holat izsiz tuzaladi. Yetim
          obyekt esa `orphan_keys` bilan topiladi.
        """
        response = await _call(
            _OP_PUT,
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            ),
        )
        return PutResult(etag=str(response["ETag"]), size_bytes=len(data))

    async def head(self, key: str) -> HeadResult | None:
        """Obyektning metama'lumoti; MAVJUD BO'LMASA — `None`, istisno EMAS.

        ⚠ UCH HOLATLI JAVOBNING BIR OILADAGI QARORI (`go2rtc.py:340-347`):
          "yo'q" va "ayta olmadim" ARALASHTIRILMAYDI. Birinchisi `None`,
          ikkinchisi `StorageError`. Ikkalasini bitta `None` ga yig'ish
          ombor yiqilganda "kadrlar umuman yo'q ekan" degan jimgina
          xulosaga olib kelardi va retention o'sha kunni o'tkazib yuborardi.
        """
        failure: StorageError | None = None
        try:
            response = await self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if not _is_absent(exc):
                failure = _failure(_OP_HEAD, exc)
        except (BotoCoreError, TimeoutError) as exc:
            failure = _failure(_OP_HEAD, exc)
        else:
            return HeadResult(etag=str(response["ETag"]), size_bytes=int(response["ContentLength"]))
        if failure is not None:
            raise failure from None
        return None

    async def get(self, key: str) -> bytes:
        """Obyektning baytlari.

        `head` dan FARQLI o'laroq mavjud bo'lmagan kalit ham `StorageError`
        beradi: "baytlar" savoliga bo'sh javob YO'Q va uni `None` bilan
        ifodalash har bir chaqiruvchini `if` yozishga majbur qilardi.
        """
        response = await _call(_OP_GET, self._client.get_object(Bucket=self._bucket, Key=key))
        body = await _call(_OP_GET, response["Body"].read())
        return bytes(body)

    async def list_prefix(self, prefix: str, *, limit: int | None = None) -> list[str]:
        """Prefiks ostidagi kalitlar — SAHIFALANGAN va TO'LIQ.

        ⚠ FAQAT RETENTION VA YETIM OBYEKT SUPURGISI UCHUN (modul
          docstringi, 2-majburiyat). Foydalanuvchi so'rovi bazadan javob
          oladi.

        O'lchandi (2026-08-04, SeaweedFS 4.40): xom `ListObjectsV2` 1 000
        kalitda KESADI va `IsTruncated` bilan davom etish tokenini beradi.
        Ya'ni sahifalash bu omborga nisbatan HAQIQIY — sahifalanmagan
        chaqiruv 1 001-obyektdan boshlab JIMGINA to'liqsiz ro'yxat berardi
        va retention eng eski kadrlarni hech qachon o'chirmasdi.

        Args:
            prefix: kalit prefiksi (odatda `KEY_PREFIX_FOR_DAY()` ning
                chiqishi).
            limit: shuncha kalit yig'ilgach to'xtaladi. `None` — hammasi.
        """
        keys: list[str] = []
        failure: StorageError | None = None
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                for item in page.get("Contents") or ():
                    keys.append(str(item["Key"]))
                    if limit is not None and len(keys) >= limit:
                        return keys
        except (ClientError, BotoCoreError, TimeoutError) as exc:
            failure = _failure(_OP_LIST, exc)
        if failure is not None:
            raise failure from None
        return keys

    async def delete_many(self, keys: Sequence[str]) -> int:
        """Kalitlarni 1 000 talik to'plamlarda o'chiradi; O'CHIRILGANLAR SONINI beradi.

        ⚠ `Quiet` REJIMI ISHLATILMAYDI VA BU O'LCHANGAN QAROR. `Quiet=True`
          bilan SeaweedFS javobda `Deleted` ni ham, `Errors` ni ham
          UMUMAN qaytarmadi (o'lchandi 2026-08-04: javobda faqat
          `ResponseMetadata`). Ya'ni "nechta o'chdi" va "nimadir
          o'chmadimi" savollarining ikkalasi ham javobsiz qolardi va
          retention har kuni "hammasi o'chdi" deb hisobot berardi.

        Qisman nosozlik JIMGINA o'tkazilmaydi: bitta kalit ham o'chmasa
        `StorageError` ko'tariladi. Retention uchun bu to'g'ri yo'nalish —
        o'chmagan obyekt ertaga qayta uriniladi (predikat holat ustida),
        "o'chdi" deb belgilangan obyekt esa hech qachon qaytmasdi.
        """
        if not keys:
            return 0

        deleted = 0
        for start in range(0, len(keys), _DELETE_BATCH):
            chunk = keys[start : start + _DELETE_BATCH]
            response = await _call(
                _OP_DELETE,
                self._client.delete_objects(
                    Bucket=self._bucket,
                    Delete={"Objects": [{"Key": key} for key in chunk]},
                ),
            )
            errors = response.get("Errors") or ()
            if errors:
                raise StorageError(
                    f"ombor `{_OP_DELETE}` amali {len(errors)} kalitni o'chira olmadi"
                )
            deleted += len(response.get("Deleted") or ())
        return deleted


@asynccontextmanager
async def open(settings: Settings) -> AsyncIterator[SnapshotStorage]:
    """Ombor klientini ochadi va chiqishda YOPADI.

    ⚠ NOM `open` — VA U O'RNAShGAN `builtins.open` NI SOYALAYDI. Bu ataylab:
      modul har doim `storage.open(settings)` shaklida chaqiriladi
      (`from … import open` TAQIQ), ya'ni chaqiruv joyida nom to'liq
      ma'noli bo'ladi va bu modul faylning O'ZI hech qachon `builtins.open`
      ga muhtoj emas.

    Klient `async with` ichida yashaydi: `aiobotocore` ning ulanish puli
    jimgina yopilmaydi va yopilmagan pul `aiohttp` ning "Unclosed
    connector" ogohlantirishi bilan tugardi — ya'ni resurs oqishi FAQAT
    jurnalda ko'rinadigan shaklda qolardi.
    """
    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        # ⚠ OCHIQ QIYMATGA BORISH SHU YERDA VA BOSHQA HECH QAYERDA
        #   (`go2rtc.py:293-296` va `03-04` dagi `nvr_cipher()` bilan bir
        #   xil qoida): bitta, grep bilan topiladigan, ko'zga tashlanadigan
        #   qadam. Ikkinchi joy paydo bo'lishi sanoq darvozasini qizartiradi.
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        # SeaweedFS mintaqani e'tiborsiz qoldiradi, `botocore` esa uni
        # TALAB qiladi — klient `region_name` siz umuman qurilmaydi.
        region_name=settings.s3_region,
        config=AioConfig(
            connect_timeout=_CONNECT_TIMEOUT_SECONDS,
            read_timeout=_READ_TIMEOUT_SECONDS,
            retries={"max_attempts": _MAX_ATTEMPTS, "mode": _RETRY_MODE},
        ),
    ) as client:
        yield SnapshotStorage(client, bucket=settings.s3_bucket)
