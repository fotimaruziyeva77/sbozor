import { createNavigation } from "next-intl/navigation";

import { routing } from "./routing";

/**
 * Locale'ni biladigan navigatsiya API'lari.
 *
 * Bularni `next/link` va `next/navigation` o'rniga ishlating — ular URL
 * prefiksini (`/uz`, `/uz-cyrl`, `/ru`) avtomatik qo'yadi.
 *
 * ESKIRGAN: next-intl 3.x dagi `createSharedPathnamesNavigation`.
 */
export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
