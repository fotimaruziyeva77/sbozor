"""weekday_choice: `open_weekdays` ning jimgina "har kuni ochiq" standartini olib tashlash

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-02

=============================================================================
BU MIGRATSIYA QO'SHMAYDI — OLIB TASHLAYDI, VA AYNAN SHU TUZATISHNING O'ZI.

02-REVIEW.md WR-06 (va 02-VERIFICATION.md SC#4 ogohlantirishi) o'lchagan
holat: `market_profile.open_weekdays` IKKI yo'ldan standart qiymat olardi —

  1. `market_create()` tanasidagi
     `COALESCE(p_open_weekdays, ARRAY[1,2,3,4,5,6,7]::smallint[])`;
  2. ustunning o'zidagi `server_default = '{1,2,3,4,5,6,7}'`.

Natijada `array_length(open_weekdays, 1) > 0` HAR DOIM rost bo'lardi, ya'ni
`MarketRepository._SETUP_STATUS` dagi `calendar_configured` har doim `True`,
`markets.py::_blocking()` dagi `calendar_missing` (step 7) bandi esa bozor
yaratadigan YAGONA yo'lda (`POST /api/v1/markets` -> `market_create()`) HECH
QACHON ishga tushmasdi. To'siq kodda bor edi, hayotda yo'q edi.

OQIBAT — PUL NIZOSI, "kosmetika" EMAS: dushanba kuni yopiladigan bozor
"har kuni ochiq" deb faollashardi. D-17/D-18 bo'yicha `open_weekdays`
6-fazadagi kunlik patta hisobining KIRISHI, ya'ni sotuvchi bozor yopiq
bo'lgan kun uchun hisob olardi — bu mahsulot bartaraf etish uchun mavjud
bo'lgan nizo sinfining o'zi.

TESTNING YOZIB BO'LMASLIGI BELGINING O'ZI EDI: `calendar_missing` uchun
assert 02-11 dan beri YOZIB BO'LMAS holatda edi, chunki holat yuzaga
kelmasdi. `tests/integration/test_wizard_flow.py::INCOMPLETE_CASES`
docstringi buni "strukturaviy jihatdan erishib bo'lmaydigan holat" deb
yozib ham qo'ygan edi — ya'ni nosozlik hujjatlashtirilgan, lekin
xatti-harakat sifatida qabul qilingan edi.
=============================================================================

IKKALA YO'LNI HAM YOPISH SHART, BITTASINI EMAS. Faqat `COALESCE` olib
tashlansa, ustun sanab o'tilmagan har qanday `INSERT` (seed, fixture,
kelajakdagi kod) standartni ikkinchi yo'ldan qaytarardi va to'siq o'sha
yo'lda yana ishlamay qolardi.

YANGI KONTRAKT — UCH HOLAT, UCHALASI BOSHQA MA'NODA:

  * `NULL`  — "hali tanlanmagan". RUXSAT ETILADI va u `calendar_missing`
    to'sig'ini ISHGA TUSHIRADI.
  * `'{}'`  — "hech qachon ochilmaydi". RAD ETILADI (CHECK) — bu boshqa
    nosozlik va u fail-closed `market_is_open()` bilan birga tushumni
    jimgina nolga tushirardi.
  * to'ldirilgan massiv — normal holat.

`market_is_open()` VA `_SETUP_STATUS` ATAYIN TEGILMAYDI. Ikkalasi ham
`NULL` ni ALLAQACHON to'g'ri talqin qiladi va bu o'lchandi:
  * `EXTRACT(ISODOW FROM d)::smallint = ANY(NULL)` -> `NULL` -> uch qavatli
    `COALESCE` oxiridagi `false` (fail-closed saqlanadi);
  * `array_length(NULL, 1)` -> `NULL` -> `COALESCE(..., 0) > 0` -> `false`
    (`calendar_configured` yolg'on).
Ya'ni bu migratsiya mavjud fail-closed mantiqni O'ZGARTIRMAYDI — u shu
mantiq YETIB BORA OLMAGAN holatni yuzaga keltiradi.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from alembic_utils.pg_function import PGFunction

from migrations.entities.functions import MARKET_CREATE
from migrations.helpers import APP_ROLE, create_entity, drop_entity

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_market_profile_open_weekdays_valid"

_NEW_CHECK = (
    "open_weekdays IS NULL OR ("
    "open_weekdays <@ ARRAY[1,2,3,4,5,6,7]::smallint[] "
    "AND array_length(open_weekdays,1) IS NOT NULL)"
)
"""`sbozor_core.models.market.OPEN_WEEKDAYS_CHECK` BILAN AYNAN BIR XIL.

