"""Boshqaruv API testlari uchun umumiy yordamchilar (URL'lar, sessiya, audit).

`tests/fixtures/` da yashaydi, `tests/integration/` da EMAS — 01-05
deviatsiya #5 da o'rnatilgan qoida: `tests/` namespace paket va pytest
`conftest.py` ni ALOHIDA modul sifatida yuklaydi, ya'ni testlar orasida
ulashilgan kod uchun yagona xavfsiz joy shu paket.

Yordamchilar ATAYIN yupqa: ular test mantiqini yashirmaydi, faqat
takrorlanadigan URL va sessiya qadamlarini bir joyga yig'adi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from fixtures.auth_api import LOGIN_URL, SELECT_MARKET_URL, login

if TYPE_CHECKING:
    from uuid import UUID

    import httpx
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy import Row

    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed

__all__ = [
    "AUDIT_URL",
    "CALENDAR_URL",
    "CATEGORIES_URL",
    "MARKETS_URL",
    "PROFILE_URL",
    "STALLS_URL",
    "TARIFFS_URL",
    "TEST_PHONE_PREFIX",
    "USERS_URL",
    "ZONES_URL",
    "audit_entries",
    "bearer",
    "cleanup_test_users",
    "insert_audit_probe",
    "new_phone",
    "platform_admin_headers",
    "session_headers",
]

USERS_URL = "/api/v1/users"
PROFILE_URL = "/api/v1/me"
MARKETS_URL = "/api/v1/markets"
AUDIT_URL = "/api/v1/audit"

# --- 2-faza: bozor domeni reestrlari ---
#
# URL'lar SHU YERDA, testlarda literal sifatida EMAS: prefiks o'zgarganda
# (masalan `/api/v2/`) bitta joy tahrirlanadi va o'nlab test fayli
# ergashadi. 1-fazadagi to'rttasi bilan aynan bir xil qoida.
ZONES_URL = "/api/v1/zones"
CATEGORIES_URL = "/api/v1/categories"
STALLS_URL = "/api/v1/stalls"
TARIFFS_URL = "/api/v1/tariffs"
CALENDAR_URL = "/api/v1/calendar"

TEST_PHONE_PREFIX = "+99893"
"""Testlar YARATADIGAN foydalanuvchilarning telefon diapazoni.

