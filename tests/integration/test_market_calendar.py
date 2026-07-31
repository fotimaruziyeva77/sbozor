"""Ish kunlari kalendari — SC#4 ning DB darajasidagi isboti (MARKET-05, D-17/D-18).

=============================================================================
SC#4: «bayram/yopiq kunga patta hisoblanmaydi». Butun qaror BITTA
funksiyada — `market_is_open(market_id, date)` — va 6-faza unga BITTA shart
sifatida murojaat qiladi::

    WHERE market_is_open(:market_id, :business_date)

Ya'ni bu funksiyaning har bir qavati bevosita PULGA aylanadi: `true` ortiqcha
qaytsa bozor yopiq kunda ham qarz yozadi (sotuvchilar bilan nizo), `false`
ortiqcha qaytsa butun kunning tushumi jimgina yo'qoladi.

UCH QAVAT VA ULARNING TARTIBI (RESEARCH Pattern 7):
  1. `market_calendar_exceptions` — istisno HAR DOIM ustun (D-18);
  2. `market_profile.open_weekdays` — haftalik jadval (ISO kun raqami);
  3. `false` — FAIL-CLOSED.
=============================================================================

⚠ FAIL-CLOSED'NING IKKI TARMOG'I ATAYIN ALOHIDA SINALADI va ikkinchisi
funksiyaning HUQUQ REJIMIGA bog'liq: `market_is_open()` — 2-fazadagi
YAGONA `SECURITY DEFINER` BO'LMAGAN funksiya, ya'ni u chaqiruvchi huquqi
bilan ishlaydi va RLS unga to'liq qo'llanadi. `SECURITY DEFINER` qilinganda
u `owner_bootstrap` policy'si ostida RLS'dan chiqib ketardi va bir bozor
boshqasining bayram jadvalini o'qiy olardi (T-02-41).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fixtures import MarketScope
from fixtures.market_domain import MarketDomainSeed
from psycopg import Connection
from psycopg.rows import TupleRow

IS_OPEN = "SELECT market_is_open(%s, %s::date)"

INSERT_EXCEPTION = (
    "INSERT INTO market_calendar_exceptions (market_id, exception_date, is_open, note) "
    "VALUES (%s, %s, %s, %s) RETURNING id"
)
DELETE_EXCEPTION = "DELETE FROM market_calendar_exceptions WHERE id = %s"

READ_PROFILE_ID = "SELECT id FROM market_profile WHERE market_id = %s"
UPDATE_WEEKDAYS = "UPDATE market_profile SET open_weekdays = %s WHERE market_id = %s"

CALENDAR_COLUMNS = (
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_schema = 'public' AND table_name = 'market_calendar_exceptions'"
)

AUDIT_ROWS = (
    "SELECT action, old_value, new_value, changed_keys FROM audit_log "
    "WHERE table_name = %s AND row_id = %s ORDER BY id"
)

CLOSED_MONDAY = date(2026, 8, 24)
"""DUSHANBA — A bozorining `open_weekdays` ida (2..7) YO'Q, ya'ni yopiq.

