"use client";

import { useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { KeyRound, Lock, MoreHorizontal, Unlock, UserCog } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { EditRolesDialog } from "@/components/users/edit-roles-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import type { UserListItem } from "@/lib/api-types";
import { assignableRoles } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import {
  adminErrorMessageKey,
  useBlockUser,
  useResetPassword,
  useUnblockUser,
  useUsersQuery,
} from "@/lib/queries";
import type { RoleLabelKey } from "@/lib/rbac";
import { hasPermission, roleLabelKey } from "@/lib/rbac";

/*
 * Foydalanuvchilar ro'yxati — KARTA ko'rinishida (topshiriq §7: "jadval
 * emas — kartalar va toza ro'yxatlar"). Jadval telefon ekranida gorizontal
 * skroll talab qilardi va bozor admini bu ekranni ko'pincha telefonda ochadi.
 *
 * DIQQAT: amallar `USER_MANAGE` bo'lmasa RENDER QILINMAYDI. Bu — UI ko'zgusi
 * (T-01-62): direktorda `USER_VIEW` bor, `USER_MANAGE` yo'q (D-07), ya'ni u
 * ro'yxatni ko'radi, lekin bloklash/tiklash tugmalarini umuman ko'rmaydi.
 * Yashirilgan so'rovni qo'lda yuborgan foydalanuvchi serverda 403 oladi.
 */

type PendingAction = {
  kind: "block" | "unblock" | "reset";
  user: UserListItem;
};

/**
 * Rol bandi ko'rinadimi — SERVER DARVOZASINING KO'ZGUSI (Topilma №G).
 *
 * IKKI SHART VA IKKALASINING SABABI BOSHQA:
 *
 *   (a) O'Z QATORI EMAS. Server buni 400 `cannot_change_own_roles` bilan
 *       rad etadi, ya'ni bandning bu qatorda HECH QANDAY muvaffaqiyat
 *       yo'li yo'q — u o'lik affordans bo'lardi (Topilma №F bilan aynan
 *       bir xil sinf).
 *
 *       ⚠ «Bloklash» esa YASHIRILMAYDI va farq ataylab: uning
 *         muvaffaqiyat yo'li BOR (boshqa qatorda), o'z qatorida esa
 *         server sababni aytadi. Yashirish «bu amal umuman yo'q» degan
 *         yolg'on berardi.
 *
 *   (b) NISHONNING JORIY ROLLARI CHAQIRUVCHI BERA OLADIGAN TO'PLAM
 *       ICHIDA. Bu server endpointidagi 3-darvozaning (JORIY rollar)
 *       ko'zgusi: bozor admini teng adminni yoki direktorni pasaytira
 *       olmaydi va urinishi 403 bilan qaytardi.
 *
 * ⛔ BU TEKSHIRUV DARVOZANING TAKRORI EMAS — haqiqiy qaror hamon
 *    serverda (`users.py::update_user_roles`). Bu yerdagisi faqat
 *    bosilganda 403 beradigan bandni ekranga chiqarmaslik uchun.
 */
function canEditRolesOf(
  user: UserListItem,
  selfUserId: string | null,
  isPlatformAdmin: boolean,
): boolean {
  if (selfUserId !== null && user.id === selfUserId) return false;
  const allowed = new Set<string>(assignableRoles(isPlatformAdmin));
  return user.roles.every((role) => allowed.has(role));
}

export function UserList({
  onTemporaryPassword,
}: {
  /**
   * Parol tiklashdan keyingi bir martalik parol. Ro'yxat uni O'ZI
   * ko'rsatmaydi — dialogni ota-komponent boshqaradi, ya'ni parol bitta
   * joyda tug'iladi va bitta joyda tozalanadi (T-01-68).
   */
  onTemporaryPassword: (temporaryPassword: string) => void;
}) {
  const t = useTranslations();
  const usersQuery = useUsersQuery();
  const { principal } = useAuthStore();
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  /*
   * ⛔ `PendingAction["kind"]` GA QO'SHILMAYDI: rol tahriri tasdiq
   *    dialogi emas, ALOHIDA forma. Uni `ConfirmDialog` mashinasiga
   *    tiqish `confirmTitle`/`confirmQuestion` shoxlarini uchinchi
   *    holatga majburlardi va o'sha holat matn emas, forma talab qiladi.
   */
  const [rolesFor, setRolesFor] = useState<UserListItem | null>(null);

  const blockUser = useBlockUser();
  const unblockUser = useUnblockUser();
  const resetPassword = useResetPassword();

  const canManage = hasPermission(principal?.roles ?? [], "user_manage");

  async function confirmPending() {
    if (!pending) return;
    setActionError(null);
    try {
      if (pending.kind === "block") {
        await blockUser.mutateAsync(pending.user.id);
      } else if (pending.kind === "unblock") {
        await unblockUser.mutateAsync(pending.user.id);
      } else {
        const result = await resetPassword.mutateAsync(pending.user.id);
        onTemporaryPassword(result.temporary_password);
      }
      setPending(null);
    } catch (error) {
      setActionError(t(adminErrorMessageKey(error)));
    }
  }

  if (usersQuery.isPending) {
    return (
      <p className="text-sm text-text-muted" role="status">
        {t("common.loading")}
      </p>
    );
  }

  if (usersQuery.isError) {
    return (
      <p className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text" role="alert">
        {t(adminErrorMessageKey(usersQuery.error))}
      </p>
    );
  }

  const items = usersQuery.data.items;

  if (items.length === 0) {
    return (
      <EmptyState
        description={t("users.emptyStateHint")}
        title={t("users.emptyState")}
      />
    );
  }

  const isBusy =
    blockUser.isPending || unblockUser.isPending || resetPassword.isPending;

  /*
   * Sarlavha va savol SHU YERDA hisoblanadi: `ui/confirm-dialog` — umumiy
   * primitiv va unda foydalanuvchiga ko'rinadigan matn bo'lmaydi.
   */
  const confirmTitle =
    pending === null
      ? ""
      : pending.kind === "block"
        ? t("users.block")
        : pending.kind === "unblock"
          ? t("users.unblock")
          : t("users.resetPassword");

  const confirmQuestion =
    pending === null
      ? ""
      : pending.kind === "reset"
        ? t("users.confirmReset")
        : pending.kind === "block"
          ? t("users.confirmBlock")
          : t("users.confirmUnblock");

  return (
    <>
      <ul aria-label={t("users.title")} className="flex flex-col gap-3">
        {items.map((user) => (
          <li key={user.id}>
            <UserCard
              canEditRoles={canEditRolesOf(
                user,
                principal?.userId ?? null,
                principal?.isPlatformAdmin ?? false,
              )}
              canManage={canManage}
              onAction={(kind) => {
                setActionError(null);
                setPending({ kind, user });
              }}
              onEditRoles={() => setRolesFor(user)}
              user={user}
            />
          </li>
        ))}
      </ul>

      {/*
       * Bloklash va parol tiklash QAYTARIB BO'LMAYDIGAN yon ta'sirga ega
       * (bloklash darhol kuchga kiradi, tiklash foydalanuvchining barcha
       * sessiyalarini bekor qiladi) — shuning uchun bir bosishda
       * bajarilmaydi. `unblock` esa TIKLOVCHI amal, shu sababli uning
       * tugmasi qizil EMAS.
       */}
      <ConfirmDialog
        cancelLabel={t("common.cancel")}
        confirmLabel={isBusy ? t("common.loading") : t("users.confirm")}
        confirmVariant={pending?.kind === "block" ? "destructive" : "default"}
        description={confirmQuestion}
        isBusy={isBusy}
        onConfirm={() => void confirmPending()}
        onOpenChange={(next) => {
          if (next) return;
          setPending(null);
          setActionError(null);
        }}
        open={pending !== null}
        title={confirmTitle}
      >
        {/* D-16: ism/telefon DB kontenti — tarjima qilinmaydi. */}
        {pending ? (
          <p className="rounded-sm bg-surface-muted px-3 py-2 text-sm font-semibold">
            {pending.user.full_name ?? pending.user.phone}
          </p>
        ) : null}

        {actionError ? (
          <p
            className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
            role="alert"
          >
            {actionError}
          </p>
        ) : null}
      </ConfirmDialog>

      {/*
       * Rol tahriri — `ConfirmDialog` YONIDA, uning ICHIDA emas: bu amal
       * tasdiq emas, forma (yuqoridagi `rolesFor` izohi).
       */}
      <EditRolesDialog
        onOpenChange={(next) => {
          if (!next) setRolesFor(null);
        }}
        open={rolesFor !== null}
        user={rolesFor}
      />
    </>
  );
}

function UserCard({
  canEditRoles,
  canManage,
  onAction,
  onEditRoles,
  user,
}: {
  canEditRoles: boolean;
  canManage: boolean;
  onAction: (kind: PendingAction["kind"]) => void;
  onEditRoles: () => void;
  user: UserListItem;
}) {
  const t = useTranslations();
  const tRoles = useTranslations("roles");
  const format = useFormatter();

  const roleLabels = user.roles
    .map((role) => roleLabelKey(role))
    .filter((key): key is RoleLabelKey => key !== null)
    .map((key) => tRoles(key));

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3 pb-2">
        <div className="min-w-0">
          {/* D-16: ism va telefon DB kontenti — tarjima qilinmaydi. */}
          <p className="truncate text-lg font-semibold">
            {user.full_name ?? user.phone}
          </p>
          <p className="truncate text-sm text-text-muted">{user.phone}</p>
        </div>

        {canManage ? (
          <UserActions
            canEditRoles={canEditRoles}
            isActive={user.is_active}
            onAction={onAction}
            onEditRoles={onEditRoles}
            userLabel={user.full_name ?? user.phone}
          />
        ) : null}
      </CardHeader>

      <CardContent className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {user.is_active ? (
            <Badge tone="success">{t("users.statusActive")}</Badge>
          ) : (
            <Badge tone="danger">{t("users.statusBlocked")}</Badge>
          )}
          {user.must_change_password ? (
            <Badge tone="warning">{t("users.statusMustChange")}</Badge>
          ) : null}
        </div>

        {roleLabels.length > 0 ? (
          <p className="text-sm text-text-muted">
            {t("users.rolesLabel")}: {roleLabels.join(" · ")}
          </p>
        ) : null}

        <p className="text-xs text-text-muted">
          {t("users.createdAt")}:{" "}
          {format.dateTime(new Date(user.created_at), {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </p>
      </CardContent>
    </Card>
  );
}

function UserActions({
  canEditRoles,
  isActive,
  onAction,
  onEditRoles,
  userLabel,
}: {
  canEditRoles: boolean;
  isActive: boolean;
  onAction: (kind: PendingAction["kind"]) => void;
  onEditRoles: () => void;
  userLabel: string;
}) {
  const t = useTranslations();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        aria-label={`${t("users.actions")}: ${userLabel}`}
        className="inline-flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-surface transition-colors hover:bg-surface-muted"
      >
        <MoreHorizontal aria-hidden="true" className="size-4" />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          className="z-50 mt-1 min-w-48 rounded-md border border-border bg-surface p-1 shadow-raised"
          sideOffset={4}
        >
          <DropdownMenu.Item
            className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
            onSelect={() => onAction(isActive ? "block" : "unblock")}
          >
            {isActive ? (
              <Lock aria-hidden="true" className="size-4" />
            ) : (
              <Unlock aria-hidden="true" className="size-4" />
            )}
            {isActive ? t("users.block") : t("users.unblock")}
          </DropdownMenu.Item>

          {canEditRoles ? (
            <DropdownMenu.Item
              className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
              onSelect={onEditRoles}
            >
              <UserCog aria-hidden="true" className="size-4" />
              {t("users.editRoles")}
            </DropdownMenu.Item>
          ) : null}

          <DropdownMenu.Item
            className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
            onSelect={() => onAction("reset")}
          >
            <KeyRound aria-hidden="true" className="size-4" />
            {t("users.resetPassword")}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
