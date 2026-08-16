"use client";

import { Suspense } from "react";
import { DoorOpen } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { localeHref } from "@/lib/locale-href";
import { ForbiddenNotice } from "@/components/auth/forbidden-notice";
import { CollectSession } from "@/components/collect/collect-session";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

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
 * ⚠ `Suspense` chegarasi bu yerda BOSHQA sababga ko'ra turibdi.
 *   `occupancy` va `snapshots` sahifalarida u MAJBURIY, chunki ular
 *   `?day=` ni `useSearchParams` orqali o'qiydi va Next 16 shunday
 *   daraxtni statik prerender ro'yxatidan chiqarib buildni yiqitadi. Bu
 *   yerda o'sha sabab YO'Q (URL holati taqiqlangan) — chegara ish
 *   maydonini SARLAVHADAN ajratadi, ya'ni sessiya yuklanayotganda ham
 *   `[Smena]` havolasi darhol bosiladigan bo'lib qoladi.
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

export default function CollectPage() {
  const t = useTranslations();
  const locale = useLocale();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "payment_create")) {
    return <ForbiddenNotice />;
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

      {/*
       * ⛔⛔ KOMPOZITSIYA KONTRAKTI — QURILGAN NARSA RENDER QILINISHI SHART.
       *
       *   Bu fazaning eng JIM nuqsoni shu bo'lardi: yettita komponent
       *   qurilib, ularni hech kim chizmasa uchala task ham yashil
       *   qaytardi va `/collect` — kuniga 300–1000 marta ochiladigan yuza
       *   — BO'SH QOBIQ bo'lib qolardi. CASH-01/02/03 esa ekranda umuman
       *   MAVJUD BO'LMASDI.
       *
       *   ⛔ Shu sababdan bu yerda komponentning O'ZI chiziladi: bo'sh
       *      o'ram ham, `null` ham, `data-*` o'rami ham EMAS.
       */}
      <Suspense
        fallback={
          <p className="text-sm text-text-muted" role="status">
            {t("common.loading")}
          </p>
        }
      >
        <CollectSession shiftHref={localeHref(locale, "/collect/shift")} />
      </Suspense>
    </div>
  );
}
