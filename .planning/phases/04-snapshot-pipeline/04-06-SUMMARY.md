---
phase: 04-snapshot-pipeline
plan: 06
subsystem: backend
tags: [s3, aiobotocore, seaweedfs, storage, object-key, secret-free-errors, cam-07, d-17]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 01
    provides: "`aiobotocore==3.9.0` prod bog'liqligi, `storage` (SeaweedFS 4.40) konteyneri, `ops/seaweedfs/s3.json.example` + README, `tests` blokidagi `S3_*` o'zgaruvchilari"
  - phase: 04-snapshot-pipeline
    plan: 04
    provides: "`object_key()` / `KEY_PREFIX_FOR_DAY()` kalit fabrikasi va `Settings` ning `s3_*` maydonlari (`s3_secret_key` — `SecretStr`)"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 14
    provides: "MOCK'SIZ o'lchov metodikasi — `test_live_view_e2e.py` va uning «nomlar mahsulotdan olinadi» qoidasi"
provides:
  - "`app/services/storage.py` — `SnapshotStorage`: `put` / `head` / `get` / `list_prefix` / `delete_many`; `create_bucket`/`delete_bucket` STRUKTURAVIY ravishda yo'q"
  - "`StorageError` + `_failure()` — amal + istisno turi + status, `raise … from None` bilan zanjir uzilgan"
  - "`storage.open(settings)` — `@asynccontextmanager`, `get_secret_value()` ning YAGONA joyi"
  - "`orphan_keys(storage, prefix, expected)` — sof taqqoslash, KUN PREFIKSIDAN tashqari chaqiruvni `ValueError` bilan rad etadi"
  - "`tests/integration/conftest.py` — `s3_settings` / `s3_client` / `s3_markets` fixture'lari (HAQIQIY SeaweedFS, `pytest.skip` YO'Q)"
  - "`tests/integration/test_storage_layout.py` — 16 test, jumladan mock'siz o'lchov meta-testi"