Nusxa bo'lishining sababi `0007` dagi `tin_format` bilan bir xil: bog'liqlik
yo'nalishi. `0007` konstantani IMPORT qiladi (ya'ni yangi baza darhol yangi
ifoda bilan quriladi), bu migratsiya esa MAVJUD bazadagi eski ifodani
almashtiradi — shuning uchun bu yerda literal turishi SHART, aks holda
migratsiya o'z tarixini qayta yozardi.
"""

_OLD_CHECK = (
    "open_weekdays <@ ARRAY[1,2,3,4,5,6,7]::smallint[] "
    "AND array_length(open_weekdays,1) IS NOT NULL"
)
"""`downgrade()` uchun `0007` dagi ASL ifoda (`NULL` haqida jim)."""

_OLD_DEFAULT = "'{1,2,3,4,5,6,7}'"

_BACKFILL_NULLS = (
    "UPDATE public.market_profile "  # noqa: S608 — literal DDL, foydalanuvchi kiritmasi yo'q
    "SET open_weekdays = '{1,2,3,4,5,6,7}'::smallint[] "
    "WHERE open_weekdays IS NULL"
)
"""`downgrade()` da MAJBURIY va u ma'lumotni O'ZGARTIRADI — ochiq yoziladi.

`NULL` qatorlarni to'ldirmasdan `SET NOT NULL` qo'yish
`column "open_weekdays" of relation "market_profile" contains null values`
bilan YIQILARDI. To'ldirish esa "tanlanmagan" holatini "har kuni ochiq" ga
aylantiradi — ya'ni downgrade AYNAN shu migratsiya tuzatgan nosozlikni
qaytaradi. Bu downgrade'ning ma'nosi (eski sxemaga qaytish), lekin uni
ishlatgan odam buni BILISHI kerak.
"""


MARKET_CREATE_WITH_DEFAULT = PGFunction(
    schema="public",
    signature=MARKET_CREATE.signature,
    definition="""
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
DECLARE
  v_market_id uuid;
BEGIN
  INSERT INTO public.markets (name, timezone, is_active)
  VALUES (p_name, COALESCE(NULLIF(p_timezone, ''), 'Asia/Tashkent'), false)
  RETURNING id INTO v_market_id;

  INSERT INTO public.market_profile (
      market_id, operating_since, open_weekdays,
      address, tin, bank_account, bank_mfo, contact_phone
  )
  VALUES (
      v_market_id,
      p_operating_since,
      COALESCE(p_open_weekdays, ARRAY[1,2,3,4,5,6,7]::smallint[]),
      NULLIF(p_address, ''),
      NULLIF(p_tin, ''),
      NULLIF(p_bank_account, ''),
      NULLIF(p_bank_mfo, ''),
      NULLIF(p_contact_phone, '')
  );

  RETURN v_market_id;
END $$
""",
)
"""`0007`/`0010` davridagi `market_create()` — `COALESCE` standarti bilan.

BU YERDA, MIGRATSIYANING O'ZIDA MUZLATILGANI ATAYIN: `alembic_utils`
`PGFunction` ni MODUL ta'rifidan oladi va `migrations/entities/functions.py`
endi YANGI (standartsiz) tanani saqlaydi. `drop_entity()` faqat imzo bilan
ishlaydi, `create_entity()` esa TANANI yozadi — ya'ni bu nusxa bo'lmasa
`downgrade()` yangi tanani qaytarardi va "0010 ga qaytdim" degan da'vo
YOLG'ON bo'lardi.

