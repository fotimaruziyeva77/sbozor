"""Operatsion jadvallar: `audit_log` (FOUND-03) va `system_heartbeats` (FOUND-06).

=============================================================================
`audit_log` APPEND-ONLY. Bu ORM konvensiyasi emas, DB darajasidagi kafolat.

Bu modeldan ORM orqali `session.delete()` chaqirish yoki maydonini
o'zgartirib `flush()` qilish HECH QACHON ishlatilmaydi — va agar kimdir
ishlatsa, u ishlamaydi ham: `migrations/versions/0002_audit.py` to'rt
qatlamli qulf o'rnatadi (huquqlar, RLS policy'lari, `BEFORE UPDATE OR
DELETE` triggeri va `BEFORE TRUNCATE` triggeri). Model bu yerda faqat
O'QISH va Alembic autogenerate pariteti uchun.

Yozuvning ODATIY yo'li ham ORM emas: moliyaviy va huquq-o'zgartiruvchi
jadvallarda qatorni `fn_audit_row()` DB-triggeri qo'yadi (D-10), ya'ni xom
SQL bilan qilingan o'zgarish ham audit qoldiradi. ORM orqali yoziladigan
yagona holat — DB o'zgarishi BO'LMAGAN hodisalar (`login`, `logout`,
`read`), ular `source='app'` bilan ketadi.
=============================================================================
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Computed,
    Date,
    DateTime,
    Identity,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.models.base import Base

__all__ = ["AUDIT_BUSINESS_DATE_EXPR", "AuditLog", "SystemHeartbeat"]

AUDIT_BUSINESS_DATE_EXPR = "((at AT TIME ZONE 'Asia/Tashkent')::date)"
"""`audit_log.business_date` generated column ifodasi.

