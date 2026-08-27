"use client";

import { memo } from "react";
import { useTranslations } from "next-intl";

import type { StallCell as StallCellData } from "@/components/stalls/stall-map-types";
import {
  DAY_TONE_ICONS,
  INVENTORY_TONE_ICONS,
  TONE_STATUS,
  TONE_STYLES,
} from "@/components/stalls/stall-tone";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * Xaritaning bitta katagi — HAQIQIY `<button type="button">`.
 *
 * Canvas renderer (RESEARCH Pattern 11) aynan shu sababdan rad etilgan:
 * canvasda tugma yo'q, ya'ni klaviatura ham, skrinrider ham ishlamaydi va
 * SSR umuman bo'lmaydi. Bu yerda esa har katak brauzer beradigan barcha
 * xulqni tekinga oladi (Enter/Space, fokus, `aria-label`).
 *
 * ⚠ TANLANGAN RASTA ID'SI BU PROPLARDA YO'Q va bo'lmasligi ham kerak
 * (Pitfall 8): "bu katak tanlanganmi?" ma'nosini beradigan har qanday
 * prop har bosishda 1000 katakni qayta render qilardi, chunki u har
 * katakda o'zgaradi. Tanlangan ID sahifa holatida yashaydi va faqat
 * `<Dialog>` uni o'qiydi. Taqiqning literal prop nomlari bu izohda
 * yozilmaydi — qoida mexanik grep darvozasi bilan qulflangan.
 *
 * `memo` bilan o'ralgan: proplar o'zgarmasa render umuman bo'lmaydi.
 * Roving tabindex `tabIndex` propini FAQAT ikkita katakda o'zgartiradi
 * (eskisi va yangisi), ya'ni klaviatura bilan yurish ham arzon.
 * =============================================================================
 */

export type StallCellProps = {
  cell: StallCellData;
  /** DB kontenti — tarjima qilinmaydi (D-16). */
  zoneName: string;
  /** DB kontenti; xarita endpointida yo'q bo'lsa `null`. */
  categoryName: string | null;
  /** DB kontenti; xarita endpointida yo'q bo'lsa `null`. */
  vendorName: string | null;
  onSelect: (stallId: string) => void;
  /** Roving tabindex: zonada AYNAN BITTA katak `0` oladi (§7.7). */
  tabIndex: number;
};

/**
 * Matn sig'imi (§7.4).
 *
 * Karmanada kodlar 1–1000 (≤4 belgi), ya'ni >6 — degenerativ holat. Lekin
 * u JIMGINA buzilmasligi kerak: uzun kod kesiladi va to'liq qiymati
 * `title` da qoladi. `aria-label` esa HECH QACHON kesilmaydi.
 */
function codeClassName(code: string): string {
  if (code.length <= 4) return "text-sm";
  if (code.length <= 6) return "text-xs";
  return "truncate text-xs";
}

