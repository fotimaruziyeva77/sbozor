"""Toifa tarixi — D-04 ning isboti va u `test_tariff_history.py` ning JUFTI.

=============================================================================
NEGA ALOHIDA FAYL, LEKIN AYNAN BIR XIL TESTLAR:

Toifa tarif orqali summani TO'G'RIDAN-TO'G'RI belgilaydi. Faqat tarifni
qulflab toifa davrini ochiq qoldirish qo'riqchini BUTUNLAY bekor qilardi:
o'tmishdagi rastani "arzon" toifaga surib qo'yish narxni retroaktiv
o'zgartirish bilan AYNAN bir xil natija beradi (T-02-47). Shuning uchun
D-04 mexanizmi D-06/D-07 bilan bir xil — voris modeli + o'tmish qulfi — va
uning testlari ham juft bo'lib yoziladi.

`stalls.category_id` ustuni ATAYIN YO'Q va bu STRUKTURAVIY qaror: ustun
bo'lganda toifani o'zgartirish o'tmishdagi hisobni ham qayta yozardi,
chunki hisob-kitob "rasta qaysi toifada" savoliga BUGUNGI javobni olardi.
=============================================================================

`test_lateral_lookup_returns_category_and_tariff_for_a_date` — 6-fazaning
asosiy so'rovi (RESEARCH Pattern 3). U ikkala tarixni BIR SO'ROVDA
bog'laydi va `amount_soum IS NULL` holati aynan D-08 anomaliyasining
manbai bo'lib qoladi.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

import psycopg
import pytest
from fixtures import MarketScope
from fixtures.market_domain import B_TARIFF_AMOUNT, MarketDomainSeed
from psycopg import Connection
from psycopg.rows import TupleRow

CURRENT_CATEGORY = (
    "SELECT category_id FROM stall_category_periods "
    "WHERE market_id = %s AND stall_id = %s AND valid_from <= %s::date "
    "ORDER BY valid_from DESC LIMIT 1"
)
"""«D sanada rasta qaysi toifada» — `CURRENT_TARIFF` bilan AYNAN bir shakl."""

INSERT_CATEGORY_PERIOD = (
    "INSERT INTO stall_category_periods (market_id, stall_id, category_id, valid_from) "
    "VALUES (%s, %s, %s, %s) RETURNING id"
)

SEEDED_PERIOD_ID = (
    "SELECT id FROM stall_category_periods "
    "WHERE market_id = %s AND stall_id = %s AND valid_from = %s"
)

READ_PERIOD_ROW = "SELECT category_id, valid_from FROM stall_category_periods WHERE id = %s"

STALL_COLUMNS = (
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_schema = 'public' AND table_name = 'stalls'"
)

LATERAL_LOOKUP = """
SELECT s.id, cat.category_id, tar.amount_soum
FROM stalls AS s
LEFT JOIN LATERAL (
    SELECT p.category_id
    FROM stall_category_periods AS p
    WHERE p.market_id = s.market_id AND p.stall_id = s.id AND p.valid_from <= %s::date
    ORDER BY p.valid_from DESC
    LIMIT 1
) AS cat ON true
LEFT JOIN LATERAL (
    SELECT t.amount_soum
    FROM tariffs AS t
    WHERE t.market_id = s.market_id AND t.category_id = cat.category_id
      AND t.valid_from <= %s::date
    ORDER BY t.valid_from DESC
    LIMIT 1
) AS tar ON true
WHERE s.market_id = %s AND s.status = 'active'
"""
"""RESEARCH Pattern 3 dagi so'rov — 6-faza kunlik job'ining YADROSI.

Ikkala `LATERAL` ham AYNAN bir xil "oxirgi qator" shaklida: toifa
`stall_category_periods` dan, narx esa TOPILGAN toifa orqali `tariffs`
dan. `LEFT JOIN` ATAYIN — `INNER` bo'lganda toifasiz yoki tarifsiz rasta
natijadan BUTUNLAY tushib qolardi va anomaliya hech qachon ko'rinmasdi.
"""

DAYS_AHEAD = 30
"""Kelajakdagi kuchga kirish sanasi — `market_today` dan hisoblanadi.

