"""Tenant izolyatsiyasi META-TESTLARI — rol invariantlari (FOUND-02).

Bu 1-fazaning eng qimmatli artefaktlaridan biri: u keyingi 7 fazada RLS
regressiyasini doimiy ushlab turadi.

NEGA ROLLAR, NEGA POLICY EMAS:
`FORCE ROW LEVEL SECURITY` faqat jadval EGASINI policy'ga bo'ysundiradi.
Superuser va `BYPASSRLS` atributli rollar RLS'ni HAR DOIM chetlab o'tadi —
va agar test fixture'i o'sha rol bilan ulansa, keyingi barcha RLS testlari
YOLG'ON-YASHIL beradi. Shuning uchun rol invariantlari birinchi qulflanadi.

SXEMA INVARIANTLARI (01-04): bu fayl endi rol invariantlaridan tashqari
SXEMA invariantlarini ham qulflaydi va ular HAR YANGI JADVALNI avtomatik
qamrab oladi — ro'yxat qo'lda yuritilmaydi, `pg_catalog` dan o'qiladi.
Yangi jadval qo'shgan odam RLS'ni unutsa, u testni "yangilashi" kerak
bo'ladi, ya'ni unutish ko'rinmas emas, ATAYIN qilingan harakatga aylanadi.

Istisnolar YAGONA manbada — `sbozor_core.schema_contract.GLOBAL_TABLES`.
Ro'yxat bu faylda TAKRORLANMAYDI.
"""

from __future__ import annotations

import re
from pathlib import Path

import psycopg
import pytest
from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.models.identity import LOCALE_VALUES, ROLE_VALUES
from sbozor_core.schema_contract import (
    AUDITED_TABLES,
    FINANCIAL_TABLES,
    GLOBAL_TABLES,
    NON_POSITIVE_MONEY_TABLES,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from migrations.helpers import audit_trigger_name

pytestmark = pytest.mark.tenancy

TENANT_GUC = "app.market_id"

# `market_id` bilan BOSHLANMASLIGI ruxsat etilgan indekslar. Har biri uchun
# sabab shu yerda yozilishi SHART — ro'yxat o'sib ketsa, u sharh bilan
# birga code review'da ko'rinadi.
INDEX_EXCEPTIONS = {
    # Refresh cookie kelganda bozor HALI noma'lum: token aynan shu global
    # kalit bo'yicha topiladi va bozor undan keyin aniqlanadi.
    "uq_refresh_tokens_jti",
    # --- 3-faza, `0012_nvr_domain`. IKKALASI HAM ATAYIN GLOBAL. ---
    #
    # D-07: ikkita bozor bir xil `tunnel_subnet` e'lon qilsa VPS ning
    # marshrut jadvali chalkashadi va A bozorining trafigi B ga ketishi
    # mumkin — ya'ni tenant izolyatsiyasi TARMOQ darajasida buzilardi
    # (T-03-19). To'qnashuv aynan bozorlar ORASIDA yuz beradi, shuning
    # uchun noyoblikni `(market_id, tunnel_subnet)` ga tushirish himoyani
    # BUTUNLAY yo'q qilardi: har bozor o'z ichida noyob bo'lardi va
    # muammo sezilmasdan qolardi. Indeks qisman (`IS NOT NULL`) — subnet
    # hali e'lon qilinmagan qurilmalar bir-biriga xalaqit bermaydi.
    "uq_nvr_devices_tunnel_subnet_global",
    # go2rtc BITTA jarayon va uning oqim nomlari fazosi BARCHA bozorlar
    # uchun UMUMIY (`03-RESEARCH.md` D.13). Ya'ni `stream_name` ning
    # noyobligi tenant ichida emas, PLATFORMA bo'yicha bo'lishi shart —
    # aks holda ikki bozorning oqimi go2rtc'da bir-birining ustiga
    # yozilardi va B bozorining direktori A bozorining kamerasini ko'rib
    # qolishi mumkin edi. Nom `cam_<uuid>` shaklida hosil qilinadi.
    "uq_cameras_stream_name",
    # --- 4-faza, `0014_snapshot_domain` (W0-8). ---
    #
    # Kechikkan kadr olishning WATCHDOG'i BARCHA BOZORLAR ustidan
    # yuradi: u «`scheduled_at` + grace o'tgan, lekin hamon `pending`
    # yoki `running`» qatorlarni izlaydi va bu so'rovda `market_id`
    # UMUMAN YO'Q — chunki savol «qaysi bozorda?» emas, «umuman
    # nimadir osilib qoldimi?». Indeksni `market_id` bilan boshlash uni
    # o'sha so'rov uchun BUTUNLAY FOYDASIZ qilardi (rejalashtiruvchi
    # birinchi ustunsiz undan foydalana olmaydi) va watchdog bozorlar
    # soni o'sgani sari to'liq skanga o'tardi.
    #
    # Bu `uq_nvr_devices_tunnel_subnet_global` bilan BIR XIL SINF, lekin
    # farqi bor va u yozib qo'yilishi kerak: tunnel subneti — TENANT
    # IZOLYATSIYASINING chegarasi (T-03-19), bu esa ISH REJASINING
    # chegarasi. Ya'ni bu istisno xavfsizlik da'vosini SUSAYTIRMAYDI:
    # watchdog faqat identifikatorlarni oladi va har qanday keyingi
    # o'qish odatdagidek RLS ostidan o'tadi (04-07).
    "ix_capture_runs_overdue",
    # --- 4-faza, `0014_snapshot_domain` (D-16 / T-04-17). ---
    #
    # ⚠ BU ISTISNO OPTIMIZATSIYA EMAS — U TUZILMAVIY ZARURAT.
    #
    # `uq_snapshots_billable_anchor` `(id, is_billable)` ustida va u
    # BOSHQA FAZA uchun mavjud: 5-fazada `occupancy_events` AYNAN shu
    # juftlikka kompozit FK qo'yadi
    #
    #     FOREIGN KEY (snapshot_id, snapshot_is_billable)
    #         REFERENCES snapshots (id, is_billable)
    #
    # va `CHECK (snapshot_is_billable)` bilan birga yaroqsiz kadrga
    # bandlik dalilini bog'lashni IMKONSIZ qiladi. FK NISHONI esa
    # havola qiluvchi ustunlar bilan AYNAN mos kelishi shart — ya'ni
    # konstraytga `market_id` ni oldindan qo'shish uni 5-fazaning FK'si
    # UCHUN YAROQSIZ qilardi. Boshqacha aytganda: bu indeksni «tuzatish»
    # ning yagona yo'li D-16 ning butun kafolatini olib tashlash bo'lardi.
    #
    # Yuqoridagi ikkita istisnodan FARQI: ular SO'ROV YO'LI (indeks
    # rejalashtiruvchi uchun), bu esa umuman so'rov yo'li EMAS —
    # `snapshots` ni `market_id` bo'yicha izlaydigan har bir so'rov
    # `uq_snapshots_market_id_capture_run_id` yoki
    # `uq_snapshots_market_id_object_key` dan foydalanadi, ikkalasi ham
    # `market_id` bilan BOSHLANADI. Bu konstrayt esa faqat FK nishoni
    # sifatida o'qiladi va tenant filtrlash uchun HECH QACHON
    # ishlatilmaydi, ya'ni istisno P9 ning ishlash da'vosini ham
    # susaytirmaydi.
    #
    # Shakl `04-01` ning W0-1 zondi bilan HAQIQIY `postgres:18.4` da
    # o'lchangan (`BILLABLE_ANCHOR_SUPPORTED = true`).
    "uq_snapshots_billable_anchor",
    # --- 5-faza, `0018_occupancy_domain` (D-17.3 / T-05-17). ---
    #
    # ⚠ UCHALASI HAM `uq_snapshots_billable_anchor` BILAN BIR SINFDA:
    #   ular SO'ROV YO'LI EMAS, KAFOLAT KONSTRAYTI. Hech biri tenant
    #   filtrlash uchun ishlatilmaydi — har bir o'qish so'rovi
    #   `market_id` bilan boshlanadigan boshqa indeksdan foydalanadi
    #   (`uq_review_assignments_market_id_id`,
    #   `uq_occupancy_events_market_id_id` va h.k.).
    #
    # (a) «BITTA HODISA IKKI NAVBATDA BO'LA OLMAYDI». Da'vo tenant
    #     chegarasiga bog'liq BO'LMASLIGI kerak: `(market_id,
    #     occupancy_event_id)` shakli bugun bir xil natija berardi
    #     (`occupancy_events.id` global noyob), lekin u kafolatni IKKINCHI
    #     faktga bog'lab qo'yardi va o'sha fakt o'zgargan kuni «bir hodisa
    #     — bir navbat» qoidasi JIMGINA bo'shardi. Poyga DB'ga topshirilgan
    #     (`nvr_repo.py:509-517` naqshi), ya'ni bu konstrayt ilova
    #     mantig'ining O'RNIGA turadi, uning yonida emas.
    "uq_review_assignments_occupancy_event_id",
    # (b) «BITTA TOPSHIRIQQA BITTA JAVOB» — (a) bilan bir xil sabab.
    #     Ikkinchi javob o'zgarmaslik triggerini `INSERT` orqali chetlab
    #     o'tish yo'li bo'lardi: tahrirlash o'rniga ikkinchi qator
    #     yoziladi va «qaysi biri hisobga kiradi?» savoli javobsiz qoladi.
    "uq_zone_reviews_review_assignment_id",
    # (c) KO'R AUDIT LANGARI — `(id, queue_kind)`. Bu konstrayt
    #     `uq_snapshots_billable_anchor` ning AYNAN takrori va u ham
    #     TUZILMAVIY ZARURAT: `zone_reviews` `(review_assignment_id,
    #     queue_kind)` juftligiga kompozit FK qo'yadi, FK NISHONI esa
    #     havola qiluvchi ustunlar bilan AYNAN mos kelishi shart — ya'ni
    #     konstraytga `market_id` ni qo'shish uni FK uchun YAROQSIZ
    #     qilardi. Langar `zone_reviews.queue_kind` nusxasini HALOL
    #     qiladi; usiz D-17.3 ning `CHECK` i o'z nusxasiga ishonardi va
    #     nusxani `'uncertain'` deb yozish «ko'r, lekin ko'rsatilgan»
    #     qatoriga yo'l ochardi.
    "uq_review_assignments_queue_anchor",
}

EXPECTED_DEFINER_FUNCTIONS = {
    # 0001 — login bootstrap (O'QISH yuzasi, Pattern 2)
    "auth_find_login",
    "auth_memberships",
    "auth_list_markets",
    "auth_user_state",
    # 0003 — sessiya va parol (YOZISH yuzasi). `refresh_tokens` ham shu
    # yerda, chunki refresh cookie kelganda bozor hali noma'lum va RLS
    # `jti` bo'yicha global qidiruvni 0 qatorga tushiradi.
    "auth_find_login_by_id",
    "auth_update_password_hash",
    "auth_set_active",
    "auth_refresh_issue",
    "auth_refresh_find",
    "auth_refresh_rotate",
    "auth_refresh_revoke_family",
    "auth_refresh_revoke_user",
    # 0004 — foydalanuvchi boshqaruvi va profil. `users` app-rolga butunlay
    # yopiq, ya'ni yaratish, profil o'qish va til saqlash ham shu yuzadan
    # o'tadi; `auth_list_markets_full` esa `timezone` bilan bozor ro'yxati.
    "auth_create_user",
    "auth_set_locale",
    "auth_list_users",
    "auth_list_markets_full",
    # 0005 — platforma-global (`market_id IS NULL`) audit qatorlari. Bu
    # funksiya boshqalardan farqli o'laroq RLS QO'YILGAN jadvalni o'qiydi,
    # ya'ni u yolg'iz o'zi yetarli emas: `audit_read_platform` policy'si
    # bilan juftlikda ishlaydi (pastdagi alohida test).
    "auth_list_platform_audit",
    # 0007 — bozor hayot sikli (Pattern 6). `sbozor_app` ga `markets` da
    # FAQAT `SELECT` grant'i berilgan va policy predikati `id =
    # app.market_id`, ya'ni yangi bozor yaratishga ikki mustaqil to'siq bor —
    # yagona yo'l shu uchta funksiya.
    #
    # ⚠ `market_is_open` bu ro'yxatga HECH QACHON QO'SHILMAYDI: u ATAYIN
    # `SECURITY DEFINER` EMAS (u CHAQIRUVCHI huquqi bilan ishlashi va RLS
    # ostida qolishi kerak, aks holda bir bozor boshqasining bayram jadvalini
    # o'qiy olardi — T-02-22/T-02-41). Uning INVOKER ekani
    # `test_market_domain_meta.py::test_market_is_open_is_not_security_definer`
    # da ALOHIDA va TESKARI yo'nalishda qulflangan: u yerdagi test
    # `prosecdef` ROSTGA aylansa qizaradi. Ya'ni nomni "unutilgan" deb bu
    # yerga qo'shish ikkita testni bir vaqtda buzadi — biri talab qiladi,
    # ikkinchisi taqiqlaydi.
    "market_create",
    "market_activate",
    "market_rename",
    # 0010 — qoralama bozorni o'chirish. `SECURITY DEFINER`, chunki u o'nta
    # domen jadvalidan va `markets` dan `DELETE` qiladi; `sbozor_app` da esa
    # `markets` ustida faqat `SELECT` grant'i bor (T-02-45).
    "market_delete_draft",
}

# `AUDITED_TABLES` da RO'YXATGA OLINGAN, lekin jadval hali TUG'ILMAGAN nomlar.
#
# Reyestr (`sbozor_core.schema_contract.AUDITED_TABLES`) 2-fazaning boshida,
# birinchi migratsiyadan OLDIN to'ldirildi — ATAYIN. Teskari tartib (avval
# migratsiya, keyin reyestr) darvozani vaqtincha ochiq qoldirardi: triggersiz
# jadval hech qayerda ko'rinmasdan o'tib ketishi mumkin bo'lardi.
#
# NEGA BU "SHUNCHAKI QIZIL TEST" EMAS: bu ro'yxat 02-05 va 02-06 migratsiyalari
# yozilgunga qadar 16 ta rejaning har birida `npm run test:tenancy` ni qizil
# qilib turardi va o'sha 16 reja uchun darvoza SIGNAL BERMAY qolardi — "mening
# o'zgarishim tenancy'ni buzdimi yoki bu o'sha ma'lum qizilmi?" savoliga javob
# yo'qolardi. Buzilgan darvoza — darvoza emas.
#
# Ro'yxat IKKI TOMONLAMA qulflangan (pastdagi `==` solishtiruvi):
#   * trigger ULANSA  -> `missing` kichrayadi -> test QIZARADI va migratsiya
#     muallifini shu ro'yxatdan nomni o'chirishga majbur qiladi. Ya'ni qarz
#     jimgina "yopilib" ketolmaydi.
#   * mavjud trigger YO'QOLSA (masalan `user_market_roles`) -> `missing`
#     kattalashadi -> test QIZARADI. Ya'ni amaldagi kafolat susaymaydi.
#
# Bu `INDEX_EXCEPTIONS` va `POLICY_TENANT_GUC_EXCEPTIONS` bilan bir xil naqsh:
# istisno testda, sababi yozma, o'zgartirish code review'da ko'zga tashlanadi.
PENDING_AUDIT_TRIGGERS: frozenset[str] = frozenset()
"""`AUDITED_TABLES` ga OLINGAN, lekin jadvali hali TUG'ILMAGAN nomlar.

✅ QARZ YOPILDI (`06-04` / T2, 2026-08-10) — `0020_billing_domain` BILAN
BIR COMMITDA. `06-04` / T1 `charge_adjustments` va `cashier_shifts` ni
`sbozor_core.schema_contract.AUDITED_TABLES` ga qo'shib, AYNI VAQTDA shu
yerga ham yozgan edi (OP-4); `0020` endi `attach_audit_trigger()` ni
chaqirdi, ya'ni `missing` bo'shadi va ikkala nom bu yerdan O'CHIRILDI.
Ro'yxat yana BO'SH.

⛔ IKKALA YO'NALISH HAM QULFLANGAN: nomni bu yerda qoldirish `closed`
asserti bilan qizartirardi, `AUDITED_TABLES` ga qo'shib bu yerga
yozmaslik esa `regressed` bilan. Ya'ni `test_audited_tables_have_trigger`
`06-04` / T1 dan T2 gacha UZLUKSIZ YASHIL turdi — «kutilgan qizil» holat
HECH QACHON bo'lmadi.

✅ OLDINGI QARZ YOPILGAN (`05-05` / T2, 2026-08-09). `0018_occupancy_domain`
`camera_zones` va `zone_reviews` ga audit triggerini ULADI, ya'ni ikkala
nom O'SHA MIGRATSIYA BILAN BIR COMMITDA bu yerdan O'CHIRILGAN edi. Bu
`04-01` → `04-03` juftligining (`snapshot_schedules`,
`snapshot_schedule_slots`) AYNAN takrori va uchinchi marta qo'llanishi.

⚠ NOMNI UNUTIB QOLDIRISH TESTNI TESKARI YO'NALISHDAN QIZARTIRARDI:
solishtiruv `missing == PENDING_AUDIT_TRIGGERS` (pastdagi `closed`
asserti), ya'ni «trigger ulandi, lekin nom hamon ro'yxatda» holati ham
qizil beradi. Qulf IKKI TOMONLAMA.

⚠ BU RO'YXATGA YANGI NOM QO'SHISH — OXIRGI CHORA, ODATIY QADAM EMAS.
Reyestrga (`AUDITED_TABLES`) jadval qo'shilgan, lekin
`attach_audit_trigger()` hali chaqirilmagan HOLAT faqat jadval KEYINGI
migratsiyada tug'ilganda ma'noli — `05-01` da AYNAN shu holat edi: u
Wave 0 reja va birorta migratsiya YOZMAYDI, ya'ni
`attach_audit_trigger("camera_zones")` ni chaqirishning FIZIK imkoni
yo'q edi (jadval hali mavjud emas). Bir migratsiya ichida ikkalasini ham
qilish mumkin bo'lsa, ro'yxat BO'SH qolishi kerak.

⛔ «KUTILGAN QIZIL» HOLAT HECH QACHON BO'LMADI va bu farq butun
mexanizmning mazmuni. Ro'yxat va amaldagi triggerlar AYNI COMMITDA
tenglashdi:

  * `05-01` / T1 — `AUDITED_TABLES` ga ikki nom qo'shildi VA ular shu
    yerda: `missing == PENDING_AUDIT_TRIGGERS`, test YASHIL;
  * `05-05` / T2 (`0018`) — triggerlar ulandi, `missing` bo'shadi va
    nomlar shu yerdan o'chirildi: yana YASHIL.

Ya'ni `test_audited_tables_have_trigger` `05-01` dan `05-05` gacha
UZLUKSIZ yashil turdi va oraliqdagi to'rt reja uchun darvoza SIGNAL
BERISHDA DAVOM ETDI. 2-fazada qarz o'n olti reja davomida darvozani qizil
qilib turgan va o'sha o'n olti reja uchun darvoza SIGNAL BERMAY qolgan
edi — yuqoridagi izohdagi «Buzilgan darvoza — darvoza emas» bandi aynan
shu haqda."""

# Ilova roliga tenant predikatisiz ruxsat beruvchi policy'lar. Har biri uchun
# sabab SHU YERDA yozilishi SHART — istisno qo'shish code review'da ko'zga
# tashlanadigan, ataylab qilingan harakat bo'lib qolsin.
POLICY_TENANT_GUC_EXCEPTIONS = {
    # `audit_log` ga YOZISH hech qachon bloklanmasligi kerak: tenant
    # kontekstisiz bajarilgan har qanday o'zgarish (fon job, migratsiya,
    # admin skripti) aks holda audit yozuvini jimgina yo'qotardi — ya'ni eng
    # kam nazorat qilinadigan yo'l eng kam iz qoldirardi. Istisno FAQAT
    # `WITH CHECK` ga tegishli; O'QISH (`audit_read`) to'liq tenant-scoped
    # va u pastdagi `test_audit_read_policy_is_tenant_scoped` bilan alohida
    # qulflangan.
    ("audit_log", "audit_append"),
}

# (policyname, roles, qual, with_check)
type PolicyRow = tuple[str, list[str], str, str | None]


def _role_flags(conn: Connection[TupleRow], rolname: str) -> tuple[bool, bool]:
    """`(rolsuper, rolbypassrls)` juftligini qaytaradi."""
    row = conn.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s",
        (rolname,),
    ).fetchone()
    assert row is not None, f"{rolname} roli mavjud emas — ops/db/init/01-roles.sql bajarilmagan"
    return bool(row[0]), bool(row[1])


