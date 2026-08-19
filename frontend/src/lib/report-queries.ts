"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, apiRequest } from "@/lib/api-client";
import type { ReportKind } from "@/lib/api-types";
import {
  anomalyArchiveSchema,
  ledgerImportResultSchema,
  receivablesReportSchema,
  liveRevenueSchema,
  revenueReportSchema,
  threeWayReportSchema,
} from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey, IMPORTS_PATH, saveBlob } from "@/lib/market-queries";

/*
 * =============================================================================
 * HISOBOT YUZASINING SERVER HOLATI VA YAGONA EKSPORT YO'LI (W0-F1, §5.3).
 *
 * `occupancy-queries.ts` NAQSHI. Uchta banddan iborat va uchalasi ham
 * DARVOZAGA bog'langan (`scripts/report-copy.test.mjs`).
 *
 * -----------------------------------------------------------------------
 * ⛔ MUTATSIYA BU MODULDA FAQAT DAFTAR IMPORTI UCHUN.
 * -----------------------------------------------------------------------
 * Hisobot — HOSILA (D-03): u `daily_charges`, `payments` va bandlik
 * hodisalaridan chiqadi va ularning BIRORTASI bu yerdan o'zgartirilmaydi.
 * Yagona yozuv — kunlik daftarning `.xlsx` importi (D-17) va u ham
 * ALMASHTIRUVCHI amal, tahrirlovchi emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ FOIZ BU MODULDA HISOBLANMAYDI.
 * -----------------------------------------------------------------------
 * Uch nisbat ham, oraliqlar ham, bazaviy ulush ham javobning O'ZIDAN
 * keladi (05-14 darsi: klientdagi qayta hisob XATO bo'lib emas, IKKINCHI
 * JAVOB bo'lib chiqadi — 5,4 % va 3,8 % ikkalasi ham arifmetik to'g'ri,
 * lekin BOSHQA savolga javob). Yig'indilar ham serverniki: `rows` ustidan
 * yurib jamlash sahifalash tufayli ekrandagi 50 qatorni butun davr deb
 * ko'rsatardi (§8.6).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ `fetch(` BU MODULDA YO'Q — `apiRequest` YAGONA YO'L. VA BU
 *     INTIZOM EMAS, MEXANIKA (§0.2, M-7).
 * -----------------------------------------------------------------------
 * Access token XOTIRADA yashaydi va SO'ROV SARLAVHASIDA ketadi
 * (`api-client.ts:215`); cookie'da faqat refresh bor. Demak
 * `<a href="/api/v1/reports/revenue.xlsx" download>` brauzer tomonidan
 * ⛔ TOKENSIZ ketadi va 401 oladi — brauzer esa 401 javob TANASINI
 * `revenue.xlsx` nomi bilan diskka SAQLAYDI. Foydalanuvchi «fayl
 * yuklandi» deb o'ylaydi, Excel «fayl buzilgan» deydi va xato HECH
 * QAYERDA ko'rinmaydi.
 *
 * ⛔ Shuning uchun `window.open`, `location.href`,
 *    `document.createElement("a")` va ikkinchi tarmoq chaqiruvi bu yerda
 *    YOZILMAYDI. Yagona zanjir:
 *
 *      apiRequest(path) -> response.blob() -> saveBlob(blob, nom)
 *
 * ⚠ `saveBlob()` ICHIDA anchor ham, `URL.createObjectURL` ham BOR — u
 *   `market-queries.ts:1157` da yashaydi va bu skan maydonidan
 *   TASHQARIDA. Bu ATAYIN va ochiq yozilgan (§8.5): `saveBlob` blobni
 *   ALLAQACHON olingan baytlardan saqlaydi, ya'ni tarmoqqa tokensiz
 *   so'rov yubormaydi. Taqiq TARMOQ chaqiruviga, saqlash gigiyenasiga
 *   emas.
 *
 * ⚠ KALITLAR TUG'ILISHIDANOQ DOIRALANGAN (§5.4). `domainKey`
 *   `market-queries.ts` DAN IMPORT QILINADI — ikkinchi nusxa
 *   yaratilmaydi. GLOBAL (marketsiz) KALIT KONSTANTASI BU MODULDA
 *   UMUMAN YO'Q: har fabrikaning BIRINCHI argumenti `marketId`.
 * =============================================================================
 */