Sobit sana yozilmasligining sababi `conftest.py::market_today` da.
"""


def _category_at(
    conn: Connection[TupleRow], market_id: UUID, stall_id: UUID, day: date
) -> UUID | None:
    row = conn.execute(CURRENT_CATEGORY, (market_id, stall_id, day)).fetchone()
    return None if row is None else UUID(str(row[0]))


def _target_stall(seed: MarketDomainSeed) -> UUID:
    """Toifa testlari ishlaydigan rasta — ATAYIN biriktirilmagan rasta.

    `handover_stall` va `gap_stall` biriktirish testlarining boshlang'ich
    holati; ular ustida toifa davri qo'shish ikki faylni bir-biriga
    bog'lardi va nosozlik sababi boshqa faylda ko'rinardi.
    """
    stall_id = seed.market_a.unassigned_stall_id
    assert stall_id is not None, "seed'da biriktirilmagan rasta yo'q"
    return stall_id


# ===========================================================================
# D-04 — O'TMISHDAGI TOIFA O'ZGARMAYDI
# ===========================================================================


def test_past_date_keeps_old_category(
    market_scope: MarketScope, market_domain: MarketDomainSeed, market_today: date
) -> None:
    """Toifa o'zgartirilganda o'tmishdagi sana ESKI toifani beradi (D-04).

    `test_past_date_keeps_old_price` ning aynan jufti — va u kerak, chunki
    hisob-kitob narxni TOIFA orqali topadi. Toifa surilsa summa ham
    o'zgaradi, ya'ni tarif qulfini chetlab o'tishning ikkinchi yo'li
    ochilardi.
    """
    a = market_domain.market_a
    stall_id = _target_stall(market_domain)
    old_category = a.category_by_stall[stall_id]
    new_category = next(c for c in a.category_ids if c != old_category)

    effective = market_today + timedelta(days=DAYS_AHEAD)
    day_before = effective - timedelta(days=1)

    with market_scope(a.market_id) as conn:
        before = _category_at(conn, a.market_id, stall_id, day_before)
        assert before == old_category, "seed boshlang'ich toifasi kutilganidan boshqa"

        conn.execute(INSERT_CATEGORY_PERIOD, (a.market_id, stall_id, new_category, effective))

        after = _category_at(conn, a.market_id, stall_id, day_before)

    assert after == old_category, (
        f"{day_before} sanasidagi toifa `{after}` ga o'zgardi — yangi toifa davri "
        "O'TMISHGA ta'sir qildi va o'sha kunlarning summasi retroaktiv qayta yozildi"
    )


def test_effective_day_uses_new_category(
    market_scope: MarketScope, market_domain: MarketDomainSeed, market_today: date
) -> None:
    """Kuchga kirish KUNINING O'ZI yangi toifani beradi — chegara INKLYUZIV."""
    a = market_domain.market_a
    stall_id = _target_stall(market_domain)
    old_category = a.category_by_stall[stall_id]
    new_category = next(c for c in a.category_ids if c != old_category)
    effective = market_today + timedelta(days=DAYS_AHEAD)

    with market_scope(a.market_id) as conn:
        conn.execute(INSERT_CATEGORY_PERIOD, (a.market_id, stall_id, new_category, effective))
        on_effective_day = _category_at(conn, a.market_id, stall_id, effective)

    assert on_effective_day == new_category, (
        f"kuchga kirish kunida ({effective}) toifa `{on_effective_day}` — chegara "
        "EKSKLYUZIV bo'lib qolgan va toifa o'zgarishi bir kun kechikadi"
    )


