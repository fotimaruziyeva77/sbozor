"use client";

import { DoorOpen } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";
import { routing } from "@/i18n/routing";

/*
 * =============================================================================
 * Y-1 — KASSIR YIG'ISH EKRANI (UI-SPEC §4.1, §8).
 *
 * ⛔⛔ FAZANING ENG KO'P BOSILADIGAN YUZASI: kuniga 300–1000 marta,
 *     telefonda, bozor ichida, ehtimol quyoshda va bir qo'lda.
 *
 * -----------------------------------------------------------------------
 * ⛔ URL HOLATI YO'Q — VA BU UCH SABABLI TAQIQ (§4.5)
 * -----------------------------------------------------------------------
 * Rasta kodi `searchParams` da ham, `nuqs` da ham YASHAMAYDI:
 *
 *   1. URL'dagi kod ULASHILADIGAN va zakladkaga qo'yiladigan «to'lov
 *      varag'i» yaratardi — u ertasi kuni ESKI summa bilan ochilardi;
 *   2. Idempotentlik kaliti SAHIFA HOLATIDA yashaydi (§8.7) va URL bilan
 *      qaytish kalitni YO'QOTIB, dublikat to'lov tug'dirardi;
 *   3. «Orqaga» tugmasi «to'lovdan oldingi holat» ga qaytarib, yozilgan
 *      to'lovni BEKOR QILINGANDEK ko'rsatardi.
 *
 * ⚠ Shu sababdan bu sahifada `Suspense` chegarasi ham YO'Q. `occupancy`
 *   va `snapshots` sahifalarida u MAJBURIY, chunki ular `?day=` ni
 *   `useSearchParams` orqali o'qiydi va Next 16 shunday daraxtni statik
 *   prerender ro'yxatidan chiqarib buildni yiqitadi. Bu yerda o'sha sabab
 *   MAVJUD EMAS — chegarani «har ehtimolga qarshi» qo'yish naqshni
 *   sababisiz ko'chirish bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⚠ HUQUQ KO'ZGUSI — HAQIQIY NAZORAT SERVERDA
 * -----------------------------------------------------------------------
 * `payment_create` yo'q sessiyada sahifa umuman chizilmaydi (naqsh
 * `occupancy/page.tsx:90-99` dan). Bu FOYDALANUVCHI TAJRIBASI, himoya
 * emas: `POST /payments` serverda `require_permission(PAYMENT_CREATE)`
 * ostida va u yagona yuk ko'taruvchi qatlam.
 *
 * ⛔ `/collect/shift` NAVIGATSIYAGA QO'SHILMAYDI (§4.6) — u shu
 *    sahifaning bolasi va sarlavhadagi havola sifatida yashaydi
 *    (`/cameras/[id]/zones` bilan bir xil naqsh).
 * =============================================================================
 */

/**
 * Til prefiksli manzil — `@/i18n/navigation` NING O'RNIGA.
 *
 * ⚠ 05-09 (deviatsiya #2) O'LCHAGAN: `@/i18n/navigation` zanjiri VITEST
 *   ostida YECHILMAYDI va uni import qilgan fayl «0 test» bilan
 *   yiqiladi. Bu BESHINCHI nusxa (`camera-row.tsx`, `review/page.tsx`,
 *   `review/uncertain/page.tsx`, `occupancy/page.tsx`); prefiks XARITASI
 *   esa nusxa ko'chirilmaydi — u `routing.localePrefix` dan o'qiladi.
 */
function localeHref(locale: string, path: string): string {
  const config = routing.localePrefix;
  const prefixes: Partial<Record<string, string>> =
    typeof config === "object" && "prefixes" in config
      ? (config.prefixes ?? {})
      : {};
  return `${prefixes[locale] ?? `/${locale}`}${path}`;
}

export default function CollectPage() {
  const t = useTranslations();
  const locale = useLocale();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "payment_create")) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
        role="alert"
      >
        {t("errors.forbidden")}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("collect.title")}
        </h1>

        <a
          className="inline-flex min-h-11 items-center gap-2 rounded-md border border-border bg-surface px-4 text-sm font-semibold text-text hover:bg-surface-muted"
          href={localeHref(locale, "/collect/shift")}
        >
          <DoorOpen aria-hidden="true" className="size-4" />
          {t("collect.shiftTitle")}
        </a>
      </div>
    </div>
  );
}
