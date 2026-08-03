"""NVR kashfiyotining fon-vazifasi — loyihaning BIRINCHI so'rov-tashqari kodi.

=============================================================================
BU FAYLDA NAVBAT KUTUBXONASI IMPORT QILINMAYDI (D-06).

`discover_nvr` — SOF `async def` funksiya. Uni navbatga bog'laydigan yupqa
qobiq `app/worker.py` da va kutubxona nomi FAQAT o'sha faylda uchraydi.
4-faza boshqa mexanizmni tanlasa ko'chirish narxi ~10 qator bo'lishi kerak;
ikki mexanizm bir vaqtda saqlanmaydi.

⚠ Buni `grep -cE "^\\s*(import|from)\\s+taskiq"` mexanik tekshiradi.
=============================================================================

=============================================================================
PITFALL 13 — JOB TENANT KONTEKSTINI O'ZI O'RNATADI, VA BUSIZ U JIMGINA YOLG'ON
GAPIRADI.

`app/deps.py::get_tenant_session` — HTTP dependency'si: u `Request` dan
`Principal` oladi va GUC'larni o'rnatadi. Worker jarayonida `Request` YO'Q,
ya'ni o'sha yo'l umuman bajarilmaydi va GUC'lar bo'sh qoladi.

Bo'sh GUC ostida RLS FAIL-CLOSED ishlaydi, lekin "fail" so'zi bu yerda
aldamchi:

    SELECT / UPDATE  ->  0 qator, ISTISNO YO'Q
    INSERT           ->  `WITH CHECK` buzilishi (bu esa KO'RINADI)

Ya'ni kashfiyot jobi qurilmani "topa olmaydi", yugurish qatorini "yangilay
olmaydi" va hech qanday xato ham bermaydi. Natija: admin tugmani bosadi,
spinner aylanadi, so'ng hech nima bo'lmaydi — bu eng yomon xato turi.

Yechim shu modulda va u BITTA joyda: `_system_transaction()` HAR
tranzaksiyada `set_tenant_context(..., actor_kind=ActorKind.SYSTEM)` ni
chaqiradi. GUC'lar `SET LOCAL`, ya'ni ular har `COMMIT` da tozalanadi va
har yangi tranzaksiya uchun QAYTA o'rnatilishi SHART.

O'lchov: `tests/integration/test_nvr_discovery_job.py::
test_worker_sets_tenant_context` kontekstsiz chaqiruvda `channels_added`
ning 0 bo'lishini ANIQ ko'rsatadi (T-03-38).
=============================================================================

=============================================================================
NEGA UZUN TRANZAKSIYA ATAYIN VA `on_channels_found` NEGA UNDAN TASHQARIDA.

Kashfiyot ~17–60 soniya davom etadi (`03-RESEARCH.md` E.16 byudjeti) va
`run_discovery` yozuvlarni (`upsert_cameras` / `mark_missing_offline` /
`update_device`) OXIRIDA qiladi. Ya'ni ular BITTA tranzaksiyada bo'lishi
kerak — yarim yozilgan skan SC#2 ning idempotentlik da'vosini buzardi.

Lekin UI-SPEC §5.2 [TALAB] `channels_found` ni sub-oqim tekshiruvlaridan
OLDIN ko'rsatishni talab qiladi, ya'ni o'sha yangilanish poll qilayotgan
mijozga DARHOL ko'rinishi kerak. Uzun tranzaksiya ichida yozilgan qiymat
esa `COMMIT` gacha hech kimga ko'rinmasdi — talab bajarilgandek ko'rinib,
amalda BAJARILMASDI.

Shuning uchun `_publish_channels_found()` O'Z sessiyasini va O'Z
tranzaksiyasini ochadi va darhol commit qiladi. Narxi — ikkinchi ulanish
(pul o'lchami kamida 2 bo'lishi shart).
=============================================================================

JOB JARAYONI HECH QACHON YIQILMAYDI. Har istisno tutiladi va `failed`
sifatida yoziladi. Sabab navbat semantikasida: taskiq (va har qanday
navbat) yiqilgan vazifani QAYTA yetkazishi mumkin, qayta urinish esa
NVR ga ikkinchi marta borardi — D-03 ning qulflash arifmetikasi aynan
shuni taqiqlaydi.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final

import structlog
from sbozor_core.enums import ActorKind, AuditAction, DiscoveryRunStatus
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.nvr_repo import NvrRepository
from app.security.audit import TABLE_NVR_DISCOVERY_RUNS, write_app_audit
from app.security.secrets import InvalidToken, decrypt_nvr_password
from app.services.isapi.client import IsapiClient
from app.services.isapi.discovery import run_discovery
from app.services.isapi.errors import NvrError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

log = structlog.get_logger(__name__)

__all__ = [
    "DISCOVERY_JOB_ERROR_CODES",
    "JOB_INTERNAL_ERROR",
    "NVR_CREDENTIAL_UNREADABLE",
    "NVR_NOT_FOUND",
    "SYSTEM_ACTOR_LABEL",
    "discover_nvr",
]


NVR_NOT_FOUND: Final[str] = "nvr_not_found"
"""Qurilma qatori topilmadi (o'chirilgan yoki begona bozorniki).

API qatlamida bu 404 ning `detail` i, job qatlamida esa
`nvr_discovery_runs.error_code`. IKKALASIDA HAM BIR XIL SATR — aks holda
admin bir xil holat uchun ikki xil xabar ko'rardi.
"""

NVR_CREDENTIAL_UNREADABLE: Final[str] = "nvr_credential_unreadable"
"""Saqlangan parolni O'QIB BO'LMADI — bu ISAPI ning `401` idan BOSHQA holat.

⚠ AJRATISH 03-04 NING OCHIQ TALABI: *«`InvalidToken` yutilmaydi va uni
  ISAPI ning `401` idan farqlash SHART (SC#3 taksonomiyasi)»*. Sabab
  operatsion: `nvr_bad_credentials` "NVR dagi parol noto'g'ri" deydi va
  admin uni qayta kiritadi; bu kod esa "bizning SHIFR KALITIMIZ bilan
  muammo" deydi va uning yechimi butunlay boshqa joyda (kalit rotatsiyasi,
  `NVR_CREDENTIAL_KEYS_RETIRED`). Ikkalasini birlashtirish operatorni
  noto'g'ri joyni qidirishga majbur qilardi.

⚠ NEGA U `NVR_ERROR_CODES` GA QO'SHILMADI: o'sha reyestr ISAPI MULOQOTINING
  taksonomiyasi va uning "aynan o'n ikkita" ekani `03-VALIDATION.md` qamrov
  jadvali hamda `tests/unit/test_isapi_errors.py::
  test_registry_has_exactly_twelve_unique_codes` bilan qulflangan. Bu kod
  esa NVR bilan umuman gaplashishdan OLDIN, o'z bazamizda tug'iladi.
  Shuning uchun u `MARKET_ERROR_CODES` (domen kodlari reyestri) ga
  qo'shiladi.
"""

JOB_INTERNAL_ERROR: Final[str] = "discovery_internal_error"
"""Kutilmagan istisno — kod nuqsoni yoki infratuzilma nosozligi.

Bu kod `NvrError` ning O'RNINI BOSMAYDI: har qanday tanilgan sabab o'z
kodi bilan yoziladi va bu yerga FAQAT taksonomiyaga tushmagan istisno
keladi. To'liq iz `log.exception` bilan jurnalda qoladi; foydalanuvchiga
esa stack izi ham, istisno matni ham CHIQMAYDI (T-02-99).
"""

DISCOVERY_JOB_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {NVR_NOT_FOUND, NVR_CREDENTIAL_UNREADABLE, JOB_INTERNAL_ERROR}
)
"""Job YOZADIGAN, lekin ISAPI taksonomiyasiga TUSHMAYDIGAN kodlar.

`app/schemas.py::MARKET_ERROR_CODES` bu to'plamni IMPORT qiladi — qo'lda
takrorlamaydi. Ikki nusxa bo'lganda job bazaga kod yozib, API uni
tanimasdi va frontend `errors.generic` ko'rsatib sababni yo'qotardi
(§S-5 ning aynan o'zi).
"""

SYSTEM_ACTOR_LABEL: Final[str] = "tizim — NVR kashfiyoti"
"""`audit_log.actor_label` — jurnalni O'QIYOTGAN odam uchun.

`actor_user_id` baribir yoziladi (kashfiyotni ODAM ishga tushirgan), lekin
`actor_kind` `system`: yozuvni HTTP so'rovi emas, fon jarayoni qoldirgan.
Ikkalasi birga "buni X admin so'radi, bajargani esa tizim" deydi.
"""

_MAX_DETAIL_CHARS: Final[int] = 500
"""Job yozadigan `error_detail["raw"]` ning chegarasi.

`NvrError` o'z chegarasini KONSTRUKTORDA qo'yadi (4000), lekin bu yerdagi
matnlar `NvrError` dan o'tmaydi — ular bevosita `finish_run()` ga boradi.
Chegarasiz istisno matni (masalan uzun SQL) `jsonb` ustuniga cheksiz
o'sardi (T-03-30 bilan bir xil mulohaza, boshqa yo'lda).
"""


@asynccontextmanager
async def _system_transaction(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    actor_id: UUID | None,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti O'RNATILGAN sessiya — `deps.py:418-449` ning worker jufti.

    Uch farq bor va uchalasi ham ataylab:

      1. `Principal` YO'Q — `market_id` va `actor_id` argument sifatida
         keladi (ularni navbat xabari olib keladi);
      2. `actor_kind=ActorKind.SYSTEM` — `audit_log` da "buni odam emas,
         fon jarayoni yozdi" deb ko'rinsin;
      3. `HTTPException` YO'Q — worker'da javob beriladigan mijoz yo'q.

    ⚠ HAR CHAQIRUVDA YANGI TRANZAKSIYA VA YANGI KONTEKST. GUC'lar
      `SET LOCAL` bilan qo'yiladi, ya'ni `COMMIT` da tozalanadi. "Bir marta
      o'rnatib, keyin qayta ishlataman" yo'li fail-closed holatga tushardi
      va u JIMGINA 0 qator berardi (modul docstringi).
    """
    # SIM117 (ikki `async with` ni birlashtirish) `deps.py:434-439` dagi
    # bilan AYNAN bir xil sababdan rad etilgan: ichki blok TRANZAKSIYA
    # chegarasi va u shu yerdagi butun xavfsizlik da'vosini ushlab turadi.
    async with sessionmaker() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=actor_id,
                request_id=request_id,
                actor_kind=ActorKind.SYSTEM,
            )
            yield session


