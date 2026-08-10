"""Pul yozuvlarining O'ZGARMASLIGI — XULQ bo'yicha isbot (D-07/D-23/D-25/D-27).

=============================================================================
UCHTA QOIDA BU FAYLNING SHAKLINI BELGILAYDI VA UCHALASI HAM O'LCHANGAN.

  1. ⛔ ULANISH `sbozor_owner` BILAN — ENG KATTA HUQUQLI ROL BILAN.
     `sbozor_app` bilan sinash ZAIFROQ bo'lardi: RLS qatorni yashirsa
     urinish 0 qatorga tegib, JIMGINA «muvaffaqiyatli» tugardi va biz
     «RLS to'sdi» bilan «trigger to'sdi» ni umuman ajrata olmasdik.
     Qo'riqchilar `SECURITY DEFINER` emas va hech qanday rolga istisno
     bermaydi, ya'ni ega ham ulardan o'tolmaydi
     (`test_occupancy_immutable.py:1-20` da o'rnatilgan qoida).

  2. ⛔ HAQIQIY `postgres:18.4` — soxta qatlam YO'Q. Tekshirilayotgan
     narsaning O'ZI DB triggeri va `CHECK` konstraytidir; ularni
     almashtirgan test o'z tasavvurini o'lchagan bo'lardi.

  3. ⛔ HAR RAD ETISH DA'VOSI SQLSTATE NI OCHIQ SOLISHTIRADI, istisno
     klassining nomi bilan kifoyalanmaydi. Repoda xato-sinfi qo'riqchi
     SHAKLI bilan birga yuradi (06-04 da qulflangan):

         P0001 (`RaiseException`)  -> SHARTSIZ append-only qo'riqchi
                                      (`charge_immutable`, `payment_immutable`)
         23514 (`CheckViolation`)  -> SHARTLI domen-qoidasi qo'riqchisi
                                      (`shift_declaration_immutable`)

     Ya'ni `cashier_shifts` ga SHARTSIZ shakl qo'yilsa (yoki teskarisi)
     kodning O'ZI o'zgaradi va test qizaradi — «rad etildi» bilan
     kifoyalanish shaklning JIMGINA almashtirilishini sezmasdi.
=============================================================================
NAZORAT HOLATLARI MAJBURIY — ULARSIZ HAR RAD ETISH DA'VOSI BO'SH BO'LARDI.

`BEFORE INSERT OR UPDATE OR DELETE` deb yozilgan qo'riqchi rad etish
testlarining HAMMASINI yashil qoldirardi va butun kassa quvurini jimgina
o'ldirardi: 06-08 birorta hisob yoza olmasdi va nosozlik faqat kunlik
hisobot bo'sh chiqqanda ko'rinardi. Shuning uchun har guruhda O'TISHI
KERAK bo'lgan yo'l ham o'lchanadi:

    daily_charges     -> `INSERT` o'tadi
    payments          -> STORNO qatori o'tadi (D-23 ning butun yo'li)
    cashier_shifts    -> `open` -> `closed` o'tadi (CASH-04 ning oqimi)
    charge_adjustments-> tuzatish qatori o'tadi (D-07 ning ijobiy yarmi)
=============================================================================
⚠ KASKAD SHOXI BU YERDA TAKRORLANMAYDI. «Qoralama bozorda `DELETE`
o'tadi» da'vosi `test_market_delete_guard.py::test_draft_market_deletion_
covers_the_billing_domain` da funksiyani HAQIQATAN chaqirib o'lchangan.
Bu fayl faqat JONLI bozorni ko'radi — istisnoning IKKINCHI tomonini.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from fixtures.billing_domain import (
    SEED_BUSINESS_DATE,
    TARIFF_SOUM,
    BillingDomainSeed,
    MarketBillingRows,
    add_charge_evidence,
    add_daily_charge,
    add_payment,
    billing_domain,
    billing_domain_before_day_close,
    slot_count,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    PaymentKind,
    ReversalReason,
    ShiftStatus,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SET_MARKET = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti — `audit_log` ni O'QISH uchun.

`audit_read` policy'si tenant-scoped va u jadval EGASIGA ham qo'llanadi
(`FORCE`). Kontekstsiz sanoq HAR IKKALA o'lchovda ham 0 bo'lardi va
audit da'vosi BO'SH ROST bo'lib qolardi
(`test_occupancy_immutable.py:276-282` da o'lchangan tuzoq).
"""

AUDIT_COUNT = "SELECT count(*) FROM audit_log WHERE table_name = %s"

UNCONDITIONAL = "P0001"
"""SHARTSIZ append-only qo'riqchining SQLSTATE'i (fayl docstringidagi 3-qoida)."""

CONDITIONAL = "23514"
"""SHARTLI domen-qoidasi qo'riqchisining (VA `CHECK` konstraytining) SQLSTATE'i."""

UNIQUE_VIOLATION = "23505"


