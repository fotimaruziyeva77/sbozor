"""Tarif tarixi — SC#3 ning DB darajasidagi TO'LIQ isboti (MARKET-03).

=============================================================================
NEGA BU TESTLAR API'DAN OLDIN YOZILADI VA NEGA ULAR API'NI SINAMAYDI:

SC#3 — moliyaviy yaxlitlik kafolati: "tarif o'zgartirilganda o'tmishdagi
hisob eski narxda qoladi". Uni "API 403 qaytaradi" bilan isbotlab BO'LMAYDI,
chunki tahdid modeli (T-02-46) aynan XOM SQL yo'lini nazarda tutadi: qarzni
yashirmoqchi bo'lgan insider `psql` ochadi, endpoint emas. Shuning uchun
bu yerdagi da'volar sxemaning va DB triggerlarining O'ZIGA qarshi olinadi,
ilova qatlamiga emas — 1-fazadagi D-10 falsafasining aynan davomi.

Testlar API yozilishidan OLDIN turgani uchun 02-09 dagi tarif endpointi
allaqachon QULFLANGAN shartnomaga qarshi quriladi: `23514` -> `403`,
`23505` -> `409`, "tarif topilmadi" -> 0 qator (0 so'm EMAS).
=============================================================================

MODEL: VORIS (successor) — `valid_to` SAQLANMAYDI (RESEARCH Pattern 2, Pitfall 9).
Yangi narx = YANGI qator (D-06); eski qatorga HECH QACHON tegilmaydi (D-07).
"D sanadagi amaldagi tarif" — `valid_from <= :d ORDER BY valid_from DESC
LIMIT 1`. Birinchi qatordan OLDINGI sana uchun bu so'rov 0 qator beradi va
bu ATAYIN (D-08 fail-closed) — tarifsiz kun hisob emas, ANOMALIYA.

NAZORAT HOLATLARI JUFTLIGI: har bir "rad etiladi" testining yonida
"qabul qilinadi" jufti turadi va u JUFTIDAN OLDIN e'lon qilinadi. Usiz
"hamma narsa bloklangan" holati ham yashil ko'rinardi.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

import psycopg
import pytest
from fixtures import MarketScope
from fixtures.market_domain import A_TARIFF_AMOUNTS, MarketDomainSeed
from psycopg import Connection
from psycopg.rows import TupleRow

# ---------------------------------------------------------------------------
# So'rov shakllari — 6-fazaga beriladigan KONTRAKTNING o'zi
# ---------------------------------------------------------------------------

CURRENT_TARIFF = (
    "SELECT amount_soum FROM tariffs "
    "WHERE market_id = %s AND category_id = %s AND valid_from <= %s::date "
    "ORDER BY valid_from DESC LIMIT 1"
)
"""«D sanadagi amaldagi tarif» — 02-04 SUMMARY dagi kontrakt satri.

