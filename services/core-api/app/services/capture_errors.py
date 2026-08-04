"""Kadr olish xato taksonomiyasi — o'n bir kod, IKKI iste'molchi, BITTA reyestr.

=============================================================================
NEGA REYESTR BITTA (§S-5, §S-7 — `isapi/errors.py` bilan aynan bir xil sabab).

Bu ro'yxatning ikkita iste'molchisi bor va ular turli qatlamlarda:

    capture_runs.error_code                     -> baza ustuni  (04-05)
    HTTPException(detail={"error_code": ...})   -> HTTP javobi  (04-07)

Ularni ikki ro'yxatga bo'lish IKKI HAQIQAT MANBAI hosil qilardi: job
bazaga `capture_stream_limit` yozib, API uni tanimay `errors.generic`
ko'rsatardi va nosozlik faqat foydalanuvchi ekranida ko'rinardi.

⚠ `app/schemas.py` `CAPTURE_JOB_ERROR_CODES` ni IMPORT qiladi (04-07),
  qayta YOZMAYDI (`discovery.py:141-150` naqshi).
=============================================================================

D-02: backend **KOD** beradi, matnni frontend uch tilda chizadi. Bu modulda
foydalanuvchi matni YO'Q va bo'lmaydi — u `frontend/messages/*.json` da
(`snapshots.errorCause.*` / `snapshots.errorFix.*`, `04-UI-SPEC.md` §11.8).

=============================================================================
⛔ `AUTH_LOCKING_CODES` NING 4-FAZADAGI YANGI MA'NOSI.

3-fazada bu to'plam FAQAT frontendning «Qayta urinish» tugmasini
boshqarardi. Bu yerda u BACKEND XULQIGA aylanadi: bunday kodda TIKNING
HAM qayta urinishi TAQIQLANADI — qator DARHOL `failed` bo'ladi va
`attempts = max_attempts` qo'yiladi.

Arifmetika shafqatsiz: tik har DAQIQADA ishlaydi. Taqiq bo'lmasa 25
kamera x 10 tik = 250 muvaffaqiyatsiz autentifikatsiya urinishi va
Hikvision hisobni ~5 urinishdan keyin 30 daqiqaga QULFLAYDI. Undan
keyin TO'G'RI PAROL HAM ishlamaydi, ya'ni tizim o'zining tuzatish
yo'lini o'zi yopib qo'yardi — va buni butun bozorning har bir kamerasi
uchun qilardi.

⚠ `capture_stream_limit` BU TO'PLAMDA EMAS va bu ATAYIN: u retry emas,
  KECHIKTIRISH (`locked_until` qayta ishlatiladi). NVR shunchaki band;
  oqim bo'shagach kadr olish MUVAFFAQIYATLI bo'ladi. Uni qulflovchi
  kodlarga qo'shish slotni butunlay tashlab yuborardi — ya'ni «NVR band
  edi» sababi «kadr yo'q» ga aylanardi.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

__all__ = [
    "CAPTURE_AUTH_LOCKING_CODES",
    "CAPTURE_DEFER_CODES",
    "CAPTURE_ERROR_CODES",
    "CAPTURE_ERROR_META",
    "CAPTURE_JOB_ERROR_CODES",
    "MAX_DETAIL_CHARS",
    "CaptureError",
    "CaptureErrorMeta",
]

Actor = Literal["admin", "platform", "none"]
"""KIM tuzatadi — xato matnining UCHINCHI qismi (`04-UI-SPEC.md` §5.3).

SABAB + NIMA QILISH KERAK yetarli emas: aktorsiz xabar admin va platforma
jamoasini bir-birini kutib turishga majbur qiladi. `none` — «harakat talab
qilinmaydi» va u ATAYIN faqat BITTA kodda (pastga qarang).
"""

MAX_DETAIL_CHARS: Final[int] = 500
"""`capture_runs.error_detail` ga yoziladigan matnning chegarasi.

`discovery.py:160-166` bilan bir xil son va bir xil sabab: buzilgan yoki
soxta NVR megabaytlab javob yuborishi mumkin va u bazaga tushmasligi
kerak (T-03-30).

⚠ `NvrError` ning 4000 belgili chegarasidan KICHIK — bu farq ataylab: u
  yerdagi matn ISAPI ning XML javobi (tashxis uchun kontekst kerak), bu
  yerdagi esa bitta jumlalik texnik sabab.
