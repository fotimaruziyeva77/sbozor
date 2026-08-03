"""NVR xato taksonomiyasi — o'n ikki kod, IKKI iste'molchi, BITTA reyestr.

=============================================================================
NEGA REYESTR BITTA (`03-PATTERNS.md` §S-5).

Bu ro'yxatning ikkita iste'molchisi bor va ular turli qatlamlarda:

    HTTPException(detail={"error_code": ...})   -> HTTP javobi (03-07)
    nvr_discovery_runs.error_code               -> baza ustuni  (03-06)

Ularni ikki ro'yxatga bo'lish IKKI HAQIQAT MANBAI hosil qilardi: job
bazaga `nvr_clock_drift` yozib, API esa uni tanimay `errors.generic`
ko'rsatardi va nosozlik faqat foydalanuvchi ekranida ko'rinardi.
Shuning uchun reyestr shu yerda, bir joyda va IZOHDA GURUH-GURUH —
`app/schemas.py:471-510` (`MARKET_ERROR_CODES`) bilan aynan bir xil
uslub va bir xil sabab.
=============================================================================

D-02: backend **KOD** beradi, matnni frontend uch tilda chizadi. Bu modulda
foydalanuvchi matni YO'Q va bo'lmaydi — u `frontend/messages/*.json` da
(`cameras.errorCause.*`).

⚠ D-05 NING HEDGING QOIDASI HAM O'SHA TOMONDA. `nvr_stream_limit` — o'n
ikki koddan YAGONA hedged kodi (UI-SPEC §7.5), lekin hedge SO'ZINING O'ZI
faqat uch tildagi matnda yashaydi va G-3 darvozasi (03-08) uni o'sha yerda
tekshiradi. Backend hedge qilmaydi: u kod beradi va xom javobni
`detail.raw` da saqlaydi. Shu sababdan hedge so'zi bu faylda — izohda ham —
YOZILMAYDI va buni `test_backend_never_writes_the_hedge_word` qulflaydi
(u kodni izohdan ajratmaydi, va bu ataylab).
"""

from __future__ import annotations

from typing import Any, Final

from app.repositories.audit_repo import mask_sensitive

__all__ = [
    "AUTH_LOCKING_CODES",
    "ERROR_DETAIL_KEYS",
    "MAX_RAW_DETAIL_CHARS",
    "NVR_ERROR_CODES",
    "NvrError",
]


NVR_ERROR_CODES: Final[tuple[str, ...]] = (
    # ---------------------------------------------------------------
    # 1-GURUH — AUTENTIFIKATSIYA. Qayta urinish HOLATNI O'ZGARTIRADI.
    #
    # Hikvision ~5 xato urinishdan keyin hisobni 30 daqiqaga qulflaydi
    # va undan keyin TO'G'RI PAROL HAM ISHLAMAYDI (`03-RESEARCH.md` A.3).
    # Shuning uchun bu uchtasi `AUTH_LOCKING_CODES` ga ham kiradi va
    # ularda retry ham (backend), retry affordansi ham (frontend) YO'Q.
    # ---------------------------------------------------------------
    "nvr_bad_credentials",
    "nvr_account_locked",
    "nvr_user_no_permission",
    # ---------------------------------------------------------------
    # 2-GURUH — SOZLAMA. Qayta urinish XAVFSIZ va foydali.
    #
    # Uchalasining sababi ham NVR interfeysida yoki tarmoqda tuzatiladi
    # (NTP yoqish, Web-auth rejimini `digest/basic` ga qo'yish). Qayta
    # tekshirish hech qanday hisoblagichni oshirmaydi: `nvr_clock_drift`
    # umuman rekvizit yubormasdan aniqlanadi.
    # ---------------------------------------------------------------
    "nvr_clock_drift",
    "nvr_digest_stale",
    "nvr_auth_mode_basic_only",
    # ---------------------------------------------------------------
    # 3-GURUH — TARMOQ va QURILMA.
    #
    # `channel_offline` bu guruhda ATAYIN: u BLOK EMAS (UI-SPEC §7.3 —
    # «qator badge'i»). Kashfiyot u tufayli TO'XTAMAYDI va kamera yozuvi
    # BARIBIR yaratiladi (SC#2). U reyestrda, chunki u ham sabab kodi va
    # frontend uni ham uch tilda chizadi.
    # ---------------------------------------------------------------
    "nvr_unreachable",
    "nvr_isapi_unavailable",
    "nvr_tls_untrusted",
    "device_not_supported",
    "nvr_stream_limit",
    "channel_offline",
)
"""SC#3 ning butun shartnomasi: «ulanmadi» QABUL QILINMAYDI, sabab kod bilan keladi.

⚠ Ro'yxat TARTIBLANGAN (`tuple`, `frozenset` emas) va tartib ma'noli:
guruhlar yuqoridagi izohlar bilan mos keladi. `set` bo'lganda guruhlash
ko'rinmas bo'lib qolardi va yangi kod «qayerga qo'shaman?» degan savolsiz
oxiriga tushib ketardi.
"""


