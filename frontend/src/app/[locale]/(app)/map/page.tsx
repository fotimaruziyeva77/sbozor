"use client";

import { Suspense, useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { parseAsString, useQueryStates } from "nuqs";

import { StallCardDialog } from "@/components/stalls/stall-card-dialog";
import { StallMap } from "@/components/stalls/stall-map";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * Sxematik plan-xarita (MARKET-06).
 *
 * Huquq tekshiruvi SO'ROVDAN OLDIN: `market_data_view` bo'lmasa xarita
 * komponenti umuman render qilinmaydi, ya'ni `GET /stalls/map` ga so'rov
 * ham ketmaydi.
 *
 * `Suspense` MAJBURIY: qidiruv maydoni URL parametrini o'qiydi va bu
 * daraxtning shu qismini klient renderiga o'tkazadi. Chegara bo'lmasa
 * Next.js butun sahifani statik prerender ro'yxatidan chiqarardi.
 *
 * TANLANGAN RASTA SHU YERDA (Pitfall 8): u katakning propiga TUSHMAYDI —
 * aks holda har bosishda 1000 katak qayta render bo'lardi.
 * =============================================================================
 */
export default function MapPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const [selectedStallId, setSelectedStallId] = useState<string | null>(null);

  const roles = principal?.roles ?? [];
  const canView = hasPermission(roles, "market_data_view");
  const canManage = hasPermission(roles, "stall_manage");

  // Barqaror havola: u `StallMap` orqali memoizatsiyalangan kataklarga
  // tushadi va har renderda yangilansa memo butunlay ma'nosiz bo'lardi.
  const openStall = useCallback((stallId: string) => {
    setSelectedStallId(stallId);
  }, []);

  if (!canView) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t("errors.forbidden")}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">
        {t("map.title")}
      </h1>

      <Suspense
        fallback={
          <div aria-busy="true" className="flex flex-col gap-4" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-16 rounded-lg" />
            <Skeleton className="h-64 rounded-lg" />
          </div>
        }
      >
        <MapWorkspace onSelectStall={openStall} />
      </Suspense>

      <StallCardDialog
        canManage={canManage}
        onClose={() => setSelectedStallId(null)}
        stallId={selectedStallId}
      />
    </div>
  );
}

/** URL holatini o'qiydigan qism — `Suspense` chegarasining ICHIDA. */
function MapWorkspace({
  onSelectStall,
}: {
  onSelectStall: (stallId: string) => void;
}) {
  const t = useTranslations();
  const [urlFilters, setUrlFilters] = useQueryStates({
    // Reestrdagi bilan bir xil mexanizm (UI-SPEC §8.3): nuqs'ning O'ZI
    // tarixga yozishni cheklaydi, maxsus debounce hooki yozilmaydi.
    q: parseAsString.withDefault("").withOptions({ throttleMs: 300 }),
  });

  return (
    <>
      <Field id="map-q" label={t("map.searchPlaceholder")}>
        <Input
          autoComplete="off"
          enterKeyHint="search"
          id="map-q"
          inputMode="numeric"
          onChange={(event) => void setUrlFilters({ q: event.target.value })}
          placeholder={t("map.searchPlaceholder")}
          type="search"
          value={urlFilters.q}
        />
      </Field>

      <StallMap focusCode={urlFilters.q} onSelectStall={onSelectStall} />
    </>
  );
}
