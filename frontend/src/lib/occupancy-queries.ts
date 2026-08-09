"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import {
  accuracyReportSchema,
  auditRoundSchema,
  occupancyDaySchema,
} from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * BANDLIK VA ANIQLIK HISOBOTINING SERVER HOLATI (05-12 kontrakti, §8.5, §11).
 *
 * `snapshot-queries.ts` TO'LIQ SHABLON; oltinchi modul o'sha sababdan
 * ochildi — har domenning poll qoidasi va bekor qilish to'plami O'ZINIKI.
 *
 * ⚠ KALITLAR TUG'ILISHIDANOQ DOIRALANGAN (§5.4, §S-12). `domainKey`
 *   `market-queries.ts` DAN IMPORT QILINADI — ikkinchi nusxa yaratilmaydi.
 *   GLOBAL (marketsiz) KALIT KONSTANTASI BU MODULDA UMUMAN YO'Q: har
 *   fabrikaning BIRINCHI argumenti `marketId`.
 *
 * ⛔ MUTATSIYA BU MODULDA YO'Q VA BO'LMAYDI HAM.
 *
 *    Hisobot — O'QISH yuzasi. «Namunani qayta tortish» marshruti serverda
 *    umuman yozilmagan (D-17.1) va uning yo'qligi 05-11 ning OpenAPI skani
 *    bilan o'lchanadi; bu yerda ham unga simi yo'q. Bandlikni qo'lda
 *    o'zgartiradigan yo'l ham yo'q (`V2-AI-02`).
 *
 * ⛔ FOIZ BU MODULDA HISOBLANMAYDI. Uch nisbat ham, oraliqlar ham,
 *    bazaviy ulush ham javobning O'ZIDAN keladi (`api-types.ts` dagi
 *    blok izohiga qarang).
 * =============================================================================
 */

/* --- Yo'l konstantasi ------------------------------------------------------ */

export const OCCUPANCY_PATH = "/occupancy";

/* --- Poll konstantasi (§8.5) ---------------------------------------------- */

/**
 * Bandlik kunining poll oralig'i — 60 SONIYA.
 *
 * ⚠ 4-FAZANING 30 s I KO'CHIRILMAYDI va bu qaror har domenda QAYTA
 *   hisoblanadi (`snapshot-queries.ts:57-71` ning aynan qoidasi). U yerda
 *   oyna kadr olish sloti (eng tez 15 daqiqa) va 30 s «hozir olinyapti»
 *   ni ko'rsatish uchun edi. Bu yerda ko'rsatiladigan narsa BANDLIK, u esa
 *   slot bo'yicha o'zgaradi — ya'ni 30 s serverni ikki barobar ortiqcha
 *   yuklab, hech qanday yangi ma'lumot bermasdi.
 *
 * ⚠⚠ VA'DA TOR: bugungi kunning MATERIALIZATSIYASI ertasi kuni 03:40 da
 *    bo'ladi (`worker.py::DAY_CLOSE_CRON`, 05-12), ya'ni bugungi javob
 *    odatda BO'SH bo'ladi va poll uni to'ldirmaydi. Poll shunga qaramay
 *    bor, chunki u YAGONA to'g'ri xulq bo'lgan kunni ham qoplaydi:
 *    kun yopilishi qo'lda yoki qayta yuritilganda ekran o'zi yangilanadi.
 *    Bu kutish `occupancy.emptyDay` matni bilan ham aytiladi.
 */
export const OCCUPANCY_POLL_INTERVAL_MS = 60_000;

/* --- Query kalitlari (TUG'ILISHIDANOQ doiralangan, §5.4) ------------------ */

export const occupancyDayKey = (marketId: string, day: string) =>
  domainKey(marketId, "occupancy", "day", day);

/**
 * Aniqlik hisobotining kaliti — davr KALITNING BIR QISMI.
 *
 * ⛔ DAVR TANLAGICHI EKRANDA YO'Q (§16.2 — 8-fazaning yuzasi) va standart
 *    davr SERVERDA hisoblanadi (`ACCURACY_WINDOW_DAYS = 30`). Shuning
 *    uchun normal oqimda ikkala argument ham `null` bo'ladi va so'rovga
 *    birorta parametr qo'shilmaydi: davrni klientda hisoblash o'sha
 *    qoidaning IKKINCHI nusxasini tug'dirardi va ikkovi yarim tunda
 *    ajralib ketardi.
 *
 * ⚠ Argumentlar imzoda QOLADI: ular kalitni davr bo'yicha ajratadi, ya'ni
 *   8-fazada tanlagich qo'shilganda kesh yozuvi O'ZI to'g'ri bo'linadi.
 */
export const accuracyKey = (
  marketId: string,
  from: string | null,
  to: string | null,
) => domainKey(marketId, "occupancy", "accuracy", from, to);

export const roundKey = (marketId: string, day: string) =>
  domainKey(marketId, "occupancy", "round", day);

