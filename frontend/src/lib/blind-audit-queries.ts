"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import {
  answerRequestBody,
  answerResponseSchema,
  blindAuditItemSchema,
  reviewBudgetResponseSchema,
} from "@/lib/api-types";
import type { HumanAnswer } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * ⛔⛔ KO'RMASDAN TEKSHIRISHNING SO'ROV QATLAMI — ALOHIDA MODUL.
 *
 * -----------------------------------------------------------------------
 * NEGA U `review-queries.ts` GA QO'SHILMAYDI [QAROR — UI-SPEC §5.3]
 * -----------------------------------------------------------------------
 * Qo'shish TEXNIK JIHATDAN to'g'ri bo'lardi: bir domen, bir backend,
 * o'xshash shakl, ~40 qator kamroq kod. RAD ETILADI.
 *
 * G-12 darvozasi (`scripts/blind-payload.test.mjs`) FAYL TO'PLAMINI
 * skanerlaydi, satrni emas: «bu faylda va `components/blind-audit/**` da
 * taqiqlangan nomlar UMUMAN uchramaydi» — TO'LIQ va MEXANIK shart.
 * Aralash modulda u «taqiqlangan nom faqat noaniq navbat funksiyalarida
 * uchraydi» degan KONTEKSTGA BOG'LIQ shartga aylanardi, ya'ni `grep`
 * bilan tekshirib bo'lmaydigan, kod-ko'rikka qaytadigan shartga. Kod
 * ko'rigi esa aynan shu sinfdagi xatoni 2 va 3-fazada 15+ marta
 * o'tkazib yuborgan.
 *
 * Takrorlanishning narxi — ~40 qator. Xolislik kafolatining narxi —
 * hisobotdagi ANIQLIK RAQAMI, ya'ni undan ancha yuqori.
 *
 * -----------------------------------------------------------------------
 * ⛔ KESH: `remove`, `invalidate` EMAS [§14.3, 4-qatlam — G-14(b)]
 * -----------------------------------------------------------------------
 * `invalidateQueries` yozuvni keshda QOLDIRIB uni «eskirgan» deb
 * belgilaydi — ya'ni ko'rilgan band brauzer xotirasida turaveradi va
 * React Query DevTools'da bir bosishda o'qiladi. `removeQueries` esa uni
 * GRAFDAN CHIQARADI. Darvoza bu faylda `invalidateQueries` so'zining
 * O'ZINI ham taqiqlaydi.
 *
 * ⛔ Har so'rov `gcTime: 0`, `staleTime: 0` va
 *    `refetchOnWindowFocus: false` bilan yuritiladi.
 *
 * ⚠⚠ DA'VO SABOTAJ BILAN TORAYTIRILDI (05-13). «`remove` `invalidate`
 *    dan xavfsizroq» — BUGUNGI sozlamada O'LCHANADIGAN da'vo EMAS:
 *    `removeQueries` -> `invalidateQueries` almashuvi `blind-session.
 *    test.tsx` ning 18 testidan BIRORTASINI ham qizartirmadi. Sabab
 *    strukturaviy: oshkor ma'lumot keshga umuman tushmaydi, `invalidate`
 *    keshda qoldiradigan BAND payloadi esa `gcTime: 0` tufayli
 *    kuzatuvchi uzilishi bilan baribir o'chadi.
 *
 *    Ya'ni kafolat JUFTLIKDAN chiqadi: `gcTime: 0` OYNANI yopadi,
 *    `removeQueries` esa DARHOL tozalaydi va `gcTime` bir kun oshirilsa
 *    yolg'iz o'zi ham kafolat beradi. Shuning uchun IKKALASI ham
 *    alohida qo'riqlanadi: `removeQueries` — statik darvoza (G-14b),
 *    `gcTime`/`staleTime` — `review-queries.test.tsx` dagi xulq testi.
 *
 * -----------------------------------------------------------------------
 * ⛔ POLL YO'Q (§8.5) va SESSIYA HOLATI URL'DA EMAS (§4.5)
 * -----------------------------------------------------------------------
 * Navbat SO'ROV BO'YICHA yuriydi: javob -> `mutate` -> kesh tozalanadi ->
 * keyingi band. Marshrutda band identifikatori YO'Q, ya'ni «orqaga
 * qaytib javobni o'zgartirish» yo'lining O'ZI mavjud emas (D-17,
 * 4-himoya).
 *
 * ⚠ KEYINGI BANDNI OLDINDAN YUKLASH RUXSAT (§7.7): u ham ko'r payload.
 *   OSHKOR ma'lumot esa HECH QACHON oldindan yuklanmaydi — u faqat
 *   `useMutation` ning natijasida yashaydi va kesh grafiga umuman
 *   tushmaydi.
 * =============================================================================
 */

/* --- Yo'l konstantalari --------------------------------------------------- */

export const BLIND_PATH = "/review/blind";
export const BLIND_BUDGET_PATH = "/review/budget";

/* --- Query kalitlari (ALOHIDA prefiks, §5.4) ------------------------------- */

