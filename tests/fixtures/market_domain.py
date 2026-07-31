"""Ikki bozorli DOMEN seed'i — `two_markets` ustiga qatlanadi.

`fixtures/two_markets.py` bozor + foydalanuvchi + a'zolik qatlamini beradi,
bu modul esa uning ustiga 2-fazaning DOMEN qatlamini qo'yadi: profil, zona,
toifa, rasta, tarif, toifa davri, sotuvchi va biriktirish. Ikki bozor
qoidasi shu yerda ham amal qiladi va sabab bir xil: "0 qator qaytdi" javobi
izolyatsiya ishlaganini ham, jadval bo'shligini ham bildirishi mumkin.

=============================================================================
SEED KONTRAKTI — HAR BIR ELEMENT ANIQ BIR TESTNI OZIQLANTIRADI.
Hech biri "to'liqlik uchun" emas; birortasini olib tashlash aniq bir
downstream testni YOLG'ON-YASHIL qiladi:

  * **Har rastaga bittadan toifa davri (MAJBURIY).** 02-08 dagi ro'yxat va
    xarita so'rovlari joriy toifani `LEFT JOIN LATERAL` bilan qidiradi.
    Qator bo'lmasa natija `NULL` bo'ladi va downstream test "toifa yo'q"
    bilan "toifa NOTO'G'RI" ni AJRATA OLMAYDI; tarif qidiruvi ham (u toifa
    orqali boradi) jimgina bo'sh bo'lib qolardi. 02-11 dagi
    `stalls_with_category` sanog'i ham aynan shu jadvaldan o'qiydi.
  * **Toifalar rastalar bo'ylab TAQSIMLANADI**, bitta toifaga jamlanmaydi —
    aks holda "toifa bo'yicha filtr" testi hech nimani ajratmasdi va
    filtr umuman ishlamaganda ham yashil bo'lardi.
  * **`valid_from` = `market_profile.operating_since`** (A3), import kuni
    EMAS. Aks holda 6-faza `operating_since` dan bugungacha bo'lgan har bir
    kunni "tarifsiz/toifasiz" deb topib butun tarixni anomaliyaga
    aylantirardi.
  * **A bozorida uch xil biriktirish holati** — D-10 almashinuvi, D-11
    bo'shlig'i va D-11 ning ikkinchi shakli (umuman biriktirilmagan rasta).
  * **B bozorida bitta toifa TARIFSIZ qoladi** — bu ATAYIN nuqson: 02-11
    dagi `activate` to'liqlik tekshiruvi ("har toifada tarif bor") uchun
    manfiy holat kerak, aks holda u faqat baxtli yo'lda sinalardi.
=============================================================================

Seed `sbozor_owner` autocommit ulanishi bilan yoziladi (`two_markets` bilan
bir xil sabab): ma'lumot boshqa ulanishdagi `sbozor_app` testlariga DARHOL
ko'rinishi kerak, va ega `owner_bootstrap` policy'si ostida tenant
kontekstisiz yoza oladi.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import TupleRow
from psycopg.types.range import Range as PgRange
from sbozor_core.periods import assignment_period

from fixtures.two_markets import TwoMarketSeed

__all__ = [
    "A_STALL_CODES",
    "A_STALL_CODES_BY_SORT",
    "GAP_DAY",
    "HANDOVER_DAY",
    "MarketDomainRows",
    "MarketDomainSeed",
    "cleanup_market_domain",
    "seed_market_domain",
    "to_pg_period",
]

# ---------------------------------------------------------------------------
# A bozori — 3 zona / 3 toifa / 6 rasta / 3 sotuvchi / 4 biriktirish
# ---------------------------------------------------------------------------

A_OPERATING_SINCE = date(2026, 1, 15)
"""A bozorining ish boshlagan sanasi — ATAYIN O'TGAN SANA.

Karmana holatiga mos (bozor yillar davomida ishlagan, raqamlashtirish esa
bugun boshlanadi) va 02-09 dagi "boshlang'ich narx" tarmog'ini sinash
imkonini beradi: `valid_from` bugundan OLDIN bo'lgan tarif D-07 qulfi ostida
turadi, ya'ni tahrirlash yo'li yopiq.
"""

A_OPEN_WEEKDAYS = (2, 3, 4, 5, 6, 7)
"""ISO kun raqamlari — DUSHANBA (1) YO'Q, ya'ni A bozori dushanba yopiq.

