"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Ellipsis, Pencil, Plus, Trash2 } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { TariffDialog } from "@/components/tariffs/tariff-dialog";
import type { TariffItem } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { formatAmount } from "@/lib/format-number";
import { marketErrorMessageKey } from "@/lib/market-errors";
import {
  useCategoriesQuery,
  useDeleteTariff,
  useTariffsQuery,
} from "@/lib/market-queries";

/*
 * =============================================================================
 * Tarif TARIXI — toifa bo'yicha guruhlangan qatorlar (D-06/D-07).
 *
 * TARIF APPEND-ONLY: narx "o'zgartirilmaydi", yangi sanadan YANGI qator
 * qo'shiladi. Shuning uchun bu ekran tahrir formasi emas, TARIX: har qator
 * "qaysi narx qachondan qachongacha amal qilgan" savoliga javob beradi va
 * kunlik patta hisobining asosi shu.
 *
 * ⚠ O'TGAN QATORDA TAHRIR/O'CHIRISH TUGMALARI RENDER QILINMAYDI, LEKIN BU
 * DARVOZA EMAS — QULAYLIK. Haqiqiy qulf DB triggerida
 * (`trg_tariff_past_immutable`) va server o'tgan qatorga har qanday yozuvni
 * 403 `tariff_past_locked` bilan rad etadi (matni — `tariffs.pastLocked`).
 * Ikkisining ROLI boshqa: bu yerdagisi foydalanuvchini bajarilmaydigan
 * amaldan saqlaydi, serverdagisi esa ma'lumotni himoya qiladi. Keyingi
 * ishlovchi "tekshiruv frontendda bor" deb serverdagisini OLIB TASHLAMASIN
 * — DevTools bilan bu shartni o'chirish bir necha soniyalik ish.
 *
 * `valid_to` DB'da USTUN EMAS — u keyingi qatordan hisoblanadi va oxirgi
 * qator uchun `null` ("hozircha amalda").
 * =============================================================================
 */

const SKELETON_ROWS = [0, 1, 2];

