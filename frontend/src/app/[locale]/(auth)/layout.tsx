import { Instrument_Sans } from "next/font/google";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import {
  getMessages,
  getTimeZone,
  getTranslations,
  setRequestLocale,
} from "next-intl/server";

import { AppProviders } from "@/components/shell/app-providers";
import { routing } from "@/i18n/routing";
import { cn } from "@/lib/cn";

/*
 * Landing bilan BIR XIL shrift (dizayn v2): kirish — landing'dan keladigan
 * eshik, boshqa garnitura ko'rsatilsa ikki xil mahsulot taassuroti tug'ilardi.
 * ⛔ `latin` + `latin-ext` quyi to'plamlari: kirill YO'Q (Google bu
 * garniturada kirill bermaydi) — kirill matn tizim shriftiga tushadi va bu
 * ONGLI: yolg'on «qo'llab-quvvatlanadi» taassuroti berilmaydi.
 */
const instrumentSans = Instrument_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "600", "700"],
});

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
  // Request-config'dagi Asia/Tashkent (FOUND-05) — klient provayder uni
  // o'zi meros olmaydi, oshkora uzatiladi (app-providers.tsx sarlavhasi).
  const timeZone = await getTimeZone();
  const tCommon = await getTranslations("common");

  return (
    <AppProviders locale={locale} messages={messages} timeZone={timeZone}>
      {/* Tungi indigo sahna — landing bilan bir xil (dizayn v2): kirish
          landing'ning davomi bo'lib ko'rinadi, yangi rang reyestri ochilmaydi.
          ⛔⛔ Qorong'i qamrov FAQAT fon qatlamida va so'zbelgida: kontent
          ustiga qo'yilsa karta ham qorayardi — `data-theme="light"` uni
          qaytara OLMAYDI, chunki yorug' tema bazaviy holat va uning
          `[data-theme]` bloki umuman yo'q (o'lchandi). */}
      <div
        className={cn(
          instrumentSans.className,
          "relative flex flex-1 flex-col items-center justify-center gap-6 p-6",
        )}
      >
        <div
          aria-hidden="true"
          className="landing-night absolute inset-0"
          data-theme="dark"
        />
        {/* So'zbelgi — header/footer bilan bir xil shakl (S + aksent). */}
        <div className="relative" data-theme="dark">
          <p className="text-lg font-bold tracking-[0.08em] text-text">
            {tCommon("appName").slice(0, 1)}
            <span className="text-accent-text">
              {tCommon("appName").slice(1)}
            </span>
          </p>
        </div>
        <main className="relative w-full max-w-md">{children}</main>
      </div>
    </AppProviders>
  );
}