class Env:
    """Beshta qatlamli seed — `test_day_close.Env` shakli.

    ⚠ `billing_domain_before_day_close` VARIANTI ISHLATILADI (ya'ni
      `day_close` CHAQIRILMAYDI) va bu ONGLI tanlov: o'zgarmaslik
      qo'riqchilari `stall_slot_occupancy` ga UMUMAN tegmaydi va bu
      guruhlarning birortasi ham materializatsiya qilingan slotga
      tayanmaydi — qatorlarni testning O'ZI yozadi. Ikkinchi variantni
      shu yerda ishlatish har testga ikki `day_close` yugurishini
      qo'shardi va faza byudjetini (`gate` 1250 s) sababsiz yeb qo'yardi.

      `billing_domain` (slotlar BILAN) varianti shu faylning OXIRGI
      testida o'lchanadi — dalil zanjiri aynan o'sha slotlarga tayanadi.
    """

    def __init__(self, billing: BillingDomainSeed) -> None:
        self.billing = billing

    @property
    def live(self) -> MarketBillingRows:
        """A bozori — JONLI (`is_active = true`) va qo'riqchilar to'liq kuchda."""
        return self.billing.market_a

    @property
    def market_id(self) -> UUID:
        return self.live.market_id

    @property
    def stall_id(self) -> UUID:
        stall_id = self.live.stall_with_one_ai_occupied_slot
        assert stall_id is not None, "nazorat: seedda hisob yoziladigan rasta yo'q"
        return stall_id


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        yield Env(billing)


def _rows(conn: Connection[TupleRow], sql: str, params: tuple[object, ...]) -> int:
    row = conn.execute(sql, params).fetchone()
    assert row is not None
    return int(row[0])


def _assert_live(conn: Connection[TupleRow], market_id: UUID) -> None:
    """NAZORAT: bozor JONLI. Qoralamada `DELETE` o'tadi va test o'z shartini yo'qotardi."""
    row = conn.execute("SELECT is_active FROM markets WHERE id = %s", (str(market_id),)).fetchone()
    assert row is not None and row[0] is True, (
        "bozor JONLI emas — uchala qo'riqchi ham qoralama bozorda `DELETE` ni "
        "o'tkazadi va rad etish da'volari hech nimani o'lchamasdi"
    )


def _charge(conn: Connection[TupleRow], env: Env) -> UUID:
    """Seedning tarif zanjiridan BITTA hisob yozadi (NAZORAT holati ham shu)."""
    charge_id, _ = add_daily_charge(
        conn,
        market_id=env.market_id,
        stall_id=env.stall_id,
        vendor_id=env.live.vendor_id,
        tariff_id=env.live.tariff_id,
    )
    return charge_id


# ===========================================================================
# 1. `daily_charges` — YOZILGAN HISOB TAHRIRLANMAYDI HAM, O'CHMAYDI HAM (D-07)
# ===========================================================================


