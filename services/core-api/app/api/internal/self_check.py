"""O'z-o'zini kuzatish — worker o'lganini BOSHQA JARAYONDAN ko'rish (FOUND-06, D-20).

=============================================================================
⛔ QOIDA 1 — BU MARSHRUT `/healthz` GA ULANMAYDI VA KONTEYNER
   `healthcheck` IDA ISHLATILMAYDI (RESEARCH Pitfall 14).

Konteyner healthcheck'i — *liveness* probe: u yiqilsa Docker konteynerni
QAYTA ISHGA TUSHIRADI. Liveness'ni BOG'LIQLIK holatidan bog'lash klassik
anti-naqsh, va bu yerda u aniq zarar berardi: fon jarayonining yurak
urishi eskirgani uchun SOG'LOM API qayta ishga tushirilardi. Bu hech
nimani tuzatmasdi — aksincha, restart paytida API ham javob bermay
turardi, ya'ni bitta nosozlik IKKITAGA aylanardi.

`compose.yaml` ga tegilmagani `git diff` va alohida test bilan
tekshiriladi (`test_capture_schedule.py::test_self_check_is_not_wired_
into_the_container_healthcheck`).
=============================================================================

=============================================================================
⛔ QOIDA 2 — BUTUN MA'NOSI SHUNDAKI, U BOSHQA JARAYONDA.

`capture_tick` va `alert_sweep` worker konteynerida ishlaydi. Worker
o'lsa ikkalasi ham JIM bo'ladi — va sukunat nosozlikning eng yomon
shakli: hech qanday xato chiqmaydi, hech qanday alert yozilmaydi,
hisobotdagi son shunchaki o'sishdan to'xtaydi.

`core-api` esa ALOHIDA konteyner va u tirik qoladi. Ya'ni «detektorning
o'zi bajarilmadi» holatini u KO'RA oladi. Ikkalasi bir vaqtda o'lishi
uchun xost yoki compose butunlay yiqilishi kerak — va o'shanda nginx
ham `502` beradi, ya'ni nosozlik baribir KO'RINADI.

Bu D-20 ning eng pastki qatlami: alert MUVAFFAQIYAT SIGNALINING
YO'QLIGIGA qo'yiladi, faqat xato chiqish kodiga emas.
=============================================================================

=============================================================================
⛔ QOIDA 3 — JAVOB MINIMAL (§E.12).

Faqat `ok` bayrog'i va eskirgan komponentlarning NOMLARI. Bozor nomi,
kamera soni, `market_id` yoki topologiya haqida hech nima YO'Q.

Sabab: endpoint AUTENTIFIKATSIYASIZ ishlaydi (tashqi kuzatuvchi —
healthchecks.io / UptimeRobot — unga `Authorization` sarlavhasi bilan
kelmaydi). Autentifikatsiyasiz javob esa AXBOROT YUZASIGA aylanmasligi
kerak: «22 kamera» yoki bozor nomi tashqaridan so'ralganda o'sha
platformaning hajmi va mijozlari haqida ma'lumot bergan bo'lardi.

⛔ SHU FAYLDA TAQIQLANGAN MAYDON NOMLARINI LITERAL YOZMANG. Darvoza
   faylni MATN sifatida o'qiydi (`test_self_check_response_surface_stays_
   narrow`), ya'ni izohda ham yozilsa u qizarardi. Taqiq shu sababdan
   so'z bilan ta'riflangan: bozor nomi va kamera soni.
=============================================================================

-----------------------------------------------------------------------------
⚠⚠ `stale` VA `never_seen` — IKKI ALOHIDA RO'YXAT, VA `ok` FAQAT
   BIRINCHISI BO'YICHA HISOBLANADI.

`backup` komponenti 8-fazada yoziladi, ya'ni BUGUN u hech qachon yurak
urishi yozmagan. Ikkala holatni birlashtirgan variant endpointni
BIRINCHI KUNDAN `503` qilardi — va tashqi kuzatuvchi doimiy qizil
signalni ko'rib uni O'CHIRIB qo'yardi. O'shanda darvoza mavjud bo'lib
turib, hech nimani kuzatmasdi: haqiqiy nosozlik kelganda ham hech kim
xabar olmasdi.

Shuning uchun:

    stale       — chegaradan OSHGAN (yozilgan, lekin eskirgan) -> `ok=false`
    never_seen  — HECH QACHON yozilmagan                       -> `ok` ga ta'sir qilmaydi

⚠ `never_seen` JAVOBDA KO'RINADI va jimgina yashirilmaydi: «hali
  qurilmagan» holat OPERATORGA aytilishi kerak, aks holda 8-faza
  kelganda ham hech kim `backup` ning ulanmaganini sezmasdi.

⚠ BITTA ISTISNO: BIRORTA komponent ham ko'rinmasa (`system_heartbeats`
  butunlay bo'sh), `ok` HAM `false` bo'ladi. Bu «hali yozilmagan» emas,
  «hech nima ishlamayapti» holati — yangi o'rnatilgan tizimda worker
  umuman ko'tarilmagan bo'lishi mumkin va aynan o'sha kun eng muhim.
-----------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import structlog
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse
from sbozor_core.models import SystemHeartbeat
from sqlalchemy import func, select

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy import ColumnElement

    from app.settings import Settings

log = structlog.get_logger(__name__)

router = APIRouter(include_in_schema=False)
"""OpenAPI'ga CHIQMAYDI — `live_authz` bilan bir xil qaror va bir xil sabab.

