import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";

import { AppGuard } from "@/components/shell/app-guard";
import { AppProviders } from "@/components/shell/app-providers";
import { routing } from "@/i18n/routing";

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

  return (
    <AppProviders locale={locale} messages={messages}>
      <AppGuard>{children}</AppGuard>
    </AppProviders>
  );
}
