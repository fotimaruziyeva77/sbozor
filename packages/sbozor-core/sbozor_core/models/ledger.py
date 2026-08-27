"""Qog'oz daftar reyestri — SC#5 ning UCH TOMONLAMA SOLISHTIRUVIDAGI MANBA.

=============================================================================
BU JADVALDA QOTIB QOLADIGAN UCH QAROR (D-17/D-21/R-4):

1. ⛔⛔ `ledger_entries` MOLIYAVIY JADVAL EMAS — U TASHQI QOG'OZ MANBANING
   NUSXASI.

   Shuning uchun `financial_guards()` CHAQIRILMAYDI va nom
   `sbozor_core.schema_contract.FINANCIAL_TABLES` ga QO'SHILMAYDI.

   Sabab MEXANIK, uslubiy emas: `financial_guards()` chiqaradigan DDL
   `CHECK (amount_soum > 0)` ni talab qiladi, daftar esa `0` summani ham
   yozishi mumkin va bu QONUNIY holat — «bu rastadan bugun hech nima
   yig'ilmadi» degan yozuv AYNAN nomuvofiqlikning dalili va u
   solishtiruvdan CHIQARIB TASHLANMASLIGI kerak. Cheklov qo'yilsa
   importer o'sha qatorni jimgina tashlab ketardi va SC#5 ning eng
   muhim holati («daftarda 0, tizimda band») KO'RINMAS bo'lardi.

   ⚠ BU IZOHSIZ KEYINGI IJROCHI JADVALNI REYESTRGA QO'SHISHGA URINARDI:
   unda `amount_soum` nomli ustun bor, ya'ni u «pul jadvali» bo'lib
   KO'RINADI. `test_financial_tables_have_guards` esa undan `business_date`
   generated ustunini va `CHECK (amount_soum > 0)` ni talab qilardi —
   ya'ni reyestr sxemani NOTO'G'RI shaklga majburlagan bo'lardi
   (`stall_assignments` / `cashier_shifts` bilan AYNAN bir xil tuzoq:
   2-faza Pitfall 3 va 6-faza).

2. ⛔ TAKRORIY IMPORT ALMASHTIRADI — `ON CONFLICT DO UPDATE`,
   `DO NOTHING` EMAS.

   Daftar KUN ICHIDA tuzatiladi (kassir xato yozdi, keyin to'g'riladi) va
   ikkinchi fayl birinchisini ALMASHTIRISHI kerak. `DO NOTHING` birinchi
   (xato) qiymatni MUZLATIB qo'yardi va tuzatilgan daftar tizimga umuman
   yetib bormasdi.

   Bu `daily_charges` ning o'zgarmaslik qoidasini BUZMAYDI va sabab
   yuqoridagi 1-bandda: bu jadval hisob EMAS, tashqi manbaning nusxasi.
   Hisob qatori o'zgarmas bo'lib qolaveradi.

   Idempotentlikning O'ZI esa DB KAFOLATI, ilova intizomi emas:
   `UNIQUE (market_id, business_date, stall_id)`. Ilova qatlamidagi
   «avval tekshir, keyin yoz» ikki parallel import yugurishida IKKITA
   qator yozardi (D-21 ning `notification_outbox` dagi bilan aynan bir
   sinf).

3. ⛔ YANGI `SECURITY DEFINER` FUNKSIYA QO'SHILMAYDI (D-21, T-06-22 /
   G7-7). `0024` DEFINER yuzasini KENGAYTIRMAYDI: `market_delete_draft(uuid)`
   ning faqat TANASI kengayadi, IMZOSI o'zgarmaydi va yangi funksiya
   umuman tug'ilmaydi. `DEFINER_SURFACES` BO'SH qolishi SHART
   (`0023_notification_domain.py:65-69` bandining so'zma-so'z takrori).
=============================================================================

⚠ PUL — `BIGINT` SO'M ↔ Python `int`. Kasrli tip HECH QAYERDA: yaxlitlanish
drifti aynan mahsulot bartaraf etadigan nizoni tug'diradi va u HECH QANDAY
xato bermasdan yig'iladi.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import BigInteger, Date, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.models.base import Base, TenantMixin, TimestampMixin, uuid_pk

__all__ = ["LEDGER_DAY_STALL_UNIQUE", "LedgerEntry"]

LEDGER_DAY_STALL_UNIQUE = "uq_ledger_entries_market_day_stall"
"""⛔ TAKRORIY IMPORTNI IDEMPOTENT QILADIGAN KAFOLAT (modul docstringi, 2-band).

