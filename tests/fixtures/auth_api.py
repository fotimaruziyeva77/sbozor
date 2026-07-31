"""Auth API testlari uchun umumiy yordamchilar (URL'lar, audit o'qish, DB holati).

Bu modul `tests/fixtures/` da yashaydi, `tests/integration/` da EMAS:
`tests/` namespace paket va `conftest.py` ni pytest alohida modul sifatida
yuklaydi, ya'ni testlar orasida ulashilgan kod uchun yagona xavfsiz joy —
`fixtures` paketi (01-05 deviatsiya #5 da o'rnatilgan qoida).

Yordamchilar ATAYIN yupqa: ular test mantiqini YASHIRMAYDI, faqat
takrorlanadigan SQL va URL satrlarini bir joyga yig'adi.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy import Row
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from fixtures import TenantSessionFactory

__all__ = [
    "CHANGE_PASSWORD_URL",
    "LOGIN_URL",
    "LOGOUT_URL",
    "ME_URL",
    "REFRESH_URL",
    "SELECT_MARKET_URL",
    "audit_rows",
    "draft_market",
    "global_audit_rows",
    "login",
    "refresh_token_row",
    "set_user_active",
]

LOGIN_URL = "/api/v1/auth/login"
SELECT_MARKET_URL = "/api/v1/auth/select-market"
REFRESH_URL = "/api/v1/auth/refresh"  # noqa: S105 — marshrut, sir emas
LOGOUT_URL = "/api/v1/auth/logout"
CHANGE_PASSWORD_URL = "/api/v1/auth/change-password"  # noqa: S105 — marshrut, sir emas
ME_URL = "/api/v1/auth/me"

_TENANT_AUDIT = text(
    "SELECT action, actor_user_id, actor_label, table_name, source, new_value "
    "FROM audit_log WHERE market_id = :market_id AND action = :action ORDER BY id"
)

_GLOBAL_AUDIT = """
    SELECT action, source, new_value
    FROM audit_log
    WHERE market_id IS NULL AND action = %s AND new_value ->> 'phone' = %s
    ORDER BY id
"""

_REFRESH_FIND = text(
    "SELECT market_id, user_id, family_id, expires_at, revoked_at, replaced_by_jti "
    "FROM auth_refresh_find(:jti)"
)

_SET_ACTIVE = text("SELECT auth_set_active(:user_id, :is_active)")


async def login(client: httpx.AsyncClient, phone: str, password: str) -> httpx.Response:
    """`POST /auth/login` — testlarning eng ko'p takrorlanadigan qadami."""
    return await client.post(LOGIN_URL, json={"phone": phone, "password": password})


async def audit_rows(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
    *,
    action: str,
) -> list[Row[Any]]:
    """Bozorga tegishli audit qatorlari — ILOVA roli va tenant konteksti bilan.

    Superuser bilan O'QILMAYDI: audit ekrani (D-11) aynan shu yo'ldan
    ma'lumot oladi, ya'ni test mahsulot yo'lini sinaydi.
    """
    async with tenant_session(market_id) as session:
        result = await session.execute(
            _TENANT_AUDIT, {"market_id": str(market_id), "action": action}
        )
        return list(result.fetchall())


def global_audit_rows(
    conn: Connection[TupleRow],
    *,
    action: str,
    phone: str,
) -> list[tuple[Any, ...]]:
    """`market_id IS NULL` yozuvlari — KLASTER SUPERUSERI bilan.

    Bunday qatorlar `audit_read` policy'si ostida NA ilova, NA ega roliga
    ko'rinadi (bu ataylab: platforma-global yozuvlar umumiy o'qish yuzasi
    orqali berilmaydi). Ularni tekshirishning boshqa yo'li hozircha yo'q —
    mahsulot yo'li (tor `SECURITY DEFINER` funksiya) 01-07 rejasida.

    `phone` bo'yicha filtr MAJBURIY: bu qatorlarni o'chirib bo'lmaydi va
    ular sessiya davomida to'planadi, ya'ni filtrsiz test boshqa testning
    yozuvini ko'rardi.
    """
    return list(conn.execute(_GLOBAL_AUDIT, (action, phone)).fetchall())


