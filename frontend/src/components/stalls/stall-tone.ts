import { AlertCircle, Ban, Check, Minus, Tent, TriangleAlert, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type {
  StallDayStateKey,
  StallTone,
} from "@/components/stalls/stall-map-types";
import type { StallStatusValue } from "@/lib/api-types";
import type { MapDayState } from "@/lib/map-day-queries";

/*
 * =============================================================================
 * Xarita katagining USLUB xaritasi (UI-SPEC §7.2 / §7.4).
 *
 * IKKI QATLAM, IKKI MANBA:
 *
 *   INVENTAR toni (`toneOf`)   — `stalls.status` dan. RANG (hue) YO'Q:
 *                                D-20 "faol (neytral), ta'mirda (kulrang),
 *                                yopiq (o'chgan)" deydi va butun hue
 *                                maydonini to'lov qatlamiga qoldiradi.
 *   TO'LOV toni (`dayToneOf`)  — SERVER bergan `MapDayState` dan
 *                                (quick 260816-75e, D-C1). Hue AYNAN shu
 *                                yerda ishlatiladi va u inventar tonining
 *                                USTIGA qo'yiladi.
 *
 * Har ikkala qatlamda ham rang YAGONA SIGNAL EMAS (WCAG 1.4.1, §4.4):
 * yonida chegara turi, ikonka va matn (legenda + `aria-label` bo'lagi)
 * turadi.
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
    /*
     * ⛔ YARMARKA — INVENTAR QATLAMIDA RANG OLADIGAN YAGONA HOLAT (0028).
     *
     *   `maintenance`/`closed` rangsiz (D-20 hue'ni to'lov qatlamiga
     *   qoldiradi), `fair` esa ISTISNO va sabab pulda: bu holatning
     *   MA'NOSI «patta olinmaydi», ya'ni u to'lov qatlamining o'zi.
     *   Teal — beshinchi mustaqil hue (`--color-info`), to'rttala
     *   to'lov rangidan ajralib turadi.
     */
    case "fair":
      return "fair";
  }
}

/**
 * Server bergan KUNLIK holatdan katak toniga (D-C1).
 *
 * ⛔ USTUVORLIK BU YERDA QO'LLANMAYDI — u SERVERDA, `billing_repo.
 *    _map_day_state()` da, BITTA sof funksiyada bajarilgan. Bu yerda
 *    faqat «qiymat -> uslub» maps'i bor. Qoidani ikkinchi marta yozish
 *    ikki tilda ikki haqiqat yaratardi.
 *
 * ⛔ `no_billing` uchun `null`: yopiq kunda yoki tarifsiz rastada rang
 *    QO'YILMAYDI va katak inventar tonida qoladi. Unga kulrang
 *    «to'lanmagan» rangi berish hisob yo'qligini qarzdorlikdan
 *    ajratmasdi, «to'landi» deb chizish esa YOLG'ON bo'lardi.
 *
 * ⚠ `default` TARMOG'I YO'Q — `toneOf()` bilan aynan bir xil sabab:
 *   serverga oltinchi holat qo'shilsa kod KOMPILYATSIYA BO'LMAYDI.
 */
export function dayToneOf(state: MapDayState): StallTone | null {
  switch (state) {
    case "paid":
      return "paid";
    case "due":
      return "debt";
    case "mismatch":
      return "mismatch";
    case "free":
      return "free";
    case "no_billing":
      return null;
    case "fair":
      return "fair";
  }
}

/**
 * Kunlik holatning SO'ZI — rangdan mustaqil kanal (WCAG 1.4.1).
 *
 * ⚠ TO'LIQ `Record`, `switch` EMAS: bu sof ma'lumot va `Record` da kalit
 *   tushib qolsa KOMPILYATSIYA XATOSI bo'ladi. `no_billing` ham kalitga
 *   EGA — u rangsiz, lekin SO'ZSIZ emas: legenda «bugun hisob yo'q»
 *   satrini aynan shundan oladi.
 */
export const DAY_STATE_KEYS: Record<MapDayState, StallDayStateKey> = {
  paid: "map.dayStatePaid",
  due: "map.dayStateDue",
  mismatch: "map.dayStateMismatch",
  free: "map.dayStateFree",
  no_billing: "map.dayStateNoBilling",
  fair: "map.dayStateFair",
};

/**
 * Uslub xaritasi — TO'LIQ (exhaustive) `Record`.
 *
 * ⚠ `Partial<Record<...>>` ham, `switch` + `default` ham ATAYIN RAD ETILGAN
 * (T-02-105). To'liq `Record` da kalit tushib qolsa **kompilyatsiya
 * xatosi** bo'ladi; muqobil variantlarda esa `debt` uslubini yozishni
 * unutib, qarzdor rastani jimgina "hammasi joyida" ko'rinishida chizsa
 * bo'lardi — bu esa aynan mahsulot fosh qilishi kerak bo'lgan holat.
 *
 * Chegara RANGI (`border-border-ui`) va o'lchamlar barcha tone'lar uchun
 * bir xil, shuning uchun ular katakning ASOSIY sinflarida turadi; bu yerda
 * faqat FARQ qiladigan qism yoziladi.
 *
 * ⛔ YANGI `@theme` TOKENI YARATILMAGAN (globals.css cheklovi): to'rtala
 *    to'lov toni ham MAVJUD semantik tokenlardan quriladi va ularning
 *    kontrasti o'sha faylda o'lchangan — `*-text` variantlari AYNAN tint
 *    fon ustida AA dan o'tadi (`--color-warning` esa matn rangi sifatida
 *    HECH QACHON ishlatilmaydi).
 */
