"""calendar: ish kunlari istisnolari + market_is_open() + market_delete_draft()

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-31

2-FAZANING OXIRGI MIGRATSIYASI. Undan keyin o'nta domen jadvali ham, beshta
bozor funksiyasi ham bazada bo'ladi va `test_autogenerate_is_empty` BUTUN
sxemani qamrab oladi (`PENDING_DOMAIN_TABLES` bo'shaydi).

=============================================================================
JADVAL VA IKKI FUNKSIYA BIR MIGRATSIYADA — BU TARTIB EMAS, TEXNIK ZARURAT:

  * `market_is_open()` — `LANGUAGE sql`, ya'ni uning tanasi `CREATE
    FUNCTION` PAYTIDA parse va validatsiya qilinadi (`check_function_bodies`
    standart `on`). Tana `market_calendar_exceptions` ga murojaat qiladi —
    demak funksiya o'sha jadval TUG'ILGANIDAN KEYIN yaratilishi shart. `0007`
    da yaratishga urinish `relation "public.market_calendar_exceptions" does
    not exist` bilan yiqilardi (02-05 da o'lchangan).
  * `market_delete_draft()` — `plpgsql`, ya'ni CREATE paytida tekshirilmaydi,
    LEKIN u `stall_assignments` / `vendors` / `market_calendar_exceptions`
    dan `DELETE` qiladi. Uning yagona ma'noli o'rni — o'sha uchala jadval
    ham mavjud bo'lgan payt.

Shuning uchun `MARKET_DOMAIN_FUNCTIONS` `MARKET_CORE_*` (0007) va
`MARKET_CALENDAR_*` (shu yer) ga bo'lingan. Aggregat FAQAT autogenerate
reyestri — birorta migratsiya u ustidan tsikl QILMAYDI.
=============================================================================

⚠ FAIL-CLOSED'NING TESKARI TOMONI — OCHIQ YOZILADI, CHUNKI U QIMMAT:

`market_is_open()` ning oxirgi `COALESCE` argumenti `false`. Ya'ni
`market_profile` qatori BO'LMAGAN bozor uchun funksiya HAR KUNI `false`
qaytaradi — bozor hech qachon ishlamaydi va 6-fazadagi kunlik job hech
qanday hisob yozmaydi. Xato chiqmaydi, alert chiqmaydi: TUSHUM JIMGINA
NOLGA TUSHADI. Bu eng yomon nosozlik turi.

Uch himoya shu narxni to'laydi:
  1. `market_create()` `market_profile` qatorini bozor bilan BIR
     TRANZAKSIYADA yaratadi — profilsiz bozor umuman tug'ilmaydi;
  2. 02-11 dagi `activate` to'liqlik tekshiruvi `open_weekdays` ni ham
     talab qiladi (bo'sh massiv `ck_market_profile_open_weekdays_valid`
     bilan ham rad etiladi);
  3. 8-fazaga ilgak: "N kun ketma-ket yopiq" hisoboti — fail-closed jimgina
     ishlab ketgan holatni KO'RINADIGAN qiladi.

Teskari standart (`true` — "sozlanmagan bozor har kuni ishlaydi") ham
tanlanishi mumkin edi va u bu nosozlikni yo'q qilardi, LEKIN o'rniga
boshqasini keltirardi: bayram kuni sozlamasi yo'qolganda sotuvchilarga
NOO'RIN hisob yozilardi va bu pul nizosi — mahsulot aynan bartaraf etadigan
narsa. Ikki yomonlikdan kamrog'i tanlandi.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import CALENDAR_TENANT_TABLES
from migrations.entities.functions import (
    MARKET_CALENDAR_FUNCTIONS,
    MARKET_CALENDAR_GRANT_SIGNATURES,
)
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.helpers import (
    APP_ROLE,
    attach_audit_trigger,
    create_entity,
    detach_audit_trigger,
    drop_entity,
    enable_tenant_rls,
)

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_pk() -> sa.Column[UUID]:
    """PG18 native `uuidv7()` — vaqt-tartiblangan, B-tree do'st."""
    return sa.Column(
        "id",
        pg.UUID(as_uuid=True),
        server_default=sa.text("uuidv7()"),
        nullable=False,
    )


def _market_id() -> sa.Column[UUID]:
    """Tenant kaliti — HAR BIR jadvalda birinchi ustun."""
    return sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False)


