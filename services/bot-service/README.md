# bot-service — loyihaning UCHINCHI Python bog'liqlik to'plami

`bot-service` sotuvchi va direktor Telegram botlarini yuritadi: sotuvchi
o'z qoldig'i va to'lov tarixini so'raydi, direktor ertalabki dayjest va
kechki nomuvofiqlik hisobotini oladi.

| Nima | Qiymat |
|------|--------|
| Rol | aiogram **long-poller** (DQ-1) — HTTP xizmati EMAS |
| Ishga tushirish | `python -m app.main` |
| Ma'lumot manbai | ⛔ **FAQAT** `core-api` ning `/internal/bot/*` yuzasi (D-10) |
| Baza | ⛔ **YO'Q** — bot Postgres'ni ko'rmaydi (D-08/1) |
| FSM ombori | Valkey **`db 1`** — `core-api` ning `db 0` idan **ajratilgan** |
| Image | `services/bot-service/Dockerfile` — `dev` va `runtime` bosqichlari |
| Testlar | `services/bot-service/tests/`, `bot-tests` konteynerida (`npm run bot:test`) |

---

## 1. ⚠⚠ Nega alohida `pyproject.toml` + `uv.lock` + `Dockerfile` (D-09)

Bu **qulaylik emas, majburiyat**. `aiogram 3.30.0` ning metadatasi ikkita
qattiq shift beradi va ikkalasi ham `core-api` ning pinlari bilan
**to'qnashadi**:

| Paket | `aiogram 3.30.0` talabi | `core-api` pini | Natija |
|---|---|---|---|
| `redis[hiredis]` | `>=6.2.0,<8` | **`==8.0.1`** | ⛔ **To'qnashuv** |
| `pydantic` | `>=2.4.1,<2.14` | `==2.13.4` | Bugun mos, ertaga emas |

`redis` qatori bitta lockfaylda hal qilib bo'lmaydigan holat: `aiogram`
ni `core-api` ga qo'shish `redis` ni **7.x ga tushirardi** va
`app/security/ratelimit.py` bilan sessiya keshi jimgina eskiroq klientda
ishlab qolardi — ya'ni buzilish bot kodida emas, **butunlay boshqa
joyda** chiqardi.

Bu **`arq` darsining aynan takrori** (D-06) va u shu repoda allaqachon
mexanik qulflangan:

```python
# tests/unit/test_runtime_deps.py::test_redis_pin_is_not_downgraded
assert specs == ["redis[hiredis]==8.0.1"], (
    "`redis` pini o'zgargan: ... pasayish `arq` sinfidagi to'qnashuv "
    "sodir bo'lganini bildiradi"
)
```

Shuning uchun `bot-service` **o'z** manifesti va **o'z** `uv.lock` i bilan
keladi. `pydantic` qiymati bugun `core-api` niki bilan bir xil (`2.13.4`),
lekin u **alohida lockfaylda** yashaydi: `pydantic 2.14` chiqqan kuni
`core-api` ko'chishi mumkin, `bot-service` esa **yo'q**.

CLAUDE.md ning «aynan 3 ta servis» cheklovi **buzilmaydi**: `bot-service`
allaqachon uchlikning a'zosi (`core-api`, `cv-service`, `bot-service`).
`bot-tests` — **yangi servis emas**, o'sha image'ning boshqa entrypointi
(`cv-tests` ↔ `cv-service` naqshining aynan takrori).

## 2. ⛔ Bu yerga QO'SHILMAYDIGAN paketlar va sabab (D-08/1)

`pyproject.toml` ning docstringida to'liq yozilgan, qisqasi:

| Paket | Nega yo'q |
|---|---|
| `sqlalchemy`, `asyncpg` | ⛔ **Ikkinchi RLS yuzasi ochilmaydi.** Bot Telegram'dan kelgan **autentifikatsiya qilinmagan** oqim ostida turadi (T-07-01) |
| `sbozor-core` | ⚠ Vasvasa eng katta band — unda enumlar va pul turi bor. Lekin u `models/` orqali **SQLAlchemy'ni tortadi** va yuqoridagi taqiqni bilvosita buzardi |
| `taskiq`, `taskiq-redis` | Bot job bajarmaydi — u **faqat kiruvchi** oqimni qabul qiladi. Jo'natish `worker` ning `notify.outbox_tick` ida qoladi |
| `phonenumbers` | ⛔ E.164 normalizatsiyasi **`core-api` da** (D-25): ikki joyda normallashtirish ikki xil natija bergan kunda bog'lanish **jimgina** buzilardi |

