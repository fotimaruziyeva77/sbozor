---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
reviewed: 2026-08-12
depth: standard
status: issues_found
files_reviewed: 62
findings:
  blocker: 9
  warning: 26
  info: 8
  total: 43
parts:
  - 07-REVIEW-backend.md
  - 07-REVIEW-frontend.md
---

# 7-faza — kod ko'rigi (birlashtirilgan indeks)

Ko'rik **ikkita parallel agentga** bo'lindi: fazaning diffi 125 faylni o'zgartirgan,
bu bitta ko'ruvchi uchun yuzaki natija berardi.

**Qamrov:** 62 ta ishlab chiqarish fayli.
**Ataylab qamrovdan tashqarida:** 63 ta test fayli — bu fazada ijrochilarning o'zlari
testlarni sabotaj bilan o'lchagan va aynan shu yo'l bilan bir nechta darvoza nuqsonini
topgan (07-14 ning `MIN_COMPONENTS` chegarasi, 07-15 ning bo'sh-bo'shiga yashil bo'lgan
uchta asserti). Qayta ko'rish qiymat qo'shmasdi.

| Qism | Fayl | Ko'rilgan | Blocker | Warning | Info |
|------|------|-----------|---------|---------|------|
| Backend | [07-REVIEW-backend.md](07-REVIEW-backend.md) | 26 | 4 | 10 | — |
| Frontend + bot + infra | [07-REVIEW-frontend.md](07-REVIEW-frontend.md) | 36 | 5 | 16 | 8 |
| **Jami** | | **62** | **9** | **26** | **8** |

## Nega bu topilmalar rejalar darvozalaridan o'tib ketgan

Har bir reja **izolyatsiyalangan git worktree'da** bajarildi va faqat o'zi ko'rgan kodni
sinay oldi. Quyidagi nuqsonlarning deyarli hammasi **ikki reja chegarasida** yotadi —
ya'ni ularni birlashgan natijadan boshqa hech qayerdan ko'rib bo'lmasdi.

Eng kuchli dalil: **ikkala ko'ruvchi bir-biridan mustaqil, qarama-qarshi tomonlardan
bir xil nuqsonni topdi** — `assignee_user_id` ning jimgina tashlanishi (backend CR-02,
frontend CR-01). Bittasi marshrutdan, ikkinchisi dialogdan qaragan.

## Blockerlar — birlashtirilgan ro'yxat

### B-1. Dayjest produksiyada hech qachon yetib bormaydi *(backend CR-01)*

`market_notification_settings` jadvaliga **yozuv yo'li umuman yo'q** — repoda unga
`INSERT` qiladigan kod yo'q (migratsiya, usta, `/api/v1/*`, `/internal/bot/*`, bot
handlerlari). Direktor handleri ham yaratilmagan.

Zanjir: `digest_morning`/`digest_evening` har kuni qator yozadi → `resolve_chat_id()`
`None` qaytaradi → `_settle()` da `UNRESOLVED` shoxi `MAX_ATTEMPTS` tekshiruvidan
**chetlab o'tadi** → qator abadiy `pending` → yiliga ~730 o'lik qator/bozor → ular
`_CLAIM_DUE` ning `ORDER BY o.created_at` da eng eski → ~250 kundan keyin
`OUTBOX_BATCH_SIZE = 500` to'ladi → **kvitansiya umuman jo'natilmay qoladi**
(head-of-line blocking).

⚠ **Nega 07-17 ning mezoni yashil:** test `respx` bilan tarmoq chegarasini ushlaydi va
sozlama qatorini fixture'da o'zi yozadi. Test rost — mahsulot produksiyada ishlamaydi.
Bu darvozaning nuqsoni emas, qamrovining chegarasi.

### B-2. `assignee_user_id` jimgina tashlanadi + tenancy teshigi *(backend CR-02, frontend CR-01)*

Frontend uni haqiqatan yuboradi (`reconciliation-queries.ts:629-633`),
`CaseUpdateRequest` uni `extra="forbid"` ostida e'lon qiladi, marshrut
(`api/v1/reconciliation.py:657-666`) esa hech qachon o'qimaydi va `transition()` da
bunday parametr ham yo'q. SQL: `assignee_user_id = COALESCE(:actor_user_id, ...)`.

