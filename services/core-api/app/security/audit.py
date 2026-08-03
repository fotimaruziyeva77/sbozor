"""App-qatlam audit yozuvi — `source='app'` (D-09, FOUND-03).

=============================================================================
IKKI XIL AUDIT YOZUVI BOR VA ULAR ARALASHTIRILMAYDI:

* `source='db_trigger'` — `fn_audit_row()` DB-triggeri yozadi. Qamrov:
  moliyaviy va huquq-o'zgartiruvchi JADVALLAR (D-10). Xom SQL bilan
  qilingan o'zgarish ham qamraladi, ya'ni ilova kodini chetlab o'tib
  bo'lmaydi.
* `source='app'` — SHU MODUL yozadi. Qamrov: DB o'zgarishi BO'LMAGAN
  hodisalar — `login`, `login_failed`, `logout`, `market_selected`,
  `refresh_reuse_detected`, `password_changed` va (01-07 da) shaxsiy
  ma'lumot O'QISHLARI.

Ya'ni bu modul triggerning O'RNINI BOSMAYDI; u trigger ko'ra olmaydigan
hodisalarni yozadi. Login DB'da hech nimani o'zgartirmaydi — trigger uchun
u umuman sodir bo'lmagan hodisa.
=============================================================================

`audit_append` policy'si `WITH CHECK (true)`, ya'ni jurnalga yozish
TENANT KONTEKSTIDAN QAT'I NAZAR ishlaydi — bu ataylab: `login_failed`
yozuvi bozor hali aniqlanmagan paytda ham qoldirilishi kerak.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import BackgroundTasks, Request
from sbozor_core.enums import ActorKind, AuditAction, AuditSource
from sqlalchemy import Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.exc import SQLAlchemyError

from app.deps import Principal, PrincipalDep

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = [
    "TABLE_AUDIT_LOG",
    "TABLE_CAMERAS",
    "TABLE_MARKETS",
    "TABLE_MARKET_PROFILE",
    "TABLE_NVR_DEVICES",
    "TABLE_NVR_DISCOVERY_RUNS",
    "TABLE_REFRESH_TOKENS",
    "TABLE_STALLS",
    "TABLE_TARIFFS",
    "TABLE_USERS",
    "TABLE_VENDORS",
    "AuditReadIntent",
    "audit_read",
    "platform_admin_label",
    "write_app_audit",
]

log = structlog.get_logger(__name__)

TABLE_USERS = "users"
"""`login`, `login_failed`, `password_changed` — hodisa foydalanuvchiga tegishli."""

TABLE_AUDIT_LOG = "audit_log"
"""Jurnalning O'ZINI o'qish (D-11) — `action='read'` yozuvining resursi."""

TABLE_MARKETS = "markets"
"""`market_selected` — hodisa bozor konteksti tanlanishiga tegishli (D-06)."""

TABLE_REFRESH_TOKENS = "refresh_tokens"  # noqa: S105 — jadval nomi, sir emas
"""`logout`, `refresh_reuse_detected` — hodisa sessiyaga tegishli."""

# ---------------------------------------------------------------------------
# 2-faza domen jadvallari.
#
# ⚠ BULARNING KO'PCHILIGIDA DB TRIGGERI BOR (`fn_audit_row()`, 02-05/02-06),
# ya'ni yozuv o'zi auditga tushadi va `write_app_audit()` chaqirilmaydi —
# aks holda har `INSERT` uchun IKKITA qator paydo bo'lardi va jurnalni
# o'qiyotgan odam "nima ikki marta sodir bo'ldi?" degan savol bilan qolardi.
#
# Konstantalar baribir kerak, chunki `source='app'` yozuvi trigger KO'RA
# OLMAYDIGAN hodisalar uchun yoziladi: shaxsiy ma'lumot O'QISHI (D-09 —
# `SELECT` uchun trigger yo'q) va DB o'zgarishisiz sodir bo'ladigan
# harakatlar. Nomlar bir joyda turgani uchun ular literal satr sifatida
# router fayllariga tarqalmaydi va `audit.table_name` filtri bilan mos
# qoladi.
# ---------------------------------------------------------------------------

TABLE_STALLS = "stalls"
"""`GET /stalls`, `GET /stalls/map`, `GET /stalls/{id}` — reestr resursi."""

TABLE_VENDORS = "vendors"
"""`GET /vendors` — SHAXSIY MA'LUMOT o'qishi (D-09), 02-10 `audit_read` manbai."""

TABLE_TARIFFS = "tariffs"
"""`GET /tariffs`, `POST /tariffs` — narx tarixi resursi (02-09)."""

TABLE_MARKET_PROFILE = "market_profile"
"""`PUT /calendar/weekdays` va usta rekvizitlari — bozor profili (02-09/02-11)."""

# ---------------------------------------------------------------------------
# 3-faza NVR domeni.
#
# ⚠ UCHTASI UCH XIL SABABDAN BOR VA ULAR ALMASHTIRIB BO'LMAYDI.
#
# `nvr_devices` va `cameras` DB TRIGGERI ostida (`0012_nvr_domain` ning 7-bandi:
# `NVR_AUDITED_TABLES`), ya'ni ularning har `INSERT`/`UPDATE`/`DELETE` i o'zi
# auditga tushadi va `write_app_audit()` ular uchun IKKINCHI qator yozardi.
# Konstantalar baribir kerak: trigger KO'RA OLMAYDIGAN hodisalar bor —
# parolning almashtirilishi (`nvr_credentials` ATAYIN triggersiz, T-03-13)
# `nvr_devices` ustiga QIYMATSIZ yoziladi, kamera yuzasining o'qish auditi
# esa 03-07 da shu nom bilan qo'shiladi.
#
# `nvr_discovery_runs` da esa trigger ATAYIN YO'Q va sabab migratsiyada
# yozilgan: u hodisa jurnali va faqat qo'shiladi, ya'ni trigger uning
# IKKINCHI nusxasini yozardi. Shuning uchun kashfiyotning ishga tushishi va
# yakunlanishi ILOVA qatlamida yoziladi (`03-PATTERNS.md` §S-6) — va aynan
# shu konstanta bilan.
# ---------------------------------------------------------------------------

TABLE_NVR_DEVICES = "nvr_devices"
"""`POST /nvr-devices/{id}/password` — parol almashtirish FAKTI (SC#4).

Yozuv QIYMATSIZ (`{"credentials_updated": True}`): "kim, qachon parolni
almashtirdi" savoliga javob bor, "parol nima edi" savoliga esa hech
qachon bo'lmaydi (`sbozor_core.models.nvr.NvrCredential` docstringi).
"""

TABLE_NVR_DISCOVERY_RUNS = "nvr_discovery_runs"
"""`POST /nvr-devices/{id}/discover` va fon jobining bosqichlari (§S-6).

Bu jadvalda DB triggeri YO'Q (yuqoridagi izoh), ya'ni "kashfiyot ishga
tushdi/tugadi" hodisasining yagona izi — shu nom bilan yozilgan
`source='app'` qatorlari.
"""

TABLE_CAMERAS = "cameras"
"""`GET /cameras` va kamera amallari (03-07) — kameralar reestri resursi.

Trigger `cameras` ni allaqachon qamraydi, ya'ni O'ZGARISHLAR uchun bu
konstanta ishlatilmaydi. U 03-07 ning O'QISH yuzasi uchun oldindan
e'lon qilinadi (`TABLE_VENDORS` bilan aynan bir xil naqsh: nom bir
joyda turadi va router fayllariga literal satr bo'lib tarqalmaydi).
"""

_INSERT_AUDIT = text(
    "INSERT INTO audit_log ("
    "market_id, actor_user_id, actor_kind, actor_label, action, table_name, row_id, "
    "old_value, new_value, changed_keys, request_id, ip, source"
    ") VALUES ("
    ":market_id, :actor_user_id, :actor_kind, :actor_label, :action, :table_name, :row_id, "
    ":old_value, :new_value, :changed_keys, :request_id, CAST(:ip AS inet), :source)"
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("actor_user_id", type_=PgUuid(as_uuid=True)),
    bindparam("row_id", type_=PgUuid(as_uuid=True)),
    bindparam("old_value", type_=JSONB),
    bindparam("new_value", type_=JSONB),
    bindparam("changed_keys", type_=ARRAY(Text)),
)
"""=============================================================================
NEGA ORM `insert(AuditLog)` EMAS, XOM `text()`:

SQLAlchemy mapped klass ustidagi `insert()` uchun `RETURNING id` QO'SHADI
(`Identity(always=True)` kaliti shu yo'l bilan qaytariladi). PostgreSQL esa
`INSERT ... RETURNING` da qaytariladigan qatorga **SELECT policy'sini**
qo'llaydi — `audit_log` da u tenant-scoped (`audit_read`). Natijada auth
oqimidagi (tenant kontekstisiz) har bir audit yozuvi

    new row violates row-level security policy for table "audit_log"

bilan yiqilardi va butun login endpointi 404 qaytarardi. Yozuvchiga
qatorni QAYTA O'QISH huquqi kerak emas va berilmasligi ham kerak —
`audit_append` policy'si ATAYIN faqat `WITH CHECK (true)`, `USING` emas.

Bind parametrlari `bindparam(type_=...)` bilan tiplangan: `text()` da
SQLAlchemy tipni ustundan chiqara olmaydi va `jsonb` / `text[]` / `uuid`
qiymatlari asyncpg'ga xom `dict`/`list` bo'lib borardi.
============================================================================="""


def platform_admin_label(phone: str | None, market_name: str | None) -> str:
    """D-06: "platforma admini X bozorida" — auditda o'qiladigan aktor tavsifi.

    `actor_user_id` va `market_id` ustunlari baribir yoziladi; bu matn
    jurnalni O'QIYOTGAN odam uchun: u ID'larni jadvalga bog'lamasdan
    "bu harakat platforma admini tomonidan, X bozori kontekstida qilingan"
    degan xulosaga kelishi kerak.
    """
    who = phone or "noma'lum"
    where = market_name or "bozor tanlanmagan"
    return f"platforma admini {who} — {where} bozorida"


async def write_app_audit(
    session: AsyncSession,
    *,
    action: AuditAction,
    table_name: str,
    row_id: UUID | None = None,
    old: dict[str, Any] | None = None,
    new: dict[str, Any] | None = None,
    principal: Principal | None = None,
    actor_label: str | None = None,
    actor_user_id: UUID | None = None,
    market_id: UUID | None = None,
    request_id: str | None = None,
    ip: str | None = None,
    actor_kind: ActorKind = ActorKind.USER,
    track_changes: bool = True,
) -> None:
    """`audit_log` ga bitta app-qatlam yozuvi qo'shadi.

    `track_changes=False` — `changed_keys` bo'sh qoldiriladi. Bu O'QISH
    yozuvlari uchun: `new_value` da filtr tavsifi turadi, lekin HECH
    NARSA O'ZGARMAGAN. Kalitlarni "o'zgargan" deb yozish jurnalni
    o'qiyotgan odamga yolg'on ma'lumot berardi (D-12 ning ko'rish UI'si
    aynan shu ustunni "nima o'zgardi" deb ko'rsatadi).

    `principal` berilsa, undan `actor_user_id` / `market_id` / `request_id` /
    `actor_label` STANDART QIYMAT sifatida olinadi; aniq argument har doim
    ustun turadi. Bu ikki chaqiruvchi uchun kerak:

    * himoyalangan endpointlar — `Principal` mavjud, hech nima uzatilmaydi;
    * `/auth/login` — `Principal` HALI YO'Q (u aynan shu so'rov natijasida
      tug'iladi), shuning uchun maydonlar aniq uzatiladi. `login_failed`
      holatida `market_id` `None` bo'lib qoladi: kim urinayotgani noma'lum,
      ya'ni bozorni "taxmin qilib" yozish yolg'on dalil bo'lardi.

    DIQQAT: chaqiruvchi tranzaksiyani O'ZI yopadi (`session.commit()`).
    Rad etish yo'llarida audit qatori commit qilinib, KEYIN `HTTPException`
    ko'tariladi — aks holda rollback jurnalni ham o'chirib yuborardi va
    aynan muvaffaqiyatsiz urinishlar izsiz qolardi.
    """
    resolved_actor = actor_user_id if actor_user_id is not None else _principal_user(principal)
    resolved_market = market_id if market_id is not None else _principal_market(principal)
    resolved_request = request_id if request_id is not None else _principal_request(principal)
    resolved_label = actor_label if actor_label is not None else _principal_label(principal)

    await session.execute(
        _INSERT_AUDIT,
        {
            "market_id": resolved_market,
            "actor_user_id": resolved_actor,
            "actor_kind": str(actor_kind),
            "actor_label": resolved_label,
            "action": str(action),
            "table_name": table_name,
            "row_id": row_id,
            "old_value": old,
            "new_value": new,
            "changed_keys": sorted(new) if (new and track_changes) else None,
            "request_id": resolved_request,
            "ip": ip,
            "source": str(AuditSource.APP),
        },
    )


def _principal_user(principal: Principal | None) -> UUID | None:
    return principal.user_id if principal is not None else None


def _principal_market(principal: Principal | None) -> UUID | None:
    return principal.market_id if principal is not None else None


def _principal_request(principal: Principal | None) -> str | None:
    return principal.request_id if principal is not None else None


def _principal_label(principal: Principal | None) -> str | None:
    return principal.actor_label if principal is not None else None


# ===========================================================================
# O'QISH AUDITI (D-09) — SHAXSIY MA'LUMOT O'QISHLARI HAM QAYD ETILADI
# ===========================================================================
#
# PostgreSQL'da `SELECT` uchun trigger YO'Q, ya'ni o'qishni faqat ilova
# qatlami yozib qo'yishi mumkin (RESEARCH Pattern 6).
#
# BLANKET MIDDLEWARE ATAYIN YOZILMAYDI. U:
#   * HAR bir so'rovni yozardi (`/healthz`, statik, OpenAPI) va jurnalni
#     foydasiz shovqin bilan to'ldirardi — natijada haqiqiy o'qish
#     hodisasi shovqin ichida yo'qolardi;
#   * qaysi RESURS o'qilganini bilmasdi (marshrut yo'li resurs turi emas);
#   * "nima uchun o'qildi" savoliga hech qachon javob bera olmasdi.
#
# Buning o'rniga — endpointda ANIQ E'LON QILINADIGAN dependency. Qamrov
# 1-fazada bitta (audit ko'rish UI'ning o'zi, D-11), keyingi fazalarda har
# bir shaxsiy-ma'lumot endpointi bir satr bilan qo'shiladi.
#
# YOZUV ALOHIDA TRANZAKSIYADA: o'qish SODIR BO'LGAN. Biznes tranzaksiyasi
# rollback bo'lsa ham (masalan keyinroq xato chiqsa) jurnalda iz qolishi
# kerak — aks holda aynan muvaffaqiyatsiz tugagan so'rovlar izsiz qolardi.


@dataclass
class AuditReadIntent:
    """Endpoint bilan fon vazifasi o'rtasidagi o'qish tavsifi.

    ATAYIN `frozen=True` EMAS: dependency uni so'rov BOSHIDA quradi
    (o'shanda natija hali noma'lum), endpoint esa `filters` va
    `result_count` ni to'ldiradi. Fon vazifasi javob yuborilgandan keyin
    ishlaydi va allaqachon to'ldirilgan obyektni ko'radi.
    """

    resource_type: str
    reason: str
    filters: dict[str, Any] = field(default_factory=dict)
    result_count: int = 0


async def _write_read_audit(
    sessionmaker: async_sessionmaker[AsyncSession],
    principal: Principal,
    intent: AuditReadIntent,
) -> None:
    """O'qish yozuvini YANGI sessiyada va alohida tranzaksiyada yozadi.

    Xato YUTILADI (log'ga yozib): bu kod javob mijozga JO'NATILGANDAN
    KEYIN ishlaydi, ya'ni istisno ko'tarish hech kimga yetib bormaydi va
    faqat "Task exception was never retrieved" ogohlantirishini beradi.
    Buning o'rniga nosozlik `error` darajasida yoziladi — monitoring uni
    aynan shu satrdan ko'radi.
    """
    try:
        async with sessionmaker() as session:
            await write_app_audit(
                session,
                action=AuditAction.READ,
                table_name=intent.resource_type,
                principal=principal,
                new={
                    "reason": intent.reason,
                    "filters": intent.filters,
                    "result_count": intent.result_count,
                },
                track_changes=False,
            )
            await session.commit()
    except SQLAlchemyError as exc:
        log.error(
            "audit_read_write_failed",
            resource_type=intent.resource_type,
            reason=intent.reason,
            error=str(exc),
        )


def audit_read(
    resource_type: str,
    *,
    reason: str,
) -> Callable[[Request, Principal, BackgroundTasks], Coroutine[Any, Any, AuditReadIntent]]:
    """O'qish auditini e'lon qiluvchi dependency fabrikasi (D-09).

    Ishlatilishi::

        ViewerDep = Annotated[Principal, Depends(require_permission(AUDIT_VIEW))]
        IntentDep = Annotated[
            AuditReadIntent,
            Depends(audit_read("audit_log", reason="audit_view")),
        ]

        @router.get("")
        async def list_audit(principal: ViewerDep, intent: IntentDep, ...):
            intent.filters = ...
            intent.result_count = len(items)

    RAD ETILGAN SO'ROV IZ QOLDIRMASLIGINI IKKI MUSTAQIL MEXANIZM
    ta'minlaydi (ikkalasi ham sabotaj bilan o'lchangan, batafsil sabab
    `app/api/v1/audit.py` modul docstringida):

      * huquq tekshiruvi dependency'si SHUNDAN OLDIN e'lon qilinadi —
        403 olgan so'rov bu yergacha yetib kelmaydi;
      * yozuv `BackgroundTasks` orqali ketadi, u esa endpoint
        MUVAFFAQIYATLI qaytargan javobga biriktiriladi — istisno bilan
        tugagan so'rov (masalan 422 query validatsiyasi) uchun FastAPI
        yangi javob quradi va unda fon vazifasi yo'q.
    """

    async def _dependency(
        request: Request,
        principal: PrincipalDep,
        background: BackgroundTasks,
    ) -> AuditReadIntent:
        intent = AuditReadIntent(resource_type=resource_type, reason=reason)
        # `request.state` — endpointdan tashqaridagi kod (masalan kelajakdagi
        # exception handler) niyatni topa olishi uchun; endpointning o'zi
        # obyektni dependency qiymati sifatida to'g'ridan-to'g'ri oladi.
        request.state.audit_read = intent
        background.add_task(
            _write_read_audit,
            request.app.state.sessionmaker,
            principal,
            intent,
        )
        return intent

    # INTROSPEKTSIYA TEGI — ISH PAYTIDA HECH KIM O'QIMAYDI.
    #
    # Yozuvni yuqoridagi `background.add_task(...)` qiladi va bu atribut
    # unga umuman tegmaydi. Teg BITTA iste'molchi uchun bor —
    # `tests/tenancy/test_personal_data_coverage.py` marshrutning
    # bog'liqlik grafini yurib "bu marshrutda o'qish auditi e'lon
    # qilinganmi va qaysi resurs uchun?" savoliga javob olishi kerak.
    #
    # Sabab va tanlangan tiplash varianti `deps.py::require_permission`
    # dagi jufti bilan AYNAN bir xil (manba matnini regex bilan tirnash
    # dekorator shakli o'zgarganda jimgina yashil qolardi).
    _dependency.audit_resource = resource_type  # type: ignore[attr-defined]
    return _dependency
