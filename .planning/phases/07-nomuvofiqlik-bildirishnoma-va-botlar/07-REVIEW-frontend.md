---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
reviewed: 2026-08-12T00:00:00Z
depth: standard
files_reviewed: 36
files_reviewed_list:
  - services/bot-service/Dockerfile
  - services/bot-service/pyproject.toml
  - services/bot-service/app/__init__.py
  - services/bot-service/app/core_client.py
  - services/bot-service/app/handlers/__init__.py
  - services/bot-service/app/handlers/binding.py
  - services/bot-service/app/handlers/start.py
  - services/bot-service/app/handlers/vendor.py
  - services/bot-service/app/i18n.py
  - services/bot-service/app/main.py
  - services/bot-service/app/observability.py
  - services/bot-service/app/settings.py
  - services/bot-service/app/locales/uz_Latn/LC_MESSAGES/bot.po
  - services/bot-service/app/locales/uz_Cyrl/LC_MESSAGES/bot.po
  - services/bot-service/app/locales/ru/LC_MESSAGES/bot.po
  - frontend/src/app/[locale]/(app)/dashboard/page.tsx
  - frontend/src/app/[locale]/(app)/reconciliation/page.tsx
  - frontend/src/components/headline/headline-card.tsx
  - frontend/src/components/reconciliation/case-detail-dialog.tsx
  - frontend/src/components/reconciliation/case-list.tsx
  - frontend/src/components/reconciliation/case-status-badge.tsx
  - frontend/src/components/reconciliation/day-picker.tsx
  - frontend/src/components/reconciliation/delivery-badge.tsx
  - frontend/src/components/reconciliation/delivery-list.tsx
  - frontend/src/components/reconciliation/evidence-link.tsx
  - frontend/src/components/reconciliation/hit-rate-card.tsx
  - frontend/src/components/reconciliation/unpaid-list.tsx
  - frontend/src/components/reconciliation/unregistered-list.tsx
  - frontend/src/components/shell/app-shell.tsx
  - frontend/src/components/snapshots/alert-row.tsx
  - frontend/src/lib/api-types.ts
  - frontend/src/lib/headline-queries.ts
  - frontend/src/lib/reconciliation-errors.ts
  - frontend/src/lib/reconciliation-queries.ts
  - frontend/src/lib/vendor-labels.ts
  - compose.yaml
  - .env.example
  - package.json
  - pyproject.toml
findings:
  critical: 5
  warning: 16
  info: 8
  total: 29
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-08-12
**Depth:** standard
**Files Reviewed:** 36 (bot-service, frontend recon/headline yuzasi, infra)
**Status:** issues_found

## Summary

Ko'rib chiqilgan yuza: `bot-service` (uchinchi servis, sotuvchi boti), nomuvofiqlik hisoboti
ekrani, hukm dialogi, yetkazilganlik bloki va infra (compose / npm skriptlari). Kod bazasi
juda yaxshi hujjatlashtirilgan va ko'p qaror izohda asoslangan — lekin aynan shu izohlar bir
necha joyda **shiplangan kod bilan mos kelmaydi**, va o'sha nomuvofiqliklar eng qimmat
nuqsonlarni bergan.

Uch sinf muammo topildi:

1. **Yozuv yuzasi jimgina yiqiladi.** Hukm dialogi (fazadagi YAGONA yozuv amali) uch xil yo'l
   bilan foydalanuvchini aldaydi: mas'ul tanlovi serverga umuman yetib bormaydi (CR-01), har
   qanday xato matnsiz o'tadi (CR-02), va ikkinchi qaror jim tashlab yuboriladi (CR-04).
   Uchalasida ham ekranda «hech nima bo'lmagandek» ko'rinadi.
2. **Ro'yxatlar jimgina qisqaradi.** Navbat va yetkazilganlik jadvallari serverdan kelgan
   `next_cursor` ni HECH QACHON iste'mol qilmaydi, sanoqlar esa kun bo'yicha to'liq keladi —
   ya'ni direktor «120» sonini va 50 qatorni bir ekranda ko'radi (CR-05).
3. **Bot `npm run up` bilan umuman ko'tarilmaydi** (CR-03) — `compose.yaml` ning o'z izohi
   teskarisini da'vo qiladi.

Uchala locale kaliti va ICU platsholderlari **to'liq juft** (1207 kalit, 0 yetishmovchilik,
0 platsholder farqi); gettext kataloglarining msgid to'plami ham teng va platsholderlar
uchala tilda mos. Ya'ni «bir tilda bor, boshqasida yo'q» sinfidagi defekt topilmadi —
buning o'rniga **hech bir tilda erishib bo'lmaydigan** matn topildi (WR-16).

Sirlar va shaxsiy ma'lumot bo'yicha: `core_client.py` va `observability.py` intizomi mustahkam
(token faqat sarlavhada, istisno matni hech qayerga yozilmaydi, Telegram tokeni URL'da
maskalanadi). Ikki qoldiq xavf: test konteyneriga prod tokenlari oqib o'tishi (WR-10) va
xodim telefon raqamining audit iziga yorliq sifatida chizilishi (WR-09).

## Critical Issues

### CR-01: Mas'ul tanlagichi direktorning tanlovini jimgina tashlab yuboradi va server case'ni AKTORGA biriktiradi

**File:** `frontend/src/components/reconciliation/case-detail-dialog.tsx:326-328, 357, 393-408`
**Bog'liq:** `frontend/src/lib/reconciliation-queries.ts:629-633`

**Issue:** Dialogda to'liq ishlaydigandek ko'rinadigan «Mas'ul» `<Select>` bor, `useCaseUpdate`
esa uni `assignee_user_id` bo'lib tanaga qo'yadi. Lekin shiplangan marshrut bu maydonni
**umuman o'qimaydi**:

```python
# services/core-api/app/api/v1/reconciliation.py:657-666
await reconciliation_repo.transition(
    session, market_id=market_id, case_id=case_id,
    to_status=payload.status.value,
    actor_user_id=principal.user_id,
    note=payload.resolution_note,   # ← `payload.assignee_user_id` YO'Q
)
```