Seed'lar `+99897…` (`two_markets`) va `+99890…` (`auth_users`) ni
ishlatadi, ya'ni bu uchinchi diapazon ular bilan to'qnashmaydi va
`cleanup_test_users()` uni aniq nishonga oladi.
"""

_PHONE_COUNTER = 3_000_000


def new_phone() -> str:
    """`users.phone_e164` unique — har chaqiruvda yangi E.164 raqam.

    API orqali yaratilgan foydalanuvchini `two_markets` teardown'i
    O'CHIRMAYDI (u faqat o'z seed'ini biladi), ya'ni raqam qayta
    ishlatilsa keyingi test kutilmagan `409 phone_taken` olardi.
    """
    global _PHONE_COUNTER
    _PHONE_COUNTER += 1
    return f"{TEST_PHONE_PREFIX}{_PHONE_COUNTER:07d}"


def cleanup_test_users(conn: Connection[TupleRow]) -> None:
    """Testlar yaratgan foydalanuvchilarni o'chiradi (`sbozor_owner` bilan).

    A'zolik va refresh token qatorlari `ON DELETE CASCADE` bilan ketadi.
    `audit_log` qatorlari QOLADI — jadval append-only va ularni o'chirish
    imkonsiz (aynan kutilgan xulq).

    Sxema hali qurilmagan bo'lsa JIMGINA qaytadi: bu tozalash `autouse`
    fixture'dan chaqiriladi va `tests/integration` da migratsiyaga umuman
    tegmaydigan testlar ham bor (masalan frontend fayli bilan
    solishtirish). Ularni `migrated` ga bog'lab qo'yish tozalash uchun
    butun bazani ko'tarishga majbur qilardi.
    """
    row = conn.execute("SELECT to_regclass('public.users')").fetchone()
    if row is None or row[0] is None:
        return
    conn.execute("DELETE FROM users WHERE phone_e164 LIKE %s", (f"{TEST_PHONE_PREFIX}%",))


def bearer(token: str) -> dict[str, str]:
    """`Authorization` sarlavhasi."""
    return {"Authorization": f"Bearer {token}"}


async def session_headers(
    client: httpx.AsyncClient,
    phone: str,
    password: str,
    *,
    market_id: UUID | None = None,
) -> dict[str, str]:
    """Login (kerak bo'lsa + bozor tanlash) -> `Authorization` sarlavhasi.

    `market_id` platforma admini uchun MAJBURIY: uning a'zoligi bir nechta,
    shuning uchun `/auth/login` bozorni avtomatik tanlamaydi va tokenda
    `mid` bo'lmaydi (01-06). Bunday token bilan har qanday tenant
    endpointi `409 market_not_selected` beradi.
    """
    response = await login(client, phone, password)
    if response.status_code != 200:
        raise AssertionError(f"{LOGIN_URL} kutilmagan javob berdi: {response.status_code}")
    token = response.json()["access_token"]

    if market_id is not None:
        selected = await client.post(
            SELECT_MARKET_URL,
            json={"market_id": str(market_id)},
            headers=bearer(token),
        )
        if selected.status_code != 200:
            raise AssertionError(
                f"{SELECT_MARKET_URL} kutilmagan javob berdi: {selected.status_code}"
            )
        token = selected.json()["access_token"]

    return bearer(token)


async def platform_admin_headers(
    client: httpx.AsyncClient,
    seed: AuthSeed,
    market_id: UUID | None = None,
) -> dict[str, str]:
    """Platforma admini sessiyasi (D-06: login -> bozor tanlash)."""
    return await session_headers(
        client,
        seed.platform_admin.phone,
        seed.password,
        market_id=market_id if market_id is not None else seed.market_a_id,
    )


_AUDIT_ENTRIES = text(
    "SELECT id, action, actor_user_id, actor_label, table_name, row_id, "
    "old_value, new_value, changed_keys, source "
    "FROM audit_log WHERE market_id = :market_id ORDER BY id"
)


def insert_audit_probe(
    conn: Connection[TupleRow],
    market_id: UUID,
    *,
    table_name: str,
    new_value: str,
    action: str = "update",
) -> None:
    """Bozorga sun'iy audit qatori qo'yadi (`sbozor_owner` bilan).

    NEGA KERAK: maskalash testi jurnalda SEZGIR KALIT bo'lgan qatorni
    talab qiladi, mahsulot kodi esa bunday qatorni HECH QACHON yozmaydi
    (parol ham, hash ham auditga tushmaydi). Ya'ni maskalashni haqiqiy
    ma'lumot bilan sinab bo'lmaydi — u aynan "kimdir bir kun sezgir
    maydonni auditga yozib qo'ysa" holatiga qarshi himoya.

    `audit_append` policy'si `WITH CHECK (true)` va `TO` bandisiz, ya'ni
    ega ham yoza oladi (01-05 da hujjatlashtirilgan qaror).
    """
    conn.execute(
        "INSERT INTO audit_log (market_id, action, table_name, new_value, source) "
        "VALUES (%s, %s, %s, %s::jsonb, 'app')",
        (str(market_id), action, table_name, new_value),
    )


async def audit_entries(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
) -> list[Row[Any]]:
    """Bozorning BARCHA audit qatorlari — ILOVA roli va tenant konteksti bilan.

    Superuser bilan O'QILMAYDI: audit ekrani (D-11) aynan shu yo'ldan
    ma'lumot oladi, ya'ni test mahsulot yo'lini sinaydi.
    """
    async with tenant_session(market_id) as session:
        result = await session.execute(_AUDIT_ENTRIES, {"market_id": str(market_id)})
        return list(result.fetchall())
