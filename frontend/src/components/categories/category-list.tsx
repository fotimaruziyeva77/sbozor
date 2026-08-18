"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Ellipsis, Pencil, Trash2 } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { CategoryItem } from "@/lib/api-types";
import { formatAmount } from "@/lib/format-number";
import { marketErrorMessageKey } from "@/lib/market-errors";
import {
  useCategoriesQuery,
  useCreateCategory,
  useDeleteCategory,
  useUpdateCategory,
} from "@/lib/market-queries";

/*
 * =============================================================================
 * Toifalar ro'yxati (D-05) — `zone-list.tsx` bilan BIR XIL shakl.
 *
 * Ikki joyda ishlatiladi: `/tariffs` yon panelida va ustaning 3-qadamida
 * (02-16), shuning uchun u sahifaga bog'lanmagan.
 *
 * FARQI BITTA, LEKIN MUHIM: har toifa yonida uning BUGUNGI narxi
 * (`current_tariff_soum`) ko'rinadi va u `null` bo'lsa ogohlantirish
 * chiqadi (D-08). `null` — MA'NOLI holat, nuqson emas: toifa bor, narx
 * yo'q. Backend `0` qaytarMAYDI, chunki nol "bepul toifa" degan yolg'on
 * ma'no berardi.
 *
 * NEGA OGOHLANTIRISH KERAK: tarifsiz toifadagi rastaga kunlik patta
 * HISOBLANMAYDI. Bu 6-fazada anomaliyaga aylanadi, lekin uni AYNAN shu
 * ekranda ko'rsatish arzon — admin bu yerda narx qo'shishi mumkin.
 * =============================================================================
 */

const SKELETON_ROWS = [0, 1, 2];

export function CategoryList({ canManage }: { canManage: boolean }) {
  const t = useTranslations();
  const categoriesQuery = useCategoriesQuery();
  const createCategory = useCreateCategory();
  const deleteCategory = useDeleteCategory();

  const [newName, setNewName] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [editing, setEditing] = useState<CategoryItem | null>(null);
  const [pendingDelete, setPendingDelete] = useState<CategoryItem | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleAdd() {
    const name = newName.trim();
    if (name === "") {
      setAddError(t("errors.required"));
      return;
    }
    setAddError(null);
    try {
      await createCategory.mutateAsync({ name });
      setNewName("");
    } catch (error) {
      setAddError(t(marketErrorMessageKey(error)));
    }
  }

  async function confirmDelete() {
    if (pendingDelete === null) return;
    setDeleteError(null);
    try {
      await deleteCategory.mutateAsync(pendingDelete.id);
      setPendingDelete(null);
    } catch (error) {
      setDeleteError(t(marketErrorMessageKey(error)));
    }
  }

  let content: ReactNode;

  if (categoriesQuery.isPending) {
    content = (
      <div aria-busy="true" className="flex flex-col gap-2" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        {SKELETON_ROWS.map((row) => (
          <Skeleton className="h-10 rounded-sm" key={row} />
        ))}
      </div>
    );
  } else if (categoriesQuery.isError) {
    content = (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t(marketErrorMessageKey(categoriesQuery.error))}
      </p>
    );
  } else if (categoriesQuery.data.items.length === 0) {
    content = (
      <EmptyState
        className="py-6"
        description={t("categories.emptyStateHint")}
        title={t("categories.emptyState")}
      />
    );
  } else {
    content = (
      <ul aria-label={t("categories.title")} className="flex flex-col gap-1">
        {categoriesQuery.data.items.map((category) => (
          <li key={category.id}>
            <CategoryRow
              canManage={canManage}
              category={category}
              onDelete={() => {
                setDeleteError(null);
                setPendingDelete(category);
              }}
              onEdit={() => setEditing(category)}
            />
          </li>
        ))}
      </ul>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <h2 className="text-lg font-semibold">{t("categories.title")}</h2>
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        {content}

        {/*
         * QO'SHISH — INLINE, dialog EMAS: element bitta maydondan iborat
         * va usta 3-qadamida admin ketma-ket bir nechta toifa kiritadi.
         */}
        {canManage ? (
          <div className="flex items-end gap-2 border-t border-border pt-3">
            <Field
              className="flex-1"
              error={addError ?? undefined}
              id="category-new-name"
              label={t("categories.nameLabel")}
            >
              <Input
                aria-describedby={
                  addError ? "category-new-name-error" : undefined
                }
                aria-invalid={addError ? true : undefined}
                autoComplete="off"
                id="category-new-name"
                onChange={(event) => {
                  setNewName(event.target.value);
                  setAddError(null);
                }}
                onKeyDown={(event) => {
                  if (event.key !== "Enter") return;
                  event.preventDefault();
                  void handleAdd();
                }}
                placeholder={t("categories.addPlaceholder")}
                value={newName}
              />
            </Field>

            <Button
              className="mb-0.5"
              disabled={createCategory.isPending}
              onClick={() => void handleAdd()}
              variant="secondary"
            >
              {createCategory.isPending
                ? t("common.loading")
                : t("categories.add")}
            </Button>
          </div>
        ) : null}
      </CardContent>

      {canManage && editing !== null ? (
        <RenameDialog
          category={editing}
          key={editing.id}
          onOpenChange={(next) => {
            if (!next) setEditing(null);
          }}
        />
      ) : null}

      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={
          deleteCategory.isPending
            ? t("common.loading")
            : t("categories.delete")
        }
        description={t("categories.deleteConfirm")}
        isBusy={deleteCategory.isPending}
        onConfirm={() => void confirmDelete()}
        onOpenChange={(next) => {
          if (next) return;
          setPendingDelete(null);
          setDeleteError(null);
        }}
        open={pendingDelete !== null}
        title={t("categories.delete")}
      >
        {pendingDelete ? (
          // D-16: toifa nomi DB kontenti.
          <p className="rounded-sm bg-surface-muted px-3 py-2 text-sm font-semibold">
            {pendingDelete.name}
          </p>
        ) : null}

        {/* 409 `category_in_use` — dialog OCHIQ qoladi va sabab ko'rinadi. */}
        {deleteError ? (
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {deleteError}
          </p>
        ) : null}
      </ConfirmDialog>
    </Card>
  );
}

