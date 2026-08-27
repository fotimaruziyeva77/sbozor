import { Instrument_Sans } from "next/font/google";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import {
  getMessages,
  getTimeZone,
  getTranslations,
  setRequestLocale,
} from "next-intl/server";

import { LoginBackdrop } from "@/components/auth/login-backdrop";
import { MarketingLocaleSwitcher } from "@/components/marketing/locale-switcher";
import { AppProviders } from "@/components/shell/app-providers";
import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { cn } from "@/lib/cn";

/*
 * Kirish oqimining qobig'i — «Sbozor Login» dizayni bo'yicha tungi sahna.
 *
 * 10-03: provayderlar ildizdan shu yerga tushdi — Server Component bo'lib
 * qoladi va `AppProviders` (klient) ni render qiladi (qonuniy: RESEARCH
 * §4.3, VERIFIED). ⛔ `messages`/`locale` OSHKORA uzatiladi: berilmasa
 * klient provayder throw qiladi, server varianti esa TO'LIQ katalogni
 * jimgina meros olardi — ikkala holat ham kontraktni buzadi.
 *
 * ⛔⛔ QORONG'I QAMROV FAQAT FON QATLAMIDA emas — bu yerda BUTUN sahna
 * qorong'i (dizayn: karta ham shishasimon quyuq panel), shuning uchun
 * `data-theme="dark"` tashqi konteynerda turadi. Yorug' orol kerak bo'lsa
 * (masalan boshqa auth sahifasining oq kartasi) — u fon qatlami naqshiga
 * o'tkaziladi: `data-theme="light"` HECH NIMA qilmaydi (yorug' tema —
 * bazaviy holat, uning CSS bloki yo'q; o'lchandi).
 */
const instrumentSans = Instrument_Sans({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "600", "700"],
});

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
  const t = await getTranslations("auth");
  const tCommon = await getTranslations("common");

  return (
    <AppProviders locale={locale} messages={messages} timeZone={timeZone}>
      <div
        className={cn(
          instrumentSans.className,
          "login-scene relative flex min-h-svh flex-col overflow-hidden",
        )}
        data-theme="dark"
      >
        <LoginBackdrop />
        <div aria-hidden="true" className="login-veil absolute inset-0" />

        <div className="landing-shell relative z-[2] mx-auto flex w-full flex-1 flex-col px-6 pt-7 pb-16">
          <header className="mb-14 flex items-center justify-between gap-4">
            {/* So'zbelgi landing bilan bir xil shakl (S + aksent). */}
            <Link
              className="inline-flex min-h-11 items-center text-lg font-bold tracking-[0.08em] text-text"
              href="/"
            >
              {tCommon("appName").slice(0, 1)}
              <span className="text-accent-text">
                {tCommon("appName").slice(1)}
              </span>
            </Link>
            <div className="flex items-center gap-4.5">
              <MarketingLocaleSwitcher />
              <Link
                className="inline-flex min-h-11 items-center text-sm font-semibold text-text-muted hover:text-text"
                href="/"
              >
                {t("login.backToSite")}
              </Link>
            </div>
          </header>
          <main className="flex flex-1 items-center">{children}</main>
        </div>
      </div>
    </AppProviders>
  );
}
