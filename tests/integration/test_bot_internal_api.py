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
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.jobs.alerting import ALERT_META
from app.repositories import billing_repo, binding_repo
from app.repositories.binding_repo import (
    VENDOR_BINDING_CONFLICT_ALERT_KEY,
    DirectorResolveStatus,
    PendingVendor,
    ResolveOutcome,
    ResolveStatus,
    active_bindings,
    resolve,
    resolve_director,
)
from app.security.ratelimit import BOT_RESOLVE_LIMIT
from fixtures.billing_domain import (
    TARIFF_SOUM,
    add_daily_charge,
    add_payment,
    billing_domain_before_day_close,
)
from fixtures.notification_domain import (
    cleanup_same_phone_in_two_markets,
    seed_binding,
    seed_same_phone_in_two_markets,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD_HASH
from pydantic import SecretStr
from sbozor_core.enums import AdjustmentReason, Role
from sbozor_core.phone import normalize_phone
from sbozor_core.timeutil import business_today
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures import TenantSessionFactory
    from fixtures.market_domain import MarketDomainSeed
    from fixtures.notification_domain import TwoMarketPhoneSeed
    from fixtures.two_markets import TwoMarketSeed
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

BOT_ROUTER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "core-api"
    / "app"
    / "api"
    / "internal"
    / "bot.py"
)

TELEGRAM_ID_A = 7_610_000_001
"""⛔ `2**31` DAN KATTA — `DEFAULT_TELEGRAM_USER_ID` bilan bir xil sabab."""

TELEGRAM_ID_B = 7_610_000_002
TELEGRAM_ID_BILLING = 7_610_000_003
TELEGRAM_ID_RATE_LIMIT = 7_610_000_004
TELEGRAM_ID_UNBOUND = 7_610_000_005

DIRECTOR_CHAT_A = 7_620_000_001
"""Direktorning Telegram akkaunti — ⛔ shu shoxda u AYNAN `director_chat_id`.

Ya'ni bu son SIR: mahsulot kodida u jurnalga ham, javob tanasiga ham
chiqmaydi (`binding_repo.resolve_director` docstringi). Testda esa u
bazadan O'QIB solishtiriladi — «yozuv yo'li HAQIQATAN yozdi» degan
da'voning yagona shakli.
"""

DIRECTOR_CHAT_B = 7_620_000_002

TELEGRAM_ID_DIRECTOR_RATE_LIMIT = 7_620_000_003
"""⛔ ALOHIDA QIYMAT: rate-limit sanagichi Valkey'da TEST ORASIDA yashaydi
(oyna 15 daqiqa), ya'ni boshqa test bilan bo'lingan identifikator
sanoqni oldindan yeb qo'yardi va darvoza tasodifiy qizarardi."""

_SHARED_DIRECTOR_PHONE_COUNTER = 76_000_000
"""⛔ `two_markets._next_phone()` (70 000 000) VA `notification_domain.
_next_vendor_phone()` (79 000 000) DIAPAZONLARIDAN TASHQARIDA.

Uchala diapazon ham `+9989 7…` prefiksini beradi (haqiqiy O'zbekiston
operator kodi), ya'ni test xatosini o'qiyotgan odam raqamga qarab uning
QAYSI seeddan kelganini darhol ajratadi.
"""

_INSERT_SHARED_DIRECTOR = (
    "INSERT INTO users (id, phone_e164, password_hash, full_name, is_platform_admin) "
    "VALUES (%s, %s, %s, %s, false)"
)

_INSERT_DIRECTOR_ROLE = (
    "INSERT INTO user_market_roles (id, market_id, user_id, roles) VALUES (%s, %s, %s, %s)"
)

_DIRECTOR_CHAT_ROW = (
    "SELECT director_chat_id, quiet_hours_start, quiet_hours_end, overdue_days "
    "FROM market_notification_settings WHERE market_id = %s"
)

_SETTINGS_COUNT = (
    "SELECT count(*) FROM market_notification_settings WHERE market_id = ANY(%s::uuid[])"
)


@dataclass(frozen=True)
class BoundVendor:
    """Hisoblari BOR va Telegram akkauntiga BOG'LANGAN sotuvchi."""

    market_id: UUID
    vendor_id: UUID
    telegram_user_id: int


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


@dataclass(frozen=True)
class SharedDirectorSeed:
    """BIR ODAM — IKKI BOZORNING direktori (`users.phone_e164` global noyob).

    ⛔ BU SHAKL D-26(b) NING DIREKTORDAGI JUFTI EMAS, UNING TESKARISI.
       Sotuvchida ikki moslik REYESTR NUQSONI (telefon `vendors` da global
       noyob emas), bu yerda esa QONUNIY HOLAT: bir odam ikki bozorni
       boshqaradi va HAR BIR bozorning dayjesti unga borishi kerak.
    """

    user_id: UUID
    phone: str
    market_ids: tuple[UUID, ...]


def _next_shared_director_phone() -> str:
    """⛔ RAQAM `normalize_phone()` DAN O'TKAZILADI, QO'LDA YASALMAYDI.

    Fixture DB'ga to'g'ridan-to'g'ri yozadi (`users.phone_e164` da format
    `CHECK` i YO'Q), ya'ni qalbaki satr jimgina o'tib ketardi va test
    mahsulot HECH QACHON ko'rmaydigan shakl ustidan yugurgan bo'lardi
    (`notification_domain._next_vendor_phone()` ning aynan qarori).
    """
    global _SHARED_DIRECTOR_PHONE_COUNTER
    _SHARED_DIRECTOR_PHONE_COUNTER += 1
    return normalize_phone(f"+9989{_SHARED_DIRECTOR_PHONE_COUNTER:08d}")


