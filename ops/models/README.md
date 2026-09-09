# ONNX artefakti — aniqlagichning yagona haqiqat manbai (W0-12, D-24)

`cv-service` **hech qachon `rfdetr` ni o'rnatmaydi**. U faqat
`onnxruntime` ni yuritadi va oldindan eksport qilingan **bitta `.onnx`
faylni** o'qiydi. Bu katalog o'sha faylning kelib chiqishini, nomini va
joyini yozadi.

| Nima | Qiymat |
|------|--------|
| Fayl nomi | `ops/models/rfdetr-large.onnx` |
| Model varianti | **`RFDETRLarge`** (D-08) |
| Litsenziya | **Apache-2.0** (kod ham, vazn ham) |
| Image'ga qanday kiradi | `Dockerfile` ning `runtime` bosqichida `COPY` (D-24) |
| Repoda saqlanadimi | **Yo'q** — `.gitignore` da `ops/models/*.onnx` |

---

## 1. ⚠⚠ Nega `cv-service` ga `rfdetr` o'rnatilmaydi (D-04)

`rfdetr` **Apache-2.0** va u to'g'ri tanlov — lekin **`torch` uning
ekstrasi emas, MAJBURIY bog'liqligi** (CLAUDE.md «Version Compatibility»,
2026-08-05 da tekshirilgan). Ya'ni `uv add rfdetr` ishlab chiqarish
image'iga **~800 MB** qo'shadi, ONNX Runtime esa aynan o'sha inferensni
**~15 MB** da bajaradi.

Shuning uchun ish ikkiga bo'lingan:

```
cv-train  (ijara GPU, oyiga bir marta)   ->  rfdetr[train,onnx] + torch  ->  .onnx
cv-service (Contabo VPS, har kuni)       ->  onnxruntime + .onnx
```

Bu **intizom emas, darvoza**: `tests/unit/test_license_fence.py`
`rfdetr` ni ham, `torch` ni ham, `rfdetr-plus` ni ham
`services/cv-service/pyproject.toml` va `uv.lock` da **mexanik rad
etadi**.

## 2. ⚠ `RFDETRLarge` VA UNDAN KATTASI EMAS (D-03, D-08)

| Variant | Litsenziya | Ruxsat |
|---------|-----------|--------|
| Nano / Small / Medium / **Large** | Apache-2.0 | ✅ |
| **XLarge / 2XLarge** | **PML 1.0** (`rfdetr-plus`) | ⛔ **TAQIQ** |

1.9.x dan boshlab PML variantlari **alohida distributivda** yashaydi —
`rfdetr-plus` (`license_expression = LicenseRef-PML-1.0`) va u **faqat**
`rfdetr[plus]` ekstrasi orqali tortiladi. Ya'ni «XLarge ishlatmaymiz»
degan intizom **lockfile invariantiga** aylandi: `[plus]` yozilgan zahoti
`uv.lock` ga `rfdetr-plus` bloki tushadi va litsenziya devorining
ikkinchi qatlami qizaradi.

`RFDETRLarge` **aniqlik uchun** tanlangan, tezlik uchun emas: 175
kadr/kun/bozor da eng yomon holat ham ~47 daqiqa CPU/kun, ya'ni kechikish
bu yerda chegara emas (D-08).

## 3. Eksport retsepti — **alohida image, ijara GPU**

Quyidagilar `cv-service` image'ida **bajarilmaydi** va uning bog'liqlik
to'plamiga **qo'shilmaydi**.

```bash
# Ijara GPU mashinasida, alohida vaqtinchalik muhitda:
uv venv --python 3.13 && . .venv/bin/activate
uv pip install "rfdetr[train,onnx]==1.9.1"      # ⚠ `[plus]` EMAS — PML 1.0

python - <<'PY'
from rfdetr import RFDETRLarge

model = RFDETRLarge()          # fine-tune qilingan vaznlar bo'lsa: RFDETRLarge(pretrain_weights=...)
model.export(format="onnx")    # -> output/inference_model.onnx
PY

# Nomni loyiha konvensiyasiga keltiring va VPS ga ko'chiring:
mv output/inference_model.onnx rfdetr-large.onnx
scp rfdetr-large.onnx <vps>:/srv/sbozor/ops/models/rfdetr-large.onnx
```

Fayl joyiga qo'yilgach image qayta quriladi (`COPY` build paytida
bajariladi):

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml build cv-service && docker compose up -d cv-service
```

## 4. ⚠ Nega repoda saqlanmaydi

Artefakt **yuzlab megabayt**, `git-lfs` esa bu loyihada **yo'q**. Uni
oddiy git obyekti sifatida commit qilish har bir klonni va har bir CI
yugurishini o'sha hajm bilan yuklardi va tarixdan uni o'chirish
`filter-repo` talab qilardi.

Shuning uchun:

* `.gitignore` da — `ops/models/*.onnx`;
* `.gitattributes:31` da `*.onnx binary` **allaqachon bor** va u
  **o'zgartirilmaydi** — bu boshqa qaror (agar biror kun kichik artefakt
  commit qilinsa, diff shovqin bermasligi uchun);
* bu `README.md` esa **commit qilinadi** va u katalogni mavjud qiladi,
  ya'ni `COPY ops/models/ /app/models/` artefaktsiz ham **build bo'ladi**.

> **Build o'tadi, ishga tushish esa yiqiladi — va bu ATAYIN.** Artefakt
> yo'q bo'lsa `cv-service` `Settings` ning `field_validator` ida
> **ishga tushishda** to'xtaydi va sabab `docker compose logs cv-service`
> da ochiq yoziladi. Muqobil (birinchi kadrda yiqilish) nosozlikni
> ertalab 06:00 ga — hech kim qaramayotgan paytga — surib qo'yardi
> (05-PATTERNS §4.1).

## 5. ⚠ Ish paytida yuklab olish YO'Q (D-24)

Model faylini konteyner ishga tushganda internetdan olish **qilinmaydi**:

* start **tarmoqsiz** va **takrorlanadigan** bo'lishi kerak — Contabo
  qayta ishga tushirilganda yoki O'zbekiston hostingiga ko'chishda tashqi
  URL mavjudligiga tayanish yangi nosozlik nuqtasi bo'lardi;
* yuklab olingan fayl **tekshirilmagan** bo'lardi — T-05-08 («soxta ONNX
  artefakti») aynan shu yo'l bilan ochilardi. Bugungi dispozitsiya —
  `accept`: artefaktni **ops qo'yadi**, manba va retsept esa shu faylda
  nomma-nom yozilgan.
