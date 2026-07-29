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

__all__ = ["ALL_TRIGGER_FUNCTIONS", "AUDIT_IMMUTABLE", "FN_AUDIT_ROW"]

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

ALL_TRIGGER_FUNCTIONS: list[PGFunction] = [
    FN_AUDIT_ROW,
    AUDIT_IMMUTABLE,
]
