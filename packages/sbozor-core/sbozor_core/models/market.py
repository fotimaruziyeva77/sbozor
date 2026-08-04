"""Bozor domeni: profil, zonalar, toifalar, rastalar, tariflar, sotuvchilar, kalendar.

=============================================================================
ASOSIY ARXITEKTURA QARORI — BU FAYLDA IKKI XIL TEMPORAL MODEL YASHAYDI VA
ULARNING FARQI ATAYIN:

  `tariffs`, `stall_category_periods`  ->  VORIS (successor) modeli:
                                           faqat `valid_from`; yuqori chegara
                                           SAQLANMAYDI, u keyingi qatordan
                                           hosila.

  `stall_assignments`                  ->  `daterange` + `EXCLUDE USING gist`:
                                           davr haqiqatan yopiladi va
                                           qoplanish DB darajasida taqiqlanadi.

NEGA TARIFDA `daterange` EMAS (bu fazadagi eng muhim model qarori):

  D-06 — "yangi narx = YANGI qator, eskisi O'ZGARMAYDI". `daterange` bilan
  yangi narx kiritish eski qatorning yuqori chegarasini YOPISHNI, ya'ni uni
  UPDATE qilishni talab qilardi.
  D-07 — "sanasi o'tgan tarif QULFLANADI". Ya'ni o'sha majburiy UPDATE
  aynan taqiqlangan amal bo'lib chiqadi: ikki qoida bir-birini inkor qiladi.

  Voris modelida esa narx qo'shish BITTA `INSERT` — hech qanday qatorga
  tegilmaydi, `tariff_past_immutable()` triggeri bilan hech qachon
  to'qnashmaydi va audit diff'i toza qoladi (faqat `insert` qatorlari).

NEGA BIRIKTIRISHDA `daterange` TO'G'RI:

  (a) davr HAQIQATAN yopiladi — sotuvchi ketadi va bu oddiy amal;
  (b) bo'shliq (hech kim biriktirilmagan kunlar) — XATO EMAS, D-11 ning
      "sotuvchisiz band rasta" anomaliyasi, ya'ni uzluksizlik majburlanmaydi;
  (c) o'tmishdagi davrni yopishni taqiqlaydigan D-07 kabi qoida YO'Q;
  (d) "bir vaqtda 1 rasta = 1 sotuvchi" (D-09) — bu QOPLANISH taqiqi va uni
      ilova qatlamida tekshirish parallel yozuvda ishonchsiz. `EXCLUDE USING
      gist` esa atomik.
=============================================================================

O'ZGARMAS HODISA JADVALLARIDA `TimestampMixin` ISHLATILMAYDI (`tariffs`,
`stall_category_periods`, `stall_assignments`): ularda `updated_at` bo'lishi
"bu qatorni tahrirlash mumkin" degan yolg'on va'da beradi. Ular faqat
qo'shiladi (`RefreshToken` naqshi va uning docstringidagi sabab).

CHEGARA KONVENTSIYASI: `stall_assignments.period` HAR DOIM
`sbozor_core.periods.assignment_period()` orqali quriladi (`[)`). Xom
`Range(...)` yoki `daterange(...)` yozish yo'lida boshqa joyda yozilmaydi —
RESEARCH Pitfall 10.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, DATERANGE, ExcludeConstraint, Range
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.enums import StallStatus
from sbozor_core.models.base import Base, TenantMixin, TimestampMixin, uuid_pk

__all__ = [
    "OPEN_WEEKDAYS_CHECK",
    "STALL_CODE_SORT_EXPR",
    "STALL_STATUS_CHECK",
    "STALL_STATUS_VALUES",
    "TARIFF_BUSINESS_DATE_EXPR",
    "MarketCalendarException",
    "MarketProfile",
    "Stall",
    "StallAssignment",
    "StallCategory",
    "StallCategoryPeriod",
    "StallCodeRegistry",
    "Tariff",
    "Vendor",
    "Zone",
]

STALL_STATUS_VALUES: tuple[str, ...] = tuple(status.value for status in StallStatus)


def _quoted(values: Iterable[str]) -> str:
    """SQL literal ro'yxati. Qiymatlar `StrEnum` a'zolari — tashqi kirish emas.

    `identity.py` dagi jufti bilan bir xil ikki qatorli funksiya. Umumiy
    modulga chiqarilmadi: u `models/base.py` ning ommaviy yuzasini kengaytirar
    va ikkala chaqiruvchi ham baribir o'z enum'i bilan qulflangan
    (`test_role_check_constraint_matches_enum` naqshi 02-05 da `stalls` uchun
    takrorlanadi).
    """
    return ", ".join(f"'{value}'" for value in values)


STALL_STATUS_CHECK = f"status IN ({_quoted(STALL_STATUS_VALUES)})"
"""`stalls.status` faqat ma'lum holatlardan biri bo'lishi shart.

