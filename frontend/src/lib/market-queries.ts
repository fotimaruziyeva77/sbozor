"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { ApiError, apiFetch, apiRequest } from "@/lib/api-client";
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
} from "@/lib/api-types";

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

export const ZONES_KEY = ["zones"] as const;
export const CATEGORIES_KEY = ["categories"] as const;
export const STALLS_KEY = ["stalls"] as const;
export const MAP_KEY = ["map"] as const;
export const TARIFFS_KEY = ["tariffs"] as const;
export const CALENDAR_KEY = ["calendar"] as const;
export const VENDORS_KEY = ["vendors"] as const;
export const ASSIGNMENTS_KEY = ["assignments"] as const;
export const SETUP_STATUS_KEY = ["setup-status"] as const;

export const zonesKey = () => ZONES_KEY;
export const categoriesKey = () => CATEGORIES_KEY;
export const stallsKey = (filters: StallFilters) =>
  [...STALLS_KEY, "list", filters] as const;
export const stallKey = (stallId: string) =>
  [...STALLS_KEY, "detail", stallId] as const;
export const mapKey = () => MAP_KEY;
export const tariffsKey = (categoryId: string | null) =>
  [...TARIFFS_KEY, categoryId] as const;
export const calendarKey = () => CALENDAR_KEY;
export const vendorsKey = (filters: VendorFilters) =>
  [...VENDORS_KEY, "list", filters] as const;
export const vendorKey = (vendorId: string) =>
  [...VENDORS_KEY, "detail", vendorId] as const;
export const assignmentsKey = (stallId: string) =>
  [...ASSIGNMENTS_KEY, stallId] as const;
export const setupStatusKey = (marketId: string) =>
  [...SETUP_STATUS_KEY, marketId] as const;

/*
 * Invalidatsiya YORDAMCHILARI.
 *
 * Ular ATAYIN funksiya, konstanta emas: bir nechta mutatsiya bir xil
 * to'plamni bekor qiladi va uni har `onSuccess` da qo'lda sanash aynan
 * "bittasini unutish" xatosiga olib kelardi.
 *
 * `setup-status` KENG bekor qilinadi (`marketId` siz): usta faqat BITTA
 * bozor uchun ochiq bo'ladi va kalitni aniqlashtirish uchun mutatsiyaga
 * `marketId` ni uzatish har chaqiruvchini bozor kontekstini bilishga
 * majburlardi — holbuki server uni tokendan oladi.
 */
function invalidate(client: QueryClient, keys: readonly (readonly unknown[])[]) {
  for (const key of keys) {
    void client.invalidateQueries({ queryKey: key });
  }
}

/** Rasta o'zgarishi: ro'yxat + xarita + zona/toifa sanoqlari + usta holati. */
const STALL_SIDE_EFFECTS = [
  STALLS_KEY,
  MAP_KEY,
  ZONES_KEY,
  CATEGORIES_KEY,
  SETUP_STATUS_KEY,
] as const;

/* --- Zonalar (D-03) ------------------------------------------------------- */

export function useZonesQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: zonesKey(),
    queryFn: () => apiFetch(ZONES_PATH, { schema: zoneListResponseSchema }),
    enabled: options?.enabled ?? true,
  });
}

export function useCreateZone() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string }) =>
      apiFetch(ZONES_PATH, {
        method: "POST",
        body: { name: input.name },
        schema: zoneItemSchema,
      }),
    onSuccess: () => invalidate(client, [ZONES_KEY, SETUP_STATUS_KEY]),
  });
}

export function useUpdateZone() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: string; name: string }) =>
      apiFetch(`${ZONES_PATH}/${input.id}`, {
        method: "PATCH",
        body: { name: input.name },
        schema: zoneItemSchema,
      }),
    // Zona NOMI rasta ro'yxatida va xaritada ham ko'rinadi (`zone_name`).
    onSuccess: () =>
      invalidate(client, [ZONES_KEY, STALLS_KEY, MAP_KEY, SETUP_STATUS_KEY]),
  });
}

