"""Ikki bozor seed'i — cross-tenant matritsasining MANBAI.

Bitta bozorli seed bilan tenant izolyatsiyasini isbotlab bo'lmaydi: "0 qator
qaytdi" javobi izolyatsiya ishlaganini ham, jadval bo'shligini ham
bildirishi mumkin. Shuning uchun har doim IKKI bozor seed qilinadi va
testlar "A ni ko'raman, B ni ko'rmayman" shaklida yoziladi.

Seed `sbozor_owner` bilan bajariladi:
  * `users` — `sbozor_app` ga `REVOKE ALL` qilingan (Pattern 2);
  * `markets` — app-rolga faqat `SELECT` beriladi;
  * `user_market_roles` — app-rol bilan yozish uchun avval tenant konteksti
    kerak bo'lardi, ya'ni seed o'zi sinalayotgan mexanizmga tayanib qolardi.

Har chaqiruvda YANGI UUID'lar hosil qilinadi va teardown seed'ni to'liq
o'chiradi — testlar orasida qoldiq qator qolmaydi (`auth_list_markets()`
kabi global funksiyalar aks holda flaky bo'lardi).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.security import hash_password

__all__ = [
    "SEED_PASSWORD",
    "SEED_PASSWORD_HASH",
    "MarketSeed",
    "TwoMarketSeed",
    "cleanup_two_markets",
    "seed_two_markets",
]

SEED_PASSWORD = "sbozor-test-parol-2026"
"""Seed foydalanuvchilarining ochiq paroli — BARCHA test seed'lari uchun yagona.

`fixtures/auth_users.py` uni AYNAN shu yerdan oladi. Ikki modulda ikki
literal bo'lganda ular jimgina ajralib ketardi va `MarketSeed.admin_password`
`auth_seed` faol bo'lgan testlarda yolg'on qiymat bo'lib qolardi (login 401
bilan yiqilardi, sabab esa fixture'da ko'rinmasdi).
"""

SEED_PASSWORD_HASH = hash_password(SEED_PASSWORD)
"""Hash BIR MARTA hisoblanadi (modul import paytida, ~100 ms).

01-04 seed'i bu yerga o'rinbosar satr yozardi va login oqimi u bilan
ishlamasdi. Endi seed foydalanuvchilarining HAMMASI mahsulot yo'lidan
(`POST /auth/login`) kira oladi — cross-tenant matritsasi tokenni aynan
shu yo'l bilan oladi, qo'lda yasalgan token bilan emas.
"""

_AUDIT_ID_PENDING = 0
"""`audit_row_id` uchun vaqtinchalik qiymat — `seed_two_markets()` ichida almashtiriladi.

Bu qiymat funksiyadan TASHQARIGA hech qachon chiqmaydi: `MarketSeed`
qaytarilishidan oldin `dataclasses.replace()` bilan haqiqiy `audit_log.id`
qo'yiladi.
"""


@dataclass(frozen=True)
class MarketSeed:
    """Bitta bozor va uning foydalanuvchilari."""

    id: UUID
    name: str
    admin_user_id: UUID
    admin_phone: str
    admin_role_id: UUID
    cashier_user_id: UUID
    cashier_phone: str
    cashier_role_id: UUID
    director_user_id: UUID
    director_phone: str
    director_role_id: UUID
    audit_row_id: int
    """Shu bozorning BIRINCHI `audit_log` qatorining kaliti.

    Qator seed paytida a'zolik INSERT'ining triggeri tomonidan yoziladi —
    ya'ni mahsulot yo'lidan tug'ilgan haqiqiy yozuv.

    Cross-tenant matritsasi undan foydalanadi: A bozori tokeni bilan
    olingan `GET /api/v1/audit` javobida B bozorining AYNAN SHU `id` si
    bo'lmasligi tekshiriladi. "Javobda B'ning UUID'lari yo'q" da'vosidan
    kuchliroq — bu yerda tekshirilayotgan qatorning MAVJUDLIGI ham
    isbotlangan (`test_audit_list_shows_the_own_market_probe_row`).
    """

    admin_password: str = SEED_PASSWORD
    """Bozor adminining ochiq paroli (barcha seed foydalanuvchilarida bir xil)."""

    @property
    def user_ids(self) -> tuple[UUID, ...]:
        return (self.admin_user_id, self.cashier_user_id, self.director_user_id)

    @property
    def role_ids(self) -> tuple[UUID, ...]:
        """A'zolik qatorlarining kalitlari (`audit_log.row_id` shular bilan to'ladi)."""
        return (self.admin_role_id, self.cashier_role_id, self.director_role_id)

    @property
    def phones(self) -> tuple[str, ...]:
        return (self.admin_phone, self.cashier_phone, self.director_phone)


@dataclass(frozen=True)
class TwoMarketSeed:
    """Ikki bozor + ikkalasiga a'zo platforma admini (D-06 oqimi uchun)."""

    market_a: MarketSeed
    market_b: MarketSeed
    platform_admin_id: UUID
    platform_admin_phone: str
    platform_admin_role_ids: dict[UUID, UUID] = field(default_factory=dict)

    @property
    def markets(self) -> tuple[MarketSeed, MarketSeed]:
        return (self.market_a, self.market_b)

    @property
    def all_user_ids(self) -> tuple[UUID, ...]:
        return (*self.market_a.user_ids, *self.market_b.user_ids, self.platform_admin_id)


