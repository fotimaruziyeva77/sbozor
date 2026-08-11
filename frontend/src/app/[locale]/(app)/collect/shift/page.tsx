"use client";

import { useCallback, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { ShiftOpenCard } from "@/components/collect/shift-open-card";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";
import { useOpenShift } from "@/lib/shift-queries";
import { routing } from "@/i18n/routing";

/*
 * =============================================================================
 * Y-3 — SMENA VA KO'R NAQD DEKLARATSIYASI (UI-SPEC §4.1, §4.2, §10).
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA MARSHRUT `/collect` OSTIDA, MUSTAQIL `/shifts` EMAS (§4.2)
 * -----------------------------------------------------------------------
 * 1. Smena — kassir oqimining SHARTI, alohida ish emas: `/collect` ochiq
 *    smenasiz ishlamaydi va u yerdan bitta havola bilan shu sahifaga
 *    o'tiladi. URL ierarxiyasi shu bog'liqlikni TAKRORLAYDI.
 * 2. Navigatsiya byudjeti: mustaqil element kassirning mobil panelida
 *    kuniga 2 marta bosiladigan narsani kuniga 500 marta bosiladigan
 *    narsa bilan TENG OG'IRLIKDA qo'yardi.
 * 3. Direktorga bu marshrut kerak emas — u farqni Y-4 da, kun kesimida
 *    ko'radi (§11.5), ya'ni ikkinchi marshrut ikkinchi iste'molchi
 *    topmasdi.
 *
 * ⛔ SHUNING UCHUN BU SAHIFA `NAV_ITEMS` GA QO'SHILMAYDI (§4.6) — u
 *    `/collect` sarlavhasidagi havola bo'lib yashaydi, `/cameras/[id]/zones`
 *    bilan AYNAN bir xil naqsh: bola marshrut nav elementi emas.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ URL HOLATI TAQIQLANADI (§4.5)
 * -----------------------------------------------------------------------
 * Deklaratsiya bir marta yoziladi va O'ZGARMAS (D-25). Har qanday
 * so'rov parametri uni OLDINDAN TO'LDIRILGAN qilib qo'yardi, ya'ni
 * kassir naqdni SANAB emas, ekrandagi tayyor raqamni TASDIQLAB
 * yuborardi — ko'r deklaratsiya o'z maqsadini yo'qotardi.
 *
 * ⚠ Shu sababdan bu faylda so'rov parametrini o'qiydigan hech qanday
 *   ilgak yo'q va `Suspense` chegarasi ham KERAK EMAS (`occupancy` va
 *   `snapshots` sahifalarida u AYNAN o'sha ilgak tufayli majburiy edi).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ KOMPOZITSIYA — SAHIFA BOLALARINI O'ZI ALMASHTIRADI
 * -----------------------------------------------------------------------
 * Naqsh `occupancy/page.tsx:149-328` dan: sahifa bolalarini O'ZI import
 * qilib, holatga qarab ALMASHTIRADI. Yopish yuzasi kartaga ko'tarilmaydi
 * (`shift-open-card.tsx` ning §10.1 shartnomasi — IKKI holat, uchinchisi
 * yo'q).
 *
 * ⛔ ALMASHTIRISH, QO'SHISH EMAS: yopish oqimida karta DOM'dan CHIQADI
 *    (`hidden` yoki `display:none` bilan yashirilmaydi). Aks holda
 *    yopilgandan keyin ekranda §10.3 ning AYNAN UCHTA narsasi o'rniga
 *    BESHTA bo'lardi va ko'rlikning ekran qatlami buzilardi.
 *
 * ⚠ HUQUQ KO'ZGUSI — HAQIQIY NAZORAT SERVERDA. `shift_manage` yo'q
 *   sessiyada sahifa umuman chizilmaydi (naqsh `collect/page.tsx:76-85`
 *   dan). Yuk ko'taruvchi qatlam — `require_permission(SHIFT_MANAGE)`
 *   (06-10).
 * =============================================================================
 */

/**
 * Til prefiksli manzil — `@/i18n/navigation` NING O'RNIGA.
 *
 * ⚠ 05-09 (deviatsiya #2) O'LCHAGAN: `@/i18n/navigation` zanjiri VITEST
 *   ostida YECHILMAYDI va uni import qilgan fayl «0 test» bilan
 *   yiqiladi. Bu OLTINCHI nusxa (`camera-row.tsx`, `review/page.tsx`,
 *   `review/uncertain/page.tsx`, `occupancy/page.tsx`, `collect/page.tsx`);
 *   prefiks XARITASI esa nusxa ko'chirilmaydi — u `routing.localePrefix`
 *   dan o'qiladi.
 */
function localeHref(locale: string, path: string): string {
  const config = routing.localePrefix;
  const prefixes: Partial<Record<string, string>> =
    typeof config === "object" && "prefixes" in config
      ? (config.prefixes ?? {})
      : {};
  return `${prefixes[locale] ?? `/${locale}`}${path}`;
}

export default function CollectShiftPage() {
  const t = useTranslations();
  const locale = useLocale();
  const { principal } = useAuthStore();

  const [closing, setClosing] = useState(false);
  const requestClose = useCallback(() => setClosing(true), []);

  const canManage = hasPermission(principal?.roles ?? [], "shift_manage");

  /*
   * ⛔ Ochiq smenaning identifikatori SAHIFADA yechiladi — yopish oqimi
   *    shu qiymatga tayanadi. Karta ham shu ilgakni chaqiradi, LEKIN bu
   *    ikkinchi so'rov EMAS: react-query kalit bo'yicha dedupe qiladi
   *    (`occupancy/page.tsx` da ham xuddi shu naqsh).
   */
  const { data } = useOpenShift({ enabled: canManage });
  const openShift = data ?? null;

  if (!canManage) {
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
          {t("collect.shiftTitle")}
        </h1>

        <a
          className="inline-flex min-h-11 items-center gap-2 rounded-md border border-border bg-surface px-4 text-sm font-semibold text-text hover:bg-surface-muted"
          href={localeHref(locale, "/collect")}
        >
          <ArrowLeft aria-hidden="true" className="size-4" />
          {t("collect.title")}
        </a>
      </div>

      {/*
       * ⛔⛔ YOPISH SHOXI SHU REJANING IKKINCHI TASKIDA TO'LDIRILADI.
       *
       *   Bugun u `null`, va bu ATAYIN: yopish formasi moduli hali
       *   tug'ilmagan, `tsc --noEmit` esa BUTUN proyektni tekshiradi —
       *   oldindan murojaat bu taskning darvozasini BAJARILMAYDIGAN
       *   qilardi.
       *
       *   ⚠ Ikkinchi taskda shox komponentning O'ZIGA almashadi: bo'sh
       *     o'ram ham, `data-*` o'rami ham EMAS.
       */}
      {closing && openShift !== null ? null : <ShiftOpenCard onRequestClose={requestClose} />}
    </div>
  );
}