Bu `market_is_open()` testlari uchun boshlang'ich holat: haftalik jadval
qatlami hech qanday istisno qatorisiz ham `false` beradigan kun kerak.
"""

A_STALL_CODES = ("2", "10", "100", "7", "55", "3")
"""Kiritish tartibi ATAYIN ARALASH va kodlar ATAYIN shunday tanlangan.

`ORDER BY code_sort` -> `2, 3, 7, 10, 55, 100` (inson-raqamli),
`ORDER BY code`      -> `10, 100, 2, 3, 55, 7` (matn tartibi).
Ikkalasi bir-biridan farq qilmasa `code_sort` umuman ishlamaganda ham
tartib testi yashil bo'lib qolardi.
"""

A_STALL_CODES_BY_SORT = ("2", "3", "7", "10", "55", "100")
"""`ORDER BY code_sort` ning KUTILGAN natijasi — QO'LDA yozilgan literal.

ATAYIN hisoblab chiqarilmaydi (`sorted(..., key=int)` bilan emas): hisoblab
chiqarilgan kutilma DB ifodasining o'z mantiqini takrorlardi va ikkalasi
birga xato bo'lganda test baribir yashil bo'lardi. Bu ro'yxat — INSON
tekshirgan javob.
"""

A_CATEGORY_NAMES = ("Sabzavot", "Go'sht", "Kiyim")
A_ZONE_NAMES = ("Markaziy", "Sharqiy", "G'arbiy")
A_TARIFF_AMOUNTS = (5_000, 12_000, 8_000)
"""Toifa narxlari HAR XIL — "D sanadagi tarif" qidiruvi qaysi qatorni
topganini ajrata olishi uchun. Bir xil summalar bilan test noto'g'ri
toifaning tarifini topganda ham yashil bo'lardi."""

A_VENDOR_NAMES = ("Aliyev Vali", "Karimova Nodira", "Rasulov Sardor")
A_VENDOR_PHONES = ("+998901110001", "+998901110002", "+998901110003")
"""Telefonlar SOBIT (global hisoblagich YO'Q) va bu D-12 ning bevosita natijasi.

`users.phone_e164` GLOBAL unique, shuning uchun `two_markets` u yerda
hisoblagich ishlatadi. `vendors` da esa unikalik faqat `(market_id,
phone_e164)` bo'yicha — har test YANGI bozor UUID'lari oladi, ya'ni sobit
telefonlar hech qachon to'qnashmaydi. Aksincha, ular B bozorida ATAYIN
QAYTA ISHLATILADI (pastga qarang).
"""

# D-10 / D-11 stsenariysi. Sanalar SOBIT: davrlar chegarasi testda emas,
# SEED da bir marta ta'riflanadi va downstream testlar shu yerdan oladi.
HANDOVER_START = date(2026, 8, 1)
HANDOVER_DAY = date(2026, 8, 10)
"""D-10: almashinuv KUNI — eski sotuvchining davri shu kuni tugaydi va
AYNAN shu kun YANGI sotuvchiga tegishli (`[)` chegarasi)."""

GAP_START = date(2026, 8, 1)
GAP_CLOSED_AT = date(2026, 8, 5)
GAP_REOPENED_AT = date(2026, 8, 20)
"""D-11: `2026-08-05` … `2026-08-19` oralig'ida rasta SOTUVCHISIZ.

Bu XATO EMAS — 6-faza aynan shu bo'shliqni "band, lekin sotuvchisiz"
anomaliyasi sifatida topadi. Davrlar uzluksizligi hech qayerda
majburlanmaydi.
"""

GAP_DAY = date(2026, 8, 10)
"""Bo'shliq ichidagi kun — `period @> :d` shu kunda 0 qator berishi shart."""

# ---------------------------------------------------------------------------
# B bozori — kichikroq to'plam (cross-tenant nazorat holati)
# ---------------------------------------------------------------------------

