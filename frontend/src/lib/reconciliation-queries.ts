"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { apiFetch } from "@/lib/api-client";
import {
  CASE_STATUSES,
  SUBJECT_KINDS,
  soumSchema,
} from "@/lib/api-types";
import type { CaseStatusValue, SubjectKindValue } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * NOMUVOFIQLIK YUZASINING SERVER HOLATI — ⛔ YAGONA MODUL (W0-F4, §5.3).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ NEGA YAGONA VA NEGA `billing-*` GA QO'SHILMAYDI
 * -----------------------------------------------------------------------
 * 1. ⛔ DARVOZA SHUNDAN KEYIN YOZILISHI MUMKIN. Taqiqlangan nomlar
 *    reyestri (§16.6) `components/reconciliation/**` VA AYNAN SHU FAYL
 *    bo'ylab izlanadi. Aralash modulda ba'zi nom QONUNIY bo'lardi
 *    (`billing-charge-queries.ts` da sotuvchi ustuni bor) va shart
 *    KONTEKSTGA BOG'LIQ bo'lib qolardi — 06-UI-SPEC §5.3 ning takrori.
 *
 * 2. KESH SIYOSATI BIR XIL — hammasi YOZILGAN ma'lumot (D-07); istisno
 *    faqat yetkazilganlik va u shu faylda OCHIQ yozilgan (pastda).
 *
 * 3. TIP TIZIMI ISH QILADI — aralash modulda tip birlashmasi paydo
 *    bo'lardi va `undefined` JIMGINA o'tardi.
 *
 * ⚠ YETKAZILGANLIK SO'ROVI HAM SHU MODULDA TUG'ILADI (07-16 uni
 *   KENGAYTIRADI, ikkinchi modul OCHMAYDI). Bugun bu yerda uning KESH
 *   SIYOSATI va kalit fabrikasi bor; sxemasi va hook'i 07-16 niki.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ ANIQLIK ULUSHI BU YERDA SO'RALMAYDI — VA BU QAROR
 * -----------------------------------------------------------------------
 * Serverda `GET /reconciliation/hit-rate?from=&to=` bor (07-10) va u
 * DAVR kesimida ishlaydi. Ekrandagi «aniqlik ulushi» esa KUN kesimida va
 * u `GET /reconciliation/cases` envelope'ining ⛔ TO'RT SANOG'IDAN
 * RENDER PAYTIDA hisoblanadi (§9.2, §9.5, D-13):
 *
 *   * ⛔ IKKINCHI SO'ROV QILINMAYDI — ikki so'rov ikki lahzani ko'rsatib,
 *     ekranda «ikki xil haqiqat» tug'dirardi (§5.4 ning butun mazmuni);
 *   * ⛔ NISBAT KLIENTDA SAQLANMAYDI — na o'zgaruvchi, na maydon
 *     nomida. Saqlangan hosila ikkinchi haqiqat manbai bo'lardi va
 *     §16.6 dagi taqiqlangan nomlar reyestri buni MEXANIK ravishda
 *     o'lchaydi.
 *
 * ⚠ Shuning uchun bu faylda o'sha marshrutning javob sxemasi ATAYIN
 *   YO'Q: sxema serverning maydon nomini LITERAL sifatida olib kirardi
 *   va taqiq faqat izohda qolardi. Davr kesimidagi ulush — 8-fazaning
 *   trend yuzasi (§17.1).
 * =============================================================================
 */

/* --- Yo'l konstantalari ---------------------------------------------------- */

export const RECONCILIATION_REPORT_PATH = "/reconciliation/report";
export const RECONCILIATION_CASES_PATH = "/reconciliation/cases";
export const RECONCILIATION_DELIVERY_PATH = "/reconciliation/delivery";

/**
 * Bitta sahifadagi eng ko'p case — SERVER CHEGARASINING ko'zgusi.
 *
 * ⛔ Sahifalash ⛔ KEYSET (DQ-4): kursor serverdan kelgan UNUMSIZ satr
 *    bo'lib qaytariladi va klient uni PARSE QILMAYDI. Siljish bo'yicha
 *    sahifalash ⛔ ISHLATILMAYDI — navbat kun davomida o'sadi va u
 *    takroriy yoki tushib qolgan qatorlar berardi.
 */
export const CASE_PAGE_SIZE = 50;

/* --- Yopiq to'plamlarning YUMSHOQ o'qilishi -------------------------------- */

