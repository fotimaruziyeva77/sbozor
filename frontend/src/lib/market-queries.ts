"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

/*
 * ⚠ IMPORT YO'NALISHI ONGLI QAROR — «qatlam buzilishi» deb qaytarib
 *   tashlanmasin (Topilma №A).
 *
 * `wizard-steps.ts` — SOF domen moduli: JSX yo'q, `"use client"` yo'q va
 * yagona importi `@/lib/api-types`. Ya'ni bu yerdan uni chaqirish sikl
 * hosil QILMAYDI.
 *
 * Ko'rib chiqilgan va RAD ETILGAN ikki muqobil:
 *   (a) qoidani shu faylga NUSXALASH — aynan tuzatilayotgan nuqsonni
 *       (bitta qoida, ikki nusxa, ajralib ketish) qaytarardi;
 *   (b) funksiyani KOMPONENTGA ko'chirish — render qatlamiga tarmoq
 *       chaqiruvini kiritardi.
 */
import { fallbackStep } from "@/components/wizard/wizard-steps";
import { ApiError, apiFetch, apiRequest } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";
import {
  assignmentListResponseSchema,
  assignmentItemSchema,
  calendarExceptionSchema,
  calendarResponseSchema,
  categoryItemSchema,
  categoryListResponseSchema,
  emptyResponseSchema,
  importErrorResponseSchema,
  importResultSchema,
  staffImportResultSchema,
  marketCreateResponseSchema,
  marketIncompleteSchema,
  marketListSchema,
  setupStatusResponseSchema,
  stallDetailSchema,
  stallListResponseSchema,
  stallMapResponseSchema,
  tariffItemSchema,
  tariffListResponseSchema,
  vendorListItemSchema,
  vendorListResponseSchema,
  zoneItemSchema,
  zoneListResponseSchema,
} from "@/lib/api-types";
import type {
  BlockingItem,
  ImportErrorItem,
  ImportErrorResponse,
  ImportResult,
  StaffImportResult,
} from "@/lib/api-types";
import { usersKey } from "@/lib/queries";

/*
 * =============================================================================
 * 2-faza domenining SERVER HOLATI (02-08…02-12 kontrakti).
 *
 * Har bir endpoint FAQAT shu yerda chaqiriladi: komponent HTTP qatlamiga
 * to'g'ridan-to'g'ri tegmaydi. Sabab — invalidatsiya. Rasta yaratilgandan
 * keyin ro'yxat ham, xarita ham, ustaning to'liqlik holati ham eskiradi;
 * uch joyni yangilashni komponentga qoldirish "bir joyda esdan chiqadi"
 * sinfidagi xatoni KAFOLATLAYDI — admin yangi rastani ro'yxatda ko'rib
 * turadi-yu, xaritada ko'rmaydi va ustada "rasta qo'shilmagan" to'sig'i
 * turaveradi.
 *
 * `queries.ts` (01-07 ma'muriy ekranlari) BU YERGA KO'CHIRILMAYDI: u
 * mavjud ekranlarga xizmat qiladi va uni qayta yozish ularning testlarini
 * sababsiz qayta ko'rib chiqishga majburlardi. Ikki modul bir xil
 * qoidalarga bo'ysunadi.
 *
 * TARTIB SERVERDA: `GET /stalls` `code_sort` bo'yicha inson-raqamli
 * tartibda keladi (2 < 10 < 100) va bu yerda ham, komponentda ham QAYTA
 * SARALANMAYDI — klient saralashi uchala tilda boshqa natija berardi.
 *
 * KESH — TENANT CHEGARASINING BIR QISMI (CR-01). CLAUDE.md ning eng qat'iy
 * me'moriy cheklovi «hamma jadvalda `market_id`» Postgres'da bajarilgan va
 * bir muddat brauzerda tashlab yuborilgan edi: kalitlar global (`["zones"]`)
 * bo'lgani uchun ikki bozor bitta kesh yozuvini bo'lishardi. Endi har bir
 * domen kaliti `["m", marketId, ...]` bilan boshlanadi va ISTISNO YO'Q —
 * pastdagi `domainKey` ga qarang.
 * =============================================================================
 */

/* --- Yo'l konstantalari --------------------------------------------------- */

export const ZONES_PATH = "/zones";
export const CATEGORIES_PATH = "/categories";
export const STALLS_PATH = "/stalls";
export const STALL_MAP_PATH = "/stalls/map";
export const TARIFFS_PATH = "/tariffs";
export const CALENDAR_PATH = "/calendar";
export const VENDORS_PATH = "/vendors";
export const ASSIGNMENTS_PATH = "/assignments";
export const MARKETS_PATH = "/markets";
export const IMPORTS_PATH = "/imports";

/**
 * Bitta sahifadagi element soni (UI-SPEC §8.3).
 *
 * Backend chegarasi 200 (`STALL_PAGE_SIZE_MAX` / `VENDOR_PAGE_SIZE_MAX`);
 * 50 — o'qish uchun qulay sahifa va "Ko'proq yuklash" qolganini kursor
 * bilan olib keladi.
 */
export const PAGE_SIZE = 50;

/* --- Query kalitlari ------------------------------------------------------ */

