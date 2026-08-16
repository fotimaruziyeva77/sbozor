"""`market_notification_settings` ning audit tarixi — O'LCHOV MARKERI.

=============================================================================
⛔⛔ WAVE-0 ZONDINING NATIJASI SHU YERDA, KODDA QULFLANADI.

08-RESEARCH Open Question 1: repo'ning UCH joyi bir xil da'voni
takrorlaydi — «`fn_audit_row()` `id` ustunisiz jadvalda HAR DML DA
YIQILADI»:

  * `sbozor_core.schema_contract.AUDITED_TABLES` docstringi;
  * `migrations/entities/__init__.py::NOTIFICATION_AUDITED_TABLES`;
  * `services/core-api/app/repositories/binding_repo.py::bind_director()`.

Manba kodini o'qish buni TASDIQLAMAYDI:

    COALESCE((v_new ->> 'id')::uuid, (v_old ->> 'id')::uuid)

`jsonb ->> '<yo'q kalit>'` `NULL` beradi, `NULL::uuid` esa istisno
KO'TARMAYDI, `audit_log.row_id` esa `nullable=True` (`0002_audit.py`).

⛔ SHUNING UCHUN REJA DA'VOGA TAYANGAN TEST YOZMAYDI — U AVVAL O'LCHADI.
=============================================================================
"""

from __future__ import annotations

from typing import Final

import pytest

pytestmark = pytest.mark.usefixtures("migrated")

AUDIT_ROW_WITHOUT_ID_COLUMN_RAISES: Final[bool] = False
"""ZOND NATIJASI — `fn_audit_row()` `id` ustunisiz jadvalda YIQILADIMI.

**O'lchov:** 2026-08-16, `PostgreSQL 18.4 (Debian trixie)`, testcontainer.
**Qanday o'lchandi:** `market_notification_settings` ga (o'sha paytdagi
holatida, ya'ni PK `market_id`, `id` ustuni YO'Q) `fn_audit_row()`
triggeri QO'LDA ulandi va bitta `UPDATE ... SET overdue_days = 7`
bajarildi.

**O'LCHANGAN NATIJA — VARIANT (b), YA'NI REPO HUJJATI YOLG'ON EDI:**

    DML O'TDI (istisno YO'Q).
    audit_log qatorlari : 1
    row_id              : NULL
    action              : 'update'
    changed_keys        : ['overdue_days']

⚠ O'LCHOVNING SHARTI — `audit_log` NI O'QISH UCHUN TENANT KONTEKSTI.
Birinchi urinishda sanoq `0` chiqdi va u «qator yozilmadi» degan YOLG'ON
xulosaga olib borardi: `audit_read` policy'si tenant-scoped va u jadval
EGASIGA ham qo'llanadi (`FORCE`). `set_config('app.market_id', ...)` dan
keyin qator KO'RINDI. Ya'ni «0 qator» bu yerda IKKI XIL sababdan kelib
chiqishi mumkin edi va ularni ajratmaslik butun zondni bekor qilardi.

⛔ **OQIBAT — TEST DA'VOSI SHUNDAN CHIQADI.** Trigger yiqilmagani uchun
«`fn_audit_row()` yiqiladi» shaklidagi test YOZILMAYDI. Haqiqiy nuqson
BOSHQA: `row_id IS NULL` bo'lgan audit qatori QAYSI QATORGA tegishli
ekanini AYTMAYDI — ya'ni «direktor chatini kim, qachon almashtirdi?»
savoli javobsiz qolardi. `0025` `id uuid` ustunini aynan SHU sababdan
qo'shadi (D-24), «aks holda trigger yiqiladi» degan sababdan EMAS.

⛔ QIYMAT QO'LDA YOZILMAYDI: quyidagi testlar `0025` DAN KEYINGI holatni
o'lchaydi va `row_id IS NOT NULL` ni TALAB qiladi. Marker esa «nega
da'vo shu shaklda?» savoliga O'LCHOV bilan javob beradi — usiz keyingi
ishlovchi repo hujjatidagi taxminni qaytadan haqiqat deb qabul qilardi.
"""

AUDIT_ROW_MEASURED_AT: Final[str] = "2026-08-16 · PostgreSQL 18.4"
"""Zondning sanasi va serveri (`BILLABLE_ANCHOR_SUPPORTED` naqshi).

Yozilmasa natija keyinroq «qayerda va qachon o'lchangan?» degan javobsiz
savolga aylanardi. PG major versiyasi ko'tarilganda zond QAYTA
yugurtiriladi va bu satr yangilanadi.
"""
