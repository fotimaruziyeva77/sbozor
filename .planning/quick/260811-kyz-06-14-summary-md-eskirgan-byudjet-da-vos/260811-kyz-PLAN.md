---
quick_id: 260811-kyz
phase: quick
plan: 260811-kyz
type: execute
wave: 1
depends_on: []
autonomous: true
requirements: [F-2]
files_modified:
  - .planning/phases/06-billing-va-kassir/06-14-SUMMARY.md

must_haves:
  truths:
    - "06-14-SUMMARY.md ni SO'ZMA-SO'Z o'qigan ijrochi `gate` byudjeti O'LCHANGANini va `nyquist_compliant: true` ekanini ko'radi"
    - "Har to'rt eskirgan joyning ASL MATNI faylda qoladi — tarix o'chirilmaydi"
    - "Har bir yopilish aniq raqam (1703/1733/1899 s · 2300 s · 200 s) va yopgan artefakt nomi bilan ko'rsatiladi"
    - "`## Ochiq bandlar` ro'yxatining 1-bandi endi ⛔ bilan emas, ✅ **YOPILDI** bilan boshlanadi"
    - "`deferred-items.md` ning 3- va 9-bandlari OCHIQ deb QOLADI — ular 6-fazaniki emas va ularga tegilmaydi"
    - "Frontmatter YAML sintaksisi buzilmaydi — `decisions` hamon to'rtta bir qatorli qo'shtirnoqli satr"
    - "Faqat bitta fayl o'zgaradi"
  artifacts:
    - path: ".planning/phases/06-billing-va-kassir/06-14-SUMMARY.md"
      provides: "Yopilgan holatga moslangan 06-14 SUMMARY (tarix saqlangan holda)"
      contains: "YOPILDI"
  key_links:
    - from: ".planning/phases/06-billing-va-kassir/06-14-SUMMARY.md"
      to: "package.json `//gate-budget` / `//gate-fast-budget`"
      via: "o'lchangan raqamlarga so'zma-so'z havola (1703/1733/1899 s · 2300 s · 200 s)"
      pattern: "1703|2300"
    - from: ".planning/phases/06-billing-va-kassir/06-14-SUMMARY.md"
      to: ".planning/phases/06-billing-va-kassir/06-VALIDATION.md"
      via: "`nyquist_compliant: true` bayrog'iga havola"
      pattern: "nyquist_compliant: true"
    - from: ".planning/phases/06-billing-va-kassir/06-14-SUMMARY.md"
      to: ".planning/phases/06-billing-va-kassir/deferred-items.md"
      via: "7-band = yopilish dalili (19-qator)"
      pattern: "deferred-items.md. 7-band"
---

<objective>
`06-14-SUMMARY.md` to'rt joyda «gate byudjeti O'LCHANMADI» va
«`nyquist_compliant` HAMON false» deb yozadi, amalda esa byudjet o'lchangan
(1703/1733/1899 s, exit 0), qayta belgilangan (1250 → 2300 s) va bayroq `true`.
Xavfsizlik auditining **F-2** topilmasi: SUMMARY o'z holatidan orqada qolgan va uni
so'zma-so'z o'qigan keyingi ijrochi 6-fazani ochiq deb hisoblardi.

Purpose: hujjat yolg'on «ochiq band» signalini bermasin — lekin **tarix ham
o'chirilmasin**: SUMMARY o'sha paytdagi holatni qayd etadigan artefakt.
Output: bitta fayl — `06-14-SUMMARY.md` — asl matn joyida, ustiga yopilish
eslatmalari qo'shilgan holda.
</objective>

<execution_context>
@C:/Users/hayda/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/hayda/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-billing-va-kassir/06-14-SUMMARY.md
@.planning/phases/06-billing-va-kassir/deferred-items.md
@CLAUDE.md
</context>

<verified_facts>
Bu raqamlar **mustaqil tekshirilgan** — tahrirlarda AYNAN shular ishlatiladi,
qayta o'lchash yoki taxmin qilish YO'Q:

