"""core-api konfiguratsiyasi — 12-faktor uslubida, muhit o'zgaruvchilaridan.

Sirlar (JWT_SECRET, DB parollari) HECH QACHON kodda yoki repoda saqlanmaydi —
ular faqat muhitdan keladi (`.env` gitignore'da, `.env.example` da faqat
kalit nomlari).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sbozor_core.models.occupancy import POLYGON_MAX_VERTICES, POLYGON_MIN_VERTICES

from app.services.quality import QUALITY_THRESHOLDS_VERSION, QualityThresholds

# PyJWT 2.11+ HS256 uchun kalit uzunligini majburiy tekshiradi
# (RFC 7518 §3.2: kalit >= hash chiqishi = 256 bit = 32 bayt).
MIN_JWT_SECRET_BYTES = 32

MAX_TIMES_PER_DAY = 12
"""Kuniga eng ko'p slot — SERVERDAGI qattiq shift (`04-UI-SPEC.md` §4.6).

Arifmetika: 12 x 25 kamera = 300 kadr/kun ~ 6,5 GB/yil. Chegarasiz «har 5
daqiqada» esa 4 225 kadr/kun beradi va bu Contabo diskini bir necha oyda
to'ldirardi.

⚠ MIJOZDAGI CHEGARA XAVFSIZLIK CHEGARASI EMAS. UI 12 tani ko'rsatadi,
  lekin API'ga to'g'ridan-to'g'ri so'rov yuborish uni butunlay chetlab
  o'tadi. Shuning uchun ayni son SERVERDA ham majburlanadi.

⚠ `SNAPSHOT_MAX_TIMES_PER_DAY` bu sondan YUQORI qo'yilishi mumkin EMAS —
  faqat pasaytiriladi. Shiftni ko'tarish UI va serverni BIRGA o'zgartirishni
  talab qiladi, ya'ni u kod qarori, muhit o'zgaruvchisining qarori emas.
  Aks holda ikkalasi jimgina ajralib ketardi.