/* --- Yo'l konstantasi ------------------------------------------------------ */

export const REPORTS_PATH = "/reports";

/* --- Kesh siyosati (§5.4) -------------------------------------------------- */

/**
 * Davr hisobotlarining `staleTime` — 5 DAQIQA.
 *
 * ⛔ Sabab MA'LUMOTNING O'ZIDA, did emas: davrning yuqori chegarasi
 *    ALLAQACHON kecha (§4.4), ya'ni javob YOPILGAN kunlardan chiqadi va
 *    ⛔ O'ZGARMAS. Qisqaroq oyna serverni sababsiz qayta so'ratardi va
 *    ekranda AYNAN o'sha sonni chizardi.
 */
export const REPORT_STALE_TIME_MS = 5 * 60_000;

/**
 * Solishtiruvning `staleTime` — 30 SONIYA.
 *
 * ⛔ Davr hisobotlaridan QISQA va bu ataylab: daftar importi shu kunning
 *    javobini O'ZGARTIRADI (D-17). Bozor admini faylni yuklab, jadvalni
 *    darhol ko'rishi kerak.
 */
export const COMPARE_STALE_TIME_MS = 30_000;

/* --- Davr --- */

/** Hisobot davri — ⛔ IKKALA chegara ham MAJBURIY (§1.2 qoida 2). */
export type ReportPeriod = {
  readonly from: string;
  readonly to: string;
};

/* --- Query kalitlari (TUG'ILISHIDANOQ doiralangan, §5.4) ------------------ */

/**
 * Davr hisobotining kaliti — `kind` VA davr kalitning bir qismi.
 *
 * ⚠ `accuracy` bu fabrikadan FOYDALANMAYDI: aniqlik hisoboti
 *   `occupancy-queries.ts::accuracyKey` da yashaydi va u MAVJUD kalit
 *   (§5.4). Ikkinchi kalit yaratilsa `/occupancy` va `/reports` bir xil
 *   davrda IKKI KESH yozuvini to'ldirardi va «ikki xil haqiqat» aynan
 *   shu yerdan tug'ilardi.
 */
export const reportKey = (
  marketId: string,
  kind: ReportKind,
  from: string | null,
  to: string | null,
) => domainKey(marketId, "report", kind, from, to);

/**
 * Panel tushumining kaliti — ⛔ `reportKey` DAN AYRIM VA BU ATAYIN.
 *
 * `REPORT_KINDS` — EKSPORT QILINADIGAN hisobotlar reyestri (uning
 * docstringiga qarang). `live` marshrutining `.xlsx` jufti YO'Q, ya'ni
 * uni o'sha reyestrga qo'shish «bu ham yuklab olinadi» degan yolg'on
 * da'vo bo'lardi va `buildReportExportPath()` unga mavjud bo'lmagan
 * fayl yo'lini qurib berardi.
 *
 * Naqsh `compareKey` bilan bir xil — u ham xuddi shu sababdan
 * reyestrdan tashqarida.
 */
export const liveRevenueKey = (
  marketId: string,
  from: string,
  to: string,
) => domainKey(marketId, "live-revenue", from, to);

/** Uch tomonlama solishtiruvning kaliti — davri KUN, oraliq EMAS (§4.3). */
export const compareKey = (marketId: string, day: string) =>
  domainKey(marketId, "compare", day);

/**
 * Joriy bozor — kalit qurish uchun YAGONA manba.
 *
 * `occupancy-queries.ts:97-100` bilan AYNI sabab va AYNI shakl. Funksiya
 * EKSPORT QILINMAYDI — u modulning ichki kontrakti.
 */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/* --- Yo'l quruvchilar ------------------------------------------------------ */