`signature` `MARKET_CREATE` dan OLINADI, qayta yozilmaydi: imzo bu
migratsiyada o'zgarmaydi va uni ikkinchi marta yozish ikki nusxa
ajralib ketadigan yana bir joy bo'lardi.
"""


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. Ustun: `NOT NULL` va `server_default` — IKKALASI HAM olib
    #    tashlanadi (sabab fayl boshidagi izohda: bitta yo'l qolsa
    #    standart o'sha yo'ldan qaytardi).
    #
    #    TARTIB: CHECK'ni AVVAL yangilash SHART EMAS — eski ifoda
    #    (`open_weekdays <@ ... AND array_length(...) IS NOT NULL`) `NULL`
    #    ustida `NULL` beradi, `NULL` natijali CHECK esa Postgresda
    #    O'TADI. Ya'ni oraliq holat ham to'g'ri ishlaydi. CHECK baribir
    #    qayta yoziladi — sabab 3-banda.
    # ------------------------------------------------------------------
    op.alter_column("market_profile", "open_weekdays", nullable=True)
    op.execute("ALTER TABLE public.market_profile ALTER COLUMN open_weekdays DROP DEFAULT")

    # ------------------------------------------------------------------
    # 2. CHECK — `NULL` ni ATAYIN VA KO'RINADIGAN qilib ruxsat etadi.
    #
    #    Semantik jihatdan bu eski ifoda bilan bir xil (yuqoridagi izoh),
    #    LEKIN farq HUJJAT darajasida: eski ifodani o'qigan odam ustun
    #    hamon `NOT NULL` deb o'ylardi va `NULL` holatini "tasodifiy
    #    teshik" deb yopib qo'yardi. Yangi ifoda `NULL` ni QAROR sifatida
    #    yozadi.
    # ------------------------------------------------------------------
    _replace_check(_NEW_CHECK)

    # ------------------------------------------------------------------
    # 3. `market_create()` — `COALESCE` standartisiz qayta yaratiladi.
    #
    #    IMZO O'ZGARMAYDI, ya'ni `GRANT`/`REVOKE` ni qayta yozish KERAK
    #    EMAS: `DROP FUNCTION` grant'larni ham olib tashlaydi, lekin
    #    `CREATE` dan keyin Postgres `EXECUTE TO PUBLIC` ni standart
    #    qaytaradi — shuning uchun `REVOKE`/`GRANT` juftini QAYTA
    #    yozamiz (`0010` dagi bilan bir xil naqsh).
    # ------------------------------------------------------------------
    drop_entity(MARKET_CREATE_WITH_DEFAULT)
    create_entity(MARKET_CREATE)
    _regrant()


def downgrade() -> None:
    """Downgrade schema."""
    # Teskari tartib: funksiya -> CHECK -> ma'lumot -> ustun cheklovlari.
    drop_entity(MARKET_CREATE)
    create_entity(MARKET_CREATE_WITH_DEFAULT)
    _regrant()

    _replace_check(_OLD_CHECK)

    # ⚠ MA'LUMOT O'ZGARADI — `_BACKFILL_NULLS` docstringiga qarang.
    op.execute(_BACKFILL_NULLS)

    op.execute(
        f"ALTER TABLE public.market_profile ALTER COLUMN open_weekdays SET DEFAULT {_OLD_DEFAULT}"
    )
    op.alter_column("market_profile", "open_weekdays", nullable=False)


def _replace_check(expression: str) -> None:
    """`ck_market_profile_open_weekdays_valid` ni berilgan ifoda bilan almashtiradi.

    `op.drop_constraint` + `op.create_check_constraint` EMAS: ikkinchisi
    nom konvensiyasini (`ck_<table>_<name>`) qayta qo'llaydi va shu bilan
    nom ikki joyda — bu yerda va `models/base.py::NAMING_CONVENTION` da —
    hosil qilinardi. Xom SQL da nom AYNAN bitta konstantadan
    (`_CONSTRAINT`) keladi, ya'ni `upgrade()` va `downgrade()` bir xil
    nomga tegishi KAFOLATLANADI.
    """
    op.execute(f"ALTER TABLE public.market_profile DROP CONSTRAINT {_CONSTRAINT}")
    op.execute(
        f"ALTER TABLE public.market_profile ADD CONSTRAINT {_CONSTRAINT} CHECK ({expression})"
    )


def _regrant() -> None:
    """`market_create()` uchun `REVOKE PUBLIC` + `GRANT sbozor_app` (0007 naqshi).

    `DROP FUNCTION` grant'ni ham olib tashlaydi va `CREATE FUNCTION` dan
    keyin Postgres yangi funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi.
    Usiz bazadagi HAR QANDAY rol qoralama bozor yarata olardi — ya'ni
    `market_create()` ning butun "tor yuza" qarori (funksiya docstringi)
    jimgina bekor bo'lardi.
    """
    signature = "market_create(text, text, date, smallint[], text, text, text, text, text)"
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")