| Fakt | Qiymat | Manba (tekshirildi) |
|---|---|---|
| `gate` uch o'lchov | **1703 / 1733 / 1899 s**, uchalasi ham exit 0 | `package.json::"//gate-budget"` · `deferred-items.md:19` |
| `gate` tarqoqligi | **196 s** = eng yomonning **10,3 %** | `package.json::"//gate-budget"` |
| `gate` yangi byudjeti | **2300 s** (1899 × 1,20 = 2278,8 → 50 ga yuqoriga) | `package.json` `//gate-budget` **va** `06-VALIDATION.md:94` — BIR XIL |
| `gate` eski byudjeti | **1250 s** (05-15 niki) | `package.json::"//gate-budget"` |
| `gate:fast` o'lchovlari | **160 / 154 / 152 s**, tarqoqlik 8 s (5,0 %) | `package.json::"//gate-fast-budget"` |
| `gate:fast` byudjeti | **180 → 200 s** (160 × 1,20 = 192 → 200) | `package.json::"//gate-fast-budget"` |
| Validatsiya bayroqlari | `status: complete` · `nyquist_compliant: true` · `wave_0_complete: true` | `06-VALIDATION.md:1-6` |
| Imzo darvozasi | `node scripts/check-validation-signoff.mjs` → **exit 0** | yugurtirildi |
| O'sish sababi | to'plamning o'sishi: 173 backend testi, vitest **620 → 717**, uchta yangi SSG marshruti — **ifloslanishdan EMAS** | `package.json::"//gate-budget"` |
| `deferred-items.md` **7-band** | ✅ **TO'LIQ YOPILDI**: to'lqin 7 post-merge, **so'ng to'lqin 9 dan keyin to'liq `gate` uch marta** (1703/1733/1899 s, exit 0) | `deferred-items.md:19` |
| `deferred-items.md` **3-band** (SUMMARY havola qiladigani) | ⚠ **HAMON OCHIQ** — `PUT /api/v1/camera-zones` ning `QUERY_PARAM_ROUTES` istisnosi, **05-06 dan meros**, `✅` belgisi YO'Q | `deferred-items.md:10` |
| `deferred-items.md` **9-band** | ⚠ **HAMON OCHIQ** — ism joini, 8-fazaning hisobot yuzasi, `✅` belgisi YO'Q | `deferred-items.md:21` |

⛔ **TUZOQ — `deferred-items.md` da «3» raqami IKKI MARTA ishlatilgan** (fayl ikki
blokdan iborat, raqamlar takrorlanadi): **10-qatordagi** 3-band (camera-zones,
05-06 merosi) **OCHIQ**; **14-qatordagi** 3-band (`gate` ning frontend yarmi)
to'lqin 5 da yopilgan, ya'ni 06-14 yozilishidan **OLDIN** — SUMMARY unga umuman
havola qilmaydi. SUMMARY ning 379-qatoridagi «3 va 9 **boshqa fazalarniki**» izohi
**10-qatordagini** ko'rsatadi va u **TO'G'RI**. ⛔ «3-band YOPILDI» deb yozish —
biz tuzatayotgan nuqsonning AYNAN takrori bo'lardi. **3- va 9-bandlarga
TEGILMAYDI**; 379-qatorda eskirgan YAGONA narsa — 7-band haqidagi «**qisman**
yopildi» qaydi.
</verified_facts>

<tasks>

<task type="auto">
  <name>Task 1: 06-14-SUMMARY.md ning beshta eskirgan da'vosini yopilgan holatga moslash</name>
  <files>.planning/phases/06-billing-va-kassir/06-14-SUMMARY.md</files>
  <action>
Faqat shu faylni tahrir qil. Quyidagi `<tahrir_matnlari>` bo'limidagi T-1…T-5
bloklari — **tayyor matn**: ularni o'ylab topma, ko'chirib qo'y (raqamlar
`<verified_facts>` dan keladi va ular allaqachon tekshirilgan).

⛔ **TARIXNI O'CHIRMA.** Har bir eskirgan da'voning asl matni faylda **qoladi**;
ustiga yopilish eslatmasi **qo'shiladi**. Asl jumlalarni qayta yozma, qisqartirma
yoki «to'g'rilama».

⛔ **Faylning O'Z konvensiyasi:** yopilish markeri AYNAN `✅ **YOPILDI — ...**`
(365-qatordagi 2-band va `deferred-items.md` shu naqshni ishlatadi). Yangi uslub
o'ylab topilmaydi. Frontmatterda esa (T-1) markdown emas — YAML string ichida
`— KEYIN YOPILDI (...)` shakli.

⛔ **YANGI DA'VO QO'SHMA.** Faqat `<verified_facts>` da turgan faktlar yoziladi.
Ayniqsa T-5 da: `deferred-items.md` ning **3- va 9-bandlari OCHIQ bo'lib qoladi**
va ularning holati o'zgartirilmaydi — ular 6-fazaniki emas.

