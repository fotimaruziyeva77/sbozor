"""Sotuvchi biriktirish — QARZ EGALIGINING semantikasi (MARKET-04, D-09…D-12).

=============================================================================
BU FAYL BITTA SAVOLGA JAVOB BERADI: «FALON KUNI FALON RASTANING PATTASI KIMGA
YOZILADI?» — va javob DB darajasida, `[)` chegara konventsiyasi ustida
qulflanadi.

Almashinuv kunidagi xato eng qimmat xato: u yo pattani IKKI MARTA yozadi
(ikkala sotuvchi ham qarzdor bo'lib chiqadi), yo UMUMAN yozmaydi (kun
tushumdan tushib qoladi). Ikkalasi ham nizoda mahsulotning butun da'vosini
("raqamlar va rasm-dalil") bekor qiladi.

`tests/tenancy/test_market_domain_meta.py` bilan MUNOSABATI: u yerda
`ex_stall_assignments_no_overlap` KONSTRAYTINING mavjudligi va shakli
tekshiriladi (`pg_constraint` dan o'qib), bu yerda esa uning XULQI va u
ilova qatlamiga beradigan SHARTNOMA — qaysi `sqlstate`, qaysi kunda qaysi
sotuvchi, bo'shliqda nima. Biri "mexanizm o'rnatilgan", ikkinchisi
"mexanizm kutilgan javobni beradi" deydi.
=============================================================================

XATO AJRATISH — FAQAT `sqlstate` (RESEARCH Pattern 4, o'lchangan):
RLS yoqilgan jadvalda Postgres `EXCLUDE`/`UNIQUE` buzilishining `DETAIL`
qatorini BUTUNLAY o'chiradi (Pitfall 4), `exc.orig.constraint_name` esa
asyncpg o'ramida `None` bo'lib qaytadi. Ya'ni 02-10 dagi endpoint
`23P01 -> 409 assignment_period_overlaps` xaritasini FAQAT `sqlstate`
bo'yicha qura oladi va bu testlar aynan shuni qulflaydi.

DAVR QURISHNING YAGONA YO'LI — `to_pg_period()` (u o'z navbatida
`sbozor_core.periods.assignment_period()` ni chaqiradi). Bu faylda xom
`daterange(...)` matni ham, `'[)'` literali ham YO'Q: konvensiya bitta
joyda yashaydi (Pitfall 10) va uni o'zgartirish mahsulot kodini ham,
testni ham BIR VAQTDA o'zgartiradi.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

import psycopg
import pytest
from fixtures import MarketScope
from fixtures.market_domain import GAP_DAY, HANDOVER_DAY, MarketDomainSeed, to_pg_period
from psycopg import Connection
from psycopg.rows import TupleRow
from psycopg.types.range import Range as PgRange
from sbozor_core.periods import PERIOD_BOUNDS

INSERT_ASSIGNMENT = (
    "INSERT INTO stall_assignments (market_id, stall_id, vendor_id, period) "
    "VALUES (%s, %s, %s, %s) RETURNING id"
)

VENDOR_ON_DAY = (
    "SELECT vendor_id FROM stall_assignments "
    "WHERE market_id = %s AND stall_id = %s AND period @> %s::date"
)
"""«D sanada kim biriktirilgan» — 6-fazaga beriladigan kontrakt satri.

