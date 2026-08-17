import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import {
  getMessages,
  getTranslations,
  setRequestLocale,
} from "next-intl/server";
import { NuqsAdapter } from "nuqs/adapters/next/app";
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
    /*
     * `data-theme="light"` — server HTML'ining standart temasi;
     * `suppressHydrationWarning` — pastdagi inline skript atributni React
     * gidratatsiyasidan OLDIN o'zgartirgani uchun MAJBURIY (aks holda React
     * nomuvofiqlikni «tuzatib», temani qayta light'ga qaytarardi).
     * Naqsh: next/dist/docs/01-app/02-guides/preventing-flash-before-hydration.md
     */
    <html
      lang={locale}
      className="h-full"
      data-theme="light"
      suppressHydrationWarning
    >
      <head>
        {/*
          ⛔ FOUC'ga qarshi BLOKLOVCHI skript (09-UI-SPEC §11.2): saqlangan
          tema birinchi bo'yashdan OLDIN qo'llanadi. `useEffect` YARAMASDI —
          u bo'yashdan keyin ishlaydi va oq miltillash ko'rinardi.

          ⛔ Satr STATIK va build paytida qotirilgan — foydalanuvchi
          ma'lumoti interpolatsiya QILINMAYDI (T-09-02: XSS yuzasi yo'q).
          ⛔ Reyestr validatsiyasi skript ICHIDA: `localStorage` dagi
          ixtiyoriy satr `data-theme` ga o'ta OLMAYDI (T-09-01) — faqat
          aynan "light" / "dark" / "sun".
          ⛔ `try/catch` — `localStorage` bloklangan brauzerlar uchun.
          Skript locale'ga ham, sessiyaga ham bog'liq emas — SSG buzilmaydi.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              `(function(){try{var t=localStorage.getItem("sbozor-theme");` +
              `if(t==="light"||t==="dark"||t==="sun")` +
              `document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`,
          }}
        />
      </head>
      <body className="flex min-h-full flex-col">
        {/*
          Provayder tartibi: i18n -> URL holati -> server holati keshi -> sessiya.
          `AuthProvider` eng ichkarida, chunki sessiya tiklash `apiFetch` ga
          tayanadi va u `QueryProvider` bilan bir xil daraxtda bo'lishi kerak.

          `NuqsAdapter` — URL qidiruv parametrlarini holat sifatida o'qiydigan
          komponentlar uchun (audit filtrlari). U marshrutlashga bog'liq,
          shuning uchun keshdan ham, sessiyadan ham TASHQARIDA turadi.
        */}
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
      </body>
    </html>
  );
}