B_OPERATING_SINCE = date(2026, 2, 1)
"""A dan FARQLI sana — test ikkalasini tasodifan tenglashtirib qo'ymasin."""

B_OPEN_WEEKDAYS = (1, 2, 3, 4, 5, 6, 7)
"""B har kuni ochiq — A ning dushanbasi bilan solishtirish uchun nazorat holati."""

B_STALL_CODES = ("1", "2")
B_CATEGORY_NAMES = ("Meva", "Quruq meva")
B_ZONE_NAMES = ("Yagona",)
B_TARIFF_AMOUNT = 7_000
B_VENDOR_NAME = "Boboyev Jasur"
B_VENDOR_PHONE = A_VENDOR_PHONES[0]
"""A bozorining BIRINCHI sotuvchisi bilan AYNAN BIR XIL telefon — ATAYIN.

D-12: unikalik BOZOR ICHIDA. Bir odam ikki bozorda savdo qilishi mumkin va
MVP uni ikki alohida qator sifatida ko'radi. Seed shu holatni O'ZIDA
ifodalaydi, ya'ni kimdir `UNIQUE(phone_e164)` ni global qilib qo'ysa seed
DARHOL yiqiladi va sabab ko'rinadi (T-02-44).
"""

B_ASSIGNMENT_START = date(2026, 8, 1)


@dataclass(frozen=True)
class MarketDomainRows:
    """Bitta bozorning domen qatorlari."""

    market_id: UUID
    operating_since: date
    open_weekdays: tuple[int, ...]
    zone_ids: tuple[UUID, ...]
    category_ids: tuple[UUID, ...]
    stall_ids: tuple[UUID, ...]
    stall_codes: tuple[str, ...]
    vendor_ids: tuple[UUID, ...]
    assignment_ids: tuple[UUID, ...]
    category_by_stall: dict[UUID, UUID] = field(default_factory=dict)
    """`stall_id -> category_id` — seed yozgan BOSHLANG'ICH toifa davri.

    Testlar "joriy toifa" `LEFT JOIN LATERAL` qidiruvining natijasini shu
    xarita bilan solishtiradi; usiz ular DB nima qaytarsa shuni "to'g'ri"
    deb qabul qilardi.
    """
    tariff_by_category: dict[UUID, UUID] = field(default_factory=dict)
    """`category_id -> tariff_id`. B bozorida BITTA toifa bu xaritada YO'Q."""

    handover_stall_id: UUID | None = None
    """D-10: sotuvchi almashgan rasta (ikkita ketma-ket davr)."""
    gap_stall_id: UUID | None = None
    """D-11: davrlari orasida ATAYIN bo'shliq qoldirilgan rasta."""
    unassigned_stall_id: UUID | None = None
    """D-11 ning ikkinchi shakli: hech qachon biriktirilmagan rasta."""


@dataclass(frozen=True)
class MarketDomainSeed:
    """Ikki bozorning domen qatlami."""

    market_a: MarketDomainRows
    market_b: MarketDomainRows

    @property
    def markets(self) -> tuple[MarketDomainRows, MarketDomainRows]:
        return (self.market_a, self.market_b)

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return (self.market_a.market_id, self.market_b.market_id)


_INSERT_PROFILE = (
    "INSERT INTO market_profile (market_id, operating_since, open_weekdays) VALUES (%s, %s, %s)"
)
_INSERT_ZONE = "INSERT INTO zones (id, market_id, name) VALUES (%s, %s, %s)"
_INSERT_CATEGORY = "INSERT INTO stall_categories (id, market_id, name) VALUES (%s, %s, %s)"
_INSERT_STALL = "INSERT INTO stalls (id, market_id, zone_id, code) VALUES (%s, %s, %s, %s)"
_INSERT_TARIFF = (
    "INSERT INTO tariffs (id, market_id, category_id, amount_soum, valid_from) "
    "VALUES (%s, %s, %s, %s, %s)"
)
_INSERT_CATEGORY_PERIOD = (
    "INSERT INTO stall_category_periods (id, market_id, stall_id, category_id, valid_from) "
    "VALUES (%s, %s, %s, %s, %s)"
)
_INSERT_VENDOR = (
    "INSERT INTO vendors (id, market_id, full_name, phone_e164) VALUES (%s, %s, %s, %s)"
)
_INSERT_ASSIGNMENT = (
    "INSERT INTO stall_assignments (id, market_id, stall_id, vendor_id, period) "
    "VALUES (%s, %s, %s, %s, %s)"
)

