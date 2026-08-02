# Phase 3: NVR avtomatik kashfiyoti va tarmoq ulanishi — Context

**Gathered:** 2026-08-03
**Status:** Ready for planning
**Source:** 2026-08-01 mahsulot direktivasi + `03-RESEARCH.md` ning 7 ochiq savoli (hammasi taklif qilingan standart qiymatda qulflandi)

<domain>
## Phase Boundary

**Bu fazada:** NVR qurilmasini ro'yxatga olish (manzil + login/parol), Hikvision ISAPI orqali avtomatik kashfiyot (qurilmani aniqlash + kanallarni sanash + kameralarni avtomat yaratish), idempotent qayta skanerlash, ulanish testi va sababi ko'rsatilgan xatolar, hisob ma'lumotlarining Fernet shifri, WireGuard split-tunnel, avtorizatsiya ortidagi jonli ko'rish, va **buning hammasini real uskunasiz isbotlaydigan simulyatsiya qilingan Hikvision NVR**.

**Bu fazada EMAS:** snapshot jadvali va kadr olish (Phase 4), kamera-zona poligonlari va CV (Phase 5). Kameralar shu fazada tug'iladi, lekin ulardan kadr olish keyingi fazada.

</domain>

<decisions>
## Implementation Decisions

### Mahsulot qoidasi (majburiy, 2026-08-01)

- **D-01**: Admin saytga **faqat** NVR manzili + login/parolni kiritadi. Qo'lda RTSP URL yozish, qo'lda kamera qo'shish yoki har kamerani sozlash — **yo'q**. Muhandis aralashuvi talab qiladigan har qanday yechim fazani buzadi.
- **D-02**: Xato hech qachon "ulanmadi" degan quruq xabar bo'lmaydi — **sababi va tuzatish yo'li** ko'rsatiladi. Tadqiqot topilmasi: noto'g'ri parol, soat farqi va bloklangan hisob **uchalasi ham 401** qaytaradi, ya'ni status kod farqlamaydi. Farq qurilmaning `Date` sarlavhasini mahalliy UTC bilan solishtirib aniqlanadi — bu drift'ni **auth muvaffaqiyatsiz bo'lishidan oldin** ushlaydi.
- **D-03**: **401 ni qayta urinish TAQIQLANADI** — Hikvision hisobni bloklaydi (~5 urinish / 30 daqiqa). Retry siyosati odatdagiga teskari: tarmoq xatosida qayta urinamiz, autentifikatsiya xatosida **hech qachon**.

### Tadqiqotning 7 ochiq savoli — hammasi standart qiymatda qulflandi

