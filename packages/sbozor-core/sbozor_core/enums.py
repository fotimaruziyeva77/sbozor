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
    "AuditAction",
    "AuditSource",
    "CameraStatus",
    "DiscoveryRunStatus",
    "Locale",
    "Role",
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
