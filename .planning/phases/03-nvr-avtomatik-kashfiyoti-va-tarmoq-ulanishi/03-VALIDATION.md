---
phase: 3
slug: nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-03
---

# Phase 3 — Validation Strategy

> Fazani ijro qilish davomida teskari aloqa namunasini olish uchun validatsiya kontrakti.
> **Manba:** `03-RESEARCH.md` § `Validation Architecture`, `03-UI-SPEC.md` darvozalari (G-1…G-7), `03-PATTERNS.md` §5 (Wave 0).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`asyncio_mode=auto`) · vitest (frontend) · `node:test` (skript darvozalari) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) · `frontend/vitest.config.ts` |
| **Quick run command** | `docker compose --profile test run --rm tests pytest tests/unit -x -q` |
| **Full suite command** | `npm run gate` |
| **Estimated runtime** | ~470–590 s to'liq (2-fazada o'lchangan: 464 s / 571 s / 585 s — Docker kesh o'zgaruvchanligi katta) |

**Yangi infratuzilma (bu fazada tug'iladi):**

| Komponent | Nima uchun | Holat |
|---|---|---|
| `--profile sim` (Hikvision NVR simulyatori) | CAM-09 — real uskunasiz uchidan-uchiga isbot | Wave 0 da quriladi |
| `taskiq` worker konteyneri | D-06 — loyihaning birinchi fon job'i | Wave 0 da quriladi |
| ISAPI fixture'lari (`DS-7616NI-K2`, `DS-7732NI-M4`) | D-04 — **real yozib olingan dumplar**, o'ylab topilgan XML emas | Wave 0 da olinadi |

---

## Sampling Rate

- **Har task commitidan keyin:** `pytest tests/unit -x -q`
- **Har to'lqindan keyin:** `npm run gate`
- **`/gsd-verify-work` dan oldin:** to'liq to'plam yashil
- **Maksimal teskari aloqa kechikishi:** 180 s

> ⚠ **2-fazadan ochiq qolgan band:** to'lqin darajasidagi kechikish o'lchandi — **225 s**, chegara 180 s. Sabab: `npm run gate` Docker konteynerini har safar ko'taradi. Bu fazada `--profile sim` yana bitta konteyner qo'shadi, ya'ni kechikish o'sadi. **Wave 0 da hal qilinishi kerak:** yo chegara realistik qiymatga ko'tariladi (o'lchov bilan asoslanib), yo tez yo'l ajratiladi (masalan `pytest -m "not slow"` + simsiz). Jimgina chegaradan oshib ketish qabul qilinmaydi.

---

## Per-Task Verification Map

*Rejalashtirish tugagach `gsd-planner` tomonidan to'ldiriladi — har PLAN.md taski uchun bitta qator.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *(rejalashtiruvda to'ldiriladi)* | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

`03-PATTERNS.md` §5 yetti bandni sanaydi; ulardan uchtasi **jimgina yiqiladigan** turdagi — testlar yashil bo'lgani holda ishlab chiqarish buziladi:

- [ ] **W0-1** — `httpx` ni `[dependency-groups] dev` dan `[project] dependencies` ga ko'chirish. **Aks holda 24 test fayli yashil qoladi va deploy'da import xatosi beradi.** (D-16)
- [ ] **W0-2** — `rbac.py` **va** `rbac.ts` da `CAMERA_VIEW` + `CAMERA_MANAGE`. `PLATFORM_ADMIN` ga `CAMERA_VIEW` berilishi shart: self-service onboarding'da bozorni aynan platforma admini ulaydi, ya'ni u o'zi topgan kameralarni ko'ra olmasdi. Ikki fayl **birga** o'zgaradi. (D-15)
- [ ] **W0-3** — `nvr_credentials` jadvalini audit triggeridan **chiqarish**. `fn_audit_row()` `to_jsonb(NEW)` yozadi, ya'ni Fernet shifrmat `audit_log` ga ochiq tushardi va shifrlash ma'nosini yo'qotardi. Ikkinchi mustaqil sabab: `attach_audit_trigger()` `id uuid` PK talab qiladi, 1:1 credentials jadvalida u yo'q.
- [ ] **W0-4** — `--profile sim` simulyator konteyneri + real yozib olingan ISAPI fixture'lari
- [ ] **W0-5** — `taskiq` + `taskiq-redis 1.2.3` va worker konteyneri (`arq` o'rnatib bo'lmaydi — `redis[hiredis]<6` vs pin `8.0.1`)
- [ ] **W0-6** — `gen-cyrillic.mjs` allowlist'i (`NVR`, `RTSP`, `ISAPI`) + UI-SPEC §11.7 dagi ikkinchi nuqson sinfi uchun regressiya assert'i
- [ ] **W0-7** — `market_delete_draft()` kaskadi. **`0012` migratsiya qo'ngan zahoti buziladi** — u yangi tenant jadvalini bilmaydi. WR-02 (2-fazadan eskalatsiya, D-17) shu yerda DB darajasida cheklanadi.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Owner | Trigger |
|----------|-------------|------------|-------|---------|
| Real Hikvision NVR'da kashfiyot | CAM-08 | Simulyator **modul** darajasida ishonchli, lekin real firmware'ning kutilmagan XML shakli yoki kanal raqamlash chetlanishi faqat qurilmada chiqadi | Bozor admini | NVR kirish ma'lumotlari kelganda |
| CGNAT ostidagi WireGuard tunneli | CAM-02 | Bozor tomonidagi ISP topologiyasini simulyatsiya qilib bo'lmaydi | Ops | Bozor tomonidagi qurilma o'rnatilganda |
| Bir vaqtdagi sessiya limiti (real qiymat) | CAM-08 | Chegara firmware va bitreytga bog'liq; simulyatorda **ikkala** stsenariy modellashtirilgan (D-05), lekin haqiqiy qiymat o'lchanmagan | Ops | Real NVR ulanganda |
| Jonli tasvir sifati va kechikishi | CAM-03 | Idrok o'lchovi — real tarmoq, real kamera, real ekran | Direktor | Pilot tayyorlanganda |

> Bu bandlar **fazani bloklamaydi** (2026-08-01 self-service direktivasi). Ular egasi va tetigi bilan yozilgan; `nyquist_compliant` ularning bajarilganini emas, **shaklini** tekshiradigan skript bilan hisoblanadi — 2-fazadagi `scripts/check-validation-signoff.mjs` naqshi.

---

## Validation Sign-Off

- [ ] Har taskda `<automated>` verify yoki Wave 0 bog'liqligi bor
- [ ] Namuna uzluksizligi: ketma-ket 3 taskda avtomatik verify yo'qligi holati yo'q
- [ ] Wave 0 barcha MISSING havolalarni qoplaydi
- [ ] Watch-mode bayrog'i yo'q
- [ ] Teskari aloqa kechikishi o'lchangan va chegara asoslangan (2-fazadan meros qolgan 225 s / 180 s bandi hal qilingan)
- [ ] `nyquist_compliant: true` skript bilan **hisoblangan**, qo'lda yozilmagan

**Approval:** pending
