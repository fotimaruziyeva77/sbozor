"use client";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { VendorAccount } from "@/components/director/vendor-account";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * SOTUVCHI HISOBI — `Sbozor Direktor - Sotuvchi.dc.html`.
 *
 * ⛔ IKKI HUQUQ KERAK: `report_view` (qarzdorlik reestri) va
 *    `vendor_view` (ism ko'rinadi). Ikkalasi ham direktorda bor,
 *    kassirda BIRORTASI ham yo'q. Shart komponentdan tashqarida —
 *    huquqsiz sessiyada so'rov ketmaydi.
 * =============================================================================
 */

export default function VendorAccountPage() {
  const { principal } = useAuthStore();
  const roles = principal?.roles ?? [];

  if (!hasPermission(roles, "report_view") || !hasPermission(roles, "vendor_view")) {
    return <ForbiddenNotice />;
  }

  return <VendorAccount />;
}
