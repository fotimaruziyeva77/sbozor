import { JetBrains_Mono, Manrope } from "next/font/google";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getMessages, getTimeZone, setRequestLocale } from "next-intl/server";

import { AppGuard } from "@/components/shell/app-guard";
import { AppProviders } from "@/components/shell/app-providers";
import { routing } from "@/i18n/routing";
import { cn } from "@/lib/cn";

/*
 * Ilova shrifti (2026-08-25, foydalanuvchi: «font family yaxshila»).
 *
 * ⛔ `next/font` — build paytida yuklanadi va o'zi self-host qiladi:
 *    runtime'da tashqi so'rov NOL (auth/marketing'dagi Instrument Sans
 *    bilan bir xil, tekshirilgan naqsh).
 *
 * ⛔ KIRILL SUBSETI MAJBURIY: interfeys uz-Cyrl va ru da ham yashaydi —
 *    Instrument Sans (faqat lotin) shu sababdan APP ichida ISHLATILMAYDI.
 *
 * ⚠ Og'irliklar AYNAN 500/700: `globals.css` dagi rol shkalasi
 *   (`--font-weight-normal: 500`, `--font-weight-semibold: 700`) bilan
 *   bir manba — boshqa og'irlik yuklash o'lik kilobayt bo'lardi.
 *
 * `variable:` rejimi ATAYIN (`className` emas): `globals.css` dagi
 * `--font-sans`/`--font-mono` ro'yxatlari bu o'zgaruvchilarni BIRINCHI
 * o'ringa oladi va app'dan tashqarida (marketing/auth) ular bo'sh qolib,
 * zanjir keyingi shriftga o'tadi.
 */
const appSans = Manrope({
  subsets: ["latin", "latin-ext", "cyrillic"],
  weight: ["500", "700"],
  variable: "--font-app-sans",
});

const appMono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  weight: ["500", "700"],
  variable: "--font-app-mono",
});

/*
 * Himoyalangan guruhning layout'i (10-03 dan keyin — YUPQA server qobiq).
 *
 * Sobiq klient tanasi (sessiya tiklash, redirect shoxlari, skelet) AYNAN
 * ko'chirilgan holda `@/components/shell/app-guard.tsx` da yashaydi.
 * Bu fayl endi faqat ikki ishni qiladi:
 *   1. TO'LIQ matn katalogini oladi (`getMessages`) — app interfeysi barcha
 *      fazoviy nomlarni ishlatadi, toraytirish faqat `(marketing)` uchun.
 *   2. `AppProviders` ni o'raydi va guardni provayderlar ICHIDA render
 *      qiladi. ⛔ Tartib MUZOKARASIZ (Tuzoq 3): `AppGuard` hook'lari
 *      (`useAuthStore`, `useTranslations`) provayder daraxtidan TASHQARIDA
 *      chaqirilsa SSG prerender `throw` bilan yiqiladi — aynan shu sabab
 *      guard va layout IKKI komponentga ajratilgan.
 *
 * NEGA SERVER KOMPONENT: `messages`/`locale` klient tomonda olinolmaydi —
 * klient kontekstidagi `NextIntlClientProvider` `locale`siz throw qiladi
 * (next-intl 4.13.4 da o'lchandi), katalogni klientga import qilish esa
 * uchala tilni bundle'ga qo'shib yuborardi. Server qobiq ikkalasini so'rov
 * kontekstidan bepul oladi.
 */
export default async function AppLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  // Statik renderni yoqadi — segmentlar mustaqil render bo'ladi, ildiz
  // layoutdagi chaqiruv BU segmentni qoplamaydi.
  setRequestLocale(locale);

  const messages = await getMessages();
  // Request-config'dagi Asia/Tashkent (FOUND-05) — klient provayder uni
  // o'zi meros olmaydi, oshkora uzatiladi (app-providers.tsx sarlavhasi).
  const timeZone = await getTimeZone();

  return (
    <AppProviders locale={locale} messages={messages} timeZone={timeZone}>
      {/* Shrift o'zgaruvchilari shu o'ramdan pastga meros bo'ladi. */}
      <div className={cn("contents app-fonts", appSans.variable, appMono.variable)}>
        <AppGuard>{children}</AppGuard>
      </div>
    </AppProviders>
  );
}
