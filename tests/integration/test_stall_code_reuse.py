"""Rasta raqami va holati — SC#2 ning DB tomoni (MARKET-02, D-01/D-02).

=============================================================================
SC#2: «rasta holati o'zgarishlari auditda ko'rinadi — XOM SQL yo'lida ham —
va yopilgan rastaning raqami qayta ishlatilmaydi».

Ikkala yarmi ham bitta savolga xizmat qiladi: hisobotdagi «12-rasta» YILLAR
davomida BITTA jismoniy joyni anglatishi kerak. Aks holda nizoda ko'rsatilgan
dalil («12-rasta 40 kun to'lamagan») hech narsani isbotlamaydi — raqam o'sha
davrda ikki xil rastani bildirgan bo'lishi mumkin.

`UNIQUE(market_id, code)` bu kafolatni BERMAYDI: kod tahrirlangach eski
qiymat BO'SHAB QOLADI va yangi rastaga berilishi mumkin. Kafolat
`stall_code_registry` + `trg_stall_code_claim` juftligida (D-02).
=============================================================================

IKKI XIL RAD ETISH — IKKI XIL MEXANIZM, BIR XIL `sqlstate`:
  * `uq_stalls_market_id_code`  — kod AYNI PAYTDA band (D-01);
  * `trg_stall_code_claim`      — kod CHETLANGAN, boshqa rastaniki (D-02).
Ikkalasi ham `23505` beradi va bu ATAYIN: chaqiruvchi ularni BIR XIL yo'lda
`409` ga aylantiradi, ikkita alohida xato kodini ushlashi shart emas.
Testlar esa ularni xato MATNI bo'yicha ajratadi — shu bilan ikkinchisi
birinchisining ortiga yashirinib qololmaydi.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
import pytest
from fixtures import MarketScope
from fixtures.market_domain import MarketDomainSeed
from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.enums import StallStatus

INSERT_STALL = "INSERT INTO stalls (market_id, zone_id, code) VALUES (%s, %s, %s) RETURNING id"
UPDATE_CODE = "UPDATE stalls SET code = %s WHERE id = %s"
UPDATE_STATUS = "UPDATE stalls SET status = %s WHERE id = %s"
READ_CODE = "SELECT code FROM stalls WHERE id = %s"
READ_STATUS = "SELECT status FROM stalls WHERE id = %s"

AUDIT_ROWS = (
    "SELECT action, old_value, new_value, changed_keys FROM audit_log "
    "WHERE table_name = 'stalls' AND row_id = %s ORDER BY id"
)

# Seed'dagi kodlar: ("2", "10", "100", "7", "55", "3"). Quyidagilar BO'SH va
# ular ataylab shunday tanlangan — mavjud kod bilan to'qnashuv testning
# nima isbotlayotganini chalkashtirardi.
ORIGINAL_CODE = "12"
EDITED_CODE = "99"
DUPLICATE_CODE = "77"


def _one(conn: Connection[TupleRow], sql: str, params: tuple[Any, ...]) -> Any:
    row = conn.execute(sql, params).fetchone()
    assert row is not None, f"so'rov 0 qator qaytardi: {sql}"
    return row


def _new_stall(conn: Connection[TupleRow], market_id: UUID, zone_id: UUID, code: str) -> UUID:
    stall_id: UUID = _one(conn, INSERT_STALL, (market_id, zone_id, code))[0]
    return stall_id


# ===========================================================================
# D-02 — KOD TAHRIRLANADI, LEKIN QAYTA ISHLATILMAYDI
# ===========================================================================


def test_code_edit_is_allowed_and_audited(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Rasta raqamini tahrirlash MUMKIN va u auditda old->new bilan ko'rinadi (SC#2).

    Tahrirlash yo'li ochiq bo'lishi SHART: import yoki qo'lda kiritishdagi
    xato («12» o'rniga «1 2») aks holda abadiy qolib ketardi. Lekin har bir
    o'zgarish iz qoldirishi kerak — raqam hisobotdagi dalilning kaliti, va
    uni jimgina almashtirish o'sha dalilni bekor qiladi.

    `code_sort` ham `changed_keys` ga tushishi KUTILADI (u generated ustun
    va koddan hosil bo'ladi) — shuning uchun tekshiruv `code` ning
    BORLIGINI talab qiladi, ro'yxatning aynan bir elementli bo'lishini emas.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        stall_id = _new_stall(conn, a.market_id, a.zone_ids[0], ORIGINAL_CODE)
        conn.execute(UPDATE_CODE, (EDITED_CODE, stall_id))

        assert _one(conn, READ_CODE, (stall_id,))[0] == EDITED_CODE, (
            "kod tahrirlanmadi — import xatosini tuzatish yo'li yopiq"
        )
        rows = conn.execute(AUDIT_ROWS, (stall_id,)).fetchall()

    updates = [row for row in rows if row[0] == "update"]
    assert len(updates) == 1, (
        f"kod o'zgarishi uchun {len(updates)} audit qatori topildi — kutilgan 1 (SC#2)"
    )

    _action, old_value, new_value, changed_keys = updates[0]
    assert changed_keys is not None and "code" in changed_keys, (
        f"`changed_keys` da `code` yo'q: {changed_keys}"
    )
    assert old_value is not None and new_value is not None
    assert (old_value["code"], new_value["code"]) == (ORIGINAL_CODE, EDITED_CODE), (
        f"auditdagi farq {old_value['code']} -> {new_value['code']}, kutilgan "
        f"{ORIGINAL_CODE} -> {EDITED_CODE}"
    )


def test_retired_code_cannot_be_reused_by_a_new_stall(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """Bo'shab qolgan kodni YANGI rastaga berib bo'lmaydi (D-02, T-02-49).

    Bu testning butun ma'nosi shundaki, `UNIQUE(market_id, code)` bu
    holatda HECH NARSA DEMAYDI: kod tahrirlangandan keyin «12» qiymati
    `stalls` da umuman yo'q, ya'ni unikalik konstrayti yangi qatorni bemalol
    o'tkazib yuborardi. Rad etish `stall_code_registry` dagi tarixiy
    qatordan keladi.

    Xato MATNI ham tekshiriladi (`stall code`): usiz test kod aslida hali
    ham band bo'lgan holatdan — ya'ni oddiy unikalik buzilishidan —
    farq qilmasdi va D-02 mexanizmi umuman ishlamaganda ham yashil bo'lardi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        stall_id = _new_stall(conn, a.market_id, a.zone_ids[0], ORIGINAL_CODE)
        conn.execute(UPDATE_CODE, (EDITED_CODE, stall_id))

        with pytest.raises(psycopg.errors.UniqueViolation) as excinfo:
            conn.execute(INSERT_STALL, (a.market_id, a.zone_ids[0], ORIGINAL_CODE))

    assert excinfo.value.sqlstate == "23505", (
        f"chetlangan kod `{excinfo.value.sqlstate}` bilan rad etildi — chaqiruvchi uni "
        "oddiy 'kod band' holati bilan bir xil yo'lda `409` ga aylantira olmaydi"
    )
    assert "stall code" in str(excinfo.value), (
        f"rad etish REYESTR triggeridan kelmadi: {excinfo.value}. Xabar `uq_stalls_...` "
        "bo'lsa demak kod hali ham `stalls` da band va test D-02 ni sinamayapti"
    )


