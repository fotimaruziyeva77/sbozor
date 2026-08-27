"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { z } from "zod";

import { apiFetch } from "@/lib/api-client";
import {
  CASE_STATUSES,
  DELIVERY_STATES,
  NOTIFICATION_KINDS,
  SUBJECT_KINDS,
  soumSchema,
} from "@/lib/api-types";
import type {
  CaseStatusValue,
  DeliveryStateValue,
  NotificationKindValue,
  SubjectKindValue,
} from "@/lib/api-types";
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
 *
 * ⛔⛔ KONSTANTA SO'ROVGA YUBORILADI — VA BU O'LCHANGAN NUQSONNING
 *    TUZATISHI (B-6). U bir muddat e'lon qilingan, lekin ⛔ HECH QAYERDA
 *    ishlatilmagan edi: ro'yxat serverning standart 50 tasini olardi,
 *    sanoqlar esa KUN BO'YICHA to'liq kelardi va direktor «Yangi 120»
 *    yozuvini 50 qatorli jadval ustida ko'rardi. ⛔ Yonidagi songa ZID
 *    ro'yxat — yetishmayotgan funksiyadan QIMMATROQ nuqson: u ekranning
 *    HAMMASIGA bo'lgan ishonchni yo'qotadi.
 */
export const CASE_PAGE_SIZE = 50;

/**
 * Bitta sahifadagi eng ko'p yetkazilganlik qatori — `CASE_PAGE_SIZE` naqshi.
 *
 * ⛔ Server `le=DELIVERY_PAGE_SIZE` bilan CHEGARALAYDI, ya'ni bu son
 *    o'sha chegaraning ko'zgusi; kattaroq qiymat `422` bilan qaytardi.
 */
export const DELIVERY_PAGE_SIZE = 50;

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

/** Yetkazilganlik holati reyestrda bormi — ⛔ zaxira yorliq shundan. */
export function isDeliveryState(value: string): value is DeliveryStateValue {
  return (DELIVERY_STATES as readonly string[]).includes(value);
}