def test_a_written_charge_cannot_be_edited_or_deleted(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """`UPDATE` (ikki xil ustun) va `DELETE` rad etiladi; `INSERT` O'TADI.

    =========================================================================
    TAHDID IKKI TOMONDAN KELADI VA IKKALASI HAM ALOHIDA O'LCHANADI:

      `SET amount_soum = 1`   -> qarzni JIMGINA yo'q qilish (T-06-15);
      `SET service_date = ...`-> hisobni BOSHQA kunga ko'chirish, ya'ni
                                 idempotentlik kalitini
                                 (`market_id, stall_id, service_date`)
                                 chetlab o'tib IKKINCHI hisob yozish yo'li;
      `DELETE`                -> qarzni butunlay YO'Q qilish.

    Uchalasi ham SHARTSIZ qo'riqchi bilan yopiladi, ya'ni SQLSTATE
    `P0001`. Tuzatish YANGI QATOR bo'ladi (`charge_adjustments`) va asl
    summa nizoda ko'rinib qoladi (D-02).

    ⚠ XATO XABARIDA `TG_OP` BO'LISHI ALOHIDA tekshiriladi: ikki xil
      urinish ikki xil tahdid modelidan keladi va log'da ular ajralib
      turishi kerak.
    =========================================================================
    """
    _assert_live(sync_owner_conn, env.market_id)

    before = _rows(
        sync_owner_conn,
        "SELECT count(*) FROM daily_charges WHERE market_id = %s",
        (str(env.market_id),),
    )
    charge_id = _charge(sync_owner_conn, env)
    after = _rows(
        sync_owner_conn,
        "SELECT count(*) FROM daily_charges WHERE market_id = %s",
        (str(env.market_id),),
    )
    assert after == before + 1, (
        f"NAZORAT `INSERT` i o'tmadi ({before} -> {after}) — qo'riqchi `INSERT` ni "
        "ham bloklayapti va butun kunlik hisob quvuri o'lik"
    )

    with pytest.raises(psycopg.errors.RaiseException) as amount_error:
        sync_owner_conn.execute(
            "UPDATE daily_charges SET amount_soum = 1 WHERE id = %s", (str(charge_id),)
        )
    assert amount_error.value.sqlstate == UNCONDITIONAL
    assert "daily_charges is append-only" in str(amount_error.value)
    assert "UPDATE" in str(amount_error.value), (
        f"xato xabarida `TG_OP` yo'q: {amount_error.value!r} — ikki xil urinishni "
        "log'da ajratib bo'lmasdi"
    )

    with pytest.raises(psycopg.errors.RaiseException) as date_error:
        sync_owner_conn.execute(
            "UPDATE daily_charges SET service_date = service_date - 1 WHERE id = %s",
            (str(charge_id),),
        )
    assert date_error.value.sqlstate == UNCONDITIONAL

    with pytest.raises(psycopg.errors.RaiseException) as delete_error:
        sync_owner_conn.execute("DELETE FROM daily_charges WHERE id = %s", (str(charge_id),))
    assert delete_error.value.sqlstate == UNCONDITIONAL
    assert "DELETE" in str(delete_error.value)

    # HOLAT O'ZGARMAGANINI ALOHIDA o'lchash: istisno ko'tarilib, qator
    # baribir o'zgargan bo'lishi mumkin edi (trigger `AFTER` bo'lib qolgan
    # taqdirda).
    row = sync_owner_conn.execute(
        "SELECT amount_soum FROM daily_charges WHERE id = %s", (str(charge_id),)
    ).fetchone()
    assert row is not None and row[0] == TARIFF_SOUM, (
        f"hisob qatori o'zgardi yoki o'chdi ({row}) — qo'riqchi `BEFORE` emas, "
        "`AFTER` bo'lib qolgan bo'lishi mumkin"
    )


# ===========================================================================
# 2. `payments` — APPEND-ONLY, TUZATISH FAQAT STORNO (D-23)
# ===========================================================================


def test_a_payment_cannot_be_edited_or_deleted(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """To'lovni tahrirlash ham, o'chirish ham rad etiladi (T-06-16).

    Tahdid `daily_charges` nikidan TESKARI tomondan keladi va u
    kuchliroq: yozilgan to'lovni o'chirish «pul kelmagan» degan da'voni
    HECH QANDAY iz qoldirmasdan yaratadi — ya'ni aynan mahsulot fosh
    qiladigan nosozlik turi (`PROJECT.md` Core Value).
    """
    _assert_live(sync_owner_conn, env.market_id)
    payment_id = add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=env.stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
    )

    with pytest.raises(psycopg.errors.RaiseException) as amount_error:
        sync_owner_conn.execute(
            "UPDATE payments SET amount_soum = 1 WHERE id = %s", (str(payment_id),)
        )
    assert amount_error.value.sqlstate == UNCONDITIONAL
    assert "payments is append-only" in str(amount_error.value)

    # ⛔ IKKINCHI USTUN ATAYIN `reversal_reason`: «to'lovni bekor
    #    qilganday ko'rsatish» eng arzon soxtalashtirish yo'li bo'lardi —
    #    summa o'zgarmaydi, lekin qator hisobotdan chiqib ketardi.
    with pytest.raises(psycopg.errors.RaiseException) as reason_error:
        sync_owner_conn.execute(
            "UPDATE payments SET reversal_reason = %s WHERE id = %s",
            (ReversalReason.WRONG_AMOUNT.value, str(payment_id)),
        )
    assert reason_error.value.sqlstate == UNCONDITIONAL

    with pytest.raises(psycopg.errors.RaiseException) as delete_error:
        sync_owner_conn.execute("DELETE FROM payments WHERE id = %s", (str(payment_id),))
    assert delete_error.value.sqlstate == UNCONDITIONAL
    assert "DELETE" in str(delete_error.value)


def test_the_reversal_path_is_open_and_leaves_the_original_row(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """NAZORAT: STORNO YO'LI ISHLAYDI va asl qator O'ZGARMAY QOLADI (D-23/D-02).

    =========================================================================
    ⛔ USIZ YUQORIDAGI TEST «to'lovni umuman tuzatib bo'lmaydi» ni
       isbotlagan bo'lardi — bu esa MAHSULOTNI ISHLAMAYDIGAN qilardi:
       kassir noto'g'ri rastaga yozgan to'lovni tuzatishning YAGONA yo'li
       yo'q bo'lardi.

    Nizoda IKKALA yozuv ham ko'rinadi — «to'ladi» va «bekor qilindi,
    sababi shu» (D-02). Aynan shuning uchun asl qatorning O'ZGARMAGANI
    ham alohida o'lchanadi: storno uni tahrirlab qo'ysa D-02 ning butun
    modeli qulardi.
    =========================================================================
    """
    original_id = add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=env.stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
    )

    reversal_id = add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=env.stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
        kind=PaymentKind.REVERSAL.value,
        reverses_payment_id=original_id,
        reversal_reason=ReversalReason.WRONG_STALL.value,
    )

    rows = sync_owner_conn.execute(
        "SELECT id, kind, amount_soum, reverses_payment_id, reversal_reason "
        "FROM payments WHERE id = ANY(%s::uuid[]) ORDER BY kind",
        ([str(original_id), str(reversal_id)],),
    ).fetchall()
    by_id = {row[0]: row for row in rows}

    assert by_id[original_id][1] == PaymentKind.PAYMENT.value
    assert by_id[original_id][2] == TARIFF_SOUM, "asl to'lov storno bilan O'ZGARDI (D-02 buzilgan)"
    assert by_id[original_id][3] is None
    assert by_id[original_id][4] is None
    assert by_id[reversal_id][3] == original_id, "storno asl qatorga bog'lanmagan"
    assert by_id[reversal_id][4] == ReversalReason.WRONG_STALL.value