Ifoda `sbozor_core.enums.StallStatus` dan HOSIL QILINADI, qo'lda
ko'chirilmaydi — `identity.py::ROLES_SUBSET_CHECK` bilan aynan bir xil sabab.
Enum kengayib migratsiya unutilsa, bazadagi amaldagi konstrayt enum bilan
solishtiriladi va darvoza yopiladi.
"""

OPEN_WEEKDAYS_CHECK = (
    "open_weekdays IS NULL OR ("
    "open_weekdays <@ ARRAY[1,2,3,4,5,6,7]::smallint[] "
    "AND array_length(open_weekdays,1) IS NOT NULL)"
)
"""Haftalik jadval — ISO kun raqamlari (1=dushanba … 7=yakshanba), D-17.

UCH holat va UCHALASI HAM BOSHQA-BOSHQA MA'NOGA EGA — bu farq mahsulot
qarori, texnik nuqta emas (WR-06, `0011_weekday_choice`):

  * `NULL` — **HALI TANLANMAGAN**, RUXSAT ETILADI. Bu holat ATAYIN
    mavjud: `market_create()` ish rejimini TAXMIN QILMAYDI, chunki
    taxmin qilingan jadval `calendar_configured` ni har doim rost
    qilardi va `calendar_missing` to'sig'i ustaning YAGONA yo'lida hech
    qachon ishga tushmasdi. `NULL` esa to'siqni ishga tushiradi —
    sozlanmagan bozor faollashmaydi.
  * `'{}'` (bo'sh massiv) — **RAD ETILADI**. U "bozor hech qachon
    ochilmaydi" degani: `market_is_open()` har kuni `false` beradi va
    tushum JIMGINA nolga tushadi (RESEARCH Pattern 7 ogohlantirishi).
    Ya'ni `NULL` ("hali javob yo'q") bilan `'{}'` ("javob: hech qachon")
    aralashtirilmaydi — birinchisi to'siq, ikkinchisi nosozlik.
  * to'ldirilgan massiv — `<@` bilan tekshiriladi, ya'ni 8 yoki 0 kabi
    ma'nosiz raqam o'tmaydi.

`array_length(...) IS NOT NULL` AYNAN bo'sh massivni ushlaydi: bo'sh
massiv `<@` dan bemalol o'tadi.

⚠ IFODA IKKI JOYDA — bu yerda va `migrations/versions/0007_market_domain.py`
(u shu KONSTANTANI import qiladi) hamda `0011_weekday_choice.py` (u xom
SQL bilan qayta yaratadi). Uchalasi QO'LDA sinxron saqlanadi; farq
`alembic revision --autogenerate` da EMAS, faqat ko'rikda ko'rinadi
(`tin_format` bilan bir xil holat).
"""

STALL_CODE_SORT_EXPR = r"lpad(regexp_replace(code, '\D', '', 'g'), 12, '0') || code"
"""`stalls.code_sort` — INSON-RAQAMLI tartib uchun hisoblanadigan ustun.

`code` — `text` (rasta raqami "12", "12a", "A-3" bo'lishi mumkin), ya'ni
oddiy `ORDER BY code` "1, 10, 100, 11, 2" beradi. Bu shunchaki chiroyli
emaslik emas: xarita va ro'yxat ISHLAYOTGANDEK ko'rinadi, lekin kassir
qidirayotgan rasta ko'z bilan topilmaydigan joyga tushadi (UI-SPEC §7.3).

Ifoda: kod ichidagi RAQAMLAR ajratilib 12 xonagacha nol bilan to'ldiriladi,
so'ng xom `code` qo'shiladi — shunda "12" < "12a" va raqamsiz kodlar ham
barqaror tartibda qoladi. `lpad`, `regexp_replace` va `||` ning uchalasi ham
IMMUTABLE, ya'ni generated ustunda ruxsat etiladi (`BUSINESS_DATE_EXPR`
dagi bilan bir xil talab).

O'LCHANGAN TARTIB (`postgres:18.4-trixie`, aynan shu ifoda bilan):

    kiritilgan:  2, 10, 100, 11, 12a, A-3
    natija:      2, A-3, 10, 11, 12a, 100

Ya'ni HARFLI kod O'Z RAQAMI bo'yicha joylashadi ("A-3" -> 3), oxiriga
tashlanmaydi. Bu ifodaning to'g'ridan-to'g'ri oqibati va UI uchun MUHIM:
"A-3" 3-rasta yonida turadi. Agar bozor harfli prefikslarni ALOHIDA blok
sifatida ko'rishni xohlasa, bu ifodani o'zgartirish kerak bo'ladi (ustun
generated — `ALTER TABLE ... DROP/ADD COLUMN` migratsiyasi), ilova tomonida
qayta tartiblash EMAS. Raqamsiz kodlar (masalan "A") uchun raqam qismi bo'sh
bo'ladi va ular "000000000000" bilan boshlanib eng oldinga tushadi.