def test_app_role_cannot_bypass_rls(sync_app_conn: Connection[TupleRow]) -> None:
    """`sbozor_app` RLS'ni chetlab o'ta olmaydi (T-01-01)."""
    is_super, can_bypass = _role_flags(sync_app_conn, "sbozor_app")
    assert not is_super, "sbozor_app SUPERUSER — tenant izolyatsiyasi umuman yo'q"
    assert not can_bypass, "sbozor_app BYPASSRLS — RLS policy'lari ta'sirsiz qoladi"


def test_owner_role_is_not_superuser(sync_app_conn: Connection[TupleRow]) -> None:
    """`sbozor_owner` (migratsiya roli) ham superuser emas."""
    is_super, can_bypass = _role_flags(sync_app_conn, "sbozor_owner")
    assert not is_super, "sbozor_owner SUPERUSER — migratsiyalar RLS'ni chetlab o'tadi"
    assert not can_bypass, "sbozor_owner BYPASSRLS — FORCE ROW LEVEL SECURITY ma'nosiz bo'ladi"


async def test_app_engine_connects_as_sbozor_app(app_engine: AsyncEngine) -> None:
    """Fixture'ning O'ZINI himoyalaydi (T-01-02).

    Agar kimdir `app_engine` ni `superuser_url` ga qaytarsa, bu test yiqiladi
    va CI to'xtaydi — RLS testlari jimgina yolg'on-yashil bo'lib qolmaydi.
    """
    async with app_engine.connect() as conn:
        current_user = (await conn.execute(text("SELECT current_user"))).scalar_one()

    assert current_user == "sbozor_app", (
        f"app_engine `{current_user}` bilan ulangan, `sbozor_app` bilan emas — "
        "RLS testlari endi hech narsani isbotlamaydi"
    )


def test_app_cannot_disable_triggers(sync_app_conn: Connection[TupleRow]) -> None:
    """`sbozor_app` audit triggerlarini o'chira olmaydi (T-01-05).

    `SET session_replication_role = replica` — triggerlarni butun sessiya uchun
    o'chirish yo'li. Ilova roli uni o'zgartira olsa, audit jurnali chetlab
    o'tiladi.
    """
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as excinfo:
        sync_app_conn.execute("SET session_replication_role = replica")

    assert "session_replication_role" in str(excinfo.value)


def test_public_schema_create_revoked_from_public(sync_app_conn: Connection[TupleRow]) -> None:
    """`sbozor_app` `public` sxemada obyekt yarata olmaydi (T-01-06)."""
    row = sync_app_conn.execute(
        "SELECT has_schema_privilege('sbozor_app', 'public', 'CREATE')"
    ).fetchone()
    assert row is not None
    assert row[0] is False, (
        "sbozor_app `public` sxemada CREATE huquqiga ega — RLS'siz yordamchi "
        "jadval yaratib izolyatsiyani chetlab o'tish mumkin"
    )


