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

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import TupleRow

__all__ = ["MarketSeed", "TwoMarketSeed", "cleanup_two_markets", "seed_two_markets"]


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

    @property
    def user_ids(self) -> tuple[UUID, ...]:
        return (self.admin_user_id, self.cashier_user_id)


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


# Har bozorda: admin + kassir + platforma admini = 3 a'zolik qatori.
ROLES_PER_MARKET = 3

_PHONE_COUNTER = 700_000_00


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
    )


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
    users.append((str(platform_admin_id), platform_admin_phone, "Platforma admini", True))

    for user_id, phone, full_name, is_platform_admin in users:
        conn.execute(
            "INSERT INTO users (id, phone_e164, password_hash, full_name, is_platform_admin) "
            "VALUES (%s, %s, %s, %s, %s)",
            # Parol hash'i seed uchun ahamiyatsiz: bu testlar RLS va GRANT
            # yo'llarini sinaydi, parol tekshiruvini emas (u `tests/unit`da).
            (user_id, phone, "argon2-seed-placeholder", full_name, is_platform_admin),
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

    return TwoMarketSeed(
        market_a=market_a,
        market_b=market_b,
        platform_admin_id=platform_admin_id,
        platform_admin_phone=platform_admin_phone,
        platform_admin_role_ids=platform_role_ids,
    )


def cleanup_two_markets(conn: Connection[TupleRow], seed: TwoMarketSeed) -> None:
    """Seed'ni to'liq o'chiradi (FK tartibida)."""
    market_ids = [str(market.id) for market in seed.markets]
    user_ids = [str(user_id) for user_id in seed.all_user_ids]

    conn.execute("DELETE FROM refresh_tokens WHERE market_id = ANY(%s::uuid[])", (market_ids,))
    conn.execute("DELETE FROM user_market_roles WHERE market_id = ANY(%s::uuid[])", (market_ids,))
    conn.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (user_ids,))
    conn.execute("DELETE FROM markets WHERE id = ANY(%s::uuid[])", (market_ids,))
