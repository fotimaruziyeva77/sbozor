# Phase 10: landing-sbozor-uz — Naqsh xaritasi

**Xaritalandi:** 2026-08-17
**Fayllar tahlil qilindi:** 36 (yangi + o'zgartiriladigan)
**Analoglar topildi:** 30 / 36 (6 tasi kodbazada analogsiz — yangi mexanika)

---

## Fayl klassifikatsiyasi

| Yangi/O'zgartiriladigan fayl | Rol | Data-oqim | Eng yaqin analog | Moslik |
|---|---|---|---|---|
| `frontend/src/app/[locale]/(marketing)/layout.tsx` | route/layout | request-response (SSG) | `frontend/src/app/[locale]/(auth)/layout.tsx` + `frontend/src/app/[locale]/layout.tsx` (provayder tartibi) | rol-mos + naqsh-mos |
| `frontend/src/app/[locale]/(marketing)/page.tsx` | route/page | request-response (SSG) | `frontend/src/app/[locale]/(auth)/login/page.tsx` | aynan |
| `frontend/src/app/[locale]/(marketing)/maxfiylik/page.tsx` | route/page | request-response (SSG) | `frontend/src/app/[locale]/(auth)/login/page.tsx` | rol-mos |
| `frontend/src/app/[locale]/page.tsx` | route/page | — | **O'CHIRILADI** | n/a |
| `frontend/src/app/[locale]/layout.tsx` | route/layout | request-response (SSG) | o'zi (hozirgi holat — provayderlar chiqariladi) | aynan (diff) |
| `frontend/src/app/[locale]/(app)/layout.tsx` | route/layout | request-response | o'zi (hozirgi `AppLayout`) | aynan (diff) |
| `frontend/src/app/[locale]/(auth)/layout.tsx` | route/layout | request-response | o'zi (hozirgi holat) | aynan (diff) |
| `frontend/src/components/shell/app-providers.tsx` | provider | event-driven (lifecycle) | `frontend/src/app/[locale]/layout.tsx:112-121` (provayder tanasi) | aynan (ko'chirish) |
| `frontend/src/components/marketing/hero.tsx` | component (server) | request-response | `frontend/src/app/[locale]/(auth)/login/page.tsx` (server komponent kompozitsiyasi) | rol-mos |
| `frontend/src/components/marketing/hero-scene.tsx` | component (client) | event-driven | `frontend/src/components/dashboard/revenue-card.tsx` + `frontend/src/components/collect/success-choreography.tsx` + `frontend/src/components/review/review-session.tsx` | qisman (3 analog kombinatsiyasi — pastga qarang) |
| `frontend/src/components/marketing/step-line.tsx` | component (client) | event-driven | `frontend/src/components/dashboard/revenue-card.tsx` (`--i` stagger) | qisman |
| `frontend/src/components/marketing/reveal.tsx` | component (client) | event-driven | `frontend/src/lib/motion.ts` (bir martalik guard idiomasi) | qisman — IntersectionObserver kodbazada YO'Q |
| `frontend/src/components/marketing/demo-form.tsx` | component (client) | request-response | `frontend/src/components/auth/login-form.tsx` | aynan |
| `frontend/src/components/marketing/section.tsx` | component (server) | transform | `frontend/src/components/ui/card.tsx` | rol-mos |
| `frontend/src/components/marketing/locale-switcher.tsx` | component (client) | event-driven | `frontend/src/components/shell/locale-switcher.tsx` | aynan (nimani OLISH/TASHLASH aniq) |
| `frontend/src/components/marketing/{pain-cards,role-cards,trust-block,faq,footer,header}.tsx` | component (server) | transform | `frontend/src/components/ui/card.tsx` + `frontend/src/components/ui/badge.tsx` | rol-mos |
| `frontend/src/app/sitemap.ts` | config (route) | batch | — | analog YO'Q (Next rasmiy naqsh) |
| `frontend/src/app/robots.ts` | config (route) | batch | `frontend/scripts/motion-tokens.test.mjs::listProductFiles` (hosila-ro'yxat idiomasi) | qisman |
| `frontend/src/app/globals.css` | config | transform | o'zi (mavjud `@keyframes`/`@theme` bloklari) | aynan |
| `frontend/src/components/ui/button.tsx` | component (ui) | transform | o'zi (mavjud `size` variantlari) | aynan |
| `frontend/scripts/landing-surface.test.mjs` | test (gate) | batch | `frontend/scripts/motion-tokens.test.mjs` | aynan (bir fayl, ko'p tekshiruv) |
| `frontend/scripts/phase10-criteria.test.mjs` | test (meta-gate) | batch | `frontend/scripts/phase9-criteria.test.mjs` | aynan |
| `frontend/src/components/marketing/hero-scene.test.tsx` | test (vitest) | batch | `frontend/src/components/collect/success-choreography.test.tsx` (matchMedia stub) | qisman |
| `frontend/src/components/marketing/demo-form.test.tsx` | test (vitest) | batch | — | analog YO'Q (`login-form.test.tsx` mavjud emas) |
| `frontend/messages/uz-Latn.json` (+ru, +uz-Cyrl generated) | i18n data | transform | o'zi (31 mavjud fazoviy nom) | aynan |
| `frontend/messages/uz-Cyrl.overrides.json` | i18n data | transform | o'zi (`"IR": "IR"` juftligi) | aynan |
| `frontend/scripts/gen-cyrillic.test.mjs` | test (gate) | batch | o'zi (`allowed` regeksi, `_comment_alphanumeric` naqshi) | aynan |
| `frontend/scripts/error-codes.test.mjs` | test (gate) | batch | o'zi (`MARKET_ERROR_CODES` ko'zgu bloki) | aynan |
| `services/core-api/app/schemas.py` (qo'shimcha) | model | request-response | `LoginRequest`/`LoginResponse` (272-310-qatorlar) + `MARKET_ERROR_CODES` (645-qator) | aynan |
| `services/core-api/app/api/v1/public.py` (YANGI modul, nom rejaga ochiq) | controller | request-response | `services/core-api/app/api/v1/auth.py::login()` (256-320) + `app/api/internal/self_check.py` (auth-siz router) | qisman (ikki analog kombinatsiyasi) |
| `services/core-api/app/security/ratelimit.py` (qo'shimcha) | utility | CRUD (counter) | `check_bot_resolve_rate()` (215-267-qatorlar) | aynan |
| `services/core-api/app/deps.py` (qo'shimcha `SenderDep`) | utility | request-response | `get_cache`/`CacheDep` (221-227-qatorlar) | aynan |
| `services/core-api/app/main.py` (lifespan qo'shimchasi) | config | event-driven (lifecycle) | o'zi (86-125-qatorlar, `broker.startup()`/`state.cache` naqshi) | aynan |
| `tests/tenancy/test_cross_tenant.py` (`EXEMPT_ROUTES` qo'shimchasi) | test | batch | o'zi (`/api/v1/me` "global" yozuvi, 286-qator) | aynan |
| `tests/integration/test_demo_request.py` | test (integration) | request-response | `services/core-api/app/api/internal/self_check.py` (auth-siz kontrakt) + `tests/integration/test_alerting.py` (respx mock) | qisman |

---

## Naqsh tayinlashlari

### `frontend/src/app/[locale]/(marketing)/layout.tsx` (route/layout, request-response)

**Analog:** `frontend/src/app/[locale]/(auth)/layout.tsx` (soddaligi) + RESEARCH'ning tasdiqlangan kod namunasi (next-intl 4.13.4 API bilan tekshirilgan)

**Hozirgi `(auth)/layout.tsx` — TOR layout namunasi** (butun fayl, 19 qator):
```tsx
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 p-6">
      {children}
    </main>
  );
}
```

**Marketing layout — ko'chirish shakli** (RESEARCH tomonidan next-intl tipi bilan VERIFIED):
```tsx
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";

export default async function MarketingLayout({
  children, params,
}: { children: React.ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);                 // SSG sharti — birinchi
  const messages = await getMessages();      // server tomonda TO'LIQ — bepul

  return (
    <NextIntlClientProvider messages={{ common: messages.common, landing: messages.landing }}>
      {children}
    </NextIntlClientProvider>
  );
}
```

**NIMANI OLISH:** `setRequestLocale` birinchi chaqiruv tartibi (`[locale]/layout.tsx:61` naqshi), `getMessages()` dan keyin qo'lda `pick` qilish (`next-intl` da o'rnatilgan `pick` yo'q — RESEARCH VERIFIED).
**NIMANI TASHLASH:** `NuqsAdapter`/`QueryProvider`/`AuthProvider`/`Toaster` — bular `(app)`/`(auth)` ga tushadi (pastga qarang).
**Ehtiyot:** provayderga uzatilgan fazoviy nomlar (`["common","landing"]`) VA komponentlarda chaqirilgan `useTranslations()`/`getTranslations()` argumentlari BIR XIL reyestrning ikki yarmi — biri unutilsa `MISSING_MESSAGE` faqat brauzerda, hidratatsiyadan keyin chiqadi (Tuzoq 1, RESEARCH).

---

### `frontend/src/app/[locale]/layout.tsx` (route/layout) — provayderlarni chiqarish

**Analog:** o'zi — hozirgi 126 qatorlik fayl to'liq o'qildi.

**Hozirgi holat** (`E:\bozor\frontend\src\app\[locale]\layout.tsx:112-121`):
```tsx
<NextIntlClientProvider messages={messages}>
  <NuqsAdapter>
    <QueryProvider>
      <AuthProvider>
        {children}
        <Toaster position="top-center" richColors />
      </AuthProvider>
    </QueryProvider>
  </NuqsAdapter>
</NextIntlClientProvider>
```

**Keyin qoladigan qism:** `<html lang data-theme suppressHydrationWarning>` + FOUC skripti (`layout.tsx:93-100`, **butunlay statik, o'zgarmaydi**) + `<body>` + `generateStaticParams` (26-29-qator) + `generateMetadata` (31-46-qator). Beshala provayder **chiqadi**, `{children}` to'g'ridan-to'g'ri `<body>` ichida qoladi.

**MAJBURIY tartib saqlanishi:** i18n → nuqs → query → auth → Toaster (izoh, 104-110-qator: `AuthProvider` eng ichkarida, chunki `QueryProvider` `subscribeSessionReset` ni ulaydi). `AppProviders` ichida bu tartib **aynan** ko'chiriladi.

---

### `frontend/src/components/shell/app-providers.tsx` (YANGI — provider)

**Analog:** `frontend/src/app/[locale]/layout.tsx:112-121` (provayder tanasi, yuqoridagi bilan bir xil kod bloki, endi mustaqil `"use client"` faylga ko'chadi).

```tsx
"use client";

export function AppProviders({ messages, children }: { messages: ...; children: React.ReactNode }) {
  return (
    <NextIntlClientProvider messages={messages}>
      <NuqsAdapter>
        <QueryProvider>
          <AuthProvider>
            {children}
            <Toaster position="top-center" richColors />
          </AuthProvider>
        </QueryProvider>
      </NuqsAdapter>
    </NextIntlClientProvider>
  );
}
```

**Ehtiyot (Tuzoq 3, RESEARCH):** `(app)/layout.tsx` bugun **o'zi** `"use client"` va `useAuthStore()`/`useTranslations()` ni **o'zi** chaqiradi (pastga qarang). `AppProviders` shu hook'lardan **tashqarida** turishi shart — ikkitasini bitta komponentga aralashtirish "hook provayderdan oldin ishladi" xatosini beradi.

---

### `frontend/src/app/[locale]/(app)/layout.tsx` (route/layout) — `AppProviders` + `AppGuard` ajratish

**Analog:** o'zi — hozirgi 134 qatorlik `AppLayout` to'liq o'qildi (`E:\bozor\frontend\src\app\[locale]\(app)\layout.tsx`).

**Hozirgi holat:** `"use client"` fayl, `useTranslations("shell")`, `useAuthStore()`, uchta `useEffect` (sessiya tiklash, `mustChangePassword`/`select-market` redirect, profil to'ldirish), `ready` hosila holati, skeleton fallback (114-130-qator), `return <AppShell>{children}</AppShell>` (132-qator).

**Yechim (Tuzoq 3):** mavjud butun tana **`AppGuard`** deb nomlangan ichki komponentga ko'chadi, `AppLayout` esa faqat:
```tsx
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppProviders messages={...}>
      <AppGuard>{children}</AppGuard>
    </AppProviders>
  );
}
```
**Ogohlantirish belgisi (mavjud, bepul erta signal):** `frontend/src/app/[locale]/(app)/layout.test.tsx` (7415 bayt) — bu fayl bugun mavjud va `AppLayout` ni to'g'ridan-to'g'ri render qiladi; noto'g'ri ajratilsa shu test qizaradi.

---

### `frontend/src/app/[locale]/(auth)/layout.tsx` (route/layout)

**Analog:** o'zi (19 qator, yuqorida to'liq keltirilgan).

**Yechim:** Server Component bo'lib qoladi, faqat `<AppProviders>` bilan o'raladi:
```tsx
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppProviders messages={...}>
      <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 p-6">
        {children}
      </main>
    </AppProviders>
  );
}
```
Server Component'dan klient komponentini render qilish — RESEARCH tomonidan **qonuniy** deb tasdiqlangan (§4.3).

---

### `frontend/src/components/marketing/hero.tsx` (server) va `(marketing)/page.tsx`

**Analog:** `frontend/src/app/[locale]/(auth)/login/page.tsx` (butun fayl, 44 qator, to'liq o'qildi).

**Naqsh:**
```tsx
export default async function LoginPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const t = await getTranslations("common");
  return (
    <Card>
      <CardHeader>
        <h1 className="text-2xl font-semibold tracking-tight">{t("appName")}</h1>
        <p className="text-sm text-text-muted">{t("appTagline")}</p>
      </CardHeader>
      <CardContent><LoginForm /></CardContent>
    </Card>
  );
}
```

**KO'CHIRISH:** `hasLocale`/`notFound`/`setRequestLocale` tartibi, server-side `getTranslations()`, server komponent klient formani `children` sifatida joylashtirishi (bu yerda `<LoginForm />` → landing'da `<DemoForm />`).
**TASHLASH:** `Card`/`CardHeader` — landing hero `text-hero` (yangi token) ishlatadi, `text-2xl` EMAS (§7.1.1 — G-land-5(a) shuni qulflaydi).
**Muhim farq:** `hero.tsx` da `"use client"` **0 marta** bo'lishi SHART (G-land-1(b)) — `h1` LCP nomzodi klient JS'ga bog'lanmaydi.

---

### `frontend/src/components/marketing/hero-scene.tsx` (client, event-driven) — ENG MURAKKAB FAYL

**Analog (uch manba kombinatsiyasi — kodbazada "taymer reyestri" naqshi YO'Q):**

**1) `frontend/src/components/dashboard/revenue-card.tsx`** (269 qator, to'liq o'qildi) — motion-enter + useCountUp + sr-only intizomi:
```tsx
<div className="motion-enter" style={{ "--i": 0 } as CSSProperties}>
  <Card aria-busy={report.isPending ? true : undefined} ref={cardRef}>
    ...
    <p className="text-2xl font-semibold tracking-tight">
      <span className="sr-only">{format.number(report.data.total_collected_soum)}</span>
      <span aria-hidden="true" className="font-mono" data-numeric>
        {format.number(shownTotal ?? report.data.total_collected_soum)}
      </span>
    </p>
```
**KO'CHIRISH:** `useCountUp(value, durationMs, updateDurationMs)` chaqiruv shakli (`frontend/src/lib/use-count-up.ts:77-152`, to'liq o'qildi) — hook FAQAT sonni qaytaradi, formatlash chaqiruvchida; `sr-only` (to'liq qiymat) + `aria-hidden` (sanalayotgan qiymat) juftligi.

**2) `frontend/src/components/collect/success-choreography.tsx`** (107 qator, to'liq o'qildi) — imperativ, holatsiz, faqat-tozalash uchun `setTimeout`:
```tsx
import { prefersReducedMotion } from "@/lib/motion";

export function flyAmountToList({ from, to }: FlyAmountOptions): void {
  if (prefersReducedMotion()) return;   // ⛔ ERTA RETURN — taymer UMUMAN yaratilmaydi
  ...
  window.setTimeout(() => clone.remove(), 450);   // FAQAT tozalash, holat o'zgartirish YO'Q
}
```
**KO'CHIRISH:** `prefersReducedMotion()` ni effekt/funksiya **BIRINCHI** qatorida tekshirish (Tuzoq 4 — aks holda taymerlar baribir yaratiladi va G-land-2(a) qizaradi).

**3) `frontend/src/components/review/review-session.tsx`** (`timerRef` + cleanup, 132-186-qatorlar, grep bilan tasdiqlangan):
```tsx
const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
...
useEffect(
  () => () => {
    if (timerRef.current !== null) clearTimeout(timerRef.current);
  },
  [],
);
```
**KO'CHIRISH VA KENGAYTIRISH:** bu yerda BITTA `timerRef` bor; hero-scene.tsx'ga **massiv** (`useRef<ReturnType<typeof setTimeout>[]>([])`) kerak — 5 fazaning har biri o'z taymerini push qiladi, `unmount`/to'xtash paytida hammasi `clearTimeout` qilinadi (G-land-2(d): "taymerlar soni == `clearTimeout` chaqiriqlari soni").

**⛔ ANALOG YO'Q:** `IntersectionObserver` kodbazada **hech qayerda ishlatilmagan** (grep: 0 natija). `document.visibilitychange` ham yo'q. Bu ikkalasi — G-land-2(e) va §5.6 mexanizm 2/3 — vanilladan yozilishi kerak, RESEARCH'ning kod namunalaridan tashqari boshqa manba yo'q. Tuzoq 5 ga ehtiyot: ko'rinuvchanlik (IntersectionObserver) va tab-fokus (visibilitychange) **ikki mustaqil shart, bitta natija** (`running = visible && !hidden`) — bitta bayroqqa yig'ilsa rewind bug'i chiqadi.

**`@keyframes` iste'moli** (`E:\bozor\frontend\src\app\globals.css:291-307`):
```css
@keyframes enter { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.motion-enter {
  animation: enter var(--motion-base) var(--ease-out) both;
  animation-delay: calc(var(--i, 0) * 60ms);
}
```
```css
@keyframes attention { from { box-shadow: 0 0 0 0 oklch(0.78 0.15 85 / 0.55); } to { box-shadow: 0 0 0 10px oklch(0.78 0.15 85 / 0); } }
.motion-attention { animation: attention var(--motion-slow) var(--ease-out) both; animation-iteration-count: 1; }
```
Ikkalasi ham **mavjud va qayta yozilmaydi** [L-10] — sinf nomlarini ishlatish kifoya.

---

### `frontend/src/components/marketing/step-line.tsx` (client)

**Analog:** `revenue-card.tsx` ning `--i` stagger naqshi (yuqorida) + `globals.css:343`dagi izoh: *«katak stagger'i `@keyframes` bilan emas, `transition-delay` bilan beriladi»*.

**CSS to'lish naqshi (UI-SPEC §10.2, `globals.css` ga qo'shiladigan)** — mavjud fayldagi hech qanday sinfga o'xshamaydi, lekin uslub bir xil:
```css
.landing-step-fill { transform: scaleY(0); transform-origin: top;
  transition: transform 900ms var(--ease-out); }
[data-step="1"] .landing-step-fill { transform: scaleY(0.3333); }
```
Bu — `card.tsx:27` dagi bare `transition hover:-translate-y-0.5` naqshining davomi (token asosidagi `transition`, `transition-[...]` ixtiyoriy sintaksisi EMAS — G-motion-3(b) taqiqi).

---

### `frontend/src/components/marketing/demo-form.tsx` (client, request-response) — ENG ANIQ ANALOG

**Analog:** `frontend/src/components/auth/login-form.tsx` (195 qator, to'liq o'qildi). Bu ikkalasi ham: (a) anonim/pre-session forma, (b) `react-hook-form` + `zodResolver`, (c) bitta `role="alert"` xato bloki, (d) `disabled={isSubmitting}` yagona shart.

**KO'CHIRISH — forma skeleti** (`login-form.tsx:57-96, 142-193`):
```tsx
const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
  resolver: zodResolver(schema),
  defaultValues: { ... },
});

async function onSubmit(values: FormValues) {
  setFormError(null);
  try {
    const response = await /* fetch */;
    /* success */
  } catch (error) {
    setFormError(t(errorKey(error)));
  }
}

return (
  <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit(onSubmit)}>
    <Field error={errors.phone?.message} id="phone" label={t("...")}>
      <Input id="phone" type="tel" inputMode="tel" {...register("phone")}
        aria-invalid={errors.phone ? true : undefined}
        aria-describedby={errors.phone ? "phone-error" : undefined} />
    </Field>
    {formError ? (
      <p className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text" role="alert">
        {formError}
      </p>
    ) : null}
    <Button type="submit" size="lg" disabled={isSubmitting}>
      {isSubmitting ? t("...submitting") : t("...submit")}
    </Button>
  </form>
);
```
Bu naqsh **G-SUBMIT** (`submit-gate.test.mjs`) bilan avtomatik mos keladi (D-1: domen-shartli `disabled` yo'q — faqat `isSubmitting`).

**⛔⛔ NIMANI TASHLASH — B-2 ning to'g'ridan-to'g'ri sababi:** `login-form.tsx:13-14`
```tsx
import { ApiError, NetworkError, apiFetch } from "@/lib/api-client";
import { loginResponseSchema } from "@/lib/api-types";
```
Bu ikki import `demo-form.tsx` da **QILINMAYDI**. `api-client.ts` (`E:\bozor\frontend\src\lib\api-client.ts:7-20`) o'zi `api-types.ts` dan `apiErrorSchema`/`meResponseSchema`/`sessionResponseSchema` importlaydi — aynan shu graf **69 KB gzip** (B-2, o'lchandi). O'rniga:
```ts
// api-client.ts o'rniga — literal konstanta, modul importi YO'Q
const DEMO_REQUEST_PATH = "/api/v1/public/demo-requests";   // API_BASE_URL="/api/v1" konstantasi naqshi (api-client.ts:31)
// mahalliy zod sxema — demo-form.tsx ICHIDA, api-types.ts dan EMAS
const schema = z.object({ name: z.string().trim().min(2), phone: z.string().trim().min(9), ... });
// oddiy fetch — ApiError/NetworkError klasslarisiz
const res = await fetch(DEMO_REQUEST_PATH, { method: "POST", body: JSON.stringify(payload), headers: {"Content-Type":"application/json"} });
```
**Sabab:** `react-hook-form` + `zod` resolver — alohida, arzon chunk (31 KB xom / 11 KB gzip, RESEARCH o'lchovi) va u **kerak**; `api-client`/`api-types` grafi esa `LocaleSwitcher` bilan bir xil sababdan **kerak emas**.

**Checkbox uslubi (rozilik maydoni)** — `frontend/src/components/wizard/market-requisites-form.tsx:565-572`:
```tsx
<input checked={checked} className="size-4 accent-accent" onChange={onToggle} type="checkbox" />
```

---

### `frontend/src/components/marketing/section.tsx` (server, transform)

**Analog:** `frontend/src/components/ui/card.tsx` (47 qator, to'liq o'qildi) — soddaligi va `cn()` bilan `className` uzatish naqshi:
```tsx
export type CardProps = ComponentPropsWithRef<"div">;
export function Card({ className, ...props }: CardProps) {
  return <div className={cn("rounded-lg border ...", className)} {...props} />;
}
```
`section.tsx` xuddi shu shaklda, lekin `py-16`/`py-24` (§8.2, YANGI, faqat shu faylda) responsive breakpoint bilan.

---

### `frontend/src/components/marketing/locale-switcher.tsx` (client) — B-1 yechimi C

**Analog:** `frontend/src/components/shell/locale-switcher.tsx` (177 qator, to'liq o'qildi).

**NIMANI OLISH (aynan):**
- Sirg'anuvchi indikator naqshi (86-176-qator) — `LOCALES.map()`, `activeIndex`, `translateX(calc(var(--idx) * (100% + 0.25rem)))`.
- `usePathname`/`useRouter` **faqat** `@/i18n/navigation` dan (8-qator) — Next'ning o'z navigatsiya moduli EMAS (grep darvozasi bilan qulflangan qoida).
- `router.replace(pathname, { locale: next })` chaqiruvi (98-qator).
- `useLocale()`/`useTranslations("common")` (5, 87-qator).

**NIMANI TASHLASH (B-1 ning butun mohiyati):**
```tsx
// ⛔ shell/locale-switcher.tsx:8,10-14,16,92,103-113 — hech biri marketing variantida YO'Q
import { apiFetch } from "@/lib/api-client";
import { LOCALE_LABELS, LOCALES, meLocaleResponseSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
...
const { accessToken, updatePrincipal } = useAuthStore();   // ⛔ throw qiladi, provayder yo'q
...
if (!accessToken) return;
updatePrincipal({ locale: next });
void apiFetch(ME_PATH, { method: "PATCH", ... });           // ⛔ PATCH /me — anonim uchun ma'nosiz
```
**O'rniga:** `LOCALE_LABELS` obyekti **literal** ko'chiriladi (B-1 tahlili, `A8` taxmin jurnalida): endonimlar tarjima qilinmaydi, ya'ni takror emas — ikkinchi manba drift bermaydi. `LOCALES` massivi ham literal (`["uz-Latn", "uz-Cyrl", "ru"] as const`, `frontend/src/lib/api-types.ts:16` dan literal nusxa, import EMAS). Faqat URL almashadi, `AuthStore`ga umuman tegilmaydi.

**Muqobil (agar reja takrorni istamasa):** `LOCALE_LABELS` ni `api-types.ts` dan **zodsiz** `lib/locales.ts` ga ko'chirish, `api-types.ts` undan re-export qiladi — bitta qatorlik ko'chirish.

---

### `frontend/src/app/globals.css` — token va keyframe qo'shimchasi

**Analog:** o'zi, mavjud `--text-display` bloki (61-62-qator) va `@keyframes attention` bloki (345-358-qator) — izoh uslubi va joylashuv qoidasi naqsh sifatida ko'chiriladi.

**`--text-hero` qo'shish o'rni** (`@theme` bloki, 20-62-qator oralig'ida, `--text-display` dan keyin):
```css
@theme {
  ...
  --text-display: 2.5rem;
  --text-display--line-height: 1.1;
  /* YANGI — G-land-5(a,b) bilan qulflangan, aynan 1 fayl/1 element */
  --text-hero: clamp(1.75rem, 4.4vw, 2.75rem);
  --text-hero--line-height: 1.15;
  --text-hero--letter-spacing: -0.02em;
}
```

**`sweep` `@keyframes` qo'shish o'rni** (`@layer components`, mavjud `@keyframes` reyestri 9-nomga chiqadi, 234-378-qator oralig'ida, mavjud `attention` blokidan keyin):
```css
/* Kamera nuri — 2s linear, FAQAT transform (L-8 tuzatishi, sketch'ning `left` xatosi EMAS). */
@keyframes sweep {
  from { transform: translateX(0); }
  to { transform: translateX(100cqw); }
}
.landing-sweep { animation: sweep 2s linear; }
```
**Ehtiyot:** ruxsat etilgan xossalar to'plami (`ALLOWED_KEYFRAME_PROPS`, `motion-tokens.test.mjs:82-91`) — `transform`/`opacity`/`background*`/`box-shadow`/`stroke-*` — `sweep` shu to'plamdan chetga chiqmaydi.

---

### `frontend/src/components/ui/button.tsx` — `hero` o'lchami

**Analog:** o'zi (73 qator, to'liq o'qildi), mavjud `size` varianti (38-45-qator):
```tsx
size: {
  sm: "h-9 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "min-h-11 px-6 py-3 text-sm",
  // YANGI — landing birlamchi CTA
  hero: "min-h-14 px-8 text-lg",
},
```
`variant`/`defaultVariants` **tegilmaydi**. `buttonVariants`/`SIZES` darvoza bilan qulflanmagan (L-18, grep 0 natija) — qo'shish hech qanday testni buzmaydi.

---

### `frontend/scripts/landing-surface.test.mjs` (YANGI — bitta faylda G-land-1,3,4,5)

**Analog PRIMARY:** `frontend/scripts/motion-tokens.test.mjs` (771 qator — registrlar + `stripComments` + `extractKeyframes` + har `G-motion-*` uchun alohida `test()` bloki + REYESTR NAZORATI yakuniy testi).

**KO'CHIRILADIGAN infratuzilma** (`motion-tokens.test.mjs:185-258` — `stripComments`, satr literallarini saqlagan holda izoh olib tashlash; **AYNAN NUSXA**, mustaqil to'rtinchi logika yozilmaydi — izoh shunday deydi):
```js
function stripComments(source) { /* code/line/block holat mashinasi — 79 qator, aynan ko'chiriladi */ }
```

**KO'CHIRILADIGAN — `@keyframes` parser** (`motion-tokens.test.mjs:311-329`):
```js
function extractKeyframes(source) {
  const blocks = [];
  for (const m of source.matchAll(/@keyframes\s+([A-Za-z_][\w-]*)/gu)) {
    /* qavs-balans bilan blok chegarasini topadi */
  }
  return blocks;
}
```

**⛔⛔ YANGI FUNKSIYA KERAK — G-land-3(a) mavjud darvozaning O'LCHANGAN BO'SHLIG'INI yopadi:** `motion-tokens.test.mjs` faqat `@keyframes` bloklarini parse qiladi, `.landing-*`/`.motion-*` sinflaridagi `transition:` deklaratsiyasini **tekshirmaydi** (RESEARCH L-8 shu bo'shliqni topdi: sketch manbasining `transition: height 900ms` i bugun **jimgina o'tib ketardi**). Yangi parser CSS klass selektorini (`.landing-step-fill { ... }`) topib, ichidagi `transition:` qatoridagi xossalarni ruxsat to'plamiga solishtiradi — `extractKeyframes` bilan bir xil qavs-balans texnikasi, boshqa selektor.

**KO'CHIRILADIGAN — fayl skaneri** (`motion-tokens.test.mjs:364-379`):
```js
function listProductFiles(dir, extensions) {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) found.push(...listProductFiles(full, extensions));
    else if (extensions.includes(path.extname(entry)) && !TEST_FILE.test(entry)) found.push(full);
  }
  return found;
}
```

**KO'CHIRILADIGAN — registri+testi juftligi shakli** (`motion-tokens.test.mjs:600-650`, G-motion-3(a) testi — G-land-3(a)/(d) uchun bevosita namuna):
```js
test("G-motion-3(a): har `@keyframes` faqat ruxsat etilgan xossalarni ishlatadi", () => {
  const blocks = extractKeyframes(css);
  assert.ok(blocks.length >= MIN_KEYFRAMES_BLOCKS, `...`);
  for (const { body, name } of blocks) {
    const props = keyframeProps(body);
    for (const prop of props) {
      if (!allowed.has(prop)) problems.push(`@keyframes ${name} -> \`${prop}\``);
      for (const banned of BANNED_KEYFRAME_PROPS) {
        if (prop === banned || prop.startsWith(`${banned}-`)) bannedHits.push(...);
      }
    }
  }
  assert.deepEqual(bannedHits, [], "..."); assert.deepEqual(problems, [], "...");
});
```

**SECONDARY — `DEVIATION_CEILINGS` massiv shakli** (G-land-5(d) uchun, `typography.test.mjs:112-121` naqshi):
```js
const DEVIATION_CEILINGS = [
  ["text-base", /\btext-base\b/gu, 7],
  ["text-xl", /\btext-xl\b/gu, 4],
];
```
Landing uchun bu chegaralar `marketing/**` skanida **0** bo'lishi kerak (mavjud repo-bo'ylab chegara allaqachon to'lgan, §0.2).

**SECONDARY — submit skan yuzasi** (`submit-gate.test.mjs:51-54`):
```js
const SRC = path.join(FRONTEND_ROOT, "src");
const TEST_FILE = /\.test\.tsx?$/;
```
Bu **mavjud** darvoza `src/**` ni skanerlaydi — `demo-form.tsx` avtomatik qamrovga tushadi, o'zgartirish shart emas (L-19).

---

### `frontend/scripts/phase10-criteria.test.mjs` (YANGI — meta-gate)

**Analog:** `frontend/scripts/phase9-criteria.test.mjs` (657 qator, **to'liq o'qildi**) — bu AYNAN bir xil vazifa, boshqa faza uchun.

**KO'CHIRILADIGAN struktura (naqsh butunlay, nomlar almashadi):**
1. `parseCriteria()` (289-316-qator) — `ROADMAP.md` dan `### Phase 9` / `**Success Criteria**` bo'limini parse qiladi → **Phase 10 uchun** `### Phase 10` ga almashadi.
2. Har SC uchun ikki dalil: (i) MAHSULOT — `readProduct(rel)` bilan `src/` fayli o'qiladi va oddiy `assert.ok`/`assert.match` bilan tekshiriladi; (ii) ZANJIR — `assertChainTsx`/`assertChainMjs` bilan test faylining CI glob'iga tushishi tasdiqlanadi (165-190-qator):
```js
function assertChainMjs(rel) {
  assert.ok(existsSync(path.join(FRONTEND_ROOT, rel)), `zanjir fayli TOPILMADI: ${rel}`);
  assert.match(rel, /^scripts\/[^/]+\.test\.mjs$/u, `...CI'da yugurmasdi`);
}
```
3. `CRITERION_ANCHORS` — har SC jumlasi o'z regex-langarini tashiydi (138-144-qator) — Phase 10 uchun `/anonim/iu`, `/12s|jonli/iu`, `/Telegram|bot/iu`, `/halol|yolg'on/iu`, `/Lighthouse|LCP/iu` kabi so'zlar.
4. META-test (534-591-qator) — AYNAN 5 mezon parse bo'lishi, modulda AYNAN 5 test bo'lishi, `gate`/`gate:fast` zanjirida ishga tushishi.
5. SOXTALASHTIRISH darvozasi (597-610-qator) — har SC bloki `src/` yoki `package.json` yoziga murojaat qilishi SHART.
6. REYESTR NAZORATI (616-656-qator) — `child_process`/`execSync` **importi YO'Q** ekanini o'z manbasidan tekshiradi (mavjud darvozalar qayta yugurtirilmaydi — `gate:fast` byudjeti).

**Farq:** Phase 10 uchun SC#3 (demo-forma) va SC#4 (halollik) testlari backend (`tests/integration/test_demo_request.py`) va yangi `landing-surface.test.mjs`ga ishora qiladi — `assertChainMjs`ga qo'shimcha ravishda pytest fayli mavjudligini tekshiruvchi uchinchi yordamchi (`assertChainPytest`) kerak bo'lishi mumkin (mavjud ikkitasida yo'q — yangi, lekin bir xil shaklda).

---

### `frontend/src/components/marketing/hero-scene.test.tsx` (YANGI — vitest)

**Analog:** `frontend/src/components/collect/success-choreography.test.tsx` — `matchMedia` stub chaqiruvi tasdiqlangan (`phase9-criteria.test.mjs:475`: `choreoTest.includes('stubGlobal("matchMedia"')`). Vaqt siljitish uchun `frontend/src/components/collect/collect-session.test.tsx` dagi `advanceTimersByTimeAsync(150)` naqshi (`phase9-criteria.test.mjs:482`) — hero-scene uchun `advanceTimersByTimeAsync(13500)` shakliga kengayadi.

**jsdom cheklovlari (MEROS, 09-RESEARCH, qayta tasdiqlangan):** `window.matchMedia` YO'Q → `vi.stubGlobal` bilan har testda alohida stub; `IntersectionObserver` YO'Q → qo'lda mock (`observe`/`disconnect` chaqiruvlarini sanaydigan, callback'ni qo'lda ateshlaydigan); `getBoundingClientRect()` 0 qaytaradi; `requestAnimationFrame` BOR va `vi.useFakeTimers()` uni patch qiladi.

---

## Umumiy naqshlar (Shared Patterns)

### 1. Server/klient bo'linishi (LCP qoidasi)

**Manba:** `frontend/src/app/[locale]/(auth)/login/page.tsx` (server) + `frontend/src/components/auth/login-form.tsx` (client)
**Qo'llash:** barcha marketing fayllariga — `hero.tsx`/`(marketing)/page.tsx`/`section.tsx`/kontent kartalar **Server Component**; faqat `hero-scene.tsx`, `step-line.tsx`, `reveal.tsx`, `demo-form.tsx`, (mavjud) `locale-switcher.tsx` — klient orollari (G-land-1(a) reyestri, aynan 5 fayl).

### 2. Reduced-motion — erta `return`, holat emas

**Manba:** `frontend/src/lib/motion.ts` (`prefersReducedMotion()`, 41 qator) + `frontend/src/components/collect/success-choreography.tsx:82` (`if (prefersReducedMotion()) return;`)
**Qo'llash:** `hero-scene.tsx` effektining **birinchi qatori** — Tuzoq 4: taymer chaqirilmasligi shart, `if (reduced) return` ichkarida emas.

### 3. Motion sinflari — faqat `globals.css`, faqat token orqali

**Manba:** `frontend/src/app/globals.css:226-241` (reyestr izohi) + `frontend/src/components/ui/card.tsx:27` (bare `transition` naqshi)
**Qo'llash:** `sweep`/`.landing-step-fill`/`.landing-sweep` — barchasi `globals.css` da, komponentda `duration-<son>`/`transition-[...]`/inline `animation:` **0** (G-motion-3(b), landing fayllariga ham avtomatik qo'llanadi).

### 4. Rate-limit — `_bump()` + fail-open + IP-only kesim

**Manba:** `services/core-api/app/security/ratelimit.py:241-267` (`check_bot_resolve_rate`, to'liq o'qildi)
```python
async def check_bot_resolve_rate(cache: Redis, *, telegram_user_id: int) -> None:
    key = f"{_BOT_RESOLVE_KEY}{telegram_user_id}"
    try:
        allowed = await _bump(cache, key, BOT_RESOLVE_LIMIT, BOT_RESOLVE_WINDOW_SECONDS)
    except RedisError as exc:
        log.warning("bot_resolve_rate_limit_unavailable", error=str(exc))
        return
    if not allowed:
        raise TooManyAttempts("bot_resolve")
```
**Qo'llash:** `check_demo_request_rate(cache, *, ip: str)` — **aynan shu shakl**, `_DEMO_REQUEST_KEY = "rl:demo_request:"`, `DEMO_REQUEST_LIMIT = 5`, oyna 15 daqiqa. Valkey yo'q bo'lsa **o'tkaziladi** (fail-open — uchala mavjud chaqiruv bilan bir xil qaror). Kesim **faqat IP** — telefon Valkey'ga yozilmaydi (T-07-41 qoidasi, `_BOT_RESOLVE_KEY` docstringidan meros).

### 5. `app.state` → `Depends()` dependency ko'prigi

**Manba:** `services/core-api/app/deps.py:221-227` (to'liq o'qildi)
```python
def get_cache(request: Request) -> Redis:
    return request.app.state.cache

CacheDep = Annotated["Redis", Depends(get_cache)]
```
**Qo'llash:** yangi `get_sender(request: Request) -> AlertSender: return request.app.state.sender` + `SenderDep = Annotated["AlertSender", Depends(get_sender)]` — `public.py` route'i shu orqali `AlertSender` ga yetadi.

### 6. Lifespan resurs egaligi — bir marta ochish, `finally`da yopish

**Manba:** `services/core-api/app/main.py:86-125` (to'liq o'qildi)
```python
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    ...
    await broker.startup()
    application.state.cache = cache
    try:
        yield
    finally:
        await broker.shutdown()
        await cache.aclose()
        await engine.dispose()
```
**Qo'llash:** `sender = _alert_sender(settings)` (worker.py:819-847 dagi tarjima funksiyasi **import qilinadi, nusxa olinmaydi** — RESEARCH B-4 tavsiyasi), `application.state.sender = sender`, `finally` blokiga `await sender.aclose()` qo'shiladi (`AlertSender.aclose()` — `services/alerts.py:495-498`, allaqachon no-op-xavfsiz).
**⚠ Ochiq qaror:** `_alert_sender()` bugun `worker.py` da **underscore-prefiks** bilan modul-xususiy. `main.py` uni import qilishi (`from app.worker import _alert_sender`) kodbaza konvensiyasiga ko'ra g'ayrioddiy — muqobil: funksiyani umumiy joyga (masalan `services/alerts.py` ichiga yoki yangi kichik modulga) ko'chirish. RESEARCH birinchisini tavsiya qiladi ("nusxa olinmaydi"); reja ikkalasidan birini tanlaydi.

### 7. Pydantic so'rov sxemasi + telefon normalizatsiyasi

**Manba:** `services/core-api/app/schemas.py:272-291` (`LoginRequest`, to'liq o'qildi)
```python
class LoginRequest(BaseModel):
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise ValueError(str(exc)) from exc
```
**⚠ Ehtiyot — ikki xil naqsh, reja birini tanlashi kerak:** `LoginRequest` yuqoridagi `field_validator` orqali normalizatsiya qiladi va **FastAPI'ning standart 422 shakli** (`{"detail":[{"loc":...,"msg":...}]}`) bilan yiqiladi — bitta `"invalid_phone"` satri EMAS. Aksincha, parol kuchini tekshirish (`schemas.py:229-241`, `validate_password_strength`) **ATAYIN** `field_validator` dan qochadi va docstringda sababi yozilgan: *«tekshiruv Pydantic field_validator ichida bo'lganda FastAPI 422 qaytaradi va e'lon qilingan kontraktdan chetga chiqadi»* — shuning uchun `change_password` endpointi (`auth.py:881-889`) qo'lda tekshirib `HTTPException(400, detail="weak_password")` ko'taradi. LAND-03 talab qiladigan **bitta** `422 invalid_phone` kodi ikkinchi naqshga (qo'lda `normalize_phone()` chaqirish + `HTTPException(422, detail="invalid_phone")`) yaqinroq — reja buni ochiq tanlov sifatida ko'rsin.

### 8. Backend xato-kod reyestri + frontend ko'zgu darvozasi

**Manba:** `services/core-api/app/schemas.py:645` (`MARKET_ERROR_CODES: Final[frozenset[str]]`) + `frontend/scripts/error-codes.test.mjs:187-199` (ko'zgu tekshiruvi)
**Qo'llash:** `DEMO_ERROR_CODES: Final[frozenset[str]] = frozenset({"rate_limited", "invalid_phone", "validation_error", "delivery_failed"})` — `schemas.py` ichida, yangi `DemoRequestPayload`/`DemoRequestResponse` klasslari yoniga. `error-codes.test.mjs` ga mos ko'zgu bloki qo'shiladi (RESEARCH "Variant A" tavsiyasi).

### 9. Tenant-chegaradan istisno + sabab satri

**Manba:** `tests/tenancy/test_cross_tenant.py:270-333` (`EXEMPT_ROUTES`, to'liq o'qildi)
```python
EXEMPT_ROUTES: dict[str, str] = {
    ...
    "/api/v1/me": "global — profil (ism, til) bozorga tegishli emas va bozorsiz ishlaydi (D-13)",
    ...
}
```
**Qo'llash:** `"/api/v1/public/demo-requests": "global — anonim marketing so'rovi, tenant konteksti yo'q va DB'ga yozilmaydi (10-UI-SPEC §12.5)"`. **MAJBURIY qo'shimcha ish** (docstring, 354-361-qator): istisno marshrutni matritsadan **to'liq** chiqaradi, ya'ni tokensiz/buzilgan-token testlari HAM qamrovdan tushadi — shuning uchun `tests/integration/test_demo_request.py` o'sha qamrovni **mustaqil tiklashi** shart (7 bandli integratsiya testi, `/internal/self-check` presedenti).

---

## Analog topilmagan fayllar

Kodbazada yaqin moslik yo'q — RESEARCH'ning o'z kod namunalaridan yoki Next.js rasmiy hujjatlaridan foydalaniladi:

| Fayl | Rol | Data-oqim | Sabab |
|---|---|---|---|
| `frontend/src/app/sitemap.ts` | config (route) | batch | `find src/app -name "sitemap*"` → 0 natija [L-24, O'LCHANDI]. Next 16 rasmiy `sitemap.md` namunasi RESEARCH'da CITED — ishlatiladi. |
| `frontend/src/app/robots.ts` | config (route) | batch | Xuddi shu — 0 natija. Next 16 `robots.md` namunasi CITED. |
| `frontend/src/components/marketing/reveal.tsx` (IntersectionObserver o'ramasi) | component (client) | event-driven | `IntersectionObserver` kodbazada **hech qayerda** ishlatilmagan (grep: 0 natija). Faqat `matchMedia` bir martalik o'qish naqshi (`lib/motion.ts`) qisman ilhom beradi. |
| Honeypot + dwell-time anti-spam | component (client) | event-driven | Kodbazada hech qanday anti-spam mexanizmi yo'q — bu domenda birinchi marta. |
| `frontend/src/components/marketing/demo-form.test.tsx` | test (vitest) | batch | `login-form.test.tsx` **mavjud emas** (`find` → yo'q). React Testing Library umumiy konvensiyasi (`fireEvent`, `@testing-library/react`) boshqa domenlarda (`blind-session.test.tsx`) tasdiqlangan, lekin forma-maxsus vitest analogi yo'q. |
| `services/core-api/app/api/v1/public.py` (butun yangi router fayli) | controller | request-response | Backend'da **hech qanday anonim marshrut yo'q** (L-25, 26 modul skanerlandi, 0 natija). `auth.py::login()` + `self_check.py` ikkalasi ham qisman — biri auth-bootstrap (baribir DB yozadi), ikkinchisi DB'ga umuman tegmaydi va OpenAPI'dan yashirin. Yangi fayl ikkalasining eng yaxshi qismini birlashtiradi. |

---

## Metadata

**Analog qidiruv qamrovi:** `frontend/src/app/`, `frontend/src/components/`, `frontend/src/lib/`, `frontend/scripts/`, `frontend/messages/`, `services/core-api/app/`, `tests/tenancy/`, `tests/integration/`, `packages/sbozor-core/`
**Fayllar skanerlandi:** ~45 (to'liq yoki qisman o'qildi) + Glob/Grep bilan ~15 qo'shimcha joylashuv tasdiqlandi
**Naqsh ajratish sanasi:** 2026-08-17