def test_stall_can_reclaim_its_own_code(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """NAZORAT HOLATI: rasta O'Z eski kodini qaytarib olishi MUMKIN.

    Usiz yuqoridagi kafolat «kodni umuman tahrirlab bo'lmaydi» ga aylanib
    ketardi: reyestrga qator tushgach HAR QANDAY qaytish bloklanardi va
    noto'g'ri tuzatishni BEKOR QILISH imkonsiz bo'lardi. Reyestrda
    `stall_id` saqlanishining sababi ham aynan shu — u «kod band» emas,
    «kod KIMNIKI» savoliga javob beradi.
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        stall_id = _new_stall(conn, a.market_id, a.zone_ids[0], ORIGINAL_CODE)
        conn.execute(UPDATE_CODE, (EDITED_CODE, stall_id))
        conn.execute(UPDATE_CODE, (ORIGINAL_CODE, stall_id))

        code = _one(conn, READ_CODE, (stall_id,))[0]

    assert code == ORIGINAL_CODE, (
        f"rasta o'z kodiga qayta olmadi (hozirgi kod `{code}`) — tuzatishni bekor qilish "
        "yo'li yopilgan va D-02 kafolati kutilganidan KENG qamrayapti"
    )


def test_code_is_unique_within_market(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """AYNI paytda ikki rastada bir xil kod bo'lishi mumkin emas (D-01).

    D-02 dan MUSTAQIL qatlam: bu yerda kod hali BAND, ya'ni rad etish
    `uq_stalls_market_id_code` dan keladi. Ikkala qatlam ham kerak —
    biri "hozir band", ikkinchisi "avval ishlatilgan".
    """
    a = market_domain.market_a

    with market_scope(a.market_id) as conn:
        _new_stall(conn, a.market_id, a.zone_ids[0], DUPLICATE_CODE)

        with pytest.raises(psycopg.errors.UniqueViolation) as excinfo:
            conn.execute(INSERT_STALL, (a.market_id, a.zone_ids[0], DUPLICATE_CODE))

    assert excinfo.value.sqlstate == "23505"
    assert "uq_stalls_market_id_code" in str(excinfo.value), (
        f"band kod REYESTR triggeri bilan rad etildi: {excinfo.value}. Ikki qatlam "
        "aralashib ketgan — unikalik konstrayti yo'qolgan bo'lishi mumkin"
    )


def test_same_code_in_another_market_is_accepted(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """NAZORAT HOLATI: AYNI kod BOSHQA bozorda qabul qilinadi (D-01).

    D-01 «raqam BOZOR bo'yicha yagona» deydi, «platforma bo'yicha» emas.
    Har bozorda «12-rasta» bor va bo'lishi ham kerak — global unikalik
    ikkinchi bozorni ro'yxatga olishni imkonsiz qilardi (multi-tenant
    da'vosining o'zi buzilardi).

    Kod IKKALA bozorda ham yaratiladi: yolg'iz B bozoridagi INSERT hech
    nimani isbotlamasdi, chunki kod A da band bo'lmasa nizo ham yo'q.
    """
    a = market_domain.market_a
    b = market_domain.market_b

    with market_scope(a.market_id) as conn:
        in_a = _new_stall(conn, a.market_id, a.zone_ids[0], ORIGINAL_CODE)

    with market_scope(b.market_id) as conn:
        in_b = _new_stall(conn, b.market_id, b.zone_ids[0], ORIGINAL_CODE)
        code_in_b = _one(conn, READ_CODE, (in_b,))[0]

    assert in_a != in_b
    assert code_in_b == ORIGINAL_CODE, (
        "B bozorida A bilan bir xil kod yaratib bo'lmadi — unikalik yoki kod reyestri "
        "GLOBAL bo'lib qolgan va ikkinchi bozor o'z raqamlarini ishlata olmaydi (D-01)"
    )


# ===========================================================================
# SC#2 — HOLAT O'ZGARISHLARI AUDITDA, XOM SQL YO'LIDA HAM
# ===========================================================================


def test_raw_sql_update_is_audited(
    sync_owner_conn: Connection[TupleRow],
    market_scope: MarketScope,
    market_domain: MarketDomainSeed,
) -> None:
    """`sbozor_owner` bilan qilingan xom `UPDATE` ham audit qatorini hosil qiladi.

    ⚠ ORM UMUMAN ISHLATILMAYDI va rol ATAYIN EGA. Bu 1-fazadagi D-10
    falsafasining 2-fazadagi tekshiruvi: `before_flush` kabi ORM hook'i
    xom `UPDATE` ni, bulk operatsiyani va migratsiyani KO'RMAYDI — ya'ni
    aynan texnik savodli insider ishlatadigan yo'llarni. Audit DB-trigger
    bilan yozilgani uchun bu yo'l ham qamraladi.

    Amal ATAYIN `status = 'closed'`: rastani "yopiq" deb belgilash uning
    kunlik hisobini butunlay to'xtatadi (A4), ya'ni bu tushumni jimgina
    kamaytirishning eng arzon yo'li.
    """
    a = market_domain.market_a
    stall_id = a.stall_ids[0]

    sync_owner_conn.execute(UPDATE_STATUS, (StallStatus.CLOSED.value, stall_id))

    with market_scope(a.market_id) as conn:
        assert _one(conn, READ_STATUS, (stall_id,))[0] == StallStatus.CLOSED.value
        rows = conn.execute(AUDIT_ROWS, (stall_id,)).fetchall()

    updates = [row for row in rows if row[0] == "update"]
    assert len(updates) == 1, (
        f"xom SQL orqali qilingan o'zgarish uchun {len(updates)} audit qatori topildi — "
        "kutilgan 1. Auditsiz qolgan yo'l — insider uchun ochiq qolgan yo'l (D-10)"
    )

    _action, old_value, new_value, changed_keys = updates[0]
    assert changed_keys == ["status"], (
        f"`changed_keys` = {changed_keys} — xom SQL faqat `status` ga tegdi, boshqa "
        "ustunlar ro'yxatga tushmasligi kerak"
    )
    assert old_value is not None and new_value is not None
    assert (old_value["status"], new_value["status"]) == (
        StallStatus.ACTIVE.value,
        StallStatus.CLOSED.value,
    )


def test_status_transition_is_audited(
    market_scope: MarketScope, market_domain: MarketDomainSeed
) -> None:
    """`active -> maintenance -> closed` zanjirining HAR QADAMI auditda (SC#2).

    Uchta yozuv kutiladi va ular rastaning uchta holatiga mos keladi:
    yaratilish (`insert`, `active`) va ikkita o'tish (`update`). Faqat
    OXIRGI holatni saqlaydigan jurnal («hozir yopiq») nizoda foydasiz —
    savol har doim «QACHON va KIM yopdi?» bo'ladi.

    Har bir `update` da `status` ning `changed_keys` da bo'lishi ham
    tekshiriladi: `to_jsonb` diff'i buzilsa jurnal «qator o'zgardi» deb
    yozardi-yu, NIMA o'zgarganini ko'rsatmasdi.
    """
    a = market_domain.market_a
    transitions = (StallStatus.MAINTENANCE.value, StallStatus.CLOSED.value)

    with market_scope(a.market_id) as conn:
        stall_id = _new_stall(conn, a.market_id, a.zone_ids[0], ORIGINAL_CODE)
        for status in transitions:
            conn.execute(UPDATE_STATUS, (status, stall_id))
        rows = conn.execute(AUDIT_ROWS, (stall_id,)).fetchall()

    assert [row[0] for row in rows] == ["insert", "update", "update"], (
        f"audit zanjiri {[row[0] for row in rows]} — kutilgan ['insert', 'update', "
        "'update']. Holat tarixi to'liq bo'lmasa 'qachon yopildi' savoli javobsiz qoladi"
    )

    expected_pairs = (
        (StallStatus.ACTIVE.value, StallStatus.MAINTENANCE.value),
        (StallStatus.MAINTENANCE.value, StallStatus.CLOSED.value),
    )
    for (_action, old_value, new_value, changed_keys), expected in zip(
        rows[1:], expected_pairs, strict=True
    ):
        assert changed_keys is not None and "status" in changed_keys, (
            f"`changed_keys` da `status` yo'q: {changed_keys}"
        )
        assert old_value is not None and new_value is not None
        assert (old_value["status"], new_value["status"]) == expected, (
            f"auditdagi o'tish {old_value['status']} -> {new_value['status']}, "
            f"kutilgan {expected[0]} -> {expected[1]}"
        )
