# cv-service — loyihaning IKKINCHI Python bog'liqlik to'plami

`cv-service` kamera kadridagi rasta zonalarining bandligini aniqlaydi:
ONNX Runtime bilan inference, `supervision.PolygonZone` bilan zona
verdikti, natija `occupancy_events` ga yoziladi.

| Nima | Qiymat |
|------|--------|
| Rol | `taskiq` **worker** (D-23) — HTTP xizmati EMAS |
| Navbat | `sbozor:cv` — `core-api` ning `sbozor:jobs` idan **ajratilgan** |
| Image | `services/cv-service/Dockerfile` — `dev` va `runtime` bosqichlari |
| Testlar | `services/cv-service/tests/`, `cv-tests` konteynerida (`npm run cv:test`) |
| Model | `ops/models/rfdetr-large.onnx` — build paytida `COPY` (D-24) |

---

## 1. ⚠⚠ Nega alohida `pyproject.toml` + `uv.lock` + `Dockerfile` (W0-2)

Repoda shu paytgacha **bitta** Python bog'liqlik to'plami bor edi.
`services/nvr-sim` ham `core-api` image'ining `dev` target'ini qayta
ishlatadi — ya'ni bu shakl loyihada **hech qachon qurilmagan**.

**Rad etilgan muqobil:** CV kutubxonalarini `core-api` ning `dev`
guruhiga yoki `packages/sbozor-core` ga olib kirish va mavjud `tests`
konteynerida sinash.

**Nega rad etildi — bu fikr emas, o'lchov.** `core-api`
`opencv` ni **ataylab** rad etadi va taqiq **mexanik**:

```python
# tests/unit/test_runtime_deps.py:91-94
    # D-13: sifat filtri uchun `Pillow` yetadi. `opencv` — `cv-service`
    # ning bog'liqligi (5-faza) va u runtime image'ga ~70 MB qo'shardi.
    "opencv-python",
    "opencv-python-headless",
```

Taqiq **ikkala guruhga** ham qo'llanadi va sabab o'sha testda yozilgan:
`uv add --dev` ham bitta `uv.lock` ni qayta hal qiladi. Ya'ni CV
kutubxonalarini `tests` konteyneriga olib kirish **o'lchangan darvozani
bo'shatish** bo'lardi — 5-fazani mavjud darvozani buzish bilan boshlash.

CLAUDE.md ning «aynan 3 ta servis» cheklovi **buzilmaydi**: `cv-service`
allaqachon uchlikning a'zosi (`core-api`, `cv-service`, `bot-service`).

**Nima baham ko'riladi:** `packages/sbozor-core` — modellar, enumlar,
tenant konteksti va jurnal. U **ikkala** manifestda ham `editable`
manba sifatida turadi, ya'ni sxema o'zgarganda ikkala servis ham darhol
ko'radi.

## 2. ⚠⚠ `rfdetr` bu yerda YO'Q va u qo'shilmaydi (D-04)

`torch` — `rfdetr` ning **ekstrasi emas, majburiy bog'liqligi** (~800 MB).
Ishlab chiqarish image'i `onnxruntime` (~15 MB) + oldindan eksport
qilingan `.onnx` bilan ishlaydi; eksport **alohida** `cv-train` muhitida,
ijara GPU'da bajariladi (retsept: `ops/models/README.md`).

PML litsenziyali variantlar (`rfdetr-plus` — XLarge/2XLarge) ham
**taqiq** (D-03).

Uchala taqiq ham `tests/unit/test_license_fence.py` da **uch qatlamda**
qulflangan:

| Qatlam | Nimani ko'radi |
|--------|----------------|
| manifest | `pyproject.toml` dagi **niyat** (ikkala guruh ham) |
| `uv.lock` | hal qilingan graf — **tranzitiv** tortishni ham |
| o'rnatilgan metadata | `LicenseRef-*` / AGPL **predikati** (nomlar ro'yxati emas) |

