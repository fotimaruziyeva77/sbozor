# Faza 4: Snapshot pipeline — Tadqiqot

**Tadqiqot sanasi:** 2026-08-04
**Domen:** rejalashtirilgan kadr olish (scheduled capture), idempotent orkestratsiya, sifat filtri, S3 obyekt-ombor, yo'qlikka alert (alert-on-absence)
**Ishonch darajasi:** MEDIUM-HIGH — orkestratsiya va sxema **HIGH** (`taskiq` manbasi o'qildi va o'lchandi, PyPI metadata tekshirildi); sifat chegaralari **LOW** (real Karmana kadri yo'q — ataylab sozlanadigan); NVR sessiya chegarasining namoyon bo'lishi **LOW** (3-fazadan meros)

> **HOLAT: TO'LIQ.** Barcha bo'limlar (A–E) va Validation Architecture yozilgan.

---

## Xulosa

Bu faza **ikkita qaror** atrofida aylanadi va qolgan hammasi ulardan kelib chiqadi. **Birinchi qaror — orkestratsiya** (ROADMAP Open Decision #2). ROADMAP uni «DB-materialized `capture_runs` + `SKIP LOCKED` **vs** `taskiq`» deb qo'ygan, lekin bu tadqiqotning asosiy topilmasi shuki — **ular muqobil emas, ular bir muammoning ikki yarmi**. `taskiq` ning planerini o'qib chiqish (o'rnatilgan 0.12.4 manbasi) uchta o'lchangan faktni berdi: (a) planer **alohida jarayon**; (b) cron ning «oxirgi ishga tushish» holati **jarayon xotirasida** (`SchedulerLoop.cron_tasks_last_run` — oddiy `dict`), ya'ni **qayta ishga tushishdan omon qolmaydi**; (c) hech qanday taqsimlangan qulf yo'q, ya'ni ikkita planer jarayoni har slotni **ikki marta** ishga tushiradi. Bu uchtasi birgalikda «har slot uchun bitta cron» yondashuvini **CAM-05 ning o'z matni bilan** rad etadi: «o'tkazib yuborilgan slot jurnalda ochiq ko'rinadi» — xotiradagi cron o'tkazib yuborilgan slotni **hech qanday iz qoldirmasdan** yo'qotadi. Shuning uchun tavsiya: `taskiq scheduler` **faqat soat** bo'ladi (bitta, `* * * * *` shaklidagi holatsiz tick), reja/lease/idempotentlik/yo'qlik yozuvi esa **Postgres `capture_runs`** da yashaydi. Tick **konstruksiyasi bo'yicha idempotent** bo'lgani uchun `taskiq` ning uchala yiqilish rejimi ham zararsizlanadi — o'tkazib yuborilgan tick keyingi tickda tiklanadi, dublikat tick `FOR UPDATE SKIP LOCKED` da hech nima olmaydi, ikkinchi planer jarayoni esa dublikat tickdan farq qilmaydi.

**Ikkinchi qaror — «yo'qlikni ko'rinadigan qilish»**. CAM-05 va FOUND-06 ikkalasi ham xato haqida emas, **yo'qlik** haqida: «slot o'tkazib yuborildi» va «backup muvaffaqiyat signali kelmadi». Yo'qlikni so'rov bilan topib bo'lmaydi — u faqat **kutilgan narsa oldindan yozilgan** bo'lsa ko'rinadi. Shuning uchun kunlik reja (bozor × kamera × slot = ~175 qator/kun) **kun boshida materializatsiya qilinadi** va har qator `pending` holatda tug'iladi. «O'tkazib yuborilgan slot» — bu `scheduled_at + grace` dan o'tib ketgan, hamon `pending` qator; u so'rov bilan topiladi, jurnalda ko'rinadi va watchdog uni `missed` ga o'tkazib alert yuboradi. Xuddi shu naqsh backup uchun ham qo'llanadi (heartbeat qatori). **Kechikkan kadr olinmaydi**: 06:00 sloti 07:05 da bajarilsa, u boshqa savolga javob beradigan ma'lumot bo'ladi — shuning uchun `grace` oynasidan chiqqan slot `missed` deb yopiladi, bajarilmaydi.

Qolgan uch bo'lim shu ikki qarordan chiqadi va ularning har birida bitta o'lchangan xavf bor. **Sifat filtri** (CAM-06) `Pillow` ustida sof funksiya bo'ladi — `opencv` KERAK EMAS: `ImageStat` o'rtacha yorug'lik va standart og'ishni beradi, dekodning o'zi esa buzuq kadrni `OSError: Truncated File Read` bilan tutadi (mahalliy tekshirildi). Kafolat («yaroqsiz kadr billing'ga ta'sir qilmaydi») **kelishuv emas, hisoblanadigan ustun** bo'lishi kerak: `snapshots.is_billable` — `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED`, ustiga qisman indeks. **Ombor** (CAM-07) — SeaweedFS 4.40 (Apache-2.0, faol, `chrislusf/seaweedfs:4.40` tegi mavjud), S3 API orqali; lekin `aioboto3 15.5.0` **`aiobotocore[boto3]==2.25.1` ni qattiq pinlaydi**, u esa `boto3<1.40.62` ni majburlaydi — ya'ni CLAUDE.md dagi `boto3 1.43.57` bilan **BIR VAQTDA MUMKIN EMAS** (PyPI metadata bilan tasdiqlandi). Bu `arq` epizodining ikkinchi nusxasi va u rejaga ta'sir qiladi. **Alert** (FOUND-06) uchun `bot-service` **yaratilmaydi** — `httpx` bilan Telegram `sendMessage` chaqiruvi yetadi va `aiogram` 7-fazada o'z joyida qoladi.

**Primary recommendation:** `snapshot_schedules` (2-fazaning `daterange` + `EXCLUDE USING gist` naqshi — «bir kunga aynan bitta profil» DB invarianti) + `snapshot_schedule_slots` (`time` ro'yxati, cron satri EMAS) + kun boshida materializatsiya qilinadigan `capture_runs` (`UNIQUE (market_id, camera_id, business_date, slot_time)`) + `snapshots` (kadr metama'lumoti va `is_billable` generated ustuni). Soat — `taskiq scheduler` ning bitta 1-daqiqali ticki; bajaruv — `FOR UPDATE SKIP LOCKED` bilan lease olingan, NVR bo'yicha semafor va stagger bilan chegaralangan fan-out; kadr — `go2rtc /api/frame.jpeg` (sozlanadigan, zaxira ISAPI `/picture`); ombor — SeaweedFS S3 (`aioboto3` **yoki** `asyncio.to_thread(boto3)` — §D.9.2 dagi pin qaroriga qarab); alert — `httpx` → Telegram, guruhlangan va yo'qlikka asoslangan.

---

## User Constraints

**CONTEXT.md bu faza uchun MAVJUD EMAS** (`has_context: false`, `gsd-tools init.phase-op 4`). Ya'ni bu tadqiqot qulflangan foydalanuvchi qarorlari bilan cheklanmagan. Uning o'rniga **majburiy kirish** sifatida uchta manba qabul qilinadi va ular rejada qayta muhokama qilinmaydi.

### 1. Mahsulot qoidasi (ROADMAP.md, 2026-08-01 — MAJBURIY)

> **Admin saytda faqat kerakli ma'lumotni kiritadi — tizim qolganini o'zi, xatosiz bajaradi.**

Bu faza uchun uchta aniq oqibati bor:

| Oqibat | 4-fazada nimani anglatadi |
|---|---|
| Muhandis aralashuvi bilan ishlaydigan onboarding **qabul qilinmaydi** | Snapshot jadvali **saytdan** sozlanadi. Cron satri, YAML fayl, `.env` kaliti yoki SSH bilan tahrirlanadigan jadval — **rad etiladi**. Yangi bozor jadval uchun kod yozdirmaydi |
| Tashqi bog'liqlik hech qachon `Blocks:` bo'lmaydi | Real Karmana kadrlari yo'q. Sifat chegaralari **simulyatorda standart qiymat oladi** va pilot ma'lumotida **sozlama** bilan aniqlashtiriladi — qayta loyihalash bilan emas |
| Tekshiruv **simulyator ustida** bajariladigan qilib loyihalanadi | Butun kadr olish → sifat → arxiv → alert zanjiri `--profile sim` ostida CI'da o'lchanadi. Real NVR'ga o'tish **sozlama o'zgarishi** bo'ladi |

### 2. ROADMAP Open Decision'lari — bu fazaga tegishlilari

| # | Holat | Bu tadqiqot nima qiladi |
|---|-------|-------------------------|
| **1 — kadr olish usuli** | ✅ **HAL QILINGAN 2026-08-01.** Standart `go2rtc /api/frame.jpeg`, zaxira ISAPI `/picture`, oxirgi chora `ffmpeg`. Uchalasi **sozlanadigan** | **Qayta ochilmaydi.** Faqat *qanday* sozlanadigan qilinishi va har birining narxi ko'rsatiladi (§B.6) |
| **2 — job orkestratsiyasi** | ⛔ **OCHIQ.** `arq` o'chirildi (`redis<6` vs pin `8.0.1`). Qolgan tanlov: DB-materialized `capture_runs` + `SKIP LOCKED` **vs** `taskiq` | **Shu faza hal qiladi.** §A.2 ning javobi: ular **muqobil emas** — biri taymer, ikkinchisi davomiylik. Ikkalasi ham ishlatiladi, chegarasi aniq chizilgan |
| **3 — obyekt-ombor nomi** | SeaweedFS (MinIO arxivlangan) | Tasdiqlandi (§D.9); `aioboto3` ning **qattiq pin muammosi** topildi (§D.9.2) |

### 3. Claude ixtiyorida (bu tadqiqot tavsiya beradi)

Jadval sxemasining aniq shakli · slot ↔ `business_date` bog'lanishi · idempotentlik kaliti · retry semantikasi · fan-out konkurentligi va stagger · sifat metrikalari va standart chegaralari · `light_mode` ning saqlanish shakli · S3 kalit tartibi · retention'ni kim bajaradi · alert kanali va guruhlash siyosati.

### Bu fazada QURILMAYDI (Scope Fence — pastdagi bo'limga qarang)

Kamera-zona poligonlari va CV (5-faza) · billing (6-faza) · `bot-service` ning o'zi va sotuvchi/direktor botlari (7-faza) · Excel hisobotlar va tiklash mashqi (8-faza, FOUND-07).

---

## Phase Requirements

| ID | Tavsif (REQUIREMENTS.md dan) | Tadqiqot qaysi topilma bilan qo'llab-quvvatlaydi |
|----|------------------------------|--------------------------------------------------|
| **CAM-04** | Snapshot jadvali har bozor uchun sozlanadi va **mavsumiy profilni** qo'llaydi (standart: 06:00–08:00 har 30 daq + 16:00, 18:00) | **A.1** (profil sxemasi: `daterange` + `EXCLUDE`, slot ↔ `business_date` formulasi) · **A.3** (ko'p bozor, mintaqa) |
| **CAM-05** | Rejalashtirilgan kadr olish **idempotent** va **retry'li**; o'tkazib yuborilgan slot jurnalda ko'rinadi va **alert yuboradi** | **A.2** (taymer qarori va yiqilish rejimlari) · **B.4** (idempotentlik kaliti, yarim-muvaffaqiyat) · **B.5** (yo'qlikni aniqlash) · **B.6** (fan-out va sessiya chegarasi) |
| **CAM-06** | Har kadr **sifat filtridan** o'tadi (qorong'i/buzuq/bo'sh belgilanadi, `light_mode` saqlanadi) — yaroqsiz kadr **billing'ga ta'sir qilmaydi** | **C.7** (o'lchanadigan metrikalar va standart chegaralar) · **C.8** (`light_mode` shakli va **strukturaviy** billing kafolati) |
| **CAM-07** | Kadrlar **S3-mos** omborda (SeaweedFS) bozor/kamera/sana bo'yicha saqlanadi; **90 kun to'liq, keyin siqilgan 1 yil** (sozlanadigan) | **D.9** (SeaweedFS topologiyasi, kalit tartibi, pin to'qnashuvi) · **D.10** (retention va uning isboti) · **D.11** (hajm arifmetikasi) |
| **FOUND-06** | Tizim o'zini kuzatadi: kamera offline, **o'tkazib yuborilgan snapshot**, backup xatosi — platforma adminiga **Telegram-alert**; xatolar **Sentry**'da | **E.12** (yo'qlikka alert — heartbeat va watchdog) · **E.13** (alert charchog'i: guruhlash, chegara, bostirilmaydiganlar) |

---

## Architectural Responsibility Map

| Qobiliyat | Asosiy qatlam | Ikkinchi qatlam | Sabab |
|-----------|---------------|-----------------|-------|
| Jadval **ta'rifi** (mavsumiy profil, slotlar) | **Database (`snapshot_schedules` + `snapshot_schedule_slots`)** | API (validatsiya) | CAM-04 «har bozor uchun sozlanadi» deydi. Kodda yoki YAML'da turgan jadval self-service qoidasini buzadi. `daterange` + `EXCLUDE` «bir kunga aynan bitta profil» ni **DB invarianti** qiladi |
| Kunlik rejaning **materializatsiyasi** | **Database (`capture_runs`, `ON CONFLICT DO NOTHING`)** | Worker (tick jobi) | «O'tkazib yuborilgan slot ko'rinadi» (CAM-05) faqat slot **oldindan yozilgan** bo'lsa bajariladi. Yozilmagan slot — yo'qlik, uni so'rov topa olmaydi |
| **Taymer** (vaqt kelganini bilish) | **`taskiq scheduler` jarayoni (bitta 1-daqiqali tick)** | — | Taymer yozish — hand-roll. `taskiq` tsikli o'lchangan va u allaqachon stekda (§A.2) |
| **Davomiylik va dublikatsizlik** | **Database (`UNIQUE` + `FOR UPDATE SKIP LOCKED` + lease)** | — | `taskiq scheduler` ning cron holati **jarayon xotirasida** (o'lchandi, §A.2) — qayta ishga tushishdan omon qolmaydi |
| Kadr olish (media) | **go2rtc `/api/frame.jpeg`** | ISAPI `/picture` → `ffmpeg` | ROADMAP Open Decision #1 (hal qilingan). Uchala yo'l bitta interfeys ortida |
| NVR sessiya byudjetini hurmat qilish | **Worker (per-NVR semafor + stagger)** | `nvr_devices.max_concurrent_captures` sozlamasi | Chegara **noma'lum** (03-RESEARCH A.5: LOW). Yechim uni bilishni talab qilmasligi kerak |
| Sifat filtri (qorong'i/buzuq/bo'sh) | **core-api worker (sof funksiya, `Pillow`)** | Database (`quality_*` ustunlari) | cv-service 5-fazada tug'iladi; unga bog'lanish bu fazani bloklardi. Filtr — **bayt → qaror** sof funksiyasi, ko'chirish narxi nol |
| «Yaroqsiz kadr billing'ga ta'sir qilmaydi» | **Database (`snapshots.is_billable` GENERATED + partial index)** | 5/6-faza so'rovlari | Kelishuv («bu ustunni tekshirishni unutmang») 6-fazada birinchi so'rovdayoq buziladi (§C.8) |
| Obyekt saqlash | **SeaweedFS (S3 API)** | Database (kalit + `etag` + `size_bytes`) | CAM-07. Bayt omborda, **metama'lumot bazada** — ombor almashsa faqat `endpoint` o'zgaradi |
| Saqlash siyosati (90 kun → siqilgan 1 yil) | **Worker (kunlik `retention` jobi)** | SeaweedFS TTL (**ishlatilmaydi** — §D.10) | «Siqish» — o'qib-qayta yozish, ya'ni uni ombor emas, ilova bajaradi |
| Alert yetkazish | **core-api/worker → Telegram Bot API (`httpx`)** | Sentry (xato izlari) | `bot-service` 7-fazada tug'iladi. `sendMessage` chaqiruvi yetadi — `aiogram` ni tortish 7-fazani oldinga surardi |
| Yo'qlikni aniqlash (alert-on-absence) | **Database (kechikkan `pending` qatorlar so'rovi)** + **watchdog jobi** | Telegram | «Xato bo'lmadi» ≠ «ish bajarildi». Yagona ishonchli signal — **kutilgan qator kutilgan holatda emas** (§E.12) |
| Audit | **Database (`fn_audit_row()` triggeri)** — `snapshot_schedules`, `snapshot_schedule_slots` | — | Jadvalni o'zgartirish kunlik dalil hajmini o'zgartiradi; 6-fazada nizoda «kim slotni o'chirdi» so'raladi |

---

## Project Constraints (CLAUDE.md dan)

Quyidagilar **majburiy** va rejada qayta muhokama qilinmaydi.

| Direktiva | Bu fazada nimani anglatadi |
|-----------|----------------------------|
| **Servislar soni aynan 3** (`core-api`, `cv-service`, `bot-service`) | Snapshot pipeline — `core-api` kod bazasining **worker** entrypointida. Yangi `scheduler` konteyneri — **oltinchi konteyner, uchinchi servis emas** (`migrate`/`tests`/`worker` bilan bir xil naqsh) |
| **Snapshot: go2rtc `/api/frame.jpeg` → ISAPI `/picture` → ffmpeg** | Aynan shu tartib. Uchalasi bitta protokol ortida, tanlov `nvr_devices` ustunida |
| **`arq` TAQIQ** (`redis<6` vs pin `redis==8.0.1`) | 3-fazada empirik tasdiqlangan. `taskiq 0.12.4` + `taskiq-redis 1.2.3` qoladi |
| **`boto3`/`aioboto3` S3 API — `minio-py` EMAS** | Ombor almashishi **sozlama** bo'lib qolishi uchun. ⚠ `aioboto3` ning **qattiq pini** topildi — §D.9.2 |
| **`Pillow 12.3.0`** siqish uchun | Retention'ning «siqilgan 1 yil» qismi **va** sifat metrikalari |
| **`float` pul uchun TAQIQ / naive datetime TAQIQ** | Bu fazada pul yo'q, lekin **vaqt bor va u markaziy**: `timestamptz` + `ZoneInfo("Asia/Tashkent")`, `business_date` generated column |
| **Testlarda SQLite TAQIQ** | RLS faqat haqiqiy `postgres:18.4` + testcontainers |
| **`uv` per-service `pyproject.toml`** | Yangi paketlar faqat `services/core-api/pyproject.toml` ga |
| **AGPL TAQIQ** (tijoriy SaaS) | SeaweedFS Apache-2.0 ✅; **Garage AGPL-3.0 — muqobil sifatida ham yozilmaydi** [VERIFIED: GitHub API `license.spdx_id = AGPL-3.0`, 2026-08-04] |
| **3 til majburiy** | Jadval UI'si, sifat sabablari va alert matnlari — **i18n kalitlari**, qotib qolgan matn emas |
| **`tenacity 9.1.4`** so'rov ichidagi retry uchun | Bitta kadr olishning qayta urinishi. Job-darajasidagi retry'dan **boshqa qatlam** (§B.4) |
| **NVR faqat WireGuard orqali; RTSP parollari Fernet** | 3-fazadan meros. Kadr olish yo'li **o'sha** tunneldan o'tadi va **o'sha** `authenticated_rtsp_source()` ni ishlatadi |
| **GSD Workflow Enforcement** | Fayl o'zgartirish faqat GSD komandasi ichida |

---

## A. Jadval va mavsumiy profil (CAM-04)

### A.1 — Sxema: mavsumiy profil qanday ifodalanadi va slot `business_date` ga qanday bog'lanadi

#### Nima uchun cron satri EMAS

Birinchi refleks — `snapshot_schedules(market_id, cron text)`. U **rad etiladi** va sabab uchta:

| Muammo | Oqibat |
|---|---|
| Cron satri **uch joyda** parsing talab qiladi (UI validatsiyasi, API validatsiyasi, bajaruvchi) | Uchtasi bir xil parserni ishlatmasa jimgina ajraladi. `pycron` (taskiq bog'liqligi) va JS cron kutubxonalari **bir xil emas** — masalan `L`, `#`, `?` sintaksisi |
| Cron **kerak bo'lmagan quvvat** beradi (`0 6 */3 * 2`) | Mahsulot «har uchinchi seshanba» ni hech qachon so'ramaydi, lekin admin uni **yoza oladi** va natijada kutilmagan kunlik dalil hajmi paydo bo'ladi |
| Cron satri **i18n va tushuntirishga qarshi** | «Bugungi slotlar» ekranini cron'dan qayta qurish kerak bo'lardi. Uchala tilda «`0,30 6-8 * * *` nimani anglatadi» ni tushuntirish — mahsulot muammosi |

O'rniga: **slot vaqtlarining tekis ro'yxati** (`time` tipi). U `<input type="time">` ga to'g'ridan-to'g'ri mos keladi, DB tipi bilan validatsiya qilinadi va uchala tilda tarjimasiz ko'rsatiladi.

⚠ «06:00–08:00 har 30 daqiqada» **oraliq sifatida saqlanmaydi**. Standart jadvalda ikkita shakl bor (oraliq + yakka vaqtlar: 16:00, 18:00) va ikkalasini sxemada saqlash **ikkita kod yo'lini** tug'diradi. Oraliqni **UI kengaytiradi** (generator tugmasi: boshlanish · tugash · qadam → 5 qator), baza esa **faqat tekis ro'yxatni** ko'radi. Bu 2-fazadagi «usta holati — domen ma'lumotining o'zi» qarorining aynan takrori.

#### Sxema

```sql
-- Mavsumiy profil. 2-fazaning tarif/biriktirish naqshi bilan BIR XIL shakl.
CREATE TABLE snapshot_schedules (
    id          uuid PRIMARY KEY DEFAULT uuidv7(),
    market_id   uuid NOT NULL,
    name        text NOT NULL,                  -- "Yozgi", "Qishki" — admin yozadi
    period      daterange NOT NULL,             -- [) — sbozor_core.periods.PERIOD_BOUNDS
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_snapshot_schedules_period_not_empty CHECK (NOT isempty(period)),
    CONSTRAINT ex_snapshot_schedules_no_overlap
        EXCLUDE USING gist (market_id WITH =, period WITH &&)
);

CREATE TABLE snapshot_schedule_slots (
    id           uuid PRIMARY KEY DEFAULT uuidv7(),
    market_id    uuid NOT NULL,
    schedule_id  uuid NOT NULL,
    slot_time    time NOT NULL,                 -- MAHALLIY devor-soati
    CONSTRAINT uq_snapshot_schedule_slots
        UNIQUE (market_id, schedule_id, slot_time),
    CONSTRAINT fk_snapshot_schedule_slots_schedule
        FOREIGN KEY (market_id, schedule_id)
        REFERENCES snapshot_schedules (market_id, id) ON DELETE CASCADE
);
```

| Element | Nima uchun aynan shunday |
|---|---|
| `EXCLUDE USING gist (market_id WITH =, period WITH &&)` | **«Bir kunga aynan bitta profil»** — DB invarianti, ilova qoidasi emas. `btree_gist` kengaytmasi **allaqachon o'rnatilgan** (02-01) va `stall_assignments` aynan shu naqshni ishlatadi |
| `daterange` `[)` | `sbozor_core.periods.PERIOD_BOUNDS` — loyihada **yagona** chegara konventsiyasi. Xom `Range(...)` yozilmaydi |
| `time`, `timetz` EMAS | Slot — **mahalliy devor-soati**. `timetz` PostgreSQL'ning o'zi «kamdan-kam foydali» deb belgilagan tipi va u DST/mintaqa bilan noto'g'ri munosabatda bo'ladi |
| Composite FK `(market_id, schedule_id)` | 1-faza S-1 naqshi: tenant chegarasi FK'da ham qulflanadi |
| `ON DELETE CASCADE` faqat slotlarda | Profil o'chirilsa slotlari ketadi. **`capture_runs` ga kaskad YO'Q** — o'tmishdagi dalil jadval o'zgarishidan omon qolishi shart |

#### Mavsumiylik amalda qanday ishlaydi

`EXCLUDE` kesishishni taqiqlagani uchun «yozgi profil qo'shish» — 2-fazadagi tarif qo'shish bilan **bir xil amal**: mavjud, ochiq oxirli profil **bo'linadi**.

```
Bozor faollashtirildi 2026-08-15:
  [2026-08-15, ∞)   "Standart"   -> 06:00 06:30 07:00 07:30 08:00 16:00 18:00

Admin qishki profil qo'shadi [2026-11-01, 2027-03-01):
  [2026-08-15, 2026-11-01)  "Standart"
  [2026-11-01, 2027-03-01)  "Qishki"    -> 07:00 07:30 08:00 15:00 17:00
  [2027-03-01, ∞)           "Standart"  (nusxa)
```

⚠ **Bo'shliq ATAYIN mumkin.** Ikki profil orasida qoplanmagan kun bo'lsa — o'sha kunga **umuman slot yo'q**, ya'ni kadr olinmaydi. Bu xato emas (mavsumiy yopiladigan bozor), lekin u **UI'da ko'rinishi SHART**: jadval sahifasida «keyingi 90 kunda 12 kun qoplanmagan» ogohlantirishi. Ko'rinmasa bu jim ma'lumot yo'qotish bo'ladi — 2-fazada `market_is_open()` ning fail-closed xulqi bilan bir xil sinf.

**Standart profil ustada yoziladi** (MARKET-01 ning «snapshot jadvali» qadami, ROADMAP Phase 2 Note): bozor faollashtirilganda `market_create()` bilan bir xil ruhda, 7 ta standart slot bilan bitta ochiq oxirli profil. Admin **hech nima kiritmasdan** ishlaydigan jadvalga ega bo'ladi — self-service qoidasi.

#### Slot → `business_date` bog'lanishi

```sql
-- Materializatsiya so'rovi ichida:
scheduled_at := ((:business_date::date + s.slot_time) AT TIME ZONE m.timezone)
```

`timestamp AT TIME ZONE 'Asia/Tashkent'` — **naive** vaqtni Toshkent devor-soati sifatida talqin qilib `timestamptz` beradi. Yo'nalish to'g'ri (teskarisi `timestamptz AT TIME ZONE ...` bo'lardi va u naive qiymat qaytarardi).

⚠ **Toshkent UTC+5, yozgi vaqt YO'Q** — ya'ni «mavjud bo'lmagan soat» va «ikki marta uchraydigan soat» sinfidagi butun xatolar **bu yerda yo'q**. Buni ochiq yozish kerak, chunki DST bilan ishlagan har bir dasturchi bu yerda ortiqcha himoya qo'shishga urinadi.

`capture_runs.business_date` — **hisoblanadigan ustun**, lekin 1-fazadagi shakldan **farq qiladi**:

```sql
business_date date GENERATED ALWAYS AS
    ((scheduled_at AT TIME ZONE 'Asia/Tashkent')::date) STORED
```

| Farq | Sabab |
|---|---|
| `created_at` EMAS, **`scheduled_at`** | Reja qatori tegishli kunidan **oldin** yaratilishi mumkin (kun boshida, yoki kelajakda oldindan). `created_at` ga tayanish 00:00–00:05 oynasida qatorni **oldingi kunga** yozardi |
| Mintaqa **literal**, `m.timezone` EMAS | `GENERATED` ifodasi `IMMUTABLE` bo'lishi shart va boshqa jadvalga havola qila olmaydi. Bu cheklov 1-fazada allaqachon hujjatlashtirilgan (`models/identity.py:85-90`) |

⚠ **Bu assimetriya xavfli va u qo'riqlanishi kerak.** `scheduled_at` `markets.timezone` dan hisoblanadi, `business_date` esa literaldan. Bugun ikkalasi bir xil (`markets.timezone` standarti `'Asia/Tashkent'`), lekin boshqa mintaqadagi bozor qo'shilsa `scheduled_at` to'g'ri, `business_date` esa **noto'g'ri** bo'lardi — va bu 6-fazada pul chegarasini siljitardi. **Darvoza:** meta-test `SELECT count(*) FROM markets WHERE timezone <> 'Asia/Tashkent'` → 0 talab qiladi. Ikkinchi mintaqa qo'shilgan kuni test **qizaradi**, biznes-kun esa jimgina siljimaydi.

#### Yopiq kun (MARKET-05) bilan munosabat

Bayram/ishlamaydigan kunda kadr olinadimi? **Ha, standart bo'yicha** — va bu ataylab:

- Yopiq deb e'lon qilingan kunda band rasta ko'rinsa, bu **aynan mahsulot izlaydigan anomaliya** («ro'yxatga olinmagan savdo», BILL-04 ning qo'shnisi)
- Narxi kichik: yiliga ~15 bayram kuni × 175 kadr ≈ 2 600 kadr
- Sozlanadigan: `market_profile.capture_on_closed_days boolean NOT NULL DEFAULT true`

Materializatsiya `market_is_open(:market_id, :business_date)` funksiyasini (2-fazadan mavjud) **qayta ishlatadi** — kalendar mantig'i takrorlanmaydi. Yopiq kunning `capture_runs` qatorlari `is_market_open = false` bayrog'i bilan tug'iladi va 6-faza ularni billing'dan chiqaradi, hisobotdan esa **chiqarmaydi**.

**Ishonch:** HIGH — sxema butunlay mavjud, o'lchangan 2-faza naqshlaridan quriladi (`daterange`, `EXCLUDE`, `btree_gist`, composite FK, generated column). Yangi mexanizm yo'q.

---

### A.2 — Orkestratsiya: ROADMAP Open Decision #2 ning javobi

> Bu bo'lim fazaning **markaziy qarori**. Quyidagi faktlar `taskiq 0.12.4` ning **o'rnatilgan manbasini o'qish** bilan olingan, hujjatdan emas.

#### O'lchangan faktlar — `taskiq` planeri haqiqatda nima qiladi

| # | Fakt | Manba |
|---|------|-------|
| 1 | Planer — **alohida jarayon**: `taskiq scheduler <modul>:scheduler`. `run_scheduler()` o'z CLI entrypointi | [VERIFIED: `taskiq/cli/scheduler/run.py::run_scheduler`, o'rnatilgan 0.12.4 manbasi o'qildi 2026-08-04] |
| 2 | Cron ning «oxirgi ishga tushish» holati — **jarayon xotirasidagi `dict`**: `SchedulerLoop.cron_tasks_last_run: dict[ScheduleId, datetime]`. **Hech qayerga yozilmaydi** | [VERIFIED: `SchedulerLoop.__init__`] |
| 3 | **Taqsimlangan qulf YO'Q.** Ikkita planer jarayoni har slotni mustaqil ravishda ishga tushiradi | [VERIFIED: `SchedulerLoop.run()` da qulf yo'q] |
| 4 | Cron **UTC'da** baholanadi (`now = datetime.now(tz=timezone.utc)`); har jadval uchun `cron_offset` mintaqa nomi (`"Asia/Tashkent"`) yoki `timedelta` bo'lishi mumkin | [VERIFIED: `is_cron_task_now()` — `now.astimezone(ZoneInfo(offset))`] |
| 5 | Bir xil `schedule_id` uchun **1 daqiqalik debounce**: `if round(seconds_spend) < 60: return False` | [VERIFIED: `is_cron_task_now()`] |
| 6 | `--skip-first-run` **bo'lmasa**, startupda joriy daqiqaga to'g'ri keladigan cron **darhol ishga tushadi** | [VERIFIED: `_mark_cron_tasks_as_already_run()` faqat `skip_first_run=True` da chaqiriladi] |
| 7 | Jadvallar manbasi har `update_interval` (standart **60 s**) da qayta o'qiladi | [VERIFIED: `run()` tsikli] |
| 8 | `LabelScheduleSource` jadvalni **kod dekoratoridan** oladi (`schedule=[{"cron": ...}]`) — ya'ni **bozorga qarab o'zgara olmaydi** | [VERIFIED: `taskiq/schedule_sources/label_based.py`] |
| 9 | `RedisScheduleSource` jadvalni **Redis'da** saqlaydi (`add_schedule`/`delete_schedule`/`get_schedules`) | [VERIFIED: `taskiq_redis` eksportlari va `__init__` imzosi] |

