"""`market_notification_settings` ning audit tarixi — 07 №4 ning YOPILISHI.

=============================================================================
⛔⛔ WAVE-0 ZONDINING NATIJASI SHU YERDA, KODDA QULFLANADI.

08-RESEARCH Open Question 1: repo'ning UCH joyi bir xil da'voni
takrorlagan edi — «`fn_audit_row()` `id` ustunisiz jadvalda HAR DML DA
YIQILADI»:

  * `sbozor_core.schema_contract.AUDITED_TABLES` docstringi;
  * `migrations/entities/__init__.py::NOTIFICATION_AUDITED_TABLES`;
  * `services/core-api/app/repositories/binding_repo.py::bind_director()`.

Manba kodini o'qish buni TASDIQLAMAGAN edi:

    COALESCE((v_new ->> 'id')::uuid, (v_old ->> 'id')::uuid)

`jsonb ->> '<yo'q kalit>'` `NULL` beradi, `NULL::uuid` esa istisno
KO'TARMAYDI, `audit_log.row_id` esa `nullable=True` (`0002_audit.py`).

⛔ SHUNING UCHUN REJA DA'VOGA TAYANGAN TEST YOZMADI — U AVVAL O'LCHADI,
   VA O'LCHOV DA'VONI RAD ETDI (pastdagi marker).
=============================================================================

QUYIDAGI UCH TEST `0025` DAN KEYINGI HOLATNI o'lchaydi:

  (a) `bind_director()` ikki marta — birinchisi INSERT, ikkinchisi UPDATE
      shoxidan o'tadi va IKKALASI ham xatosiz (`ON CONFLICT` sinmagani);
  (b) audit qatorlari bor VA ⛔ `row_id IS NOT NULL`;
  (c) `row_id` jadvaldagi `id` bilan TENG.

⛔ «`fn_audit_row()` yiqiladi» shaklidagi test YOZILMAYDI — u o'lchov
   bilan rad etilgan da'voni qulflagan bo'lardi.
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

import pytest

# ⚠ `tenant_session` ATAYIN QAYTA NOMLANADI: `conftest.py` da AYNAN shu
#   nomli FIXTURE bor (`TenantSessionFactory`) va u boshqa narsa. Bir xil
#   nom bu faylda o'quvchini chalg'itardi — qaysi biri chaqirilayotgani
#   faqat argument shaklidan bilinardi.
from app.repositories.binding_repo import bind_director
from app.repositories.binding_repo import tenant_session as bot_tenant_session
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import cleanup_notification_domain
from psycopg import Connection
from psycopg.rows import TupleRow
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

AUDIT_ROW_WITHOUT_ID_COLUMN_RAISES: Final[bool] = False
"""ZOND NATIJASI — `fn_audit_row()` `id` ustunisiz jadvalda YIQILADIMI.

**O'lchov:** 2026-08-16, `PostgreSQL 18.4 (Debian trixie)`, testcontainer.
**Qanday o'lchandi:** `market_notification_settings` ga (`0025` DAN
OLDINGI holatida, ya'ni PK `market_id`, `id` ustuni YO'Q) `fn_audit_row()`
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
keyin qator KO'RINDI. Ya'ni «0 qator» IKKI XIL sababdan kelib chiqishi
mumkin edi va ularni ajratmaslik butun zondni bekor qilardi.

⛔ **OQIBAT — QUYIDAGI TEST DA'VOLARI SHUNDAN CHIQADI.** Trigger
yiqilmagani uchun «yiqiladi» shaklidagi test YOZILMAYDI. Haqiqiy nuqson
BOSHQA: `row_id IS NULL` bo'lgan audit qatori QAYSI QATORGA tegishli
ekanini AYTMAYDI — ya'ni «direktor chatini kim, qachon almashtirdi?»
savoli javobsiz qolardi. `0025` `id uuid` ni aynan SHU sababdan qo'shadi
(D-24), «aks holda trigger yiqiladi» degan sababdan EMAS.

⛔ MARKER QO'LDA O'ZGARTIRILMAYDI: quyidagi `test_audit_row_id_is_not_null`
`0025` DAN KEYINGI holatni o'lchaydi va `row_id IS NOT NULL` ni TALAB
qiladi. Marker esa «nega da'vo shu shaklda?» savoliga O'LCHOV bilan javob
beradi — usiz keyingi ishlovchi repo hujjatidagi taxminni qaytadan
haqiqat deb qabul qilardi.
"""

AUDIT_ROW_MEASURED_AT: Final[str] = "2026-08-16 · PostgreSQL 18.4"
"""Zondning sanasi va serveri (`BILLABLE_ANCHOR_SUPPORTED` naqshi).

