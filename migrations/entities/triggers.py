"""Audit trigger funksiyalari — `PGFunction` ta'riflarining YAGONA joyi (D-10).

=============================================================================
NEGA ORM HOOK EMAS, NEGA DB-TRIGGER (RESEARCH Pattern 4 / Pitfall 5):

`before_flush` kabi ORM hook'i ORM abstraksiyasining ICHIDA yashaydi. U
quyidagilarni UMUMAN ko'rmaydi:

  * `session.execute(text("UPDATE payments SET ..."))` — xom SQL;
  * bulk `update()` / `delete()` konstruksiyalari;
  * migratsiyalar va `psql` dan qo'lda kiritilgan o'zgarishlar.

Ya'ni hook aynan texnik savodli insider ishlatadigan yo'llarni ochiq
qoldiradi — bu esa mahsulotning butun ma'nosiga (kim qancha patta yig'di)
qarshi. Shuning uchun moliyaviy va huquq-o'zgartiruvchi jadvallarda audit
DB-trigger bilan yoziladi: u yozuv yo'lidan qat'i nazar ishlaydi.

Empirik (postgres:18.4): xom `UPDATE ... SET ...` audit qatorini YOZDI;
bir xil qiymat bilan qilingan no-op UPDATE esa YOZMADI (shovqin yo'q).
=============================================================================

NEGA `SECURITY DEFINER` EMAS — bu ATAYIN qilingan tanlov:

`audit_log` da `FOR INSERT WITH CHECK (true)` policy'si bor va `sbozor_app`
ga `INSERT` huquqi berilgan, ya'ni trigger CHAQIRUVCHI huquqi bilan ham
bemalol yoza oladi. Funksiyani ega huquqiga ko'tarish hech qanday qo'shimcha
imkoniyat bermaydi, lekin privilege-escalation yuzasini ochadi (`SECURITY
DEFINER` funksiya har doim `search_path` va argument tekshiruvi bo'yicha
qo'shimcha xavf). `tests/tenancy/test_meta.py` bu qarorni `pg_proc.prosecdef`
bo'yicha qulflaydi.

`SET search_path = pg_catalog, public` esa SHUNDA HAM majburiy: trigger
DML qilayotgan sessiyaning `search_path` i bilan ishlaydi, ya'ni chaqiruvchi
o'z sxemasida soxta `audit_log` yaratib yozuvni o'sha yerga burib yuborishi
mumkin bo'lardi.
"""

from __future__ import annotations

from alembic_utils.pg_function import PGFunction

__all__ = [
    "ALL_TRIGGER_FUNCTIONS",
    "AUDIT_IMMUTABLE",
    "AUDIT_TRIGGER_FUNCTIONS",
    "BILLING_TRIGGER_FUNCTIONS",
    "CASE_EVENT_IMMUTABLE",
    "CATEGORY_PERIOD_PAST_IMMUTABLE",
    "CHARGE_IMMUTABLE",
    "FN_AUDIT_ROW",
    "MARKETS_DELETE_GUARD",
    "MARKET_DOMAIN_TRIGGER_FUNCTIONS",
    "NOTIFICATION_TRIGGER_FUNCTIONS",
    "NVR_DOMAIN_TRIGGER_FUNCTIONS",
    "OCCUPANCY_EVENT_IMMUTABLE",
    "OCCUPANCY_TRIGGER_FUNCTIONS",
    "PAYMENT_IMMUTABLE",
    "SHIFT_DECLARATION_IMMUTABLE",
    "STALL_CODE_CLAIM",
    "TARIFF_PAST_IMMUTABLE",
    "ZONE_REVIEW_IMMUTABLE",
]

FN_AUDIT_ROW = PGFunction(
    schema="public",
    signature="fn_audit_row()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_old  jsonb := CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END;
  v_new  jsonb := CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END;
  v_keys text[];
BEGIN
  IF TG_OP = 'UPDATE' THEN
    SELECT array_agg(n.k ORDER BY n.k) INTO v_keys
    FROM jsonb_each(v_new) AS n(k, v)
    WHERE n.v IS DISTINCT FROM (v_old -> n.k);

    -- Hech narsa o'zgarmagan UPDATE audit shovqini yaratmaydi: jurnal
    -- o'qiladigan bo'lib qolishi kerak, aks holda undan hech kim
    -- foydalanmaydi va u faqat disk yeydi.
    IF v_keys IS NULL THEN
      RETURN NULL;
    END IF;
  END IF;

  INSERT INTO public.audit_log (
      market_id, actor_user_id, actor_kind, action, table_name,
      row_id, old_value, new_value, changed_keys, request_id, source
  )
  VALUES (
      COALESCE((v_new ->> 'market_id')::uuid, (v_old ->> 'market_id')::uuid),
      NULLIF(current_setting('app.actor_id', true), '')::uuid,
      COALESCE(NULLIF(current_setting('app.actor_kind', true), ''), 'user'),
      lower(TG_OP),
      TG_TABLE_NAME,
      COALESCE((v_new ->> 'id')::uuid, (v_old ->> 'id')::uuid),
      v_old,
      v_new,
      v_keys,
      NULLIF(current_setting('app.request_id', true), ''),
      'db_trigger'
  );

  RETURN NULL;
END $$
""",
)
"""`AFTER INSERT OR UPDATE OR DELETE ... FOR EACH ROW` uchun universal audit yozuvchisi.

Qiymatlar qayerdan keladi:

| Ustun           | Manba                                                     |
| --------------- | --------------------------------------------------------- |
| `market_id`     | `NEW.market_id`, yo'q bo'lsa `OLD.market_id` (DELETE)      |
| `actor_user_id` | `app.actor_id` GUC — `set_tenant_context()` o'rnatadi      |
| `actor_kind`    | `app.actor_kind` GUC, standart `user` (fon job -> `system`)|
| `action`        | `lower(TG_OP)` — `sbozor_core.enums.AuditAction` bilan mos |
| `changed_keys`  | `to_jsonb` diff — faqat HAQIQATAN o'zgargan ustunlar       |
| `request_id`    | `app.request_id` GUC — log satrlari bilan bog'lash uchun   |
| `source`        | `'db_trigger'` (`AuditSource.DB_TRIGGER`)                  |

GUC'lar `NULLIF(..., '')` orqali o'qiladi: `set_config(..., true)` tranzaksiya
tugagach qiymatni `NULL` ga emas, BO'SH SATRGA qaytaradi va `''::uuid`
`invalid input syntax` bilan yiqilardi (Pitfall 1 — RLS predikatidagi bilan
aynan bir xil sinf xato). Kontekst umuman o'rnatilmagan bo'lsa audit qatori
BARIBIR yoziladi, faqat aktori `NULL` bo'ladi — "kim" noma'lum bo'lgani
yozuvni yo'qotish uchun sabab emas.

CHEKLOV: `row_id` `uuid` ga keltiriladi, ya'ni bu triggerni birlamchi kaliti
`uuid` bo'lmagan jadvalga ulash mumkin emas (`audit_log` ning o'ziga ham —
u append-only va o'z-o'zini audit qilmaydi).
"""

AUDIT_IMMUTABLE = PGFunction(
    schema="public",
    signature="audit_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only (attempted %)', TG_OP;
END $$
""",
)
"""`audit_log` ustidagi 3- va 4-qatlam qo'riqchisi.

Ikkala triggerda ham (`BEFORE UPDATE OR DELETE FOR EACH ROW` va
`BEFORE TRUNCATE FOR EACH STATEMENT`) ishlatiladi. `TG_OP` xabarga
qo'shiladi, chunki uch xil urinish (UPDATE / DELETE / TRUNCATE) uch xil
tahdid modelidan keladi va log'da ular ajralib turishi kerak.
"""

