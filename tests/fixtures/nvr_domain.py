"""Ikki bozorli NVR seed'i — `two_markets` ustiga qatlanadi.

`fixtures/two_markets.py` bozor + foydalanuvchi + a'zolik qatlamini beradi,
bu modul esa uning ustiga 3-fazaning NVR qatlamini qo'yadi: qurilma, uning
siri, kameralar va bitta yakunlangan kashfiyot yugurishi. Ikki bozor qoidasi
shu yerda ham amal qiladi va sabab bir xil: "0 qator qaytdi" javobi
izolyatsiya ishlaganini ham, jadval bo'shligini ham bildirishi mumkin.

=============================================================================
SEED KONTRAKTI — HAR BIR ELEMENT ANIQ BIR TESTNI OZIQLANTIRADI.

  * **Har bozorda BITTA `nvr_devices` qatori.** A bozorida `host="nvr-sim"`
    (03-02 ning simulyatori bilan bir xil nom — sim testlari seed'ni qayta
    yozmasdan shu qatorga tayanadi), B bozorida esa `host="192.168.2.64"`,
    ya'ni XOM IP. Ikki xil shakl ATAYIN: `host` ustuni `text` va u
    hostname'ni ham, IP'ni ham qabul qilishi kerak — bir xil shakldagi
    ikki qator bu talabni umuman sinamasdi.

  * **Har NVR ga BITTA `nvr_credentials` qatori.** Bayt SHIFRLANMAGAN va bu
    ATAYIN: bu fazada seed sirni HOSIL QILMAYDI (Fernet kaliti test
    muhitida yo'q va uni shu yerda yasash shifrlash kontraktining ikkinchi
    manbaini tug'dirardi). Qator faqat ustunning MAVJUDLIGINI va composite
    FK ning ishlashini tekshiradi. Haqiqiy shifrlash 03-04 da o'z testi
    bilan keladi.

  * **A bozorida UCH kanal, B bozorida BITTA.** Sonlar farqli, chunki
    "kameralar ro'yxati" testi A ni ko'rib B ni ko'rmasligini isbotlashi
    kerak; ikkalasida ham bir xil son bo'lsa noto'g'ri bozorning qatorlari
    qaytganda ham sanoq mos kelib qolardi.

  * **A ning uchinchi kanali ARXIVLANGAN (`is_archived = true`).** D-10
    ning soft-delete'i uchun manfiy holat: "faol kameralar" filtri uni
    chiqarib tashlashi shart. Usiz filtr umuman ishlamaganda ham test
    yashil bo'lardi.

  * **A ning ikkinchi kanalida `name_overridden = true`.** SC#2 ning
    "mavjudi tegilmaydi" bandi uchun: qayta skan bu qatorning nomini
    YOZMASLIGI kerak va 03-05 dagi upsert testi aynan shu qatorga yozishga
    urinadi.

  * **A da bitta YAKUNLANGAN (`succeeded`) kashfiyot yugurishi.** ATAYIN
    `queued`/`running` EMAS: `0012` dagi qisman UNIQUE indeks faol
    yugurishni qulflaydi, ya'ni seed faol qator qoldirsa har qanday
    downstream test "bu NVR da skan allaqachon ketyapti" holatiga tushib
    qolardi va 409 ni SINAB ko'ra olmasdi. Faol qator kerak bo'lgan test
    uni O'ZI yozadi va o'zi tozalaydi.

  * **`tunnel_subnet` FAQAT A bozorida.** D-07 ning bozorlar aro noyoblik
    indeksi qisman (`IS NOT NULL`), ya'ni ikkala bozorda ham `NULL`
    qolsa indeks hech nimani qamramaganini test sezmasdi; ikkalasiga ham
    qiymat berilsa esa seed'ning O'ZI to'qnashuv testini bloklab qo'yardi
    (u ikkinchi qiymatni bo'sh joyga yozishi kerak).
=============================================================================

UUID'LAR DETERMINISTIK EMAS — HAR CHAQIRUVDA YANGI (`uuid4`).
`two_markets` va `market_domain` bilan AYNAN bir xil qaror va sabab ham bir
xil: bozor UUID'lari har testda yangi, ya'ni qotib qolgan NVR UUID'i o'sha
bozorlarga bog'lana olmasdi. `stream_name` esa noyob prefiks bilan
quriladi — u GLOBAL UNIQUE va sobit qiymat ikkinchi testda `23505` berardi.

Seed `sbozor_owner` autocommit ulanishi bilan yoziladi (`market_domain`
bilan bir xil sabab): ma'lumot boshqa ulanishdagi `sbozor_app` testlariga
DARHOL ko'rinishi kerak, va ega `owner_bootstrap` policy'si ostida tenant
kontekstisiz yoza oladi.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import TupleRow

from fixtures.two_markets import TwoMarketSeed

__all__ = [
    "A_CAMERA_CHANNELS",
    "A_HOST",
    "A_TUNNEL_SUBNET",
    "B_CAMERA_CHANNELS",
    "B_HOST",
    "NVR_PASSWORD_PLACEHOLDER",
    "NVR_PORT",
    "NVR_USERNAME",
    "MarketNvrRows",
    "NvrDomainSeed",
    "cleanup_nvr_domain",
    "seed_nvr_domain",
]

NVR_USERNAME = "sbozor"
"""ISAPI hisobi — OCHIQ MATN, sir emas (`nvr_devices.username`)."""

NVR_PORT = 80
"""ISAPI HTTP porti — `nvr_devices.port` ning standarti bilan bir xil."""

NVR_PASSWORD_PLACEHOLDER = b"seed-placeholder-not-a-fernet-token"
"""SHIFRLANMAGAN bayt — seed sirni ATAYIN hosil qilmaydi (modul docstringi).

