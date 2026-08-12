"""D-26 ning uch shoxi va `/internal/bot/*` ning tor yuzasi (BOT-01/BOT-02).

=============================================================================
⛔⛔ D-26(b) IKKI BOZORLI SEED BILAN O'LCHANADI — VA BU SHART, QULAYLIK EMAS.

`uq_vendors_market_id_phone_e164` bir bozor ICHIDA ko'p moslikni IMKONSIZ
qiladi. Ya'ni bitta bozorli seed bilan yozilgan «bir nechta moslik» testi
YASHIL bo'lib turadi va HECH NIMANI o'lchamaydi (Pitfall 10): `resolve()`
umuman ishlamay qolgan taqdirda ham u yashil qolardi.

Shuning uchun bu fayl `fixtures/notification_domain.py::
seed_same_phone_in_two_markets()` dan foydalanadi — o'sha funksiya O'Z-O'ZINI
tekshiradi (2 qator, ikki xil bozor, teng telefon) va u 07-04 da AYNAN shu
shox uchun qurilgan.

⛔ NAZORAT O'LCHOVI MAJBURIY: o'sha seedda sotuvchilardan BITTASI
o'chirilganda AYNI telefon `BOUND` beradi. Usiz yuqoridagi test «ko'p
moslik» ni emas, UMUMIY nosozlikni (masalan `resolve()` har doim
`MULTIPLE_MATCHES` qaytarishini) o'lchagan bo'lardi.
=============================================================================

=============================================================================
⛔ ANOMALIYA HAQIQIY QATOR BILAN O'LCHANADI (T-07-44a).

«`MULTIPLE_MATCHES` qaytdi» degan da'vo YETARLI EMAS: reyestr nuqsoni
adminga YETIB BORISHI kerak. `_upsert()` esa `ALERT_META[key]` ustida
ishlaydi — ro'yxatga olinmagan kalit `KeyError` beradi va (xato yutilsa)
anomaliya JIMGINA yo'qolardi. Shuning uchun bu yerda `alert_events`
jadvalidagi HAQIQIY qatorlar sanaladi va ular IKKALA bozorda ham talab
qilinadi.
=============================================================================
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.jobs.alerting import ALERT_META
from app.repositories import binding_repo
from app.repositories.binding_repo import (
    VENDOR_BINDING_CONFLICT_ALERT_KEY,
    PendingVendor,
    ResolveOutcome,
    ResolveStatus,
    active_bindings,
    resolve,
)
from fixtures.notification_domain import (
    cleanup_same_phone_in_two_markets,
    seed_same_phone_in_two_markets,
)
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fixtures import TenantSessionFactory
    from fixtures.notification_domain import TwoMarketPhoneSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

BINDING_REPO_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "core-api"
    / "app"
    / "repositories"
    / "binding_repo.py"
)

TELEGRAM_ID_A = 7_610_000_001
"""⛔ `2**31` DAN KATTA — `DEFAULT_TELEGRAM_USER_ID` bilan bir xil sabab."""

TELEGRAM_ID_B = 7_610_000_002


# ---------------------------------------------------------------------------
# Fixture'lar
# ---------------------------------------------------------------------------


@pytest.fixture
def phone_seed(sync_owner_conn: Connection[TupleRow]) -> Iterator[TwoMarketPhoneSeed]:
    """D-26(b) ning YAGONA bajariladigan kirish holati (fayl docstringi)."""
    seed = seed_same_phone_in_two_markets(sync_owner_conn)
    try:
        yield seed
    finally:
        sync_owner_conn.execute(
            "DELETE FROM alert_events WHERE market_id = ANY(%s::uuid[])",
            ([str(market_id) for market_id in seed.market_ids],),
        )
        sync_owner_conn.execute(
            "DELETE FROM vendor_telegram_bindings WHERE market_id = ANY(%s::uuid[])",
            ([str(market_id) for market_id in seed.market_ids],),
        )
        # ⛔ `audit_log` TOZALANMAYDI va bu ATAYIN: jurnal append-only
        #   (`test_audit_immutable.py`) va `cleanup_two_markets()` ham
        #   unga tegmaydi. Har test YANGI bozor identifikatorlarini oladi,
        #   ya'ni sanoqlar baribir ajratilgan.
        cleanup_same_phone_in_two_markets(sync_owner_conn, seed)


def _binding_rows(conn: Connection[TupleRow], seed: TwoMarketPhoneSeed) -> list[tuple[Any, ...]]:
    return conn.execute(
        "SELECT market_id, vendor_id, telegram_user_id, revoked_at, revoked_reason "
        "FROM vendor_telegram_bindings WHERE market_id = ANY(%s::uuid[]) ORDER BY created_at",
        ([str(market_id) for market_id in seed.market_ids],),
    ).fetchall()


def _conflict_markets(conn: Connection[TupleRow], seed: TwoMarketPhoneSeed) -> set[UUID]:
    rows = conn.execute(
        "SELECT market_id FROM alert_events WHERE alert_key = %s AND market_id = ANY(%s::uuid[])",
        (
            VENDOR_BINDING_CONFLICT_ALERT_KEY,
            [str(market_id) for market_id in seed.market_ids],
        ),
    ).fetchall()
    return {UUID(str(row[0])) for row in rows}


def _drop_second_vendor(conn: Connection[TupleRow], seed: TwoMarketPhoneSeed) -> None:
    """NAZORAT HOLATI: telefonni AYNAN BITTA bozorda qoldiradi (fayl docstringi)."""
    conn.execute("DELETE FROM vendors WHERE id = %s", (str(seed.vendor_b_id),))


async def _binding_audit_count(tenant_session: TenantSessionFactory, market_id: UUID) -> int:
    """`vendor_telegram_bindings` ustidagi audit qatorlari — ILOVA roli bilan.

    ⛔ `sync_owner_conn` BILAN O'QILMAYDI: `audit_read` policy'si `sbozor_app`
       ga va TENANT KONTEKSTIGA bog'langan, ega roli esa `audit_log` da
       hech nima ko'rmaydi. Ega bilan yozilgan sanoq HAR DOIM 0 berardi va
       «audit yozildi» da'vosi jimgina bo'sh-rost bo'lib qolardi
       (`fixtures/auth_api.py::audit_rows` ning aynan o'sha qarori).
    """
    async with tenant_session(market_id) as session:
        found = await session.execute(
            text(
                "SELECT count(*) FROM audit_log "
                "WHERE market_id = :market_id AND table_name = :table_name"
            ),
            {"market_id": market_id, "table_name": "vendor_telegram_bindings"},
        )
        return int(found.scalar_one())


# ---------------------------------------------------------------------------
# Shakl darvozalari — ular BAZAGA UMUMAN TEGMAYDI
# ---------------------------------------------------------------------------


def test_resolve_status_is_a_closed_set_of_three() -> None:
    """⛔ D-26 ning uch shoxi NOMLANGAN va to'rtinchi a'zo YO'Q.

    To'rtinchi a'zo («noaniq», «xato») shoxni NOMSIZ qoldirardi va
    chaqiruvchi uni jimgina `no_match` bilan bir xil ko'rsatardi.
    """
    assert {member.value for member in ResolveStatus} == {
        "bound",
        "no_match",
        "multiple_matches",
    }


def test_resolve_outcome_carries_no_phone_field() -> None:
    """⛔ `ResolveOutcome` DA TELEFON MAYDONI YO'Q (T-07-41).

    Javob bot-service ga uzatiladi va u yerdan jurnalga tushishi mumkin —
    ya'ni maydon MAVJUD bo'lsa u ertami-kechmi log'ga chiqardi. Yo'q
    maydon sizib chiqa olmaydi.
    """
    names = {field.name for field in dataclasses.fields(ResolveOutcome)}

    assert names == {"status", "vendor"}, names
    assert not names & {"phone", "phone_e164", "raw_phone"}


def test_pending_vendor_response_has_no_personal_fields() -> None:
    """⛔ D-05: `PERSONAL_ROUTES` o'smasligi uchun MAYDONNING O'ZI bo'lmasligi kerak.

    `tests/tenancy/test_personal_data_coverage.py::PERSONAL_FIELDS` aynan
    `vendor_name` / `phone` / `full_name` nomlarini qidiradi. Ularni
    dataklassdan chiqarish darvozani «istisno» bilan emas, STRUKTURA
    bilan yopadi.
    """
    names = {field.name for field in dataclasses.fields(PendingVendor)}

    assert names == {"vendor_id", "stall_codes"}, names


def test_the_conflict_alert_key_is_registered_in_alert_meta() -> None:
    """⛔⛔ T-07-44a — RO'YXATGA OLINMAGAN KALIT `_upsert()` DA `KeyError` BERADI.

    Kalitni keyingi rejaga qoldirish ikki natijadan BIRINI berardi:
    yiqilgan `resolve()` yoki JIMGINA yo'qolgan anomaliya. Ikkinchisi
    aynan D-26(b) oldini olmoqchi bo'lgan nosozlik.
    """
    assert VENDOR_BINDING_CONFLICT_ALERT_KEY in ALERT_META

    meta = ALERT_META[VENDOR_BINDING_CONFLICT_ALERT_KEY]
    assert meta.severity == "warning"
    assert meta.never_suppressed is False
    assert meta.platform_scoped is False
    assert meta.storable is True


def test_the_conflict_key_is_not_a_platform_heartbeat_signal() -> None:
    """⛔ ONGLI RAD ETISH: kalit `_platform_signals` ga QO'SHILMAYDI.

    `_platform_signals::watched` — YURAK URISHI ESKIRISHI signallari
    uchun (zaxira, retention, patta yopilishi). Bu kalit esa HODISA bilan
    tug'iladi, YO'QLIK bilan emas: supurgi uni qayta topa olmaydi, chunki
    moslik telefon bilan qidirilgan va hech qayerda saqlanmagan.

    Sabab shu yerda YOZILADI, aks holda keyingi reja uni «unutilgan» deb
    o'qib, supurgiga qo'shib qo'yardi.
    """
    from app.jobs import alerting

    assert VENDOR_BINDING_CONFLICT_ALERT_KEY not in inspect.getsource(alerting._platform_signals)


def test_binding_repo_adds_no_rls_bypassing_surface() -> None:
    """⛔ G7-7 — yangi `SECURITY DEFINER` yuzasi YO'Q (T-07-43).

    Modul `active_market_ids()` ni IMPORT QILADI (yagona chetlab o'tuvchi
    yuza) va o'ziga `auth_list_markets_full()` chaqiruvini ham, yangi
    `SECURITY DEFINER` ta'rifini ham QO'SHMAYDI.
    """
    source = BINDING_REPO_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(BINDING_REPO_SOURCE))

    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "app.jobs.retention"
        for alias in node.names
    }
    assert "active_market_ids" in imported, imported

    # Matn darajasidagi taqiq — izohda ham, kodda ham bo'lmasligi kerak:
    # bu ikkita nom modulning MAVZUSI emas, ya'ni ularni «tushuntirish»
    # uchun yozish ham kerak emas (03-07 darsi teskari yo'nalishda
    # qo'llanmaydi).
    for banned in ("auth_list_markets_full", "SECURITY DEFINER"):
        assert banned not in source, f"`binding_repo` da taqiqlangan nom: {banned}"


def test_resolve_never_breaks_out_of_the_market_loop() -> None:
    """⛔ TAYM-ORACLE: `resolve()` ning tsiklida `break` YO'Q (T-07-40).

    Erta chiqish javob VAQTINI mosliknning bor-yo'qligiga bog'lardi va
    neytral javob ma'nosini yo'qotardi: raqamlarni ketma-ket sinab,
    bozorda kim savdo qilishini TAYMINGDAN o'qish mumkin bo'lardi.

    ⚠ AST, GREP EMAS: `break` so'zi izohda yoki satr ichida uchrasa sodda
      grep uni JAZOLARDI va yagona «tuzatish» yo'li sababni o'chirish
      bo'lardi (03-07 / G7-8 darsi).
    """
    tree = ast.parse(BINDING_REPO_SOURCE.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
    }

    assert "resolve" in functions, sorted(functions)
    breaks = [node for node in ast.walk(functions["resolve"]) if isinstance(node, ast.Break)]

    assert not breaks, (
        "`resolve()` ichida `break` topildi — moslik topilganda tsikl erta "
        "tugaydi va javob vaqti reyestr haqida ma'lumot beradi (T-07-40)."
    )


# ---------------------------------------------------------------------------
# D-26(b) — BIR NECHTA MOSLIK, IKKI BOZORLI SEED USTIDA
# ---------------------------------------------------------------------------


async def test_resolve_reports_multiple_matches_and_writes_no_binding(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ D-26(b): bog'lanish YOZILMAYDI va «birinchisi» tanlanmaydi (T-07-44)."""
    outcome = await resolve(
        app_sessionmaker,
        raw_phone=phone_seed.phone_e164,
        telegram_user_id=TELEGRAM_ID_A,
    )

    assert outcome.status is ResolveStatus.MULTIPLE_MATCHES
    assert outcome.vendor is None
    assert _binding_rows(sync_owner_conn, phone_seed) == []


async def test_multiple_matches_writes_a_real_alert_row_in_both_markets(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ T-07-44a — anomaliya IKKALA bozorda ham HAQIQIY qator bo'lib yoziladi.

    `platform_scoped=False` qarorining bevosita o'lchovi: to'qnashuv
    ikkala reyestrga tegishli va har bozor direktori O'Z qatorini
    ko'rishi kerak.
    """
    await resolve(
        app_sessionmaker,
        raw_phone=phone_seed.phone_e164,
        telegram_user_id=TELEGRAM_ID_A,
    )

    assert _conflict_markets(sync_owner_conn, phone_seed) == set(phone_seed.market_ids)


async def test_a_second_attempt_does_not_grow_the_alert_queue(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ D-22: takroriy urinish YANGI qator emas, `occurrences + 1` beradi.

    Sotuvchi tugmani qayta-qayta bosishi mumkin. Debounce'siz bitta
    dublikat raqam adminga o'nlab xabar yuborardi — `alerting.py` ning
    «75 ta xabar» sinfi.
    """
    for _ in range(2):
        await resolve(
            app_sessionmaker,
            raw_phone=phone_seed.phone_e164,
            telegram_user_id=TELEGRAM_ID_A,
        )

    rows = sync_owner_conn.execute(
        "SELECT market_id, occurrences FROM alert_events "
        "WHERE alert_key = %s AND market_id = ANY(%s::uuid[]) ORDER BY market_id",
        (
            VENDOR_BINDING_CONFLICT_ALERT_KEY,
            [str(market_id) for market_id in phone_seed.market_ids],
        ),
    ).fetchall()

    assert len(rows) == 2, rows
    assert {int(row[1]) for row in rows} == {2}, rows


async def test_the_control_seed_binds_when_only_one_market_matches(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ NAZORAT: AYNI telefon, AYNI kod — bitta moslikda `BOUND`.

    Usiz yuqoridagi testlar `resolve()` ning UMUMIY nosozligini (masalan
    «har doim `MULTIPLE_MATCHES`») ko'p moslik deb o'qigan bo'lardi.
    """
    _drop_second_vendor(sync_owner_conn, phone_seed)

    outcome = await resolve(
        app_sessionmaker,
        raw_phone=phone_seed.phone_e164,
        telegram_user_id=TELEGRAM_ID_A,
    )

    assert outcome.status is ResolveStatus.BOUND
    assert outcome.vendor is not None
    assert outcome.vendor.vendor_id == phone_seed.vendor_a_id
    assert outcome.vendor.market_id == phone_seed.markets.market_a.id
    assert _conflict_markets(sync_owner_conn, phone_seed) == set()

    rows = _binding_rows(sync_owner_conn, phone_seed)
    assert len(rows) == 1
    assert rows[0][3] is None, "yangi bog'lanish FAOL bo'lishi kerak"


# ---------------------------------------------------------------------------
# D-26(a) — MOSLIK YO'Q
# ---------------------------------------------------------------------------


async def test_an_unknown_number_leaves_the_binding_table_empty(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ D-26(a): qator YOZILMAYDI va telefon HECH QAYERGA saqlanmaydi (A5)."""
    outcome = await resolve(
        app_sessionmaker,
        raw_phone="+998900000001",
        telegram_user_id=TELEGRAM_ID_A,
    )

    assert outcome.status is ResolveStatus.NO_MATCH
    assert outcome.vendor is None
    assert _binding_rows(sync_owner_conn, phone_seed) == []
    assert _conflict_markets(sync_owner_conn, phone_seed) == set()


async def test_an_unparseable_number_is_indistinguishable_from_an_unknown_one(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """⛔ Format xatosi ham `NO_MATCH` beradi — sabab OSHKOR QILINMAYDI.

    «Raqamingiz noto'g'ri formatda» javobi «raqamingiz reyestrda yo'q»
    dan ajralib turardi va o'sha farqning O'ZI enumeratsiya signali
    bo'lardi.
    """
    outcome = await resolve(
        app_sessionmaker,
        raw_phone="salom-bu-raqam-emas",
        telegram_user_id=TELEGRAM_ID_A,
    )

    assert outcome == ResolveOutcome(status=ResolveStatus.NO_MATCH)


async def test_a_number_without_a_plus_resolves_to_the_same_vendor(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⚠ Telegram `Contact.phone_number` BA'ZAN `+` SIZ keladi (Pattern 6).

    `+` siz satrni `phonenumbers` MILLIY raqam deb o'qiydi va 12 xonali
    «milliy» raqam `is_valid_number()` dan o'tmaydi — ya'ni normalizatsiya
    bo'lmasa mahsulot yo'li `NO_MATCH` berardi va sabab formatda bo'lardi.
    """
    _drop_second_vendor(sync_owner_conn, phone_seed)
    bare = phone_seed.phone_e164.removeprefix("+")
    assert bare != phone_seed.phone_e164

    outcome = await resolve(
        app_sessionmaker,
        raw_phone=bare,
        telegram_user_id=TELEGRAM_ID_A,
    )

    assert outcome.status is ResolveStatus.BOUND
    assert outcome.vendor is not None
    assert outcome.vendor.vendor_id == phone_seed.vendor_a_id


# ---------------------------------------------------------------------------
# D-26(c) — QAYTA ULANISH
# ---------------------------------------------------------------------------


async def test_rebinding_revokes_the_old_row_and_keeps_it(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
) -> None:
    """⛔ D-26(c): eski qator O'CHIRILMAYDI, BEKOR QILINADI + audit qatori.

    `DELETE` yozish «eski bog'lanish qachon, nega bekor qilindi?»
    savolini javobsiz qoldirardi — holbuki aynan shu savol nizoda (D-02)
    «xabar kimga ketgan edi?» degan javobni beradi.
    """
    _drop_second_vendor(sync_owner_conn, phone_seed)
    await resolve(
        app_sessionmaker,
        raw_phone=phone_seed.phone_e164,
        telegram_user_id=TELEGRAM_ID_A,
    )
    audit_before = await _binding_audit_count(tenant_session, phone_seed.markets.market_a.id)

    await resolve(
        app_sessionmaker,
        raw_phone=phone_seed.phone_e164,
        telegram_user_id=TELEGRAM_ID_B,
    )

    rows = _binding_rows(sync_owner_conn, phone_seed)
    assert len(rows) == 2, "eski qator O'CHIRILGAN — append-only buzilgan"
    revoked = [row for row in rows if row[3] is not None]
    active = [row for row in rows if row[3] is None]
    assert len(revoked) == 1 and len(active) == 1
    assert int(revoked[0][2]) == TELEGRAM_ID_A
    assert revoked[0][4] == "rebound"
    assert int(active[0][2]) == TELEGRAM_ID_B

    audit_after = await _binding_audit_count(tenant_session, phone_seed.markets.market_a.id)
    assert audit_after - audit_before == 1


async def test_resolving_the_same_pair_twice_writes_no_second_audit_row(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
) -> None:
    """Ayni juftlik qayta kelganda audit jurnali BO'SH o'zgarish bilan to'lmaydi."""
    _drop_second_vendor(sync_owner_conn, phone_seed)
    for _ in range(2):
        await resolve(
            app_sessionmaker,
            raw_phone=phone_seed.phone_e164,
            telegram_user_id=TELEGRAM_ID_A,
        )

    assert len(_binding_rows(sync_owner_conn, phone_seed)) == 1
    assert await _binding_audit_count(tenant_session, phone_seed.markets.market_a.id) == 0


# ---------------------------------------------------------------------------
# FAOL BOG'LANISHLAR — BOT BOZORNI BILMAYDI
# ---------------------------------------------------------------------------


async def test_active_bindings_finds_the_vendor_without_knowing_the_market(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ Pattern 7: qidiruv `active_market_ids()` bo'ylab yuradi, GUC'siz emas."""
    _drop_second_vendor(sync_owner_conn, phone_seed)
    await resolve(
        app_sessionmaker,
        raw_phone=phone_seed.phone_e164,
        telegram_user_id=TELEGRAM_ID_A,
    )

    found = await active_bindings(app_sessionmaker, telegram_user_id=TELEGRAM_ID_A)

    assert len(found) == 1
    assert found[0].vendor_id == phone_seed.vendor_a_id
    assert found[0].market_id == phone_seed.markets.market_a.id


async def test_active_bindings_is_empty_for_an_unknown_telegram_id(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """Bog'lanmagan akkaunt uchun ro'yxat BO'SH — `None` bilan ajratilmaydi."""
    assert await active_bindings(app_sessionmaker, telegram_user_id=uuid4().int % 10**12) == ()


async def test_the_market_loop_visits_every_market_in_both_outcomes(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """⛔⛔ TAYM-ORACLE O'LCHOVI — bozorlar soni IKKALA holatda ham BIR XIL.

    `test_resolve_never_breaks_out_of_the_market_loop` matnni o'lchaydi,
    bu esa XULQNI: skanerlash bosqichida ochilgan tenant sessiyalari
    ro'yxati moslik topilgan va topilmagan holatlarda AYNAN bir xil
    boshlanadi. Ikkalasi ham kerak — AST darvozasi `break` o'rniga
    `return` qo'yilgan holatni ko'rmasdi.
    """
    visited: list[UUID] = []
    original = binding_repo._tenant_session

    def _spy(*args: Any, **kwargs: Any) -> Any:
        visited.append(kwargs["market_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(binding_repo, "_tenant_session", _spy)

    await resolve(
        app_sessionmaker,
        raw_phone="+998900000002",
        telegram_user_id=TELEGRAM_ID_A,
    )
    scanned_without_match = list(visited)

    visited.clear()
    await resolve(
        app_sessionmaker,
        raw_phone=phone_seed.phone_e164,
        telegram_user_id=TELEGRAM_ID_A,
    )
    scanned_with_match = visited[: len(scanned_without_match)]

    assert scanned_without_match, "birorta faol bozor topilmadi — o'lchov bo'sh"
    assert set(phone_seed.market_ids) <= set(scanned_without_match)
    assert scanned_with_match == scanned_without_match
