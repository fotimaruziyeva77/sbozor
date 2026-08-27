"use client";

import type { ComponentType } from "react";
import {
  ArrowRight,
  CircleDashed,
  ClipboardCheck,
  Store,
} from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { businessDayIn } from "@/components/snapshots/day-picker";
import { Card, CardContent } from "@/components/ui/card";
import { BrandLoader } from "@/components/ui/brand-loader";
import { Link } from "@/i18n/navigation";
import { formatAmount } from "@/lib/format-number";
import { useOccupancyDay } from "@/lib/occupancy-queries";
import { useReviewBudget } from "@/lib/review-queries";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * NAZORATCHI PANELI (2026-08-25 auditi N1/N2 — foydalanuvchi: «har bir
 * rolni 10/10 qil, dashboardga o'xshasin»).
 *
 * Auditgacha nazoratchining bosh ekrani sarlavha + bitta son edi — kunlik
 * ishiga eshik YO'Q edi (kassirning 260819-dagi kasali). Endi kassir
 * paneli bilan bir tilda: uch hisoblagich + jarayon kartasi + eshiklar.
 *
 *   1-qator — UCH SANOQ: Ko'rmasdan tekshirish (answered/budget) ·
 *             Noaniq navbati (answered/budget) · Bugungi bandlik
 *             (occupied/stalls);
 *   2-qator — jarayon kartasi (ikki navbat yig'indisi, progress chiziq)
 *             + urg'uli «Ko'rib chiqish» eshigi va «Bandlik» eshigi.
 *
 * ⛔⛔ FAQAT BACKENDDA BOR MA'LUMOT: `GET /review/budget` (uchala son ham
 *     serverdan — `queueBudgetSchema` izohi) va `GET /occupancy?day=`.
 *     Yangi endpoint YO'Q, arifmetika faqat ko'rsatish uchun qo'shish.
 *
 * ⛔ So'rovlar FAQAT nazoratchida ketadi: chaqiruvchi (`dashboard/page.tsx`)
 *    komponentni `occupancy_review` sharti bilan chizadi — shart
 *    KOMPONENTDAN TASHQARIDA (kodbazadagi naqsh, G-motion-6(b,c) ruhi).
 * =============================================================================
 */

export function InspectorBrief() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  const todayIso = businessDayIn("Asia/Tashkent", new Date());
  const budget = useReviewBudget(todayIso);
  const occupancy = useOccupancyDay(todayIso, todayIso);

  if (budget.isPending) {
    /* Bozor «rasta ustunlari» loaderi — spinner EMAS (masterplan §3.2). */
    return <BrandLoader />;
  }

  const blind = budget.data?.blind_audit ?? null;
  const uncertain = budget.data?.uncertain ?? null;
  const occ = occupancy.data ?? null;

  const answered =
    blind === null || uncertain === null
      ? null
      : blind.answered + uncertain.answered;
  const total =
    blind === null || uncertain === null
      ? null
      : blind.budget + uncertain.budget;
  const ratio = total === null || total === 0 ? 0 : (answered as number) / total;
  const percent = Math.round(ratio * 100);

  const pair = (part: number | null | undefined, whole: number | null | undefined) =>
    part === null || part === undefined || whole === null || whole === undefined
      ? "—"
      : `${formatAmount(format, part, locale)} / ${formatAmount(format, whole, locale)}`;

  return (
    <div className="flex flex-col gap-4">
      {/* ---- 1-qator: uch hisoblagich ----------------------------------- */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard
          icon={ClipboardCheck}
          label={t("review.blindTitle")}
          tone="accent"
          value={pair(blind?.answered, blind?.budget)}
        />
        <StatCard
          icon={CircleDashed}
          label={t("review.uncertainTitle")}
          tone="info"
          value={pair(uncertain?.answered, uncertain?.budget)}
        />
        <StatCard
          icon={Store}
          label={t("dashboard.occupancyTitle")}
          tone="success"
          value={pair(occ?.occupied, occ?.stalls)}
        />
      </div>

      {/* ---- 2-qator: jarayon + eshiklar -------------------------------- */}
      <div className="grid items-stretch gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardContent className="flex h-full flex-col justify-center gap-2 pt-5">
            <p className="text-sm font-semibold uppercase tracking-wide text-text-muted">
              {t("dashboard.inspProgress")}
            </p>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="font-mono text-2xl font-semibold tabular-nums">
                {total === null ? "—" : pair(answered, total)}
              </span>
              <span className="font-mono text-sm font-semibold tabular-nums text-accent-text">
                {total === null ? "" : `${percent}%`}
              </span>
            </div>
            <div
              aria-hidden="true"
              className="h-2.5 w-full overflow-hidden rounded-full bg-border"
            >
              <div
                className="cashier-bar-fill h-full rounded-full bg-accent"
                style={{ width: `${percent}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex h-full flex-col justify-center gap-3 pt-5">
            <Link
              className={cn(
                "group flex min-h-12 items-center gap-3 rounded-xl bg-accent px-4",
                "text-sm font-semibold text-accent-fg transition-colors hover:bg-accent-hover",
              )}
              href="/review"
            >
              <ClipboardCheck aria-hidden className="size-5 shrink-0" />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate">{t("review.title")}</span>
                <span className="truncate text-xs font-normal text-accent-fg/80">
                  {t("dashboard.reviewHint")}
                </span>
              </span>
              <ArrowRight aria-hidden className="size-5 shrink-0" />
            </Link>
            <Link
              className={cn(
                "group flex min-h-12 items-center gap-3 rounded-xl border border-border-ui px-4",
                "text-sm font-semibold transition-colors hover:bg-surface-muted",
              )}
              href="/occupancy"
            >
              <Store aria-hidden className="size-5 shrink-0" />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate">{t("occupancy.title")}</span>
                <span className="truncate text-xs font-normal text-text-muted">
                  {t("dashboard.occupancyHint")}
                </span>
              </span>
              <ArrowRight
                aria-hidden
                className="size-4 shrink-0 transition-transform group-hover:translate-x-0.5"
              />
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

/* ---- hisoblagich kartasi (kassir paneli bilan bir til) ------------------ */

const STAT_TONE = {
  accent: "bg-accent/12 text-accent-text",
  info: "bg-info/15 text-info-text",
  success: "bg-success/10 text-success-text",
} as const;

function StatCard({
  icon: Icon,
  label,
  tone,
  value,
}: {
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  label: string;
  tone: keyof typeof STAT_TONE;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-5">
        <span
          aria-hidden="true"
          className={cn(
            "grid size-12 shrink-0 place-items-center rounded-xl",
            STAT_TONE[tone],
          )}
        >
          <Icon aria-hidden className="size-6" />
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="truncate text-sm font-semibold text-text-muted">
            {label}
          </span>
          <span className="font-mono text-2xl font-semibold tabular-nums">
            {value}
          </span>
        </span>
      </CardContent>
    </Card>
  );
}
