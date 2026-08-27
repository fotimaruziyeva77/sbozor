"use client";

import { useQuery, type useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiFetch } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * KASSIR RO'YXATI — «kimdan oldim / kim qoldi» (0027).
 *
 * ⛔⛔ SUMMA MAYDONI YO'Q VA U QO'SHILMAYDI — KO'R SMENA SANOG'I (D-25/D-26).
 *
 *   Kassir naqdni O'ZI sanab kiritadi, tizim esa unga o'z yig'indisini
 *   BERMAYDI; farqni faqat direktor ko'radi. `GET /payments/recent` aynan
 *   shu sababdan serverda BESHTA qator bilan chegaralangan — kassir
 *   ularni qo'shib chiqara olmasin.
 *
 *   Bu ro'yxat esa TO'LIQ (barcha rasta), ya'ni unga summa qo'shilsa
 *   chegaralashning butun ma'nosi yo'qolardi: kassir jamini qo'shib,
 *   smena yopishda AYNAN o'sha sonni yozardi va farq HAR DOIM nol
 *   bo'lardi.
 *
 *   ⛔ `strictObject` bu taqiqni MEXANIK qiladi: server bir kun summa
 *      yuborsa sxema javobni RAD ETADI va nosozlik jimgina o'tmaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ SAHIFA HAJMI SERVERDA (`per_page` so'rov parametri YO'Q).
 *
 *   Klient `per_page=1000` yuborib butun ro'yxatni bir so'rovda ololmasin.
 *   Server `per_page` ni JAVOBDA qaytaradi — klient uni o'zi bilmaydi va
 *   qotirib qo'ymaydi.
 * =============================================================================
 */

export const COLLECT_ROSTER_PATH = "/billing/collect-roster";

export const ROSTER_STATES = ["unpaid", "paid", "unassigned"] as const;
export type RosterState = (typeof ROSTER_STATES)[number];
/**
 * ⛔ TARTIB AHAMIYATLI: `unpaid` BIRINCHI va u STANDART tanlov.
 *
 * Kassirning savoli «kim qoldi?», «kimdan oldim?» EMAS — birinchisi
 * ishning O'ZI, ikkinchisi tekshiruv. Standartni `paid` qilish har
 * ochilishda bitta ortiqcha bosish qo'shardi.
 */

export const rosterRowSchema = z.strictObject({
  /** ⛔ Kassir yuzasidagi YAGONA identifikator (§5.5). */
  stall_code: z.string(),
  /**
   * Bugun biriktirish BORMI — ⛔ BUL, identifikator EMAS (C-10).
   *
   * To'lanmagan ro'yxatda MUHIM: sotuvchisiz rastadan patta olib
   * bo'lmaydi (409 `stall_not_assigned`) va kassir buni ro'yxatda
   * ko'rib, behuda urinmasligi kerak.
   */
  vendor_assigned: z.boolean(),
  /** Oxirgi to'lov vaqti (ISO) — FAQAT to'langan qatorlarda. */
  paid_at: z.string().nullable(),
});

export type RosterRow = z.infer<typeof rosterRowSchema>;

export const collectRosterSchema = z.strictObject({
  service_date: z.string(),
  state: z.enum(ROSTER_STATES),
  rows: z.array(rosterRowSchema),
  /** Shu FILTR bo'yicha JAMI qator — sahifadagi emas. */
  total: z.number().int(),
  page: z.number().int(),
  per_page: z.number().int(),
  page_count: z.number().int(),
  /**
   * ⛔ IKKALA SANOQ HAM HAR IKKALA SO'ROVDA KELADI — klient «12 / 38»
   *    yozuvini ikkinchi so'rov yubormasdan chizadi.
   *
   * ⚠ BU SUMMA EMAS, SANOQ. Kassir undan yig'indi chiqara olmaydi —
   *   ko'r sanoq taqig'i buzilmaydi.
   */
  paid_count: z.number().int(),
  unpaid_count: z.number().int(),
  /**
   * Sotuvchisiz rastalar — ⛔ `unpaid_count` GA KIRMAYDI (O'-01 auditi).
   *
   * Ulardan patta olib bo'lmaydi (409 `stall_not_assigned`), ya'ni
   * «to'lanmagan» hisobiga qo'shilsa kassir har kuni bajarib
   * bo'lmaydigan reja bilan qolardi.
   */
  unassigned_count: z.number().int(),
  fetched_at: z.string(),
});

export type CollectRoster = z.infer<typeof collectRosterSchema>;

/* --- Query kalitlari (TUG'ILISHIDANOQ doiralangan, §5.4) ------------------ */

export const rosterPrefix = (marketId: string) =>
  domainKey(marketId, "collect-roster");

export const rosterKey = (marketId: string, state: RosterState, page: number) =>
  domainKey(marketId, "collect-roster", state, String(page));

/** Joriy bozor — kalit qurish uchun YAGONA manba (eksport QILINMAYDI). */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/**
 * To'lovdan keyin IKKALA ro'yxat ham eskiradi — bitta prefiks bilan.
 *
 * ⛔ `removeQueries`, `invalidateQueries` EMAS: rasta to'langanda u
 *    «to'lanmagan» ro'yxatidan CHIQIB KETADI. Eskirgan yozuvni keshda
 *    qoldirish keyingi ochilishda o'sha rastani bir lahza «hali
 *    to'lanmagan» deb ko'rsatardi — pul ekranida bu yolg'on.
 */
export function dropRosterAfterPayment(
  client: ReturnType<typeof useQueryClient>,
  marketId: string | null,
): void {
  if (marketId === null) return;
  client.removeQueries({ queryKey: rosterPrefix(marketId) });
}

/**
 * `GET /billing/collect-roster?state=…&page=…`
 *
 * ⚠ `placeholderData` YO'Q va bu ONGLI: sahifa almashganda eski
 *   sahifaning qatorlarini ko'rsatib turish «bu rasta shu sahifada» degan
 *   yolg'on beradi. Skeleton halolroq (UI-SPEC §16 — spinner emas,
 *   skeleton).
 */
export function useCollectRoster(state: RosterState, page: number) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: rosterKey(marketId ?? "", state, page),
    queryFn: () =>
      apiFetch(`${COLLECT_ROSTER_PATH}?state=${state}&page=${page}`, {
        schema: collectRosterSchema,
      }),
    enabled: marketId !== null,
    retry: false,
    /*
     * ⛔ `staleTime: 0` — pul ekranida eskirgan ro'yxat ko'rsatilmaydi.
     *   `gcTime` esa NOLGA TUSHIRILMAYDI (`recentPayments` dan FARQ):
     *   sahifalar orasida oldinga-orqaga yurish har safar tarmoqqa
     *   chiqishga majbur qilardi va telefon internetida ro'yxat
     *   «sakrab» turardi.
     */
    staleTime: 0,
    refetchOnWindowFocus: false,
  });
}
