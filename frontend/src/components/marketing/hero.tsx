import type { CSSProperties } from "react";

import { getTranslations } from "next-intl/server";

import { HeroScene } from "@/components/marketing/hero-scene";
import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/cn";

/*
 * Y-1 — hero: birinchi ekran matni (10-UI-SPEC §5.1, sketch 003-B [K-1]).
 *
 * ⛔ SERVER COMPONENT — bu faylda klient direktivasi 0 marta (G-land-1(b),
 * darvoza satr skani izohni ham sanaydi — shuning uchun direktiv ibora bu
 * izohda literal yozilmaydi): LCP nomzodi `h1` va u klient JS'ga
 * BOG'LANMAYDI (§1.2 qoida 1). Bitta direktiva sarlavhani hidratatsiya
 * kutishiga bog'lab SC#5 ni jimgina yiqitadi. Naqsh:
 * `(auth)/login/page.tsx` — server matn + klient orol kompozitsiyasi.
 *
 * ⛔⛔ `h1` `.motion-enter` NI ATAYIN OLMAYDI — bu unutilgan EMAS, LCP
 * qarori (10-RESEARCH [A1], reja Task 1): `.motion-enter` `opacity: 0`
 * dan boshlanadi va Chrome'ning LCP algoritmi `opacity: 0` elementni
 * «chizilgan» deb hisoblamaydi — `h1` ketma-ketlikda tursa LCP ~310 ms
 * (60 ms delay + 250 ms davomiylik) sof yo'qotishga suriladi va G-land-1
 * buni USHLAMAYDI (u klient direktivasini izlaydi). Kirish ketma-ketligi
 * shu sabab `brand` dan boshlanib lid → CTA → ⭐ → ishonch qatoriga
 * qo'llanadi (`--i` 0 dan). Natija HUMAN-UAT #1 da LCP soni bilan yopiladi.
 * ⛔ Bu izohni o'qib `h1` ga `.motion-enter` QO'SHMANG.
 *
 * ⛔ Hero-o'lcham utilitasi (`h1` sinfida) — butun repozitoriyada AYNAN shu
 * faylda va AYNAN BIR marta (G-land-5(a) ikki qatlamli qulf: fayl +
 * uchrashuv soni; utilita nomi izohda literal yozilmaydi — uchrashuv sanog'i
 * izohga qoqilmasin). Displey-pul utilitasi ISHLATILMAYDI [L-4]: u pul roli
 * va `TEXT_DISPLAY_FILES` `deepEqual` bilan ikki app fayliga qulflangan.
 *
 * ⛔ Vertikal seksiya bo'shliqlari bu faylda YO'Q — sahifa heroni
 * `<Section>` bilan o'raydi va u qiymatlarning yagona uyi `section.tsx`
 * (G-land-5(c)).
 *
 * ≤840px da bir ustun: matn BIRINCHI, sahna OSTIDA (§5.8) — DOM tartibi
 * shuni beradi, media-shox faqat ustun sonini almashtiradi.
 */
export async function Hero() {
  const t = await getTranslations("landing");
  const tCommon = await getTranslations("common");

  return (
    <div className="grid items-center gap-8 min-[841px]:grid-cols-[1.05fr_1fr]">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-3">
          <p
            className="motion-enter text-sm font-semibold tracking-wide text-accent"
            style={{ "--i": 0 } as CSSProperties}
          >
            {tCommon("appName")}
          </p>
          {/* LCP nomzodi — `.motion-enter`siz (sabab modul sarlavhasida). */}
          <h1 className="text-hero font-semibold text-balance text-text">
            {t("hero.headline")}
          </h1>
        </div>
        <p
          className="motion-enter max-w-[66ch] text-lg leading-relaxed text-text-muted"
          style={{ "--i": 1 } as CSSProperties}
        >
          {t("hero.sub")}
        </p>
        <div
          className="motion-enter flex flex-wrap items-center gap-3"
          style={{ "--i": 2 } as CSSProperties}
        >
          {/*
           * Birlamchi CTA — sahifa ichidagi `#demo` ankeri: locale prefiksli
           * `Link` shart emas (header skip-link presedenti). Ikkilamchi —
           * `size="lg"`, ⛔ `hero` EMAS: ikki teng og'irlikdagi tugma
           * «yagona CTA» qoidasini [K-2] buzardi (§7.4).
           */}
          <a
            className={cn(
              buttonVariants({ size: "hero", variant: "default" }),
              "landing-cta-glow",
            )}
            href="#demo"
          >
            {t("hero.ctaPrimary")}
          </a>
          <Link
            className={cn(buttonVariants({ size: "lg", variant: "secondary" }))}
            href="/login"
          >
            {t("hero.ctaSecondary")}
          </Link>
        </div>
        <p
          className="motion-enter max-w-[52ch] text-sm text-text-muted"
          style={{ "--i": 3 } as CSSProperties}
        >
          <span aria-hidden="true">⭐ </span>
          <strong className="font-semibold text-text">
            {t("hero.claimStrong")}
          </strong>{" "}
          {t("hero.claim")}
        </p>
        {/*
         * Ishonch qatori — ✓ belgilari DEKORATIV (§15.12: rang yolg'iz
         * signal emas, ma'no matnda). `trust.residency` `#ishonch`
         * ankeriga HAVOLA (G-land-4(c), §13.5): qisqa shakl bu yerda,
         * to'liq va halol izoh ishonch blokida.
         */}
        <ul
          className="motion-enter flex flex-wrap gap-x-5 gap-y-2 text-xs text-text-muted"
          style={{ "--i": 4 } as CSSProperties}
        >
          <li>
            <a className="underline-offset-2 hover:underline" href="#ishonch">
              <span aria-hidden="true" className="font-semibold text-success-text">
                ✓{" "}
              </span>
              {t("trust.residency")}
            </a>
          </li>
          <li>
            <span aria-hidden="true" className="font-semibold text-success-text">
              ✓{" "}
            </span>
            {t("trust.vpn")}
          </li>
          <li>
            <span aria-hidden="true" className="font-semibold text-success-text">
              ✓{" "}
            </span>
            {t("trust.audit")}
          </li>
          <li>
            <span aria-hidden="true" className="font-semibold text-success-text">
              ✓{" "}
            </span>
            {t("trust.languages")}
          </li>
        </ul>
        {/* Halol raqamlar lentasi — da'vo emas, mahsulot faktlari (K-7). */}
        <dl
          className="landing-stats motion-enter grid grid-cols-2 gap-x-6 gap-y-4 pt-5 sm:grid-cols-4"
          style={{ "--i": 5 } as CSSProperties}
        >
          <div>
            <dt className="text-xs text-text-muted">{t("stats.tapsLabel")}</dt>
            <dd className="text-lg font-semibold text-text" data-numeric>
              {t("stats.tapsValue")}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">
              {t("stats.archiveLabel")}
            </dt>
            <dd className="text-lg font-semibold text-text" data-numeric>
              {t("stats.archiveValue")}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">{t("stats.langsLabel")}</dt>
            <dd className="text-lg font-semibold text-text" data-numeric>
              {t("stats.langsValue")}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">{t("stats.replyLabel")}</dt>
            <dd className="text-lg font-semibold text-text" data-numeric>
              {t("stats.replyValue")}
            </dd>
          </div>
        </dl>
      </div>
      <HeroScene />
    </div>
  );
}
