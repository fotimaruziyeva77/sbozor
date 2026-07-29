"use client";

import { useTransition } from "react";
import { useLocale, useTranslations } from "next-intl";

import { usePathname, useRouter } from "@/i18n/navigation";
import { apiFetch } from "@/lib/api-client";
import type { ApiLocale } from "@/lib/api-types";
import { meLocaleResponseSchema } from "@/lib/api-types";
import { cn } from "@/lib/cn";
import { useAuthStore } from "@/lib/auth-store";

/*
 * Bir bosishli til almashtirgich (FOUND-04, ROADMAP mezoni #2).
 *
 * Bitta bosish IKKI ishni bajaradi:
 *   1. `router.replace(pathname, {locale})` — URL prefiksi almashadi
 *      (`/uz` -> `/uz-cyrl` -> `/ru`) va butun interfeys qayta render bo'ladi.
 *   2. `PATCH /api/v1/me {locale}` — tanlov DB profiliga yoziladi (D-13).
 *      DB — bitta haqiqat manbai: keyingi login yoki boshqa qurilmadagi
 *      sessiya ham shu tilda ochiladi.
 *
 * DIQQAT: `usePathname`/`useRouter` FAQAT `@/i18n/navigation` dan olinadi —
 * Next'ning o'z navigatsiya modulidan EMAS. U yerdagi versiya locale
 * prefiksini bilmaydi va `replace(pathname, {locale})` shakli unda umuman
 * yo'q — natijada til almashtirish jimgina ishlamay qolardi. Bu qoida grep
 * darvozasi bilan qulflangan, shuning uchun o'sha modul nomi bu faylda
 * literal sifatida yozilmaydi.
 */

/** D-13: profil endpointi. To'liq yo'l — `/api/v1/me`. */
const ME_PATH = "/me";

/*
 * Yorliqlar ATAYIN tarjima fayllarida EMAS: til nomi har doim O'Z tilida
 * yoziladi (endonim). "Русский" ni o'zbekchaga tarjima qilish tanlovni
 * o'qib bo'lmas holga keltirardi — foydalanuvchi o'zi tushunadigan yagona
 * variantni izlaydi.
 */
const LOCALE_OPTIONS: readonly { code: ApiLocale; label: string }[] = [
  { code: "uz-Latn", label: "O'zbekcha" },
  { code: "uz-Cyrl", label: "Ўзбекча" },
  { code: "ru", label: "Русский" },
];

export function LocaleSwitcher() {
  const t = useTranslations("common");
  const active = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const { accessToken, updatePrincipal } = useAuthStore();

  function change(next: ApiLocale) {
    if (next === active) return;

    startTransition(() => {
      router.replace(pathname, { locale: next });

      // Kirish qilinmagan holatda (login sahifasi) profil yo'q — faqat URL
      // almashadi. Tanlov keyingi kirishdan so'ng profildan o'qiladi (D-15:
      // brauzer tili HECH QACHON so'ralmaydi).
      if (!accessToken) return;

      updatePrincipal({ locale: next });
      void apiFetch(ME_PATH, {
        method: "PATCH",
        body: { locale: next },
        schema: meLocaleResponseSchema,
      }).catch(() => {
        // Interfeys allaqachon yangi tilda. Yozuv yiqilsa ham foydalanuvchini
        // to'xtatmaymiz — u keyingi bosishda yoki keyingi sessiyada saqlanadi.
      });
    });
  }

  return (
    <div
      aria-label={t("languageLabel")}
      className="inline-flex items-center gap-0.5 rounded-md border border-border bg-surface p-0.5"
      role="group"
    >
      {LOCALE_OPTIONS.map((option) => {
        const isActive = option.code === active;
        return (
          <button
            aria-current={isActive ? "true" : undefined}
            className={cn(
              "rounded-sm px-2.5 py-1 text-xs font-medium transition-colors",
              "disabled:pointer-events-none disabled:opacity-50",
              isActive
                ? "bg-accent text-accent-fg"
                : "text-text-muted hover:bg-surface-muted hover:text-text",
            )}
            disabled={isPending}
            key={option.code}
            lang={option.code}
            onClick={() => change(option.code)}
            type="button"
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
