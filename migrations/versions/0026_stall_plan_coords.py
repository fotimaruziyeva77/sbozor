"""stalls.plan_x / plan_y — plan-xaritani QO'LDA chizish uchun

Revision ID: 0026
Revises: 0025
Create Date: 2026-08-20

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR.

Plan-xarita bugungacha SXEMATIK edi: zona = qator, rastalar kod tartibida
avtomatik terilardi («Rasta qo'shilgach xarita avtomatik chiziladi»). Bu
ishlaydi, lekin bozorning HAQIQIY joylashuvini ifodalay olmaydi — qatorlar
orasidagi yo'l, burchakdagi katta rasta, ikki blokka bo'lingan bozor.
Ma'muriyat xaritani aynan shu tarzda o'qiydi va «bu qaysi rasta?» savoliga
javob shu yerdan chiqadi.

⛔ IKKALA USTUN HAM `NULL` — VA BU ASOSIY QAROR:

  · mavjud bozorlar hech narsa yo'qotmaydi: koordinatasi yo'q rasta
    sxematik xaritada qolaveradi va ikki rejim YONMA-YON yashaydi;
  · Excel bilan 1000 rasta yuklagan bozor DARHOL ishlay boshlaydi,
    joylashtirishni keyin, bo'sh vaqtda qiladi;
  · «koordinatasi yo'q» va «koordinatasi (0,0)» BOSHQA ikki holat —
    ularni aralashtirish barcha rastani chap yuqori burchakka yig'ib
    qo'yardi.

⛔ `INTEGER` va SHARTLI KATAK — piksel EMAS. Piksel ekran o'lchamiga
   bog'lanib qolardi va boshqa qurilmada plan siljirdi. Katak o'lchamsiz:
   muharrir ham, ko'ruvchi ham uni o'z kengligiga moslaydi. Rasta katakka
   tortilgani (snap) uchun kasr koordinata mavjud emas.

⛔ MANFIY QIYMAT TAQIQLANADI: plan chap-yuqori burchakdan boshlanadi.
   Manfiy koordinata ko'ruvchi maydondan tashqariga chiqib, rastani
   KO'RINMAS qilardi — ya'ni ma'lumot bor, ekranda esa yo'q.

⛔ YUQORI CHEGARA HAM BOR (`< 1000`): u xotira uchun emas, TASODIF
   uchun — muharrirdagi xato yoki buzuq import bitta rastani 10^9
   katakka uloqtirsa, xarita butun bozorni ko'rsatolmay qolardi.
=============================================================================
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """⛔ Cheklov nomlari PREFIKSSIZ beriladi.

    `alembic.ini` dagi nomlash konvensiyasi `ck_%(table_name)s_` prefiksini
    O'ZI qo'shadi. Bu yerda ham yozilsa nom `ck_stalls_ck_stalls_…` bo'lib
    ikki marta prefikslanadi — sxemada abadiy qoladigan tartibsizlik.
    """
    op.add_column("stalls", sa.Column("plan_x", sa.Integer(), nullable=True))
    op.add_column("stalls", sa.Column("plan_y", sa.Integer(), nullable=True))

    # ⛔ IKKALASI BIRGA yoki IKKALASI HAM YO'Q: yarim koordinata rastani
    #    qayerga qo'yishni ayta olmaydi va u jimgina sxematik rejimga
    #    tushib qolardi — «saqladim, lekin ko'rinmayapti» sinfidagi xato.
    op.create_check_constraint(
        "plan_xy_together",
        "stalls",
        "(plan_x IS NULL) = (plan_y IS NULL)",
    )
    op.create_check_constraint(
        "plan_x_range",
        "stalls",
        "plan_x IS NULL OR (plan_x >= 0 AND plan_x < 1000)",
    )
    op.create_check_constraint(
        "plan_y_range",
        "stalls",
        "plan_y IS NULL OR (plan_y >= 0 AND plan_y < 1000)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_stalls_plan_y_range", "stalls", type_="check")
    op.drop_constraint("ck_stalls_plan_x_range", "stalls", type_="check")
    op.drop_constraint("ck_stalls_plan_xy_together", "stalls", type_="check")
    op.drop_column("stalls", "plan_y")
    op.drop_column("stalls", "plan_x")
