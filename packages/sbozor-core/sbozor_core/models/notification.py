"""Bildirishnoma domeni: case, case tarixi, outbox, bog'lanish va sozlama.

=============================================================================
BU FAYLDA OLTITA QAROR YASHAYDI VA HAMMASI KODDA EMAS, SXEMADA.

1. CASE — ALOHIDA JADVAL (D-11). `billing_anomalies` ga ham, `daily_charges`
   ga ham ustun QO'SHILMAYDI. Sabab MA'NODA: anomaliya/hisob — HODISA
   (o'zgarmas dalil, 6-fazaning `charge_immutable()` / o'zgarmaslik
   triggerlari bilan qulflangan), case esa JARAYON — mas'ul, holat va
   yechim matni O'ZGARADI. Ikkisini bitta qatorga qo'shish o'zgarmas dalil
   qatorini O'ZGARUVCHAN qilardi va 6-fazaning D-07/T-06-15 sinfini
   buzardi. Bog'lanish MUZLATILGAN POINTER bilan (D-08/6-faza).

2. NOMUVOFIQLIK IKKI SINF VA ULAR BIR JADVALDA YASHAMAYDI (Pattern 4).
   Shuning uchun `reconciliation_cases` IKKI MUSTAQIL, o'zaro istisno
   qiluvchi kompozit FK oladi:

       anomaly_id -> billing_anomalies (market_id, id)   «ro'yxatga olinmagan savdo»
       charge_id  -> daily_charges     (market_id, id)   «band, lekin to'lovsiz»

   ⛔ IKKINCHI SINF UCHUN TO'RTINCHI `AnomalyKind` QO'SHILMAYDI. Sabab
   mexanik: `billing_close` 04:10 da ishlaydi, o'sha kunning to'lovlari esa
   hali kelmagan — «to'lanmagan» ni o'sha paytda qator qilib yozish ertaga
   to'lov kelganda YOLG'ONGA aylanadigan SAQLANGAN HOSILA bo'lardi
   (D-06/D-13 aynan shu sinfni taqiqlaydi).

3. IDEMPOTENTLIK — CHEKLOV, ILOVA INTIZOMI EMAS (D-21). Bir to'lov uchun
   ikki kvitansiya yuborilishi 6-fazaning T-06-49 bilan AYNAN bir sinfdagi
   xato bo'lardi; u yerda yechim `UNIQUE` cheklov edi, bu yerda ham
   SHUNDAY: `UNIQUE (market_id, dedupe_key)`. Bir anomaliya/hisob uchun
   ikkinchi case ochilishi ham STRUKTURAVIY imkonsiz — ikki QISMAN UNIQUE
   indeks (`uq_alert_events_market_id_alert_key_open` naqshi).

4. OUTBOX — APPEND-ONLY HOLAT MASHINASI (D-20):
   `pending -> sent -> delivered | failed | blocked`. O'chirish yo'q; qayta
   urinish `attempt_count` va `next_attempt_at` bilan, ASL NIYAT QATORI esa
   o'zgarmaydi.

5. BOG'LANISH — ALOHIDA JADVAL, `vendors` GA USTUN EMAS (D-27). Bitta
   sotuvchining vaqt bo'yicha bir necha bog'lanish TARIXI bo'ladi va
   D-26(c) (qayta ulanish: o'sha raqam, boshqa Telegram akkaunti) aynan
   shuni talab qiladi. Ustun bo'lganda «eski bog'lanish qachon va nega
   bekor qilindi?» savoli javobsiz qolardi.

6. QUIET HOURS VA `overdue_days` — BOZOR KESIMIDA (D-19), global konstanta
   EMAS. Sabab multi-tenant cheklovdan chiqadi: «yangi bozor kod yozmasdan
   wizard orqali ulanadi». Global konstanta ikkinchi bozor uchun kod
   o'zgartirishni talab qilardi.
=============================================================================

BESHALA JADVAL HAM TENANT JADVALI: `market_id` + RLS `ENABLE` va `FORCE` +
tenant policy + `market_id` bilan boshlanuvchi domen konstraytlari +
kompozit FK. `market_id` ustunida inline `ForeignKey` YOZILMAYDI — sabab
`models/base.py::market_fk_column()` docstringida.

⚠ PG `ENUM` TIPI ISHLATILMAYDI. Ustunlar `text` + enum'dan HOSILA `CHECK`
ifodasi (`models/billing.py` va `models/occupancy.py` naqshi). Sabab
ikkita: (a) PG enum tipiga qiymat qo'shish tranzaksiya ichida bajarilmaydi;
(b) loyihada `stalls.status`, `cameras.status`, `payments.kind` allaqachon
`text`+`CHECK` — yangi shakl IKKINCHI konventsiya yaratardi.

⚠ ⛔ BU FAYLDA PUL USTUNI YO'Q va bo'lmasligi ham kerak (G7-8, D-06/D-07).
Xabardagi summa `payload` da KO'CHIRMA bo'lib turadi, manba esa
`payments` / `daily_charges`. Saqlangan qoldiq nomi ham, kasrli tip va
yaxlitlash chaqiruvlari ham bu faylga TARQAMAYDI.

⛔ TAQIQLANGAN NOMLAR BU YERDA LITERAL YOZILMAYDI — 3-fazaning (03-07)
o'lchangan darsi: sodda `grep` darvozasi izohni koddan AJRATMAYDI, ya'ni
taqiqni tushuntirish uchun yozilgan literal darvozani O'Z-O'ZIGA QARSHI
qo'yardi va yagona «tuzatish» yo'li darvozaga istisno qo'shish bo'lardi.
Ro'yxatning O'ZI `07-04` ning `FORBIDDEN_OUTBOX_COLUMN_TOKENS` reyestrida
va u yerda `information_schema` TO'PLAM TENGLIGI bilan o'lchanadi (G7-2,
G7-8) — ya'ni da'vo susaymaydi, u O'LCHANADIGAN joyga ko'chadi.

⚠ `TimestampMixin` FAQAT O'ZGARADIGAN jadvallarga qo'yiladi. `updated_at`
«bu qatorni tahrirlash mumkin» degan VA'DA beradi va u faqat case, outbox
hamda sozlama uchun ROST. `reconciliation_case_events` va
`vendor_telegram_bindings` da u YO'Q: birinchisi o'zgarmaslik triggeri
bilan qulflangan, ikkinchisida esa o'zgarish `revoked_at` ni to'ldirish
bilan ifodalanadi.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Final
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.enums import (
    OutboxKind,
    OutboxRecipientKind,
    OutboxStatus,
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
)
from sbozor_core.models.base import Base, TenantMixin, TimestampMixin, uuid_pk

__all__ = [
    "CASE_KEYSET_INDEX",
    "CASE_STATUS_CHECK",
    "CASE_STATUS_VALUES",
    "CASE_SUBJECT_ANOMALY_INDEX",
    "CASE_SUBJECT_ANOMALY_PREDICATE",
    "CASE_SUBJECT_CHARGE_INDEX",
    "CASE_SUBJECT_CHARGE_PREDICATE",
    "CASE_WORKLIST_INDEX",
    "EVENT_FROM_STATUS_CHECK",
    "EVENT_STATUS_TRANSITION_CHECK",
    "EVENT_TO_STATUS_CHECK",
    "OUTBOX_DUE_INDEX",
    "OUTBOX_DUE_PREDICATE",
    "OUTBOX_KIND_CHECK",
    "OUTBOX_KIND_VALUES",
    "OUTBOX_RECIPIENT_KIND_CHECK",
    "OUTBOX_RECIPIENT_KIND_VALUES",
    "OUTBOX_STATUS_CHECK",
    "OUTBOX_STATUS_VALUES",
    "RECIPIENT_MATCHES_VENDOR_CHECK",
    "RESOLUTION_NOTE_MAX_LENGTH",
    "RESOLUTION_NOTE_LENGTH_CHECK",
    "SUBJECT_IS_EXCLUSIVE_CHECK",
    "SUBJECT_KIND_CHECK",
    "SUBJECT_KIND_MATCHES_TARGET_CHECK",
    "SUBJECT_KIND_VALUES",
    "BINDING_ACTIVE_PREDICATE",
    "BINDING_TELEGRAM_ACTIVE_INDEX",
    "BINDING_VENDOR_ACTIVE_INDEX",
    "MarketNotificationSettings",
    "NotificationOutbox",
    "ReconciliationCase",
    "ReconciliationCaseEvent",
    "VendorTelegramBinding",
]

CASE_STATUS_VALUES: tuple[str, ...] = tuple(s.value for s in ReconciliationCaseStatus)
SUBJECT_KIND_VALUES: tuple[str, ...] = tuple(k.value for k in ReconciliationSubjectKind)
OUTBOX_KIND_VALUES: tuple[str, ...] = tuple(k.value for k in OutboxKind)
OUTBOX_RECIPIENT_KIND_VALUES: tuple[str, ...] = tuple(r.value for r in OutboxRecipientKind)
OUTBOX_STATUS_VALUES: tuple[str, ...] = tuple(s.value for s in OutboxStatus)


def _quoted(values: tuple[str, ...]) -> str:
    """SQL literal ro'yxati. Qiymatlar `StrEnum` a'zolari — tashqi kirish emas.

    `market.py`, `identity.py`, `nvr.py`, `snapshot.py`, `occupancy.py` va
    `billing.py` dagi jufti bilan bir xil ikki qatorli funksiya va u ATAYIN
    YETTINCHI marta takrorlanadi: umumiy modulga chiqarish
    `models/base.py` ning ommaviy yuzasini kengaytirardi, har bir
    chaqiruvchi esa baribir O'Z enum'i bilan qulflangan.
    """
    return ", ".join(f"'{value}'" for value in values)


_ANOMALY: Final = ReconciliationSubjectKind.ANOMALY.value
_VENDOR: Final = OutboxRecipientKind.VENDOR.value
"""Ikki a'zo qiymati QISQA nom ostida — ifodalar 100 belgilik chegaraga sig'sin.