/**
 * ⛔ PREFIKS `review-*` DAN AJRALGAN va bu darvozaning ikkinchi yarmi:
 *    kesh FAQAT shunda PREFIKS BO'YICHA tozalanishi mumkin. Umumiy
 *    prefiksda tozalash noaniq navbatning holatini ham o'chirib,
 *    nazoratchini boshqa sessiyada band yo'qotishga majburlardi.
 */
export const blindPrefix = (marketId: string) =>
  domainKey(marketId, "blind-audit");

export const blindNextKey = (marketId: string) =>
  domainKey(marketId, "blind-audit", "next");

export const blindBudgetKey = (marketId: string, day: string) =>
  domainKey(marketId, "blind-audit", "budget", day);

/** Joriy bozor — kalit qurish uchun YAGONA manba (eksport QILINMAYDI). */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/* --- Navbatdagi band ------------------------------------------------------- */

/**
 * `GET /review/blind/next` — navbatdagi BITTA band.
 *
 * ⛔ KLIENT QAYSI BAND KELISHINI TANLAY OLMAYDI. Sessiya holatining
 *    YAGONA manbai — SERVER (§4.5). Sahifa yangilansa server O'SHA
 *    bandni qaytaradi (javob yozilmagan bo'lsa) yoki KEYINGISINI
 *    (yozilgan bo'lsa) — «yangilab qayta ko'raman» yo'li shu bilan
 *    yopiladi.
 *
 * ⛔ SXEMA `z.strictObject` (G-13): server bir kun ortiqcha maydon
 *    qo'shsa klient PARSE PAYTIDA yiqiladi va ekran qizil blok
 *    ko'rsatadi. Bu «buzilgan ekran» emas — bu o'lchovni himoya qilish:
 *    ankorlangan javob hisobotga kiruvchi YOLG'ON ma'lumot bo'lardi.
 *
 * ⚠ `retry: false`: bo'sh navbat, tortilmagan namuna va tugagan byudjet
 *   — uchalasi ham 409 bilan keladi va ular NORMAL holatlar.
 */
export function useBlindNext(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: blindNextKey(marketId ?? ""),
    queryFn: () => apiFetch(`${BLIND_PATH}/next`, { schema: blindAuditItemSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
    retry: false,
    gcTime: 0,
    staleTime: 0,
    refetchOnWindowFocus: false,
  });
}

/* --- Kunlik hisoblagich ---------------------------------------------------- */

/**
 * `GET /review/budget?day=…` — lentadagi `{done} / {total}`.
 *
 * ⚠ MARSHRUT `review-queries.ts` DAGI BILAN BIR XIL, KALIT esa BOSHQA
 *   PREFIKSDA — va bu ATAYIN. Javob yozilgach bu modul O'Z prefiksini
 *   butunlay tozalaydi; umumiy kalitda o'sha tozalash noaniq navbatning
 *   hisoblagichiga ham tegardi.
 */
export function useBlindBudget(day: string, options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: blindBudgetKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(`${BLIND_BUDGET_PATH}?day=${encodeURIComponent(day)}`, {
        schema: reviewBudgetResponseSchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
    gcTime: 0,
    staleTime: 0,
    refetchOnWindowFocus: false,
  });
}

/* --- Javob ----------------------------------------------------------------- */

/**
 * `POST /review/blind/{id}/answer` — BITTA, O'ZGARMAS javob (D-17.4).
 *
 * =========================================================================
 * ⛔ IKKINCHI CHAQIRUV SERVERDA `409 blind_answer_locked` OLADI va UI
 *    QAYTA URINISH TUGMASI BERMAYDI (§4.5, S-10). Shuning uchun bu yerda
 *    ham `retry: false`: avtomatik takror urinish nazoratchi ko'rmagan
 *    holda 409 hosil qilardi va u xato blokiga aylanardi.
 *
 * ⛔ MUVAFFAQIYATDAN KEYIN KESH TOZALANADI — `remove`, `invalidate`
 *    EMAS. Ya'ni javob berilgan band brauzer xotirasida QOLMAYDI.
 *    Hisoblagich ham shu prefiksda, ya'ni u ham yangilanadi.
 * =========================================================================
 *
 * ⚠ TANA `answerRequestBody()` DAN keladi va u `api-types.ts` da
 *   yashaydi. Sabab MEXANIK va u o'sha faylda yozilgan: server
 *   maydonining nomi G-12 ning taqiqlangan tokenini o'z ichiga oladi,
 *   ya'ni bu fayl uni YOZA OLMAYDI. Darvozaning o'zi kodlashni sim
 *   qatlamiga majburlaydi.
 *
 * ⛔ MASSIV TANA YO'Q va uning yo'li ham yo'q (D-18): funksiya aynan
 *    bitta band identifikatori va aynan bitta javob oladi.
 */
export function useAnswerBlindItem() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: (input: { assignmentId: string; answer: HumanAnswer }) =>
      apiFetch(
        `${BLIND_PATH}/${encodeURIComponent(input.assignmentId)}/answer`,
        {
          method: "POST",
          body: answerRequestBody(input.answer),
          schema: answerResponseSchema,
        },
      ),
    retry: false,
    onSuccess: () => {
      client.removeQueries({ queryKey: blindPrefix(marketId) });
    },
  });
}