/*
 * ⛔⛔ SXEMA REYESTR BILAN QULFLANMAYDI (04-10 darsi).
 *
 * `subject_kind` va `status` — YOPIQ to'plamlar, lekin ular sxemada
 * `z.string()` bo'lib qoladi. Sabab mexanik: qulflangan sxemada bitta
 * yangi backend a'zosi butun javobni PARSE CHEGARASIDA yiqitardi va
 * direktor kunlik hisobot o'rniga BO'SH SAHIFA ko'rardi — ya'ni yagona
 * yangi a'zo eng yuqori ustuvorlikdagi yuzani (§1.1, Y-1) o'chirardi.
 *
 * Yopiqlik KO'RINISHDA majburlanadi: noma'lum qiymat zaxira yorliq
 * oladi va reyestr bo'ylab yuradigan darvoza uni ushlaydi.
 */

/** Qiymat reyestrda bormi — KO'RINISH qatlamining yagona shoxi. */
export function isCaseStatus(value: string): value is CaseStatusValue {
  return (CASE_STATUSES as readonly string[]).includes(value);
}

export function isSubjectKind(value: string): value is SubjectKindValue {
  return (SUBJECT_KINDS as readonly string[]).includes(value);
}

/* --- Sxemalar — HAMMASI `z.strictObject` ---------------------------------- */

/**
 * Kunlik hisobotning bitta qatori (§8.3).
 *
 * ⛔ SOTUVCHI ISMI BU JAVOBDA YO'Q — faqat `vendor_id`. Ism KLIENTDA,
 *    mavjud va AUDIT QILINGAN `GET /vendors` marshrutidan olinadi
 *    (§5.5, D-05). Server 07-10 da buni SABOTAJ bilan o'lchagan:
 *    ismning qo'shilishi TO'RT tenancy testini qizartirgan.
 *
 * ⛔ `expected_soum` — `anomaly` sinfida ⛔ `null`, NOL EMAS.
 *    Biriktirilmagan zonaning tarifi BILINMAYDI, ya'ni nol yozish «bu
 *    savdodan hech nima kutilmagan» degan YOLG'ON da'vo bo'lardi. Klient
 *    ham uni nolga AYLANTIRMAYDI va yig'indiga QO'SHMAYDI.
 *
 * ⛔ `case_id` / `status` `null` bo'lishi mumkin: nomuvofiqlikning O'ZI
 *    `recon.open` yugurishidan OLDIN ham mavjud bo'ladi. Bunday qatorda
 *    ekran «Navbatga olinmagan» yorlig'ini beradi va ⛔ AMAL YO'Q (§8.5).
 *
 * ⛔ `evidence_snapshot_ids` — FAQAT identifikatorlar. Ular kadr
 *    BAYTLARIGA aylanmaydi: bu yuzada dalil ⛔ HAVOLA (§8.4, M-7).
 */
export const reportRowSchema = z.strictObject({
  subject_kind: z.string(),
  case_id: z.uuid().nullable(),
  status: z.string().nullable(),
  service_date: z.string(),
  stall_code: z.string(),
  vendor_id: z.uuid().nullable(),
  expected_soum: soumSchema.nullable(),
  paid_soum: soumSchema.nullable(),
  evidence_snapshot_ids: z.array(z.uuid()),
});

export type ReportRow = z.infer<typeof reportRowSchema>;

/**
 * `GET /reconciliation/report?day=` javobining O'RAMI (07-10 kontrakti).
 *
 * =========================================================================
 * ⛔⛔ IKKI SANOQ VA ULAR HECH QACHON QO'SHILMAYDI (Pattern 4, §8.2).
 *
 *   `unpaid_count`       — sinf A: HOSILA (`daily_charges` − `payments`).
 *                          Ertaga to'lov kelsa qator YO'QOLADI.
 *   `unregistered_count` — sinf B: QATOR (`billing_anomalies`). QOLAVERADI.
 *
 * Bitta songa qo'shish ikki xil UMR KO'RADIGAN narsani teng qilardi. Va
 * undan qimmatrog'i — B da summa ⛔ UMUMAN YO'Q, ya'ni yig'indi NOL
 * qo'shib hisoblanardi va u ⛔ KAM KO'RSATILGAN YO'QOTISH bo'lardi.
 *
 * ⛔ Shuning uchun `unpaid_expected_soum` FAQAT sinf A ustida yig'iladi
 *    va serverdan KELGAN HOLICHA olinadi — klient uni qayta hisoblamaydi.
 * =========================================================================
 *
 * ⛔ IKKALA SANOQ HAM NOL BO'LGANDA HAM KELADI: «bu kunda nomuvofiqlik
 *    yo'q» va «hisoblagich ishlamayapti» bir xil ko'rinmasligi kerak.
 */
