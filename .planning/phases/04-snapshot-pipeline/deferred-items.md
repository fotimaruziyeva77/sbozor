# 4-faza — doiradan tashqarida topilgan bandlar

Bu fayl **tuzatilmagan** topilmalar reyestri. Har band uchun: qayerda,
nima o'lchangan, nima uchun bu rejada tegilmagan, egasi kim.

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

## 2. `.env` ↔ `worker`/`scheduler` ↔ sozlama darvozasi uchburchagi

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

---

## 3. `ops/seaweedfs/s3.json` KATALOG bo'lib yaratilib qolgan edi

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