`reconciliation_repo.transition()` (941-949) da bunday parametr yo'q, va SQL (874-882):

```sql
assignee_user_id = COALESCE(:actor_user_id, assignee_user_id)
```

Ya'ni mas'ul — **o'tishni qilgan odam**, tanlangan odam emas. Uch oqibat:

1. tanlangan xodim HECH QACHON biriktirilmaydi;
2. har qanday holat o'zgarishi mas'ulni **jimgina o'g'irlaydi** — ilgari Aliyevga biriktirilgan
   case direktor «Ko'rilmoqda» qilishi bilan direktorniki bo'lib qoladi;
3. `<option value="">Biriktirilmagan</option>` (400-401) mavjud bo'lmagan amalni va'da qiladi —
   `COALESCE` `NULL` ni **e'tiborsiz** qoldiradi, ya'ni biriktirishni bekor qilib bo'lmaydi.

Fayl izohining o'zi (108-112) teskarisini yozadi: «Mas'ul holat o'zgarishi BILAN BIRGA
yoziladi». Bu da'vo shiplangan serverga qarshi **noto'g'ri**.

`invalidateQueries` dan keyin ro'yxat aktorni mas'ul qilib chizadi — ya'ni direktor o'z
tanlovi bekor qilinganini ko'radi, lekin sababini bilmaydi.

**Fix:** Klient tomonda — boshqaruvni va tana maydonini shiplangan kontraktga moslashtirish
(server tuzatilgunicha):

```tsx
// case-detail-dialog.tsx — `<Field id="case-assignee">` blokini OLIB TASHLASH,
// `assignee` state'ini ham. O'rniga joriy mas'ulni FAQAT O'QISH sifatida ko'rsatish:
<dl className="flex gap-2 text-sm">
  <dt className="text-text-muted">{t("recon.assigneeLabel")}</dt>
  <dd className="m-0">
    {detail.assignee_user_id === null
      ? t("recon.assigneeNone")
      : <ActorLabel userId={detail.assignee_user_id} />}
  </dd>
</dl>
```

```ts
// reconciliation-queries.ts:629-633 — jo'natilmaydigan maydon olib tashlanadi
body: { status: input.status, resolution_note: input.resolutionNote },
```

To'g'ri (uzoqroq) tuzatish — serverda alohida biriktirish amali; u holda bu boshqaruv qaytadi.

---

### CR-02: Hukm saqlashdagi HAR QANDAY xato matnsiz o'tadi — muvaffaqiyat bilan bir xil ko'rinadi

**File:** `frontend/src/components/reconciliation/case-detail-dialog.tsx:342-344, 426-434`

**Issue:**

```tsx
const errorView = reconErrorView(
  update.error instanceof ApiError ? update.error.detail : null,
);
...
{errorView === null ? null : (<p role="alert">…</p>)}
```

`reconErrorView()` faqat besh kodni biladi (`not_found`, `status_unchanged`,
`case_status_conflict`, `case_resolution_required`, `forbidden`). Qolgan HAMMA holat `null`
qaytaradi va **hech qanday element chizilmaydi**:

* `NetworkError` (server yiqilgan / aloqa uzilgan) — `ApiError` emas → `null`;
* `422` — FastAPI `detail` ni MASSIV qilib beradi, `api-client.ts:121-124` dagi `detailOf()`
  bo'sh satr qaytaradi → `null`;
* `429`, `500`, `503` — kod xaritada yo'q → `null`;
* `market_not_selected` (`reconciliation.py:212`, 403) — xaritada yo'q → `null`.

`reconciliation-errors.ts:106-108` ochiq yozadi: «Xaritada YO'Q kod `null` qaytaradi va
chaqiruvchi `errors.generic` ga tushadi» — **yagona chaqiruvchi bu shartnomani bajarmaydi**.

Oqibati eng yomon sinfdan: `onError` da `submittedRef` bo'shatiladi, tugma yana faol
ko'rinadi, `<Select>` da direktor tanlagan holat turibdi, dialog ochiq qoladi — ya'ni
**yiqilgan hukm muvaffaqiyatli hukmdan farq qilmaydi**. Nizo hujjati (D-02) yozilmagan holda
direktor uni yozilgan deb hisoblaydi.

**Fix:**

```tsx
{update.isError ? (
  errorView === null ? (
    <p className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text" role="alert">
      {t("errors.generic")}
    </p>
  ) : (
    <p className="flex flex-col gap-1 rounded-sm bg-surface-muted px-3 py-2 text-sm" role="alert">
      <span>{t(errorView.causeKey)}</span>
      <span className="text-text-muted">{t(errorView.fixKey)}</span>
    </p>
  )
) : null}
```

---

### CR-03: `npm run up` `bot-service` ni ko'tarmaydi — faza mahsuloti hujjatlashtirilgan buyruq bilan umuman ishlamaydi

**File:** `package.json:7`
**Bog'liq:** `compose.yaml:601-605`

**Issue:**

```json
"up": "docker compose up -d db cache storage core-api worker scheduler cv-service go2rtc --wait"
```

Ro'yxat ANIQ va unda `bot-service` YO'Q. `compose.yaml:601-605` esa buning teskarisini da'vo
qiladi:

> ⚠ PROFILSIZ — `worker`/`scheduler`/`cv-service` bilan bir xil sabab: bu ISHLAB CHIQARISH
> komponenti va **`npm run up` uni ham ko'taradi**. Profil ortiga yashirilsa sotuvchi botga
> yozardi va javob HECH QACHON kelmasdi — hech qanday xato bermasdan.

Profilsizlik bu nosozlikni to'smaydi, chunki `up` skripti servislarni nomma-nom sanaydi.
Nosozlik shakli aynan izoh ogohlantirgan sinfdan: `docker compose ps` toza, jurnal bo'sh,
sotuvchilar javob olmaydi. Diff (`4d2303f..HEAD`) `package.json` da faqat `bot:test`/`bot:lint`
va `gate` o'zgarganini ko'rsatadi — `up` **tegilmagan**.

**Fix:**

