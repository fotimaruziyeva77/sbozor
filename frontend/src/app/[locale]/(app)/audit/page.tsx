"use client";

import { Suspense } from "react";
import { useTranslations } from "next-intl";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { AuditFiltersPanel } from "@/components/audit/audit-filters";
import { AuditList } from "@/components/audit/audit-list";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * Audit jurnali (D-11, D-12) — ROADMAP mezoni #3 ning ko'rinadigan isboti.
 *
 * KIM KO'RADI: `AUDIT_VIEW` — platforma admini, direktor va bozor admini.
 * Kassir va nazoratchi bu bo'limni umuman ko'rmaydi: navigatsiyada havola
 * yashirilgan, sahifa `errors.forbidden` ko'rsatadi va (hal qiluvchi qatlam)
 * backend `require_permission(AUDIT_VIEW)` bilan 403 qaytaradi (T-01-70).
 *
 * DIQQAT — huquq tekshiruvi so'rovdan OLDIN: huquqsiz foydalanuvchi uchun
 * ro'yxat komponenti umuman render qilinmaydi, ya'ni `GET /audit` ga
 * so'rov ham ketmaydi. Bu 403 ni yashirish uchun emas (u baribir bo'lardi),
 * balki jurnalga ma'nosiz rad etilgan urinishlar yozilmasligi uchun.
 *
 * `Suspense` MAJBURIY: filtrlar URL qidiruv parametrlarini o'qiydi, bu esa
 * daraxtning shu qismini klient tomonda render qilishga o'tkazadi. Chegara
 * bo'lmasa Next.js butun sahifani statik prerender ro'yxatidan chiqarardi.
 */
export default function AuditPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "audit_view")) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">
        {t("audit.title")}
      </h1>

      <Suspense
        fallback={
          <p className="text-sm text-text-muted" role="status">
            {t("common.loading")}
          </p>
        }
      >
        <AuditFiltersPanel />
        <AuditList />
      </Suspense>
    </div>
  );
}