## 3. Testlar qayerda yuradi

```bash
npm run cv:test     # docker compose --profile test run --rm cv-tests pytest -q
npm run cv:lint     # ruff check + ruff format --check + mypy
```

Ikkalasi ham `npm run gate` zanjirida (`lint`/`test` dan keyin,
frontend'dan oldin).

* `cv-tests` — `cv-service` Dockerfile'ining **`dev`** target'i
  (`tests` ↔ `core-api` naqshining aynan takrori: yangi Dockerfile yo'q).
* `working_dir` — `/app/services/cv-service`, **`/app` emas**: `pytest`,
  `ruff` va `mypy` uchalasi ham shu katalogdagi `pyproject.toml` ni
  topishi shart, aks holda ular repo ildizidagi konfiguratsiyani olib,
  `core-api` ning to'plamini shu image'da ishga tushirardi.
* `-m "not model"` — **standart holat**: haqiqiy `.onnx` artefaktini
  talab qiladigan testlar (`@pytest.mark.model`) fazani bloklamaydi
  (`core-api` dagi `-m "not hardware"` qarorining takrori).
* `tests/` ning o'zi **paket emas** (`__init__.py` yo'q) — repo
  ildizidagi `tests/` bilan aynan bir xil shakl. Fixture'lar
  `from fixtures.detections import …` bo'lib import qilinadi.

## 4. Konteyner nima yuritadi va healthcheck nega yo'q

`compose.yaml` dagi `cv-service` **sof worker**:

```yaml
command: ["taskiq", "worker", "app.worker:broker", "--workers", "1"]
```

`healthcheck` **ataylab yozilmagan** — `scheduler` blokidagi o'lchangan
qarorning aynan takrori: jarayon tirikligi «aniqlash bajarilyaptimi?»
savoliga **javob bermaydi**. `nc -z` uchun ataylab port ochish o'z portiga
o'zi javob beradigan yuza bo'lardi, ya'ni **yolg'on ishonch**.

Yagona ishonchli signal — bazadagi natija: `cv_detect` yurak urishi va uni
o'qiydigan `/internal/self-check` (`core-api` ning
`EXPECTED_COMPONENTS` reyestri). Komponent **bugundan** reyestrda va u
`never_seen` holatida — 05-08 uni yozadigan qiladi.

`app/main.py` (minimal FastAPI, faqat `/healthz`) D-23 talab qilgan health
yuzasi sifatida saqlanadi, lekin bugun uni **birorta konteyner
yuritmaydi**. U sinalmagan kod emas:
`tests/unit/test_sentry_entrypoints.py::test_health_surface_also_installs_sentry`
uni obyekt darajasida o'lchaydi.

## 5. Kuzatuv — ikkita darvoza, ikkita qatlam

`compose.yaml` `cv-service` ga `SENTRY_DSN` beradi, ya'ni
`tests/unit/test_sentry_processes.py` **avtomatik** talab qo'yadi:
o'sha jarayon `init_sentry()` ni chaqirishi shart.

⚠ Root darvoza `core-api` image'ida yuradi va u bu paketni import qila
**olmaydi**: paket nomi (`app`) `core-api` niki bilan to'qnashadi, ya'ni
import jimgina noto'g'ri modulni qaytarardi. Shuning uchun:

| Darvoza | Qayerda | Nimani o'lchaydi |
|---------|---------|------------------|
| `tests/unit/test_sentry_processes.py` | `tests` konteyneri | begona kod ildizi uchun **manba** darajasi: fayl, atribut, ilmoq, `init_sentry(` |
| `services/cv-service/tests/unit/test_sentry_entrypoints.py` | `cv-tests` konteyneri | **obyekt** darajasi: brokerning `WORKER_STARTUP` reyestri va FastAPI `lifespan` zanjiri |

Ikkalasi ham `compose.yaml` dan **hosila** — servis nomlari ro'yxat
sifatida hech qayerda yozilmagan (§S-10).