`models/billing.py::_CLOSED` bilan bir xil qaror: qiymat baribir ENUMDAN
HOSILA, ya'ni a'zo qiymati o'zgarsa ifoda O'ZI yangilanadi.
"""

CASE_STATUS_CHECK = f"status IN ({_quoted(CASE_STATUS_VALUES)})"
"""`reconciliation_cases.status` — `ReconciliationCaseStatus` DAN HOSILA (D-12).

⛔ `other` A'ZOSI YO'Q va bu ro'yxatning butun qiymati (sabab
`enums.py::ReconciliationCaseStatus` docstringida): erkin matn hisobotda
guruhlanmasdi va hit-rate ni (D-13) o'lchab bo'lmasdi.
"""

SUBJECT_KIND_CHECK = f"subject_kind IN ({_quoted(SUBJECT_KIND_VALUES)})"
"""`reconciliation_cases.subject_kind` — `ReconciliationSubjectKind` DAN HOSILA."""

OUTBOX_KIND_CHECK = f"kind IN ({_quoted(OUTBOX_KIND_VALUES)})"
"""`notification_outbox.kind` — `OutboxKind` DAN HOSILA (BOT-04)."""

OUTBOX_RECIPIENT_KIND_CHECK = f"recipient_kind IN ({_quoted(OUTBOX_RECIPIENT_KIND_VALUES)})"
"""`notification_outbox.recipient_kind` — `OutboxRecipientKind` DAN HOSILA."""

OUTBOX_STATUS_CHECK = f"status IN ({_quoted(OUTBOX_STATUS_VALUES)})"
"""`notification_outbox.status` — `OutboxStatus` DAN HOSILA (D-20).

Holat mashinasining O'TISHLARI bu `CHECK` bilan majburlanmaydi (u faqat
to'plamni yopadi) — o'tish qoidasi jo'natuvchi worker'da va u har bir
o'tishni `UPDATE ... WHERE status = <kutilgan>` bilan qiladi.
"""

SUBJECT_IS_EXCLUSIVE_CHECK = "(anomaly_id IS NULL) <> (charge_id IS NULL)"
"""⛔ XOR: case AYNAN BITTA o'zgarmas qatorga ishora qiladi (DQ-5).

IKKI TOMONLAMA va ikkala nosozlikni ham yopadi:
  * IKKALASI ham to'ldirilgan -> case ikki xil dalilga ishora qilardi va
    «qaysi biri hisobotga tushadi?» savoli javobsiz qolardi;
  * IKKALASI ham `NULL` -> case UMUMAN dalilsiz bo'lardi, ya'ni navbatda
    tekshirib bo'lmaydigan qator paydo bo'lardi.

⚠ `<>` (`XOR`) ATAYIN, `OR` EMAS: `OR` ikkalasi to'ldirilgan holatni
O'TKAZARDI.
"""

SUBJECT_KIND_MATCHES_TARGET_CHECK = f"(subject_kind = '{_ANOMALY}') = (anomaly_id IS NOT NULL)"
"""⛔ DISKRIMINATOR USTUN BILAN MOS (DQ-5) — `GROUP BY` ning halolligi.