# Har bozorda: admin + kassir + direktor + platforma admini = 4 a'zolik qatori.
ROLES_PER_MARKET = 4

_PHONE_COUNTER = 700_000_00

_SET_MARKET_GUC = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti (`is_local=false`).

`audit_log` ga `owner_bootstrap` policy'si ATAYIN berilmagan
(`migrations/entities/__init__.py`), ya'ni EGA ham `audit_read` ning tenant
predikatiga bo'ysunadi: kontekstsiz `SELECT` 0 qator qaytaradi.
"""

_FIRST_AUDIT_ROW = "SELECT id FROM audit_log WHERE market_id = %s ORDER BY id LIMIT 1"


def _next_phone() -> str:
    """Testlar orasida to'qnashmaydigan E.164 telefon (`users.phone_e164` unique)."""
    global _PHONE_COUNTER
    _PHONE_COUNTER += 1
    return f"+9989{_PHONE_COUNTER:08d}"


def _make_market(name: str) -> MarketSeed:
    return MarketSeed(
        id=uuid4(),
        name=name,
        admin_user_id=uuid4(),
        admin_phone=_next_phone(),
        admin_role_id=uuid4(),
        cashier_user_id=uuid4(),
        cashier_phone=_next_phone(),
        cashier_role_id=uuid4(),
        director_user_id=uuid4(),
        director_phone=_next_phone(),
        director_role_id=uuid4(),
        audit_row_id=_AUDIT_ID_PENDING,
    )


def _first_audit_row_id(conn: Connection[TupleRow], market_id: UUID) -> int:
    """Bozorning BIRINCHI audit qatorining kalitini qaytaradi.

    QATOR SUN'IY YARATILMAYDI: a'zolik qatorlari yozilganda `fn_audit_row()`
    triggeri ularni allaqachon jurnalga tushirgan. Qo'shimcha "probe"
    qatori yozish mavjud testlarni buzardi — masalan
    `test_patch_locale_writes_an_audit_row_with_old_and_new` bozordagi
    `update` qatorlarini SANAYDI va sun'iy qator uni ikkiga chiqarardi.
    Ya'ni bu yerda mahsulot yo'lidan tug'ilgan HAQIQIY yozuv olinadi.

    KONTEKST QAYTA BO'SHATILISHI SHART: `conn` autocommit rejimida va
    `set_config(..., false)` qiymati SESSIYA davomida saqlanadi. Uni
    qoldirib ketish `cleanup_two_markets()` ni jimgina buzardi — o'chirish
    faqat bitta bozorning qatorlarini ko'rib, ikkinchisi FK bilan qolib
    ketardi. Bo'sh satr `NULLIF` tufayli "kontekst yo'q" bilan bir xil.
    """
    try:
        conn.execute(_SET_MARKET_GUC, (str(market_id),))
        row = conn.execute(_FIRST_AUDIT_ROW, (str(market_id),)).fetchone()
    finally:
        conn.execute(_SET_MARKET_GUC, ("",))

    if row is None:
        raise AssertionError(
            f"{market_id}: seed audit qatori topilmadi — `fn_audit_row()` triggeri ishlamayapti"
        )
    return int(row[0])


