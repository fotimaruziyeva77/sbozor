"use client";

import { LayoutDashboard, ScrollText, Users } from "lucide-react";
import { useTranslations } from "next-intl";

import { LocaleSwitcher } from "@/components/shell/locale-switcher";
import { UserMenu } from "@/components/shell/user-menu";
import { Link, usePathname } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { cn } from "@/lib/cn";
import type { Permission } from "@/lib/rbac";
import { hasPermission } from "@/lib/rbac";

/*
 * Ilova qobig'i — Apple-uslub minimal navigatsiya (topshiriq §7):
 * yumshoq chegaralar, past kontrast, jadval-og'ir tartib yo'q.
 *
 * Mobil kenglikda navigatsiya PASTKI panelga tushadi — kassir bu ilovani
 * telefonda ishlatadi (PROJECT.md cheklovi) va yon panel u yerda ekranning
 * yarmini yeb qo'yardi.
 *
 * DIQQAT: `permission` faqat MENYUNI YASHIRADI. Foydalanuvchi yashirilgan
 * yo'lni to'g'ridan-to'g'ri ochsa, sahifadagi so'rov serverda 403 oladi —
 * xavfsizlik chegarasi o'sha yerda (T-01-62).
 */
type NavItem = {
  href: "/dashboard" | "/users" | "/audit";
  labelKey: "dashboard" | "users" | "audit";
  icon: typeof LayoutDashboard;
  permission: Permission | null;
};

const NAV_ITEMS: readonly NavItem[] = [
  {
    href: "/dashboard",
    labelKey: "dashboard",
    icon: LayoutDashboard,
    permission: null,
  },
  { href: "/users", labelKey: "users", icon: Users, permission: "user_view" },
  { href: "/audit", labelKey: "audit", icon: ScrollText, permission: "audit_view" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations();
  const pathname = usePathname();
  const { principal } = useAuthStore();

  const roles = principal?.roles ?? [];
  const items = NAV_ITEMS.filter(
    (item) => item.permission === null || hasPermission(roles, item.permission),
  );

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="sticky top-0 z-40 border-b border-border bg-surface/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <div className="min-w-0">
            <p className="text-xs text-text-muted">{t("shell.marketLabel")}</p>
            {/* D-16: bozor nomi DB kontenti — tarjima qilinmaydi. */}
            <p className="truncate text-sm font-semibold">
              {principal?.marketName ?? t("common.appName")}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <LocaleSwitcher />
            <UserMenu />
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-6xl flex-1 gap-6 px-4 py-6">
        {/* Yon panel — faqat `md` dan kattaroq ekranlarda. */}
        <nav
          aria-label={t("shell.sections")}
          className="hidden w-52 shrink-0 flex-col gap-1 md:flex"
        >
          {items.map((item) => (
            <NavLink
              active={pathname === item.href}
              href={item.href}
              icon={item.icon}
              key={item.href}
              label={t(`nav.${item.labelKey}`)}
            />
          ))}
        </nav>

        <main className="min-w-0 flex-1 pb-20 md:pb-0">{children}</main>
      </div>

      {/* Mobil pastki panel — barmoq nishoni uchun kamida 44px balandlik. */}
      <nav
        aria-label={t("shell.sections")}
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-border bg-surface md:hidden"
      >
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex min-h-14 flex-1 flex-col items-center justify-center gap-1 text-xs",
                active ? "text-accent" : "text-text-muted",
              )}
              href={item.href}
              key={item.href}
            >
              <Icon aria-hidden="true" className="size-5" />
              {t(`nav.${item.labelKey}`)}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function NavLink({
  active,
  href,
  icon: Icon,
  label,
}: {
  active: boolean;
  href: NavItem["href"];
  icon: NavItem["icon"];
  label: string;
}) {
  return (
    <Link
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-surface-muted text-text"
          : "text-text-muted hover:bg-surface-muted hover:text-text",
      )}
      href={href}
    >
      <Icon aria-hidden="true" className="size-4" />
      {label}
    </Link>
  );
}
