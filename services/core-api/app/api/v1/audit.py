"""Audit jurnalini ko'rish (D-11, D-12) — va ko'rishning O'ZINI qayd etish (D-09).

=============================================================================
KIM KO'RADI: `AUDIT_VIEW` huquqi bo'lganlar — platforma admini, direktor
va bozor admini (01-06 matritsasi). Kassir va nazoratchida bu huquq YO'Q
va bu ataylab: jurnal shaxsiy ma'lumot (kim, qachon, qaysi telefon bilan
kirgani) to'plami, ya'ni unga kirish nazorat funksiyasi bilan cheklanadi.

NIMA KO'RADI: FAQAT o'z bozorining yozuvlari. Buni ikki qatlam
majburlaydi — `audit_read` RLS policy'si (01-05) va `AuditRepository`
ning `scoped()` predikati. Platforma admini ham istisno emas: u bozor
TANLAB kiradi va tanlangandan keyin oddiy tenant kontekstida ishlaydi
(D-06).

KO'RGANI YOZILADI: `Depends(audit_read(...))` — bu endpointning
qaytariladigan ma'lumotidan KAM emas darajada muhim qismi. O'zbekiston
shaxsiy ma'lumotlar qonuni o'qishni ham qayd etishni talab qiladi (D-09).
=============================================================================

RAD ETILGAN SO'ROV JURNALDA IZ QOLDIRMAYDI — IKKI MUSTAQIL QATLAM:

    1. E'LON TARTIBI. `require_permission(AUDIT_VIEW)` `audit_read` dan
       OLDIN turadi. FastAPI dependency'larni aynan shu tartibda hal
       qiladi va birinchi `HTTPException` qolganlarini umuman chaqirmaydi,
       ya'ni 403 olgan so'rovda o'qish niyati QURILMAYDI ham.
    2. FON VAZIFASI JAVOBGA BOG'LANADI. Yozuv `BackgroundTasks` orqali
       ketadi, `BackgroundTasks` esa endpoint MUVAFFAQIYATLI qaytargan
       javob obyektiga biriktiriladi. Istisno bilan tugagan so'rov uchun
       FastAPI YANGI javob quradi va unda fon vazifasi yo'q — shu sababli
       422 (query validatsiyasi endpointdan KEYIN xato beradi) ham iz
       qoldirmaydi.

IKKALASI HAM O'LCHANDI: bittasini alohida buzganda testlar YASHIL qoladi
(ikkinchisi ushlaydi), ikkalasi birga buzilganda esa
`test_rejected_request_writes_no_read_row` va
`test_invalid_query_writes_no_read_row` darhol qizaradi. Ya'ni bu
haqiqiy ikki qatlam, bir qarorning ikki ta'rifi emas.

Nima uchun ikkitasi kerak: jurnaldagi YOLG'ON dalil (403 olgan kassir
"o'qidi" deb yozilishi) nizoni hal qilishda aynan shu yozuvga tayanadigan
odamni chalg'itadi — bu jurnalning bo'sh qolishidan ham yomonroq.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.audit_repo import (
    AuditRepository,
    InvalidCursorError,
    mask_sensitive,
)
from app.schemas import AuditEntry, AuditListResponse, AuditQuery
from app.security.audit import TABLE_AUDIT_LOG, AuditReadIntent, audit_read
from app.security.rbac import Permission

if TYPE_CHECKING:
    from uuid import UUID

router = APIRouter(tags=["audit"])

AuditViewerDep = Annotated[Principal, Depends(require_permission(Permission.AUDIT_VIEW))]
AuditReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_AUDIT_LOG, reason="audit_view")),
]


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`TenantSessionDep` allaqachon 409 qaytargan bo'lardi)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _describe(query: AuditQuery) -> dict[str, Any]:
    """Qo'llangan filtrlarning JSON tavsifi — o'qish yozuvi uchun.

    `mode="json"` sana va UUID qiymatlarini satrga o'giradi (JSONB'ga
    to'g'ridan-to'g'ri tushadi). `cursor` CHIQARIB TASHLANADI: u opaque
    va jurnalni o'qiyotgan odamga hech nima aytmaydi; `limit` esa qoladi,
    chunki "kim butun jurnalni yuklab oldi" savoliga aynan u javob beradi.
    """
    return query.model_dump(mode="json", exclude_none=True, exclude={"cursor"}, by_alias=True)


@router.get("", response_model=AuditListResponse)
async def list_audit(
    principal: AuditViewerDep,
    intent: AuditReadIntentDep,
    query: Annotated[AuditQuery, Query()],
    session: TenantSessionDep,
) -> AuditListResponse:
    """Filtrlanadigan audit ro'yxati (D-12).

    Javobdagi `old_value`/`new_value` JSONB'lari MASKALANADI: jurnalga
    tasodifan tushgan sezgir maydon ko'rish ekrani orqali tarqalmasligi
    kerak (T-01-52).
    """
    try:
        page = await AuditRepository(session, _market_id(principal)).list_audit(query)
    except InvalidCursorError as exc:
        # `HTTP_422_UNPROCESSABLE_CONTENT` — RFC 9110 dagi joriy nom;
        # eski `..._ENTITY` taxallusi Starlette'da eskirgan (bir xil 422).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_cursor",
        ) from exc

    intent.filters = _describe(query)
    intent.result_count = len(page.rows)

    return AuditListResponse(
        items=[
            AuditEntry(
                id=row.id,
                at=row.at,
                business_date=row.business_date,
                actor_user_id=row.actor_user_id,
                actor_label=row.actor_label,
                action=row.action,
                table_name=row.table_name,
                row_id=row.row_id,
                changed_keys=row.changed_keys,
                old_value=mask_sensitive(row.old_value),
                new_value=mask_sensitive(row.new_value),
                request_id=row.request_id,
                source=row.source,
            )
            for row in page.rows
        ],
        next_cursor=page.next_cursor,
    )
