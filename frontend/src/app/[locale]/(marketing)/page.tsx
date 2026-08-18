import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { DemoForm } from "@/components/marketing/demo-form";
import { Faq } from "@/components/marketing/faq";
import { Footer } from "@/components/marketing/footer";
import { Header } from "@/components/marketing/header";
import { Hero } from "@/components/marketing/hero";
import { LossCalc } from "@/components/marketing/loss-calc";
import { PainCards } from "@/components/marketing/pain-cards";
import { Pilot } from "@/components/marketing/pilot";
import { Proof } from "@/components/marketing/proof";
import { Reveal } from "@/components/marketing/reveal";
import { RoleCards } from "@/components/marketing/role-cards";
import { Section } from "@/components/marketing/section";
import { StepLine } from "@/components/marketing/step-line";
import { TrustBlock } from "@/components/marketing/trust-block";
import { Card, CardContent } from "@/components/ui/card";
import { routing } from "@/i18n/routing";
import { cn } from "@/lib/cn";

/*
 * Landing yakuniy kompozitsiyasi (10-07, ROADMAP SC#1/#2/#4/#5) — sobiq
 * 10-03 qobig'ining to'liq shakli. Server Component; klient direktivasi bu
 * faylda 0 marta (G-land-1 (10-UI-SPEC) reyestri faqat besh orolni biladi).
 *
 * ⛔ SSG shartlari o'zgarmagan (10-03 [QAROR]): sessiyaga qarab redirect
 * YO'Q; `cookies()` / `headers()` / `searchParams` ISHLATILMAYDI;
 * `setRequestLocale` — BIRINCHI next-intl chaqiruvi. Ildiz HAR DOIM landing.
 *
 * ⛔ Bloklar tartibi — §9.1 ning YOPIQ ro'yxati (11 blok): Header · hero ·
 * og'riq · 3-qadam · ⭐ dalil · rol-kartalar · ishonch · pilot · FAQ ·
 * CTA takrori + demo-forma · Footer. Boshqa blok YO'Q: narx kalkulyatori,
 * ro'yxatdan o'tish, blog, mijozlar logotiplari — hech biri (brief §1).
 *
 * ⛔ Sarlavha ierarxiyasi (§15.11): sahifada AYNAN BITTA `h1` (hero ichida);
 * har seksiya bloki O'Z `h2` sini chizadi — shuning uchun `<Section>` bu
 * faylda `title` PROP'SIZ (aks holda h2 ikkilanadi) va trust-block uchun
 * `id` SIZ (anchor blokning o'zida — 10-06 shartnomasi).
 *
 * ⛔ Vertikal ritm FAQAT `<Section>` orqali — seksiya bo'shliq qiymatlari
 * bu faylda 0 marta (G-land-5(c) (10-UI-SPEC), yagona uy section.tsx).
 * Hero-o'lcham utilitasi ham bu faylda yozilmaydi (G-land-5(a) quli).
 *
 * ⛔⛔ JSON-LD — IKKI TUR, BOSHQASI YO'Q (§14.3, T-10-13):
 * `Organization` (brend, logotip, aloqa) va `FAQPage` (§13.7 ning 5 savoli).
 * Reyting/sharh sinflari TAQIQ (K-7) — ular soxta ijtimoiy isbot bo'lardi.
 * Matn TARJIMA KATALOGIDAN: FAQ savol-javoblari komponentda ham, bu yerda
 * ham literal yozilmaydi — bitta manba, ikkita chiqish (G-land-4(d), T-10-14).
 */

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://sbozor.uz";

/**
 * FAQ indekslari — `faq.tsx` dagi FAQ_ITEMS bilan AYNI ro'yxat. Bu matn
 * manbai EMAS (matn `landing.faq.*` da) — faqat strukturaviy sanoq.
 */
const FAQ_JSONLD_ITEMS = [1, 2, 3, 4, 5] as const;

/**
 * OG locale — `ll_CC` shakli (Open Graph protokoli yozuv subtag'ini
 * bilmaydi). Ikkala o'zbek sahifasi ham `uz_UZ` — til to'g'ri, yozuv farqini
 * esa `hreflang` alternates ko'taradi.
 */
