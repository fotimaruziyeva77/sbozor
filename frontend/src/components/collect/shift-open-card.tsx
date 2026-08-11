"use client";

import { useCallback, useState } from "react";
import { DoorOpen, Loader2 } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { billingErrorView } from "@/lib/billing-errors";
import type { BillingErrorCode } from "@/lib/billing-errors";
import { useOpenShift, useOpenShiftMutation } from "@/lib/shift-queries";

/*
 * =============================================================================
 * SMENA OCHISH KARTASI — IKKI HOLAT, UCHINCHISI YO'Q (UI-SPEC §10.1).
 *
 *   Ochiq smena YO'Q -> `EmptyState` + [Smenani ochish]  -> `POST /shifts`
 *   Ochiq smena BOR  -> Karta: boshlangan vaqt + [Smenani yopish]
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ KARTA YOPISH FORMASINI O'ZI CHIZMAYDI — VA BU QAROR
 * -----------------------------------------------------------------------
 * [Smenani yopish] bosilganda karta AYNAN `onRequestClose` ni chaqiradi va
 * shu bilan tugaydi. Kompozitsiya SAHIFADA (`collect/shift/page.tsx`,
 * `occupancy/page.tsx:149-328` naqshi): sahifa bolalarini o'zi import
 * qilib, holatga qarab ALMASHTIRADI.
 *
 * ⛔ Nega bu yerda emas: yopish formasi `ui/` primitiviga ko'tarilmagani
 *    kabi (§3.2) u KARTAGA ham ko'tarilmaydi. Aks holda kartaning §10.1
 *    dagi IKKI holati UCHGA aylanardi va «uchinchisi yo'q» degan jumla
 *    o'z ma'nosini yo'qotardi.
 *
 * ⛔ `onRequestClose` MAJBURIY, ixtiyoriy EMAS. Ixtiyoriy bo'lsa keyingi
 *    ijrochi kartani propsiz chizib, [Smenani yopish] ni HECH QAYERGA
 *    olib bormaydigan tugmaga aylantirardi va CASH-04 ekranda kuzatilmas
 *    bo'lib qolardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ KARTADA KO'RINMAYDIGAN NARSALAR — TAQIQ RO'YXATI (§10.1 oxirgi bandi)
 * -----------------------------------------------------------------------
 * To'lovlar soni · yig'ilgan naqd miqdori · o'rtacha qiymat · «bugungi
 * natija» — HECH QANDAY SHAKLDA. Sabab §10.3 da: har qanday arifmetika
 * kassirga tizim raqamini beradi va ertaga deklaratsiya SANASH emas,
 * KO'CHIRISH bo'lib qolardi. Ya'ni bu yerdagi «yo'qlik» bezak emas —
 * u ko'r deklaratsiyaning EKRAN qatlami.
 *
 * -----------------------------------------------------------------------
 * ⛔ IKKINCHI «OCHISH» TUGMASI YO'Q (D-27)
 * -----------------------------------------------------------------------
 * Bir vaqtda bitta ochiq smena — STRUKTURAVIY kafolat (qisman `UNIQUE`
 * indeks, 06-04) va server 409 bilan javob beradi (06-10). UI uchinchi
 * qatlam: ochiq smena bo'lsa «ochish» affordansi UMUMAN chizilmaydi.
 *
 * ⚠ Server baribir `shift_already_open` qaytarsa (ikki qurilma, bitta
 *   kassir — poyga), xato §13.7 dagi SABAB + NIMA QILISH KERAK juftligi
 *   bilan chiziladi VA ochiq smena holati qayta so'raladi: server «sizda
 *   ochiq smena bor» degan bo'lsa, ekran uni KO'RSATISHI kerak, aks holda
 *   kassir tugmani qayta bosib turardi.
 * =============================================================================
 */

