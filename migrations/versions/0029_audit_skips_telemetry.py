"""Audit jurnali telemetriya yangilanishlarini yozmaydi.

⛔⛔ NEGA KERAK BO'LDI (260829, panelda o'lchandi).

    `cameras.last_seen_at` — «qurilma hali javob beryapti» degan
    o'lchov. CamAgent obyektida u har heartbeat'da (60 soniya) 16
    kamera uchun suriladi va audit triggeriga har safar UPDATE bo'lib
    ko'rinardi: 24 daqiqada 432 yozuv, ya'ni kuniga ~26 000.

    Jurnal shu bilan to'lib, HAQIQIY o'zgarishlar — nom tahriri,
    arxivlash, rekvizit almashuvi — ularning orasida ko'rinmay
    qolardi. Nizoda esa audit jurnali birinchi so'raladigan hujjat.

⚠ FILTR TOR: faqat `last_seen_at`, `last_discovery_at` va
  `updated_at`. Boshqa har qanday ustun o'zgarsa yozuv AVVALGIDEK
  yoziladi — ya'ni bu qadam auditning qamrovini kamaytirmaydi,
  shovqinni oladi.

Revision ID: 0029
Revises: 0028
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | Sequence[str] | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_YANGI = """
CREATE OR REPLACE FUNCTION public.fn_audit_row()
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

    -- ⛔⛔ TELEMETRIYA AUDIT HODISASI EMAS (260829, panelda o'lchandi).
    --
    --     `last_seen_at` / `last_discovery_at` — «qurilma hali
    --     javob beryapti» degan o'lchov. U CamAgent obyektida har
    --     heartbeat'da (60 s) 16 kamera uchun suriladi va audit
    --     triggeriga har safar UPDATE bo'lib ko'rinardi: 24 daqiqada
    --     432 yozuv, ya'ni kuniga ~26 000. Jurnal shu bilan to'lib,
    --     HAQIQIY o'zgarishlar — nom tahriri, arxivlash, rekvizit
    --     almashuvi — ularning orasida ko'rinmay qolardi.
    --
    --     Nizoda audit jurnali BIRINCHI so'raladigan hujjat: uni
    --     telemetriya bilan to'ldirish uni yaroqsiz qiladi.
    --
    -- ⚠ `updated_at` ro'yxatda, LEKIN u YOLG'IZ o'zgarmaydi — u har
    --   doim haqiqiy o'zgarish bilan birga keladi. Ro'yxatda turishi
    --   shuning uchun xavfsiz: faqat telemetriya bilan BIRGA
    --   kelganida yozuv o'tkazib yuboriladi.
    IF v_keys <@ ARRAY['last_seen_at', 'last_discovery_at', 'updated_at'] THEN
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
"""

_ESKI = """
CREATE OR REPLACE FUNCTION public.fn_audit_row()
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
"""


def upgrade() -> None:
    """⚠ `CREATE OR REPLACE` — TRIGGERLAR QAYTA ULANMAYDI.

    Funksiya tanasi almashadi, unga bog'langan o'nlab trigger esa
    o'z joyida qoladi. `DROP FUNCTION ... CASCADE` ularning HAMMASINI
    o'chirib yuborardi va har birini qayta yaratish kerak bo'lardi —
    bittasi unutilsa o'sha jadval jimgina auditsiz qolardi.
    """
    op.execute(_YANGI)


def downgrade() -> None:
    op.execute(_ESKI)