/**
 * HAR BIR domen kaliti shu yerdan quriladi — `["m", marketId, ...]`.
 *
 * ⚠ GLOBAL KALIT KONSTANTALARI (`ZONES_KEY`, `STALLS_KEY`, ...) ATAYIN
 * O'CHIRILGAN va qaytarilmaydi. Ular qolsa keyingi kod ularni "qulay" deb
 * qayta ishlatardi va bo'shliq jimgina qaytardi — CR-01 ning o'zi aynan shu
 * sinfdagi xato edi. Endi doiralashni chetlab o'tish TS xatosisiz mumkin
 * emas: kalit fabrikasining birinchi argumenti `marketId`.
 *
 * Prefiks bo'yicha bekor qilish shu shakl bilan ishlaydi: TanStack Query
 * kalitni PREFIKS sifatida solishtiradi, ya'ni `domainKey(m, "stalls")`
 * `["m", m, "stalls", "list", filtrlar]` ni ham, `[..., "detail", id]` ni
 * ham qamraydi. Shu sababli `["m", marketId]` prefiksi bitta bozorning
 * BARCHA domen so'rovlarini bildiradi.
 */
export const domainKey = (marketId: string, ...rest: readonly unknown[]) =>
  ["m", marketId, ...rest] as const;

export const zonesKey = (marketId: string) => domainKey(marketId, "zones");
export const categoriesKey = (marketId: string) =>
  domainKey(marketId, "categories");
export const stallsKey = (marketId: string, filters: StallFilters) =>
  domainKey(marketId, "stalls", "list", filters);
export const stallKey = (marketId: string, stallId: string) =>
  domainKey(marketId, "stalls", "detail", stallId);
export const mapKey = (marketId: string) => domainKey(marketId, "map");
export const tariffsKey = (marketId: string, categoryId: string | null) =>
  domainKey(marketId, "tariffs", categoryId);
export const calendarKey = (marketId: string) =>
  domainKey(marketId, "calendar");
export const vendorsKey = (marketId: string, filters: VendorFilters) =>
  domainKey(marketId, "vendors", "list", filters);
export const vendorKey = (marketId: string, vendorId: string) =>
  domainKey(marketId, "vendors", "detail", vendorId);
export const assignmentsKey = (marketId: string, stallId: string) =>
  domainKey(marketId, "assignments", stallId);
export const setupStatusKey = (marketId: string) =>
  domainKey(marketId, "setup-status");

/**
 * Joriy bozor — kalit qurish uchun YAGONA manba.
 *
 * `useAuthStore()` ni har hookda takrorlash o'rniga bitta joyda o'qiladi:
 * takrorlangan `principal?.marketId ?? null` qatorlari orasidan bittasi
 * tushib qolsa, o'sha hook jimgina global kalitga qaytardi.
 */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

/*
 * Invalidatsiya YORDAMCHILARI.
 *
 * Ular ATAYIN funksiya, konstanta emas: bir nechta mutatsiya bir xil
 * to'plamni bekor qiladi va uni har `onSuccess` da qo'lda sanash aynan
 * "bittasini unutish" xatosiga olib kelardi.
 *
 * `setup-status` bir vaqtlar KENG (`marketId` siz) bekor qilinardi va sabab
 * qilib "usta faqat BITTA bozor uchun ochiq bo'ladi" taxmini keltirilgan
 * edi. TAXMIN NOTO'G'RI BO'LIB CHIQDI: platforma admini bitta sessiyada
 * ikkinchi bozor yaratishi — ustaning butun maqsadi, va aynan shu yo'l
 * A bozorining zonalarini B bozorining 2-qadamida ko'rsatgan (CR-01).
 * Yangi qoida bitta jumla: HAR BIR domen kaliti `market_id` bilan
 * boshlanadi va istisno yo'q.
 */
function invalidate(client: QueryClient, keys: readonly (readonly unknown[])[]) {
  for (const key of keys) {
    void client.invalidateQueries({ queryKey: key });
  }
}

/** Rasta o'zgarishi: ro'yxat + xarita + zona/toifa sanoqlari + usta holati. */
const stallSideEffects = (marketId: string) =>
  [
    domainKey(marketId, "stalls"),
    mapKey(marketId),
    zonesKey(marketId),
    categoriesKey(marketId),
    setupStatusKey(marketId),
  ] as const;

/* --- Zonalar (D-03) ------------------------------------------------------- */

/**
 * ⚠ `enabled` shartidagi `marketId !== null` QULAYLIK EMAS, kontrakt.
 *
 * Bozorsiz sessiyada domen so'rovi serverda `409 market_not_selected` oladi
 * (`deps.py:408-412`) va o'sha xato kesh grafida yashab qolardi. Aynan shu
 * sababli `marketId` `null` bo'lganda kalitdagi bo'sh satr ham xavfsiz:
 * o'sha kalit ostida hech qachon ma'lumot yozilmaydi.
 */
export function useZonesQuery(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: zonesKey(marketId ?? ""),
    queryFn: () => apiFetch(ZONES_PATH, { schema: zoneListResponseSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

export function useCreateZone() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { name: string }) =>
      apiFetch(ZONES_PATH, {
        method: "POST",
        body: { name: input.name },
        schema: zoneItemSchema,
      }),
    onSuccess: () =>
      invalidate(client, [zonesKey(marketId), setupStatusKey(marketId)]),
  });
}

export function useUpdateZone() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { id: string; name: string }) =>
      apiFetch(`${ZONES_PATH}/${input.id}`, {
        method: "PATCH",
        body: { name: input.name },
        schema: zoneItemSchema,
      }),
    // Zona NOMI rasta ro'yxatida va xaritada ham ko'rinadi (`zone_name`).
    onSuccess: () =>
      invalidate(client, [
        zonesKey(marketId),
        domainKey(marketId, "stalls"),
        mapKey(marketId),
        setupStatusKey(marketId),
      ]),
  });
}

