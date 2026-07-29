import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import {
  getMessages,
  getTranslations,
  setRequestLocale,
} from "next-intl/server";
import { Toaster } from "sonner";

import { routing } from "@/i18n/routing";
import { AuthProvider } from "@/lib/auth-store";
import { QueryProvider } from "@/lib/query-provider";

import "../globals.css";

type LocaleParams = { locale: string };

/*
 * Bu — ilovaning ILDIZ layout'i (`app/layout.tsx` mavjud emas): next-intl
 * strukturasida `<html>` locale segmentida render bo'ladi, chunki `lang`
 * atributi locale'ga bog'liq.
 */

export function generateStaticParams() {
  // `routing.locales` — TO'LIQ locale qiymatlari (`uz-Latn`), URL prefiksi emas.
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<LocaleParams>;
}): Promise<Metadata> {
  const { locale } = await params;
  const resolved = hasLocale(routing.locales, locale)
    ? locale
    : routing.defaultLocale;
  const t = await getTranslations({ locale: resolved, namespace: "common" });

  return {
    title: t("appName"),
    description: t("appTagline"),
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<LocaleParams>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  // Statik renderni yoqadi — busiz har sahifa dinamik bo'lib qoladi.
  setRequestLocale(locale);

  const messages = await getMessages();

  return (
    <html lang={locale} className="h-full">
      <body className="flex min-h-full flex-col">
        {/*
          Provayder tartibi: i18n -> server holati keshi -> sessiya.
          `AuthProvider` eng ichkarida, chunki sessiya tiklash `apiFetch` ga
          tayanadi va u `QueryProvider` bilan bir xil daraxtda bo'lishi kerak.
        */}
        <NextIntlClientProvider messages={messages}>
          <QueryProvider>
            <AuthProvider>
              {children}
              <Toaster position="top-center" richColors />
            </AuthProvider>
          </QueryProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
