"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiFetch } from "@/lib/api-client";
import { soumSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { ADJUSTMENT_REASONS } from "@/lib/billing-charge-queries";
import type { AdjustmentReason } from "@/lib/billing-charge-queries";
import { dropPendingAfterPayment } from "@/lib/billing-pending-queries";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * TO'LOV YOZUVI — KASSIR YUZASINING YAGONA YOZUV QATLAMI (CASH-01, CASH-03).
 *
 * -----------------------------------------------------------------------
 * ⛔ TO'LOV HISOBGA BOG'LANMAYDI (C-4)
 * -----------------------------------------------------------------------
 * «Qaysi kun uchun to'lanyapti?» savoliga `service_date` javob beradi,
 * hisob identifikatori EMAS — u bu yuzada umuman mavjud emas. Sabab
 * mexanik: hisob D+1 04:10 da tug'iladi, to'lov esa BUGUN yoziladi,
 * ya'ni bog'lanish uchun narsaning o'zi yo'q. Kredit sotuvchi kesimida
 * eng qadimgi to'lanmagan kundan boshlab yopiladi (FIFO) va bu qoida
 * SERVERDA, hosila ko'rinish sifatida yashaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ SHAXSIY MAYDON YO'Q (C-10, §5.5)
 * -----------------------------------------------------------------------
 * Sotuvchi ismi ham, telefoni ham bu javoblarda yo'q. Kassirda
 * `vendor_view` huquqi YO'Q, ya'ni ism unga MARSHRUT DARAJASIDA emas,
 * HUQUQ DARAJASIDA yopiq — «kassir ekranida ism ko'rsatmaymiz» degan
 * kod-ko'rik da'vosi kerak emas.
 *
 * ⛔ Nom bilan aylanib o'tish (`payer`, `who`, sotuvchi yorlig'i) ham
 *    taqiqlanadi va u statik darvozaning reyestrida yashaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ IDEMPOTENTLIK KALITI BU MODULDA TUG'ILMAYDI (D-21, §8.7)
 * -----------------------------------------------------------------------
 * Kalit SAHIFA HOLATIDA yashaydi va uni `payment-bar.tsx` (06-11)
 * boshqaradi: rasta topilganda tug'iladi, tarmoq xatosida SAQLANADI,
 * summa yoki to'lov turi o'zgarganda YANGISI olinadi, 2xx dan keyin
 * iste'foga chiqadi.
 *
 * ⛔ Uni mutatsiya ichida tug'dirish D-21 ni BUZARDI: har qayta urinish
 *    yangi kalit olib, server uchun YANGI TO'LOV bo'lib ko'rinardi —
 *    ya'ni dublikat to'siqning server yarmi (`UNIQUE (market_id,
 *    idempotency_key)`) umuman ishlamasdi.
 * =============================================================================
 */

/* --- Yo'l konstantasi ------------------------------------------------------ */

export const PAYMENTS_PATH = "/payments";

/* --- Reyestrlar (yopiq to'plamlar) ---------------------------------------- */

/**
 * To'lov yozuvining turi (D-23).
 *
 * ⛔ Storno — O'CHIRISH emas, YANGI QATOR. Eski qator o'zgarmaydi va
 *    ekranda `tone="muted"` bo'lib qoladi. Qoldiq — belgili summalar
 *    yig'indisi, belgi esa FAQAT ko'rinishda tug'iladi (C-5).
 */
export const PAYMENT_KINDS = ["payment", "reversal"] as const;

export type PaymentKind = (typeof PAYMENT_KINDS)[number];

/**
 * To'lov usuli — YOPIQ to'plam (`CHECK (method IN ('cash','terminal'))`).
 *
 * ⚠ 06-02 (W0-F7) bu reyestrning ko'zgusini `api-types.ts` ga qo'yadi;
 *   ikkovi bir to'lqinda ishlangani uchun bu modul hozircha o'z nusxasini
 *   saqlaydi va ko'zgu yetib kelganda import bilan almashtiriladi.
 */
export const PAYMENT_METHODS = ["cash", "terminal"] as const;

export type PaymentMethod = (typeof PAYMENT_METHODS)[number];

/**
 * Storno sabab-kodlari — YOPIQ ro'yxat (D-23, §8.8).
 *
 * ⛔ `other`/`custom` YO'Q: erkin matn hisobotda guruhlanmaydi va amalda
 *    ENG KATTA guruh bo'lib qolardi (D-19 bilan bir xil mulohaza).
 */
export const REVERSAL_REASONS = [
  "wrong_stall",
  "wrong_amount",
  "duplicate_entry",
  "customer_refund",
] as const;