CLEANUP_ORDER: tuple[str, ...] = (
    "stall_assignments",
    "stall_category_periods",
    "tariffs",
    "market_calendar_exceptions",
    "stall_code_registry",
    "stalls",
    "vendors",
    "zones",
    "stall_categories",
    "market_profile",
)
"""O'CHIRISH TARTIBI — FK bo'yicha bolalardan ota-onaga.

`market_calendar_exceptions` seed tomonidan YOZILMAYDI, lekin ro'yxatda
ATAYIN bor: kalendar testlari o'z istisnolarini qo'shadi va ular tozalanmasa
keyingi testda `UNIQUE(market_id, exception_date)` ni buzardi yoki
`markets` ni o'chirish FK bilan yiqilardi.
"""


def to_pg_period(start: date, end: date | None) -> PgRange[date]:
    """`assignment_period()` natijasini psycopg qiymatiga o'tkazadi.

    OMMAVIY: biriktirish yozadigan TESTLAR ham shu yerdan o'tadi, o'z
    `daterange(...)` satrini qurmaydi — quyidagi sabab ular uchun ham
    bir xil kuchda.

    ⚠ CHEGARA HARFI (`'[)'`) BU MODULDA HECH QAYERDA YOZILMAYDI va xom
    `daterange(...)` SQL matni ham qurilmaydi. Konvensiya AYNAN bitta
    joyda — `sbozor_core.periods.PERIOD_BOUNDS` da — yashaydi va bu yerga
    `assignment_period()` ning qaytargan qiymatidan (`period.bounds`)
    KO'CHIRILADI. Aks holda seed ikkinchi haqiqat manbai bo'lib qolardi:
    kimdir konvensiyani `'[]'` ga o'zgartirsa mahsulot kodi o'zgarardi-yu,
    seed eski shaklda qolib testlarni yashil ko'rsatib turardi — ya'ni
    almashinuv kunidagi eng qimmat xato aynan testdan yashirinardi.

    Ikki `Range` sinfi bir-biriga o'tkaziladi (SQLAlchemy -> psycopg), chunki
    seed ORM emas, xom `psycopg` ulanishi bilan yozadi.
    """
    period = assignment_period(start, end)
    return PgRange(period.lower, period.upper, period.bounds)