#### Nima uchun «har slot uchun bitta cron» RAD ETILADI

Fakt 2 + Fakt 3 birgalikda CAM-05 ni **bevosita** buzadi:

```
06:00 sloti. Planer konteyneri 05:58 da qayta ishga tushdi (deploy, OOM, xost restart).
  -> `cron_tasks_last_run` bo'sh, lekin 06:00 daqiqasi hali kelmagan  -> OK
06:00 sloti. Planer 05:59:30 – 06:00:40 oralig'ida o'lik edi.
  -> 06:00 daqiqasi HECH KIM tomonidan ko'rilmadi
  -> job navbatga TUSHMADI
  -> jurnalda HECH NIMA yo'q
  -> alert YO'Q
```

CAM-05 ning matni: «o'tkazib yuborilgan slot jurnalda **ochiq ko'rinadi** va **alert yuboradi**». Xotiradagi cron bu talabni **printsipial** bajara olmaydi: yo'q bo'lgan narsa haqida hech kim bilmaydi.

Va teskari tomoni (Fakt 6): planer 06:00:15 da qayta ko'tarilsa va `--skip-first-run` berilmagan bo'lsa, u 06:00 ni **ikkinchi marta** yuboradi.

#### Nima uchun `RedisScheduleSource` RAD ETILADI

```yaml
# compose.yaml (mavjud)
cache:
  image: valkey/valkey:9.1.1-alpine
  command: ["valkey-server", "--save", "", "--appendonly", "no"]
```

Valkey bu o'rnatmada **davomiyliksiz** — RDB ham, AOF ham o'chirilgan (ataylab: u kesh). `RedisScheduleSource` esa jadvalni aynan o'sha Valkey'da saqlaydi. Ya'ni:

> **Kesh konteyneri qayta ishga tushsa BARCHA bozorlarning snapshot jadvali jimgina yo'q bo'ladi va hech qanday xato chiqmaydi.**