Sxema MIJOZLAR uchun yoziladi, bu yerda esa mijoz yo'q: endpointni
tashqi kuzatuvchi bitta URL sifatida so'raydi va unga tip ta'rifi kerak
emas. UI ham uni KO'RSATMAYDI (`04-UI-SPEC.md` §16.2).
"""

EXPECTED_COMPONENTS: Final[tuple[str, ...]] = (
    "capture_tick",
    "alert_sweep",
    "retention",
    "backup",
    "cv_detect",
    "billing_close",
    "outbox_tick",
    "reconciliation_open",
    "notify_digest_morning",
    "notify_digest_evening",
    "notify_overdue",
)
"""Yurak urishi KUTILADIGAN fon komponentlari.

⚠ RO'YXAT SHU YERDA QATTIQ YOZILGAN va u `system_heartbeats` jadvalidan
  HOSILA EMAS — bu farq butun darvozaning mazmuni. Jadvaldan o'qilsa
  «hech qachon yozilmagan komponent» tushunchasining O'ZI yo'qolardi:
  bo'sh jadval «kutilayotgan hech nima yo'q» degan ma'no berib, endpoint
  `200 ok` qaytarardi — ya'ni worker umuman ko'tarilmagan holat
  «hammasi joyida» bo'lib ko'rinardi.

⚠ `backup` 8-fazada quriladi va bugun u DOIM `never_seen` da bo'ladi.
  Uni ro'yxatdan olib turish «keyin qo'shamiz» qarziga aylanardi va
  8-faza uni qo'shishni unutsa hech narsa qizarmasdi.

⚠ `cv_detect` — AYNAN SHU HOLATNING IKKINCHI NAMUNASI (05-02, W0-11).
  Komponent `cv-service` KONTEYNERIDA, ya'ni BOSHQA image'da ishlaydi va
  yurak urishini 05-08 yozadigan qiladi; bugun u DOIM `never_seen` da.
  Reyestrga BUGUN qo'shilishining sababi `backup` niki bilan bir xil va
  bu yerda yanada o'tkir: `cv-service` — ALOHIDA konteyner, ya'ni uning
  jimgina o'lishini `core-api` dan boshqa hech kim ko'rmaydi. Ro'yxatga
  keyin qo'shish «05-08 unutsa hech narsa qizarmaydi» degani bo'lardi.