affects: [04-07, 04-08, 04-09, 04-12, 05-cv-zonalar, 06-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sirsizlik testi NAZORAT HOLATI bilan boshlanadi: oqish yo'lining MAVJUDLIGI avval o'lchanadi (`assert URL in str(raw)`), keyin bizning xabarimizda YO'QLIGI — aks holda test o'z farazini tasdiqlaydi"
    - "Istisno `except` blokidan TASHQARIDA ko'tariladi (`_call`): blok tugagach kontekst tozalanadi, ya'ni `__context__` ham, `__cause__` ham xom istisnoni tashimaydi"
    - "Chegara tekshiruvi REGEX bilan cheklanmaydi — o'qilgan bo'laklardan satr FABRIKA orqali QAYTA QURILADI va solishtiriladi, shunda tekshiruv fabrikadan ajralib keta olmaydi"
    - "Tozalash fixture'i test yozgan kalitlarni EMAS, unga BERILGAN bozor prefikslarini supuradi — ya'ni u faqat kontrakt metodlaridan foydalanadi va yashirin yo'l ochmaydi"
    - "Mock taqig'i matn bo'yicha emas, `ast` daraxti bo'yicha o'qiladi — satr qidiruvi izohni, docstringni va darvozaning O'Z konstantasini koddan ajrata olmaydi"

key-files:
  created:
    - services/core-api/app/services/storage.py
    - tests/integration/test_storage_layout.py
  modified:
    - tests/integration/conftest.py
  deleted: []

key-decisions:
  - "O'LCHANDI VA REJANING FARAZI YARIM NOTO'G'RI CHIQDI: `ClientError` ning matni ombor manzilini ham, rekvizitni ham TASHIMAYDI; to'liq URL'ni (bucket va OBYEKT KALITI bilan) `BotoCoreError` oilasi — `EndpointConnectionError` — tashiydi. Mitigatsiya ikkalasiga ham qo'llanadi, lekin test endi HAQIQATAN oqadigan shoxni o'lchaydi"
  - "`delete_objects` da `Quiet` ISHLATILMAYDI: o'lchandi — `Quiet=True` bilan SeaweedFS javobda `Deleted` ni ham, `Errors` ni ham qaytarmadi, ya'ni «nechta o'chdi» va «nimadir o'chmadimi» savollarining ikkalasi ham javobsiz qolardi"
  - "`head()` ning «yo'q» kodlari ro'yxati O'LCHANGAN: SeaweedFS `HEAD` da `\"404\"`, `GET` da `NoSuchKey` beradi (HEAD javobida tana yo'q, `botocore` kodni statusdan hosil qiladi). Faqat `NoSuchKey` tekshirilsa har bir mavjud bo'lmagan kalit `StorageError` berardi"
  - "`NoSuchBucket` ATAYIN «yo'q» ro'yxatiga kiritilmadi — u ham 404 beradi, lekin ma'nosi konfiguratsiya nosozligi; fail-closed yo'nalish `StorageError`"
  - "Sirsizlik testi Task 1 ning `<behavior>` ida bor edi, lekin rejada unga TEST ajratilmagan (Task 1 ning `<files>` ida test fayli yo'q) — test qo'shildi va u nazorat holati bilan keldi"
  - "`s3_client` fixture'i `test_settings` ni ISHLATMAYDI: u Postgres/Valkey testcontainerlarini talab qilardi va ombor o'lchovi baza qatlamining ko'tarilishiga bog'lanib qolardi"
  - "Bucket zondi `head_bucket` EMAS, kontraktdagi `head()` bilan bajariladi — `SnapshotStorage` ga bucket darajasidagi metod qo'shish qobiqni kontraktdan kengaytirardi"
  - "Sahifalash testi `slow` markerini oldi: `npm run test:sim` ning tez yo'lidan chetda, `pytest -q` (to'liq darvoza) esa uni BARIBIR bajaradi"

patterns-established:
  - "Pattern: ikki darvoza bir xil obyektni tekshirsa ham TURLI da'voni o'lchashi kerak — ustiga yozish testi kun prefiksidan BOZOR prefiksiga ko'chirildi, aks holda kalit tartibi sabotaji ikkala testni birdan qizartirib, «qaysi darvoza nimani o'lchaydi» savolini javobsiz qoldirardi"
  - "Pattern: fixture o'tkazib yubormaydi, YIQILADI — profilsiz konteynerning yo'qligi normal ish oqimi emas, konfiguratsiya xatosi (`nvr-sim` ning skip qoidasidan ATAYIN farq qiladi va farq fixture docstringida yozilgan)"
  - "Pattern: yangi qatlamning har bir ombor-xulqi (yo'q kalit kodi, sahifa chegarasi, `Quiet` semantikasi) hujjatdan emas, TIRIK konteynerdan o'lchanadi va o'lchov sanasi bilan kod izohiga yoziladi"

requirements-completed: [CAM-07]

# Metrics
duration: 3h 55m
completed: 2026-08-04
---

# Phase 4 Plan 06: Obyekt-ombor qatlami Summary

**Loyihaning BIRINCHI S3 klienti tug'ildi va uning har bir da'vosi TIRIK SeaweedFS konteynerida o'lchandi: kadr deterministik kalit bilan yoziladi, o'sha kalitga qayta yozish idempotent, kun prefiksi retention'ning yagona skanini beradi, prefiks izolyatsiyasi ikki bozorli holatda tasdiqlangan, sahifalash 1000-obyektdan keyin ham to'liq ro'yxat beradi, `StorageError` esa ombor manzilini — bucket va obyekt kaliti bilan birga — na xabarida, na `traceback` ida olib chiqmaydi.**

## Performance

- **Duration:** ~3 soat 55 daqiqa
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 3 (2 yangi, 1 o'zgartirilgan) — 530 qator ishlab chiqarish kodi, 16 yangi test
- **Commits:** 4 (bitta to'liq RED→GREEN juftligi + bitta darvoza ajratish + bitta feat)

## Task Commits

| # | Task | Commit | Turi |
|---|------|--------|------|
| 2 (RED) | `s3_*` fixture'lari + `test_storage_layout.py` | `eb4318b` | `test` |
| 1 (GREEN) | `storage.py` — `aiobotocore` qobig'i, sirsiz xato | `faa7734` | `feat` |
| 2 (aniqlash) | Ustiga yozish darvozasini kun prefiksidan ajratish | `cbf95d6` | `test` |
| 3 | `orphan_keys` + kun prefiksi chegarasi | `7a9d027` | `feat` |

## O'LCHOVLAR — hech biri hujjatdan olinmadi

Barcha raqamlar `chrislusf/seaweedfs:4.40` + `aiobotocore 3.9.0` konteynerida,
2026-08-04 da olingan.

| Savol | O'lchangan javob | Qarorga ta'siri |
|---|---|---|
| `head_object(yo'q kalit)` qanday kod beradi? | **`Error.Code = "404"`**, HTTP 404 | Faqat `NoSuchKey` tekshirilsa `head()` HAR BIR yo'q kalit uchun `StorageError` berardi |
| `get_object(yo'q kalit)`? | **`NoSuchKey`**, HTTP 404 | Ikkala kod ham ro'yxatda |
| `head_object(yo'q bucket)`? | **`403`** (qadalgan rekvizit) | Bucket zondi ishlaydi: bucket bor -> `None`, yo'q -> `StorageError` |
| `list_objects_v2` 1005 obyektda? | **`KeyCount=1000`, `IsTruncated=True`**, davom etish tokeni bor | Sahifalash SHU omborga nisbatan haqiqiy — test bo'sh urinish emas |
| Paginator o'sha holatda? | **1005 kalit, 2 sahifa, 0,6 s** | `list_prefix` paginator bilan yoziladi |
| `delete_objects(Quiet=True)`? | Javobda **faqat `ResponseMetadata`** — `Deleted` ham, `Errors` ham YO'Q | `Quiet` ISHLATILMAYDI (pastda, 4-deviatsiya) |
| `delete_objects` (Quiet'siz), 1000+5 kalit? | `Deleted: 1000` + `Deleted: 5`, `Errors: 0` | To'plam chegarasi 1000 ta |
| 1005 `put_object` narxi (32 parallel)? | **3,6 s** | Sahifalash testi qimmat emas |
| `ClientError` matnida manzil bormi? | **YO'Q** (`SignatureDoesNotMatch`, `InvalidAccessKeyId`, `NoSuchKey` — uchalasida ham) | Rejaning farazi yarim noto'g'ri (pastda, 3-deviatsiya) |
| `EndpointConnectionError` matnida? | **BOR — to'liq URL, bucket VA obyekt kaliti bilan** | Sirsizlik testi AYNAN shu shoxni o'lchaydi |
| Rekvizit (access/secret) istisno matnida? | Uchala holatda ham **YO'Q** | Test ikkalasini ham tekshiradi (regressiya darvozasi) |

## Sabotaj o'lchovlari — nima QIZARDI va nima YASHIL QOLDI

Bu loyihada ikkinchi ustun qayta-qayta birinchisidan ko'ra ko'proq ma'lumot bergan.

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Xulosa |
|---|---|---|---|---|
| 1 | `object_key()` tartibi `market/sana/kamera/slot` -> **`market/kamera/sana/slot`** | **AYNAN 1 test**: `test_the_day_prefix_finds_every_camera_of_that_day_only`. Xabar mahsulot atamalari bilan: «kalit tartibi `market/sana/kamera/slot` emas»; diff `[] == [4 ta kalit]` | **Qolgan 9 test**, jumladan `put`/`head`/`get`, ustiga yozish, prefiks izolyatsiyasi va sahifalash | Tartib qarori ALOHIDA o'lchanadi. ⚠ Birinchi urinishda **2 test** qizargan edi — ustiga yozish testi ham kun prefiksidan foydalanardi; u tuzatilib, `cbf95d6` da bozor prefiksiga ko'chirildi |
| 2 | `orphan_keys` dan `_assert_day_prefix(prefix)` chaqiruvi olib tashlandi | **AYNAN 4 test** — `test_orphan_keys_rejects_a_free_prefix` ning to'rtala parametri (`""`, `"sbozor/"`, `"{uuid}/"`, `"{uuid}/2026-09-01"`) | **Qolgan 12 test**, jumladan `orphan_keys` ning IKKALA funksional testi (yetimni topadi, yolg'on-musbat bermaydi) | Chegara funksionallikdan MUSTAQIL o'lchanadi — rejaning bashorati aynan tasdiqlandi |

Ikkala holatda ham fayl darhol `git checkout -- <fayl>` bilan tiklandi va to'plam
qayta yashil bo'ldi (16/16).

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm run sim:up` | exit 0; `storage`, `go2rtc`, `nvr-sim`, `nvr-sim-rtsp` — **healthy** |
| 2 | `pytest tests/integration/test_storage_layout.py -m sim -q` | **16 test**, exit 0 (talab: >= 10) |
| 3 | `ruff check . && ruff format --check . && mypy .` | exit 0 — 222 fayl formatlangan, **216 fayl tiplangan** |
| 4 | `pytest -q` (to'liq) | **1 670 test**, exit 0 (talab: >= 1 520) |
| 5 | `pytest tests/unit/test_no_sim_branching.py -q` | **5**, exit 0 |
| 6 | `git diff --exit-code worker.py pyproject.toml frontend/package.json` | **o'zgarish yo'q** (T-04-SC tasdiqlandi) |
| 7 | `npm run gate` | exit 0, **642 s** (sovuq worktree: `node_modules` yangi o'rnatilgan, `.next` keshi yo'q) |
| 8 | `pytest tests/tenancy -q --collect-only` | **426** (o'zgarmagan) |
| 9 | vitest / node darvozalari | **246** / **111** (ikkalasi ham o'zgarmagan) |
| 10 | `npm --prefix frontend run i18n:check` | **577 kalit x 3 til**, drift yo'q |

**Task 1 ning matn mezonlari** (hammasi exit 0): `get_secret_value()` sanog'i **1**;
`from None` bor; izohsiz tanada qo'lda imzolash literallari **yo'q**; `_failure`
ning tanasida istisno interpolyatsiyasi ham, `endpoint` so'zi ham **yo'q**;
`hasattr(SnapshotStorage, "create_bucket"/"delete_bucket")` — **ikkalasi ham
`False`**; `storage.py` **530 qator** (talab >= 150).

**Task 2/3 ning matn mezonlari:** test faylida mock kutubxonalari import
qilinmagan; kalit `object_key(` fabrikasidan olinadi; `pytest.skip` literali
**yo'q**; `storage.py` da `ValueError` va `KEY_PREFIX` bor; `orphan_keys` ning
imzosida `prefix` parametri bor.

## Bazaviy holat

| O'lchov | Bu worktree bazasi (`6db3d51`) | Hozir | Holat |
|---|---|---|---|
| pytest (backend) | 1 654 | **1 670** | +16 |
| tenancy | 426 | **426** | o'zgarmagan |
| vitest | 246 | **246** | o'zgarmagan |
| node darvozalari | 111 | **111** | o'zgarmagan |
| i18n | 577x3 | **577x3** | o'zgarmagan |
| `ruff` + `ruff format` + `mypy` | toza | **toza** | — |

⚠ Topshiriqda berilgan «pytest 1580» bazasi ESKIROQ nuqtani (04-03/04-04 merge'idan
oldingi holatni) bildiradi. Bu worktree `6db3d51` (`merge(04-04)`) dan boshlanadi va
o'sha nuqtada sanoq **1 654** edi; +16 aynan shu rejaning testlari.

## Decisions Made

1. **Sirsizlik testi NAZORAT HOLATI bilan keladi.** Test avval xom
   `EndpointConnectionError` ning manzilni HAQIQATAN tashishini o'lchaydi, keyin
   bizning `StorageError` da uning yo'qligini. Nazoratsiz test `_failure()` butunlay
   oqib turgan holatda ham yashil bo'lishi mumkin edi — 04-04 ning 2a/2b darsi.

2. **Istisno `except` blokidan TASHQARIDA ko'tariladi** (`_call` yordamchisi). Blok
   tugagach Python istisno kontekstini tozalaydi, ya'ni `__context__` ham bo'sh
   qoladi. `from None` yolg'iz o'zi faqat `__cause__` ni yopardi. Test ikkalasini ham
   o'lchaydi (`__cause__ is None`, `__suppress_context__ is True`, va butun
   `format_exception` chiqishida manzil yo'q).

3. **Chegara tekshiruvi FABRIKA orqali qayta quriladi.** `_assert_day_prefix` regex
   bilan shaklni o'qiydi, so'ng bo'laklardan prefiksni `KEY_PREFIX_FOR_DAY()` bilan
   QAYTA QURADI va kirish bilan solishtiradi. Faqat regex qoldirilsa u bir kun kalit
   fabrikasidan jimgina ajralib ketardi — `KEY_PREFIX_FOR_DAY` ning O'Z docstringi
   aynan shu sinfni nomlaydi.

4. **`tenacity` qo'shilmadi.** `botocore` ning `retries={"max_attempts": 3, "mode":
   "standard"}` siyosati yetarli; ikkinchi qatlam urinishlar sonini 9 ga ko'tarardi va
   umumiy vaqt byudjetini hech kim hisoblamasdi (`isapi/client.py` qoidasi).

5. **`s3_markets` fixture'i — tozalashning yagona mexanizmi.** Reja «fixture yozilgan
   kalitlarni tozalaydi» deydi, lekin fixture test qaysi kalitlarni yozganini BILA
   OLMAYDI. Yechim: fixture ikki bozor identifikatorini O'ZI beradi va testdan keyin
   ularning prefikslarini `list_prefix` + `delete_many` bilan supuradi — ya'ni tozalash
   ham faqat kontrakt metodlaridan foydalanadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — bloklovchi] `aiobotocore` va `botocore` da `py.typed` YO'Q**

- **Topildi:** Task 1, birinchi `mypy .` yugurishida
- **Muammo:** O'lchandi — `aiobotocore` va `botocore` ning ikkalasida ham `py.typed`
  markeri yo'q (`aiohttp` da bor). `mypy --strict` ostida ularning importi
  `import-untyped` xatosi beradi, ya'ni butun repo bo'yicha tip tekshiruvi yiqilardi.
- **Yechim:** Uch import satriga (`storage.py`) va bittasiga (test moduli)
  `# type: ignore[import-untyped]` qo'yildi. **Muqobil rad etildi:** ildizdagi
  `pyproject.toml` ning `[[tool.mypy.overrides]]` bloki (mavjud «`py.typed` YO'Q
  paketlar» ro'yxati) semantik jihatdan to'g'riroq joy, lekin u fayl bu rejaning
  `files_modified` idan TASHQARIDA va parallel to'lqindagi ijrochi bilan umumiy.
  Ikkala yo'l ham bir xil natija beradi; farqi joylashuvda.
- **Qoldiq:** ro'yxatga ko'chirish arzon va uni `compose.yaml`/`pyproject.toml` ga
  tegadigan keyingi reja bajarishi mumkin (`04-08`). `warn_unused_ignores` yoqilgan,
  ya'ni ko'chirilgan kuni ortiqcha `# type: ignore` DARHOL qizaradi — qarz jimgina
  qolmaydi.
- **Fayllar:** `services/core-api/app/services/storage.py`, `tests/integration/test_storage_layout.py` — `faa7734`

**2. [O'z-o'ziga zid mezon] Task 1 `tdd="true"`, lekin uning `<files>` ida test fayli YO'Q**

- **Qayerda:** Task 1 ning frontmatteri va `<files>` bandi
- **Muammo:** RED bosqichini Task 1 ning fayl to'plami ichida bajarib bo'lmaydi —
  `storage.py` yagona fayl. Task 1 ning `<behavior>` bandlari esa (ustiga yozish,
  `head` -> `None`, sahifalash) haqiqiy ombor talab qiladi, ya'ni ular Task 2 ning
  test modulida yashaydi.
- **Yechim:** RED/GREEN juftligi tasklar orasidan o'tkazildi va HAQIQIY qoldi:
  `eb4318b` (Task 2 ning fayllari) **o'lchangan RED** berdi —
  `ImportError: cannot import name 'storage' from 'app.services'`; `faa7734` (Task 1
  ning fayli) uni GREEN qildi. Har ikki taskning fayl to'plami buzilmadi.
- **Fayllar:** yo'q (faqat tartib)

**3. [Rule 1 — o'lchanmagan faraz] `ClientError` endpoint URL'ini TASHIMAYDI — oqish `BotoCoreError` da**

- **Topildi:** Task 1, sirsizlik testini yozishdan oldingi zondda
- **Muammo:** Reja va `04-RESEARCH.md` §D.9.2 «`aiobotocore` ning `ClientError` i
  endpoint URL'ini va ba'zan imzo bo'laklarini matnda tashiydi» deydi. **O'lchandi —
  bu yarim noto'g'ri:**

  ```
  ClientError (SignatureDoesNotMatch): manzil YO'Q, rekvizit YO'Q
  ClientError (InvalidAccessKeyId)   : manzil YO'Q, rekvizit YO'Q
  ClientError (NoSuchKey)            : manzil YO'Q, rekvizit YO'Q
  EndpointConnectionError            : "Could not connect to the endpoint URL:
                                        http://…:8333/sbozor-snapshots/<market>/
                                        <sana>/<kamera>/0630.jpg"   <-- TO'LIQ URL
  ```

- **Nima uchun kritik:** faqat `ClientError` ustida yozilgan sirsizlik testi
  `_failure()` BUTUNLAY oqib turgan holatda ham yashil bo'lardi — chunki o'sha shoxda
  oqadigan narsaning o'zi yo'q. Ya'ni darvoza «bor» bo'lib ko'rinardi.
- **Yechim:** mitigatsiya IKKALA oilaga ham qo'llanadi (chaqiruvchi qaysi sinf
  kelganini bilmaydi), lekin **test aynan oqadigan shoxni** o'lchaydi: yetib
  bo'lmaydigan manzilga `put` -> `EndpointConnectionError` -> `StorageError`. Natija
  modul docstringiga o'lchov sanasi bilan yozildi.
- **Fayllar:** `services/core-api/app/services/storage.py`, `tests/integration/test_storage_layout.py` — `faa7734`

**4. [Rule 1 — bug] `delete_objects(Quiet=True)` SeaweedFS'da hech nima qaytarmaydi**

- **Topildi:** Task 1, `delete_many` ni yozishdan oldingi zondda
- **Muammo:** S3 spetsifikatsiyasi `Quiet=True` uchun «faqat xatolar qaytadi» deydi.
  O'lchandi — SeaweedFS 4.40 javobda **na `Deleted`, na `Errors`** qaytardi (faqat
  `ResponseMetadata`). Ya'ni `Quiet` bilan yozilgan `delete_many` HAR DOIM `0`
  qaytarardi va qisman nosozlikni HECH QACHON sezmasdi — retention har kuni
  «hammasi o'chdi» deb hisobot berardi.
- **Yechim:** `Quiet` umuman ishlatilmaydi. Quiet'siz javob `Deleted: 1000` /
  `Errors: 0` beradi (o'lchandi), ya'ni sanoq ham, xato tekshiruvi ham haqiqiy.
  Qisman nosozlik `StorageError` ga aylanadi (fail-closed: o'chmagan obyekt ertaga
  qayta uriniladi, «o'chdi» deb belgilangan obyekt esa qaytmasdi).
- **Fayllar:** `services/core-api/app/services/storage.py` — `faa7734`

**5. [Rule 1 — o'z kodimdagi bug] Ustiga yozish testi kun prefiksiga BOG'LANGAN edi**

- **Topildi:** Task 2 ning sabotaj o'lchovida
- **Muammo:** Birinchi variantda ustiga yozish testi obyektlar sonini
  `KEY_PREFIX_FOR_DAY(...)` orqali sanardi. Kalit tartibi sabotaji **ikkala** testni
  birdan qizartirdi, ya'ni sabotaj «qaysi darvoza nimani o'lchaydi» savoliga javob
  bermasdi.
- **Yechim:** ustiga yozish testi BOZOR prefiksiga (`f"{market}/"`) ko'chirildi — u
  segment tartibiga bog'liq emas. Qayta o'lchandi: sabotaj endi **AYNAN bitta**
  testni qizartiradi. Sabab kodda, o'sha satrning yonida yozildi.
- **Fayllar:** `tests/integration/test_storage_layout.py` — `cbf95d6`

**6. [Rule 2 — yetishmayotgan kritik test] `StorageError` ning sirsizligiga test ajratilmagan edi**

- **Topildi:** Task 1 ning `<behavior>` bandini bajarganda
- **Muammo:** Reja `StorageError` ning matnida manzil/kalit bo'lmasligini va
  `__cause__` ning `None` bo'lishini TALAB qiladi, lekin Task 1 ning `<files>` ida
  test fayli yo'q va Task 2 ning `<behavior>` ida bu band yo'q. Ya'ni T-04-40 ning
  mitigatsiyasi kodda bo'lib, o'lchovsiz qolardi.
- **Yechim:** `test_a_storage_error_never_carries_the_endpoint_url` qo'shildi. U
  oltita da'voni o'lchaydi: manzil xabarda yo'q, manzil `traceback` da yo'q, obyekt
  kaliti ikkalasida ham yo'q, access kaliti yo'q, maxfiy kalit yo'q, `__cause__ is
  None` va `__suppress_context__ is True` — va istisno TURI xabarda BOR (diagnostika
  yo'qolmagani).
- **Fayllar:** `tests/integration/test_storage_layout.py` — `faa7734`

**7. [Rule 2 — bajarib bo'lmaydigan mexanika] Fixture yozilgan kalitlarni BILA OLMAYDI**

- **Topildi:** Task 2, `s3_client` fixture'ini yozishda
- **Muammo:** Reja «fixture testdan keyin yozilgan kalitlarni tozalaydi
  (`delete_many`)» deydi. Fixture esa test qaysi kalitlarni yozganini bilmaydi va
  uni bilishi uchun `put` ni o'rab olish (ya'ni mahsulot obyektini almashtirish)
  kerak bo'lardi — bu esa aynan shu faylda TAQIQLANGAN yo'l.
- **Yechim:** `s3_markets` fixture'i qo'shildi: u testga ikki bozor identifikatorini
  BERADI va testdan keyin ularning prefikslarini supuradi. Qoida («bozor
  identifikatori faqat shu fixture'dan olinadi») docstringda yozildi. Yon foyda:
  prefiks izolyatsiyasi testi uchun kerak bo'lgan ikkinchi bozor shu yerdan keladi.
- **Fayllar:** `tests/integration/conftest.py` — `eb4318b`

**8. [Rule 2] `head_bucket` o'rniga kontraktdagi `head()`**

- **Topildi:** Task 2
- **Muammo:** Reja «fixture'ning `head_bucket` tekshiruvi» deydi, lekin
  `SnapshotStorage` da bunday metod yo'q va uni qo'shish qobiqni kontraktdan
  kengaytirardi (Task 1 ning butun mazmuni — metodlar ro'yxatining yopiqligi).
- **Yechim:** zond `head()` bilan bajariladi. O'lchandi: bucket BOR bo'lsa yo'q kalit
  `None` beradi; bucket YO'Q bo'lsa qadalgan rekvizit `403` oladi va u
  `_ABSENT_ERROR_CODES` da yo'q, ya'ni `StorageError` chiqadi. Ya'ni zond bir xil
  aniqlikda ishlaydi va yangi metod kerak emas.
- **Fayllar:** `tests/integration/conftest.py` — `eb4318b`

---

**Total deviations:** 8 (2x Rule 1 bug, 3x Rule 2 yetishmayotgan xulq, 1x Rule 3
bloklovchi, 2x o'z-o'ziga zid/bajarib bo'lmaydigan mezon)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Uchtasi (3, 4, 5) rejaning
yoki mening O'LCHANMAGAN farazlarimni o'lchov bilan almashtirdi va uchalasida ham
natija rejadagidan **kuchliroq** darvoza berdi.

## Qoldiq chegaralar — ochiq yozilgan

1. **`pytest -q` endi `storage` konteynerisiz YIQILADI (16 test).** Bu ATAYIN: reja
   `pytest.skip` ni ochiq taqiqlaydi, chunki o'tkazib yuborilgan test yashil darvozada
   ko'rinmaydi va CAM-07 isbotsiz qolardi. Xato matni ikkala sababni ham (konteyner
   ko'tarilmagan / bucket yaratilmagan) va ikkala yechimni ham nomlaydi.

   ⚠ **Lekin `compose.yaml` ning `tests` xizmatida `depends_on` YO'Q**, ya'ni
   `npm run test` ni yolg'iz chaqirgan dev'da konteyner avtomatik ko'tarilmaydi.
   `npm run gate` va `npm run test:sim` `sim:up` ni O'Z ichiga oladi, `npm run up` esa
   `storage` ni profilsiz ko'taradi — ya'ni hujjatlangan uchala yo'l ham ishlaydi.
   `compose.yaml` bu rejaning fayllari ichida emas; **egasi `04-08`** (retention shu
   omborga ulanadigan birinchi reja) yoki `04-12` (faza darvozasi):
   `tests` xizmatiga `depends_on: {storage: {condition: service_healthy}}` qo'shilsa
   bu qoldiq butunlay yopiladi.

2. **`S3_REGION` hali `.env.example` da yo'q va `_ENV_EXAMPLE_TODO` reyestrida
   qoladi.** `04-04` bu bandni `04-06` ga **shartli** o'tkazgan edi («agar `04-06` uni
   o'sha faylga qo'shsa, reyestrdan ham OLIB TASHLASHI shart»). `.env.example` bu
   rejaning `files_modified` ida YO'Q va u parallel to'lqin bilan umumiy fayl, ya'ni
   band OCHIQ qoldirildi va ikki tomonlama darvoza (`test_every_settings_field_is_
   documented_or_registered`) hozircha yashil. **Egasi:** `.env.example` ga keyingi
   tegadigan reja.

3. **Bitta rekvizit barcha bozorlarni ochadi** (T-04-43, `accept`). Bu bazadagi
   ishonch modeli bilan bir xil va u yangi teshik emas. Kompensatsiya SHU REJADA
   o'lchandi: prefiks izolyatsiyasi ikki bozorli test bilan tasdiqlangan, ya'ni
   ilova qatlami kalitni to'g'ri qurganda kadrlar aralashmaydi.

4. **`put()` ning `size_bytes` i YOZILGAN tananing uzunligi**, ombor tasdiqlagan hajm
   emas: SeaweedFS `PutObject` javobida hajmni qaytarmaydi (o'lchandi — javobda
   faqat `ETag` va `ChecksumCRC32`). Ombor tomonidan tasdiqlash uchun har yuklashga
   ikkinchi `head()` so'rovi kerak bo'lardi. `head()` esa haqiqiy hajmni beradi va
   test aynan shu yo'l bilan ustiga yozishni tasdiqlaydi.

## Known Stubs

Yo'q. Uchala amal ham to'liq ishlaydi va har biri o'z o'lchovi bilan keldi.
`04-07` (worker resursi) va `04-08` (retention) uchun ochiq qolgan ulanishlar
STUB emas — ular boshqa rejalarning fayllarida yashaydi va o'sha rejalarning
qabul mezonlarida nomlangan.

## Threat Flags

Yangi tarmoq endpointi, auth yo'li yoki sxema chegarasi YO'Q — bu reja mavjud
ombor chegarasining MIJOZ tomonini yozadi. Threat register'ning yetti
mitigatsiyasi bajarildi va o'lchandi:

| Threat | Holat |
|---|---|
| T-04-40 (xatoda manzil/imzo) | `_failure()` uch faktdan boshqa hech nima bermaydi; `raise … from None` **va** `except` blokidan tashqarida ko'tarish; test xabarni ham, `traceback` ni ham tekshiradi. ⚠ Oqish yo'li o'lchandi va u `BotoCoreError` da (3-deviatsiya) |
| T-04-41 (maxfiy kalitga bir necha joydan borish) | Ochiq qiymatga borish **aynan bitta** joyda; sanoq darvozasi `== 1` |
| T-04-42 (bucket yaratish/o'chirish) | `create_bucket`/`delete_bucket` **umuman yozilmagan**; `hasattr` darvozasi ikkalasi uchun ham `False`; xom klient tashqariga chiqarilmaydi (`__getattr__` yo'q) |
| T-04-43 (bitta rekvizit barcha bozorlarga) | `accept` — kompensatsiya sifatida prefiks izolyatsiyasi IKKI bozorli test bilan o'lchandi |
| T-04-44 (qo'lda imzolash) | Imzolash butunlay `aiobotocore` da; matn darvozasi izohsiz tanada tegishli literallarni topmadi |
| T-04-45 (mock ostidagi o'lchov) | `test_storage_layout_uses_no_mock` — `ast` daraxti bo'yicha import ildizlari va nomlari, **hamda** haqiqiy omborga boradigan testlarning quyi chegarasi (>= 6; hozir 11) |
| T-04-46 (erkin prefiksli listing) | `orphan_keys` faqat kun prefiksini qabul qiladi; shakl fabrikadan QAYTA QURILADI; to'rt xil erkin prefiks bilan o'lchandi |
| T-04-47 (yarim muvaffaqiyat kompensatsiyasi) | Ustiga yozish idempotentligi haqiqiy omborda o'lchandi (`etag` o'zgaradi, `size_bytes` yangilanadi, prefiksda **bitta** obyekt qoladi) |
| T-04-SC (paket o'rnatish) | Yangi paket YO'Q; `git diff --exit-code services/core-api/pyproject.toml frontend/package.json` toza |

## Issues Encountered

- **`ops/seaweedfs/s3.json` va bucket QO'LDA yaratildi.** Ikkalasi ham `.gitignore`
  da / holatda, ya'ni repo o'zgarmadi. Kalitlar `compose.yaml` ning `tests` blokidagi
  standartlar bilan AYNAN bir xil qo'yildi (`sbozor-local-access-key` /
  `sbozor-local-secret-key`) — shunda `.env` siz ham zanjir butun bo'ladi.
  `README.md` dagi `printf … | weed shell` shakli ishladi (`created bucket
  sbozor-snapshots`), ya'ni `04-01` ning tuzatishi to'g'ri.
- **Frontend `node_modules` bu worktree'da yo'q edi** — `npm ci --prefix frontend`
  bajarildi. `package.json`/`package-lock.json` **tegilmadi**.
- **`npm run gate` 642 s** — `04-01` ning 461–490 s seriyasidan yuqori, lekin
  o'lchov sharti BOSHQA: bu worktree'da `node_modules` yangi o'rnatilgan va `.next`
  keshi umuman yo'q edi. Chegara (1 200 s) hali ham ikki barobar zaxira bilan
  bajarilyapti. **Chegara bu rejada o'zgartirilmadi** va `04-VALIDATION.md` ga
  TEGILMADI — u parallel to'lqin bilan umumiy fayl.
- **Parallel ijro va bitta compose loyihasi.** `04-05` ijrochisi bir xil `sbozor`
  compose loyihasida ishlaydi. Faqat `up` amallari bajarildi (`storage`, keyin
  `sim:up`); birorta konteyner to'xtatilmadi yoki o'chirilmadi.

## Next Phase Readiness

**`04-07` (tik/scheduler/worker) uchun tayyor va u shu uch satrni o'qishi kerak:**
- `storage.open(settings)` — `@asynccontextmanager`. Worker jarayonida u
  `WORKER_STARTUP` da ochilib `TaskiqState` ga qo'yiladi, `WORKER_SHUTDOWN` da
  yopiladi. `worker.py` bu rejada **TEGILMADI** (`git diff --exit-code` bilan
  tasdiqlandi).
- Tartib QATIY: avval `storage.put(object_key(...), data)`, KEYIN baza qatori (§B.4).
  Teskari tartib 6-fazaga mavjud bo'lmagan dalilga havola berardi.
- `StorageError` ni ushlab, uni `capture_errors.py` ning kodiga aylantirish
  chaqiruvchining ishi — `storage.py` xato KODINI bilmaydi va bilishi shart emas.

**`04-08` (retention + alert) uchun:**
- `list_prefix(KEY_PREFIX_FOR_DAY(...))` va `delete_many(...)` tayyor; `delete_many`
  o'chirilganlar SONINI qaytaradi va qisman nosozlikda yiqiladi.
- `orphan_keys(storage, prefix=…, expected=…)` — kunlik supurgining ichiga
  qo'yiladi; `expected` bazadan (`snapshot_repo`) keladi.
- **Ikki band shu rejadan o'tkazildi:** (a) `tests` xizmatiga `depends_on: storage`,
  (b) `censor_secrets` ning `s3_*` qamrovi (`04-04` dan meros — u hali ham
  `s3_access_key`/`s3_secret_key` ni QAMRAMAYDI, ya'ni bu rejaning kodi ombor
  sirlarini structlog kalitiga HECH QAYERDA bermaydi va bermasligi kerak).

**`04-09` (rasm proxysi) uchun:** klient SO'ROV DAVOMIDA `async with
storage.open(...)` bilan ochiladi — farq va sababi `storage.py` ning modul
docstringida yozilgan. `get(key)` baytlarni bayt-bayt qaytaradi (o'lchandi).

**`04-12` (faza darvozasi) uchun:** mock'siz o'lchovning jufti tayyor —
`test_storage_layout.py` da `test_storage_layout_uses_no_mock` va u haqiqiy
omborga boradigan testlarning quyi chegarasini ham qo'yadi (>= 6, hozir 11).

**Bloklovchi yo'q.**

## Self-Check: PASSED

- **Yaratilgan 2 fayl + o'zgartirilgan 1 fayl** — uchalasi ham diskda tekshirildi
  (`MISSING COUNT: 0`).
- **To'rtala commit `git log` da tasdiqlandi:** `eb4318b`, `faa7734`, `cbf95d6`,
  `7a9d027` — bazasi `6db3d51`.
- **Reja artefakt shartlari o'lchandi:** `storage.py` **530 qator** (talab >= 150) va
  `StorageError` ni o'z ichiga oladi; `test_storage_layout.py` da `sim` markeri bor
  va **16 test** yig'iladi (talab >= 10).
- **`key_links` o'lchandi:** `storage.py` `app.services.object_key` dan
  `KEY_PREFIX_FOR_DAY` ni IMPORT qiladi va uni `_assert_day_prefix` da CHAQIRADI
  (satr qo'lda qurilmaydi); `test_storage_layout.py` `s3_client` fixture'i orqali
  haqiqiy `aiobotocore` klientiga boradi.
- **`STATE.md` va `ROADMAP.md` TEGILMADI** — ular to'lqin merge'idan keyin
  orkestrator tomonidan yangilanadi.

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-04*