export function TariffList({
  canManage,
  categoryFilter,
  createOpen,
  onCreateOpenChange,
}: {
  canManage: boolean;
  /** `nuqs` dagi `category` filtri; bo'sh satr — filtr qo'yilmagan. */
  categoryFilter: string;
  createOpen: boolean;
  onCreateOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations();
  const tariffsQuery = useTariffsQuery(
    categoryFilter === "" ? null : categoryFilter,
  );
  const categoriesQuery = useCategoriesQuery();
  const deleteTariff = useDeleteTariff();

  const [editing, setEditing] = useState<TariffItem | null>(null);
  const [pendingDelete, setPendingDelete] = useState<TariffItem | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function confirmDelete() {
    if (pendingDelete === null) return;
    setActionError(null);
    try {
      await deleteTariff.mutateAsync(pendingDelete.id);
      setPendingDelete(null);
    } catch (error) {
      // Dialog OCHIQ qoladi: xato aynan shu amalga tegishli va uni
      // yopilgan dialog ortida ko'rsatish sababni yo'qotardi.
      setActionError(t(marketErrorMessageKey(error)));
    }
  }

  let content: ReactNode;

  if (tariffsQuery.isPending) {
    content = (
      <div aria-busy="true" className="flex flex-col gap-3" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        {SKELETON_ROWS.map((row) => (
          <Skeleton className="h-24 rounded-lg" key={row} />
        ))}
      </div>
    );
  } else if (tariffsQuery.isError) {
    content = (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t(marketErrorMessageKey(tariffsQuery.error))}
      </p>
    );
  } else if (tariffsQuery.data.items.length === 0) {
    content = (
      <EmptyState
        action={
          canManage ? (
            <Button onClick={() => onCreateOpenChange(true)}>
              <Plus aria-hidden="true" />
              {t("tariffs.create")}
            </Button>
          ) : null
        }
        description={t("tariffs.emptyStateHint")}
        title={t("tariffs.emptyState")}
      />
    );
  } else {
    content = (
      <div className="flex flex-col gap-6">
        {groupByCategory(tariffsQuery.data.items).map((group) => (
          <section className="flex flex-col gap-2" key={group.categoryId}>
            {/* D-16: toifa nomi DB kontenti — tarjima qilinmaydi. */}
            <h3 className="text-sm font-semibold text-text-muted">
              {group.categoryName}
            </h3>

            <ul className="flex flex-col gap-2">
              {group.items.map((item) => (
                <li key={item.id}>
                  <TariffRow
                    canManage={canManage}
                    onDelete={() => {
                      setActionError(null);
                      setPendingDelete(item);
                    }}
                    onEdit={() => setEditing(item)}
                    tariff={item}
                  />
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {content}

      {canManage && tariffsQuery.data ? (
        <>
          <TariffDialog
            categories={categoriesQuery.data?.items ?? []}
            /*
             * ⚠ `min_valid_from` JAVOBDAN TO'G'RIDAN-TO'G'RI uzatiladi.
             * Bu yerda `??` yoki `||` bilan zaxira qiymat berilmaydi —
             * sxemada u MAJBURIY va uni "to'ldirish" qoralama bozorda
             * ustaning 4-qadamini bajarilmas qilardi (T-02-119a).
             */
            minValidFrom={tariffsQuery.data.min_valid_from}
            onOpenChange={onCreateOpenChange}
            open={createOpen}
            tariff={null}
          />
          <TariffDialog
            categories={categoriesQuery.data?.items ?? []}
            minValidFrom={tariffsQuery.data.min_valid_from}
            onOpenChange={(next) => {
              if (!next) setEditing(null);
            }}
            open={editing !== null}
            tariff={editing}
          />
        </>
      ) : null}

      {/*
       * §10.6 D-3: kelajakdagi tarifni o'chirish — 1-darajali tasdiq.
       * Tugma yorlig'i O'Z FE'LI ("Tarifni o'chirish"), generic
       * "Tasdiqlash" emas: foydalanuvchi ko'pincha dialog matnini o'qimasdan
       * tugmaga qarab qaror qiladi.
       */}
      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={
          deleteTariff.isPending
            ? t("common.loading")
            : t("tariffs.deleteAction")
        }
        description={t("tariffs.deleteConfirm")}
        isBusy={deleteTariff.isPending}
        onConfirm={() => void confirmDelete()}
        onOpenChange={(next) => {
          if (next) return;
          setPendingDelete(null);
          setActionError(null);
        }}
        open={pendingDelete !== null}
        title={t("tariffs.deleteAction")}
      >
        {actionError ? (
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {actionError}
          </p>
        ) : null}
      </ConfirmDialog>
    </div>
  );
}

type TariffGroup = {
  categoryId: string;
  categoryName: string;
  items: TariffItem[];
};

/**
 * Qatorlarni toifa bo'yicha guruhlaydi, SERVER TARTIBINI saqlagan holda.
 *
 * Qayta SARALASH yo'q: tartib serverda hal qilingan va uni klientda
 * takrorlash uchala tilda boshqa natija berardi (`market-queries.ts`
 * dagi bir xil qoida).
 */
function groupByCategory(items: readonly TariffItem[]): TariffGroup[] {
  const groups = new Map<string, TariffGroup>();

  for (const item of items) {
    const group = groups.get(item.category_id);
    if (group) {
      group.items.push(item);
    } else {
      groups.set(item.category_id, {
        categoryId: item.category_id,
        categoryName: item.category_name,
        items: [item],
      });
    }
  }

  return [...groups.values()];
}

/**
 * Qatorning yorlig'i — ⛔ SERVERNING `is_past` BAYROG'IDAN, sanadan EMAS.
 *
 * =============================================================================
 * ⛔⛔ TARTIB AHAMIYATLI VA U TOPILMANING O'ZI (№E, quick 260816-75c).
 *
 * KELAJAK sharti BIRINCHI tekshiriladi, chunki kelajakdagi qator HAM
 * `valid_to === null` bo'lishi mumkin (u oxirgi qator). Aynan shu
 * ustma-uslik bugungi nuqsonni tug'dirgan: 2026-09-01 dan boshlanadigan
 * tarif «Hozircha amalda» deb yorliqlangan edi, ya'ni ekran KELAJAKNI
 * HOZIR deb ko'rsatardi.
 *
 * ⛔ `new Date()` BILAN SOLISHTIRISH YO'Q. Server `is_past` ni
 *    `valid_from <= business_today()` (Asia/Tashkent) deb hisoblaydi;
 *    brauzer mintaqasi undan farq qilsa yarim tunda ikki ekran ikki xil
 *    yorliq ko'rsatardi — «ikki haqiqat manbai».
 * =============================================================================
 */
export function tariffRowBadge(
  tariff: Pick<TariffItem, "is_past" | "valid_to">,
): "current" | "future" | null {
  if (!tariff.is_past) return "future";
  if (tariff.valid_to === null) return "current";
  return null;
}

export function TariffRow({
  canManage,
  onDelete,
  onEdit,
  tariff,
}: {
  canManage: boolean;
  onDelete: () => void;
  onEdit: () => void;
  tariff: TariffItem;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  const validFrom = formatBusinessDay(format, tariff.valid_from, locale);
  const validTo =
    tariff.valid_to === null
      ? t("tariffs.openEnded")
      : formatBusinessDay(format, tariff.valid_to, locale);
  const badge = tariffRowBadge(tariff);

  return (
    <Card className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="flex min-w-0 flex-col gap-0.5">
        <p className="text-base font-semibold tabular-nums">
          {formatAmount(format, tariff.amount_soum, locale)} {t("tariffs.amountUnit")}
        </p>
        <p className="text-xs text-text-muted tabular-nums">
          <span className="sr-only">{t("tariffs.periodLabel")}: </span>
          {validFrom} — {validTo}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {/*
         * ⛔ Rang YOLG'IZ signal emas (§12.4): yorliq har ikkala shoxda
         *    ham MATN tashiydi, shuning uchun ikonka qo'shilmaydi.
         *
         * ⚠ Sana `validFrom` DAN — qator davri bilan AYNI formatterdan.
         *   Ikkinchi formatlash yozilsa yorliqdagi sana davrdagi sanadan
         *   bir kun farq qila boshlardi.
         */}
        {badge === "current" ? (
          <Badge tone="success">{t("tariffs.openEnded")}</Badge>
        ) : badge === "future" ? (
          <Badge tone="warning">
            {t("tariffs.startsOn", { date: validFrom })}
          </Badge>
        ) : null}

        {/*
         * O'TGAN QATOR: amallar menyusi O'RNIGA sabab matni turadi.
         * Tugmani `disabled` qilish emas, UMUMAN chizmaslik — o'chirilgan
         * tugma "nega bosilmayapti?" savolini tug'diradi, matn esa javob
         * beradi.
         */}
        {tariff.is_past ? (
          <p className="text-xs text-text-muted">{t("tariffs.pastRowHint")}</p>
        ) : canManage ? (
          <TariffActions onDelete={onDelete} onEdit={onEdit} />
        ) : null}
      </div>
    </Card>
  );
}

const MENU_ITEM_CLASS =
  "flex min-h-11 cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted";

function TariffActions({
  onDelete,
  onEdit,
}: {
  onDelete: () => void;
  onEdit: () => void;
}) {
  const t = useTranslations();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        aria-label={t("tariffs.actions")}
        className="inline-flex size-11 shrink-0 items-center justify-center rounded-md border border-border-ui bg-surface transition-colors hover:bg-surface-muted"
      >
        <Ellipsis aria-hidden="true" className="size-4" />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          className="z-50 mt-1 min-w-48 rounded-md border border-border bg-surface p-1 shadow-raised"
          sideOffset={4}
        >
          <DropdownMenu.Item className={MENU_ITEM_CLASS} onSelect={onEdit}>
            <Pencil aria-hidden="true" className="size-4" />
            {t("tariffs.edit")}
          </DropdownMenu.Item>

          <DropdownMenu.Item className={MENU_ITEM_CLASS} onSelect={onDelete}>
            <Trash2 aria-hidden="true" className="size-4" />
            {t("tariffs.deleteAction")}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