/**
 * ⛔⛔ IKKI YO'L, IKKI NOM — VA BU ATAYIN.
 *
 * Ekran JSON o'qiydi, eksport esa `.xlsx` BAYTLARINI oladi. Bitta
 * funksiyaga format argumenti qo'shish o'sha argumentni UNUTISH
 * mumkin qilardi va unutilgan holat JIMGINA JSON qaytarardi — ya'ni
 * `saveBlob` foydalanuvchining diskiga `revenue.xlsx` nomi bilan JSON
 * yozardi. Bu §0.2 dagi 401-nosozlikning aynan shakli: tugma ishlagandek
 * ko'rinadi, Excel esa «fayl buzilgan» deydi.
 */
function buildReportDataPath(kind: ReportKind, period: ReportPeriod): string {
  const query = new URLSearchParams({ from: period.from, to: period.to });
  return `${REPORTS_PATH}/${kind}?${query.toString()}`;
}

/** ⛔ EKSPORT yo'li — `.xlsx`. `downloadReport` FAQAT shuni ishlatadi. */
export function buildReportPath(
  kind: ReportKind,
  period: ReportPeriod,
): string {
  const query = new URLSearchParams({ from: period.from, to: period.to });
  return `${REPORTS_PATH}/${kind}.xlsx?${query.toString()}`;
}

/* --- (A) Davr hisobotlari -------------------------------------------------- */

/**
 * `GET /reports/revenue?from=…&to=…` — davr tushumi (§8.2).
 *
 * ⚠ `enabled: marketId !== null` — KONTRAKT (`market-queries.ts:186-192`),
 *   qulaylik emas: bozorsiz sessiyada javob `403 market_not_selected`
 *   bo'lardi va u kesh grafida yashab qolardi.
 *
 * ⛔ `refetchOnWindowFocus: false` — yopilgan kun oynani almashtirganda
 *    o'zgarmaydi; qayta so'rash direktorning ekranini sababsiz
 *    miltillatardi.
 */
export function useRevenueReport(
  period: ReportPeriod,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: reportKey(marketId ?? "", "revenue", period.from, period.to),
    queryFn: () =>
      apiFetch(buildReportDataPath("revenue", period), {
        schema: revenueReportSchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
    staleTime: REPORT_STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });
}

/**
 * `GET /reports/live?from=…&to=…` — PANEL tushumi, BUGUN ham qamraladi.
 *
 * ⛔ `useRevenueReport` DAN AYRIM va u O'RNINI BOSMAYDI: hisobot
 *    sahifasi hamon `/reports/revenue` dan o'qiydi, chunki o'sha javob
 *    `.xlsx` ga aylanadi va imzolanadi. Bu marshrutning `.xlsx` jufti
 *    YO'Q — sabab `reports.py::live_revenue` docstringida.
 */
export function useLiveRevenue(
  period: ReportPeriod,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: liveRevenueKey(marketId ?? "", period.from, period.to),
    queryFn: () =>
      apiFetch(`/reports/live?from=${period.from}&to=${period.to}`, {
        schema: liveRevenueSchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
    staleTime: REPORT_STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });
}

/** `GET /reports/debtors?from=…&to=…` — qarzdorlik ro'yxati (§8.3). */
export function useReceivablesReport(
  period: ReportPeriod,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: reportKey(marketId ?? "", "debtors", period.from, period.to),
    queryFn: () =>
      apiFetch(buildReportDataPath("debtors", period), {
        schema: receivablesReportSchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
    staleTime: REPORT_STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });
}

/** `GET /reports/anomalies?from=…&to=…` — nomuvofiqlik arxivi (§8.5). */
export function useAnomalyArchive(
  period: ReportPeriod,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: reportKey(marketId ?? "", "anomalies", period.from, period.to),
    queryFn: () =>
      apiFetch(buildReportDataPath("anomalies", period), {
        schema: anomalyArchiveSchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
    staleTime: REPORT_STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });
}

