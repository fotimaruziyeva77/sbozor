---
quick_id: 260811-kyz
phase: quick
plan: 260811-kyz
subsystem: hujjat-yaxlitligi
tags: [documentation, audit, F-2, gate-budget, nyquist, summary-drift]

requires:
  - phase: 06-billing-va-kassir
    provides: "06-14-SUMMARY.md (eskirgan da'volar), package.json //gate-budget o'lchovlari, 06-VALIDATION.md bayroqlari, deferred-items.md 7-band"
provides:
  - "06-14-SUMMARY.md — beshala eskirgan byudjet/nyquist da'vosi yopilish eslatmasi bilan qoplangan, ASL MATN so'zma-so'z saqlangan holda"
  - "Xavfsizlik auditining F-2 topilmasi YOPILDI"
  - "Naqsh: SUMMARY tarixiy artefakt — eskirgan da'vo O'CHIRILMAYDI, ustiga o'lchangan raqam + dalil artefakti bilan yopilish qatlami qo'shiladi"
affects: [06-billing-va-kassir, gsd-verify-work, 07-faza, 08-faza]

tech-stack:
  added: []
  patterns:
    - "Hujjat tuzatishida TARIX o'chirilmaydi — yopilish USTIGA yoziladi va `grep -c ... = 1` darvozasi asl matn joyida turganini o'lchaydi"
    - "Har yopilish da'vosi O'LCHANGAN RAQAM (1703/1733/1899 s · 2300 s · 200 s) va DALIL ARTEFAKTI nomi bilan qulflanadi — bo'sh «endi yopildi» taqiqlanadi"
    - "Yopilish qamrovi TOR ushlanadi: qo'shni ochiq bandlar (`deferred-items.md` 3/9) ATAYIN OCHIQ qoldiriladi va buni alohida darvoza o'lchaydi"

key-files:
  created:
    - ".planning/quick/260811-kyz-06-14-summary-md-eskirgan-byudjet-da-vos/260811-kyz-SUMMARY.md"
  modified:
    - ".planning/phases/06-billing-va-kassir/06-14-SUMMARY.md"

key-decisions:
  - "Asl da'volar QAYTA YOZILMADI — beshalasi so'zma-so'z qoldi va grep darvozalari bilan qulflandi; SUMMARY o'sha paytdagi holatni qayd etuvchi tarixiy artefakt"
  - "Yopilish markeri faylning O'Z konvensiyasi bo'yicha (`✅ **YOPILDI — ...**`); frontmatterda YAML string ichida `— KEYIN YOPILDI (...)`"
  - "T-5 qamrovi FAQAT 7-band bilan cheklandi — `deferred-items.md` 3- va 9-bandlari OCHIQ qoldirildi, chunki «3-band yopildi» deyish biz tuzatayotgan F-2 nuqsonining aynan takrori bo'lardi"
  - "Qamrov darvozasi (`git diff --name-only` = aynan bitta yo'l) `git add` dan OLDIN yugurtirildi — commitdan keyin u bo'sh bo'lib yashil-yolg'on bergan bo'lardi"

patterns-established:
  - "Eskirgan hujjat da'vosini yopish: ASL MATN + `✅ YOPILDI` qatlami + o'lchangan raqam + artefakt nomi + qamrov chegarasi"
  - "Sarlavha darajasidagi yopilish: `## ⛔ ... (ochiq band) → ✅ YOPILDI (...)` — mundarijani ko'zdan kechirgan o'quvchi ham holatni ko'radi"
  - "Solishtirma jadval «O'shanda | Hozir | Dalil artefakti» — tarixni o'chirmasdan farqni ko'rsatadi"

requirements-completed: [F-2]

duration: ~20 min
completed: 2026-08-11
---

# Quick 260811-kyz: 06-14-SUMMARY.md eskirgan byudjet da'volari Summary