@pytest.fixture
def shared_director(
    sync_owner_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> Iterator[SharedDirectorSeed]:
    """AYNI odamga IKKALA bozorda ham `director` roli beradi.

    ⚠ `seed_same_phone_in_two_markets()` NAQSHI ISHLATILMAYDI va bu farq
      MAJBURIY: o'sha seed IKKI SOTUVCHI qatori yozadi (telefon `vendors`
      da global noyob emas). Bu yerda esa BITTA `users` qatori va IKKI
      `user_market_roles` qatori bo'lishi shart — aks holda test mahsulot
      qura olmaydigan holatni o'lchagan bo'lardi.
    """
    user_id = uuid4()
    phone = _next_shared_director_phone()
    market_ids = tuple(market.id for market in two_markets.markets)

    sync_owner_conn.execute(
        _INSERT_SHARED_DIRECTOR,
        (str(user_id), phone, SEED_PASSWORD_HASH, "Ikki bozor direktori"),
    )
    for market_id in market_ids:
        sync_owner_conn.execute(
            _INSERT_DIRECTOR_ROLE,
            (str(uuid4()), str(market_id), str(user_id), [Role.DIRECTOR.value]),
        )

    try:
        yield SharedDirectorSeed(user_id=user_id, phone=phone, market_ids=market_ids)
    finally:
        # ⛔ SOZLAMA QATORLARI SHU YERDA O'CHIRILADI: `cleanup_two_markets()`
        #   `market_notification_settings` ni BILMAYDI va qoldiq qator
        #   `DELETE FROM markets` ni FK bilan yiqitardi.
        _clear_settings(sync_owner_conn, market_ids)
        sync_owner_conn.execute("DELETE FROM user_market_roles WHERE user_id = %s", (str(user_id),))
        sync_owner_conn.execute("DELETE FROM users WHERE id = %s", (str(user_id),))


def _clear_settings(conn: Connection[TupleRow], market_ids: tuple[UUID, ...]) -> None:
    conn.execute(
        "DELETE FROM market_notification_settings WHERE market_id = ANY(%s::uuid[])",
        ([str(market_id) for market_id in market_ids],),
    )


def _director_chat(conn: Connection[TupleRow], market_id: UUID) -> int | None:
    """Bozorning dayjest manzili — ⛔ BAZADAN, natija obyektidan EMAS.

    Da'vo aynan shu yerda tug'iladi: `resolve_director()` `BOUND` qaytarib,
    hech nima YOZMAGAN bo'lishi mumkin edi va natijani o'qiydigan test
    buni ko'rmasdi (07-VERIFICATION gap #1 ning aynan shakli).
    """
    row = conn.execute(_DIRECTOR_CHAT_ROW, (str(market_id),)).fetchone()
    return None if row is None else (None if row[0] is None else int(row[0]))


def _settings_rows(conn: Connection[TupleRow], market_ids: tuple[UUID, ...]) -> int:
    row = conn.execute(_SETTINGS_COUNT, ([str(market_id) for market_id in market_ids],)).fetchone()
    assert row is not None
    return int(row[0])


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


async def test_pending_vendors_lists_unbound_vendors_and_drops_bound_ones(
    phone_seed: TwoMarketPhoneSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ D-26(a) NING ADMIN KO'RINISHI HAQIQATAN YUGURADI.

    ⚠ Bu funksiyaning HTTP iste'molchisi bu fazada YO'Q (`billing_repo.
      vendor_charge_allocation()` bilan aynan bir xil holat), ya'ni uni
      hech qanday marshrut testi qamramaydi. Sinovsiz qolgan `LEFT JOIN`
      esa keyingi rejada birinchi chaqiruvdayoq `ProgrammingError` bilan
      yiqilardi va sabab «yangi marshrut buzuq» kabi ko'rinardi.
    """
    market_a = phone_seed.markets.market_a.id
    async with binding_repo.tenant_session(
        app_sessionmaker, market_id=market_a, request_id=None
    ) as session:
        before = await binding_repo.pending_vendors(
            session, market_id=market_a, business_date=business_today()
        )

    assert [item.vendor_id for item in before.items] == [phone_seed.vendor_a_id]
    assert before.next_cursor is None

    _drop_second_vendor(sync_owner_conn, phone_seed)
    await resolve(
        app_sessionmaker,
        raw_phone=phone_seed.phone_e164,
        telegram_user_id=TELEGRAM_ID_A,
    )

    async with binding_repo.tenant_session(
        app_sessionmaker, market_id=market_a, request_id=None
    ) as session:
        after = await binding_repo.pending_vendors(
            session, market_id=market_a, business_date=business_today()
        )

    assert after.items == (), "bog'langan sotuvchi «kutilmoqda» ro'yxatida QOLDI"


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
    original = binding_repo.tenant_session

    def _spy(*args: Any, **kwargs: Any) -> Any:
        visited.append(kwargs["market_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(binding_repo, "tenant_session", _spy)

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


# ---------------------------------------------------------------------------
# DIREKTOR SHOXI — `director_chat_id` NING YAGONA YOZUV YO'LI (RECON-03)
#
# ⛔⛔ 07-18 GACHA BU YO'L UMUMAN MAVJUD EMAS EDI: sozlama ustuniga butun
#    repo bo'ylab birorta yozuvchi yo'q edi, ya'ni `outbox_repo` ning
#    o'quvchisi produksiyada HAR DOIM `None` qaytarardi va direktor
#    dayjestni HECH QACHON olmasdi. Quyidagi da'volarning HAR BIRI
#    bazadan O'QIB tasdiqlanadi — natija obyektining O'ZI yetarli emas.
# ---------------------------------------------------------------------------


async def test_a_registered_director_gets_the_digest_address_written(
    two_markets: TwoMarketSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ MEZON #3 NING YOZUV YARMI: qator BAZADA paydo bo'ladi."""
    market_a = two_markets.market_a
    try:
        outcome = await resolve_director(
            app_sessionmaker,
            raw_phone=market_a.director_phone,
            telegram_user_id=DIRECTOR_CHAT_A,
        )

        assert outcome.status is DirectorResolveStatus.BOUND
        assert [ref.market_id for ref in outcome.markets] == [market_a.id]
        assert outcome.markets[0].user_id == market_a.director_user_id
        assert _director_chat(sync_owner_conn, market_a.id) == DIRECTOR_CHAT_A, (
            "⛔ `resolve_director()` `bound` qaytardi, lekin "
            "`market_notification_settings.director_chat_id` BAZADA yozilmadi — "
            "aynan shu bo'shliq mezon #3 ni bajarilmas qilgan edi"
        )
    finally:
        _clear_settings(sync_owner_conn, (market_a.id,))


async def test_one_person_directing_two_markets_gets_both_rows_written(
    shared_director: SharedDirectorSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ IKKALA BOZORNING HAM qatori yoziladi — «birinchisi» tanlanmaydi.

    `users.phone_e164` GLOBAL NOYOB, ya'ni bir telefon = bir odam va
    uning ikki bozorda direktor bo'lishi QONUNIY. D-26(b) ning
    «bir nechta moslik -> bog'lanish YO'Q» qoidasi bu shoxga
    QO'LLANMAYDI: u yerda noaniqlik reyestr nuqsoni edi, bu yerda esa
    ikkala javob ham to'g'ri.
    """
    outcome = await resolve_director(
        app_sessionmaker,
        raw_phone=shared_director.phone,
        telegram_user_id=DIRECTOR_CHAT_A,
    )

    assert outcome.status is DirectorResolveStatus.BOUND
    assert {ref.market_id for ref in outcome.markets} == set(shared_director.market_ids)
    assert {ref.user_id for ref in outcome.markets} == {shared_director.user_id}
    for market_id in shared_director.market_ids:
        assert _director_chat(sync_owner_conn, market_id) == DIRECTOR_CHAT_A, market_id


async def test_an_unknown_number_writes_no_settings_row(
    two_markets: TwoMarketSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ Reyestrda yo'q telefon: `no_match` va YANGI QATOR YO'Q.

    ⚠ `finally` DA TOZALASH — DA'VONI ZAIFLASHTIRMAYDI, TESHIKNI YOPADI:
      da'vo `_settings_rows(...) == 0` da o'lchanadi va u tozalashdan
      OLDIN bajariladi. Tozalashsiz regressiya (qator YOZILDI) `DELETE
      FROM markets` ni FK bilan yiqitib, butun to'plamga ERROR kaskadi
      tarqatardi — nosozlik AYNAN o'z testida qolishi kerak.
    """
    market_ids = tuple(market.id for market in two_markets.markets)

    try:
        outcome = await resolve_director(
            app_sessionmaker,
            raw_phone="+998900000011",
            telegram_user_id=DIRECTOR_CHAT_A,
        )

        assert outcome.status is DirectorResolveStatus.NO_MATCH
        assert outcome.markets == ()
        assert _settings_rows(sync_owner_conn, market_ids) == 0
    finally:
        _clear_settings(sync_owner_conn, market_ids)


async def test_an_unparseable_number_is_indistinguishable_for_the_director_branch(
    two_markets: TwoMarketSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ Format xatosi ham `no_match` — sabab OSHKOR QILINMAYDI.

    «Raqamingiz noto'g'ri formatda» javobi «raqamingiz reyestrda yo'q»
    dan ajralib turardi va farqning O'ZI enumeratsiya signali bo'lardi
    (`resolve()` ning aynan qoidasi).
    """
    market_ids = tuple(market.id for market in two_markets.markets)

    try:
        outcome = await resolve_director(
            app_sessionmaker,
            raw_phone="salom-bu-raqam-emas",
            telegram_user_id=DIRECTOR_CHAT_A,
        )

        assert outcome.status is DirectorResolveStatus.NO_MATCH
        assert _settings_rows(sync_owner_conn, market_ids) == 0
    finally:
        _clear_settings(sync_owner_conn, market_ids)


async def test_a_blocked_director_gets_no_digest_address(
    two_markets: TwoMarketSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ BLOKLANGAN XODIM DAYJEST OLMAYDI (`is_active is False`).

    Aks holda bloklangan direktor bozorning kunlik tushumini, bandligini
    va TOP-10 qarzdorini olishda DAVOM ETARDI — bloklash esa aynan shu
    oqimni to'xtatish uchun mavjud (D-08).
    """
    market_a = two_markets.market_a
    sync_owner_conn.execute(
        "UPDATE users SET is_active = false WHERE id = %s",
        (str(market_a.director_user_id),),
    )

    try:
        outcome = await resolve_director(
            app_sessionmaker,
            raw_phone=market_a.director_phone,
            telegram_user_id=DIRECTOR_CHAT_A,
        )

        assert outcome.status is DirectorResolveStatus.NO_MATCH
        assert _director_chat(sync_owner_conn, market_a.id) is None
    finally:
        _clear_settings(sync_owner_conn, (market_a.id,))


async def test_a_cashier_phone_never_becomes_a_digest_address(
    two_markets: TwoMarketSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ ROL TEKSHIRUVI HAQIQIY: kassir telefoni `no_match` (T-07-97).

    Bu darvoza yo'q bo'lsa HAR QANDAY xodim — kassir, nazoratchi — o'z
    kontaktini ulashib bozorning butun kunlik tushumini o'z chatiga
    yo'naltira olardi.
    """
    market_a = two_markets.market_a

    try:
        outcome = await resolve_director(
            app_sessionmaker,
            raw_phone=market_a.cashier_phone,
            telegram_user_id=DIRECTOR_CHAT_A,
        )

        assert outcome.status is DirectorResolveStatus.NO_MATCH
        assert _director_chat(sync_owner_conn, market_a.id) is None
    finally:
        _clear_settings(sync_owner_conn, (market_a.id,))


async def test_rebinding_overwrites_the_address_without_growing_the_table(
    two_markets: TwoMarketSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ QAYTA ULANISH: qiymat USTIGA yoziladi, qatorlar soni O'SMAYDI.

    Direktor telefonini yangi Telegram akkauntiga ko'chirsa (akkaunt
    almashtirildi, telefon o'g'irlandi) dayjest ESKI chatga ketishda
    davom etmasligi kerak.
    """
    market_a = two_markets.market_a
    try:
        await resolve_director(
            app_sessionmaker,
            raw_phone=market_a.director_phone,
            telegram_user_id=DIRECTOR_CHAT_A,
        )
        await resolve_director(
            app_sessionmaker,
            raw_phone=market_a.director_phone,
            telegram_user_id=DIRECTOR_CHAT_B,
        )

        assert _director_chat(sync_owner_conn, market_a.id) == DIRECTOR_CHAT_B
        assert _settings_rows(sync_owner_conn, (market_a.id,)) == 1
    finally:
        _clear_settings(sync_owner_conn, (market_a.id,))


async def test_binding_the_director_never_touches_the_market_settings(
    two_markets: TwoMarketSeed,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ NAZORAT (T-07-100): `UPSERT` FAQAT BITTA USTUNGA tegadi.

    `quiet_hours_*` va `overdue_days` — BOZOR sozlamasi (D-19) va ular
    direktorning telefonidan kelmaydi. `EXCLUDED` bilan ustiga yozish
    qayta ulanishni «sozlamalarni standartga qaytarish» amaliga
    aylantirardi va direktor sababni HECH QAYERDA ko'rmasdi.
    """
    market_a = two_markets.market_a
    try:
        sync_owner_conn.execute(
            "INSERT INTO market_notification_settings "
            "(market_id, quiet_hours_start, quiet_hours_end, overdue_days) "
            "VALUES (%s, %s, %s, %s)",
            (str(market_a.id), "22:30", "06:15", 7),
        )

        await resolve_director(
            app_sessionmaker,
            raw_phone=market_a.director_phone,
            telegram_user_id=DIRECTOR_CHAT_A,
        )

        row = sync_owner_conn.execute(_DIRECTOR_CHAT_ROW, (str(market_a.id),)).fetchone()
        assert row is not None
        assert int(row[0]) == DIRECTOR_CHAT_A
        assert (row[1].hour, row[1].minute) == (22, 30), row
        assert (row[2].hour, row[2].minute) == (6, 15), row
        assert int(row[3]) == 7, row
    finally:
        _clear_settings(sync_owner_conn, (market_a.id,))


def test_resolve_director_never_breaks_out_of_the_market_loop() -> None:
    """⛔ TAYM-ORACLE: skaner tsiklida `break` YO'Q (T-07-101).

    `resolve()` bilan AYNI sabab: erta chiqish javob VAQTINI moslikning
    bor-yo'qligiga bog'lardi va neytral javob ma'nosini yo'qotardi.

    ⚠ AST, GREP EMAS (`test_resolve_never_breaks_out_of_the_market_loop`
      ning aynan qarori): `break` so'zi izohda uchrasa sodda grep uni
      jazolardi va yagona «tuzatish» yo'li sababni o'chirish bo'lardi.
    """
    tree = ast.parse(BINDING_REPO_SOURCE.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
    }

    assert "resolve_director" in functions, sorted(functions)
    breaks = [
        node for node in ast.walk(functions["resolve_director"]) if isinstance(node, ast.Break)
    ]
    assert not breaks, "`resolve_director()` ichida `break` topildi (T-07-101)."


def test_the_director_write_path_adds_no_audit_call() -> None:
    """⛔ `market_notification_settings` GA AUDIT QATORI YOZILMAYDI (T-07-102).

    Jadval `AUDITED_TABLES` dan TEXNIK sababga ko'ra chiqarilgan: unda
    `id uuid` ustuni yo'q va `fn_audit_row()` `row_id` ni `uuid` ga
    keltiradi, ya'ni trigger har DML da yiqilardi. Ilova darajasida qo'lda
    yozish esa `revoke()` da topilgan WR-03 nuqsonining takrori bo'lardi.

    ⚠ SANOQ AST BILAN O'LCHANADI, GREP BILAN EMAS: mahsulot fayli
      taqiqning SABABINI o'z docstringida yozadi va sodda matn qidiruvi
      o'sha izohni «yangi chaqiruv» deb o'qirdi — yagona «tuzatish» yo'li
      sababni o'chirish bo'lardi (03-07 / G7-8 darsi).
    """
    tree = ast.parse(BINDING_REPO_SOURCE.read_text(encoding="utf-8"))
    audit_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "write_app_audit"
    ]

    assert len(audit_calls) == 1, (
        f"`binding_repo` da {len(audit_calls)} ta audit chaqiruvi bor — kutilgani "
        "AYNAN BITTA (`revoke()`). Direktor yo'li audit qatori YOZMAYDI."
    )


# ---------------------------------------------------------------------------
# `/internal/bot/*` — SERVIS TOKENI VA TOR YUZA
# ---------------------------------------------------------------------------


SERVICE_TOKEN = "test-bot-service-token-not-a-real-secret"  # noqa: S105 - test uskunasi


@pytest.fixture
def bot_token(api_app: FastAPI, test_settings: Settings) -> Iterator[str]:
    """`bot_service_token` O'RNATILGAN `Settings` — TESTDAN KEYIN QAYTARILADI.

    ⚠ `test_settings` SESSIYA doirasida va uni JOYIDA o'zgartirish tokenni
      butun to'plamga tarqatardi: «sozlanmagan token -> 503» testi keyingi
      yugurishda jimgina o'z ma'nosini yo'qotardi.
    """
    original = api_app.state.settings
    api_app.state.settings = test_settings.model_copy(
        update={"bot_service_token": SecretStr(SERVICE_TOKEN)}
    )
    try:
        yield SERVICE_TOKEN
    finally:
        api_app.state.settings = original


@pytest.fixture
def bot_headers(bot_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {bot_token}"}


@pytest.fixture
def bound_vendor(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[BoundVendor]:
    """HAQIQIY hisob va QISMAN to'lov + o'sha sotuvchiga Telegram bog'lanishi.

    ⛔⛔ HISOB `_safe_service_date()` (BAZANING «kechagi kuni») BILAN
       YOZILADI, `SEED_BUSINESS_DATE` (2026-09-01) BILAN EMAS — VA BU
       O'LCHANGAN FARQ. Ikkala marshrut ham `as_of = business_today()`
       beradi, `vendor_outstanding()` esa hisoblarni `service_date <
       as_of` bilan cheklaydi. Seed'ning QADALGAN sanasi bugundan KEYIN
       bo'lgani uchun u filtrdan o'tmasdi va tenglik testlari `0 == 0` /
       `[] == []` bo'lib BO'SH-ROST bo'lib qolardi.

    ⚠ TO'LOV HISOBDAN KAM: to'liq to'langan hisob `settled=True` va
      `outstanding = 0` berardi — ya'ni «qoldiq qaytadimi?» degan da'vo
      nolni nol bilan solishtirardi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        rows = billing.market_a
        stall_id = rows.stall_with_two_occupied_slots
        assert stall_id is not None, "A bozorining rastasi yo'q — seed buzilgan"

        _charge_id, service_day = add_daily_charge(
            sync_owner_conn,
            market_id=rows.market_id,
            stall_id=stall_id,
            vendor_id=rows.vendor_id,
            tariff_id=rows.tariff_id,
        )
        # ⚠ `override_reason` MAJBURIY: `ck_payments_override_is_paired`
        #   server bergan summadan HAR QANDAY chetlanish uchun NOMLANGAN
        #   sabab talab qiladi (D-19 sxemaga ko'chirilgan).
        add_payment(
            sync_owner_conn,
            market_id=rows.market_id,
            stall_id=stall_id,
            vendor_id=rows.vendor_id,
            cashier_id=rows.cashier_id,
            shift_id=rows.open_shift_id,
            service_date=service_day,
            amount_soum=TARIFF_SOUM // 3,
            override_reason=AdjustmentReason.PARTIAL_DAY.value,
        )
        binding_id = seed_binding(
            sync_owner_conn,
            market_id=rows.market_id,
            vendor_id=rows.vendor_id,
            telegram_user_id=TELEGRAM_ID_BILLING,
        )
        try:
            yield BoundVendor(
                market_id=rows.market_id,
                vendor_id=rows.vendor_id,
                telegram_user_id=TELEGRAM_ID_BILLING,
            )
        finally:
            sync_owner_conn.execute(
                "DELETE FROM vendor_telegram_bindings WHERE id = %s", (str(binding_id),)
            )


async def test_a_request_without_a_token_is_rejected(
    api_client: httpx.AsyncClient, bot_headers: dict[str, str]
) -> None:
    """⛔ Tokensiz so'rov `401` va javob TANASI sababni aytmaydi (T-07-38)."""
    assert bot_headers  # token SOZLANGAN — ya'ni 503 emas, 401 o'lchanadi

    response = await api_client.get("/internal/bot/vendor/summary?telegram_user_id=1")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


async def test_a_request_with_a_wrong_token_is_rejected_identically(
    api_client: httpx.AsyncClient, bot_headers: dict[str, str]
) -> None:
    """⛔ «Token yo'q» va «token noto'g'ri» — BAYT-BAYT AYNI javob.

    Ajratish hujumchiga «sarlavha shakli to'g'ri edi» degan foydali
    signal berardi.
    """
    assert bot_headers

    missing = await api_client.get("/internal/bot/vendor/summary?telegram_user_id=1")
    wrong = await api_client.get(
        "/internal/bot/vendor/summary?telegram_user_id=1",
        headers={"Authorization": "Bearer butunlay-boshqa-token"},
    )

    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


async def test_an_unconfigured_token_closes_the_surface_completely(
    api_client: httpx.AsyncClient,
) -> None:
    """⛔ FAIL-CLOSED: sozlanmagan token `503` beradi, «hammaga ochiq» EMAS.

    ⚠ Bu test `bot_token` fixture'ini ATAYIN SO'RAMAYDI — `test_settings`
      ning standart holati aynan shu: `bot_service_token` bo'sh.
    """
    response = await api_client.post(
        "/internal/bot/resolve",
        json={"telegram_user_id": TELEGRAM_ID_A, "phone": "+998900000003"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "unavailable"}


async def test_the_internal_surface_never_sets_a_cookie(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    phone_seed: TwoMarketPhoneSeed,
) -> None:
    """⛔ D-10 / T-07-39: SESSIYA TUG'ILMAYDI — `Set-Cookie` YO'Q."""
    response = await api_client.post(
        "/internal/bot/resolve",
        headers=bot_headers,
        json={"telegram_user_id": TELEGRAM_ID_A, "phone": phone_seed.phone_e164},
    )

    assert response.status_code == 200
    assert "set-cookie" not in {name.lower() for name in response.headers}


def test_the_internal_router_creates_no_session_primitives() -> None:
    """⛔ D-10 GREP DARVOZASI — token chiqaruvchi nomlar manbada YO'Q.

    ⚠ Bu `Set-Cookie` testidan ALOHIDA va u kerak: cookie'siz JWT
      chiqarish (masalan javob tanasida) ham ikkinchi sessiya modeli
      bo'lardi va sarlavha testi uni KO'RMASDI.
    """
    source = BOT_ROUTER_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(BOT_ROUTER_SOURCE))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    forbidden = names & {
        "create_access_token",
        "encode_access",
        "issue_refresh",
        "issue_live_token",
        "Principal",
        "set_cookie",
        "require_permission",
    }
    assert forbidden == set(), forbidden

    # Doimiy vaqtli solishtiruv — VA `==` YO'Q.
    assert "compare_digest" in source
    assert "token ==" not in source
    assert "== token" not in source

    # ⛔ D-06: «saqlangan qoldiq» ma'nosini beradigan nom NA JAVOBDA, NA
    #   KODDA, NA IZOHDA. Izohda ham taqiqlanishi 03-07 / 07-02 darsi:
    #   sodda darvoza izohni koddan ajratmaydi, ya'ni sababni yozish
    #   yagona «tuzatish» yo'lini sababni o'chirishga aylantirardi.
    assert "balance" not in source, (
        "`balance` nomi `/internal/bot/*` yuzasiga kirib qoldi — saqlangan "
        "qoldiq ustuni loyihada MAVJUD EMAS (D-06) va uni nom darajasida "
        "tiklash ikkinchi haqiqat manbaiga birinchi qadam bo'lardi"
    )


async def test_multiple_matches_is_neutral_in_shape(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    phone_seed: TwoMarketPhoneSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ D-26(b) javobi `no_match` BILAN AYNI SHAKLDA (qo'shimcha maydon yo'q).

    Bot ikkalasida ham BIR XIL matn ko'rsatadi; shox faqat serverda
    yoziladi (`alert_events`).
    """
    conflict = await api_client.post(
        "/internal/bot/resolve",
        headers=bot_headers,
        json={"telegram_user_id": TELEGRAM_ID_A, "phone": phone_seed.phone_e164},
    )
    unknown = await api_client.post(
        "/internal/bot/resolve",
        headers=bot_headers,
        json={"telegram_user_id": TELEGRAM_ID_B, "phone": "+998900000004"},
    )

    assert conflict.status_code == unknown.status_code == 200
    assert conflict.json() == {"status": "multiple_matches", "vendor": None}
    assert unknown.json() == {"status": "no_match", "vendor": None}
    assert set(conflict.json()) == set(unknown.json())
    # ⛔ Anomaliya SERVERDA yozilgan — javob neytral bo'lgani bilan
    #   reyestr nuqsoni yo'qolmadi.
    assert _conflict_markets(sync_owner_conn, phone_seed) == set(phone_seed.market_ids)


async def test_resolve_is_rate_limited_per_telegram_account(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    phone_seed: TwoMarketPhoneSeed,
) -> None:
    """⛔ T-07-40 ning IKKINCHI qatlami — cheksiz urinish yo'li yopiq."""
    telegram_id = TELEGRAM_ID_RATE_LIMIT
    statuses = [
        (
            await api_client.post(
                "/internal/bot/resolve",
                headers=bot_headers,
                json={"telegram_user_id": telegram_id, "phone": "+998900000005"},
            )
        ).status_code
        for _ in range(BOT_RESOLVE_LIMIT + 1)
    ]

    assert statuses[:BOT_RESOLVE_LIMIT] == [200] * BOT_RESOLVE_LIMIT
    assert statuses[-1] == 429


# ---------------------------------------------------------------------------
# `POST /internal/bot/director/resolve` — YOZUV YO'LI HTTP ORQALI
# ---------------------------------------------------------------------------

DIRECTOR_RESOLVE_URL = "/internal/bot/director/resolve"


async def test_the_director_route_writes_the_address_and_reports_the_count(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    two_markets: TwoMarketSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ MEZON #3 NING MAHSULOT YO'LI — HTTP dan bazagacha.

    Da'vo javob bilan TUGAMAYDI: `market_notification_settings` dan
    O'QILADI. `{"status": "bound"}` qaytarib hech nima yozmaydigan
    marshrut aynan 07-VERIFICATION topgan bo'shliqning shakli bo'lardi.
    """
    market_a = two_markets.market_a
    try:
        response = await api_client.post(
            DIRECTOR_RESOLVE_URL,
            headers=bot_headers,
            json={
                "telegram_user_id": DIRECTOR_CHAT_A,
                "phone": market_a.director_phone,
            },
        )

        assert response.status_code == 200, response.text
        assert response.json() == {"status": "bound", "market_count": 1}
        assert _director_chat(sync_owner_conn, market_a.id) == DIRECTOR_CHAT_A
    finally:
        _clear_settings(sync_owner_conn, (market_a.id,))


async def test_the_director_route_is_neutral_for_an_unknown_number(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    two_markets: TwoMarketSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ Noma'lum raqam: `no_match` + `market_count = 0`, qator YO'Q."""
    market_ids = tuple(market.id for market in two_markets.markets)

    try:
        response = await api_client.post(
            DIRECTOR_RESOLVE_URL,
            headers=bot_headers,
            json={"telegram_user_id": DIRECTOR_CHAT_B, "phone": "+998900000012"},
        )

        assert response.status_code == 200, response.text
        assert response.json() == {"status": "no_match", "market_count": 0}
        assert _settings_rows(sync_owner_conn, market_ids) == 0
    finally:
        _clear_settings(sync_owner_conn, market_ids)


async def test_the_director_route_carries_no_secret_in_its_response(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    two_markets: TwoMarketSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """⛔ T-07-99: javobda `chat_id`, telefon va ism YO'Q; `Set-Cookie` ham YO'Q.

    Skan REKURSIV va u XOM MATN ustida: maydon nomini o'zgartirish
    (`chat_id` -> `address`) kalitlar bo'yicha yozilgan da'vodan o'tib
    ketardi.
    """
    market_a = two_markets.market_a
    try:
        response = await api_client.post(
            DIRECTOR_RESOLVE_URL,
            headers=bot_headers,
            json={
                "telegram_user_id": DIRECTOR_CHAT_A,
                "phone": market_a.director_phone,
            },
        )

        assert response.status_code == 200, response.text
        assert set(response.json()) == {"status", "market_count"}
        assert "set-cookie" not in {name.lower() for name in response.headers}

        body = response.text
        assert str(DIRECTOR_CHAT_A) not in body, (
            "⛔ Direktorning chat identifikatori javob tanasiga chiqdi — u SIR"
        )
        assert market_a.director_phone not in body
        assert market_a.director_phone.removeprefix("+") not in body
        assert str(market_a.id) not in body, (
            "⛔ Bozor identifikatori ham qaytarilmaydi: bot uni ishlatmaydi va "
            "qaytarish yuzani sababsiz kengaytirardi"
        )
    finally:
        _clear_settings(sync_owner_conn, (market_a.id,))


async def test_the_director_route_rejects_a_missing_and_a_wrong_token_identically(
    api_client: httpx.AsyncClient, bot_headers: dict[str, str]
) -> None:
    """⛔ «Token yo'q» va «token noto'g'ri» — BAYT-BAYT AYNI javob (T-07-38).

    ⚠ Javob mavjud `/resolve` niki bilan ham solishtiriladi: ikki yuzaning
      rad etish matni ajralib qolsa, hujumchi qaysi marshrutga tushganini
      javobdan o'qiy olardi.
    """
    assert bot_headers  # token SOZLANGAN — ya'ni 401 o'lchanadi, 503 emas

    payload = {"telegram_user_id": DIRECTOR_CHAT_A, "phone": "+998900000013"}
    missing = await api_client.post(DIRECTOR_RESOLVE_URL, json=payload)
    wrong = await api_client.post(
        DIRECTOR_RESOLVE_URL,
        headers={"Authorization": "Bearer butunlay-boshqa-token"},
        json=payload,
    )
    vendor_surface = await api_client.post(
        "/internal/bot/resolve",
        json={"telegram_user_id": DIRECTOR_CHAT_A, "phone": "+998900000013"},
    )

    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()
    assert missing.json() == vendor_surface.json()


async def test_the_director_route_is_fail_closed_without_a_token_setting(
    api_client: httpx.AsyncClient,
) -> None:
    """⛔ FAIL-CLOSED: sozlanmagan token `503`, «hammaga ochiq» EMAS.

    ⚠ Bu test `bot_token` fixture'ini ATAYIN SO'RAMAYDI — `test_settings`
      ning standart holati aynan shu: `bot_service_token` bo'sh.
    """
    response = await api_client.post(
        DIRECTOR_RESOLVE_URL,
        json={"telegram_user_id": DIRECTOR_CHAT_A, "phone": "+998900000014"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "unavailable"}


async def test_the_director_route_shares_the_rate_limit_counter(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    two_markets: TwoMarketSeed,
) -> None:
    """⛔ SANAGICH SOTUVCHINIKI BILAN BO'LINADI VA BU ONGLI QAROR (T-07-103).

    Bot bitta kontakt ulashishda IKKI so'rov yuboradi, ya'ni alohida
    sanagich bitta Telegram akkauntining umumiy byudjetini IKKI BAROBAR
    oshirardi. Bu yerda budjet BIR: `/resolve` yegan urinishlar
    `/director/resolve` uchun ham hisoblanadi.
    """
    payload = {
        "telegram_user_id": TELEGRAM_ID_DIRECTOR_RATE_LIMIT,
        "phone": "+998900000015",
    }

    for _ in range(BOT_RESOLVE_LIMIT):
        first = await api_client.post("/internal/bot/resolve", headers=bot_headers, json=payload)
        assert first.status_code == 200, first.text

    blocked = await api_client.post(DIRECTOR_RESOLVE_URL, headers=bot_headers, json=payload)

    assert blocked.status_code == 429, blocked.text
    assert blocked.json() == {"detail": "too_many_attempts"}


async def test_vendor_summary_equals_the_billing_repo_number(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    bound_vendor: BoundVendor,
    app_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """⛔ D-06: son `billing_repo.vendor_outstanding()` BILAN `==` TENG.

    Yangi SQL yozish IKKINCHI HAQIQAT MANBAI tug'dirardi: bir kun bot bir
    sonni, qarzdorlik reestri boshqasini ko'rsatardi va ikkalasi ham
    «to'g'ri» bo'lardi.
    """
    response = await api_client.get(
        "/internal/bot/vendor/summary",
        headers=bot_headers,
        params={"telegram_user_id": bound_vendor.telegram_user_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["markets"]) == 1
    entry = payload["markets"][0]
    assert entry["market_id"] == str(bound_vendor.market_id)
    assert entry["vendor_id"] == str(bound_vendor.vendor_id)

    as_of = date.fromisoformat(entry["as_of"])
    async with binding_repo.tenant_session(
        app_sessionmaker, market_id=bound_vendor.market_id, request_id=None
    ) as session:
        expected = await billing_repo.vendor_outstanding(
            session,
            market_id=bound_vendor.market_id,
            vendor_ids=[bound_vendor.vendor_id],
            as_of=as_of,
        )

    assert entry["outstanding_soum"] == expected[bound_vendor.vendor_id]
    assert entry["outstanding_soum"] != 0, (
        "qoldiq NOL — seed hisob yozmagan va tenglik BO'SH-ROST bo'lib qolardi"
    )
    assert "balance" not in entry
    assert not {"vendor_name", "phone", "full_name"} & set(entry)


async def test_vendor_payments_mirrors_the_allocation_rows(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    bound_vendor: BoundVendor,
    app_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """⛔ D-24: qatorlar `vendor_charge_allocation()` DAN HOSILA.

    6-faza funksiyani ATAYIN iste'molchisiz qoldirgan va bu faza uning
    iste'molchisi — ya'ni yangi taqsimlash arifmetikasi YOZILMAYDI.
    """
    response = await api_client.get(
        "/internal/bot/vendor/payments",
        headers=bot_headers,
        params={
            "telegram_user_id": bound_vendor.telegram_user_id,
            "market_id": str(bound_vendor.market_id),
        },
    )

    assert response.status_code == 200
    payload = response.json()

    async with binding_repo.tenant_session(
        app_sessionmaker, market_id=bound_vendor.market_id, request_id=None
    ) as session:
        allocation = await billing_repo.vendor_charge_allocation(
            session,
            market_id=bound_vendor.market_id,
            vendor_id=bound_vendor.vendor_id,
            as_of=business_today(),
        )

    assert payload["rule"] == allocation.rule
    assert allocation.rows, "seed birorta hisob yozmagan — ko'zgu BO'SH-ROST bo'lardi"
    returned = [
        (row["service_date"], row["stall_code"], row["due_soum"]) for row in payload["rows"]
    ]
    assert returned == [
        (row.service_date.isoformat(), row.stall_code, row.due_soum) for row in allocation.rows
    ]
    assert [row["paid_soum"] for row in payload["rows"]] == [
        row.paid_soum for row in allocation.rows
    ]
    assert [row["settled"] for row in payload["rows"]] == [row.settled for row in allocation.rows]


async def test_vendor_payments_needs_an_active_binding_in_that_market(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
    bound_vendor: BoundVendor,
) -> None:
    """⛔ Begona bozor uchun `404` — «bor, lekin sizniki emas» farqi ochilmaydi."""
    response = await api_client.get(
        "/internal/bot/vendor/payments",
        headers=bot_headers,
        params={
            "telegram_user_id": bound_vendor.telegram_user_id,
            "market_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "not_bound"}


async def test_vendor_summary_is_404_for_an_unbound_account(
    api_client: httpx.AsyncClient,
    bot_headers: dict[str, str],
) -> None:
    """Bog'lanmagan akkaunt uchun `404` — bo'sh ro'yxat EMAS.

    Bo'sh `200` bot tomonda «qarzingiz yo'q» bo'lib ko'rinardi, holbuki
    haqiqat «siz hali ulanmagansiz» — ikki butunlay boshqa xabar.
    """
    response = await api_client.get(
        "/internal/bot/vendor/summary",
        headers=bot_headers,
        params={"telegram_user_id": TELEGRAM_ID_UNBOUND},
    )

    assert response.status_code == 404
