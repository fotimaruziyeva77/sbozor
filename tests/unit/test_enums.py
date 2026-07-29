"""`sbozor_core.enums` — qiymat kontraktini qulflaydi.

Bu enum qiymatlari DB ustunlarida matn sifatida yashaydi va JWT claim'lari
orqali frontend'ga uzatiladi. Ya'ni ularni o'zgartirish — migratsiya + token
bekor qilish. Shuning uchun qiymatlar shu yerda literal sifatida yozilgan:
test "kod nima qilsa shuni tasdiqlash" emas, KONTRAKTni qulflash uchun.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sbozor_core.enums import ActorKind, AuditAction, AuditSource, Locale, Role

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTING_TS = REPO_ROOT / "frontend" / "src" / "i18n" / "routing.ts"


def test_role_has_exactly_five_panel_roles() -> None:
    """Sotuvchi (`vendor`) roli bu yerda YO'Q — u Telegram-bot identifikatori."""
    assert [role.value for role in Role] == [
        "platform_admin",
        "director",
        "market_admin",
        "cashier",
        "inspector",
    ]


def test_locale_values_match_frontend_contract() -> None:
    assert [locale.value for locale in Locale] == ["uz-Latn", "uz-Cyrl", "ru"]


def test_locale_matches_frontend_routing_ts() -> None:
    """Backend `Locale` va frontend `routing.ts` drift qilmasligi kerak.

    Bu ikki ro'yxat ajralib ketsa, foydalanuvchi profilida saqlangan til
    frontend'da mavjud bo'lmaydi va sahifa 404 yoki standart tilga tushadi —
    bu esa faqat qo'lda sinovda ko'rinadi.
    """
    if not ROUTING_TS.exists():
        pytest.skip("frontend/src/i18n/routing.ts topilmadi (backend-only checkout)")

    source = ROUTING_TS.read_text(encoding="utf-8")
    match = re.search(r"locales:\s*\[([^\]]*)\]", source)
    assert match is not None, "routing.ts dagi `locales:` ro'yxati topilmadi"

    frontend_locales = re.findall(r'["\']([^"\']+)["\']', match.group(1))
    assert frontend_locales == [locale.value for locale in Locale]


def test_audit_action_db_ops_are_lowercase() -> None:
    """DB-trigger `lower(TG_OP)` yozadi — ilova qiymatlari mos bo'lishi shart."""
    assert AuditAction.INSERT.value == "insert"
    assert AuditAction.UPDATE.value == "update"
    assert AuditAction.DELETE.value == "delete"


def test_audit_action_covers_auth_lifecycle() -> None:
    values = {action.value for action in AuditAction}
    assert {
        "login",
        "login_failed",
        "logout",
        "market_selected",
        "password_reset",
        "password_changed",
        "user_blocked",
        "user_unblocked",
        "refresh_reuse_detected",
        "read",
    } <= values


def test_audit_source_and_actor_kind_match_sql_defaults() -> None:
    """`fn_audit_row()` da yozilgan literal qiymatlar bilan aynan bir xil."""
    assert AuditSource.DB_TRIGGER.value == "db_trigger"
    assert AuditSource.APP.value == "app"
    assert ActorKind.USER.value == "user"
    assert ActorKind.SYSTEM.value == "system"


@pytest.mark.parametrize(
    ("member", "expected"),
    [(Role.CASHIER, "cashier"), (Locale.RU, "ru"), (ActorKind.SYSTEM, "system")],
)
def test_str_enum_members_render_as_their_value(member: str, expected: str) -> None:
    """`StrEnum` SQL parametri va JSON qiymati sifatida konversiyasiz ketadi.

    Oddiy `Enum` bo'lganda `f"{member}"` -> `"Role.CASHIER"` bo'lardi va bu
    qiymat jimgina DB'ga yozilardi.
    """
    assert isinstance(member, str)
    assert member == expected
    assert f"{member}" == expected