export function useDeleteZone() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (zoneId: string) =>
      apiFetch(`${ZONES_PATH}/${zoneId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () =>
      invalidate(client, [zonesKey(marketId), setupStatusKey(marketId)]),
  });
}

/* --- Toifalar (D-05) ------------------------------------------------------ */

export function useCategoriesQuery(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: categoriesKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(CATEGORIES_PATH, { schema: categoryListResponseSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

export function useCreateCategory() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { name: string }) =>
      apiFetch(CATEGORIES_PATH, {
        method: "POST",
        body: { name: input.name },
        schema: categoryItemSchema,
      }),
    onSuccess: () =>
      invalidate(client, [categoriesKey(marketId), setupStatusKey(marketId)]),
  });
}

export function useUpdateCategory() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { id: string; name: string }) =>
      apiFetch(`${CATEGORIES_PATH}/${input.id}`, {
        method: "PATCH",
        body: { name: input.name },
        schema: categoryItemSchema,
      }),
    // Toifa NOMI rasta ro'yxatida va tarif tarixida ham ko'rinadi.
    onSuccess: () =>
      invalidate(client, [
        categoriesKey(marketId),
        domainKey(marketId, "stalls"),
        domainKey(marketId, "tariffs"),
        setupStatusKey(marketId),
      ]),
  });
}

export function useDeleteCategory() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (categoryId: string) =>
      apiFetch(`${CATEGORIES_PATH}/${categoryId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () =>
      invalidate(client, [
        categoriesKey(marketId),
        domainKey(marketId, "tariffs"),
        setupStatusKey(marketId),
      ]),
  });
}

/* --- Rastalar (D-01/D-02/D-04) -------------------------------------------- */

/**
 * `/stalls` filtrlari (UI-SPEC §8.3). Bo'sh satr — "filtr qo'yilmagan".
 *
 * Tiplar `string`, `UUID` emas: qiymatlar `nuqs` orqali URL'dan keladi va
 * URL har doim satr beradi. Ularni bu yerda tiplashga urinish har
 * chaqiruvchida bitta o'girish qatlamini talab qilardi.
 */
export type StallFilters = {
  q: string;
  zone: string;
  category: string;
  status: string;
};

export const EMPTY_STALL_FILTERS: StallFilters = {
  q: "",
  zone: "",
  category: "",
  status: "",
};

function buildStallsPath(filters: StallFilters, cursor: string | null): string {
  const params = new URLSearchParams();
  // Nomlar backend'dagi `StallQuery` dan.
  if (filters.q) params.set("q", filters.q);
  if (filters.zone) params.set("zone", filters.zone);
  if (filters.category) params.set("category", filters.category);
  if (filters.status) params.set("status", filters.status);
  params.set("limit", String(PAGE_SIZE));
  if (cursor) params.set("cursor", cursor);
  return `${STALLS_PATH}?${params.toString()}`;
}

/**
 * Rasta reestri — KURSOR bilan sahifalanadi ("Ko'proq yuklash", §8.3).
 *
 * Sahifa RAQAMI ishlatilmaydi: reestr so'rovlar ORASIDA o'sadi (import,
 * ikkinchi admin) va raqamli sahifalashda yangi qatorlar sahifalarni surib
 * yuborardi. `queryKey` filtrlarni to'liq o'z ichiga oladi — filtr
 * o'zgarganda kesh yangi zanjir boshlaydi va eski sahifalar aralashmaydi.
 */
export function useStallsQuery(filters: StallFilters) {
  const marketId = useMarketId();
  return useInfiniteQuery({
    queryKey: stallsKey(marketId ?? "", filters),
    queryFn: ({ pageParam }) =>
      apiFetch(buildStallsPath(filters, pageParam), {
        schema: stallListResponseSchema,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    enabled: marketId !== null,
  });
}

export function useStallQuery(stallId: string | null) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: stallKey(marketId ?? "", stallId ?? ""),
    queryFn: () =>
      apiFetch(`${STALLS_PATH}/${stallId}`, { schema: stallDetailSchema }),
    enabled: marketId !== null && stallId !== null,
  });
}

export type StallCreateInput = {
  code: string;
  zone_id: string;
  category_id: string;
  status: string;
  note: string | null;
};

/**
 * Rasta yaratish.
 *
 * ⚠ `valid_from` MAYDONI YO'Q va qo'shilmaydi (D-04): boshlang'ich toifa
 * davrining sanasini SERVER `market_profile.operating_since` dan oladi.
 * Klient sana bera olsa, o'tmishdagi kunni tanlab hisob tarixini surib
 * qo'yardi (T-02-61a).
 */
export function useCreateStall() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: StallCreateInput) =>
      apiFetch(STALLS_PATH, {
        method: "POST",
        body: input,
        schema: stallDetailSchema,
      }),
    onSuccess: () => invalidate(client, stallSideEffects(marketId)),
  });
}

export type StallUpdateInput = {
  id: string;
  code?: string;
  zone_id?: string;
  status?: string;
  note?: string | null;
};

