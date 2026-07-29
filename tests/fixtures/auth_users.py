"""Auth testlari uchun maxsus holatdagi foydalanuvchilar (bloklangan, parol almashtiruvchi).

Bu modul mavjud `two_markets` seed'i USTIGA quriladi:
  * seed foydalanuvchilarining hash'i bir xil, HAQIQIY Argon2 hash bilan
    qayta yoziladi (01-10 dan boshlab `two_markets` allaqachon aynan shu
    hash'ni yozadi, ya'ni bu yozuv endi holatni O'ZGARTIRMAYDI va faqat
    modulning o'z-o'ziga yetarliligini saqlaydi);
  * ikkita qo'shimcha foydalanuvchi qo'shiladi — BLOKLANGAN (D-08) va
    MAJBURIY PAROL ALMASHTIRADIGAN (D-02); ularsiz o'sha ikki qaror
    umuman sinalmagan bo'lardi.

PAROL VA HASH `fixtures/two_markets.py` DAN OLINADI. Ikki modulda ikki
literal bo'lganda ular jimgina ajralib ketardi va `MarketSeed.admin_password`
`auth_seed` faol bo'lgan testlarda yolg'on qiymatga aylanardi. Hash ham
BIR MARTA hisoblanadi (~100 ms) — har testda `hash_password()` chaqirish
butun to'plamga o'nlab soniya qo'shardi va hech qanday yangi narsani
isbotlamasdi (Argon2 ning o'zi `tests/unit/test_password.py` da sinalgan).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fixtures.two_markets import SEED_PASSWORD, SEED_PASSWORD_HASH

if TYPE_CHECKING:
    from psycopg import Connection
    from psycopg.rows import TupleRow

    from fixtures.two_markets import TwoMarketSeed

__all__ = ["PASSWORD", "AuthSeed", "AuthUser", "cleanup_auth_users", "seed_auth_users"]

PASSWORD = SEED_PASSWORD
"""Barcha seed foydalanuvchilari uchun bitta parol (yagona manba — `two_markets`)."""

_PASSWORD_HASH = SEED_PASSWORD_HASH

# `two_markets` `+99897…` diapazonini ishlatadi; bu yerdagi qo'shimcha
# foydalanuvchilar `+99890…` da — to'qnashuv bo'lmasligi uchun.
_PHONE_COUNTER = 1_000_000


def _next_phone() -> str:
    """`users.phone_e164` unique — testlar orasida to'qnashmaydigan E.164."""
    global _PHONE_COUNTER
    _PHONE_COUNTER += 1
    return f"+99890{_PHONE_COUNTER:07d}"


@dataclass(frozen=True)
class AuthUser:
    """Login qila oladigan test foydalanuvchisi."""

    user_id: UUID
    phone: str


@dataclass(frozen=True)
class AuthSeed:
    """Auth oqimlari uchun to'liq manzara: ikki bozor + beshta rol holati."""

    password: str
    market_a_id: UUID
    market_a_name: str
    market_b_id: UUID
    market_b_name: str
    market_admin: AuthUser
    """A bozorining admini — AYNAN BITTA a'zolik (bozor avtomatik tanlanadi)."""
    cashier: AuthUser
    """A bozorining kassiri — eng tor huquqli rol."""
    other_market_admin: AuthUser
    """B bozorining admini — cross-tenant testlar uchun."""
    platform_admin: AuthUser
    """Ikkala bozorga a'zo + `is_platform_admin` (D-06 oqimi)."""
    blocked: AuthUser
    """`is_active = false` (D-08)."""
    must_change: AuthUser
    """`must_change_password = true` (D-02)."""

    @property
    def extra_user_ids(self) -> tuple[UUID, ...]:
        """`two_markets` tozalashi qamramaydigan foydalanuvchilar."""
        return (self.blocked.user_id, self.must_change.user_id)


def _insert_member(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    phone: str,
    full_name: str,
    roles: list[str],
    is_active: bool = True,
    must_change_password: bool = False,
) -> AuthUser:
    """Foydalanuvchi + a'zolik qatorini yozadi (`sbozor_owner` bilan)."""
    user_id = uuid4()
    conn.execute(
        "INSERT INTO users (id, phone_e164, password_hash, full_name, is_active, "
        "must_change_password) VALUES (%s, %s, %s, %s, %s, %s)",
        (str(user_id), phone, _PASSWORD_HASH, full_name, is_active, must_change_password),
    )
    conn.execute(
        "INSERT INTO user_market_roles (id, market_id, user_id, roles) VALUES (%s, %s, %s, %s)",
        (str(uuid4()), str(market_id), str(user_id), roles),
    )
    return AuthUser(user_id=user_id, phone=phone)


def seed_auth_users(conn: Connection[TupleRow], markets: TwoMarketSeed) -> AuthSeed:
    """Ikkita maxsus holatdagi foydalanuvchi qo'shadi (bloklangan, parol almashtiruvchi).

    Quyidagi `UPDATE` 01-10 dan beri holatni O'ZGARTIRMAYDI (`two_markets`
    aynan shu hash'ni yozadi), lekin ATAYIN qoldirilgan: u bu modulning
    "parol haqiqiy hash bilan yozilgan" degan talabini o'z ichida
    saqlaydi va seed manbasi kelajakda o'zgarsa ham buzilmaydi.
    """
    conn.execute(
        "UPDATE users SET password_hash = %s WHERE id = ANY(%s::uuid[])",
        (_PASSWORD_HASH, [str(user_id) for user_id in markets.all_user_ids]),
    )

    blocked = _insert_member(
        conn,
        market_id=markets.market_a.id,
        phone=_next_phone(),
        full_name="Bloklangan kassir",
        roles=["cashier"],
        is_active=False,
    )
    must_change = _insert_member(
        conn,
        market_id=markets.market_a.id,
        phone=_next_phone(),
        full_name="Yangi nazoratchi",
        roles=["inspector"],
        must_change_password=True,
    )

    return AuthSeed(
        password=PASSWORD,
        market_a_id=markets.market_a.id,
        market_a_name=markets.market_a.name,
        market_b_id=markets.market_b.id,
        market_b_name=markets.market_b.name,
        market_admin=AuthUser(
            user_id=markets.market_a.admin_user_id, phone=markets.market_a.admin_phone
        ),
        cashier=AuthUser(
            user_id=markets.market_a.cashier_user_id, phone=markets.market_a.cashier_phone
        ),
        other_market_admin=AuthUser(
            user_id=markets.market_b.admin_user_id, phone=markets.market_b.admin_phone
        ),
        platform_admin=AuthUser(
            user_id=markets.platform_admin_id, phone=markets.platform_admin_phone
        ),
        blocked=blocked,
        must_change=must_change,
    )


def cleanup_auth_users(conn: Connection[TupleRow], seed: AuthSeed) -> None:
    """Qo'shimcha foydalanuvchilarni o'chiradi.

    A'zolik va refresh token qatorlari `ON DELETE CASCADE` bilan o'zi
    ketadi. `audit_log` qatorlari QOLADI — jadval append-only va ularni
    o'chirish IMKONSIZ (bu aynan kutilgan xulq); testlar shu sababli
    yozuvlarni har safar YANGI `market_id`/`phone` bo'yicha filtrlaydi.
    """
    conn.execute(
        "DELETE FROM users WHERE id = ANY(%s::uuid[])",
        ([str(user_id) for user_id in seed.extra_user_ids],),
    )
