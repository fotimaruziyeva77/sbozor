"""Audit YOZUVI — ORM yo'li ham, xom SQL yo'li ham qamrab olinganmi (D-10).

=============================================================================
BU FAYLNING ENG MUHIM TESTI — `test_raw_sql_is_audited`.

RESEARCH Pitfall 5: `before_flush` kabi ORM hook'i bulk UPDATE'ni, xom
`session.execute(text(...))` ni va migratsiyalarni UMUMAN ko'rmaydi — ya'ni
aynan texnik savodli insider ishlatadigan yo'llarni. Shuning uchun audit
DB-trigger bilan yoziladi va bu fayl ikkala yo'lni ham alohida isbotlaydi:

  * ORM yo'li  -> `session.add(UserMarketRole(...))` + `flush()`
  * xom yo'li  -> `session.execute(text("UPDATE user_market_roles SET ..."))`

Ikkinchisida hech qanday ORM obyekti yaratilmaydi va `flush()` chaqirilmaydi,
ya'ni ORM abstraksiyasi HAQIQATAN chetlab o'tiladi.
=============================================================================

Seed haqida: `two_markets` fixture'i a'zolik qatorlarini `sbozor_owner` bilan
yozadi, ya'ni har bozorda uchtadan audit qatori ALLAQACHON mavjud bo'ladi
(trigger ega yo'lida ham ishlaydi). Shuning uchun har bir test o'z qatorini
`row_id` bo'yicha filtrlaydi, umumiy sanoqqa tayanmaydi.
"""

from __future__ import annotations

from uuid import UUID

from fixtures import TenantSessionFactory
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import ActorKind, AuditAction, AuditSource
from sbozor_core.models import AuditLog, UserMarketRole
from sqlalchemy import select, text

UPDATE_ROLES_RAW = text("UPDATE user_market_roles SET roles = :roles WHERE id = :role_id")
NOOP_UPDATE_RAW = text("UPDATE user_market_roles SET roles = roles WHERE id = :role_id")
DELETE_MEMBERSHIP_RAW = text("DELETE FROM user_market_roles WHERE id = :role_id")


async def _audit_rows(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
    row_id: UUID,
    action: AuditAction | None = None,
) -> list[AuditLog]:
    """Berilgan qator uchun audit yozuvlari — TENANT KONTEKSTI ostida.

    `audit_read` policy'si tenant-scoped, shuning uchun o'qish ham
    `app.market_id` talab qiladi (`sbozor_app` roli bilan).

    `action` filtri KERAK: `two_markets` seed'i a'zolik qatorini yozganda
    trigger allaqachon `insert` yozuvini qo'yadi, ya'ni mavjud qator ustida
    ishlaydigan test uchun `row_id` bo'yicha filtr YOLG'IZ O'ZI yetarli emas.
    """
    conditions = [AuditLog.table_name == "user_market_roles", AuditLog.row_id == row_id]
    if action is not None:
        conditions.append(AuditLog.action == action)

    async with tenant_session(market_id) as session:
        result = await session.execute(select(AuditLog).where(*conditions).order_by(AuditLog.id))
        return list(result.scalars().all())


