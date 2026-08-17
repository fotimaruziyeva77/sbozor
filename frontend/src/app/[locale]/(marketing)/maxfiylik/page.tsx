import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Footer } from "@/components/marketing/footer";
import { Header } from "@/components/marketing/header";
import { Section } from "@/components/marketing/section";
import { routing } from "@/i18n/routing";

/*
 * Maxfiylik siyosati — MAJBURIY sahifa (K-8: CCTV shaxsiy ma'lumot qonuni
 * ostida), uchala tilda SSG. Skelet `(marketing)/page.tsx` bilan bir xil:
 * hasLocale -> notFound -> setRequestLocale -> getTranslations("landing").
 *
 * Yetti bo'lim — §11.3 YOPIQ reyestri (matn `landing.privacy.*` dan):
 * kim yig'adi · kamera tasvirlari (90 kun -> siqilgan 1 yil) · demo-forma
 * (DB'da SAQLANMAYDI + T-10-07 OSHKORA: Telegram serverlari O'zR
 * chegarasidan tashqarida, u yerga FAQAT matn ketadi) · sotuvchi
 * ma'lumotlari · uzatish (uchinchi tomon YO'Q) · huquqlar · cookie.
 *
 * ⛔ Cookie-banner QO'YILMAYDI [QAROR]: landing marketing/analitika
 * cookie'si o'rnatmaydi — banner yolg'on taassurot berardi («bizda
 * kuzatuv bor») va LCP yo'liga overlay qo'shardi. Tetigi: analitika
 * qo'shilsa (§17.2 da rad etilgan) — banner o'sha kunda majburiy.
 *
 * ⛔ `text-hero` bu sahifada YO'Q (u hero.tsx ning yagona uyi, G-land-5(a));
 * sarlavhalar `text-2xl`, proza `text-sm` + `max-w-[66ch]` (§7.3).
 */

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://sbozor.uz";

/** Bo'limlar reyestri — tarjima katalogidagi `privacy.s1..s7` ga teng. */
const PRIVACY_SECTIONS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7"] as const;

/**
 * URL prefiksi — `i18n/routing.ts` dan HOSILA (qo'lda takrorlanmaydi):
 * custom prefiks bo'lmagan locale (ru) standart `/{locale}` oladi —
 * next-intl'ning o'z qoidasi bilan bir xil.
 */
function urlPrefix(locale: string): string {
  // `localePrefix` ittifoqida `prefixes`siz rejimlar ham bor — `in` sharti.
  const config = routing.localePrefix;
  const prefixes: Partial<Record<string, string>> =
    typeof config === "object" && "prefixes" in config
      ? (config.prefixes ?? {})
      : {};
  return prefixes[locale] ?? `/${locale}`;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const resolved = hasLocale(routing.locales, locale)
    ? locale
    : routing.defaultLocale;
  const t = await getTranslations({ locale: resolved, namespace: "landing" });

  return {
    metadataBase: new URL(SITE_URL),
    title: t("privacy.title"),
    description: t("privacy.intro"),
    // Bu sahifa INDEKSLANADI (robots.ts ham ruxsat beradi) — huquqiy
    // sahifaning topilishi ishonch qatlamining bir qismi.
    robots: { index: true },
    alternates: {
      canonical: `${urlPrefix(resolved)}/maxfiylik`,
      languages: Object.fromEntries(
        routing.locales.map((entry) => [
          entry,
          `${urlPrefix(entry)}/maxfiylik`,
        ]),
      ),
    },
  };
}

export default async function PrivacyPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  // Statik renderni yoqadi — busiz sahifa dinamik bo'lib qoladi.
  setRequestLocale(locale);

  const t = await getTranslations("landing");

  return (
    <>
      <Header />
      <main className="flex-1" id="kontent">
        <Section>
          {/* Sahifada AYNAN bitta <h1> (§15.11); bo'limlar <h2>. */}
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("privacy.title")}
          </h1>
          <div className="flex max-w-[66ch] flex-col gap-8">
            <p className="text-sm leading-relaxed text-text-muted">
              {t("privacy.intro")}
            </p>
            {PRIVACY_SECTIONS.map((key) => (
              <section className="flex flex-col gap-2" key={key}>
                <h2 className="text-2xl font-semibold tracking-tight">
                  {t(`privacy.${key}.title`)}
                </h2>
                <p className="text-sm leading-relaxed text-text-muted">
                  {t(`privacy.${key}.body`)}
                </p>
              </section>
            ))}
          </div>
        </Section>
      </main>
      <Footer />
    </>
  );
}
