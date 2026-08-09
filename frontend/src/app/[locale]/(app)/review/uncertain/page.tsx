"use client";

import { useLocale, useTranslations } from "next-intl";

import { ReviewSession } from "@/components/review/review-session";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";
import { routing } from "@/i18n/routing";

/*
 * =============================================================================
 * Y-2 SESSIYASI — NOANIQ NAVBAT (AI-03).
 *
 * ⚠ SAHIFA QOBIQ: butun mantiq `review-session.tsx` da. Sabab
 *   `cameras/page.tsx` dagi bilan bir xil — huquq darvozasi so'rovdan
 *   OLDIN turishi kerak, ya'ni huquqsiz sessiyada `GET /review/...` ga
 *   so'rov UMUMAN ketmaydi va jurnalga ma'nosiz rad etilgan urinishlar
 *   yozilmaydi. Haqiqiy nazorat serverda
 *   (`require_permission(OCCUPANCY_REVIEW)`).
 *
 * ⛔ URL'DA HOLAT YO'Q (§4.5): band identifikatori manzilda bo'lsa,
 *    nazoratchi orqaga qaytib javobni QAYTA KO'RA olardi. Navbat
 *    SERVERDA yuriydi va sahifa yangilansa server javob berilmagan
 *    bandni qaytaradi.
 *
 * ⚠ `Suspense` KERAK EMAS: bu sahifa `nuqs` ni umuman ishlatmaydi
 *   (yuqoridagi qoida), ya'ni statik prerender chegarasi buzilmaydi.
 * =============================================================================
 */

/**
 * Til prefiksli manzil — sabab `review/page.tsx:64` da yozilgan
 * (`@/i18n/navigation` vitest ostida yechilmaydi, 05-09 deviatsiya #2).
 */
function localeHref(locale: string, path: string): string {
  const config = routing.localePrefix;
  const prefixes: Partial<Record<string, string>> =
    typeof config === "object" && "prefixes" in config
      ? (config.prefixes ?? {})
      : {};
  return `${prefixes[locale] ?? `/${locale}`}${path}`;
}

export default function UncertainReviewPage() {
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

  return <ReviewSession exitHref={localeHref(locale, "/review")} />;
}