`%s::date` shakli ATAYIN (02-06 da o'lchangan): `DATE %s` literal prefiksi
bind parametr bilan sintaksis xatosi beradi.
"""

INSERT_TARIFF = (
    "INSERT INTO tariffs (market_id, category_id, amount_soum, valid_from) "
    "VALUES (%s, %s, %s, %s) RETURNING id"
)

READ_TARIFF_ROW = "SELECT amount_soum, valid_from, created_at FROM tariffs WHERE id = %s"

TARIFF_HISTORY = (
    "SELECT valid_from, "
    "       LEAD(valid_from) OVER (PARTITION BY market_id, category_id ORDER BY valid_from), "
    "       amount_soum "
    "FROM tariffs WHERE market_id = %s AND category_id = %s ORDER BY valid_from"
)
"""Pitfall 9: «bu tarif qachongacha amal qildi» — HOSILA, saqlanadigan ustun EMAS."""

TARIFF_COLUMNS = (
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_schema = 'public' AND table_name = 'tariffs'"
)

# ---------------------------------------------------------------------------
# Seed konstantalari — QIYMATLAR SEED MODULIDAN KELADI (02-06 naqshi)
# ---------------------------------------------------------------------------

SEEDED_CATEGORY_INDEX = 2
"""A bozorining UCHINCHI toifasi ("Kiyim") — seed'da 8 000 so'm.

Indeks yozilgan, summa esa `A_TARIFF_AMOUNTS` dan olinadi: seed narxni
o'zgartirsa test o'z-o'zidan moslashadi, lekin qaysi toifa sinalayotgani
ko'rinib turadi.
"""

SEEDED_AMOUNT = A_TARIFF_AMOUNTS[SEEDED_CATEGORY_INDEX]

NEW_AMOUNT = 15_000
"""Yangi narx — seed'dagi UCHALA summadan ham FARQLI (5 000 / 12 000 / 8 000).

Bu ataylab: agar so'rov `category_id` filtrini yo'qotib qo'ysa va boshqa
toifaning tarifini topsa, seed'dagi summa bilan mos kelib test YASHIL
qolardi. Seed'da umuman uchramaydigan qiymat bu yo'lni yopadi.
"""

DAYS_AHEAD = 30
"""Yangi tarif kuchga kiradigan sana bugundan necha kun keyin.

⚠ SOBIT SANA ATAYIN YOZILMAGAN — sabab `conftest.py::market_today`
docstringida (qotirilgan "kelajak" bir oydan keyin o'tmishga aylanadi va
nazorat holatlari jimgina ma'nosini yo'qotadi).
"""


def _price_at(
    conn: Connection[TupleRow], market_id: UUID, category_id: UUID, day: date
) -> int | None:
    """`day` sanasidagi amaldagi narx; tarif topilmasa — `None`.

    `0` EMAS, `None`: bu farq D-08 ning butun ma'nosi. "0 so'm" javobi
    tarifsiz kunni BEPUL kun deb ko'rsatardi va hisob-kitob jimgina nol
    yozardi; `None` esa chaqiruvchini anomaliya yo'liga majburlaydi.
    """
    row = conn.execute(CURRENT_TARIFF, (market_id, category_id, day)).fetchone()
    return None if row is None else int(row[0])


def _category(seed: MarketDomainSeed) -> UUID:
    return seed.market_a.category_ids[SEEDED_CATEGORY_INDEX]


# ===========================================================================
# SC#3 — O'TMISH ESKI NARXDA QOLADI, KUCHGA KIRGAN KUN YANGISINI BERADI
# ===========================================================================


def test_past_date_keeps_old_price(
    market_scope: MarketScope, market_domain: MarketDomainSeed, market_today: date
) -> None:
    """Yangi tarif qo'shilgandan KEYIN ham o'tmishdagi sana eski narxni beradi (SC#3).

    Uch qadam ham kerak:
      1. narx yangi qatordan OLDIN o'lchanadi (boshlang'ich holat aniq);
      2. yangi qator qo'shiladi (D-06 — INSERT, UPDATE emas);
      3. AYNI sana QAYTA o'qiladi va javob O'ZGARMAGAN bo'lishi shart.

    Ikkinchi o'lchovsiz test hech nimani isbotlamasdi: birinchi javobning
    to'g'ri bo'lishi yangi qatorning eski javobga TA'SIR QILMASLIGINI
    ko'rsatmaydi.
    """
    a = market_domain.market_a
    category_id = _category(market_domain)
    effective = market_today + timedelta(days=DAYS_AHEAD)
    day_before = effective - timedelta(days=1)

    with market_scope(a.market_id) as conn:
        before = _price_at(conn, a.market_id, category_id, day_before)
        assert before == SEEDED_AMOUNT, (
            f"boshlang'ich narx {before}, kutilgan {SEEDED_AMOUNT} — seed o'zgargan va "
            "test o'z shartini bajarmayapti"
        )

        conn.execute(INSERT_TARIFF, (a.market_id, category_id, NEW_AMOUNT, effective))

        after = _price_at(conn, a.market_id, category_id, day_before)

    assert after == SEEDED_AMOUNT, (
        f"{day_before} sanasidagi narx {after} ga o'zgardi — yangi tarif O'TMISHGA "
        "ta'sir qildi va o'sha kunlarning hisobi retroaktiv qayta yozildi (SC#3 buzilgan)"
    )


def test_effective_day_uses_new_price(
    market_scope: MarketScope, market_domain: MarketDomainSeed, market_today: date
) -> None:
    """Kuchga kirish KUNINING O'ZI yangi narxni beradi — chegara INKLYUZIV.

    `valid_from <= :d` shakli aynan shu chegarani belgilaydi. `<` bo'lganda
    yangi narx bir kun kechikardi va o'sha kunning butun tushumi eski
    tarifda hisoblanardi — yiliga bir necha marta takrorlanadigan, jimgina
    yo'qoladigan farq.
    """
    a = market_domain.market_a
    category_id = _category(market_domain)
    effective = market_today + timedelta(days=DAYS_AHEAD)

    with market_scope(a.market_id) as conn:
        conn.execute(INSERT_TARIFF, (a.market_id, category_id, NEW_AMOUNT, effective))
        on_effective_day = _price_at(conn, a.market_id, category_id, effective)

    assert on_effective_day == NEW_AMOUNT, (
        f"kuchga kirish kunida ({effective}) narx {on_effective_day} — chegara "
        "EKSKLYUZIV bo'lib qolgan, ya'ni yangi tarif bir kun kechikadi"
    )


def test_before_first_tariff_is_fail_closed(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Birinchi tarifdan OLDINGI sana 0 QATOR beradi — `0` so'm EMAS (D-08).

    ⚠ BU YERDA "0 so'm" QAYTARISH ENG XAVFLI XATO BO'LARDI. U tarifsiz
    kunni BEPUL kun sifatida ko'rsatardi: 6-faza o'sha kunga `amount = 0`
    li hisob yozardi, qarzdorlik reestrida hech narsa ko'rinmasdi va
    "band, lekin to'lovsiz" rastalar o'sha kunlar uchun butunlay yo'qolardi.

    Fail-closed shakli buni STRUKTURAVIY yopadi: qator YO'Q, ya'ni
    chaqiruvchi `None` ni tekshirishga MAJBUR va yagona ma'noli javob —
    anomaliya (RESEARCH Pattern 2, empirik tasdiqlangan).
    """
    a = market_domain.market_a
    category_id = _category(market_domain)
    before_first = a.operating_since - timedelta(days=1)

    with market_scope(a.market_id) as conn:
        price = _price_at(conn, a.market_id, category_id, before_first)

    assert price is None, (
        f"`{before_first}` uchun narx `{price}` qaytdi — tarifsiz davr uchun so'rov 0 qator "
        "berishi SHART (D-08). Har qanday son, ayniqsa `0`, o'sha kunni 'bepul' deb "
        "ko'rsatadi va anomaliya hech qachon chiqmaydi"
    )


# ===========================================================================
# D-07 — O'TGAN QATOR XOM SQL BILAN HAM O'ZGARMAYDI (T-02-46)
# ===========================================================================


def test_past_tariff_is_immutable_even_via_raw_sql(
    sync_owner_conn: Connection[TupleRow], market_domain: MarketDomainSeed
) -> None:
    """O'tgan sanali tarif EGA roli bilan ham `23514` beradi (D-07, T-02-46).

    ⚠ HUJUM ATAYIN `sbozor_owner` BILAN QILINADI — `sbozor_app` bilan emas.
    Bu testning butun ma'nosi: agar qo'riqchi faqat ilova roli uchun
    ishlaganida, u RLS'ning takrori bo'lib qolardi va migratsiya, `psql`
    hamda import skripti yo'llari OCHIQ qolardi. Ega — bazadagi eng yuqori
    huquqli rol (o'sha rol bilan sxema qurilgan), ya'ni undan o'tgan
    qo'riqchi ilova qatlamidan MUSTAQIL ekani isbotlanadi.

    `DELETE` ham tekshiriladi va bu takror EMAS: qatorni O'CHIRISH uni
    o'zgartirish bilan AYNAN bir xil natija beradi — o'sha kunlar tarifsiz
    qolib, hisob-kitob ularni "bepul" yoki "anomaliya" deb ko'rsatadi.

    Nazorat holati — `test_future_tariff_is_editable` (pastda).
    """
    a = market_domain.market_a
    tariff_id = a.tariff_by_category[_category(market_domain)]

    with pytest.raises(psycopg.errors.CheckViolation) as update_error:
        sync_owner_conn.execute("UPDATE tariffs SET amount_soum = %s WHERE id = %s", (1, tariff_id))
    assert update_error.value.sqlstate == "23514", (
        f"o'tgan tarifni UPDATE qilish `{update_error.value.sqlstate}` berdi, `23514` emas — "
        "ilova qatlami uni `403` dan ajrata olmaydi"
    )

    with pytest.raises(psycopg.errors.CheckViolation) as delete_error:
        sync_owner_conn.execute("DELETE FROM tariffs WHERE id = %s", (tariff_id,))
    assert delete_error.value.sqlstate == "23514", (
        f"o'tgan tarifni DELETE qilish `{delete_error.value.sqlstate}` berdi — o'chirish "
        "yo'li ochiq qolsa D-07 kafolati bir buyruq bilan chetlab o'tiladi"
    )

    row = sync_owner_conn.execute(READ_TARIFF_ROW, (tariff_id,)).fetchone()
    assert row is not None, "qator o'chib ketdi — istisno chiqdi, lekin amal bajarildi"
    assert row[0] == SEEDED_AMOUNT, f"summa {row[0]} ga o'zgargan — UPDATE qisman o'tdi"


def test_future_tariff_is_editable(
    market_scope: MarketScope,
    sync_owner_conn: Connection[TupleRow],
    market_domain: MarketDomainSeed,
    market_today: date,
) -> None:
    """NAZORAT HOLATI: KELAJAKDAGI qator tahrirlanadi VA o'chiriladi (D-07).

    Bu test yuqoridagisidan keyin turadi, lekin usiz o'sha test hech nimani
    isbotlamasdi: `tariffs` ustidagi HAR QANDAY `UPDATE`/`DELETE` ni
    bloklaydigan buzuq trigger ham (masalan `OLD.valid_from <= ...` sharti
    tushib qolgan tana) yuqoridagi testdan bemalol o'tardi va natija
    "kafolat ishlayapti" bo'lib ko'rinardi — aslida esa xato bilan
    kiritilgan kelajakdagi narxni TUZATIB BO'LMAY qolardi.
    """
    a = market_domain.market_a
    category_id = _category(market_domain)
    effective = market_today + timedelta(days=DAYS_AHEAD)

    with market_scope(a.market_id) as conn:
        created = conn.execute(
            INSERT_TARIFF, (a.market_id, category_id, NEW_AMOUNT, effective)
        ).fetchone()
    assert created is not None
    tariff_id: UUID = created[0]

    sync_owner_conn.execute(
        "UPDATE tariffs SET amount_soum = %s WHERE id = %s", (99_000, tariff_id)
    )
    updated = sync_owner_conn.execute(READ_TARIFF_ROW, (tariff_id,)).fetchone()
    assert updated is not None and updated[0] == 99_000, (
        "kelajakdagi tarifni tahrirlash o'tmadi — xato kiritilgan narxni tuzatish yo'li yopiq"
    )

    sync_owner_conn.execute("DELETE FROM tariffs WHERE id = %s", (tariff_id,))
    assert sync_owner_conn.execute(READ_TARIFF_ROW, (tariff_id,)).fetchone() is None, (
        "kelajakdagi tarifni o'chirish o'tmadi — noto'g'ri rejalashtirilgan narxni bekor "
        "qilishning yagona yo'li yopiq"
    )


def test_existing_row_is_never_touched(
    market_scope: MarketScope, market_domain: MarketDomainSeed, market_today: date
) -> None:
    """D-06: yangi narx qo'shilganda ESKI qator BAYT-BAYTGA o'zgarmaydi.

    `daterange` + `EXCLUDE` modeli tanlanganda bu IMKONSIZ bo'lardi: yangi
    davr kiritish uchun eskisining yuqori chegarasini yopish, ya'ni uni
    `UPDATE` qilish kerak edi — va o'sha `UPDATE` D-07 qulfiga urilardi
    (RESEARCH Pattern 2 dagi solishtiruv jadvalining birinchi ikki satri).

    `created_at` ham tekshiriladi: u o'zgarsa audit jurnalidagi vaqt
    chizig'i ham siljigan bo'lardi.
    """
    a = market_domain.market_a
    category_id = _category(market_domain)
    tariff_id = a.tariff_by_category[category_id]
    effective = market_today + timedelta(days=DAYS_AHEAD)

    with market_scope(a.market_id) as conn:
        before = conn.execute(READ_TARIFF_ROW, (tariff_id,)).fetchone()
        conn.execute(INSERT_TARIFF, (a.market_id, category_id, NEW_AMOUNT, effective))
        after = conn.execute(READ_TARIFF_ROW, (tariff_id,)).fetchone()

    assert before is not None and after is not None
    assert before == after, (
        f"mavjud tarif qatori o'zgardi: {before} -> {after}. D-06 ning butun ma'nosi — "
        "yangi narx YANGI qator; eskisiga tegilsa o'tmishdagi hisob qayta yoziladi"
    )


# ===========================================================================
# YOZISH YUZASI — NIMA RUXSAT, NIMA RAD ETILADI
# ===========================================================================


def test_two_future_tariffs_on_the_same_day_are_allowed(
    market_scope: MarketScope, market_domain: MarketDomainSeed, market_today: date
) -> None:
    """Bir kunda IKKITA kelajak tarifi kiritish MUMKIN (`financial_guards()` chaqirilmagan).

    Bu — 02-05 dagi "`financial_guards(\"tariffs\")` chaqirilmaydi"
    qarorining tirik darvozasi. Helper `UNIQUE(market_id, category_id,
    business_date)` konstraytini qo'shadi, `business_date` esa `created_at`
    dan hosil bo'ladi (`valid_from` dan EMAS) — ya'ni chaqirilganda
    "sentabr narxini ham, oktabr narxini ham BUGUN kiritish" IMKONSIZ
    bo'lardi va tarif rejalashtirish oqimi (02-09) yiqilardi.

    Ikkala qator ham AYNI kunda yaratiladi, lekin `valid_from` lari TURLI —
    aynan shu juftlik yuqoridagi konstraytga urilardi.
    """
    a = market_domain.market_a
    category_id = _category(market_domain)
    first = market_today + timedelta(days=DAYS_AHEAD)
    second = market_today + timedelta(days=DAYS_AHEAD * 2)

    with market_scope(a.market_id) as conn:
        conn.execute(INSERT_TARIFF, (a.market_id, category_id, NEW_AMOUNT, first))
        conn.execute(INSERT_TARIFF, (a.market_id, category_id, NEW_AMOUNT + 1_000, second))

        same_day = conn.execute(
            "SELECT count(DISTINCT business_date), count(*) FROM tariffs "
            "WHERE market_id = %s AND category_id = %s AND valid_from > %s::date",
            (a.market_id, category_id, market_today),
        ).fetchone()

    assert same_day is not None
    assert same_day == (1, 2), (
        f"kutilgan (1 biznes-kun, 2 qator), topilgani {same_day} — ikkala kelajak tarifi "
        "AYNI kunda kiritilgani testning sharti"
    )


def test_duplicate_valid_from_is_rejected(
    market_scope: MarketScope, market_domain: MarketDomainSeed, market_today: date
) -> None:
    """AYNI `(category_id, valid_from)` uchun ikkinchi qator `23505` beradi.

    Yuqoridagi test bilan JUFTLIK: u nima RUXSAT etilishini, bu esa nima
    RAD etilishini belgilaydi. Ikkalasisiz "hamma narsa mumkin" ham,
    "hech narsa mumkin emas" ham shu testlardan o'tib ketardi.

    Bir sanaga ikki narx bo'lganda "D sanadagi tarif" so'rovi `ORDER BY
    valid_from DESC LIMIT 1` bilan IKKALASIDAN BIRINI tanlab olardi — ya'ni
    javob ma'lumot tartibiga bog'liq bo'lib qolardi.
    """
    a = market_domain.market_a
    category_id = _category(market_domain)
    effective = market_today + timedelta(days=DAYS_AHEAD)

    with market_scope(a.market_id) as conn:
        conn.execute(INSERT_TARIFF, (a.market_id, category_id, NEW_AMOUNT, effective))

        with pytest.raises(psycopg.errors.UniqueViolation) as excinfo:
            conn.execute(INSERT_TARIFF, (a.market_id, category_id, NEW_AMOUNT + 500, effective))

    assert excinfo.value.sqlstate == "23505", (
        f"takroriy `valid_from` `{excinfo.value.sqlstate}` bilan rad etildi — ilova qatlami "
        "uni `409` ga aylantira olmaydi"
    )


def test_tariff_history_shows_computed_valid_to(
    market_scope: MarketScope, market_domain: MarketDomainSeed, market_today: date
) -> None:
    """«Tarif qachongacha amal qildi» — HOSILA, saqlanadigan ustun EMAS (Pitfall 9).

    Ikki qismli darvoza:
      1. STRUKTURAVIY — `tariffs` da `valid_to` ustuni YO'Q. Kimdir "UI
         uchun qulay bo'lsin" deb qo'shsa, u keyingi qatorning `valid_from`
         i bilan ajralib ketadi va "tarif oxiri" bilan "keyingi tarif
         boshi" mos kelmaydigan qatorlar paydo bo'ladi.
      2. XULQ — `LEAD(...)` oynasi kutilgan javobni beradi va OXIRGI qator
         uchun `NULL` qaytaradi ("hozir amaldagi narx").

    Birinchisisiz ikkinchisi ustun qo'shilganda ham yashil qolardi.
    """
    a = market_domain.market_a
    category_id = _category(market_domain)
    effective = market_today + timedelta(days=DAYS_AHEAD)

    with market_scope(a.market_id) as conn:
        columns = {row[0] for row in conn.execute(TARIFF_COLUMNS).fetchall()}
        assert "valid_to" not in columns, (
            "`tariffs` ga `valid_to` ustuni qo'shilgan — voris modelida yuqori chegara "
            "SAQLANMAYDI, u keyingi qatordan hisoblanadi (Pitfall 9)"
        )

        conn.execute(INSERT_TARIFF, (a.market_id, category_id, NEW_AMOUNT, effective))
        history = conn.execute(TARIFF_HISTORY, (a.market_id, category_id)).fetchall()

    assert len(history) == 2, f"tarif tarixida {len(history)} qator — kutilgan 2"

    first_from, first_to, first_amount = history[0]
    second_from, second_to, second_amount = history[1]

    assert (first_from, first_amount) == (a.operating_since, SEEDED_AMOUNT)
    assert (second_from, second_amount) == (effective, NEW_AMOUNT)
    assert first_to == second_from, (
        f"birinchi tarifning hisoblangan oxiri `{first_to}`, keyingisining boshi "
        f"`{second_from}` — ikki qiymat AJRALGAN, ya'ni tarixda bo'shliq yoki qoplanish bor"
    )
    assert second_to is None, (
        f"oxirgi tarifning oxiri `{second_to}` — u OCHIQ bo'lishi shart ('hozir amaldagi "
        "narx'), aks holda UI bugungi tarifni tugagan deb ko'rsatadi"
    )
