# 4-faza — doiradan tashqarida topilgan bandlar

Bu fayl **tuzatilmagan** topilmalar reyestri. Har band uchun: qayerda,
nima o'lchangan, nima uchun bu rejada tegilmagan, egasi kim.

⚠ **Yopilgan band O'CHIRILMAYDI** — reyestrning qiymati tarixida:
`04-VERIFICATION.md` bu bandlarga **raqami bilan** havola qiladi va
o'chirilgan band havolani uzardi. Yopilgani sarlavhada **✅ YOPILDI** bilan
belgilanadi, sababi esa band oxirida yangi kichik bo'lim bo'lib qo'shiladi.

| # | Bu rejadagi holat | Qayerda yopildi |
|---|---|---|
| 2 | ✅ **YOPILDI** | `04-14` / T1 — `.env.example` ↔ `s3.json.example` juftligi + uning tenglik darvozasi |
| 3 | ✅ **YOPILDI** | `04-14` / T1 — `ops/seaweedfs/README.md` §2 dagi «`npm run up` dan OLDIN» ogohlantirishi |

⚠ **#1 bu rejada TEGILMADI** — uning matni, egasi va tetigi
o'zgarmagan. Uning holati bu reyestrda emas, `04-VERIFICATION.md` ning
«Kechiktirilgan bandlar» bo'limida yuritiladi va o'sha hujjat
2026-08-05 da **«#1 yopilgan»** deb yozgan (`_anchor_today()`, `04-12`).
O'lchov: `grep -c _anchor_today tests/tenancy/test_snapshot_domain_meta.py`
→ **3**. Bu yerda hech qanday YANGI da'vo qilinmaydi; havola faqat
o'quvchi «#1 ochiqmi?» savoliga reyestrni qayta o'qimasdan javob olishi
uchun.

---

## 1. `test_capture_due_markets_exposes_only_identifiers` YARIM TUNDA flaky

**Qayerda:** `tests/tenancy/test_snapshot_domain_meta.py:636` (`_NEAR = 5 daqiqa`)

**O'lchangan (2026-08-04 23:59:33, `npm run gate` ichida):**

```
qator_kuni = 2026-08-05      bugun = 2026-08-04
disjunkt_1 (muddati kelgan `pending`) = 0
disjunkt_2 (bugungi reja YO'Q)        = TRUE   <- bozorni QAYTARADI
disjunkt_3 (ijarasi tugagan `running`) = FALSE
```

Test `now() + 5 daqiqa` da `pending` qator yozib, «bozor qaytarilmaydi» deb
da'vo qiladi. Yarim tundan 5 daqiqa oldin o'sha qator **ertangi**
biznes-kunga tushadi, ya'ni «bugungi reja YO'Q» sharti rost bo'ladi va
bozor qaytariladi. Assertion qizaradi.

**Bu 04-07 ning `0017` o'zgarishi TUFAYLI EMAS:** uchinchi disjunkt
`status = 'running'` talab qiladi, test esa FAQAT `pending` qator yozadi —
yuqoridagi o'lchovda u `FALSE`. Nosozlik `0015` dan beri mavjud va test
o'z `_NEAR` docstringida uni ochiq nomlaydi: *«test faqat yarim tunning
atigi o'n daqiqalik oynasida nozik bo'lib qoladi»*.

**Nima uchun bu rejada tuzatilmadi:** fayl `04-07` ning `files_modified`
idan tashqarida va tuzatish qarori (oynani kichraytirish, `freezegun`,
yoki sanani argument qilish) sinov metodikasiga tegadi.

**Egasi:** `04-12` (faza darvozasi) yoki `tests/tenancy` ga keyingi
tegadigan reja. **Tetik:** `npm run gate` ni 23:55–00:00 oralig'ida
ishga tushirish.

---

## 2. ✅ YOPILDI — `.env` ↔ `worker`/`scheduler` ↔ sozlama darvozasi uchburchagi

**Qayerda:** `compose.yaml` (`worker`/`scheduler`/`core-api` bloklari),
`.env.example:108-109`, `services/core-api/app/settings.py:44`

**O'lchangan:** `compose.yaml` `worker` va `scheduler` ga
`S3_ACCESS_KEY: ${S3_ACCESS_KEY}` ni **standartsiz** beradi, ya'ni ular
`.env` da HAQIQIY qiymat bo'lmasa ishga tushishda `ValidationError` bilan
yiqiladi. `.env.example` esa o'sha kalitlarni **bo'sh** beradi.

`Settings.model_config` da `env_file=".env"` va `tests` konteyneri
repozitoriyni `/app` ga mount qiladi — ya'ni dasturchining `.env` fayli
unit testlarga ko'rinadi.

**Bu rejada nima qilindi:** `test_snapshot_settings.py` ning ikki joyiga
`_env_file=None` qo'shildi, ya'ni sozlama darvozasi endi maydonning
STANDARTINI o'lchaydi va mahalliy fayldan mustaqil (commit `d8b71e5`).

