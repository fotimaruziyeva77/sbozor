import { shiftIsoDay } from "@/components/snapshots/day-picker";

/*
 * =============================================================================
 * DIREKTOR PANELINING DAVR MODELI (260819).
 *
 * ⛔⛔ NEGA PAYDO BO'LDI: panel KECHAGI kunga QOTIRILGAN edi va u buni
 *     sarlavhada ochiq aytardi ham («kechagi kun bo'yicha yopilgan
 *     raqamlar»). Foydalanuvchi buni nuqson deb baholadi va u haq:
 *     direktor «hozir qanday ketyapti» degan savol bilan ekranga
 *     qaraydi, kechagi kun bilan emas.
 *
 * ⛔⛔ VA BUGUNGI TUSHUMNI KO'RSATISH TEXNIK JIHATDAN MUMKIN — TEKSHIRILDI.
 *
 *     `report_repo._REVENUE_BY_DAY` to'lovlarni `payments.business_date`
 *     bo'yicha TO'G'RIDAN-TO'G'RI o'qiydi; «kun yopilgan bo'lsin» degan
 *     shart u yerda YO'Q. Ya'ni kassir to'lovni yozishi bilan u shu
 *     so'rovga tushadi. Panelning kechagi kunga qotirilishi ma'lumot
 *     cheklovi emas, EHTIYOTKORLIK qarori edi.
 *
 * ⛔ LEKIN BIR TOMONI HAQIQATAN TAYYOR EMAS: `charged_soum` (hisoblangan
 *    patta) `daily_charges` dan keladi va u kunlik hisoblash yurgandan
 *    keyin paydo bo'ladi. Shuning uchun BUGUN tanlanganda «yig'ilish
 *    darajasi» soxta 0% yoki 100% qilib chizilmaydi — u «hali
 *    hisoblanmagan» deb aytiladi. Yolg'on foiz hokimga ko'rsatiladigan
 *    ekranda eng qimmat xato bo'lardi.
 *
 * ⛔ Taqqoslash davri MA'NOLI tanlanadi, «oldingi N kun» emas:
 *      · bitta kun    -> O'TGAN HAFTA SHU KUNI (bozorda hafta kuni
 *                        savdo hajmini belgilaydi: dushanba ≠ shanba);
 *      · ko'p kunlik  -> BEVOSITA oldingi teng uzunlikdagi davr.
 * =============================================================================
 */

/** Yopiq reyestr — yangi rejim faqat shu ro'yxat bilan BIRGA qo'shiladi. */
export const PERIOD_KINDS = [
  "today",
  "yesterday",
  "week",
  "month",
  "custom",
] as const;

export type PeriodKind = (typeof PERIOD_KINDS)[number];

export type Period = {
  kind: PeriodKind;
  /** Davrning birinchi kuni (ISO `YYYY-MM-DD`, kiradi). */
  from: string;
  /** Davrning oxirgi kuni (kiradi). */
  to: string;
};

/** Ekrandagi yorliqlar — bitta manba (piker ham, sarlavha ham shundan). */
export const PERIOD_LABEL: Readonly<Record<PeriodKind, string>> = {
  today: "Bugun",
  yesterday: "Kecha",
  week: "7 kun",
  month: "30 kun",
  custom: "Oraliq",
};

/** Tayyor rejimning kun oralig'i. `custom` — chaqiruvchi o'zi beradi. */
export function periodRange(kind: Exclude<PeriodKind, "custom">, todayIso: string): Period {
  switch (kind) {
    case "today":
      return { kind, from: todayIso, to: todayIso };
    case "yesterday": {
      const day = shiftIsoDay(todayIso, -1);
      return { kind, from: day, to: day };
    }
    case "week":
      return { kind, from: shiftIsoDay(todayIso, -6), to: todayIso };
    case "month":
      return { kind, from: shiftIsoDay(todayIso, -29), to: todayIso };
  }
}

/** Davr uzunligi kunlarda (ikkala chegara ham kiradi). */
export function periodDays(period: Period): number {
  const from = Date.parse(`${period.from}T00:00:00Z`);
  const to = Date.parse(`${period.to}T00:00:00Z`);
  return Math.round((to - from) / 86_400_000) + 1;
}

/**
 * Taqqoslash davri (modul sarlavhasidagi qoida).
 *
 * ⛔ Bitta kun uchun `-7`: bozorda hafta kuni savdo hajmini belgilaydi va
 *    dushanbani yakshanba bilan solishtirish soxta «pasayish» ko'rsatardi.
 */
export function comparePeriod(period: Period): Period {
  const days = periodDays(period);
  if (days === 1) {
    const day = shiftIsoDay(period.from, -7);
    return { kind: period.kind, from: day, to: day };
  }
  return {
    kind: period.kind,
    from: shiftIsoDay(period.from, -days),
    to: shiftIsoDay(period.from, -1),
  };
}

/** Davr BUGUNNI o'z ichiga oladimi — «to'liq emas» ogohlantirishi uchun. */
export function includesToday(period: Period, todayIso: string): boolean {
  return period.from <= todayIso && todayIso <= period.to;
}

/** Taqqoslash matni — davr shakliga qarab (ekranda ikki xil jumla). */
export function compareNote(period: Period): string {
  return periodDays(period) === 1
    ? "o'tgan hafta shu kuniga nisbatan"
    : "oldingi teng davrga nisbatan";
}