def test_btree_gist_extension_is_installed(sync_app_conn: Connection[TupleRow]) -> None:
    """`btree_gist` bazada MAVJUD — ya'ni init qadami haqiqatan bajarilgan.

    `ops/db/init/00-extensions.sql` prod'da `docker-entrypoint-initdb.d`
    orqali, testda esa `_bootstrap_extensions` fixture'i orqali ishlaydi.
    Ikkinchisi jimgina o'chirilsa yoki fixture bog'liqligi uzilsa, sabab
    faqat 02-05 migratsiyasi yozilganda — ya'ni bir necha reja keyin —
    ko'rinardi. Bu test uni SHU ZAHOTI ko'rsatadi.

    Kengaytma `stall_assignments` dagi `EXCLUDE USING gist (market_id
    WITH =, stall_id WITH =, period WITH &&)` uchun kerak: `uuid`/`date`
    skalyar tiplarining GiST operator klasslarini aynan u beradi.

    `sync_app_conn` ATAYIN — `pg_extension` ni ilova roli ham o'qiy oladi
    va tekshiruv aynan ilova ko'radigan haqiqatga tegishli.
    """
    row = sync_app_conn.execute(
        "SELECT extname FROM pg_extension WHERE extname = 'btree_gist'"
    ).fetchone()
    assert row is not None, (
        "`btree_gist` kengaytmasi yo'q — `ops/db/init/00-extensions.sql` "
        "bajarilmagan. `sbozor_owner` uni O'ZI o'rnata olmaydi "
        "(`permission denied to create extension`), ya'ni migratsiya bu "
        "holatni tuzata olmaydi."
    )


def test_no_bypassrls_role_exists(sync_app_conn: Connection[TupleRow]) -> None:
    """Klasterda superuser bo'lmagan `BYPASSRLS` roli YO'Q (D-06 / T-01-24).

    Platforma admini bozorni TANLAB kiradi va tanlagan bozorining oddiy
    tenant policy'siga bo'ysunadi. `BYPASSRLS` roli paydo bo'lishi — bu
    qarorni jimgina bekor qilish yo'li, shuning uchun butun klaster
    tekshiriladi, faqat ma'lum ikki rol emas.
    """
    rows = sync_app_conn.execute(
        "SELECT rolname FROM pg_roles WHERE rolbypassrls AND NOT rolsuper"
    ).fetchall()
    assert rows == [], (
        f"BYPASSRLS atributli rol(lar) topildi: {[r[0] for r in rows]} — "
        "ular RLS'ni butunlay chetlab o'tadi va D-06 ni buzadi"
    )


# ===========================================================================
# SXEMA INVARIANTLARI (01-04) — har yangi jadval avtomatik qamraladi
# ===========================================================================


def _base_tables(conn: Connection[TupleRow]) -> list[str]:
    """`public` sxemadagi barcha oddiy jadvallar."""
    rows = conn.execute(
        "SELECT c.relname FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind = 'r' "
        "ORDER BY c.relname"
    ).fetchall()
    return [row[0] for row in rows]


def _has_column(conn: Connection[TupleRow], table: str, column: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = %s AND a.attname = %s "
        "AND a.attnum > 0 AND NOT a.attisdropped",
        (table, column),
    ).fetchone()
    return row is not None


def _rls_flags(conn: Connection[TupleRow], table: str) -> tuple[bool, bool]:
    row = conn.execute(
        "SELECT c.relrowsecurity, c.relforcerowsecurity FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = %s",
        (table,),
    ).fetchone()
    assert row is not None, f"{table} jadvali `pg_class` da topilmadi"
    return bool(row[0]), bool(row[1])


def _policies(conn: Connection[TupleRow], table: str) -> list[PolicyRow]:
    rows = conn.execute(
        "SELECT policyname, roles, qual, with_check FROM pg_policies "
        "WHERE schemaname = 'public' AND tablename = %s ORDER BY policyname",
        (table,),
    ).fetchall()
    return [(r[0], list(r[1]), r[2], r[3]) for r in rows]