Ikki tomonlama tenglik (`=`, `->` EMAS): «`anomaly` deydi, lekin
`charge_id` to'ldirilgan» ham, «`occupied_unpaid` deydi, lekin
`anomaly_id` to'ldirilgan» ham IFODALAB BO'LMAYDI.

Usiz `subject_kind` YOLG'ON GURUH berardi: hisobot «ro'yxatga olinmagan
savdo» deb sanagan qator aslida hisob qatoriga ishora qilardi va ikki
sinfning nisbati (RECON-01 ning butun mazmuni) noto'g'ri chiqardi.

⚠ IKKINCHI SHOX ALOHIDA YOZILMAYDI: `SUBJECT_IS_EXCLUSIVE_CHECK` bilan
BIRGA bu ifoda `occupied_unpaid` uchun `charge_id IS NOT NULL` ni ham
majburlaydi — XOR ikkinchi ustunni allaqachon qulflagan.
"""

EVENT_TO_STATUS_CHECK = f"to_status IN ({_quoted(CASE_STATUS_VALUES)})"
"""`reconciliation_case_events.to_status` — `ReconciliationCaseStatus` DAN HOSILA.

⚠ IFODA MODELDA E'LON QILINADI, MIGRATSIYADA EMAS va bu OP-10 ning aynan
qoidasi: `0023` uni SHU YERDAN import qiladi, ya'ni qiymat ro'yxatining
IKKINCHI NUSXASI umuman tug'ilmaydi. Nusxa bo'lganda «enumga a'zo
qo'shilib migratsiya yozilmadi» holati mumkin bo'lardi.
"""

EVENT_FROM_STATUS_CHECK = f"from_status IS NULL OR from_status IN ({_quoted(CASE_STATUS_VALUES)})"
"""`reconciliation_case_events.from_status` — enumdan HOSILA, lekin NULLABLE.

⚠ `IS NULL OR ...` shakli ATAYIN OCHIQ yozilgan: `NULL IN (...)` `NULL`
beradi va `CHECK` `NULL` ni O'TKAZADI, ya'ni shart usiz ham ishlardi.
Ochiq yozilgani NIYATNI ko'rsatadi — case TUG'ILGANDA oldingi holat YO'Q
va bu QONUNIY holat, unutilgan `NOT NULL` emas
(`REVERSAL_REASON_CHECK` docstringidagi bilan bir xil qaror).
"""

RESOLUTION_NOTE_MAX_LENGTH: Final[int] = 2000
"""`resolution_note` ning belgilardagi chegarasi — V5 kirish validatsiyasi.

Chegara SXEMADA, faqat ilova qatlamida EMAS: xom SQL yo'li ilova
validatsiyasini BUTUNLAY chetlab o'tadi (`migrations/entities/triggers.py`
da o'lchangan sinf). Cheklanmagan `text` ustuni bitta so'rov bilan
megabaytlab matn qabul qilardi va u `pg_dump` -> restic -> tashqi bucket
zanjiriga tushardi.
"""

RESOLUTION_NOTE_LENGTH_CHECK = (
    f"resolution_note IS NULL OR char_length(resolution_note) <= {RESOLUTION_NOTE_MAX_LENGTH}"
)
"""Yechim matnining uzunlik chegarasi (`RESOLUTION_NOTE_MAX_LENGTH` docstringi).

⚠ `IS NULL OR ...` MAJBURIY: ustun nullable va `NULL <= 2000` `NULL`
beradi — `CHECK` esa `NULL` ni O'TKAZADI, ya'ni shart busiz ham ishlardi.
Ochiq yozilgani NIYATNI ko'rsatadi: bo'sh yechim matni QONUNIY holat
(case hali hal qilinmagan).
"""

EVENT_STATUS_TRANSITION_CHECK = "from_status IS DISTINCT FROM to_status"
"""Case tarixi qatori HAQIQIY o'tishni yozadi (D-14).

`from_status = to_status` bo'lgan qator «o'zgarish bo'ldi» deb yozilardi-yu,
hech nima o'zgarmagan bo'lardi — ya'ni tarix SHOVQIN bilan to'lardi va
«case necha marta qo'ldan qo'lga o'tdi?» savoli noto'g'ri javob berardi.

⚠ `IS DISTINCT FROM` ATAYIN, `<>` EMAS: `from_status` NULLABLE (case
TUG'ILGANDA oldingi holat YO'Q) va `NULL <> 'new'` `NULL` berardi, ya'ni
`CHECK` uni o'tkazib yuborardi.
"""

RECIPIENT_MATCHES_VENDOR_CHECK = f"(recipient_kind = '{_VENDOR}') = (vendor_id IS NOT NULL)"
"""Sotuvchiga xabar `vendor_id` TALAB QILADI, direktorniki esa uni KO'TARMAYDI.