```json
"up": "docker compose up -d db cache storage core-api worker scheduler cv-service bot-service go2rtc --wait"
```

⚠ `--wait` bilan birga: `bot-service` da `healthcheck` ATAYIN yo'q (compose:671-679), ya'ni
`--wait` uning uchun faqat «konteyner ishga tushdi» ni kutadi — bu kutilgan xulq.

---

### CR-04: Bitta ochiq dialogda IKKINCHI qaror jimgina tashlab yuboriladi

**File:** `frontend/src/components/reconciliation/case-detail-dialog.tsx:335, 346-370`

**Issue:** Qulf `detail.case_id` ni saqlaydi va u FAQAT `onError` da bo'shatiladi:

```tsx
const submittedRef = useRef<string | null>(null);
...
if (submittedRef.current === detail.case_id) return;   // ← jim `return`
submittedRef.current = detail.case_id;
update.mutate({...}, { onError: () => { submittedRef.current = null; } });
```

Muvaffaqiyatdan keyin dialog **yopilmaydi** (`case-list.tsx:184-189` — `openCaseId` faqat
`onOpenChange(false)` da tozalanadi) va `DecisionForm` unmount bo'lmaydi (`detail.isPending`
false, refetch paytida komponent tirik). Ya'ni real oqim:

1. direktor `new → in_review` qiladi → saqlanadi, qulf o'rnatiladi;
2. yechim matnini yozib `in_review → justified` qilmoqchi bo'ladi;
3. `unchanged` false, `noteRequired` qanoatlantirilgan → `blocked` **false**, tugma faol
   ko'rinadi va `aria-disabled` ham false;
4. bosadi — `submittedRef.current === detail.case_id` → **jim `return`**. So'rov ketmaydi,
   xato yo'q, spinner yo'q, hech nima o'zgarmaydi.

Izoh (360-364) qulfni «muvaffaqiyatda ikkinchi so'rov nol o'tish (409) bo'lardi» deb
asoslaydi — bu faqat holat O'ZGARMAGANDA rost. Holat o'zgargan bo'lsa nol o'tish EMAS va
so'rov qonuniy.

**Fix:** Qulfni yuborilgan QARORGA bog'lash (case'ga emas) — nol o'tish shoxini `unchanged`
allaqachon to'sib turibdi:

```tsx
const submittedRef = useRef<string | null>(null);
...
const ticket = `${detail.case_id}:${status}`;
if (submittedRef.current === ticket) return;
submittedRef.current = ticket;
update.mutate({...}, { onSettled: () => { submittedRef.current = null; } });
```

---

### CR-05: Navbat va yetkazilganlik jadvallari 50 qatorda jimgina qirqiladi — `next_cursor` hech qachon iste'mol qilinmaydi

**File:** `frontend/src/lib/reconciliation-queries.ts:82, 237, 366, 485-504, 557-576`
**Bog'liq:** `frontend/src/components/reconciliation/case-list.tsx:104, 154-182`,
`frontend/src/components/reconciliation/delivery-list.tsx:121, 194-220`

**Issue:** Ikkala sxema ham `next_cursor` ni PARSE qiladi, `CASE_PAGE_SIZE = 50` konstantasi
e'lon qilingan — lekin `next_cursor` ni o'qiydigan, `cursor` ni oshiradigan yoki «yana
yuklash» beradigan BIRORTA iste'molchi yo'q. Ikkala hook ham qat'iy `cursor = ""` bilan
chaqiriladi (`case-list.tsx:104`, `hit-rate-card.tsx:77`), `CASE_PAGE_SIZE` esa butun kod
bazasida **hech qayerda ishlatilmaydi** (o'lchandi: `grep` — faqat e'lon qatori).

Server chegaralari: `reconciliation.py:433,477` → `CASE_PAGE_SIZE = 50`;
`outbox_repo.py:883` → `DELIVERY_PAGE_SIZE = 50`.

Sanoqlar esa server kontraktiga ko'ra **sahifadan va filtrdan mustaqil** — ya'ni butun kun
bo'yicha:

> ⛔ TO'RTALA HISOBLAGICH HAM ⛔ FILTRDAN MUSTAQIL (kun bo'yicha)
> — `reconciliation.py:445-447`

Natijada 300–1000 rastali bozorda direktor ekranda «Yangi 120» yozuvini va 50 qatorli
jadvalni ko'radi, qolgan 70 tasi esa DOM'da UMUMAN yo'q va ularga yetadigan boshqaruv ham
yo'q. Bu fazaning eng yuqori ustuvorlikdagi yuzasida (Y-1) **jim ma'lumot yo'qotishi** va u
`case-list.tsx:63-71` ning o'z printsipiga («yo'qolgan sanoq ... jim xato») to'g'ridan-to'g'ri
zid.

**Fix (minimal — qirqilish KO'RINADIGAN bo'lsin):**

```tsx
// case-list.tsx — jadvaldan keyin
{cases.data?.next_cursor !== null && cases.data !== undefined ? (
  <p className="text-sm text-text-muted" role="status">
    {t("recon.casesTruncated", { shown: rows.length })}
  </p>
) : null}
```

**To'g'ri tuzatish:** `useInfiniteQuery` + `getNextPageParam: (last) => last.next_cursor`
(`market-queries.ts:682-691` naqshi) va `[Yana yuklash]` tugmasi. ⚠ Aniqlik ulushi
`caseListSchema` ning to'rt sanog'idan hisoblanadi va u sahifadan mustaqil — ya'ni
`hit-rate-card.tsx` birinchi sahifa kalitida qolaveradi.

## Warnings

### WR-01: Har qanday `404` «siz bog'lanmagansiz» ga aylanadi va sotuvchini kontakt tugmasiga qaytaradi

**File:** `services/bot-service/app/core_client.py:105-107, 162-164`
**Iste'molchilar:** `app/handlers/start.py:104-105`, `app/handlers/vendor.py:153-154, 189-190, 227-228`

**Issue:** `_failure()` STATUS bo'yicha shox tanlaydi:

```python
if status == _NOT_BOUND_STATUS:            # 404
    return NotBoundError(...)
```

Ya'ni `CORE_API_URL` noto'g'ri sozlangan, marshrut qayta nomlangan yoki oldida turgan proxy
404 bergan holatlarning HAMMASI `NotBoundError` bo'ladi. `start.py:97-98` esa aynan buni
taqiqlaydi:

> ⛔ NOSOZLIKDA KONTAKT TUGMASI KO'RSATILMAYDI: u «siz bog'lanmagansiz» degan YOLG'ON xulosa
> bo'lardi.

Bugungi kodda o'sha yolg'on xulosa **infratuzilma nosozligida chiqadi**, va bog'langan
sotuvchi «Avval raqamingizni ulashing» matnini oladi.

**Fix:** Serverning nomlangan holatiga tayanish (`bot.py:102` — `_NOT_BOUND = "not_bound"`):

```python
except httpx.HTTPStatusError as exc:
    detail = None
    if exc.response.status_code == _NOT_BOUND_STATUS:
        with contextlib.suppress(ValueError):
            body = exc.response.json()
            detail = body.get("detail") if isinstance(body, dict) else None
    raise _failure(operation, exc, exc.response.status_code, not_bound=detail == "not_bound") from exc
```

⛔ `detail` FAQAT tenglik uchun ishlatiladi va hech qayerga yozilmaydi — D-04 buzilmaydi.

---

### WR-02: FSM ma'lumoti buzilganda `on_more` ushlanmagan `ValueError` beradi

**File:** `services/bot-service/app/handlers/vendor.py:215, 220, 224`

**Issue:**

```python
pages: list[list[str]] = list(data.get(PAGES_KEY) or [])
...
market_id_raw, cursor = pages[0]        # ← ValueError, agar element 2 a'zoli bo'lmasa
page = await core.vendor_payments(..., market_id=UUID(market_id_raw), ...)  # ← ValueError
```

