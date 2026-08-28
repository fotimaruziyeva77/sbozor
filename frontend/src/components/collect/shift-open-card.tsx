"use client";

import { useCallback, useState } from "react";
import { CircleDot, DoorOpen, Loader2 } from "lucide-react";
import { useFormatter, useLocale, useNow, useTranslations } from "next-intl";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { BrandLoader } from "@/components/ui/brand-loader";
import { ApiError } from "@/lib/api-client";
import { billingErrorView } from "@/lib/billing-errors";
import type { BillingErrorCode } from "@/lib/billing-errors";
import { useOpenShift, useOpenShiftMutation } from "@/lib/shift-queries";
import { isUzLatn, uzLatnDateTime } from "@/lib/uz-latn-date";

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
  const locale = useLocale();
  /*
   * ⛔ `Date.now()` EMAS (260828, `react-hooks/purity` ushladi) —
   *   sabab `cashier-brief.tsx` dagi bilan bir xil: render paytida
   *   chaqirilgan soat komponentni SOF EMAS qiladi va serverda
   *   hisoblangan davomiylik mijoznikidan farq qilardi.
   */
  const now = useNow();

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
      onSuccess: () => {
        setBusy(false);
        /*
         * ⛔ §13.8 NING 4-TOASTI — NATIJA, BUYRUQ EMAS.
         *
         * Karta holati `EmptyState` dan boshlangan-vaqt kartasiga
         * o'tadi va bu o'zgarish EKRANNING pastki qismida bo'lishi
         * mumkin — kassir telefonda uni sezmasligi mumkin. Toast
         * o'zgarishni E'LON qiladi.
         *
         * ⛔ `collect.shiftOpen` ISHLATILMAYDI: u «Smenani ochish» —
         *    BUYRUQ. Natija o'rniga buyruqni ko'rsatish kassirga
         *    «yana bosish kerakmi?» degan savol qoldirardi.
         */
        toast.success(t("collect.shiftOpened"));
      },
    });
  }, [openShift, refetch, t]);

  const failureView =
    failureCode === null ? null : billingErrorView(failureCode);

  if (isLoading) {
    /* Bozor «rasta ustunlari» loaderi — spinner EMAS (masterplan §3.2). */
    return <BrandLoader />;
  }

  const shift = data ?? null;

  return (
    <div className="flex flex-col gap-4">
      {shift === null ? (
        /*
         * §13.8 ning 1-bo'sh holati — 2026-08-25 maketida GERO shaklga
         * ko'tarildi («smena ochish birinchi»): kun shu tugmadan
         * boshlanadi, ya'ni u sahifaning eng katta va yagona urg'uli
         * elementi. Sarlavha va tavsif HAMON §13.7 ning SABAB + NIMA
         * QILISH KERAK juftligidan quriladi — yangi matn kaliti
         * to'qilmadi (copy egaligi 06-02 da).
         *
         * ⛔ Tugma endi `default` (urg'uli) variant, `secondary` EMAS:
         *    bu ekranda undan boshqa amal YO'Q va ikkilamchi ko'rinish
         *    «asosiy amal qayerda?» savolini tug'dirardi.
         */
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
            <span
              aria-hidden="true"
              className="grid size-16 place-items-center rounded-full bg-accent/12 text-accent-text"
            >
              <DoorOpen aria-hidden className="size-8" />
            </span>
            <div className="flex max-w-md flex-col gap-1">
              <p className="text-lg font-semibold">
                {t("collect.errorCause.no_open_shift")}
              </p>
              <p className="text-sm leading-relaxed text-text-muted">
                {t("collect.errorFix.no_open_shift")}
              </p>
            </div>
            <Button className="min-h-12 px-8" onClick={requestOpen}>
              {busy ? (
                <Loader2
                  aria-hidden="true"
                  className="animate-spin motion-reduce:animate-none"
                />
              ) : (
                <DoorOpen aria-hidden="true" />
              )}
              {t("collect.shiftOpen")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            {/*
             * ⛔ Rang YOLG'IZ signal EMAS (WCAG 1.4.1): nuqta yonida
             *    «Smena ochiq» MATNI turadi va u rangsiz ham o'qiladi.
             */}
            <p className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-3 py-1 text-sm font-semibold text-success-text">
                <CircleDot aria-hidden="true" className="size-4" strokeWidth={2.5} />
                {t("collect.shiftStatusOpen")}
              </span>
            </p>
            <p className="text-xs font-semibold tracking-wide text-text-muted uppercase">
              {t("collect.shiftOpenedAt")}
            </p>
            <p className="text-lg font-semibold tabular-nums">
              {/*
               * ⛔ O'zbek lotin yozuvida `Intl` ildiz shablonini beradi
               *    («2026 M08 15 06:45») — sabab `lib/uz-latn-date.ts` da.
               *    Vaqtning o'zi raqamli, ya'ni u har tilda to'g'ri chiqadi
               *    va `Intl` dan olinaveradi.
               */}
              {isUzLatn(locale)
                ? uzLatnDateTime(
                    new Date(shift.opened_at),
                    format.dateTime(new Date(shift.opened_at), {
                      timeStyle: "short",
                    }),
                  )
                : format.dateTime(new Date(shift.opened_at), {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
            </p>
            {/*
             * DAVOMIYLIK — SANOQ, summa emas (§10.1 taqiq ro'yxati
             * buzilmaydi): «necha soatdan beri ishlayapman» kassirning
             * o'z savoli, «qancha yig'dim» esa TAQIQDA qolaveradi.
             */}
            <p className="text-sm tabular-nums text-text-muted">
              {(() => {
                const totalMinutes = Math.max(
                  0,
                  Math.floor(
                    (now.getTime() - new Date(shift.opened_at).getTime()) /
                      60_000,
                  ),
                );
                return t("collect.shiftDurationShort", {
                  hours: Math.floor(totalMinutes / 60),
                  minutes: totalMinutes % 60,
                });
              })()}
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