**Tartib:** tahrirlarni **pastdan yuqoriga** qo'lla (T-5 → T-4 → T-3c → T-3b →
T-3a → T-2 → T-1), shunda qator raqamlari siljimaydi. Har birini noyob anchor
satr bo'yicha qil.

**Anchorlar (joriy holatdagi qator raqamlari):**
- T-1 → 41-qator: `  - "nyquist_compliant HAMON false — ...` (ALMASHTIRILADI)
- T-2 → 55-qatordan keyin, 57-qatordagi `---` dan oldin (QO'SHILADI)
- T-3a → 226-qator sarlavhasi `## ⛔ Byudjet — O'LCHANMADI (ochiq band)` (KENGAYTIRILADI)
- T-3b → yangi sarlavhadan keyin, `⛔ **Bu bo'limni to'g'ri o'qing:` xatboshisidan OLDIN (QO'SHILADI)
- T-3c → `**Yopish yo'li (bir qadam):**` xatboshisidan keyin, `**Bu rejada TO'LIQ yugurgan` dan oldin (QO'SHILADI)
- T-4 → 363-364-qatorlar, `## Ochiq bandlar` ning 1-bandi (ALMASHTIRILADI)
- T-5 → 378-379-qatorlar, `## Ochiq bandlar` ning 5-bandi (ALMASHTIRILADI)

**T-5 nega kiradi va qamrovi NEGA TOR:** 379-qator «7-band bu rejada **qisman**
yopildi — backend darvozasi yugurtirildi» deydi. `deferred-items.md:19` esa endi
uni **TO'LIQ** yopilgan deb yozadi (to'lqin 9 dan keyin to'liq `gate` uch marta).
Ya'ni bu ham F-2 sinfi — lekin **faqat 7-band bo'yicha**. O'sha qatordagi «3 va 9
boshqa fazalarniki» qismi **TO'G'RI va TEGILMAYDI** (`<verified_facts>` dagi
TUZOQ eslatmasini o'qi: `deferred-items.md` da «3» raqami ikki marta ishlatilgan).

**Formatlash qoidalari (darvoza shularga tayanadi):**
- Faylning ~80 belgili qator kengligiga ergash; boshqa joylarni **qayta
  formatlama** (bo'sh o'zgarish bo'lmasin).
- T-1 — **bitta qator**, ichida **qo'shtirnoq YO'Q** (`"` ishlatma; `package.json`
  izohiga havola qilganda backtick ishlat). YAML sintaksisi buzilmasin.
- Quyidagi iboralar **bitta qatorda butun qolsin** (grep darvozasi ular bo'yicha
  o'lchaydi): `yagona bajarilmagan qabul mezoni` · `3-, 7- va 9-bandlar` ·
  `Byudjet — O'LCHANMADI (ochiq band)` · `nyquist_compliant HAMON false` ·
  `3- va 9-bandlar HAMON OCHIQ`.
- `^1. ✅ **YOPILDI` — `## Ochiq bandlar` ning 1-bandi shu bilan boshlansin.

⛔ **Boshqa hech qanday faylga tegilmaydi**: `services/`, `frontend/`, `tests/`,
`migrations/`, `packages/`, `package.json`, `06-VALIDATION.md`,
`deferred-items.md`, `ROADMAP.md`, `06-SECURITY.md` — TEGILMAYDI. `<verify>` ning
birinchi darvozasi shuni o'lchaydi va u **`git add` dan OLDIN** yugurtiriladi.
  </action>
  <verify>
    <automated>
f=.planning/phases/06-billing-va-kassir/06-14-SUMMARY.md
# 0) Qamrov: FAQAT bitta fayl o'zgargan (git add dan OLDIN yugurtiriladi;
#    kuzatilmagan .docx/.json fayllar git diff ga kirmaydi)
test "$(git diff --name-only | tr -d '\r')" = "$f" || { echo "FAIL: qamrov"; exit 1; }
# 1) TARIX SAQLANDI — to'rt+bir asl da'vo hamon joyida (har biri AYNAN 1 marta)
test "$(grep -c 'nyquist_compliant HAMON false' "$f")" = 1 || { echo "FAIL: T-1 tarixi"; exit 1; }
test "$(grep -c "byudjeti esa O'LCHANMADI" "$f")" = 1 || { echo "FAIL: T-2 tarixi"; exit 1; }
test "$(grep -c "Byudjet — O'LCHANMADI (ochiq band)" "$f")" = 1 || { echo "FAIL: T-3 tarixi"; exit 1; }
test "$(grep -c 'yagona bajarilmagan qabul mezoni' "$f")" = 1 || { echo "FAIL: T-4 tarixi"; exit 1; }
test "$(grep -c '3-, 7- va 9-bandlar' "$f")" = 1 || { echo "FAIL: T-5 tarixi"; exit 1; }
test "$(grep -oi "o.lchanmadi" "$f" | wc -l | tr -d '[:space:]')" -ge 5 || { echo "FAIL: tarix qisqardi"; exit 1; }
# 2) YOPILISH QO'SHILDI — kutilgan 9 ta (3 tasi asl matnda edi), quyi chegara 8
test "$(grep -o 'YOPILDI' "$f" | wc -l | tr -d '[:space:]')" -ge 8 || { echo "FAIL: YOPILDI markerlari"; exit 1; }
# 3) YOPILISH RAQAM VA ARTEFAKT BILAN — bo'sh da'vo yetarli emas
test "$(grep -o '1703' "$f" | wc -l | tr -d '[:space:]')" -ge 4 || { echo "FAIL: o'lchov raqami"; exit 1; }
test "$(grep -o '2300' "$f" | wc -l | tr -d '[:space:]')" -ge 4 || { echo "FAIL: yangi byudjet"; exit 1; }
test "$(grep -c 'nyquist_compliant: true' "$f")" -ge 2 || { echo "FAIL: bayroq havolasi"; exit 1; }
# 4) Ochiq bandlar ro'yxatining 1-bandi endi ⛔ emas, ✅ YOPILDI bilan boshlanadi
test "$(grep -c '^1\. ✅ \*\*YOPILDI' "$f")" = 1 || { echo "FAIL: 1-band markeri"; exit 1; }
# 5) T-5 QAMROVI: 7-band TO'LIQ yopildi, 3- va 9-bandlar OCHIQ deb QOLDI
#    (yolg'on «3-band yopildi» da'vosining oldini oladi)
test "$(grep -c '3- va 9-bandlar HAMON OCHIQ' "$f")" = 1 || { echo "FAIL: 3/9 ochiq qolmadi"; exit 1; }
test "$(grep -c "7-band TO'LIQ YOPILDI" "$f")" = 1 || { echo "FAIL: 7-band markeri"; exit 1; }
# 6) YAML shakli buzilmadi — decisions hamon 4 ta bir qatorli qo'shtirnoqli satr
test "$(sed -n '/^decisions:/,/^metrics:/p' "$f" | grep -c '^  - "[^"]*"$')" = 4 || { echo "FAIL: YAML"; exit 1; }
# 7) Regressiya: imzo darvozasi hamon yashil
node scripts/check-validation-signoff.mjs || exit 1
echo "OK"
    </automated>
  </verify>
  <done>
`06-14-SUMMARY.md` ning beshala eskirgan da'vosi asl holida saqlangan holda
yopilish eslatmasi bilan qoplangan; har bir eslatmada o'lchangan raqamlar
(1703/1733/1899 s · 2300 s · 200 s) va yopgan artefakt (`package.json`,
`06-VALIDATION.md`, `deferred-items.md:19`) nomma-nom ko'rsatilgan; 3- va
9-bandlar OCHIQ deb qolgan; yuqoridagi darvoza `OK` bilan tugaydi va
`git diff --name-only` da faqat shu bitta fayl turadi.
  </done>
</task>

</tasks>

<tahrir_matnlari>

## T-1 — 41-qator (frontmatter `decisions` oxirgi bandi) · ALMASHTIRISH

**Eski (uning O'ZI qayta yoziladi — mazmuni saqlanadi):**

~~~
  - "nyquist_compliant HAMON false — `gate` byudjeti o'lchanmadi va band YASHIRILMADI"
~~~

**Yangi (bitta qator, ichida qo'shtirnoq YO'Q):**

~~~
  - "nyquist_compliant HAMON false — `gate` byudjeti o'lchanmadi va band YASHIRILMADI — KEYIN YOPILDI (orkestrator, to'lqin 9 dan keyin: `gate` uch marta 1703/1733/1899 s exit 0, byudjet 1250 -> 2300 s, `gate:fast` 180 -> 200 s, `06-VALIDATION.md` da nyquist_compliant: true)"
~~~

---

## T-2 — 55-qatordan keyin (sarlavha xatboshisi) · QO'SHISH

Bold xatboshi (51-55) **tegilmaydi**. Undan keyin, 57-qatordagi `---` dan oldin
bo'sh qator + quyidagi matn qo'yiladi:

~~~
✅ **YOPILDI — byudjet KEYINCHALIK O'LCHANDI va qayta belgilandi (orkestrator,
to'lqin 9 dan keyin — ya'ni bu reja YAKUNLANGANDAN so'ng).** Yuqoridagi xatboshi
06-14 tugagan paytdagi holatni qayd etadi va TARIX sifatida o'zgarmaydi.
`npm run gate` tinch xostda **uch marta** yugurtirildi — **1703 / 1733 / 1899 s,
uchalasi ham exit 0** — byudjet **1250 → 2300 s** (`package.json` dagi
`//gate-budget` izohi), `gate:fast` esa **160 / 154 / 152 s** o'lchovi bilan
**180 → 200 s**. `06-VALIDATION.md` frontmatteri endi `nyquist_compliant: true` ·
`status: complete` · `wave_0_complete: true`, va
`node scripts/check-validation-signoff.mjs` → **exit 0**. Batafsil quyidagi
«Byudjet» bo'limida; dalil: `deferred-items.md` 7-band.
~~~

---

## T-3a — 226-qator sarlavhasi · KENGAYTIRISH

**Eski:**

~~~
## ⛔ Byudjet — O'LCHANMADI (ochiq band)
~~~

**Yangi** (asl so'zlar joyida qoladi, ustiga marker qo'shiladi — shunda
mundarijani ko'zdan kechirgan o'quvchi ham yopilganini ko'radi):

~~~
## ⛔ Byudjet — O'LCHANMADI (ochiq band) → ✅ YOPILDI (o'lchov reja yakunlangandan keyin)
~~~

---

## T-3b — yangi sarlavhadan keyin · QO'SHISH

`⛔ **Bu bo'limni to'g'ri o'qing:` bilan boshlanadigan xatboshidan **OLDIN**:

~~~
✅ **YOPILDI — `gate` O'LCHANDI, byudjet qayta belgilandi (orkestrator, to'lqin 7
ning post-merge darvozasi va to'lqin 9 dan keyin).** ⛔ Quyidagi jadval va
«Oqibat va qaror» bandlari **06-14 ijrosi paytidagi** holatni qayd etadi — ular
TARIX va O'CHIRILMAYDI. O'shandan beri o'zgargani:

| Nima | O'shanda (06-14 ijrosi) | Hozir (yopilgandan keyin) | Dalil artefakti |
|---|---|---|---|
| `npm run gate` yugurishi | ❌ 1-yugurish ~33 % da transport xatosi bilan uzildi | ✅ **uch marta, tinch xostda: 1703 / 1733 / 1899 s — uchalasi ham exit 0** | `deferred-items.md` 7-band |
| Tarqoqlik | ❌ hisoblanmadi | ✅ **196 s = eng yomonning 10,3 %** | `package.json` `//gate-budget` |
| `gate` byudjeti | 1250 s (05-15 niki) | ✅ **2300 s** = 1899 × 1,20 = 2278,8 → 50 ga yuqoriga yaxlitlandi | `package.json` `//gate-budget` **va** `06-VALIDATION.md` — BIR XIL |
| `gate:fast` nazorat o'lchovi | ❌ olinmadi | ✅ **160 / 154 / 152 s**, tarqoqlik 8 s (5,0 %) | `package.json` `//gate-fast-budget` |
| `gate:fast` byudjeti | 180 s | ✅ **200 s** = 160 × 1,20 = 192 → 50 ga yuqoriga yaxlitlandi | `package.json` `//gate-fast-budget` |
| `nyquist_compliant` | ⛔ `false` | ✅ **`true`** (`status: complete`, `wave_0_complete: true`) | `06-VALIDATION.md` frontmatteri |
| `check-validation-signoff.mjs` | «Ochiq qoidalar (1)» | ✅ **exit 0** | `node scripts/check-validation-signoff.mjs` |

⚠ **Quyidagi qo'rquv ASOSLI edi:** «241 s zaxira yetarli ekani TASDIQLANMAGAN» —
o'lchov 1250 s byudjetini haqiqatan **oshirdi** (eng yomoni 1899 s). ⚠ Lekin
o'sish **to'plamning o'sishidan, ifloslanishdan EMAS** (`//gate-budget` izohida
yozilgan): 6-faza 173 ta backend testi qo'shdi, vitest **620 → 717**, va uchta
yangi marshrut (`/collect`, `/collect/shift`, `/billing`) uchala locale'da SSG
build'ga qo'shildi.
~~~

---

## T-3c — «Yopish yo'li (bir qadam)» xatboshisidan keyin · QO'SHISH

`**Bu rejada TO'LIQ yugurgan va YASHIL bo'lgan darvozalar**` dan **OLDIN**:

~~~
✅ **Shu yo'l AYNAN bajarildi** (yuqoridagi jadvalga qarang): uch o'lchov olindi,
eng yomoni (**1899 s**) 1250 s dan oshdi, shuning uchun yangi chegara
**1899 × 1,20 = 2278,8 → 2300 s** qilib belgilandi va u `package.json` dagi
`//gate-budget` izohida **va** `06-VALIDATION.md` da **BIR XIL** yozildi. Ikkala
band `[x]` bo'ldi.
~~~

---

## T-4 — 363-364-qatorlar (`## Ochiq bandlar` 1-bandi) · ALMASHTIRISH

**Eski:**

~~~
1. ⛔ **`gate` byudjeti o'lchanmadi** — yuqoridagi «Byudjet» bo'limi. Bu rejaning
   yagona bajarilmagan qabul mezoni.
~~~

**Yangi** (asl ikki jumla **so'zma-so'z** ichida qoladi):

~~~
1. ✅ **YOPILDI — `gate` byudjeti O'LCHANDI va qayta belgilandi.** O'sha paytdagi
   yozuv TARIX sifatida saqlanadi: ⛔ **`gate` byudjeti o'lchanmadi** — yuqoridagi
   «Byudjet» bo'limi. Bu rejaning yagona bajarilmagan qabul mezoni. ✅ **Yopilishi:**
   orkestrator to'lqin 9 dan keyin tinch xostda `npm run gate` ni **uch marta**
   yugurtirdi (**1703 / 1733 / 1899 s, uchalasi ham exit 0**); byudjet
   **1250 → 2300 s** (`package.json` `//gate-budget`), `gate:fast` **180 → 200 s**
   (o'lchovlar 160 / 154 / 152 s); `06-VALIDATION.md` da `nyquist_compliant: true`
   va `node scripts/check-validation-signoff.mjs` → **exit 0**. Dalil:
   `deferred-items.md` 7-band.
~~~

---

## T-5 — 378-379-qatorlar (`## Ochiq bandlar` 5-bandi) · ALMASHTIRISH

⛔ **Qamrov TOR:** faqat **7-band** «qisman» → «TO'LIQ yopildi» ga o'tadi.
**3- va 9-bandlar OCHIQ bo'lib qoladi** — SUMMARY ning «3 va 9 boshqa
fazalarniki» izohi to'g'ri (`deferred-items.md:10` va `:21` da `✅` belgisi yo'q).

**Eski:**

~~~
5. **`deferred-items.md` 3-, 7- va 9-bandlar** ochiq (7-band bu rejada qisman
   yopildi — backend darvozasi yugurtirildi; 3 va 9 boshqa fazalarniki).
~~~

**Yangi** (asl jumla so'zma-so'z ichida qoladi):

~~~
5. ⚠ **QISMAN ESKIRGAN — 7-band endi TO'LIQ yopilgan; 3- va 9-bandlar OCHIQ.**
   O'sha paytdagi yozuv: **`deferred-items.md` 3-, 7- va 9-bandlar** ochiq (7-band
   bu rejada qisman yopildi — backend darvozasi yugurtirildi; 3 va 9 boshqa
   fazalarniki). ✅ **7-band TO'LIQ YOPILDI** — `deferred-items.md` ning 19-qatori
   endi shuni yozadi: orkestrator to'lqin 7 ning post-merge darvozasida, so'ng
   to'lqin 9 dan keyin to'liq `gate` ni **uch marta** yugurtirdi
   (**1703 / 1733 / 1899 s, exit 0**), ya'ni «qisman» qaydi — faqat backend yarmi —
   endi o'rinli emas. ⚠ **3- va 9-bandlar HAMON OCHIQ va bu TO'G'RI:** 3-band
   (`PUT /api/v1/camera-zones` ning `QUERY_PARAM_ROUTES` istisnosi) 05-06 dan
   meros, 9-band (`charge-list.tsx` da sotuvchi ismi joini faqat birinchi 50 lik
   sahifani ko'radi) esa 8-fazaning hisobot yuzasiniki — ikkalasi ham 6-fazaniki
   EMAS va bu rejada ularga TEGILMAYDI.
~~~

⚠ **Ijrochiga eslatma:** `deferred-items.md` da «3» raqami **ikki marta**
ishlatilgan (10- va 14-qatorlar). 14-qatordagi 3-band (`gate` ning frontend
yarmi) to'lqin 5 da — 06-14 dan **oldin** — yopilgan va SUMMARY unga havola
qilmaydi. Yuqoridagi matn AYNAN 10-qatordagi ochiq bandni nazarda tutadi.

</tahrir_matnlari>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| — | YANGI chegara YO'Q: bu faqat `.planning/` ichidagi hujjat tahriri. Ishga tushadigan kod, tarmoq yuzasi, ma'lumot oqimi o'zgarmaydi. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-QUICK-01 | Tampering (hujjat) | `06-14-SUMMARY.md` tarixi | mitigate | Tahrir asl matnni **o'chirmaydi**; darvoza beshala asl da'voning `grep -c … = 1` bilan joyida turganini o'lchaydi |
| T-QUICK-02 | Information disclosure (yolg'on «yashil») | Keyingi ijrochining qarori | mitigate | Har yopilish o'lchangan raqam + artefakt nomi bilan yoziladi; bo'sh «endi yopildi» da'vosi taqiqlanadi va `1703`/`2300` sanog'i bilan o'lchanadi |
| T-QUICK-03 | Spoofing (YANGI yolg'on da'vo) | `deferred-items.md` 3- va 9-bandlari | mitigate | T-5 qamrovi 7-band bilan cheklangan; `grep -c '3- va 9-bandlar HAMON OCHIQ' = 1` darvozasi ular ochiq qolganini o'lchaydi |
| T-QUICK-04 | Elevation (qamrov chetiga chiqish) | Manba kodi / `package.json` / `06-VALIDATION.md` | mitigate | `git diff --name-only` **aynan bitta** yo'lga teng bo'lishi darvoza sifatida, `git add` dan oldin |
| T-QUICK-SC | Tampering | npm/pip/cargo o'rnatish | accept | Bu rejada birorta paket o'rnatilmaydi — `package.json` ga TEGILMAYDI, `node_modules` o'zgarmaydi |
</threat_model>

<verification>
1. `<verify>` darvozasi `OK` bilan tugaydi (15 ta tekshiruv + imzo skripti).
2. Faylni ko'z bilan o'qib chiq: `## Ochiq bandlar` bo'limida `⛔` bilan
   boshlanadigan **byudjet** bandi qolmagan; 5-bandda esa 3- va 9-bandlar hamon
   ochiq deb turibdi.
3. Frontmatterni YAML sifatida o'qigan har qanday vosita xato bermaydi
   (`decisions` — to'rtta bir qatorli qo'shtirnoqli satr).
</verification>

<success_criteria>
- [ ] `06-14-SUMMARY.md` dagi beshala eskirgan da'vo yopilish eslatmasi bilan qoplangan
- [ ] Beshala asl matn faylda **so'zma-so'z** qolgan (`grep -c … = 1` bilan o'lchanadi)
- [ ] Har eslatmada aniq raqam (1703/1733/1899 · 2300 · 200) **va** yopgan artefakt nomi bor
- [ ] Yopilish markeri faylning o'z konvensiyasi (`✅ **YOPILDI — …**`) bo'yicha
- [ ] `## Ochiq bandlar` 1-bandi `1. ✅ **YOPILDI` bilan boshlanadi
- [ ] 5-bandda faqat 7-band «TO'LIQ YOPILDI» ga o'tgan; **3- va 9-bandlar OCHIQ qolgan**
- [ ] `decisions` frontmatteri hamon to'rtta bir qatorli qo'shtirnoqli YAML satri
- [ ] `git diff --name-only` da **aynan bitta** fayl
- [ ] `node scripts/check-validation-signoff.mjs` → exit 0
</success_criteria>

<output>
Create `.planning/quick/260811-kyz-06-14-summary-md-eskirgan-byudjet-da-vos/260811-kyz-SUMMARY.md` when done
</output>