export type ReversalReason = (typeof REVERSAL_REASONS)[number];

/* --- Sxemalar -------------------------------------------------------------- */

/**
 * Yozilgan to'lov qatori (§8.8).
 *
 * =========================================================================
 * ⛔ KALITLAR TO'PLAMI AYNAN SAKKIZTA va `z.strictObject` buni
 *    qo'riqlaydi.
 *
 * ⛔ HISOB IDENTIFIKATORI YO'Q (C-4) — u bu domenda mavjud emas.
 * ⛔ SOTUVCHI ISMI VA TELEFONI YO'Q (C-10) — kassir yuzasida shaxsiy
 *    maydon bo'lmasligi shu sxemadan boshlanadi.
 * ⛔ YIG'INDI MAYDONI YO'Q: qator o'z summasini biladi, smenaning
 *    jamini EMAS. Jami — smena ko'rligining (§10.3) buzilishi bo'lardi.
 * =========================================================================
 */
export const paymentResponseSchema = z.strictObject({
  payment_id: z.uuid(),
  stall_code: z.string(),
  service_date: z.string(),
  amount_soum: soumSchema,
  kind: z.enum(PAYMENT_KINDS),
  method: z.enum(PAYMENT_METHODS),
  created_at: z.string(),
  /** Qator storno qilinganmi — [Bekor qilish] affordansining sharti. */
  reversed: z.boolean(),
});

export type PaymentRecord = z.infer<typeof paymentResponseSchema>;

/**
 * `GET /payments/recent` javobi — SERVERDA qat'iy chegaralangan oyna.
 *
 * ⛔ Javob YIG'INDI maydonini ham, umumiy SANOQNI ham qaytarmaydi:
 *    ikkalasi ham §10.3 ning ko'r deklaratsiyasini arifmetika bilan
 *    buzishga yo'l ochardi.
 */
export const recentPaymentsSchema = z.strictObject({
  items: z.array(paymentResponseSchema),
});

export type RecentPayments = z.infer<typeof recentPaymentsSchema>;

/* --- So'rov tanalari ------------------------------------------------------- */

/**
 * `POST /payments` tanasi.
 *
 * ⚠ Maydon nomlari SIM QATLAMINING nomlari (snake_case): tarjima qatlami
 *   ataylab qo'yilmadi — u ikkinchi haqiqat manbai bo'lardi va serverning
 *   `request_fingerprint` i aynan shu maydonlardan hisoblanadi.
 */
export type PaymentInput = {
  idempotency_key: string;
  stall_code: string;
  method: PaymentMethod;
  amount_soum: number;
  /** Faqat summa tarifdan farq qilganda (D-19, §8.6). */
  reason_code?: AdjustmentReason;
};

/** `POST /payments/{id}/reverse` tanasi — sabab MAJBURIY (D-23). */
export type ReversalInput = {
  payment_id: string;
  reason_code: ReversalReason;
};

/* --- Query kalitlari ------------------------------------------------------- */

export const recentPaymentsKey = (marketId: string) =>
  domainKey(marketId, "payments", "recent");

/** Joriy bozor — kalit qurish uchun YAGONA manba (eksport QILINMAYDI). */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/**
 * Ikki kesh prefiksini birdan tozalaydi — to'lov va storno uchun BIR XIL.
 *
 * ⛔ Proyeksiya `dropPendingAfterPayment()` bilan chiqariladi (ya'ni
 *    `removeQueries`, kesh yozuvini «eskirgan» deb belgilash EMAS):
 *    to'lovdan keyingi eski proyeksiya endi YOLG'ON summa va u brauzer
 *    xotirasida turishi ham kerak emas (§5.4, G-23e).
 */
function dropAfterWrite(
  client: ReturnType<typeof useQueryClient>,
  marketId: string,
): void {
  dropPendingAfterPayment(client, marketId);
  client.removeQueries({ queryKey: recentPaymentsKey(marketId) });
}

/* --- To'lov yozish --------------------------------------------------------- */