/**
 * Rastani tahrirlash.
 *
 * ⚠ `category_id` BU YERDA YO'Q (D-04): toifa — SANADAN kuchga kiradigan
 * atribut va uni oddiy tahrir bilan almashtirish o'tmishdagi hisobni qayta
 * yozardi. Uning yo'li — `useSetStallCategory`.
 */
export function useUpdateStall() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: ({ id, ...body }: StallUpdateInput) =>
      apiFetch(`${STALLS_PATH}/${id}`, {
        method: "PATCH",
        body,
        schema: stallDetailSchema,
      }),
    onSuccess: (_data, variables) => {
      invalidate(client, stallSideEffects(marketId));
      void client.invalidateQueries({
        queryKey: stallKey(marketId, variables.id),
      });
    },
  });
}

/**
 * Rastaga YANGI toifa davrini ochadi (D-04 — voris modeli).
 *
 * Javob TANASIZ (201): yangi davr KELAJAKDA kuchga kiradi, ya'ni bugungi
 * holatni ko'rsatuvchi javob "yozildimi?" savoliga yo'q deb javob berardi.
 *
 * `valid_from` faqat KELAJAK bo'lishi mumkin; bugun ham rad etiladi (403
 * `category_period_past_locked`). Sana maydonining `min` atributi —
 * QULAYLIK, darvoza serverda.
 */
export function useSetStallCategory() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: {
      stallId: string;
      category_id: string;
      valid_from: string;
    }) =>
      apiFetch(`${STALLS_PATH}/${input.stallId}/category`, {
        method: "POST",
        body: { category_id: input.category_id, valid_from: input.valid_from },
        schema: emptyResponseSchema,
      }),
    onSuccess: (_data, variables) => {
      invalidate(client, stallSideEffects(marketId));
      void client.invalidateQueries({
        queryKey: stallKey(marketId, variables.stallId),
      });
    },
  });
}

/**
 * Plan-xarita — butun bozor BIR SO'ROVDA (sahifalashsiz).
 *
 * `GET /stalls?limit=1000` ATAYIN ishlatilmaydi: xarita katagi uchun atigi
 * to'rt maydon kerak va alohida endpoint 1000 rastali bozorda ham javobni
 * kichik ushlab turadi.
 */
export function useStallMapQuery(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: mapKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(STALL_MAP_PATH, { schema: stallMapResponseSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

/* --- Tariflar (D-06/D-07) ------------------------------------------------- */

/**
 * Tarif tarixi + `min_valid_from`.
 *
 * ⚠ JAVOB O'ZGARTIRILMASDAN QAYTARILADI. `min_valid_from` ga `??` yoki
 * `||` bilan fallback berish, yoki uni ertangi sana bilan almashtirish
 * TAQIQ: qoralama bozorda server ruxsat bergan eng erta sana O'TMISHDA
 * (`operating_since`) va lokal "ertangi kun" hisobi ustaning 4-qadamini
 * UI darajasida bajarilmas qilardi (T-02-104a).
 */
export function useTariffsQuery(
  categoryId: string | null = null,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: tariffsKey(marketId ?? "", categoryId),
    queryFn: () =>
      apiFetch(
        categoryId ? `${TARIFFS_PATH}?category=${categoryId}` : TARIFFS_PATH,
        { schema: tariffListResponseSchema },
      ),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

/*
 * Tarif o'zgarishi TOIFA ro'yxatiga ham tegadi: `CategoryItem` da
 * `current_tariff_soum` bor va u eskirsa, ekranda "tarif kiritilmagan"
 * ogohlantirishi narx qo'shilgandan keyin ham turaverardi.
 */
const tariffSideEffects = (marketId: string) =>
  [
    domainKey(marketId, "tariffs"),
    categoriesKey(marketId),
    domainKey(marketId, "stalls"),
    setupStatusKey(marketId),
  ] as const;

export function useCreateTariff() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: {
      category_id: string;
      amount_soum: number;
      valid_from: string;
    }) =>
      apiFetch(TARIFFS_PATH, {
        method: "POST",
        body: input,
        schema: tariffItemSchema,
      }),
    onSuccess: () => invalidate(client, tariffSideEffects(marketId)),
  });
}

export function useUpdateTariff() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: {
      id: string;
      amount_soum?: number;
      valid_from?: string;
    }) =>
      apiFetch(`${TARIFFS_PATH}/${id}`, {
        method: "PATCH",
        body,
        schema: tariffItemSchema,
      }),
    onSuccess: () => invalidate(client, tariffSideEffects(marketId)),
  });
}

/** Faqat KELAJAKDAGI qator o'chiriladi — o'tgani serverda qulflangan. */
export function useDeleteTariff() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (tariffId: string) =>
      apiFetch(`${TARIFFS_PATH}/${tariffId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => invalidate(client, tariffSideEffects(marketId)),
  });
}

/* --- Ish kunlari kalendari (D-17/D-18) ------------------------------------ */

export function useCalendarQuery(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: calendarKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(CALENDAR_PATH, { schema: calendarResponseSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

const calendarSideEffects = (marketId: string) =>
  [calendarKey(marketId), setupStatusKey(marketId)] as const;

export function useUpdateWeekdays() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (openWeekdays: readonly number[]) =>
      apiFetch(`${CALENDAR_PATH}/weekdays`, {
        method: "PUT",
        body: { open_weekdays: openWeekdays },
        schema: calendarResponseSchema,
      }),
    onSuccess: () => invalidate(client, calendarSideEffects(marketId)),
  });
}

export function useCreateException() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: {
      exception_date: string;
      is_open: boolean;
      note: string | null;
    }) =>
      apiFetch(`${CALENDAR_PATH}/exceptions`, {
        method: "POST",
        body: input,
        schema: calendarExceptionSchema,
      }),
    onSuccess: () => invalidate(client, calendarSideEffects(marketId)),
  });
}

export function useDeleteException() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (exceptionId: string) =>
      apiFetch(`${CALENDAR_PATH}/exceptions/${exceptionId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => invalidate(client, calendarSideEffects(marketId)),
  });
}

