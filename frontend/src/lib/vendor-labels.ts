"use client";

import { EMPTY_VENDOR_FILTERS, useVendorsQuery } from "@/lib/market-queries";
import { useAuthStore } from "@/lib/auth-store";
import { useUsersQuery } from "@/lib/queries";
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

/* -------------------------------------------------------------------------- */
/* MAS'UL — `assignee_user_id` -> EKRANDA KO'RINADIGAN NOM (§5.5, DL-5)        */
/* -------------------------------------------------------------------------- */

/**
 * ⛔⛔ NEGA BU SHU MODULDA VA NEGA `user-labels.ts` OCHILMADI.
 *
 * Modulning chegarasi «sotuvchi» EMAS: u ⛔ **shaxsiy ISMNI TAQIQLANGAN
 * YUZADAN TASHQARIDA o'qish** chegarasi. `full_name` tokeni
 * `components/reconciliation/**` da ham, `lib/reconciliation-queries.ts`
 * da ham ⛔ **0** ga qulflangan (07-UI-SPEC §16.6) — ya'ni mas'ulning
 * ismi ham AYNAN SHU tomonda o'qilishi kerak.
 *
 * Ikkinchi modul ochish o'sha chegarani ⛔ **IKKIGA** bo'lardi: keyingi
 * ijrochi uchinchisini ochish uchun pretsedent topardi va taqiq
 * «qaysi fayl skanlanadi?» degan kontekstga bog'liq shartga aylanardi.
 * Bu yerda esa qoida bitta jumla: ⛔ **ism SHU faylda o'qiladi, yuzaga
 * faqat TAYYOR YORLIQ chiqadi.**
 *
 * ⛔ HUQUQ YO'Q -> SO'ROV HAM YO'Q: `user_view` bo'lmagan sessiyada
 *    `GET /users` ⛔ **umuman yubormaydi** (`useVendorLabels` bilan
 *    aynan bir qoida — ko'rinmaydigan ekran uchun fon so'rovi audit
 *    jurnalini ma'nosiz yozuvlar bilan to'ldirardi).
 */
export type AssigneeOption = {
  id: string;
  /** ⛔ TAYYOR YORLIQ: ism bo'lmasa identifikatorning qisqa shakli. */
  label: string;
};

export type AssigneeLabels = {
  /** `null` — biriktirilmagan, huquq yo'q yoki reestrda topilmadi. */
  labelOf: (userId: string | null) => string | null;
  /** DL-5 dagi native `<select>` ning variantlari — BARQAROR tartibda. */
  options: readonly AssigneeOption[];
  isPending: boolean;
};

export function useAssigneeLabels(options?: {
  enabled?: boolean;
}): AssigneeLabels {
  const { principal } = useAuthStore();
  const allowed = hasPermission(principal?.roles ?? [], "user_view");
  const enabled = allowed && (options?.enabled ?? true);

  const users = useUsersQuery({ enabled });

  const items = users.data?.items ?? [];

  /*
   * ⚠ FAOL BO'LMAGAN FOYDALANUVCHI VARIANTLARDA YO'Q, lekin YORLIQDA
   *   BOR: bloklangan xodimga YANGI case biriktirib bo'lmaydi, ammo u
   *   ilgari biriktirilgan case'da ⛔ NOMI BILAN ko'rinishi SHART —
   *   aks holda audit izi «kimdir» ga aylanardi.
   */
  /*
   * ⛔⛔ ZAXIRA — IDENTIFIKATORNING QISQA SHAKLI, ⛔ TELEFON RAQAMI EMAS.
   *
   * Telefon raqami — O'zR qonuni ostidagi ⛔ SHAXSIY MA'LUMOT va u
   * ⛔ UI BEZAGI bo'lolmaydi. Eski zaxira (ism yo'q bo'lganda RAQAM)
   * uni ikki yuzaga chiqarardi: mas'ul TANLAGICHIGA va ⛔ AUDIT IZIGA —
   * ya'ni raqam nizo hujjatining (D-02) o'zgarmas nusxasiga tushardi.
   *
   * ⛔ `ActorLabel` NING O'Z IZOHI SHUNI KO'ZDA TUTGAN: «Ism kelmasa
   *    identifikatorning qisqa shakli — bo'sh katak EMAS». Ya'ni bu
   *    tuzatish yangi qoida joriy qilmaydi, ⛔ ALLAQACHON YOZILGAN
   *    qoidani tiklaydi.
   *
   * ⛔ IKKI JOYDA BIR VAQTDA (`byId` va `options`): faqat bittasini
   *    tuzatish raqamni ikkinchisida qoldirardi va darvoza «tuzatildi»
   *    deb yashil bo'lardi.
   */
  const labelOfUser = (user: { id: string; full_name: string | null }) =>
    user.full_name ?? user.id.slice(0, 8);

  const byId = new Map(items.map((user) => [user.id, labelOfUser(user)] as const));

  return {
    labelOf: (userId) => (userId === null ? null : (byId.get(userId) ?? null)),
    options: items
      .filter((user) => user.is_active)
      .map((user) => ({ id: user.id, label: labelOfUser(user) })),
    isPending: enabled && users.isPending,
  };
}
