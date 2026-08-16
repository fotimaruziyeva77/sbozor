"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import type { ReportKind } from "@/lib/api-types";
import { reportErrorView } from "@/lib/report-errors";
import { downloadCompareReport, downloadReport } from "@/lib/report-queries";
import type { ReportPeriod } from "@/lib/report-queries";

/*
 * =============================================================================
 * ⛔⛔ EKSPORT TUGMASI — BUTUN MAZMUNI «ODDIY HAVOLA BO'LA OLMASLIK» (§12.2).
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA BRAUZERNING O'Z YUKLAB OLISH YO'LI ISHLATILMAYDI (M-7, T-08-35).
 * -----------------------------------------------------------------------
 * Access token XOTIRADA yashaydi va so'rov SARLAVHASIDA ketadi
 * (`api-client.ts:215`); cookie'da faqat refresh bor. Demak brauzerning
 * o'zi boshlaydigan har qanday yuklab olish — anchor atributi bilan
 * bo'ladimi, yangi oyna ochish bilanmi, manzil satrini almashtirish
 * bilanmi, yoki qo'lda qurilgan anchor bilanmi — ⛔ TOKENSIZ ketadi va
 * `401` oladi. Brauzer esa 401 javob TANASINI `revenue.xlsx` nomi bilan
 * diskka SAQLAYDI: foydalanuvchi «fayl yuklandi» deb o'ylaydi, Excel
 * «fayl buzilgan» deydi va nosozlik ⛔ HECH QAYERDA ko'rinmaydi.
 *
 * ⛔ Shuning uchun bu faylda o'sha to'rt yo'lning HECH BIRI yozilmaydi va
 *    bu ⛔ INTIZOM EMAS, MEXANIKA: G-38(a) darvozasi ularni
 *    `components/reports/**` da 0 ga qulflaydi.
 *
 * ⚠ `saveBlob()` ICHIDA anchor ham bor — u `market-queries.ts:1157` da
 *   yashaydi va skan maydonidan TASHQARIDA. Bu ATAYIN: `saveBlob`
 *   ALLAQACHON olingan baytlarni saqlaydi, ya'ni tarmoqqa tokensiz
 *   so'rov YUBORMAYDI. Taqiq TARMOQ chaqiruviga, saqlash gigiyenasiga
 *   emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA BU TUGMA `ui/` GA KO'TARILMAYDI.
 * -----------------------------------------------------------------------
 * `ui/` dagi «umumiy yuklab olish tugmasi» ertaga manzil PROPINI olardi —
 * va o'sha lahzada yuqoridagi butun mulohaza chaqiruvchining tanloviga
 * aylanardi. Bu yerdagi mazmun esa aynan shu tanlovning YO'QLIGI.
 *
 * -----------------------------------------------------------------------
 * ⛔ XATO — INLINE, TOAST EMAS (§14.7: fazada AYNAN BITTA toast turi).
 * -----------------------------------------------------------------------
 * Toast g'oyib bo'ladi va foydalanuvchi tugmani QAYTA-QAYTA bosardi;
 * har bosish esa og'ir eksport so'rovini serverga qaytadan urardi
 * (T-08-38). Inline matn EKRANDA QOLADI va keyingi qadamni aytadi.
 * =============================================================================
 */

/**
 * Eksport nishoni — ⛔ DISKRIMINATSIYALANGAN ITTIFOQ, ixtiyoriy maydonlar EMAS.
 *
 * ⛔ Solishtiruv `REPORT_KINDS` reyestridan TASHQARIDA (§12.1): uning davri
 *    ⛔ KUN, qolgan to'rttaniki esa ORALIQ. Ikkalasini bitta shaklga
 *    (`kind` + ixtiyoriy `period` + ixtiyoriy `day`) siqish ⛔ DAVRSIZ
 *    eksport chaqiruvini tip tizimidan JIMGINA o'tkazardi — va davrsiz
 *    fayl §1.2 qoida 2 ning bevosita buzilishi: chop etilgan varaqdan
 *    davr yo'qolsa, raqam hech nimaga bog'lanmagan bo'lib qoladi.
 */