def _seed_market(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    operating_since: date,
    open_weekdays: tuple[int, ...],
    zone_names: tuple[str, ...],
    category_names: tuple[str, ...],
    stall_codes: tuple[str, ...],
    tariff_amounts: tuple[int, ...],
    vendor_names: tuple[str, ...],
    vendor_phones: tuple[str, ...],
) -> MarketDomainRows:
    """Bitta bozorning umumiy qatlamini yozadi (biriktirishlarSIZ).

    `tariff_amounts` `category_names` dan KALTAROQ bo'lishi mumkin — o'shanda
    oxirgi toifa(lar) TARIFSIZ qoladi. B bozori aynan shu holatdan
    foydalanadi (modul docstringi).
    """
    conn.execute(_INSERT_PROFILE, (str(market_id), operating_since, list(open_weekdays)))

    zone_ids = tuple(uuid4() for _ in zone_names)
    for zone_id, name in zip(zone_ids, zone_names, strict=True):
        conn.execute(_INSERT_ZONE, (str(zone_id), str(market_id), name))

    category_ids = tuple(uuid4() for _ in category_names)
    for category_id, name in zip(category_ids, category_names, strict=True):
        conn.execute(_INSERT_CATEGORY, (str(category_id), str(market_id), name))

    tariff_by_category: dict[UUID, UUID] = {}
    for category_id, amount in zip(category_ids, tariff_amounts, strict=False):
        tariff_id = uuid4()
        # A3: `valid_from` `operating_since` dan — import kunidan EMAS.
        conn.execute(
            _INSERT_TARIFF,
            (str(tariff_id), str(market_id), str(category_id), amount, operating_since),
        )
        tariff_by_category[category_id] = tariff_id

    stall_ids = tuple(uuid4() for _ in stall_codes)
    category_by_stall: dict[UUID, UUID] = {}
    for index, (stall_id, code) in enumerate(zip(stall_ids, stall_codes, strict=True)):
        # Zonalar ham, toifalar ham rastalar bo'ylab AYLANMA taqsimlanadi:
        # hammasi bitta zonaga/toifaga tushsa zona va toifa filtri testlari
        # hech nimani ajratmasdi.
        zone_id = zone_ids[index % len(zone_ids)]
        category_id = category_ids[index % len(category_ids)]
        conn.execute(_INSERT_STALL, (str(stall_id), str(market_id), str(zone_id), code))
        # HAR RASTAGA BOSHLANG'ICH TOIFA DAVRI — modul docstringidagi
        # birinchi band. Bu qator ixtiyoriy EMAS.
        conn.execute(
            _INSERT_CATEGORY_PERIOD,
            (str(uuid4()), str(market_id), str(stall_id), str(category_id), operating_since),
        )
        category_by_stall[stall_id] = category_id

    vendor_ids = tuple(uuid4() for _ in vendor_names)
    for vendor_id, name, phone in zip(vendor_ids, vendor_names, vendor_phones, strict=True):
        conn.execute(_INSERT_VENDOR, (str(vendor_id), str(market_id), name, phone))

    return MarketDomainRows(
        market_id=market_id,
        operating_since=operating_since,
        open_weekdays=open_weekdays,
        zone_ids=zone_ids,
        category_ids=category_ids,
        stall_ids=stall_ids,
        stall_codes=stall_codes,
        vendor_ids=vendor_ids,
        assignment_ids=(),
        category_by_stall=category_by_stall,
        tariff_by_category=tariff_by_category,
    )


def _assign(
    conn: Connection[TupleRow],
    market_id: UUID,
    stall_id: UUID,
    vendor_id: UUID,
    start: date,
    end: date | None,
) -> UUID:
    assignment_id = uuid4()
    conn.execute(
        _INSERT_ASSIGNMENT,
        (
            str(assignment_id),
            str(market_id),
            str(stall_id),
            str(vendor_id),
            to_pg_period(start, end),
        ),
    )
    return assignment_id