/**
 * Joriy bozor — kalit qurish uchun YAGONA manba.
 *
 * `review-queries.ts:97-100` bilan AYNI sabab va AYNI shakl. Funksiya
 * EKSPORT QILINMAYDI — u modulning ichki kontrakti.
 */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/**
 * Poll qarori — SOF FUNKSIYA (`refetchInterval` uni faqat chaqiradi, §S-13).
 *
 * ⛔ O'TGAN KUN UCHUN POLL YO'Q: yopilgan kun O'ZGARMAYDI, ya'ni uni
 *    so'rash mavjud bo'lmagan hodisani kutish bo'lardi. Kelajakdagi kun
 *    esa umuman tanlanmaydi (`useDaySelection` uni bugunga tushiradi).
 *
 * ⚠ Shart `capturePollInterval` dagi IKKI shartning faqat BIRINCHISI:
 *   bu yerda «faol qator» tushunchasi yo'q, chunki bandlik qatori
 *   tug'ilishidanoq terminal (kun yopilishi uni bir marta yozadi).
 */
export function occupancyPollInterval(input: {
  day: string;
  todayIso: string;
}): number | false {
  return input.day === input.todayIso ? OCCUPANCY_POLL_INTERVAL_MS : false;
}

/* --- (A) va (D): kunlik xulosa + rastalar ro'yxati ------------------------ */

/**
 * `GET /occupancy?day=…` — besh hisoblagich va rastalar ro'yxati BITTA javobda.
 *
 * ⛔ IKKI SO'ROVGA BO'LINMAYDI: xulosadagi hisoblagich va ro'yxatdagi
 *    badge serverda AYNAN BIR CTE dan chiqadi (`_PER_STALL_CTE`). Ularni
 *    ikki marshrutdan olish o'sha yagona manbani klientda ikkiga
 *    ajratardi va «xulosada 68, ro'yxatda 69» holati QAYTIB kelardi.
 *
 * ⚠ `enabled: marketId !== null` — KONTRAKT (`market-queries.ts:186-192`),
 *   qulaylik emas: bozorsiz sessiyada javob `403 market_not_selected`
 *   bo'lardi va u kesh grafida yashab qolardi.
 */
export function useOccupancyDay(
  day: string,
  todayIso: string,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: occupancyDayKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(`${OCCUPANCY_PATH}?day=${encodeURIComponent(day)}`, {
        schema: occupancyDaySchema,
      }),
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    refetchInterval: () => occupancyPollInterval({ day, todayIso }),
    refetchIntervalInBackground: false,
  });
}

/* --- (B): aniqlik hisoboti ------------------------------------------------ */

/**
 * `GET /occupancy/accuracy` — chalkashlik matritsasi va uch oraliq.
 *
 * =========================================================================
 * ⛔ POLL YO'Q — VA BU KUN TANLAGICHIDAN MUSTAQIL QAROR.
 *
 *    Blok KUNLIK EMAS: u oyning to'plangan namunasi (§11.1 — «(B)
 *    o'zgarmaydi»). Uni kun bilan birga poll qilish har 60 soniyada
 *    30 kunlik agregatni qayta hisoblatardi va ekranda hech nima
 *    o'zgarmasdi.
 *
 * ⛔ DAVR PARAMETRLARI YUBORILMAYDI: standart davr serverning
 *    `ACCURACY_WINDOW_DAYS` konstantasidan keladi. Klient `from`/`to` ni
 *    hisoblasa, o'sha qoidaning ikkinchi nusxasi tug'ilardi.
 * =========================================================================
 */
export function useAccuracyReport(options?: { enabled?: boolean }) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: accuracyKey(marketId ?? "", null, null),
    queryFn: () =>
      apiFetch(`${OCCUPANCY_PATH}/accuracy`, { schema: accuracyReportSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
    refetchOnWindowFocus: false,
  });
}

/* --- (C): namuna holati --------------------------------------------------- */

/**
 * `GET /occupancy/round?day=…` — bugungi ko'r audit turining holati.
 *
 * ⚠ POLL KUNLIK SO'ROV BILAN AYNI QOIDADA: nazoratchi kun davomida javob
 *   beradi, ya'ni bugungi javobsizlar soni HAQIQATAN o'zgaradi. O'tgan
 *   kunniki esa qotgan.
 *
 * ⛔ «QAYTA TORTISH» YO'Q: bu hook faqat O'QIYDI. Turni qayta tortadigan
 *    marshrut serverda umuman yozilmagan (D-17.1).
 */
export function useAuditRound(
  day: string,
  todayIso: string,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: roundKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(`${OCCUPANCY_PATH}/round?day=${encodeURIComponent(day)}`, {
        schema: auditRoundSchema,
      }),
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    refetchInterval: () => occupancyPollInterval({ day, todayIso }),
    refetchIntervalInBackground: false,
  });
}