Kunning haqiqatan dushanba ekani har bir testda ASSERT qilinadi: sana
noto'g'ri tanlansa test o'z ma'nosini jimgina yo'qotardi va "yopiq kun
yopiq" o'rniga "ochiq kun ochiq" ni sinardi.
"""

OPEN_TUESDAY = date(2026, 8, 25)
"""SESHANBA — A bozorining haftalik jadvalida BOR (nazorat holati)."""

ALL_WEEKDAYS = [1, 2, 3, 4, 5, 6, 7]

HOLIDAY_NOTE = "Mustaqillik kuni (probe)"


def _one(conn: Connection[TupleRow], sql: str, params: tuple[Any, ...]) -> Any:
    row = conn.execute(sql, params).fetchone()
    assert row is not None, f"so'rov 0 qator qaytardi: {sql}"
    return row


def _is_open(conn: Connection[TupleRow], market_id: UUID, day: date) -> bool:
    return bool(_one(conn, IS_OPEN, (market_id, day))[0])


@pytest.fixture
def market_without_profile(sync_owner_conn: Connection[TupleRow], migrated: None) -> Iterator[UUID]:
    """`market_profile` qatori BO'LMAGAN bozor — fail-closed'ning 1-tarmog'i.

    ATAYIN xom `INSERT INTO markets` bilan yaratiladi, `market_create()`
    bilan EMAS: mahsulot funksiyasi profil qatorini bozor bilan BIR
    TRANZAKSIYADA yaratadi (aynan shu holat yuzaga kelmasin deb), ya'ni u
    orqali bunday bozor umuman qurib bo'lmaydi.

    Holat baribir haqiqiy: profil qatori qo'lda o'chirilishi, migratsiya
    yarim qolishi yoki eski ma'lumot ko'chirilishi mumkin. O'shanda
    funksiya `false` qaytarishi SHART — "sozlamasi yo'q bozorda hamma kun
    ochiq" degan teskari standart har bir kunga soxta qarz yozardi.
    """
    market_id = uuid4()
    sync_owner_conn.execute(
        "INSERT INTO markets (id, name) VALUES (%s, %s)",
        (str(market_id), "Profilsiz probe bozori"),
    )
    try:
        yield market_id
    finally:
        sync_owner_conn.execute("DELETE FROM markets WHERE id = %s", (str(market_id),))


# ===========================================================================
# 2-QAVAT — HAFTALIK JADVAL (rad etish + nazorat JUFTLIGI)
# ===========================================================================


def test_weekly_closed_day_is_closed(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Haftalik jadvalda yo'q kun — `false`, birorta istisno qatorisiz (D-17).

    Bu 2-qavatning o'zi: `market_calendar_exceptions` BO'SH, ya'ni javob
    faqat `open_weekdays` massividan keladi. Karmanada dushanba — bozor
    yopiq kuni, va o'sha kunga patta hisoblash sotuvchilar bilan darhol
    nizo keltirib chiqarardi.
    """
    a = market_domain.market_a
    assert CLOSED_MONDAY.isoweekday() == 1, "sana dushanba emas — test o'z shartini bajarmayapti"
    assert 1 not in a.open_weekdays, (
        f"seed'ning haftalik jadvali {a.open_weekdays} — dushanba YOPIQ bo'lishi kerak"
    )

    with market_scope(a.market_id) as conn:
        result = _is_open(conn, a.market_id, CLOSED_MONDAY)

    assert result is False, (
        f"{CLOSED_MONDAY} (dushanba) uchun `market_is_open` `{result}` qaytardi — haftalik "
        "jadval qavati ishlamayapti va yopiq kunga patta hisoblanadi (SC#4 buzilgan)"
    )


def test_open_weekday_is_open(market_scope: MarketScope, market_domain: MarketDomainSeed) -> None:
    """NAZORAT HOLATI: jadvalda BOR kun — `true`.

    Usiz yuqoridagi test HAR DOIM `false` qaytaradigan buzuq funksiyadan
    (masalan `COALESCE` ning oxirgi `false` argumenti birinchiga surilib
    qolgan holatdan) bemalol o'tardi — va o'shanda bozor HECH QACHON
    ishlamasdi, tushum jimgina nolga tushardi.
    """
    a = market_domain.market_a
    assert OPEN_TUESDAY.isoweekday() == 2, "sana seshanba emas"
    assert 2 in a.open_weekdays

    with market_scope(a.market_id) as conn:
        result = _is_open(conn, a.market_id, OPEN_TUESDAY)

    assert result is True, (
        f"{OPEN_TUESDAY} (seshanba) uchun `market_is_open` `{result}` qaytardi — NAZORAT "
        "HOLATI yiqildi, ya'ni funksiya har doim `false` beryapti va butun tushum yo'qoladi"
    )


# ===========================================================================
# 1-QAVAT — ISTISNO HAR IKKI YO'NALISHDA USTUN TURADI (D-18)
# ===========================================================================


