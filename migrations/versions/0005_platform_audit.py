"""platform_audit: market_id IS NULL audit qatorlarini o'qish yo'li (Gap 5)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-29

=============================================================================
BU MIGRATSIYA SXEMANI O'ZGARTIRMAYDI — jadval ham, ustun ham, indeks ham
qo'shilmaydi. U faqat BITTA policy va BITTA funksiya qo'shadi, ya'ni mavjud
`audit_log` ustidagi O'QISH yo'lini kengaytiradi.

MUAMMO (01-06, 01-07, 01-09 SUMMARY'larida uch marta ketma-ket ochiq qayd
etilgan): `login_failed` kabi platforma-global yozuvlar ATAYIN
`market_id = NULL` bilan yoziladi — rad etilgan login urinishida bozor
NOMA'LUM va uni taxmin qilish jurnalga YOLG'ON dalil yozish bo'lardi.
`audit_read` policy'si esa `market_id = app.market_id` shaklida, ya'ni bunday
qator HECH QANDAY tenant konteksti bilan mos kelmaydi va mahsulot yo'lida
HECH KIMGA ko'rinmaydi. Ular faqat test-superuseri bilan o'qilardi — FOUND-03
ning "kim, qachon, nima" da'vosi shu joyda uzilib qolardi.

NEGA IKKI OBYEKT, BITTASI EMAS (bu qismni qisqartirib bo'lmaydi):

| Obyekt                  | Yolg'iz nima beradi           | Nega yetmaydi                     |
| ----------------------- | ----------------------------- | --------------------------------- |
| `SECURITY DEFINER` fn   | ega huquqi bilan ishlash      | `audit_log` da FORCE RLS —        |
|                         |                               | ega ham policy'ga bo'ysunadi,     |
|                         |                               | ega uchun SELECT policy'si yo'q   |
|                         |                               | -> **0 qator**                    |
| `audit_read_platform`   | egaga NULL qatorlarni ochish  | ilova `sbozor_app` bilan ulanadi, |
|                         |                               | policy unga qo'llanmaydi ->       |
|                         |                               | to'g'ridan-to'g'ri SELECT baribir |
|                         |                               | **0 qator**                       |

Ya'ni juftlik AYNAN mo'ljallangan darvozani beradi: NULL qatorlarga yagona
yo'l — grant qilingan funksiya; `sbozor_app` ning to'g'ridan-to'g'ri
`SELECT ... WHERE market_id IS NULL` so'rovi 0 qator qaytaraveradi.

O'ZGARMASLIK BUZILMAYDI. Yangi policy `FOR SELECT`, `FOR ALL` EMAS —
`UPDATE`/`DELETE` uchun `audit_log` da baribir birorta policy yo'q va
o'zgarmaslikning to'rt qatlami (`0002_audit.py`) o'zgarishsiz qoladi.
Aynan shu sababdan `owner_bootstrap` policy'si bu jadvalga HALI HAM
berilmaydi: u `FOR ALL ... USING (true)` bo'lardi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from migrations.entities.functions import (
    PLATFORM_AUDIT_FUNCTIONS,
    PLATFORM_AUDIT_GRANT_SIGNATURES,
)
from migrations.entities.policies import audit_read_platform_policy
from migrations.helpers import APP_ROLE, create_entity, drop_entity

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Policy AVVAL: funksiya usiz ham yaratiladi, lekin chaqirilganda 0 qator
    # qaytarardi. Tartib mantiqni ko'rsatib turadi — funksiya policy USTIGA
    # quriladi, teskarisi emas.
    create_entity(audit_read_platform_policy())

    for function in PLATFORM_AUDIT_FUNCTIONS:
        create_entity(function)

    for signature in PLATFORM_AUDIT_GRANT_SIGNATURES:
        # PUBLIC dan AVVAL olib tashlanadi: Postgres yangi funksiyaga
        # `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni REVOKE'siz
        # platforma-global audit jurnali bazadagi HAR QANDAY rol uchun
        # ochiq bo'lib qolardi.
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    for function in reversed(PLATFORM_AUDIT_FUNCTIONS):
        drop_entity(function)

    drop_entity(audit_read_platform_policy())
