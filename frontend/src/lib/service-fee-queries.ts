"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiFetch } from "@/lib/api-client";
import { emptyResponseSchema, soumSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * MAJBURIY XIZMAT HAQI (tarozi) — bozor darajasidagi narx tarixi (0027).
 *
 * ⛔ TARIF EMAS VA `tariff-*` MODULIGA QO'SHILMAYDI: tarif TOIFAGA
 *    bog'langan (`(category_id, valid_from)`), xizmat haqi esa BOZORGA
 *    (`(market_id, valid_from)`). Ikkalasi bir modulda yashasa
 *    `category_id` ni ixtiyoriy qilishga to'g'ri kelardi va «qaysi
 *    toifaning xizmat haqi?» degan javobsiz savol tug'ilardi.
 *
 * ⚠ EKRANDA ular BITTA sahifada (Tariflar) — foydalanuvchi talabi:
 *   «Ta'riflarda qushiladi u uzgarsa u yerda ko'rinsin». UI joylashuvi
 *   API shaklini belgilamaydi.
 * =============================================================================
 */

export const SERVICE_FEES_PATH = "/service-fees";

export const serviceFeeItemSchema = z.strictObject({
  id: z.string(),
  /** `0` — bu bozorda xizmat haqi olinmaydi (`>= 0`, `> 0` EMAS). */
  amount_soum: soumSchema,
  /** Kvitansiyada ko'rinadigan nom — ⛔ BOZOR KIRITGAN MATN, i18n kaliti EMAS. */
  label: z.string(),
  valid_from: z.string(),
  /** `null` — OXIRGI qator, narx hozircha muddatsiz (`LEAD()` dan). */
  valid_to: z.string().nullable(),
  /** `valid_from <= bugun` — SO'ROV PAYTIDAGI holat, saqlangan ustun emas. */
  is_past: z.boolean(),
});

export type ServiceFeeItem = z.infer<typeof serviceFeeItemSchema>;

export const serviceFeeListSchema = z.strictObject({
  items: z.array(serviceFeeItemSchema),
  min_valid_from: z.string(),
  /**
   * ⛔ RO'YXATDAN HOSILA QILINMAYDI — serverdan alohida keladi.
   *
   * Tartib `valid_from DESC`, ya'ni BIRINCHI qator KELAJAKDAGI narx
   * bo'lishi mumkin. «Hozir amalda qancha?» savoliga ro'yxatdan javob
   * olish klientda sana solishtirishni talab qilardi — pul haqidagi
   * qarorni klientga surish esa D-20 ning aynan taqig'i.
   */
  current_amount_soum: soumSchema.nullable(),
  current_label: z.string().nullable(),
});

export type ServiceFeeList = z.infer<typeof serviceFeeListSchema>;

/* --- Query kalitlari ------------------------------------------------------- */

export const serviceFeesKey = (marketId: string) =>
  domainKey(marketId, "service-fees");

/** Joriy bozor — kalit qurish uchun YAGONA manba (eksport QILINMAYDI). */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

export function useServiceFees() {
  const marketId = useMarketId();

  return useQuery({
    queryKey: serviceFeesKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(SERVICE_FEES_PATH, { schema: serviceFeeListSchema }),
    enabled: marketId !== null,
    retry: false,
  });
}

export type ServiceFeeCreateInput = {
  amount_soum: number;
  label: string;
  valid_from: string;
};

export function useCreateServiceFee() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: (input: ServiceFeeCreateInput) =>
      apiFetch(SERVICE_FEES_PATH, {
        method: "POST",
        body: input,
        schema: serviceFeeItemSchema,
      }),
    /*
     * ⛔ KASSIR PROYEKSIYASI HAM ESKIRADI — LEKIN U BOSHQA SESSIYADA.
     *
     *   Bu mutatsiya bozor ADMINI brauzerida ketadi; kassirning
     *   `billing-pending` keshi UNING brauzerida yashaydi va bu yerdan
     *   tozalanmaydi. Kassir yangi narxni keyingi rasta qidiruvida
     *   ko'radi — proyeksiya `staleTime: 0` bilan HAR SAFAR serverdan
     *   olinadi (`billing-pending-queries.ts`). Ya'ni bu yerda
     *   qo'shimcha hech nima kerak emas va «kesh ikki brauzer orasida
     *   sinxronlanadi» degan yolg'on kod YOZILMAYDI.
     */
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: serviceFeesKey(marketId) });
    },
  });
}

export function useDeleteServiceFee() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: (feeId: string) =>
      apiFetch(`${SERVICE_FEES_PATH}/${feeId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: serviceFeesKey(marketId) });
    },
  });
}
