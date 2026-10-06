"use client";

import { Fragment } from "react";
import type { ReactNode } from "react";
import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";

import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { VendorHistoryDay } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { formatSoum } from "@/lib/format-number";
import { useVendorHistory } from "@/lib/report-queries";

/*
 * =============================================================================
 * SOTUVCHINING KUNMA-KUN TO'LOV TARIXI — IKKI JOYDA ISHLATILADI.
 *
 *   * «Sotuvchi hisobi» (`vendor-account.tsx`) — faqat QARZDORLAR;
 *   * «Sotuvchilar» ro'yxati (`vendor-list.tsx`) — HAR sotuvchi.
 *
 * ⛔ IKKINCHI JOY NEGA KERAK BO'LDI (261006): «Sotuvchi hisobi» faqat qarzi
 *    noldan katta sotuvchilarni ko'rsatadi. 2026-10-05 da bozorning qarzi
 *    nolga tushirilgach u yerda deyarli hech kim qolmadi, ya'ni «sotuvchini
 *    bossam tarixini ko'raman» degan talab amalda ishlamay qoldi.
 *
 * ⛔⛔ HOLAT — «O'SHA KUN PATTASI YOPILGANMI?», «O'SHA KUNI PUL BERDIMI?»
 *     EMAS. Kassir bugungi pattani va eski qarzni BITTA to'lov bilan oladi,
 *     shuning uchun server holatni FIFO taqsimlashidan chiqaradi
 *     (`report_repo._VENDOR_DAY_HISTORY`). O'sha kuni kassaga tushgan pul
 *     esa ALOHIDA fakt bo'lib qatorda turadi — ikkalasi bir-biriga zid
 *     ko'rinmasligi uchun ekranda qoida bir jumla bilan aytiladi.
 * =============================================================================
 */

/** Tarix oynasi — `vendor-account.tsx` dagi qarzdorlik oynasi bilan bir xil. */
const HISTORY_WINDOW_DAYS = 90;

/**
 * Davr tanlovi yo'q joy uchun (`vendor-list.tsx`): oxirgi 90 kun, KECHA
 * bilan tugaydi — bugungi patta kechasi yoziladi va oyna bugunni olsa,
 * bugungi to'lov har doim «hisobsiz kun» bo'lib ko'rinardi.
 *
 * ⚠ OYNA SHU YERDA, RO'YXATDA EMAS: soat (`useNow`) faqat tarix OCHILGANDA
 *   o'qiladi va ro'yxat o'zi vaqtga bog'lanmaydi.
 */
export function VendorDaysRecent({ vendorId }: { vendorId: string }) {
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const to = shiftIsoDay(businessDayIn(timeZone, now), -1);
  const from = shiftIsoDay(to, -(HISTORY_WINDOW_DAYS - 1));
  return <VendorDays from={from} to={to} vendorId={vendorId} />;
}

/**
 * Bitta sotuvchining KUNMA-KUN tarixi.
 *
 * ⛔ HOLAT SERVERDAN KELADI (`status`) va bu yerda faqat TARJIMA
 *    qilinadi. Qoidani bu yerda qayta yozish ekran bilan hisobotni
 *    ajratib yuborardi (`report_repo.vendor_day_status`).
 */