/*
 * ⛔⛔ TINTLAR 10% -> 18–30% VA RANGLI HALQA QO'SHILDI (2026-08-25).
 *
 *   Foydalanuvchi topilmasi: «rastalarni ranglarga bo'yash — kamida
 *   5 xil rang». 10% tint deyarli oq edi va besh holat bir-biridan
 *   faqat ikonka bilan ajralardi. Endi BESH mustaqil hue (indigo ·
 *   qizil · amber · yashil · teal) + har katakda o'sha rangning
 *   halqasi — xarita bir qarashda o'qiladi.
 *
 * ⚠ MATN TOKENLARI O'ZGARMADI: `*-text` qiymatlari tint fonda AA dan
 *   o'lchangan; tintni quyuqlashtirish kontrastni faqat OSHIRADI
 *   (matn to'q, fon esa oqdan uzoqlashdi).
 */
export const TONE_STYLES: Record<StallTone, string> = {
  neutral: "bg-surface text-text font-semibold",
  muted: "bg-surface-muted text-text-muted",
  off: "bg-surface-muted text-text-muted line-through",
  paid: "bg-accent/20 text-accent-text font-semibold ring-1 ring-inset ring-accent/45",
  debt: "bg-danger/18 text-danger-text font-semibold ring-1 ring-inset ring-danger/45",
  mismatch:
    "bg-warning/30 text-warning-text font-semibold ring-1 ring-inset ring-warning/60",
  free: "bg-success/18 text-success-text ring-1 ring-inset ring-success/45",
  fair: "bg-info/20 text-info-text font-semibold ring-1 ring-inset ring-info/45",
};

/**
 * TO'LOV ikonkalari — rangdan mustaqil IKKINCHI kanal.
 *
 * ⛔ INVENTAR TONLARI UCHUN `null` VA BU ATAYIN: `muted`/`off`
 *    ikonkalari (`Wrench`/`Ban`) katakning YUQORI-O'NG burchagida,
 *    to'lov ikonkasi esa PASTKI-CHAP burchagida chiziladi — ikkalasi bir
 *    vaqtda ko'rinishi mumkin va shuning uchun ular ARALASHTIRILMAYDI.
 *
 * ⚠ `neutral` ham `null`: inventar «faol» holati ikonkasiz qoladi
 *   (2-fazadan beri) va bu yerda o'zgarmaydi.
 */
export const DAY_TONE_ICONS: Record<StallTone, LucideIcon | null> = {
  neutral: null,
  muted: null,
  off: null,
  paid: Check,
  debt: AlertCircle,
  mismatch: TriangleAlert,
  free: Minus,
  /*
   * ⛔ `null` — yarmarka ikonkasi INVENTAR burchagida (`Tent`), to'lov
   *   burchagida uni TAKRORLASH bitta katakka ikkita chodir chizardi.
   */
  fair: null,
};

/**
 * INVENTAR ikonkalari — yuqori-o'ng burchak (2-fazadan beri o'zgarmagan).
 *
 * ⚠ Ro'yxat `DAY_TONE_ICONS` dan ALOHIDA: ikkala to'plam bitta `Record`
 *   ga birlashtirilsa bitta katak IKKI ikonkani bir joyda chizishi
 *   kerak bo'lardi va ular ustma-ust tushardi.
 */
export const INVENTORY_TONE_ICONS: Record<StallTone, LucideIcon | null> = {
  neutral: null,
  muted: Wrench,
  off: Ban,
  paid: null,
  debt: null,
  mismatch: null,
  free: null,
  fair: Tent,
};

/**
 * Katak uslubidan HOLAT SO'ZIGA — faqat `aria-label` uchun.
 *
 * `StallCell` kontraktida `status` YO'Q (§7.2 dan aynan), skrinrider esa
 * holatni eshitishi SHART, shuning uchun so'z `tone` dan tiklanadi.
 *
 * ⛔ TO'LOV TONLARI `active` GA TUSHADI VA BU TO'G'RI: ular rastaning
 *    HOLATI emas, uning ustiga qo'yiladigan TO'LOV holati — rasta o'zi
 *    faol bo'lib qolaveradi. To'lov ma'nosi `aria-label` ga ALOHIDA
 *    bo'lak sifatida qo'shiladi (`DAY_STATE_KEYS`), ya'ni skrinrider
 *    ikkala faktni ham ALOHIDA eshitadi.
 *
 * ⚠ Bu xarita FAQAT `cell.tone` (inventar) bilan chaqiriladi —
 *   `cell.dayTone` bilan EMAS. Aks holda to'lov qatlami rastaning
 *   reyestr holatini JIMGINA «faol» ga aylantirardi.
 */
export const TONE_STATUS: Record<StallTone, StallStatusValue> = {
  neutral: "active",
  muted: "maintenance",
  off: "closed",
  paid: "active",
  debt: "active",
  mismatch: "active",
  free: "active",
  fair: "fair",
};
