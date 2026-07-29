# Phase 1: Poydevor va tenant xavfsizligi - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Har foydalanuvchi o'z rolida, o'z bozorida, o'z tilida xavfsiz ishlaydi va har harakat o'chmas izda qoladi. Faza yetkazadi: auth + RBAC (5 rol), `market_id` + Postgres RLS tenant izolyatsiyasi (avtomatik cross-tenant test bilan isbotlangan), o'zgarmas audit jurnali (minimal ko'rish UI bilan), 3 tilli i18n skaffolding, biznes-kun (Asia/Tashkent) va BIGINT so'm pul poydevori, hamda moliyaviy jadvallarning dublikat-himoya/o'zgarmaslik konstraytlari (6-fazadan oldin o'rnida bo'lishi shart).

Talablar: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05. Loyiha skeleti (repo, Docker Compose, CI, dizayn-tizim asoslari) shu faza ichida — bu birinchi build fazasi, kod bazasi greenfield.

</domain>

<decisions>
## Implementation Decisions

### Kirish va sessiya siyosati
- **D-01:** Login identifikatori — **telefon raqami** (+998, E.164 normalizatsiya `phonenumbers` bilan) + parol. Email/username ishlatilmaydi. Telefon `users` jadvalida unique.
- **D-02:** Parol tiklash — **admin orqali**: bozor admini / platforma admini vaqtinchalik parol beradi, foydalanuvchi birinchi kirishda majburiy almashtiradi. Har tiklash auditda. SMS/email/bot-kod oqimi yo'q (MVP).
- **D-03:** Sessiya — **30 kun sliding refresh** (har faol ishlatilganda uzayadi); access token qisqa (stack: 15 daq, httpOnly cookie'da refresh). Kassir telefonida amalda qayta login so'ralmaydi.
- **D-04:** Foydalanuvchi yaratish — **ikki bosqichli**: platforma admini bozor va uning admin/direktorini yaratadi; bozor admini o'z bozori xodimlarini (kassir, nazoratchi) o'zi yaratadi. O'z-o'zidan ro'yxatdan o'tish yo'q. Foydalanuvchi boshqaruv UI (yaratish, bloklash, parol tiklash) 1-fazada.

### Rol va bozor biriktirish modeli
- **D-05:** Bitta foydalanuvchi = **bitta bozor + rollar TO'PLAMI** (masalan, bozor admini + kassir bir odamda). Sxema kelajakda ko'p-bozorga kengayadigan qilib quriladi (user↔market↔role strukturasi), lekin MVP UI faqat bitta bozor biriktiradi.
- **D-06:** Platforma admini — **bozor tanlab kiradi** (kontekst tanlash): global bozorlar ro'yxatini ko'radi, ichiga kirganda RLS o'sha bozorga o'rnatiladi. **RLS bypass yo'li yo'q**; harakatlari auditda "platforma admini X bozorida" sifatida yoziladi.
- **D-07:** Direktor — **faqat ko'rish + nizo qarori**: hisobotlar, dayjest, jonli kamera; nomuvofiqlik case qarori (7-faza). Rasta/tarif/xodim o'zgartirmaydi. Rol-huquq matritsasi kodda qat'iy (sozlanadigan permission tizimi emas).
- **D-08:** Bloklash — **darhol kuchga kiradi**: har so'rovda foydalanuvchi holati tekshiriladi (Valkey kesh bilan arzon qilinadi). Bloklangan kassir bir soniya ham to'lov kirita olmaydi.

### Audit jurnali qamrovi
- **D-09:** Qamrov — **barcha moliyaviy/ma'muriy o'zgarishlar + shaxsiy ma'lumot O'QISHLARI ham** (kim qaysi sotuvchining qarzini/ma'lumotini ko'rdi). O'zR shaxsiy ma'lumotlar qonuni ostida himoya; davlat bosqichiga tayyor. Texnik/pipeline yozuvlari (snapshot olish va h.k.) audit jurnaliga kirmaydi.
- **D-10:** Mexanizm — **moliyaviy jadvallarda DB-trigger** (`daily_charges`, `charge_adjustments`, `payments`, `tariffs`, `stall_assignments` — hech qanday kod yo'li chetlab o'tolmaydi), qolgan jadvallarda app-qatlam. Audit jadvalidan app DB-roliga UPDATE/DELETE huquqi umuman berilmaydi (append-only).
- **D-11:** Ko'rish huquqi — **platforma admini + direktor + bozor admini**, har biri o'z bozori doirasida (RLS ostida). Auditni ko'rish ham audit-o'qish sifatida yoziladi.
- **D-12:** Ko'rish UI — **minimal filtrlanadigan ro'yxat 1-fazada** (kim / qachon / nima / eski→yangi). Muvaffaqiyat mezoni #3 ko'rsatib isbotlanadi; keyingi fazalarda boyitiladi.

### Til mexanikasi
- **D-13:** Til tanlovi — **foydalanuvchi profilida (DB)** saqlanadi + cookie tez routing uchun. 7-fazada bot xabarlari ham shu manbadan oladi — bitta haqiqat manbai.
- **D-14:** Kirillcha — **build-time avto-transliteratsiya** uz-Latn → uz-Cyrl + qo'lda tuzatish lug'ati (е/э, ь, o'zlashma so'zlar). Tarjima yuzasi: uz-Latn (asosiy) + ru qo'lda, uz-Cyrl generatsiya.
- **D-15:** Standart til — **har doim uz-Latn** (brauzer Accept-Language'dan aniqlash YO'Q). Bir bosishda almashtiriladi va profilda qoladi.
- **D-16:** DB kontent (toifa/zona nomlari, rekvizitlar) — **bir tilda qoladi** (qanday kiritilgan bo'lsa shunday ko'rinadi). Faqat interfeys (UI chrome) 3 tilda. Multi-til kontent sxemasi qurilmaydi.

### Claude's Discretion
- JWT tuzilishi, token claim'lari, refresh-rotatsiya detali — stack hujjati doirasida (PyJWT, pwdlib[argon2]).
- RLS policy sintaksisi, `SET LOCAL` mexanikasi, TenantScopedRepository dizayni — tadqiqot tavsiyalari asosida.
- Audit jadval sxemasi (JSONB diff formati, indekslash) va o'qish-audit qayerda yozilishi (middleware vs endpoint).
- Dizayn-tizim komponentlari va login/shell UI detallari (Apple-uslub minimal, PROJECT.md cheklovi doirasida).
- Docker Compose skeleti, CI quvuri, migratsiya tartibi.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Mahsulot va talablar
- `SBOZOR-MVP-texnik-topshiriq.md` — asosiy manba (v1.1): §3 rollar jadvali, §5 arxitektura, §6 ma'lumotlar modeli (jadval ro'yxati, BIGINT so'm, UTC/Tashkent), §7 UI/i18n tamoyillari
- `.planning/REQUIREMENTS.md` — FOUND-01…05 matni va traceability
- `.planning/PROJECT.md` — cheklovlar (stek, 3 servis, litsenziya) va Key Decisions jadvali
- `.planning/ROADMAP.md` — 1-faza muvaffaqiyat mezonlari (5 ta), fazalar chegarasi

### Texnik tadqiqot (1-fazaga tegishli bo'limlar)
- `.planning/research/ARCHITECTURE.md` — monorepo strukturasi (`packages/sbozor-core`: models, tenancy.py, money.py, timeutil.py), RLS + composite FK, `tests/tenancy/` meta-test, bitta Alembic tarixi
- `.planning/research/PITFALLS.md` — cross-tenant izolyatsiya (RLS backstop + app-filter + CI cross-tenant test: A tokeni bilan B obyektiga 404; `SET LOCAL` transaction ichida, session emas; composite indekslar `market_id` bilan boshlanadi); M10 audit teshiklari (DB-trigger tavsiyasi); moliyaviy o'zgarmaslik (append-only, computed balance)
- `.planning/research/STACK.md` va `CLAUDE.md` — versiyalar va taqiqlar: PyJWT (python-jose EMAS), pwdlib[argon2] (passlib EMAS), next-intl + `proxy.ts` (middleware.ts EMAS Next 16'da), postgres:18.4, uv per-service pyproject

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Kod bazasi greenfield — hali kod yo'q. Bu faza repo skeletini (monorepo strukturasi, Docker Compose, CI, per-service pyproject) o'zi yaratadi.

### Established Patterns
- `.planning/research/ARCHITECTURE.md` da tayyor struktura-reja bor: `packages/sbozor-core` (modellar/enum/infra, biznes logikasiz), `services/{core-api,cv-service,bot-service}`, `migrations/` ildizda (bitta Alembic tarixi), `tests/tenancy/` meta-test.
- Stack qat'iy versiyalar bilan CLAUDE.md'da qulflangan — kutubxona tanlash bu fazada qayta muhokama qilinmaydi.

### Integration Points
- 2-faza (wizard) shu fazaning auth/RBAC/RLS ustiga quriladi; 6-faza moliyaviy jadvallar shu fazada tug'iladigan konstraytlarga (`UNIQUE(market_id, stall_id, business_date)`, append-only) tayanadi.
- i18n skaffolding (next-intl, uchala til fayli, transliteratsiya skripti) shu fazada o'rnatiladi — keyingi barcha frontend fazalari shu tizimga matn qo'shadi.

</code_context>

<specifics>
## Specific Ideas

- Telefon-login tanlovining sababi: kelajakda Telegram-bot (7-faza) bilan bir xil identifikator — sotuvchi reestri ham telefon asosida.
- Platforma adminining "bozor tanlab kirish" modeli auditda aniq iz qoldirishi kerak: "platforma admini X bozorida Y qildi".
- Bir odam ikki vazifa (admin + kassir) — Karmana kabi kichik bozorlarda real hol; rollar to'plami shu uchun.

</specifics>

<deferred>
## Deferred Ideas

- Ko'p-bozorli foydalanuvchi (bir direktor ikki bozorda) — sxema tayyor bo'ladi, UI va bozor almashtirgich keyingi bosqichda (v2)
- Parol tiklash Telegram-bot orqali — bot 7-fazada kelgach ko'rib chiqilishi mumkin
- Maker-checker tarif tasdiqlash (direktor tasdiqlaydi) — v2 nomzodi
- Sozlanadigan permission tizimi (rol-huquq matritsasini bozor kesimida o'zgartirish) — MVP'da qat'iy kodda

</deferred>

---

*Phase: 1-Poydevor va tenant xavfsizligi*
*Context gathered: 2026-07-29*