Ikkinchi sabab (davomiylikdan qat'i nazar): jadval **ikkinchi haqiqat manbai** bo'lardi — DB'dagi `snapshot_schedules` va Redis'dagi nusxa drift qiladi. Bu 3-fazada `PATCH /api/config` bilan go2rtc YAML'iga yozish rad etilgan sababning aynan o'zi.

#### TAVSIYA: soat `taskiq` da, reja Postgres'da

```
┌──────────────────────────────────────────────────────────────┐
│  scheduler konteyneri (taskiq scheduler)                     │
│  LabelScheduleSource: BITTA jadval — cron "* * * * *"        │
│  Yagona vazifasi: `capture.tick` ni navbatga qo'yish          │
└────────────────────────────┬─────────────────────────────────┘
                             │ (holatsiz, idempotent)
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  worker konteyneri — `capture_tick` jobi                     │
│  1. ensure_plan(business_date=bugun)   ON CONFLICT DO NOTHING│
│  2. mark_overdue_as_missed()           grace oynasidan tashqari│
│  3. claim_due()  SELECT ... FOR UPDATE SKIP LOCKED LIMIT n   │
│  4. NVR bo'yicha guruhlab `capture_batch` larni navbatga qo'yish│
└────────────────────────────┬─────────────────────────────────┘
                             ▼
              `capture_batch(nvr_id, slot)` — semafor + stagger (§B.6)
```

**Nima uchun bu ikkala variantning ham eng yaxshi tomonini oladi:**

| `taskiq` ning yiqilish rejimi | Tick idempotent bo'lgani uchun nima bo'ladi |
|---|---|
| Planer o'lik edi, tick o'tkazib yuborildi | **Zararsiz** — keyingi tick (≤60 s) hali `pending` bo'lgan barcha muddati kelgan qatorlarni oladi |
| Planer qayta ko'tarilib tickni takrorladi | **Zararsiz** — `claim_due()` `SKIP LOCKED` bilan ishlaydi, `ensure_plan` esa `ON CONFLICT DO NOTHING` |
| Ikkita planer jarayoni ishlayapti | **Zararsiz** — yuqoridagi bilan bir xil. «Aynan bitta planer» operatsion talabi **yo'qoladi** |
| Soat sakradi (NTP step, xost migratsiyasi) | **Zararsiz** — predikat `scheduled_at <= now()`, cron daqiqasiga moslashish emas |

⚠ **Kompensatsiya oynasi CHEGARALANGAN va bu MAJBURIY.** Tick «hali bajarilmagan har qanday slot»ni cheksiz kutmaydi: `scheduled_at + capture_grace_seconds < now()` bo'lsa qator **bajarilmaydi**, `missed` deb yopiladi. Standart `grace = 600 s`. Sabab **mahsulotda**: 06:00 sloti 07:05 da olingan kadr «06:00 da rasta band edimi?» savoliga **javob bermaydi** — u boshqa savolga javob beradi va uni 6-faza dalil sifatida ishlatsa noto'g'ri hisob chiqadi. Kechikkan kadr — **yo'q kadrdan yomonroq**.

#### Rad etilgan muqobillar

| Variant | Verdikt |
|---|---|
| Worker `WORKER_STARTUP` ilgagida `while True: asyncio.sleep(60)` tsikli | ❌ Taymerni hand-roll qilish. Tsikl o'lsa konteyner **`Up` va `healthy`** bo'lib qolaveradi — `worker.py` ning `socket_timeout` izohida hujjatlashtirilgan «jimgina yolg'on» sinfining aynan o'zi. Prefetcher bilan bitta event loop'da raqobatlashadi |
| `pg_cron` kengaytmasi | ❌ `shared_preload_libraries` + superuser talab qiladi; `postgres:18.4-trixie` da yo'q; Python kodimizni chaqira olmaydi; O'zbekiston hostingiga ko'chishda boshqariladigan DB'da mavjud bo'lmasligi mumkin |
| Xost `cron` / `systemd timer` → HTTP endpoint | ❌ Compose'dan tashqarida holat; «ko'chirish arzon» xususiyatini buzadi; yangi autentifikatsiyalangan ichki endpoint = yangi hujum yuzasi |
| `RedisStreamBroker` (`taskiq_redis`) ni ack bilan ishlatish | ⚠ Kelajakda. `worker.py` da hujjatlashtirilgan sabab bu yerda **teskari** ishlaydi: kadr olishda `ack` bilan qayta yetkazish **foydali** (yiqilgan worker'ning ishi qaytadi). Lekin lease allaqachon shu ishni bajaradi va ikki mexanizmni birga saqlash D-06 ni buzadi |
| Faqat DB (planersiz), tickni `core-api` ning `lifespan` idan | ❌ `uvicorn --workers 1` — uzun tsikl API bilan bitta jarayonda; T-03-42 ning takrori |

#### `capture_runs` sxemasi (orkestratsiyaning yuragi)

```sql
CREATE TYPE capture_run_status AS ENUM
    ('pending', 'running', 'succeeded', 'failed', 'missed', 'skipped');

CREATE TABLE capture_runs (
    id            uuid PRIMARY KEY DEFAULT uuidv7(),
    market_id     uuid NOT NULL,
    camera_id     uuid NOT NULL,
    nvr_id        uuid NOT NULL,          -- fan-out guruhlash uchun denormalizatsiya
    slot_time     time NOT NULL,
    scheduled_at  timestamptz NOT NULL,
    business_date date GENERATED ALWAYS AS
                  ((scheduled_at AT TIME ZONE 'Asia/Tashkent')::date) STORED,
    status        capture_run_status NOT NULL DEFAULT 'pending',
    attempts      smallint NOT NULL DEFAULT 0,
    locked_until  timestamptz,            -- lease
    locked_by     text,                   -- worker identifikatori (diagnostika)
    started_at    timestamptz,
    finished_at   timestamptz,
    error_code    text,                   -- i18n KALITI, matn emas
    error_detail  jsonb,                  -- mask_sensitive dan o'tadi
    capture_method text,                  -- 'go2rtc' | 'isapi' | 'ffmpeg'
    is_market_open boolean NOT NULL,
    snapshot_id   uuid,                   -- muvaffaqiyatda
    created_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_capture_runs_slot
        UNIQUE (market_id, camera_id, business_date, slot_time)
);

-- Muddati kelgan ishni tanlash (tick ning issiq yo'li)
CREATE INDEX ix_capture_runs_due
    ON capture_runs (market_id, scheduled_at)
    WHERE status = 'pending';

-- Yo'qlik detektori (watchdog ning issiq yo'li)
CREATE INDEX ix_capture_runs_overdue
    ON capture_runs (scheduled_at)
    WHERE status IN ('pending', 'running');
```

`claim_due()` — yagona qulflash so'rovi:

```sql
WITH due AS (
    SELECT id
      FROM capture_runs
     WHERE status = 'pending'
       AND scheduled_at <= now()
       AND scheduled_at > now() - make_interval(secs => :grace_seconds)
     ORDER BY scheduled_at
     LIMIT :batch
     FOR UPDATE SKIP LOCKED
)
UPDATE capture_runs c
   SET status = 'running',
       attempts = c.attempts + 1,
       locked_until = now() + make_interval(secs => :lease_seconds),
       locked_by = :worker_id,
       started_at = COALESCE(c.started_at, now())
  FROM due
 WHERE c.id = due.id
RETURNING c.*;
```

⚠ **`FOR UPDATE SKIP LOCKED` faqat tranzaksiya davomida himoya qiladi.** Worker qatorni `running` ga o'tkazib **commit qilgach**, qulf tushadi. Ikkinchi himoya — **lease**: `locked_until` o'tib ketgan `running` qatorlar `pending` ga qaytariladi (tickning 0-qadami). Ikkalasi ham kerak va ular **turli** muddatni qoplaydi: `SKIP LOCKED` — «bir vaqtda ikki worker tanlab olmasin», lease — «worker o'rtada o'lsa ish qaytsin».

**Ishonch:** HIGH — `taskiq` faktlari manbadan o'qildi; `SKIP LOCKED` va lease naqshi Postgres'ning standart, hujjatlashtirilgan xulqi.

---

### A.3 — Ko'p bozor: bitta worker puli, mintaqa va tenant konteksti

#### Tick tenant chegarasini qanday kesib o'tadi

Bu **yangi muammo** va u 3-fazada bo'lmagan: kashfiyot jobi **bitta** `market_id` bilan chaqirilgan, tick esa **hamma** bozorlar ustida ishlashi kerak. Lekin RLS `FORCE` qilingan va `markets` policy'si `id = app.market_id`, ya'ni `sbozor_app` roli kontekstsiz **hech qanday** bozorni ko'rmaydi.

Loyihada bu muammoning **allaqachon yechilgan** shakli bor: `auth_list_markets_full()` — `SECURITY DEFINER` funksiya, `market_repo.py` da platforma admini uchun ishlatiladi. Xuddi shu naqsh:

```
1. Tick `SECURITY DEFINER` funksiya bilan FAQAT identifikatorlarni oladi:
       SELECT market_id FROM capture_due_markets()
   -> funksiya faol bozorlarni va ularning muddati kelgan slotlari borligini qaytaradi.
      TENANT MA'LUMOTINI QAYTARMAYDI (nom ham, kadr ham, sotuvchi ham).

2. Har bozor uchun ALOHIDA tranzaksiya ochiladi va unda
       set_tenant_context(market_id=..., actor_kind=ActorKind.SYSTEM)
   chaqiriladi -> keyingi barcha so'rovlar oddiy RLS ostida.
```

| Qaror | Sabab |
|---|---|
| `SECURITY DEFINER` yuzasi **iloji boricha tor** | Faqat `market_id` (va ixtiyoriy `due_count`). Kengroq yuza — kengroq chetlab o'tish. `market_repo` ning izohi aynan shuni talab qiladi |
| Bozor bo'yicha **alohida tranzaksiya** | GUC'lar `SET LOCAL`, ya'ni `COMMIT` da tozalanadi. Bitta tranzaksiyada ikki bozorni aralashtirish — tenant sizib chiqishining eng qisqa yo'li |
| `ActorKind.SYSTEM` | 3-fazadagi `jobs/discovery.py::_system_transaction()` naqshi **aynan qayta ishlatiladi** — yangi naqsh o'ylab topilmaydi |

⚠ **Pitfall 13 ning takrori xavfi.** 3-fazada bu xato bir marta hujjatlashtirilgan: kontekstsiz job **jimgina 0 qator** ko'radi va hech qanday xato bermaydi. Tick uchun bu «bugun hech qaysi bozorda ish yo'q» degan **yolg'on tinchlik** bo'lardi. Darvoza: `test_capture_tick_sets_tenant_context` — kontekstsiz chaqiruvda materializatsiya **0 qator** yozishini ANIQ ko'rsatadi.

#### Mintaqa: v1 uchun bu muammo YO'Q va buni ochiq aytish kerak

O'zbekiston — **bitta mintaqa** (UTC+5), yozgi vaqt yo'q. `markets.timezone` ustuni 1-fazada yaratilgan va standarti `'Asia/Tashkent'`. Ya'ni:

- «Har bozorning o'z mintaqasi» — **v1 da amaliy muammo emas**
- Ammo `business_date` generated ustuni **literal**ga qadalgan (A.1) va bu farq ikkinchi mintaqa qo'shilgan kuni **jimgina** noto'g'ri javob berardi
- Shuning uchun tikilgan darvoza: `tests/tenancy/test_meta.py` ga bitta invariant — **barcha `markets.timezone = 'Asia/Tashkent'`**

Bu «ortiqcha ehtiyot» emas: 6-faza pul chegarasini `business_date` bo'yicha oladi, ya'ni bir kunlik siljish **sotuvchi bilan nizo** demakdir.

#### Miqyos arifmetikasi

```
1 bozor   = 25 kamera × 7 slot          = 175 kadr/kun
10 bozor  = 1 750 kadr/kun              ≈ 0,02 kadr/soniya o'rtacha
```

Lekin **o'rtacha yolg'on gapiradi**: 7 slotning har biri **ayni bir daqiqada** 25 (yoki 250) kadr talab qiladi. Ya'ni tizim o'rtacha yuk uchun emas, **cho'qqi** uchun loyihalanadi — va cho'qqini yumshatish §B.6 ning mavzusi (stagger + semafor). Bitta worker puli o'nlab bozorni ko'taradi; chegara CPU emas, **NVR va tunnel** tomonda.

**Ishonch:** HIGH (naqsh mavjud va o'lchangan) · mintaqa masalasi HIGH (faktik: O'zbekiston bitta mintaqa).

---

## B. Idempotent kadr olish va retry (CAM-05)

### B.4 — Idempotentlik kaliti va «yarim muvaffaqiyat» muammosi

#### Kalit

**`UNIQUE (market_id, camera_id, business_date, slot_time)`** — `capture_runs` da.

Nima uchun `scheduled_at` emas: `scheduled_at` — **hosila** (`business_date + slot_time` mintaqa bilan). Uni kalit qilish tenglikni `timestamptz` ustida bajarardi, ya'ni jadval tahriri yoki mintaqa sozlamasi tegishi bilan «bir xil slot» tushunchasi siljib ketardi. `(business_date, slot_time)` esa slotning **biznes identifikatori**: «2026-09-01 kunidagi 06:30 sloti, 7-kamera». U inson tushunchasiga ham, hisobot filtriga ham, dalil havolasiga ham mos.

⚠ **Kalitda `nvr_id` YO'Q.** Kamera boshqa NVR'ga ko'chirilishi (fizik almashtirish) tarixdagi slotlar identifikatorini o'zgartirmasligi kerak. `nvr_id` — fan-out uchun **denormalizatsiya**, identifikatsiya emas.

#### «Yarim muvaffaqiyat»: kadr olindi, yuklash yiqildi

Bu **eng nozik** holat va uni tartib bilan hal qilish kerak, kompensatsiya bilan emas.

```
1. Kadr olish            -> baytlar XOTIRADA
2. Sifat tahlili         -> sof funksiya, xotirada (§C.7)
3. S3 ga PUT             -> DETERMINISTIK kalit
4. `snapshots` qatori + `capture_runs.status='succeeded'`  -> BITTA tranzaksiya
```

**Deterministik kalit — butun yechimning yuragi:**

```
{market_id}/{business_date}/{camera_id}/{slot_time}.jpg
1f0c…/2026-09-01/9a2b…/0630.jpg
```

Kalit **tasodifiy UUID emas**, u `capture_runs` ning o'z identitetidan hosil bo'ladi. Natijada **qayta yuklash o'sha obyektni ustiga yozadi** — S3 `PUT` bir xil kalit uchun idempotent. Ya'ni:

| Qayerda uzildi | Holat | Qayta urinish nima qiladi |
|---|---|---|
| 1 va 3 orasida | Omborda hech nima yo'q, bazada `running` | Lease tugaydi → qator `pending` → toza qayta bajarish |
| 3 va 4 orasida | **Obyekt bor, baza qatori yo'q** | Qayta bajarish o'sha kalitga qayta yozadi va qatorni yozadi → **izsiz tuzaladi** |
| 4 dan keyin | Ikkalasi ham bor, `succeeded` | `claim_due()` faqat `pending` ni oladi → **hech qachon qayta bajarilmaydi** |

⚠ **QOIDA: baza qatori omborda obyekt BORLIGINI TASDIQLAYDI.** Teskari tartib (avval qator, keyin yuklash) 6-fazaga **mavjud bo'lmagan dalilga havola** berardi — BILL-02 («har hisob dalil-kadrlarga bog'langan») aynan buni ko'tara olmaydi. Bu tartib muzokara qilinmaydi.

⚠ **Yetim obyekt** (3 bajarildi, keyin qator `missed`/`failed` bo'lib qoldi) — mumkin va u **muammo emas**: kaliti deterministik bo'lgani uchun uni topish arzon (kun uchun kutilgan kalitlar to'plami `capture_runs` dan hisoblanadi). Retention jobi (§D.10) kunlik supurgi sifatida uni tozalaydi. **Ustuvorligi past** — bitta 60 KB obyekt hech kimga zarar bermaydi.

#### Retry — ikki qatlam va ular ARALASHTIRILMAYDI

| Qatlam | Vosita | Nimani qoplaydi | Chegara |
|---|---|---|---|
| **Urinish ICHIDA** | `tenacity` (3-fazadagi `AsyncRetrying` naqshi) | Bir martalik tarmoq uzilishi: timeout, connection reset, 5xx | `MAX_RETRY_ATTEMPTS = 3`, eksponensial kutish |
| **Urinishlar ORASIDA** | Tick + lease | Worker o'ldi, konteyner qayta ko'tarildi, NVR vaqtincha yo'q edi | `max_attempts` (standart **3**) **VA** `grace` oynasi — qaysi biri oldin tugasa |

⚠ **3-fazaning TESKARI RETRY SIYOSATI bu yerda ham amal qiladi va u meros olinadi, qayta ixtiro qilinmaydi.** `app/services/isapi/client.py` da hujjatlashtirilgan qoida:

> `401` / autentifikatsiya xatosi → **retry YO'Q** (Hikvision ~5 urinishdan keyin hisobni 30 daqiqaga qulflaydi va undan keyin **to'g'ri parol ham ishlamaydi**);
> tarmoq xatosi → retry, ≤3 urinish.

`AUTH_LOCKING_CODES` (`nvr_bad_credentials`, `nvr_account_locked`, `nvr_user_no_permission`) — bu kodlarda **tickning ham qayta urinishi taqiqlanadi**: qator darhol `failed` deb yopiladi va `attempts` `max_attempts` ga o'rnatiladi. Aks holda tick har daqiqada NVR'ga borib **butun bozorning hisobini qulflab qo'yardi** — 25 kamera × 10 tick = 250 muvaffaqiyatsiz autentifikatsiya urinishi.

⚠ Ikkinchi qulflash yo'li: **`nvr_stream_limit`**. Bu kodda ham darhol qayta urinish **foydasiz va zararli** (chegara hali bo'shamagan). Yechim — retry emas, **kechiktirish**: qator `pending` bo'lib qoladi, lekin `scheduled_at` o'zgarmaydi va `retry_after` maydoni (`locked_until` ni qayta ishlatib) keyingi tickni ~30 s kechiktiradi. Bu §B.6 dagi adaptiv pasaytirish bilan bir xil signal.

#### `snapshots` sxemasi

```sql
CREATE TYPE snapshot_quality AS ENUM ('ok', 'dark', 'blank', 'corrupt');
CREATE TYPE snapshot_light_mode AS ENUM ('day', 'low_light', 'ir_night', 'unknown');
CREATE TYPE snapshot_tier AS ENUM ('full', 'compressed');

CREATE TABLE snapshots (
    id             uuid PRIMARY KEY DEFAULT uuidv7(),
    market_id      uuid NOT NULL,
    camera_id      uuid NOT NULL,
    capture_run_id uuid NOT NULL,

    -- ⚠ KUN `scheduled_at` DAN hisoblanadi, `captured_at` DAN EMAS (Pitfall 4)
    scheduled_at   timestamptz NOT NULL,
    captured_at    timestamptz NOT NULL,          -- forenzika uchun
    slot_time      time NOT NULL,
    business_date  date GENERATED ALWAYS AS
                   ((scheduled_at AT TIME ZONE 'Asia/Tashkent')::date) STORED,

    object_key     text NOT NULL,
    storage_tier   snapshot_tier NOT NULL DEFAULT 'full',
    size_bytes     integer NOT NULL,
    etag           text,
    width          integer,
    height         integer,

    quality_verdict            snapshot_quality NOT NULL,
    quality_mean               numeric(6,2) NOT NULL,   -- 0..255
    quality_stddev             numeric(6,2) NOT NULL,
    quality_saturation         numeric(6,2),            -- IR aniqlash uchun
    quality_thresholds_version smallint NOT NULL,
    light_mode                 snapshot_light_mode NOT NULL,

    capture_method text NOT NULL,                  -- 'go2rtc' | 'isapi' | 'ffmpeg'
    created_at     timestamptz NOT NULL DEFAULT now(),

    is_billable boolean GENERATED ALWAYS AS (quality_verdict = 'ok') STORED,

    CONSTRAINT uq_snapshots_run    UNIQUE (market_id, capture_run_id),
    CONSTRAINT uq_snapshots_key    UNIQUE (market_id, object_key),
    -- 5-FAZA UCHUN ILGAK (§C.8): `occupancy_events` shu juftlikka FK qo'yadi
    CONSTRAINT uq_snapshots_billable_anchor UNIQUE (id, is_billable)
);
```

**Ishonch:** HIGH (tartib va deterministik kalit — standart naqsh) · `uq_snapshots_billable_anchor` ning FK maqsadi sifatida ishlashi **MEDIUM** (§C.8 da tushuntirilgan, bajarib ko'rilmagan).

---

### B.5 — «Hech qachon ishlamagan slot» ni qanday aniqlash

#### Muammoning shakli

| Savol | Qanday javob beriladi |
|---|---|
| «Ishladi va yiqildi» | `status='failed'`, `attempts > 0`, `error_code` to'ldirilgan — **bu oson**, xato hodisa qoldiradi |
| «Umuman ishlamadi» | **Faqat kutilgan qator OLDINDAN yozilgan bo'lsa** aniqlanadi |
| «Hali vaqti kelmagan» | `status='pending'`, `scheduled_at > now()` |

Yo'qlik hodisa qoldirmaydi. Shuning uchun **materializatsiya majburiy** — u «alert-on-absence» ni «alert-on-state» ga aylantiradigan yagona qadam. Kunlik reja:

```
25 kamera × 7 slot = 175 qator/kun/bozor
365 kun × 10 bozor = 638 750 qator/yil   -> kichik jadval (uuid + bir necha ustun ≈ 150 B/qator ≈ 100 MB/yil)
```

#### Watchdog so'rovi

```sql
-- 1. Muddati o'tgan va HECH QACHON boshlanmagan slotlar -> `missed`
UPDATE capture_runs
   SET status = 'missed',
       finished_at = now(),
       error_code = 'capture_slot_missed'
 WHERE status = 'pending'
   AND scheduled_at < now() - make_interval(secs => :grace_seconds)
RETURNING market_id, camera_id, business_date, slot_time;

-- 2. Boshlangan, lekin lease'i tugagan va qayta urinish byudjeti tugagan
UPDATE capture_runs
   SET status = 'failed',
       finished_at = now(),
       error_code = COALESCE(error_code, 'capture_worker_lost')
 WHERE status = 'running'
   AND locked_until < now()
   AND attempts >= :max_attempts;

-- 3. Boshlangan, lease tugadi, byudjet bor -> QAYTARILADI
UPDATE capture_runs
   SET status = 'pending', locked_until = NULL, locked_by = NULL
 WHERE status = 'running'
   AND locked_until < now()
   AND attempts < :max_attempts;
```

Uchtasi ham `capture_tick` ning **birinchi qadami** (kadr olishdan **oldin**), ya'ni alohida watchdog jobi kerak emas — bitta kamroq harakatlanuvchi qism.

⚠ **`missed` va `failed` NI ARALASHTIRMANG.** Operatsion jihatdan ular butunlay boshqa: `failed` — «NVR javob bermadi, sabab X» (kamera/tarmoq muammosi), `missed` — «bizning tizimimiz ishlamadi» (bizning muammomiz). Ikkalasini bitta kodga yig'ish dala diagnostikasini o'ldiradi va alert matnini ma'nosiz qiladi.

#### «Rejaning O'ZI yaratilmadi» holati — yangi bozor tuzog'i

Bozor soat 12:00 da faollashtirilsa, o'sha kunning 06:00–08:00 slotlari **allaqachon o'tib ketgan**. Ularni oddiy `pending` qilib yozish **darhol 5 ta soxta `missed` alert** berardi va platforma admini birinchi kunidayoq alertga ishonishni to'xtatardi.

**Yechim:** materializatsiya paytida `scheduled_at + grace < now()` bo'lgan slotlar to'g'ridan-to'g'ri **`skipped`** holatida (kod: `capture_plan_created_late`) yoziladi va **alert bermaydi**. Ular hisobotda ko'rinadi (shaffoflik), lekin nosozlik sifatida sanalmaydi.

⚠ Xuddi shu yo'l **tizim uzoq vaqt o'lik bo'lgandan keyin** ham ishlaydi va bu **noto'g'ri**: 8 soatlik uzilishdan keyin materializatsiya emas, **watchdog** ishlaydi (qatorlar allaqachon bor) va ular `missed` bo'ladi — to'g'ri natija. Farq: `skipped` faqat **qator materializatsiya paytida yaratilayotgan bo'lsa** beriladi.

#### «Watchdogni kim kuzatadi» — halol javob

Agar planer **ham**, worker **ham** o'lik bo'lsa, hech kim hech nimani `missed` deb belgilamaydi va **jimlik hukm suradi**. Bu yopilishi kerak bo'lgan haqiqiy bo'shliq. Qatlamlar:

| # | Qatlam | Nimani qoplaydi | Narxi |
|---|--------|-----------------|-------|
| 1 | Tick ichidagi watchdog | Kadr olishning o'zi yiqilishi | 0 (allaqachon bor) |
| 2 | `system_heartbeats` jadvali + `core-api` ning `/internal/self-check` endpointi | **Worker/planer butunlay o'lik** — `core-api` boshqa jarayon, u tirik qoladi | ~40 qator |
| 3 | Kunlik **dayjest** («bugun 175/175 kadr, 0 o'tkazib yuborildi») belgilangan soatda | Butun stek o'lik — **odam xabar kelmaganini sezadi** | ~30 qator |
| 4 | Tashqi ping (healthchecks.io / cronitor / UptimeRobot) `/internal/self-check` ga | Xost/VPS butunlay o'lik | Tashqi xizmat, **v1 uchun majburiy emas** |

⚠ **`/healthz` ga ULAMANG.** Konteyner healthcheck'i (`compose.yaml`) — *liveness*: u yiqilsa Docker konteynerni qayta ishga tushiradi. Worker'ning yurak urishi eskirgani uchun sog'lom API'ni qayta ishga tushirish — klassik anti-naqsh. Yangi, **alohida** `/internal/self-check` endpointi kerak va u konteyner healthcheck'ida **ishlatilmaydi**.

`system_heartbeats` — juda kichik jadval (`GLOBAL_TABLES` ga kiradi, chunki komponent bozorga tegishli emas):

```sql
CREATE TABLE system_heartbeats (
    component    text PRIMARY KEY,      -- 'capture_tick', 'retention', 'backup'
    last_seen_at timestamptz NOT NULL,
    detail       jsonb
);
```

**Ishonch:** HIGH (materializatsiya naqshi) · 4-qatlam **ATAYIN OCHIQ QOLDIRILGAN** va Open Questions'da nomlangan.

---

### B.6 — Fan-out: 25 kamera × 7 slot va NOMA'LUM sessiya chegarasi

> Bu fazaning **eng katta operatsion noma'lumi**. 03-RESEARCH A.5: chegara «6–16 ulanish» emas, amalda **chiquvchi bitreyt**; uning RTSP javobida qanday ko'rinishi **LOW** ishonch; simulyator esa **umuman chegara modellamaydi** (03-VERIFICATION da ochiq yozilgan).

#### Birinchi topilma: vaqt byudjeti shunchalik keng'ki, KETMA-KET ham ishlaydi

Bu eng muhim de-risking fakti va u rejaga to'g'ridan-to'g'ri kiradi.

```
Bitta sovuq kadr (go2rtc /api/frame.jpeg):
  RTSP handshake (tunnel ortida)          ≈ 0,3–1,0 s
  Birinchi keyframe kutish (GOP 1–4 s)    ≈ 0,5–4,0 s
  JPEG kodlash + uzatish                  ≈ 0,1–0,3 s
  ---------------------------------------------------
  ≈ 1–5 s, ehtiyotkor baho: 4 s

25 kamera, TO'LIQ KETMA-KET, konkurentsiz:  25 × 4 s = 100 s
`grace` oynasi:                                        600 s
```

**Ya'ni `max_concurrent_captures = 1` HAM byudjetga sig'adi.** Bu shuni anglatadiki: NVR chegarasi qanchalik qattiq bo'lib chiqsa ham, yechim **sozlama** bilan topiladi va qayta loyihalash talab qilmaydi. Fazaning eng katta noma'lumi shu bitta fakt bilan **bloklovchi bo'lishdan chiqadi**.

⚠ Bu 10 bozor uchun ham to'g'ri: bozorlar **parallel** ishlaydi (har biri o'z NVR'i), ya'ni kutish vaqti ko'paymaydi.

#### Ikki darajali chegara

```python
# Global — VPS, go2rtc va tunnel umumiy resurs
GLOBAL_CAPTURE_SEMAPHORE = asyncio.Semaphore(settings.capture_global_concurrency)  # 8

# NVR bo'yicha — chegara AYNAN shu yerda
per_nvr = asyncio.Semaphore(nvr.max_concurrent_captures)                          # 4
```

| Sozlama | Joyi | Standart | Sabab |
|---|---|---|---|
| `capture_global_concurrency` | `Settings` (env) | **8** | VPS 4–6 vCPU; go2rtc bir vaqtda 8 dan ortiq oqim ochsa CPU va tunnel bo'g'iladi |
| `nvr_devices.max_concurrent_captures` | **DB, har NVR uchun** | **4** | Chegara qurilmaga xos. Admin UI'dan pasaytira oladi — self-service |
| `nvr_devices.capture_stagger_ms` | DB | **500** | Ulanishlarni vaqt bo'yicha yoyish. Semafor 4 ta parallel ruxsat bersa ham, ular **bir zumda** ochilmaydi |
| `capture_grace_seconds` | `Settings` | **600** | §A.2 |

#### Adaptiv pasaytirish — FAQAT pasaytirish

```
Agar bitta batch ichida >=2 kamera `nvr_stream_limit` yoki `nvr_unreachable` bilan
yiqilsa VA kamida bittasi MUVAFFAQIYATLI bo'lsa
  -> `nvr_devices.observed_stream_limit` ga muvaffaqiyatli soni yoziladi
  -> shu kun uchun samarali konkurentlik `max(1, muvaffaqiyatli_soni)` ga tushadi
  -> AUDIT yozuvi qoldiriladi
```

⚠ **Avtomatik OSHIRISH YO'Q.** Oshirish tebranishga (yiqilish → pasayish → tiklanish → oshirish → yiqilish) olib keladi va u chegara noma'lum bo'lgan holatda ayniqsa xavfli. Oshirish — **admin harakati**, va u UI'da o'lchangan qiymat bilan birga taklif qilinadi («o'lchandi: 4 parallel oqim ishladi, 6 yiqildi»).

⚠ «Kamida bittasi muvaffaqiyatli» sharti **majburiy**: aks holda NVR butunlay yo'q bo'lganda (tunnel uzildi) tizim konkurentlikni 1 ga tushirib, muammoni «chegara» deb noto'g'ri talqin qilardi.

#### Asosiy oqim vs sub-oqim — 3-faza qaroridan FARQ QILADI va bu ataylab

03-RESEARCH A.5 «go2rtc **doimiy ravishda** faqat sub-oqimga ulanadi» degan. Bu **jonli ko'rish** uchun to'g'ri va o'zgarmaydi. Kadr olish esa **boshqa profil**:

| Xususiyat | Jonli ko'rish | Kadr olish |
|---|---|---|
| Davomiyligi | Daqiqalar | **~4 soniya** |
| Bir vaqtda nechta | 1–3 | ≤4 (semafor) |
| Bitreyt ta'siri | Doimiy | **O'tkinchi** |
| Sifat talabi | «Ko'rinsa bo'ldi» | **5-faza aniqligining tomi** |

25 doimiy asosiy oqim = ~100 Mbps (imkonsiz). 4 ta o'tkinchi asosiy oqim × 4 s = ~16 Mbps × 4 s — butunlay boshqa narsa.

**Tavsiya:** `cameras.capture_stream text NOT NULL DEFAULT 'main'` (`'main'` | `'sub'`). Sabab **5-fazada**: sub-oqim odatda D1 (704×576) yoki past, va uzoqdagi kichik rastalar u yerda **yo'qoladi** — bu AI aniqligining ustki chegarasini oldindan pasaytiradi. Chegara muammosi chiqsa `'sub'` ga o'tish **bitta sozlama**.

⚠ Bu qaror 5-fazaning aniqlik shiftiga bevosita ta'sir qiladi va uni **real Karmana kadrida o'lchash kerak** (Phase 0 ma'lumoti). Open Questions'da nomlangan.

#### ISAPI `/picture` — «zaxira» emas, sessiya bosimida ENG XAVFSIZ yo'l

Bu 03-RESEARCH ning bir jumlasini kuchaytirish: ISAPI `/picture` **RTSP sessiyasini umuman ochmaydi** — u NVR'dan to'liq o'lchamli JPEG ni HTTP orqali oladi.

| Usul | RTSP sessiyasi | Kechikish | Sifat | Verdikt |
|---|---|---|---|---|
| go2rtc `/api/frame.jpeg` | **1 ta o'tkinchi** | 1–5 s | oqim sifati | **Standart** (CLAUDE.md) |
| ISAPI `/picture` | **0 ta** | 0,3–2 s (dekod yo'q) | to'liq o'lcham | **Sessiya bosimida afzal** |
| `ffmpeg` bir martalik | 1 ta + to'liq handshake | 3–10 s | to'liq | Oxirgi chora / diagnostika |

`nvr_devices.capture_method text NOT NULL DEFAULT 'go2rtc'` — uchala qiymat ham qo'llab-quvvatlanadi, tanlov **ma'lumot**, kod emas. Real NVR chegarasi ma'lum bo'lgach admin (yoki adaptiv mantiq) `'isapi'` ga o'tadi.

⚠ **`IsapiClient` ga yangi metod kerak.** Mavjud `get_xml(path)` javobni XML deb kutadi; `/picture` esa `image/jpeg` qaytaradi. Yangi `fetch_picture(channel_no, stream) -> bytes` metodi **XML parseridan o'tmaydi** va `Content-Type` ni tekshiradi (HTML xato sahifasini JPEG deb qabul qilib qo'ymaslik uchun — §C.7 ning magic-bayt darvozasi bu yerda ikkinchi qatlam).

#### go2rtc `/api/frame.jpeg` ning aniq shakli

```
GET http://go2rtc:1984/api/frame.jpeg?src=<stream_name>
```

Qo'llab-quvvatlanadigan parametrlar [CITED: AlexxIT/go2rtc `internal/mjpeg/README.md`]:

| Parametr | Ma'nosi | Bu fazada |
|---|---|---|
| `src` | **Majburiy** — oqim nomi (`cam_<uuid4>`) | Ha |
| `w` / `width`, `h` / `height` | O'lcham o'zgartirish | **YO'Q** — 5-faza to'liq o'lchamni xohlaydi; kichraytirish ma'lumot yo'qotadi va uni qaytarib bo'lmaydi |
| `rotate` | 90/180/270/−90 | Faqat kamera teskari o'rnatilgan bo'lsa (kamera darajasida sozlama) |
| `cache` (`10s`, `1m`) | Keshlangan kadr | ⚠ **ISHLATILMAYDI.** Kesh «bu kadr aynan shu slotda olingan» da'vosini buzadi — dalil zanjiri uchun halokatli |
| `hw` / `hardware` | Apparat tezlatish | Yo'q (VPS'da GPU yo'q) |

⚠ **Oqim go2rtc'da ro'yxatga olinmagan bo'lishi mumkin.** 3-fazada ro'yxatga olish **lazy** (faqat ko'rish so'ralganda). Kadr olish yo'li `Go2rtcClient.ensure_stream()` ni **avval** chaqirishi shart — u allaqachon mavjud va `PUT` ning `400` javobini natijadan o'lchaydi (03-14 topilmasi). Yangi kod yozilmaydi, mavjud klient qayta ishlatiladi.

**Ishonch:** vaqt byudjeti **MEDIUM** (komponentlar hisoblab chiqilgan, real tunnelda o'lchanmagan) · usullar taqqoslash **HIGH** (03-RESEARCH + go2rtc hujjati) · chegaraning namoyon bo'lishi **LOW** (o'zgarmadi).

---
## C. Sifat filtri va light_mode (CAM-06)

### C.7 — Qorong'i / buzuq / bo'sh kadrni ANIQ qanday aniqlash

#### Birinchi qaror: `opencv` KERAK EMAS

CLAUDE.md `opencv-python-headless` ni **cv-service** ning bog'liqligi sifatida sanaydi, cv-service esa **5-fazada tug'iladi**. 4-fazani unga bog'lash noto'g'ri: (a) yangi servisni bir faza oldin ochish kerak bo'lardi, (b) ~70 MB image o'sishi, (c) 4-faza aslida **hech qanday kompyuter ko'rishini** talab qilmaydi.

`Pillow` uchala hodisani ham beradi va u allaqachon retention siqishi uchun kerak (CLAUDE.md) — ya'ni **yangi bog'liqlik nolga teng**.

| Hodisa | Vosita | Mahalliy tekshirildi |
|---|---|---|
| Buzuq / kesilgan JPEG | `Image.open(...).load()` → `OSError: Truncated File Read` | ✅ 2026-08-04, `Pillow 12.2.0` |
| O'rtacha yorug'lik | `ImageStat.Stat(img.convert("L")).mean[0]` | ✅ (`mean == [10.0]`) |
| Kontrast / axborot miqdori | `ImageStat.Stat(...).stddev[0]` | ✅ (bir xil rangdagi kadr → `0.0`) |
| Dekompressiya bombasi | `Image.MAX_IMAGE_PIXELS` (standart **89 478 485**) | ✅ o'qildi |

#### Filtr zanjiri — arzondan qimmatga

```
1. len(data) < MIN_BYTES (2 000)              -> corrupt   [dekod YO'Q]
   len(data) > MAX_BYTES (8 MiB)              -> corrupt   [xotira chegarasi]
2. data[:3] != b"\xff\xd8\xff"                -> corrupt   [JPEG SOI yo'q]
   data[-2:] != b"\xff\xd9"                   -> corrupt   [EOI yo'q = kesilgan]
3. Image.open(BytesIO(data)); im.draft("L", (320, 180)); im.load()
       OSError / UnidentifiedImageError / DecompressionBombError -> corrupt
4. stat = ImageStat.Stat(im.convert("L"))
       mean, stddev
5. To'yinganlik (IR aniqlash): kichraytirilgan RGB dan HSV, o'rtacha S
6. Qaror -> quality_verdict + light_mode
```

⚠ **1 va 2-qadam dekodsiz ishlaydi va ular ENG QIMMATLI**: NVR yoki go2rtc xato holatida **HTML sahifa** yoki bo'sh javob qaytarishi mumkin va u JPEG emas. Magic-bayt darvozasi buni `Content-Type` sarlavhasiga ishonmasdan tutadi.

⚠ **`im.draft("L", (320, 180))`** — JPEG DCT darajasida kichraytirilgan dekod. To'liq dekoddan **bir necha barobar tez** va sifat metrikalari uchun 320×180 yetarli. Bu `Pillow` ning JPEG'ga xos xususiyati va uni ishlatmaslik CPU'ni behuda sarflardi.

⚠ **`ImageFile.LOAD_TRUNCATED_IMAGES` `False` bo'lib qolishi SHART** (standart qiymati; mahalliy tasdiqlandi). Biror bog'liqlik uni global ravishda `True` qilsa **kesilgan kadr jimgina o'tib ketardi** — ya'ni buzuq detektori butunlay o'chib qolardi va hech qanday test qizarmasdi. Darvoza: `test_truncated_images_flag_is_false`.

#### Chegaralar — RAQAM emas, QOIDA muhim

Real Karmana kadri yo'q, ya'ni har qanday raqam **taxmin**. Lekin **qoidaning shakli** ma'lumotsiz ham himoyalanadi:

```
corrupt  := dekod yiqildi YOKI magic/EOI yiqildi YOKI o'lcham chegaradan tashqarida
blank    := stddev < BLANK_STDDEV          (mean dan QAT'I NAZAR)
dark     := mean < DARK_MEAN  VA  stddev < DARK_STDDEV
ok       := qolgan hammasi
```

| Chegara | Standart | Nima uchun bu shakl |
|---|---|---|
| `MIN_BYTES` | 2 000 | To'liq qora 1280×720 JPEG ham ~1–3 KB. Bundan kichigi — javob emas, xato |
| `BLANK_STDDEV` | **8** | «Bo'sh» ning ta'rifi — **axborot yo'qligi**, qorong'ilik emas. Butunlay qora ekran (`stddev≈0`), kulrang «signal yo'q» ekrani (`stddev≈1`), yopilgan linza — hammasi `stddev` bilan tutiladi |
| `DARK_MEAN` | **40** / 255 | Yakka o'zi **yetarli emas** |
| `DARK_STDDEV` | **20** | ⚠ **Ikkinchi shart MAJBURIY.** Qishki 06:00 tong kadri qonuniy ravishda qorong'i bo'ladi (`mean≈30`), lekin unda **tuzilma bor** (`stddev>25`) — u YAROQLI. Faqat `mean` bilan filtrlash yiliga oylab qonuniy tong kadrlarini tashlab yuborardi va bu **kunlik hisobning yo'qolishi** demakdir |

⚠ Yagona shartli `dark` — bu fazadagi **eng qimmat xato** bo'lardi: u ma'lumotni jimgina yo'q qilardi va nosozlik faqat oylar keyin, tushum tahlilida ko'rinardi.

#### O'LCHOVNI SAQLASH — chegaradan muhimroq qaror

`quality_mean`, `quality_stddev`, `quality_saturation`, `size_bytes` **saqlanadi** (§B.4 sxemasi), faqat verdikt emas. Buning uchta natijasi bor:

1. **Chegaralar o'z ma'lumotimizdan chiqariladi.** Karmananing bir haftalik kadri kelgach: `SELECT percentile_cont(0.05) WITHIN GROUP (ORDER BY quality_mean) FROM snapshots WHERE ...` — chegara **taxmin emas, taqsimotdan** olinadi. Qayta suratga olish kerak emas
2. **Qayta tasniflash S3 ga tegmaydi** — barcha kirish ma'lumoti bazada
3. Phase 0 ning «real kadrlar → sifat chegaralarini sozlash» vazifasi **so'rov** bo'lib qoladi, tadqiqot ishi emas

#### Chegaralar o'zgarsa TARIX O'ZGARMAYDI

`quality_verdict` — **yozish paytida** qo'yiladigan oddiy ustun, hisoblanadigan emas. `quality_thresholds_version smallint` u qaysi chegara to'plami bilan qo'yilganini yozadi.

⚠ Agar verdikt chegaralardan **hisoblanadigan** bo'lganda, chegarani o'zgartirish **o'tmishdagi kadrlarning billing yaroqliligini retroaktiv o'zgartirardi** — ya'ni allaqachon yozilgan hisoblar asossiz bo'lib qolardi. Bu BILL-02 va AI-02 ning o'zgarmaslik falsafasining bevosita buzilishi. Qayta tasniflash **ataylab qilinadigan migratsiya** bo'ladi, audit yozuvi bilan.

**Ishonch:** vositalar **HIGH** (mahalliy tekshirildi) · aniq raqamlar **LOW** (ataylab — ular ma'lumot bilan aniqlashtiriladi) · qoidaning **shakli** MEDIUM-HIGH (ikki shartli `dark` qonuniy tong kadrlari argumentidan kelib chiqadi).

---

### C.8 — `light_mode` nima va «billing'ga ta'sir qilmaydi» qanday KAFOLATLANADI

#### `light_mode` ning ikki o'qilishi va tanlangan superset

CAM-06 ning matni qisqa: *«qorong'i/buzuq/bo'sh kadr belgilanadi, `light_mode` saqlanadi»*. Ikki o'qish mumkin:

| O'qish | Ma'nosi | Baho |
|---|---|---|
| (a) `light_mode` = **kameraning yorug'lik rejimi** (`day` / `ir_night`) | IR rejimidagi kadr monoxrom va detektor uchun **butunlay boshqa taqsimot** | ✅ Keyingi fazalar uchun **haqiqiy qiymat** |
| (b) `light_mode` = sifat yorlig'i | `quality_verdict` bilan **dublikat** | ⚠ Ma'lumot qo'shmaydi |

**Tanlov: (a), va `quality_verdict` alohida ustun bo'lib qoladi.** Narxi ~15 qator, foydasi 5 va 8-fazalarda:

- **5-faza (AI-02):** IR kadrda detektor aniqligi kunduzgidan sezilarli farq qiladi — fine-tuning dataseti `light_mode` bo'yicha muvozanatlanishi kerak
- **8-faza (RECON-05):** aniqlik hisoboti `light_mode` kesimida bo'linadi, aks holda «umumiy 92%» raqami tunda 70% ni yashirardi
- **Dala diagnostikasi:** kamera IR'ga umuman o'tmasa (IR yoritgich yonmagan) bu `light_mode='low_light'` ning barqaror ketma-ketligi sifatida ko'rinadi

```
ir_night   := to'yinganlik < IR_SATURATION (0,05)  VA  mean < NIGHT_MEAN (110)
low_light  := to'yinganlik >= IR_SATURATION        VA  mean < NIGHT_MEAN
day        := mean >= NIGHT_MEAN
unknown    := verdict = 'corrupt' (o'lchab bo'lmadi)
```

IR kadr — amalda **monoxrom**: R≈G≈B, ya'ni HSV to'yinganligi ≈0. Bu o'lchov arzon (64×64 gacha kichraytirilgan tasvirda).

⚠ `light_mode` **billing qaroriga kirmaydi**: IR tundagi kadr to'liq yaroqli dalil. U faqat **segmentatsiya** uchun. Aks holda tizim tunda yig'ilgan pattani asossiz rad etardi.

#### Kafolat: kelishuv emas, TUZILMA

CAM-06 ning oxirgi jumlasi — «yaroqsiz kadr billing'ga ta'sir qilmaydi». Uni bajarishning to'rt darajasi bor va ular **kuchayib boradi**:

| Daraja | Mexanizm | Qanday buziladi |
|---|---|---|
| 1 ❌ | Hujjat: «6-fazada `quality_verdict` ni tekshiring» | Birinchi so'rovda unutiladi |
| 2 ⚠ | `is_billable boolean GENERATED ALWAYS AS (quality_verdict = 'ok') STORED` | Ustun bor, lekin `WHERE` yozish baribir **eslashga** bog'liq |
| 3 ⚠ | Partial indeks + `analyzable_snapshots` ko'rinishi | Ko'rinishni chetlab o'tish mumkin |
| 4 ✅ | **`occupancy_events` yaroqsiz kadrga FK qo'ya OLMAYDI** | Buzib bo'lmaydi — DB rad etadi |

**4-daraja qanday quriladi (ikki fazaga bo'lingan):**

```sql
-- 4-FAZA (shu faza) — ILGAKNI QO'YADI:
ALTER TABLE snapshots
    ADD CONSTRAINT uq_snapshots_billable_anchor UNIQUE (id, is_billable);

-- 5-FAZA (keyingi faza) — ILGAKKA OSADI:
CREATE TABLE occupancy_events (
    ...,
    snapshot_id uuid NOT NULL,
    snapshot_is_billable boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_occupancy_billable_only CHECK (snapshot_is_billable),
    CONSTRAINT fk_occupancy_snapshot
        FOREIGN KEY (snapshot_id, snapshot_is_billable)
        REFERENCES snapshots (id, is_billable)
);
```

Natija: `quality_verdict <> 'ok'` bo'lgan kadr uchun `is_billable = false`, ya'ni FK juftligi `(id, true)` **mavjud emas** → `INSERT` DB darajasida rad etiladi. «Yaroqsiz kadr bandlik dalilini umuman TUG'DIRA OLMAYDI», ya'ni 6-faza unga tayanishi **jismonan** mumkin emas.

Bu 1-fazadagi naqshning aynan takrori: `FINANCIAL_TABLES` reyestri jadvallar **tug'ilishidan oldin** yozilgan, shunda 6-fazada `payments` yaratilgan kuni darvoza avtomatik yopilgan. Bu yerda ham 4-faza **ilgakni** qo'yadi, 5-faza esa uni topib **osadi**.

⚠ **`is_billable` ning `GENERATED` ustun sifatida `UNIQUE` ga kirishi tekshirilmagan** (PG 12+ da STORED generated ustunlar indekslanadi va unique constraint'ga kirishi kutiladi, lekin bu yerda **bajarib ko'rilmadi**). Reja **Wave 0 da buni o'lchashi** shart. Yiqilsa zaxira: `is_billable` ni oddiy `boolean NOT NULL` ustun qilib, `BEFORE INSERT/UPDATE` triggeri bilan `quality_verdict` dan hisoblash — kafolat saqlanadi, narxi bitta trigger. **[ASSUMED — DDL bajarilmagan]**

#### Yaroqsiz kadr NIMA QILADI

⚠ **O'CHIRILMAYDI.** Yaroqsiz kadr ham saqlanadi va admin uni ko'ra oladi. Sabab: «kamera qorong'i kadr beryapti» — bu **operatsion muammoning dalili** (IR yoritgich buzilgan, linza iflos, kamera burilgan) va uni ko'rmasdan tuzatib bo'lmaydi. U faqat **dalil zanjiridan** chiqariladi, arxivdan emas.

Kunlik hisobotda: «7 slotdan 2 tasi qorong'i — 12-kameraning IR yoritgichini tekshiring».

**Ishonch:** `light_mode` talqini **MEDIUM** (talab matni qisqa — Open Questions'da nomlangan) · FK-ilgak texnikasi **HIGH** (standart naqsh), aniq DDL **MEDIUM** (bajarilmagan).

---
## D. Obyekt-ombor va saqlash siyosati (CAM-07)

### D.9 — SeaweedFS: topologiya, kalit tartibi va rekvizit

#### Nima uchun SeaweedFS (qayta ochilmaydi, lekin tasdiqlandi)

| Manba | Holat 2026-08-04 |
|---|---|
| `seaweedfs/seaweedfs` | **Apache-2.0**, arxivlanmagan, 33 885 yulduz, oxirgi push **2026-08-03**, oxirgi reliz **4.40** (2026-07-20) [VERIFIED: GitHub API] |
| `chrislusf/seaweedfs:4.40` Docker tegi | **Mavjud**, 2026-07-20 [VERIFIED: Docker Hub API] |
| `deuxfleurs-org/garage` | **AGPL-3.0** [VERIFIED: GitHub API] → CLAUDE.md ning AGPL taqiqi bo'yicha **muqobil sifatida ham yozilmaydi** |
| MinIO | Arxivlangan (3-fazadan meros) |

#### Compose shakli

```yaml
  storage:
    # OLTINCHI/YETTINCHI KONTEYNER, UCHINCHI SERVIS EMAS — tayyor image
    # (`db`, `cache`, `go2rtc`, `nginx` bilan bir toifa).
    image: chrislusf/seaweedfs:4.40
    command:
      - "server"
      - "-dir=/data"
      - "-s3"
      - "-s3.port=8333"                       # ⚠ ANIQ beriladi (pastdagi izoh)
      - "-s3.config=/etc/seaweedfs/s3.json"
      - "-master.volumeSizeLimitMB=1024"
    volumes:
      - seaweed:/data
      - ./ops/seaweedfs/s3.json:/etc/seaweedfs/s3.json:ro   # `:ro` — loyiha qoidasi
    environment:
      TZ: ${TZ:-Asia/Tashkent}
    healthcheck:
      # `nc` — `go2rtc` va `nvr-sim-rtsp` bilan BIR XIL qaror: "jarayon
      # tinglayaptimi?" savoliga to'liq javob, tekshirilmagan endpointga
      # tayanmaydi.
      test: ["CMD", "nc", "-z", "127.0.0.1", "8333"]
    restart: unless-stopped
    # ⚠ `ports:` YO'Q — T-01-04 qoidasi. Ombor faqat compose tarmog'idan ko'rinadi.
```

| Qaror | Sabab |
|---|---|
| `weed server -s3` (bitta jarayon) | Master + volume + filer + S3 gateway'ni bitta jarayonda ko'taradi — bitta bozor uchun taqsimlangan rejim keraksiz murakkablik |
| **`-s3.port=8333` ANIQ beriladi** | Bu **standart qiymat** [VERIFIED: `weed/command/server.go:161` — `cmdServer.Flag.Int("s3.port", 8333, ...)`], lekin standartga tayanish keyingi major versiyada jimgina buzilishi mumkin |
| `ports:` bloki yo'q | 3-fazadagi go2rtc qarori bilan bir xil: ombor internetdan ko'rinmasligi kerak |
| `-master.volumeSizeLimitMB=1024` | Ko'p mayda fayl — SeaweedFS ning maqsadli holati; 1 GB volume fayllari zaxira nusxa uchun qulay |

#### `s3.json` — va undagi TUZOQ

Rasmiy misol fayli **aynan shunday boshlanadi** [VERIFIED: `docker/compose/s3.json`, `curl` bilan olindi 2026-08-04]:

```json
{ "identities": [ { "name": "anonymous", "actions": ["Read"] }, ... ] }
```

> ⚠⚠ **`anonymous` + `Read` — BUTUN ARXIVNI AUTENTIFIKATSIYASIZ O'QISHGA OCHADI.** Misol faylni nusxalash barcha bozorlarning dalil-kadrlarini portga yeta oladigan har kimga beradi. Bu shaxsiy ma'lumot (bozor tashrifchilari tasvirlari) va O'zR qonuni ostidagi ma'lumot. `anonymous` yozuvi **BO'LMASLIGI SHART**.

Bizning faylimiz:

```json
{
  "identities": [
    {
      "name": "sbozor-core-api",
      "credentials": [{ "accessKey": "${S3_ACCESS_KEY}", "secretKey": "${S3_SECRET_KEY}" }],
      "actions": ["Read:sbozor-snapshots", "Write:sbozor-snapshots",
                  "List:sbozor-snapshots", "Tagging:sbozor-snapshots"]
    }
  ]
}
```

`Action:bucket` (va `Action:bucket/prefix`) shakli qo'llab-quvvatlanadi [VERIFIED: `weed/s3api/auth_credentials.go:2127,2189` — *«"Read:bucket", "Write:bucket/prefix" or "Write:bucket/prefix/\*" is scoped»*]. `Admin` **berilmaydi** — ilova bucket yaratish/o'chirishga muhtoj emas (bucket bir marta, qo'lda yoki migratsiya bilan yaratiladi).

⚠ `s3.json` da **sirlar bor**, ya'ni u `.env` dan interpolatsiya qilinadi yoki `compose` sekretlari orqali beriladi. `git` ga **kalitlari bilan commit qilinmaydi** — repoda `s3.json.example` turadi (3-fazadagi `wg0.conf.example` naqshi).

#### Bitta bucket, `market_id` prefiksi — bozor boshiga bucket EMAS

| Variant | Verdikt |
|---|---|
| **Bitta bucket `sbozor-snapshots`, `market_id` — birinchi prefiks** | ✅ **TANLANDI.** SeaweedFS har bucket uchun *collection* yaratadi — o'nlab/yuzlab bucket operatsion yuk. Tenant izolyatsiyasi baribir **ilova + DB** da, chunki ilovada bitta rekvizit bor |
| Bozor boshiga bucket | ❌ Yangi bozor onboardingiga «bucket yarat + IAM yozuvi qo'sh» qadamini qo'shardi — **self-service qoidasining buzilishi** |

⚠ **Halol e'tirof:** bitta rekvizit — buzilgan `core-api` barcha bozorlarning kadrlarini o'qiy oladi. Bu **DB bilan bir xil ishonch modeli** (`sbozor_app` roli GUC o'zgarishi bilan istalgan bozorga qaray oladi). Ya'ni bu yangi teshik emas, mavjud chegaraning davomi — lekin u Security Domain'da nomlanadi, jimgina qoldirilmaydi.

#### Kalit tartibi — `sana` `kamera` dan OLDIN

```
sbozor-snapshots/{market_id}/{business_date}/{camera_id}/{HHMM}.jpg
sbozor-snapshots/1f0c…/2026-09-01/9a2b…/0630.jpg
```

| Tartib | «Kun bo'yicha» amallar | «Kamera bo'yicha» amallar |
|---|---|---|
| **`market/sana/kamera/slot`** ✅ | **Bitta prefiks skani** — retention, kunlik zaxira, kunni o'chirish | Kamera+sana ham bitta prefiks; «kameraning butun tarixi» — **DB indeksidan** |
| `market/kamera/sana/slot` | N ta prefiks skani (har kamera uchun) — retention qimmatlashadi | — |

**Hal qiluvchi dalil:** eng katta ommaviy amal — **retention** (kunlik, barcha kadrlar ustidan). U sana bo'yicha ishlaydi. «Kameraning butun tarixi» so'rovi esa **hech qachon S3 listing bilan bajarilmaydi** — u `snapshots` jadvalining indeksidan keladi.

> ⚠ **QOIDA: S3 hech qachon so'rov mexanizmi emas.** `ListObjectsV2` faqat retention va yetim obyekt supurgisi uchun. Har qanday foydalanuvchi so'rovi bazadan javob oladi. Aks holda ombor almashishi (Uzbekiston hostingiga ko'chish) so'rov semantikasini ham o'zgartirardi.

Kalit **deterministik** (§B.4) — tasodifiy komponent yo'q. Siqilgan versiya **o'sha kalitni ustiga yozadi**: 6-fazadagi dalil havolalari **hech qachon buzilmasligi** kerak, ya'ni siqish kalit o'zgartirmaydi. Tier `snapshots.storage_tier` da yashaydi.

---

### D.9.2 — ⚠ `aioboto3` PIN TO'QNASHUVI — CLAUDE.md TUZATILISHI KERAK

Bu bo'lim `arq` epizodining ikkinchi nusxasi: CLAUDE.md ikkita versiyani birga sanaydi, PyPI metadata esa ularni **birga o'rnatib bo'lmasligini** ko'rsatadi.

```
CLAUDE.md:  aioboto3 15.5.0  VA  boto3 1.43.57

Haqiqatda [VERIFIED: PyPI JSON API, 2026-08-04]:
  aioboto3 15.5.0  ->  aiobotocore[boto3]==2.25.1      (QATTIQ `==` pin)
  aiobotocore 2.25.1 ->  botocore<1.40.62,>=1.40.46
                     ->  boto3<1.40.62,>=1.40.46       (`boto3` extra)

  ya'ni aioboto3 15.5.0 bilan boto3 1.43.57 BIR VAQTDA MUMKIN EMAS —
  eng yuqorisi boto3 1.40.61 (uch minor orqada).
```

Qo'shimcha xolat signali: `aioboto3` ning oxirgi relizi **2025-10-30**, oxirgi push **2025-12-15** — ya'ni ~8–9 oy harakat yo'q, va u **eskirgan `aiobotocore 2.25.1`** ni qattiq pinlaydi (`aiobotocore` ning o'zi allaqachon **3.9.0**, 2026-08-01) [VERIFIED: GitHub API + PyPI].

⚠ Bu `arq` dan **yengilroq**: `core-api` da `boto3` hozircha **umuman yo'q**, ya'ni mavjud pin buzilmaydi. Lekin qattiq `==` pin **botocore xavfsizlik yangilanishlarini bloklaydi** va bu 12 oylik saqlash siyosati bo'lgan tizim uchun muhim.

#### Uchta variant va tavsiya

| Variant | Paketlar | Holat | Verdikt |
|---|---|---|---|
| **C. `aiobotocore==3.9.0`** (to'g'ridan-to'g'ri) | `aiobotocore` → `botocore<1.43.57,>=1.43.3`, `aiohttp>=3.14` | Reliz **2026-08-01**, push 2026-08-03, **Apache-2.0**, faol | ✅ **TAVSIYA.** Async, joriy, qattiq `==` pin yo'q. Bizga faqat `put_object`/`get_object`/`head_object`/`delete_objects` kerak — hammasi past darajali klientda bor. ⚠ `aiohttp` **allaqachon o'rnatilgan** (`taskiq` uni talab qiladi — [VERIFIED: `taskiq 0.12.4` `requires_dist`]), ya'ni yangi HTTP steki kirmaydi |
| B. `boto3` (joriy) + `asyncio.to_thread(...)` | `boto3`, `botocore` | Eng qo'llab-quvvatlanadigan | ⚠ **Kuchli zaxira.** Kunlik ~175 chaqiruv uchun ip (thread) narxi nolga yaqin. `aioboto3` ning barcha muammolarini chetlab o'tadi. Kamchiligi: bloklovchi chaqiruv worker ipida |
| A. `aioboto3==15.5.0` | + `aiobotocore==2.25.1` + `boto3<1.40.62` | Eskirgan, qattiq pinli | ❌ **RAD ETILADI** va CLAUDE.md ning yozuvi shu tadqiqot bilan tuzatiladi |

⚠ **`minio-py` — CLAUDE.md da allaqachon TAQIQ** va bu tadqiqot uni qayta ochmaydi.

⚠ **Qo'lda SigV4 imzolash — mutlaqo RAD ETILADI.** Kanonik so'rov qurish va HMAC zanjiri — xavfsizlikka tegishli kod va uni qo'lda yozish `Don't Hand-Roll` ro'yxatining birinchi qatori.

---

### D.10 — Saqlash siyosati: kim bajaradi, qanday isbotlanadi

#### Siyosat

```
0–90 kun      : storage_tier='full'        — original JPEG
91–455 kun    : storage_tier='compressed'  — QAYTA KODLANGAN (o'sha kalit)
455+ kun      : storage_tier='purged'      — OBYEKT o'chiriladi, QATOR QOLADI
```

| Sozlama | Standart | Joyi |
|---|---|---|
| `retention_full_days` | 90 | `Settings` (env) — CAM-07 «sozlanadigan» deydi |
| `retention_compressed_days` | 365 | `Settings` |
| `retention_jpeg_quality` | 55 | `Settings` |
| `retention_batch_size` | 500 | `Settings` — bitta yugurishda qancha obyekt |

#### ⚠ QATOR HECH QACHON O'CHIRILMAYDI

Bu qarorning sababi 6-fazada: `daily_charges` dalil-kadrlarga bog'lanadi (BILL-02) va `snapshots` qatorini o'chirish **hisob yozuvining dalil havolasini uzardi** yoki FK'ni buzardi. Shuning uchun:

- Obyekt o'chiriladi (`object_deleted_at` qo'yiladi, `storage_tier='purged'`)
- Qator qoladi va u «kadr mavjud edi, arxivdan 2027-11-30 da chiqarildi» deb **halol** ko'rsatiladi
- `is_billable` **o'zgarmaydi** — o'sha paytda qilingan hisob retroaktiv bekor qilinmaydi

#### Kim bajaradi

**Kunlik `retention.daily` vazifasi**, o'sha `taskiq scheduler` orqali — lekin **oddiy cron bilan**, tick orqali emas:

```python
@broker.task(task_name="retention.daily",
             schedule=[{"cron": "20 3 * * *", "cron_offset": "Asia/Tashkent"}])
```

⚠ **Nima uchun bu yerda cron QABUL QILINADI, kadr olishda esa YO'Q** — farq nozik va u yozib qo'yilishi kerak:

| Xususiyat | Kadr olish sloti | Retention |
|---|---|---|
| Vazifa turi | **Vaqt nuqtasi** — 06:00 kadri faqat 06:00 da olinadi | **Konvergent** — «`full` va 90 kundan eski hamma narsani siq» |
| Bir kun o'tkazib yuborilsa | Ma'lumot **butunlay yo'qoladi** | Ertaga **o'zi tutib oladi** (predikat holat ustida, vaqt ustida emas) |
| `taskiq` ning xotiradagi cron holati | **Halokatli** | **Ahamiyatsiz** |

`cron_offset="Asia/Tashkent"` — `taskiq` cronni UTC'da baholaydi va `cron_offset` mintaqa nomini qabul qiladi [VERIFIED: `is_cron_task_now()` → `now.astimezone(ZoneInfo(offset))`]. Busiz 03:20 **UTC** da, ya'ni Toshkentda 08:20 da — kadr olish cho'qqisining o'rtasida ishlagan bo'lardi.

#### Siqish qadami

```python
im = Image.open(BytesIO(original))
im.load()
buf = BytesIO()
im.save(buf, "JPEG", quality=settings.retention_jpeg_quality,
        optimize=True, progressive=True)
```

| Qaror | Sabab |
|---|---|
| **Kichraytirilmaydi** (faqat qayta kodlash) | CAM-07 «siqilgan» deydi, «kichraytirilgan» emas. Kichraytirish geometriyani buzadi va kelajakda CV'ni qayta ishga tushirish imkonini yo'qotadi. Ixtiyoriy `RETENTION_MAX_EDGE` sozlamasi **standart bo'yicha o'chiq** |
| `WHERE storage_tier='full'` — **qat'iy shart** | Qayta kodlash **yo'qotishli**. Ikki marta siqilgan kadr ikki marta buziladi. Predikat buni **strukturaviy** to'sadi (holat mashinasining bir yo'nalishli o'tishi) |
| Bir marta o'qish, bir marta yozish, keyin baza | §B.4 dagi tartib bilan bir xil qoida: baza obyektning **joriy holatini** tasdiqlaydi |

#### 90 kunni KUTMASDAN qanday isbotlanadi

Bu §F.15 ning bir qismi va u **rejaga bevosita kiradi**:

1. **Chegara — parametr, konstanta emas.** Test `retention_full_days=0` qo'yadi va bugungi kadr darhol siqilishini o'lchaydi
2. **Vaqt in'ektsiya qilinadi.** Job `today: date` argumentini oladi (standarti `business_today()`). ⚠ Job ichida `date.today()` **TAQIQLANGAN** — bu ham loyiha qoidasi (`timeutil` docstringi), ham testlanuvchanlik sharti
3. **«Tiklash» shu fazada = qayta o'qish.** Siqilgandan keyin obyekt `GET` qilinadi, dekod qilinadi va (a) dekod muvaffaqiyatli, (b) o'lchamlar **o'zgarmagan**, (c) `size_bytes` **kamaygani** tasdiqlanadi
4. **To'liq zaxira/tiklash mashqi bu faza EMAS** — u FOUND-07 / 8-faza. Bu yerda faqat obyektning **o'qilishi** isbotlanadi

**Ishonch:** HIGH (mexanizm oddiy va to'liq sinaladigan) · siqish nisbati **MEDIUM** (real kadrda o'lchanmagan).

---

### D.11 — Hajm arifmetikasi: oqim tanlovi omborni ~12 BAROBAR o'zgartiradi

```
Bir bozor: 25 kamera × 7 slot = 175 kadr/kun
```

| Oqim | Bir kadr | Kun/bozor | 90 kun `full` | 365 kun `compressed` (~4×) | **Barqaror holat** |
|---|---|---|---|---|---|
| **Asosiy (4 MP)** | ~500 KB | 87,5 MB | **7,9 GB** | ~8,0 GB | **~16 GB/bozor** |
| **Sub (D1)** | ~40 KB | 7,0 MB | 0,63 GB | ~0,64 GB | **~1,3 GB/bozor** |

Contabo diski **400+ GB**:

| Ssenariy | Bozorlar soni (diskning ~70% i) |
|---|---|
| Asosiy oqim | **~17 bozor** |
| Sub-oqim | **~200 bozor** (disk chegara bo'lishdan chiqadi) |

⚠ **Bu §B.6 dagi `capture_stream` qarorining ikkinchi yuzi.** Asosiy oqim 5-fazaning aniqlik shiftini ko'taradi va omborni 12 barobar oshiradi. Ikkalasi bitta sozlamada hal bo'ladi va **real kadr o'lchamini bilmaguncha** to'g'ri javob yo'q.

**Tavsiya:** standart `'main'`, lekin **birinchi haftadanoq real o'lcham o'lchanadi** (`snapshots.size_bytes` allaqachon saqlanadi — hech qanday qo'shimcha ish kerak emas) va disk prognozini UI'da ko'rsatuvchi oddiy so'rov beriladi:

```sql
SELECT avg(size_bytes), count(*) FROM snapshots WHERE business_date > current_date - 7;
```

⚠ **Postgres tomonidagi o'sish alohida va u kichik:** `capture_runs` ~150 B/qator × 175/kun/bozor ≈ 10 MB/yil/bozor; `snapshots` shunga yaqin. Ya'ni **baza hech qachon disk chegarasi bo'lmaydi** — chegara har doim obyekt arxivi.

⚠ **Zaxira nusxa (FOUND-07, 8-faza) shu raqamlarni meros oladi:** 16 GB/bozor tashqi bucketga nusxalanishi kerak. Sana-birinchi kalit tartibi (§D.9) bu yerda ikkinchi marta foyda beradi — `rclone sync` bitta prefiks bilan «faqat kechagi kun» ni ko'chira oladi.

**Ishonch:** arifmetika **HIGH**, kirish kattaliklari **LOW-MEDIUM** (kadr o'lchami real NVR'da o'lchanmagan — shuning uchun ikkala ssenariy ham ko'rsatilgan).

---
## E. Alert va o'z-o'zini kuzatish (FOUND-06)

### E.12 — Yo'qlikka alert: heartbeat, watchdog, dead-man's switch

#### CLAUDE.md ning talabi va uning aniq ma'nosi

> *«Backup failure → Telegram alert. Alert on **absence of a success signal**, not just on error exit codes.»*

Bu bitta jumla butun bo'limning arxitekturasini belgilaydi. Xato hodisasiga alert — **oson va yetarsiz**: kod umuman ishga tushmasa xato ham chiqmaydi. Uch xil «jimlik» bor va ular **turli** mexanizm talab qiladi:

| Jimlik turi | Misol | Detektor |
|---|---|---|
| **Ish bajarildi, natija yomon** | NVR `401` qaytardi | Oddiy `try/except` → `capture_runs.failed` → Sentry |
| **Ish umuman bajarilmadi** | 06:00 sloti hech kim tomonidan olinmadi | **Materializatsiya + watchdog** (§B.5) |
| **Detektorning O'ZI bajarilmadi** | Worker ham, planer ham o'lik | **Heartbeat + tashqi kuzatuvchi** |

#### Uch mustaqil manba (FOUND-06 ning uchta bandi)

| Signal | Manba | «Yo'qlik» ni qanday aniqlaydi |
|---|---|---|
| **Kamera offline** | 3-fazadan mavjud: `cameras.status`, `channel_offline` kodi | Kadr olish yiqilishlari **ketma-ketligi**: `N` slot ketma-ket `failed` → kamera offline deb e'lon qilinadi (bitta yiqilish alert bermaydi) |
| **O'tkazib yuborilgan slot** | `capture_runs.status='missed'` | Materializatsiya (§B.5) — yo'qlik **qatorga** aylanadi |
| **Backup xatosi** | `system_heartbeats('backup')` | ⚠ **Backup 8-fazada quriladi (FOUND-07).** 4-faza uning uchun **heartbeat kontraktini** beradi: har muvaffaqiyatli zaxira `last_seen_at` ni yangilaydi; watchdog «24 soatdan beri yangilanmagan» ni ko'radi. Ya'ni backup **hech qachon yozilmasa ham** alert keladi |

#### Uch komponentli o'z-o'zini kuzatish

```
┌─ 1 ── capture_tick (har daqiqada)
│       - lease qaytarish / `missed` belgilash / `failed` yopish
│       - system_heartbeats['capture_tick'].last_seen_at = now()
│
├─ 2 ── alert_sweep (har 5 daqiqada, o'sha planerdan)
│       - yangi `missed`/`failed` larni GURUHLAB Telegram'ga yuboradi
│       - eskirgan heartbeat larni tekshiradi  ('backup', 'retention')
│
└─ 3 ── core-api GET /internal/self-check   (ALOHIDA JARAYON)
        - `capture_tick` heartbeat'i > N daqiqa eskirganmi?
        - 200 {"ok": true} / 503 {"ok": false, "stale": ["capture_tick"]}
        - ⚠ konteyner healthcheck'ida ISHLATILMAYDI
```

⚠ **3-qadamning butun ma'nosi — u BOSHQA JARAYONDA.** 1 va 2 worker'da; worker o'lsa ikkalasi ham jim bo'ladi. `core-api` esa alohida konteyner va u tirik qoladi. Ikkalasi bir vaqtda o'lishi uchun xost yoki compose butunlay yiqilishi kerak — va o'shanda nginx ham 502 beradi, ya'ni **ko'rinadi**.

⚠ **`/healthz` ga ULANMAYDI.** Liveness probe'ni bog'liqlik holatidan bog'lash — klassik anti-naqsh: worker'ning yurak urishi eskirgani uchun **sog'lom API qayta ishga tushirilardi** va bu hech nimani tuzatmasdi.

#### Dead-man's switch — halol chegara

To'liq ishonchli javob **quti tashqarisida** bo'lishi kerak: agar VPS butunlay o'lsa, ichkaridagi hech bir kod alert yubora olmaydi. Uch pog'onali javob:

| Pog'ona | Vosita | v1 da |
|---|---|---|
| Ichki | `alert_sweep` + `/internal/self-check` | ✅ **Quriladi** |
| Insonga tayangan | **Kunlik dayjest** belgilangan soatda: «Bugun 175/175 kadr, 0 o'tkazib yuborildi, 3 sifatsiz» | ✅ **Quriladi.** Xabar **kelmasa** — bu ham signal. Zaif, lekin narxi nolga yaqin va u **butun stek o'lik** holatini qoplaydi |
| Tashqi | healthchecks.io / cronitor / UptimeRobot → `/internal/self-check` | ⚠ **ATAYIN OCHIQ.** Bitta URL sozlash — ops ishi, kod emas. `ops/docs/` ga yoziladi va Open Questions'da nomlanadi |

#### Yetkazish: Telegram Bot API to'g'ridan-to'g'ri, `aiogram`siz

`bot-service` **7-fazada** tug'iladi (BOT-01…BOT-04). Uni 4-fazaga tortish butun bir servisni bir faza oldinga surardi. FOUND-06 uchun **bitta HTTP chaqiruv** yetadi:

```
POST https://api.telegram.org/bot<TOKEN>/sendMessage
{"chat_id": <PLATFORM_ADMIN_CHAT_ID>, "text": "...", "parse_mode": "HTML"}
```

| Qaror | Sabab |
|---|---|
| `httpx` (allaqachon prod bog'liqligi, D-16) | Yangi paket **YO'Q**. `aiogram` 7-fazada o'z joyida qoladi |
| Faqat `sendMessage` | 4-fazada tugma, FSM, webhook, inline — **hech biri kerak emas** |
| `ALERT_TELEGRAM_BOT_TOKEN`, `ALERT_TELEGRAM_CHAT_ID` — `Settings` | ⚠ Token — **sir**: `SecretStr`, `censor_secrets` ro'yxatiga qo'shiladi, `repr` da chiqmaydi (`settings.py` ning mavjud naqshi) |
| Bo'sh token = alert **o'chiq**, lekin **jimgina emas** | Ishga tushishda `log.warning("alerts_disabled")`. Bo'sh token bilan jimgina ishlash — aynan «alert bor deb o'ylash» yolg'oni |
| **Chegara: 5 s timeout + `tenacity` bilan 2 urinish** | Telegram javob bermasa kadr olish yo'li **bloklanmasligi** kerak. Alert yiqilishi — jurnalga va Sentry'ga, boshqa hech nima |

⚠ **Alert yuborish HECH QACHON asosiy yo'lni bloklamaydi.** U `capture_tick` ning tranzaksiyasidan **tashqarida** va alohida vazifada. Aks holda Telegram uzilishi kadr olishni to'xtatardi — kuzatuv vositasi kuzatilayotgan tizimni yiqitardi.

⚠ **Sentry — alertning o'rnini BOSMAYDI va teskarisi ham.** Sentry: dasturchi uchun istisno izi va stack frame. Telegram: platforma admini uchun operatsion signal. Sentry'da `missed` sloti hech qachon ko'rinmaydi (istisno yo'q), Telegram'da esa stack trace hech qachon ko'rinmaydi (foydasiz). Ikkalasi ham FOUND-06 da nomlangan.

**Ishonch:** HIGH (mexanizm oddiy, komponentlar mavjud) · tashqi dead-man's switch **ATAYIN OCHIQ**.

---

### E.13 — Alert charchog'i: guruhlash, chegara va HECH QACHON bostirilmaydiganlar

#### Muammoning ko'lami

```
Yomon kun: tunnel 07:00–08:00 da uzildi.
  25 kamera × 3 slot = 75 ta yiqilish
  Guruhlashsiz: 75 ta Telegram xabari
```

Telegram cheklovlari [CITED: core.telegram.org/bots/faq]:

> *«In a single chat, avoid sending more than **one message per second**. We may allow short bursts that go over this limit, but eventually you'll begin receiving **429** errors.»*
> *«For bulk notifications, bots are not able to broadcast more than about **30 messages per second**.»*
> *«In a group, bots are not be able to send more than **20 messages per minute**.»*

⚠ Platforma admini alertlarni **guruhda** olishi ehtimoli yuqori (ops guruhi) → amaldagi chegara **daqiqasiga 20 ta xabar**. 75 ta xabar birinchi daqiqada `429` beradi va **eng muhim xabarlar yo'qoladi**.

Lekin texnik chegara ikkinchi darajali. Asosiy muammo **inson**: ketma-ket 75 ta xabar olgan admin ertasi kuni bildirishnomani o'chiradi va **haqiqiy nosozlik ham ko'rinmay qoladi**.

#### Guruhlash qoidalari

| Qoida | Amalda |
|---|---|
| **Slot bo'yicha yig'ish** | Bitta slotdagi barcha yiqilishlar — **bitta** xabar: «06:30 — 25 kameradan 22 tasi yiqildi (`nvr_unreachable`). Bozor: Karmana» |
| **Sabab kodi bo'yicha yig'ish** | Bir xil `error_code` ni takrorlamaydi; har kod bir marta + soni |
| **Bozor bo'yicha ajratish** | Ko'p bozorli xabar o'qib bo'lmaydigan bo'ladi. Har bozor — o'z xabari |
| **Debounce** | Bir xil `(market_id, error_code)` juftligi uchun **60 daqiqada bir marta**. Takrorlar `alert_events` da sanaladi va keyingi xabarda «(so'nggi soatda yana 47 marta)» bo'lib chiqadi |
| **Eskalatsiya, spam emas** | Muammo davom etsa **chastota oshmaydi**, xabar **darajasi** oshadi: 1-soat `warning`, 3-soat `critical`, matnda davomiylik ko'rsatiladi |
| **Tiklanish ham xabar qilinadi** | «Karmana: kadr olish tiklandi (2 s 15 daq uzilishdan keyin)». Yopilmagan alert — ochiq ish, va uni yopadigan yagona narsa — tiklanish xabari |

`alert_events` jadvali (kichik, `GLOBAL_TABLES`):

```sql
CREATE TABLE alert_events (
    id            uuid PRIMARY KEY DEFAULT uuidv7(),
    market_id     uuid,                 -- NULL = platforma darajasi
    alert_key     text NOT NULL,        -- 'capture_missed', 'camera_offline', 'backup_stale'
    severity      text NOT NULL,        -- 'info' | 'warning' | 'critical'
    first_seen_at timestamptz NOT NULL,
    last_seen_at  timestamptz NOT NULL,
    occurrences   integer NOT NULL DEFAULT 1,
    notified_at   timestamptz,          -- oxirgi Telegram xabari
    resolved_at   timestamptz,
    detail        jsonb
);
CREATE UNIQUE INDEX uq_alert_events_open
    ON alert_events (COALESCE(market_id, '00000000-0000-0000-0000-000000000000'::uuid), alert_key)
    WHERE resolved_at IS NULL;
```

⚠ Qisman UNIQUE indeks **ochiq alert bitta bo'lishini** kafolatlaydi — bu 3-fazadagi `nvr_discovery_runs` ning «bir vaqtda ikki skan yo'q» indeksi bilan bir xil naqsh.

#### HECH QACHON bostirilmaydiganlar

Guruhlash va debounce **hamma narsaga** qo'llanmaydi. Quyidagilar **har doim va darhol** yuboriladi:

| Hodisa | Nima uchun bostirilmaydi |
|---|---|
| **Butun bozorda kadr olish 2 slot ketma-ket 0%** | Bu «bir necha kamera» emas, **bozor ko'r bo'lib qoldi**. Kunlik hisobning butun asosi yo'qoladi |
| **Backup heartbeat > 26 soat eskirgan** | Ma'lumot yo'qotish xavfi. FOUND-07 ning yagona kuzatuv nuqtasi |
| **`nvr_account_locked`** | Vaqt sezgir: 30 daqiqalik qulf oynasi bor va uni kutish kerak — bostirilgan xabar admin'ni kechiktirardi |
| **Shifr kaliti xatosi (`nvr_credential_unreadable`)** | Konfiguratsiya nosozligi; kadr olish **hech qachon** o'zi tuzalmaydi |
| **Disk to'lishi > 85%** | ⚠ **Yangi va u qo'shilishi kerak** — §D.11 ning bevosita natijasi. Disk to'lsa Postgres ham, ombor ham to'xtaydi va **hech qanday alert yuborib bo'lmaydi** |

⚠ **Bitta kamera bitta slotda yiqilishi — ALERT EMAS.** U jurnalda va kunlik dayjestda ko'rinadi. Har bir o'tkinchi tarmoq uzilishiga alert yuborish — alert kanalini birinchi haftadayoq o'ldirish yo'li. Chegara: **kamida 3 ta ketma-ket slot** yoki **bitta slotda ≥30% kameralar**.

#### Kunlik dayjest — asosiy kuzatuv sirtidir, alertlar emas

```
📊 Karmana — 2026-09-01
Kadrlar: 173/175 (98,9%)
  ✅ 168 yaroqli · 🌑 3 qorong'i · ⬛ 1 bo'sh · ❌ 1 buzuq
  ⏭ 2 o'tkazib yuborilgan (06:30 — 12-kamera, 18:00 — 7-kamera)
Ombor: 84 MB (jami 6,2 GB) · Zaxira: ✅ 03:40
⚠ 12-kamera 3 kundan beri qorong'i kadr beryapti — IR yoritgichni tekshiring
```

⚠ Bu **yagona xabar** kunlik holatning 90% ini beradi. To'g'ri sozlangan tizimda **alert kamdan-kam keladi va aynan shu narsa uni ishonchli qiladi**.

**Ishonch:** Telegram raqamlari **HIGH** (rasmiy FAQ) · guruhlash siyosati **MEDIUM** (loyihaga xos mulohaza, standart amaliyot bilan mos) · chegara qiymatlari **LOW** (pilotda sozlanadi).

---
## Standard Stack

### Yangi paketlar — `services/core-api/pyproject.toml`

| Paket | Versiya | Litsenziya | Maqsad | Ishonch |
|---|---|---|---|---|
| **`aiobotocore`** | **3.9.0** (2026-08-01) | Apache-2.0 | SeaweedFS S3 API (async `put_object`/`get_object`/`head_object`/`delete_objects`) | HIGH — PyPI metadata + slopcheck `[OK]` |
| **`Pillow`** | **12.3.0** (2026-07-01) | MIT-CMU | Sifat metrikalari (`ImageStat`) **va** retention siqishi | HIGH — mahalliy tekshirildi (12.2.0 da) |

⚠ **`aioboto3` QO'SHILMAYDI** — sabab §D.9.2 (empirik tasdiqlandi, pastdagi audit jadvali).
⚠ **`opencv-python-headless` QO'SHILMAYDI** — §C.7. U `cv-service` ning bog'liqligi va u 5-fazada tug'iladi.
⚠ **`aiogram` QO'SHILMAYDI** — §E.12. Telegram alerti `httpx` bilan.

### Allaqachon mavjud va QAYTA ISHLATILADI (yangi paket kerak emas)

| Paket | Bu fazada nima uchun |
|---|---|
| `taskiq` 0.12.4 + `taskiq-redis` 1.2.3 | Tick, `capture_batch`, `retention.daily`, `alert_sweep`. **Planer allaqachon paketda** — `taskiq scheduler` CLI |
| `httpx` 0.28.1 | go2rtc `/api/frame.jpeg`, ISAPI `/picture`, Telegram `sendMessage` |
| `tenacity` 9.1.4 | Urinish ichidagi retry (§B.4) |
| `structlog` 26.1.0 + `asgi-correlation-id` 5.0.1 | Job jurnallari (`market_id`, `camera_id`, `run_id` bog'lanadi) |
| `sentry-sdk[fastapi]` 2.66.1 | Istisnolar; `before_send` maskalash **allaqachon** o'rnatilgan |
| `sqlalchemy` 2.0.51 + `alembic` 1.18.5 + `alembic-utils` 0.8.8 | Sxema, RLS siyosatlari, `EXCLUDE` konstraytlari |
| `cryptography` 49.0.0 | NVR paroli (3-fazadan; kadr olish yo'li uni qayta ishlatadi) |
| `tzdata` 2026.3 | `ZoneInfo("Asia/Tashkent")` |
| `aiohttp` (tranzitiv, `taskiq` orqali) | `aiobotocore` ning transporti — **yangi HTTP steki emas** [VERIFIED: `taskiq` `requires_dist`: `aiohttp>=3`] |

### Yangi konteyner image'lari

| Image | Teg | Litsenziya | Maqsad |
|---|---|---|---|
| `chrislusf/seaweedfs` | **4.40** | Apache-2.0 | S3-mos obyekt-ombor [VERIFIED: Docker Hub API, 2026-07-20] |

⚠ `scheduler` — **yangi image emas**: `services/core-api/Dockerfile` `target: runtime`, boshqa `command` (`taskiq scheduler app.worker:scheduler`). `worker`/`migrate`/`tests` bilan aynan bir xil naqsh.

### Alternatives Considered

| O'rniga | Muqobil | Qachon muqobil to'g'ri |
|---|---|---|
| `aiobotocore` | `boto3` + `asyncio.to_thread` | `aiobotocore` API'si noqulay bo'lsa yoki `botocore` pini muammo tug'dirsa. Kunlik ~175 chaqiruv uchun ip narxi ahamiyatsiz — **kuchli zaxira** |
| `aiobotocore` | `aioboto3` | ❌ Hech qachon — §D.9.2 |
| `Pillow` | `opencv-python-headless` | 5-fazada `cv-service` tug'ilganda sifat filtri u yerga ko'chirilishi mumkin. **Bu fazada yo'q** |
| `taskiq scheduler` + DB | Faqat `taskiq` cron | ❌ §A.2 — CAM-05 ni buzadi |
| `taskiq scheduler` + DB | Faqat DB (planer jarayonisiz) | ⚠ Taymerni hand-roll qilish; `core-api` ning event loop'ini bloklaydi |
| SeaweedFS | Garage | ❌ AGPL-3.0 (CLAUDE.md taqiqi) |
| SeaweedFS | Oddiy fayl tizimi + FastAPI | ⚠ 175 fayl/kun uchun texnik jihatdan yetarli, lekin S3 abstraksiyasi yo'qoladi va O'zbekiston hostingiga ko'chish qimmatlashadi |
| Telegram `httpx` | `aiogram` | 7-fazada `bot-service` tug'ilganda alertlar unga **ko'chirilishi mumkin** (bir joyda outbox, BOT-04). Bu fazada emas |

---

## Package Legitimacy Audit

`slopcheck 0.6.1` bilan tekshirildi (2026-08-04, `slopcheck install -e pypi ...`):

| Paket | Reyestr | Yoshi | Litsenziya | Manba repo | slopcheck | Qaror |
|---|---|---|---|---|---|---|
| `aiobotocore` | PyPI | 3.9.0 — **2026-08-01** | Apache-2.0 | `aio-libs/aiobotocore` (1 421 ★, push 2026-08-03) | **[OK]** | ✅ **Qabul qilindi** |
| `pillow` | PyPI | 12.3.0 — 2026-07-01 | MIT-CMU | `python-pillow/Pillow` | **[OK]** | ✅ **Qabul qilindi** |
| `boto3` | PyPI | 1.43.62 — 2026-07-31 | Apache-2.0 | `boto/boto3` (9 869 ★) | **[OK]** | ⚠ **Zaxira variant** (§D.9.2 B) |
| `aioboto3` | PyPI | 15.5.0 — **2025-10-30** | Apache-2.0 | `terricain/aioboto3` (1 003 ★, push **2025-12-15**) | **[OK]** | ❌ **RAD ETILDI** — slop emas, **eskirgan + qattiq `==` pin** |

**`[SLOP]` verdikti olgan paket:** yo'q.
**`[SUS]` verdikti olgan paket:** yo'q.

### ⚠ `aioboto3` — EMPIRIK tasdiqlangan pasaytirish (`arq` epizodining takrori)

`slopcheck install -e pypi aiobotocore pillow boto3 aioboto3` chiqishi (2026-08-04):

```
Collecting aiobotocore
  Downloading aiobotocore-3.9.0-py3-none-any.whl.metadata      <- avval 3.9.0 tanlandi
  Downloading aiobotocore-2.25.1-py3-none-any.whl.metadata     <- `aioboto3` uni 2.25.1 GA TUSHIRDI
Collecting botocore<1.40.62,>=1.40.46 (from aiobotocore)
Collecting boto3
  Downloading boto3-1.40.61-py3-none-any.whl                   <- boto3 1.43.62 -> 1.40.61
```

Ya'ni `aioboto3` ni qo'shish `aiobotocore` ni **bitta major orqaga**, `boto3` ni **uch minor orqaga** tortadi. Bu `arq` ning `redis` ni 8.0.0 dan 5.3.1 ga tushirishi bilan **aynan bir xil sinf** va u **kuzatilgan**, taxmin qilingan emas.

**CLAUDE.md TUZATILISHI KERAK:** «`boto3` / `aioboto3` 1.43.57 / 15.5.0» qatori bajarilmaydigan kombinatsiya. To'g'ri yozuv: **`aiobotocore==3.9.0`** (yoki `boto3` yakka holda).

---

## Don't Hand-Roll

| Muammo | Qurmang | O'rniga | Nima uchun |
|---|---|---|---|
| Davriy ishga tushirish (taymer) | `while True: sleep(60)` tsikli | `taskiq scheduler` (paketda **bor**) | Tsikl o'lganda konteyner **sog'lom** bo'lib qolaveradi; qayta ishga tushirish semantikasi, signal ishlovi, `asyncio` bekor qilinishi — hammasi qaytadan yoziladi |
| Ish navbatini tanlash/qulflash | Xotiradagi `set` yoki fayl qulfi | Postgres `SELECT … FOR UPDATE SKIP LOCKED` | O'nlab yillik, tranzaksiyaga qadalgan semantika. Xotiradagi qulf ikkinchi worker'da mavjud emas |
| S3 imzolash (SigV4) | `hmac` + kanonik so'rov qurish | `aiobotocore` / `boto3` | Kanonizatsiya, sana oynasi, chunked imzolash, retry — xavfsizlikka tegishli va nozik. Qo'lda yozilgan imzo **jimgina noto'g'ri** bo'lishi mumkin |
| JPEG dekodlash / buzuqlikni aniqlash | Bayt-daraja JPEG parseri | `Pillow` (`Image.load()`) | Kesilgan fayl, noto'g'ri Huffman jadvali, progressive skan — hammasi allaqachon hal qilingan va u `OSError` bilan chiqadi |
| Yorug'lik/kontrast statistikasi | Piksel bo'yicha `for` tsikli | `PIL.ImageStat.Stat` | C darajasida bajariladi; Python tsikli 1280×720 uchun ~1 s, `ImageStat` ~2 ms |
| JPEG kichraytirilgan dekod | To'liq dekod + `resize` | `Image.draft("L", size)` | DCT darajasida kichraytirish — bir necha barobar tez |
| Mintaqa/biznes-kun hisobi | `datetime.now()` + qo'lda offset | `sbozor_core.timeutil` + DB generated column | 1-faza qarori; ikkita haqiqat manbai yarim tunda bir kun farq qiladi |
| Davr kesishmasligi | `SELECT … WHERE period && …` tekshiruvi | `EXCLUDE USING gist` | Ilova tekshiruvi **poyga sharoitida** ikkita kesishuvchi profilni o'tkazib yuboradi |
| Retry siyosati | Qo'lda `for attempt in range(3)` | `tenacity` (paketda bor) + `capture_runs.attempts` | Eksponensial kutish, jitter, predikat bo'yicha filtrlash |
| Telegram xabar navbati | Qo'lda `sleep(1)` | Guruhlash + `alert_events` debounce (§E.13) | ⚠ To'liq outbox 7-fazada (BOT-04) — bu yerda uni **oldindan qurmang** |
| Alert holati mashinasi | `dict` da «oxirgi qachon yubordim» | `alert_events` jadvali + qisman UNIQUE indeks | Xotiradagi holat qayta ishga tushishdan omon qolmaydi — §A.2 ning aynan takrori |

**Asosiy fikr:** bu fazada hand-roll qilish xavfi **kutubxona yo'qligidan emas, mavjudini ko'rmaslikdan** keladi. `taskiq` planeri, `Pillow` statistikasi va Postgres `SKIP LOCKED` — uchalasi ham **allaqachon qo'lda**, ularni qayta yozish esa yashil test bilan yashiringan nosozliklar tug'diradi.

---

## Common Pitfalls

### Pitfall 1: «Cron qo'ydim, demak ishlaydi» (VERIFIED — manba o'qildi)
**Nima noto'g'ri ketadi:** Har slot uchun `taskiq` cron'i qo'yiladi va u haqiqatan ishlaydi — **planer tirik bo'lganda**. Deploy paytidagi 40 soniyalik uzilish 06:00 slotini yo'q qiladi va **hech qanday iz qolmaydi**.
**Sabab:** `SchedulerLoop.cron_tasks_last_run` — oddiy `dict`, jarayon xotirasida.
**Oldini olish:** Reja **Postgres'da materializatsiya qilinadi**; cron faqat holatsiz tick uchun ishlatiladi.
**Erta belgi:** «O'tkazib yuborilgan slot» uchun test yozib bo'lmayapti — chunki o'tkazib yuborilgan slot **hech qanday obyekt qoldirmaydi**.

### Pitfall 2: `aioboto3` ni CLAUDE.md aytgani uchun o'rnatish (VERIFIED — empirik)
**Nima noto'g'ri ketadi:** `aioboto3 15.5.0` `aiobotocore` ni 3.9.0 dan 2.25.1 ga, `boto3` ni 1.43.62 dan 1.40.61 ga **tushiradi**.
**Sabab:** `aiobotocore[boto3]==2.25.1` — qattiq `==` pin; `aioboto3` ning oxirgi relizi 2025-10-30.
**Oldini olish:** `aiobotocore==3.9.0` to'g'ridan-to'g'ri (past darajali klient bizga yetadi).
**Erta belgi:** `pip install` chiqishida bir xil paketning **ikkita metadata** yuklab olinishi (backtracking).

### Pitfall 3: `business_date` ni `captured_at` dan hisoblash
**Nima noto'g'ri ketadi:** Admin 23:55 slotini qo'shadi; kadr 00:01 da olinadi; `snapshots.business_date` **ertangi kun** bo'ladi, `capture_runs.business_date` esa **bugungi** → kadr noto'g'ri kunga fayllanadi va 6-fazada hisob boshqa kunga tushadi.
**Sabab:** Ikki jadvalda ikkita mustaqil hisoblash manbai.
**Oldini olish:** `snapshots.scheduled_at` **nusxalanadi** va `business_date` **undan** hisoblanadi — ikkalasi konstruksiya bo'yicha mos.
**Erta belgi:** Yo'q — bu xato faqat yarim tunga yaqin slot qo'shilganda va **oylar keyin** chiqadi. Shuning uchun invariant testi kerak: `snapshots.business_date = capture_runs.business_date` (har doim).

### Pitfall 4: Baza qatorini obyektdan OLDIN yozish
**Nima noto'g'ri ketadi:** `snapshots` qatori yoziladi, keyin S3 `PUT` yiqiladi → 6-fazadagi dalil havolasi **mavjud bo'lmagan** obyektga ishora qiladi.
**Sabab:** «Avval metama'lumot, keyin bayt» — intuitiv, lekin teskari.
**Oldini olish:** Tartib qat'iy: kadr → sifat → **S3 PUT** → baza. Qator obyekt **borligini tasdiqlaydi**.
**Erta belgi:** «Yetim qator» ni tuzatish uchun kompensatsiya kodi yozila boshlanishi.

### Pitfall 5: `s3.json` ni rasmiy misoldan nusxalash
**Nima noto'g'ri ketadi:** SeaweedFS ning misol `s3.json` fayli `{"name": "anonymous", "actions": ["Read"]}` bilan boshlanadi → **butun dalil arxivi autentifikatsiyasiz o'qiladi**.
**Sabab:** Misol fayl s3-tests to'plami uchun yozilgan, ishlab chiqarish uchun emas.
**Oldini olish:** `anonymous` yozuvi **umuman bo'lmaydi**; faqat bitta identity, bucketga qadalgan `Action:bucket` bilan.
**Erta belgi:** Konfiguratsiya faylida `anonymous` so'zi — darvoza testi uni grep bilan tutadi.

### Pitfall 6: Qorong'ilikni FAQAT o'rtacha yorug'lik bilan aniqlash
**Nima noto'g'ri ketadi:** Qishki 06:00 tong kadri `mean≈30` beradi va `mean < 40` qoidasi uni rad etadi → **oylab qonuniy ertalabki kadrlar tashlab yuboriladi**, ya'ni kunlik hisob asosi yo'qoladi.
**Sabab:** «Qorong'i» va «axborotsiz» — **turli** narsalar.
**Oldini olish:** `dark := mean < DARK_MEAN VA stddev < DARK_STDDEV`. Tuzilma bo'lgan qorong'i kadr — **yaroqli**.
**Erta belgi:** `quality_verdict='dark'` ulushining tong slotlarida keskin oshishi (kunlik dayjest buni ko'rsatadi).

### Pitfall 7: `ImageFile.LOAD_TRUNCATED_IMAGES = True` (biror joyda)
**Nima noto'g'ri ketadi:** Kesilgan JPEG **jimgina** dekod bo'ladi (qolgan qismi kulrang) → buzuq detektori **butunlay o'chadi** va hech qanday test qizarmaydi.
**Sabab:** Bu **global** bayroq; uni har qanday kutubxona yoki fayl o'rnatishi mumkin.
**Oldini olish:** `test_truncated_images_flag_is_false` — import qatlamida tekshiradi.
**Erta belgi:** Yo'q. Aynan shuning uchun test kerak.

### Pitfall 8: `/api/frame.jpeg?cache=` ni ishlatish
**Nima noto'g'ri ketadi:** go2rtc keshlangan kadrni qaytaradi → «bu kadr 06:30 da olingan» da'vosi **yolg'on** bo'ladi va dalil zanjiri buziladi.
**Sabab:** Parametr «tezlashtirish» sifatida jozibali ko'rinadi.
**Oldini olish:** `cache` **hech qachon** berilmaydi. Darvoza: klientda so'rov parametrlari allow-list.
**Erta belgi:** Ketma-ket slotlarda **bir xil `etag`/`size_bytes`**.

### Pitfall 9: Tick tenant kontekstisiz (3-fazadagi Pitfall 13 ning takrori)
**Nima noto'g'ri ketadi:** Materializatsiya 0 qator yozadi, `claim_due()` 0 qator qaytaradi, **hech qanday xato yo'q** → tizim «bugun ish yo'q» deb jim turadi.
**Sabab:** RLS kontekstsiz `SELECT` uchun fail-closed, lekin **istisnosiz**.
**Oldini olish:** `_system_transaction()` naqshi (3-fazadan) + `test_capture_tick_sets_tenant_context`.
**Erta belgi:** Yo'q — bu **eng jim** xato sinfi.

### Pitfall 10: Yangi bozorning birinchi kunidagi soxta `missed` alertlari
**Nima noto'g'ri ketadi:** Bozor 12:00 da faollashtiriladi, materializatsiya 06:00–08:00 slotlarini `pending` qilib yozadi, watchdog ularni darhol `missed` qiladi → **5 ta alert birinchi daqiqada**.
**Sabab:** Materializatsiya o'tmishdagi slotlarni hozirgi slotlardan ajratmagan.
**Oldini olish:** Materializatsiya paytida `scheduled_at + grace < now()` bo'lgan qatorlar `skipped` (`capture_plan_created_late`) holatida tug'iladi va **alert bermaydi**.
**Erta belgi:** Birinchi onboarding demosida alert oqimi.

### Pitfall 11: `401` da tickning qayta urinishi (3-faza D-03 ning kuchaytirilgan shakli)
**Nima noto'g'ri ketadi:** NVR paroli o'zgardi. Tick har daqiqada 25 kamera uchun qayta urinadi → 10 daqiqada **250 muvaffaqiyatsiz autentifikatsiya** → Hikvision hisobni 30 daqiqaga qulflaydi va **to'g'ri parol ham ishlamaydi**.
**Sabab:** Job darajasidagi retry `AUTH_LOCKING_CODES` ni hurmat qilmagan.
**Oldini olish:** `AUTH_LOCKING_CODES` da qator **darhol `failed`** va `attempts = max_attempts`.
**Erta belgi:** `nvr_bad_credentials` dan keyin `nvr_account_locked` ga o'tish.

### Pitfall 12: `retention.daily` cron'ini `cron_offset` siz qo'yish
**Nima noto'g'ri ketadi:** `"20 3 * * *"` UTC'da baholanadi → Toshkentda **08:20**, ya'ni ertalabki kadr olish cho'qqisining o'rtasida disk I/O va CPU raqobati.
**Sabab:** `taskiq` cron'ni UTC'da baholaydi (VERIFIED).
**Oldini olish:** `cron_offset="Asia/Tashkent"` **har bir** cron jadvalida.
**Erta belgi:** 08:00 slotining muntazam sekinlashishi.

### Pitfall 13: Ikki marta siqish
**Nima noto'g'ri ketadi:** Retention jobi `storage_tier` filtrisiz ishlaydi → har kuni bir xil kadr qayta kodlanadi → **avlod yo'qotishi** to'planadi va dalil bir yildan keyin o'qib bo'lmas holga keladi.
**Oldini olish:** `WHERE storage_tier = 'full'` — bir yo'nalishli holat o'tishi.
**Erta belgi:** `size_bytes` ning har kuni kamayib borishi.

### Pitfall 14: Heartbeat'ni konteyner `healthcheck` iga ulash
**Nima noto'g'ri ketadi:** Worker heartbeat'i eskirgani uchun `core-api` **`unhealthy`** bo'ladi va Docker uni qayta ishga tushiradi → sog'lom API uzilib turadi, muammo esa boshqa konteynerda.
**Oldini olish:** Alohida `/internal/self-check`; konteyner healthcheck'i **tegilmaydi**.

### Pitfall 15: Alertga kadr rasmini biriktirish
**Nima noto'g'ri ketadi:** «Dalil bilan alert» jozibali ko'rinadi → dalil-kadr **Telegram serverlariga** yuklanadi. Bu bozor tashrifchilari tasvirlari, ya'ni **shaxsiy ma'lumot**, va u O'zR data-rezidentlik doirasidan **chiqib ketadi**.
**Oldini olish:** Alertlarda **faqat matn va raqamlar**. Kadr — panelga havola (avtorizatsiya ortida).
**Erta belgi:** `sendPhoto` chaqiruvi kodda paydo bo'lishi — darvoza testi uni taqiqlaydi.

---

## Environment Availability

| Bog'liqlik | Kim talab qiladi | Mavjud | Versiya | Zaxira |
|---|---|---|---|---|
| Docker | Butun stek | ✅ | **29.4.2** | — |
| Docker Compose | Orkestratsiya | ✅ | **v5.1.3** | — |
| Node.js | Frontend + skriptlar | ✅ | **24.14.1** | — |
| Python (xost) | Yordamchi skriptlar | ✅ | 3.14.3 | Konteynerda 3.13 |
| `chrislusf/seaweedfs:4.40` | CAM-07 | ⚠ **Yuklab olinmagan** | — | Yo'q — `docker pull` birinchi ishga tushishda |
| `uv` (xost) | Bog'liqlik boshqaruvi | ❌ | — | ✅ Konteyner ichida (`Dockerfile`) — xostda kerak emas |
| `ffmpeg` (xost) | — | ❌ | — | ✅ Kerak emas: `mediamtx:1.19.3-ffmpeg` image'ida bor, `ffmpeg` kadr olish yo'li esa **oxirgi chora** va u ham konteyner ichida |
| Telegram bot token | FOUND-06 | ⚠ **Yo'q** | — | ✅ Bo'sh token = alertlar o'chiq + `log.warning`. **Fazani bloklamaydi** (testlar `respx` bilan) |
| Real Hikvision NVR | Real o'lchov | ❌ | — | ✅ `--profile sim` + `hardware` markeri (3-fazadan) |
| Real Karmana kadrlari | Sifat chegaralari | ❌ | — | ✅ Sintetik kadrlar (`Pillow`) + sozlanadigan chegaralar |

**Zaxirasiz bloklovchi yetishmovchilik:** **yo'q**.

---

## Validation Architecture

### Test Framework

| Xususiyat | Qiymat |
|---|---|
| Framework | `pytest 9.1.1` + `pytest-asyncio 1.4.0` (`asyncio_mode = "auto"`) + `testcontainers 4.15.0` |
| Konfiguratsiya | `pyproject.toml` (repo ildizi) — `[tool.pytest.ini_options]` |
| Markerlar | `tenancy`, `sim`, `hardware`, `slow` — **yangi marker kerak emas** |
| Standart filtr | `-m "not hardware"` (`addopts` da) |
| Tez yugurish | `npm run test:fast` → `pytest tests/unit -x -q` |
| To'liq to'plam | `npm run test` → `pytest -q` |
| Sim to'plami | `npm run test:sim` → `pytest tests/integration -m "sim and not slow" -x -q` |
| Faza darvozasi | `npm run gate` |

### Faza mezonlari → test xaritasi

| SC | Xulq | Test turi | Buyruq | Fayl bormi |
|---|---|---|---|---|
| **SC#1** Admin jadvalni sozlaydi, ertasi kuni aynan o'sha slotlarda kadr paydo bo'ladi | Jadval → materializatsiya → kadr | integration `sim` | `pytest tests/integration/test_phase4_criteria.py::test_sc1_schedule_produces_slots -x` | ❌ Wave 0 |
| **SC#2** Uzilish/takror — dublikat yo'q, retry bor, o'tkazib yuborilgan slot ko'rinadi | Idempotentlik + watchdog | integration | `pytest tests/integration/test_capture_tick.py -x` | ❌ Wave 0 |
| **SC#3** Qorong'i/buzuq/bo'sh belgilanadi, `light_mode` saqlanadi, billing'ga ta'sir qilmaydi | Sifat filtri + FK ilgagi | unit + integration | `pytest tests/unit/test_quality_filter.py tests/integration/test_snapshot_quality.py -x` | ❌ Wave 0 |
| **SC#4** S3'da bozor/kamera/sana bo'yicha topiladi; 90 kun → siqilgan siyosat ishlaydi | Kalit tartibi + retention | integration `sim` | `pytest tests/integration/test_storage_layout.py tests/integration/test_retention.py -x` | ❌ Wave 0 |
| **SC#5** Kamera offline / slot o'tkazib yuborilgan / backup xato → Telegram + Sentry | Alert (respx mock) | integration | `pytest tests/integration/test_alerting.py -x` | ❌ Wave 0 |

### Talab → test xaritasi

| REQ | Xulq | Test | Buyruq |
|---|---|---|---|
| CAM-04 | Mavsumiy profil kesishmaydi; standart 7 slot; bo'shliq ko'rinadi | integration | `pytest tests/integration/test_capture_schedule.py -x` |
| CAM-04 | Slot → `business_date` (Toshkent) to'g'ri | integration | `pytest tests/integration/test_capture_schedule.py::test_business_date_binding -x` |
| CAM-05 | `UNIQUE` dublikatni to'sadi; ikkinchi tick hech nima olmaydi | integration | `pytest tests/integration/test_capture_tick.py::test_duplicate_tick_is_noop -x` |
| CAM-05 | Lease tugaganda qator qaytadi | integration | `pytest tests/integration/test_capture_tick.py::test_expired_lease_returns_to_pending -x` |
| CAM-05 | `grace` dan chiqqan slot `missed`, bajarilMAYDI | integration | `pytest tests/integration/test_capture_tick.py::test_overdue_slot_is_missed_not_executed -x` |
| CAM-06 | Sintetik qora/kulrang/kesilgan kadr → to'g'ri verdikt | **unit** | `pytest tests/unit/test_quality_filter.py -x` |
| CAM-06 | Yaroqsiz kadrga bandlik hodisasini bog'lab bo'lmaydi | integration | `pytest tests/integration/test_snapshot_quality.py::test_non_billable_cannot_be_referenced -x` |
| CAM-07 | Kalit shakli va prefiks bo'yicha topish | integration `sim` | `pytest tests/integration/test_storage_layout.py -x` |
| CAM-07 | `retention_full_days=0` → siqiladi, o'lchamlar saqlanadi | integration `sim` | `pytest tests/integration/test_retention.py -x` |
| FOUND-06 | `missed` → guruhlangan bitta xabar (75 ta emas) | integration | `pytest tests/integration/test_alerting.py::test_missed_slots_are_grouped -x` |
| FOUND-06 | Backup heartbeat eskirsa alert (backup **yozilmagan** bo'lsa ham) | integration | `pytest tests/integration/test_alerting.py::test_stale_heartbeat_alerts -x` |
| FOUND-06 | Telegram yiqilsa kadr olish **davom etadi** | integration | `pytest tests/integration/test_alerting.py::test_telegram_failure_does_not_block_capture -x` |

### Simulyator ustida NIMA isbotlanadi (F.14 ning javobi)

Joriy sim **faqat** `testsrc2` rangli test-namunasini beradi — ya'ni **qorong'i ham, bo'sh ham, buzuq ham kadr bera olmaydi**. Uchta qo'shimcha kerak va ular Wave 0 ga kiradi:

| Ehtiyoj | Yechim | Fayl |
|---|---|---|
| **Qorong'i / bo'sh** kadr | `mediamtx.yml` ga sifat-ssenariy yo'llari: `color=c=black`, `color=c=gray`, past kontrastli manba — **kanal raqami bo'yicha** tanlanadi (masalan 90–99) | `ops/mediamtx/mediamtx.yml` |
| **Buzuq** kadr | MediaMTX **yaroqli** oqim beradi, ya'ni buzuqlikni u yerdan olib bo'lmaydi. Yechim: `nvr-sim` ning `/ISAPI/Streaming/channels/{ch}/picture` endpointi + `POST /__sim__/state {"frame_mode": "truncated"}` — sim **baytlarni o'zi boshqaradi** | `services/nvr-sim/` |
| **Chegara qiymatlari** | Sintetik JPEG generatori (`Pillow`): berilgan `mean`/`stddev` bilan kadr yasaydi | `tests/fixtures/frames.py` |

> ⚠ **«Simulyator o'zini o'zi tasdiqlaydi» antinaqshi (3-fazadan meros).** Sim kadrni **fizik xususiyat** bilan yasashi kerak («o'rtacha yorug'ligi 8 bo'lgan kadr»), **detektorning chegarasi bilan emas** («detektor rad etadigan kadr»). Ikkinchisi hech nimani isbotlamaydi — u chegarani o'ziga o'zi tekshiradi. Fixture nomlari ham shunga mos: `frame_mean_8_stddev_2`, `frame_rejected_by_filter` **emas**.

### Uskunasiz / vaqtsiz nima isbotlanMAYDI

| Da'vo | Nima uchun isbotlanmaydi | Qanday boshqariladi |
|---|---|---|
| Real NVR sessiya chegarasi | Sim chegarani modellamaydi (03-VERIFICATION) | `hardware` markeri; `max_concurrent_captures=1` **ishlaydigan zaxira** (§B.6) |
| Real kadr o'lchami va sifat taqsimoti | Real kamera yo'q | `size_bytes`/`quality_*` **saqlanadi** → Phase 0 ma'lumoti kelganda so'rov bilan hisoblanadi |
| 90 kunlik retention **haqiqiy vaqtda** | Kutib bo'lmaydi | Chegara — parametr; sana in'ektsiya qilinadi (§D.10) |
| Telegram haqiqatda yetkazdimi | Token yo'q, tashqi xizmat | `respx` bilan HTTP kontrakti; **bitta qo'lda UAT bandi** |
| Tunnel ortidagi haqiqiy kechikish | WireGuard CI'da yo'q (CAM-02 bloklangan) | `hardware` markeri; byudjet hisobi (§B.6) |
| Disk 1 yildan keyin | Vaqt | Arifmetika (§D.11) + `avg(size_bytes)` monitoringi |

### Sampling Rate

- **Har task commitida:** `npm run test:fast` (`tests/unit`)
- **Har to'lqin merge'ida:** `npm run test` + `npm run test:sim`
- **Faza darvozasi:** `npm run gate` to'liq yashil + `tests/integration/test_phase4_criteria.py` beshala mezoni

### Wave 0 Gaps

- [ ] `tests/fixtures/frames.py` — sintetik JPEG generatori (mean/stddev/to'yinganlik bo'yicha)
- [ ] `tests/unit/test_quality_filter.py` — CAM-06 chegaralari va `LOAD_TRUNCATED_IMAGES` darvozasi
- [ ] `tests/unit/test_object_key.py` — deterministik kalit va uning barqarorligi
- [ ] `tests/integration/test_capture_schedule.py` — CAM-04
- [ ] `tests/integration/test_capture_tick.py` — CAM-05 (idempotentlik, lease, grace)
- [ ] `tests/integration/test_snapshot_quality.py` — CAM-06 ning DB kafolati
- [ ] `tests/integration/test_storage_layout.py` — CAM-07 kalit tartibi (`sim`)
- [ ] `tests/integration/test_retention.py` — CAM-07 siqish (`sim`)
- [ ] `tests/integration/test_alerting.py` — FOUND-06 (`respx`)
- [ ] `tests/integration/test_phase4_criteria.py` — beshala mezonning yagona darvozasi
- [ ] `ops/mediamtx/mediamtx.yml` — sifat-ssenariy yo'llari
- [ ] `services/nvr-sim/` — `/picture` endpointi + `frame_mode` holati
- [ ] `ops/seaweedfs/s3.json.example` + `compose.yaml` da `storage` xizmati
- [ ] `compose.yaml` da `scheduler` xizmati (`taskiq scheduler`)
- [ ] `sbozor_core.schema_contract.AUDITED_TABLES` ga `snapshot_schedules`, `snapshot_schedule_slots`
- [ ] `tests/tenancy/test_meta.py` — `markets.timezone` invarianti (§A.3)
- [ ] ⚠ **`is_billable` GENERATED ustunining `UNIQUE` ga kirishini O'LCHASH** (§C.8, OQ-4) — birinchi migratsiyadan **oldin**

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1` (`.planning/config.json`).

### Qo'llanadigan ASVS toifalari

| ASVS toifasi | Qo'llanadimi | Standart nazorat |
|---|---|---|
| **V2 Authentication** | Qisman | Yangi foydalanuvchi yo'li yo'q. NVR rekviziti — 3-fazadan (Fernet) |
| **V3 Session Management** | Yo'q | Yangi sessiya yuzasi yo'q |
| **V4 Access Control** | **Ha** | Jadval boshqaruvi — `CAMERA_MANAGE` (3-fazadan **mavjud**). Yangi huquq **qo'shilmaydi**: jadval kameraning davomi va u bir xil persona. ⚠ `PLATFORM_ADMIN` da `CAMERA_MANAGE` borligi 3-fazada tuzatilgan — **tekshiriladi, taxmin qilinmaydi** |
| **V5 Input Validation** | **Ha** | Slot vaqtlari (`time` tipi), `daterange` (`EXCLUDE`), retention parametrlari (`Settings` chegaralari), **JPEG baytlari** (magic + o'lcham + `MAX_IMAGE_PIXELS`) |
| **V6 Cryptography** | **Ha** | `cryptography` Fernet (3-fazadan). S3 maxfiy kaliti va Telegram tokeni — `SecretStr` + `censor_secrets`. **Qo'lda SigV4 imzolash TAQIQ** |
| **V7 Error Handling & Logging** | **Ha** | `error_detail jsonb` — `mask_sensitive` dan o'tadi (3-faza naqshi); `structlog` ga xom javob tanasi yozilmaydi |
| **V12 Files & Resources** | **Ha** | Dekompressiya bombasi (`MAX_IMAGE_PIXELS`), yuklab olish o'lchami chegarasi, deterministik obyekt kaliti (foydalanuvchi kiritmasidan qurilmaydi) |
| **V13 API** | Qisman | Yangi endpointlar: jadval CRUD, `/internal/self-check` |
| **V14 Configuration** | **Ha** | `s3.json` — `anonymous` yo'q; `ports:` publish qilinmaydi; sirlar `.env` da |

### Ma'lum tahdid naqshlari (FastAPI + SeaweedFS + go2rtc + Telegram)

| Naqsh | STRIDE | Standart yumshatish |
|---|---|---|
| **Anonim S3 o'qish** (misol `s3.json` dan) | Information Disclosure | `anonymous` identity **yo'q**; `Action:bucket` bilan chegaralangan; port publish qilinmaydi (Pitfall 5) |
| **Obyekt kalitida yo'l chiqishi** (`../`) | Tampering | Kalit **faqat** UUID + ISO sana + `HHMM` dan quriladi — foydalanuvchi matni **umuman yo'q**. Darvoza: kalit generatorining unit testi |
| **Dekompressiya bombasi** (buzilgan NVR) | DoS | `Image.MAX_IMAGE_PIXELS` aniq o'rnatiladi; `MAX_BYTES` chegarasi dekoddan **oldin** |
| **JPEG o'rniga HTML xato sahifasi** | Tampering | Magic-bayt darvozasi `Content-Type` ga ishonmaydi (§C.7) |
| **go2rtc `src` orqali RCE** (GHSA-wwww-5h25-jf98) | Elevation of Privilege | 3-fazadan meros: `assert_safe_go2rtc_src` allow-listi, nginx bloki, port publish qilinmasligi — **uchala qatlam saqlanadi** |
| **Rekvizitning jurnalga sizishi** | Information Disclosure | 3-fazadan meros: `SecretStr`, `_failure()` da URL interpolatsiyasi yo'q, Sentry `before_send` + `stacktrace.frames[].vars` maskalash |
| **Alert kanali orqali ma'lumot chiqishi** | Information Disclosure | ⚠ **YANGI VA MUHIM:** alertga kadr **biriktirilmaydi** — dalil-kadr shaxsiy ma'lumot va Telegram serverlari O'zR data-rezidentlik doirasidan tashqarida. Faqat matn/raqam (Pitfall 15) |
| **Log injection** (`error_code`/`error_detail`) | Tampering | 3-faza qoidasi: rad etilgan qiymat xato matniga **yozilmaydi** |
| **Tenant chegarasining kesib o'tilishi** (tick) | Elevation of Privilege | `SECURITY DEFINER` yuzasi **faqat `market_id`**; har bozor uchun alohida tranzaksiya + `set_tenant_context` |
| **Bitta S3 rekviziti barcha bozorlarga** | Information Disclosure | ⚠ **Qabul qilingan xavf** — DB ishonch modeli bilan bir xil (`sbozor_app` GUC bilan istalgan bozorga qaray oladi). Kompensatsiya: `core-api` ga kirish nazorati, audit, va kalit rotatsiyasi hujjati |
| **`/internal/self-check` ning oshkor bo'lishi** | Information Disclosure | Javob **faqat** «eskirganmi» bayrog'ini beradi — bozor nomi, kamera soni yoki topologiya **yo'q**. nginx'da ichki tarmoq bilan chegaralanadi |

---

## Scope Fence — bu fazada QURILMAYDIGAN narsalar

| Narsa | Qaysi fazada | Nima uchun bu yerda emas |
|---|---|---|
| Kamera-zona poligonlari, `PolygonZone` | 5-faza (AI-01) | Kadr **kirish ma'lumoti**; zonalar uning ustidagi qatlam |
| RF-DETR, ONNX Runtime, `cv-service` | 5-faza (AI-02) | `cv-service` hali mavjud emas; sifat filtri **CV emas** |
| `occupancy_events` jadvali | 5-faza | 4-faza faqat **FK ilgagini** qo'yadi (`uq_snapshots_billable_anchor`) |
| Kunlik patta, `daily_charges` | 6-faza | Kadr — dalil, hisob emas |
| `bot-service`, sotuvchi/direktor botlari, outbox | 7-faza (BOT-01…04) | Alert `httpx` bilan; outbox 7-fazaning naqshi |
| Excel eksport | 8-faza (RECON-04) | — |
| **Zaxira nusxa va tiklash mashqi** | 8-faza (FOUND-07) | 4-faza faqat **heartbeat kontraktini** beradi (`system_heartbeats['backup']`) |
| WireGuard tunnelini isbotlash | Ops (CAM-02, `03-HUMAN-UAT.md` #1–#2) | 3-fazada bloklangan; 4-faza uni **ochmaydi va yopmaydi** |
| Kadr olishni NVR arxividan tiklash | v2 (V2-AI-03) | REQUIREMENTS.md da aniq v2 |
| Kamera siljishini aniqlash | v2 (V2-AI-01) | REQUIREMENTS.md da aniq v2 |
| To'liq interaktiv plan-xarita | v2 (V2-PROC-04) | — |

---

## Assumptions Log

| # | Da'vo | Bo'lim | Xato bo'lsa oqibati |
|---|---|---|---|
| **A1** | `is_billable` (GENERATED STORED) `UNIQUE (id, is_billable)` konstraytiga kira oladi va FK maqsadi bo'la oladi | §C.8 | 5-fazadagi strukturaviy kafolat trigger bilan almashtiriladi (~15 qator). **Wave 0 da o'lchanadi** |
| **A2** | Bir kadr ~500 KB (asosiy 4 MP) / ~40 KB (sub D1) | §D.11 | Disk prognozi ×2 gacha xato bo'lishi mumkin. `size_bytes` saqlangani uchun birinchi haftadayoq tuzatiladi |
| **A3** | Sovuq kadr ~4 s (RTSP handshake + keyframe) | §B.6 | 25 kamera ketma-ket 100 s emas, 250 s bo'lishi mumkin — **hamon `grace=600 s` ichida** |
| **A4** | Hikvision sub-oqimi D1 (704×576) atrofida | §B.6, §D.11 | Firmware'ga bog'liq; `capture_stream` sozlamasi buni yopadi |
| **A5** | `light_mode` = kameraning yorug'lik rejimi (talab matni ikki xil o'qiladi) | §C.8 | Superset qurilgani uchun ikkala o'qish ham qanoatlantiriladi |
| **A6** | Platforma admini alertlarni **guruhda** oladi (daqiqasiga 20 xabar chegarasi) | §E.13 | Shaxsiy chatda chegara yumshoqroq — guruhlash baribir kerak |
| **A7** | IR kadr HSV to'yinganligi < 0,05 | §C.8 | Kamera modeliga bog'liq; `quality_saturation` saqlangani uchun keyin qayta sozlanadi |
| **A8** | SeaweedFS `weed server -s3` bitta bozor yuki uchun yetarli (kuniga ~175 mayda obyekt) | §D.9 | Ko'p bozorda ham 1 750 obyekt/kun — SeaweedFS ning maqsadli holatidan ancha past |
| **A9** | `nvr-sim` ga `/picture` endpointini qo'shish arzon (~60 qator) | Validation | Qimmatroq bo'lsa buzuq kadr faqat unit qatlamda sinaladi |

---

## Open Questions (RESOLVED where possible)

### OQ-1 — `light_mode` aynan nimani anglatadi?
- **Bilamiz:** CAM-06 «`light_mode` saqlanadi» deydi, ta'rif bermaydi.
- **Noaniq:** Kameraning yorug'lik rejimimi yoki sifat yorlig'imi.
- **✅ Taklif qilingan standart:** **Superset** — `light_mode` enum (`day`/`low_light`/`ir_night`/`unknown`) **va** alohida `quality_verdict`. Narxi ~15 qator, 5 va 8-fazalarga aniq foyda. **Bloklamaydi.**

### OQ-2 — Kadr asosiy oqimdanmi yoki sub-oqimdanmi?
- **Bilamiz:** Jonli ko'rish — sub-oqim (3-faza). Kadr olish o'tkinchi, ya'ni bitreyt profili boshqa.
- **Noaniq:** Sub-oqim 5-fazaning aniqligiga yetadimi; asosiy oqim NVR chegarasiga uriladimi.
- **✅ Taklif qilingan standart:** `cameras.capture_stream` = **`'main'`**. `'sub'` — bitta sozlama bilan. Real kadrda Phase 0/pilotda o'lchanadi. **Bloklamaydi.**

### OQ-3 — Tashqi dead-man's switch v1 da bo'ladimi?
- **Bilamiz:** Ichki qatlamlar (watchdog + `/internal/self-check` + kunlik dayjest) VPS tirik bo'lganda yetarli.
- **Noaniq:** VPS butunlay o'lganda kim xabar qiladi.
- **✅ Taklif qilingan standart:** **Kod yozilmaydi**; `ops/docs/monitoring.md` ga bitta URL sozlash yo'riqnomasi (healthchecks.io/UptimeRobot) yoziladi va `03-HUMAN-UAT.md` uslubida ops bandi ochiladi. **Bloklamaydi.**

### OQ-4 — `GENERATED` ustun `UNIQUE`/FK maqsadi bo'la oladimi?
- **Bilamiz:** PG 12+ da STORED generated ustunlar indekslanadi.
- **Noaniq:** Bu loyihaning `postgres:18.4` versiyasida aynan shu DDL **bajarilmagan**.
- **✅ Taklif qilingan standart:** **Wave 0 da bitta migratsiya bilan o'lchanadi.** Yiqilsa — `BEFORE INSERT/UPDATE` trigger varianti (kafolat saqlanadi). **Bloklamaydi**, lekin **birinchi migratsiyadan oldin** hal qilinishi shart.

### OQ-5 — Yopiq kunlarda kadr olinadimi?
- **✅ Taklif qilingan standart:** **Ha** (`capture_on_closed_days` standarti `true`). Yopiq kundagi band rasta — aynan mahsulot izlaydigan anomaliya. Yiliga ~2 600 qo'shimcha kadr. **Bloklamaydi.**

### OQ-6 — «90 kun to'liq + 1 yil siqilgan» — jami 455 kunmi yoki 365 kunmi?
- **Bilamiz:** CAM-07: «90 kun to'liq, keyin siqilgan 1 yil (sozlanadigan)».
- **Noaniq:** «Keyin 1 yil» — 90+365 = 455 kunmi yoki jami 365 kunmi.
- **✅ Taklif qilingan standart:** **90 + 365 = 455 kun** (matnning to'g'ridan-to'g'ri o'qilishi). Ikkalasi ham `Settings` da, ya'ni buyurtmachi javobiga qarab **bitta qiymat** o'zgaradi. **Bloklamaydi.**

### OQ-7 — Kadr olishdan keyin go2rtc oqimi ro'yxatdan chiqariladimi?
- **Bilamiz:** go2rtc **yalqov** — tomoshabin bo'lmasa RTSP sessiyasini yopadi (03-RESEARCH D.14). Ro'yxatga olinganlik NVR'ga yuk bermaydi.
- **✅ Taklif qilingan standart:** **Chiqarilmaydi.** `ensure_stream()` idempotent va `remove_stream()` faqat kamera arxivlanganda. **Bloklamaydi.**

### OQ-8 — `capture_batch` bitta NVR uchunmi yoki bitta kamera uchunmi?
- **✅ Taklif qilingan standart:** **NVR + slot bo'yicha bitta vazifa.** Sabab: konkurentlik chegarasi **NVR ga** tegishli, ya'ni semafor bitta jarayonda bo'lishi kerak. Kamera bo'yicha vazifa `max_concurrent` ni taqsimlangan qulf talab qilardi. **Bloklamaydi.**

### OQ-9 — Jadval kun o'rtasida o'zgartirilsa bugungi rejaga ta'sir qiladimi?
- **Bilamiz:** SC#1 aniq yozgan: «**ertasi kuni** aynan o'sha slotlarda kadrlar paydo bo'ladi».
- **✅ Taklif qilingan standart:** **Yo'q.** Reja kunning birinchi tickida materializatsiya qilinadi va keyingi tahrirlar unga tegmaydi. UI «bugun: 7 slot · ertaga: 5 slot» ni ko'rsatadi. **Bloklamaydi.**

### OQ-10 — Snapshot jadvali ustaga (MARKET-01) qo'shiladimi?
- **Bilamiz:** MARKET-01 «…kameralar → kamera zonalari → snapshot jadvali» deydi; ROADMAP Phase 2 Note: «Ustaning kamera / kamera-zona / snapshot-jadval qadamlari 3–5 fazalarda ulanadi».
- **✅ Taklif qilingan standart:** **Ha, lekin standart qiymat bilan** — usta 7 ta standart slotli profil yozadi va admin **hech nima kiritmaydi**. Alohida tahrirlash sahifasi keyin. Self-service qoidasi shuni talab qiladi. **Bloklamaydi.**

---

## Sources

### Primary (HIGH — o'zim o'lchadim yoki rasmiy/manba kodi)

- **`taskiq 0.12.4` o'rnatilgan manbasi** (2026-08-04): `taskiq/cli/scheduler/run.py` (`run_scheduler`, `SchedulerLoop.run`, `is_cron_task_now`, `_mark_cron_tasks_as_already_run`), `taskiq/scheduler/scheduled_task.py`, `taskiq/schedule_sources/label_based.py` — planer jarayoni, xotiradagi cron holati, `cron_offset`, 1-daqiqali debounce
- **`taskiq_redis 1.2.3`** eksportlari va `RedisScheduleSource.__init__` imzosi
- **PyPI JSON API** (2026-08-04): `taskiq`, `taskiq-redis`, `aioboto3`, `aiobotocore` (2.25.1 va 3.9.0), `boto3`, `pillow`, `opencv-python-headless`, `numpy` — versiyalar, `requires_dist`, litsenziyalar, reliz sanalari
- **`slopcheck 0.6.1`** (`slopcheck install -e pypi aiobotocore pillow boto3 aioboto3`) — 4/4 `[OK]`; **`aioboto3` ning `aiobotocore` ni 3.9.0 → 2.25.1 va `boto3` ni 1.43.62 → 1.40.61 ga tushirishi EMPIRIK kuzatildi**
- **`Pillow` mahalliy o'lchov** (12.2.0): `ImageStat.Stat` mean/stddev/var; kesilgan JPEG → `OSError: Truncated File Read`; `Image.MAX_IMAGE_PIXELS = 89478485`; `ImageFile.LOAD_TRUNCATED_IMAGES = False`
- **SeaweedFS manba kodi:** `weed/command/server.go:161` (`-s3.port` standarti **8333**); `weed/s3api/auth_credentials.go:2127,2189` (`"Read:bucket"`, `"Write:bucket/prefix"` shakli)
- **SeaweedFS `docker/compose/s3.json`** (`curl` bilan olindi) — `identities` shakli **va** `anonymous`/`Read` yozuvi
- **GitHub API** (2026-08-04): `seaweedfs/seaweedfs` (Apache-2.0, arxivlanmagan, push 2026-08-03, reliz 4.40), `deuxfleurs-org/garage` (**AGPL-3.0**), `terricain/aioboto3` (push **2025-12-15**), `aio-libs/aiobotocore` (push 2026-08-03), `AlexxIT/go2rtc` (MIT, v1.9.14)
- **Docker Hub API:** `chrislusf/seaweedfs:4.40` tegi mavjud (2026-07-20)
- **go2rtc `internal/mjpeg/README.md`** — `/api/frame.jpeg` va `src`/`w`/`h`/`rotate`/`hw`/`cache` parametrlari
- **core.telegram.org/bots/faq** — «one message per second» (chat), «20 messages per minute» (guruh), «about 30 messages per second» (bulk), `429`
- **Loyihaning o'z kodi (o'qildi):** `app/worker.py`, `app/jobs/discovery.py`, `app/services/go2rtc.py`, `app/services/live_source.py`, `app/services/isapi/client.py`, `app/services/isapi/errors.py`, `app/repositories/market_repo.py`, `packages/sbozor-core/sbozor_core/timeutil.py`, `periods.py`, `schema_contract.py`, `models/identity.py`, `compose.yaml`, `pyproject.toml`, `package.json`, `ops/go2rtc/go2rtc.yaml`, `ops/mediamtx/mediamtx.yml`
- **Xost muhiti o'lchandi:** Docker 29.4.2, Compose v5.1.3, Node 24.14.1, Python 3.14.3; `uv` va `ffmpeg` xostda **yo'q**

### Secondary (MEDIUM — tekshirilgan, lekin bevosita o'lchanmagan)

- SeaweedFS wiki «Amazon S3 API» — `weed server -s3` bitta jarayonda master+volume+filer+S3 ni ko'taradi
- `docker/compose/local-s3tests-compose.yml` — `-s3.config` mount naqshi va port shakli
- Telegram rate-limit tahlillari (gramio.dev, tdlib/td #3034) — FAQ raqamlarini tasdiqlaydi

### Tertiary (LOW — tasdiq talab qiladi)

- Kadr o'lchami taxminlari (4 MP ~500 KB, D1 ~40 KB) — **[ASSUMED]**, real kamerada o'lchanmagan
- Sovuq kadr kechikishi ~4 s — **[ASSUMED]**, komponentlardan hisoblangan
- IR kadrning to'yinganlik chegarasi (< 0,05) — **[ASSUMED]**
- Sifat chegaralarining aniq raqamlari — **[ASSUMED]** va ataylab sozlanadigan

### Negative findings (VERIFIED — yo'qligi tasdiqlandi)

- `taskiq` da cron holatini **davomiy saqlaydigan** manba **yo'q** (`RedisScheduleSource` jadval ta'rifini saqlaydi, «oxirgi ishga tushish» ni emas)
- `taskiq` planerida **taqsimlangan qulf yo'q**
- MediaMTX sim'i **qorong'i/bo'sh/buzuq** kadr bera **olmaydi** (faqat `testsrc2`)
- `aioboto3` bilan `boto3 1.43.x` **birga o'rnatilmaydi**

---

## Metadata

**Ishonch taqsimoti:**

| Soha | Daraja | Sabab |
|---|---|---|
| Orkestratsiya (§A.2) | **HIGH** | `taskiq` manbasi o'qildi; `SKIP LOCKED` + lease — standart naqsh |
| Sxema (§A.1, §B.4) | **HIGH** | 1 va 2-fazaning o'lchangan naqshlaridan quriladi |
| Sifat vositalari (§C.7) | **HIGH** | `Pillow` mahalliy tekshirildi |
| Sifat **chegaralari** (§C.7) | **LOW** | Real kadr yo'q — ataylab sozlanadigan; o'lchov saqlanadi |
| Ombor (§D.9) | **HIGH** | Manba kodi + Docker Hub + `s3.json` tekshirildi |
| Paket pinlari (§D.9.2) | **HIGH** | Empirik o'rnatish bilan tasdiqlandi |
| Hajm arifmetikasi (§D.11) | **MEDIUM** | Formula HIGH, kirish kattaliklari LOW |
| Sessiya chegarasi (§B.6) | **LOW** | 3-fazadan o'zgarmadi; `max_concurrent=1` zaxirasi uni bloklovchi bo'lishdan chiqaradi |
| Alert (§E) | **HIGH** (Telegram raqamlari) / **MEDIUM** (guruhlash siyosati) | Rasmiy FAQ / loyihaga xos mulohaza |

**Tadqiqot sanasi:** 2026-08-04
**Amal qilish muddati:** **21 kun** — `aiobotocore` va `taskiq` faol rivojlanmoqda; `aioboto3` holati va SeaweedFS relizi qayta tekshirilishi kerak. Pin qarorlari (§D.9.2) rejalashtirishdan **oldin** qayta o'lchansin.
