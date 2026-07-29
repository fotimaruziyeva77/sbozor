"""Auth testlari uchun maxsus holatdagi foydalanuvchilar (bloklangan, parol almashtiruvchi).

Bu modul mavjud `two_markets` seed'i USTIGA quriladi:
  * seed foydalanuvchilarining hash'i bir xil, HAQIQIY Argon2 hash bilan
    qayta yoziladi (01-10 dan boshlab `two_markets` allaqachon aynan shu
    hash'ni yozadi, ya'ni bu yozuv endi holatni O'ZGARTIRMAYDI va faqat
    modulning o'z-o'ziga yetarliligini saqlaydi);
  * to'rtta qo'shimcha foydalanuvchi qo'shiladi — BLOKLANGAN (D-08),
    MAJBURIY PAROL ALMASHTIRADIGAN (D-02), oddiy NAZORATCHI (RBAC rad
    etish testini D-02 darvozasidan ajratish uchun, 01-11) va GIBRID
    a'zolik roli (`platform_admin` roli + `is_platform_admin=false`,
    CR-03 regressiya darvozasi); ularsiz o'sha qarorlar umuman
    sinalmagan yoki noto'g'ri sababdan yashil bo'lardi.

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
    """`must_change_password = true` (D-02) — FAQAT parol-darvoza testlari uchun.

    01-11 dan boshlab bu foydalanuvchi hech qanday tenant endpointiga kira
    OLMAYDI: `require_password_current` uni 403 `password_change_required`
    bilan rad etadi. Shuning uchun uni RBAC rad etish testlarida ishlatib
    BO'LMAYDI — o'sha testlar 403 olardi-yu, sababi huquq yetishmasligi
    emas, darvoza bo'lardi (green-for-wrong-reason). RBAC uchun `inspector`
    bor.
    """
    inspector: AuthUser
    """A bozorining nazoratchisi — `must_change=false`, RBAC rad etish testi uchun.

    `must_change` bilan AYNAN BIR XIL rol (`inspector`), farqi faqat D-02
    bayrog'ida. Aynan shu farq `test_inspector_cannot_view_the_audit_log`
    da 403 ning sababini bir ma'noli qiladi: nazoratchida `AUDIT_VIEW`
    YO'Q, parol darvozasi esa umuman qatnashmaydi.
    """
    hybrid_platform_role: AuthUser
    """`roles=["platform_admin"]` a'zoligi, LEKIN `is_platform_admin = false` (CR-03).

    Bunday hisobni 01-11 dan keyin API ORQALI yaratib BO'LMAYDI
    (`_assert_roles_assignable` `platform_admin` ni har doim rad etadi),
    shuning uchun u to'g'ridan-to'g'ri seed qilinadi. Vazifasi —
    `markets.py::list_markets` ning branch MANBASINI qulflash: bu hisobda
    `MARKET_VIEW_ALL` huquqi BOR, bayroq esa YO'Q. Branch huquqqa
    qaytarilsa (CR-03 regressiyasi) u barcha bozorlarni ko'radi va
    `test_market_view_all_without_the_flag_sees_only_its_own_market`
    DARHOL qizaradi.
    """

    @property
    def extra_user_ids(self) -> tuple[UUID, ...]:
        """`two_markets` tozalashi qamramaydigan foydalanuvchilar."""
        return (
            self.blocked.user_id,
            self.must_change.user_id,
            self.inspector.user_id,
            self.hybrid_platform_role.user_id,
        )


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
    """To'rtta maxsus holatdagi foydalanuvchi qo'shadi.

    Quyidagi `UPDATE` 01-10 dan beri holatni O'ZGARTIRMAYDI (`two_markets`
    aynan shu hash'ni yozadi), lekin ATAYIN qoldirilgan: u bu modulning
    "parol haqiqiy hash bilan yozilgan" degan talabini o'z ichida
    saqlaydi va seed manbasi kelajakda o'zgarsa ham buzilmaydi.

    Yangi a'zolar (`inspector`, `hybrid_platform_role`) A bozoriga
    qo'shiladi. Mavjud testlar a'zolikni `in`/`not in` bilan tekshiradi
    (`test_list_users_returns_only_current_market_members`), aniq sanoq
    bilan emas — ya'ni qo'shimcha a'zo ularni buzmaydi.
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
    inspector = _insert_member(
        conn,
        market_id=markets.market_a.id,
        phone=_next_phone(),
        full_name="Nazoratchi",
        roles=["inspector"],
        must_change_password=False,
    )
    hybrid_platform_role = _insert_member(
        conn,
        market_id=markets.market_a.id,
        phone=_next_phone(),
        full_name="Gibrid hisob",
        roles=["platform_admin"],
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
        inspector=inspector,
        hybrid_platform_role=hybrid_platform_role,
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