def test_a_reversal_without_a_reason_is_impossible(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """Sababsiz storno IFODALAB BO'LMAYDI -> `CheckViolation` (D-19/D-23).

    Sababsiz storno «pul kelmagan» da'vosini HECH NARSA bilan
    izohlamasdi: nizoda «bekor qilindi» yozuvi turardi-yu, NEGA bekor
    qilingani javobsiz qolardi. `ck_payments_reversal_reason_is_paired`
    ikki tomonlama tenglik, ya'ni teskarisi ham (oddiy to'lovda sabab)
    imkonsiz.
    """
    original_id = add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=env.stall_id,
        vendor_id=env.live.vendor_id,
        cashier_id=env.live.cashier_id,
        shift_id=env.live.open_shift_id,
    )

    with pytest.raises(psycopg.errors.CheckViolation) as error:
        add_payment(
            sync_owner_conn,
            market_id=env.market_id,
            stall_id=env.stall_id,
            vendor_id=env.live.vendor_id,
            cashier_id=env.live.cashier_id,
            shift_id=env.live.open_shift_id,
            kind=PaymentKind.REVERSAL.value,
            reverses_payment_id=original_id,
            reversal_reason=None,
        )
    assert error.value.sqlstate == CONDITIONAL
    assert "reversal_reason_is_paired" in str(error.value), (
        f"xato boshqa konstraytdan keldi: {error.value!r}"
    )


# ===========================================================================
# 3. `cashier_shifts` — SHARTLI QO'RIQCHI VA UNING CHEGARASI (D-25, D-27)
# ===========================================================================


