"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  AlertCircle,
  Ban,
  CalendarClock,
  Check,
  Ellipsis,
  Minus,
  Pencil,
  Tent,
  TriangleAlert,
  Wrench,
} from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { formatSoum } from "@/lib/format-number";

import { useStallFilters } from "@/components/stalls/stall-filters";
import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { StallListItem, StallStatusValue } from "@/lib/api-types";
import type { MapDayRow } from "@/lib/map-day-queries";
import { useMapDayStatusQuery } from "@/lib/map-day-queries";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useStallsQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * Rastalar reestri — JADVAL EMAS, zich karta qatori (UI-SPEC §8.1).
 *
 * 1-faza `<table>` ni ataylab rad etgan (telefonda gorizontal skroll); 2-faza
 * o'sha qarorni saqlaydi, lekin miqyos boshqa (10 foydalanuvchi -> 1000 rasta)
 * shuning uchun karta ZICHLASHTIRILGAN: `px-4 py-3`, `<640px` uch qator,
 * `>=640px` bitta qator.
 *
 * USTUN USTUVORLIGI (§8.2): tor ekranda FAQAT "bugungi tarif" yo'qoladi — u
 * toifadan hosila va kartada baribir ko'rinadi. Rasta raqami, holati va
 * sotuvchisi hech qachon yo'qolmaydi, chunki ular reestrning MAQSADI.
 *
 * PAGINATSIYA — keyset ("Ko'proq yuklash", §8.3). Sahifa raqami YO'Q: reestr
 * so'rovlar ORASIDA o'sadi (import, ikkinchi admin) va raqamli sahifalashda
 * yangi qatorlar sahifalarni surib yuborardi.
 * =============================================================================
 */

/**
 * Holat -> badge tone.
 *
 * `active` NEYTRAL: 1000 rastali reestrda "hammasi yashil" devori hech
 * qanday ma'lumot bermaydi va Apple-uslub minimalizmga zid (UI-SPEC §4.1 —
 * rang faqat harakat va xavf uchun). Farq badge MATNI va IKONKASI bilan
 * beriladi, ya'ni rang YAGONA signal emas (WCAG 1.4.1, §4.4).
 */
const STATUS_TONE: Record<StallStatusValue, BadgeTone> = {
  active: "neutral",
  maintenance: "warning",
  closed: "muted",
  // Yarmarka (0028) — success EMAS: yashil «pul keldi» degani, bu esa
  // «pul ATAYIN olinmaydi». Neytral badge + matn yetarli.
  fair: "neutral",
};

export function StallStatusBadge({ status }: { status: StallStatusValue }) {
  const tStatus = useTranslations("stalls.status");

  return (
    <Badge className="gap-1" tone={STATUS_TONE[status]}>
      {status === "maintenance" ? (
        <Wrench aria-hidden="true" className="size-3" />
      ) : null}
      {status === "closed" ? (
        <Ban aria-hidden="true" className="size-3" />
      ) : null}
      {tStatus(status)}
    </Badge>
  );
}

