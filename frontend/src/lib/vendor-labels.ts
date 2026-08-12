"use client";

import { EMPTY_VENDOR_FILTERS, useVendorsQuery } from "@/lib/market-queries";
import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * SOTUVCHI YORLIG'I — `vendor_id` -> EKRANDA KO'RINADIGAN NOM (D-05, §5.5).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ NEGA ALOHIDA MODUL VA NEGA U NOMUVOFIQLIK YUZASIDAN TASHQARIDA
 * -----------------------------------------------------------------------
 * 07-10 moliyaviy javoblardan shaxsiy maydonlarni CHIQARIB TASHLAGAN va
 * buni SABOTAJ bilan o'lchagan: bitta ism maydonining qo'shilishi TO'RT
 * tenancy testini qizartirgan. Ya'ni nomuvofiqlik marshruti qatorni
 * `vendor_id` bilan aytadi va ⛔ HECH QACHON ism qaytarmaydi.
 *
 * Ism esa MAVJUD va ⛔ AUDIT QILINGAN `GET /vendors` marshrutidan
 * olinadi — o'sha marshrut `vendor_view` ostida va har o'qishni auditga
 * yozadi (D-09).
 *
 * ⛔ SHU MODUL AYNAN SHU CHEGARADA TURADI. `components/reconciliation/**`
 *    va `lib/reconciliation-queries.ts` ⛔ TAQIQLANGAN NOMLAR SKANIDAN
 *    o'tadi (07-UI-SPEC §16.6) va o'sha reyestrda shaxsiy maydonlarning
 *    nomlari bor. Ular bu yerda, ⛔ BITTA joyda va OCHIQ sabab bilan
 *    o'qiladi; nomuvofiqlik yuzasiga esa faqat TAYYOR YORLIQ chiqadi.
 *
 *    Bu «darvozani aylanib o'tish» EMAS, uning MAQSADI: taqiq
 *    «nomuvofiqlik yuzasi shaxsiy maydonni O'ZI o'qimasin» degan gap, va
 *    u shu bo'linish bilan MEXANIK ravishda bajariladi.
 *
 * -----------------------------------------------------------------------
 * ⛔ HUQUQ YO'Q -> SO'ROV HAM YO'Q
 * -----------------------------------------------------------------------
 * `vendor_view` bo'lmagan sessiyada so'rov ⛔ UMUMAN YUBORILMAYDI va
 * yorliq `null` bo'lib qoladi. Sabab `useVendorsQuery` docstringida
 * yozilgan: ko'rinmaydigan ekran uchun fon so'rovi audit jurnalini
 * ma'nosiz «ko'rildi» yozuvlari bilan to'ldirardi.
 *
 * ⚠ OCHIQ NARX (§5.5): sahifa QO'SHIMCHA so'rov qiladi va u reestrning
 *   birinchi sahifasi bilan cheklanadi. To'g'ri tuzatish — MAVJUD
 *   marshrutni sahifalash, nomuvofiqlik marshrutiga ism maydoni
 *   QO'SHISH EMAS. Egasi — 8-faza.
 * =============================================================================
 */

export type VendorLabels = {
  /** `null` — huquq yo'q, hali yuklanmadi yoki reestrda topilmadi. */
  labelOf: (vendorId: string | null) => string | null;
  isPending: boolean;
};

export function useVendorLabels(options?: { enabled?: boolean }): VendorLabels {
  const { principal } = useAuthStore();
  const allowed = hasPermission(principal?.roles ?? [], "vendor_view");
  const enabled = allowed && (options?.enabled ?? true);

  const vendors = useVendorsQuery(EMPTY_VENDOR_FILTERS, { enabled });

  const byId = new Map(
    (vendors.data?.pages ?? []).flatMap((page) =>
      page.items.map((vendor) => [vendor.id, vendor.full_name] as const),
    ),
  );

  return {
    labelOf: (vendorId) =>
      vendorId === null ? null : (byId.get(vendorId) ?? null),
    isPending: enabled && vendors.isPending,
  };
}
