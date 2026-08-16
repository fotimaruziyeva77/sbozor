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
    "AdjustmentDirection",
    "AdjustmentReason",
    "AlertSeverity",
    "AnomalyKind",
    "AuditAction",
    "AuditSource",
    "CameraStatus",
    "CaptureMethod",
    "CaptureRunStatus",
    "DiscoveryRunStatus",
    "Locale",
    "MapDayState",
    "OccupancyVerdict",
    "OutboxKind",
    "OutboxRecipientKind",
    "OutboxStatus",
    "PaymentKind",
    "PaymentMethod",
    "ReconciliationCaseStatus",
    "ReconciliationSubjectKind",
    "ResolutionSource",
    "ReversalReason",
    "ReviewPurpose",
    "ReviewQueueKind",
    "Role",
    "ShiftStatus",
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


class OccupancyVerdict(StrEnum):
    """`occupancy_events.verdict` qiymatlari — AYNAN uchta (5-faza, D-11/D-12).

    Qiymatlar DB KONTENTI va ATAYIN BITTA TILDA (`CaptureRunStatus` bilan bir
    xil qoida): ular `occupancy_events.verdict` ustunida matn sifatida
    yashaydi va `0018_occupancy_domain` dagi qisman indeksning predikati
    (`verdict = 'uncertain'`) AYNAN shu a'zodan HOSILA. Qiymatni o'zgartirish
    migratsiya talab qiladi — indeks jimgina hech nimani qamramay qolardi va
    noaniq navbat to'liq skanga o'tardi.

    ⚠ `uncertain` — «MODEL BILMAYDI», «rasta yarim band» EMAS. U ikki
    chegara orasidagi confidence oynasi (D-11) va uning YAGONA ma'nosi —
    «bu zona INSON ko'zini talab qiladi». Chegaralar `thresholds_version`
    bilan QATORDA yashaydi, ya'ni ularni sozlash migratsiya emas, `UPDATE`.

    ⚠ TASDIQLANMAGAN `uncertain` KUN OXIRIDA «BO'SH» BO'LADI (AI-06/D-19),
    LEKIN QATORNING O'ZI O'ZGARMAYDI: hukm `stall_slot_occupancy` ga
    `resolution_source = 'default_empty'` bilan yoziladi va hisobotda
    ALOHIDA belgi oladi. Ya'ni «hech kim qaramadi» jimgina «bo'sh» ga
    aylanmaydi — bu farq hisobotdan o'chib ketsa nazoratning yo'qligi
    yaxshi natijaga o'xshab qolardi.

    `occupied`  — zonada savdo bor; kunlik patta hisobiga kiradi
    `empty`     — zona bo'sh
    `uncertain` — ishonch chegaralari orasida; nazoratchi navbatiga tushadi
    """

    OCCUPIED = "occupied"
    EMPTY = "empty"
    UNCERTAIN = "uncertain"


class ReviewQueueKind(StrEnum):
    """`review_assignments.queue_kind` — AYNAN ikkita navbat (D-13/D-17).

    Ikki navbat IKKI XIL SAVOLGA javob beradi va ularni aralashtirish
    aniqlik hisobotini jimgina shishirardi:

      `uncertain`   — «modelni TUZAT»: faqat model ikkilangan zonalar. Bu
                      TANLANGAN (biased) namuna — undagi to'g'rilik foizi
                      modelning umumiy aniqligi EMAS.
      `blind_audit` — «modelni O'LCHA»: kunlik `frame` dan HOSILA URUG' bilan
                      tortilgan xolis namuna (D-13: 30 band/kun). Nazoratchi
                      AI javobini KO'RMAYDI, ya'ni javob ankorlanmaydi.

    ⚠ TARTIB MAJBURIY (`05-RESEARCH.md` §C.8.3): avval ko'r audit namunasi
    tortiladi, KEYIN noaniq navbat quriladi. Teskari tartibda audit doirasi
    «noaniq» lardan tozalangan bo'lardi va o'lchangan aniqlik sun'iy
    ko'tarilardi.

    ⚠ QIYMAT SXEMAGA QADALGAN: `zone_reviews` dagi
    `CHECK (queue_kind <> 'blind_audit' OR shown_ai_verdict = false)`
    aynan shu literalga tayanadi (D-17.3).
    """

    UNCERTAIN = "uncertain"
    BLIND_AUDIT = "blind_audit"


