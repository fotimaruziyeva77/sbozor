"use client";

import { Suspense } from "react";
import { useTranslations } from "next-intl";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ParkingReportWorkspace } from "@/components/parking/parking-report";
import { BrandLoader } from "@/components/ui/brand-loader";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * «Avtoturargoh» — agent obyektining davr hisoboti (kirdi / chiqdi /
 * tushum + Excel).
 *
 * Sahifa `camera_view` bilan ochiladi — server marshruti
 * (`edge_sites.py::parking_report_*`) AYNAN shu huquq ostida,
 * `parking-summary` bilan bir xil; menyu yozuvi ham (`app-shell.tsx`).
 * Haqiqiy darvoza — serverdagi `require_permission`.
 *
 * ⚠ `Suspense` MAJBURIY: ish maydoni `?site=&from=&to=` ni `nuqs` orqali
 *   KLIENTDA o'qiydi va chegara bo'lmasa Next 16 marshrutni statik
 *   prerender ro'yxatidan chiqarib `build` ni yiqitadi (`/reports` da
 *   o'lchangan).
 *
 * Sarlavha (`<title>`) `parking/layout.tsx` dan — sahifa `"use client"`
 * va `metadata` eksport qila olmaydi (K-03).
 */
export default function ParkingPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "camera_view")) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("parkingReport.title")}
        </h1>
        <p className="text-sm text-text-muted">{t("parkingReport.subtitle")}</p>
      </div>

      <Suspense fallback={<BrandLoader />}>
        <ParkingReportWorkspace />
      </Suspense>
    </div>
  );
}