export function VendorDays({
  from,
  to,
  vendorId,
}: {
  from: string;
  to: string;
  vendorId: string;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const tarix = useVendorHistory(vendorId, { from, to });

  if (tarix.isPending) {
    return <Skeleton className="h-24" />;
  }
  if (tarix.isError) {
    return <p className="dir-tile-note">{t("errors.loadFailedBody")}</p>;
  }

  const { rows: kunlar } = tarix.data;
  if (kunlar.length === 0) {
    return <p className="dir-tile-note">{t("director.vaHistoryEmpty")}</p>;
  }

  const soum = (value: number) => formatSoum(format, value, locale);
  const yigindi = [
    t("director.vaHistorySummary", {
      days: kunlar.length,
      unpaid: tarix.data.unpaid_days,
    }),
  ];
  if (tarix.data.outstanding_soum > 0) {
    yigindi.push(
      t("director.vaHistoryDebt", { sum: soum(tarix.data.outstanding_soum) }),
    );
  }
  if (tarix.data.advance_soum > 0) {
    yigindi.push(
      t("director.vaHistoryAdvance", { sum: soum(tarix.data.advance_soum) }),
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="dir-tile-note">{yigindi.join(" · ")}</p>
      <p className="text-xs text-text-muted">{t("director.vaHistoryRule")}</p>
      <ul className="flex flex-col gap-1">
        {kunlar.map((kun) => (
          <li
            className="flex flex-col gap-1 rounded-md border border-border px-3 py-2"
            key={kun.service_date}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-xs tabular-nums">
                {formatBusinessDay(format, kun.service_date, locale)}
              </span>
              {/*
                ⚠ RASTA KODI KO'RSATILADI: bir sotuvchida bir nechta rasta
                  bo'lishi mumkin va «qaysi rasta to'lanmagan?» degan savol
                  aynan shu yerda tug'iladi.
              */}
              <span className="dir-tile-note">{kun.stall_codes ?? "—"}</span>
              <Badge tone={KUN_TONE[kun.status]}>
                {t(`director.vaDay_${kun.status}`)}
              </Badge>
            </div>
            <KunTafsiloti kun={kun} />
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Qator tafsiloti: hisob, o'sha kungi pul, kechirim, qolgan qarz.
 *
 * ⚠ «Shu kuni to'langan» — FAKT (kassaga yozilgan pul), holat EMAS. U
 *   holatdan farq qilishi normal: masalan pul berilmagan kun FIFO bo'yicha
 *   keyingi pul bilan yopilgan bo'ladi.
 */
function KunTafsiloti({ kun }: { kun: VendorHistoryDay }) {
  const t = useTranslations("director");
  const format = useFormatter();
  const locale = useLocale();
  const soum = (value: number) => formatSoum(format, value, locale);

  const qismlar: { kalit: string; matn: ReactNode }[] = [
    {
      kalit: "hisob",
      matn:
        kun.status === "advance"
          ? t("vaRowNoCharge")
          : t("vaRowCharged", { sum: soum(kun.charged_soum) }),
    },
    {
      kalit: "pul",
      matn:
        kun.paid_soum === 0
          ? t("vaRowNoCash")
          : t("vaRowCash", { sum: soum(kun.paid_soum) }),
    },
  ];
  if (kun.waived_soum > 0) {
    qismlar.push({
      kalit: "kechirim",
      matn: t("vaRowWaived", { sum: soum(kun.waived_soum) }),
    });
  }
  if (kun.unpaid_soum > 0) {
    qismlar.push({
      kalit: "qarz",
      matn: (
        <span className="text-danger-text">
          {t("vaRowDebt", { sum: soum(kun.unpaid_soum) })}
        </span>
      ),
    });
  }

  return (
    <p className="flex flex-wrap gap-x-2 text-xs tabular-nums text-text-muted">
      {qismlar.map(({ kalit, matn }, i) => (
        // Ajratgich O'Z elementida va `aria-hidden`: har fakt alohida
        // o'qiladi, ekran o'quvchi esa «nuqta» ni talaffuz qilmaydi.
        <Fragment key={kalit}>
          {i > 0 ? <span aria-hidden="true">·</span> : null}
          <span>{matn}</span>
        </Fragment>
      ))}
    </p>
  );
}

/**
 * Holat -> rang.
 *
 * ⛔ `waived` SARIQ, YASHIL EMAS: pul tushmagan, qarz kechirilgan.
 *    Yashil qilish uni to'langan kun bilan tenglashtirardi va
 *    hisobotda kassaga tushmagan pul tushgandek ko'rinardi.
 */
export const KUN_TONE: Record<VendorHistoryDay["status"], BadgeTone> = {
  paid: "success",
  partial: "warning",
  unpaid: "danger",
  waived: "warning",
  /*
   * ⚠ `accent`, `success` EMAS: hisobsiz kun — pul olingan, patta
   *   yozilmagan. Yashil uni yopilgan patta bilan tenglashtirardi.
   */
  advance: "accent",
};
