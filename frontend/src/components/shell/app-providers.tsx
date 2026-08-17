"use client";

import type { ComponentProps } from "react";
import type { Locale } from "next-intl";
import { NextIntlClientProvider } from "next-intl";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import { Toaster } from "sonner";

import { AuthProvider } from "@/lib/auth-store";
import { QueryProvider } from "@/lib/query-provider";

/*
 * Beshala provayderning YAGONA ta'rifi (10-03, UI-SPEC §4.3).
 *
 * Ildiz layoutdan AYNAN ko'chirilgan tana: `(app)` va `(auth)` guruhlari shu
 * bitta komponentni import qiladi — nusxa YO'Q. `(marketing)` esa uni
 * ISHLATMAYDI: anonim sahifa faqat toraytirilgan `NextIntlClientProvider`
 * oladi va rq/nuqs/sonner/sessiya grafini yuklamaydi (o'lchangan sabab:
 * 10-RESEARCH B-2 — provayder chunki ~21 KB gzip).
 *
 * Provayder tartibi: i18n -> URL holati -> server holati keshi -> sessiya.
 * `AuthProvider` eng ichkarida, chunki sessiya tiklash `apiFetch` ga
 * tayanadi va u `QueryProvider` bilan bir xil daraxtda bo'lishi kerak.
 *
 * `NuqsAdapter` — URL qidiruv parametrlarini holat sifatida o'qiydigan
 * komponentlar uchun (audit filtrlari). U marshrutlashga bog'liq,
 * shuning uchun keshdan ham, sessiyadan ham TASHQARIDA turadi.
 *
 * `Toaster` `AuthProvider` ICHIDA, `{children}` YONIDA — joyi ildiz
 * layoutdagi bilan AYNAN bir xil (tartib muzokarasiz).
 *
 * ⛔ `locale` va `messages` OSHKORA uzatiladi: bu fayl klient moduli va
 * klient kontekstidagi `NextIntlClientProvider` server konfiguratsiyasini
 * o'qiy olmaydi — `locale`siz u shartnoma bo'yicha throw qiladi
 * (shared/NextIntlClientProvider.js:9-10, next-intl 4.13.4 da o'lchandi).
 * Ya'ni ikkala qiymat ham server-layout chaqiruvchidan keladi.
 */

type Messages = ComponentProps<typeof NextIntlClientProvider>["messages"];

export function AppProviders({
  locale,
  messages,
  children,
}: {
  locale: Locale;
  messages: Messages;
  children: React.ReactNode;
}) {
  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
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