/* --- Sotuvchilar va biriktirishlar (D-09…D-12) ---------------------------- */

export type VendorFilters = { q: string };

export const EMPTY_VENDOR_FILTERS: VendorFilters = { q: "" };

function buildVendorsPath(
  filters: VendorFilters,
  cursor: string | null,
): string {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  params.set("limit", String(PAGE_SIZE));
  if (cursor) params.set("cursor", cursor);
  return `${VENDORS_PATH}?${params.toString()}`;
}

/**
 * Sotuvchi reestri — kursor bilan sahifalanadi.
 *
 * ⚠ HAR SO'ROV SHAXSIY MA'LUMOTNI O'QIYDI va server buni auditga yozadi
 * (D-09). Shuning uchun so'rov `enabled` bilan boshqarilishi kerak:
 * ko'rinmaydigan ekran uchun fon so'rovi audit jurnalini ma'nosiz
 * "ko'rildi" yozuvlari bilan to'ldirardi.
 */
export function useVendorsQuery(
  filters: VendorFilters,
  options?: { enabled?: boolean },
) {
  const marketId = useMarketId();
  return useInfiniteQuery({
    queryKey: vendorsKey(marketId ?? "", filters),
    queryFn: ({ pageParam }) =>
      apiFetch(buildVendorsPath(filters, pageParam), {
        schema: vendorListResponseSchema,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

export function useVendorQuery(vendorId: string | null) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: vendorKey(marketId ?? "", vendorId ?? ""),
    queryFn: () =>
      apiFetch(`${VENDORS_PATH}/${vendorId}`, { schema: vendorListItemSchema }),
    enabled: marketId !== null && vendorId !== null,
  });
}

export function useCreateVendor() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { full_name: string; phone: string }) =>
      apiFetch(VENDORS_PATH, {
        method: "POST",
        body: input,
        schema: vendorListItemSchema,
      }),
    onSuccess: () =>
      invalidate(client, [
        domainKey(marketId, "vendors"),
        setupStatusKey(marketId),
      ]),
  });
}

export function useUpdateVendor() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: {
      id: string;
      full_name?: string;
      phone?: string;
    }) =>
      apiFetch(`${VENDORS_PATH}/${id}`, {
        method: "PATCH",
        body,
        schema: vendorListItemSchema,
      }),
    // Sotuvchi ISMI rasta ro'yxatida ham ko'rinadi (`vendor_name`).
    onSuccess: (_data, variables) => {
      invalidate(client, [
        domainKey(marketId, "vendors"),
        domainKey(marketId, "stalls"),
        domainKey(marketId, "assignments"),
      ]);
      void client.invalidateQueries({
        queryKey: vendorKey(marketId, variables.id),
      });
    },
  });
}

export function useStallAssignmentsQuery(stallId: string | null) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: assignmentsKey(marketId ?? "", stallId ?? ""),
    queryFn: () =>
      apiFetch(`${STALLS_PATH}/${stallId}/assignments`, {
        schema: assignmentListResponseSchema,
      }),
    enabled: marketId !== null && stallId !== null,
  });
}

/*
 * Biriktirish o'zgarishi UCH yuzaga tegadi: sotuvchi ro'yxatidagi rasta
 * sanog'i, rasta reestridagi `vendor_name` va xaritadagi `has_vendor`.
 * "Band, lekin sotuvchisiz" — 6-fazadagi anomaliya hisobining asosi, ya'ni
 * eskirgan `has_vendor` xaritani jimgina yolg'on qilardi.
 */
const assignmentSideEffects = (marketId: string) =>
  [
    domainKey(marketId, "assignments"),
    domainKey(marketId, "vendors"),
    domainKey(marketId, "stalls"),
    mapKey(marketId),
    setupStatusKey(marketId),
  ] as const;

export function useCreateAssignment() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: {
      stall_id: string;
      vendor_id: string;
      from_date: string;
      to_date: string | null;
    }) =>
      apiFetch(ASSIGNMENTS_PATH, {
        method: "POST",
        body: input,
        schema: assignmentItemSchema,
      }),
    onSuccess: () => invalidate(client, assignmentSideEffects(marketId)),
  });
}

/**
 * OCHIQ davrni yopadi.
 *
 * `from_date` tahrirlanmaydi (D-10): o'tmishdagi kunlarning qarz egaligini
 * boshqa sotuvchiga ko'chirish `daily_charges` ni qayta baholardi. Davrni
 * "surish" uchun yagona yo'l — eskisini yopib, yangisini ochish.
 */
export function useCloseAssignment() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: { id: string; to_date: string }) =>
      apiFetch(`${ASSIGNMENTS_PATH}/${input.id}`, {
        method: "PATCH",
        body: { to_date: input.to_date },
        schema: assignmentItemSchema,
      }),
    onSuccess: () => invalidate(client, assignmentSideEffects(marketId)),
  });
}

/* --- "Yangi bozor" ustasi (MARKET-01, D-16) ------------------------------- */

