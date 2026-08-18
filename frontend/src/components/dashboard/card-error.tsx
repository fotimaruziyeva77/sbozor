"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

/*
 * KARTADAGI XATO — «Sbozor Direktor» dizaynining talabi (brief §4, §10).
 *
 * ⛔⛔ NIMANI TUZATADI: panel kartalari xato bo'lganda `return null`
 *    qilardi, ya'ni karta EKRANDAN YO'QOLARDI. Natijada direktor uchta
 *    butunlay boshqa holatni ajrata olmasdi:
 *      — ruxsat yo'q
 *      — bu kunda ma'lumot yo'q
 *      — server javob bermadi
 *    Uchalasi ham «bo'sh joy» bo'lib ko'rinardi. Bu eng ko'p ochiladigan
 *    ekrandagi kuzatuvchanlik teshigi edi.
 *
 * ⛔ Karta O'RNIDA qoladi: yo'qolgan blok «bunday ma'lumot yo'q» degan
 *    yolg'on xabar beradi.
 */
export type CardErrorProps = {
  onRetry: () => void;
};

export function CardError({ onRetry }: CardErrorProps) {
  const t = useTranslations();

  return (
    <div
      className="flex flex-col items-start gap-2 rounded-sm bg-danger/10 px-3 py-2"
      role="alert"
    >
      <p className="text-sm font-semibold text-danger-text">
        {t("errors.loadFailedTitle")}
      </p>
      <p className="text-sm text-text">{t("errors.loadFailedBody")}</p>
      <Button onClick={onRetry} size="sm" variant="secondary">
        {t("common.retry")}
      </Button>
    </div>
  );
}