def _base_url(host: str, port: int, *, use_tls: bool) -> str:
    """`nvr_devices` qatoridan ISAPI bazaviy manzili.

    Manzil BAZADAN quriladi va boshqa hech qayerdan: "real qurilmaga
    o'tish — SOZLAMA o'zgarishi, kod o'zgarishi emas" (SC#7) da'vosining
    butun mazmuni shunda.
    """
    scheme = "https" if use_tls else "http"
    return f"{scheme}://{host}:{port}"


def _raw(message: str) -> dict[str, Any]:
    """`error_detail` ning yagona shakli — `raw` kaliti (UI-SPEC §7.4 allowlist'i)."""
    return {"raw": message[:_MAX_DETAIL_CHARS]}


async def discover_nvr(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    nvr_id: UUID,
    run_id: UUID,
    actor_id: UUID | None = None,
) -> None:
    """Kashfiyotni boshidan oxirigacha bajaradi va natijani yugurish qatoriga yozadi.

    Ketma-ketlik:

        1. `queued` -> `running`, rekvizit va qurilma o'qiladi (1-tranzaksiya)
        2. ISAPI muloqoti (`run_discovery`) — DB yozuvi OXIRIDA (2-tranzaksiya)
           + `channels_found` OWN, QISQA tranzaksiyada (UI-SPEC §5.2)
        3. `succeeded` / `failed` + hisoblagichlar (2- yoki 3-tranzaksiya)

    Args:
        sessionmaker: sessiya fabrikasi. ARGUMENT, modul globali EMAS —
            `app/security/audit.py::_write_read_audit` (loyihadagi yagona
            so'rov-tashqari DB yozuvi) ham aynan shunday oladi. Worker uni
            o'z startup ilgagida bir marta quradi (`app/worker.py`), test
            esa o'z engine'ini beradi.
        market_id: tenant. Navbat xabaridan keladi va u YAGONA manba —
            bazadan qayta o'qish "qaysi bozor?" savolini RLS ostida
            javobsiz qoldirardi (kontekstsiz o'qish 0 qator beradi).
        nvr_id: skanerlanadigan qurilma.
        run_id: `nvr_discovery_runs` qatori — uni API ALLAQACHON yaratgan
            (`queued`), ya'ni 409 poygasi HTTP chegarasida hal bo'lgan.
        actor_id: tugmani bosgan admin. `None` — rejalashtirilgan skan
            (kelajakdagi cron; `triggered_by` NULL bo'ladi).

    Returns:
        Hech nima. Natija — bazadagi yugurish qatori, navbatning javobi
        emas: mijoz uni `GET /discovery-runs/{run_id}` bilan poll qiladi.
    """
    # Butun skan uchun BITTA vaqt tamg'asi (03-04: `upsert_cameras` va
    # `mark_missing_offline` uni `<` bilan taqqoslaydi, ikki xil vaqt
    # chegarada noaniqlik berardi).
    run_started_at = datetime.now(tz=UTC)

    # ⚠ SO'ROV IDENTIFIKATORI DETERMINISTIK. Tasodifiy qiymat har
    #   tranzaksiyada boshqa bo'lardi va bitta skanning audit qatorlarini
    #   bir ipga bog'lash imkonsiz bo'lardi. `run_id` esa aynan shu skanni
    #   nomlaydi — jurnalda ham, `audit_log.request_id` da ham.
    request_id = f"job-discovery-{run_id}"

    context: dict[str, Any] = {
        "market_id": str(market_id),
        "nvr_id": str(nvr_id),
        "run_id": str(run_id),
    }

    try:
        device = await _begin_run(
            sessionmaker,
            market_id=market_id,
            nvr_id=nvr_id,
            run_id=run_id,
            actor_id=actor_id,
            request_id=request_id,
        )
    except SQLAlchemyError:
        # Yugurishni BOSHLAY olmadik, ya'ni `failed` yozishga ham
        # ishonchimiz yo'q. Iz jurnalda qoladi va navbat vazifani
        # muvaffaqiyatli deb hisoblaydi — qayta urinish NVR ga ikkinchi
        # marta borardi (D-03).
        log.exception("nvr_discovery_start_failed", **context)
        return

    if device is None:
        return

    finish = _Finisher(
        sessionmaker,
        market_id=market_id,
        run_id=run_id,
        actor_id=actor_id,
        request_id=request_id,
        context=context,
    )

    if device.error_code is not None:
        await finish.failed(device.error_code, _raw(device.error_detail or ""))
        return

    try:
        await _run_and_finish(
            sessionmaker,
            device=device,
            market_id=market_id,
            nvr_id=nvr_id,
            run_id=run_id,
            actor_id=actor_id,
            request_id=request_id,
            run_started_at=run_started_at,
            finish=finish,
            context=context,
        )
    except NvrError as error:
        # TANILGAN sabab — kod va tafsilot ALLAQACHON allowlist'dan
        # o'tgan (`NvrError` konstruktori), ya'ni ular to'g'ridan-to'g'ri
        # yoziladi.
        log.info("nvr_discovery_failed", error_code=error.code, **context)
        await finish.failed(error.code, error.detail)
    except Exception as exc:  # noqa: BLE001 - job jarayoni yiqilmasligi SHART
        log.exception("nvr_discovery_crashed", **context)
        await finish.failed(JOB_INTERNAL_ERROR, _raw(type(exc).__name__))


