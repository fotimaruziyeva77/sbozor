"""stalls.status — to'rtinchi holat: `fair` (yarmarka)

Revision ID: 0028
Revises: 0027
Create Date: 2026-08-25

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR (foydalanuvchi talabi, 2026-08-25).

Bozorda PATTA OLINMAYDIGAN rastalar bor: bayram yarmarkasi, ijtimoiy
joylar, ma'muriyat qarori bilan bepul ajratilgan rastalar. Ular uchun
modelda holat yo'q edi va admin ikkita yomon yo'ldan birini tanlardi:

  * `active` qoldirish — tizim har kuni undirilmaydigan «qarz» yozadi va
    «to'lanmagan» ro'yxati abadiy yolg'on ko'rsatkich bilan turadi;
  * `closed` deb belgilash — rasta REYESTRDA «foydalanishdan chiqarilgan»
    bo'lib qoladi, holbuki u ishlayapti.

`fair` bu ikkilikni yechadi: rasta TIRIK, lekin pul qoidasi «olinmaydi».

-----------------------------------------------------------------------------
⛔ SXEMA O'ZGARISHI FAQAT CHECK KONSTRAYT — USTUN YO'Q.

`STALL_STATUS_CHECK` ifodasi `StallStatus` enumidan HOSIL QILINADI
(model bilan bitta manba). Enum `fair` ni oldi — konstrayt qaytadan
o'sha konstantadan quriladi, ya'ni ro'yxat bu faylda QO'LDA yozilmaydi
va model bilan ajralib keta olmaydi (0007 bilan aynan bir xil naqsh).

-----------------------------------------------------------------------------
⚠ PUL QOIDASI SXEMADA EMAS, `resolve_stall_day_money()` DA: bu holatga
  `fair_stall` sababi bilan `amount = None` beriladi (D-16 — pul yechimi
  yagona joyda). Migratsiya faqat qiymatni QONUNIYLASHTIRADI.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sbozor_core.models.market import STALL_STATUS_CHECK

# revision identifiers, used by Alembic.
revision: str = "0028"
down_revision: str | Sequence[str] | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """⛔ Nom PREFIKSSIZ — `alembic.ini` konvensiyasi `ck_stalls_` ni o'zi qo'yadi."""
    # ⚠ DROP ham PREFIKSSIZ nom oladi — `alembic.ini` konvensiyasi uni
    #   o'zi o'raydi (birinchi urinish `ck_stalls_ck_stalls_…` bilan
    #   yiqildi — o'lchandi).
    op.drop_constraint("status_allowed", "stalls", type_="check")
    op.create_check_constraint("status_allowed", "stalls", STALL_STATUS_CHECK)


def downgrade() -> None:
    """⚠ `fair` qiymatli qator BOR bo'lsa downgrade CHECK yaratishda yiqiladi.

    Bu ATAYIN himoya: eski uchlik konstraytni yarmarka qatorlari ustiga
    jimgina qo'yish mumkin emas — avval ularga boshqa holat beriladi.
    """
    op.drop_constraint("status_allowed", "stalls", type_="check")
    op.create_check_constraint(
        "status_allowed",
        "stalls",
        "status IN ('active', 'maintenance', 'closed')",
    )