**`06-14-SUMMARY.md` ning beshala eskirgan «gate byudjeti O'LCHANMADI / nyquist_compliant HAMON false» da'vosi — asl matn so'zma-so'z saqlangan holda — o'lchangan raqam (1703/1733/1899 s · 1250→2300 s · 180→200 s) va dalil artefakti nomi bilan yopildi; `deferred-items.md` 3- va 9-bandlari ATAYIN OCHIQ qoldirildi.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-08-11T10:27:38Z
- **Tasks:** 1 (5 ta tahrir: T-1…T-5)
- **Files modified:** 1

## Muammo (F-2)

`06-14-SUMMARY.md` to'rt joyda `gate` byudjeti **o'lchanmagan** va
`nyquist_compliant` **hamon `false`** deb yozardi. Amalda esa:

- byudjet o'lchangan (**1703 / 1733 / 1899 s**, uchalasi exit 0),
- qayta belgilangan (**1250 → 2300 s**, `gate:fast` **180 → 200 s**),
- `06-VALIDATION.md` bayrog'i **`true`**, imzo skripti **exit 0**.

Ya'ni faylni **so'zma-so'z o'qigan** keyingi ijrochi 6-fazani ochiq deb
hisoblardi. Beshinchi (qo'shimcha) eskirgan joy: `deferred-items.md` **7-bandi**
«qisman yopildi» deb turardi, holbuki u endi **to'liq** yopilgan.

## Bajarilgan tahrirlar

| # | Joy | Amal | Nima qo'shildi |
|---|-----|------|----------------|
| **T-1** | Frontmatter `decisions` 4-bandi (41-qator) | ALMASHTIRISH | Asl string saqlanib, oxiriga `— KEYIN YOPILDI (orkestrator, to'lqin 9 dan keyin: gate uch marta 1703/1733/1899 s exit 0, byudjet 1250 -> 2300 s, gate:fast 180 -> 200 s, 06-VALIDATION.md da nyquist_compliant: true)` qo'shildi. **Bitta qator, ichida qo'shtirnoq YO'Q** |
| **T-2** | Sarlavha xatboshisidan keyin (56-qator) | QO'SHISH | `✅ **YOPILDI — byudjet KEYINCHALIK O'LCHANDI...**` bloki (10 qator): uch o'lchov, ikkala byudjet, uchala validatsiya bayrog'i, imzo skripti, dalil `deferred-items.md` 7-band |
| **T-3a** | `## ⛔ Byudjet — O'LCHANMADI (ochiq band)` sarlavhasi (226-qator) | KENGAYTIRISH | Asl so'zlar joyida; oxiriga `→ ✅ YOPILDI (o'lchov reja yakunlangandan keyin)` |
| **T-3b** | Yangi sarlavhadan keyin, `⛔ **Bu bo'limni to'g'ri o'qing:` dan OLDIN | QO'SHISH | `✅ **YOPILDI — gate O'LCHANDI...**` + **7 qatorli «O'shanda \| Hozir \| Dalil artefakti» jadvali** + «qo'rquv ASOSLI edi, lekin o'sish to'plamning o'sishidan» izohi |
| **T-3c** | «Yopish yo'li (bir qadam)» dan keyin | QO'SHISH | `✅ **Shu yo'l AYNAN bajarildi**` — 1899 × 1,20 = 2278,8 → 2300 s hisob-kitobi va ikki joyda BIR XIL yozilgani |
| **T-4** | `## Ochiq bandlar` **1-bandi** (363–364-qatorlar) | ALMASHTIRISH | `1. ⛔ ...` → `1. ✅ **YOPILDI — gate byudjeti O'LCHANDI va qayta belgilandi.**`; asl ikki jumla ichida **so'zma-so'z** qoldi |
| **T-5** | `## Ochiq bandlar` **5-bandi** (378–379-qatorlar) | ALMASHTIRISH | `⚠ **QISMAN ESKIRGAN — 7-band endi TO'LIQ yopilgan; 3- va 9-bandlar OCHIQ.**`; asl jumla ichida qoldi; **3- va 9-bandlar OCHIQ deb aniq yozildi** |

**Tartib:** tahrirlar **pastdan yuqoriga** (T-5 → T-4 → T-3c → T-3b → T-3a → T-2 →
T-1) qo'llandi, shunda qator raqamlari siljimadi.

## Verify darvozalari — o'lchangan sonlar

Hamma darvoza **`git add` dan OLDIN** yugurtirildi (G-0 aynan shuni talab qiladi).

| # | Darvoza | Kutilgan | **Haqiqiy** | Natija |
|---|---------|----------|-------------|--------|
| **G-0** | `git diff --name-only` = `06-14-SUMMARY.md` | aynan 1 yo'l | **`.planning/phases/06-billing-va-kassir/06-14-SUMMARY.md`** | ✅ |
| **G-1** | `grep -c 'nyquist_compliant HAMON false'` (T-1 tarixi) | `= 1` | **1** | ✅ |
| **G-2** | `grep -c "byudjeti esa O'LCHANMADI"` (T-2 tarixi) | `= 1` | **1** | ✅ |
| **G-3** | `grep -c "Byudjet — O'LCHANMADI (ochiq band)"` (T-3 tarixi) | `= 1` | **1** | ✅ |
| **G-4** | `grep -c 'yagona bajarilmagan qabul mezoni'` (T-4 tarixi) | `= 1` | **1** | ✅ |
| **G-5** | `grep -c '3-, 7- va 9-bandlar'` (T-5 tarixi) | `= 1` | **1** | ✅ |
| **G-6** | `grep -oi "o.lchanmadi"` (tarix qisqarmadi) | `≥ 5` | **5** | ✅ |
| **G-7** | `grep -o 'YOPILDI'` (yopilish markerlari) | `≥ 8` (kutilgan 9) | **9** | ✅ |
| **G-8** | `grep -o '1703'` (o'lchov raqami) | `≥ 4` | **5** | ✅ |
| **G-9** | `grep -o '2300'` (yangi byudjet) | `≥ 4` | **5** | ✅ |
| **G-10** | `grep -c 'nyquist_compliant: true'` (bayroq havolasi) | `≥ 2` | **3** | ✅ |
| **G-11** | `grep -c '^1\. ✅ \*\*YOPILDI'` (1-band markeri) | `= 1` | **1** | ✅ |
| **G-12** | `grep -c '3- va 9-bandlar HAMON OCHIQ'` (T-5 qamrovi) | `= 1` | **1** | ✅ |
| **G-13** | `grep -c "7-band TO'LIQ YOPILDI"` | `= 1` | **1** | ✅ |
| **G-14** | `sed -n '/^decisions:/,/^metrics:/p' \| grep -c '^  - "[^"]*"$'` (YAML) | `= 4` | **4** | ✅ |
| **G-15** | `node scripts/check-validation-signoff.mjs` | exit 0 | **exit 0** (`nyquist_compliant: true — hisob-kitob bilan MOS · Per-Task: 42 · inson bandlari: 4`) | ✅ |

**Darvoza yakuni: 16/16 yashil, `OK`.** Birorta darvoza qizarmadi.

### Baseline → yakuniy (o'zgarish o'lchandi)

| O'lchov | Tahrirdan OLDIN | Tahrirdan KEYIN |
|---|---|---|
| `YOPILDI` markerlari | 3 | **9** (+6) |
| `1703` | 0 | **5** |
| `2300` | 0 | **5** |
| `nyquist_compliant: true` qatorlari | 0 | **3** |
| `^1. ✅ **YOPILDI` | 0 | **1** |
| `3- va 9-bandlar HAMON OCHIQ` | 0 | **1** |
| `7-band TO'LIQ YOPILDI` | 0 | **1** |
| **Tarix markerlari (G1–G5)** | 1 / 1 / 1 / 1 / 1 | **1 / 1 / 1 / 1 / 1 — o'zgarmadi** |
| `o.lchanmadi` | 5 | **5 — o'zgarmadi** |
| YAML `decisions` satrlari | 4 | **4 — o'zgarmadi** |

## Qo'shimcha (rejadan tashqari) tekshiruvlar

Ular **darvoza emas**, `<verification>` bo'limining 2- va 3-bandlari:

1. **YAML parse (verification #3)** — `js-yaml` bilan frontmatter parse qilindi:
   `YAML PARSE: OK`, `decisions` — **4 ta** massiv elementi, to'rtinchisi bitta
   qatorda, ichida qo'shtirnoqsiz. Vosita xato bermaydi.
2. **Ko'z bilan o'qish (verification #2)** — `## Ochiq bandlar` bandlarining
   boshlanish belgilari: `1. ✅` · `2. ✅` · `3.` · `4.` · `5. ⚠` · `6. ⚠`.
   **`⛔` bilan boshlanadigan byudjet bandi QOLMADI**; 5-band esa 3- va
   9-bandlarni hamon ochiq deb ko'rsatadi.
3. **Diff tahlili** — `git diff --numstat` → **62 qo'shildi / 6 o'chirildi**.
   O'chirilgan 6 qatorning **hammasi** almashtirilgan 5 ta anchor (T-1: 1 qator,
   T-3a: 1, T-4: 2, T-5: 2) va ularning matni yangi bloklar **ichida so'zma-so'z**
   qayta paydo bo'ldi (G1/G3/G4/G5 shuni o'lchaydi). Boshqa hech nima
   o'chirilmadi.
4. **Post-commit o'chirish tekshiruvi** — `git diff --diff-filter=D HEAD~1 HEAD`
   → **0 ta fayl**.

## Task Commits

1. **Task 1: 06-14-SUMMARY.md ning beshta eskirgan da'vosini yopilgan holatga moslash** — `8b5cf6f` (docs)

```
docs(06-14): eskirgan byudjet da'volari YOPILGAN holatga moslandi (F-2)
1 file changed, 62 insertions(+), 6 deletions(-)
```

⚠ Quick-task artefaktlari (`260811-kyz-PLAN.md`, `260811-kyz-SUMMARY.md`,
`.planning/STATE.md`) **ATAYIN commit qilinmadi** — ularni orkestrator 8-qadamda
o'zi commit qiladi.

## Files Created/Modified

- `.planning/phases/06-billing-va-kassir/06-14-SUMMARY.md` — beshta eskirgan
  da'voga yopilish qatlami qo'shildi; asl matn so'zma-so'z saqlandi
  (**YAGONA o'zgargan fayl**)

## Decisions Made

- **Asl da'volar qayta yozilmadi.** SUMMARY — o'sha paytdagi holatni qayd
  etuvchi **tarixiy artefakt**. Beshala da'vo so'zma-so'z qoldi va `grep -c = 1`
  darvozalari bilan qulflandi. Agar tarix o'chirilsa, G1–G5 **qizarardi**.
- **Yopilish markeri faylning O'Z konvensiyasidan olindi** (`✅ **YOPILDI — ...**`,
  365-qatordagi 2-band va `deferred-items.md` shu naqshni ishlatadi). Yangi uslub
  o'ylab topilmadi.
- **T-5 qamrovi TOR ushlandi.** `deferred-items.md` da «3» raqami **ikki marta**
  ishlatilgan (10-qator: camera-zones, 05-06 merosi, **OCHIQ**; 14-qator: `gate`
  ning frontend yarmi, to'lqin 5 da yopilgan). SUMMARY 10-qatordagini nazarda
  tutadi. «3-band yopildi» deb yozish — **biz tuzatayotgan F-2 nuqsonining aynan
  takrori** bo'lardi, shuning uchun faqat **7-band** «qisman» → «TO'LIQ» ga
  o'tkazildi va 3/9 bandlarning ochiqligi alohida darvoza (G-12) bilan
  qulflandi.
- **Qamrov darvozasi `git add` dan OLDIN yugurtirildi.** Commitdan keyin
  `git diff --name-only` bo'sh bo'lardi va darvoza **yashil-yolg'on** bergan
  bo'lardi.
- **Worktree izolyatsiyasi ISHLATILMADI** (topshiriq bo'yicha): bitta agent,
  bitta markdown fayl, parallellik yo'q. Bu repoda worktree konteyner poygalari
  06-08/06-09/06-11 SUMMARY'larida qayd etilgan.

## Deviations from Plan

**None — reja so'zma-so'z bajarildi.** `<tahrir_matnlari>` bo'limidagi T-1…T-5
matnlari o'zgartirilmasdan ko'chirildi; birorta raqam qayta o'lchanmadi yoki
taxmin qilinmadi (hammasi `<verified_facts>` dan).

Tegilmagani (topshiriq talabi bo'yicha, tasdiqlandi): `services/`, `frontend/`,
`tests/`, `migrations/`, `packages/`, `package.json`, `06-VALIDATION.md`,
`deferred-items.md`, `ROADMAP.md`, `06-SECURITY.md`.

## Issues Encountered

**None.** Birorta darvoza qizarmadi, birorta auto-fix urinishi kerak bo'lmadi.

⚠ Bitta e'tiborga loyiq nuqta: **G-6 (`o.lchanmadi` ≥ 5) aynan chegarada — 5.**
Ya'ni asl «o'lchanmadi» so'zlaridan **bittasi ham** o'chirilmaydi; kelajakda bu
fayldan bitta «o'lchanmadi» olib tashlansa, darvoza darhol qizaradi. Bu ataylab
shunday loyihalangan (tarix qisqarishini ushlaydi) — nuqson emas.

## Known Stubs

**None.** Hujjat tahriri; ishga tushadigan kod, tarmoq yuzasi yoki ma'lumot
oqimi o'zgarmadi.

## Threat Flags

**Yangi tahdid yuzasi YO'Q.** Reja `<threat_model>` ining to'rtala `mitigate`
bandi bajarildi:

| ID | Mitigatsiya | Qanday o'lchandi |
|---|---|---|
| T-QUICK-01 | Tarix o'chirilmadi | G1–G5 (`= 1`) + G-6 (`≥ 5`) |
| T-QUICK-02 | Bo'sh «yopildi» da'vosi yo'q | G-8 (`1703` ≥ 4), G-9 (`2300` ≥ 4), G-10 (bayroq ≥ 2) |
| T-QUICK-03 | 3/9 bandlar OCHIQ qoldi | G-12 (`= 1`) |
| T-QUICK-04 | Qamrov chetiga chiqilmadi | G-0 (`git diff --name-only` = aynan 1 yo'l, `git add` dan oldin) |
| T-QUICK-SC | Paket o'rnatilmadi | `package.json` TEGILMADI, `node_modules` o'zgarmadi |

## Self-Check: PASSED

**Fayllar:**

- `.planning/phases/06-billing-va-kassir/06-14-SUMMARY.md` — FOUND (modified)
- `.planning/quick/260811-kyz-06-14-summary-md-eskirgan-byudjet-da-vos/260811-kyz-SUMMARY.md` — FOUND

**Commitlar:**

- `8b5cf6f` docs(06-14): eskirgan byudjet da'volari YOPILGAN holatga moslandi (F-2) — FOUND

## Next Readiness

- **F-2 YOPILDI.** `06-14-SUMMARY.md` endi o'z holatidan orqada qolmaydi va
  yolg'on «ochiq band» signalini bermaydi.
- 6-fazani yopish qarori hamon **`/gsd-verify-work`** zimmasida — bu tahrir
  `ROADMAP.md` dagi faza belgisiga **TEGMADI**.
- `deferred-items.md` **3- va 9-bandlari OCHIQ** bo'lib qoldi: 3-band 05-06
  merosi (`QUERY_PARAM_ROUTES` istisnosi), 9-band 8-fazaning hisobot yuzasi
  (`charge-list.tsx` ism joini). Ikkalasi ham 6-fazaniki emas.

---
*Quick: 260811-kyz · 2026-08-11*
