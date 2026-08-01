"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";

import { Skeleton } from "@/components/ui/skeleton";
import { WizardStepper } from "@/components/wizard/wizard-stepper";
import { marketErrorMessageKey } from "@/lib/market-errors";
import { useSetupStatusQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * Usta qobig'i — rels + kontent (UI-SPEC §6.1, §6.3).
 *
 * HOLAT SERVERDAN: `useSetupStatusQuery` bajarilganlikni hisoblab beradi va
 * qobiq uni stepperga uzatadi. Klientda qadam holatini saqlaydigan xotira
 * YO'Q va bo'lmasligi ham kerak — brauzer xotirasining hech qanday turi
 * ham, global store ham bu yerda ISHLATILMAYDI. Aynan shuning uchun sahifa
 * yangilash, boshqa qurilmadan davom ettirish va uzilishdan tiklanish
 * qo'shimcha kodsiz ishlaydi; saqlangan qadam esa serverdagi haqiqatdan
 * ajralib, "bajarilgan" deb turgan bo'sh qadamni ko'rsatardi.
 *
 * ⚠ Bu qoida mexanik grep bilan qulflangan: taqiqlangan brauzer-xotira
 * API'larining nomlari shu izohda ham LITERAL yozilmaydi — keyingi
 * ishlovchi ularni "tushuntirish uchun" qaytarib qo'ymasin.
 *
 * `marketId === null` — bozor hali TUG'ILMAGAN (`/markets/new`). So'rov
 * yuborilmaydi va stepper `status = null` bilan chiziladi. Bu yerda joriy
 * TANLANGAN bozorning holatini o'qish TAQIQ: u BOSHQA bozor va uning
 * progressini yangi bozor ustasida ko'rsatish sof yolg'on bo'lardi.
 *
 * XATO HOLATI TO'SIQ EMAS: `setup-status` yiqilsa qadam mazmuni baribir
 * chiziladi (zona qo'shish `GET /setup-status` ga bog'liq emas). Stepper
 * o'shanda "hech nima bajarilmagan" ko'rinishida qoladi va sabab qatori
 * yoziladi — usta esa ishlayveradi.
 * =============================================================================
 */
export function WizardShell({
  children,
  currentStep,
  marketId,
  title,
}: {
  children: ReactNode;
  currentStep: number;
  /** `null` — `/markets/new`: bozor hali yaratilmagan. */
  marketId: string | null;
  title: string;
}) {
  const t = useTranslations();
  const statusQuery = useSetupStatusQuery(marketId);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>

      <div className="flex flex-col gap-6 md:flex-row md:items-start">
        <WizardStepper
          currentStep={currentStep}
          status={statusQuery.data ?? null}
        />

        <div className="flex min-w-0 flex-1 flex-col gap-4">
          {statusQuery.isError ? (
            /*
             * `role="status"`, shoshilinch e'lon EMAS: to'liqlik holati
             * o'qilmadi, lekin ustaning O'ZI ishlayveradi. Uni xato ekraniga
             * aylantirish foydalanuvchini ishlaydigan oqimdan chiqarardi.
             */
            <p className="text-sm text-text-muted" role="status">
              {t(marketErrorMessageKey(statusQuery.error))}
            </p>
          ) : null}

          {statusQuery.isPending && marketId !== null ? (
            <div aria-busy="true" className="flex flex-col gap-3" role="status">
              <span className="sr-only">{t("common.loading")}</span>
              <Skeleton className="h-32 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
            </div>
          ) : (
            children
          )}
        </div>
      </div>
    </div>
  );
}