Nomning o'zi da'voni ochiq aytadi: bu Fernet tokeni EMAS. Kimdir uni
haqiqiy sir deb o'ylab test muhitiga kalit qo'shmoqchi bo'lsa, nom uni
to'xtatadi. `password_encrypted` da faqat `octet_length(...) > 0` CHECK'i
bor, ya'ni bu qiymat sxema talabini to'liq qondiradi.
"""

A_HOST = "nvr-sim"
"""A bozorining NVR xosti — 03-02 simulyatorining compose xizmat nomi.

Sim testlari (`-m sim`) seed'ni QAYTA YOZMASDAN shu qatorga tayanishi
uchun aynan shu nom. Hostname shakli `host` ustunining `text` ekanini ham
sinaydi (B bozoridagi xom IP bilan juftlikda)."""

B_HOST = "192.168.2.64"
"""B bozorining NVR xosti — XOM IP (A dagi hostname bilan juftlik)."""

A_TUNNEL_SUBNET = "192.168.1.0/24"
"""FAQAT A bozorida (D-07). Eng ko'p uchraydigan uy/ofis subneti — ya'ni
to'qnashuv testi haqiqiy stsenariyni takrorlaydi."""

A_CAMERA_CHANNELS = (1, 2, 3)
"""A bozorining kanallari. Uchinchisi ARXIVLANGAN (modul docstringi)."""

B_CAMERA_CHANNELS = (1,)
"""B bozorida BITTA kanal — A dan farqli SON (modul docstringi)."""

A_OVERRIDDEN_CHANNEL = 2
"""Nomi ADMIN tomonidan o'zgartirilgan kanal (SC#2 uchun)."""

A_ARCHIVED_CHANNEL = 3
"""Arxivlangan kanal (D-10 soft-delete uchun manfiy holat)."""

_INSERT_NVR = (
    "INSERT INTO nvr_devices "
    "(id, market_id, host, port, username, model, device_type, "
    " serial_number, rtsp_port, rtsp_port_assumed, tunnel_subnet) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_CREDENTIAL = (
    "INSERT INTO nvr_credentials (market_id, nvr_id, password_encrypted) VALUES (%s, %s, %s)"
)
_INSERT_CAMERA = (
    "INSERT INTO cameras "
    "(id, market_id, nvr_id, channel_no, stream_name, name, "
    " name_overridden, status, is_archived, has_substream) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_DISCOVERY_RUN = (
    "INSERT INTO nvr_discovery_runs "
    "(id, market_id, nvr_id, status, finished_at, channels_found, channels_added) "
    "VALUES (%s, %s, %s, %s, now(), %s, %s)"
)