Ikki tomonlama tenglik — `SUBJECT_KIND_MATCHES_TARGET_CHECK` bilan bir xil
qaror sinfi. «`vendor` deydi, lekin kimga ekani noma'lum» qatori jo'natish
paytida manzilsiz qolardi (`vendor_telegram_bindings` ga `JOIN` qiladigan
kalit yo'q); «`market_director` deydi, lekin `vendor_id` to'ldirilgan»
qatori esa direktor xabarini sotuvchi bog'lanishiga bog'lardi.
"""

CASE_SUBJECT_ANOMALY_INDEX = "uq_reconciliation_cases_anomaly"
"""BIR ANOMALIYAGA BITTA CASE — qisman UNIQUE indeks (D-21 naqshi).

`uq_alert_events_market_id_alert_key_open` va `SHIFT_OPEN_INDEX` bilan
AYNAN bir xil qaror: poyga DB'GA topshiriladi, ilova qatlamida «avval
tekshir, keyin yoz» QILINMAYDI. `recon.open` cron KONVERGENT — u o'sha kun
uchun QAYTA-QAYTA yugurishi NORMAL holat va ilova qatlamidagi tekshiruv
ikkita parallel yugurishda ikkita case yozardi. O'shanda navbat bir xil
anomaliyani ikki marta ko'rsatardi va hit-rate maxraji (D-13) shishardi.
"""

CASE_SUBJECT_ANOMALY_PREDICATE = "anomaly_id IS NOT NULL"
"""Anomaliya case'ining qisman indeks predikati.

⚠ QISMAN bo'lishi MAJBURIY: to'liq UNIQUE indeks `anomaly_id IS NULL`
bo'lgan BARCHA hisob case'larini ham bir-biriga to'qnashtirardi — PG da
`NULL` lar UNIQUE indeksda o'zaro teng emas, lekin `(market_id, NULL)`
juftliklari indeksni keraksiz shishirardi va niyatni yashirardi.
"""

CASE_SUBJECT_CHARGE_INDEX = "uq_reconciliation_cases_charge"
"""BIR HISOBGA BITTA CASE — `CASE_SUBJECT_ANOMALY_INDEX` ning jufti."""

CASE_SUBJECT_CHARGE_PREDICATE = "charge_id IS NOT NULL"
"""Hisob case'ining qisman indeks predikati (`CASE_SUBJECT_ANOMALY_PREDICATE` jufti)."""

CASE_WORKLIST_INDEX = "ix_reconciliation_cases_market_status_service_date"
"""«Bu kunning ochiq case'lari» — navbat ekranining kirishi (DQ-4)."""

CASE_KEYSET_INDEX = "ix_reconciliation_cases_market_created_at_id"
"""Keyset sahifalash indeksi — `(created_at DESC, id DESC)` (DQ-4).

⛔ `offset` ISHLATILMAYDI va indeks aynan shuning uchun bu shaklda: case
ro'yxati kun davomida O'SADI va offset sahifalash takroriy yoki tushib
qolgan qatorlar berardi — nazoratchi bir case'ni ikki marta ko'rib,
ikkinchisini umuman ko'rmasdi.
"""

OUTBOX_DUE_INDEX = "ix_notification_outbox_market_next_attempt_pending"
"""Jo'natuvchi tikning YAGONA so'rov yo'li — qisman indeks (DQ-2).

⚠ QISMAN (`WHERE status = 'pending'`) va bu O'LCHOV masalasi emas, HAJM
masalasi: `delivered` qatorlar HECH QACHON o'chirilmaydi (D-20, append-only)
va bir yildan keyin ular jadvalning ~99 % ini tashkil qiladi. To'liq
indeks har daqiqadagi tikni o'sha o'lik qatorlar ustidan yurgizardi.
"""

OUTBOX_DUE_PREDICATE = f"status = '{OutboxStatus.PENDING.value}'"
"""Tik indeksining predikati — `OutboxStatus` DAN HOSILA.

`SHIFT_OPEN_PREDICATE` / `CAPTURE_DUE_PREDICATE` bilan bir xil qoida va
bir xil sabab: qo'lda ko'chirilgan literal enum bilan ajralib ketganda
indeks JIMGINA hech nimani qamramay qolardi.
"""

BINDING_ACTIVE_PREDICATE = "revoked_at IS NULL"
"""Faol bog'lanishning qisman indeks predikati (D-26c).

Bekor qilingan bog'lanishlar TARIXDA qoladi (D-27), ya'ni noyoblik faqat
FAOL qatorlar ustida ma'noga ega. To'liq UNIQUE indeks qayta ulanishni
BUTUNLAY imkonsiz qilardi — sotuvchi telefonini yangi Telegram akkauntiga
ko'chira olmasdi.
"""

BINDING_VENDOR_ACTIVE_INDEX = "uq_vendor_telegram_bindings_vendor_active"
"""BIR SOTUVCHIDA BIR FAOL BOG'LANISH — qisman UNIQUE indeks (D-26c).

Ikkinchi faol bog'lanish qarz eslatmasini IKKI chatga yuborardi va
ulardan biri sotuvchining O'ZINIKI bo'lmasligi mumkin edi.
"""

BINDING_TELEGRAM_ACTIVE_INDEX = "uq_vendor_telegram_bindings_telegram_active"
"""BIR TELEGRAM AKKAUNTIDA BIR FAOL BOG'LANISH — bozor ICHIDA (D-26c).

⚠⚠ BOZORLAR ARO BU CHEKLANMAYDI va bu ATAYIN: bitta sotuvchi IKKI BOZORDA
savdo qilishi mumkin va u ikkala bozorda ham o'z qarzini ko'rishi kerak.
Indeks `market_id` bilan boshlangani uchun to'qnashuv faqat bozor ichida
tekshiriladi — global noyoblik ikkinchi bozordagi qonuniy bog'lanishni
JIMGINA rad etardi va sotuvchi sababini hech qachon bilmasdi.
"""


class ReconciliationCase(Base, TenantMixin, TimestampMixin):
    """Nomuvofiqlik case'i — JARAYON, hodisa EMAS (D-11, RECON-02).

    =========================================================================
    NEGA ALOHIDA JADVAL VA NEGA USTUN EMAS.

    `billing_anomalies` va `daily_charges` — DALIL qatorlari va ikkalasi ham
    o'zgarmas (6-fazaning `charge_immutable()` qo'riqchisi va anomaliyaning
    hodisa-jurnali tabiati). Case esa jarayonni yuritadi: mas'ul
    biriktiriladi, holat o'zgaradi, yechim matni yoziladi. Bu ustunlarni
    dalil qatoriga qo'shish uni O'ZGARUVCHAN qilardi — ya'ni nizoda (D-02)
    «asl dalil nima edi?» savoliga javob beradigan yagona qator o'z tarixini
    yo'qotardi.

    ⛔ CASE AYNAN BITTA O'ZGARMAS QATORGA ISHORA QILADI (DQ-5): `anomaly_id`
    XOR `charge_id`, ikkalasi ham KOMPOZIT FK (`market_id` bilan) va yopiq
    `subject_kind` diskriminatori bilan bog'langan. Uchala kafolat BIRGA
    ishlaydi:
      * kompozit FK    -> begona bozorning dalili STRUKTURAVIY yetib kelmaydi;
      * XOR `CHECK`    -> ikki dalil ham, dalilsizlik ham imkonsiz;
      * `matches_target` -> diskriminator ustundan ajralib keta olmaydi.
    =========================================================================

    ⛔ `hit_rate` USTUNI YO'Q VA QO'SHILMAYDI (D-13). U HOSILA:
    `justified / (justified + unjustified)`, `NULLIF` bilan SO'ROVDA
    hisoblanadi. Saqlangan ustun D-06 taqiqlagan qoldiq ustuni bilan AYNAN
    bir sinfda bo'lardi: ikkinchi haqiqat manbai birinchisidan jimgina
    ajralib ketardi va «qaysi son rost?» savoli javobsiz qolardi.

    ⛔ `no_coverage_stall` GA CASE OCHILMAYDI (Pattern 4). U kamera qamrovi
    nuqsoni, tushum nomuvofiqligi EMAS — uni navbatga qo'shish har kuni
    ko'r nuqtalar bilan to'ldirardi va nazoratchining diqqati (D-10/5-faza
    byudjeti) haqiqiy nomuvofiqlikdan chalg'irdi. Taqiq bu yerda SXEMA
    bilan emas, `recon.open` ning tanlov shartida — `AnomalyKind` ning
    uchala a'zosi ham `billing_anomalies` da qonuniy.

    JADVAL AUDIT OSTIDA (`AUDITED_TABLES`): holat o'zgarishi INSONNING
    qarori va u nizoda dalil bo'ladi (D-14). `notification_outbox` esa
    ATAYIN auditsiz — sabab `schema_contract.AUDITED_TABLES` docstringida.

    ⚠ `TimestampMixin` BOR va bu ATAYIN — `models/billing.py` dagi oltala
    jadvaldan FARQ. U yerda `updated_at` YOLG'ON va'da bo'lardi (qatorlar
    o'zgarmas), bu yerda esa qator HAQIQATAN o'zgaradi: holat `new` dan
    `in_review` ga, undan `justified` ga o'tadi.
    """

    __tablename__ = "reconciliation_cases"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_reconciliation_cases_market_id_markets"
        ),
        # ⚠⚠ IKKI MUSTAQIL KOMPOZIT FK — DQ-5 ning butun mexanizmi.
        #   Nishon UNIQUE cheklovlari 6-fazadan ALLAQACHON MAVJUD
        #   (`uq_billing_anomalies_market_id_id`, `uq_daily_charges_market_id_id`)
        #   — `0023` ularni YARATMAYDI.
        #
        #   ⛔ `ondelete` YO'Q (NO ACTION): case'i bor dalil qatorini
        #     o'chirish RAD ETILADI. `CASCADE` bo'lganda dalilni o'chirish
        #     uning ustidagi nomuvofiqlik tekshiruvini ham JIMGINA
        #     yo'qotardi.
        ForeignKeyConstraint(
            ["market_id", "anomaly_id"],
            ["billing_anomalies.market_id", "billing_anomalies.id"],
            name="fk_reconciliation_cases_anomaly",
        ),
        ForeignKeyConstraint(
            ["market_id", "charge_id"],
            ["daily_charges.market_id", "daily_charges.id"],
            name="fk_reconciliation_cases_charge",
        ),
        # KOMPOZIT FK NISHONI: `reconciliation_case_events` `(market_id,
        # case_id)` ga havola qiladi.
        UniqueConstraint("market_id", "id", name="uq_reconciliation_cases_market_id_id"),
        CheckConstraint(CASE_STATUS_CHECK, name="status_allowed"),
        CheckConstraint(SUBJECT_KIND_CHECK, name="subject_kind_allowed"),
        CheckConstraint(SUBJECT_IS_EXCLUSIVE_CHECK, name="subject_is_exclusive"),
        CheckConstraint(SUBJECT_KIND_MATCHES_TARGET_CHECK, name="subject_kind_matches_target"),
        CheckConstraint(RESOLUTION_NOTE_LENGTH_CHECK, name="resolution_note_length"),
        # ⚠⚠ D-21 NAQSHI — IKKI QISMAN UNIQUE INDEKS. Ular `__table_args__`
        #   da e'lon qilinishi SHART: modelda yo'q indeks autogenerate'da
        #   «o'chirilgan» bo'lib ko'rinardi (`0020` ning OP-10 darsi).
        Index(
            CASE_SUBJECT_ANOMALY_INDEX,
            "market_id",
            "anomaly_id",
            unique=True,
            postgresql_where=text(CASE_SUBJECT_ANOMALY_PREDICATE),
        ),
        Index(
            CASE_SUBJECT_CHARGE_INDEX,
            "market_id",
            "charge_id",
            unique=True,
            postgresql_where=text(CASE_SUBJECT_CHARGE_PREDICATE),
        ),
        Index(CASE_WORKLIST_INDEX, "market_id", "status", "service_date"),
        Index(CASE_KEYSET_INDEX, "market_id", text("created_at DESC"), text("id DESC")),
    )

    id: Mapped[UUID] = uuid_pk()
    # `sbozor_core.enums.ReconciliationSubjectKind` — YOPIQ diskriminator.
    subject_kind: Mapped[str] = mapped_column(Text(), nullable=False)
    # ⛔ XOR: ikkalasidan AYNAN BITTASI to'ldiriladi
    # (`SUBJECT_IS_EXCLUSIVE_CHECK`).
    anomaly_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    charge_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    # DOMEN sanasi — nomuvofiqlik QAYSI KUN uchun aniqlandi. `daily_charges`
    # va `billing_anomalies` dagi `service_date` bilan AYNAN bir xil ma'no.
    service_date: Mapped[date] = mapped_column(Date(), nullable=False)
    # `sbozor_core.enums.ReconciliationCaseStatus` — yopiq to'rtlik (D-12).
    status: Mapped[str] = mapped_column(
        Text(),
        nullable=False,
        server_default=text(f"'{ReconciliationCaseStatus.NEW.value}'"),
    )
    # `NULL` = hali hech kimga biriktirilmagan. ⛔ `users` ga FK BU YERDA
    # YO'Q: `users` GLOBAL jadval (`GLOBAL_TABLES`) va unga kompozit FK
    # yozib bo'lmaydi; yagona ustunli FK esa `market_id` bilan
    # bog'lanmagani uchun begona bozor xodimini biriktirishni to'xtata
    # olmasdi. Tekshiruv ilova qatlamida, `user_market_roles` ustidan.
    assignee_user_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    # ERKIN MATN, lekin UZUNLIGI CHEKLANGAN (V5). ⚠ Holat esa YOPIQ
    # ro'yxat — ikkisi ATAYIN aralashmaydi (D-14): matn odamga, holat
    # hisobotga gapiradi.
    resolution_note: Mapped[str | None] = mapped_column(Text(), nullable=True)