Ikkala qator ham `try` blokidan TASHQARIDA (`try` faqat 221-qatordan boshlanadi — `UUID()`
esa 224-qatorda, ya'ni ichida; lekin `unpack` tashqarida). FSM `db 1` da yashaydi va u
`--save "" --appendonly no` bilan ishlaydi, ya'ni sxema versiyasi o'zgarganda (masalan
`pending` elementiga uchinchi a'zo qo'shilsa) eski kalitlar qoladi. Istisno aiogram jurnaliga
tushadi, foydalanuvchi esa **hech qanday javob olmaydi**.

**Fix:**

```python
entry = pages[0]
if len(entry) != 2:
    await state.update_data({PAGES_KEY: []})
    await message.answer(_("bot.payments.noMore"), reply_markup=main_menu_keyboard())
    return
market_id_raw, cursor = entry
try:
    market_id = UUID(market_id_raw)
except ValueError:
    await state.update_data({PAGES_KEY: []})
    await message.answer(_("bot.payments.noMore"), reply_markup=main_menu_keyboard())
    return
```

---

### WR-03: To'lov sahifalarida BOZOR nomi yo'q, «Ko'proq» esa bozorlarni aylantiradi

**File:** `services/bot-service/app/handlers/vendor.py:178-200, 234-241`

**Issue:** `on_payments` har bozor uchun bitta sahifa oladi va ularni `"\n\n"` bilan
yopishtiradi — **qaysi blok qaysi bozorniki ekani hech qayerda yozilmagan**. `on_more` esa
navbatning birinchisini olib, oxiriga qaytadan qo'yadi (`rest.append(...)`), ya'ni bosishlar
A-sahifa2, B-sahifa2, A-sahifa3 … tartibida keladi va ularning HECH BIRIDA bozor
ko'rsatilmagan.

Bu `core_client.py:372-376` ning o'z asosiga zid:

> ⛔ `market_id` MAJBURIY VA BU 07-08 NING QARORI: … serverda «birinchisini tanlash»
> sotuvchiga BOSHQA bozorning tarixini ko'rsatardi.

Server tanlamasligi to'g'ri, lekin klient ikkalasini **ajratmasdan** ko'rsatadi — natija
o'sha: sotuvchi qaysi bozorning qatorini o'qiyotganini bilmaydi. `on_debt` (160-169) ham
bozorni emas, faqat rasta kodlarini yozadi.

**Fix:** Har blokka sarlavha qo'shish. Server `market_id` dan boshqa hech nima bermaydi
(D-05), shuning uchun yorliq rasta kodlaridan quriladi — u `on_debt` da allaqachon bor:

```python
chunks.append(
    _("bot.payments.marketHeader").format(
        stalls=", ".join(market.stall_codes) or _("bot.summary.noStalls")
    )
    + "\n"
    + _render_page(page)
)
```
va `on_more` uchun `pending` ga rasta kodlarini ham saqlash. ⚠ Yangi kalit UCHALA `.po` ga
qo'shiladi (D-31).

---

### WR-04: Botda zaxira handler yo'q — istalgan matn yozgan sotuvchi mutlaq sukunat oladi

**File:** `services/bot-service/app/handlers/__init__.py:23-35`

**Issue:** Ro'yxatda uchta router bor va ularning filtrlari: `CommandStart()`,
`Command("help")`, `F.contact`, `F.text.in_(...)` — uchta qat'iy tugma matni. **Boshqa hech
qanday xabar handlerga tushmaydi.** Sotuvchining eng tabiiy harakati (raqamini yozish, «qarzim
qancha?» deb so'rash) **hech qanday javob bermaydi**.

Bu `main.py:130-136` ning o'z asosiga zid:

> Botning butun qiymati «sotuvchi yozgan xabar javob oladi» degani.

⚠ D-24 buzilmaydi: taqiq QO'LDA TERILGAN RAQAMNI O'QISHGA tegishli, javob berishga emas.
`test_binding.py::test_typed_phone_number_is_not_handled` predikati manbada «phone» so'zini
sanaydi — quyidagi handler uni ishlatmaydi va darvoza yashil qoladi.

**Fix:** `vendor` routeridan KEYIN, oxirgi router sifatida:

```python
@router.message()
async def on_unknown(message: Message) -> None:
    """Tugmadan tashqari har qanday xabar — menyuni QAYTA ko'rsatadi."""
    await message.answer(_("bot.unknown"), reply_markup=main_menu_keyboard())
```
⚠ `bot.unknown` uchala `.po` ga qo'shiladi va matnda reyestrga a'zolik haqida hech nima
aytilmaydi (D-26a).

---

### WR-05: Aniqlik ulushi bloki so'rov YIQILGANDA o'lchangan faktni da'vo qiladi

**File:** `frontend/src/components/reconciliation/hit-rate-card.tsx:95-110`

**Issue:** Xato shoxida `recon.accuracyNone` chiziladi — matni «Hali hal qilingan
nomuvofiqlik yo'q». Bu **o'lchangan qiymat da'vosi**, holbuki haqiqat «o'lchov umuman
kelmadi». Aynan shu sinf fayl izohining 2-bandida taqiqlangan («`0 %` ... TESKARI XULOSANI
berardi — holbuki hech nima hali tekshirilmagan») va 05-14 ning «o'lchanmagan sonning
o'rniga NOL yozilmaydi» darsi ham shu.

Yumshatuvchi holat: qo'shni `CaseList` bloki `errors.loadFailedBody` ni `role="alert"` bilan
chizadi, ya'ni ekranda xato KO'RINADI — lekin bu blok baribir yolg'on gapiradi.

**Fix:** Xato shoxida alohida nomlangan sabab:

```tsx
<p className="text-sm text-text-muted">{t("errors.loadFailedBody")}</p>
```

---

### WR-06: `UnpaidList` klientda pul arifmetikasi qiladi — fayl o'z invariantini buzadi

**File:** `frontend/src/components/reconciliation/unpaid-list.tsx:180-183`

**Issue:**

```tsx
const outstanding = expected === null || paid === null ? null : expected - paid;
```

Fayl docstringi (54-56) ochiq yozadi:

> ⛔ ARIFMETIKA YO'Q: qarz serverdan KELGAN ikki sondan chiziladi va ularning birortasi ham
> klientda qayta hisoblanmaydi.

Ayirma `int` ustida ketadi, ya'ni pul turi buzilmaydi (D-07 saqlanadi) — lekin bu **ikkinchi
haqiqat manbai**: qarz serverda `billing_repo.vendor_outstanding()` va
`allocate_charge_credit()` qoidalari bilan hisoblanadi, bu yerda esa oddiy ayirma bilan.
Serverga tuzatish (`charge_adjustments`) yoki kredit taqsimoti qo'shilgan kunda ikki son
jimgina ajraladi va nizo hujjatida (D-02) ikki xil raqam qoladi.

**Fix:** Marshrutdan `outstanding_soum` ni so'rash (server uni allaqachon hisoblaydi) va
klientdagi ayirmani olib tashlash. Bugungi kontrakt bilan — hech bo'lmaganda izohni haqiqatga
moslashtirish va ayirmani `lib/` dagi bitta yordamchiga chiqarish, ustun ostiga esa qoidani
yozish.

---

### WR-07: `service_date` bir fazaning uch faylida uch xil chiziladi; bittasi vaqt-mintaqasiga mo'rt

**File:** `frontend/src/components/reconciliation/unregistered-list.tsx:165-169`,
`frontend/src/components/reconciliation/case-detail-dialog.tsx:225`,
`frontend/src/components/reconciliation/case-list.tsx:149`

**Issue:** Bir xil maydon uch xil o'qiladi:

| Joy | Shakl | Natija |
|---|---|---|
| `unregistered-list.tsx:166` | `new Date(\`${d}T00:00:00\`)` + `format.dateTime` | lokalizatsiya qilingan, lekin **mo'rt** |
| `case-detail-dialog.tsx:225` | `{detail.service_date}` xom | uchala tilda `2026-08-11` |
| `case-list.tsx:149` va boshqalar | `{ date: day }` xom | uchala tilda ISO |

Birinchisining mo'rtligi mexanik: `"2026-08-11T00:00:00"` (ofsetsiz) **brauzerning MAHALLIY
mintaqasida** parse qilinadi, keyin `Asia/Tashkent` da formatlanadi. UTC+5 dan sharqdagi
mijoz (UTC+6 Bishkek, UTC+7, UTC+8) uchun natija **bir kun oldin** chiqadi. Bundan tashqari
SSR (`TZ=Asia/Tashkent` konteynerda) va CSR (brauzer mintaqasi) boshqa qiymat beradi — ya'ni
React **gidratatsiya nomuvofiqligi**.

Karmana pilotida hamma UTC+5 da, shuning uchun bugun ko'rinmaydi — lekin bu «tasodifan
to'g'ri» toifadagi kod va `billing/day-picker.tsx:92-97` allaqachon to'g'ri naqshni
(`useTimeZone()` + `businessDayIn`) ko'rsatadi.

**Fix:** Sana-faqat qiymat uchun bitta sof yordamchi va uchala joyda o'sha:

```ts
// lib/format-day.ts
export function isoDayToDate(day: string): Date {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d, 12));  // ⛔ 12:00 UTC — har qanday ofsetda AYNI kun
}
```
va `case-detail-dialog.tsx:225` da ham `format.dateTime(isoDayToDate(detail.service_date), { dateStyle: "medium" })`.

---

### WR-08: To'rtta `<dl>` sanoq bloki `role="status"` bilan — semantik yo'qoladi va sahifada to'rtta jonli hudud paydo bo'ladi

**File:** `frontend/src/components/reconciliation/case-list.tsx:133`,
`delivery-list.tsx:173`, `unpaid-list.tsx:106`, `unregistered-list.tsx:102`

**Issue:** `role="status"` `<dl>` ning implicit rolini (`list`) **almashtiradi**, ya'ni
`<dt>`/`<dd>` juftligi skrinriderda atama–qiymat bog'lanishini yo'qotadi: «Yangi 3
Ko'rilmoqda 2» degan bo'lak matn oqimiga aylanadi.

Bundan tashqari to'rtta blok bir sahifada to'rtta mustaqil `aria-live` hududi ochadi va
ularning uchtasida (`case-list`, `unpaid-list`, `unregistered-list`) foydalanuvchi
boshlaydigan yangilash **umuman yo'q** — ya'ni jonli hudud faqat sahifa yuklanganda, hech kim
kutmagan paytda, e'lon qiladi. Bu ustiga `role="status"` li yuklanish platsholderlari bilan
qo'shiladi (`aria-busy` + `role="status"`, har blokda) → bir yuklashda ~8 ta e'lon.

`delivery-list.tsx:170-171` izohi jonli hududni `[Yangilash]` bilan asoslaydi — o'sha asos
faqat SHU blokda amal qiladi.

**Fix:**

```tsx
{/* case-list / unpaid-list / unregistered-list — jonli hudud OLIB TASHLANADI */}
<dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">

{/* delivery-list — semantika saqlanadi, jonli hudud O'RAMDA */}
<div aria-live="polite">
  <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">…</dl>
</div>
```

---

### WR-09: Mas'ul/aktor yorliqlari tenant-doiralanmagan kesh kaliti orqali o'qiladi va telefon raqamiga tushadi

**File:** `frontend/src/lib/vendor-labels.ts:120, 130-135, 138-142`
**Bog'liq:** `frontend/src/lib/queries.ts:37, 53-59`

**Issue (a) — doiralash:** `useAssigneeLabels` `useUsersQuery()` ga boradi, u esa
`USERS_QUERY_KEY = ["users"]` — ya'ni **`marketId` siz** global kalit. Kod bazasining o'z
konvensiyasi (`domainKey(marketId, …)`, `market-queries.ts:116-117`,
`tenant-cache.test.tsx` bilan qulflangan) chetlab o'tilgan. Ikki oqibat:

1. `domainKey(marketId)` prefiksi bo'yicha tozalash bu kalitga **YETIB BORMAYDI** —
   `reconciliation-queries.ts:641-643` ning tozalash siyosati unga ta'sir qilmaydi;
2. bozor almashtirilganda oldingi bozorning xodimlar ro'yxati keshda qoladi va audit izidagi
   aktor **boshqa bozorning** xodimi nomi bilan yorliqlanishi mumkin.

`useVendorLabels` esa to'g'ri (`vendorsKey(marketId, …)`) — ya'ni bir modulda ikki xil
qoida.

**Issue (b) — shaxsiy ma'lumot:** yorliq zaxirasi **telefon raqami**:

```ts
[user.id, user.full_name ?? user.phone]
...
.map((user) => ({ id: user.id, label: user.full_name ?? user.phone }))
```

Ismi yo'q xodim uchun audit izida (`case-detail-dialog.tsx:298-309`) va mas'ul
tanlagichida telefon raqami chiziladi. `user_view` huquqi ostida bo'lsa-da, bu
`assignee_user_id.slice(0, 8)` bilan solishtirganda ma'lumot yuzasining kengayishi va u
`ActorLabel` ning o'z izohida ko'zda tutilmagan.

**Fix:**

```ts
// queries.ts — kalitni doiralash (barcha iste'molchilar bilan birga)
export const usersKey = (marketId: string) => domainKey(marketId, "users");

// vendor-labels.ts — telefon zaxirasi O'RNIGA identifikatorning qisqa shakli
const label = (user: UserListItem) => user.full_name ?? user.id.slice(0, 8);
```

---

### WR-10: `bot-tests` konteyneri PROD Telegram va servis tokenlarini meros oladi

**File:** `compose.yaml:720-721`

**Issue:**

```yaml
TELEGRAM_BOT_TOKEN: "${TELEGRAM_BOT_TOKEN:-123456:TEST-TOKEN-NOT-REAL}"
BOT_SERVICE_TOKEN: "${BOT_SERVICE_TOKEN:-test-service-token}"
```

`:-` **standart**, majburlash emas. `bot-service` bloki (630, 633) bu ikki kalitni
standartsiz talab qiladi, ya'ni ishlaydigan har qanday `.env` da ikkalasi ham to'ldirilgan
bo'lishi SHART — natijada `npm run bot:test` test konteynerini **haqiqiy prod bot tokeni** va
**haqiqiy servis tokeni** bilan ko'taradi. `app/main.py:51` esa `Bot(token=...)` ni MODUL
DARAJASIDA quradi, ya'ni token har test yig'ilishida jarayonga yuklanadi.

compose izohi (719) buni ochiq inkor qiladi:

> ⚠ QIYMAT SIR EMAS, USKUNA: u Telegram'da mavjud emas va tarmoqqa umuman chiqmaydi.

Bu da'vo faqat `.env` BO'SH bo'lgan mashinada rost. Xavf: bitta tasodifiy tarmoq chaqiruvi
(yoki kelajakdagi integratsiya testi) prod bot sessiyasiga tegadi — va DQ-1 bo'yicha bu prod
botni **jim qoldiradi**.

**Fix:** Test konteynerida indirection'ni butunlay olib tashlash:

```yaml
# ⛔ `${...:-}` YO'Q: uskuna qiymati MUHITDAN kelmaydi.
TELEGRAM_BOT_TOKEN: "123456:TEST-TOKEN-NOT-REAL"
BOT_SERVICE_TOKEN: "test-service-token"
```

---

### WR-11: Noma'lum `severity` jimgina ENG PAST darajaga tushiriladi

**File:** `frontend/src/components/snapshots/alert-row.tsx:157-159`

**Issue:**

```tsx
const severity: SeverityView =
  SEVERITY_VIEW[alert.severity as keyof typeof SEVERITY_VIEW] ?? SEVERITY_VIEW.info;
```

Backend to'rtinchi daraja qo'shsa (masalan `emergency`), u ekranda «Ma'lumot» ko'k nishoni
bilan chiziladi. Bu faylning o'z qoidasiga (78-80: «XOM KALIT EKRANGA HECH QACHON CHIQMAYDI …
noma'lum kalit `errors.generic` ga tushadi») nomuvofiq: u yerda noma'lum qiymat NOMLANGAN
zaxira oladi, bu yerda esa **eng zararsiz** qiymatga tushadi.

**Fix:** `warning` tonига tushirish (eng kam zarar), yoki `snapshots.severity.unknown`
zaxira yorlig'i qo'shish:

```tsx
const known = SEVERITY_VIEW[alert.severity as keyof typeof SEVERITY_VIEW];
const severity: SeverityView = known ?? {
  labelKey: "snapshots.severity.unknown",
  tone: "warning",
};
```

---

### WR-12: `alertDurationParts` `NaN` ni ekranga chiqara oladi

**File:** `frontend/src/components/snapshots/alert-row.tsx:134-142`

**Issue:**

```ts
const ms = Math.max(0, Date.parse(toIso) - Date.parse(fromIso));
const minutes = Math.max(1, Math.round(ms / 60_000));
if (minutes < 120) return { unit: "minute", value: minutes };
return { unit: "hour", value: Math.round(minutes / 60) };
```

`Date.parse` yaroqsiz satrda `NaN` beradi. `Math.max(0, NaN) === NaN` va
`Math.max(1, NaN) === NaN` (JS semantikasi), `NaN < 120` esa `false` → funksiya
`{ unit: "hour", value: NaN }` qaytaradi va `format.number(NaN, {style:"unit"})` ekranga
**«NaN soat»** chizadi. To'qilgan qiymat sinfining aynan o'zi (05-14).

**Fix:**

```ts
const from = Date.parse(fromIso);
const to = Date.parse(toIso);
if (!Number.isFinite(from) || !Number.isFinite(to)) {
  return { unit: "minute", value: 1 };
}
```
(yoki `null` qaytarib, davomiylik qatorini umuman chizmaslik — chaqiruvchida `duration === null`
shoxi allaqachon bor, `alert-row.tsx:277`).

---

### WR-13: Noma'lum `subject_kind` qatorlari IKKALA blokdan ham jimgina yo'qoladi

**File:** `frontend/src/components/reconciliation/unpaid-list.tsx:69-71`,
`frontend/src/components/reconciliation/unregistered-list.tsx:65-67`

**Issue:** Ikkala blok ham `filter(row => row.subject_kind === SUBJECT)` qiladi. Server
uchinchi sinf qo'shsa (sxema `z.string()`, ATAYIN qulflanmagan — `reconciliation-queries.ts:87-97`),
o'sha qatorlar **hech bir blokda chizilmaydi**, ammo `unpaid_count`/`unregistered_count`
serverda hisoblanadi va sanoq bilan ro'yxat ajraladi.

Bu `case-status-badge.tsx:38-43` va `delivery-badge.tsx:66-70` da o'rnatilgan qoidaga zid
(«NOMA'LUM QIYMAT YASHIRILMAYDI, ZAXIRA YORLIQ OLADI»), va aynan shu ehtiyoj uchun yozilgan
`isSubjectKind()` (`reconciliation-queries.ts:104-106`) **hech qayerda chaqirilmaydi**
(o'lchandi: butun `frontend/src` bo'yicha 0 iste'molchi).

**Fix:** Uchinchi shox — noma'lum sinf qatorlari alohida ko'rinsin (yoki hech bo'lmaganda
sanoq bilan ro'yxat farqi e'lon qilinsin):

```tsx
const known = rows.filter((r) => isSubjectKind(r.subject_kind));
const orphan = (report.data?.rows ?? []).length - known.length;
```

---

### WR-14: `compose.yaml` dagi `NEXT_PUBLIC_API_BASE_URL` ta'sirsiz

**File:** `compose.yaml:792-794`
**Bog'liq:** `frontend/Dockerfile` (`ARG` yo'q), `frontend/src/lib/api-client.ts:31`

**Issue:** `NEXT_PUBLIC_*` Next.js da **build paytida** bandlga inline qilinadi.
`frontend/Dockerfile` da bu qiymat uchun `ARG` ham, build-time `ENV` ham yo'q, ya'ni
compose'dagi runtime `environment` qiymati **hech narsaga ta'sir qilmaydi**. Bugun nosozlik
ko'rinmaydi, chunki `api-client.ts:31` ning zaxirasi (`"/api/v1"`) compose standarti bilan
mos — lekin operator qiymatni o'zgartirsa u JIMGINA e'tiborsiz qoladi.

⚠ Bu 7-fazadan oldin mavjud (compose'ning `frontend` bloki bu fazada tegilmagan), lekin fayl
ko'rib chiqish doirasida.

**Fix:** `frontend/Dockerfile` ga `ARG NEXT_PUBLIC_API_BASE_URL` + `ENV` qo'shish va
compose'da `build.args` orqali berish; yoki compose'dagi `environment` qatorini olib tashlab,
izohda «bu qiymat build paytida qadaladi» deb yozish.

---

### WR-15: Yechim matnini TOZALASH mumkin emas, lekin forma buni va'da qiladi

**File:** `frontend/src/components/reconciliation/case-detail-dialog.tsx:356`

**Issue:** `resolutionNote: note.trim() === "" ? null : note.trim()` — bo'shatilgan
`<textarea>` `null` yuboradi. Server esa:

```sql
resolution_note = COALESCE(:note, resolution_note)
```
(`reconciliation_repo.py:878`) — ya'ni `null` **eski matnni saqlab qoladi**. Foydalanuvchi
matnni o'chirib saqlaydi, forma bo'sh turadi, bazada esa eski matn qoladi. Keyingi ochilishda
(`useState(detail.resolution_note ?? "")`) eski matn qaytib chiqadi — bu «o'zgarishim
yo'qoldi» taassuroti beradi.

**Fix:** Bo'sh matnni `null` emas, bo'sh SATR bilan yuborish (server uni yozadi), yoki
tozalash imkoniyati yo'qligini UI'da ochiq aytish (hint matni). Birinchisi afzal:

```ts
resolutionNote: note.trim(),
```
⚠ Server sxemasi `str | None` — bo'sh satr `COALESCE` da `NULL` emas, ya'ni yoziladi.

---

### WR-16: `case_resolution_required` matni HECH BIR tilda erishib bo'lmaydi

**File:** `frontend/src/lib/reconciliation-errors.ts:48-53, 80, 113`,
`frontend/messages/{uz-Latn,uz-Cyrl,ru}.json` (`recon.errorCause.case_resolution_required`,
`recon.errorFix.case_resolution_required`)

**Issue:** Kod uchala locale'da yozilgan, lekin unga olib boradigan yo'l yo'q:

1. server bu kodni HECH QACHON qaytarmaydi — `reconciliation.py` da faqat `not_found`,
   `status_unchanged`, `day_in_future`, `range_invalid`, `range_too_wide`,
   `market_not_selected` va `forbidden` literallari bor;
2. klientdagi yagona tekshiruv `blocked` ichida (`case-detail-dialog.tsx:337-340`) va u
   **hech qanday matn chizmaydi** — `onSave` jim `return` qiladi (CR-02 bilan bir sinf).

Natija: yakuniy holat uchun yechim matni MAJBURIY degan qoida foydalanuvchiga **hech qachon
aytilmaydi**. U «Asosli» ni tanlaydi, `[Holatni saqlash]` ni bosadi va hech nima bo'lmaydi.

**Fix:** `blocked` sababini KO'RSATISH (CR-02 ning tuzatishi bilan birga):

```tsx
{noteRequired && note.trim() === "" ? (
  <p className="text-sm" id="case-blocked" role="status">
    {t("recon.errorCause.case_resolution_required")}{" "}
    <span className="text-text-muted">{t("recon.errorFix.case_resolution_required")}</span>
  </p>
) : null}
<Button aria-describedby={blocked ? "case-blocked" : undefined} aria-disabled={blocked} …>
```

## Info

### IN-01: `Dockerfile` da `CMD`/`ENTRYPOINT` yo'q, lekin izoh mount'siz `docker run` ni va'da qiladi

**File:** `services/bot-service/Dockerfile:69-70, 101`
**Issue:** Izoh «mount'siz `docker run` ham ishlasin» deydi, lekin ikkala bosqichda ham
standart buyruq yo'q — konteyner `command` siz ishga tushmaydi.
**Fix:** `runtime` bosqichiga `CMD ["python", "-m", "app.main"]`, `dev` ga `CMD ["pytest", "-q"]`.

---

### IN-02: Keraksiz tur assertsiyalari `!== undefined` qo'riqchisi ichida

**File:** `frontend/src/components/reconciliation/case-list.tsx:140`,
`frontend/src/components/reconciliation/delivery-list.tsx:180`
**Issue:** `STATUS_COUNT[status](cases.data as CaseListResponse)` — `cases.data` allaqachon
toraytirilgan. `as` `strict` rejimda tur xatosini yashirishi mumkin.
**Fix:** Assertsiyalarni olib tashlash.

---

### IN-03: Eskirgan izoh — `ALERT_META` reyestri 15 a'zoli, izoh «o'n bitta» deydi

**File:** `frontend/src/components/snapshots/alert-row.tsx:96`
**Issue:** Bu fazada beshta yangi kalit qo'shildi (jami 15), izoh esa oldingi sonda qoldi.
**Fix:** «o'n beshta yozuv».

---

### IN-04: `delivery-list.tsx` `disabled` ishlatadi, `case-detail-dialog.tsx` esa uni taqiqlaydi

**File:** `frontend/src/components/reconciliation/delivery-list.tsx:141` vs
`frontend/src/components/reconciliation/case-detail-dialog.tsx:441-447`
**Issue:** Bir fazada bir xil savolga ikki javob. `disabled` yangilanish paytida fokusni
yo'qotadi — klaviatura foydalanuvchisi tugmadan «tushib qoladi».
**Fix:** `aria-disabled={deliveries.isFetching}` + `onClick` ichida erta `return`.

---

### IN-05: Nomuvofiqlik bloki `headline` namespace'idan pul birligini o'qiydi

**File:** `frontend/src/components/reconciliation/unpaid-list.tsx:117`
**Issue:** `t("headline.amountUnit")` — recon yuzasi bosh ekran namespace'iga bog'lanadi.
**Fix:** `common.amountUnit` (yoki `recon.amountUnit`) kalitini uchala locale'ga qo'shib,
`headline` dan mustaqil qilish.

---

### IN-06: `app-shell.tsx` da bitta nav yozuvi bir qatorda, qolgan 15 tasi ko'p qatorda

**File:** `frontend/src/components/shell/app-shell.tsx:339`
**Issue:** `{ href: "/users", labelKey: "users", … }` — formatlash izchil emas (ehtimol
`prettier` diapazondan chetda qolgan).
**Fix:** Boshqa yozuvlar bilan bir shaklga keltirish.

---

### IN-07: `_main()` ning `finally` bloki faqat `CoreClient` ni yopadi

**File:** `services/bot-service/app/main.py:178-185`
**Issue:** `RedisStorage` va `Bot` sessiyasi aiogram'ning ichki tozalashiga qoldirilgan.
Odatda `start_polling` ularni yopadi, lekin `TelegramConflictError` yo'lida bu kafolatlanmagan.
**Fix:** `finally` ga `await storage.close()` va `await bot.session.close()` qo'shish
(idempotent).

---

### IN-08: Recon bloklari `marketId === null` ni `HeadlineCard` kabi qo'riqlamaydi

**File:** `frontend/src/lib/reconciliation-queries.ts:474, 501, 526, 572`
**Issue:** `enabled: marketId !== null && …` — TanStack v5 da o'chirilgan so'rov `isPending`
holatida qoladi, ya'ni to'rt blok ham **cheksiz skelet** ko'rsatadi. Bugun erishib
bo'lmaydi (`report_view` egalarida `marketId` bor), lekin `HeadlineCard:98` bu holatni ochiq
qo'riqlaydi — recon esa yo'q.
**Fix:** Bloklarda `marketId === null` shoxini nomlash yoki sahifada bir marta tekshirish.

---

_Reviewed: 2026-08-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