Oqibat: mas'ul har doim **o'tishni qilgan odam**; direktorning tanlovi tashlanadi;
har holat o'zgarishi mavjud biriktirishni jimgina o'g'irlaydi; `<option value="">
Biriktirilmagan</option>` imkonsiz amalni va'da qiladi (`COALESCE` `NULL` ni
e'tiborsiz qoldiradi); javob esa `200`.

⛔ Maydonni shunchaki "ulab qo'yish" **tenancy teshigini ochadi**: `user_market_roles`
ustidan begona-bozor tekshiruvi hech qayerda yo'q, `0023:344-347` esa uni "ilova
qatlamida" deb yozgan.

### B-3. `outbox_tick` vaqt byudjetini o'lchamaydi → kvitansiya ikki marta *(backend CR-03)*

`OUTBOX_TICK_BUDGET_SECONDS = 20` hech qayerda o'qilmaydi (faqat `OUTBOX_BATCH_SIZE`
ni hisoblashda). `_Throttle` 25 msg/s ni butun tik uchun qo'llaydi, tsikl esa hamma
bozor bo'ylab ketma-ket yuradi → 7+ to'la navbatli bozorda tik
`OUTBOX_LEASE_SECONDS (120)` dan oshadi → `release_expired_leases()` in-flight qatorni
`pending` ga qaytaradi → **kvitansiya ikki marta ketadi**.

`dedupe_key` buni ushlamaydi — u faqat `enqueue` bosqichida ishlaydi.
Qo'shimcha: `now` tik boshida bir marta olinadi, ya'ni ijara va backoff eskirgan
paytdan hisoblanadi.

### B-4. `attempt_count` `claim()` da oshadi, kafolat esa buni taqiqlaydi *(backend CR-04)*

`_CLAIM_DUE` shartsiz `attempt_count + 1` qiladi; `_settle()` faqat *tekshiruvni*
`RETRY` ga cheklaydi. Botga ulanmagan sotuvchi: 96 `attempt_count++`/kun → 3 kundan
keyin ulanadi → birinchi vaqtinchalik `502` da `288 >= 5` → darhol `failed`, qayta
urinishsiz. Docstringning o'zi aynan shu natijani taqiqlagan.

### B-5. Har qanday saqlash xatosi matnsiz o'tadi *(frontend CR-02)*

`case-detail-dialog.tsx:342-344, 426-434`: `reconErrorView()` besh koddan boshqasi
uchun `null` qaytaradi va chaqiruvchi **hech nima chizmaydi** — `NetworkError`, `422`,
`429`, `5xx`, `market_not_selected` hammasi jim. `reconciliation-errors.ts:106-108`
"chaqiruvchi `errors.generic` ga tushadi" deb yozadi; yagona chaqiruvchi buni bajarmaydi.

### B-6. Navbat 50 qatorda jimgina qirqiladi *(frontend CR-05)*

`next_cursor` uchala sxemada parse qilinadi, `CASE_PAGE_SIZE = 50` e'lon qilingan —
**hech qayerda ishlatilmaydi**. Sanoqlar server kontrakti bo'yicha kun bo'yicha to'liq
keladi, jadval esa 50 ta. Direktor "Yangi 120" yozuvini va 50 qatorni ko'radi,
qolganiga yo'l yo'q.

### B-7. Ikkinchi qaror jim tashlanadi *(frontend CR-04)*

`submittedRef` `case_id` ni saqlaydi va faqat `onError` da bo'shaydi; dialog
muvaffaqiyatda yopilmaydi. `new→in_review` dan keyin `in_review→justified` bosilganda
`blocked` false (tugma faol ko'rinadi), lekin `onSave` jim `return` qiladi.

### B-8. `npm run up` botni ko'tarmaydi *(frontend CR-03)*

`package.json:7` servislarni nomma-nom sanaydi, `bot-service` ro'yxatda yo'q;
`compose.yaml:601-605` esa "`npm run up` uni ham ko'taradi" deydi. Diff tasdiqlaydi:
`up` bu fazada tegilmagan.

### B-9. `bot-tests` prod tokenini meros oladi *(frontend WR-10, blocker sinfi)*

`${TELEGRAM_BOT_TOKEN:-…}` orqali. Compose izohi (719) buni inkor qiladi, lekin
`bot-service` bloki o'sha kalitni standartsiz talab qilgani uchun ishlaydigan har
qanday `.env` da u to'ldirilgan bo'ladi — ya'ni testlar haqiqiy bot tokeni bilan
yuguradi.

## Toza chiqqan joylar

- **Sxema qatlami:** `0023`, XOR/diskriminator, qisman UNIQUE indekslar, kaskad tartibi,
  `case_event_immutable()` — nuqsonsiz.
- **Sirlar:** `SecretStr`, `hmac.compare_digest`, `_LAST_FAILURE` `ContextVar`,
  `_validate_error_type()` — to'g'ri.
- **Pul:** hech qayerda `float` ga aylanmaydi (loyihaning qattiq cheklovi).
- **Locale:** 1207 kalit, uchala JSON'da **0 yetishmovchilik**, **0 ICU platsholder
  farqi**; `.po` msgid to'plamlari teng. "Bir tilda bor, boshqasida yo'q" defekti yo'q —
  buning o'rniga *hech bir tilda erishib bo'lmaydigan* matn topildi (WR-16).
- Debug artefakt yo'q.

## Batafsil

Warning va Info darajasidagi 34 ta topilma qismlar fayllarida:
[07-REVIEW-backend.md](07-REVIEW-backend.md) · [07-REVIEW-frontend.md](07-REVIEW-frontend.md)