/**
 * ⚠ `MARKETS_KEY` ATAYIN DOIRALANMAGAN va shunday qoladi.
 *
 * `GET /markets` — PLATFORMA darajasidagi ro'yxat: u bozor tanlashdan
 * OLDIN, tenant konteksti hali umuman yo'q paytda o'qiladi, ya'ni uni
 * `market_id` bilan doiralash mumkin ham emas. Bu izoh shu yerda turibdi,
 * chunki usiz keyingi o'quvchi uni "doiralash unutilgan" deb hisoblab
 * "tuzatardi" — va bozor tanlash ekranini bo'shatib qo'yardi.
 *
 * Tenant chegarasi bu kalitda BOSHQA chora bilan ta'minlanadi: sessiya
 * identifikatori o'zgarganda butun kesh `client.clear()` bilan bo'shaydi
 * (`query-provider.tsx`), ya'ni oldingi foydalanuvchining bozorlar ro'yxati
 * keyingisiga qolmaydi.
 */
export const MARKETS_KEY = ["markets"] as const;

/**
 * Foydalanuvchi kira oladigan bozorlar (D-06).
 *
 * FILTR YO'Q — qoralama bozor ham ro'yxatga tushadi (UI-SPEC §12.1.1):
 * usta 1-qadamda qoralama tug'diradi va foydalanuvchi ishni yarim tashlab
 * ketishi mumkin; u qaytib kelganda aynan shu ro'yxatdan davom etadi.
 */
export function useMarketsQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: MARKETS_KEY,
    queryFn: () => apiFetch(MARKETS_PATH, { schema: marketListSchema }),
    enabled: options?.enabled ?? true,
  });
}

/**
 * `setup-status` javobsiz qolganda tushiladigan qadam.
 *
 * ⚠ MA'NOSI TORAYDI (Topilma №A): bu qiymat endi FAQAT "javob umuman
 * kelmadi" holatiga tegishli. Ilgari u ikkinchi vazifani ham bajarardi —
 * "javob keldi va `blocking` bo'sh" — va aynan o'sha ikkinchi ma'no
 * `fallbackStep()` bilan ZIDDIYATDA edi: bitta savolga ikki javob. Endi
 * javob BOR bo'lgan har qanday holatda qarorni `fallbackStep()` beradi.
 *
 * FAIL-SAFE, fail-closed EMAS — bu navigatsiya, xavfsizlik chegarasi emas.
 * Endpoint yiqilsa foydalanuvchi baribir ustaga kiradi va 1-qadamdan davom
 * etadi; muqobil variant — "xato" ekrani — uni qoralama bozor ichiga
 * umuman kirita olmasdi.
 */
export const FIRST_WIZARD_STEP = 1;

/**
 * Bozor tanlangandan keyin qo'niladigan qadam (UI-SPEC §6.4 qoidasi).
 *
 * ⛔ QARORNING O'ZI BU YERDA EMAS: u `wizard-steps.ts::fallbackStep()` da
 * va bu YAGONA manba. Ilgari qoida shu funksiya tanasida IKKINCHI marta
 * yozilgan edi va ikki nusxa ajralib ketgandi — bo'sh `blocking` uchun
 * `fallbackStep()` faollashtirish qadamini, bu yer esa birinchi qadamni
 * qaytarardi. Natijada 7/7 bajarilgan qoralama bozor har safar ustaning
 * boshiga tushib, "Davom etish" karuselida aylanardi.
 *
 * Bu funksiyaning qolgan mas'uliyati — TARMOQ: javobni olib kelish va
 * javobsizlikni fail-safe qadamga aylantirish.
 *
 * HOOK EMAS: chaqiruv bozor tanlangan LAHZADA, mutatsiya `onSuccess` i
 * ichida bo'ladi. `useQuery` ga o'ralsa u render tsikliga bog'lanardi va
 * "tanlash tugadi, endi qayerga?" savoliga o'z vaqtida javob bermasdi.
 */
export async function fetchFirstIncompleteStep(
  marketId: string,
): Promise<number> {
  try {
    const status = await apiFetch(`${MARKETS_PATH}/${marketId}/setup-status`, {
      schema: setupStatusResponseSchema,
    });
    return fallbackStep(status);
  } catch {
    return FIRST_WIZARD_STEP;
  }
}

export type MarketCreateInput = {
  name: string;
  timezone: string;
  operating_since: string;
  open_weekdays?: readonly number[] | null;
  address?: string | null;
  tin?: string | null;
  bank_account?: string | null;
  bank_mfo?: string | null;
  contact_phone?: string | null;
};

/**
 * Ustaning 1-qadami — QORALAMA bozor tug'iladi (`is_active === false`).
 *
 * ⚠ Bu mutatsiya YANGI bozor tug'diradi, ya'ni `onSuccess` paytida store'da
 * hamon ESKI (yoki `null`) bozor turadi va `setupStatusKey` shunga tushadi.
 * Bu zarar qilmaydi: darhol keyin `applySession(...)` sessiya identifikatorini
 * o'zgartiradi va butun keshni bo'shatadi (`query-provider.tsx`). Platforma
 * ro'yxati (`MARKETS_KEY`) esa doiralanmagan va to'g'ri bekor qilinadi.
 */