/* --- (B) Uch tomonlama solishtiruv ---------------------------------------- */

/**
 * `GET /reports/compare?day=…` — daftar vs tizim vs AI-kutilgan (§10.4).
 *
 * ⛔ POLL YO'Q: kun ALLAQACHON yopilgan (maksimum kecha, §10.2) va
 *    javobni o'zgartiradigan yagona hodisa — daftar importi, u esa
 *    kalitni O'ZI bekor qiladi (`useLedgerUpload`).
 */
export function useThreeWayReport(
  day: string,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: compareKey(marketId ?? "", day),
    queryFn: () =>
      apiFetch(`${REPORTS_PATH}/compare?day=${encodeURIComponent(day)}`, {
        schema: threeWayReportSchema,
      }),
    enabled: marketId !== null && day !== "" && (options?.enabled ?? true),
    staleTime: COMPARE_STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });
}

/* --- (C) Eksport — ⛔ YAGONA YO'L (§12.2) ---------------------------------- */

/**
 * Zaxira fayl nomi — ⛔ ASCII shablon, bozor nomisiz (§12.3).
 *
 * ⛔ BO'SH NOM, `undefined.xlsx` VA `download` HECH QACHON. Uchalasi ham
 *    diskda tanib bo'lmas fayl qoldirardi va direktor uni qaysi davrga
 *    tegishli ekanini BILMASDI — §1.2 qoida 2 ning bevosita buzilishi.
 */
function fallbackFilename(kind: ReportKind, period: ReportPeriod): string {
  return `sbozor-${kind}-${period.from}_${period.to}.xlsx`;
}

/**
 * `Content-Disposition` dan fayl nomini O'QIYDI — ⛔ QURMAYDI (D-06).
 *
 * =========================================================================
 * ⛔⛔ NOMNING EGASI — SERVER, KLIENT FAQAT O'QIYDI.
 *
 * D-06 nomni `{market}_{hisobot}_{from}_{to}.xlsx` deb belgilagan va
 * bozor nomi — O'ZBEKCHA MATN (bo'sh joy, apostrof, kirill). Uni ASCII
 * slug'ga aylantirish qoidasi IKKI TILDA ikki marta yozilardi va bir kun
 * ajralib ketardi: server `karmana_revenue_….xlsx` deb, klient
 * `Karmana-bozori_….xlsx` deb nomlardi va ⛔ QAYSI BIRI HUJJAT ekani
 * noaniq bo'lib qolardi.
 *
 * ⚠ Sarlavha KLIENTGA OCHIQ, chunki so'rov BIR XIL ORIGIN'dan ketadi
 *   (`API_BASE_URL = "/api/v1"`, nginx orqali) [M-9]. Boshqa origin
 *   qo'yilsa CORS umuman sozlanmagani uchun avtorizatsiyaning O'ZI
 *   yiqilardi — ya'ni bu faraz loyihada allaqachon ko'taruvchi.
 * =========================================================================
 *
 * ⛔ ZAXIRA YO'L SHARTSIZ: sarlavha yo'q, bo'sh, o'qib bo'lmas yoki
 *    `download` bo'lsa — ASCII shablon ishlatiladi.
 */
export function filenameFrom(
  response: Response,
  kind: ReportKind,
  period: ReportPeriod,
): string {
  const header = response.headers.get("content-disposition");
  const parsed = header === null ? null : parseDispositionFilename(header);

  /*
   * ⛔ `download` ALOHIDA rad etiladi: ba'zi proxy'lar sarlavhani
   *   `attachment; filename=download` ga aylantiradi va u diskda
   *   kengaytmasiz «download» fayli bo'lib qolardi.
   */
  if (parsed === null || parsed === "" || parsed === "download") {
    return fallbackFilename(kind, period);
  }
  return parsed;
}

