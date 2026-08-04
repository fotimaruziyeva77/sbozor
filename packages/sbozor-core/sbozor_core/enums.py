"""SBOZOR domen enum'lari — uch servis uchun yagona haqiqat manbai.

Qiymatlar DB'da matn sifatida saqlanadi va JWT/JSON orqali frontend'ga
uzatiladi. Ya'ni ular BARQAROR KONTRAKT: a'zo NOMINI o'zgartirish arzon,
QIYMATINI o'zgartirish esa migratsiya + token bekor qilish talab qiladi.

`StrEnum` (Python 3.11+) tanlandi: a'zo to'g'ridan-to'g'ri `str` bo'lib
ishlaydi, shuning uchun SQLAlchemy parametrlariga, `json.dumps` ga va JWT
claim'lariga qo'shimcha konversiyasiz uzatiladi.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "ActorKind",
    "AlertSeverity",
    "AuditAction",
    "AuditSource",
    "CameraStatus",
    "CaptureMethod",
    "CaptureRunStatus",
    "DiscoveryRunStatus",
    "Locale",
    "Role",
    "SnapshotLightMode",
    "SnapshotQuality",
    "SnapshotTier",
    "StallStatus",
]


class Role(StrEnum):
    """Panel rollari — AYNAN beshta (D-05: foydalanuvchida rollar TO'PLAMI).

    Sotuvchi (`vendor`) roli bu yerda ATAYIN YO'Q: sotuvchi veb-panelga
    umuman kirmaydi, u Telegram-bot identifikatori bo'lib, 7-fazadagi
    `vendors` jadvali bilan keladi. Uni shu enum'ga qo'shish "sotuvchi ham
    panel foydalanuvchisi" degan noto'g'ri modelni tug'diradi.
    """

    PLATFORM_ADMIN = "platform_admin"
    DIRECTOR = "director"
    MARKET_ADMIN = "market_admin"
    CASHIER = "cashier"
    INSPECTOR = "inspector"


class Locale(StrEnum):
    """Qo'llab-quvvatlanadigan tillar (D-13 — foydalanuvchi profilida saqlanadi).

    Qiymatlar `frontend/src/i18n/routing.ts` dagi `locales` ro'yxati va
    `frontend/messages/<locale>.json` fayl nomlari bilan AYNAN mos.
    URL prefikslari (`/uz`, `/uz-cyrl`, `/ru`) esa boshqa narsa — ular faqat
    frontend marshrutlashda yashaydi va bu yerga chiqmaydi.
    """

    UZ_LATN = "uz-Latn"
    UZ_CYRL = "uz-Cyrl"
    RU = "ru"


class StallStatus(StrEnum):
    """`stalls.status` qiymatlari — AYNAN uchta (2-faza A4 taxmini).

    Qiymatlar DB KONTENTI va ATAYIN BITTA TILDA (1-faza D-16): ular
    `stalls.status` ustunida matn sifatida yashaydi va `STALL_STATUS_CHECK`
    konstraytiga aynan shu ro'yxatdan hosil qilinadi. UI ularni tarjima
    QILMAYDI — u `stalls.status.*` i18n kalitlari orqali uch tilda
    ko'rsatadi (`stalls.status.active` va h.k.), ya'ni tilni almashtirish
    DB qiymatiga hech qachon tegmaydi.

    A4 TAXMINI — QIYMATLARNING MAZMUNI (6-faza billing kontrakti):
    `closed` va `maintenance` rastalarga kunlik hisob YOZILMAYDI. Bu
    keyinroq qo'shiladigan filtr emas, holatlarning O'Z ma'nosi: rasta
    "yopiq" deb belgilangani — "bu kun uchun pul talab qilinmaydi" degani.
    Shuning uchun yangi holat qo'shish 6-fazadagi hisob filtrini jimgina
    o'zgartiradi va `tests/unit/test_enums.py::
    test_stall_status_has_exactly_three_states` ataylab qizaradi.

    `active`      — rasta ishlaydi, hisob yoziladi
    `maintenance` — vaqtincha ta'mirda; hisob YO'Q
    `closed`      — foydalanishdan chiqarilgan; hisob YO'Q. Qator
                    O'CHIRILMAYDI (kod reyestri va tarix saqlanadi, D-02).
    """

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


class CameraStatus(StrEnum):
    """`cameras.status` qiymatlari — AYNAN uchta (3-faza, `03-RESEARCH.md` E.15).

    Qiymatlar DB KONTENTI va ATAYIN BITTA TILDA (`StallStatus` bilan bir xil
    qoida): ular `cameras.status` ustunida matn sifatida yashaydi va audit
    triggeri (`fn_audit_row()`) ularni `audit_log.new_value` ga TO'G'RIDAN-
    TO'G'RI yozadi. Ya'ni qiymat o'zgarishi audit tarixini ikkiga bo'lardi —
    eski qatorlar eski matn bilan qolardi va "kamera qachon offline bo'ldi"
    savoliga ikki xil kalit bilan javob berishga to'g'ri kelardi.

    UI ularni tarjima QILMAYDI — u `nvr.camera.status.*` i18n kalitlari
    orqali uch tilda ko'rsatadi (CLAUDE.md "3 til majburiy").

    `unknown` ALOHIDA HOLAT va u `offline` ning sinonimi EMAS:
      `online`  — kashfiyot kanalni topdi va u ishlayapti;
      `offline` — kanal RO'YXATDA bor, lekin javob bermayapti (D-10 bo'yicha
                  qator O'CHIRILMAYDI — 4-fazadagi snapshotlar va 5-fazadagi
                  zonalar `cameras.id` ga bog'lanadi);
      `unknown` — kanal yozildi, lekin holati HALI o'lchanmagan. Boshlang'ich
                  qiymat aynan shu: `offline` ni standart qilish "kamera
                  buzuq" degan YOLG'ON dalilni birinchi skandan oldin
                  yozardi.
    """

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class DiscoveryRunStatus(StrEnum):
    """`nvr_discovery_runs.status` qiymatlari — AYNAN to'rtta (3-faza).

    Qiymatlar DB KONTENTI: `nvr_discovery_runs.status` ustunida matn sifatida
    yashaydi va `0012_nvr_domain` dagi QISMAN UNIQUE indeksning predikati
    (`status IN ('queued','running')`) AYNAN shu ikkitasiga tayanadi. Ya'ni
    a'zo qiymatini o'zgartirish migratsiya talab qiladi — indeks predikati
    jimgina hech nimani qamramay qolardi va bir NVR uchun ikkita parallel
    kashfiyot bloklanmasdi (T-03-16).

    `queued` va `running` — "FAOL" to'plami; `succeeded` va `failed` —
    yakunlangan. Bo'linish qasddan ikkita qiymatga tayanadi, bitta
    `is_finished` bayrog'iga emas: navbatda turgan va ishlayotgan yugurish
    operator uchun boshqa-boshqa holat, lekin ikkinchi skanni IKKALASI ham
    bloklashi kerak.
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CaptureRunStatus(StrEnum):
    """`capture_runs.status` qiymatlari — AYNAN oltita (4-faza, `04-RESEARCH.md` §A.2).

    Qiymatlar DB KONTENTI va ATAYIN BITTA TILDA (`CameraStatus` bilan bir xil
    qoida): ular `capture_runs.status` ustunida matn sifatida yashaydi va
    `0014_snapshot_domain` dagi IKKALA qisman indeksning predikati ham AYNAN
    shu a'zolardan HOSILA. Qiymatni o'zgartirish migratsiya talab qiladi —
    indeks predikati jimgina hech nimani qamramay qolardi va muddati kelgan
    slotlar tanlanmasdan, watchdog esa osilib qolgan qatorlarni ko'rmasdan
    qolardi.

    ⚠ `missed` VA `failed` NI ARALASHTIRMANG — bu enum'ning eng qimmat
    qarori (`04-RESEARCH.md` §B.5):

      `missed` — «BIZNING tizimimiz ishlamadi». Slot uchun kadr olish hech
                 qachon boshlanmadi: planer, worker yoki butun stek o'lik
                 edi. Muammo BIZDA.
      `failed` — «NVR javob bermadi». Kadr olish HAQIQATAN urinildi va
                 `error_code` sababni aytadi (tarmoq, autentifikatsiya,
                 sessiya chegarasi). Muammo DALADA.

    Ikkalasini bitta kodga yig'ish dala diagnostikasini o'ldiradi: «bugun 12
    slot yiqildi» xabari operatorga nima qilishni aytmasdi — VPS'ga qarash
    kerakmi yoki bozorga borish kerakmi. Aynan shu farq `04-UI-SPEC.md`
    §6.4 dagi C5/C6 ikonkalarining ikki xilligining sababi ham.

    `skipped` UCHINCHI, ALOHIDA holat va u `missed` ning sinonimi EMAS:
    bozor kun o'rtasida faollashtirilganda o'sha kunning o'tib ketgan
    slotlari `skipped` (`capture_plan_created_late`) bo'lib tug'iladi va
    ALERT BERMAYDI. Ularni `missed` qilish platforma adminiga birinchi
    kunidayoq beshta soxta alert yuborardi va u alertga ishonishni
    to'xtatardi (`04-RESEARCH.md` §B.5).

    `pending`   — reja qatori yozilgan, vaqti hali kelmagan yoki navbatda
    `running`   — worker ijara (lease) oldi va kadr olyapti
    `succeeded` — kadr olindi va omborga yozildi (`snapshot_id` to'ldirilgan)
    `failed`    — urinildi, NVR/tarmoq javob bermadi (`error_code` bor)
    `missed`    — hech qachon urinilmadi, grace oynasi o'tdi (BIZNING nosozlik)
    `skipped`   — ataylab o'tkazib yuborildi (reja kech tuzildi)
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    MISSED = "missed"
    SKIPPED = "skipped"


class SnapshotQuality(StrEnum):
    """`snapshots.quality_verdict` qiymatlari — AYNAN to'rtta (D-14/D-16).

    ⚠ BU ENUM BILLING KAFOLATINING KIRISHI. `snapshots.is_billable`
    `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED`, ya'ni `'ok'`
    LITERALI sxemaga qadalgan. A'zoning QIYMATINI o'zgartirish generated
    ifodani ham o'zgartirishni talab qiladi — bu jadvalni qayta yozadigan
    migratsiya, «bir satrlik tuzatish» emas.

    Verdikt YOZISH PAYTIDA qo'yiladi va hech qachon qayta hisoblanmaydi
    (T-04-23): chegara to'plami `quality_thresholds_version` da qayd
    etiladi. Aks holda chegarani sozlash o'tmishdagi kadrlarning billing
    yaroqliligini RETROAKTIV o'zgartirardi.

    `ok`      — kadr yaroqli; `is_billable = true` va 5-faza unga bandlik
                dalilini bog'lay OLADI
    `dark`    — IKKI SHARTLI qoida bo'yicha qorong'i (`mean < X` VA
                `stddev < Y`, D-14). Faqat o'rtachaga tayangan qoida
                qonuniy qish-tong kadrlarini oylab jimgina tashlardi
    `blank`   — tuzilmasiz, bir tekis kadr (obyektiv yopilgan, signal yo'q)
    `corrupt` — dekodlanmadi yoki kesilgan (`OSError: Truncated File Read`)
    """

    OK = "ok"
    DARK = "dark"
    BLANK = "blank"
    CORRUPT = "corrupt"


class SnapshotLightMode(StrEnum):
    """`snapshots.light_mode` qiymatlari — AYNAN to'rtta (D-12).

    ⚠ `quality_verdict` NING DUBLIKATI EMAS va bu ATAYIN (D-12: «superset»).
    Ikki savol butunlay boshqa:

      `quality_verdict` — «bu kadrni ISHLATSA bo'ladimi?» (billing qarori)
      `light_mode`      — «bu kadr QANDAY yorug'likda olingan?» (kontekst)

    Qonuniy IR-tungi kadr `quality_verdict='ok'` VA `light_mode='ir_night'`
    bo'lishi mumkin — ya'ni u to'liq yaroqli, lekin 5-fazadagi detektor
    uchun boshqa ishonch darajasiga ega. Ikkalasini bitta ustunga yig'ish
    `dark` ni «yaroqsiz» va «tungi» ma'nolarini birlashtirib, 5-fazada
    fine-tuning to'plamini tanlashni imkonsiz qilardi (narxi ~15 qator).

    `day`       — kunduzgi yorug'lik
    `low_light` — tong/shom, rangli lekin past yorug'lik
    `ir_night`  — IR yorituvchi yoqilgan (deyarli monoxrom — `quality_saturation`)
    `unknown`   — o'lchash imkoni bo'lmadi (kadr buzuq yoki metrika yo'q)
    """

    DAY = "day"
    LOW_LIGHT = "low_light"
    IR_NIGHT = "ir_night"
    UNKNOWN = "unknown"


class SnapshotTier(StrEnum):
    """`snapshots.storage_tier` qiymatlari — AYNAN uchta (D-18, CAM-07).

    ⚠ UCHINCHI A'ZO (`purged`) MAJBURIY va u «kelajak uchun zaxira» EMAS.
    `04-RESEARCH.md` §B.4 ikkitasini sanaydi, §D.10 esa uchtasini — va
    uchtalik to'g'ri, chunki saqlash siyosati 455 kundan keyin OBYEKTNI
    o'chiradi, QATORNI esa qoldiradi:

        0–90 kun    `full`        — original JPEG
        91–455 kun  `compressed`  — qayta kodlangan, AYNAN O'SHA kalit
        455+ kun    `purged`      — obyekt o'chirildi, qator qoldi

    Qatorning qolishi 6-fazaning talabi: `daily_charges` dalil-kadrga
    bog'lanadi (BILL-02), ya'ni `snapshots` qatorini o'chirish hisob
    yozuvining dalil havolasini uzardi. `purged` qator «kadr mavjud edi,
    arxivdan chiqarildi» deb HALOL ko'rsatiladi (`object_deleted_at` sana
    beradi) va `is_billable` O'ZGARMAYDI — o'sha paytda qilingan hisob
    retroaktiv bekor qilinmaydi.

    ⚠ O'TISH BIR YO'NALISHLI: `full` -> `compressed` -> `purged`. Retention
    jobi `WHERE storage_tier = 'full'` bilan filtrlanadi, aks holda bir
    xil kadr har kuni qayta kodlanib avlod yo'qotishi to'planardi va dalil
    bir yildan keyin o'qib bo'lmas holga kelardi (Pitfall 13).
    """

    FULL = "full"
    COMPRESSED = "compressed"
    PURGED = "purged"


class AlertSeverity(StrEnum):
    """`alert_events.severity` qiymatlari — AYNAN uchta (D-22).

    Daraja ESKALATSIYA o'qi, chastota emas (`04-RESEARCH.md` §E.13):
    muammo davom etsa xabar CHASTOTASI oshmaydi, uning DARAJASI oshadi
    (1-soat `warning`, 3-soat `critical`). Teskarisi — takroriy xabar
    yuborish — alert kanalini birinchi haftadayoq o'ldirardi.

    `info`     — kuzatuv uchun; Telegram'ga chiqmasligi mumkin
    `warning`  — e'tibor talab qiladi, lekin bozor hali ishlayapti
    `critical` — kunlik hisobning asosi yo'qolyapti (bozor ko'r bo'ldi,
                 backup eskirdi, hisob qulflandi) — HECH QACHON bo'g'ilmaydi
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CaptureMethod(StrEnum):
    """Kadr olish YO'LI — AYNAN uchta (D-06/D-07).

    Qiymat UCH JOYDA yashaydi va uchalasi ham bitta CHECK ifodasidan
    oziqlanadi: `nvr_devices.capture_method` (SOZLAMA — qaysi yo'l
    ishlatiladi), `capture_runs.capture_method` va
    `snapshots.capture_method` (DALIL — qaysi yo'l HAQIQATAN ishladi).
    Sozlama va dalilni ajratish majburiy: fallback ishga tushganda
    ikkalasi FARQ qiladi va aynan shu farq dala diagnostikasining
    birinchi savoliga javob beradi.

    ⚠ `isapi` — «zaxira» EMAS, u SESSIYA BOSIMIDA ENG XAVFSIZ yo'l (D-07):
    ISAPI `/picture` NOL RTSP sessiyasi ochadi, go2rtc esa sessiyani ochiq
    ushlab turadi. Hikvision NVR'ining o'lchanmagan sessiya chegarasiga
    yaqinlashganda tanlov ataylab `isapi` ga o'tkaziladi — ya'ni ro'yxat
    tartibi ustuvorlik emas, u shunchaki uchta imkoniyat.

    `go2rtc` — `/api/frame.jpeg`, standart (jonli ko'rish bilan bir xil komponent)
    `isapi`  — Hikvision `/ISAPI/Streaming/channels/<ch>01/picture`, nol sessiya
    `ffmpeg` — bir martalik RTSP handshake, oxirgi chora va diagnostika
    """

    GO2RTC = "go2rtc"
    ISAPI = "isapi"
    FFMPEG = "ffmpeg"


class AuditAction(StrEnum):
    """`audit_log.action` qiymatlari.

    DB-trigger `lower(TG_OP)` yozadi, shuning uchun `insert`/`update`/`delete`
    KICHIK harfda bo'lishi shart — aks holda ilova yozgan va trigger yozgan
    qatorlar bir xil hisobotda ikki xil qiymat bo'lib ko'rinadi.
    """

    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    MARKET_SELECTED = "market_selected"
    # S105 — bular audit HODISASI nomlari, sir emas: `audit_log.action`
    # ustuniga yoziladigan qiymatlar. Hech qanday parol saqlanmaydi.
    PASSWORD_RESET = "password_reset"  # noqa: S105
    PASSWORD_CHANGED = "password_changed"  # noqa: S105
    USER_BLOCKED = "user_blocked"
    USER_UNBLOCKED = "user_unblocked"
    REFRESH_REUSE_DETECTED = "refresh_reuse_detected"


class AuditSource(StrEnum):
    """`audit_log.source` — yozuvni kim qo'ygani.

    `db_trigger` yozuvlari xom SQL yo'lini ham qamraydi (D-10); `app`
    yozuvlari esa DB o'zgarishi bo'lmagan hodisalar uchun (login, logout,
    bozor tanlash, o'qish auditi).
    """

    DB_TRIGGER = "db_trigger"
    APP = "app"


class ActorKind(StrEnum):
    """`app.actor_kind` GUC'i va `audit_log.actor_kind` ustuni.

    Fon jarayonlari (billing tick, snapshot pipeline) `system` bilan yozadi —
    shunda "kim o'zgartirdi?" savoliga javob hech qachon bo'sh bo'lmaydi.
    """

    USER = "user"
    SYSTEM = "system"
