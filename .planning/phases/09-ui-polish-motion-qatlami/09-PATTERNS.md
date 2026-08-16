# Phase 9: UI-polish — motion qatlami — Naqsh xaritasi

**Xaritalandi:** 2026-08-17
**Tahlil qilingan fayllar:** 34 (11 yangi, 23 o'zgaruvchi)
**Analog topilgan:** 30 / 34 (4 tasi "Analog topilmadi" bo'limida — sabab bilan)

**Manba:** `.planning/phases/09-ui-polish-motion-qatlami/09-RESEARCH.md` (Tavsiya etilgan fayl tuzilishi, Wave tartibi, Kod namunalari 1-6) + `09-UI-SPEC.md` (§3.3, §3.4, §4-16 — fayl-darajasidagi shartnoma).

---

## Fayl klassifikatsiyasi

| Yangi/O'zgaruvchi fayl | Rol | Data-flow | Eng yaqin analog | Moslik |
|---|---|---|---|---|
| `frontend/src/lib/motion.ts` | utility | event-driven (browser guard) | `src/components/stalls/stall-map.tsx:46,56` | **exact** |
| `frontend/src/lib/theme.ts` | utility+hook | event-driven (DOM external store) | `src/components/stalls/stall-map.tsx:40-69` (`useIsDesktop`) | role-match |
| `frontend/src/lib/use-count-up.ts` | hook | transform (rAF animation) | `src/lib/wilson.ts` / `src/lib/zone-geometry.ts` (lib/ sof-funksiya+tor-hook naqshi) | partial |
| `frontend/src/components/shell/theme-toggle.tsx` | component | request-response (tugma guruh + saqlash) | `src/components/shell/locale-switcher.tsx` | **exact** |
| `frontend/src/components/collect/success-choreography.tsx` | utility (imperativ DOM) | event-driven (FLIP) | Yo'q (yangi); modul-docstring naqshi: `src/lib/zone-geometry.ts`; ulanish naqshi: `collect-session.tsx:265-295` | partial |
| `frontend/src/components/collect/success-choreography.test.tsx` | test | component | `src/components/collect/payment-bar.test.tsx:31-75` + `src/components/cameras/discovery-panel.test.tsx:245` (`useFakeTimers`) | role-match |
| `frontend/src/components/dashboard/revenue-card.tsx` | component | request-response (data card + SVG) | `src/components/dashboard/market-status-card.tsx` + `src/lib/report-queries.ts::useRevenueReport` + `src/components/camera-zones/zone-canvas.tsx` (sof SVG) | role-match |
| `frontend/src/components/dashboard/occupancy-donut.tsx` | component | request-response (data card + SVG) | xuddi yuqoridagi + `src/lib/occupancy-queries.ts::useOccupancyDay` | role-match |
| `frontend/scripts/motion-tokens.test.mjs` | test | batch (CSS/matn parse darvozasi) | `frontend/scripts/collect-surface.test.mjs` | **exact** |
| `frontend/scripts/theme-tokens.test.mjs` | test | batch | `frontend/scripts/collect-surface.test.mjs` | **exact** |
| `frontend/scripts/contrast.test.mjs` | test | batch (parse+hisob+solishtirish) | `frontend/scripts/collect-surface.test.mjs` + `src/lib/wilson.ts` (sof matematika uslubi) | role-match |
| `frontend/scripts/typography.test.mjs` | test | batch | `frontend/scripts/collect-surface.test.mjs` | **exact** |
| `frontend/src/app/globals.css` | config | CRUD (token qo'shish) | O'ZI (mavjud `@theme`/`@layer` tuzilishi) | self |
| `frontend/src/app/[locale]/layout.tsx` | provider/layout | request-response | O'ZI + Next.js rasmiy hujjati (`09-RESEARCH` Kod namunalari 6) | self+cited |
| `frontend/src/components/shell/app-shell.tsx` | component | request-response | O'ZI, qo'shish nuqtasi: `app-shell.tsx:480` | self |
| `frontend/src/components/collect/collect-session.tsx` | component (state machine) | event-driven | O'ZI, `onWritten` §265-295 | self |
| `frontend/src/components/collect/payment-bar.tsx` | component | request-response | O'ZI, `Loader2` §293 | self |
| `frontend/src/components/collect/pending-card.tsx` | component | request-response | O'ZI, skeleton §183, summa §273 | self |
| `frontend/src/components/collect/payment-row.tsx` | component | CRUD (list item) | O'ZI, shartli `cn()` naqshi §148-155 | self |
| `frontend/src/components/headline/headline-card.tsx` | component | request-response | O'ZI, skeleton §110, summa §138-150 | self |
| `frontend/src/components/ui/button.tsx` | ui primitive | CRUD | O'ZI §14 + `src/components/stalls/stall-cell.tsx:127` (`active:scale`) | self+cited |
| `frontend/src/components/ui/card.tsx` | ui primitive | CRUD | O'ZI (21 qator) | self |
| `frontend/src/components/ui/dialog.tsx` | ui primitive | CRUD | O'ZI (Radix `data-[state]` allaqachon mavjud atribut) | self |
| `frontend/src/components/ui/skeleton.tsx` | ui primitive | CRUD | O'ZI §26-37 | self |
| `frontend/src/components/ui/field.tsx` | ui primitive | CRUD | O'ZI §65-69 (xato bloki) — ⚠ ziddiyat, pastga qarang | self (ehtiyot bilan) |
| `frontend/src/app/[locale]/(app)/dashboard/page.tsx` | page | request-response | O'ZI §105-110 (`MarketStatusCard` huquq sharti) | **exact** |
| `frontend/src/app/[locale]/(app)/dashboard/page.test.tsx` | test | component | O'ZI (H6/H7 `describe` bloklari) | **exact** |
| `frontend/messages/uz-Latn.json` | i18n | CRUD | O'ZI, `dashboard` §1391-1399, `common` §2-12 | self |
| `frontend/messages/ru.json` | i18n | CRUD | `uz-Latn.json` bilan oyna | self |
| `frontend/src/app/[locale]/(app)/review/page.tsx` | page | request-response | O'ZI §217 (bitta token) | self |
| `frontend/src/components/blind-audit/blind-session.tsx` | component | event-driven | O'ZI §212 (bitta token) | self |
| `frontend/src/components/shell/locale-switcher.tsx` | component | request-response | O'ZI (faol indikator, §84-105) | self |
| `frontend/src/components/collect/shift-close-form.tsx` | component | request-response | `payment-bar.tsx:293` (`Loader2` naqshi) | **exact** |
| `frontend/src/components/collect/shift-open-card.tsx` | component | request-response | `payment-bar.tsx:293` | **exact** |
| `frontend/src/components/review/decision-bar.tsx` | component | request-response | `payment-bar.tsx:293` | **exact** |

⚠ `frontend/src/components/snapshots/capture-cell.tsx:273` — bu fayl **O'ZGARMAYDI**: u yagona joy bo'lib, `motion-reduce:animate-none` allaqachon bor [M-7]. Qolgan to'rttasi unga TENGLASHTIRILADI.

---

## Pattern Assignments

### `frontend/src/lib/motion.ts` (utility, event-driven)

**Analog:** `frontend/src/components/stalls/stall-map.tsx:46,56`

**Nimani ko'chirish kerak** — jsdom'da `window.matchMedia` yo'qligiga qarshi GUARD:

```ts
// src/components/stalls/stall-map.tsx:52-58
function readIsDesktop(): boolean {
  // jsdom (va eski muhitlar) `matchMedia` ni bermaydi — "desktop" deb
  // hisoblanadi, ya'ni hamma zona ochiq va hech qanday kontent
  // yashirilmaydi. Fail-OPEN: bu joylashuv, xavfsizlik chegarasi emas.
  if (typeof window.matchMedia !== "function") return true;
  return window.matchMedia(DESKTOP_QUERY).matches;
}
```

09-RESEARCH bu naqshni AYNAN shu joyga ishora qilib, `prefersReducedMotion()` uchun qayta yozadi (Kod namunalari 4):

```ts
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  if (typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
```

**Farq:** `stall-map.tsx` fail-**OPEN** (`true` — hamma narsa ko'rinsin), `motion.ts` fail-**SAFE** boshqa yo'nalishda (`false` — animatsiya YOQILGAN deb hisoblanadi, chunki mavjud bo'lmagan API "cheklov yo'q" degani). ⚠ Bu ataylab teskari standart — ko'r nusxa ko'chirilmasin, mantiq qayta o'ylansin.

**Nimani KO'CHIRMASLIK kerak:** `stall-map.tsx` bu funksiyani `useSyncExternalStore` ichida ishlatadi (reaktiv, `addEventListener("change", ...)` bilan). `motion.ts` dagi `prefersReducedMotion()` esa **bir martalik o'qish** — hodisa bo'lganda qayta chaqiriladi, obuna emas (RESEARCH: "klonga inline uslub" bir martalik tekshiruv sifatida ishlatiladi). `subscribeToDesktop`/`addEventListener` qismini KO'CHIRMANG.

---

### `frontend/src/lib/theme.ts` (utility+hook, event-driven)

**Analog:** `frontend/src/components/stalls/stall-map.tsx:40-69` (`useIsDesktop`) — struktura uchun; `frontend/src/components/shell/locale-switcher.tsx` — yozish/saqlash yarmi uchun.

**Nimani ko'chirish kerak** — DOM tashqi tizim bo'lgani uchun `useSyncExternalStore`:

```ts
// src/components/stalls/stall-map.tsx:60-69
/**
 * Ekran kengligi — TASHQI TIZIM, shuning uchun `useSyncExternalStore`.
 *
 * `useEffect` + `setState` varianti gidratatsiya nomuvofiqligini ham,
 * kaskadli renderni ham keltirib chiqarardi. Server surati `true`:
 * JS ishlamaydigan holatda ham barcha zonalar OCHIQ qoladi.
 */
function useIsDesktop(): boolean {
  return useSyncExternalStore(subscribeToDesktop, readIsDesktop, () => true);
}
```

09-RESEARCH Naqsh 4 buni AYNAN shu sabab bilan `theme.ts` uchun talab qiladi: `getServerSnapshot` — `"light"` qaytaradi (`stall-map.tsx` dagi `() => true` bilan bir xil rol — SSR'da mavjud bo'lmagan holat uchun xavfsiz standart).

**Yozish yarmi uchun** — `locale-switcher.tsx:55-76` dagi "o'zgartir + saqla, xatoni yutib yubor" naqshi:

```ts
// src/components/shell/locale-switcher.tsx:55-76 (soddalashtirilgan)
function change(next: ApiLocale) {
  if (next === active) return;
  startTransition(() => {
    router.replace(pathname, { locale: next });
    // ... profilga yozish, xato bo'lsa jim ketadi (foydalanuvchi to'xtamaydi)
  });
}
```

**Nimani KO'CHIRMASLIK kerak:**
1. `locale-switcher.tsx` tanlovni **serverga** (`PATCH /me`) yozadi — tema esa UI-SPEC §11.2 bo'yicha qat'iyan **faqat `localStorage`**, serverga HECH QACHON yozilmaydi. `apiFetch(ME_PATH, ...)` chaqiruvini KO'CHIRMANG.
2. `stall-map.tsx` **o'qiydigan** hook (`MediaQueryList.matches`) — `theme.ts` esa DOM **atributini** (`documentElement.dataset.theme`) o'qishi kerak, `matchMedia` emas. `subscribeToDesktop`'dagi `list.addEventListener("change", ...)` o'rniga `MutationObserver` kerak bo'ladi (A5: taxmin, past xavf).
3. `auth-store.ts` dagi og'irroq modul-darajasidagi pub-sub'ni ANALOG sifatida OLMANG — u JWT sessiyasi uchun maxsus qurilgan (xotirada, `client-only`), tema esa oddiy, faqat DOM+localStorage.

---

### `frontend/src/lib/use-count-up.ts` (hook, transform)

**Analog:** To'g'ridan-to'g'ri yo'q — [M-34] kodbazada `requestAnimationFrame` **0 marta** ishlatilgan. Eng yaqin **rol** bo'yicha o'xshashlik: `frontend/src/lib/wilson.ts` va `frontend/src/lib/zone-geometry.ts` — ikkalasi ham `lib/` da yashaydigan **sof funksiya + tor hook**, DOM'siz, React holatisiz yadro bilan.

**Nimani ko'chirish kerak** — `wilson.ts` dan **modul konvensiyasi**:
- Fayl boshida bitta katta docstring: NEGA bu yerda (kutubxona emas, formula), qanday tekshiriladi
- Eksport qilingan sof funksiya + ichki yordamchi (`assertCount` kabi) eksport qilinmaydi
- "Kutubxona nega qo'shilmaydi" mulohazasi izohda yozilgan (09-UI-SPEC §Qo'lda yozilmasin jadvalidagi "Sanoq animatsiyasi" qatoriga mos)

09-RESEARCH Naqsh 6 aniq talab qiladi:
```
rAF + kubik ease (1-(1-p)³); oraliq kadrlar Math.round(); oxirgi kadr AYNAN format.number(value)
```

**Nimani KO'CHIRMASLIK kerak:** `wilson.ts`/`zone-geometry.ts` — HECH QANDAY `useEffect`/`requestAnimationFrame` ishlatmaydi (ular butunlay sinxron matematika). `use-count-up.ts` esa hook qismida albatta `useEffect` + `requestAnimationFrame` + tozalash (`cancelAnimationFrame`) kerak bo'ladi — bu qism ULARDAN emas, React hujjatidan olinadi. `C-7` (CLAUDE.md): oraliq qiymatlar `Math.round()`, HECH QACHON `toFixed`/`parseFloat` emas — pul butun so'm.

---

### `frontend/src/components/shell/theme-toggle.tsx` (component, request-response)

**Analog:** `frontend/src/components/shell/locale-switcher.tsx` — 09-RESEARCH bu faylni "naqshning aynan nusxasi" deb ataydi.

**Nimani ko'chirish kerak** — butun render tuzilishi:

```tsx
// src/components/shell/locale-switcher.tsx:78-107
<div
  aria-label={t("languageLabel")}
  className="inline-flex items-center gap-1 rounded-md border border-border bg-surface p-1"
  role="group"
>
  {LOCALES.map((code) => {
    const isActive = code === active;
    return (
      <button
        aria-current={isActive ? "true" : undefined}
        className={cn(
          "rounded-sm px-2 py-1 text-xs font-semibold transition-colors",
          "disabled:pointer-events-none disabled:opacity-50",
          isActive
            ? "bg-accent text-accent-fg"
            : "text-text-muted hover:bg-surface-muted hover:text-text",
        )}
        disabled={isPending}
        key={code}
        onClick={() => change(code)}
        type="button"
      >
        {LOCALE_LABELS[code]}
      </button>
    );
  })}
</div>
```

`role="group"` + `aria-label` + `aria-current="true"` — UI-SPEC §15 bu naqshni so'zma-so'z talab qiladi ("Tema tugmasi | `role="group"` + `aria-label` + `aria-current="true"` — ⛔ `LocaleSwitcher` naqshi").

**Nimani KO'CHIRMASLIK kerak:**
1. `useTransition`/`router.replace` — bular marshrut almashtirish uchun; tema hech qanday marshrutga tegmaydi.
2. `LOCALES.map(...)` — statik massiv o'rniga `theme-toggle.tsx` uchta qat'iy qiymatli (`light`/`dark`/`sun`) reyestrni ishlatadi (G-motion-4(d): "aynan 3 a'zo").
3. Tugma o'lchami: `locale-switcher.tsx` `px-2 py-1` (kichik, header ichida qulay); UI-SPEC §15 "Barmoq nishoni ≥44px — tema tugmalari `min-h-11`" deydi — bu FARQ, ko'r nusxa emas.

---

### `frontend/src/components/collect/success-choreography.tsx` (imperativ utility, event-driven)

**Analog:** To'g'ridan-to'g'ri yo'q ([M-34]: fayl bugun mavjud emas). Ulanish nuqtasi **allaqachon mavjud** analog: `frontend/src/components/collect/collect-session.tsx:265-295` (`onWritten`).

**Nimani ko'chirish kerak** — `onWritten` ning MAVJUD tartibi (kengaytiriladi, qayta yozilmaydi):

```tsx
// src/components/collect/collect-session.tsx:265-295
const onWritten = useCallback(
  (record: PaymentRecord) => {
    setWrote(record);
    dropPendingAfterPayment(client, marketId);
    setSubmittedCode("");
    setDraft("");
    setMethod(null);
    setExtraAmount(null);
    setOverride(null);

    /* ⛔ Fokus qidiruv maydoniga QAYTADI — kassir hech nima bosmaydi. */
    inputRef.current?.focus();

    toast.success(
      `${t("collect.written")} · ${record.stall_code} · ${money(record.amount_soum)}`,
    );
  },
  [client, marketId, money, t],
);
```

09-UI-SPEC §8.3 — xoreografiya **shu blokdan KEYIN**, `focus()`'dan **keyin**, `toast.success`'dan **keyin** qo'shiladi, `await`siz, `try/catch` ichida (09-RESEARCH Kod namunalari 2):

```tsx
inputRef.current?.focus();                         // 6-QADAM — BIRINCHI (o'zgarmaydi)
toast.success(`${t("collect.written")} · …`);

// 1–5-QADAM SHU YERDAN. `await` YO'Q. `try/catch` MAJBURIY:
try {
  flyAmountToList({ from: amountRef.current, to: listRef.current });
} catch { /* bayram — bezak; oqimni to'xtatmaydi */ }
```

**Modul shakli uchun ikkinchi analog** — `frontend/src/lib/zone-geometry.ts` (DOM'siz, React'siz sof funksiyalar moduli hujjatlash konvensiyasi): katta docstring header, "QAROR N" formatidagi bo'limlar, rad etilgan muqobillar aniq yozilgan.

**Nimani KO'CHIRMASLIK kerak:**
1. `onWritten`ning ICHIGA yozmang — xoreografiya **tashqi**, alohida modul/funksiya bo'lib qoladi va `onWritten` faqat uni **chaqiradi** (import qilingan `flyAmountToList` kabi).
2. `setTimeout` ichida **hech qanday** `setState`/`set[A-Z]` chaqiruvi bo'lmasin (G-motion-2(d), AST bilan tekshiriladi) — `setTimeout` FAQAT `clone.remove()` uchun.
3. jsdom'da `getBoundingClientRect()` **0** qaytaradi — 09-RESEARCH Tuzoq 1: bo'lish amali (`/`) qilinmasin, `NaN` xavfi bor.
4. Kod namunasi 3 (`flyAmountToList`) — `pointer-events` **inline** stil bilan beriladi (`clone.style.pointerEvents = "none"`), CSS klassi bilan EMAS: jsdom Tailwind sinfini KO'RMAYDI (`getComputedStyle` `"auto"` qaytaradi class-only holatda).

---

### `frontend/src/components/dashboard/revenue-card.tsx` va `occupancy-donut.tsx` (component, request-response)

**Analog 1 (karta qobig'i + huquqsiz-fetch himoyasi):** `frontend/src/components/dashboard/market-status-card.tsx`

```tsx
// src/components/dashboard/market-status-card.tsx:77-96 (qisqartirilgan)
export function MarketStatusCard({ isActive, marketId }: MarketStatusCardProps) {
  const setupStatus = useSetupStatusQuery(marketId);
  const users = useUsersQuery();

  /* Bozor tanlanmagan — so'rov ham yuborilmaydi, karta ham chizilmaydi. */
  if (marketId === null) return null;

  const busy = setupStatus.isPending || users.isPending;
  const count = (value: number | undefined): string =>
    value === undefined ? UNKNOWN : format.number(value);

  return (
    <Card aria-busy={busy ? true : undefined}>
      <CardHeader className="pb-2">
        <h2 className="text-lg font-semibold">{t("dashboard.marketStatus")}</h2>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {busy ? <span className="sr-only" role="status">{t("common.loading")}</span> : null}
        {/* ... */}
      </CardContent>
    </Card>
  );
}
```

Bu fayl komponentning **rolni o'qimasligi** naqshini ham ko'rsatadi — shart (`report_view`) `dashboard/page.tsx` da, komponentda EMAS (§Naqsh 5, G-motion-6(c)).

**Analog 2 (mavjud data hook — YANGI so'rov QURILMAYDI):**

```ts
// src/lib/report-queries.ts:179-195
export function useRevenueReport(
  period: ReportPeriod,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: reportKey(marketId ?? "", "revenue", period.from, period.to),
    queryFn: () => apiFetch(buildReportDataPath("revenue", period), { schema: revenueReportSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
    staleTime: REPORT_STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });
}
```

```ts
// src/lib/occupancy-queries.ts:138-155 — occupancy-donut uchun
export function useOccupancyDay(day: string, todayIso: string, options?: { enabled?: boolean }) {
  // ...
  refetchInterval: () => occupancyPollInterval({ day, todayIso }),
  refetchIntervalInBackground: false,
}
```

⚠ 09-RESEARCH Tuzoq 3 va 4: `occupancy-donut.tsx` **bugun**ni emas, **kecha**ni so'rasin (`useOccupancyDay(kecha, todayIso)`) — chunki (a) bugungi kun har doim BO'SH javob beradi [VERIFIED: `occupancy.py:114` docstring] va (b) `day === todayIso` bo'lganda avtomatik poll YOQILADI, bu esa UI-SPEC §10.6 "Avtomatik poll QO'SHILMAYDI" qoidasini buzadi. Kechani so'rash ikkala tuzoqni ham bir yo'la yopadi.

**Analog 3 (sof SVG render — kutubxonasiz):** `frontend/src/components/camera-zones/zone-canvas.tsx:265-298` (`viewBox`, `<polygon>`, `<circle>` — kodbazadagi YAGONA qo'l bilan yozilgan SVG geometriyasi):

```tsx
// src/components/camera-zones/zone-canvas.tsx (struktura, taxminiy)
<svg
  aria-hidden="true"
  viewBox={`0 0 ${VIEW_WIDTH} ${vh}`}
  // ...
>
  <polygon /* ... */ />
</svg>
```

**Nimani KO'CHIRMASLIK kerak:**
1. `zone-canvas.tsx` konteyner `aria-hidden="true"` beradi, chunki ochiqlik **birodar** `zone-list.tsx` da yashaydi. `revenue-card`/`occupancy-donut` uchun bu **teskari**: UI-SPEC §10.4 aniq talab qiladi — `<title>` + `role="img"` + YONIDA matnli yig'indi, ya'ni SVG **o'zi** ochiq bo'lishi kerak. `aria-hidden="true"` ni ko'chirmang.
2. `market-status-card.tsx` `—` (UNKNOWN) belgisini "o'lchanmagan" uchun ishlatadi — sparkline/donut uchun bu boshqacha: ma'lumot yetarli bo'lmasa (7 kundan kam nuqta) chiziq **umuman chizilmaydi**, `EmptyState` chiqadi (D-10 "o'lchanmagan son chizilmaydi" — `—` emas, butun blok almashadi).
3. `useRevenueReport`/`useOccupancyDay` ICHIGA hech narsa qo'shilmaydi (yangi parametr, yangi maydon) — ular **mavjud holicha** chaqiriladi; `occupancy-donut.tsx` faqat `select:` bilan javobni ikkita songa qisqartiradi (react-query `select`, keshga tegmaydi) — Tuzoq 4 ning uchinchi ta'siri.
4. `market-status-card.tsx` ikki MUSTAQIL so'rovni (`setupStatus`, `users`) alohida `isPending` bilan ko'rsatadi — sparkline/donut uchun BITTA so'rov, demak bu qismni soddalashtirib ko'chiring.

---

### `frontend/scripts/motion-tokens.test.mjs`, `theme-tokens.test.mjs`, `contrast.test.mjs`, `typography.test.mjs` (test, batch)

**Analog:** `frontend/scripts/collect-surface.test.mjs` (632 qator) — bu TO'RTALA yangi fayl uchun ham **eng kuchli va yagona kerakli** analog. RESEARCH buni bevosita tasdiqlaydi: "4 ta yangi `scripts/*.test.mjs` skeleti... darvozalar komponentlardan oldin tirik bo'lsin" va "postcss import qilmasin" (§Qo'lda yozilmasin jadvali: "CSS parse darvozalarda ... Oddiy matn skani ... mavjud 18 ta `scripts/*.test.mjs` ning hech biri tashqi paketga bog'liq emas").

**Nimani ko'chirish kerak** — to'rtta mexanik naqsh, aynan shu tartibda:

1. **Reyestr + QUYI chegara + takror nazorati:**
```js
// scripts/collect-surface.test.mjs:91-142
const FORBIDDEN_NAMES = [ /* ... */ ];
const MIN_FORBIDDEN_NAMES = 14;
// ...
test("reyestrlar uzunligi quyi chegaradan kam EMAS", () => {
  assert.ok(FORBIDDEN_NAMES.length >= MIN_FORBIDDEN_NAMES, /* ... */);
  assert.equal(new Set(FORBIDDEN_NAMES).size, FORBIDDEN_NAMES.length, /* takror nazorati */);
});
```
G-motion-3(a) uchun bu — ruxsat etilgan `@keyframes` xossalari to'plami (`{transform, opacity, background, ...}`); G-motion-7(d) uchun — `text-base ≤7` kabi YUQORI chegaralar (o'sishni to'xtatish, kamayishni emas).

2. **Izohlarni olib tashlash + "yutib yubormaslik" nazorati** (`contrast.test.mjs` uchun MUHIM — `globals.css` dagi `N.NN:1` izohlarini o'qish kerak, lekin CSS izohi ICHIDAGI eski raqamlarni EMAS):
```js
// scripts/collect-surface.test.mjs:215-298 — stripComments() + readCode()
// runaway nazorati: agar filtr butun faylni yutib yuborsa (masalan
// `@theme` bloki "kodsiz" ko'rinsa), keyingi barcha assert JIMGINA
// yashil bo'ladi — buni ushlaydigan alohida test bor.
```

3. **Hosila qamrov, qo'lda ro'yxat YO'Q:**
```js
// scripts/collect-surface.test.mjs:311-326
function listProductFiles(dir) {
  const found = [];
  for (const entry of readdirSync(dir)) {
    // rekursiv, .test. fayllarni chiqarib tashlaydi
  }
  return found;
}
```

4. **O'z-o'zini tekshiruvchi sun'iy-ijobiy nazorat** (UI-SPEC §16.3 "sabotaj majburiyati" — bu allaqachon mavjud madaniyat):
```js
// scripts/collect-surface.test.mjs:451-467
test("detektor sun'iy IJOBIY manbani USHLAYDI (uchala reyestr)", () => {
  assert.deepEqual(hitsOf("const s = { system_soum: 1 };", BLIND_DECLARATION_TOKENS), ["system_soum"]);
  // ...
});
```

**`contrast.test.mjs` uchun qo'shimcha analog** (sof matematika modul-hujjatlash uslubi): `frontend/src/lib/wilson.ts` — bitta formula, tashqi paketsiz, "nega kutubxona qo'shilmaydi" mulohazasi izohda. 09-RESEARCH Kod namunalari 5 kalkulyatorning to'liq kodini allaqachon beradi (`oklchToLinear`, `contrastRatio`) — bu kod **ko'chiriladi**, qayta ixtiro qilinmaydi.

**Nimani KO'CHIRMASLIK kerak:**
1. `collect-surface.test.mjs` `components/collect/` katalogini skanerlaydi — yangi fayllar `globals.css` (bitta fayl) yoki `components/**`/`package.json` ni skanerlaydi. `COLLECT_COMPONENTS`/`PENDING_QUERIES` konstantalarini ko'chirmang — o'z manzillaringizni yozing.
2. `collectMissingIsRecorded()` ("hali tug'ilmagan" holati) — bu FAQAT `components/collect/` 06-fazada hali mavjud bo'lmagani uchun kerak edi. `globals.css` va `package.json` BUGUN ham mavjud, ya'ni bu "ochiq qayd" mexanizmi kerak EMAS — soddalashtirib tashlang.
3. `G-motion-3(d)` (dependencies to'plam tengligi) uchun `collect-surface.test.mjs`da TO'G'RIDAN-TO'G'RI analog yo'q — eng yaqini `scripts/role-gate.test.mjs:195-217` (`assert.deepEqual([...frontend].sort(), [...backend].sort())` — ikki manbadan o'qib to'plam tengligini solishtirish). 09-RESEARCH ochiq ogohlantiradi: **son emas** (`length === 20`), **to'plam** (`assert.deepEqual(actual, EXPECTED_SET)`) — Tuzoq 5.

---

### `frontend/src/app/[locale]/(app)/dashboard/page.tsx` (page, request-response)

**Analog:** O'ZI — mavjud `MarketStatusCard` sharti aynan nusxalanadigan naqsh:

```tsx
// src/app/[locale]/(app)/dashboard/page.tsx:105-110
{hasPermission(roles, "market_manage") && principal?.marketId ? (
  <MarketStatusCard
    isActive={principal.marketIsActive}
    marketId={principal.marketId}
  />
) : null}
```

Ikki yangi karta AYNAN shu shaklda qo'shiladi, `report_view` bilan:
```tsx
{hasPermission(roles, "report_view") && principal?.marketId ? (
  <>
    <RevenueCard marketId={principal.marketId} />
    <OccupancyDonut marketId={principal.marketId} />
  </>
) : null}
```

**Test analogi:** `frontend/src/app/[locale]/(app)/dashboard/page.test.tsx` — H6/H7 `describe` bloklari ikki qatlamli tekshiruvni (DOM'da yo'qligi VA so'rov yuborilmaganligi) allaqachon ko'rsatadi:

```tsx
// page.test.tsx:160-179 — direktor blokining AYNAN o'zi kengaytiriladi
test("karta UMUMAN chizilmaydi VA `setup-status` ga so'rov ketmaydi", async () => {
  routeFetch();
  renderPage(["director"], { marketIsActive: false });
  expect(screen.getByText(messages.nav.dashboard)).toBeInTheDocument();
  await waitFor(() => { expect(requestedPaths().length).toBeGreaterThan(0); });
  expect(document.body.textContent).not.toContain(messages.dashboard.marketStatus);
  expect(requestedPaths().filter((path) => path.includes("setup-status"))).toEqual([]);
});
```

G-motion-6(b) uchun bu naqsh `cashier` roli bilan, `/reports/revenue` va `/occupancy` yo'llari uchun takrorlanadi.

**Nimani KO'CHIRMASLIK kerak:** `market_manage` — FAQAT `platform_admin` da bor huquq; yangi kartalar `report_view` bilan darvozalanadi (director + market_admin da bor, kassirda YO'Q [VERIFIED: `rbac.ts`]). Ikki huquqni aralashtirmang — noto'g'ri huquq bilan darvozalash kassirga tushum sizib chiqarishi mumkin (G-motion-6 ning butun maqsadi shuni oldini olish).

---

### `frontend/src/components/ui/button.tsx`, `card.tsx`, `dialog.tsx`, `skeleton.tsx` (ui primitivlar, CRUD)

**Button — bosish-masshtabi uchun analog:** `frontend/src/components/stalls/stall-cell.tsx:127`

```
"active:scale-[0.97] motion-reduce:scale-100"
```

09-UI-SPEC M-8 buni so'zma-so'z tasdiqlaydi: "bosish-masshtabi naqshi ALLAQACHON mavjud va reduced-motion bilan JUFT — §12.1 uni `ui/button.tsx` ga ko'taradi, ixtiro qilmaydi". Mavjud `button.tsx:14` qatori:

```tsx
// src/components/ui/button.tsx:10-17 (o'zgaradigan qism)
"transition-colors duration-150",
```

`duration-150` → `duration-(--motion-fast)` (Tailwind 4 `(--var)` sintaksisi), qo'shiladi `active:scale-[0.97] motion-reduce:scale-100`.

**Skeleton** — mavjud tuzilma (§26-37) saqlanadi, faqat `animate-pulse` → yangi `shimmer` klassi:
```tsx
// src/components/ui/skeleton.tsx:30-33
"animate-pulse rounded-sm bg-surface-muted motion-reduce:animate-none",
```
`motion-reduce:animate-none` qatori **o'zgarmaydi** — u allaqachon to'g'ri naqsh.

**Dialog** — Radix `DialogPrimitive.Content` avtomatik `data-state="open"|"closed"` beradi (kod hozir buni ishlatmaydi, lekin atribut allaqachon DOM'da bor); yangi CSS `data-[state=open]:` variant qo'shiladi `CONTENT_BASE`/`CONTENT_CENTERED` klasslariga (`dialog.tsx:46-51`).

**Nimani KO'CHIRMASLIK kerak:** `stall-cell.tsx`dagi naqsh **bandlik katakchasi** kontekstida (`role="button"`-ga yaqin element); `button.tsx` haqiqiy `<button>` elementi, ya'ni `:active` pseudo-klassi tabiiy ishlaydi — qo'shimcha `onPointerDown`/`onPointerUp` state kerak EMAS. `card.tsx` uchun `@media (hover:hover)` shart — telefonlarda "sticky hover" nuqsonining oldini olish uchun; bu `stall-cell.tsx` yoki `button.tsx`da yo'q qo'shimcha shart, ko'r nusxa ko'chirmang.

---

### `frontend/src/components/ui/field.tsx` — ⚠ ZIDDIYAT, rejalashtiruvchi hal qilishi kerak

09-UI-SPEC §3.3 jadvali `Field`ni **"Tegilmaydi"** ro'yxatida ko'rsatadi. Lekin §12.7 aniq talab qiladi: *"Xato maydoni ⛔ `translateX` shake (2px, 200ms, `--ease-out`) + xabar `translateY` bilan"*. `field.tsx:65-69` — xato blokining yagona joyi:

```tsx
{error ? (
  <p className="text-sm text-danger-text" id={`${id}-error`}>
    {error}
  </p>
) : null}
```

**Tavsiya:** `field.tsx`ning **props kontraktiga TEGMASDAN** (`FieldProps` o'zgarmaydi — §3.3 ning ma'nosi shu), faqat ICHKI render'ga shartli animatsiya klassi qo'shiladi (`error` mavjud bo'lganda). Bu "primitiv o'zgarmaydi" (API darajasida) va "shake qo'shiladi" (render darajasida) ikkalasini ham qondiradi. Reja bosqichida bu ziddiyat ochiq qayd etilishi kerak.

---

## Shared Patterns

### 1. jsdom guard — `typeof window.matchMedia !== "function"`
**Manba:** `src/components/stalls/stall-map.tsx:46,56`
**Qo'llaniladi:** `lib/motion.ts`, `lib/theme.ts` (agar `matchMedia` orqali sinxronlansa)
```ts
if (typeof window.matchMedia !== "function") return /* fail-safe qiymat */;
```

### 2. `useSyncExternalStore` — DOM/brauzer tashqi tizim uchun
**Manba:** `src/components/stalls/stall-map.tsx:60-69`
**Qo'llaniladi:** `lib/theme.ts` (DOM `data-theme` atributini o'qish)
```ts
return useSyncExternalStore(subscribe, readSnapshot, getServerSnapshot);
```
Server surati har doim SSR-xavfsiz standart qiymat qaytaradi (`stall-map.tsx`da `true`, `theme.ts`da `"light"`).

### 3. Gate script — reyestr + QUYI chegara + hosila skan + o'z-o'zini tekshiruv
**Manba:** `frontend/scripts/collect-surface.test.mjs` (to'liq)
**Qo'llaniladi:** 4 ta yangi `scripts/*.test.mjs` (motion-tokens, theme-tokens, contrast, typography)
- `MIN_*` konstantasi + `assert.ok(list.length >= MIN_*)`
- `new Set(list).size === list.length` (takror nazorati)
- `readdirSync` rekursiv — qo'lda ro'yxat YO'Q
- Sun'iy-ijobiy nazorat testi — "detektor haqiqatan ishlaydimi" o'z-o'zidan tekshiriladi

### 4. Huquq sharti — sahifada, komponentda EMAS
**Manba:** `src/app/[locale]/(app)/dashboard/page.tsx:105-110`
**Qo'llaniladi:** `dashboard/page.tsx` (revenue-card, occupancy-donut qo'shilishi)
```tsx
{hasPermission(roles, "<permission>") && principal?.marketId ? <Card .../> : null}
```
Komponent ICHIDA `hasPermission(` chaqiruvi 0 marta bo'lishi kerak (G-motion-6(c) buni mexanik tekshiradi).

### 5. `Loader2` + `motion-reduce:animate-none`
**Manba:** `src/components/snapshots/capture-cell.tsx:273` (kodbazadagi YAGONA to'g'ri namuna)
**Qo'llaniladi:** `collect/payment-bar.tsx:293`, `collect/shift-close-form.tsx:280`, `collect/shift-open-card.tsx:154`, `review/decision-bar.tsx:150`
```tsx
className={cn("size-4", state === "running" ? "animate-spin motion-reduce:animate-none" : null)}
```
Sodda holatlarda (`<Loader2 className="animate-spin" />`) faqat `motion-reduce:animate-none` qo'shiladi.

### 6. Reduced-motion — global CSS, komponent darajasida EMAS
**Manba:** 09-RESEARCH Kod namunalari 1 (`globals.css`ga yangi blok, kodbazada hozircha 0 marta [M-6])
```css
@layer base {
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
}
```
Bu blok **BARCHA** yangi/o'zgaruvchi komponentlar uchun umumiy zaxira qatlam — har komponent o'z ichida `prefers-reduced-motion` so'ramaydi (faqat `lib/motion.ts` orqali DOM klon yaratish/yaratmaslikni hal qilganda).

### 7. i18n kalit qo'shish — mavjud namespace tuzilishi
**Manba:** `frontend/messages/uz-Latn.json:1391-1399` (`dashboard` namespace)
```json
"dashboard": {
  "marketStatus": "Bozor holati",
  // ... 7 yangi kalit shu yerga qo'shiladi
}
```
Yangi `theme` namespace uchun aniq joy ko'rsatilmagan — `common` (global UI-chrome) yonida yoki fayl oxirida qo'shilishi mumkin; ikkalasi ham mavjud konvensiyaga (feature-xronologik tartib, alifbo emas) mos.
⚠ `uz-Cyrl.json` QO'LDA TAHRIRLANMAYDI — `npm run i18n:gen` orqali generatsiya qilinadi (`gen-cyrillic.mjs`); `uz-Cyrl.overrides.json` HAM tegilmaydi.

---

## Analog topilmadi

| Fayl | Rol | Data-flow | Sabab |
|---|---|---|---|
| `frontend/src/lib/use-count-up.ts` | hook | transform | [M-34] kodbazada `requestAnimationFrame` 0 marta ishlatilgan; RESEARCH Kod namunalari 6 asosida yoziladi (rAF+kubik ease+`Math.round`), `wilson.ts`/`zone-geometry.ts` faqat MODUL KONVENSIYASI uchun ishlatiladi |
| `frontend/src/components/collect/success-choreography.tsx` | imperativ utility | event-driven (FLIP) | [M-34] fayl bugun yo'q; eng yaqin narsa — `zone-canvas.tsx`ning DOM-manipulyatsiya USLUBI emas, balki `onWritten` ULANISH nuqtasi. 09-RESEARCH Kod namunalari 3 to'liq kodni beradi |
| `frontend/src/components/dashboard/{revenue-card,occupancy-donut}.tsx` — SVG chizish qismi | component | request-response | Sparkline/donut geometriyasi (`stroke-dasharray`/`stroke-dashoffset`) kodbazada mutlaqo yo'q; `zone-canvas.tsx` faqat SVG **konteyner** konvensiyasi (viewBox, aria) uchun qisman analog, chizish mantig'i RESEARCH'dan (A6: `stroke-dasharray: 220` — ko'z bilan sozlangan taxmin) |
| Jadval qator hover (§12.8) | — | CRUD | UI-SPEC o'zi buni "tarqoq" deb ataydi — 12+ faylda (`billing/charge-list.tsx`, `reports/revenue-report.tsx`, `stalls/stall-list.tsx` va h.k.) mustaqil `<table>` ishlatiladi, umumiy `ui/table.tsx` primitiv YO'Q. Yagona fayl-darajasidagi xarita mumkin emas — bu Wave 3 ("kichik, tarqoq") ga qoldirilgan, har jadval o'z faylida alohida hal qilinadi |

---

## Metadata

**Analog qidiruv doirasi:** `frontend/src/components/**`, `frontend/src/lib/**`, `frontend/src/app/**`, `frontend/scripts/**`, `frontend/messages/**`
**Skanerlangan fayllar:** ~180 (`src/components` va `src/lib` daraxti to'liq `find`/`grep` bilan)
**Naqsh ajratish sanasi:** 2026-08-17

**Asosiy topilma:** Bu faza deyarli hech qanday tubdan yangi UI naqsh talab qilmaydi. To'rtta kuchli, aniq analog butun fazaning 70%+ ini qamraydi:
1. `stall-map.tsx` (matchMedia guard + useSyncExternalStore) → `lib/motion.ts`, `lib/theme.ts`
2. `locale-switcher.tsx` (role="group" tugma guruh + saqlash) → `shell/theme-toggle.tsx`
3. `collect-surface.test.mjs` (reyestr + hosila skan + o'z-o'zini tekshiruv) → 4 ta yangi `scripts/*.test.mjs`
4. `dashboard/page.tsx:105-110` (huquq sharti sahifada) → ikki yangi dashboard kartasi

Yagona haqiqiy "noldan yozish" ikkita joy: `use-count-up.ts` (rAF) va `success-choreography.tsx` (FLIP klon) — ikkalasi ham 09-RESEARCH'da to'liq kod namunasi bilan tayyor (Kod namunalari 3, Naqsh 6), demak "analog yo'q" amalda "tayyor retsept RESEARCH'da" degani.
