"""market_delete_guard: kaskad NVR domenini qamraydi + faol bozor DB darajasida qulflanadi

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-03

=============================================================================
WR-02 NING TARIXI — NEGA U 2-FAZADA EMAS, SHU YERDA.

Band 2-fazaning `02-REVIEW.md` ida ochilgan va o'sha yerda `0011` bilan BIR
OYNAGA tiqilmadi. Sabab texnik edi: `0011` `market_create()` ni almashtiradi
va uning `downgrade()` i eski tanani QAYTA YOZADI. Unga ikkinchi, mutlaqo
boshqa mavzudagi o'zgarishni qo'shish downgrade'ni ikki mustaqil narsani
bir vaqtda orqaga qaytarishga majburlardi — ya'ni "0010 ga qaytdim" degan
da'vo tekshirib bo'lmaydigan holga kelardi.

3-fazada esa u O'Z JOYINI TOPDI va bu tasodif emas: `0012` to'rtta yangi
tenant jadvalini olib keldi, ya'ni `market_delete_draft()` kaskadi BARIBIR
kengaytirilishi shart edi (aks holda `test_market_delete_guard.py` qizil
qolardi). Ikkala o'zgarish ham AYNAN BIR funksiyaga tegadi, ya'ni ularni
bitta revisionda qilish downgrade'ni SODDALASHTIRADI — bitta eski ta'rif,
bitta qaytish nuqtasi.
=============================================================================

IKKI QATLAM, IKKALASI HAM KERAK VA ULAR BIR-BIRINI ALMASHTIRMAYDI:

  1. `market_delete_draft()` — ILOVA yo'lining qo'riqchisi. `is_active`
     `false` bo'lmasa `false` qaytaradi va hech nimaga tegmaydi.
     Chaqiruvchi buni 404/409 ga aylantiradi va foydalanuvchi TUSHUNARLI
     xabar oladi.
  2. `markets_delete_guard()` — SXEMA qatlamining qo'riqchisi. `psql` dan
     yuborilgan xom `DELETE FROM markets` ham, xato yozilgan kelajakdagi
     `SECURITY DEFINER` funksiya ham shu yerdan o'tolmaydi (T-03-17).

Birinchisiz foydalanuvchi tushunarsiz DB xatosini ko'rardi; ikkinchisisiz
kafolat ilova qatlamining odob-axloqiga tayanardi. Shuning uchun ikkalasi
ham bor va ikkalasi ham ALOHIDA o'lchanadi.

⚠ TRIGGER `market_delete_draft()` NI BLOKLAMAYDI.
Funksiya faqat QORALAMA bozorni o'chiradi, ya'ni triggerning sharti uning
yo'lida hech qachon otilmaydi. Buni IKKI TOMONDAN o'lchash shart (qoralama
o'chadi / faol o'chmaydi) — faqat ikkinchisini tekshirish "cheklov to'g'ri
ishlayapti" ni emas, "hech narsa o'chmayapti" ni isbotlagan bo'lardi.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from alembic_utils.pg_function import PGFunction

from migrations.entities.functions import MARKET_DELETE_DRAFT
from migrations.entities.triggers import MARKETS_DELETE_GUARD
from migrations.helpers import APP_ROLE, create_entity, drop_entity

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DELETE_GUARD_TRIGGER = "trg_markets_delete_guard"

MARKET_DELETE_DRAFT_SIGNATURE = "market_delete_draft(uuid)"
"""`REVOKE`/`GRANT` uchun imzo — `0010` dagi shakl bilan bir xil."""


MARKET_DELETE_DRAFT_WITHOUT_NVR = PGFunction(
    schema="public",
    signature=MARKET_DELETE_DRAFT.signature,
    definition="""
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
DECLARE
  v_is_active boolean;
BEGIN
  SELECT m.is_active INTO v_is_active
  FROM public.markets AS m
  WHERE m.id = p_market_id;

  IF v_is_active IS DISTINCT FROM false THEN
    RETURN false;
  END IF;

  DELETE FROM public.stall_assignments          WHERE market_id = p_market_id;
  DELETE FROM public.stall_category_periods     WHERE market_id = p_market_id;
  DELETE FROM public.tariffs                    WHERE market_id = p_market_id;
  DELETE FROM public.stall_code_registry        WHERE market_id = p_market_id;
  DELETE FROM public.stalls                     WHERE market_id = p_market_id;
  DELETE FROM public.vendors                    WHERE market_id = p_market_id;
  DELETE FROM public.zones                      WHERE market_id = p_market_id;
  DELETE FROM public.stall_categories           WHERE market_id = p_market_id;
  DELETE FROM public.market_calendar_exceptions WHERE market_id = p_market_id;
  DELETE FROM public.market_profile             WHERE market_id = p_market_id;
  DELETE FROM public.user_market_roles          WHERE market_id = p_market_id;
  DELETE FROM public.refresh_tokens             WHERE market_id = p_market_id;
  DELETE FROM public.markets                    WHERE id = p_market_id;

  RETURN true;
