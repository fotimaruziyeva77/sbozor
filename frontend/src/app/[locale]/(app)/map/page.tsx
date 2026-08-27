"use client";

import { Suspense, useCallback, useState } from "react";
/*
 * ⛔⛔ `next/link` EMAS, i18n `Link` (2026-08-25 audit, «bo'limlarni
 *     bossak boshqa joyga o'tyapti»).
 *
 *   Xom `next/link` locale prefiksini QO'YMAYDI: /ru dagi direktor
 *   katakni bosganda proxy uni STANDART locale'ga (/uz) qaytarardi —
 *   ya'ni bosish tilni almashtirib, «boshqa joyga» olib borardi.
 */
import { Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { parseAsString, useQueryStates } from "nuqs";
import { Pencil } from "lucide-react";

import { BrandLoader } from "@/components/ui/brand-loader";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { PlanView } from "@/components/stalls/plan-view";
import { StallCardDialog } from "@/components/stalls/stall-card-dialog";
import { StallMap } from "@/components/stalls/stall-map";
import { Button, buttonVariants } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/auth-store";
import { cn } from "@/lib/cn";
import { useStallMapQuery } from "@/lib/market-queries";
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
    return <ForbiddenNotice />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("map.title")}
        </h1>

        {/*
         * ⛔ CHIZISH HAVOLASI FAQAT `stall_manage` OSTIDA. Direktor va
         *   nazoratchi uni umuman ko'rmaydi — bosib borib 403 olish
         *   «nega menga ruxsat yo'q?» degan savolni ekranda emas,
         *   xatoda tug'dirardi.
         */}
        {canManage ? (
          <Link
            className={cn(
              buttonVariants({ size: "sm", variant: "secondary" }),
              "ms-auto",
            )}
            href="/map/plan"
          >
            <Pencil aria-hidden="true" />
            {t("plan.openEditor")}
          </Link>
        ) : null}
      </div>

      <Suspense
        fallback={
          <BrandLoader />
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

      <MapSurface focusCode={urlFilters.q} onSelectStall={onSelectStall} />
    </>
  );
}

/**
 * Ikki ko'rinish — SXEMATIK va QO'LDA CHIZILGAN PLAN.
 *
 * =============================================================================
 * ⛔⛔ ALMASHTIRGICH FAQAT CHIZMA BOR BO'LGANDA CHIQADI.
 *
 *     Hech narsa chizilmagan bozorda ikkita tugma ko'rsatish — biri
 *     bo'sh ekranga olib boradigan — foydalanuvchini «men nimadir
 *     buzdimmi?» degan savolga qo'yardi. Chizma paydo bo'lgach
 *     almashtirgich O'ZI paydo bo'ladi.
 *
 * ⛔ BOSHLANG'ICH KO'RINISH — SXEMATIK, chizma bo'lganda ham.
 *   Sxematik ko'rinish HAR DOIM to'liq: unda barcha rasta bor. Plan
 *   esa CHALA bo'lishi mumkin (yarmi chizilgan) va uni sukut bo'yicha
 *   ochish odamga bozorning yarmini ko'rsatib, qolganini yashirardi.
 * =============================================================================
 */
function MapSurface({
  focusCode,
  onSelectStall,
}: {
  focusCode: string;
  onSelectStall: (stallId: string) => void;
}) {
  const t = useTranslations();
  const [view, setView] = useState<"schematic" | "plan">("schematic");
  const mapQuery = useStallMapQuery();

  const hasPlan = (mapQuery.data?.zones ?? []).some((zone) =>
    zone.cells.some((cell) => cell.plan_x !== null),
  );

  if (!hasPlan) {
    return <StallMap focusCode={focusCode} onSelectStall={onSelectStall} />;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-1" role="group">
        <Button
          aria-pressed={view === "schematic"}
          onClick={() => setView("schematic")}
          size="sm"
          variant={view === "schematic" ? "default" : "secondary"}
        >
          {t("plan.viewSchematic")}
        </Button>
        <Button
          aria-pressed={view === "plan"}
          onClick={() => setView("plan")}
          size="sm"
          variant={view === "plan" ? "default" : "secondary"}
        >
          {t("plan.viewPlan")}
        </Button>
      </div>

      {view === "schematic" ? (
        <StallMap focusCode={focusCode} onSelectStall={onSelectStall} />
      ) : (
        <PlanView focusCode={focusCode} onSelectStall={onSelectStall} />
      )}
    </div>
  );
}