def test_every_table_is_tenant_scoped(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """Har bir jadval: `market_id` + RLS ENABLE + FORCE + policy.

    Uchtasi ham kerak va uchtasi ham ALOHIDA buzilishi mumkin:
      * `market_id` yo'q -> jadval umuman tenant'ga bog'lanmagan;
      * ENABLE yo'q      -> policy TA'SIRSIZ, hamma narsa ochiq (Pitfall 10);
      * FORCE yo'q       -> ega (migratsiya roli) policy'dan chetda qoladi;
      * policy yo'q      -> RLS bor, lekin deny-all (fail-closed, lekin ilova ishlamaydi).
    """
    tables = _base_tables(sync_app_conn)
    assert tables, "`public` sxemada birorta jadval yo'q — migratsiya bajarilmagan"

    problems: list[str] = []
    checked = 0
    for table in tables:
        if table in GLOBAL_TABLES:
            continue
        checked += 1
        if not _has_column(sync_app_conn, table, "market_id"):
            problems.append(f"{table}: `market_id` ustuni yo'q")
            continue
        enabled, forced = _rls_flags(sync_app_conn, table)
        if not enabled:
            problems.append(f"{table}: `ENABLE ROW LEVEL SECURITY` yo'q")
        if not forced:
            problems.append(f"{table}: `FORCE ROW LEVEL SECURITY` yo'q")
        if not _policies(sync_app_conn, table):
            problems.append(f"{table}: birorta policy yo'q")

    assert checked > 0, (
        "birorta tenant jadval tekshirilmadi — GLOBAL_TABLES butun sxemani "
        "yutib yuborgan bo'lishi mumkin"
    )
    assert not problems, "Tenant invariantlari buzilgan:\n  " + "\n  ".join(problems)


def test_markets_rls_and_policy(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """`markets` MAXSUS HOLATINING alohida isboti (RESEARCH Open Question 4).

    `markets` `GLOBAL_TABLES` da, ya'ni yuqoridagi umumiy tsikldan chiqib
    ketadi. Istisno qilingan jadval tekshiruvsiz qolmasligi SHART, shuning
    uchun uning RLS'i va policy'si shu yerda qulflanadi: predikat
    `market_id = ...` EMAS, `id = ...` — chunki `markets` da tenant kaliti
    `id` ning O'ZI.
    """
    enabled, forced = _rls_flags(sync_app_conn, "markets")
    assert enabled, "markets: `ENABLE ROW LEVEL SECURITY` yo'q"
    assert forced, "markets: `FORCE ROW LEVEL SECURITY` yo'q"

    policies = _policies(sync_app_conn, "markets")
    assert policies, "markets: birorta policy yo'q"

    app_policies = [p for p in policies if "sbozor_app" in p[1]]
    assert app_policies, "markets: `sbozor_app` uchun policy yo'q"

    quals = " ".join(p[2] or "" for p in app_policies)
    # DIQQAT: `market_id` satri GUC NOMIDA ham bor (`app.market_id`), shuning
    # uchun tekshiruv USTUN havolasi bo'yicha — ya'ni `<ustun> =` shakli
    # bo'yicha — qilinadi, oddiy substring bo'yicha emas.
    assert re.search(r"\bid\s*=", quals), "markets policy'si `id` ustuni bilan solishtirmayapti"
    assert not re.search(r"\bmarket_id\s*=", quals), (
        "markets policy'si `market_id` USTUNIGA murojaat qilmoqda — bunday "
        "ustun yo'q, tenant kaliti `id` ning o'zi"
    )
    assert "NULLIF" in quals.upper(), (
        "markets policy'sida `NULLIF` yo'q — pool'dagi ulanishda "
        '`invalid input syntax for type uuid: ""` beradi (Pitfall 1)'
    )
    assert TENANT_GUC in quals, f"markets policy'si `{TENANT_GUC}` GUC'iga tayanmaydi"


def test_tenant_indexes_lead_with_market_id(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Tenant jadvallarining indekslari `market_id` bilan boshlanadi (P9).

    Ikkinchi qatlam filtri (`TenantScopedRepository`) har so'rovga
    `market_id = ...` qo'shadi; indeks boshqa ustundan boshlansa,
    rejalashtiruvchi uni ishlata olmaydi va bozor kattalashgan sari
    so'rovlar sekinlashadi.
    """
    rows = sync_app_conn.execute(
        "SELECT t.relname, i.relname, x.indisprimary, a.attname "
        "FROM pg_index x "
        "JOIN pg_class t ON t.oid = x.indrelid "
        "JOIN pg_class i ON i.oid = x.indexrelid "
        "JOIN pg_namespace n ON n.oid = t.relnamespace "
        "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = x.indkey[0] "
        "WHERE n.nspname = 'public' AND t.relkind = 'r' "
        "ORDER BY t.relname, i.relname"
    ).fetchall()

    problems: list[str] = []
    for table, index, is_primary, first_column in rows:
        if table in GLOBAL_TABLES or is_primary or index in INDEX_EXCEPTIONS:
            continue
        if first_column != "market_id":
            problems.append(f"{table}.{index}: birinchi ustun `{first_column}`, `market_id` emas")

    assert not problems, (
        "Indekslar `market_id` bilan boshlanmayapti:\n  "
        + "\n  ".join(problems)
        + "\n(atayin istisno bo'lsa `INDEX_EXCEPTIONS` ga sabab bilan qo'shing)"
    )


def test_security_definer_functions_pin_search_path(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Har bir `SECURITY DEFINER` funksiya `search_path` ni pin qiladi (T-01-23).

    Pin qilinmasa chaqiruvchi o'z sxemasida soxta `users` jadvali yaratib
    funksiyani unga qaratishi mumkin — klassik privilege escalation.
    Test butun `public` sxemani skanerlaydi, ya'ni kelajakdagi funksiyalar
    ham avtomatik qamraladi.
    """
    rows = sync_app_conn.execute(
        "SELECT p.proname, p.proconfig FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.prosecdef ORDER BY p.proname"
    ).fetchall()

    found = {row[0] for row in rows}
    assert found >= EXPECTED_DEFINER_FUNCTIONS, (
        f"kutilgan login funksiyalari yo'q: {sorted(EXPECTED_DEFINER_FUNCTIONS - found)}"
    )

    for name, proconfig in rows:
        assert proconfig, f"{name}: `SECURITY DEFINER`, lekin `proconfig` bo'sh"
        assert any(item.startswith("search_path=") for item in proconfig), (
            f"{name}: `SET search_path = ...` yo'q — privilege escalation vektori"
        )


def test_market_is_open_is_absent_from_definer_registry() -> None:
    """Reyestrning O'ZI qulflanadi: `market_is_open` bu ro'yxatga TUSHMASLIGI shart.

    Yuqoridagi test BAZANI tekshiradi (`pg_proc.prosecdef`), bu esa
    REYESTRNI — va aynan shu tartibda ikkalasi bir-birini yopadi.

    Nega yolg'iz baza tekshiruvi yetarli emas: `EXPECTED_DEFINER_FUNCTIONS`
    ga `market_is_open` qo'shilsa, yuqoridagi `found >= EXPECTED_...`
    da'vosi uni `SECURITY DEFINER` QILISHNI talab qilib qizarardi. Xatoni
    o'qigan keyingi ishlovchi uchun eng tabiiy "tuzatish" — migratsiyada
    funksiyaga `SECURITY DEFINER` qo'shish, ya'ni AYNAN T-02-41 ni ochish
    (u RLS'dan chiqadi va bir bozor boshqasining bayram jadvalini o'qiy
    oladi). Bu test o'sha yo'lni boshidayoq to'sadi va sababni aytadi.

    Funksiyaning haqiqiy huquq rejimi
    `test_market_domain_meta.py::test_market_is_open_is_not_security_definer`
    da qulflangan.
    """
    assert "market_is_open" not in EXPECTED_DEFINER_FUNCTIONS, (
        "`market_is_open` `EXPECTED_DEFINER_FUNCTIONS` ga qo'shilgan — u ATAYIN INVOKER "
        "(chaqiruvchi huquqi + RLS). Reyestr uni `SECURITY DEFINER` qilishga majburlaydi "
        "va bu T-02-41 ni ochadi. Nomni ro'yxatdan OLIB TASHLANG."
    )
    assert "market_delete_draft" in EXPECTED_DEFINER_FUNCTIONS, (
        "`market_delete_draft` reyestrdan tushib qolgan — u o'nta domen jadvalidan va "
        "`markets` dan `DELETE` qiladi, `sbozor_app` da esa bunday grant YO'Q (T-02-45)"
    )


def test_auth_memberships_returns_is_active(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`auth_memberships()` qaytish to'plamida `is_active boolean` bor (0006).

    NEGA BU ALOHIDA DARVOZA: funksiyaning IMZOSI (`auth_memberships(uuid)`)
    o'zgarmadi, faqat QAYTISH TIPI kengaydi. Ya'ni `EXPECTED_DEFINER_FUNCTIONS`,
    `GRANT_SIGNATURES` va mavjud bootstrap testlarining birortasi ham eski
    (uch ustunli) ta'rif tiklanib qolganini KO'RMAYDI: nom joyida, grant
    joyida, `search_path` joyida. Nosozlik faqat ilova qatlamida —
    `auth_repo.memberships()` da `column "is_active" does not exist` bo'lib
    chiqardi va sababi migratsiyada emas, repozitoriyda izlanardi.

    `pg_get_function_result()` bazadagi AMALDAGI ta'rifni o'qiydi, entity
    modulini emas — ya'ni test `0006` migratsiyasi HAQIQATAN bajarilganini
    tekshiradi, kod nusxasini emas.
    """
    row = sync_app_conn.execute(
        "SELECT pg_get_function_result('public.auth_memberships(uuid)'::regprocedure)"
    ).fetchone()

    assert row is not None, "`auth_memberships(uuid)` funksiyasi bazada yo'q"
    result_type = row[0]
    assert "is_active boolean" in result_type, (
        f"`auth_memberships()` qaytish to'plami: {result_type!r} — `is_active boolean` yo'q. "
        "Qoralama bozor (`markets.is_active = false`) a'zolik tarmog'ida "
        "'faol' deb yolg'on yorliqlanadi (UI-SPEC §12.1.1 X-2)"
    )


def test_app_role_policies_all_reference_tenant_guc(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`sbozor_app` ga tegishli HAR BIR policy tenant GUC'iga tayanadi.

    Bu — butun dizaynning qulfi: ilova roliga `USING (true)` bergan bitta
    policy barcha tenant izolyatsiyasini bir zarbada yo'q qiladi va boshqa
    hech qanday test buni ko'rmaydi (hamma so'rov "muvaffaqiyatli" qaytadi,
    faqat begona qatorlar bilan).
    """
    rows = sync_app_conn.execute(
        "SELECT tablename, policyname, roles, qual, with_check FROM pg_policies "
        "WHERE schemaname = 'public' ORDER BY tablename, policyname"
    ).fetchall()
    assert rows, "birorta policy yo'q — migratsiya bajarilmagan"

    problems: list[str] = []
    for table, policy, roles, qual, with_check in rows:
        role_names = set(roles)
        if not ({"sbozor_app", "public"} & role_names):
            continue
        if (table, policy) in POLICY_TENANT_GUC_EXCEPTIONS:
            continue
        for label, expression in (("USING", qual), ("WITH CHECK", with_check)):
            if expression is None:
                continue
            if TENANT_GUC not in expression:
                problems.append(f"{table}.{policy} {label}: `{TENANT_GUC}` ga murojaat yo'q")

    assert not problems, (
        "Ilova roliga tenant filtri qo'ymaydigan policy topildi:\n  "
        + "\n  ".join(problems)
        + "\n(atayin istisno bo'lsa `POLICY_TENANT_GUC_EXCEPTIONS` ga sabab bilan qo'shing)"
    )


def test_audit_read_policy_is_tenant_scoped(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`audit_append` istisnosi O'QISH tomoniga TARQALMAGAN (D-11).

    Yuqoridagi test `audit_log` uchun bitta istisnoga ruxsat beradi. Bu test
    o'sha istisnoning CHEGARASINI belgilaydi: `audit_log` da `SELECT`
    policy'si bo'lishi va u tenant GUC'iga tayanishi SHART. Aks holda
    "yozishni bloklab bo'lmaydi" degan to'g'ri qoida "hamma hammaning
    auditini o'qiy oladi" degan noto'g'ri natijaga aylanib ketardi.

    Shuningdek `UPDATE`/`DELETE` uchun policy YO'Q ekani tekshiriladi — bu
    o'zgarmaslikning 2-qatlami va u tasodifan qo'shilgan policy bilan
    jimgina yo'qoladi.

    UCHINCHI POLICY (`audit_read_platform`, 0005) — ATAYIN va u APP-ROLNING
    o'qish yuzasini KENGAYTIRMAYDI: u `TO sbozor_owner`, ya'ni `sbozor_app`
    uni umuman ishlata olmaydi, va u faqat `market_id IS NULL` qatorlarni
    ochadi — tenant qatorlari bilan kesishmaydi. Uning owner-only ekani
    pastdagi `test_audit_read_platform_is_owner_only` da alohida qulflanadi;
    bu yerda esa TO'PLAM qulflanadi: `w`/`d` komandali policy paydo bo'lishi
    (yoki bu uchtasidan biri yo'qolishi) darhol qizaradi.
    """
    rows = sync_app_conn.execute(
        "SELECT p.polname, p.polcmd FROM pg_policy p "
        "JOIN pg_class c ON c.oid = p.polrelid "
        "WHERE c.relname = 'audit_log' ORDER BY p.polname"
    ).fetchall()

    commands = {row[0]: row[1] for row in rows}
    assert commands == {
        "audit_append": "a",
        "audit_read": "r",
        "audit_read_platform": "r",
    }, (
        f"`audit_log` policy'lari kutilganidan farq qiladi: {commands} — "
        "`w` (UPDATE) yoki `d` (DELETE) policy'si paydo bo'lsa jadval "
        "egasiga qarshi o'zgarmaslikning 2-qatlami yo'qoladi"
    )

    read_qual = sync_app_conn.execute(
        "SELECT qual FROM pg_policies "
        "WHERE schemaname = 'public' AND tablename = 'audit_log' AND policyname = 'audit_read'"
    ).fetchone()
    assert read_qual is not None
    assert TENANT_GUC in (read_qual[0] or ""), (
        "`audit_read` policy'si tenant GUC'iga tayanmayapti — boshqa bozor "
        "auditi ko'rinadigan bo'lib qoladi"
    )


def test_audit_log_is_read_only_for_app_role(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """1-QATLAM: `sbozor_app` da faqat `SELECT` va `INSERT` huquqi bor (T-01-30).

    Bu qatlam BALAND OVOZDA ishlaydi (`permission denied`), qolgan uchtasi
    esa jimroq — shuning uchun u birinchi va eng muhim.
    """
    row = sync_app_conn.execute(
        "SELECT has_table_privilege('sbozor_app', 'audit_log', 'SELECT'), "
        "       has_table_privilege('sbozor_app', 'audit_log', 'INSERT'), "
        "       has_table_privilege('sbozor_app', 'audit_log', 'UPDATE'), "
        "       has_table_privilege('sbozor_app', 'audit_log', 'DELETE'), "
        "       has_table_privilege('sbozor_app', 'audit_log', 'TRUNCATE')"
    ).fetchone()
    assert row is not None
    can_select, can_insert, can_update, can_delete, can_truncate = row

    assert can_select, "sbozor_app `audit_log` ni o'qiy olmaydi — audit ekrani ishlamaydi"
    assert can_insert, "sbozor_app `audit_log` ga yoza olmaydi — trigger har DML da yiqiladi"
    assert not can_update, "sbozor_app `audit_log` ni TAHRIRLAY oladi (T-01-30)"
    assert not can_delete, "sbozor_app `audit_log` dan O'CHIRA oladi (T-01-30)"
    assert not can_truncate, "sbozor_app `audit_log` ni TRUNCATE qila oladi (T-01-32)"


def test_audit_trigger_function_is_not_security_definer(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`fn_audit_row()` ATAYIN `SECURITY DEFINER` EMAS (T-01-35).

    `audit_log` da `WITH CHECK (true)` policy'si va app-rolga `INSERT` grant'i
    bor, ya'ni trigger chaqiruvchi huquqi bilan bemalol yozadi. Ega huquqiga
    ko'tarish hech qanday qo'shimcha imkoniyat bermaydi, faqat
    privilege-escalation yuzasini ochadi.

    `search_path` esa SHUNDA HAM pin qilinishi shart: trigger DML qilayotgan
    sessiyaning `search_path` i bilan ishlaydi va chaqiruvchi o'z sxemasida
    soxta `audit_log` yaratib yozuvni o'sha yerga burib yuborishi mumkin.
    """
    rows = sync_app_conn.execute(
        "SELECT p.proname, p.prosecdef, p.proconfig FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.proname IN ('fn_audit_row', 'audit_immutable') "
        "ORDER BY p.proname"
    ).fetchall()

    found = {row[0] for row in rows}
    assert found == {"audit_immutable", "fn_audit_row"}, (
        f"audit trigger funksiyalari yo'q yoki nomi o'zgargan: {sorted(found)}"
    )

    for name, is_definer, proconfig in rows:
        assert not is_definer, (
            f"{name} `SECURITY DEFINER` bo'lib qolgan — bu ataylab qilingan "
            "qarorning bekor qilinishi (T-01-35)"
        )
        assert proconfig and "search_path=pg_catalog, public" in proconfig, (
            f"{name}: `SET search_path = pg_catalog, public` yo'q — chaqiruvchi "
            "soxta `audit_log` yaratib audit yozuvini burib yuborishi mumkin"
        )


def test_audit_log_business_date_is_stored_generated(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`audit_log.business_date` — STORED generated ustun (FOUND-05).

    `attgenerated = 's'` bo'lmasa ustun oddiy `date` bo'lib qoladi va uni
    ilova to'ldirishi kerak bo'ladi — ya'ni mintaqa arifmetikasi ikkinchi
    marta, boshqa qatlamda takrorlanadi va aynan yarim tun atrofida farq
    qiladi (Anti-Pattern 10).
    """
    row = sync_app_conn.execute(
        "SELECT a.attgenerated FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = 'audit_log' "
        "AND a.attname = 'business_date'"
    ).fetchone()
    assert row is not None, "`audit_log.business_date` ustuni yo'q"
    assert row[0] == "s", (
        f"`business_date` generated STORED emas (attgenerated={row[0]!r}) — "
        "biznes-kun endi DB kafolati emas"
    )


def test_owner_bootstrap_policies_are_owner_only(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`owner_bootstrap` policy'si FAQAT `sbozor_owner` ga berilgan.

    Bu policy `SECURITY DEFINER` login funksiyalari FORCE ostida bloklanib
    qolmasligi uchun bor (`migrations/entities/policies.py` da batafsil).
    U `sbozor_app` ga yoki `PUBLIC` ga kengaysa, ilova roli bir zarbada
    barcha bozorlarni ko'radi — shuning uchun rollar ro'yxati qulflanadi.
    """
    rows = sync_app_conn.execute(
        "SELECT tablename, roles FROM pg_policies "
        "WHERE schemaname = 'public' AND policyname = 'owner_bootstrap' "
        "ORDER BY tablename"
    ).fetchall()
    assert rows, "birorta `owner_bootstrap` policy yo'q"

    for table, roles in rows:
        assert set(roles) == {"sbozor_owner"}, (
            f"{table}.owner_bootstrap `{sorted(roles)}` rollariga berilgan — "
            "faqat `sbozor_owner` bo'lishi shart"
        )


def test_audit_read_platform_is_owner_only(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`audit_read_platform` FAQAT `sbozor_owner` ga va FAQAT `SELECT` uchun (Gap 5).

    Bu — 0005 ning butun xavfsizlik da'vosi bitta testda. Uchala shart
    ALOHIDA buzilishi mumkin va har biri boshqa nosozlik beradi:

      * rollar kengaysa (`sbozor_app` yoki `PUBLIC`) -> ilova roli
        platforma-global audit qatorlarini TO'G'RIDAN-TO'G'RI o'qiy oladi va
        `auth_list_platform_audit()` darvozasi ma'nosiz bo'lib qoladi;
      * komanda `ALL` ga aylansa -> egaga `UPDATE`/`DELETE` da qatorlar
        KO'RINADI va o'zgarmaslikning 2-qatlami yo'qoladi (aynan shu sababdan
        `audit_log` ga `owner_bootstrap` berilmagan);
      * predikat kengaysa (`market_id IS NULL` o'rniga `true`) -> policy
        BUTUN audit jurnalini ochadi, ya'ni `SECURITY DEFINER` funksiya
        orqali tenant qatorlari ham sizib chiqishi mumkin bo'lardi.

    Uchtasi ham `pg_policies` dan o'qiladi, kod ta'rifidan emas — ya'ni test
    fabrikaning nusxasini emas, BAZADAGI haqiqatni tekshiradi.
    """
    rows = sync_app_conn.execute(
        "SELECT roles, cmd, qual FROM pg_policies "
        "WHERE schemaname = 'public' AND tablename = 'audit_log' "
        "AND policyname = 'audit_read_platform'"
    ).fetchall()
    assert len(rows) == 1, (
        "`audit_read_platform` policy'si topilmadi — `market_id IS NULL` "
        "audit qatorlari yana hech kimga ko'rinmaydi (Gap 5)"
    )

    roles, cmd, qual = rows[0]

    assert set(roles) == {"sbozor_owner"}, (
        f"audit_read_platform `{sorted(roles)}` rollariga berilgan — faqat "
        "`sbozor_owner` bo'lishi shart, aks holda `sbozor_app` platforma-global "
        "qatorlarni to'g'ridan-to'g'ri o'qiy oladi"
    )
    assert cmd == "SELECT", (
        f"audit_read_platform komandasi `{cmd}` — `FOR ALL`/`UPDATE`/`DELETE` "
        "egaga o'zgartirish yo'lini ochadi va o'zgarmaslikning 2-qatlamini "
        "yo'q qiladi"
    )
    assert (qual or "").strip() == "(market_id IS NULL)", (
        f"audit_read_platform predikati `{qual}` — u AYNAN `market_id IS NULL` "
        "bo'lishi shart, aks holda policy tenant qatorlarini ham ochadi"
    )


def _check_literals(conn: Connection[TupleRow], constraint: str) -> set[str]:
    """Konstrayt ta'rifidagi matn literallarini ajratib oladi."""
    row = conn.execute(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = %s",
        (constraint,),
    ).fetchone()
    assert row is not None, f"{constraint} konstrayti topilmadi"
    return set(re.findall(r"'([^']+)'::text", row[0]))


def test_role_check_constraint_matches_enum(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """DB dagi rol ro'yxati `sbozor_core.enums.Role` bilan AYNAN mos.

    Enum'ga yangi rol qo'shilib migratsiya unutilsa, ilova o'sha rolni
    yozmoqchi bo'lganda `check constraint` xatosi bilan yiqilardi —
    va sabab kod bilan sxema orasidagi jimgina drift bo'lardi.
    """
    assert _check_literals(sync_app_conn, "ck_user_market_roles_roles_allowed") == set(ROLE_VALUES)


def test_locale_check_constraint_matches_enum(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """DB dagi til ro'yxati `sbozor_core.enums.Locale` bilan AYNAN mos (D-13)."""
    assert _check_literals(sync_app_conn, "ck_users_locale_allowed") == set(LOCALE_VALUES)


def test_audited_tables_have_trigger(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """`AUDITED_TABLES` reyestri va amaldagi triggerlar AYNAN mos.

    Reyestr (`sbozor_core.schema_contract`) va amaldagi DDL
    (`migrations/versions/*.py`) ikki alohida joyda yashaydi, ya'ni ular
    ajralib ketishi mumkin. Bu darvoza ikkalasini `pg_trigger` bilan
    solishtiradi: 2- va 6-fazalarda `payments` yoki `daily_charges`
    yaratilib `attach_audit_trigger()` unutilsa, CI shu yerda qizaradi —
    va bu "audit bor" degan yolg'on ishonchdan ancha arzon.

    Solishtiruv `not missing` EMAS, `missing == PENDING_AUDIT_TRIGGERS`:
    reyestr birinchi migratsiyadan OLDIN to'ldirilgan (2-faza), ya'ni hali
    tug'ilmagan jadvallar unda ATAYIN bor. Tenglik ikkala yo'nalishni ham
    qulflaydi — sabab va mexanika `PENDING_AUDIT_TRIGGERS` yonida.
    """
    rows = sync_app_conn.execute(
        "SELECT c.relname, t.tgname FROM pg_trigger t "
        "JOIN pg_class c ON c.oid = t.tgrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND NOT t.tgisinternal"
    ).fetchall()
    triggers = {(row[0], row[1]) for row in rows}

    missing = {
        table for table in AUDITED_TABLES if (table, audit_trigger_name(table)) not in triggers
    }

    regressed = missing - PENDING_AUDIT_TRIGGERS
    assert not regressed, (
        f"`AUDITED_TABLES` da bor, lekin audit triggeri YO'Q: {sorted(regressed)} — "
        "jadval o'zgarishlari izsiz qoladi (D-10)"
    )

    closed = PENDING_AUDIT_TRIGGERS - missing
    assert not closed, (
        f"{sorted(closed)} jadval(lar)iga audit triggeri ULANGAN, lekin ular hamon "
        "`PENDING_AUDIT_TRIGGERS` ro'yxatida — nomni o'sha ro'yxatdan O'CHIRING. "
        "Aks holda kelajakda trigger yo'qolsa bu test buni SEZMAY qolardi."
    )


CASCADE_REGISTRY_HINT = (
    "Tushib qolgan jadval `0014` qo'ngandan keyin qoralama bozorni o'chirishni "
    "chet el kaliti buzilishi bilan yiqitardi (W0-6) va sabab faqat ish paytida, "
    "admin ekranida ko'rinardi."
)
"""Tuzatish yo'riqnomasi ALOHIDA konstantada, assert ichidagi f-satrda EMAS.

`test_market_delete_guard.py::CASCADE_FIX_HINT` da o'rnatilgan qoida: ruff'ning
`S608` qoidasi SQL kalit so'zi bo'lgan formatlangan satrni «so'rov qurilishi»
deb hisoblaydi va bu yerda YOLG'ON-MUSBAT berardi (bu — xato XABARI, so'rov
emas). Matnni oddiy satrga ko'chirish qoidani chetlab o'tmaydi, uni
QO'LLANILMAYDIGAN qiladi.
"""

TENANT_REGISTRY_HINT = (
    "`ALL_ENTITIES` aynan `ALL_TENANT_TABLES` dan quriladi, ya'ni tushib qolgan "
    "jadval `tenant_isolation` policy'sisiz — RLS himoyasisiz — qolardi. "
    "Qo'shish `0014` bilan BIR OYNADA bajariladi (`04-03` / T2)."
)


def test_snapshot_registries_are_self_consistent(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """4-faza reyestrlari o'zaro MOS — jadval tug'ilishidan OLDIN (W0-5/W0-6).

    Uchta ro'yxat uch xil savolga javob beradi va ular AJRALIB KETISHI
    mumkin, chunki uchalasi qo'lda yuritiladi:

      * `SNAPSHOT_TENANT_TABLES`  -> RLS + policy tsikli (`0014`);
      * `SNAPSHOT_AUDITED_TABLES` -> audit triggeri (`AUDITED_TABLES` ning kichik to'plami);
      * `SNAPSHOT_DELETE_ORDER`   -> `market_delete_draft()` kaskadi (`0015`).

    ⚠ `ALL_TENANT_TABLES` TEKSHIRUVI SHARTLI va bu O'LCHOVGA asoslangan
      qaror — batafsili quyida, o'sha assertning yonida.

    ⚠ NEGA BU DARVOZA `test_market_delete_guard.py` NI TAKRORLAMAYDI. U
      yerdagi darvoza BAZANI o'qiydi (`pg_get_functiondef`), ya'ni u
      `0014` jadvallarni YARATGANDAN KEYIN ishlaydi. Bu esa REYESTRNI
      o'qiydi va BUGUNDAN ishlaydi: `SNAPSHOT_DELETE_ORDER` dan tushib
      qolgan jadval `04-03` da `0015` yozilayotganda emas, HOZIR
      ko'rinadi. Ikkalasi ketma-ket turadi, biri ikkinchisini yopadi.

    ⚠ IMPORT TEST FUNKSIYASINING ICHIDA — bu ataylab. Reyestr hali
      tug'ilmagan bosqichda modul darajasidagi import BUTUN FAYLNING
      yig'ilishini yiqitardi, ya'ni W0-5 ning ikki tomonlama qulfi
      (`test_audited_tables_have_trigger`) o'sha bosqichda umuman
      ishlamas va o'lchab bo'lmasdi.
    """
    from migrations.entities import (
        ALL_TENANT_TABLES,
        SNAPSHOT_AUDITED_TABLES,
        SNAPSHOT_DELETE_ORDER,
        SNAPSHOT_TENANT_TABLES,
    )

    assert len(SNAPSHOT_TENANT_TABLES) == 5, (
        f"`SNAPSHOT_TENANT_TABLES` da {len(SNAPSHOT_TENANT_TABLES)} jadval: "
        f"{list(SNAPSHOT_TENANT_TABLES)}. Kutilgani beshta (`04-PATTERNS.md` §S-1)."
    )
    assert len(set(SNAPSHOT_TENANT_TABLES)) == len(SNAPSHOT_TENANT_TABLES), (
        f"`SNAPSHOT_TENANT_TABLES` da dublikat bor: {list(SNAPSHOT_TENANT_TABLES)}"
    )

    # ⚠ O'ZI QUROLLANADIGAN DARVOZA — shartsiz `<=` EMAS, va bu ATAYIN.
    #
    # `ALL_ENTITIES` `ALL_TENANT_TABLES` dan quriladi, `alembic_utils` ning
    # komparatori esa har bir policy'ni HAQIQATAN yaratib ko'radi
    # (`simulate_entity`). Ya'ni jadval TUG'ILMASDAN OLDIN uni ro'yxatga
    # qo'shish `test_autogenerate_is_empty` ni `UndefinedTable` bilan
    # yiqitadi — O'LCHANGAN, 2026-08-04.
    #
    # Shuning uchun shart BAZAGA bog'lanadi: jadval bazada paydo bo'lgan
    # zahoti u ro'yxatda ham TALAB qilinadi. Bugun — yashil (jadvallar
    # yo'q); `0014` qo'ngan kuni — `04-03` ro'yxatni kengaytirmaguncha
    # QIZIL. Qarzning egasi ham, tetigi ham shu yerda.
    existing = {
        row[0]
        for row in sync_app_conn.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r'"
        ).fetchall()
    }
    born = set(SNAPSHOT_TENANT_TABLES) & existing
    assert born <= set(ALL_TENANT_TABLES), (
        f"jadval BAZADA bor, lekin `ALL_TENANT_TABLES` da yo'q: "
        f"{sorted(born - set(ALL_TENANT_TABLES))}. " + TENANT_REGISTRY_HINT
    )

    assert set(SNAPSHOT_DELETE_ORDER) == set(SNAPSHOT_TENANT_TABLES), (
        "kaskad tartibi tenant reyestriga mos emas.\n"
        f"  kaskadda yo'q: {sorted(set(SNAPSHOT_TENANT_TABLES) - set(SNAPSHOT_DELETE_ORDER))}\n"
        f"  ortiqcha:      {sorted(set(SNAPSHOT_DELETE_ORDER) - set(SNAPSHOT_TENANT_TABLES))}\n"
        + CASCADE_REGISTRY_HINT
    )
    assert len(SNAPSHOT_DELETE_ORDER) == len(set(SNAPSHOT_DELETE_ORDER)), (
        f"`SNAPSHOT_DELETE_ORDER` da dublikat bor: {list(SNAPSHOT_DELETE_ORDER)}"
    )

    # Tartib — bolalardan ota-onaga. `snapshots` `capture_runs` ga,
    # `capture_runs` `cameras` ga, `snapshot_schedule_slots` esa
    # `snapshot_schedules` ga tayanadi, ya'ni bola HAR DOIM oldinroq
    # turishi shart — aks holda funksiya o'z FK'siga urilib yiqilardi.
    order = list(SNAPSHOT_DELETE_ORDER)
    for child, parent in (
        ("snapshots", "capture_runs"),
        ("snapshot_schedule_slots", "snapshot_schedules"),
    ):
        assert order.index(child) < order.index(parent), (
            f"`{child}` `{parent}` dan KEYIN o'chirilyapti — kaskad o'z chet el "
            "kalitiga uriladi. Tartib bolalardan ota-onaga bo'lishi shart."
        )

    assert set(SNAPSHOT_AUDITED_TABLES) < set(SNAPSHOT_TENANT_TABLES), (
        "`SNAPSHOT_AUDITED_TABLES` tenant reyestrining QAT'IY kichik to'plami "
        f"bo'lishi shart. Topilgani: {list(SNAPSHOT_AUDITED_TABLES)}. Uchta "
        "hodisa jurnali (`capture_runs`, `snapshots`, `alert_events`) auditdan "
        "ATAYIN chiqarilgan — sabab `schema_contract.AUDITED_TABLES` docstringida."
    )
    assert set(SNAPSHOT_AUDITED_TABLES) <= AUDITED_TABLES, (
        f"audit reyestriga tushmagan nom(lar): "
        f"{sorted(set(SNAPSHOT_AUDITED_TABLES) - AUDITED_TABLES)} — "
        "`SNAPSHOT_AUDITED_TABLES` va `AUDITED_TABLES` ajralib ketgan."
    )


OCCUPANCY_CASCADE_HINT = (
    "Tushib qolgan jadval `0018` qo'ngandan keyin qoralama bozorni o'chirishni "
    "chet el kaliti buzilishi bilan yiqitardi (W0-6) va sabab faqat ish paytida, "
    "admin ekranida ko'rinardi. Kaskad `0019` da yoziladi (`05-05` / T3)."
)
"""Tuzatish yo'riqnomasi ALOHIDA konstantada — sabab `CASCADE_REGISTRY_HINT` da."""

OCCUPANCY_TENANT_REGISTRY_HINT = (
    "`ALL_ENTITIES` aynan `ALL_TENANT_TABLES` dan quriladi, ya'ni tushib qolgan "
    "jadval `tenant_isolation` policy'sisiz — RLS himoyasisiz — qolardi. "
    "Qo'shish `0018` bilan BIR OYNADA bajariladi (`05-05` / T2)."
)


def test_occupancy_registries_are_self_consistent(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """5-faza reyestrlari o'zaro MOS — jadval tug'ilishidan OLDIN (W0-4/W0-5/W0-6).

    `test_snapshot_registries_are_self_consistent` ning AYNAN shakli, uchinchi
    marta qo'llangan. Uchta ro'yxat uch xil savolga javob beradi va ular
    AJRALIB KETISHI mumkin, chunki uchalasi qo'lda yuritiladi:

      * `OCCUPANCY_TENANT_TABLES`  -> RLS + policy tsikli (`0018`);
      * `OCCUPANCY_AUDITED_TABLES` -> audit triggeri (`AUDITED_TABLES` kichik to'plami);
      * `OCCUPANCY_DELETE_ORDER`   -> `market_delete_draft()` kaskadi (`0019`).

    ⚠ IMPORT TEST FUNKSIYASINING ICHIDA — 4-fazadagi bilan bir xil sabab:
      reyestr hali tug'ilmagan bosqichda modul darajasidagi import BUTUN
      FAYLNING yig'ilishini yiqitardi, ya'ni W0-5 ning ikki tomonlama qulfi
      (`test_audited_tables_have_trigger`) o'sha bosqichda umuman
      ishlamas va o'lchab bo'lmasdi.
    """
    from migrations.entities import (
        ALL_TENANT_TABLES,
        OCCUPANCY_AUDITED_TABLES,
        OCCUPANCY_DELETE_ORDER,
        OCCUPANCY_TENANT_TABLES,
    )

    assert len(OCCUPANCY_TENANT_TABLES) == 6, (
        f"`OCCUPANCY_TENANT_TABLES` da {len(OCCUPANCY_TENANT_TABLES)} jadval: "
        f"{list(OCCUPANCY_TENANT_TABLES)}. Kutilgani oltita (`05-PATTERNS.md` §S-1)."
    )
    assert len(set(OCCUPANCY_TENANT_TABLES)) == len(OCCUPANCY_TENANT_TABLES), (
        f"`OCCUPANCY_TENANT_TABLES` da dublikat bor: {list(OCCUPANCY_TENANT_TABLES)}"
    )

    # 🔴 D-06 — NOM TO'QNASHUVI MEXANIK QULFLANDI. `zones` 2-fazada bozor
    # hududlari uchun BAND va unga `stalls.zone_id NOT NULL` tayanadi. Reyestrga
    # `zones` yozilishi `0018` ni «jadval allaqachon mavjud» bilan yiqitardi —
    # yoki, bundan ham yomoni, mavjud jadvalga ikkinchi policy qo'yardi.
    assert "zones" not in OCCUPANCY_TENANT_TABLES, (
        "`zones` nomi 2-fazadan BAND (`models/market.py::Zone`, `stalls.zone_id "
        "NOT NULL` unga tayanadi). Kamera zonasi jadvali `camera_zones` deb "
        "nomlanadi (D-06)."
    )
    assert "camera_zones" in OCCUPANCY_TENANT_TABLES, (
        "`camera_zones` reyestrda yo'q — D-06 ning butun mazmuni shu nomda."
    )

    # ⚠ O'ZI QUROLLANADIGAN DARVOZA — shartsiz `<=` EMAS, va bu ATAYIN.
    # Sabab `test_snapshot_registries_are_self_consistent` da o'lchangan
    # (`UndefinedTable`, 2026-08-04): jadval TUG'ILMASDAN OLDIN uni
    # `ALL_TENANT_TABLES` ga qo'shish `test_autogenerate_is_empty` ni
    # yiqitadi, chunki `alembic_utils` komparatori policy'ni HAQIQATAN
    # yaratib ko'radi. Bugun — yashil (jadvallar yo'q); `0018` qo'ngan kuni
    # — `05-05` ro'yxatni kengaytirmaguncha QIZIL.
    existing = {
        row[0]
        for row in sync_app_conn.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r'"
        ).fetchall()
    }
    born = set(OCCUPANCY_TENANT_TABLES) & existing
    assert born <= set(ALL_TENANT_TABLES), (
        f"jadval BAZADA bor, lekin `ALL_TENANT_TABLES` da yo'q: "
        f"{sorted(born - set(ALL_TENANT_TABLES))}. " + OCCUPANCY_TENANT_REGISTRY_HINT
    )

    assert set(OCCUPANCY_DELETE_ORDER) == set(OCCUPANCY_TENANT_TABLES), (
        "kaskad tartibi tenant reyestriga mos emas.\n"
        f"  kaskadda yo'q: {sorted(set(OCCUPANCY_TENANT_TABLES) - set(OCCUPANCY_DELETE_ORDER))}\n"
        f"  ortiqcha:      {sorted(set(OCCUPANCY_DELETE_ORDER) - set(OCCUPANCY_TENANT_TABLES))}\n"
        + OCCUPANCY_CASCADE_HINT
    )
    assert len(OCCUPANCY_DELETE_ORDER) == len(set(OCCUPANCY_DELETE_ORDER)), (
        f"`OCCUPANCY_DELETE_ORDER` da dublikat bor: {list(OCCUPANCY_DELETE_ORDER)}"
    )

    # Tartib — BOLALARDAN OTA-ONAGA. Har juftlik `05-RESEARCH.md` §A.2/§B.5/
    # §C.8/§D.12 sxemalaridagi HAQIQIY FK ga mos keladi, ya'ni bu ro'yxat
    # ixtiyoriy tartib emas — u `0019` ning `DELETE` ketma-ketligi.
    order = list(OCCUPANCY_DELETE_ORDER)
    for child, parent in (
        ("stall_slot_occupancy", "occupancy_events"),
        ("zone_reviews", "review_assignments"),
        ("review_assignments", "occupancy_events"),
        ("review_assignments", "audit_rounds"),
        ("occupancy_events", "camera_zones"),
    ):
        assert order.index(child) < order.index(parent), (
            f"`{child}` `{parent}` dan KEYIN o'chirilyapti — kaskad o'z chet el "
            "kalitiga uriladi. Tartib bolalardan ota-onaga bo'lishi shart."
        )

    assert set(OCCUPANCY_AUDITED_TABLES) < set(OCCUPANCY_TENANT_TABLES), (
        "`OCCUPANCY_AUDITED_TABLES` tenant reyestrining QAT'IY kichik to'plami "
        f"bo'lishi shart. Topilgani: {list(OCCUPANCY_AUDITED_TABLES)}. To'rtta "
        "jadval (`occupancy_events`, `audit_rounds`, `review_assignments`, "
        "`stall_slot_occupancy`) auditdan ATAYIN chiqarilgan — sabab "
        "`migrations/entities/__init__.py::OCCUPANCY_AUDITED_TABLES` docstringida."
    )
    assert set(OCCUPANCY_AUDITED_TABLES) <= AUDITED_TABLES, (
        f"audit reyestriga tushmagan nom(lar): "
        f"{sorted(set(OCCUPANCY_AUDITED_TABLES) - AUDITED_TABLES)} — "
        "`OCCUPANCY_AUDITED_TABLES` va `AUDITED_TABLES` ajralib ketgan."
    )


ENTITIES_SOURCE = Path(__file__).resolve().parents[2] / "migrations" / "entities" / "__init__.py"

DERIVED_ORDER_PATTERN = re.compile(r"^\s*(\w+)_DELETE_ORDER[^=]*=\s*tuple\s*\(", re.MULTILINE)
"""`<DOMEN>_DELETE_ORDER = tuple(reversed(...))` shaklini topadigan naqsh.

⛔ NAQSH UMUMLASHTIRILDI (`06-04` / T3, §5.8 ning yopilishi). Ilgari u
`OCCUPANCY_DELETE_ORDER` NOMIGA QATTIQ YOZILGAN edi, ya'ni 6-fazaning
`BILLING_DELETE_ORDER` i uni UMUMAN QAMRAMASDI va §S-2 ning qoidasi
yangi domenda JIMGINA bo'shab qolardi.

⛔ IKKINCHI KONSTANTA QO'SHISH RAD ETILDI va sabab arifmetik: har yangi
domen darvozaga BITTA QATOR qo'shishni talab qilardi va uchinchi domen
paydo bo'lganda YANA tahrir kerak bo'lardi — ya'ni darvozaning qamrovi
qo'lda yuritiladigan ro'yxatga aylanardi (D-32: darvoza SANOQ emas,
MANBADAN HOSILA). Umumlashtirilgan naqsh esa `SNAPSHOT_DELETE_ORDER` ni
ham, kelajakdagi har qanday `*_DELETE_ORDER` ni ham AVTOMATIK qamraydi.

⚠ UMUMLASHTIRISH MAVJUD OCCUPANCY DA'VOSINI SUSAYTIRMAYDI va bu
TAXMIN EMAS, O'LCHANADI: `test_billing_delete_order_is_declared_not_
derived` naqshni POZITIV (hosila e'lon TOPILADI, shu jumladan
`OCCUPANCY_DELETE_ORDER` niki) va NEGATIV (literal e'lon TOPILMAYDI)
nazorat bilan sinaydi.

Faqat E'LON satri qidiriladi — docstring ichidagi tushuntirish matni
(«bu `reversed()` i EMAS») darvozani qizartirmasligi kerak, aks holda
yagona «tuzatish» yo'li SABABNI O'CHIRISH bo'lardi (3-fazada o'lchangan
naqsh: taqiqlangan ibora skanerlanadigan faylning izohida ham yozilmaydi).
"""


def test_occupancy_delete_order_is_declared_not_derived() -> None:
    """`OCCUPANCY_DELETE_ORDER` LITERAL e'lon qilinadi — hosila EMAS (§S-2).

    =====================================================================
    ⚠ BU TEST REJANING QABUL MEZONINI QAYTA SHAKLLANTIRADI VA SABAB O'LCHOV.

    `05-01-PLAN.md` mezoni «`OCCUPANCY_DELETE_ORDER !=
    tuple(reversed(OCCUPANCY_TENANT_TABLES))` — testda literal
    tasdiqlanadi» deb yozilgan. Rejaning O'ZI bergan ikki ro'yxat esa
    AYNAN bir-birining teskarisi:

        tenant:  camera_zones, occupancy_events, audit_rounds,
                 review_assignments, zone_reviews, stall_slot_occupancy
        delete:  stall_slot_occupancy, zone_reviews, review_assignments,
                 audit_rounds, occupancy_events, camera_zones

    Ya'ni `!=` da'vosi bu ma'lumot ustida YOLG'ON va uni «qondirish»ning
    yagona yo'li ro'yxatlardan birini ataylab NOTO'G'RI tartibda yozish
    bo'lardi — o'sha holda `0019` ning kaskadi o'z chet el kalitiga
    urilardi.

    4-fazada `!=` ROST edi, chunki `alert_events` FK zanjirida umuman
    turmasdi. Bu domenda zanjirdan chetda turgan jadval YO'Q, ya'ni
    ustma-ustlik TASODIF.

    ✅ MEZONNING NIYATI esa ustma-ustlikda emas: §S-2 «ALOHIDA RO'YXAT,
    hosila emas» deydi. Shuning uchun bu test TENGSIZLIKNI emas,
    MUSTAQILLIKNI o'lchaydi — qiymat `reversed()` dan HISOBLANMAGANINI.
    Bu kuchliroq da'vo: ustma-ustlik tasodifan yo'qolganda ham u kuchda
    qoladi, `!=` esa o'sha kundan boshlab hech nima demay qo'yardi.
    =====================================================================

    Darvoza MANBA MATNINI o'qiydi, import qilmaydi (§S-10): import qilingan
    qiymat `tuple(reversed(...))` bilan LITERAL tuple'ni bir-biridan
    ajrata olmaydi — ikkalasi ham bir xil obyekt beradi.

    ⚠ `06-04` / T3 DAN BERI NAQSH UMUMLASHTIRILGAN (`(\\w+)_DELETE_ORDER`),
    ya'ni bu test endi occupancy'ni ham, boshqa har qanday domen
    ro'yxatini ham qamraydi. Da'vo SUSAYMADI — u KENGAYDI; nazorati
    `test_billing_delete_order_is_declared_not_derived` da.
    """
    source = ENTITIES_SOURCE.read_text(encoding="utf-8")

    # QUYI CHEGARA: fayl yo'li noto'g'ri bo'lsa yoki konstanta qayta
    # nomlansa quyidagi "topilmadi" assert'i JIMGINA yashil qolardi.
    assert "OCCUPANCY_DELETE_ORDER" in source, (
        f"`OCCUPANCY_DELETE_ORDER` {ENTITIES_SOURCE} da topilmadi — darvoza "
        "noto'g'ri faylni o'qiyapti yoki konstanta qayta nomlangan."
    )

    derived = DERIVED_ORDER_PATTERN.search(source)
    assert derived is None, (
        "`*_DELETE_ORDER` HOSILA qiymat sifatida yozilgan: "
        f"{derived.group(0).strip() if derived else ''!r}\n"
        "RLS tartibi (ota-onadan bolalarga) va o'chirish tartibi (bolalardan "
        "ota-onaga) IKKI XIL savolga javob beradi va MUSTAQIL o'zgaradi. "
        "FK zanjiridan chetda turgan bitta jadval qo'shilgan kuni hosila "
        "qiymat JIMGINA noto'g'ri bo'lardi — 4-fazada `alert_events` aynan "
        "shunday edi (§S-2)."
    )


BILLING_CASCADE_HINT = (
    "Tushib qolgan jadval `0020` qo'ngandan keyin qoralama bozorni o'chirishni "
    "chet el kaliti buzilishi bilan yiqitardi (OP-1) va sabab faqat ish paytida, "
    "admin ekranida ko'rinardi. Kaskad `0021` da yoziladi (`06-04` / T3)."
)
"""Tuzatish yo'riqnomasi ALOHIDA konstantada — sabab `CASCADE_REGISTRY_HINT` da."""

BILLING_TENANT_REGISTRY_HINT = (
    "`ALL_ENTITIES` aynan `ALL_TENANT_TABLES` dan quriladi, ya'ni tushib qolgan "
    "jadval `tenant_isolation` policy'sisiz — RLS himoyasisiz — qolardi. "
    "Qo'shish `0020` bilan BIR OYNADA bajariladi (`06-04` / T2, OP-3)."
)


def test_billing_registries_are_self_consistent(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """6-faza reyestrlari o'zaro MOS (D-32).

    `test_occupancy_registries_are_self_consistent` ning AYNAN shakli,
    to'rtinchi marta qo'llangan. Uchta ro'yxat uch xil savolga javob beradi
    va ular AJRALIB KETISHI mumkin, chunki uchalasi qo'lda yuritiladi:

      * `BILLING_TENANT_TABLES`  -> RLS + policy tsikli (`0020`);
      * `BILLING_AUDITED_TABLES` -> audit triggeri (`AUDITED_TABLES` kichik to'plami);
      * `BILLING_DELETE_ORDER`   -> `market_delete_draft()` kaskadi (`0021`).

    ⚠ IMPORT TEST FUNKSIYASINING ICHIDA — 4- va 5-fazadagi bilan bir xil
      sabab: reyestr hali tug'ilmagan bosqichda modul darajasidagi import
      BUTUN FAYLNING yig'ilishini yiqitardi.
    """
    from migrations.entities import (
        ALL_TENANT_TABLES,
        BILLING_AUDITED_TABLES,
        BILLING_DELETE_ORDER,
        BILLING_TENANT_TABLES,
    )

    assert len(BILLING_TENANT_TABLES) == 6, (
        f"`BILLING_TENANT_TABLES` da {len(BILLING_TENANT_TABLES)} jadval: "
        f"{list(BILLING_TENANT_TABLES)}. Kutilgani oltita (`06-PATTERNS.md` §2 R-1)."
    )
    assert len(set(BILLING_TENANT_TABLES)) == len(BILLING_TENANT_TABLES), (
        f"`BILLING_TENANT_TABLES` da dublikat bor: {list(BILLING_TENANT_TABLES)}"
    )

    # 🔴 C-1 — NOM MEXANIK QULFLANDI. `charges` nomi `FINANCIAL_TABLES` da
    # 1-fazadan beri `daily_charges` deb yozilgan va
    # `test_financial_tables_have_guards` bazada AYNAN shu nomni izlaydi.
    # `charges` deb nomlash darvozani «jadval yo'q» holatida JIMGINA yashil
    # qoldirardi — uchala moliyaviy qo'riqchi ham tekshirilmasdi.
    assert "charges" not in BILLING_TENANT_TABLES, (
        "`charges` nomi TAQIQLANGAN: `sbozor_core.schema_contract."
        "FINANCIAL_TABLES` 1-fazadan beri `daily_charges` ni kutadi (C-1)."
    )
    assert "daily_charges" in BILLING_TENANT_TABLES, (
        "`daily_charges` reyestrda yo'q — C-1 ning butun mazmuni shu nomda."
    )

    # ⛔ C-4/D-24 — YETTINCHI JADVAL YARATILMAYDI. Taqsimlash HOSILA qoida
    # (`FIFO_OLDEST_SERVICE_DATE_FIRST`, 06-01) va u SAQLANMAYDI: saqlangan
    # taqsimlash D-07 (yozilgan hisob o'zgarmas) va BILL-03 (qoldiq
    # hisoblanadigan ko'rinish) ning IKKALASINI ham buzardi.
    assert "payment_allocations" not in BILLING_TENANT_TABLES, (
        "`payment_allocations` reyestrga qo'shilgan — D-24 ning mexanizmi "
        "HOSILA qoida, saqlanadigan jadval EMAS (C-4)."
    )

    # ⚠ O'ZI QUROLLANADIGAN DARVOZA — shartsiz `<=` EMAS (sabab
    # `test_occupancy_registries_are_self_consistent` da o'lchangan).
    existing = {
        row[0]
        for row in sync_app_conn.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r'"
        ).fetchall()
    }
    born = set(BILLING_TENANT_TABLES) & existing
    assert born <= set(ALL_TENANT_TABLES), (
        f"jadval BAZADA bor, lekin `ALL_TENANT_TABLES` da yo'q: "
        f"{sorted(born - set(ALL_TENANT_TABLES))}. " + BILLING_TENANT_REGISTRY_HINT
    )

    assert set(BILLING_DELETE_ORDER) == set(BILLING_TENANT_TABLES), (
        "kaskad tartibi tenant reyestriga mos emas.\n"
        f"  kaskadda yo'q: {sorted(set(BILLING_TENANT_TABLES) - set(BILLING_DELETE_ORDER))}\n"
        f"  ortiqcha:      {sorted(set(BILLING_DELETE_ORDER) - set(BILLING_TENANT_TABLES))}\n"
        + BILLING_CASCADE_HINT
    )
    assert len(BILLING_DELETE_ORDER) == len(set(BILLING_DELETE_ORDER)), (
        f"`BILLING_DELETE_ORDER` da dublikat bor: {list(BILLING_DELETE_ORDER)}"
    )

    # Tartib — BOLALARDAN OTA-ONAGA. Har juftlik `models/billing.py` dagi
    # HAQIQIY kompozit FK ga mos keladi, ya'ni bu ro'yxat ixtiyoriy tartib
    # emas — u `0021` ning `DELETE` ketma-ketligi. ⚠ IKKI MUSTAQIL zanjir.
    order = list(BILLING_DELETE_ORDER)
    for child, parent in (
        ("charge_evidence", "daily_charges"),
        ("charge_adjustments", "daily_charges"),
        ("payments", "cashier_shifts"),
    ):
        assert order.index(child) < order.index(parent), (
            f"`{child}` `{parent}` dan KEYIN o'chirilyapti — kaskad o'z chet el "
            "kalitiga uriladi. Tartib bolalardan ota-onaga bo'lishi shart."
        )

    assert set(BILLING_AUDITED_TABLES) < set(BILLING_TENANT_TABLES), (
        "`BILLING_AUDITED_TABLES` tenant reyestrining QAT'IY kichik to'plami "
        f"bo'lishi shart. Topilgani: {list(BILLING_AUDITED_TABLES)}. To'rtta "
        "jadval (`daily_charges`, `payments`, `charge_evidence`, "
        "`billing_anomalies`) auditdan ATAYIN chiqarilgan — sabab "
        "`sbozor_core.schema_contract.AUDITED_TABLES` docstringida."
    )
    assert set(BILLING_AUDITED_TABLES) <= AUDITED_TABLES, (
        f"audit reyestriga tushmagan nom(lar): "
        f"{sorted(set(BILLING_AUDITED_TABLES) - AUDITED_TABLES)} — "
        "`BILLING_AUDITED_TABLES` va `AUDITED_TABLES` ajralib ketgan."
    )


def test_billing_delete_order_is_declared_not_derived() -> None:
    """`BILLING_DELETE_ORDER` LITERAL e'lon qilinadi — hosila EMAS (§5.8/D-32).

    =====================================================================
    ⚠ BU TEST IKKI DA'VONI BIRDAN O'LCHAYDI VA IKKALASI HAM KERAK.

    **(1) YANGI RO'YXAT QAMRALDI.** `DERIVED_ORDER_PATTERN` `06-04` gacha
    `OCCUPANCY_DELETE_ORDER` NOMIGA QATTIQ YOZILGAN edi (`05-01` / §S-10),
    ya'ni `BILLING_DELETE_ORDER = tuple(reversed(BILLING_TENANT_TABLES))`
    deb yozish darvozadan JIMGINA o'tib ketardi. Bu 5-fazadagidan
    ham QIMMAT xato bo'lardi: u yerda ikki ro'yxat TASODIFAN ustma-ust
    tushardi, bu domenda esa ular USTMA-UST TUSHMAYDI —
    `reversed(BILLING_TENANT_TABLES)` `payments` ni `charge_evidence` dan
    OLDIN qo'yardi va kaskad o'z chet el kalitiga urilardi.

    **(2) UMUMLASHTIRISH ESKI DA'VONI SUSAYTIRMADI.** Naqshni kengaytirish
    uni «hech nimani topmaydigan» qilib qo'yishi mumkin edi va o'shanda
    IKKALA ro'yxat ham qo'riqsiz qolardi — test esa BARIBIR yashil
    bo'lardi («hosila e'lon topilmadi» har doim rost). Shuning uchun naqsh
    POZITIV va NEGATIV nazorat bilan sinaladi: u sun'iy HOSILA e'lonni
    (o'sha jumladan eski `OCCUPANCY_DELETE_ORDER` shaklini) TOPISHI va
    sun'iy LITERAL e'lonni TOPMASLIGI shart.

    Darvoza MANBA MATNINI o'qiydi, import qilmaydi (§S-10): import qilingan
    qiymat `tuple(reversed(...))` bilan LITERAL tuple'ni bir-biridan
    ajrata olmaydi — ikkalasi ham bir xil obyekt beradi.
    =====================================================================
    """
    source = ENTITIES_SOURCE.read_text(encoding="utf-8")

    # QUYI CHEGARA: fayl yo'li noto'g'ri bo'lsa yoki konstanta qayta
    # nomlansa quyidagi "topilmadi" assert'i JIMGINA yashil qolardi.
    assert "BILLING_DELETE_ORDER" in source, (
        f"`BILLING_DELETE_ORDER` {ENTITIES_SOURCE} da topilmadi — darvoza "
        "noto'g'ri faylni o'qiyapti yoki konstanta qayta nomlangan."
    )

    derived = [match.group(1) for match in DERIVED_ORDER_PATTERN.finditer(source)]
    assert "BILLING" not in derived, (
        "`BILLING_DELETE_ORDER` HOSILA qiymat sifatida yozilgan.\n"
        "RLS tartibi (ota-onadan bolalarga) va o'chirish tartibi (bolalardan "
        "ota-onaga) IKKI XIL savolga javob beradi va MUSTAQIL o'zgaradi. "
        "Bu domenda ular USTMA-UST HAM TUSHMAYDI: hosila qiymat `payments` "
        "ni `charge_evidence` dan oldin qo'yardi va kaskad o'z chet el "
        "kalitiga urilardi (§5.8)."
    )
    assert not derived, (
        f"hosila `*_DELETE_ORDER` e'lon(lar)i topildi: {sorted(derived)} — "
        "har bir domen ro'yxati LITERAL yozilishi shart (§S-2)."
    )

    # ⚠⚠ NAQSHNING O'ZI SINALADI — usiz yuqoridagi assert'lar «hech nima
    #   topilmadi» degan BO'SH rost bilan yashil qolardi (§S-6: darvoza
    #   quyi chegarasi). Pozitiv nazoratda ESKI (occupancy) shakli ham bor:
    #   umumlashtirish 5-fazaning da'vosini yo'qotmaganini aynan shu satr
    #   isbotlaydi.
    positive = (
        "OCCUPANCY_DELETE_ORDER = tuple(reversed(OCCUPANCY_TENANT_TABLES))\n"
        "BILLING_DELETE_ORDER: tuple[str, ...] = tuple(reversed(BILLING_TENANT_TABLES))\n"
        "    SNAPSHOT_DELETE_ORDER = tuple (reversed(SNAPSHOT_TENANT_TABLES))\n"
    )
    found = {match.group(1) for match in DERIVED_ORDER_PATTERN.finditer(positive)}
    assert found == {"OCCUPANCY", "BILLING", "SNAPSHOT"}, (
        f"`DERIVED_ORDER_PATTERN` hosila e'lonlarni topmayapti: {sorted(found)}. "
        "Naqsh umumlashtirilgandan keyin HECH NIMANI topmaydigan bo'lib "
        "qolgan bo'lishi mumkin — o'shanda yuqoridagi assert'lar BO'SH rost "
        "bilan yashil qolardi."
    )

    negative = (
        'OCCUPANCY_DELETE_ORDER: tuple[str, ...] = (\n    "zone_reviews",\n)\n'
        'BILLING_DELETE_ORDER: tuple[str, ...] = (\n    "charge_evidence",\n)\n'
        "# `BILLING_DELETE_ORDER = tuple(reversed(...))` DEB YOZISH TAQIQLANGAN\n"
    )
    assert not DERIVED_ORDER_PATTERN.search(negative), (
        "`DERIVED_ORDER_PATTERN` LITERAL e'lonni (yoki izohdagi tushuntirish "
        "matnini) hosila deb ko'rsatyapti — darvoza YOLG'ON-QIZIL beradi va "
        "yagona «tuzatish» yo'li SABABNI O'CHIRISH bo'lardi."
    )


def test_markets_all_use_tashkent_timezone(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """BARCHA bozorlar `Asia/Tashkent` da — biznes-kun JIMGINA siljimasin (W0-7).

    =====================================================================
    ASSIMETRIYA — VA U ATAYIN:

      * `capture_runs.scheduled_at` bozorning O'Z mintaqasidan hisoblanadi
        (`markets.timezone`), ya'ni «06:00» har bozorda o'zining mahalliy
        soati bo'ladi;
      * `business_date` esa `GENERATED` ifodasida **LITERAL**
        `'Asia/Tashkent'` dan hisoblanadi, chunki `GENERATED ... STORED`
        ustun `IMMUTABLE` ifoda talab qiladi va boshqa jadvaldan o'qish
        (`markets.timezone`) bu shartni buzadi. Cheklov
        `models/identity.py` da hujjatlashtirilgan.

    Bugun ikkalasi bir xil natija beradi, chunki hamma bozor bitta
    mintaqada. Ikkinchi mintaqadagi bozor qo'shilgan kuni ular AJRALADI
    va nosozlik shakli o'ta yomon bo'lardi: kadr to'g'ri vaqtda olinardi,
    lekin BOSHQA KUNGA yozilardi — ya'ni 6-fazada pul chegarasi bir kunga
    surilardi va buni hech kim ko'rmasdi.

    Shuning uchun bu invariant CI'da turadi: ikkinchi mintaqa qo'shilgan
    kuni test QIZARADI va qaror (ikkalasini ham mintaqadan hisoblash yoki
    `business_date` ni ilova qatlamiga ko'chirish) ATAYIN qabul qilinadi.
    =====================================================================

    ⚠ QUYI CHEGARA ATAYIN QO'SHILMAGAN. `markets` bo'sh bo'lsa ham assert
      ma'noli (0 = 0): invariant «noto'g'ri qiymat YO'Q» shaklida, «kamida
      N qator BOR» shaklida emas. Quyi chegara qo'shish testni seed
      tartibiga bog'lab, flaky qilardi.
    """
    row = sync_app_conn.execute(
        "SELECT count(*), coalesce(string_agg(DISTINCT timezone, ', '), '') "
        "FROM markets WHERE timezone <> 'Asia/Tashkent'"
    ).fetchone()
    assert row is not None

    assert row[0] == 0, (
        f"{row[0]} ta bozor boshqa mintaqada ({row[1]}). `business_date` "
        "`GENERATED` ifodasida LITERAL `'Asia/Tashkent'` dan hisoblanadi, "
        "`scheduled_at` esa `markets.timezone` dan — ikkinchi mintaqa "
        "qo'shilishi biznes-kun chegarasini JIMGINA siljitadi. Qarorni "
        "ATAYIN qabul qiling: yoki `business_date` ni ilova qatlamiga "
        "ko'chiring, yoki bu invariantni sabab bilan yumshating (W0-7)."
    )


def test_financial_tables_have_guards(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """MAVJUD moliyaviy jadvallarning har birida uchta konstrayt bor (mezon #5).

    1-fazada `FINANCIAL_TABLES` dagi jadvallarning HECH BIRI hali yo'q
    (ular 2- va 6-fazalarda tug'iladi), ya'ni bu test HOZIRCHA vakuum —
    lekin u vakuum bo'lib QOLMAYDI: jadval paydo bo'lgan kuni darvoza
    avtomatik yopiladi va `financial_guards()` chaqirilmagan bo'lsa CI
    qizaradi. Reyestrni oldindan yozishning butun ma'nosi shu.

    Uch talab (har biri boshqa nosozlikni yopadi):
      * `business_date` STORED generated ustuni  -> biznes-kun chegarasi;
      * `CHECK (<amount> > 0)`                    -> pul musbat va `bigint`;
      * `market_id` bilan boshlanadigan UNIQUE    -> kun yopilishi idempotent.

    ⛔ IKKINCHI TALABNING YAGONA ISTISNOSI — `NON_POSITIVE_MONEY_TABLES`
       (0027). U yerdagi jadvalda `>= 0` qabul qilinadi, chunki NOL
       «bu xizmat bu bozorda umuman yo'q» degan HALOL javob. Istisno
       REYESTRDAN o'qiladi, shu yerda nom bilan yozilmaydi: ikkinchi
       ro'yxat bir kun birinchisidan ajralib ketardi.

    ⚠ Qolgan IKKALA talab istisno jadvalda ham O'ZGARISHSIZ qoladi —
      «pul musbat» yumshatildi, «biznes-kun» va «idempotentlik» EMAS.
    """
    existing = set(_base_tables(sync_app_conn)) & FINANCIAL_TABLES

    problems: list[str] = []
    for table in sorted(existing):
        generated = sync_app_conn.execute(
            "SELECT a.attgenerated FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = %s AND a.attname = 'business_date'",
            (table,),
        ).fetchone()
        if generated is None or generated[0] != "s":
            problems.append(f"{table}: `business_date` STORED generated ustuni yo'q")

        checks = sync_app_conn.execute(
            "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
            "WHERE c.contype = 'c' AND c.conrelid = %s::regclass",
            (table,),
        ).fetchall()
        if table in NON_POSITIVE_MONEY_TABLES:
            # `>=` ni ham qabul qiladigan shakl. ⛔ `>` ni umuman
            # tekshirmaslik EMAS: ustun baribir CHEKLANGAN bo'lishi shart,
            # faqat pastki chegara nol.
            money_check = r"amount_soum\s*>=?\s*0"
            expected = "`CHECK (amount_soum >= 0)`"
        else:
            money_check = r"amount_soum\s*>\s*0"
            expected = "`CHECK (amount_soum > 0)`"
        if not any(re.search(money_check, row[0]) for row in checks):
            problems.append(f"{table}: {expected} yo'q")

        uniques = sync_app_conn.execute(
            "SELECT (SELECT a.attname FROM pg_attribute a "
            "        WHERE a.attrelid = c.conrelid AND a.attnum = c.conkey[1]) "
            "FROM pg_constraint c WHERE c.contype = 'u' AND c.conrelid = %s::regclass",
            (table,),
        ).fetchall()
        if not any(row[0] == "market_id" for row in uniques):
            problems.append(f"{table}: `market_id` bilan boshlanadigan UNIQUE konstrayt yo'q")

    assert not problems, (
        "Moliyaviy jadval `financial_guards()` siz yaratilgan:\n  "
        + "\n  ".join(problems)
        + "\n(`migrations/helpers.py::financial_guards()` ni chaqiring)"
    )


def test_users_table_is_closed_to_app_role(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`users` da `sbozor_app` uchun HECH QANDAY huquq yo'q (T-01-25)."""
    row = sync_app_conn.execute(
        "SELECT bool_or(has_table_privilege('sbozor_app', 'users', priv)) "
        "FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','REFERENCES','TRIGGER']) AS priv"
    ).fetchone()
    assert row is not None
    assert row[0] is False, (
        "sbozor_app `users` jadvaliga huquqqa ega — global identifikatsiya "
        "ma'lumoti ORM orqali o'qilishi mumkin bo'lib qoladi"
    )
