"use client";

import { Suspense, useCallback, useState } from "react";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";

import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { StallCardDialog } from "@/components/stalls/stall-card-dialog";
import { StallCategoryDialog } from "@/components/stalls/stall-category-dialog";
import { StallDialog } from "@/components/stalls/stall-dialog";
import { StallFiltersPanel } from "@/components/stalls/stall-filters";
import { StallList } from "@/components/stalls/stall-list";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { StallListItem } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Rastalar reestri (MARKET-02).
 *
 * IKKI HUQUQ, IKKI XIL NATIJA:
 *   `market_data_view` — reestrni ko'rish (direktor ham ko'radi);
 *   `stall_manage`     — qo'shish / tahrirlash / toifa davri ochish.
 *
 * DIQQAT — huquq tekshiruvi SO'ROVDAN OLDIN: huquqsiz foydalanuvchi uchun
 * ro'yxat komponenti umuman render qilinmaydi, ya'ni `GET /stalls` ga so'rov
 * ham ketmaydi. Bu 403 ni yashirish uchun emas (u baribir bo'lardi), balki
 * auditga ma'nosiz rad etilgan urinishlar yozilmasligi uchun.
 *
 * `Suspense` MAJBURIY: filtrlar URL qidiruv parametrlarini o'qiydi va bu
 * daraxtning shu qismini klient renderiga o'tkazadi. Chegara bo'lmasa
 * Next.js butun sahifani statik prerender ro'yxatidan chiqarardi.
 *
 * TANLANGAN RASTA SHU YERDA yashaydi (Pitfall 8): uni ro'yxat ham, xarita
 * katagi ham prop sifatida OLMAYDI — faqat `<StallCardDialog>` o'qiydi.
 * =============================================================================
 */
export default function StallsPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  const [selectedStallId, setSelectedStallId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editStallId, setEditStallId] = useState<string | null>(null);
  const [categoryStall, setCategoryStall] = useState<StallListItem | null>(
    null,
  );

  const roles = principal?.roles ?? [];
  const canView = hasPermission(roles, "market_data_view");
  const canManage = hasPermission(roles, "stall_manage");

  // Havola BARQAROR bo'lishi shart: `StallFiltersPanel` uni effekt
  // bog'liqligi sifatida ishlatadi.
  const openStall = useCallback((stallId: string) => {
    setSelectedStallId(stallId);
  }, []);

  if (!canView) {
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("stalls.title")}
        </h1>

        {/* Huquq yo'q -> tugma RENDER QILINMAYDI (yashirilmaydi). */}
        {canManage ? (
          <Button onClick={() => setCreateOpen(true)}>
            <Plus aria-hidden="true" />
            {t("stalls.create")}
          </Button>
        ) : null}
      </div>

      <Suspense
        fallback={
          <div aria-busy="true" className="flex flex-col gap-4" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-40 rounded-lg" />
            <Skeleton className="h-16 rounded-lg" />
          </div>
        }
      >
        <StallFiltersPanel onOpenStall={openStall} />
        <StallList
          canManage={canManage}
          onChangeCategory={setCategoryStall}
          onEditStall={(stall) => setEditStallId(stall.id)}
          onOpenStall={openStall}
        />
      </Suspense>

      {/*
       * Kartadan "Tahrirlash" bosilganda karta YOPILADI va tahrir dialogi
       * ochiladi: ikkita modal bir vaqtda fokus tuzog'ini talashib qolardi.
       */}
      <StallCardDialog
        canManage={canManage}
        onClose={() => setSelectedStallId(null)}
        onEdit={(stallId) => {
          setSelectedStallId(null);
          setEditStallId(stallId);
        }}
        stallId={selectedStallId}
      />

      {canManage ? (
        <>
          <StallDialog
            mode="create"
            onOpenChange={setCreateOpen}
            open={createOpen}
            stallId={null}
          />

          <StallDialog
            mode="edit"
            onOpenChange={(next) => {
              if (!next) setEditStallId(null);
            }}
            open={editStallId !== null}
            stallId={editStallId}
          />

          <StallCategoryDialog
            onOpenChange={(next) => {
              if (!next) setCategoryStall(null);
            }}
            open={categoryStall !== null}
            stall={categoryStall}
          />
        </>
      ) : null}
    </div>
  );
}