/**
 * D-27 ning poyga shoxi — nomi KODDA, chunki u xulqni boshqaradi.
 *
 * Bu kod kelganda ekran faqat xato chizmaydi: u ochiq smena so'rovini
 * QAYTA yugurtiradi va karta ikkinchi holatiga o'tadi.
 */
const ALREADY_OPEN: BillingErrorCode = "shift_already_open";

export type ShiftOpenCardProps = {
  /**
   * [Smenani yopish] bosilganda chaqiriladi — ⛔ MAJBURIY.
   *
   * Karta yopish yuzasini O'ZI chizmaydi; kompozitsiya sahifada.
   */
  onRequestClose: () => void;
};

export function ShiftOpenCard({ onRequestClose }: ShiftOpenCardProps) {
  const t = useTranslations();
  const format = useFormatter();

  const { data, isLoading, refetch } = useOpenShift();
  const openShift = useOpenShiftMutation();

  const [busy, setBusy] = useState(false);
  const [failureCode, setFailureCode] = useState<string | null>(null);

  const requestOpen = useCallback(() => {
    setFailureCode(null);
    setBusy(true);

    openShift.mutate(undefined, {
      onError: (error) => {
        setBusy(false);
        const code = error instanceof ApiError ? error.detail : null;
        setFailureCode(code);
        /* Server «ochiq smena bor» dedi — ekran uni ko'rsatishi shart. */
        if (code === ALREADY_OPEN) void refetch();
      },
      onSuccess: () => setBusy(false),
    });
  }, [openShift, refetch]);

  const failureView =
    failureCode === null ? null : billingErrorView(failureCode);

  if (isLoading) {
    return (
      <div aria-busy="true" className="flex flex-col gap-2" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-24" />
      </div>
    );
  }

  const shift = data ?? null;

  return (
    <div className="flex flex-col gap-4">
      {shift === null ? (
        /*
         * §13.8 ning 1-bo'sh holati. Sarlavha va tavsif §13.7 ning
         * SABAB + NIMA QILISH KERAK juftligidan quriladi — yangi matn
         * kaliti to'qilmaydi (copy egaligi 06-02 da).
         */
        <EmptyState
          action={
            <Button
              className="min-h-11"
              onClick={requestOpen}
              variant="secondary"
            >
              {busy ? (
                <Loader2 aria-hidden="true" className="animate-spin" />
              ) : (
                <DoorOpen aria-hidden="true" />
              )}
              {t("collect.shiftOpen")}
            </Button>
          }
          description={t("collect.errorFix.no_open_shift")}
          title={t("collect.errorCause.no_open_shift")}
        />
      ) : (
        <Card>
          <CardHeader>
            <p className="text-xs font-semibold tracking-wide text-text-muted uppercase">
              {t("collect.shiftOpenedAt")}
            </p>
            <p className="text-lg font-semibold tabular-nums">
              {format.dateTime(new Date(shift.opened_at), {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </p>
          </CardHeader>

          <CardContent>
            {/*
             * ⛔ Bu tugma FORMANI OCHMAYDI — u sahifaga «yopish oqimiga
             *    o't» deb XABAR beradi. Formani sahifa chizadi.
             */}
            <Button className="min-h-11 w-full" onClick={onRequestClose}>
              {t("collect.shiftClose")}
            </Button>
          </CardContent>
        </Card>
      )}

      {/*
       * §13.7 — yalang'och «xato» emas, SABAB + NIMA QILISH KERAK.
       * `role="alert"`: ish davom etmaydi, ya'ni e'lon uzilishi kerak.
       */}
      {failureView !== null ? (
        <div
          className="flex flex-col gap-1 rounded-sm bg-danger/10 px-3 py-2"
          role="alert"
        >
          <p className="text-sm font-semibold text-danger-text">
            {t(failureView.causeKey)}
          </p>
          <p className="text-sm text-text">{t(failureView.fixKey)}</p>
        </div>
      ) : null}
    </div>
  );
}
