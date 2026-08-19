"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Ellipsis, Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { ZoneItem } from "@/lib/api-types";
import { marketErrorMessageKey } from "@/lib/market-errors";
import {
  useCreateZone,
  useDeleteZone,
  useUpdateZone,
  useZonesQuery,
} from "@/lib/market-queries";

/*
 * =============================================================================
 * Zonalar ro'yxati (D-03) — MUSTAQIL komponent, sahifaga bog'lanmagan.
 *
 * U ikki joyda ishlatiladi: `/tariffs` sahifasining yon panelida va
 * ustaning 2-qadamida (02-16). Shuning uchun u o'z sarlavhasini, o'z
 * qo'shish qatorini va o'z dialoglarini olib yuradi — chaqiruvchi faqat
 * huquqni uzatadi.
 *
 * QO'SHISH — INLINE QATOR, dialog EMAS. Element BITTA maydondan iborat
 * (nom), ya'ni dialog bitta matn maydoni uchun butun modal, fokus tuzog'i
 * va ikkita tugma qo'shardi. Usta 2-qadamida esa admin ketma-ket 5-10 ta
 * zona kiritadi va har biriga modal ochish oqimni sekinlashtirardi.
 *
 * TAHRIRLASH esa MODAL (UI-SPEC §8.4): nomni o'zgartirish serverda 409
 * (`zone_name_taken`) bilan RAD ETILISHI mumkin va inline maydonda o'sha
 * tushuntirishni qo'yadigan joy yo'q.
 *
 * O'CHIRISH — `ui/confirm-dialog` 1-darajasi. Server 409 `zone_in_use`
 * qaytarsa dialog YOPILMAYDI va sabab uning ichida ko'rinadi: yopilgan
 * dialog ortidagi xato "nega hech narsa bo'lmadi?" savolini qoldirardi.
 * =============================================================================
 */

const SKELETON_ROWS = [0, 1, 2];