Yozilmasa natija keyinroq «qayerda va qachon o'lchangan?» degan javobsiz
savolga aylanardi. PG major versiyasi ko'tarilganda zond QAYTA
yugurtiriladi va bu satr yangilanadi.
"""

FIRST_CHAT_ID = 7_452_119_003
"""⚠ `2**31` DAN KATTA — `BIGINT` qarorining jufti.

Telegram identifikatorlari 32-bit chegarasidan ALLAQACHON oshib ketgan.
32-bit diapazondagi qiymat bilan yozilgan test `INTEGER` ga qaytarilgan
ustunni ham O'TKAZIB YUBORARDI (`test_seed_binding_default_id_is_outside_
the_32_bit_range` bilan aynan bir xil mulohaza).
"""

SECOND_CHAT_ID = 8_113_557_224
"""Qayta ulanish — BOSHQA Telegram akkaunti, o'sha bozor."""

SETTINGS_AUDIT_ROWS = """
SELECT row_id, action
FROM audit_log
WHERE table_name = 'market_notification_settings' AND market_id = %s
ORDER BY at
"""

SETTINGS_ROW = "SELECT id, director_chat_id FROM market_notification_settings WHERE market_id = %s"

SET_MARKET = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti — `audit_log` ni O'QISH uchun.

`audit_read` policy'si tenant-scoped va u jadval EGASIGA ham qo'llanadi
(`FORCE`). Kontekstsiz sanoq HAR IKKALA o'lchovda ham 0 bo'lardi va audit
da'vosi BO'SH ROST bo'lib qolardi — bu AYNAN yuqoridagi zondda BIR MARTA
sodir bo'lgan tuzoq.
"""


async def _bind_twice(
    sessionmaker: async_sessionmaker[AsyncSession], *, market_id: UUID
) -> tuple[bool, bool]:
    """`bind_director()` ni ikki marta chaqiradi va IKKALA natijani qaytaradi.

    Har chaqiruv O'Z tranzaksiyasida — `resolve_director()` ning aynan
    naqshi (u ham har bozor uchun alohida `tenant_session` ochadi).
    """
    async with bot_tenant_session(sessionmaker, market_id=market_id, request_id=None) as session:
        first = await bind_director(session, market_id=market_id, chat_id=FIRST_CHAT_ID)

    async with bot_tenant_session(sessionmaker, market_id=market_id, request_id=None) as session:
        second = await bind_director(session, market_id=market_id, chat_id=SECOND_CHAT_ID)

    return first, second


async def test_bind_director_is_idempotent_across_two_calls(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    market_domain: MarketDomainSeed,
) -> None:
    """(a) Birinchi chaqiruv INSERT, ikkinchisi UPDATE — IKKALASI ham xatosiz.

    =========================================================================
    ⛔⛔ BU TEST `0025` NING `UNIQUE (market_id)` BANDINI QO'RIQLAYDI.

    PK `market_id` dan `id` ga ko'chgach 1:1 kafolati AVTOMATIK yo'qoladi.
    `_BIND_DIRECTOR_CHAT` esa `ON CONFLICT (market_id) DO UPDATE` yozadi va
    bu INFERENCE shakli AYNAN o'sha ustun ustidagi UNIQUE cheklovni
    QIDIRADI. Cheklov bo'lmasa Postgres:

        there is no unique or exclusion constraint matching the
        ON CONFLICT specification

    ⛔ SABOTAJ BILAN O'LCHANGAN (`08-02` / T3, 2026-08-16): `0025` dan
       `op.create_unique_constraint(...)` satri vaqtincha olib tashlandi
       va AYNAN SHU test QIZARDI. O'lchangan xato — LITERAL:

           asyncpg.exceptions.InvalidColumnReferenceError: there is no
           unique or exclusion constraint matching the ON CONFLICT
           specification

       ⚠ TIP `asyncpg.*`, `psycopg.*` EMAS: `bind_director()` ilovaning
         ASYNC yo'lidan (SQLAlchemy + asyncpg) o'tadi, quyidagi
         tekshiruvlar esa sinxron `psycopg` ulanishi bilan bajariladi.
         Ikkalasi bir faylda yonma-yon turadi va ularni chalkashtirish
         `pytest.raises(...)` ni hech qachon ushlamaydigan qilardi.

       Ya'ni darvoza HAQIQATAN o'sha bandni o'lchaydi, shaklga qaramaydi.

    ⚠ IKKALA SHOX HAM MAJBURIY: faqat birinchi chaqiruv o'lchansa
      `ON CONFLICT` bandi UMUMAN bajarilmasdi (konflikt yo'q edi) va
      test cheklovsiz sxemada ham YASHIL qolardi.
    =========================================================================
    """
    market_id = market_domain.market_a.market_id

    try:
        first, second = await _bind_twice(app_sessionmaker, market_id=market_id)

        assert first is True, (
            "birinchi `bind_director()` `False` qaytardi — ya'ni qator ALLAQACHON "
            "mavjud edi. Test o'z shartini yo'qotdi: INSERT shoxi o'lchanmadi."
        )
        assert second is False, (
            "ikkinchi `bind_director()` `True` qaytardi — ya'ni u YANGI qator "
            "yaratdi. `ON CONFLICT (market_id) DO UPDATE` shoxi bajarilmagan, "
            "demak 1:1 kafolati (`uq_market_notification_settings_market_id`) "
            "YO'Q va bir bozorda IKKITA sozlama qatori tug'ilgan."
        )

        # ⛔ NATIJA BAZADAN O'QILADI: qaytish qiymati «yozildi» degan
        #   DA'VO, yozilgan QIYMAT esa boshqa savol. Ikkinchi chaqiruv
        #   manzilni ALMASHTIRGAN bo'lishi shart.
        row = sync_owner_conn.execute(SETTINGS_ROW, (str(market_id),)).fetchone()
        assert row is not None, "sozlama qatori umuman yozilmagan"
        assert int(row[1]) == SECOND_CHAT_ID, (
            f"`director_chat_id` = {row[1]}, kutilgani {SECOND_CHAT_ID}. Qayta "
            "ulanish manzilni ALMASHTIRISHI shart — aks holda direktor eski "
            "chatda dayjest kutib qolardi."
        )
    finally:
        cleanup_notification_domain(sync_owner_conn, market_ids=[market_id])


async def test_settings_changes_are_audited_with_a_non_null_row_id(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    market_domain: MarketDomainSeed,
) -> None:
    """(b) Audit qatorlari bor VA ⛔ `row_id IS NOT NULL` (D-24).

    =========================================================================
    07 `deferred-items.md` №4 NING O'LCHOVI.

    `row_id IS NOT NULL` — bu faylning butun mazmuni. Zond ko'rsatgan
    holatda (`id` ustuni yo'q) trigger BARIBIR ishlardi va qator BARIBIR
    yozilardi — ya'ni «audit qatori bormi?» degan savol YOLG'ON-YASHIL
    javob berardi. Farqni faqat `row_id` ning qiymati ko'rsatadi.

    ⚠ IKKI QATOR KUTILADI: `insert` va `update` (ikki chaqiruv). Sanoqning
      O'ZI ham ma'noli — `fn_audit_row()` HECH NARSA o'zgarmagan
      `UPDATE` da qator YOZMAYDI (`v_keys IS NULL -> RETURN NULL`), ya'ni
      ikkinchi chaqiruv HAQIQATAN qiymatni almashtirganini ham shu
      tasdiqlaydi.
    =========================================================================
    """
    market_id = market_domain.market_a.market_id

    try:
        await _bind_twice(app_sessionmaker, market_id=market_id)

        # ⚠ Tenant konteksti — `SET_MARKET` docstringi. Usiz sanoq 0
        #   bo'lardi va quyidagi da'vo BO'SH ROST bo'lib qolardi.
        sync_owner_conn.execute(SET_MARKET, (str(market_id),))
        rows = sync_owner_conn.execute(SETTINGS_AUDIT_ROWS, (str(market_id),)).fetchall()

        assert rows, (
            "`market_notification_settings` uchun audit qatori YO'Q. `0025` "
            "unga `fn_audit_row()` triggerini ulaydi va nomni "
            "`AUDITED_TABLES` ga qo'shadi — ikkalasidan biri tushib qolgan."
        )

        null_row_ids = [action for row_id, action in rows if row_id is None]
        assert null_row_ids == [], (
            f"`row_id IS NULL` bo'lgan audit qatorlari topildi: {null_row_ids}. "
            "AYNAN SHU nuqson 07 `deferred-items.md` №4 ning mazmuni edi: "
            "bunday qator QAYSI QATORGA tegishli ekanini AYTMAYDI. `0025` "
            "jadvalga `id uuid` PK berishi kerak edi."
        )

        actions = [action for _, action in rows]
        assert actions == ["insert", "update"], (
            f"audit harakatlari {actions}, kutilgani `['insert', 'update']`. "
            "Ikki chaqiruv AYNAN ikki shoxdan o'tishi kerak edi."
        )
    finally:
        sync_owner_conn.execute(
            "DELETE FROM audit_log WHERE table_name = 'market_notification_settings' "
            "AND market_id = %s",
            (str(market_id),),
        )
        cleanup_notification_domain(sync_owner_conn, market_ids=[market_id])


async def test_audit_row_id_matches_the_settings_row_id(
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    market_domain: MarketDomainSeed,
) -> None:
    """(c) `row_id` jadvaldagi `id` bilan TENG — «qaysi qator?» javobsiz qolmaydi.

    =========================================================================
    ⛔ `IS NOT NULL` YOLG'IZ YETARLI EMAS VA BU FARQ MEXANIK.

    Yuqoridagi (b) testi faqat «qiymat bor» deydi. `fn_audit_row()`
    `COALESCE((v_new ->> 'id')::uuid, (v_old ->> 'id')::uuid)` yozadi,
    ya'ni u NOTO'G'RI ustunni o'qiydigan qilib o'zgartirilsa (masalan
    `'market_id'`) qiymat BARIBIR `NOT NULL` bo'lardi va (b) YASHIL
    qolardi — audit esa butunlay boshqa identifikatorga ishora qilardi.

    Tenglik esa aynan shu shoxni yopadi: audit qatori HAQIQATAN o'sha
    sozlama qatoriga ishora qiladi.

    ⚠ `market_id` VA `id` ATAYIN FARQ QILADI (ikkalasi ham `uuid`, lekin
      boshqa qiymat), ya'ni bu tenglik TASODIFAN bajarilmaydi.
    =========================================================================
    """
    market_id = market_domain.market_a.market_id

    try:
        await _bind_twice(app_sessionmaker, market_id=market_id)

        settings_row = sync_owner_conn.execute(SETTINGS_ROW, (str(market_id),)).fetchone()
        assert settings_row is not None, "sozlama qatori yozilmagan"
        settings_id = UUID(str(settings_row[0]))

        sync_owner_conn.execute(SET_MARKET, (str(market_id),))
        rows = sync_owner_conn.execute(SETTINGS_AUDIT_ROWS, (str(market_id),)).fetchall()
        assert rows, "audit qatori yo'q — quyidagi tenglik bo'sh rost bo'lib qolardi"

        audit_row_ids = {UUID(str(row_id)) for row_id, _ in rows}

        assert audit_row_ids == {settings_id}, (
            f"audit `row_id` lari {sorted(map(str, audit_row_ids))}, sozlama "
            f"qatorining `id` si esa {settings_id}. Audit qatori BOSHQA "
            "identifikatorga ishora qilyapti — ya'ni «qaysi qator "
            "o'zgardi?» savoli hamon javobsiz."
        )

        # ⛔ NAZORAT: `row_id` `market_id` NING NUSXASI EMAS. Usiz
        #   yuqoridagi tenglik `fn_audit_row()` noto'g'ri ustunni
        #   o'qiydigan holatda ham rost bo'lishi mumkin edi — agar
        #   `id` tasodifan `market_id` ga teng bo'lsa.
        assert settings_id != market_id, (
            "sozlama qatorining `id` si `market_id` ga TENG — bu holatda "
            "yuqoridagi tenglik `fn_audit_row()` noto'g'ri ustunni "
            "o'qiganda ham rost bo'lardi va nazorat yo'qolardi."
        )
    finally:
        sync_owner_conn.execute(
            "DELETE FROM audit_log WHERE table_name = 'market_notification_settings' "
            "AND market_id = %s",
            (str(market_id),),
        )
        cleanup_notification_domain(sync_owner_conn, market_ids=[market_id])
