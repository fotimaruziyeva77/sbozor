"""W0-3 ZONDI — ko'r audit namunasining SQL yo'li kengaytmasiz ishlaydimi.

=============================================================================
ZONDNING TO'RT SAVOLI:

    1. Yadro `sha256(bytea)` chaqirilishi MUMKINMI — hech qanday
       kengaytmasiz (`postgres:18.4`)?
    2. `pgcrypto` ning hash funksiyasi bazada YO'QMI?
    3. Hosila urug' + hash tartibi IKKI ALOHIDA SESSIYADA aynan bir xil
       to'plam beradimi?
    4. Turning raqami o'zgarganda to'plam O'ZGARADIMI (urug' haqiqatan
       ta'sir qiladimi)?

Javob `migrations/versions/0018_occupancy_domain.py` NING SHAKLINI
belgilaydi: `require_extension()` chaqiriladimi yoki YO'QMI, va
`ops/db/init/00-extensions.sql` ga yangi satr qo'shiladimi.

⚠ NEGA JADVAL EMAS, ZOND. `audit_rounds` ning o'zi hali mavjud emas
  (`0018` uni shu o'lchovdan KEYIN yaratadi) va aynan shu sabab o'lchovni
  migratsiyadan OLDIN qilishga majbur qiladi: natijani keyin bilib olish
  QAYTA MIGRATSIYA demakdir. Shabloni — `tests/fixtures/billable_probe.py`
  (u ham mavjud bo'lmagan jadvalning DDL yo'lini oldindan isbotlagan).

⚠ HAR FAKT ALOHIDA SQL BILAN O'LCHANADI VA BU MAJBURIY. Birlashtirilsa
  bitta faktning nosozligi qolganlarining natijasini yutib yuborardi va
  zond «nima ishlamadi» ni ayta olmasdi — natija «zond qurilmadi» degan
  ma'nosiz signalga aylanardi (`billable_probe.py` dagi bilan bir xil
  qoida).

⚠ BU FAYLDA QARORNING SABABI YO'Q — VA BU ATAYIN. Rad etilgan
  muqobillarning NOMLARI bu yerda umuman yozilmaydi; ular
  `tests/tenancy/test_audit_seed_probe.py` ning modul docstringida
  yashaydi. Sabab 3-fazada o'lchangan: taqiqlangan literal skanerlanadigan
  faylning IZOHIDA ham yozilmasligi kerak, aks holda sodda darvoza o'zini
  o'zi qizartiradi va yagona «tuzatish» yo'li darvozani BO'SHATISH bo'lardi.
  Shu sababdan `_PGCRYPTO_PROBE_SQL` — bu fayldagi YAGONA joy, u yerda
  o'lchanayotgan funksiya nomi uchraydi.
=============================================================================

Jadval `sbozor_owner` bilan yaratiladi (`sbozor_app` `public` sxemada
obyekt yarata olmaydi — T-01-06) va har testdan keyin o'chiriladi. RLS
ATAYIN yoqilmaydi: bu zond TARTIBNI o'lchaydi, izolyatsiyani emas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import psycopg
from psycopg import Connection
from psycopg.rows import TupleRow

__all__ = [
    "PROBE_TABLE",
    "SAMPLE_LIMIT",
    "AuditSeedProbe",
    "create_audit_seed_probe",
    "drop_audit_seed_probe",
    "sample_ids",
]

# Jadval nomi SQL matnlarida LITERAL yozilgan (`billable_probe.py:60-63` da
# takrorlangan, `financial.py:53-58` da o'rnatilgan qoida).
PROBE_TABLE = "probe_audit_frames"

_DROP_SQL = "DROP TABLE IF EXISTS probe_audit_frames"

# Kadrlar soni ATAYIN namuna hajmidan ANCHA katta: 5/40 tanlovda ikki xil
# tartibning AYNI to'plamni berish ehtimoli 1/658008, ya'ni 4-fakt
# («tur o'zgarsa to'plam o'zgaradi») ma'noli bo'ladi. Kichik jadvalda
# (masalan 6 qator) u tasodifan yashil bo'lib qolishi mumkin edi.
_FRAME_COUNT: Final = 40
SAMPLE_LIMIT: Final = 5

# ⚠ ID LAR QADALGAN — `uuidv7()` ATAYIN ISHLATILMAYDI.
#
# `uuidv7()` har yugurishda BOSHQA identifikatorlar berardi, ya'ni 3- va
# 4-faktlar har safar BOSHQA ma'lumot ustida o'lchanardi va «gohida
# yiqiladi» degan eng yomon test turi tug'ilardi (`frames.py` MAJBURIYAT 2:
# bir xil argument -> bir xil baytlar). Qadalgan ID lar bilan zondning
# natijasi TAKRORLANADI va qizargan holat qayta tiklanadi.
#
# Shakl `00000000-0000-4000-8000-<12 hex>` — yaroqli v4 varianti, lekin
# qiymati to'liq hosila. Qiymatning O'ZI ahamiyatsiz, QADALGANLIGI
# ahamiyatli (`frames.py:102-103`).
_CREATE_TABLE = """
CREATE TABLE probe_audit_frames (
    id uuid PRIMARY KEY
)
"""

_SEED_FRAMES = """
INSERT INTO probe_audit_frames (id)
SELECT ('00000000-0000-4000-8000-' || lpad(to_hex(g), 12, '0'))::uuid
FROM generate_series(1, %s) AS g
"""

# --- 1-FAKT: yadro hash funksiyasi, kengaytmasiz --------------------------
#
# `bytea` qaytadi (32 bayt). Natija QIYMATI tekshirilmaydi — savol
# «funksiya CHAQIRILADIMI», «u to'g'ri hash beradimi» emas: ikkinchisi
# PostgreSQL ning o'z testlari zimmasida.
_SHA256_PROBE_SQL = "SELECT length(sha256('sbozor-w0-3'::bytea))"

# --- 2-FAKT: kengaytma funksiyasi YO'QLIGI --------------------------------
#
# ⚠ BU SATR — FUNKSIYA NOMI UCHRAYDIGAN YAGONA JOY. U boshqa hech qayerda,
#   jumladan izohlarda ham, takrorlanmaydi (yuqoridagi modul docstringiga
#   qarang).
_PGCRYPTO_PROBE_SQL = "SELECT digest('sbozor-w0-3'::bytea, 'sha256')"

# --- 3/4-FAKT: hosila urug' + hash tartibi --------------------------------
#
# Urug' TANLANMAYDI, HOSILA qilinadi: `(market_id, business_date, round_no)`
# uchligidan. Ya'ni namunani tortayotgan odamda «boshqa urug' sinab
# ko'raman» degan harakatning O'ZI yo'q — uchlik biznes fakti, tanlov emas.
#
# Ikkala bosqich ham BITTA so'rovda va bu ataylab: urug'ni ilovada
# hisoblash `0018` ning yo'lini boshqa (uchinchi) yo'lga aylantirardi,
# zond esa AYNAN migratsiya yozadigan yo'lni o'lchashi kerak.
_SAMPLE_SQL = """
WITH derived_seed AS (
    SELECT encode(
        sha256((%(market_id)s || '|' || %(business_date)s || '|' || %(round_no)s)::bytea),
        'hex'
    ) AS value
)
SELECT f.id
FROM probe_audit_frames f, derived_seed s
ORDER BY sha256((f.id::text || s.value)::bytea)
LIMIT %(limit)s
"""

_SERVER_VERSION = "SELECT version()"


@dataclass(frozen=True)
class AuditSeedProbe:
    """O'lchov natijasi — to'rtta fakt va ular olingan server.

    ⚠ MAYDON NOMLARI KATTA HARFDA VA BU ATAYIN. Bular obyektning
    xususiyatlari emas, O'LCHOVNING NATIJALARI: `05-05` ularni
    `0018_occupancy_domain.py` ning `audit_rounds` docstringiga AYNAN shu
    nomlar bilan ko'chiradi (`04-01` ning `BILLABLE_ANCHOR_SUPPORTED` i
    bilan bir xil qoida). Nom o'zgarsa ikki hujjat jimgina ajralib
    ketardi.

    `FAILURE` `AUDIT_SEED_SHA256_SUPPORTED = False` bo'lganda xatoning
    TO'LIQ matnini tashiydi: yalang'och `False` `05-05` ga `0018` ni
    qanday yozishni aytmasdi, xato matni esa aytadi.

    `SERVER_VERSION` SUMMARY uchun: o'lchov AYNAN qaysi serverda olingani
    yozilmasa, natija keyinroq «qayerda o'lchangan?» degan javobsiz
    savolga aylanardi.
    """

    conn: Connection[TupleRow]
    AUDIT_SEED_SHA256_SUPPORTED: bool
    PGCRYPTO_ABSENT: bool
    FAILURE: str | None
    SERVER_VERSION: str


def create_audit_seed_probe(conn: Connection[TupleRow]) -> AuditSeedProbe:
    """Zond jadvalini quradi va 1- hamda 2-faktni ALOHIDA o'lchaydi.

    3- va 4-faktlar bu yerda o'lchanmaydi: ular IKKI ALOHIDA SESSIYANI
    talab qiladi, ulanishlarni boshqarish esa test qatlamining (pytest
    fixture'larining) ishi — `billable_probe.py` bilan bir xil chegara.
    Ular uchun `sample_ids()` bor.

    Jadvalning yiqilishi KUTILMAGAN holat va u ATAYIN yuqoriga ko'tariladi:
    bitta `uuid` ustunli jadval allaqachon isbotlangan sinf, ya'ni u
    yerdagi xato zondning savoliga emas, muhitga tegishli (noto'g'ri
    huquq, yetishmayotgan rol) va uni faktga aylantirish o'lchovni
    SOXTALASHTIRARDI.
    """
    drop_audit_seed_probe(conn)

    row = conn.execute(_SERVER_VERSION).fetchone()
    assert row is not None, "`SELECT version()` javob bermadi"
    server_version = str(row[0])

    conn.execute(_CREATE_TABLE)
    conn.execute(_SEED_FRAMES, (_FRAME_COUNT,))

    sha256_supported = True
    failure: str | None = None
    try:
        sha256_row = conn.execute(_SHA256_PROBE_SQL).fetchone()
    except psycopg.Error as error:
        sha256_supported = False
        failure = f"{type(error).__name__}: {error}".strip()
    else:
        assert sha256_row is not None, "hash so'rovi qator qaytarmadi"

    # 2-FAKT TESKARI YO'NALISHDA O'LCHANADI: kutilgan natija — XATO.
    # Muvaffaqiyat bu yerda «kengaytma bazada bor» degani va u qarorni
    # o'zgartirardi (`0018` da `require_extension()` ma'noli bo'lib
    # qolardi), shuning uchun u ham FAKT sifatida qayd etiladi, jimgina
    # o'tkazib yuborilmaydi.
    try:
        conn.execute(_PGCRYPTO_PROBE_SQL)
    except psycopg.errors.UndefinedFunction:
        pgcrypto_absent = True
    else:
        pgcrypto_absent = False

    return AuditSeedProbe(
        conn=conn,
        AUDIT_SEED_SHA256_SUPPORTED=sha256_supported,
        PGCRYPTO_ABSENT=pgcrypto_absent,
        FAILURE=failure,
        SERVER_VERSION=server_version,
    )


def sample_ids(
    conn: Connection[TupleRow],
    *,
    market_id: str,
    business_date: str,
    round_no: int,
    limit: int = SAMPLE_LIMIT,
) -> list[str]:
    """Hosila urug' bo'yicha tortilgan namunani QATOR TARTIBIDA qaytaradi.

    Ro'yxat (to'plam emas) qaytadi va bu ataylab: chaqiruvchi to'plam
    tengligini ham, TARTIB tengligini ham o'lchay olsin. `ORDER BY` ning
    o'zi ham qayta chiqarilishi kerak — aks holda «bir xil beshta kadr,
    lekin boshqa navbatda» holati sezilmay qolardi.
    """
    rows = conn.execute(
        _SAMPLE_SQL,
        {
            "market_id": market_id,
            "business_date": business_date,
            "round_no": str(round_no),
            "limit": limit,
        },
    ).fetchall()
    return [str(row[0]) for row in rows]


def drop_audit_seed_probe(conn: Connection[TupleRow]) -> None:
    """Zond jadvalini o'chiradi.

    Tozalash MAJBURIY: `DROP` qilinmasa keyingi yugurish `DuplicateTable`
    bilan yiqilardi va sabab o'lchov natijasi kabi ko'rinardi.
    """
    conn.execute(_DROP_SQL)