def test_exception_open_overrides_weekly_closure(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """«Bu dushanba ishlaymiz» — istisno haftalik jadvaldan USTUN (D-18).

    Bayramoldi savdosi yoki maxsus bozor kuni — Karmanada odatiy holat.
    Istisnosiz ma'muriyat butun haftalik jadvalni vaqtincha o'zgartirishga
    majbur bo'lardi va uni QAYTA TIKLASHNI unutishi mumkin edi.

    Boshlang'ich holat ham o'lchanadi (`false`), aks holda test "istisno
    ta'sir qildi" ni "kun allaqachon ochiq edi" dan ajrata olmasdi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        assert _is_open(conn, a.market_id, CLOSED_MONDAY) is False, "boshlang'ich holat noto'g'ri"

        conn.execute(INSERT_EXCEPTION, (a.market_id, CLOSED_MONDAY, True, "Maxsus savdo kuni"))
        result = _is_open(conn, a.market_id, CLOSED_MONDAY)

    assert result is True, (
        f"`is_open=true` istisnosi qo'yilgandan keyin ham {CLOSED_MONDAY} yopiq — istisno "
        "qavati haftalik jadvaldan PASTDA turibdi (COALESCE tartibi buzilgan)"
    )


def test_holiday_exception_closes_an_open_day(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Bayram — ochiq kunni yopadi (D-18 ning teskari yo'nalishi).

    Ikkala yo'nalish ham kerak: faqat "yopiqni ochish" ishlaydigan
    implementatsiya (masalan `COALESCE(NULLIF(e.is_open, false), ...)`)
    birinchi testdan o'tib, bayram kunini OCHIQ qoldirardi — ya'ni yilning
    eng ko'p nizo chiqadigan kunlariga qarz yozilardi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        assert _is_open(conn, a.market_id, OPEN_TUESDAY) is True, "boshlang'ich holat noto'g'ri"

        conn.execute(INSERT_EXCEPTION, (a.market_id, OPEN_TUESDAY, False, HOLIDAY_NOTE))
        result = _is_open(conn, a.market_id, OPEN_TUESDAY)

    assert result is False, (
        f"bayram istisnosi qo'yilgandan keyin ham {OPEN_TUESDAY} ochiq — `is_open=false` "
        "e'tiborga olinmayapti va bayram kuniga patta hisoblanadi (SC#4 buzilgan)"
    )


# ===========================================================================
# 3-QAVAT — FAIL-CLOSED, IKKI TARMOQ (nazorat holati bilan)
# ===========================================================================


def test_calendar_is_fail_closed(
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
    market_without_profile: UUID,
) -> None:
    """Sozlamasiz bozor VA cross-tenant so'rov — ikkalasi ham `false` (T-02-41).

    IKKI TARMOQ IKKI XIL SABABDAN `false` beradi va ikkalasi ham kerak:

      (a) SOZLAMASIZ BOZOR — `market_profile` qatori yo'q, ya'ni 2-qavat
          `NULL` qaytaradi va `COALESCE` oxirgi argumentga tushadi. Teskari
          standart (`true`) tanlanganda profilsiz bozor HAR KUNI ochiq
          bo'lib, har bir rastaga soxta qarz yozilardi.

      (b) CROSS-TENANT — A konteksti ostida B ning `market_id` si
          so'ralganda IKKALA subquery ham RLS tufayli 0 qator beradi. Bu
          funksiyaning INVOKER huquqi bilan ishlashining BEVOSITA natijasi:
          `SECURITY DEFINER` bo'lganda u B ning kalendarini o'qib `true`
          qaytarishi mumkin edi.

    ⚠ (b) UCHUN NAZORAT HOLATI MAJBURIY: `false` javobi izolyatsiyadan ham,
    funksiyaning buzuqligidan ham kelishi mumkin. B kontekstiga o'tib AYNI
    so'rov `true` berishi ikkalasini ajratadi — usiz bu test har doim
    `false` qaytaradigan funksiyadan ham o'tib ketardi.
    """
    a = market_domain.market_a
    b = market_domain.market_b

    with market_scope(market_without_profile) as conn:
        no_profile = _is_open(conn, market_without_profile, OPEN_TUESDAY)
    assert no_profile is False, (
        "profil qatori yo'q bozor uchun `market_is_open` `true` qaytardi — fail-closed "
        "buzilgan va sozlanmagan bozor har kuni qarz yozadi"
    )

    with market_scope(a.market_id) as conn:
        cross_tenant = _is_open(conn, b.market_id, OPEN_TUESDAY)
    assert cross_tenant is False, (
        "A konteksti ostida B ning kalendari O'QILDI — `market_is_open()` `SECURITY "
        "DEFINER` ga o'tkazilgan bo'lishi mumkin (T-02-41)"
    )

    with market_scope(b.market_id) as conn:
        own_context = _is_open(conn, b.market_id, OPEN_TUESDAY)
    assert own_context is True, (
        "NAZORAT HOLATI YIQILDI: B o'z konteksti ostida ham `false` qaytardi — yuqoridagi "
        "cross-tenant `false` izolyatsiyadan emas, funksiyaning buzuqligidan kelgan"
    )


# ===========================================================================
# YOZISH YUZASI, AUDIT VA STRUKTURA
# ===========================================================================


def test_duplicate_exception_date_is_rejected(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Bir sanaga ikkinchi istisno `23505` beradi.

    Unikaliksiz `market_is_open()` ning birinchi subquery'si IKKI qator
    olib "more than one row returned by a subquery" bilan yiqilardi — ya'ni
    butun kunlik hisob-kitob bitta takroriy qator sababli to'xtardi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        conn.execute(INSERT_EXCEPTION, (a.market_id, CLOSED_MONDAY, True, None))

        with pytest.raises(psycopg.errors.UniqueViolation) as excinfo:
            conn.execute(INSERT_EXCEPTION, (a.market_id, CLOSED_MONDAY, False, None))

    assert excinfo.value.sqlstate == "23505", (
        f"takroriy istisno `{excinfo.value.sqlstate}` bilan rad etildi — ilova qatlami uni "
        "`409` ga aylantira olmaydi"
    )


def test_exception_change_is_audited(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Istisno qo'shilishi VA o'chirilishi `audit_log` da ko'rinadi (T-02-50).

    Bir kunni "bayram" deb belgilash — o'sha kunning BUTUN yig'imini
    hisobdan chiqaradi va bu jadvalda pul ustuni yo'q, ya'ni moliyaviy
    jadvallar auditi uni umuman qamramaydi. Undan qoladigan yagona iz —
    shu trigger.

    `DELETE` ham tekshiriladi: istisnoni qo'yib, kun o'tgach uni O'CHIRIB
    tashlash — izni yo'qotishning eng oddiy usuli bo'lardi va jurnalda
    faqat "qo'shildi" qolib, "olib tashlandi" ko'rinmasdi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        exception_id = _one(
            conn, INSERT_EXCEPTION, (a.market_id, OPEN_TUESDAY, False, HOLIDAY_NOTE)
        )[0]
        conn.execute(DELETE_EXCEPTION, (exception_id,))
        rows = conn.execute(AUDIT_ROWS, ("market_calendar_exceptions", exception_id)).fetchall()

    actions = [row[0] for row in rows]
    assert actions == ["insert", "delete"], (
        f"audit jurnalida {actions} — kutilgan ['insert', 'delete']. Yopiq kun belgilash "
        "yoki uni bekor qilish izsiz qolgan"
    )

    inserted, deleted = rows
    assert inserted[2] is not None and inserted[2]["note"] == HOLIDAY_NOTE, (
        "qo'shilgan istisno auditda IZOHSIZ yozilgan — 'nega yopiq' savoli javobsiz qoladi"
    )
    assert deleted[1] is not None and deleted[1]["is_open"] is False, (
        "o'chirilgan istisnoning ESKI qiymati auditda yo'q — nima yo'qotilgani ko'rinmaydi"
    )


def test_weekday_change_is_audited(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """`open_weekdays` o'zgarishi auditda old->new bilan ko'rinadi (T-02-50).

    Haftalik jadvalni o'zgartirish — istisno qo'yishdan ham KATTA ta'sirga
    ega: u bitta kunni emas, HAR HAFTADAGI o'sha kunni hisobdan chiqaradi.
    Shuning uchun u ham istisno bilan bir xil audit qamrovida bo'lishi
    shart, aks holda "dushanbani jimgina yopiq qilib qo'yish" hech qanday
    iz qoldirmasdi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        profile_id = _one(conn, READ_PROFILE_ID, (a.market_id,))[0]
        conn.execute(UPDATE_WEEKDAYS, (ALL_WEEKDAYS, a.market_id))
        rows = conn.execute(AUDIT_ROWS, ("market_profile", profile_id)).fetchall()

    updates = [row for row in rows if row[0] == "update"]
    assert len(updates) == 1, (
        f"haftalik jadval o'zgarishi uchun {len(updates)} audit qatori topildi — kutilgan 1"
    )

    _action, old_value, new_value, changed_keys = updates[0]
    assert changed_keys is not None and "open_weekdays" in changed_keys, (
        f"`changed_keys` da `open_weekdays` yo'q: {changed_keys}"
    )
    assert old_value is not None and new_value is not None
    assert old_value["open_weekdays"] == list(a.open_weekdays), (
        f"auditdagi eski jadval {old_value['open_weekdays']}, seed'da {list(a.open_weekdays)}"
    )
    assert new_value["open_weekdays"] == ALL_WEEKDAYS, (
        f"auditdagi yangi jadval {new_value['open_weekdays']}, kutilgan {ALL_WEEKDAYS}"
    )


def test_calendar_is_market_level_only(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """`market_calendar_exceptions` da `zone_id`/`stall_id` ustuni YO'Q — D-18 ning strukturasi.

    D-18: ish kunlari FAQAT bozor darajasida. Zona yoki rasta darajasidagi
    kalendar `market_is_open()` ni ikki argumentli funksiyadan chiqarib
    yuborardi va 6-fazadagi "bitta shart" kontrakti buzilardi — kunlik job
    har bir rasta uchun alohida kalendar qidirishga majbur bo'lardi.

    Xulq testlari bu holatni USHLAMASDI: ustun qo'shilgani bilan mavjud
    qatorlar `NULL` bo'lib qolardi va hamma javob o'zgarmasdi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        columns = {row[0] for row in conn.execute(CALENDAR_COLUMNS).fetchall()}

    forbidden = {"zone_id", "stall_id"} & columns
    assert not forbidden, (
        f"`market_calendar_exceptions` ga {sorted(forbidden)} ustun(lar)i qo'shilgan — "
        "kalendar endi bozor darajasidan pastga tushdi va `market_is_open(market_id, date)` "
        "kontrakti yetarli emas (D-18)"
    )
