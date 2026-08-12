"use client";

import {
  BillingDayPicker,
  useBillingDay,
} from "@/components/billing/day-picker";
import type { BillingDaySelection } from "@/components/billing/day-picker";

/*
 * =============================================================================
 * KUN TANLAGICHI — ⛔ IKKINCHI NUSXA YOZILMAYDI.
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA QAYTA ISHLATISH, NEGA KO'CHIRISH EMAS
 * -----------------------------------------------------------------------
 * Bu ekranning kun kontrakti 6-fazanikidan ⛔ AYNAN BIR XIL:
 *
 *   * standart — ⛔ KECHA (hisob D+1 04:10 da, navbat D+1 04:25 da
 *     tug'iladi; standarti «bugun» bo'lgan sahifa HAR DOIM bo'sh
 *     ochilardi va direktor «tizim ishlamayapti» degan xulosaga kelardi);
 *   * maksimum — ⛔ BUGUN (kelajak kuni imkonsiz);
 *   * URL holati — ⛔ faqat `?day=`, `nuqs` bilan.
 *
 * Ikkinchi nusxa bir kun `en-CA` formatlagichi yoki UTC arifmetikasi
 * bo'yicha ajralib ketardi va ⛔ IKKI EKRAN BOSHQA-BOSHQA biznes-kunni
 * ko'rsatardi — buni hech qanday test ko'rmasdi, chunki har nusxa O'Z
 * testi bilan kelardi. Aynan shu sabab bilan 6-faza ham sof
 * yordamchilarni 4-fazadan qayta ishlatgan.
 *
 * ⛔ VA BU YERDA HOOK HAM QAYTA ISHLATILADI, faqat yordamchilar emas:
 *    6-fazadagi hook'ning standarti ALLAQACHON «kecha» va sabab
 *    IKKALA ekranda ham BIR XIL (kunlik yopilish jadvali). 4-fazaning
 *    `useDaySelection()` i esa «bugun» beradi va u qayta ishlatilmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ BU KOMPONENT MAZMUN ATRIBUTINI CHIQARMAYDI
 * -----------------------------------------------------------------------
 * U — BOSHQARUV, ro'yxat emas: mazmun juftligi darvozasida `day` bloki
 * yagona istisno va istisnolar to'plamining O'LCHAMI alohida assert
 * bilan qulflangan. ⚠ Atributning NOMI ham bu faylda uchramaydi.
 * =============================================================================
 */

export type ReconciliationDaySelection = BillingDaySelection;

/** Nomuvofiqlik ekranining kun tanlovi — YAGONA manba (sahifa ham shundan). */
export function useReconciliationDay(): ReconciliationDaySelection {
  return useBillingDay();
}

/** Kun tanlagichi — 6-fazaning boshqaruvi, o'zgarishsiz. */
export function ReconciliationDayPicker() {
  return <BillingDayPicker />;
}