export function ZoneList({ canManage }: { canManage: boolean }) {
  const t = useTranslations();
  const zonesQuery = useZonesQuery();
  const createZone = useCreateZone();
  const deleteZone = useDeleteZone();

  const [newName, setNewName] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ZoneItem | null>(null);
  const [pendingDelete, setPendingDelete] = useState<ZoneItem | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleAdd() {
    const name = newName.trim();
    if (name === "") {
      setAddError(t("errors.required"));
      return;
    }
    setAddError(null);
    try {
      await createZone.mutateAsync({ name });
      setNewName("");
    } catch (error) {
      setAddError(t(marketErrorMessageKey(error)));
    }
  }

  async function confirmDelete() {
    if (pendingDelete === null) return;
    setDeleteError(null);
    try {
      await deleteZone.mutateAsync(pendingDelete.id);
      setPendingDelete(null);
    } catch (error) {
      setDeleteError(t(marketErrorMessageKey(error)));
    }
  }

  let content: ReactNode;

  if (zonesQuery.isPending) {
    content = (
      <div aria-busy="true" className="flex flex-col gap-2" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        {SKELETON_ROWS.map((row) => (
          <Skeleton className="h-10 rounded-sm" key={row} />
        ))}
      </div>
    );
  } else if (zonesQuery.isError) {
    content = (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t(marketErrorMessageKey(zonesQuery.error))}
      </p>
    );
  } else if (zonesQuery.data.items.length === 0) {
    content = (
      <EmptyState
        className="py-6"
        description={t("zones.emptyStateHint")}
        title={t("zones.emptyState")}
      />
    );
  } else {
    content = (
      <ul aria-label={t("zones.title")} className="flex flex-col gap-1">
        {zonesQuery.data.items.map((zone) => (
          <li
            className="flex items-center justify-between gap-3 rounded-sm px-2 py-1.5 hover:bg-surface-muted"
            key={zone.id}
          >
            {/* D-16: zona nomi DB kontenti — tarjima qilinmaydi. */}
            <span className="truncate text-sm" title={zone.name}>
              {zone.name}
            </span>

            {/*
       * ⛔ `flex-wrap`, `shrink-0` YO'Q (260819): bu guruh badge va amal
       *    tugmalarini tutadi va ularning yig'indisi telefonda 375px dan
       *    OSHADI. `shrink-0` bilan u hech qachon siqilmasdi va BUTUN
       *    SAHIFANI cho'zib yuborardi — `/tariffs` da o'lchandi: sahifa
       *    413px, ekran 375px. Endi tor ekranda guruh ikki satrga
       *    bo'linadi; keng ekranda ko'rinish o'zgarmaydi.
       */}
      <span className="flex flex-wrap items-center justify-end gap-2">
              <Badge tone="muted">
                {t("zones.stallCount", { count: zone.stall_count })}
              </Badge>

              {canManage ? (
                <RowActions
                  deleteLabel={t("zones.delete")}
                  editLabel={t("zones.edit")}
                  label={`${t("zones.actions")}: ${zone.name}`}
                  onDelete={() => {
                    setDeleteError(null);
                    setPendingDelete(zone);
                  }}
                  onEdit={() => setEditing(zone)}
                />
              ) : null}
            </span>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <h2 className="text-lg font-semibold">{t("zones.title")}</h2>
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        {content}

        {canManage ? (
          <div className="flex flex-col gap-2 border-t border-border pt-3">
            <div className="flex items-end gap-2">
              <Field
                className="flex-1"
                error={addError ?? undefined}
                id="zone-new-name"
                label={t("zones.nameLabel")}
              >
                <Input
                  aria-describedby={
                    addError ? "zone-new-name-error" : undefined
                  }
                  aria-invalid={addError ? true : undefined}
                  autoComplete="off"
                  id="zone-new-name"
                  onChange={(event) => {
                    setNewName(event.target.value);
                    setAddError(null);
                  }}
                  /*
                   * `Enter` inline qatorni yuboradi — usta 2-qadamida
                   * admin ketma-ket zona kiritadi va har safar sichqonchaga
                   * o'tish oqimni uzardi. Forma EMAS: bu karta boshqa
                   * formalar ichida ham render bo'lishi mumkin (02-16) va
                   * ichma-ich `<form>` HTML'da yaroqsiz.
                   */
                  onKeyDown={(event) => {
                    if (event.key !== "Enter") return;
                    event.preventDefault();
                    void handleAdd();
                  }}
                  placeholder={t("zones.addPlaceholder")}
                  value={newName}
                />
              </Field>

              <Button
                className="mb-0.5"
                disabled={createZone.isPending}
                onClick={() => void handleAdd()}
                variant="secondary"
              >
                {createZone.isPending ? t("common.loading") : t("zones.add")}
              </Button>
            </div>
          </div>
        ) : null}
      </CardContent>

      {/*
       * `key` — dialog HAR ZONA uchun yangidan montaj qilinadi, ya'ni
       * boshlang'ich qiymat `useState(zone.name)` bilan beriladi va
       * effekt ichida `setState` qilinmaydi (kaskad renderlar).
       */}
      {canManage && editing !== null ? (
        <RenameDialog
          key={editing.id}
          onOpenChange={(next) => {
            if (!next) setEditing(null);
          }}
          zone={editing}
        />
      ) : null}

      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={
          deleteZone.isPending ? t("common.loading") : t("zones.delete")
        }
        description={t("zones.deleteConfirm")}
        isBusy={deleteZone.isPending}
        onConfirm={() => void confirmDelete()}
        onOpenChange={(next) => {
          if (next) return;
          setPendingDelete(null);
          setDeleteError(null);
        }}
        open={pendingDelete !== null}
        title={t("zones.delete")}
      >
        {pendingDelete ? (
          // D-16: zona nomi DB kontenti.
          <p className="rounded-sm bg-surface-muted px-3 py-2 text-sm font-semibold">
            {pendingDelete.name}
          </p>
        ) : null}

        {/*
         * 409 `zone_in_use` shu yerda ko'rinadi va dialog OCHIQ qoladi:
         * "bu zonada rastalar bor" — foydalanuvchi bajarishi kerak bo'lgan
         * keyingi qadamni aytadigan xabar, oddiy rad javobi emas.
         */}
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

/** Nomni o'zgartirish — modal (§8.4: 409 uchun joy kerak). */
function RenameDialog({
  onOpenChange,
  zone,
}: {
  onOpenChange: (open: boolean) => void;
  zone: ZoneItem;
}) {
  const t = useTranslations();
  const updateZone = useUpdateZone();
  const [name, setName] = useState(zone.name);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSave() {
    const trimmed = name.trim();
    if (trimmed === "") {
      setFormError(t("errors.required"));
      return;
    }
    setFormError(null);
    try {
      await updateZone.mutateAsync({ id: zone.id, name: trimmed });
      onOpenChange(false);
    } catch (caught) {
      setFormError(t(marketErrorMessageKey(caught)));
    }
  }

  return (
    <Dialog.Root onOpenChange={onOpenChange} open>
      <Dialog.Content
        description={t("zones.nameLabel")}
        size="md"
        srOnlyDescription
        title={t("zones.editTitle")}
      >
        <Field id="zone-rename" label={t("zones.nameLabel")}>
          <Input
            aria-invalid={formError ? true : undefined}
            autoComplete="off"
            id="zone-rename"
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
            disabled={updateZone.isPending}
            onClick={() => void handleSave()}
          >
            {updateZone.isPending ? t("common.loading") : t("common.save")}
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
  deleteLabel,
  editLabel,
  label,
  onDelete,
  onEdit,
}: {
  deleteLabel: string;
  editLabel: string;
  label: string;
  onDelete: () => void;
  onEdit: () => void;
}) {
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
            {editLabel}
          </DropdownMenu.Item>

          <DropdownMenu.Item className={MENU_ITEM_CLASS} onSelect={onDelete}>
            <Trash2 aria-hidden="true" className="size-4" />
            {deleteLabel}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