# ===========================================================================
# 0007/0008 — DOMEN QOIDALARI (2-faza, D-02 / D-04 / D-07)
# ===========================================================================
#
# Uchala trigger ham bitta falsafaga bo'ysunadi: qoida ILOVADA emas, DB'da.
# Ilova qatlami baribir tushunarli xabar (403 / 409) qaytaradi, lekin
# KAFOLAT shu yerda — chunki `psql` dan yozilgan bitta `UPDATE` ham,
# migratsiya ham, kelajakdagi import skripti ham shu yo'ldan o'tadi.

STALL_CODE_CLAIM = PGFunction(
    schema="public",
    signature="stall_code_claim()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  INSERT INTO public.stall_code_registry (market_id, code, stall_id)
  VALUES (NEW.market_id, NEW.code, NEW.id)
  ON CONFLICT (market_id, code) DO NOTHING;

  IF NOT EXISTS (
    SELECT 1
    FROM public.stall_code_registry AS r
    WHERE r.market_id = NEW.market_id
      AND r.code = NEW.code
      AND r.stall_id = NEW.id
  ) THEN
    RAISE EXCEPTION 'stall code % is already retired in this market (D-02)', NEW.code
      USING ERRCODE = '23505';
  END IF;

  RETURN NULL;
END $$
""",
)
"""`AFTER INSERT OR UPDATE OF code ON stalls` — raqam QAYTA ISHLATILMAYDI (D-02).

`UNIQUE(market_id, code)` yetarli emas: rasta kodi tahrirlangach eski kod
BO'SHAB QOLADI va yangi rastaga berilishi mumkin bo'lardi. Natijada
hisobotdagi "12-rasta" yillar davomida ikki xil jismoniy joyni anglatardi
va nizoda dalil sifatida ishlamasdi.

MEXANIKA: kod reyestrga BIR MARTA yoziladi (`ON CONFLICT DO NOTHING`), so'ng
qator AYNAN shu rastaga tegishli ekani tekshiriladi. Boshqa rastaga
biriktirilgan kod uchun tekshiruv yiqiladi. Eski rastaning O'Z kodini
qaytarib olishi (tuzatishni bekor qilish) esa ruxsat — reyestrda `stall_id`
allaqachon o'sha rasta.

`ERRCODE = '23505'` (unique_violation) ATAYIN: chaqiruvchi uni oddiy
"kod band" holati bilan BIR XIL yo'lda 409 ga aylantiradi va ikkita alohida
xato kodini ushlashi shart emas.

⚠ `AFTER`, `BEFORE` EMAS — O'LCHANGAN ZARURIYAT:
RESEARCH Pattern 8 `BEFORE INSERT` deb yozgan, lekin u
`fk_stall_code_registry_market_id_stall_id_stalls` FK'si bilan BIR VAQTDA
ISHLAY OLMAYDI. `BEFORE INSERT` paytida `stalls` qatori HALI YOZILMAGAN,
ya'ni reyestrga `stall_id = NEW.id` bilan yozish darhol FK buzilishini
beradi (o'lchangan: `Key (market_id, stall_id)=(...) is not present in table
"stalls"`). `AFTER` da qator allaqachon mavjud va FK bajariladi.

XATO KAFOLATI ZAIFLASHMAYDI: `AFTER` trigger'idagi `RAISE` ham butun
operatsiyani bekor qiladi — farq faqat qachon tekshirilishida.
`RETURN NULL` — `AFTER ROW` trigger'ining qaytish qiymati e'tiborga
olinmaydi (`fn_audit_row()` bilan bir xil).

IMPORT UCHUN OQIBAT (02-12 ga kirish sharti): `AFTER` bo'lgani uchun
`INSERT ... ON CONFLICT (market_id, code) DO NOTHING` da konflikt YUZAGA
KELGAN qator uchun trigger UMUMAN ishga tushmaydi. Ya'ni D-15 rejalashtirgan
xulq to'g'ridan-to'g'ri ishlaydi: mavjud kodli qatorlar jimgina o'tkazib
yuboriladi va javobda `skipped` sifatida sanaladi (RESEARCH Code Example 3).
Ilova qatlamidagi oldindan filtrlash foydali qoladi (foydalanuvchiga
`skipped` sonini ko'rsatish uchun), lekin u endi TO'G'RILIK sharti emas.

`SECURITY DEFINER` YO'Q: `stall_code_registry` tenant policy'si ostida va
`sbozor_app` ga `INSERT` grant'i bor, ya'ni trigger chaqiruvchi huquqi
bilan bemalol yozadi. `NEW.market_id` GUC bilan mos kelmasa `WITH CHECK`
uni to'xtatadi — bu qo'shimcha qatlam, kamchilik emas.
"""

TARIFF_PAST_IMMUTABLE = PGFunction(
    schema="public",
    signature="tariff_past_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF OLD.valid_from <= (now() AT TIME ZONE 'Asia/Tashkent')::date
     AND NOT EXISTS (
       SELECT 1 FROM public.markets AS m
       WHERE m.id = OLD.market_id AND m.is_active = false
     ) THEN
    RAISE EXCEPTION 'tariff row valid from % is locked (D-07)', OLD.valid_from
      USING ERRCODE = '23514';
  END IF;

  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$
""",
)
"""`BEFORE UPDATE OR DELETE ON tariffs` — o'tmishdagi narx QULFLANADI (D-07).

Bu tampering qo'riqchisi (T-02-23): retroaktiv narx o'zgartirish o'tmishdagi
qarzni yashirishning eng arzon yo'li bo'lardi va u aynan mahsulot fosh
qiladigan nosozlik turi. Ilova qatlami 403 ni ustiga qo'yadi, lekin kafolat
shu yerda — xom SQL yo'li ham qamraladi (1-faza D-10 falsafasi).

`(now() AT TIME ZONE 'Asia/Tashkent')::date` — biznes-kun chegarasi
`BUSINESS_DATE_EXPR` bilan bir xil mintaqada. Naive `current_date` UTC
bo'lardi va mahalliy 00:00–04:59 oralig'ida bir kun farq qilardi.

`RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END` — `BEFORE DELETE`
triggeri `NEW` ni umuman ko'rmaydi (u `NULL`), `NULL` qaytarish esa amalni
JIMGINA bekor qilardi.

QORALAMA BOZOR ISTISNOSI (`m.is_active = false`) — o'lchangan zaruriyat,
qulaylik emas:

`market_delete_draft()` tashlab ketilgan qoralamani o'chirishi kerak va u
`tariffs` dan ham `DELETE` qiladi. Qoralamaning BIRINCHI tarifi esa
`valid_from = market_profile.operating_since` bilan yaratiladi (A3), ya'ni
odatda BUGUN yoki O'TGAN sana. Istisnosiz bu trigger har bunday qoralamani
o'chirishni `23514` bilan bloklardi — ya'ni rejaning ikki qismi
bir-birini inkor qilardi va tashlab ketilgan qoralamalar bazada abadiy
to'planardi.

NEGA BU XAVFSIZLIK ZAIFLASHUVI EMAS: `is_active` `false` dan `true` ga
FAQAT `market_activate()` orqali o'tadi va TESKARI yo'l YO'Q —
`market_deactivate()` funksiyasi ataylab yaratilmagan. Ya'ni bir marta
jonli bo'lgan bozor hech qachon qoralamaga qayta olmaydi va istisno unga
HECH QACHON qo'llanmaydi. Qoralamada esa hisob-kitob umuman ishlamagan
(6-faza `WHERE m.is_active` bilan filtrlaydi), ya'ni himoya qilinadigan
o'tmish YO'Q.

`markets` o'qish `SECURITY DEFINER` siz, ya'ni RLS ostida bajariladi:
tenant kontekstsiz sessiyada 0 qator qaytadi, `NOT EXISTS` rost bo'ladi va
qator QULFLANGAN deb hisoblanadi — FAIL-CLOSED.
"""

CATEGORY_PERIOD_PAST_IMMUTABLE = PGFunction(
    schema="public",
    signature="category_period_past_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF OLD.valid_from <= (now() AT TIME ZONE 'Asia/Tashkent')::date
     AND NOT EXISTS (
       SELECT 1 FROM public.markets AS m
       WHERE m.id = OLD.market_id AND m.is_active = false
     ) THEN
    RAISE EXCEPTION 'stall category period valid from % is locked (D-04)', OLD.valid_from
      USING ERRCODE = '23514';
  END IF;

  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$
""",
)
"""`BEFORE UPDATE OR DELETE ON stall_category_periods` — `tariff_past_immutable()` ning JUFTI.

Tana ataylab AYNAN bir xil va bu takror emas, ZARURAT (T-02-24): toifa
tarif orqali summani TO'G'RIDAN-TO'G'RI belgilaydi. Faqat tarifni qulflab
toifa davrini ochiq qoldirish qo'riqchini butunlay bekor qilardi —
o'tmishdagi rastani "arzon" toifaga surib qo'yish narxni o'zgartirish bilan
bir xil natija berardi (D-04: "o'tmishdagi hisob buzilmaydi").

Ikkita alohida funksiya, bitta umumiy funksiya EMAS: xato xabari qaysi
qoida buzilganini aytishi kerak, `TG_TABLE_NAME` bo'yicha shoxlanadigan
umumiy funksiya esa ikkala jadvalni bir-biriga bog'lab qo'yardi.

Qoralama bozor istisnosi va uning nega xavfsiz ekani —
`TARIFF_PAST_IMMUTABLE` docstringida.
"""

# ===========================================================================
# 0013 — FAOL BOZORNI O'CHIRISH TAQIG'I (3-faza, WR-02 / D-17, T-03-17)
# ===========================================================================

MARKETS_DELETE_GUARD = PGFunction(
    schema="public",
    signature="markets_delete_guard()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF OLD.is_active IS DISTINCT FROM false THEN
    RAISE EXCEPTION 'market % is active and cannot be deleted (WR-02)', OLD.id
      USING ERRCODE = '23514';
  END IF;

  RETURN OLD;
END $$
""",
)
"""`BEFORE DELETE ON markets` — FAOL bozor DB darajasida o'chirilmaydi.

=============================================================================
NEGA `market_delete_draft()` DAGI `IF` YETARLI EMAS EDI.

O'sha shart FAQAT o'z yo'lini qo'riqlaydi. `psql` dan yuborilgan bitta
`DELETE FROM markets WHERE id = ...` uni BUTUNLAY chetlab o'tardi — ya'ni
"faol bozorni o'chirib bo'lmaydi" kafolati ilova qatlamining odob-axloqiga
tayanardi, SXEMAGA emas. Xato yozilgan kelajakdagi `SECURITY DEFINER`
funksiya ham xuddi shu teshikdan o'tardi (T-03-17).

Zarari qaytarilmas: bozor bilan birga `market_delete_draft()` kaskadidagi
o'n oltita jadvalning qatorlari ham FK bo'yicha... aslida YO'Q — kaskad
qo'lda yozilgan, ya'ni xom `DELETE` FK buzilishi bilan yiqilardi. Lekin
kaskad TO'LIQ bo'lgan kunda (bugun) u muvaffaqiyatli bajarilardi va
`audit_log` dagi izlar YETIM qolardi: jurnal saqlanadi, lekin u ishora
qilayotgan bozor endi mavjud emas.
=============================================================================

⚠ BU TRIGGER `market_delete_draft()` NI BLOKLAMAYDI.
Funksiya `is_active IS DISTINCT FROM false` bo'lganda `false` qaytaradi va
BIRORTA qatorga tegmaydi, ya'ni uning `DELETE FROM markets` iga faqat
QORALAMA bozor yetib keladi va triggerning sharti hech qachon otilmaydi.
Buni ikki tomondan o'lchash SHART (`tests/integration/
test_market_delete_guard.py`): qoralama o'chadi VA faol o'chmaydi. Faqat
ikkinchisini tekshirish "cheklov ishlayapti" ni emas, "hech narsa
o'chmayapti" ni isbotlagan bo'lardi.

`ERRCODE = '23514'` (check_violation) — `TARIFF_PAST_IMMUTABLE` va
`CATEGORY_PERIOD_PAST_IMMUTABLE` bilan AYNAN bir xil kod va bu ataylab:
uchalasi ham "domen qoidasi buzildi" sinfiga tegishli va chaqiruvchi
ularni bitta yo'lda 409 ga aylantiradi. Yangi konvensiya KIRITILMAYDI.

`SECURITY DEFINER` YO'Q: trigger birorta jadvalga murojaat qilmaydi, u
faqat `OLD.is_active` ni o'qiydi. `SECURITY DEFINER` bu yerda hech qanday
huquq bermasdi va uni `tests/tenancy/test_meta.py::
EXPECTED_DEFINER_FUNCTIONS` ro'yxatiga qo'shishni talab qilardi — ya'ni
faqat yuza kengaytirardi.

`RETURN OLD` — `BEFORE DELETE` trigger'i `NULL` qaytarsa o'chirish JIMGINA
bekor qilinadi (xatosiz!). Bu eng yomon variant bo'lardi: qoralama bozor
"o'chirildi" deb ko'rinardi-yu, aslida joyida qolardi.
"""

# ===========================================================================
# 0018 — BANDLIK DOMENINING O'ZGARMASLIGI (5-faza, D-12 / D-17.4, T-05-17)
# ===========================================================================
#
# ⚠⚠ SHAKL TANLOVI — BU FAZANING ENG OSON JIMGINA BUZILADIGAN QARORI.
#
# Yuqorida IKKI XIL o'zgarmaslik shakli bor va ular BIR-BIRIGA O'XSHAYDI:
#
#   SHARTSIZ  (`AUDIT_IMMUTABLE`)        -> har qanday UPDATE/DELETE rad etiladi
#   SHARTLI   (`TARIFF_PAST_IMMUTABLE`)  -> faqat O'TMISHDAGI qator qulflanadi
#                                           (`valid_from <= bugun`), qolgani ochiq
#
# 5-faza SHARTLI shaklning VAQT SHARTINI RAD ETADI (`05-PATTERNS.md` §S-3)
# va sabab MA'NODA: `valid_from <= bugun` qo'riqchisi «bugungi» qatorni
# OCHIQ qoldiradi, holbuki aynan bugungi javob — AI verdikti va nazoratchi
# javobi — o'lchov natijasini belgilaydi. «Bugun yozilgan javobni bugun
# to'g'rilash mumkin» qoidasi ostida xolis aniqlik da'vosi UMUMAN ma'noga
# ega bo'lmasdi: ko'r auditda AI javobi OSHKOR QILINGANDAN KEYIN javobni
# unga moslashtirish yo'li ochiq qolardi.
#
# =========================================================================
# ⚠⚠ LEKIN QORALAMA-BOZOR ISTISNOSI SAQLANADI VA U O'LCHANGAN ZARURAT.
#
# `market_delete_draft()` (`0019`) bu ikkala jadvaldan ham `DELETE` qiladi.
# Butunlay shartsiz qo'riqchi o'sha `DELETE` ni HAR DOIM `RAISE EXCEPTION`
# bilan to'xtatardi, ya'ni rejaning ikki qismi bir-birini INKOR QILARDI:
# tashlab ketilgan qoralama bozorlar bazada ABADIY to'planardi va yagona
# "tuzatish" yo'li kaskadni buzish bo'lardi. Bu YANGI muammo emas —
# `TARIFF_PAST_IMMUTABLE` docstringi uni 2-fazada AYNAN shu shaklda
# o'lchagan va `fixtures/two_markets.py::cleanup_two_markets()` ham,
# `cleanup_market_domain()` ham o'shandan beri `is_active = false` qadamini
# bajaradi.
#
# ⛔ RAD ETILGAN UCH MUQOBIL VA HAR BIRI BOSHQA SABABDAN:
#   * `session_replication_role = replica` — T-01-33 ning AYNAN o'zi:
#     u BARCHA triggerlarni (audit ham) o'chiradi va `sbozor_app` uchun
#     ataylab taqiqlangan;
#   * `ALTER TABLE ... DISABLE TRIGGER` kaskad ichida — `ACCESS EXCLUSIVE`
#     lock oladi va qo'riqchini butun baza uchun (boshqa sessiyalar uchun
#     ham) tranzaksiya davomida o'chirardi;
#   * `current_user = 'sbozor_owner'` sharti — EGANI ISTISNO QILARDI,
#     holbuki `tests/integration/test_audit_immutable.py` butun falsafasi
#     shundaki, qo'riqchi EGAGA QARSHI ham ishlashi kerak.
#
# ✅ TANLANGAN SHAKL — `TARIFF_PAST_IMMUTABLE` DAN KUCHLIROQ:
#   * `UPDATE`  -> HAR DOIM rad etiladi (bozor faolmi yoki qoralamami —
#                  farqi YO'Q). Tampering yo'li BUTUNLAY yopiq.
#   * `DELETE`  -> faqat QORALAMA bozor uchun o'tadi (`market_delete_draft()`
#                  ning yagona yo'li). Jonli bozorda rad etiladi.
# `TARIFF_PAST_IMMUTABLE` istisnoni IKKALA amalga ham beradi; bu yerda u
# faqat `DELETE` ga tegishli, ya'ni yuza IKKI BAROBAR TOR.
#
# NEGA BU XAVFSIZLIK ZAIFLASHUVI EMAS (`TARIFF_PAST_IMMUTABLE` bilan bir
# xil dalil): `is_active` `false` dan `true` ga FAQAT `market_activate()`
# orqali o'tadi va TESKARI yo'l YO'Q — `market_deactivate()` ataylab
# yaratilmagan. Ya'ni bir marta jonli bo'lgan bozor hech qachon qoralamaga
# qayta olmaydi va istisno unga HECH QACHON qo'llanmaydi. Qoralamada esa
# na kadr olinadi (`capture_due_markets()` `WHERE m.is_active`), na hisob
# yuritiladi — himoya qilinadigan o'lchov YO'Q.
#
# FAIL-CLOSED: `markets` o'qish `SECURITY DEFINER` siz, ya'ni RLS ostida
# bajariladi. Tenant kontekstsiz sessiyada 0 qator qaytadi, `EXISTS`
# yolg'on bo'ladi va qator QULFLANGAN deb hisoblanadi.
# =========================================================================
#
# ⛔ `SECURITY DEFINER` YOZILMAYDI: `markets` ni CHAQIRUVCHI huquqi bilan
# o'qish yuqoridagi fail-closed xulqning O'ZI. `tests/tenancy/test_meta.py`
# uni `pg_proc.prosecdef` bo'yicha qulflaydi.

OCCUPANCY_EVENT_IMMUTABLE = PGFunction(
    schema="public",
    signature="occupancy_event_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF TG_OP = 'DELETE'
     AND EXISTS (
       SELECT 1 FROM public.markets AS m
       WHERE m.id = OLD.market_id AND m.is_active = false
     ) THEN
    RETURN OLD;
  END IF;

  RAISE EXCEPTION 'occupancy_events is append-only (attempted %)', TG_OP;
END $$
""",
)
"""`BEFORE UPDATE OR DELETE ON occupancy_events` — AI JAVOBI TAHRIRLANMAYDI (D-12).

Model bergan verdikt — O'LCHOVNING KIRISHI. Uni tahrirlash mumkin bo'lsa
«model qanchalik to'g'ri edi?» savoliga javob beradigan yagona ma'lumot
yo'qolardi va aniqlik hisoboti o'z natijasini o'zi yozardi. Qayta ishlash
YANGI QATOR bo'ladi (`UNIQUE (market_id, snapshot_id, camera_zone_id,
model_version)`), eskisi esa joyida qoladi va ikkalasi SOLISHTIRILADI —
§E.15 dagi `timm` ilgagining butun mexanizmi shu.

`UPDATE` uchun SHART UMUMAN YO'Q — bozor faolmi yoki qoralamami, farqi
yo'q. `DELETE` uchun yagona istisno — QORALAMA bozor
(`market_delete_draft()` yo'li) va uning sababi yuqoridagi blokda,
rad etilgan muqobillari bilan birga.

`TG_OP` xabarga qo'shiladi (`AUDIT_IMMUTABLE` bilan bir xil sabab): ikki
xil urinish (UPDATE / DELETE) ikki xil tahdid modelidan keladi — birinchisi
natijani MOSLASHTIRADI, ikkinchisi noqulay dalilni YO'Q QILADI — va log'da
ular ajralib turishi kerak.

`RETURN OLD` FAQAT istisno shoxida: `BEFORE DELETE` triggeri `NULL`
qaytarsa amal JIMGINA bekor qilinadi (xatosiz!) va `market_delete_draft()`
"o'chirdim" deb `true` qaytarardi-yu, qatorlar joyida qolardi — ya'ni
kaskad yolg'on gapirardi. `RAISE` dan keyin esa qaytish nuqtasi umuman
yo'q (`AUDIT_IMMUTABLE` ham yozmaydi).

⚠ IKKI ALOHIDA FUNKSIYA, BITTA UMUMIY EMAS (`helpers.py:279-283` qoidasi):
xato xabari QAYSI qoida buzilganini aytishi kerak. `TG_TABLE_NAME` bo'yicha
shoxlanadigan umumiy funksiya ikkala jadvalni bir-biriga bog'lab qo'yardi
va birining qoidasini o'zgartirish ikkinchisiga ham tegardi.
"""

ZONE_REVIEW_IMMUTABLE = PGFunction(
    schema="public",
    signature="zone_review_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF TG_OP = 'DELETE'
     AND EXISTS (
       SELECT 1 FROM public.markets AS m
       WHERE m.id = OLD.market_id AND m.is_active = false
     ) THEN
    RETURN OLD;
  END IF;

  RAISE EXCEPTION 'zone_reviews is append-only (attempted %)', TG_OP;
END $$
""",
)
"""`BEFORE UPDATE OR DELETE ON zone_reviews` — NAZORATCHI JAVOBI QULFLANADI (D-17.4).

`OCCUPANCY_EVENT_IMMUTABLE` ning JUFTI va tana ataylab deyarli bir xil —
bu takror emas, ZARURAT (`tariff_past_immutable()` /
`category_period_past_immutable()` juftligi bilan bir xil qaror sinfi).

Bu yerdagi tahdid boshqa va u kuchliroq: ko'r auditda nazoratchi javob
berganidan KEYIN AI javobi oshkor bo'ladi (D-17). Javob o'sha paytda
tahrirlanishi mumkin bo'lsa xolis o'lchov ma'nosini BUTUNLAY yo'qotardi —
«to'g'rilash mumkin bo'lgan o'lchov o'lchov emas». Nosozlik jimgina
bo'lardi: hamma qator to'g'ri ko'rinardi va aniqlik foizi o'z-o'zidan
o'sardi.

⚠ JADVALDA IKKALA TRIGGER HAM BOR (audit + o'zgarmaslik). Postgres ning
tartib qoidasi (`helpers.py::attach_immutability_trigger` docstringi)
aynan kerakli natijani beradi: `BEFORE` `AFTER` dan oldin yuradi, ya'ni bu
qo'riqchi rad etgan `UPDATE` `audit_log` ga qator QOLDIRMAYDI. Rad etilgan
urinish "o'zgardi" deb yozilmasin — aks holda audit jurnali hech qachon
sodir bo'lmagan o'zgarishlarni ko'rsatardi.

⚠ QORALAMA `DELETE` ISTISNOSI AUDITNI YO'QOTMAYDI: istisno shoxi `RETURN
OLD` qiladi, ya'ni o'chirish HAQIQATAN sodir bo'ladi va `AFTER` audit
triggeri unga `delete` qatorini yozadi. Iz `audit_log` da qoladi — u esa
`market_delete_draft()` kaskadiga ATAYIN kiritilmagan (3-fazada
o'lchangan tuzoq).
"""

# ===========================================================================
# 0020 — BILLING DOMENINING O'ZGARMASLIGI (6-faza, D-07 / D-23 / D-25)
# ===========================================================================
#
# ⚠⚠ BU YERDA IKKALA SHAKL HAM ISHLATILADI VA TANLOV HAR FUNKSIYADA
#    OCHIQ YOZILGAN. Yuqoridagi 0018 bloki ikki shaklni solishtirgan:
#
#      SHARTSIZ  (`OCCUPANCY_EVENT_IMMUTABLE`) -> har qanday UPDATE/DELETE
#                                                 rad etiladi; `DELETE`
#                                                 uchun yagona istisno —
#                                                 QORALAMA bozor
#      SHARTLI   (`TARIFF_PAST_IMMUTABLE`)     -> faqat ma'lum shartdagi
#                                                 qator qulflanadi
#
# `daily_charges` va `payments` — SHARTSIZ (D-07 / D-23).
# `cashier_shifts` — SHARTLI (D-25) va bu SHAKL EMAS, ZARURAT: smena
# `open` -> `closed` o'tishi RUXSAT ETILISHI SHART, aks holda smenani
# umuman yopib bo'lmasdi. Uchala funksiyada ham `SECURITY DEFINER`
# YOZILMAYDI (yuqoridagi 0018 blokining oxirgi bandi) va
# `SET search_path = pg_catalog, public` MAJBURIY.
#
# QORALAMA-BOZOR ISTISNOSI UCHALASIDA HAM SAQLANADI va u O'LCHANGAN
# ZARURAT: `market_delete_draft()` (`0021`) oltala jadvaldan ham `DELETE`
# qiladi. Butunlay shartsiz qo'riqchi o'sha `DELETE` ni HAR DOIM
# `RAISE EXCEPTION` bilan to'xtatardi, ya'ni rejaning ikki qismi
# bir-birini INKOR QILARDI. Rad etilgan uch muqobil
# (`session_replication_role`, `DISABLE TRIGGER`, `current_user` sharti)
# yuqoridagi 0018 blokida sanab chiqilgan va bu yerda TAKRORLANMAYDI.

CHARGE_IMMUTABLE = PGFunction(
    schema="public",
    signature="charge_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF TG_OP = 'DELETE'
     AND EXISTS (
       SELECT 1 FROM public.markets AS m
       WHERE m.id = OLD.market_id AND m.is_active = false
     ) THEN
    RETURN OLD;
  END IF;

  RAISE EXCEPTION 'daily_charges is append-only (attempted %)', TG_OP;
END $$
""",
)
"""`BEFORE UPDATE OR DELETE ON daily_charges` — YOZILGAN HISOB TAHRIRLANMAYDI (D-07).

SHAKL: SHARTSIZ (`OCCUPANCY_EVENT_IMMUTABLE` ning aynan nusxasi), SHARTLI
EMAS. Sabab MA'NODA: `tariff_past_immutable()` ning `valid_from <= bugun`
sharti «bugungi» qatorni OCHIQ qoldiradi, holbuki hisob ERTASI KUNI 04:10
da tug'iladi — ya'ni har bir hisob o'zining birinchi kunida tahrirlanadigan
bo'lib qolardi. Aynan o'sha oyna esa eng qimmat: kassir kun yopilgandan
keyin «tuzatib» qo'yishi mumkin bo'lgan yagona payt.

Tuzatish YANGI QATOR bo'ladi (`charge_adjustments`, D-19), ya'ni asl summa
nizoda ko'rinib qoladi va «qancha talab qilingan edi?» savoli javobsiz
qolmaydi (D-02). Yakuniy summa — HISOBLANADIGAN KO'RINISH.

`TG_OP` xabarga qo'shiladi (`AUDIT_IMMUTABLE` bilan bir xil sabab): ikki
xil urinish ikki xil tahdid modelidan keladi — `UPDATE` summani JIMGINA
o'zgartiradi (T-06-15), `DELETE` esa qarzni butunlay yo'q qiladi.

`RETURN OLD` FAQAT istisno shoxida: `BEFORE DELETE` triggeri `NULL`
qaytarsa amal JIMGINA bekor qilinadi (xatosiz!) va `market_delete_draft()`
"o'chirdim" deb `true` qaytarardi-yu, qatorlar joyida qolardi — ya'ni
kaskad YOLG'ON gapirardi.

⚠ IKKI ALOHIDA FUNKSIYA, BITTA UMUMIY EMAS (`helpers.py:278-282` qoidasi):
xato xabari QAYSI jadvalning qoidasi buzilganini aytishi kerak. Tanasi
`payment_immutable()` niki bilan deyarli bir xil bo'lgani TAKROR emas,
ZARURAT — `tariff_past_immutable()` / `category_period_past_immutable()`
juftligi bilan aynan bir xil qaror sinfi.
"""

PAYMENT_IMMUTABLE = PGFunction(
    schema="public",
    signature="payment_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF TG_OP = 'DELETE'
     AND EXISTS (
       SELECT 1 FROM public.markets AS m
       WHERE m.id = OLD.market_id AND m.is_active = false
     ) THEN
    RETURN OLD;
  END IF;

  RAISE EXCEPTION 'payments is append-only (attempted %)', TG_OP;
END $$
""",
)
"""`BEFORE UPDATE OR DELETE ON payments` — TO'LOV O'CHIRILMAYDI (D-23, T-06-16).

`CHARGE_IMMUTABLE` ning JUFTI, lekin tahdid TESKARI TOMONDAN keladi va u
kuchliroq: yozilgan to'lovni o'chirish «pul kelmagan» degan da'voni HECH
QANDAY iz qoldirmasdan yaratadi. `daily_charges` da tahdid qarzni
YASHIRISH edi; bu yerda esa TUSHUMNI yashirish — ya'ni aynan mahsulot fosh
qiladigan nosozlik turi (`PROJECT.md` Core Value).

Xato yozuv STORNO qatori bilan qoplanadi: `kind = 'reversal'` +
`reverses_payment_id` + `reversal_reason` (uchalasi ham `0020` da ikki
tomonlama `CHECK` bilan bog'langan). Nizoda IKKALA yozuv ham ko'rinadi —
«to'ladi» va «bekor qilindi, sababi shu» (D-02).

⚠ JADVALDA AUDIT TRIGGERI YO'Q va bu qo'riqchini KUCHSIZLANTIRMAYDI: iz
`payments` NING O'ZIDA yashaydi (append-only jadval o'z tarixi), ilova
darajasidagi audit esa `AuditAction.PAYMENT_REVERSE` bilan yoziladi
(`enums.py::AuditAction` docstringi).
"""

SHIFT_DECLARATION_IMMUTABLE = PGFunction(
    schema="public",
    signature="shift_declaration_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF EXISTS (
      SELECT 1 FROM public.markets AS m
      WHERE m.id = OLD.market_id AND m.is_active = false
    ) THEN
      RETURN OLD;
    END IF;

    RAISE EXCEPTION 'cashier_shifts rows are not deletable (attempted %)', TG_OP
      USING ERRCODE = '23514';
  END IF;

  IF OLD.status = 'closed' THEN
    RAISE EXCEPTION 'cashier shift % is closed and cannot be changed (D-25)', OLD.id
      USING ERRCODE = '23514';
  END IF;

  IF OLD.declared_soum IS NOT NULL
     AND NEW.declared_soum IS DISTINCT FROM OLD.declared_soum THEN
    RAISE EXCEPTION 'declared_soum of shift % is already recorded (D-25)', OLD.id
      USING ERRCODE = '23514';
  END IF;

  IF OLD.system_soum IS NOT NULL
     AND NEW.system_soum IS DISTINCT FROM OLD.system_soum THEN
    RAISE EXCEPTION 'system_soum of shift % is already recorded (D-25)', OLD.id
      USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END $$
""",
)
"""`BEFORE UPDATE OR DELETE ON cashier_shifts` — KO'R DEKLARATSIYA QULFLANADI (D-25).

=============================================================================
⛔ SHAKL TANLOVI: SHARTLI (`TARIFF_PAST_IMMUTABLE` sinfi), SHARTSIZ EMAS —
   VA BU ZARURAT, QULAYLIK EMAS.

Shartsiz shakl (`CHARGE_IMMUTABLE` / `PAYMENT_IMMUTABLE`) HAR QANDAY
`UPDATE` ni rad etadi. Smena esa `open` -> `closed` o'tishini TALAB QILADI:
u yagona holat o'zgarishi va usiz smenani umuman yopib bo'lmasdi, ya'ni
CASH-04 ning butun oqimi (ko'r deklaratsiya -> variance) IMKONSIZ bo'lardi.
Ya'ni bu yerda «kuchliroq shakl» ni tanlash mahsulotni ishlamaydigan
qilardi — 0018 blokidagi tanlovning TESKARI tomoni.

Shartli shakl esa `tariffs` nikidan HAM TOR: u vaqt shartiga
(`valid_from <= bugun`) umuman tayanmaydi, chunki bu yerdagi qulf VAQT
emas, HOLAT va QIYMAT bo'yicha. Ruxsat etilgan yagona o'zgarish —
`NULL` dan qiymatga o'tish.

TO'RT SHOX VA HAR BIRI BOSHQA NOSOZLIKNI YOPADI:

  (a) `OLD.status = 'closed'` -> HAR QANDAY `UPDATE` rad etiladi.
      «Qayta ochish» yo'li smenani tizim summasiga MOSLASHTIRISH imkonini
      berardi va ko'r deklaratsiya ma'nosini butunlay yo'qotardi (D-25:
      `closed` — YAKUNIY holat).
  (b) `declared_soum` bir marta yozilgach QAYTA YOZILMAYDI. Bu (a) dan
      MUSTAQIL: deklaratsiya `open` smenaga ham yozilishi mumkin va
      o'shanda (a) hali ishlamaydi.
  (c) `system_soum` uchun ayni shart. Tizim summasi yopilish paytida
      MUZLATILADI, chunki `payments` keyin ham o'zgaradi (storno YANGI
      qator) — qayta hisoblangan son BOSHQA javob berardi.
  (d) `DELETE` — qoralama bozor shoxidan tashqari RAD ETILADI. Smenani
      o'chirish variance yozuvini butunlay yo'q qilardi.

⚠ `IS DISTINCT FROM` MAJBURIY, `<>` EMAS: `NEW.declared_soum` `NULL`
  bo'lsa `<>` `NULL` berardi va shart JIMGINA o'tib ketardi — ya'ni
  deklaratsiyani `NULL` ga qaytarish yo'li ochiq qolardi.

⚠ `RETURN NEW` — `UPDATE` shoxining YAGONA chiqishi. `DELETE` shoxi
  yuqorida tugaydi (`RETURN OLD` yoki `RAISE`), ya'ni bu yerga faqat
  `UPDATE` yetib keladi va `NEW` HAR DOIM mavjud.

⚠ JADVALDA IKKALA TRIGGER HAM BOR (audit + o'zgarmaslik). `BEFORE`
  `AFTER` dan oldin yuradi, ya'ni bu qo'riqchi rad etgan `UPDATE`
  `audit_log` ga qator QOLDIRMAYDI (`helpers.py:295-298`) — rad etilgan
  urinish "o'zgardi" deb yozilmasin.

⛔ `ERRCODE = '23514'` (check_violation) — TO'RTALA SHOXDA HAM, VA BU
  FUNKSIYA ICHIDA IZCHIL BO'LISHI SHART.

  Repoda ikki xato-sinfi bor va ular SHAKL bilan birga yuradi:
    * SHARTSIZ append-only qo'riqchi (`audit_immutable()`,
      `occupancy_event_immutable()`, `charge_immutable()`,
      `payment_immutable()`) — ERRCODE'siz, ya'ni `P0001`
      (`psycopg.errors.RaiseException`);
    * SHARTLI domen-qoidasi qo'riqchisi (`tariff_past_immutable()`,
      `category_period_past_immutable()`, `markets_delete_guard()`) —
      `23514` (`psycopg.errors.CheckViolation`).

  Bu funksiya IKKINCHI sinfda (yuqoridagi SHAKL TANLOVI bloki), shuning
  uchun uning HAR TO'RT shoxi ham `23514` beradi — `DELETE` shoxi ham.
  Bitta funksiya ichida ikki xato-sinfini aralashtirish chaqiruvchini
  IKKI xil `except` yozishga majburlardi va `MARKETS_DELETE_GUARD`
  docstringidagi «Yangi konvensiya KIRITILMAYDI» qoidasini buzardi.

⚠ `status` LITERALI (`'closed'`) TANADA QO'LDA YOZILGAN va bu boshqa
  yo'li yo'q: `PGFunction` ta'rifi SQL matni, ya'ni u `sbozor_core.enums`
  ni import qila olmaydi (`migrations/entities` `alembic_utils` ga
  bog'langan, `sbozor_core` esa unga bog'lanmaydi). Qiymatning o'zgarishi
  esa `0020` ning `SHIFT_STATUS_CHECK` ini ham buzardi, ya'ni u jimgina
  o'tib keta olmaydi.
=============================================================================
"""

OCCUPANCY_TRIGGER_FUNCTIONS: list[PGFunction] = [
    OCCUPANCY_EVENT_IMMUTABLE,
    ZONE_REVIEW_IMMUTABLE,
]
"""5-faza qo'riqchilari — `0018_occupancy_domain` yaratadi.

Trigger FUNKSIYASI bu yerda, trigger'ning O'ZI esa migratsiyada
`attach_immutability_trigger(...)` bilan (`0008_temporal.py` naqshi —
`alembic-utils` triggerlarni boshqarmaydi).

Ro'yxat ALOHIDA va u `AUDIT_TRIGGER_FUNCTIONS` / `MARKET_DOMAIN_TRIGGER_
FUNCTIONS` bilan bir xil qoidaga bo'ysunadi: har migratsiya O'Z scope'li
ro'yxatini oladi, `ALL_TRIGGER_FUNCTIONS` esa faqat KUZATUV aggregati.
"""

NVR_DOMAIN_TRIGGER_FUNCTIONS: list[PGFunction] = [
    MARKETS_DELETE_GUARD,
]
"""3-faza qo'riqchisi — `0013_market_delete_guard` yaratadi.

Trigger FUNKSIYASI bu yerda, trigger'ning O'ZI esa migratsiyada xom
`op.execute("CREATE TRIGGER ...")` bilan (`0002_audit.py` dagi naqsh —
`alembic-utils` triggerlarni boshqarmaydi).
"""

AUDIT_TRIGGER_FUNCTIONS: list[PGFunction] = [
    FN_AUDIT_ROW,
    AUDIT_IMMUTABLE,
]
"""`0002_audit` YARATADIGAN to'plam — BU RO'YXAT MUZLATILGAN.

⚠ YANGI FUNKSIYA BU YERGA QO'SHILMAYDI. `migrations/versions/0002_audit.py`
shu ro'yxat ustidan `upgrade()` da ham, `downgrade()` da ham TSIKL qiladi.
Kengaytirilganda oqibat O'LCHANGAN (`DuplicateFunction`): 2-faza funksiyalari
1-fazaning audit migratsiyasida yaratilib qolardi va keyin ularni O'Z
migratsiyasida (`0007`/`0008`) yaratmoqchi bo'lgan `create_entity()`
`function "stall_code_claim" already exists` bilan yiqilardi. Qo'shimcha
zarar: `0002` ning `downgrade()` i 2-faza funksiyalarini ham o'chirib
yuborardi.

Bu `migrations/entities/__init__.py::TENANT_TABLES` bilan AYNAN bir xil
qoida — migratsiya tsikl qiladigan ro'yxat o'sha migratsiyaga tegishli va
keyin muzlaydi.
"""

MARKET_DOMAIN_TRIGGER_FUNCTIONS: list[PGFunction] = [
    STALL_CODE_CLAIM,
    TARIFF_PAST_IMMUTABLE,
    CATEGORY_PERIOD_PAST_IMMUTABLE,
]
"""2-faza domen qoidalari — `0007` (kod reyestri) va `0008` (daxlsizlik) yaratadi.

Trigger FUNKSIYASI bu yerda, trigger'ning O'ZI esa migratsiyada xom
`op.execute("CREATE TRIGGER ...")` bilan (`alembic-utils` triggerlarni
boshqarmaydi — `0002_audit.py` dagi naqsh).
"""

BILLING_TRIGGER_FUNCTIONS: list[PGFunction] = [
    CHARGE_IMMUTABLE,
    PAYMENT_IMMUTABLE,
    SHIFT_DECLARATION_IMMUTABLE,
]
"""6-faza qo'riqchilari — `0020_billing_domain` yaratadi.

Trigger FUNKSIYASI bu yerda, trigger'ning O'ZI esa migratsiyada
`attach_immutability_trigger(...)` bilan (`0018` naqshi — `alembic-utils`
triggerlarni boshqarmaydi).

UCHTA ALOHIDA FUNKSIYA, ikkitasining tanasi deyarli bir xil bo'lsa ham:
umumiy `TG_TABLE_NAME` funksiyasi `helpers.py:278-282` bilan TAQIQLANGAN —
xato xabari QAYSI jadvalning qoidasi buzilganini aytishi kerak va uchala
qoida ham MUSTAQIL o'zgaradi (D-07, D-23, D-25 uch xil qaror).

Ro'yxat ALOHIDA va u `OCCUPANCY_TRIGGER_FUNCTIONS` bilan bir xil qoidaga
bo'ysunadi: har migratsiya O'Z scope'li ro'yxatini oladi,
`ALL_TRIGGER_FUNCTIONS` esa faqat KUZATUV aggregati.
"""

# ===========================================================================
# 7-FAZA — BILDIRISHNOMA DOMENI (0023_notification_domain, D-14 / D-20)
# ===========================================================================
#
# ⚠ SHAKL 0018/0020 BLOKLARIDAN NUSXA: `SECURITY DEFINER` YOZILMAYDI va
#   `SET search_path = pg_catalog, public` MAJBURIY.
#
# QORALAMA-BOZOR ISTISNOSI SAQLANADI va u O'LCHANGAN ZARURAT:
# `market_delete_draft()` (`0023` ning kaskad kengaytmasi) bu jadvaldan ham
# `DELETE` qiladi. Butunlay shartsiz qo'riqchi o'sha `DELETE` ni HAR DOIM
# `RAISE EXCEPTION` bilan to'xtatardi, ya'ni rejaning ikki qismi
# bir-birini INKOR QILARDI. Rad etilgan uch muqobil
# (`session_replication_role`, `DISABLE TRIGGER`, `current_user` sharti)
# yuqoridagi 0018 blokida sanab chiqilgan va bu yerda TAKRORLANMAYDI.

CASE_EVENT_IMMUTABLE = PGFunction(
    schema="public",
    signature="case_event_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF TG_OP = 'DELETE'
     AND EXISTS (
       SELECT 1 FROM public.markets AS m
       WHERE m.id = OLD.market_id AND m.is_active = false
     ) THEN
    RETURN OLD;
  END IF;

  RAISE EXCEPTION 'reconciliation_case_events is append-only (attempted %)', TG_OP;
END $$
""",
)
"""`BEFORE UPDATE OR DELETE ON reconciliation_case_events` — TARIX QAYTA YOZILMAYDI.

SHAKL: SHARTSIZ (`OCCUPANCY_EVENT_IMMUTABLE` / `CHARGE_IMMUTABLE` ning
aynan nusxasi). Sabab MA'NODA: case tarixi «kim, qachon, qaysi holatdan
qaysi holatga o'tkazdi» degan savolning YAGONA javobi (D-14) va u nizoda
(D-02) dalil bo'ladi. Tahrirlanadigan tarix — tarix EMAS.

Bu T-07-09 ning aynan mitigatsiyasi: «case tarixining qayta yozilishi»
tahdidi faqat SXEMA darajasida yopiladi — ilova qatlamidagi «biz UPDATE
yozmaymiz» kelishuvini xom SQL yo'li BUTUNLAY chetlab o'tadi
(`migrations/entities/triggers.py` boshidagi o'lchangan sinf).

⚠ NEGA `reconciliation_cases` GA BUNDAY QO'RIQCHI QO'YILMAYDI: o'sha
jadval ATAYIN o'zgaradi (`new` -> `in_review` -> `justified`) — u JARAYON
qatori (D-11). Uning izi audit triggeri bilan olinadi
(`schema_contract.AUDITED_TABLES`), bu jadval esa o'sha izning
O'ZGARMAS, ilova yozadigan jufti.

`RETURN OLD` FAQAT istisno shoxida: `BEFORE DELETE` triggeri `NULL`
qaytarsa amal JIMGINA bekor qilinadi (xatosiz!) va `market_delete_draft()`
"o'chirdim" deb `true` qaytarardi-yu, qatorlar joyida qolardi — ya'ni
kaskad YOLG'ON gapirardi.

⚠ ALOHIDA FUNKSIYA, umumiy `TG_TABLE_NAME` shoxlanishi EMAS
(`helpers.py:278-282` qoidasi): xato xabari QAYSI jadvalning qoidasi
buzilganini aytishi kerak.
"""

NOTIFICATION_TRIGGER_FUNCTIONS: list[PGFunction] = [CASE_EVENT_IMMUTABLE]
"""7-faza qo'riqchisi — `0023_notification_domain` yaratadi.

BITTA FUNKSIYA, chunki bu domenda o'zgarmas jadval AYNAN BITTA:
`reconciliation_case_events`. Qolgan to'rttasi ATAYIN o'zgaradi —
`reconciliation_cases` (jarayon), `notification_outbox` (holat mashinasi),
`vendor_telegram_bindings` (bekor qilinadi), `market_notification_settings`
(sozlama).

Ro'yxat ALOHIDA va u `BILLING_TRIGGER_FUNCTIONS` bilan bir xil qoidaga
bo'ysunadi: har migratsiya O'Z scope'li ro'yxatini oladi,
`ALL_TRIGGER_FUNCTIONS` esa faqat KUZATUV aggregati.
"""

ALL_TRIGGER_FUNCTIONS: list[PGFunction] = [
    *AUDIT_TRIGGER_FUNCTIONS,
    *MARKET_DOMAIN_TRIGGER_FUNCTIONS,
    *NVR_DOMAIN_TRIGGER_FUNCTIONS,
    *OCCUPANCY_TRIGGER_FUNCTIONS,
    *BILLING_TRIGGER_FUNCTIONS,
    *NOTIFICATION_TRIGGER_FUNCTIONS,
]
"""BARCHA trigger funksiyalari — autogenerate reyestri (`ALL_ENTITIES`) uchun.

Faqat KUZATUV ro'yxati: `register_entities()` unga qarab ta'rif o'zgarganda
`op.replace_entity(...)` taklif qiladi. Birorta migratsiya bu aggregat
ustidan tsikl QILMAYDI — har bir migratsiya o'z scope'li ro'yxatini oladi.
"""