class ReviewPurpose(StrEnum):
    """`review_assignments.purpose` — javob NIMAGA ishlatilishi (D-14, 70/30).

    ⚠ TORTISH PAYTIDA belgilanadi, javob kelganda EMAS. Sabab bitta va u
    D-14 ning butun mazmuni: agar bo'linish keyin qilinsa, kimdir (yoki
    kelajakdagi kod) «yaxshi» javoblarni `eval` ga, «yomon» larini `train`
    ga surib qo'yishi mumkin bo'lardi — ya'ni aniqlik hisoboti o'z
    namunasini o'zi tanlardi.

    `eval`  — XOLIS o'lchov namunasi. Aniqlik hisoboti FAQAT shundan
              hisoblanadi va bu qatorlar hech qachon o'qitishga bermaydi.
    `train` — kelajakdagi krop-klassifikator (`timm`, §E.15) uchun yorliq.
              Noaniq navbatning BARCHA javoblari shu yerga tushadi: ular
              tanlangan namuna, ya'ni ular bilan o'lchash aniqlikni
              shishirardi.

    Ya'ni `eval` FAQAT `queue_kind = 'blind_audit'` bilan birga bo'la oladi
    va bu `review_assignments` da `CHECK` bilan qulflangan — konventsiya
    emas, sxema.
    """

    EVAL = "eval"
    TRAIN = "train"


class ResolutionSource(StrEnum):
    """`stall_slot_occupancy.resolution_source` — hukm QAYERDAN keldi (AI-05/AI-06).

    ⚠ BU USTUN «QO'SHIMCHA METAMA'LUMOT» EMAS — u D-19 va D-22 ning
    bajarilish mexanizmi. Usiz uch butunlay boshqa holat hisobotda BIR XIL
    ko'rinardi: «model bo'sh dedi», «hech kim qaramadi, standart bo'sh» va
    «bu rastani birorta kamera ko'rmaydi».

    `ai`            — model verdikti to'g'ridan-to'g'ri qabul qilindi
    `human`         — nazoratchi javobi modelnikini ALMASHTIRDI (D-12: AI
                      qatori TAHRIRLANMAYDI, inson javobi ALOHIDA qator)
    `default_empty` — `uncertain` kun oxirigacha tasdiqlanmadi (AI-06/D-19).
                      ⛔ `zone_reviews` ga SOXTA qator YOZILMAYDI: tizim
                      «nazoratchi buni bo'sh deb tasdiqladi» deb yolg'on
                      gapirardi va o'sha yolg'on keyin trening datasetiga
                      tushardi.
    `no_coverage`   — rastani birorta kamera zonasi qamramaydi (D-22). Bu
                      «bo'sh» EMAS va hech qachon «bo'sh» hisoblagichiga
                      qo'shilmaydi — qamrovsiz rasta jimgina yo'qotishga
                      aylanardi.
    """

    AI = "ai"
    HUMAN = "human"
    DEFAULT_EMPTY = "default_empty"
    NO_COVERAGE = "no_coverage"


class PaymentKind(StrEnum):
    """`payments.kind` — qator TO'LOVMI yoki uning BEKORIMI (D-23).

    `payments` APPEND-ONLY: o'chirish ham, tahrirlash ham yo'q. Xato yozuv
    `reversal` qatori bilan qoplanadi va u `reverses_payment_id` orqali asl
    qatorga bog'lanadi. Qoldiq — belgili summalarning YIG'INDISI.

    ⛔ Ekranda «storno» so'zi ISHLATILMAYDI (§13.1): kassir qilayotgan
    ishning nomi «bekor qilish». Kod nomi shu yerda `reversal` bo'lib
    QOLADI — atama ajralishi ATAYIN va u §13.1 jadvalida reyestrga olingan.
    """

    PAYMENT = "payment"
    REVERSAL = "reversal"