/**
 * `attachment; filename="…"` yoki `filename*=UTF-8''…` dan nomni ajratadi.
 *
 * ⚠ `filename*` OLDIN tekshiriladi (RFC 6266): u mavjud bo'lsa, u
 *   ANIQROQ shakl va `filename` esa eski klientlar uchun qoldirilgan
 *   soddalashtirilgan nusxa bo'ladi.
 *
 * ⛔ Yo'l ajratgichlari TASHLANADI: server ASCII slug quradi (D-06),
 *    lekin nom TASHQI matn bo'lgani uchun `../` yoki `/` ni ishonchli
 *    deb qabul qilish TAMOMILA keraksiz xavf bo'lardi (T-08-11).
 */
function parseDispositionFilename(header: string): string | null {
  const extended = /filename\*\s*=\s*[^']*'[^']*'([^;]+)/iu.exec(header);
  if (extended) {
    try {
      return sanitizeFilename(decodeURIComponent(extended[1].trim()));
    } catch {
      return null;
    }
  }

  const quoted = /filename\s*=\s*"([^"]*)"/iu.exec(header);
  if (quoted) return sanitizeFilename(quoted[1]);

  const bare = /filename\s*=\s*([^;]+)/iu.exec(header);
  if (bare) return sanitizeFilename(bare[1].trim());

  return null;
}

/** Yo'l ajratgichlari va boshlang'ich nuqtalarni tashlaydi (T-08-11). */
function sanitizeFilename(value: string): string {
  const base = value.split(/[/\\]/u).pop() ?? "";
  return base.replace(/^\.+/u, "").trim();
}

/**
 * `.xlsx` ni foydalanuvchining diskiga tushiradi — ⛔ YAGONA eksport yo'li.
 *
 * ⛔ HOOK EMAS, oddiy `async` funksiya (§5.4, `downloadTemplate` naqshi):
 *    bu keshlanadigan HOLAT emas, bir martalik YON TA'SIR. `useQuery` ga
 *    o'ralsa natija keshda qolib, ikkinchi bosishda ESKI faylni berardi.
 *
 * ⛔ Til so'rovda YUBORILMAYDI — server uni profildan oladi (D-06, bitta
 *    haqiqat manbai).
 *
 * ⚠ Xato `ApiError` bo'lib KO'TARILADI va chaqiruvchi uni tugma yonida
 *   INLINE ko'rsatadi, toast bilan EMAS (§12.2): toast g'oyib bo'ladi va
 *   foydalanuvchi tugmani qayta-qayta bosardi.
 */
export async function downloadReport(
  kind: ReportKind,
  period: ReportPeriod,
): Promise<void> {
  const response = await apiRequest(buildReportPath(kind, period));
  saveBlob(await response.blob(), filenameFrom(response, kind, period));
}

/**
 * Solishtiruv eksporti — ⛔ `REPORT_KINDS` DAN TASHQARIDA (§12.1).
 *
 * Uning davri KUN, shakli esa IMZOLI varaq. Reyestrga tiqish
 * `REPORT_KINDS` ni «hisobot turi» dan «yuklab olinadigan narsa» ga
 * aylantirardi va davr parametrlari IXTIYORIY bo'lib qolardi.
 */
export async function downloadCompareReport(day: string): Promise<void> {
  const response = await apiRequest(
    `${REPORTS_PATH}/compare.xlsx?day=${encodeURIComponent(day)}`,
  );
  const header = response.headers.get("content-disposition");
  const parsed = header === null ? null : parseDispositionFilename(header);

  saveBlob(
    await response.blob(),
    parsed === null || parsed === "" || parsed === "download"
      ? `sbozor-compare-${day}.xlsx`
      : parsed,
  );
}

/* --- (D) Daftar importi — ⛔ YAGONA mutatsiya (D-17) ----------------------- */

