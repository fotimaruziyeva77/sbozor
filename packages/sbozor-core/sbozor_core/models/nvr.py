"""NVR domeni: qurilma, uning siri, kameralar (kanallar) va kashfiyot yugurishlari.

=============================================================================
BU FAYLDA UCHTA QAT'IY QAROR YASHAYDI. UCHALASI HAM "QULAYLIK UCHUN"
BUZILISHI OSON, SHUNING UCHUN SABABLARI SHU YERDA TURADI.

1. SIR ALOHIDA JADVALDA (`nvr_credentials`) VA AUDIT TRIGGERIDAN CHIQARILGAN.
   Ikki MUSTAQIL sabab bir xil qarorga olib keladi — pastdagi
   `NvrCredential` docstringiga qarang.

2. `cameras` DA `rtsp_url` USTUNI YO'Q. URL — HOSILA, ustun emas.
   Sabab `Camera` docstringida.

3. KAMERANING IDENTIFIKATSIYA KALITI — `(market_id, nvr_id, channel_no)`.
   Seriya raqami/MAC/IP kalit EMAS (`03-RESEARCH.md` A.4): ular kamera
   almashtirilganda o'zgaradi, kanal esa NVR'dagi jismoniy uyaning o'zi.
   `source_ip`/`source_model` — KUZATILADIGAN atributlar, ya'ni ular
   o'zgarsa bu "boshqa kamera" degani emas, "shu kanaldagi kamera
   almashtirildi" degani va aynan shu fakt 5-fazada zonaning yaroqsiz
   bo'lib qolish sababini beradi.
=============================================================================

TO'RTALA JADVAL HAM TENANT JADVALI (`03-PATTERNS.md` §S-1): `market_id` +
RLS `ENABLE` va `FORCE` + tenant policy + `market_id` bilan boshlanuvchi
domen konstraytlari + composite FK. `market_id` ustunida inline `ForeignKey`
YOZILMAYDI — sabab `models/base.py::market_fk_column()` docstringida.

O'CHIRISH SIYOSATI (D-10): kamera qatori HECH QACHON `DELETE` qilinmaydi.
`is_archived` bayrog'i ishlatiladi, chunki 4-fazadagi snapshotlar va
5-fazadagi zonalar `cameras.id` ga bog'lanadi — qator yo'qolsa ular yetim
qoladi. Yagona istisno — `market_delete_draft()` kaskadi (qoralama bozor
butunlay o'chiriladi va unda hech qanday tarix yo'q).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CIDR, INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.enums import CameraStatus, DiscoveryRunStatus
from sbozor_core.models.base import Base, TenantMixin, TimestampMixin, uuid_pk

__all__ = [
    "CAMERA_STATUS_CHECK",
    "CAMERA_STATUS_VALUES",
    "DISCOVERY_RUN_ACTIVE_STATUSES",
    "DISCOVERY_RUN_STATUS_CHECK",
    "DISCOVERY_RUN_STATUS_VALUES",
    "Camera",
    "NvrCredential",
    "NvrDevice",
    "NvrDiscoveryRun",
]

CAMERA_STATUS_VALUES: tuple[str, ...] = tuple(status.value for status in CameraStatus)
DISCOVERY_RUN_STATUS_VALUES: tuple[str, ...] = tuple(status.value for status in DiscoveryRunStatus)

DISCOVERY_RUN_ACTIVE_STATUSES: tuple[str, ...] = (
    DiscoveryRunStatus.QUEUED.value,
    DiscoveryRunStatus.RUNNING.value,
)
"""«Bir vaqtda ikki skan bo'lolmaydi» qoidasining FAOL to'plami (T-03-16).