async def refresh_token_row(
    sessionmaker: async_sessionmaker[AsyncSession],
    jti: str,
) -> Row[Any] | None:
    """`refresh_tokens` qatori — `SECURITY DEFINER` funksiyasi orqali.

    To'g'ridan-to'g'ri `SELECT` ISHLAMAYDI: jadval tenant-scoped va bu
    yerda tenant konteksti yo'q (aynan mahsulot yo'lidagi holat).
    """
    async with sessionmaker() as session:
        result = await session.execute(_REFRESH_FIND, {"jti": jti})
        return result.one_or_none()


_INSERT_DRAFT_MARKET = "INSERT INTO markets (id, name, is_active) VALUES (%s, %s, false)"
_INSERT_MEMBERSHIP = (
    "INSERT INTO user_market_roles (id, market_id, user_id, roles) VALUES (%s, %s, %s, %s)"
)
_DELETE_MEMBERSHIPS = "DELETE FROM user_market_roles WHERE market_id = %s"
_DELETE_REFRESH = "DELETE FROM refresh_tokens WHERE market_id = %s"
_DELETE_MARKET = "DELETE FROM markets WHERE id = %s"


@contextmanager
def draft_market(
    conn: Connection[TupleRow],
    *,
    name: str = "Qoralama bozor",
    member_id: UUID | None = None,
    roles: list[str] | None = None,
) -> Iterator[UUID]:
    """QORALAMA bozor (`markets.is_active = false`) — usta 1-qadamidan keyingi holat.

    `sbozor_owner` bilan yoziladi (`two_markets` seed'i bilan bir xil sabab):
    `markets` app-rolga faqat `SELECT` beradi, `user_market_roles` ga yozish
    esa avval tenant kontekstini talab qilardi — ya'ni seed o'zi sinayotgan
    mexanizmga tayanib qolardi.

    `member_id` berilsa o'sha foydalanuvchiga a'zolik qatori ham yoziladi:
    UI-SPEC §12.1.1 X-2 dagi holat aynan shu — qoralama bozorga tayinlangan
    bozor admini uni ro'yxatda ALLAQACHON ko'radi va savol faqat uning
    to'g'ri YORLIQLANISHIDA.

    Teardown FK tartibida: sessiya qatorlari -> a'zolik -> bozor.
    `audit_log` qatorlari ATAYIN qoladi — jadval append-only va uni
    o'chirib bo'lmaydi (`cleanup_two_markets` bilan bir xil qoida).
    """
    market_id = uuid4()
    conn.execute(_INSERT_DRAFT_MARKET, (str(market_id), name))
    if member_id is not None:
        conn.execute(
            _INSERT_MEMBERSHIP,
            (str(uuid4()), str(market_id), str(member_id), roles or ["market_admin"]),
        )
    try:
        yield market_id
    finally:
        conn.execute(_DELETE_REFRESH, (str(market_id),))
        conn.execute(_DELETE_MEMBERSHIPS, (str(market_id),))
        conn.execute(_DELETE_MARKET, (str(market_id),))


async def set_user_active(
    sessionmaker: async_sessionmaker[AsyncSession],
    user_id: UUID,
    *,
    is_active: bool,
) -> None:
    """Bloklaydi/tiklaydi — 01-07 dagi boshqaruv endpointi bilan BIR XIL yo'ldan.

    `UPDATE users ...` to'g'ridan-to'g'ri bajarilmaydi: `sbozor_app` da
    o'sha jadvalga huquq YO'Q va test aynan shu cheklovni hurmat qilishi
    kerak, aks holda u mahsulot qila olmaydigan narsani qilardi.
    """
    async with sessionmaker() as session:
        await session.execute(_SET_ACTIVE, {"user_id": str(user_id), "is_active": is_active})
        await session.commit()