export function useCreateMarket() {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation({
    mutationFn: (input: MarketCreateInput) =>
      apiFetch(MARKETS_PATH, {
        method: "POST",
        body: input,
        schema: marketCreateResponseSchema,
      }),
    onSuccess: () =>
      invalidate(client, [MARKETS_KEY, setupStatusKey(marketId)]),
  });
}

/**
 * Ustaning to'liqlik holati.
 *
 * `can_activate` SERVER qarori va u sanoqlardan QAYTA HISOBLANMAYDI —
 * aks holda to'liqlik qoidasi ikki joyda yashab, bir kun `activate`
 * darvozasi bilan ajralib ketardi.
 */
export function useSetupStatusQuery(
  marketId: string | null,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: setupStatusKey(marketId ?? ""),
    queryFn: () =>
      apiFetch(`${MARKETS_PATH}/${marketId}/setup-status`, {
        schema: setupStatusResponseSchema,
      }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}

/**
 * Bozorni faollashtirish (ustaning 7-qadami).
 *
 * 409 `market_incomplete` — XATO EMAS, yo'l ko'rsatkichi: javob bilan
 * birga `blocking[]` keladi va UI foydalanuvchini chala qadamga olib
 * boradi (UI-SPEC §6.6).
 */
export function useActivateMarket() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (marketId: string) =>
      apiFetch(`${MARKETS_PATH}/${marketId}/activate`, {
        method: "POST",
        schema: marketCreateResponseSchema,
      }),
    // `marketId` STORE'dan emas, MUTATSIYA argumentidan olinadi: faollashgan
    // bozor aynan shu, va u store'dagi joriy bozordan farq qilishi mumkin.
    onSuccess: (_data, marketId) =>
      invalidate(client, [MARKETS_KEY, setupStatusKey(marketId)]),
  });
}

/**
 * 409 `market_incomplete` javobidagi to'siqlar — `ApiError.body` dan.
 *
 * `null` qaytsa javob to'liqlik haqida EMAS (masalan `market_is_active`,
 * 403 yoki tarmoq): chaqiruvchi u holda odatdagi xato matnini ko'rsatadi.
 *
 * NEGA HOOK EMAS va nega KOMPONENTDA emas: shakl chegarada, bitta joyda
 * ochiladi (`importErrorsOf` bilan AYNI naqsh). Komponent `ApiError` ni
 * ham, zod sxemasini ham ko'rmaydi — u faqat `BlockingItem[]` oladi va
 * uni `setup-status` dan kelgan ro'yxat bilan BIR XIL yo'ldan chizadi
 * (UI-SPEC §6.6: alohida xato UI'si YO'Q).
 */
export function activationBlockingOf(
  error: unknown,
): readonly BlockingItem[] | null {
  if (!(error instanceof ApiError)) return null;
  const parsed = marketIncompleteSchema.safeParse(error.body);
  return parsed.success ? parsed.data.blocking : null;
}