AUTH_LOCKING_CODES: Final[frozenset[str]] = frozenset(
    {
        "nvr_bad_credentials",
        "nvr_account_locked",
        "nvr_user_no_permission",
    }
)
"""UI-SPEC §4.4 ning BACKEND tomoni: bu kodlarda «Qayta urinish» affordansi YO'Q.

Qoida bitta jumlada: *tugma faqat qayta urinish HOLATNI O'ZGARTIRMAYDIGAN
hollarda ko'rinadi.* Autentifikatsiya urinishi qurilmadagi qulflash
hisoblagichini oshiradi, ya'ni u holatni o'zgartiradi — shuning uchun
frontend u yerda tugmani RENDER QILMAYDI (yashirmaydi: u umuman yo'q).

⚠ Bu to'plam `NVR_ERROR_CODES` ning QISM TO'PLAMI bo'lishi shart va buni
test qulflaydi. Aks holda frontend hech qachon kelmaydigan kod uchun
qoida saqlab yurardi.
"""


ERROR_DETAIL_KEYS: Final[frozenset[str]] = frozenset(
    {
        # `nvr_clock_drift` — «NVR soati {N} daqiqa farq qilyapti»
        "drift_seconds",
        "device_time",
        "server_time",
        # `nvr_account_locked` — «Qulf {time} dan keyin ochiladi» taymeri
        "unlock_at",
        # `channel_offline` — «Kanal {N} ({nom}) oflayn»
        "channel_no",
        "channel_name",
        # `device_not_supported` — «Bu qurilma qo'llab-quvvatlanmaydi ({model})»
        "model",
        # Xom javob — `<details>` ichida, YOPIQ, `font-mono`, matn sifatida
        "raw",
    }
)
"""UI-SPEC §7.4 [TALAB]: UI FAQAT shu kalitlarni chizadi.

Noma'lum kalit UI'da RENDER QILINMAYDI — ya'ni backend ro'yxatdan tashqari
kalit yozsa u foydalanuvchiga YETIB BORMAYDI. Bu ataylab shunday: xom
`detail` ni ko'r-ko'rona chizish 02-fazadagi T-02-99 ning (stack izi yoki
SQL matni foydalanuvchiga chiqishi) aynan takrori bo'lardi.

⚠ SHU SABABDAN cheklov KONSTRUKTORDA majburlanadi (pastga qarang). Faqat
hujjatda qolgan allowlist — bu jimgina MA'LUMOT YO'QOTISH: backend kalit
yozadi, hech kim xato qilmaganday ko'rinadi, foydalanuvchi esa uni hech
qachon ko'rmaydi va sabab hech qayerda yozilmaydi (T-03-32).
"""


MAX_RAW_DETAIL_CHARS: Final[int] = 4000
"""`detail["raw"]` ning yuqori chegarasi — UI ning 2000 belgisidan KATTA, ataylab.

UI 2000 belgidan kesadi (UI-SPEC §7.4). Backend chegarasi undan kattaroq,
chunki xom javob `nvr_discovery_runs.error_detail` (jsonb) ga ham tushadi
va u yerda texnik yordam uchun biroz ko'proq kontekst foydali. Lekin
CHEKSIZ emas: buzilgan yoki soxta NVR megabaytlab javob yuborishi mumkin
va u bazaga tushmasligi kerak (T-03-30).
"""


