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
    "CATEGORY_PERIOD_PAST_IMMUTABLE",
    "FN_AUDIT_ROW",
    "MARKET_DOMAIN_TRIGGER_FUNCTIONS",
    "STALL_CODE_CLAIM",
    "TARIFF_PAST_IMMUTABLE",
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

ALL_TRIGGER_FUNCTIONS: list[PGFunction] = [
    *AUDIT_TRIGGER_FUNCTIONS,
    *MARKET_DOMAIN_TRIGGER_FUNCTIONS,
]
"""BARCHA trigger funksiyalari — autogenerate reyestri (`ALL_ENTITIES`) uchun.

Faqat KUZATUV ro'yxati: `register_entities()` unga qarab ta'rif o'zgarganda
`op.replace_entity(...)` taklif qiladi. Birorta migratsiya bu aggregat
ustidan tsikl QILMAYDI — har bir migratsiya o'z scope'li ro'yxatini oladi.
"""