Taqiq **izoh emas, darvoza**:
`services/bot-service/tests/unit/test_runtime_deps.py` har birini **ikki
qatlamda** o'lchaydi — `importlib.metadata.distribution(...)` va haqiqiy
`import` xulqi.

## 3. ⛔⛔ BIR TOKENGA AYNAN BITTA POLLER

Bu bo'lim **operatsion xavfsizlik bandi**, tavsiya emas.

Telegram Bot API da bir tokenga **faqat bitta** `getUpdates` oqimi
bo'lishi mumkin. Ikkinchisi `409 Conflict` oladi **yoki** update'ni
**tortib oladi**.

⛔ **`compose.yaml` da `deploy.replicas` YOZILMAYDI.** Compose darvozasi
buni sanaydi: `docker compose config | grep -c replicas` → `0`.

⚠ **Eng qimmat amaliy holat — dev mashina:**

| Nima bo'ladi | Ko'rinishi |
|---|---|
| Dasturchi `.env` ga **prod** tokenini qo'yadi va lokalda `bot-service` ni ko'taradi | Lokal bot ishlaydi |
| Prod bot o'sha update'larni **olmay qoladi** | ⛔ **Hech qanday xato yo'q**: konteyner `Up`, jurnal toza, sotuvchilar javob olmaydi |

Shuning uchun:

* lokal ishlab chiqishda **ALOHIDA dev bot tokeni** olinadi
  (`.env.example` dagi ogohlantirish bandi);
* `TelegramConflictError` **jim yutilmaydi** — `log.critical` + Sentry +
  qayta ko'tariladi, ya'ni konteyner yiqiladi va sabab **ko'rinadi**
  (`app/main.py`, Pitfall 5).

⚠ `TELEGRAM_BOT_TOKEN` **bir xil token ikki maqsadda** ishlatiladi: alert
supurgisi (`core-api`/`worker`) va sotuvchi boti (A1). Bu ongli qaror —
ikkinchi token ikkinchi bot profili, ikkinchi nom va foydalanuvchida
chalkashlik demakdir.

## 4. ⚠ Nega FSM ombori `db 1`

`core-api` va `cv-service` Valkey ning **`db 0`** ida ishlaydi va u yerda
uchta narsa yashaydi: login rate-limit sanagichlari, sessiya keshi va
`sbozor:jobs` navbati.

aiogram FSM kalitlarini o'sha makonga qo'shish ikki xavf tug'dirardi:

1. `FLUSHDB` (yoki nom to'qnashuvi) xatosi **ikki tizimni birdan**
   yiqitardi — bitta noto'g'ri buyruq bot dialoglarini ham, navbat va
   rate-limitni ham o'chirardi;
2. «Kim bu kalitni yozdi?» savoli har nosozlikda qaytardi.

⚠ `cache` konteyneri `--save "" --appendonly no` bilan ishlaydi, ya'ni
FSM holati qayta ko'tarilganda **yo'qoladi**. Bu qonuniy: FSM — bir necha
soniyalik dialog bosqichi, biznes holati emas. Biznes holati Postgres'da
(`vendor_telegram_bindings`) va u **bu servisga tegishli emas**.

## 5. ⛔ Bot bugun `/start` ga JAVOB BERMAYDI

`app/main.py` da `dp` **bo'sh router** bilan ishga tushadi — handlerlar bu
rejada **yozilmagan**, ular 07-11 niki. Skelet ulardan oldin yoziladi,
chunki uchinchi servisning tug'ilishi `compose.yaml`, `package.json` va
`tests/unit/test_sentry_processes.py` darvozasiga tegadi; bu uchtasi
handlerlar bilan bir commitda aralashsa, darvozaning qizarishi «handler
buzuq» deb o'qilardi.

Ya'ni **bugungi to'g'ri xulq**: konteyner ko'tariladi, Telegram'ga
ulanadi, update oladi va **hech nima qilmaydi**.

## 6. Kuzatuv — ikkita darvoza, ikkita qatlam

`compose.yaml` `bot-service` ga `SENTRY_DSN` beradi, ya'ni
`tests/unit/test_sentry_processes.py` **avtomatik** talab qo'yadi: o'sha
jarayon `init_sentry()` ni chaqirishi shart.

⚠ **Bu faza darvozani ATAYIN buzdi va o'sha yerda tuzatdi** (Pitfall 3):
aiogram ning ishga tushish ilmog'i na `TaskiqEvents.*`, na `lifespan=`
markeriga mos kelmaydi, va `python -m app.main` buyrug'ida
`modul:atribut` shaklidagi token **yo'q**. Darvoza **kengaytirildi**
(`FOREIGN_HOOK_MARKERS` ga `dp.startup.register`, (b) bosqichiga `-m`
shakli) va kengaytma **nazorat testi** bilan qulflandi. ⛔ Testni
o'chirish yoki `skip` shoxi qo'shish taqiqlanadi.

| Darvoza | Qayerda | Nimani o'lchaydi |
|---------|---------|------------------|
| `tests/unit/test_sentry_processes.py` | `tests` konteyneri | begona kod ildizi uchun **manba** darajasi: fayl, atribut, ilmoq, `init_sentry(` |
| `services/bot-service/tests/unit/test_sentry_entrypoints.py` | `bot-tests` konteyneri | **reyestr** darajasi: `dp.startup` observeriga haqiqatan ro'yxatga olingan callback'lar |

Ikkalasi ham `compose.yaml` dan **hosila** — servis nomlari ro'yxat
sifatida hech qayerda yozilmagan (§S-10).

## 7. Testlar qayerda yuradi

```bash
npm run bot:test     # docker compose --profile test run --rm bot-tests pytest -q
npm run bot:lint     # ruff check + ruff format --check + mypy
```

Ikkalasi ham `npm run gate` zanjirida (`cv:test` dan keyin).
⛔ **`gate:fast` ga QO'SHILMAYDI**: `bot-service` mustaqil kod bazasi va
uning konteyner ko'tarilishi 200 s byudjetining ~10 % ini bir zarbada
yeydi (`07-VALIDATION.md` byudjet bandi).

* `bot-tests` — shu Dockerfile'ning **`dev`** target'i (yangi Dockerfile
  yo'q, yangi servis ham yo'q);
* `working_dir` — `/app/services/bot-service`, **`/app` emas**: `pytest`,
  `ruff` va `mypy` uchalasi ham shu katalogdagi `pyproject.toml` ni
  topishi shart;
* ⛔ `bot-tests` ga `SENTRY_DSN` **berilmaydi** — test jarayonining
  istisnolari ishlab chiqarish Sentry loyihasiga tushmasligi kerak;
* ⛔ `depends_on` **yo'q** — testlar tarmoqqa chiqmaydi.

## 8. `uv.lock` xostda emas, konteynerda generatsiya qilinadi

```bash
docker run --rm -v "$PWD:/app" -w /app/services/bot-service \
  ghcr.io/astral-sh/uv:0.11.33-python3.13-trixie-slim uv lock
```

⚠ `aiogram[fast]` `uvloop` ni tortadi va uning **Windows g'ildiragi yo'q**
— xostda `uv lock` manbadan qurishga urinib yiqiladi. Bu **xost
artefakti, paket nuqsoni emas**: konteyner bazasi `python:3.13-slim-trixie`
(Debian/glibc) va PyPI'da `uvloop-0.22.1-cp313-…-manylinux_2_28_x86_64.whl`
**mavjud** (07-RESEARCH § Package Legitimacy Audit).

⛔ Shu sababdan Dockerfile bazasi **Alpine emas**: musl ostida `uvloop`
uchun g'ildirak yo'q.

## 9. Deploy

```bash
docker compose up -d --force-recreate bot-service
```

⚠ `--force-recreate` **ataylab**: konteyner yangi image bilan qayta
yaratilmasa, eski jarayon eski token/sozlama bilan pollingda qolib
ketardi va hech qanday xato chiqmasdi.