Nom MODELDA e'lon qilinadi va migratsiya uni SHU YERDAN import qiladi —
`0023` ning indeks nomlari bilan AYNAN bir xil sabab (OP-10): nom ikki
joyda literal yozilsa ular ajralib ketishi mumkin va `downgrade()` boshqa
nomni qidirardi.
"""


class LedgerEntry(Base, TenantMixin, TimestampMixin):
    """Qog'oz daftarning BIR KUN × BIR RASTA yozuvi (SC#5, D-17).

    Bu qator TIZIM hisobi EMAS — u bozor ma'muriyati yuritadigan QOG'OZ
    daftardan import qilingan NUSXA. Uch tomonlama solishtiruv (08-16)
    aynan shu ustunni `daily_charges` (tizim hisobi) va `payments`
    (kassir qayd etgan to'lov) bilan yonma-yon qo'yadi — «daftarda bor,
    tizimda yo'q» va teskarisi shu yerdan ko'rinadi.

    ⛔ `imported_by` GA `users.id` FK QO'YILMAYDI va bu ATAYIN: `users`
    GLOBAL jadval (`schema_contract.GLOBAL_TABLES`), unda `market_id`
    ustuni YO'Q, ya'ni bu jadvalning KOMPOZIT tenant FK naqshi
    (`(market_id, <parent_id>)`) u yerga BORMAYDI. Yagona ustunli FK esa
    begona bozor xodimini biriktirishni TO'XTATA OLMASDI — ya'ni u
    kafolat emas, kafolat KO'RINISHI bo'lardi. Tekshiruv ilova
    qatlamida. `reconciliation_cases.assignee_user_id` (0023) bilan
    AYNAN bir xil qaror va aynan bir xil sabab.

    ⚠ `business_date` — DOMEN sanasi, `created_at` dan HOSILA EMAS. U
    daftarning O'ZIDA yozilgan kunni bildiradi: import kechikib, ertasi
    kuni bajarilishi mumkin va o'shanda hosila ustun qatorni NOTO'G'RI
    kunga tushirardi. `daily_charges.service_date` (C-2) bilan bir
    oilada — u yerda ham domen sanasi va audit sanasi ATAYIN ajratilgan.
    """

    __tablename__ = "ledger_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_ledger_entries_market_id_markets"
        ),
        # ⛔ KOMPOZIT — `market_id` BILAN: A bozorining daftar qatori B
        #   bozorining rastasiga havola qila OLMAYDI. Bu RLS emas, SXEMA
        #   darajasidagi kafolat va u RLS kontekst o'rnatilmay qolgan
        #   holatda ham kuchda qoladi (T-08-04).
        ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_ledger_entries_stall",
        ),
        # KOMPOZIT FK NISHONI — keyingi fazalar bu jadvalga
        # `(market_id, id)` bilan tayanishi mumkin (`0023` naqshi).
        UniqueConstraint("market_id", "id", name="uq_ledger_entries_market_id_id"),
        # ⛔⛔ IDEMPOTENTLIK KAFOLATI — modul docstringining 2-bandi.
        UniqueConstraint("market_id", "business_date", "stall_id", name=LEDGER_DAY_STALL_UNIQUE),
    )

    id: Mapped[UUID] = uuid_pk()
    # DOMEN sanasi — klass docstringi.
    business_date: Mapped[date] = mapped_column(Date(), nullable=False)
    stall_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # ⚠ `BIGINT` so'm ↔ `int`. ⛔ `CHECK (amount_soum > 0)` ATAYIN YO'Q —
    #   `0` QONUNIY qiymat va u SC#5 ning eng muhim holati (modul
    #   docstringining 1-bandi).
    amount_soum: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    # ⛔ `users.id` GA FK YO'Q — klass docstringi.
    imported_by: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