class PaymentMethod(StrEnum):
    """`payments.method` — naqd yoki terminal (CASH-01).

    ⛔ UCHINCHI TUR YO'Q. QR / bank o'tkazmasi + referens `V2-CASH-03` da va
    u UMUMAN BOSHQA maydonlar to'plamini (referens raqami, UzQR solishtiruvi,
    hisob-kitob kuni) talab qiladi. Bugundan `transfer` a'zosini qo'shish
    kassirga referenssiz «o'tkazma» yozish yo'lini ochardi — ya'ni nizoda
    HECH QANDAY dalil qoldirmaydigan to'lov turi.
    """

    CASH = "cash"
    TERMINAL = "terminal"


class AdjustmentDirection(StrEnum):
    """`charge_adjustments.direction` — tuzatish hisobni oshiradimi/kamaytiradimi.

    ⛔ BELGILI SUMMA EMAS, KATTALIK + YO'NALISH (C-5). Sabab o'lchanadigan:
    belgili `BIGINT` da «-15000» ni yozgan odam «15000 qaytarildi» ni ham,
    «15000 kamaytirildi» ni ham nazarda tutgan bo'lishi mumkin va hisobot
    ikkalasini BIR XIL guruhga qo'shardi. Yo'nalish alohida ustun bo'lganda
    esa «qancha qo'shildi» va «qancha kamaytirildi» ikki MUSTAQIL yig'indi.

    Ekranda: «Qo'shildi» / «Kamaytirildi» (§13.4).
    """

    INCREASE = "increase"
    DECREASE = "decrease"


class AdjustmentReason(StrEnum):
    """`charge_adjustments.reason` — YOPIQ sabab-kod ro'yxati (D-19).

    =========================================================================
    ⛔ `other` / `custom` A'ZOSI YO'Q va bu ro'yxatning butun qiymati.

    Erkin matn (yoki uni qaytarib keltiradigan `other` a'zosi) ikki narsani
    birdan buzardi: (1) hisobotda guruhlanmaydi — «boshqa» AMALDA eng katta
    guruh bo'lib qolardi va tuzatishlarning haqiqiy sababi hech qachon
    o'lchanmasdi; (2) D-19 ning maqsadi — summani o'zgartirishni ATAYIN
    QIMMAT qilish — bekor bo'lardi: bitta bo'sh maydon har qanday
    o'zgartirishni oqlab yuborardi.

    Ro'yxat kengaytirilishi MUMKIN, lekin faqat NOMLANGAN a'zo bilan va
    o'shanda uchala locale ham `billing-copy.test.mjs` (G-24) darvozasida
    to'plam TENGLIGI bo'yicha tekshiriladi.
    =========================================================================
    """

    LATE_REVIEW = "late_review"
    AI_FALSE_POSITIVE = "ai_false_positive"
    TARIFF_CORRECTION = "tariff_correction"
    PARTIAL_DAY = "partial_day"
    DIRECTOR_WAIVER = "director_waiver"


class ReversalReason(StrEnum):
    """`payments.reversal_reason` — YOPIQ sabab-kod ro'yxati (D-19, D-23).

    ⛔ `other` / `custom` A'ZOSI YO'Q — sabab yuqoridagi `AdjustmentReason`
    docstringida va u ikkala ro'yxat uchun ham AYNAN bir xil.

    ⚠ Storno HAR DOIM sabab talab qiladi va o'z QATORI bo'ladi: asl to'lov
    tahrirlanmaydi. Ya'ni nizoda ikkala yozuv ham ko'rinadi — «to'ladi» va
    «bekor qilindi, sababi shu» (D-02).
    """

    WRONG_STALL = "wrong_stall"
    WRONG_AMOUNT = "wrong_amount"
    DUPLICATE_ENTRY = "duplicate_entry"
    CUSTOMER_REFUND = "customer_refund"