/**
 * Daftar shabloni — ⛔ AYNAN IKKI USTUN (D-17, 08-14).
 *
 * =========================================================================
 * ⛔⛔ NEGA `ImportKind` GA BESHINCHI A'ZO QO'SHILMADI.
 *
 * `ImportKind` (`market-queries.ts`) reyestr EMAS, ⛔ OQIM tavsifi: har
 * a'zosi `POST /imports/{kind}` marshrutiga, `import-panel.tsx` dagi
 * matn uchligiga va tugagandan keyingi ⛔ REESTR MARSHRUTIGA
 * (`LIST_PATHS`) bog'langan. Daftarda ularning BIRORTASI yo'q: u
 * `POST /reports/compare/ledger` ga boradi, o'z paneliga ega va
 * tugagandan keyin ⛔ HECH QAYERGA yo'naltirmaydi (natija shu ekranda).
 *
 * ⛔ Beshinchi a'zo qo'shilsa `Record<ImportKind, …>` jadvallari uchta
 *    faylda to'ldirilishi kerak bo'lardi va ularning uchtasi ham
 *    ⛔ TO'QILGAN qiymat olardi — «daftar reestri» degan marshrut
 *    MAVJUD EMAS.
 *
 * ⚠ Shablon marshruti esa AYNAN o'sha (`/imports/template?kind=`), ya'ni
 *   ikkinchi oqim ham qurilmaydi (§10.3).
 * =========================================================================
 */
export async function downloadLedgerTemplate(): Promise<void> {
  const response = await apiRequest(`${IMPORTS_PATH}/template?kind=ledger`);
  saveBlob(await response.blob(), "sbozor-daftar-shablon.xlsx");
}

/**
 * `POST /reports/compare/ledger` — kunlik daftarning `.xlsx` importi.
 *
 * ⛔ ALL-OR-NOTHING (§10.3): `422` da server xatolar ro'yxatini qaytaradi
 *    va HECH NIMA yozilmaydi. Yarim yozilgan daftar solishtiruvni
 *    ma'nosiz qilardi.
 */
export async function uploadLedger(day: string, file: File) {
  const form = new FormData();
  form.append("file", file);

  return apiFetch(
    `${REPORTS_PATH}/compare/ledger?day=${encodeURIComponent(day)}`,
    { method: "POST", body: form, schema: ledgerImportResultSchema },
  );
}

/**
 * Daftar importi + bekor qilish.
 *
 * =========================================================================
 * ⛔⛔ `invalidateQueries`, ⛔ `removeQueries` EMAS — VA SABAB
 *     6-FAZANIKIDAN FARQ QILADI (§5.4).
 *
 * 6-fazada keshdan CHIQARISH kerak edi: eski summa NOTO'G'RI PUL
 * YIG'ISHGA olib borardi. Bu yerda esa keshdan chiqarish jadvalni
 * ⛔ BO'SHATARDI va bozor admini importni ⛔ MUVAFFAQIYATSIZ deb
 * o'ylardi — ya'ni to'g'ri ishlagan yozuv buzuq bo'lib ko'rinardi va u
 * faylni QAYTA yuklardi (DL-6 tasdig'ini har safar bosib).
 * =========================================================================
 *
 * ⛔ AYNAN BITTA KALIT: `compareKey(marketId, day)`. Davr hisobotlari
 *    (`report`) daftardan HOSILA EMAS — daftar TIZIMGA yozilmaydi, u
 *    faqat solishtiruvning uchinchi ustuni. Ularni ham bekor qilish
 *    to'rt so'rovni sababsiz qayta yurgizardi va «hisobot o'zgardi»
 *    degan YOLG'ON signal berardi.
 */
export function useLedgerUpload() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";

  return useMutation({
    mutationFn: (input: { day: string; file: File }) =>
      uploadLedger(input.day, input.file),
    onSuccess: (_data, input) => {
      void client.invalidateQueries({
        queryKey: compareKey(marketId, input.day),
      });
    },
  });
}