const OG_LOCALES: Record<string, string> = {
  "uz-Latn": "uz_UZ",
  "uz-Cyrl": "uz_UZ",
  ru: "ru_RU",
};

/**
 * URL prefiksi — `i18n/routing.ts` dan HOSILA (maxfiylik sahifasi bilan bir
 * xil funksiya): custom prefiks bo'lmagan locale (ru) standart `/{locale}`.
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
  const tCommon = await getTranslations({
    locale: resolved,
    namespace: "common",
  });

  return {
    metadataBase: new URL(SITE_URL),
    // ⛔ Brend VA va'da bitta title'da (§14.1) — raqibning faqat-brend
    // sarlavhasi xatosi bu yerda arzon g'alaba.
    title: t("meta.title"),
    description: t("meta.description"),
    alternates: {
      canonical: urlPrefix(resolved),
      // ⛔ Uchala locale ham hreflang'da — qidiruv har tilni o'z sahifasiga
      // yo'naltiradi (kirill auditoriyasi lotin sahifasiga tushmasin).
      languages: Object.fromEntries(
        routing.locales.map((entry) => [entry, urlPrefix(entry)]),
      ),
    },
    openGraph: {
      title: t("meta.title"),
      description: t("meta.description"),
      url: urlPrefix(resolved),
      siteName: tCommon("appName"),
      locale: OG_LOCALES[resolved] ?? resolved,
      type: "website",
      images: [
        {
          // Rasm TIL-NEYTRAL statik PNG (§14.1 [QAROR] — `ImageResponse`
          // emas); `alt` esa locale bo'yicha tarjima qilinadi.
          url: "/og/sbozor-og.png",
          width: 1200,
          height: 630,
          alt: t("meta.ogAlt"),
        },
      ],
    },
    twitter: { card: "summary_large_image" },
  };
}

/**
 * JSON-LD skript bloki — Next'ning RASMIY xavfsizlik naqshi (T-10-08).
 *
 * `.replace` dekorativ emas: matn tarjima katalogidan keladi va satrda
 * yopuvchi skript-teg ketma-ketligi paydo bo'lsa, brauzer skript blokini
 * erta yopib qolganini HTML sifatida o'qiy boshlardi. `<` ni `<`
 * escape'iga almashtirish shu sinfni butunlay yopadi — xavf past, lekin
 * nolga teng emas, rasmiy naqsh esa arzon.
 */
function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(data).replace(/</g, "\\u003c"),
      }}
      type="application/ld+json"
    />
  );
}