export function StallList({
  canManage,
  onChangeCategory,
  onEditStall,
  onOpenStall,
}: {
  canManage: boolean;
  onChangeCategory: (stall: StallListItem) => void;
  onEditStall: (stall: StallListItem) => void;
  onOpenStall: (stallId: string) => void;
}) {
  const t = useTranslations();
  const { filters, isEmpty } = useStallFilters();
  const stallsQuery = useStallsQuery(filters);
  /*
   * 261016: har qatorda BUGUNGI to'lov holati — xarita bilan AYNI javob
   * (`/billing/map`). Huquq bo'lmasa so'rov ketmaydi va qatorda holat yo'q.
   */
  const dayLayer = useMapDayStatusQuery();

  /*
   * TO'RT HOLAT (UI-SPEC §9): yuklanish / xato / bo'sh / natija.
   *
   * Yuklanish — `Skeleton`, matnli "Yuklanmoqda" EMAS (§9.1): matn layoutni
   * yig'ib, keyin 50 qator bilan yoyadi (CLS). E'lon KONTEYNER darajasida
   * BIR MARTA beriladi, har blokda emas.
   */
  if (stallsQuery.isPending) {
    return (
      <div aria-busy="true" className="flex flex-col gap-3" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        {[0, 1, 2, 3, 4].map((row) => (
          <Skeleton className="h-16 rounded-lg" key={row} />
        ))}
      </div>
    );
  }

  if (stallsQuery.isError) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t(marketErrorMessageKey(stallsQuery.error))}
      </p>
    );
  }

  const items = stallsQuery.data.pages.flatMap((page) => page.items);

  /*
   * IKKI XIL BO'SH HOLAT (§9.2) — ularning KEYINGI QADAMI boshqa:
   *   hech narsa yo'q -> yaratish/import;
   *   filtr topmadi   -> filtrni tozalash yoki raqamni tekshirish.
   * Bittasi bilan cheklanish adminni "rasta yo'q ekan" degan yolg'on
   * xulosaga olib borardi.
   */
  if (items.length === 0) {
    return isEmpty ? (
      <EmptyState
        description={t("stalls.emptyStateHint")}
        title={t("stalls.emptyState")}
      />
    ) : (
      <EmptyState
        description={t("stalls.emptyFilteredHint")}
        title={t("stalls.emptyFiltered")}
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/*
       * Natija soni `role="status"` bilan; yangi sahifa qo'shilganda
       * `aria-live="polite"` uni e'lon qiladi (§8.3) — aks holda skrinrider
       * foydalanuvchisi "hech narsa o'zgarmadi" deb o'ylaydi.
       */}
      <p
        aria-live="polite"
        className="text-sm text-text-muted"
        role="status"
      >
        {t("stalls.resultCount", { count: items.length })}
      </p>

      <ul aria-label={t("stalls.title")} className="flex flex-col gap-3">
        {items.map((stall) => (
          <li key={stall.id}>
            <StallRow
              canManage={canManage}
              day={dayLayer.byStallId.get(stall.id) ?? null}
              onChangeCategory={onChangeCategory}
              onEditStall={onEditStall}
              onOpenStall={onOpenStall}
              stall={stall}
            />
          </li>
        ))}
      </ul>

      {stallsQuery.hasNextPage ? (
        <div>
          <Button
            disabled={stallsQuery.isFetchingNextPage}
            onClick={() => void stallsQuery.fetchNextPage()}
            variant="secondary"
          >
            {stallsQuery.isFetchingNextPage
              ? t("common.loading")
              : t("stalls.loadMore")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function StallRow({
  canManage,
  day,
  onChangeCategory,
  onEditStall,
  onOpenStall,
  stall,
}: {
  canManage: boolean;
  /** Bugungi to'lov holati (`/billing/map`) — qatlam yo'q bo'lsa `null`. */
  day: MapDayRow | null;
  onChangeCategory: (stall: StallListItem) => void;
  onEditStall: (stall: StallListItem) => void;
  onOpenStall: (stallId: string) => void;
  stall: StallListItem;
}) {
  const t = useTranslations();
  const tProduct = useTranslations("stalls.productType");
  const format = useFormatter();
  const locale = useLocale();

  // D-16: zona, toifa va sotuvchi nomi DB kontenti — TARJIMA QILINMAYDI.
  // Ular `truncate` bo'ladi va yoniga doim `title` qo'yiladi (§5.1 qoida 4).
  const categoryLabel = stall.category_name ?? t("stalls.categoryUnset");
  // 0031: mahsulot turi va maydon — faqat KIRITILGAN bo'lsa (bo'shi shovqin).
  const placeParts = [stall.zone_name, categoryLabel];
  if (stall.product_type !== null) placeParts.push(tProduct(stall.product_type));
  if (stall.area_m2 !== null) {
    placeParts.push(
      t("stalls.areaValue", {
        area: format.number(stall.area_m2, { maximumFractionDigits: 2 }),
      }),
    );
  }
  const placeLabel = placeParts.join(" · ");
  const vendorLabel = stall.vendor_name ?? t("stalls.noVendor");

  return (
    <Card className="relative px-4 py-3 transition-shadow hover:shadow-raised">
      <div className="grid gap-2 sm:grid-cols-[auto_1fr_auto_auto_auto] sm:items-center sm:gap-4">
        <div className="flex items-center justify-between gap-3 sm:justify-start">
          {/*
           * Raqamning O'ZI kartani ochadi. D-16: raqam DB kontenti.
           * `tabular-nums` — raqamlar tik ustunda tursin. 2026-08-25:
           * yalang'och matn -> CHIP disk (maket uslubi) — bosiladigan
           * ekani endi shakldan ham ko'rinadi.
           */}
          {/*
           * 261016: BUTUN QATOR bosiladi — kod tugmasining `after:` qatlami
           * kartani qoplaydi (ichma-ich tugma yo'q, skrinrider uchun bitta
           * tugma). Amallar menyusi `z-10` bilan uning ustida qoladi.
           */}
          <button
            className="grid min-h-12 min-w-12 place-items-center rounded-xl bg-accent/12 px-2 font-mono text-sm font-semibold tabular-nums text-accent-text transition-colors after:absolute after:inset-0 after:rounded-lg after:content-[''] hover:bg-accent/8"
            onClick={() => onOpenStall(stall.id)}
            type="button"
          >
            {stall.code}
          </button>

          {/*
           * 261016: «Faol» — oddiy holat va har qatorda takrorlanib shovqin
           * edi. Belgi faqat ODATDAN tashqari holatda: ta'mirda, yopiq,
           * yarmarka.
           */}
          {stall.status === "active" ? null : <StallStatusBadge status={stall.status} />}
        </div>

        <div className="min-w-0">
          <p className="truncate text-xs text-text-muted" title={placeLabel}>
            {placeLabel}
          </p>
          <p className="truncate text-sm font-semibold" title={vendorLabel}>
            {vendorLabel}
          </p>
        </div>

        {/*
         * Bugungi tarif — YAGONA yo'qoladigan ustun va faqat `>1024px` da
         * ko'rinadi (§8.2). Summa `Intl` valyuta formatlagichi bilan
         * chiqadi: pul BIRLIGI tarjima katalogida takrorlanmaydi va uchala
         * tilda CLDR beradigan shaklda ko'rinadi.
         */}
        <div className="justify-self-start sm:justify-self-end">
          {day === null ? null : <DayPill day={day} />}
        </div>

        <p className="hidden font-mono text-sm font-semibold tabular-nums lg:block">
          <span className="sr-only">{t("stalls.tariffLabel")}: </span>
          {stall.tariff_soum === null
            ? t("stalls.noTariff")
            : formatSoum(format, stall.tariff_soum, locale)}
        </p>

        <div className="relative z-10 justify-self-end">
          {canManage ? (
            <StallRowActions
              onChangeCategory={() => onChangeCategory(stall)}
              onEditStall={() => onEditStall(stall)}
              stallCode={stall.code}
            />
          ) : null}
        </div>
      </div>
    </Card>
  );
}

/**
 * Qator amallari.
 *
 * ⚠ `stall_manage` YO'Q bo'lsa bu blok UMUMAN render qilinmaydi (yashirilmaydi)
 * — 1-fazadagi RBAC ko'zgusi naqshi. Bu XAVFSIZLIK CHEGARASI EMAS
 * (T-02-109): haqiqiy darvoza serverda, `require_permission` da.
 */
function StallRowActions({
  onChangeCategory,
  onEditStall,
  stallCode,
}: {
  onChangeCategory: () => void;
  onEditStall: () => void;
  stallCode: string;
}) {
  const t = useTranslations();

  return (
    <DropdownMenu.Root>
      {/* `min-h-11 min-w-11` — barmoq nishoni (WCAG 2.5.5, §2 istisnosi). */}
      <DropdownMenu.Trigger
        aria-label={`${t("stalls.actions")}: ${stallCode}`}
        className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-md border border-border bg-surface transition-colors hover:bg-surface-muted"
      >
        <Ellipsis aria-hidden="true" className="size-4" />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          className="z-50 mt-1 min-w-52 rounded-md border border-border bg-surface p-1 shadow-raised"
          sideOffset={4}
        >
          <DropdownMenu.Item
            className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
            onSelect={onEditStall}
          >
            <Pencil aria-hidden="true" className="size-4" />
            {t("stalls.edit")}
          </DropdownMenu.Item>

          {/*
           * Toifa ALOHIDA amal (D-04): u sanadan kuchga kiradi va oddiy
           * tahrir bilan almashtirilsa o'tmishdagi patta hisobi qayta
           * yozilardi. Shu sababli u tahrir formasida emas, o'z dialogida.
           */}
          <DropdownMenu.Item
            className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
            onSelect={onChangeCategory}
          >
            <CalendarClock aria-hidden="true" className="size-4" />
            {t("stalls.changeCategory")}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

/**
 * Bugungi to'lov holati — rangli yorliq + ikonka + so'z (261016).
 *
 * ⛔ Holat va qoldiq SERVERDAN (`state`, `remaining_soum`); klient faqat
 *    yozadi. Rang yolg'iz emas: ikonka va so'z bor.
 */
function DayPill({ day }: { day: MapDayRow }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  switch (day.state) {
    case "paid":
      return (
        <Badge className="gap-1" tone="success">
          <Check aria-hidden="true" className="size-3" />
          {t("map.tilePaid")}
        </Badge>
      );
    case "due":
      return (
        <Badge className="gap-1" tone="danger">
          <AlertCircle aria-hidden="true" className="size-3" />
          {t("map.tileDue")}
          {day.remaining_soum !== null && day.remaining_soum > 0
            ? ` · ${formatSoum(format, day.remaining_soum, locale)}`
            : ""}
        </Badge>
      );
    case "mismatch":
      return (
        <Badge className="gap-1" tone="warning">
          <TriangleAlert aria-hidden="true" className="size-3" />
          {t("map.tileMismatch")}
        </Badge>
      );
    case "free":
      return (
        <Badge className="gap-1" tone="muted">
          <Minus aria-hidden="true" className="size-3" />
          {t("map.tileFree")}
        </Badge>
      );
    case "fair":
      return (
        <Badge className="gap-1" tone="neutral">
          <Tent aria-hidden="true" className="size-3" />
          {t("director.stallFair")}
        </Badge>
      );
    case "no_billing":
      return <Badge tone="muted">{t("director.stallNoBilling")}</Badge>;
  }
}