export const StallCell = memo(function StallCell({
  categoryName,
  cell,
  onSelect,
  tabIndex,
  vendorName,
  zoneName,
}: StallCellProps) {
  const t = useTranslations();
  const tStatus = useTranslations("stalls.status");

  /*
   * `aria-label` TO'LIQ va kesilmaydi (§7.4). To'rt bo'lak: raqam, holat,
   * toifa, sotuvchi.
   *
   * Toifa va sotuvchi nomi `GET /stalls/map` javobida YO'Q (u ataylab
   * to'rt maydonli — 1000 rastali bozorda javob kichik qolsin). Server
   * `has_vendor` bayrog'ini beradi, ya'ni "biriktirilgan/biriktirilmagan"
   * farqi baribir eshitiladi; aniq ism rasta kartasida ko'rinadi.
   *
   * XAVFSIZLIK (T-02-110): `aria-label` MATN atributi — HTML sifatida
   * talqin qilinmaydi va React qiymatni ekranlaydi, ya'ni zona/sotuvchi
   * nomidagi belgilar razmetkaga aylanmaydi.
   */
  const baseLabel = t("map.cellLabel", {
    code: cell.code,
    // ⛔ INVENTAR toni bilan, `dayTone` bilan EMAS: to'lov qatlami
    //    rastaning REYESTR holatini almashtirmaydi (`TONE_STATUS` izohi).
    status: tStatus(TONE_STATUS[cell.tone]),
    category: categoryName ?? t("map.cellCategoryUnknown"),
    vendor:
      vendorName ??
      (cell.hasVendor
        ? t("map.cellVendorAssigned")
        : t("stalls.noVendor")),
  });

  /*
   * TO'LOV HOLATI — `aria-label` ning BESHINCHI, ALOHIDA bo'lagi.
   *
   * ⛔ Qatlam yo'q bo'lganda (huquq yo'q, qoralama bozor, hali
   *   yuklanmadi) jumla HOZIRGIDEK to'rt bo'lakli qoladi: bo'sh bo'lak
   *   qo'shish skrinriderga «... , , ...» deb o'qilardi va mavjud a11y
   *   testining to'rt bo'lakli da'vosini jimgina o'zgartirardi.
   */
  const label =
    cell.dayStateKey === null
      ? baseLabel
      : `${baseLabel}, ${t(cell.dayStateKey)}`;

  const InventoryIcon = INVENTORY_TONE_ICONS[cell.tone];
  const DayIcon = cell.dayTone === null ? null : DAY_TONE_ICONS[cell.dayTone];

  return (
    <button
      aria-label={label}
      className={cn(
        // 44x44 — WCAG 2.5.5 barmoq nishoni (§2 hujjatlashtirilgan istisnosi).
        "relative inline-flex aspect-square min-h-11 min-w-11 items-center justify-center",
        "rounded-sm border border-border-ui p-1 tabular-nums",
        "transition-colors",
        // Hover CHEGARA rangi bilan: `hover:bg-surface-muted` "ta'mirda" va
        // "yopiq" kataklarida umuman ko'rinmasdi — ular allaqachon shu fonda.
        "hover:border-text-muted",
        "active:scale-[0.97] motion-reduce:scale-100",
        // Global fokus qoidasi `offset: 2px` beradi; 8px oraliqda ikki
        // tomondan 2+2 = 4px halqalar tegib ketardi. Katak uchun `offset-1`
        // -> 3px, 2px zaxira. `z-10` halqa qo'shni katak ostida qolmasin.
        "focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent",
        /*
         * ⛔ TO'LOV TONI INVENTAR TONINING USTIGA QO'YILADI, uni
         *   ALMASHTIRADI. `dayTone` `null` bo'lganda (qatlam yo'q yoki
         *   holat `no_billing`) katak inventar tonida qoladi — bu ikkala
         *   holatning ham YAGONA to'g'ri ko'rinishi.
         *
         * ⚠ `Record` TO'LIQ, ya'ni kalit tushib qolsa KOMPILYATSIYA
         *   XATOSI (`stall-tone.ts` ning butun mexanizmi shu).
         */
        TONE_STYLES[cell.dayTone ?? cell.tone],
        // Sotuvchisiz rasta — UZUQ-UZUQ chegara. Bu rangdan MUSTAQIL
        // ikkinchi kanal (§4.4) va legendada tushuntiriladi.
        cell.hasVendor ? "border-solid" : "border-dashed",
        codeClassName(cell.code),
      )}
      data-stall-code={cell.code}
      onClick={() => onSelect(cell.id)}
      tabIndex={tabIndex}
      /*
       * `title` FAQAT kod vizual kesilganda (§7.4). Yoniga zona nomi ham
       * qo'shiladi: kesilgan kodni ochadigan yagona ipucha ayni paytda
       * "bu qaysi zona edi?" savoliga ham javob bersin. D-16: ikkalasi
       * ham DB kontenti — tarjima qilinmaydi.
       */
      title={cell.code.length > 6 ? `${cell.code} · ${zoneName}` : undefined}
      type="button"
    >
      {/* INVENTAR ikonkasi — yuqori-o'ng, rangdan mustaqil kanal (§4.4). */}
      {InventoryIcon === null ? null : (
        <InventoryIcon
          aria-hidden="true"
          className="absolute top-1 right-1 size-3"
        />
      )}

      {/*
       * TO'LOV ikonkasi — PASTKI-CHAP burchak.
       *
       * ⛔ INVENTAR IKONKASI BILAN BIR VAQTDA KO'RINISHI MUMKIN (ta'mirdagi
       *   rasta ham patta to'laydi — `_market_projection()` qarori), ya'ni
       *   ikkalasi BOSHQA burchakda turishi SHART. Bitta burchakda ular
       *   ustma-ust tushib, ikkinchi kanal jimgina yo'qolardi.
       *
       * `data-day-tone` — o'lchov nuqtasi: ikonkaning MAVJUDLIGI ham,
       * uning QAYSI holatga tegishliligi ham testda ko'rinadi
       * (`data-stall-code` bilan bir xil naqsh).
       */}
      {DayIcon === null ? null : (
        <span
          aria-hidden="true"
          className="absolute bottom-1 left-1 inline-flex"
          data-day-tone={cell.dayTone}
        >
          <DayIcon className="size-3" />
        </span>
      )}

      {/*
       * KO'RINADIGAN matn kesilishi mumkin; `aria-label` esa to'liq.
       * D-16: rasta raqami DB kontenti — tarjima qilinmaydi.
       * `aria-hidden` — skrinrider `aria-label` ni o'qiydi, raqamni ikki
       * marta emas.
       */}
      <span aria-hidden="true" className="max-w-full">
        {cell.code}
      </span>
    </button>
  );
});