CLEANUP_ORDER: tuple[str, ...] = (
    "cameras",
    "nvr_discovery_runs",
    "nvr_credentials",
    "nvr_devices",
)
"""O'CHIRISH TARTIBI — FK bo'yicha BOLALARDAN ota-onaga.

Uchala bolasi ham `nvr_devices` ga composite FK `(market_id, nvr_id)` bilan
tayanadi, ya'ni ota-ona oldin o'chirilsa tozalash FK buzilishi bilan
yiqilardi. Bu ro'yxat `migrations/entities/functions.py::MARKET_DELETE_DRAFT`
kaskadidagi tartib bilan BIR XIL va bu tasodif emas — ikkalasi ham bir xil
FK zanjiridan kelib chiqadi.
"""


@dataclass(frozen=True)
class MarketNvrRows:
    """Bitta bozorning NVR qatorlari."""

    market_id: UUID
    nvr_id: UUID
    host: str
    camera_ids: tuple[UUID, ...]
    camera_channels: tuple[int, ...]
    stream_names: tuple[str, ...]
    tunnel_subnet: str | None = None
    discovery_run_ids: tuple[UUID, ...] = ()
    overridden_camera_id: UUID | None = None
    """`name_overridden = true` bo'lgan kamera (SC#2 uchun)."""
    archived_camera_id: UUID | None = None
    """`is_archived = true` bo'lgan kamera (D-10 uchun)."""

    @property
    def active_camera_ids(self) -> tuple[UUID, ...]:
        """Arxivlanmagan kameralar — «faol kameralar» filtrining KUTILMASI.

        Testlar bu qiymatni seed'dan oladi, o'zi hisoblamaydi: hisoblab
        chiqarilgan kutilma filtr mantig'ini takrorlardi va ikkalasi birga
        xato bo'lganda test baribir yashil bo'lardi (`market_domain.py`
        dagi `A_STALL_CODES_BY_SORT` bilan bir xil qoida).
        """
        return tuple(
            camera_id for camera_id in self.camera_ids if camera_id != self.archived_camera_id
        )


@dataclass(frozen=True)
class NvrDomainSeed:
    """Ikki bozorning NVR qatlami."""

    market_a: MarketNvrRows
    market_b: MarketNvrRows

    @property
    def markets(self) -> tuple[MarketNvrRows, MarketNvrRows]:
        return (self.market_a, self.market_b)

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return (self.market_a.market_id, self.market_b.market_id)


def _seed_market_nvr(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    host: str,
    channels: tuple[int, ...],
    tunnel_subnet: str | None,
    with_discovery_run: bool,
) -> MarketNvrRows:
    """Bitta bozorning NVR qatlamini yozadi."""
    nvr_id = uuid4()
    conn.execute(
        _INSERT_NVR,
        (
            str(nvr_id),
            str(market_id),
            host,
            NVR_PORT,
            NVR_USERNAME,
            "DS-7616NI-K2",
            "NVR",
            f"SEED{nvr_id.hex[:12].upper()}",
            554,
            # `rtsp_port_assumed = false` — seed «kashf etilgan» holatni
            # ifodalaydi. `true` qilish har bir downstream testni
            # diagnostika holatidan boshlardi.
            False,
            tunnel_subnet,
        ),
    )
    conn.execute(
        _INSERT_CREDENTIAL,
        (str(market_id), str(nvr_id), NVR_PASSWORD_PLACEHOLDER),
    )

    camera_ids: list[UUID] = []
    stream_names: list[str] = []
    overridden_id: UUID | None = None
    archived_id: UUID | None = None
    for channel_no in channels:
        camera_id = uuid4()
        # GLOBAL UNIQUE (`uq_cameras_stream_name`) — nom har chaqiruvda
        # YANGI bo'lishi shart, aks holda ikkinchi test `23505` berardi.
        # Shakl mahsulot yo'lidagi bilan bir xil: `cam_<uuid>`.
        stream_name = f"cam_{camera_id.hex}"
        is_overridden = channel_no == A_OVERRIDDEN_CHANNEL and len(channels) > 1
        is_archived = channel_no == A_ARCHIVED_CHANNEL and len(channels) > 1
        conn.execute(
            _INSERT_CAMERA,
            (
                str(camera_id),
                str(market_id),
                str(nvr_id),
                channel_no,
                stream_name,
                f"Kanal {channel_no}" if not is_overridden else "Sabzavot qatori (admin nomi)",
                is_overridden,
                # `online` — seed «o'lchangan va ishlayapti» holatini
                # ifodalaydi. `unknown` (ustun standarti) qoldirilsa har bir
                # downstream test o'lchanmagan holatdan boshlardi va
                # "kamera offline" filtri sinalmasdi.
                "online",
                is_archived,
                True,
            ),
        )
        camera_ids.append(camera_id)
        stream_names.append(stream_name)
        if is_overridden:
            overridden_id = camera_id
        if is_archived:
            archived_id = camera_id

    discovery_run_ids: tuple[UUID, ...] = ()
    if with_discovery_run:
        run_id = uuid4()
        # ⚠ `succeeded` — ATAYIN YAKUNLANGAN. `queued`/`running` qoldirilsa
        #   `0012` dagi qisman UNIQUE indeks shu NVR uchun har qanday yangi
        #   faol yugurishni bloklardi va 409 stsenariysi umuman sinalmasdi.
        conn.execute(
            _INSERT_DISCOVERY_RUN,
            (str(run_id), str(market_id), str(nvr_id), "succeeded", len(channels), len(channels)),
        )
        discovery_run_ids = (run_id,)

    return MarketNvrRows(
        market_id=market_id,
        nvr_id=nvr_id,
        host=host,
        camera_ids=tuple(camera_ids),
        camera_channels=channels,
        stream_names=tuple(stream_names),
        tunnel_subnet=tunnel_subnet,
        discovery_run_ids=discovery_run_ids,
        overridden_camera_id=overridden_id,
        archived_camera_id=archived_id,
    )


