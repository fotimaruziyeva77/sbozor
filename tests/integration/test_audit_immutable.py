"""`audit_log` o'zgarmasligining TO'RT QATLAMI — holat bo'yicha isbot.

=============================================================================
DIQQAT — BU FAYLNI "SODDALASHTIRMANG" (RESEARCH Pitfall 9, empirik):

Jadval EGASIGA (`sbozor_owner`) qarshi `UPDATE` va `DELETE` **XATO
TASHLAMAYDI**. Ular jimgina `UPDATE 0` / `DELETE 0` qaytaradi, chunki
`audit_log` da UPDATE/DELETE uchun policy YO'Q va FORCE ostida ega ham
policy'ga bo'ysunadi — ya'ni komanda hech qanday qatorni KO'RMAYDI.

Shuning uchun egaga qarshi testlar `pytest.raises` BILAN YOZILMAYDI. Ular
urinishdan OLDIN va KEYIN holatni (qator soni + `action` qiymatlari)
o'lchaydi va o'zgarmaganini tasdiqlaydi. `pytest.raises` bilan yozilgan
variant AVVAL yiqilardi, keyin esa kimdir uni "tuzatib" himoyani yo'q
qilardi.

`pytest.raises` FAQAT ikki holatda ishlatiladi:
  * app-rol urinishlari  -> 1-qatlam `permission denied` beradi (BALAND OVOZ);
  * `TRUNCATE`           -> 4-qatlam triggeri exception ko'taradi.
=============================================================================

Qatorlar qayerdan: `two_markets` seed'i a'zolik qatorlarini yozganda audit
triggeri har bozor uchun uchtadan qator qo'yadi. Ya'ni hujum qilinadigan
ma'lumot testga tayyor holda keladi.
"""

from __future__ import annotations

import psycopg
import pytest
from fixtures.two_markets import TwoMarketSeed
from psycopg import Connection
from psycopg.rows import TupleRow

TAMPERED = "tampered"

SET_MARKET = "SELECT set_config('app.market_id', %s, false)"
SNAPSHOT = "SELECT id, action, table_name FROM audit_log ORDER BY id"

# Hujum operatorlari — ATAYIN `WHERE` siz: eng agressiv shakl sinaladi.
# Matn LITERAL yozilgan (f-string EMAS): hujum operatori nima qilishini
# o'qiyotgan odam boshqa joyga qaramasdan ko'rishi kerak, va f-string bu
# yerda ruff `S608` ni ham keltirib chiqarardi.
TAMPER_UPDATE = "UPDATE audit_log SET action = 'tampered'"
TAMPER_DELETE = "DELETE FROM audit_log"
TAMPER_TRUNCATE = "TRUNCATE audit_log"


def _snapshot(conn: Connection[TupleRow]) -> list[tuple[object, ...]]:
    """Ko'rinadigan audit qatorlarining to'liq holati."""
    return [tuple(row) for row in conn.execute(SNAPSHOT).fetchall()]


def _with_market(conn: Connection[TupleRow], seed: TwoMarketSeed) -> list[tuple[object, ...]]:
    """A bozori kontekstini o'rnatadi va boshlang'ich holatni qaytaradi.

    Kontekst KERAK: `audit_read` policy'si tenant-scoped va u jadval egasiga
    ham qo'llanadi (FORCE). Kontekstsiz snapshot bo'sh bo'lar edi va test
    "hech narsa o'zgarmadi" degan bo'sh da'voni isbotlagan bo'lardi.
    """
    conn.execute(SET_MARKET, (str(seed.market_a.id),))
    before = _snapshot(conn)
    assert before, (
        "audit_log bo'sh — seed audit qatorlarini yaratmagan; bu testlar hech narsani isbotlamaydi"
    )
    return before


# ===========================================================================
# 1-QATLAM: huquqlar — ilova roli va SQL injection'ga qarshi (BALAND OVOZDA)
# ===========================================================================