"""


@dataclass(frozen=True, slots=True)
class CaptureErrorMeta:
    """Kodning XULQI — retry siyosati va UI aktori BIR JOYDA.

    ⚠ `retry_safe` va `locks_account` MUSTAQIL bayroqlar, bittasi
      ikkinchisidan hosil emas. `capture_timeout` — `retry_safe=True`,
      `locks_account=False`; `capture_credential_unreadable` —
      `retry_safe=False`, `locks_account=False` (qayta urinish foydasiz,
      lekin hech nima qulflanmaydi). Ularni bitta bayroqqa yig'ish
      uchinchi holatni ifodalab bo'lmas qilardi.

    Attributes:
        code: `CAPTURE_ERROR_CODES` dagi satr. Mashina uchun BARQAROR.
        retry_safe: qayta urinish HOLATNI o'zgartirmaydimi.
        locks_account: qayta urinish NVR hisobini qulflaydimi.
        defer: qator KECHIKTIRILADIMI (`failed` emas, `locked_until`).
        actor: kim tuzatadi.
    """

    code: str
    retry_safe: bool
    locks_account: bool
    defer: bool
    actor: Actor


# ---------------------------------------------------------------------------
# Reyestr — `04-UI-SPEC.md` §11.8 bilan AYNAN mos, guruh-guruh
# ---------------------------------------------------------------------------

CAPTURE_SLOT_MISSED: Final[str] = "capture_slot_missed"
"""Slot grace oynasi ichida UMUMAN bajarilmadi — YO'QLIK yozuvi (D-20).

API qatlamida bu `detail` ning `error_code` i, job qatlamida esa
`capture_runs.error_code`. IKKALASIDA HAM BIR XIL SATR.

⚠ Bu kod «xato bergan slot» ni emas, «HECH QANDAY HODISA BO'LMAGAN» ni
  ifodalaydi va aynan shuning uchun u rejadan kelib chiqadi: yozuv slot
  vaqti kelishidan OLDIN yaratiladi. Aks holda «hech qachon bajarilmagan»
  holatini aniqlaydigan hech narsa qolmasdi.

⚠ Qayta urinish MA'NOSIZ: vaqt QAYTARILMAYDI. 06:00 sloti 07:05 da
  olingan kadr «06:00 da rasta band edimi?» savoliga javob bermaydi.
"""

CAPTURE_WORKER_LOST: Final[str] = "capture_worker_lost"
"""Kadr olish boshlandi, lekin tugallanmadi — jarayon o'ldi yoki ijara tugadi."""

CAPTURE_PLAN_CREATED_LATE: Final[str] = "capture_plan_created_late"
"""Slot bozor tizimga ulangunicha o'tib ketgan edi (C9).

⚠ YAGONA `actor="none"` kodi. Bu XATO emas, TARIXIY FAKT: yangi bozor
  kunning o'rtasida ulanganda o'tib ketgan slotlar yo'qlik yozuvi oladi.
  Uni `capture_slot_missed` bilan birlashtirish yangi bozorning birinchi
  kunini «tizim ishlamadi» degan qizil hisobot bilan boshlardi.
"""

CAPTURE_SOURCE_UNREACHABLE: Final[str] = "capture_source_unreachable"
"""Manbaga (go2rtc yoki NVR) umuman ulanib bo'lmadi — tunnel yoki tarmoq."""

CAPTURE_CAMERA_OFFLINE: Final[str] = "capture_camera_offline"
"""NVR javob berdi, LEKIN kanal oflayn — kamera quvvati yoki kabeli."""

CAPTURE_BAD_CREDENTIALS: Final[str] = "capture_bad_credentials"
"""NVR login yoki parolni qabul qilmadi.

⛔ `locks_account=True`, `retry_safe=False` — modul docstringidagi
   arifmetikaga qarang. Tik bu kodda QAYTA URINMAYDI.
"""

CAPTURE_STREAM_LIMIT: Final[str] = "capture_stream_limit"
"""NVR ning bir vaqtdagi oqim chegarasi (EHTIMOL — §11.8 hedged kodi).

⚠ `defer=True`, `locks_account=False`. Kechiktirish, qulflash EMAS:
  oqim bo'shagach kadr olish muvaffaqiyatli bo'ladi.

⚠ Hedge SO'ZINING O'ZI faqat uch tildagi matnda yashaydi
  (`isapi/errors.py` ning `nvr_stream_limit` bilan bir xil qarori):
  backend hedge qilmaydi, u kod beradi.
"""