`period @> :d` ATAYIN (`period_contains()` EMAS): faqat shu shakl
`ex_stall_assignments_no_overlap` ostidagi GiST indeksidan foydalanadi.
Kod-qatlamidagi tekshiruv butun jadvalni tortib olardi.
"""

READ_PERIOD = "SELECT period FROM stall_assignments WHERE id = %s"
UPDATE_PERIOD = "UPDATE stall_assignments SET period = %s WHERE id = %s"

INSERT_VENDOR = (
    "INSERT INTO vendors (market_id, full_name, phone_e164) VALUES (%s, %s, %s) RETURNING id"
)
READ_VENDOR_PHONE = "SELECT phone_e164 FROM vendors WHERE id = %s"
COUNT_VENDORS_BY_PHONE = "SELECT count(*) FROM vendors WHERE market_id = %s AND phone_e164 = %s"

AUDIT_ROWS = (
    "SELECT action, old_value, new_value, changed_keys FROM audit_log "
    "WHERE table_name = %s AND row_id = %s ORDER BY id"
)

# Bo'sh rasta ustida qurilgan probe davrlari. Sanalar seed'nikidan
# FARQ QILADI: aralashib ketsa nosozlik xabari qaysi davr haqida ekanini
# ko'rsatmasdi.
PROBE_START = date(2026, 8, 1)
PROBE_SWITCH = date(2026, 8, 10)
PROBE_OVERLAP_START = date(2026, 8, 5)
PROBE_OVERLAP_END = date(2026, 8, 20)

PROBE_VENDOR_NAME = "Probe sotuvchi"


def _one(conn: Connection[TupleRow], sql: str, params: tuple[Any, ...]) -> Any:
    row = conn.execute(sql, params).fetchone()
    assert row is not None, f"so'rov 0 qator qaytardi: {sql}"
    return row


def _free_stall(seed: MarketDomainSeed) -> UUID:
    """Hech qachon biriktirilmagan rasta — probe davrlari shu yerda quriladi.

    Seed'dagi biriktirilgan rastalar (`handover_stall`, `gap_stall`) ustida
    yangi davr qo'shish o'sha rastalarning boshlang'ich holatini buzardi va
    D-10/D-11 testlari BOSHQA testning yon ta'siriga bog'liq bo'lib qolardi.
    """
    stall_id = seed.market_a.unassigned_stall_id
    assert stall_id is not None, "seed'da biriktirilmagan rasta yo'q"
    return stall_id


# ===========================================================================
# D-09 — BIR VAQTDA 1 RASTA = 1 SOTUVCHI (nazorat holati BIRINCHI)
# ===========================================================================


def test_adjacent_periods_are_accepted(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """NAZORAT HOLATI: qo'shni (kesishmaydigan) davrlar QABUL qilinadi.

    ⚠ BU TEST KEYINGISIDAN OLDIN TURADI VA USIZ KEYINGISI YOLG'ON-YASHIL.
    Konstrayt HAR QANDAY ikkinchi davrni rad etayotgan bo'lsa ham (masalan
    `&&` o'rniga `=` yozilgan bo'lsa) "qoplanish bloklandi" degan xulosa
    chiqardi — va o'shanda sotuvchi almashtirish umuman imkonsiz bo'lardi,
    ya'ni MARKET-04 ning asosiy oqimi ishlamasdi.

    Ayni paytda bu D-10 ning o'zi: `[)` chegarasida `PROBE_SWITCH` kuni
    ikkala davrga tegishli EMAS — u faqat YANGISIGA tegishli, shuning uchun
    davrlar kesishmaydi.
    """
    a = market_domain.market_a
    stall = _free_stall(market_domain)

    with market_scope(a.market_id) as conn:
        conn.execute(
            INSERT_ASSIGNMENT,
            (a.market_id, stall, a.vendor_ids[0], to_pg_period(PROBE_START, PROBE_SWITCH)),
        )
        conn.execute(
            INSERT_ASSIGNMENT,
            (a.market_id, stall, a.vendor_ids[1], to_pg_period(PROBE_SWITCH, None)),
        )
        count = _one(
            conn,
            "SELECT count(*) FROM stall_assignments WHERE market_id = %s AND stall_id = %s",
            (a.market_id, stall),
        )

    assert count[0] == 2, (
        f"qo'shni davrlar qabul qilinmadi ({count[0]} qator) — konstrayt kutilganidan KENG "
        "qamrayapti va sotuvchi almashtirish oqimi butunlay yopiq"
    )


def test_overlapping_period_is_rejected(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Qoplanuvchi davr `23P01` bilan rad etiladi (D-09, T-02-37).

    `sqlstate` ATAYIN tekshiriladi, konstrayt NOMI emas: RLS yoqilgan
    jadvalda `DETAIL` qatori umuman yo'q (Pitfall 4, ega uchun ham
    o'lchangan) va `exc.orig.constraint_name` asyncpg o'ramida `None` bo'lib
    qaytadi. Ya'ni 02-10 dagi endpoint uchun YAGONA ishonchli diskriminator
    — `sqlstate`, va u `409 assignment_period_overlaps` ga aylanadi.

    Konstraytsiz bu qoida ilova qatlamidagi "avval tekshir, keyin yoz"
    naqshiga tushardi va IKKI PARALLEL so'rovda ikkalasi ham o'tib ketardi —
    bir kunda ikkita sotuvchi biriktirilgan bo'lib chiqardi (T-02-43).
    """
    a = market_domain.market_a
    stall = _free_stall(market_domain)

    with market_scope(a.market_id) as conn:
        conn.execute(
            INSERT_ASSIGNMENT,
            (a.market_id, stall, a.vendor_ids[0], to_pg_period(PROBE_START, PROBE_SWITCH)),
        )

        with pytest.raises(psycopg.errors.ExclusionViolation) as excinfo:
            conn.execute(
                INSERT_ASSIGNMENT,
                (
                    a.market_id,
                    stall,
                    a.vendor_ids[1],
                    to_pg_period(PROBE_OVERLAP_START, PROBE_OVERLAP_END),
                ),
            )

    assert excinfo.value.sqlstate == "23P01", (
        f"qoplanish `{excinfo.value.sqlstate}` bilan rad etildi, `23P01` emas — ilova "
        "qatlami uni boshqa konflikt turlaridan ajrata olmaydi"
    )


