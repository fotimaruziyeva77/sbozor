"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { apiFetch } from "@/lib/api-client";
import { soumSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { AMOUNT_UNAVAILABLE_REASONS } from "@/lib/billing-pending-queries";
import { domainKey } from "@/lib/market-queries";
import { hasPermission } from "@/lib/rbac";

/*
 * =============================================================================
 * ⛔⛔ PLAN-XARITANING TO'LOV QATLAMI — ALOHIDA MODUL (MARKET-06).
 *
 * -----------------------------------------------------------------------
 * ⛔ 1. RANG SERVERDAN KELADI, KLIENTDA HISOBLANMAYDI [D-C1]
 * -----------------------------------------------------------------------
 * Server YOPIQ enum (`MapDayState`) beradi va ustuvorlik qoidasi
 * (`mismatch` > `no_billing` > `free` > `paid` > `due`) faqat
 * `billing_repo._map_day_state()` da yashaydi. Bu modul uni FAQAT
 * `StallTone` ga maps qiladi (`stall-tone.ts::dayToneOf`).
 *
 * Qoidani bu yerda takrorlash ikki tilda ikki qoida yaratardi va ular
 * ⛔ BIR KUN AJRALIB KETARDI — o'shanda xaritadagi rang bilan hisobotdagi
 * holat farq qilardi, IKKALASI HAM «to'g'ri» bo'lgan holda. Kodbazada bu
 * «ikki haqiqat manbai» sinfi takroran topilgan.
 *
 * -----------------------------------------------------------------------
 * ⛔ 2. HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN [D-C4]
 * -----------------------------------------------------------------------
 * `enabled` sharti `hasPermission(roles, "billing_collect_view")` ni O'Z
 * ICHIGA OLADI, ya'ni huquqsiz sessiyada so'rov ⛔ UMUMAN YUBORILMAYDI.
 * Naqsh `map/page.tsx` dagi `market_data_view` tekshiruvining aynan o'zi
 * va u chaqiruvchini huquq mantig'idan OZOD QILADI: `StallMap` «kim
 * ko'radi?» degan savolga javob bermaydi.
 *
 * ⚠ Bu UI KO'ZGUSI, xavfsizlik chegarasi EMAS — chegara serverda
 *   (`require_permission(BILLING_COLLECT_VIEW)`). Ko'zgu esa yolg'on
 *   affordansning oldini oladi: o'chirilgan element ham, platsholder ham
 *   qo'yilmaydi (RBAC UI ko'zgusining mavjud qoidasi).
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. `byStallId` — BARQAROR HAVOLA (Pitfall 8)
 * -----------------------------------------------------------------------
 * Hook har renderda YANGI `Map` qaytarsa `stall-map.tsx` dagi `zones`
 * memo'si har safar qayta hisoblanardi, ya'ni 1000 katakning har biri
 * YANGI `cell` obyekti olardi va `memo` butunlay ma'nosiz bo'lardi.
 * O'shanda `stall-map.test.tsx` ning «tanlash gridni qayta render
 * qilmaydi» darvozasi qizarardi — va u haq bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. NEGA `billing-pending-queries.ts` GA QO'SHILMAYDI
 * -----------------------------------------------------------------------
 * O'sha modul `scripts/collect-surface.test.mjs` ning skan maydonida:
 * darvoza unda taqiqlangan nomlarni BUTUN FAYL bo'ylab qidiradi. Xarita
 * qatlami esa `open_case_id` bilan ishlaydi va u kassir yuzasiga
 * tegishli EMAS. Aralash modulda darvoza «taqiqlangan nom faqat
 * proyeksiya funksiyalarida uchramaydi» degan KONTEKSTGA BOG'LIQ shartga
 * aylanardi — ya'ni matn skani bilan tekshirib bo'lmaydigan shartga.
 *
 * ⚠ `AMOUNT_UNAVAILABLE_REASONS` esa o'sha moduldan IMPORT qilinadi:
 *   ro'yxat SERVERNING yopiq to'plami (`billing_errors.
 *   AMOUNT_UNAVAILABLE_REASONS`) va ikkinchi nusxa uni bir kun
 *   ajratardi.
 * =============================================================================
 */

/* --- Yo'l konstantasi ------------------------------------------------------ */

export const MAP_DAY_PATH = "/billing/map";

/* --- Holat (YOPIQ enum, serverdan) ---------------------------------------- */

/**
 * `MapDayState` ning klient ko'zgusi.
 *
 * ⛔ TARTIB SERVERDAGI BILAN BIR XIL va bu hujjat: ro'yxat D-C2
 *    ustuvorlik jadvalining tartibida o'qiladi. Klient ustuvorlikni
 *    QO'LLAMAYDI — u faqat kelgan qiymatni tanidi.
 */
export const MAP_DAY_STATES = [
  "mismatch",
  "no_billing",
  "free",
  "paid",
  "due",
] as const;

export const mapDayStateSchema = z.enum(MAP_DAY_STATES);

export type MapDayState = z.infer<typeof mapDayStateSchema>;

/* --- Sxemalar -------------------------------------------------------------- */

/**
 * Bitta KATAKNING bugungi holati.
 *
 * =========================================================================
 * ⛔ `z.strictObject`: server bir kun ortiqcha maydon qo'shsa klient PARSE
 *    PAYTIDA yiqiladi va ekran xato blokini ko'rsatadi. Bu «buzilgan
 *    ekran» emas — bu payload yuzasining o'sishini ko'rinadigan qiladi
 *    (brauzerga yetgan maydon O'QILADI: DevTools, `JSON.stringify`).
 *
 * ⛔ `stall_code` YO'Q: katak `id` bo'yicha bog'lanadi va kod
 *    `GET /stalls/map` da ALLAQACHON bor.
 *
 * ⛔ Sotuvchi kesimidagi qarz YO'Q (D-C6): u RASTA darajasidagi miqdor
 *    emas va bir sotuvchining bir necha katagida takrorlanib, ko'z bilan
 *    qo'shilganda YOLG'ON jami berardi.
 * =========================================================================
 */
export const mapDayRowSchema = z.strictObject({
  stall_id: z.uuid(),
  state: mapDayStateSchema,
  /** Bugungi patta. `null` — FAQAT nomlangan sabab bilan. */
  amount_soum: soumSchema.nullable(),
  unavailable_reason: z.enum(AMOUNT_UNAVAILABLE_REASONS).nullable(),
  /** Bugun shu rastaga tushgan BELGILI to'lov — nol ham NATIJA. */
  paid_soum: soumSchema,
  open_case_id: z.uuid().nullable(),
  /**
   * Ochiq case QAYSI KUNNIKI — ⛔ «bugun» DEB TAXMIN QILINMAYDI.
   *
   * Nomuvofiqlik kechagi kunniki bo'lishi mumkin (server uni kun bo'yicha
   * filtrlamaydi) va uni bugungi deb ko'rsatish YOLG'ON bo'lardi.
   */
  open_case_service_date: z.string().nullable(),
});

export type MapDayRow = z.infer<typeof mapDayRowSchema>;

/**
 * `GET /billing/map` javobi.
 *
 * ⛔ `market_open` — `boolean | null`, VA `null` «O'LCHANMADI» DEGANI.
 *    Qoralama bozorda server kalendarni UMUMAN so'ramaydi (`rows` ham
 *    bo'sh keladi), ya'ni «yopiq» deyish o'lchanmagan miqdorni
 *    o'lchangan qilib ko'rsatardi. UI bu holatda QORALAMA bannerini
 *    chizadi, «yopiq kun» bannerini emas.
 */
export const mapDayStatusSchema = z.strictObject({
  service_date: z.string(),
  market_active: z.boolean(),
  market_open: z.boolean().nullable(),
  rows: z.array(mapDayRowSchema),
});

export type MapDayStatus = z.infer<typeof mapDayStatusSchema>;

/* --- Query kaliti (TUG'ILISHIDANOQ doiralangan, CR-01) --------------------- */

export const mapDayKey = (marketId: string) => domainKey(marketId, "map-day");

/* --- Hook ------------------------------------------------------------------ */

export type MapDayLayer = {
  /** ⛔ `false` bo'lsa so'rov UMUMAN yuborilmagan (huquq yoki bozor yo'q). */
  isEnabled: boolean;
  isPending: boolean;
  isError: boolean;
  /** Javobning o'zi — hali kelmagan bo'lsa `null`. */
  status: MapDayStatus | null;
  /** `stall_id -> qator`. ⛔ BARQAROR havola (modul docstringi, 3-band). */
  byStallId: ReadonlyMap<string, MapDayRow>;
};

/**
 * Xarita katagining bugungi to'lov holati — QATLAMNING YAGONA manbai.
 *
 * ⚠ `staleTime: 0` va `gcTime: 0`: raqam KUN ICHIDA o'zgaradi (kassir
 *   to'lov yozadi) va eski javob xaritada «hozirgi holat» bo'lib
 *   ko'rinardi. Bu `useMarketPending` bilan aynan bir xil qaror va
 *   aynan bir xil sabab.
 *
 * ⚠ AVTOMATIK TAYMER YO'Q (`refetchInterval` yozilmaydi): raqamni o'qib
 *   turgan paytda uni jimgina o'zgartirib qo'yish «men boshqa raqam
 *   ko'rgandim» nizosining manbai.
 *
 * ⚠ `retry: false`: to'lov qatlami xaritani BLOKLAMAYDI — nosozlikda
 *   bitta sabab qatori chiziladi va inventar ranglari joyida qoladi.
 *   Avtomatik takror urinish adminni «rang hozir chiqadi» deb kutishga
 *   majburlardi.
 */
export function useMapDayStatusQuery(): MapDayLayer {
  const { principal } = useAuthStore();

  const marketId = principal?.marketId ?? null;
  const roles = principal?.roles ?? [];
  // ⛔ HUQUQ TEKSHIRUVI SO'ROVDAN OLDIN (modul docstringi, 2-band).
  const isEnabled =
    marketId !== null && hasPermission(roles, "billing_collect_view");

  const query = useQuery({
    queryKey: mapDayKey(marketId ?? ""),
    queryFn: () => apiFetch(MAP_DAY_PATH, { schema: mapDayStatusSchema }),
    enabled: isEnabled,
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });

  const status = query.data ?? null;

  const byStallId = useMemo(() => {
    const index = new Map<string, MapDayRow>();
    /*
     * ⛔ QORALAMA BOZORDA INDEKS BO'SH QOLADI VA BU IKKI QATLAMLI:
     *   server `rows: []` yuboradi (birinchi qatlam), bu shart esa
     *   kelajakda server o'zgarsa ham birorta katakning rang OLMASLIGINI
     *   kafolatlaydi (ikkinchi qatlam). Yolg'on qizil — bu ekranning eng
     *   qimmat xatosi.
     */
    if (status !== null && status.market_active) {
      for (const row of status.rows) index.set(row.stall_id, row);
    }
    return index as ReadonlyMap<string, MapDayRow>;
  }, [status]);

  return {
    isEnabled,
    // `enabled: false` holatida TanStack `status` ni `pending` deb
    // qoldiradi — chaqiruvchi uni «yuklanmoqda» deb o'qimasligi uchun
    // shart `isEnabled` bilan JUFT.
    isPending: isEnabled && query.isPending,
    isError: isEnabled && query.isError,
    status,
    byStallId,
  };
}
