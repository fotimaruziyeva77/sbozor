"use client";

import { useLocale } from "next-intl";

import { localeHref } from "@/lib/locale-href";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ReviewSession } from "@/components/review/review-session";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

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

export default function UncertainReviewPage() {
  const locale = useLocale();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "occupancy_review")) {
    return <ForbiddenNotice />;
  }

  return <ReviewSession exitHref={localeHref(locale, "/review")} />;
}
