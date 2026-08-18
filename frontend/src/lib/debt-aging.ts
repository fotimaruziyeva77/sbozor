import { daysBetweenIsoDays } from "@/lib/format-day";

/*
 * =============================================================================
 * QARZ YOSHI — 0–30 / 31–60 / 61–90 / 90+ (dizayn talabi).
 *
 * Manba: `Sbozor Direktor - Hisobot.dc.html` (MCP orqali o'qildi
 * 2026-08-19) — qarzdorlar reestrida to'rtta yosh ustuni.
 *
 * ⛔⛔ SERVER YOSH GURUHLARINI BERMAYDI VA BU YERDA HISOBLANADI —
 *     LEKIN IKKINCHI HAQIQAT MANBAI TUG'ILMAYDI.
 *
 * `ReceivablesReportRow` da ikkita maydon bor: `outstanding_soum` (qancha)
 * va `oldest_debt_date` (qachondan beri). Guruh AYNAN shu ikkisidan
 * chiqadi — yangi son o'ylab topilmaydi, mavjud son GURUHGA joylanadi.
 *
 * ⛔ SOTUVCHINING BUTUN QARZI BITTA GURUHGA TUSHADI — eng eski qarzi
 *    bo'yicha. Sabab mexanik: server qarzni sanalar bo'yicha ajratib
 *    bermaydi, faqat yig'indi va eng eski sanani beradi. Yig'indini
 *    guruhlarga «taqsimlash» esa TO'QIMA bo'lardi — biz bilmaydigan
 *    narsani bilgandek ko'rsatish.
 *
 *    ⚠ Shuning uchun ustun sarlavhasi «qancha qarz shu yoshda» emas,
 *      «shu yoshdagi qarzdorlarning jami qarzi» ma'nosini beradi va
 *      jadval izohida shu yoziladi.
 *
 * ⛔ `oldest_debt_date === null` — GURUHLANMAYDI. Sana o'lchanmagan
 *    bo'lsa uni «0–30 kun» ga qo'yish eng yosh guruhga soxta yengillik
 *    berardi; bunday qatorlar alohida `unknown` da qoladi.
 * =============================================================================
 */

/** Guruh chegaralari — dizayndagi to'rtlik. */
export const AGE_BUCKETS = ["b0", "b31", "b61", "b90"] as const;
export type AgeBucket = (typeof AGE_BUCKETS)[number];

export type AgingRow = {
  outstanding_soum: number;
  oldest_debt_date: string | null;
};

export type AgingTotals = Record<AgeBucket | "unknown", number>;

/** Bitta qator qaysi guruhga tushishini aytadi. `null` — o'lchanmagan. */
export function bucketOf(
  row: AgingRow,
  todayIso: string,
): AgeBucket | null {
  if (row.oldest_debt_date === null) return null;

  const days = daysBetweenIsoDays(row.oldest_debt_date, todayIso);
  if (days === null) return null;

  if (days <= 30) return "b0";
  if (days <= 60) return "b31";
  if (days <= 90) return "b61";
  return "b90";
}

/**
 * Barcha qatorlarni guruhlar bo'yicha yig'adi.
 *
 * ⛔ MANFIY QOLDIQ (ortiqcha to'lov) YIG'INDIGA KIRMAYDI: u qarz emas
 *    va yosh guruhida ko'rsatilsa, qarzdorlik jami sun'iy kamayardi.
 */
export function sumByAge(
  rows: readonly AgingRow[],
  todayIso: string,
): AgingTotals {
  const totals: AgingTotals = {
    b0: 0,
    b31: 0,
    b61: 0,
    b90: 0,
    unknown: 0,
  };

  for (const row of rows) {
    if (row.outstanding_soum <= 0) continue;

    const bucket = bucketOf(row, todayIso);
    if (bucket === null) totals.unknown += row.outstanding_soum;
    else totals[bucket] += row.outstanding_soum;
  }

  return totals;
}
