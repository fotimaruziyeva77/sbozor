import type { StallTone } from "@/components/stalls/stall-map-types";
import type { StallStatusValue } from "@/lib/api-types";

/*
 * =============================================================================
 * Xarita katagining USLUB xaritasi (UI-SPEC §7.2 / §7.4).
 *
 * RANG (hue) UMUMAN ISHLATILMAYDI. D-20 "faol (neytral), ta'mirda (kulrang),
 * yopiq (o'chgan)" ni aynan shunday talqin qiladi va butun hue maydonini
 * 6–7 fazalarga (to'langan / qarzdor / nomuvofiqlik) BO'SH qoldiradi.
 * Holat farqi to'ldirish + chegara turi + ikonka + matn uslubi bilan
 * beriladi, ya'ni rang yagona signal emas (WCAG 1.4.1, §4.4).
 * =============================================================================
 */

/**
 * Rasta holatidan katak uslubiga.
 *
 * ⚠ `default` TARMOG'I ATAYIN YO'Q: `StallStatusValue` — yopiq birlashma
 * va TypeScript to'liqlikni O'ZI tekshiradi. `default` qo'shilsa DB'ga
 * yangi holat qiymati kiritilganda kompilyator jim qolardi va yangi holat
 * jimgina "faol" bo'lib chizilardi.
 */
export function toneOf(stall: { status: StallStatusValue }): StallTone {
  switch (stall.status) {
    case "active":
      return "neutral";
    case "maintenance":
      return "muted";
    case "closed":
      return "off";
  }
}

/**
 * Uslub xaritasi — TO'LIQ (exhaustive) `Record`.
 *
 * ⚠ `Partial<Record<...>>` ham, `switch` + `default` ham ATAYIN RAD ETILGAN
 * (T-02-105). To'liq `Record` da kalit tushib qolsa **kompilyatsiya
 * xatosi** bo'ladi; muqobil variantlarda esa 6-faza `debt` uslubini
 * yozishni unutib, qarzdor rastani jimgina "hammasi joyida" ko'rinishida
 * chizardi — bu esa aynan mahsulot fosh qilishi kerak bo'lgan holat.
 *
 * Chegara RANGI (`border-border-ui`) va o'lchamlar barcha tone'lar uchun
 * bir xil, shuning uchun ular katakning ASOSIY sinflarida turadi; bu yerda
 * faqat FARQ qiladigan qism yoziladi.
 */
export const TONE_STYLES: Record<StallTone, string> = {
  neutral: "bg-surface text-text font-semibold",
  muted: "bg-surface-muted text-text-muted",
  off: "bg-surface-muted text-text-muted line-through",
  // 6–7 fazalar bu uchtasini TO'LDIRADI. Hozircha `neutral` bilan bir xil:
  // ular 2-fazada HECH QACHON hosil qilinmaydi (`toneOf` ularni
  // qaytarmaydi), lekin `Record` to'liqligi yuqoridagi kafolatni beradi.
  paid: "bg-surface text-text font-semibold",
  debt: "bg-surface text-text font-semibold",
  mismatch: "bg-surface text-text font-semibold",
};

/**
 * Katak uslubidan HOLAT SO'ZIGA — faqat `aria-label` uchun.
 *
 * `StallCell` kontraktida `status` YO'Q (§7.2 dan aynan), skrinrider esa
 * holatni eshitishi SHART, shuning uchun so'z `tone` dan tiklanadi.
 *
 * 6–7 fazalarning uch qiymati `active` ga tushadi va bu to'g'ri: ular
 * rastaning HOLATI emas, uning ustiga qo'yiladigan TO'LOV holati — rasta
 * o'zi faol bo'lib qolaveradi. To'lov ma'nosi o'sha fazalarda `aria-label`
 * ga alohida bo'lak sifatida qo'shiladi.
 */
export const TONE_STATUS: Record<StallTone, StallStatusValue> = {
  neutral: "active",
  muted: "maintenance",
  off: "closed",
  paid: "active",
  debt: "active",
  mismatch: "active",
};