/**
 * `POST /payments` — kassir oqimining yagona yozuv nuqtasi.
 *
 * =========================================================================
 * ⛔ `retry: false` — QAYTA YUBORISH FOYDALANUVCHI QARORI (D-21 ning UI
 *    shakli).
 *
 *    Avtomatik takror urinish kassir KO'RMAGAN holda ikkinchi so'rov
 *    yuborardi. Server tomonda dublikat to'sig'i bor (o'sha kalit ->
 *    o'sha to'lov, 200), lekin UI o'sha paytda «yubordim/yubormadim»
 *    holatini yo'qotardi va kassir uchinchi marta bosardi. Qayta
 *    yuborish KO'RINMAS bo'lishi kerak — LEKIN BOSISH bilan.
 *
 * ⛔ XATODA IDEMPOTENTLIK KALITI TOZALANMAYDI VA BU YERDA BUNI
 *    QILADIGAN KOD YO'Q.
 *
 *    Kalit sahifa holatida yashaydi (§8.7 jadvali). Agar `onError`
 *    ichida u tozalansa (yoki mutatsiya ichida qayta tug'ilsa), 5xx dan
 *    keyingi [Qayta yuborish] YANGI kalit bilan ketardi va server uni
 *    IKKINCHI TO'LOV deb yozardi — ya'ni D-21 ning butun mexanizmi
 *    aynan tiklanishi kerak bo'lgan lahzada ishdan chiqardi.
 *
 *    ⚠ Bu ochiq yozilgan, chunki keyingi ijrochi uchun «kalitni shu
 *      yerda boshqarish» tabiiy ko'rinadi. Ko'rinishi to'g'ri, natijasi
 *      noto'g'ri.
 * =========================================================================
 */
export function usePayment() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: (input: PaymentInput) =>
      apiFetch(PAYMENTS_PATH, {
        method: "POST",
        body: input,
        schema: paymentResponseSchema,
      }),
    retry: false,
    onSuccess: () => {
      dropAfterWrite(client, marketId);
    },
  });
}

/* --- Storno ---------------------------------------------------------------- */

/**
 * `POST /payments/{id}/reverse` — storno YANGI QATOR yozadi (D-23).
 *
 * ⛔ SABAB-KOD MAJBURIY va u tipda ham majburiy: ixtiyoriy qilingan
 *    maydon birinchi shoshilinch tuzatishda bo'sh ketardi va hisobotda
 *    «sababsiz storno» guruhi paydo bo'lardi.
 *
 * ⛔ [Tahrirlash] va [O'chirish] marshrutlari YO'Q — na bu modulda, na
 *    serverda. `payments` append-only.
 *
 * ⚠ Kassir FAQAT o'z ochiq smenasidagi to'lovni bekor qiladi (§8.8);
 *   eski to'lov uchun yuza 6-fazada qurilmaydi.
 */
export function useReversePayment() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: (input: ReversalInput) =>
      apiFetch(
        `${PAYMENTS_PATH}/${encodeURIComponent(input.payment_id)}/reverse`,
        {
          method: "POST",
          body: { reason_code: input.reason_code },
          schema: paymentResponseSchema,
        },
      ),
    retry: false,
    onSuccess: () => {
      dropAfterWrite(client, marketId);
    },
  });
}

/* --- Oxirgi to'lovlar oynasi ----------------------------------------------- */

/**
 * `GET /payments/recent` — OXIRGI 5 TO'LOV, oyna SERVERDA qat'iy.
 *
 * =========================================================================
 * ⛔ FUNKSIYA ARGUMENTSIZ VA URL'GA BIRORTA SO'ROV PARAMETRI
 *    QO'SHILMAYDI: na oyna o'lchami, na siljish, na sahifa belgisi.
 *    Sahifalash yuzasi bu modulda MAVJUD EMAS (§8.8).
 *
 *    Sabab pul bilan bog'liq: kassir o'zi yozgan to'lovlarni ko'rishi
 *    KERAK (bekor qilish uchun). Lekin u smenasining HAMMA to'lovini
 *    ko'rsa, ularni qo'shib tizim summasini chiqarib olardi — ya'ni
 *    §10.3 ning ko'r deklaratsiyasi ARIFMETIKA BILAN buzilardi.
 *
 *    5 qator bekor qilish uchun yetadi (xato darhol seziladi) va
 *    jamlash uchun MA'NOSIZ. Mexanizm shu yerda: yig'indi yo'lini
 *    maydon yashirish emas, MARSHRUTNING IMKONIYATI to'sadi.
 *
 * ⛔ `staleTime: 0` + `gcTime: 0`: storno yozilgach eski qator
 *    ro'yxatda «hali bekor qilinmagan» bo'lib turishi mumkin emas.
 * =========================================================================
 */
export function useRecentPayments() {
  const marketId = useMarketId();

  return useQuery({
    queryKey: recentPaymentsKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(`${PAYMENTS_PATH}/recent`, { schema: recentPaymentsSchema }),
    enabled: marketId !== null,
    retry: false,
    staleTime: 0,
    gcTime: 0,
    refetchOnWindowFocus: false,
  });
}
