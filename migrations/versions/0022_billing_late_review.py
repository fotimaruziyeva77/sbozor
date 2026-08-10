"""billing_late_review: tizim yozadigan tuzatish uchun ikkita qulf

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-10

=============================================================================
⛔⛔ BU MIGRATSIYA 06-07 NING «KECH KELGAN TASDIQ» SHOXINI IFODALANADIGAN
    QILADI. USIZ O'SHA SHOX YOZILGANDA HAM ISHLAMASDI.

`06-07-PLAN.md` ning Task 1 / 6-bandi shunday deydi: nazoratchi D + 1
kunduzida «bo'sh» degach, `billing_close` yozilgan hisobni ⛔ BEKOR
QILMAYDI (`daily_charges` o'zgarmas — D-07), o'rniga `charge_adjustments`
ga `direction = 'decrease'`, `reason_code = 'late_review'`,
`actor_user_id = NULL` (tizim) qatorini `ON CONFLICT DO NOTHING` bilan
IDEMPOTENT yozadi.

`0020` da esa AYNAN shu ikki narsa MEXANIK IMKONSIZ edi:

  1. `charge_adjustments.actor_user_id` `NOT NULL` (+ `users.id` ga FK).
     Tizim yozadigan qatorda esa odam YO'Q — `set_tenant_context()` fon
     jobida `actor_id = NULL`, `actor_kind = 'system'` bilan chaqiriladi.
  2. `ON CONFLICT DO NOTHING` uchun NISHON YO'Q edi: jadvalda faqat
     `uq_charge_adjustments_market_id_id` bor (u kompozit FK uchun) va u
     har `INSERT` da YANGI `uuid` bilan HECH QACHON to'qnashmasdi.

=============================================================================
1-QULF — `actor_user_id` `NULL` QABUL QILADI.

⚠ MUQOBIL RAD ETILDI: «tizim foydalanuvchisi» qatorini `users` ga yozish.
  U ikki narsani buzardi: (a) `users` — GLOBAL jadval va unda soxta
  hisob RBAC sanoqlarini jimgina siljitardi (`two_markets` ning kassir
  qidiruvi rol bo'yicha ishlaydi); (b) nizoda audit qatori «kim qaror
  qildi?» savoliga ODAM ko'rsatardi, holbuki qaror MODELNIKI —
  yolg'on javob javobning yo'qligidan yomonroq (D-02).

⚠ NAQSH YANGI EMAS: `audit_log.actor_user_id` `0002` dan beri `nullable`
  va uning sababi AYNAN shu («kim» noma'lum bo'lgani yozuvni yo'qotish
  uchun sabab emas — `fn_audit_row()` docstringi).

⚠ TESKARI YO'NALISH (`downgrade`) MA'LUMOT YO'QOTISHI MUMKIN: `NULL`
  aktorli qator bor bo'lsa `SET NOT NULL` yiqiladi. Bu ATAYIN va u
  jimgina tuzatilmaydi — `downgrade` qatorni O'CHIRMAYDI, chunki
  o'chirish moliyaviy yozuvni yo'qotardi. Operator avval o'sha
  qatorlarni ko'radi.

=============================================================================
2-QULF — BIR HISOBGA BITTA `late_review` TUZATISHI (QISMAN UNIQUE INDEKS).

⛔ IDEMPOTENTLIK ILOVA QATLAMIDA QILINMAYDI. «Avval tekshir, keyin yoz»
   shakli ikkita parallel yugurishda ikkalasiga ham BO'SH holatni
   ko'rsatardi va hisobga IKKI MARTA to'liq summali kamaytirish
   yozilardi — netto summa MANFIY bo'lib qolardi va nosozlik faqat
   qarzdorlik reestrida, oy oxirida ko'rinardi. Bu `SHIFT_OPEN_INDEX`
   (D-27) da o'lchangan qarorning AYNAN o'zi: poyga DB'GA topshiriladi.

⚠ INDEKS QISMAN VA U FAQAT TIZIM YOZADIGAN SABAB KODINI qamraydi.
  `CHARGE_ADJUSTMENT_INDEX` docstringidagi «bir hisobga bir necha
  tuzatish MUTLAQO qonuniy» qoidasi qolgan sabab kodlari uchun KUCHIDA
  QOLADI — to'liq unikalik `tariff_correction` ni ikki marta yozishni ham
  bloklardi, holbuki u INSONNING qonuniy amali.

⚠ PREDIKAT `AdjustmentReason` DAN HOSILA (`LATE_REVIEW_ADJUSTMENT_
  PREDICATE`), bu faylga literal ko'chirilmaydi — `test_billing_domain_
  meta.py::test_no_migration_hard_codes_a_value_list` ning qoidasi
  (D-32). Bu YOLG'IZ QIYMAT, ro'yxat emas, ya'ni u darvozaning
  naqshiga ham tushmaydi; import baribir qilinadi, chunki nom va enum
  bir kun jimgina ajralib ketishi mumkin.

⚠ INDEKS `market_id` BILAN BOSHLANADI -> `INDEX_EXCEPTIONS` ga hech nima
  qo'shilmaydi (`0020` ning 7-blokidagi qoida).
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.billing import (
    LATE_REVIEW_ADJUSTMENT_INDEX,
    LATE_REVIEW_ADJUSTMENT_PREDICATE,
)
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision: str = "0022"
down_revision: str | Sequence[str] | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "charge_adjustments",
        "actor_user_id",
        existing_type=pg.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_index(
        LATE_REVIEW_ADJUSTMENT_INDEX,
        "charge_adjustments",
        ["market_id", "charge_id"],
        unique=True,
        postgresql_where=sa.text(LATE_REVIEW_ADJUSTMENT_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index(LATE_REVIEW_ADJUSTMENT_INDEX, table_name="charge_adjustments")
    # ⚠ `NULL` aktorli qator bor bo'lsa bu ATAYIN yiqiladi — fayl
    #   boshidagi uchinchi ⚠. Moliyaviy qatorni jimgina o'chirish
    #   `downgrade` ning ishi EMAS.
    op.alter_column(
        "charge_adjustments",
        "actor_user_id",
        existing_type=pg.UUID(as_uuid=True),
        nullable=False,
    )