CAPTURE_TIMEOUT: Final[str] = "capture_timeout"
"""Manba ulandi, lekin kutish vaqti ichida kadr bermadi."""

CAPTURE_INVALID_RESPONSE: Final[str] = "capture_invalid_response"
"""Javob keldi, lekin ichida TASVIR YO'Q — `quality.py` uni `corrupt` dedi.

⚠ `capture_timeout` DAN AJRATILGAN: bu yerda manba javob BERDI (HTTP
  `200` bo'lishi ham mumkin), tanada esa HTML xato sahifasi, bo'sh tana
  yoki kesilgan JPEG bor. Yechim boshqa joyda — oqim sozlamasi, NVR
  firmware'i yoki tarmoq barqarorligi.
"""

CAPTURE_STORAGE_UNAVAILABLE: Final[str] = "capture_storage_unavailable"
"""Kadr OLINDI, lekin omborga yozilmadi — «yarim muvaffaqiyat» (§B.4).

⚠ Qayta urinish TO'G'RI va ARZON: kadr allaqachon olingan, faqat yuklash
  takrorlanadi. Uni `capture_source_unreachable` bilan birlashtirish
  adminni NVR ni tekshirishga yuborardi, holbuki muammo bizning
  omborimizda.
"""

CAPTURE_CREDENTIAL_UNREADABLE: Final[str] = "capture_credential_unreadable"
"""Saqlangan parolni O'QIB BO'LMADI — SHIFR KALITI mos kelmayapti.

⚠ `capture_bad_credentials` DAN AJRATISH MAJBURIY (`discovery.py:112-121`
  ning aynan takrori): birinchisi «NVR dagi parol noto'g'ri» deydi va
  admin uni qayta kiritadi; bu esa «BIZNING kalitimiz bilan muammo»
  deydi va yechim butunlay boshqa joyda (`NVR_CREDENTIAL_KEYS_RETIRED`
  rotatsiyasi). Ikkalasini birlashtirish adminni o'zi tuzata olmaydigan
  ishga yuborardi.

⚠ D-22: bu alert HECH QACHON bostirilmaydi — u o'zi tuzalmaydi.
"""


CAPTURE_ERROR_META: Final[dict[str, CaptureErrorMeta]] = {
    meta.code: meta
    for meta in (
        # ---------------------------------------------------------------
        # 1-GURUH — ORKESTRATSIYA. Sabab BIZDA, NVR da emas.
        # ---------------------------------------------------------------
        CaptureErrorMeta(CAPTURE_SLOT_MISSED, False, False, False, "platform"),
        CaptureErrorMeta(CAPTURE_WORKER_LOST, True, False, False, "platform"),
        CaptureErrorMeta(CAPTURE_PLAN_CREATED_LATE, False, False, False, "none"),
        # ---------------------------------------------------------------
        # 2-GURUH — TARMOQ va QURILMA. Qayta urinish XAVFSIZ va foydali.
        # ---------------------------------------------------------------
        CaptureErrorMeta(CAPTURE_SOURCE_UNREACHABLE, True, False, False, "admin"),
        CaptureErrorMeta(CAPTURE_CAMERA_OFFLINE, True, False, False, "admin"),
        CaptureErrorMeta(CAPTURE_TIMEOUT, True, False, False, "admin"),
        CaptureErrorMeta(CAPTURE_INVALID_RESPONSE, True, False, False, "admin"),
        # ---------------------------------------------------------------
        # 3-GURUH — AUTENTIFIKATSIYA. Qayta urinish HOLATNI O'ZGARTIRADI.
        # ---------------------------------------------------------------
        CaptureErrorMeta(CAPTURE_BAD_CREDENTIALS, False, True, False, "admin"),
        # ---------------------------------------------------------------
        # 4-GURUH — RESURS. Retry emas, KECHIKTIRISH.
        # ---------------------------------------------------------------
        CaptureErrorMeta(CAPTURE_STREAM_LIMIT, False, False, True, "admin"),
        # ---------------------------------------------------------------
        # 5-GURUH — PLATFORMA NOSOZLIGI.
        # ---------------------------------------------------------------
        CaptureErrorMeta(CAPTURE_STORAGE_UNAVAILABLE, True, False, False, "platform"),
        CaptureErrorMeta(CAPTURE_CREDENTIAL_UNREADABLE, False, False, False, "platform"),
    )
}
"""Kod -> xulq. GURUH-GURUH va tartib MA'NOLI (`NVR_ERROR_CODES` naqshi).

`set` bo'lganda guruhlash ko'rinmas bo'lib qolardi va yangi kod «qayerga
qo'shaman?» degan savolsiz oxiriga tushib ketardi.
"""