export default async function MarketingRootPage({
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
  const tCommon = await getTranslations("common");
  // O-06: aloqa kanali faqat env berilganda — yolg'on kanal ochilmaydi.
  const contactPhone = process.env.NEXT_PUBLIC_CONTACT_PHONE;
  const contactTelegram = process.env.NEXT_PUBLIC_CONTACT_TELEGRAM;

  const organizationJsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: tCommon("appName"),
    url: SITE_URL,
    logo: `${SITE_URL}/og/sbozor-og.png`,
    ...(contactPhone
      ? {
          contactPoint: [
            {
              "@type": "ContactPoint",
              contactType: "sales",
              telephone: contactPhone,
            },
          ],
        }
      : {}),
  };

  const faqJsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: FAQ_JSONLD_ITEMS.map((n) => ({
      "@type": "Question",
      name: t(`faq.q${n}`),
      acceptedAnswer: { "@type": "Answer", text: t(`faq.a${n}`) },
    })),
  };

  return (
    <>
      <JsonLd data={organizationJsonLd} />
      <JsonLd data={faqJsonLd} />
      {/* ⛔ Header hero bilan BIR XIL tungi qamrovda (dizayn v2): oq tasma
          indigo ustida qolsa birinchi ekran ikkiga bo'linib ko'rinardi.
          `.landing-night-top` — gradientning BOSHLANISH rangi, shuning
          uchun header/hero chegarasida chok ko'rinmaydi. */}
      <div className="landing-night-top" data-theme="dark">
        <Header />
      </div>
      <main className="flex-1" id="kontent">
        {/* 1 · Hero — tungi bozor atmosferasi: dark token-qamrov + nur
            (yangi rang reyestri OCHILMAYDI — mavjud dark scope ishlatiladi) */}
        <Section className="landing-night pt-6" data-theme="dark">
          <Hero />
        </Section>
        {/* 2 · Og'riq — 3 karta (v2: MUAMMO kicker) */}
        <Section className="bg-surface-muted">
          <PainCards />
        </Section>
        {/* 2.5 · v2 YANGI: yo'qotish kalkulyatori (HISOB-KITOB) —
            foydalanuvchining O'Z taxmini, ikki disclaimer bilan */}
        <Section>
          <LossCalc />
        </Section>
        {/* 3 · Qanday ishlaydi — 3 qadam [K-3] */}
        <Section className="bg-surface-muted">
          <StepLine />
        </Section>
        {/* 4 · ⭐ Bosh dalil — v2: och ko'k gradient banner */}
        <Section>
          <Proof />
        </Section>
        {/* 5 · Rol-kartalar — skrinshotsiz (§9.3) */}
        <Section className="bg-surface-muted">
          <RoleCards />
        </Section>
        {/* 6 · Ishonch bloki — v2: yorug' 4 ustun (10-06 shartnomasi) */}
        <Section>
          <TrustBlock />
        </Section>
        {/* 7 · Pilot holati — raqamsiz [K-7]; v2: halollik kartasi bilan */}
        <Section className="bg-surface-muted">
          <Pilot />
        </Section>
        {/* 8 · FAQ — native details/summary (§15.8) */}
        <Section>
          <Faq />
        </Section>
        {/* 9 · CTA takrori + demo-forma — v2: indigo tunda oq karta */}
        <Section className="landing-night" id="demo">
          {/* ⛔ Qorong'i qamrov SEKSIYAGA qo'yilmaydi: ichidagi oq karta
              qorayardi va `data-theme="light"` uni qaytara olmaydi (yorug'
              tema — bazaviy holat, uning bloki yo'q). Fon sinfning o'zida. */}
          <Reveal>
            {/* v2: indigo tun ichida YORUG' karta — ichki light-qamrov. */}
            <Card className="landing-demo-card mx-auto w-full max-w-2xl">
              <CardContent className="flex flex-col gap-6 pt-5">
                <div className="flex flex-col gap-2">
                  <h2 className="text-2xl font-semibold tracking-tight">
                    {t("form.title")}
                  </h2>
                  <p className="max-w-[66ch] text-sm leading-relaxed text-text-muted">
                    {t("form.subtitle")}
                  </p>
                </div>
                <DemoForm />
              </CardContent>
            </Card>
          </Reveal>
          {/* v2: forma ostida TIRIK odam kanali — forma to'ldirishni
              istamagan mijoz uchun. Telefon/Telegram `.env` dan; berilmasa
              karta UMUMAN chizilmaydi (yolg'on kanal ochilmaydi — O-06). */}
          {contactPhone || contactTelegram ? (
            <Reveal delayIndex={1}>
              <div
                className="mx-auto mt-7 flex w-full max-w-2xl flex-wrap items-center gap-5 rounded-2xl border border-border bg-surface-muted px-7 py-6"
                data-theme="dark"
              >
                <span
                  aria-hidden="true"
                  className="flex size-14 shrink-0 items-center justify-center rounded-full border border-border bg-surface text-lg font-bold text-accent-text"
                >
                  {tCommon("appName").slice(0, 2)}
                </span>
                <div className="min-w-[12.5rem] flex-1">
                  <p className="text-xs text-text-muted">
                    {t("contact.label")}
                  </p>
                  {contactPhone ? (
                    <a
                      className="mt-1 inline-flex text-sm font-semibold text-text hover:text-accent-text"
                      data-numeric
                      href={`tel:${contactPhone}`}
                    >
                      {contactPhone}
                    </a>
                  ) : null}
                  <p className="mt-0.5 text-xs text-text-muted">
                    {t("contact.hours")}
                  </p>
                </div>
                {contactTelegram ? (
                  <a
                    className={cn(
                      "inline-flex min-h-11 items-center justify-center rounded-lg",
                      "border border-border px-5 text-sm font-semibold text-text",
                      "hover:border-accent hover:text-accent-text",
                    )}
                    href={contactTelegram}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {t("contact.telegram")}
                  </a>
                ) : null}
              </div>
            </Reveal>
          ) : null}
        </Section>
      </main>
      <Footer />
    </>
  );
}
