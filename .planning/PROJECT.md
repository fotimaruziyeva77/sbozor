# SBOZOR

## What This Is

SBOZOR — O'zbekiston an'anaviy bozorlarini raqamlashtiruvchi universal SaaS platforma. Bozor ma'muriyati uchun: mavjud NVR kameralaridan olingan snapshotlarni AI tahlil qilib, band rastalarni aniqlaydi, kunlik patta hisobini yuritadi va to'lovlar bilan solishtirib nomuvofiqlikni fosh qiladi. MVP — Karmana tumani bozori (Navoiy viloyati, ~300–1000 rasta) pilotida "har bir band rastadan patta to'liq yig'ilyaptimi?" savoliga raqamlar va rasm-dalil bilan javob berish.

## Core Value

Bozor ma'muriyati har bir band rastadan patta to'liq yig'ilayotganini raqamlar va rasm-dalil bilan ko'radi — "band, lekin to'lovsiz" rastalar kunlik hisobotda avtomatik fosh bo'ladi.

## Requirements

### Validated

*(Build-tasdiq: mexanik darvozalar + sabotaj o'lchovlari bilan. Pilot/dala tasdig'i alohida — `08-HUMAN-UAT.md` va faza HUMAN-UAT fayllarida egasi/tetigi bilan.)*

