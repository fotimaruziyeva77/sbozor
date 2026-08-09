"use client";

import { useLocale, useTranslations } from "next-intl";

import { BlindSession } from "@/components/blind-audit/blind-session";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";
import { routing } from "@/i18n/routing";

/*
 * =============================================================================
 * ⛔⛔ Y-3 SESSIYASI — MARSHRUTDA DINAMIK SEGMENT YO'Q (AI-04, D-17.4).
 *
 * Bu katalogda `[` bilan boshlanadigan fayl yoki papka BO'LMASLIGI shart
 * va uni `scripts/blind-payload.test.mjs` (G-14a) FAYL TIZIMI darajasida
 * o'lchaydi. Shart qo'pol — va u ATAYIN qo'pol: nozikroq tekshiruv (URL
 * parametrlarini tahlil qilish) o'zi buzilishi mumkin bo'lgan KODGA
 * aylanardi.
 *
 * Identifikatorli URL uch yo'lni ochardi va uchalasi ham namunani KEYIN
 * TAHRIRLASH (05-RESEARCH §C.8, 4-dushman):
 *   (a) brauzer tarixi orqali javob berilgan bandga qaytish;
 *   (b) havolani nusxalab qayta ochish;
 *   (c) tarixdan bandni topib qayta urinish.
 * Identifikator bo'lmasa — uchalasi ham IMKONSIZ.
 *
 * ⛔ TAB EMAS, ALOHIDA MARSHRUT (§4.3). Tab bitta komponent daraxti,
 *    bitta kesh grafi va URL'da yashaydigan holat degani bo'lardi;
 *    alohida marshrut esa alohida katalog va G-12 aynan KATALOGNI
 *    skanerlaydi.
 *
 * ⚠ NAVIGATSIYADA BU MARSHRUT YO'Q (§4.6): u SESSIYA, bo'lim emas.
 *   Unga faqat `/review` uyidan, OCHIQ NIYAT bilan kiriladi.
 * =============================================================================
 */

/** Til prefiksli manzil — sabab `review/page.tsx:64` da. */
function localeHref(locale: string, path: string): string {
  const config = routing.localePrefix;
  const prefixes: Partial<Record<string, string>> =
    typeof config === "object" && "prefixes" in config
      ? (config.prefixes ?? {})
      : {};
  return `${prefixes[locale] ?? `/${locale}`}${path}`;
}

export default function BlindReviewPage() {
  const t = useTranslations();
  const locale = useLocale();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "occupancy_review")) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t("errors.forbidden")}
      </p>
    );
  }

  return <BlindSession exitHref={localeHref(locale, "/review")} />;
}