class _DeviceContext:
    """1-qadamdan chiqadigan hamma narsa — ORM obyekti EMAS, oddiy qiymatlar.

    Tranzaksiya YOPILGANDAN keyin ORM obyektiga tegish `expire_on_commit`
    sozlamasiga bog'lanib qolardi (`make_sessionmaker` uni `False` qiladi,
    lekin bu ikkinchi joydagi sozlama). Qiymatlar tranzaksiya ICHIDA
    ko'chiriladi va undan keyin hech qanday DB yo'li qolmaydi.
    """

    __slots__ = ("base_url", "error_code", "error_detail", "password", "username")

    def __init__(
        self,
        *,
        base_url: str = "",
        username: str = "",
        password: str = "",
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password
        self.error_code = error_code
        self.error_detail = error_detail


async def _begin_run(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    nvr_id: UUID,
    run_id: UUID,
    actor_id: UUID | None,
    request_id: str,
) -> _DeviceContext | None:
    """`queued` -> `running` + qurilma va rekvizitni o'qiydi.

    Returns:
        `None` — yugurish BOSHLANMADI (allaqachon boshlangan yoki tenant
        konteksti yo'q). `error_code` to'ldirilgan `_DeviceContext` —
        boshlandi, lekin darhol yiqiladi.
    """
    async with _system_transaction(
        sessionmaker, market_id=market_id, actor_id=actor_id, request_id=request_id
    ) as session:
        repo = NvrRepository(session, market_id)

        if not await repo.start_run(run_id):
            # ⚠ IKKI SABAB, BIR XIL NATIJA VA IKKALASI HAM XATO EMAS:
            #   (a) vazifa IKKINCHI MARTA yetkazildi (navbatlar "kamida bir
            #       marta" kafolatini beradi) — qator allaqachon `running`;
            #   (b) tenant konteksti YO'Q — RLS 0 qator berdi (Pitfall 13).
            # Ikkalasida ham to'g'ri xulq — HECH NIMA QILMASLIK: ikkinchi
            # skan NVR ga ikkinchi marta borardi.
            log.warning(
                "nvr_discovery_run_not_startable",
                market_id=str(market_id),
                nvr_id=str(nvr_id),
                run_id=str(run_id),
            )
            return None

        await write_app_audit(
            session,
            action=AuditAction.UPDATE,
            table_name=TABLE_NVR_DISCOVERY_RUNS,
            row_id=run_id,
            new={"status": DiscoveryRunStatus.RUNNING.value, "nvr_id": str(nvr_id)},
            actor_user_id=actor_id,
            market_id=market_id,
            request_id=request_id,
            actor_label=SYSTEM_ACTOR_LABEL,
            actor_kind=ActorKind.SYSTEM,
            track_changes=False,
        )

        device = await repo.get_device(nvr_id)
        if device is None:
            return _DeviceContext(
                error_code=NVR_NOT_FOUND,
                error_detail="nvr_devices qatori topilmadi",
            )

        token = await repo.get_credential(nvr_id)
        if token is None:
            return _DeviceContext(
                error_code=NVR_CREDENTIAL_UNREADABLE,
                error_detail="nvr_credentials qatori yo'q — parolni qayta kiriting",
            )

        base_url = _base_url(device.host, device.port, use_tls=device.use_tls)
        username = device.username

    try:
        password = decrypt_nvr_password(token)
    except InvalidToken:
        # ⚠ JURNALGA NA TOKEN, NA UNING BO'LAGI TUSHADI. Xabar operatorga
        #   QAYERGA qarashni aytadi (shifr kaliti), qiymatni emas.
        log.error(
            "nvr_credential_decrypt_failed",
            market_id=str(market_id),
            nvr_id=str(nvr_id),
        )
        return _DeviceContext(
            error_code=NVR_CREDENTIAL_UNREADABLE,
            error_detail=(
                "saqlangan parolni joriy shifr kaliti bilan ochib bo'lmadi "
                "(NVR_CREDENTIAL_KEY / NVR_CREDENTIAL_KEYS_RETIRED)"
            ),
        )

    return _DeviceContext(base_url=base_url, username=username, password=password)


async def _run_and_finish(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    device: _DeviceContext,
    market_id: UUID,
    nvr_id: UUID,
    run_id: UUID,
    actor_id: UUID | None,
    request_id: str,
    run_started_at: datetime,
    finish: _Finisher,
    context: dict[str, Any],
) -> None:
    """ISAPI muloqoti + muvaffaqiyatli yakun — BITTA tranzaksiyada.

    `run_discovery` yozuvlarni oxirida qiladi, ya'ni istisno ko'tarilganda
    tranzaksiya ROLLBACK bo'ladi va yarim yozilgan skan qolmaydi. `failed`
    yozuvi shuning uchun ALOHIDA, YANGI tranzaksiyada ketadi (`_Finisher`).
    """

    async def publish_channels_found(count: int) -> None:
        await _publish_channels_found(
            sessionmaker,
            market_id=market_id,
            actor_id=actor_id,
            request_id=request_id,
            run_id=run_id,
            count=count,
        )

    async with _system_transaction(
        sessionmaker, market_id=market_id, actor_id=actor_id, request_id=request_id
    ) as session:
        repo = NvrRepository(session, market_id)
        async with IsapiClient(device.base_url, device.username, device.password) as client:
            outcome = await run_discovery(
                repo,
                client,
                nvr_id=nvr_id,
                run_started_at=run_started_at,
                on_channels_found=publish_channels_found,
            )

        await repo.finish_run(
            run_id,
            DiscoveryRunStatus.SUCCEEDED.value,
            counts=outcome.counts,
        )
        await write_app_audit(
            session,
            action=AuditAction.UPDATE,
            table_name=TABLE_NVR_DISCOVERY_RUNS,
            row_id=run_id,
            new={
                "status": DiscoveryRunStatus.SUCCEEDED.value,
                "channels_found": outcome.counts.channels_found,
                "channels_added": outcome.counts.channels_added,
                "channels_marked_offline": outcome.counts.channels_marked_offline,
            },
            actor_user_id=actor_id,
            market_id=market_id,
            request_id=request_id,
            actor_label=SYSTEM_ACTOR_LABEL,
            actor_kind=ActorKind.SYSTEM,
            track_changes=False,
        )

    log.info(
        "nvr_discovery_succeeded",
        channels_found=outcome.counts.channels_found,
        channels_added=outcome.counts.channels_added,
        channels_marked_offline=outcome.counts.channels_marked_offline,
        # ⚠ OFLAYN KANALLAR XATO EMAS (UI-SPEC §6.4) — skan `succeeded`
        #   bo'lib qoladi va sabablar faqat jurnalga chiqadi.
        channel_issues=[error.code for error in outcome.channel_issues],
        **context,
    )
    finish.done = True


async def _publish_channels_found(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    actor_id: UUID | None,
    request_id: str,
    run_id: UUID,
    count: int,
) -> None:
    """`channels_found` ni ALOHIDA, QISQA tranzaksiyada yozadi (UI-SPEC §5.2 [TALAB]).

    ⚠ XATO YUTILADI (jurnalga yozib). Bu yozuv PROGRESS ko'rsatkichi, skan
      natijasi emas: uning yiqilishi butun kashfiyotni to'xtatishi mumkin
      emas. Aynan shu mulohaza `audit.py::_write_read_audit` da ham bor va
      u yerda ham xato yutiladi.
    """
    try:
        async with _system_transaction(
            sessionmaker, market_id=market_id, actor_id=actor_id, request_id=request_id
        ) as session:
            await NvrRepository(session, market_id).set_channels_found(run_id, count)
    except SQLAlchemyError as exc:
        log.warning(
            "nvr_discovery_progress_not_published",
            run_id=str(run_id),
            channels_found=count,
            error=str(exc),
        )


class _Finisher:
    """`failed` yozuvining YAGONA joyi — uch xato yo'li uni baham ko'radi.

    `done` bayrog'i faqat hujjat sifatida emas: u `_run_and_finish`
    muvaffaqiyatli tugaganini bildiradi va shu bilan "muvaffaqiyat ham,
    nosozlik ham yozilmagan" holatini imkonsiz qiladi.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        market_id: UUID,
        run_id: UUID,
        actor_id: UUID | None,
        request_id: str,
        context: dict[str, Any],
    ) -> None:
        self._sessionmaker = sessionmaker
        self._market_id = market_id
        self._run_id = run_id
        self._actor_id = actor_id
        self._request_id = request_id
        self._context = context
        self.done = False

    async def failed(self, error_code: str, error_detail: dict[str, Any]) -> None:
        """Yugurishni `failed` deb yopadi. Bu chaqiruv HECH QACHON ISTISNO KO'TARMAYDI."""
        try:
            async with _system_transaction(
                self._sessionmaker,
                market_id=self._market_id,
                actor_id=self._actor_id,
                request_id=self._request_id,
            ) as session:
                repo = NvrRepository(session, self._market_id)
                await repo.finish_run(
                    self._run_id,
                    DiscoveryRunStatus.FAILED.value,
                    error_code=error_code,
                    error_detail=error_detail,
                )
                await write_app_audit(
                    session,
                    action=AuditAction.UPDATE,
                    table_name=TABLE_NVR_DISCOVERY_RUNS,
                    row_id=self._run_id,
                    new={
                        "status": DiscoveryRunStatus.FAILED.value,
                        "error_code": error_code,
                    },
                    actor_user_id=self._actor_id,
                    market_id=self._market_id,
                    request_id=self._request_id,
                    actor_label=SYSTEM_ACTOR_LABEL,
                    actor_kind=ActorKind.SYSTEM,
                    track_changes=False,
                )
        except SQLAlchemyError:
            # Oxirgi chegara: nosozlikni YOZA olmadik. Jurnal yagona iz
            # bo'lib qoladi va job baribir tinch tugaydi.
            log.exception("nvr_discovery_failure_not_recorded", **self._context)
        else:
            self.done = True