Moliyaviy jadvallardagi (`migrations.helpers.BUSINESS_DATE_EXPR`) bilan bir
xil MANTIQ, lekin boshqa ustun ustida (`at`, `created_at` emas) — shuning
uchun umumiy konstantaga birlashtirilmagan. Ikki argumentli `AT TIME ZONE`
shakli MAJBURIY: u IMMUTABLE, bitta argumentli varianti esa STABLE va
generated column'da umuman ruxsat etilmaydi.
"""


class AuditLog(Base):
    """Kim / qachon / nima / eski -> yangi (FOUND-03, D-09, D-10).

    `TimestampMixin` ATAYIN ISHLATILMAGAN: unda `updated_at` bor, bu jadvalda
    esa yangilanish tushunchasining O'ZI yo'q. Vaqt ustuni ham `created_at`
    emas, `at` deb ataladi — hodisa sodir bo'lgan payt.

    `TenantMixin` ham ISHLATILMAGAN: undagi `market_id` `NOT NULL`, bu yerda
    esa u NULL bo'lishi mumkin — platforma darajasidagi harakatlar (bozor
    yaratish, platforma admini o'zgartirishlari) hech qaysi bozorga
    tegishli emas. Jadval shunga qaramay tenant-scoped hisoblanadi:
    `market_id` ustuni bor, RLS ENABLE+FORCE qilingan va o'qish policy'si
    tenant predikatiga bo'ysunadi, ya'ni
    `tests/tenancy/test_meta.py::test_every_table_is_tenant_scoped`
    darvozasidan istisnosiz o'tadi.

    `market_id` da FOREIGN KEY ATAYIN YO'Q. Ikki sabab:
      1. Audit yozuvi u tasvirlagan qatordan (va hatto bozordan) UZOQ
         yashashi kerak — `ON DELETE CASCADE` audit izini o'chirar edi,
         `RESTRICT` esa bozorni o'chirishni umuman imkonsiz qilardi.
      2. DELETE audit qatori aynan o'chirilayotgan qator bilan bir
         tranzaksiyada yoziladi; FK bu yerda tartib bo'yicha nozik va
         hech qanday himoya bermaydi.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        # "Bu bozorda oxirgi nima bo'ldi" — audit ekranining asosiy so'rovi.
        Index("ix_audit_log_market_id_at", "market_id", text("at DESC")),
        # "Bu qator bilan nima bo'lgan" — bitta rasta/hisob tarixi.
        Index("ix_audit_log_market_id_table_name_row_id", "market_id", "table_name", "row_id"),
        # "Bu xodim nima qildi" — nizo tekshiruvining asosiy kesimi.
        Index(
            "ix_audit_log_market_id_actor_user_id_at",
            "market_id",
            "actor_user_id",
            text("at DESC"),
        ),
    )

    # `uuidv7()` EMAS: audit qatorlari faqat ketma-ket qo'shiladi va hech
    # qachon tashqaridan ID bo'yicha izlanmaydi, shuning uchun `bigint`
    # identity ham arzonroq, ham "nechta yozuv bor" savoliga to'g'ridan-to'g'ri
    # javob beradi. `ALWAYS` — ilova ID o'ylab topa olmaydi.
    id: Mapped[int] = mapped_column(BigInteger(), Identity(always=True), primary_key=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # DB tomonda hisoblanadi va hech qachon drift qilmaydi. Hisobot filtri
    # `WHERE business_date = ...` bo'lib qoladi, ya'ni ilova mintaqa
    # arifmetikasini takrorlamaydi (Anti-Pattern 10).
    business_date: Mapped[date] = mapped_column(
        Date(),
        Computed(AUDIT_BUSINESS_DATE_EXPR, persisted=True),
        nullable=False,
    )
    market_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    # `sbozor_core.enums.ActorKind` — `user` yoki `system`. Fon jarayonlari
    # `system` bilan yozadi, shunda "kim?" savoli hech qachon bo'sh qolmaydi.
    actor_kind: Mapped[str] = mapped_column(Text(), nullable=False, server_default=text("'user'"))
    # D-06: "platforma admini X bozorida" — aktor kim sifatida ish
    # ko'rayotganini o'qiladigan matn bilan saqlaydi.
    actor_label: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # `sbozor_core.enums.AuditAction`. Trigger `lower(TG_OP)` yozadi, ilova
    # esa `login`/`read` kabi qiymatlarni — ikkalasi bitta ustunda.
    action: Mapped[str] = mapped_column(Text(), nullable=False)
    table_name: Mapped[str] = mapped_column(Text(), nullable=False)
    row_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    # Faqat HAQIQATAN o'zgargan ustunlar. Busiz har audit qatorini o'qiyotgan
    # odam ikkita JSONB'ni ko'z bilan solishtirishi kerak bo'lardi.
    changed_keys: Mapped[list[str] | None] = mapped_column(ARRAY(Text()), nullable=True)
    request_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    ip: Mapped[str | None] = mapped_column(INET(), nullable=True)
    # `sbozor_core.enums.AuditSource` — `db_trigger` yoki `app`.
    source: Mapped[str] = mapped_column(Text(), nullable=False)


class SystemHeartbeat(Base):
    """Fon komponentining «oxirgi marta qachon ishladi» yozuvi (FOUND-06, D-20).

    =========================================================================
    ⚠ `market_id` USTUNI ATAYIN YO'Q — JADVAL `GLOBAL_TABLES` DA.

    Komponent (`capture_tick`, `retention`, `backup`) BOZORGA TEGISHLI
    EMAS: tik butun platforma uchun BITTA jarayonda ishlaydi va uning
    to'xtagani hamma bozorga birdan tegadi.

    Uni tenant-scoped qilish MANTIQIY XATO bo'lardi: tik umuman
    ishlamayotgan bo'lsa, uning yo'qligini bozor kontekstida qidirish 0
    qator berardi va sukunat «hammasi joyida» bilan bir xil ko'rinardi —
    ya'ni D-20 («alert MUVAFFAQIYAT SIGNALINING YO'QLIGIGA qo'yiladi»)
    ning aynan buziladigan joyi.

    Bu FOUND-06 ning eng pastki qatlami — «detektorning O'ZI bajarilmadi»
    holati. Tik ichidagi watchdog kadr olishning yiqilishini qoplaydi;
    worker VA planer ikkalasi ham o'lik bo'lsa esa hech kim hech nimani
    `missed` deb belgilamaydi va JIMLIK HUKM SURADI. Bu jadval o'sha
    bo'shliqni yopadi: `core-api` BOSHQA jarayon, u tirik qoladi va
    `/internal/self-check` orqali yurak urishining eskirganini ko'rsatadi.
    =========================================================================

    ⚠ `/healthz` GA ULAMANG (Pitfall 14). Konteyner healthcheck'i —
    *liveness*: u yiqilsa Docker konteynerni QAYTA ISHGA TUSHIRADI.
    Worker'ning yurak urishi eskirgani uchun sog'lom API'ni qayta ishga
    tushirish klassik anti-naqsh. `/internal/self-check` ALOHIDA endpoint
    va u `compose.yaml` dagi healthcheck'da ISHLATILMAYDI.

    RLS QO'YILMAYDI va bu ZIDDIYAT EMAS: jadvalda tenant ma'lumoti yo'q
    (komponent nomi + vaqt tamg'asi), tenant predikati esa yozib
    bo'lmaydigan bo'lardi — `market_id` ustuni yo'q. Ilova roliga to'liq
    DML `0014` da `grant_app_dml()` bilan beriladi: worker yurak urishini
    YOZISHI, `core-api` esa O'QISHI kerak.

    `TimestampMixin` YO'Q: `created_at` ma'nosiz (qator bir marta
    tug'iladi va mangu yashaydi), `updated_at` esa `last_seen_at` ning
    dublikati bo'lardi.
    """

    __tablename__ = "system_heartbeats"

    # KOMPONENT NOMI — BIRLAMCHI KALITNING O'ZI (surrogat `id` YO'Q).
    # Har komponentga AYNAN bitta qator va yozuv `ON CONFLICT (component)
    # DO UPDATE` bilan ketadi. Surrogat kalit ikkinchi `capture_tick`
    # qatorini yozishga yo'l ochardi va «oxirgi urish qaysi?» savoli
    # javobsiz qolardi.
    component: Mapped[str] = mapped_column(Text(), primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Ixtiyoriy diagnostika: oxirgi tikda nechta bozor ko'rildi, nechta
    # qator materializatsiya qilindi. Alert QARORI bu maydonga tayanmaydi —
    # u faqat `last_seen_at` ning eskirishiga qaraydi.
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