async def test_orm_insert_writes_one_audit_row(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """ORM orqali qo'shilgan a'zolik bitta to'liq audit qatorini hosil qiladi.

    Aktor va `request_id` GUC'lardan olinadi — ya'ni audit yozuvi HTTP
    so'rovi bilan `request_id` orqali bog'lanadi va "kim?" savoli javobsiz
    qolmaydi.
    """
    market = two_markets.market_a
    actor = market.admin_user_id
    # B bozori admini A bozorida HALI a'zo emas — ya'ni yangi a'zolik uchun
    # to'g'ri nomzod (`UNIQUE(market_id, user_id)` buzilmaydi).
    new_member = two_markets.market_b.admin_user_id

    async with tenant_session(market.id, actor, request_id="req-insert") as session:
        membership = UserMarketRole(market_id=market.id, user_id=new_member, roles=["cashier"])
        session.add(membership)
        await session.flush()
        role_id = membership.id

    rows = await _audit_rows(tenant_session, market.id, role_id)

    assert len(rows) == 1, f"bitta audit qatori kutilgan, {len(rows)} ta topildi"
    entry = rows[0]
    assert entry.action == AuditAction.INSERT
    assert entry.source == AuditSource.DB_TRIGGER
    assert entry.table_name == "user_market_roles"
    assert entry.market_id == market.id
    assert entry.actor_user_id == actor
    assert entry.actor_kind == ActorKind.USER
    assert entry.request_id == "req-insert"
    assert entry.old_value is None
    assert entry.new_value is not None
    assert entry.new_value["roles"] == ["cashier"]
    # INSERT da "nima o'zgardi" savolining ma'nosi yo'q — butun qator yangi.
    assert entry.changed_keys is None


async def test_update_records_only_changed_keys(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """`changed_keys` faqat HAQIQATAN o'zgargan ustunlarni beradi.

    Busiz audit qatorini o'qiyotgan odam ikkita JSONB'ni ko'z bilan
    solishtirishi kerak bo'lardi va nizoda "nima o'zgardi" savoli javobsiz
    qolardi.
    """
    market = two_markets.market_a
    role_id = market.cashier_role_id

    async with tenant_session(market.id, market.admin_user_id) as session:
        membership = await session.get_one(UserMarketRole, role_id)
        membership.roles = ["cashier", "inspector"]
        await session.flush()

    rows = await _audit_rows(tenant_session, market.id, role_id, AuditAction.UPDATE)
    assert len(rows) == 1
    entry = rows[0]

    assert entry.changed_keys is not None
    assert "roles" in entry.changed_keys
    # ORM `updated_at` ni `onupdate` bilan yangilaydi, shuning uchun u
    # ro'yxatda bo'lishi MUMKIN — lekin tegilmagan ustunlar BO'LMASLIGI SHART.
    assert set(entry.changed_keys) <= {"roles", "updated_at"}, (
        f"tegilmagan ustunlar `changed_keys` ga tushdi: {entry.changed_keys}"
    )
    assert entry.old_value is not None and entry.new_value is not None
    assert entry.old_value["roles"] == ["cashier"]
    assert entry.new_value["roles"] == ["cashier", "inspector"]


async def test_raw_sql_is_audited(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """ORM'ni BUTUNLAY chetlab o'tgan o'zgarish ham audit qatorini hosil qiladi.

    M10 himoyasi (Pitfall 5). Bu yerda hech qanday ORM obyekti yaratilmaydi
    va `flush()` chaqirilmaydi — faqat xom `text()` operatori bajariladi.
    Agar audit `before_flush` hook'i bilan yozilganida, bu test AYNAN shu
    yerda yiqilardi va insider yo'li ochiq qolardi.
    """
    market = two_markets.market_a
    role_id = market.cashier_role_id

    async with tenant_session(market.id, market.admin_user_id) as session:
        result = await session.execute(
            UPDATE_ROLES_RAW, {"roles": ["market_admin"], "role_id": str(role_id)}
        )
        assert result.rowcount == 1, "xom UPDATE qatorga tegmadi — test o'z shartini bajarmadi"

    rows = await _audit_rows(tenant_session, market.id, role_id, AuditAction.UPDATE)
    assert len(rows) == 1, "xom SQL orqali qilingan o'zgarish AUDITSIZ qoldi (M10)"
    entry = rows[0]

    assert entry.source == AuditSource.DB_TRIGGER
    # Xom SQL `updated_at` ga tegmaydi (u ORM'ning `onupdate` xulqi),
    # shuning uchun bu yerda ro'yxat AYNAN bitta ustundan iborat.
    assert entry.changed_keys == ["roles"]
    assert entry.old_value is not None and entry.new_value is not None
    assert entry.old_value["roles"] == ["cashier"]
    assert entry.new_value["roles"] == ["market_admin"]


async def test_noop_update_writes_nothing(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """Hech narsani o'zgartirmagan UPDATE audit qatori QOLDIRMAYDI.

    Postgres baribir yangi qator versiyasini yozadi (`rowcount == 1`), lekin
    jurnalda bundan iz qolmasligi kerak: shovqin bilan to'lgan audit — hech
    kim o'qimaydigan audit.
    """
    market = two_markets.market_a
    role_id = market.cashier_role_id

    async with tenant_session(market.id, market.admin_user_id) as session:
        result = await session.execute(NOOP_UPDATE_RAW, {"role_id": str(role_id)})
        assert result.rowcount == 1, "no-op UPDATE qatorga umuman tegmadi — test ma'nosiz"

    # Seed qo'ygan `insert` qatoridan boshqa HECH NARSA qo'shilmasligi shart.
    updates = await _audit_rows(tenant_session, market.id, role_id, AuditAction.UPDATE)
    assert updates == [], f"no-op UPDATE {len(updates)} ta audit qatori yaratdi"

    everything = await _audit_rows(tenant_session, market.id, role_id)
    assert [row.action for row in everything] == [AuditAction.INSERT], (
        "no-op UPDATE audit jurnaliga yangi qator qo'shdi"
    )


async def test_delete_records_old_value_only(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """DELETE dan keyin qator YO'Q, lekin uning to'liq nusxasi auditda qoladi.

    Bu — audit jurnalining asosiy ma'nosi: o'chirilgan narsani keyin
    tiklash yoki hech bo'lmasa nima bo'lganini ko'rsatish mumkin.
    """
    market = two_markets.market_a
    role_id = market.cashier_role_id

    async with tenant_session(market.id, market.admin_user_id) as session:
        result = await session.execute(DELETE_MEMBERSHIP_RAW, {"role_id": str(role_id)})
        assert result.rowcount == 1

    rows = await _audit_rows(tenant_session, market.id, role_id, AuditAction.DELETE)
    assert len(rows) == 1
    entry = rows[0]

    assert entry.new_value is None
    assert entry.old_value is not None
    assert entry.old_value["roles"] == ["cashier"]
    assert entry.old_value["user_id"] == str(market.cashier_user_id)
    assert entry.changed_keys is None


async def test_audit_row_is_invisible_to_other_market(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """A bozorining audit qatori B konteksti ostida KO'RINMAYDI (D-11, T-01-34).

    Audit jurnali — bozorning eng nozik ma'lumoti (kim qancha pul harakati
    qildi). Uning o'qilishi boshqa hamma jadval bilan bir xil tenant
    predikatiga bo'ysunadi.
    """
    market = two_markets.market_a
    role_id = market.cashier_role_id

    async with tenant_session(market.id, market.admin_user_id) as session:
        await session.execute(UPDATE_ROLES_RAW, {"roles": ["director"], "role_id": str(role_id)})

    visible_in_a = await _audit_rows(tenant_session, market.id, role_id, AuditAction.UPDATE)
    assert len(visible_in_a) == 1, "o'z bozorida ko'rinmayapti — test shartini bajarmadi"

    visible_in_b = await _audit_rows(tenant_session, two_markets.market_b.id, role_id)
    assert visible_in_b == [], "A bozorining audit qatori B konteksti ostida KO'RINMOQDA"


async def test_system_actor_kind_is_recorded(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """Fon jarayoni `system` sifatida yoziladi, `user` sifatida emas.

    Kunlik hisob-kitob tick'i va snapshot pipeline'i odam nomidan ish
    ko'rmaydi. Ularni `user` deb yozish nizoda soxta dalil bo'lardi:
    "bu o'zgarishni kassir qildi" degan xulosa chiqarilardi.
    """
    market = two_markets.market_a
    role_id = market.cashier_role_id

    async with tenant_session(
        market.id, None, actor_kind=ActorKind.SYSTEM, request_id="billing-tick"
    ) as session:
        await session.execute(UPDATE_ROLES_RAW, {"roles": ["inspector"], "role_id": str(role_id)})

    rows = await _audit_rows(tenant_session, market.id, role_id, AuditAction.UPDATE)
    assert len(rows) == 1
    entry = rows[0]

    assert entry.actor_kind == ActorKind.SYSTEM
    assert entry.actor_user_id is None
    assert entry.request_id == "billing-tick"


async def test_change_without_actor_context_is_still_audited(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """Aktor konteksti O'RNATILMAGAN bo'lsa ham audit qatori YOZILADI.

    Bu ataylab: "kim" noma'lum bo'lgani yozuvni YO'QOTISH uchun sabab emas.
    Aks holda kontekstni o'rnatmaslik auditdan qochishning eng oson yo'li
    bo'lib qolardi — ya'ni eng kam nazorat qilinadigan yo'l eng kam iz
    qoldirardi.
    """
    market = two_markets.market_a
    role_id = market.cashier_role_id

    async with tenant_session(market.id, None, request_id="") as session:
        await session.execute(UPDATE_ROLES_RAW, {"roles": ["director"], "role_id": str(role_id)})

    rows = await _audit_rows(tenant_session, market.id, role_id, AuditAction.UPDATE)
    assert len(rows) == 1, "aktorsiz o'zgarish auditsiz qoldi"
    entry = rows[0]

    assert entry.actor_user_id is None
    assert entry.request_id is None
    # Standart qiymat — GUC bo'sh bo'lsa ham ustun NOT NULL bo'lib qoladi.
    assert entry.actor_kind == ActorKind.USER
    assert entry.changed_keys == ["roles"]
