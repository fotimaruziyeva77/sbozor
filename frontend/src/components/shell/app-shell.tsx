"use client";

import { useState } from "react";
import {
  Banknote,
  CalendarDays,
  Ellipsis,
  LayoutDashboard,
  Map,
  ScrollText,
  Store,
  UserRound,
  Users,
  Video,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { LocaleSwitcher } from "@/components/shell/locale-switcher";
import { NavMoreSheet } from "@/components/shell/nav-more-sheet";
import type { NavSheetItem } from "@/components/shell/nav-more-sheet";
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
 * 2-FAZA KENGAYTMASI (UI-SPEC §12.3): bo'limlar soni 3 dan 8 ga chiqdi.
 *   * Desktop — uch guruh: (guruhsiz) Boshqaruv paneli · Bozor · Tizim.
 *     Guruhlash sakkizta yassi havolani skanerlanadigan qiladi.
 *   * Mobil   — ENG KO'PI 5 element: birinchi to'rttasi + "Ko'proq".
 *     360px kenglikda 8 element har biriga ~45px qoldirardi va barmoq
 *     nishoni 44px dan pastga tushardi (WCAG 2.5.8).
 *
 * DIQQAT: `permission` faqat MENYUNI YASHIRADI. Foydalanuvchi yashirilgan
 * yo'lni to'g'ridan-to'g'ri ochsa, sahifadagi so'rov serverda 403 oladi —
 * xavfsizlik chegarasi o'sha yerda (T-01-62 / T-02-101). Kassir va
 * nazoratchida `market_data_view` YO'Q (RESEARCH A8), ya'ni ular faqat
 * Boshqaruv panelini ko'radi va bu ro'yxatdan avtomatik kelib chiqadi.
 */

/** Yon paneldagi guruh; `null` — sarlavhasiz, eng tepada. */
type NavGroup = "market" | "system" | null;

type NavItem = {
  href:
    | "/dashboard"
    | "/map"
    | "/stalls"
    | "/vendors"
    | "/tariffs"
    | "/calendar"
    | "/cameras"
    | "/users"
    | "/audit"
    | "/markets/new";
  labelKey:
    | "dashboard"
    | "map"
    | "stalls"
    | "vendors"
    | "tariffs"
    | "calendar"
    | "cameras"
    | "users"
    | "audit"
    | "newMarket";
  icon: LucideIcon;
  permission: Permission | null;
  group: NavGroup;
};

/*
 * TARTIB MA'NOLI va tasodifiy emas:
 *   * mobil panel birinchi TO'RTTASINI oladi (`MOBILE_PRIMARY_COUNT`), ya'ni
 *     bu ro'yxatning boshi = eng ko'p ishlatiladigan bo'limlar;
 *   * yon panel guruhlarni shu tartibda chizadi (guruhsiz -> Bozor -> Tizim).
 * Elementni ko'chirish IKKALA yuzani ham o'zgartiradi.
 */
const NAV_ITEMS: readonly NavItem[] = [
  {
    href: "/dashboard",
    labelKey: "dashboard",
    icon: LayoutDashboard,
    permission: null,
    group: null,
  },
  {
    href: "/map",
    labelKey: "map",
    icon: Map,
    permission: "market_data_view",
    group: "market",
  },
  {
    href: "/stalls",
    labelKey: "stalls",
    icon: Store,
    permission: "market_data_view",
    group: "market",
  },
  {
    // Sotuvchi — SHAXSIY MA'LUMOT, shuning uchun o'z huquqi bor (D-09).
    href: "/vendors",
    labelKey: "vendors",
    icon: UserRound,
    permission: "vendor_view",
    group: "market",
  },
  {
    href: "/tariffs",
    labelKey: "tariffs",
    icon: Banknote,
    permission: "market_data_view",
    group: "market",
  },
  {
    href: "/calendar",
    labelKey: "calendar",
    icon: CalendarDays,
    permission: "market_data_view",
    group: "market",
  },
  /*
   * "Kameralar" — 3-fazaning YAGONA yangi bo'limi (UI-SPEC §3.3).
   *
   * `market` GURUHIDA: kamera — bozor ICHIDAGI obyekt (xarita, rasta va
   * tarif bilan bir qatorda), platforma amali emas. "Yangi bozor" ning
   * `system` guruhida turishi bilan izchil.
   *
   * `/calendar` DAN KEYIN TURISHI ATAYIN: yuqoridagi izohga ko'ra
   * ro'yxatning BOSHI mobil pastki panelning birinchi to'rttasini beradi
   * (`MOBILE_PRIMARY_COUNT`). Kamerani yuqoriga ko'chirish kassir va
   * admin eng ko'p ishlatadigan bo'limni paneldan siqib chiqarardi —
   * jonli ko'rish esa KUNLIK amal emas, u nizo yoki tekshiruvda
   * ochiladi. Element "Ko'proq" varag'iga tushadi va mobil kontrakt
   * (eng ko'pi 5 element) BUZILMAYDI.
   *
   * `camera_view` faqat menyuni yashiradi (fayl boshidagi DIQQAT
   * bandiga qarang). Haqiqiy darvoza — `require_permission(CAMERA_VIEW)`
   * (03-06/03-07).
   */
  {
    href: "/cameras",
    labelKey: "cameras",
    icon: Video,
    permission: "camera_view",
    group: "market",
  },
  { href: "/users", labelKey: "users", icon: Users, permission: "user_view", group: "system" },
  {
    href: "/audit",
    labelKey: "audit",
    icon: ScrollText,
    permission: "audit_view",
    group: "system",
  },
  /*
   * "Yangi bozor" — CR-03 ning ikkinchi to'sig'ini yopadigan yozuv.
   *
   * OXIRDA TURISHI ATAYIN: yuqoridagi izohga ko'ra ro'yxatning BOSHI mobil
   * pastki panelning birinchi to'rttasini beradi. Yozuv oxirda bo'lgani
   * uchun u "Ko'proq" varag'iga tushadi va UI-SPEC §12.3 ning "mobilda eng
   * ko'pi 5 element" kontrakti BUZILMAYDI. Uni yuqoriga ko'chirish kassir
   * eng ko'p ishlatadigan bo'limni paneldan siqib chiqarardi.
   *
   * `system` GURUHI ATAYIN: bu bozor ICHIDAGI ma'lumot emas (Bozor guruhi
   * — xarita, rastalar, tariflar), balki platforma darajasidagi amal.
   *
   * `market_manage` faqat menyuni yashiradi (yuqoridagi DIQQAT bandiga
   * qarang). Haqiqiy darvozalar: `markets/new/page.tsx` (`market_manage`
   * VA `isPlatformAdmin`) hamda server `POST /markets` (02-11).
   */
  {
    href: "/markets/new",
    labelKey: "newMarket",
    icon: Store,
    permission: "market_manage",
    group: "system",
  },
];

/** Pastki panelda to'g'ridan-to'g'ri ko'rinadigan element soni (+ "Ko'proq" = 5). */
const MOBILE_PRIMARY_COUNT = 4;

/**
 * Yon paneldagi guruhlar CHIZILISH tartibida.
 *
 * `titleKey` TO'LIQ kalit (`nav.` prefiksi bilan) va literal tip sifatida
 * e'lon qilinadi: `src/global.ts` dagi augmentatsiya tufayli mavjud
 * bo'lmagan kalit KOMPILYATSIYA VAQTIDA xatoga aylanadi, runtime'dagi
 * `MISSING_MESSAGE` ga aylanmaydi.
 */
const NAV_GROUPS: readonly {
  group: NavGroup;
  titleKey: "nav.groupMarket" | "nav.groupSystem" | null;
}[] = [
  { group: null, titleKey: null },
  { group: "market", titleKey: "nav.groupMarket" },
  { group: "system", titleKey: "nav.groupSystem" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations();
  const pathname = usePathname();
  const { principal } = useAuthStore();
  const [moreOpen, setMoreOpen] = useState(false);

  const roles = principal?.roles ?? [];
  const items = NAV_ITEMS.filter(
    (item) => item.permission === null || hasPermission(roles, item.permission),
  );

  const primary = items.slice(0, MOBILE_PRIMARY_COUNT);
  const overflow = items.slice(MOBILE_PRIMARY_COUNT);

  const sheetItems: readonly NavSheetItem[] = overflow.map((item) => ({
    href: item.href,
    label: t(`nav.${item.labelKey}`),
    icon: item.icon,
    active: pathname === item.href,
  }));

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
          className="hidden w-52 shrink-0 flex-col gap-4 md:flex"
        >
          {NAV_GROUPS.map(({ group, titleKey }) => {
            const groupItems = items.filter((item) => item.group === group);
            // Huquqi yo'q foydalanuvchida butun guruh bo'sh qolishi mumkin —
            // u holda SARLAVHA ham chizilmaydi (bo'sh sarlavha "bu yerda
            // nimadir bor" degan yolg'on signal berardi).
            if (groupItems.length === 0) return null;

            return (
              <div className="flex flex-col gap-1" key={titleKey ?? "root"}>
                {titleKey === null ? null : (
                  <p className="px-3 text-xs font-semibold text-text-muted">
                    {t(titleKey)}
                  </p>
                )}
                {groupItems.map((item) => (
                  <NavLink
                    active={pathname === item.href}
                    href={item.href}
                    icon={item.icon}
                    key={item.href}
                    label={t(`nav.${item.labelKey}`)}
                  />
                ))}
              </div>
            );
          })}
        </nav>

        <main className="min-w-0 flex-1 pb-20 md:pb-0">{children}</main>
      </div>

      {/* Mobil pastki panel — barmoq nishoni uchun kamida 44px balandlik. */}
      <nav
        aria-label={t("shell.sections")}
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-border bg-surface md:hidden"
      >
        {primary.map((item) => {
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

        {overflow.length === 0 ? null : (
          <button
            aria-expanded={moreOpen}
            className={cn(
              "flex min-h-14 flex-1 flex-col items-center justify-center gap-1 text-xs",
              // Yashirilgan bo'limlardan biri ochiq bo'lsa, "Ko'proq" ham
              // faol ko'rinadi — aks holda pastki panelda HECH BIR element
              // belgilanmagan holat paydo bo'lardi.
              sheetItems.some((item) => item.active)
                ? "text-accent"
                : "text-text-muted",
            )}
            onClick={() => setMoreOpen(true)}
            type="button"
          >
            <Ellipsis aria-hidden="true" className="size-5" />
            {t("nav.more")}
          </button>
        )}
      </nav>

      <NavMoreSheet
        description={t("shell.sections")}
        items={sheetItems}
        onOpenChange={setMoreOpen}
        open={moreOpen}
        title={t("nav.more")}
      />
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
        "flex min-h-11 items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition-colors",
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