`0012_nvr_domain` dagi qisman UNIQUE indeksning predikati AYNAN shu
ro'yxatdan hosil qilinadi, qo'lda ko'chirilmaydi: ikki nusxa ajralib
ketganda indeks jimgina hech nimani qamramay qolardi va NVR ikki barobar
yuk (va ikki barobar `401` urinishi -> hisob qulflanishi) olardi.
"""


def _quoted(values: tuple[str, ...]) -> str:
    """SQL literal ro'yxati. Qiymatlar `StrEnum` a'zolari — tashqi kirish emas.

    `market.py` va `identity.py` dagi jufti bilan bir xil ikki qatorli
    funksiya va u ATAYIN uchinchi marta takrorlanadi: umumiy modulga
    chiqarish `models/base.py` ning ommaviy yuzasini kengaytirardi, har bir
    chaqiruvchi esa baribir O'Z enum'i bilan qulflangan.
    """
    return ", ".join(f"'{value}'" for value in values)


CAMERA_STATUS_CHECK = f"status IN ({_quoted(CAMERA_STATUS_VALUES)})"
"""`cameras.status` faqat ma'lum holatlardan biri (ifoda enum'dan HOSILA)."""

DISCOVERY_RUN_STATUS_CHECK = f"status IN ({_quoted(DISCOVERY_RUN_STATUS_VALUES)})"
"""`nvr_discovery_runs.status` faqat ma'lum holatlardan biri (ifoda enum'dan HOSILA)."""


class NvrDevice(Base, TenantMixin, TimestampMixin):
    """NVR qurilmasi — bozorning kameralarga yagona kirish nuqtasi (CAM-01).

    PAROL BU YERDA YO'Q va bu ATAYIN: u `nvr_credentials` da yashaydi.
    `username` esa shu yerda qoladi — u sir emas, u qurilmaning konfiguratsiya
    atributi va uni ko'rsatish onboarding'da kerak («qaysi hisob bilan
    ulanyapmiz?»). Sirni ajratish sababi `NvrCredential` docstringida.

    `tunnel_subnet` GLOBAL NOYOB (D-07) — bu shu fayldagi YAGONA tenant
    chegarasidan tashqaridagi cheklov va u `0012_nvr_domain` da qisman UNIQUE
    indeks sifatida yoziladi (model darajasida emas, chunki u qisman va
    `market_id` bilan boshlanmaydi). Sabab mahsulot darajasida: ko'p tarmoq
    `192.168.1.0/24` ishlatadi va ikkita bozor bir xil subnet e'lon qilsa
    VPS ning marshrut jadvali chalkashadi — A bozorining trafigi B ga ketishi
    mumkin (T-03-19). `1:1 NAT` yechimi ATAYIN implement qilinmaydi
    (D-07): to'qnashuvda onboarding aniq xato beradi.
    """

    __tablename__ = "nvr_devices"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_nvr_devices_market_id_markets"
        ),
        # Composite FK NISHONI: `cameras`, `nvr_credentials` va
        # `nvr_discovery_runs` `(market_id, nvr_id)` ga havola qiladi, ya'ni
        # cross-tenant bog'lanish SXEMA darajasida yopiladi (T-03-14). RLS
        # chetlab o'tilishi mumkin bo'lgan har qanday yo'lda (migratsiya,
        # `psql`, xato yozilgan `SECURITY DEFINER`) bu FK baribir turadi.
        UniqueConstraint("market_id", "id", name="uq_nvr_devices_market_id_id"),
        # Bitta bozorda bitta NVR ikki marta qo'shilmaydi. `port` kalitga
        # KIRADI: bitta xostda ikkita qurilma (masalan HTTP 80 va 8080 da)
        # bo'lishi haqiqiy holat, `host` ning yolg'iz o'zi esa uni bloklardi.
        UniqueConstraint("market_id", "host", "port", name="uq_nvr_devices_market_id_host_port"),
        CheckConstraint("port BETWEEN 1 AND 65535", name="port_range"),
        # `rtsp_port` NULL bo'lishi MUMKIN ("hali kashf etilmagan"), lekin
        # to'ldirilgan bo'lsa u ham haqiqiy port bo'lishi shart.
        CheckConstraint(
            "rtsp_port IS NULL OR rtsp_port BETWEEN 1 AND 65535", name="rtsp_port_range"
        ),
        # Bo'sh yoki faqat bo'shliqdan iborat `host` hech qachon ulanmaydi va
        # jimgina "fantom qurilma" qatorini yaratardi (`zones.name_not_blank`
        # bilan bir xil sabab).
        CheckConstraint("length(btrim(host)) > 0", name="host_not_blank"),
        CheckConstraint("length(btrim(username)) > 0", name="username_not_blank"),
    )

    id: Mapped[UUID] = uuid_pk()
    # IP yoki hostname. OMMAVIY IP chegarada rad etiladi (`03-RESEARCH.md`
    # C.11) — bu yerda CHECK bilan emas: `inet` tipi ham, matn regex'i ham
    # "xususiy diapazon" ta'rifini DB'ga muzlatib qo'yardi va WireGuard
    # topologiyasi o'zgarganda migratsiya talab qilardi. Ustun `text`,
    # chunki hostname ham qabul qilinadi.
    host: Mapped[str] = mapped_column(Text(), nullable=False)
    port: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("80"))
    use_tls: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=text("false"))
    # ⚠ IKKI USTUN JUFTLIK: `rtsp_port` NULL = "hali skan qilinmagan",
    # `rtsp_port_assumed = true` = "554 fallback ishlatildi" (`03-RESEARCH.md`
    # A.2). Ularni bitta ustunga birlashtirib bo'lmaydi: "kashf etilgan 554"
    # va "taxmin qilingan 554" bir xil raqam, lekin DIAGNOSTIKADA butunlay
    # boshqa holat — birinchisi ishonchli, ikkinchisi jonli ko'rish
    # yiqilganda birinchi tekshiriladigan gumondor.
    rtsp_port: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    rtsp_port_assumed: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("false")
    )
    # OCHIQ MATN — sir EMAS. Parol `nvr_credentials.password_encrypted` da.
    username: Mapped[str] = mapped_column(Text(), nullable=False)
    model: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # Qurilmaning BARQAROR identifikatori — diagnostika uchun kuzatiladi.
    # Kalit sifatida ISHLATILMAYDI: qurilma almashtirilganda `host` o'sha
    # bo'lib qolishi mumkin va o'shanda seriya raqami bo'yicha "yangi NVR"
    # yaratish butun kamera tarixini uzib qo'yardi.
    serial_number: Mapped[str | None] = mapped_column(Text(), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # `NVR` / `IPCamera` — kashfiyot YO'LINI belgilaydi (`03-RESEARCH.md` E.15):
    # NVR uchun `InputProxy/channels`, yakka kamera uchun boshqa endpoint.
    device_type: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # D-07. Noyoblik BOZORLAR ARO va u `0012` dagi qisman UNIQUE indeksda
    # (klass docstringiga qarang) — bu yerda faqat ustunning o'zi.
    tunnel_subnet: Mapped[str | None] = mapped_column(CIDR(), nullable=True)
    last_discovery_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class NvrCredential(Base, TenantMixin):
    """NVR paroli — ALOHIDA jadvalda va AUDIT TRIGGERIDAN BUTUNLAY CHIQARILGAN.

    =========================================================================
    IKKI MUSTAQIL SABAB, BIR XIL QAROR (`03-PATTERNS.md` §S-6, SC#4).

    (a) `fn_audit_row()` `to_jsonb(NEW)` YOZADI. Trigger bu jadvalga ulansa
        Fernet SHIFRMATNI `audit_log.new_value` ga tushardi. Bu ochiq matn
        emas, lekin kalit buzilganda u TARIXIY parollarni ham beradi — ya'ni
        shifrlash o'z ma'nosini yo'qotardi va `audit_log` (append-only,
        o'chirib bo'lmaydigan jadval) eng uzoq yashaydigan sir omboriga
        aylanardi (T-03-13).

    (b) `attach_audit_trigger()` jadvalning birlamchi kaliti `id uuid`
        bo'lishini TALAB qiladi (`fn_audit_row()` `row_id` ni `uuid` ga
        keltiradi). Bu 1:1 jadvalda esa PK — `nvr_id`, ya'ni trigger bu
        yerda TEXNIK jihatdan ham ishlamaydi. `stall_code_registry` bilan
        aynan bir xil holat.

    Ikkalasidan birortasi yolg'iz ham yetarli bo'lardi; ikkitasi birga
    qarorni MUHOKAMASIZ qiladi. Shuning uchun jadval
    `sbozor_core.schema_contract.AUDITED_TABLES` ga QO'SHILMAYDI va bu
    istisno o'sha reyestrning docstringida to'rtinchi band sifatida yozilgan.

    AUDIT IZI YO'QOLMAYDI: parol o'zgarishining FAKTI ilova qatlamida
    `nvr_devices` ustiga QIYMATSIZ yoziladi
    (`action='nvr_credentials_updated'`, `03-RESEARCH.md` E.15) — ya'ni
    "kim, qachon parolni almashtirdi" savoliga javob bor, "parol nima edi"
    savoliga esa hech qachon bo'lmaydi.
    =========================================================================

    `TimestampMixin` YO'Q: `created_at` ma'nosiz (qator NVR bilan birga
    tug'iladi va uning `created_at` i `nvr_devices` da), `updated_at` esa
    ATAYIN mavjud va u YAGONA vaqt belgisi — rotatsiya qachon bo'lganini
    aynan shu ustun aytadi.
    """

    __tablename__ = "nvr_credentials"
    __table_args__ = (
        # PK `nvr_id` — 1:1 munosabat sxemada, ilova qatlamida emas. Ikkinchi
        # qator paydo bo'lsa «qaysi parol amaldagisi?» savoli javobsiz
        # qolardi va ulanish tasodifiy natija berardi.
        PrimaryKeyConstraint("nvr_id", name="pk_nvr_credentials"),
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_nvr_credentials_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "nvr_id"],
            ["nvr_devices.market_id", "nvr_devices.id"],
            name="fk_nvr_credentials_market_id_nvr_id_nvr_devices",
        ),
        # Bo'sh `bytea` — "parol bor" degan YOLG'ON da'vo bo'lardi va
        # ulanish `401` bilan yiqilib, sabab noma'lum qolardi.
        CheckConstraint("octet_length(password_encrypted) > 0", name="password_not_empty"),
        CheckConstraint("key_version > 0", name="key_version_positive"),
    )

    nvr_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # Fernet TOKENI (`cryptography`), ochiq matn EMAS. Kalit env/secret dan
    # keladi va DB'da HECH QACHON saqlanmaydi (CLAUDE.md spec §5).
    password_encrypted: Mapped[bytes] = mapped_column(LargeBinary(), nullable=False)
    # Kalit rotatsiyasini KUZATILADIGAN qiladi: kalit almashtirilganda eski
    # versiyadagi qatorlar qaysiligi so'rov bilan topiladi. Usiz rotatsiya
    # «hammasini qayta shifrlab ko'ramiz» ga aylanardi.
    key_version: Mapped[int] = mapped_column(
        SmallInteger(), nullable=False, server_default=text("1")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Camera(Base, TenantMixin, TimestampMixin):
    """NVR kanali — 4-fazadagi snapshot va 5-fazadagi zonaning tayanch obyekti.

    =========================================================================
    `rtsp_url` USTUNI ATAYIN YO'Q (`03-RESEARCH.md` A.2, `03-PATTERNS.md` §3.1).

    URL SOF FUNKSIYADA hosil qilinadi: `nvr_devices.host` + kashf etilgan
    `rtsp_port` + `{channel_no}01`/`{channel_no}02`. Ustun qo'shilsa IKKITA
    haqiqat manbai paydo bo'lardi va ikkalasi ham noto'g'ri tomonga ketardi:

      * NVR ning IP'si yoki RTSP porti o'zgarganda BITTA qator emas, 25 ta
        kamera URL'i yangilanishi kerak bo'lardi — va bittasi unutilsa
        jonli ko'rish jimgina eski manzilga urinardi;
      * URL ichida foydalanuvchi nomi/parol bo'lishi mumkin bo'lgan shakl
        (`rtsp://user:pass@host/...`) sirni `cameras` jadvaliga, ya'ni
        AUDIT TRIGGERI ULANGAN jadvalga olib kirardi — `NvrCredential`
        docstringidagi butun ajratish bekor bo'lardi.

    ⚠ Bu ustunni «qulaylik uchun» qo'shish taklifi kelsa: qulaylik sof
    funksiyada, ustunda emas.
    =========================================================================

    IKKI BAYROQ, BIR XIL SEMANTIKA — «ADMIN QARORIGA TEGILMAYDI»:

      `name_overridden` — nomni admin qo'lda o'zgartirgan. Qayta skan NVR dan
                          kelgan nomni YOZMAYDI (SC#2: "mavjudi tegilmaydi").
      `is_archived`     — kanalni admin arxivlagan (D-10 dagi soft-delete).
                          Qayta skan uni TIKLAMAYDI.

    Ikkalasi ham bir xil qoidaga bo'ysunadi va bu tasodif emas: kashfiyot
    NVR ni HAQIQAT manbai deb biladi, LEKIN admin qarori undan ustun. Aks
    holda har kechagi skan adminning ishini bekor qilardi va u buni faqat
    ertasi kuni sezardi.

    QATOR HECH QACHON O'CHIRILMAYDI (D-10): 4-fazadagi snapshotlar va
    5-fazadagi zonalar `cameras.id` ga bog'lanadi.
    """

    __tablename__ = "cameras"
    __table_args__ = (
        ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_cameras_market_id_markets"),
        ForeignKeyConstraint(
            ["market_id", "nvr_id"],
            ["nvr_devices.market_id", "nvr_devices.id"],
            name="fk_cameras_market_id_nvr_id_nvr_devices",
        ),
        UniqueConstraint("market_id", "id", name="uq_cameras_market_id_id"),
        # ⚠ SC#2 NING YAGONA DB KAFOLATI (T-03-15).
        #
        #   Ilova qatlamidagi «avval tekshir, keyin yoz» IKKI PARALLEL skanda
        #   ikkalasini ham o'tkazib yuborardi (ikkalasi ham bo'sh holatni
        #   ko'radi) va kanal uchun IKKITA qator tug'ilardi. 5-fazada esa
        #   zona qaysi qatorga bog'langani tasodifga bog'liq bo'lib qolardi.
        #
        #   Konstrayt `market_id` bilan BOSHLANADI — tenant invarianti #5
        #   (`test_tenant_indexes_lead_with_market_id`).
        #
        #   Buzilganda SQLSTATE `23505`; 03-05 dagi upsert aynan shu
        #   konstraytga `ON CONFLICT` qiladi.
        UniqueConstraint(
            "market_id", "nvr_id", "channel_no", name="uq_cameras_market_id_nvr_id_channel_no"
        ),
        # go2rtc'dagi oqim nomi — GLOBAL noyob (`03-RESEARCH.md` D.13).
        # ⚠ Bu ATAYIN tenant chegarasidan tashqarida: go2rtc bitta jarayon va
        #   uning oqim nomlari fazosi BARCHA bozorlar uchun umumiy. Nom
        #   `cam_<uuid4>` ko'rinishida hosil qilinadi, ya'ni to'qnashuv
        #   amalda imkonsiz — konstrayt esa nom QO'LDA berilgan holatda
        #   ikki bozorning oqimini bir-birining ustiga yozishni bloklaydi.
        UniqueConstraint("stream_name", name="uq_cameras_stream_name"),
        CheckConstraint("channel_no > 0", name="channel_no_positive"),
        CheckConstraint(CAMERA_STATUS_CHECK, name="status_allowed"),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
        CheckConstraint("length(btrim(stream_name)) > 0", name="stream_name_not_blank"),
    )

    id: Mapped[UUID] = uuid_pk()
    nvr_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # IDENTIFIKATSIYA KALITI (`03-RESEARCH.md` A.4) — NVR dagi jismoniy uya.
    channel_no: Mapped[int] = mapped_column(Integer(), nullable=False)
    stream_name: Mapped[str] = mapped_column(Text(), nullable=False)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    name_overridden: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("false")
    )
    # `sbozor_core.enums.CameraStatus`. Boshlang'ich qiymat `unknown` va bu
    # ATAYIN: `offline` ni standart qilish «kamera buzuq» degan YOLG'ON
    # dalilni birinchi o'lchovdan OLDIN yozardi.
    status: Mapped[str] = mapped_column(Text(), nullable=False, server_default=text("'unknown'"))
    # D-10 dagi soft-delete. `DELETE` HECH QACHON.
    is_archived: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("false")
    )
    # `{ch}02` mavjudmi (`03-RESEARCH.md` A.2). `true` STANDART, chunki
    # Hikvision NVR larida sub-oqim odatiy holat; kashfiyot uni tekshirib
    # `false` ga tushiradi. Teskari standart har bir kamerani «sub-oqimsiz»
    # deb belgilab, jonli ko'rishni asosiy (og'ir) oqimga majburlardi.
    has_substream: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("true")
    )
    # KUZATILADIGAN atributlar — kalit EMAS (fayl boshidagi 3-band).
    # O'zgarishi `fn_audit_row()` triggeri orqali auditga tushadi va 5-fazada
    # «zona nega yaroqsiz bo'lib qoldi?» savoliga javob beradi.
    source_ip: Mapped[str | None] = mapped_column(INET(), nullable=True)
    source_model: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # HECH QACHON YANGILANMAYDI — kanal birinchi marta qachon ko'rilgani.
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # HAR SKANDA yangilanadi. `last_seen_at` eskirishi «kanal yo'qoldi»
    # signali va u `status` dan MUSTAQIL: status oxirgi O'LCHOVni aytadi,
    # bu ustun esa o'lchov QACHON bo'lganini.
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NvrDiscoveryRun(Base, TenantMixin):
    """Kashfiyot yugurishi — SC#2 ni KUZATILADIGAN qiladigan yozuv (CAM-08).

    Jadval faqat jurnal emas, u IKKI vazifani bajaradi:

      1. Frontend `id` bo'yicha poll qiladi (kashfiyot HTTP so'rovi ichida
         emas, JOB da ishlaydi — `03-RESEARCH.md` E.16).
      2. `status IN ('queued','running')` ustidagi QISMAN UNIQUE indeks
         (`0012_nvr_domain`) bir NVR uchun IKKINCHI parallel skanni
         bloklaydi. Ilova qatlami 409 ni aynan shu konstrayt buzilishidan
         hosil qiladi (03-06), ya'ni «tekshir-keyin-yoz» poygasi yo'q.
         Bu shunchaki tozalik emas: ikki skan NVR ga ikki barobar yuk va
         ikki barobar `401` urinishi beradi — Hikvision hisobi qulflanishi
         mumkin (T-03-16).

    `TimestampMixin` YO'Q: hodisa jadvali `created_at`/`updated_at` emas,
    `started_at`/`finished_at` bilan o'lchanadi va ikkinchi vaqt juftligi
    faqat chalkashlik qo'shardi (`StallAssignment` bilan bir xil qoida).
    """

    __tablename__ = "nvr_discovery_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_nvr_discovery_runs_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "nvr_id"],
            ["nvr_devices.market_id", "nvr_devices.id"],
            name="fk_nvr_discovery_runs_market_id_nvr_id_nvr_devices",
        ),
        UniqueConstraint("market_id", "id", name="uq_nvr_discovery_runs_market_id_id"),
        CheckConstraint(DISCOVERY_RUN_STATUS_CHECK, name="status_allowed"),
        # Yakunlangan yugurishning tugash vaqti boshlanishidan OLDIN
        # bo'lolmaydi — teskari juftlik davomiylikni manfiy qilardi va
        # SC#3 dagi «sekin NVR» o'lchovini ma'nosiz qilardi.
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at", name="finished_after_started"
        ),
        CheckConstraint(
            "channels_found IS NULL OR channels_found >= 0", name="channels_found_non_negative"
        ),
        CheckConstraint(
            "channels_added IS NULL OR channels_added >= 0", name="channels_added_non_negative"
        ),
        CheckConstraint(
            "channels_marked_offline IS NULL OR channels_marked_offline >= 0",
            name="channels_marked_offline_non_negative",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    nvr_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # `sbozor_core.enums.DiscoveryRunStatus`.
    status: Mapped[str] = mapped_column(Text(), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # UCHALASI HAM `NULL` bo'lishi mumkin — yugurish HALI tugamagan. Nolga
    # tenglashtirish «0 ta kanal topildi» degan YOLG'ON natija berardi va
    # `queued` holatdagi yugurish muvaffaqiyatsiz skandan farq qilmasdi.
    channels_found: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    channels_added: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    channels_marked_offline: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    # KOD, MATN EMAS (`03-RESEARCH.md` E.15 / A.3 taksonomiyasi). Frontend
    # uni uch tilga tarjima qiladi (`nvr.error.clock_drift` va h.k.) —
    # CLAUDE.md ning «3 til majburiy» qoidasi. Matn saqlansa u bitta tilda
    # muzlab qolardi.
    error_code: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # Xom diagnostika (drift soniyalari, xom ISAPI javobi).
    # ⚠ YOZISHDAN OLDIN `mask_sensitive` DAN O'TADI (`03-PATTERNS.md` §S-7):
    #   filtr faqat KALIT nomiga qaraydi, ya'ni parol shu yerga NOMLANGAN
    #   kalit sifatida tushishi shart, formatlangan matn ichida hech qachon.
    error_detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    # Kim ishga tushirdi. `users.id` ga FK ATAYIN YO'Q: `users` — GLOBAL
    # jadval (`GLOBAL_TABLES`), unda `market_id` yo'q va composite FK
    # qurib bo'lmaydi; oddiy FK esa foydalanuvchi o'chirilganda kashfiyot
    # tarixini ham olib ketardi. `NULL` = fon/tizim yugurishi
    # (`ActorKind.SYSTEM`).
    triggered_by: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