def test_app_role_cannot_update_audit_log(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """`sbozor_app` bilan `UPDATE audit_log` -> `permission denied` (T-01-30)."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as excinfo:
        sync_app_conn.execute(TAMPER_UPDATE)

    assert "audit_log" in str(excinfo.value)


def test_app_role_cannot_delete_audit_log(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """`sbozor_app` bilan `DELETE FROM audit_log` -> `permission denied` (T-01-30)."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as excinfo:
        sync_app_conn.execute(TAMPER_DELETE)

    assert "audit_log" in str(excinfo.value)


def test_app_role_cannot_truncate_audit_log(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """`sbozor_app` bilan `TRUNCATE` -> huquq tekshiruvi triggerdan OLDIN (T-01-32).

    Ilova roli uchun 4-qatlamgacha ish yetib bormaydi: `TRUNCATE` huquqi
    umuman berilmagan. 4-qatlam aynan EGAGA qarshi kerak.
    """
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as excinfo:
        sync_app_conn.execute(TAMPER_TRUNCATE)

    assert "audit_log" in str(excinfo.value)


# ===========================================================================
# 2- va 3-QATLAM: jadval egasiga qarshi — JIMGINA (holat bo'yicha tekshiruv)
# ===========================================================================


def test_owner_update_changes_nothing(
    sync_owner_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """Ega `UPDATE` qila olmaydi — va bu XATOSIZ sodir bo'ladi (Pitfall 9).

    Istisno kutuvchi kontekst-menejer bu yerda ATAYIN ISHLATILMAGAN: UPDATE
    uchun policy yo'q, ya'ni komanda 0 qator ko'radi va MUVAFFAQIYATLI
    tugaydi. Yagona to'g'ri verifikatsiya — HOLATNI o'lchash. Fayl
    docstringida sabab batafsil yozilgan.
    """
    before = _with_market(sync_owner_conn, two_markets)

    cursor = sync_owner_conn.execute(TAMPER_UPDATE)

    assert cursor.rowcount == 0, (
        f"ega {cursor.rowcount} ta audit qatoriga tegdi — o'zgarmaslikning "
        "2-qatlami buzilgan (UPDATE uchun policy paydo bo'lgan bo'lishi mumkin)"
    )
    after = _snapshot(sync_owner_conn)
    assert after == before, "audit_log holati o'zgardi — jurnal endi ishonchsiz"
    assert all(row[1] != TAMPERED for row in after)


def test_owner_delete_changes_nothing(
    sync_owner_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """Ega `DELETE` qila olmaydi — bu ham XATOSIZ va jimgina."""
    before = _with_market(sync_owner_conn, two_markets)

    cursor = sync_owner_conn.execute(TAMPER_DELETE)

    assert cursor.rowcount == 0, (
        f"ega {cursor.rowcount} ta audit qatorini o'chirdi — jurnal o'zgarmas emas"
    )
    assert _snapshot(sync_owner_conn) == before


# ===========================================================================
# 4-QATLAM: TRUNCATE — RLS unga UMUMAN qo'llanmaydi, shuning uchun trigger
# ===========================================================================


def test_owner_truncate_is_rejected_and_changes_nothing(
    sync_owner_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """`TRUNCATE` egaga qarshi ham exception bilan rad etiladi (T-01-32).

    Bu qatlam ALOHIDA kerak: 2-qatlam (RLS) `TRUNCATE` ni to'xtatmaydi,
    chunki row-level security qator darajasida ishlaydi, `TRUNCATE` esa
    butun jadvalni bir operatsiyada bo'shatadi.
    """
    before = _with_market(sync_owner_conn, two_markets)

    with pytest.raises(psycopg.errors.RaiseException) as excinfo:
        sync_owner_conn.execute(TAMPER_TRUNCATE)

    assert "append-only" in str(excinfo.value)
    assert "TRUNCATE" in str(excinfo.value)
    assert _snapshot(sync_owner_conn) == before


# ===========================================================================
# Triggerni butunlay o'chirib chetlab o'tish yo'li (T-01-33)
# ===========================================================================


def test_app_cannot_bypass_trigger_via_replication_role(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """`session_replication_role = replica` — audit'ni o'chirishning eng qisqa yo'li.

    Bu sozlama butun sessiya uchun BARCHA triggerlarni (audit triggeri ham)
    o'chiradi, ya'ni undan keyingi har qanday o'zgarish izsiz qolardi.
    Uni o'zgartirish `SUPERUSER` yoki aniq berilgan huquq talab qiladi —
    `sbozor_app` da ikkalasi ham yo'q.
    """
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as excinfo:
        sync_app_conn.execute("SET session_replication_role = replica")

    assert "session_replication_role" in str(excinfo.value)

    row = sync_app_conn.execute("SHOW session_replication_role").fetchone()
    assert row is not None
    assert row[0] == "origin", "sozlama o'zgarib ketdi — triggerlar o'chirilgan holatda"
