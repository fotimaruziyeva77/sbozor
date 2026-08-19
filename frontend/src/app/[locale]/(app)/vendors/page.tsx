"use client";

import { Suspense, useState } from "react";
import { Info, UserPlus } from "lucide-react";
import { useTranslations } from "next-intl";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { ReadOnlyNote } from "@/components/auth/read-only-note";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { VendorList } from "@/components/vendors/vendor-list";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Sotuvchilar reestri (MARKET-04, D-09…D-12).
 *
 * IKKI HUQUQ, IKKI XIL NATIJA:
 *   `VENDOR_VIEW`   — ro'yxatni ko'rish (platforma admini, direktor, bozor admini)
 *   `VENDOR_MANAGE` — qo'shish / tahrirlash / biriktirish (direktorda YO'Q — D-07)
 *
 * Huquq tekshiruvi so'rovdan OLDIN (`audit/page.tsx` naqshi): huquqsiz
 * foydalanuvchi uchun ro'yxat komponenti umuman render qilinmaydi, ya'ni
 * `GET /vendors` ga so'rov ham ketmaydi. Bu 403 ni yashirish uchun emas —
 * u baribir bo'lardi — balki SHAXSIY MA'LUMOT o'qish auditiga ma'nosiz
 * "ko'rildi" yozuvlari tushmasligi uchun (D-09).
 *
 * `Suspense` MAJBURIY: ro'yxat qidiruv satrini URL'dan o'qiydi (`nuqs`), bu
 * esa daraxtning shu qismini klient renderiga o'tkazadi. Chegara bo'lmasa
 * Next.js butun sahifani statik prerender ro'yxatidan chiqarardi
 * (`audit/page.tsx:25-26` naqshi).
 *
 * DIQQAT — BU FAYLDA DIALOG YO'Q va bu ATAYIN. Audit bildirishi (§8.6)
 * modal EMASligi shu sahifaning asosiy qarori; barcha yozuv dialoglari
 * (yaratish / tahrirlash / biriktirish) `vendor-list.tsx` ichida yashaydi,
 * ya'ni bu yerda bildirishni tasodifan dialog ichiga solib qo'yish MUMKIN
 * emas. Yaratish tugmasining holati faqat prop bo'lib pastga uzatiladi.
 * =============================================================================
 */
export default function VendorsPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const [createOpen, setCreateOpen] = useState(false);

  const roles = principal?.roles ?? [];
  const canView = hasPermission(roles, "vendor_view");
  const canManage = hasPermission(roles, "vendor_manage");

  if (!canView) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("vendors.title")}
          </h1>

          {canManage ? (
            <Button onClick={() => setCreateOpen(true)}>
              <UserPlus aria-hidden="true" />
              {t("vendors.create")}
            </Button>
          ) : null}
        </div>

        {/*
         * SHAXSIY MA'LUMOT BILDIRISHI — UI-SPEC §8.6 ning aynan shakli:
         * PASSIV bir qator, sarlavha ostida, ekranga BIR MARTA.
         *
         * Modal EMAS va tasdiq EMAS: bozor admini bu ekranni kuniga o'nlab
         * marta ochadi va har safargi tasdiq refleks bilan bosiladigan
         * bo'lib qolardi (warning fatigue) — bu esa loyihaning "≤3 bosish"
         * tamoyiliga bevosita zid. Qator-bo'yicha belgi ham EMAS: audit
         * RO'YXAT O'QISHINI yozadi, har qatorni emas, ya'ni qator belgisi
         * mexanizmni noto'g'ri tasvirlardi.
         *
         * To'siq KO'RINMASA, to'sadigan narsa yo'q: audit'ning maqsadi —
         * shaxsiy ma'lumotni sababsiz varaqlashning OLDINI OLISH (D-09),
         * ko'rinmaydigan jurnal esa faqat keyin ayblaydi.
         */}
        <p className="flex items-center gap-2 text-xs text-text-muted">
          <Info aria-hidden="true" className="size-3.5 shrink-0" />
          {t("vendors.auditNotice")}
        </p>

        {canManage ? null : <ReadOnlyNote />}
      </div>

      <Suspense
        fallback={
          <div aria-busy="true" className="flex flex-col gap-3" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-10 rounded-md" />
            <Skeleton className="h-24 rounded-lg" />
            <Skeleton className="h-24 rounded-lg" />
          </div>
        }
      >
        <VendorList
          canManage={canManage}
          createOpen={createOpen}
          onCreateOpenChange={setCreateOpen}
        />
      </Suspense>
    </div>
  );
}
