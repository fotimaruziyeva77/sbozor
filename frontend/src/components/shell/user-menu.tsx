"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { useMutation } from "@tanstack/react-query";
import { ChevronDown, LogOut } from "lucide-react";
import { useTranslations } from "next-intl";

import { useRouter } from "@/i18n/navigation";
import { apiFetch } from "@/lib/api-client";
import { emptyResponseSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import type { RoleLabelKey } from "@/lib/rbac";
import { roleLabelKey } from "@/lib/rbac";

/**
 * Foydalanuvchi menyusi: ism/telefon, rollar va chiqish.
 *
 * Rollar TARJIMA qilingan yorliqlar bilan ko'rsatiladi — xom `market_admin`
 * satri foydalanuvchiga hech qachon ko'rinmaydi.
 *
 * Endpoint: `POST /api/v1/auth/logout` -> 204.
 */
const LOGOUT_PATH = "/auth/logout";

export function UserMenu() {
  const t = useTranslations();
  const tRoles = useTranslations("roles");
  const router = useRouter();
  const { principal, clearSession } = useAuthStore();

  const logout = useMutation({
    mutationFn: () =>
      apiFetch(LOGOUT_PATH, { method: "POST", schema: emptyResponseSchema }),
    // Server javobidan QAT'I NAZAR sessiya tozalanadi: aks holda tarmoq
    // uzilganda brauzerda ishlaydigan token qolib ketardi.
    onSettled: () => {
      clearSession();
      router.replace("/login");
    },
  });

  if (!principal) return null;

  const roleLabels = principal.roles
    .map((role) => roleLabelKey(role))
    .filter((key): key is RoleLabelKey => key !== null)
    .map((key) => tRoles(key));

  // Profil `GET /api/v1/me` bilan to'ldiriladi; u yetib kelmagan bo'lsa
  // rol yorlig'i ko'rsatiladi — bo'sh tugma emas.
  const displayName =
    principal.fullName ?? principal.phone ?? roleLabels[0] ?? "";

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium transition-colors hover:bg-surface-muted">
        <span className="max-w-[10rem] truncate">{displayName}</span>
        <ChevronDown aria-hidden="true" className="size-4 text-text-muted" />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          className="z-50 mt-2 min-w-56 rounded-md border border-border bg-surface p-1 shadow-raised"
          sideOffset={4}
        >
          <DropdownMenu.Label className="px-3 py-2">
            <span className="block text-sm font-medium">{displayName}</span>
            {roleLabels.length > 0 ? (
              <span className="mt-0.5 block text-xs text-text-muted">
                {roleLabels.join(" · ")}
              </span>
            ) : null}
          </DropdownMenu.Label>

          <DropdownMenu.Separator className="my-1 h-px bg-border" />

          <DropdownMenu.Item
            className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm outline-none select-none data-[highlighted]:bg-surface-muted"
            disabled={logout.isPending}
            onSelect={() => logout.mutate()}
          >
            <LogOut aria-hidden="true" className="size-4" />
            {t("nav.logout")}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
