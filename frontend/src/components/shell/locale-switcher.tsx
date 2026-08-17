"use client";

import type { CSSProperties } from "react";
import { useTransition } from "react";
import { useLocale, useTranslations } from "next-intl";

import { usePathname, useRouter } from "@/i18n/navigation";
import { apiFetch } from "@/lib/api-client";
import type { ApiLocale } from "@/lib/api-types";
import {
  LOCALE_LABELS,
  LOCALES,
  meLocaleResponseSchema,
} from "@/lib/api-types";
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
 * variantni izlaydi. Ro'yxat `api-types.ts` da: yangi foydalanuvchi
 * formasidagi til tanlovi ham SHU manbadan o'qiydi va ikkisi ajralib
 * keta olmaydi.
 */

/*
 * ---------------------------------------------------------------------------
 * SIRG'ALUVCHI FAOL INDIKATOR (09-UI-SPEC §12.9, 09-06 Task 1).
 *
 * Faol fon endi tugmadan-tugmaga SAKRAMAYDI: guruh ichida BITTA absolut
 * indikator yashaydi va u `transform: translateX()` bilan siljiydi.
 *
 * ⛔ O'LCHOVSIZ IJRO — ataylab: uchala tugma bir xil `w-20` kenglikda,
 *    indikator ham `w-20`, siljish `translateX(calc(var(--idx) *
 *    (100% + 0.25rem)))` — bu yerda `100%` indikatorning O'Z kengligi
 *    (= tugma kengligi), `0.25rem` esa `gap-1`. `getBoundingClientRect()`
 *    ISHLATILMAYDI: jsdom'da u 0 qaytaradi va o'lchov `ResizeObserver` +
 *    ikkinchi render talab qilardi.
 *
 * ⛔ `width`/`left`/`margin` ANIMATSIYA QILINMAYDI (G-motion-3(a) ruhi:
 *    layout xossalari 60fps ni o'ldiradi) — `transition-transform` sinfi
 *    tranzitsiyani transform OILASI bilan chegaralaydi; davomiylik/ease
 *    `--default-transition-*` tokenlaridan (09-01), sehrli son YO'Q.
 *
 * ⚠ Yorliqlar ENDONIM bo'lib QOLADI (yuqoridagi 01-08 qarori) — 09-06
 *   rejasi «UZ/ЎЗ/RU» deb taxmin qilgan edi, mavjud kontrakt yutdi.
 *   `w-20` (80px) eng uzun endonim («O'zbekcha», ~55px @ text-xs) uchun
 *   yetarli; kenglik ENDONIM O'ZGARSA qayta ko'riladi.
 *
 * ⚠ Reduced-motion: global `@media (prefers-reduced-motion: reduce)` bloki
 *   (09-01) `transition-duration` ni 0.01ms ga tushiradi — indikator
 *   sirg'almasdan DARHOL joyiga tushadi, alohida shox kerak emas.
 *
 * ⚠ `ThemeToggle` bu naqshni OLMAYDI (09-06 reja taqiqi): uning yorliqlari
 *   («Yorug'»/«Tungi»/«Quyosh ostida») turli kenglikda va o'lchovsiz teng
 *   kenglik yechimi u yerda ishlamaydi; §12.9 faqat `LocaleSwitcher` ni
 *   nomlaydi.
 * ---------------------------------------------------------------------------
 */

/** Tugma VA indikatorning umumiy kenglik sinfi — bitta haqiqat manbai. */
const BUTTON_WIDTH_CLASS = "w-20";

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

  /* Faol indeks — indikatorning yagona kirishi (`--idx`). */
  const activeIndex = LOCALES.findIndex((code) => code === active);

  return (
    <div
      aria-label={t("languageLabel")}
      className="relative inline-flex items-center gap-1 rounded-md border border-border bg-surface p-1"
      role="group"
    >
      {/*
        * Indikator tugmalardan OLDIN chiziladi: absolut element bir xil
        * stacking kontekstda keyingi `relative` tugmalar OSTIDA qoladi —
        * matn kontrasti (`text-accent-fg` faol tugmada) buzilmaydi.
        * `aria-hidden` + `pointer-events-none` — bu bezak, bosishni
        * yutmaydi (pending-card halqasi bilan bir sinf).
        */}
      {activeIndex >= 0 ? (
        <span
          aria-hidden="true"
          className={cn(
            "pointer-events-none absolute inset-y-1 left-1 rounded-sm bg-accent",
            "transition-transform",
            BUTTON_WIDTH_CLASS,
          )}
          data-active-index={activeIndex}
          style={
            {
              "--idx": String(activeIndex),
              transform: "translateX(calc(var(--idx) * (100% + 0.25rem)))",
            } as CSSProperties
          }
        />
      ) : null}
      {LOCALES.map((code) => {
        const isActive = code === active;
        return (
          <button
            aria-current={isActive ? "true" : undefined}
            className={cn(
              "relative rounded-sm px-2 py-1 text-xs font-semibold transition-colors",
              "disabled:pointer-events-none disabled:opacity-50",
              BUTTON_WIDTH_CLASS,
              /* Faol fon endi INDIKATORDA — tugma faqat matn rangini oladi. */
              isActive
                ? "text-accent-fg"
                : "text-text-muted hover:bg-surface-muted hover:text-text",
            )}
            disabled={isPending}
            key={code}
            lang={code}
            onClick={() => change(code)}
            type="button"
          >
            {LOCALE_LABELS[code]}
          </button>
        );
      })}
    </div>
  );
}