# ===========================================================================
# D-10 — ALMASHINUV KUNI YANGI SOTUVCHIGA TEGISHLI
# ===========================================================================


@pytest.mark.parametrize(
    ("day_offset", "vendor_index"),
    [(-2, 0), (-1, 0), (0, 1), (1, 1)],
    ids=[
        "ikki kun oldin -> ESKI",
        "bir kun oldin -> ESKI",
        "ALMASHINUV KUNI -> YANGI",
        "bir kun keyin -> YANGI",
    ],
)
def test_handover_day_boundary(
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
    day_offset: int,
    vendor_index: int,
) -> None:
    """D-10 chegara jadvali: almashinuv kuni AYNAN bitta va YANGI sotuvchiga.

    To'rt sana ham kerak va ular chegarani IKKALA tomondan qamraydi:
    yolg'iz "almashinuv kuni yangi sotuvchiniki" da'vosi butun davrni yangi
    sotuvchiga bergan buzuq ma'lumot ustida ham yashil bo'lardi; oldingi
    ikki kun esa eski sotuvchida qolishini talab qiladi.

    Sanalar `HANDOVER_DAY` dan HISOBLANADI, testda QAYTA YOZILMAYDI —
    seed konstantasi o'zgarganda test o'z-o'zidan ergashadi (02-06 naqshi).

    Har bir sana uchun qator soni ham tekshiriladi: `[]` konventsiyasida
    almashinuv kuni IKKALA davrga tushardi va o'sha kunning pattasi ikki
    marta yozilardi.
    """
    a = market_domain.market_a
    day = HANDOVER_DAY + timedelta(days=day_offset)
    expected_vendor = a.vendor_ids[vendor_index]

    with market_scope(a.market_id) as conn:
        rows = conn.execute(VENDOR_ON_DAY, (a.market_id, a.handover_stall_id, day)).fetchall()

    assert len(rows) == 1, (
        f"{day} kunida {len(rows)} sotuvchi biriktirilgan — AYNAN bittasi bo'lishi shart; "
        "0 bo'lsa kun tushumdan tushadi, 2 bo'lsa patta ikki marta yoziladi (D-10)"
    )
    assert UUID(str(rows[0][0])) == expected_vendor, (
        f"{day} kunida kutilmagan sotuvchi biriktirilgan — `[)` chegara konventsiyasi "
        "buzilgan (yuqori chegara davrga KIRMAYDI, ya'ni almashinuv kuni YANGISINIKI)"
    )


# ===========================================================================
# D-11 — SOTUVCHISIZ KUN XATO EMAS, ANOMALIYA MANBAI
# ===========================================================================