export function isNotificationKind(
  value: string,
): value is NotificationKindValue {
  return (NOTIFICATION_KINDS as readonly string[]).includes(value);
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

/**
 * Tarixning bitta bo'g'ini — ⛔ O'ZGARMAS QATOR (D-14).
 *
 * ⛔ `actor_user_id === null` = ⛔ **TIZIM**, «noma'lum» EMAS: navbatni
 *    `recon.open` cron'i ochadi va unga odam biriktirish «kim qaror
 *    qildi?» savoliga YOLG'ON javob bo'lardi.
 *
 * ⛔ `from_status === null` = qator TUG'ILDI: birinchi hodisada oldingi
 *    holat FIZIK ravishda mavjud emas.
 */
export const caseEventSchema = z.strictObject({
  from_status: z.string().nullable(),
  to_status: z.string(),
  actor_user_id: z.uuid().nullable(),
  note: z.string().nullable(),
  created_at: z.string(),
});

export type CaseEvent = z.infer<typeof caseEventSchema>;

/**
 * `GET /reconciliation/cases/{case_id}` — DL-5 ning butun mazmuni.
 *
 * ⛔ TARIX SAHIFALANMAYDI va bu SERVER qarori: u nazoratchining QO'L
 *    harakatlaridan o'sadi va nizo hujjatida (D-02) aynan TO'LIQLIK
 *    muhim. Klient uni QISQARTIRMAYDI ham — «oxirgi 5 ta» ko'rinishi
 *    o'zgarish tarixini jimgina kesib qo'yardi.
 *
 * ⛔ `resolution_note` — case'ning JORIY matni; tarixdagi har `note` esa
 *    O'SHA QADAMNIKI. Ikkalasi bir-birini almashtirmaydi.
 */
export const caseDetailSchema = z.strictObject({
  case_id: z.uuid(),
  subject_kind: z.string(),
  anomaly_id: z.uuid().nullable(),
  charge_id: z.uuid().nullable(),
  service_date: z.string(),
  status: z.string(),
  assignee_user_id: z.uuid().nullable(),
  created_at: z.string(),
  resolution_note: z.string().nullable(),
  events: z.array(caseEventSchema),
  evidence_snapshot_ids: z.array(z.uuid()),
});

export type CaseDetail = z.infer<typeof caseDetailSchema>;

/**
 * Yetkazilganlik jadvalining bitta qatori (BOT-04, §11.3).
 *
 * =========================================================================
 * ⛔⛔ XABARNING MAZMUNI BU SXEMADA YO'Q — VA U «UNUTILGAN» EMAS.
 *
 * Server xabarning TANASINI ham, tayyor MATNNI ham, Telegram
 * IDENTIFIKATORINI ham QAYTARMAYDI (07-16 marshrut kontrakti).
 * ⛔ `z.strictObject` shuning uchun MAJBURIY: server bir kun «qulaylik
 * uchun» qo'shsa, klient PARSE chegarasida darhol qizaradi va maydon
 * ekranga JIMGINA chiqib ketolmaydi.
 *
 * ⚠ Taqiqlangan maydon nomlari bu izohda LITERAL yozilmaydi —
 *   `badge.tsx:24-26` da o'rnatilgan kodbaza konvensiyasi (skan izohni
 *   koddan ajratsa ham, nusxa darvozani o'ziga qarshi qo'yish odati
 *   ATAYIN rad etilgan).
 * =========================================================================
 *
 * ⛔ `status` — reyestr bilan QULFLANMAYDI (`z.string()`): backend
 *    oltinchi a'zo qo'shsa butun jadval parse chegarasida yiqilardi va
 *    direktor «xabar bordimi?» savoliga BO'SH SAHIFA ko'rardi. Yopiqlik
 *    KO'RINISHDA majburlanadi (`delivery-badge.tsx` zaxira yorliq
 *    beradi) va reyestrdan yuradigan darvoza uni ushlaydi.
 *
 * ⛔ `error_type` — ⛔ TUR NOMI (`type(exc).__name__`), xato MATNI EMAS
 *    (D-04): Telegram istisnosining matni bot TOKENINI tashiydi.
 *    Chegara SERVERDA, yozish paytida qo'yiladi.
 *
 *    ⚠ Serverdagi USTUN nomi boshqacha va farq ATAYIN: taqiqlangan
 *      nomlar reyestri o'sha nomni PREFIKS sifatida qidiradi va u
 *      XAVFSIZ maydonni ham ushlab qolardi. Sim nomi shu sababdan
 *      qisqartirilgan; sabab server sxemasining docstringida to'liq
 *      yozilgan. ⚠ Eski nom bu izohda LITERAL yozilmaydi.
 *
 * ⛔ EKRANDA XOM QIYMAT CHIZILMAYDI: u `lib/reconciliation-errors.ts`
 *    dagi YOPIQ to'plamga xaritalanadi (§14.9) — istisno sinfining nomi
 *    direktorga hech nima aytmaydi.
 *
 * ⚠ `updated_at` — OXIRGI HOLAT O'ZGARISHI. `notification_outbox` da
 *   `last_attempt_at` USTUNI YO'Q (07-16 SUMMARY); har holat o'zgarishi
 *   `updated_at` ni yangilaydi, ya'ni u aynan shu savolga javob beradi.
 */
export const deliveryRowSchema = z.strictObject({
  outbox_id: z.uuid(),
  kind: z.string(),
  recipient_kind: z.string(),
  vendor_id: z.uuid().nullable(),
  status: z.string(),
  attempt_count: z.number().int(),
  created_at: z.string(),
  updated_at: z.string(),
  error_type: z.string().nullable(),
  error_status_code: z.number().int().nullable(),
});

export type DeliveryRow = z.infer<typeof deliveryRowSchema>;

/**
 * `GET /reconciliation/delivery?day=` — kunning yetkazilganlik yozuvi.
 *
 * ⛔ BESHALA HISOBLAGICH HAM NOL BO'LGANDA HAM KELADI va klient ularni
 *    ⛔ SHARTSIZ chizadi: «bu kunda bloklangan sotuvchi yo'q» bilan
 *    «hisoblagich ishlamayapti» bir xil ko'rinsa, direktor D-02
 *    nizosida noto'g'ri xulosaga kelardi.
 *
 * ⛔ `blocked_count` `failed_count` GA ⛔ QO'SHILMAYDI (D-22): blok —
 *    sotuvchining HUQUQI va qarz undirish jarayonining bir qismi,
 *    texnik nosozlik EMAS.
 */
export const deliveryListSchema = z.strictObject({
  day: z.string(),
  rows: z.array(deliveryRowSchema),
  pending_count: z.number().int(),
  sent_count: z.number().int(),
  delivered_count: z.number().int(),
  failed_count: z.number().int(),
  blocked_count: z.number().int(),
  next_cursor: z.string().nullable(),
});

export type DeliveryList = z.infer<typeof deliveryListSchema>;

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

/**
 * ⛔ KURSOR KALITNING BIR QISMI ⛔ EMAS — sahifalar BITTA zanjirda yashaydi.
 *
 * Avval har sahifa O'Z kesh yozuvida edi va bu `useInfiniteQuery` bilan
 * ⛔ TO'QNASHADI: TanStack sahifalarni bitta kalit ostida `pages[]` bo'lib
 * saqlaydi. Kursor kalitga qo'shilsa, ikkinchi sahifa YANGI zanjir
 * boshlardi va birinchisi ⛔ YO'QOLARDI — ya'ni «Yana yuklash» 50 qatorni
 * boshqa 20 taga ALMASHTIRARDI (`useStallsQuery` naqshi bilan ayni sabab).
 */
export const casesKey = (marketId: string, day: string) =>
  domainKey(marketId, "recon-cases", day);

export const deliveryKey = (marketId: string, day: string) =>
  domainKey(marketId, "recon-delivery", day);

/**
 * Bitta nomuvofiqlikning tafsiloti — DL-5 ning kaliti.
 *
 * ⚠ KUN EMAS, IDENTIFIKATOR bo'yicha doiralangan: dialog KUNDAN
 *   mustaqil ochiladi va o'sha case boshqa kunga ko'chsa ham (u
 *   ko'chmaydi — `service_date` o'zgarmas) kalit BARQAROR qoladi.
 */
export const caseDetailKey = (marketId: string, caseId: string) =>
  domainKey(marketId, "recon-case", caseId);

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

/**
 * Joriy bozor — kalit qurish uchun YAGONA manba.
 *
 * =========================================================================
 * ⛔⛔ ENDI EKSPORT QILINADI — VA BU «QULAYLIK» EMAS (IN-08).
 *
 * Barcha so'rovlar `enabled: marketId !== null` bilan boshqariladi, lekin
 * ⛔ TanStack v5 da O'CHIRILGAN so'rov `isPending` HOLATIDA QOLADI. Ya'ni
 * bozorsiz sessiyada to'rtala recon bloki ham ⛔ CHEKSIZ SKELET
 * ko'rsatardi: foydalanuvchi kutardi, hech nima kelmasdi va sabab
 * ⛔ HECH QAYERDA yozilmasdi.
 *
 * ⛔ `HeadlineCard` bu holatni ALLAQACHON ochiq qo'riqlaydi
 *    (`marketId === null` -> so'rov ham, karta ham yo'q). Recon bloklari
 *    esa yo'q edi — ya'ni bir kod bazasida bir savolga IKKI javob.
 *
 * ⛔ SHART BLOKDA, SAHIFADA EMAS: sahifada bir marta tekshirish blokning
 *    O'Z mazmun atributini (`data-recon-content`) ham olib tashlardi va
 *    sahifa darvozasi «blok chizilmadi» deb qizarardi — holbuki haqiqiy
 *    sabab BOSHQA. Har blok o'z holatini O'ZI nomlaydi (`unpaid-list.tsx`
 *    ning «HAR BLOK ... SAHIFA EMAS» bandi).
 *
 * ⚠ NOMI `useMarketId` EMAS: `market-queries.ts` da AYNI nomli MAHALLIY
 *   funksiya bor va ikki modul bir nomni eksport qilsa, keyingi ijrochi
 *   ularni bir narsa deb hisoblardi.
 * =========================================================================
 */
export function useReconciliationMarketId(): string | null {
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
  const marketId = useReconciliationMarketId();

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

/* --- Sahifalangan so'rovning YUPQA O'RAMI --------------------------------- */

/*
 * =============================================================================
 * ⛔⛔ NEGA O'RAM BOR VA NEGA U «QULAYLIK» EMAS.
 *
 * Sahifalangan javobda IKKI XIL narsa bor va ular ⛔ BOSHQA-BOSHQA
 * qoidaga bo'ysunadi:
 *
 *   `rows`   — sahifalar bo'ylab ⛔ YIG'ILADI (birlashma);
 *   sanoqlar — ⛔ BIRINCHI SAHIFADAN o'qiladi va ⛔ YIG'ILMAYDI.
 *
 * Sabab server kontraktida: sanoq `status` filtridan HAM, sahifadan HAM
 * MUSTAQIL — u HAR javobda BUTUN kunning soni bo'lib keladi. Ularni
 * qo'shish «Yangi 120» ni ikkinchi sahifadan keyin «Yangi 240» qilardi,
 * ya'ni B-6 ni ⛔ TESKARI tomondan takrorlardi.
 *
 * ⛔ O'RAM IKKALA ISTE'MOLCHINI BITTA SHAKLGA QARATADI: navbat bloki ham,
 *    aniqlik ulushi ham AYNAN shu maydonlarni o'qiydi, ya'ni ulush
 *    ARIFMETIKASI o'zgarishsiz qoladi (u hamon to'rt sanoqning hosilasi
 *    va ⛔ IKKINCHI SO'ROV QILMAYDI).
 * =============================================================================
 */

/** Sahifalangan so'rov + ikki hosila maydon. ⛔ Nisbat bu yerda YO'Q. */
export type PagedQuery<TPage, TRow> = UseInfiniteQueryResult<
  InfiniteData<TPage>,
  Error
> & {
  /** Barcha yuklangan sahifalarning qatorlari — TARTIB SAQLANADI. */
  readonly rows: readonly TRow[];
  /** ⛔ BIRINCHI sahifaning envelope'i — sanoqlarning YAGONA manbai. */
  readonly counts: TPage | undefined;
};

function withPages<TPage, TRow>(
  query: UseInfiniteQueryResult<InfiniteData<TPage>, Error>,
  pick: (page: TPage) => readonly TRow[],
): PagedQuery<TPage, TRow> {
  const pages = query.data?.pages ?? [];
  return Object.assign(query, {
    rows: pages.flatMap((page) => [...pick(page)]),
    counts: pages[0],
  });
}

/**
 * `GET /reconciliation/cases?day=` — navbat va uning to'rt sanog'i.
 *
 * ⛔⛔ SAHIFALASH KEYSET (DQ-4) va `useStallsQuery` NAQSHINING AYNAN
 *    NUSXASI: `initialPageParam: null` + `getNextPageParam: (last) =>
 *    last.next_cursor`. Yangi shakl o'ylab topilmaydi — kodbazada
 *    sahifalashning BITTA naqshi bo'lishi kerak.
 *
 * ⚠ `cursor` ARGUMENTI OLIB TASHLANDI: uni chaqiruvchi bergan paytda
 *   ikkala iste'molchi ham `""` yozardi va ikkinchi sahifaga yo'l
 *   ⛔ UMUMAN OCHILMASDI (B-6). Endi kursorni TanStack olib yuradi va
 *   klient uni ⛔ PARSE QILMAYDI, faqat qaytaradi.
 */
export function useReconciliationCases(
  day: string,
  options?: { enabled?: boolean },
): PagedQuery<CaseList, CaseRow> {
  const marketId = useReconciliationMarketId();

  const query = useInfiniteQuery({
    queryKey: casesKey(marketId ?? "", day),
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({ day });
      /* ⛔ KONSTANTANING HAQIQIY ISTE'MOLCHISI — chegara AYTIB yuboriladi. */
      params.set("limit", String(CASE_PAGE_SIZE));
      if (pageParam !== null) params.set("cursor", pageParam);
      return apiFetch(`${RECONCILIATION_CASES_PATH}?${params.toString()}`, {
        schema: caseListSchema,
      });
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    staleTime: CASES_STALE_TIME_MS,
  });

  return withPages(query, (page) => page.rows);
}

/**
 * `GET /reconciliation/cases/{case_id}` — DL-5 ochilganda VA FAQAT o'shanda.
 *
 * ⛔ `enabled` DIALOG HOLATIDAN keladi: ro'yxatdagi har qator uchun
 *    oldindan tafsilot tortish 10-50 ta ortiqcha so'rov bo'lardi va
 *    ularning har biri serverda audit shovqinini yozardi.
 */
export function useCaseDetail(
  caseId: string | null,
  options?: { enabled?: boolean },
) {
  const marketId = useReconciliationMarketId();

  return useQuery({
    queryKey: caseDetailKey(marketId ?? "", caseId ?? ""),
    queryFn: () =>
      apiFetch(
        `${RECONCILIATION_CASES_PATH}/${encodeURIComponent(caseId ?? "")}`,
        { schema: caseDetailSchema },
      ),
    enabled:
      marketId !== null && caseId !== null && (options?.enabled ?? true),
    staleTime: CASES_STALE_TIME_MS,
  });
}

/**
 * ⛔⛔ YETKAZILGANLIK — `day = bugun` DA JONLI (§5.4, §11.4).
 *
 * =========================================================================
 * Bugungi holat SONIYALARDA o'zgaradi (`pending -> sent -> delivered`) va
 * eski javob «hali yuborilmadi» deb ⛔ YOLG'ON GAPIRARDI — aynan shu
 * yolg'on BOT-04 ning butun mavjudlik sababini («xabar kelmadi» nizosi,
 * D-02) yo'q qilardi.
 *
 * ⛔ SHUNING UCHUN `staleTime` HAM, `gcTime` HAM NOL (`deliveryCachePolicy`
 *    docstringi): `staleTime` yolg'iz o'zi YETARLI EMAS — blok qayta
 *    chizilganda TanStack avval keshdagi eski javobni ko'rsatadi va
 *    direktor uni «hozirgi holat» deb o'qirdi.
 *
 * ⛔ AVTOMATIK SO'ROV YO'Q: `refetchInterval` ⛔ YOZILMAYDI. Ochiq
 *    qoldirilgan sahifa har necha soniyada so'rov yuborardi va raqam
 *    JIMGINA o'zgarardi — «men boshqa raqam ko'rgandim» nizosi.
 *    Yangilash — foydalanuvchining OCHIQ NIYATI (`[Yangilash]`).
 * =========================================================================
 *
 * ⚠ `isToday` ARGUMENT, hook ichida HISOBLANMAYDI: biznes-kun tanlagichda
 *   yechiladi (`useReconciliationDay()`) va ikkinchi hisob ikki manba
 *   tug'dirardi — Toshkent yarim tunidan keyingi besh soatda ular
 *   BOSHQA-BOSHQA kunni ko'rsatardi.
 *
 * ⛔⛔ BU RO'YXAT HAM SAHIFALANADI (B-6 ning ikkinchi yarmi): marshrut
 *    `next_cursor` qaytaradi va u ham bir muddat ⛔ HECH KIM TOMONIDAN
 *    o'qilmasdi. Kvitansiya soni kunlik to'lov soniga TENG, ya'ni
 *    Karmana konvertida 50 dan oshishi ODATIY holat.
 *
 * ⚠ `refetch()` `[Yangilash]` TUGMASIDA ishlatiladi va `useInfiniteQuery`
 *   da u ⛔ BARCHA yuklangan sahifalarni QAYTA so'raydi. Bu ⛔ KUTILGAN
 *   xulq: direktor «hozirgi holat» so'raganda ekrandagi HAMMA qator
 *   yangilanishi kerak — yarmi yangi, yarmi eski ro'yxat aynan
 *   `deliveryCachePolicy()` oldini olmoqchi bo'lgan yolg'on bo'lardi.
 *
 * ⛔ `refetchInterval` HAMON YOZILMAYDI (§11.4) va `deliveryCachePolicy()`
 *    ning `staleTime`/`gcTime` qarori ⛔ O'ZGARMAYDI.
 */
export function useDeliveries(
  day: string,
  isToday: boolean,
  options?: { enabled?: boolean },
): PagedQuery<DeliveryList, DeliveryRow> {
  const marketId = useReconciliationMarketId();
  const policy = deliveryCachePolicy(isToday);

  const query = useInfiniteQuery({
    queryKey: deliveryKey(marketId ?? "", day),
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({ day });
      params.set("limit", String(DELIVERY_PAGE_SIZE));
      if (pageParam !== null) params.set("cursor", pageParam);
      return apiFetch(`${RECONCILIATION_DELIVERY_PATH}?${params.toString()}`, {
        schema: deliveryListSchema,
      });
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    staleTime: policy.staleTime,
    gcTime: policy.gcTime,
  });

  return withPages(query, (page) => page.rows);
}

/**
 * `PATCH /reconciliation/cases/{case_id}` — hukm VA mas'ul (D-14).
 *
 * =========================================================================
 * ⛔⛔ BEKOR QILISH `invalidateQueries` BILAN, ⛔ `removeQueries` EMAS —
 *     VA SABAB 6-FAZANIKIDAN FARQ QILADI (§5.4).
 *
 * 6-fazada keshdan CHIQARISH kerak edi: eski rastaning summasi
 * NOTO'G'RI PUL YIG'ISHGA olib borardi. Bu yerda esa keshdan chiqarish
 * ro'yxatni ⛔ BO'SHATIB, direktor o'z o'zgarishini ⛔ YO'QOLGAN deb
 * o'ylardi — ya'ni to'g'ri ishlagan yozuv buzuq bo'lib ko'rinardi.
 * =========================================================================
 *
 * ⛔⛔ BEKOR QILINADIGAN DOMENLAR — VA NEGA ULAR IKKITA, UCHTA EMAS:
 *
 *   `recon-cases`  — navbat qatorining O'ZI (holat, mas'ul) ⛔ VA
 *                    ANIQLIK ULUSHI ham. Ulush ⛔ ALOHIDA SO'ROV
 *                    QILMAYDI: u `caseListSchema` ning to'rt sanog'idan
 *                    RENDER PAYTIDA hisoblanadi (§9.2/§9.5, D-13,
 *                    07-15 qarori). Ya'ni `recon-hitrate` degan kesh
 *                    kaliti ⛔ MAVJUD EMAS va uni bekor qilish
 *                    ⛔ NO-OP bo'lardi — kodda esa «ulush ham
 *                    yangilanadi» degan YOLG'ON izoh qolardi.
 *   `recon-report` — hisobot qatoridagi case NISHONI (§8.5).
 *
 * Bittasi unutilsa ekranda ⛔ IKKI XIL HAQIQAT qolardi: navbatda
 * «Asosli», hisobot qatorida esa hamon «Yangi».
 *
 * ⛔ `recon-delivery` bekor QILINMAYDI: hukm chiqarish xabar
 *    yubormaydi va u navbatga tegmaydi. Uni ham bekor qilish jonli
 *    blokni sababsiz qayta so'ratardi.
 *
 * ⚠ Tafsilotning O'ZI (`recon-case`) ham bekor qilinadi: audit izi
 *   YANGI QATOR bilan o'sadi va u dialogda DARHOL ko'rinishi kerak
 *   (D-14 — o'zgarish tarixda ko'rinadi).
 */
export function useCaseUpdate() {
  const client = useQueryClient();
  const marketId = useReconciliationMarketId() ?? "";

  return useMutation({
    /*
     * ⛔⛔ `resolutionNote` — ⛔ `string`, `string | null` EMAS (WR-15).
     *
     * Server `resolution_note = COALESCE(:note, resolution_note)` yozadi,
     * ya'ni `null` «O'ZGARTIRMA» degani. Foydalanuvchi matnni o'chirib
     * saqlaganda eski matn ⛔ QOLIB KETARDI va dialog qayta ochilganda u
     * ⛔ QAYTIB CHIQARDI — «o'zgarishim yo'qoldi» taassuroti.
     *
     * ⛔ TIP DARAJASIDA YOPILADI: `null` ni tasodifan qaytarish endi
     *    ⛔ `tsc` da qizaradi, ya'ni nuqson izohga emas, TIP TIZIMIGA
     *    bog'landi. Bo'sh SATR esa `COALESCE` uchun `NULL` EMAS —
     *    u YOZILADI (server sxemasida `min_length` yo'q, o'lchandi).
     */
    mutationFn: (input: {
      caseId: string;
      status: CaseStatusValue;
      resolutionNote: string;
      assigneeUserId: string | null;
    }) =>
      apiFetch(
        `${RECONCILIATION_CASES_PATH}/${encodeURIComponent(input.caseId)}`,
        {
          method: "PATCH",
          body: {
            status: input.status,
            resolution_note: input.resolutionNote,
            assignee_user_id: input.assigneeUserId,
          },
          schema: caseDetailSchema,
        },
      ),
    onSuccess: (_data, input) => {
      void client.invalidateQueries({
        queryKey: caseDetailKey(marketId, input.caseId),
      });
      for (const domain of ["recon-cases", "recon-report"]) {
        void client.invalidateQueries({ queryKey: domainKey(marketId, domain) });
      }
    },
  });
}
