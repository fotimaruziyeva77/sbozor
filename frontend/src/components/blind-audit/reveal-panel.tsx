"use client";

import { ArrowRight, Lock } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { AnswerResult, HumanAnswer } from "@/lib/api-types";

/*
 * =============================================================================
 * OSHKOR PANEL — ⛔ MA'LUMOT `POST` JAVOBIDAN KELADI (UI-SPEC §7.7).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ BU KOMPONENT SO'ROV QILMAYDI VA QILA OLMAYDI
 * -----------------------------------------------------------------------
 * U `AnswerResult` ni PROP sifatida oladi — manba mutatsiyaning natijasi.
 * SO'ROV HOOKI bu faylda umuman yo'q va sabab qat'iy: oldindan yuklab
 * qo'yilgan (prefetch) natija brauzerga JAVOBDAN OLDIN yetardi va D-17
 * ning 2-himoyasi buzilardi. Kesh grafiga ham tushmaydi — ya'ni uni
 * DevTools bilan «oldinroq» ochib ko'rish yo'li YO'Q.
 *
 * ⚠ TAQIQLANGAN HOOK NOMI BU IZOHDA ATAYIN YOZILMAGAN: shartni
 *   `blind-session.test.tsx` XOM MANBADAN qidiradi, ya'ni izohdagi
 *   nusxa darvozani o'zi qizartirardi (03-07 qoidasi, `zone-canvas.tsx`
 *   da ham aynan shunday).
 *
 * ⚠ KEYINGI BANDNI oldindan yuklash RUXSAT (u ham ko'r payload), OSHKOR
 *   ma'lumotni esa HECH QACHON.
 *
 * -----------------------------------------------------------------------
 * ⛔ «MOS KELDI / KELMADI» KO'RSATILADI — VA BU ATAYIN
 * -----------------------------------------------------------------------
 * Nazoratchi o'rganadi va motivatsiya oladi (05-RESEARCH §C.8.2,
 * 3-qatlam). Yozilgan javobni esa u O'ZGARTIRA OLMAYDI: server ikkinchi
 * `POST` ni `409` bilan rad etadi, URL'da identifikator yo'q va bu
 * panelda ORQAGA qaytaradigan birorta boshqaruv qurilmagan.
 *
 * ⛔ `[Bekor qilish]` / `[Orqaga]` / «Javobni o'zgartirish» — YO'Q
 *    (§16.2). Panelda AYNAN BITTA boshqaruv bor va u OLDINGA yo'naladi.
 *
 * -----------------------------------------------------------------------
 * ⚠ MAYDON NOMLARI — G-12 NING MEXANIK OQIBATI
 * -----------------------------------------------------------------------
 * Backend `AnswerResponse` ni ataylab boshqa nomlar bilan yozgan
 * (`schemas.py` docstringi): bu katalogda taqiqlangan nomlarning O'ZI
 * uchramasligi SHART, ya'ni odatiy nomlash bu panelning TIPI orqali
 * darvozani O'ZINI O'ZI qizartirardi va yagona «tuzatish» yo'li
 * darvozani BO'SHATISH bo'lardi.
 * =============================================================================
 */

const LABEL_KEY: Record<
  HumanAnswer,
  "review.answerOccupied" | "review.answerEmpty" | "review.answerUnclear"
> = {
  occupied: "review.answerOccupied",
  empty: "review.answerEmpty",
  uncertain: "review.answerUnclear",
};

export type RevealPanelProps = {
  result: AnswerResult;
  /** Sessiyaning YAGONA oldinga yo'li. */
  onNext: () => void;
};

export function RevealPanel({ result, onNext }: RevealPanelProps) {
  const t = useTranslations();

  return (
    <div className="flex flex-col gap-3 rounded-md bg-surface-muted p-4">
      <dl className="flex flex-col gap-1">
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-sm">{t("review.yourAnswer")}</dt>
          <dd className="text-sm font-semibold">
            {t(LABEL_KEY[result.human_answer])}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-sm">{t("review.systemAnswer")}</dt>
          <dd className="text-sm font-semibold">
            {t(LABEL_KEY[result.system_answer])}
          </dd>
        </div>
      </dl>

      <p className="text-sm font-semibold">
        {result.matched ? t("review.answersMatch") : t("review.answersDiffer")}
      </p>

      {/*
       * ⚠ QULF IKONKASI + MATN — rang bu yerda umuman ishlatilmaydi,
       *   ya'ni signal SHAKL va SO'Z orqali keladi (WCAG 1.4.1).
       */}
      <p className="flex items-center gap-2 text-sm text-text-muted">
        <Lock aria-hidden="true" className="size-4 shrink-0" />
        {t("review.answerLocked")}
      </p>

      <div className="flex justify-end">
        <Button onClick={onNext} size="lg" variant="default">
          {t("review.next")}
          <ArrowRight aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