Tartiblash kursori `(code_sort, id)` bo'ladi va u `ix_stalls_market_id_code_sort`
indeksidan foydalanadi (keyset — OFFSET hech qachon).
"""

TARIFF_BUSINESS_DATE_EXPR = "((created_at AT TIME ZONE 'Asia/Tashkent')::date)"
"""`tariffs.business_date` generated column ifodasi.

`migrations/helpers.py::BUSINESS_DATE_EXPR` bilan AYNAN bir xil bo'lishi
SHART. Nusxa bo'lishining sababi bog'liqlik yo'nalishi: `migrations.helpers`
`alembic.op` ni import qiladi, `sbozor_core` esa migratsiya vositalariga
bog'lanmaydi (u uchala servisda ishlaydi). `models/ops.py::
AUDIT_BUSINESS_DATE_EXPR` bilan bir xil naqsh.

02-05 MIGRATSIYASIGA TOPSHIRIQ: DDL tomonida ifodani QAYTA YOZMANG —
`migrations.helpers.BUSINESS_DATE_EXPR` ni import qiling. Shunda uchinchi
nusxa paydo bo'lmaydi.

IKKI ARGUMENTLI `AT TIME ZONE` shakli MAJBURIY: u IMMUTABLE, bitta
argumentli varianti esa STABLE va generated column'da umuman ruxsat
etilmaydi.
"""


class MarketProfile(Base, TenantMixin, TimestampMixin):
    """Bozorning rekvizitlari va HAFTALIK ish jadvali — bozorga BITTA qator.

    `markets` jadvalidan ATAYIN alohida: `markets` — tenant chegarasining
    o'zi (`id` bo'yicha policy, `SECURITY DEFINER` orqali yoziladi), bu esa
    oddiy tenant jadvali. Rekvizitlarni `markets` ga qo'shish har bir
    rekvizit tahririni `SECURITY DEFINER` yuzasidan o'tkazishga majburlardi.

    QATOR BOZOR BILAN BIR TRANZAKSIYADA TUG'ILADI (`market_create()`).
    Sababi jiddiy: `market_is_open()` fail-closed — profil qatori bo'lmasa u
    HAR KUNI `false` qaytaradi, ya'ni bozor hech qachon ishlamaydi va tushum
    jimgina nolga tushadi (RESEARCH Pattern 7).
    """

    __tablename__ = "market_profile"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_market_profile_market_id_markets"
        ),
        # Bozorga AYNAN bitta profil. Ikkinchi qator paydo bo'lsa
        # `market_is_open()` dagi skalyar subquery "more than one row
        # returned" bilan yiqilardi — ya'ni bu unikalik funksiyaning ishlash
        # sharti, shunchaki tozalik emas.
        UniqueConstraint("market_id", name="uq_market_profile_market_id"),
        UniqueConstraint("market_id", "id", name="uq_market_profile_market_id_id"),
        CheckConstraint(OPEN_WEEKDAYS_CHECK, name="open_weekdays_valid"),
        # A2 TAXMINI (RESEARCH Assumptions Log): STIR — 9 raqam. Rasmiy
        # me'yoriy hujjat bevosita o'qilmagan, manba — gov.uz qidiruv
        # natijalari. Phase 0 ning buyurtmachi savollari bilan tasdiqlanadi;
        # noto'g'ri bo'lsa bu bitta `ALTER ... DROP CONSTRAINT` migratsiyasi.
        CheckConstraint("tin IS NULL OR tin ~ '^[0-9]{9}$'", name="tin_format"),
    )

    id: Mapped[UUID] = uuid_pk()
    # A3 TAXMINI: bozorning TIZIMDAGI ish boshlash sanasi. Barcha BOSHLANG'ICH
    # `valid_from` (birinchi tarif va birinchi toifa davri) AYNAN shu sanadan
    # olinadi. Import kuni qo'yilsa, 6-faza undan oldingi har bir kunni
    # "tarifsiz" deb topadi va butun tarixni anomaliyaga aylantiradi.
    # Shuning uchun ustun `NOT NULL` — "keyin to'ldiramiz" holati yo'q.
    operating_since: Mapped[date] = mapped_column(Date(), nullable=False)
    # D-17: haftalik jadval FAQAT bozor darajasida (zona/rasta darajasida
    # emas). ISO kun raqamlari — `EXTRACT(ISODOW FROM ...)` bilan bir xil
    # asosda, ya'ni `market_is_open()` da konversiya kerak emas.
    #
    # ⚠ `nullable=True` va `server_default` YO'Q — IKKALASI HAM ATAYIN
    # (WR-06, `0011_weekday_choice`). Standart qiymat IKKI yo'ldan
    # kelardi: `market_create()` ichidagi `COALESCE` va ustunning
    # `server_default` i. Ikkalasi ham olib tashlandi, chunki bittasini
    # qoldirish "ustun sanab o'tilmagan har qanday INSERT" (seed,
    # fixture, kelajakdagi kod) uchun teshik qoldirardi va
    # `calendar_missing` to'sig'i o'sha yo'lda yana ishlamay qolardi.
    # `NULL` = "hali tanlanmagan" (ma'nosi `OPEN_WEEKDAYS_CHECK` da).
    open_weekdays: Mapped[list[int] | None] = mapped_column(
        ARRAY(SmallInteger()),
        nullable=True,
    )
    address: Mapped[str | None] = mapped_column(Text(), nullable=True)
    tin: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # A1 TAXMINI: bank rekvizitlari MVP'da hisobot sarlavhasi uchun. Ular
    # `tin` dan farqli o'laroq DB darajasida FORMATLANMAYDI — A1 buyurtmachi
    # bilan tasdiqlanmagan va noto'g'ri qat'iy format haqiqiy rekvizitni rad
    # etardi. Chegara validatsiyasi zod/pydantic tomonida (RESEARCH Code
    # Example 5); tasdiqdan keyin CHECK qo'shish oson.
    bank_account: Mapped[str | None] = mapped_column(Text(), nullable=True)
    bank_mfo: Mapped[str | None] = mapped_column(Text(), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # ===================================================================
    # 4-FAZA: YOPIQ KUNLARDA HAM KADR OLINADIMI (D-10, `0014_snapshot_domain`)
    # ===================================================================
    #
    # STANDART `true` va bu ATAYIN, «e'tiborsizlikdan» emas: YOPIQ deb
    # e'lon qilingan kunda ko'ringan BAND RASTA — aynan mahsulot izlaydigan
    # anomaliya («ro'yxatga olinmagan savdo», BILL-04 ning qo'shnisi).
    # Yopiq kunda kadr olishni to'xtatish o'sha anomaliyani KO'RINMAS
    # qilardi. Narxi kichik: yiliga ~15 bayram kuni × 175 kadr ≈ 2 600 kadr.
    #
    # ⚠ BAYROQ KADR OLISHNI boshqaradi, BILLINGNI EMAS. Yopiq kunning
    #   `capture_runs` qatorlari `is_market_open = false` bilan tug'iladi
    #   (`market_is_open()` dan) va 6-faza ularni HISOBDAN chiqaradi,
    #   HISOBOTDAN esa chiqarmaydi. Ikkalasini aralashtirish yopiq kundagi
    #   dalilni ham yo'qotardi.
    #
    # ⚠ UI'DA TAHRIRLANMAYDI (`04-UI-SPEC.md` §16): D-10 uni `true` qilib
    #   qulflagan va jadval sahifasida faqat O'QISH uchun qatori bor. Bitta
    #   checkbox uchun boshqa fazaning sozlamalar yuzasini ochish — noto'g'ri
    #   egalik; qiymat kerak bo'lsa `UPDATE` bilan o'zgaradi.
    capture_on_closed_days: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )


class Zone(Base, TenantMixin, TimestampMixin):
    """Bozor zonasi — YASSI ro'yxat, ierarxiya YO'Q (D-03).

    Zona kaliti rasta RAQAMIGA kirmaydi (D-01: raqam bozor bo'yicha yagona),
    ya'ni rastani boshqa zonaga ko'chirish uning raqamini o'zgartirmaydi va
    tarixni buzmaydi.
    """

    __tablename__ = "zones"
    __table_args__ = (
        ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_zones_market_id_markets"),
        UniqueConstraint("market_id", "name", name="uq_zones_market_id_name"),
        UniqueConstraint("market_id", "id", name="uq_zones_market_id_id"),
        # Import rastalarni zonaga NOM bo'yicha bog'laydi (D-14 validatsiyasi).
        # Bo'sh yoki faqat bo'shliqdan iborat nom hech qachon mos kelmaydi va
        # jimgina "fantom" zona yaratardi.
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text(), nullable=False)


class StallCategory(Base, TenantMixin, TimestampMixin):
    """Mahsulot toifasi — tarif kalitining O'ZI (D-05).

    Rasta bilan bog'lanish TO'G'RIDAN-TO'G'RI EMAS: `stalls.category_id`
    ustuni ATAYIN YO'Q (D-04). Toifa sanadan kuchga kiradi va tarixi
    `stall_category_periods` da yashaydi — aks holda toifani o'zgartirish
    O'TMISHDAGI hisobni ham qayta yozardi.
    """

    __tablename__ = "stall_categories"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_categories_market_id_markets"
        ),
        UniqueConstraint("market_id", "name", name="uq_stall_categories_market_id_name"),
        UniqueConstraint("market_id", "id", name="uq_stall_categories_market_id_id"),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text(), nullable=False)


class Stall(Base, TenantMixin, TimestampMixin):
    """Rasta — "band, lekin to'lovsiz" da'vosining tayanch obyekti.

    `category_id` ustuni ATAYIN YO'Q (D-04) — joriy toifa
    `stall_category_periods` dan `valid_from <= :d` bo'yicha oxirgi qator
    sifatida olinadi.
    """

    __tablename__ = "stalls"
    __table_args__ = (
        ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_stalls_market_id_markets"),
        # D-03: zona MAJBURIY (`zone_id` `NOT NULL`) va composite FK orqali —
        # A bozoridagi rasta B bozorining zonasiga havola qila olmaydi
        # (T-01-26: bu RLS emas, SXEMA darajasidagi kafolat).
        ForeignKeyConstraint(
            ["market_id", "zone_id"],
            ["zones.market_id", "zones.id"],
            name="fk_stalls_market_id_zone_id_zones",
        ),
        # D-01: raqam BOZOR bo'yicha yagona (zona bo'yicha emas).
        UniqueConstraint("market_id", "code", name="uq_stalls_market_id_code"),
        UniqueConstraint("market_id", "id", name="uq_stalls_market_id_id"),
        CheckConstraint(STALL_STATUS_CHECK, name="status_allowed"),
        CheckConstraint("length(btrim(code)) > 0", name="code_not_blank"),
        # Keyset kursori `(code_sort, id)` shu indeksdan foydalanadi.
        # Tenant invarianti #5 bo'yicha `market_id` bilan BOSHLANADI.
        Index("ix_stalls_market_id_code_sort", "market_id", "code_sort"),
    )

    id: Mapped[UUID] = uuid_pk()
    zone_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(Text(), nullable=False)
    # DB hisoblaydi — ilova tartiblash kalitini QURMAYDI. Ikkinchi haqiqat
    # manbai bo'lganda ro'yxat va xarita boshqa-boshqa tartibda chiqardi.
    code_sort: Mapped[str] = mapped_column(
        Text(),
        Computed(STALL_CODE_SORT_EXPR, persisted=True),
        nullable=False,
    )
    # `sbozor_core.enums.StallStatus`. A4: `closed`/`maintenance` rastalarga
    # 6-fazada hisob YOZILMAYDI — bu holat qiymatlarining MAZMUNI.
    status: Mapped[str] = mapped_column(Text(), nullable=False, server_default=text("'active'"))
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)


class StallCodeRegistry(Base, TenantMixin):
    """Bozorda BIR MARTA ishlatilgan rasta raqamlari — D-02 ning DB kafolati.

    `UNIQUE(market_id, code)` YETARLI EMAS: rasta kodi tahrirlangach eski kod
    bo'shab qoladi va boshqa rastaga berilishi mumkin bo'lib qolardi. U holda
    hisobotdagi "12-rasta" yillar davomida ikki xil jismoniy joyni
    anglatardi. Bu reyestr kodni rastaga BIR MARTA biriktiradi va
    `stall_code_claim()` triggeri uni majburlaydi. Eski rastaning O'Z kodini
    qaytarib olishi (tuzatishni bekor qilish) ruxsat etiladi.

    `id uuid` USTUNI YO'Q va bu ataylab — birlamchi kalit `(market_id, code)`
    ning o'zi. Oqibati hujjatlashtirilgan: jadval
    `sbozor_core.schema_contract.AUDITED_TABLES` ga KIRMAYDI, chunki
    `fn_audit_row()` `row_id` ni `uuid` ga keltiradi va bunday jadvalda har
    DML da yiqilardi. Audit izi baribir yo'qolmaydi — kod o'zgarishi `stalls`
    qatorining auditida ko'rinadi.

    `TimestampMixin` ham YO'Q: qator o'zgarmas — u faqat qo'shiladi.
    `first_seen` ATAYIN `created_at` deb atalmagan, chunki u qatorning emas,
    KODNING bozorda birinchi ko'rilgan paytini bildiradi.
    """

    __tablename__ = "stall_code_registry"
    __table_args__ = (
        PrimaryKeyConstraint("market_id", "code", name="pk_stall_code_registry"),
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_code_registry_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_stall_code_registry_market_id_stall_id_stalls",
        ),
    )

    code: Mapped[str] = mapped_column(Text(), nullable=False)
    stall_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StallCategoryPeriod(Base, TenantMixin):
    """Rastaning toifa tarixi — VORIS modeli (D-04), tarif bilan bir xil mexanizm.

    Yuqori chegara ustuni YO'Q (Pitfall 9): "bu toifa qachongacha amal
    qilgan" savoli keyingi qatordan hosila va so'rovda `LEAD(valid_from)`
    bilan hisoblanadi.

    `TimestampMixin` ATAYIN YO'Q: qator o'zgarmas hodisa yozuvi. Uni
    tahrirlash o'tmishdagi hisobni boshqa tarifga surib yuborardi, shuning
    uchun o'tgan sanali qatorlarni `category_period_past_immutable()`
    triggeri qulflaydi.

    KONSTRAYT NOMLARI `stall_category_periods` PREFIKSI BILAN: to'liq
    konvensiya nomi (`fk_stall_category_periods_market_id_category_id_
    stall_categories`) 64 bayt bo'lib Postgres'ning 63 baytlik chegarasidan
    oshadi va JIMGINA kesiladi — kesilgan nom modeldagi nom bilan mos
    kelmay, autogenerate uni har safar "o'zgargan" deb ko'rsatardi. Shuning
    uchun toifa FK'sining NOMIDA `market_id` segmenti yo'q; konstraytning
    O'ZI baribir composite.
    """

    __tablename__ = "stall_category_periods"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_category_periods_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_stall_category_periods_market_id_stall_id_stalls",
        ),
        ForeignKeyConstraint(
            ["market_id", "category_id"],
            ["stall_categories.market_id", "stall_categories.id"],
            name="fk_stall_category_periods_category_id_stall_categories",
        ),
        # Bir rastaga bir kunda IKKITA toifa berib bo'lmaydi. Bu ayni paytda
        # "D sanadagi toifa" so'rovining indeksi ham (`valid_from <= :d`
        # bo'yicha teskari Index Scan).
        UniqueConstraint(
            "market_id",
            "stall_id",
            "valid_from",
            name="uq_stall_category_periods_market_id_stall_id_valid_from",
        ),
        UniqueConstraint("market_id", "id", name="uq_stall_category_periods_market_id_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    stall_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    category_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # A3: BIRINCHI qatorning `valid_from` i `market_profile.operating_since`
    # dan olinadi — import kuni EMAS.
    valid_from: Mapped[date] = mapped_column(Date(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Tariff(Base, TenantMixin):
    """Toifa narxi tarixi — VORIS modeli (D-05/D-06/D-07).

    KALIT AYNAN `(market_id, category_id, valid_from)` (D-05): zona, rasta
    o'lchami, hafta kuni yoki mavsum bo'yicha farq YO'Q va bunday ustun
    QO'SHILMAYDI. Yangi kesim kerak bo'lsa u yangi TOIFA sifatida
    ifodalanadi — shunda 6-fazadagi narx qidiruvi bitta shaklda qoladi.

    `valid_to` USTUNI YO'Q (Pitfall 9) — u ikkinchi haqiqat manbai bo'lardi
    va keyingi qatorning `valid_from` i bilan ajralib ketardi. Ko'rsatish
    uchun `LEAD(valid_from) OVER (PARTITION BY market_id, category_id
    ORDER BY valid_from)` ishlatiladi.

    ⚠ `migrations.helpers.financial_guards()` BU JADVALGA CHAQIRILMAYDI. U
    `UNIQUE(market_id, category_id, business_date)` beradi, ya'ni bir kunda
    ikkita KELAJAK tarifini kiritishni bloklardi (masalan sentabr va oktabr
    narxlarini bugun kiritish). Uchala qo'riqchi shu yerda QO'LDA:
    `business_date` Computed ustuni, `CHECK (amount_soum > 0)` va
    `UNIQUE(market_id, category_id, valid_from)`. Jadval baribir
    `FINANCIAL_TABLES` da qoladi — unda haqiqiy pul ustuni bor.
    """

    __tablename__ = "tariffs"
    __table_args__ = (
        ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_tariffs_market_id_markets"),
        ForeignKeyConstraint(
            ["market_id", "category_id"],
            ["stall_categories.market_id", "stall_categories.id"],
            name="fk_tariffs_market_id_category_id_stall_categories",
        ),
        # D-06: bir toifaga bir sanada BITTA narx. Takroriy kiritish 409
        # bo'ladi, eski qator esa hech qachon o'zgarmaydi.
        UniqueConstraint(
            "market_id",
            "category_id",
            "valid_from",
            name="uq_tariffs_market_id_category_id_valid_from",
        ),
        UniqueConstraint("market_id", "id", name="uq_tariffs_market_id_id"),
        # Pul — `bigint` so'm; `float` TAQIQLANGAN. Nol yoki manfiy narx
        # "bepul rasta" ni ifodalamaydi — u hisobni jimgina yo'qotadi.
        CheckConstraint("amount_soum > 0", name="amount_soum_positive"),
    )

    id: Mapped[UUID] = uuid_pk()
    category_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    amount_soum: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    # BIZNES sanasi — narx QACHONDAN amal qiladi. `created_at` (qator qachon
    # yozilgan) bilan chalkashtirilmaydi: kelajakdagi narx bugun kiritiladi.
    valid_from: Mapped[date] = mapped_column(Date(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Qator QAYSI BIZNES-KUNDA kiritilgani (auditga va idempotentlikka).
    # `valid_from` bilan aralashtirilmaydi — bu ikki xil savol.
    business_date: Mapped[date] = mapped_column(
        Date(),
        Computed(TARIFF_BUSINESS_DATE_EXPR, persisted=True),
        nullable=False,
    )


class Vendor(Base, TenantMixin, TimestampMixin):
    """Sotuvchi — SHAXSIY MA'LUMOT (F.I.Sh. + telefon), D-09 bo'yicha O'QISH ham auditda.

    D-12: telefon MAJBURIY va BOZOR ICHIDA unique. Bozorlararo unique EMAS —
    bir odam ikki bozorda savdo qilishi mumkin va MVP uni ikki alohida
    sotuvchi qatori sifatida ko'radi (yagona shaxs sifatida birlashtirish v2
    ehtiyoji).

    Telefon FORMATI DB'da tekshirilmaydi: normalizatsiya chegarada
    (`sbozor_core.phone.normalize_phone`) bajariladi — `users.phone_e164`
    bilan aynan bir xil qaror. Ikki joyda tekshirish formatni ikki marta
    ta'riflardi va ular ajralib ketardi.
    """

    __tablename__ = "vendors"
    __table_args__ = (
        ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_vendors_market_id_markets"),
        UniqueConstraint("market_id", "phone_e164", name="uq_vendors_market_id_phone_e164"),
        UniqueConstraint("market_id", "id", name="uq_vendors_market_id_id"),
        # Qarzdorlik reestrida ismsiz qator "kimdan undirish kerak?"
        # savoliga javob bermaydi — ya'ni mahsulotning asosiy hujjati
        # foydasiz bo'lib qoladi.
        CheckConstraint("length(btrim(full_name)) > 0", name="full_name_not_blank"),
    )

    id: Mapped[UUID] = uuid_pk()
    full_name: Mapped[str] = mapped_column(Text(), nullable=False)
    phone_e164: Mapped[str] = mapped_column(Text(), nullable=False)


class StallAssignment(Base, TenantMixin):
    """Rasta ↔ sotuvchi biriktirish DAVRI (D-09/D-10/D-11).

    PUL USTUNI YO'Q va BO'LMAYDI (D-10): qarz `daily_charges` da tug'iladi
    va ESKI sotuvchida qoladi. Shuning uchun jadval `FINANCIAL_TABLES` dan
    ataylab chiqarilgan (02-01) — meta-test undan `CHECK (amount_soum > 0)`
    talab qilardi va yagona "tuzatish" yo'li soxta pul ustuni qo'shish
    bo'lardi.

    `TimestampMixin` YO'Q: davr yopilishi `period` ning yuqori chegarasi
    bilan ifodalanadi, `updated_at` bilan emas.

    ⚠ ALEMBIC `ExcludeConstraint` NI AVTOGENERATSIYA QILMAYDI va uning
    YO'QOLGANINI HAM SEZMAYDI (empirik). Ya'ni bu e'lon migratsiyaga
    O'ZI ko'chmaydi: u 02-06 da ANIQ yoziladi va mavjudligi meta-test bilan
    qulflanadi. `btree_gist` kengaytmasi ham shart (`market_id`/`stall_id`
    tenglik operatorlari GiST da shu kengaytmadan keladi) — migratsiya
    `require_extension("btree_gist")` bilan boshlanadi.
    """

    __tablename__ = "stall_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_assignments_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_stall_assignments_market_id_stall_id_stalls",
        ),
        ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_stall_assignments_market_id_vendor_id_vendors",
        ),
        UniqueConstraint("market_id", "id", name="uq_stall_assignments_market_id_id"),
        # D-09: bir vaqtda 1 rasta = 1 sotuvchi. Ilova qatlamidagi "avval
        # tekshir, keyin yoz" ikki parallel so'rovda ikkalasini ham
        # o'tkazib yuborardi; `EXCLUDE` esa atomik va xom SQL yo'lini ham
        # qamraydi. Buzilganda SQLSTATE `23P01` (exclusion_violation).
        ExcludeConstraint(
            ("market_id", "="),
            ("stall_id", "="),
            ("period", "&&"),
            name="ex_stall_assignments_no_overlap",
            using="gist",
        ),
        # Quyi chegarasiz davr "abadiy o'tmishdan beri biriktirilgan" degani
        # bo'lardi va har qanday tarixiy hisobga kirib qolardi.
        CheckConstraint("lower(period) IS NOT NULL", name="lower_bound_required"),
        # "Shu sotuvchining rastalari" — qarzdorlik reestri va sotuvchi
        # kartochkasining asosiy so'rovi.
        Index("ix_stall_assignments_market_id_vendor_id", "market_id", "vendor_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    stall_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    vendor_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # HAR DOIM `sbozor_core.periods.assignment_period()` bilan quriladi.
    # Xom `Range(...)` yozilsa chegara konventsiyasi (`[)`) ikkinchi manbaga
    # ega bo'ladi va almashinuv kunidagi patta ikki sotuvchiga yozilardi.
    period: Mapped[Range[date]] = mapped_column(DATERANGE(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MarketCalendarException(Base, TenantMixin, TimestampMixin):
    """Haftalik jadvaldan chiqadigan ALOHIDA kunlar (D-18) — FAQAT bozor darajasida.

    `is_open` ikki tomonlama: `false` — bayram/yopiq kun, `true` — haftalik
    jadvalda dam olish bo'lgan, lekin ISHLAYDIGAN kun. Bitta jadval ikkala
    holatni ham ifodalaydi, chunki `market_is_open()` da istisno HAR DOIM
    haftalik jadvaldan ustun turadi (birinchi `COALESCE` argumenti).

    Zona yoki rasta darajasidagi istisno MVP'da YO'Q (D-18): u kunlik
    hisobni har bir rasta uchun alohida shartga bog'lardi va 6-fazadagi
    yagona `WHERE market_is_open(...)` kontrakti buzilardi.
    """

    __tablename__ = "market_calendar_exceptions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_market_calendar_exceptions_market_id_markets",
        ),
        # Bir kunga ikkita istisno bo'lsa `market_is_open()` dagi skalyar
        # subquery yiqilardi — bu unikalik funksiyaning ishlash sharti.
        UniqueConstraint(
            "market_id",
            "exception_date",
            name="uq_market_calendar_exceptions_market_id_exception_date",
        ),
        UniqueConstraint("market_id", "id", name="uq_market_calendar_exceptions_market_id_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    exception_date: Mapped[date] = mapped_column(Date(), nullable=False)
    is_open: Mapped[bool] = mapped_column(nullable=False)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
