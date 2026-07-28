# SBOZOR

## What This Is

SBOZOR — O'zbekiston an'anaviy bozorlarini raqamlashtiruvchi universal SaaS platforma. Bozor ma'muriyati uchun: mavjud NVR kameralaridan olingan snapshotlarni AI tahlil qilib, band rastalarni aniqlaydi, kunlik patta hisobini yuritadi va to'lovlar bilan solishtirib nomuvofiqlikni fosh qiladi. MVP — Karmana tumani bozori (Navoiy viloyati, ~300–1000 rasta) pilotida "har bir band rastadan patta to'liq yig'ilyaptimi?" savoliga raqamlar va rasm-dalil bilan javob berish.

## Core Value

Bozor ma'muriyati har bir band rastadan patta to'liq yig'ilayotganini raqamlar va rasm-dalil bilan ko'radi — "band, lekin to'lovsiz" rastalar kunlik hisobotda avtomatik fosh bo'ladi.

## Requirements

### Validated

(Hali yo'q — pilot bilan tasdiqlanadi)

### Active

- [ ] "Yangi bozor" ustasi (wizard): rekvizitlar → plan-rasm → rastalar → toifalar/tariflar → kameralar → kamera zonalari (poligonlar) → snapshot jadvali
- [ ] Rasta va tarif moduli: zonalar, mahsulot toifalari, tarixiy tariflar, rasta holatlari, sotuvchi biriktirish
- [ ] Snapshot pipeline: NVR (RTSP/ffmpeg) → kuniga 7 kadr → MinIO arxiv → retry/xato jurnali
- [ ] CV tahlil: kamera zonalarida band/bo'sh/noaniq aniqlash (Apache-2.0 litsenziyali detektor), occupancy events
- [ ] Nazoratchi tasdiqlash oqimi (human-in-the-loop): noaniq natijalar navbati, tasdiq/tuzatish, fine-tuning dataseti
- [ ] Billing: kun oxirida yakuniy hisob (birorta snapshotda band → to'liq kunlik patta), dalil-snapshot bog'lanishi, qarzdorlik (faqat biriktirilgan sotuvchiga), charge_adjustments
- [ ] Kassir moduli (mobil rejim): rasta qidirish → tarifdan avtomatik summa → naqd/terminal → 3 bosishda to'lov
- [ ] Nomuvofiqlik hisoboti: "band, lekin to'lovsiz" + "ro'yxatga olinmagan savdo" (biriktirilmagan rasta band), rasm-dalillar bilan
- [ ] Telegram-bot (sotuvchi): ro'yxatdan o'tish, qoldiq/qarz, to'lov tarixi, qarz eslatmalari
- [ ] Telegram-bot (direktor): ertalabki dayjest, kechki nomuvofiqlik hisoboti
- [ ] Hisobotlar + Excel eksport: tushum, bandlik, qarzdorlik reestri, kassir kesimi, AI aniqlik hisoboti
- [ ] Audit jurnali: har harakat (kim, qachon, nima, eski→yangi)
- [ ] Jonli kamera ko'rish paneli (go2rtc RTSP→WebRTC/HLS)
- [ ] 3 til: o'zbek-lotin (asosiy), o'zbek-kirill, rus
- [ ] Rollar va auth: platforma admini, direktor, bozor admini, kassir, nazoratchi
- [ ] Tizim monitoringi: kamera offline / snapshot o'tkazildi / backup xatosi → admin'ga Telegram-alert

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
- **Stek**: FastAPI (core-api, cv-service) + aiogram (bot-service) + Next.js/Tailwind (frontend) + PostgreSQL/Redis/MinIO + Docker Compose — jamoa ko'nikmasi, MVP topshirig'ida qat'iylashtirilgan
- **Servislar soni**: aynan 3 ta (core-api, cv-service, bot-service) — ortiqcha mikroservis bo'linmaydi
- **Litsenziya**: CV modellar faqat Apache-2.0/MIT (RT-DETR/D-FINE/YOLOX oilasi); AGPL (Ultralytics) taqiqlangan — tijoriy SaaS
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
*Last updated: 2026-07-28 after initialization*