CAPTURE_ERROR_CODES: Final[tuple[str, ...]] = tuple(CAPTURE_ERROR_META)
"""O'n bitta kod — `04-UI-SPEC.md` §11.8 bilan AYNAN bir xil hajmda.

Reyestrdan HOSILA (`CAPTURE_ERROR_META` dan), qo'lda ikkinchi marta
YOZILMAGAN. Sanoq darvozasi: `test_registry_has_exactly_eleven_unique_codes`.
"""

CAPTURE_AUTH_LOCKING_CODES: Final[frozenset[str]] = frozenset(
    code for code, meta in CAPTURE_ERROR_META.items() if meta.locks_account
)
"""Tik ham, foydalanuvchi ham QAYTA URINA OLMAYDIGAN kodlar.

⚠ METADAN HOSILA (`nvr-errors.ts:139` naqshi), qo'lda sanalmagan. Qo'lda
  yozilgan nusxa jadval bilan bir kun ajralib ketardi va qoida BITTA
  yuzada qolardi.
"""

CAPTURE_DEFER_CODES: Final[frozenset[str]] = frozenset(
    code for code, meta in CAPTURE_ERROR_META.items() if meta.defer
)
"""Qatorni `failed` qilmasdan KECHIKTIRADIGAN kodlar (`locked_until`)."""

CAPTURE_JOB_ERROR_CODES: Final[frozenset[str]] = frozenset(CAPTURE_ERROR_META)
"""`app/schemas.py` bu to'plamni IMPORT qiladi (04-07), qayta yozmaydi.

Ikki nusxa bo'lganda job bazaga kod yozib, API uni tanimasdi va frontend
`errors.generic` ko'rsatib sababni yo'qotardi (§S-5).
"""


def _truncate(detail: str) -> str:
    """`error_detail` ni chegaraga qisadi (`discovery.py::_raw` naqshi)."""
    if len(detail) <= MAX_DETAIL_CHARS:
        return detail
    return detail[:MAX_DETAIL_CHARS] + "…"


class CaptureError(Exception):
    """Kadr olishning har qanday rad etilishi — BITTA sinf, `code` bilan.

    ⚠ NEGA HAR KOD UCHUN ALOHIDA SINF EMAS (`NvrError` bilan aynan bir xil
      mulohaza): chaqiruvchilarning HECH BIRI TIP bo'yicha tarmoqlanmaydi.
      Ular `code` ni oladi va uni O'ZGARTIRMASDAN uzatadi — job uni
      `capture_runs.error_code` ustuniga yozadi, API uni JSON'ga qo'yadi,
      frontend undan i18n kalitini yasaydi. Ya'ni QIYMAT chegaralardan
      o'tadi, TIP esa birinchi `json.dumps()` da yo'qoladi.

      O'n bir subclass shu sababdan faqat `except` blokida bir marta
      ishlatilardi va yangi kod qo'shilganda o'sha ro'yxatni yangilashni
      unutish JIMGINA ishlardi.

    Attributes:
        code: `CAPTURE_ERROR_CODES` dagi kod.
        detail: bitta jumlalik texnik sabab, `MAX_DETAIL_CHARS` ga qisilgan.
        meta: kodning retry siyosati — chaqiruvchi uni ISTISNODAN o'qiydi
            va reyestrga qaytib murojaat qilmaydi (aks holda `except`
            bloklaridan bittasi buni unutardi).
    """

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in CAPTURE_ERROR_META:
            # `assert` EMAS, `ValueError`: `assert` `python -O` bilan
            # o'chib ketadi va u holda allowlist aynan ishlab chiqarishda
            # jimgina yo'qolardi (`isapi/errors.py` bilan bir xil qaror).
            raise ValueError(
                f"noma'lum error_code={code!r}. Ruxsat etilganlar reyestri: "
                f"`app/services/capture_errors.py::CAPTURE_ERROR_CODES` "
                f"({len(CAPTURE_ERROR_CODES)} ta)."
            )

        self.code: str = code
        self.detail: str = _truncate(detail)
        self.meta: CaptureErrorMeta = CAPTURE_ERROR_META[code]
        super().__init__(code)

    def __repr__(self) -> str:
        return f"CaptureError(code={self.code!r}, detail={self.detail!r})"