def seed_market_domain(conn: Connection[TupleRow], base: TwoMarketSeed) -> MarketDomainSeed:
    """`two_markets` ustiga domen qatlamini yozadi.

    `conn` `sbozor_owner` bilan ochilgan va AUTOCOMMIT rejimida bo'lishi
    kerak — `two_markets` bilan aynan bir xil talab.
    """
    a = _seed_market(
        conn,
        market_id=base.market_a.id,
        operating_since=A_OPERATING_SINCE,
        open_weekdays=A_OPEN_WEEKDAYS,
        zone_names=A_ZONE_NAMES,
        category_names=A_CATEGORY_NAMES,
        stall_codes=A_STALL_CODES,
        tariff_amounts=A_TARIFF_AMOUNTS,
        vendor_names=A_VENDOR_NAMES,
        vendor_phones=A_VENDOR_PHONES,
    )

    # ---- A bozori: uch xil biriktirish holati (D-10 va D-11 ning ikki shakli)
    handover_stall = a.stall_ids[0]
    gap_stall = a.stall_ids[1]
    unassigned_stall = a.stall_ids[2]

    assignment_ids = (
        # D-10: eski sotuvchi -> yangi sotuvchi. Chegara `[)` bo'lgani uchun
        # ALMASHINUV KUNI (`HANDOVER_DAY`) YANGI sotuvchiga tegishli va
        # o'sha kunning pattasi unga yoziladi.
        _assign(conn, a.market_id, handover_stall, a.vendor_ids[0], HANDOVER_START, HANDOVER_DAY),
        _assign(conn, a.market_id, handover_stall, a.vendor_ids[1], HANDOVER_DAY, None),
        # D-11: ikki davr orasida ATAYIN bo'shliq.
        _assign(conn, a.market_id, gap_stall, a.vendor_ids[2], GAP_START, GAP_CLOSED_AT),
        _assign(conn, a.market_id, gap_stall, a.vendor_ids[2], GAP_REOPENED_AT, None),
    )
    # `unassigned_stall` ga BIRORTA biriktirish yozilmaydi — bu D-11 ning
    # ikkinchi shakli va u ham ma'noli holat, xato emas.

    market_a = replace(
        a,
        assignment_ids=assignment_ids,
        handover_stall_id=handover_stall,
        gap_stall_id=gap_stall,
        unassigned_stall_id=unassigned_stall,
    )

    b = _seed_market(
        conn,
        market_id=base.market_b.id,
        operating_since=B_OPERATING_SINCE,
        open_weekdays=B_OPEN_WEEKDAYS,
        zone_names=B_ZONE_NAMES,
        category_names=B_CATEGORY_NAMES,
        stall_codes=B_STALL_CODES,
        # BITTA tarif, IKKITA toifa -> ikkinchi toifa ATAYIN tarifsiz.
        tariff_amounts=(B_TARIFF_AMOUNT,),
        vendor_names=(B_VENDOR_NAME,),
        vendor_phones=(B_VENDOR_PHONE,),
    )
    b_assignments = (
        _assign(conn, b.market_id, b.stall_ids[0], b.vendor_ids[0], B_ASSIGNMENT_START, None),
    )
    market_b = replace(b, assignment_ids=b_assignments)

    return MarketDomainSeed(market_a=market_a, market_b=market_b)


def cleanup_market_domain(conn: Connection[TupleRow], seed: MarketDomainSeed) -> None:
    """Domen qatlamini FK tartibida o'chiradi.

    ⚠ AVVAL BOZORLAR QORALAMAGA QAYTARILADI VA BUSIZ TOZALASH YIQILADI.

    `two_markets` bozorlarni `INSERT INTO markets (id, name)` bilan
    yaratadi, `markets.is_active` esa `DEFAULT true` — ya'ni seed bozorlari
    FAOL. Seed'dagi tarif va toifa davrlarining `valid_from` i esa
    `operating_since` (O'TGAN sana, A3 talabi). `trg_tariff_past_immutable`
    va `trg_category_period_past_immutable` aynan shu juftlikni qulflaydi:
    faol bozorda `valid_from <= bugun` bo'lgan qatorni O'CHIRISH `23514`
    beradi (D-07). Ya'ni tozalash birinchi `DELETE FROM tariffs` da
    yiqilardi va har bir test qoldiq ma'lumot qoldirardi.

    Yechim mahsulotning O'Z yechimi bilan bir xil: ikkala qo'riqchi ham
    QORALAMA bozorni (`is_active = false`) istisno qiladi va
    `market_delete_draft()` aynan shunga tayanadi (02-04 deviatsiya #3).
    Bayroqni tushirish bu yerda semantik jihatdan HALOL: qator bir necha
    satr keyin `cleanup_two_markets()` tomonidan butunlay o'chiriladi.

    ALTERNATIVALAR VA NEGA ULAR EMAS:
      * `ALTER TABLE ... DISABLE TRIGGER` — qo'riqchini butunlay o'chiradi,
        ya'ni u ROSTDAN buzilgan holatni ham yashirardi;
      * kelajakdagi `valid_from` — A3 ni buzardi va 6-faza uchun butun
        tarixni tarifsiz qoldirardi (seed'ning butun ma'nosi yo'qolardi).
    """
    market_ids = [str(market_id) for market_id in seed.market_ids]

    conn.execute(
        "UPDATE markets SET is_active = false WHERE id = ANY(%s::uuid[])",
        (market_ids,),
    )
    for table in CLEANUP_ORDER:
        # Jadval nomlari shu moduldagi SOBIT `CLEANUP_ORDER` dan keladi —
        # tashqi kirish emas, ya'ni f-string bu yerda xavfsiz.
        conn.execute(
            f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
            (market_ids,),
        )
