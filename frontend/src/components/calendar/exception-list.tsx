"use client";

import { useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Ellipsis, Trash2 } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import type { CalendarException } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useDeleteException } from "@/lib/market-queries";

/*
 * =============================================================================
 * Istisno kunlar ro'yxati (D-18).
 *
 * TARTIB — SANA BO'YICHA KAMAYISH: yaqin va kelayotgan kunlar tepada.
 * O'sish tartibida bir yillik ro'yxatning boshida o'tgan bayramlar
 * turardi-yu, admin qidirayotgan "kelasi dushanba" pastda qolardi.
 *
 * Sana `useFormatter()` bilan chiqadi — vaqt mintaqasi `i18n/request.ts`
 * da BITTA joyda (`Asia/Tashkent`) belgilangan. Qo'lda formatlash har
 * komponentda mintaqani qayta e'lon qilishga majbur qilardi va bir kun
 * kimdir UTC ko'rsatib, yozuvni noto'g'ri biznes-kunga bog'lardi
 * (FOUND-05).
 * =============================================================================
 */

export function ExceptionList({
  canManage,
  exceptions,
}: {
  canManage: boolean;
  exceptions: readonly CalendarException[];
}) {
  const t = useTranslations();
  const deleteException = useDeleteException();

  const [pendingDelete, setPendingDelete] = useState<CalendarException | null>(
    null,
  );
  const [actionError, setActionError] = useState<string | null>(null);

  /*
   * Nusxa ustida saralanadi: `exceptions` — so'rov keshidan kelgan massiv
   * va uni JOYIDA saralash keshdagi obyektni o'zgartirardi (TanStack Query
   * ma'lumotini mutatsiya qilish taqiqlangan).
   */
  const sorted = [...exceptions].sort((a, b) =>
    b.exception_date.localeCompare(a.exception_date),
  );

  async function confirmDelete() {
    if (pendingDelete === null) return;
    setActionError(null);
    try {
      await deleteException.mutateAsync(pendingDelete.id);
      setPendingDelete(null);
    } catch (error) {
      setActionError(t(marketErrorMessageKey(error)));
    }
  }

  if (sorted.length === 0) {
    return (
      <EmptyState
        className="py-8"
        description={t("calendar.emptyStateHint")}
        title={t("calendar.emptyState")}
      />
    );
  }

  return (
    <>
      <ul
        aria-label={t("calendar.exceptionsTitle")}
        className="flex flex-col gap-2"
      >
        {sorted.map((exception) => (
          <li key={exception.id}>
            <ExceptionRow
              canManage={canManage}
              exception={exception}
              onDelete={() => {
                setActionError(null);
                setPendingDelete(exception);
              }}
            />
          </li>
        ))}
      </ul>

      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={
          deleteException.isPending
            ? t("common.loading")
            : t("calendar.deleteException")
        }
        description={t("calendar.deleteExceptionConfirm")}
        isBusy={deleteException.isPending}
        onConfirm={() => void confirmDelete()}
        onOpenChange={(next) => {
          if (next) return;
          setPendingDelete(null);
          setActionError(null);
        }}
        open={pendingDelete !== null}
        title={t("calendar.deleteException")}
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
    </>
  );
}

function ExceptionRow({
  canManage,
  exception,
  onDelete,
}: {
  canManage: boolean;
  exception: CalendarException;
  onDelete: () => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  return (
    <Card className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="text-sm font-semibold tabular-nums">
          {formatBusinessDay(format, exception.exception_date, locale)}
        </span>

        {/* D-16: izoh DB kontenti — tarjima qilinmaydi. */}
        {exception.note !== null ? (
          <span className="truncate text-xs text-text-muted">
            {exception.note}
          </span>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {/*
         * Rang YAGONA signal emas (WCAG 1.4.1): badge har doim MATN
         * tashiydi, ya'ni holat rangsiz ham o'qiladi.
         */}
        <Badge tone={exception.is_open ? "success" : "muted"}>
          {exception.is_open
            ? t("calendar.badgeOpen")
            : t("calendar.badgeClosed")}
        </Badge>

        {canManage ? (
          <DropdownMenu.Root>
            <DropdownMenu.Trigger
              aria-label={t("calendar.actions")}
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
                <DropdownMenu.Item
                  className="flex min-h-11 cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
                  onSelect={onDelete}
                >
                  <Trash2 aria-hidden="true" className="size-4" />
                  {t("calendar.deleteException")}
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        ) : null}
      </div>
    </Card>
  );
}
