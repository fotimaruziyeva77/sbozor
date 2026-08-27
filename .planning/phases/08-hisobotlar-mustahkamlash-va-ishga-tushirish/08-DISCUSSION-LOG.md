# Phase 8: Hisobotlar, mustahkamlash va ishga tushirish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-13
**Phase:** 8-hisobotlar-mustahkamlash-va-ishga-tushirish
**Areas discussed:** Hisobot yuzasi va davr modeli; Excel eksport va shaxsiy ma'lumot chegarasi; AI aniqlik hisoboti yuzasi; Backup va tiklash mashqi; 3 tomonlama solishtiruv vositasi; Go-live runbook va mustahkamlash qarzlari

> ⚙ **`--auto` rejim** (foydalanuvchining doimiy `no-questions-autonomous-mode`
> ko'rsatmasi, 2026-08-01): har savolda tavsiya etilgan variant tanlandi,
> AskUserQuestion ishlatilmadi. Quyida har soha uchun ko'rilgan muqobillar.

---

## Hisobot yuzasi va davr modeli (RECON-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Yangi `/reports` bo'lim | Uch hisobot bitta direktor yuzasida, davr tanlovi bilan | ✓ |
| Mavjud sahifalarni kengaytirish | `/billing` va `/reconciliation` ga eksport tugmasi qo'shish | |

**Choice:** Yangi `/reports` — operativ yuza va davr-hujjat aralashtirilmaydi; kassir ko'rmaydi (T-06-53/59).

---

## Excel eksport va shaxsiy ma'lumot chegarasi

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side XlsxWriter + `_freeze_zip`, ism serverda joinlanadi (auditli hisobot marshruti) | 06 №9 ning «tabiiy egasi» yechimi; PERSONAL_ROUTES o'smaydi, bitta audit_read | ✓ |
| Klientda eksport (sheetjs) | Ism bo'shlig'i hal bo'lmaydi, determinizm yo'q | |
| Moliyaviy javobga vendor_name qo'shish | 06 №9 da AYNAN rad etilgan (C-10/§5.5) | |

---

## AI aniqlik hisoboti (RECON-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Mavjud `accuracy_report.py` yuzaga chiqariladi + xlsx | Yangi hisob yozilmaydi; formulalar 05-14 dan o'zgarmaydi | ✓ |
| Yangi hisobot xizmati | Ikkinchi haqiqat manbai — loyihada takror topilgan xato sinfi | |

**Notes:** WR-05 (yiqilgan so'rov «0 %») shu fazada «o'lchanmagan son chizilmaydi» qoidasi bilan yopiladi; AI-02 Blocked holati yashirilmaydi.

---

## Backup va tiklash mashqi (FOUND-07)

| Option | Description | Selected |
|--------|-------------|----------|
| restic + pg_dump, alohida compose `backup` xizmati, heartbeat kuzatuvi | CLAUDE.md qat'iy tanlovi; ko'chish oson; yo'qlik alerti | ✓ |
| Host cron + skript | Hujjatlashtirilmagan qo'l ishi, migratsiyada yo'qoladi | |
| pgBackRest/WAL | RPO<24h talab qilinmaguncha ortiqcha (CLAUDE.md) | |

**Notes:** Tiklash mashqi ikki qatlam — CI'da toza konteynerga pg_restore (mexanizm), real toza serverda bir martalik mashq (08-HUMAN-UAT, egasi Ops).

---

## 3 tomonlama solishtiruv vositasi (SC#5)

| Option | Description | Selected |
|--------|-------------|----------|
| xlsx import (2-faza infratuzilmasi) + ekran/xlsx chiqish + imzo qatorlari | Import yo'li o'lchangan; 300–1000 rasta uchun forma amaliy emas | ✓ |
| Kunlik qo'lda kiritish formasi | Hajm uchun yaroqsiz | |
| Raqamli imzo | Qog'oz jarayon yetarli, scope tashqarisida | |

**Notes:** Bajaruvchi nazoratchi/admin, KASSIR EMAS (ROADMAP Post-Launch). Phase 0 bazasiga bog'lanmaydi.

---

## Go-live runbook va mustahkamlash qarzlari (SC#4)

| Option | Description | Selected |
|--------|-------------|----------|
| `ops/docs/go-live.md` + HUMAN-UAT jamlanmasi + 13 WR/Info bandlari qamrovda | Egasi «8-faza» deb yozilgan hamma band rejaga kiradi yoki sababi yoziladi | ✓ |
| Faqat runbook, qarzlar keyinga | «Mustahkamlash haftasi» ta'rifiga zid — qarzlar aynan shu fazaniki | |

**Notes:** 07 №6 (dayjest kaliti) ATAYIN kengaytirilmaydi — bandning o'z tahlili yetarli; V2.

---

## Claude's Discretion

Huquq nomlari; jadval/ustun/endpoint nomlari; xlsx ustun tartibi; backup
konteyner image'i va heartbeat mexanikasi; solishtiruv sahifalash usuli;
13 WR ning rejalarga taqsimoti; SeaweedFS ko'zgusi uchun restic/rclone
tanlovi.

## Deferred Ideas

Direktor botining buyruq yuzasi (V2); sotuvchi botidan to'lov (V2);
07 №6 dayjest kaliti (V2); to'liq interaktiv xarita (v2); kassir
offline-lite (V2); AI-02 to'liq yopilishi (05-HUMAN-UAT, Ops);
Phase 0 bazasini ulash (operatsion amal).