/** Tashlab ketilgan QORALAMANI o'chiradi. Jonli bozor hech qachon o'chmaydi. */
export function useDeleteDraftMarket() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (marketId: string) =>
      apiFetch(`${MARKETS_PATH}/${marketId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: (_data, marketId) =>
      invalidate(client, [MARKETS_KEY, setupStatusKey(marketId)]),
  });
}

/* --- Excel import (D-13/D-14/D-15) ---------------------------------------- */

export type ImportKind = "stalls" | "vendors" | "staff";

/**
 * 422 javobining tanasi — `ApiError` ga biriktirilgan.
 *
 * `null` qaytsa xato import validatsiyasi EMAS (masalan 403 yoki tarmoq):
 * chaqiruvchi u holda odatdagi xato matnini ko'rsatadi.
 */
export function importErrorsOf(error: unknown): ImportErrorResponse | null {
  if (!(error instanceof ApiError)) return null;
  const parsed = importErrorResponseSchema.safeParse(error.body);
  return parsed.success ? parsed.data : null;
}

/**
 * `.xlsx` faylni yuklaydi (D-14: validatsiya YOZISHDAN OLDIN).
 *
 * 422 kelganda bazaga HECH NARSA yozilmagan — xatolar ro'yxatini
 * `importErrorsOf(error)` beradi.
 */
/**
 * Import yon ta'sirlari — `kind` bo'yicha IKKI xil to'plam (WR-10).
 *
 * ⚠ `vendors` tarmog'ida `assignments` MAJBURIY:
 * `ImportRepository.insert_vendors()` (`import_repo.py:223-234`) rasta kodi
 * ko'rsatilgan HAR sotuvchi uchun `stall_assignments` qatori yozadi. Bu
 * kalit tushib qolganida ochiq turgan `GET /stalls/{id}/assignments` paneli
 * import tugagandan keyin ham import OLDIDAGI bo'sh tarixni ko'rsatib
 * turardi.
 *
 * `stalls` va `map` sotuvchi tarmog'ida ham bor: rasta qatoridagi
 * `has_vendor` va `vendor_name` biriktirish yaratilganda o'zgaradi.
 *
 * Ro'yxat qo'lda emas, shu yerda quriladi — ayni modulning invalidatsiya
 * kontrakti buzilgan YAGONA joyi aynan qo'lda yozilgan ro'yxat edi.
 */
const importSideEffects = (
  marketId: string,
  kind: ImportKind,
): readonly (readonly unknown[])[] => {
  if (kind === "stalls") {
    return [
      domainKey(marketId, "stalls"),
      mapKey(marketId),
      zonesKey(marketId),
      categoriesKey(marketId),
      setupStatusKey(marketId),
    ];
  }
  if (kind === "vendors") {
    return [
      domainKey(marketId, "vendors"),
      domainKey(marketId, "assignments"),
      domainKey(marketId, "stalls"),
      mapKey(marketId),
      setupStatusKey(marketId),
    ];
  }
  /*
   * `staff` tarmog'i ham endi DOIRALANGAN (WR-09, 07-23).
   *
   * ⚠ ILGARI BU YERDA «YAGONA doiralanMAGAN kalitli tarmoq» deb yozilgan
   *   edi va sabab MEROS deb ko'rsatilgan: xodimlar kaliti 01-07 da
   *   global (`["users"]`) qilib yozilgan edi. O'sha meros `usersKey()` bilan
   *   tugatildi, ya'ni izohning O'ZI ham eskirdi — uni qoldirish kodda
   *   ⛔ YOLG'ON hujjat qoldirardi.
   *
   * ⛔ KALIT SHU YERDA QAYTA IXTIRO QILINMAYDI: fabrikasi `queries.ts` da
   *    va ro'yxatning EGASI o'sha modul. Ikkinchi nusxa bir muddat bir xil
   *    shakl berib, keyin jimgina ajralib ketardi.
   */
  return [usersKey(marketId), setupStatusKey(marketId)];
};

/**
 * `.xlsx` faylni yuklaydi (D-14: validatsiya YOZISHDAN OLDIN).
 *
 * ⚠ JAVOB SXEMASI `kind` BO'YICHA TANLANADI. `staff` javobi ochiq
 * parollarni olib yuradi va uning shakli boshqa (`credentials[]`);
 * bitta "hammasiga to'g'ri keladigan" sxema parol maydonini ixtiyoriy
 * qilardi va tip xavfsizligini yo'qotardi.
 *
 * ⚠ `useMutation` (`useQuery` EMAS) — parol React Query KESHIGA
 * tushmasligi kerak (`temp-password-dialog.tsx` dagi bilan aynan bir xil
 * sabab, D-02).
 */
export function useImportMutation<K extends ImportKind>(kind: K) {
  const client = useQueryClient();
  const marketId = useMarketId() ?? "";
  return useMutation<K extends "staff" ? StaffImportResult : ImportResult, Error, File>({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const path = `${IMPORTS_PATH}/${kind}`;
      const result =
        kind === "staff"
          ? await apiFetch(path, {
              method: "POST",
              body: form,
              schema: staffImportResultSchema,
            })
          : await apiFetch(path, {
              method: "POST",
              body: form,
              schema: importResultSchema,
            });
      return result as K extends "staff" ? StaffImportResult : ImportResult;
    },
    onSuccess: () => invalidate(client, importSideEffects(marketId, kind)),
  });
}

/**
 * `Blob` ni foydalanuvchining diskiga tushiradi.
 *
 * `revokeObjectURL` MAJBURIY (T-02-104): usiz obyekt URL'i sahifa yopilgunga
 * qadar xotirada qoladi va u ORQALI fayl mazmuni har qanday skriptga ochiq
 * bo'lardi.
 *
 * Bekor qilish DARHOL emas, keyingi makrotaskda: `click()` dan keyin
 * yuklash ba'zi brauzerlarda ASINXRON boshlanadi va zudlik bilan revoke
 * qilish uni bo'sh fayl bilan tugatardi.
 *
 * 02-24 dan boshlab EKSPORT QILINADI: `staff-credentials.tsx` faylni
 * KLIENTDA quradi (server yo'li parollarni ikkinchi marta tarmoqqa
 * chiqarardi) va o'sha `revokeObjectURL` gigiyenasiga muhtoj. Ikkinchi
 * nusxa yozish uni bir kun unutishga olib kelardi.
 */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/**
 * Import shablonini yuklab oladi.
 *
 * HOOK EMAS, oddiy funksiya: bu keshlanadigan holat emas, bir martalik
 * yon ta'sir. `useQuery` ga o'ralsa natija keshda qolib, zona nomi
 * o'zgargandan keyin ham eski shablonni berardi (server uni HAR SAFAR
 * yangidan quradi).
 *
 * Til so'rovda YUBORILMAYDI — server uni profildan oladi (bitta haqiqat
 * manbai).
 */
export async function downloadTemplate(kind: ImportKind): Promise<void> {
  const response = await apiRequest(`${IMPORTS_PATH}/template?kind=${kind}`);
  saveBlob(await response.blob(), `sbozor-${kind}-shablon.xlsx`);
}

/**
 * 422 dagi xatolar ro'yxatini `.xlsx` qilib yuklab oladi (UI-SPEC §8.5).
 *
 * Ro'yxat serverga QAYTA YUBORILADI va u uni SAQLAMAYDI: 300 qatorlik xato
 * ro'yxatini bazaga yozish hech qanday savolga javob bermaydigan, lekin
 * saqlash muddati talab qiladigan ma'lumot yaratardi.
 *
 * Ekranda faqat birinchi 50 tasi ko'rsatiladi (T-02-103) — qolgani aynan
 * shu fayl orqali yetkaziladi.
 */
export async function downloadErrorReport(
  errors: readonly ImportErrorItem[],
): Promise<void> {
  const response = await apiRequest(`${IMPORTS_PATH}/errors.xlsx`, {
    method: "POST",
    body: { errors },
  });
  saveBlob(await response.blob(), "sbozor-import-xatolar.xlsx");
}