export const reportSchema = z.strictObject({
  day: z.string(),
  rows: z.array(reportRowSchema),
  unpaid_count: z.number().int(),
  unregistered_count: z.number().int(),
  unpaid_expected_soum: soumSchema,
});

export type ReconciliationReport = z.infer<typeof reportSchema>;

/**
 * Navbatning bitta qatori (§9.2).
 *
 * ⚠ `anomaly_id` / `charge_id` — ⛔ XOR: ikkalasidan AYNAN BITTASI
 *   to'ldirilgan. Shox `subject_kind` bo'yicha tanlanadi, «qaysi ustun
 *   bo'sh?» bo'yicha EMAS (DQ-5).
 *
 * ⛔ `assignee_user_id` — IDENTIFIKATOR, ISM EMAS. `null` = hali hech
 *    kimga biriktirilmagan va ekranda «Biriktirilmagan» deb chiziladi.
 */
export const caseRowSchema = z.strictObject({
  case_id: z.uuid(),
  subject_kind: z.string(),
  anomaly_id: z.uuid().nullable(),
  charge_id: z.uuid().nullable(),
  service_date: z.string(),
  status: z.string(),
  assignee_user_id: z.uuid().nullable(),
  created_at: z.string(),
});

export type CaseRow = z.infer<typeof caseRowSchema>;

/**
 * `GET /reconciliation/cases?day=` — kun kesimidagi navbat (DQ-4).
 *
 * =========================================================================
 * ⛔⛔ TO'RT SANOQ ENVELOPE'DA KELADI — VA AYNIQSA SHU SABABLI.
 *
 * Aniqlik ulushi (§9.5) ularning ⛔ HOSILASI va ⛔ IKKINCHI SO'ROV
 * QILMAYDI. Ikki so'rov ikki LAHZANI ko'rsatardi: navbat qatori bilan
 * foiz bir-biriga mos kelmay qolardi va direktor «ekranda ikki xil
 * raqam» ni ko'rib tizimga ishonmay qo'yardi (§1.2 ssenariysi).
 *
 * ⛔ SANOQLAR `status` FILTRIDAN MUSTAQIL (server kontrakti): filtr
 *    yoqilganda «bugun nechta nomuvofiqlik yopildi?» savolining javobi
 *    O'ZGARMASLIGI kerak.
 * =========================================================================
 *
 * ⚠ `next_cursor` — ATAYIN UNUMSIZ SATR. Klient uni PARSE QILMAYDI va
 *   serverga o'zgarishsiz qaytaradi; kursorning ichki shakli SERVER
 *   qarori (07-10) va uni klientga ochish sahifalash qoidasini ikkiga
 *   bo'lardi.
 */
export const caseListSchema = z.strictObject({
  day: z.string(),
  rows: z.array(caseRowSchema),
  new_count: z.number().int(),
  in_review_count: z.number().int(),
  justified_count: z.number().int(),
  unjustified_count: z.number().int(),
  next_cursor: z.string().nullable(),
});

export type CaseList = z.infer<typeof caseListSchema>;

/* --- Kesh kalitlari (TUG'ILISHIDANOQ doiralangan, §5.4) ------------------- */

/*
 * ⛔ HAR KALIT `domainKey(marketId, ...)` DAN QURILADI — ya'ni BIRINCHI
 *    ARGUMENT `marketId` va natija `["m", marketId, ...]` prefiksi
 *    ostida qoladi (04-10 konvensiyasi, `tenant-cache.test.tsx` bilan
 *    qulflangan). Yalang'och `[marketId, "..."]` shakli kodbazadagi
 *    yagona doiralash konvensiyasini IKKIGA bo'lardi va prefiks bo'yicha
 *    tozalash bu kalitlarga YETIB BORMASDI (07-05 da o'lchangan).
 */

export const reportKey = (marketId: string, day: string) =>
  domainKey(marketId, "recon-report", day);

export const casesKey = (marketId: string, day: string, cursor: string) =>
  domainKey(marketId, "recon-cases", day, cursor);