**Qoldiq:** `.env.example` hali ham bo'sh kalit beradi, ya'ni uni
nusxalagan dasturchining `npm run up` i `worker`/`scheduler` da
yiqiladi va sabab faqat `docker compose logs` da ko'rinadi.
`ops/seaweedfs/README.md` da qiymatlar bor, lekin `.env.example` ular
bilan bog'lanmagan.

**Egasi:** `.env.example` ga keyingi tegadigan reja (`04-08` yoki `04-12`).

### ✅ Yopilishi (2026-08-05, `04-14` / T1)

`.env.example:108-109` bo'sh emas: ikkala kalit ham
`ops/seaweedfs/s3.json.example` dagi AYNAN o'sha
`NAMUNA-ALMASHTIRING-*` qiymatlarini tashiydi, ya'ni
`cp .env.example .env` qilgan yangi klon `npm run up` da yiqilmaydi.

**Darvoza:** `tests/unit/test_storage_config.py::test_env_example_matches_the_s3_config_example`
— da'vo **TENGLIK** sifatida yozilgan (yo'qlik sifatida emas: «bo'sh S3
satri yo'q» shaklidagi grep faylning O'Z izoh matni bilan to'qnashardi).
Yonida ikkita qo'shimcha darvoza: bo'shlik taqig'i
(`test_env_example_credentials_are_not_empty`) va parserning quyi
chegarasi (`test_env_example_parser_actually_sees_the_keys`).

**Bandning ASOSIY nosozligi qaytarilmadi:** darvoza `.env` FAYLINI
o'qimaydi — faqat ikki NAMUNA faylni solishtiradi. Aks holda u aynan shu
band o'lchagan sinfga (`tests` konteyneri dasturchining `.env` ini
ko'radi) qaytib tushardi va `_env_file=None` tuzatishini bekor qilardi.

⚠ **`compose.yaml` TEGILMADI.** `:-` bilan bo'sh standart berilmagani
ATAYIN va bu tuzatishdan keyin ham to'g'ri qaror bo'lib qoladi: kalitni
butunlay o'chirgan deploy ISHGA TUSHISHDA yiqilishi kerak. O'lchandi:
`docker compose --env-file .env.example config` chiqishida
`S3_ACCESS_KEY: NAMUNA-ALMASHTIRING-access` **3 marta** —
`core-api`, `worker`, `scheduler`.

---

## 3. ✅ YOPILDI — `ops/seaweedfs/s3.json` KATALOG bo'lib yaratilib qolgan edi

**Qayerda:** ish stantsiyasidagi holat (fayl `.gitignore` ostida).

Docker bind-mount manba fayli mavjud bo'lmaganda uni **katalog** qilib
yaratadi. Natijada `storage` konteyneri `-s3.config=/etc/seaweedfs/s3.json`
ni katalog sifatida ko'rardi.

**Bu rejada tuzatildi** (`rmdir` + `.example` dan fayl), lekin muammoning
O'ZI qaytishi mumkin: `ops/seaweedfs/README.md` da ogohlantirish yo'q va
`npm run up` ni fayl yaratilmasdan ishga tushirish uni qayta tug'diradi.

**Egasi:** `ops/seaweedfs/README.md` ga keyingi tegadigan reja.
**Taklif:** `npm run up` dan oldin `s3.json` ning FAYL ekanini tekshiradigan
bitta qatorli darvoza (`test_storage_config.py` da).

### ✅ Yopilishi (2026-08-05, `04-14` / T1)

`ops/seaweedfs/README.md` §2 ga `cp` buyrug'ining ostiga ⛔ bloki
qo'shildi: qadam `npm run up` DAN OLDIN bajarilishi shart, sabab
(Docker mavjud bo'lmagan bind-mount manbasini KATALOG qilib yaratadi) va
tuzatish yo'li (`rmdir` + qayta `cp`) yozilgan. §3 ga ikkinchi
ogohlantirish qo'shildi: `docker compose down -v` `seaweed` volume'ini va
u bilan birga BUCKETNI o'chiradi, ilova esa uni qayta yaratmaydi
(`Admin` amali ataylab berilmagan) — `s3.bucket.create` qo'lda
takrorlanadi.

⚠ **Yuqoridagi «Taklif» ATAYIN BAJARILMADI va sabab o'lchangan.**
`ops/seaweedfs/s3.json` `.gitignore` ostida: yangi klonda u UMUMAN
mavjud emas, ya'ni «bu yo'l FAYLmi?» darvozasi toza klonda **qizil**
bo'lardi va uni yashil qilish uchun har dasturchi test ishlatishdan
oldin faylni yaratishga majbur bo'lardi. Bundan tashqari u darvozani
mahalliy holatga bog'lardi — bu #2 o'lchagan aynan o'sha sinf. Shuning
uchun band **hujjat** bilan yopildi, darvoza bilan emas, va bu farq shu
yerda ochiq yoziladi.