def seed_nvr_domain(conn: Connection[TupleRow], base: TwoMarketSeed) -> NvrDomainSeed:
    """`two_markets` ustiga NVR qatlamini yozadi.

    `conn` `sbozor_owner` bilan ochilgan va AUTOCOMMIT rejimida bo'lishi
    kerak — `two_markets` bilan aynan bir xil talab.
    """
    market_a = _seed_market_nvr(
        conn,
        market_id=base.market_a.id,
        host=A_HOST,
        channels=A_CAMERA_CHANNELS,
        tunnel_subnet=A_TUNNEL_SUBNET,
        with_discovery_run=True,
    )
    market_b = _seed_market_nvr(
        conn,
        market_id=base.market_b.id,
        host=B_HOST,
        channels=B_CAMERA_CHANNELS,
        # `NULL` — D-07 to'qnashuv testi ikkinchi qiymatni bo'sh joyga
        # yozishi kerak (modul docstringi).
        tunnel_subnet=None,
        # B bozorida kashfiyot yugurishi YO'Q: "yugurishlar ro'yxati bo'sh"
        # holati ham sinalishi kerak va ikkala bozorda ham qator bo'lsa
        # bunday nazorat holati qolmasdi.
        with_discovery_run=False,
    )
    return NvrDomainSeed(market_a=market_a, market_b=market_b)


def cleanup_nvr_domain(conn: Connection[TupleRow], seed: NvrDomainSeed) -> None:
    """NVR qatlamini FK tartibida o'chiradi.

    ⚠ `cameras` da `is_archived` SOFT-DELETE bo'lsa ham bu yerda QATTIQ
    `DELETE` ishlatiladi va bu ZIDDIYAT EMAS: D-10 mahsulot yo'liga
    tegishli (kamera 4-fazadagi snapshotlar va 5-fazadagi zonalar bilan
    bog'langan), test seed'ida esa hech qanday tarix yo'q.
    `market_delete_draft()` kaskadi ham aynan shu tartibda yuradi.
    """
    market_ids = [str(market_id) for market_id in seed.market_ids]

    for table in CLEANUP_ORDER:
        # Jadval nomlari shu moduldagi SOBIT `CLEANUP_ORDER` dan keladi —
        # tashqi kirish emas, ya'ni f-string bu yerda xavfsiz
        # (`market_domain.py` dagi jufti bilan bir xil naqsh).
        conn.execute(
            f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
            (market_ids,),
        )
