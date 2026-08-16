"use client";

import { useEffect } from "react";

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
 * -----------------------------------------------------------------------
 * ⛔⛔ LUG'AT REESTRNI ⛔ TO'LIQ SAHIFALAB O'QIYDI (07 №2, D-08)
 * -----------------------------------------------------------------------
 * Ilgari u ⛔ BIRINCHI SAHIFA bilan cheklangan edi (`fetchNextPage()`
 * HECH QACHON chaqirilmasdi), ya'ni 50 dan ortiq sotuvchili bozorda
 * ro'yxatning quyi qismidagi HAR qator «Ko'rsatilmagan» yorlig'ini
 * olardi — Karmana konvertida (300–1000 rasta) bu ⛔ ODATIY hol edi.
 *
 * ⛔ D-08 IKKI MEXANIKADAN BIRINI ruxsat beradi va tanlangani —
 *    ⛔ MAVJUD, AUDIT QILINGAN marshrutni ⛔ SAHIFALASH. Nomuvofiqlik
 *    marshrutiga `vendor_name` maydoni ⛔ QO'SHILMAYDI: 07-10 buni
 *    SABOTAJ bilan o'lchagan — ism qo'shilganda TO'RT tenancy testi
 *    qizaradi.
 * =============================================================================
 */

/**
 * ⛔⛔ YORLIQ LUG'ATI UCHUN O'QILADIGAN SAHIFALARNING ENG KO'P SONI.
 *
 * =========================================================================
 * ⛔ BU QO'RIQCHI MUZOKARASIZ VA SABAB IKKITA:
 *
 *   1. ⛔ AUDIT SHOVQINI — `GET /vendors` HAR chaqiruvda `audit_read`
 *      yozadi (D-09). Chegarasiz halqa katta reestrda jurnalni ma'nosiz
 *      «ko'rildi» yozuvlari bilan to'ldirardi va nizo tekshiruvida
 *      HAQIQIY o'qishlar ular orasida ko'rinmay qolardi.
 *
 *   2. ⛔ CHEKSIZ HALQA — server kursori buzilgan (yoki hech qachon
 *      tugamaydigan) holatda so'rovlar ⛔ TO'XTAMASDI va bunda
 *      ⛔ BIRORTA XATO ham chiqmasdi: har javob `200`.
 *
 * ⛔ CHEGARAGA YETILGANDA QOLGAN ISMLAR ⛔ BO'SH KATAK BO'LIB QOLADI —
 *    `labelOf()` `null` qaytaradi va bu ⛔ KUTILGAN XULQ (kod izohida,
 *    konsolda EMAS: ogohlantirish har render takrorlanardi va hech kim
 *    o'qimasdi). Yorliqni TO'QISH («—», «Noma'lum», identifikator
 *    bo'lagi) nizo hujjatiga (D-02) YOLG'ON ism kiritardi — 05-14 darsi.
 *
 * ⚠ SIG'IM: 20 × `PAGE_SIZE` (50) = 1000 sotuvchi. Karmana pilotining
 *   yuqori chegarasi ~1000 RASTA, ya'ni sotuvchi soni undan KAM — chegara
 *   amaliyotda urilmaydi. O'lchov (`vendor-labels.test.tsx`): 120
 *   sotuvchili bozor AYNAN 3 so'rov, bitta sahifali bozor AYNAN 1 so'rov.
 * =========================================================================
 */
export const MAX_LABEL_PAGES = 20;

export type VendorLabels = {
  /** `null` — huquq yo'q, hali yuklanmadi, chegaradan keyin yoki topilmadi. */
  labelOf: (vendorId: string | null) => string | null;
  isPending: boolean;
};

export function useVendorLabels(options?: { enabled?: boolean }): VendorLabels {
  const { principal } = useAuthStore();
  const allowed = hasPermission(principal?.roles ?? [], "vendor_view");
  const enabled = allowed && (options?.enabled ?? true);

  const vendors = useVendorsQuery(EMPTY_VENDOR_FILTERS, { enabled });

  const pageCount = vendors.data?.pages.length ?? 0;
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = vendors;

  /*
   * ⛔⛔ KEYINGI SAHIFA `useEffect` DA, ⛔ RENDER PAYTIDA EMAS.
   *
   * Render paytidagi yon ta'sir React'ning `StrictMode` ikki chaqirig'ida
   * so'rovni ⛔ IKKILANTIRARDI va u AUDIT jurnaliga ham ikki qator
   * yozardi — ya'ni tuzatishning O'ZI 1-qo'riqchining sababini buzardi.
   *
   * ⛔ `staleTime` / kesh siyosati ⛔ TEGILMAYDI: sahifalar `useVendorsQuery`
   *    ning MAVJUD kalitiga (`vendorsKey(marketId, filtrlar)`) qo'shiladi,
   *    ya'ni reestr sahifasi bilan AYNI kesh yozuvi ishlatiladi va
   *    ikkinchi manba TUG'ILMAYDI.
   */
  useEffect(() => {
    if (!enabled) return;
    if (!hasNextPage) return;
    if (isFetchingNextPage) return;
    if (pageCount >= MAX_LABEL_PAGES) return;
    void fetchNextPage();
  }, [enabled, hasNextPage, isFetchingNextPage, pageCount, fetchNextPage]);

  const byId = new Map(
    (vendors.data?.pages ?? []).flatMap((page) =>
      page.items.map((vendor) => [vendor.id, vendor.full_name] as const),
    ),
  );

  return {
    /*
     * ⛔ ZAXIRA YO'Q: topilmagan identifikator `null` bo'lib qaytadi va
     *   chaqiruvchi o'z NOMLANGAN holatini chizadi. Bu modul HECH NIMA
     *   to'qimaydi (yuqoridagi 2-qo'riqcha).
     */
    labelOf: (vendorId) =>
      vendorId === null ? null : (byId.get(vendorId) ?? null),
    /*
     * ⛔ «Yuklanmoqda» — BIRINCHI sahifa kelgunicha. Keyingi sahifalar
     *   FONDA yig'iladi va ular yorliqlarni ⛔ BLOKLAMAYDI: 50-chi
     *   qatorgacha bo'lgan ismlar darhol ko'rinadi.
     */
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
