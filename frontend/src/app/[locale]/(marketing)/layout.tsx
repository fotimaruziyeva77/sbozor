import { notFound } from "next/navigation";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";

import { routing } from "@/i18n/routing";

/*
 * `(marketing)` guruhining layout'i — anonim yuzaning provayder chegarasi
 * (10-03, UI-SPEC §4.3, G-land-1(c)).
 *
 * ⛔ FAQAT `NextIntlClientProvider` va FAQAT IKKI fazoviy nom: `common` +
 * `landing`. Boshqa provayder (URL holati, server keshi, sessiya, toast)
 * QO'SHILMAYDI — anonim tashrifchida sessiya ham, so'rov holati ham yo'q,
 * ularning JS grafi esa o'lchangan ~21 KB gzip (10-RESEARCH B-2 jadvali).
 *
 * ⛔ Toraytirish QO'LDA obyekt qurish bilan: next-intl 4.13.4 da o'rnatilgan
 * `pick` YO'Q (tip VERIFIED). Va `messages` OSHKORA beriladi — berilmasa
 * server varianti so'rov kontekstidan TO'LIQ 1373 kalitli katalogni meros
 * oladi va toraytirish jimgina bekor bo'lardi.
 *
 * ⛔ Klient kontrakti (Tuzoq 1): landing komponentlaridagi
 * `useTranslations`/`getTranslations` argumentlari shu IKKI nomdan chetga
 * chiqmasin. Chetga chiqsa server render O'TADI (server kontekstda to'liq
 * katalog bor), klient esa `MISSING_MESSAGE` bilan faqat brauzerda,
 * hidratatsiyadan keyin yiqiladi. G-land-1(c) (10-07) buni ikki tomonlama
 * o'lchaydi.
 */
export default async function MarketingLayout({
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
  // ⛔ BIRINCHI next-intl chaqiruvi — busiz sahifa dinamik bo'lib qoladi
  // (SSG sharti); `hasLocale` tipni ham toraytiradi (`setRequestLocale`
  // faqat ro'yxatdagi locale'ni oladi).
  setRequestLocale(locale);

  // Server tomonda TO'LIQ katalog — bepul; klientga faqat ikki nom tushadi.
  const messages = await getMessages();

  return (
    <NextIntlClientProvider
      messages={{ common: messages.common, landing: messages.landing }}
    >
      {children}
    </NextIntlClientProvider>
  );
}