⚠ QO'SHILISH `/internal/self-check` NI BUZMAYDI: `healthy = not stale and
  bool(seen)` — `never_seen` `ok` ga TA'SIR QILMAYDI (fayl boshidagi
  oxirgi blok). Ya'ni endpoint bugun ham `200` qaytaradi va javobda
  `cv_detect` `never_seen` ro'yxatida OCHIQ ko'rinadi.

=============================================================================
⛔⛔ `billing_close` — 6-FAZADA QO'SHILDI VA U MEXANIK KO'RLIKNI YOPADI.

Satr `app/jobs/billing_close.py::BILLING_CLOSE_COMPONENT` bilan AYNAN bir
xil bo'lishi SHART va ular MATN sifatida bog'langan (reyestr jadvaldan
hosila EMAS — yuqoridagi birinchi ⚠). Nom ayrilsa endpoint uni MANGU
`never_seen` da ko'rsatardi, holbuki job ishlab turardi.

⛔ NEGA BU QATOR KERAK: cron jadvali `import` PAYTIDA olinadi
(`worker.py:55-58`), ya'ni `scheduler` konteyneri qayta ishga
tushirilmasa `billing.close` vazifasi RO'YXATGA OLINMAYDI — job hech
qachon ishlamaydi va HECH QANDAY xato chiqmaydi. Birorta test buni
ushlamaydi (testlar reyestrni jarayonning O'ZIDA o'qiydi). Bu qator
(va `alerting.py::watched` dagi jufti) — YAGONA mexanik himoya.

⚠ `day_close` ATAYIN QO'SHILMADI va bu qarz sifatida OCHIQ yozilgan:
  u 5-faza domeni va uning AYNAN SHU bo'shlig'i (yurak urishi
  `system_heartbeats` ga yoziladi, lekin uning YO'QLIGI hech qayerda
  ko'rinmaydi) shu rejaning SUMMARY sida nomlangan o'tkazma band bo'lib
  qoladi. Uni «yo'l-yo'lakay» qo'shish 6-fazani 5-fazaning qarziga
  bog'lardi: `day_close` ning yurak urishi 5-fazadagi testlar bilan
  o'lchanadi va reyestrga qo'shilishi ularning kutilmasini ham
  siljitardi.
=============================================================================

=============================================================================
⛔⛔ OXIRGI BESH SATR — 7-FAZANING FON OQIMI (07-14, D-17; 07-21 da BESHTA).

`outbox_tick` · `reconciliation_open` · `notify_digest_morning` ·
`notify_digest_evening` · `notify_overdue`

⛔ (a) SATRLAR `app/jobs/*.py` DAGI KOMPONENT KONSTANTALARI BILAN AYNAN
   BIR XIL BO'LISHI SHART va ular MATN sifatida bog'langan — reyestr
   jadvaldan hosila EMAS (yuqoridagi birinchi ⚠). Manbalari:

       app/jobs/outbox.py::OUTBOX_COMPONENT
       app/jobs/reconciliation.py::RECON_OPEN_COMPONENT
       app/jobs/notifications.py::DIGEST_MORNING_COMPONENT /
                                 DIGEST_EVENING_COMPONENT / OVERDUE_COMPONENT

   Nom ayrilsa endpoint komponentni MANGU `never_seen` da ko'rsatardi,
   holbuki job ishlab turardi. Tenglik `tests/unit/test_heartbeat_
   registry.py` da AST bilan, HOSILA darvoza sifatida o'lchanadi: ro'yxat
   qo'lda solishtirilmaydi, `app/jobs/` katalogi TO'LIQ skanerlanadi.

⛔ (b) NEGA BU QATORLAR KERAK — `billing_close` bandi bilan AYNAN BIR XIL
   SABAB VA U ENDI BESH VAZIFAGA TEGISHLI: cron jadvali `import` PAYTIDA
   olinadi, ya'ni `scheduler` konteyneri qayta ishga tushirilmasa
   vazifalar RO'YXATGA OLINMAYDI — job hech qachon ishlamaydi va HECH
   QANDAY xato chiqmaydi. Birorta test buni ushlamaydi (testlar reyestrni
   jarayonning O'ZIDA o'qiydi). Bu qatorlar (va `alerting.py::watched`
   dagi juftlari) — YAGONA mexanik himoya.

⛔ (c) `notify_overdue` ALOHIDA QO'SHILDI VA BU TADQIQOTDAN CHETLANISH.
   `07-RESEARCH.md` UCHTA komponentni sanagan (`outbox_tick`,
   `reconciliation_open`, `notify_digest`) — BOT-03 ning jobi o'sha
   ro'yxatda YO'Q edi. D-17 esa «yangi cron joblar» deydi: ko'plikda va
   ISTISNOSIZ. `deferred-items.md` ning 2-bandi aynan shunday BITTA
   unutilgan komponent edi va uning oqibati o'lchangan: kuzatilmagan
   eslatma jobi hech qanday xato bermaydi — sotuvchilar shunchaki
   eslatma olmay qo'yadi va buni ma'muriyat OYLAR keyin sezadi.

⛔ (d) IKKI DAYJEST — IKKI SATR (07-21, WR-10). Ilgari bu yerda BITTA
   `notify_digest` turardi va u 07-13 ning OCHIQ NARXI edi: ikkala job
   ham o'sha bitta qatorni yangilardi, ya'ni kechkisi ishlab
   ertalabkisi o'lganda yurak urishi HAMON YANGI ko'rinardi va reyestr
   faqat «IKKALASI HAM o'ldi» holatini ko'rardi. Endi HAR BIRI o'z
   nomini yozadi, ya'ni yarim o'lgan juftlik `stale` yoki `never_seen`
   ro'yxatida NOMMA-NOM ko'rinadi.
   ⚠ `alerting.py::watched` da esa alert KALITI bitta qoladi
     (`digest_stale`) — sabab o'sha kortej ustidagi izohda.
=============================================================================
"""

_OK = "ok"
_STALE = "stale"
_NEVER_SEEN = "never_seen"


@router.get("/internal/self-check")
async def self_check(request: Request) -> Response:
    """`200 {"ok": true}` yoki `503 {"ok": false, ...}` — fayl boshidagi uch qoida.

    Marshrut PREFIKSSIZ va RBAC dependency'siz (`live_authz` va
    `main.py::healthz` naqshi): uni foydalanuvchi emas, TASHQI KUZATUVCHI
    chaqiradi va unda `Authorization` sarlavhasi umuman bo'lmaydi.

    ⚠ TENANT KONTEKSTI KERAK EMAS: `system_heartbeats` — GLOBAL jadval
      (`market_id` ustunining O'ZI yo'q, `GLOBAL_TABLES` da) va unga RLS
      qo'yilmagan. Bu ZIDDIYAT EMAS: jadvalda tenant ma'lumoti yo'q,
      tenant predikatini esa yozib ham bo'lmaydi. Aksincha — uni
      tenant-scoped qilish MANTIQIY XATO bo'lardi: tik umuman
      ishlamayotgan bo'lsa uning yo'qligini bozor kontekstida qidirish 0
      qator berardi va sukunat «hammasi joyida» bilan bir xil ko'rinardi.

    Javob `JSONResponse` bilan QO'LDA quriladi: `503` holatida ham TANA
    bo'lishi kerak (qaysi komponent eskirgani), `HTTPException` esa uni
    `detail` ichiga o'rab, shaklni o'zgartirib yuborardi.
    """
    settings: Settings = request.app.state.settings
    sessionmaker = request.app.state.sessionmaker

    async with sessionmaker() as session:
        # ⚠ «ESKIRGANMI?» QARORI BAZANING SOATIDA (`now()`), ilovaniki-da
        #   EMAS. Ikki jarayon ikki xil soatda ishlashi mumkin (konteyner
        #   drift, NTP sakrashi) va o'shanda chegara jimgina siljirdi.
        #   Yurak urishini YOZUVCHI ham `now()` ishlatadi (`jobs/capture.py`),
        #   ya'ni yozish va o'qish AYNI manbaga tayanadi.
        rows = await session.execute(
            select(
                SystemHeartbeat.component,
                SystemHeartbeat.last_seen_at < _threshold(settings.self_check_stale_minutes),
            )
        )
        seen = {str(component): bool(is_stale) for component, is_stale in rows}

    stale = sorted(name for name in EXPECTED_COMPONENTS if seen.get(name) is True)
    never_seen = sorted(name for name in EXPECTED_COMPONENTS if name not in seen)
    # `ok` FAQAT `stale` bo'yicha — modul docstringidagi oxirgi blok.
    # Bitta istisno: birorta komponent ham ko'rinmasa, bu «hali
    # qurilmagan» emas, «hech nima ishlamayapti».
    healthy = not stale and bool(seen)

    if not healthy:
        log.warning("self_check_degraded", stale=stale, never_seen=never_seen)
    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={_OK: healthy, _STALE: stale, _NEVER_SEEN: never_seen},
    )


def _threshold(stale_minutes: int) -> ColumnElement[datetime]:
    """`now() - make_interval(mins => :n)` — SQL ifodasi, Python vaqti EMAS.

    ⚠ INTERVAL BAZA TOMONIDA HISOBLANADI. `datetime.now(tz=...)` bilan
      qurilgan chegara `core-api` konteynerining soatiga tayanardi va
      baza soatidan bir necha soniya farq qilishi mumkin edi — 10
      daqiqalik oynada bu sezilmaydi, lekin chegarani 1 daqiqaga
      tushirgan operator uchun u tasodifiy signal berardi. Yurak urishini
      YOZUVCHI ham `now()` ishlatadi, ya'ni ikkala tomon AYNI soatga
      tayanadi.

    ⚠ `make_interval()` POZITSION argumentlar bilan chaqiriladi va son
      BOG'LANGAN parametr bo'lib ketadi. `text(f"interval '{n} minutes'")
      varianti sozlamani SQL matniga interpolyatsiya qilardi — bu yerda
      qiymat `int` bo'lgani uchun xavfsiz bo'lsa ham, u naqsh sifatida
      keyingi faylga nusxa bo'lib o'tardi va o'sha yerda satr bo'lardi.
    """
    minutes_position = (0, 0, 0, 0, 0, stale_minutes)
    return func.now() - func.make_interval(*minutes_position)