export type ExportTarget =
  | { kind: ReportKind; period: ReportPeriod }
  | { day: string; kind: "three-way" };

export type ExportButtonProps = ExportTarget & {
  className?: string;
  /**
   * Hozir yuklab olib bo'lmaydi (masalan davr bo'sh, §4.4).
   *
   * ⛔ `aria-disabled` GA aylanadi, `disabled` ga EMAS [MEROS: 05-UI-SPEC
   *    §13.3]: o'chirilgan tugma fokusni YO'QOTADI va skrinrider
   *    foydalanuvchisi «tugma qayerga ketdi?» holatida qoladi. Tugma
   *    BOSILADI, lekin so'rov yuborilmaydi.
   */
  unavailable?: boolean;
};

/** ⛔ Zaxira juftlik — noma'lum kod nomlangan sababga tushadi (07 D-04). */
const FALLBACK_ERROR_CODE = "report_export_failed";

export function ExportButton(props: ExportButtonProps) {
  const t = useTranslations();
  const [busy, setBusy] = useState(false);
  /** `null` — xato yo'q; aks holda serverning MEXANIK kodi. */
  const [errorCode, setErrorCode] = useState<string | null>(null);

  async function run(): Promise<void> {
    if (props.unavailable === true) return;

    setErrorCode(null);
    setBusy(true);
    try {
      /*
       * ⛔ IKKI YO'L, IKKI FUNKSIYA — `report-queries.ts` dagi
       *   `buildReportPath` / `buildReportDataPath` ajratilishi bilan
       *   AYNI mulohaza: bitta funksiyaga format yoki davr argumentini
       *   qo'shish uni UNUTISH mumkin qilardi.
       */
      if (props.kind === "three-way") {
        await downloadCompareReport(props.day);
      } else {
        await downloadReport(props.kind, props.period);
      }
    } catch (error) {
      setErrorCode(
        error instanceof ApiError ? error.detail : FALLBACK_ERROR_CODE,
      );
    } finally {
      setBusy(false);
    }
  }

  const view = errorCode === null ? null : reportErrorView(errorCode);
  const causeKey =
    view?.causeKey ?? `reports.errorCause.${FALLBACK_ERROR_CODE}`;
  const fixKey = view?.fixKey ?? `reports.errorFix.${FALLBACK_ERROR_CODE}`;

  return (
    <div className="flex flex-col gap-2">
      {/*
       * ⛔ `variant="secondary"` — AKSENT EMAS (§13.3). Yuklab olish
       *    tugmalari TO'RTTA va teng og'irlikda; har biri aksent fonli
       *    bo'lsa sahifada to'rtta RAQOBATLASHUVCHI aksent paydo bo'lardi
       *    va 10 % chegarasi buzilardi. Bittasini tanlab aksent berish
       *    esa qolgan uchtasini ikkinchi darajali deb ko'rsatardi —
       *    holbuki RECON-04 uchalasini TENG talab qiladi.
       *
       * ⛔ `size="md"` (40 px), `lg` EMAS (§6.1): bu DESKTOP yuzasi —
       *    direktor hisobotni kompyuterda chiqaradi va tugma sahifada
       *    to'rt marta takrorlanadi.
       */}
      <Button
        aria-busy={busy}
        aria-disabled={props.unavailable === true}
        className={props.className}
        onClick={() => void run()}
        size="md"
        variant="secondary"
      >
        <Download aria-hidden="true" />
        {/*
         * ⛔ MATN YUKLANISH DAVOMIDA O'ZGARMAYDI (§12.2): almashtirilsa
         *    tugma torayardi va yonidagi uchtasi SIYLARDI. Holat
         *    `aria-busy` bilan e'lon qilinadi.
         */}
        {t("reports.export")}
      </Button>

      {errorCode !== null ? (
        <p className="flex flex-col gap-1 text-sm text-text-muted" role="alert">
          <span>{t(causeKey)}</span>
          {/* ⛔ TUZATISH MATNI MAJBURIY (D-02): yolg'iz sabab keyingi qadamni bermaydi. */}
          <span>{t(fixKey)}</span>
        </p>
      ) : null}
    </div>
  );
}