def seed_two_markets(conn: Connection[TupleRow]) -> TwoMarketSeed:
    """Ikki bozor, beshta foydalanuvchi va oltita a'zolik qatorini yozadi.

    `conn` `sbozor_owner` bilan ochilgan va autocommit rejimida bo'lishi
    kerak — ma'lumot boshqa ulanishdagi (`sbozor_app`) testlarga darhol
    ko'rinishi shart.
    """
    market_a = _make_market("A bozori")
    market_b = _make_market("B bozori")
    platform_admin_id = uuid4()
    platform_admin_phone = _next_phone()
    platform_role_ids = {market_a.id: uuid4(), market_b.id: uuid4()}

    for market in (market_a, market_b):
        conn.execute(
            "INSERT INTO markets (id, name) VALUES (%s, %s)",
            (str(market.id), market.name),
        )

    users: list[tuple[str, str, str, bool]] = []
    for market in (market_a, market_b):
        users.append(
            (str(market.admin_user_id), market.admin_phone, f"{market.name} admini", False)
        )
        users.append(
            (str(market.cashier_user_id), market.cashier_phone, f"{market.name} kassiri", False)
        )
        users.append(
            (str(market.director_user_id), market.director_phone, f"{market.name} direktori", False)
        )
    users.append((str(platform_admin_id), platform_admin_phone, "Platforma admini", True))

    for user_id, phone, full_name, is_platform_admin in users:
        conn.execute(
            "INSERT INTO users (id, phone_e164, password_hash, full_name, is_platform_admin) "
            "VALUES (%s, %s, %s, %s, %s)",
            # HAQIQIY Argon2 hash: seed foydalanuvchilari mahsulot yo'lidan
            # (`POST /auth/login`) kira olishi kerak — cross-tenant matritsasi
            # tokenni aynan shu yo'ldan oladi. `users` jadvalida audit
            # triggeri YO'Q (`0002` faqat `user_market_roles` ga ulaydi),
            # ya'ni hash jurnalga tushmaydi.
            (user_id, phone, SEED_PASSWORD_HASH, full_name, is_platform_admin),
        )

    memberships: list[tuple[str, str, str, list[str]]] = []
    for market in (market_a, market_b):
        memberships.append(
            (str(market.admin_role_id), str(market.id), str(market.admin_user_id), ["market_admin"])
        )
        memberships.append(
            (str(market.cashier_role_id), str(market.id), str(market.cashier_user_id), ["cashier"])
        )
        memberships.append(
            (
                str(market.director_role_id),
                str(market.id),
                str(market.director_user_id),
                ["director"],
            )
        )
        memberships.append(
            (
                str(platform_role_ids[market.id]),
                str(market.id),
                str(platform_admin_id),
                ["platform_admin"],
            )
        )

    for role_id, market_id, user_id, roles in memberships:
        conn.execute(
            "INSERT INTO user_market_roles (id, market_id, user_id, roles) VALUES (%s, %s, %s, %s)",
            (role_id, market_id, user_id, roles),
        )

    # Audit kalitlari ENG OXIRIDA o'qiladi: qatorlarni yuqoridagi a'zolik
    # INSERT'lari triggeri yozadi, `_first_audit_row_id()` esa tenant
    # kontekstini sessiya darajasida o'rnatadi — undan keyin bajarilgan
    # har qanday `markets`/`users` yozuvi boshqa policy ostiga tushardi.
    market_a = replace(market_a, audit_row_id=_first_audit_row_id(conn, market_a.id))
    market_b = replace(market_b, audit_row_id=_first_audit_row_id(conn, market_b.id))

    return TwoMarketSeed(
        market_a=market_a,
        market_b=market_b,
        platform_admin_id=platform_admin_id,
        platform_admin_phone=platform_admin_phone,
        platform_admin_role_ids=platform_role_ids,
    )


def cleanup_two_markets(conn: Connection[TupleRow], seed: TwoMarketSeed) -> None:
    """Seed'ni to'liq o'chiradi (FK tartibida).

    ⚠ AVVAL BOZORLAR QORALAMAGA QAYTARILADI VA BUSIZ TOZALASH YIQILADI
    (`0013_market_delete_guard`, WR-02).

    Seed bozorlarni `INSERT INTO markets (id, name)` bilan yaratadi va
    `markets.is_active` `DEFAULT true` — ya'ni ular FAOL. `0013` esa
    `markets` ga `BEFORE DELETE` trigger qo'ydi: faol bozorni o'chirishga
    urinish `23514` (`market ... is active and cannot be deleted`) beradi.
    Ya'ni tozalash oxirgi `DELETE FROM markets` da yiqilardi va har bir
    test qoldiq bozor qoldirardi.

    Bu ZAIFLASHTIRISH EMAS, MAHSULOT QOIDASINING O'ZI: faol bozorni
    o'chirish yo'li ATAYIN yo'q (`market_deactivate()` funksiyasi
    yaratilmagan — sabab `migrations/entities/functions.py::MARKET_ACTIVATE`
    docstringida), va endi bu sxemada ham majburlanadi. Bayroqni tushirish
    bu yerda semantik jihatdan HALOL: qator bir necha satr keyin butunlay
    o'chiriladi.

    Naqsh YANGI EMAS — `fixtures/market_domain.py::cleanup_market_domain()`
    aynan shu qadamni o'zgarmaslik triggerlari uchun 02-04 dan beri
    bajaradi. Farqi shundaki, u yerda `is_active = false` `tariffs`
    o'chirilishi uchun kerak edi, bu yerda esa `markets` ning o'zi uchun.
    """
    market_ids = [str(market.id) for market in seed.markets]
    user_ids = [str(user_id) for user_id in seed.all_user_ids]

    conn.execute(
        "UPDATE markets SET is_active = false WHERE id = ANY(%s::uuid[])",
        (market_ids,),
    )
    conn.execute("DELETE FROM refresh_tokens WHERE market_id = ANY(%s::uuid[])", (market_ids,))
    conn.execute("DELETE FROM user_market_roles WHERE market_id = ANY(%s::uuid[])", (market_ids,))
    conn.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (user_ids,))
    conn.execute("DELETE FROM markets WHERE id = ANY(%s::uuid[])", (market_ids,))