- **D-04** (OQ-1): `DS-7616NI-K2` (16 kanal) va `DS-7732NI-M4` (32 kanal) **real yozib olingan fixture**'lari bilan ishlanadi. Kod `deviceType`/`model` ga qarab **tarmoqlanadi**, qotib qolmaydi. Fixture o'zimiz o'ylab topgan XML bo'lmasligi shart — aks holda test faqat o'z taxminimizni tasdiqlaydi.
- **D-05** (OQ-2): Sessiya limiti RTSP darajasida qanday ko'rinishi noaniq (`453`/`503` yoki jimgina uzilish) — **ikkala stsenariy ham** simulyatorda modellashtiriladi. Xabar "**ehtimol** sessiya limitiga yetildi" deydi va `error_detail` da xom javobni saqlaydi. Heuristika sozlanadigan.
- **D-06** (OQ-3): Navbat — **`taskiq` + `taskiq-redis 1.2.3`**. (`arq` o'rnatib bo'lmaydi: `redis[hiredis]<6` talab qiladi, core-api `8.0.1` ga qadalgan — 2026-08-02 da PyPI metadata bilan tasdiqlandi.) **Job'lar sof `async def` funksiya sifatida yoziladi, taskiq dekoratori faqat yupqa qobiq** — Phase 4 boshqa mexanizmni tanlasa ko'chirish ~10 qator. Ikki mexanizm bir vaqtda saqlanmaydi.
- **D-07** (OQ-4): `nvr_devices.tunnel_subnet` (`cidr`) maydoni **hozirdan** qo'shiladi + **bozorlar aro global noyoblik tekshiruvi**. Ko'p tarmoq `192.168.1.0/24` ishlatadi, ya'ni ikkinchi bozor qo'shilganda VPS marshrut jadvali chalkashadi. To'qnashuvda onboarding'da aniq xato beriladi. `1:1 NAT` yechimi hujjatlashtiriladi, implement qilinmaydi.
- **D-08** (OQ-5): Jonli ko'rish tokeni — **qisqa muddatli JWT** (`aud="live"`, `exp<=60s`, ichida `camera_id` + `market_id` + `user_id`). 60 soniya bekor qilishni keraksiz qiladi; mavjud `tokens.py` qayta ishlatiladi.
- **D-09** (OQ-6): Simulyator CI'da **6 kanal** (tez, `DS-7616NI-K2` fixture'iga mos). **25 kanal** — alohida sekin test (`-m slow`). `stream_limit` testi **4** bilan.
- **D-10** (OQ-7): Kamerani o'chirish — **soft-delete** (`is_archived`). Qattiq `DELETE` **hech qachon**: snapshot va zona bog'lanishlari saqlanishi kerak. Arxivlangan kanal qayta skanda **tiklanmaydi** (`is_archived` `name_overridden` kabi ishlaydi). Qayta skan hech qachon `DELETE` qilmaydi.

### Xavfsizlik (tadqiqotda topilgan, muzokara qilinmaydi)