def test_a_shift_closes_once_and_never_reopens(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """`open` -> `closed` O'TADI; yopilgan qatorga ikkinchi `UPDATE` RAD ETILADI.

    =========================================================================
    ⛔ IKKALA YARIM HAM MAJBURIY VA ULAR BIR-BIRINI ALMASHTIRMAYDI.

    Faqat rad etishni sinash BUTUNLAY SHARTSIZ qo'riqchini ham yashil
    ko'rsatardi — holbuki o'shanda smenani umuman yopib bo'lmasdi va
    CASH-04 ning oqimi (ko'r deklaratsiya -> variance) IMKONSIZ bo'lardi.
    Faqat o'tishni sinash esa «qayta ochish» yo'lini ochiq qoldirardi:
    smenani tizim summasiga MOSLASHTIRISH mumkin bo'lardi va ko'r
    deklaratsiya ma'nosini butunlay yo'qotardi.

    ⚠ SQLSTATE `23514` (`CheckViolation`), `P0001` EMAS — bu SHARTLI
      qo'riqchi va shakl 06-04 da qulflangan (fayl docstringidagi
      3-qoida).
    =========================================================================
    """
    shift_id = env.live.open_shift_id

    sync_owner_conn.execute(
        "UPDATE cashier_shifts SET status = %s, closed_at = now(), "
        "declared_soum = 100000, system_soum = 90000 WHERE id = %s",
        (ShiftStatus.CLOSED.value, str(shift_id)),
    )
    closed = sync_owner_conn.execute(
        "SELECT status, declared_soum, system_soum FROM cashier_shifts WHERE id = %s",
        (str(shift_id),),
    ).fetchone()
    assert closed is not None and closed[0] == ShiftStatus.CLOSED.value, (
        "smenani yopib bo'lmadi — qo'riqchi SHARTSIZ shaklga aylangan bo'lishi "
        "mumkin va o'shanda CASH-04 ning butun oqimi IMKONSIZ"
    )
    assert (closed[1], closed[2]) == (100000, 90000)

    with pytest.raises(psycopg.errors.CheckViolation) as reopened:
        sync_owner_conn.execute(
            "UPDATE cashier_shifts SET declared_soum = 1 WHERE id = %s", (str(shift_id),)
        )
    assert reopened.value.sqlstate == CONDITIONAL
    assert str(shift_id) in str(reopened.value), (
        f"xato xabari qaysi smena rad etilganini aytmayapti: {reopened.value!r}"
    )

    # ⛔ IKKINCHI `UPDATE` ning MAZMUNI AHAMIYATSIZ — «har qanday» degan
    #    da'vo aynan shu bilan o'lchanadi. Faqat `declared_soum` ni sinash
    #    `status` ni qaytarish yo'lini ochiq qoldirardi.
    with pytest.raises(psycopg.errors.CheckViolation) as reverted:
        sync_owner_conn.execute(
            "UPDATE cashier_shifts SET status = %s WHERE id = %s",
            (ShiftStatus.OPEN.value, str(shift_id)),
        )
    assert reverted.value.sqlstate == CONDITIONAL


def test_an_open_shift_cannot_carry_a_declaration(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """SHARTLI QO'RIQCHINING CHEGARASI — DEKLARATSIYA FAQAT YOPILISH BILAN KELADI.

    =========================================================================
    ⚠⚠ BU TEST 06-05 NING S-B SABOTAJIDAN TUG'ILDI VA U DA'VONI
        KENGAYTIRILGAN HOLATGA KO'CHIRADI.

    `shift_declaration_immutable()` ning TO'RT shoxidan ikkitasi
    (`declared_soum` va `system_soum` qayta yozilishi) FAQAT
    `OLD.<ustun> IS NOT NULL` bo'lganda ishlaydi. `ck_cashier_shifts_
    closed_has_declaration` esa `(status = 'closed') = (declared_soum IS
    NOT NULL)` ni majburlaydi — ya'ni `declared_soum` to'lgan qator HAR
    DOIM `closed` va o'sha holatda BIRINCHI shox (`OLD.status =
    'closed'`) allaqachon rad etgan bo'ladi.

    Ya'ni D-25 ning kafolati IKKI MEXANIZMDAN keladi va ular
    ALMASHTIRILADIGAN emas, KETMA-KET:

        (a) YOPILGAN smenaga har qanday `UPDATE` rad etiladi (trigger);
        (b) OCHIQ smenaga deklaratsiya UMUMAN yozib bo'lmaydi (`CHECK`).

    Ikkinchisini o'lchamasdan «ko'r deklaratsiya qayta yozilmaydi» degan
    da'vo YARIM bo'lardi: kassir smenani yopmasdan turib summani
    kiritib, keyin uni erkin o'zgartira olardi va «ko'r» deklaratsiya
    tizim summasiga MOSLASHTIRILGAN bo'lardi.

    -------------------------------------------------------------------------
    ⛔ O'LCHOV (06-05, S-B) — SHOXLARNING QAYSI BIRI YUK KO'TARADI:

      * `shift_declaration_immutable()` dan `declared_soum` SHOXI olib
        tashlandi -> butun fayl YASHIL qoldi. Ya'ni o'sha shox
        YETIB BO'LMAYDIGAN: uning sharti (`OLD.declared_soum IS NOT
        NULL`) yuqoridagi `CHECK` tufayli `OLD.status = 'closed'` ni
        BILDIRADI va birinchi shox allaqachon rad etgan bo'ladi;
      * `OLD.status = 'closed'` SHOXI ham olib tashlanganda
        `test_a_shift_closes_once_and_never_reopens` DARHOL QIZARDI
        («DID NOT RAISE CheckViolation»).

    XULOSA: D-25 ni AMALDA `status` shoxi + juftlangan `CHECK` ushlab
    turadi; `declared_soum`/`system_soum` shoxlari CHUQURLIKDAGI
    HIMOYA. ⛔ Ular «o'lik kod» deb OLIB TASHLANMAYDI: `CHECK` bir kun
    bo'shatilsa (masalan ochiq smenaga oraliq deklaratsiya ruxsat
    etilsa) ular DARHOL yuk ko'taradigan bo'lib qoladi.
    =========================================================================
    """
    with pytest.raises(psycopg.errors.CheckViolation) as error:
        sync_owner_conn.execute(
            "UPDATE cashier_shifts SET declared_soum = 50000 WHERE id = %s",
            (str(env.live.open_shift_id),),
        )
    assert error.value.sqlstate == CONDITIONAL
    assert "closed_has_declaration" in str(error.value), (
        f"xato boshqa mexanizmdan keldi: {error.value!r} — bu holatni AYNAN "
        "`ck_cashier_shifts_closed_has_declaration` bloklashi kerak"
    )

    # NAZORAT: smena hamon OCHIQ va deklaratsiyasi BO'SH, ya'ni rad etish
    # qatorni o'zgartirmagan.
    row = sync_owner_conn.execute(
        "SELECT status, declared_soum FROM cashier_shifts WHERE id = %s",
        (str(env.live.open_shift_id),),
    ).fetchone()
    assert row is not None and (row[0], row[1]) == (ShiftStatus.OPEN.value, None)


def test_a_shift_cannot_be_deleted_on_a_live_market(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """Smenani o'chirish rad etiladi — variance yozuvi YO'Q QILINMAYDI (D-25 (d)).

    Smena o'chirilsa «kassirda qancha bo'lishi kerak edi?» savoliga javob
    beradigan yagona qator yo'qolardi va nomuvofiqlik hisoboti o'sha kun
    uchun BO'SH chiqardi — ya'ni nazoratning yo'qligi yaxshi natijaga
    o'xshab qolardi.
    """
    _assert_live(sync_owner_conn, env.market_id)

    with pytest.raises(psycopg.errors.CheckViolation) as error:
        sync_owner_conn.execute(
            "DELETE FROM cashier_shifts WHERE id = %s", (str(env.live.open_shift_id),)
        )
    assert error.value.sqlstate == CONDITIONAL
    assert "not deletable" in str(error.value)


def test_a_cashier_cannot_open_a_second_shift(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """Bir kassirda IKKINCHI ochiq smena -> `UniqueViolation` (D-27, T-06-29).

    =========================================================================
    POYGA DB'GA TOPSHIRILGAN, ILOVA MANTIG'IGA EMAS.

    Ikki oynadan bir vaqtda ochilgan smena — poyga holati va «avval
    tekshir, keyin yoz» ikkalasiga ham bo'sh holatni ko'rsatardi.
    O'shanda kassir to'lovlarni ikki smenaga bo'lib yozardi va variance
    HAR IKKALASIDA ham kichik ko'rinardi: nomuvofiqlik ikkiga bo'linib
    YO'QOLARDI.

    ⚠ NAZORAT SHU TESTNING ICHIDA: smena YOPILGANDAN keyin ikkinchisini
      ochish O'TISHI kerak. Usiz to'liq (qismansiz) `UNIQUE` indeks ham
      yashil ko'rinardi — holbuki u kassirning ERTANGI smenasini ham
      bloklardi va bozor ikkinchi kuni ishlamasdi.
    =========================================================================
    """
    with pytest.raises(psycopg.errors.UniqueViolation) as error:
        sync_owner_conn.execute(
            "INSERT INTO cashier_shifts (id, market_id, cashier_id) VALUES (%s, %s, %s)",
            (str(uuid4()), str(env.market_id), str(env.live.cashier_id)),
        )
    assert error.value.sqlstate == UNIQUE_VIOLATION
    assert "cashier_open" in str(error.value), (
        f"xato boshqa noyoblik konstraytidan keldi: {error.value!r}"
    )

    sync_owner_conn.execute(
        "UPDATE cashier_shifts SET status = %s, closed_at = now(), "
        "declared_soum = 0, system_soum = 0 WHERE id = %s",
        (ShiftStatus.CLOSED.value, str(env.live.open_shift_id)),
    )
    next_shift_id = uuid4()
    sync_owner_conn.execute(
        "INSERT INTO cashier_shifts (id, market_id, cashier_id) VALUES (%s, %s, %s)",
        (str(next_shift_id), str(env.market_id), str(env.live.cashier_id)),
    )
    assert (
        _rows(
            sync_owner_conn,
            "SELECT count(*) FROM cashier_shifts WHERE id = %s",
            (str(next_shift_id),),
        )
        == 1
    ), (
        "yopilgan smenadan keyin YANGISINI ochib bo'lmadi — indeks QISMAN "
        "emas, to'liq bo'lib qolgan va bozor ertaga ishlamasdi"
    )


# ===========================================================================
# 4. `audit_log` ASSIMETRIYASI — IKKI YO'NALISH, IKKALASI HAM MAJBURIY
# ===========================================================================


def test_the_audit_log_records_only_what_actually_happened(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """Rad etilgan `UPDATE` audit izini QOLDIRMAYDI; o'tgani QOLDIRADI (T-06-27).

    =========================================================================
    ⛔ IKKI YO'NALISH VA BITTASI YOLG'IZ O'ZI BO'SH DA'VO BO'LARDI.

    Faqat «rad etilgan urinish yozilmadi» ni o'lchash audit triggeri
    UMUMAN ishlamayotgan holatda ham yashil bo'lardi — ya'ni «kim nimani
    o'zgartirdi?» savoli abadiy javobsiz qolardi va biz buni sezmasdik.
    Faqat «o'tgan amal yozildi» ni o'lchash esa rad etilgan urinishning
    ham yozilishini o'tkazib yuborardi.

    MEXANIZM: Postgres `BEFORE` triggerni `AFTER` dan OLDIN yuritadi
    (`migrations/helpers.py:295-298`), ya'ni o'zgarmaslik qo'riqchisi rad
    etgan `UPDATE` audit triggerigacha umuman YETIB BORMAYDI. Aks holda
    jurnal HECH QACHON SODIR BO'LMAGAN o'zgarishlarni ko'rsatardi va
    kassirning smenasi «tahrirlangan» bo'lib ko'rinardi — audit dalilning
    O'ZINI shubhaga qo'yardi.
    =========================================================================
    """
    sync_owner_conn.execute(SET_MARKET, (str(env.market_id),))
    try:
        before = _rows(sync_owner_conn, AUDIT_COUNT, ("cashier_shifts",))
        assert before > 0, (
            "`cashier_shifts` uchun audit qatori umuman yo'q — seedning `INSERT` i "
            "auditga tushmagan, ya'ni bu test hech nimani o'lchamaydi"
        )

        # (1) RAD ETILGAN amal — yopilmagan smenaga deklaratsiya yozish.
        with pytest.raises(psycopg.errors.CheckViolation):
            sync_owner_conn.execute(
                "UPDATE cashier_shifts SET declared_soum = 1 WHERE id = %s",
                (str(env.live.open_shift_id),),
            )
        rejected = _rows(sync_owner_conn, AUDIT_COUNT, ("cashier_shifts",))
        assert rejected == before, (
            f"rad etilgan `UPDATE` dan keyin audit qatorlari {before} -> {rejected} "
            "bo'ldi — qo'riqchi `AFTER` bo'lib qolgan yoki audit triggeri undan "
            "OLDIN ishlagan"
        )

        # (2) O'TGAN amal — smenani yopish.
        sync_owner_conn.execute(
            "UPDATE cashier_shifts SET status = %s, closed_at = now(), "
            "declared_soum = 100000, system_soum = 100000 WHERE id = %s",
            (ShiftStatus.CLOSED.value, str(env.live.open_shift_id)),
        )
        accepted = _rows(sync_owner_conn, AUDIT_COUNT, ("cashier_shifts",))
        assert accepted == before + 1, (
            f"muvaffaqiyatli `open -> closed` dan keyin audit qatorlari "
            f"{before} -> {accepted} — `AUDITED_TABLES` ishlamayapti va "
            "smenaning yopilishi izsiz qolyapti"
        )
    finally:
        # Kontekst BO'SHATILADI: `conn` autocommit rejimida va qiymat
        # SESSIYA davomida saqlanadi — uni qoldirib ketish keyingi
        # fixture'ning tozalashini jimgina buzardi
        # (`two_markets._first_audit_row_id()` da o'lchangan tuzoq).
        sync_owner_conn.execute(SET_MARKET, ("",))


# ===========================================================================
# 5. `charge_adjustments` — D-07 NING IJOBIY YARMI
# ===========================================================================


def test_a_correction_is_a_new_row_and_it_is_audited(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """Tuzatish qatori O'TADI va `audit_log` da iz QOLDIRADI (D-07/D-19).

    =========================================================================
    ⛔ BU TEST 1-GURUHNI MA'NOLI QILADI.

    «Hisobni tahrirlab bo'lmaydi» degan da'vo yolg'iz o'zi mahsulotni
    ishlamaydigan qilardi: nazoratchi kechikkan javob berganda (yoki AI
    yolg'on musbat bergan kunda) summani tuzatishning YAGONA yo'li
    bo'lmasdi. Yo'l bor va u ALOHIDA QATOR: asl summa nizoda ko'rinib
    qoladi (D-02), yakuniy summa esa HISOBLANADIGAN ko'rinish.

    ⚠ `charge_adjustments` `AUDITED_TABLES` da — tuzatish INSONNING
      moliyaviy oqibatli qarori va «kim qaror qildi?» savoli javobsiz
      qolmasligi kerak.
    =========================================================================
    """
    charge_id = _charge(sync_owner_conn, env)
    sync_owner_conn.execute(SET_MARKET, (str(env.market_id),))
    try:
        before = _rows(sync_owner_conn, AUDIT_COUNT, ("charge_adjustments",))

        sync_owner_conn.execute(
            "INSERT INTO charge_adjustments "
            "(market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                str(env.market_id),
                str(charge_id),
                AdjustmentDirection.DECREASE.value,
                AdjustmentReason.LATE_REVIEW.value,
                5_000,
                str(env.live.cashier_id),
            ),
        )

        after = _rows(sync_owner_conn, AUDIT_COUNT, ("charge_adjustments",))
        assert after == before + 1, (
            f"tuzatish auditga tushmadi ({before} -> {after}) — «kim qaror "
            "qildi?» savoli javobsiz qoladi (D-02)"
        )
    finally:
        sync_owner_conn.execute(SET_MARKET, ("",))

    # ASL HISOB O'ZGARMAGAN: tuzatish uni TAHRIRLAMAYDI.
    row = sync_owner_conn.execute(
        "SELECT amount_soum FROM daily_charges WHERE id = %s", (str(charge_id),)
    ).fetchone()
    assert row is not None and row[0] == TARIFF_SOUM


def test_a_correction_cannot_be_negative_or_unnamed(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """Manfiy summa ham, reyestrdan tashqari sabab ham RAD ETILADI (C-5/D-19).

    =========================================================================
    IKKI MUSTAQIL DA'VO:

      * MANFIY SUMMA (C-5): belgili `bigint` da «-15000» ni yozgan odam
        «15000 qaytarildi» ni ham, «15000 kamaytirildi» ni ham nazarda
        tutgan bo'lishi mumkin va hisobot ikkalasini BIR GURUHGA
        qo'shardi. Yo'nalish ALOHIDA ustunda, summa esa MUSBAT KATTALIK.

      * REYESTRDAN TASHQARI SABAB (D-19): `AdjustmentReason` da `other`
        A'ZOSI YO'Q va bu ro'yxatning butun qiymati — bitta bo'sh maydon
        har qanday summa o'zgartirishini oqlab yuborardi va hisobotda
        «boshqa» AMALDA eng katta guruh bo'lib qolardi.
    =========================================================================
    """
    charge_id = _charge(sync_owner_conn, env)

    with pytest.raises(psycopg.errors.CheckViolation) as negative:
        sync_owner_conn.execute(
            "INSERT INTO charge_adjustments "
            "(market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                str(env.market_id),
                str(charge_id),
                AdjustmentDirection.DECREASE.value,
                AdjustmentReason.LATE_REVIEW.value,
                -5_000,
                str(env.live.cashier_id),
            ),
        )
    assert negative.value.sqlstate == CONDITIONAL
    assert "amount_soum_positive" in str(negative.value)

    with pytest.raises(psycopg.errors.CheckViolation) as unnamed:
        sync_owner_conn.execute(
            "INSERT INTO charge_adjustments "
            "(market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
            "VALUES (%s, %s, %s, 'not_a_real_reason', %s, %s)",
            (
                str(env.market_id),
                str(charge_id),
                AdjustmentDirection.DECREASE.value,
                5_000,
                str(env.live.cashier_id),
            ),
        )
    assert unnamed.value.sqlstate == CONDITIONAL
    assert "reason_code_allowed" in str(unnamed.value), (
        f"xato boshqa konstraytdan keldi: {unnamed.value!r}"
    )


# ===========================================================================
# 6. DALIL ZANJIRI — SEEDNING `day_close` VARIANTI USTIDA (BILL-02)
# ===========================================================================


async def test_the_evidence_chain_needs_materialised_slots(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> None:
    """Dalil qatori FAQAT materializatsiya qilingan slot ustida yoziladi (C-3/C-7).

    =========================================================================
    ⛔ BU TEST SEEDNING IKKINCHI VARIANTINI (`billing_domain`) O'LCHAYDI VA
       U ZARURAT, QULAYLIK EMAS.

    Qolgan beshta guruh `before_day_close` variantida yuguradi, ya'ni
    ular slot qatorlariga umuman tegmaydi. Agar `day_close` chaqiradigan
    variant BIRORTA testda ishlatilmasa, u shu rejadan SINALMAGAN holda
    chiqardi — va C-3 ning butun mexanizmi («slotlar mahsulot yo'lidan
    tug'iladi») faqat KELAJAKDAGI rejada birinchi marta yugurardi.

    O'lchanadigan zanjir (C-7):

        charge_evidence -> stall_slot_occupancy  (AUDIT havolasi)
                        -> occupancy_events      (MUZLATILGAN dalil)
                        -> snapshots             (kadrga yo'l, D-21 langari)

    Uchala nishon ham BIR XIL bozorga tegishli bo'lishi kompozit FK
    bilan majburlanadi, ya'ni «dalil boshqa bozorning kadriga ishora
    qilyapti» holati IFODALAB BO'LMAYDI.
    =========================================================================
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        async with billing_domain(
            sync_owner_conn, app_sessionmaker, two_markets, market_domain, occupancy
        ) as billing:
            live = billing.market_a
            assert slot_count(sync_owner_conn, live.market_id, SEED_BUSINESS_DATE) > 0, (
                "`day_close` birorta slot qatori yozmadi — dalil zanjiri langarsiz qolardi (C-3)"
            )

            stall_id = live.stall_with_one_ai_occupied_slot
            assert stall_id is not None
            charge_id, _ = add_daily_charge(
                sync_owner_conn,
                market_id=live.market_id,
                stall_id=stall_id,
                vendor_id=live.vendor_id,
                tariff_id=live.tariff_id,
            )

            evidence_id = add_charge_evidence(
                sync_owner_conn, market_id=live.market_id, charge_id=charge_id
            )
            assert evidence_id is not None, (
                "g'olib hodisali slot qatori topilmadi — `day_close` yugurgan, "
                "lekin birorta `occupied` slot yozmagan bo'lishi mumkin"
            )

            chain = sync_owner_conn.execute(
                "SELECT e.snapshot_id, s.is_billable, o.verdict "
                "FROM charge_evidence AS ev "
                "JOIN occupancy_events AS e ON e.id = ev.occupancy_event_id "
                "JOIN snapshots AS s ON s.id = ev.snapshot_id "
                "JOIN stall_slot_occupancy AS o ON o.id = ev.stall_slot_occupancy_id "
                "WHERE ev.id = %s",
                (str(evidence_id),),
            ).fetchone()
            assert chain is not None, "dalil zanjiri uzilgan — `JOIN` 0 qator qaytardi"
            assert chain[1] is True, (
                "dalil YAROQSIZ kadrga ishora qilyapti — D-21 langari ishlamayapti"
            )
            assert chain[2] == "occupied", (
                f"dalil `{chain[2]}` slotga bog'landi — hisobning dalili AYNAN "
                "band slot bo'lishi shart"
            )
