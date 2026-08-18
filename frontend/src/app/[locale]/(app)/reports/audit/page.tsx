"use client";

import { AuditSheet } from "@/components/director/audit-sheet";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * TEKSHIRUV UCHUN YIG'MA VARAQ — `Sbozor Direktor - Tekshiruv.dc.html`.
 *
 * ⛔ HUQUQ `report_view`: varaqda tushum, qarz va nomuvofiqlik raqamlari
 *    birga turadi — ya'ni u hisobot yuzasining eng to'liq ko'rinishi.
 *    Kassirda bu huquq YO'Q va u bu sahifani UMUMAN ochmaydi.
 *
 * ⛔ SHART KOMPONENTDAN TASHQARIDA: huquqsiz sessiyada `AuditSheet`
 *    umuman render qilinmaydi, ya'ni oltita so'rovning BIRORTASI ham
 *    ketmaydi.
 * =============================================================================
 */

export default function AuditPage() {
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "report_view")) {
    return <ForbiddenNotice />;
  }

  return <AuditSheet />;
}