class AnomalyKind(StrEnum):
    """Kun yopilishida hisob YOZILMAGAN, lekin e'tibor talab qiladigan holatlar.

    Uchala a'zo UCH BOSHQA qarordan chiqadi va ular HECH QACHON bitta
    hisoblagichga qo'shilmaydi (C-12):

    `unassigned_occupied`  — rasta band, lekin sotuvchi biriktirilmagan
        (D-28). Hisob YOZILMAYDI va `vendor_id` NULL bilan ham yozilmaydi:
        «kimdir qarzdor, lekin kim ekani noma'lum» yozuvi qarz hisobotini
        buzardi. Ekranda: «Ro'yxatga olinmagan savdo».

    `closed_day_occupied`  — yopiq kunda savdo ko'rindi (D-10). Yopiq kunda
        hisob yozilmaydi, lekin hodisani jimgina yo'qotish ham noto'g'ri.

    `no_coverage_stall`    — rastani birorta kamera zonasi qamramaydi
        (D-05). ⛔ BU «BAND, LEKIN TO'LOVSIZ» EMAS: «ko'ra olmadik» ≠ «band».
        Ikkisini bir joyga qo'shish KO'R NUQTADAN tushum da'vosi to'qish
        bo'lardi. Ekranda: «Qamrovsiz rasta» — «bo'sh» so'zi TAQIQLANADI
        (G-26).
    """

    UNASSIGNED_OCCUPIED = "unassigned_occupied"
    CLOSED_DAY_OCCUPIED = "closed_day_occupied"
    NO_COVERAGE_STALL = "no_coverage_stall"


class MapDayState(StrEnum):
    """Plan-xarita katagining BUGUNGI to'lov holati — YOPIQ enum (MARKET-06).

    =========================================================================
    ⛔⛔ A'ZOLARNING TARTIBI — MANTIQNING O'ZI, ALIFBO EMAS.

    Ustuvorlik qoidasi (D-C2) AYNAN shu tartibda o'qiladi va u
    `billing_repo._map_day_state()` da BIR MARTA bajariladi:

        | # | Shart                          | Holat        | Rang       |
        |---|--------------------------------|--------------|------------|
        | 1 | rastada ochiq case bor         | `mismatch`   | sariq      |
        | 2 | `amount_soum is None`          | `no_billing` | rang YO'Q  |
        | 3 | `vendor_id is None`            | `free`       | yashil     |
        | 4 | `amount_soum - paid_soum <= 0` | `paid`       | ko'k       |
        | 5 | qolgan hamma holat             | `due`        | qizil      |

    ⛔ QAROR SERVERDA, KLIENTDA EMAS. Ustuvorlikni ikki tilda (Python va
       TypeScript) yozish ularni bir kun ajratardi va o'shanda xaritadagi
       rang bilan hisobotdagi holat FARQ qilardi — ikkalasi ham «to'g'ri»
       bo'lgan holda. Klient bu qiymatni faqat CSS sinfiga MAPS qiladi.

    =========================================================================
    ⛔ `free` NING MA'NOSI — «SOTUVCHI BIRIKTIRILMAGAN», BANDLIK EMAS (D-C3).

    MARKET-06 matni «yashil bo'sh» ni CV bandligi ma'nosida yozgan. CV
    modeli yo'q (AI-02 `Blocked`), ya'ni bandlik O'LCHANMAGAN va
    o'lchanmagan miqdorni rang bilan da'vo qilish TAQIQLANADI (D-01).
    Shuning uchun `free` = «bugun bu rastadan patta KUTILMAYDI, chunki
    sotuvchi biriktirilmagan» va legenda AYNAN shu jumlani yozadi.
    «Bo'sh» so'zi bu enum atrofida ISHLATILMAYDI.

    =========================================================================
    ⛔ `no_billing` — RANG QO'YILMAYDIGAN YAGONA A'ZO.

    Yopiq kunda yoki tarifsiz rastada katak INVENTAR tonida qoladi va
    sabab (`market_closed` / `tariff_missing`) ekranda SO'Z bilan
    ko'rinadi. Kulrang «to'lanmagan» rangi bilan yonma-yon turganda
    farqlanmasdi, «to'landi» deb chizish esa yolg'on bo'lardi.
    """

    MISMATCH = "mismatch"
    NO_BILLING = "no_billing"
    FREE = "free"
    PAID = "paid"
    DUE = "due"


class ShiftStatus(StrEnum):
    """`cashier_shifts.status` — smena ochiqmi yoki yopilganmi (D-27).

    Bir kassirda bir vaqtda AYNAN BITTA ochiq smena bo'lishi qisman `UNIQUE`
    indeks bilan STRUKTURAVIY majburlanadi (`uq_alert_events_..._open`
    naqshi), ilova mantig'i bilan emas: ikki oynadan bir vaqtda ochilgan
    smena poyga holati va uni faqat sxema to'xtata oladi.

    ⚠ `closed` — YAKUNIY holat: yopilgan smena qayta ochilmaydi va
    deklaratsiya o'zgartirilmaydi (D-25). «Qayta ochish» yo'li smenani
    tizim summasiga MOSLASHTIRISH imkonini berardi.
    """

    OPEN = "open"
    CLOSED = "closed"