function CategoryRow({
  canManage,
  category,
  onDelete,
  onEdit,
}: {
  canManage: boolean;
  category: CategoryItem;
  onDelete: () => void;
  onEdit: () => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  return (
    <div className="flex items-center justify-between gap-3 rounded-sm px-2 py-1.5 hover:bg-surface-muted">
      <div className="flex min-w-0 flex-col">
        {/* D-16: toifa nomi DB kontenti — tarjima qilinmaydi. */}
        <span className="truncate text-sm" title={category.name}>
          {category.name}
        </span>

        {/*
         * D-08: narx yo'q -> ogohlantirish. Rang YAGONA signal emas —
         * matnning o'zi holatni aytadi (WCAG 1.4.1).
         */}
        {category.current_tariff_soum === null ? (
          <span className="text-xs text-danger-text">
            {t("stalls.noTariff")}
          </span>
        ) : (
          <span className="text-xs text-text-muted tabular-nums">
            {formatAmount(format, category.current_tariff_soum, locale)}{" "}
            {t("tariffs.amountUnit")}
          </span>
        )}
      </div>

      <span className="flex shrink-0 items-center gap-2">
        <Badge tone="muted">
          {t("categories.stallCount", { count: category.stall_count })}
        </Badge>

        {canManage ? (
          <RowActions
            label={`${t("categories.actions")}: ${category.name}`}
            onDelete={onDelete}
            onEdit={onEdit}
          />
        ) : null}
      </span>
    </div>
  );
}

/** Nomni o'zgartirish — modal (§8.4: 409 `category_name_taken` uchun joy). */
function RenameDialog({
  category,
  onOpenChange,
}: {
  category: CategoryItem;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations();
  const updateCategory = useUpdateCategory();
  const [name, setName] = useState(category.name);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSave() {
    const trimmed = name.trim();
    if (trimmed === "") {
      setFormError(t("errors.required"));
      return;
    }
    setFormError(null);
    try {
      await updateCategory.mutateAsync({ id: category.id, name: trimmed });
      onOpenChange(false);
    } catch (error) {
      setFormError(t(marketErrorMessageKey(error)));
    }
  }

  return (
    <Dialog.Root onOpenChange={onOpenChange} open>
      <Dialog.Content
        description={t("categories.nameLabel")}
        size="md"
        srOnlyDescription
        title={t("categories.editTitle")}
      >
        <Field id="category-rename" label={t("categories.nameLabel")}>
          <Input
            aria-invalid={formError ? true : undefined}
            autoComplete="off"
            id="category-rename"
            onChange={(event) => {
              setName(event.target.value);
              setFormError(null);
            }}
            value={name}
          />
        </Field>

        {formError ? (
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {formError}
          </p>
        ) : null}

        <Dialog.Footer>
          <Button
            className="sm:flex-1"
            disabled={updateCategory.isPending}
            onClick={() => void handleSave()}
          >
            {updateCategory.isPending ? t("common.loading") : t("common.save")}
          </Button>
          <Dialog.Close asChild>
            <Button className="sm:flex-1" variant="secondary">
              {t("common.cancel")}
            </Button>
          </Dialog.Close>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog.Root>
  );
}

const MENU_ITEM_CLASS =
  "flex min-h-11 cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted";

function RowActions({
  label,
  onDelete,
  onEdit,
}: {
  label: string;
  onDelete: () => void;
  onEdit: () => void;
}) {
  const t = useTranslations();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        aria-label={label}
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
            {t("categories.edit")}
          </DropdownMenu.Item>

          <DropdownMenu.Item className={MENU_ITEM_CLASS} onSelect={onDelete}>
            <Trash2 aria-hidden="true" className="size-4" />
            {t("categories.delete")}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