export const deliveryKey = (marketId: string, day: string) =>
  domainKey(marketId, "recon-delivery", day);

/** Yozilgan hisobot O'ZGARMAS (D-07) — 60 soniya XAVFSIZ. */
export const REPORT_STALE_TIME_MS = 60_000;

/**
 * Navbat KUN ICHIDA o'zgaradi (holat, mas'ul) — 30 soniya.
 *
 * ⚠ Aniqlik ulushi ham SHU so'rovdan chiqadi, ya'ni u navbat bilan
 *   AYNAN BIR TEZLIKDA yangilanadi va ikkalasi hech qachon ajralmaydi.
 */
export const CASES_STALE_TIME_MS = 30_000;

/** O'tgan kunning yetkazilganligi O'ZGARMAS — 60 soniya. */
export const DELIVERY_PAST_STALE_TIME_MS = 60_000;

export type CachePolicy = { staleTime: number; gcTime: number };

/**
 * ⛔⛔ YETKAZILGANLIKNING KESH SIYOSATI — `bugun` DA NOL, IKKALASI HAM.
 *
 * =========================================================================
 * Bugungi yetkazilganlik ⛔ JONLI: `pending -> sent -> delivered`
 * SONIYALARDA o'zgaradi. Eski javob «hali yuborilmadi» deb ⛔ YOLG'ON
 * GAPIRARDI va aynan shu yolg'on BOT-04 ning butun mavjudlik sababini
 * («xabar kelmadi» nizosi, D-02) yo'q qilardi.
 *
 * ⛔ IKKALASI HAM NOL BO'LISHI SHART va `staleTime: 0` YETARLI EMAS:
 *    `gcTime` musbat qolsa, blok qayta chizilganda TanStack avval
 *    keshdagi eski javobni ko'rsatadi va yangisi kelguncha ekranda
 *    eskirgan holat turadi. Direktor uni «hozirgi holat» deb o'qirdi.
 *
 * ⛔ AVTOMATIK SO'ROV YO'Q (§11.4): `refetchInterval` YOZILMAYDI. Ochiq
 *    qoldirilgan sahifa har necha soniyada so'rov yuborardi va raqam
 *    JIMGINA o'zgarardi — «men boshqa raqam ko'rgandim» nizosi (§10.5
 *    bilan bir sinf). Yangilash — foydalanuvchining OCHIQ NIYATI.
 * =========================================================================
 */
export function deliveryCachePolicy(isToday: boolean): CachePolicy {
  if (isToday) return { staleTime: 0, gcTime: 0 };
  return {
    staleTime: DELIVERY_PAST_STALE_TIME_MS,
    gcTime: DELIVERY_PAST_STALE_TIME_MS,
  };
}

/* --- So'rovlar ------------------------------------------------------------- */

/** Joriy bozor — kalit qurish uchun YAGONA manba (eksport QILINMAYDI). */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/**
 * `GET /reconciliation/report?day=` — ikkala sinf ham bitta javobda.
 *
 * ⚠ Bu so'rov `day = bugun` da UMUMAN YUBORILMAYDI (§4.4): hisob D+1
 *   04:10 da, case'lar D+1 04:25 da tug'iladi. Shart SAHIFADA
 *   qo'llanadi va bu yerga `enabled` bo'lib keladi — hook kun haqida
 *   o'zi qaror qabul qilmaydi.
 */
export function useReconciliationReport(
  day: string,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: reportKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(
        `${RECONCILIATION_REPORT_PATH}?day=${encodeURIComponent(day)}`,
        { schema: reportSchema },
      ),
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    staleTime: REPORT_STALE_TIME_MS,
  });
}

/**
 * `GET /reconciliation/cases?day=` — navbat va uning to'rt sanog'i.
 *
 * ⚠ `cursor` — serverdan kelgan satr O'ZGARISHSIZ. Bo'sh satr = birinchi
 *   sahifa; u kalitning bir qismi, ya'ni har sahifa O'Z keshida yashaydi.
 */
export function useReconciliationCases(
  day: string,
  cursor: string,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: casesKey(marketId ?? "", day, cursor),
    queryFn: () => {
      const params = new URLSearchParams({ day });
      if (cursor !== "") params.set("cursor", cursor);
      return apiFetch(`${RECONCILIATION_CASES_PATH}?${params.toString()}`, {
        schema: caseListSchema,
      });
    },
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    staleTime: CASES_STALE_TIME_MS,
  });
}
