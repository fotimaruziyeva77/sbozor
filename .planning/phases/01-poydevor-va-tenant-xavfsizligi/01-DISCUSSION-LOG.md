# Phase 1: Poydevor va tenant xavfsizligi - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 1-Poydevor va tenant xavfsizligi
**Areas discussed:** Kirish va sessiya siyosati, Rol va bozor biriktirish modeli, Audit jurnali qamrovi, Til mexanikasi

---

## Kirish va sessiya siyosati

**Savol 1: Panel foydalanuvchilari tizimga nima bilan kiradi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Telefon raqami (Tavsiya) | +998 formatda, parol bilan; O'zbekiston kontekstida tabiiy; phonenumbers normalizatsiya; bot bilan bir xil identifikator | ✓ |
| Username (login so'zi) | Eng sodda, infra kerak emas; unutiladi, reestr bilan bog'lanmaydi | |
| Email | Klassik SaaS, lekin bozor xodimlarida email kam | |

**Savol 2: Parol tiklash oqimi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Admin tiklaydi (Tavsiya) | Vaqtinchalik parol, birinchi kirishda majburiy almashtirish; har tiklash auditda | ✓ |
| Telegram-bot orqali kod | Bot 7-fazada — 1-fazada ishlamaydi | |
| SMS kod | SMS kanal MVP qamrovidan tashqarida | |

**Savol 3: Sessiya (refresh token) muddati?**

| Option | Description | Selected |
|--------|-------------|----------|
| 30 kun, harakat uzaytiradi (Tavsiya) | Sliding; kassir deyarli qayta kirmaydi; yo'qolgan telefon — admin bloklash bilan yopiladi | ✓ |
| 7 kun qat'iy | Haftada bir qayta kirish; dala xodimlariga ishqalanish | |
| Har kuni (12 soat) | Har smena qayta kirish; ≤3 bosish tamoyiliga zid | |

**Savol 4: Foydalanuvchilarni kim yaratadi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Ikki bosqichli (Tavsiya) | Platforma admini → bozor + admin/direktor; bozor admini → o'z xodimlari (kassir, nazoratchi) | ✓ |
| Faqat platforma admini | Pilot uchun sodda, masshtabda to'siq | |
| 1-fazada seed, UI keyin | Eng tez, lekin FOUND-01 chala ko'rinadi | |

---

## Rol va bozor biriktirish modeli

**Savol 1: Bitta foydalanuvchi nechta rol va bozorga ega bo'la oladi?**

| Option | Description | Selected |
|--------|-------------|----------|
| 1 bozor, bir nechta rol (Tavsiya) | Rollar to'plami (admin + kassir); telefon-login cheklovi bilan mos; sxema ko'p-bozorga kengayadigan | ✓ |
| 1 bozor, 1 rol | Eng sodda; ikki vazifa = ikkinchi SIM — dala to'sig'i | |
| Ko'p bozor, ko'p rol | To'liq moslashuvchan; MVP'da ortiqcha murakkablik | |

**Savol 2: Platforma admini bozorlar ma'lumotiga qanday kiradi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Bozor tanlab kiradi (Tavsiya) | Kontekst tanlash; RLS o'sha bozorga o'rnatiladi; toza audit iz, bypass yo'q | ✓ |
| Hamma narsani bir vaqtda ko'radi | RLS bypass; izolyatsiya kafolati zaiflashadi | |
| Faqat bozor yaratish/sozlash | Eng qattiq; support/debugging imkonsiz | |

**Savol 3: Direktor huquqlari?**

| Option | Description | Selected |
|--------|-------------|----------|
| Faqat ko'rish + nizo qarori (Tavsiya) | Hisobotlar, dayjest, jonli kamera, case qarori (7-faza); spec §3 ga mos | ✓ |
| Ko'rish + tarif tasdiqlash | Maker-checker; MVP'ga qo'shimcha workflow | |
| To'liq boshqaruv | Rollar chegarasi yo'qoladi | |

**Savol 4: Bloklash qachon kuchga kiradi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Darhol (Tavsiya) | Har so'rovda holat tekshiruvi (Valkey kesh); moliyaviy tizimda to'g'ri standart | ✓ |
| ≤15 daqiqa ichida | Token muddatigacha ishlaydi; bloklangan kassir 15 daqiqa to'lov kirita oladi | |

---

## Audit jurnali qamrovi

**Savol 1: Audit jurnaliga nima yoziladi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Yozuvlar + shaxsiy o'qishlar (Tavsiya) | Moliyaviy/ma'muriy o'zgarishlar + shaxsiy ma'lumot o'qishlari; O'zR qonuni; davlat bosqichiga tayyor | ✓ |
| Faqat o'zgarishlar | FOUND-03 minimal; "kim ko'rgan" javobsiz | |
| Hamma narsa, har jadvalda | Signal shovqinga ko'miladi | |

**Savol 2: Yozish mexanizmi va o'zgarmaslik kafolati?**

| Option | Description | Selected |
|--------|-------------|----------|
| DB-trigger moliyaviyda (Tavsiya) | Moliyaviy jadvallar trigger bilan (raw SQL chetlab o'tolmaydi), qolgani app-qatlam; app-rolga UPDATE/DELETE yo'q | ✓ |
| Faqat app-qatlam | Sodda, lekin M10 pitfall — insayder teshigi | |
| Hammasi DB-trigger | O'qish-audit baribir app kerak; migratsiya og'irlashadi | |

**Savol 3: Audit jurnalini kim ko'radi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Platf. admin + direktor + bozor admini (Tavsiya) | Har biri o'z bozori doirasida (RLS); ko'rish ham audit-o'qish sifatida yoziladi | ✓ |
| Platf. admin + direktor | Bozor admini ko'rmaydi — diagnostika cheklanadi | |
| Faqat platforma admini | Direktor nazorat vositasisiz | |

**Savol 4: Ko'rish UI 1-fazada?**

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal ro'yxat 1-fazada (Tavsiya) | Filtrlanadigan ro'yxat (kim/qachon/nima/eski→yangi); mezon #3 isbotlanadi | ✓ |
| Faqat yozish, UI keyin | Mezon #3 faqat SQL bilan ko'rsatiladi | |

---

## Til mexanikasi

**Savol 1: Til tanlovi qayerda saqlanadi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Profil + cookie (Tavsiya) | DB'da profil, cookie routing uchun; bot ham shu manbadan (7-faza) | ✓ |
| Faqat cookie | Qurilma almashsa yo'qoladi | |
| Faqat URL | Har safar qayta tanlash | |

**Savol 2: O'zbek-kirill tarjimalari qanday yaratiladi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Avto-transliteratsiya (Tavsiya) | Build-time uz-Latn → uz-Cyrl + qo'lda tuzatish lug'ati; tarjima yuzasi 1/3 ga qisqaradi | ✓ |
| Qo'lda alohida fayllar | Har matn 3 joyga; kirillcha orqada qoladi | |

**Savol 3: Standart til qanday aniqlanadi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Har doim uz-Latn (Tavsiya) | Spec asosiy til; bashoratli | ✓ |
| Brauzer tilidan aniqlash | Ru-sozlangan telefonlarda chalkashlik | |

**Savol 4: Admin kiritadigan DB kontent tarjima qilinadimi?**

| Option | Description | Selected |
|--------|-------------|----------|
| Bir tilda qoladi (Tavsiya) | Faqat UI 3 tilda; sxema sodda, wizard tez | ✓ |
| 3 tilda kiritiladi | Wizard'da 3× kiritish yuki; ≤3 kun onboarding mezoniga zid | |
| Avto-transliteratsiya DB'da ham | Ru uchun ishlamaydi | |

---

## Claude's Discretion

- JWT tuzilishi, token claim'lari, refresh-rotatsiya detali (stack doirasida: PyJWT, pwdlib[argon2])
- RLS policy sintaksisi, `SET LOCAL` mexanikasi, TenantScopedRepository dizayni
- Audit jadval sxemasi (JSONB diff, indekslash), o'qish-audit yozish nuqtasi (middleware vs endpoint)
- Dizayn-tizim komponentlari, login/shell UI detallari
- Docker Compose skeleti, CI quvuri, migratsiya tartibi

## Deferred Ideas

- Ko'p-bozorli foydalanuvchi (bir direktor ikki bozorda) — sxema tayyor, UI v2
- Parol tiklash Telegram-bot orqali — bot kelgach (7-fazadan keyin)
- Maker-checker tarif tasdiqlash — v2 nomzodi
- Sozlanadigan permission tizimi — MVP'da qat'iy kodda