class ReconciliationCaseEvent(Base, TenantMixin):
    """Case holatining o'zgarishi — YANGI QATOR, tahrir EMAS (D-14).

    =========================================================================
    `charge_adjustments` NING AYNAN NAQSHI VA AYNAN BIR XIL SABABDAN.

    Holatni joyida tahrirlash oldingi holatni O'CHIRARDI — ya'ni «case
    qachon va kim tomonidan `justified` ga o'tkazildi?» savoliga javob
    beradigan yagona ma'lumot yo'qolardi. Nizoda (D-02) aynan shu javob
    dalil bo'ladi.

    Jadval O'ZGARMAS: `0023` unga SHARTSIZ `BEFORE UPDATE OR DELETE`
    qo'riqchisini ulaydi (`occupancy_event_immutable()` / `charge_immutable()`
    shakli). Tarixni qayta yozish — T-07-09 ning aynan tahdidi.
    =========================================================================

    ⛔ `actor_user_id` `NULL` = TIZIM va u YO'Q JAVOB EMAS (`0022` qarori
    bilan bir xil). Case'ni `recon.open` cron TUG'DIRADI, ya'ni birinchi
    hodisa qatorida hech qanday odam yo'q. O'sha qatorga birorta odamning
    `user_id` sini yozish YOLG'ON bo'lardi — «kim qaror qildi?» savoliga
    noto'g'ri odamni ko'rsatgan javob javobning YO'QLIGIDAN yomonroq.

    ⚠ `from_status` NULLABLE: case TUG'ILGANDA oldingi holat YO'Q. Nol
    qiymat («`new` dan `new` ga») yozish tarixni birinchi qatoridanoq
    yolg'on qilardi — `EVENT_STATUS_TRANSITION_CHECK` aynan shuni
    to'xtatadi.

    ⚠ `TimestampMixin` QO'YILMAYDI: `updated_at` o'zgarmas jadvalda YOLG'ON
    VA'DA bo'lardi (`models/billing.py` ning oxirgi bandidagi qoida).
    """

    __tablename__ = "reconciliation_case_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_reconciliation_case_events_market_id_markets",
        ),
        ForeignKeyConstraint(
            ["market_id", "case_id"],
            ["reconciliation_cases.market_id", "reconciliation_cases.id"],
            name="fk_reconciliation_case_events_case",
        ),
        # ⛔ `ondelete` YO'Q — `charge_adjustments.actor_user_id` bilan bir
        #   xil sabab: hodisasi bor foydalanuvchini o'chirish RAD ETILADI.
        ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_reconciliation_case_events_actor_user_id_users",
        ),
        UniqueConstraint("market_id", "id", name="uq_reconciliation_case_events_market_id_id"),
        CheckConstraint(EVENT_FROM_STATUS_CHECK, name="from_status_allowed"),
        CheckConstraint(EVENT_TO_STATUS_CHECK, name="to_status_allowed"),
        CheckConstraint(EVENT_STATUS_TRANSITION_CHECK, name="status_actually_changed"),
        Index("ix_reconciliation_case_events_market_case", "market_id", "case_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    case_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # `NULL` = case TUG'ILDI (oldingi holat yo'q) — klass docstringi.
    from_status: Mapped[str | None] = mapped_column(Text(), nullable=True)
    to_status: Mapped[str] = mapped_column(Text(), nullable=False)
    # ⛔ `NULL` = TIZIM (klass docstringi), «noma'lum» EMAS.
    actor_user_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    # Erkin izoh — holat YOPIQ ro'yxat bo'lib qoladi (D-14).
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NotificationOutbox(Base, TenantMixin, TimestampMixin):
    """Chiquvchi xabar navbati — append-only holat mashinasi (BOT-04, D-20/D-21).

    =========================================================================
    ⛔⛔ BU JADVALDA QAYSI USTUNLAR YO'Q VA NEGA (G7-2, D-03).

    KADR IDENTIFIKATORI, OBYEKT KALITI, TASVIR MANZILI VA TAYYOR XABAR
    MATNI uchun ustun UMUMAN YO'Q. Bu ro'yxat SHU YERDA nomma-nom yozilgan,
    chunki har biri boshqa yo'l bilan qaytib kelishi mumkin:

      * `snapshot_id` / `object_key` / `image_url` -> dalil-kadr Telegramga
        chiqadigan yo'l ochilardi. D-03 buni MUZOKARA QILINMAYDIGAN taqiq
        deb belgilaydi va sabab huquqiy: kadrda tashrifchilar yuzi bor
        (O'zR shaxsiy ma'lumotlar qonuni) va Telegram serverlari
        CHEGARADAN TASHQARIDA. Nomuvofiqlik xabarida dalil HAVOLA bo'lib
        boradi (veb yuzasiga, autentifikatsiya ostida) — BAYT bo'lib
        bormaydi.
      * `text` / `body` / `message` -> tayyor matn sotuvchining ismini,
        rasta kodini va summani BAZAGA yozardi, u yerdan `pg_dump` ->
        restic -> TASHQI BUCKET ga chiqardi (Pitfall 6). Matn `kind` +
        `payload` dan JO'NATISH PAYTIDA quriladi.
      * `chat_id` -> D-26(c): qayta ulanish eski bog'lanishni BEKOR
        QILADI va navbatda turgan xabar ESKI chatga ketmasligi kerak.
        Manzil `vendor_telegram_bindings` dan (yoki direktor uchun
        `market_notification_settings.director_chat_id` dan) jo'natish
        paytida `JOIN` bilan olinadi.

    ⚠ Yo'qlik `07-04` da `information_schema` TO'PLAM TENGLIGI bilan
    o'lchanadi, grep bilan EMAS (G7-2) — grep izohdagi so'zni ham topardi
    va yuqoridagi tushuntirish darvozani o'z-o'ziga qarshi qo'yardi.
    =========================================================================

    ⛔ IDEMPOTENTLIK STRUKTURAVIY (D-21): `UNIQUE (market_id, dedupe_key)`.
    Bir to'lov uchun ikki kvitansiya 6-fazaning T-06-49 bilan AYNAN bir
    sinfdagi xato bo'lardi va u yerda ham yechim `UNIQUE` edi. Kvitansiya
    to'lov bilan BIR TRANZAKSIYADA yoziladi (`dedupe_key =
    f"receipt:{payment_id}"`), ya'ni takroriy `POST /payments` ikkinchi
    xabarni STRUKTURAVIY ravishda yoza olmaydi.

    ⛔ `last_error_type` NOMINING O'ZI SHARTNOMA (D-04): unga faqat
    `type(exc).__name__` yoziladi, HECH QACHON `str(exc)`. Sabab
    o'lchangan: Telegram Bot API ning URL'i BOT TOKENINI tashiydi, ya'ni
    istisno MATNI tokenni logga, bazaga va alertga chiqarardi. Ustun nomida
    `_type` qo'shimchasi ATAYIN — `last_error` deb nomlash xom matn
    yozishga TAKLIF qilardi.

    ⚠ `provider_message_id` — `BIGINT`, `INTEGER` EMAS. Telegram ning
    identifikatorlari 32-bitdan ALLAQACHON oshib ketgan; `INTEGER` ustun
    bir kun `NumericValueOutOfRange` bilan yiqilardi va u AYNAN eng band
    kunda birinchi marta ko'rinardi.

    JADVAL AUDIT TRIGGERIDAN ATAYIN CHIQARILGAN — sabab
    `schema_contract.AUDITED_TABLES` docstringida (qator har daqiqada
    yangilanadi va audit jurnalini TEXNIK SHOVQIN bilan to'ldirardi).
    """

    __tablename__ = "notification_outbox"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_notification_outbox_market_id_markets"
        ),
        # ⚠ NULLABLE KOMPOZIT FK: direktor xabarida `vendor_id` YO'Q va
        #   `RECIPIENT_MATCHES_VENDOR_CHECK` buni ikki tomonlama
        #   majburlaydi (`billing_anomalies.occupancy_event_id` naqshi).
        ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_notification_outbox_vendor",
        ),
        # ⚠⚠ D-21 NING BUTUN MEXANIZMI — bir niyat, bir qator.
        UniqueConstraint(
            "market_id", "dedupe_key", name="uq_notification_outbox_market_id_dedupe_key"
        ),
        UniqueConstraint("market_id", "id", name="uq_notification_outbox_market_id_id"),
        CheckConstraint(OUTBOX_KIND_CHECK, name="kind_allowed"),
        CheckConstraint(OUTBOX_RECIPIENT_KIND_CHECK, name="recipient_kind_allowed"),
        CheckConstraint(OUTBOX_STATUS_CHECK, name="status_allowed"),
        CheckConstraint(RECIPIENT_MATCHES_VENDOR_CHECK, name="recipient_matches_vendor"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        # `payload` OBYEKT bo'lishi shart: massiv yoki skalyar kalit
        # bo'yicha o'qiydigan matn quruvchini JIMGINA yiqitardi
        # (`POLYGON_IS_ARRAY_CHECK` bilan bir xil qaror sinfi).
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_is_object"),
        Index(
            OUTBOX_DUE_INDEX,
            "market_id",
            "next_attempt_at",
            postgresql_where=text(OUTBOX_DUE_PREDICATE),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    # `sbozor_core.enums.OutboxKind` — matn SHUNDAN quriladi (Pitfall 6).
    kind: Mapped[str] = mapped_column(Text(), nullable=False)
    # `sbozor_core.enums.OutboxRecipientKind` — `vendor` / `market_director`.
    recipient_kind: Mapped[str] = mapped_column(Text(), nullable=False)
    # `NULL` = direktor xabari (`recipient_matches_vendor` MAJBURLAYDI).
    vendor_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    # ⛔ D-21 NING KALITI. Shakli `"<kind>:<manba-id>"` — masalan
    #   `receipt:<payment_id>`. Kalit ILOVA tomonidan quriladi, lekin uning
    #   NOYOBLIGINI faqat `UNIQUE` cheklov kafolatlaydi.
    dedupe_key: Mapped[str] = mapped_column(Text(), nullable=False)
    # ⛔ ALLOWLIST BILAN CHEKLANGAN kalitlar (`alerting.py::_detail()`
    #   naqshi) — ro'yxatdan tashqari kalit `ValueError`, ya'ni «kodda
    #   xato, ma'lumot xatosi emas». Tayyor MATN bu yerda EMAS.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    # `sbozor_core.enums.OutboxStatus` — besh holat (D-20).
    status: Mapped[str] = mapped_column(
        Text(), nullable=False, server_default=text(f"'{OutboxStatus.PENDING.value}'")
    )
    attempt_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("0"))
    # Backoff nuqtasi (DQ-3). `429` javobidagi `retry_after` USTUN keladi.
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # IJARA (`FOR UPDATE SKIP LOCKED` bilan birga): tik ikki nusxada
    # yugurganda bir xabar IKKI MARTA jo'natilmasin. `NULL` = ijara yo'q.
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # ⚠ `BIGINT` — Telegram ID lari 32-bitdan oshib ketgan (klass docstringi).
    provider_message_id: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    # ⛔ FAQAT `type(exc).__name__` (D-04) — klass docstringi.
    last_error_type: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_status_code: Mapped[int | None] = mapped_column(Integer(), nullable=True)


class VendorTelegramBinding(Base, TenantMixin):
    """Sotuvchi <-> Telegram bog'lanishi — ALOHIDA JADVAL, ustun EMAS (D-27).

    =========================================================================
    NEGA `vendors` GA USTUN QO'SHILMAYDI.

    D-26(c) qayta ulanishni QONUNIY shox deb belgilaydi: o'sha telefon,
    boshqa Telegram akkaunti (telefon almashtirildi, akkaunt o'g'irlandi,
    oila a'zosining telefoni edi). Ustun bo'lganda eski qiymat USTIGA
    yozilardi va «eski bog'lanish qachon, nega bekor qilindi?» savoli
    javobsiz qolardi — holbuki aynan shu savol nizoda (D-02) «xabar kimga
    ketgan edi?» degan javobni beradi.

    Ya'ni bu jadval TARIX: bekor qilingan qatorlar QOLADI (`revoked_at` +
    `revoked_reason`), faol qator esa qisman UNIQUE indekslar bilan
    BITTAGA cheklanadi.
    =========================================================================

    ⚠ `telegram_user_id` — `BIGINT`, `INTEGER` EMAS. Telegram ning
    foydalanuvchi identifikatorlari 32-bitdan ALLAQACHON oshib ketgan.
    `INTEGER` ustun bugun ishlab, ertaga yangi akkauntda
    `NumericValueOutOfRange` bilan yiqilardi va sabab «bot ishlamayapti»
    bo'lib ko'rinardi.

    ⚠⚠ BOZORLAR ARO BIR `telegram_user_id` BIR NECHA BOG'LANISHGA EGA
    BO'LISHI RUXSAT (`BINDING_TELEGRAM_ACTIVE_INDEX` docstringi): sotuvchi
    ikki bozorda savdo qilishi mumkin va u ikkalasida ham o'z qarzini
    ko'rishi kerak. Cheklov `market_id` bilan boshlanadi, ya'ni u faqat
    bozor ICHIDA ishlaydi.

    ⚠ D-26(b) («bir nechta moslik» -> ulanish YO'Q + anomaliya) BU YERDA
    SXEMA bilan ifodalanmaydi va ifodalanishi ham kerak emas: u
    `vendors` REYESTRIDAGI nuqson (bir bozorda ikki sotuvchida bir xil
    telefon) va uni `uq_vendors_market_id_phone_e164` allaqachon bozor
    ichida imkonsiz qiladi. Shox faqat BOZORLAR ARO ma'noga ega va u
    ilova qatlamida hal qilinadi.

    ⚠ `TimestampMixin` QO'YILMAYDI: qator tug'ilgach faqat BEKOR
    QILINADI (`revoked_at`), ya'ni «oxirgi tahrir vaqti» degan tushuncha
    unga umuman tegishli emas.
    """

    __tablename__ = "vendor_telegram_bindings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_vendor_telegram_bindings_market_id_markets",
        ),
        ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_vendor_telegram_bindings_vendor",
        ),
        UniqueConstraint("market_id", "id", name="uq_vendor_telegram_bindings_market_id_id"),
        # Bekor qilingan bog'lanishda SABAB bor, faolda esa YO'Q — ikki
        # tomonlama tenglik (`REVERSAL_REASON_IS_PAIRED_CHECK` naqshi).
        CheckConstraint(
            "(revoked_at IS NOT NULL) = (revoked_reason IS NOT NULL)",
            name="revocation_is_paired",
        ),
        # ⚠⚠ IKKI QISMAN UNIQUE INDEKS — D-26(c) ning butun mexanizmi.
        Index(
            BINDING_VENDOR_ACTIVE_INDEX,
            "market_id",
            "vendor_id",
            unique=True,
            postgresql_where=text(BINDING_ACTIVE_PREDICATE),
        ),
        Index(
            BINDING_TELEGRAM_ACTIVE_INDEX,
            "market_id",
            "telegram_user_id",
            unique=True,
            postgresql_where=text(BINDING_ACTIVE_PREDICATE),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    vendor_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # ⚠ `BIGINT` — klass docstringi.
    telegram_user_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    # `NULL` = bog'lanish FAOL (qisman indekslarning predikati).
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # `revocation_is_paired` uni `revoked_at` bilan JUFTLIKDA majburlaydi.
    revoked_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MarketNotificationSettings(Base, TenantMixin, TimestampMixin):
    """Bozor kesimidagi bildirishnoma sozlamasi — 1:1 (D-19).

    =========================================================================
    NEGA GLOBAL KONSTANTA EMAS.

    Multi-tenant cheklov ochiq yozilgan: «yangi bozor KOD YOZMASDAN wizard
    orqali ulanadi». Quiet hours va `overdue_days` global konstanta bo'lsa
    ikkinchi bozorning boshqa ish rejimi KOD O'ZGARTIRISHNI talab qilardi —
    ya'ni platformaning butun va'dasi birinchi mijozdayoq buzilardi.

    ⚠ QATOR MAJBURIY EMAS va bu ATAYIN SOZLASH NUQTASI: qator yo'q bo'lsa
    o'quvchilar `COALESCE` bilan quyidagi kod standartlariga tushadi.
    Har bozor uchun majburiy qator wizard'ga yana bir qadam qo'shardi va
    o'sha qadam 300 rastali bozorda hech qanday qiymat bermasdi.
    =========================================================================

    STANDART QIYMATLAR `[ASSUMED]` VA SABABI SHU YERDA:

      * `quiet_hours_start = 21:00`, `quiet_hours_end = 08:00` (A2) —
        sotuvchilar ERTA boshlaydi (kadr olishning birinchi sloti 06:00),
        ya'ni eslatma savdo boshlanishidan OLDIN kelmasligi kerak. Kechki
        chegara esa oilaviy vaqtni himoya qiladi.
        ⛔ KVITANSIYA (CASH-05) BU CHEGARAGA BO'YSUNMAYDI (D-18): u
        sotuvchining HOZIRGINA to'laganini isbotlaydi va uni ertaga
        surish nizo modelini buzardi. Istisno `kind` bo'yicha, `WHERE`
        bandida (Pitfall 7 aynan shu unutishni tasvirlaydi).
      * `overdue_days = 3` (A3) — kichikroq qiymat case navbatini
        SHOVQINGA aylantirardi: bu `alerting.py` ning D-22 bandidagi «75 ta
        xabar olgan admin bildirishnomani o'chiradi» sinfi va u loyihada
        allaqachon bir marta o'lchangan.

    ⛔ `overdue_days` — BOT-03 (sotuvchi eslatmasi) VA `recon.open` (case
    tug'ilishi) uchun AYNAN BIR KNOB. Ikki alohida sozlama ajralib
    ketardi va sotuvchi eslatma olmagan qarz uchun case ochilardi (yoki
    teskarisi) — ya'ni sotuvchi ogohlantirilmagan holda navbatga tushardi.

    ⚠ `market_id` BIRLAMCHI KALIT (1:1), ya'ni bu jadvalda alohida `id`
    ustuni YO'Q. Naqsh loyihada bor: `nvr_credentials` (PK `nvr_id`) va
    `stall_code_registry` (PK `(market_id, code)`). Oqibati SHU YERDA
    yozilgan: `fn_audit_row()` `row_id` ni `uuid` ga keltiradi va `id`
    ustuni yo'q jadvalda har DML da yiqilardi — jadval shuning uchun ham
    `AUDITED_TABLES` ga QO'SHILMAYDI.

    ⚠ `market_profile` GA USTUN QO'SHILMADI va bu ATAYIN (DQ-6): u jadval
    AUDIT ostida va uning diffini bildirishnoma sozlamalari bilan
    aralashtirish «kim ish jadvalini o'zgartirdi?» degan audit savolini
    texnik shovqin bilan ko'mib yuborardi.
    """

    __tablename__ = "market_notification_settings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_market_notification_settings_market_id_markets",
        ),
        # ⚠ `overdue_days` NING IKKI TOMONLAMA CHEGARASI. Yuqori chegara
        #   (90) ham MA'NOLI: undan kattasi eslatmani AMALDA o'chirardi va
        #   «sozladim» degan direktor nazoratni jimgina yo'qotardi.
        CheckConstraint("overdue_days > 0", name="overdue_days_positive"),
        CheckConstraint("overdue_days <= 90", name="overdue_days_bounded"),
    )

    market_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), primary_key=True)
    # [ASSUMED] A2 — klass docstringi.
    quiet_hours_start: Mapped[time] = mapped_column(
        Time(), nullable=False, server_default=text("'21:00'")
    )
    quiet_hours_end: Mapped[time] = mapped_column(
        Time(), nullable=False, server_default=text("'08:00'")
    )
    # [ASSUMED] A3 — klass docstringi. BOT-03 va `recon.open` uchun BIR knob.
    overdue_days: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("3"))
    # ⚠ `BIGINT` — Telegram ID lari 32-bitdan oshib ketgan. `NULL` =
    #   direktor hali botga ulanmagan, ya'ni dayjest jo'natilmaydi (va bu
    #   XATO EMAS: jo'natuvchi bunday qatorni `blocked` ga emas, o'z
    #   navbatiga umuman qo'ymaydi).
    director_chat_id: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
