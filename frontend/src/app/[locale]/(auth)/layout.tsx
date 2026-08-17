import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";

import { AppProviders } from "@/components/shell/app-providers";
import { routing } from "@/i18n/routing";

/*
 * Kirish oqimining qobig'i: markazlashtirilgan tor ustun, bitta karta.
 * Apple-uslub (topshiriq §7) — bitta aniq harakat, ortiqcha bezaksiz.
 *
 * 10-03: provayderlar ildizdan shu yerga tushdi — Server Component bo'lib
 * qoladi va `AppProviders` (klient) ni render qiladi (qonuniy: RESEARCH
 * §4.3, VERIFIED). ⛔ `messages`/`locale` OSHKORA uzatiladi: berilmasa
 * klient provayder throw qiladi, server varianti esa TO'LIQ katalogni
 * jimgina meros olardi — ikkala holat ham kontraktni buzadi.
 *
 * DIQQAT: bu yerda hech qanday matn yo'q — barchasi sahifalarda
 * `next-intl` orqali keladi.
 */
export default async function AuthLayout({
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
  // Statik renderni yoqadi — segmentlar mustaqil render bo'ladi.
  setRequestLocale(locale);

  const messages = await getMessages();

  return (
    <AppProviders locale={locale} messages={messages}>
      <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 p-6">
        {children}
      </main>
    </AppProviders>
  );
}