"""


class Settings(BaseSettings):
    """core-api ish vaqti sozlamalari."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Ma'lumotlar bazasi ---
    # ILOVA roli (sbozor_app): NOSUPERUSER + NOBYPASSRLS.
    # Bu yerga `postgres` superuseri berilsa tenant izolyatsiyasi butunlay
    # yo'qoladi va hech bir test buni ko'rsatmaydi.
    database_url: str
    # DDL egasi (sbozor_owner) — faqat Alembic `migrate` jobida ishlatiladi.
    migration_database_url: str = ""

    # --- Kesh / navbat ---
    valkey_url: str

    # --- Auth ---
    jwt_secret: str
    jwt_issuer: str = "sbozor"
    jwt_audience: str = "sbozor-api"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    # Dev'da HTTP -> false; prod'da (TLS ortida) true bo'lishi SHART.
    cookie_secure: bool = False

    # --- Excel import chegaralari (02-12, A7) ---
    #
    # Chegaralar SOZLANADIGAN, chunki A7 ning o'zi ularni taxmin deb
    # belgilaydi: "1000 rastadan kattaroq bozor kelganda chegaraga
    # urilinadi (sozlanadigan qilinsin)". Standart qiymatlar
    # `app/services/xlsx_reader.py` dagi modul konstantalari bilan AYNAN
    # bir xil va o'sha yerda `test_default_limits_match_the_documented_
    # values` bilan qulflangan — ya'ni bittasini o'zgartirish ikkinchisini
    # jimgina eskirtira olmaydi.
    #
    # Ikkita hajm chegarasi MUSTAQIL va ikkalasi ham majburiy:
    # `import_max_upload_bytes` — tarmoqdan kelgan XOM bayt (`.xlsx` = ZIP),
    # `import_max_uncompressed_bytes` — o'sha ZIP OCHILGANDAGI hajmi.
    # 1 MB fayl 10 GB ga ochilishi mumkin, ya'ni birinchisi ikkinchisidan
    # hech qanday himoya bermaydi (T-02-88).
    import_max_upload_bytes: int = 5 * 1024 * 1024
    import_max_uncompressed_bytes: int = 50 * 1024 * 1024
    import_max_rows: int = 5_000
    import_max_cols: int = 32
    import_max_sheets: int = 8
    import_max_zip_entries: int = 200

    # Xodimlar rosteri (02-24, MARKET-07) — `import_max_rows` DAN ALOHIDA
    # va ATAYIN ancha tor. Ikki mustaqil sabab:
    #
    #   1. HAJM: xodimlar ro'yxati o'nlab kishilik (Karmanada ~10–30),
    #      rastalar ro'yxati esa mingtacha. Bitta chegara ikkalasiga ham
    #      to'g'ri kelmaydi.
    #   2. NARX VA YUZA: har qator Argon2id hash'lash talab qiladi (CPU
    #      bo'yicha ATAYIN qimmat) va har qator platformadagi telefon
    #      band-emasligini oshkor qiladi (T-02-181). 5000 qatorli fayl
    #      butun ishchini bloklab, bir so'rovda 5000 raqamni sanab
    #      chiqish imkonini berardi.
    import_max_staff_rows: int = 200

    # --- NVR rekvizitlari (03-04, SC#4) ---
    #
    # Shifr kaliti `JWT_SECRET` DAN ALOHIDA va bu ATAYIN — ikki xil xavf
    # modeli. JWT kaliti almashtirilsa sessiyalar tushadi (arzon, o'z-o'zidan
    # tuzaladi); shifr kaliti almashtirilsa MA'LUMOT YO'QOLADI (qimmat,
    # tuzalmaydi). Bitta sirdan ikkalasiga foydalanish birinchisining
    # arzon rotatsiyasini ikkinchisining qimmat rotatsiyasiga bog'lab
    # qo'yardi.
    #
    # STANDART QIYMAT YO'Q va bu ham ATAYIN: bo'sh standart bilan ilova
    # shifrlashsiz KO'TARILARDI va xato faqat birinchi rekvizit yozilganda
    # ko'rinardi (T-03-22 aynan shu xulqni rad etadi).
    #
    # ⚠ TIP `SecretStr`, ODDIY `str` EMAS — va bu O'LCHANGAN qaror.
    #   `BaseSettings` ning `repr` i BARCHA maydonlarni chop etadi, Sentry
    #   esa istisno paytida LOKAL O'ZGARUVCHILARNI yig'adi. `lifespan` da
    #   `settings` aynan lokal o'zgaruvchi (`main.py:99`), ya'ni ilova
    #   ko'tarilayotganda yuz bergan har qanday istisno butun shifr kalitini
    #   Sentry'ga yuborardi. Kalit oshkor bo'lsa BARCHA NVR parollari —
    #   o'tmishdagilari ham — ochiladi, ya'ni bu yagona eng qimmat sir.
    #   `SecretStr` uni `repr` da `**********` ga aylantiradi
    #   (`03-RESEARCH.md` C.10 ni ichki qiymatlar uchun aynan shu tavsiya).
    #   Qiymatga borish faqat `.get_secret_value()` orqali — ya'ni chegara
    #   grep bilan topiladigan va ko'zga tashlanadigan bo'ladi.
    nvr_credential_key: SecretStr
    # Iste'foga chiqqan kalitlar, VERGUL bilan ajratilgan (ixtiyoriy).
    # Rotatsiya hali bo'lmagan o'rnatmada bo'sh — majburiy qilinsa har bir
    # yangi o'rnatma soxta qiymat yozishga majbur bo'lardi.
    # Semantikasi: `app/security/secrets.py::build_cipher` — birinchi kalit
    # YOZADI, hammasi O'QIYDI. Tip yuqoridagi bilan bir xil sababdan
    # `SecretStr`: bu ham AYNAN o'sha kalit materiali.
    nvr_credential_keys_retired: SecretStr = SecretStr("")

    # --- Jonli ko'rish (03-07, D-11) ---
    #
    # go2rtc ning ICHKI manzili — u compose tarmog'idan tashqarida
    # MAVJUD EMAS va xost portiga publish qilinmaydi (`compose.yaml`).
    #
    # ⚠ STANDART QIYMAT BOR va bu `nvr_credential_key` bilan qarama-qarshi
    #   emas: bu maydon SIR emas, u compose xizmatining nomi. Majburiy
    #   qilinsa har bir test/CI muhiti uni takrorlashga majbur bo'lardi,
    #   bo'sh qoldirilsa esa jonli ko'rish yo'li ish paytida tushunarsiz
    #   xato berardi. Standart — mahsulot topologiyasining o'zi.
    go2rtc_url: str = "http://go2rtc:1984"

    # --- Snapshot ombori (04-01/04-06, CAM-07) ---
    #
    # S3-mos ombor — `storage` xizmati (SeaweedFS). Endpoint compose
    # tarmog'ining ICHIDA: ombor xost portiga publish QILINMAYDI (T-04-02).
    #
    # ⚠ MANZIL VA BUCKET DA STANDART QIYMAT BOR, KALITLARDA — YO'Q. Bu
    #   `go2rtc_url` bilan bir xil ajratish: manzil mahsulot TOPOLOGIYASI
    #   (sir emas, har CI muhitida takrorlanishi bekorchilik), kalitlar esa
    #   SIR. Bo'sh standart bilan servis ko'tarilardi va nosozlik ertalab
    #   06:00 da, birinchi yuklashda `SignatureDoesNotMatch` bo'lib chiqardi
    #   — ya'ni butun kunlik reja yo'qolgandan KEYIN (T-04-29).
    #
    # ⚠ KALITLARDA STANDART QIYMAT `""` VA U `nvr_credential_key` NING
    #   «standartsiz» QARORIDAN FARQ QILADI — sabab MEXANIK, xavfsizlik
    #   emas, va kafolat AYNAN O'SHA:
    #
    #     standartsiz  -> pydantic "Field required" beradi;
    #     `""` + validator -> BIZNING xabarimiz beriladi.
    #
    #   Ikkala yo'lda ham `Settings()` ISHGA TUSHISHDA yiqiladi (maydon
    #   yetishmasa `""` ga tushadi, validator esa uni rad etadi), ya'ni
    #   himoya bir xil. Farq FAQAT xabar sifatida: bizniki `ops/seaweedfs/
    #   s3.json` ga yo'l ko'rsatadi, pydantic'niki esa yo'q.
    #
    #   Standartsiz variant BUNDAN TASHQARI mavjud `Settings(...)`
    #   chaqiruvlarini (`tests/conftest.py`, `test_nvr_secrets.py`) mypy
    #   darajasida buzardi — ular bu rejaning fayllari EMAS. Ya'ni
    #   standartsiz shakl xavfsizlikni oshirmasdan begona fayllarga
    #   o'zgarish talab qilardi.
    s3_endpoint_url: str = "http://storage:8333"
    s3_bucket: str = "sbozor-snapshots"
    s3_access_key: str = ""
    s3_secret_key: SecretStr = SecretStr("")
    # SeaweedFS mintaqani E'TIBORSIZ qoldiradi, lekin `botocore` uni
    # TALAB qiladi (`region_name` siz klient umuman qurilmaydi). Ya'ni bu
    # qiymat SeaweedFS uchun ma'nosiz va klient uchun majburiy — u
    # o'zgaradigan yagona holat AWS S3 yoki O'zbekiston bulutiga ko'chish.
    s3_region: str = "us-east-1"

    # --- Kadr olish orkestratsiyasi (04-05/04-07, CAM-05) ---
    #
    # Slot vaqti o'tgach kadr olish uchun beriladigan muhlat. Undan keyin
    # slot `missed` bo'lib YO'QLIK YOZUVI sifatida qoladi.
    #
    # ⚠ SABAB MAHSULOTDA, TEXNIKADA EMAS: 06:00 sloti 07:05 da olingan kadr
    #   «06:00 da rasta band edimi?» savoliga JAVOB BERMAYDI. Kechikkan kadr
    #   yo'q kadrdan YOMONROQ — u savolga javob bermaydi, lekin javob
    #   berganday ko'rinadi. 600 s — D-08 arifmetikasi: 25 kamera to'liq
    #   ketma-ket ~100 s, ya'ni oltibarobar zaxira.
    capture_grace_seconds: Annotated[int, Field(ge=1)] = 600
    # Bitta NVR ga bir vaqtda nechta kadr so'rovi ketadi (D-08). Standart 1
    # (ketma-ket): NVR ning O'LCHANMAGAN sessiya chegarasi shu bilan fazani
    # HECH QACHON bloklay olmaydi, faqat kechikish narxini beradi.
    capture_global_concurrency: Annotated[int, Field(ge=1)] = 1
    # ⚠ `401`/`403` da retry QILINMAYDI — Hikvision hisobni ~5 urinishdan
    #   keyin qulflaydi (03-05 dan meros teskari retry siyosati). Ro'yxat
    #   `app/services/capture_errors.py::CAPTURE_AUTH_LOCKING_CODES` da.
    capture_max_attempts: Annotated[int, Field(ge=1)] = 3
    # `capture_runs` qatorining ijarasi: worker yiqilsa qator shu muddatdan
    # keyin qayta olinadigan bo'ladi. `capture_grace_seconds` dan KICHIK
    # bo'lishi kerak, aks holda yiqilgan worker slotni grace oynasi
    # tugagunicha ushlab turardi.
    capture_lease_seconds: Annotated[int, Field(ge=1)] = 120
    # Bitta tikda olinadigan qator soni — bazani bir marta uzoq
    # bloklamaslik uchun.
    capture_batch_size: Annotated[int, Field(ge=1)] = 50
    # Server tomonidagi qattiq chegara (yuqoridagi `MAX_TIMES_PER_DAY`).
    snapshot_max_times_per_day: Annotated[int, Field(ge=1, le=MAX_TIMES_PER_DAY)] = (
        MAX_TIMES_PER_DAY
    )
    # Jadval sahifasi «keyingi {n} kunda qoplanmagan kun bormi?» savolini
    # shu ufq ichida beradi (`04-UI-SPEC.md` §4.3 — `uncovered_horizon_days`).
    #
    # ⚠ UFQ JAVOBDA HAM QAYTADI, faqat sanoq emas. «3 kun qoplanmagan»
    #   jumlasi qaysi oyna ustida aytilganini bilmasa ma'nosiz bo'lardi:
    #   90 kunlik oynadagi 3 kun bilan 7 kunlik oynadagi 3 kun butunlay
    #   boshqa shoshilinchlik darajasi.
    schedule_horizon_days: Annotated[int, Field(ge=1)] = 90

    # --- O'z-o'zini kuzatish (04-09, FOUND-06, D-20) ---
    #
    # `system_heartbeats.last_seen_at` shu muddatdan eski bo'lsa komponent
    # ESKIRGAN hisoblanadi. `capture_tick` har DAQIQADA uradi, ya'ni 10
    # daqiqa — o'nbarobar zaxira: bitta o'tkazib yuborilgan tik (deploy,
    # qisqa tarmoq uzilishi) alert bermaydi, o'lgan worker esa beradi.
    self_check_stale_minutes: Annotated[int, Field(ge=1)] = 10

    # --- Saqlash siyosati (04-08, CAM-07, D-18) ---
    #
    # 90 kun to'liq sifat + 365 kun siqilgan = 455 kun. IKKALA QIYMAT HAM
    # SOZLAMA va bu D-18 ning butun mazmuni: buyurtmachi javobiga qarab
    # BITTA SON o'zgaradi, kod emas.
    #
    # ⚠ `0` QONUNIY qiymat («to'liq sifatda umuman saqlanmasin»), manfiy —
    #   emas. Manfiy muddat retention so'rovini kelajakka yo'naltirib,
    #   hali olinmagan kadrlarni o'chirishga urinardi.
    retention_full_days: Annotated[int, Field(ge=0)] = 90
    retention_compressed_days: Annotated[int, Field(ge=0)] = 365
    # Siqishdan keyingi JPEG sifati. Yuqori chegara 95 — Pillow shkalasi
    # (`tests/fixtures/frames.py::_validate` bilan bir xil chegara).
    retention_jpeg_quality: Annotated[int, Field(ge=1, le=95)] = 60
    retention_batch_size: Annotated[int, Field(ge=1)] = 200

    # --- Sifat filtri chegaralari (04-04, CAM-06, D-14/D-15) ---
    #
    # ⚠ BU QIYMATLAR ATAYIN `LOW CONFIDENCE`. Real Karmana kadri HALI YO'Q,
    #   ya'ni har qanday raqam TAXMIN. Lekin qoidaning SHAKLI (ikki shartli
    #   `dark`, `stddev` ga tayangan `blank`) ma'lumotsiz ham himoyalanadi —
    #   u qonuniy qish-tong kadri argumentidan kelib chiqadi, o'lchovdan
    #   emas.
    #
    # ⚠ SOZLASH QAYTA KADR OLISHNI TALAB QILMAYDI (D-15): o'lchovlarning
    #   O'ZI (`snapshots.quality_mean`, `quality_stddev`, `quality_
    #   saturation`) saqlanadi. Phase 0 ning real kadrlari kelganda chegara
    #   `percentile_cont` bilan TAQSIMOTDAN olinadi va bu bitta SQL
    #   so'rovi bo'ladi.
    #
    # ⚠ CHEGARANI O'ZGARTIRISH O'TMISHNI QAYTA YOZMAYDI: verdikt yozish
    #   paytida qo'yiladi va `quality_thresholds_version` u qaysi to'plam
    #   bilan qo'yilganini yozadi.
    quality_min_bytes: Annotated[int, Field(ge=1)] = 4096
    quality_max_bytes: Annotated[int, Field(ge=1)] = 8 * 1024 * 1024
    quality_blank_stddev_max: Annotated[float, Field(ge=0.0)] = 3.0
    quality_dark_mean_max: Annotated[float, Field(ge=0.0)] = 25.0
    quality_dark_stddev_max: Annotated[float, Field(ge=0.0)] = 12.0
    quality_ir_saturation: Annotated[float, Field(ge=0.0, le=1.0)] = 0.05
    quality_night_mean: Annotated[float, Field(ge=0.0)] = 110.0

    # --- Kamera zonalari (05-06, AI-01, D-07) ---
    #
    # ⚠ KLIENTDAGI CHEGARA — QULAYLIK, XAVFSIZLIK CHEGARASI SHU YERDA.
    #   `frontend/src/lib/zone-geometry.ts::MAX_VERTICES_PER_ZONE` va
    #   `MAX_ZONES_PER_CAMERA` adminlarga chegaraga urilganini DARHOL
    #   ko'rsatadi, lekin ular `curl` bilan chetlab o'tiladi. Bu
    #   qiymatlar `validate_polygon()` ga ARGUMENT bo'lib kiradi — sof
    #   modul `Settings` ni bilmaydi (§S-8, D-11 naqshi).
    #
    # ⚠ YUQORI CHEGARA `POLYGON_MAX_VERTICES` DAN OLINADI, LITERAL EMAS.
    #   Sozlamani DB `CHECK` idan (12) yuqoriga qo'yish mumkin bo'lsa,
    #   13 tepali poligon ilova darvozasidan O'TIB, bazada `23514` bilan
    #   rad etilardi. `_zone_conflict()` uni tanimasdi va admin
    #   `zone_polygon_too_many_points` o'rniga 500 ko'rardi. Pastga
    #   qo'yish (qat'iyroq) esa QONUNIY va u kutilgan sozlash yo'li.
    zone_max_vertices: Annotated[int, Field(ge=POLYGON_MIN_VERTICES, le=POLYGON_MAX_VERTICES)] = (
        POLYGON_MAX_VERTICES
    )
    # Kutilgan qiymat 10–40; 60 — zaxira (05-UI-SPEC §6.5). Chegarasiz
    # bitta kamera uchun cheksiz poligon yozib, kunlik bandlik hisobini
    # sekinlashtirish mumkin edi (T-05-23).
    zone_max_per_camera: Annotated[int, Field(ge=1)] = 60
    # Kadr nisbati farqining ruxsat etilgan chegarasi (§6.8).
    #
    # ⚠ SOZLAMA, ROUTERDAGI LITERAL EMAS: `aspect_ratio_matches()` uni
    #   ARGUMENT sifatida oladi (`Settings` ni bilmaydi), ya'ni qiymat
    #   baribir biror joyda yozilishi kerak. Router ichida qolsa u
    #   `quality_*` chegaralari bilan bir xil sinfdagi raqam bo'lib
    #   turib, ularning yonida KO'RINMASDI.
    #
    # ⚠⚠ 0,05 — VA U «EHTIYOT UCHUN KENG» EMAS, O'LCHANGAN ZARURIYAT.
    #
    #   Joriy kadr o'lchami `snapshots.width`/`height` dan olinadi, ular
    #   esa `quality.py::analyze()` ning `draft("RGB", (320, 180))`
    #   natijasi — ya'ni DEKODLANGAN (kichraytirilgan) o'lcham, kadrning
    #   haqiqiy o'lchami EMAS. Pillow `draft()` ni ikkala o'qqa BIR XIL
    #   ko'paytuvchi bilan qo'llaydi, ya'ni NISBAT saqlanadi — lekin
    #   natija `ceil()` bilan yaxlitlanadi va 1/8 masshtabda (1920x1080 ->
    #   240x135) har o'qdagi bir pikselli farq nisbatni ~0,013 ga
    #   siljitishi mumkin. 0,01 tolerans bilan bu HAR ZONANI «tekshirish
    #   kerak» qilib, bayroqni butunlay ma'nosiz qilardi — admin uni
    #   birinchi haftadayoq e'tiborsiz qoldirardi va HAQIQIY nisbat
    #   o'zgarishi shovqin ostida ko'milardi.
    #
    #   0,05 esa 16:9 (1,7778) va 4:3 (1,3333) orasidagi farqdan (0,4444)
    #   TO'QQIZ barobar kichik, ya'ni haqiqiy nisbat o'zgarishi baribir
    #   ishonchli ushlanadi.
    zone_aspect_tolerance: Annotated[float, Field(gt=0.0, le=1.0)] = 0.05

    # --- 05-10: nazoratchi navbatlari (AI-03/AI-04, D-13) ---
    #
    # ⛔ IKKALA BYUDJET HAM SOZLAMA VA BU O'YLANGAN QAROR. «Nazoratchi
    #   kuniga 30 bandni ulgurayaptimi?» — INSON o'lchovi va uning javobi
    #   `05-HUMAN-UAT` da, kodda emas. Qiymatni kodda qotirish o'sha
    #   savolni «sozlanmaydigan haqiqat» qilib ko'rsatardi.
    #
    # ⚠ BYUDJET — KVOTA EMAS, DIQQAT CHEGARASI (`REVIEW_BUDGET_EXHAUSTED`
    #   docstringi). Uni oshirish charchagan holda berilgan javoblarni
    #   ma'lumotga aylantiradi va AYNAN o'sha ma'lumot bilan tizim
    #   aniqligi o'lchanadi — ya'ni chegarani yumshatish o'lchov
    #   asbobining o'zini buzadi.
    review_uncertain_daily_budget: Annotated[int, Field(ge=1)] = 50
    # ⚠ 30 — D-13 ning O'LCHANGAN qiymati: oylik ±2–3 f.p. aniqlik
    #   oralig'i. Uni PASAYTIRISH oraliqni kengaytiradi, ya'ni hisobotning
    #   «aniqlik 92%» da'vosi kuchsizlanadi — bu qulaylik emas, O'LCHOV
    #   qarori. Bugun uni FAQAT `GET /review/budget` o'qiydi; ko'r audit
    #   tortishining O'ZI 05-11 da.
    review_blind_daily_budget: Annotated[int, Field(ge=1)] = 30
    # Noaniq oynaning O'RTASI — «chegaraga yaqinlik» ustuvorligining
    # o'lchov nuqtasi (05-RESEARCH §C.9: klassik uncertainty sampling).
    #
    # ⛔ BU SON DARVOZA EMAS, FAQAT TARTIB. Uni `cv-service` dagi
    #   `UNCERTAIN_THRESHOLDS = (0.30, 0.60)` bilan sinxron ushlab
    #   turadigan MEXANIZM ATAYIN YO'Q va sabab shu ustunda: qiymat faqat
    #   `ORDER BY` ga kiradi, ya'ni drift navbat TARTIBINI biroz
    #   o'zgartiradi va birorta HUKMGA tegmaydi. Ikki kod bazasini bitta
    #   songa mexanik bog'lash (05-08 dagi navbat nomi darvozasi kabi)
    #   bu yerda o'z narxini oqlamaydi — u yerda ajralish JIM NOSOZLIK
    #   berardi, bu yerda esa faqat suboptimal tartib.
    #
    # ⚠ 0,45 = (0.30 + 0.60) / 2. Chegaralar qatorda yashaydi (D-11) va
    #   `thresholds_version` bilan o'zgaradi; o'shanda bu qiymat ham
    #   `.env` dan sozlanadi — migratsiya kerak emas.
    review_uncertain_midpoint: Annotated[float, Field(ge=0.0, le=1.0)] = 0.45

    # --- Telegram alertlari (04-08, FOUND-06) ---
    #
    # ⚠ S3 KALITLARIDAN TESKARI: bo'sh qiymat — QONUNIY holat. Bo'sh token
    #   «alertlar o'chiq» degani, jarayon bir marta `log.warning` yozadi va
    #   kadr olish DAVOM ETADI. Alertsiz kadr — alertli kadrsizlikdan
    #   yaxshiroq (D-19): token ustida yiqilish butun quvurni to'xtatardi.
    #
    # ⚠ LEKIN JIMGINA ISHLAMAYDI. Bo'sh token bilan `log.warning` siz
    #   ishlash aynan «alert bor deb o'ylash» yolg'onini tug'diradi va u
    #   D-20 ning («alert muvaffaqiyat signalining YO'QLIGIGA qo'yiladi»)
    #   bevosita buzilishi bo'lardi. Ogohlantirishni `04-08` ning
    #   jo'natuvchisi yozadi va uning darvozasi o'sha rejada.
    #
    # ⚠ TIP `SecretStr`: bot tokeni bilan istalgan odam bot nomidan xabar
    #   yubora oladi va uning yozishmalarini o'qiy oladi.
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""

    # --- Kuzatuv ---
    sentry_dsn: str = ""
    log_level: str = "info"

    @property
    def alerts_enabled(self) -> bool:
        """Alert jo'natish MUMKINMI — HOSILA qiymat, alohida bayroq EMAS.

        ⚠ Alohida `ALERTS_ENABLED` bayrog'i uchinchi holatni ochardi:
          «yoqilgan, lekin tokensiz». O'shanda tizim alert jo'natishga
          urinib, har safar yiqilardi va nosozlik jurnalda ko'milib
          qolardi. Hosila qiymatda bunday holat MAVJUD EMAS.

        Ikkala qiymat ham talab qilinadi: chat ID'siz token bilan xabar
        yuborib bo'lmaydi va teskarisi ham.
        """
        return bool(self.telegram_bot_token.get_secret_value() and self.telegram_chat_id)

    def quality_thresholds(self) -> QualityThresholds:
        """Sifat filtri uchun chegaralar to'plami.

        ⚠ IMPORT YO'NALISHI: `settings.py` -> `services/quality.py`, aksincha
          EMAS. Sof modul sozlamani BILMAYDI — shunda uni testda argument
          bilan chaqirish mumkin bo'ladi va test muhitga bog'lanmaydi
          (`test_quality_filter.py` docstringi).
        """
        return QualityThresholds(
            min_bytes=self.quality_min_bytes,
            max_bytes=self.quality_max_bytes,
            blank_stddev=self.quality_blank_stddev_max,
            dark_mean=self.quality_dark_mean_max,
            dark_stddev=self.quality_dark_stddev_max,
            ir_saturation=self.quality_ir_saturation,
            night_mean=self.quality_night_mean,
            version=QUALITY_THRESHOLDS_VERSION,
        )

    @field_validator("s3_access_key")
    @classmethod
    def _validate_s3_access_key(cls, value: str) -> str:
        """Bo'sh ombor kalitini ISHGA TUSHISHDA rad etadi (T-04-29).

        `_validate_jwt_secret` naqshi. Xato matnida KALIT NOMI bor, lekin
        QIYMAT yo'q — rad etilgan qiymat ta'rifi bo'yicha ishonchsiz.
        """
        if not value.strip():
            raise ValueError(
                "S3_ACCESS_KEY bo'sh bo'lishi mumkin emas. U "
                "`ops/seaweedfs/s3.json` dagi qiymat bilan AYNAN bir xil "
                "bo'lishi shart (`ops/seaweedfs/README.md`)."
            )
        return value

    @field_validator("s3_secret_key")
    @classmethod
    def _validate_s3_secret_key(cls, value: SecretStr) -> SecretStr:
        """Bo'sh ombor maxfiy kalitini ISHGA TUSHISHDA rad etadi (T-04-29)."""
        if not value.get_secret_value().strip():
            raise ValueError(
                "S3_SECRET_KEY bo'sh bo'lishi mumkin emas. U "
                "`ops/seaweedfs/s3.json` dagi qiymat bilan AYNAN bir xil "
                "bo'lishi shart (`ops/seaweedfs/README.md`)."
            )
        return value

    @field_validator("nvr_credential_key")
    @classmethod
    def _validate_nvr_credential_key(cls, value: SecretStr) -> SecretStr:
        """Kalit formatini ISHGA TUSHISHDA tekshiradi (`_validate_jwt_secret` naqshi).

        Noto'g'ri kalit bilan ilova ko'tarilib, birinchi kamera qo'shilganda
        yiqilishi eng yomon variant bo'lardi: xato NVR bilan bog'liqday
        ko'rinardi va operator tarmoqni, parolni va NVR ni tekshirib
        vaqt yo'qotardi.

        Xato matni kalitning O'ZINI TAKRORLAMAYDI — faqat format talabi va
        hosil qilish buyrug'i beriladi.

        ⚠ O'LCHANGAN CHEKLOV, YASHIRILMAYDI: pydantic ning O'ZI
          `ValidationError.__str__` ga `input_value=...` ni qo'shadi, ya'ni
          RAD ETILGAN qiymat baribir xabarga tushadi. Bu bizning matnimizga
          bog'liq emas va uni yozib bo'lmaydi: `SecretStr` ham, `mode=
          "after"` model validatori ham buni to'sib qololmadi (ikkalasi ham
          empirik sinaldi — pydantic XOM kiritmani chop etadi). Xuddi shu
          xulq `_validate_jwt_secret` da ham bor, ya'ni bu shu maydon
          kiritgan yangi teshik emas.
          Amaliy oqibati TOR: chop etiladigan qiymat ta'rifi bo'yicha
          ISHLAMAYDIGAN kalit va bu yo'l faqat ilova ko'tarilmaganda ochiladi
          (Sentry hali sozlanmagan — `main.py` uni sozlamalardan KEYIN
          ishga tushiradi, ya'ni xabar faqat konteyner stderr'iga boradi).
          `SecretStr` esa MUVAFFAQIYATLI ko'tarilgan holatdagi ancha kengroq
          yo'lni — `repr(settings)` va Sentry ning lokal o'zgaruvchilar
          yig'ishini — yopadi.
        """
        try:
            Fernet(value.get_secret_value().encode())
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "NVR_CREDENTIAL_KEY — Fernet kaliti bo'lishi kerak "
                "(base64url, 32 bayt). Hosil qilish: "
                'python -c "from cryptography.fernet import Fernet;'
                'print(Fernet.generate_key().decode())"'
            ) from exc
        return value

    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret(cls, value: str) -> str:
        if len(value.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
            raise ValueError(
                f"JWT_SECRET kamida {MIN_JWT_SECRET_BYTES} bayt bo'lishi kerak. "
                'Hosil qilish: python -c "import secrets;print(secrets.token_urlsafe(48))"'
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Sozlamalarni bir marta o'qiydi va keshlaydi."""
    # mypy majburiy maydonlarni argument sifatida kutadi, lekin pydantic-settings
    # ularni MUHITDAN to'ldiradi (pydantic mypy plagini atayin yoqilmagan).
    # Yetishmayotgan qiymat ish vaqtida `ValidationError` beradi — bu kutilgan xulq.
    return Settings()  # type: ignore[call-arg]