class AuditAction(StrEnum):
    """`audit_log.action` qiymatlari.

    DB-trigger `lower(TG_OP)` yozadi, shuning uchun `insert`/`update`/`delete`
    KICHIK harfda bo'lishi shart — aks holda ilova yozgan va trigger yozgan
    qatorlar bir xil hisobotda ikki xil qiymat bo'lib ko'rinadi.

    =========================================================================
    ⛔ 6-FAZA AYNAN IKKI A'ZO QO'SHADI — VA BU UI-SPEC §13.6 NING NOMZOD
       TO'PLAMIDAN (`charge_adjust`, `shift_open`, `shift_close`) ATAYIN
       CHETLASHISH. §13.6 buni OCHIQ ruxsat etadi: «Reja bu to'plamdan chetga
       chiqsa, darvoza O'ZI aytadi va bu hujjat tuzatishni talab qilmaydi.»

    Sabab MEXANIK va u `AUDITED_TABLES` reyestridan chiqadi:

      * `payments` `AUDITED_TABLES` da YO'Q (append-only, hajmi katta —
        `schema_contract.py` tavsiyasi). Ya'ni DB-trigger u yerda hech nima
        yozmaydi va `write_app_audit()` YAGONA audit yo'li. Shuning uchun
        `payment_override` va `payment_reverse` HAQIQIY ishlab chiqaruvchiga
        ega bo'ladi (06-09: summa override i va storno).

      * ⛔ `shift_open` / `shift_close` QO'SHILMAYDI: `cashier_shifts`
        `AUDITED_TABLES` da BOR, ya'ni DB-trigger qatorni O'ZI yozadi va app
        darajasidagi audit DUBLIKAT bo'lardi — bitta hodisa jurnalda ikki
        marta ko'rinardi va «nechta smena yopildi?» savoli ikki xil javob
        berardi.

      * ⛔ `charge_adjust` QO'SHILMAYDI: `charge_adjustments` ham
        `AUDITED_TABLES` da BOR — o'sha sabab.

    ⚠ IKKALA A'ZO 06-09 DAGI `write_app_audit()` CHAQIRUVLARI PAYDO BO'LGUNGA
      QADAR ISHLATILMASDAN TURADI va bu KUTILGAN. `audit-actions.test.mjs`
      faqat enum <-> TS <-> i18n parity'sini o'lchaydi, ISHLATILISHNI emas.
      Sabab shu yerda yozilgan, aks holda keyingi ijrochi ularni «o'lik kod»
      deb o'chirib, 06-09 ni audit izisiz qoldirardi.
    =========================================================================
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
    PAYMENT_OVERRIDE = "payment_override"
    PAYMENT_REVERSE = "payment_reverse"


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


class ReconciliationCaseStatus(StrEnum):
    """`reconciliation_cases.status` — YOPIQ TO'RT A'ZOLI ro'yxat (D-12).

    ⚠ QIYMATLAR INGLIZCHA, ko'rsatiladigan matn esa i18n KALITI —
    `PaymentKind` / `AnomalyKind` bilan AYNAN bir xil shakl. 7-fazaning
    kontekstidagi o'zbekcha nomlar (`yangi` / `ko'rilmoqda` / `asosli` /
    `asossiz`) MA'NO, qiymat emas.

    =========================================================================
    ⛔ `other` / `custom` A'ZOSI YO'Q VA U QO'SHILMAYDI.

    Sabab `AdjustmentReason` docstringidagi bilan AYNAN bir sinfda
    (6-faza D-19 / T-06-07): erkin matnni qaytarib keltiradigan a'zo
    hisobotda GURUHLANMAYDI — u AMALDA eng katta guruh bo'lib qolardi va
    nomuvofiqlik navbatining haqiqiy natijasi hech qachon o'lchanmasdi.

    ⛔ HIT-RATE NING MAXRAJI HAM SHU YERDA QULFLANADI (D-13):

        hit_rate = justified / (justified + unjustified)

    `new` va `in_review` maxrajga ⛔ KIRMAYDI. Sabab mexanik: hali
    ko'rilmagan case metrikani PASAYTIRARDI, ya'ni navbatni tez ko'rib
    chiqmaslik ko'rsatkichni yomonlashtirardi va ko'rsatkich o'z
    jarayonini o'lchash o'rniga uning KECHIKISHINI o'lchardi.

    ⛔ `hit_rate` USTUNI HECH QAYERDA SAQLANMAYDI — u `NULLIF` bilan
    so'rovda hisoblanadi (D-06 bilan bir sinf: saqlangan hosila ikkinchi
    haqiqat manbai bo'lardi).
    =========================================================================

    `new`         — case tug'ildi, hali hech kim qaramagan
    `in_review`   — mas'ul biriktirildi, tekshiruv ketmoqda
    `justified`   — nomuvofiqlik TASDIQLANDI (haqiqiy yo'qotish/qoida buzilishi)
    `unjustified` — nomuvofiqlik TASDIQLANMADI (tizim xatosi, oqlangan holat)
    """

    NEW = "new"
    IN_REVIEW = "in_review"
    JUSTIFIED = "justified"
    UNJUSTIFIED = "unjustified"


class ReconciliationSubjectKind(StrEnum):
    """`reconciliation_cases.subject_kind` — case NIMAGA ochilgan (DQ-5).

    =========================================================================
    ⛔ YOPIQ DISKRIMINATOR — `NULL` TEKSHIRISH EMAS.

    Case ikki xil o'zgarmas qatorga ishora qiladi va ular BIR JADVALDA
    yashamaydi: `anomaly_id` (`billing_anomalies` qatori — HODISA) yoki
    `charge_id` (`daily_charges` qatori — HISOB). Sinfni «qaysi ustun
    bo'sh?» mantig'i bilan aniqlash hisobotni USTUN SHAKLIGA bog'lardi:
    uchinchi manba qo'shilgan kuni har bir `GROUP BY` qayta yozilishi
    kerak bo'lardi va eski so'rovlar JIMGINA noto'g'ri guruh berardi.

    Yopiq diskriminator `GROUP BY` ni BITTA ustunga tushiradi va uning
    ustundan ajralib ketishi `subject_kind_matches_target` `CHECK` bilan
    STRUKTURAVIY imkonsiz qilingan.
    =========================================================================

    `anomaly`         — «ro'yxatga olinmagan savdo» sinfi: `billing_anomalies`
                        qatori (`unassigned_occupied` / `closed_day_occupied`).
                        ⛔ `no_coverage_stall` ga case OCHILMAYDI — u kamera
                        qamrovi nuqsoni, tushum nomuvofiqligi EMAS.
    `occupied_unpaid` — «band, lekin to'lovsiz» sinfi: `daily_charges`
                        qatori. ⛔ Bu sinf uchun TO'RTINCHI `AnomalyKind`
                        qo'shilmaydi — «to'lanmagan» hosila, hodisa emas
                        (D-06/D-13), va uni 04:10 da qator qilib yozish
                        ertaga to'lov kelganda YOLG'ONGA aylanardi.
    """

    ANOMALY = "anomaly"
    OCCUPIED_UNPAID = "occupied_unpaid"


class OutboxKind(StrEnum):
    """`notification_outbox.kind` — QANDAY xabar navbatga qo'yilgan (BOT-04).

    =========================================================================
    ⛔ TAYYOR MATN QATORDA SAQLANMAYDI — U JO'NATISH PAYTIDA QURILADI.

    Qatorda faqat `kind` (shu yopiq to'plam) va `payload` (allowlist bilan
    cheklangan kalitlar, `alerting.py::_detail()` naqshi) bo'ladi. Tayyor
    matnni ustunga yozish sotuvchining ismini, rasta kodini va summani
    bazaga, u yerdan `pg_dump` → restic → TASHQI BUCKET ga chiqarardi
    (D-03 ning aynan shu sababdan yozilgan tashqi chegara bandi).
    =========================================================================

    `payment_receipt`  — kvitansiya (CASH-05). ⛔ HECH QACHON to'xtatilmaydi:
                         na quiet hours, na throttling uni ushlab qolmaydi
                         (D-18) — u sotuvchining HOZIRGINA to'laganini
                         isbotlaydigan yozuv va uni kechiktirish nizo
                         modelini buzardi.
    `overdue_reminder` — qarz eslatmasi (BOT-03). Quiet hours ga BO'YSUNADI.
    `digest_morning`   — direktorning ertalabki dayjesti (08:00): manba
                         `daily_charges` + `payments`, ya'ni kechagi
                         YOZILGAN kun (D-16).
    `digest_evening`   — kechki nomuvofiqlik xabari (20:45): manba
                         `pending_projection()`, ya'ni bugungi KUTILAYOTGAN
                         holat (D-15). ⛔ Ikki sonning farq qilishi NUQSON
                         EMAS, DIZAYN — va matn buni ochiq aytadi.
    """

    PAYMENT_RECEIPT = "payment_receipt"
    OVERDUE_REMINDER = "overdue_reminder"
    DIGEST_MORNING = "digest_morning"
    DIGEST_EVENING = "digest_evening"


class OutboxRecipientKind(StrEnum):
    """`notification_outbox.recipient_kind` — xabar KIMGA ketadi.

    =========================================================================
    ⛔ `chat_id` OUTBOX QATORIDA SAQLANMAYDI (D-26c).

    Manzil jo'natish PAYTIDA olinadi: sotuvchi uchun
    `vendor_telegram_bindings` dan (faqat `revoked_at IS NULL` qatori),
    direktor uchun `market_notification_settings.director_chat_id` dan.

    Sabab mexanik: qayta ulanish (o'sha telefon, BOSHQA Telegram akkaunti)
    eski bog'lanishni BEKOR QILADI. `chat_id` qatorga muzlatilgan bo'lsa,
    navbatda turgan qarz eslatmasi ESKI chatga ketardi — ya'ni sotuvchining
    moliyaviy ma'lumoti u boshqarmaydigan akkauntga tushardi.
    =========================================================================

    `vendor`          — sotuvchi (`vendor_id` MAJBURIY,
                        `recipient_matches_vendor` `CHECK` bilan qulflangan)
    `market_director` — bozor direktori (`vendor_id` BO'LMAYDI)
    """

    VENDOR = "vendor"
    MARKET_DIRECTOR = "market_director"


class OutboxStatus(StrEnum):
    """`notification_outbox.status` — append-only holat mashinasi (D-20).

        pending -> sent -> delivered | failed | blocked

    =========================================================================
    ⛔⛔ HAR A'ZONING MA'NOSI AYNAN SHU — KAM HAM, KO'P HAM EMAS.

    `pending`   — qator yozilgan, urinish hali QILINMAGAN.
    `sent`      — ijara olingan, HTTP so'rov YO'LDA.
    `delivered` — Telegram **200** qaytardi va `message_id` berdi, ya'ni
                  xabar chatga JOYLANDI.
    `failed`    — urinishlar tugadi yoki qayta urinib bo'lmaydigan xato.
    `blocked`   — `403`: foydalanuvchi botni bloklagan (D-22).

    ⛔ `delivered` FOYDALANUVCHI XABARNI OCHGANINI BILDIRMAYDI. Bot API ning
    `sendMessage` javobi — `Message` obyekti (`message_id`, `date`); Telegram
    yetkazilganlik yoki ochilganlik KVITANSIYASINI UMUMAN BERMAYDI. Nizoda
    (D-02) bunday da'vo tizimni ISBOTLAB BO'LMAYDIGAN gapga majburlardi,
    ya'ni dalil o'rniga taxmin qo'yardi. Uchala locale'dagi UI matni ham
    «Telegram qabul qildi» ma'nosini beradi.

    ⚠ `blocked` — MA'LUMOT, XATO EMAS (D-22). U sotuvchi bilan aloqa
    uzilganini bildiradi: keyingi urinishlar QILINMAYDI va direktor buni
    ekranda topishi kerak. Uni `failed` ga qo'shish aloqa uzilishini
    texnik nosozlik shovqiniga ko'mib yuborardi.
    =========================================================================
    """

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BLOCKED = "blocked"