def test_past_category_period_is_immutable_even_via_raw_sql(
    sync_owner_conn: Connection[TupleRow], market_domain: MarketDomainSeed
) -> None:
    """O'tgan toifa davri EGA roli bilan ham `23514` beradi (D-04, T-02-47).

    Hujum ATAYIN `sbozor_owner` bilan — sabab `test_tariff_history.py::
    test_past_tariff_is_immutable_even_via_raw_sql` da to'liq yozilgan.

    `UPDATE` bu yerda `category_id` ni o'zgartiradi, `valid_from` ni emas:
    aynan shu — "o'tmishdagi rastani arzon toifaga surib qo'yish" — bu
    triggerning MAVJUD BO'LISH sababi.
    """
    a = market_domain.market_a
    stall_id = _target_stall(market_domain)
    old_category = a.category_by_stall[stall_id]
    other_category = next(c for c in a.category_ids if c != old_category)

    found = sync_owner_conn.execute(
        SEEDED_PERIOD_ID, (a.market_id, stall_id, a.operating_since)
    ).fetchone()
    assert found is not None, "seed'ning boshlang'ich toifa davri topilmadi"
    period_id: UUID = found[0]

    with pytest.raises(psycopg.errors.CheckViolation) as update_error:
        sync_owner_conn.execute(
            "UPDATE stall_category_periods SET category_id = %s WHERE id = %s",
            (other_category, period_id),
        )
    assert update_error.value.sqlstate == "23514", (
        f"o'tgan toifa davrini UPDATE qilish `{update_error.value.sqlstate}` berdi — tarif "
        "qulfi bilan BIR XIL kod bo'lishi shart, aks holda ilova ikkita yo'lni ajratadi"
    )

    with pytest.raises(psycopg.errors.CheckViolation) as delete_error:
        sync_owner_conn.execute("DELETE FROM stall_category_periods WHERE id = %s", (period_id,))
    assert delete_error.value.sqlstate == "23514"

    row = sync_owner_conn.execute(READ_PERIOD_ROW, (period_id,)).fetchone()
    assert row is not None, "qator o'chib ketdi — istisno chiqdi, lekin amal bajarildi"
    assert UUID(str(row[0])) == old_category, "toifa o'zgargan — UPDATE qisman o'tdi"


def test_future_category_period_is_editable(
    market_scope: MarketScope,
    sync_owner_conn: Connection[TupleRow],
    market_domain: MarketDomainSeed,
    market_today: date,
) -> None:
    """NAZORAT HOLATI: KELAJAKDAGI toifa davri tahrirlanadi VA o'chiriladi.

    Usiz yuqoridagi test `stall_category_periods` ustidagi HAR QANDAY
    `UPDATE`/`DELETE` ni bloklaydigan buzuq triggerdan ham bemalol o'tardi —
    va "rastani kelasi oydan boshqa toifaga o'tkazamiz" qaroridan qaytish
    imkonsiz bo'lib qolardi.
    """
    a = market_domain.market_a
    stall_id = _target_stall(market_domain)
    old_category = a.category_by_stall[stall_id]
    new_category = next(c for c in a.category_ids if c != old_category)
    effective = market_today + timedelta(days=DAYS_AHEAD)

    with market_scope(a.market_id) as conn:
        created = conn.execute(
            INSERT_CATEGORY_PERIOD, (a.market_id, stall_id, new_category, effective)
        ).fetchone()
    assert created is not None
    period_id: UUID = created[0]

    later = effective + timedelta(days=1)
    sync_owner_conn.execute(
        "UPDATE stall_category_periods SET valid_from = %s WHERE id = %s", (later, period_id)
    )
    updated = sync_owner_conn.execute(READ_PERIOD_ROW, (period_id,)).fetchone()
    assert updated is not None and updated[1] == later, (
        "kelajakdagi toifa davrini tahrirlash o'tmadi — rejalashtirilgan o'zgarishni "
        "surish yo'li yopiq"
    )

    sync_owner_conn.execute("DELETE FROM stall_category_periods WHERE id = %s", (period_id,))
    assert sync_owner_conn.execute(READ_PERIOD_ROW, (period_id,)).fetchone() is None, (
        "kelajakdagi toifa davrini o'chirish o'tmadi — rejani bekor qilish yo'li yopiq"
    )


# ===========================================================================
# STRUKTURAVIY DARVOZA VA 6-FAZANING SO'ROVI
# ===========================================================================