def test_vacancy_gap_returns_no_vendor(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Bo'shliq kunida `period @> :d` 0 QATOR beradi va bu KUTILGAN xulq (D-11).

    Bu test ISTISNO KUTMAYDI va shu bilan qolganlaridan farq qiladi:
    davrlar uzluksizligi HECH QAYERDA majburlanmaydi. Bo'shliq — 6-faza
    topadigan "band, lekin sotuvchisiz" anomaliyasining manbai; uni sxema
    darajasida taqiqlash mahsulotning asosiy da'vosini o'chirardi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        rows = conn.execute(VENDOR_ON_DAY, (a.market_id, a.gap_stall_id, GAP_DAY)).fetchall()

    assert rows == [], (
        f"bo'shliq kunida ({GAP_DAY}) {len(rows)} sotuvchi topildi — seed D-11 holatini "
        "ifodalamayapti yoki davrlar jimgina to'ldirib yuborilgan"
    )


def test_unassigned_stall_returns_no_vendor(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Hech qachon biriktirilmagan rasta uchun ham 0 qator — D-11 ning IKKINCHI shakli.

    Bo'shliqdan farqi bor va ikkalasi ham kerak: bo'shliq "sotuvchi bor edi,
    ketdi", bu esa "hech qachon ro'yxatga olinmagan". Ikkinchisi Karmanada
    ancha keng tarqalgan holat (rasta bor, savdo bor, qog'ozda yo'q) va
    aynan u mahsulot fosh qiladigan nosozlik.
    """
    a = market_domain.market_a
    stall = _free_stall(market_domain)

    with market_scope(a.market_id) as conn:
        rows = conn.execute(VENDOR_ON_DAY, (a.market_id, stall, HANDOVER_DAY)).fetchall()

    assert rows == [], f"biriktirilmagan rastada {len(rows)} sotuvchi topildi"


# ===========================================================================
# DAVRNING SHAKLI — YOZILDI VA QAYTA O'QILDI
# ===========================================================================


def test_open_ended_period_round_trips(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Ochiq oxirli davr (`end=None`) qo'shimcha konversiyasiz qaytadi.

    "Sotuvchi hali ishlayapti" — biriktirishlarning KO'PCHILIGI shu shaklda.
    Agar `upper` qaytishda `None` bo'lmasa (masalan `infinity` sanasiga
    aylansa), ilova qatlami "davr tugagan" deb ko'rsatardi va sotuvchi
    ro'yxatidan jimgina yo'qolardi.

    `bounds` ham tekshiriladi: Postgres diskret `daterange` ni HAR DOIM
    `[)` shakliga keltiradi, ya'ni kimdir bir kun `'[]'` bilan yozsa ham
    saqlangan qiymat boshqa MA'NOGA ega bo'lardi — bu assertion
    konvensiyaning DB tomonidagi jufti.
    """
    a = market_domain.market_a
    stall = _free_stall(market_domain)

    with market_scope(a.market_id) as conn:
        created = _one(
            conn,
            INSERT_ASSIGNMENT,
            (a.market_id, stall, a.vendor_ids[0], to_pg_period(PROBE_START, None)),
        )
        stored = _one(conn, READ_PERIOD, (created[0],))

    period: PgRange[date] = stored[0]
    assert period.lower == PROBE_START, f"quyi chegara `{period.lower}` ga o'zgargan"
    assert period.upper is None, (
        f"ochiq oxirli davrning yuqori chegarasi `{period.upper}` bo'lib qaytdi — sotuvchi "
        "ro'yxatda 'ketgan' deb ko'rinadi"
    )
    assert period.bounds == PERIOD_BOUNDS, (
        f"chegara shakli `{period.bounds}`, kutilgan `{PERIOD_BOUNDS}` — almashinuv kuni "
        "boshqa sotuvchiga o'tib ketadi (Pitfall 10)"
    )


def test_lower_bound_is_required(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Quyi chegarasiz davr `CheckViolation` beradi.

    Quyi chegarasi `NULL` bo'lgan davr "sotuvchi ABADIY o'tmishdan beri
    biriktirilgan" degani: u bozor tarixidagi HAR BIR kunni qamrab olardi va
    o'sha rastaning butun o'tmishdagi qarzi bitta sotuvchiga yozilardi.

    ⚠ `PgRange(None, ...)` ni qurish uchun `assignment_period()` ISHLATIB
    BO'LMAYDI — u `start: date` talab qiladi va aynan shu holatni
    STRUKTURAVIY imkonsiz qiladi (bu yordamchining maqsadi). Shuning uchun
    bu YAGONA joyda `PgRange` to'g'ridan-to'g'ri quriladi, lekin chegara
    HARFI baribir `PERIOD_BOUNDS` dan olinadi — ya'ni konvensiyaning ikkinchi
    nusxasi bu yerda ham yaratilmaydi.
    """
    a = market_domain.market_a
    stall = _free_stall(market_domain)
    unbounded: PgRange[date] = PgRange(None, PROBE_SWITCH, PERIOD_BOUNDS)

    with (
        market_scope(a.market_id) as conn,
        pytest.raises(psycopg.errors.CheckViolation) as excinfo,
    ):
        conn.execute(INSERT_ASSIGNMENT, (a.market_id, stall, a.vendor_ids[0], unbounded))

    assert "lower_bound_required" in str(excinfo.value), (
        f"kutilmagan CHECK buzilishi: {excinfo.value} — quyi chegara qo'riqchisi "
        "boshqa konstrayt tomonidan almashtirilgan bo'lishi mumkin"
    )


# ===========================================================================
# CROSS-TENANT VA AUDIT
# ===========================================================================


def test_cross_tenant_vendor_assignment_is_rejected(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """A bozorining rastasiga B bozorining sotuvchisi biriktirilmaydi (T-02-52).

    Bu RLS EMAS, SXEMA darajasidagi kafolat: composite FK `(market_id,
    vendor_id) -> vendors (market_id, id)` juftligini talab qiladi va
    `(A, B_ning_sotuvchisi)` juftligi UMUMAN mavjud emas.

    Farq amaliy: RLS "kim nimani ko'radi" ni hal qiladi, lekin qatorni
    YOZAYOTGAN kod allaqachon A kontekstida — u B ning `vendor_id` sini
    boshqa yo'ldan (import fayli, eski API javobi, qo'lda kiritilgan UUID)
    olib kelishi mumkin. Referensial butunlik tekshiruvi RLS'ni CHETLAB
    o'tadi (Postgres qoidasi), ya'ni bu darvoza kontekstdan qat'i nazar
    ishlaydi.
    """
    a = market_domain.market_a
    b = market_domain.market_b
    stall = _free_stall(market_domain)

    with (
        market_scope(a.market_id) as conn,
        pytest.raises(psycopg.errors.ForeignKeyViolation) as excinfo,
    ):
        conn.execute(
            INSERT_ASSIGNMENT,
            (a.market_id, stall, b.vendor_ids[0], to_pg_period(PROBE_START, None)),
        )

    assert "fk_stall_assignments_market_id_vendor_id_vendors" in str(excinfo.value), (
        f"kutilmagan FK buzilishi: {excinfo.value} — cross-tenant to'siq SOTUVCHI FK'si "
        "bo'lishi shart (rasta FK'si boshqa xatoni bildiradi)"
    )


def test_period_change_is_audited(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Biriktirish davrining surilishi `audit_log` da old->new bilan ko'rinadi (T-02-53).

    Davrni orqaga surish — qarzni boshqa sotuvchiga o'tkazishning eng
    to'g'ridan-to'g'ri yo'li: chegarani bir kunga siljitish o'sha kunning
    pattasini butunlay boshqa odamga yozadi. Undan qoladigan YAGONA iz —
    shu trigger, chunki `stall_assignments` da `updated_at` ustuni ham yo'q
    (qator o'zgarganini boshqa hech narsa ko'rsatmaydi).

    Yangi davr `to_pg_period()` bilan quriladi va boshlanish sanasi MAVJUD
    qatordan o'qiladi — test seed sanasini QAYTA YOZMAYDI.
    """
    a = market_domain.market_a
    assignment_id = a.assignment_ids[-1]

    with market_scope(a.market_id) as conn:
        current: PgRange[date] = _one(conn, READ_PERIOD, (assignment_id,))[0]
        assert current.lower is not None
        shifted = to_pg_period(current.lower + timedelta(days=1), None)

        conn.execute(UPDATE_PERIOD, (shifted, assignment_id))
        rows = conn.execute(AUDIT_ROWS, ("stall_assignments", assignment_id)).fetchall()

    updates = [row for row in rows if row[0] == "update"]
    assert len(updates) == 1, (
        f"davr o'zgarishi uchun {len(updates)} audit qatori topildi — kutilgan 1. "
        "Yozuvsiz qolgan o'zgarish nizoda 'bu men emas edim' javobini imkonsiz qiladi"
    )

    _action, old_value, new_value, changed_keys = updates[0]
    assert changed_keys is not None and "period" in changed_keys, (
        f"`changed_keys` da `period` yo'q: {changed_keys} — jurnal 'nima o'zgardi' "
        "savoliga javob bermayapti"
    )
    assert old_value is not None and new_value is not None
    assert old_value["period"] != new_value["period"], (
        "audit qatorida eski va yangi davr bir xil — farq yozilmagan"
    )


# ===========================================================================
# D-12 — TELEFON UNIKALLIGI BOZOR ICHIDA (juftlik: rad etish + nazorat)
# ===========================================================================


def test_phone_is_unique_per_market(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """AYNI bozorda takroriy telefon `23505` beradi (D-12).

    Telefon — sotuvchining Telegram orqali kelgan shaxsiy identifikatori
    (02-10 dan boshlab). Bir bozorda ikkita "Aliyev Vali" bo'lsa qarzdorlik
    reestri kimga tegishli ekanini ko'rsata olmaydi va bot xabari noto'g'ri
    odamga ketadi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        phone = _one(conn, READ_VENDOR_PHONE, (a.vendor_ids[1],))[0]

        with pytest.raises(psycopg.errors.UniqueViolation) as excinfo:
            conn.execute(INSERT_VENDOR, (a.market_id, PROBE_VENDOR_NAME, phone))

    assert excinfo.value.sqlstate == "23505", (
        f"takroriy telefon `{excinfo.value.sqlstate}` bilan rad etildi — ilova qatlami "
        "uni `409` ga aylantira olmaydi"
    )


def test_same_phone_in_another_market_is_accepted(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """NAZORAT HOLATI: AYNI telefon BOSHQA bozorda qabul qilinadi (D-12).

    ⚠ D-12 NING BUTUN MA'NOSI SHU TESTDA. Yuqoridagi test yolg'iz qolganda
    `UNIQUE(phone_e164)` ni GLOBAL qilib qo'ygan holat ham yashil bo'lardi —
    va o'shanda ikki bozorda savdo qiladigan odam ikkinchi bozorga UMUMAN
    ro'yxatga olinmasdi (Karmanada odatiy holat), sabab esa "telefon band"
    degan tushunarsiz xato bo'lardi.

    Telefon A bozoridan O'QILADI (konstantadan emas): shu bilan u
    haqiqatan MAVJUD ekani isbotlanadi va test "hech qayerda bo'lmagan
    telefon qabul qilindi" degan bo'sh da'vodan farq qiladi.
    """
    a = market_domain.market_a
    b = market_domain.market_b

    with market_scope(a.market_id) as conn:
        phone = _one(conn, READ_VENDOR_PHONE, (a.vendor_ids[1],))[0]

    with market_scope(b.market_id) as conn:
        before = _one(conn, COUNT_VENDORS_BY_PHONE, (b.market_id, phone))[0]
        assert before == 0, (
            f"telefon B bozorida allaqachon {before} marta uchraydi — test o'z shartini "
            "bajarmayapti (seed o'zgargan)"
        )

        conn.execute(INSERT_VENDOR, (b.market_id, PROBE_VENDOR_NAME, phone))
        after = _one(conn, COUNT_VENDORS_BY_PHONE, (b.market_id, phone))[0]

    assert after == 1, (
        f"B bozorida ayni telefon bilan {after} qator bor — A bozoridagi telefon boshqa "
        "bozorga yozilishini bloklab qo'ygan (unikalik GLOBAL bo'lib qolgan, D-12 buzilgan)"
    )