- **D-11**: **go2rtc'ning HTTP API'si hech qachon foydalanuvchiga proksilanmaydi.** `PUT /api/streams?src=exec:…` ixtiyoriy buyruq bajaradi (GHSA-wwww-5h25-jf98, CVSS 9.1). core-api uzatadigan har qanday `src` faqat `rtsp://` sxemasi bilan allow-list qilinadi. go2rtc — ishonchli tarmoq ichidagi ichki servis.
- **D-12**: NVR paroli Fernet bilan shifrlangan saqlanadi va **hech qachon** API javobida, jurnalda yoki audit yozuvida ko'rinmaydi. Phase 1 allaqachon `nvr_password`/`rtsp_password` ni `SENSITIVE_KEYS` ga qo'shgan — buni **tasdiqlash kerak, taxmin qilmaslik**.
- **D-13**: WireGuard `AllowedIPs` **faqat NVR subneti**, hech qachon `0.0.0.0/0`. To'liq tunnel VPS'ning butun chiqish trafigini bozorning DSL'i orqali yuboradi va Telegram, Let's Encrypt va foydalanuvchilar trafigini birga o'ldiradi. Tunnel yagona yo'l ekani **test bilan isbotlanadi** (tunnel o'chsa ulanish uziladi).
- **D-14**: CGNAT mahsulot muammosi emas — bozor tomonida oldindan sozlangan qurilma `PersistentKeepalive = 25` bilan o'zi qo'ng'iroq qiladi. Admin uni faqat rozetkaga ulaydi.

### Wave 0 blokerlar (tadqiqot kodni o'qib topgan — reja BULARDAN boshlanadi)

- **D-15**: `services/core-api/app/security/rbac.py` da `PLATFORM_ADMIN` da `CAMERA_VIEW` **yo'q**, `CAMERA_MANAGE` esa umuman **mavjud emas**. Bu Phase 2 ning Pitfall 6 ining aynan takrori — o'shanda ham rol matritsasi yangi domendan orqada qolgan edi.
- **D-16**: `httpx` core-api'ning `[dependency-groups] dev` guruhida turibdi, lekin ISAPI klienti **ishlab chiqarish kodi**. Uni `[project] dependencies` ga ko'chirmasa — **hamma testlar yashil bo'lgani holda deploy'da import xatosi**.
- **D-17**: **WR-02 (2-fazadan eskalatsiya, YUQORI ustuvorlik):** `market_delete_draft()` o'n ikki jadval bo'ylab kaskad o'chiradi va yagona chegarasi ilova qatlamida. Bu fazada migratsiya bilan DB darajasida cheklanadi; qoralama bo'lmagan bozorni o'chirish imkonsizligi test bilan isbotlanadi.

### Claude's Discretion

Sxema tafsilotlari (jadval/ustun nomlari, indekslar), ISAPI klientining ichki tuzilishi, simulyatorning implementatsiya tili va freymvorki, UI komponentlarining parchalanishi, test fayllarining nomlanishi — mavjud `02-PATTERNS.md` konventsiyalariga mos bo'lsa yetarli.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agentlar rejalashtirish yoki implementatsiyadan OLDIN o'qishi SHART.**

### Fazaning o'z tadqiqoti
- `.planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-RESEARCH.md` — 1838 qator; ISAPI endpointlari va javob shakllari, simulyator dizayni, `## Validation Architecture`, manbalar bilan

### Loyiha darajasidagi qarorlar
- `CLAUDE.md` — stek yozuvi; **`arq` → `taskiq` o'zgarishi**, go2rtc RCE ogohlantirishi va `httpx` dev-guruh tuzog'i 2026-08-02 da yozildi
- `.planning/ROADMAP.md` — «Mahsulot qoidasi: self-service onboarding (MAJBURIY)» bo'limi va Phase 3 ning 8 mezoni

### Qayta ishlatiladigan naqshlar
- `.planning/phases/02-bozor-domeni-va-yangi-bozor-ustasi/02-PATTERNS.md` — kod konventsiyalari
- `.planning/phases/02-bozor-domeni-va-yangi-bozor-ustasi/02-19-SUMMARY.md` — `audit_read` + marshrut darajasidagi permission naqshi (kamera marshrutlariga aynan shu qo'llanadi)
- `.planning/phases/01-poydevor-va-tenant-xavfsizligi/` — RLS, `SENSITIVE_KEYS`, `tokens.py`

</canonical_refs>

<specifics>
## Specific Ideas

- ISAPI kashfiyot endpointlari: `/ISAPI/System/deviceInfo` (model/firmware/serial), `/ISAPI/ContentMgmt/InputProxy/channels` (**NVR'da avtoritetli**), `/ISAPI/System/Video/inputs/channels` (bo'sh slotlarni ham sanaydi — avtoritetli EMAS)
- RTSP porti `/ISAPI/Security/adminAccesses` dan **aniqlanadi**, 554 deb taxmin qilinmaydi
- Kanal raqamlash: `{ch}01` asosiy oqim, `{ch}02` sub oqim
- Simulyator mavjud emas (ikki mustaqil qidiruv bilan tasdiqlangan) — quriladi; fixture'lar `hikvision_next` ning real dumplaridan
- Simulyator **xato rejimlarini** ham modellashtiradi: noto'g'ri parol (401 + Digest challenge), soat farqi, `digest`-only firmware, offline kanal, sessiya limiti
- Compose'da `--profile sim` — ishlab chiqarishga hech qachon chiqmaydi

</specifics>

<deferred>
## Deferred Ideas

- `1:1 NAT` subnet to'qnashuvi yechimi — hujjatlashtiriladi, implement qilinmaydi (ikkinchi bozor kelganda)
- ONVIF avtomatik kashfiyoti (noma'lum brend kameralar uchun) — Hikvision yetarli; keyingi milestone
- Kamerani qattiq o'chirish — hech qachon (D-10)
- Real uskunada tasdiqlash — `03-VALIDATION.md` ning inson bandlari; fazani bloklamaydi (self-service qoidasi)

</deferred>

---

*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Context gathered: 2026-08-03 — mahsulot direktivasi + tadqiqot standartlari*