export function useDeleteZone() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (zoneId: string) =>
      apiFetch(`${ZONES_PATH}/${zoneId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => invalidate(client, [ZONES_KEY, SETUP_STATUS_KEY]),
  });
}

/* --- Toifalar (D-05) ------------------------------------------------------ */

export function useCategoriesQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: categoriesKey(),
    queryFn: () =>
      apiFetch(CATEGORIES_PATH, { schema: categoryListResponseSchema }),
    enabled: options?.enabled ?? true,
  });
}

export function useCreateCategory() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string }) =>
      apiFetch(CATEGORIES_PATH, {
        method: "POST",
        body: { name: input.name },
        schema: categoryItemSchema,
      }),
    onSuccess: () => invalidate(client, [CATEGORIES_KEY, SETUP_STATUS_KEY]),
  });
}

export function useUpdateCategory() {
  const client = useQueryClient();
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
        CATEGORIES_KEY,
        STALLS_KEY,
        TARIFFS_KEY,
        SETUP_STATUS_KEY,
      ]),
  });
}

export function useDeleteCategory() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (categoryId: string) =>
      apiFetch(`${CATEGORIES_PATH}/${categoryId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () =>
      invalidate(client, [CATEGORIES_KEY, TARIFFS_KEY, SETUP_STATUS_KEY]),
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
  return useInfiniteQuery({
    queryKey: stallsKey(filters),
    queryFn: ({ pageParam }) =>
      apiFetch(buildStallsPath(filters, pageParam), {
        schema: stallListResponseSchema,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}

export function useStallQuery(stallId: string | null) {
  return useQuery({
    queryKey: stallKey(stallId ?? ""),
    queryFn: () =>
      apiFetch(`${STALLS_PATH}/${stallId}`, { schema: stallDetailSchema }),
    enabled: stallId !== null,
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
  return useMutation({
    mutationFn: (input: StallCreateInput) =>
      apiFetch(STALLS_PATH, {
        method: "POST",
        body: input,
        schema: stallDetailSchema,
      }),
    onSuccess: () => invalidate(client, STALL_SIDE_EFFECTS),
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
  return useMutation({
    mutationFn: ({ id, ...body }: StallUpdateInput) =>
      apiFetch(`${STALLS_PATH}/${id}`, {
        method: "PATCH",
        body,
        schema: stallDetailSchema,
      }),
    onSuccess: (_data, variables) => {
      invalidate(client, STALL_SIDE_EFFECTS);
      void client.invalidateQueries({ queryKey: stallKey(variables.id) });
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
      invalidate(client, STALL_SIDE_EFFECTS);
      void client.invalidateQueries({ queryKey: stallKey(variables.stallId) });
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
  return useQuery({
    queryKey: mapKey(),
    queryFn: () =>
      apiFetch(STALL_MAP_PATH, { schema: stallMapResponseSchema }),
    enabled: options?.enabled ?? true,
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
  return useQuery({
    queryKey: tariffsKey(categoryId),
    queryFn: () =>
      apiFetch(
        categoryId ? `${TARIFFS_PATH}?category=${categoryId}` : TARIFFS_PATH,
        { schema: tariffListResponseSchema },
      ),
    enabled: options?.enabled ?? true,
  });
}

/*
 * Tarif o'zgarishi TOIFA ro'yxatiga ham tegadi: `CategoryItem` da
 * `current_tariff_soum` bor va u eskirsa, ekranda "tarif kiritilmagan"
 * ogohlantirishi narx qo'shilgandan keyin ham turaverardi.
 */
const TARIFF_SIDE_EFFECTS = [
  TARIFFS_KEY,
  CATEGORIES_KEY,
  STALLS_KEY,
  SETUP_STATUS_KEY,
] as const;

export function useCreateTariff() {
  const client = useQueryClient();
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
    onSuccess: () => invalidate(client, TARIFF_SIDE_EFFECTS),
  });
}

export function useUpdateTariff() {
  const client = useQueryClient();
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
    onSuccess: () => invalidate(client, TARIFF_SIDE_EFFECTS),
  });
}

/** Faqat KELAJAKDAGI qator o'chiriladi — o'tgani serverda qulflangan. */
export function useDeleteTariff() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (tariffId: string) =>
      apiFetch(`${TARIFFS_PATH}/${tariffId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => invalidate(client, TARIFF_SIDE_EFFECTS),
  });
}

/* --- Ish kunlari kalendari (D-17/D-18) ------------------------------------ */

export function useCalendarQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: calendarKey(),
    queryFn: () =>
      apiFetch(CALENDAR_PATH, { schema: calendarResponseSchema }),
    enabled: options?.enabled ?? true,
  });
}

export function useUpdateWeekdays() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (openWeekdays: readonly number[]) =>
      apiFetch(`${CALENDAR_PATH}/weekdays`, {
        method: "PUT",
        body: { open_weekdays: openWeekdays },
        schema: calendarResponseSchema,
      }),
    onSuccess: () => invalidate(client, [CALENDAR_KEY, SETUP_STATUS_KEY]),
  });
}

export function useCreateException() {
  const client = useQueryClient();
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
    onSuccess: () => invalidate(client, [CALENDAR_KEY, SETUP_STATUS_KEY]),
  });
}

export function useDeleteException() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (exceptionId: string) =>
      apiFetch(`${CALENDAR_PATH}/exceptions/${exceptionId}`, {
        method: "DELETE",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => invalidate(client, [CALENDAR_KEY, SETUP_STATUS_KEY]),
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
  return useInfiniteQuery({
    queryKey: vendorsKey(filters),
    queryFn: ({ pageParam }) =>
      apiFetch(buildVendorsPath(filters, pageParam), {
        schema: vendorListResponseSchema,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    enabled: options?.enabled ?? true,
  });
}

export function useVendorQuery(vendorId: string | null) {
  return useQuery({
    queryKey: vendorKey(vendorId ?? ""),
    queryFn: () =>
      apiFetch(`${VENDORS_PATH}/${vendorId}`, { schema: vendorListItemSchema }),
    enabled: vendorId !== null,
  });
}

export function useCreateVendor() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { full_name: string; phone: string }) =>
      apiFetch(VENDORS_PATH, {
        method: "POST",
        body: input,
        schema: vendorListItemSchema,
      }),
    onSuccess: () => invalidate(client, [VENDORS_KEY, SETUP_STATUS_KEY]),
  });
}

export function useUpdateVendor() {
  const client = useQueryClient();
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
      invalidate(client, [VENDORS_KEY, STALLS_KEY, ASSIGNMENTS_KEY]);
      void client.invalidateQueries({ queryKey: vendorKey(variables.id) });
    },
  });
}

export function useStallAssignmentsQuery(stallId: string | null) {
  return useQuery({
    queryKey: assignmentsKey(stallId ?? ""),
    queryFn: () =>
      apiFetch(`${STALLS_PATH}/${stallId}/assignments`, {
        schema: assignmentListResponseSchema,
      }),
    enabled: stallId !== null,
  });
}

/*
 * Biriktirish o'zgarishi UCH yuzaga tegadi: sotuvchi ro'yxatidagi rasta
 * sanog'i, rasta reestridagi `vendor_name` va xaritadagi `has_vendor`.
 * "Band, lekin sotuvchisiz" — 6-fazadagi anomaliya hisobining asosi, ya'ni
 * eskirgan `has_vendor` xaritani jimgina yolg'on qilardi.
 */
const ASSIGNMENT_SIDE_EFFECTS = [
  ASSIGNMENTS_KEY,
  VENDORS_KEY,
  STALLS_KEY,
  MAP_KEY,
  SETUP_STATUS_KEY,
] as const;

export function useCreateAssignment() {
  const client = useQueryClient();
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
    onSuccess: () => invalidate(client, ASSIGNMENT_SIDE_EFFECTS),
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
  return useMutation({
    mutationFn: (input: { id: string; to_date: string }) =>
      apiFetch(`${ASSIGNMENTS_PATH}/${input.id}`, {
        method: "PATCH",
        body: { to_date: input.to_date },
        schema: assignmentItemSchema,
      }),
    onSuccess: () => invalidate(client, ASSIGNMENT_SIDE_EFFECTS),
  });
}

/* --- "Yangi bozor" ustasi (MARKET-01, D-16) ------------------------------- */

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
 * FAIL-SAFE, fail-closed EMAS — bu navigatsiya, xavfsizlik chegarasi emas.
 * Endpoint yiqilsa foydalanuvchi baribir ustaga kiradi va 1-qadamdan davom
 * etadi; muqobil variant — "xato" ekrani — uni qoralama bozor ichiga
 * umuman kirita olmasdi.
 */
export const FIRST_WIZARD_STEP = 1;

/**
 * Birinchi TUGALLANMAGAN qadam raqami (UI-SPEC §6.4 qoidasi).
 *
 * `blocking[]` dagi ENG KICHIK qadam olinadi, "oxirgi ochilgan qadam"
 * EMAS: klientda hech qanday xotira yo'q va bo'lmasligi ham kerak —
 * haqiqat manbai DB'dagi qoralama bozorning O'ZI.
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
    const steps = status.blocking.map((item) => item.step);
    return steps.length > 0 ? Math.min(...steps) : FIRST_WIZARD_STEP;
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

/** Ustaning 1-qadami — QORALAMA bozor tug'iladi (`is_active === false`). */
export function useCreateMarket() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: MarketCreateInput) =>
      apiFetch(MARKETS_PATH, {
        method: "POST",
        body: input,
        schema: marketCreateResponseSchema,
      }),
    onSuccess: () => invalidate(client, [MARKETS_KEY, SETUP_STATUS_KEY]),
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
    onSuccess: () => invalidate(client, [MARKETS_KEY, SETUP_STATUS_KEY]),
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
    onSuccess: () => invalidate(client, [MARKETS_KEY, SETUP_STATUS_KEY]),
  });
}

/* --- Excel import (D-13/D-14/D-15) ---------------------------------------- */

export type ImportKind = "stalls" | "vendors";

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
export function useImportMutation(kind: ImportKind) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return apiFetch(`${IMPORTS_PATH}/${kind}`, {
        method: "POST",
        body: form,
        schema: importResultSchema,
      });
    },
    onSuccess: () =>
      invalidate(client, [
        kind === "stalls" ? STALLS_KEY : VENDORS_KEY,
        MAP_KEY,
        ZONES_KEY,
        CATEGORIES_KEY,
        SETUP_STATUS_KEY,
      ]),
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
 */
function saveBlob(blob: Blob, filename: string): void {
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