- ✓ Rollar va auth: 5 rol, RBAC matritsasi, tenant sessiyasi — Phase 1
- ✓ Audit jurnali: har harakat, DB-trigger, 4 qatlamli o'zgarmaslik — Phase 1
- ✓ "Yangi bozor" ustasi: rekvizit → plan → rasta → tarif → kamera → zona → jadval — Phase 2
- ✓ Rasta va tarif moduli: tarixiy tariflar, holatlar, biriktirish davri — Phase 2
- ✓ Jonli kamera paneli (go2rtc, NVR avtokashfiyot, WireGuard-only) — Phase 3
- ✓ Snapshot pipeline: NVR → kunlik kadrlar → SeaweedFS arxiv → retry/jurnal — Phase 4
- ✓ CV tahlil mexanikasi: zona occupancy, noaniq-navbat (aniqlik o'lchovi — AI-02, Active da) — Phase 5
- ✓ Nazoratchi HITL oqimi: ko'r audit, tasdiq/tuzatish, dataset yig'ish — Phase 5
- ✓ Billing: kun yakuni hisobi, dalil-kadr bog'lanishi, qarzdorlik, charge_adjustments — Phase 6
- ✓ Kassir moduli: qidiruv → avtosumma → ≤3 bosish to'lov — Phase 6
- ✓ Nomuvofiqlik hisoboti: "band, to'lovsiz" + "ro'yxatsiz savdo", rasm-dalil — Phase 7
- ✓ Telegram-botlar (sotuvchi + direktor): dayjest, qarz, alertlar — Phase 7 (jonli token bilan sinov — dala bandi)
- ✓ Hisobotlar + Excel eksport: tushum/qarzdorlik/nomuvofiqlik/solishtiruv, imzoli `.xlsx`, davr chegaralari — Phase 8
- ✓ Uch tomonlama solishtiruv: daftar importi (all-or-nothing) vs tizim vs AI-kutilgan — Phase 8
- ✓ Zaxira mexanizmi: quvursiz backup, yurak urishi, tiklash mashqi CI qatlami — Phase 8 (offsite S3 — Active da)
- ✓ 3 til: uz-Latn / uz-Cyrl / ru, parity darvozalari (tabiiylik ko'rigi — dala bandi) — Phase 1–8
- ✓ Tizim monitoringi: kamera offline, snapshot o'tkazildi, backup_stale → Telegram-alert — Phase 4/7/8

### Active

- [ ] AI aniqlik o'lchovi (AI-02): oltin to'plam + real ONNX artefakti ustida detektor aniqligi — mexanika yashilligi bilan YOPILMAYDI (D-01)
- [ ] Offsite S3 konfiguratsiyasi (FOUND-07 ochiq yarmi): provayder + byudjet qarori buyurtmachidan; ungacha `backup_stale` halol chiqib turadi
- [ ] UI-polish/motion qatlami: `UI-UX-MASTERPLAN.md` bo'yicha — redesign emas, mavjud tizim ustiga (sketch → UI-SPEC → mini-faza)
- [ ] Landing sahifasi (sbozor.uz): `LANDING-BRIEF.md` bo'yicha — `(marketing)` route-guruhi, SSG, 3 til; go-live'dan oldin
- [ ] Go-live dala darvozalari: `08-HUMAN-UAT.md` 6 band (tiklash mashqi real serverda, RESTIC parol tartibi, uch til ko'rigi, `npm run up`, meros bandlar)

### Out of Scope

- Do'kon ijarasi (yillik shartnoma) — MVP faqat rasta/kunlik patta; keyingi bosqich
- Avtoturargoh (ANPR) — alohida modul, 2-bosqich
- Hojatxona moduli — 2-bosqich
- Onlayn to'lov (Payme/Click merchant) — MVP'da kassir qayd etadi; merchant shartnomalari keyin
- Xaridor super-ilovasi — strategik farqlovchi, lekin MVP'dan keyin
- Rasta broni, SMS kanal, heatmap — 2-bosqich
- Kassir offline rejimi — 2-bosqich (internet barqaror)
- Soliq/OFD va E-bozor integratsiyasi — davlat bosqichida
- Ultralytics YOLO (AGPL) — litsenziya xavfi; faqat Apache-2.0/MIT modellar

## Context

**Hujjatlar:** `SBOZOR-MVP-texnik-topshiriq.md` (v1.1, 2026-07-28 — asosiy manba), `Golib-strategiya_va_yol-xaritasi.docx` (to'rt ustunli strategiya), `Raqamli-bozor_vs_eBazaar_tahlil.docx` (raqobat tahlili).

**Bozor konteksti:** Prezident topshirig'i (~500 bozorni raqamlashtirish, 2025-07); Chorsu tajribasi (tushum 2x). Raqobatchilar: raqamli-bozor.uz (RealSoft — brend+AI+mobil, yopiq narx) va eBazaar (EverbestLab — ochiq narx, Buxoro/Navoiy). SBOZOR farqi: AI-nazorat + tezkor joriy etish + keyinchalik davlat integratsiyasi.

**Karmana pilot faktlari (2026-07-28 tasdiqlangan):**
- ~20–25 kamera, Hikvision NVR; login/parolni bozor ma'muriyati beradi
- Internet barqaror, stream uchun ham yetarli
- Kameralar rastalarning ~90% ini qamraydi; qolgani qo'lda rejimda
- Nazoratchilar bozorda mavjud — HITL tasdiqlashni ular bajaradi
- Parallel rejim: ishga tushirilgach 2–4 hafta kassir eski usulda ham yozadi
- Baza o'lchovi: joriy tushum birinchi 2 haftada o'lchanadi

**Jamoa:** loyiha rahbari (arxitektura + AI/CV) · backend (Python/FastAPI) · frontend (Next.js). Ishlab chiqishda AI (Claude Code) faol ishlatiladi.

## Constraints

- **Muddat**: 12 hafta (2026-07-28 → ~2026-10-18 Karmanada jonli) — davlat dasturi oynasi va raqobat tezligi
- **Stek**: FastAPI (core-api, cv-service) + aiogram (bot-service) + Next.js/Tailwind (frontend) + PostgreSQL/Valkey/SeaweedFS + Docker Compose — jamoa ko'nikmasi, MVP topshirig'ida qat'iylashtirilgan (tadqiqot 2026-07-29: MinIO arxivlangan → SeaweedFS; Redis → Valkey)
- **Servislar soni**: aynan 3 ta (core-api, cv-service, bot-service) — ortiqcha mikroservis bo'linmaydi
- **Litsenziya**: CV modellar faqat Apache-2.0/MIT — tanlov: RF-DETR (Nano→Large; XLarge/2XLarge PML 1.0 — TAQIQ); AGPL (Ultralytics) taqiqlangan — tijoriy SaaS
- **Infra**: Contabo VPS (8–16 GB RAM, 4–6 vCPU, 400+ GB disk), GPU'siz inference (CPU yetadi); fine-tuning uchun vaqtinchalik ijara GPU
- **Data-rezidentlik**: shaxsiy ma'lumotlar O'zR qonuni ostida — davlat bosqichidan oldin O'zbekiston hostingiga ko'chish rejalashtirilgan (compose ko'chishni osonlashtiradi)
- **Multi-tenant**: hamma jadvalda `market_id` — bitta kod bazasi, cheksiz bozor; yangi bozor kod yozmasdan wizard orqali ulanadi
- **UI**: Apple-uslub minimal dizayn; kassir oqimi ≤3 bosish; 3 til majburiy
- **Xavfsizlik**: NVR faqat VPN (WireGuard) orqali; RTSP parollari shifrlangan; audit jurnali majburiy

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Snapshot jadvali: 06:00–08:00 har 30 daq + 16:00, 18:00 (04:00 yo'q) | Bozor ertalab gavjum; 04:00 qorong'i va keraksiz | — Pending |
| Istalgan snapshotda band → to'liq kunlik patta | Karmana amaliyoti: bozorga chiqqan sotuvchidan to'liq patta | — Pending |
| Qarz faqat biriktirilgan sotuvchiga; biriktirilmagan band rasta → "ro'yxatga olinmagan savdo" anomaliyasi | To'lovchisiz qarz ma'nosiz; anomaliya ro'yxatga olishga undaydi | — Pending |
| `noaniq` kun oxirigacha tasdiqlanmasa → "bo'sh" | Kam hisoblash xavfsizroq; ortiqcha hisoblash nizo keltiradi | — Pending |
| Kassir summasi tarifdan avtomatik, o'zgartirish sabab-kod bilan | Erkin summa — korrupsiya teshigi | — Pending |
| Jonli kamera ko'rish MVP'da qoladi | Buyurtmachi talabi (2026-07-28) | — Pending |
| Hosting hozircha Contabo, keyin O'zbekistonga ko'chish | Tezlik; lokalizatsiya davlat bosqichidan oldin | — Pending |
| CV: Apache-2.0 modellar (RT-DETR/D-FINE/YOLOX), Ultralytics AGPL emas | Tijoriy SaaS uchun litsenziya xavfi | — Pending |
| "SBOZOR" nomi yakuniy | Buyurtmachi tasdiqladi | ✓ Good |
| Obyekt-ombor: SeaweedFS (MinIO emas) | MinIO upstream arxivlangan (2026-04); S3 API boto3 orqali — almashish .env darajasida | ✓ Good (4–8-fazalar davomida ishlab turdi) |
| Klient kontrakti — marshrut nomlarining haqiqat manbai | `REPORT_KINDS` to'plam tengligi bilan qulflangan (08-03); reja matni bilan farqda kontrakt yutadi — aks holda 404 faqat jonli ekranda ko'rinardi (08-07/12/14/16 da to'rt marta tasdiqlandi) | ✓ Good |
| `platform_admin` ga `REPORT_VIEW` berilmaydi | Bozorlararo rolga hisobot ochish bitta akkauntni butun platformaning shaxsiy-ma'lumot xaritasiga aylantirardi (Pitfall 11-A, UI-SPEC O-07) | ✓ Good |
| Sabotaj o'lchovi majburiy — test yozish yetarli emas | 8-fazada TO'RT marta testning o'zidagi yolg'on-yashilni fosh qildi (jumladan: shaxsiy eksportdan `audit_read` olib tashlansa 854 test yashil qolardi) | ✓ Good |
| Detektor: RF-DETR Nano→Large (ONNX Runtime CPU) | Yagona faol Apache-2.0 oila; XLarge/2XLarge PML 1.0 litsenziyada — ishlatilmaydi | — Pending |
| Patta sharti: ≥2 kadr tasdiq (yoki 1 kadr + nazoratchi) | Bitta kadr nizo generatori (o'tkinchi odam xatosi) — buyurtmachi 2026-07-29 tasdiqladi | — Pending |
| Aniqlik KPI: ko'r tasodifiy audit + xatolik turlari | noaniq-navbatdan o'lchash statistik xato (selection bias) | — Pending |
| Fikrlash tili: hujjatlar o'zbek-lotin | Jamoa va buyurtmachi o'zbek tilida ishlaydi | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-16 after Phase 8 (build milestone v1.0 yakunlandi; ochiq: AI-02, offsite S3, dala darvozalari, UI-polish + landing)*
