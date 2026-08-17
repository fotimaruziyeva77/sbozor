import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Footer } from "@/components/marketing/footer";
import { Header } from "@/components/marketing/header";
import { Section } from "@/components/marketing/section";
import { routing } from "@/i18n/routing";

/*
 * Anonim ildiz sahifasi (SSG) — sobiq `[locale]/page.tsx` redirect'ining
 * O'RNI (10-03, ROADMAP SC#1). ⛔ Bu fayl bilan o'sha redirect JUFT
 * almashtirildi: turli guruhlardagi ikki marshrut bir URL'ga tushsa Next 16
 * build xatosi beradi; ikkalasi ham yo'q bo'lsa `/uz` 404 bo'lardi
 * (G-land-1(d) shu juftlikni qulflaydi).
 *
 * ⛔ SESSIYAGA QARAB REDIRECT YO'Q (SPEC §4.1 [QAROR]): sessiya tekshiruvi
 * sahifani dinamik qilib SSG'ni (SC#5 asosini) yo'q qilardi — refresh token
 * httpOnly cookie'da, ya'ni tekshiruv serverda API chaqirig'ini talab qilib
 * LCP yo'liga tushardi. Ildiz HAR DOIM landing; app'ga o'tish — header'dagi
 * ko'rinadigan «Tizimga kirish» tugmasi.
 *
 * ⛔ `cookies()` / `headers()` / `searchParams` ISHLATILMAYDI (SSG buziladi).
 * ⛔ `generateStaticParams` KO'CHIRILMAYDI — `[locale]/layout.tsx` dagisi
 * guruhga avtomatik meros bo'ladi (81 marshrut isboti bilan o'lchangan).
 *
 * Bu to'lqinda sahifa — QOBIQ: Header + bitta Section + Footer. Yakuniy
 * kompozitsiya (hero `text-hero` bilan, seksiyalar, forma, JSON-LD,
 * metadata) — 10-07 ning ishi va bu fayl o'sha rejada qayta yoziladi.
 * ⛔ `text-hero` bu faylda ISHLATILMAYDI (u `marketing/hero.tsx` ning
 * yagona uyi, G-land-5(a)).
 */
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

  return (
    <>
      <Header />
      <main className="flex-1" id="kontent">
        <Section>
          {/* Sahifada AYNAN bitta <h1> (§15.11); o'lcham bu to'lqinda
              seksiya darajasida — `text-hero` 10-07 dagi hero.tsx bilan
              keladi. */}
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("hero.headline")}
          </h1>
        </Section>
      </main>
      <Footer />
    </>
  );
}