def _created_at() -> sa.Column[datetime]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def _updated_at() -> sa.Column[datetime]:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. market_calendar_exceptions — haftalik jadvaldan chiqadigan kunlar.
    #
    #    `is_open` IKKI TOMONLAMA va bitta jadval ikkala holatni ham
    #    ifodalaydi (D-17/D-18):
    #      * `false` — bayram / yopiq kun (haftalik jadvalda ish kuni edi);
    #      * `true`  — istisno ish kuni (haftalik jadvalda dam olish edi).
    #    Ikkinchisi "shunchaki to'liqlik uchun" emas: Karmanada bayram
    #    oldidan dam olish kunida savdo bo'lishi odatiy holat va usiz
    #    o'sha kunning butun tushumi yozilmay qolardi.
    #
    #    ZONA yoki RASTA darajasidagi istisno ATAYIN YO'Q (D-18): u kunlik
    #    hisobni har bir rasta uchun alohida shartga bog'lardi va 6-fazaning
    #    yagona `WHERE market_is_open(:m, :d)` kontrakti buzilardi.
    #
    #    `UNIQUE(market_id, exception_date)` — tozalik emas, FUNKSIYANING
    #    ISHLASH SHARTI: `market_is_open()` istisnoni SKALYAR subquery bilan
    #    o'qiydi va bir sanaga ikkinchi qator paydo bo'lsa "more than one row
    #    returned by a subquery" bilan yiqilardi — ya'ni butun kunlik job
    #    to'xtardi.
    # ------------------------------------------------------------------
    op.create_table(
        "market_calendar_exceptions",
        _market_id(),
        _uuid_pk(),
        sa.Column("exception_date", sa.Date(), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_market_calendar_exceptions"),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_market_calendar_exceptions_market_id_markets",
        ),
        sa.UniqueConstraint(
            "market_id",
            "exception_date",
            name="uq_market_calendar_exceptions_market_id_exception_date",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_market_calendar_exceptions_market_id_id"),
    )

    # ------------------------------------------------------------------
    # 2. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
    # ------------------------------------------------------------------
    for table in CALENDAR_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 3. Audit MAJBURIY (MARKET-05, T-02-40).
    #
    #    Yopiq kun belgilash — TUSHUMNI NOLGA TUSHIRUVCHI amal va u eng
    #    arzon suiiste'mol yo'li: bir kunni "bayram" deb belgilash o'sha
    #    kunning butun yig'imini hisobdan chiqaradi va hech qanday pul
    #    yozuvi o'zgarmaydi (ya'ni moliyaviy jadvallar auditi buni
    #    KO'RSATMAYDI). Iz faqat shu triggerda qoladi.
    # ------------------------------------------------------------------
    for table in CALENDAR_TENANT_TABLES:
        attach_audit_trigger(table)

    # ------------------------------------------------------------------
    # 4. Qolgan ikki bozor funksiyasi.
    #
    #    TARTIB: jadval AVVAL (yuqorida), funksiyalar KEYIN — fayl boshidagi
    #    izoh. `MARKET_CALENDAR_FUNCTIONS` ichida `market_delete_draft`
    #    (SECURITY DEFINER) va `market_is_open` (ATAYIN INVOKER) bor.
    #
    #    ⚠ `market_is_open()` `SECURITY DEFINER` EMAS va bu shu fazadagi
    #    YAGONA bunday funksiya — farq qasddan (T-02-41). U CHAQIRUVCHI
    #    huquqi bilan ishlaydi, ya'ni RLS unga TO'LIQ qo'llanadi: boshqa
    #    bozorning `market_id` si so'ralganda ikkala subquery ham 0 qator
    #    beradi va natija `false` bo'ladi. `SECURITY DEFINER` qilish uni
    #    RLS'dan chiqarardi va bir bozor boshqasining bayram jadvalini —
    #    ya'ni uning ish rejimini — o'qiy olardi.
    #
    #    Uning INVOKER ekani `tests/tenancy/test_market_domain_meta.py::
    #    test_market_is_open_is_not_security_definer` da qulflangan va
    #    `EXPECTED_DEFINER_FUNCTIONS` ga QO'SHILMAYDI (izoh o'sha yerda).
    # ------------------------------------------------------------------
    for function in MARKET_CALENDAR_FUNCTIONS:
        create_entity(function)

    for signature in MARKET_CALENDAR_GRANT_SIGNATURES:
        # PUBLIC dan AVVAL olib tashlanadi: Postgres yangi funksiyaga
        # `EXECUTE TO PUBLIC` ni STANDART beradi. `market_is_open` uchun ham
        # kerak — RLS baribir qatorlarni yashiradi, lekin funksiyaning
        # MAVJUDLIGI ham keraksiz axborot.
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    for function in reversed(MARKET_CALENDAR_FUNCTIONS):
        drop_entity(function)

    for table in reversed(CALENDAR_TENANT_TABLES):
        detach_audit_trigger(table)

    for table in reversed(CALENDAR_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_table("market_calendar_exceptions")
