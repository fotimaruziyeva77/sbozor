"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Ban, CalendarClock, Ellipsis, Pencil, Wrench } from "lucide-react";
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
  onChangeCategory,
  onEditStall,
  onOpenStall,
  stall,
}: {
  canManage: boolean;
  onChangeCategory: (stall: StallListItem) => void;
  onEditStall: (stall: StallListItem) => void;
  onOpenStall: (stallId: string) => void;
  stall: StallListItem;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  // D-16: zona, toifa va sotuvchi nomi DB kontenti — TARJIMA QILINMAYDI.
  // Ular `truncate` bo'ladi va yoniga doim `title` qo'yiladi (§5.1 qoida 4).
  const categoryLabel = stall.category_name ?? t("stalls.categoryUnset");
  const placeLabel = `${stall.zone_name} · ${categoryLabel}`;
  const vendorLabel = stall.vendor_name ?? t("stalls.noVendor");

  return (
    <Card className="px-4 py-3">
      <div className="grid gap-1 sm:grid-cols-[auto_1fr_auto_auto] sm:items-center sm:gap-4">
        <div className="flex items-center justify-between gap-3 sm:justify-start">
          {/*
           * Raqamning O'ZI kartani ochadi. D-16: raqam DB kontenti.
           * `tabular-nums` — raqamlar tik ustunda tursin.
           */}
          <button
            className="rounded-sm font-mono text-sm font-semibold tabular-nums underline-offset-2 hover:underline"
            onClick={() => onOpenStall(stall.id)}
            type="button"
          >
            {stall.code}
          </button>

          <StallStatusBadge status={stall.status} />
        </div>

        <div className="min-w-0">
          <p className="truncate text-xs text-text-muted" title={placeLabel}>
            {placeLabel}
          </p>
          <p className="truncate text-sm" title={vendorLabel}>
            {vendorLabel}
          </p>
        </div>

        {/*
         * Bugungi tarif — YAGONA yo'qoladigan ustun va faqat `>1024px` da
         * ko'rinadi (§8.2). Summa `Intl` valyuta formatlagichi bilan
         * chiqadi: pul BIRLIGI tarjima katalogida takrorlanmaydi va uchala
         * tilda CLDR beradigan shaklda ko'rinadi.
         */}
        <p className="hidden text-sm tabular-nums lg:block">
          <span className="sr-only">{t("stalls.tariffLabel")}: </span>
          {stall.tariff_soum === null
            ? t("stalls.noTariff")
            : formatSoum(format, stall.tariff_soum, locale)}
        </p>

        <div className="justify-self-end">
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