def test_stall_has_no_category_column(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """`stalls` da `category_id` ustuni YO'Q — D-04 ning STRUKTURAVIY isboti.

    Ustun qo'shish "qulaylik" bo'lib ko'rinadi (bitta `JOIN` kamayadi),
    lekin u ikkinchi haqiqat manbai yaratadi: toifani o'zgartirish shu
    ustunni yangilash bilan bajarilardi va o'tmishdagi hisob AVTOMATIK
    ravishda yangi toifada qayta hisoblanardi — ya'ni D-04, D-07 va SC#3
    bir vaqtda buzilardi va HECH QANDAY xato chiqmasdi.

    Yuqoridagi xulq testlari bu holatni USHLAMASDI: ular
    `stall_category_periods` ni o'qiydi va u to'g'ri javob berishda davom
    etardi — faqat mahsulot kodi boshqa ustunni o'qiy boshlardi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        columns = {row[0] for row in conn.execute(STALL_COLUMNS).fetchall()}

    assert "category_id" not in columns, (
        "`stalls` ga `category_id` ustuni qo'shilgan — toifa endi SANADAN kuchga "
        "kirmaydi va o'tmishdagi hisob har o'zgarishda qayta yoziladi (D-04)"
    )


def test_lateral_lookup_returns_category_and_tariff_for_a_date(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """6-fazaning so'rovi ishlaydi VA tarifsiz rasta uchun `NULL` beradi (D-08).

    B bozori ATAYIN tanlangan: seed unda IKKITA toifa yaratadi, lekin
    faqat BIRINCHISIGA tarif yozadi (`fixtures/market_domain.py` modul
    docstringi). Ya'ni bu yerda bir vaqtda ikkala tarmoq ham o'lchanadi:

      * NAZORAT — tarifli rasta uchun `amount_soum` TO'LDIRILGAN;
      * ANOMALIYA — tarifsiz rasta uchun `amount_soum IS NULL`.

    Yolg'iz birinchi tarmoq `LEFT JOIN` `INNER JOIN` ga aylantirilganda ham
    yashil qolardi — va o'shanda tarifsiz rasta natijadan BUTUNLAY tushib,
    "band, lekin tarifsiz" anomaliyasi jimgina yo'qolardi.
    """
    b = market_domain.market_b
    day = b.operating_since

    with market_scope(b.market_id) as conn:
        rows: list[tuple[Any, Any, Any]] = conn.execute(
            LATERAL_LOOKUP, (day, day, b.market_id)
        ).fetchall()

    by_stall = {UUID(str(row[0])): (row[1], row[2]) for row in rows}
    assert set(by_stall) == set(b.stall_ids), (
        f"so'rov {len(by_stall)} rasta qaytardi, seed'da {len(b.stall_ids)} ta — "
        "`LEFT JOIN` `INNER` ga aylantirilgan bo'lishi mumkin"
    )

    for stall_id, (category_id, amount) in by_stall.items():
        expected_category = b.category_by_stall[stall_id]
        assert UUID(str(category_id)) == expected_category, (
            f"rasta {stall_id} uchun toifa `{category_id}`, kutilgan `{expected_category}`"
        )
        if expected_category in b.tariff_by_category:
            assert amount == B_TARIFF_AMOUNT, (
                f"tarifli toifa uchun summa `{amount}`, kutilgan {B_TARIFF_AMOUNT}"
            )
        else:
            assert amount is None, (
                f"TARIFSIZ toifadagi rasta uchun summa `{amount}` qaytdi — u `NULL` "
                "bo'lishi SHART (D-08). Har qanday son o'sha kunni hisoblanadigan "
                "qilib ko'rsatadi va anomaliya chiqmaydi"
            )

    untariffed = [stall for stall, (_, amount) in by_stall.items() if amount is None]
    assert len(untariffed) == 1, (
        f"tarifsiz rastalar soni {len(untariffed)}, kutilgan 1 — seed B bozorida BITTA "
        "toifani ataylab tarifsiz qoldiradi va bu testning manfiy holati"
    )
