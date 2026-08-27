"""`sbozor_core.enums` — qiymat kontraktini qulflaydi.

Bu enum qiymatlari DB ustunlarida matn sifatida yashaydi va JWT claim'lari
orqali frontend'ga uzatiladi. Ya'ni ularni o'zgartirish — migratsiya + token
bekor qilish. Shuning uchun qiymatlar shu yerda literal sifatida yozilgan:
test "kod nima qilsa shuni tasdiqlash" emas, KONTRAKTni qulflash uchun.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

import pytest
from sbozor_core import enums as enums_module
from sbozor_core.enums import (
    ActorKind,
    AuditAction,
    AuditSource,
    Locale,
    OutboxKind,
    OutboxRecipientKind,
    OutboxStatus,
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
    Role,
    StallStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTING_TS = REPO_ROOT / "frontend" / "src" / "i18n" / "routing.ts"

PHASE_7_ENUMS: tuple[type[StrEnum], ...] = (
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
    OutboxKind,
    OutboxRecipientKind,
    OutboxStatus,
)
"""7-faza qo'shgan besh enum — reyestr to'liqligi darvozasining kirishi.

⚠ Ular BU YERDA sanaladi, chunki `__all__` reyestri UNUTILISHI mumkin
bo'lgan yagona joy. Yopiqlik (to'plam tengligi) esa BOSHQA faylda —
`tests/unit/test_reconciliation_enums.py`: bu yerda «ro'yxatga olinganmi»,
u yerda «to'plami yopiqmi» o'lchanadi va ikkalasi mustaqil buziladi.
"""


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


def test_stall_status_has_exactly_four_states() -> None:
    """A4 + 0028: `active` / `maintenance` / `closed` / `fair` — aynan to'rtta.

    Bu test ATAYIN qattiq va u 0028 da AYNAN kutilganidek qizardi: yangi
    holat qo'shilishi billing qoidasini o'zgartiradi va o'sha savolga
    javob HUJJATLASHTIRILDI — `fair` (yarmarka) rastaga hisob YOZILMAYDI,
    `resolve_stall_day_money()` unga `fair_stall` sababi bilan
    `amount = None` beradi (enum docstringi va 0028 migratsiyasi).
    """
    assert [status.value for status in StallStatus] == [
        "active",
        "maintenance",
        "closed",
        "fair",
    ]


def test_stall_status_is_a_closed_set() -> None:
    """`STALL_STATUS_CHECK` shu to'plamdan hosil qilinadi — DB uni qulflaydi."""
    assert {status.value for status in StallStatus} == {
        "active",
        "maintenance",
        "closed",
        "fair",
    }
    assert len(StallStatus) == 4


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


def test_every_enum_is_registered_in_all() -> None:
    """`sbozor_core.enums` dagi HAR `StrEnum` `__all__` reyestrida bor.

    =========================================================================
    ⛔ DARVOZA REYESTRDAN EMAS, MODULDAN YURADI va bu farq butun mazmuni.

    `__all__` ni o'qib «har nom modulda bormi?» deb tekshirish TESKARI
    yo'nalish va u hech nimani ushlamaydi: unutilgan enum reyestrda ham
    yo'q, ya'ni tekshiruv uni umuman ko'rmasdi. Shuning uchun manba —
    modul o'zi (`vars(...)`), reyestr esa KUTILMA.

    Nima buziladi: `__all__` ga tushmagan enum `from sbozor_core.enums
    import *` bilan kelmaydi va `ruff` ning `F401` qoidasi uni «ishlatilmagan
    import» deb ko'rsatadi — natijada keyingi ijrochi uni «o'lik kod» deb
    o'chirib, DB'dagi `CHECK` ni manbasiz qoldirardi.
    =========================================================================
    """
    declared = set(enums_module.__all__)
    defined = {
        name
        for name, value in vars(enums_module).items()
        if isinstance(value, type) and issubclass(value, StrEnum) and value is not StrEnum
    }

    missing = defined - declared
    assert not missing, (
        f"`sbozor_core.enums.__all__` ga qo'shilmagan enum(lar): {sorted(missing)} — "
        "reyestrga tushmagan enum `import *` bilan kelmaydi va `ruff` uni "
        "«ishlatilmagan» deb ko'rsatadi."
    )

    # TESKARI YO'NALISH: reyestrda bor, lekin modulda YO'Q nom `import *` ni
    # `AttributeError` bilan yiqitardi va bu faqat iste'molchi servisda
    # ko'rinardi (`cv-service` / `bot-service` startup'ida).
    stale = {name for name in declared if not hasattr(enums_module, name)}
    assert not stale, f"`__all__` da mavjud bo'lmagan nom(lar): {sorted(stale)}"


@pytest.mark.parametrize("enum_cls", PHASE_7_ENUMS, ids=lambda cls: cls.__name__)
def test_phase_7_enums_are_in_the_registry(enum_cls: type[StrEnum]) -> None:
    """Beshala yangi enum reyestrda NOMMA-NOM (yuqoridagi darvozaning jufti).

    ⚠ Umumiy darvoza (`test_every_enum_is_registered_in_all`) yolg'iz o'zi
    yetarli emas: u modulning O'ZIDAN yuradi, ya'ni enum MODULDAN butunlay
    o'chirilsa ham yashil qolardi (yo'q narsa reyestrda ham yo'q). Bu test
    esa nomni LITERAL talab qiladi — o'chirish endi ko'rinadigan qarorga
    aylanadi.
    """
    assert enum_cls.__name__ in enums_module.__all__
    assert getattr(enums_module, enum_cls.__name__) is enum_cls


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
