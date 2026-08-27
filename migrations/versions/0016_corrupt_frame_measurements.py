"""corrupt_frame_measurements: `quality_mean`/`quality_stddev` NULLABLE bo'ladi

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-04

=============================================================================
BU MIGRATSIYA IKKI REJANING OCHIQ ZIDDIYATINI YOPADI VA QARORNI YOZADI.

`04-05` ijrosi ziddiyatni topib, uni ATAYIN qattiq yiqiladigan qilib
qoldirgan edi (`snapshot_repo.SnapshotMeasurementMissingError`) va egasini
`04-07` deb nomlagan:

  * `04-03` (sxema)     -> `snapshots.quality_mean`/`quality_stddev` NOT NULL
  * `04-04` (sof modul) -> `analyze()` `corrupt` kadr uchun o'lchovlarni
                           `None` qaytaradi. Nol qiymat ATAYIN rad etilgan:
                           u «o'lchandi va nol chiqdi» ma'nosini berardi va
                           D-15 ning `percentile_cont` bilan chegara
                           chiqarish yo'lini buzardi
  * `04-UI-SPEC` §6.4   -> C4 hujayrasi = `succeeded` + `corrupt`, ya'ni
                           bunday QATOR MAVJUD bo'lishi kutiladi
  * `04-04` xato reyestri -> `capture_invalid_response` = «javob keldi,
                           lekin ichida TASVIR YO'Q»

`04-05` bu to'rtta bandni «uchinchisi va to'rtinchisi bir vaqtda to'g'ri
bo'la olmaydi» deb baholagan edi. **O'lchov ko'rsatdiki, ular ikki XIL
QATLAMDA yashaydi va ziddiyat aslida yo'q:**

    javob UMUMAN kadr emas (HTML sahifa, bo'sh tana, JPEG bo'lmagan bayt)
        -> `frame_source` ning magic-bayt darvozasi uni SIFAT TAHLILIGA
           umuman qo'ymaydi
        -> `capture_invalid_response`, qator `failed`, `snapshots` qatori
           YO'Q                                        <- 4-band BAJARILDI

    javob KADR, lekin YAROQSIZ (kesilgan JPEG, dekod xatosi)
        -> `quality.analyze()` uni `corrupt` deb belgilaydi va o'lchovlarni
           `None` qaytaradi
        -> qator `succeeded`, `snapshots` qatori BOR, `is_billable = false`
                                                     <- 3-band BAJARILDI

Ya'ni «(a) yoki (b)» tanlovi noto'g'ri qo'yilgan savol edi: **ikkalasi ham
kerak**, chunki ular ikki xil nosozlikni ifodalaydi. Yagona narsa —
ikkinchi yo'l uchun ustunlar `NULL` qabul qilishi kerak.

⚠ NEGA SENTINEL NOL EMAS: `0` qiymat bazada «o'lchandi va nol chiqdi»
  degan MA'NOGA ega bo'lardi. D-15 ning butun maqsadi — chegaralarni
  HAQIQIY taqsimotdan (`percentile_cont`) chiqarish; `corrupt` kadrlarning
  soxta nollari o'sha taqsimotni pastga tortardi va Phase 0 da sozlangan
  chegara jimgina noto'g'ri bo'lardi.

⚠ NEGA `is_billable` GA TEGILMAYDI: u `quality_verdict = 'ok'` dan hosila
  (`GENERATED ALWAYS ... STORED`), ya'ni `corrupt` qator uchun u AVTOMATIK
  `false` bo'ladi va D-16 ning kompozit FK ilgagi 5-fazada bunday kadrga
  bandlik dalilini yaratishga YO'L QO'YMAYDI. Kafolat bu migratsiyadan
  MUSTAQIL va u zaiflashmaydi.
=============================================================================

⚠ `downgrade()` MA'LUMOT YO'QOTISHI MUMKIN va bu OCHIQ yozilgan: `NULL`
o'lchovli qator bo'lsa `SET NOT NULL` yiqiladi. Bu TO'G'RI yo'nalish —
sxemani orqaga qaytarish uchun dalil-qatorni jimgina o'chirish yoki nol
bilan to'ldirish yuqoridagi butun mulohazani bekor qilardi. Operator
qatorlarni O'ZI hal qilishi kerak va xato xabari buni aytadi.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NULLABLE_COLUMNS: tuple[str, ...] = ("quality_mean", "quality_stddev")
"""`corrupt` kadrda o'lchab BO'LMAYDIGAN ikki ustun.

`quality_saturation` bu ro'yxatda YO'Q — u `0014` da allaqachon nullable
(«IR aniqlash uchun; `NULL` = o'lchanmadi»), ya'ni «o'lchanmagan qiymat
`NULL`» qoidasi o'sha faylda BOSHLANGAN va bu migratsiya uni faqat
qolgan ikkitasiga yoyadi.
"""


def upgrade() -> None:
    for column in _NULLABLE_COLUMNS:
        op.alter_column(
            "snapshots",
            column,
            existing_type=sa.Numeric(6, 2),
            nullable=True,
        )


def downgrade() -> None:
    for column in _NULLABLE_COLUMNS:
        op.alter_column(
            "snapshots",
            column,
            existing_type=sa.Numeric(6, 2),
            nullable=False,
        )