class NvrError(Exception):
    """NVR bilan ishlashning har qanday rad etilishi — BITTA sinf, `code` bilan.

    ⚠ NEGA HAR KOD UCHUN ALOHIDA SINF EMAS (o'n ikki subclass):

    Chaqiruvchilarning HECH BIRI tip bo'yicha tarmoqlanmaydi. Ular
    `code` ni oladi va uni O'ZGARTIRMASDAN uzatadi: job uni
    `nvr_discovery_runs.error_code` ustuniga yozadi, API uni JSON'ga
    qo'yadi, frontend undan i18n kalitini yasaydi. Ya'ni qiymat
    chegaralardan o'tadi, TIP esa o'tmaydi — birinchi `json.dumps()` da
    u yo'qoladi.

    O'n ikki subclass shu sababdan faqat `except` blokida bir marta
    ishlatilardi (`except (NvrBadCredentials, NvrAccountLocked, ...)`) va
    yangi kod qo'shilganda o'sha ro'yxatni yangilashni unutish JIMGINA
    ishlardi. Bitta sinf + tekshiriladigan `code` esa reyestrni yagona
    haqiqat manbai qilib qoldiradi.

    Attributes:
        code: `NVR_ERROR_CODES` dagi kod. Mashina uchun BARQAROR.
        detail: `ERROR_DETAIL_KEYS` bilan CHEKLANGAN kontekst.
    """

    def __init__(self, code: str, detail: dict[str, Any] | None = None) -> None:
        if code not in NVR_ERROR_CODES:
            raise ValueError(
                f"noma'lum error_code={code!r}. Ruxsat etilganlar reyestri: "
                f"`app/services/isapi/errors.py::NVR_ERROR_CODES` ({len(NVR_ERROR_CODES)} ta)."
            )

        payload = dict(detail or {})
        unknown = set(payload) - ERROR_DETAIL_KEYS
        if unknown:
            # `assert` EMAS, `ValueError`: `assert` `python -O` bilan
            # o'chib ketadi va u holda allowlist ishlab chiqarishda
            # jimgina yo'qolardi — ya'ni himoya aynan kerak bo'lgan
            # muhitda bo'lmasdi.
            raise ValueError(
                f"`detail` da ruxsat etilmagan kalit(lar): {sorted(unknown)}. "
                f"UI faqat {sorted(ERROR_DETAIL_KEYS)} ni chizadi (UI-SPEC §7.4), "
                "ya'ni boshqa kalit foydalanuvchiga YETIB BORMAYDI."
            )

        raw = payload.get("raw")
        if isinstance(raw, str) and len(raw) > MAX_RAW_DETAIL_CHARS:
            payload["raw"] = raw[:MAX_RAW_DETAIL_CHARS] + "…"

        # ⚠ `mask_sensitive` KALIT NOMIGA qaraydi (`audit_repo.py:106-121`),
        #   ya'ni u `{"password": ...}` ni maskalaydi, lekin `raw` ICHIDAGI
        #   matnni O'QIMAYDI. Bu chegara ochiq: xom XML matnidagi hech narsa
        #   maskalanmaydi. Himoya u yerda boshqa manbadan keladi — ISAPI
        #   javoblari rekvizitni QAYTARMAYDI (ular `Authorization` ni
        #   takrorlamaydi) va uzunlik yuqorida kesilgan. Filtr baribir
        #   qo'llanadi, chunki `detail` kelajakda ichma-ich obyekt olishi
        #   mumkin va o'shanda u ishlaydi (T-03-32, §S-7).
        masked: dict[str, Any] = mask_sensitive(payload)

        self.code: str = code
        self.detail: dict[str, Any] = masked
        super().__init__(code)

    def __repr__(self) -> str:
        return f"NvrError(code={self.code!r}, detail={self.detail!r})"