END $$
""",
)
"""`0010`/`0012` davridagi `market_delete_draft()` — NVR jadvallarisiz.

BU YERDA, MIGRATSIYANING O'ZIDA MUZLATILGANI ATAYIN va sabab
`0011_weekday_choice.py::MARKET_CREATE_WITH_DEFAULT` bilan AYNAN BIR XIL:
`alembic_utils` `PGFunction` ni MODUL ta'rifidan oladi va
`migrations/entities/functions.py` endi YANGI (NVR jadvallari bilan) tanani
saqlaydi. `drop_entity()` faqat imzo bilan ishlaydi, `create_entity()` esa
TANANI yozadi — ya'ni bu nusxa bo'lmasa `downgrade()` yangi tanani
qaytarardi va "0012 ga qaytdim" degan da'vo YOLG'ON bo'lardi.

Bundan tashqari bu yerda u ZARURAT: downgrade'dan keyin NVR jadvallari
`0012` ning `downgrade()` i bilan o'chiriladi, ya'ni ularga `DELETE` yozgan
funksiya `relation "public.cameras" does not exist` bilan yiqilardi
(`plpgsql` tanasi CREATE paytida tekshirilmaydi — xato faqat CHAQIRUVDA
chiqadi, ya'ni eng yomon paytda).

`signature` `MARKET_DELETE_DRAFT` dan OLINADI, qayta yozilmaydi: imzo bu
migratsiyada o'zgarmaydi va uni ikkinchi marta yozish ikki nusxa ajralib
ketadigan yana bir joy bo'lardi.
"""


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. Kaskad NVR domenini qamraydi (W0-7 ning ikkinchi yarmi).
    #
    #    IMZO O'ZGARMAYDI, lekin `DROP FUNCTION` grant'ni ham olib tashlaydi
    #    va `CREATE` dan keyin Postgres `EXECUTE TO PUBLIC` ni STANDART
    #    qaytaradi — shuning uchun `REVOKE`/`GRANT` jufti QAYTA yoziladi
    #    (`0011` dagi bilan bir xil naqsh). Usiz bazadagi HAR QANDAY rol
    #    qoralama bozorni o'chira olardi.
    # ------------------------------------------------------------------
    drop_entity(MARKET_DELETE_DRAFT_WITHOUT_NVR)
    create_entity(MARKET_DELETE_DRAFT)
    _regrant()

    # ------------------------------------------------------------------
    # 2. Sxema qatlamining qo'riqchisi (WR-02 ning asosiy mazmuni).
    #
    #    Trigger FUNKSIYASI `alembic-utils` nazoratida
    #    (`migrations/entities/triggers.py`), trigger'ning O'ZI esa xom
    #    `op.execute("CREATE TRIGGER ...")` bilan — `0002_audit.py` da
    #    o'rnatilgan naqsh. Ikkala mexanizmni aralashtirish autogenerate'ni
    #    har safar "o'zgargan" deb ko'rsatishga majburlardi.
    #
    #    `BEFORE`, `AFTER` EMAS: qo'riqchi o'chirish SODIR BO'LISHIDAN
    #    OLDIN to'xtatishi kerak (`attach_immutability_trigger()` bilan bir
    #    xil sabab).
    # ------------------------------------------------------------------
    create_entity(MARKETS_DELETE_GUARD)
    op.execute(
        f"CREATE TRIGGER {DELETE_GUARD_TRIGGER} "
        "BEFORE DELETE ON markets "
        "FOR EACH ROW EXECUTE FUNCTION markets_delete_guard()"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Teskari tartib: trigger -> trigger funksiyasi -> kaskad.
    op.execute(f"DROP TRIGGER IF EXISTS {DELETE_GUARD_TRIGGER} ON markets")
    drop_entity(MARKETS_DELETE_GUARD)

    drop_entity(MARKET_DELETE_DRAFT)
    create_entity(MARKET_DELETE_DRAFT_WITHOUT_NVR)
    _regrant()


def _regrant() -> None:
    """`market_delete_draft()` uchun `REVOKE PUBLIC` + `GRANT sbozor_app`.

    `0010` va `0011` dagi bilan AYNAN bir xil naqsh: `DROP FUNCTION` grant'ni
    ham olib tashlaydi va `CREATE FUNCTION` dan keyin Postgres yangi
    funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi. Usiz `market_delete_
    draft()` ning butun "tor yuza" qarori jimgina bekor bo'lardi — u
    `SECURITY DEFINER` va o'n oltita jadvaldan `DELETE` qiladi.
    """
    op.execute(f"REVOKE ALL ON FUNCTION {MARKET_DELETE_DRAFT_SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {MARKET_DELETE_DRAFT_SIGNATURE} TO {APP_ROLE}")
