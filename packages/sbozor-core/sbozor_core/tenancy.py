"""Tenant konteksti — PostgreSQL GUC'lari va ikkinchi qatlam filtri.

Izolyatsiya UCH qatlamda quriladi va uchalasi ham kerak (Pattern 1, P9):

1. **RLS policy** (DB) — himoya to'ri. App-rol `NOSUPERUSER NOBYPASSRLS`
   bo'lgani uchun uni chetlab o'tish yo'li yo'q.
2. **`TenantScopedRepository`** (ilova) — asosiy filtr. RLS ishlayotgan
   bo'lsa ham, so'rov o'zi to'g'ri bo'lishi kerak: aks holda "0 qator"
   javoblari xato deb emas, bo'sh ma'lumot deb talqin qilinadi.
3. **Composite FK** (sxema) — cross-tenant bog'lanishni strukturaviy
   imkonsiz qiladi (01-04).

Bu modul 1- va 2-qatlamning ILOVA TOMONIDAGI mexanikasini beradi.

=============================================================================
NEGA `set_config`, NEGA `SET` BUYRUG'I EMAS:
Postgres'ning `SET` buyrug'i (uning tranzaksiya-lokal varianti ham) bind
parametr QABUL QILMAYDI — `SET app.market_id = :m` shakli empirik ravishda
`PostgresSyntaxError: syntax error at or near "$1"` beradi. Yagona to'g'ri
yo'l — `SELECT set_config('app.market_id', :m, true)`: bu oddiy funksiya
chaqiruvi, ya'ni parametrni normal qabul qiladi.

Bu qoida `tests/unit/test_tenancy.py` da qulflangan.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import text

from sbozor_core.enums import ActorKind

if TYPE_CHECKING:
    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "ACTOR_ID_GUC",
    "ACTOR_KIND_GUC",
    "MARKET_ID_GUC",
    "REQUEST_ID_GUC",
    "SET_TENANT_CONTEXT",
    "TENANT_GUCS",
    "TenantScopedRepository",
    "set_tenant_context",
]

# GUC nomlari — migratsiyalar (RLS policy matni) va testlar shu yerdan oladi,
# satrni qaytadan yozmaydi. Quyidagi SQL'da ular ATAYIN literal ko'chirilgan:
# xavfsizlik uchun kritik bo'lgan bu ifodani f-string ortiga yashirmaslik
# kerak — u o'qiganda ham, `grep` qilganda ham ko'rinib turishi shart.
MARKET_ID_GUC = "app.market_id"
ACTOR_ID_GUC = "app.actor_id"
REQUEST_ID_GUC = "app.request_id"
ACTOR_KIND_GUC = "app.actor_kind"

TENANT_GUCS = (MARKET_ID_GUC, ACTOR_ID_GUC, REQUEST_ID_GUC, ACTOR_KIND_GUC)

SET_TENANT_CONTEXT = text(
    "SELECT set_config('app.market_id', :market_id, true), "
    "set_config('app.actor_id', :actor_id, true), "
    "set_config('app.request_id', :request_id, true), "
    "set_config('app.actor_kind', :actor_kind, true)"
)
"""To'rtta GUC'ni BITTA operatorda o'rnatadi.

Uchinchi argument (`is_local`) `true` — qiymat tranzaksiya oxirida
tark etiladi. Bu majburiy: puldagi ulanish keyingi so'rovga o'tganda eski
bozorning konteksti bilan ketmasligi kerak.
"""


async def set_tenant_context(
    session: AsyncSession,
    *,
    market_id: UUID | None,
    actor_id: UUID | None,
    request_id: str | None,
    actor_kind: ActorKind = ActorKind.USER,
) -> None:
    """Tenant kontekstini JORIY TRANZAKSIYAGA o'rnatadi.

    `None` qiymatlar bo'sh satr (`''`) bo'lib uzatiladi, `NULL` emas —
    `set_config` matn kutadi. Policy tomonida ular
    `NULLIF(current_setting('app.market_id', true), '')::uuid` orqali `NULL`
    ga aylanadi va natija FAIL-CLOSED bo'ladi: 0 qator, xato emas
    (Pitfall 1 — `''::uuid` "invalid input syntax" beradi).

    Raises:
        RuntimeError: sessiyada ochiq tranzaksiya bo'lmasa. Autocommit
            rejimida har operator o'z tranzaksiyasida ketadi, ya'ni
            `set_config(..., true)` qiymati DARHOL yo'qoladi va keyingi
            so'rov kontekstsiz — jimgina 0 qator bilan — bajariladi.
    """
    if not session.in_transaction():
        raise RuntimeError(
            "set_tenant_context() ochiq tranzaksiya talab qiladi. "
            "`async with session.begin():` bloki ichida chaqiring — "
            "set_config(..., is_local=true) autocommit rejimida qiymatni "
            "darhol yo'qotadi va tenant konteksti umuman o'rnatilmaydi."
        )

    await session.execute(
        SET_TENANT_CONTEXT,
        {
            "market_id": str(market_id) if market_id is not None else "",
            "actor_id": str(actor_id) if actor_id is not None else "",
            "request_id": request_id if request_id is not None else "",
            "actor_kind": str(actor_kind),
        },
    )


class TenantScopedRepository:
    """Repozitoriylar uchun baza — IKKINCHI qatlam filtri.

    RLS himoya to'ri bo'lsa ham, so'rovga `market_id` predikatini qo'shish
    majburiy (P9). Ikki sabab:

    * RLS bir kun noto'g'ri migratsiya bilan o'chib qolsa, ilova baribir
      to'g'ri ishlaydi;
    * predikat rejalashtiruvchiga indeks ishlatish imkonini beradi — RLS
      ifodasi yolg'iz o'zi har doim ham indeksga tushmaydi.

    Voris klasslar `self.session` va `self.market_id` dan foydalanadi va har
    bir `select()` ni `self.scoped(...)` orqali o'tkazadi.
    """

    def __init__(self, session: AsyncSession, market_id: UUID) -> None:
        self.session = session
        self.market_id = market_id

    def scoped[SelectT: Select[Any]](self, stmt: SelectT) -> SelectT:
        """Berilgan `SELECT` ga `market_id` predikatini qo'shadi.

        Raises:
            TypeError: so'rovning asosiy entity'sini aniqlab bo'lmasa yoki
                unda `market_id` ustuni bo'lmasa. Bu ATAYIN qattiq: jimgina
                filtrsiz qaytish — aynan oldini olinayotgan nosozlik.
        """
        descriptions = stmt.column_descriptions
        if not descriptions:
            raise TypeError(
                "scoped() so'rovning asosiy entity'sini aniqlay olmadi — "
                "`select(Model)` yoki `select(Model.column)` shaklini bering"
            )

        entity = descriptions[0].get("entity")
        if entity is None:
            raise TypeError(
                "scoped() ORM entity'siz so'rovda ishlatib bo'lmaydi "
                f"(masalan `select(func.count())`): {descriptions[0].get('name')!r}"
            )

        column = getattr(entity, "market_id", None)
        if column is None:
            raise TypeError(
                f"{getattr(entity, '__name__', entity)!r} da `market_id` ustuni yo'q. "
                "Tenant-scoped bo'lmagan jadval uchun bu repozitoriyni "
                "ishlatmang (istisnolar: sbozor_core.schema_contract.GLOBAL_TABLES)."
            )

        return stmt.where(column == self.market_id)
